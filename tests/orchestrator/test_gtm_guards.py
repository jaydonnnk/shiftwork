"""Isolated S23 guard branches used by the retained source-omission matrix."""
import base64
import copy
import json
from types import SimpleNamespace
from collections import UserDict

import pytest
from pydantic import ValidationError

from tests.orchestrator.test_gtm_pipeline import (
    assessed, material_json, mission_and_state, pair_specs, response_for, reviewed_copy, prepare_flow, FakeAssist,
)
from shiftwork import orchestrator
from shiftwork.domain import canonical, task_contract
from shiftwork.domain.errors import MissionSpecInvalid, PublicStateInvalid
from shiftwork.evaluator import evaluator
from shiftwork.packs import registry
from shiftwork.domain.models import RunPurpose, RunState


SPEC_FAULTS = ("extra_duplicate_task", "duplicate_kind", "duplicate_id", "two_entities", "extra_condition", "decisions_not_list",
               "empty_decisions", "duplicate_decisions", "owner_not_text", "empty_owner", "repeat_not_text",
               "empty_repeat", "qualification_optional", "conditional_required")


@pytest.mark.parametrize("fault", SPEC_FAULTS)
def test_pipeline_spec_branches_refuse_independently(fault):
    raw = pair_specs(1)[0].model_dump(mode="json")
    if fault == "extra_duplicate_task": raw["tasks"].append(copy.deepcopy(raw["tasks"][0]))
    elif fault == "duplicate_kind": raw["tasks"][3]["kind"] = raw["tasks"][2]["kind"]
    elif fault == "duplicate_id": raw["tasks"][3]["id"] = raw["tasks"][2]["id"]
    elif fault == "two_entities": raw["requested_entities"].append("signal:another")
    elif fault == "qualification_optional": raw["tasks"][0]["required"] = False
    elif fault == "conditional_required": raw["tasks"][1]["required"] = True
    else:
        for task in raw["tasks"]:
            condition = task["condition_json"]
            if fault == "extra_condition": condition["send"] = True
            elif fault == "decisions_not_list": condition["expected_decisions"] = {"QUALIFIED": True}
            elif fault == "empty_decisions": condition["expected_decisions"] = []
            elif fault == "duplicate_decisions": condition["expected_decisions"] = ["QUALIFIED", "QUALIFIED"]
            elif fault == "owner_not_text": condition["qualified_owner"] = 7
            elif fault == "empty_owner": condition["qualified_owner"] = ""
            elif fault == "repeat_not_text": condition["repeat_of"] = 7
            elif fault == "empty_repeat": condition["repeat_of"] = ""
    with pytest.raises(ValidationError, match="pipeline"):
        task_contract.CustomerRequestSpec.model_validate(raw)


@pytest.mark.parametrize("fault", ["empty_existing_owner", "empty_existing_ref", "routes_missing", "empty_route",
    "review_route", "extra_dependency", "duplicate_record_id", "duplicate_entity_ref", "orphan_entity"])
def test_signal_inventory_branches_refuse_independently(fault):
    raw = material_json("fixtures/state/gtm_compare_state_v1.json")
    if fault.startswith("empty_existing"):
        raw["records"][0]["value"].update(existing_owner="owner-apac-platform", existing_record_ref="pipeline:signal:pair-intent")
        # Bind the reference to this actual signal, so only the empty-field guard can fail.
        raw["records"][0]["value"]["existing_record_ref"] = "pipeline:" + raw["records"][0]["entity_ref"]
        raw["records"][0]["value"]["existing_owner" if fault == "empty_existing_owner" else "existing_record_ref"] = ""
        with pytest.raises(ValidationError, match="cannot be empty"):
            task_contract.SignalFacts.model_validate(raw["records"][0]["value"])
        return
    if fault == "routes_missing": raw["routing_rules"].pop("APAC/platform")
    elif fault == "empty_route": raw["routing_rules"]["APAC/platform"] = ""
    elif fault == "review_route": raw["routing_rules"]["APAC/platform"] = "revenue-review"
    elif fault == "extra_dependency": raw["dependencies"]["crm"] = "available"
    elif fault == "duplicate_record_id": raw["records"][1]["record_id"] = raw["records"][0]["record_id"]
    elif fault == "duplicate_entity_ref":
        raw["records"][1]["entity_ref"] = raw["records"][0]["entity_ref"]
        raw["records"][1]["value"]["account_domain"] = raw["records"][0]["value"]["account_domain"]
    elif fault == "orphan_entity": raw["entities"].pop(raw["records"][0]["entity_ref"])
    # Validate this layer alone: the outer loader also rejects missing entities.
    with pytest.raises(ValidationError):
        task_contract.PipelineSnapshot.model_validate(raw)


