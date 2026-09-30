"""S17 exact selection and S18 selected-version operation proofs."""

import base64
import json
import shutil
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from demos.final_pivot import create_v5_sample
from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain.errors import InvalidSealedCase
from shiftwork.sealed import store as sealed_store
from shiftwork.store import db, repo
from shiftwork.domain.models import (ExecutorFailure, RunOutput, RunState,
                                     LedgerEventDraft, LedgerEventType,
                                      ExecutionObservation, ObservationKind,
                                      CheckResult, ReasonCode)
from shiftwork.gateway.redaction import serialized_contains
from shiftwork.ledger import chain
from shiftwork.ledger import reducer
from shiftwork.evaluator import evaluator
from shiftwork.domain import task_contract
from shiftwork.domain.models import RunPurpose, OperationalAssessment
from shiftwork.domain.task_contract import TaskAssessment, TaskOutcome
from shiftwork.executor.base import RawCapture, RawObservation, RunResult
from shiftwork.executor.local_process import LocalProcessAdapter


def _candidate(client, shift_id, label):
    saved = client.put(
        f"/api/shifts/{shift_id}/artifact",
        json={"files": config.comparison_candidate_files(label)},
    )
    assert saved.status_code == 200, saved.text
    frozen = client.post(
        f"/api/shifts/{shift_id}/artifact/versions",
        json={"contract": config.PIVOT_STARTER_CONTRACT_JSON},
    )
    assert frozen.status_code == 201, frozen.text
    return frozen.json()


def _comparison(client, shift_id, source_run_id):
    investigation = client.post(f"/api/shifts/{shift_id}/investigations", json={
        "source_run_id": source_run_id, "source_request_ordinal": 1,
        "cause": "the old response omits a required task",
        "falsifier": "the frozen request receives every required task result",
        "public_test": "check every required task independently",
        "client_request_id": f"investigate-{shift_id}",
    })
    assert investigation.status_code == 201, investigation.text
    a, b = (_candidate(client, shift_id, label) for label in ("A", "B"))
    created = client.post(f"/api/shifts/{shift_id}/experiments", json={
        "kind": "QUALIFYING_COMPARISON",
        "investigation_id": investigation.json()["id"],
        "candidate_a_version_id": a["id"],
        "candidate_b_version_id": b["id"],
        "declared_treatment": "A chooses lowest price; B chooses highest stock",
        "client_request_id": f"compare-{shift_id}",
    })
    assert created.status_code == 202, created.text
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        view = client.get(f"/api/experiments/{created.json()['id']}").json()
        if view["state"] in ("FINALIZED", "FAILED"):
            break
        time.sleep(0.05)
    assert view["outcome"]["status"] == "COMPLETE", view
    assert all(item["eligible"] for item in view["outcome"]["eligibility"])
    return a, b, view


def _choice(comparison, version, prior, key="choice-1", rationale="A answers the required tasks"):
    return {
        "comparison_id": comparison["id"],
        "selected_version_id": version["id"],
        "rationale": rationale,
        "expected_prior_selection_id": prior,
        "client_request_id": key,
    }


@pytest.fixture
def selected_migrated(tmp_path):
    copied = tmp_path / "selected-operation.db"
    create_v5_sample(copied)
    with TestClient(create_app(str(copied))) as client:
        opened = client.post("/api/engagements/bookshop/shifts")
        assert opened.status_code == 201, opened.text
        shift_id = opened.json()["id"]
        a, b, comparison = _comparison(client, shift_id, "run-v5-0001")
        choice = client.post(f"/api/shifts/{shift_id}/selections",
                             json=_choice(comparison, b, None, key="s18-choice"))
        assert choice.status_code == 201, choice.text
        yield client, copied, shift_id, choice.json(), a, b, comparison


def test_selected_operation_newer_save_and_exact_key_replay(selected_migrated):
    client, _, shift_id, selected, _, b, _ = selected_migrated
    newer = _candidate(client, shift_id, "A")
    assert newer["id"] != selected["selected_version_id"]
    path = f"/api/shifts/{shift_id}/runs"
    before = client.get("/api/engagements/bookshop/ledger").json()["events"]
    started = client.post(path, json={"client_request_id": "s18-operation"})
    assert started.status_code == 202, started.text
    run = client.get(f"/api/runs/{started.json()['id']}").json()
    assert run["state"] == "FINALIZED" and run["artifact_version_id"] == b["id"]
    assert run["selection_id"] == selected["id"] and run["purpose"] == "OPERATION"
    checks = client.get(f"/api/runs/{run['id']}/checks").json()
    outputs = client.get(f"/api/runs/{run['id']}/outputs").json()
    events = client.get("/api/engagements/bookshop/ledger").json()["events"]
    assert checks and checks[0]["public_check_id"].startswith("task:")
    assert outputs and outputs[0]["customer_answer"]["display_text"]
    assert [event["event_type"] for event in events[len(before):]] == ["SALE_COMPLETED"]
    assert events[-1]["synthetic"] is True and events[-1]["derivation"]["run_id"] == run["id"]
    replay = client.post(path, json={"client_request_id": "s18-operation"})
    assert replay.status_code == 202 and replay.json()["id"] == run["id"]
    assert client.get("/api/engagements/bookshop/ledger").json()["events"] == events
    assert client.post(path, json={"client_request_id": "second-operation"}).status_code == 409


def test_finalized_operation_unique_constraint_is_database_enforced(selected_migrated):
    client, db_file, shift_id, _, _, _, _ = selected_migrated
    started = client.post(f"/api/shifts/{shift_id}/runs",
                          json={"client_request_id": "unique-first"})
    assert started.status_code == 202 and client.get(f"/api/runs/{started.json()['id']}").json()["state"] == "FINALIZED"
    conn = db.connect(db_file)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed: runs.shift_id"):
            conn.execute(
                "INSERT INTO runs (id, shift_id, artifact_version_id, request_batch_ref, "
                "shop_snapshot_ref, attempt_number, state, adapter, started_at, purpose, "
                "evidence_mode, selection_id, context_id) "
                "SELECT 'run-s18-success-fault', shift_id, artifact_version_id, "
                "request_batch_ref, shop_snapshot_ref, attempt_number + 1, 'FINALIZED', adapter, "
                "started_at, purpose, evidence_mode, selection_id, context_id "
                "FROM runs WHERE id = ?", (started.json()["id"],))
    finally:
        conn.rollback()
        conn.close()


