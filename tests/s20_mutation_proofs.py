"""Named S20 mutations for the inheritance, ancestry and later-condition guards.

Every row faults one guard of the Slice 20 code and must fail its named test at
an assertion, never as a crash, a timeout or a syntax error. The scope column
narrows a replacement to one function so a shared statement elsewhere in the
file is not touched, and each target file is restored byte-for-byte afterwards.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORCH = "shiftwork/orchestrator.py"
CMP = "shiftwork/comparison_flow.py"
ROUTES = "tests/api/test_pivot_routes.py::test_later_condition_experiment_shape_is_controller_enforced"
LATER = "tests/orchestrator/test_selection_operation.py::test_later_alternative_experiment_does_not_rewrite_original_history"
WORLDS = "tests/orchestrator/test_selection_operation.py::test_later_condition_needs_an_observed_change_and_its_own_world"
INHERIT = "tests/orchestrator/test_close_inheritance.py::test_next_shift_inherits_selection_rationale_alternative_tests_and_limits"
ANCESTRY = "tests/orchestrator/test_close_inheritance.py::test_freeze_ancestry_follows_the_draft_base_and_explicit_restore"
ATOMIC = "tests/orchestrator/test_selection_operation.py::test_a_fault_mid_later_reservation_leaves_no_partial_comparison"
CASES = (
    ("later_choice_guard_removed", CMP,
     'if selection.kind != "LEARNER_CHOICE":',
     "if False:",
     ROUTES, 1, "create_later_condition_comparison"),
    ("observed_run_guard_removed", CMP,
     "        if (\n"
     "            observed_run.purpose is not RunPurpose.OPERATION\n"
     "            or observed_run.state is not RunState.FINALIZED\n"
     "            or observed_run.shift_id != shift.id\n"
     "            or observed_run.selection_id != selection.id\n"
     "            or observed_run.context_id is None\n"
     "        ):",
     "        if False:",
     LATER, 1, "create_later_condition_comparison"),
    ("observed_run_shift_clause_removed", CMP,
     "            or observed_run.shift_id != shift.id\n",
     "",
     LATER, 1, "create_later_condition_comparison"),
    ("observed_run_state_clause_removed", CMP,
     "            or observed_run.state is not RunState.FINALIZED\n",
     "",
     LATER, 1, "create_later_condition_comparison"),
    ("normal_condition_guard_removed", CMP,
     'if observed_context.condition.kind == "normal":',
     "if False:",
     WORLDS, 1, "create_later_condition_comparison"),
    ("dependency_variation_guard_removed", CMP,
     "    if changed:",
     "    if False:",
     WORLDS, 1, "_require_dependency_only_variation"),
    # Added 2026-10-01: the key-set limb lacked a failing-capable test. The
    # world test now runs a differently shaped reviewed world and requires the
    # shape refusal by name, before the workload manifest is ever read.
    ("later_world_shape_check_removed", CMP,
     "    if set(reviewed) != set(observed):\n",
     "    if False:\n",
     WORLDS, 1, "_require_dependency_only_variation"),
    ("observed_context_not_linked", CMP,
     "        repo.insert_observed_context(\n"
     "            conn, experiment.id, observed_run.id, observed_context.id, experiment.created_at\n"
     "        )",
     "        pass",
     LATER, 1, "create_later_condition_comparison"),
    ("later_cap_removed", CMP,
     "        if used >= LATER_COMPARISONS_PER_SHIFT:",
     "        if False:",
     LATER, 1, "create_later_condition_comparison"),
    ("later_idempotency_replay_removed", CMP,
     "        replay = repo.get_experiment_by_client_request_id(conn, client_request_id)",
     "        replay = None",
     LATER, 1, "create_later_condition_comparison"),
    ("later_versions_swapped", CMP,
     '        versions = {"A": selected_version, "B": retained_version}',
     '        versions = {"A": retained_version, "B": selected_version}',
     LATER, 1, "create_later_condition_comparison"),
    ("later_workloads_flattened", CMP,
     "            workload = workloads[pair - 1]",
     "            workload = workloads[0]",
     LATER, 1, "create_later_condition_comparison"),
    ("later_context_bytes_from_config", CMP,
     "        snapshot_bytes = base64.b64decode(observed_context.public_data_bytes_base64, validate=True)",
     "        snapshot_bytes = config.PIVOT_COMPARE_STATE.read_bytes()",
     LATER, 1, "create_later_condition_comparison"),
    # The rollback guard is byte-identical in the qualifying body this one was
    # copied from, so the scope is what keeps the two proofs separate: the
    # qualifying atomicity row cannot see this copy and this row cannot see that.
    ("later_reservation_rollback_removed", CMP,
     "    except Exception:\n        conn.rollback()\n        raise\n    return experiment\n",
     "    except Exception:\n        raise\n    return experiment\n",
     ATOMIC, 1, "create_later_condition_comparison"),
    ("inherit_base_from_newest_save", ORCH,
     "    base_version_id = repo.get_draft_base_version_id(conn, shift_id)",
     "    base_version_id = None",
     ANCESTRY, 1, "freeze_version"),
    ("restore_base_not_set", ORCH,
     "    repo.set_draft_base_version(conn, shift_id, version.id)",
     "    pass",
     ANCESTRY, 1, "restore_version_to_draft"),
    ("restore_closed_shift_allowed", ORCH,
     "    shift = _require_open_shift(conn, shift_id)",
     "    shift = _require_shift(conn, shift_id)",
     ANCESTRY, 1, "restore_version_to_draft"),
    ("inheritance_projection_dropped", ORCH,
     '        "inherited_requirements": inherited_requirements,',
     '        "inherited_requirements": None,',
     INHERIT, 1, "board_snapshot"),
    # Added 2026-10-01: the observed-context link's two database triggers had no
    # failing-capable test. Both are now faulted independently against the
    # migration test that owns the append-once rule for that table.
    ("observed_context_update_trigger_removed", "shiftwork/store/migrations/v6_tables.sql",
     "BEFORE UPDATE ON experiment_observed_contexts\n"
     "BEGIN\n"
     "    SELECT RAISE(ABORT, 'an observed-context reference is never rewritten');\n"
     "END;",
     "BEFORE UPDATE ON experiment_observed_contexts\n"
     "BEGIN\n"
     "    SELECT 1;\n"
     "END;",
     "tests/store/test_pivot_migration.py"
     "::test_observed_context_references_reject_update_and_delete",
     1, None),
    ("observed_context_delete_trigger_removed", "shiftwork/store/migrations/v6_tables.sql",
     "BEFORE DELETE ON experiment_observed_contexts\n"
     "BEGIN\n"
     "    SELECT RAISE(ABORT, 'an observed-context reference is never deleted');\n"
     "END;",
     "BEFORE DELETE ON experiment_observed_contexts\n"
     "BEGIN\n"
     "    SELECT 1;\n"
     "END;",
     "tests/store/test_pivot_migration.py"
     "::test_observed_context_references_reject_update_and_delete",
     1, None),
)

EXPECTED_ASSERTIONS = {
    "later_choice_guard_removed": "assert 404 == 409",
    "observed_run_guard_removed": "assert 'finalized operation' in",
    "observed_run_shift_clause_removed": "assert 'finalized operation' in",
    "observed_run_state_clause_removed": "assert 'finalized operation' in",
    "normal_condition_guard_removed": "assert 202 == 409",
    "dependency_variation_guard_removed": "assert 202 == 409",
    "later_world_shape_check_removed": "is not the reviewed comparison world",
    "observed_context_not_linked": "assert None ==",
    "later_cap_removed": "must be refused by the per-shift cap",
    "later_idempotency_replay_removed": "assert 409 == 202",
    "later_versions_swapped": "assert 'NOT_COMPARABLE' == 'COMPLETE'",
    "later_workloads_flattened": "assert 'NOT_COMPARABLE' == 'COMPLETE'",
    "later_context_bytes_from_config": "the observed context bytes do not verify",
    "later_reservation_rollback_removed": "left a partial row behind",
    "inherit_base_from_newest_save": "must descend from the exact selection",
    "restore_base_not_set": "must record A as the parent",
    "restore_closed_shift_allowed": "DID NOT RAISE",
    "inheritance_projection_dropped": "assert None is not None",
    "observed_context_update_trigger_removed": "DID NOT RAISE",
    "observed_context_delete_trigger_removed": "DID NOT RAISE",
}


def _scoped(source: str, needle: str, replacement: str, scope: str | None) -> tuple[str, int]:
    """Apply one replacement, optionally restricted to one function's body."""
    if scope is None:
        return source.replace(needle, replacement), source.count(needle)
    head, tail = source.split(f"def {scope}(", 1)
    body, rest = tail.split("\ndef ", 1)
    return (head + f"def {scope}(" + body.replace(needle, replacement) + "\ndef " + rest,
            body.count(needle))


