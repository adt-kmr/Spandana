"""Phase 4: Resource planner — operational heuristics (no ML).

Translates an event's scale into a staffing/equipment plan using simple ratios from config:
officers per N attendees, barricades per road closure, one tow truck per M attendees. Officers
are scaled up for high-impact events via the shared event multiplier. Pure function, no I/O.
"""
from __future__ import annotations

import math

from .config import get_settings
from .event_intel import multiplier_for

def plan_resources(attendees: int, road_closures: int = 0, event_type: str | None = None) -> dict:
	settings = get_settings()
	attendees = max(0, int(attendees))
	road_closures = max(0, int(road_closures))
	base_officers = math.ceil(attendees / settings.officers_per_attendees) if attendees else 0
	m = multiplier_for(event_type)
	return {
		"attendees": attendees,
		"road_closures": road_closures,
		"event_type": (event_type or "normal"),
		"multiplier": round(m, 3),
		"officers": math.ceil(base_officers * m),
		"officers_base": base_officers,
		"barricades": road_closures * settings.barricades_per_closure,
		"tow_trucks": math.ceil(attendees / settings.tow_per_attendees) if attendees else 0,
		"note": (
			f"Heuristic plan (no ML): 1 officer / {settings.officers_per_attendees} attendees, "
			f"{settings.barricades_per_closure} barricades / closure, "
			f"1 tow / {settings.tow_per_attendees} attendees; officers scaled by event multiplier."
		),
	}
