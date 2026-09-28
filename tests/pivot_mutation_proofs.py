"""S10, S11 and S15 guard proofs: each source fault must fail one named assertion.

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
- A write-removal fault for the protected-case snapshot write has no row: every
  reachable shape surfaces as the reservation readback's incidental
  ``InvalidSealedCase`` rather than as an assertion (the pre-repair run's
  ``s15_protected_snapshot_write_removed``, kept in
  ``docs/plans/shiftwork/evidence/slice15-mutation-rerun-2026-09-28-pre-repair.txt``).
  ``s15_protected_snapshot_immutability_removed`` faults the
  ``protected_case_snapshots_no_update`` trigger against the same named test
  instead, caught as ``Failed: DID NOT RAISE IntegrityError``.
- The slot-count limb ``workload.request_count != slot.request_count`` has no
  row: with the limb removed, the ``[slot_count]`` tamper is caught only by the
  comparison view's private-material guard raising ``LifecycleError``
  ("public comparison evidence contains private material"), measured
  2026-09-28 as ``CAUGHT_INCIDENTAL``, so no named test fails and the limb has
  no failing-capable shape. ``[slot_count]`` stays as a fail-closed scenario.

Repair round 2026-09-28. The first full run under the hardened driver reported
92 of 96 rows ``FAIL_CAUGHT`` and found that four older rows had lost
proof-grade status when the protected-phase guards landed: the snapshot
write-removal row turned incidental, the manifest count row was masked by the
protected-ordinal tie, and both slot-binding rows were masked for every context
tamper by the frozen context-hash re-verification. The rows were re-anchored:
``s15_slot_binding_not_reverified`` now faults only the slot-hash limb against
``[slot_hash]``; ``s15_request_line_identity_unchecked`` (renamed from
``s15_slot_count_binding_not_reverified``) faults the request-line identity
check against ``[wrong_request_id_with_recomputed_pin]``; the manifest count row
names the pin-consistent ``[extra_request_with_recomputed_pin]`` parameter; and
the new ``s15_frozen_context_hash_not_reverified`` faults the context-hash
check itself against ``[swap_bytes]``, the branch every other context tamper
rides on. Verified after the repairs: all 97 anchors present exactly once; each
repaired or new row individually ``FAIL_CAUGHT restored=True``; the full 97-row
run exits 0 with 97 of 97 ``FAIL_CAUGHT`` and every target restored
(``docs/plans/shiftwork/evidence/slice15-mutation-rerun-2026-09-28.txt``).

Slice 11 moved two S10 anchors without weakening either assertion. The
``current == SCHEMA_VERSION`` early return became a reconciliation call, so
``s10_migration_transaction_removed`` now anchors past ``try:`` to stay unique
against ``_complete_v6_tables``'s own transaction, and
``s10_rerun_reapplies_v6_ddl`` injects its marker table into the idempotent
script instead of the removed early return. Both still fault
``test_v6_migration_is_atomic_and_idempotent``.

Re-anchoring round 2026-09-29. Uncommitted S16 work moved six anchors in
``shiftwork/orchestrator.py`` and a line-ending regime change hid two more, so the
run returned 89 of 97 with eight ``SKIP pattern not found`` rows. The diagnosis and
the 2/6 split are recorded in
``docs/plans/shiftwork/evidence/slice16-anchor-rot-run-2026-09-29.txt``; the two
ending-rot rows were fixed in the runner's CRLF handling, not here. The six moved
rows were re-anchored onto the current bytes with their faults unchanged:
``s15_missing_capture_success_flag`` still drops the ``capture_complete`` limb, now
past the ``retired`` reservation check; ``s15_protected_phase_skipped`` still forces
the protected phase off, now against the ``public_complete and ... == "ACTIVE"``
condition; ``s15_protected_counts_before_terminal`` still forces the terminal guard
open, now over ``_comparison_outcome``; and both frozen-order rows keep their
authored mutations against the refreshed block.

``s15_eligible_derived`` changed DIRECTION and must not be flipped back. S16 made
``eligible`` derived from ``outcome.eligibility`` and the compare-station scenario
derives ``True``, so pinning ``True`` mutated nothing and the row correctly reported
``NOT_CAUGHT``. It now pins ``False``, which breaks the named test's
``view["eligible"] == any(item["eligible"] ...)`` and is the failing-capable
direction. ``RESULTS_LOG`` also moved off the committed S15 evidence file, because
``main()`` truncates it on every run and a single run destroyed the recorded
97-of-97 record.
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
        "name": "s15_draft_manifest_review_gate_removed",
        "file": "shiftwork/orchestrator.py",
        "old": '    if data.get("review_status") != "OPERATOR_SEALED" or data.get("sealed_payload_sha256") != digest:\n',
        "new": '    if False:\n',
        "tests": f"{LIFECYCLE}::test_a_status_label_without_an_exact_seal_cannot_admit_material",
        "expect": "test_a_status_label_without_an_exact_seal_cannot_admit_material",
    },
    {
        "name": "s15_draft_protected_review_gate_removed",
        "file": "shiftwork/sealed/store.py",
        "old": '    if data.get("review_status") != "OPERATOR_SEALED" or data.get("sealed_payload_sha256") != digest:\n',
        "new": '    if False:\n',
        "tests": f"{LIFECYCLE}::test_a_status_label_without_an_exact_seal_cannot_admit_material",
        "expect": "test_a_status_label_without_an_exact_seal_cannot_admit_material",
    },
    {
        "name": "s15_six_variant_admission_removed",
        "file": "shiftwork/sealed/rotation.py",
        "old": '    if len(cases) < 6 or len({variant_ref(case) for case in cases}) < 6:\n',
        "new": '    if False:\n',
        "tests": f"{LIFECYCLE}::test_three_available_variants_are_not_a_six_variant_inventory",
        "expect": "test_three_available_variants_are_not_a_six_variant_inventory",
    },
    {
        "name": "s15_protected_snapshot_immutability_removed",
        "file": "shiftwork/store/migrations/v6_tables.sql",
        "old": "CREATE TRIGGER IF NOT EXISTS protected_case_snapshots_no_update\r\nBEFORE UPDATE ON protected_case_snapshots\r\nBEGIN\r\n    SELECT RAISE(ABORT, 'protected case snapshots are immutable');\r\nEND;",
        "new": "",
        "tests": f"{LIFECYCLE}::test_reserved_protected_cases_survive_later_edits_to_the_authored_file",
        "expect": "test_reserved_protected_cases_survive_later_edits_to_the_authored_file",
    },
    {
        "name": "s15_missing_capture_success_flag",
        "file": "shiftwork/orchestrator.py",
        "old": '        retired = repo.get_exposure_reservation(conn, reservation.id).state != "ACTIVE"\n        failure = (ExecutorFailure.INTERNAL if retired else public_result.failure\n                   or (protected_result.failure if protected_result else None)\n                   or (None if capture_complete else ExecutorFailure.CAPTURE_TRUNCATED))\n',
        "new": '        retired = repo.get_exposure_reservation(conn, reservation.id).state != "ACTIVE"\n        failure = (ExecutorFailure.INTERNAL if retired else public_result.failure\n                   or (protected_result.failure if protected_result else None))\n',
        "tests": f"{LIFECYCLE}::test_success_flag_without_captures_fails_the_slot_without_refunding_exposure",
        "expect": "test_success_flag_without_captures_fails_the_slot_without_refunding_exposure",
    },
    {
        "name": "s15_starting_ledger_state_placeholder",
        "file": "shiftwork/orchestrator.py",
        "old": '            "ledger_event_count": len(events),\n',
        "new": '            "ledger_event_count": 0,\n',
        "tests": f"{LIFECYCLE}::test_a_comparison_freezes_two_candidates_three_workloads_and_six_slots_before_results",
        "expect": "test_a_comparison_freezes_two_candidates_three_workloads_and_six_slots_before_results",
    },
    {
        "name": "s15_live_adapter_rejects_multirequest",
        "file": "shiftwork/executor/tokenfactory.py",
        "old": '            if not 1 <= len(batch) <= 4:\n',
        "new": '            if len(batch) != 1:\n',
        "tests": "tests/executor/test_gateway_isolation.py::test_adapter_streams_only_the_current_request_and_reads_back_each_capture",
        "expect": "test_adapter_streams_only_the_current_request_and_reads_back_each_capture",
    },
    {
        "name": "s15_live_gateway_accepts_wrong_ordinal",
        "file": "shiftwork/gateway/service_inference.py",
        "old": '        if request.request_ordinal != self.policy.request_ordinal:\n',
        "new": '        if request.request_ordinal != 1:\n',
        "tests": "tests/executor/test_gateway_isolation.py::test_gateway_binds_each_request_call_to_the_current_ordinal",
        "expect": "test_gateway_binds_each_request_call_to_the_current_ordinal",
    },
    {
        "name": "s15_live_second_capture_not_read_back",
        "file": "shiftwork/executor/tokenfactory.py",
        "old": '            for ordinal, summary in enumerate(capture_summaries, start=1):\n',
        "new": '            for ordinal, summary in enumerate(capture_summaries[:1], start=1):\n',
        "tests": "tests/executor/test_gateway_isolation.py::test_adapter_streams_only_the_current_request_and_reads_back_each_capture",
        "expect": "test_adapter_streams_only_the_current_request_and_reads_back_each_capture",
    },
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
        "old": '        if not isolated and version.content_hash != config.TRUSTED_LOCAL_FIXTURES["pivot_starter"][0]:\n            raise LifecycleError(\n                "conflict",\n                "only the pinned reviewed starter is executable as a public diagnostic candidate",\n            )\n',
        "new": '        if False:\n            raise LifecycleError(\n                "conflict",\n                "only the pinned reviewed starter is executable as a public diagnostic candidate",\n            )\n',
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
        # Re-anchored for Slice 15. The guard moved into reserve_bootstrap_diagnostic
        # when the live bootstrap landed; the proof is unchanged: without the
        # legacy-first-choice guard an ordinary shift's null-investigation
        # bootstrap is no longer refused with its own reason.
        "old": '    if shift.opening_mode is not ShiftOpeningMode.LEGACY_FIRST_CHOICE:\n        raise BootstrapBlocked("a null investigation is reserved only for a legacy first-choice shift")\n',
        "new": '    if False:\n        raise BootstrapBlocked("a null investigation is reserved only for a legacy first-choice shift")\n',
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
        # Re-anchored for Slice 15: the diagnostic run row now carries the
        # isolated/offline split, and the comparison loop repeats the offline
        # spelling byte-identically, so the anchor carries the diagnostic run's
        # own batch reference.
        "old": '            request_batch_ref=config.PIVOT_INCIDENT_REQUESTS.name,\n            shop_snapshot_ref=f"frozen-context:{context.id}",\n            attempt_number=repo.count_runs(conn, shift.id) + 1,\n            state=RunState.QUEUED,\n            adapter=adapter,\n            started_at=_now(),\n            purpose=RunPurpose.EXPERIMENT,\n            evidence_mode=EvidenceMode.ISOLATED_LIVE if isolated else EvidenceMode.TRUSTED_LOCAL,\n',
        "new": '            request_batch_ref=config.PIVOT_INCIDENT_REQUESTS.name,\n            shop_snapshot_ref=f"frozen-context:{context.id}",\n            attempt_number=repo.count_runs(conn, shift.id) + 1,\n            state=RunState.QUEUED,\n            adapter=adapter,\n            started_at=_now(),\n            purpose=RunPurpose.EXPERIMENT,\n            evidence_mode=EvidenceMode.RECORDED_INSPECTION,\n',
        "tests": f"{LIFECYCLE}::test_the_pinned_starter_fails_the_request_where_it_actually_fails",
        "expect": "test_the_pinned_starter_fails_the_request_where_it_actually_fails",
    },
    {
        "name": "s11_completion_counted_without_the_required_tasks",
        "file": "shiftwork/orchestrator.py",
        # The comparison slot repeats these two lines, so the anchor carries the
        # diagnostic-only assessment tail to stay unambiguous.
        "old": "            if evaluator.request_usefully_completed(spec, request_assessments):\n                completed += 1\n        repo.insert_run_assessment(\n            conn,\n            RunAssessment(\n                run_id=run.id,\n                context_hash=context.content_hash,\n                complete_request_count=completed,\n                expected_request_count=len(mission.request_specs),\n",
        "new": "            completed += 1\n        repo.insert_run_assessment(\n            conn,\n            RunAssessment(\n                run_id=run.id,\n                context_hash=context.content_hash,\n                complete_request_count=completed,\n                expected_request_count=len(mission.request_specs),\n",
        "tests": f"{LIFECYCLE}::test_the_pinned_starter_fails_the_request_where_it_actually_fails",
        "expect": "test_the_pinned_starter_fails_the_request_where_it_actually_fails",
    },
    {
        "name": "s11_assessment_reads_the_live_fixture",
        "file": "shiftwork/orchestrator.py",
        "old": "    workload = context.workloads[0]\r\n    try:\n        snapshot_bytes = base64.b64decode(context.public_data_bytes_base64)\n        mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))\n",
        "new": "    workload = context.workloads[0]\r\n    try:\n        snapshot_bytes = base64.b64decode(context.public_data_bytes_base64)\n        mission = task_contract.load_mission(config.PIVOT_MISSION)\n",
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
        "old": '        if investigation is not None and investigation.shift_id != shift.id:\n            raise LifecycleError(\n                "conflict", "a diagnostic must cite an investigation owned by this shift"\n            )\n',
        "new": '        if False:\n            raise LifecycleError(\n                "conflict", "a diagnostic must cite an investigation owned by this shift"\n            )\n',
        "tests": f"{LIFECYCLE}::test_an_investigation_from_another_shift_cannot_authorise_a_diagnostic",
        "expect": "test_an_investigation_from_another_shift_cannot_authorise_a_diagnostic",
    },
    {
        "name": "s14_absent_assist_gateway_claims_success",
        "file": "shiftwork/orchestrator.py",
        "old": '    if gateway is None:\n        raise AssistGatewayUnavailable(\n            f"assist gateway is not configured for this session; {role.value} is unavailable"\n        )',
        "new": '    if gateway is None:\n        return None',
        "tests": f"{ASSIST}::test_diagnostic_help_needs_an_investigation_and_is_denied_anyway",
        "expect": "test_diagnostic_help_needs_an_investigation_and_is_denied_anyway",
    },
    # --- Slice 15: the qualifying comparison -----------------------------------
    # The workspace rows leave a shared directory under the OS temp root while
    # the proof runs (that is the fault); nothing in the repository changes.
    {
        "name": "s15_pair_binding_collapsed",
        "file": "shiftwork/orchestrator.py",
        "old": "            workload = workloads[pair - 1]\n",
        "new": "            workload = workloads[0]\n",
        "tests": f"{LIFECYCLE}::test_each_pair_shares_one_workload_and_the_reviewed_bytes_are_pinned",
        "expect": "test_each_pair_shares_one_workload_and_the_reviewed_bytes_are_pinned",
    },
    {
        "name": "s15_pair_two_b_workload_swapped",
        "file": "shiftwork/orchestrator.py",
        "old": "            workload = workloads[pair - 1]\n",
        "new": "            workload = workloads[0] if (pair == 2 and label == \"B\") else workloads[pair - 1]\n",
        "tests": f"{LIFECYCLE}::test_each_pair_shares_one_workload_and_the_reviewed_bytes_are_pinned",
        "expect": "test_each_pair_shares_one_workload_and_the_reviewed_bytes_are_pinned",
    },
    {
        "name": "s15_schedule_pair_two_swapped",
        "file": "shiftwork/orchestrator.py",
        "old": '    order = [(1, "A"), (1, "B"), (2, "B"), (2, "A"), (3, pair_three[0]), (3, pair_three[1])]\n',
        "new": '    order = [(1, "A"), (1, "B"), (2, "A"), (2, "B"), (3, pair_three[0]), (3, pair_three[1])]\n',
        "tests": f"{LIFECYCLE}::test_the_precommitted_schedule_is_stored_executed_once_and_not_reorderable",
        "expect": "test_the_precommitted_schedule_is_stored_executed_once_and_not_reorderable",
    },
    {
        "name": "s15_pair_three_order_not_derived",
        "file": "shiftwork/orchestrator.py",
        "old": '    pair_three = ("A", "B") if decision[-1] & 1 == 0 else ("B", "A")\n',
        "new": '    pair_three = ("B", "A") if decision[-1] & 1 == 0 else ("A", "B")\n',
        "tests": f"{LIFECYCLE}::test_the_precommitted_schedule_is_stored_executed_once_and_not_reorderable",
        "expect": "test_the_precommitted_schedule_is_stored_executed_once_and_not_reorderable",
    },
    {
        "name": "s15_manifest_hash_not_recomputed",
        "file": "shiftwork/orchestrator.py",
        "old": '            hashlib.sha256(batch_bytes).hexdigest() != entry.get("request_bytes_sha256")\n',
        "new": "            False\n",
        "tests": f"{LIFECYCLE}::test_a_manifest_mismatch_fails_closed_and_reserves_nothing[wrong_claimed_hash]",
        "expect": "test_a_manifest_mismatch_fails_closed_and_reserves_nothing[wrong_claimed_hash]",
    },
    {
        "name": "s15_manifest_length_not_recomputed",
        "file": "shiftwork/orchestrator.py",
        "old": '            hashlib.sha256(batch_bytes).hexdigest() != entry.get("request_bytes_sha256")\n            or len(batch_bytes) != entry.get("request_bytes_length")\n',
        "new": '            hashlib.sha256(batch_bytes).hexdigest() != entry.get("request_bytes_sha256")\n',
        "tests": f"{LIFECYCLE}::test_a_manifest_mismatch_fails_closed_and_reserves_nothing[wrong_claimed_length]",
        "expect": "test_a_manifest_mismatch_fails_closed_and_reserves_nothing[wrong_claimed_length]",
    },
    {
        "name": "s15_manifest_specs_hash_not_recomputed",
        "file": "shiftwork/orchestrator.py",
        "old": '        if hashlib.sha256(canonical_specs).hexdigest() != entry.get("task_specs_sha256"):\n',
        "new": "        if False:\n",
        "tests": f"{LIFECYCLE}::test_a_manifest_mismatch_fails_closed_and_reserves_nothing[wrong_claimed_specs_hash]",
        "expect": "test_a_manifest_mismatch_fails_closed_and_reserves_nothing[wrong_claimed_specs_hash]",
    },
    {
        "name": "s15_manifest_count_not_recomputed",
        "file": "shiftwork/orchestrator.py",
        "old": '            len(batch) != entry.get("request_count")\n            or len(specs) != entry.get("request_count")\n            or not 1 <= len(specs) <= 4\n',
        "new": "            False\n",
        "tests": f"{LIFECYCLE}::test_a_manifest_mismatch_fails_closed_and_reserves_nothing[extra_request_with_recomputed_pin]",
        "expect": "test_a_manifest_mismatch_fails_closed_and_reserves_nothing[extra_request_with_recomputed_pin]",
    },
    {
        "name": "s15_blank_line_silently_removed_before_execution",
        "file": "shiftwork/orchestrator.py",
        "old": "            batch = executor.load_batch(\n",
        "new": "            batch_bytes = b''.join(line for line in batch_bytes.splitlines(keepends=True) if line.strip())\n            batch = executor.load_batch(\n",
        "tests": f"{LIFECYCLE}::test_executor_incompatible_blank_line_fails_before_exposure",
        "expect": "test_executor_incompatible_blank_line_fails_before_exposure",
    },
    {
        "name": "s15_restart_omits_comparison_terminalization",
        "file": "shiftwork/orchestrator.py",
        "old": "    for experiment in repo.list_nonterminal_comparisons(conn):\n",
        "new": "    for experiment in ():\n",
        "tests": f"{LIFECYCLE}::test_restart_terminalizes_comparison_without_retry_and_keeps_capture[claimed]",
        "expect": "test_restart_terminalizes_comparison_without_retry_and_keeps_capture[claimed]",
    },
    {
        "name": "s15_manifest_engagement_unchecked",
        "file": "shiftwork/orchestrator.py",
        "old": '    if (data.get("engagement_slug") != slug or data.get("schema_version") != 1\n            or data.get("comparison_state_sha256") != _hash_bytes(snapshot_bytes)):\n',
        "new": "    if False:\n",
        "tests": f"{LIFECYCLE}::test_a_manifest_mismatch_fails_closed_and_reserves_nothing[cross_engagement]",
        "expect": "test_a_manifest_mismatch_fails_closed_and_reserves_nothing[cross_engagement]",
    },
    {
        "name": "s15_reservation_rollback_removed",
        "file": "shiftwork/orchestrator.py",
        "old": "    except Exception:\r\n        conn.rollback()\r\n        raise\r\n    return experiment\r\n\r\n\r\ndef _comparison_run_request(",
        "new": "    except Exception:\r\n        raise\r\n    return experiment\r\n\r\n\r\ndef _comparison_run_request(",
        "tests": f"{LIFECYCLE}::test_a_fault_mid_reservation_leaves_no_partial_comparison[insert_experiment]",
        "expect": "test_a_fault_mid_reservation_leaves_no_partial_comparison[insert_experiment]",
    },
    {
        "name": "s15_execution_claim_bypassed",
        "file": "shiftwork/orchestrator.py",
        "old": "    if not repo.claim_comparison_execution(conn, experiment.id):\n        conn.rollback()\n        return repo.get_experiment(conn, experiment.id)\n    conn.commit()\n",
        "new": "    repo.update_experiment_state(conn, experiment.id, \"RUNNING\")\n    conn.commit()\n",
        "tests": f"{LIFECYCLE}::test_a_repeated_comparison_worker_cannot_execute_reserved_slots_twice",
        "expect": "test_a_repeated_comparison_worker_cannot_execute_reserved_slots_twice",
    },
    {
        "name": "s15_background_error_leaves_comparison_running",
        "file": "shiftwork/orchestrator.py",
        "old": "        repo.update_experiment_state(conn, experiment.id, \"FAILED\")\n        conn.commit()\n        raise\n",
        "new": "        conn.commit()\n        raise\n",
        "tests": f"{LIFECYCLE}::test_an_unexpected_slot_error_fails_the_comparison_without_retry",
        "expect": "test_an_unexpected_slot_error_fails_the_comparison_without_retry",
    },
    {
        "name": "s15_pre_adapter_error_leaves_touched_slot_reserved",
        "file": "shiftwork/orchestrator.py",
        "old": "        if active_slot_id is not None:\n",
        "new": "        if False:\n",
        "tests": f"{LIFECYCLE}::test_a_pre_adapter_slot_error_fails_the_touched_slot_without_retry",
        "expect": "test_a_pre_adapter_slot_error_fails_the_touched_slot_without_retry",
    },
    {
        "name": "s15_incomplete_comparison_finalized",
        "file": "shiftwork/orchestrator.py",
        "old": '    final = "FINALIZED" if slots and all(slot.state == "COMPLETE" for slot in slots) else "FAILED"\n',
        "new": '    final = "FINALIZED"\n',
        "tests": f"{LIFECYCLE}::test_a_failed_slot_stays_visible_and_the_comparison_is_never_refunded",
        "expect": "test_a_failed_slot_stays_visible_and_the_comparison_is_never_refunded",
    },
    {
        "name": "s15_slot_binding_not_reverified",
        "file": "shiftwork/orchestrator.py",
        "old": "        or workload.request_batch_hash != slot.request_batch_hash\n",
        "new": "",
        "tests": f"{LIFECYCLE}::test_a_tampered_workload_binding_fails_the_slot_instead_of_running_another_batch[slot_hash]",
        "expect": "test_a_tampered_workload_binding_fails_the_slot_instead_of_running_another_batch[slot_hash]",
    },
    {
        "name": "s15_request_line_identity_unchecked",
        "file": "shiftwork/orchestrator.py",
        "old": '                or parsed_line.get("request_id") != spec.id\n',
        "new": "                or False\n",
        "tests": f"{LIFECYCLE}::test_a_manifest_mismatch_fails_closed_and_reserves_nothing[wrong_request_id_with_recomputed_pin]",
        "expect": "test_a_manifest_mismatch_fails_closed_and_reserves_nothing[wrong_request_id_with_recomputed_pin]",
    },
    {
        "name": "s15_slot_workspace_not_fresh",
        "file": "shiftwork/orchestrator.py",
        "old": '        with tempfile.TemporaryDirectory(prefix=f"shiftwork-compare-{slot.pair_ordinal}-") as directory:\n            snapshot_path = Path(directory) / "public_state.json"\n',
        "new": '        import contextlib\n        directory = os.path.join(tempfile.gettempdir(), f"shiftwork-compare-{slot.pair_ordinal}-shared")\n        os.makedirs(directory, exist_ok=True)\n        with contextlib.nullcontext(directory) as directory:\n            snapshot_path = Path(directory) / "public_state.json"\n',
        "tests": f"{LIFECYCLE}::test_every_slot_gets_its_own_fresh_reset_workspace",
        "expect": "test_every_slot_gets_its_own_fresh_reset_workspace",
    },
    {
        "name": "s15_executor_workspace_reused",
        "file": "shiftwork/executor/local_process.py",
        "old": '        with tempfile.TemporaryDirectory(prefix="shiftwork-fixture-") as workspace:\n            root = Path(workspace)\n',
        "new": '        import contextlib\n        workspace = os.path.join(tempfile.gettempdir(), "shiftwork-fixture-shared")\n        os.makedirs(workspace, exist_ok=True)\n        with contextlib.nullcontext(workspace) as workspace:\n            root = Path(workspace)\n',
        "tests": f"{LIFECYCLE}::test_a_sentinel_left_by_one_execution_is_invisible_to_the_next",
        "expect": "test_a_sentinel_left_by_one_execution_is_invisible_to_the_next",
    },
    {
        "name": "s15_duplicate_pair_key_allowed",
        "file": "shiftwork/store/migrations/v6_tables.sql",
        "old": "    UNIQUE (experiment_id, pair_ordinal, candidate_label),\n",
        "new": "",
        "tests": f"{LIFECYCLE}::test_the_database_constraints_reject_duplicate_keys_not_just_the_controller",
        "expect": "test_the_database_constraints_reject_duplicate_keys_not_just_the_controller",
    },
    {
        "name": "s15_duplicate_order_key_allowed",
        "file": "shiftwork/store/migrations/v6_tables.sql",
        "old": "    UNIQUE (experiment_id, execution_ordinal),\n",
        "new": "",
        "tests": f"{LIFECYCLE}::test_the_database_constraints_reject_duplicate_keys_not_just_the_controller",
        "expect": "test_the_database_constraints_reject_duplicate_keys_not_just_the_controller",
    },
    {
        "name": "s15_eligible_derived",
        "file": "shiftwork/orchestrator.py",
        "old": '        "eligible": bool(outcome and any(item.eligible for item in outcome.eligibility)),\n        "eligibility_reason": (\n            "No winner is derived here. Candidate eligibility requires a complete "\n',
        "new": '        "eligible": False,\n        "eligibility_reason": (\n            "No winner is derived here. Candidate eligibility requires a complete "\n',
        "tests": f"{LIFECYCLE}::test_the_compare_station_shows_all_six_slots_without_a_winner",
        "expect": "test_the_compare_station_shows_all_six_slots_without_a_winner",
    },
    {
        "name": "s15_protected_refs_projected",
        "file": "shiftwork/orchestrator.py",
        "old": '            "workload_ordinal": slot.pair_ordinal,\n',
        "new": '            "workload_ordinal": slot.pair_ordinal,\n            "protected_variant_refs": list(slot.protected_variant_refs),\n',
        "tests": f"{LIFECYCLE}::test_the_workload_summary_exposes_no_future_request_bytes_or_protected_refs",
        "expect": "test_the_workload_summary_exposes_no_future_request_bytes_or_protected_refs",
    },
    {
        "name": "s15_candidate_pin_ignored",
        "file": "shiftwork/orchestrator.py",
        "old": "            if {candidate_a.content_hash, candidate_b.content_hash} != pinned:\n",
        "new": "            if False:\n",
        "tests": f"{LIFECYCLE}::test_a_comparison_requires_two_distinct_reviewed_candidates_and_an_owned_entry",
        "expect": "test_a_comparison_requires_two_distinct_reviewed_candidates_and_an_owned_entry",
    },
    {
        "name": "s15_foreign_investigation_accepted",
        "file": "shiftwork/orchestrator.py",
        "old": '        if investigation.shift_id != shift.id:\n            raise LifecycleError(\n                "conflict", "a qualifying comparison requires an investigation owned by this shift"\n            )\n',
        "new": '        if False:\n            raise LifecycleError(\n                "conflict", "a qualifying comparison requires an investigation owned by this shift"\n            )\n',
        "tests": f"{LIFECYCLE}::test_a_comparison_requires_two_distinct_reviewed_candidates_and_an_owned_entry",
        "expect": "test_a_comparison_requires_two_distinct_reviewed_candidates_and_an_owned_entry",
    },
    # Slice 15 protected phase (Gate 4 trace rows 50 to 54): each row faults one
    # named obligation-50 to 54 guard branch and requires the protected-phase,
    # pairing, privacy or denominator test to fail with an assertion-level catch.
    {
        "name": "s15_protected_phase_skipped",
        "file": "shiftwork/orchestrator.py",
        "old": '        protected_result = None\n        if public_complete and repo.get_exposure_reservation(conn, reservation.id).state == "ACTIVE":\n',
        "new": '        protected_result = None\n        if False:\n',
        "tests": f"{LIFECYCLE}::test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
        "expect": "test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
    },
    {
        "name": "s15_protected_phase_state_swapped",
        "file": "shiftwork/orchestrator.py",
        "old": '        with tempfile.TemporaryDirectory(prefix=f"shiftwork-compare-{slot.pair_ordinal}-") as directory:\r\n            snapshot_path = Path(directory) / "public_state.json"\r\n            snapshot_path.write_bytes(snapshot_bytes)\r\n',
        "new": '        with tempfile.TemporaryDirectory(prefix=f"shiftwork-compare-{slot.pair_ordinal}-") as directory:\r\n            snapshot_path = Path(directory) / "public_state.json"\r\n            snapshot_path.write_bytes(protected_state_bytes)\r\n',
        "tests": f"{LIFECYCLE}::test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
        "expect": "test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
    },
    {
        "name": "s15_protected_phase_executed_before_public",
        "file": "shiftwork/orchestrator.py",
        "old": '        with tempfile.TemporaryDirectory(prefix=f"shiftwork-compare-{slot.pair_ordinal}-") as directory:\n            snapshot_path = Path(directory) / "public_state.json"\n            snapshot_path.write_bytes(snapshot_bytes)\n            request = request.model_copy(update={"shop_snapshot_ref": str(snapshot_path)})\n            if run.adapter == TokenFactoryAdapter.name:\n                adapter = TokenFactoryAdapter(\n                    run_id=run.id,\n                    allowed_tool_names=tuple(mission.allowed_tool_vocabulary),\n                    token=os.environ.get("NEBIUS_API_KEY", ""),\n                    project=os.environ.get("NEBIUS_PROJECT_ID", ""),\n                    model=context.service_model or config.SERVICE_MODEL,\n                )\n            elif run.adapter == LocalProcessAdapter.name:\n                adapter = LocalProcessAdapter()\n            else:\n                raise LifecycleError("conflict", "reserved comparison slot has no safe executor")\n            public_result = asyncio.run(adapter.execute(request))\n        public_complete = (\n            public_result.failure is None\n            and len(public_result.captures) == workload.request_count\n            and {capture.request_ordinal for capture in public_result.captures}\n                == set(range(1, workload.request_count + 1))\n            and all(capture.transport_error is None and capture.body for capture in public_result.captures)\n        )\n        protected_result = None\n        if public_complete and repo.get_exposure_reservation(conn, reservation.id).state == "ACTIVE":\n            with tempfile.TemporaryDirectory(prefix=f"shiftwork-protected-{slot.pair_ordinal}-") as directory:\n                protected_path = Path(directory) / "protected_state.json"\n                protected_path.write_bytes(protected_state_bytes)\n                protected_request = request.model_copy(update={\n                    "shop_snapshot_ref": str(protected_path),\n                    "request_batch": protected_ref,\n                    "request_batch_bytes": protected_line,\n                    "single_request_ordinal": slot.executed_request_count,\n                })\n                protected_result = asyncio.run(adapter.execute(protected_request))\n',
        "new": '        if run.adapter == TokenFactoryAdapter.name:\n            adapter = TokenFactoryAdapter(\n                run_id=run.id,\n                allowed_tool_names=tuple(mission.allowed_tool_vocabulary),\n                token=os.environ.get("NEBIUS_API_KEY", ""),\n                project=os.environ.get("NEBIUS_PROJECT_ID", ""),\n                model=context.service_model or config.SERVICE_MODEL,\n            )\n        elif run.adapter == LocalProcessAdapter.name:\n            adapter = LocalProcessAdapter()\n        else:\n            raise LifecycleError("conflict", "reserved comparison slot has no safe executor")\n        protected_result = None\n        with tempfile.TemporaryDirectory(prefix=f"shiftwork-protected-{slot.pair_ordinal}-") as directory:\n            protected_path = Path(directory) / "protected_state.json"\n            protected_path.write_bytes(protected_state_bytes)\n            protected_request = request.model_copy(update={\n                "shop_snapshot_ref": str(protected_path),\n                "request_batch": protected_ref,\n                "request_batch_bytes": protected_line,\n                "single_request_ordinal": slot.executed_request_count,\n            })\n            protected_result = asyncio.run(adapter.execute(protected_request))\n        with tempfile.TemporaryDirectory(prefix=f"shiftwork-compare-{slot.pair_ordinal}-") as directory:\n            snapshot_path = Path(directory) / "public_state.json"\n            snapshot_path.write_bytes(snapshot_bytes)\n            request = request.model_copy(update={"shop_snapshot_ref": str(snapshot_path)})\n            public_result = asyncio.run(adapter.execute(request))\n        public_complete = (\n            public_result.failure is None\n            and len(public_result.captures) == workload.request_count\n            and {capture.request_ordinal for capture in public_result.captures}\n                == set(range(1, workload.request_count + 1))\n            and all(capture.transport_error is None and capture.body for capture in public_result.captures)\n        )\n',
        "tests": f"{LIFECYCLE}::test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
        "expect": "test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
    },
    {
        "name": "s15_protected_workspace_reused",
        "file": "shiftwork/orchestrator.py",
        "old": '        with tempfile.TemporaryDirectory(prefix=f"shiftwork-compare-{slot.pair_ordinal}-") as directory:\n            snapshot_path = Path(directory) / "public_state.json"\n            snapshot_path.write_bytes(snapshot_bytes)\n            request = request.model_copy(update={"shop_snapshot_ref": str(snapshot_path)})\n            if run.adapter == TokenFactoryAdapter.name:\n                adapter = TokenFactoryAdapter(\n                    run_id=run.id,\n                    allowed_tool_names=tuple(mission.allowed_tool_vocabulary),\n                    token=os.environ.get("NEBIUS_API_KEY", ""),\n                    project=os.environ.get("NEBIUS_PROJECT_ID", ""),\n                    model=context.service_model or config.SERVICE_MODEL,\n                )\n            elif run.adapter == LocalProcessAdapter.name:\n                adapter = LocalProcessAdapter()\n            else:\n                raise LifecycleError("conflict", "reserved comparison slot has no safe executor")\n            public_result = asyncio.run(adapter.execute(request))\n        public_complete = (\n            public_result.failure is None\n            and len(public_result.captures) == workload.request_count\n            and {capture.request_ordinal for capture in public_result.captures}\n                == set(range(1, workload.request_count + 1))\n            and all(capture.transport_error is None and capture.body for capture in public_result.captures)\n        )\n        protected_result = None\n        if public_complete and repo.get_exposure_reservation(conn, reservation.id).state == "ACTIVE":\n            with tempfile.TemporaryDirectory(prefix=f"shiftwork-protected-{slot.pair_ordinal}-") as directory:\n                protected_path = Path(directory) / "protected_state.json"\n                protected_path.write_bytes(protected_state_bytes)\n                protected_request = request.model_copy(update={\n                    "shop_snapshot_ref": str(protected_path),\n                    "request_batch": protected_ref,\n                    "request_batch_bytes": protected_line,\n                    "single_request_ordinal": slot.executed_request_count,\n                })\n                protected_result = asyncio.run(adapter.execute(protected_request))\n',
        "new": '        import contextlib\n        shared_workspace = tempfile.mkdtemp(prefix=f"shiftwork-compare-shared-{slot.executed_request_count}-")\n        with contextlib.nullcontext(shared_workspace) as directory:\n            snapshot_path = Path(directory) / "public_state.json"\n            snapshot_path.write_bytes(snapshot_bytes)\n            request = request.model_copy(update={"shop_snapshot_ref": str(snapshot_path)})\n            if run.adapter == TokenFactoryAdapter.name:\n                adapter = TokenFactoryAdapter(\n                    run_id=run.id,\n                    allowed_tool_names=tuple(mission.allowed_tool_vocabulary),\n                    token=os.environ.get("NEBIUS_API_KEY", ""),\n                    project=os.environ.get("NEBIUS_PROJECT_ID", ""),\n                    model=context.service_model or config.SERVICE_MODEL,\n                )\n            elif run.adapter == LocalProcessAdapter.name:\n                adapter = LocalProcessAdapter()\n            else:\n                raise LifecycleError("conflict", "reserved comparison slot has no safe executor")\n            public_result = asyncio.run(adapter.execute(request))\n        public_complete = (\n            public_result.failure is None\n            and len(public_result.captures) == workload.request_count\n            and {capture.request_ordinal for capture in public_result.captures}\n                == set(range(1, workload.request_count + 1))\n            and all(capture.transport_error is None and capture.body for capture in public_result.captures)\n        )\n        protected_result = None\n        if public_complete:\n            with contextlib.nullcontext(shared_workspace) as directory:\n                protected_path = Path(directory) / "protected_state.json"\n                protected_path.write_bytes(protected_state_bytes)\n                protected_request = request.model_copy(update={\n                    "shop_snapshot_ref": str(protected_path),\n                    "request_batch": protected_ref,\n                    "request_batch_bytes": protected_line,\n                    "single_request_ordinal": slot.executed_request_count,\n                })\n                protected_result = asyncio.run(adapter.execute(protected_request))\n',
        "tests": f"{LIFECYCLE}::test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
        "expect": "test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
    },
    {
        "name": "s15_protected_line_through_batch_loader",
        "file": "shiftwork/executor/local_process.py",
        "old": "            batch = ((load_single_request(request.request_batch, request.request_batch_bytes,\n"
               "                                          request.single_request_ordinal),)\n"
               "                     if request.single_request_ordinal is not None else\n"
               "                     load_batch(request.request_batch, request.request_batch_bytes))\n",
        "new": "            batch = load_batch(request.request_batch, request.request_batch_bytes)\n",
        "tests": f"{LIFECYCLE}::test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
        "expect": "test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
    },
    {
        "name": "s15_single_request_multiline_accepted",
        "file": "shiftwork/executor/base.py",
        "old": '    if len(lines) != 1 or not lines[0].strip():\n        raise ValueError("protected request must be exactly one non-empty line")\n',
        "new": '    if False:\n        raise ValueError("protected request must be exactly one non-empty line")\n',
        "tests": f"{LIFECYCLE}::test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
        "expect": "test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
    },
    {
        "name": "s15_single_request_ordinal_unchecked",
        "file": "shiftwork/executor/base.py",
        "old": '    if stimulus.ordinal != ordinal:\n        raise ValueError("protected request ordinal mismatch")\n',
        "new": '    if False:\n        raise ValueError("protected request ordinal mismatch")\n',
        "tests": f"{LIFECYCLE}::test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
        "expect": "test_slot_runs_public_phase_then_protected_phase_in_frozen_order",
    },
    {
        "name": "s15_protected_pair_variant_leaked",
        "file": "shiftwork/orchestrator.py",
        "old": "                protected_variant_refs=reserved.get(pair, ()),\n",
        "new": '                protected_variant_refs=reserved.get(1 if (pair == 2 and label == "B") else pair, ()),\n',
        "tests": f"{LIFECYCLE}::test_each_pair_shares_one_identical_protected_stimulus",
        "expect": "test_each_pair_shares_one_identical_protected_stimulus",
    },
    {
        "name": "s15_protected_slot_second_variant",
        "file": "shiftwork/orchestrator.py",
        "old": "                protected_variant_refs=reserved.get(pair, ()),\n",
        "new": "                protected_variant_refs=reserved.get(pair, ()) + reserved.get(1 if pair != 1 else 2, ()),\n",
        "tests": f"{LIFECYCLE}::test_each_pair_shares_one_identical_protected_stimulus",
        "expect": "test_each_pair_shares_one_identical_protected_stimulus",
    },
    {
        "name": "s15_protected_ordinal_mismatch",
        "file": "shiftwork/orchestrator.py",
        "old": "                executed_request_count=workload.request_count + 1,\n",
        "new": "                executed_request_count=workload.request_count,\n",
        "tests": f"{LIFECYCLE}::test_each_pair_shares_one_identical_protected_stimulus",
        "expect": "test_each_pair_shares_one_identical_protected_stimulus",
    },
    {
        "name": "s15_protected_binding_hash_not_pinned",
        "file": "shiftwork/orchestrator.py",
        "old": "            protected_state_hash=reserved.resolved_state_sha256,\n",
        "new": "            protected_state_hash=canonical.content_hash(reserved.resolved_state_sha256),\n",
        "tests": f"{LIFECYCLE}::test_protected_variant_is_bound_and_snapshotted_before_any_result",
        "expect": "test_protected_variant_is_bound_and_snapshotted_before_any_result",
    },
    {
        "name": "s15_protected_collision_accepted",
        "file": "shiftwork/domain/task_contract.py",
        "old": "    if (existing_entities & added_entities or existing_records & set(added_records)\n"
               "            or len(added_records) != len(set(added_records))):\n"
               '        raise PublicStateInvalid("protected delta collides with comparison state")\n',
        "new": "    if False:\n"
               '        raise PublicStateInvalid("protected delta collides with comparison state")\n',
        "tests": f"{LIFECYCLE}::test_protected_delta_collision_is_rejected_before_exposure[entity]",
        "expect": "test_protected_delta_collision_is_rejected_before_exposure[entity]",
    },
    {
        "name": "s15_protected_request_canonicalizer_denormalized",
        "file": "shiftwork/domain/task_contract.py",
        "old": '    return canonical.canonical_bytes(row.model_dump(mode="json")) + b"\\n"\n',
        "new": '    return json.dumps(row.model_dump(mode="json"), sort_keys=True, '
               'separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\\n"\n',
        "tests": f"{LIFECYCLE}::test_protected_variant_is_bound_and_snapshotted_before_any_result",
        "expect": "test_protected_variant_is_bound_and_snapshotted_before_any_result",
    },
    {
        "name": "s15_protected_state_canonicalizer_unpinned",
        "file": "shiftwork/domain/task_contract.py",
        "old": '    base_data["description"] = delta.description\n',
        "new": "    pass  # MUTATION: the delta description is no longer applied\n",
        "tests": f"{LIFECYCLE}::test_protected_variant_is_bound_and_snapshotted_before_any_result",
        "expect": "test_protected_variant_is_bound_and_snapshotted_before_any_result",
    },
    {
        "name": "s15_protected_response_filter_removed",
        "file": "shiftwork/orchestrator.py",
        "old": "    return [output for output in repo.list_outputs(conn, run_id)\n"
               "            if slot is None or output.request_ordinal <= slot.request_count]\n",
        "new": "    return list(repo.list_outputs(conn, run_id))\n",
        "tests": f"{LIFECYCLE}::test_protected_content_and_captures_never_reach_public_surfaces",
        "expect": "test_protected_content_and_captures_never_reach_public_surfaces",
    },
    {
        "name": "s15_protected_observation_filter_removed",
        "file": "shiftwork/orchestrator.py",
        "old": "        for observation in repo.list_observations(conn, run.id)\n"
               "        if observation.request_ordinal <= public_count\n    ]\r\n",
        "new": "        for observation in repo.list_observations(conn, run.id)\n    ]\r\n",
        "tests": f"{LIFECYCLE}::test_protected_content_and_captures_never_reach_public_surfaces",
        "expect": "test_protected_content_and_captures_never_reach_public_surfaces",
    },
    {
        "name": "s15_protected_denominator_merged",
        "file": "shiftwork/orchestrator.py",
        "old": '        "shared_public_denominator_requests": sum(item.request_count for item in context.workloads),\n',
        "new": '        "shared_public_denominator_requests": sum(item.request_count for item in context.workloads) + len(context.workloads),\n',
        "tests": f"{LIFECYCLE}::test_public_and_protected_counts_reconcile_without_merging",
        "expect": "test_public_and_protected_counts_reconcile_without_merging",
    },
    {
        "name": "s15_protected_counts_before_terminal",
        "file": "shiftwork/orchestrator.py",
        "old": '    if experiment.state in ("FINALIZED", "FAILED", "INVALIDATED"):\n        outcome = _comparison_outcome(conn, experiment, context, slots)\n        protected_counts = {\n',
        "new": '    if True:\n        outcome = _comparison_outcome(conn, experiment, context, slots)\n        protected_counts = {\n',
        "tests": f"{LIFECYCLE}::test_public_and_protected_counts_reconcile_without_merging",
        "expect": "test_public_and_protected_counts_reconcile_without_merging",
    },
    {
        "name": "s15_candidate_b_prefers_lowest_price",
        "file": "shiftwork/fixtures/artifacts/bookshop/compare_repair_b_service.py",
        "old": '            qualifying.append((-stock["value"], price["value"], entity_ref, claims))\n',
        "new": '            qualifying.append((price["value"], -stock["value"], entity_ref, claims))\n',
        "tests": f"{LIFECYCLE}::test_candidates_make_a_measured_price_versus_stock_choice_on_request_011",
        "expect": "test_candidates_make_a_measured_price_versus_stock_choice_on_request_011",
    },
    # 2026-09-28 repair round: rows 68/69 were masked for every context tamper
    # by this frozen context-hash re-verification; it is faulted on its own now.
    {
        "name": "s15_frozen_context_hash_not_reverified",
        "file": "shiftwork/orchestrator.py",
        "old": "                or _frozen_comparison_context_hash(context, bindings) != context.content_hash\n",
        "new": "                or False\n",
        "tests": f"{LIFECYCLE}::test_a_tampered_workload_binding_fails_the_slot_instead_of_running_another_batch[swap_bytes]",
        "expect": "test_a_tampered_workload_binding_fails_the_slot_instead_of_running_another_batch[swap_bytes]",
    },
]


# Must stay an uncommitted path for the round in progress. main() truncates this
# file on every run, and it previously pointed at the committed S15 record, so a
# single run destroyed the recorded 97-of-97 evidence (2026-09-29).
RESULTS_LOG = ROOT / "docs" / "plans" / "shiftwork" / "evidence" / "slice16-pivot-mutation-2026-09-29.txt"


def append_result(line: str) -> None:
    with RESULTS_LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def main() -> int:
    # Crash-proof evidence: per-row flushed output plus a results file appended
    # after each row, so a crash keeps every completed row and names the row
    # that died (MISTAKES.md 2026-09-28: a buffered 96-row run lost all row
    # output when the restore write failed at row 95).
    RESULTS_LOG.write_text("", encoding="utf-8")
    print(f"results file: {RESULTS_LOG}", flush=True)
    results = []
    for index, case in enumerate(CASES, start=1):
        label = f"[{index}/{len(CASES)}] {case['name']}"
        print(f"{label} ...", flush=True)
        append_result(f"{label} START")
        try:
            result = runner.run_mutation(case)
        except Exception as exc:
            append_result(f"{label} CRASH {type(exc).__name__}: {str(exc).replace(chr(10), ' ')}")
            print(f"  CRASH {type(exc).__name__}: {exc}", flush=True)
            raise
        results.append(result)
        detail = str(result.get("detail", result.get("reason", ""))).replace("\n", " ")
        append_result(f"{label} {result['status']} restored={result.get('sha256_restored', False)} {detail}")
        print(f"  {result['status']} restored={result.get('sha256_restored', False)} {detail}", flush=True)

    print("\n=== MUTATION PROOF TABLE ===", flush=True)
    for result in results:
        print(
            result["name"], result["status"],
            f"restored={result.get('sha256_restored', False)}",
            result.get("detail", result.get("reason", "")),
        )
    return 0 if all(result["status"] == "FAIL_CAUGHT" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
