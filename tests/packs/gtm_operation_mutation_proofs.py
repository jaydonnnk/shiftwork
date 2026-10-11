"""S24 named source faults, using the existing exact-restoration receipt runner.

Run only after all other tests and app processes in this checkout have stopped.
Each control must fail its named assertion with no test setup errors.
"""
import re

from tests.packs import gtm_mutation_proofs as proof

TEST = "tests/orchestrator/test_gtm_pipeline.py"
GUARDS = "tests/orchestrator/test_gtm_operation_guards.py"
RED = "shiftwork/ledger/reducer.py"
OR = "shiftwork/orchestrator.py"
TC = "shiftwork/domain/task_contract.py"
CA = "shiftwork/domain/customer_answer.py"
EX = "shiftwork/experiments.py"
CASES = []


def fault(name, file, old, new, node, test=TEST):
    scope = None
    if file == RED:
        scope = "reduce_operation" if name in {"operation_purpose", "selection_binding", "assessment_purpose", "assessment_run"} else "_reduce_pipeline_operation"
    elif file == TC:
        scope = "apply_pipeline_history"
    elif file == "shiftwork/comparison_flow.py":
        scope = "create_later_condition_comparison"
    elif file == "shiftwork/evaluator/evaluator.py":
        scope = "_assess_pipeline_request"
    elif file == CA:
        scope = "render_assessed_task_customer_text"
    elif file == EX:
        scope = "_diagnostic_customer_text"
    elif file == OR:
        scope = ("operation_consequence_inputs" if name.startswith("rule_") else
                 "freeze_diagnostic_context" if name.startswith("freeze_") else
                 "append_selection" if name == "stale_selection" else
                 "_reserve_selected_operation" if name == "operation_accounting" else
                 "replay_assessment" if name == "unreadable_replay_binding" or name.startswith("replay_") else
                 "output_evidence_for")
    CASES.append(dict(name=name, file=file, old=old, new=new, scope=scope, node=f"{test}::{node}"))


original_anchor = proof.anchor
original_run = proof.run


EXPECTED_ASSERTIONS = {
    "missing_task_assurance": ["derived text claims no action despite a required task failure"],
    "unreadable_replay_binding": ["unreadable retained binding escaped replay as "
                                  "RetainedRecordUnreadable('retained execution context is unreadable')"],
    "replay_context_outside_conversion": ["unreadable retained binding escaped replay as "
                                          "RetainedRecordUnreadable('retained execution context is unreadable')"],
    "replay_outputs_outside_conversion": ["unreadable retained run_outputs row escaped replay as "
                                          "RetainedRecordUnreadable('retained run output is unreadable')"],
    "replay_checks_outside_conversion": ["unreadable retained check_results row escaped replay as "
                                         "RetainedRecordUnreadable('retained check result is unreadable')"],
    "replay_drafts_outside_conversion": ["unreadable retained ledger_events row escaped replay as "
                                         "RetainedRecordUnreadable('retained ledger event is unreadable')"],
    "retained_value_arm": ["inheritance over an unreadable retained binding escaped as 1 validation error for ContextCondition"],
    "retained_type_arm": ["inheritance over an unreadable retained binding escaped as "
                          "TypeError(\"a bytes-like object is required, not 'str'\")"],
    "retained_context_rows": ["retry over an unreadable reused context returned 500"],
    "retained_output_rows": ["unreadable retained run_outputs row escaped replay as 1 validation error for RunOutput"],
    "retained_check_rows": ["unreadable retained check_results row escaped replay as "
                            "ValueError(\"'NOT_A_CODE' is not a valid ReasonCode\")"],
    "retained_ledger_rows": ["unreadable retained ledger_events row escaped replay as "
                             "ValueError(\"'NOT_A_TYPE' is not a valid LedgerEventType\")"],
    "retained_assessment_rows": ["unreadable task assessment returned 500"],
    "unassessed_projection": ["unassessed capture claims an assessment rejection"],
    "unassessed_response_task": ["an unassessed response task left the no-action assurance"],
    "rejected_fallback_shown": ["diagnostic text claims no action despite a rejected required task"],
    "rejection_sentence": ["diagnostic text omits the rejected required task"],
    "diagnostic_unfiltered": ["diagnostic text presents a rejected owner"],
    "owner_event": ["assert ['SLA_CLOCK_S"],
    "clock_event": ["assert ['OWNER_ASSIG"],
    "handoff_event": ["assert ['OWNER_ASSIG"],
    "human_terminal": ["'SENT_MESSAGE' == 'HUMAN_HANDOFF'"],
    "success_provenance": ["assert [('pipeline-r"],
    "success_weight": ["assert False"],
    "incident_trace": ["assert [] == ['qualificati"],
    "incident_tasks": ["assert [] == ['owner']"],
    "incident_provenance": ["wrong-source-check"],
    "history_overlay": ["assert None == 'owner-apac-platform'"],
    "freeze_history_overlay": ["reprocessing wrote another owner, record or clock"],
    "later_history_overlay": ["the observed world changes more than dependency availability", "assert 409 == 202"],
    "later_pack_pins": ["only the two pinned reviewed candidates", "assert 409 == 202"],
    "stale_selection": ["assert 201 == 409"],
    "projection_revenue": ['unsafe pipeline surface: "revenue":'],
    "projection_sent_message": ['unsafe pipeline surface: "sent_message":'],
    **{name: ["INCIDENT_OPENED"] for name in ("operational_duplicate_owner", "operational_duplicate_write",
        "operational_sent_message", "operational_revenue", "operational_missing_owner", "operational_missing_handoff")},
}


