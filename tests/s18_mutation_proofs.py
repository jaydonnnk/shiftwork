"""Named S18 guard mutations. Each source file is restored byte-for-byte."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = "tests/orchestrator/test_selection_operation.py::"
CASES = (
    ("invalid_selection", "shiftwork/orchestrator.py",
     'if selection is None or selection.state != "VALID":', "if selection is None or False:",
     "test_selected_operation_rejects_invalid_choice_even_with_active_exposure", 1),
    ("selected_hash", "shiftwork/orchestrator.py",
     "or version.content_hash != selection.selected_content_hash", "or False",
     "test_selected_operation_rejects_changed_selected_hash", 1),
    ("partial_retry", "shiftwork/orchestrator.py",
     "if (repo.list_outputs(conn, previous.id)", "if (False",
     "test_selected_operation_partial_output_blocks_retry", 1),
    ("changed_choice_retry", "shiftwork/orchestrator.py",
     "previous.selection_id != selection.id", "False",
     "test_selected_operation_changed_choice_blocks_zero_output_retry", 1),
    ("changed_context_retry", "shiftwork/orchestrator.py",
     "prior_operations[0].context_id != context.id", "False",
     "test_selected_operation_changed_context_blocks_zero_output_retry", 1),
    ("business_write_retry", "shiftwork/orchestrator.py",
     "previous.id in event.cause_refs", "False",
     "test_selected_operation_prior_business_write_blocks_zero_output_retry", 1),
    ("operation_key_replay", "shiftwork/orchestrator.py",
     'if replay is not None:\n        prior = repo.get_run(conn, replay["id"])',
     'if False:\n        prior = repo.get_run(conn, replay["id"])',
     "test_selected_operation_newer_save_and_exact_key_replay", 1),
    ("captured_mission", "shiftwork/orchestrator.py",
     "mission_bytes = base64.b64decode(context.mission_bytes_base64, validate=True)",
     "mission_bytes = config.PIVOT_MISSION.read_bytes()",
     "test_selected_operation_uses_captured_mission_after_file_change", 1),
    ("experiment_reducer", "shiftwork/ledger/reducer.py",
     "if (run.purpose is not RunPurpose.OPERATION or run.selection_id is None",
     "if (False or run.selection_id is None",
     "test_experiment_cannot_construct_operational_business_drafts", 1),
    ("same_version_resolution", "shiftwork/orchestrator.py",
     "opened.artifact_version_id == version.id", "False",
     "test_incident_resolves_only_after_selected_operational_regression", 1),
    ("pinned_rule_resolution", "shiftwork/orchestrator.py",
     "or opened_context.mission_hash != context.mission_hash", "or False",
     "test_incident_resolves_only_after_selected_operational_regression", 1),
    ("inflight_database", "shiftwork/store/migrations/v6_tables.sql",
     "AND r.purpose = 'OPERATION' AND r.state NOT IN ('FINALIZED', 'FAILED')",
     "AND r.purpose = 'EXPERIMENT' AND r.state NOT IN ('FINALIZED', 'FAILED')",
     "test_selected_operation_database_limits_and_zero_output_retry", 2),
    ("inflight_engagement_scope", "shiftwork/store/migrations/v6_tables.sql",
     "s.engagement_slug = target.engagement_slug", "s.id = target.id",
     "test_selected_operation_database_limits_and_zero_output_retry", 2),
    ("one_success_database", "shiftwork/store/migrations/v6_tables.sql",
     "WHERE purpose = 'OPERATION' AND context_id IS NOT NULL AND state = 'FINALIZED'",
     "WHERE purpose = 'LEGACY_OPERATION' AND context_id IS NOT NULL AND state = 'FINALIZED'",
     "test_finalized_operation_unique_constraint_is_database_enforced", 1),
    ("mandatory_sale", "shiftwork/ledger/reducer.py",
     "if required and evaluator.request_usefully_completed(spec, rows):", "if required:",
     "test_optional_unsupported_claim_cannot_create_synthetic_sale", 1),
    ("frozen_requirement_recheck", "shiftwork/orchestrator.py",
     "if context.mission_hash != selection.requirement_set_hash:", "if False:",
     "test_changed_mission_between_selection_check_and_freeze_blocks_run", 1),
    ("inflight_purpose_update", "shiftwork/store/migrations/v6_tables.sql",
     "BEFORE UPDATE OF state, purpose, context_id, shift_id ON runs",
     "BEFORE UPDATE OF state ON runs",
     "test_database_rejects_purpose_change_to_second_inflight_operation", 1),
    ("partial_retry_board", "shiftwork/orchestrator.py",
     "bool(repo.list_outputs(conn, operation_runs[0].id))", "False",
     "test_selected_operation_partial_output_blocks_retry", 1),
    ("existing_v6_trigger_upgrade", "shiftwork/store/migrations/v6_tables.sql",
     "DROP TRIGGER IF EXISTS one_inflight_pivot_operation_update;\nCREATE TRIGGER one_inflight_pivot_operation_update",
     "-- Keep the old trigger\nCREATE TRIGGER IF NOT EXISTS one_inflight_pivot_operation_update",
     "test_existing_v6_database_replaces_old_inflight_update_trigger", 1),
)

EXPECTED_ASSERTIONS = {
    "invalid_selection": "assert 202 == 409",
    "selected_hash": "assert 202 == 409",
    "partial_retry": "DID NOT RAISE LifecycleError",
    "changed_choice_retry": "DID NOT RAISE LifecycleError",
    "changed_context_retry": "DID NOT RAISE LifecycleError",
    "business_write_retry": "DID NOT RAISE LifecycleError",
    "operation_key_replay": "assert (409 == 202)",
    "captured_mission": "captured mission was rejected after file change",
    "experiment_reducer": "DID NOT RAISE ValueError",
    "same_version_resolution": "same version resolved an incident",
    "pinned_rule_resolution": "changed pinned rule resolved an incident",
    "inflight_database": "DID NOT RAISE Exception",
    "inflight_engagement_scope": "DID NOT RAISE IntegrityError",
    "one_success_database": "DID NOT RAISE IntegrityError",
    "mandatory_sale": "assert not any(draft.event_type is LedgerEventType.SALE_COMPLETED for draft in drafts)",
    "frozen_requirement_recheck": "DID NOT RAISE LifecycleError",
    "inflight_purpose_update": "DID NOT RAISE IntegrityError",
    "partial_retry_board": "assert 1 == 0",
    "existing_v6_trigger_upgrade": "DID NOT RAISE IntegrityError",
}


def main() -> int:
    failures = []
    for name, relative, needle, replacement, test, expected_count in CASES:
        path = ROOT / relative
        original = path.read_bytes()
        source = original.decode("utf-8").replace("\r\n", "\n")
        if name == "captured_mission":
            head, tail = source.split("def finalize_selected_operation", 1)
            scope, rest = tail.split("\ndef execute_run_task", 1)
            count = scope.count(needle)
        else:
            count = source.count(needle)
        if count != expected_count:
            print(f"SKIP {name}: anchor count {count}, expected {expected_count}", flush=True)
            failures.append(name)
            continue
        try:
            mutated = (head + "def finalize_selected_operation" + scope.replace(needle, replacement)
                       + "\ndef execute_run_task" + rest
                       if name == "captured_mission" else source.replace(needle, replacement))
            path.write_bytes(mutated.encode("utf-8"))
            command = [sys.executable, "-m", "pytest", TEST + test, "-q", "--tb=short"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                    text=True, timeout=120, check=False)
        finally:
            path.write_bytes(original)
        assertion_lines = [line.strip() for line in result.stdout.splitlines()
                           if line.startswith("E   ")]
        caught = (result.returncode == 1 and f"FAILED {TEST}{test}" in result.stdout
                  and "ERROR " not in result.stdout and "SyntaxError" not in result.stdout
                  and EXPECTED_ASSERTIONS[name] in result.stdout
                  and any(line.startswith(("E   assert", "E   AssertionError", "E   Failed:"))
                          for line in assertion_lines))
        print(f"{'FAIL_CAUGHT' if caught else 'UNPROVEN'} {name}: {test} "
              f"assertion={assertion_lines[:2]}", flush=True)
        if not caught:
            failures.append(name)
            print((result.stdout + result.stderr)[-2200:], flush=True)
    print(f"S18_MUTATIONS caught={len(CASES) - len(failures)} total={len(CASES)} "
          f"unproven={','.join(failures) or 'none'}", flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
