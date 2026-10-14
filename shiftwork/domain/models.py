"""Durable domain models (program design S3.2).

Slice 2 carries the real contract, catalog, structured-response and ledger-draft
types the thin vertical path needs. Later slices added rotation and assist
models; the operator-only curation models live in ``shiftwork.curation``
(Slice 26) outside the runtime application.
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

type JsonValue = str | int | bool | None | list[JsonValue] | dict[str, JsonValue]
type Id = str
type Slug = str

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class RunState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    CAPTURED = "CAPTURED"
    FINALIZED = "FINALIZED"
    FAILED = "FAILED"


class RunPurpose(StrEnum):
    EXPERIMENT = "EXPERIMENT"
    OPERATION = "OPERATION"
    LEGACY_OPERATION = "LEGACY_OPERATION"


class EvidenceMode(StrEnum):
    RECORDED_INSPECTION = "RECORDED_INSPECTION"
    TRUSTED_LOCAL = "TRUSTED_LOCAL"
    ISOLATED_LIVE = "ISOLATED_LIVE"


class ShiftOpeningMode(StrEnum):
    STANDARD = "STANDARD"
    LEGACY_FIRST_CHOICE = "LEGACY_FIRST_CHOICE"


class DrawState(StrEnum):
    """Rotation-draw lifecycle. A compromised group is retired by this state change,
    never by deletion (ADR 0001); a refill cannot clear it (program design S7.1)."""

    ACTIVE = "active"
    INVALIDATED = "invalidated"


class ExecutorFailure(StrEnum):
    PROVISION_FAILED = "PROVISION_FAILED"
    SERVICE_UNREACHABLE = "SERVICE_UNREACHABLE"
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
    CAPTURE_TRUNCATED = "CAPTURE_TRUNCATED"
    CAPTURE_NON_UTF8 = "CAPTURE_NON_UTF8"
    SANDBOX_TERMINATED = "SANDBOX_TERMINATED"
    INTERNAL = "INTERNAL"


class ReasonCode(StrEnum):
    INVENTED_FACT = "INVENTED_FACT"
    STALE_BEYOND_RULE = "STALE_BEYOND_RULE"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    WRONG_ACTION = "WRONG_ACTION"
    UNSAFE_CONTINUATION = "UNSAFE_CONTINUATION"
    DUPLICATE_COMMITMENT = "DUPLICATE_COMMITMENT"
    LATENCY_BUDGET = "LATENCY_BUDGET"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    REGRESSION = "REGRESSION"
    # Gate 3 S3.3 task-aware vocabulary, added by Slice 11. CONTEXT_DRIFT,
    # EXPOSURE_INVALIDATED and GATEWAY_LIMIT_EXCEEDED from the same list arrive
    # with the slices that can produce them.
    WRONG_ENTITY = "WRONG_ENTITY"
    REQUIRED_TASK_MISSING = "REQUIRED_TASK_MISSING"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    INVALID_COMMITMENT = "INVALID_COMMITMENT"
    UNJUSTIFIED_REFUSAL = "UNJUSTIFIED_REFUSAL"
    UNJUSTIFIED_REFERRAL = "UNJUSTIFIED_REFERRAL"
    UNJUSTIFIED_CLARIFICATION = "UNJUSTIFIED_CLARIFICATION"
    MISSING_EXECUTION_EVIDENCE = "MISSING_EXECUTION_EVIDENCE"


class LedgerEventType(StrEnum):
    SALE_COMPLETED = "SALE_COMPLETED"
    REFUND_REQUIRED = "REFUND_REQUIRED"
    BOOKING_COMMITTED = "BOOKING_COMMITTED"
    ESCALATION_TO_HUMAN = "ESCALATION_TO_HUMAN"
    INCIDENT_OPENED = "INCIDENT_OPENED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"
    BACKLOG_RECORDED = "BACKLOG_RECORDED"
    LIMIT_DECLARED = "LIMIT_DECLARED"
    OWNER_ASSIGNED = "OWNER_ASSIGNED"
    SLA_CLOCK_STARTED = "SLA_CLOCK_STARTED"
    HANDOFF_ESCALATED = "HANDOFF_ESCALATED"
    ROLLOUT_APPROVED = "ROLLOUT_APPROVED"
    HANDOVER_DECLARED = "HANDOVER_DECLARED"
    COUNTER_FOLLOWUP_RECORDED = "COUNTER_FOLLOWUP_RECORDED"


class IncidentState(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    CLOSED_UNRESOLVED = "CLOSED_UNRESOLVED"


class ContractDimension(StrEnum):
    MUST_NEVER = "MUST_NEVER"
    STANCE = "STANCE"
    CLARIFY_WHEN = "CLARIFY_WHEN"
    ESCALATE_WHEN = "ESCALATE_WHEN"
    MAY_ESTIMATE_WHEN = "MAY_ESTIMATE_WHEN"
    REPEAT_REQUEST_RULE = "REPEAT_REQUEST_RULE"


class ContractOptionId(StrEnum):
    NEVER_INVENT_PRICE_STOCK_POLICY = "NEVER_INVENT_PRICE_STOCK_POLICY"
    VERIFY_EXACT_CLAIMS_NOW = "VERIFY_EXACT_CLAIMS_NOW"
    USE_NEWEST_RECORD_WITH_AGE = "USE_NEWEST_RECORD_WITH_AGE"
    HARD_CHECK_HIGH_RISK_ONLY = "HARD_CHECK_HIGH_RISK_ONLY"
    CLARIFY_TITLE_OR_EDITION = "CLARIFY_TITLE_OR_EDITION"
    CLARIFY_ANY_UNCERTAIN_FACT = "CLARIFY_ANY_UNCERTAIN_FACT"
    CLARIFY_HIGH_RISK_FACT = "CLARIFY_HIGH_RISK_FACT"
    NEVER_UNSAFE_CONTINUATION = "NEVER_UNSAFE_CONTINUATION"
    ESTIMATE_ONLY_WITH_EVIDENCE = "ESTIMATE_ONLY_WITH_EVIDENCE"
    ESCALATE_UNSAFE_REPAIR = "ESCALATE_UNSAFE_REPAIR"
    DEDUPLICATE_BOOKING_BY_REQUEST_ID = "DEDUPLICATE_BOOKING_BY_REQUEST_ID"
    NEVER_UNOWNED_OR_DUPLICATE_SIGNAL = "NEVER_UNOWNED_OR_DUPLICATE_SIGNAL"
    REVIEW_AMBIGUOUS_SIGNAL = "REVIEW_AMBIGUOUS_SIGNAL"
    DEDUPLICATE_PIPELINE_BY_SIGNAL = "DEDUPLICATE_PIPELINE_BY_SIGNAL"


class ContractOption(BaseModel):
    """Immutable once its catalog version has been used (program design S3.2)."""

    model_config = _FROZEN

    id: ContractOptionId
    dimension: ContractDimension
    learner_label: str
    evaluator_rule_id: str


class ContractCatalog(BaseModel):
    model_config = _FROZEN

    engagement_slug: Slug
    version: int
    content_hash: str
    required_dimensions: tuple[ContractDimension, ...]
    options: tuple[ContractOption, ...]
    frozen_at: datetime


class ContractParams(BaseModel):
    """Frozen into an ArtifactVersion; drives parameterized checks (S3.2)."""

    model_config = _FROZEN

    catalog_version: int
    must_never: tuple[ContractOptionId, ...]
    selections: dict[ContractDimension, ContractOptionId]
    response_time_limit_ms: Literal[1000, 3000, 8000]
    declared_limits: tuple[str, ...]


class Claim(BaseModel):
    """Typed claim the evaluator compares deterministically. Floats forbidden."""

    model_config = _FROZEN

    kind: Literal["price", "stock", "availability", "policy_answer", "booking", "none"]
    value: JsonValue


class ServiceResponse(BaseModel):
    """The structured response contract; captured bytes must validate (S3.2)."""

    model_config = _FROZEN

    action: Literal["answer", "ask", "decline", "escalate"]
    claims: tuple[Claim, ...]
    evidence_refs: tuple[str, ...]
    record_age_ms: int | None = None


class Shift(BaseModel):
    model_config = _FROZEN

    id: Id
    engagement_slug: Slug
    seq: int
    state: Literal["open", "closed"]
    opened_at: datetime
    closed_at: datetime | None = None
    opening_mode: ShiftOpeningMode | None = None
    operation_allowed: bool = False


class ArtifactVersion(BaseModel):
    """Immutable, content-hashed snapshot (program design S3.2).

    ``content_hash`` covers the frozen ``files`` + ``contract`` (ContractParams) +
    ``contract_catalog_hash``. ``files`` and ``storage_ref`` are internal: they are
    never exposed in a public projection (S3.9).
    """

    model_config = _FROZEN

    id: Id
    shift_id: Id
    parent_id: Id | None
    restored_from_id: Id | None = None
    content_hash: str
    storage_ref: str
    files: dict[str, str]
    contract: ContractParams
    contract_catalog_hash: str
    created_by: Literal["template", "learner"]
    created_at: datetime


class Run(BaseModel):
    model_config = _FROZEN

    id: Id
    shift_id: Id
    artifact_version_id: Id
    request_batch_ref: str
    shop_snapshot_ref: str
    attempt_number: int
    state: RunState
    adapter: Literal["local_process", "recorded", "tokenfactory"]
    failure_kind: ExecutorFailure | None = None
    started_at: datetime
    ended_at: datetime | None = None
    purpose: RunPurpose = RunPurpose.OPERATION
    evidence_mode: EvidenceMode | None = None
    selection_id: Id | None = None
    context_id: Id | None = None
    experiment_id: Id | None = None
    trial_slot_id: Id | None = None


class OperatingSelection(BaseModel):
    model_config = _FROZEN

    id: Id
    engagement_slug: Slug
    shift_id: Id
    kind: Literal["STARTER_BASELINE", "LEARNER_CHOICE"]
    selected_version_id: Id
    selected_content_hash: str
    comparison_id: Id | None = None
    retained_alternative_version_id: Id | None = None
    rationale: str
    requirement_set_hash: str
    prior_selection_id: Id | None = None
    state: Literal["VALID", "INVALIDATED"]
    client_request_id: str
    created_at: datetime


class SelectionRequest(BaseModel):
    model_config = _FROZEN

    comparison_id: Id
    selected_version_id: Id
    rationale: str = Field(min_length=1, max_length=2000)
    expected_prior_selection_id: Id | None
    client_request_id: str = Field(min_length=1)


class Investigation(BaseModel):
    """The learner's own diagnosis, appended before any diagnostic help (S3.2).

    Append-only: a revision writes a new row carrying ``revision_of_id`` and
    leaves the parent intact, so the original cause and falsifier stay readable
    as the history of what the learner actually believed.
    """

    model_config = _FROZEN

    id: Id
    shift_id: Id
    source_run_id: Id
    source_request_ordinal: int
    cause: str
    falsifier: str
    public_test: str
    revision_of_id: Id | None = None
    authored_by: Literal["learner"] = "learner"
    created_at: datetime


class InvestigationRequest(BaseModel):
    model_config = _FROZEN

    source_run_id: Id
    source_request_ordinal: int
    cause: str
    falsifier: str
    public_test: str
    revision_of_id: Id | None = None
    client_request_id: str


class AssistRole(StrEnum):
    HINT = "HINT"
    DIAGNOSIS = "DIAGNOSIS"
    PATCH_PROPOSAL = "PATCH_PROPOSAL"


class AssistEvent(BaseModel):
    model_config = _FROZEN

    id: Id
    shift_id: Id
    investigation_id: Id
    role: AssistRole
    model_id: str
    reported_model_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    elapsed_ms: int | None = None
    request_text: str
    response_text: str
    proposed_patch: str | None = None
    accepted: bool | None = None
    state: Literal["PENDING", "COMPLETE", "FAILED"]
    failure_code: str | None = None
    client_request_id: str
    created_at: datetime


class ObservationKind(StrEnum):
    INTERPRETATION = "INTERPRETATION"
    TOOL_REQUEST = "TOOL_REQUEST"
    TOOL_RESULT = "TOOL_RESULT"
    INFERENCE_REQUEST = "INFERENCE_REQUEST"
    INFERENCE_RESULT = "INFERENCE_RESULT"
    USAGE = "USAGE"


class ExecutionObservation(BaseModel):
    """One sanitized observation from a run (program design S3.5).

    ``raw_payload_ref`` is internal: only ``public_payload_json`` is projectable.
    Observations describe what the service reported or what the controller
    verified, and their ``source`` field keeps those two apart. They are never
    model reasoning presented as fact.
    """

    model_config = _FROZEN

    id: Id
    run_id: Id
    request_ordinal: int
    ordinal: int
    kind: ObservationKind
    public_payload_json: dict[str, JsonValue]
    raw_payload_ref: str
    measured_at: datetime


class ContextCondition(BaseModel):
    model_config = _FROZEN

    id: Id
    kind: Literal["normal", "data_update", "dependency_unavailable"]
    public_label: str
    exact_bytes_base64: str
    content_hash: str


class FrozenWorkload(BaseModel):
    """One reviewed request batch, frozen as exact bytes plus its parsed shape."""

    model_config = _FROZEN

    id: Id
    ordinal: int
    request_batch_bytes_base64: str
    request_batch_hash: str
    request_specs_bytes_base64: str
    request_specs_hash: str
    request_count: int


class ExecutionContext(BaseModel):
    """Everything an assessment depends on, frozen and content-hashed (S3.1).

    A mutable path or a current fixture cannot reconstruct old evidence, so the
    public mission, request batch and public state are retained as bytes with
    their hashes. ``protected_reservation_id`` is an internal controller reference
    and is never projected.
    """

    model_config = _FROZEN

    id: Id
    schema_version: Literal[1] = 1
    engagement_slug: Slug
    workloads: tuple[FrozenWorkload, ...]
    mission_bytes_base64: str
    mission_hash: str
    public_data_bytes_base64: str
    public_data_hash: str
    starting_business_state_json: dict[str, JsonValue]
    starting_business_state_hash: str
    requirement_set_id: Id
    requirement_set_hash: str
    visible_check_set_hash: str
    protected_reservation_id: Id | None = None
    condition: ContextCondition
    evaluator_version: str
    reducer_version: str
    executor_class: EvidenceMode
    harness_hash: str
    image_ref: str | None = None
    service_model: str | None = None
    service_model_settings_json: dict[str, JsonValue]
    resource_limits_json: dict[str, JsonValue]
    created_at: datetime
    content_hash: str


class RunAssessment(BaseModel):
    """One immutable summary row per terminal assessed run (program design S3.4)."""

    model_config = _FROZEN

    run_id: Id
    context_hash: str
    complete_request_count: int
    expected_request_count: int
    mandatory_pass: bool
    rule_version: str
    assessed_at: datetime


class OperationalAssessment(RunAssessment):
    """A selected operational assessment, never constructible from a trial."""

    purpose: Literal[RunPurpose.OPERATION] = RunPurpose.OPERATION
    selection_id: Id


class ReplayReport(BaseModel):
    """One read-only semantic replay of a finalized operational assessment (S19).

    Differences compare the re-derived checks and ledger-event drafts against
    the stored rows using only the run's captured inputs; a run whose captured
    inputs are incomplete reports ``UNKNOWN_MISSING_INPUTS`` rather than a
    guessed replay. Chain integrity stays a separate ``chain.verify_chain``
    check; neither proof substitutes for the other.
    """

    model_config = _FROZEN

    run_id: Id
    status: Literal["IDENTICAL", "DIFFERENT", "UNKNOWN_MISSING_INPUTS"]
    check_differences: tuple[dict[str, JsonValue], ...]
    event_draft_differences: tuple[dict[str, JsonValue], ...]
    wrote_rows: Literal[False]


class ExperimentKind(StrEnum):
    DIAGNOSTIC = "DIAGNOSTIC"
    QUALIFYING_COMPARISON = "QUALIFYING_COMPARISON"
    LATER_CONDITION_COMPARISON = "LATER_CONDITION_COMPARISON"


class CandidateRef(BaseModel):
    model_config = _FROZEN

    label: Literal["A", "B"]
    artifact_version_id: Id
    artifact_content_hash: str


class Experiment(BaseModel):
    """One reserved experiment.

    The row is the durable reservation: a diagnostic whose run fails still
    consumed its slot, and nothing here can be edited afterwards. A diagnostic
    carries exactly one candidate and never a protected reservation, so it can
    never make a version eligible (program design S3.5 and section 7).
    """

    model_config = _FROZEN

    id: Id
    shift_id: Id
    kind: ExperimentKind
    investigation_id: Id | None
    candidates: tuple[CandidateRef, ...]
    declared_treatment: str
    context_id: Id
    observed_run_id: Id | None = None
    observed_context_id: Id | None = None
    content_hash: str
    trial_count_per_candidate: Literal[1, 3]
    state: Literal["PLANNED", "RUNNING", "FINALIZED", "FAILED", "INVALIDATED"]
    client_request_id: str
    created_at: datetime


class TrialSlot(BaseModel):
    """One ordered candidate/workload slot of a qualifying comparison (S3.5).

    Slots are reserved with the experiment, before any result exists, and are
    never edited afterwards except for their run binding and terminal state. A
    slot binds its pair's frozen workload identity and count, so execution and
    replay read the slot rather than a mutable fixture path, and it carries the
    protected variant refs both slots of its pair share.
    """

    model_config = _FROZEN

    id: Id
    experiment_id: Id
    pair_ordinal: int
    execution_ordinal: int
    candidate_label: Literal["A", "B"]
    artifact_version_id: Id
    workload_id: Id
    request_batch_hash: str
    request_count: int
    executed_request_count: int
    protected_variant_refs: tuple[str, ...]
    run_id: Id | None = None
    state: Literal["RESERVED", "RUNNING", "COMPLETE", "FAILED"] = "RESERVED"


class ExposureReservation(BaseModel):
    """One comparison- or operation-scoped protected reservation (S3.1, S4).

    A compromised or leaked reservation is retired by a state change on this row
    and its items; nothing is ever deleted (ADR 0001).
    """

    model_config = _FROZEN

    id: Id
    engagement_slug: Slug
    scope: Literal["comparison", "operation"]
    experiment_id: Id | None
    state: Literal["ACTIVE", "INVALIDATED"] = "ACTIVE"
    created_at: datetime


class ExposureItem(BaseModel):
    """One reserved protected variant, shared by both slots of its pair (S4).

    ``variant_ref`` is opaque and never reusable within an engagement for the
    family and cycle; the unique key on (engagement, family, cycle, variant_ref)
    makes a relabelled copy collide with the exposed identity instead of
    counting as a fresh holdout.
    """

    model_config = _FROZEN

    id: Id
    reservation_id: Id
    engagement_slug: Slug
    family: str
    cycle: int
    variant_ref: str
    pair_ordinal: int
    state: DrawState = DrawState.ACTIVE
    drawn_at: datetime


class RunOutput(BaseModel):
    model_config = _FROZEN

    id: Id
    run_id: Id
    request_ordinal: int
    request_text: str
    http_status: int | None
    body: bytes
    elapsed_ms: int | None
    transport_error: ExecutorFailure | None = None
    log_ref: str | None = None


class CheckResult(BaseModel):
    model_config = _FROZEN

    id: Id
    run_id: Id
    check_id: Id
    verdict: Literal["pass", "fail", "error"]
    observed_ref: str
    expected_ref: str | None = None
    reason_code: ReasonCode | None = None


class Incident(BaseModel):
    model_config = _FROZEN

    id: Id
    engagement_slug: Slug
    shift_id: Id
    opening_run_id: Id
    failing_output_ref: str
    check_result_id: Id
    reason_code: ReasonCode
    opened_event_seq: int
    state: IncidentState
    resolving_version_id: Id | None = None
    resolved_event_seq: int | None = None


class RotationDraw(BaseModel):
    """Append-only exposure record for one drawn variant (program design S3.2).

    ``variant_ref`` is opaque and never reusable within an engagement; ``cycle``
    names the operator-authored inventory generation, and a refill appends a new
    cycle without deleting any prior draw. ``state`` is the only mutation, and it
    exists so a compromised group can be retired by a state change.
    """

    model_config = _FROZEN

    id: Id
    engagement_slug: Slug
    family: str
    variant_ref: str
    run_id: Id
    cycle: int
    drawn_at: datetime
    state: DrawState = DrawState.ACTIVE


class CloseShiftFacts(BaseModel):
    """Facts captured at shift close; reduce_close turns these into drafts (S3.4)."""

    model_config = _FROZEN

    shift_id: Id
    declared_limits: tuple[str, ...]
    unresolved_incident_ids: tuple[Id, ...]
    committed_contract: ContractParams
    handover_runbook_version_id: Id | None = None


class LedgerEventDraft(BaseModel):
    """Reducer output before chaining; carries no seq/hash fields (S3.4)."""

    model_config = _FROZEN

    event_type: LedgerEventType
    cause_refs: tuple[Id, ...]
    payload: dict[str, JsonValue]
    synthetic: Literal[True] = True


class LedgerEvent(LedgerEventDraft):
    """After ledger.chain.append assigns seq and hashes (S3.5)."""

    seq: int
    prev_hash: str
    hash: str
