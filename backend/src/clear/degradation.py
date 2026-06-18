"""Graceful degradation: last-known corridor risk + FIFO queue, labeled stale (constraint 13)."""
from __future__ import annotations

from typing import Any

from . import db
from .schema import PRIORITY_ORD

def stale_corridor_risk(conn) -> dict[str, Any]:
    """Return last persisted corridor risk, flagged stale, when the forecast model is down."""
    rows = db.get_last_corridor_risk(conn)
    for r in rows:
        r["stale"] = 1
    return {
        "degraded": True,
        "source": "last_known_corridor_risk",
        "note": "Forecast model unavailable; serving last-known risk (stale).",
        "corridors": rows,
    }

def fifo_queue(conn, limit: int = 50) -> dict[str, Any]:
    """Deterministic priority-FIFO fallback queue when dispatch optimization is unavailable."""
    active = db.get_active_incidents(conn)
    ordered = sorted(
        active,
        key=lambda r: (-PRIORITY_ORD.get(r.get("priority", "medium"), 1), r.get("start_ist") or ""),
    )
    queue = [
        {
            "rank": i + 1,
            "event_id": r["event_id"],
            "corridor": r.get("corridor"),
            "priority": r.get("priority"),
            "start_ist": r.get("start_ist"),
        }
        for i, r in enumerate(ordered[:limit])
    ]
    return {
        "degraded": True,
        "strategy": "fifo_priority",
        "note": "Dispatch optimizer unavailable; priority-FIFO queue (no optimization).",
        "queue": queue,
    }
