"""S45 assertion-bound faults. No provider calls; restore bytes after every fault."""
import ast
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

CF = 'shiftwork/comparison_flow.py'
POL = 'shiftwork/domain/comparison.py'
PUB = 'shiftwork/public_evidence.py'
BUD = 'shiftwork/live_budget.py'
T = 'tests/orchestrator/test_comparison_repetitions.py'
D = 'tests/domain/test_repeated_comparison_policy.py'
P = 'tests/orchestrator/test_public_reasoning.py'
S = 'tests/orchestrator/test_comparison_phase_status.py'
B = 'tests/executor/test_comparison_repetition_budget.py'
L = 'tests/orchestrator/test_comparison_later_repetitions.py'
CASES = []
def fault(name, file, scope, old, new, test, assertion):
    CASES.append((name, file, scope, old, new, test, assertion))

fault('api_ceiling', 'shiftwork/api/schemas.py', 'ExperimentRequest._check_kind_shape', 'self.public_repetitions > 3', 'self.public_repetitions > 10', f'{T}::test_comparison_repetition_bounds_reserve_nothing[4]', 'assert response.status_code == 422')
for scope, test in [('create_qualifying_comparison',f'{T}::test_direct_comparison_bound_refuses_before_reservation'), ('create_later_condition_comparison',f'{L}::test_later_comparison_repetitions_freeze_and_never_rewrite_history')]:
    fault('bound_'+scope, CF, scope, 'if type(public_repetitions) is not int or not 1 <= public_repetitions <= 3:', 'if False:', test, 'DID NOT RAISE')
    fault('replay_'+scope, CF, scope, '                and comparison.public_repetition_count(repo.get_execution_context(conn, replay.context_id)) == public_repetitions\n', '', f'{T}::test_repetition_count_changed_after_results_is_refused' if scope=='create_qualifying_comparison' else test, 'cannot change')
    fault('reserve_'+scope, CF, scope, 'for repetition in range(public_repetitions):', 'for repetition in range(1):', f'{T}::test_all_repetitions_are_reserved_before_any_result' if scope=='create_qualifying_comparison' else test, 'all declared public runs' if scope=='create_qualifying_comparison' else 'later["state"]')
fault('freeze_count', CF, '_comparison_context_fields', 'fields["resource_limits_json"]["public_repetitions"] = public_repetitions', 'fields["resource_limits_json"]["public_repetitions"] = 1', f'{T}::test_all_repetitions_are_reserved_before_any_result', 'declaration must be frozen')
fault('execute_each', CF, 'execute_comparison_slot', 'for repetition in repetition_runs[1:]:', 'for repetition in []:', f'{T}::test_three_public_repetitions_keep_exact_runs_and_one_protected_phase', 'three public workspaces')
fault('persist_before_next', CF, 'execute_comparison_slot', '        public_complete = _retain_public_repetition(conn, run, context, workload,\n            public_result, mission, snapshot_bytes, finalize=False)\n', '        public_complete = True\n', f'{T}::test_repetition_driver_error_terminalizes_its_pending_runs', "must survive the next driver's exception")
fault('persist_before_assessment', CF, '_retain_public_repetition', '    conn.commit()  # Raw captures survive even an assessment or later-phase error.\n', '', f'{T}::test_public_raw_capture_survives_an_assessment_error', 'raw public captures must commit')
fault('terminal_pending', CF, '_terminalize_comparison_slot', 'if run.state not in (RunState.FINALIZED, RunState.FAILED):', 'if False:', f'{T}::test_repetition_driver_error_terminalizes_its_pending_runs', 'no pending or RUNNING run')
fault('public_separate_from_protection', CF, '_public_repetition_state', 'if status is not None and status.public_payload_json.get("source") == "controller_verified":', 'if False:', f'{T}::test_protected_transport_failure_does_not_lower_a_completed_public_rate', 'protected transport failure cannot lower')
fault('status_identity', CF, '_public_repetition_state', 'if row.id == f"{run.id}-public-status"', 'if True', f'{S}::test_public_phase_status_rejects_untrusted_or_nonboolean_success[identity]', 'only an owned controller record')
fault('status_source', CF, '_public_repetition_state', ' and status.public_payload_json.get("source") == "controller_verified"', '', f'{S}::test_public_phase_status_rejects_untrusted_or_nonboolean_success[source]', 'only an owned controller record')
fault('status_boolean', CF, '_public_repetition_state', 'status.public_payload_json.get("public_repetition_complete") is True', 'bool(status.public_payload_json.get("public_repetition_complete"))', f'{S}::test_public_phase_status_rejects_untrusted_or_nonboolean_success[integer]', 'only an owned controller record')
fault('dispatcher_fallback', CF, '_comparison_adapter', '    raise LifecycleError("conflict", "reserved comparison slot has no safe executor")', '    return orchestrator.LocalProcessAdapter()', f'{S}::test_comparison_dispatcher_refuses_recorded_without_local_fallback', 'DID NOT RAISE')
for field, old in [('artifact_version_id','or item.artifact_version_id != slot.artifact_version_id'),('context_id','or item.context_id != context.id'),('experiment_id','or item.experiment_id != slot.experiment_id'),('adapter','or item.adapter != run.adapter'),('evidence_mode','or item.evidence_mode != run.evidence_mode'),('purpose','or item.purpose != run.purpose')]:
    fault('queued_'+field, CF, 'execute_comparison_slot', old, '', f'{T}::test_changed_queued_repetition_binding_sends_no_executor_call[{field}]', 'must be refused before execution')
