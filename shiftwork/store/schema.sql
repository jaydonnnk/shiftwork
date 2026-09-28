-- Shiftwork fresh schema, version 6. Existing version 5 databases use
-- migrations/v6.sql instead; their historical columns are never re-created.
--
-- Slice 2 replaces the tracer's inline stub schema with this real DDL. Gate 3 S4
-- assigns every pivot table to version 6, but a table's DDL lands with the slice
-- that first uses it, in migrations/v6_tables.sql. db.ensure_schema applies that
-- script on every open, including an already-v6 database, so a database migrated
-- by an earlier build gains the tables a later slice added. Keep the pivot tables
-- there rather than duplicating them here: two copies of one constraint drift
-- silently, and only the migration copy is exercised against real v5 evidence.
--
-- The incidents table exists from the tracer and is read by the board, but
-- Slice 2 opens no incidents (Slice 5/7). assist_events landed in Slice 14 and
-- trial_slots, exposure_reservations and exposure_items landed in Slice 15, all
-- in migrations/v6_tables.sql. Still awaiting its owning slice:
-- idempotency_records.

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
    opening_mode TEXT CHECK (opening_mode IN ('STANDARD', 'LEGACY_FIRST_CHOICE')),
    UNIQUE (engagement_slug, seq)
);

CREATE TABLE IF NOT EXISTS draft_artifacts (
    shift_id TEXT PRIMARY KEY REFERENCES shifts(id),
    files_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    base_version_id TEXT REFERENCES artifact_versions(id)
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
    created_at TEXT NOT NULL,
    restored_from_id TEXT REFERENCES artifact_versions(id),
    authorship_json TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    shift_id TEXT NOT NULL REFERENCES shifts(id),
    artifact_version_id TEXT NOT NULL REFERENCES artifact_versions(id),
    request_batch_ref TEXT NOT NULL,
    shop_snapshot_ref TEXT NOT NULL,
    shop_snapshot_bytes BLOB,
    attempt_number INTEGER NOT NULL,
    state TEXT NOT NULL,
    adapter TEXT NOT NULL,
    failure_kind TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    purpose TEXT NOT NULL DEFAULT 'OPERATION'
        CHECK (purpose IN ('EXPERIMENT', 'OPERATION', 'LEGACY_OPERATION')),
    evidence_mode TEXT
        CHECK (evidence_mode IN ('RECORDED_INSPECTION', 'TRUSTED_LOCAL', 'ISOLATED_LIVE')),
    context_id TEXT,
    experiment_id TEXT,
    trial_slot_id TEXT,
    selection_id TEXT REFERENCES operating_selections(id),
    client_request_id TEXT,
    UNIQUE (shift_id, attempt_number)
);

CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    shift_id TEXT NOT NULL REFERENCES shifts(id),
    kind TEXT NOT NULL CHECK (
        kind IN ('DIAGNOSTIC', 'QUALIFYING_COMPARISON', 'LATER_CONDITION_COMPARISON')
    ),
    investigation_id TEXT,
    candidates_json TEXT NOT NULL CHECK (
        json_valid(candidates_json) AND
        ((kind = 'DIAGNOSTIC' AND json_array_length(candidates_json) = 1) OR
         (kind != 'DIAGNOSTIC' AND json_array_length(candidates_json) = 2))
    ),
    declared_treatment TEXT NOT NULL,
    context_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    trial_count_per_candidate INTEGER NOT NULL CHECK (trial_count_per_candidate IN (1, 3)),
    state TEXT NOT NULL CHECK (state IN ('PLANNED', 'RUNNING', 'FINALIZED', 'FAILED', 'INVALIDATED')),
    client_request_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS operating_selections (
    id TEXT PRIMARY KEY,
    engagement_slug TEXT NOT NULL REFERENCES engagements(slug),
    shift_id TEXT NOT NULL REFERENCES shifts(id),
    kind TEXT NOT NULL CHECK (kind IN ('STARTER_BASELINE', 'LEARNER_CHOICE')),
    selected_version_id TEXT NOT NULL REFERENCES artifact_versions(id),
    selected_content_hash TEXT NOT NULL,
    comparison_id TEXT REFERENCES experiments(id),
    retained_alternative_version_id TEXT REFERENCES artifact_versions(id),
    rationale TEXT NOT NULL,
    requirement_set_hash TEXT NOT NULL,
    prior_selection_id TEXT REFERENCES operating_selections(id),
    state TEXT NOT NULL CHECK (state IN ('VALID', 'INVALIDATED')),
    client_request_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
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

CREATE TABLE IF NOT EXISTS rotation_draws (
    id TEXT PRIMARY KEY,
    engagement_slug TEXT NOT NULL REFERENCES engagements(slug),
    family TEXT NOT NULL,
    variant_ref TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES runs(id),
    cycle INTEGER NOT NULL,
    drawn_at TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'active',
    UNIQUE (engagement_slug, variant_ref),
    UNIQUE (run_id, family)
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
