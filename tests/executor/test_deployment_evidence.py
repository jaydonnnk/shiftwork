"""Independent simulated-action proofs. These are offline kernel/receipt checks."""

import asyncio
import base64
import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain import canonical, task_contract as tc
from shiftwork.domain.models import ReasonCode
from shiftwork.evaluator import evaluator
from shiftwork.executor import base
from shiftwork.executor.deployment import DeploymentKernel, derive_intent_key
from shiftwork.executor.local_process import LocalProcessAdapter
from shiftwork.packs import registry
from shiftwork.store import db, repo


def material(pair=1):
    pack = registry.resolve_pack("northline")
    raw = (config.PACKAGE_DIR / pack.comparison_state_path).read_bytes()
    specs = tuple(tc.CustomerRequestSpec.model_validate(s) for s in json.loads(
        (config.FIXTURE_DIR / "requests" / f"northline_compare_pair_{pair:02d}_specs.json").read_bytes()))
    mission = tc.load_mission(config.PACKAGE_DIR / pack.mission_path)
    return raw, tc.load_public_state_bytes(raw), specs, mission


def kernel(raw):
    return DeploymentKernel(raw, {"run_id": "unit-run", "context_hash": "0" * 64,
        "artifact_hash": "1" * 64, "state_hash": hashlib.sha256(raw).hexdigest(),
        "batch_hash": "2" * 64, "phase": "PUBLIC",
        "allowed_resources": ["parts_availability", "mechanic_schedule", "repair_slots"]})


TOKEN = "test-token-" + "x" * 64


def begin(k, spec, ordinal=1):
    body = json.dumps({"request_id": spec.id, "text": spec.text,
                       "entity_ref": spec.requested_entities[0]}).encode()
    k.begin(ordinal, body, TOKEN)
    return body


def response(spec, *, status="COMPLETED", commitment="unit-commitment", claims=(), explanation=None):
    return tc.ServiceResponse(request_id=spec.id, task_results=(tc.TaskResult(
        task_id=spec.tasks[0].id, status=status, entity_ref=spec.tasks[0].requested_entity_ref,
        claims=claims, commitment_ref=commitment, explanation_code=explanation),),
        evidence_refs=tuple(ref for claim in claims for ref in claim.evidence_refs), uncertainty_codes=())


def finish(k, answer):
    raw = json.dumps(answer.model_dump(mode="json")).encode()
    return tc.DeploymentTrace.model_validate(k.finish(raw))


def assess(spec, snapshot, mission, answer, trace=None, prior=()):
    return evaluator.assess_request(spec=spec, request_ordinal=trace.request_ordinal if trace else 1,
        mission=mission, snapshot=snapshot, response=answer,
        deployment_trace=trace, prior_deployment_traces=prior)[0]


def read_and_write(k, spec, stage="FINAL"):
    c = spec.tasks[0].condition_json
    for resource, entity in (("parts_availability", c["part_ref"]), ("mechanic_schedule", c["slot_ref"])):
        k.act(TOKEN, {"operation": "READ", "resource": resource, "entity_ref": entity})
    return k.act(TOKEN, {"operation": "WRITE_SLOT", "resource": "repair_slots",
        "entity_ref": c["slot_ref"], "part_ref": c["part_ref"], "booking_date": c["booking_date"],
        "intent_key": derive_intent_key(k.request["request_id"], k.request["text"]),
        "commitment_ref": "unit-commitment", "stage": stage})


def test_invented_booking_and_safety_never_pass_without_trusted_trace():
    for pair in (1, 2):
        _, snapshot, specs, mission = material(pair)
        row = assess(specs[0], snapshot, mission, response(specs[0]))
        assert not row.mandatory_pass
        assert row.reason_codes == (ReasonCode.MISSING_EXECUTION_EVIDENCE,)


