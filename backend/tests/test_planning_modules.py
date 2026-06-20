"""Phase 4 planning modules: deterministic, no-DB unit tests."""
from __future__ import annotations

from clear.diversion import diversions_for
from clear.event_intel import apply_impact, known_event_types, multiplier_for
from clear.resource_planner import plan_resources

def test_multiplier_known_and_unknown() -> None:
	assert multiplier_for("ipl_match") == 2.3
	assert multiplier_for("IPL Match") == 2.3          # normalization
	assert multiplier_for("unknown_event") == 1.0      # default fallback
	assert multiplier_for(None) == 1.0
	assert "ipl_match" in known_event_types()

def test_apply_impact_scales_and_caps() -> None:
	out = apply_impact("ipl_match", base_minutes=100, base_risk=60)
	assert out["adjusted_clearance_minutes"] == 230.0
	assert out["adjusted_risk"] == 100.0               # 60*2.3=138 -> capped at 100
	assert apply_impact("normal")["multiplier"] == 1.0

def test_resource_planner_math() -> None:
	p = plan_resources(attendees=10000, road_closures=3, event_type="normal")
	assert p["officers"] == 20                          # ceil(10000/500)*1.0
	assert p["barricades"] == 12                         # 3*4
	assert p["tow_trucks"] == 1                          # ceil(10000/10000)
	assert plan_resources(0, 0)["officers"] == 0
	hi = plan_resources(10000, 0, "ipl_match")
	assert hi["officers"] > p["officers"]                # scaled up for high-impact

def test_diversion_lookup() -> None:
	d = diversions_for("MG Road")
	assert d["has_diversion"] is True
	assert d["alternates"][0]["rank"] == "primary"
	assert "delta_minutes" in d["alternates"][0]
	assert diversions_for("Nonexistent Road")["has_diversion"] is False