fault('queued_state', CF, 'execute_comparison_slot', 'item.state is not RunState.QUEUED or ', '', f'{T}::test_changed_queued_repetition_binding_sends_no_executor_call[state]', 'must be refused before execution')
fault('queued_count', CF, 'execute_comparison_slot', '        or len(repetition_runs) != comparison.public_repetition_count(context)\n', '', f'{T}::test_changed_queued_repetition_binding_sends_no_executor_call[count]', 'must be refused before execution')
fault('queued_primary', CF, 'execute_comparison_slot', '        or not repetition_runs or repetition_runs[0].id != slot.run_id\n', '', f'{T}::test_changed_queued_repetition_binding_sends_no_executor_call[primary-order]', 'must be refused before execution')
for field, old in [('artifact_version_id',' or repeated.artifact_version_id != slot.artifact_version_id'),('context_id','repeated.context_id != context.id or '),('adapter',' or repeated.adapter != run.adapter'),('evidence_mode','repeated.evidence_mode != run.evidence_mode or '),('experiment_id','repeated.experiment_id != experiment.id or '),('purpose',' or repeated.purpose != run.purpose')]:
    fault('retained_'+field, CF, '_comparison_outcome', old, '', f'{T}::test_retained_repetition_binding_drift_blocks_eligibility[{field}]', 'every retained repetition must keep')
