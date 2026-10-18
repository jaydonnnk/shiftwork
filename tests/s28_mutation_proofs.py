"""S28 assertion-only wiring faults. Run on a disposable physical source copy."""

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.mutation_proofs import run_mutation

TEST = 'tests/api/test_hosted.py'
ROWS = []

def row(name, file, old, new, test):
    ROWS.append(dict(name=name, file=file, old=old, new=new,
                     tests=shlex.quote(TEST + '::' + test), expect=test))

HOST = 'shiftwork/hosted.py'
APP = 'shiftwork/app.py'
ROUTES = 'shiftwork/api/routes.py'
row('render_flag_ignored', APP, 'if executor is None and os.environ.get("RENDER") == "true":',
    'if executor is None:', 'test_local_default_does_not_enable_provider_from_credentials')
row('render_explicit_executor_ignored', APP, 'if executor is None and os.environ.get("RENDER") == "true":',
    'if (executor is None or executor == "local_process") and os.environ.get("RENDER") == "true":',
    'test_explicit_demo_executor_is_preserved_on_render')
row('render_delegation_removed', APP, 'if executor is None and os.environ.get("RENDER") == "true":',
    'if False:', 'test_both_credentials_enable_live_and_its_assistance')
row('key_not_required', HOST, 'live = bool(token and project)', 'live = bool(project)',
    'test_missing_credential_serves_labelled_recorded_fallback[NEBIUS_API_KEY]')
row('project_not_required', HOST, 'live = bool(token and project)', 'live = bool(token)',
    'test_missing_credential_serves_labelled_recorded_fallback[NEBIUS_PROJECT_ID]')
row('fallback_wrong_executor', HOST, "executor='tokenfactory' if live else 'recorded'",
    "executor='tokenfactory' if live else 'local_process'",
    'test_missing_credential_serves_labelled_recorded_fallback[both]')
row('live_help_missing', HOST, 'assist_gateway=LiveAssistGateway(token) if live else None,',
    'assist_gateway=None,', 'test_both_credentials_enable_live_and_its_assistance')
row('partial_credentials_enable_help', HOST, 'assist_gateway=LiveAssistGateway(token) if live else None,',
    'assist_gateway=LiveAssistGateway(token),',
    'test_missing_credential_serves_labelled_recorded_fallback[NEBIUS_PROJECT_ID]')
row('fallback_operation_meter_enabled', HOST, 'live_operation_budget=operation_budget if live else None,',
    'live_operation_budget=operation_budget,',
    'test_missing_credential_serves_labelled_recorded_fallback[both]')
row('fallback_comparison_meter_enabled', HOST, 'live_comparison_budget=comparison_budget if live else None,',
    'live_comparison_budget=comparison_budget,',
    'test_missing_credential_serves_labelled_recorded_fallback[both]')
row('key_whitespace_accepted', HOST, 'token != token.strip()', 'False',
    'test_invalid_present_credentials_fail_closed[NEBIUS_API_KEY- S28_SYNTHETIC_PROVIDER_CANARY]')
row('project_whitespace_accepted', HOST, 'project != project.strip()', 'False',
    'test_invalid_present_credentials_fail_closed[NEBIUS_PROJECT_ID-aiproject-S28-SYNTHETIC ]')
row('generic_project_accepted', HOST, "not project.startswith('aiproject-')", 'False',
    'test_invalid_present_credentials_fail_closed[NEBIUS_PROJECT_ID-project-S28-SYNTHETIC]')
for permission in ('cancel', 'import', 'list', 'set_image_tag', 'spawn', 'spawn_disposable'):
    row('permission_' + permission + '_omitted', HOST,
        "PERMISSIONS = ('cancel', 'import', 'list', 'set_image_tag', 'spawn', 'spawn_disposable')",
        "PERMISSIONS = tuple(name for name in ('cancel', 'import', 'list', 'set_image_tag', 'spawn', 'spawn_disposable') if name != " + repr(permission) + ')',
        'test_each_missing_permission_stops_live_startup[' + permission + ']')
row('permission_guard_bypassed', HOST, 'if not all(permissions.values()):', 'if False:',
    'test_each_missing_permission_stops_live_startup[spawn]')
