"""The qualifying and later-condition comparison subsystem, moved verbatim out of orchestrator."""

import asyncio
import base64
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from shiftwork import config
from shiftwork import orchestrator
# Adapter classes resolve via orchestrator at call time so monkeypatch replacements stay effective.
from shiftwork.domain import canonical, comparison, task_contract
from shiftwork.domain.errors import BootstrapBlocked, ShiftworkDomainError, TaskEnvelopeInvalid
from shiftwork.domain.models import (
    CandidateRef,
    ContextCondition,
    EvidenceMode,
    ExecutionContext,
    ExecutionObservation,
    ExecutorFailure,
    Experiment,
    ExperimentKind,
    ExposureItem,
    ExposureReservation,
    FrozenWorkload,
    IncidentState,
    ObservationKind,
    Run,
    RunAssessment,
    RunPurpose,
    RunState,
    Shift,
    TrialSlot,
)
from shiftwork.evaluator import evaluator
from shiftwork.executor import base as executor
from shiftwork.gateway.protocol import GATEWAY_MAX_OUTPUT_TOKENS
from shiftwork.gateway.redaction import assert_public_safe
from shiftwork.ledger import chain
from shiftwork.live_budget import LiveComparisonBudget
from shiftwork.packs.registry import FamilyClass
from shiftwork.orchestrator import (
    COMPARE_DEADLINE_S,
    DIAGNOSTIC_HARNESS_REF,
    DIAGNOSTIC_IMAGE_REF,
    LifecycleError,
    _comparison_run_request,
    _encode,
    _hash_bytes,
    _now,
    _private_public_needles,
    _require_open_shift,
    _selected_operating_version,
    observed_condition,
)
from shiftwork.sealed import rotation
from shiftwork.sealed import store as sealed_store
from shiftwork.store import db, repo


# --- Slice 15: the qualifying comparison ------------------------------------

COMPARISONS_PER_SHIFT = 1
# One retained-alternative re-test per shift, reserved separately from the
# qualifying comparison (Gate 3 S6.7); it consumes its own protected exposure.
LATER_COMPARISONS_PER_SHIFT = 1
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
    pack = orchestrator.admit_pack(slug)
    manifest_path = config.PACKAGE_DIR / pack.manifest_path
    try:
        data = json.loads(manifest_path.read_bytes().decode("utf-8"))
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
                manifest_path.parent / str(entry["request_file"])
            ).read_bytes()
            specs_bytes = (
                manifest_path.parent / str(entry["task_spec_file"])
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
        pack = orchestrator.admit_pack(shift.engagement_slug)
        isolated = adapter == orchestrator.TokenFactoryAdapter.name
        if adapter not in (orchestrator.LocalProcessAdapter.name, orchestrator.TokenFactoryAdapter.name):
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

        mission_path = config.PACKAGE_DIR / pack.mission_path
        mission_bytes = mission_path.read_bytes()
        mission = task_contract.load_mission_bytes(mission_bytes, label=mission_path.name)
        if mission.engagement_slug != shift.engagement_slug:
            raise LifecycleError("conflict", "reviewed mission belongs to another engagement")
        state_path = config.PACKAGE_DIR / pack.comparison_state_path
        snapshot_bytes = state_path.read_bytes()
        snapshot = task_contract.load_public_state_bytes(
            snapshot_bytes, label=state_path.name
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
        for declaration in pack.families:
            if declaration.family_class is not FamilyClass.COMPARISON:
                continue
            family = declaration.family
            drawn = rotation.select_pair_variants(
                family,
                sealed_store.load_declared_family(declaration, slug=pack.slug).cases,
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
                        cycle=declaration.cycle,
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
        pack = orchestrator.admit_pack(shift.engagement_slug)
        isolated = adapter == orchestrator.TokenFactoryAdapter.name
        if adapter not in (orchestrator.LocalProcessAdapter.name, orchestrator.TokenFactoryAdapter.name):
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

        mission_path = config.PACKAGE_DIR / pack.mission_path
        mission_bytes = mission_path.read_bytes()
        mission = task_contract.load_mission_bytes(mission_bytes, label=mission_path.name)
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
        reviewed_comparison_bytes = (config.PACKAGE_DIR / pack.comparison_state_path).read_bytes()
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
        for declaration in pack.families:
            if declaration.family_class is not FamilyClass.COMPARISON:
                continue
            family = declaration.family
            drawn = rotation.select_pair_variants(
                family,
                sealed_store.load_declared_family(declaration, slug=pack.slug).cases,
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
                    cycle=declaration.cycle, variant_ref=ref,
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
            request = orchestrator.bind_deployment_request(request, run, context, version, mission, snapshot_bytes)
            if run.adapter == orchestrator.TokenFactoryAdapter.name:
                adapter = orchestrator.TokenFactoryAdapter(
                    run_id=run.id,
                    allowed_tool_names=tuple(mission.allowed_tool_vocabulary),
                    token=os.environ.get("NEBIUS_API_KEY", ""),
                    project=os.environ.get("NEBIUS_PROJECT_ID", ""),
                    model=context.service_model or config.SERVICE_MODEL,
                    live_budget=live_budget,
                )
            elif run.adapter == orchestrator.LocalProcessAdapter.name:
                adapter = orchestrator.LocalProcessAdapter()
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
                protected_request = orchestrator.bind_deployment_request(
                    protected_request, run, context, version, mission, protected_state_bytes, phase="PROTECTED")
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
                **orchestrator.deployment_assessment_inputs(conn, run, spec, index, snapshot_bytes,
                    base64.b64decode(workload.request_batch_bytes_base64)),
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
            **orchestrator.deployment_assessment_inputs(conn, run, protected_spec, slot.executed_request_count,
                protected_state_bytes, protected_line, phase="PROTECTED"),
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
                or any(run is None or run.adapter != orchestrator.TokenFactoryAdapter.name for run in runs)
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
                    **orchestrator.deployment_assessment_inputs(
                        conn, run, spec, ordinal, public_bytes,
                        base64.b64decode(next(item.request_batch_bytes_base64
                                             for item in context.workloads
                                             if item.id == slot.workload_id), validate=True),
                        phase="PUBLIC",
                    ) if run is not None else {},
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
                        **orchestrator.deployment_assessment_inputs(
                            conn, run, protected_spec, slot.executed_request_count,
                            reserved.resolved_state_bytes,
                            task_contract.protected_request_bytes(reserved.case.stimulus.request),
                            phase="PROTECTED",
                        ),
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
