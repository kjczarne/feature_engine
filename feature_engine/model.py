"""
Data model for the Feature Engine.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from enum import Enum, auto

from ruamel import yaml
from functools import reduce
import networkx as nx


class BindingTime(Enum):
    COMPILATION = "compilation"
    INITIALIZATION = "initialization"
    RUNTIME = "runtime"


class RelationshipTypes(Enum):
    ALTERNATIVE = "alternative"


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
    incompatible_with: List[Feature] = field(default_factory=list)
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
            [Feature.from_dict(f) for f in d["incompatible_with"]],
            [Relationship(r["guid"], RelationshipTypes(r["rel"])) for r in d["relationships"]],
        )


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
    
    def to_nx_graph(self) -> nx.Graph:
        G = nx.Graph()
        G.add_nodes_from([
            (f.guid, {k: v for k, v in f.__dict__.items() if k != "guid"})
            for f in self.features
        ])

        G.add_edges_from(reduce(lambda x, y: x + y, [
            [ (f.guid, r) for r in f.relationship_guids]
            for f in self.features
        ]))
        return G
