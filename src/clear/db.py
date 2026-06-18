"""Postgres persistence (Neon). All SQL is isolated here; the rest of the app is
database-agnostic and only calls these helpers. Store -> infer -> serve."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import psycopg
from psycopg.rows import dict_row

from .config import get_settings

# Mirrors the original SQLite tables with Postgres types. Booleans are INTEGER (0/1) and
# timestamps are TEXT on purpose, to keep behavior identical to the SQLite version.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
  event_id TEXT PRIMARY KEY,
  payload_json TEXT NOT NULL,
  event_cause TEXT, corridor TEXT, priority TEXT,
  requires_road_closure INTEGER,
  start_ist TEXT, resolved_ist TEXT, closed_ist TEXT,
  duration_minutes DOUBLE PRECISION, event_observed INTEGER, admin_close INTEGER,
  junction_node TEXT, latitude DOUBLE PRECISION, longitude DOUBLE PRECISION,
  status TEXT, ingested_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_incidents_corridor ON incidents(corridor);
CREATE INDEX IF NOT EXISTS idx_incidents_start ON incidents(start_ist);
CREATE TABLE IF NOT EXISTS dead_letter (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  raw_json TEXT, error TEXT, attempts INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS predictions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id TEXT, model TEXT, output_json TEXT, model_version TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS recommendations (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  created_at TEXT, payload_json TEXT, confirmed INTEGER DEFAULT 0, approval_event_json TEXT
);
CREATE TABLE IF NOT EXISTS corridor_risk (
  corridor TEXT PRIMARY KEY, as_of TEXT, risk DOUBLE PRECISION, horizon_hours INTEGER, stale INTEGER
);
CREATE TABLE IF NOT EXISTS model_registry (
  model TEXT, version TEXT, stage TEXT, path TEXT, metrics_json TEXT, created_at TEXT,
  PRIMARY KEY (model, version)
);
CREATE TABLE IF NOT EXISTS correctness_metrics (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  model TEXT, metric TEXT, value DOUBLE PRECISION, created_at TEXT
);
CREATE TABLE IF NOT EXISTS junction_cache (
  raw_key TEXT PRIMARY KEY, node_id TEXT, node_lat DOUBLE PRECISION, node_lon DOUBLE PRECISION
);
"""

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def get_conn() -> psycopg.Connection:
    """Open a Neon/Postgres connection yielding dict rows (like sqlite3.Row).
    Point CLEAR_DATABASE_URL at the Neon *pooler* host; psycopg reads sslmode=require
    from the URL itself."""
    settings = get_settings()
    settings.ensure_dirs()
    return psycopg.connect(settings.database_url, row_factory=dict_row)

def init_db(conn: Optional[psycopg.Connection] = None) -> None:
    own = conn is None
    conn = conn or get_conn()
    try:
        with conn.cursor() as cur:
            for stmt in _SCHEMA.split(";"):
                if stmt.strip():
                    cur.execute(stmt)
        conn.commit()
    finally:
        if own:
            conn.close()

def incident_exists(conn: psycopg.Connection, event_id: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM incidents WHERE event_id = %s", (event_id,)
    ).fetchone() is not None

# Shared INSERT used by BOTH the single-row and bulk paths so the column list and placeholders
# can never drift apart. Named placeholders (%(name)s) let executemany reuse one prepared
# statement across every row in a batch.
_INSERT_INCIDENT_SQL = """INSERT INTO incidents (event_id, payload_json, event_cause, corridor,
    priority, requires_road_closure, start_ist, resolved_ist, closed_ist, duration_minutes,
    event_observed, admin_close, junction_node, latitude, longitude, status, ingested_at)
    VALUES (%(event_id)s,%(payload_json)s,%(event_cause)s,%(corridor)s,%(priority)s,
    %(requires_road_closure)s,%(start_ist)s,%(resolved_ist)s,%(closed_ist)s,
    %(duration_minutes)s,%(event_observed)s,%(admin_close)s,%(junction_node)s,
    %(latitude)s,%(longitude)s,%(status)s,%(ingested_at)s)
    ON CONFLICT (event_id) DO NOTHING"""

def insert_incident(conn: psycopg.Connection, row: dict[str, Any], *, commit: bool = True) -> bool:
    """Idempotent insert keyed on event_id (constraint 8). Returns True if newly written.
    ON CONFLICT DO NOTHING makes a duplicate a single round-trip; rowcount is 1 for a new
    write, 0 for a skip. commit=False lets bulk ingest batch many rows per transaction."""
    cur = conn.execute(_INSERT_INCIDENT_SQL, {**row, "ingested_at": _now()})
    if commit:
        conn.commit()
    return cur.rowcount > 0

def insert_incidents_batch(
    conn: psycopg.Connection, rows: list[dict[str, Any]], *, commit: bool = True
) -> tuple[int, int]:
    """Bulk-insert many incidents in ~ONE network round-trip via executemany.

    Inserting row-by-row over the network to Neon costs one round-trip PER row (~8k just to
    seed the dataset), which is why the first seed crawled. psycopg3's executemany() pipelines
    the whole batch to the server in a single exchange, collapsing those round-trips into one.

    Returns (written, duplicates). Because ON CONFLICT DO NOTHING silently swallows duplicates,
    we pre-resolve which event_ids already exist (one round-trip) and de-dup within the batch so
    the written/duplicate counts stay exact. Insertion order is preserved."""
    if not rows:
        return (0, 0)
    ids = [r["event_id"] for r in rows]
    existing = {
        rec["event_id"]
        for rec in conn.execute(
            "SELECT event_id FROM incidents WHERE event_id = ANY(%s)", (ids,)
        ).fetchall()
    }
    new_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in rows:
        eid = r["event_id"]
        if eid in existing or eid in seen:
            continue
        seen.add(eid)
        new_rows.append(r)
    if new_rows:
        ts = _now()
        params = [{**r, "ingested_at": ts} for r in new_rows]
        # executemany() uses libpq pipeline mode internally (psycopg 3.1+): all rows are sent
        # before results are read, so the batch costs ~one round-trip instead of len(rows).
        with conn.cursor() as cur:
            cur.executemany(_INSERT_INCIDENT_SQL, params)
    if commit:
        conn.commit()
    return (len(new_rows), len(rows) - len(new_rows))