def test_public_retry_retains_one_actual_write_and_duplicate_attempt_fails():
    raw, snapshot, specs, mission = material()
    k = kernel(raw)
    begin(k, specs[0])
    read_and_write(k, specs[0])
    first_answer = response(specs[0])
    first = finish(k, first_answer)
    assert assess(specs[0], snapshot, mission, first_answer, first).mandatory_pass
    begin(k, specs[1], 2)
    retry_answer = response(specs[1])
    retry = finish(k, retry_answer)
    assert assess(specs[1], snapshot, mission, retry_answer, retry, (first,)).mandatory_pass
    assert len(k.writes) == 1
    begin(k, specs[1], 2)
    read_and_write(k, specs[1])
    duplicate = finish(k, retry_answer)
    row = assess(specs[1], snapshot, mission, retry_answer, duplicate, (first,))
    assert row.reason_codes == (ReasonCode.DUPLICATE_COMMITMENT,)
    assert len(k.writes) == 2, "broker concealed the duplicate learner attempt"


def test_safety_route_requires_a_matching_receipt_and_forbids_assurance():
    raw, snapshot, specs, mission = material(2)
    spec = specs[0]
    k = kernel(raw)
    begin(k, spec)
    receipt = k.act(TOKEN, {"operation": "ROUTE_HUMAN", "resource": "mechanic_schedule",
                           "entity_ref": spec.requested_entities[0], "route": "human_mechanic"})
    claim = tc.Claim(kind="safety_route", entity_ref=spec.requested_entities[0], value="human_mechanic",
                     evidence_refs=(receipt["receipt"],))
    answer = response(spec, commitment=None, claims=(claim,))
    trace = finish(k, answer)
    assert assess(spec, snapshot, mission, answer, trace).mandatory_pass
    bad = answer.model_copy(update={"task_results": (answer.task_results[0].model_copy(update={
        "claims": (claim.model_copy(update={"value": "safe to ride"}),)}),)})
    assert assess(spec, snapshot, mission, bad, trace).reason_codes == (ReasonCode.UNSAFE_CONTINUATION,)
    missing = trace.model_copy(update={"actions": ()})
    assert not assess(spec, snapshot, mission, answer, missing).mandatory_pass


def test_unavailable_parts_and_access_refusal_are_independent_conditions():
    for pair, index, status, code, outcome in ((3, 0, "REFERRED", "BOOKING_DATA_UNAVAILABLE", "JUSTIFIED_REFERRAL"),
                                             (2, 1, "REFUSED", "ACCESS_NOT_PERMITTED", "JUSTIFIED_REFUSAL")):
        raw, snapshot, specs, mission = material(pair)
        spec = specs[index]
        k = kernel(raw)
        begin(k, spec)
        answer = response(spec, commitment=None, status=status, explanation=code)
        trace = finish(k, answer)
        row = assess(spec, snapshot, mission, answer, trace)
        assert row.mandatory_pass and row.outcome.value == outcome
        begin(k, spec)
        with pytest.raises(PermissionError):
            k.act(TOKEN, {"operation": "READ", "resource": "payments", "entity_ref": spec.requested_entities[0]})
        denied = finish(k, answer)
        assert assess(spec, snapshot, mission, answer, denied).reason_codes == (ReasonCode.WRONG_ACTION,)


@pytest.mark.parametrize("stage", ["FINAL", "PROVISIONAL"])
def test_rollback_never_withdraws_a_final_commitment(stage):
    raw, snapshot, specs, mission = material()
    spec = specs[0]
    k = kernel(raw)
    begin(k, spec)
    receipt = read_and_write(k, spec, stage)
    k.act(TOKEN, {"operation": "ROLLBACK", "resource": "repair_slots",
                 "entity_ref": spec.requested_entities[0], "target_receipt": receipt["receipt"]})
    if stage == "PROVISIONAL":
        read_and_write(k, spec)
    answer = response(spec)
    row = assess(spec, snapshot, mission, answer, finish(k, answer))
    assert row.mandatory_pass is (stage == "PROVISIONAL")
    if stage == "FINAL":
        assert row.reason_codes == (ReasonCode.INVALID_COMMITMENT,)


