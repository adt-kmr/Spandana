"""Shared pytest fixtures for the CLEAR suite.

There was no conftest before this. Two existing test modules are pure unit tests (validation,
preprocessing) and need no database. The idempotency/dead-letter module talks to the DB; its
_use_temp_db helper still sets CLEAR_DB_PATH, a leftover from the old SQLite design that is now
IGNORED (Settings uses extra="ignore"), so those tests run against CLEAR_DATABASE_URL. To make
that safe and repeatable we:

  * refuse to run DB-backed tests against a non-local database, so a misconfigured .env pointing
    at Neon can never write test rows into production, and
  * truncate the incidents + dead_letter tables before and after each DB test.

A module is treated as DB-backed if it imports ingest_one (the hasattr check below); pure unit
modules are left completely untouched.
"""
from __future__ import annotations

import pytest

from clear.config import get_settings

# Tables the DB-backed tests write to; truncated around each such test for isolation.
_DB_TABLES = ("incidents", "dead_letter")

# Substrings that mark a database as REMOTE/managed -> never run destructive tests against it.
_REMOTE_MARKERS = ("neon.tech", "amazonaws.com", "rds.", "render.com", "supabase.co")
# Substrings that mark a database as safely LOCAL/disposable.
_LOCAL_MARKERS = ("localhost", "127.0.0.1", "@postgres")

def _database_is_local() -> bool:
    """True only when CLEAR_DATABASE_URL clearly points at a local/disposable database.

    Conservative by design: an explicit remote marker always wins (returns False); an unset or
    empty URL is treated as local (matches the localhost default in Settings); anything we don't
    recognize is treated as NOT local, so we fail safe by skipping rather than risk a real DB."""
    url = (get_settings().database_url or "").lower()
    if any(marker in url for marker in _REMOTE_MARKERS):
        return False
    if not url or any(marker in url for marker in _LOCAL_MARKERS):
        return True
    return False

def _truncate_db() -> None:
    """Wipe the test-written tables so each DB test starts from a clean slate (psycopg3)."""
    import clear.db as db

    conn = db.get_conn()
    try:
        conn.execute(f"TRUNCATE {', '.join(_DB_TABLES)} RESTART IDENTITY CASCADE")
        conn.commit()
    finally:
        conn.close()

@pytest.fixture(autouse=True)
def _db_isolation(request):
    """Around every DB-backed test: ensure schema, guard against remote DBs, truncate, run, then
    truncate again. Pure unit tests (no ingest_one import) skip this fixture entirely so they pay
    no DB cost."""
    is_db_test = hasattr(request.module, "ingest_one")
    if not is_db_test:
        yield
        return
    if not _database_is_local():
        pytest.skip(
            "Refusing to run DB tests against a non-local CLEAR_DATABASE_URL. Point it at a "
            "local/disposable Postgres (or unset it) to run these."
        )
    import clear.db as db

    db.init_db()
    _truncate_db()
    try:
        yield
    finally:
        _truncate_db()
