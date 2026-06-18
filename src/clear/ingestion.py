"""Ingestion: validate -> idempotency -> store, bounded retries + dead-letter (constraints 8,10)."""
from __future__ import annotations

import argparse
import time
from typing import Any, Optional

from pydantic import ValidationError

from . import db
from .config import get_settings
from .logging_setup import configure_logging
from .preprocessing import (
    apply_column_aliases,
    normalize_columns,
    parse_utc,
    prepare_records,
    scrub_sentinels,
    to_ist,
)
from .schema import IncidentIn

log = configure_logging()

def _to_row(payload: IncidentIn) -> dict[str, Any]:
    prepared = prepare_records([payload.model_dump(mode="json")], as_of=None)
    p = prepared.iloc[0]
    start_ist = p["start_ist"]
    resolved_ist = to_ist(parse_utc(payload.resolved_datetime)) if payload.resolved_datetime else None
    closed_ist = to_ist(parse_utc(payload.closed_datetime)) if payload.closed_datetime else None
    return {
        "event_id": payload.event_id,
        "payload_json": payload.model_dump_json(),
        "event_cause": payload.event_cause,
        "corridor": payload.corridor,
        "priority": payload.priority,
        "requires_road_closure": int(payload.requires_road_closure),
        "start_ist": start_ist.isoformat() if start_ist is not None else None,
        "resolved_ist": resolved_ist.isoformat() if resolved_ist is not None else None,
        "closed_ist": closed_ist.isoformat() if closed_ist is not None else None,
        "duration_minutes": p["duration_minutes"],
        "event_observed": int(p["event_observed"]),
        "admin_close": int(p["admin_close"]),
        "junction_node": p["junction_node"],
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "status": payload.status,
    }

def ingest_one(conn, raw: dict, *, settings=None) -> dict:
    """Validate + idempotently store one raw incident. Bounded retries, then dead-letter."""
    settings = settings or get_settings()
    attempts = 0
    last_err: Optional[str] = None
    while attempts < settings.ingest_max_retries:
        attempts += 1
        try:
            payload = IncidentIn.model_validate(raw)
        except ValidationError as exc:
            # Schema errors are not transient: dead-letter immediately, no pointless retries.
            db.insert_dead_letter(conn, raw, f"validation: {exc.errors()}", attempts)
            return {"event_id": raw.get("event_id"), "written": False,
                    "dead_lettered": True, "attempts": attempts}
        try:
            written = db.insert_incident(conn, _to_row(payload))  # idempotent on event_id
            return {"event_id": payload.event_id, "written": written,
                    "duplicate": not written, "attempts": attempts}
        except Exception as exc:  # noqa: BLE001 - transient storage path -> backoff
            last_err = repr(exc)
            time.sleep(settings.ingest_backoff_base_seconds * (2 ** (attempts - 1)))
    db.insert_dead_letter(conn, raw, f"exhausted: {last_err}", attempts)
    return {"event_id": raw.get("event_id"), "written": False,
            "dead_lettered": True, "attempts": attempts}

def ingest_csv(csv_path: str) -> dict:
    import pandas as pd

    db.init_db()
    conn = db.get_conn()
    try:
        raw = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        raw = scrub_sentinels(apply_column_aliases(normalize_columns(raw)))
        written = dup = dead = 0
        for rec in raw.to_dict(orient="records"):
            res = ingest_one(conn, rec)
            written += int(res.get("written", False))
            dup += int(res.get("duplicate", False))
            dead += int(res.get("dead_lettered", False))
        return {"rows": len(raw), "written": written, "duplicates": dup, "dead_lettered": dead}
    finally:
        conn.close()

def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Ingest incidents CSV into the CLEAR store.")
    parser.add_argument("--csv", default=str(settings.raw_data_dir / "incidents.csv"))
    args = parser.parse_args()
    summary = ingest_csv(args.csv)
    log.info("ingest summary: %s", summary)
    print(summary)

if __name__ == "__main__":
    main()
