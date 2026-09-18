"""Thin real vertical path: open shift, edit draft, freeze, run, real finalize, close.

Slice 2 replaces the tracer's stub persistence and stub finalization with the real
deterministic components: content-hashed freeze, the recorded adapter replaying one
checked-in transcript, the sealed-case evaluator producing one real CheckResult, and
the reducer plus hash chain producing one real LedgerEvent. Incident opening is a
later slice (S5/S7); Slice 2 opens no incident.
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shiftwork import config
from shiftwork.domain import canonical, contract_catalog
from shiftwork.domain.models import (
    ArtifactVersion,
    CheckResult,
    ContractParams,
    ExecutorFailure,
    Incident,
    IncidentState,
    JsonValue,
    Run,
    RunOutput,
    RunState,
    Shift,
)
from shiftwork.evaluator import evaluator
from shiftwork.executor import base as executor
from shiftwork.executor.recorded import RecordedAdapter
from shiftwork.ledger import chain, reducer
from shiftwork.sealed import store as sealed_store
from shiftwork.store import db, repo


class LifecycleError(Exception):
    """Typed lifecycle failure. ``kind`` is "not_found" or "conflict"."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


BOOKSHOP_DRAFT_FILES: dict[str, str] = {
    name: (config.ARTIFACT_TEMPLATE_DIR / name).read_bytes().decode("utf-8")
    for name in ("service.py", "contract.json", "response_contract.json")
}


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


def _attempt_limit(conn: sqlite3.Connection, slug: str) -> int:
    row = repo.get_engagement_config(conn, slug)
    return int(row["attempt_limit"]) if row else config.DEFAULT_ATTEMPT_LIMIT


def _adapter() -> RecordedAdapter:
    return RecordedAdapter(config.THIN_TRANSCRIPT)


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
    # Slice 2 seeds the template draft. Later slices seed from the inherited
    # artifact version and carry open incidents and ledger state forward.
    repo.upsert_draft(conn, shift.id, BOOKSHOP_DRAFT_FILES, shift.opened_at)
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


def freeze_version(
    conn: sqlite3.Connection, shift_id: str, contract: ContractParams
) -> ArtifactVersion:
    """Freeze ONE immutable, content-hashed version of the draft + contract.

    The hash covers the frozen files, the ContractParams and the catalog hash, so
    any later change to a stored version is detected on read (test 21).
    """
    shift = _require_open_shift(conn, shift_id)
    draft = repo.get_draft(conn, shift_id)
    if draft is None:
        raise LifecycleError("conflict", f"no draft to freeze for shift: {shift_id}")
    files, _ = draft

    catalog = contract_catalog.load_catalog(shift.engagement_slug, contract.catalog_version)
    contract_catalog.validate_contract(catalog, contract)

    content_hash = canonical.artifact_content_hash(
        files, canonical.contract_params_json(contract), catalog.content_hash
    )
    ordinal = repo.count_versions(conn) + 1
    parent = repo.get_latest_version(conn, shift_id) or repo.get_latest_version_for_engagement(
        conn, shift.engagement_slug
    )
    version = ArtifactVersion(
        id=f"ver-{ordinal:04d}",
        shift_id=shift_id,
        parent_id=parent.id if parent else None,
        content_hash=content_hash,
        storage_ref=f"inline:{content_hash}",
        files=dict(files),
        contract=contract,
        contract_catalog_hash=catalog.content_hash,
        created_by="learner",
        created_at=_now(),
    )
    repo.insert_version(conn, version)
    conn.commit()
    return version


