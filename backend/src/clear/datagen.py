"""Synthetic 46-column Bengaluru incident generator.

Runs the app with no private dataset. If data/raw/incidents.csv already exists
with real data, ingestion/training will use it instead.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from .config import get_settings
from .schema import RAW_COLUMNS

_CORRIDORS = [
    ("Mysore Road", 0.18), ("Bellary Road", 0.12), ("Tumkur Road", 0.11),
    ("ORR East", 0.10), ("ORR West", 0.10), ("Old Madras Road", 0.08),
    ("Hosur Road", 0.09), ("Magadi Road", 0.07), ("Kanakapura Road", 0.08),
    ("Sarjapur Road", 0.07),
]
_CAUSES = [
    ("breakdown", 0.599), ("accident", 0.14), ("pot_holes", 0.066),
    ("water_logging", 0.056), ("tree_fall", 0.04), ("public_event", 0.03),
    ("others", 0.069),
]
_VEH = ["truck", "bus", "car", "auto", "two_wheeler", "lcv"]

_URGENCY = [("minor", 0.40), ("moderate", 0.30), ("serious", 0.20), ("severe", 0.10)]
# urgency is now a PRIMARY label driver, so the words alone can move the band
_URGENCY_SCORE = {"minor": 0.0, "moderate": 1.1, "serious": 2.3, "severe": 3.6}

def _pick(rng, options):
    names = [o[0] for o in options]
    probs = np.array([o[1] for o in options], dtype=float)
    probs = probs / probs.sum()
    return names[int(rng.choice(len(names), p=probs))]

def generate(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = datetime(2023, 11, 1, tzinfo=timezone.utc)
    rows: list[dict] = []
    for i in range(n):
        cause = _pick(rng, _CAUSES)
        corridor = _pick(rng, _CORRIDORS)
        start = base + timedelta(minutes=int(rng.integers(0, 181 * 24 * 60)))
        closure = bool(rng.random() < (0.5 if cause in ("accident", "tree_fall") else 0.06))
        urgency = _pick(rng, _URGENCY)
        priority = _pick(
            rng,
            [("low", 0.35), ("medium", 0.4), ("high", 0.2), ("critical", 0.05)],
        )
        # ~94% right-censored: resolved_datetime mostly null (constraint 2 reality).
        resolved = None
        closed = None
        true_dur = float(rng.gamma(shape=2.0, scale=25.0)) + (40 if closure else 0)
        roll = rng.random()
        if roll < 0.043:
            resolved = start + timedelta(minutes=true_dur)
        elif roll < 0.06:
            closed = start + timedelta(minutes=true_dur + rng.gamma(2.0, 120.0))
        rain = float(max(0.0, rng.normal(2.0, 6.0)))
        lanes = int(rng.integers(0, 4)) if closure else int(rng.integers(0, 2))
        # Severity label as a calibratable band (constraint 5 training target).
        score = (
            1.2 * closure
            + 0.5 * {"low": 0, "medium": 1, "high": 2, "critical": 3}[priority]
            + 0.5 * lanes
            + (1.0 if cause == "accident" else 0.0)
            + _URGENCY_SCORE[urgency]          # text-expressed urgency = primary driver
            + rng.normal(0, 0.5)
        )
        band = (
            "critical" if score > 4.0 else "high" if score > 2.5
            else "medium" if score > 1.2 else "low"
        )
        veh = rng.choice(_VEH) if cause == "breakdown" else ""
        rows.append(
            {
                "event_id": f"EVT-{i:06d}",
                "created_datetime": start.isoformat(),
                "start_datetime": start.isoformat(),
                "resolved_datetime": resolved.isoformat() if resolved else "",
                "closed_datetime": closed.isoformat() if closed else "",
                "end_datetime": "",  # intentionally null; never a duration source (constraint 3)
                "event_cause": cause,
                "sub_cause": "",
                "description": _desc(rng, cause, closure, urgency),
                "comment": "",
                "priority": priority,
                "requires_road_closure": str(closure).lower(),
                "corridor": corridor,
                "zone": f"Z{int(rng.integers(1, 9))}",
                "ward": f"W{int(rng.integers(1, 199))}",
                "junction": "" if rng.random() < 0.85 else f"J{int(rng.integers(1, 400))}",
                "latitude": round(float(rng.uniform(12.84, 13.13)), 6),
                "longitude": round(float(rng.uniform(77.46, 77.77)), 6),
                "veh_type": veh,
                "veh_no": (f"KA{int(rng.integers(1, 60)):02d}AB{int(rng.integers(0, 9999)):04d}"
                           if veh else ""),
                "reported_by": "officer",
                "source_channel": "radio",
                "status": "resolved" if resolved else ("closed" if closed else "open"),
                "severity_reported": band,
                "Pot_holes": "1" if cause == "pot_holes" else "0",  # capital -> normalized
                "water_logging": "1" if cause == "water_logging" else "0",
                "tree_fall": "1" if cause == "tree_fall" else "0",
                "weather": "rain" if rain > 5 else "clear",
                "rainfall_mm": round(rain, 2),
                "temperature_c": round(float(rng.normal(26, 3)), 1),
                "lanes_blocked": lanes,
                "num_vehicles_involved": int(rng.integers(1, 4)),
                "injuries": int(rng.integers(1, 4)) if urgency in ("serious", "severe") and cause == "accident" else 0,
                "fatalities": 0,
                "responder_unit": "",
                "response_team_size": int(rng.integers(0, 5)),
                "diversion_applied": str(closure).lower(),
                "signal_id": f"SIG{int(rng.integers(1, 165))}",
                "camera_id": "",
                "district": "Bengaluru",
                "police_station": f"PS{int(rng.integers(1, 50))}",
                "contact_number": "",
                "landmark": "",
                "direction": rng.choice(["NB", "SB", "EB", "WB"]),
                "updated_datetime": start.isoformat(),
                "remarks": "",
            }
        )
    return pd.DataFrame(rows, columns=RAW_COLUMNS)

def _desc(rng, cause: str, closure: bool, urgency: str) -> str:
    cause_phrase = {
        "breakdown": ["vehicle breakdown", "stalled truck blocking lane", "bus broke down mid-road"],
        "accident": ["accident reported", "vehicle collision", "two-wheeler crash"],
        "tree_fall": ["tree fallen across carriageway", "large branch down on road"],
        "water_logging": ["water logging on the stretch", "flooded road slowing traffic"],
        "pot_holes": ["pothole causing slowdown", "damaged road surface"],
        "public_event": ["public event procession", "rally spilling onto road"],
        "others": ["incident reported", "obstruction on the road"],
    }
    urgency_phrase = {
        "minor": ["minor, traffic still moving", "no injuries, slight slowdown"],
        "moderate": ["partially blocking traffic", "moderate congestion building"],
        "serious": ["lane blocked, injuries reported, ambulance requested", "people injured, ambulance on the way"],
        "severe": ["people trapped, ambulance and fire services needed", "fatal, road fully blocked, severe jam"],
    }
    base = str(rng.choice(cause_phrase.get(cause, ["incident reported"])))
    urg = str(rng.choice(urgency_phrase[urgency]))
    text = f"{base}; {urg}"
    if closure:
        text += "; road closure required"
    return text

def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Generate synthetic CLEAR incident CSV.")
    parser.add_argument("--out", default=str(settings.raw_data_dir / "incidents.csv"))
    parser.add_argument("--n", type=int, default=8173)
    parser.add_argument("--seed", type=int, default=settings.random_seed)
    args = parser.parse_args()
    settings.ensure_dirs()
    df = generate(args.n, args.seed)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows x {len(df.columns)} cols -> {args.out}")

if __name__ == "__main__":
    main()
