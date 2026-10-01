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
import itertools
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
from shiftwork.domain import canonical, comparison, contract_catalog, customer_answer, task_contract
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
    ExposureItem,
    ExposureReservation,
    FrozenWorkload,
    Incident,
    IncidentState,
    Investigation,
    InvestigationRequest,
    JsonValue,
    LedgerEventDraft,
    LedgerEventType,
    OperatingSelection,
    SelectionRequest,
    RotationDraw,
    Run,
    RunAssessment,
    RunOutput,
    RunPurpose,
    RunState,
    ReasonCode,
    ObservationKind,
    OperationalAssessment,
    ReplayReport,
    ServiceResponse,
    Shift,
    ShiftOpeningMode,
    TrialSlot,
)
from shiftwork.evaluator import evaluator
from shiftwork.executor import base as executor
from shiftwork.executor.local_process import LocalProcessAdapter
from shiftwork.executor.recorded import RecordedAdapter
from shiftwork.executor.tokenfactory import TokenFactoryAdapter
from shiftwork.gateway.protocol import GATEWAY_MAX_OUTPUT_TOKENS
from shiftwork.gateway.redaction import assert_public_safe
from shiftwork.live_budget import LiveComparisonBudget, LiveOperationBudget
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


def append_selection(
    conn: sqlite3.Connection, shift_id: str, request: SelectionRequest
) -> OperatingSelection:
    """Append an exact learner choice after atomic stored-evidence revalidation."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        shift = _require_shift(conn, shift_id)
        rationale = request.rationale.strip()
        if not rationale or not request.client_request_id.strip():
            raise LifecycleError("conflict", "selection needs a rationale and request key")
        replay = repo.get_selection_by_client_request_id(conn, request.client_request_id)
        if replay is not None:
            if (replay.shift_id == shift.id
                    and replay.comparison_id == request.comparison_id
                    and replay.selected_version_id == request.selected_version_id
                    and replay.rationale == rationale
                    and replay.prior_selection_id == request.expected_prior_selection_id):
                conn.rollback()
                return replay
            raise LifecycleError("conflict", "client_request_id was already used for another selection")
        shift = _require_open_shift(conn, shift_id)
        prior = repo.get_latest_operating_selection(conn, shift.engagement_slug)
        if request.expected_prior_selection_id != (prior.id if prior else None):
            raise LifecycleError("conflict", "expected prior selection is stale")
        if any(run.purpose is RunPurpose.OPERATION
               and run.state not in (RunState.FINALIZED, RunState.FAILED)
               for run in repo.list_runs_for_shift(conn, shift.id)):
            raise LifecycleError("conflict", "operation in flight; selection refused")
        experiment = repo.get_experiment(conn, request.comparison_id)
        if experiment is None:
            raise LifecycleError("conflict", "qualifying comparison is missing")
        if (experiment.shift_id != shift.id
                or experiment.kind is not ExperimentKind.QUALIFYING_COMPARISON
                or experiment.state != "FINALIZED"):
            raise LifecycleError("conflict", "a completed owned comparison is required")
        context = repo.get_execution_context(conn, experiment.context_id)
        if context is None or context.engagement_slug != shift.engagement_slug:
            raise LifecycleError("conflict", "frozen comparison context is unavailable")
        slots = repo.list_trial_slots(conn, experiment.id)
        outcome = _comparison_outcome(conn, experiment, context, slots)
        if outcome.status != "COMPLETE":
            raise LifecycleError("conflict", "comparison is incomplete or no longer comparable")
        candidate = next(
            (item for item in experiment.candidates
             if item.artifact_version_id == request.selected_version_id), None
        )
        if candidate is None:
            raise LifecycleError("conflict", "selected version was not in this comparison")
        eligibility = next(
            (item for item in outcome.eligibility
             if item.candidate_label == candidate.label
             and item.candidate_version_id == candidate.artifact_version_id), None
        )
        if eligibility is None or not eligibility.eligible:
            raise LifecycleError("conflict", "selected exact version is not eligible")
        version = repo.get_version(conn, candidate.artifact_version_id)
        if (version is None or version.shift_id != shift.id
                or version.content_hash != candidate.artifact_content_hash):
            raise LifecycleError("conflict", "selected version changed after the comparison")
        if shift.engagement_slug != config.BOOKSHOP_SLUG:
            raise LifecycleError("conflict", "current requirements are unavailable for this engagement")
        if _hash_bytes(config.PIVOT_MISSION.read_bytes()) != context.requirement_set_hash:
            raise LifecycleError("conflict", "requirements changed after the comparison")
        alternative = next(
            (item for item in experiment.candidates if item.label != candidate.label), None
        )
        if alternative is None:
            raise LifecycleError("conflict", "comparison has no retained alternative")
        selection = OperatingSelection(
            id=f"sel-{repo.count_operating_selections(conn) + 1:04d}",
            engagement_slug=shift.engagement_slug, shift_id=shift.id,
            kind="LEARNER_CHOICE",
            selected_version_id=version.id,
            selected_content_hash=version.content_hash,
            comparison_id=experiment.id,
            retained_alternative_version_id=alternative.artifact_version_id,
            rationale=rationale,
            requirement_set_hash=context.requirement_set_hash,
            prior_selection_id=prior.id if prior else None,
            state="VALID", client_request_id=request.client_request_id,
            created_at=_now(),
        )
        assert_public_projection({
            "rationale": selection.rationale,
            "selected_version_id": selection.selected_version_id,
            "selected_content_hash": selection.selected_content_hash,
            "comparison_id": selection.comparison_id,
            "retained_alternative_version_id": selection.retained_alternative_version_id,
        }, conn)
        repo.insert_operating_selection(conn, selection)
        conn.commit()
        return selection
    except Exception:
        conn.rollback()
        raise


def selection_history(conn: sqlite3.Connection, slug: str) -> list[OperatingSelection]:
    if repo.get_engagement(conn, slug) is None:
        raise LifecycleError("not_found", f"unknown engagement: {slug}")
    return repo.list_operating_selections(conn, slug)


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

    Ancestry comes from the draft's base, never from the newest stored version:
    a draft inherited from the selected version, or explicitly restored from one,
    records that base as ``parent_id`` and ``restored_from_id`` (Gate 3 S3.6), so
    saving or freezing a new candidate cannot substitute itself as an ancestor.
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
    base_version_id = repo.get_draft_base_version_id(conn, shift_id)
    if base_version_id is not None:
        base = repo.get_version(conn, base_version_id)
        if base is None:
            raise LifecycleError("conflict", "the draft base version is missing")
    else:
        base = repo.get_latest_version(conn, shift_id) or repo.get_latest_version_for_engagement(
            conn, shift.engagement_slug
        )
    version = ArtifactVersion(
        id=f"ver-{ordinal:04d}",
        shift_id=shift_id,
        parent_id=base.id if base else None,
        restored_from_id=base_version_id,
        content_hash=content_hash,
        storage_ref=f"inline:{content_hash}",
        files=dict(files),
        contract=contract,
        contract_catalog_hash=catalog.content_hash,
        created_by="learner",
        created_at=_now(),
    )
    repo.insert_version(conn, version)
    # The draft now holds exactly this version, so it becomes the base a later
    # freeze descends from; a subsequent restore points the base somewhere else.
    repo.set_draft_base_version(conn, shift_id, version.id)
    conn.commit()
    return version


def restore_version_to_draft(
    conn: sqlite3.Connection, shift_id: str, version_id: str
) -> dict[str, Any]:
    """Replace the draft with one stored version and record it as the new base.

    Restoring A after saving B makes the next freeze descend from A, not from the
    newest stored version (Gate 3 S3.6). The version must belong to this
    engagement, and its stored bytes are re-verified on read, so a restore cannot
    seed the draft from a tampered or foreign version.
    """
    shift = _require_open_shift(conn, shift_id)
    version = repo.get_version(conn, version_id)
    if version is None:
        raise LifecycleError("not_found", f"unknown artifact version: {version_id}")
    owner = repo.get_shift(conn, version.shift_id)
    if owner is None or owner.engagement_slug != shift.engagement_slug:
        raise LifecycleError("conflict", "a restored version must belong to this engagement")
    updated_at = _now()
    repo.upsert_draft(conn, shift_id, dict(version.files), updated_at, version.id)
    repo.set_draft_base_version(conn, shift_id, version.id)
    conn.commit()
    return {
        "shift_id": shift_id,
        "files": dict(version.files),
        "updated_at": updated_at,
        "restored_from_version_id": version.id,
    }


def start_run(
    conn: sqlite3.Connection,
    shift_id: str,
    *,
    executor: str | None = None,
    shop_snapshot: str | Path | None = None,
    client_request_id: str | None = None,
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
    candidate leaves the operating pointer unchanged. The controller's executor
    choice carries into a selected-operation reservation: only the isolated
    executor freezes an isolated context, and every other configured executor
    keeps the shipped trusted-local reservation.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        shift = _require_open_shift(conn, shift_id)
        selection, version = _selected_operating_version(conn, shift)
        adapter = executor or config.EXECUTOR_ADAPTER
        if selection.kind == "LEARNER_CHOICE" and selection.comparison_id is not None:
            run = _reserve_selected_operation(
                conn, shift, selection, version, client_request_id,
                adapter=(TokenFactoryAdapter.name if adapter == TokenFactoryAdapter.name
                         else LocalProcessAdapter.name),
            )
            conn.commit()
            return run
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


def _reserve_selected_operation(
    conn: sqlite3.Connection, shift: Shift, selection: OperatingSelection,
    version: ArtifactVersion, client_request_id: str | None,
    adapter: str = LocalProcessAdapter.name,
) -> Run:
    """Reserve an exact choice and frozen current conditions in the caller's transaction.

    ``adapter`` is the controller's configured executor, never a learner input:
    the isolated adapter freezes an isolated context and fails closed without
    controller credentials, every other configured executor keeps the shipped
    trusted-local reservation.
    """
    isolated = adapter == TokenFactoryAdapter.name
    if adapter not in (LocalProcessAdapter.name, TokenFactoryAdapter.name):
        raise LifecycleError("conflict", "no safe operation executor is configured")
    if isolated and (not os.environ.get("NEBIUS_API_KEY") or not os.environ.get("NEBIUS_PROJECT_ID")):
        raise BootstrapBlocked(
            "the verified isolated executor and its controller credentials are unavailable"
        )
    if not client_request_id or not client_request_id.strip():
        raise LifecycleError("conflict", "selected operation needs a request key")
    replay = conn.execute(
        "SELECT id FROM runs WHERE client_request_id = ?", (client_request_id,)
    ).fetchone()
    if replay is not None:
        prior = repo.get_run(conn, replay["id"])
        if prior.shift_id == shift.id and prior.selection_id == selection.id:
            return prior
        raise LifecycleError("conflict", "operation request key was already used")
    if selection.comparison_id is not None:
        reservation = repo.get_exposure_reservation_for_experiment(conn, selection.comparison_id)
        if reservation is None or reservation.state != "ACTIVE":
            raise LifecycleError("conflict", "selected comparison exposure was invalidated")
    if shift.engagement_slug != config.BOOKSHOP_SLUG:
        raise LifecycleError("conflict", "operational mission is unavailable for this engagement")
    mission_bytes = config.PIVOT_MISSION.read_bytes()
    if _hash_bytes(mission_bytes) != selection.requirement_set_hash:
        raise LifecycleError("conflict", "selected requirements changed before operation")
    prior_operations = [run for run in repo.list_runs_for_shift(conn, shift.id)
                        if run.purpose is not RunPurpose.EXPERIMENT]
    if any(run.state is RunState.FINALIZED for run in prior_operations):
        raise LifecycleError("conflict", "one successful operation is already finalized this shift")
    if any(run.state not in (RunState.FINALIZED, RunState.FAILED) for run in prior_operations):
        raise LifecycleError("conflict", "operation already in flight")
    if len(prior_operations) >= 2:
        raise LifecycleError("conflict", "two operational reservations already spent")
    if prior_operations:
        previous = prior_operations[0]
        if (repo.list_outputs(conn, previous.id)
                or any(previous.id in event.cause_refs for event in
                       repo.list_ledger_events(conn, shift.engagement_slug))):
            raise LifecycleError("conflict", "retry requires zero captured outputs and no business write")
        if previous.selection_id != selection.id or previous.context_id is None:
            raise LifecycleError("conflict", "retry selection or context changed")
    context = freeze_diagnostic_context(conn, shift, operation=True, isolated=isolated)
    if context.mission_hash != selection.requirement_set_hash:
        raise LifecycleError("conflict", "selected requirements changed before operation")
    if prior_operations and prior_operations[0].context_id != context.id:
        raise LifecycleError("conflict", "retry conditions changed")
    ordinal = repo.count_runs_all(conn) + 1
    run = Run(
        id=f"run-{ordinal:04d}", shift_id=shift.id, artifact_version_id=version.id,
        request_batch_ref=f"frozen-workload:{context.workloads[0].id}",
        shop_snapshot_ref="pivot:frozen",
        attempt_number=repo.count_runs(conn, shift.id) + 1, state=RunState.QUEUED,
        adapter=adapter, started_at=_now(), purpose=RunPurpose.OPERATION,
        evidence_mode=EvidenceMode.ISOLATED_LIVE if isolated else EvidenceMode.TRUSTED_LOCAL,
        selection_id=selection.id,
        context_id=context.id,
    )
    repo.insert_run(conn, run)
    conn.execute("UPDATE runs SET client_request_id = ? WHERE id = ?", (client_request_id, run.id))
    repo.insert_exposure_reservation(conn, ExposureReservation(
        id=f"exposure-operation-{run.id}", engagement_slug=shift.engagement_slug,
        scope="operation", experiment_id=None, state="ACTIVE", created_at=_now(),
    ))
    return run


def execute_run(conn: sqlite3.Connection, run_id: str,
                live_budget: LiveOperationBudget | None = None) -> Run:
    """Execute a queued run against the snapshot bytes it captures here.

    The controller reads the configured snapshot once, persists those exact bytes
    on the run and provisions the adapter from a controller-owned copy, so
    transcript selection, execution, scoring and the client's later comparison all
    resolve the same bytes even if the source path is edited or removed (Slice 9).
    """
    run = repo.get_run(conn, run_id)
    if run is None:
        raise LifecycleError("not_found", f"unknown run: {run_id}")
    if run.context_id is not None and run.purpose is RunPurpose.OPERATION:
        return execute_selected_operation(conn, run_id, live_budget)
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


def execute_selected_operation(conn: sqlite3.Connection, run_id: str,
                               live_budget: LiveOperationBudget | None = None) -> Run:
    """Run only the frozen public workload, retaining captures before consequences.

    The run row names the executor. The isolated executor gets the run-bound
    gateway and needs the controller's bounded operation ceiling; every other
    executor keeps the shipped trusted-local path.
    """
    run = get_run(conn, run_id)
    if run.purpose is not RunPurpose.OPERATION or run.context_id is None:
        raise LifecycleError("conflict", "selected operation required")
    if run.state is not RunState.QUEUED:
        return run
    context = repo.get_execution_context(conn, run.context_id)
    version = repo.get_version(conn, run.artifact_version_id)
    if context is None or version is None or len(context.workloads) != 1:
        repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED, _now())
        conn.commit()
        return repo.get_run(conn, run.id)
    workload = context.workloads[0]
    try:
        mission_bytes = base64.b64decode(context.mission_bytes_base64, validate=True)
        state_bytes = base64.b64decode(context.public_data_bytes_base64, validate=True)
        batch_bytes = base64.b64decode(workload.request_batch_bytes_base64, validate=True)
        mission = task_contract.load_mission_bytes(mission_bytes)
        task_contract.load_public_state_bytes(state_bytes)
        if (_hash_bytes(mission_bytes) != context.mission_hash
                or _hash_bytes(state_bytes) != context.public_data_hash
                or canonical.content_hash(_encode(batch_bytes)) != workload.request_batch_hash
                or run.selection_id is None):
            raise ValueError("frozen operation context digest mismatch")
        request = _comparison_run_request(run, context, workload, version)
    except (ValueError, ShiftworkDomainError):
        repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED, _now())
        conn.commit()
        return repo.get_run(conn, run.id)
    if run.adapter == TokenFactoryAdapter.name:
        # The live operation refuses to run without its own bounded ceiling: the
        # comparison meter is a different frozen shape and never covers a spawn.
        try:
            if not isinstance(live_budget, LiveOperationBudget):
                raise ValueError("a live selected operation requires its own operation budget")
            live_budget.preflight(model=context.service_model or config.SERVICE_MODEL,
                                  requests=workload.request_count)
        except ValueError:
            repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED, _now())
            conn.commit()
            return repo.get_run(conn, run.id)
    repo.update_run(conn, run.id, RunState.RUNNING)
    repo.set_run_snapshot_bytes(conn, run.id, state_bytes)
    conn.commit()
    try:
        with tempfile.TemporaryDirectory(prefix="shiftwork-operation-") as directory:
            state_path = Path(directory) / "public_state.json"
            state_path.write_bytes(state_bytes)
            request = request.model_copy(update={"shop_snapshot_ref": str(state_path)})
            if run.adapter == TokenFactoryAdapter.name:
                adapter = TokenFactoryAdapter(
                    run_id=run.id,
                    allowed_tool_names=tuple(mission.allowed_tool_vocabulary),
                    token=os.environ.get("NEBIUS_API_KEY", ""),
                    project=os.environ.get("NEBIUS_PROJECT_ID", ""),
                    model=context.service_model or config.SERVICE_MODEL,
                    live_budget=live_budget,
                )
            elif run.adapter == LocalProcessAdapter.name:
                adapter = LocalProcessAdapter()
            else:
                raise LifecycleError("conflict", "selected operation has no safe executor")
            result = asyncio.run(adapter.execute(request))
        for ordinal, observation in enumerate(result.observations, start=1):
            raw = json.dumps(observation.raw_payload, sort_keys=True, default=str).encode("utf-8")
            repo.insert_observation(conn, ExecutionObservation(
                id=f"{run.id}-obs-{ordinal}", run_id=run.id,
                request_ordinal=observation.public_payload.get("request_ordinal", 1),
                ordinal=ordinal, kind=ObservationKind(observation.kind),
                public_payload_json=observation.public_payload,
                raw_payload_ref="data:application/json;base64," + _encode(raw), measured_at=_now(),
            ))
        batch = {item.ordinal: item for item in executor.load_batch(request.request_batch, batch_bytes)}
        for capture in executor.normalize_captures(result.captures, request.deadline_s):
            repo.insert_output(conn, capture.model_copy(update={
                "id": f"{run.id}-out-{capture.request_ordinal}", "run_id": run.id,
                "request_text": batch[capture.request_ordinal].text,
            }))
        # This boundary keeps raw evidence even when assessment or reduction fails.
        conn.commit()
        if result.failure is not None:
            repo.update_run(conn, run.id, RunState.FAILED, result.failure, _now())
            conn.commit()
        elif (len(repo.list_outputs(conn, run.id)) != workload.request_count
              or any(item.transport_error is not None or not item.body
                     for item in repo.list_outputs(conn, run.id))):
            repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.CAPTURE_TRUNCATED, _now())
            conn.commit()
        else:
            repo.update_run(conn, run.id, RunState.CAPTURED)
            conn.commit()
            finalize_selected_operation(conn, run.id)
    except Exception:
        conn.rollback()
        if repo.get_run(conn, run.id).state not in (RunState.FINALIZED, RunState.FAILED):
            repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
            conn.commit()
        raise
    return repo.get_run(conn, run.id)


def finalize_selected_operation(conn: sqlite3.Connection, run_id: str) -> Run:
    """Commit checks, synthetic events, incidents and terminal state together."""
    run = get_run(conn, run_id)
    if run.state is RunState.FINALIZED:
        return run
    if run.purpose is not RunPurpose.OPERATION or run.context_id is None:
        raise LifecycleError("conflict", "selected operation required for business finalization")
    conn.execute("BEGIN IMMEDIATE")
    try:
        run = get_run(conn, run_id)
        if run.state is not RunState.CAPTURED:
            raise LifecycleError("conflict", "operation has no completed capture")
        shift = _require_shift(conn, run.shift_id)
        selection, version = _selected_operating_version(conn, shift)
        context = repo.get_execution_context(conn, run.context_id)
        if (selection.id != run.selection_id or version.id != run.artifact_version_id
                or context is None or context.engagement_slug != shift.engagement_slug
                or len(context.workloads) != 1):
            raise LifecycleError("conflict", "selected operation binding changed")
        if selection.comparison_id:
            exposure = repo.get_exposure_reservation_for_experiment(conn, selection.comparison_id)
            if exposure is None or exposure.state != "ACTIVE":
                raise LifecycleError("conflict", "selected comparison exposure was invalidated")
        operation_exposure = repo.get_exposure_reservation(conn, f"exposure-operation-{run.id}")
        if operation_exposure is None or operation_exposure.state != "ACTIVE":
            raise LifecycleError("conflict", "operational exposure was invalidated")
        mission_bytes = base64.b64decode(context.mission_bytes_base64, validate=True)
        state_bytes = base64.b64decode(context.public_data_bytes_base64, validate=True)
        if (_hash_bytes(mission_bytes) != context.mission_hash
                or _hash_bytes(state_bytes) != context.public_data_hash
                or repo.get_run_snapshot_bytes(conn, run.id) != state_bytes):
            raise LifecycleError("conflict", "captured operational mission or state differs")
        mission = task_contract.load_mission_bytes(mission_bytes)
        snapshot = task_contract.load_public_state_bytes(state_bytes)
        outputs = repo.list_outputs(conn, run.id)
        workload = context.workloads[0]
        if (len(outputs) != workload.request_count
                or {item.request_ordinal for item in outputs}
                != set(range(1, workload.request_count + 1))
                or any(item.transport_error is not None or not item.body for item in outputs)):
            raise LifecycleError("conflict", "operational capture is incomplete")
        captured = {item.request_ordinal: item for item in outputs}
        assessed = []
        completed = 0
        mandatory_pass = True
        for index, spec in enumerate(mission.request_specs, start=1):
            output = captured[index]
            try:
                response = task_contract.validate_response_envelope(spec, output.body)
            except TaskEnvelopeInvalid:
                response = None
            rows = evaluator.assess_request(spec=spec, request_ordinal=index,
                                            mission=mission, snapshot=snapshot, response=response)
            assessed.extend(rows)
            completed += int(evaluator.request_usefully_completed(spec, rows))
            mandatory_pass &= all(row.mandatory_pass for row in rows)
        assessment = OperationalAssessment(
            run_id=run.id, context_hash=context.content_hash,
            complete_request_count=completed, expected_request_count=len(mission.request_specs),
            mandatory_pass=mandatory_pass, rule_version=context.reducer_version,
            assessed_at=_now(), selection_id=selection.id,
        )
        checks: dict[str, CheckResult] = {}
        for row in assessed:
            check_id = f"task:{row.request_id}:{row.task_id}"
            check = CheckResult(
                id=f"cr-{repo.count_check_results(conn) + 1:04d}", run_id=run.id,
                check_id=check_id, verdict="pass" if row.mandatory_pass else "fail",
                observed_ref=captured[row.request_ordinal].id,
                reason_code=(row.reason_codes[0] if row.reason_codes else
                             (None if row.mandatory_pass else ReasonCode.REQUIRED_TASK_MISSING)),
            )
            repo.insert_check_result(conn, check)
            repo.insert_task_assessment(conn, assessment_id=f"{run.id}-a{row.request_ordinal}-{row.task_id}",
                                        run_id=run.id, assessment=row, assessed_at=_now())
            checks[check_id] = check
        repo.insert_run_assessment(conn, assessment)
        drafts = reducer.reduce_operation(run, assessment, mission, tuple(assessed), tuple(checks.values()))
        resolving = []
        for incident in repo.list_incidents(conn, shift.engagement_slug):
            if incident.state is IncidentState.RESOLVED:
                continue
            opened = repo.get_run(conn, incident.opening_run_id)
            old_check = next((row for row in repo.list_check_results(conn, incident.opening_run_id)
                              if row.id == incident.check_result_id), None)
            regression = checks.get(old_check.check_id) if old_check else None
            opened_context = (repo.get_execution_context(conn, opened.context_id)
                              if opened is not None and opened.context_id is not None else None)
            if (opened is None or opened.artifact_version_id == version.id
                    or opened_context is None
                    or opened_context.mission_hash != context.mission_hash
                    or opened_context.evaluator_version != context.evaluator_version
                    or regression is None or regression.verdict != "pass"):
                continue
            resolving.append((incident.id, LedgerEventDraft(
                event_type=LedgerEventType.INCIDENT_RESOLVED,
                cause_refs=(run.id, regression.id, incident.id),
                payload={"incident_id": incident.id, "resolving_version_id": version.id,
                         "rule_version": assessment.rule_version},
            )))
        existing = repo.list_ledger_events(conn, shift.engagement_slug)
        events = chain.append(drafts + [item[1] for item in resolving],
                              prev_hash=chain.next_prev_hash(existing), start_seq=chain.next_seq(existing))
        for event in events:
            repo.insert_ledger_event(conn, shift.engagement_slug, event)
        for draft, event in zip(drafts, events):
            if draft.event_type is not LedgerEventType.INCIDENT_OPENED:
                continue
            check = next(item for item in checks.values() if item.id == draft.cause_refs[1])
            repo.insert_incident(conn, Incident(
                id=f"{config.INCIDENT_PREFIX}-{repo.count_incidents(conn, shift.engagement_slug) + 1:02d}",
                engagement_slug=shift.engagement_slug, shift_id=shift.id,
                opening_run_id=run.id, failing_output_ref=check.observed_ref,
                check_result_id=check.id,
                reason_code=check.reason_code or ReasonCode(draft.payload["reason_code"]),
                opened_event_seq=event.seq, state=IncidentState.OPEN,
            ))
        for (incident_id, _), event in zip(resolving, events[len(drafts):]):
            repo.resolve_incident(conn, incident_id, version.id, event.seq)
        repo.update_run(conn, run.id, RunState.FINALIZED, ended_at=_now())
        conn.commit()
    except Exception:
        conn.rollback()
        repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
        conn.commit()
        raise
    return get_run(conn, run.id)


def execute_run_task(db_path: str, run_id: str,
                     live_budget: LiveOperationBudget | None = None) -> None:
    conn = db.connect(db_path)
    try:
        execute_run(conn, run_id, live_budget)
    finally:
        conn.close()


_OPERATION_DRAFT_TYPES = (LedgerEventType.SALE_COMPLETED, LedgerEventType.INCIDENT_OPENED)


def replay_assessment(conn: sqlite3.Connection, run_id: str) -> ReplayReport:
    """Re-derive one finalized operation from its captured bytes, writing nothing (S19).

    The captured context, captured outputs and captured public state are the only
    inputs, so editing the current mission fixture, another fixture or today's
    incident state cannot change the result. A legacy run that predates the
    capture reports UNKNOWN_MISSING_INPUTS instead of a guessed replay. Chain
    integrity stays a separate ``chain.verify_chain`` check; neither proof
    substitutes for the other.
    """
    run = repo.get_run(conn, run_id)
    if run is None:
        raise LifecycleError("not_found", f"unknown run: {run_id}")
    if run.purpose is RunPurpose.LEGACY_OPERATION or run.context_id is None:
        return _unknown_inputs_report(run.id)
    if run.purpose is not RunPurpose.OPERATION:
        raise LifecycleError("conflict", "semantic replay is defined for operational runs")
    if run.state is not RunState.FINALIZED:
        raise LifecycleError("conflict", "replay needs a finalized assessment")
    context = repo.get_execution_context(conn, run.context_id)
    snapshot_bytes = repo.get_run_snapshot_bytes(conn, run.id)
    outputs = repo.list_outputs(conn, run.id)
    workload = (context.workloads[0]
                if context is not None and len(context.workloads) == 1 else None)
    if (context is None or workload is None or snapshot_bytes is None
            or not outputs or run.selection_id is None):
        return _unknown_inputs_report(run.id)
    try:
        mission_bytes = base64.b64decode(context.mission_bytes_base64, validate=True)
        state_bytes = base64.b64decode(context.public_data_bytes_base64, validate=True)
        batch_bytes = base64.b64decode(workload.request_batch_bytes_base64, validate=True)
        if (_hash_bytes(mission_bytes) != context.mission_hash
                or _hash_bytes(state_bytes) != context.public_data_hash
                or snapshot_bytes != state_bytes
                or canonical.content_hash(_encode(batch_bytes)) != workload.request_batch_hash):
            return _unknown_inputs_report(run.id)
        mission = task_contract.load_mission_bytes(mission_bytes)
        snapshot = task_contract.load_public_state_bytes(state_bytes)
    except (ValueError, ShiftworkDomainError):
        return _unknown_inputs_report(run.id)
    captured = {item.request_ordinal: item for item in outputs}
    if set(captured) != set(range(1, workload.request_count + 1)):
        return _unknown_inputs_report(run.id)
    stored_checks = repo.list_check_results(conn, run.id)
    stored_by_check_id = {check.check_id: check for check in stored_checks}
    assessed: list[task_contract.TaskAssessment] = []
    recomputed: dict[str, CheckResult] = {}
    completed = 0
    mandatory_pass = True
    for index, spec in enumerate(mission.request_specs, start=1):
        output = captured[index]
        try:
            response = task_contract.validate_response_envelope(spec, output.body)
        except TaskEnvelopeInvalid:
            response = None
        rows = evaluator.assess_request(spec=spec, request_ordinal=index, mission=mission,
                                        snapshot=snapshot, response=response)
        assessed.extend(rows)
        completed += int(evaluator.request_usefully_completed(spec, rows))
        mandatory_pass &= all(row.mandatory_pass for row in rows)
        for row in rows:
            check_id = f"task:{row.request_id}:{row.task_id}"
            stored = stored_by_check_id.get(check_id)
            recomputed[check_id] = CheckResult(
                # The stored id is provenance the replay must not re-allocate:
                # re-deriving the global count would shift every later id.
                id=(stored.id if stored is not None
                    else f"replay-unstored-{len(recomputed) + 1:02d}"),
                run_id=run.id,
                check_id=check_id,
                verdict="pass" if row.mandatory_pass else "fail",
                observed_ref=output.id,
                reason_code=(row.reason_codes[0] if row.reason_codes else
                             (None if row.mandatory_pass else ReasonCode.REQUIRED_TASK_MISSING)),
            )
    assessment = OperationalAssessment(
        run_id=run.id, context_hash=context.content_hash,
        complete_request_count=completed, expected_request_count=len(mission.request_specs),
        mandatory_pass=mandatory_pass, rule_version=context.reducer_version,
        assessed_at=_now(), selection_id=run.selection_id,
    )
    drafts = reducer.reduce_operation(run, assessment, mission, tuple(assessed),
                                      tuple(recomputed.values()))
    check_differences = _check_differences(stored_checks, list(recomputed.values()))
    event_draft_differences = _event_draft_differences(
        _stored_operation_drafts(conn, run, context.engagement_slug), drafts)
    status = "DIFFERENT" if check_differences or event_draft_differences else "IDENTICAL"
    return ReplayReport(run_id=run.id, status=status,
                        check_differences=tuple(check_differences),
                        event_draft_differences=tuple(event_draft_differences),
                        wrote_rows=False)


def _unknown_inputs_report(run_id: str) -> ReplayReport:
    """A run without captured inputs has no replayable evidence; never guess one."""
    return ReplayReport(run_id=run_id, status="UNKNOWN_MISSING_INPUTS",
                        check_differences=(), event_draft_differences=(), wrote_rows=False)


def _check_differences(stored: list[CheckResult],
                       replayed: list[CheckResult]) -> list[dict[str, JsonValue]]:
    """Field-level differences between stored checks and their replay, by check id."""
    stored_by_id = {check.check_id: check for check in stored}
    replayed_by_id = {check.check_id: check for check in replayed}
    differences: list[dict[str, JsonValue]] = []
    for check_id in sorted(set(stored_by_id) | set(replayed_by_id)):
        stored_check = stored_by_id.get(check_id)
        replayed_check = replayed_by_id.get(check_id)
        if stored_check is None or replayed_check is None:
            differences.append({"check_id": check_id,
                                "difference": "extra_stored" if stored_check else "missing_stored"})
            continue
        stored_view = stored_check.model_dump(mode="json")
        replayed_view = replayed_check.model_dump(mode="json")
        for field in ("verdict", "observed_ref", "reason_code"):
            if stored_view[field] != replayed_view[field]:
                differences.append({"check_id": check_id, "field": field,
                                    "stored": stored_view[field],
                                    "replayed": replayed_view[field]})
    return differences


def _stored_operation_drafts(conn: sqlite3.Connection, run: Run,
                             slug: str) -> list[dict[str, JsonValue]]:
    """The stored reduction output of one run: its own sale/incident-opened events.

    An incident-resolution event also names the resolving run, but it derives
    from the incident state at finalization, not from the run's captured bytes,
    so it is not part of the semantic replay; chain verification covers its
    integrity.
    """
    views: list[dict[str, JsonValue]] = []
    for event in repo.list_ledger_events(conn, slug):
        if (event.event_type in _OPERATION_DRAFT_TYPES and event.cause_refs
                and event.cause_refs[0] == run.id):
            view = event.model_dump(mode="json")
            views.append({key: view[key]
                          for key in ("event_type", "cause_refs", "payload", "synthetic")})
    return views


def _event_draft_differences(stored: list[dict[str, JsonValue]],
                             replayed: list[LedgerEventDraft]) -> list[dict[str, JsonValue]]:
    """Field-level differences between stored operation events and replayed drafts."""
    replayed_views: list[dict[str, JsonValue]] = []
    for draft in replayed:
        view = draft.model_dump(mode="json")
        replayed_views.append({key: view[key]
                               for key in ("event_type", "cause_refs", "payload", "synthetic")})
    differences: list[dict[str, JsonValue]] = []
    for position, (first, second) in enumerate(
            itertools.zip_longest(stored, replayed_views), start=1):
        if first is None or second is None:
            differences.append({
                "position": position,
                "difference": "missing_stored" if first is None else "extra_stored",
                "stored": first, "replayed": second,
            })
            continue
        for field in ("event_type", "cause_refs", "payload", "synthetic"):
            if first[field] != second[field]:
                differences.append({"position": position, "field": field,
                                    "stored": first[field], "replayed": second[field]})
    return differences


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
    """Startup recovery: fail nonterminal work without retrying or refunding it.

    A restart can leave runs in QUEUED, RUNNING or CAPTURED; none of them
    resumes. Each is marked FAILED with the typed INTERNAL failure kind (the
    interruption is the controller's, not the service's) while its completed
    captures, log bytes and rotation draws stay byte-for-byte intact and no
    checks or events are written. A restart can also strand an assist event
    between its committed reservation and its outcome write; each such event is
    marked FAILED with the controller-side ``ASSIST_INTERRUPTED`` code, keeps
    its consumed budget slot and refuses every decision, exactly like a provider
    failure. Terminal, decided, FINALIZED and FAILED rows are untouched, so the
    call is idempotent. A reserved or claimed comparison also becomes FAILED;
    its six slots remain visible, and any stored capture is retained. Returns
    the reconciled run, assist event and comparison ids.

    Startup is the only reconciliation point (``app.py`` lifespan is the sole call
    site): work left nonterminal while the app keeps running, for example a run
    whose background task never executes or an assist outcome write that failed,
    is not reconciled until the process restarts, and ``close_shift`` refuses
    that shift until its runs are reconciled.
    """
    reconciled: list[str] = []
    for run in repo.list_nonterminal_runs(conn):
        repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
        if run.trial_slot_id is not None:
            # A comparison slot shares its run's fate: the slot is not refunded,
            # not re-executed and not silently dropped from the six-slot schedule.
            repo.update_trial_slot(conn, run.trial_slot_id, state="FAILED")
        reconciled.append(run.id)
    for event in repo.list_pending_assist_events(conn):
        repo.finish_assist_event(
            conn, event.id, response="", proposed_patch=None, failure_code=ASSIST_INTERRUPTED
        )
        reconciled.append(event.id)
    for experiment in repo.list_nonterminal_comparisons(conn):
        for slot in repo.list_trial_slots(conn, experiment.id):
            if slot.state not in ("COMPLETE", "FAILED"):
                repo.update_trial_slot(conn, slot.id, state="FAILED")
        repo.update_experiment_state(conn, experiment.id, "FAILED")
        reconciled.append(experiment.id)
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
    slot = repo.get_trial_slot_for_run(conn, run_id)
    return [output for output in repo.list_outputs(conn, run_id)
            if slot is None or output.request_ordinal <= slot.request_count]


def list_check_results(conn: sqlite3.Connection, run_id: str) -> list[CheckResult]:
    get_run(conn, run_id)
    return repo.list_check_results(conn, run_id)


def get_incident(conn: sqlite3.Connection, incident_id: str) -> Incident:
    incident = repo.get_incident(conn, incident_id)
    if incident is None:
        raise LifecycleError("not_found", f"unknown incident: {incident_id}")
    return incident


def _stimulus_record(conn: sqlite3.Connection, run: Run, ordinal: int,
                     records: dict[str, JsonValue]) -> JsonValue | None:
    """The public record the executed request ordinal asked about, or None.

    The stimulus comes from the run's persisted request batch; any unavailable or
    inconsistent source degrades to None instead of failing the caller.
    """
    if run.purpose is RunPurpose.LEGACY_OPERATION:
        return None
    try:
        if run.context_id:
            context = repo.get_execution_context(conn, run.context_id)
            if context is None:
                return None
            workload = next((item for item in context.workloads
                             if run.request_batch_ref == f"frozen-workload:{item.id}"), None)
            if workload is None:
                return None
            frozen_bytes = base64.b64decode(workload.request_batch_bytes_base64)
            batch = executor.load_batch(executor.BatchRef(
                path_ref=run.request_batch_ref, content_hash=workload.request_batch_hash,
            ), frozen_bytes)
        else:
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
    record_id = body.get("record_id")
    if isinstance(record_id, str):
        return records.get(record_id)
    entity_ref = body.get("entity_ref")
    if isinstance(entity_ref, str):
        stock = [record for record in records.values()
                 if record.get("entity_ref") == entity_ref and record.get("kind") == "stock"]
        if len(stock) == 1:
            return stock[0]
    return None


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
    if run.context_id is not None and run.purpose is RunPurpose.OPERATION:
        context = repo.get_execution_context(conn, run.context_id)
        if context is None:
            return evidence
        try:
            mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))
            snapshot = task_contract.load_public_state_bytes(base64.b64decode(context.public_data_bytes_base64))
            spec = mission.request_specs[output.request_ordinal - 1]
            response = task_contract.validate_response_envelope(spec, output.body)
            display = customer_answer.render_task_customer_text(
                spec=spec, mission=mission, snapshot=snapshot, response=response)
        except (IndexError, ShiftworkDomainError, ValueError):
            return evidence
        statuses = {item.status.value for item in response.task_results}
        action = ("escalate" if "REFERRED" in statuses else "ask" if "NEEDS_CLARIFICATION" in statuses
                  else "decline" if "REFUSED" in statuses else "answer")
        evidence["customer_answer"] = {
            "action": action, "display_text": display,
            "claims": [{"kind": claim.kind, "value": claim.value}
                       for task in response.task_results for claim in task.claims],
            "evidence_refs": list(response.evidence_refs), "verified_record_age_ms": None,
        }
        return evidence
    records: dict[str, JsonValue] = {}
    try:
        snapshot_bytes = _snapshot_bytes_for_run(conn, run)
        records = _public_records(snapshot_bytes)
    except (OSError, ValueError):
        snapshot_bytes = None
    record = _stimulus_record(conn, run, output.request_ordinal, records) if snapshot_bytes else None
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
    if (latest_run is None and latest_shift is not None
            and latest_shift.opening_mode is ShiftOpeningMode.LEGACY_FIRST_CHOICE):
        previous = conn.execute(
            "SELECT id FROM shifts WHERE engagement_slug = ? AND seq = ? AND state = 'closed'",
            (slug, latest_shift.seq - 1),
        ).fetchone()
        if previous is not None:
            historical = repo.get_latest_run(conn, previous["id"])
            if historical is not None and historical.purpose is RunPurpose.LEGACY_OPERATION:
                latest_run = historical
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
    requests_run = len(list_outputs(conn, latest_run.id)) if latest_run else 0
    attempts_used = repo.count_operation_runs(conn, latest_shift.id) if latest_shift else 0
    attempt_limit = (2 if selection is not None and selection.kind == "LEARNER_CHOICE"
                     and selection.comparison_id is not None
                     else _attempt_limit(conn, slug))
    successful_operation = (latest_shift is not None and any(
        run.purpose is not RunPurpose.EXPERIMENT and run.state is RunState.FINALIZED
        for run in repo.list_runs_for_shift(conn, latest_shift.id)))
    incidents = repo.list_incidents(conn, slug)
    events = repo.list_ledger_events(conn, slug)
    status = chain.verify_chain(events)
    if status is chain.ChainStatus.BROKEN:
        raise LifecycleError("conflict", "ledger chain is BROKEN; refusing board counters")
    operation_runs = ([run for run in repo.list_runs_for_shift(conn, latest_shift.id)
                       if run.purpose is not RunPurpose.EXPERIMENT]
                      if latest_shift else [])
    retry_blocked = (attempt_limit == 2 and len(operation_runs) == 1
                     and operation_runs[0].state is RunState.FAILED
                     and (bool(repo.list_outputs(conn, operation_runs[0].id))
                          or any(operation_runs[0].id in event.cause_refs for event in events)
                          or operation_runs[0].selection_id != (selection.id if selection else None)))
    attempts_remaining = (0 if attempt_limit == 2 and (successful_operation or retry_blocked)
                          else max(0, attempt_limit - attempts_used))
    totals: dict[str, int] = {}
    for event in events:
        totals[event.event_type.value] = totals.get(event.event_type.value, 0) + 1
    inherited_requirements = None
    if selection is not None and selection.comparison_id is not None:
        comparison = repo.get_experiment(conn, selection.comparison_id)
        comparison_context = (
            repo.get_execution_context(conn, comparison.context_id) if comparison else None
        )
        if comparison_context is not None:
            inherited_requirements = {
                "comparison_id": comparison.id,
                "requirement_set_id": comparison_context.requirement_set_id,
                "requirement_set_hash": comparison_context.requirement_set_hash,
                "visible_check_set_hash": comparison_context.visible_check_set_hash,
            }
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
        "inherited_requirements": inherited_requirements,
        "artifact_files": tuple(sorted(latest_version.files)) if latest_version else (),
        "requests_run": requests_run,
        "attempts_used": attempts_used,
        "attempt_limit": attempt_limit,
        "attempts_remaining": attempts_remaining,
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

    The source run must belong to this shift, except for the immediately prior
    closed v5 shift when this is its first-choice successor. It must have produced
    the named request ordinal. ``authored_by`` is not caller-controlled: the model fixes it to
    the learner, and no assist or model output can author one.
    """
    shift = _require_open_shift(conn, shift_id)

    run = repo.get_run(conn, request.source_run_id)
    if run is None:
        raise LifecycleError("not_found", f"unknown source run: {request.source_run_id}")
    source_shift = repo.get_shift(conn, run.shift_id)
    inherited_source = (
        shift.opening_mode is ShiftOpeningMode.LEGACY_FIRST_CHOICE
        and source_shift is not None
        and source_shift.engagement_slug == shift.engagement_slug
        and source_shift.seq == shift.seq - 1
        and source_shift.state == "closed"
        and source_shift.opening_mode is None
        and run.purpose is RunPurpose.LEGACY_OPERATION
    )
    if run.shift_id != shift.id and not inherited_source:
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


