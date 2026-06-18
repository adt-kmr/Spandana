"""Dispatch decision-support: ranked suggestion vs FIFO/nearest baseline (constraint 7).
ZERO autonomous actuation. Emits a recommendation requiring explicit operator
confirmation; unit positions are clearly labeled assumed/external."""
from __future__ import annotations

from typing import Any

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
    return float(PRIORITY_ORD.get(str(incident.get("priority", "medium")).lower(), 1) + 1)


def _assign_min_travel(cost: list[list[float]]) -> dict[int, int]:
    """Optimal assignment of every ROW to a distinct COLUMN minimizing total cost. Requires
    n_rows <= n_cols. Uses OR-Tools when available, else a deterministic greedy fallback.
    Returns {row_index: col_index}."""
    n_rows = len(cost)
    n_cols = len(cost[0]) if cost else 0
    if n_rows == 0 or n_cols == 0:
        return {}
    if HAVE_ORTOOLS:
        solver = linear_sum_assignment.SimpleLinearSumAssignment()
        for r in range(n_rows):
            for c in range(n_cols):
                solver.add_arc_with_cost(r, c, int(round(cost[r][c] * 1000)))
        if solver.solve() == solver.OPTIMAL:
            return {r: solver.right_mate(r) for r in range(n_rows)}
    # Greedy fallback: cheapest feasible pair first, each row/col used once.
    ranked = sorted(
        ((cost[r][c], r, c) for r in range(n_rows) for c in range(n_cols)),
        key=lambda x: x[0],
    )
    used_r: set[int] = set()
    used_c: set[int] = set()
    out: dict[int, int] = {}
    for _, r, c in ranked:
        if r in used_r or c in used_c:
            continue
        out[r] = c
        used_r.add(r)
        used_c.add(c)
        if len(out) == n_rows:
            break
    return out


def _fifo_nearest(units: list[dict], incidents: list[dict]) -> dict[int, int]:
    """Baseline: incidents in arrival order each take the nearest still-free unit.
    Returns {incident_index: unit_index}."""
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
    """Rank a dispatch suggestion and compare it to the FIFO/nearest baseline.

    Selection + assignment are optimized jointly: the highest-impact incidents are served
    first, then matched to the BEST available units (minimum total travel time) -- so when
    there are more units than incidents the CLOSEST units are chosen, not the first ones.
    The baseline is FIFO/nearest over the SAME served incidents, so improvement_pct is an
    apples-to-apples comparison and is provably >= 0 (optimal total travel <= greedy)."""
    meta = {
        "requires_confirmation": True,   # gated behind operator confirmation (constraint 7)
        "autonomous_actuation": False,   # never actuates signals
        "unit_positions": "assumed/external (not authoritative)",
        "kind": "decision_support_recommendation",
    }
    units = [dict(u) for u in units]
    incidents = [
        inc for inc in incidents
        if inc.get("latitude") is not None and inc.get("longitude") is not None
    ]
    n = min(len(units), len(incidents))
    if n == 0:
        return {**meta, "method": "none", "assignments": [],
                "units_available": len(units), "incidents_considered": len(incidents),
                "incidents_served": 0, "optimized_total_eta_minutes": 0.0,
                "baseline_strategy": "fifo_nearest", "baseline_total_eta_minutes": 0.0,
                "improvement_pct": 0.0, "note": "no units or geolocated incidents available"}

    # Serve the n highest-impact incidents; keep arrival order for the FIFO baseline.
    served = sorted(incidents, key=_impact, reverse=True)[:n]

    # rows = served incidents (n) <= cols = units (U): every served incident gets its own unit
    # and the best U units are chosen when U > n. (fixes the old first-n-units suboptimality)
    cost = [[_travel_minutes(u, inc) for u in units] for inc in served]
    pairing = _assign_min_travel(cost)  # {incident_idx: unit_idx}
    method = "ortools_lsa" if HAVE_ORTOOLS else "greedy_min_travel"

    assignments = []
    opt_minutes = 0.0
    for ti, ui in pairing.items():
        tm = _travel_minutes(units[ui], served[ti])
        opt_minutes += tm
        assignments.append(
            {
                "unit_id": units[ui].get("unit_id", f"unit-{ui}"),
                "event_id": served[ti].get("event_id"),
                "priority": served[ti].get("priority"),
                "eta_minutes": round(tm, 1),
            }
        )
    assignments.sort(
        key=lambda a: (-PRIORITY_ORD.get(str(a["priority"] or "medium").lower(), 1),
                       a["eta_minutes"])
    )
    for i, a in enumerate(assignments):
        a["rank"] = i + 1

    # Baseline: FIFO/nearest over the SAME served incidents (apples-to-apples).
    base_pairing = _fifo_nearest(units, served)
    base_minutes = sum(_travel_minutes(units[ui], served[ti])
                       for ti, ui in base_pairing.items())
    improvement = ((base_minutes - opt_minutes) / base_minutes * 100.0) if base_minutes > 0 else 0.0

    return {
        **meta,
        "method": method,
        "assignments": assignments,
        "units_available": len(units),
        "incidents_considered": len(incidents),
        "incidents_served": n,
        "optimized_total_eta_minutes": round(opt_minutes, 1),
        "baseline_strategy": "fifo_nearest",
        "baseline_total_eta_minutes": round(base_minutes, 1),
        "improvement_pct": round(max(0.0, improvement), 1),
    }