@pytest.mark.parametrize("fault", ["write_not_object", "trace_not_list", "trace_short", "trace_method"])
def test_pipeline_row_shape_branches_fail_only_write(fault):
    spec = pair_specs(1)[0]
    raw = response_for(spec, "QUALIFIED")
    claim = raw["task_results"][2]["claims"][0]
    if fault == "write_not_object": claim["value"] = "a claimed CRM success"
    elif fault == "trace_not_list": claim["value"]["decision_trace"] = "RULES_FIRST"
    elif fault == "trace_short": claim["value"]["decision_trace"] = ["RULES_FIRST"]
    elif fault == "trace_method": claim["value"]["decision_trace"][0] = "SENT_TO_CRM"
    rows = assessed(spec, raw)
    assert [row.task_id for row in rows if not row.mandatory_pass] == ["write"]
    assert rows[2].reason_codes == (task_contract.ReasonCode.WRONG_ACTION,)


@pytest.mark.parametrize("fault", ["row_type", "trace_type", "trace_short", "active_status"])
def test_assessor_secondary_shape_guards_are_independent(fault):
    spec = pair_specs(1)[0]
    mission, state = mission_and_state()
    response = task_contract.validate_response_envelope(spec, json.dumps(response_for(spec, "QUALIFIED")).encode())
    results = list(response.task_results)
    target = 1 if fault == "active_status" else 2
    result = results[target]
    if fault == "active_status": result = result.model_copy(update={"status": task_contract.TaskStatus.REFUSED})
    else:
        claim = result.claims[0]
        value = dict(claim.value)
        if fault == "row_type": value = UserDict(value)
        elif fault == "trace_type": value["decision_trace"] = tuple(value["decision_trace"])
        else:
            class ShortCount(list):
                def __len__(self): return 1
            # Keep both indexed fields readable while isolating the length guard.
            value["decision_trace"] = ShortCount(value["decision_trace"])
        result = result.model_copy(update={"claims": (claim.model_copy(update={"value": value}),)})
    results[target] = result
    response = response.model_copy(update={"task_results": tuple(results)})
    rows = evaluator.assess_request(spec=spec, request_ordinal=1, mission=mission, snapshot=state, response=response)
    assert [row.task_id for row in rows if not row.mandatory_pass] == [result.task_id]


def test_pinned_decision_cannot_be_widened_by_correct_route():
    spec = pair_specs(3)[0]
    raw = spec.model_dump(mode="json")
    for task in raw["tasks"]: task["condition_json"]["expected_decisions"] = ["REVIEW"]
    narrowed = task_contract.CustomerRequestSpec.model_validate(raw)
    assert all(row.mandatory_pass for row in assessed(narrowed, response_for(spec, "REVIEW")))
    assert not any(row.mandatory_pass for row in assessed(narrowed, response_for(spec, "QUALIFIED")))


def test_existing_owner_cannot_change_even_without_second_write():
    mission, state = mission_and_state()
    spec = pair_specs(1)[0]
    data = state.model_dump(mode="json")
    record = next(row for row in data["records"] if row["entity_ref"] == spec.requested_entities[0])
    record["value"].update(existing_owner="owner-amer-platform", existing_record_ref="pipeline:" + record["entity_ref"])
    response = task_contract.validate_response_envelope(spec, json.dumps(response_for(spec, "QUALIFIED", repeat=True)).encode())
    rows = evaluator.assess_request(spec=spec, request_ordinal=1, mission=mission,
        snapshot=task_contract.PipelineSnapshot.model_validate(data), response=response)
    assert not any(row.mandatory_pass for row in rows), "existing owner cannot be replaced"


@pytest.mark.parametrize("fault", ["status", "claim", "commitment"])
def test_inactive_task_secondary_guards_are_independent(fault):
    spec = pair_specs(2)[1]
    mission, state = mission_and_state()
    response = task_contract.validate_response_envelope(spec, json.dumps(response_for(spec, "DISQUALIFIED")).encode())
    result = response.task_results[1]
    if fault == "status": result = result.model_copy(update={"status": task_contract.TaskStatus.COMPLETED})
    elif fault == "claim": result = result.model_copy(update={"claims": (task_contract.Claim(kind="owner_assignment", entity_ref=result.entity_ref,
        value="owner-apac-platform", evidence_refs=response.evidence_refs),)})
    else: result = result.model_copy(update={"commitment_ref": "invented"})
    # Deliberately bypass envelope shape validation to isolate the assessor's secondary guard.
    response = response.model_copy(update={"task_results": (response.task_results[0], result, *response.task_results[2:])})
    rows = evaluator.assess_request(spec=spec, request_ordinal=1, mission=mission, snapshot=state, response=response)
    assert [row.task_id for row in rows if not row.mandatory_pass] == ["owner"]


