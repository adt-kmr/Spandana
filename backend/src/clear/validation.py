"""Output validator: reject NaN / out-of-range model outputs before any persist (constraint 9)."""
from __future__ import annotations

import math
from typing import Any

from .config import get_settings
from .schema import SEVERITY_BANDS

class OutputValidationError(ValueError):
    """Raised when a model output is NaN, infinite, or outside its valid domain."""

def _finite(name: str, value: Any) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise OutputValidationError(f"{name} is not numeric: {value!r}") from exc
    if math.isnan(v) or math.isinf(v):
        raise OutputValidationError(f"{name} is NaN/inf")
    return v

def validate_severity(output: dict) -> dict:
    band = output.get("band")
    if band not in SEVERITY_BANDS:
        raise OutputValidationError(f"severity band invalid: {band!r}")
    conf = _finite("confidence", output.get("confidence"))
    if not 0.0 <= conf <= 1.0:
        raise OutputValidationError(f"confidence out of [0,1]: {conf}")
    return {"band": band, "confidence": round(conf, 4)}

def validate_clearance(output: dict) -> dict:
    cap = get_settings().max_clearance_minutes
    median = _finite("median", output.get("median_minutes"))
    p10 = _finite("p10", output.get("p10_minutes"))
    p90 = _finite("p90", output.get("p90_minutes"))
    for name, v in (("median", median), ("p10", p10), ("p90", p90)):
        if not 0.0 < v <= cap:
            raise OutputValidationError(f"{name} out of (0,{cap}]: {v}")
    if not p10 <= median <= p90:
        raise OutputValidationError(
            f"interval not ordered: p10={p10} median={median} p90={p90}"
        )
    return {
        "median_minutes": round(median, 2),
        "p10_minutes": round(p10, 2),
        "p90_minutes": round(p90, 2),
    }

def validate_forecast(output: dict) -> dict:
    risk = _finite("risk", output.get("risk"))
    if not 0.0 <= risk <= 100.0:
        raise OutputValidationError(f"risk out of [0,100]: {risk}")
    return {"risk": round(risk, 2)}
