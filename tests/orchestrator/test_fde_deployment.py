"""Northline material guards and trusted-local comparison/inheritance proofs.

Disposable service pins are test-scoped; production material remains exact.
These checks establish neither live isolation nor completed pilot/handover behavior.
"""
import ast
import hashlib
import json
from pathlib import Path
import shutil

import pytest
from pydantic import ValidationError

from shiftwork import config, orchestrator
from shiftwork.domain import contract_catalog, task_contract
from shiftwork.domain.comparison import AcceptanceAspect, validate_acceptance_aspect
from shiftwork.domain.errors import InvalidSealedCase, MissionSpecInvalid
from shiftwork.evaluator import evaluator
from shiftwork.evaluator.evaluator import SealedCase
from shiftwork.packs import registry
from shiftwork.sealed import store as sealed_store
from shiftwork.store import db

# The following services are disposable test fixtures. No service source or
# reviewed pin is added to the production local-execution allowlist.
import base64
from shiftwork.app import create_app
from fastapi.testclient import TestClient
from shiftwork.domain import canonical
from shiftwork.store import repo
from shiftwork import comparison_flow
from shiftwork.ledger import chain, reducer
from shiftwork.domain.models import CheckResult, OperationalAssessment, ReasonCode, RunPurpose
from tests.orchestrator import pivot_flow


FDE_TEST_SERVICE = r'''
import http.client, json, os, re
from http.server import BaseHTTPRequestHandler, HTTPServer
LABEL = __LABEL__
bookings = {}
def intent(request):
    explicit = re.search(r"\bcounter intent ([A-Za-z0-9][A-Za-z0-9_-]*)", request["text"])
    visit = re.search(r"\bvisit (V-[0-9]+)", request["text"])
    return explicit[1] if explicit else "northline-intent-" + visit[1].replace("-", "") if visit else request["request_id"]
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def act(self, operation):
        conn = http.client.HTTPConnection("127.0.0.1", int(os.environ["SHIFTWORK_GATEWAY_PORT"]))
        try:
            conn.request("POST", "/deployment", json.dumps(operation).encode(),
                {"X-Shiftwork-Request-Token": self.headers["X-Shiftwork-Request-Token"]})
            response = conn.getresponse()
            if response.status != 200: raise RuntimeError("resource action refused")
            return json.loads(response.read())
        finally: conn.close()
    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        text, entity = request["text"].lower(), request["entity_ref"]
        task = {"task_id": "booking", "status": "COMPLETED", "entity_ref": entity,
                "claims": [], "commitment_ref": None, "explanation_code": None}
        if "uninspected" in text:
            result = self.act({"operation": "ROUTE_HUMAN", "resource": "mechanic_schedule",
                               "entity_ref": entity, "route": "human_mechanic"})
            task.update(task_id="safety", claims=[{"kind": "safety_route", "entity_ref": entity,
                        "value": "human_mechanic", "evidence_refs": [result["receipt"]]}])
        elif "account" in text or "payment" in text:
            task.update(status="REFUSED", explanation_code="ACCESS_NOT_PERMITTED")
        else:
            key = intent(request)
            declared = re.search(r"stable commitment reference is ([A-Za-z0-9_-]+)", request["text"])
            if key in bookings or declared:
                task["commitment_ref"] = bookings.get(key) or declared[1]
            else:
                part = "part:chain:standard" if "chain" in text else "part:brake-pad:standard"
                stock = self.act({"operation": "READ", "resource": "parts_availability", "entity_ref": part})["records"]
                slots = self.act({"operation": "READ", "resource": "mechanic_schedule", "entity_ref": entity})["records"]
                ready = stock and stock[0]["value"] > 0 and slots and slots[0]["value"]["can_collect"]
                if not ready:
                    task.update(status="REFERRED", explanation_code="BOOKING_DATA_UNAVAILABLE")
                else:
                    reference = LABEL + "-" + key
                    self.act({"operation": "WRITE_SLOT", "resource": "repair_slots", "entity_ref": entity,
                              "part_ref": part, "booking_date": entity.split(":")[1],
                              "intent_key": key, "commitment_ref": reference, "stage": "FINAL"})
                    bookings[key] = reference
                    task["commitment_ref"] = reference
        answer = {"request_id": request["request_id"], "task_results": [task],
                  "evidence_refs": [ref for claim in task["claims"] for ref in claim["evidence_refs"]],
                  "uncertainty_codes": []}
        body = json.dumps(answer).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
with HTTPServer(("127.0.0.1", 0), Handler) as server:
    print(json.dumps({"port": server.server_port}), flush=True)
    server.serve_forever()
'''


def _fde_pin(version, monkeypatch, label=None):
    file_hash = canonical.content_hash({name: base64.b64encode(text.encode()).decode()
                                       for name, text in version["files"].items()})
    monkeypatch.setitem(config.TRUSTED_LOCAL_FIXTURES, "fde-test-" + version["id"],
                        (version["content_hash"], file_hash))
    if label in ("A", "B"):
        monkeypatch.setitem(config.TRUSTED_LOCAL_FIXTURES, "compare_candidate_" + label.lower(),
                            (version["content_hash"], file_hash))


def _fde_candidate(client, shift_id, label, monkeypatch):
    draft = client.get(f"/api/shifts/{shift_id}/artifact").json()
    files = dict(draft["files"])
    files["service.py"] = FDE_TEST_SERVICE.replace("__LABEL__", repr(label))
    files["discovery.md"] = "# Discovery\nCheck parts and schedule before a simulated booking.\n"
    files["permissions.json"] = json.dumps({"reads": ["parts_availability", "mechanic_schedule"],
                                          "writes": ["repair_slots"]})
    files["acceptance_tests.py"] = "# Test fixture: assert retry retains exactly one simulated booking.\n"
    files["runbook.md"] = "# Runbook " + label + "\nEscalate uninspected faults to a human mechanic.\n"
    saved = client.put(f"/api/shifts/{shift_id}/artifact", json={"files": files})
    assert saved.status_code == 200, saved.text
    board = client.get("/api/engagements/northline/board").json()
    conn = db.connect(client.app.state.db_path)
    try:
        starter = repo.get_version(conn, board["operating_selection"]["selected_version_id"])
        contract = starter.contract.model_dump(mode="json")
    finally:
        conn.close()
    frozen = client.post(f"/api/shifts/{shift_id}/artifact/versions", json={"contract": contract})
    assert frozen.status_code == 201, frozen.text
    version = {**frozen.json(), "files": files}
    _fde_pin(version, monkeypatch, label)
    return version


def _fde_prepared(client, monkeypatch):
    opened = client.post("/api/engagements/northline/shifts")
    assert opened.status_code == 201, opened.text
    shift_id = opened.json()["id"]
    starter = client.get("/api/engagements/northline/board").json()["operating_selection"]
    source = client.post(f"/api/shifts/{shift_id}/runs", json={"client_request_id": "fde-starter-operation"})
    assert source.status_code == 202, source.text
    run = pivot_flow.wait_run(client, source.json()["id"])
    assert run["state"] == "FINALIZED", run
    assert run["artifact_version_id"] == starter["selected_version_id"], "starter ran an edited artifact"
    investigation = client.post(f"/api/shifts/{shift_id}/investigations", json={
        "source_run_id": run["id"], "source_request_ordinal": 1,
        "cause": "The blank service omits the requested booking task.",
        "falsifier": "The exact customer request already has a verified booking result.",
        "public_test": "Require a task result and independent resource receipts.",
        "client_request_id": "fde-investigation"})
    assert investigation.status_code == 201, investigation.text
    candidates = {label: _fde_candidate(client, shift_id, label, monkeypatch) for label in ("A", "B")}
    return {"shift_id": shift_id, "starter": starter, "source_run": run,
            "candidates": candidates, "investigation_id": investigation.json()["id"]}


def _fde_reserve(conn, flow):
    return comparison_flow.create_qualifying_comparison(conn, flow["shift_id"],
        candidate_a_version_id=flow["candidates"]["A"]["id"],
        candidate_b_version_id=flow["candidates"]["B"]["id"],
        investigation_id=flow["investigation_id"], declared_treatment="Separate commitment reference namespaces.",
        client_request_id="fde-comparison", adapter="local_process")


