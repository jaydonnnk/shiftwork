"""Independent, byte-restored fault injections for S16 outcome claims.

Each row must fail its named assertion, not merely crash or time out. Do not run
this concurrently with other source edits or the full S15 mutation harness.
"""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("shiftwork_mutation_runner", ROOT / "tests" / "mutation_proofs.py")
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

PURE = "tests/domain/test_comparison.py"
LIFECYCLE = "tests/orchestrator/test_experiment_lifecycle.py"
CASES = [
    {
        "name": "public_denominator_uses_all_frozen_requests",
        "file": "shiftwork/domain/comparison.py",
        "old": "public_denominator_requests=sum(item.request_count for item in workloads),",
        "new": "public_denominator_requests=len(workloads),",
        "tests": f"{PURE}::test_public_and_protected_denominators_and_unknown_cost_are_separate",
        "expect": "test_public_and_protected_denominators_and_unknown_cost_are_separate",
    },
    {
        "name": "protected_denominator_one_per_pair",
        "file": "shiftwork/domain/comparison.py",
        "old": "protected_denominator=len(workloads), protected_passed=protected_passed,",
        "new": "protected_denominator=1, protected_passed=protected_passed,",
        "tests": f"{PURE}::test_public_and_protected_denominators_and_unknown_cost_are_separate",
        "expect": "test_public_and_protected_denominators_and_unknown_cost_are_separate",
    },
    {
        "name": "one_task_is_not_a_completed_multi_task_request",
        "file": "shiftwork/domain/comparison.py",
        "old": "if ordinal <= len(reading.public_specs) and ordinal in captured and request_usefully_completed(\n                reading.public_specs[ordinal - 1], assessments\n            ):",
        "new": "if ordinal <= len(reading.public_specs) and ordinal in captured and bool(assessments):",
        "tests": f"{PURE}::test_one_completed_task_cannot_credit_a_multi_task_request",
        "expect": "test_one_completed_task_cannot_credit_a_multi_task_request",
    },
    {
        "name": "overlapping_task_outcomes_are_both_counted",
        "file": "shiftwork/domain/comparison.py",
        "old": "outcomes = {item.outcome for item in assessments",
        "new": "outcomes = {assessments[0].outcome for item in assessments",
        "tests": f"{PURE}::test_overlapping_noncompletion_counts_are_not_a_partition",
        "expect": "test_overlapping_noncompletion_counts_are_not_a_partition",
    },
    {
        "name": "optional_missing_does_not_count_as_missing_request",
        "file": "shiftwork/domain/comparison.py",
        "old": "if item.outcome is not TaskOutcome.MISSING_OUTPUT or item.task_id in required_ids}",
        "new": "if True}",
        "tests": f"{PURE}::test_missing_optional_answer_does_not_erase_completed_required_work",
        "expect": "test_missing_optional_answer_does_not_erase_completed_required_work",
    },
    *(
        {
            "name": f"{kind}_clarification_has_its_own_counter",
            "file": "shiftwork/domain/comparison.py",
            "old": "if outcome in outcomes:\n                    counts[name] += 1",
            "new": f"if outcome in outcomes and outcome is not TaskOutcome.{kind.upper()}_CLARIFICATION:\n                    counts[name] += 1",
            "tests": f"{PURE}::test_fallback_categories_never_become_useful_completion[{kind.upper()}_CLARIFICATION-{kind}_clarifications]",
            "expect": "test_fallback_categories_never_become_useful_completion",
        }
        for kind in ("justified", "unjustified")
    ),
    {
        "name": "unknown_cost_is_not_zero",
        "file": "shiftwork/domain/comparison.py",
        "old": "provisioning_latency_ms=None, cost_minor_units=None,",
        "new": "provisioning_latency_ms=None, cost_minor_units=0,",
        "tests": f"{PURE}::test_public_and_protected_denominators_and_unknown_cost_are_separate",
        "expect": "test_public_and_protected_denominators_and_unknown_cost_are_separate",
    },
    {
        "name": "zero_recorded_calls_is_not_a_measured_zero",
        "file": "shiftwork/domain/comparison.py",
        "old": "    measured = evidence_mode is EvidenceMode.TRUSTED_LOCAL or meter_complete",
        "new": "    measured = True",
        "tests": f"{PURE}::test_live_controller_meter_proves_zero_and_missing_one_marker_restores_unknown",
        "expect": "test_live_controller_meter_proves_zero_and_missing_one_marker_restores_unknown",
    },
    {
        "name": "missing_model_result_keeps_usage_unknown",
        "file": "shiftwork/domain/comparison.py",
        "old": "if len(values) != expected or any(type(value) is not int or value < 0 for value in values):",
        "new": "if any(type(value) is not int or value < 0 for value in values):",
        "tests": f"{PURE}::test_missing_result_for_a_model_call_keeps_usage_and_latency_unknown",
        "expect": "test_missing_result_for_a_model_call_keeps_usage_and_latency_unknown",
    },
    {
        "name": "protected_failure_blocks_its_candidate",
        "file": "shiftwork/domain/comparison.py",
        "old": "if reading.protected_pass is False:\n                blockers.extend(reading.protected_rule_ids)",
        "new": "if False:\n                blockers.extend(reading.protected_rule_ids)",
        "tests": f"{PURE}::test_one_protected_mandatory_failure_blocks_only_that_candidate",
        "expect": "test_one_protected_mandatory_failure_blocks_only_that_candidate",
    },
    {
        "name": "public_mandatory_failure_blocks_its_candidate",
        "file": "shiftwork/domain/comparison.py",
        "old": "if any(reading.assessment is None or not reading.assessment.mandatory_pass",
        "new": "if any(reading.assessment is None and not reading.assessment.mandatory_pass",
        "tests": f"{PURE}::test_one_completed_task_cannot_credit_a_multi_task_request",
        "expect": "test_one_completed_task_cannot_credit_a_multi_task_request",
    },
    {
        "name": "failed_slot_cannot_be_complete",
        "file": "shiftwork/domain/comparison.py",
        "old": "and all(_reading_complete(item) for item in readings))",
        "new": "and all(True for item in readings))",
        "tests": f"{PURE}::test_failed_slot_cannot_be_called_complete_even_if_experiment_state_is_finalized",
        "expect": "test_failed_slot_cannot_be_called_complete_even_if_experiment_state_is_finalized",
    },
    {
        "name": "task_identity_is_part_of_completeness",
        "file": "shiftwork/domain/comparison.py",
        "old": "and len(public_rows) == len(expected_tasks) and actual_tasks == expected_tasks)",
        "new": "and len(public_rows) == len(expected_tasks))",
        "tests": f"{PURE}::test_task_identity_mismatch_cannot_look_like_a_complete_slot",
        "expect": "test_task_identity_mismatch_cannot_look_like_a_complete_slot",
    },
    {
        "name": "context_drift_blocks_both_candidates",
        "file": "shiftwork/domain/comparison.py",
        "old": "status = \"NOT_COMPARABLE\" if drift else \"COMPLETE\" if complete else \"INCOMPLETE\"",
        "new": "status = \"COMPLETE\" if complete else \"INCOMPLETE\"",
        "tests": f"{PURE}::test_context_drift_blocks_both_candidates_before_efficiency",
        "expect": "test_context_drift_blocks_both_candidates_before_efficiency",
    },
    {
        "name": "candidates_drift_returns_a_verdict_not_a_crash",
        "file": "shiftwork/domain/comparison.py",
        "old": "candidates[label].artifact_version_id if label in candidates else \"\",",
        "new": "candidates[label].artifact_version_id,",
        "tests": f"{PURE}::test_a_declared_candidate_set_that_is_not_exactly_a_and_b_returns_a_verdict",
        "expect": "test_a_declared_candidate_set_that_is_not_exactly_a_and_b_returns_a_verdict",
    },
    *(
        {
            "name": f"run_{field}_must_match_frozen_execution",
            "file": "shiftwork/domain/comparison.py",
            "old": condition,
            "new": "or False" if field != "evidence_mode" else "run is not None and (False",
            "tests": f"{PURE}::test_recorded_or_wrongly_bound_run_mode_cannot_qualify",
            "expect": "test_recorded_or_wrongly_bound_run_mode_cannot_qualify",
        }
        for field, condition in (
            ("evidence_mode", "run is not None and (run.evidence_mode != context.executor_class"),
            ("adapter", "or run.adapter != expected_adapter"),
            ("purpose", "or run.purpose is not RunPurpose.EXPERIMENT"),
        )
    ),
    {
        "name": "recorded_context_class_is_rejected",
        "file": "shiftwork/domain/comparison.py",
        "old": "if expected_adapter is None:\n        drift.add(\"executor_class\")",
        "new": "if False:\n        drift.add(\"executor_class\")",
        "tests": f"{PURE}::test_recorded_or_wrongly_bound_run_mode_cannot_qualify",
        "expect": "test_recorded_or_wrongly_bound_run_mode_cannot_qualify",
    },
    {
        "name": "unknown_mandatory_budget_blocks",
        "file": "shiftwork/domain/comparison.py",
        "old": "if value is None:\n                blockers.append(f\"unknown_mandatory_budget:{metric_name}\")",
        "new": "if value is None:\n                pass",
        "tests": f"{PURE}::test_unknown_mandatory_cost_and_exceeded_call_budget_block_eligibility",
        "expect": "test_unknown_mandatory_cost_and_exceeded_call_budget_block_eligibility",
    },
    {
        "name": "exceeded_mandatory_budget_blocks",
        "file": "shiftwork/domain/comparison.py",
        "old": "elif value > limit:\n                blockers.append(f\"mandatory_budget_exceeded:{metric_name}\")",
        "new": "elif False:\n                blockers.append(f\"mandatory_budget_exceeded:{metric_name}\")",
        "tests": f"{PURE}::test_unknown_mandatory_cost_and_exceeded_call_budget_block_eligibility",
        "expect": "test_unknown_mandatory_cost_and_exceeded_call_budget_block_eligibility",
    },
    {
        "name": "stored_usage_counts_service_calls",
        "file": "shiftwork/domain/comparison.py",
        "old": "calls += sum(item.kind is ObservationKind.INFERENCE_REQUEST for item in public_observations)",
        "new": "calls += 0",
        "tests": f"{PURE}::test_missing_usage_is_unknown_even_with_a_recorded_model_call",
        "expect": "test_missing_usage_is_unknown_even_with_a_recorded_model_call",
    },
    {
        "name": "protected_usage_is_not_public_efficiency",
        "file": "shiftwork/domain/comparison.py",
        "old": "if 1 <= item.request_ordinal <= slot.request_count)",
        "new": "if item.request_ordinal >= 1)",
        "tests": f"{PURE}::test_protected_model_usage_never_enters_public_efficiency_metrics",
        "expect": "test_protected_model_usage_never_enters_public_efficiency_metrics",
    },
    {
        "name": "protected_mandatory_failure_is_never_accepted",
        "file": "shiftwork/domain/comparison.py",
        "old": "or not by_id[task.id].mandatory_pass for task in spec.tasks",
        "new": "or False for task in spec.tasks",
        "tests": f"{PURE}::test_protected_aspect_needs_its_specific_task_outcome",
        "expect": "test_protected_aspect_needs_its_specific_task_outcome",
    },
    {
        "name": "frozen_context_hash_is_verified_on_readback",
        "file": "shiftwork/comparison_flow.py",
        "old": "elif _frozen_comparison_context_hash(context, bindings) != context.content_hash:",
        "new": "elif False:",
        "tests": f"{LIFECYCLE}::test_every_claim_defining_context_field_blocks_a_stale_outcome",
        "expect": "test_every_claim_defining_context_field_blocks_a_stale_outcome",
    },
    *(
        {
            "name": f"readback_guard_{guard}_reports_its_own_field",
            "file": "shiftwork/comparison_flow.py",
            "old": anchor,
            "new": replacement,
            "tests": f"{LIFECYCLE}::test_each_named_readback_drift_guard_reports_its_own_field",
            "expect": "test_each_named_readback_drift_guard_reports_its_own_field",
        }
        for guard, anchor, replacement in (
            (
                "public_data_bytes_hash",
                '        if _hash_bytes(public_bytes) != context.public_data_hash:\n'
                '            drift.add("public_data_bytes_hash")',
                '        if False:\n            drift.add("public_data_bytes_hash")',
            ),
            (
                "condition",
                '    if (context.condition.content_hash != _hash_bytes(condition_bytes)\n'
                '            or context.condition.content_hash != context.public_data_hash\n'
                '            or (public_bytes is not None and condition_bytes != public_bytes)):\n'
                '        drift.add("condition")',
                '    if False:\n        drift.add("condition")',
            ),
            (
                "visible_check_set",
                '    if canonical.content_hash([\n'
                '        {"ordinal": item.ordinal, "task_specs_hash": item.request_specs_hash}\n'
                '        for item in context.workloads\n'
                '    ]) != context.visible_check_set_hash:\n'
                '        drift.add("visible_check_set")',
                '    if False:\n        drift.add("visible_check_set")',
            ),
            (
                "workload_1",
                '            if (canonical.content_hash(_encode(batch_bytes)) != workload.request_batch_hash\n'
                '                    or _hash_bytes(_canonical_specs_bytes(specs)) != workload.request_specs_hash\n'
                '                    or len(specs) != workload.request_count):\n'
                '                drift.add(f"workload_{workload.ordinal}")',
                '            if False:\n                drift.add(f"workload_{workload.ordinal}")',
            ),
            (
                "assessment_context",
                '        if assessment is not None and assessment.context_hash != context.content_hash:\n'
                '            drift.add("assessment_context")',
                '        if False:\n            drift.add("assessment_context")',
            ),
            (
                "experiment_schedule",
                '    }) != experiment.content_hash:\n        drift.add("experiment_schedule")',
                '    }) != experiment.content_hash:\n        pass',
            ),
            (
                "candidate_A",
                '        if version is None or version.content_hash != candidate.artifact_content_hash:\n'
                '            drift.add(f"candidate_{candidate.label}")',
                '        if False:\n            drift.add(f"candidate_{candidate.label}")',
            ),
            (
                "run_binding",
                '        if (run is None or run.context_id != context.id or run.artifact_version_id != slot.artifact_version_id\n'
                '                or run.trial_slot_id != slot.id or run.experiment_id != experiment.id):\n'
                '            drift.add("run_binding")',
                '        if False:\n            drift.add("run_binding")',
            ),
        )
    ),
    {
        "name": "public_assessments_are_recomputed_on_readback",
        "file": "shiftwork/comparison_flow.py",
        "old": "if (tuple(expected_public) != recorded_public",
        "new": "if (False",
        "tests": f"{LIFECYCLE}::test_public_and_protected_assessment_tampering_blocks_outcome",
        "expect": "test_public_and_protected_assessment_tampering_blocks_outcome",
    },
    {
        "name": "protected_assessments_are_recomputed_on_readback",
        "file": "shiftwork/comparison_flow.py",
        "old": "if expected_protected != protected_assessments:",
        "new": "if False:",
        "tests": f"{LIFECYCLE}::test_public_and_protected_assessment_tampering_blocks_outcome",
        "expect": "test_public_and_protected_assessment_tampering_blocks_outcome",
    },
    {
        "name": "diagnostic_panel_never_projects_a_comparison",
        "file": "shiftwork/experiments.py",
        "old": "diagnostics = [item for item in experiments if item.kind is ExperimentKind.DIAGNOSTIC]",
        "new": "diagnostics = list(experiments)",
        "tests": f"{LIFECYCLE}::test_the_investigate_station_projects_a_comparison_only_as_a_comparison",
        "expect": "test_the_investigate_station_projects_a_comparison_only_as_a_comparison",
    },
    {
        "name": "retired_reservation_state_is_invalidated",
        "file": "shiftwork/comparison_flow.py",
        "old": "repo.update_exposure_reservation_state(conn, reservation.id, \"INVALIDATED\")",
        "new": "repo.update_exposure_reservation_state(conn, reservation.id, \"ACTIVE\")",
        "tests": f"{LIFECYCLE}::test_retiring_a_compromised_comparison_keeps_evidence_and_blocks_reuse",
        "expect": "test_retiring_a_compromised_comparison_keeps_evidence_and_blocks_reuse",
    },
]


# Use a fresh, uncommitted path for each round. Exclusive creation refuses to
# overwrite archived evidence, including logs committed after their first run.
RESULTS_LOG = ROOT / "docs" / "plans" / "shiftwork" / "evidence" / "slice20-next-slice16-mutation-2026-10-02.txt"


def main() -> int:
    RESULTS_LOG.touch(exist_ok=False)
    failures = 0
    for index, case in enumerate(CASES, 1):
        label = f"[{index}/{len(CASES)}] {case['name']}"
        print(f"{label} ...", flush=True)
        with RESULTS_LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"{label} START\n")
        result = runner.run_mutation(case)
        print(f"  {result['status']} restored={result.get('sha256_restored', False)} {result.get('detail', result.get('reason', ''))}", flush=True)
        with RESULTS_LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"{label} {result['status']} restored={result.get('sha256_restored', False)} "
                         f"{result.get('detail', result.get('reason', ''))}\n")
        failures += result["status"] != "FAIL_CAUGHT"
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
