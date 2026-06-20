"""Phase 5: blend live Weather Union rain with a corridor's historical water-logging propensity
into a 0..100 rain-clog risk score. Pure scoring fn + thin orchestration; no model, no DB writes,
no change to existing routes."""
from __future__ import annotations

from .config import get_settings
from .weather_union import rain_at

def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))

def rain_clog_score(intensity_mm_min: float, accumulation_mm: float,
                    waterlog_weight: float) -> float:
    """0..100. Live rain (intensity + accumulation, each normalized to a reference) scaled by how
    flood-prone the corridor historically is. A flood-prone corridor clogs at lower rain."""
    s = get_settings()
    intensity_n = (_clamp(intensity_mm_min / s.rain_intensity_ref_mm_per_min)
                   if s.rain_intensity_ref_mm_per_min else 0.0)
    accum_n = (_clamp(accumulation_mm / s.rain_accumulation_ref_mm)
               if s.rain_accumulation_ref_mm else 0.0)
    rain_pressure = _clamp(0.6 * intensity_n + 0.4 * accum_n)
    weight = 0.4 + 0.6 * _clamp(waterlog_weight)  # never fully ignore live rain
    return round(100.0 * _clamp(rain_pressure * weight), 1)

def _unavailable(name: str, reason: str) -> dict:
    return {
        "corridor": name,
        "available": False,
        "reason": reason,
        "rain_clog_score": 0.0,
        "risk_band": "unknown",
        "rain_multiplier": 1.0,
    }

def corridor_rain_risk(corridor: str) -> dict:
    """Live rain-clog risk for a corridor. Always returns a dict; available=False (with a reason
    and a neutral 1.0 multiplier) whenever the feature is off or live rain can't be resolved."""
    s = get_settings()
    name = (corridor or "").strip()
    key = name.lower()
    if not s.rain_clog_enabled:
        return _unavailable(name, "rain-clog disabled")
    latlon = s.corridor_latlon.get(key)
    if not latlon:
        return _unavailable(name, "no location mapping for corridor")
    rain = rain_at(latlon[0], latlon[1])
    if rain is None:
        return _unavailable(name, "live rain unavailable")
    waterlog = s.corridor_waterlog.get(key, s.corridor_waterlog_default)
    score = rain_clog_score(rain["intensity"], rain["accumulation"], waterlog)
    band = "high" if score >= 66 else "moderate" if score >= 33 else "low"
    multiplier = round(1.0 + 0.6 * (score / 100.0), 2)  # 1.0 .. 1.6, fold into ETA like events
    return {
        "corridor": name,
        "available": True,
        "rain_clog_score": score,
        "risk_band": band,
        "rain_multiplier": multiplier,
        "waterlog_weight": round(waterlog, 2),
        "stale": bool(rain.get("stale", False)),
        "rain": rain,
    }
