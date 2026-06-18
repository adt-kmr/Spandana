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

def _to_row_from_prepared(payload: IncidentIn, p) -> dict[str, Any]:
    """Build a DB row from a validated payload and its ALREADY-prepared feature row `p` (one row
    of a prepare_records frame). The single-row and bulk paths both go through here so their
    output can never drift. resolved_ist/closed_ist come straight from the payload because
    prepare_records does not emit them - identical to the original _to_row."""
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

def _to_row(payload: IncidentIn) -> dict[str, Any]:
    """Single-row shaping (used by the live /ingest + /citizen/report path). Runs the feature
    pipeline for ONE record; bulk CSV loads use _prepare_rows_bulk to vectorize this."""
    prepared = prepare_records([payload.model_dump(mode="json")], as_of=None)
    return _to_row_from_prepared(payload, prepared.iloc[0])

def _prepare_row(raw: dict) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Validate + shape one raw record. Returns (row, None) on success, or (None, error) when
    the record is invalid so the caller can dead-letter it. Validation errors are NOT transient,
    so there is no retry here."""
    try:
        payload = IncidentIn.model_validate(raw)
    except ValidationError as exc:
        return None, f"validation: {exc.errors()}"
    return _to_row(payload), None

def _prepare_rows_bulk(
    records: list[dict],
) -> tuple[list[dict[str, Any]], list[tuple[dict, str]]]:
    """Vectorized shaping for bulk CSV loads. Validates every raw record, then runs the feature
    pipeline (prepare_records) ONCE over all valid payloads instead of once per row - this is
    the hot path that made seeding slow. Returns (rows, errors) where errors is [(raw, message)]
    for records that failed validation, so the caller can dead-letter them.

    Correctness: prepare_records builds its frame from the payloads in order and preserves that
    order, so prepared.iloc[i] lines up with payloads[i]; as_of=None matches the original
    per-row _to_row call exactly (unresolved rows stay right-censored). The resulting rows are
    therefore identical to looping _prepare_row per record, just far faster."""
    payloads: list[IncidentIn] = []
    errors: list[tuple[dict, str]] = []
    for raw in records:
        try:
            payloads.append(IncidentIn.model_validate(raw))
        except ValidationError as exc:
            errors.append((raw, f"validation: {exc.errors()}"))
    if not payloads:
        return [], errors
    prepared = prepare_records([p.model_dump(mode="json") for p in payloads], as_of=None)
    rows = [_to_row_from_prepared(p, prepared.iloc[i]) for i, p in enumerate(payloads)]
    return rows, errors

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

def _maybe_enrich_weather(raw: dict, settings) -> None:
    """Phase 1: fill rainfall_mm from Open-Meteo when enabled and not already supplied. Any
    failure leaves rainfall_mm untouched (-> schema default 0.0), so /ingest never blocks on
    weather and flag-off behavior is identical to today."""
    if not settings.weather_enabled:
        return
    existing = raw.get("rainfall_mm")
    try:
        if existing is not None and float(existing) > 0:
            return  # caller already supplied a real reading; don't override
    except (TypeError, ValueError):
        pass
    from .weather import rainfall_for  # lazy: no cost when disabled
    lat, lon = raw.get("latitude"), raw.get("longitude")
    try:
        lat_f = float(lat) if lat is not None else None
        lon_f = float(lon) if lon is not None else None
    except (TypeError, ValueError):
        return
    mm = rainfall_for(lat_f, lon_f, parse_utc(raw.get("start_datetime")))
    if mm and mm > 0:
        raw["rainfall_mm"] = mm

def ingest_one(conn, raw: dict, *, settings=None, commit: bool = True) -> dict:
    """Validate + idempotently store ONE raw incident (used by the live /ingest and
    /citizen/report endpoints). Bulk CSV loads go through ingest_csv, which batches inserts.
    Bounded retries on transient storage errors, then dead-letter."""
    settings = settings or get_settings()
    _maybe_enrich_weather(raw, settings)
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
        records = raw.to_dict(orient="records")
        # Validate + shape the WHOLE file in one vectorized pass (prepare_records runs once for
        # all rows, not once per row) before any DB writes.
        rows, errors = _prepare_rows_bulk(records)
        dead = 0
        for bad_raw, err in errors:
            db.insert_dead_letter(conn, bad_raw, err, 1, commit=False)
            dead += 1
        if dead:
            conn.commit()
        written = dup = 0
        for i in range(0, len(rows), _COMMIT_BATCH):  # flush in executemany batches
            w, d = _flush_batch(conn, rows[i : i + _COMMIT_BATCH], settings=settings)
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