"""SQLite connection factory and versioned schema bootstrap."""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
MIGRATION_V6_PATH = Path(__file__).with_name("migrations") / "v6.sql"
SCHEMA_VERSION = 6
# Slice 7 backfills pre-rotation runs with the refs the controller hardcoded then.
_LEGACY_RUN_BATCH = "thin.jsonl"
_LEGACY_RUN_SNAPSHOT = "bookshop_snapshot.json"


def connect(db_path: str | Path) -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may create and close a request-scoped
    # connection on different threadpool workers; connections are never shared.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _execute_statements(conn: sqlite3.Connection, script: str) -> None:
    """Run a plain SQL script without executescript's implicit COMMIT."""
    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            conn.execute(pending)
            pending = ""
    if pending.strip():
        raise RuntimeError("incomplete schema migration SQL")


def ensure_schema(conn: sqlite3.Connection) -> None:
    current = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if current not in (0, 2, 3, 4, 5, SCHEMA_VERSION):
        raise RuntimeError(
            f"database schema is at version {current}, this build expects {SCHEMA_VERSION}. "
            "This schema cannot be migrated in place; "
            "point SHIFTWORK_DB_PATH at a fresh file."
        )
    if current == SCHEMA_VERSION:
        return
    if conn.in_transaction:
        raise RuntimeError("commit pending writes before migrating the database schema")

    # Older pre-v5 fixtures relied on the idempotent table bootstrap before their
    # column upgrades. A v5 database must skip it: all v6 DDL belongs to the
    # transaction below, including the version marker.
    if current in (2, 3, 4):
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    conn.execute("BEGIN IMMEDIATE")
    try:
        if current == 0:
            _execute_statements(conn, SCHEMA_PATH.read_text(encoding="utf-8"))
        if current == 2:
            conn.execute("ALTER TABLE run_outputs ADD COLUMN log_ref TEXT")
        if current in (2, 3):
            # One transaction covers the DDL and the version marker, so an
            # interruption cannot leave the columns added under the old version.
            conn.execute("ALTER TABLE runs ADD COLUMN request_batch_ref TEXT")
            conn.execute("ALTER TABLE runs ADD COLUMN shop_snapshot_ref TEXT")
            conn.execute(
                "UPDATE runs SET request_batch_ref = ?, shop_snapshot_ref = ? "
                "WHERE request_batch_ref IS NULL",
                (_LEGACY_RUN_BATCH, _LEGACY_RUN_SNAPSHOT),
            )
        if current in (2, 3, 4):
            # Slice 9 evidence binding: legacy runs keep a NULL capture, so their
            # historical projections fall back to the path (best effort) instead of
            # claiming bytes the controller never recorded.
            conn.execute("ALTER TABLE runs ADD COLUMN shop_snapshot_bytes BLOB")
        if current in (2, 3, 4, 5):
            _execute_statements(conn, MIGRATION_V6_PATH.read_text(encoding="utf-8"))
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()
