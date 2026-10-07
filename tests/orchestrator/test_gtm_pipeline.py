"""S23 exact approved material, disposable refusal guards and trusted-local proof."""
import copy
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from demos.gtm_review import MATERIAL_PATHS
from demos.gtm_reviewed import reviewed_inventory
from demos.final_pivot import _bytes, create_v5_sample, snapshot_v5_rows
from packs.gtm_material import assert_version_pin, staged_gtm
from shiftwork import comparison_flow, config, orchestrator
from shiftwork.app import create_app
from shiftwork.assist.gateway import AssistReply
from shiftwork.domain import customer_answer, task_contract
from shiftwork.domain.errors import MissionSpecInvalid, PublicStateInvalid, TaskEnvelopeInvalid
from shiftwork.domain.models import ReasonCode
from shiftwork.evaluator import evaluator
from shiftwork.packs import registry
from shiftwork.sealed import store
from shiftwork.store import db, repo
from tests.orchestrator import pivot_flow


def material_json(path):
    return json.loads((config.PACKAGE_DIR / path).read_bytes())


def mission_and_state():
    pack = registry.resolve_pack("gtm")
    return (task_contract.load_mission(config.PACKAGE_DIR / pack.mission_path),
            task_contract.load_public_state(config.PACKAGE_DIR / pack.comparison_state_path))


def pair_specs(pair):
    return tuple(task_contract.CustomerRequestSpec.model_validate(raw) for raw in material_json(
        f"fixtures/requests/gtm_compare_pair_{pair:02d}_specs.json"))


def response_for(spec, decision, *, repeat=False):
    _, state = mission_and_state()
    entity = spec.requested_entities[0]
    record = next(r for r in state.records if r.entity_ref == entity)
    owner = "revenue-review" if decision == "REVIEW" else spec.tasks[0].condition_json["qualified_owner"]
    values = {"qualification": ("qualification", decision, True),
              "owner": ("owner_assignment", owner, decision != "DISQUALIFIED" and not repeat),
              "write": ("pipeline_write", {"owner": owner, "record_ref": "pipeline:" + entity,
                        "decision_trace": ["RULES_FIRST", decision]}, decision != "DISQUALIFIED" and not repeat),
              "handoff": ("handoff", "revenue-review", decision == "REVIEW" and not repeat)}
    return {"request_id": spec.id, "task_results": [
        {"task_id": task.id, "status": "COMPLETED" if values[task.id][2] else "NOT_APPLICABLE", "entity_ref": entity,
         "claims": [{"kind": values[task.id][0], "entity_ref": entity, "value": values[task.id][1],
                     "evidence_refs": [record.record_id]}] if values[task.id][2] else [],
         "commitment_ref": None, "explanation_code": None} for task in spec.tasks],
        "evidence_refs": [record.record_id], "uncertainty_codes": []}


def assessed(spec, response, prior=()):
    mission, state = mission_and_state()
    validated = task_contract.validate_response_envelope(spec, json.dumps(response).encode())
    return evaluator.assess_request(spec=spec, request_ordinal=1, mission=mission, snapshot=state,
                                    response=validated, prior_pipeline_results=prior)


