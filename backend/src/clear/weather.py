"""Open-Meteo rainfall enrichment (real weather, not a fabricated constant).

Dependency-free (urllib only) so it adds nothing to the build. EVERY failure path returns 0.0
-- exactly today's value -- so /ingest never blocks on the weather API and flag-off behavior is
byte-for-byte the current backend.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from .config import get_settings
from .logging_setup import configure_logging

log = configure_logging()

def _http_get_json(url: str, params: dict, timeout: float) -> Optional[dict]:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(full, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - any failure -> caller falls back to 0.0
        log.warning("open-meteo fetch failed (%s): %s", url, exc)
        return None

@lru_cache(maxsize=8192)
def _cached_rainfall(lat_r: float, lon_r: float, hour_iso: str) -> float:
    """Hourly precipitation (mm) for a rounded point + UTC hour. Cached per process so nearby
    incidents in the same hour share one HTTP call."""
    settings = get_settings()
    dt = datetime.strptime(hour_iso, "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)
    date_str = dt.strftime("%Y-%m-%d")
    age_days = (datetime.now(timezone.utc) - dt).days
    # The archive API lags ~5 days; use the forecast API (with past_days) for recent timestamps.
    if age_days > 5:
        data = _http_get_json(settings.weather_archive_url, {
            "latitude": lat_r, "longitude": lon_r,
            "start_date": date_str, "end_date": date_str,
            "hourly": "precipitation", "timezone": "UTC",
        }, settings.weather_timeout_seconds)
    else:
        past = min(max(age_days + 1, 1), 92)
        data = _http_get_json(settings.weather_forecast_url, {
            "latitude": lat_r, "longitude": lon_r,
            "hourly": "precipitation", "past_days": past, "forecast_days": 1,
            "timezone": "UTC",
        }, settings.weather_timeout_seconds)
    if not data:
        return 0.0
    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    precip = hourly.get("precipitation") or []
    target = dt.strftime("%Y-%m-%dT%H:00")
    for t, p in zip(times, precip):
        if t == target and p is not None:
            try:
                return float(p)
            except (TypeError, ValueError):
                return 0.0
    vals = [float(p) for p in precip if p is not None]
    return float(max(vals)) if vals else 0.0  # fall back to day's peak if exact hour absent

def rainfall_for(lat: Optional[float], lon: Optional[float],
                 dt_utc: Optional[datetime]) -> float:
    """Best-effort hourly precipitation (mm). Returns 0.0 when disabled, when inputs are
    missing, or on any error -- so the caller's behavior is unchanged in all those cases."""
    settings = get_settings()
    if not settings.weather_enabled:
        return 0.0
    if lat is None or lon is None or dt_utc is None:
        return 0.0
    try:
        return _cached_rainfall(round(float(lat), 2), round(float(lon), 2),
                                dt_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H"))
    except Exception as exc:  # noqa: BLE001
        log.warning("rainfall_for failed: %s", exc)
        return 0.0
