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
import hashlib
import json
import os
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shiftwork import config
from shiftwork.assist.gateway import (
    AssistGateway, AssistRejected, ASSIST_SYSTEM_MESSAGE, MAX_INPUT_BYTES, SAFE_FAILURE_CODES,
)
from shiftwork.domain import canonical, contract_catalog, customer_answer, task_contract
from shiftwork.domain.errors import (
    AssistGatewayUnavailable,
    BootstrapBlocked,
    InvestigationIncomplete,
    ServiceResponseInvalid,
    ShiftworkDomainError,
    TaskEnvelopeInvalid,
)
from shiftwork.domain.models import (
    ArtifactVersion,
    AssistEvent,
    AssistRole,
    CandidateRef,
    CheckResult,
    CloseShiftFacts,
    ContextCondition,
    ContractParams,
    EvidenceMode,
    ExecutionObservation,
    ExecutionContext,
    ExecutorFailure,
    Experiment,
    ExperimentKind,
    FrozenWorkload,
    Incident,
    IncidentState,
    Investigation,
    InvestigationRequest,
    JsonValue,
    LedgerEventDraft,
    LedgerEventType,
    OperatingSelection,
    RotationDraw,
    Run,
    RunAssessment,
    RunOutput,
    RunPurpose,
    RunState,
    ObservationKind,
    ServiceResponse,
    Shift,
    ShiftOpeningMode,
)
from shiftwork.evaluator import evaluator
from shiftwork.executor import base as executor
from shiftwork.executor.local_process import LocalProcessAdapter
from shiftwork.executor.recorded import RecordedAdapter
from shiftwork.executor.tokenfactory import TokenFactoryAdapter
from shiftwork.gateway.protocol import GATEWAY_MAX_OUTPUT_TOKENS
from shiftwork.gateway.redaction import assert_public_safe
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