fault('retained_assessment_context', CF, '_comparison_outcome', 'if repeated_assessment.context_hash != context.content_hash:', 'if False:', f'{T}::test_child_assessment_keeps_the_frozen_context_hash', 'each repetition assessment must retain')
fault('retained_reassessment', CF, '_comparison_outcome', 'if mission is not None and public_snapshot is not None and not _public_assessment_matches(', 'if False and mission is not None and public_snapshot is not None and not _public_assessment_matches(', f'{T}::test_changed_retained_repetition_changes_the_shown_rate', 'tampered assessments must fail')
fault('reasoning_oracle', CF, '_comparison_outcome', '    drift: set[str] = set()\n', '    drift: set[str] = set()\n    if any("reasoning-oracle-counterexample" in __import__("base64").b64decode(obs.raw_payload_ref.split(",", 1)[1]).decode() for slot in slots for run in repo.list_slot_runs(conn, slot.id) for obs in repo.list_observations(conn, run.id)):\n        drift.add("reasoning_oracle")\n', f'{T}::test_public_reasoning_changes_the_view_but_never_the_outcome', 'provider reasoning must never set')
fault('each_mandatory_repetition', POL, 'compare', 'for reading in candidate_readings for rep in (reading,) + reading.repetitions', 'for reading in candidate_readings for rep in (reading,)', f'{T}::test_one_failed_repetition_blocks_eligibility', 'one failed mandatory repetition must block')
fault('unequal_count', POL, 'compare', 'len(item.repetitions) == repetitions - 1', 'True', f'{D}::test_missing_public_repetition_stays_in_the_frozen_denominator', 'unequal public repetition counts')
fault('child_completeness', POL, 'compare', '_reading_complete(rep, False)', 'True', f'{D}::test_an_incomplete_public_repetition_cannot_look_complete[output]', 'every public repetition needs complete')
fault('metrics_each', POL, '_metrics', 'public_readings = (reading,) + reading.repetitions', 'public_readings = (reading,)', f'{D}::test_repetition_metrics_count_public_evidence_and_protection_once', 'every retained repetition contributes')
fault('metrics_protected_once', POL, '_metrics', 'protected_passed += 1', 'protected_passed += repetitions', f'{D}::test_repetition_metrics_count_public_evidence_and_protection_once', 'must never multiply protected')
fault('metrics_missing', POL, '_metrics', 'max(0, repetitions - len(public_readings)) * workload.request_count', '0', f'{D}::test_missing_public_repetition_stays_in_the_frozen_denominator', 'missing repetitions must retain')
fault('frozen_count_type', POL, 'public_repetition_count', 'type(count) is not int or ', '', f'{D}::test_invalid_frozen_repetition_count_is_not_comparable[True]', 'invalid frozen repetition counts')
fault('frozen_count_lower', POL, 'public_repetition_count', 'not 1 <= count <= 3', 'count > 3', f'{D}::test_invalid_frozen_repetition_count_is_not_comparable[0]', 'invalid frozen repetition counts')
fault('frozen_count_upper', POL, 'public_repetition_count', 'not 1 <= count <= 3', 'not 1 <= count <= 10', f'{D}::test_invalid_frozen_repetition_count_is_not_comparable[4]', 'invalid frozen repetition counts')
for name, old, new, case in [('rate_row_count','len(row["task_assessments"]) == len(expected)','True','duplicate-task'),('rate_task_identity','actual == expected','True','task-identity'),('rate_body',' and o["body_base64"]','','empty-capture'),('rate_public_state','row["state"] == "COMPLETE"','True','failed-run')]:
    fault(name,CF,'_comparison_repetition_summary',old,new,f'{T}::test_retained_rate_needs_complete_unambiguous_public_rows[{case}]','incomplete or ambiguous retained rows')
fault('rate_mandatory',CF,'_comparison_repetition_summary','all(a["mandatory_pass"] for a in row["task_assessments"])','True',f'{T}::test_one_failed_repetition_blocks_eligibility','shown rate must count')
fault('rate_retained_only',CF,'_comparison_repetition_summary',' and bool(row["outputs"] or row["observations"])','',f'{T}::test_repetition_driver_error_terminalizes_its_pending_runs','unexecuted failed reservations cannot count')
fault('extra_run_slot_binding','shiftwork/store/repo.py','get_trial_slot_for_run','SELECT t.* FROM trial_slots t JOIN runs r ON r.trial_slot_id = t.id WHERE r.id = ?','SELECT * FROM trial_slots WHERE run_id = ?',f'{T}::test_additional_run_output_route_keeps_its_public_ordinal_boundary','additional run must resolve its slot')
fault('direct_meter',CF,'execute_comparison_slot','and comparison.public_repetition_count(context) > 1 and live_budget is None','and False',f'{T}::test_repeated_live_slot_requires_a_meter_before_execution','DID NOT RAISE')
fault('stop_failed_phase',CF,'execute_comparison_slot','if not public_complete and live_budget is not None:','if False:',f'{T}::test_live_driver_failure_stops_remaining_phases[1]','must stop before any further send')
fault('stop_failed_slot',CF,'execute_comparison','if live_budget is not None and repo.get_trial_slot(conn, slot.id).state == "FAILED":','if False:',f'{T}::test_live_driver_failure_stops_remaining_phases[1]','DID NOT RAISE')
for name, old, new, case in [('budget_repetition_type','type(public_repetitions) is not int','False','repetitions-True'),('budget_repetition_lower','not 1 <= public_repetitions <= 3','public_repetitions > 3','repetitions-0'),('budget_repetition_upper','not 1 <= public_repetitions <= 3','not 1 <= public_repetitions <= 10','repetitions-4'),('budget_slot_counts','len(requests_per_slot) != slots','False','slot-count-5'),('budget_request_counts','any(type(count) is not int or not 1 <= count <= 4 for count in requests_per_slot)','False','request-count-5'),('budget_operations','self.max_operations < slots * (public_repetitions + 1)','False','max-operations-23'),('budget_calls','self.max_calls < requests','False','max-calls-41'),('budget_fresh_operations','self.operations or self.calls','self.calls','used-operations-1'),('budget_fresh_calls','self.operations or self.calls','self.operations','used-calls-1')]:
    fault(name,BUD,'LiveComparisonBudget.preflight',old,new,f'{B}::test_meter_shape_guards_are_independent[{case}]','DID NOT RAISE')
