"""
Dijkstra's shortest-path algorithm — manual implementation.

Uses Python's ``heapq`` as a min-priority queue.
No external graph libraries are used.

Complexity
──────────
Time:  O((V + E) log V)  — each node extracted once from the heap (log V),
       each edge relaxed at most once (constant + log V push).
Space: O(V)              — distance and predecessor arrays.
"""

from __future__ import annotations

import heapq
import time
from typing import TYPE_CHECKING

from .result import PathResult

if TYPE_CHECKING:
    from app.graph.graph import Graph


def dijkstra(graph: "Graph", source: str, destination: str) -> PathResult:
    """
    Compute the shortest path from *source* to *destination* using
    Dijkstra's algorithm with a binary-heap priority queue.

    Args:
        graph:       The traffic graph (uses ``current_weight`` on edges).
        source:      ID of the start node.
        destination: ID of the goal node.

    Returns:
        A :class:`PathResult` with path, cost, metrics, and timing.

    Raises:
        ValueError: If *source* or *destination* is not in the graph.

    Complexity:
        Time:  O((V + E) log V)
        Space: O(V)
    """
    if source not in graph:
        raise ValueError(f"Source node '{source}' not in graph.")
    if destination not in graph:
        raise ValueError(f"Destination node '{destination}' not in graph.")

    # ── Initialisation ────────────────────────────────────────────────
    start_time = time.perf_counter()

    dist: dict[str, float] = {source: 0.0}
    prev: dict[str, str | None] = {source: None}
    visited: set[str] = set()
    nodes_visited = 0
    relaxations = 0

    # Min-heap entries: (distance, node_id)
    # Using a counter as tie-breaker is unnecessary — node IDs are unique strings.
    heap: list[tuple[float, str]] = [(0.0, source)]

    # ── Main loop ─────────────────────────────────────────────────────
    while heap:
        # Extract the node with smallest tentative distance  — O(log V)
        d_u, u = heapq.heappop(heap)

        # Lazy deletion: skip if we already found a shorter path
        if u in visited:
            continue

        visited.add(u)
        nodes_visited += 1

        # Early exit when destination is settled
        if u == destination:
            break

        # Relax all outgoing edges  — O(degree(u))
        for edge in graph.get_neighbors(u):
            v = edge.to_node

            if v in visited:
                continue

            # Blocked edges are impassable
            new_dist = d_u + edge.current_weight

            # Relax  — O(log V) for heap push
            if new_dist < dist.get(v, float("inf")):
                dist[v] = new_dist
                prev[v] = u
                heapq.heappush(heap, (new_dist, v))
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
            algorithm="dijkstra",
        )

    path: list[str] = []
    node: str | None = destination
    while node is not None:
        path.append(node)
        node = prev.get(node)
    path.reverse()

    return PathResult(
        path=path,
        total_cost=dist[destination],
        nodes_visited=nodes_visited,
        relaxations=relaxations,
        runtime_ms=elapsed_ms,
        algorithm="dijkstra",
    )