def test_selected_operation_restart_retains_capture_without_business_write(selected_migrated):
    _, db_file, shift_id, _, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        run = orchestrator.start_run(conn, shift_id, client_request_id="interrupted-operation")
        repo.insert_output(conn, RunOutput(id=f"{run.id}-out-1", run_id=run.id,
            request_ordinal=1, request_text="captured request", http_status=200,
            body=b"partial capture", elapsed_ms=1))
        repo.insert_observation(conn, ExecutionObservation(
            id=f"{run.id}-usage-1", run_id=run.id, request_ordinal=1, ordinal=1,
            kind=ObservationKind.USAGE,
            public_payload_json={"source": "controller_verified", "input_tokens": 4},
            raw_payload_ref="data:application/json;base64,e30=",
            measured_at=orchestrator._now(),
        ))
        exposure = repo.get_exposure_reservation(conn, f"exposure-operation-{run.id}")
        assert exposure is not None and exposure.state == "ACTIVE"
        conn.commit()
        before = repo.list_ledger_events(conn, "bookshop")
        assert run.id in orchestrator.reconcile_interrupted(conn)
        assert repo.get_run(conn, run.id).state is RunState.FAILED
        assert len(repo.list_outputs(conn, run.id)) == 1
        assert repo.list_observations(conn, run.id)[0].public_payload_json["input_tokens"] == 4
        assert repo.get_exposure_reservation(conn, exposure.id) == exposure
        assert repo.list_check_results(conn, run.id) == []
        assert repo.list_ledger_events(conn, "bookshop") == before
        assert orchestrator.reconcile_interrupted(conn) == []
    finally:
        conn.close()


def test_selected_operation_failed_adapter_retains_usage_without_business_write(
    selected_migrated, monkeypatch
):
    client, db_file, shift_id, _, _, _, _ = selected_migrated
    before = client.get("/api/engagements/bookshop/ledger").json()["events"]
    async def failed_execute(self, request):
        return RunResult(
            captures=(RawCapture(request_ordinal=1, http_status=None, body=b"partial",
                                 elapsed_ms=4, transport_error=ExecutorFailure.SERVICE_UNREACHABLE,
                                 log_ref=None),),
            executor_ref=None, failure=ExecutorFailure.SERVICE_UNREACHABLE, wall_ms=4,
            observations=(RawObservation(kind="USAGE", public_payload={"input_tokens": 4},
                                         raw_payload={"input_tokens": 4}),),
        )
    monkeypatch.setattr(LocalProcessAdapter, "execute", failed_execute)
    started = client.post(f"/api/shifts/{shift_id}/runs",
                          json={"client_request_id": "failed-service"})
    assert started.status_code == 202
    conn = db.connect(db_file)
    try:
        run = repo.get_run(conn, started.json()["id"])
        assert run.state is RunState.FAILED and run.failure_kind is ExecutorFailure.SERVICE_UNREACHABLE
        assert len(repo.list_outputs(conn, run.id)) == 1
        assert repo.list_observations(conn, run.id)[0].public_payload_json["input_tokens"] == 4
        assert repo.list_check_results(conn, run.id) == []
        assert client.get("/api/engagements/bookshop/ledger").json()["events"] == before
    finally:
        conn.close()


def test_incident_resolves_only_after_selected_operational_regression(selected_migrated, monkeypatch):
    client, db_file, shift_id, first_selection, _, _, _ = selected_migrated
    original_execute = LocalProcessAdapter.execute
    async def failed_task(self, request):
        result = await original_execute(self, request)
        captures = tuple(item.model_copy(update={"body": b"{}"}) for item in result.captures)
        return result.model_copy(update={"captures": captures})
    with monkeypatch.context() as patch:
        patch.setattr(LocalProcessAdapter, "execute", failed_task)
        first = client.post(f"/api/shifts/{shift_id}/runs",
                            json={"client_request_id": "open-incident"})
    assert first.status_code == 202
    first_run = client.get(f"/api/runs/{first.json()['id']}").json()
    assert first_run["state"] == "FINALIZED"
    conn = db.connect(db_file)
    try:
        incidents = [item for item in repo.list_incidents(conn, "bookshop")
                     if item.opening_run_id == first_run["id"]]
        assert incidents
        before = [(item.id, item.state) for item in incidents]
        assert all(item.state.value == "OPEN" for item in incidents)
    finally:
        conn.close()
    assert client.post(f"/api/shifts/{shift_id}/close").status_code == 200
    next_shift = client.post("/api/engagements/bookshop/shifts")
    assert next_shift.status_code == 201, next_shift.text
    next_id = next_shift.json()["id"]
    same_version = client.post(f"/api/shifts/{next_id}/runs",
                               json={"client_request_id": "same-version-regression"})
    assert same_version.status_code == 202, same_version.text
    assert client.get(f"/api/runs/{same_version.json()['id']}").json()["state"] == "FINALIZED"
    a, b, comparison = _comparison(client, next_id, same_version.json()["id"])
    conn = db.connect(db_file)
    try:
        assert [(item.id, item.state) for item in repo.list_incidents(conn, "bookshop")
                if item.opening_run_id == first_run["id"]] != []
        assert all(item.state.value == "CLOSED_UNRESOLVED" for item in
                   repo.list_incidents(conn, "bookshop") if item.opening_run_id == first_run["id"]), "same version resolved an incident"
    finally:
        conn.close()
    choice = client.post(f"/api/shifts/{next_id}/selections",
                         json=_choice(comparison, a, first_selection["id"], key="regression-choice"))
    assert choice.status_code == 201, choice.text
    assert client.post(f"/api/shifts/{next_id}/close").status_code == 200
    third_shift = client.post("/api/engagements/bookshop/shifts")
    assert third_shift.status_code == 201, third_shift.text
    original_context = repo.get_execution_context
    conn = db.connect(db_file)
    try:
        opening_context_id = repo.get_run(conn, first_run["id"]).context_id
    finally:
        conn.close()
    def different_pinned_rule(conn, context_id):
        context = original_context(conn, context_id)
        if context_id == opening_context_id:
            return context.model_copy(update={"mission_hash": "0" * 64})
        return context
    with monkeypatch.context() as patch:
        patch.setattr(repo, "get_execution_context", different_pinned_rule)
        mismatched = client.post(f"/api/shifts/{third_shift.json()['id']}/runs",
                                 json={"client_request_id": "mismatched-rule"})
    assert mismatched.status_code == 202, mismatched.text
    assert client.get(f"/api/runs/{mismatched.json()['id']}").json()["state"] == "FINALIZED"
    conn = db.connect(db_file)
    try:
        assert all(item.state.value == "CLOSED_UNRESOLVED" for item in
                   repo.list_incidents(conn, "bookshop") if item.opening_run_id == first_run["id"]), "changed pinned rule resolved an incident"
    finally:
        conn.close()
    assert client.post(f"/api/shifts/{third_shift.json()['id']}/close").status_code == 200
    fourth_shift = client.post("/api/engagements/bookshop/shifts")
    assert fourth_shift.status_code == 201, fourth_shift.text
    second = client.post(f"/api/shifts/{fourth_shift.json()['id']}/runs",
                         json={"client_request_id": "resolve-incident"})
    assert second.status_code == 202, second.text
    assert client.get(f"/api/runs/{second.json()['id']}").json()["state"] == "FINALIZED"
    conn = db.connect(db_file)
    try:
        after = [item for item in repo.list_incidents(conn, "bookshop")
                 if item.opening_run_id == first_run["id"]]
        assert [(item.id, item.state.value) for item in after] == [
            (incident_id, "RESOLVED") for incident_id, _ in before]
        assert all(item.resolving_version_id == a["id"] for item in after)
    finally:
        conn.close()


