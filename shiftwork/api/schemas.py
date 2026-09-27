"""HTTP request/response models (tracer subset of program design S3.9)."""

import base64
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from shiftwork.domain.models import (
    ArtifactVersion,
    CheckResult,
    Claim,
    Incident,
    JsonValue,
    OperatingSelection,
    Run,
    RunOutput,
    Shift,
)

_FROZEN = ConfigDict(frozen=True, extra="forbid", from_attributes=True)


class DraftView(BaseModel):
    model_config = _FROZEN

    shift_id: str
    files: dict[str, str]
    updated_at: datetime


class DraftUpdate(BaseModel):
    model_config = _FROZEN

    files: dict[str, str]


class ContractView(BaseModel):
    """Public projection of a frozen ContractParams (no expected values)."""

    model_config = _FROZEN

    catalog_version: int
    must_never: tuple[str, ...]
    selections: dict[str, str]
    response_time_limit_ms: Literal[1000, 3000, 8000]
    declared_limits: tuple[str, ...]


class FreezeVersionRequest(BaseModel):
    model_config = _FROZEN

    contract: ContractView


class ShiftView(BaseModel):
    model_config = _FROZEN

    id: str
    engagement_slug: str
    seq: int
    state: Literal["open", "closed"]
    opened_at: datetime
    closed_at: datetime | None = None
    opening_mode: Literal["STANDARD", "LEGACY_FIRST_CHOICE"] | None = None
    operation_allowed: bool

    @classmethod
    def of(cls, shift: Shift) -> "ShiftView":
        return cls.model_validate(shift)


class ArtifactVersionView(BaseModel):
    model_config = _FROZEN

    id: str
    shift_id: str
    parent_id: str | None = None
    content_hash: str
    contract: ContractView
    contract_catalog_hash: str
    created_by: Literal["template", "learner"]
    created_at: datetime

    @classmethod
    def of(cls, version: ArtifactVersion) -> "ArtifactVersionView":
        return cls.model_validate(version)


class ArtifactSourceView(BaseModel):
    """Owned source with logical filenames, without any storage locator."""

    model_config = _FROZEN

    id: str
    parent_id: str | None
    content_hash: str
    files: dict[str, str]
    contract: ContractView
    authorship: Literal["template", "learner"]


class RunView(BaseModel):
    model_config = _FROZEN

    id: str
    shift_id: str
    artifact_version_id: str
    attempt_number: int
    state: Literal["QUEUED", "RUNNING", "CAPTURED", "FINALIZED", "FAILED"]
    adapter: Literal["local_process", "recorded", "tokenfactory"]
    failure_kind: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    purpose: Literal["EXPERIMENT", "OPERATION", "LEGACY_OPERATION"]
    evidence_mode: Literal["RECORDED_INSPECTION", "TRUSTED_LOCAL", "ISOLATED_LIVE"] | None
    selection_id: str | None

    @classmethod
    def of(cls, run: Run) -> "RunView":
        return cls.model_validate(run)


class CustomerAnswerView(BaseModel):
    model_config = _FROZEN

    action: Literal["answer", "ask", "decline", "escalate"]
    display_text: str
    claims: tuple[Claim, ...]
    evidence_refs: tuple[str, ...]
    verified_record_age_ms: int | None


class PublicShopRecordView(BaseModel):
    """Only independently published record fields, never snapshot metadata."""

    model_config = _FROZEN

    record_id: str
    kind: str
    title: str | None
    edition: str | None
    value: JsonValue
    record_age_ms: int