def _selected_operating_version(
    conn: sqlite3.Connection, shift: Shift
) -> tuple[OperatingSelection, ArtifactVersion]:
    selection = repo.get_latest_operating_selection(conn, shift.engagement_slug)
    if selection is None or selection.state != "VALID":
        raise LifecycleError("conflict", "explicit valid selection required before operation")
    version = repo.get_version(conn, selection.selected_version_id)
    owner = repo.get_shift(conn, version.shift_id) if version else None
    if (
        version is None
        or owner is None
        or owner.engagement_slug != shift.engagement_slug
        or version.content_hash != selection.selected_content_hash
    ):
        raise LifecycleError("conflict", "selected version is missing or changed")
    return selection, version


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
    """Open a selected shift or a non-operational first-choice shift atomically."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        if repo.get_engagement(conn, slug) is None:
            raise LifecycleError("not_found", f"unknown engagement: {slug}")
        current = repo.get_latest_shift(conn, slug)
        if current is not None and current.state == "open":
            raise LifecycleError("conflict", f"shift {current.id} is still open; close it first")
        selection = repo.get_latest_operating_selection(conn, slug)
        if selection is not None and selection.state != "VALID":
            raise LifecycleError("conflict", "operating selection is invalidated")

        seq = repo.max_shift_seq(conn, slug) + 1
        is_first_shift = current is None
        if is_first_shift and selection is not None:
            raise LifecycleError("conflict", "starter selection has no owning shift")
        is_legacy_first_choice = (
            current is not None and current.opening_mode is None and selection is None
        )
        if not is_first_shift and not is_legacy_first_choice and selection is None:
            raise LifecycleError("conflict", "an explicit operating selection is required")
        shift = Shift(
            id=f"{slug}-shift-{seq:02d}",
            engagement_slug=slug,
            seq=seq,
            state="open",
            opened_at=_now(),
            opening_mode=(
                ShiftOpeningMode.LEGACY_FIRST_CHOICE
                if is_legacy_first_choice
                else ShiftOpeningMode.STANDARD
            ),
        )
        repo.insert_shift(conn, shift)

        if is_first_shift:
            if slug != config.BOOKSHOP_SLUG:
                raise LifecycleError("conflict", "reviewed initial starter is unavailable")
            # Slice 11 supplies the reviewed, executable failing starter as the new
            # engagement's editable draft, so the first shift's public diagnostic can
            # run exactly the artifact the learner can read and edit. The pins in
            # config.TRUSTED_LOCAL_FIXTURES are what makes it executable offline.
            files = {
                name: path.read_text(encoding="utf-8")
                for name, path in sorted(config.PIVOT_STARTER_ARTIFACT_PATHS.items())
            }
            contract = ContractParams.model_validate(config.PIVOT_STARTER_CONTRACT_JSON)
            catalog = contract_catalog.load_catalog(slug, contract.catalog_version)
            contract_catalog.validate_contract(catalog, contract)
            content_hash = canonical.artifact_content_hash(
                files, canonical.contract_params_json(contract), catalog.content_hash
            )
            starter = ArtifactVersion(
                id=f"ver-{repo.count_versions(conn) + 1:04d}",
                shift_id=shift.id,
                parent_id=None,
                content_hash=content_hash,
                storage_ref=f"inline:{content_hash}",
                files=dict(files),
                contract=contract,
                contract_catalog_hash=catalog.content_hash,
                created_by="template",
                created_at=shift.opened_at,
            )
            repo.insert_version(conn, starter)
            repo.upsert_draft(conn, shift.id, files, shift.opened_at, starter.id)
            repo.insert_operating_selection(
                conn,
                OperatingSelection(
                    id=f"sel-{repo.count_operating_selections(conn) + 1:04d}",
                    engagement_slug=slug,
                    shift_id=shift.id,
                    kind="STARTER_BASELINE",
                    selected_version_id=starter.id,
                    selected_content_hash=starter.content_hash,
                    rationale="Reviewed failing Bellwether starter; executable offline, not a qualified repair or live service.",
                    requirement_set_hash=canonical.content_hash(
                        {
                            "catalog_hash": catalog.content_hash,
                            "contract": canonical.contract_params_json(contract),
                        }
                    ),
                    state="VALID",
                    client_request_id=f"starter:{slug}",
                    created_at=shift.opened_at,
                ),
            )
        else:
            inherited = (
                repo.get_latest_version_for_engagement(conn, slug)
                if is_legacy_first_choice
                else repo.get_version(conn, selection.selected_version_id)
            )
            if selection is not None and (
                inherited is None or inherited.content_hash != selection.selected_content_hash
            ):
                raise LifecycleError("conflict", "selected version is missing or changed")
            if inherited is None and slug != config.BOOKSHOP_SLUG:
                raise LifecycleError("conflict", "reviewed initial draft is unavailable")
            files = dict(inherited.files) if inherited is not None else dict(BOOKSHOP_DRAFT_FILES)
            repo.upsert_draft(
                conn, shift.id, files, shift.opened_at, inherited.id if inherited else None
            )
        conn.commit()
        return repo.get_shift(conn, shift.id)
    except Exception:
        conn.rollback()
        raise


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

    Operation uses the exact selected version. Saving or freezing another
    candidate leaves the operating pointer unchanged.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        shift = _require_open_shift(conn, shift_id)
        selection, version = _selected_operating_version(conn, shift)
        used = repo.count_operation_runs(conn, shift_id)
        limit = _attempt_limit(conn, shift.engagement_slug)
        if used >= limit:
            raise LifecycleError("conflict", "attempt budget exhausted for this shift")

        drawn: dict[str, Any] = {}
        exposed = {draw.variant_ref for draw in repo.list_rotation_draws(conn, shift.engagement_slug)}
        for family in _enabled_families(conn, shift.engagement_slug):
            drawn[family] = rotation.select_variant(family, sealed_store.load_family(family).cases, exposed)
        request_batch = _attempt_batch(rotation.shared_ordinal(drawn))

        ordinal = repo.count_runs_all(conn) + 1
        adapter = executor or config.EXECUTOR_ADAPTER
        run = Run(
            id=f"run-{ordinal:04d}",
            shift_id=shift_id,
            artifact_version_id=version.id,
            request_batch_ref=request_batch.path_ref,
            shop_snapshot_ref=str(shop_snapshot or config.BOOKSHOP_SNAPSHOT),
            # Numbering counts every run so a diagnostic cannot collide with an
            # operation attempt; the budget check above counts only what spends it.
            attempt_number=repo.count_runs(conn, shift_id) + 1,
            state=RunState.QUEUED,
            adapter=adapter,
            started_at=_now(),
            purpose=RunPurpose.OPERATION,
            selection_id=selection.id,
            evidence_mode=(
                EvidenceMode.RECORDED_INSPECTION
                if adapter == "recorded"
                else EvidenceMode.TRUSTED_LOCAL if adapter == "local_process" else None
            ),
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

    Captured bytes are authoritative. A legacy run without them has unknown
    historical input; reading today's file would fabricate evidence for that run.
    """
    stored = repo.get_run_snapshot_bytes(conn, run.id)
    if stored is not None:
        return stored
    if run.purpose is RunPurpose.LEGACY_OPERATION:
        raise OSError("legacy run has no captured shop snapshot")
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
    ``CloseShiftFacts`` from the exact selected version;
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
        _, version = _selected_operating_version(conn, shift)
        in_flight = [
            run.id
            for run in repo.list_runs_for_shift(conn, shift_id)
            if run.state not in (RunState.FINALIZED, RunState.FAILED)
        ]
        if in_flight:
            raise LifecycleError("conflict", "run in flight; close refused: " + ", ".join(in_flight))
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
    """Startup recovery (S3.6, S6.B.9, S14): fail the work a restart left nonterminal.

    A restart can leave runs in QUEUED, RUNNING or CAPTURED; none of them
    resumes. Each is marked FAILED with the typed INTERNAL failure kind (the
    interruption is the controller's, not the service's) while its completed
    captures, log bytes and rotation draws stay byte-for-byte intact and no
    checks or events are written. A restart can also strand an assist event
    between its committed reservation and its outcome write; each such event is
    marked FAILED with the controller-side ``ASSIST_INTERRUPTED`` code, keeps
    its consumed budget slot and refuses every decision, exactly like a provider
    failure. Terminal, decided, FINALIZED and FAILED rows are untouched, so the
    call is idempotent. Returns the reconciled run and assist event ids.

    Startup is the only reconciliation point (``app.py`` lifespan is the sole call
    site): work left nonterminal while the app keeps running, for example a run
    whose background task never executes or an assist outcome write that failed,
    is not reconciled until the process restarts, and ``close_shift`` refuses
    that shift until its runs are reconciled.
    """
    reconciled: list[str] = []
    for run in repo.list_nonterminal_runs(conn):
        repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
        reconciled.append(run.id)
    for event in repo.list_pending_assist_events(conn):
        repo.finish_assist_event(
            conn, event.id, response="", proposed_patch=None, failure_code=ASSIST_INTERRUPTED
        )
        reconciled.append(event.id)
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
    if run.purpose is RunPurpose.LEGACY_OPERATION:
        return None
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
    latest_saved = repo.get_latest_version(conn, latest_shift.id) if latest_shift else None
    latest_version = latest_saved
    if latest_version is None and latest_shift is not None:
        # A freshly opened shift has no version of its own yet; the board shows
        # the inherited one until the learner freezes their own (Slice 8).
        latest_version = repo.get_latest_version_for_engagement(conn, slug)
    latest_run = repo.get_latest_run(conn, latest_shift.id) if latest_shift else None
    selection = repo.get_latest_operating_selection(conn, slug)
    if latest_shift is None:
        operating_status = None
    elif selection is None:
        operating_status = "NEEDS_FIRST_CHOICE"
    elif selection.state == "INVALIDATED":
        operating_status = "INVALIDATED"
    elif selection.kind == "STARTER_BASELINE":
        operating_status = "STARTER_BASELINE"
    else:
        operating_status = "SELECTED"
    requests_run = len(repo.list_outputs(conn, latest_run.id)) if latest_run else 0
    attempts_used = repo.count_operation_runs(conn, latest_shift.id) if latest_shift else 0
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
        "operating_status": operating_status,
        "draft_base_version_id": (
            repo.get_draft_base_version_id(conn, latest_shift.id) if latest_shift else None
        ),
        "latest_saved_version_id": latest_saved.id if latest_saved else None,
        "operating_selection": selection,
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


# ---------------------------------------------------------------------------
# Slice 11: investigation, orientation and the two denials
# ---------------------------------------------------------------------------

#: Deterministic UI copy. Gate 3 S1 fixes orientation as allowed before the
#: learner's prediction, so this must stay free of any model call and must not
#: depend on an investigation existing.
ORIENTATION_COPY: tuple[str, ...] = (
    "Read the customer's request and the exact output the service produced.",
    "Name the required tasks the request asked for and which of them went unanswered.",
    "Write the cause you believe explains the gap.",
    "Write a falsifier: an observation that would prove your cause wrong.",
    "Write one public test that distinguishes your cause from a working service.",
)

ASSIST_GATE_REASON = (
    "Diagnostic help needs your own cause, falsifier and public test first."
)

#: The outcome for an assist call a restart interrupted between its committed
#: reservation and its outcome write. The interruption is the controller's, not
#: the service's, so this stays distinct from the gateway's safe failure codes.
ASSIST_INTERRUPTED = "ASSIST_INTERRUPTED"


def orientation(shift_id: str) -> dict[str, Any]:
    """Deterministic orientation, available before any investigation exists."""
    return {"shift_id": shift_id, "steps": list(ORIENTATION_COPY), "source": "deterministic_copy"}