def test_operational_event_projection_scanner_self_test_and_error(selected_migrated, monkeypatch):
    client, db_file, shift_id, _, _, _, _ = selected_migrated
    started = client.post(f"/api/shifts/{shift_id}/runs",
                          json={"client_request_id": "projection-operation"})
    assert started.status_code == 202
    normal = client.get("/api/engagements/bookshop/ledger")
    assert normal.status_code == 200 and normal.json()["events"][-1]["synthetic"] is True
    needle = r"C:\controller\private\S18-operation-7c92.txt"
    assert serialized_contains({"event": {"payload": {"detail": needle}}}, needle)
    assert serialized_contains({"event": json.dumps({"detail": needle})}, needle)
    assert serialized_contains({"event": {"detail": needle.replace("\\", "/")}}, needle)
    assert serialized_contains({"body_base64": base64.b64encode(needle.encode()).decode()}, needle)
    monkeypatch.setenv("NEBIUS_API_KEY", needle)
    conn = db.connect(db_file)
    try:
        latest = repo.list_ledger_events(conn, "bookshop")[-1]
        payload = dict(latest.payload)
        payload["detail"] = needle
        digest = chain.event_hash(seq=latest.seq, prev_hash=latest.prev_hash,
            event_type=latest.event_type.value, cause_refs=latest.cause_refs,
            payload=payload, synthetic=True)
        conn.execute("UPDATE ledger_events SET payload_json = ?, hash = ? "
                     "WHERE engagement_slug = ? AND seq = ?",
                     (json.dumps(payload, sort_keys=True), digest, "bookshop", latest.seq))
        conn.commit()
    finally:
        conn.close()
    error = client.get("/api/engagements/bookshop/ledger")
    assert error.status_code == 409
    assert not serialized_contains(error.json(), needle)
    assert "private material" in error.json()["detail"]


def test_selected_operation_invalidated_at_run_start(selected_migrated):
    client, db_file, shift_id, _, _, _, comparison = selected_migrated
    conn = db.connect(db_file)
    try:
        reservation = repo.get_exposure_reservation_for_experiment(conn, comparison["id"])
        orchestrator.retire_comparison_exposure(conn, reservation.id)
    finally:
        conn.close()
    refused = client.post(f"/api/shifts/{shift_id}/runs",
                          json={"client_request_id": "invalidated-operation"})
    assert refused.status_code == 409
    assert "selection" in refused.json()["detail"]


def test_selected_operation_rejects_changed_selected_hash(selected_migrated):
    client, db_file, shift_id, selected, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        conn.execute("UPDATE operating_selections SET selected_content_hash = ? WHERE id = ?",
                     ("f" * 64, selected["id"]))
        conn.commit()
    finally:
        conn.close()
    refused = client.post(f"/api/shifts/{shift_id}/runs",
                          json={"client_request_id": "changed-hash"})
    assert refused.status_code == 409
    assert "missing or changed" in refused.json()["detail"]


def test_selected_operation_rejects_invalid_choice_even_with_active_exposure(selected_migrated):
    client, db_file, shift_id, selected, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        conn.execute("UPDATE operating_selections SET state = 'INVALIDATED' WHERE id = ?",
                     (selected["id"],))
        conn.commit()
    finally:
        conn.close()
    refused = client.post(f"/api/shifts/{shift_id}/runs",
                          json={"client_request_id": "invalid-choice"})
    assert refused.status_code == 409
    assert "valid selection" in refused.json()["detail"]


def test_selected_operation_invalidated_after_capture_has_no_business_write(selected_migrated):
    _, db_file, shift_id, selected, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        run = orchestrator.start_run(conn, shift_id, client_request_id="late-invalidation")
        before = repo.list_ledger_events(conn, "bookshop")
        conn.execute("UPDATE operating_selections SET state = 'INVALIDATED' WHERE id = ?",
                     (selected["id"],))
        conn.commit()
        with pytest.raises(orchestrator.LifecycleError, match="valid selection"):
            orchestrator.execute_selected_operation(conn, run.id)
        assert repo.get_run(conn, run.id).state is RunState.FAILED
        assert repo.list_outputs(conn, run.id)
        assert repo.list_check_results(conn, run.id) == []
        assert repo.list_ledger_events(conn, "bookshop") == before
    finally:
        conn.close()


