"""Client rate guard faults, named Node assertions and byte-identical controls."""

import hashlib
from pathlib import Path
import subprocess
import sys

FILE = Path("shiftwork/client/evidence.js")
TEST = "tests/client/comparison_rates.test.mjs"
FAULTS = [
    ("identity_missing", "!row.run_id || ", "", "client refuses a repetition without a run identity", "a missing run identity must be refused"),
    ("identity_duplicate", "seen.has(row.run_id)", "false", "comparison rate refuses a fabricated rate and duplicate run identity", "one run cannot supply two repetitions"),
    ("summary_agreement", "if (summary.passed !== passed || summary.retained !== retained || summary.declared !== declared || rows.length > declared)", "if (false)", "comparison rate refuses a fabricated rate and duplicate run identity", "a fabricated comparison rate must be refused"),
    ("frozen_plan", "rows.length > declared", "false", "client refuses more repetitions than the frozen plan", "retained repetitions cannot exceed the frozen plan"),
    ("mandatory", "row.task_assessments.every(task => task.mandatory_pass)", "true", "client refuses a failed mandatory row counted as a pass", "a failed mandatory row cannot count as passing"),
    ("capture_body", " && output.body_base64", "", "comparison rate refuses an empty retained capture counted as passing", "an empty retained capture cannot count as passing"),
    ("capture_ordinals", ".size === trial.request_count", ".size >= 0", "client refuses missing capture ordinals counted as a pass", "a missing capture cannot count as passing"),
    ("public_state", "row.state === 'COMPLETE' && row.task_assessments.length > 0", "row.task_assessments.length > 0", "client refuses a failed execution counted as a pass", "a failed execution cannot count as passing"),
    ("retained_evidence", "rows.filter(({row}) => ['COMPLETE', 'FAILED'].includes(row.state) && (row.outputs.length || row.observations.length)).length", "rows.filter(({row}) => ['COMPLETE', 'FAILED'].includes(row.state)).length", "client refuses an unexecuted reservation counted as retained evidence", "an unexecuted reservation cannot count as retained evidence"),
    ("cause_cutoff", "if (reply.finish_reason === 'length')", "if (false)", "comparison rate counts each retained repetition and attributes its failed reply", "cut-off cause must come from the same retained reply"),
    ("cause_request", "row.public_payload_json?.request_ordinal === assessment.request_ordinal", "true", "comparison causes distinguish invalid, omitted, unknown and other failures", "failure categories must be attributable"),
    ("cause_invalid", "if (reply.plan_failure)", "if (false)", "comparison causes distinguish invalid, omitted, unknown and other failures", "failure categories must be attributable"),
    ("cause_omitted", "!reply.plan.some(step => step.task_type === assessment.task_id)", "false", "comparison causes distinguish invalid, omitted, unknown and other failures", "failure categories must be attributable"),
    ("cause_execution", "if (row.state === 'FAILED' && (row.outputs.length || row.observations.length))", "if (false)", "a failed public execution stays distinct from model check failures", "a driver failure must not be attributed to model task omission"),
]


def branch():
    assert subprocess.check_output(["git", "branch", "--show-current"], text=True).strip() == "shiftwork/slice-45"


def main():
    output = Path("/tmp/shiftwork-s45-client-mutations-20261024")
    output.mkdir(exist_ok=True)
    survivors = []
    for name, old, new, test, assertion in FAULTS:
        original = FILE.read_bytes()
        digest = hashlib.sha256(original).hexdigest()
        source = original.decode()
        assert source.count(old) == 1, (name, source.count(old))
        command = ["node", "--test", "--test-reporter=tap", "--test-name-pattern=^" + test + "$", TEST]
        branch()
        FILE.write_text(source.replace(old, new, 1))
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        finally:
            branch()
            FILE.write_bytes(original)
        assert hashlib.sha256(FILE.read_bytes()).hexdigest() == digest
        clean = subprocess.run(command, capture_output=True, text=True, timeout=60)
        assert clean.returncode == 0, (name, clean.stdout, clean.stderr)
        (output / f"{name}.log").write_text(result.stdout + result.stderr)
        killed = result.returncode == 1 and assertion in result.stdout and "AssertionError" in result.stdout
        print(f"{name}: {'KILLED at named assertion' if killed else 'SURVIVED'}; bytes restored; clean control passed", flush=True)
        if not killed:
            survivors.append(name)
            print(result.stdout + result.stderr)
    print("SURVIVORS", len(survivors), survivors, flush=True)
    return bool(survivors)


if __name__ == "__main__":
    sys.exit(main())