def test_pipeline_assessor_requires_pipeline_snapshot():
    mission, state = mission_and_state()
    spec = pair_specs(1)[0]
    response = task_contract.validate_response_envelope(spec, json.dumps(response_for(spec, "QUALIFIED")).encode())
    with pytest.raises(MissionSpecInvalid, match="owning GTM"):
        evaluator.assess_request(spec=spec, request_ordinal=1, mission=mission,
            snapshot=SimpleNamespace(**{key: getattr(state, key) for key in type(state).model_fields}), response=response)


def test_admission_requires_gtm_family_tasks_after_independent_loading(reviewed_copy, monkeypatch):
    pack = registry.resolve_pack("gtm")
    loaded = orchestrator.sealed_store.load_declared_family(pack.families[0], slug="gtm")
    first = loaded.cases[0]
    spec = first.stimulus.task_spec.model_copy(update={"tasks": first.stimulus.task_spec.tasks[:1]})
    broken = first.model_copy(update={"stimulus": first.stimulus.model_copy(update={"task_spec": spec})})
    monkeypatch.setattr(orchestrator.sealed_store, "load_declared_family", lambda *args, **kwargs: loaded.model_copy(update={"cases": (broken, *loaded.cases[1:])}))
    with pytest.raises(registry.PackUnavailable, match="pipeline contract"):
        orchestrator._verify_pack_material(pack)


@pytest.mark.parametrize("fault", ["count", "request_id", "text", "entity"])
def test_incident_binding_guards_are_independent(reviewed_copy, monkeypatch, fault):
    original = orchestrator.executor.load_batch
    def load(ref, raw):
        rows = original(ref, raw)
        if not ref.path_ref.endswith("gtm_pipeline_incident.jsonl"): return rows
        if fault == "count":
            class WrongCount(tuple):
                def __len__(self): return super().__len__() + 1
            # Keep content/zip binding valid while independently faulting cardinality.
            return WrongCount(rows)
        row = rows[0]
        if fault == "text": row = row.model_copy(update={"text": "another request"})
        else:
            body = json.loads(row.body)
            body["request_id" if fault == "request_id" else "entity_ref"] = "another-signal"
            row = row.model_copy(update={"body": json.dumps(body).encode()})
        return (row, *rows[1:])
    monkeypatch.setattr(orchestrator.executor, "load_batch", load)
    with pytest.raises(registry.PackUnavailable, match="incident request"):
        orchestrator._verify_pack_material(registry.resolve_pack("gtm"))


@pytest.mark.parametrize("fault", ["protected_phase", "missing_context", "foreign_context", "wrong_batch", "duplicate_batch",
    "zero_ordinal", "past_ordinal", "wrong_spec", "transport", "malformed"])
def test_prior_pipeline_input_guards_refuse_unbound_evidence(monkeypatch, fault):
    first, spec = pair_specs(3)[1:]
    batch = b"frozen batch"
    encoded = base64.b64encode(json.dumps([s.model_dump(mode="json") for s in (first, spec)]).encode()).decode()
    workload = SimpleNamespace(request_batch_hash=canonical.content_hash(base64.b64encode(batch).decode()), request_specs_bytes_base64=encoded)
    context = SimpleNamespace(engagement_slug="gtm", workloads=(workload,))
    output = SimpleNamespace(request_ordinal=1, transport_error=None, body=json.dumps(response_for(first, "QUALIFIED")).encode())
    phase, ordinal, current = "PUBLIC", 2, spec
    if fault == "protected_phase": phase = "PROTECTED"
    elif fault == "missing_context": context = None
    elif fault == "foreign_context": context.engagement_slug = "bookshop"
    elif fault == "wrong_batch": workload.request_batch_hash = "wrong"
    elif fault == "duplicate_batch": context.workloads = (workload, workload)
    elif fault == "zero_ordinal": ordinal = 0
    elif fault == "past_ordinal": ordinal = 3
    elif fault == "wrong_spec": current = spec.model_copy(update={"id": "other-request"})
    elif fault == "transport": output.transport_error = "failed"
    elif fault == "malformed": output.body = b"{}"
    monkeypatch.setattr(orchestrator.repo, "get_execution_context", lambda *args: context)
    monkeypatch.setattr(orchestrator.repo, "list_outputs", lambda *args: (output,))
    values = orchestrator.deployment_assessment_inputs(None, SimpleNamespace(context_id="context", id="run"), current, ordinal, b"state", batch, phase=phase)
    assert not values.get("prior_pipeline_results"), "unbound evidence must not count as a committed prior record"


