"""
Data model for the Feature Engine.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple, Union
from enum import Enum

from ruamel import yaml
from functools import reduce
from pathlib import Path

import dash_cytoscape as cyto
from dash import html
import networkx as nx


class RelationshipInvalidError(Exception):
    """This exception is raised when a relationship
    between features is invalid."""
    pass


class NoSuchFeatureException(Exception):
    """Raised when a feature is not found in any context."""
    pass


class FeatureGuidException(Exception):
    """Raised when a feature has an invalid guid."""
    pass


class CompileException(Exception):
    """Raised when the feature graph cannot be compiled."""
    pass


class BindingTime(Enum):
    COMPILATION = "compilation"
    INITIALIZATION = "initialization"
    RUNTIME = "runtime"


class RelationshipTypes(Enum):
    ALTERNATIVE = "alternative"
    INCOMPATIBLE = "incompatible"
    COMPLEX = "complex"  # complex, nontrivial relationship between features


class Direction(Enum):
    TO_SELF = "to_self"
    TO_OTHER = "to_other"


@dataclass
class Relationship:
    """
    A relationship between two features.
    """
    guid: int
    rel: RelationshipTypes


@dataclass
class DirectionalRelationship(Relationship):
    """
    A relationship between two features with explicit relationship direction.
    """
    direction: Direction


@dataclass
class Feature:
    """
    Describes a feature representation.
    """
    guid: int
    name: str
    binding_time: BindingTime
    rationale: str
    is_mandatory: bool
    relationships: List[Relationship] = field(default_factory=list)

    def filter_relationships(self, relationship_type: RelationshipTypes) -> List[Relationship]:
        """
        Filter relationships by relationship type.
        """
        return [rel for rel in self.relationships if rel.rel == relationship_type]

    def has_rel_to(self, other: Feature) -> bool:
        return self.get_rel_to(other) is not None

    def get_rel_to(self, other: Feature) -> Optional[Relationship]:
        for r in self.relationships:
            if r.guid == other.guid:
                return r
        for r in other.relationships:
            if r.guid == self.guid:
                return r

    @property
    def relationship_guids(self):
        return [r.guid for r in self.relationships]

    @classmethod
    def from_dict(cls, d: dict) -> Feature:
        """
        Constructs a Feature from a dictionary.
        """
        return Feature(
            d["guid"],
            d["name"],
            BindingTime(d["binding_time"]),
            d["rationale"],
            d["is_mandatory"],
            [Relationship(r["guid"], RelationshipTypes(r["rel"])) for r in d["relationships"]],
        )


RuleFailMessage = str
RuleFunction = Callable[[Feature, Feature], bool]
RuleFunctionWithMessage = Callable[[Feature, Feature], Tuple[bool, RuleFailMessage]]


def rule(rule_function: RuleFunctionWithMessage) -> RuleFunctionWithMessage:
    def wrapper(f: Feature, g: Feature) -> Tuple[bool, RuleFailMessage]:
        """
        Returns true if the two features are compatible. Explicitly
        disallows self-relationships.

        Note for developers: This wrapper can be modified to account
        for extra logic that should be applied to each rule.
        """
        rule_met, message = rule_function(f, g)
        return f.guid != g.guid and rule_met, message
    return wrapper


# LATER: refactor to make color style configurable
class Colors(Enum):
    """
    Colors for the feature graph.
    """
    MANDATORY = "#eb4034"
    OPTIONAL = "#79e05c"
    INCOMPATIBLE = "#f50000"
    ALTERNATIVE = "#6a12e6"
    DEFAULT = "#514b59"


@rule
def __disallow_obligatory_mutual_exclusion(f1: Feature, f2: Feature) -> Tuple[bool, RuleFailMessage]:
    if not (f1.is_mandatory and f2.is_mandatory and
            f1.get_rel_to(f2) == RelationshipTypes.INCOMPATIBLE):
        return False, "Obligatory functions cannot be mutually exclusive. " + \
                      f"Features: {f1.name}/{f1.guid} and {f2.name}/{f2.guid}"
    return True, "OK"


@rule
def __disallow_conflicting_relationships(f1: Feature, f2: Feature) -> Tuple[bool, RuleFailMessage]:
    if f1.get_rel_to(f2) is not None and f2.get_rel_to(f1) is not None:
        # check only if mutual relationship exists
        return True, "OK"
    else:
        return False, f"Conflicting relationships: {f1.name}/{f1.guid} and {f2.name}/{f2.guid}: " + \
            f"{f1.name} has {f1.get_rel_to(f2)} and {f2.name} has {f2.get_rel_to(f1)}"


@rule
def __disallow_nonunique_guids(f1: Feature, f2: Feature) -> Tuple[bool, RuleFailMessage]:
    if f1.guid == f2.guid:
        return False, f"Features {f1.name}/{f1.guid} and {f2.name}/{f2.guid} have the same guid"
    return True, "OK"


def _default_rules():
    return [
        __disallow_obligatory_mutual_exclusion,
        __disallow_conflicting_relationships,
        __disallow_nonunique_guids,
    ]


@dataclass
class FeatureContainer:

    features: List[Feature] = field(default_factory=list)
    debug: bool = False
    rules: List[RuleFunctionWithMessage] = field(default_factory=_default_rules, init=False)

    def __post_init__(self):
        # to make user experience better, no explicit call to `compile()`
        # should be necessary, however there should be a way to split
        # initialization from compilation if we need to debug the graph
        if not self.debug:
            self.compile()

    @classmethod
    def from_yaml(cls, path: Union[str, Path], debug: bool = False) -> FeatureContainer:
        """
        Creates a FeatureContainer from a YAML file.
        """
        with open(path, "r") as f:
            dct = yaml.YAML(typ="unsafe", pure=True).load(f)
            return cls([Feature.from_dict(f) for f in dct["features"]], debug)

    def to_yaml(self, path: Union[str, Path]) -> None:
        """
        Writes a FeatureContainer to a YAML file.
        """
        with open(path, "w") as f:
            yaml.dump(self, f)

    def get_feature_by_guid(self, guid: int) -> Feature:
        """Extracts a feature from the container by its GUID

        Args:
            guid (int): GUID of the feature to extract

        Raises:
            NoSuchFeatureException: when a feature with the given GUID
                does not exist in the container
            FeatureGuidException: when multiple features with the same
                GUID exist in the container

        Returns:
            Feature: the `Feature` object that matches the GUID
        """
        matching = list(filter(lambda f: f.guid == guid, self.features))
        if len(matching) == 0:
            raise NoSuchFeatureException(f"No feature with guid {guid}")
        elif len(matching) == 1:
            return matching[0]
        else:
            raise FeatureGuidException(
                f"Multiple features with guid {guid}! This is not allowed."
            )

    @property
    def edges(self):
        """Lists all edges in the feature graph as `(Feature, Feature)` tuples."""
        return [(f, self.get_feature_by_guid(r.guid)) for f in self.features for r in f.relationships]

    @property
    def nx_nodes(self):
        """Creates a list of nodes for the `networkx` graph."""
        return [
            (f.guid, {k: v for k, v in f.__dict__.items() if k != "guid"})
            for f in self.features
        ]

    @property
    def nx_edges(self):
        """Creates a list of edges for the `networkx` graph."""
        return reduce(lambda x, y: x + y, [
            [(f.guid, r.guid) for r in f.relationships]
            for f in self.features
        ])

    def to_nx_graph(self) -> nx.Graph:
        """Converts the feature graph to a `networkx` graph."""
        G = nx.Graph()
        G.add_nodes_from(self.nx_nodes)
        G.add_edges_from(self.nx_edges)
        return G

    def cytoscape(self):
        """Produces a `cytoscape` representation of the feature graph.
        This component can be used within Python Dash applications to
        visualize the feature graph.
        """
        nodes = [{"data": {"id": str(f.guid), "label": f.name}, "style": {
                  "background-color": Colors.MANDATORY.value if f.is_mandatory else Colors.OPTIONAL.value}}
                 for f in self.features]
        edges = [{"data": {"source": str(f.guid), "target": str(r.guid), "label": str(r.rel.value)}, "style": {
                 #   "mid-target-arrow-color": "red",
                 #   "mid-target-arrow-shape": "vee",
                  "line-color": Colors.ALTERNATIVE.value if r.rel == RelationshipTypes.ALTERNATIVE else Colors.DEFAULT.value,
                  'opacity': 0.9,
                  #   'z-index': 5000,
                  'label': 'data(label)',
                  "text-wrap": "wrap"}}
                 for f in self.features
                 for r in f.relationships]
        return html.Div([
            cyto.Cytoscape(
                id='cytoscape',
                elements=nodes + edges,
                layout={'name': 'circle'},
                style={
                    'height': '95vh',
                    'width': '100%'
                },
                stylesheet=[
                    {
                        'selector': 'edge',
                        'style': {
                            'label': 'data(label)'
                        }
                    }
                ]
            )
        ])

    def compile(self):
        """This method walks the feature graph
        and determines whether the relationships between
        features are correct or not.
        """
        for is_rule_met, message in [r(f1, f2) for f1, f2 in self.edges for r in self.rules]:
            if not is_rule_met:
                raise CompileException(message)
