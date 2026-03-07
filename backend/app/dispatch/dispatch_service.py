"""
Dispatch Service — orchestrates ambulance fleet, hospitals, and emergencies.

Central coordinator between the dispatch algorithms and the API layer.
Manages entity state and provides high-level dispatch operations.
"""

from __future__ import annotations

import random
import threading
from typing import Callable, TYPE_CHECKING

from .models import (
    Ambulance,
    AmbulanceStatus,
    Hospital,
    Emergency,
    DispatchResult,
)
from .greedy import greedy_dispatch
from .hungarian import hungarian_dispatch

if TYPE_CHECKING:
    from app.graph.graph import Graph


# Callback: (event_type, data_dict) -> None
DispatchCallback = Callable[[str, dict], None]


# ── Preset data — ambulances and hospitals for T. Nagar, Chennai ──


# Selected from actual intersections in map.json
_AMBULANCE_PRESETS = [
    ("AMB-01", "Alpha Unit", "12852450817"),   # North Usman Rd & Panagal Park
    ("AMB-02", "Bravo Unit", "250364033"),      # Maharajapuram Santhanam Salai
    ("AMB-03", "Charlie Unit", "1701428465"),   # GN Rd & North Crescent Rd
    ("AMB-04", "Delta Unit", "250364075"),      # Mambalam High Rd & Ramakrishna St
    ("AMB-05", "Echo Unit", "250364747"),       # Arulambal St & Habibullah Rd
]

_HOSPITAL_PRESETS = [
    ("H-01", "T. Nagar General Hospital", "2197203112", 80, 45),  # GN Rd & Panagal Park
    ("H-02", "Mambalam Medical Centre", "298154015", 60, 35),     # Gangai Amman St
    ("H-03", "Usman Road Clinic", "2197415767", 40, 28),          # Habibullah Rd & North Usman Rd
]