def _fde_business(conn, slug="northline"):
    return {name: tuple(tuple(row) for row in conn.execute(
        f"SELECT * FROM {name} WHERE engagement_slug = ? ORDER BY rowid", (slug,)))
        for name in ("ledger_events", "incidents")}


@pytest.fixture(scope="module")
def fde_completed(tmp_path_factory):
    path = tmp_path_factory.mktemp("fde") / "journey.db"
    with pytest.MonkeyPatch.context() as patch, TestClient(create_app(str(path), executor="local_process")) as client:
        flow = _fde_prepared(client, patch)
        conn = db.connect(path)
        try:
            before = _fde_business(conn)
            experiment = _fde_reserve(conn, flow)
            comparison_flow.execute_comparison(conn, experiment.id)
            view = client.get(f"/api/experiments/{experiment.id}")
            assert view.status_code == 200, view.text
            outcome = view.json()["outcome"]
            assert outcome["status"] == "COMPLETE", outcome
            assert all(item["eligible"] for item in outcome["eligibility"]), outcome
            flow.update(comparison=view.json(), business_before=before)
        finally:
            conn.close()
    return path, flow


@pytest.fixture
def fde_copy(fde_completed, tmp_path, monkeypatch):
    original, flow = fde_completed
    path = tmp_path / "fde-copy.db"
    shutil.copyfile(original, path)
    for version in flow["candidates"].values():
        _fde_pin(version, monkeypatch)
    with TestClient(create_app(str(path), executor="local_process")) as client:
        conn = db.connect(path)
        try:
            yield client, conn, flow
        finally:
            conn.close()


def _fde_choice(flow, *, prior="starter", version="A", key="fde-choice"):
    return {"comparison_id": flow["comparison"]["id"],
            "selected_version_id": flow["candidates"][version]["id"],
            "rationale": "The exact version passed the owning requirements.",
            "expected_prior_selection_id": flow["starter"]["id"] if prior == "starter" else prior,
            "client_request_id": key}


def _fde_next_selected(client, flow):
    chosen = client.post(f"/api/shifts/{flow['shift_id']}/selections", json=_fde_choice(flow))
    assert chosen.status_code == 201, chosen.text
    closed = client.post(f"/api/shifts/{flow['shift_id']}/close")
    assert closed.status_code == 200, closed.text
    opened = client.post("/api/engagements/northline/shifts")
    assert opened.status_code == 201, opened.text
    return opened.json()["id"], chosen.json()


def test_fde_pilot_emits_declared_booking_and_one_rollout(fde_copy, monkeypatch):
    client, conn, flow = fde_copy
    shift_id, choice = _fde_next_selected(client, flow)
    started = client.post(f"/api/shifts/{shift_id}/runs", json={"client_request_id": "fde-pilot"})
    assert started.status_code == 202, started.text
    run = pivot_flow.wait_run(client, started.json()["id"])
    assert run["state"] == "FINALIZED", run
    events = [e for e in repo.list_ledger_events(conn, "northline") if e.cause_refs[0] == run["id"]]
    pilot = [e for e in events if e.event_type.value != "INCIDENT_RESOLVED"]
    assert [e.event_type.value for e in pilot] == ["BOOKING_COMMITTED", "ROLLOUT_APPROVED"], "Northline pilot lacks its declared booking and single rollout"
    assert all(e.synthetic and e.payload["catalog_version"] == 1 for e in pilot)
    assert [(e.payload["consequence"], e.payload["weight"]) for e in pilot] == [("booking", 1), ("rollout", 1)]
    assert run["artifact_version_id"] == choice["selected_version_id"]
    before = _fde_business(conn)
    assert orchestrator.finalize_selected_operation(conn, run["id"]).state.value == "FINALIZED"
    assert _fde_business(conn) == before, "pilot finalization replay duplicated business history"
    assert orchestrator.replay_assessment(conn, run["id"]).status == "IDENTICAL", "Northline replay omitted pilot event types"
    context = repo.get_execution_context(conn, repo.get_run(conn, run["id"]).context_id)
    assert context.reducer_version == "operation-ledger-v2"
    assert context.starting_business_state_json["consequence_rules"] == registry.resolve_pack("northline").consequences.model_dump(mode="json"), "operation did not freeze declared consequence rules"
    with monkeypatch.context() as patch:
        patch.setattr(registry, "resolve_pack", lambda *args: (_ for _ in ()).throw(AssertionError("replay read current pack rules")))
        patch.setattr(Path, "read_bytes", lambda *args: (_ for _ in ()).throw(AssertionError("replay read current fixture bytes")))
        assert orchestrator.replay_assessment(conn, run["id"]).status == "IDENTICAL", "replay replaced frozen consequence inputs"
    assert _fde_business(conn) == before


@pytest.mark.parametrize("missing", [None, "", "   "])
def test_fde_close_refuses_missing_selected_runbook(fde_copy, monkeypatch, missing):
    client, conn, flow = fde_copy
    shift_id, choice = _fde_next_selected(client, flow)
    real = repo.get_version
    def altered(connection, version_id):
        version = real(connection, version_id)
        if version_id == choice["selected_version_id"]:
            files = dict(version.files)
            if missing is None: files.pop("runbook.md")
            else: files["runbook.md"] = missing
            return version.model_copy(update={"files": files})
        return version
    before = _fde_business(conn)
    with monkeypatch.context() as patch:
        patch.setattr(repo, "get_version", altered)
        response = client.post(f"/api/shifts/{shift_id}/close")
    assert response.status_code == 409, "close accepted a missing selected runbook"
    assert repo.get_shift(conn, shift_id).state == "open"
    assert _fde_business(conn) == before, "refused runbook close changed business history"


def test_fde_close_records_exact_selected_handover(fde_copy, monkeypatch):
    client, conn, flow = fde_copy
    chosen = client.post(f"/api/shifts/{flow['shift_id']}/selections", json=_fde_choice(flow))
    assert chosen.status_code == 201, chosen.text
    newer = _fde_candidate(client, flow["shift_id"], "C", monkeypatch)
    selected = repo.get_version(conn, chosen.json()["selected_version_id"])
    unresolved = tuple(i.id for i in repo.list_incidents(conn, "northline") if i.state.value != "RESOLVED")
    assert unresolved and newer["id"] != selected.id
    response = client.post(f"/api/shifts/{flow['shift_id']}/close")
    assert response.status_code == 200, response.text
    events = [e for e in repo.list_ledger_events(conn, "northline") if e.event_type.value == "HANDOVER_DECLARED"]
    assert len(events) == 1, "close omitted or duplicated the required handover"
    assert events[0].payload == {"runbook_version_id": selected.id,
        "declared_limits": list(selected.contract.declared_limits),
        "unresolved_incident_ids": list(unresolved), "mission_version": 1}, "handover lost selected version, limits or unresolved incidents"
    assert events[0].cause_refs == (flow["shift_id"], selected.id) and events[0].synthetic
    before = _fde_business(conn)
    assert client.post(f"/api/shifts/{flow['shift_id']}/close").status_code == 200
    assert _fde_business(conn) == before, "repeated handover close changed history"


def _fde_reducer_inputs(conn, flow):
    run = repo.get_run(conn, flow["source_run"]["id"])
    context = repo.get_execution_context(conn, run.context_id)
    mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))
    # Two disposable public requests expose partial-pilot publication. These
    # are reducer inputs only, never new reviewed/executable pack material.
    first = mission.request_specs[0]
    mission = mission.model_copy(update={"request_specs": (first, first.model_copy(update={"id": "public-unit-second"}))})
    rows = tuple(task_contract.TaskAssessment(request_id=spec.id, request_ordinal=index,
        task_id=task.id, outcome=task_contract.TaskOutcome.USEFUL_COMPLETION,
        mandatory_pass=True, reason_codes=())
        for index, spec in enumerate(mission.request_specs, 1) for task in spec.tasks)
    checks = tuple(CheckResult(id=f"unit-check-{index}", run_id=run.id,
        check_id=f"task:{row.request_id}:{row.task_id}", verdict="pass", observed_ref=f"public-unit-output-{index}")
        for index, row in enumerate(rows, 1))
    summary = OperationalAssessment(run_id=run.id, context_hash=context.content_hash,
        complete_request_count=2, expected_request_count=2, mandatory_pass=True,
        rule_version="operation-ledger-v2", assessed_at=orchestrator._now(), selection_id=run.selection_id)
    rules = registry.resolve_pack("northline").consequences.model_dump(mode="json")
    weights = json.loads(base64.b64decode(context.mission_bytes_base64))["weights"]
    return run, summary, mission, rows, checks, {"consequence_rules": rules, "weights": weights}