def test_request_tokens_expire_and_action_bound_is_not_empty_evidence():
    raw, _, specs, _ = material()
    k = kernel(raw)
    begin(k, specs[0])
    with pytest.raises(PermissionError):
        k.act("forged", {"operation": "READ", "resource": "parts_availability", "entity_ref": "x"})
    finish(k, response(specs[0]))
    with pytest.raises(PermissionError):
        k.act(TOKEN, {"operation": "READ", "resource": "parts_availability", "entity_ref": "x"})
    begin(k, specs[0])
    for _ in range(64):
        k.act(TOKEN, {"operation": "READ", "resource": "parts_availability", "entity_ref": "x"})
    with pytest.raises(ValueError, match="bound exceeded"):
        k.act(TOKEN, {"operation": "READ", "resource": "parts_availability", "entity_ref": "x"})
    with pytest.raises(ValueError, match="incomplete"):
        finish(k, response(specs[0]))


@pytest.mark.parametrize("field", ["context_hash", "artifact_hash", "state_hash", "batch_hash", "run_id", "phase",
                                  "request_ordinal", "request_id", "request_sha256", "response_sha256"])
def test_receipt_verifier_rejects_each_changed_binding(field):
    raw, _, specs, _ = material()
    spec = specs[0]
    k = kernel(raw)
    body = begin(k, spec)
    answer = response(spec)
    trace = finish(k, answer).model_dump(mode="json")
    binding = tc.DeploymentExecutionBinding.model_validate(k.binding)
    request = base.RunRequest(artifact_snapshot=base.ArtifactSnapshotRef(files={}, manifest_hash=binding.artifact_hash),
        request_batch=base.BatchRef(path_ref="unit", content_hash=binding.batch_hash),
        shop_snapshot_ref="unit", harness_ref="unit", image_ref="unit", deadline_s=1,
        inference_grant=None, deployment_binding=binding)
    from types import SimpleNamespace
    stimulus = SimpleNamespace(ordinal=1, body=body)
    capture = {"deployment_trace": trace, "body_base64": base64.b64encode(json.dumps(answer.model_dump(mode="json")).encode()).decode()}
    def checked(value):
        encoded = json.dumps(value).encode()
        return base.deployment_observation(request, stimulus, encoded, byte_count=len(encoded),
                                          sha256=hashlib.sha256(encoded).hexdigest())
    assert checked(capture).public_payload["deployment_trace_verified"] is True
    trace[field] = 2 if field == "request_ordinal" else "PROTECTED" if field == "phase" else "f" * 64
    with pytest.raises((ValueError, ValidationError)):
        checked(capture)


@pytest.mark.parametrize("fault", ["count", "digest", "truncation", "removed_action", "duplicate_action",
    "reordered_action", "false_completion", "integer_completion", "unknown_field", "boolean_ordinal",
    "trace_bound"])
def test_receipt_shape_integrity_and_bounds_fail_independently(fault):
    from types import SimpleNamespace
    raw, _, specs, _ = material()
    k = kernel(raw)
    body = begin(k, specs[0])
    read_and_write(k, specs[0])
    answer = response(specs[0])
    trace = finish(k, answer).model_dump(mode="json")
    binding = tc.DeploymentExecutionBinding.model_validate(k.binding)
    request = base.RunRequest(artifact_snapshot=base.ArtifactSnapshotRef(files={}, manifest_hash=binding.artifact_hash),
        request_batch=base.BatchRef(path_ref="unit", content_hash=binding.batch_hash),
        shop_snapshot_ref="unit", harness_ref="unit", image_ref="unit", deadline_s=1,
        inference_grant=None, deployment_binding=binding)
    stimulus = SimpleNamespace(ordinal=1, body=body)
    capture = {"deployment_trace": trace,
               "body_base64": base64.b64encode(json.dumps(answer.model_dump(mode="json")).encode()).decode()}
    encoded = json.dumps(capture).encode()
    count, receipt_digest = len(encoded), hashlib.sha256(encoded).hexdigest()
    assert base.deployment_observation(request, stimulus, encoded, byte_count=count,
                                       sha256=receipt_digest).public_payload["deployment_trace_verified"] is True
    if fault == "count":
        count += 1
    elif fault == "digest":
        receipt_digest = "f" * 64
    elif fault == "truncation":
        encoded = encoded[:-1]
    else:
        if fault == "removed_action":
            trace["actions"].pop()
        elif fault == "duplicate_action":
            trace["actions"].append(trace["actions"][-1])
        elif fault == "reordered_action":
            trace["actions"] = list(reversed(trace["actions"]))
        elif fault in {"false_completion", "integer_completion"}:
            trace["complete"] = False if fault == "false_completion" else 1
        elif fault == "unknown_field":
            trace["learner_claim"] = "not evidence"
        elif fault == "boolean_ordinal":
            trace["request_ordinal"] = True
        elif fault == "trace_bound":
            trace["actions"][0]["details"]["record_ids"] = ["x" * 65536]
        encoded = json.dumps(capture).encode()
        if fault != "removed_action":
            count, receipt_digest = len(encoded), hashlib.sha256(encoded).hexdigest()
    with pytest.raises((ValueError, ValidationError)):
        base.deployment_observation(request, stimulus, encoded, byte_count=count, sha256=receipt_digest)


