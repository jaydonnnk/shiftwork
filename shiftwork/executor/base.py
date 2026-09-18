import base64
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, StrictBytes

from shiftwork.domain import canonical
from shiftwork.domain.models import ExecutorFailure, RunOutput


class ExecutorModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ArtifactSnapshotRef(ExecutorModel):
    files: dict[str, StrictBytes]
    manifest_hash: str


class BatchRef(ExecutorModel):
    path_ref: str
    content_hash: str


class InferenceGrant(ExecutorModel):
    endpoint: str
    scoped_key_ref: str
    token_budget: int = Field(gt=0)


class RunRequest(ExecutorModel):
    artifact_snapshot: ArtifactSnapshotRef
    request_batch: BatchRef
    shop_snapshot_ref: str
    harness_ref: str
    image_ref: str
    deadline_s: int = Field(gt=0)
    inference_grant: InferenceGrant | None


class RawCapture(ExecutorModel):
    request_ordinal: int = Field(gt=0)
    http_status: int | None
    body: StrictBytes
    elapsed_ms: int | None = Field(ge=0)
    transport_error: ExecutorFailure | None
    log_ref: str | None


class RunResult(ExecutorModel):
    captures: tuple[RawCapture, ...]
    executor_ref: str | None
    failure: ExecutorFailure | None
    wall_ms: int = Field(ge=0)


class ExecutorAdapter(Protocol):
    name: str

    async def execute(self, request: RunRequest) -> RunResult: ...


class RequestStimulus(ExecutorModel):
    ordinal: int = Field(gt=0)
    text: str
    body: StrictBytes


def load_batch(ref: BatchRef) -> tuple[RequestStimulus, ...]:
    root = Path(__file__).resolve().parents[1] / "fixtures" / "requests"
    path = (root / ref.path_ref).resolve()
    if not path.is_relative_to(root):
        raise ValueError("request batch must be inside fixtures/requests")
    raw = path.read_bytes()
    if canonical.content_hash(base64.b64encode(raw).decode("ascii")) != ref.content_hash:
        raise ValueError("request batch hash mismatch")
    requests = []
    for line in raw.splitlines(keepends=True):
        entry = json.loads(line)
        requests.append(RequestStimulus(ordinal=entry["ordinal"], text=entry["text"], body=line))
    if not requests or [r.ordinal for r in requests] != list(range(1, len(requests) + 1)):
        raise ValueError("batch ordinals must be consecutive from 1")
    return tuple(requests)


def normalize_captures(raw: Iterable[RawCapture], deadline_s: int) -> tuple[RunOutput, ...]:
    if deadline_s <= 0:
        raise ValueError("deadline_s must be positive")
    captures = sorted(raw, key=lambda capture: capture.request_ordinal)
    ordinals = [capture.request_ordinal for capture in captures]
    if len(ordinals) != len(set(ordinals)):
        raise ValueError("duplicate capture ordinal")
    # Run identity and customer text belong to the controller, not the executor.
    return tuple(RunOutput(
        id=f"out-{capture.request_ordinal}",
        run_id="",
        request_text="",
        request_ordinal=capture.request_ordinal,
        http_status=capture.http_status,
        body=capture.body,
        elapsed_ms=capture.elapsed_ms,
        transport_error=capture.transport_error,
        log_ref=capture.log_ref,
    ) for capture in captures)