def test_selected_operation_uses_captured_mission_after_file_change(
    selected_migrated, monkeypatch, tmp_path
):
    _, db_file, shift_id, _, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        run = orchestrator.start_run(conn, shift_id, client_request_id="captured-mission")
        context = repo.get_execution_context(conn, run.context_id)
        changed = tmp_path / "mission-after-start.json"
        changed.write_text('{"not":"the captured mission"}', encoding="utf-8")
        monkeypatch.setattr(config, "PIVOT_MISSION", changed)
        try:
            finished = orchestrator.execute_selected_operation(conn, run.id)
        except orchestrator.LifecycleError as error:
            pytest.fail(f"captured mission was rejected after file change: {error}")
        assert finished.state is RunState.FINALIZED
        assert repo.get_execution_context(conn, run.context_id).mission_hash == context.mission_hash
        assert any(run.id in event.cause_refs for event in repo.list_ledger_events(conn, "bookshop"))
    finally:
        conn.close()


def test_experiment_cannot_construct_operational_business_drafts(selected_migrated):
    _, db_file, shift_id, _, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        run = orchestrator.start_run(conn, shift_id, client_request_id="purpose-guard")
        context = repo.get_execution_context(conn, run.context_id)
        mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))
        assessment = OperationalAssessment(run_id=run.id, context_hash=context.content_hash,
            complete_request_count=0, expected_request_count=1, mandatory_pass=False,
            rule_version="operation-ledger-v1", assessed_at=orchestrator._now(),
            selection_id=run.selection_id)
        before = repo.list_ledger_events(conn, "bookshop")
        with pytest.raises(ValueError, match="selected operational run"):
            reducer.reduce_operation(run.model_copy(update={"purpose": RunPurpose.EXPERIMENT}),
                                     assessment, mission, (), ())
        assert repo.list_ledger_events(conn, "bookshop") == before
    finally:
        conn.close()


def test_optional_unsupported_claim_cannot_create_synthetic_sale(selected_migrated):
    _, db_file, shift_id, _, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        run = orchestrator.start_run(conn, shift_id, client_request_id="optional-claim")
        mission = task_contract.load_mission_bytes(config.PIVOT_MISSION.read_bytes())
        spec = mission.request_specs[0]
        rows = tuple(TaskAssessment(
            request_id=spec.id, request_ordinal=1, task_id=task.id,
            outcome=(TaskOutcome.INCORRECT_OUTPUT if task.id == "price"
                     else TaskOutcome.USEFUL_COMPLETION),
            mandatory_pass=task.id != "price",
            reason_codes=((ReasonCode.UNSUPPORTED_CLAIM,)
                          if task.id == "price" else ()),
        ) for task in spec.tasks)
        assert not evaluator.request_usefully_completed(spec, rows)
        assessment = OperationalAssessment(
            run_id=run.id, context_hash="test-context", complete_request_count=0,
            expected_request_count=1, mandatory_pass=False, rule_version="operation-ledger-v1",
            assessed_at=orchestrator._now(), selection_id=run.selection_id,
        )
        checks = tuple(CheckResult(
            id=f"check-{task.id}", run_id=run.id,
            check_id=f"task:{spec.id}:{task.id}", verdict="fail" if task.id == "price" else "pass",
            observed_ref="output-1",
            reason_code=(ReasonCode.UNSUPPORTED_CLAIM if task.id == "price" else None),
        ) for task in spec.tasks)
        drafts = reducer.reduce_operation(run, assessment, mission, rows, checks)
        assert not any(draft.event_type is LedgerEventType.SALE_COMPLETED for draft in drafts)
    finally:
        conn.close()


def test_changed_mission_between_selection_check_and_freeze_blocks_run(
    selected_migrated, monkeypatch,
):
    _, db_file, shift_id, _, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    original_read = type(config.PIVOT_MISSION).read_bytes
    mission_reads = 0

    def changed_second_read(path):
        nonlocal mission_reads
        payload = original_read(path)
        if path == config.PIVOT_MISSION:
            mission_reads += 1
            if mission_reads == 2:
                return payload + b"\n"
        return payload

    try:
        before = repo.count_runs_all(conn)
        monkeypatch.setattr(type(config.PIVOT_MISSION), "read_bytes", changed_second_read)
        with pytest.raises(orchestrator.LifecycleError, match="selected requirements changed"):
            orchestrator.start_run(conn, shift_id, client_request_id="changed-mission")
        assert repo.count_runs_all(conn) == before
    finally:
        conn.close()


def test_database_rejects_purpose_change_to_second_inflight_operation(selected_migrated):
    _, db_file, shift_id, _, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        first = orchestrator.start_run(conn, shift_id, client_request_id="inflight-first")
        conn.execute(
            "INSERT INTO runs (id, shift_id, artifact_version_id, request_batch_ref, "
            "shop_snapshot_ref, attempt_number, state, adapter, started_at, purpose, "
            "evidence_mode, selection_id, context_id) "
            "SELECT 'run-s18-purpose-fault', shift_id, artifact_version_id, "
            "request_batch_ref, shop_snapshot_ref, attempt_number + 1, state, adapter, "
            "started_at, 'EXPERIMENT', evidence_mode, selection_id, context_id "
            "FROM runs WHERE id = ?", (first.id,))
        with pytest.raises(sqlite3.IntegrityError, match="operation already in flight"):
            conn.execute("UPDATE runs SET purpose = 'OPERATION' WHERE id = 'run-s18-purpose-fault'")
    finally:
        conn.rollback()
        conn.close()


def test_existing_v6_database_replaces_old_inflight_update_trigger(selected_migrated):
    _, db_file, shift_id, _, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        conn.execute("DROP TRIGGER one_inflight_pivot_operation_update")
        conn.execute(
            "CREATE TRIGGER one_inflight_pivot_operation_update "
            "BEFORE UPDATE OF state ON runs BEGIN SELECT 1; END"
        )
        conn.commit()
        db.ensure_schema(conn)
        first = orchestrator.start_run(conn, shift_id, client_request_id="inflight-upgrade")
        conn.execute(
            "INSERT INTO runs (id, shift_id, artifact_version_id, request_batch_ref, "
            "shop_snapshot_ref, attempt_number, state, adapter, started_at, purpose, "
            "evidence_mode, selection_id, context_id) "
            "SELECT 'run-s18-old-trigger-fault', shift_id, artifact_version_id, "
            "request_batch_ref, shop_snapshot_ref, attempt_number + 1, state, adapter, "
            "started_at, 'EXPERIMENT', evidence_mode, selection_id, context_id "
            "FROM runs WHERE id = ?", (first.id,))
        with pytest.raises(sqlite3.IntegrityError, match="operation already in flight"):
            conn.execute("UPDATE runs SET purpose = 'OPERATION' WHERE id = 'run-s18-old-trigger-fault'")
    finally:
        conn.rollback()
        conn.close()