def named_run(case, out):
    row = original_run(case, out)
    expected = EXPECTED_ASSERTIONS.get(case["name"], ["Failed: DID NOT RAISE"])
    row["expected_assertions"] = expected
    row["assertion_matches"] = all(needle in row["message"] for needle in expected)
    if not row["assertion_matches"]:
        row["status"] = "NOT_PROVED"
    return row


def scoped_anchor(raw, case):
    if not case.get("scope"):
        return original_anchor(raw, case)
    starts = list(re.finditer(rb"(?m)^def " + case["scope"].encode() + rb"\(", raw))
    if len(starts) != 1:
        raise ValueError("function scope must match exactly once: " + case["name"])
    start = starts[0].start()
    following = re.search(rb"(?m)^def ", raw[starts[0].end():])
    end = starts[0].end() + following.start() if following else len(raw)
    before = raw[start:end]
    old, new = original_anchor(before, case)
    return before, before.replace(old, new, 1)


REDUCE = "test_gtm_consequence_classes_reduce_from_operational_captures_only"
LIFE = "test_gtm_exact_selection_operation_restart_inheritance_and_later_condition"
REFUSE = "test_gtm_reducer_refuses_unbound_or_experimental_pipeline_inputs"
EVIDENCE = "test_pipeline_reduction_refuses_inconsistent_controller_evidence"

for name, old, new, node in (
    ("operation_purpose", "run.purpose is not RunPurpose.OPERATION or run.selection_id is None", "False or run.selection_id is None", REFUSE + "[experiment]"),
    ("selection_binding", "assessment.selection_id != run.selection_id", "False", REFUSE + "[wrong_selection]"),
    ("assessment_purpose", "assessment.purpose is not RunPurpose.OPERATION", "False", EVIDENCE + "[assessment_purpose]"),
    ("assessment_run", "assessment.run_id != run.id", "False", EVIDENCE + "[assessment_run]"),
    ("check_cardinality", "len(checks) != len(by_check) or set(by_check) != expected", "False or set(by_check) != expected", EVIDENCE + "[duplicate_check]"),
    ("check_inventory", "len(checks) != len(by_check) or set(by_check) != expected", "len(checks) != len(by_check) or False", EVIDENCE + "[extra_check]"),
    ("row_inventory", "len(rows) != len(expected) or len(outputs) != len(captured)", "False or len(outputs) != len(captured)", EVIDENCE + "[extra_row]"),
    ("output_cardinality", "len(rows) != len(expected) or len(outputs) != len(captured)", "len(rows) != len(expected) or False", REFUSE + "[duplicate_output]"),
    ("output_ordinals", "set(captured) != set(range(1, len(mission.request_specs) + 1))", "False", EVIDENCE + "[extra_output]"),
    ("output_run", "output.run_id != run.id or output.transport_error is not None", "False or output.transport_error is not None", REFUSE + "[foreign_run]"),
    ("output_transport", "output.run_id != run.id or output.transport_error is not None", "output.run_id != run.id or False", EVIDENCE + "[transport]"),
    ("task_request", "any(row.request_id != spec.id for row in assessed)", "False", EVIDENCE + "[wrong_request]"),
    ("check_run", "check.run_id != run.id or check.observed_ref != output.id", "False or check.observed_ref != output.id", REFUSE + "[foreign_check]"),
    ("check_output", "check.run_id != run.id or check.observed_ref != output.id", "check.run_id != run.id or False", REFUSE + "[foreign_output]"),
    ("check_verdict", 'check.verdict != ("pass" if row.mandatory_pass else "fail")', "False", EVIDENCE + "[wrong_verdict]"),
):
    fault(name, RED, old, new, node, GUARDS if node.startswith(EVIDENCE) else TEST)

