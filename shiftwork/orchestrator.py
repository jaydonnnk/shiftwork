"""Thin real vertical path: open shift, edit draft, freeze, run, real finalize, close.

Slice 2 replaces the tracer's stub persistence and stub finalization with the real
deterministic components: content-hashed freeze, the recorded adapter replaying one
checked-in transcript, the sealed-case evaluator producing one real CheckResult, and
the reducer plus hash chain producing one real LedgerEvent. Slice 7 adds budget
enforcement with per-attempt rotation draws, binds each run to the request batch and
shop snapshot it consumed, and resolves incidents only when a later run of a new
version passes the linked regression and that family's current unseen variant.
Slice 8 makes the run row the single source of execution identity: ``start_run``
persists the controller-configured executor and shop snapshot, and ``execute_run``
resolves the adapter from those persisted values, with an unmapped recorded pairing
or an unimplemented adapter failing closed as a typed PROVISION_FAILED. Slice 8
also lands close and inheritance: ``close_shift`` records the committed declared
limits as hash-chained LIMIT_DECLARED events and retires unresolved incidents as
CLOSED_UNRESOLVED rows in one transaction, ``open_next_shift`` seeds the next
draft from the inherited version, and ``reconcile_interrupted`` fails the runs a
restart left nonterminal while keeping their captures and draws.
"""

import asyncio
import base64
import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shiftwork import config
from shiftwork.domain import canonical, contract_catalog, customer_answer
from shiftwork.domain.errors import ServiceResponseInvalid
from shiftwork.domain.models import (
    ArtifactVersion,
    CheckResult,
    CloseShiftFacts,
    ContractParams,
    DrawState,
    ExecutorFailure,
    Incident,
    IncidentState,
    JsonValue,
    LedgerEventDraft,
    LedgerEventType,
    RotationDraw,
    Run,
    RunOutput,
    RunState,
    ServiceResponse,
    Shift,
)
from shiftwork.evaluator import evaluator
from shiftwork.executor import base as executor
from shiftwork.executor.local_process import LocalProcessAdapter
from shiftwork.executor.recorded import RecordedAdapter
from shiftwork.ledger import chain, reducer
from shiftwork.sealed import rotation
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


def _enabled_families(conn: sqlite3.Connection, slug: str) -> tuple[str, ...]:
    row = repo.get_engagement_config(conn, slug)
    if row is None:
        return config.BOOKSHOP_FAMILIES
    return tuple(json.loads(row["enabled_check_families_json"]))


def _attempt_batch(ordinal: int) -> executor.BatchRef:
    """The frozen stimulus prefix this attempt executes (program design S5.3).

    The drawn variants share one request ordinal k; the run executes the customer
    requests 1..k and nothing later, so future stimuli stay absent until their run.
    """
    refs = config.BOOKSHOP_ATTEMPT_BATCHES
    if not 1 <= ordinal <= len(refs):
        raise LifecycleError("conflict", f"no stimulus batch exists for request ordinal {ordinal}")
    path_ref = refs[ordinal - 1]
    path = config.FIXTURE_DIR / "requests" / path_ref
    content_hash = canonical.content_hash(base64.b64encode(path.read_bytes()).decode("ascii"))
    return executor.BatchRef(path_ref=path_ref, content_hash=content_hash)


def _adapter_for(run: Run, snapshot_bytes: bytes) -> executor.ExecutorAdapter | None:
    """Resolve the executor the run row names, or None to fail closed.

    Recorded runs replay the transcript the authored map pairs with the run's own
    frozen batch and the snapshot it consumed. The caller passes the captured
    snapshot bytes, so transcript selection uses the same bytes the run executes
    against, never a re-read of the mutable source path. An absent pairing and an
    adapter with no implementation here (tokenfactory before Slice 14) resolve to
    None, which ``execute_run`` records as a typed PROVISION_FAILED failure. No
    other pair's transcript is ever substituted.
    """
    if run.adapter == "local_process":
        return LocalProcessAdapter()
    if run.adapter != "recorded":
        return None
    snapshot_hash = canonical.content_hash(base64.b64encode(snapshot_bytes).decode("ascii"))
    ref = config.RECORDED_TRANSCRIPTS.get((run.request_batch_ref, snapshot_hash))
    if ref is None:
        return None
    transcript = Path(ref)
    if not transcript.is_absolute():
        transcript = config.FIXTURE_DIR / "runs" / transcript
    return RecordedAdapter(transcript)


