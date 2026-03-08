"""
Traffic Simulation Engine.

Runs in a background thread and periodically perturbs edge weights
to simulate real-world traffic conditions:

    • **Congestion**  — weight × random multiplier (1.5–3.0)
    • **Accident**    — weight = ∞  (edge impassable)
    • **Recovery**    — gradual return toward base_weight

The engine emits change events via registered callbacks so that the
routing service can decide whether to trigger a path recomputation.

Design
──────
• Mutates ``Edge.current_weight`` and ``Edge.status`` **in-place**.
• Does NOT re-create the graph — the same ``Graph`` instance is shared.
• Thread-safe via a ``threading.Lock`` on the graph mutation section.
• Configurable tick interval, congestion probability, and recovery rate.
"""

from __future__ import annotations

import math
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, TYPE_CHECKING
from enum import Enum

from app.graph.models import Edge, EdgeStatus

if TYPE_CHECKING:
    from app.graph.graph import Graph


# ── Types ─────────────────────────────────────────────────────────────────

# Callback signature: (list_of_changed_edges) → None
ChangeCallback = Callable[[list[dict]], None]


class TimeOfDay(Enum):
    MORNING_RUSH = "Morning Rush"
    OFF_PEAK_DAY = "Off-Peak"
    EVENING_RUSH = "Evening Rush"
    NIGHT = "Night"


@dataclass
class TrafficConfig:
    """
    Tunable simulation parameters.

    Attributes:
        tick_interval:       Seconds between simulation ticks.
        congestion_prob:     Probability that a given edge becomes congested per tick.
        accident_prob:       Probability that a given edge suffers an accident per tick.
        recovery_rate:       Fraction of (current − base) weight recovered per tick.
        max_congestion_mult: Upper bound of the congestion multiplier.
        min_congestion_mult: Lower bound of the congestion multiplier.
    """

    tick_interval: float = 3.0
    congestion_prob: float = 0.005
    accident_prob: float = 0.001
    recovery_rate: float = 0.30
    max_congestion_mult: float = 3.0
    min_congestion_mult: float = 1.5