fault("mission_owner", RED, 'if mission.engagement_slug != "gtm" or rules is None:',
    "if rules is None:", EVIDENCE + "[foreign_mission]", GUARDS)
fault("owner_event", RED, 'for rule in rules["success_events"]:', 'for rule in rules["success_events"][1:]:', REDUCE)
fault("clock_event", RED, 'for rule in rules["success_events"]:', 'for rule in rules["success_events"][:1]:', REDUCE)
fault("handoff_event", RED, 'if by_task[handoff_task.id].outcome is task_contract.TaskOutcome.USEFUL_COMPLETION:', 'if False:', REDUCE)
fault("human_terminal", RED, '"terminal_action": "HUMAN_HANDOFF"', '"terminal_action": "SENT_MESSAGE"', REDUCE)
fault("success_provenance", RED, 'source_task = owner_task if event == "OWNER_ASSIGNED" else write_task', 'source_task = owner_task', REDUCE)
fault("success_weight", RED, '"weight": weights[key]', '"weight": weights[key] + 1', REDUCE)
fault("incident_trace", RED, '"decision_trace": [row.model_dump(mode="json") for row in assessed]', '"decision_trace": []',
    "test_gtm_one_traced_incident_per_failing_record[missing_handoff-REQUIRED_TASK_MISSING]")
fault("incident_tasks", RED, '"failed_task_ids": [row.task_id for row in failed]', '"failed_task_ids": []',
    "test_gtm_one_traced_incident_per_failing_record[missing_owner-REQUIRED_TASK_MISSING]")
fault("incident_provenance", RED, 'source = by_check[f"task:{spec.id}:{failed[0].task_id}"]',
    'source = by_check[f"task:{spec.id}:{failed[0].task_id}"].model_copy(update={"id": "wrong-source-check"})',
    "test_gtm_one_traced_incident_per_failing_record[wrong_owner-WRONG_ACTION]")
fault("malformed_accepted_capture", RED, 'raise ValueError("accepted pipeline capture is not a valid envelope") from exc', 'return []',
    "test_accepted_pipeline_capture_must_still_parse_as_its_request_envelope", GUARDS)

for label, old, new, node in (
    ("record_ref", 'record["record_ref"] != "pipeline:" + signal', "False", "wrong_ref"),
    ("owner_empty", 'not record["owner"]', "False", "empty_owner"),
    ("record_fields", 'set(record) != {"owner", "record_ref"}', "False", "extra_field"),
    ("owner_type", 'not isinstance(record["owner"], str)', "False", "owner_not_text"),
    ("signal_prefix", 'not signal.startswith("signal:")', "False", "signal_prefix"),
):
    fault("history_" + label, TC, old, new,
        "test_inherited_records_are_validated_even_when_not_in_current_batch[" + node + "]", GUARDS)
fault("history_conflict", TC, 'facts["existing_owner"] != prior["owner"]', "False",
    "test_pipeline_inheritance_refuses_corrupt_or_conflicting_record[conflicting_observation]")
fault("history_overlay", TC, 'facts.update(existing_owner=prior["owner"], existing_record_ref=prior["record_ref"])', 'pass',
    "test_pipeline_inheritance_uses_history_without_rewriting_reviewed_state")

for name, old, new, node in (
    ("rule_pack", 'context.engagement_slug != "gtm" or rules.success_events', 'False or rules.success_events', "test_pipeline_rule_resolution_refuses_wrong_owner_or_unbound_history[foreign_pack]"),
    ("rule_handoff_weight", 'type(weights["handoff"]) is not int', "False", "test_pipeline_rule_resolution_refuses_wrong_owner_or_unbound_history[boolean_handoff]"),
    ("rule_history_hash", 'canonical.content_hash(context.starting_business_state_json) != context.starting_business_state_hash', "False", "test_pipeline_rule_resolution_refuses_wrong_owner_or_unbound_history[history_hash]"),
):
    fault(name, OR, old, new, node, GUARDS)
