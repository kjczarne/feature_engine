"""
Data model for the Feature Engine.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Generator, List, Optional, Tuple, Union
from enum import Enum

from ruamel import yaml
from functools import reduce
from pathlib import Path

import dash_cytoscape as cyto
from dash import html
import networkx as nx


__version__ = "0.1.0"


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


class MalformedYamlFileException(Exception):
    """Raised when the YAML file loaded is `None`."""
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

    def get_rel_to(self, other: Feature, drop_direction: bool = False) -> Optional[Relationship]:
        for r in self.relationships:
            if r.guid == other.guid:
                return r
        if not drop_direction:
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
RuleTupleReturn = Tuple[bool, RuleFailMessage]
RuleFunction = Callable[[Feature, Feature], bool]
EdgeRuleFunctionWithMessage = Callable[[Feature, Feature], RuleTupleReturn]


def edge_rule(rule_function: EdgeRuleFunctionWithMessage) -> EdgeRuleFunctionWithMessage:
    def wrapper(f: Feature, g: Feature) -> RuleTupleReturn:
        """
        Returns true if the two features are compatible.

        Note for developers: This wrapper can be modified to account
        for extra logic that should be applied to each rule.
        """
        return rule_function(f, g)
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


@edge_rule
def __disallow_obligatory_mutual_exclusion(f1: Feature, f2: Feature) -> RuleTupleReturn:

    def eval_relationship(relationship: RelationshipTypes) -> RuleTupleReturn:
        if relationship == RelationshipTypes.INCOMPATIBLE and f1.is_mandatory and f2.is_mandatory:
            return False, "Obligatory functions cannot be mutually exclusive. " + \
                          f"Features: {f1.name}/{f1.guid} and {f2.name}/{f2.guid}"
        return True, f"OK: no mutual exclusion among mandatory features: {f1.name}/{f1.guid} and {f2.name}/{f2.guid}"
    rel = f1.get_rel_to(f2)
    if rel is not None:
        return eval_relationship(rel.rel)
    else:
        # just using any other `RelationshipTypes` here to reuse the `else` logic
        return eval_relationship(RelationshipTypes.COMPLEX)


@edge_rule
def __disallow_conflicting_relationships(f1: Feature, f2: Feature) -> RuleTupleReturn:
    if f1.get_rel_to(f2, drop_direction=True) is not None and f2.get_rel_to(f1, drop_direction=True) is not None:
        # check only if mutual relationship exists
        return False, f"Conflicting relationships: {f1.name}/{f1.guid} and {f2.name}/{f2.guid}: " + \
            f"{f1.name} has {f1.get_rel_to(f2)} and {f2.name} has {f2.get_rel_to(f1)}"
    else:
        return True, "OK: no conflicting relationships"


GraphRuleGeneratorReturn = Generator[RuleTupleReturn, None, None]
GraphRuleFunctionWithMessage = Callable[[List[Feature]], GraphRuleGeneratorReturn]


def graph_rule(rule_function: GraphRuleFunctionWithMessage) -> GraphRuleFunctionWithMessage:
    def wrapper(fg: List[Feature]) -> GraphRuleGeneratorReturn:
        """
        Returns true if the graph rule is fulfilled.

        Note for developers: This wrapper can be modified to account
        for extra logic that should be applied to each rule.
        """
        return rule_function(fg)
    return wrapper


@graph_rule
def __disallow_nonunique_guids(features: List[Feature]) -> GraphRuleGeneratorReturn:
    sorted_by_guid = sorted(features, key=lambda f: f.guid)
    for idx, f in enumerate(sorted_by_guid):
        if idx == len(sorted_by_guid) - 1:
            break
        fplus1 = sorted_by_guid[idx + 1]
        if f.guid == fplus1.guid:
            yield False, f"Features {f.name}/{f.guid} and {fplus1.name}/{fplus1.guid} have the same guid"
        yield True, "OK: all GUIDs are unique"


def _default_edge_rules():
    return [
        __disallow_obligatory_mutual_exclusion,
        __disallow_conflicting_relationships,
    ]


def _default_graph_rules():
    return [
        __disallow_nonunique_guids,
    ]


@dataclass
class FeatureContainer:
    features: List[Feature] = field(default_factory=list)
    version: str = field(default=__version__, compare=False)
    debug: bool = field(default=False, compare=False)
    edge_rules: List[EdgeRuleFunctionWithMessage] = field(
        default_factory=_default_edge_rules,
        init=False,
        compare=False
    )
    graph_rules: List[GraphRuleFunctionWithMessage] = field(
        default_factory=_default_graph_rules,
        init=False,
        compare=False
    )

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
            if dct is None:
                raise MalformedYamlFileException(f"Malformed YAML file: {path}")
            return cls([Feature.from_dict(f) for f in dct["features"]], dct["version"], debug)

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
        for is_rule_met, message in [r(f1, f2) for f1, f2 in self.edges for r in self.edge_rules]:
            if self.debug:
                print(message)
            if not is_rule_met:
                raise CompileException(message)
        for is_rule_met, message in [t for r in self.graph_rules for t in r(self.features)]:
            if self.debug:
                print(message)
            if not is_rule_met:
                raise CompileException(message)