def insert_dead_letter(conn, raw, error, attempts, *, commit: bool = True) -> None:
    conn.execute(
        "INSERT INTO dead_letter (raw_json, error, attempts, created_at) VALUES (%s,%s,%s,%s)",
        (json.dumps(raw, default=str), error, attempts, _now()),
    )
    if commit:
        conn.commit()

def save_prediction(conn, event_id, model, output, version) -> None:
    conn.execute(
        "INSERT INTO predictions (event_id, model, output_json, model_version, created_at)"
        " VALUES (%s,%s,%s,%s,%s)",
        (event_id, model, json.dumps(output, default=str), version, _now()),
    )
    conn.commit()

def save_recommendation(conn, payload: dict) -> int:
    rec_id = conn.execute(
        "INSERT INTO recommendations (created_at, payload_json) VALUES (%s,%s) RETURNING id",
        (_now(), json.dumps(payload, default=str)),
    ).fetchone()["id"]
    conn.commit()
    return int(rec_id)

def confirm_recommendation(conn, rec_id, approval_event) -> bool:
    if conn.execute(
        "SELECT 1 FROM recommendations WHERE id = %s", (rec_id,)
    ).fetchone() is None:
        return False
    conn.execute(
        "UPDATE recommendations SET confirmed = 1, approval_event_json = %s WHERE id = %s",
        (json.dumps(approval_event, default=str), rec_id),
    )
    conn.commit()
    return True

def upsert_corridor_risk(conn, corridor, risk, horizon, stale) -> None:
    conn.execute(
        """INSERT INTO corridor_risk (corridor, as_of, risk, horizon_hours, stale)
           VALUES (%s,%s,%s,%s,%s)
           ON CONFLICT (corridor) DO UPDATE SET as_of = EXCLUDED.as_of, risk = EXCLUDED.risk,
           horizon_hours = EXCLUDED.horizon_hours, stale = EXCLUDED.stale""",
        (corridor, _now(), float(risk), int(horizon), int(bool(stale))),
    )
    conn.commit()

def get_last_corridor_risk(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM corridor_risk").fetchall()]

def register_model(conn, model, version, stage, path, metrics) -> None:
    conn.execute(
        """INSERT INTO model_registry (model, version, stage, path, metrics_json, created_at)
           VALUES (%s,%s,%s,%s,%s,%s)
           ON CONFLICT (model, version) DO UPDATE SET stage = EXCLUDED.stage,
           path = EXCLUDED.path, metrics_json = EXCLUDED.metrics_json""",
        (model, version, stage, str(path), json.dumps(metrics, default=str), _now()),
    )
    conn.commit()

def set_model_stage(conn, model, version, stage) -> None:
    conn.execute(
        "UPDATE model_registry SET stage = %s WHERE model = %s AND version = %s",
        (stage, model, version),
    )
    conn.commit()

def get_models(conn, model=None) -> list[dict]:
    if model:
        rows = conn.execute(
            "SELECT * FROM model_registry WHERE model = %s ORDER BY created_at DESC", (model,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM model_registry ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

def record_metric(conn, model, metric, value) -> None:
    conn.execute(
        "INSERT INTO correctness_metrics (model, metric, value, created_at) VALUES (%s,%s,%s,%s)",
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
        "SELECT * FROM incidents ORDER BY start_ist DESC LIMIT %s", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]

def get_incident(conn, event_id: str) -> Optional[dict]:
    row = conn.execute("SELECT * FROM incidents WHERE event_id = %s", (event_id,)).fetchone()
    return dict(row) if row else None

def get_active_incidents(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM incidents WHERE event_observed = 0 ORDER BY start_ist DESC LIMIT 200"
    ).fetchall()
    return [dict(r) for r in rows]

def recent_hourly_counts(conn, corridor, as_of_iso, hours) -> list[int]:
    """Counts per hour for the `hours` hours ending at as_of (IST ISO strings, sortable)."""
    as_of = datetime.fromisoformat(as_of_iso)
    counts: list[int] = []
    for i in range(hours, 0, -1):
        lo = (as_of - timedelta(hours=i)).isoformat()
        hi = (as_of - timedelta(hours=i - 1)).isoformat()
        c = conn.execute(
            "SELECT COUNT(*) AS c FROM incidents WHERE corridor = %s AND start_ist >= %s"
            " AND start_ist < %s",
            (corridor, lo, hi),
        ).fetchone()["c"]
        counts.append(int(c))
    return counts

def sla_over_resolved(conn, threshold_minutes: int) -> dict:
    """SLA% computed ONLY over the physically-resolved subset, labeled as such (constraint 19)."""
    row = conn.execute(
        """SELECT
             SUM(CASE WHEN duration_minutes <= %s THEN 1 ELSE 0 END) AS within,
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