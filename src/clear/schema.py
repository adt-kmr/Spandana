"""Canonical schema: 46-column raw incident contract + validated inbound model."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# The 46-column Bengaluru incident schema the datagen emits and ingestion accepts.
# Intentionally includes a capitalized \"Pot_holes\" to exercise normalization (constraint 17).
RAW_COLUMNS: list[str] = [
    "event_id", "created_datetime", "start_datetime", "resolved_datetime",
    "closed_datetime", "end_datetime", "event_cause", "sub_cause", "description",
    "comment", "priority", "requires_road_closure", "corridor", "zone", "ward",
    "junction", "latitude", "longitude", "veh_type", "veh_no", "reported_by",
    "source_channel", "status", "severity_reported", "Pot_holes", "water_logging",
    "tree_fall", "weather", "rainfall_mm", "temperature_c", "lanes_blocked",
    "num_vehicles_involved", "injuries", "fatalities", "responder_unit",
    "response_team_size", "diversion_applied", "signal_id", "camera_id",
    "district", "police_station", "contact_number", "landmark", "direction",
    "updated_datetime", "remarks",
]
assert len(RAW_COLUMNS) == 46

EVENT_CAUSES: list[str] = [
    "breakdown", "accident", "tree_fall", "water_logging", "pot_holes",
    "public_event", "others",
]
PRIORITIES: list[str] = ["low", "medium", "high", "critical"]
PRIORITY_ORD: dict[str, int] = {p: i for i, p in enumerate(PRIORITIES)}
SEVERITY_BANDS: list[str] = ["low", "medium", "high", "critical"]

class IncidentIn(BaseModel):
    """Validated inbound incident. Timestamps are UTC (converted to IST downstream)."""

    event_id: str = Field(min_length=1)
    start_datetime: datetime
    event_cause: str = "others"
    corridor: str = "unknown"
    latitude: float
    longitude: float

    created_datetime: Optional[datetime] = None
    resolved_datetime: Optional[datetime] = None
    closed_datetime: Optional[datetime] = None
    description: str = ""
    comment: str = ""
    priority: str = "medium"
    requires_road_closure: bool = False
    zone: str = "unknown"
    junction: Optional[str] = None
    veh_type: Optional[str] = None
    veh_no: Optional[str] = None
    rainfall_mm: float = 0.0
    lanes_blocked: int = 0
    num_vehicles_involved: int = 0
    status: str = "open"
    severity_reported: Optional[str] = None

    @field_validator("event_cause", mode="before")
    @classmethod
    def _norm_cause(cls, v: object) -> str:
        s = str(v or "").strip().lower().replace(" ", "_")
        return s if s in EVENT_CAUSES else "others"

    @field_validator("priority", mode="before")
    @classmethod
    def _norm_priority(cls, v: object) -> str:
        s = str(v or "").strip().lower()
        return s if s in PRIORITIES else "medium"

    @field_validator("latitude")
    @classmethod
    def _lat_range(cls, v: float) -> float:
        if not -90.0 <= v <= 90.0:
            raise ValueError("latitude out of range")
        return v

    @field_validator("longitude")
    @classmethod
    def _lon_range(cls, v: float) -> float:
        if not -180.0 <= v <= 180.0:
            raise ValueError("longitude out of range")
        return v