def open_next_shift(conn: sqlite3.Connection, slug: str = config.BOOKSHOP_SLUG) -> Shift:
    """Open the next shift, seeded from the engagement's inheritance (S5.1).

    The seed is the latest artifact version: its files become the new draft, so
    the learner continues from the inherited artifact (the shipped template
    applies only when no version exists yet). Unresolved incidents (OPEN and
    CLOSED_UNRESOLVED), declared limits and the ledger summary are engagement
    rows read live by the board, so they carry forward without a copy. A shift
    that is still open refuses a second open with a conflict.
    """
    if repo.get_engagement(conn, slug) is None:
        raise LifecycleError("not_found", f"unknown engagement: {slug}")
    current = repo.get_latest_shift(conn, slug)
    if current is not None and current.state == "open":
        raise LifecycleError("conflict", f"shift {current.id} is still open; close it first")
    seq = repo.max_shift_seq(conn, slug) + 1
    shift = Shift(
        id=f"{slug}-shift-{seq:02d}",
        engagement_slug=slug,
        seq=seq,
        state="open",
        opened_at=_now(),
    )
    repo.insert_shift(conn, shift)
    inherited = repo.get_latest_version_for_engagement(conn, slug)
    files = dict(inherited.files) if inherited is not None else BOOKSHOP_DRAFT_FILES
    repo.upsert_draft(conn, shift.id, files, shift.opened_at)
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


