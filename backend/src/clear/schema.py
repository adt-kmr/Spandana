"""Canonical schema: 46-column raw incident contract + validated inbound model."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# The 46-column Bengaluru incident schema the datagen emits and ingestion accepts.
# Intentionally includes a capitalized "Pot_holes" to exercise normalization (constraint 17).
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

# Real exports label causes differently from our canonical set (the anonymized ASTraM CSV
# uses "vehicle_breakdown", "construction", "vip_movement", ...). Map known variants onto
# canonical causes, then fall back to keyword matching, so the SAME normalization serves
# synthetic and real data. normalize_cause() lowercases first, so capitalized variants
# ("Debris", "Fog / Low Visibility") collapse onto their lowercase keys automatically.
CAUSE_ALIASES: dict[str, str] = {
    "vehicle_breakdown": "breakdown",
    "breakdown": "breakdown",
    "road_accident": "accident",
    "accident": "accident",
    "tree_fall": "tree_fall",
    "tree_fallen": "tree_fall",
    "water_logging": "water_logging",
    "waterlogging": "water_logging",
    "flooding": "water_logging",
    "pot_holes": "pot_holes",
    "potholes": "pot_holes",
    "pothole": "pot_holes",
    "public_event": "public_event",
    # --- real ASTraM export variants (from event_cause value counts) ---
    "procession": "public_event",
    "vip_movement": "public_event",
    "protest": "public_event",
    "construction": "others",
    "road_conditions": "others",
    "road_condition": "others",
    "congestion": "others",
    "debris": "others",
    "test_demo": "others",
    "fog": "others",
}

_CAUSE_KEYWORDS: list[tuple[str, str]] = [
    ("breakdown", "breakdown"),
    ("accident", "accident"),
    ("collision", "accident"),
    ("tree", "tree_fall"),
    ("water", "water_logging"),
    ("flood", "water_logging"),
    ("pot", "pot_holes"),
    ("event", "public_event"),
    ("procession", "public_event"),
    ("protest", "public_event"),
    ("vip", "public_event"),
]

def normalize_cause(value: object) -> str:
    """Map a raw event_cause onto a canonical EVENT_CAUSES value (exact, alias, keyword, else others)."""
    s = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if s in EVENT_CAUSES:
        return s
    if s in CAUSE_ALIASES:
        return CAUSE_ALIASES[s]
    for keyword, canonical in _CAUSE_KEYWORDS:
        if keyword in s:
            return canonical
    return "others"

PRIORITIES: list[str] = ["low", "medium", "high", "critical"]
PRIORITY_ORD: dict[str, int] = {p: i for i, p in enumerate(PRIORITIES)}
SEVERITY_BANDS: list[str] = ["low", "medium", "high", "critical"]

class IncidentIn(BaseModel):
    """Validated inbound incident. Datetimes may arrive as Postgres timestamptz text; they are
    parsed leniently (see _parse_datetimes) and stored tz-aware. Only event_id/start_datetime/
    latitude/longitude are truly required; every other field has a default that is substituted
    when the export sends an explicit null (see _none_to_field_default)."""

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

    @model_validator(mode="before")
    @classmethod
    def _none_to_field_default(cls, data: object) -> object:
        # Real exports send an explicit null for most columns (comment, zone, corridor,
        # status, requires_road_closure, ...). In Pydantic v2 a field default only applies
        # when the KEY IS ABSENT -- a present-but-None value is validated against the field
        # type and a non-Optional str/bool/number field rejects it, dead-lettering the row.
        # Substitute the declared default for any present-but-None field that has a concrete
        # (non-None) default. Truly required fields (no default) are left as-is so genuinely
        # missing event_id/start_datetime/lat/lon still fail loudly. Optional[...] = None
        # fields keep their None (e.g. datetimes routed through _parse_datetimes).
        if not isinstance(data, dict):
            return data
        out = dict(data)
        for name, field in cls.model_fields.items():
            if (
                out.get(name) is None
                and not field.is_required()
                and field.default is not None
            ):
                out[name] = field.default
        return out

    @field_validator(
        "start_datetime", "created_datetime", "resolved_datetime", "closed_datetime",
        mode="before",
    )
    @classmethod
    def _parse_datetimes(cls, v: object) -> object:
        # Real exports write Postgres timestamptz text ("2024-03-07 17:01:48.111+00") and the
        # literal "NULL" for missing values. Pydantic's native parser rejects the short "+00"
        # offset and "NULL", which dead-letters every row. Route through parse_utc (dateutil-
        # based, the SAME parser training uses) so ingestion and training agree: it returns a
        # tz-aware datetime, or None for missing/sentinel values. Lazy import breaks the
        # schema <-> preprocessing import cycle.
        from .preprocessing import parse_utc
        return parse_utc(v)

    @field_validator("event_cause", mode="before")
    @classmethod
    def _norm_cause(cls, v: object) -> str:
        return normalize_cause(v)

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
