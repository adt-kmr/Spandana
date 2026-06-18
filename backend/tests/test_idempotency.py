"""Idempotency + dead-letter tests: duplicate event_id never double-counts (constraints 8,10)."""
from __future__ import annotations

import clear.db as db
from clear.config import get_settings
from clear.ingestion import ingest_one

def _raw(event_id: str = "EVT-1") -> dict:
    return {
        "event_id": event_id,
        "start_datetime": "2024-01-01T00:00:00Z",
        "event_cause": "breakdown",
        "corridor": "Mysore Road",
        "latitude": 12.95,
        "longitude": 77.6,
        "priority": "high",
    }

def _use_temp_db(tmp_path, monkeypatch, name: str) -> None:
    monkeypatch.setenv("CLEAR_DB_PATH", str(tmp_path / name))
    get_settings.cache_clear()  # rebuild settings against the temp DB path

def test_duplicate_event_id_not_double_counted(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch, "dupe.db")
    db.init_db()
    conn = db.get_conn()
    try:
        first = ingest_one(conn, _raw())
        second = ingest_one(conn, _raw())
        assert first["written"] is True
        assert second["written"] is False and second["duplicate"] is True
        count = conn.execute("SELECT COUNT(*) AS c FROM incidents").fetchone()["c"]
        assert count == 1  # deduped on event_id
    finally:
        conn.close()
        get_settings.cache_clear()

def test_malformed_goes_to_dead_letter(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch, "dlq.db")
    db.init_db()
    conn = db.get_conn()
    try:
        res = ingest_one(conn, {"event_id": "BAD", "latitude": 12.9})  # missing start_datetime
        assert res["dead_lettered"] is True
        dl = conn.execute("SELECT COUNT(*) AS c FROM dead_letter").fetchone()["c"]
        assert dl == 1
    finally:
        conn.close()
        get_settings.cache_clear()
