"""
Core data models for the traffic simulation graph.

This module defines the fundamental building blocks — Node and Edge — used
to represent a city road network as a weighted directed graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class EdgeStatus(str, Enum):
    """
    Possible states of a road segment.

    Attributes:
        NORMAL:    Free-flowing traffic.
        CONGESTED: Elevated travel time (weight multiplied by 1.5–3×).
        BLOCKED:   Road completely impassable (weight = ∞).
    """

    NORMAL = "normal"
    CONGESTED = "congested"
    BLOCKED = "blocked"


@dataclass(slots=True)
class Node:
    """
    A single intersection / waypoint on the map.

    Attributes:
        id: Unique string identifier (typically the OSM node ID).
        x:  Longitude or projected x-coordinate.
        y:  Latitude  or projected y-coordinate.

    Space complexity: O(1) per node.
    """

    id: str
    x: float
    y: float
    label: str = ""

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self.id == other.id


@dataclass(slots=True)
class Edge:
    """
    A directed road segment connecting two nodes.

    Attributes:
        from_node:      ID of the source node.
        to_node:        ID of the destination node.
        base_weight:    Static travel cost (derived from road length / speed limit).
        current_weight: Dynamic travel cost — mutated by the traffic simulation.
        status:         Current traffic condition on this edge.

    Invariants:
        • base_weight > 0
        • current_weight >= base_weight  (except during recovery it may equal base_weight)
        • When status == BLOCKED, current_weight should be treated as infinity.

    Space complexity: O(1) per edge.
    """

    from_node: str
    to_node: str
    base_weight: float
    current_weight: float = 0.0  # default sentinel — set in __post_init__
    status: EdgeStatus = EdgeStatus.NORMAL

    def __post_init__(self) -> None:
        """Default current_weight to base_weight when not explicitly provided."""
        if self.current_weight == 0.0:
            self.current_weight = self.base_weight
