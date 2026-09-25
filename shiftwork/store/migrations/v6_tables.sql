-- Idempotent v6 table completion. Gate 3 section 4 assigns these tables to
-- schema version 6, but they land with the slices that first use them, so a
-- database migrated by an earlier build is missing them while already reporting
-- user_version 6. db.ensure_schema therefore re-applies this script on every
-- open, including the already-v6 path.
--
-- Every statement here must stay idempotent. No ALTER TABLE, no UPDATE and no
-- destructive statement may be added: this script runs against databases that
-- already hold accepted historical evidence. Column changes and row backfills
-- belong in v6.sql, which only ever runs on the v5 and older paths.

-- Append-only: a revision never overwrites its parent, and the parent must
-- belong to the same shift. SQLite CHECK constraints cannot hold a subquery, so
-- the cross-row rule is a trigger rather than a constraint.
CREATE TABLE IF NOT EXISTS investigations (
    id TEXT PRIMARY KEY,
    shift_id TEXT NOT NULL REFERENCES shifts(id),
    source_run_id TEXT NOT NULL REFERENCES runs(id),
    source_request_ordinal INTEGER NOT NULL CHECK (source_request_ordinal >= 1),
    cause TEXT NOT NULL CHECK (cause != ''),
    falsifier TEXT NOT NULL CHECK (falsifier != ''),
    public_test TEXT NOT NULL CHECK (public_test != ''),
    revision_of_id TEXT REFERENCES investigations(id),
    authored_by TEXT NOT NULL DEFAULT 'learner' CHECK (authored_by = 'learner'),
    created_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS investigations_revision_same_shift
BEFORE INSERT ON investigations
FOR EACH ROW WHEN NEW.revision_of_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'an investigation revision must reference a parent in the same shift')
    WHERE NOT EXISTS (
        SELECT 1 FROM investigations
        WHERE id = NEW.revision_of_id AND shift_id = NEW.shift_id
    );
END;

CREATE TRIGGER IF NOT EXISTS investigations_no_update
BEFORE UPDATE ON investigations
BEGIN
    SELECT RAISE(ABORT, 'investigations are append-only');
END;

CREATE TRIGGER IF NOT EXISTS investigations_no_delete
BEFORE DELETE ON investigations
BEGIN
    SELECT RAISE(ABORT, 'investigations are append-only');
END;

-- content_hash UNIQUE makes a context immutable by identity: a changed frozen
-- input is a new context, never an edit. protected_reservation_id is an internal
-- controller reference and is never projected.
CREATE TABLE IF NOT EXISTS execution_contexts (
    id TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL DEFAULT 1 CHECK (schema_version = 1),
    engagement_slug TEXT NOT NULL REFERENCES engagements(slug),
    workloads_json TEXT NOT NULL CHECK (
        json_valid(workloads_json) AND
        (json_array_length(workloads_json) = 1 OR json_array_length(workloads_json) = 3)
    ),
    mission_bytes BLOB NOT NULL,
    mission_hash TEXT NOT NULL,
    public_data_bytes BLOB NOT NULL,
    public_data_hash TEXT NOT NULL,
    starting_business_state_json TEXT NOT NULL CHECK (json_valid(starting_business_state_json)),
    starting_business_state_hash TEXT NOT NULL,
    requirement_set_id TEXT NOT NULL,
    requirement_set_hash TEXT NOT NULL,
    visible_check_set_hash TEXT NOT NULL,
    protected_reservation_id TEXT,
    condition_json TEXT NOT NULL CHECK (json_valid(condition_json)),
    evaluator_version TEXT NOT NULL,
    reducer_version TEXT NOT NULL,
    executor_class TEXT NOT NULL CHECK (
        executor_class IN ('RECORDED_INSPECTION', 'TRUSTED_LOCAL', 'ISOLATED_LIVE')
    ),
    harness_hash TEXT NOT NULL,
    image_ref TEXT,
    service_model TEXT,
    service_model_settings_json TEXT NOT NULL CHECK (json_valid(service_model_settings_json)),
    resource_limits_json TEXT NOT NULL CHECK (json_valid(resource_limits_json)),
    created_at TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE
);

-- The exact outcome and its reason codes are controller-derived. No column here
-- can hold model-authored grading text.
CREATE TABLE IF NOT EXISTS task_assessments (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    request_id TEXT NOT NULL,
    request_ordinal INTEGER NOT NULL,
    task_id TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN (
        'USEFUL_COMPLETION', 'INCORRECT_OUTPUT', 'JUSTIFIED_REFUSAL',
        'JUSTIFIED_REFERRAL', 'JUSTIFIED_CLARIFICATION',
        'UNJUSTIFIED_REFUSAL', 'UNJUSTIFIED_REFERRAL',
        'UNJUSTIFIED_CLARIFICATION', 'MISSING_OUTPUT'
    )),
    mandatory_pass INTEGER NOT NULL CHECK (mandatory_pass IN (0, 1)),
    reason_codes_json TEXT NOT NULL CHECK (json_valid(reason_codes_json)),
    assessed_at TEXT NOT NULL,
    UNIQUE (run_id, request_ordinal, task_id)
);

-- raw_payload_ref stays internal; only the sanitized public payload is readable
-- through a projection.
CREATE TABLE IF NOT EXISTS execution_observations (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    request_ordinal INTEGER NOT NULL,
    ordinal INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN (
        'INTERPRETATION', 'TOOL_REQUEST', 'TOOL_RESULT',
        'INFERENCE_REQUEST', 'INFERENCE_RESULT', 'USAGE'
    )),
    public_payload_json TEXT NOT NULL CHECK (json_valid(public_payload_json)),
    raw_payload_ref TEXT NOT NULL,
    measured_at TEXT NOT NULL,
    UNIQUE (run_id, request_ordinal, ordinal)
);

CREATE TRIGGER IF NOT EXISTS execution_observations_no_update
BEFORE UPDATE ON execution_observations
BEGIN
    SELECT RAISE(ABORT, 'execution observations are append-only');
END;

CREATE TRIGGER IF NOT EXISTS execution_observations_no_delete
BEFORE DELETE ON execution_observations
BEGIN
    SELECT RAISE(ABORT, 'execution observations are append-only');
END;

-- One immutable row per terminal assessed run; check_results and
-- task_assessments hold the per-item detail.
CREATE TABLE IF NOT EXISTS run_assessments (
    run_id TEXT PRIMARY KEY REFERENCES runs(id),
    context_hash TEXT NOT NULL,
    complete_request_count INTEGER NOT NULL CHECK (complete_request_count >= 0),
    expected_request_count INTEGER NOT NULL CHECK (expected_request_count >= 0),
    mandatory_pass INTEGER NOT NULL CHECK (mandatory_pass IN (0, 1)),
    rule_version TEXT NOT NULL,
    assessed_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS run_assessments_no_update
BEFORE UPDATE ON run_assessments
BEGIN
    SELECT RAISE(ABORT, 'run assessments are immutable');
END;

CREATE TRIGGER IF NOT EXISTS run_assessments_no_delete
BEFORE DELETE ON run_assessments
BEGIN
    SELECT RAISE(ABORT, 'run assessments are immutable');
END;
