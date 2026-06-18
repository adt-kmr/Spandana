"""One-time idempotent boot: schema + seed-ingest-if-empty + train-if-no-models.
Safe to run on every container start."""
from __future__ import annotations

import subprocess
import sys

from . import db
from .config import get_settings
from .logging_setup import configure_logging

log = configure_logging()

def _incident_count() -> int:
    conn = db.get_conn()
    try:
        return int(conn.execute("SELECT COUNT(*) AS c FROM incidents").fetchone()["c"])
    finally:
        conn.close()

def main() -> None:
    settings = get_settings()
    db.init_db()

    if _incident_count() == 0:
        from .ingestion import ingest_csv

        csv_path = settings.raw_data_dir / "incidents.csv"
        log.info("bootstrap: empty DB, ingesting %s", csv_path)
        log.info("bootstrap: ingest summary: %s", ingest_csv(str(csv_path)))
    else:
        log.info("bootstrap: incidents already present, skipping ingest")

    if not (settings.model_dir / "forecast.joblib").exists():
        log.info("bootstrap: no models on disk, training all")
        subprocess.run([sys.executable, "-m", "clear.train", "all"], check=True)
    else:
        log.info("bootstrap: models present, skipping training")

if __name__ == "__main__":
    main()