for name, old, new, param in (
    ("rule_success_events", 'rules.success_events != (\n                    "OWNER_ASSIGNED owner", "SLA_CLOCK_STARTED sla")', "False", "wrong_events"),
    ("rule_rollout", "rules.rollout_event is not None or rules.handover_record_required", "False or rules.handover_record_required", "rollout"),
    ("rule_handover", "rules.rollout_event is not None or rules.handover_record_required", "rules.rollout_event is not None or False", "handover"),
):
    fault(name, OR, old, new, "test_gtm_frozen_consequence_rules_refuse_drift[" + param + "]")
fault("freeze_broken_chain", OR, 'if chain.verify_chain(events) is chain.ChainStatus.BROKEN:', 'if False:',
    "test_pipeline_freeze_refuses_broken_chain_before_inheriting", GUARDS)
fault("freeze_duplicate_owner", OR, "if signal in owned:", "if False:",
    "test_pipeline_freeze_refuses_duplicate_owners_in_valid_chain", GUARDS)
fault("freeze_history_overlay", OR, "snapshot_bytes = task_contract.apply_pipeline_history(snapshot_bytes, owned)", "snapshot_bytes = snapshot_bytes", LIFE)
fault("later_history_hash", "shiftwork/comparison_flow.py",
    "if canonical.content_hash(observed_context.starting_business_state_json) != observed_context.starting_business_state_hash:", "if False:",
    "test_later_gtm_comparison_refuses_unbound_ownership_history", GUARDS)
fault("later_history_overlay", "shiftwork/comparison_flow.py",
    'reviewed_observed_world = task_contract.apply_pipeline_history(\n                reviewed_comparison_bytes, observed_context.starting_business_state_json["pipeline_records"])',
    "reviewed_observed_world = reviewed_comparison_bytes", LIFE)
fault("later_pack_pins", "shiftwork/comparison_flow.py", "_, candidate_a_key, candidate_b_key = config.offline_fixture_keys(shift.engagement_slug)",
    '_, candidate_a_key, candidate_b_key = config.offline_fixture_keys("bookshop")', LIFE)
fault("stale_selection", OR, "if request.expected_prior_selection_id != (prior.id if prior else None):", "if False:", LIFE)
fault("operation_accounting", OR, "if any(run.state is RunState.FINALIZED for run in prior_operations):", "if False:",
    "test_gtm_finalized_operation_guard_precedes_retry_and_storage", GUARDS)
fault("projection_revenue", OR, "for task in response.task_results if task.task_id in accepted_tasks for claim in task.claims]",
    "for task in response.task_results for claim in task.claims]",
    "test_gtm_customer_projection_does_not_present_rejected_output_claims[revenue]")
fault("projection_sent_message", OR, "for task in response.task_results if task.task_id in accepted_tasks for claim in task.claims]",
    "for task in response.task_results for claim in task.claims]",
    "test_gtm_customer_projection_does_not_present_rejected_output_claims[sent_message]")

for name, old, new, parameter in (
    ("operational_duplicate_owner", "elif len(result.claims) != 1:", "elif not result.claims:", "duplicate_owner-DUPLICATE_COMMITMENT"),
    ("operational_duplicate_write", "elif len(result.claims) != 1:", "elif not result.claims:", "duplicate_write-DUPLICATE_COMMITMENT"),
    ("operational_sent_message", 'set(row) != {"owner", "record_ref", "decision_trace"}', "False", "sent_message-WRONG_ACTION"),
    ("operational_revenue", 'set(row) != {"owner", "record_ref", "decision_trace"}', "False", "revenue-WRONG_ACTION"),
    ("operational_missing_owner", "if result is None:\n            codes.append(ReasonCode.REQUIRED_TASK_MISSING)", "if result is None:\n            pass", "missing_owner-REQUIRED_TASK_MISSING"),
    ("operational_missing_handoff", "if result is None:\n            codes.append(ReasonCode.REQUIRED_TASK_MISSING)", "if result is None:\n            pass", "missing_handoff-REQUIRED_TASK_MISSING"),
):
    fault(name, "shiftwork/evaluator/evaluator.py", old, new,
        "test_gtm_one_traced_incident_per_failing_record[" + parameter + "]")

REPAIRS = "tests/orchestrator/test_gtm_review_repairs.py"
# The shared assessed-text helper (S24 review F2): each guard arm, plus the
# diagnostic projection's GTM dispatch into it.
fault("missing_task_assurance", CA, "rejected = (any(not row.mandatory_pass for row in rows)", "rejected = (False",
    "test_gtm_missing_required_task_cannot_present_no_action_assurance[both]", test=REPAIRS)
fault("unassessed_projection", CA, "    if not rows:\n        return None\n", "    if False:\n        return None\n",
    "test_gtm_unassessed_capture_presents_no_derived_answer", test=REPAIRS)
