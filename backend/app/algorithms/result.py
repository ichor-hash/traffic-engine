"""
Shared result type returned by all shortest-path algorithms.

Keeps algorithm implementations focused on logic rather than output formatting.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PathResult:
    """
    Outcome of a shortest-path computation.

    Attributes:
        path:           Ordered list of node IDs from source → destination.
                        Empty if no path exists.
        total_cost:     Sum of current_weight along the path.
                        ``float('inf')`` when unreachable.
        nodes_visited:  Number of unique nodes popped from the priority queue.
        relaxations:    Number of edge relaxations performed.
        runtime_ms:     Wall-clock time of the algorithm in milliseconds.
        algorithm:      Name identifier (``"dijkstra"`` or ``"astar"``).
    """

    path: list[str] = field(default_factory=list)
    total_cost: float = float("inf")
    nodes_visited: int = 0
    relaxations: int = 0
    runtime_ms: float = 0.0
    algorithm: str = ""

    @property
    def found(self) -> bool:
        """``True`` if a valid path was discovered."""
        return len(self.path) > 0

    def to_dict(self) -> dict:
        """JSON-serialisable representation."""
        cost = self.total_cost
        if cost == float("inf"):
            cost = None  # JSON doesn't support Infinity
        return {
            "path": self.path,
            "total_cost": cost,
            "nodes_visited": self.nodes_visited,
            "relaxations": self.relaxations,
            "runtime_ms": round(self.runtime_ms, 4),
            "algorithm": self.algorithm,
            "found": self.found,
        }
