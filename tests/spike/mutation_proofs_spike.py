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
`run_*`, `emit_*` and `budget_*` rows are the F2 stamping rule. A row reporting
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
