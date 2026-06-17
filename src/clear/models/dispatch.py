"""Dispatch decision-support: ranked suggestion vs FIFO/nearest baseline (constraint 7).

ZERO autonomous actuation. Emits a recommendation requiring explicit operator
confirmation; unit positions are clearly labeled assumed/external.
"""
from __future__ import annotations

from typing import Any, Optional

from ..preprocessing import haversine_m
from ..schema import PRIORITY_ORD

try:
    from ortools.graph.python import linear_sum_assignment

    HAVE_ORTOOLS = True
except Exception:  # noqa: BLE001 - OR-Tools optional; deterministic greedy fallback used
    HAVE_ORTOOLS = False

_SPEED_KMPH = 25.0

def _travel_minutes(unit: dict, incident: dict) -> float:
    d = haversine_m(
        float(unit["lat"]), float(unit["lon"]),
        float(incident["latitude"]), float(incident["longitude"]),
    )
    return (d / 1000.0) / _SPEED_KMPH * 60.0

def _impact(incident: dict) -> float:
    return float(PRIORITY_ORD.get(incident.get("priority", "medium"), 1) + 1)

def _cost_matrix(units: list[dict], incidents: list[dict]) -> list[list[float]]:
    # Cost = travel time discounted by incident impact (reach high-impact incidents fast).
    return [[_travel_minutes(u, inc) / _impact(inc) for inc in incidents] for u in units]

def _assign_ortools(cost: list[list[float]]) -> Optional[dict[int, int]]:
    n = len(cost)
    assigner = linear_sum_assignment.SimpleLinearSumAssignment()
    for w in range(n):
        for t in range(n):
            assigner.add_arc_with_cost(w, t, int(round(cost[w][t] * 1000)))
    if assigner.solve() != assigner.OPTIMAL:
        return None
    return {w: assigner.right_mate(w) for w in range(n)}

def _assign_greedy(cost: list[list[float]]) -> dict[int, int]:
    n = len(cost)
    used: set[int] = set()
    pairing: dict[int, int] = {}
    for w in range(n):
        best_t, best_c = None, float("inf")
        for t in range(n):
            if t not in used and cost[w][t] < best_c:
                best_t, best_c = t, cost[w][t]
        pairing[w] = best_t if best_t is not None else 0
        used.add(pairing[w])
    return pairing

def _fifo_nearest(units: list[dict], incidents: list[dict]) -> dict[int, int]:
    """Baseline: incidents in arrival order each take the nearest still-free unit."""
    used: set[int] = set()
    pairing: dict[int, int] = {}
    for ti, inc in enumerate(incidents):
        best_u, best_t = None, float("inf")
        for ui, u in enumerate(units):
            if ui in used:
                continue
            tm = _travel_minutes(u, inc)
            if tm < best_t:
                best_u, best_t = ui, tm
        if best_u is not None:
            pairing[ti] = best_u
            used.add(best_u)
    return pairing

def suggest(units: list[dict], incidents: list[dict]) -> dict[str, Any]:
    """Rank a dispatch suggestion and compare it to the FIFO/nearest baseline."""
    meta = {
        "requires_confirmation": True,  # gated behind operator confirmation (constraint 7)
        "autonomous_actuation": False,  # never actuates signals
        "unit_positions": "assumed/external (not authoritative)",
        "kind": "decision_support_recommendation",
    }
    units = [dict(u) for u in units]
    incidents = sorted(incidents, key=_impact, reverse=True)
    n = min(len(units), len(incidents))
    if n == 0:
        return {**meta, "assignments": [], "baseline_strategy": "fifo_nearest",
                "improvement_pct": 0.0, "method": "none",
                "note": "no units or incidents available"}
    sel = incidents[:n]
    cost = _cost_matrix(units, sel)
    pairing, method = None, "greedy"
    if HAVE_ORTOOLS:
        pairing = _assign_ortools(cost)
        method = "ortools_lsa" if pairing is not None else "greedy"
    if pairing is None:
        pairing = _assign_greedy(cost)
    assignments = []
    opt_minutes = 0.0
    for ui in range(n):
        ti = pairing[ui]
        tm = _travel_minutes(units[ui], sel[ti])
        opt_minutes += tm
        assignments.append(
            {
                "unit_id": units[ui].get("unit_id", f"unit-{ui}"),
                "event_id": sel[ti].get("event_id"),
                "priority": sel[ti].get("priority"),
                "eta_minutes": round(tm, 1),
            }
        )
    assignments.sort(
        key=lambda a: (-PRIORITY_ORD.get(a["priority"] or "medium", 1), a["eta_minutes"])
    )
    for i, a in enumerate(assignments):
        a["rank"] = i + 1
    base_pairing = _fifo_nearest(units, sel)
    base_minutes = sum(_travel_minutes(units[ui], sel[ti]) for ti, ui in base_pairing.items())
    improvement = ((base_minutes - opt_minutes) / base_minutes * 100.0) if base_minutes > 0 else 0.0
    return {
        **meta,
        "method": method,
        "assignments": assignments,
        "optimized_total_eta_minutes": round(opt_minutes, 1),
        "baseline_strategy": "fifo_nearest",
        "baseline_total_eta_minutes": round(base_minutes, 1),
        "improvement_pct": round(improvement, 1),
    }
