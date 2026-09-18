-- Shiftwork schema (program design S2, architecture S4 tables + engagement_config).
--
-- Slice 2 replaces the tracer's inline stub schema with this real DDL. Tables
-- whose owning slice has not landed yet are intentionally absent and are added
-- by that slice without renumbering: rotation_draws (Slice 7), assist_events
-- (Slice 12), mission_sources (Slice 15). The incidents table exists from the
-- tracer and is read by the board, but Slice 2 opens no incidents (Slice 5/7).

CREATE TABLE IF NOT EXISTS engagements (
    slug TEXT PRIMARY KEY,
    business_kind TEXT NOT NULL,
    display_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS engagement_config (
    slug TEXT PRIMARY KEY REFERENCES engagements(slug),
    business_kind TEXT NOT NULL,
    assist_level TEXT NOT NULL,
    allowed_assist_roles_json TEXT NOT NULL,
    total_assist_budget_per_shift INTEGER NOT NULL,
    enabled_check_families_json TEXT NOT NULL,
    attempt_limit INTEGER NOT NULL,
    rotation_group_size INTEGER NOT NULL
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
    storage_ref TEXT NOT NULL,
    files_json TEXT NOT NULL,
    contract_json TEXT NOT NULL,
    contract_catalog_hash TEXT NOT NULL,
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
    log_ref TEXT,
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
    engagement_slug TEXT NOT NULL REFERENCES engagements(slug),
    seq INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    cause_refs_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    synthetic INTEGER NOT NULL DEFAULT 1,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL,
    PRIMARY KEY (engagement_slug, seq)
);
