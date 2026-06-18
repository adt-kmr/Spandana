"""Scheduled correctness monitoring: out-of-sample MAE + PSI drift, with an alert flag."""
from __future__ import annotations

from . import db
from .config import get_settings
from .logging_setup import configure_logging
from .metrics import clearance_drift_psi, holdout_clearance_error

log = configure_logging()

def drift_report() -> dict:
    settings = get_settings()
    db.init_db()
    conn = db.get_conn()
    try:
        mae = holdout_clearance_error(conn)
        psi = clearance_drift_psi(conn)
    finally:
        conn.close()
    psi_val = psi.get("psi")
    drift = psi_val is not None and psi_val >= settings.drift_psi_threshold
    if drift:
        log.warning("DRIFT DETECTED: clearance duration PSI=%.4f >= %.2f",
                    psi_val, settings.drift_psi_threshold)
    return {"holdout_mae": mae, "drift_psi": psi,
            "drift_detected": bool(drift), "psi_threshold": settings.drift_psi_threshold}

def main() -> None:
    print(drift_report())

if __name__ == "__main__":
    main()