class DispatchService:
    """
    Central dispatch coordinator.

    Manages the ambulance fleet, hospital registry, and emergency queue.
    Provides dispatch operations using greedy and Hungarian algorithms.
    
    DISPATCH-inspired mechanics:
    - Score system: faster response to high-severity emergencies = more points
    - Auto-emergencies: random emergencies spawn during simulation
    - Cooldown: dispatched ambulances return to available after a delay
    """

    def __init__(self, graph: "Graph") -> None:
        self._graph = graph
        self._lock = threading.Lock()
        self._callbacks: list[DispatchCallback] = []

        # Initialise fleet and hospitals
        self._ambulances: list[Ambulance] = []
        self._hospitals: list[Hospital] = []
        self._emergencies: list[Emergency] = []
        self._dispatch_history: list[DispatchResult] = []

        # Scoring — DISPATCH-inspired
        self._score: int = 0
        self._dispatches_count: int = 0
        self._missed_count: int = 0  # emergencies that expired
        self._auto_emg_counter: int = 0  # ticks until next auto-emergency
        self._cooldown_timers: dict[str, int] = {}  # amb_id -> ticks remaining

        self._init_presets()

    def _init_presets(self) -> None:
        """Load ambulances and hospitals from preset data."""
        for aid, name, loc in _AMBULANCE_PRESETS:
            self._ambulances.append(Ambulance(
                id=aid, name=name, location=loc,
            ))
        for hid, name, loc, cap, load in _HOSPITAL_PRESETS:
            self._hospitals.append(Hospital(
                id=hid, name=name, location=loc,
                capacity=cap, current_load=load,
            ))

    # ── Public API ────────────────────────────────────────────────

    def on_dispatch_event(self, callback: DispatchCallback) -> None:
        """Register a callback for dispatch events."""
        self._callbacks.append(callback)

    def get_state(self) -> dict:
        """Return current state of the dispatch system."""
        with self._lock:
            return {
                "ambulances": [a.to_dict() for a in self._ambulances],
                "hospitals": [h.to_dict() for h in self._hospitals],
                "emergencies": [e.to_dict() for e in self._emergencies],
                "history": [d.to_dict() for d in self._dispatch_history[-10:]],
                "score": self._score,
                "dispatches": self._dispatches_count,
                "missed": self._missed_count,
            }

    def generate_emergency(self) -> Emergency:
        """
        Create a random emergency at a graph node.

        Picks a random node and assigns a random severity 1–5.
        """
        all_nodes = self._graph.get_all_nodes()
        node = random.choice(all_nodes)
        severity = random.choices([1, 2, 3, 4, 5], weights=[5, 15, 40, 25, 15])[0]

        emg = Emergency(location=node.id, severity=severity)

        with self._lock:
            self._emergencies.append(emg)

        # Notify listeners
        self._emit("emergency_new", emg.to_dict())

        return emg

    def dispatch_greedy(self, emergency_id: str | None = None) -> DispatchResult | None:
        """
        Dispatch using the greedy (nearest ambulance) algorithm.

        If emergency_id is None, dispatches the oldest pending emergency.
        """
        with self._lock:
            emg = self._find_emergency(emergency_id)
            if emg is None:
                return None

            result = greedy_dispatch(
                self._graph, emg, self._ambulances, self._hospitals,
            )

            if result:
                self._apply_assignment(emg, result)

        if result:
            self._emit("dispatch_assigned", result.to_dict())

        return result

    def dispatch_hungarian(self) -> list[DispatchResult]:
        """
        Dispatch all pending emergencies using the Hungarian algorithm.

        Returns a list of assignments.
        """
        with self._lock:
            pending = [e for e in self._emergencies if not e.assigned]
            if not pending:
                return []

            results = hungarian_dispatch(
                self._graph, pending, self._ambulances, self._hospitals,
            )

            for result in results:
                emg = next((e for e in self._emergencies if e.id == result.emergency_id), None)
                if emg:
                    self._apply_assignment(emg, result)

        for result in results:
            self._emit("dispatch_assigned", result.to_dict())

        return results

    def compare_methods(self, emergency_id: str | None = None) -> dict:
        """
        Run both greedy and hungarian on the same emergency set
        and return side-by-side results WITHOUT applying changes.
        """
        with self._lock:
            emg = self._find_emergency(emergency_id)
            if emg is None:
                return {"error": "No pending emergency found"}

            pending = [e for e in self._emergencies if not e.assigned]

            # Run greedy (doesn't mutate)
            greedy_result = greedy_dispatch(
                self._graph, emg, self._ambulances, self._hospitals,
            )

            # Run hungarian on all pending
            hungarian_results = hungarian_dispatch(
                self._graph, pending, self._ambulances, self._hospitals,
            )

            # Find the hungarian result for our specific emergency
            hungarian_for_emg = next(
                (r for r in hungarian_results if r.emergency_id == emg.id),
                None,
            )

        return {
            "emergency": emg.to_dict(),
            "greedy": greedy_result.to_dict() if greedy_result else None,
            "hungarian": hungarian_for_emg.to_dict() if hungarian_for_emg else None,
        }

    def reset(self) -> None:
        """Reset all ambulances to available and clear emergencies."""
        with self._lock:
            for amb in self._ambulances:
                for aid, _, loc in _AMBULANCE_PRESETS:
                    if amb.id == aid:
                        amb.location = loc
                        break
                amb.status = AmbulanceStatus.AVAILABLE

            for hosp in self._hospitals:
                for hid, _, _, cap, load in _HOSPITAL_PRESETS:
                    if hosp.id == hid:
                        hosp.current_load = load
                        break

            self._emergencies.clear()
            self._dispatch_history.clear()
            self._score = 0
            self._dispatches_count = 0
            self._missed_count = 0
            self._cooldown_timers.clear()
            self._auto_emg_counter = 0

    def tick_hospitals(self) -> None:
        """
        Simulation tick: adjust hospital loads, process cooldowns,
        auto-generate emergencies, and broadcast updates.
        """
        with self._lock:
            # Hospital load fluctuation
            for hosp in self._hospitals:
                delta = random.choices([-2, -1, 0, 1, 2, 3], weights=[5, 15, 40, 25, 10, 5])[0]
                hosp.current_load = max(0, min(hosp.capacity, hosp.current_load + delta))

            # Ambulance cooldown — return to available after ticks
            expired = []
            for amb_id, ticks in self._cooldown_timers.items():
                if ticks <= 1:
                    expired.append(amb_id)
                else:
                    self._cooldown_timers[amb_id] = ticks - 1

            for amb_id in expired:
                del self._cooldown_timers[amb_id]
                amb = next((a for a in self._ambulances if a.id == amb_id), None)
                if amb and amb.status == AmbulanceStatus.DISPATCHED:
                    amb.status = AmbulanceStatus.AVAILABLE
                    # Return to a random preset location
                    preset = random.choice(_AMBULANCE_PRESETS)
                    amb.location = preset[2]

        self._emit("hospital_update", {
            "hospitals": [h.to_dict() for h in self._hospitals],
        })

        # Auto-generate emergency (every 3-6 ticks during simulation)
        self._auto_emg_counter += 1
        if self._auto_emg_counter >= random.randint(3, 6):
            self._auto_emg_counter = 0
            self.generate_emergency()

    # ── Internals ─────────────────────────────────────────────────

    def _find_emergency(self, emergency_id: str | None) -> Emergency | None:
        """Find a specific or oldest pending emergency."""
        if emergency_id:
            return next(
                (e for e in self._emergencies
                 if e.id == emergency_id and not e.assigned),
                None,
            )
        # Return oldest pending
        pending = [e for e in self._emergencies if not e.assigned]
        return pending[0] if pending else None

    def _apply_assignment(self, emg: Emergency, result: DispatchResult) -> None:
        """
        Apply a dispatch assignment — mark emergency as assigned,
        ambulance as dispatched, increment hospital load.
        Score: severity × 20 − total_time, bonus for fast response.

        Must be called under self._lock.
        """
        emg.assigned = True

        amb = next((a for a in self._ambulances if a.id == result.ambulance_id), None)
        if amb:
            amb.status = AmbulanceStatus.DISPATCHED
            amb.location = emg.location
            # Set cooldown: 3 ticks before ambulance returns
            self._cooldown_timers[amb.id] = 3

        hosp = next((h for h in self._hospitals if h.id == result.hospital_id), None)
        if hosp:
            hosp.current_load = min(hosp.current_load + 1, hosp.capacity)

        self._dispatch_history.append(result)

        # Score calculation
        base = emg.severity * 20
        time_penalty = int(result.total_time)
        speed_bonus = 10 if result.total_time < 50 else 0
        points = max(0, base + speed_bonus - time_penalty)
        self._score += points
        self._dispatches_count += 1

    def _emit(self, event_type: str, data: dict) -> None:
        """Notify all registered callbacks."""
        for cb in self._callbacks:
            try:
                cb(event_type, data)
            except Exception:
                pass
