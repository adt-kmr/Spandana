"""Output validator tests: NaN/out-of-range/unordered outputs are rejected (constraint 9)."""
from __future__ import annotations

import math

import pytest

from clear.validation import (
    OutputValidationError,
    validate_clearance,
    validate_forecast,
    validate_severity,
)

def test_severity_valid():
    out = validate_severity({"band": "high", "confidence": 0.82})
    assert out["band"] == "high" and out["confidence"] == 0.82

def test_severity_bad_band():
    with pytest.raises(OutputValidationError):
        validate_severity({"band": "extreme", "confidence": 0.5})

def test_severity_nan_confidence():
    with pytest.raises(OutputValidationError):
        validate_severity({"band": "low", "confidence": math.nan})

def test_clearance_valid():
    out = validate_clearance({"median_minutes": 45, "p10_minutes": 20, "p90_minutes": 120})
    assert out["p10_minutes"] <= out["median_minutes"] <= out["p90_minutes"]

def test_clearance_interval_order_enforced():
    with pytest.raises(OutputValidationError):
        validate_clearance({"median_minutes": 50, "p10_minutes": 80, "p90_minutes": 90})

def test_forecast_out_of_range():
    with pytest.raises(OutputValidationError):
        validate_forecast({"risk": 150})
