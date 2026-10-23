"""S44 named-assertion faults, byte-identical restoration and clean controls.

Run serially against source checks. No live calls or credential reads.
"""
import hashlib
from pathlib import Path
import re
import subprocess
import sys

TEST = "tests/orchestrator/test_diagnostic_repetitions.py"
EX = "shiftwork/experiments.py"
REC = "shiftwork/diagnostic_recording.py"
MUTATIONS = [
    ("retained_count", EX, "    if len(runs) != count:\n", "    if False:\n",
     "test_summary_refuses_a_missing_run_row", "DID NOT RAISE"),
    ("retained_assessments", EX,
     "                or {(row.request_ordinal, row.task_id) for row in assessments} != expected):",
     "                or False):", "test_summary_refuses_an_unexpected_assessment_row", "DID NOT RAISE"),
    ("retained_capture", EX,
     "                or {output.request_ordinal for output in outputs} != set(range(1, len(mission.request_specs) + 1))\n",
     "", "test_summary_refuses_missing_capture_instead_of_calling_it_a_model_miss", "DID NOT RAISE"),
    ("retained_reply", EX,
     '            if len(replies) != len(mission.request_specs) or any(\n                    not _has_retained_reply(row) for row in replies):',
     '            if False:', "test_summary_refuses_a_missing_model_reply", "DID NOT RAISE"),
    ("raw_reply_parse", EX,
     '    except (ValueError, KeyError, IndexError, TypeError):\n        return False\n',
     '    except (ValueError, KeyError, IndexError, TypeError):\n        return True\n',
     "test_summary_refuses_an_unreadable_retained_model_reply[bad-json]", "DID NOT RAISE"),
    ("raw_reply_content", EX, '        return isinstance(message, dict) and "content" in message\n',
     '        return True\n', "test_summary_refuses_an_unreadable_retained_model_reply[missing-content]", "DID NOT RAISE"),
    ("raw_reply_prefix", EX,
     '    if not observation.raw_payload_ref.startswith("data:application/json;base64,"):\n        return False\n',
     '', "test_summary_refuses_an_unreadable_retained_model_reply[wrong-prefix]", "DID NOT RAISE"),
    ("frozen_declaration", EX, "        if diagnostic_context_hash(context) != context.content_hash:",
     "        if False:", "test_changed_frozen_count_is_refused_even_if_storage_is_modified", "DID NOT RAISE"),
    ("idempotency_count", EX, "                and repetition_count(conn, replay) == public_repetitions\n", "",
     "test_repetition_count_changed_after_results_is_refused", "a published declaration cannot change"),
    ("reserve_every_run", EX, "        for _ in range(public_repetitions):\n", "        for _ in range(1):\n",
     "test_each_repetition_is_retained_and_rate_counts_the_actual_miss", "each declared repetition must retain"),
    ("trial_version_binding", EX,
     '                "artifact_version_id": run.artifact_version_id if run is not None else None,\n', '',
     "test_each_repetition_is_retained_and_rate_counts_the_actual_miss", "retained trials must publish their exact version binding"),
    ("rate_numerator", EX, '"misses": len(misses), "total": count',
     '"misses": len(misses) + 1, "total": count',
     "test_each_repetition_is_retained_and_rate_counts_the_actual_miss", "the displayed rate must count"),
    ("optional_not_a_miss_rate", EX, '            if not task.required:\n                continue\n', '',
     "test_each_repetition_is_retained_and_rate_counts_the_actual_miss", "only required tasks have miss rates"),
    ("api_meter", "shiftwork/api/routes.py",
     '        if adapter == "tokenfactory" and body.public_repetitions > 1 and live_budget is None:',
     '        if False:', "test_api_refuses_repetitions_without_a_meter", "a repeated live batch needs"),
    ("direct_meter", EX,
     '    if (run.adapter == orchestrator.TokenFactoryAdapter.name\n            and repetition_count(conn, experiment) > 1 and live_budget is None):',
     '    if False:', "test_direct_execution_refuses_repetitions_without_a_meter", "DID NOT RAISE"),
    ("restart", "shiftwork/orchestrator.py",
     '    for experiment_id in diagnostics:\n        repo.update_experiment_state(conn, experiment_id, "FAILED")\n',
     '', "test_restart_marks_every_unfinished_repetition_failed_without_retry", "restart must terminate"),
    ("operation_ceiling", "shiftwork/live_budget.py",
     '        if self.operations >= self.max_operations:\n            raise ValueError("live operation Sandbox operation ceiling reached")\n',
     '', "test_meter_refuses_the_next_call_operation_and_overspend", "DID NOT RAISE"),
    ("call_ceiling", "shiftwork/live_budget.py",
     '        if model != self.model or self.calls >= self.max_calls:\n            raise ValueError("live diagnostic inference call ceiling reached")\n',
     '', "test_meter_refuses_the_next_call_operation_and_overspend", "DID NOT RAISE"),
    ("spend_ceiling", "shiftwork/live_budget.py",
     '        if self._cost(self.calls + 1) > self.max_projected_usd:\n            raise ValueError("live diagnostic projected inference spend ceiling reached")\n',
     '', "test_meter_refuses_the_next_call_operation_and_overspend", "DID NOT RAISE"),
    ("diagnostic_preflight_shape", "shiftwork/live_budget.py",
     '        if (model != self.model or type(repetitions) is not int',
     '        if (False and model != self.model or False and type(repetitions) is not int',
     "test_meter_preflight_refuses_wrong_model_and_unaffordable_batch", "DID NOT RAISE"),
    ("diagnostic_preflight_spend", "shiftwork/live_budget.py",
     '        if self._cost(repetitions * requests) > self.max_projected_usd:', '        if False:',
     "test_meter_preflight_refuses_wrong_model_and_unaffordable_batch", "DID NOT RAISE"),
    ("recording_digest", REC, '        if payload["digest"] != recording_digest(payload):',
     '        if False:', "test_recording_rejects_incomplete_or_mismatched_provenance[digest]", "DID NOT RAISE"),
    ("recording_source", REC, ' or payload["source_evidence_mode"] != "ISOLATED_LIVE"',
     '', "test_recording_rejects_incomplete_or_mismatched_provenance[source]", "DID NOT RAISE"),
    ("recording_starter", REC,
     '                or hashlib.sha256(version.files["service.py"].encode()).hexdigest() != starter_pin\n',
     '', "test_recording_rejects_incomplete_or_mismatched_provenance[starter]", "DID NOT RAISE"),
    ("recording_count", REC, ' or len(payload["trials"]) != count',
     '', "test_recording_rejects_incomplete_or_mismatched_provenance[extra_trial]", "DID NOT RAISE"),
    ("recording_unique_trials", REC,
     '                or len({trial["run_id"] for trial in payload["trials"]}) != count',
     '', "test_recording_rejects_incomplete_or_mismatched_provenance[duplicate_trial]", "DID NOT RAISE"),
    ("recording_mode", REC,
     '"executor_class": EvidenceMode.RECORDED_INSPECTION, "resource_limits_json": limits,',
     '"executor_class": EvidenceMode.ISOLATED_LIVE, "resource_limits_json": limits,',
     "test_recorded_capture_replays_exact_rows_without_credentials_or_eligibility[recorded]", "AssertionError"),
    ("recording_trial_complete", REC,
     '            if (trial["state"] != "COMPLETE" or trial["evidence_mode"] != "ISOLATED_LIVE"',
     '            if (False and trial["state"] != "COMPLETE" or trial["evidence_mode"] != "ISOLATED_LIVE"',
     "test_recording_rejects_incomplete_or_mismatched_provenance[unfinished_trial]", "DID NOT RAISE"),
    ("recording_budget", REC, '    if used >= orchestrator.DIAGNOSTIC_EXPERIMENTS_PER_SHIFT:',
     '    if False:', "test_recorded_replay_reuses_context_and_idempotency_but_keeps_the_two_slot_cap", "DID NOT RAISE"),
]


