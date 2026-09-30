"""Named S19 replay-guard mutations. Each source file is restored byte-for-byte.

Every row faults one guard of ``orchestrator.replay_assessment`` (or one helper
it delegates to) and must fail its named test at an assertion, never as a crash
or a syntax error. The scope column narrows a replacement to one function so a
shared statement elsewhere in the file is not touched.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = "tests/orchestrator/test_replay.py::"
ORCH = "shiftwork/orchestrator.py"
CASES = (
    ("current_mission_used", ORCH,
     "mission_bytes = base64.b64decode(context.mission_bytes_base64, validate=True)",
     "mission_bytes = config.PIVOT_MISSION.read_bytes()",
     "test_semantic_replay_uses_original_inputs_and_writes_nothing", 1, "replay_assessment"),
    ("current_state_used", ORCH,
     "snapshot_bytes = repo.get_run_snapshot_bytes(conn, run.id)",
     "snapshot_bytes = config.PIVOT_PUBLIC_STATE.read_bytes()",
     "test_semantic_replay_uses_original_inputs_and_writes_nothing", 1, "replay_assessment"),
    ("zero_write_added", ORCH,
     '    status = "DIFFERENT" if check_differences or event_draft_differences else "IDENTICAL"\n'
     "    return ReplayReport(run_id=run.id, status=status,",
     '    conn.execute("UPDATE runs SET attempt_number = 99 WHERE id = ?", (run.id,))\n'
     '    status = "DIFFERENT" if check_differences or event_draft_differences else "IDENTICAL"\n'
     "    return ReplayReport(run_id=run.id, status=status,",
     "test_semantic_replay_uses_original_inputs_and_writes_nothing", 1, "replay_assessment"),
    ("captured_output_ignored", ORCH,
     "response = task_contract.validate_response_envelope(spec, output.body)",
     'response = task_contract.validate_response_envelope(spec, b"{}")',
     "test_semantic_replay_uses_original_inputs_and_writes_nothing", 1, "replay_assessment"),
    ("status_never_different", ORCH,
     'status = "DIFFERENT" if check_differences or event_draft_differences else "IDENTICAL"',
     'status = "IDENTICAL"',
     "test_chain_verification_and_semantic_replay_fail_independently", 1, "replay_assessment"),
    ("checks_not_compared", ORCH,
     'for field in ("verdict", "observed_ref", "reason_code"):',
     "for field in ():",
     "test_chain_verification_and_semantic_replay_fail_independently", 1, "_check_differences"),
    ("events_not_compared", ORCH,
     "    event_draft_differences = _event_draft_differences(\n"
     "        _stored_operation_drafts(conn, run, context.engagement_slug), drafts)",
     "    event_draft_differences = []",
     "test_stored_event_draft_divergence_reports_different", 1, "replay_assessment"),
    ("event_fields_not_compared", ORCH,
     'for field in ("event_type", "cause_refs", "payload", "synthetic"):',
     "for field in ():",
     "test_stored_event_draft_divergence_reports_different", 1, "_event_draft_differences"),
    ("legacy_guessed", ORCH,
     "if run.purpose is RunPurpose.LEGACY_OPERATION or run.context_id is None:",
     "if False:",
     "test_legacy_replay_reports_unknown_missing_inputs", 1, "replay_assessment"),
    ("missing_inputs_guessed", ORCH,
     "    if (context is None or workload is None or snapshot_bytes is None\n"
     "            or not outputs or run.selection_id is None):",
     "    if False:",
     "test_replay_reports_unknown_when_the_captured_context_is_gone", 1, "replay_assessment"),
    ("experiment_guard_removed", ORCH,
     "    if run.purpose is not RunPurpose.OPERATION:",
     "    if False:",
     "test_replay_refuses_experimental_and_unfinalized_runs", 1, "replay_assessment"),
    ("unfinalized_guard_removed", ORCH,
     "if run.state is not RunState.FINALIZED:",
     "if False:",
     "test_replay_refuses_experimental_and_unfinalized_runs", 1, "replay_assessment"),
    ("unknown_run_guessed", ORCH,
     "if run is None:",
     "if False:",
     "test_replay_refuses_unknown_runs", 1, "replay_assessment"),
    ("capture_integrity_unguarded", ORCH,
     "if (_hash_bytes(mission_bytes) != context.mission_hash",
     "if (False and _hash_bytes(mission_bytes) != context.mission_hash",
     "test_replay_reports_unknown_when_capture_integrity_is_broken", 1, "replay_assessment"),
    ("workload_coverage_unguarded", ORCH,
     "if set(captured) != set(range(1, workload.request_count + 1)):",
     "if False:",
     "test_replay_reports_unknown_when_captured_outputs_do_not_cover_the_workload", 1,
     "replay_assessment"),
    ("check_inventory_unguarded", ORCH,
     "if stored_check is None or replayed_check is None:",
     "if False:",
     "test_stored_check_inventory_divergence_reports_both_directions", 1, "_check_differences"),
)

EXPECTED_ASSERTIONS = {
    "current_mission_used": "assert 'UNKNOWN_MISSING_INPUTS' == 'IDENTICAL'",
    "current_state_used": "assert 'UNKNOWN_MISSING_INPUTS' == 'IDENTICAL'",
    "zero_write_added": "historical runs bytes changed",
    "captured_output_ignored": "assert 'DIFFERENT' == 'IDENTICAL'",
    "status_never_different": "assert 'IDENTICAL' == 'DIFFERENT'",
    "checks_not_compared": "assert 'IDENTICAL' == 'DIFFERENT'",
    "events_not_compared": "assert 'IDENTICAL' == 'DIFFERENT'",
    "event_fields_not_compared": "assert 'IDENTICAL' == 'DIFFERENT'",
    "legacy_guessed": "Failed: legacy replay raised LifecycleError",
    "missing_inputs_guessed": "Failed: a vanished capture reported",
    "experiment_guard_removed": "Failed: wrong failure type ValueError",
    "unfinalized_guard_removed": "Failed: an unfinalized run replayed",
    "unknown_run_guessed": "Failed: wrong failure type AttributeError",
    "capture_integrity_unguarded": "assert 'DIFFERENT' == 'UNKNOWN_MISSING_INPUTS'",
    "workload_coverage_unguarded": "assert 'IDENTICAL' == 'UNKNOWN_MISSING_INPUTS'",
    "check_inventory_unguarded": "Failed: a changed check inventory raised AttributeError",
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
    failures = []
    for name, relative, needle, replacement, test, expected_count, scope in CASES:
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
            command = [sys.executable, "-m", "pytest", TEST + test, "-q", "--tb=short"]
            result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                    text=True, timeout=240, check=False)
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
    print(f"S19_MUTATIONS caught={len(CASES) - len(failures)} total={len(CASES)} "
          f"unproven={','.join(failures) or 'none'}", flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