fault("unassessed_response_task", CA, "or any(task.task_id not in passed for task in response.task_results))", "or False)",
    "test_gtm_response_task_without_assessment_row_is_rejected", test=REPAIRS)
DIAGNOSTIC = "test_gtm_diagnostic_text_matches_assessment["
fault("rejected_fallback_shown", CA, "    shown = accepted if rejected else passed\n", "    shown = passed\n",
    DIAGNOSTIC + "missing_both]", test=REPAIRS)
fault("rejection_sentence", CA, "    if rejected:\n        text += ", "    if False:\n        text += ",
    DIAGNOSTIC + "missing_owner]", test=REPAIRS)
fault("diagnostic_unfiltered", EX, '    if mission.engagement_slug == "gtm":\n', "    if False:\n",
    DIAGNOSTIC + "wrong_owner]", test=REPAIRS)

# Retained-row storage boundary: each guard arm and each decorated row type.
REPO = "shiftwork/store/repo.py"
CONVERT = "            except (ValueError, TypeError) as exc:\n                raise RetainedRecordUnreadable("
BINDING = "test_gtm_inheritance_refuses_unreadable_retained_binding["
ROW = "test_gtm_unreadable_retained_row_returns_verdict_and_refuses_inheritance["
fault("retained_value_arm", REPO, CONVERT, CONVERT.replace("(ValueError, TypeError)", "TypeError"),
    BINDING + "condition_binding_absent]", test=REPAIRS)
fault("retained_type_arm", REPO, CONVERT, CONVERT.replace("(ValueError, TypeError)", "ValueError"),
    BINDING + "mission_bytes_text]", test=REPAIRS)
for name, label, node in (
    ("retained_context_rows", "execution context", "test_gtm_retry_refuses_reused_unreadable_context[spec_binding_absent]"),
    ("retained_output_rows", "run output", ROW + "output_failure]"),
    ("retained_check_rows", "check result", ROW + "check_reason]"),
    ("retained_ledger_rows", "ledger event", ROW + "ledger_event_type]"),
    ("retained_assessment_rows", "task assessment", "test_gtm_unreadable_task_assessment_is_a_typed_conflict"),
):
    fault(name, REPO, f'@_retained("{label}")\n', "", node, test=REPAIRS)

# Replay's evidence-verdict conversion: its catch and each retained read inside it.
VERDICT = "test_gtm_unreadable_retained_binding_returns_evidence_verdict["
EXCEPT = "    except RetainedRecordUnreadable:\n"
RETURN = "        return _unknown_inputs_report(run.id)\n"
CHECKS = "        stored_checks = repo.list_check_results(conn, run.id)\n"
DRAFTS = ("        stored_drafts = (_stored_operation_drafts(conn, run, context.engagement_slug)\n"
          "                         if context is not None else [])\n")
fault("unreadable_replay_binding", OR, EXCEPT, "    except ():\n", VERDICT + "spec_binding_absent]", test=REPAIRS)
fault("replay_context_outside_conversion", OR,
    "    try:\n        context = repo.get_execution_context(conn, run.context_id)\n",
    "    context = repo.get_execution_context(conn, run.context_id)\n    try:\n",
    VERDICT + "condition_binding_absent]", test=REPAIRS)
# Each moved read runs after the conversion; the original return becomes dead code.
fault("replay_outputs_outside_conversion", OR,
    "        outputs = repo.list_outputs(conn, run.id)\n" + CHECKS + DRAFTS + EXCEPT,
    CHECKS + DRAFTS + EXCEPT + RETURN + "    outputs = repo.list_outputs(conn, run.id)\n    if False:\n",
    ROW + "output_failure]", test=REPAIRS)
fault("replay_checks_outside_conversion", OR, CHECKS + DRAFTS + EXCEPT,
    DRAFTS + EXCEPT + RETURN + CHECKS.replace("        ", "    ", 1) + "    if False:\n",
    ROW + "check_verdict]", test=REPAIRS)
fault("replay_drafts_outside_conversion", OR, DRAFTS + EXCEPT,
    "        pass\n" + EXCEPT + RETURN
    + "    stored_drafts = (_stored_operation_drafts(conn, run, context.engagement_slug)\n"
    + "                     if context is not None else [])\n    if False:\n",
    ROW + "ledger_event_type]", test=REPAIRS)


if __name__ == "__main__":
    proof.anchor = scoped_anchor
    proof.run = named_run
    proof.CASES = CASES
    raise SystemExit(proof.main())