def main() -> int:
    wanted = {argument for argument in sys.argv[1:] if not argument.startswith("-")}
    rows = [case for case in CASES if not wanted or case[0] in wanted]
    failures = []
    for name, relative, needle, replacement, test, expected_count, scope in rows:
        path = ROOT / relative
        original = path.read_bytes()
        source = original.decode("utf-8").replace("\r\n", "\n")
        mutated, count = _scoped(source, needle, replacement, scope)
        if count != expected_count:
            print(f"SKIP {name}: anchor count {count}, expected {expected_count}", flush=True)
            failures.append(name)
            continue
        try:
            path.write_bytes(mutated.encode("utf-8"))
            command = [sys.executable, "-m", "pytest", test, "-q", "--tb=short"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                    text=True, timeout=300, check=False)
        finally:
            path.write_bytes(original)
        assertion_lines = [line.strip() for line in result.stdout.splitlines()
                           if line.startswith("E   ")]
        caught = (result.returncode == 1 and f"FAILED {test}" in result.stdout
                  and "ERROR " not in result.stdout and "SyntaxError" not in result.stdout
                  and EXPECTED_ASSERTIONS[name] in result.stdout
                  and any(line.startswith(("E   assert", "E   AssertionError", "E   Failed:"))
                          for line in assertion_lines))
        print(f"{'FAIL_CAUGHT' if caught else 'UNPROVEN'} {name}: {test.split('::')[-1]} "
              f"assertion={assertion_lines[:2]}", flush=True)
        if not caught:
            failures.append(name)
            print((result.stdout + result.stderr)[-2200:], flush=True)
    print(f"S20_MUTATIONS caught={len(rows) - len(failures)} total={len(rows)} "
          f"unproven={','.join(failures) or 'none'}", flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
