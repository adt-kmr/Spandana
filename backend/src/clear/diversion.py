"""Phase 4: Diversion generator — computed alternate-corridor lookup via haversine distance.

Computes nearest alternate corridors dynamically using straight-line distance.
"""
from __future__ import annotations
import math
from .config import get_settings

AVG_DETOUR_SPEED_KMPH = 18.0  # representative Bengaluru arterial speed for delta estimates
MAX_ALTERNATES = 3

def _haversine_km(a: list[float], b: list[float]) -> float:
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def _display(name: str) -> str:
    return name.strip().title()

def diversions_for(corridor: str) -> dict:
    coords = get_settings().corridor_latlon
    key = (corridor or "").strip().lower()
    origin = coords.get(key)
    if origin is None:
        return {
            "blocked_corridor": corridor,
            "has_diversion": False,
            "alternates": [],
            "note": "No location data available for this corridor.",
        }
    ranked = sorted(
        ((name, _haversine_km(origin, ll)) for name, ll in coords.items() if name != key),
        key=lambda t: (t[1], t[0]),
    )[:MAX_ALTERNATES]
    alternates = [
        {
            "corridor": _display(name),
            "rank": "primary" if i == 0 else "secondary",
            "delta_minutes": max(1, round(dist_km / AVG_DETOUR_SPEED_KMPH * 60)),
        }
        for i, (name, dist_km) in enumerate(ranked)
    ]
    return {
        "blocked_corridor": corridor,
        "has_diversion": bool(alternates),
        "alternates": alternates,
        "note": (
            "Computed nearest alternate corridors by straight-line distance (haversine); "
            "travel-time deltas are estimates."
            if alternates else "No alternate corridors available."
        ),
    }

def all_corridors_with_diversions() -> list[str]:
    return sorted(_display(name) for name in get_settings().corridor_latlon.keys())