def test_selected_operation_database_limits_and_zero_output_retry(selected_migrated):
    _, db_file, shift_id, selection, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        first = orchestrator.start_run(conn, shift_id, client_request_id="empty-first")
        with pytest.raises(Exception, match="operation already in flight"):
            conn.execute(
                "INSERT INTO runs (id, shift_id, artifact_version_id, request_batch_ref, "
                "shop_snapshot_ref, attempt_number, state, adapter, started_at, purpose, "
                "evidence_mode, selection_id, context_id) "
                "SELECT 'run-s18-inflight-fault', shift_id, artifact_version_id, "
                "request_batch_ref, shop_snapshot_ref, attempt_number + 1, state, adapter, "
                "started_at, purpose, evidence_mode, selection_id, context_id "
                "FROM runs WHERE id = ?", (first.id,))
        conn.rollback()
        conn.execute(
            "INSERT INTO shifts (id, engagement_slug, seq, state, opened_at, opening_mode) "
            "SELECT 'bookshop-shift-s18-inflight', engagement_slug, seq + 1, state, "
            "opened_at, opening_mode FROM shifts WHERE id = ?", (shift_id,))
        with pytest.raises(sqlite3.IntegrityError, match="operation already in flight"):
            conn.execute(
                "INSERT INTO runs (id, shift_id, artifact_version_id, request_batch_ref, "
                "shop_snapshot_ref, attempt_number, state, adapter, started_at, purpose, "
                "evidence_mode, selection_id, context_id) "
                "SELECT 'run-s18-cross-shift-fault', 'bookshop-shift-s18-inflight', "
                "artifact_version_id, request_batch_ref, shop_snapshot_ref, 1, state, adapter, "
                "started_at, purpose, evidence_mode, selection_id, context_id "
                "FROM runs WHERE id = ?", (first.id,))
        conn.rollback()
        repo.update_run(conn, first.id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED,
                        orchestrator._now())
        conn.commit()
        second = orchestrator.start_run(conn, shift_id, client_request_id="empty-second")
        assert second.id != first.id and second.selection_id == selection["id"]
        assert second.context_id == first.context_id
        repo.update_run(conn, second.id, RunState.FAILED, ExecutorFailure.INTERNAL,
                        orchestrator._now())
        conn.commit()
        with pytest.raises(orchestrator.LifecycleError, match="two operational reservations"):
            orchestrator.start_run(conn, shift_id, client_request_id="third")
    finally:
        conn.close()


def test_selected_operation_partial_output_blocks_retry(selected_migrated):
    _, db_file, shift_id, _, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        first = orchestrator.start_run(conn, shift_id, client_request_id="partial-first")
        repo.insert_output(conn, RunOutput(
            id=f"{first.id}-out-1", run_id=first.id, request_ordinal=1,
            request_text="captured request", http_status=200, body=b"partial", elapsed_ms=1,
        ))
        repo.update_run(conn, first.id, RunState.FAILED, ExecutorFailure.CAPTURE_TRUNCATED,
                        orchestrator._now())
        conn.commit()
        assert orchestrator.board_snapshot(conn, "bookshop")["attempts_remaining"] == 0
        with pytest.raises(orchestrator.LifecycleError, match="zero captured outputs"):
            orchestrator.start_run(conn, shift_id, client_request_id="partial-second")
        assert len(repo.list_outputs(conn, first.id)) == 1
    finally:
        conn.close()


def test_selected_operation_changed_choice_blocks_zero_output_retry(selected_migrated):
    _, db_file, shift_id, _, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        first = orchestrator.start_run(conn, shift_id, client_request_id="choice-first")
        repo.update_run(conn, first.id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED,
                        orchestrator._now())
        prior = repo.get_latest_operating_selection(conn, "bookshop")
        repo.insert_operating_selection(conn, prior.model_copy(update={
            "id": "sel-s18-retry-change", "prior_selection_id": prior.id,
            "client_request_id": "changed-choice-for-retry",
        }))
        conn.commit()
        with pytest.raises(orchestrator.LifecycleError, match="retry selection or context changed"):
            orchestrator.start_run(conn, shift_id, client_request_id="choice-second")
    finally:
        conn.close()


def test_selected_operation_changed_context_blocks_zero_output_retry(
    selected_migrated, monkeypatch, tmp_path
):
    _, db_file, shift_id, _, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        first = orchestrator.start_run(conn, shift_id, client_request_id="context-first")
        repo.update_run(conn, first.id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED,
                        orchestrator._now())
        conn.commit()
        changed = tmp_path / "changed-public-state.json"
        changed.write_bytes(config.PIVOT_PUBLIC_STATE.read_bytes() + b"\n")
        monkeypatch.setattr(config, "PIVOT_PUBLIC_STATE", changed)
        with pytest.raises(orchestrator.LifecycleError, match="retry conditions changed"):
            orchestrator.start_run(conn, shift_id, client_request_id="context-second")
    finally:
        conn.close()


def test_selected_operation_prior_business_write_blocks_zero_output_retry(
    selected_migrated, monkeypatch,
):
    _, db_file, shift_id, _, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        first = orchestrator.start_run(conn, shift_id, client_request_id="event-first")
        original_context = repo.get_execution_context(conn, first.context_id)
        existing = repo.list_ledger_events(conn, "bookshop")
        event = chain.append([LedgerEventDraft(
            event_type=LedgerEventType.SALE_COMPLETED, cause_refs=(first.id,),
            payload={"synthetic_orders": 1},
        )], prev_hash=chain.next_prev_hash(existing), start_seq=chain.next_seq(existing))[0]
        repo.insert_ledger_event(conn, "bookshop", event)
        repo.update_run(conn, first.id, RunState.FAILED, ExecutorFailure.INTERNAL,
                        orchestrator._now())
        conn.commit()
        assert orchestrator.board_snapshot(conn, "bookshop")["attempts_remaining"] == 0
        # Hold the frozen context constant, so only the business-write guard can reject.
        monkeypatch.setattr(orchestrator, "freeze_diagnostic_context",
                            lambda *_args, **_kwargs: original_context)
        with pytest.raises(orchestrator.LifecycleError, match="no business write"):
            orchestrator.start_run(conn, shift_id, client_request_id="event-second")
    finally:
        conn.close()


