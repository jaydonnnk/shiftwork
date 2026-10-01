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

-- Reserve before calling the model. PENDING and FAILED calls consume the same
-- budget as COMPLETE calls; a crash can never refund a provider attempt.
CREATE TABLE IF NOT EXISTS assist_events (
    id TEXT PRIMARY KEY,
    shift_id TEXT NOT NULL REFERENCES shifts(id),
    investigation_id TEXT NOT NULL REFERENCES investigations(id),
    role TEXT NOT NULL CHECK (role IN ('HINT', 'DIAGNOSIS', 'PATCH_PROPOSAL')),
    model_id TEXT NOT NULL,
    reported_model_id TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    elapsed_ms INTEGER,
    request_text TEXT NOT NULL,
    response_text TEXT NOT NULL DEFAULT '',
    proposed_patch TEXT,
    accepted INTEGER CHECK (accepted IN (0, 1)),
    state TEXT NOT NULL CHECK (state IN ('PENDING', 'COMPLETE', 'FAILED')),
    failure_code TEXT,
    client_request_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS assist_events_shift ON assist_events(shift_id);
CREATE TRIGGER IF NOT EXISTS assist_events_owned_investigation
BEFORE INSERT ON assist_events
BEGIN
    SELECT RAISE(ABORT, 'assist must cite an investigation in the same shift')
    WHERE NOT EXISTS (
        SELECT 1 FROM investigations
        WHERE id = NEW.investigation_id AND shift_id = NEW.shift_id
    );
END;
CREATE TRIGGER IF NOT EXISTS assist_events_no_delete
BEFORE DELETE ON assist_events BEGIN
    SELECT RAISE(ABORT, 'assist events cannot be deleted');
END;
CREATE TRIGGER IF NOT EXISTS assist_events_guard_update
BEFORE UPDATE ON assist_events BEGIN
    SELECT RAISE(ABORT, 'assist event history is immutable except completion and decision')
    WHERE NOT (
        OLD.id IS NEW.id AND OLD.shift_id IS NEW.shift_id AND
        OLD.investigation_id IS NEW.investigation_id AND OLD.role IS NEW.role AND
        OLD.model_id IS NEW.model_id AND OLD.request_text IS NEW.request_text AND
        OLD.client_request_id IS NEW.client_request_id AND OLD.created_at IS NEW.created_at AND
        ((OLD.state = 'PENDING' AND NEW.state IN ('COMPLETE', 'FAILED') AND
          NEW.accepted IS NULL) OR
         (OLD.state = 'COMPLETE' AND NEW.state = 'COMPLETE' AND
          OLD.accepted IS NULL AND NEW.accepted IN (0, 1) AND
          OLD.response_text IS NEW.response_text AND OLD.proposed_patch IS NEW.proposed_patch AND
          OLD.failure_code IS NEW.failure_code AND OLD.reported_model_id IS NEW.reported_model_id AND
          OLD.input_tokens IS NEW.input_tokens AND OLD.output_tokens IS NEW.output_tokens AND
          OLD.elapsed_ms IS NEW.elapsed_ms))
    );
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

-- Slice 15: one qualifying comparison reserves its two candidates, three paired
-- public workloads, three never-exposed protected variants and six ordered trial
-- slots before any result exists. Slots are immutable except for their run
-- binding and terminal state; nothing here has a delete path.
CREATE TABLE IF NOT EXISTS trial_slots (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiments(id),
    pair_ordinal INTEGER NOT NULL CHECK (pair_ordinal BETWEEN 1 AND 3),
    execution_ordinal INTEGER NOT NULL CHECK (execution_ordinal BETWEEN 1 AND 6),
    candidate_label TEXT NOT NULL CHECK (candidate_label IN ('A', 'B')),
    artifact_version_id TEXT NOT NULL REFERENCES artifact_versions(id),
    workload_id TEXT NOT NULL,
    request_batch_hash TEXT NOT NULL,
    request_count INTEGER NOT NULL CHECK (request_count BETWEEN 1 AND 4),
    executed_request_count INTEGER NOT NULL CHECK (executed_request_count BETWEEN 1 AND 5 AND executed_request_count IN (request_count, request_count + 1)),
    protected_variant_refs_json TEXT NOT NULL CHECK (json_valid(protected_variant_refs_json)),
    run_id TEXT REFERENCES runs(id),
    state TEXT NOT NULL CHECK (state IN ('RESERVED', 'RUNNING', 'COMPLETE', 'FAILED')),
    UNIQUE (experiment_id, pair_ordinal, candidate_label),
    UNIQUE (experiment_id, execution_ordinal),
    UNIQUE (run_id)
);

CREATE TRIGGER IF NOT EXISTS trial_slots_guard_update
BEFORE UPDATE ON trial_slots
WHEN NEW.id IS NOT OLD.id
    OR NEW.experiment_id IS NOT OLD.experiment_id
    OR NEW.pair_ordinal IS NOT OLD.pair_ordinal
    OR NEW.execution_ordinal IS NOT OLD.execution_ordinal
    OR NEW.candidate_label IS NOT OLD.candidate_label
    OR NEW.artifact_version_id IS NOT OLD.artifact_version_id
    OR NEW.workload_id IS NOT OLD.workload_id
    OR NEW.request_batch_hash IS NOT OLD.request_batch_hash
    OR NEW.request_count IS NOT OLD.request_count
    OR NEW.executed_request_count IS NOT OLD.executed_request_count
    OR NEW.protected_variant_refs_json IS NOT OLD.protected_variant_refs_json
BEGIN
    SELECT RAISE(ABORT, 'trial slots are immutable except for their run and state');
END;

CREATE TRIGGER IF NOT EXISTS trial_slots_no_delete
BEFORE DELETE ON trial_slots
BEGIN
    SELECT RAISE(ABORT, 'trial slots are never deleted');
END;

-- One comparison- or operation-scoped reservation. Invalidation is a state
-- change on this row; the row and its items are never deleted (ADR 0001).
CREATE TABLE IF NOT EXISTS exposure_reservations (
    id TEXT PRIMARY KEY,
    engagement_slug TEXT NOT NULL REFERENCES engagements(slug),
    scope TEXT NOT NULL CHECK (scope IN ('comparison', 'operation')),
    experiment_id TEXT REFERENCES experiments(id),
    state TEXT NOT NULL CHECK (state IN ('ACTIVE', 'INVALIDATED')),
    created_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS exposure_reservations_no_delete
BEFORE DELETE ON exposure_reservations
BEGIN
    SELECT RAISE(ABORT, 'exposure reservations are never deleted');
END;

-- One reserved protected variant. The engagement-wide unique key makes an
-- exposed identity unreusable in the same family and cycle, and one item binds
-- both candidate slots of exactly one pair.
CREATE TABLE IF NOT EXISTS exposure_items (
    id TEXT PRIMARY KEY,
    reservation_id TEXT NOT NULL REFERENCES exposure_reservations(id),
    engagement_slug TEXT NOT NULL REFERENCES engagements(slug),
    family TEXT NOT NULL,
    cycle INTEGER NOT NULL,
    variant_ref TEXT NOT NULL,
    pair_ordinal INTEGER NOT NULL CHECK (pair_ordinal BETWEEN 1 AND 3),
    state TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active', 'invalidated')),
    drawn_at TEXT NOT NULL,
    UNIQUE (engagement_slug, family, cycle, variant_ref),
    UNIQUE (reservation_id, family, pair_ordinal)
);

CREATE TRIGGER IF NOT EXISTS exposure_items_no_delete
BEFORE DELETE ON exposure_items
BEGIN
    SELECT RAISE(ABORT, 'exposure items are never deleted');
END;

-- Restricted, immutable contents behind a comparison exposure identity. A
-- later edit to the authored family file cannot change what was reserved.
CREATE TABLE IF NOT EXISTS protected_case_snapshots (
    exposure_item_id TEXT PRIMARY KEY REFERENCES exposure_items(id),
    variant_ref TEXT NOT NULL,
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
    payload_sha256 TEXT NOT NULL,
    resolved_state_bytes BLOB NOT NULL,
    resolved_state_sha256 TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS protected_case_snapshots_no_update
BEFORE UPDATE ON protected_case_snapshots
BEGIN
    SELECT RAISE(ABORT, 'protected case snapshots are immutable');
END;

CREATE TRIGGER IF NOT EXISTS protected_case_snapshots_no_delete
BEFORE DELETE ON protected_case_snapshots
BEGIN
    SELECT RAISE(ABORT, 'protected case snapshots are never deleted');
END;

-- Historical runs have no frozen operation context. The partial constraint
-- governs S18 pivot operations without rewriting accepted legacy evidence.
CREATE UNIQUE INDEX IF NOT EXISTS one_finalized_pivot_operation_per_shift
ON runs(shift_id) WHERE purpose = 'OPERATION' AND context_id IS NOT NULL AND state = 'FINALIZED';

CREATE TRIGGER IF NOT EXISTS one_inflight_pivot_operation_insert
BEFORE INSERT ON runs
WHEN NEW.purpose = 'OPERATION' AND NEW.context_id IS NOT NULL
 AND NEW.state NOT IN ('FINALIZED', 'FAILED')
BEGIN
    SELECT RAISE(ABORT, 'operation already in flight for engagement')
    WHERE EXISTS (
        SELECT 1 FROM runs r JOIN shifts s ON s.id = r.shift_id
        JOIN shifts target ON target.id = NEW.shift_id
        WHERE s.engagement_slug = target.engagement_slug
          AND r.purpose = 'OPERATION' AND r.state NOT IN ('FINALIZED', 'FAILED')
    );
END;

-- Replace the earlier state-only trigger when completing an existing v6 database.
-- The completion migration runs in one transaction, so no write can slip between
-- the drop and replacement.
DROP TRIGGER IF EXISTS one_inflight_pivot_operation_update;
CREATE TRIGGER one_inflight_pivot_operation_update
BEFORE UPDATE OF state, purpose, context_id, shift_id ON runs
WHEN NEW.purpose = 'OPERATION' AND NEW.context_id IS NOT NULL
 AND NEW.state NOT IN ('FINALIZED', 'FAILED')
BEGIN
    SELECT RAISE(ABORT, 'operation already in flight for engagement')
    WHERE EXISTS (
        SELECT 1 FROM runs r JOIN shifts s ON s.id = r.shift_id
        JOIN shifts target ON target.id = NEW.shift_id
        WHERE s.engagement_slug = target.engagement_slug AND r.id != NEW.id
          AND r.purpose = 'OPERATION' AND r.state NOT IN ('FINALIZED', 'FAILED')
    );
END;

-- Slice 20: a later-condition comparison's reference to the already-observed
-- operational context it re-tests under. Created here, not in v6.sql, so an
-- already-v6 database gains it on reopen (Gate 2 S4, Gate 3 S6.7).
CREATE TABLE IF NOT EXISTS experiment_observed_contexts (
    experiment_id TEXT PRIMARY KEY REFERENCES experiments(id),
    observed_run_id TEXT NOT NULL REFERENCES runs(id),
    observed_context_id TEXT NOT NULL REFERENCES execution_contexts(id),
    created_at TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS experiment_observed_contexts_no_update
BEFORE UPDATE ON experiment_observed_contexts
BEGIN
    SELECT RAISE(ABORT, 'an observed-context reference is never rewritten');
END;

CREATE TRIGGER IF NOT EXISTS experiment_observed_contexts_no_delete
BEFORE DELETE ON experiment_observed_contexts
BEGIN
    SELECT RAISE(ABORT, 'an observed-context reference is never deleted');
END;
