"""
Unit tests for the Traffic Simulation Engine (Phase 4).

Covers:
  • Single tick produces changes on a seeded RNG
  • Congested edges recover toward base_weight
  • Blocked edges eventually unblock
  • Callbacks fire with correct payloads
  • Start/stop lifecycle
  • Graph is mutated in-place (not recreated)
"""

from __future__ import annotations

import random
import time

import pytest

from app.graph.models import Edge, EdgeStatus, Node
from app.graph.graph import Graph
from app.simulation.engine import TrafficConfig, TrafficEngine


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def small_graph() -> Graph:
    """3-node triangle graph."""
    g = Graph()
    g.add_node(Node("A", 0.0, 0.0))
    g.add_node(Node("B", 1.0, 0.0))
    g.add_node(Node("C", 0.5, 1.0))
    g.add_edge(Edge("A", "B", base_weight=100.0))
    g.add_edge(Edge("B", "C", base_weight=150.0))
    g.add_edge(Edge("A", "C", base_weight=200.0))
    return g


@pytest.fixture
def aggressive_config() -> TrafficConfig:
    """Config with high probabilities so changes happen every tick."""
    return TrafficConfig(
        tick_interval=0.1,
        congestion_prob=0.80,
        accident_prob=0.10,
        recovery_rate=0.50,
        max_congestion_mult=3.0,
        min_congestion_mult=1.5,
    )


# ── Tests ─────────────────────────────────────────────────────────────────


class TestTrafficEngine:

    def test_tick_produces_changes(self, small_graph: Graph, aggressive_config: TrafficConfig) -> None:
        """With high probabilities, at least one edge should change."""
        random.seed(42)
        engine = TrafficEngine(small_graph, aggressive_config)
        changes = engine.tick()
        assert len(changes) > 0

    def test_edge_mutated_in_place(self, small_graph: Graph, aggressive_config: TrafficConfig) -> None:
        """Edge objects in the graph should be mutated, not replaced."""
        edge_before = small_graph.get_edge("A", "B")
        assert edge_before is not None
        original_weight = edge_before.current_weight

        random.seed(42)
        engine = TrafficEngine(small_graph, aggressive_config)

        # Run multiple ticks to ensure at least one change
        for _ in range(10):
            engine.tick()

        edge_after = small_graph.get_edge("A", "B")
        # Same object reference (mutated in-place)
        assert edge_after is edge_before

    def test_callback_fires(self, small_graph: Graph, aggressive_config: TrafficConfig) -> None:
        """Registered callbacks should receive change events."""
        random.seed(42)
        received: list[list[dict]] = []

        engine = TrafficEngine(small_graph, aggressive_config)
        engine.on_change(lambda changes: received.append(changes))
        engine.tick()

        assert len(received) > 0
        # Each change should have the expected keys
        for change in received[0]:
            assert "from_node" in change
            assert "to_node" in change
            assert "old_weight" in change
            assert "new_weight" in change
            assert "status" in change

    def test_change_dict_status_values(self, small_graph: Graph, aggressive_config: TrafficConfig) -> None:
        """Status values in changes should be valid EdgeStatus strings."""
        random.seed(42)
        engine = TrafficEngine(small_graph, aggressive_config)
        valid_statuses = {"normal", "congested", "blocked"}

        for _ in range(20):
            changes = engine.tick()
            for c in changes:
                assert c["status"] in valid_statuses

    def test_congestion_multiplier_range(self, small_graph: Graph) -> None:
        """Congested edges should have weight in [base*1.5, base*3.0]."""
        random.seed(42)
        config = TrafficConfig(
            congestion_prob=1.0,  # guaranteed congestion
            accident_prob=0.0,
        )
        engine = TrafficEngine(small_graph, config)
        engine.tick()

        for edge in small_graph.get_all_edges():
            if edge.status == EdgeStatus.CONGESTED:
                assert edge.current_weight >= edge.base_weight * 1.5
                assert edge.current_weight <= edge.base_weight * 3.0

    def test_accident_sets_infinity(self, small_graph: Graph) -> None:
        """Accident should set weight to infinity and status to BLOCKED."""
        random.seed(42)
        config = TrafficConfig(
            congestion_prob=0.0,
            accident_prob=1.0,  # guaranteed accident
        )
        engine = TrafficEngine(small_graph, config)
        engine.tick()

        for edge in small_graph.get_all_edges():
            assert edge.status == EdgeStatus.BLOCKED
            assert edge.current_weight == float("inf")

    def test_recovery_reduces_weight(self, small_graph: Graph) -> None:
        """Congested edges should gradually recover toward base_weight."""
        # First congest all edges
        for edge in small_graph.get_all_edges():
            edge.current_weight = edge.base_weight * 2.5
            edge.status = EdgeStatus.CONGESTED

        config = TrafficConfig(
            congestion_prob=0.0,
            accident_prob=0.0,
            recovery_rate=0.50,
        )
        engine = TrafficEngine(small_graph, config)
        engine.tick()

        for edge in small_graph.get_all_edges():
            # Weight should have decreased (recovered)
            assert edge.current_weight < edge.base_weight * 2.5

    def test_full_recovery_snaps_to_normal(self, small_graph: Graph) -> None:
        """After enough ticks, congested edges return to NORMAL."""
        for edge in small_graph.get_all_edges():
            edge.current_weight = edge.base_weight * 1.04  # just barely congested
            edge.status = EdgeStatus.CONGESTED

        config = TrafficConfig(
            congestion_prob=0.0,
            accident_prob=0.0,
            recovery_rate=0.90,
        )
        engine = TrafficEngine(small_graph, config)
        engine.tick()

        for edge in small_graph.get_all_edges():
            assert edge.status == EdgeStatus.NORMAL
            assert edge.current_weight == edge.base_weight

    def test_start_stop_lifecycle(self, small_graph: Graph) -> None:
        """Engine should start and stop cleanly."""
        config = TrafficConfig(tick_interval=0.05)
        engine = TrafficEngine(small_graph, config)

        assert not engine.is_running
        engine.start()
        assert engine.is_running

        time.sleep(0.15)  # let a few ticks run
        engine.stop()
        assert not engine.is_running

    def test_no_change_on_normal_low_probability(self, small_graph: Graph) -> None:
        """With zero probability, normal edges should stay unchanged."""
        config = TrafficConfig(
            congestion_prob=0.0,
            accident_prob=0.0,
        )
        engine = TrafficEngine(small_graph, config)
        changes = engine.tick()
        assert len(changes) == 0

        for edge in small_graph.get_all_edges():
            assert edge.status == EdgeStatus.NORMAL
            assert edge.current_weight == edge.base_weight
