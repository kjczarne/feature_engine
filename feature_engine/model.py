"""
Data model for the Feature Engine.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from enum import Enum, auto

from ruamel import yaml
from functools import reduce

import dash_cytoscape as cyto
from dash import html
import networkx as nx


class BindingTime(Enum):
    COMPILATION = "compilation"
    INITIALIZATION = "initialization"
    RUNTIME = "runtime"


class RelationshipTypes(Enum):
    ALTERNATIVE = "alternative"
    INCOMPATIBLE = "incompatible"


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


@dataclass
class FeatureContainer:

    features: List[Feature] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str) -> FeatureContainer:
        """
        Creates a FeatureContainer from a YAML file.
        """
        with open(path, "r") as f:
            dct = yaml.load(f, Loader=yaml.Loader)
            return cls([Feature.from_dict(f) for f in dct["features"]])

    def to_yaml(self, path: str) -> None:
        """
        Writes a FeatureContainer to a YAML file.
        """
        with open(path, "w") as f:
            yaml.dump(self, f)

    @property
    def nx_nodes(self):
        return [
            (f.guid, {k: v for k, v in f.__dict__.items() if k != "guid"})
            for f in self.features
        ]

    @property
    def nx_edges(self):
        return reduce(lambda x, y: x + y, [
            [(f.guid, r.guid) for r in f.relationships]
            for f in self.features
        ])

    def to_nx_graph(self) -> nx.Graph:
        G = nx.Graph()
        G.add_nodes_from(self.nx_nodes)
        G.add_edges_from(self.nx_edges)
        return G

    def cytoscape(self):
        nodes = [{"data": {"id": str(f.guid), "label": f.name}, "style": {
                  "background-color": Colors.MANDATORY.value if f.is_mandatory else Colors.OPTIONAL.value
                }}
                 for f in self.features]
        edges = [{"data": {"source": str(f.guid), "target": str(r.guid), "label": str(r.rel.value)}, "style": {
                #   "mid-target-arrow-color": "red",
                #   "mid-target-arrow-shape": "vee",
                  "line-color": Colors.ALTERNATIVE.value if r.rel == RelationshipTypes.ALTERNATIVE else Colors.DEFAULT.value,
                  'opacity': 0.9,
                #   'z-index': 5000,
                  'label': 'data(label)',
                  "text-wrap": "wrap"
                 }}
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