@pytest.mark.parametrize("fault", ["currency", "facts", "foreign_state"])
def test_protected_signal_delta_refuses_invalid_inputs(monkeypatch, fault):
    case = material_json("sealed/cases/gtm_pipeline_ownership.json")["cases"][0]
    raw = copy.deepcopy(case["stimulus"]["state_delta"])
    if fault == "currency": raw["add_records"][0]["currency"] = "USD"
    elif fault == "facts": raw["add_records"][0]["value"]["confidence"] = 101
    delta = task_contract.ProtectedStateDelta.model_validate(raw)
    from shiftwork import config
    base_bytes = (config.PACKAGE_DIR / "fixtures/state/gtm_compare_state_v1.json").read_bytes()
    original = task_contract.load_public_state_bytes
    def load(encoded):
        if encoded == base_bytes:
            base = original(encoded)
            return base.model_copy(update={"engagement_slug": "bookshop"}) if fault == "foreign_state" else base
        # Bypass the final snapshot validation to isolate the earlier delta guards.
        data = json.loads(encoded)
        return SimpleNamespace(entities=data["entities"], records=tuple(SimpleNamespace(record_id=row["record_id"]) for row in data["records"]))
    monkeypatch.setattr(task_contract, "load_public_state_bytes", load)
    with pytest.raises(PublicStateInvalid):
        task_contract.resolve_protected_state(base_bytes, delta)


@pytest.mark.parametrize("path_kind", ["public_state_path", "comparison_state_path"])
def test_admission_checks_each_state_owner_independently(reviewed_copy, monkeypatch, path_kind):
    pack = registry.resolve_pack("gtm")
    original = task_contract.load_public_state
    target = reviewed_copy / getattr(pack, path_kind)
    def load(path):
        state = original(path)
        return state.model_copy(update={"engagement_slug": "bookshop"}) if path == target else state
    monkeypatch.setattr(task_contract, "load_public_state", load)
    with pytest.raises(registry.PackUnavailable, match="public state belongs"):
        orchestrator._verify_pack_material(pack)


def test_experimental_run_cannot_enter_selected_execution(monkeypatch):
    run = SimpleNamespace(purpose=RunPurpose.EXPERIMENT, context_id="gtm-context", state=RunState.RUNNING)
    monkeypatch.setattr(orchestrator, "get_run", lambda *args: run)
    with pytest.raises(orchestrator.LifecycleError, match="selected operation required"):
        orchestrator.execute_selected_operation(None, "gtm-experiment")


def test_gtm_operation_freezes_declared_rules_before_execution(tmp_path):
    from shiftwork.store import db
    from fastapi.testclient import TestClient
    from shiftwork.app import create_app
    from shiftwork.store import repo
    path = tmp_path / "gtm-freeze.db"
    with TestClient(create_app(str(path))) as client:
        opened = client.post("/api/engagements/gtm/shifts")
        assert opened.status_code == 201, opened.text
        conn = db.connect(path)
        try:
            context = orchestrator.freeze_diagnostic_context(conn, repo.get_shift(conn, opened.json()["id"]), operation=True)
            assert context.reducer_version == "operation-ledger-v3"
            assert context.starting_business_state_json.get("consequence_rules") == registry.resolve_pack("gtm").consequences.model_dump(mode="json"), "GTM frozen consequence rules omitted"
            assert context.starting_business_state_json["pipeline_records"] == {}
        finally:
            conn.close()


def test_gtm_role_guard_does_not_depend_on_patch_budget(tmp_path, monkeypatch, reviewed_copy):
    from fastapi.testclient import TestClient
    from shiftwork.app import create_app
    from shiftwork.store import db
    gateway = FakeAssist()
    with TestClient(create_app(str(tmp_path / "role-boundary.db"), executor="local_process", assist_gateway=gateway)) as client:
        flow = prepare_flow(client, monkeypatch)
        # Bypass only the secondary patch-count refusal. The role guard must still refuse.
        policy = registry.resolve_pack("gtm").assist.model_copy(update={"max_patch_proposals": 1})
        monkeypatch.setattr(orchestrator, "verified_assist_policy", lambda *args: policy)
        result = client.post(f"/api/shifts/{flow['shift_id']}/assist", json={"investigation_id": flow["investigation_id"],
            "role": "PATCH_PROPOSAL", "client_request_id": "forbidden-role"})
        assert result.status_code == 409 and gateway.roles == [], "GTM role refusal must hold before any provider call"


