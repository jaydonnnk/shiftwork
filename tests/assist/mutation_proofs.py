"""Failing-capable proofs for S14's independent assist policy branches.

Run explicitly with the repository Python. The shared runner restores each
modified source file byte-identically after its single named test.
"""

import importlib.util
import shlex
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
        "old": "        if role is AssistRole.PATCH_PROPOSAL and sum(",
        "new": "        if False and sum(",
        "tests": f"{TEST}::test_mixed_role_budget_patch_cap_and_idempotency",
        "expect": "test_mixed_role_budget_patch_cap_and_idempotency",
    },
    {
        "name": "northline_diagnosis_allowed",
        "file": "shiftwork/orchestrator.py",
        "old": "    if role not in policy.allowed_roles:",
        "new": "    if False:",
        "tests": f"{TEST}::test_disallowed_diagnosis_is_refused_before_gateway",
        "expect": "test_disallowed_diagnosis_is_refused_before_gateway",
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


# S22a: every new declaration/projection guard has its own fault.
for name, target, old, new, node in (
    ("declared_gtm_call_budget_widened", "shiftwork/orchestrator.py",
     "        limit = policy.total_calls_per_shift", "        limit = 3",
     "test_assist_policy_is_declared_per_pack[gtm]"),
    ("declared_gtm_view_budget_widened", "shiftwork/orchestrator.py",
     "    assist_limit = policy.total_calls_per_shift", "    assist_limit = 3",
     "test_assist_policy_is_declared_per_pack[gtm]"),
    ("zero_patch_budget_ignored", "shiftwork/orchestrator.py",
     "        ) >= policy.max_patch_proposals:", "        ) >= 1:",
     "test_patch_limit_comes_from_declaration"),
    ("assist_level_projection_ignored", "shiftwork/orchestrator.py",
     '                   and row["assist_level"] == policy.level_label', '',
     "test_assist_projection_mismatch_refuses_route_view_and_startup[assist_level-widened]"),
    ("assist_roles_projection_ignored", "shiftwork/orchestrator.py",
     '                   and json.loads(row["allowed_assist_roles_json"]) == [role.value for role in policy.allowed_roles]', '',
     'test_assist_projection_mismatch_refuses_route_view_and_startup[allowed_assist_roles_json-["HINT"]]'),
    ("assist_total_projection_ignored", "shiftwork/orchestrator.py",
     '                   and row["total_assist_budget_per_shift"] == policy.total_calls_per_shift)', ')',
     "test_assist_projection_mismatch_refuses_route_view_and_startup[total_assist_budget_per_shift-9]"),
    ("malformed_assist_projection_admitted", "shiftwork/orchestrator.py",
     "    except (ValueError, TypeError):\n        matches = False", "    except (ValueError, TypeError):\n        matches = True",
     "test_assist_projection_mismatch_refuses_route_view_and_startup[allowed_assist_roles_json-malformed-json]"),
    ("startup_assist_verification_skipped", "shiftwork/app.py",
     "        orchestrator.verify_assist_policy_projections(conn)", "        pass",
     "test_assist_projection_mismatch_refuses_route_view_and_startup[assist_level-widened]"),
    ("unreviewed_pack_help_admitted", "shiftwork/orchestrator.py",
     "    policy = verified_assist_policy(conn, shift.engagement_slug)\n    admit_pack(shift.engagement_slug)\n    if role not in policy.allowed_roles:",
     "    policy = verified_assist_policy(conn, shift.engagement_slug)\n    if role not in policy.allowed_roles:",
     "test_unreviewed_northline_refuses_help_before_gateway"),
    ("failed_help_restores_budget", "shiftwork/orchestrator.py",
     "        if len(events) >= limit:",
     '        if sum(event.state == "COMPLETE" for event in events) >= limit:',
     "test_failed_help_consumes_the_declared_reduced_budget"),
    ("startup_seeds_hardcoded_assist_budget", "shiftwork/orchestrator.py",
     "        repo.seed_engagement_assist_policy(\n            conn, pack.slug,\n            assist_level=pack.assist.level_label,\n            allowed_assist_roles=tuple(role.value for role in pack.assist.allowed_roles),\n            total_assist_budget_per_shift=pack.assist.total_calls_per_shift,",
     "        repo.seed_engagement_assist_policy(\n            conn, pack.slug,\n            assist_level=pack.assist.level_label,\n            allowed_assist_roles=tuple(role.value for role in pack.assist.allowed_roles),\n            total_assist_budget_per_shift=3,",
     "test_startup_seeds_declared_policy_idempotently"),
    ("absent_current_assist_projection_ignored", "shiftwork/orchestrator.py",
     "    if not matches:\n        raise LifecycleError(\"conflict\", \"assist policy projection disagrees with the registered declaration\")",
     "    if not matches and row is not None:\n        raise LifecycleError(\"conflict\", \"assist policy projection disagrees with the registered declaration\")",
     "test_missing_current_projection_refuses_help_and_view_without_historical_fallback"),
    ("historical_assist_config_fallback", "shiftwork/orchestrator.py",
     "    row = repo.get_engagement_assist_policy(conn, slug)",
     "    row = repo.get_engagement_assist_policy(conn, slug) or repo.get_engagement_config(conn, slug)",
     "test_missing_current_projection_refuses_help_and_view_without_historical_fallback"),
    ("startup_missing_projection_not_checked", "shiftwork/orchestrator.py",
     '    for row in conn.execute("SELECT slug FROM engagements"):',
     '    for row in conn.execute("SELECT slug FROM engagement_assist_policy"):',
     "test_startup_verifies_every_seeded_engagement_projection"),
    ("startup_overwrites_assist_mismatch", "shiftwork/store/repo.py",
     '        "INSERT OR IGNORE INTO engagement_assist_policy (slug, assist_level, "',
     '        "INSERT OR REPLACE INTO engagement_assist_policy (slug, assist_level, "',
     "test_assist_projection_mismatch_refuses_route_view_and_startup[assist_level-widened]"),
):
    CASES.append(dict(name=name, file=target, old=old, new=new,
                      tests=shlex.quote(f"{TEST}::{node}"), node=f"{TEST}::{node}", expect=node))


def main() -> int:
    outcomes = [runner.run_mutation(case) for case in CASES]
    for outcome in outcomes:
        print(outcome)
    return 0 if all(outcome["status"] == "FAIL_CAUGHT" and outcome["sha256_restored"]
                    for outcome in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
