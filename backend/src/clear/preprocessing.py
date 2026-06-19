"""Preprocessing lib: column normalization, UTC->IST, censoring labels,
junction snap-to-OSM-node (cached), and null-safe vehicle features."""
from __future__ import annotations

import math
import unicodedata
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd
from dateutil import parser as dtparser
from sklearn.neighbors import BallTree

from .config import get_settings
from .schema import PRIORITY_ORD, normalize_cause

CUE_WORDS = (
    "accident", "collision", "overturn", "fire", "injury", "injured", "blocked",
    "block", "severe", "major", "fatal", "ambulance", "trapped", "fallen",
    "flood", "waterlog", "stuck", "jam",
)

# Tiered, multilingual severity cue lexicons (EN / हिन्दी / ಕನ್ನಡ / romanized). These power the
# text-only severity model and work with ZERO torch, so /nlp/severity stays confident in prod
# even on a MuRIL cache miss. Substring .count() matching; non-Latin scripts are case-stable.
SEVERE_CUES = (
    # English
    "fatal", "fatality", "fatalities", "died", "death", "dead", "killed",
    "casualty", "casualties", "trapped", "fire", "burning", "burnt", "blaze",
    "explosion", "critical", "severe", "overturn", "overturned", "flipped",
    "drowned", "drowning", "washed away",
    # हिन्दी
    "मृत", "मौत", "मृत्यु", "लाश", "फँसे", "फंसे", "फँस", "फंस",
    "आग", "गंभीर", "भीषण", "भयानक", "घातक", "जानलेवा",
    # ಕನ್ನಡ
    "ಸಾವು", "ಮೃತ", "ಬೆಂಕಿ", "ಸಿಲುಕಿ", "ಗಂಭೀರ", "ಭೀಕರ", "ಮಾರಣಾಂತಿಕ",
)
SERIOUS_CUES = (
    "injured", "injury", "injuries", "ambulance", "blood", "collision",
    "accident", "crash", "head-on", "rammed",
    # serious flooding
    "submerged", "stranded", "swept", "marooned", "knee-deep", "waist-deep", "overflowing",
    "घायल", "एम्बुलेंस", "दुर्घटना", "टक्कर", "हादसा", "एक्सीडेंट",
    "डूब", "बाढ़", "बह गया",
    "ಗಾಯ", "ಆಂಬುಲೆನ್ಸ್", "ಅಪಘಾತ", "ಡಿಕ್ಕಿ", "ಗಾಯಗೊಂಡ",
    "ಮುಳುಗಿ", "ಕೊಚ್ಚಿ", "ಪ್ರವಾಹ",
)
MODERATE_CUES = (
    "blocked", "block", "jam", "congestion", "slow", "partially", "stuck",
    "diversion", "queue", "tailback",
    # neutral flooding / disruption
    "water logging", "waterlogging", "waterlogged", "flooded", "flooding",
    "रुका", "जाम", "भीड़", "धीमा", "रुकावट", "जलभराव", "पानी भर",
    "ಬ್ಲಾಕ್", "ಜಾಮ್", "ನಿಧಾನ", "ದಟ್ಟಣೆ", "ತಡೆ", "ನೀರು ನಿಂತಿ", "ನೀರು ತುಂಬಿ",
)
MINOR_CUES = (
    "minor", "slight", "small", "cleared", "moving", "normal",
    "मामूली", "छोटा", "हल्का", "सामान्य",
    "ಸಣ್ಣ", "ಚಿಕ್ಕ", "ಲಘು", "ಸಾಮಾನ್ಯ",
)
CLOSURE_CUES = (
    "closure", "closed", "fully blocked", "shut", "road closed", "blocked off",
    "बंद", "पूरी तरह बंद",
    "ಬಂದ್", "ಸಂಪೂರ್ಣ ಬಂದ್",
)