def start_run(
    conn: sqlite3.Connection,
    shift_id: str,
    *,
    executor: str | None = None,
    shop_snapshot: str | Path | None = None,
) -> Run:
    """Reserve one attempt: budget check, one never-exposed draw per family, atomically.

    The whole reservation - run row, its frozen batch and snapshot refs, and one
    draw per enabled family - commits in one transaction, so a concurrent boundary
    POST cannot produce two runs and a fault between the run row and the draws
    rolls the entire reservation back (program design S5.3, tests 24 and 25).

    The run persists the controller-configured adapter and the shop snapshot it
    consumes (Slice 8); the learner never supplies either through the API, and
    ``execute_run`` resolves the adapter from these persisted values. Callers that
    pass nothing get the shipped controller defaults.

    The artifact version in force is this shift's own latest version, or the
    inherited one before the learner freezes their own: a shift that opens from
    inheritance can run the system it inherited without re-freezing identical
    bytes (program design S5.1/S5.3).
    """
    shift = _require_open_shift(conn, shift_id)
    version = repo.get_latest_version(conn, shift_id) or repo.get_latest_version_for_engagement(
        conn, shift.engagement_slug
    )
    if version is None:
        raise LifecycleError("conflict", "freeze a version before starting a run")

    conn.execute("BEGIN IMMEDIATE")
    try:
        used = repo.count_runs(conn, shift_id)
        limit = _attempt_limit(conn, shift.engagement_slug)
        if used >= limit:
            raise LifecycleError("conflict", "attempt budget exhausted for this shift")

        drawn: dict[str, Any] = {}
        exposed = {draw.variant_ref for draw in repo.list_rotation_draws(conn, shift.engagement_slug)}
        for family in _enabled_families(conn, shift.engagement_slug):
            drawn[family] = rotation.select_variant(family, sealed_store.load_family(family).cases, exposed)
        request_batch = _attempt_batch(rotation.shared_ordinal(drawn))

        ordinal = repo.count_runs_all(conn) + 1
        run = Run(
            id=f"run-{ordinal:04d}",
            shift_id=shift_id,
            artifact_version_id=version.id,
            request_batch_ref=request_batch.path_ref,
            shop_snapshot_ref=str(shop_snapshot or config.BOOKSHOP_SNAPSHOT),
            attempt_number=used + 1,
            state=RunState.QUEUED,
            adapter=executor or config.EXECUTOR_ADAPTER,
            started_at=_now(),
        )
        repo.insert_run(conn, run)
        for family, case in drawn.items():
            repo.insert_rotation_draw(
                conn,
                RotationDraw(
                    id=f"draw-{run.id}-{family}",
                    engagement_slug=shift.engagement_slug,
                    family=family,
                    variant_ref=rotation.variant_ref(case),
                    run_id=run.id,
                    cycle=sealed_store.family_cycle(family),
                    drawn_at=_now(),
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return run


def execute_run(conn: sqlite3.Connection, run_id: str) -> Run:
    """Execute a queued run against the snapshot bytes it captures here.

    The controller reads the configured snapshot once, persists those exact bytes
    on the run and provisions the adapter from a controller-owned copy, so
    transcript selection, execution, scoring and the client's later comparison all
    resolve the same bytes even if the source path is edited or removed (Slice 9).
    """
    run = repo.get_run(conn, run_id)
    if run is None:
        raise LifecycleError("not_found", f"unknown run: {run_id}")
    if run.state is not RunState.QUEUED:
        return run
    try:
        snapshot_bytes = Path(run.shop_snapshot_ref).read_bytes()
    except OSError:
        # Fail closed, typed: an unreadable snapshot is a provisioning failure,
        # never a reason to execute against a different snapshot.
        repo.update_run(conn, run_id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED, _now())
        conn.commit()
        return repo.get_run(conn, run_id)
    adapter = _adapter_for(run, snapshot_bytes)
    if adapter is None:
        # Fail closed, typed: an unmapped recorded pairing or an adapter with no
        # implementation here never replays something else and writes no captures.
        repo.update_run(conn, run_id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED, _now())
        conn.commit()
        return repo.get_run(conn, run_id)
    repo.update_run(conn, run_id, RunState.RUNNING)
    repo.set_run_snapshot_bytes(conn, run_id, snapshot_bytes)
    conn.commit()
    try:
        version = repo.get_version(conn, run.artifact_version_id)
        batch_path = config.FIXTURE_DIR / "requests" / run.request_batch_ref
        with tempfile.TemporaryDirectory(prefix="shiftwork-run-snapshot-") as snapshot_dir:
            snapshot_path = Path(snapshot_dir) / "shop_snapshot.json"
            snapshot_path.write_bytes(snapshot_bytes)
            request = executor.RunRequest(
                artifact_snapshot=executor.ArtifactSnapshotRef(
                    files={path: text.encode("utf-8") for path, text in version.files.items()},
                    manifest_hash=version.content_hash,
                ),
                request_batch=executor.BatchRef(
                    path_ref=run.request_batch_ref,
                    content_hash=canonical.content_hash(base64.b64encode(batch_path.read_bytes()).decode("ascii")),
                ),
                shop_snapshot_ref=str(snapshot_path),
                harness_ref="stdlib-loopback-v1",
                image_ref="local-python-stdlib",
                deadline_s=5,
                inference_grant=None,
            )
            batch = {entry.ordinal: entry for entry in executor.load_batch(request.request_batch)}
            result = asyncio.run(adapter.execute(request))
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


def _public_records(snapshot_bytes: bytes) -> dict[str, JsonValue]:
    data = json.loads(snapshot_bytes)
    return {record["record_id"]: record for record in data["records"]}


def _snapshot_bytes_for_run(conn: sqlite3.Connection, run: Run) -> bytes:
    """The shop snapshot bytes this run consumed (Slice 9 run binding).

    Runs executed under the current controller carry their captured bytes; a run
    that predates the capture falls back to reading the recorded path, which is
    best effort and may raise OSError if that source no longer exists.
    """
    stored = repo.get_run_snapshot_bytes(conn, run.id)
    if stored is not None:
        return stored
    return Path(run.shop_snapshot_ref).read_bytes()


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


def _incident_case(conn: sqlite3.Connection, incident: Incident):
    """The sealed case behind an incident's failing check, by internal check id."""
    failing = next(
        (
            result
            for result in repo.list_check_results(conn, incident.opening_run_id)
            if result.id == incident.check_result_id
        ),
        None,
    )
    if failing is None:
        return None
    return sealed_store.case_for_check_id(failing.check_id)


def _resolution_drafts(
    conn: sqlite3.Connection,
    run: Run,
    cases,
    check_results: list[CheckResult],
) -> list[tuple[str, LedgerEventDraft]]:
    """Resolution drafts this run has earned (program design S5.7).

    An unresolved incident (OPEN, or CLOSED_UNRESOLVED after a close inherited it)
    resolves only when all three hold: the linked regression passes in this run,
    the run is not the incident's opening run's version, and this run's drawn
    (never-exposed) variant for the same family passes. Re-running an old
    regression alone never resolves anything, and a repeated version is not a
    repair.
    """
    results_by_check = {result.check_id: result for result in check_results}
    drawn_refs = {draw.variant_ref for draw in repo.list_rotation_draws_for_run(conn, run.id)}
    drawn_by_family = {
        case.family: case for case in cases.cases if rotation.variant_ref(case) in drawn_refs
    }
    slug = run.shift_id.rsplit("-shift-", 1)[0]
    resolutions: list[tuple[str, LedgerEventDraft]] = []
    for incident in repo.list_incidents(conn, slug):
        if incident.state is IncidentState.RESOLVED:
            continue
        linked = _incident_case(conn, incident)
        if linked is None:
            continue
        regression = results_by_check.get(linked.check_id)
        if regression is None or regression.verdict != "pass":
            continue
        opening = repo.get_run(conn, incident.opening_run_id)
        if opening is None or opening.artifact_version_id == run.artifact_version_id:
            continue
        acceptance = drawn_by_family.get(linked.family)
        acceptance_result = results_by_check.get(acceptance.check_id) if acceptance else None
        if acceptance_result is None or acceptance_result.verdict != "pass":
            continue
        resolutions.append(
            (
                incident.id,
                LedgerEventDraft(
                    event_type=LedgerEventType.INCIDENT_RESOLVED,
                    cause_refs=(run.id, regression.id, regression.observed_ref, incident.id),
                    payload={
                        "reason_code": incident.reason_code.value,
                        "incident_id": incident.id,
                        "family": linked.family,
                        "resolving_version_id": run.artifact_version_id,
                    },
                ),
            )
        )
    return resolutions


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
    cases = sealed_store.load_drawn_cases(conn, run_id)
    # Score against the snapshot this run actually consumed - its captured bytes,
    # never the module default or a re-read of the mutable path (Slice 5 review's
    # latent bug; program design S5.3/S5.5).
    public_records = _public_records(_snapshot_bytes_for_run(conn, run))
    mission = reducer.load_mission(config.BOOKSHOP_MISSION)

    try:
        check_results: list[CheckResult] = []
        for result in evaluator.evaluate(outputs, cases, version.contract, public_records):
            # count_check_results sees this transaction's earlier inserts, so the
            # ordinal is not double-counted by len(check_results).
            result = result.model_copy(
                update={"id": f"cr-{repo.count_check_results(conn) + 1:04d}"}
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
        resolutions = _resolution_drafts(conn, run, cases, check_results)
        existing = repo.list_ledger_events(conn, shift.engagement_slug)
        events = chain.append(
            drafts + [draft for _, draft in resolutions],
            prev_hash=chain.next_prev_hash(existing),
            start_seq=chain.next_seq(existing),
        )
        for event in events:
            repo.insert_ledger_event(conn, shift.engagement_slug, event)
        _open_incidents(conn, run, pairs, events)
        for (incident_id, _draft), event in zip(resolutions, events[len(drafts):]):
            repo.resolve_incident(conn, incident_id, run.artifact_version_id, event.seq)
        repo.update_run(conn, run_id, RunState.FINALIZED, ended_at=_now())
        conn.commit()
    except Exception:
        conn.rollback()
        repo.update_run(conn, run_id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
        conn.commit()
        raise
    return repo.get_run(conn, run_id)


def close_shift(conn: sqlite3.Connection, shift_id: str) -> Shift:
    """Close the shift atomically and idempotently (program design S5.8).

    One transaction: refuse while a run of this shift is nonterminal; capture
    ``CloseShiftFacts`` from the artifact version in force (this shift's own
    latest version, or the inherited one when the shift never froze its own);
    append the hash-chained LIMIT_DECLARED events for its declared limits exactly
    once; retire the engagement's unresolved OPEN incidents as CLOSED_UNRESOLVED
    rows (inherited as incidents, never as LIMIT_DECLARED events); mark the shift
    closed. An already closed shift returns without writes, so a retried or
    concurrent close cannot append a second event set, and a fault anywhere
    leaves neither a partial close nor partial events.
    """
    shift = _require_shift(conn, shift_id)
    conn.execute("BEGIN IMMEDIATE")
    try:
        shift = _require_shift(conn, shift_id)
        if shift.state == "closed":
            conn.rollback()
            return shift
        in_flight = [
            run.id
            for run in repo.list_runs_for_shift(conn, shift_id)
            if run.state not in (RunState.FINALIZED, RunState.FAILED)
        ]
        if in_flight:
            raise LifecycleError("conflict", "run in flight; close refused: " + ", ".join(in_flight))
        version = repo.get_latest_version(conn, shift_id) or repo.get_latest_version_for_engagement(
            conn, shift.engagement_slug
        )
        drafts: list[LedgerEventDraft] = []
        if version is not None:
            facts = CloseShiftFacts(
                shift_id=shift.id,
                declared_limits=tuple(version.contract.declared_limits),
                unresolved_incident_ids=tuple(
                    incident.id
                    for incident in repo.list_incidents(conn, shift.engagement_slug)
                    if incident.state is IncidentState.OPEN
                ),
                committed_contract=version.contract,
            )
            drafts = reducer.reduce_close(reducer.load_mission(config.BOOKSHOP_MISSION), facts)
        existing = repo.list_ledger_events(conn, shift.engagement_slug)
        events = chain.append(
            drafts,
            prev_hash=chain.next_prev_hash(existing),
            start_seq=chain.next_seq(existing),
        )
        for event in events:
            repo.insert_ledger_event(conn, shift.engagement_slug, event)
        repo.close_unresolved_incidents(conn, shift.engagement_slug)
        repo.close_shift(conn, shift_id, _now())
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return _require_shift(conn, shift_id)


def reconcile_interrupted(conn: sqlite3.Connection) -> list[str]:
    """Startup recovery (S3.6, S6.B.9): fail the runs a restart left nonterminal.

    A restart can leave runs in QUEUED, RUNNING or CAPTURED; none of them
    resumes. Each is marked FAILED with the typed INTERNAL failure kind (the
    interruption is the controller's, not the service's) while its completed
    captures, log bytes and rotation draws stay byte-for-byte intact and no
    checks or events are written. FINALIZED and FAILED runs are untouched, so
    the call is idempotent. Returns the reconciled run ids.

    Startup is the only reconciliation point (``app.py`` lifespan is the sole call
    site): a run left nonterminal while the app keeps running, for example one
    whose background task never executes, is not reconciled until the process
    restarts, and ``close_shift`` refuses that shift until then.
    """
    reconciled: list[str] = []
    for run in repo.list_nonterminal_runs(conn):
        repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
        reconciled.append(run.id)
    if reconciled:
        conn.commit()
    return reconciled


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


def _stimulus_record(run: Run, ordinal: int, records: dict[str, JsonValue]) -> JsonValue | None:
    """The public record the executed request ordinal asked about, or None.

    The stimulus comes from the run's persisted request batch; any unavailable or
    inconsistent source degrades to None instead of failing the caller.
    """
    try:
        batch_path = config.FIXTURE_DIR / "requests" / run.request_batch_ref
        batch = executor.load_batch(executor.BatchRef(
            path_ref=run.request_batch_ref,
            content_hash=canonical.content_hash(base64.b64encode(batch_path.read_bytes()).decode("ascii")),
        ))
    except (OSError, ValueError, KeyError):
        return None
    stimulus = next((entry for entry in batch if entry.ordinal == ordinal), None)
    if stimulus is None:
        return None
    try:
        body = json.loads(stimulus.body)
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None
    return records.get(body.get("record_id"))


def output_evidence_for(conn: sqlite3.Connection, output: RunOutput, run: Run) -> dict[str, Any]:
    """Public comparison follows the executed request, not service citations or sealed checks.

    Records and hash come from the bytes this run captured at execution, so an
    edited or deleted source path cannot change what the run is said to have
    consumed. An unavailable snapshot or stimulus degrades only the optional
    comparison fields; the stored answer and the raw captured bytes stay
    retrievable (Slice 9 review, findings 2 and 3).
    """
    evidence: dict[str, Any] = {
        "customer_answer": None,
        "public_shop_record": None,
        "public_shop_record_ref": None,
        "public_shop_snapshot_hash": None,
    }
    records: dict[str, JsonValue] = {}
    try:
        snapshot_bytes = _snapshot_bytes_for_run(conn, run)
        records = _public_records(snapshot_bytes)
    except (OSError, ValueError):
        snapshot_bytes = None
    record = _stimulus_record(run, output.request_ordinal, records) if snapshot_bytes else None
    if record is not None:
        evidence.update({
            "public_shop_record": {
                "record_id": record["record_id"],
                "kind": record["kind"],
                "title": record.get("title"),
                "edition": record.get("edition"),
                "value": record["value"],
                "record_age_ms": record["record_age_ms"],
            },
            "public_shop_record_ref": record["record_id"],
            "public_shop_snapshot_hash": canonical.content_hash(
                base64.b64encode(snapshot_bytes).decode("ascii")
            ),
        })
    try:
        response = ServiceResponse.model_validate_json(output.body)
        validated = customer_answer.validate_service_response(response, records)
    except (ValueError, ServiceResponseInvalid):
        return evidence
    evidence["customer_answer"] = {
        "action": validated.action,
        "display_text": customer_answer.render_customer_text(validated),
        "claims": validated.claims,
        "evidence_refs": validated.evidence_refs,
        "verified_record_age_ms": validated.verified_record_age_ms,
    }
    return evidence


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
    if latest_version is None and latest_shift is not None:
        # A freshly opened shift has no version of its own yet; the board shows
        # the inherited one until the learner freezes their own (Slice 8).
        latest_version = repo.get_latest_version_for_engagement(conn, slug)
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
        "artifact_files": tuple(sorted(latest_version.files)) if latest_version else (),
        "requests_run": requests_run,
        "attempts_used": attempts_used,
        "attempt_limit": attempt_limit,
        "attempts_remaining": attempt_limit - attempts_used,
        "incidents": [
            incident
            for incident in incidents
            if incident.state in (IncidentState.OPEN, IncidentState.CLOSED_UNRESOLVED)
        ],
        "total_incidents": len(incidents),
        "unresolved_limits": repo.list_unresolved_limits(conn, slug),
        "ledger_event_count": len(events),
        "ledger_totals": totals,
        "chain_status": status.value,
    }