def start_run(conn: sqlite3.Connection, shift_id: str) -> Run:
    shift = _require_open_shift(conn, shift_id)
    version = repo.get_latest_version(conn, shift_id)
    if version is None:
        raise LifecycleError("conflict", "freeze a version before starting a run")
    used = repo.count_runs(conn, shift_id)
    limit = _attempt_limit(conn, shift.engagement_slug)
    if used >= limit:
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
        version = repo.get_version(conn, run.artifact_version_id)
        request = executor.RunRequest(
            artifact_snapshot=executor.ArtifactSnapshotRef(
                files={path: text.encode("utf-8") for path, text in version.files.items()},
                manifest_hash=version.content_hash,
            ),
            request_batch=executor.BatchRef(path_ref="thin.jsonl", content_hash=config.THIN_BATCH_HASH),
            shop_snapshot_ref=str(config.BOOKSHOP_SNAPSHOT),
            harness_ref="stdlib-loopback-v1",
            image_ref="local-python-stdlib",
            deadline_s=5,
            inference_grant=None,
        )
        batch = {entry.ordinal: entry for entry in executor.load_batch(request.request_batch)}
        result = asyncio.run(_adapter().execute(request))
        outputs = []
        for output in executor.normalize_captures(result.captures, request.deadline_s):
            output = output.model_copy(update={
                "id": f"{run.id}-out-{output.request_ordinal}",
                "run_id": run.id,
                "request_text": batch[output.request_ordinal].text,
            })
            repo.insert_output(conn, output)
            outputs.append(output)
        if result.failure is not None:
            repo.update_run(conn, run_id, RunState.FAILED, result.failure, _now())
        else:
            repo.update_run(conn, run_id, RunState.CAPTURED)
            _finalize(conn, run, outputs)
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


def _public_records(snapshot_path: Path) -> dict[str, JsonValue]:
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return {record["record_id"]: record for record in data["records"]}


def _finalize(conn: sqlite3.Connection, run: Run, outputs: list[RunOutput]) -> None:
    """Real finalization: evaluate the drawn sealed cases, reduce to chained events.

    Slice 4 scores every captured response against the sealed family inventory
    (the whole first family while variant rotation does not exist) under the
    version's committed contract, then reduces the failing checks into
    hash-chained ledger drafts. No incident is opened (that is a later slice);
    the run ends FINALIZED with real CheckResults and real LedgerEvents
    persisted. The run-consumed snapshot is the same file the executor received.
    """
    shift = _require_shift(conn, run.shift_id)
    version = repo.get_version(conn, run.artifact_version_id)
    if version is None:
        raise LifecycleError("not_found", f"unknown artifact version: {run.artifact_version_id}")
    cases = sealed_store.load_drawn_cases(run.id)
    public_records = _public_records(config.BOOKSHOP_SNAPSHOT)
    mission = reducer.load_mission(config.BOOKSHOP_MISSION)

    check_results: list[CheckResult] = []
    for result in evaluator.evaluate(outputs, cases, version.contract, public_records):
        result = result.model_copy(
            update={"id": f"cr-{repo.count_check_results(conn) + len(check_results) + 1:04d}"}
        )
        repo.insert_check_result(conn, result)
        check_results.append(result)

    drafts = reducer.reduce_run(mission, run, check_results)
    existing = repo.list_ledger_events(conn, shift.engagement_slug)
    seq = chain.next_seq(existing)
    prev_hash = chain.next_prev_hash(existing)
    for draft in drafts:
        event = chain.seal_draft(draft, seq=seq, prev_hash=prev_hash)
        repo.insert_ledger_event(conn, shift.engagement_slug, event)
        seq = event.seq + 1
        prev_hash = event.hash


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
    events = repo.list_ledger_events(conn, slug)
    return {
        "events": events,
        "chain_status": chain.verify_chain(events).value,
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
    attempt_limit = _attempt_limit(conn, slug)
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
        "attempt_limit": attempt_limit,
        "attempts_remaining": attempt_limit - attempts_used,
        "open_incidents": [incident for incident in incidents if incident.state == IncidentState.OPEN],
        "total_incidents": len(incidents),
        "ledger_event_count": len(events),
        "ledger_totals": totals,
        "chain_status": chain.verify_chain(events).value,
    }
