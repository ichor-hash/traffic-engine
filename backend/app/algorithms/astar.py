"""
A* shortest-path algorithm — manual implementation.

Uses Python's ``heapq`` as a min-priority queue and Euclidean distance
as the heuristic function.

Heuristic admissibility
───────────────────────
The Euclidean (straight-line) distance between two points never
overestimates the true shortest-path cost on a road network where
edge weights are ≥ the geometric distance.  This guarantees optimality.

Complexity
──────────
Time:  O((V + E) log V)  — same worst-case as Dijkstra, but in practice
       A* visits fewer nodes due to the heuristic guiding search toward
       the goal.
Space: O(V)              — distance, predecessor, and f-score arrays.
"""

from __future__ import annotations

import heapq
import math
import time
from typing import TYPE_CHECKING

from .result import PathResult

if TYPE_CHECKING:
    from app.graph.graph import Graph
    from app.graph.models import Node


def _haversine(a: "Node", b: "Node") -> float:
    """
    Compute Haversine (Great-Circle) distance between two lat/lon points in meters.
    
    Used as the admissible heuristic h(n) for A*. Because our edge weights
    are in meters, returning proper meters instead of Euclidean degrees
    makes A* orders of magnitude faster while remaining optimal.

    a.x = lon, a.y = lat
    b.x = lon, b.y = lat
    """
    R = 6371000.0  # Earth radius in meters
    
    lat1_rad = math.radians(a.y)
    lat2_rad = math.radians(b.y)
    dlat = math.radians(b.y - a.y)
    dlon = math.radians(b.x - a.x)

    a_val = (math.sin(dlat / 2) ** 2) + math.cos(lat1_rad) * math.cos(lat2_rad) * (math.sin(dlon / 2) ** 2)
    c_val = 2 * math.atan2(math.sqrt(a_val), math.sqrt(1 - a_val))

    return R * c_val


def astar(graph: "Graph", source: str, destination: str) -> PathResult:
    """
    Compute the shortest path from *source* to *destination* using the
    A* algorithm with Euclidean distance heuristic.

    Args:
        graph:       The traffic graph (uses ``current_weight`` on edges).
        source:      ID of the start node.
        destination: ID of the goal node.

    Returns:
        A :class:`PathResult` with path, cost, metrics, and timing.

    Raises:
        ValueError: If *source* or *destination* is not in the graph.

    Complexity:
        Time:  O((V + E) log V)  — worst-case identical to Dijkstra
        Space: O(V)
    """
    if source not in graph:
        raise ValueError(f"Source node '{source}' not in graph.")
    if destination not in graph:
        raise ValueError(f"Destination node '{destination}' not in graph.")

    goal_node = graph.get_node(destination)
    assert goal_node is not None  # guaranteed by the check above

    # ── Initialisation ────────────────────────────────────────────────
    start_time = time.perf_counter()

    g_score: dict[str, float] = {source: 0.0}  # best known cost from source
    prev: dict[str, str | None] = {source: None}
    visited: set[str] = set()
    nodes_visited = 0
    relaxations = 0

    # Compute initial heuristic
    source_node = graph.get_node(source)
    assert source_node is not None
    h_start = _haversine(source_node, goal_node)

    # Min-heap entries: (f_score, node_id)
    # f(n) = g(n) + h(n)
    heap: list[tuple[float, str]] = [(h_start, source)]

    # ── Main loop ─────────────────────────────────────────────────────
    while heap:
        # Extract node with lowest f-score  — O(log V)
        f_u, u = heapq.heappop(heap)

        # Lazy deletion: skip already-settled nodes
        if u in visited:
            continue

        visited.add(u)
        nodes_visited += 1

        # Early exit when destination is settled — A* guarantees optimality
        # at first extraction when heuristic is admissible.
        if u == destination:
            break

        g_u = g_score[u]

        # Relax all outgoing edges  — O(degree(u))
        for edge in graph.get_neighbors(u):
            v = edge.to_node

            if v in visited:
                continue

            tentative_g = g_u + edge.current_weight

            # Only update if we found a cheaper path to v
            if tentative_g < g_score.get(v, float("inf")):
                g_score[v] = tentative_g
                prev[v] = u

                # Compute f(v) = g(v) + h(v)
                v_node = graph.get_node(v)
                assert v_node is not None
                h_v = _haversine(v_node, goal_node)
                f_v = tentative_g + h_v

                heapq.heappush(heap, (f_v, v))
                relaxations += 1

    # ── Reconstruct path ──────────────────────────────────────────────
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    if destination not in visited:
        return PathResult(
            path=[],
            total_cost=float("inf"),
            nodes_visited=nodes_visited,
            relaxations=relaxations,
            runtime_ms=elapsed_ms,
            algorithm="astar",
        )

    path: list[str] = []
    node: str | None = destination
    while node is not None:
        path.append(node)
        node = prev.get(node)
    path.reverse()

    return PathResult(
        path=path,
        total_cost=g_score[destination],
        nodes_visited=nodes_visited,
        relaxations=relaxations,
        runtime_ms=elapsed_ms,
        algorithm="astar",
    )
