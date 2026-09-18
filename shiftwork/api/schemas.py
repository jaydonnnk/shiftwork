"""HTTP request/response models (tracer subset of program design S3.9)."""

import base64
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from shiftwork.domain.models import (
    ArtifactVersion,
    CheckResult,
    Incident,
    LedgerEvent,
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

    @classmethod
    def of(cls, run: Run) -> "RunView":
        return cls.model_validate(run)


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

    @classmethod
    def of(cls, output: RunOutput) -> "RunOutputView":
        return cls(
            id=output.id,
            run_id=output.run_id,
            request_ordinal=output.request_ordinal,
            request_text=output.request_text,
            http_status=output.http_status,
            body_base64=base64.b64encode(output.body).decode("ascii"),
            elapsed_ms=output.elapsed_ms,
            transport_error=output.transport_error.value if output.transport_error else None,
        )


class CheckResultView(BaseModel):
    model_config = _FROZEN

    id: str
    run_id: str
    check_id: str
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
            check_id=result.check_id,
            verdict=result.verdict,
            observed_ref=result.observed_ref,
            expected_ref=result.expected_ref,
            reason_code=result.reason_code.value if result.reason_code else None,
            # Sealed expectations are never rendered; only reason-code outcomes surface.
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


class LedgerView(BaseModel):
    model_config = _FROZEN

    chain_status: Literal["VALID", "BROKEN"]
    events: tuple[LedgerEvent, ...]


class BoardView(BaseModel):
    model_config = _FROZEN

    engagement_slug: str
    business_kind: str
    latest_shift: ShiftView | None = None
    latest_version: ArtifactVersionView | None = None
    latest_run: RunView | None = None
    requests_run: int
    attempts_used: int
    attempt_limit: int
    attempts_remaining: int
    open_incidents: tuple[IncidentView, ...]
    total_incidents: int
    ledger_event_count: int
    ledger_totals: dict[str, int]
    chain_status: Literal["VALID", "BROKEN"]

    @classmethod
    def of(cls, snapshot: dict[str, Any]) -> "BoardView":
        return cls.model_validate(snapshot)
