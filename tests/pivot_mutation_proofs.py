"""S10 and S11 guard proofs: each source fault must fail one named assertion.

Uses the existing mutation runner, which restores every target byte-identically
and rejects collection errors, crashes, and timeouts as non-proof.

Deliberately excluded, with the measured reason:

- Removing ``BEGIN IMMEDIATE`` from ``open_next_shift`` is caught by the
  concurrent-open assertion only 6 of 8 runs; the other 2 pass because the two
  requests do not overlap. A proof that can pass by luck is not a proof, so
  ``s10_partial_shift_open_committed`` faults the same transaction
  deterministically instead and carries the atomic-shift-open clause.
- Dropping version 5 from the accepted-upgrade list surfaces as ``RuntimeError``
  rather than as an assertion failure. It is real fail-closed behavior but an
  incidental catch, so it is not listed here.

Slice 11 moved two S10 anchors without weakening either assertion. The
``current == SCHEMA_VERSION`` early return became a reconciliation call, so
``s10_migration_transaction_removed`` now anchors past ``try:`` to stay unique
against ``_complete_v6_tables``'s own transaction, and
``s10_rerun_reapplies_v6_ddl`` injects its marker table into the idempotent
script instead of the removed early return. Both still fault
``test_v6_migration_is_atomic_and_idempotent``.
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
TASKCONTRACT = "tests/domain/test_task_contract.py"
CUSTOMER = "tests/domain/test_customer_answer.py"
EVALUATOR = "tests/evaluator/test_evaluator.py"
LIFECYCLE = "tests/orchestrator/test_experiment_lifecycle.py"
ASSIST = "tests/orchestrator/test_investigation_assist.py"
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
        # Anchored past `try:` because Slice 11 gave _complete_v6_tables its own
        # BEGIN IMMEDIATE. The shorter anchor matched both and the runner skipped
        # the case as ambiguous, which would have silently dropped an accepted S10
        # proof. The assertion this faults is unchanged.
        "old": "    conn.execute(\"BEGIN IMMEDIATE\")\n    try:\n        if current == 0:\n",
        "new": "    try:\n        if current == 0:\n",
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
        # Re-anchored for Slice 11: the `current == SCHEMA_VERSION` early return it
        # faulted is now a reconciliation call, so the mutation injects a marker
        # table into the idempotent script instead. Same proof: a rerun that
        # changes sqlite_master fails the idempotency assertion.
        "old": '    script = MIGRATION_V6_TABLES_PATH.read_text(encoding="utf-8")\n',
        "new": '    script = MIGRATION_V6_TABLES_PATH.read_text(encoding="utf-8") + "CREATE TABLE IF NOT EXISTS s10_rerun_marker (x TEXT);"\n',
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
    # --- Slice 11: task-aware assessment, envelope and v6 reconciliation ------
    {
        "name": "s11_v6_reconcile_skipped",
        "file": "shiftwork/store/db.py",
        "old": "    if current == SCHEMA_VERSION:\n        _complete_v6_tables(conn)\n        return\n",
        "new": "    if current == SCHEMA_VERSION:\n        return\n",
        "tests": f"{MIGRATION}::test_already_v6_database_gains_missing_tables_without_touching_history",
        "expect": "test_already_v6_database_gains_missing_tables_without_touching_history",
    },
    {
        "name": "s11_envelope_accepts_independent_prose",
        "file": "shiftwork/domain/task_contract.py",
        "old": '_FROZEN = ConfigDict(frozen=True, extra="forbid")',
        "new": '_FROZEN = ConfigDict(frozen=True, extra="ignore")',
        "tests": f"{TASKCONTRACT}::test_independent_prose_field_is_rejected[customer_text]",
        "expect": "test_independent_prose_field_is_rejected[customer_text]",
    },
    {
        "name": "s11_record_conflict_treated_as_agreed",
        "file": "shiftwork/domain/task_contract.py",
        "old": "    if len(identities) > 1:",
        "new": "    if False:",
        "tests": f"{TASKCONTRACT}::test_conflicting_values_are_unsupported_even_when_the_newest_is_cited",
        "expect": "test_conflicting_values_are_unsupported_even_when_the_newest_is_cited",
    },
    {
        "name": "s11_collection_conflict_rule_removed",
        "file": "shiftwork/domain/task_contract.py",
        "old": "    return isinstance(quantity, int) and not isinstance(quantity, bool) and quantity <= 0",
        "new": "    return False",
        "tests": f"{TASKCONTRACT}::test_true_collection_with_zero_stock_is_conflicting_necessary_information",
        "expect": "test_true_collection_with_zero_stock_is_conflicting_necessary_information",
    },
    {
        "name": "s11_missing_required_task_accepted",
        "file": "shiftwork/evaluator/evaluator.py",
        "old": "    codes = (ReasonCode.REQUIRED_TASK_MISSING,) if task.required else ()",
        "new": "    codes = ()",
        "tests": f"{EVALUATOR}::test_true_price_without_collection_or_alternative_fails_required_tasks",
        "expect": "test_true_price_without_collection_or_alternative_fails_required_tasks",
    },
    {
        "name": "s11_request_completion_ignores_required_tasks",
        "file": "shiftwork/evaluator/evaluator.py",
        # Pointed at the case where every mandatory rule passes. Against the
        # price-only starter this mutation was NOT_CAUGHT, because a missing
        # required task already trips the mandatory_pass short-circuit first and
        # two checks catching one fault proves neither.
        "old": "        for task in spec.tasks\n        if task.required\n    )",
        "new": "        for task in spec.tasks\n        if False\n    )",
        "tests": f"{EVALUATOR}::test_justified_fallbacks_on_every_required_task_do_not_complete_the_request",
        "expect": "test_justified_fallbacks_on_every_required_task_do_not_complete_the_request",
    },
    {
        "name": "s11_result_labelled_with_the_wrong_entity_accepted",
        "file": "shiftwork/evaluator/evaluator.py",
        # The result-level limb only. Against the hardback-collection case this was
        # NOT_CAUGHT, because that case's claims are also mislabelled and the
        # claim-level limb below caught the same fault.
        "old": "    if result.entity_ref != task.requested_entity_ref:\n        return [ReasonCode.WRONG_ENTITY]",
        "new": "    if False:\n        return [ReasonCode.WRONG_ENTITY]",
        "tests": f"{EVALUATOR}::test_a_result_labelled_with_the_wrong_entity_fails_even_when_its_claims_are_right",
        "expect": "test_a_result_labelled_with_the_wrong_entity_fails_even_when_its_claims_are_right",
    },
    {
        "name": "s11_claim_about_the_wrong_entity_accepted",
        "file": "shiftwork/evaluator/evaluator.py",
        "old": "        for claim in result.claims\n        if claim.entity_ref != task.requested_entity_ref\n    ]",
        "new": "        for claim in result.claims\n        if False\n    ]",
        "tests": f"{EVALUATOR}::test_a_true_price_for_the_wrong_edition_is_unsupported",
        "expect": "test_a_true_price_for_the_wrong_edition_is_unsupported",
    },
    {
        "name": "s11_unsupported_claim_value_accepted",
        "file": "shiftwork/evaluator/evaluator.py",
        "old": "    if group.value != claim.value:\n        return False",
        "new": "    if group.value != claim.value:\n        return True",
        "tests": f"{EVALUATOR}::test_an_unsupported_claim_value_fails",
        "expect": "test_an_unsupported_claim_value_fails",
    },
    {
        "name": "s11_fallback_always_justified",
        "file": "shiftwork/evaluator/evaluator.py",
        "old": '    if code == "MISSING_ENTITY_DETAIL":\n        return False',
        "new": '    if code == "MISSING_ENTITY_DETAIL":\n        return True',
        "tests": f"{EVALUATOR}::test_an_unneeded_clarification_is_unjustified",
        "expect": "test_an_unneeded_clarification_is_unjustified",
    },
    {
        "name": "s11_missing_capture_becomes_a_justified_refusal",
        "file": "shiftwork/evaluator/evaluator.py",
        "old": "                outcome=TaskOutcome.MISSING_OUTPUT,\n                mandatory_pass=False,\n                reason_codes=(ReasonCode.MISSING_EXECUTION_EVIDENCE,),",
        "new": "                outcome=TaskOutcome.JUSTIFIED_REFUSAL,\n                mandatory_pass=True,\n                reason_codes=(),",
        "tests": f"{EVALUATOR}::test_missing_capture_is_missing_evidence_not_refusal",
        "expect": "test_missing_capture_is_missing_evidence_not_refusal",
    },
    {
        "name": "s11_not_applicable_self_declared_by_the_service",
        "file": "shiftwork/evaluator/evaluator.py",
        "old": "    if date is None or not _collection_independently_confirmed(\n        snapshot, mission, task.requested_entity_ref, date\n    ):",
        "new": "    if False:",
        "tests": f"{EVALUATOR}::test_not_applicable_needs_independently_confirmed_collection",
        "expect": "test_not_applicable_needs_independently_confirmed_collection",
    },
    {
        "name": "s11_referral_borrows_another_candidates_data_problem",
        "file": "shiftwork/evaluator/evaluator.py",
        "old": '    if "QUALIFIES" in classifications.values():\n        return False',
        "new": '    if "QUALIFIES" in classifications.values():\n        return True',
        "tests": f"{EVALUATOR}::test_a_referral_cannot_borrow_another_candidates_data_problem",
        "expect": "test_a_referral_cannot_borrow_another_candidates_data_problem",
    },
    {
        "name": "s11_availability_answer_creates_a_commitment",
        "file": "shiftwork/evaluator/evaluator.py",
        "old": "    if result.commitment_ref is not None and task.kind in _AVAILABILITY_KINDS:",
        "new": "    if False:",
        "tests": f"{EVALUATOR}::test_a_collection_answer_may_not_create_a_commitment",
        "expect": "test_a_collection_answer_may_not_create_a_commitment",
    },
    {
        "name": "s11_renderer_authors_its_own_fallback_sentence",
        "file": "shiftwork/domain/customer_answer.py",
        "old": "    return explanation.customer_text",
        "new": "    return \"Your order is ready for collection.\"",
        "tests": f"{CUSTOMER}::test_a_fallback_renders_the_missions_own_public_text",
        "expect": "test_a_fallback_renders_the_missions_own_public_text",
    },
    {
        "name": "s11_renderer_invents_a_price",
        "file": "shiftwork/domain/customer_answer.py",
        "old": "    return f\"{symbol}{units}.{remainder:02d}\"",
        "new": "    return f\"{symbol}0.00\"",
        "tests": f"{CUSTOMER}::test_the_recorded_starter_renders_only_the_price_it_answered",
        "expect": "test_the_recorded_starter_renders_only_the_price_it_answered",
    },
    {
        "name": "s11_renderer_leaks_an_unknown_entity_ref",
        "file": "shiftwork/domain/customer_answer.py",
        "old": "    if entity is None:\n        raise ServiceResponseInvalid(\n            f\"the response names entity {entity_ref!r}, which the frozen public state does not define\"\n        )",
        "new": "    if entity is None:\n        return ShopEntity(title=entity_ref, edition=\"unknown\", genre=\"unknown\")",
        "tests": f"{CUSTOMER}::test_an_unknown_entity_fails_closed_instead_of_leaking_its_ref",
        "expect": "test_an_unknown_entity_fails_closed_instead_of_leaking_its_ref",
    },
    # --- Slice 11: the public diagnostic experiment and its boundaries ---------
    {
        "name": "s11_diagnostic_reserves_a_protected_case",
        "file": "shiftwork/orchestrator.py",
        "old": "        protected_reservation_id=None,",
        "new": "        protected_reservation_id=\"reservation-0001\",",
        "tests": f"{LIFECYCLE}::test_the_frozen_context_pins_the_reviewed_bytes_and_reserves_nothing",
        "expect": "test_the_frozen_context_pins_the_reviewed_bytes_and_reserves_nothing",
    },
    {
        "name": "s11_diagnostic_candidate_pin_removed",
        "file": "shiftwork/orchestrator.py",
        "old": '        if version.content_hash != config.TRUSTED_LOCAL_FIXTURES["pivot_starter"][0]:',
        "new": "        if False:",
        "tests": f"{LIFECYCLE}::test_only_the_pinned_reviewed_starter_is_executable",
        "expect": "test_only_the_pinned_reviewed_starter_is_executable",
    },
    {
        "name": "s11_diagnostic_budget_ignored",
        "file": "shiftwork/orchestrator.py",
        "old": "        if used >= DIAGNOSTIC_EXPERIMENTS_PER_SHIFT:",
        "new": "        if False:",
        "tests": f"{LIFECYCLE}::test_the_diagnostic_budget_is_two_per_shift",
        "expect": "test_the_diagnostic_budget_is_two_per_shift",
    },
    {
        "name": "s11_null_investigation_bootstrap_allowed",
        "file": "shiftwork/orchestrator.py",
        "old": "        if investigation_id is None:\n            # The only null-investigation experiment is the no-source legacy",
        "new": "        if False:\n            # The only null-investigation experiment is the no-source legacy",
        "tests": f"{LIFECYCLE}::test_a_null_investigation_bootstrap_is_denied_and_reserves_nothing",
        "expect": "test_a_null_investigation_bootstrap_is_denied_and_reserves_nothing",
    },
    {
        "name": "s11_diagnostic_spends_the_operation_budget",
        "file": "shiftwork/store/repo.py",
        "old": '            "SELECT COUNT(*) AS n FROM runs WHERE shift_id = ? AND purpose != ?",',
        "new": '            "SELECT COUNT(*) AS n FROM runs WHERE shift_id = ? AND purpose != ? OR 1 = 1",',
        "tests": f"{LIFECYCLE}::test_the_diagnostic_does_not_spend_the_operation_budget",
        "expect": "test_the_diagnostic_does_not_spend_the_operation_budget",
    },
    {
        "name": "s11_diagnostic_claims_recorded_inspection",
        "file": "shiftwork/orchestrator.py",
        "old": "            evidence_mode=EvidenceMode.TRUSTED_LOCAL,",
        "new": "            evidence_mode=EvidenceMode.RECORDED_INSPECTION,",
        "tests": f"{LIFECYCLE}::test_the_pinned_starter_fails_the_request_where_it_actually_fails",
        "expect": "test_the_pinned_starter_fails_the_request_where_it_actually_fails",
    },
    {
        "name": "s11_completion_counted_without_the_required_tasks",
        "file": "shiftwork/orchestrator.py",
        "old": "            if evaluator.request_usefully_completed(spec, request_assessments):\n                completed += 1",
        "new": "            completed += 1",
        "tests": f"{LIFECYCLE}::test_the_pinned_starter_fails_the_request_where_it_actually_fails",
        "expect": "test_the_pinned_starter_fails_the_request_where_it_actually_fails",
    },
    {
        "name": "s11_assessment_reads_the_live_fixture",
        "file": "shiftwork/orchestrator.py",
        "old": "        snapshot_bytes = base64.b64decode(context.public_data_bytes_base64)\n        mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))",
        "new": "        snapshot_bytes = base64.b64decode(context.public_data_bytes_base64)\n        mission = task_contract.load_mission(config.PIVOT_MISSION)",
        "tests": f"{LIFECYCLE}::test_a_fixture_edit_after_reservation_cannot_rewrite_the_assessment",
        "expect": "test_a_fixture_edit_after_reservation_cannot_rewrite_the_assessment",
    },
    {
        "name": "s11_help_accepts_a_foreign_shifts_investigation",
        "file": "shiftwork/orchestrator.py",
        "old": '    if investigation.shift_id != shift.id:\n        raise LifecycleError(\n            "conflict", "diagnostic help must reference an investigation owned by this shift"\n        )',
        "new": '    if False:\n        raise LifecycleError(\n            "conflict", "diagnostic help must reference an investigation owned by this shift"\n        )',
        "tests": f"{ASSIST}::test_help_with_another_open_shifts_investigation_is_refused_before_the_gateway",
        "expect": "test_help_with_another_open_shifts_investigation_is_refused_before_the_gateway",
    },
    {
        "name": "s11_diagnostic_accepts_a_foreign_shifts_investigation",
        "file": "shiftwork/orchestrator.py",
        "old": '        if investigation.shift_id != shift.id:\n            raise LifecycleError(\n                "conflict", "a diagnostic must cite an investigation owned by this shift"\n            )',
        "new": '        if False:\n            raise LifecycleError(\n                "conflict", "a diagnostic must cite an investigation owned by this shift"\n            )',
        "tests": f"{LIFECYCLE}::test_an_investigation_from_another_shift_cannot_authorise_a_diagnostic",
        "expect": "test_an_investigation_from_another_shift_cannot_authorise_a_diagnostic",
    },
    {
        "name": "s11_absent_assist_gateway_claims_success",
        "file": "shiftwork/orchestrator.py",
        "old": '    raise AssistGatewayUnavailable(\n        f"no assist gateway exists yet, so a {role.value} cannot be produced; "\n        "diagnostic help arrives with Slice 14"\n    )',
        "new": "    return None",
        "tests": f"{ASSIST}::test_diagnostic_help_needs_an_investigation_and_is_denied_anyway",
        "expect": "test_diagnostic_help_needs_an_investigation_and_is_denied_anyway",
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
