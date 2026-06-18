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

# Rows are accumulated and flushed to Postgres in batches via executemany (ONE network
# round-trip per batch) instead of one INSERT per row. Over a remote Neon connection this is
# the difference between thousands of round-trips and a handful. Re-runs stay safe because the
# bulk insert still uses ON CONFLICT(event_id) DO NOTHING.
_COMMIT_BATCH = 1000

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

def _prepare_row(raw: dict) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Validate + shape one raw record. Returns (row, None) on success, or (None, error) when
    the record is invalid so the caller can dead-letter it. Validation errors are NOT transient,
    so there is no retry here."""
    try:
        payload = IncidentIn.model_validate(raw)
    except ValidationError as exc:
        return None, f"validation: {exc.errors()}"
    return _to_row(payload), None

def _flush_batch(conn, batch: list[dict[str, Any]], *, settings) -> tuple[int, int]:
    """Bulk-insert a batch with bounded retries + exponential backoff on transient storage
    errors. Returns (written, duplicates). On exhaustion every row in the batch is dead-lettered
    so nothing is silently dropped."""
    attempts = 0
    last_err: Optional[str] = None
    while attempts < settings.ingest_max_retries:
        attempts += 1
        try:
            return db.insert_incidents_batch(conn, batch, commit=True)
        except Exception as exc:  # noqa: BLE001 - transient storage path -> backoff
            last_err = repr(exc)
            conn.rollback()
            time.sleep(settings.ingest_backoff_base_seconds * (2 ** (attempts - 1)))
    for raw in batch:
        db.insert_dead_letter(conn, raw, f"exhausted: {last_err}", attempts, commit=False)
    conn.commit()
    return (0, 0)

def ingest_one(conn, raw: dict, *, settings=None, commit: bool = True) -> dict:
    """Validate + idempotently store ONE raw incident (used by the live /ingest and
    /citizen/report endpoints). Bulk CSV loads go through ingest_csv, which batches inserts.
    Bounded retries on transient storage errors, then dead-letter."""
    settings = settings or get_settings()
    row, err = _prepare_row(raw)
    if err is not None:
        # Schema errors are not transient: dead-letter immediately, no pointless retries.
        db.insert_dead_letter(conn, raw, err, 1, commit=commit)
        return {"event_id": raw.get("event_id"), "written": False,
                "dead_lettered": True, "attempts": 1}
    attempts = 0
    last_err: Optional[str] = None
    while attempts < settings.ingest_max_retries:
        attempts += 1
        try:
            written = db.insert_incident(conn, row, commit=commit)  # idempotent on event_id
            return {"event_id": row["event_id"], "written": written,
                    "duplicate": not written, "attempts": attempts}
        except Exception as exc:  # noqa: BLE001 - transient storage path -> backoff
            last_err = repr(exc)
            time.sleep(settings.ingest_backoff_base_seconds * (2 ** (attempts - 1)))
    db.insert_dead_letter(conn, raw, f"exhausted: {last_err}", attempts, commit=commit)
    return {"event_id": raw.get("event_id"), "written": False,
            "dead_lettered": True, "attempts": attempts}

def ingest_csv(csv_path: str) -> dict:
    import pandas as pd
    settings = get_settings()
    db.init_db()
    conn = db.get_conn()
    try:
        raw = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        raw = scrub_sentinels(apply_column_aliases(normalize_columns(raw)))
        written = dup = dead = 0
        batch: list[dict[str, Any]] = []
        for rec in raw.to_dict(orient="records"):
            row, err = _prepare_row(rec)
            if err is not None:
                db.insert_dead_letter(conn, rec, err, 1, commit=True)
                dead += 1
                continue
            batch.append(row)
            if len(batch) >= _COMMIT_BATCH:
                w, d = _flush_batch(conn, batch, settings=settings)
                written += w
                dup += d
                batch.clear()
        if batch:  # flush the final partial batch
            w, d = _flush_batch(conn, batch, settings=settings)
            written += w
            dup += d
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