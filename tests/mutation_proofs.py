"""Mutation proofs for the Slice 7 guard branches and the Slice 8 run binding.

Each mutation independently breaks one guard branch with a valid code change,
runs the named test selection, and requires that the named expected test fails
with an assertion-level outcome: AssertionError, or pytest's Failed (for
example "DID NOT RAISE" from pytest.raises). A mutation that only trips a
collection error, an unexpected exception or a timeout is NOT a proof of the
guard and is reported distinctly, so a crash can never masquerade as coverage.
Every file is restored byte-identically (sha256 before == after). Windows
trap: restoration uses raw bytes, never git checkout, and every target write
retries a few times because this OneDrive-synced tree can transiently fail
with EINVAL (seen 2026-09-28).

Slice 11 re-anchoring (2026-09-26). Three Slice 8 rows silently stopped
matching when Slice 10 replaced the inherited-version fallbacks with
``_selected_operating_version`` and grew a legacy branch inside
``_snapshot_bytes_for_run``: the harness reported SKIP, and the main harness was
not re-run after that refactor, so the loss went unnoticed. All three were
repaired here. ``snapshot_capture_bypassed_for_the_mutable_path`` keeps its name
and claim; the other two faulted branches that no longer exist as code, and
re-anchoring them onto the selection gate would duplicate the faults already
carried by the ``s10_legacy_*_guard_removed`` rows in
``tests/pivot_mutation_proofs.py``, which is evidence of neither. They are
renamed onto uncovered branches in the same functions instead, keeping their
original named tests covered.
"""

import hashlib
import shlex
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Subprocesses must run under the same interpreter as the harness. The previous
# hardcoded .venv path is now blocked by Windows Smart App Control on this
# machine, and a pinned path is not portable across machines anyway.
PYTHON = sys.executable