fault('budget_spend_preflight',BUD,'LiveComparisonBudget.preflight','''        if (self.input_usd_per_million * self.reserved_input_tokens_per_call
                + self.output_usd_per_million * self.reserved_output_tokens_per_call
                ) * requests / 1_000_000 > self.max_projected_usd:''','        if False:',f'{B}::test_comparison_meter_refuses_reserved_spend_before_any_call','DID NOT RAISE')
fault('budget_spend_next',BUD,'LiveComparisonBudget.before_inference','if next_projection > self.max_projected_usd:','if False:',f'{B}::test_spend_refusal_does_not_reserve_an_unsent_call','DID NOT RAISE')
fault('budget_operation_ceiling',BUD,'LiveComparisonBudget.before_operation','if self.operations >= self.max_operations:','if False:',f'{B}::test_comparison_meter_reserves_42_calls_and_24_operations','DID NOT RAISE')
fault('budget_call_ceiling',BUD,'LiveComparisonBudget.before_inference',' or self.calls >= self.max_calls','',f'{B}::test_comparison_meter_reserves_42_calls_and_24_operations','DID NOT RAISE')
fault('reasoning_public_only',PUB,'public_observation','if not 1 <= observation.request_ordinal <= public_count:','if False:',f'{P}::test_protected_reasoning_is_never_projected','protected ordinals must be rejected')
fault('reasoning_scan',PUB,'public_observation','assert_public_safe({"reasoning_text": text}, needles)','pass',f'{P}::test_reasoning_scan_detects_serialized_needles_and_withholds_text[raw]','unsafe provider reasoning must be withheld')
fault('reasoning_character_count',PUB,'public_observation','payload["reasoning_characters"] = len(text)','payload["reasoning_characters"] = len(text) + 1',f'{P}::test_public_reasoning_is_exact_provider_text_with_character_count','character count is not a reasoning-token count')
fault('reasoning_text_limit',PUB,'public_observation','if len(text) > 65536:','if False:',f'{P}::test_reasoning_character_cap_refuses_oversized_provider_text','inside the public text bound')
fault('reasoning_prefix',PUB,'public_observation','not observation.raw_payload_ref.startswith(prefix) or ','',f'{P}::test_unusable_raw_reply_stays_unknown[prefix]','unusable raw evidence cannot become')
fault('reasoning_raw_limit',PUB,'public_observation',' or len(observation.raw_payload_ref) > 400000','',f'{P}::test_unusable_raw_reply_stays_unknown[raw-size]','unusable raw evidence cannot become')
fault('reasoning_text_type',PUB,'public_observation','if isinstance(text, str):','if True:',f'{P}::test_unusable_raw_reply_stays_unknown[non-string]','unusable raw evidence cannot become')
fault('example_no_rescue','demos/s45_repairs.py','candidate_files','    compile(source, f"s45-example-{label}", "exec")','    source += "\\nanswer = lambda request, snapshot: {\\\"task_results\\\": []}\\n"\n    compile(source, f"s45-example-{label}", "exec")','tests/executor/test_s45_example_repairs.py::test_example_repairs_change_only_prompt_or_reasoning_setting_and_keep_no_rescue_code','may not add hidden rescue code')
fault('example_no_tuning','demos/s45_repairs.py',None,'Return only the JSON task plan. Do not write reasoning or explanation.','Return only a compact JSON task plan. Do not write reasoning or explanation.','tests/executor/test_s45_example_repairs.py::test_example_a_matches_the_separately_frozen_probe_prompt','must not be tuned after its retained stop')
fault('public_observation_ordinal',CF,'_retain_public_repetition',
    'if type(request_ordinal) is not int or not 1 <= request_ordinal <= workload.request_count:',
    'if False:',f'{T}::test_additional_public_run_rejects_out_of_workload_ordinals[observation]','DID NOT RAISE')
fault('public_capture_ordinal',CF,'_retain_public_repetition',
    'if not 1 <= output.request_ordinal <= workload.request_count:',
    'if False:',f'{T}::test_additional_public_run_rejects_out_of_workload_ordinals[capture]','DID NOT RAISE')