@pytest.mark.parametrize("fault", ["checks", "events", "incidents", "terminal"])
def test_selected_operation_finalization_fault_is_atomic(selected_migrated, monkeypatch, fault):
    _, db_file, shift_id, _, _, _, _ = selected_migrated
    conn = db.connect(db_file)
    try:
        run = orchestrator.start_run(conn, shift_id, client_request_id=f"fault-{fault}")
        baseline_events = repo.list_ledger_events(conn, "bookshop")
        if fault == "incidents":
            original_reduce = orchestrator.reducer.reduce_operation
            def incident_draft(*args):
                drafts = original_reduce(*args)
                check = args[-1][0]
                return [LedgerEventDraft(event_type=LedgerEventType.INCIDENT_OPENED,
                                         cause_refs=(run.id, check.id, check.observed_ref),
                                         payload={"reason_code": "REQUIRED_TASK_MISSING"})]
            monkeypatch.setattr(orchestrator.reducer, "reduce_operation", incident_draft)
        target = {"checks": "insert_check_result", "events": "insert_ledger_event",
                  "incidents": "insert_incident", "terminal": "update_run"}[fault]
        original = getattr(repo, target)
        def break_write(*args, **kwargs):
            if fault != "terminal" or (len(args) > 2 and args[2] is RunState.FINALIZED):
                raise RuntimeError(f"fault at {fault}")
            return original(*args, **kwargs)
        monkeypatch.setattr(repo, target, break_write)
        with pytest.raises(RuntimeError, match=f"fault at {fault}"):
            orchestrator.execute_selected_operation(conn, run.id)
        assert repo.get_run(conn, run.id).state is RunState.FAILED
        assert repo.list_outputs(conn, run.id)
        assert repo.list_check_results(conn, run.id) == []
        assert repo.list_task_assessments(conn, run.id) == []
        assert repo.list_ledger_events(conn, "bookshop") == baseline_events
        assert all(item.opening_run_id != run.id for item in repo.list_incidents(conn, "bookshop"))
        replay = orchestrator.start_run(conn, shift_id, client_request_id=f"fault-{fault}")
        assert replay.id == run.id and replay.state is RunState.FAILED
        assert repo.list_ledger_events(conn, "bookshop") == baseline_events
    finally:
        conn.close()


def test_exact_choice_revalidates_and_never_changes_on_save_or_retry(session):
    source = session.attempt()
    assert source["state"] == "FINALIZED"
    a, b, comparison = _comparison(session.client, session.shift_id, source["id"])
    prior = session.board()["operating_selection"]["id"]
    path = f"/api/shifts/{session.shift_id}/selections"
    body = _choice(comparison, a, prior)
    assert session.client.post(path, json={**body, "expected_prior_selection_id": None}).status_code == 409
    assert session.client.post(path, json={**body, "selected_version_id": source["artifact_version_id"]}).status_code == 409
    assert session.client.post(path, json={**body, "rationale": "  "}).status_code == 409
    assert len(session.client.get("/api/engagements/bookshop/selections").json()) == 1

    chosen = session.client.post(path, json=body)
    assert chosen.status_code == 201, chosen.text
    selected = chosen.json()
    assert selected["selected_version_id"] == a["id"]
    assert selected["selected_content_hash"] == a["content_hash"]
    assert selected["retained_alternative_version_id"] == b["id"]
    assert selected["comparison_id"] == comparison["id"]
    assert selected["prior_selection_id"] == prior
    assert len(selected["requirement_set_hash"]) == 64
    assert session.client.post(path, json=body).json() == selected
    assert session.client.post(path, json={**body, "rationale": "different"}).status_code == 409
    board = session.board()
    assert board["operating_status"] == "SELECTED"
    assert board["operating_selection"]["id"] == selected["id"]
    assert board["latest_shift"]["operation_allowed"] is True
    assert len(session.client.get("/api/engagements/bookshop/selections").json()) == 2

    session.edit()
    frozen = session.freeze()
    after = session.board()
    assert after["latest_saved_version_id"] == frozen["id"]
    assert after["operating_selection"]["id"] == selected["id"]
    assert after["operating_selection"]["selected_version_id"] == a["id"]

    conn = db.connect(session.db_file)
    try:
        reservation = repo.get_exposure_reservation_for_experiment(conn, comparison["id"])
        orchestrator.retire_comparison_exposure(conn, reservation.id)
    finally:
        conn.close()
    invalid = session.board()
    assert invalid["operating_status"] == "INVALIDATED"
    assert invalid["operating_selection"]["id"] == selected["id"]
    assert invalid["latest_shift"]["operation_allowed"] is False
    assert session.client.post(f"/api/shifts/{session.shift_id}/runs").status_code == 409
    assert session.client.get("/api/engagements/bookshop/selections").json()[-1]["state"] == "INVALIDATED"


def test_choice_rejects_incomplete_drifted_and_changed_requirements(session, tmp_path, monkeypatch):
    source = session.attempt()
    a, _, comparison = _comparison(session.client, session.shift_id, source["id"])
    prior = session.board()["operating_selection"]["id"]
    path = f"/api/shifts/{session.shift_id}/selections"
    body = _choice(comparison, a, prior)

    conn = db.connect(session.db_file)
    try:
        conn.execute("UPDATE experiments SET state = 'PLANNED' WHERE id = ?", (comparison["id"],))
        conn.commit()
    finally:
        conn.close()
    assert session.client.post(path, json=body).status_code == 409
    conn = db.connect(session.db_file)
    try:
        conn.execute("UPDATE experiments SET state = 'FINALIZED' WHERE id = ?", (comparison["id"],))
        # This 409 is reached at the completeness guard: a changed content hash is
        # already candidate_A drift, so the comparison is NOT_COMPARABLE first.
        conn.execute("UPDATE artifact_versions SET content_hash = ? WHERE id = ?", ("f" * 64, a["id"]))
        conn.commit()
    finally:
        conn.close()
    assert session.client.post(path, json=body).status_code == 409
    conn = db.connect(session.db_file)
    try:
        conn.execute("UPDATE artifact_versions SET content_hash = ? WHERE id = ?", (a["content_hash"], a["id"]))
        conn.commit()
    finally:
        conn.close()
    new_mission = tmp_path / "changed-mission.json"
    new_mission.write_bytes(config.PIVOT_MISSION.read_bytes() + b"\n")
    monkeypatch.setattr(config, "PIVOT_MISSION", new_mission)
    assert session.client.post(path, json=body).status_code == 409
    assert len(session.client.get("/api/engagements/bookshop/selections").json()) == 1


