import base64
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, StrictBytes

from shiftwork import config
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


SANDBOX_SHOP_SNAPSHOT_NAME = "shop.json"

# Device names Win32 resolves before ordinary files, so a payload declared as ``NUL``
# or ``CON.txt`` never materializes as a payload file.
_RESERVED_DEVICE_NAMES = frozenset(
    {"con", "prn", "aux", "nul", *(f"com{n}" for n in range(1, 10)), *(f"lpt{n}" for n in range(1, 10))}
)


def _collapsed_name(path: str) -> str:
    """The single name the platform resolves ``path`` to: casefolded, trailing dots/space dropped.

    NTFS is case-insensitive and strips trailing dots and spaces from a final
    component, so ``SHOP.JSON``, ``shop.json.`` and ``shop.json `` all name the same
    file. The collision check compares this collapsed form, never the literal string.
    """
    return path.casefold().rstrip(" .")


def _validate_sandbox_path(path: str) -> None:
    """Reject a declared payload path that could leave or alias the workspace.

    Containment is a filename rule, not a category rule: ``../escape`` is not made
    safe by being declared under an allowlisted category. Backslashes and ``:`` are
    rejected outright because a Windows separator or drive-letter form would slip
    past a POSIX containment check. A payload path is a single filename: a directory
    component cannot be provisioned (the payload cannot create directories, and a
    junction placed inside the workspace could redirect a nested write outside it).
    Names the platform collapses or reserves (case, trailing dots or spaces, device
    names) are refused here, because two declared paths aliasing one file, or a
    declared path that never materializes, is not a payload.
    """
    if not path or path in (".", ".."):
        raise ValueError(f"sandbox payload path is not a filename: {path!r}")
    if path.startswith("/") or "\\" in path or ":" in path:
        raise ValueError(f"sandbox payload path is absolute or ambiguous: {path!r}")
    if "/" in path:
        raise ValueError(f"sandbox payload path is not a single filename: {path!r}")
    collapsed = _collapsed_name(path)
    if not collapsed or collapsed in (".", ".."):
        raise ValueError(f"sandbox payload path is not a filename: {path!r}")
    if collapsed.split(".", 1)[0] in _RESERVED_DEVICE_NAMES:
        raise ValueError(f"sandbox payload path is a reserved device name: {path!r}")


class SandboxManifest(ExecutorModel):
    """The declared sandbox payload: what enters the sandbox and what stays out.

    ``provisioned`` maps an allowlisted category to the sandbox-relative paths
    written for it; ``controller_side`` maps a category to a ref that is delivered
    without ever entering the sandbox (the request batch is streamed one request at
    a time by the harness, and the harness itself is controller code). Sealed specs
    and expectations are not a category and cannot become one.
    """

    provisioned: dict[str, tuple[str, ...]]
    controller_side: dict[str, str]

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(sorted(path for group in self.provisioned.values() for path in group))

    @property
    def categories(self) -> frozenset[str]:
        return frozenset(self.provisioned) | frozenset(self.controller_side)


def provisioning_manifest(request: RunRequest) -> SandboxManifest:
    """Declare the exact payload for ``request``, fail-closed against the allowlist."""
    manifest = SandboxManifest(
        provisioned={
            "artifact_snapshot": tuple(sorted(request.artifact_snapshot.files)),
            "shop_snapshot": (SANDBOX_SHOP_SNAPSHOT_NAME,),
        },
        controller_side={
            "request_batch": request.request_batch.path_ref,
            "harness": request.harness_ref,
        },
    )
    extra = manifest.categories - set(config.SANDBOX_PAYLOAD_ALLOWLIST)
    if extra:
        raise ValueError(f"sandbox payload category outside the allowlist: {sorted(extra)}")
    missing = set(config.SANDBOX_PAYLOAD_ALLOWLIST) - manifest.categories
    if missing:
        raise ValueError(f"sandbox payload manifest is missing allowlisted categories: {sorted(missing)}")
    seen: set[str] = set()
    for group in manifest.provisioned.values():
        for path in group:
            _validate_sandbox_path(path)
            collapsed = _collapsed_name(path)
            if collapsed in seen:
                raise ValueError(f"sandbox payload path collision: {path!r}")
            seen.add(collapsed)
    return manifest


def provision_workspace(root: Path, request: RunRequest, shop_snapshot: bytes) -> SandboxManifest:
    """Write exactly the manifest's provisioned paths into ``root``.

    Every write is derived from the manifest, so a declared-but-unwritten path or an
    undeclared write is a mismatch the isolation tests can observe. The caller supplies
    the already-validated snapshot bytes; this function performs no trust decisions.
    """
    manifest = provisioning_manifest(request)
    files = request.artifact_snapshot.files
    sources = {"artifact_snapshot": files, "shop_snapshot": {SANDBOX_SHOP_SNAPSHOT_NAME: shop_snapshot}}
    for category, paths in manifest.provisioned.items():
        for path in paths:
            (root / path).write_bytes(sources[category][path])
    return manifest


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
