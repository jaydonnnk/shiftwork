"""Tracer lifecycle: open shift, edit draft, freeze, run, stub finalize, close.

Slice 2 replaces the stubbed persistence and Slice 5+ replaces the stub
finalization (evaluator, reducer, chain, incident opening) with the approved
deterministic components.
"""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from shiftwork import config
from shiftwork.domain.models import (
    ArtifactVersion,
    CheckResult,
    ExecutorFailure,
    Incident,
    IncidentState,
    LedgerEvent,
    LedgerEventType,
    ReasonCode,
    Run,
    RunOutput,
    RunState,
    Shift,
)
from shiftwork.executor.recorded import RawCapture, RecordedAdapter
from shiftwork.store import db, repo


class LifecycleError(Exception):
    """Typed lifecycle failure. ``kind`` is "not_found" or "conflict"."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


TRACER_CONTRACT: dict[str, Any] = {
    "catalog_version": 0,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "response_time_limit_ms": 3000,
    "declared_limits": ["Tracer contract stub, replaced by the catalog-backed contract (Slice 2 catalog, Slice 4 ContractParams)."],
}

_SERVICE_TEMPLATE = '''"""Bookshop customer-information service (learner-owned artifact).

Answers one request at a time with a structured JSON envelope. This tracer
scaffold returns fixed placeholder data; the learner replaces it with real logic.
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

