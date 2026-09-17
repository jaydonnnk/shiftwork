"""Tracer subset of the durable domain models (program design S3.2).

Slice 2 replaces the stubbed persistence and extends these types to the full set.
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


class Shift(BaseModel):
    model_config = _FROZEN

    id: Id
    engagement_slug: Slug
    seq: int
    state: Literal["open", "closed"]
    opened_at: datetime
    closed_at: datetime | None = None


class ArtifactVersion(BaseModel):
    model_config = _FROZEN

    id: Id
    shift_id: Id
    parent_id: Id | None
    content_hash: str
    contract: dict[str, JsonValue]
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


class LedgerEvent(BaseModel):
    model_config = _FROZEN

    event_type: LedgerEventType
    cause_refs: tuple[Id, ...]
    payload: dict[str, JsonValue]
    synthetic: Literal[True] = True
    seq: int
    prev_hash: str
    hash: str
