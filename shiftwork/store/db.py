"""SQLite connection factory and the tracer schema.

Slice 2 replaces TRACER_SCHEMA with store/schema.sql and the migration path
described in the approved program design (S2).
"""

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

TRACER_SCHEMA = """
CREATE TABLE IF NOT EXISTS engagements (
    slug TEXT PRIMARY KEY,
    business_kind TEXT NOT NULL,
    display_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shifts (
    id TEXT PRIMARY KEY,
    engagement_slug TEXT NOT NULL REFERENCES engagements(slug),
    seq INTEGER NOT NULL,
    state TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    UNIQUE (engagement_slug, seq)
);

CREATE TABLE IF NOT EXISTS draft_artifacts (
    shift_id TEXT PRIMARY KEY REFERENCES shifts(id),
    files_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifact_versions (
    id TEXT PRIMARY KEY,
    shift_id TEXT NOT NULL REFERENCES shifts(id),
    parent_id TEXT REFERENCES artifact_versions(id),
    content_hash TEXT NOT NULL,
    contract_json TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    shift_id TEXT NOT NULL REFERENCES shifts(id),
    artifact_version_id TEXT NOT NULL REFERENCES artifact_versions(id),
    attempt_number INTEGER NOT NULL,
    state TEXT NOT NULL,
    adapter TEXT NOT NULL,
    failure_kind TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    UNIQUE (shift_id, attempt_number)
);

CREATE TABLE IF NOT EXISTS run_outputs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    request_ordinal INTEGER NOT NULL,
    request_text TEXT NOT NULL,
    http_status INTEGER,
    body BLOB NOT NULL,
    elapsed_ms INTEGER,
    transport_error TEXT,
    UNIQUE (run_id, request_ordinal)
);

CREATE TABLE IF NOT EXISTS check_results (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    check_id TEXT NOT NULL,
    verdict TEXT NOT NULL,
    observed_ref TEXT NOT NULL,
    expected_ref TEXT,
    reason_code TEXT
);

CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    engagement_slug TEXT NOT NULL REFERENCES engagements(slug),
    shift_id TEXT NOT NULL REFERENCES shifts(id),
    opening_run_id TEXT NOT NULL REFERENCES runs(id),
    failing_output_ref TEXT NOT NULL,
    check_result_id TEXT NOT NULL REFERENCES check_results(id),
    reason_code TEXT NOT NULL,
    opened_event_seq INTEGER NOT NULL,
    state TEXT NOT NULL,
    resolving_version_id TEXT REFERENCES artifact_versions(id),
    resolved_event_seq INTEGER
);

CREATE TABLE IF NOT EXISTS ledger_events (
    seq INTEGER PRIMARY KEY,
    engagement_slug TEXT NOT NULL REFERENCES engagements(slug),
    event_type TEXT NOT NULL,
    cause_refs_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    synthetic INTEGER NOT NULL DEFAULT 1,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may create and close a request-scoped
    # connection on different threadpool workers; connections are never shared.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(TRACER_SCHEMA)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.commit()
