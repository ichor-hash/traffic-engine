"""
Routing Service — orchestrates pathfinding and traffic-aware recomputation.

This service acts as the glue between the graph, the shortest-path
algorithms, and the traffic simulation engine.

Responsibilities
────────────────
1. Accept (source, destination, algorithm) and compute a route.
2. Store the currently active path.
3. When notified of edge changes by the TrafficEngine, check whether
   any changed edge lies on the active path.  If so → recompute.
4. Expose the latest ``PathResult`` (and comparison results in
   Performance Mode).

Design
──────
• Stateful — holds the active route so the API layer can query it.
• The ``on_traffic_change`` method is designed to be passed as a
  callback to ``TrafficEngine.on_change()``.
• Thread-safe: the active path is protected by a ``threading.Lock``.
"""

from __future__ import annotations

import threading
from typing import Callable, Literal, TYPE_CHECKING

from app.algorithms.dijkstra import dijkstra
from app.algorithms.astar import astar
from app.algorithms.result import PathResult

if TYPE_CHECKING:
    from app.graph.graph import Graph

Algorithm = Literal["dijkstra", "astar"]

# Callback signature: (PathResult, reason: str) → None
RouteUpdateCallback = Callable[[PathResult, str], None]


class RoutingService:
    """
    Central routing coordinator.

    Usage::

        svc = RoutingService(graph)
        result = svc.compute_route("1", "25", "dijkstra")
        engine.on_change(svc.on_traffic_change)   # wire to TrafficEngine
    """

    _ALGORITHMS = {
        "dijkstra": dijkstra,
        "astar": astar,
    }

    def __init__(self, graph: "Graph") -> None:
        self._graph = graph
        self._lock = threading.Lock()

        # Active route state
        self._source: str | None = None
        self._destination: str | None = None
        self._algorithm: Algorithm = "dijkstra"
        self._active_result: PathResult | None = None
        self._active_path_edges: set[tuple[str, str]] = set()

        # Listeners
        self._update_callbacks: list[RouteUpdateCallback] = []

    # ── Public API ────────────────────────────────────────────────────

    def on_route_update(self, callback: RouteUpdateCallback) -> None:
        """Register a callback for route recomputations."""
        self._update_callbacks.append(callback)

    def compute_route(
        self,
        source: str,
        destination: str,
        algorithm: Algorithm = "dijkstra",
    ) -> PathResult:
        """
        Compute a new route and set it as the active path.

        Args:
            source:      Start node ID.
            destination: Goal node ID.
            algorithm:   ``"dijkstra"`` or ``"astar"``.

        Returns:
            The computed :class:`PathResult`.

        Raises:
            ValueError: If the algorithm name is invalid.

        Time complexity: O((V + E) log V) — delegated to the algorithm.
        """
        if algorithm not in self._ALGORITHMS:
            raise ValueError(
                f"Unknown algorithm '{algorithm}'. "
                f"Choose from: {list(self._ALGORITHMS.keys())}"
            )

        algo_fn = self._ALGORITHMS[algorithm]
        result = algo_fn(self._graph, source, destination)

        with self._lock:
            self._source = source
            self._destination = destination
            self._algorithm = algorithm
            self._active_result = result
            self._active_path_edges = self._path_to_edge_set(result.path)

        return result

    def compare_algorithms(
        self,
        source: str,
        destination: str,
    ) -> dict[str, PathResult]:
        """
        Run both Dijkstra and A* and return results side-by-side.

        Used by the Performance Mode feature.

        Returns:
            ``{"dijkstra": ..., "astar": ...}``
        """
        return {
            "dijkstra": dijkstra(self._graph, source, destination),
            "astar": astar(self._graph, source, destination),
        }

    def recompute(self) -> PathResult | None:
        """
        Re-run the current algorithm on the current source/destination.

        Returns ``None`` if no active route is set.
        """
        with self._lock:
            if self._source is None or self._destination is None:
                return None
            source = self._source
            destination = self._destination
            algorithm = self._algorithm

        result = self.compute_route(source, destination, algorithm)

        # Notify listeners
        for cb in self._update_callbacks:
            cb(result, "recomputed")

        return result

    @property
    def active_result(self) -> PathResult | None:
        """The most recent routing result (thread-safe read)."""
        with self._lock:
            return self._active_result

    @property
    def active_path(self) -> list[str]:
        """Node IDs of the active path, or empty list."""
        with self._lock:
            if self._active_result is None:
                return []
            return list(self._active_result.path)

    # ── Traffic callback ──────────────────────────────────────────────

    def on_traffic_change(self, changes: list[dict]) -> None:
        """
        Callback for ``TrafficEngine.on_change()``.

        Checks whether any changed edge intersects the active path.
        If yes → triggers ``recompute()``.
        If no  → ignores (no unnecessary work).

        Time complexity: O(len(changes)) — set lookup is O(1) per edge.
        """
        with self._lock:
            if not self._active_path_edges:
                return  # no active route
            path_edges = self._active_path_edges

        # Check if any changed edge is on the active path
        for change in changes:
            edge_key = (change["from_node"], change["to_node"])
            if edge_key in path_edges:
                self.recompute()
                return  # one recompute is enough

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _path_to_edge_set(path: list[str]) -> set[tuple[str, str]]:
        """
        Convert a node path to a set of (from, to) edge tuples
        for O(1) membership testing.

        Time complexity: O(len(path)).
        """
        edges: set[tuple[str, str]] = set()
        for i in range(len(path) - 1):
            edges.add((path[i], path[i + 1]))
        return edges