fault('proof_cache_isolation','tests/s45_mutation_proofs.py','run',
    ", 'PYTHONPYCACHEPREFIX': cache",'',
    'tests/executor/test_s45_proof_runtime.py::test_mutation_checks_import_restored_source_despite_a_poisoned_cache',
    'mutation checks must read restored source, not cached faults')
fault('primary_slot_boundary','shiftwork/store/repo.py','get_trial_slot_for_run',
    '    row = conn.execute("SELECT * FROM trial_slots WHERE run_id = ?", (run_id,)).fetchone()',
    '    row = None',f'{T}::test_primary_output_boundary_survives_a_missing_run_back_reference',
    'primary slot pointer must preserve its public output boundary')

R = 'tests/executor/test_reasoning_control.py'
RC = 'tests/orchestrator/test_reasoning_context.py'
GI = 'shiftwork/gateway/service_inference.py'
OR = 'shiftwork/orchestrator.py'
TF = 'shiftwork/executor/tokenfactory.py'
fault('reasoning_strict_false','shiftwork/gateway/protocol.py','InferenceRequest.strict_reasoning_off',
    'if value is not False:', 'if False:', f'{R}::test_only_a_strict_false_value_is_admitted[zero]', 'non-false values must be refused')
fault('reasoning_permission',GI,'ServiceInferenceGateway.infer',
    'self.policy.allow_reasoning_off is not True', 'False', f'{R}::test_reasoning_off_needs_frozen_permission_and_the_exact_model[permission]', 'reasoning-off needs the exact frozen permission and model')
fault('reasoning_permission_boolean',GI,'ServiceInferenceGateway.infer',
    'self.policy.allow_reasoning_off is not True', 'not bool(self.policy.allow_reasoning_off)', f'{R}::test_reasoning_off_needs_frozen_permission_and_the_exact_model[nonboolean-permission]', 'reasoning-off needs the exact frozen permission and model')
fault('reasoning_model',GI,'ServiceInferenceGateway.infer',
    'self.policy.model != REASONING_OFF_MODEL', 'False', f'{R}::test_reasoning_off_needs_frozen_permission_and_the_exact_model[model]', 'reasoning-off needs the exact frozen permission and model')
fault('reasoning_optional',GI,'ServiceInferenceGateway.infer',
    'if request.enable_thinking is False and (', 'if (', f'{R}::test_omission_keeps_the_original_provider_body', 'omission must preserve the original wire body')
fault('reasoning_wire',GI,'ServiceInferenceGateway.infer',
    'provider_request["chat_template_kwargs"] = {"enable_thinking": False}', 'pass', f'{R}::test_strict_false_adds_only_the_approved_provider_flag_and_observation', 'only the admitted flag may change the provider body')
fault('reasoning_observation',GI,'ServiceInferenceGateway.infer',
    '**({"enable_thinking": False} if request.enable_thinking is False else {})', '**{}', f'{R}::test_strict_false_adds_only_the_approved_provider_flag_and_observation', 'the controller must retain the requested false setting')
fault('reasoning_wire_omission',GI,'ServiceInferenceGateway.infer',
    'if request.enable_thinking is False:', 'if True:', f'{R}::test_omission_keeps_the_original_provider_body', 'omission must preserve the original wire body')
fault('reasoning_adapter_store',TF,'TokenFactoryAdapter.__init__',
    'self.allow_reasoning_off = allow_reasoning_off', 'self.allow_reasoning_off = False', f'{RC}::test_new_comparison_context_freezes_permission_before_execution[nano]', 'both candidates and protected phases need their frozen permission')
fault('reasoning_gateway_first',TF,'TokenFactoryAdapter.execute',
    'request_ordinal=1,\n                task_vocabulary=self.task_vocabulary,\n                allow_reasoning_off=self.allow_reasoning_off,',
    'request_ordinal=1,\n                task_vocabulary=self.task_vocabulary,\n                allow_reasoning_off=False,', f'{R}::test_permission_reaches_every_gateway_in_a_multi_request_operation', 'the first gateway must receive the frozen permission')