MUTATIONS = [
    {
        "name": "budget_comparison_off_by_one",
        "file": "shiftwork/orchestrator.py",
        "old": b"if used >= limit:",
        "new": b"if used > limit:",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_budget_enforced_controller_side",
        "expect": "test_budget_enforced_controller_side",
    },
    {
        "name": "exposure_filter_removed",
        "file": "shiftwork/sealed/rotation.py",
        "old": b"return tuple(case for case in cases if variant_ref(case) not in exposed)",
        "new": b"return tuple(case for case in cases)",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_select_variant_excludes_exposed_variants",
        "expect": "test_select_variant_excludes_exposed_variants",
    },
    {
        "name": "select_variant_tiebreak_reversed",
        "file": "shiftwork/sealed/rotation.py",
        "old": b"return min(available, key=lambda case: (min(case.request_ordinals), cases.index(case)))",
        "new": b"return min(available, key=lambda case: (min(case.request_ordinals), len(cases) - 1 - cases.index(case)))",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_select_variant_ordinal_tie_prefers_earlier_file_order",
        "expect": "test_select_variant_ordinal_tie_prefers_earlier_file_order",
    },
    {
        "name": "shared_ordinal_misconfig_not_raised",
        "file": "shiftwork/sealed/rotation.py",
        "old": b"""    if len(tuples) != 1:
        raise RotationMisconfigured(
            "drawn variants must share exactly one request ordinal; got "
            + ", ".join(f"{family}: {case.request_ordinals}" for family, case in sorted(draws.items()))
        )""",
        "new": b"""    if len(tuples) != 1:
        pass""",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_shared_ordinal_rejects_mismatched_draws",
        "expect": "test_shared_ordinal_rejects_mismatched_draws",
    },
    {
        "name": "shared_ordinal_multi_ordinal_not_raised",
        "file": "shiftwork/sealed/rotation.py",
        "old": b"""    if len(shared) != 1:
        raise RotationMisconfigured(f"a drawn variant binds several request ordinals: {shared}")""",
        "new": b"""    if len(shared) != 1:
        pass  # MUTATION: was raise""",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_shared_ordinal_rejects_multi_ordinal_variant",
        "expect": "test_shared_ordinal_rejects_multi_ordinal_variant",
    },
    {
        "name": "rollback_except_path_removed",
        "file": "shiftwork/orchestrator.py",
        "old": b"""    except Exception:
        conn.rollback()
        raise
    return run""",
        "new": b"""    except Exception:
        raise
    return run""",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_reservation_fault_rolls_back_the_whole_reservation",
        "expect": "test_reservation_fault_rolls_back_the_whole_reservation",
    },
    {
        "name": "resolution_gate_version_removed",
        "file": "shiftwork/orchestrator.py",
        "old": b"if opening is None or opening.artifact_version_id == run.artifact_version_id:",
        "new": b"if opening is None:",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_repair_resolution_same_version_never_resolves",
        "expect": "test_repair_resolution_same_version_never_resolves",
    },
    {
        "name": "resolution_gate_regression_removed",
        "file": "shiftwork/orchestrator.py",
        "old": b"if regression is None or regression.verdict != \"pass\":",
        "new": b"if regression is None:",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_repair_resolution_failing_regression_never_resolves",
        "expect": "test_repair_resolution_failing_regression_never_resolves",
    },
    {
        "name": "resolution_gate_acceptance_removed",
        "file": "shiftwork/orchestrator.py",
        "old": b"if acceptance_result is None or acceptance_result.verdict != \"pass\":",
        "new": b"if acceptance_result is None:",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_repair_resolution_failing_acceptance_never_resolves",
        "expect": "test_repair_resolution_failing_acceptance_never_resolves",
    },
    {
        "name": "invalidate_state_filter_removed",
        "file": "shiftwork/store/repo.py",
        "old": b"\"UPDATE rotation_draws SET state = ? WHERE engagement_slug = ? AND family = ? AND state = ?\",\n        (DrawState.INVALIDATED.value, slug, family, DrawState.ACTIVE.value),",
        "new": b"\"UPDATE rotation_draws SET state = ? WHERE engagement_slug = ? AND family = ?\",\n        (DrawState.INVALIDATED.value, slug, family),",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_invalidate_rotation_group_retires_only_active_draws",
        "expect": "test_invalidate_rotation_group_retires_only_active_draws",
    },
    {
        "name": "cycle_hardcoded_to_one",
        "file": "shiftwork/orchestrator.py",
        "old": b"cycle=sealed_store.family_cycle(family),",
        "new": b"cycle=1,",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_rotation_exhaustion_fail_closed",
        "expect": "test_rotation_exhaustion_fail_closed",
    },
    {
        "name": "validate_refill_exposed_rejection_removed",
        "file": "shiftwork/sealed/rotation.py",
        "old": b"""        if ref in exposed:
            raise RotationMisconfigured(
                f"refill reuses the exposed identity of variant {case.id!r} ({ref})"
            )""",
        "new": b"""        if ref in exposed:
            pass  # MUTATION: was raise""",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_rotation_exhaustion_fail_closed",
        "expect": "test_rotation_exhaustion_fail_closed",
    },
    {
        "name": "validate_refill_repeated_rejection_removed",
        "file": "shiftwork/sealed/rotation.py",
        "old": b"""        if ref in seen:
            raise RotationMisconfigured(f"refill repeats the identity of variant {case.id!r} ({ref})")""",
        "new": b"""        if ref in seen:
            pass  # MUTATION: was raise""",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_rotation_exhaustion_fail_closed",
        "expect": "test_rotation_exhaustion_fail_closed",
    },
    {
        "name": "sealed_store_schema_validation_removed",
        "file": "shiftwork/sealed/store.py",
        "old": b"""    if file_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnsupportedSealedSchema(
            f"sealed family {family!r} declares unsupported file schema_version {file_version!r}"
        )""",
        "new": b"""    if file_version not in SUPPORTED_SCHEMA_VERSIONS:
        pass""",
        "tests": "tests/sealed/test_store_validation.py",
        "expect": "test_unsupported_file_schema_version_raises",
    },
    {
        "name": "sealed_store_ordinal_validation_removed",
        "file": "shiftwork/sealed/store.py",
        "old": b"""        if (
            not isinstance(ordinals, list)
            or not ordinals
            or any(isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1 for ordinal in ordinals)
            or len(set(ordinals)) != len(ordinals)
        ):
            raise InvalidSealedCase(
                f"sealed case {raw.get('id')!r} needs a non-empty, duplicate-free list of "
                f"positive request ordinals; got {ordinals!r}"
            )""",
        "new": b"""        if (
            not isinstance(ordinals, list)
            or not ordinals
            or any(isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1 for ordinal in ordinals)
            or len(set(ordinals)) != len(ordinals)
        ):
            pass""",
        "tests": "tests/sealed/test_store_validation.py",
        "expect": "test_empty_ordinals_raises",
    },
    {
        "name": "load_drawn_cases_resolved_filter_removed",
        "file": "shiftwork/sealed/store.py",
        "old": b"""    for incident in repo.list_incidents(conn, engagement_slug):
        if incident.state is IncidentState.RESOLVED:
            continue
        failing = next(""",
        "new": b"""    for incident in repo.list_incidents(conn, engagement_slug):
        if False:
            continue
        failing = next(""",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_resolved_incident_regression_excluded_from_later_run",
        "expect": "test_resolved_incident_regression_excluded_from_later_run",
    },
    {
        "name": "migration_v2_log_ref_skipped",
        "file": "shiftwork/store/db.py",
        "old": b"""        if current == 2:
            conn.execute("ALTER TABLE run_outputs ADD COLUMN log_ref TEXT")""",
        "new": b"""        if current == 2:
            pass  # MUTATION: was ALTER TABLE run_outputs ADD COLUMN log_ref""",
        "tests": "tests/executor/test_conformance.py::test_existing_schema_two_gets_log_column_without_data_loss",
        "expect": "test_existing_schema_two_gets_log_column_without_data_loss",
    },
    {
        "name": "migration_v2_runs_columns_skipped",
        "file": "shiftwork/store/db.py",
        "old": b"        if current in (2, 3):",
        "new": b"        if current in (3,):",
        "tests": "tests/executor/test_conformance.py::test_existing_schema_two_gets_log_column_without_data_loss",
        "expect": "test_existing_schema_two_gets_log_column_without_data_loss",
    },
    {
        "name": "migration_v3_runs_columns_skipped",
        "file": "shiftwork/store/db.py",
        "old": b"        if current in (2, 3):",
        "new": b"        if current == 2:",
        "tests": "tests/executor/test_conformance.py::test_existing_schema_three_gets_rotation_columns_without_data_loss",
        "expect": "test_existing_schema_three_gets_rotation_columns_without_data_loss",
    },
    {
        "name": "migration_backfill_removed",
        "file": "shiftwork/store/db.py",
        "old": b"""            conn.execute(
                "UPDATE runs SET request_batch_ref = ?, shop_snapshot_ref = ? "
                "WHERE request_batch_ref IS NULL",
                (_LEGACY_RUN_BATCH, _LEGACY_RUN_SNAPSHOT),
            )""",
        "new": b"""            pass  # MUTATION: was the legacy-run backfill UPDATE""",
        "tests": "tests/executor/test_conformance.py::test_existing_schema_two_gets_log_column_without_data_loss",
        "expect": "test_existing_schema_two_gets_log_column_without_data_loss",
    },
    # Slice 8 run binding (Route A): the run row is the single source of
    # execution identity, unmapped pairings fail closed, and the controller
    # configuration is what start_run persists.
    {
        "name": "resolution_ignores_run_row",
        "file": "shiftwork/orchestrator.py",
        "old": b"""    if run.adapter == "local_process":
        return LocalProcessAdapter()
    if run.adapter != "recorded":
        return None""",
        "new": b"""    if False:
        return LocalProcessAdapter()
    if False:
        return None""",
        "tests": "tests/orchestrator/test_run_binding.py::test_run_row_adapter_is_load_bearing",
        "expect": "test_run_row_adapter_is_load_bearing",
    },
    {
        "name": "unimplemented_adapter_falls_through",
        "file": "shiftwork/orchestrator.py",
        "old": b"""    if run.adapter != "recorded":
        return None""",
        "new": b"""    if run.adapter not in ("recorded", "tokenfactory"):
        return None""",
        "tests": "tests/orchestrator/test_run_binding.py::test_unimplemented_adapter_fails_closed_before_execution",
        "expect": "test_unimplemented_adapter_fails_closed_before_execution",
    },
    {
        "name": "unmapped_pairing_falls_back_to_the_batch",
        "file": "shiftwork/orchestrator.py",
        "old": b"""    ref = config.RECORDED_TRANSCRIPTS.get((run.request_batch_ref, snapshot_hash))
    if ref is None:
        return None""",
        "new": b"""    ref = config.RECORDED_TRANSCRIPTS.get((run.request_batch_ref, snapshot_hash))
    if ref is None:
        ref = next((name for (batch, _), name in config.RECORDED_TRANSCRIPTS.items() if batch == run.request_batch_ref), None)
    if ref is None:
        return None""",
        "tests": "tests/orchestrator/test_run_binding.py::test_unmapped_pairing_fails_closed_without_invoking_an_adapter",
        "expect": "test_unmapped_pairing_fails_closed_without_invoking_an_adapter",
    },
    {
        "name": "pairing_key_ignores_the_snapshot",
        "file": "shiftwork/orchestrator.py",
        "old": b"""    ref = config.RECORDED_TRANSCRIPTS.get((run.request_batch_ref, snapshot_hash))""",
        "new": b"""    ref = next((name for (batch, _), name in config.RECORDED_TRANSCRIPTS.items() if batch == run.request_batch_ref), None)  # MUTATION: snapshot ignored""",
        "tests": "tests/api/test_thin_path.py::test_thin_path_produces_real_checks_and_a_real_chained_event",
        "expect": "test_thin_path_produces_real_checks_and_a_real_chained_event",
    },
    {
        "name": "route_ignores_the_configured_executor",
        "file": "shiftwork/api/routes.py",
        "old": b"""        executor=request.app.state.executor,""",
        "new": b"""        executor=None,""",
        "tests": "tests/orchestrator/test_run_binding.py::test_route_persists_the_controller_configured_adapter",
        "expect": "test_route_persists_the_controller_configured_adapter",
    },
    {
        "name": "route_drops_the_configured_snapshot",
        "file": "shiftwork/api/routes.py",
        "old": b"""        shop_snapshot=request.app.state.shop_snapshot,""",
        "new": b"""        shop_snapshot=None,""",
        "tests": "tests/api/test_thin_path.py::test_thin_path_produces_real_checks_and_a_real_chained_event",
        "expect": "test_thin_path_produces_real_checks_and_a_real_chained_event",
    },
    {
        "name": "snapshot_pin_edited",
        "file": "shiftwork/config.py",
        "old": b'"bd66a4136c8dc1156ff50645195d437328cb3ea18206be9eba976d3ea168933f"',
        "new": b'"ad66a4136c8dc1156ff50645195d437328cb3ea18206be9eba976d3ea168933f"',
        "tests": "tests/orchestrator/test_run_binding.py::test_snapshot_pins_and_authored_pairings_match_the_fixtures",
        "expect": "test_snapshot_pins_and_authored_pairings_match_the_fixtures",
    },
    # Slice 8 close, inheritance, restart recovery and the pre-proof seam: each row
    # independently breaks one guard branch and names the test that must fail.
    {
        "name": "close_declares_limits_only_from_the_version_in_force",
        "file": "shiftwork/orchestrator.py",
        "old": b"""            facts = CloseShiftFacts(
                shift_id=shift.id,
                declared_limits=tuple(version.contract.declared_limits),""",
        "new": b"""            facts = CloseShiftFacts(
                shift_id=shift.id,
                declared_limits=(),""",
        "tests": "tests/orchestrator/test_close_inheritance.py::test_close_declares_the_inherited_limits_when_a_shift_never_froze",
        "expect": "test_close_declares_the_inherited_limits_when_a_shift_never_froze",
    },
    {
        "name": "close_in_flight_refusal_removed",
        "file": "shiftwork/orchestrator.py",
        "old": b"""        in_flight = [
            run.id
            for run in repo.list_runs_for_shift(conn, shift_id)
            if run.state not in (RunState.FINALIZED, RunState.FAILED)
        ]
        if in_flight:""",
        "new": b"""        in_flight: list[str] = []
        if in_flight:""",
        "tests": "tests/orchestrator/test_close_inheritance.py::test_close_refuses_while_a_run_is_in_flight",
        "expect": "test_close_refuses_while_a_run_is_in_flight",
    },
    {
        "name": "close_idempotency_removed",
        "file": "shiftwork/orchestrator.py",
        "old": b"""        if shift.state == "closed":
            conn.rollback()
            return shift""",
        "new": b"""        if False:
            conn.rollback()
            return shift""",
        "tests": "tests/orchestrator/test_close_inheritance.py::test_close_shift_records_unresolved_limits",
        "expect": "test_close_shift_records_unresolved_limits",
    },
    {
        "name": "reconcile_marks_nothing",
        "file": "shiftwork/orchestrator.py",
        "old": b"    for run in repo.list_nonterminal_runs(conn):",
        "new": b"    for run in []:  # MUTATION: was repo.list_nonterminal_runs(conn)",
        "tests": "tests/ledger/test_ledger.py::test_restart_reconciles_nonterminal_runs_keeping_captures_and_draws",
        "expect": "test_restart_reconciles_nonterminal_runs_keeping_captures_and_draws",
    },
    {
        "name": "resolution_ignores_closed_unresolved",
        "file": "shiftwork/orchestrator.py",
        "old": b"""    for incident in repo.list_incidents(conn, slug):
        if incident.state is IncidentState.RESOLVED:
            continue
        linked = _incident_case(conn, incident)""",
        "new": b"""    for incident in repo.list_incidents(conn, slug):
        if incident.state is not IncidentState.OPEN:
            continue
        linked = _incident_case(conn, incident)""",
        "tests": "tests/orchestrator/test_close_inheritance.py::test_inherited_unresolved_incident_resolves_on_a_later_passing_run",
        "expect": "test_inherited_unresolved_incident_resolves_on_a_later_passing_run",
    },
    {
        "name": "drawn_cases_skip_closed_unresolved",
        "file": "shiftwork/sealed/store.py",
        "old": b"""    for incident in repo.list_incidents(conn, engagement_slug):
        if incident.state is IncidentState.RESOLVED:
            continue
        failing = next(""",
        "new": b"""    for incident in repo.list_incidents(conn, engagement_slug):
        if incident.state is not IncidentState.OPEN:
            continue
        failing = next(""",
        "tests": "tests/orchestrator/test_close_inheritance.py::test_inherited_unresolved_incident_resolves_on_a_later_passing_run",
        "expect": "test_inherited_unresolved_incident_resolves_on_a_later_passing_run",
    },
    {
        "name": "resolve_incident_only_from_open",
        "file": "shiftwork/store/repo.py",
        "old": b"""        "WHERE id = ? AND state IN (?, ?)",
        (
            IncidentState.RESOLVED.value,
            resolving_version_id,
            resolved_event_seq,
            incident_id,
            IncidentState.OPEN.value,
            IncidentState.CLOSED_UNRESOLVED.value,
        ),""",
        "new": b"""        "WHERE id = ? AND state IN (?, ?)",
        (
            IncidentState.RESOLVED.value,
            resolving_version_id,
            resolved_event_seq,
            incident_id,
            IncidentState.OPEN.value,
            IncidentState.OPEN.value,
        ),""",
        "tests": "tests/orchestrator/test_close_inheritance.py::test_inherited_unresolved_incident_resolves_on_a_later_passing_run",
        "expect": "test_inherited_unresolved_incident_resolves_on_a_later_passing_run",
    },
    {
        "name": "limits_projection_unions_all_declarations",
        "file": "shiftwork/store/repo.py",
        "old": b"""        if (_load(row["cause_refs_json"]) or [None])[0] == latest_closed["id"]""",
        "new": b"""        if True""",
        "tests": "tests/orchestrator/test_close_inheritance.py::test_unresolved_limits_follow_the_latest_close",
        "expect": "test_unresolved_limits_follow_the_latest_close",
    },
    {
        "name": "close_leaves_incidents_open",
        "file": "shiftwork/store/repo.py",
        "old": b"        (IncidentState.CLOSED_UNRESOLVED.value, slug, IncidentState.OPEN.value),",
        "new": b"        (IncidentState.OPEN.value, slug, IncidentState.OPEN.value),",
        "tests": "tests/orchestrator/test_close_inheritance.py::test_close_shift_records_unresolved_limits",
        "expect": "test_close_shift_records_unresolved_limits",
    },
    {
        "name": "board_hides_closed_unresolved",
        "file": "shiftwork/orchestrator.py",
        "old": b"""        "incidents": [
            incident
            for incident in incidents
            if incident.state in (IncidentState.OPEN, IncidentState.CLOSED_UNRESOLVED)
        ],""",
        "new": b"""        "incidents": [
            incident
            for incident in incidents
            if incident.state is IncidentState.OPEN
        ],""",
        "tests": "tests/orchestrator/test_close_inheritance.py::test_close_shift_records_unresolved_limits",
        "expect": "test_close_shift_records_unresolved_limits",
    },
    {
        "name": "start_run_draws_one_variant_per_enabled_family",
        "file": "shiftwork/orchestrator.py",
        "old": b"        for family in _enabled_families(conn, shift.engagement_slug):\n",
        "new": b"        for family in list(_enabled_families(conn, shift.engagement_slug))[:1]:\n",
        "tests": "tests/orchestrator/test_test1_preproof.py::test_full_budget_preserves_unseen_inherited_case",
        "expect": "test_full_budget_preserves_unseen_inherited_case",
    },
    {
        "name": "board_snapshot_inherited_version_fallback_removed",
        "file": "shiftwork/orchestrator.py",
        "old": b"    if latest_version is None and latest_shift is not None:",
        "new": b"    if False:  # MUTATION: inherited-version fallback disabled",
        "tests": "tests/orchestrator/test_close_inheritance.py::test_open_shift_seeds_from_inheritance",
        "expect": "test_open_shift_seeds_from_inheritance",
    },
    {
        "name": "rotation_exhaustion_message_drops_the_refusal_detail",
        "file": "shiftwork/sealed/rotation.py",
        "old": b'            f"rotation group {family!r} has no never-exposed variant left; "',
        "new": b'            f"rotation group {family!r} is exhausted; "',
        "tests": "tests/orchestrator/test_test1_preproof.py::test_next_shift_needs_the_six_variant_inventory",
        "expect": "test_next_shift_needs_the_six_variant_inventory",
    },
    # Slice 9 review round: each row breaks one new provenance guard branch and
    # names the test that must fail when the run consumes the mutable path again.
    {
        "name": "snapshot_capture_bypassed_for_the_mutable_path",
        "file": "shiftwork/orchestrator.py",
        "old": b"""    stored = repo.get_run_snapshot_bytes(conn, run.id)
    if stored is not None:
        return stored
""",
        "new": b"",
        "tests": "tests/api/test_client_evidence.py::test_historical_projection_binds_the_bytes_the_run_consumed_not_the_current_file",
        "expect": "test_historical_projection_binds_the_bytes_the_run_consumed_not_the_current_file",
    },
    {
        "name": "retrieval_aborts_when_the_comparison_source_is_missing",
        "file": "shiftwork/orchestrator.py",
        "old": b"""    try:
        snapshot_bytes = _snapshot_bytes_for_run(conn, run)
        records = _public_records(snapshot_bytes)
    except (OSError, ValueError):
        snapshot_bytes = None""",
        "new": b"""    snapshot_bytes = _snapshot_bytes_for_run(conn, run)
    records = _public_records(snapshot_bytes)""",
        "tests": "tests/api/test_client_evidence.py::test_legacy_run_without_capture_degrades_when_the_source_is_missing",
        "expect": "test_legacy_run_without_capture_degrades_when_the_source_is_missing",
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_bytes_with_retry(path: Path, data: bytes, attempts: int = 4) -> OSError | None:
    """Retry OneDrive-synced writes that transiently fail with EINVAL (2026-09-28, MISTAKES.md)."""
    last: OSError | None = None
    for attempt in range(attempts):
        try:
            path.write_bytes(data)
            return None
        except OSError as exc:
            last = exc
            time.sleep(0.25 * (attempt + 1))
    return last


def catch_kind(message: str) -> str:
    """Assertion-level catches only.

    pytest's junit message for a failed assertion is the rendered assertion
    ("assert 409 == 202"), or "AssertionError: ..." when the assertion carried a
    message; pytest.raises and pytest.fail failures read "Failed: ...". Any
    exception class name (sqlite3.ProgrammingError, ValueError, ...) is a crash.
    """
    head = (message or "").strip()
    if head.startswith(("assert", "AssertionError", "Failed:")):
        return "clean"
    return "incidental"


def summary_line(stdout: str) -> str:
    """The pytest summary line, ignoring any trailing stderr noise."""
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith(("=", "FAILED", "ERROR")):
            continue
        if "passed" in line or "failed" in line or "error" in line or "no tests ran" in line:
            return line
    return lines[-1] if lines else "no output"


def read_junit(report: Path) -> tuple[dict[str, dict], dict[str, str]]:
    """Per-test failure kinds and setup errors from a pytest junit report."""
    failures: dict[str, dict] = {}
    errors: dict[str, str] = {}
    if not report.exists():
        return failures, errors
    for case in ET.parse(report).getroot().iter("testcase"):
        module = (case.get("classname") or "").lstrip(".").replace(".", "/")
        key = f"{module}.py::{case.get('name')}"
        for failure in case.findall("failure"):
            message = failure.get("message") or ""
            failures[key] = {"kind": catch_kind(message), "message": message}
        for error in case.findall("error"):
            errors[key] = error.get("message") or ""
    return failures, errors


def run_mutation(mutation: dict) -> dict:
    target = REPO / mutation["file"]
    original_bytes = target.read_bytes()
    original_hash = hashlib.sha256(original_bytes).hexdigest()

    old = mutation["old"]
    new = mutation["new"]
    if isinstance(old, str):
        old = old.encode("utf-8")
    if isinstance(new, str):
        new = new.encode("utf-8")

    # Handle CRLF: the worktree may use CRLF
    if old not in original_bytes:
        old_crlf = old.replace(b"\n", b"\r\n")
        if old_crlf in original_bytes:
            old = old_crlf
            new = new.replace(b"\n", b"\r\n")
        else:
            return {"name": mutation["name"], "status": "SKIP", "reason": "pattern not found"}

    count = original_bytes.count(old)
    if count != 1:
        return {"name": mutation["name"], "status": "SKIP", "reason": f"pattern found {count} times"}

    mutated = original_bytes.replace(old, new, 1)

    timeout = False
    stdout = ""
    failures: dict[str, dict] = {}
    errors: dict[str, str] = {}
    try:
        mutation_error = write_bytes_with_retry(target, mutated)
        if mutation_error is not None:
            raise mutation_error
        test_args = shlex.split(mutation["tests"])
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "junit.xml"
            process = subprocess.Popen(
                [PYTHON, "-m", "pytest", *test_args, "-q", "--tb=short", "--no-header", "-rf",
                 f"--junitxml={report}"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=str(REPO),
            )
            try:
                stdout, _ = process.communicate(timeout=240)
            except subprocess.TimeoutExpired:
                process.kill()
                partial, _ = process.communicate()
                stdout = partial or ""
                timeout = True
            failures, errors = read_junit(report)
    finally:
        restore_error = write_bytes_with_retry(target, original_bytes)
        restored_hash = sha256(target)
        assert restored_hash == original_hash, (
            f"RESTORATION FAILED for {mutation['name']}: {restored_hash} != {original_hash}"
            + (f" (last write error: {restore_error!r})" if restore_error is not None else "")
        )

    base = {"name": mutation["name"], "sha256_restored": restored_hash == original_hash}
    last_line = summary_line(stdout)

    if timeout:
        tail = " | ".join(line.strip() for line in stdout.splitlines()[-3:] if line.strip())
        return {**base, "status": "NOT_CAUGHT", "detail": f"TIMEOUT: no test failed; last output: {tail[:200]}"}

    expect = mutation["expect"]
    matched = [key for key in failures if expect in key]

    if not matched:
        if failures or errors:
            detail = "expected " + expect + " to fail; failures: " + ", ".join(sorted(failures))
            if errors:
                detail += "; errors: " + ", ".join(sorted(errors))
        else:
            detail = "no test-level failure (" + last_line + ")"
        return {**base, "status": "NOT_CAUGHT", "detail": detail}

    entry = failures[matched[0]]
    message = entry["message"].replace("\n", " ")[:110]
    if entry["kind"] != "clean":
        return {**base, "status": "CAUGHT_INCIDENTAL",
                "detail": f"{expect}: {message} (not an assertion-level failure)"}

    return {**base, "status": "FAIL_CAUGHT", "detail": f"{message} [{last_line}]"}


def main():
    results = []
    for mutation in MUTATIONS:
        print(f"  mutating: {mutation['name']}...", end=" ", flush=True)
        result = run_mutation(mutation)
        results.append(result)
        print(result["status"])

    print("\n=== MUTATION PROOF TABLE ===")
    print(f"{'mutation':<47} {'status':<17} {'sha256 ok':<10} catch")
    print("-" * 150)
    for r in results:
        sha_ok = r.get("sha256_restored", "N/A")
        print(f"{r['name']:<47} {r['status']:<17} {str(sha_ok):<10} "
              f"{r.get('detail', r.get('reason', ''))}")

    caught = [r for r in results if r["status"] == "FAIL_CAUGHT"]
    incidental = [r["name"] for r in results if r["status"] == "CAUGHT_INCIDENTAL"]
    not_caught = [r["name"] for r in results if r["status"] == "NOT_CAUGHT"]
    skipped = [r["name"] for r in results if r["status"] == "SKIP"]

    print(f"\nassertion-level catches: {len(caught)}/{len(results)}")
    if incidental:
        print(f"INCIDENTAL catches (crash, not an assertion-level proof): {incidental}")
    if not_caught:
        print(f"NOT CAUGHT (guard may be vacuous): {not_caught}")
    if skipped:
        print(f"SKIPPED (pattern issue): {skipped}")
    return 1 if len(caught) != len(results) else 0


if __name__ == "__main__":
    sys.exit(main())