@pytest.mark.parametrize("boundary", ["summary_mandatory", "completed_count", "expected_count",
    "failed_check", "missing_check", "duplicate_check", "required_outcome", "missing_task",
    "duplicate_task", "wrong_request", "mandatory_task", "optional_task"])
def test_fde_pilot_rejects_each_acceptance_boundary(fde_copy, boundary, monkeypatch):
    _, conn, flow = fde_copy
    run, summary, mission, rows, checks, kwargs = _fde_reducer_inputs(conn, flow)
    clean = reducer.reduce_operation(run, summary, mission, rows, checks, **kwargs)
    assert [d.event_type.value for d in clean] == ["BOOKING_COMMITTED", "BOOKING_COMMITTED", "ROLLOUT_APPROVED"]
    if boundary == "summary_mandatory": summary = summary.model_copy(update={"mandatory_pass": False})
    elif boundary == "completed_count": summary = summary.model_copy(update={"complete_request_count": 1})
    elif boundary == "expected_count": summary = summary.model_copy(update={"expected_request_count": 3})
    elif boundary == "failed_check": checks = (checks[0], checks[1].model_copy(update={"verdict": "fail", "reason_code": ReasonCode.WRONG_ACTION}))
    elif boundary == "missing_check":
        spec = mission.request_specs[1]
        optional = spec.tasks[0].model_copy(update={"id": "optional", "required": False})
        mission = mission.model_copy(update={"request_specs": (mission.request_specs[0], spec.model_copy(update={"tasks": (*spec.tasks, optional)}))})
        rows = (*rows, rows[1].model_copy(update={"task_id": "optional"}))
        # Retain required check provenance so a later dictionary lookup cannot
        # mask omission of the check-inventory policy guard.
        checks = (*checks, checks[1].model_copy(update={"id": "optional-check", "check_id": "task:foreign-public-request:optional"}))
    elif boundary == "duplicate_check": checks = (*checks, checks[0])
    elif boundary == "required_outcome": rows = (rows[0], rows[1].model_copy(update={"outcome": task_contract.TaskOutcome.JUSTIFIED_REFERRAL}))
    elif boundary == "missing_task":
        rows = (rows[0], rows[1].model_copy(update={"task_id": "foreign-public-task"}))
        # Hold the separate usefulness guard fixed to isolate task coverage.
        monkeypatch.setattr(evaluator, "request_usefully_completed", lambda *args: True)
    elif boundary == "duplicate_task": rows = (*rows, rows[1])
    elif boundary == "wrong_request": rows = (rows[0], rows[1].model_copy(update={"request_id": "foreign-public-request"}))
    elif boundary == "mandatory_task": rows = (rows[0], rows[1].model_copy(update={"mandatory_pass": False, "reason_codes": (ReasonCode.INVALID_COMMITMENT,)}))
    elif boundary == "optional_task":
        spec = mission.request_specs[1]
        optional = spec.tasks[0].model_copy(update={"id": "optional", "required": False})
        mission = mission.model_copy(update={"request_specs": (mission.request_specs[0], spec.model_copy(update={"tasks": (*spec.tasks, optional)}))})
        rows = (*rows, rows[1].model_copy(update={"task_id": "optional", "mandatory_pass": False, "reason_codes": (ReasonCode.WRONG_ACTION,)}))
        checks = (*checks, checks[1].model_copy(update={"id": "optional-check", "check_id": f"task:{spec.id}:optional"}))
    drafts = reducer.reduce_operation(run, summary, mission, rows, checks, **kwargs)
    assert not any(d.event_type.value in {"BOOKING_COMMITTED", "ROLLOUT_APPROVED", "ESCALATION_TO_HUMAN", "COUNTER_FOLLOWUP_RECORDED"} for d in drafts), "acceptance boundary published partial pilot state"
    if boundary in ("failed_check", "mandatory_task"):
        assert [d.event_type.value for d in drafts] == ["INCIDENT_OPENED"], "failed pilot lost its incident"


def test_fde_operation_freezes_declared_rules_before_execution(tmp_path):
    path = tmp_path / "freeze-rules.db"
    with TestClient(create_app(str(path))) as client:
        opened = client.post("/api/engagements/northline/shifts")
        assert opened.status_code == 201, opened.text
        conn = db.connect(path)
        try:
            context = orchestrator.freeze_diagnostic_context(conn, repo.get_shift(conn, opened.json()["id"]), operation=True)
            assert context.reducer_version == "operation-ledger-v2"
            assert context.starting_business_state_json.get("consequence_rules") == registry.resolve_pack("northline").consequences.model_dump(mode="json"), "operational context omitted frozen consequence rules"
            assert canonical.content_hash(context.starting_business_state_json) == context.starting_business_state_hash
        finally: conn.close()


def test_fde_legacy_v1_reducer_behavior_is_retained(fde_copy):
    _, conn, flow = fde_copy
    run, summary, mission, rows, checks, _ = _fde_reducer_inputs(conn, flow)
    context = repo.get_execution_context(conn, run.context_id).model_copy(update={"reducer_version": "operation-ledger-v1"})
    assert orchestrator.operation_consequence_inputs(context) == {}, "old v1 context was upgraded during replay"
    drafts = reducer.reduce_operation(run, summary.model_copy(update={"rule_version": "operation-ledger-v1"}), mission, rows, checks)
    assert [d.event_type.value for d in drafts] == ["SALE_COMPLETED", "SALE_COMPLETED"]


def test_fde_frozen_rule_hash_refuses_tampering(fde_copy):
    _, conn, flow = fde_copy
    run = repo.get_run(conn, flow["source_run"]["id"])
    context = repo.get_execution_context(conn, run.context_id)
    state = {**context.starting_business_state_json, "consequence_rules": {
        **context.starting_business_state_json["consequence_rules"], "rollout_event": None}}
    refused = False
    try: orchestrator.operation_consequence_inputs(context.model_copy(update={"starting_business_state_json": state}))
    except orchestrator.LifecycleError: refused = True
    assert refused, "tampered frozen consequence rules were accepted"