def test_failed_first_choice_comparison_keeps_exposure_and_operation_block(tmp_path):
    original = tmp_path / "original.db"
    copied = tmp_path / "copy.db"
    create_v5_sample(original)
    shutil.copy2(original, copied)
    with TestClient(create_app(str(copied))) as client:
        shift_id = client.post("/api/engagements/bookshop/shifts").json()["id"]
        a, b, comparison = _comparison(client, shift_id, "run-v5-0001")
        conn = db.connect(copied)
        try:
            reservation = repo.get_exposure_reservation_for_experiment(conn, comparison["id"])
            before = repo.count_exposure_reservations(conn)
            orchestrator.retire_comparison_exposure(conn, reservation.id)
        finally:
            conn.close()
        refused = client.post(f"/api/shifts/{shift_id}/selections", json=_choice(comparison, a, None))
        assert refused.status_code == 409, refused.text
        assert client.post(f"/api/shifts/{shift_id}/runs").status_code == 409
        assert client.post("/api/engagements/bookshop/shifts").status_code == 409
        assert client.get("/api/engagements/bookshop/selections").json() == []
        retry = client.post(f"/api/shifts/{shift_id}/experiments", json={
            "kind": "QUALIFYING_COMPARISON",
            "investigation_id": client.get(f"/api/shifts/{shift_id}/investigations").json()["latest_investigation_id"],
            "candidate_a_version_id": a["id"],
            "candidate_b_version_id": b["id"],
            "declared_treatment": "try again",
            "client_request_id": "new-comparison-after-failure",
        })
        assert retry.status_code == 409
        conn = db.connect(copied)
        try:
            assert repo.count_exposure_reservations(conn) == before
            assert repo.get_exposure_reservation(conn, reservation.id).state == "INVALIDATED"
        finally:
            conn.close()


def test_new_operation_with_unknown_sealed_check_still_fails_closed(session):
    source = session.attempt()
    conn = db.connect(session.db_file)
    try:
        incident = repo.list_incidents(conn, config.BOOKSHOP_SLUG)[0]
        conn.execute("UPDATE check_results SET check_id = ? WHERE id = ?",
                     ("unknown-new-check", incident.check_result_id))
        conn.commit()
        with pytest.raises(InvalidSealedCase, match="no family file provides"):
            sealed_store.load_drawn_cases(conn, source["id"])
    finally:
        conn.close()


def test_first_choice_unlocks_migrated_shift_only_after_complete_comparison(tmp_path):
    original = tmp_path / "original.db"
    copied = tmp_path / "copy.db"
    create_v5_sample(original)
    original_bytes = original.read_bytes()
    shutil.copy2(original, copied)
    with TestClient(create_app(str(copied))) as client:
        opened = client.post("/api/engagements/bookshop/shifts")
        assert opened.status_code == 201, opened.text
        shift_id = opened.json()["id"]
        assert opened.json()["opening_mode"] == "LEGACY_FIRST_CHOICE"
        assert opened.json()["operation_allowed"] is False
        board = client.get("/api/engagements/bookshop/board").json()
        assert board["latest_run"] is not None, board
        assert board["latest_run"]["id"] == "run-v5-0001"
        assert board["latest_run"]["purpose"] == "LEGACY_OPERATION"
        assert board["requests_run"] == 1
        a, b, comparison = _comparison(client, shift_id, "run-v5-0001")
        assert client.get("/api/engagements/bookshop/board").json()["operating_selection"] is None
        body = _choice(comparison, b, None, key="first-choice", rationale="B passes the same requirements")
        selected = client.post(f"/api/shifts/{shift_id}/selections", json=body)
        assert selected.status_code == 201, selected.text
        assert selected.json()["prior_selection_id"] is None
        assert selected.json()["retained_alternative_version_id"] == a["id"]
        board = client.get("/api/engagements/bookshop/board").json()
        assert board["latest_shift"]["opening_mode"] == "LEGACY_FIRST_CHOICE"
        assert board["latest_shift"]["operation_allowed"] is True
        assert board["operating_selection"]["selected_version_id"] == b["id"]
        newer = _candidate(client, shift_id, "A")
        assert newer["id"] != b["id"]
        ledger_before = client.get("/api/engagements/bookshop/ledger").json()["events"]
        started = client.post(f"/api/shifts/{shift_id}/runs",
                              json={"client_request_id": "first-choice-operation"})
        assert started.status_code == 202, started.text
        assert started.json()["artifact_version_id"] == b["id"]
        assert started.json()["selection_id"] == selected.json()["id"]
        assert client.get(f"/api/runs/{started.json()['id']}").json()["state"] == "FINALIZED"
        events = client.get("/api/engagements/bookshop/ledger").json()["events"]
        assert [event["event_type"] for event in events[len(ledger_before):]] == ["SALE_COMPLETED"]
        assert len(events) > len(ledger_before)
        assert any(event["derivation"] and event["derivation"]["run_id"] == started.json()["id"]
                   for event in events[len(ledger_before):])
        assert client.get(f"/api/runs/{started.json()['id']}/checks").json()
        assert client.get("/api/incidents/BWB-v5-01").json()["state"] == "CLOSED_UNRESOLVED"
        closed = client.post(f"/api/shifts/{shift_id}/close")
        assert closed.status_code == 200, closed.text
        assert closed.json()["state"] == "closed"
        replay = client.post(f"/api/shifts/{shift_id}/selections", json=body)
        assert replay.status_code == 201, replay.text
        assert replay.json() == selected.json()
        assert len(client.get("/api/engagements/bookshop/selections").json()) == 1
        changed = client.post(f"/api/shifts/{shift_id}/selections", json={
            **body, "rationale": "a different choice after close",
        })
        assert changed.status_code == 409, changed.text
        fresh = client.post(f"/api/shifts/{shift_id}/selections", json={
            **body, "client_request_id": "new-choice-after-close",
        })
        assert fresh.status_code == 409, fresh.text
        next_shift = client.post("/api/engagements/bookshop/shifts")
        assert next_shift.status_code == 201, next_shift.text
        foreign = client.post(
            f"/api/shifts/{next_shift.json()['id']}/selections", json=body)
        assert foreign.status_code == 409, foreign.text
    assert original.read_bytes() == original_bytes