def _private_public_needles(conn: sqlite3.Connection | None = None) -> tuple[str, ...]:
    """Values that must not appear in serialized diagnostic projections."""
    needles = {str(Path.cwd()), sealed_store.private_storage_locator(), "sealed/cases"}
    for key in ("NEBIUS_API_KEY", "NEBIUS_PROJECT_ID"):
        value = os.environ.get(key)
        if value:
            needles.add(value)
    for family in (*config.BOOKSHOP_FAMILIES, *config.BOOKSHOP_COMPARISON_FAMILIES):
        for case in sealed_store.load_family(family).cases:
            needles.update((case.id, case.check_id))
            note = case.expected.get("note")
            if isinstance(note, str) and len(note) >= 25:
                needles.add(note)
            if case.stimulus is not None:
                stimulus = case.stimulus
                needles.update((stimulus.request.request_id, stimulus.request.text,
                                stimulus.task_spec.id, stimulus.task_spec.text,
                                stimulus.state_delta.description))
                aspect = case.expected.get("aspect")
                if isinstance(aspect, str) and len(aspect) >= 8:
                    needles.add(aspect)
    if conn is not None:
        needles.update(row["resolved_state_sha256"] for row in conn.execute(
            "SELECT resolved_state_sha256 FROM protected_case_snapshots"))
    return tuple(needle for needle in needles if len(needle) >= 8)


