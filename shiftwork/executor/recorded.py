"""Recorded transcript adapter: replays checked-in captures.

Slice 1 uses this adapter so the lifecycle is fully deterministic offline. The
Token Factory sandbox adapter arrives under the same shape after the capability
spike (program design S9).
"""

import base64
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from shiftwork.domain.models import ExecutorFailure, Id


class RawCapture(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    request_ordinal: int
    request_text: str
    http_status: int | None
    body: bytes
    elapsed_ms: int | None
    transport_error: ExecutorFailure | None = None


class RecordedAdapter:
    name = "recorded"

    def __init__(self, transcript_path: Path) -> None:
        self._transcript_path = transcript_path

    def execute(self, *, shift_id: Id, artifact_version_id: Id) -> list[RawCapture]:
        transcript = json.loads(self._transcript_path.read_text(encoding="utf-8"))
        captures = [
            RawCapture(
                request_ordinal=entry["request_ordinal"],
                request_text=entry["request_text"],
                http_status=entry["http_status"],
                body=base64.b64decode(entry["body_base64"]),
                elapsed_ms=entry["elapsed_ms"],
                transport_error=entry.get("transport_error"),
            )
            for entry in transcript["captures"]
        ]
        return sorted(captures, key=lambda capture: capture.request_ordinal)
