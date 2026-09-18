"""Thin real vertical path: open shift, edit draft, freeze, run, real finalize, close.

Slice 2 replaces the tracer's stub persistence and stub finalization with the real
deterministic components: content-hashed freeze, the recorded adapter replaying one
checked-in transcript, the sealed-case evaluator producing one real CheckResult, and
the reducer plus hash chain producing one real LedgerEvent. Incident opening is a
later slice (S5/S7); Slice 2 opens no incident.
"""

import asyncio
import base64
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shiftwork import config
from shiftwork.domain import canonical, contract_catalog, customer_answer
from shiftwork.domain.errors import ServiceResponseInvalid
from shiftwork.domain.models import (
    ArtifactVersion,
    CheckResult,
    ContractParams,
    ExecutorFailure,
    Incident,
    IncidentState,
    JsonValue,
    LedgerEventType,
    Run,
    RunOutput,
    RunState,
    ServiceResponse,
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
            conn.commit()
        else:
            repo.update_run(conn, run_id, RunState.CAPTURED)
            conn.commit()
            finalize_run(conn, run_id)
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


def _open_incidents(
    conn: sqlite3.Connection,
    run: Run,
    pairs: list[tuple[CheckResult, reducer.MissionTransition]],
    events: list,
) -> None:
    """Open one incident per failing check whose transition is INCIDENT_OPENED."""
    slug = run.shift_id.rsplit("-shift-", 1)[0]
    for (result, transition), event in zip(pairs, events):
        if transition.event_type is not LedgerEventType.INCIDENT_OPENED:
            continue
        ordinal = repo.count_incidents(conn, slug) + 1
        repo.insert_incident(
            conn,
            Incident(
                id=f"{config.INCIDENT_PREFIX}-{ordinal:02d}",
                engagement_slug=slug,
                shift_id=run.shift_id,
                opening_run_id=run.id,
                failing_output_ref=result.observed_ref,
                check_result_id=result.id,
                reason_code=result.reason_code,
                opened_event_seq=event.seq,
                state=IncidentState.OPEN,
            ),
        )


def finalize_run(conn: sqlite3.Connection, run_id: str) -> Run:
    """Evaluate -> reduce -> chain -> events -> incidents -> FINALIZED (S5.5).

    The whole sequence commits as one transaction: a failure anywhere leaves no
    check results and no ledger events and marks the run FAILED. Re-finalizing
    an already-finalized run is a no-op (zero net new events, no duplicate
    incidents), which is the idempotency the repair loop and restart recovery
    rely on.
    """
    run = repo.get_run(conn, run_id)
    if run is None:
        raise LifecycleError("not_found", f"unknown run: {run_id}")
    if run.state is RunState.FINALIZED or repo.list_check_results(conn, run_id):
        return run

    shift = _require_shift(conn, run.shift_id)
    version = repo.get_version(conn, run.artifact_version_id)
    if version is None:
        raise LifecycleError("not_found", f"unknown artifact version: {run.artifact_version_id}")
    outputs = repo.list_outputs(conn, run_id)
    cases = sealed_store.load_drawn_cases(run_id)
    public_records = _public_records(config.BOOKSHOP_SNAPSHOT)
    mission = reducer.load_mission(config.BOOKSHOP_MISSION)

    try:
        check_results: list[CheckResult] = []
        for result in evaluator.evaluate(outputs, cases, version.contract, public_records):
            result = result.model_copy(
                update={"id": f"cr-{repo.count_check_results(conn) + len(check_results) + 1:04d}"}
            )
            repo.insert_check_result(conn, result)
            check_results.append(result)

        pairs: list[tuple[CheckResult, reducer.MissionTransition]] = []
        for result in check_results:
            if result.verdict != "fail" or result.reason_code is None:
                continue
            transition = reducer.transition_for(mission, result.reason_code)
            if transition is not None:
                pairs.append((result, transition))

        drafts = reducer.reduce(mission, outputs, check_results, version.contract)
        existing = repo.list_ledger_events(conn, shift.engagement_slug)
        events = chain.append(
            drafts,
            prev_hash=chain.next_prev_hash(existing),
            start_seq=chain.next_seq(existing),
        )
        for event in events:
            repo.insert_ledger_event(conn, shift.engagement_slug, event)
        _open_incidents(conn, run, pairs, events)
        repo.update_run(conn, run_id, RunState.FINALIZED, ended_at=_now())
        conn.commit()
    except Exception:
        conn.rollback()
        repo.update_run(conn, run_id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
        conn.commit()
        raise
    return repo.get_run(conn, run_id)


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


def customer_text_for(output: RunOutput) -> str | None:
    """Derive the customer-facing sentence from an output's raw body (S5.6).

    Returns None when the body does not parse, a cited ref resolves to no public
    record, or the attested age is false; the exact raw bytes stay available as
    ``body_base64`` on the view.
    """
    try:
        response = ServiceResponse.model_validate_json(output.body)
        validated = customer_answer.validate_service_response(
            response, _public_records(config.BOOKSHOP_SNAPSHOT)
        )
    except (ValueError, ServiceResponseInvalid):
        return None
    return customer_answer.render_customer_text(validated)


def _resolve_derivation(conn: sqlite3.Connection, event) -> dict[str, Any] | None:
    """Resolve an event's cause refs to the raw run/check/output records."""
    if len(event.cause_refs) < 3:
        return None
    run_id, check_id, observed_ref = event.cause_refs[0], event.cause_refs[1], event.cause_refs[2]
    outputs = repo.list_outputs(conn, run_id)
    output = next((item for item in outputs if item.id == observed_ref), None)
    checks = repo.list_check_results(conn, run_id)
    check = next((item for item in checks if item.id == check_id), None)
    if output is None or check is None:
        return None
    return {
        "run_id": run_id,
        "check_id": check_id,
        "observed_ref": observed_ref,
        "request_ordinal": output.request_ordinal,
        "request_text": output.request_text,
        "output_body_base64": base64.b64encode(output.body).decode("ascii"),
        "verdict": check.verdict,
        "reason_code": check.reason_code.value if check.reason_code else None,
    }


def _resolve_catalog(slug: str, event) -> dict[str, Any] | None:
    """Resolve an event payload's catalog_version reference to the raw catalog record."""
    version = event.payload.get("catalog_version")
    if not isinstance(version, int):
        return None
    path = config.CATALOG_DIR / f"{slug}_v{version}.json"
    if not path.exists():
        return None
    return {"catalog_version": version, "catalog_record": json.loads(path.read_text(encoding="utf-8"))}


def ledger(conn: sqlite3.Connection, slug: str) -> dict[str, Any]:
    if repo.get_engagement(conn, slug) is None:
        raise LifecycleError("not_found", f"unknown engagement: {slug}")
    events = repo.list_ledger_events(conn, slug)
    status = chain.verify_chain(events)
    if status is chain.ChainStatus.BROKEN:
        raise LifecycleError("conflict", "ledger chain is BROKEN; refusing unverified events")
    enriched = []
    for event in events:
        enriched.append(
            {
                "seq": event.seq,
                "event_type": event.event_type.value,
                "cause_refs": list(event.cause_refs),
                "payload": event.payload,
                "synthetic": event.synthetic,
                "prev_hash": event.prev_hash,
                "hash": event.hash,
                "derivation": _resolve_derivation(conn, event),
                "catalog": _resolve_catalog(slug, event),
            }
        )
    return {"events": enriched, "chain_status": status.value}


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
    status = chain.verify_chain(events)
    if status is chain.ChainStatus.BROKEN:
        raise LifecycleError("conflict", "ledger chain is BROKEN; refusing board counters")
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
        "chain_status": status.value,
    }