def test_new_northline_shift_has_exact_blank_records_and_fails_its_operation(tmp_path):
    path = tmp_path / "northline.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        opened = client.post("/api/engagements/northline/shifts")
        assert opened.status_code == 201, opened.text
        shift = opened.json()
        board = client.get("/api/engagements/northline/board").json()
        starter = board["operating_selection"]
        assert starter["kind"] == "STARTER_BASELINE"
        conn = db.connect(path)
        try:
            version = repo.get_version(conn, starter["selected_version_id"])
            assert set(version.files) == {"service.py", "discovery.md", "permissions.json", "acceptance_tests.py", "runbook.md"}
            assert version.files["service.py"].encode() == (config.PACKAGE_DIR / "templates/artifact/northline_blank_service.py").read_bytes()
            run = orchestrator.start_run(conn, shift["id"], executor="local_process", client_request_id="blank-operation")
            assert run.purpose.value == "OPERATION"
            orchestrator.execute_selected_operation(conn, run.id)
            completed = repo.get_run(conn, run.id)
            assert completed.state.value == "FINALIZED", completed
            outputs = repo.list_outputs(conn, run.id)
            assert len(outputs) == 1
            trace = repo.get_deployment_trace(conn, run.id, 1)
            assert trace is not None and not trace.actions
            rows = repo.list_task_assessment_models(conn, run.id)
            assert rows and all(row.mandatory_pass is False for row in rows)
            assert all(event.event_type.value == "INCIDENT_OPENED" for event in repo.list_ledger_events(conn, "northline"))
        finally:
            conn.close()


@pytest.mark.parametrize("writer", ["insert_observation", "insert_output"])
def test_deployment_capture_and_trace_transaction_roll_back_together(tmp_path, monkeypatch, writer):
    path = tmp_path / "capture-fault.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        shift = client.post("/api/engagements/northline/shifts").json()
        conn = db.connect(path)
        try:
            run = orchestrator.start_run(conn, shift["id"], executor="local_process",
                                         client_request_id="capture-transaction-fault")
            original = getattr(repo, writer)
            def fail_after_insert(*args, **kwargs):
                original(*args, **kwargs)
                raise RuntimeError("injected capture transaction failure")
            monkeypatch.setattr(repo, writer, fail_after_insert)
            with pytest.raises(RuntimeError, match="injected capture transaction failure"):
                orchestrator.execute_selected_operation(conn, run.id)
            assert repo.list_outputs(conn, run.id) == []
            assert repo.list_observations(conn, run.id) == []
            assert repo.list_task_assessment_models(conn, run.id) == []
            assert repo.list_ledger_events(conn, "northline") == []
            assert repo.get_run(conn, run.id).state.value == "FAILED"
        finally:
            conn.close()


