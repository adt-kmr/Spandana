"""SQLite persistence. Mirrors the AWS flow locally: store -> infer -> serve."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .config import get_settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
  event_id TEXT PRIMARY KEY,
  payload_json TEXT NOT NULL,
  event_cause TEXT, corridor TEXT, priority TEXT,
  requires_road_closure INTEGER,
  start_ist TEXT, resolved_ist TEXT, closed_ist TEXT,
  duration_minutes REAL, event_observed INTEGER, admin_close INTEGER,
  junction_node TEXT, latitude REAL, longitude REAL,
  status TEXT, ingested_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_incidents_corridor ON incidents(corridor);
CREATE INDEX IF NOT EXISTS idx_incidents_start ON incidents(start_ist);
CREATE TABLE IF NOT EXISTS dead_letter (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  raw_json TEXT, error TEXT, attempts INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT, model TEXT, output_json TEXT, model_version TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS recommendations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT, payload_json TEXT, confirmed INTEGER DEFAULT 0,
  approval_event_json TEXT
);
CREATE TABLE IF NOT EXISTS corridor_risk (
  corridor TEXT PRIMARY KEY, as_of TEXT, risk REAL, horizon_hours INTEGER, stale INTEGER
);
CREATE TABLE IF NOT EXISTS model_registry (
  model TEXT, version TEXT, stage TEXT, path TEXT, metrics_json TEXT, created_at TEXT,
  PRIMARY KEY (model, version)
);
CREATE TABLE IF NOT EXISTS correctness_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model TEXT, metric TEXT, value REAL, created_at TEXT
);
CREATE TABLE IF NOT EXISTS junction_cache (
  raw_key TEXT PRIMARY KEY, node_id TEXT, node_lat REAL, node_lon REAL
);
"""

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def get_conn(path: Optional[Path] = None) -> sqlite3.Connection:
    settings = get_settings()
    settings.ensure_dirs()
    conn = sqlite3.connect(str(path or settings.db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db(conn: Optional[sqlite3.Connection] = None) -> None:
    own = conn is None
    conn = conn or get_conn()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        if own:
            conn.close()

def incident_exists(conn: sqlite3.Connection, event_id: str) -> bool:
    cur = conn.execute("SELECT 1 FROM incidents WHERE event_id = ?", (event_id,))
    return cur.fetchone() is not None

def insert_incident(conn: sqlite3.Connection, row: dict[str, Any]) -> bool:
    """Idempotent insert keyed on event_id (constraint 8). Returns True if newly written."""
    if incident_exists(conn, row["event_id"]):
        return False
    conn.execute(
        """INSERT INTO incidents (event_id, payload_json, event_cause, corridor, priority,
           requires_road_closure, start_ist, resolved_ist, closed_ist, duration_minutes,
           event_observed, admin_close, junction_node, latitude, longitude, status, ingested_at)
           VALUES (:event_id,:payload_json,:event_cause,:corridor,:priority,
           :requires_road_closure,:start_ist,:resolved_ist,:closed_ist,:duration_minutes,
           :event_observed,:admin_close,:junction_node,:latitude,:longitude,:status,:ingested_at)""",
        {**row, "ingested_at": _now()},
    )
    conn.commit()
    return True

def insert_dead_letter(conn: sqlite3.Connection, raw: dict, error: str, attempts: int) -> None:
    conn.execute(
        "INSERT INTO dead_letter (raw_json, error, attempts, created_at) VALUES (?,?,?,?)",
        (json.dumps(raw, default=str), error, attempts, _now()),
    )
    conn.commit()

def save_prediction(conn, event_id, model, output, version) -> None:
    conn.execute(
        "INSERT INTO predictions (event_id, model, output_json, model_version, created_at)"
        " VALUES (?,?,?,?,?)",
        (event_id, model, json.dumps(output, default=str), version, _now()),
    )
    conn.commit()

def save_recommendation(conn, payload: dict) -> int:
    cur = conn.execute(
        "INSERT INTO recommendations (created_at, payload_json) VALUES (?,?)",
        (_now(), json.dumps(payload, default=str)),
    )
    conn.commit()
    return int(cur.lastrowid)

def confirm_recommendation(conn, rec_id: int, approval_event: dict) -> bool:
    cur = conn.execute("SELECT 1 FROM recommendations WHERE id = ?", (rec_id,))
    if cur.fetchone() is None:
        return False
    conn.execute(
        "UPDATE recommendations SET confirmed = 1, approval_event_json = ? WHERE id = ?",
        (json.dumps(approval_event, default=str), rec_id),
    )
    conn.commit()
    return True

def upsert_corridor_risk(conn, corridor, risk, horizon, stale) -> None:
    conn.execute(
        """INSERT INTO corridor_risk (corridor, as_of, risk, horizon_hours, stale)
           VALUES (?,?,?,?,?)
           ON CONFLICT(corridor) DO UPDATE SET as_of=excluded.as_of, risk=excluded.risk,
           horizon_hours=excluded.horizon_hours, stale=excluded.stale""",
        (corridor, _now(), float(risk), int(horizon), int(bool(stale))),
    )
    conn.commit()

def get_last_corridor_risk(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM corridor_risk").fetchall()
    return [dict(r) for r in rows]

def register_model(conn, model, version, stage, path, metrics: dict) -> None:
    conn.execute(
        """INSERT INTO model_registry (model, version, stage, path, metrics_json, created_at)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(model, version) DO UPDATE SET stage=excluded.stage,
           path=excluded.path, metrics_json=excluded.metrics_json""",
        (model, version, stage, str(path), json.dumps(metrics, default=str), _now()),
    )
    conn.commit()

def set_model_stage(conn, model, version, stage) -> None:
    conn.execute(
        "UPDATE model_registry SET stage = ? WHERE model = ? AND version = ?",
        (stage, model, version),
    )
    conn.commit()

def get_models(conn, model: Optional[str] = None) -> list[dict]:
    if model:
        rows = conn.execute(
            "SELECT * FROM model_registry WHERE model = ? ORDER BY created_at DESC", (model,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM model_registry ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]

def record_metric(conn, model, metric, value) -> None:
    conn.execute(
        "INSERT INTO correctness_metrics (model, metric, value, created_at) VALUES (?,?,?,?)",
        (model, metric, float(value), _now()),
    )
    conn.commit()

def get_metrics(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT model, metric, value, created_at FROM correctness_metrics"
        " ORDER BY created_at DESC LIMIT 200"
    ).fetchall()
    return [dict(r) for r in rows]

def get_incidents(conn, limit: int = 500) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM incidents ORDER BY start_ist DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]

def get_incident(conn, event_id: str) -> Optional[dict]:
    row = conn.execute("SELECT * FROM incidents WHERE event_id = ?", (event_id,)).fetchone()
    return dict(row) if row else None

def get_active_incidents(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM incidents WHERE event_observed = 0 ORDER BY start_ist DESC LIMIT 200"
    ).fetchall()
    return [dict(r) for r in rows]

def recent_hourly_counts(conn, corridor: str, as_of_iso: str, hours: int) -> list[int]:
    """Counts per hour for the `hours` hours ending at as_of (IST strings, lexicographically sortable)."""
    from datetime import timedelta

    as_of = datetime.fromisoformat(as_of_iso)
    counts: list[int] = []
    for i in range(hours, 0, -1):
        lo = (as_of - timedelta(hours=i)).isoformat()
        hi = (as_of - timedelta(hours=i - 1)).isoformat()
        cur = conn.execute(
            "SELECT COUNT(*) AS c FROM incidents WHERE corridor = ? AND start_ist >= ? AND start_ist < ?",
            (corridor, lo, hi),
        )
        counts.append(int(cur.fetchone()["c"]))
    return counts

def sla_over_resolved(conn, threshold_minutes: int) -> dict:
    """SLA% computed ONLY over the resolved subset, labeled as such (constraint 19)."""
    row = conn.execute(
        """SELECT
             SUM(CASE WHEN duration_minutes <= ? THEN 1 ELSE 0 END) AS within,
             COUNT(*) AS resolved
           FROM incidents WHERE event_observed = 1 AND admin_close = 0""",
        (threshold_minutes,),
    ).fetchone()
    resolved = int(row["resolved"] or 0)
    within = int(row["within"] or 0)
    pct = (100.0 * within / resolved) if resolved else None
    return {
        "sla_pct": pct,
        "resolved_subset_size": resolved,
        "threshold_minutes": threshold_minutes,
        "note": "Computed only over physically-resolved incidents (admin-close excluded).",
    }