def append_investigation(
    conn: sqlite3.Connection, shift_id: str, request: InvestigationRequest
) -> Investigation:
    """Append the learner's diagnosis. A revision never overwrites its parent.

    The source run must belong to this shift and must actually have produced the
    named request ordinal, so an investigation cannot cite evidence this shift
    does not hold. ``authored_by`` is not caller-controlled: the model fixes it to
    the learner, and no assist or model output can author one.
    """
    shift = _require_open_shift(conn, shift_id)

    run = repo.get_run(conn, request.source_run_id)
    if run is None:
        raise LifecycleError("not_found", f"unknown source run: {request.source_run_id}")
    if run.shift_id != shift.id:
        raise LifecycleError(
            "conflict", "a source run must belong to the shift that investigates it"
        )

    ordinals = {output.request_ordinal for output in repo.list_outputs(conn, run.id)}
    if request.source_request_ordinal not in ordinals:
        raise LifecycleError(
            "conflict",
            f"run {run.id} produced no request ordinal {request.source_request_ordinal}",
        )

    for field in ("cause", "falsifier", "public_test"):
        if not getattr(request, field).strip():
            raise InvestigationIncomplete(f"{field} is required before an investigation exists")
        if len(getattr(request, field)) > 2000:
            raise InvestigationIncomplete(f"{field} exceeds 2000 characters")

    if request.revision_of_id is not None:
        parent = repo.get_investigation(conn, request.revision_of_id)
        if parent is None:
            raise LifecycleError(
                "not_found", f"unknown investigation to revise: {request.revision_of_id}"
            )
        if parent.shift_id != shift.id:
            raise LifecycleError(
                "conflict", "a revision must reference an investigation in the same shift"
            )

    investigation = Investigation(
        id=f"inv-{repo.count_investigations(conn) + 1:04d}",
        shift_id=shift.id,
        source_run_id=run.id,
        source_request_ordinal=request.source_request_ordinal,
        cause=request.cause.strip(),
        falsifier=request.falsifier.strip(),
        public_test=request.public_test.strip(),
        revision_of_id=request.revision_of_id,
        created_at=_now(),
    )
    repo.insert_investigation(conn, investigation)
    conn.commit()
    return investigation


def request_assist(
    conn: sqlite3.Connection, shift_id: str, investigation_id: str | None, role: AssistRole,
    *, message: str = "", client_request_id: str = "", gateway: AssistGateway | None = None,
) -> AssistEvent:
    """Reserve a bounded call after learner commitment, then record its outcome.

    A failed or interrupted provider call stays in the shared budget. The model
    receives public request wording and learner reasoning only; the controller
    never supplies assessment, protected cases or promotion capabilities.
    """
    shift = _require_open_shift(conn, shift_id)
    if investigation_id is None:
        raise InvestigationIncomplete(ASSIST_GATE_REASON)
    investigation = repo.get_investigation(conn, investigation_id)
    if investigation is None:
        raise LifecycleError("not_found", f"unknown investigation: {investigation_id}")
    if investigation.shift_id != shift.id:
        raise LifecycleError(
            "conflict", "diagnostic help must reference an investigation owned by this shift"
        )

    if gateway is None:
        raise AssistGatewayUnavailable(
            f"assist gateway is not configured for this session; {role.value} is unavailable"
        )
    if not client_request_id.strip() or len(client_request_id) > 200:
        raise LifecycleError("conflict", "a bounded client request ID is required")
    if len(message) > 2000:
        raise LifecycleError("conflict", "assist message exceeds 2000 characters")
    if any(len(getattr(investigation, field)) > 2000 for field in ("cause", "falsifier", "public_test")):
        raise LifecycleError("conflict", "investigation text exceeds the assist limit")
    output = next((row for row in repo.list_outputs(conn, investigation.source_run_id)
                   if row.request_ordinal == investigation.source_request_ordinal), None)
    if output is None:
        raise LifecycleError("conflict", "the investigation source request is unavailable")
    try:
        observed_response = output.body.decode("utf-8")
    except UnicodeDecodeError:
        observed_response = "Unavailable: the captured response was not UTF-8 text."
    if not observed_response:
        observed_response = "Unavailable: the captured response was empty."
    prompt = (
        f"Role: {role.value}\nPublic customer request: {output.request_text}\n"
        f"Observed service response: HTTP {output.http_status}; {observed_response}\n"
        f"Learner cause: {investigation.cause}\nLearner falsifier: {investigation.falsifier}\n"
        f"Learner public test: {investigation.public_test}\nLearner question: {message.strip()}"
    )
    if len(prompt.encode("utf-8")) + len(ASSIST_SYSTEM_MESSAGE.encode("utf-8")) > MAX_INPUT_BYTES:
        raise LifecycleError("conflict", "assist prompt exceeds the gateway input limit")
    try:
        assert_public_safe({"prompt": prompt}, _private_public_needles())
    except ValueError as exc:
        raise LifecycleError("conflict", "assist prompt contains private material") from exc

    conn.execute("BEGIN IMMEDIATE")
    try:
        replay = repo.get_assist_by_client_request_id(conn, client_request_id)
        if replay is not None:
            if (replay.shift_id, replay.investigation_id, replay.role, replay.request_text) != (
                shift.id, investigation.id, role, prompt
            ):
                raise LifecycleError("conflict", "client request ID belongs to another assist request")
            conn.rollback()
            return replay
        events = repo.list_assist_for_shift(conn, shift.id)
        northline = shift.engagement_slug != config.BOOKSHOP_SLUG
        limit = 1 if northline else config.BOOKSHOP_TOTAL_ASSIST_BUDGET
        if northline and role is not AssistRole.HINT:
            raise LifecycleError("conflict", "this engagement permits one hint only")
        if len(events) >= limit:
            raise LifecycleError("conflict", f"assist budget exhausted ({len(events)} of {limit} used)")
        if role is AssistRole.PATCH_PROPOSAL and any(
            event.role is AssistRole.PATCH_PROPOSAL for event in events
        ):
            raise LifecycleError("conflict", "one patch proposal maximum per shift")
        model_id = getattr(gateway, "model_id", config.ASSIST_MODEL)
        event = AssistEvent(
            id=f"assist-{shift.id}-{len(events) + 1}", shift_id=shift.id,
            investigation_id=investigation.id, role=role, model_id=model_id,
            request_text=prompt, response_text="", state="PENDING",
            client_request_id=client_request_id, created_at=_now(),
        )
        repo.insert_assist_event(conn, event)
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    started = time.monotonic()
    try:
        reply = gateway.generate(model_id=event.model_id, role=role, prompt=prompt)
        if not reply.text.strip() or len(reply.text.encode("utf-8")) > 8192:
            raise AssistRejected("ASSIST_OUTPUT_LIMIT")
        if reply.output_tokens is not None and not 0 <= reply.output_tokens <= 1024:
            raise AssistRejected("ASSIST_OUTPUT_LIMIT")
        try:
            assert_public_safe({"reply": reply.text, "reported_model_id": reply.reported_model_id},
                               _private_public_needles())
        except ValueError as exc:
            raise AssistRejected("ASSIST_PRIVATE_OUTPUT") from exc
        repo.finish_assist_event(conn, event.id, response=reply.text,
                                 proposed_patch=reply.text if role is AssistRole.PATCH_PROPOSAL else None,
                                 failure_code=None, reported_model_id=reply.reported_model_id,
                                 input_tokens=reply.input_tokens, output_tokens=reply.output_tokens,
                                 elapsed_ms=reply.elapsed_ms if reply.elapsed_ms is not None
                                 else round((time.monotonic() - started) * 1000))
    except AssistRejected as exc:
        repo.finish_assist_event(conn, event.id, response="", proposed_patch=None,
                                 failure_code=exc.code if exc.code in SAFE_FAILURE_CODES else "ASSIST_GATEWAY_FAILED",
                                 elapsed_ms=round((time.monotonic() - started) * 1000))
    except Exception:
        repo.finish_assist_event(conn, event.id, response="", proposed_patch=None,
                                 failure_code="ASSIST_GATEWAY_FAILED",
                                 elapsed_ms=round((time.monotonic() - started) * 1000))
    conn.commit()
    return repo.get_assist_event(conn, event.id)