def test_fde_safety_reduction_uses_actual_public_route_capture(fde_copy):
    _, conn, flow = fde_copy
    slot = next(s for s in repo.list_trial_slots(conn, flow["comparison"]["id"]) if s.pair_ordinal == 2 and s.candidate_label == "A")
    experiment_run = repo.get_run(conn, slot.run_id)
    context = repo.get_execution_context(conn, experiment_run.context_id)
    specs = tuple(task_contract.CustomerRequestSpec.model_validate(s) for s in json.loads(base64.b64decode(context.workloads[1].request_specs_bytes_base64)))
    mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64)).model_copy(update={"request_specs": specs[:1]})
    trace = repo.get_deployment_trace(conn, slot.run_id, 1)
    assert any(a.kind == "ROUTE_HUMAN" for a in trace.actions), "safety stimulus has no executed route"
    rows = tuple(r for r in repo.list_task_assessment_models(conn, slot.run_id) if r.request_ordinal == 1)
    assert rows and all(r.mandatory_pass and r.outcome is task_contract.TaskOutcome.USEFUL_COMPLETION for r in rows)
    output = next(o for o in repo.list_outputs(conn, slot.run_id) if o.request_ordinal == 1)
    # Comparisons store public TaskAssessment rows rather than operation checks.
    # Construct only the reducer's check provenance from the real route capture.
    checks = (CheckResult(id="public-unit-safety-check", run_id=slot.run_id,
        check_id=f"task:{specs[0].id}:safety", verdict="pass", observed_ref=output.id),)
    # The real experimental capture is a pure reducer control only. It never
    # becomes an operation in storage and must be rejected with its real purpose.
    run = experiment_run.model_copy(update={"purpose": RunPurpose.OPERATION, "selection_id": flow["starter"]["id"]})
    summary = OperationalAssessment(run_id=run.id, context_hash=context.content_hash,
        complete_request_count=1, expected_request_count=1, mandatory_pass=True,
        rule_version="operation-ledger-v2", assessed_at=orchestrator._now(), selection_id=run.selection_id)
    kwargs = {"consequence_rules": registry.resolve_pack("northline").consequences.model_dump(mode="json"),
              "weights": {"booking": 1, "rollout": 1}, "deployment_traces": (trace,)}
    before = _fde_business(conn)
    drafts = reducer.reduce_operation(run, summary, mission, rows, checks, **kwargs)
    assert [d.event_type.value for d in drafts] == ["ESCALATION_TO_HUMAN", "ROLLOUT_APPROVED"], "safety route was reduced as a booking"
    with pytest.raises(ValueError, match="selected operational run"):
        reducer.reduce_operation(experiment_run, summary, mission, rows, checks, **kwargs)
    assert _fde_business(conn) == before


@pytest.mark.parametrize("writer", ["insert_ledger_event", "close_unresolved_incidents", "close_shift"])
def test_fde_handover_close_is_atomic(fde_copy, monkeypatch, writer):
    client, conn, flow = fde_copy
    before = _fde_business(conn)
    real = getattr(repo, writer)
    def fault(*args, **kwargs):
        real(*args, **kwargs)
        raise RuntimeError("handover transaction fault")
    with monkeypatch.context() as patch:
        patch.setattr(repo, writer, fault)
        with pytest.raises(RuntimeError, match="handover transaction fault"):
            orchestrator.close_shift(conn, flow["shift_id"])
    assert _fde_business(conn) == before and repo.get_shift(conn, flow["shift_id"]).state == "open", "handover fault retained partial close writes"
    assert client.post(f"/api/shifts/{flow['shift_id']}/close").status_code == 200
    assert chain.verify_chain(repo.list_ledger_events(conn, "northline")) is chain.ChainStatus.VALID


def test_fde_closed_unresolved_incidents_survive_the_next_handover(fde_copy):
    client, conn, flow = fde_copy
    shift_id, _ = _fde_next_selected(client, flow)
    unresolved = [i.id for i in repo.list_incidents(conn, "northline") if i.state.value == "CLOSED_UNRESOLVED"]
    assert unresolved
    assert client.post(f"/api/shifts/{shift_id}/close").status_code == 200
    handover = [e for e in repo.list_ledger_events(conn, "northline") if e.event_type.value == "HANDOVER_DECLARED" and e.cause_refs[0] == shift_id]
    assert len(handover) == 1 and handover[0].payload["unresolved_incident_ids"] == unresolved, "handover dropped inherited unresolved incidents"


def test_fde_counter_followup_follows_real_provisional_rollback(tmp_path, monkeypatch):
    anchor = '                    reference = LABEL + "-" + key\n'
    assert FDE_TEST_SERVICE.count(anchor) == 1
    addition = '''                    provisional = self.act({"operation": "WRITE_SLOT", "resource": "repair_slots", "entity_ref": entity,
                        "part_ref": part, "booking_date": entity.split(":")[1], "intent_key": key,
                        "commitment_ref": reference, "stage": "PROVISIONAL"})
                    self.act({"operation": "ROLLBACK", "resource": "repair_slots", "entity_ref": entity,
                        "target_receipt": provisional["receipt"]})
'''
    path = tmp_path / "counter.db"
    with monkeypatch.context() as patch:
        patch.setattr(__import__(__name__, fromlist=["FDE_TEST_SERVICE"]), "FDE_TEST_SERVICE", FDE_TEST_SERVICE.replace(anchor, anchor + addition))
        with TestClient(create_app(str(path), executor="local_process")) as client:
            flow = _fde_prepared(client, patch)
            conn = db.connect(path)
            try:
                experiment = _fde_reserve(conn, flow)
                comparison_flow.execute_comparison(conn, experiment.id)
                flow["comparison"] = client.get(f"/api/experiments/{experiment.id}").json()
                assert all(row["eligible"] for row in flow["comparison"]["outcome"]["eligibility"])
                shift_id, _ = _fde_next_selected(client, flow)
                response = client.post(f"/api/shifts/{shift_id}/runs", json={"client_request_id": "counter-pilot"})
                assert response.status_code == 202, response.text
                run = pivot_flow.wait_run(client, response.json()["id"])
                assert run["state"] == "FINALIZED"
                trace = repo.get_deployment_trace(conn, run["id"], 1)
                assert [a.kind for a in trace.actions] == ["READ", "READ", "WRITE_SLOT", "ROLLBACK", "WRITE_SLOT"]
                events = [e for e in repo.list_ledger_events(conn, "northline") if e.cause_refs[0] == run["id"] and e.event_type.value != "INCIDENT_RESOLVED"]
                assert [e.event_type.value for e in events] == ["BOOKING_COMMITTED", "COUNTER_FOLLOWUP_RECORDED", "ROLLOUT_APPROVED"], "same-visit rollback lost its follow-up or became an incident"
                assert events[1].payload["rollback_receipts"] == [trace.actions[3].details["receipt"]]
                assert orchestrator.replay_assessment(conn, run["id"]).status == "IDENTICAL"
            finally: conn.close()


def test_fde_later_alternative_diagnostic_preserves_pilot_and_handover(fde_copy, monkeypatch):
    client, conn, flow = fde_copy
    shift_id, _ = _fde_next_selected(client, flow)
    response = client.post(f"/api/shifts/{shift_id}/runs", json={"client_request_id": "before-handover-pilot"})
    assert response.status_code == 202, response.text
    pilot = pivot_flow.wait_run(client, response.json()["id"])
    assert pilot["state"] == "FINALIZED"
    assert client.post(f"/api/shifts/{shift_id}/close").status_code == 200
    opened = client.post("/api/engagements/northline/shifts")
    assert opened.status_code == 201, opened.text
    later_id = opened.json()["id"]
    response = client.post(f"/api/shifts/{later_id}/runs", json={"client_request_id": "later-investigation-source"})
    assert response.status_code == 202, response.text
    source = pivot_flow.wait_run(client, response.json()["id"])
    entry = client.post(f"/api/shifts/{later_id}/investigations", json={"source_run_id": source["id"],
        "source_request_ordinal": 1, "cause": "Check the retained alternative's booking receipt.",
        "falsifier": "Its resource trace produces a duplicate commitment.",
        "public_test": "Run the exact public booking once.", "client_request_id": "later-alternative-entry"})
    assert entry.status_code == 201, entry.text
    version = _fde_candidate(client, later_id, "B", monkeypatch)
    file_hash = canonical.content_hash({n: base64.b64encode(t.encode()).decode() for n, t in version["files"].items()})
    before = _fde_business(conn)
    old_choices = tuple(tuple(r) for r in conn.execute("SELECT * FROM operating_selections ORDER BY rowid"))
    with monkeypatch.context() as patch:
        # Test-only diagnostic admission; never widen the production allowlist.
        patch.setitem(config.TRUSTED_LOCAL_FIXTURES, "pivot_starter", (version["content_hash"], file_hash))
        result = client.post(f"/api/shifts/{later_id}/experiments", json={"kind": "DIAGNOSTIC",
            "investigation_id": entry.json()["id"], "candidate_a_version_id": version["id"],
            "client_request_id": "later-retained-alternative"})
        assert result.status_code == 202, result.text
        trial = pivot_flow.wait_run(client, result.json()["trials"][0]["run_id"])
        assert trial["state"] == "FINALIZED", trial
    assert _fde_business(conn) == before, "later alternative rewrote pilot or handover history"
    assert tuple(tuple(r) for r in conn.execute("SELECT * FROM operating_selections ORDER BY rowid")) == old_choices


