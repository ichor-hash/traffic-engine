"""
Greedy (Naive) Ambulance Dispatch Algorithm.

Strategy: assign the single nearest available ambulance to an emergency,
and send the patient to the nearest hospital.

Complexity
──────────
Time:  O(A × (V+E) log V)  — runs Dijkstra once from the emergency,
       then scans ambulances and hospitals linearly.
Space: O(V)                — Dijkstra distance array.

This is the BASELINE method for comparison against the optimised Hungarian
algorithm dispatch.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from app.algorithms.dijkstra import dijkstra
from app.algorithms.astar import astar
from .models import Ambulance, AmbulanceStatus, Hospital, Emergency, DispatchResult

if TYPE_CHECKING:
    from app.graph.graph import Graph


def greedy_dispatch(
    graph: "Graph",
    emergency: Emergency,
    ambulances: list[Ambulance],
    hospitals: list[Hospital],
    use_astar: bool = False,
) -> DispatchResult | None:
    """
    Assign the nearest available ambulance and nearest hospital.

    Args:
        graph:      The traffic graph.
        emergency:  The emergency to respond to.
        ambulances: All ambulances in the fleet.
        hospitals:  All hospitals.
        use_astar:  If True, use A* instead of Dijkstra.

    Returns:
        A DispatchResult, or None if no ambulance is available.

    Time complexity: O(A × (V+E) log V) worst case.
    """
    available = [a for a in ambulances if a.status == AmbulanceStatus.AVAILABLE]
    if not available:
        return None

    algo_fn = astar if use_astar else dijkstra
    algo_name = "greedy_astar" if use_astar else "greedy_dijkstra"

    t_start = time.perf_counter()

    # Find nearest ambulance by computing shortest path from each to emergency
    best_amb: Ambulance | None = None
    best_amb_result = None
    best_amb_cost = float("inf")

    for amb in available:
        try:
            result = algo_fn(graph, amb.location, emergency.location)
            if result.found and result.total_cost < best_amb_cost:
                best_amb_cost = result.total_cost
                best_amb = amb
                best_amb_result = result
        except ValueError:
            continue

    if best_amb is None or best_amb_result is None:
        return None

    # Find nearest hospital from the emergency location
    best_hosp: Hospital | None = None
    best_hosp_result = None
    best_hosp_cost = float("inf")

    for hosp in hospitals:
        if hosp.available_beds <= 0:
            continue
        try:
            result = algo_fn(graph, emergency.location, hosp.location)
            if result.found and result.total_cost < best_hosp_cost:
                best_hosp_cost = result.total_cost
                best_hosp = hosp
                best_hosp_result = result
        except ValueError:
            continue

    if best_hosp is None or best_hosp_result is None:
        return None

    t_end = time.perf_counter()
    algorithm_ms = (t_end - t_start) * 1000

    total_visited = best_amb_result.nodes_visited + best_hosp_result.nodes_visited

    return DispatchResult(
        emergency_id=emergency.id,
        ambulance_id=best_amb.id,
        hospital_id=best_hosp.id,
        algorithm=algo_name,
        path_to_emergency=best_amb_result.path,
        path_to_hospital=best_hosp_result.path,
        response_time=best_amb_cost,
        transport_time=best_hosp_cost,
        total_time=best_amb_cost + best_hosp_cost,
        nodes_visited=total_visited,
        algorithm_ms=algorithm_ms,
    )