class TrafficEngine:
    """
    Background traffic simulation engine.

    Usage::

        engine = TrafficEngine(graph)
        engine.on_change(my_callback)
        engine.start()
        ...
        engine.stop()

    The callback receives a list of dicts describing changed edges::

        [
          {
            "from_node": "1",
            "to_node": "2",
            "old_weight": 220.0,
            "new_weight": 550.0,
            "status": "congested"
          },
          ...
        ]
    """

    def __init__(self, graph: "Graph", config: TrafficConfig | None = None) -> None:
        self._graph = graph
        self._config = config or TrafficConfig()
        self._callbacks: list[ChangeCallback] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._ticks_elapsed = 0
        self._time_of_day = TimeOfDay.OFF_PEAK_DAY

    # ── Public API ────────────────────────────────────────────────────

    def on_change(self, callback: ChangeCallback) -> None:
        """Register a callback to be invoked when edges change."""
        self._callbacks.append(callback)

    def start(self) -> None:
        """Start the simulation in a daemon background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="traffic-engine")
        self._thread.start()

    def stop(self) -> None:
        """Signal the simulation thread to stop and wait for it."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=self._config.tick_interval * 2)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._running

    def set_tick_interval(self, interval: float) -> None:
        """Change the simulation tick interval (speed control)."""
        self._config.tick_interval = max(0.5, min(10.0, interval))

    @property
    def time_of_day(self) -> TimeOfDay:
        return self._time_of_day

    @property
    def tick_interval(self) -> float:
        return self._config.tick_interval

    def tick(self) -> list[dict]:
        """
        Execute a single simulation tick (can also be called manually).

        Returns the list of edge-change dicts emitted in this tick.
        """
        self._ticks_elapsed += 1
        
        # Advance time of day every 60 ticks
        cycle_pos = (self._ticks_elapsed // 60) % 4
        if cycle_pos == 0:
            self._time_of_day = TimeOfDay.OFF_PEAK_DAY
        elif cycle_pos == 1:
            self._time_of_day = TimeOfDay.EVENING_RUSH
        elif cycle_pos == 2:
            self._time_of_day = TimeOfDay.NIGHT
        else:
            self._time_of_day = TimeOfDay.MORNING_RUSH

        changes: list[dict] = []
        all_edges = self._graph.get_all_edges()

        # --- Predictive Traffic Modeling ---
        # Identify "hot" nodes: intersections connected to congested or blocked roads.
        # Traffic waves will naturally propagate outwards from these hot nodes.
        hot_nodes = set()
        for edge in all_edges:
            if edge.status in (EdgeStatus.CONGESTED, EdgeStatus.BLOCKED):
                hot_nodes.add(edge.from_node)
                hot_nodes.add(edge.to_node)

        with self._lock:
            for edge in all_edges:
                is_hot = (edge.from_node in hot_nodes) or (edge.to_node in hot_nodes)
                change = self._process_edge(edge, is_hot)
                if change is not None:
                    changes.append(change)

        return changes

    def reset_traffic(self) -> list[dict]:
        """Reset all edges to base_weight and NORMAL status."""
        changes: list[dict] = []
        with self._lock:
            for edge in self._graph.get_all_edges():
                if edge.status != EdgeStatus.NORMAL:
                    changes.append({
                        "from_node": edge.from_node,
                        "to_node": edge.to_node,
                        "old_weight": edge.current_weight,
                        "new_weight": edge.base_weight,
                        "status": EdgeStatus.NORMAL.value,
                    })
                    edge.current_weight = edge.base_weight
                    edge.status = EdgeStatus.NORMAL
        
        # Notify listeners
        if changes:
            for cb in self._callbacks:
                cb(changes)
                
        return changes

    # ── Internals ─────────────────────────────────────────────────────

    def _loop(self) -> None:
        """Main simulation loop — runs on the background thread."""
        while self._running:
            changes = self.tick()
            if changes:
                for cb in self._callbacks:
                    cb(changes)
            time.sleep(self._config.tick_interval)

    def _process_edge(self, edge: Edge, is_hot: bool) -> dict | None:
        """
        Apply traffic logic to a single edge.

        Priority (checked in order):
            1. If already blocked → try recovery (small chance).
            2. If normal → maybe congest or block.
            3. If congested → maybe recover toward base.

        Returns a change dict if the edge was mutated, else None.

        Time complexity: O(1) per edge.
        """
        old_weight = edge.current_weight
        old_status = edge.status
        cfg = self._config
        roll = random.random()

        if edge.status == EdgeStatus.BLOCKED:
            # Blocked edges have a chance to recover
            if roll < cfg.recovery_rate * 0.5:
                edge.current_weight = edge.base_weight * cfg.max_congestion_mult
                edge.status = EdgeStatus.CONGESTED
            else:
                return None  # still blocked, no change

        elif edge.status == EdgeStatus.NORMAL:
            # Traffic Wave Simulation:
            # If this road connects to a congested intersection, vastly increase the chance
            # of the backlog spilling over into this road.
            
            # Rush hour multiplier
            rush_mult = 1.0
            if self._time_of_day in (TimeOfDay.MORNING_RUSH, TimeOfDay.EVENING_RUSH):
                rush_mult = 2.5
            elif self._time_of_day == TimeOfDay.NIGHT:
                rush_mult = 0.5

            acc_prob = cfg.accident_prob * (5.0 if is_hot else 1.0)
            cong_prob = cfg.congestion_prob * (3.0 if is_hot else 1.0) * rush_mult

            if roll < acc_prob:
                # Accident → blocked
                edge.current_weight = float("inf")
                edge.status = EdgeStatus.BLOCKED
            elif roll < acc_prob + cong_prob:
                # Congestion → weight multiplied
                mult = random.uniform(cfg.min_congestion_mult, cfg.max_congestion_mult)
                edge.current_weight = edge.base_weight * mult
                edge.status = EdgeStatus.CONGESTED
            else:
                return None  # stays normal

        elif edge.status == EdgeStatus.CONGESTED:
            # Gradually recover toward base_weight
            diff = edge.current_weight - edge.base_weight
            recovery = diff * cfg.recovery_rate
            edge.current_weight = max(edge.base_weight, edge.current_weight - recovery)

            if edge.current_weight <= edge.base_weight * 1.05:
                # Close enough → snap to normal
                edge.current_weight = edge.base_weight
                edge.status = EdgeStatus.NORMAL

        # Only emit if something actually changed
        if edge.current_weight == old_weight and edge.status == old_status:
            return None

        return {
            "from_node": edge.from_node,
            "to_node": edge.to_node,
            "old_weight": old_weight,
            "new_weight": edge.current_weight,
            "status": edge.status.value,
        }
