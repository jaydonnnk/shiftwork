-- Additive version 5 to version 6 migration. db.ensure_schema executes each
-- statement inside one BEGIN IMMEDIATE transaction and writes user_version last.
-- No existing column is copied, normalized, or replaced.

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

ALTER TABLE shifts ADD COLUMN opening_mode TEXT
    CHECK (opening_mode IN ('STANDARD', 'LEGACY_FIRST_CHOICE'));
ALTER TABLE draft_artifacts ADD COLUMN base_version_id TEXT
    REFERENCES artifact_versions(id);
ALTER TABLE artifact_versions ADD COLUMN restored_from_id TEXT
    REFERENCES artifact_versions(id);
ALTER TABLE artifact_versions ADD COLUMN authorship_json TEXT;

-- The DEFAULT labels preexisting rows without rewriting their old payloads.
-- New run inserts must provide purpose explicitly.
ALTER TABLE runs ADD COLUMN purpose TEXT NOT NULL DEFAULT 'LEGACY_OPERATION'
    CHECK (purpose IN ('EXPERIMENT', 'OPERATION', 'LEGACY_OPERATION'));
ALTER TABLE runs ADD COLUMN evidence_mode TEXT
    CHECK (evidence_mode IN ('RECORDED_INSPECTION', 'TRUSTED_LOCAL', 'ISOLATED_LIVE'));
ALTER TABLE runs ADD COLUMN context_id TEXT;
ALTER TABLE runs ADD COLUMN experiment_id TEXT;
ALTER TABLE runs ADD COLUMN trial_slot_id TEXT;
ALTER TABLE runs ADD COLUMN selection_id TEXT REFERENCES operating_selections(id);
ALTER TABLE runs ADD COLUMN client_request_id TEXT;

-- An old tokenfactory adapter value remains historical metadata, not proof of
-- isolated live execution; leave its evidence_mode unknown.
UPDATE runs SET evidence_mode = 'RECORDED_INSPECTION' WHERE adapter = 'recorded';
UPDATE runs SET evidence_mode = 'TRUSTED_LOCAL' WHERE adapter = 'local_process';
