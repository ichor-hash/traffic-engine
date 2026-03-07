"""
Data models for the Ambulance Dispatch System.

Defines the core entities: Ambulance, Hospital, Emergency, and DispatchResult.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AmbulanceStatus(str, Enum):
    AVAILABLE = "available"
    DISPATCHED = "dispatched"
    RETURNING = "returning"


class Severity(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    LIFE_THREATENING = 5


@dataclass
class Ambulance:
    """An ambulance unit in the fleet."""
    id: str
    name: str
    location: str  # node ID on the graph
    status: AmbulanceStatus = AmbulanceStatus.AVAILABLE

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "status": self.status.value,
        }


@dataclass
class Hospital:
    """A hospital with capacity tracking."""
    id: str
    name: str
    location: str  # node ID on the graph
    capacity: int
    current_load: int

    @property
    def congestion(self) -> float:
        """Load ratio 0.0–1.0."""
        return self.current_load / max(self.capacity, 1)

    @property
    def available_beds(self) -> int:
        return max(0, self.capacity - self.current_load)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "capacity": self.capacity,
            "current_load": self.current_load,
            "congestion": round(self.congestion, 3),
            "available_beds": self.available_beds,
        }


@dataclass
class Emergency:
    """An emergency event awaiting dispatch."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    location: str = ""  # node ID on the graph
    severity: int = 3
    timestamp: float = field(default_factory=time.time)
    assigned: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "location": self.location,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "assigned": self.assigned,
        }


@dataclass
class DispatchResult:
    """Result of a dispatch assignment."""
    emergency_id: str
    ambulance_id: str
    hospital_id: str
    algorithm: str
    path_to_emergency: list[str] = field(default_factory=list)
    path_to_hospital: list[str] = field(default_factory=list)
    response_time: float = 0.0  # distance to emergency (meters)
    transport_time: float = 0.0  # distance emergency→hospital (meters)
    total_time: float = 0.0     # total distance (meters) — kept for scoring
    nodes_visited: int = 0
    algorithm_ms: float = 0.0   # algorithm execution time in milliseconds

    # Average ambulance speed assumption: 40 km/h in urban area
    _SPEED_KMH: float = 40.0

    @property
    def response_distance_m(self) -> float:
        return self.response_time

    @property
    def transport_distance_m(self) -> float:
        return self.transport_time

    @property
    def total_distance_m(self) -> float:
        return self.response_time + self.transport_time

    @property
    def response_minutes(self) -> float:
        """Estimated response time in minutes at ambulance speed."""
        return (self.response_time / 1000.0) / self._SPEED_KMH * 60

    @property
    def transport_minutes(self) -> float:
        return (self.transport_time / 1000.0) / self._SPEED_KMH * 60

    @property
    def total_minutes(self) -> float:
        return self.response_minutes + self.transport_minutes

    def to_dict(self) -> dict:
        return {
            "emergency_id": self.emergency_id,
            "ambulance_id": self.ambulance_id,
            "hospital_id": self.hospital_id,
            "algorithm": self.algorithm,
            "path_to_emergency": self.path_to_emergency,
            "path_to_hospital": self.path_to_hospital,
            "response_distance_m": round(self.response_distance_m, 1),
            "transport_distance_m": round(self.transport_distance_m, 1),
            "total_distance_m": round(self.total_distance_m, 1),
            "response_minutes": round(self.response_minutes, 2),
            "transport_minutes": round(self.transport_minutes, 2),
            "total_minutes": round(self.total_minutes, 2),
            "nodes_visited": self.nodes_visited,
            "algorithm_ms": round(self.algorithm_ms, 2),
            # Legacy fields for backward compat
            "response_time": round(self.response_time, 2),
            "transport_time": round(self.transport_time, 2),
            "total_time": round(self.total_time, 2),
        }