def _normalize_text(text: str) -> str:
    """Lowercase + NFC + collapse Hindi chandrabindu (ँ U+0901) to anusvara
    (ं U+0902) so फँसे/फंसे, गाँव/गांव match a single lexicon spelling."""
    return unicodedata.normalize("NFC", (text or "").lower()).replace("\u0901", "\u0902")

# Negation: a danger word right next to a negator must NOT count
# ("no fire", "koi injury nahi", "कोई घायल नहीं", "ಗಾಯ ಇಲ್ಲ").
_PRE_NEGATORS = frozenset({"no", "not", "without", "never", "bina", "बिना", "ना"})
_POST_NEGATORS = frozenset({"nahi", "nahin", "नहीं", "नही"})

def _strip_negated(text: str) -> str:
    """Blank a cue token adjacent to a negator. Directional: pre-negators kill
    the next token; post-negators and the Kannada 'ಇಲ್ಲ' suffix kill the prev."""
    toks = text.split()
    out = list(toks)
    for i, raw in enumerate(toks):
        core = raw.strip(".,;:!?()-")
        if core in _PRE_NEGATORS and i + 1 < len(toks):
            out[i + 1] = ""
        if (core in _POST_NEGATORS or core.endswith("ಇಲ್ಲ")) and i - 1 >= 0:
            out[i - 1] = ""
    return " ".join(out)

def _count_terms(text: str, terms: tuple) -> int:
    t = _strip_negated(_normalize_text(text))
    return sum(t.count(_normalize_text(w)) for w in terms)

