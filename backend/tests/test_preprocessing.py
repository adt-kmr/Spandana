"""Preprocessing unit tests: UTC->IST, column normalization, censoring labels."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from clear.preprocessing import (
    clearance_label,
    normalize_columns,
    parse_utc,
    prepare_records,
    to_ist,
)

def test_utc_to_ist_offset():
    ist = to_ist(parse_utc("2024-01-01T00:00:00Z"))
    assert ist.utcoffset().total_seconds() == 5.5 * 3600
    assert (ist.hour, ist.minute) == (5, 30)  # midnight UTC -> 05:30 IST

def test_normalize_columns_potholes():
    out = normalize_columns(pd.DataFrame({"Pot_holes": [1], "Veh Type": ["car"]}))
    assert "pot_holes" in out.columns
    assert "veh_type" in out.columns

def test_clearance_label_resolved_is_observed():
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    resolved = datetime(2024, 1, 1, 1, 0, tzinfo=timezone.utc)
    minutes, observed, admin = clearance_label(start, resolved, None, None)
    assert minutes == 60.0 and observed == 1 and admin == 0

def test_clearance_label_admin_close_flagged():
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    closed = datetime(2024, 1, 1, 2, 0, tzinfo=timezone.utc)
    _, observed, admin = clearance_label(start, None, closed, None)
    assert observed == 1 and admin == 1  # closed-only -> administrative close

def test_clearance_label_censored_not_imputed():
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    as_of = datetime(2024, 1, 1, 3, 0, tzinfo=timezone.utc)
    minutes, observed, admin = clearance_label(start, None, None, as_of)
    assert observed == 0 and admin == 0 and minutes == 180.0  # right-censored at snapshot

def test_vehicle_features_gated_to_breakdown():
    records = [
        {"event_id": "A", "start_datetime": "2024-01-01T00:00:00Z", "event_cause": "breakdown",
         "veh_type": "truck", "latitude": 12.9, "longitude": 77.6, "corridor": "X"},
        {"event_id": "B", "start_datetime": "2024-01-01T00:00:00Z", "event_cause": "accident",
         "veh_type": "truck", "latitude": 12.9, "longitude": 77.6, "corridor": "X"},
    ]
    by_id = prepare_records(records, as_of=None).set_index("event_id")
    assert by_id.loc["A", "has_vehicle"] == 1  # breakdown keeps vehicle
    assert by_id.loc["B", "has_vehicle"] == 0  # non-breakdown gated off