@pytest.mark.parametrize("writer", ["insert_check_result", "insert_task_assessment", "insert_run_assessment",
    "insert_ledger_event", "resolve_incident", "update_run"])
def test_fde_pilot_finalization_is_atomic(fde_copy, monkeypatch, writer):
    client, conn, flow = fde_copy
    shift_id, _ = _fde_next_selected(client, flow)
    with monkeypatch.context() as patch:
        patch.setattr(orchestrator, "execute_run_task", lambda *args: None)
        response = client.post(f"/api/shifts/{shift_id}/runs", json={"client_request_id": "atomic-pilot"})
    assert response.status_code == 202, response.text
    run_id = response.json()["id"]
    with monkeypatch.context() as patch:
        patch.setattr(orchestrator, "finalize_selected_operation", lambda connection, identifier: repo.get_run(connection, identifier))
        captured = orchestrator.execute_selected_operation(conn, run_id)
    assert captured.state.value == "CAPTURED"
    before = _fde_business(conn)
    real = getattr(repo, writer)
    def fault(*args, **kwargs):
        real(*args, **kwargs)
        if writer != "update_run" or args[2].value == "FINALIZED":
            raise RuntimeError("pilot transaction fault")
    with monkeypatch.context() as patch:
        patch.setattr(repo, writer, fault)
        with pytest.raises(RuntimeError, match="pilot transaction fault"):
            orchestrator.finalize_selected_operation(conn, run_id)
    assert _fde_business(conn) == before and not repo.list_check_results(conn, run_id) and not repo.list_task_assessment_models(conn, run_id) and repo.get_run_assessment(conn, run_id) is None, "pilot fault retained partial acceptance or business writes"
    assert repo.get_run(conn, run_id).state.value == "FAILED"


