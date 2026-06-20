"""Phase 5: Weather Union live-rain client (real-time hyperlocal OBSERVATION, not forecast).

rain_intensity (mm/min) + rain_accumulation (mm since 12 AM IST) within ~2 km of Weather Union's
nearest device. Dependency-free (urllib only) so it adds nothing to the build. EVERY failure path
returns None (or the last cached value flagged stale) so callers degrade silently and the rest of
the API is unaffected. Disabled by default (CLEAR_RAIN_CLOG_ENABLED off) => byte-for-byte the
current backend.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Optional

from .config import get_settings
from .logging_setup import configure_logging

log = configure_logging()

# process-local cache: key -> (expires_at_epoch, value_dict)
_CACHE: dict[str, tuple[float, dict]] = {}

def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

def _http_get_json(url: str, params: dict, api_key: str, timeout: float) -> Optional[dict]:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        full,
        headers={"x-zomato-api-key": api_key, "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - any failure -> caller falls back
        log.warning("weather-union fetch failed (%s): %s", url, exc)
        return None

def rain_at(lat: Optional[float], lon: Optional[float]) -> Optional[dict]:
    """Live rain at a lat/long. Returns
    {intensity, accumulation, temperature, humidity, device_type, stale} or None when disabled,
    key missing, inputs missing, point unsupported, or on any error. On a transient upstream miss
    it serves the last cached value with stale=True if one exists."""
    settings = get_settings()
    if not settings.rain_clog_enabled or not settings.weather_union_api_key:
        return None
    if lat is None or lon is None:
        return None
    key = f"{round(float(lat), 3)},{round(float(lon), 3)}"
    now = time.time()
    hit = _CACHE.get(key)
    if hit and hit[0] > now:
        return {**hit[1], "stale": False}
    data = _http_get_json(
        f"{settings.weather_union_base_url}/get_weather_data",
        {"latitude": float(lat), "longitude": float(lon)},
        settings.weather_union_api_key,
        settings.weather_union_timeout_seconds,
    )
    wd = (data or {}).get("locality_weather_data") or {}
    if not wd:
        # transient/unsupported point: reuse last good reading if we have one, else give up
        return {**hit[1], "stale": True} if hit else None
    value = {
        "intensity": _num(wd.get("rain_intensity")),
        "accumulation": _num(wd.get("rain_accumulation")),
        "temperature": _num(wd.get("temperature")),
        "humidity": _num(wd.get("humidity")),
        "device_type": data.get("device_type"),
    }
    _CACHE[key] = (now + settings.rain_clog_cache_seconds, value)
    return {**value, "stale": False}