class RunOutputView(BaseModel):
    model_config = _FROZEN

    id: str
    run_id: str
    request_ordinal: int
    request_text: str
    http_status: int | None = None
    body_base64: str
    elapsed_ms: int | None = None
    transport_error: str | None = None
    log_base64: str | None = None
    customer_answer: CustomerAnswerView | None = None
    public_shop_record: PublicShopRecordView | None = None
    public_shop_record_ref: str | None = None
    public_shop_snapshot_hash: str | None = None

    @classmethod
    def of(
        cls,
        output: RunOutput,
        *,
        customer_answer: CustomerAnswerView | dict[str, Any] | None = None,
        public_shop_record: PublicShopRecordView | dict[str, JsonValue] | None = None,
        public_shop_record_ref: str | None = None,
        public_shop_snapshot_hash: str | None = None,
    ) -> "RunOutputView":
        return cls(
            id=output.id,
            run_id=output.run_id,
            request_ordinal=output.request_ordinal,
            request_text=output.request_text,
            http_status=output.http_status,
            body_base64=base64.b64encode(output.body).decode("ascii"),
            elapsed_ms=output.elapsed_ms,
            transport_error=output.transport_error.value if output.transport_error else None,
            log_base64=(
                output.log_ref.removeprefix("data:application/octet-stream;base64,")
                if output.log_ref and output.log_ref.startswith("data:application/octet-stream;base64,")
                else None
            ),
            customer_answer=customer_answer,
            public_shop_record=public_shop_record,
            public_shop_record_ref=public_shop_record_ref,
            public_shop_snapshot_hash=public_shop_snapshot_hash,
        )


class CheckResultView(BaseModel):
    model_config = _FROZEN

    id: str
    run_id: str
    verdict: Literal["pass", "fail", "error"]
    observed_ref: str
    expected_ref: str | None = None
    reason_code: str | None = None
    public_check_id: str | None = None

    @classmethod
    def of(cls, result: CheckResult) -> "CheckResultView":
        return cls(
            id=result.id,
            run_id=result.run_id,
            verdict=result.verdict,
            observed_ref=result.observed_ref,
            expected_ref=result.expected_ref,
            reason_code=result.reason_code.value if result.reason_code else None,
            # Sealed expectations are never rendered; only reason-code outcomes surface.
            # CheckResult.check_id is the sealed case's own identity, so it is not
            # projected either (Gate 3 S3.9: the client works without a sealed check id).
            public_check_id=None,
        )


class IncidentView(BaseModel):
    model_config = _FROZEN

    id: str
    engagement_slug: str
    shift_id: str
    opening_run_id: str
    failing_output_ref: str
    check_result_id: str
    reason_code: str
    opened_event_seq: int
    state: Literal["OPEN", "RESOLVED", "CLOSED_UNRESOLVED"]
    resolving_version_id: str | None = None
    resolved_event_seq: int | None = None

    @classmethod
    def of(cls, incident: Incident) -> "IncidentView":
        return cls.model_validate(incident)


class LedgerEventDerivation(BaseModel):
    model_config = _FROZEN

    run_id: str
    check_id: str
    observed_ref: str
    request_ordinal: int
    request_text: str
    output_body_base64: str
    verdict: Literal["pass", "fail", "error"]
    reason_code: str | None = None


class LedgerEventCatalog(BaseModel):
    model_config = _FROZEN

    catalog_version: int
    catalog_record: dict[str, Any]


class LedgerEventView(BaseModel):
    model_config = _FROZEN

    seq: int
    event_type: str
    cause_refs: tuple[str, ...]
    payload: dict[str, Any]
    synthetic: bool
    prev_hash: str
    hash: str
    derivation: LedgerEventDerivation | None = None
    catalog: LedgerEventCatalog | None = None


class LedgerView(BaseModel):
    model_config = _FROZEN

    chain_status: Literal["VALID"]
    events: tuple[LedgerEventView, ...]


class SelectionView(BaseModel):
    model_config = _FROZEN

    id: str
    kind: Literal["STARTER_BASELINE", "LEARNER_CHOICE"]
    selected_version_id: str
    selected_content_hash: str
    comparison_id: str | None
    retained_alternative_version_id: str | None
    rationale: str
    state: Literal["VALID", "INVALIDATED"]
    created_at: datetime

    @classmethod
    def of(cls, selection: OperatingSelection) -> "SelectionView":
        return cls.model_validate(selection)


class BoardView(BaseModel):
    model_config = _FROZEN

    engagement_slug: str
    business_kind: str
    latest_shift: ShiftView | None = None
    latest_version: ArtifactVersionView | None = None
    latest_run: RunView | None = None
    operating_status: Literal["NEEDS_FIRST_CHOICE", "STARTER_BASELINE", "SELECTED", "INVALIDATED"] | None
    draft_base_version_id: str | None
    latest_saved_version_id: str | None
    operating_selection: SelectionView | None
    artifact_files: tuple[str, ...]
    requests_run: int
    attempts_used: int
    attempt_limit: int
    attempts_remaining: int
    incidents: tuple[IncidentView, ...]
    total_incidents: int
    unresolved_limits: tuple[str, ...]
    ledger_event_count: int
    ledger_totals: dict[str, int]
    chain_status: Literal["VALID"]

    @classmethod
    def of(cls, snapshot: dict[str, Any]) -> "BoardView":
        return cls.model_validate(snapshot)


