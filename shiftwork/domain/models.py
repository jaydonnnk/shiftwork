"""Durable domain models (program design S3.2).

Slice 2 carries the real contract, catalog, structured-response and ledger-draft
types the thin vertical path needs. Later slices add the rotation, assist and
curation models (RotationDraw, AssistEvent, MissionSource) without renumbering
what exists here.
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

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


class LedgerEventType(StrEnum):
    SALE_COMPLETED = "SALE_COMPLETED"
    REFUND_REQUIRED = "REFUND_REQUIRED"
    BOOKING_COMMITTED = "BOOKING_COMMITTED"
    ESCALATION_TO_HUMAN = "ESCALATION_TO_HUMAN"
    INCIDENT_OPENED = "INCIDENT_OPENED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"
    BACKLOG_RECORDED = "BACKLOG_RECORDED"
    LIMIT_DECLARED = "LIMIT_DECLARED"


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
    attempt_number: int
    state: RunState
    adapter: Literal["local_process", "recorded", "tokenfactory"]
    failure_kind: ExecutorFailure | None = None
    started_at: datetime
    ended_at: datetime | None = None


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
