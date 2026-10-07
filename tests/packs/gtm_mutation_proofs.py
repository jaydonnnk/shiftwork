"""S23 independent source omissions, raw JUnit receipts and exact restoration.

Run only while no other tests or product processes use this worktree.
Each row runs one test parameter; crashes, setup errors and unrelated catches fail proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
TEST = "tests/orchestrator/test_gtm_pipeline.py"
GUARDS = "tests/orchestrator/test_gtm_guards.py"
TC = "shiftwork/domain/task_contract.py"
EV = "shiftwork/evaluator/evaluator.py"
OR = "shiftwork/orchestrator.py"
CASES = []


def fault(name, old, new, node, file=EV, test=TEST):
    CASES.append(dict(name=name, file=file, old=old, new=new, node=f"{test}::{node}"))


for label, old, new in (
    ("suppressed", "facts.suppressed or facts.employee_count < 50", "False or facts.employee_count < 50"),
    ("small_company", "facts.suppressed or facts.employee_count < 50", "facts.suppressed or False"),
    ("unavailable", 'snapshot.dependencies[record.dependency] == "available"', "True"),
    ("stale", "record.record_age_ms <= mission.max_record_age_ms", "True"),
    ("unknown_region", 'facts.region == "UNKNOWN"', "False"),
    ("unknown_product", 'facts.product == "UNKNOWN"', "False"),
    ("low_confidence", "facts.confidence < 80", "False"),
    ("ambiguous", 'facts.intent_label == "AMBIGUOUS"', "False"),
    ("research", 'facts.intent_label == "RESEARCH"', "False"),
    ("freshness_boundary", "record.record_age_ms <= mission.max_record_age_ms", "record.record_age_ms < mission.max_record_age_ms"),
    ("confidence_boundary", "facts.confidence < 80", "facts.confidence <= 80"),
    ("size_boundary", "facts.employee_count < 50", "facts.employee_count <= 50"),
):
    decision = "DISQUALIFIED" if label in {"suppressed", "small_company", "research"} else "QUALIFIED" if label.endswith("boundary") else "REVIEW"
    fault("rubric_" + label, old, new, f"test_each_public_qualification_rule_has_a_correct_and_wrong_decision[{label}-{decision}]")

for name, old, new, node in (
    ("result_entity", "result.entity_ref != entity_ref or any", "False or any", "wrong_entity"),
    ("claim_entity", "any(c.entity_ref != entity_ref for c in result.claims)", "False", "wrong_claim_entity"),
    ("claim_kind", "claim.kind != kind or result.commitment_ref is not None", "False or result.commitment_ref is not None", "wrong_claim_kind"),
    ("commitment", "claim.kind != kind or result.commitment_ref is not None", "claim.kind != kind or False", "invented_commitment"),
    ("evidence", "claim.evidence_refs != (record.record_id,)", "False", "wrong_evidence"),
    ("row_keys", 'set(row) != {"owner", "record_ref", "decision_trace"}', "False", "sent_field"),
    ("row_revenue", 'set(row) != {"owner", "record_ref", "decision_trace"}', "False", "revenue_field"),
    ("row_owner", 'row.get("owner") != owner', "False", "wrong_write_owner"),
    ("row_ref", 'row.get("record_ref") != "pipeline:" + entity_ref', "False", "wrong_record_ref"),
    ("trace_length", 'len(row["decision_trace"]) != 2', 'len(row["decision_trace"]) < 2', "extra_trace_step"),
    ("trace_decision", 'row["decision_trace"][1] != decision', "False", "wrong_trace"),
    ("scalar_value", "elif claim.value != value:", "elif False:", "wrong_owner"),
):
    fault(name, old, new, f"test_each_pipeline_output_fault_fails_its_named_task[{node}]")

fault("claim_cardinality", "elif len(result.claims) != 1:", "elif not result.claims:",
      "test_each_pipeline_output_fault_fails_its_named_task[duplicate_owner]")
fault("write_cardinality", "elif len(result.claims) != 1:", "elif not result.claims:",
      "test_each_pipeline_output_fault_fails_its_named_task[duplicate_write]")
fault("active_status", "elif result.status is not TaskStatus.COMPLETED:", "elif False:",
      "test_assessor_secondary_shape_guards_are_independent[active_status]", test=GUARDS)
fault("retry_name", "repeat_of is None or repeat_of in committed_prior_ids", "True", "test_retry_names_the_actual_valid_prior_request")
fault("prior_decision", "prior_decision is None or prior_decision == decision", "True", "test_retry_cannot_replace_a_previous_human_review_decision")
fault("prior_validity", "if not request_usefully_completed(earlier_spec, earlier):", "if False:",
      "test_retry_requires_valid_captured_first_record_and_never_writes_twice")
fault("mission_owner", 'or mission.engagement_slug != "gtm":', "or False:", "test_pipeline_assessor_requires_owning_mission_even_with_valid_gtm_state")
fault("pinned_owner", 'decision != "QUALIFIED" or condition["qualified_owner"] == owner', "True",
      "test_frozen_expected_owner_cannot_disagree_with_routing_even_when_output_is_correct")
fault("pinned_decisions", 'set(condition["expected_decisions"])', '{"QUALIFIED", "REVIEW", "DISQUALIFIED"}',
      "test_pinned_decision_cannot_be_widened_by_correct_route", test=GUARDS)
fault("existing_owner", "facts.existing_owner is None or facts.existing_owner == owner", "True",
      "test_existing_owner_cannot_change_even_without_second_write", test=GUARDS)
fault("snapshot_type", "not isinstance(snapshot, PipelineSnapshot) or mission.engagement_slug", "False or mission.engagement_slug",
      "test_pipeline_assessor_requires_pipeline_snapshot", test=GUARDS)
for label, old in (("status", "result.status is not TaskStatus.NOT_APPLICABLE"), ("claim", "result.claims"), ("commitment", "result.commitment_ref is not None")):
    anchor = "if result.status is not TaskStatus.NOT_APPLICABLE or result.claims or result.commitment_ref is not None:"
    fault("inactive_" + label, anchor, anchor.replace(old, "False"), f"test_inactive_task_secondary_guards_are_independent[{label}]", test=GUARDS)
for label, old, new in (
    ("trace_method", 'row["decision_trace"][0] not in {"RULES_FIRST", "RECORDED_CLASSIFICATION"}', "False"),
):
    fault(label, old, new, f"test_pipeline_row_shape_branches_fail_only_write[{label}]", test=GUARDS)
fault("trace_short", 'len(row["decision_trace"]) != 2', 'len(row["decision_trace"]) > 2',
      "test_assessor_secondary_shape_guards_are_independent[trace_short]", test=GUARDS)
for label, old in (("row_type", "not isinstance(row, dict)"), ("trace_type", 'not isinstance(row.get("decision_trace"), list)')):
    fault(label, old, "False", f"test_assessor_secondary_shape_guards_are_independent[{label}]", test=GUARDS)

for label, old in (
    ("extra_duplicate_task", "len(self.tasks) != 4"),
    ("duplicate_kind", "{task.kind for task in self.tasks} != kinds"),
    ("duplicate_id", "len({task.id for task in self.tasks}) != 4"),
    ("two_entities", "len(self.requested_entities) != 1"),
    ("extra_condition", 'set(condition) != {"expected_decisions", "qualified_owner", "review_owner", "repeat_of"}'),
    ("decisions_not_list", "not isinstance(decisions, list)"),
    ("empty_decisions", "not decisions"),
    ("duplicate_decisions", "len(decisions) != len(set(decisions))"),
    ("owner_not_text", 'not isinstance(condition.get("qualified_owner"), str)'),
    ("empty_owner", 'not condition["qualified_owner"]'),
    ("repeat_not_text", 'not isinstance(condition["repeat_of"], str)'),
    ("empty_repeat", 'not condition["repeat_of"]'),
    ("qualification_optional", "task.required != (task.kind is TaskKind.QUALIFY_SIGNAL)"),
    ("conditional_required", "task.required != (task.kind is TaskKind.QUALIFY_SIGNAL)"),
):
    fault("spec_" + label, old, "False", f"test_pipeline_spec_branches_refuse_independently[{label}]", file=TC, test=GUARDS)
for label, old in (
    ("wrong_signal", "any(task.requested_entity_ref != self.requested_entities[0] for task in self.tasks)"),
    ("disagreeing_conditions", "any(task.condition_json != self.tasks[0].condition_json for task in self.tasks)"),
    ("widen_review_owner", 'condition.get("review_owner") != "revenue-review"'),
    ("missing_rule", "not required_rules.issubset(self.mandatory_rule_ids)"),
):
    fault("spec_" + label, old, "False", f"test_pinned_spec_cannot_weaken_pipeline_contract[{label}]", file=TC)
fault("spec_decision_vocabulary", 'any(not isinstance(value, str) or value not in {"QUALIFIED", "REVIEW", "DISQUALIFIED"}\n                           for value in decisions)',
      "False", "test_pinned_spec_cannot_weaken_pipeline_contract[unknown_decision]", file=TC)
for label, old in (
    ("routes_missing", "set(self.routing_rules) != routes"),
    ("empty_route", "not owner or owner =="),
    ("review_route", 'owner == "revenue-review"'),
    ("extra_dependency", 'set(self.dependencies) != {"enrichment"}'),
    ("duplicate_record_id", "len({r.record_id for r in self.records}) != len(self.records)"),
    ("duplicate_entity_ref", "len({r.entity_ref for r in self.records}) != len(self.records)"),
    ("orphan_entity", "entity is None or entity.domain != facts.account_domain"),
):
    new = "False or owner ==" if label == "empty_route" else "entity is not None and entity.domain != facts.account_domain" if label == "orphan_entity" else "False"
    fault("state_" + label, old, new, f"test_signal_inventory_branches_refuse_independently[{label}]", file=TC, test=GUARDS)
for label, old, new in (
    ("empty_existing_owner", 'self.existing_owner == "" or self.existing_record_ref == ""', 'False or self.existing_record_ref == ""'),
    ("empty_existing_ref", 'self.existing_owner == "" or self.existing_record_ref == ""', 'self.existing_owner == "" or False'),
):
    fault(label, old, new, f"test_signal_inventory_branches_refuse_independently[{label}]", file=TC, test=GUARDS)
fault("state_domain", "entity.domain != facts.account_domain", "False", "test_signal_state_refuses_unusable_facts[wrong_domain]", file=TC)
fault("existing_pair", "(self.existing_owner is None) != (self.existing_record_ref is None)", "False",
      "test_signal_state_refuses_unusable_facts[incomplete_existing]", file=TC)
fault("existing_ref", 'facts.existing_record_ref != "pipeline:" + record.entity_ref', "False",
      "test_signal_state_refuses_unusable_facts[wrong_existing_ref]", file=TC)
for label, old in (("currency", "record.currency is not None"), ("foreign_state", 'base.engagement_slug != "gtm"')):
    anchor = 'if base.engagement_slug != "gtm" or record.currency is not None:'
    fault("delta_" + label, anchor, anchor.replace(old, "False"), f"test_protected_signal_delta_refuses_invalid_inputs[{label}]", file=TC, test=GUARDS)
fault("delta_facts", "                SignalFacts.model_validate(record.value)", "                pass",
      "test_protected_signal_delta_refuses_invalid_inputs[facts]", file=TC, test=GUARDS)

for label, old, new in (
    ("count", "len(incident_rows) != len(mission.request_specs)", "False"),
    ("request_id", 'json.loads(row.body).get("request_id") != spec.id', "False"),
    ("text", "row.text != spec.text", "False"),
    ("entity", 'json.loads(row.body).get("entity_ref") not in spec.requested_entities', "False"),
):
    # Preserve zip safety when omitting only the count guard.
    if label == "count": new = "False"
    fault("incident_" + label, old, new, f"test_incident_binding_guards_are_independent[{label}]", file=OR, test=GUARDS)
fault("family_tasks", "{task.kind for task in case.stimulus.task_spec.tasks} != evaluator.PIPELINE_TASK_KINDS", "False",
      "test_admission_requires_gtm_family_tasks_after_independent_loading", file=OR, test=GUARDS)
for label, old, new in (
    ("protected_phase", 'if phase != "PUBLIC":', "if False:"),
    ("foreign_context", 'context is None or context.engagement_slug != "gtm"', "context is None or False"),
    ("wrong_batch", "if workload.request_batch_hash == batch_hash", "if True"),
    ("duplicate_batch", "if len(workloads) != 1:", "if not workloads:"),
    ("zero_ordinal", "not 1 <= ordinal <= len(specs)", "ordinal > len(specs)"),
    ("wrong_spec", "specs[ordinal - 1] != spec", "False"),
    ("transport", "output.transport_error is None", "True"),
):
    fault("prior_" + label, old, new, f"test_prior_pipeline_input_guards_refuse_unbound_evidence[{label}]", file=OR, test=GUARDS)
for field, old, new in (
    ("record_id", 'text(record.get("record_id")), text(record.get("entity_ref"))', '"", text(record.get("entity_ref"))'),
    ("entity_ref", 'text(record.get("record_id")), text(record.get("entity_ref"))', 'text(record.get("record_id")), ""'),
    ("account_domain", 'needles.add(text(value.get("account_domain")))', "pass"),
    ("existing_record_ref", 'needles.add(text(value["existing_record_ref"]))', "pass"),
    ("company_name", 'text(entity.get("company_name")), text(entity.get("domain"))', '"", text(entity.get("domain"))'),
    ("domain", 'text(entity.get("company_name")), text(entity.get("domain"))', 'text(entity.get("company_name")), ""'),
):
    fault("private_" + field, old, new, f"test_each_gtm_private_signal_field_is_blocked_on_serialized_surfaces[{field}]", file="shiftwork/sealed/store.py")

for label in ("public_state_path", "comparison_state_path"):
    fault("state_owner_" + label, "if state.engagement_slug != pack.slug:", "if False:",
          f"test_admission_checks_each_state_owner_independently[{label}]", file=OR, test=GUARDS)
fault("chosen_operation_boundary", 'if shift.engagement_slug == "gtm" and selection.kind != "STARTER_BASELINE":',
      "if False:", "test_gtm_chosen_operation_waits_for_s24", file=OR, test=GUARDS)
fault("experiment_execution_boundary", "if run.purpose is not RunPurpose.OPERATION or run.context_id is None:\n        raise LifecycleError(\"conflict\", \"selected operation required\")",
      "if run.context_id is None:\n        raise LifecycleError(\"conflict\", \"selected operation required\")",
      "test_experimental_run_cannot_enter_selected_execution", file=OR, test=GUARDS)
for label, old in (
    ("allowed_assist_roles_json", 'json.loads(row["allowed_assist_roles_json"]) == [role.value for role in policy.allowed_roles]'),
    ("total_assist_budget_per_shift", 'row["total_assist_budget_per_shift"] == policy.total_calls_per_shift'),
    ("assist_level", 'row["assist_level"] == policy.level_label'),
):
    fault("assist_projection_" + label, old, "True",
          f"test_gtm_assist_projection_cannot_widen_registered_policy[{label}-" +
          {'allowed_assist_roles_json': '["HINT","DIAGNOSIS","PATCH_PROPOSAL"]', 'total_assist_budget_per_shift': '3', 'assist_level': 'unrestricted'}[label] + "]", file=OR)
fault("assist_role", "if role not in policy.allowed_roles:", "if False:",
      "test_gtm_role_guard_does_not_depend_on_patch_budget", file=OR, test=GUARDS)
fault("assist_total", "if len(events) >= limit:", "if False:",
      "test_reviewed_production_runs_six_fair_slots_without_business_writes", file=OR)
fault("experiment_ledger_write", '        repo.update_experiment_state(conn, experiment.id, final)\n        conn.commit()\n        return repo.get_experiment(conn, experiment.id)',
      '        repo.update_experiment_state(conn, experiment.id, final)\n'
      '        conn.execute("INSERT INTO ledger_events VALUES (\'gtm\', (SELECT COALESCE(MAX(seq),0)+1 FROM ledger_events WHERE engagement_slug=\'gtm\'), \'INCIDENT_OPENED\', \'[]\', \'{}\', 1, ?, ?)", ("0"*64, "1"*64))\n'
      '        conn.commit()\n        return repo.get_experiment(conn, experiment.id)',
      "test_reviewed_production_runs_six_fair_slots_without_business_writes", file="shiftwork/comparison_flow.py")
for label, old in (
    ("NAMED_TASK_OUTCOMES", "return by_id[aspect.task_id].outcome in aspect.expected_outcomes"),
    ("NO_TASK_REASON_CODE", "return all(aspect.reason_code not in entry.reason_codes for entry in assessments)"),
):
    fault("gtm_aspect_" + label, old, "return True", f"test_gtm_typed_aspects_pass_and_fail_independently[{label}]",
          file="shiftwork/domain/comparison.py", test=GUARDS)


def anchor(raw, case):
    old, new = case["old"].encode(), case["new"].encode()
    old_lf, new_lf = old.replace(b"\r\n", b"\n"), new.replace(b"\r\n", b"\n")
    for before, after in ((old, new), (old_lf, new_lf), (old_lf.replace(b"\n", b"\r\n"), new_lf.replace(b"\n", b"\r\n"))):
        if raw.count(before) == 1: return before, after
    raise ValueError("anchor must match exactly once: " + case["name"])


def run(case, out):
    path = ROOT / case["file"]
    raw = path.read_bytes()
    old, new = anchor(raw, case)
    log, xml = out / (case["name"] + ".log"), out / (case["name"] + ".xml")
    try:
        path.write_bytes(raw.replace(old, new, 1))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPYCACHEPREFIX=str(out / "unused-cache"))
        with log.open("xb") as stream:
            process = subprocess.run([sys.executable, "-m", "pytest", case["node"], "-q", "--tb=short", f"--junitxml={xml}"],
                                     cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        cases = list(ET.parse(xml).getroot().iter("testcase"))
        failures = [failure for item in cases for failure in item.findall("failure")]
        errors = [error for item in cases for error in item.findall("error")]
        message = failures[0].get("message", "") if failures else ""
        caught = process.returncode == 1 and len(cases) == 1 and len(failures) == 1 and not errors and message.startswith(("assert", "AssertionError", "Failed:"))
        return {"name": case["name"], "node": case["node"], "status": "FAIL_CAUGHT" if caught else "NOT_PROVED",
                "failures": len(failures), "errors": len(errors), "message": message, "source_sha256": hashlib.sha256(raw).hexdigest(),
                "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(), "xml_sha256": hashlib.sha256(xml.read_bytes()).hexdigest(),
                "restored": True}
    finally:
        path.write_bytes(raw)
        assert path.read_bytes() == raw, "source restoration failed"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--check-anchors", action="store_true")
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    selected = [case for case in CASES if not args.only or case["name"] in args.only]
    for case in selected: anchor((ROOT / case["file"]).read_bytes(), case)
    if args.check_anchors:
        print(json.dumps({"unique_anchors": len(selected)})); return 0
    args.out.mkdir(parents=True, exist_ok=False)
    rows = []
    for case in selected:
        row = run(case, args.out)
        rows.append(row)
        print(case["name"], row["status"], flush=True)
        (args.out / "results.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return 0 if all(row["status"] == "FAIL_CAUGHT" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