class InvestigationAppendRequest(BaseModel):
    """The learner's diagnosis. Identity is never caller-supplied."""

    model_config = _FROZEN

    source_run_id: str
    source_request_ordinal: int
    cause: str
    falsifier: str
    public_test: str
    revision_of_id: str | None = None
    client_request_id: str


class InvestigationView(BaseModel):
    model_config = _FROZEN

    id: str
    source_run_id: str
    source_request_ordinal: int
    cause: str
    falsifier: str
    public_test: str
    revision_of_id: str | None
    authored_by: Literal["learner"]
    created_at: datetime


class AssistRequest(BaseModel):
    model_config = _FROZEN

    investigation_id: str | None = None
    role: Literal["HINT", "DIAGNOSIS", "PATCH_PROPOSAL"]
    client_request_id: str


class ExperimentRequest(BaseModel):
    """S11 accepts diagnostics only; comparisons arrive with their own slice.

    The controller chooses the workload, the adapter and the treatment, so this
    body carries no candidate list, no context and no declared treatment.
    """

    model_config = _FROZEN

    kind: Literal["DIAGNOSTIC"]
    investigation_id: str | None = None
    candidate_a_version_id: str
    client_request_id: str


class FrozenWorkloadView(BaseModel):
    model_config = _FROZEN

    id: str
    ordinal: int
    request_batch_hash: str
    request_count: int


class TrialAssessmentView(BaseModel):
    model_config = _FROZEN

    request_id: str
    request_ordinal: int
    task_id: str
    outcome: str
    mandatory_pass: bool
    reason_codes: tuple[str, ...]


class TrialOutputView(BaseModel):
    """The exact capture the learner's own service produced, plus its request text."""

    model_config = _FROZEN

    request_ordinal: int
    request_text: str
    http_status: int | None
    body_base64: str
    elapsed_ms: int | None
    transport_error: str | None


class ObservationView(BaseModel):
    """A sanitized observation. The raw payload ref stays internal."""

    model_config = _FROZEN

    kind: str
    public_payload_json: dict[str, Any]


class ExperimentTrialView(BaseModel):
    model_config = _FROZEN

    pair_ordinal: int
    candidate_label: Literal["A", "B"]
    workload_id: str
    request_batch_hash: str
    request_count: int
    run_id: str | None
    state: Literal["RESERVED", "RUNNING", "COMPLETE", "FAILED"]
    evidence_mode: str | None
    task_assessments: tuple[TrialAssessmentView, ...]
    observations: tuple[ObservationView, ...]
    outputs: tuple[TrialOutputView, ...]
    customer_text: str | None
    missing_evidence: tuple[str, ...]
    metrics: dict[str, Any] | None


class CandidateView(BaseModel):
    model_config = _FROZEN

    label: Literal["A", "B"]
    artifact_version_id: str
    artifact_content_hash: str


class ExperimentView(BaseModel):
    model_config = _FROZEN

    id: str
    shift_id: str
    kind: str
    investigation_id: str | None
    declared_treatment: str
    context_hash: str
    context_evidence_class: str
    workloads: tuple[FrozenWorkloadView, ...]
    candidates: tuple[CandidateView, ...]
    trials: tuple[ExperimentTrialView, ...]
    eligible: bool
    eligibility_reason: str
    state: str

    @classmethod
    def of(cls, payload: dict[str, Any]) -> "ExperimentView":
        return cls.model_validate(payload)


class InvestigateStationView(BaseModel):
    model_config = _FROZEN

    shift_id: str
    opening_mode: str | None
    orientation: dict[str, Any]
    investigations: tuple[InvestigationView, ...]
    latest_investigation_id: str | None
    assist_available: bool
    assist_reason: str
    bootstrap_available: bool
    bootstrap_reason: str
    latest_experiment: ExperimentView | None = None

    @classmethod
    def of(cls, payload: dict[str, Any]) -> "InvestigateStationView":
        return cls.model_validate(payload)