fault('reasoning_gateway_next',TF,'TokenFactoryAdapter.execute',
    'request_ordinal=ordinal + 1,\n                                task_vocabulary=self.task_vocabulary,\n                                allow_reasoning_off=self.allow_reasoning_off,',
    'request_ordinal=ordinal + 1,\n                                task_vocabulary=self.task_vocabulary,\n                                allow_reasoning_off=False,', f'{R}::test_permission_reaches_every_gateway_in_a_multi_request_operation', 'the next gateway must receive the frozen permission')
fault('reasoning_service_wire',OR,'service_adapter',
    'allow_reasoning_off=context.resource_limits_json.get("allow_reasoning_off") is True', 'allow_reasoning_off=False', 'tests/orchestrator/test_comparison_v2_wiring.py::test_v2_comparison_preserves_pinned_workloads_and_delivers_policy_to_both_candidates', 'every public repetition and protected phase needs the frozen reasoning permission')
fault('reasoning_comparison_freeze',CF,'_comparison_context_fields',
    'fields["resource_limits_json"]["allow_reasoning_off"] = True', 'fields["resource_limits_json"]["allow_reasoning_off"] = False', f'{RC}::test_new_comparison_context_freezes_permission_before_execution[nano]', 'comparison permission must be frozen before results')
fault('reasoning_comparison_local',CF,'_comparison_context_fields',
    'if isolated and config.SERVICE_MODEL == REASONING_OFF_MODEL:', 'if config.SERVICE_MODEL == REASONING_OFF_MODEL:', f'{RC}::test_new_comparison_context_freezes_permission_before_execution[local]', 'comparison permission must be frozen before results')
fault('reasoning_comparison_model',CF,'_comparison_context_fields',
    'if isolated and config.SERVICE_MODEL == REASONING_OFF_MODEL:', 'if isolated:', f'{RC}::test_new_comparison_context_freezes_permission_before_execution[other-model]', 'comparison permission must be frozen before results')
fault('reasoning_diagnostic_freeze',OR,'freeze_diagnostic_context',
    'fields["resource_limits_json"]["allow_reasoning_off"] = True', 'fields["resource_limits_json"]["allow_reasoning_off"] = False', f'{RC}::test_new_diagnostic_context_freezes_only_the_admitted_permission[nano]', 'diagnostic permission must be frozen only for isolated Nano')
fault('reasoning_diagnostic_default',OR,'freeze_diagnostic_context',
    'config.SERVICE_MODEL == REASONING_OFF_MODEL if allow_reasoning_off is None else allow_reasoning_off', 'False if allow_reasoning_off is None else allow_reasoning_off', f'{RC}::test_new_diagnostic_context_freezes_only_the_admitted_permission[nano]', 'diagnostic permission must be frozen only for isolated Nano')
fault('reasoning_inherited_denial',OR,'freeze_diagnostic_context',
    'config.SERVICE_MODEL == REASONING_OFF_MODEL if allow_reasoning_off is None else allow_reasoning_off', 'config.SERVICE_MODEL == REASONING_OFF_MODEL', f'{RC}::test_selected_operation_inherits_permission_and_exact_version[historical-denial]', 'operation must preserve the tested permission')
fault('reasoning_inherited_model',OR,'freeze_diagnostic_context',
    'if config.SERVICE_MODEL != REASONING_OFF_MODEL:', 'if False:', f'{RC}::test_inherited_permission_cannot_move_to_another_model', 'DID NOT RAISE')
fault('reasoning_starter',OR,'_selected_reasoning_permission',
    'return False', 'return True', f'{RC}::test_starter_has_no_invented_comparison_permission', 'a starter cannot invent a selected comparison permission')
fault('reasoning_selected_missing',OR,'_selected_reasoning_permission',
    'raise LifecycleError("conflict", "selected reasoning permission is unavailable")', 'return False', f'{RC}::test_selected_permission_requires_its_retained_context', 'DID NOT RAISE')
fault('reasoning_selected_hash',OR,'_selected_reasoning_permission',
    'if _frozen_comparison_context_hash(context, bindings) != context.content_hash:', 'if False:', f'{RC}::test_selected_operation_refuses_changed_permission_before_reservation', 'DID NOT RAISE')
fault('reasoning_selected_experiment',OR,'_selected_reasoning_permission',
    'if _frozen_comparison_experiment_hash(experiment, context, slots) != experiment.content_hash:', 'if False:', f'{RC}::test_selected_operation_refuses_a_rehashed_permission_upgrade', 'DID NOT RAISE')
