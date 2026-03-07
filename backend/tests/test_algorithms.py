"""
Unit tests for Dijkstra and A* shortest-path algorithms (Phase 2).

Covers:
  • Correct shortest path on a known graph
  • Both algorithms agree on optimal cost
  • A* visits fewer or equal nodes compared to Dijkstra
  • Unreachable destination returns empty path
  • Source == destination edge case
  • Invalid node raises ValueError
  • Metrics (nodes_visited, relaxations, runtime_ms) are populated
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from app.graph.models import Edge, EdgeStatus, Node
from app.graph.graph import Graph
from app.algorithms.dijkstra import dijkstra
from app.algorithms.astar import astar
from app.algorithms.result import PathResult


# ── Fixtures ──────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def diamond_graph() -> Graph:
    """
    Diamond-shaped graph:

        A --1-- B
        |       |
        2       1
        |       |
        D --1-- C

    Shortest A→C: A → B → C  (cost 2)
    Alternative:  A → D → C  (cost 3)
    """
    g = Graph()
    g.add_node(Node("A", 0.0, 0.0))
    g.add_node(Node("B", 1.0, 0.0))
    g.add_node(Node("C", 1.0, 1.0))
    g.add_node(Node("D", 0.0, 1.0))

    # Bidirectional edges
    g.add_edge(Edge("A", "B", base_weight=1.0))
    g.add_edge(Edge("B", "A", base_weight=1.0))
    g.add_edge(Edge("B", "C", base_weight=1.0))
    g.add_edge(Edge("C", "B", base_weight=1.0))
    g.add_edge(Edge("A", "D", base_weight=2.0))
    g.add_edge(Edge("D", "A", base_weight=2.0))
    g.add_edge(Edge("D", "C", base_weight=1.0))
    g.add_edge(Edge("C", "D", base_weight=1.0))
    return g


@pytest.fixture
def linear_graph() -> Graph:
    """A → B → C → D, with increasing weights."""
    g = Graph()
    for nid, x in [("A", 0), ("B", 1), ("C", 2), ("D", 3)]:
        g.add_node(Node(nid, float(x), 0.0))
    g.add_edge(Edge("A", "B", base_weight=1.0))
    g.add_edge(Edge("B", "C", base_weight=2.0))
    g.add_edge(Edge("C", "D", base_weight=3.0))
    return g


@pytest.fixture
def disconnected_graph() -> Graph:
    """Two components: {A, B} and {C, D}."""
    g = Graph()
    g.add_node(Node("A", 0.0, 0.0))
    g.add_node(Node("B", 1.0, 0.0))
    g.add_node(Node("C", 5.0, 5.0))
    g.add_node(Node("D", 6.0, 5.0))
    g.add_edge(Edge("A", "B", base_weight=1.0))
    g.add_edge(Edge("C", "D", base_weight=1.0))
    return g


@pytest.fixture
def json_graph() -> Graph:
    """Load graph from the small_graph.json fixture."""
    g = Graph()
    g.load_from_json(FIXTURES_DIR / "small_graph.json")
    return g


# ── Dijkstra tests ────────────────────────────────────────────────────────


class TestDijkstra:

    def test_shortest_path_diamond(self, diamond_graph: Graph) -> None:
        result = dijkstra(diamond_graph, "A", "C")
        assert result.found
        assert result.path == ["A", "B", "C"]
        assert result.total_cost == pytest.approx(2.0)
        assert result.algorithm == "dijkstra"

    def test_linear_path(self, linear_graph: Graph) -> None:
        result = dijkstra(linear_graph, "A", "D")
        assert result.found
        assert result.path == ["A", "B", "C", "D"]
        assert result.total_cost == pytest.approx(6.0)

    def test_same_source_destination(self, diamond_graph: Graph) -> None:
        result = dijkstra(diamond_graph, "A", "A")
        assert result.found
        assert result.path == ["A"]
        assert result.total_cost == pytest.approx(0.0)

    def test_unreachable(self, disconnected_graph: Graph) -> None:
        result = dijkstra(disconnected_graph, "A", "C")
        assert not result.found
        assert result.path == []
        assert result.total_cost == float("inf")

    def test_invalid_source_raises(self, diamond_graph: Graph) -> None:
        with pytest.raises(ValueError, match="Source node"):
            dijkstra(diamond_graph, "Z", "A")

    def test_invalid_dest_raises(self, diamond_graph: Graph) -> None:
        with pytest.raises(ValueError, match="Destination node"):
            dijkstra(diamond_graph, "A", "Z")

    def test_metrics_populated(self, diamond_graph: Graph) -> None:
        result = dijkstra(diamond_graph, "A", "C")
        assert result.nodes_visited > 0
        assert result.relaxations > 0
        assert result.runtime_ms >= 0.0

    def test_on_json_fixture(self, json_graph: Graph) -> None:
        result = dijkstra(json_graph, "A", "C")
        assert result.found
        assert result.total_cost < float("inf")


# ── A* tests ──────────────────────────────────────────────────────────────


class TestAStar:

    def test_shortest_path_diamond(self, diamond_graph: Graph) -> None:
        result = astar(diamond_graph, "A", "C")
        assert result.found
        assert result.path == ["A", "B", "C"]
        assert result.total_cost == pytest.approx(2.0)
        assert result.algorithm == "astar"

    def test_linear_path(self, linear_graph: Graph) -> None:
        result = astar(linear_graph, "A", "D")
        assert result.found
        assert result.path == ["A", "B", "C", "D"]
        assert result.total_cost == pytest.approx(6.0)

    def test_same_source_destination(self, diamond_graph: Graph) -> None:
        result = astar(diamond_graph, "A", "A")
        assert result.found
        assert result.path == ["A"]
        assert result.total_cost == pytest.approx(0.0)

    def test_unreachable(self, disconnected_graph: Graph) -> None:
        result = astar(disconnected_graph, "A", "C")
        assert not result.found
        assert result.path == []
        assert result.total_cost == float("inf")

    def test_invalid_source_raises(self, diamond_graph: Graph) -> None:
        with pytest.raises(ValueError, match="Source node"):
            astar(diamond_graph, "Z", "A")

    def test_invalid_dest_raises(self, diamond_graph: Graph) -> None:
        with pytest.raises(ValueError, match="Destination node"):
            astar(diamond_graph, "A", "Z")

    def test_metrics_populated(self, diamond_graph: Graph) -> None:
        result = astar(diamond_graph, "A", "C")
        assert result.nodes_visited > 0
        assert result.relaxations > 0
        assert result.runtime_ms >= 0.0


# ── Cross-algorithm agreement ─────────────────────────────────────────────


class TestAlgorithmAgreement:
    """Both algorithms must agree on the optimal cost."""

    def test_same_cost_diamond(self, diamond_graph: Graph) -> None:
        d_result = dijkstra(diamond_graph, "A", "C")
        a_result = astar(diamond_graph, "A", "C")
        assert d_result.total_cost == pytest.approx(a_result.total_cost)

    def test_same_cost_linear(self, linear_graph: Graph) -> None:
        d_result = dijkstra(linear_graph, "A", "D")
        a_result = astar(linear_graph, "A", "D")
        assert d_result.total_cost == pytest.approx(a_result.total_cost)

    def test_astar_visits_leq_dijkstra(self, diamond_graph: Graph) -> None:
        """A* should visit ≤ the number of nodes Dijkstra visits."""
        d_result = dijkstra(diamond_graph, "A", "C")
        a_result = astar(diamond_graph, "A", "C")
        assert a_result.nodes_visited <= d_result.nodes_visited

    def test_same_cost_json_fixture(self, json_graph: Graph) -> None:
        d_result = dijkstra(json_graph, "A", "C")
        a_result = astar(json_graph, "A", "C")
        assert d_result.total_cost == pytest.approx(a_result.total_cost)


# ── PathResult tests ──────────────────────────────────────────────────────


class TestPathResult:

    def test_found_with_path(self) -> None:
        r = PathResult(path=["A", "B"], total_cost=5.0, algorithm="test")
        assert r.found is True

    def test_not_found_empty(self) -> None:
        r = PathResult()
        assert r.found is False

    def test_to_dict(self) -> None:
        r = PathResult(
            path=["A", "B"],
            total_cost=5.0,
            nodes_visited=3,
            relaxations=4,
            runtime_ms=1.2345,
            algorithm="dijkstra",
        )
        d = r.to_dict()
        assert d["path"] == ["A", "B"]
        assert d["found"] is True
        assert d["runtime_ms"] == 1.2345
