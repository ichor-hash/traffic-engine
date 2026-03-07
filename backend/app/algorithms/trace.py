"""
Trace-collecting variants of Dijkstra and A*.

Returns a list of exploration steps alongside the final PathResult,
allowing the frontend to animate the algorithm step-by-step.
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


def _euclidean(a: "Node", b: "Node") -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def dijkstra_trace(
    graph: "Graph", source: str, destination: str
) -> tuple[PathResult, list[dict]]:
    """
    Dijkstra with full exploration trace.

    Returns (PathResult, trace_steps) where each step is one of:
      {"type": "visit",  "node": str, "cost": float}
      {"type": "relax",  "from": str, "to": str, "cost": float}
      {"type": "path",   "path": list[str]}
    """
    if source not in graph:
        raise ValueError(f"Source node '{source}' not in graph.")
    if destination not in graph:
        raise ValueError(f"Destination node '{destination}' not in graph.")

    start_time = time.perf_counter()
    trace: list[dict] = []

    dist: dict[str, float] = {source: 0.0}
    prev: dict[str, str | None] = {source: None}
    visited: set[str] = set()
    nodes_visited = 0
    relaxations = 0

    heap: list[tuple[float, str]] = [(0.0, source)]

    while heap:
        d_u, u = heapq.heappop(heap)
        if u in visited:
            continue

        visited.add(u)
        nodes_visited += 1
        trace.append({"type": "visit", "node": u, "cost": round(d_u, 2)})

        if u == destination:
            break

        for edge in graph.get_neighbors(u):
            v = edge.to_node
            if v in visited:
                continue
            new_dist = d_u + edge.current_weight
            if new_dist < dist.get(v, float("inf")):
                dist[v] = new_dist
                prev[v] = u
                heapq.heappush(heap, (new_dist, v))
                relaxations += 1
                trace.append({
                    "type": "relax",
                    "from": u,
                    "to": v,
                    "cost": round(new_dist, 2),
                })

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    if destination not in visited:
        return PathResult(
            path=[], total_cost=float("inf"),
            nodes_visited=nodes_visited, relaxations=relaxations,
            runtime_ms=elapsed_ms, algorithm="dijkstra",
        ), trace

    path: list[str] = []
    node: str | None = destination
    while node is not None:
        path.append(node)
        node = prev.get(node)
    path.reverse()

    trace.append({"type": "path", "path": path})

    return PathResult(
        path=path, total_cost=dist[destination],
        nodes_visited=nodes_visited, relaxations=relaxations,
        runtime_ms=elapsed_ms, algorithm="dijkstra",
    ), trace


def astar_trace(
    graph: "Graph", source: str, destination: str
) -> tuple[PathResult, list[dict]]:
    """
    A* with full exploration trace.  Same step format as dijkstra_trace.
    """
    if source not in graph:
        raise ValueError(f"Source node '{source}' not in graph.")
    if destination not in graph:
        raise ValueError(f"Destination node '{destination}' not in graph.")

    goal_node = graph.get_node(destination)
    assert goal_node is not None

    start_time = time.perf_counter()
    trace: list[dict] = []

    g_score: dict[str, float] = {source: 0.0}
    prev: dict[str, str | None] = {source: None}
    visited: set[str] = set()
    nodes_visited = 0
    relaxations = 0

    source_node = graph.get_node(source)
    assert source_node is not None
    h_start = _euclidean(source_node, goal_node)
    heap: list[tuple[float, str]] = [(h_start, source)]

    while heap:
        f_u, u = heapq.heappop(heap)
        if u in visited:
            continue

        visited.add(u)
        nodes_visited += 1
        trace.append({"type": "visit", "node": u, "cost": round(g_score.get(u, 0), 2)})

        if u == destination:
            break

        g_u = g_score[u]
        for edge in graph.get_neighbors(u):
            v = edge.to_node
            if v in visited:
                continue
            tentative_g = g_u + edge.current_weight
            if tentative_g < g_score.get(v, float("inf")):
                g_score[v] = tentative_g
                prev[v] = u
                v_node = graph.get_node(v)
                assert v_node is not None
                h_v = _euclidean(v_node, goal_node)
                heapq.heappush(heap, (tentative_g + h_v, v))
                relaxations += 1
                trace.append({
                    "type": "relax",
                    "from": u,
                    "to": v,
                    "cost": round(tentative_g, 2),
                })

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    if destination not in visited:
        return PathResult(
            path=[], total_cost=float("inf"),
            nodes_visited=nodes_visited, relaxations=relaxations,
            runtime_ms=elapsed_ms, algorithm="astar",
        ), trace

    path: list[str] = []
    node: str | None = destination
    while node is not None:
        path.append(node)
        node = prev.get(node)
    path.reverse()

    trace.append({"type": "path", "path": path})

    return PathResult(
        path=path, total_cost=g_score[destination],
        nodes_visited=nodes_visited, relaxations=relaxations,
        runtime_ms=elapsed_ms, algorithm="astar",
    ), trace
