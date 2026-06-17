"""Correctness metrics: predicted-vs-actual clearance error + PSI drift (constraint 11)."""
from __future__ import annotations

import json

import numpy as np

from . import db

def population_stability_index(expected, actual, bins: int = 10) -> float:
    """PSI between a reference and a current distribution. >0.2 signals meaningful drift."""
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)
    expected = expected[np.isfinite(expected)]
    actual = actual[np.isfinite(actual)]
    if expected.size == 0 or actual.size == 0:
        return 0.0
    quantiles = np.linspace(0, 100, bins + 1)
    edges = np.unique(np.percentile(expected, quantiles))
    if edges.size < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    e_hist, _ = np.histogram(expected, bins=edges)
    a_hist, _ = np.histogram(actual, bins=edges)
    e_pct = np.clip(e_hist / max(e_hist.sum(), 1), 1e-6, None)
    a_pct = np.clip(a_hist / max(a_hist.sum(), 1), 1e-6, None)
    return float(np.sum((a_pct - e_pct) * np.log(a_pct / e_pct)))

def clearance_prediction_error(conn) -> dict:
    """MAE between predicted median clearance and actual duration on resolved incidents."""
    rows = conn.execute(
        """SELECT p.output_json AS out, i.duration_minutes AS actual
           FROM predictions p JOIN incidents i ON p.event_id = i.event_id
           WHERE p.model = 'clearance' AND i.event_observed = 1
             AND i.admin_close = 0 AND i.duration_minutes IS NOT NULL"""
    ).fetchall()
    errors = []
    for r in rows:
        try:
            pred = json.loads(r["out"]).get("median_minutes")
            if pred is not None:
                errors.append(abs(float(pred) - float(r["actual"])))
        except (ValueError, TypeError):
            continue
    if not errors:
        return {"mae_minutes": None, "n": 0}
    mae = float(np.mean(errors))
    db.record_metric(conn, "clearance", "mae_minutes", mae)
    return {"mae_minutes": round(mae, 2), "n": len(errors)}
