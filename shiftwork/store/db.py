"""SQLite connection factory and versioned schema bootstrap."""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
SCHEMA_VERSION = 3


def connect(db_path: str | Path) -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may create and close a request-scoped
    # connection on different threadpool workers; connections are never shared.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    current = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if current not in (0, 2, SCHEMA_VERSION):
        raise RuntimeError(
            f"database schema is at version {current}, this build expects {SCHEMA_VERSION}. "
            "This schema cannot be migrated in place; "
            "point SHIFTWORK_DB_PATH at a fresh file."
        )
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        if current == 2:
            conn.execute("ALTER TABLE run_outputs ADD COLUMN log_ref TEXT")
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
