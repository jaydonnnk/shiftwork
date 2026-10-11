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
    RetainedRecordUnreadable,
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
from shiftwork.packs import registry as pack_registry
from shiftwork.sealed import rotation
from shiftwork.sealed import store as sealed_store
from shiftwork.store import db, repo


class LifecycleError(Exception):
    """Typed lifecycle failure. ``kind`` is "not_found" or "conflict"."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


def _verify_pack_material(pack: pack_registry.EngagementPack) -> frozenset[str]:
    """Verify all reviewed bytes and required seals without writes or exposure."""
    pins = {pin.path: pin.sha256 for pin in pack.reviewed_pins}
    if not set(pack.required_paths()).issubset(pins):
        raise pack_registry.PackUnavailable("engagement material awaits operator review")
    for document in pack.documents:
        if pins.get(document.path) != document.sha256:
            raise pack_registry.PackUnavailable("document pin disagrees with the reviewed content pin")
    for name, digest in pins.items():
        path = config.PACKAGE_DIR / name
        # Declarations cannot traverse a symlink or otherwise leave the package.
        if not path.resolve().is_relative_to(config.PACKAGE_DIR.resolve()):
            raise pack_registry.PackUnavailable("content path leaves the package")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise pack_registry.PackUnavailable("reviewed content pin mismatch")
    mission = task_contract.load_mission(config.PACKAGE_DIR / pack.mission_path)
    if mission.engagement_slug != pack.slug:
        raise pack_registry.PackUnavailable("mission belongs to another engagement")
    catalog_name = f"fixtures/catalogs/{pack.slug}_v{mission.contract_catalog_version}.json"
    if catalog_name not in pins:
        raise pack_registry.PackUnavailable("compatible catalog lacks its reviewed pin")
    catalog = contract_catalog.load_catalog(pack.slug, mission.contract_catalog_version)
    if catalog.content_hash != mission.contract_catalog_hash:
        raise pack_registry.PackUnavailable("mission catalog binding mismatch")
    for state_path in (pack.public_state_path, pack.comparison_state_path):
        state = task_contract.load_public_state(config.PACKAGE_DIR / state_path)
        if state.engagement_slug != pack.slug:
            raise pack_registry.PackUnavailable("public state belongs to another engagement")
    incident_bytes = (config.PACKAGE_DIR / pack.incident_request_path).read_bytes()
    incident_rows = executor.load_batch(executor.BatchRef(path_ref=pack.incident_request_path,
        content_hash=canonical.content_hash(_encode(incident_bytes))), incident_bytes)
    if len(incident_rows) != len(mission.request_specs) or any(
            json.loads(row.body).get("request_id") != spec.id or row.text != spec.text
            or json.loads(row.body).get("entity_ref") not in spec.requested_entities
            for row, spec in zip(incident_rows, mission.request_specs, strict=True)):
        raise pack_registry.PackUnavailable("incident request disagrees with its owning mission")
    manifest = json.loads((config.PACKAGE_DIR / pack.manifest_path).read_bytes())
    payload = manifest.get("workloads")
    sealed_digest = hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    if (manifest.get("review_status") != "OPERATOR_SEALED"
            or manifest.get("sealed_payload_sha256") != sealed_digest):
        raise pack_registry.PackUnavailable("comparison manifest awaits operator review and sealing")
    if (manifest.get("engagement_slug") != pack.slug or manifest.get("schema_version") != 1
            or manifest.get("comparison_state_sha256") != pins[pack.comparison_state_path]):
        raise pack_registry.PackUnavailable("comparison manifest binding mismatch")
    if not isinstance(payload, list) or [entry.get("ordinal") for entry in payload] != [1, 2, 3]:
        raise pack_registry.PackUnavailable("comparison manifest needs ordinals 1, 2 and 3")
    request_dir = Path(pack.manifest_path).parent
    for entry in payload:
        for field in ("request_file", "task_spec_file"):
            name = entry[field]
            if not isinstance(name, str) or Path(name).name != name or "\\" in name:
                raise pack_registry.PackUnavailable("comparison manifest contains an invalid path")
            if (request_dir / name).as_posix() not in pins:
                raise pack_registry.PackUnavailable("comparison workload lacks its reviewed pin")
    refs: set[str] = set()
    for declaration in pack.families:
        loaded = sealed_store.load_declared_family(declaration, slug=pack.slug)
        if pack.slug == "gtm" and any(case.stimulus is None or
                {task.kind for task in case.stimulus.task_spec.tasks} != evaluator.PIPELINE_TASK_KINDS
                for case in loaded.cases):
            raise pack_registry.PackUnavailable("GTM family must assess the pipeline contract")
        family_refs = {rotation.variant_ref(case) for case in loaded.cases}
        if refs & family_refs:
            raise pack_registry.PackUnavailable("declared families share variant refs")
        refs.update(family_refs)
    return frozenset(refs)


def admit_pack(slug: str) -> pack_registry.EngagementPack:
    """Resolve operator declarations and fail closed on any required material.

    Unreviewed declarations remain unavailable. A collision with another
    declared, readable sealed family refuses admission in either display order.
    """
    pack = pack_registry.resolve_pack(slug)
    try:
        refs = _verify_pack_material(pack)
    except (OSError, ValueError, KeyError, TypeError, ShiftworkDomainError) as exc:
        raise pack_registry.PackUnavailable("engagement material is unavailable") from exc
    for other in pack_registry.registered_packs():
        if other.slug == slug:
            continue
        other = pack_registry.resolve_pack(other.slug)
        for declaration in other.families:
            try:
                loaded = sealed_store.load_declared_family(declaration, slug=other.slug)
            except (OSError, ValueError, KeyError, TypeError, ShiftworkDomainError):
                continue
            if refs & {rotation.variant_ref(case) for case in loaded.cases}:
                raise pack_registry.PackUnavailable("registered packs share variant refs")
    return pack


def workplace_boards() -> tuple[pack_registry.BoardAvailability, ...]:
    """Safe declaration-only display plus whole-pack material availability."""
    boards = []
    for declaration in pack_registry.registered_packs():
        try:
            pack = pack_registry.resolve_pack(declaration.slug)
        except (ValueError, ShiftworkDomainError):
            continue
        try:
            admit_pack(pack.slug)
            status = "AVAILABLE"
        except pack_registry.PackUnavailable:
            status = "AWAITING_OPERATOR_REVIEW"
        boards.append(pack_registry.BoardAvailability(
            engagement_slug=pack.slug, display=pack.display, availability=status,
        ))
    return tuple(boards)


def seed_registered_engagements(conn: sqlite3.Connection) -> None:
    """Seed admitted declarations only; preserve every existing row and shift."""
    for declaration in pack_registry.registered_packs():
        try:
            pack = admit_pack(declaration.slug)
        except pack_registry.PackUnavailable:
            continue
        repo.seed_engagement(conn, pack.slug, pack.slug,
                             pack.display.client or pack.display.employer)
        repo.seed_engagement_config(
            conn, pack.slug,
            business_kind=pack.slug,
            assist_level=pack.assist.level_label,
            allowed_assist_roles=tuple(role.value for role in pack.assist.allowed_roles),
            total_assist_budget_per_shift=pack.assist.total_calls_per_shift,
            enabled_check_families=tuple(f.family for f in pack.families
                                       if f.family_class is pack_registry.FamilyClass.ATTEMPT),
            attempt_limit=config.DEFAULT_ATTEMPT_LIMIT,
            rotation_group_size=min(f.min_variants for f in pack.families),
        )
        repo.seed_engagement_assist_policy(
            conn, pack.slug,
            assist_level=pack.assist.level_label,
            allowed_assist_roles=tuple(role.value for role in pack.assist.allowed_roles),
            total_assist_budget_per_shift=pack.assist.total_calls_per_shift,
        )


def verified_assist_policy(conn: sqlite3.Connection, slug: str) -> pack_registry.AssistPolicy:
    """Verify the current projection without reading historical assistance columns."""
    policy = pack_registry.resolve_pack(slug).assist
    row = repo.get_engagement_assist_policy(conn, slug)
    try:
        matches = (row is not None
                   and row["assist_level"] == policy.level_label
                   and json.loads(row["allowed_assist_roles_json"]) == [role.value for role in policy.allowed_roles]
                   and row["total_assist_budget_per_shift"] == policy.total_calls_per_shift)
    except (ValueError, TypeError):
        matches = False
    if not matches:
        raise LifecycleError("conflict", "assist policy projection disagrees with the registered declaration")
    return policy


def verify_assist_policy_projections(conn: sqlite3.Connection) -> None:
    """Fail startup closed on edited projections without rewriting their rows."""
    for row in conn.execute("SELECT slug FROM engagements"):
        verified_assist_policy(conn, row["slug"])


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
        from shiftwork.comparison_flow import _comparison_outcome
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
        pack = admit_pack(shift.engagement_slug)
        if _hash_bytes((config.PACKAGE_DIR / pack.mission_path).read_bytes()) != context.requirement_set_hash:
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
    return tuple(f.family for f in pack_registry.resolve_pack(slug).families
                 if f.family_class is pack_registry.FamilyClass.ATTEMPT)


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
            if slug not in (config.BOOKSHOP_SLUG, "northline", "gtm"):
                raise LifecycleError("conflict", "reviewed initial starter is unavailable")
            # Slice 11 supplies the reviewed, executable failing starter as the new
            # engagement's editable draft, so the first shift's public diagnostic can
            # run exactly the artifact the learner can read and edit. The pins in
            # config.TRUSTED_LOCAL_FIXTURES are what makes it executable offline.
            files = {
                name: path.read_text(encoding="utf-8")
                for name, path in sorted(config.PIVOT_STARTER_ARTIFACT_PATHS.items())
            } if slug == config.BOOKSHOP_SLUG else {}
            contract = ContractParams.model_validate(config.PIVOT_STARTER_CONTRACT_JSON)
            if slug == "gtm":
                pack = admit_pack(slug)
                files = {"service.py": (config.PACKAGE_DIR / "fixtures/artifacts/gtm/pipeline_starter_failure.py").read_text(encoding="utf-8")}
                contract = ContractParams.model_validate(config.GTM_STARTER_CONTRACT_JSON)
            if slug == "northline":
                pack = admit_pack(slug)
                files = {"service.py": (config.PACKAGE_DIR / "templates/artifact/northline_blank_service.py").read_text(encoding="utf-8"),
                         **{name: (config.PACKAGE_DIR / "templates/artifact/northline" / name).read_text(encoding="utf-8")
                            for name in ("discovery.md", "permissions.json", "acceptance_tests.py", "runbook.md")}}
                contract = ContractParams.model_validate({
                    "catalog_version": 1, "must_never": ["NEVER_UNSAFE_CONTINUATION"],
                    "selections": {"ESCALATE_WHEN": "ESCALATE_UNSAFE_REPAIR",
                                   "REPEAT_REQUEST_RULE": "DEDUPLICATE_BOOKING_BY_REQUEST_ID"},
                    "response_time_limit_ms": 3000,
                    "declared_limits": ["Fictional deployment; no real booking or customer access."],
                })
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
                    rationale=("Reviewed blank Northline starter; required tasks are deliberately missing."
                               if slug == "northline" else "Reviewed failing Stonebridge starter; wrong owner, not an eligible repair."
                               if slug == "gtm" else "Reviewed failing Bellwether starter; executable offline, not a qualified repair or live service."),
                    requirement_set_hash=(_hash_bytes((config.PACKAGE_DIR / pack.mission_path).read_bytes())
                        if slug in ("northline", "gtm") else canonical.content_hash(
                        {
                            "catalog_hash": catalog.content_hash,
                            "contract": canonical.contract_params_json(contract),
                        }
                    )),
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

    if shift.engagement_slug == "northline":
        _validate_deployment_records(files)

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


def _validate_deployment_records(files):
    for name in ("service.py", "discovery.md", "permissions.json", "acceptance_tests.py", "runbook.md"):
        if not isinstance(files.get(name), str) or not files[name].strip():
            raise LifecycleError("conflict", f"deployment artifact requires nonempty {name}")
    try:
        permissions = json.loads(files["permissions.json"])
        if (not isinstance(permissions, dict) or set(permissions) != {"reads", "writes"}
                or any(not isinstance(permissions[key], list)
                       or any(not isinstance(item, str) for item in permissions[key])
                       for key in ("reads", "writes"))):
            raise ValueError("invalid permissions map")
    except (ValueError, TypeError) as exc:
        raise LifecycleError("conflict", "deployment permissions must contain reads and writes text lists") from exc


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
        if ((selection.kind == "LEARNER_CHOICE" and selection.comparison_id is not None)
                or (shift.engagement_slug in ("northline", "gtm") and selection.kind == "STARTER_BASELINE")):
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
            drawn[family] = rotation.select_variant(
                family, sealed_store.load_family(family, slug=shift.engagement_slug).cases, exposed)
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
                    cycle=sealed_store.family_cycle(family, slug=shift.engagement_slug),
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
    pack = admit_pack(shift.engagement_slug)
    mission_bytes = (config.PACKAGE_DIR / pack.mission_path).read_bytes()
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
            request = bind_deployment_request(request, run, context, version, mission, state_bytes)
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
        batch_bytes = base64.b64decode(workload.request_batch_bytes_base64, validate=True)
        if canonical.content_hash(_encode(batch_bytes)) != workload.request_batch_hash:
            raise LifecycleError("conflict", "captured operational batch differs")
        if (len(outputs) != workload.request_count
                or {item.request_ordinal for item in outputs}
                != set(range(1, workload.request_count + 1))
                or any(item.transport_error is not None or not item.body for item in outputs)):
            raise LifecycleError("conflict", "operational capture is incomplete")
        captured = {item.request_ordinal: item for item in outputs}
        assessed = []
        verified_traces = []
        completed = 0
        mandatory_pass = True
        for index, spec in enumerate(mission.request_specs, start=1):
            output = captured[index]
            try:
                response = task_contract.validate_response_envelope(spec, output.body)
            except TaskEnvelopeInvalid:
                response = None
            inputs = deployment_assessment_inputs(conn, run, spec, index, state_bytes, batch_bytes,
                                                  require_complete=True)
            if inputs.get("deployment_trace") is not None:
                verified_traces.append(inputs["deployment_trace"])
            rows = evaluator.assess_request(spec=spec, request_ordinal=index,
                                            mission=mission, snapshot=snapshot, response=response, **inputs)
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
        drafts = reducer.reduce_operation(run, assessment, mission, tuple(assessed), tuple(checks.values()),
            **operation_consequence_inputs(context), deployment_traces=tuple(verified_traces),
            pipeline_outputs=tuple(outputs))
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


_OPERATION_DRAFT_TYPES = (LedgerEventType.SALE_COMPLETED, LedgerEventType.INCIDENT_OPENED,
                         LedgerEventType.BOOKING_COMMITTED, LedgerEventType.ESCALATION_TO_HUMAN,
                         LedgerEventType.COUNTER_FOLLOWUP_RECORDED, LedgerEventType.ROLLOUT_APPROVED,
                         LedgerEventType.OWNER_ASSIGNED, LedgerEventType.SLA_CLOCK_STARTED,
                         LedgerEventType.HANDOFF_ESCALATED)


def operation_consequence_inputs(context: ExecutionContext) -> dict[str, Any]:
    """Resolve retained rules only; old v1 operations keep their original reduction."""
    if context.reducer_version == "operation-ledger-v1":
        return {}
    if context.reducer_version not in ("operation-ledger-v2", "operation-ledger-v3"):
        raise LifecycleError("conflict", "unknown operational reducer version")
    if canonical.content_hash(context.starting_business_state_json) != context.starting_business_state_hash:
        raise LifecycleError("conflict", "frozen operational consequence rules differ")
    try:
        rules = pack_registry.ConsequenceRules.model_validate(context.starting_business_state_json["consequence_rules"])
        weights = json.loads(base64.b64decode(context.mission_bytes_base64, validate=True))["weights"]
        if context.reducer_version == "operation-ledger-v3":
            if (context.engagement_slug != "gtm" or rules.success_events != (
                    "OWNER_ASSIGNED owner", "SLA_CLOCK_STARTED sla")
                    or rules.rollout_event is not None or rules.handover_record_required
                    or type(weights["handoff"]) is not int):
                raise ValueError("invalid pipeline consequence rules")
        for rule in (*rules.success_events, *((rules.rollout_event,) if rules.rollout_event else ())):
            event, key = rule.split()
            LedgerEventType(event)
            if type(weights[key]) is not int:
                raise ValueError("invalid consequence weight")
    except (ValueError, TypeError, KeyError) as exc:
        raise LifecycleError("conflict", "frozen operational consequence rules missing or invalid") from exc
    return {"consequence_rules": rules.model_dump(mode="json"), "weights": weights}


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
    try:
        context = repo.get_execution_context(conn, run.context_id)
        snapshot_bytes = repo.get_run_snapshot_bytes(conn, run.id)
        outputs = repo.list_outputs(conn, run.id)
        stored_checks = repo.list_check_results(conn, run.id)
        stored_drafts = (_stored_operation_drafts(conn, run, context.engagement_slug)
                         if context is not None else [])
    except RetainedRecordUnreadable:
        # A retained row that no longer deserializes is unreadable evidence:
        # report the missing-input verdict instead of a typed conflict. Only the
        # storage boundary raises it; assessment and reduction stay outside.
        return _unknown_inputs_report(run.id)
    workload = (context.workloads[0]
                if context is not None and len(context.workloads) == 1 else None)
    if (context is None or workload is None or snapshot_bytes is None
            or not outputs or run.selection_id is None):
        return _unknown_inputs_report(run.id)
    try:
        mission_bytes = base64.b64decode(context.mission_bytes_base64, validate=True)
        state_bytes = base64.b64decode(context.public_data_bytes_base64, validate=True)
        batch_bytes = base64.b64decode(workload.request_batch_bytes_base64, validate=True)
        specs_bytes = base64.b64decode(workload.request_specs_bytes_base64, validate=True)
        # Match the operational producer's identity domain, not a hash of the
        # whole retained model (which also carries DB IDs, bytes and timestamps).
        identity = context.model_dump(mode="json", exclude={
            "id", "schema_version", "mission_bytes_base64", "public_data_bytes_base64",
            "starting_business_state_json", "protected_reservation_id", "created_at", "content_hash"})
        if (canonical.content_hash(identity) != context.content_hash
                or _hash_bytes(specs_bytes) != workload.request_specs_hash
                or workload.request_specs_hash != context.visible_check_set_hash
                or context.requirement_set_hash != context.mission_hash
                or context.condition.content_hash != context.public_data_hash
                or base64.b64decode(context.condition.exact_bytes_base64, validate=True) != state_bytes
                or _hash_bytes(mission_bytes) != context.mission_hash
                or _hash_bytes(state_bytes) != context.public_data_hash
                or snapshot_bytes != state_bytes
                or canonical.content_hash(_encode(batch_bytes)) != workload.request_batch_hash):
            return _unknown_inputs_report(run.id)
        mission = task_contract.load_mission_bytes(mission_bytes)
        snapshot = task_contract.load_public_state_bytes(state_bytes)
        specs = tuple(task_contract.CustomerRequestSpec.model_validate(raw) for raw in json.loads(specs_bytes))
        if (specs != mission.request_specs or workload.request_count != len(specs)
                or workload.request_count != len([line for line in batch_bytes.splitlines() if line.strip()])
                or context.engagement_slug != mission.engagement_slug):
            return _unknown_inputs_report(run.id)
    except (ValueError, TypeError, ShiftworkDomainError):
        return _unknown_inputs_report(run.id)
    captured = {item.request_ordinal: item for item in outputs}
    # Expected evidence failures are handled before reduction. Reducer errors
    # remain programming errors; do not broadly catch ValueError around it.
    if (len(captured) != len(outputs)
            or set(captured) != set(range(1, workload.request_count + 1))
            or any(item.run_id != run.id or item.transport_error is not None for item in outputs)):
        return _unknown_inputs_report(run.id)
    stored_by_check_id = {check.check_id: check for check in stored_checks}
    assessed: list[task_contract.TaskAssessment] = []
    verified_traces = []
    recomputed: dict[str, CheckResult] = {}
    completed = 0
    mandatory_pass = True
    for index, spec in enumerate(mission.request_specs, start=1):
        output = captured[index]
        try:
            deployment_inputs = deployment_assessment_inputs(
                conn, run, spec, index, state_bytes, batch_bytes, require_complete=True)
        except LifecycleError:
            return _unknown_inputs_report(run.id)
        if deployment_inputs.get("deployment_trace") is not None:
            verified_traces.append(deployment_inputs["deployment_trace"])
        try:
            response = task_contract.validate_response_envelope(spec, output.body)
        except TaskEnvelopeInvalid:
            response = None
        rows = evaluator.assess_request(spec=spec, request_ordinal=index, mission=mission,
                                        snapshot=snapshot, response=response,
                                        **deployment_inputs)
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
    try:
        consequence_inputs = operation_consequence_inputs(context)
    except LifecycleError:
        return _unknown_inputs_report(run.id)
    drafts = reducer.reduce_operation(run, assessment, mission, tuple(assessed),
                                      tuple(recomputed.values()), **consequence_inputs,
                                      deployment_traces=tuple(verified_traces), pipeline_outputs=tuple(outputs))
    check_differences = _check_differences(stored_checks, list(recomputed.values()))
    event_draft_differences = _event_draft_differences(stored_drafts, drafts)
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
    return sealed_store.case_for_check_id(failing.check_id, slug=incident.engagement_slug)


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
            pack = admit_pack(shift.engagement_slug)
            handover_required = pack.consequences.handover_record_required
            if handover_required and not version.files.get("runbook.md", "").strip():
                raise LifecycleError("conflict", "selected runbook document required before handover")
            facts = CloseShiftFacts(
                shift_id=shift.id,
                declared_limits=tuple(version.contract.declared_limits),
                unresolved_incident_ids=tuple(
                    incident.id
                    for incident in repo.list_incidents(conn, shift.engagement_slug)
                    if incident.state is IncidentState.OPEN
                    or (handover_required and incident.state is IncidentState.CLOSED_UNRESOLVED)
                ),
                committed_contract=version.contract,
                handover_runbook_version_id=version.id if handover_required else None,
            )
            close_mission = (task_contract.load_mission_bytes((config.PACKAGE_DIR / pack.mission_path).read_bytes())
                             if handover_required else reducer.load_mission(config.BOOKSHOP_MISSION))
            drafts = reducer.reduce_close(close_mission, facts, handover_record_required=handover_required)
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
        if mission.engagement_slug == "gtm":
            assessed = customer_answer.render_assessed_task_customer_text(
                spec=spec, mission=mission, snapshot=snapshot, response=response,
                request_ordinal=output.request_ordinal,
                assessments=repo.list_task_assessment_models(conn, run.id))
            if assessed is None:
                # The request has no independent assessment yet, or its finalization
                # failed: nothing is accepted or rejected, so no derived answer is
                # presented. The raw captured bytes stay retrievable.
                evidence["customer_answer"] = None
                return evidence
            display, accepted_tasks = assessed
            evidence["customer_answer"]["claims"] = [
                {"kind": claim.kind, "value": claim.value}
                for task in response.task_results if task.task_id in accepted_tasks for claim in task.claims]
            evidence["customer_answer"]["display_text"] = display
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

    policy = verified_assist_policy(conn, shift.engagement_slug)
    admit_pack(shift.engagement_slug)
    if role not in policy.allowed_roles:
        raise LifecycleError("conflict", "this engagement does not permit that assist role")
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
        policy = verified_assist_policy(conn, shift.engagement_slug)
        limit = policy.total_calls_per_shift
        if len(events) >= limit:
            raise LifecycleError("conflict", f"assist budget exhausted ({len(events)} of {limit} used)")
        if role is AssistRole.PATCH_PROPOSAL and sum(
            event.role is AssistRole.PATCH_PROPOSAL for event in events
        ) >= policy.max_patch_proposals:
            raise LifecycleError("conflict", "patch proposal budget exhausted for this shift")
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
    try:
        admit_pack(shift.engagement_slug)
    except ShiftworkDomainError as exc:
        raise BootstrapBlocked("the reviewed initial request, mission or public state is missing") from exc
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
    policy = verified_assist_policy(conn, shift.engagement_slug)
    admit_pack(shift.engagement_slug)
    assist_limit = policy.total_calls_per_shift
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
        "assist_allowed_roles": [role.value for role in policy.allowed_roles],
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
    for pack in pack_registry.registered_packs():
        for declaration in pack.families:
            try:
                private_strings = sealed_store.load_privacy_needles(declaration.family, slug=pack.slug)
            except FileNotFoundError:
                continue
            needles.update(private_strings)
        active_paths = {declaration.case_file for declaration in pack.families}
        for pin in pack.reviewed_pins:
            if pin.path.startswith("sealed/cases/") and pin.path not in active_paths:
                needles.update(sealed_store.load_pinned_privacy_needles(pin.path, slug=pack.slug))
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
    reconstruction check intact.
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


def _verify_pipeline_history(conn: sqlite3.Connection, events) -> None:
    """Validate complete GTM consequence sets against their frozen operations.

    Chain links alone do not bind an owner, clock or handoff to a checked capture.
    Replay compares the entire per-run draft set, including omitted events and
    cause refs, using historical inputs rather than today's mission or routing.
    A retained row that no longer deserializes raises the storage boundary's
    typed conflict, so unreadable history is refused rather than a server error.
    """
    runs = {run.id: run for run in repo.list_runs(conn, "gtm")
            if run.purpose is RunPurpose.OPERATION and run.state is RunState.FINALIZED}
    relevant = (LedgerEventType.OWNER_ASSIGNED, LedgerEventType.SLA_CLOCK_STARTED,
                LedgerEventType.HANDOFF_ESCALATED)
    for event in events:
        if event.event_type in relevant:
            if len(event.cause_refs) != 3 or event.cause_refs[0] not in runs:
                raise LifecycleError("conflict", "pipeline history has unbound operational provenance")
            context = repo.get_execution_context(conn, runs[event.cause_refs[0]].context_id)
            if context is None or context.engagement_slug != "gtm" or context.reducer_version != "operation-ledger-v3":
                raise LifecycleError("conflict", "pipeline history lacks its frozen GTM operation")
    for run in runs.values():
        context = repo.get_execution_context(conn, run.context_id) if run.context_id else None
        if context is not None and context.reducer_version == "operation-ledger-v3":
            if replay_assessment(conn, run.id).status != "IDENTICAL":
                raise LifecycleError("conflict", "pipeline history consequences or captured provenance differ")


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
    pack = admit_pack(shift.engagement_slug)
    mission_path = config.PACKAGE_DIR / pack.mission_path
    state_path = config.PACKAGE_DIR / pack.public_state_path
    mission_bytes = mission_path.read_bytes()
    mission = task_contract.load_mission_bytes(mission_bytes, label=mission_path.name)
    if mission.engagement_slug != shift.engagement_slug:
        raise LifecycleError("conflict", "reviewed mission belongs to another engagement")
    snapshot_bytes = state_path.read_bytes()
    snapshot = task_contract.load_public_state_bytes(
        snapshot_bytes, label=state_path.name
    )
    if not snapshot.records:
        raise LifecycleError("conflict", "the reviewed public state carries no record")
    batch_bytes = (config.PACKAGE_DIR / pack.incident_request_path).read_bytes()
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
        if shift.engagement_slug in ("northline", "gtm"):
            starting_state["consequence_rules"] = pack.consequences.model_dump(mode="json")
        if shift.engagement_slug == "gtm":
            events = repo.list_ledger_events(conn, shift.engagement_slug)
            if chain.verify_chain(events) is chain.ChainStatus.BROKEN:
                raise LifecycleError("conflict", "ledger chain is BROKEN; refusing pipeline inheritance")
            owned = {}
            for event in events:
                if event.event_type is LedgerEventType.OWNER_ASSIGNED:
                    signal = event.payload["signal_ref"]
                    if signal in owned:
                        raise LifecycleError("conflict", "pipeline history contains a duplicate owner")
                    owned[signal] = {"owner": event.payload["owner"], "record_ref": event.payload["record_ref"]}
            _verify_pipeline_history(conn, events)
            starting_state["pipeline_records"] = owned
            snapshot_bytes = task_contract.apply_pipeline_history(snapshot_bytes, owned)
            snapshot = task_contract.load_public_state_bytes(snapshot_bytes)
    condition = observed_condition(snapshot_bytes, snapshot.dependencies)
    fields = _diagnostic_context_fields(
        shift, mission, mission_bytes, snapshot_bytes, specs_bytes, workload, condition, starting_state
    )
    if operation:
        fields["evaluator_version"] = "operation-task-v1"
        fields["reducer_version"] = ("operation-ledger-v3" if shift.engagement_slug == "gtm" else
                                     "operation-ledger-v2" if shift.engagement_slug == "northline"
                                     else "operation-ledger-v1")
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


# The comparison deadline, shared with the comparison flow's frozen contexts.
COMPARE_DEADLINE_S = 10


def bind_deployment_request(request, run, context, version, mission, state_bytes, *, phase="PUBLIC"):
    """Controller-owned deployment identity; no scoring material enters the driver."""
    if not any(rule.startswith("deployment.") for rule in mission.public_rules):
        return request
    binding = task_contract.DeploymentExecutionBinding(
        run_id=run.id, context_hash=context.content_hash, artifact_hash=version.content_hash,
        state_hash=_hash_bytes(state_bytes), batch_hash=request.request_batch.content_hash,
        phase=phase, allowed_resources=tuple(mission.allowed_tool_vocabulary),
    )
    protocol = "READY_JSON"
    if version.created_by == "template":
        starter = config.PACKAGE_DIR / f"templates/artifact/{mission.engagement_slug}_blank_service.py"
        if starter.is_file() and version.files.get("service.py", "").encode() == starter.read_bytes():
            protocol = "FIXED_HTTP_8080"
    return request.model_copy(update={"deployment_binding": binding, "service_protocol": protocol})


def deployment_assessment_inputs(conn, run, spec, ordinal, state_bytes, batch_bytes, *, phase="PUBLIC",
                                 require_complete=False):
    """Supply stored verified traces only after checking their frozen run/output bindings."""
    if any(task.kind in evaluator.PIPELINE_TASK_KINDS for task in spec.tasks):
        if phase != "PUBLIC":
            return {}
        context = repo.get_execution_context(conn, run.context_id) if run.context_id else None
        if context is None or context.engagement_slug != "gtm":
            return {}
        batch_hash = canonical.content_hash(_encode(batch_bytes))
        workloads = [workload for workload in context.workloads if workload.request_batch_hash == batch_hash]
        if len(workloads) != 1:
            return {}
        specs = tuple(task_contract.CustomerRequestSpec.model_validate(raw) for raw in json.loads(
            base64.b64decode(workloads[0].request_specs_bytes_base64, validate=True)))
        if not 1 <= ordinal <= len(specs) or specs[ordinal - 1] != spec:
            return {}
        outputs = {output.request_ordinal: output for output in repo.list_outputs(conn, run.id)}
        prior = []
        for index, earlier_spec in enumerate(specs[:ordinal - 1], 1):
            output = outputs.get(index)
            if output is not None and output.transport_error is None:
                try:
                    prior.append((earlier_spec, task_contract.validate_response_envelope(earlier_spec, output.body)))
                except TaskEnvelopeInvalid:
                    pass
        return {"prior_pipeline_results": tuple(prior)}
    if not any(task.kind in (task_contract.TaskKind.CREATE_BOOKING,
                             task_contract.TaskKind.ROUTE_SAFETY_QUESTION) for task in spec.tasks):
        return {}
    context = repo.get_execution_context(conn, run.context_id) if run.context_id else None
    version = repo.get_version(conn, run.artifact_version_id)
    try:
        trace = repo.get_deployment_trace(conn, run.id, ordinal)
        if trace is None:
            raise ValueError("deployment trace missing")
        outputs = {row.request_ordinal: row for row in repo.list_outputs(conn, run.id)}
        batch_hash = canonical.content_hash(_encode(batch_bytes))
        stimuli = (executor.load_single_request(executor.BatchRef(path_ref="sealed:protected", content_hash=batch_hash),
                                              batch_bytes, ordinal),) if phase == "PROTECTED" else executor.load_batch(
            executor.BatchRef(path_ref="frozen:public", content_hash=batch_hash), batch_bytes)
        stimulus = next(row for row in stimuli if row.ordinal == ordinal)
        if (context is None or version is None or trace.run_id != run.id or trace.request_id != spec.id
                or trace.context_hash != context.content_hash or trace.artifact_hash != version.content_hash
                or trace.state_hash != _hash_bytes(state_bytes) or trace.batch_hash != batch_hash
                or trace.phase != phase or trace.request_ordinal != ordinal
                or trace.request_sha256 != _hash_bytes(stimulus.body)
                or trace.response_sha256 != _hash_bytes(outputs[ordinal].body)):
            raise ValueError("stored deployment trace binding differs")
        prior = ()
        if phase == "PUBLIC":
            prior = tuple(repo.get_deployment_trace(conn, run.id, index) for index in range(1, ordinal))
            if any(item is None for item in prior):
                raise ValueError("prior deployment trace missing")
            by_ordinal = {row.ordinal: row for row in stimuli}
            for index, item in enumerate(prior, 1):
                earlier = by_ordinal[index]
                if (item.request_ordinal != index
                        or item.request_id != json.loads(earlier.body)["request_id"]
                        or item.request_sha256 != _hash_bytes(earlier.body)
                        or item.response_sha256 != _hash_bytes(outputs[index].body)
                        or any(getattr(item, field) != getattr(trace, field) for field in
                               ("run_id", "context_hash", "artifact_hash", "state_hash", "batch_hash", "phase"))):
                    raise ValueError("prior deployment trace binding differs")
        return {"deployment_trace": trace, "prior_deployment_traces": prior}
    except (ValueError, TypeError, KeyError, StopIteration) as exc:
        if require_complete:
            raise LifecycleError("conflict", "deployment execution evidence is missing or invalid") from exc
        return {}


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


def investigation_entry(conn: sqlite3.Connection, investigation_id: str) -> Investigation:
    investigation = repo.get_investigation(conn, investigation_id)
    if investigation is None:
        raise LifecycleError("not_found", f"unknown investigation: {investigation_id}")
    return investigation
