"""Phase 4: Diversion generator — static alternate-corridor lookup with travel-time deltas.

Simplest graph-free routing: each primary corridor maps to ranked alternates, each tagged with
an average travel-time delta (minutes vs the blocked route). No ML, no live simulation.
"""
from __future__ import annotations

# corridor (lowercased) -> ordered alternates. delta_minutes = avg extra travel time vs the
# blocked primary. Extend this table as you map more corridors.
_DIVERSIONS: dict[str, list[dict]] = {
	"mg road": [
		{"corridor": "Brigade Road", "rank": "primary", "delta_minutes": 6},
		{"corridor": "Residency Road", "rank": "secondary", "delta_minutes": 11},
	],
	"residency road": [
		{"corridor": "Richmond Road", "rank": "primary", "delta_minutes": 7},
		{"corridor": "Brigade Road", "rank": "secondary", "delta_minutes": 12},
	],
	"mysore road": [
		{"corridor": "Magadi Road", "rank": "primary", "delta_minutes": 9},
		{"corridor": "Kanakapura Road", "rank": "secondary", "delta_minutes": 15},
	],
	"orr east": [
		{"corridor": "Sarjapur Road", "rank": "primary", "delta_minutes": 14},
		{"corridor": "Old Madras Road", "rank": "secondary", "delta_minutes": 19},
	],
}

def diversions_for(corridor: str) -> dict:
	alts = _DIVERSIONS.get((corridor or "").strip().lower(), [])
	return {
		"blocked_corridor": corridor,
		"has_diversion": bool(alts),
		"alternates": alts,
		"note": (
			"Static alternate corridors with average travel-time delta (minutes)."
			if alts else "No predefined diversion for this corridor."
		),
	}

def all_corridors_with_diversions() -> list[str]:
	return sorted(_DIVERSIONS.keys())