row('truthy_permission_accepted', HOST, 'response.permissions.get(name) is True',
    'bool(response.permissions.get(name))', 'test_preflight_requires_explicit_boolean_permission[1]')
row('preflight_exception_ignored', HOST,
    "raise RuntimeError('Hosted Sandbox preflight failed') from None", 'pass',
    'test_preflight_error_is_sanitized_and_stops_startup')
row('preflight_exception_leaked', HOST,
    "except Exception:\n                raise RuntimeError('Hosted Sandbox preflight failed') from None",
    "except Exception as exc:\n                raise RuntimeError(str(exc)) from None",
    'test_preflight_error_is_sanitized_and_stops_startup')
row('operation_meter_reused', HOST,
    'def operation_budget() -> LiveOperationBudget:\n    return LiveOperationBudget(config.SERVICE_MODEL, INPUT_RATE, OUTPUT_RATE)',
    'def operation_budget(meter=LiveOperationBudget(config.SERVICE_MODEL, INPUT_RATE, OUTPUT_RATE)) -> LiveOperationBudget:\n    return meter',
    'test_hosted_meters_are_fresh_and_preserve_consumed_allowances')
row('comparison_meter_reused', HOST,
    'def comparison_budget() -> LiveComparisonBudget:\n    return LiveComparisonBudget(config.SERVICE_MODEL, INPUT_RATE, OUTPUT_RATE)',
    'def comparison_budget(meter=LiveComparisonBudget(config.SERVICE_MODEL, INPUT_RATE, OUTPUT_RATE)) -> LiveComparisonBudget:\n    return meter',
    'test_hosted_meters_are_fresh_and_preserve_consumed_allowances')
row('operation_factory_wrong_type', HOST,
    'return LiveOperationBudget(config.SERVICE_MODEL, INPUT_RATE, OUTPUT_RATE)',
    'return LiveComparisonBudget(config.SERVICE_MODEL, INPUT_RATE, OUTPUT_RATE)',
    'test_hosted_meters_are_fresh_and_preserve_consumed_allowances')
row('operation_factory_ceiling_raised', HOST,
    'return LiveOperationBudget(config.SERVICE_MODEL, INPUT_RATE, OUTPUT_RATE)',
    'return LiveOperationBudget(config.SERVICE_MODEL, INPUT_RATE, OUTPUT_RATE, max_operations=2)',
    'test_hosted_meters_are_fresh_and_preserve_consumed_allowances')
row('comparison_factory_ceiling_raised', HOST,
    'return LiveComparisonBudget(config.SERVICE_MODEL, INPUT_RATE, OUTPUT_RATE)',
    'return LiveComparisonBudget(config.SERVICE_MODEL, INPUT_RATE, OUTPUT_RATE, max_calls=19)',
    'test_hosted_meters_are_fresh_and_preserve_consumed_allowances')
row('operation_handoff_missing', ROUTES,
    'background.add_task(orchestrator.execute_run_task, request.app.state.db_path, run.id, live_budget)',
    'background.add_task(orchestrator.execute_run_task, request.app.state.db_path, run.id, None)',
    'test_operation_factory_is_resolved_before_execution')
row('budget_factory_not_resolved', ROUTES,
    'budget = configured() if callable(configured) else configured', 'budget = configured',
    'test_operation_factory_is_resolved_before_execution')
row('wrong_meter_type_accepted', ROUTES,
    'if budget is not None and not isinstance(budget, expected_type):', 'if False:',
    'test_missing_or_wrong_operation_factory_refuses_before_reservation[comparison]')
row('comparison_factory_not_resolved', ROUTES,
    'live_budget = _action_budget(request.app.state.live_comparison_budget, LiveComparisonBudget)',
    'live_budget = request.app.state.live_comparison_budget',
    'test_comparison_factory_handoff_uses_one_action_meter[QUALIFYING_COMPARISON]')
row('qualifying_meter_handoff_missing', ROUTES,
    '                                    live_budget)\n    elif body.kind == "LATER_CONDITION_COMPARISON":',
    '                                    None)\n    elif body.kind == "LATER_CONDITION_COMPARISON":',
    'test_comparison_factory_handoff_uses_one_action_meter[QUALIFYING_COMPARISON]')
