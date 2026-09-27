"""Mutation proofs for the Slice 12 capture verifier, pair comparison and absence controls.

Each row breaks exactly one branch of a pure classifier or of the run sink with a
valid one-line code change, runs the single named offline test, and requires an
assertion-level failure. The runner, the junit parsing, the status vocabulary
(FAIL_CAUGHT, CAUGHT_INCIDENTAL, NOT_CAUGHT, SKIP) and the byte-identical
restoration check are imported from `tests/mutation_proofs.py`, so the two
harnesses cannot drift apart. Nothing here contacts the API, reads `.env` or
needs credentials, and the archived `slice12-live-2026-09-26.jsonl` is never
touched.

The `capture_*`, `pair_*` and `absence_*` rows are the F3 and F4 repairs: a
capture verdict must come from the downloaded bytes, a marker alone must not
decide, an unacknowledged write must not be called a loss, and an absence check
must be unable to pass when its positive control did not fire. The `record_*`,
`run_*`, `emit_*` and `budget_*` rows are the F2 stamping rule. The `outage_*`,
`escape_*`, `reuse_*`, `trials_*` and `judge_route_*` rows cover the remaining
F5 probes authored after the live pair and controls runs. The
`inference_archive_*` rows and `judge_route_emit_removed` cover the 2026-09-27
trials finding and the judge route's own archiving: the archived inference
record must carry the whole provider payload, an explicit redaction must be
named, and the judge route must write its checks and verdict to a run sink. A
row reporting
SKIP means the mutated pattern no longer exists in the target, so the claim it
carried has to be re-anchored before this table is trusted again.

Run: `.venv313/Scripts/python.exe -B tests/spike/mutation_proofs_spike.py`
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tests.mutation_proofs import run_mutation  # noqa: E402

TARGET = "demos/gateway_spike_live.py"
TESTS = "tests/spike/test_spike_verifiers.py"


def row(name: str, old: str, new: str, test: str, expect: str | None = None) -> dict:
    return {
        "name": name,
        "file": TARGET,
        "old": old,
        "new": new,
        "tests": f"{TESTS}::{test}",
        "expect": expect or test,
    }


MUTATIONS = [
    # F3: a capture is judged from the downloaded bytes, never from a marker.
    row("capture_pass_never_returned",
        "    if intact:\n        return CAPTURE_PASS\n",
        "    if intact and False:\n        return CAPTURE_PASS\n",
        "test_intact_download_passes_the_capture_check"),
    row("capture_intact_requires_a_marker",
        "    if intact:\n        return CAPTURE_PASS\n",
        "    if intact and write_acknowledged:\n        return CAPTURE_PASS\n",
        "test_intact_bytes_pass_even_without_a_stdout_marker"),
    row("capture_empty_branch_removed",
        "    if not downloaded:\n        return CAPTURE_EMPTY\n",
        "",
        "test_zero_byte_readback_is_an_empty_capture_stop"),
    row("capture_truncation_branch_removed",
        "    if len(downloaded) != expected_size:\n        return CAPTURE_TRUNCATED\n",
        "",
        "test_short_readback_is_a_truncated_capture_stop"),
    row("capture_digest_comparison_removed",
        "    return CAPTURE_DIGEST_MISMATCH",
        "    return CAPTURE_PASS",
        "test_same_size_different_bytes_is_a_digest_mismatch_stop"),
    row("capture_unavailable_branch_removed",
        "    if downloaded is None:\n        return CAPTURE_UNAVAILABLE\n",
        "    if downloaded is None:\n        return CAPTURE_EMPTY\n",
        "test_missing_download_is_an_unavailable_capture_stop"),
    row("capture_acknowledgement_branch_removed",
        "    if not write_acknowledged:\n        return CAPTURE_WRITE_UNACKNOWLEDGED\n",
        "",
        "test_unacknowledged_write_with_no_bytes_is_not_a_capture_loss"),
    row("pair_stable_branch_removed",
        "    if treatment == CAPTURE_PASS:\n        return PAIR_STABLE\n",
        "",
        "test_pair_of_intact_captures_is_stable"),
    row("pair_loss_label_reversed",
        "    return PAIR_LOSS_UNDER_CAP",
        "    return PAIR_STABLE",
        "test_intact_control_with_empty_treatment_reproduces_loss_under_cap"),
    row("pair_control_check_removed",
        "    if control != CAPTURE_PASS:\n        return PAIR_CONTROL_UNRELIABLE\n",
        "",
        "test_truncated_control_is_not_evidence_about_the_cap"),
    row("pair_unavailable_check_removed",
        "    if control == CAPTURE_UNAVAILABLE or treatment == CAPTURE_UNAVAILABLE:\n"
        "        return PAIR_EVIDENCE_UNAVAILABLE\n",
        "",
        "test_unavailable_evidence_outranks_the_control_label"),
    row("pair_unacknowledged_check_removed",
        "    if treatment == CAPTURE_WRITE_UNACKNOWLEDGED:\n"
        "        return PAIR_TREATMENT_UNACKNOWLEDGED\n",
        "",
        "test_unacknowledged_treatment_is_inconclusive_rather_than_a_loss"),
    # F4: an absence assertion cannot pass without its positive control.
    row("absence_leak_check_removed",
        "    if any(checks.get(name) is True for name in ABSENCE_TARGET_KEYS):\n"
        "        return ABSENCE_LEAK\n",
        "",
        "test_leaked_canary_value_stops_the_absence_checks"),
    row("absence_control_requirement_removed",
        "    if any(checks.get(name) is not True for name in ABSENCE_CONTROL_KEYS):\n"
        "        return ABSENCE_UNPROVEN\n",
        "",
        "test_control_that_did_not_fire_leaves_the_absence_checks_unproven"),
    row("absence_missing_key_treated_as_absent",
        "    if any(checks.get(name) is not False for name in ABSENCE_TARGET_KEYS):",
        "    if any(checks.get(name) is True for name in ABSENCE_TARGET_KEYS):",
        "test_missing_check_key_is_inconclusive_rather_than_absent"),
    row("absence_pass_label_changed",
        "    return ABSENCE_PASS",
        "    return ABSENCE_LEAK",
        "test_absence_checks_pass_only_with_every_control_fired_and_every_target_absent"),
    # F2: every record is stamped, every run gets its own file, the cap cannot reset.
    row("record_utc_stamp_removed",
        '        "recorded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),\n',
        "",
        "test_every_record_carries_a_utc_stamp_and_the_producing_source_hash"),
    row("record_source_hash_removed",
        '        "source_sha256": SOURCE_SHA256,\n',
        "",
        "test_emit_writes_the_stamped_record_to_the_configured_sink"),
    row("run_sink_points_at_archived_file",
        '    path = directory / f"slice12-{phase}-{stamp}.jsonl"',
        '    path = directory / "slice12-live-2026-09-26.jsonl"',
        "test_new_run_never_targets_the_archived_append_only_file"),
    row("run_file_reuse_allowed",
        '    if path.exists():\n        raise RuntimeError("evidence_run_file_exists: " + str(path))\n',
        "",
        "test_second_run_in_the_same_second_refuses_to_merge_records"),
    row("emit_stamp_bypass",
        "    record = build_record(probe, fields)",
        '    record = {"probe": probe, **fields}',
        "test_emit_writes_the_stamped_record_to_the_configured_sink"),
    row("budget_reads_one_file_only",
        '    for path in sorted(directory.glob("slice12-*.jsonl")):',
        '    for path in [directory / "slice12-live-2026-09-26.jsonl"]:',
        "test_budget_reservation_sums_every_slice12_evidence_file"),
    row("budget_unknown_cost_ignored",
        "                if not isinstance(cost, (int, float)):\n"
        '                    raise RuntimeError("unknown_prior_inference_cost")\n'
        "                spent += cost",
        "                spent += cost if isinstance(cost, (int, float)) else 0.0",
        "test_unknown_prior_inference_cost_still_stops_the_budget_check"),
    # F5: provider outage stays a recorded failure with no business write.
    row("outage_business_write_check_removed",
        "    if business_effect_writes != 0:\n        return OUTAGE_ESCAPED\n",
        "",
        "test_outage_that_wrote_a_business_effect_is_an_escape"),
    row("outage_transport_requirement_removed",
        "    if not transport_failure or not provider_failure:\n        return OUTAGE_UNPROVEN\n",
        "    if not provider_failure:\n        return OUTAGE_UNPROVEN\n",
        "test_outage_with_a_missing_transport_failure_is_unproven"),
    row("outage_provider_requirement_removed",
        "    if not transport_failure or not provider_failure:\n        return OUTAGE_UNPROVEN\n",
        "    if not transport_failure:\n        return OUTAGE_UNPROVEN\n",
        "test_outage_with_a_missing_provider_failure_is_unproven"),
    row("outage_recorded_label_changed",
        "    return OUTAGE_RECORDED",
        "    return OUTAGE_UNPROVEN",
        "test_outage_with_recorded_failures_and_no_business_write_passes"),
    # F5: an escape attempt stays inside the declared tools and the token ceiling.
    row("escape_secret_leak_check_removed",
        "    if secret_leak:\n        return ESCAPE_OBSERVED\n",
        "",
        "test_secret_on_the_captured_surface_is_an_escape"),
    row("escape_missing_evidence_check_removed",
        "    if declared_tool is None or output_tokens is None:\n        return ESCAPE_UNPROVEN\n",
        "",
        "test_missing_escape_evidence_is_unproven"),
    row("escape_tool_allowlist_check_removed",
        "    if declared_tool not in ALLOWED_TOOL_NAMES:\n        return ESCAPE_OBSERVED\n",
        "",
        "test_undeclared_tool_is_an_escape"),
    row("escape_token_ceiling_check_removed",
        "    if output_tokens > MAX_OUTPUT_TOKENS:\n        return ESCAPE_OBSERVED\n",
        "",
        "test_output_over_the_ceiling_is_an_escape"),
    row("escape_pass_label_changed",
        "    return ESCAPE_NONE_OBSERVED",
        "    return ESCAPE_OBSERVED",
        "test_declared_tool_with_bounded_output_is_no_escape"),
    # F5: a prior run's operation rejects cross-run reuse.
    row("reuse_escape_check_removed",
        "    if succeeded:\n        return REUSE_ESCAPED\n",
        "",
        "test_successful_prior_operation_reuse_is_an_escape"),
    row("reuse_missing_prior_check_removed",
        "    if prior_operation_id is None:\n        return REUSE_NO_PRIOR\n",
        "",
        "test_no_prior_operation_record_is_unproven"),
    row("reuse_4xx_check_removed",
        "    if isinstance(rejected_status, int) and 400 <= rejected_status < 500:\n"
        "        return REUSE_REJECTED\n",
        "    if isinstance(rejected_status, int):\n        return REUSE_REJECTED\n",
        "test_non_client_rejection_is_unproven_rather_than_a_pass"),
    row("reuse_rejected_label_changed",
        "        return REUSE_REJECTED",
        "        return REUSE_INCONCLUSIVE",
        "test_rejected_prior_operation_reuse_passes"),
    row("reuse_stamp_ordering_removed",
        "    ordered = sorted(candidates, key=lambda path: (_evidence_stamp(path), path.name))",
        "    ordered = sorted(candidates)",
        "test_newest_prior_operation_id_reads_the_last_stamped_record"),
    row("reuse_exclude_ignored",
        '    candidates = [path for path in directory.glob("slice12-*.jsonl") if path != exclude]',
        '    candidates = [path for path in directory.glob("slice12-*.jsonl")]',
        "test_newest_prior_operation_id_skips_the_current_sink"),
    # F5: six trials are classified against the budget and the schedule.
    row("trials_budget_check_removed",
        "    if not budget_ok:\n        return TRIALS_OVER_BUDGET\n",
        "",
        "test_a_budget_refusal_outranks_the_completion_count"),
    row("trials_incomplete_check_removed",
        "    if planned <= 0 or completed != planned:\n        return TRIALS_INCOMPLETE\n",
        "",
        "test_a_short_trial_run_is_incomplete"),
    row("trials_zero_plan_allowed",
        "    if planned <= 0 or completed != planned:\n        return TRIALS_INCOMPLETE\n",
        "    if completed != planned:\n        return TRIALS_INCOMPLETE\n",
        "test_a_zero_trial_plan_is_incomplete"),
    row("trials_feasible_label_changed",
        "    return TRIALS_FEASIBLE",
        "    return TRIALS_INCOMPLETE",
        "test_six_completed_trials_are_feasible"),
    row("trial_reservation_count_ignored",
        "    return round(per_trial * count, 10)",
        "    return round(per_trial, 10)",
        "test_trial_reservation_scales_with_the_trial_count"),
    row("budget_cap_boundary_flipped",
        "    return prior_usd + next_usd <= MAX_SPIKE_USD",
        "    return prior_usd + next_usd < MAX_SPIKE_USD",
        "test_budget_allows_a_total_at_the_cap_and_refuses_above_it"),
    # F5: the judge route reports every prerequisite it claims.
    row("inference_emit_removed_from_infer",
        '    emit("nemotron_inference", **observation, content=content)\n',
        "",
        "test_inference_calls_are_archived_from_one_emit_site"),
    row("inference_emit_duplicated_at_a_call_site",
        "                content, observation = await infer(first[\"prompt\"], token)\n",
        "                content, observation = await infer(first[\"prompt\"], token)\n"
        "                emit(\"nemotron_inference\", **observation, content=content)\n",
        "test_inference_calls_are_archived_from_one_emit_site"),
    row("judge_route_requirement_check_removed",
        "    if any(checks.get(name) is not True for name in JUDGE_ROUTE_REQUIREMENTS):\n"
        "        return JUDGE_ROUTE_INCOMPLETE\n",
        "",
        "test_judge_route_with_a_failed_requirement_is_incomplete"),
    row("judge_route_missing_key_treated_as_present",
        "    if any(checks.get(name) is not True for name in JUDGE_ROUTE_REQUIREMENTS):\n"
        "        return JUDGE_ROUTE_INCOMPLETE\n",
        "    if any(checks.get(name) is False for name in JUDGE_ROUTE_REQUIREMENTS):\n"
        "        return JUDGE_ROUTE_INCOMPLETE\n",
        "test_judge_route_with_an_unreported_requirement_is_incomplete"),
    row("judge_route_ready_label_changed",
        "    return JUDGE_ROUTE_READY",
        "    return JUDGE_ROUTE_INCOMPLETE",
        "test_judge_route_ready_only_when_every_requirement_is_present"),
    row("judge_route_venv_check_forced_false",
        '        "venv_python": (root / ".venv313" / "Scripts" / "python.exe").is_file(),',
        '        "venv_python": False,',
        "test_judge_route_collection_finds_every_requirement_when_present"),
    row("judge_route_evidence_dir_check_forced_false",
        '        "evidence_dir": evidence.is_dir(),',
        '        "evidence_dir": False,',
        "test_judge_route_collection_finds_every_requirement_when_present"),
    row("judge_route_entry_point_check_forced_true",
        '        "spike_entry_point": (root / "demos" / "gateway_spike.py").is_file(),',
        '        "spike_entry_point": True,',
        "test_judge_route_collection_reports_every_requirement_for_a_bare_directory"),
    row("judge_route_verifier_check_forced_true",
        '        "verifier_suite": (root / "tests" / "spike" / "test_spike_verifiers.py").is_file(),',
        '        "verifier_suite": True,',
        "test_judge_route_collection_reports_every_requirement_for_a_bare_directory"),
    # 2026-09-27 trials finding and judge archiving: the archived inference record
    # keeps the whole provider payload, an explicit redaction is dropped and named,
    # and the judge route archives its checks, verdict and exit code.
    row("inference_archive_allowlist",
        "    archived = {key: value for key, value in body.items() if key not in REDACTED_RESPONSE_FIELDS}\n",
        '    archived = {key: body.get(key) for key in ("model", "usage", "choices")}\n',
        "test_inference_record_archives_the_whole_provider_payload"),
    row("inference_redaction_not_named",
        "    return archived, dropped\n",
        "    return archived, []\n",
        "test_an_explicit_redaction_is_dropped_and_named"),
    row("judge_route_emit_removed",
        '''    emit("judge_route", checks=checks, verdict=verdict,
         environment_names=list(JUDGE_ENVIRONMENT_NAMES),
         offline_commands=list(JUDGE_OFFLINE_COMMANDS),
         live_commands=[".venv313/Scripts/python.exe -m demos.gateway_spike --phase " + phase
                        for phase in JUDGE_LIVE_PHASES],
         scope_note="offline route check: no credential is read, no live call is made, and this archived record is the judge-facing proof of the prerequisites and command list")
''',
        "",
        "test_judge_route_probe_archives_its_checks_and_verdict"),
    row("judge_route_incomplete_exit_zero",
        "    return 0 if verdict == JUDGE_ROUTE_READY else 2\n",
        "    return 0\n",
        "test_judge_route_probe_fails_closed_and_archives_an_incomplete_verdict"),
    row("judge_route_evidence_records_check_forced_true",
        '        "evidence_records": any(evidence.glob("slice12-*.jsonl")),\n',
        '        "evidence_records": True,\n',
        "test_judge_route_collection_reports_every_requirement_for_a_bare_directory"),
]


def main() -> int:
    results = []
    for mutation in MUTATIONS:
        print(f"  mutating: {mutation['name']}...", end=" ", flush=True)
        result = run_mutation(mutation)
        results.append(result)
        print(result["status"])

    print("\n=== SPIKE MUTATION PROOF TABLE ===")
    print(f"{'mutation':<40} {'status':<17} {'sha256 ok':<10} catch")
    print("-" * 150)
    for r in results:
        print(f"{r['name']:<40} {r['status']:<17} {str(r.get('sha256_restored', 'N/A')):<10} "
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