def record_assist_decision(conn: sqlite3.Connection, event_id: str, accepted: bool) -> AssistEvent:
    event = repo.get_assist_event(conn, event_id)
    if event is None:
        raise LifecycleError("not_found", f"unknown assist event: {event_id}")
    if event.state != "COMPLETE":
        raise LifecycleError("conflict", "only completed help has an accept/reject decision")
    if not repo.decide_assist_event(conn, event_id, accepted):
        raise LifecycleError("conflict", "this assist event already has a decision")
    conn.commit()
    return repo.get_assist_event(conn, event_id)


def assist_event_view(event: AssistEvent) -> dict[str, Any]:
    view = {"id": event.id, "shift_id": event.shift_id,
            "investigation_id": event.investigation_id, "role": event.role.value,
            "model_id": event.model_id, "reported_model_id": event.reported_model_id,
            "input_tokens": event.input_tokens, "output_tokens": event.output_tokens,
            "elapsed_ms": event.elapsed_ms, "request_text": event.request_text,
            "response_text": event.response_text, "proposed_patch": event.proposed_patch,
            "accepted": event.accepted, "state": event.state,
            "failure_code": event.failure_code, "created_at": event.created_at.isoformat()}
    assert_public_projection(view)
    return view


def reserve_bootstrap_diagnostic(
    conn: sqlite3.Connection, shift_id: str, *, adapter: str = "local_process"
) -> None:
    """Validate the one public source diagnostic for a no-run v5 shift."""
    shift = _require_open_shift(conn, shift_id)
    if shift.opening_mode is not ShiftOpeningMode.LEGACY_FIRST_CHOICE:
        raise BootstrapBlocked("a null investigation is reserved only for a legacy first-choice shift")
    if adapter != TokenFactoryAdapter.name or not os.environ.get("NEBIUS_API_KEY") or not os.environ.get("NEBIUS_PROJECT_ID"):
        raise BootstrapBlocked("the verified isolated executor and its controller credentials are unavailable")
    if shift.engagement_slug != config.BOOKSHOP_SLUG:
        raise BootstrapBlocked("this engagement has no reviewed initial request and public state")
    if not all(path.is_file() for path in (
        config.PIVOT_MISSION, config.PIVOT_PUBLIC_STATE, config.PIVOT_INCIDENT_REQUESTS
    )):
        raise BootstrapBlocked("the reviewed initial request, mission or public state is missing")
    if repo.count_experiments_for_shift(conn, shift.id, ExperimentKind.DIAGNOSTIC):
        raise BootstrapBlocked("a bootstrap cannot be repeated after a diagnostic reservation")
    prior_runs = conn.execute(
        "SELECT r.id FROM runs r JOIN shifts s ON s.id = r.shift_id "
        "WHERE s.engagement_slug = ? AND s.seq < ?",
        (shift.engagement_slug, shift.seq),
    ).fetchall()
    if any(repo.list_outputs(conn, row["id"]) for row in prior_runs):
        raise BootstrapBlocked("an owned source request already exists in the inherited history")


def investigation_view(conn: sqlite3.Connection, shift_id: str, *, adapter: str = "local_process",
                       assist_gateway: AssistGateway | None = None) -> dict[str, Any]:
    """The public Investigate-station projection.

    Carries the learner's own entries with their revision linkage, the
    deterministic orientation copy, and the two denial states. It never carries a
    sealed identity, an internal path, a host path or assist content.
    """
    shift = _require_shift(conn, shift_id)
    entries = repo.list_investigations_for_shift(conn, shift.id)
    latest = entries[-1] if entries else None
    assist_events = repo.list_assist_for_shift(conn, shift.id)
    assist_limit = config.BOOKSHOP_TOTAL_ASSIST_BUDGET if shift.engagement_slug == config.BOOKSHOP_SLUG else 1
    assist_available = bool(latest and assist_gateway is not None and shift.state == "open"
                            and len(assist_events) < assist_limit)
    assist_reason = (
        "This shift is closed." if shift.state != "open" else
        ASSIST_GATE_REASON if latest is None else
        "Assist gateway is not configured." if assist_gateway is None else
        f"Assist budget exhausted ({len(assist_events)} of {assist_limit} used)."
        if len(assist_events) >= assist_limit else "Diagnostic help is available."
    )
    try:
        reserve_bootstrap_diagnostic(conn, shift_id, adapter=adapter)
        bootstrap_available = True
        bootstrap_reason = "One public source diagnostic is available for this no-run legacy shift."
    except (BootstrapBlocked, LifecycleError) as exc:
        bootstrap_available = False
        bootstrap_reason = str(exc)
    return {
        "shift_id": shift.id,
        "opening_mode": shift.opening_mode.value if shift.opening_mode else None,
        "orientation": orientation(shift.id),
        "investigations": [
            {
                "id": entry.id,
                "source_run_id": entry.source_run_id,
                "source_request_ordinal": entry.source_request_ordinal,
                "cause": entry.cause,
                "falsifier": entry.falsifier,
                "public_test": entry.public_test,
                "revision_of_id": entry.revision_of_id,
                "authored_by": entry.authored_by,
                "created_at": entry.created_at.isoformat(),
            }
            for entry in entries
        ],
        "latest_investigation_id": latest.id if latest else None,
        "assist_available": assist_available,
        "assist_reason": assist_reason,
        "assist_used": len(assist_events),
        "assist_limit": assist_limit,
        "assist_events": [assist_event_view(event) for event in assist_events],
        "bootstrap_available": bootstrap_available,
        "bootstrap_reason": bootstrap_reason,
    }


