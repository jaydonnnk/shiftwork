"""SQLite connection factory and schema bootstrap.

The real DDL lives in store/schema.sql (program design S2). Slice 2 replaces the
tracer's inline stub schema with that file and bumps SCHEMA_VERSION to 2.
"""

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
SCHEMA_VERSION = 2


def connect(db_path: str | Path) -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may create and close a request-scoped
    # connection on different threadpool workers; connections are never shared.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    current = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if current not in (0, SCHEMA_VERSION):
        raise RuntimeError(
            f"database schema is at version {current}, this build expects {SCHEMA_VERSION}. "
            "A stale database file from a different schema cannot be migrated in place; "
            "remove or point SHIFTWORK_DB_PATH at a fresh file."
        )
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
