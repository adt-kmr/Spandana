"""Preprocessing lib: column normalization, UTC->IST, censoring labels,
junction snap-to-OSM-node (cached), and null-safe vehicle features."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd
from dateutil import parser as dtparser

from .config import get_settings
from .schema import EVENT_CAUSES, PRIORITY_ORD

CUE_WORDS = (
    "accident", "collision", "overturn", "fire", "injury", "injured", "blocked",
    "block", "severe", "major", "fatal", "ambulance", "trapped", "fallen",
    "flood", "waterlog", "stuck", "jam",
)

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase + snake-case all column names (e.g. Pot_holes -> pot_holes) (constraint 17)."""
    out = df.copy()
    out.columns = [
        str(c).strip().lower().replace("-", "_").replace(" ", "_") for c in out.columns
    ]
    return out

def _clean(v: Any) -> Optional[Any]:
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v

def parse_utc(value: Any) -> Optional[datetime]:
    """Parse a timestamp and return tz-aware UTC. Naive inputs are assumed UTC."""
    value = _clean(value)
    if value is None:
        return None
    dt = value if isinstance(value, datetime) else dtparser.isoparse(str(value))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def to_ist(dt_utc: Optional[datetime]) -> Optional[datetime]:
    """Convert tz-aware UTC to IST (+05:30) BEFORE any hour-of-day feature (constraint 4)."""
    if dt_utc is None:
        return None
    return dt_utc.astimezone(get_settings().ist_tz)

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))

def build_osm_node_grid() -> list[tuple[str, float, float]]:
    """Deterministic synthetic OSM-node grid over Bengaluru bounds (no network at import).

    In production this is replaced by a one-time real OSM snap; the contract is identical:
    snap each incident to the nearest cached node exactly once (constraint 18).
    """
    lat_lo, lat_hi = 12.83, 13.14
    lon_lo, lon_hi = 77.45, 77.78
    nodes: list[tuple[str, float, float]] = []
    steps = 24
    for i in range(steps):
        for j in range(steps):
            lat = lat_lo + (lat_hi - lat_lo) * i / (steps - 1)
            lon = lon_lo + (lon_hi - lon_lo) * j / (steps - 1)
            nodes.append((f"osm_{i:02d}_{j:02d}", round(lat, 6), round(lon, 6)))
    return nodes

_NODES = build_osm_node_grid()

def snap_junction(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    if lat is None or lon is None:
        return None
    best_id, best_d = None, float("inf")
    for nid, nlat, nlon in _NODES:
        d = haversine_m(lat, lon, nlat, nlon)
        if d < best_d:
            best_id, best_d = nid, d
    return best_id

def clearance_label(
    start: Optional[datetime],
    resolved: Optional[datetime],
    closed: Optional[datetime],
    as_of: Optional[datetime],
) -> tuple[Optional[float], int, int]:
    """Duration contract (constraints 2,3): clearance = resolved (fallback closed) - start.

    Returns (duration_minutes, event_observed, admin_close).
    end_datetime is never used. Unresolved rows are right-censored (never imputed).
    """
    if start is None:
        return None, 0, 0
    if resolved is not None:
        end, observed, admin = resolved, 1, 0
    elif closed is not None:
        end, observed, admin = closed, 1, 1  # administrative close flagged separately
    elif as_of is not None:
        end, observed, admin = as_of, 0, 0  # right-censored at snapshot time
    else:
        return None, 0, 0
    minutes = (end - start).total_seconds() / 60.0
    if minutes <= 0:
        return None, observed, admin
    return round(minutes, 3), observed, admin

def count_cues(text: str) -> int:
    t = (text or "").lower()
    return sum(t.count(w) for w in CUE_WORDS)

def prepare_records(records: list[dict], as_of: Optional[datetime] = None) -> pd.DataFrame:
    """Normalize raw incident dicts into the modeling frame. Shared by training and serving."""
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df = normalize_columns(df)

    start = df.get("start_datetime").map(parse_utc) if "start_datetime" in df else None
    resolved = df["resolved_datetime"].map(parse_utc) if "resolved_datetime" in df else None
    closed = df["closed_datetime"].map(parse_utc) if "closed_datetime" in df else None

    out = pd.DataFrame(index=df.index)
    out["event_id"] = df.get("event_id")
    out["event_cause"] = (
        df.get("event_cause", "others").astype(str).str.strip().str.lower().str.replace(" ", "_")
    )
    out.loc[~out["event_cause"].isin(EVENT_CAUSES), "event_cause"] = "others"
    out["corridor"] = df.get("corridor", "unknown").fillna("unknown")
    out["zone"] = df.get("zone", "unknown")
    out["priority"] = df.get("priority", "medium").astype(str).str.lower()
    out["requires_road_closure"] = (
        df.get("requires_road_closure", False).map(_to_bool).fillna(False)
    )
    out["latitude"] = pd.to_numeric(df.get("latitude"), errors="coerce")
    out["longitude"] = pd.to_numeric(df.get("longitude"), errors="coerce")
    out["rainfall_mm"] = pd.to_numeric(df.get("rainfall_mm", 0.0), errors="coerce").fillna(0.0)
    out["lanes_blocked"] = pd.to_numeric(df.get("lanes_blocked", 0), errors="coerce").fillna(0)
    out["description"] = df.get("description", "").fillna("").astype(str)
    out["comment"] = df.get("comment", "").fillna("").astype(str)
    out["severity_reported"] = df.get("severity_reported")

    # Null-safe vehicle features, gated to breakdown rows only (constraint 17).
    veh_type = df.get("veh_type")
    is_breakdown = out["event_cause"].eq("breakdown")
    out["veh_type"] = veh_type.where(is_breakdown) if veh_type is not None else None
    out["has_vehicle"] = (out["veh_type"].notna() & is_breakdown).astype(int)

    out["start_utc"] = start
    out["start_ist"] = out["start_utc"].map(to_ist) if start is not None else None
    out["hour_ist"] = (
        out["start_ist"].map(lambda d: d.hour if d is not None else np.nan)
        if start is not None
        else np.nan
    )
    out["dow_ist"] = (
        out["start_ist"].map(lambda d: d.weekday() if d is not None else np.nan)
        if start is not None
        else np.nan
    )

    durations, observed, admin = [], [], []
    for i in out.index:
        d, o, a = clearance_label(
            start.iloc[i] if start is not None else None,
            resolved.iloc[i] if resolved is not None else None,
            closed.iloc[i] if closed is not None else None,
            as_of,
        )
        durations.append(d)
        observed.append(o)
        admin.append(a)
    out["duration_minutes"] = durations
    out["event_observed"] = observed
    out["admin_close"] = admin

    out["junction_node"] = [
        snap_junction(la, lo) for la, lo in zip(out["latitude"], out["longitude"])
    ]
    out["cue_count"] = (out["description"] + " " + out["comment"]).map(count_cues)
    out["priority_ord"] = out["priority"].map(PRIORITY_ORD).fillna(1).astype(int)
    return out

def _to_bool(v: Any) -> Optional[bool]:
    v = _clean(v)
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "yes", "y", "t")

def load_and_prepare(csv_path: str, as_of: Optional[datetime] = None) -> pd.DataFrame:
    raw = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    records = raw.to_dict(orient="records")
    if as_of is None:
        starts = [parse_utc(r.get("start_datetime")) for r in records]
        starts = [s for s in starts if s is not None]
        as_of = max(starts).astimezone(get_settings().ist_tz) if starts else None
    elif as_of.tzinfo is not None:
        as_of = as_of.astimezone(get_settings().ist_tz)
    return prepare_records(records, as_of=as_of)
