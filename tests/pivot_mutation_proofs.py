"""S10 guard proofs: each source fault must fail one named assertion.

Uses the existing mutation runner, which restores every target byte-identically
and rejects collection errors, crashes, and timeouts as non-proof.

Deliberately excluded, with the measured reason:

- Removing ``BEGIN IMMEDIATE`` from ``open_next_shift`` is caught by the
  concurrent-open assertion only 6 of 8 runs; the other 2 pass because the two
  requests do not overlap. A proof that can pass by luck is not a proof, so
  ``s10_partial_shift_open_committed`` faults the same transaction
  deterministically instead and carries the atomic-shift-open clause.
- Dropping version 5 from the accepted-upgrade list, and dropping the
  ``current == SCHEMA_VERSION`` early return, both surface as ``RuntimeError``
  and ``sqlite3.OperationalError`` rather than as assertion failures. They are
  real fail-closed behavior but incidental catches, so they are not listed here.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
runner_path = ROOT / "tests" / "mutation_proofs.py"
spec = importlib.util.spec_from_file_location("shiftwork_mutation_runner", runner_path)
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

MIGRATION = "tests/store/test_pivot_migration.py"
ROUTES = "tests/api/test_pivot_routes.py"
ATOMICITY = "test_v6_migration_is_atomic_and_idempotent"
PRESERVED = "test_v5_to_v6_preserves_every_legacy_blob_hash_and_row_count"
ADAPTER = "test_legacy_adapter_label_does_not_claim_fresh_live_execution"

CASES = [
    {
        "name": "s10_legacy_starter_insertion",
        "file": "shiftwork/orchestrator.py",
        "old": "        if is_first_shift:\n",
        "new": "        if is_first_shift or is_legacy_first_choice:\n",
        "tests": f"{ROUTES}::test_closed_v5_shift_opens_first_choice_without_invented_selection",
        "expect": "test_closed_v5_shift_opens_first_choice_without_invented_selection",
    },
    {
        "name": "s10_legacy_shift_open_rejected",
        "file": "shiftwork/orchestrator.py",
        "old": "current is not None and current.opening_mode is None and selection is None",
        "new": "current is not None and current.opening_mode == ShiftOpeningMode.STANDARD and selection is None",
        "tests": f"{ROUTES}::test_closed_v5_shift_opens_first_choice_without_invented_selection",
        "expect": "test_closed_v5_shift_opens_first_choice_without_invented_selection",
    },
    {
        "name": "s10_latest_saved_promoted_for_operation",
        "file": "shiftwork/orchestrator.py",
        "old": "        selection, version = _selected_operating_version(conn, shift)\n",
        "new": "        selection, version = _selected_operating_version(conn, shift)\n        version = repo.get_latest_version(conn, shift_id) or version\n",
        "tests": f"{ROUTES}::test_fresh_starter_run_uses_selected_version_after_unselected_freeze",
        "expect": "test_fresh_starter_run_uses_selected_version_after_unselected_freeze",
    },
    {
        "name": "s10_legacy_run_guard_removed",
        "file": "shiftwork/orchestrator.py",
        "old": "        selection, version = _selected_operating_version(conn, shift)\n",
        "new": "        selection = repo.get_latest_operating_selection(conn, shift.engagement_slug)\n        version = repo.get_latest_version_for_engagement(conn, shift.engagement_slug)\n        selection = selection or type('ImplicitSelection', (), {'id': None})()\n",
        "tests": f"{ROUTES}::test_first_choice_prechoice_run_guard_is_controller_enforced",
        "expect": "test_first_choice_prechoice_run_guard_is_controller_enforced",
    },
    {
        "name": "s10_legacy_close_guard_removed",
        "file": "shiftwork/orchestrator.py",
        "old": "        _, version = _selected_operating_version(conn, shift)\n",
        "new": "        version = repo.get_latest_version_for_engagement(conn, shift.engagement_slug)\n",
        "tests": f"{ROUTES}::test_closed_v5_shift_opens_first_choice_without_invented_selection",
        "expect": "test_closed_v5_shift_opens_first_choice_without_invented_selection",
    },
    {
        "name": "s10_partial_shift_open_committed",
        "file": "shiftwork/orchestrator.py",
        "old": "            if slug != config.BOOKSHOP_SLUG:\n",
        "new": "            conn.commit()\n            if slug != config.BOOKSHOP_SLUG:\n",
        "tests": f"{ROUTES}::test_failed_first_shift_open_leaves_no_partial_state",
        "expect": "test_failed_first_shift_open_leaves_no_partial_state",
    },
    {
        "name": "s10_caller_controls_opening_mode",
        "file": "shiftwork/api/routes.py",
        "old": "    body: None = Body(default=None),\n",
        "new": "",
        "tests": f"{ROUTES}::test_first_choice_shift_open_is_atomic_and_caller_cannot_choose_mode",
        "expect": "test_first_choice_shift_open_is_atomic_and_caller_cannot_choose_mode",
    },
    {
        "name": "s10_unknown_schema_version_accepted",
        "file": "shiftwork/store/db.py",
        "old": "    if current not in (0, 2, 3, 4, 5, SCHEMA_VERSION):",
        "new": "    if False:",
        "tests": f"{MIGRATION}::test_unknown_schema_version_fails_closed",
        "expect": "test_unknown_schema_version_fails_closed",
    },
    {
        "name": "s10_migration_transaction_removed",
        "file": "shiftwork/store/db.py",
        "old": "    conn.execute(\"BEGIN IMMEDIATE\")\n    try:\n",
        "new": "    try:\n",
        "tests": f"{MIGRATION}::{ATOMICITY}",
        "expect": ATOMICITY,
    },
    {
        "name": "s10_version_marker_not_written",
        "file": "shiftwork/store/db.py",
        "old": "        conn.execute(f\"PRAGMA user_version = {SCHEMA_VERSION}\")\n    except BaseException:",
        "new": "        pass\n    except BaseException:",
        "tests": f"{MIGRATION}::{ATOMICITY}",
        "expect": ATOMICITY,
    },
    {
        "name": "s10_rerun_reapplies_v6_ddl",
        "file": "shiftwork/store/db.py",
        "old": "    if current == SCHEMA_VERSION:\n        return\n",
        "new": "    if current == SCHEMA_VERSION:\n        conn.execute(\"CREATE TABLE IF NOT EXISTS s10_rerun_marker (x TEXT)\")\n        return\n",
        "tests": f"{MIGRATION}::{ATOMICITY}",
        "expect": ATOMICITY,
    },
    {
        "name": "s10_legacy_adapter_column_rewritten",
        "file": "shiftwork/store/migrations/v6.sql",
        "old": "UPDATE runs SET evidence_mode = 'RECORDED_INSPECTION' WHERE adapter = 'recorded';",
        "new": "UPDATE runs SET evidence_mode = 'RECORDED_INSPECTION', adapter = 'recorded-inspected' WHERE adapter = 'recorded';",
        "tests": f"{MIGRATION}::{PRESERVED}",
        "expect": PRESERVED,
    },
    {
        "name": "s10_trusted_local_labelled_isolated_live",
        "file": "shiftwork/store/migrations/v6.sql",
        "old": "UPDATE runs SET evidence_mode = 'TRUSTED_LOCAL' WHERE adapter = 'local_process';",
        "new": "UPDATE runs SET evidence_mode = 'ISOLATED_LIVE' WHERE adapter = 'local_process';",
        "tests": f"{MIGRATION}::{ADAPTER}[local_process-TRUSTED_LOCAL]",
        "expect": f"{ADAPTER}[local_process-TRUSTED_LOCAL]",
    },
    {
        "name": "s10_tokenfactory_gains_evidence_mode",
        "file": "shiftwork/store/migrations/v6.sql",
        "old": "UPDATE runs SET evidence_mode = 'RECORDED_INSPECTION' WHERE adapter = 'recorded';",
        "new": "UPDATE runs SET evidence_mode = 'RECORDED_INSPECTION' WHERE adapter IN ('recorded','tokenfactory');",
        "tests": f"{MIGRATION}::{ADAPTER}[tokenfactory-None]",
        "expect": f"{ADAPTER}[tokenfactory-None]",
    },
]


def main() -> int:
    results = [runner.run_mutation(case) for case in CASES]
    for result in results:
        print(
            result["name"], result["status"],
            f"restored={result.get('sha256_restored', False)}",
            result.get("detail", result.get("reason", "")),
        )
    return 0 if all(result["status"] == "FAIL_CAUGHT" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