def test_choice_refuses_an_ineligible_candidate_and_still_accepts_the_eligible_one(
    session, monkeypatch
):
    """Obligation 25's eligible arm, substituted only at the recompute boundary.

    Stored evidence cannot reach COMPLETE plus ineligible offline: editing a
    recorded assessment adds ``public_assessment`` drift and editing
    ``resource_limits_json`` adds ``frozen_context`` drift. Every stored row here
    is real; only the recomputed outcome reports A as mandatorily blocked.
    """
    source = session.attempt()
    a, b, comparison = _comparison(session.client, session.shift_id, source["id"])
    prior = session.board()["operating_selection"]["id"]
    path = f"/api/shifts/{session.shift_id}/selections"
    real_outcome = orchestrator._comparison_outcome

    def ineligible_a(conn, experiment, context, slots):
        outcome = real_outcome(conn, experiment, context, slots)
        if experiment.id != comparison["id"]:
            return outcome
        assert outcome.status == "COMPLETE", outcome.status
        return outcome.model_copy(update={"eligibility": tuple(
            item.model_copy(update={
                "eligible": False,
                "blocking_reason_codes": ("mandatory_public_rule",),
            }) if item.candidate_label == "A" else item
            for item in outcome.eligibility
        )})

    monkeypatch.setattr(orchestrator, "_comparison_outcome", ineligible_a)
    refused = session.client.post(
        path, json=_choice(comparison, a, prior, key="choice-ineligible"))
    assert refused.status_code == 409, refused.text
    assert len(session.client.get("/api/engagements/bookshop/selections").json()) == 1
    chosen = session.client.post(path, json=_choice(
        comparison, b, prior, key="choice-eligible", rationale="B answers the required tasks"))
    assert chosen.status_code == 201, chosen.text
    assert chosen.json()["selected_version_id"] == b["id"]
    assert chosen.json()["retained_alternative_version_id"] == a["id"]
    assert len(session.client.get("/api/engagements/bookshop/selections").json()) == 2


def test_choice_refuses_a_candidate_version_owned_by_another_shift(tmp_path):
    """The ownership arm of the changed-version guard, reached on its own.

    A content-hash change is already caught earlier as candidate drift, so only
    ``version.shift_id`` reaches this arm while the comparison stays COMPLETE.
    """
    original = tmp_path / "original.db"
    copied = tmp_path / "copy.db"
    create_v5_sample(original)
    shutil.copy2(original, copied)
    with TestClient(create_app(str(copied))) as client:
        shift_id = client.post("/api/engagements/bookshop/shifts").json()["id"]
        a, _, comparison = _comparison(client, shift_id, "run-v5-0001")
        path = f"/api/shifts/{shift_id}/selections"
        body = _choice(comparison, a, None, key="ownership")
        conn = db.connect(copied)
        try:
            conn.execute("UPDATE artifact_versions SET shift_id = 'bookshop-shift-01' WHERE id = ?",
                         (a["id"],))
            conn.commit()
        finally:
            conn.close()
        refused = client.post(path, json=body)
        assert refused.status_code == 409, refused.text
        assert client.get("/api/engagements/bookshop/selections").json() == []
        conn = db.connect(copied)
        try:
            conn.execute("UPDATE artifact_versions SET shift_id = ? WHERE id = ?",
                         (shift_id, a["id"]))
            conn.commit()
        finally:
            conn.close()
        assert client.post(path, json=body).status_code == 201


def test_legacy_investigation_exception_is_narrow(tmp_path):
    """The approved S6.0 exception admits only the prior closed v5 shift's own run.

    Each stored mutation falsifies exactly one conjunct, with the unmutated 201
    before and after as the positive control. Two conjuncts are not independently
    falsifiable offline: the public API cannot open a successor while its
    predecessor is still open, so ``state == "closed"`` never varies, and the v5
    sample holds one prior shift, so ``seq == shift.seq - 1`` never varies.
    """
    original = tmp_path / "original.db"
    copied = tmp_path / "copy.db"
    create_v5_sample(original)
    shutil.copy2(original, copied)
    with TestClient(create_app(str(copied))) as client:
        shift_id = client.post("/api/engagements/bookshop/shifts").json()["id"]
        path = f"/api/shifts/{shift_id}/investigations"

        def investigate(key):
            return client.post(path, json={
                "source_run_id": "run-v5-0001", "source_request_ordinal": 1,
                "cause": "the old response omits a required task",
                "falsifier": "the frozen request receives every required task result",
                "public_test": "check every required task independently",
                "client_request_id": key,
            })

        def mutate(sql, params):
            conn = db.connect(copied)
            try:
                conn.execute(sql, params)
                conn.commit()
            finally:
                conn.close()

        assert investigate("legacy-positive").status_code == 201
        mutate("UPDATE shifts SET opening_mode = 'STANDARD' WHERE id = 'bookshop-shift-01'", ())
        assert investigate("legacy-opening-mode").status_code == 409
        mutate("UPDATE shifts SET opening_mode = NULL WHERE id = 'bookshop-shift-01'", ())
        mutate("UPDATE runs SET purpose = 'OPERATION' WHERE id = 'run-v5-0001'", ())
        assert investigate("legacy-run-purpose").status_code == 409
        mutate("UPDATE runs SET purpose = 'LEGACY_OPERATION' WHERE id = 'run-v5-0001'", ())
        assert investigate("legacy-restored").status_code == 201
        conn = db.connect(copied)
        try:
            assert repo.count_investigations(conn) == 2
        finally:
            conn.close()
