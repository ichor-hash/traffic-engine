"""
Unit tests for the Routing Service (Phase 5).

Covers:
  • compute_route with Dijkstra and A*
  • Active path tracking
  • compare_algorithms returns both results
  • Recompute triggered only when affected edges change
  • Recompute ignored when unrelated edges change
  • Invalid algorithm raises ValueError
  • Route update callbacks fire on recompute
"""

from __future__ import annotations

import pytest

from app.graph.models import Edge, EdgeStatus, Node
from app.graph.graph import Graph
from app.services.routing_service import RoutingService


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def grid_graph() -> Graph:
    """
    Simple 2×2 grid:

        A —1— B
        |     |
        2     1
        |     |
        C —1— D

    Shortest A→D: A→B→D (cost 2)
    """
    g = Graph()
    g.add_node(Node("A", 0.0, 0.0))
    g.add_node(Node("B", 1.0, 0.0))
    g.add_node(Node("C", 0.0, 1.0))
    g.add_node(Node("D", 1.0, 1.0))
    g.add_edge(Edge("A", "B", base_weight=1.0))
    g.add_edge(Edge("B", "D", base_weight=1.0))
    g.add_edge(Edge("A", "C", base_weight=2.0))
    g.add_edge(Edge("C", "D", base_weight=1.0))
    return g


# ── Tests ─────────────────────────────────────────────────────────────────


class TestRoutingService:

    def test_compute_route_dijkstra(self, grid_graph: Graph) -> None:
        svc = RoutingService(grid_graph)
        result = svc.compute_route("A", "D", "dijkstra")
        assert result.found
        assert result.path == ["A", "B", "D"]
        assert result.total_cost == pytest.approx(2.0)

    def test_compute_route_astar(self, grid_graph: Graph) -> None:
        svc = RoutingService(grid_graph)
        result = svc.compute_route("A", "D", "astar")
        assert result.found
        assert result.path == ["A", "B", "D"]
        assert result.total_cost == pytest.approx(2.0)

    def test_active_path_set_after_compute(self, grid_graph: Graph) -> None:
        svc = RoutingService(grid_graph)
        svc.compute_route("A", "D", "dijkstra")
        assert svc.active_path == ["A", "B", "D"]
        assert svc.active_result is not None
        assert svc.active_result.algorithm == "dijkstra"

    def test_active_path_empty_initially(self, grid_graph: Graph) -> None:
        svc = RoutingService(grid_graph)
        assert svc.active_path == []
        assert svc.active_result is None

    def test_invalid_algorithm_raises(self, grid_graph: Graph) -> None:
        svc = RoutingService(grid_graph)
        with pytest.raises(ValueError, match="Unknown algorithm"):
            svc.compute_route("A", "D", "bellman_ford")  # type: ignore

    def test_compare_algorithms(self, grid_graph: Graph) -> None:
        svc = RoutingService(grid_graph)
        results = svc.compare_algorithms("A", "D")
        assert "dijkstra" in results
        assert "astar" in results
        assert results["dijkstra"].total_cost == pytest.approx(results["astar"].total_cost)

    def test_recompute_returns_new_result(self, grid_graph: Graph) -> None:
        svc = RoutingService(grid_graph)
        svc.compute_route("A", "D", "dijkstra")

        # Congest the A→B edge
        edge = grid_graph.get_edge("A", "B")
        assert edge is not None
        edge.current_weight = 10.0
        edge.status = EdgeStatus.CONGESTED

        result = svc.recompute()
        assert result is not None
        assert result.found
        # Now A→C→D (cost 3) should be cheaper than A→B→D (cost 11)
        assert result.path == ["A", "C", "D"]
        assert result.total_cost == pytest.approx(3.0)

    def test_recompute_without_active_route(self, grid_graph: Graph) -> None:
        svc = RoutingService(grid_graph)
        assert svc.recompute() is None

    def test_traffic_change_triggers_recompute(self, grid_graph: Graph) -> None:
        svc = RoutingService(grid_graph)
        svc.compute_route("A", "D", "dijkstra")
        assert svc.active_path == ["A", "B", "D"]

        # Congest A→B (which IS on the active path)
        edge = grid_graph.get_edge("A", "B")
        assert edge is not None
        edge.current_weight = 10.0
        edge.status = EdgeStatus.CONGESTED

        # Simulate traffic engine callback
        changes = [{"from_node": "A", "to_node": "B", "old_weight": 1.0, "new_weight": 10.0, "status": "congested"}]
        svc.on_traffic_change(changes)

        # Path should have been recomputed to go through C
        assert svc.active_path == ["A", "C", "D"]

    def test_traffic_change_ignored_when_unrelated(self, grid_graph: Graph) -> None:
        svc = RoutingService(grid_graph)
        svc.compute_route("A", "D", "dijkstra")
        original_path = svc.active_path[:]

        # Change edge A→C (NOT on the active path A→B→D)
        changes = [{"from_node": "A", "to_node": "C", "old_weight": 2.0, "new_weight": 5.0, "status": "congested"}]
        svc.on_traffic_change(changes)

        # Path should NOT have been recomputed
        assert svc.active_path == original_path

    def test_route_update_callback_fires(self, grid_graph: Graph) -> None:
        svc = RoutingService(grid_graph)
        received: list[tuple] = []
        svc.on_route_update(lambda result, reason: received.append((result, reason)))

        svc.compute_route("A", "D", "dijkstra")
        svc.recompute()

        assert len(received) == 1
        assert received[0][1] == "recomputed"
        assert received[0][0].found