def assert_public_projection(payload: object, conn: sqlite3.Connection | None = None) -> None:
    try:
        assert_public_safe(payload, _private_public_needles(conn))
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
    assert_public_projection(payload, conn)
    return payload


def observed_condition(state_bytes: bytes, dependencies: dict[str, str]) -> ContextCondition:
    """Label the frozen public condition from the dependency state actually observed.

    The condition kind is derived from the state bytes the assessment consumes, so
    a later observed dependency outage (Gate 3 S3.1's ``dependency_unavailable``)
    is recorded by the controller, never supplied by a caller. Condition bytes and
    hash stay identical to the public state's, which keeps the frozen-context
    reconstruction check (``_frozen_comparison_context_hash``) intact.
    """
    unavailable = sorted(
        name for name, value in dependencies.items() if value != "available"
    )
    if unavailable:
        kind, identifier = "dependency_unavailable", "condition-dependency-outage"
        label = "Observed dependency outage: " + ", ".join(unavailable)
    else:
        kind, identifier = "normal", "condition-normal"
        label = "Normal public conditions"
    return ContextCondition(
        id=identifier,
        kind=kind,
        public_label=label,
        exact_bytes_base64=_encode(state_bytes),
        content_hash=_hash_bytes(state_bytes),
    )


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
    conn: sqlite3.Connection, shift: Shift, *, isolated: bool = False,
    operation: bool = False,
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
    if operation:
        starting_state = {
            "ledger_head": chain.next_prev_hash(repo.list_ledger_events(conn, shift.engagement_slug)),
            "unresolved_incident_ids": [incident.id for incident in repo.list_incidents(
                conn, shift.engagement_slug) if incident.state is not IncidentState.RESOLVED],
        }
    condition = observed_condition(snapshot_bytes, snapshot.dependencies)
    fields = _diagnostic_context_fields(
        shift, mission, mission_bytes, snapshot_bytes, specs_bytes, workload, condition, starting_state
    )
    if operation:
        fields["evaluator_version"] = "operation-task-v1"
        fields["reducer_version"] = "operation-ledger-v1"
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