# ---------------------------------------------------------------------------
# Slice 11: the public diagnostic experiment
# ---------------------------------------------------------------------------

#: Program design section 7: two public diagnostic experiments per shift, each
#: reserved durably. A diagnostic whose run fails still consumed its slot.
DIAGNOSTIC_EXPERIMENTS_PER_SHIFT = 2
DIAGNOSTIC_DEADLINE_S = 5
DIAGNOSTIC_HARNESS_REF = "stdlib-loopback-v1"
DIAGNOSTIC_IMAGE_REF = "local-python-stdlib"
DIAGNOSTIC_EVALUATOR_VERSION = evaluator.RULE_VERSION
DIAGNOSTIC_REDUCER_VERSION = "no-reduction: a public diagnostic writes no ledger event"
DIAGNOSTIC_TREATMENT = (
    "Run the pinned reviewed starter once against the frozen incident request and "
    "public state; reserve no protected case and make no version eligible."
)


def _hash_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _private_public_needles() -> tuple[str, ...]:
    """Values that must not appear in serialized diagnostic projections."""
    needles = {str(Path.cwd()), sealed_store.private_storage_locator(), "sealed/cases"}
    for key in ("NEBIUS_API_KEY", "NEBIUS_PROJECT_ID"):
        value = os.environ.get(key)
        if value:
            needles.add(value)
    for family in config.BOOKSHOP_FAMILIES:
        for case in sealed_store.load_family(family).cases:
            needles.update((case.id, case.check_id))
            note = case.expected.get("note")
            if isinstance(note, str) and len(note) >= 25:
                needles.add(note)
    return tuple(needle for needle in needles if len(needle) >= 8)


def assert_public_projection(payload: object) -> None:
    try:
        assert_public_safe(payload, _private_public_needles())
    except ValueError as exc:
        raise LifecycleError("conflict", "public evidence contains private material") from exc


def artifact_source(conn: sqlite3.Connection, version_id: str) -> dict[str, Any]:
    version = repo.get_version(conn, version_id)
    if version is None:
        raise LifecycleError("not_found", f"unknown artifact version: {version_id}")
    payload = {
        "id": version.id, "parent_id": version.parent_id,
        "content_hash": version.content_hash, "files": version.files,
        "contract": version.contract.model_dump(mode="json"), "authorship": version.created_by,
    }
    assert_public_projection(payload)
    return payload


def _diagnostic_context_fields(
    shift: Shift,
    mission: task_contract.MissionSpec,
    mission_bytes: bytes,
    snapshot_bytes: bytes,
    specs_bytes: bytes,
    workload: FrozenWorkload,
    condition: ContextCondition,
    starting_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "engagement_slug": shift.engagement_slug,
        "workloads": [workload.model_dump(mode="json")],
        "mission_hash": _hash_bytes(mission_bytes),
        "public_data_hash": _hash_bytes(snapshot_bytes),
        "starting_business_state_hash": canonical.content_hash(starting_state),
        "requirement_set_id": f"public-rubric:{mission.engagement_slug}:v{mission.version}",
        "requirement_set_hash": _hash_bytes(mission_bytes),
        "visible_check_set_hash": _hash_bytes(specs_bytes),
        "condition": condition.model_dump(mode="json"),
        "evaluator_version": DIAGNOSTIC_EVALUATOR_VERSION,
        "reducer_version": DIAGNOSTIC_REDUCER_VERSION,
        "executor_class": EvidenceMode.TRUSTED_LOCAL.value,
        "harness_hash": _hash_bytes(DIAGNOSTIC_HARNESS_REF.encode("utf-8")),
        "image_ref": DIAGNOSTIC_IMAGE_REF,
        "service_model": None,
        "service_model_settings_json": {},
        "resource_limits_json": {"deadline_s": DIAGNOSTIC_DEADLINE_S, "max_requests": 4},
    }