row('later_meter_handoff_missing', ROUTES,
    '                                    live_budget)\n    else:\n        experiment = experiments.create_diagnostic_experiment(',
    '                                    None)\n    else:\n        experiment = experiments.create_diagnostic_experiment(',
    'test_comparison_factory_handoff_uses_one_action_meter[LATER_CONDITION_COMPARISON]')
row('operation_claim_not_conditional', 'shiftwork/store/repo.py',
    "UPDATE runs SET state = 'RUNNING' WHERE id = ? AND state = 'QUEUED'",
    "UPDATE runs SET state = 'RUNNING' WHERE id = ?",
    'test_run_claim_cannot_reclaim_a_running_action')
row('lost_operation_claim_ignored', 'shiftwork/orchestrator.py',
    'if not repo.claim_run_execution(conn, run.id):',
    'if repo.claim_run_execution(conn, run.id) and False:',
    'test_selected_operation_claim_is_atomic_for_duplicate_live_requests')
row('runtime_mode_untruthful', HOST,
    "'configured_executor': app.state.executor",
    "'configured_executor': 'recorded'", 'test_both_credentials_enable_live_and_its_assistance')
row('reset_warning_removed', HOST, 'Sleep, restart or redeploy begins a fresh practice database.',
    'History always persists.', 'test_runtime_is_safe_and_reports_reset_and_distinct_boots')
row('boot_marker_reused', HOST, "'boot_id': str(uuid.uuid4())", "'boot_id': 'same-boot'",
    'test_runtime_is_safe_and_reports_reset_and_distinct_boots')
row('runtime_key_leak', HOST, "'hosted': True, 'configured_executor': app.state.executor,",
    "'hosted': True, 'configured_executor': app.state.executor, 'private': token,",
    'test_runtime_is_safe_and_reports_reset_and_distinct_boots')
row('runtime_project_leak', HOST, "'hosted': True, 'configured_executor': app.state.executor,",
    "'hosted': True, 'configured_executor': app.state.executor, 'private': project,",
    'test_runtime_is_safe_and_reports_reset_and_distinct_boots')


row('fresh_bellwether_binding_removed', 'shiftwork/orchestrator.py',
    '            adapter = "recorded"\n        if ((selection.kind == "LEARNER_CHOICE"',
    '            adapter = TokenFactoryAdapter.name\n        if ((selection.kind == "LEARNER_CHOICE"',
    'test_fresh_hosted_bellwether_replays_its_labelled_baseline')
row('fallback_local_disclosure_missing', HOST,
    'operations can run pinned fixtures as TRUSTED_LOCAL. No live inference.',
    'No live inference.', 'test_fallback_action_discloses_trusted_local_execution')
row('fresh_action_meter_cached', ROUTES,
    'budget = configured() if callable(configured) else configured',
    "budget = getattr(configured, '_s28_cached', None) if callable(configured) else configured\n    if callable(configured) and budget is None:\n        budget = configured()\n        configured._s28_cached = budget",
    'test_distinct_operations_receive_distinct_fresh_meters')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    baseline = subprocess.run([sys.executable, '-m', 'pytest', TEST, '-q', '--tb=short'],
                              cwd=ROOT, capture_output=True, text=True, timeout=120)
    (args.out.parent / 'baseline.log').write_text(baseline.stdout + baseline.stderr)
    assert baseline.returncode == 0, 'disposable-copy baseline must pass before any mutation'
    results = []
    for fault in ROWS:
        result = run_mutation(fault)
        clean = subprocess.run([sys.executable, '-m', 'pytest', *shlex.split(fault['tests']), '-q', '--tb=short'],
                               cwd=ROOT, capture_output=True, text=True, timeout=90)
        result['restored_rerun_passed'] = clean.returncode == 0
        results.append(result)
        print(json.dumps(result), flush=True)
    args.out.write_text(json.dumps(results, indent=2) + '\n')
    return 0 if all(r['status'] == 'FAIL_CAUGHT' and r.get('sha256_restored') and r['restored_rerun_passed'] for r in results) else 1

if __name__ == '__main__':
    raise SystemExit(main())