# --- Slice 15: the qualifying comparison ------------------------------------

COMPARISONS_PER_SHIFT = 1
# One retained-alternative re-test per shift, reserved separately from the
# qualifying comparison (Gate 3 S6.7); it consumes its own protected exposure.
LATER_COMPARISONS_PER_SHIFT = 1
COMPARE_DEADLINE_S = 10
COMPARE_EVALUATOR_VERSION = evaluator.RULE_VERSION
COMPARE_REDUCER_VERSION = "no-reduction: a qualifying comparison writes no ledger event"
COMPARISON_PAIRS = 3


def _canonical_specs_bytes(specs: tuple[task_contract.CustomerRequestSpec, ...]) -> bytes:
    return canonical.canonical_bytes([spec.model_dump(mode="json") for spec in specs])


def _read_comparison_workloads(
    slug: str, mission: task_contract.MissionSpec, snapshot_bytes: bytes
) -> tuple[FrozenWorkload, ...]:
    """Load and verify the engagement's reviewed workload manifest, or fail closed.

    The manifest is the controller's only source of workload paths, bytes, counts
    and task-spec hashes, and it is selected by the shift's engagement slug, never
    by caller input. Every pinned value is recomputed from the actual files here:
    a replaced batch, a swapped pair assignment, a changed count or a file edited
    after review fails before any reservation exists.
    """
    if slug != config.BOOKSHOP_SLUG:
        raise LifecycleError("conflict", "this engagement has no reviewed comparison workloads")
    try:
        data = json.loads(config.PIVOT_COMPARE_MANIFEST.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LifecycleError("conflict", "the reviewed comparison manifest is unreadable") from exc
    _require_reviewed_comparison_material(data, "comparison workload manifest", "workloads")
    if (data.get("engagement_slug") != slug or data.get("schema_version") != 1
            or data.get("comparison_state_sha256") != _hash_bytes(snapshot_bytes)):
        raise LifecycleError(
            "conflict", "the reviewed comparison manifest belongs to another engagement"
        )
    entries = data.get("workloads")
    if not isinstance(entries, list) or [entry.get("ordinal") for entry in entries] != [1, 2, 3]:
        raise LifecycleError(
            "conflict", "the reviewed comparison manifest must map ordinals 1, 2 and 3"
        )
    workloads: list[FrozenWorkload] = []
    for entry in entries:
        try:
            batch_bytes = (
                config.PIVOT_COMPARE_REQUEST_DIR / str(entry["request_file"])
            ).read_bytes()
            specs_bytes = (
                config.PIVOT_COMPARE_REQUEST_DIR / str(entry["task_spec_file"])
            ).read_bytes()
        except (OSError, KeyError, TypeError) as exc:
            raise LifecycleError(
                "conflict", f"comparison workload {entry.get('ordinal')} is unreadable"
            ) from exc
        if (
            hashlib.sha256(batch_bytes).hexdigest() != entry.get("request_bytes_sha256")
            or len(batch_bytes) != entry.get("request_bytes_length")
        ):
            raise LifecycleError(
                "conflict",
                f"comparison workload {entry['ordinal']} does not match its reviewed raw bytes",
            )
        try:
            loaded = json.loads(specs_bytes.decode("utf-8"))
            specs = tuple(
                task_contract.CustomerRequestSpec.model_validate(item) for item in loaded
            )
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise LifecycleError(
                "conflict", f"comparison workload {entry['ordinal']} task specs are unusable"
            ) from exc
        canonical_specs = _canonical_specs_bytes(specs)
        if hashlib.sha256(canonical_specs).hexdigest() != entry.get("task_specs_sha256"):
            raise LifecycleError(
                "conflict",
                f"comparison workload {entry['ordinal']} does not match its reviewed task specs",
            )
        # Parse the exact frozen bytes with the same parser that each executor
        # uses. In particular, a blank line is a malformed request, not a row
        # reservation may silently discard before exposure is spent.
        try:
            batch = executor.load_batch(
                executor.BatchRef(
                    path_ref=str(entry["request_file"]),
                    content_hash=canonical.content_hash(_encode(batch_bytes)),
                ),
                batch_bytes,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise LifecycleError(
                "conflict", f"comparison workload {entry['ordinal']} carries a malformed request"
            ) from exc
        if (
            len(batch) != entry.get("request_count")
            or len(specs) != entry.get("request_count")
            or not 1 <= len(specs) <= 4
        ):
            raise LifecycleError(
                "conflict",
                f"comparison workload {entry['ordinal']} request count does not match its manifest",
            )
        for stimulus, spec in zip(batch, specs, strict=True):
            try:
                parsed_line = json.loads(stimulus.body)
            except (TypeError, ValueError) as exc:
                raise LifecycleError(
                    "conflict", f"comparison workload {entry['ordinal']} carries a malformed request"
                ) from exc
            if (
                not isinstance(parsed_line, dict)
                or parsed_line.get("request_id") != spec.id
                or stimulus.text != spec.text
                or parsed_line.get("text") != spec.text
            ):
                raise LifecycleError(
                    "conflict",
                    f"comparison workload {entry['ordinal']} request {spec.id} does not match its spec",
                )
        for rule_id in {rule for spec in specs for rule in spec.mandatory_rule_ids}:
            if rule_id not in mission.public_rules:
                raise LifecycleError(
                    "conflict",
                    f"comparison workload {entry['ordinal']} cites an undefined public rule",
                )
        workloads.append(
            FrozenWorkload(
                id=f"workload-{entry['ordinal']:02d}",
                ordinal=entry["ordinal"],
                request_batch_bytes_base64=_encode(batch_bytes),
                request_batch_hash=canonical.content_hash(_encode(batch_bytes)),
                request_specs_bytes_base64=_encode(canonical_specs),
                request_specs_hash=hashlib.sha256(canonical_specs).hexdigest(),
                request_count=entry["request_count"],
            )
        )
    return tuple(workloads)


def _require_reviewed_comparison_material(data: dict[str, Any], label: str, payload_key: str) -> None:
    """Require an operator seal over the exact reviewed inventory, not a draft label."""
    payload = data.get(payload_key)
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if data.get("review_status") != "OPERATOR_SEALED" or data.get("sealed_payload_sha256") != digest:
        raise LifecycleError("conflict", f"{label} awaits operator review and sealing")


def _exposure_refs(conn: sqlite3.Connection, slug: str, family: str) -> set[str]:
    """Every variant of one family this engagement already consumed or retired.

    Both exposure stores count: legacy attempt draws and comparison reservations.
    A retired or invalidated item stays in the set, so a compromised group can
    never be re-drawn (ADR 0001).
    """
    refs = {
        draw.variant_ref
        for draw in repo.list_rotation_draws(conn, slug)
        if draw.family == family
    }
    refs.update(
        item.variant_ref for item in repo.list_exposure_items_for_family(conn, slug, family)
    )
    return refs


def _comparison_schedule(
    context_hash: str, candidate_hashes: tuple[str, str]
) -> tuple[tuple[int, str, int], ...]:
    """The precommitted slot order: (pair ordinal, candidate label, execution ordinal).

    Pair 1 runs A then B, pair 2 runs B then A, and pair 3's order is derived
    from the low bit of a decision hash over the context hash and both candidate
    content hashes. Pair 3's input includes the context hash, so the schedule is
    fixed with the frozen material and computed before the experiment content
    hash exists.
    """
    decision = hashlib.sha256(f"{context_hash}:{candidate_hashes[0]}:{candidate_hashes[1]}".encode("utf-8")).digest()
    pair_three = ("A", "B") if decision[-1] & 1 == 0 else ("B", "A")
    order = [(1, "A"), (1, "B"), (2, "B"), (2, "A"), (3, pair_three[0]), (3, pair_three[1])]
    return tuple((pair, label, index) for index, (pair, label) in enumerate(order, start=1))


def _comparison_context_fields(
    shift: Shift,
    mission: task_contract.MissionSpec,
    mission_bytes: bytes,
    snapshot_bytes: bytes,
    workloads: tuple[FrozenWorkload, ...],
    reservation_id: str,
    isolated: bool,
    starting_state: dict[str, Any],
    protected_bindings: tuple[task_contract.ProtectedBinding, ...],
    condition: ContextCondition,
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "engagement_slug": shift.engagement_slug,
        "workloads": [workload.model_dump(mode="json") for workload in workloads],
        "mission_hash": _hash_bytes(mission_bytes),
        "public_data_hash": _hash_bytes(snapshot_bytes),
        "starting_business_state_hash": canonical.content_hash(starting_state),
        "requirement_set_id": f"public-rubric:{mission.engagement_slug}:v{mission.version}",
        "requirement_set_hash": _hash_bytes(mission_bytes),
        "visible_check_set_hash": canonical.content_hash(
            [
                {"ordinal": workload.ordinal, "task_specs_hash": workload.request_specs_hash}
                for workload in workloads
            ]
        ),
        "condition": condition.model_dump(mode="json"),
        "evaluator_version": COMPARE_EVALUATOR_VERSION,
        "reducer_version": COMPARE_REDUCER_VERSION,
        "executor_class": EvidenceMode.ISOLATED_LIVE.value if isolated else EvidenceMode.TRUSTED_LOCAL.value,
        "harness_hash": _hash_bytes(
            (b"sandbox-driver-v1" if isolated else DIAGNOSTIC_HARNESS_REF.encode("utf-8"))
        ),
        "image_ref": config.TOKEN_FACTORY_IMAGE if isolated else DIAGNOSTIC_IMAGE_REF,
        "service_model": config.SERVICE_MODEL if isolated else None,
        "service_model_settings_json": (
            {"temperature": 0, "max_tokens": GATEWAY_MAX_OUTPUT_TOKENS} if isolated else {}
        ),
        "resource_limits_json": {
            "deadline_s": 45 if isolated else COMPARE_DEADLINE_S,
            "max_requests": 4,
            "trial_slots": 2 * COMPARISON_PAIRS,
        },
        # The reservation is part of the frozen material: the bytes that were
        # reserved are the bytes that execute, and the reservation identity the
        # context names is the one the slots carry.
        "protected_reservation_id": reservation_id,
        "protected_bindings": [binding.model_dump(mode="json") for binding in protected_bindings],
    }
    return fields


def _reserved_protected_bindings(
    conn: sqlite3.Connection, reservation_id: str,
) -> tuple[task_contract.ProtectedBinding, ...]:
    bindings = []
    for reserved in sealed_store.load_reserved_comparison_cases(conn, reservation_id):
        stimulus = reserved.case.stimulus
        bindings.append(task_contract.ProtectedBinding(
            pair_ordinal=reserved.pair_ordinal, variant_ref=rotation.variant_ref(reserved.case),
            request_ordinal=stimulus.request.ordinal,
            stimulus_hash=canonical.content_hash(stimulus.model_dump(mode="json")),
            protected_state_hash=reserved.resolved_state_sha256,
        ))
    return tuple(sorted(bindings, key=lambda item: item.pair_ordinal))


def _frozen_comparison_context_hash(
    context: ExecutionContext, bindings: tuple[task_contract.ProtectedBinding, ...],
) -> str:
    fields = {
        "engagement_slug": context.engagement_slug,
        "workloads": [item.model_dump(mode="json") for item in context.workloads],
        "mission_hash": context.mission_hash,
        "public_data_hash": context.public_data_hash,
        "starting_business_state_hash": context.starting_business_state_hash,
        "requirement_set_id": context.requirement_set_id,
        "requirement_set_hash": context.requirement_set_hash,
        "visible_check_set_hash": context.visible_check_set_hash,
        "condition": context.condition.model_dump(mode="json"),
        "evaluator_version": context.evaluator_version,
        "reducer_version": context.reducer_version,
        "executor_class": context.executor_class.value,
        "harness_hash": context.harness_hash,
        "image_ref": context.image_ref,
        "service_model": context.service_model,
        "service_model_settings_json": context.service_model_settings_json,
        "resource_limits_json": context.resource_limits_json,
        "protected_reservation_id": context.protected_reservation_id,
        "protected_bindings": [item.model_dump(mode="json") for item in bindings],
    }
    return canonical.content_hash(fields)


def create_qualifying_comparison(
    conn: sqlite3.Connection,
    shift_id: str,
    *,
    candidate_a_version_id: str,
    candidate_b_version_id: str,
    investigation_id: str,
    declared_treatment: str,
    client_request_id: str,
    adapter: str = "local_process",
) -> Experiment:
    """Reserve one qualifying comparison atomically, before any result exists.

    One transaction writes the exposure reservation and its per-pair items, the
    frozen context (three verified workloads, reviewed mission, public state and
    ceilings), the experiment with its precommitted six-slot schedule, the six
    ordered trial slots and their six queued runs. A fault anywhere rolls back
    the whole reservation: there is no partially reserved comparison, and a
    failed reservation consumes nothing.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        shift = _require_open_shift(conn, shift_id)
        isolated = adapter == TokenFactoryAdapter.name
        if adapter not in (LocalProcessAdapter.name, TokenFactoryAdapter.name):
            raise LifecycleError("conflict", "no safe comparison executor is configured")
        if isolated and (
            not os.environ.get("NEBIUS_API_KEY") or not os.environ.get("NEBIUS_PROJECT_ID")
        ):
            raise BootstrapBlocked(
                "the verified isolated executor and its controller credentials are unavailable"
            )
        if investigation_id is None:
            raise LifecycleError(
                "conflict", "a qualifying comparison requires an owned investigation"
            )
        investigation = repo.get_investigation(conn, investigation_id)
        if investigation is None:
            raise LifecycleError("not_found", f"unknown investigation: {investigation_id}")
        if investigation.shift_id != shift.id:
            raise LifecycleError(
                "conflict", "a qualifying comparison requires an investigation owned by this shift"
            )
        candidate_a = repo.get_version(conn, candidate_a_version_id)
        candidate_b = repo.get_version(conn, candidate_b_version_id)
        if candidate_a is None or candidate_b is None:
            raise LifecycleError("not_found", "unknown candidate artifact version")
        if candidate_a.shift_id != shift.id or candidate_b.shift_id != shift.id:
            raise LifecycleError("conflict", "comparison candidates must belong to this shift")
        if candidate_a.content_hash == candidate_b.content_hash:
            raise LifecycleError(
                "conflict", "a qualifying comparison needs two distinct candidate versions"
            )
        if not isolated:
            pinned = {
                config.TRUSTED_LOCAL_FIXTURES["compare_candidate_a"][0],
                config.TRUSTED_LOCAL_FIXTURES["compare_candidate_b"][0],
            }
            if {candidate_a.content_hash, candidate_b.content_hash} != pinned:
                raise LifecycleError(
                    "conflict",
                    "only the two pinned reviewed candidates are executable as an offline comparison",
                )
        candidates = (
            CandidateRef(label="A", artifact_version_id=candidate_a.id,
                         artifact_content_hash=candidate_a.content_hash),
            CandidateRef(label="B", artifact_version_id=candidate_b.id,
                         artifact_content_hash=candidate_b.content_hash),
        )
        treatment = declared_treatment.strip()
        if not treatment:
            raise LifecycleError("conflict", "a qualifying comparison needs a declared treatment")
        replay = repo.get_experiment_by_client_request_id(conn, client_request_id)
        if replay is not None:
            if (
                replay.shift_id == shift.id
                and replay.kind is ExperimentKind.QUALIFYING_COMPARISON
                and replay.investigation_id == investigation.id
                and replay.candidates == candidates
                and replay.declared_treatment == treatment
            ):
                conn.rollback()
                return replay
            raise LifecycleError(
                "conflict", "client_request_id was already used for a different experiment"
            )
        used = repo.count_experiments_for_shift(conn, shift.id, ExperimentKind.QUALIFYING_COMPARISON)
        if used >= COMPARISONS_PER_SHIFT:
            raise LifecycleError(
                "conflict",
                f"this shift already reserved its qualifying comparison ({used} of "
                f"{COMPARISONS_PER_SHIFT})",
            )

        mission_bytes = config.PIVOT_MISSION.read_bytes()
        mission = task_contract.load_mission_bytes(mission_bytes, label=config.PIVOT_MISSION.name)
        if mission.engagement_slug != shift.engagement_slug:
            raise LifecycleError("conflict", "reviewed mission belongs to another engagement")
        snapshot_bytes = config.PIVOT_COMPARE_STATE.read_bytes()
        snapshot = task_contract.load_public_state_bytes(
            snapshot_bytes, label=config.PIVOT_COMPARE_STATE.name
        )
        if not snapshot.records:
            raise LifecycleError("conflict", "the reviewed public state carries no record")
        workloads = _read_comparison_workloads(shift.engagement_slug, mission, snapshot_bytes)
        events = repo.list_ledger_events(conn, shift.engagement_slug)
        chain_status = chain.verify_chain(events)
        if chain_status is chain.ChainStatus.BROKEN:
            raise LifecycleError("conflict", "ledger chain is BROKEN; refusing comparison")
        totals: dict[str, int] = {}
        for event in events:
            totals[event.event_type.value] = totals.get(event.event_type.value, 0) + 1
        starting_state = {
            "chain_status": chain_status.value,
            "ledger_event_count": len(events),
            "ledger_head_hash": events[-1].hash if events else None,
            "ledger_totals": totals,
            "unresolved_incidents": [
                incident.model_dump(mode="json")
                for incident in repo.list_incidents(conn, shift.engagement_slug)
                if incident.state in (IncidentState.OPEN, IncidentState.CLOSED_UNRESOLVED)
            ],
            "unresolved_limits": repo.list_unresolved_limits(conn, shift.engagement_slug),
        }

        reservation_id = f"reservation-{repo.count_exposure_reservations(conn) + 1:04d}"
        reservation = ExposureReservation(
            id=reservation_id,
            engagement_slug=shift.engagement_slug,
            scope="comparison",
            experiment_id=None,
            state="ACTIVE",
            created_at=_now(),
        )
        repo.insert_exposure_reservation(conn, reservation)
        reserved: dict[int, tuple[str, ...]] = {}
        for family in config.BOOKSHOP_COMPARISON_FAMILIES:
            drawn = rotation.select_pair_variants(
                family,
                sealed_store.load_reviewed_comparison_family(family).cases,
                _exposure_refs(conn, shift.engagement_slug, family),
            )
            for pair_ordinal, case in enumerate(drawn, start=1):
                stimulus = case.stimulus
                workload = workloads[pair_ordinal - 1]
                if (stimulus is None
                        or stimulus.request.ordinal != workload.request_count + 1
                        or stimulus.task_spec.id != stimulus.request.request_id
                        or stimulus.task_spec.text != stimulus.request.text
                        or stimulus.request.entity_ref not in stimulus.task_spec.requested_entities
                        or not stimulus.task_spec.tasks
                        or len({task.id for task in stimulus.task_spec.tasks}) != len(stimulus.task_spec.tasks)
                        or any(task.requested_entity_ref != stimulus.request.entity_ref
                               for task in stimulus.task_spec.tasks)
                        or any(rule not in mission.public_rules
                               for rule in stimulus.task_spec.mandatory_rule_ids)):
                    raise LifecycleError("conflict", "protected comparison stimulus violates the frozen public contract")
                resolved_state = task_contract.resolve_protected_state(snapshot_bytes, stimulus.state_delta)
                ref = rotation.variant_ref(case)
                exposure_item_id = f"{reservation_id}-{family}-p{pair_ordinal}"
                repo.insert_exposure_item(
                    conn,
                    ExposureItem(
                        id=exposure_item_id,
                        reservation_id=reservation_id,
                        engagement_slug=shift.engagement_slug,
                        family=family,
                        cycle=sealed_store.family_cycle(family),
                        variant_ref=ref,
                        pair_ordinal=pair_ordinal,
                        drawn_at=_now(),
                    ),
                )
                case_json = json.dumps(
                    case.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False,
                )
                repo.insert_protected_case_snapshot(
                    conn, exposure_item_id, ref, case_json,
                    hashlib.sha256(case_json.encode("utf-8")).hexdigest(),
                    resolved_state, _hash_bytes(resolved_state),
                )
                reserved[pair_ordinal] = reserved.get(pair_ordinal, ()) + (ref,)

        bindings = _reserved_protected_bindings(conn, reservation_id)
        fields = _comparison_context_fields(
            shift, mission, mission_bytes, snapshot_bytes, workloads, reservation_id, isolated,
            starting_state, bindings, observed_condition(snapshot_bytes, snapshot.dependencies),
        )
        context_hash = canonical.content_hash(fields)
        existing_context = repo.get_execution_context_by_hash(conn, context_hash)
        if existing_context is not None:
            context = existing_context
        else:
            context = ExecutionContext(
                id=f"context-{repo.count_execution_contexts(conn) + 1:04d}",
                schema_version=1,
                engagement_slug=shift.engagement_slug,
                workloads=workloads,
                mission_bytes_base64=_encode(mission_bytes),
                mission_hash=fields["mission_hash"],
                public_data_bytes_base64=_encode(snapshot_bytes),
                public_data_hash=fields["public_data_hash"],
                starting_business_state_json=starting_state,
                starting_business_state_hash=fields["starting_business_state_hash"],
                requirement_set_id=fields["requirement_set_id"],
                requirement_set_hash=fields["requirement_set_hash"],
                visible_check_set_hash=fields["visible_check_set_hash"],
                protected_reservation_id=reservation_id,
                condition=ContextCondition.model_validate(fields["condition"]),
                evaluator_version=fields["evaluator_version"],
                reducer_version=fields["reducer_version"],
                executor_class=EvidenceMode(fields["executor_class"]),
                harness_hash=fields["harness_hash"],
                image_ref=fields["image_ref"],
                service_model=fields["service_model"],
                service_model_settings_json=fields["service_model_settings_json"],
                resource_limits_json=fields["resource_limits_json"],
                created_at=_now(),
                content_hash=context_hash,
            )
            repo.insert_execution_context(conn, context)
        schedule = _comparison_schedule(
            context.content_hash, (candidate_a.content_hash, candidate_b.content_hash)
        )
        experiment = Experiment(
            id=f"experiment-{shift.id}-c1",
            shift_id=shift.id,
            kind=ExperimentKind.QUALIFYING_COMPARISON,
            investigation_id=investigation.id,
            candidates=candidates,
            declared_treatment=treatment,
            context_id=context.id,
            content_hash=canonical.content_hash(
                {
                    "shift_id": shift.id,
                    "kind": ExperimentKind.QUALIFYING_COMPARISON.value,
                    "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
                    "context_hash": context.content_hash,
                    "trial_count_per_candidate": COMPARISON_PAIRS,
                    "declared_treatment": treatment,
                    # The schedule is fixed before this hash exists; storing it in
                    # the hash means a later reordering is a different experiment.
                    "schedule": [
                        {"pair_ordinal": pair, "candidate_label": label, "execution_ordinal": ordinal}
                        for pair, label, ordinal in schedule
                    ],
                }
            ),
            trial_count_per_candidate=COMPARISON_PAIRS,
            state="PLANNED",
            client_request_id=client_request_id,
            created_at=_now(),
        )
        repo.insert_experiment(conn, experiment)
        conn.execute(
            "UPDATE exposure_reservations SET experiment_id = ? WHERE id = ?",
            (experiment.id, reservation_id),
        )
        versions = {"A": candidate_a, "B": candidate_b}
        for pair, label, ordinal in schedule:
            workload = workloads[pair - 1]
            slot = TrialSlot(
                id=f"{experiment.id}-slot-{ordinal}",
                experiment_id=experiment.id,
                pair_ordinal=pair,
                execution_ordinal=ordinal,
                candidate_label=label,
                artifact_version_id=versions[label].id,
                workload_id=workload.id,
                request_batch_hash=workload.request_batch_hash,
                request_count=workload.request_count,
                executed_request_count=workload.request_count + 1,
                protected_variant_refs=reserved.get(pair, ()),
                state="RESERVED",
            )
            repo.insert_trial_slot(conn, slot)
            run = Run(
                id=f"run-{repo.count_runs_all(conn) + 1:04d}",
                shift_id=shift.id,
                artifact_version_id=versions[label].id,
                request_batch_ref=f"frozen-workload:{workload.id}",
                shop_snapshot_ref=f"frozen-context:{context.id}",
                attempt_number=repo.count_runs(conn, shift.id) + 1,
                state=RunState.QUEUED,
                adapter=adapter,
                started_at=_now(),
                purpose=RunPurpose.EXPERIMENT,
                evidence_mode=EvidenceMode.ISOLATED_LIVE if isolated else EvidenceMode.TRUSTED_LOCAL,
                context_id=context.id,
                experiment_id=experiment.id,
                trial_slot_id=slot.id,
            )
            repo.insert_run(conn, run)
            repo.update_trial_slot(conn, slot.id, run_id=run.id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return experiment


def _require_dependency_only_variation(reviewed_bytes: bytes, observed_bytes: bytes) -> None:
    """The observed world may differ from the reviewed comparison world only in
    dependency availability, so the reviewed workload manifest stays valid: every
    record and entity the reviewed requests name is byte-identical after parsing,
    and only feasibility flags were observed differently."""
    try:
        reviewed = json.loads(reviewed_bytes.decode("utf-8"))
        observed = json.loads(observed_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LifecycleError("conflict", "an observed or reviewed world is unreadable") from exc
    if not isinstance(reviewed, dict) or not isinstance(observed, dict):
        raise LifecycleError("conflict", "an observed or reviewed world is unreadable")
    if set(reviewed) != set(observed):
        raise LifecycleError(
            "conflict", "the observed world is not the reviewed comparison world"
        )
    changed = sorted(
        key for key in reviewed if key != "dependencies" and reviewed[key] != observed[key]
    )
    if changed:
        raise LifecycleError(
            "conflict",
            "the observed world changes more than dependency availability: "
            + ", ".join(changed)
            + "; the reviewed comparison workloads do not apply",
        )


def create_later_condition_comparison(
    conn: sqlite3.Connection,
    shift_id: str,
    *,
    operation_run_id: str,
    declared_treatment: str,
    client_request_id: str,
    adapter: str = "local_process",
) -> Experiment:
    """Re-test the selected and retained versions under an observed later condition.

    The candidates are the current operating selection's exact selected version
    and its retained alternative; both are re-executed in fresh matched A/B slots
    under the public bytes of one already-observed operational context (Gate 2
    section 3, Gate 3 S6.7). The preceding operational run is never one side of
    the experiment: every slot is a new run, and the reservation is separate from
    the selection's original comparison exposure. A later-condition comparison can
    never back a selection. It cannot replace the operational run, edit the prior
    choice, resolve an incident or rewrite the ledger.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        shift = _require_open_shift(conn, shift_id)
        isolated = adapter == TokenFactoryAdapter.name
        if adapter not in (LocalProcessAdapter.name, TokenFactoryAdapter.name):
            raise LifecycleError("conflict", "no safe comparison executor is configured")
        if isolated and (
            not os.environ.get("NEBIUS_API_KEY") or not os.environ.get("NEBIUS_PROJECT_ID")
        ):
            raise BootstrapBlocked(
                "the verified isolated executor and its controller credentials are unavailable"
            )
        selection, selected_version = _selected_operating_version(conn, shift)
        if selection.kind != "LEARNER_CHOICE":
            raise LifecycleError(
                "conflict", "a later-condition comparison requires an explicit learner choice"
            )
        # append_selection only records a learner choice from a completed
        # qualifying comparison, so the retained alternative always exists and
        # differs in content; the lookup still fails closed if it ever vanishes.
        retained_version = repo.get_version(conn, selection.retained_alternative_version_id)
        if retained_version is None:
            raise LifecycleError("not_found", "the retained alternative version is missing")
        observed_run = repo.get_run(conn, operation_run_id)
        if observed_run is None:
            raise LifecycleError("not_found", f"unknown run: {operation_run_id}")
        if (
            observed_run.purpose is not RunPurpose.OPERATION
            or observed_run.state is not RunState.FINALIZED
            or observed_run.shift_id != shift.id
            or observed_run.selection_id != selection.id
            or observed_run.context_id is None
        ):
            raise LifecycleError(
                "conflict",
                "the observed context must be this shift's finalized operation of the "
                "current selection",
            )
        observed_context = repo.get_execution_context(conn, observed_run.context_id)
        if observed_context is None or observed_context.engagement_slug != shift.engagement_slug:
            raise LifecycleError("conflict", "the observed operational context is unavailable")
        if observed_context.condition.kind == "normal":
            raise LifecycleError(
                "conflict", "no later condition was observed by that operational run"
            )
        for candidate_version in (selected_version, retained_version):
            owner = repo.get_shift(conn, candidate_version.shift_id)
            if owner is None or owner.engagement_slug != shift.engagement_slug:
                raise LifecycleError(
                    "conflict", "comparison candidates must belong to this engagement"
                )
        candidates = (
            CandidateRef(label="A", artifact_version_id=selected_version.id,
                         artifact_content_hash=selected_version.content_hash),
            CandidateRef(label="B", artifact_version_id=retained_version.id,
                         artifact_content_hash=retained_version.content_hash),
        )
        treatment = declared_treatment.strip()
        if not treatment:
            raise LifecycleError("conflict", "a later-condition comparison needs a declared treatment")
        replay = repo.get_experiment_by_client_request_id(conn, client_request_id)
        if replay is not None:
            if (
                replay.shift_id == shift.id
                and replay.kind is ExperimentKind.LATER_CONDITION_COMPARISON
                and replay.observed_run_id == observed_run.id
                and replay.candidates == candidates
                and replay.declared_treatment == treatment
            ):
                conn.rollback()
                return replay
            raise LifecycleError(
                "conflict", "client_request_id was already used for a different experiment"
            )
        used = repo.count_experiments_for_shift(
            conn, shift.id, ExperimentKind.LATER_CONDITION_COMPARISON
        )
        if used >= LATER_COMPARISONS_PER_SHIFT:
            raise LifecycleError(
                "conflict",
                f"this shift already reserved its later-condition comparison ({used} of "
                f"{LATER_COMPARISONS_PER_SHIFT})",
            )
        if not isolated:
            pinned = {
                config.TRUSTED_LOCAL_FIXTURES["compare_candidate_a"][0],
                config.TRUSTED_LOCAL_FIXTURES["compare_candidate_b"][0],
            }
            if {selected_version.content_hash, retained_version.content_hash} != pinned:
                raise LifecycleError(
                    "conflict",
                    "only the two pinned reviewed candidates are executable as an offline comparison",
                )

        mission_bytes = config.PIVOT_MISSION.read_bytes()
        mission = task_contract.load_mission_bytes(mission_bytes, label=config.PIVOT_MISSION.name)
        if mission.engagement_slug != shift.engagement_slug:
            raise LifecycleError("conflict", "reviewed mission belongs to another engagement")
        # The frozen public bytes are the ones the operation actually observed, so
        # a later fixture edit cannot change the condition this experiment tested.
        snapshot_bytes = base64.b64decode(observed_context.public_data_bytes_base64, validate=True)
        if _hash_bytes(snapshot_bytes) != observed_context.public_data_hash:
            raise LifecycleError("conflict", "the observed context bytes do not verify")
        snapshot = task_contract.load_public_state_bytes(snapshot_bytes, label="observed-context")
        if not snapshot.records:
            raise LifecycleError("conflict", "the observed public state carries no record")
        # The reviewed workload manifest binds to the reviewed comparison world.
        # The observed world must be that world with only dependency availability
        # observed differently, so the reviewed requests stay valid for it and
        # the experiment runs under the exact bytes the operation observed.
        reviewed_comparison_bytes = config.PIVOT_COMPARE_STATE.read_bytes()
        _require_dependency_only_variation(reviewed_comparison_bytes, snapshot_bytes)
        workloads = _read_comparison_workloads(
            shift.engagement_slug, mission, reviewed_comparison_bytes
        )
        events = repo.list_ledger_events(conn, shift.engagement_slug)
        chain_status = chain.verify_chain(events)
        if chain_status is chain.ChainStatus.BROKEN:
            raise LifecycleError("conflict", "ledger chain is BROKEN; refusing comparison")

        reservation_id = f"reservation-{repo.count_exposure_reservations(conn) + 1:04d}"
        repo.insert_exposure_reservation(conn, ExposureReservation(
            id=reservation_id, engagement_slug=shift.engagement_slug,
            scope="comparison", experiment_id=None, state="ACTIVE", created_at=_now(),
        ))
        reserved: dict[int, tuple[str, ...]] = {}
        for family in config.BOOKSHOP_COMPARISON_FAMILIES:
            drawn = rotation.select_pair_variants(
                family,
                sealed_store.load_reviewed_comparison_family(family).cases,
                _exposure_refs(conn, shift.engagement_slug, family),
            )
            for pair_ordinal, case in enumerate(drawn, start=1):
                stimulus = case.stimulus
                workload = workloads[pair_ordinal - 1]
                if (stimulus is None
                        or stimulus.request.ordinal != workload.request_count + 1
                        or stimulus.task_spec.id != stimulus.request.request_id
                        or stimulus.task_spec.text != stimulus.request.text
                        or stimulus.request.entity_ref not in stimulus.task_spec.requested_entities
                        or not stimulus.task_spec.tasks
                        or len({task.id for task in stimulus.task_spec.tasks}) != len(stimulus.task_spec.tasks)
                        or any(task.requested_entity_ref != stimulus.request.entity_ref
                               for task in stimulus.task_spec.tasks)
                        or any(rule not in mission.public_rules
                               for rule in stimulus.task_spec.mandatory_rule_ids)):
                    raise LifecycleError("conflict", "protected comparison stimulus violates the frozen public contract")
                resolved_state = task_contract.resolve_protected_state(snapshot_bytes, stimulus.state_delta)
                ref = rotation.variant_ref(case)
                exposure_item_id = f"{reservation_id}-{family}-p{pair_ordinal}"
                repo.insert_exposure_item(conn, ExposureItem(
                    id=exposure_item_id, reservation_id=reservation_id,
                    engagement_slug=shift.engagement_slug, family=family,
                    cycle=sealed_store.family_cycle(family), variant_ref=ref,
                    pair_ordinal=pair_ordinal, drawn_at=_now(),
                ))
                case_json = json.dumps(
                    case.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False,
                )
                repo.insert_protected_case_snapshot(
                    conn, exposure_item_id, ref, case_json,
                    hashlib.sha256(case_json.encode("utf-8")).hexdigest(),
                    resolved_state, _hash_bytes(resolved_state),
                )
                reserved[pair_ordinal] = reserved.get(pair_ordinal, ()) + (ref,)

        totals: dict[str, int] = {}
        for event in events:
            totals[event.event_type.value] = totals.get(event.event_type.value, 0) + 1
        starting_state = {
            "chain_status": chain_status.value,
            "ledger_event_count": len(events),
            "ledger_head_hash": events[-1].hash if events else None,
            "ledger_totals": totals,
            "unresolved_incidents": [
                incident.model_dump(mode="json")
                for incident in repo.list_incidents(conn, shift.engagement_slug)
                if incident.state in (IncidentState.OPEN, IncidentState.CLOSED_UNRESOLVED)
            ],
            "unresolved_limits": repo.list_unresolved_limits(conn, shift.engagement_slug),
        }
        bindings = _reserved_protected_bindings(conn, reservation_id)
        fields = _comparison_context_fields(
            shift, mission, mission_bytes, snapshot_bytes, workloads, reservation_id, isolated,
            starting_state, bindings, observed_condition(snapshot_bytes, snapshot.dependencies),
        )
        context_hash = canonical.content_hash(fields)
        existing_context = repo.get_execution_context_by_hash(conn, context_hash)
        if existing_context is not None:
            context = existing_context
        else:
            context = ExecutionContext(
                id=f"context-{repo.count_execution_contexts(conn) + 1:04d}",
                schema_version=1,
                engagement_slug=shift.engagement_slug,
                workloads=workloads,
                mission_bytes_base64=_encode(mission_bytes),
                mission_hash=fields["mission_hash"],
                public_data_bytes_base64=_encode(snapshot_bytes),
                public_data_hash=fields["public_data_hash"],
                starting_business_state_json=starting_state,
                starting_business_state_hash=fields["starting_business_state_hash"],
                requirement_set_id=fields["requirement_set_id"],
                requirement_set_hash=fields["requirement_set_hash"],
                visible_check_set_hash=fields["visible_check_set_hash"],
                protected_reservation_id=reservation_id,
                condition=ContextCondition.model_validate(fields["condition"]),
                evaluator_version=fields["evaluator_version"],
                reducer_version=fields["reducer_version"],
                executor_class=EvidenceMode(fields["executor_class"]),
                harness_hash=fields["harness_hash"],
                image_ref=fields["image_ref"],
                service_model=fields["service_model"],
                service_model_settings_json=fields["service_model_settings_json"],
                resource_limits_json=fields["resource_limits_json"],
                created_at=_now(),
                content_hash=context_hash,
            )
            repo.insert_execution_context(conn, context)
        schedule = _comparison_schedule(
            context.content_hash, (selected_version.content_hash, retained_version.content_hash)
        )
        experiment = Experiment(
            id=f"experiment-{shift.id}-later-1",
            shift_id=shift.id,
            kind=ExperimentKind.LATER_CONDITION_COMPARISON,
            investigation_id=None,
            candidates=candidates,
            declared_treatment=treatment,
            context_id=context.id,
            content_hash=canonical.content_hash(
                {
                    "shift_id": shift.id,
                    "kind": ExperimentKind.LATER_CONDITION_COMPARISON.value,
                    "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
                    "context_hash": context.content_hash,
                    "trial_count_per_candidate": COMPARISON_PAIRS,
                    "declared_treatment": treatment,
                    "schedule": [
                        {"pair_ordinal": pair, "candidate_label": label, "execution_ordinal": ordinal}
                        for pair, label, ordinal in schedule
                    ],
                }
            ),
            trial_count_per_candidate=COMPARISON_PAIRS,
            state="PLANNED",
            client_request_id=client_request_id,
            created_at=_now(),
        )
        repo.insert_experiment(conn, experiment)
        repo.insert_observed_context(
            conn, experiment.id, observed_run.id, observed_context.id, experiment.created_at
        )
        conn.execute(
            "UPDATE exposure_reservations SET experiment_id = ? WHERE id = ?",
            (experiment.id, reservation_id),
        )
        versions = {"A": selected_version, "B": retained_version}
        for pair, label, ordinal in schedule:
            workload = workloads[pair - 1]
            slot = TrialSlot(
                id=f"{experiment.id}-slot-{ordinal}",
                experiment_id=experiment.id,
                pair_ordinal=pair,
                execution_ordinal=ordinal,
                candidate_label=label,
                artifact_version_id=versions[label].id,
                workload_id=workload.id,
                request_batch_hash=workload.request_batch_hash,
                request_count=workload.request_count,
                executed_request_count=workload.request_count + 1,
                protected_variant_refs=reserved.get(pair, ()),
                state="RESERVED",
            )
            repo.insert_trial_slot(conn, slot)
            run = Run(
                id=f"run-{repo.count_runs_all(conn) + 1:04d}",
                shift_id=shift.id,
                artifact_version_id=versions[label].id,
                request_batch_ref=f"frozen-workload:{workload.id}",
                shop_snapshot_ref=f"frozen-context:{context.id}",
                attempt_number=repo.count_runs(conn, shift.id) + 1,
                state=RunState.QUEUED,
                adapter=adapter,
                started_at=_now(),
                purpose=RunPurpose.EXPERIMENT,
                evidence_mode=EvidenceMode.ISOLATED_LIVE if isolated else EvidenceMode.TRUSTED_LOCAL,
                context_id=context.id,
                experiment_id=experiment.id,
                trial_slot_id=slot.id,
            )
            repo.insert_run(conn, run)
            repo.update_trial_slot(conn, slot.id, run_id=run.id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return experiment


def _comparison_run_request(
    run: Run, context: ExecutionContext, workload: FrozenWorkload, version: ArtifactVersion
) -> executor.RunRequest:
    isolated = run.adapter == TokenFactoryAdapter.name
    return executor.RunRequest(
        artifact_snapshot=executor.ArtifactSnapshotRef(
            files={path: text.encode("utf-8") for path, text in version.files.items()},
            manifest_hash=version.content_hash,
        ),
        request_batch=executor.BatchRef(
            path_ref=run.request_batch_ref,
            content_hash=workload.request_batch_hash,
        ),
        shop_snapshot_ref="",
        harness_ref="sandbox-driver-v1" if isolated else DIAGNOSTIC_HARNESS_REF,
        image_ref=context.image_ref if isolated else DIAGNOSTIC_IMAGE_REF,
        deadline_s=int(context.resource_limits_json.get("deadline_s", COMPARE_DEADLINE_S)),
        inference_grant=None,
        request_batch_bytes=base64.b64decode(workload.request_batch_bytes_base64),
    )


def _terminalize_comparison_slot(
    conn: sqlite3.Connection, slot: TrialSlot, state: str, failure: ExecutorFailure | None
) -> None:
    repo.update_run(conn, slot.run_id, RunState.FAILED if failure else RunState.FINALIZED, failure, _now())
    repo.update_trial_slot(conn, slot.id, state=state)


def retire_comparison_exposure(conn: sqlite3.Connection, reservation_id: str) -> None:
    """Retire a compromised comparison without deleting its spent evidence."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        reservation = repo.get_exposure_reservation(conn, reservation_id)
        if reservation is None or reservation.scope != "comparison" or reservation.experiment_id is None:
            raise LifecycleError("not_found", "unknown comparison exposure reservation")
        if reservation.state == "INVALIDATED":
            conn.rollback()
            return
        repo.update_exposure_reservation_state(conn, reservation.id, "INVALIDATED")
        repo.update_exposure_item_state(conn, reservation.id, "invalidated")
        for slot in repo.list_trial_slots(conn, reservation.experiment_id):
            if slot.state not in ("COMPLETE", "FAILED"):
                run = repo.get_run(conn, slot.run_id) if slot.run_id else None
                if run is not None and run.state not in (RunState.FINALIZED, RunState.FAILED):
                    repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
                repo.update_trial_slot(conn, slot.id, state="FAILED")
        repo.update_experiment_state(conn, reservation.experiment_id, "INVALIDATED")
        repo.invalidate_selections_for_comparison(conn, reservation.experiment_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def execute_comparison_slot(conn: sqlite3.Connection, slot: TrialSlot,
                            live_budget: LiveComparisonBudget | None = None) -> TrialSlot:
    """Execute one reserved comparison slot against its own frozen workload.

    The slot's workload is resolved by identity from the frozen context, and the
    bytes, hash and count are re-verified before anything runs: a slot whose
    binding no longer matches the context fails closed instead of quietly
    executing another workload. Each slot runs in its own fresh workspace, so no
    cache, booking or process state carries from one candidate to the next.
    """
    if slot.state != "RESERVED" or slot.run_id is None:
        return slot
    current_slot = repo.get_trial_slot(conn, slot.id)
    if current_slot is None or current_slot.state != "RESERVED":
        return current_slot or slot
    run = repo.get_run(conn, slot.run_id)
    context = repo.get_execution_context(conn, run.context_id) if run and run.context_id else None
    reservation = (repo.get_exposure_reservation(conn, context.protected_reservation_id)
                   if context and context.protected_reservation_id else None)
    version = repo.get_version(conn, slot.artifact_version_id)
    workload = next(
        (item for item in context.workloads if item.id == slot.workload_id), None
    ) if context else None
    if (
        run is None
        or run.state is not RunState.QUEUED
        or context is None
        or version is None
        or workload is None
        or reservation is None
        or reservation.state != "ACTIVE"
        or workload.request_batch_hash != slot.request_batch_hash
        or workload.request_count != slot.request_count
    ):
        if run is not None and run.state not in (RunState.FINALIZED, RunState.FAILED):
            repo.update_run(conn, slot.run_id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED, _now())
        repo.update_trial_slot(conn, slot.id, state="FAILED")
        conn.commit()
        return repo.get_trial_slot(conn, slot.id)

    try:
        snapshot_bytes = base64.b64decode(context.public_data_bytes_base64)
        mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))
        snapshot = task_contract.load_public_state_bytes(snapshot_bytes)
        specs = tuple(
            task_contract.CustomerRequestSpec.model_validate(item)
            for item in json.loads(base64.b64decode(workload.request_specs_bytes_base64).decode("utf-8"))
        )
        request = _comparison_run_request(run, context, workload, version)
        bindings = _reserved_protected_bindings(conn, context.protected_reservation_id)
        binding = next(item for item in bindings if item.pair_ordinal == slot.pair_ordinal)
        if (len(bindings) != COMPARISON_PAIRS
                or _frozen_comparison_context_hash(context, bindings) != context.content_hash
                or slot.protected_variant_refs != (binding.variant_ref,)
                or slot.executed_request_count != workload.request_count + 1
                or binding.request_ordinal != slot.executed_request_count):
            raise ValueError("protected slot binding differs from frozen context")
        reserved_case = next(item for item in sealed_store.load_reserved_comparison_cases(
            conn, context.protected_reservation_id) if item.pair_ordinal == slot.pair_ordinal)
        protected_state_bytes = reserved_case.resolved_state_bytes
        protected_line = task_contract.protected_request_bytes(reserved_case.case.stimulus.request)
        protected_ref = executor.BatchRef(
            path_ref="sealed:protected", content_hash=canonical.content_hash(_encode(protected_line)))
        protected_stimulus = executor.load_single_request(
            protected_ref, protected_line, slot.executed_request_count)
        if (_hash_bytes(protected_state_bytes) != binding.protected_state_hash
                or canonical.content_hash(reserved_case.case.stimulus.model_dump(mode="json")) != binding.stimulus_hash):
            raise ValueError("protected stimulus digest differs from frozen binding")
    except (ValueError, ShiftworkDomainError):
        repo.update_run(conn, slot.run_id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED, _now())
        repo.update_trial_slot(conn, slot.id, state="FAILED")
        conn.commit()
        return repo.get_trial_slot(conn, slot.id)

    repo.update_run(conn, slot.run_id, RunState.RUNNING)
    repo.update_trial_slot(conn, slot.id, state="RUNNING")
    repo.set_run_snapshot_bytes(conn, slot.run_id, snapshot_bytes)
    conn.commit()
    try:
        with tempfile.TemporaryDirectory(prefix=f"shiftwork-compare-{slot.pair_ordinal}-") as directory:
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
                    live_budget=live_budget,
                )
            elif run.adapter == LocalProcessAdapter.name:
                adapter = LocalProcessAdapter()
            else:
                raise LifecycleError("conflict", "reserved comparison slot has no safe executor")
            public_result = asyncio.run(adapter.execute(request))
        public_complete = (
            public_result.failure is None
            and len(public_result.captures) == workload.request_count
            and {capture.request_ordinal for capture in public_result.captures}
                == set(range(1, workload.request_count + 1))
            and all(capture.transport_error is None and capture.body for capture in public_result.captures)
        )
        protected_result = None
        if public_complete and repo.get_exposure_reservation(conn, reservation.id).state == "ACTIVE":
            with tempfile.TemporaryDirectory(prefix=f"shiftwork-protected-{slot.pair_ordinal}-") as directory:
                protected_path = Path(directory) / "protected_state.json"
                protected_path.write_bytes(protected_state_bytes)
                protected_request = request.model_copy(update={
                    "shop_snapshot_ref": str(protected_path),
                    "request_batch": protected_ref,
                    "request_batch_bytes": protected_line,
                    "single_request_ordinal": slot.executed_request_count,
                })
                protected_result = asyncio.run(adapter.execute(protected_request))
        captures = list(public_result.captures)
        observations = list(public_result.observations)
        if protected_result is not None:
            for capture in protected_result.captures:
                captures.append(capture.model_copy(update={
                    "request_ordinal": slot.executed_request_count,
                }))
            for observation in protected_result.observations:
                observations.append(observation.model_copy(update={
                    "public_payload": {**observation.public_payload,
                                       "request_ordinal": slot.executed_request_count},
                }))

        for ordinal, observation in enumerate(observations, start=1):
            request_ordinal = observation.public_payload.get("request_ordinal", 1)
            if type(request_ordinal) is not int or not 1 <= request_ordinal <= slot.executed_request_count:
                raise ValueError("comparison observation ordinal is outside its frozen workload")
            raw = json.dumps(observation.raw_payload, sort_keys=True, default=str).encode("utf-8")
            repo.insert_observation(conn, ExecutionObservation(
                id=f"{run.id}-obs-{ordinal}", run_id=run.id, request_ordinal=request_ordinal,
                ordinal=ordinal, kind=ObservationKind(observation.kind),
                public_payload_json=observation.public_payload,
                raw_payload_ref="data:application/json;base64," + base64.b64encode(raw).decode("ascii"),
                measured_at=_now(),
            ))

        outputs = []
        if captures:
            batch = {entry.ordinal: entry for entry in executor.load_batch(request.request_batch, request.request_batch_bytes)}
            batch[protected_stimulus.ordinal] = protected_stimulus
            for output in executor.normalize_captures(captures, request.deadline_s):
                output = output.model_copy(update={
                    "id": f"{run.id}-out-{output.request_ordinal}",
                    "run_id": run.id,
                    "request_text": batch[output.request_ordinal].text,
                })
                repo.insert_output(conn, output)
                outputs.append(output)
        conn.commit()

        captured = {output.request_ordinal: output for output in outputs}
        completed = 0
        mandatory_pass = True
        for index, spec in enumerate(specs, start=1):
            output = captured.get(index)
            response = None
            if output is not None and output.transport_error is None:
                try:
                    response = task_contract.validate_response_envelope(spec, output.body)
                except TaskEnvelopeInvalid:
                    response = None
            request_assessments = evaluator.assess_request(
                spec=spec, request_ordinal=index, mission=mission, snapshot=snapshot, response=response,
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
        # The protected request is assessed only by the controller, against the
        # exact reserved task spec and resolved state. Public projections filter
        # every assessment above the frozen public ordinal bound.
        protected_spec = reserved_case.case.stimulus.task_spec
        protected_output = captured.get(slot.executed_request_count)
        protected_response = None
        if protected_output is not None and protected_output.transport_error is None:
            try:
                protected_response = task_contract.validate_response_envelope(
                    protected_spec, protected_output.body
                )
            except TaskEnvelopeInvalid:
                pass
        protected_assessments = evaluator.assess_request(
            spec=protected_spec, request_ordinal=slot.executed_request_count,
            mission=mission,
            snapshot=task_contract.load_public_state_bytes(protected_state_bytes),
            response=protected_response,
        )
        for assessment in protected_assessments:
            repo.insert_task_assessment(
                conn, assessment_id=f"{run.id}-protected-{assessment.task_id}",
                run_id=run.id, assessment=assessment, assessed_at=_now(),
            )
        repo.insert_run_assessment(
            conn,
            RunAssessment(
                run_id=run.id,
                context_hash=context.content_hash,
                complete_request_count=completed,
                expected_request_count=len(specs),
                mandatory_pass=mandatory_pass,
                rule_version=COMPARE_EVALUATOR_VERSION,
                assessed_at=_now(),
            ),
        )
        capture_complete = (
            len(outputs) == slot.executed_request_count
            and {output.request_ordinal for output in outputs} == set(range(1, slot.executed_request_count + 1))
            and all(output.transport_error is None and output.body for output in outputs)
        )
        retired = repo.get_exposure_reservation(conn, reservation.id).state != "ACTIVE"
        failure = (ExecutorFailure.INTERNAL if retired else public_result.failure
                   or (protected_result.failure if protected_result else None)
                   or (None if capture_complete else ExecutorFailure.CAPTURE_TRUNCATED))
        _terminalize_comparison_slot(conn, slot, "FAILED" if failure else "COMPLETE", failure)
        conn.commit()
    except Exception:
        conn.rollback()
        repo.update_run(conn, slot.run_id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
        repo.update_trial_slot(conn, slot.id, state="FAILED")
        conn.commit()
        raise
    return repo.get_trial_slot(conn, slot.id)


def execute_comparison(conn: sqlite3.Connection, experiment_id: str,
                       live_budget: LiveComparisonBudget | None = None) -> Experiment:
    """Execute every reserved slot of one comparison in its precommitted order.

    A slot that already terminated (for example before a restart) is reconciled
    from its run and never re-executed: a failed slot keeps its exposure and its
    missing evidence, and there is no automatic retry or refund. The experiment
    finalizes only when all six slots completed; any failure leaves it FAILED
    with every slot's state visible.
    """
    experiment = repo.get_experiment(conn, experiment_id)
    if experiment is None:
        raise LifecycleError("not_found", f"unknown experiment: {experiment_id}")
    if experiment.kind not in (
        ExperimentKind.QUALIFYING_COMPARISON, ExperimentKind.LATER_CONDITION_COMPARISON
    ):
        raise LifecycleError("conflict", "only a comparison is executed by this path")
    if live_budget is not None:
        slots = repo.list_trial_slots(conn, experiment.id)
        runs = [repo.get_run(conn, slot.run_id) if slot.run_id else None for slot in slots]
        contexts = [repo.get_execution_context(conn, run.context_id)
                    if run and run.context_id else None for run in runs]
        if (len(slots) != 6 or any(slot.state != "RESERVED" for slot in slots)
                or sorted((slot.pair_ordinal, slot.candidate_label) for slot in slots)
                    != [(pair, label) for pair in (1, 2, 3) for label in ("A", "B")]
                or any(slot.request_count != 2 or slot.executed_request_count != 3 for slot in slots)
                or any(run is None or run.adapter != TokenFactoryAdapter.name for run in runs)
                or any(context is None for context in contexts)
                or len({context.content_hash for context in contexts}) != 1):
            raise ValueError("live comparison reservation does not have six fresh bound slots")
        live_budget.preflight(model=contexts[0].service_model or config.SERVICE_MODEL,
                              slots=len(slots), requests=sum(slot.executed_request_count for slot in slots))
    if not repo.claim_comparison_execution(conn, experiment.id):
        conn.rollback()
        return repo.get_experiment(conn, experiment.id)
    conn.commit()
    active_slot_id: str | None = None
    try:
        for slot in repo.list_trial_slots(conn, experiment.id):
            if repo.get_experiment(conn, experiment.id).state == "INVALIDATED":
                return repo.get_experiment(conn, experiment.id)
            run = repo.get_run(conn, slot.run_id) if slot.run_id else None
            if slot.state == "COMPLETE":
                outputs = repo.list_outputs(conn, run.id) if run else []
                if (run is None or len(outputs) != slot.executed_request_count
                        or {output.request_ordinal for output in outputs} != set(range(1, slot.executed_request_count + 1))
                        or any(output.transport_error is not None or not output.body for output in outputs)):
                    if run is not None:
                        repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.CAPTURE_TRUNCATED, _now())
                    repo.update_trial_slot(conn, slot.id, state="FAILED")
                    conn.commit()
                continue
            if slot.state != "RESERVED":
                continue
            if run is not None and run.state in (RunState.FINALIZED, RunState.FAILED):
                outputs = repo.list_outputs(conn, run.id)
                complete = (
                    run.state is RunState.FINALIZED
                    and len(outputs) == slot.executed_request_count
                    and {output.request_ordinal for output in outputs} == set(range(1, slot.executed_request_count + 1))
                    and all(output.transport_error is None and output.body for output in outputs)
                )
                if not complete and run.state is RunState.FINALIZED:
                    repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.CAPTURE_TRUNCATED, _now())
                repo.update_trial_slot(
                    conn, slot.id, state="COMPLETE" if complete else "FAILED"
                )
                conn.commit()
                continue
            active_slot_id = slot.id
            if live_budget is None:
                execute_comparison_slot(conn, slot)
            else:
                execute_comparison_slot(conn, slot, live_budget)
            active_slot_id = None
        slots = repo.list_trial_slots(conn, experiment.id)
        if repo.get_experiment(conn, experiment.id).state == "INVALIDATED":
            return repo.get_experiment(conn, experiment.id)
        final = "FINALIZED" if slots and all(slot.state == "COMPLETE" for slot in slots) else "FAILED"
        repo.update_experiment_state(conn, experiment.id, final)
        conn.commit()
        return repo.get_experiment(conn, experiment.id)
    except Exception:
        conn.rollback()
        if active_slot_id is not None:
            # A provisioning or persistence error can happen before the slot's
            # inner try block. The worker touched this slot, so it must not
            # remain visually RESERVED after the comparison has failed.
            active = repo.get_trial_slot(conn, active_slot_id)
            if active is not None and active.state not in ("COMPLETE", "FAILED"):
                run = repo.get_run(conn, active.run_id) if active.run_id else None
                if run is not None and run.state not in (RunState.FINALIZED, RunState.FAILED):
                    repo.update_run(conn, run.id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
                repo.update_trial_slot(conn, active.id, state="FAILED")
        if repo.get_experiment(conn, experiment.id).state != "INVALIDATED":
            repo.update_experiment_state(conn, experiment.id, "FAILED")
        conn.commit()
        raise


def execute_comparison_task(db_path: str, experiment_id: str,
                            live_budget: LiveComparisonBudget | None = None) -> None:
    conn = db.connect(db_path)
    try:
        execute_comparison(conn, experiment_id, live_budget)
    finally:
        conn.close()


def comparison_run(conn: sqlite3.Connection, experiment_id: str) -> Run | None:
    """The first slot run of a reserved comparison, or None before it was created."""
    slots = repo.list_trial_slots(conn, experiment_id)
    if not slots or slots[0].run_id is None:
        return None
    return repo.get_run(conn, slots[0].run_id)


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
    """The public experiment projection, dispatched by experiment kind."""
    experiment = repo.get_experiment(conn, experiment_id)
    if experiment is None:
        raise LifecycleError("not_found", f"unknown experiment: {experiment_id}")
    if experiment.kind in (
        ExperimentKind.QUALIFYING_COMPARISON, ExperimentKind.LATER_CONDITION_COMPARISON
    ):
        return comparison_view(conn, experiment)
    return _diagnostic_experiment_view(conn, experiment)


def _slot_evidence(
    conn: sqlite3.Connection, run: Run | None, public_count: int
) -> dict[str, Any]:
    """One slot's stored evidence: assessments, exact outputs and missingness."""
    assessments: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    missing_evidence: list[str] = []
    if run is None:
        missing_evidence.append("the reserved comparison run has not been created")
        return {
            "task_assessments": assessments, "observations": observations,
            "outputs": outputs, "missing_evidence": missing_evidence,
        }
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
        if assessment.request_ordinal <= public_count
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
        if output.request_ordinal <= public_count
    ]
    observations = [
        {"kind": observation.kind.value, "public_payload_json": observation.public_payload_json}
        for observation in repo.list_observations(conn, run.id)
        if observation.request_ordinal <= public_count
    ]
    if run.failure_kind is not None:
        missing_evidence.append(f"execution failure: {run.failure_kind.value}")
    if run.state in (RunState.QUEUED, RunState.RUNNING):
        missing_evidence.append("the reserved comparison run has not finished")
    elif not outputs:
        missing_evidence.append("no capture was produced for the frozen workload")
    else:
        slot = repo.get_trial_slot_for_run(conn, run.id)
        if slot is not None and len(outputs) < slot.request_count:
            missing_evidence.append("the frozen workload has requests with no captured output")
    return {
        "task_assessments": assessments,
        "observations": observations,
        "outputs": outputs,
        "missing_evidence": missing_evidence,
    }


def _comparison_outcome(
    conn: sqlite3.Connection, experiment: Experiment, context: ExecutionContext,
    slots: list[TrialSlot],
) -> comparison.ComparisonOutcome:
    """Read frozen evidence for the pure comparison without projecting private rows."""
    drift: set[str] = set()
    public_bytes = None
    try:
        mission_bytes = base64.b64decode(context.mission_bytes_base64, validate=True)
        public_bytes = base64.b64decode(context.public_data_bytes_base64, validate=True)
        if (_hash_bytes(mission_bytes) != context.mission_hash
                or context.requirement_set_hash != context.mission_hash):
            drift.add("mission_bytes_hash")
        if _hash_bytes(public_bytes) != context.public_data_hash:
            drift.add("public_data_bytes_hash")
        mission = task_contract.load_mission_bytes(mission_bytes)
        public_snapshot = task_contract.load_public_state_bytes(public_bytes)
    except (ValueError, ShiftworkDomainError):
        mission = None
        public_snapshot = None
        drift.add("mission_bytes_hash")
    if canonical.content_hash(context.starting_business_state_json) != context.starting_business_state_hash:
        drift.add("starting_business_state")
    try:
        condition_bytes = base64.b64decode(context.condition.exact_bytes_base64, validate=True)
    except ValueError:
        condition_bytes = b""
    if (context.condition.content_hash != _hash_bytes(condition_bytes)
            or context.condition.content_hash != context.public_data_hash
            or (public_bytes is not None and condition_bytes != public_bytes)):
        drift.add("condition")
    specs_by_workload: dict[str, tuple[task_contract.CustomerRequestSpec, ...]] = {}
    for workload in context.workloads:
        try:
            batch_bytes = base64.b64decode(workload.request_batch_bytes_base64, validate=True)
            spec_bytes = base64.b64decode(workload.request_specs_bytes_base64, validate=True)
            specs = tuple(task_contract.CustomerRequestSpec.model_validate(item)
                          for item in json.loads(spec_bytes))
            if (canonical.content_hash(_encode(batch_bytes)) != workload.request_batch_hash
                    or _hash_bytes(_canonical_specs_bytes(specs)) != workload.request_specs_hash
                    or len(specs) != workload.request_count):
                drift.add(f"workload_{workload.ordinal}")
            specs_by_workload[workload.id] = specs
        except (ValueError, TypeError, ShiftworkDomainError):
            drift.add(f"workload_{workload.ordinal}")
            specs_by_workload[workload.id] = ()
    if canonical.content_hash([
        {"ordinal": item.ordinal, "task_specs_hash": item.request_specs_hash}
        for item in context.workloads
    ]) != context.visible_check_set_hash:
        drift.add("visible_check_set")
    reservation = repo.get_exposure_reservation_for_experiment(conn, experiment.id)
    reserved_cases = ()
    bindings = ()
    if reservation is None or reservation.id != context.protected_reservation_id:
        drift.add("exposure_reservation")
    else:
        if (reservation.state != "ACTIVE" or any(
            item.state.value != "active" for item in repo.list_exposure_items(conn, reservation.id)
        )):
            drift.add("exposure_reservation")
        try:
            reserved_cases = sealed_store.load_reserved_comparison_cases(conn, reservation.id)
            bindings = _reserved_protected_bindings(conn, reservation.id)
        except ShiftworkDomainError:
            drift.add("protected_binding")
    if len(bindings) != COMPARISON_PAIRS:
        drift.add("protected_binding")
    elif _frozen_comparison_context_hash(context, bindings) != context.content_hash:
        drift.add("frozen_context")
    schedule = [
        {"pair_ordinal": slot.pair_ordinal, "candidate_label": slot.candidate_label,
         "execution_ordinal": slot.execution_ordinal}
        for slot in slots
    ]
    if canonical.content_hash({
        "shift_id": experiment.shift_id, "kind": experiment.kind.value,
        "candidates": [item.model_dump(mode="json") for item in experiment.candidates],
        "context_hash": context.content_hash,
        "trial_count_per_candidate": experiment.trial_count_per_candidate,
        "declared_treatment": experiment.declared_treatment,
        "schedule": schedule,
    }) != experiment.content_hash:
        drift.add("experiment_schedule")
    for candidate in experiment.candidates:
        try:
            version = repo.get_version(conn, candidate.artifact_version_id)
        except ShiftworkDomainError:
            version = None
        if version is None or version.content_hash != candidate.artifact_content_hash:
            drift.add(f"candidate_{candidate.label}")
    by_pair = {item.pair_ordinal: item for item in reserved_cases}
    readings = []
    for slot in slots:
        run = repo.get_run(conn, slot.run_id) if slot.run_id else None
        if (run is None or run.context_id != context.id or run.artifact_version_id != slot.artifact_version_id
                or run.trial_slot_id != slot.id or run.experiment_id != experiment.id):
            drift.add("run_binding")
        all_assessments = tuple(repo.list_task_assessment_models(conn, run.id)) if run else ()
        outputs = tuple(repo.list_outputs(conn, run.id)) if run else ()
        protected_pass = None
        rule_ids: tuple[str, ...] = ()
        reserved = by_pair.get(slot.pair_ordinal)
        if reserved is None:
            drift.add("protected_binding")
        else:
            rule_ids = tuple(rule for rule in reserved.case.expected.get("rule_ids", [])
                             if type(rule) is str and mission is not None and rule in mission.public_rules)
            if not rule_ids:
                drift.add("protected_rule")
            protected_output = next((item for item in outputs
                                     if item.request_ordinal == slot.executed_request_count), None)
            if (protected_output is not None and protected_output.transport_error is None
                    and bool(protected_output.body)):
                protected_assessments = tuple(item for item in all_assessments
                                              if item.request_ordinal == slot.executed_request_count)
                if protected_assessments:
                    protected_pass = comparison.protected_acceptance(
                        reserved.case, protected_assessments
                    )
        assessment = repo.get_run_assessment(conn, run.id) if run else None
        if assessment is not None and assessment.context_hash != context.content_hash:
            drift.add("assessment_context")
        if assessment is not None and mission is not None and public_snapshot is not None:
            expected_public = []
            expected_completed = 0
            for ordinal, spec in enumerate(specs_by_workload.get(slot.workload_id, ()), 1):
                output = next((item for item in outputs if item.request_ordinal == ordinal), None)
                response = None
                if output is not None and output.transport_error is None:
                    try:
                        response = task_contract.validate_response_envelope(spec, output.body)
                    except TaskEnvelopeInvalid:
                        pass
                assessed = evaluator.assess_request(
                    spec=spec, request_ordinal=ordinal, mission=mission,
                    snapshot=public_snapshot, response=response,
                )
                expected_public.extend(assessed)
                expected_completed += evaluator.request_usefully_completed(spec, assessed)
            recorded_public = tuple(item for item in all_assessments
                                    if item.request_ordinal <= slot.request_count)
            if (tuple(expected_public) != recorded_public
                    or assessment.complete_request_count != expected_completed
                    or assessment.mandatory_pass != all(item.mandatory_pass
                                                         for item in expected_public)):
                drift.add("public_assessment")
        if reserved is not None and mission is not None and run is not None:
            protected_assessments = tuple(item for item in all_assessments
                                          if item.request_ordinal == slot.executed_request_count)
            if protected_assessments:
                try:
                    protected_state = task_contract.load_public_state_bytes(reserved.resolved_state_bytes)
                    protected_spec = reserved.case.stimulus.task_spec
                    protected_output = next((item for item in outputs
                                             if item.request_ordinal == slot.executed_request_count), None)
                    protected_response = None
                    if protected_output is not None and protected_output.transport_error is None:
                        try:
                            protected_response = task_contract.validate_response_envelope(
                                protected_spec, protected_output.body
                            )
                        except TaskEnvelopeInvalid:
                            pass
                    expected_protected = evaluator.assess_request(
                        spec=protected_spec, request_ordinal=slot.executed_request_count,
                        mission=mission, snapshot=protected_state, response=protected_response,
                    )
                    if expected_protected != protected_assessments:
                        drift.add("protected_assessment")
                except ShiftworkDomainError:
                    drift.add("protected_assessment")
        readings.append(comparison.TrialReading(
            slot=slot, run=run, assessment=assessment,
            public_specs=specs_by_workload.get(slot.workload_id, ()),
            task_assessments=all_assessments, outputs=outputs,
            observations=tuple(repo.list_observations(conn, run.id)) if run else (),
            protected_pass=protected_pass, protected_rule_ids=rule_ids,
        ))
    return comparison.compare(experiment, context, tuple(readings), tuple(drift))


def comparison_view(conn: sqlite3.Connection, experiment: Experiment) -> dict[str, Any]:
    """The Compare station projection for one qualifying comparison.

    Every one of the six ordered slots is listed with its pair, candidate label,
    exact version, frozen workload identity, batch request count, run identity,
    state and missing evidence. Before a slot runs, its workload appears only as
    a safe summary (id, ordinal, hash, count): no future request bytes and no
    protected pair refs are projected. Terminal outcomes expose aggregate metrics
    and eligibility only; they derive no winner or ranking (Gate 3 S3.7, S16).
    """
    context = repo.get_execution_context(conn, experiment.context_id)
    if context is None:
        raise LifecycleError("not_found", f"unknown context: {experiment.context_id}")
    candidates = {candidate.label: candidate for candidate in experiment.candidates}
    slots = repo.list_trial_slots(conn, experiment.id)
    trials = []
    for slot in slots:
        run = repo.get_run(conn, slot.run_id) if slot.run_id else None
        evidence = _slot_evidence(conn, run, slot.request_count)
        trials.append({
            "pair_ordinal": slot.pair_ordinal,
            "execution_ordinal": slot.execution_ordinal,
            "candidate_label": slot.candidate_label,
            "artifact_version_id": slot.artifact_version_id,
            "artifact_content_hash": (
                candidates[slot.candidate_label].artifact_content_hash
                if slot.candidate_label in candidates else ""
            ),
            "workload_id": slot.workload_id,
            "workload_ordinal": slot.pair_ordinal,
            "request_batch_hash": slot.request_batch_hash,
            "request_count": slot.request_count,
            "protected_request_count": slot.executed_request_count - slot.request_count,
            "run_id": slot.run_id,
            "state": slot.state,
            "evidence_mode": run.evidence_mode.value if run and run.evidence_mode else None,
            **evidence,
            "metrics": None,
        })
    protected_counts = None
    outcome = None
    if experiment.state in ("FINALIZED", "FAILED", "INVALIDATED"):
        outcome = _comparison_outcome(conn, experiment, context, slots)
        protected_counts = {
            label: {"reserved": item.protected_denominator,
                    "captured": item.protected_passed + item.protected_failed,
                    "missing": item.protected_missing}
            for label, item in zip(("A", "B"), outcome.candidate_metrics, strict=True)
        }
    payload = {
        "id": experiment.id,
        "shift_id": experiment.shift_id,
        "kind": experiment.kind.value,
        "investigation_id": experiment.investigation_id,
        "declared_treatment": experiment.declared_treatment,
        "context_hash": context.content_hash,
        "context_evidence_class": context.executor_class.value,
        "condition": {
            "id": context.condition.id,
            "kind": context.condition.kind,
            "public_label": context.condition.public_label,
            "content_hash": context.condition.content_hash,
        },
        "observed_run_id": experiment.observed_run_id,
        "workloads": [
            {
                "id": workload.id,
                "ordinal": workload.ordinal,
                "request_batch_hash": workload.request_batch_hash,
                "request_count": workload.request_count,
            }
            for workload in context.workloads
        ],
        "candidates": [
            {
                "label": candidate.label,
                "artifact_version_id": candidate.artifact_version_id,
                "artifact_content_hash": candidate.artifact_content_hash,
            }
            for candidate in experiment.candidates
        ],
        "trials": trials,
        "shared_public_denominator_requests": sum(item.request_count for item in context.workloads),
        "protected_denominator_requests_per_candidate": len(context.workloads),
        "protected_counts": protected_counts,
        "outcome": outcome.model_dump(mode="json") if outcome else None,
        "eligible": bool(outcome and any(item.eligible for item in outcome.eligibility)),
        "eligibility_reason": (
            "No winner is derived here. Candidate eligibility requires a complete "
            "comparable outcome, and selection is a separate learner action."
        ),
        "state": experiment.state,
    }
    try:
        assert_public_safe(payload, _private_public_needles(conn))
    except ValueError as exc:
        raise LifecycleError("conflict", "public comparison evidence contains private material") from exc
    return payload


def _diagnostic_experiment_view(conn: sqlite3.Connection, experiment: Experiment) -> dict[str, Any]:
    """The public diagnostic projection.

    It carries the frozen workload identity, the candidate, the trial's public
    assessments and the exact output the learner's own service produced. Raw
    observation payload refs, sealed identities, host paths and the protected
    reservation never appear, and eligibility stays false: a public diagnostic
    cannot qualify a version (Gate 3 S3.7, test 21).
    """
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
        assert_public_safe(payload, _private_public_needles(conn))
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
    # The diagnostic panel reads this field only. A comparison carries candidate
    # eligibility, which a diagnostic can never assert, so it is never projected
    # here even when it is the shift's latest experiment.
    diagnostics = [item for item in experiments if item.kind is ExperimentKind.DIAGNOSTIC]
    view["latest_diagnostic"] = (
        experiment_view(conn, diagnostics[-1].id) if diagnostics else None
    )
    try:
        assert_public_safe(view, _private_public_needles(conn))
    except ValueError as exc:
        raise LifecycleError("conflict", "public investigation evidence contains private material") from exc
    return view


def investigation_entry(conn: sqlite3.Connection, investigation_id: str) -> Investigation:
    investigation = repo.get_investigation(conn, investigation_id)
    if investigation is None:
        raise LifecycleError("not_found", f"unknown investigation: {investigation_id}")
    return investigation
