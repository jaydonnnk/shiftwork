import base64
import binascii
import json
from pathlib import Path

from shiftwork.domain import canonical
from shiftwork.domain.models import ExecutorFailure
from shiftwork.executor.base import RawCapture, RunRequest, RunResult, load_batch


class RecordedAdapter:
    name = "recorded"

    def __init__(self, transcript_path: Path) -> None:
        self._transcript_path = transcript_path

    async def execute(self, request: RunRequest) -> RunResult:
        try:
            batch = load_batch(request.request_batch)
            snapshot = Path(request.shop_snapshot_ref).read_bytes()
        except (OSError, ValueError, KeyError):
            return RunResult(captures=(), executor_ref=None, failure=ExecutorFailure.PROVISION_FAILED, wall_ms=0)
        try:
            transcript = json.loads(self._transcript_path.read_bytes())
            if transcript["request_batch_hash"] != request.request_batch.content_hash or transcript["shop_snapshot_hash"] != canonical.content_hash(base64.b64encode(snapshot).decode("ascii")):
                return RunResult(captures=(), executor_ref=None, failure=ExecutorFailure.PROVISION_FAILED, wall_ms=0)
            captures = []
            for entry in transcript["captures"]:
                if captures and captures[-1].transport_error is not None:
                    raise ValueError("transcript continues after a transport failure")
                body = base64.b64decode(entry["body_base64"], validate=True)
                error = entry.get("transport_error")
                try:
                    body.decode("utf-8")
                except UnicodeDecodeError:
                    if error is None:
                        error = ExecutorFailure.CAPTURE_NON_UTF8
                else:
                    if error == ExecutorFailure.CAPTURE_NON_UTF8:
                        raise ValueError("non-UTF-8 failure requires invalid UTF-8 bytes")
                log_base64 = entry.get("log_base64")
                if log_base64 is not None:
                    base64.b64decode(log_base64, validate=True)
                capture = RawCapture(
                    request_ordinal=entry["request_ordinal"],
                    http_status=entry["http_status"],
                    body=body,
                    elapsed_ms=entry["elapsed_ms"],
                    transport_error=error,
                    log_ref="data:application/octet-stream;base64," + log_base64 if log_base64 else None,
                )
                if capture.http_status is None:
                    if capture.body or capture.transport_error is None:
                        raise ValueError("missing HTTP status requires an empty failed capture")
                elif not 100 <= capture.http_status <= 599:
                    raise ValueError("invalid HTTP status")
                captures.append(capture)
            if [c.request_ordinal for c in captures] != [r.ordinal for r in batch[:len(captures)]] or len(captures) > len(batch):
                raise ValueError("transcript captures must be an executed prefix")
            capture_failure = captures[-1].transport_error if captures else None
            failure = ExecutorFailure(transcript["failure"]) if transcript.get("failure") is not None else capture_failure
            if capture_failure is not None and failure != capture_failure:
                # A dying process can leave a truncated response before its exit is observed.
                if not (failure == ExecutorFailure.SANDBOX_TERMINATED and capture_failure in (
                    ExecutorFailure.SERVICE_UNREACHABLE, ExecutorFailure.CAPTURE_TRUNCATED,
                )):
                    raise ValueError("run failure contradicts the captured transport failure")
            if failure is None and len(captures) != len(batch):
                raise ValueError("incomplete transcript without a failure")
            return RunResult(captures=tuple(captures), executor_ref=None, failure=failure, wall_ms=transcript["wall_ms"])
        except (OSError, ValueError, KeyError, TypeError, binascii.Error):
            return RunResult(captures=(), executor_ref=None, failure=ExecutorFailure.INTERNAL, wall_ms=0)
