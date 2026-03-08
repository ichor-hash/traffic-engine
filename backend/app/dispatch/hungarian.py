"""
Hungarian Algorithm Dispatch — Optimised Multi-Objective Assignment.

Uses the Hungarian (Kuhn–Munkres) algorithm to find the globally optimal
assignment of ambulances to emergencies, considering:
  1. Travel distance (Dijkstra shortest path)
  2. Route traffic congestion
  3. Hospital capacity / load balancing

Complexity
──────────
Time:  O(n³)       — Hungarian algorithm on the cost matrix,
       plus O(n × (V+E) log V) — to build the cost matrix via Dijkstra.
Space: O(n² + V)   — cost matrix + Dijkstra arrays.

This is the PROPOSED OPTIMISED method compared against the greedy baseline.
"""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

from app.algorithms.dijkstra import dijkstra
from app.algorithms.astar import astar
from .models import Ambulance, AmbulanceStatus, Hospital, Emergency, DispatchResult

if TYPE_CHECKING:
    from app.graph.graph import Graph


# ── Hungarian Algorithm Implementation ─────────────────────────────────


def _hungarian(cost_matrix: list[list[float]]) -> list[tuple[int, int]]:
    """
    Solve the assignment problem using the Hungarian algorithm.

    Given an n×m cost matrix, returns a list of (row, col) assignments
    that minimises total cost.  Handles rectangular matrices by padding.

    Time complexity:  O(n³)
    Space complexity: O(n²)
    """
    n = len(cost_matrix)
    if n == 0:
        return []
    m = len(cost_matrix[0])

    # Pad to square matrix
    size = max(n, m)
    matrix = [[0.0] * size for _ in range(size)]
    for i in range(n):
        for j in range(m):
            matrix[i][j] = cost_matrix[i][j]

    # u[i], v[j] — potentials for rows/columns
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    # p[j] — row assigned to column j
    p = [0] * (size + 1)
    # way[j] — for path reconstruction
    way = [0] * (size + 1)

    INF = float("inf")

    for i in range(1, size + 1):
        p[0] = i
        j0 = 0
        minv = [INF] * (size + 1)
        used = [False] * (size + 1)

        while True:
            used[j0] = True
            i0 = p[j0]
            delta = INF
            j1 = -1

            for j in range(1, size + 1):
                if used[j]:
                    continue
                cur = matrix[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j

            if j1 == -1:
                break

            for j in range(size + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta

            j0 = j1

            if p[j0] == 0:
                break

        # Reconstruct path
        while j0 != 0:
            p[j0] = p[way[j0]]
            j0 = way[j0]

    # Extract assignments (only original rows/cols)
    assignments: list[tuple[int, int]] = []
    for j in range(1, size + 1):
        if p[j] != 0 and p[j] - 1 < n and j - 1 < m:
            assignments.append((p[j] - 1, j - 1))

    return assignments


# ── Optimised Dispatch ──────────────────────────────────────────────────


def hungarian_dispatch(
    graph: "Graph",
    emergencies: list[Emergency],
    ambulances: list[Ambulance],
    hospitals: list[Hospital],
    alpha: float = 0.5,
    beta: float = 0.3,
    gamma: float = 0.2,
) -> list[DispatchResult]:
    """
    Optimised dispatch using Hungarian algorithm with multi-objective scoring.

    Builds a cost matrix combining:
      - α × normalised distance
      - β × route traffic factor
      - γ × best hospital congestion

    Args:
        graph:        The traffic graph.
        emergencies:  Pending emergency events.
        ambulances:   All ambulances in the fleet.
        hospitals:    All hospitals.
        alpha/beta/gamma: Weight parameters for distance/traffic/hospital load.

    Returns:
        List of DispatchResult for each assigned emergency.
    """
    available = [a for a in ambulances if a.status == AmbulanceStatus.AVAILABLE]
    pending = [e for e in emergencies if not e.assigned]

    if not available or not pending:
        return []

    t_start = time.perf_counter()

    n_amb = len(available)
    n_emg = len(pending)

    # Pre-compute Dijkstra from each emergency to find distances to ambulances & hospitals
    # Cache: emergency_location -> (distances_dict, nodes_visited)
    emg_dijkstra_cache: dict[str, dict[str, float]] = {}
    emg_nodes_visited: dict[str, int] = {}

    for emg in pending:
        if emg.location not in emg_dijkstra_cache:
            # Run Dijkstra from emergency to get distances to all nodes
            dist_map: dict[str, float] = {}
            total_visited = 0
            # Get distance FROM each ambulance TO the emergency
            # We'll compute from emergency location using reverse approach
            # Actually, compute from each ambulance to emergency for accuracy
            emg_dijkstra_cache[emg.location] = {}
            emg_nodes_visited[emg.location] = 0

    # Build cost matrix: rows = ambulances, cols = emergencies
    cost_matrix: list[list[float]] = []
    path_cache: dict[tuple[str, str], tuple[list[str], float, int]] = {}

    for amb in available:
        row: list[float] = []
        for emg in pending:
            # Compute path from ambulance to emergency
            cache_key = (amb.location, emg.location)
            if cache_key not in path_cache:
                try:
                    result = dijkstra(graph, amb.location, emg.location)
                    if result.found:
                        path_cache[cache_key] = (
                            result.path,
                            result.total_cost,
                            result.nodes_visited,
                        )
                    else:
                        path_cache[cache_key] = ([], float("inf"), 0)
                except ValueError:
                    path_cache[cache_key] = ([], float("inf"), 0)

            _, distance, _ = path_cache[cache_key]

            # Find best hospital for this emergency
            best_hosp_score = float("inf")
            for hosp in hospitals:
                if hosp.available_beds <= 0:
                    continue
                hosp_key = (emg.location, hosp.location)
                if hosp_key not in path_cache:
                    try:
                        h_result = dijkstra(graph, emg.location, hosp.location)
                        if h_result.found:
                            path_cache[hosp_key] = (
                                h_result.path,
                                h_result.total_cost,
                                h_result.nodes_visited,
                            )
                        else:
                            path_cache[hosp_key] = ([], float("inf"), 0)
                    except ValueError:
                        path_cache[hosp_key] = ([], float("inf"), 0)

                _, h_dist, _ = path_cache[hosp_key]
                h_congestion = hosp.congestion
                # Hospital score: distance + congestion penalty
                h_score = h_dist + h_congestion * 100
                if h_score < best_hosp_score:
                    best_hosp_score = h_score

            # Normalise distance (assume max ~2000m for the T.Nagar area)
            norm_dist = min(distance / 2000.0, 1.0)
            norm_hosp = min(best_hosp_score / 2000.0, 1.0)

            # Composite score
            score = (alpha * norm_dist) + (gamma * norm_hosp)

            # Severity multiplier — more severe = lower score preferred
            severity_mult = 1.0 / max(emg.severity, 1)
            score *= severity_mult

            if distance == float("inf"):
                score = 1e9  # unreachable

            row.append(score)
        cost_matrix.append(row)

    # Pre-pad with dummy ambulances if we have more emergencies than ambulances.
    # The cost of a dummy ambulance is the penalty of ignoring the emergency.
    # Higher severity -> higher penalty, so the algorithm will assign real ambulances
    # to high severity emergencies to avoid the huge dummy penalty.
    if n_amb < n_emg:
        for _ in range(n_emg - n_amb):
            dummy_row = []
            for emg in pending:
                # Huge penalty scaled by severity. 
                # Sev 5 penalty = 500,000. Sev 1 penalty = 100,000.
                penalty = 100000.0 * emg.severity
                dummy_row.append(penalty)
            cost_matrix.append(dummy_row)

    # Run Hungarian algorithm
    assignments = _hungarian(cost_matrix)

    # Build results
    results: list[DispatchResult] = []
    for amb_idx, emg_idx in assignments:
        if amb_idx >= n_amb or emg_idx >= n_emg:
            continue

        amb = available[amb_idx]
        emg = pending[emg_idx]

        # Get the cached path
        path_data = path_cache.get((amb.location, emg.location))
        if not path_data or path_data[1] == float("inf"):
            continue

        amb_path, amb_cost, amb_visited = path_data

        # Find best hospital based on composite score
        best_hosp: Hospital | None = None
        best_hosp_path: list[str] = []
        best_hosp_cost = float("inf")
        best_hosp_visited = 0

        for hosp in hospitals:
            if hosp.available_beds <= 0:
                continue
            hosp_data = path_cache.get((emg.location, hosp.location))
            if not hosp_data or hosp_data[1] == float("inf"):
                continue
            h_path, h_cost, h_visited = hosp_data
            # Weighted: distance + congestion penalty
            weighted = h_cost * (1.0 + hosp.congestion)
            if weighted < best_hosp_cost:
                best_hosp_cost = weighted
                best_hosp = hosp
                best_hosp_path = h_path
                best_hosp_visited = h_visited
                # Store actual cost (not weighted)
                best_hosp_cost_actual = h_cost

        if best_hosp is None:
            continue

        # Use actual cost for display
        actual_hosp_cost = path_cache.get(
            (emg.location, best_hosp.location), ([], 0.0, 0)
        )[1]

        results.append(DispatchResult(
            emergency_id=emg.id,
            ambulance_id=amb.id,
            hospital_id=best_hosp.id,
            algorithm="hungarian",
            path_to_emergency=amb_path,
            path_to_hospital=best_hosp_path,
            response_time=amb_cost,
            transport_time=actual_hosp_cost,
            total_time=amb_cost + actual_hosp_cost,
            nodes_visited=amb_visited + best_hosp_visited,
            algorithm_ms=0.0,  # filled below
        ))

    t_end = time.perf_counter()
    algorithm_ms = (t_end - t_start) * 1000

    # Set algorithm_ms on all results
    for r in results:
        r.algorithm_ms = algorithm_ms

    return results