@pytest.mark.parametrize("variant", range(6))
@pytest.mark.parametrize("label", ["a", "b"])
def test_each_draft_workflow_satisfies_each_typed_protected_variant(tmp_path, monkeypatch, reviewed_copy, variant, label):
    import runpy
    from shiftwork.domain import comparison
    pack = registry.resolve_pack("gtm")
    case = orchestrator.sealed_store.load_declared_family(pack.families[0], slug="gtm").cases[variant]
    state_bytes = task_contract.resolve_protected_state((reviewed_copy / pack.comparison_state_path).read_bytes(), case.stimulus.state_delta)
    (tmp_path / "shop.json").write_bytes(state_bytes)
    monkeypatch.chdir(tmp_path)
    # Exercise the authored answer function on a disposable state, without starting a server.
    module = runpy.run_path(str(reviewed_copy / f"fixtures/artifacts/gtm/gtm_compare_repair_{label}_workflow.py"))
    raw = module["answer"](case.stimulus.request.model_dump(mode="json"))
    spec = case.stimulus.task_spec
    response = task_contract.validate_response_envelope(spec, json.dumps(raw).encode())
    mission = task_contract.load_mission(reviewed_copy / pack.mission_path)
    rows = evaluator.assess_request(spec=spec, request_ordinal=case.stimulus.request.ordinal, mission=mission,
        snapshot=task_contract.load_public_state_bytes(state_bytes), response=response)
    assert all(row.mandatory_pass for row in rows)
    assert comparison.protected_acceptance(case, rows)


@pytest.mark.parametrize("fault", ["missing_kind", "unknown_kind", "missing_task", "unknown_task", "empty_outcomes", "forbidden_reason"])
def test_gtm_family_repeats_typed_aspect_admission_refusal(reviewed_copy, fault):
    import hashlib
    pack = registry.resolve_pack("gtm")
    path = reviewed_copy / pack.families[0].case_file
    data = json.loads(path.read_bytes())
    aspect = data["cases"][0]["expected"]["aspect"]
    if fault == "missing_kind": aspect.pop("kind")
    elif fault == "unknown_kind": aspect["kind"] = "ACCEPT_SERVICE_LABEL"
    elif fault == "missing_task": aspect["task_id"] = None
    elif fault == "unknown_task": aspect["task_id"] = "another-task"
    elif fault == "empty_outcomes": aspect["expected_outcomes"] = []
    else: aspect["reason_code"] = "WRONG_ACTION"
    data["sealed_payload_sha256"] = hashlib.sha256(json.dumps(data["cases"], sort_keys=True,
        separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    path.write_bytes(json.dumps(data).encode())
    # The independent family loader has no registry pin check to mask aspect validation.
    with pytest.raises(orchestrator.sealed_store.InvalidSealedCase):
        orchestrator.sealed_store.load_declared_family(pack.families[0], slug="gtm")


@pytest.mark.parametrize("kind", ["NAMED_TASK_OUTCOMES", "NO_TASK_REASON_CODE"])
def test_gtm_typed_aspects_pass_and_fail_independently(reviewed_copy, kind):
    from shiftwork.domain import comparison
    pack = registry.resolve_pack("gtm")
    case = orchestrator.sealed_store.load_declared_family(pack.families[0], slug="gtm").cases[0]
    if kind == "NO_TASK_REASON_CODE":
        case = case.model_copy(update={"expected": {**case.expected, "aspect": {"kind": kind,
            "reason_code": "DUPLICATE_COMMITMENT", "task_id": None, "expected_outcomes": []}}})
    # The aspect predicate consumes assessments; isolate it from mandatory grading.
    rows = tuple(task_contract.TaskAssessment(request_id=case.stimulus.task_spec.id,
        request_ordinal=case.stimulus.request.ordinal, task_id=task.id, outcome=task_contract.TaskOutcome.USEFUL_COMPLETION,
        mandatory_pass=True, reason_codes=()) for task in case.stimulus.task_spec.tasks)
    assert comparison.protected_acceptance(case, rows)
    altered = rows[0].model_copy(update={"outcome": task_contract.TaskOutcome.INCORRECT_OUTPUT} if kind == "NAMED_TASK_OUTCOMES"
        else {"reason_codes": (task_contract.ReasonCode.DUPLICATE_COMMITMENT,)})
    assert not comparison.protected_acceptance(case, (altered, *rows[1:]))