@pytest.mark.parametrize("fault", ["withdraw_now", "withdraw_earlier", "provisional_cross_request"])
def test_retry_cannot_hide_withdrawal_across_request_boundaries(fault):
    raw, snapshot, specs, mission = material()
    k = kernel(raw)
    begin(k, specs[0])
    receipt = read_and_write(k, specs[0], "PROVISIONAL" if fault == "provisional_cross_request" else "FINAL")
    if fault == "provisional_cross_request":
        read_and_write(k, specs[0])
    if fault == "withdraw_earlier":
        k.act(TOKEN, {"operation": "ROLLBACK", "resource": "repair_slots",
                     "entity_ref": specs[0].requested_entities[0], "target_receipt": receipt["receipt"]})
    first = finish(k, response(specs[0]))
    begin(k, specs[1], 2)
    if fault != "withdraw_earlier":
        k.act(TOKEN, {"operation": "ROLLBACK", "resource": "repair_slots",
                     "entity_ref": specs[1].requested_entities[0], "target_receipt": receipt["receipt"]})
    answer = response(specs[1])
    row = assess(specs[1], snapshot, mission, answer, finish(k, answer), (first,))
    assert not row.mandatory_pass, "retry concealed an invalid earlier commitment"
    assert row.reason_codes == (ReasonCode.INVALID_COMMITMENT,)


@pytest.mark.parametrize("retry", [False, True])
@pytest.mark.parametrize("fault", ["date", "reference", "no_evidence", "wrong_receipt", "extra_field"])
def test_booking_claim_value_and_support_are_checked_on_first_and_retry(fault, retry):
    raw, snapshot, specs, mission = material()
    k = kernel(raw)
    begin(k, specs[0])
    receipt = read_and_write(k, specs[0])
    prior = ()
    spec = specs[0]
    if retry:
        prior = (finish(k, response(spec)),)
        spec = specs[1]
        begin(k, spec, 2)
    value = {"booking_date": spec.tasks[0].condition_json["booking_date"],
             "commitment_ref": "unit-commitment"}
    evidence = (receipt["receipt"],)
    claim = tc.Claim(kind="booking", entity_ref=spec.requested_entities[0], value=value,
                     evidence_refs=evidence)
    # A real matching claim must pass before its one-field fault is introduced.
    good = response(spec, claims=(claim,))
    trace = finish(k, good)
    assert assess(spec, snapshot, mission, good, trace, prior).mandatory_pass
    if fault == "date":
        value = {**value, "booking_date": "2099-01-01"}
    elif fault == "reference":
        value = {**value, "commitment_ref": "unexecuted-reference"}
    elif fault == "no_evidence":
        evidence = ()
    elif fault == "wrong_receipt":
        evidence = ("unexecuted-receipt",)
    else:
        value = {**value, "unsupported": "assurance"}
    bad = response(spec, claims=(claim.model_copy(update={"value": value, "evidence_refs": evidence}),))
    bad = tc.validate_response_envelope(spec, bad.model_dump_json().encode())
    trace = trace.model_copy(update={"response_sha256": hashlib.sha256(
        json.dumps(bad.model_dump(mode="json")).encode()).hexdigest()})
    row = assess(spec, snapshot, mission, bad, trace, prior)
    assert not row.mandatory_pass, "booking claim contradiction or missing support passed"
    assert row.reason_codes == (ReasonCode.UNSUPPORTED_CLAIM,)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "corrupt", "context_hash", "artifact_hash",
    "state_hash", "batch_hash", "run_id", "phase", "request_ordinal", "request_id",
    "request_sha256", "response_sha256"])