def freeze_diagnostic_context(
    conn: sqlite3.Connection, shift: Shift, *, isolated: bool = False
) -> ExecutionContext:
    """Freeze the reviewed public material one diagnostic is assessed against.

    Every input the assessment reads is retained as its exact bytes plus a hash,
    so a later edit to a fixture cannot rewrite what this context measured. No
    protected reservation is created or referenced: a public diagnostic may only
    run material the learner can already read (Gate 3 S3.1, test 21).
    """
    if shift.engagement_slug != config.BOOKSHOP_SLUG:
        raise LifecycleError("conflict", "this engagement has no reviewed initial diagnostic workload")
    mission_bytes = config.PIVOT_MISSION.read_bytes()
    mission = task_contract.load_mission_bytes(mission_bytes, label=config.PIVOT_MISSION.name)
    if mission.engagement_slug != shift.engagement_slug:
        raise LifecycleError("conflict", "reviewed mission belongs to another engagement")
    snapshot_bytes = config.PIVOT_PUBLIC_STATE.read_bytes()
    snapshot = task_contract.load_public_state_bytes(
        snapshot_bytes, label=config.PIVOT_PUBLIC_STATE.name
    )
    if not snapshot.records:
        raise LifecycleError("conflict", "the reviewed public state carries no record")
    batch_bytes = config.PIVOT_INCIDENT_REQUESTS.read_bytes()
    specs_bytes = json.dumps(
        [spec.model_dump(mode="json") for spec in mission.request_specs],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    workload = FrozenWorkload(
        id="workload-01",
        ordinal=1,
        request_batch_bytes_base64=_encode(batch_bytes),
        # The executor addresses a request batch by the canonical content hash of its
        # base64 form, so the frozen hash is the value the adapter itself verifies.
        request_batch_hash=canonical.content_hash(_encode(batch_bytes)),
        request_specs_bytes_base64=_encode(specs_bytes),
        request_specs_hash=_hash_bytes(specs_bytes),
        request_count=len([line for line in batch_bytes.splitlines() if line.strip()]),
    )
    starting_state: dict[str, Any] = {
        "state": "not_applicable",
        "reason": "a public diagnostic writes no business state",
    }
    condition = ContextCondition(
        id="condition-normal",
        kind="normal",
        public_label="Normal public conditions",
        exact_bytes_base64=_encode(snapshot_bytes),
        content_hash=_hash_bytes(snapshot_bytes),
    )
    fields = _diagnostic_context_fields(
        shift, mission, mission_bytes, snapshot_bytes, specs_bytes, workload, condition, starting_state
    )
    if isolated:
        fields.update({
            "executor_class": EvidenceMode.ISOLATED_LIVE.value,
            "harness_hash": _hash_bytes(b"sandbox-driver-v1"),
            "image_ref": config.TOKEN_FACTORY_IMAGE,
            "service_model": config.SERVICE_MODEL,
            "service_model_settings_json": {
                "temperature": 0, "max_tokens": GATEWAY_MAX_OUTPUT_TOKENS,
            },
            "resource_limits_json": {"deadline_s": 45, "max_requests": 1,
                                     "max_layer_bytes": 16 * 1024 * 1024},
        })
    content_hash = canonical.content_hash(fields)
    existing = repo.get_execution_context_by_hash(conn, content_hash)
    if existing is not None:
        # Identical frozen material is one context identity, so the second
        # diagnostic over the same reviewed bytes references the stored context.
        return existing
    ordinal = repo.count_execution_contexts(conn) + 1
    context = ExecutionContext(
        id=f"context-{ordinal:04d}",
        schema_version=1,
        engagement_slug=shift.engagement_slug,
        workloads=(workload,),
        mission_bytes_base64=_encode(mission_bytes),
        mission_hash=fields["mission_hash"],
        public_data_bytes_base64=_encode(snapshot_bytes),
        public_data_hash=fields["public_data_hash"],
        starting_business_state_json=starting_state,
        starting_business_state_hash=fields["starting_business_state_hash"],
        requirement_set_id=fields["requirement_set_id"],
        requirement_set_hash=fields["requirement_set_hash"],
        visible_check_set_hash=fields["visible_check_set_hash"],
        protected_reservation_id=None,
        condition=condition,
        evaluator_version=fields["evaluator_version"],
        reducer_version=fields["reducer_version"],
        executor_class=EvidenceMode(fields["executor_class"]),
        harness_hash=fields["harness_hash"],
        image_ref=fields["image_ref"],
        service_model=fields["service_model"],
        service_model_settings_json=fields["service_model_settings_json"],
        resource_limits_json=fields["resource_limits_json"],
        created_at=_now(),
        content_hash=content_hash,
    )
    repo.insert_execution_context(conn, context)
    return context


def create_diagnostic_experiment(
    conn: sqlite3.Connection,
    shift_id: str,
    *,
    candidate_version_id: str,
    investigation_id: str | None,
    client_request_id: str,
    adapter: str = "local_process",
) -> Experiment:
    """Reserve one public diagnostic experiment and queue its single run.

    The controller chooses the workload, the executor and the treatment; the caller
    names only a candidate version and the investigation it belongs to. The
    trusted-local path stays pinned; the isolated path can execute the learner's
    frozen code. Neither path reserves a protected case or qualifies a version.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        shift = _require_open_shift(conn, shift_id)
        isolated = adapter == TokenFactoryAdapter.name
        if adapter not in (LocalProcessAdapter.name, TokenFactoryAdapter.name):
            raise LifecycleError("conflict", "no safe diagnostic executor is configured")
        if isolated and (not os.environ.get("NEBIUS_API_KEY") or not os.environ.get("NEBIUS_PROJECT_ID")):
            raise BootstrapBlocked("the verified isolated executor and its controller credentials are unavailable")
        if investigation_id is None:
            reserve_bootstrap_diagnostic(conn, shift_id, adapter=adapter)
            investigation = None
        else:
            investigation = repo.get_investigation(conn, investigation_id)
            if investigation is None:
                raise LifecycleError("not_found", f"unknown investigation: {investigation_id}")
        if investigation is not None and investigation.shift_id != shift.id:
            raise LifecycleError(
                "conflict", "a diagnostic must cite an investigation owned by this shift"
            )
        version = repo.get_version(conn, candidate_version_id)
        if version is None:
            raise LifecycleError("not_found", f"unknown artifact version: {candidate_version_id}")
        if version.shift_id != shift.id:
            raise LifecycleError("conflict", "a diagnostic candidate must belong to this shift")
        replay = repo.get_experiment_by_client_request_id(conn, client_request_id)
        if replay is not None:
            candidate = replay.candidates[0] if replay.candidates else None
            if (
                replay.shift_id == shift.id
                and replay.kind is ExperimentKind.DIAGNOSTIC
                and replay.investigation_id == (investigation.id if investigation else None)
                and candidate is not None
                and candidate.artifact_version_id == version.id
            ):
                conn.rollback()
                return replay
            raise LifecycleError(
                "conflict", "client_request_id was already used for a different experiment"
            )
        if not isolated and version.content_hash != config.TRUSTED_LOCAL_FIXTURES["pivot_starter"][0]:
            raise LifecycleError(
                "conflict",
                "only the pinned reviewed starter is executable as a public diagnostic candidate",
            )
        used = repo.count_experiments_for_shift(conn, shift_id, ExperimentKind.DIAGNOSTIC)
        if used >= DIAGNOSTIC_EXPERIMENTS_PER_SHIFT:
            raise LifecycleError(
                "conflict",
                f"diagnostic budget exhausted for this shift ({used} of "
                f"{DIAGNOSTIC_EXPERIMENTS_PER_SHIFT} used)",
            )
        context = freeze_diagnostic_context(conn, shift, isolated=isolated)
        ordinal = used + 1
        treatment = (
            "Run this frozen learner-owned service once in the isolated Sandbox "
            "against the reviewed initial public request and state; no protected "
            "case, eligibility or business consequence is reserved."
            if isolated else DIAGNOSTIC_TREATMENT
        )
        candidates = (
            CandidateRef(
                label="A",
                artifact_version_id=version.id,
                artifact_content_hash=version.content_hash,
            ),
        )
        experiment = Experiment(
            id=f"experiment-{shift.id}-d{ordinal}",
            shift_id=shift.id,
            kind=ExperimentKind.DIAGNOSTIC,
            investigation_id=investigation.id if investigation else None,
            candidates=candidates,
            declared_treatment=treatment,
            context_id=context.id,
            content_hash=canonical.content_hash(
                {
                    "shift_id": shift.id,
                    "kind": ExperimentKind.DIAGNOSTIC.value,
                    "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
                    "context_hash": context.content_hash,
                    "trial_count_per_candidate": 1,
                    "declared_treatment": treatment,
                }
            ),
            trial_count_per_candidate=1,
            state="PLANNED",
            client_request_id=client_request_id,
            created_at=_now(),
        )
        repo.insert_experiment(conn, experiment)
        run = Run(
            id=f"run-{repo.count_runs_all(conn) + 1:04d}",
            shift_id=shift.id,
            artifact_version_id=version.id,
            request_batch_ref=config.PIVOT_INCIDENT_REQUESTS.name,
            shop_snapshot_ref=f"frozen-context:{context.id}",
            attempt_number=repo.count_runs(conn, shift.id) + 1,
            state=RunState.QUEUED,
            adapter=adapter,
            started_at=_now(),
            purpose=RunPurpose.EXPERIMENT,
            evidence_mode=EvidenceMode.ISOLATED_LIVE if isolated else EvidenceMode.TRUSTED_LOCAL,
            context_id=context.id,
            experiment_id=experiment.id,
        )
        repo.insert_run(conn, run)
        repo.update_experiment_state(conn, experiment.id, "RUNNING")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return experiment


def execute_experiment(conn: sqlite3.Connection, run_id: str) -> Run:
    """Execute one reserved diagnostic and assess it against the frozen rubric.

    The frozen context is the only source of the mission, the public state and the
    workload hash, so the bytes that were reserved are the bytes that execute and
    the bytes the assessment reads. Assessment is the pure evaluator over the
    validated envelope: it opens no sealed case and writes no ledger event,
    incident, selection or business state.
    """
    run = repo.get_run(conn, run_id)
    if run is None:
        raise LifecycleError("not_found", f"unknown run: {run_id}")
    if run.purpose is not RunPurpose.EXPERIMENT:
        raise LifecycleError("conflict", "only an experiment run is executed by this path")
    if run.state is not RunState.QUEUED:
        return run
    context = repo.get_execution_context(conn, run.context_id) if run.context_id else None
    version = repo.get_version(conn, run.artifact_version_id)
    if context is None or version is None or not context.workloads:
        repo.update_run(conn, run_id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED, _now())
        repo.update_experiment_state(conn, run.experiment_id, "FAILED")
        conn.commit()
        return repo.get_run(conn, run_id)

    workload = context.workloads[0]
    try:
        snapshot_bytes = base64.b64decode(context.public_data_bytes_base64)
        mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))
        snapshot = task_contract.load_public_state_bytes(snapshot_bytes)
        request = executor.RunRequest(
            artifact_snapshot=executor.ArtifactSnapshotRef(
                files={path: text.encode("utf-8") for path, text in version.files.items()},
                manifest_hash=version.content_hash,
            ),
            request_batch=executor.BatchRef(
                path_ref=run.request_batch_ref,
                content_hash=workload.request_batch_hash,
            ),
            shop_snapshot_ref="",
            harness_ref="sandbox-driver-v1" if run.adapter == TokenFactoryAdapter.name else DIAGNOSTIC_HARNESS_REF,
            image_ref=context.image_ref if run.adapter == TokenFactoryAdapter.name else DIAGNOSTIC_IMAGE_REF,
            deadline_s=45 if run.adapter == TokenFactoryAdapter.name else DIAGNOSTIC_DEADLINE_S,
            inference_grant=None,
            request_batch_bytes=base64.b64decode(workload.request_batch_bytes_base64),
        )
    except (ValueError, ShiftworkDomainError):
        repo.update_run(conn, run_id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED, _now())
        repo.update_experiment_state(conn, run.experiment_id, "FAILED")
        conn.commit()
        return repo.get_run(conn, run_id)

    repo.update_run(conn, run_id, RunState.RUNNING)
    repo.set_run_snapshot_bytes(conn, run_id, snapshot_bytes)
    conn.commit()
    try:
        result = None
        with tempfile.TemporaryDirectory(prefix="shiftwork-diagnostic-") as directory:
            snapshot_path = Path(directory) / "public_state.json"
            snapshot_path.write_bytes(snapshot_bytes)
            request = request.model_copy(update={"shop_snapshot_ref": str(snapshot_path)})
            if run.adapter == TokenFactoryAdapter.name:
                adapter = TokenFactoryAdapter(
                    run_id=run.id,
                    allowed_tool_names=tuple(mission.allowed_tool_vocabulary),
                    token=os.environ.get("NEBIUS_API_KEY", ""),
                    project=os.environ.get("NEBIUS_PROJECT_ID", ""),
                    model=context.service_model or config.SERVICE_MODEL,
                )
            elif run.adapter == LocalProcessAdapter.name:
                adapter = LocalProcessAdapter()
            else:
                raise LifecycleError("conflict", "reserved diagnostic has no safe executor")
            result = asyncio.run(adapter.execute(request))

        for ordinal, observation in enumerate(result.observations, start=1):
            raw = json.dumps(observation.raw_payload, sort_keys=True, default=str).encode("utf-8")
            repo.insert_observation(conn, ExecutionObservation(
                id=f"{run.id}-obs-{ordinal}", run_id=run.id, request_ordinal=1,
                ordinal=ordinal, kind=ObservationKind(observation.kind),
                public_payload_json=observation.public_payload,
                raw_payload_ref="data:application/json;base64," + base64.b64encode(raw).decode("ascii"),
                measured_at=_now(),
            ))

        outputs = []
        if result.captures:
            batch = {entry.ordinal: entry for entry in executor.load_batch(request.request_batch)}
            for output in executor.normalize_captures(result.captures, request.deadline_s):
                output = output.model_copy(update={
                    "id": f"{run.id}-out-{output.request_ordinal}",
                    "run_id": run.id,
                    "request_text": batch[output.request_ordinal].text,
                })
                repo.insert_output(conn, output)
                outputs.append(output)

        # Preserve the raw capture and trusted observations before assessment.
        conn.commit()

        captured = {output.request_ordinal: output for output in outputs}
        completed = 0
        mandatory_pass = True
        for index, spec in enumerate(mission.request_specs, start=1):
            output = captured.get(index)
            response = None
            if output is not None and output.transport_error is None:
                try:
                    response = task_contract.validate_response_envelope(spec, output.body)
                except TaskEnvelopeInvalid:
                    # An envelope the contract refuses is missing execution evidence,
                    # never a refusal the service did not make (S3.3).
                    response = None
            request_assessments = evaluator.assess_request(
                spec=spec,
                request_ordinal=index,
                mission=mission,
                snapshot=snapshot,
                response=response,
            )
            for assessment in request_assessments:
                repo.insert_task_assessment(
                    conn,
                    assessment_id=f"{run.id}-a{index}-{assessment.task_id}",
                    run_id=run.id,
                    assessment=assessment,
                    assessed_at=_now(),
                )
            if any(assessment.mandatory_pass is False for assessment in request_assessments):
                mandatory_pass = False
            if evaluator.request_usefully_completed(spec, request_assessments):
                completed += 1
        repo.insert_run_assessment(
            conn,
            RunAssessment(
                run_id=run.id,
                context_hash=context.content_hash,
                complete_request_count=completed,
                expected_request_count=len(mission.request_specs),
                mandatory_pass=mandatory_pass,
                rule_version=DIAGNOSTIC_EVALUATOR_VERSION,
                assessed_at=_now(),
            ),
        )
        if result.failure is not None:
            repo.update_run(conn, run_id, RunState.FAILED, result.failure, _now())
            repo.update_experiment_state(conn, run.experiment_id, "FAILED")
        else:
            repo.update_run(conn, run_id, RunState.FINALIZED, None, _now())
            repo.update_experiment_state(conn, run.experiment_id, "FINALIZED")
        conn.commit()
    except Exception:
        conn.rollback()
        repo.update_run(conn, run_id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
        repo.update_experiment_state(conn, run.experiment_id, "FAILED")
        conn.commit()
        raise
    return repo.get_run(conn, run_id)


def execute_experiment_task(db_path: str, run_id: str) -> None:
    conn = db.connect(db_path)
    try:
        execute_experiment(conn, run_id)
    finally:
        conn.close()


def experiment_run(conn: sqlite3.Connection, experiment_id: str) -> Run | None:
    """The run a reserved experiment executes, or None before it was created."""
    experiment = repo.get_experiment(conn, experiment_id)
    if experiment is None:
        return None
    return next(
        (
            run
            for run in repo.list_runs_for_shift(conn, experiment.shift_id)
            if run.experiment_id == experiment.id
        ),
        None,
    )


def _diagnostic_customer_text(
    conn: sqlite3.Connection, context: ExecutionContext, run_id: str
) -> str | None:
    """The customer text for the run's first validated envelope, else None.

    Rendered from the validated envelope plus the frozen mission and public state
    alone, so no prose the service tried to carry can reach a customer surface
    (Gate 3 S3.3).
    """
    outputs = repo.list_outputs(conn, run_id)
    if not outputs:
        return None
    output = outputs[0]
    if output.transport_error is not None:
        return None
    try:
        mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))
        snapshot = task_contract.load_public_state_bytes(
            base64.b64decode(context.public_data_bytes_base64)
        )
        if not 1 <= output.request_ordinal <= len(mission.request_specs):
            return None
        spec = mission.request_specs[output.request_ordinal - 1]
        response = task_contract.validate_response_envelope(spec, output.body)
    except (ShiftworkDomainError, ValueError):
        return None
    return customer_answer.render_task_customer_text(
        spec=spec, mission=mission, snapshot=snapshot, response=response
    )


def experiment_view(conn: sqlite3.Connection, experiment_id: str) -> dict[str, Any]:
    """The public experiment projection.

    It carries the frozen workload identity, the candidate, the trial's public
    assessments and the exact output the learner's own service produced. Raw
    observation payload refs, sealed identities, host paths and the protected
    reservation never appear, and eligibility stays false: a public diagnostic
    cannot qualify a version (Gate 3 S3.7, test 21).
    """
    experiment = repo.get_experiment(conn, experiment_id)
    if experiment is None:
        raise LifecycleError("not_found", f"unknown experiment: {experiment_id}")
    context = repo.get_execution_context(conn, experiment.context_id)
    if context is None:
        raise LifecycleError("not_found", f"unknown context: {experiment.context_id}")
    workload = context.workloads[0]
    run = experiment_run(conn, experiment.id)
    assessments: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    customer_text = None
    missing_evidence: list[str] = []
    if run is not None:
        assessments = [
            {
                "request_id": assessment.request_id,
                "request_ordinal": assessment.request_ordinal,
                "task_id": assessment.task_id,
                "outcome": assessment.outcome.value,
                "mandatory_pass": assessment.mandatory_pass,
                "reason_codes": [code.value for code in assessment.reason_codes],
            }
            for assessment in repo.list_task_assessment_models(conn, run.id)
        ]
        outputs = [
            {
                "request_ordinal": output.request_ordinal,
                "request_text": output.request_text,
                "http_status": output.http_status,
                "body_base64": _encode(output.body),
                "elapsed_ms": output.elapsed_ms,
                "transport_error": output.transport_error.value if output.transport_error else None,
            }
            for output in repo.list_outputs(conn, run.id)
        ]
        observations = [
            {"kind": observation.kind.value, "public_payload_json": observation.public_payload_json}
            for observation in repo.list_observations(conn, run.id)
        ]
        customer_text = _diagnostic_customer_text(conn, context, run.id)
        if run.failure_kind is not None:
            missing_evidence.append(f"execution failure: {run.failure_kind.value}")
        if not outputs:
            missing_evidence.append("no capture was produced for the frozen request")
    else:
        missing_evidence.append("the reserved diagnostic run has not been executed")
    trial_state = {
        RunState.QUEUED: "RESERVED",
        RunState.RUNNING: "RUNNING",
        RunState.CAPTURED: "RUNNING",
        RunState.FINALIZED: "COMPLETE",
        RunState.FAILED: "FAILED",
    }[run.state] if run is not None else "RESERVED"
    payload = {
        "id": experiment.id,
        "shift_id": experiment.shift_id,
        "kind": experiment.kind.value,
        "investigation_id": experiment.investigation_id,
        "declared_treatment": experiment.declared_treatment,
        "context_hash": context.content_hash,
        "context_evidence_class": context.executor_class.value,
        "workloads": [
            {
                "id": workload.id,
                "ordinal": workload.ordinal,
                "request_batch_hash": workload.request_batch_hash,
                "request_count": workload.request_count,
            }
        ],
        "candidates": [
            {
                "label": candidate.label,
                "artifact_version_id": candidate.artifact_version_id,
                "artifact_content_hash": candidate.artifact_content_hash,
            }
            for candidate in experiment.candidates
        ],
        "trials": [
            {
                "pair_ordinal": 1,
                "candidate_label": experiment.candidates[0].label,
                "workload_id": workload.id,
                "request_batch_hash": workload.request_batch_hash,
                "request_count": workload.request_count,
                "run_id": run.id if run is not None else None,
                "state": trial_state,
                "evidence_mode": run.evidence_mode.value if run and run.evidence_mode else None,
                "task_assessments": assessments,
                "observations": observations,
                "outputs": outputs,
                "customer_text": customer_text,
                "missing_evidence": missing_evidence,
                "metrics": None,
            }
        ],
        "eligible": False,
        "eligibility_reason": (
            "A public diagnostic reserves no protected case and compares no "
            "candidates, so it can never qualify a version."
        ),
        "state": experiment.state,
    }
    try:
        assert_public_safe(payload, _private_public_needles())
    except ValueError as exc:
        raise LifecycleError("conflict", "public diagnostic evidence contains private material") from exc
    return payload


def investigate_station(
    conn: sqlite3.Connection, shift_id: str, *, adapter: str = "local_process",
    assist_gateway: AssistGateway | None = None,
) -> dict[str, Any]:
    """The Investigate station: the learner's entries, the denials and the latest
    public diagnostic, composed from the two narrower projections.

    Deterministic orientation is available before any investigation exists (Gate 3
    S1), and the station shows attributable assist events when a gateway is configured.
    """
    view = investigation_view(conn, shift_id, adapter=adapter, assist_gateway=assist_gateway)
    experiments = repo.list_experiments_for_shift(conn, shift_id)
    view["latest_experiment"] = (
        experiment_view(conn, experiments[-1].id) if experiments else None
    )
    try:
        assert_public_safe(view, _private_public_needles())
    except ValueError as exc:
        raise LifecycleError("conflict", "public investigation evidence contains private material") from exc
    return view


def investigation_entry(conn: sqlite3.Connection, investigation_id: str) -> Investigation:
    investigation = repo.get_investigation(conn, investigation_id)
    if investigation is None:
        raise LifecycleError("not_found", f"unknown investigation: {investigation_id}")
    return investigation
