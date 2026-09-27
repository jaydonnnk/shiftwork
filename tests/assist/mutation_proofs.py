"""Failing-capable proofs for S14's independent assist policy branches.

Run explicitly with the repository Python. The shared runner restores each
modified source file byte-identically after its single named test.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("shiftwork_mutation_runner", ROOT / "tests" / "mutation_proofs.py")
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

TEST = "tests/assist/test_gateway.py"
CASES = [
    {
        "name": "assist_shared_budget_off_by_one",
        "file": "shiftwork/orchestrator.py",
        "old": "        if len(events) >= limit:",
        "new": "        if len(events) > limit:",
        "tests": f"{TEST}::test_mixed_role_budget_patch_cap_and_idempotency",
        "expect": "test_mixed_role_budget_patch_cap_and_idempotency",
    },
    {
        "name": "assist_second_patch_allowed",
        "file": "shiftwork/orchestrator.py",
        "old": "        if role is AssistRole.PATCH_PROPOSAL and any(",
        "new": "        if False and any(",
        "tests": f"{TEST}::test_mixed_role_budget_patch_cap_and_idempotency",
        "expect": "test_mixed_role_budget_patch_cap_and_idempotency",
    },
    {
        "name": "northline_diagnosis_allowed",
        "file": "shiftwork/orchestrator.py",
        "old": "        if northline and role is not AssistRole.HINT:",
        "new": "        if False:",
        "tests": f"{TEST}::test_northline_policy_allows_one_hint_only",
        "expect": "test_northline_policy_allows_one_hint_only",
    },
    {
        "name": "private_assist_reply_accepted",
        "file": "shiftwork/orchestrator.py",
        "old": '            assert_public_safe({"reply": reply.text, "reported_model_id": reply.reported_model_id},\n                               _private_public_needles())',
        "new": "            pass",
        "tests": f"{TEST}::test_failed_call_consumes_budget_without_raw_error_or_private_output",
        "expect": "test_failed_call_consumes_budget_without_raw_error_or_private_output",
    },
    # S14 review repairs (2026-09-27): a restart must resolve a stranded PENDING
    # assist, and the injected test/demo client must carry the call deadline.
    {
        "name": "stranded_assist_left_pending",
        "file": "shiftwork/orchestrator.py",
        "old": "    for event in repo.list_pending_assist_events(conn):",
        "new": "    for event in []:  # MUTATION: was repo.list_pending_assist_events(conn)",
        "tests": "tests/orchestrator/test_investigation_assist.py::test_a_stranded_assist_is_failed_at_the_next_startup",
        "expect": "test_a_stranded_assist_is_failed_at_the_next_startup",
    },
    {
        "name": "injected_client_loses_the_deadline",
        "file": "shiftwork/assist/gateway.py",
        "old": "                    json=body, timeout=DEADLINE_S,",
        "new": "                    json=body,",
        "tests": f"{TEST}::test_injected_client_cannot_bypass_the_call_deadline",
        "expect": "test_injected_client_cannot_bypass_the_call_deadline",
    },
]


def main() -> int:
    outcomes = [runner.run_mutation(case) for case in CASES]
    for outcome in outcomes:
        print(outcome)
    return 0 if all(outcome["status"] == "FAIL_CAUGHT" and outcome["sha256_restored"]
                    for outcome in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
