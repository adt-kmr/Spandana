"""Phase 4: Event intelligence — forward-looking congestion multipliers by event type.

No ML: a tunable lookup table (derive values from historical incident density) that scales a
baseline clearance estimate / corridor risk when a known event is scheduled. Imports nothing
from the model code, so it can never affect inference.
"""
from __future__ import annotations

from .config import get_settings

def _norm(event_type: str | None) -> str:
	return (event_type or "normal").strip().lower().replace(" ", "_").replace("-", "_")

def multiplier_for(event_type: str | None) -> float:
	settings = get_settings()
	return float(settings.event_multipliers.get(_norm(event_type), settings.event_multiplier_default))

def known_event_types() -> list[str]:
	return sorted(get_settings().event_multipliers.keys())

def apply_impact(
	event_type: str | None,
	*,
	base_minutes: float | None = None,
	base_risk: float | None = None,
) -> dict:
	"""Scale a baseline clearance estimate and/or corridor risk by the event multiplier.
	Returns the multiplier plus any scaled values supplied. Risk is capped at 100."""
	m = multiplier_for(event_type)
	out: dict = {"event_type": _norm(event_type), "multiplier": round(m, 3)}
	if base_minutes is not None:
		out["adjusted_clearance_minutes"] = round(float(base_minutes) * m, 1)
	if base_risk is not None:
		out["adjusted_risk"] = round(min(100.0, float(base_risk) * m), 2)
	return out