def count_cues(text: str) -> int:
    t = _strip_negated(_normalize_text(text))
    return sum(t.count(w) for w in CUE_WORDS)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase + snake-case all column names (e.g. Pot_holes -> pot_holes) (constraint 17)."""
    out = df.copy()
    out.columns = [
        str(c).strip().lower().replace("-", "_").replace(" ", "_") for c in out.columns
    ]
    return out


# Real-world datasets (e.g. the anonymized ASTraM export) name columns differently
# from our canonical schema. Map known aliases onto canonical names so the SAME
# pipeline ingests both the synthetic CSV and a real export with no per-source code.
COLUMN_ALIASES: dict[str, str] = {
    "id": "event_id",
    "created_date": "created_datetime",
}


def apply_column_aliases(df: pd.DataFrame) -> pd.DataFrame:
    """Rename known source-specific columns to canonical names (run after normalize_columns).
    Only renames when the alias is present AND the canonical target is absent, so a real
    canonical column is never clobbered.
    """
    renames = {
        src: dst
        for src, dst in COLUMN_ALIASES.items()
        if src in df.columns and dst not in df.columns
    }
    return df.rename(columns=renames) if renames else df


# Real exports use literal sentinel strings for missing values (the anonymized ASTraM CSV
# writes "NULL"). With keep_default_na=False these survive as text, so we normalize them to
# None everywhere - otherwise parse_utc("NULL") crashes and validators choke on junk.
# Compared case-insensitively after stripping.
NULL_SENTINELS = frozenset({"", "null", "nan", "none", "na", "n/a"})


def _clean(v: Any) -> Optional[Any]:
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, str) and v.strip().lower() in NULL_SENTINELS:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return v


def scrub_sentinels(df: pd.DataFrame) -> pd.DataFrame:
    """Replace literal missing-value sentinels (e.g. "NULL", "NA") with None across every cell.
    Run right after normalize_columns + apply_column_aliases so all downstream typing, date
    parsing, and validation treat sentinels as truly missing instead of as the string "NULL".
    """
    return df.map(_clean)


def parse_utc(value: Any) -> Optional[datetime]:
    """Parse a timestamp and return tz-aware UTC.
    Real exports may store tz-aware Postgres timestamptz text (e.g. "...+00") OR naive local
    timestamps. tz-aware inputs keep their own offset; naive inputs are localized to IST (the
    operational timezone) before converting to UTC. Everything downstream treats time as UTC;
    `to_ist` re-localizes for hour-of-day features, giving exactly one IST shift. (constraint 4)
    """
    value = _clean(value)
    if value is None:
        return None
    dt = value if isinstance(value, datetime) else dtparser.isoparse(str(value))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=get_settings().ist_tz)
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
# Index the node grid ONCE in a BallTree (compiled haversine metric, radians) so snapping is
# O(log M) per point instead of a Python loop over all ~576 nodes. For N incidents this turns
# an O(N*M) brute force (~millions of haversine calls) into O(N log M). Tree is built a single
# time at import; `snap_junctions` runs one vectorized batch query for the whole frame. (perf)
_NODE_IDS: list[str] = [nid for nid, _, _ in _NODES]
_NODE_COORDS_RAD = np.radians([[lat, lon] for _, lat, lon in _NODES])
_NODE_TREE = BallTree(_NODE_COORDS_RAD, metric="haversine")


def snap_junction(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    """Snap one (lat, lon) to the nearest cached OSM node id, or None if coords are missing."""
    if lat is None or lon is None:
        return None
    _, idx = _NODE_TREE.query(np.radians([[lat, lon]]), k=1)
    return _NODE_IDS[int(idx[0][0])]


def snap_junctions(lats: pd.Series | np.ndarray, lons: pd.Series | np.ndarray) -> list[Optional[str]]:
    """Vectorized snap: ONE BallTree query for all points. Missing coords map to None."""
    lat_arr = pd.to_numeric(pd.Series(lats).reset_index(drop=True), errors="coerce")
    lon_arr = pd.to_numeric(pd.Series(lons).reset_index(drop=True), errors="coerce")
    valid = lat_arr.notna() & lon_arr.notna()
    result: list[Optional[str]] = [None] * len(lat_arr)
    if valid.any():
        coords = np.radians(
            np.column_stack([lat_arr[valid].to_numpy(), lon_arr[valid].to_numpy()])
        )
        _, idx = _NODE_TREE.query(coords, k=1)
        for pos, node_pos in zip(np.flatnonzero(valid.to_numpy()), idx[:, 0]):
            result[int(pos)] = _NODE_IDS[int(node_pos)]
    return result


def clearance_label(
    start: Optional[datetime],
    resolved: Optional[datetime],
    closed: Optional[datetime],
    as_of: Optional[datetime],
    status: Optional[str] = None,
) -> tuple[Optional[float], int, int]:
    """Duration contract (constraints 2,3): clearance = resolved (fallback closed) - start.
    Returns (duration_minutes, event_observed, admin_close).

    CRITICAL: parse_utc yields pandas NaT (not None) for missing timestamps, and
    `NaT is not None` is True. The old `is not None` checks therefore treated EVERY row as
    'resolved', stamped event_observed=1 on all 8173 rows, never reached the closed/as_of
    branches, and produced a NaN duration for every row except the 74 truly-resolved ones --
    silently starving the fitter. Always gate on pd.notna().

    Open incidents are RIGHT-CENSORED at their current age (never imputed). A row that is
    'closed'/'resolved' by status but has NO end timestamp is informative-missing (the event
    happened; the export just dropped the time) -- that is NOT genuine censoring, so it is
    dropped rather than pretending it is still running.
    """
    if start is None or pd.isna(start):
        return None, 0, 0
    has_resolved = resolved is not None and pd.notna(resolved)
    has_closed = closed is not None and pd.notna(closed)
    if has_resolved:
        end, observed, admin = resolved, 1, 0
    elif has_closed:
        end, observed, admin = closed, 1, 1  # administrative close flagged separately
    else:
        st = str(status).strip().lower() if (status is not None and pd.notna(status)) else ""
        if st in ("closed", "resolved"):
            return None, 0, 0  # informative-missing: end happened but timestamp absent -> drop
        if as_of is not None and pd.notna(as_of):
            end, observed, admin = as_of, 0, 0  # right-censored at snapshot age
        else:
            return None, 0, 0
    minutes = (end - start).total_seconds() / 60.0
    if minutes <= 0:
        return None, observed, admin
    return round(minutes, 3), observed, admin





def _col(df: pd.DataFrame, name: str, default: Any = None) -> pd.Series:
    """Return column `name` as an index-aligned Series, defaulting if it is absent.
    pandas' DataFrame.get returns the SCALAR default when a column is missing, which
    breaks chained Series ops (.astype/.map/.fillna). This always yields a Series.
    """
    if name in df.columns:
        return df[name]
    return pd.Series([default] * len(df), index=df.index)


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
    out["event_id"] = _col(df, "event_id")
    out["event_cause"] = _col(df, "event_cause", "others").map(normalize_cause)
    out["corridor"] = _col(df, "corridor", "unknown").fillna("unknown")
    out["zone"] = _col(df, "zone", "unknown")
    out["priority"] = _col(df, "priority", "medium").astype(str).str.lower()
    out["requires_road_closure"] = (
        _col(df, "requires_road_closure", False).map(_to_bool).fillna(False)
    )
    out["latitude"] = pd.to_numeric(_col(df, "latitude"), errors="coerce")
    out["longitude"] = pd.to_numeric(_col(df, "longitude"), errors="coerce")
    out["rainfall_mm"] = pd.to_numeric(_col(df, "rainfall_mm", 0.0), errors="coerce").fillna(0.0)
    out["lanes_blocked"] = pd.to_numeric(_col(df, "lanes_blocked", 0), errors="coerce").fillna(0)
    out["description"] = _col(df, "description", "").fillna("").astype(str)
    out["comment"] = _col(df, "comment", "").fillna("").astype(str)
    # Severity label: the real ASTraM export has no `severity_reported` column. Fall back to
    # `priority` (identical bands: low/medium/high/critical) so the severity model trains on a
    # real operational-urgency label instead of degrading to 503. Rows whose label is not a
    # valid severity band are ignored by the trainer.
    reported_sev = _col(df, "severity_reported").map(_clean)
    out["severity_reported"] = reported_sev.where(reported_sev.notna(), out["priority"])
    # Null-safe vehicle features, gated to breakdown rows only (constraint 17).
    veh_type = _col(df, "veh_type")
    is_breakdown = out["event_cause"].eq("breakdown")
    out["veh_type"] = veh_type.where(is_breakdown)
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
    status_col = df["status"] if "status" in df else None
    durations, observed, admin = [], [], []
    for i in out.index:
        d, o, a = clearance_label(
            start.iloc[i] if start is not None else None,
            resolved.iloc[i] if resolved is not None else None,
            closed.iloc[i] if closed is not None else None,
            as_of,
            status_col.iloc[i] if status_col is not None else None,
        )
        durations.append(d)
        observed.append(o)
        admin.append(a)
    out["duration_minutes"] = durations
    out["event_observed"] = observed
    out["admin_close"] = admin
    out["junction_node"] = snap_junctions(out["latitude"], out["longitude"])
    out["cue_count"] = (out["description"] + " " + out["comment"]).map(count_cues)
    _cue_blob = (out["description"] + " " + out["comment"])
    out["cue_severe"] = _cue_blob.map(lambda t: _count_terms(t, SEVERE_CUES))
    out["cue_serious"] = _cue_blob.map(lambda t: _count_terms(t, SERIOUS_CUES))
    out["cue_moderate"] = _cue_blob.map(lambda t: _count_terms(t, MODERATE_CUES))
    out["cue_minor"] = _cue_blob.map(lambda t: _count_terms(t, MINOR_CUES))
    out["cue_closure"] = _cue_blob.map(lambda t: _count_terms(t, CLOSURE_CUES))
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
    raw = scrub_sentinels(apply_column_aliases(normalize_columns(raw)))
    records = raw.to_dict(orient="records")
    if as_of is None:
        starts = [parse_utc(r.get("start_datetime")) for r in records]
        starts = [s for s in starts if s is not None]
        as_of = max(starts).astimezone(get_settings().ist_tz) if starts else None
    elif as_of.tzinfo is not None:
        as_of = as_of.astimezone(get_settings().ist_tz)
    return prepare_records(records, as_of=as_of)