def branch():
    assert subprocess.check_output(["git", "branch", "--show-current"], text=True).strip() == "shiftwork/slice-44"


def run(target):
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", target],
                          capture_output=True, text=True, timeout=60)


selected = set(sys.argv[1:])
survivors = 0
for name, filename, old, new, test, assertion in MUTATIONS:
    if selected and name not in selected:
        continue
    path = Path(filename)
    original = path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    source = original.decode()
    assert source.count(old) == 1, f"{name}: anchor must match once"
    branch()
    path.write_bytes(source.replace(old, new, 1).encode())
    try:
        result = run(f"{TEST}::{test}")
    finally:
        branch()
        path.write_bytes(original)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    failed = re.findall(r"^FAILED (\S+)", result.stdout, re.M)
    killed = (result.returncode == 1 and failed == [f"{TEST}::{test}"]
              and assertion in result.stdout
              and ("AssertionError" in result.stdout or "DID NOT RAISE" in result.stdout)
              and "ERROR at" not in result.stdout)
    restored = run(f"{TEST}::{test}")
    assert restored.returncode == 0, f"{name}: restored control failed\n{restored.stdout}"
    print(f"{name}: {'KILLED at named assertion' if killed else 'SURVIVED'}; bytes restored; clean control passed", flush=True)
    if not killed:
        print(result.stdout[-5000:], flush=True)
    survivors += not killed
print(f"SURVIVORS {survivors}", flush=True)
sys.exit(bool(survivors))