def test_actual_gtm_reviewed_material_is_admitted_and_seeded_idempotently(tmp_path):
    reviewed_inventory()
    assert orchestrator.admit_pack("gtm") == registry.resolve_pack("gtm")
    path = tmp_path / "reviewed-seed.db"
    conn = db.connect(path)
    try:
        db.ensure_schema(conn)
        orchestrator.seed_registered_engagements(conn)
        tables = ("engagements", "engagement_config", "engagement_assist_policy")
        before = {table: tuple(tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY slug")) for table in tables}
        assert repo.get_engagement(conn, "gtm") is not None
        for _ in range(3):
            orchestrator.seed_registered_engagements(conn)
        assert before == {table: tuple(tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY slug")) for table in tables}
        policy = orchestrator.verified_assist_policy(conn, "gtm")
        assert policy.total_calls_per_shift == 2
        assert [role.value for role in policy.allowed_roles] == ["HINT", "DIAGNOSIS"]
        for table in ("shifts", "artifact_versions", "exposure_items", "operating_selections", "ledger_events", "incidents"):
            assert conn.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
    finally:
        conn.close()
    with TestClient(create_app(str(path))) as client:
        boards = client.get("/api/boards")
        assert boards.status_code == 200
        assert boards.json()[1]["availability"] == "AVAILABLE"


def test_unreviewed_gtm_declaration_refuses_before_seed_or_exposure(tmp_path, monkeypatch):
    packs = registry.registered_packs()
    monkeypatch.setattr(registry, "_PACKS", tuple(pack.model_copy(update={"reviewed_pins": ()})
                      if pack.slug == "gtm" else pack for pack in packs))
    with pytest.raises(registry.PackUnavailable):
        orchestrator.admit_pack("gtm")
    path = tmp_path / "unreviewed.db"
    with TestClient(create_app(str(path))) as client:
        boards = client.get("/api/boards")
        assert boards.status_code == 200
        assert boards.json()[1]["availability"] == "AWAITING_OPERATOR_REVIEW"
        assert client.post("/api/engagements/gtm/shifts").status_code == 404
    conn = db.connect(path)
    try:
        assert repo.get_engagement(conn, "gtm") is None
        assert conn.execute("SELECT count(*) FROM exposure_items WHERE engagement_slug='gtm'").fetchone()[0] == 0
    finally:
        conn.close()


@pytest.mark.parametrize("with_run", [True, False])
def test_admitted_gtm_startup_preserves_all_original_v5_bytes(tmp_path, monkeypatch, with_run):
    packs = registry.registered_packs()
    monkeypatch.setattr(registry, "_PACKS", tuple(pack.model_copy(update={"reviewed_pins": ()})
                      if pack.slug == "northline" else pack for pack in packs))
    original = tmp_path / "original-v5.db"
    copied = tmp_path / "admitted-startup.db"
    create_v5_sample(original, with_run=with_run)
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    source = sqlite3.connect(original)
    try:
        before = snapshot_v5_rows(source)
    finally:
        source.close()
    shutil.copyfile(original, copied)
    for _ in range(2):
        with TestClient(create_app(str(copied))):
            pass
        conn = db.connect(copied)
        try:
            for table, (columns, expected) in before.items():
                current = tuple(b"".join(_bytes(value) for value in row) for row in conn.execute(
                    f"SELECT {', '.join(columns)} FROM {table} ORDER BY rowid"))
                if table in ("engagements", "engagement_config"):
                    assert current[:len(expected)] == expected, f"historical {table} bytes changed during admitted seeding"
                    assert len(current) == len(expected) + 1
                    assert conn.execute(f"SELECT count(*) FROM {table} WHERE slug = 'gtm'").fetchone()[0] == 1
                else:
                    assert current == expected, f"historical {table} bytes changed during admitted seeding"
            assert conn.execute("SELECT count(*) FROM shifts WHERE engagement_slug = 'gtm'").fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM operating_selections").fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM exposure_items").fetchone()[0] == 0
        finally:
            conn.close()
    assert hashlib.sha256(original.read_bytes()).hexdigest() == original_hash



def test_packet_inventory_binds_exact_approved_material_and_literal_pins():
    inventory = reviewed_inventory()
    assert len(inventory["files"]) == len(MATERIAL_PATHS) == 19
    assert inventory["workload_request_counts"] == [3, 3, 3]
    assert len(inventory["reviewed_pins"]) == 19 and len(inventory["documents"]) == 3
    assert {row["key"] for row in inventory["offline_fixture_pins"]} == {
        "gtm_starter", "gtm_compare_candidate_a", "gtm_compare_candidate_b"}


@pytest.mark.parametrize("damage", ["unknown_region", "bool_confidence", "negative_confidence", "extra_fact", "duplicate_signal", "wrong_domain", "incomplete_existing", "wrong_existing_ref"])
def test_signal_state_refuses_unusable_facts(damage):
    data = material_json("fixtures/state/gtm_compare_state_v1.json")
    fact = data["records"][0]["value"]
    if damage == "unknown_region": fact["region"] = "MARS"
    elif damage == "bool_confidence": fact["confidence"] = True
    elif damage == "negative_confidence": fact["confidence"] = -1
    elif damage == "extra_fact": fact["send_email"] = True
    elif damage == "duplicate_signal": data["records"].append(copy.deepcopy(data["records"][0]))
    elif damage == "wrong_domain": fact["account_domain"] = "someone-else.example"
    elif damage == "incomplete_existing": fact["existing_owner"] = "owner-apac-platform"
    elif damage == "wrong_existing_ref": fact.update(existing_owner="owner-apac-platform", existing_record_ref="pipeline:other")
    with pytest.raises(PublicStateInvalid):
        task_contract.load_public_state_bytes(json.dumps(data).encode())


@pytest.mark.parametrize("damage", ["missing_task", "wrong_signal", "missing_rule", "unknown_decision", "unhashable_decision", "disagreeing_conditions", "widen_review_owner"])
def test_pinned_spec_cannot_weaken_pipeline_contract(damage):
    spec = material_json("fixtures/requests/gtm_compare_pair_01_specs.json")[0]
    if damage == "missing_task": spec["tasks"].pop()
    elif damage == "wrong_signal": spec["tasks"][0]["requested_entity_ref"] = "signal:other"
    elif damage == "missing_rule": spec["mandatory_rule_ids"].remove("gtm.exactly_once")
    elif damage == "unknown_decision":
        for task in spec["tasks"]: task["condition_json"]["expected_decisions"] = ["SENT"]
    elif damage == "unhashable_decision":
        for task in spec["tasks"]: task["condition_json"]["expected_decisions"] = [{"decision": "QUALIFIED"}]
    elif damage == "disagreeing_conditions": spec["tasks"][1]["condition_json"]["qualified_owner"] = "owner-other"
    elif damage == "widen_review_owner":
        for task in spec["tasks"]: task["condition_json"]["review_owner"] = "auto-send"
    with pytest.raises(ValidationError):
        task_contract.CustomerRequestSpec.model_validate(spec)


@pytest.mark.parametrize("pair,index,decision", [(1, 0, "QUALIFIED"), (1, 1, "QUALIFIED"), (2, 0, "REVIEW"),
                                                (2, 1, "DISQUALIFIED"), (3, 0, "QUALIFIED"), (3, 0, "REVIEW")])
def test_independent_assessor_accepts_the_declared_decision_and_owner(pair, index, decision):
    spec = pair_specs(pair)[index]
    rows = assessed(spec, response_for(spec, decision))
    assert all(row.mandatory_pass for row in rows)
    assert evaluator.request_usefully_completed(spec, rows)


FAULTS = [("wrong_owner", "owner", ReasonCode.WRONG_ACTION), ("duplicate_owner", "owner", ReasonCode.DUPLICATE_COMMITMENT),
          ("duplicate_write", "write", ReasonCode.DUPLICATE_COMMITMENT), ("wrong_write_owner", "write", ReasonCode.WRONG_ACTION),
          ("wrong_record_ref", "write", ReasonCode.WRONG_ACTION), ("wrong_trace", "write", ReasonCode.WRONG_ACTION),
          ("unhashable_trace", "write", ReasonCode.WRONG_ACTION),
          ("sent_field", "write", ReasonCode.WRONG_ACTION), ("revenue_field", "write", ReasonCode.WRONG_ACTION),
          ("wrong_evidence", "owner", ReasonCode.UNSUPPORTED_CLAIM), ("wrong_entity", "owner", ReasonCode.WRONG_ENTITY),
          ("wrong_claim_entity", "owner", ReasonCode.WRONG_ENTITY), ("wrong_claim_kind", "owner", ReasonCode.WRONG_ACTION),
          ("invented_commitment", "owner", ReasonCode.WRONG_ACTION), ("extra_trace_step", "write", ReasonCode.WRONG_ACTION),
          ("missing_owner", "owner", ReasonCode.REQUIRED_TASK_MISSING), ("missing_write", "write", ReasonCode.REQUIRED_TASK_MISSING),
          ("unjustified_skip", "owner", ReasonCode.REQUIRED_TASK_MISSING), ("empty_claim", "owner", ReasonCode.REQUIRED_TASK_MISSING)]


@pytest.mark.parametrize("fault,target,reason", FAULTS, ids=[item[0] for item in FAULTS])
def test_each_pipeline_output_fault_fails_its_named_task(fault, target, reason):
    spec = pair_specs(1)[0]
    response = response_for(spec, "QUALIFIED")
    result = next(row for row in response["task_results"] if row["task_id"] == target)
    if fault == "wrong_owner": result["claims"][0]["value"] = "owner-amer-platform"
    elif fault in ("duplicate_owner", "duplicate_write"): result["claims"].append(copy.deepcopy(result["claims"][0]))
    elif fault == "wrong_write_owner": result["claims"][0]["value"]["owner"] = "owner-amer-platform"
    elif fault == "wrong_record_ref": result["claims"][0]["value"]["record_ref"] = "pipeline:other"
    elif fault == "wrong_trace": result["claims"][0]["value"]["decision_trace"] = ["RULES_FIRST", "DISQUALIFIED"]
    elif fault == "unhashable_trace": result["claims"][0]["value"]["decision_trace"] = [{"method": "RULES_FIRST"}, "QUALIFIED"]
    elif fault == "sent_field": result["claims"][0]["value"]["sent_message"] = True
    elif fault == "revenue_field": result["claims"][0]["value"]["revenue"] = 50000
    elif fault == "wrong_evidence": result["claims"][0]["evidence_refs"] = ["public:invented"]; response["evidence_refs"].append("public:invented")
    elif fault == "wrong_entity": result["entity_ref"] = "signal:other"
    elif fault == "wrong_claim_entity": result["claims"][0]["entity_ref"] = "signal:other"
    elif fault == "wrong_claim_kind": result["claims"][0]["kind"] = "handoff"
    elif fault == "invented_commitment": result["commitment_ref"] = "invented-commitment"
    elif fault == "extra_trace_step": result["claims"][0]["value"]["decision_trace"].append("EXTRA")
    elif fault in ("missing_owner", "missing_write"): response["task_results"].remove(result)
    elif fault == "unjustified_skip": result.update(status="NOT_APPLICABLE", claims=[])
    elif fault == "empty_claim": result["claims"] = []
    rows = assessed(spec, response)
    failing = [row for row in rows if not row.mandatory_pass]
    assert [row.task_id for row in failing] == [target], "fault must reach exactly its own task guard"
    assert failing[0].reason_codes == (reason,), "fault must reach its intended reason"
    assert not evaluator.request_usefully_completed(spec, rows)


@pytest.mark.parametrize("case", ["qualify_suppressed", "skip_low_confidence_handoff", "wrong_low_confidence_owner", "owner_on_disqualified", "forged_qualification"])
def test_qualification_suppression_and_human_review_are_independent(case):
    spec = pair_specs(2)[1 if case in ("qualify_suppressed", "owner_on_disqualified") else 0]
    response = response_for(spec, "DISQUALIFIED" if spec == pair_specs(2)[1] else "REVIEW")
    if case == "qualify_suppressed": response = response_for(spec, "QUALIFIED")
    elif case == "skip_low_confidence_handoff": response["task_results"][3].update(status="NOT_APPLICABLE", claims=[])
    elif case == "wrong_low_confidence_owner": response["task_results"][1]["claims"][0]["value"] = "owner-apac-platform"
    elif case == "owner_on_disqualified": response["task_results"][1].update(status="COMPLETED", claims=[{
        "kind": "owner_assignment", "entity_ref": spec.requested_entities[0], "value": "owner-apac-platform", "evidence_refs": response["evidence_refs"]}])
    elif case == "forged_qualification": response["task_results"][0]["claims"][0]["value"] = {"decision": "REVIEW"}
    assert any(not row.mandatory_pass for row in assessed(spec, response))


def test_retry_requires_valid_captured_first_record_and_never_writes_twice():
    first, retry = pair_specs(3)[1:]
    original = response_for(first, "QUALIFIED")
    prior = ((first, task_contract.validate_response_envelope(first, json.dumps(original).encode())),)
    repeated = response_for(retry, "QUALIFIED", repeat=True)
    assert all(row.mandatory_pass for row in assessed(retry, repeated, prior))
    assert any(not row.mandatory_pass for row in assessed(retry, repeated)), "a claimed retry cannot invent prior evidence"
    duplicate = response_for(retry, "QUALIFIED")
    rows = assessed(retry, duplicate, prior)
    assert {row.task_id for row in rows if ReasonCode.DUPLICATE_COMMITMENT in row.reason_codes} == {"owner", "write"}
    forged = copy.deepcopy(original)
    forged["task_results"][1]["claims"][0]["value"] = "owner-other"
    bad_prior = ((first, task_contract.validate_response_envelope(first, json.dumps(forged).encode())),)
    assert any(not row.mandatory_pass for row in assessed(retry, repeated, bad_prior))


def test_rendering_and_public_projection_do_not_repeat_service_send_or_revenue_prose():
    spec = pair_specs(1)[0]
    response = response_for(spec, "QUALIFIED")
    response["task_results"][1]["claims"][0]["value"] = "Sent a customer message and earned 50000 revenue"
    mission, state = mission_and_state()
    rendered = customer_answer.render_task_customer_text(spec=spec, mission=mission, snapshot=state,
               response=task_contract.validate_response_envelope(spec, json.dumps(response).encode()))
    assert "Sent a customer" not in rendered and "50000" not in rendered
    with pytest.raises(TaskEnvelopeInvalid):
        task_contract.validate_response_envelope(spec, json.dumps({**response, "sent_message": "yes"}).encode())


PRIVATE_FIELDS = ("record_id", "entity_ref", "account_domain", "existing_record_ref", "company_name", "domain")


@pytest.mark.parametrize("field", PRIVATE_FIELDS)
def test_each_gtm_private_signal_field_is_blocked_on_serialized_surfaces(tmp_path, monkeypatch, field):
    root = tmp_path / "private-cases"
    shutil.copytree(config.SEALED_CASES_DIR, root)
    monkeypatch.setattr(config, "SEALED_CASES_DIR", root)
    path = root / "gtm_pipeline_ownership.json"
    data = json.loads(path.read_bytes())
    needle = "PRIVATE_GTM_" + field + r"_ONLY_C:\private\signal"
    delta = data["cases"][0]["stimulus"]["state_delta"]
    record = delta["add_records"][0]
    if field in ("record_id", "entity_ref"):
        record[field] = needle
    elif field in ("account_domain", "existing_record_ref"):
        record["value"][field] = needle
    else:
        next(iter(delta["add_entities"].values()))[field] = needle
    path.write_bytes(json.dumps(data).encode())
    orchestrator.assert_public_projection({"owner": "owner-apac-platform", "decision": "QUALIFIED"})
    for surface in (needle, json.dumps({"probe": needle}), json.dumps(json.dumps({"probe": needle})),
                    json.dumps({"probe_base64": base64.b64encode(needle.encode()).decode()}),
                    json.dumps({"probe": needle.replace("\\", "/")}),
                    json.dumps({"probe_base64": base64.b64encode(needle.replace("\\", "/").encode()).decode()})):
        with pytest.raises(orchestrator.LifecycleError, match="private material"):
            orchestrator.assert_public_projection(surface)


@pytest.mark.parametrize("case,decision", [("suppressed", "DISQUALIFIED"), ("small_company", "DISQUALIFIED"),
    ("unavailable", "REVIEW"), ("stale", "REVIEW"), ("unknown_region", "REVIEW"), ("unknown_product", "REVIEW"),
    ("low_confidence", "REVIEW"), ("ambiguous", "REVIEW"), ("research", "DISQUALIFIED"),
    ("freshness_boundary", "QUALIFIED"), ("confidence_boundary", "QUALIFIED"), ("size_boundary", "QUALIFIED")])
def test_each_public_qualification_rule_has_a_correct_and_wrong_decision(case, decision):
    mission, original = mission_and_state()
    data = original.model_dump(mode="json")
    record = data["records"][1]
    assert record["entity_ref"] == "signal:pair-apac"
    facts = record["value"]
    if case == "suppressed": facts["suppressed"] = True
    elif case == "small_company": facts["employee_count"] = 49
    elif case == "unavailable": data["dependencies"]["enrichment"] = "unavailable"
    elif case == "stale": record["record_age_ms"] = mission.max_record_age_ms + 1
    elif case == "unknown_region": facts["region"] = "UNKNOWN"
    elif case == "unknown_product": facts["product"] = "UNKNOWN"
    elif case == "low_confidence": facts["confidence"] = 79
    elif case == "ambiguous": facts["intent_label"] = "AMBIGUOUS"
    elif case == "research": facts["intent_label"] = "RESEARCH"
    elif case == "freshness_boundary": record["record_age_ms"] = mission.max_record_age_ms
    elif case == "confidence_boundary": facts["confidence"] = 80
    elif case == "size_boundary": facts["employee_count"] = 50
    state = task_contract.PipelineSnapshot.model_validate(data)
    assert evaluator._pipeline_decisions(task_contract.SignalFacts.model_validate(facts), state.records[1], state,
                                        mission) == {decision}, "qualification rule must return exactly its published decisions"
    spec_data = pair_specs(1)[0].model_dump(mode="json")
    for task in spec_data["tasks"]:
        task["condition_json"]["expected_decisions"] = ["QUALIFIED", "REVIEW", "DISQUALIFIED"]
    spec = task_contract.CustomerRequestSpec.model_validate(spec_data)
    def check(value):
        response = task_contract.validate_response_envelope(spec, json.dumps(response_for(spec, value)).encode())
        return evaluator.assess_request(spec=spec, request_ordinal=1, mission=mission, snapshot=state, response=response)
    assert all(row.mandatory_pass for row in check(decision))
    wrong = "QUALIFIED" if decision != "QUALIFIED" else "REVIEW"
    assert not next(row for row in check(wrong) if row.task_id == "qualification").mandatory_pass


def test_pipeline_assessor_requires_owning_mission_even_with_valid_gtm_state():
    mission, state = mission_and_state()
    spec = pair_specs(1)[0]
    response = task_contract.validate_response_envelope(spec, json.dumps(response_for(spec, "QUALIFIED")).encode())
    with pytest.raises(MissionSpecInvalid, match="owning GTM"):
        evaluator.assess_request(spec=spec, request_ordinal=1, mission=mission.model_copy(update={"engagement_slug": "bookshop"}),
                                 snapshot=state, response=response)


def test_frozen_expected_owner_cannot_disagree_with_routing_even_when_output_is_correct():
    original = pair_specs(1)[0]
    response = response_for(original, "QUALIFIED")
    raw = original.model_dump(mode="json")
    for task in raw["tasks"]:
        task["condition_json"]["qualified_owner"] = "owner-amer-platform"
    spec = task_contract.CustomerRequestSpec.model_validate(raw)
    assert any(not row.mandatory_pass for row in assessed(spec, response)), "pinned expected owner disagrees with frozen routing"


def test_retry_names_the_actual_valid_prior_request():
    first, original = pair_specs(3)[1:]
    prior = ((first, task_contract.validate_response_envelope(first, json.dumps(response_for(first, "QUALIFIED")).encode())),)
    raw = original.model_dump(mode="json")
    for task in raw["tasks"]:
        task["condition_json"]["repeat_of"] = "invented-prior-request"
    retry = task_contract.CustomerRequestSpec.model_validate(raw)
    assert any(not row.mandatory_pass for row in assessed(retry, response_for(retry, "QUALIFIED", repeat=True), prior)), "retry must name its captured prior"


def test_retry_cannot_replace_a_previous_human_review_decision():
    first = pair_specs(3)[0]
    raw = first.model_dump(mode="json")
    raw["id"] = "gtm-repeat-recorded-intent"
    for task in raw["tasks"]:
        task["condition_json"]["repeat_of"] = first.id
    retry = task_contract.CustomerRequestSpec.model_validate(raw)
    prior = ((first, task_contract.validate_response_envelope(first, json.dumps(response_for(first, "REVIEW")).encode())),)
    assert all(row.mandatory_pass for row in assessed(retry, response_for(retry, "REVIEW", repeat=True), prior))
    assert any(not row.mandatory_pass for row in assessed(retry, response_for(retry, "QUALIFIED", repeat=True), prior)), "retry cannot replace the first decision"


@pytest.fixture
def reviewed_copy(tmp_path, monkeypatch):
    return staged_gtm(monkeypatch, tmp_path / "fault-package")


@pytest.mark.parametrize("field,value", [("allowed_assist_roles_json", '["HINT","DIAGNOSIS","PATCH_PROPOSAL"]'),
    ("total_assist_budget_per_shift", 3), ("assist_level", "unrestricted")])
def test_gtm_assist_projection_cannot_widen_registered_policy(tmp_path, reviewed_copy, field, value):
    conn = db.connect(tmp_path / "assist-policy.db")
    try:
        db.ensure_schema(conn)
        orchestrator.seed_registered_engagements(conn)
        assert orchestrator.verified_assist_policy(conn, "gtm").total_calls_per_shift == 2
        conn.execute(f"UPDATE engagement_assist_policy SET {field}=? WHERE slug='gtm'", (value,))
        conn.commit()
        with pytest.raises(orchestrator.LifecycleError, match="policy projection disagrees"):
            orchestrator.verified_assist_policy(conn, "gtm")
        assert conn.execute("SELECT count(*) FROM assist_events").fetchone()[0] == 0
    finally:
        conn.close()


@pytest.mark.parametrize("path", MATERIAL_PATHS)
def test_each_missing_gtm_file_refuses_admission_before_any_exposure(reviewed_copy, path):
    target = reviewed_copy / path
    original = target.read_bytes()
    target.unlink()
    try:
        with pytest.raises(registry.PackUnavailable):
            orchestrator.admit_pack("gtm")
    finally:
        target.write_bytes(original)


@pytest.mark.parametrize("path", MATERIAL_PATHS)
def test_each_gtm_pin_drift_refuses_admission(reviewed_copy, path):
    target = reviewed_copy / path
    original = target.read_bytes()
    target.write_bytes(original + b" ")
    try:
        with pytest.raises(registry.PackUnavailable):
            orchestrator.admit_pack("gtm")
    finally:
        target.write_bytes(original)


@pytest.mark.parametrize("path,field", [(path, field) for path in (
    "fixtures/requests/gtm_compare_manifest.json", "sealed/cases/gtm_pipeline_ownership.json")
    for field in ("review_status", "sealed_payload_sha256")])
def test_review_or_seal_missing_refuses_despite_matching_disposable_pin(reviewed_copy, monkeypatch, path, field):
    data = json.loads((reviewed_copy / path).read_bytes())
    data[field] = "DRAFT" if field == "review_status" else "0" * 64
    raw = json.dumps(data).encode()
    (reviewed_copy / path).write_bytes(raw)
    packs = registry.registered_packs()
    monkeypatch.setattr(registry, "_PACKS", tuple(pack.model_copy(update={"reviewed_pins": tuple(
        pin.model_copy(update={"sha256": hashlib.sha256(raw).hexdigest()}) if pin.path == path else pin
        for pin in pack.reviewed_pins)}) if pack.slug == "gtm" else pack for pack in packs))
    with pytest.raises(registry.PackUnavailable):
        orchestrator.admit_pack("gtm")


@pytest.mark.parametrize("source_slug", ["bookshop", "northline"])
@pytest.mark.parametrize("field", ["mission_path", "public_state_path", "comparison_state_path", "incident_request_path", "manifest_path"])
def test_cross_board_material_refuses_with_matching_disposable_pin(reviewed_copy, monkeypatch, source_slug, field):
    pack = registry.resolve_pack("gtm")
    source = registry.resolve_pack(source_slug)
    path = getattr(source, field)
    foreign = pack.model_copy(update={field: path, "reviewed_pins": (*pack.reviewed_pins,
        registry.ReviewedPin(path=path, sha256=hashlib.sha256((reviewed_copy / path).read_bytes()).hexdigest()))})
    monkeypatch.setattr(registry, "_PACKS", tuple(foreign if p.slug == "gtm" else p for p in registry.registered_packs()))
    with pytest.raises(registry.PackUnavailable):
        orchestrator.admit_pack("gtm")


def test_six_typed_protected_variants_use_their_own_additive_signal_state(reviewed_copy):
    pack = orchestrator.admit_pack("gtm")
    family = store.load_declared_family(pack.families[0], slug=pack.slug)
    assert len(family.cases) == 6
    states = []
    for case in family.cases:
        states.append(task_contract.resolve_protected_state((reviewed_copy / pack.comparison_state_path).read_bytes(),
                      case.stimulus.state_delta))
    assert len(set(states)) == 6
    assert {t.kind for case in family.cases for t in case.stimulus.task_spec.tasks} == evaluator.PIPELINE_TASK_KINDS


def business_rows(conn):
    return {table: tuple(tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY rowid"))
            for table in ("ledger_events", "incidents", "operating_selections")}


class FakeAssist:
    def __init__(self): self.roles = []
    def generate(self, *, model_id, role, prompt):
        self.roles.append(role.value)
        return AssistReply("Test-only advice: compare the observed route with the frozen region rule.")


def prepare_flow(client, monkeypatch):
    opened = client.post("/api/engagements/gtm/shifts")
    assert opened.status_code == 201, opened.text
    shift_id = opened.json()["id"]
    board = client.get("/api/engagements/gtm/board")
    assert board.status_code == 200, board.text
    starter = board.json()["operating_selection"]
    source_version = client.get(f"/api/artifact-versions/{starter['selected_version_id']}")
    assert source_version.status_code == 200, source_version.text
    assert_version_pin(source_version.json(), "gtm_starter")
    source = client.post(f"/api/shifts/{shift_id}/runs", json={"client_request_id": "gtm-starter"})
    assert source.status_code == 202, source.text
    run = pivot_flow.wait_run(client, source.json()["id"])
    assert run["state"] == "FINALIZED", run
    checks = client.get(f"/api/runs/{run['id']}/checks")
    assert checks.status_code == 200, checks.text
    conn = db.connect(client.app.state.db_path)
    try:
        assessments = repo.list_task_assessment_models(conn, run["id"])
        assert {a.task_id for a in assessments if ReasonCode.WRONG_ACTION in a.reason_codes} == {"owner", "write"}
    finally:
        conn.close()
    investigation = client.post(f"/api/shifts/{shift_id}/investigations", json={
        "source_run_id": run["id"], "source_request_ordinal": 1, "cause": "The starter ignores the region/product owner map.",
        "falsifier": "The captured APAC demo output already names its APAC owner.", "public_test": "Compare the captured owner and record with the frozen route.",
        "client_request_id": "gtm-investigation"})
    assert investigation.status_code == 201, investigation.text
    candidates = {}
    for label in ("A", "B"):
        files = {"service.py": (config.PACKAGE_DIR / f"fixtures/artifacts/gtm/gtm_compare_repair_{label.lower()}_workflow.py").read_text(encoding="utf-8")}
        saved = client.put(f"/api/shifts/{shift_id}/artifact", json={"files": files})
        assert saved.status_code == 200, saved.text
        frozen = client.post(f"/api/shifts/{shift_id}/artifact/versions", json={"contract": config.GTM_STARTER_CONTRACT_JSON})
        assert frozen.status_code == 201, frozen.text
        candidates[label] = frozen.json()
        source = client.get(f"/api/artifact-versions/{frozen.json()['id']}")
        assert source.status_code == 200, source.text
        assert_version_pin(source.json(), "gtm_compare_candidate_" + label.lower())
    return {"shift_id": shift_id, "starter": starter, "source_run": run,
            "investigation_id": investigation.json()["id"], "candidates": candidates}


def test_reviewed_production_runs_six_fair_slots_without_business_writes(tmp_path, monkeypatch):
    reviewed_inventory()
    gateway = FakeAssist()
    with TestClient(create_app(str(tmp_path / "comparison.db"), executor="local_process", assist_gateway=gateway)) as client:
        flow = prepare_flow(client, monkeypatch)
        conn = db.connect(client.app.state.db_path)
        try:
            before = business_rows(conn)
            experiment = comparison_flow.create_qualifying_comparison(conn, flow["shift_id"],
                candidate_a_version_id=flow["candidates"]["A"]["id"], candidate_b_version_id=flow["candidates"]["B"]["id"],
                investigation_id=flow["investigation_id"], declared_treatment="Rules-first human review versus recorded-confidence direct routing.",
                client_request_id="gtm-six-slots", adapter="local_process")
            comparison_flow.execute_comparison(conn, experiment.id)
            assert business_rows(conn) == before, "public/protected experiments must preserve every business row and selection"
            result = client.get(f"/api/experiments/{experiment.id}")
            assert result.status_code == 200, result.text
            outcome = result.json()["outcome"]
            assert outcome["status"] == "COMPLETE", outcome
            assert all(item["eligible"] for item in outcome["eligibility"]), outcome
            assert len(result.json()["trials"]) == 6
            treatments = {}
            for trial in result.json()["trials"]:
                if trial["pair_ordinal"] == 3:
                    captured = json.loads(base64.b64decode(trial["outputs"][0]["body_base64"]))
                    treatments[trial["candidate_label"]] = captured["task_results"][0]["claims"][0]["value"]
            assert treatments == {"A": "REVIEW", "B": "QUALIFIED"}, "the competing workflows must produce their declared difference"
            assert repo.get_latest_operating_selection(conn, "gtm").id == flow["starter"]["id"]
            context = repo.get_execution_context(conn, experiment.context_id)
            assert [w.request_count for w in context.workloads] == [3, 3, 3]
            assert len(repo.list_protected_case_snapshots(conn, context.protected_reservation_id)) == 3
            station = client.get(f"/api/shifts/{flow['shift_id']}/investigations")
            assert station.status_code == 200, station.text
            assert station.json()["assist_limit"] == 2 and station.json()["assist_allowed_roles"] == ["HINT", "DIAGNOSIS"]
            patch = client.post(f"/api/shifts/{flow['shift_id']}/assist", json={"investigation_id": flow["investigation_id"], "role": "PATCH_PROPOSAL", "client_request_id": "gtm-no-patch"})
            assert patch.status_code == 409 and gateway.roles == [], patch.text
            for index, role in enumerate(("HINT", "DIAGNOSIS")):
                response = client.post(f"/api/shifts/{flow['shift_id']}/assist", json={"investigation_id": flow["investigation_id"], "role": role, "client_request_id": f"gtm-assist-{index}"})
                assert response.status_code == 200, response.text
            exhausted = client.post(f"/api/shifts/{flow['shift_id']}/assist", json={"investigation_id": flow["investigation_id"], "role": "HINT", "client_request_id": "gtm-third-assist"})
            assert exhausted.status_code == 409 and gateway.roles == ["HINT", "DIAGNOSIS"]
            proof_out = os.environ.get("SHIFTWORK_S23_PROOF_OUT")
            if proof_out:
                database = Path(proof_out).with_suffix(".db")
                assert not database.exists()
                backup = sqlite3.connect(database)
                try:
                    conn.backup(backup)
                finally:
                    backup.close()
                proof = {"database_sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
                    "starter_task_assessments": [item.model_dump(mode="json") for item in repo.list_task_assessment_models(conn, flow["source_run"]["id"])],
                    "mode": "PRODUCTION_REVIEWED_TRUSTED_LOCAL", "production_sealed": True,
                    "production_admitted": True, "assist_gateway": "FAKE_NO_MODEL_CALL", "starter": flow["source_run"], "comparison": result.json(),
                    "competing_recorded_intent_decisions": treatments, "business_rows_before": before,
                    "business_rows_after": business_rows(conn), "assist_roles": gateway.roles,
                    "production_fixture_pins": {key: value for key, value in config.TRUSTED_LOCAL_FIXTURES.items()
                                               if key.startswith("gtm_")}}
                with Path(proof_out).open("x", encoding="utf-8") as destination:
                    destination.write(json.dumps(proof, indent=2) + "\n")
        finally:
            conn.close()