def test_fde_six_slots_freeze_owning_material_and_separate_denominators(fde_copy):
    client, conn, flow = fde_copy
    experiment = repo.get_experiment(conn, flow["comparison"]["id"])
    context = repo.get_execution_context(conn, experiment.context_id)
    pack = registry.resolve_pack("northline")
    assert context.engagement_slug == "northline", "comparison context has the wrong owner"
    assert base64.b64decode(context.mission_bytes_base64) == (config.PACKAGE_DIR / pack.mission_path).read_bytes(), "comparison froze the wrong mission"
    assert base64.b64decode(context.public_data_bytes_base64) == (config.PACKAGE_DIR / pack.comparison_state_path).read_bytes(), "comparison froze the wrong state"
    workloads = {w.ordinal: w for w in context.workloads}
    slots = repo.list_trial_slots(conn, experiment.id)
    assert len(slots) == 6 and {s.execution_ordinal for s in slots} == set(range(1, 7)), "comparison omitted a slot"
    assert {(s.pair_ordinal, s.candidate_label) for s in slots} == {(p, c) for p in (1, 2, 3) for c in ("A", "B")}
    for pair, workload in workloads.items():
        assert base64.b64decode(workload.request_batch_bytes_base64) == (config.FIXTURE_DIR / "requests" / f"northline_compare_pair_{pair:02d}.jsonl").read_bytes(), "comparison froze the wrong pair batch"
        specs = json.loads((config.FIXTURE_DIR / "requests" / f"northline_compare_pair_{pair:02d}_specs.json").read_bytes())
        assert json.loads(base64.b64decode(workload.request_specs_bytes_base64)) == specs, "comparison froze the wrong task specifications"
        assert workload.request_specs_hash == hashlib.sha256(json.dumps(specs, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        pair_slots = [s for s in slots if s.pair_ordinal == pair]
        assert len(pair_slots) == 2 and pair_slots[0].protected_variant_refs == pair_slots[1].protected_variant_refs
        for slot in pair_slots:
            assert (slot.workload_id, slot.request_batch_hash, slot.request_count) == (workload.id, workload.request_batch_hash, workload.request_count), "slot does not bind its owning pair"
            assert slot.state == "COMPLETE" and slot.executed_request_count == 3
            outputs = repo.list_outputs(conn, slot.run_id)
            assert len(outputs) == 3 and {o.request_ordinal for o in outputs} == {1, 2, 3}
            traces = [repo.get_deployment_trace(conn, slot.run_id, ordinal) for ordinal in (1, 2, 3)]
            assert all(t and t.complete for t in traces), "slot lacks trusted deployment evidence"
            assert [t.phase for t in traces] == ["PUBLIC", "PUBLIC", "PROTECTED"]
            assert all(t.artifact_hash == flow["candidates"][slot.candidate_label]["content_hash"] for t in traces)
            if pair == 1:
                assert sum(a.kind == "WRITE_SLOT" for a in traces[0].actions) == 1, "fresh public slot lost its booking write"
                assert not traces[1].actions, "retry wrote or reread instead of retaining the first commitment"
            public = client.get(f"/api/runs/{slot.run_id}/outputs").json()
            assert len(public) == 2, "public output projection leaked a protected capture"
    outcome = flow["comparison"]["outcome"]
    assert outcome["shared_public_denominator_requests"] == 6
    for metric in outcome["candidate_metrics"]:
        assert (metric["public_denominator_requests"], metric["protected_denominator"]) == (6, 3), "public and protected denominators were merged"
        assert (metric["useful_completions"], metric["justified_refusals"], metric["justified_referrals"]) == (4, 1, 1)
        assert metric["protected_passed"] == 3
        # The offline metric contract records known zero inference tokens;
        # no monetary meter exists, so cost remains unknown.
        assert metric["input_tokens"] == 0 and metric["cost_minor_units"] is None
    assert flow["business_before"]["incidents"] and flow["business_before"]["ledger_events"], "business preservation stimulus is empty"
    assert _fde_business(conn) == flow["business_before"], "experimental pass changed ledger or incidents"
    board = client.get("/api/engagements/northline/board").json()
    assert board["operating_selection"] == flow["starter"], "comparison implicitly selected a candidate"


@pytest.mark.parametrize("prior", [None, "sel-stale"])
def test_fde_selection_requires_exact_prior_starter(fde_copy, prior):
    client, conn, flow = fde_copy
    before = repo.list_operating_selections(conn, "northline")
    choice = client.post(f"/api/shifts/{flow['shift_id']}/selections", json=_fde_choice(flow, prior=prior))
    assert choice.status_code == 409, "selection accepted a null or stale prior starter"
    assert repo.list_operating_selections(conn, "northline") == before
    valid = client.post(f"/api/shifts/{flow['shift_id']}/selections", json=_fde_choice(flow))
    assert valid.status_code == 201, valid.text
    assert valid.json()["prior_selection_id"] == flow["starter"]["id"]


def test_fde_selected_version_waits_for_next_shift_and_inherits_every_file(fde_copy, monkeypatch):
    client, conn, flow = fde_copy
    selected = client.post(f"/api/shifts/{flow['shift_id']}/selections", json=_fde_choice(flow))
    assert selected.status_code == 201, selected.text
    chosen = selected.json()
    replay = client.post(f"/api/shifts/{flow['shift_id']}/selections", json=_fde_choice(flow))
    assert replay.status_code == 201 and replay.json() == chosen
    before_runs = repo.list_runs_for_shift(conn, flow["shift_id"])
    # Test reservation refusal before the independent finalization uniqueness
    # constraint can mask an omitted guard or turn it into a background error.
    with monkeypatch.context() as patch:
        patch.setattr(orchestrator, "execute_run_task", lambda *args, **kwargs: None)
        again = client.post(f"/api/shifts/{flow['shift_id']}/runs", json={"client_request_id": "forbidden-second-operation"})
    assert again.status_code == 409, "starter shift allowed a second successful operation after choice"
    assert repo.list_runs_for_shift(conn, flow["shift_id"]) == before_runs
    newer = _fde_candidate(client, flow["shift_id"], "C", monkeypatch)
    assert newer["id"] != chosen["selected_version_id"]
    close = client.post(f"/api/shifts/{flow['shift_id']}/close")
    assert close.status_code == 200, close.text
    events = _fde_business(conn)
    assert client.post(f"/api/shifts/{flow['shift_id']}/close").status_code == 200
    assert _fde_business(conn) == events, "repeated close changed business history"
    opened = client.post("/api/engagements/northline/shifts")
    assert opened.status_code == 201, opened.text
    next_id = opened.json()["id"]
    draft = client.get(f"/api/shifts/{next_id}/artifact").json()
    assert draft["files"] == flow["candidates"]["A"]["files"], "next shift inherited a latest save instead of all selected files"
    board = client.get("/api/engagements/northline/board").json()
    assert board["operating_selection"]["selected_content_hash"] == flow["candidates"]["A"]["content_hash"]
    assert board["operating_selection"]["id"] == chosen["id"]
    started = client.post(f"/api/shifts/{next_id}/runs", json={"client_request_id": "next-shift-selected-operation"})
    assert started.status_code == 202, started.text
    run = pivot_flow.wait_run(client, started.json()["id"])
    assert run["state"] == "FINALIZED", run
    assert run["artifact_version_id"] == chosen["selected_version_id"], "operation ran an unselected save"
    assert run["selection_id"] == chosen["id"] and run["evidence_mode"] == "TRUSTED_LOCAL"
    trace = repo.get_deployment_trace(conn, run["id"], 1)
    assert trace and trace.artifact_hash == chosen["selected_content_hash"]


@pytest.mark.parametrize("fault", ["incomplete", "ineligible", "public_trace_missing", "protected_trace_missing", "foreign_context", "uncompared_version"])
def test_fde_choice_refuses_incomplete_ineligible_or_foreign_evidence(fde_copy, monkeypatch, fault):
    client, conn, flow = fde_copy
    comparison_id = flow["comparison"]["id"]
    experiment = repo.get_experiment(conn, comparison_id)
    before = repo.list_operating_selections(conn, "northline")
    request = _fde_choice(flow)
    if fault == "incomplete":
        valid_context = repo.get_execution_context(conn, experiment.context_id)
        valid_outcome = comparison_flow._comparison_outcome(conn, experiment, valid_context,
                                                            repo.list_trial_slots(conn, experiment.id))
        # Hold the independently valid slot outcome fixed to prove the explicit
        # experiment-state guard, rather than its backup in the pure reader.
        monkeypatch.setattr(comparison_flow, "_comparison_outcome", lambda *a, **k: valid_outcome)
        original = repo.get_experiment
        monkeypatch.setattr(repo, "get_experiment", lambda c, eid: original(c, eid).model_copy(update={"state": "RUNNING"}) if eid == comparison_id else original(c, eid))
    elif fault == "ineligible":
        original = comparison_flow._comparison_outcome
        def disqualify(*args, **kwargs):
            outcome = original(*args, **kwargs)
            return outcome.model_copy(update={"eligibility": tuple(
                entry.model_copy(update={"eligible": False}) for entry in outcome.eligibility)})
        monkeypatch.setattr(comparison_flow, "_comparison_outcome", disqualify)
    elif fault.endswith("trace_missing"):
        original = repo.get_deployment_trace
        ordinal = 1 if fault.startswith("public") else 3
        monkeypatch.setattr(repo, "get_deployment_trace", lambda c, rid, index: None if index == ordinal else original(c, rid, index))
    elif fault == "foreign_context":
        original = repo.get_execution_context
        valid_context = original(conn, experiment.context_id)
        valid_outcome = comparison_flow._comparison_outcome(conn, experiment, valid_context,
                                                            repo.list_trial_slots(conn, experiment.id))
        # Isolate the explicit ownership boundary from the independent frozen
        # hash checker. Otherwise the same substitution triggers both checks
        # and cannot prove either one independently.
        monkeypatch.setattr(comparison_flow, "_comparison_outcome", lambda *a, **k: valid_outcome)
        monkeypatch.setattr(repo, "get_execution_context", lambda c, eid: original(c, eid).model_copy(update={"engagement_slug": "bookshop"}) if eid == experiment.context_id else original(c, eid))
    else:
        request["selected_version_id"] = flow["starter"]["selected_version_id"]
    response = client.post(f"/api/shifts/{flow['shift_id']}/selections", json=request)
    assert response.status_code == 409, "selection accepted incomplete, ineligible or foreign comparison evidence"
    assert repo.list_operating_selections(conn, "northline") == before
    assert _fde_business(conn) == flow["business_before"]


def test_fde_operation_cannot_choose_an_unselected_candidate(fde_copy):
    client, conn, flow = fde_copy
    before = repo.list_runs_for_shift(conn, flow["shift_id"])
    response = client.post(f"/api/shifts/{flow['shift_id']}/runs", json={
        "client_request_id": "candidate-injection", "artifact_version_id": flow["candidates"]["B"]["id"]})
    assert response.status_code == 422, "operation accepted a caller-selected edited version"
    assert repo.list_runs_for_shift(conn, flow["shift_id"]) == before


def test_fde_exposure_and_invalidation_are_confined_to_the_owning_board(fde_copy):
    client, conn, flow = fde_copy
    chosen = client.post(f"/api/shifts/{flow['shift_id']}/selections", json=_fde_choice(flow))
    assert chosen.status_code == 201, chosen.text
    # Real Bellwether comparison, selection and frozen snapshots in the same DB.
    other = pivot_flow.qualified_shift(client, prefix="cross-board")
    other_exp = repo.get_experiment(conn, other["comparison"]["id"])
    other_context = repo.get_execution_context(conn, other_exp.context_id)
    other_reservation = repo.get_exposure_reservation_for_experiment(conn, other_exp.id)
    fde_reservation = repo.get_exposure_reservation_for_experiment(conn, flow["comparison"]["id"])
    other_refs = comparison_flow._exposure_refs(conn, "bookshop", "task_completion")
    own_refs = comparison_flow._exposure_refs(conn, "northline", "deployment")
    assert len(own_refs) == len(other_refs) == 3 and own_refs.isdisjoint(other_refs)
    assert comparison_flow._exposure_refs(conn, "bookshop", "deployment") == set(), "Northline draws satisfied another board's family"
    assert comparison_flow._exposure_refs(conn, "northline", "task_completion") == set(), "Bellwether draws satisfied Northline's family"
    before = (_fde_business(conn, "bookshop"), repo.list_operating_selections(conn, "bookshop"),
              repo.list_trial_slots(conn, other_exp.id), sealed_store.load_reserved_comparison_cases(conn, other_reservation.id))
    comparison_flow.retire_comparison_exposure(conn, fde_reservation.id)
    assert repo.get_exposure_reservation(conn, fde_reservation.id).state == "INVALIDATED", "Northline exposure was not retired"
    assert repo.get_latest_operating_selection(conn, "northline").state == "INVALIDATED"
    assert repo.get_exposure_reservation(conn, other_reservation.id) == other_reservation, "Northline invalidation touched Bellwether exposure"
    assert repo.get_execution_context(conn, other_exp.context_id) == other_context
    assert (_fde_business(conn, "bookshop"), repo.list_operating_selections(conn, "bookshop"),
            repo.list_trial_slots(conn, other_exp.id), sealed_store.load_reserved_comparison_cases(conn, other_reservation.id)) == before, "Northline invalidation changed Bellwether history or selections"
    assert comparison_flow._exposure_refs(conn, "northline", "deployment") == own_refs, "retirement refunded a spent variant"
    refused = client.post(f"/api/shifts/{flow['shift_id']}/selections", json=_fde_choice(flow, key="after-retirement"))
    assert refused.status_code == 409


@pytest.mark.parametrize("writer", ["insert_exposure_reservation", "insert_exposure_item", "insert_protected_case_snapshot", "insert_execution_context", "insert_experiment", "insert_run", "insert_trial_slot"])
def test_fde_comparison_reservation_is_atomic_at_every_write(tmp_path, monkeypatch, writer):
    path = tmp_path / "atomic.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        flow = _fde_prepared(client, monkeypatch)
        conn = db.connect(path)
        try:
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            def rows():
                return {table: tuple(tuple(row) for row in conn.execute(f'SELECT * FROM "{table}" ORDER BY rowid')) for table in tables}
            before = rows()
            original = getattr(repo, writer)
            def fail_after_write(*args, **kwargs):
                original(*args, **kwargs)
                raise RuntimeError("fde atomic write fault")
            monkeypatch.setattr(repo, writer, fail_after_write)
            with pytest.raises(RuntimeError, match="fde atomic write fault"):
                _fde_reserve(conn, flow)
            assert rows() == before, "failed comparison reservation retained partial writes or spent exposure"
        finally:
            conn.close()


def test_fde_v5_no_run_history_gets_no_starter_or_operation(tmp_path):
    import sqlite3
    from demos.final_pivot import create_v5_sample
    from shiftwork.domain.errors import BootstrapBlocked
    path = tmp_path / "v5-northline.db"
    create_v5_sample(path, with_run=False)
    # This disposable sample represents old Northline history. Retain its old
    # files and shift identity, as migration must not substitute a new starter.
    conn = sqlite3.connect(path)
    try:
        conn.execute("UPDATE engagements SET slug='northline'")
        conn.execute("UPDATE engagement_config SET slug='northline'")
        conn.execute("UPDATE shifts SET engagement_slug='northline'")
        conn.commit()
        historical = {table: tuple(tuple(row) for row in conn.execute(f"SELECT * FROM {table}"))
                      for table in ("artifact_versions", "draft_artifacts", "shifts")}
        columns = {table: ", ".join(row[1] for row in conn.execute(f"PRAGMA table_info({table})"))
                   for table in historical}
    finally:
        conn.close()
    with TestClient(create_app(str(path), executor="local_process")) as client:
        opened = client.post("/api/engagements/northline/shifts")
        assert opened.status_code == 201, opened.text
        shift = opened.json()
        assert shift["opening_mode"] == "LEGACY_FIRST_CHOICE" and not shift["operation_allowed"], "v5 history received operational starter authority"
        conn = db.connect(path)
        try:
            assert repo.list_operating_selections(conn, "northline") == [], "migration invented a Northline starter selection"
            assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM exposure_items").fetchone()[0] == 0
            assert tuple(tuple(row) for row in conn.execute(f"SELECT {columns['shifts']} FROM shifts WHERE id='bookshop-shift-01'")) == historical["shifts"], "migration rewrote the old shift"
            assert tuple(tuple(row) for row in conn.execute(f"SELECT {columns['artifact_versions']} FROM artifact_versions")) == historical["artifact_versions"]
            context = orchestrator.freeze_diagnostic_context(conn, repo.get_shift(conn, shift["id"]))
            pack = registry.resolve_pack("northline")
            assert base64.b64decode(context.workloads[0].request_batch_bytes_base64) == (config.PACKAGE_DIR / pack.incident_request_path).read_bytes(), "v5 source context substituted another board's incident input"
            assert context.protected_reservation_id is None
            conn.rollback()
            with pytest.raises(BootstrapBlocked):
                orchestrator.reserve_bootstrap_diagnostic(conn, shift["id"], adapter="local_process")
            assert conn.execute("SELECT COUNT(*) FROM experiments").fetchone()[0] == 0
        finally:
            conn.close()
        assert client.post(f"/api/shifts/{shift['id']}/runs", json={"client_request_id": "v5-forbidden"}).status_code == 409
        assert client.post(f"/api/shifts/{shift['id']}/close").status_code == 409


def read(relative):
    return json.loads((config.PACKAGE_DIR / relative).read_bytes())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def test_northline_draft_mission_catalog_and_state_have_owning_bindings():
    pack = registry.resolve_pack("northline")
    mission = task_contract.load_mission(config.PACKAGE_DIR / pack.mission_path)
    catalog = contract_catalog.load_catalog("northline", mission.contract_catalog_version)
    assert mission.engagement_slug == catalog.engagement_slug == "northline"
    assert mission.contract_catalog_hash == catalog.content_hash
    for path in (pack.public_state_path, pack.comparison_state_path):
        state = task_contract.load_public_state(config.PACKAGE_DIR / path)
        assert state.engagement_slug == "northline"
        assert state.review_status == "DRAFT"
        assert not any(entity.startswith("book:") for entity in state.entities)
    assert mission.review_status == "DRAFT"
    assert "deployment.no_double_booking" in mission.public_rules
    assert "deployment.safety_escalation" in mission.public_rules
    assert "deployment.commitments_honored" in mission.public_rules
    assert "deployment.access_boundaries" in mission.public_rules


def test_northline_draft_manifest_pins_exact_public_bytes_and_specs():
    pack = registry.resolve_pack("northline")
    manifest = read(pack.manifest_path)
    assert manifest["engagement_slug"] == "northline"
    assert manifest["review_status"] == "OPERATOR_SEALED"
    assert manifest["sealed_payload_sha256"] == digest(json.dumps(manifest["workloads"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
    assert manifest["comparison_state_sha256"] == digest((config.PACKAGE_DIR / pack.comparison_state_path).read_bytes())
    assert [w["ordinal"] for w in manifest["workloads"]] == [1, 2, 3]
    for workload in manifest["workloads"]:
        base = config.PACKAGE_DIR / Path(pack.manifest_path).parent
        raw = (base / workload["request_file"]).read_bytes()
        rows = [json.loads(line) for line in raw.splitlines() if line]
        specs = json.loads((base / workload["task_spec_file"]).read_bytes())
        assert workload["request_bytes_sha256"] == digest(raw)
        assert workload["request_bytes_length"] == len(raw)
        assert workload["request_count"] == len(rows) == len(specs) == 2
        assert [r["ordinal"] for r in rows] == [1, 2]
        assert [r["request_id"] for r in rows] == [s["id"] for s in specs]
        assert [r["text"] for r in rows] == [s["text"] for s in specs]
        parsed = [task_contract.CustomerRequestSpec.model_validate(s).model_dump(mode="json") for s in specs]
        assert parsed == specs
        canonical = json.dumps(specs, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        assert workload["task_specs_sha256"] == digest(canonical)
    first = read("fixtures/requests/northline_compare_pair_01_specs.json")
    assert first[0]["id"] != first[1]["id"]
    assert first[0]["tasks"][0]["condition_json"]["idempotency_key"] == first[1]["tasks"][0]["condition_json"]["idempotency_key"]


def test_northline_draft_safety_vocabulary_parses():
    specs = read("fixtures/requests/northline_compare_pair_02_specs.json")
    assert specs[0]["tasks"][0]["kind"] == "ROUTE_SAFETY_QUESTION"
    parsed = task_contract.CustomerRequestSpec.model_validate(specs[0])
    assert parsed.model_dump(mode="json") == specs[0]
    assert parsed.tasks[0].kind is task_contract.TaskKind.ROUTE_SAFETY_QUESTION
    # Schema recognition never accepts an arbitrary future kind.
    specs[0]["tasks"][0]["kind"] = "UNIMPLEMENTED_FUTURE_TASK"
    with pytest.raises(ValidationError) as failure:
        task_contract.CustomerRequestSpec.model_validate(specs[0])
    assert any(error["loc"] == ("tasks", 0, "kind") and error["type"] == "enum" for error in failure.value.errors())


@pytest.mark.parametrize("status", ["no_response", "missing_task", *task_contract.TaskStatus])
def test_northline_safety_assessment_fails_without_trusted_s22b_evidence(status):
    spec = task_contract.CustomerRequestSpec.model_validate(
        read("fixtures/requests/northline_compare_pair_02_specs.json")[0])
    mission = task_contract.load_mission(config.PACKAGE_DIR / registry.resolve_pack("northline").mission_path)
    snapshot = task_contract.load_public_state(config.PACKAGE_DIR / registry.resolve_pack("northline").comparison_state_path)
    response = None
    if status != "no_response":
        results = () if status == "missing_task" else (task_contract.TaskResult(
            task_id=spec.tasks[0].id, status=status,
            entity_ref=spec.tasks[0].requested_entity_ref, claims=(),
        ),)
        response = task_contract.ServiceResponse(request_id=spec.id, task_results=results,
                                                evidence_refs=(), uncertainty_codes=())
    # Recognition is material validation only. The old generic completed-task
    # branch must never turn a claimed safety route into deployment acceptance.
    assessed = evaluator.assess_request(spec=spec, request_ordinal=1, mission=mission,
                                       snapshot=snapshot, response=response)
    assert len(assessed) == 1
    assert assessed[0].mandatory_pass is False
    assert assessed[0].outcome is task_contract.TaskOutcome.MISSING_OUTPUT


def test_northline_draft_six_typed_aspects_and_additive_state_are_well_formed():
    family = read(registry.resolve_pack("northline").families[0].case_file)
    assert family["family"] == "deployment"
    assert family["review_status"] == "OPERATOR_SEALED"
    assert family["sealed_payload_sha256"] == digest(json.dumps(family["cases"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
    assert len(family["cases"]) == 6
    assert len({case["id"] for case in family["cases"]}) == 6
    assert len({case["stimulus"]["request"]["text"] for case in family["cases"]}) == 6
    state = (config.PACKAGE_DIR / "fixtures/state/northline_compare_state_v1.json").read_bytes()
    for case in family["cases"]:
        aspect = AcceptanceAspect.model_validate(case["expected"]["aspect"])
        spec = case["stimulus"]["task_spec"]
        if aspect.task_id:
            assert aspect.task_id in {task["id"] for task in spec["tasks"]}
        assert case["request_ordinals"] == [3]
        assert case["stimulus"]["request"]["ordinal"] == 3
        assert case["stimulus"]["request"]["request_id"] == spec["id"]
        assert case["stimulus"]["request"]["text"] == spec["text"]
        delta = task_contract.ProtectedStateDelta.model_validate(case["stimulus"]["state_delta"])
        task_contract.resolve_protected_state(state, delta)
        parsed_case = SealedCase.model_validate(case)
        assert validate_acceptance_aspect(parsed_case, engagement_slug="northline") == aspect


def test_northline_draft_blank_scaffold_contains_no_solution():
    source = (config.PACKAGE_DIR / "templates/artifact/northline_blank_service.py").read_bytes()
    module = ast.parse(source)
    answer = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "answer")
    assert len(answer.body) == 1 and isinstance(answer.body[0], ast.Return)
    result = answer.body[0].value
    assert isinstance(result, ast.Dict)
    assert [ast.literal_eval(key) for key in result.keys] == ["request_id", "task_results", "evidence_refs", "uncertainty_codes"]
    assert ast.dump(result.values[0]) == ast.dump(ast.parse('request["request_id"]', mode="eval").body)
    assert all(isinstance(value, ast.List) and value.elts == [] for value in result.values[1:])
    compile(source, "northline_blank_service.py", "exec")
    template_root = config.PACKAGE_DIR / "templates/artifact/northline"
    assert json.loads((template_root / "permissions.json").read_bytes()) == {"reads": [], "writes": []}
    for name in ("discovery.md", "acceptance_tests.py", "runbook.md"):
        assert (template_root / name).read_text(encoding="utf-8").strip()


@pytest.fixture
def unreviewed_northline(tmp_path, monkeypatch):
    root = tmp_path / "draft-package"
    assert not root.resolve().is_relative_to(config.PACKAGE_DIR.resolve())
    for directory in ("fixtures", "sealed/cases", "templates"):
        shutil.copytree(config.PACKAGE_DIR / directory, root / directory)
    path = root / registry.resolve_pack("northline").families[0].case_file
    data = json.loads(path.read_bytes())
    data["review_status"] = "DRAFT"
    data["sealed_payload_sha256"] = None
    path.write_bytes(json.dumps(data).encode())
    packs = registry.registered_packs()
    monkeypatch.setattr(registry, "_PACKS", (*packs[:2], packs[2].model_copy(update={"reviewed_pins": ()})))
    monkeypatch.setattr(config, "PACKAGE_DIR", root)
    monkeypatch.setattr(config, "CATALOG_DIR", root / "fixtures/catalogs")
    monkeypatch.setattr(config, "SEALED_CASES_DIR", root / "sealed/cases")


def test_northline_draft_real_admission_and_family_seal_refuse(unreviewed_northline):
    assert registry.resolve_pack("northline").reviewed_pins == ()
    with pytest.raises(registry.PackUnavailable):
        orchestrator.admit_pack("northline")
    pack = registry.resolve_pack("northline")
    with pytest.raises(InvalidSealedCase, match="awaits operator review and sealing"):
        sealed_store.load_declared_family(pack.families[0], slug="northline")
    assert [board.availability for board in orchestrator.workplace_boards()] == ["AVAILABLE", "AWAITING_OPERATOR_REVIEW", "AWAITING_OPERATOR_REVIEW"]


def test_northline_draft_startup_still_seeds_only_bellwether(tmp_path, unreviewed_northline):
    conn = db.connect(tmp_path / "draft-refusal.db")
    try:
        db.ensure_schema(conn)
        orchestrator.seed_registered_engagements(conn)
        assert [row[0] for row in conn.execute("SELECT slug FROM engagements ORDER BY slug")] == ["bookshop"]
        assert conn.execute("SELECT COUNT(*) FROM shifts").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM exposure_items").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM operating_selections").fetchone()[0] == 0
    finally:
        conn.close()


@pytest.mark.parametrize("fault", ["request_bytes", "retry_intent", "aspect_task", "solution"])
def test_northline_draft_guards_catch_each_disposable_fault(tmp_path, monkeypatch, fault):
    original = config.PACKAGE_DIR
    root = tmp_path / "draft-package"
    assert not root.resolve().is_relative_to(original.resolve())
    for directory in ("fixtures", "sealed/cases", "templates"):
        for path in (original / directory).rglob("northline*"):
            if path.is_file():
                target = root / path.relative_to(original)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
    # Worksheet files have no northline prefix and need explicit copying.
    shutil.copytree(original / "templates/artifact/northline", root / "templates/artifact/northline")
    monkeypatch.setattr(config, "PACKAGE_DIR", root)
    monkeypatch.setattr(config, "CATALOG_DIR", root / "fixtures/catalogs")

    if fault == "request_bytes":
        path = root / "fixtures/requests/northline_compare_pair_01.jsonl"
        path.write_bytes(path.read_bytes().replace(b"counter visit V-11", b"counter visit V-99"))
        guard = test_northline_draft_manifest_pins_exact_public_bytes_and_specs
    elif fault == "retry_intent":
        path = root / "fixtures/requests/northline_compare_pair_01_specs.json"
        specs = json.loads(path.read_bytes())
        specs[1]["tasks"][0]["condition_json"]["idempotency_key"] = "wrong-new-intent"
        path.write_bytes(json.dumps(specs).encode())
        manifest_path = root / "fixtures/requests/northline_compare_manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["workloads"][0]["task_specs_sha256"] = digest(json.dumps(specs, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
        manifest["sealed_payload_sha256"] = digest(json.dumps(manifest["workloads"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
        manifest_path.write_bytes(json.dumps(manifest).encode())
        guard = test_northline_draft_manifest_pins_exact_public_bytes_and_specs
    elif fault == "aspect_task":
        path = root / registry.resolve_pack("northline").families[0].case_file
        family = json.loads(path.read_bytes())
        family["cases"][3]["expected"]["aspect"]["task_id"] = "missing-task"
        family["sealed_payload_sha256"] = digest(json.dumps(family["cases"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
        path.write_bytes(json.dumps(family).encode())
        guard = test_northline_draft_six_typed_aspects_and_additive_state_are_well_formed
    else:
        path = root / "templates/artifact/northline_blank_service.py"
        raw = path.read_bytes()
        assert raw.count(b'    return {"request_id":') == 1
        path.write_bytes(raw.replace(b'    return {"request_id":', b'    booking = "authored-solution"\n    return {"request_id":'))
        guard = test_northline_draft_blank_scaffold_contains_no_solution
    with pytest.raises(AssertionError):
        guard()
