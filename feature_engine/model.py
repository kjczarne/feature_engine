"""
Data model for the Feature Engine.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from enum import Enum, auto

from ruamel import yaml
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
class DirectionalRelationship:
    """
    A relationship between two features with explicit relationship direction.
    """
    guid: str
    rel: RelationshipTypes
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


@dataclass
class FeatureContainer:
    
    features: List[Feature] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str) -> FeatureContainer:
        """
        Creates a FeatureContainer from a YAML file.
        """
        with open(path, "r") as f:
            return cls(**yaml.load(f, Loader=yaml.Loader))
    
    def to_yaml(self, path: str) -> None:
        """
        Writes a FeatureContainer to a YAML file.
        """
        with open(path, "w") as f:
            yaml.dump(self, f)
    
    def to_nx_graph(self) -> nx.Graph:
        pass