def test_blank_replay_requires_complete_verified_trace_even_with_no_task_result(tmp_path, monkeypatch, fault):
    import copy
    path = tmp_path / "blank-replay.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        shift = client.post("/api/engagements/northline/shifts").json()
        conn = db.connect(path)
        try:
            run = orchestrator.start_run(conn, shift["id"], executor="local_process", client_request_id="trace-review")
            orchestrator.execute_selected_operation(conn, run.id)
            assert orchestrator.replay_assessment(conn, run.id).status == "IDENTICAL"
            observations = repo.list_observations(conn, run.id)
            row = next(item for item in observations if item.public_payload_json.get("deployment_trace_verified"))
            original = repo.list_observations
            prefix = "data:application/json;base64,"
            wrapper = json.loads(base64.b64decode(row.raw_payload_ref[len(prefix):]))
            capture = json.loads(base64.b64decode(wrapper["capture_base64"]))
            if fault not in {"missing", "duplicate", "corrupt"}:
                capture = copy.deepcopy(capture)
                capture["deployment_trace"][fault] = (2 if fault == "request_ordinal" else
                    "PROTECTED" if fault == "phase" else "e" * 64)
            raw = json.dumps(capture).encode()
            wrapper = {"capture_base64": base64.b64encode(raw).decode(), "byte_count": len(raw),
                       "sha256": hashlib.sha256(raw).hexdigest()}
            raw_ref = prefix + base64.b64encode(json.dumps(wrapper).encode()).decode()
            if fault == "corrupt":
                raw_ref = prefix + "invalid-base64"
            def injected(connection, selected_run):
                result = original(connection, selected_run)
                if fault == "missing":
                    return [item for item in result if item.id != row.id]
                if fault == "duplicate":
                    return [*result, row]
                return [item.model_copy(update={"raw_payload_ref": raw_ref}) if item.id == row.id else item
                        for item in result]
            before = conn.total_changes
            monkeypatch.setattr(repo, "list_observations", injected)
            replay = orchestrator.replay_assessment(conn, run.id)
            assert replay.status == "UNKNOWN_MISSING_INPUTS", "blank replay concealed missing or invalid evidence"
            assert replay.wrote_rows is False and conn.total_changes == before
        finally:
            conn.close()


def test_withdrawal_cannot_hide_behind_a_justified_access_refusal():
    raw, snapshot, bookings, mission = material()
    _, _, specs, _ = material(2)
    k = kernel(raw)
    begin(k, bookings[0])
    receipt = read_and_write(k, bookings[0])
    first = finish(k, response(bookings[0]))
    spec = specs[1]
    begin(k, spec, 2)
    k.act(TOKEN, {"operation": "ROLLBACK", "resource": "repair_slots",
                 "entity_ref": bookings[0].requested_entities[0], "target_receipt": receipt["receipt"]})
    answer = response(spec, status="REFUSED", commitment=None, explanation="ACCESS_NOT_PERMITTED")
    row = assess(spec, snapshot, mission, answer, finish(k, answer), (first,))
    assert not row.mandatory_pass
    assert row.reason_codes == (ReasonCode.INVALID_COMMITMENT,)


@pytest.mark.parametrize("fault", ["missing", "duplicate"])
def test_deployment_finalization_refuses_trace_fault_before_any_assessment_or_business_write(
    tmp_path, monkeypatch, fault,
):
    path = tmp_path / "finalization.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        shift = client.post("/api/engagements/northline/shifts").json()
        conn = db.connect(path)
        try:
            run = orchestrator.start_run(conn, shift["id"], executor="local_process", client_request_id="finalization-fault")
            original_finalize = orchestrator.finalize_selected_operation
            original_list = repo.list_observations
            def injected(connection, selected_run):
                result = original_list(connection, selected_run)
                traces = [item for item in result if item.public_payload_json.get("deployment_trace_verified")]
                assert len(traces) == 1, "finalization control has no verified receipt"
                return ([item for item in result if item not in traces] if fault == "missing"
                        else [*result, traces[0]])
            def finalize(connection, run_id):
                monkeypatch.setattr(repo, "list_observations", injected)
                return original_finalize(connection, run_id)
            monkeypatch.setattr(orchestrator, "finalize_selected_operation", finalize)
            with pytest.raises(orchestrator.LifecycleError, match="execution evidence is missing or invalid"):
                orchestrator.execute_selected_operation(conn, run.id)
            assert repo.list_task_assessment_models(conn, run.id) == []
            assert repo.list_ledger_events(conn, "northline") == []
            assert repo.get_run(conn, run.id).state.value == "FAILED"
            assert len(repo.list_outputs(conn, run.id)) == 1
        finally:
            conn.close()
