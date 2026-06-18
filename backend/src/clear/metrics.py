"""Correctness metrics: predicted-vs-actual clearance error + PSI drift (constraint 11)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

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

def _production_trained_at(conn, model: str) -> Optional[str]:
    """created_at of the current production version (model_registry), or None."""
    for m in db.get_models(conn, model):
        if m["stage"] == "production":
            return m["created_at"]
    return None

def holdout_clearance_error(conn) -> dict:
    """GENUINE out-of-sample MAE: only scores predictions on incidents INGESTED AFTER the
    production model was trained, so (unlike clearance_prediction_error) it is never in-sample."""
    trained_at = _production_trained_at(conn, "clearance")
    if trained_at is None:
        return {"mae_minutes": None, "n": 0, "note": "no production model registered"}
    rows = conn.execute(
        """SELECT p.output_json AS out, i.duration_minutes AS actual
           FROM predictions p JOIN incidents i ON p.event_id = i.event_id
           WHERE p.model = 'clearance' AND i.event_observed = 1 AND i.admin_close = 0
             AND i.duration_minutes IS NOT NULL AND i.ingested_at > %s""",
        (trained_at,),
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
        return {"mae_minutes": None, "n": 0, "note": "no out-of-sample resolved predictions yet"}
    mae = float(np.mean(errors))
    db.record_metric(conn, "clearance", "holdout_mae_minutes", mae)
    return {"mae_minutes": round(mae, 2), "n": len(errors), "since": trained_at}

def clearance_drift_psi(conn, recent_days: int = 14) -> dict:
    """PSI of recent vs older resolved-duration distributions. >= drift_psi_threshold => drift."""
    rows = conn.execute(
        """SELECT duration_minutes AS d, ingested_at AS ts FROM incidents
           WHERE event_observed = 1 AND admin_close = 0 AND duration_minutes IS NOT NULL"""
    ).fetchall()
    if len(rows) < 40:
        return {"psi": None, "n": len(rows), "note": "insufficient resolved history for PSI"}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=recent_days)).isoformat()
    recent = [float(r["d"]) for r in rows if (r["ts"] or "") >= cutoff]
    baseline = [float(r["d"]) for r in rows if (r["ts"] or "") < cutoff]
    if len(recent) < 20 or len(baseline) < 20:
        return {"psi": None, "n_recent": len(recent), "n_baseline": len(baseline),
                "note": "not enough rows in one window"}
    psi = population_stability_index(baseline, recent)
    db.record_metric(conn, "clearance", "duration_psi", psi)
    return {"psi": round(psi, 4), "n_recent": len(recent), "n_baseline": len(baseline)}
