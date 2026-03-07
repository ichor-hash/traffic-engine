"""
Unit tests for the graph data structure (Phase 1).

Covers:
  • Node / Edge creation and defaults
  • Graph add / query operations
  • JSON loading from fixture
  • Error handling for invalid operations
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.graph.models import Edge, EdgeStatus, Node
from app.graph.graph import Graph


# ── Fixtures ──────────────────────────────────────────────────────────────

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def empty_graph() -> Graph:
    """Return a fresh, empty graph."""
    return Graph()


@pytest.fixture
def sample_graph() -> Graph:
    """Build a small graph manually (no JSON)."""
    g = Graph()
    g.add_node(Node("1", 0.0, 0.0))
    g.add_node(Node("2", 1.0, 0.0))
    g.add_node(Node("3", 1.0, 1.0))
    g.add_edge(Edge(from_node="1", to_node="2", base_weight=5.0))
    g.add_edge(Edge(from_node="2", to_node="3", base_weight=3.0))
    g.add_edge(Edge(from_node="1", to_node="3", base_weight=10.0))
    return g


# ── Node tests ────────────────────────────────────────────────────────────


class TestNode:
    def test_creation(self) -> None:
        n = Node("A", 80.27, 13.08)
        assert n.id == "A"
        assert n.x == 80.27
        assert n.y == 13.08

    def test_equality_by_id(self) -> None:
        assert Node("X", 0, 0) == Node("X", 99, 99)

    def test_hash_by_id(self) -> None:
        assert hash(Node("Y", 0, 0)) == hash(Node("Y", 5, 5))


# ── Edge tests ────────────────────────────────────────────────────────────


class TestEdge:
    def test_default_current_weight(self) -> None:
        e = Edge(from_node="A", to_node="B", base_weight=4.0)
        assert e.current_weight == 4.0  # defaults to base_weight

    def test_explicit_current_weight(self) -> None:
        e = Edge(from_node="A", to_node="B", base_weight=4.0, current_weight=8.0)
        assert e.current_weight == 8.0

    def test_default_status(self) -> None:
        e = Edge(from_node="A", to_node="B", base_weight=1.0)
        assert e.status == EdgeStatus.NORMAL

    def test_custom_status(self) -> None:
        e = Edge(from_node="A", to_node="B", base_weight=1.0, status=EdgeStatus.BLOCKED)
        assert e.status == EdgeStatus.BLOCKED


# ── Graph tests ───────────────────────────────────────────────────────────


class TestGraph:

    # -- add / query --

    def test_add_and_get_node(self, empty_graph: Graph) -> None:
        n = Node("A", 1.0, 2.0)
        empty_graph.add_node(n)
        assert empty_graph.get_node("A") is n
        assert empty_graph.node_count == 1

    def test_add_duplicate_node_raises(self, empty_graph: Graph) -> None:
        empty_graph.add_node(Node("A", 0, 0))
        with pytest.raises(ValueError, match="already exists"):
            empty_graph.add_node(Node("A", 1, 1))

    def test_add_edge_missing_source_raises(self, empty_graph: Graph) -> None:
        empty_graph.add_node(Node("B", 0, 0))
        with pytest.raises(ValueError, match="Source node"):
            empty_graph.add_edge(Edge("A", "B", 1.0))

    def test_add_edge_missing_dest_raises(self, empty_graph: Graph) -> None:
        empty_graph.add_node(Node("A", 0, 0))
        with pytest.raises(ValueError, match="Destination node"):
            empty_graph.add_edge(Edge("A", "B", 1.0))

    def test_get_neighbors(self, sample_graph: Graph) -> None:
        neighbors = sample_graph.get_neighbors("1")
        dest_ids = {e.to_node for e in neighbors}
        assert dest_ids == {"2", "3"}

    def test_get_neighbors_unknown_node_raises(self, empty_graph: Graph) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            empty_graph.get_neighbors("Z")

    def test_get_all_nodes(self, sample_graph: Graph) -> None:
        assert len(sample_graph.get_all_nodes()) == 3

    def test_get_all_edges(self, sample_graph: Graph) -> None:
        assert len(sample_graph.get_all_edges()) == 3

    def test_get_edge(self, sample_graph: Graph) -> None:
        e = sample_graph.get_edge("1", "2")
        assert e is not None
        assert e.base_weight == 5.0

    def test_get_edge_missing(self, sample_graph: Graph) -> None:
        assert sample_graph.get_edge("3", "1") is None

    def test_contains(self, sample_graph: Graph) -> None:
        assert "1" in sample_graph
        assert "Z" not in sample_graph

    def test_repr(self, sample_graph: Graph) -> None:
        assert "nodes=3" in repr(sample_graph)
        assert "edges=3" in repr(sample_graph)

    # -- JSON loading --

    def test_load_from_json(self, empty_graph: Graph) -> None:
        empty_graph.load_from_json(FIXTURES_DIR / "small_graph.json")
        assert empty_graph.node_count == 4
        assert empty_graph.edge_count == 5

        # verify adjacency
        a_neighbors = {e.to_node for e in empty_graph.get_neighbors("A")}
        assert a_neighbors == {"B", "D"}

    # -- Serialisation round-trip --

    def test_to_dict(self, sample_graph: Graph) -> None:
        d = sample_graph.to_dict()
        assert len(d["nodes"]) == 3
        assert len(d["edges"]) == 3
        # Verify node ids present
        node_ids = {n["id"] for n in d["nodes"]}
        assert node_ids == {"1", "2", "3"}