fault('reasoning_selected_boolean',OR,'_selected_reasoning_permission',
    'context.resource_limits_json.get("allow_reasoning_off") is True', 'context.resource_limits_json.get("allow_reasoning_off") == True', f'{RC}::test_selected_operation_inherits_permission_and_exact_version[nonboolean]', 'operation must preserve the tested permission')
fault('reasoning_operation_forward',OR,'_reserve_selected_operation',
    'allow_reasoning_off=_selected_reasoning_permission(conn, selection)', 'allow_reasoning_off=None', f'{RC}::test_selected_operation_inherits_permission_and_exact_version[historical-denial]', 'operation must preserve the tested permission')
fault('example_control_present','demos/s45_repairs.py','candidate_files', 'if label == "B":', 'if False:',
    'tests/executor/test_s45_example_repairs.py::test_example_b_changes_only_the_reasoning_setting_from_example_a', 'B must use the same frozen wording and only request reasoning off')
fault('example_control_false','demos/s45_repairs.py','candidate_files', '"enable_thinking": False', '"enable_thinking": True',
    'tests/executor/test_s45_example_repairs.py::test_example_b_changes_only_the_reasoning_setting_from_example_a', 'B must use the same frozen wording and only request reasoning off')
fault('example_a_default','demos/s45_repairs.py','candidate_files', 'if label == "B":', 'if label in ("A", "B"):',
    'tests/executor/test_s45_example_repairs.py::test_example_b_changes_only_the_reasoning_setting_from_example_a', 'A must preserve the probed default provider settings')
fault('summary_planned_schedule',CF,'_comparison_repetition_summary', 'public requests planned for', 'public requests executed for',
    f'{T}::test_comparison_schedule_copy_does_not_claim_unexecuted_repetitions_ran', 'unexecuted repetitions must be labelled as planned')


def branch():
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='shiftwork/slice-45'


def modified(source, scope, old, new):
    if scope is None:
        assert source.count(old)==1, (scope,old,source.count(old))
        return source.replace(old,new,1)
    tree=ast.parse(source)
    if '.' in scope:
        cls,name=scope.split('.')
        parent=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name==cls)
        node=next(node for node in parent.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name)
    else:
        node=next(node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==scope)
    lines=source.splitlines(keepends=True)
    start=sum(map(len,lines[:node.lineno-1]));end=sum(map(len,lines[:node.end_lineno]))
    block=source[start:end]
    assert block.count(old)==1,(scope,old,block.count(old))
    return source[:start]+block.replace(old,new,1)+source[end:]


def run(test):
    with tempfile.TemporaryDirectory(prefix='shiftwork-s45-proof-bytecode-') as cache:
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPYCACHEPREFIX': cache}
        return subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider',test],
            text=True,capture_output=True,timeout=60,env=env)


def main():
    selected=set(sys.argv[1:]); survivors=[]
    root=Path('/tmp/shiftwork-s45-mutations-20261024');root.mkdir(exist_ok=True)
    for name,file,scope,old,new,test,assertion in CASES:
        if selected and name not in selected: continue
        path=Path(file); original=path.read_bytes(); digest=hashlib.sha256(original).hexdigest()
        changed=modified(original.decode(),scope,old,new)
        branch(); path.write_bytes(changed.encode())
        try:
            result=run(test)
        finally:
            branch(); path.write_bytes(original)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest, 'restoration differs'
        failed=re.findall(r'^FAILED (\S+)',result.stdout,re.M)
        killed=(result.returncode==1 and failed==[test] and assertion in result.stdout
                and ('AssertionError' in result.stdout or 'DID NOT RAISE' in result.stdout)
                and 'ERROR at' not in result.stdout)
        (root/(name+'.log')).write_text(result.stdout+result.stderr)
        clean=run(test)
        (root/(name+'-restored.log')).write_text(clean.stdout+clean.stderr)
        assert clean.returncode==0,(name,'restored control failed',clean.stdout[-5000:])
        print(f'{name}: {"KILLED at named assertion" if killed else "SURVIVED"}; restored byte-identically; clean control passed',flush=True)
        if not killed:
            survivors.append(name);print(result.stdout[-4000:],flush=True)
    print('SURVIVORS',len(survivors),survivors,flush=True)
    return bool(survivors)


if __name__=='__main__':
    sys.exit(main())