RESPONSES = {
    1: {
        "action": "answer",
        "claims": [
            {"kind": "price", "value": 1250},
            {"kind": "stock", "value": "in_stock"},
        ],
        "evidence_refs": ["catalog:9780141187761"],
        "record_age_ms": 30000,
    },
    2: {
        "action": "answer",
        "claims": [{"kind": "stock", "value": "in_stock"}],
        "evidence_refs": ["catalog:9780141187761"],
        "record_age_ms": 5400000,
    },
    3: {
        "action": "answer",
        "claims": [{"kind": "policy_answer", "value": "returns accepted within 30 days"}],
        "evidence_refs": ["policy:returns"],
        "record_age_ms": 60000,
    },
}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length) or b"{}")
        fallback = {"action": "decline", "claims": [], "evidence_refs": [], "record_age_ms": None}
        body = json.dumps(RESPONSES.get(request.get("ordinal"), fallback)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
'''

TRACER_DRAFT_FILES: dict[str, str] = {"service.py": _SERVICE_TEMPLATE}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_shift(conn: sqlite3.Connection, shift_id: str) -> Shift:
    shift = repo.get_shift(conn, shift_id)
    if shift is None:
        raise LifecycleError("not_found", f"unknown shift: {shift_id}")
    return shift


def _require_open_shift(conn: sqlite3.Connection, shift_id: str) -> Shift:
    shift = _require_shift(conn, shift_id)
    if shift.state != "open":
        raise LifecycleError("conflict", f"shift is closed: {shift_id}")
    return shift


def _adapter() -> RecordedAdapter:
    return RecordedAdapter(config.TRACER_TRANSCRIPT)


def open_next_shift(conn: sqlite3.Connection, slug: str = config.BOOKSHOP_SLUG) -> Shift:
    if repo.get_engagement(conn, slug) is None:
        raise LifecycleError("not_found", f"unknown engagement: {slug}")
    seq = repo.max_shift_seq(conn, slug) + 1
    shift = Shift(
        id=f"{slug}-shift-{seq:02d}",
        engagement_slug=slug,
        seq=seq,
        state="open",
        opened_at=_now(),
    )
    repo.insert_shift(conn, shift)
    # Tracer seeds the template draft. Later slices seed from the inherited
    # artifact version and carry open incidents and ledger state forward.
    repo.upsert_draft(conn, shift.id, TRACER_DRAFT_FILES, shift.opened_at)
    conn.commit()
    return shift


def get_draft(conn: sqlite3.Connection, shift_id: str) -> dict[str, Any]:
    _require_shift(conn, shift_id)
    draft = repo.get_draft(conn, shift_id)
    if draft is None:
        raise LifecycleError("not_found", f"no draft for shift: {shift_id}")
    files, updated_at = draft
    return {"shift_id": shift_id, "files": files, "updated_at": updated_at}


def save_draft(conn: sqlite3.Connection, shift_id: str, files: dict[str, str]) -> dict[str, Any]:
    _require_open_shift(conn, shift_id)
    if not files:
        raise LifecycleError("conflict", "draft must contain at least one file")
    updated_at = _now()
    repo.upsert_draft(conn, shift_id, files, updated_at)
    conn.commit()
    return {"shift_id": shift_id, "files": files, "updated_at": updated_at}


def freeze_version(conn: sqlite3.Connection, shift_id: str) -> ArtifactVersion:
    shift = _require_open_shift(conn, shift_id)
    if repo.get_draft(conn, shift_id) is None:
        raise LifecycleError("conflict", f"no draft to freeze for shift: {shift_id}")
    ordinal = repo.count_versions(conn) + 1
    parent = repo.get_latest_version(conn, shift_id) or repo.get_latest_version_for_engagement(
        conn, shift.engagement_slug
    )
    version = ArtifactVersion(
        id=f"ver-{ordinal:04d}",
        shift_id=shift_id,
        parent_id=parent.id if parent else None,
        # Placeholder: Slice 2 computes the real content hash of files + contract.
        content_hash=f"placeholder-{ordinal}",
        contract=TRACER_CONTRACT,
        created_by="learner",
        created_at=_now(),
    )
    repo.insert_version(conn, version)
    conn.commit()
    return version


def start_run(conn: sqlite3.Connection, shift_id: str) -> Run:
    _require_open_shift(conn, shift_id)
    version = repo.get_latest_version(conn, shift_id)
    if version is None:
        raise LifecycleError("conflict", "freeze a version before starting a run")
    used = repo.count_runs(conn, shift_id)
    if used >= config.DEFAULT_ATTEMPT_LIMIT:
        raise LifecycleError("conflict", "attempt budget exhausted for this shift")
    ordinal = repo.count_runs_all(conn) + 1
    run = Run(
        id=f"run-{ordinal:04d}",
        shift_id=shift_id,
        artifact_version_id=version.id,
        attempt_number=used + 1,
        state=RunState.QUEUED,
        adapter=config.TRACER_ADAPTER,
        started_at=_now(),
    )
    repo.insert_run(conn, run)
    conn.commit()
    return run


def execute_run(conn: sqlite3.Connection, run_id: str) -> Run:
    run = repo.get_run(conn, run_id)
    if run is None:
        raise LifecycleError("not_found", f"unknown run: {run_id}")
    if run.state is not RunState.QUEUED:
        return run
    repo.update_run(conn, run_id, RunState.RUNNING)
    conn.commit()
    try:
        captures = _adapter().execute(
            shift_id=run.shift_id, artifact_version_id=run.artifact_version_id
        )
        outputs = [_store_capture(conn, run, capture) for capture in captures]
        repo.update_run(conn, run_id, RunState.CAPTURED)
        _finalize_stub(conn, run, outputs)
        repo.update_run(conn, run_id, RunState.FINALIZED, ended_at=_now())
        conn.commit()
    except Exception:
        conn.rollback()
        repo.update_run(conn, run_id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
        conn.commit()
        raise
    return repo.get_run(conn, run_id)


def execute_run_task(db_path: str, run_id: str) -> None:
    conn = db.connect(db_path)
    try:
        execute_run(conn, run_id)
    finally:
        conn.close()


def _store_capture(conn: sqlite3.Connection, run: Run, capture: RawCapture) -> RunOutput:
    output = RunOutput(
        id=f"{run.id}-out-{capture.request_ordinal}",
        run_id=run.id,
        request_ordinal=capture.request_ordinal,
        request_text=capture.request_text,
        http_status=capture.http_status,
        body=capture.body,
        elapsed_ms=capture.elapsed_ms,
        transport_error=capture.transport_error,
    )
    repo.insert_output(conn, output)
    return output


def _finalize_stub(conn: sqlite3.Connection, run: Run, outputs: list[RunOutput]) -> None:
    """Hardcoded Slice 1 finalization: one failing check, two chained events, one incident."""
    shift = _require_shift(conn, run.shift_id)
    failing = next((output for output in outputs if output.request_ordinal == 2), outputs[-1])

    check_result = CheckResult(
        id=f"cr-{repo.count_check_results(conn) + 1:04d}",
        run_id=run.id,
        check_id="tracer-stale-check",
        verdict="fail",
        observed_ref=failing.id,
        expected_ref=None,
        reason_code=ReasonCode.STALE_BEYOND_RULE,
    )
    repo.insert_check_result(conn, check_result)

    incident_id = f"{config.INCIDENT_PREFIX}-{repo.count_incidents(conn, shift.engagement_slug) + 1:02d}"
    previous = repo.last_ledger_event(conn, shift.engagement_slug)
    seq = previous.seq + 1 if previous else 1
    prev_hash = previous.hash if previous else config.GENESIS_HASH

    sale = LedgerEvent(
        event_type=LedgerEventType.SALE_COMPLETED,
        cause_refs=(run.id, outputs[0].id),
        payload={"orders_completed": 1},
        seq=seq,
        prev_hash=prev_hash,
        hash=f"placeholder-chain-{seq}",
    )
    repo.insert_ledger_event(conn, shift.engagement_slug, sale)

    opened = LedgerEvent(
        event_type=LedgerEventType.INCIDENT_OPENED,
        cause_refs=(incident_id, check_result.id, failing.id),
        payload={"reason_code": check_result.reason_code.value, "incident_id": incident_id},
        seq=seq + 1,
        prev_hash=sale.hash,
        hash=f"placeholder-chain-{seq + 1}",
    )
    repo.insert_ledger_event(conn, shift.engagement_slug, opened)

    repo.insert_incident(
        conn,
        Incident(
            id=incident_id,
            engagement_slug=shift.engagement_slug,
            shift_id=shift.id,
            opening_run_id=run.id,
            failing_output_ref=failing.id,
            check_result_id=check_result.id,
            reason_code=ReasonCode.STALE_BEYOND_RULE,
            opened_event_seq=opened.seq,
            state=IncidentState.OPEN,
        ),
    )


def close_shift(conn: sqlite3.Connection, shift_id: str) -> Shift:
    shift = _require_shift(conn, shift_id)
    if shift.state == "open":
        repo.close_shift(conn, shift_id, _now())
        conn.commit()
    return _require_shift(conn, shift_id)


def get_run(conn: sqlite3.Connection, run_id: str) -> Run:
    run = repo.get_run(conn, run_id)
    if run is None:
        raise LifecycleError("not_found", f"unknown run: {run_id}")
    return run


def list_outputs(conn: sqlite3.Connection, run_id: str) -> list[RunOutput]:
    get_run(conn, run_id)
    return repo.list_outputs(conn, run_id)


def list_check_results(conn: sqlite3.Connection, run_id: str) -> list[CheckResult]:
    get_run(conn, run_id)
    return repo.list_check_results(conn, run_id)


def get_incident(conn: sqlite3.Connection, incident_id: str) -> Incident:
    incident = repo.get_incident(conn, incident_id)
    if incident is None:
        raise LifecycleError("not_found", f"unknown incident: {incident_id}")
    return incident


def ledger(conn: sqlite3.Connection, slug: str) -> dict[str, Any]:
    if repo.get_engagement(conn, slug) is None:
        raise LifecycleError("not_found", f"unknown engagement: {slug}")
    return {
        "events": repo.list_ledger_events(conn, slug),
        # Placeholder: Slice 5 runs the real verify_chain on every read.
        "chain_status": "VALID",
    }


def board_snapshot(conn: sqlite3.Connection, slug: str = config.BOOKSHOP_SLUG) -> dict[str, Any]:
    engagement = repo.get_engagement(conn, slug)
    if engagement is None:
        raise LifecycleError("not_found", f"unknown engagement: {slug}")
    latest_shift = repo.get_latest_shift(conn, slug)
    latest_version = repo.get_latest_version(conn, latest_shift.id) if latest_shift else None
    latest_run = repo.get_latest_run(conn, latest_shift.id) if latest_shift else None
    requests_run = len(repo.list_outputs(conn, latest_run.id)) if latest_run else 0
    attempts_used = repo.count_runs(conn, latest_shift.id) if latest_shift else 0
    incidents = repo.list_incidents(conn, slug)
    events = repo.list_ledger_events(conn, slug)
    totals: dict[str, int] = {}
    for event in events:
        totals[event.event_type.value] = totals.get(event.event_type.value, 0) + 1
    return {
        "engagement_slug": slug,
        "business_kind": engagement["business_kind"],
        "latest_shift": latest_shift,
        "latest_version": latest_version,
        "latest_run": latest_run,
        "requests_run": requests_run,
        "attempts_used": attempts_used,
        "attempt_limit": config.DEFAULT_ATTEMPT_LIMIT,
        "attempts_remaining": config.DEFAULT_ATTEMPT_LIMIT - attempts_used,
        "open_incidents": [incident for incident in incidents if incident.state == IncidentState.OPEN],
        "total_incidents": len(incidents),
        "ledger_event_count": len(events),
        "ledger_totals": totals,
        "chain_status": "VALID",
    }
