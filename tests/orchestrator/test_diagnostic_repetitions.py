"""S44: retained repetitions, never fixture replies presented as live evidence."""

import base64
import json
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from demos import s43_task_plan
from shiftwork import config, experiments, orchestrator
from shiftwork.app import create_app
from shiftwork.executor.base import RawCapture, RawObservation, RunResult
from shiftwork.store import db, repo


@pytest.fixture(scope="module")
def replies():
    return [s43_task_plan.run_starter_offline(reply)["responses"][0]["body"]
            for _, reply in s43_task_plan.CASES[:2]]


@pytest.fixture()
def repeated(tmp_path, monkeypatch, replies):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-only-token")
    monkeypatch.setenv("NEBIUS_PROJECT_ID", "test-only-project")
    path = tmp_path / "repetitions.db"
    from shiftwork.hosted import diagnostic_budget
    app = create_app(str(path), executor="tokenfactory", live_diagnostic_budget=diagnostic_budget)
    calls = []

    async def execute(adapter, request):
        index = len(calls) % 2
        calls.append(request)
        plan = json.loads(s43_task_plan.CASES[index][1])["plan"]
        return RunResult(captures=(RawCapture(request_ordinal=1, http_status=200,
            body=replies[index].encode(), elapsed_ms=10, transport_error=None, log_ref=None),), executor_ref=None,
            failure=None, wall_ms=10, observations=(RawObservation(kind="INFERENCE_RESULT",
                public_payload={"source": "controller_verified", "plan": plan,
                                "plan_failure": None, "request_ordinal": 1},
                raw_payload={"provider_response": {"choices": [{"message": {
                    "content": s43_task_plan.CASES[index][1]}}]}}),))

    monkeypatch.setattr(orchestrator.TokenFactoryAdapter, "execute", execute)
    with TestClient(app) as client:
        opened = client.post("/api/engagements/bookshop/shifts")
        assert opened.status_code == 201, opened.text
        shift = opened.json()["id"]
        frozen = client.post(f"/api/shifts/{shift}/artifact/versions",
                             json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
        assert frozen.status_code == 201, frozen.text
        yield client, path, shift, frozen.json()["id"], calls


def reserve(repeated, count=2, key="repeated"):
    client, _, shift, version, _ = repeated
    return client.post(f"/api/shifts/{shift}/experiments", json={
        "kind": "DIAGNOSTIC", "candidate_a_version_id": version,
        "client_request_id": key, "public_repetitions": count})


def test_each_repetition_is_retained_and_rate_counts_the_actual_miss(repeated):
    response = reserve(repeated)
    assert response.status_code == 202, response.text
    view = repeated[0].get(f'/api/experiments/{response.json()["id"]}').json()
    assert len(view["trials"]) == 2, "each declared repetition must retain its own trial"
    assert len({row["run_id"] for row in view["trials"]}) == 2
    assert all(row["artifact_version_id"] == repeated[3] for row in view["trials"]), "retained trials must publish their exact version binding"
    assert view["public_repetitions"] == 2
    assert view["repetition_summary"]["retained_repetitions"] == 2
    rates = {row["task_id"]: row for row in view["repetition_summary"]["tasks"]}
    assert set(rates) == {"collection", "alternative"}, "only required tasks have miss rates"
    assert rates["alternative"]["misses"] == 1, "the displayed rate must count the missing alternative"
    assert rates["alternative"]["total"] == 2
    assert rates["collection"]["misses"] == 0
    assert len(repeated[4]) == 2
    assert view["eligible"] is False
    with db.connect(repeated[1]) as conn:
        assert conn.execute("SELECT COUNT(*) FROM rotation_draws").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0] == 0
        for trial in view["trials"]:
            raw = repo.list_observations(conn, trial["run_id"])[0].raw_payload_ref
            assert "provider_response" in json.loads(base64.b64decode(raw.split(",", 1)[1]))


def test_repetition_count_changed_after_results_is_refused(repeated):
    first = reserve(repeated)
    assert first.status_code == 202, first.text
    changed = reserve(repeated, count=3)
    assert changed.status_code == 409, "a published declaration cannot change under the same request key"
    assert len(repeated[4]) == 2
    same = reserve(repeated)
    assert same.status_code == 202
    assert len(repeated[4]) == 2, "an idempotent replay must send no additional calls"


@pytest.mark.parametrize("count", [0, 11, True, 2.5])
def test_invalid_repetition_declaration_reserves_nothing(repeated, count):
    response = reserve(repeated, count=count)
    assert response.status_code == 422
    assert repeated[4] == []


def test_summary_refuses_a_missing_retained_repetition(repeated):
    created = reserve(repeated)
    assert created.status_code == 202, created.text
    with db.connect(repeated[1]) as conn:
        experiment = repo.get_experiment(conn, created.json()["id"])
        runs = [r for r in repo.list_runs_for_shift(conn, repeated[2])
                if r.experiment_id == experiment.id]
        conn.execute("DELETE FROM task_assessments WHERE run_id = ?", (runs[-1].id,))
        conn.commit()
        with pytest.raises(orchestrator.LifecycleError, match="retained"):
            experiments.repetition_summary(conn, experiment)


def test_summary_refuses_a_missing_run_row(repeated):
    created = reserve(repeated)
    assert created.status_code == 202, created.text
    with db.connect(repeated[1]) as conn:
        experiment = repo.get_experiment(conn, created.json()["id"])
        run = experiments.experiment_run(conn, experiment.id)
        conn.execute("UPDATE runs SET experiment_id = NULL WHERE id = ?", (run.id,))
        conn.commit()
        with pytest.raises(orchestrator.LifecycleError, match="retained"):
            experiments.repetition_summary(conn, experiment)


def test_summary_refuses_an_unexpected_assessment_row(repeated):
    created = reserve(repeated)
    assert created.status_code == 202, created.text
    with db.connect(repeated[1]) as conn:
        experiment = repo.get_experiment(conn, created.json()["id"])
        run = experiments.experiment_run(conn, experiment.id)
        row = repo.list_task_assessment_models(conn, run.id)[0]
        repo.insert_task_assessment(conn, assessment_id="unexpected", run_id=run.id,
            assessment=row.model_copy(update={"task_id": "unexpected"}), assessed_at=orchestrator._now())
        conn.commit()
        with pytest.raises(orchestrator.LifecycleError, match="retained"):
            experiments.repetition_summary(conn, experiment)


def test_summary_refuses_a_missing_model_reply(repeated):
    created = reserve(repeated)
    assert created.status_code == 202, created.text
    with db.connect(repeated[1]) as conn:
        experiment = repo.get_experiment(conn, created.json()["id"])
        run = experiments.experiment_run(conn, experiment.id)
        conn.execute("DROP TRIGGER execution_observations_no_delete")
        conn.execute("DELETE FROM execution_observations WHERE run_id = ?", (run.id,))
        conn.commit()
        with pytest.raises(orchestrator.LifecycleError, match="retained"):
            experiments.repetition_summary(conn, experiment)


@pytest.mark.parametrize("raw", ["not-json", '{"provider_response":{"choices":[{"message":{}}]}}', "wrong-prefix"],
                         ids=["bad-json", "missing-content", "wrong-prefix"])
def test_summary_refuses_an_unreadable_retained_model_reply(repeated, raw):
    created = reserve(repeated)
    assert created.status_code == 202, created.text
    with db.connect(repeated[1]) as conn:
        experiment = repo.get_experiment(conn, created.json()["id"])
        run = experiments.experiment_run(conn, experiment.id)
        conn.execute("DROP TRIGGER execution_observations_no_update")
        prefix = "data:application/json;base64,"
        if raw == "wrong-prefix":
            prefix = "data:text/plain;base64,"
            raw = '{"provider_response":{"choices":[{"message":{"content":"retained"}}]}}'
        conn.execute("UPDATE execution_observations SET raw_payload_ref = ? WHERE run_id = ?",
            (prefix + base64.b64encode(raw.encode()).decode(), run.id))
        conn.commit()
        with pytest.raises(orchestrator.LifecycleError, match="retained"):
            experiments.repetition_summary(conn, experiment)


def test_api_refuses_repetitions_without_a_meter(repeated, monkeypatch):
    repeated[0].app.state.live_diagnostic_budget = None
    monkeypatch.setattr(experiments, "execute_experiment_task", lambda *args: None)
    response = reserve(repeated)
    assert response.status_code == 409, "a repeated live batch needs its own bounded meter"
    assert repeated[4] == []


def test_direct_execution_refuses_repetitions_without_a_meter(repeated):
    # Reserve directly so no background task executes it first.
    with db.connect(repeated[1]) as conn:
        experiment = experiments.create_diagnostic_experiment(conn, repeated[2],
            candidate_version_id=repeated[3], investigation_id=None,
            client_request_id="direct", adapter="tokenfactory", public_repetitions=2)
        run = experiments.experiment_run(conn, experiment.id)
        with pytest.raises(orchestrator.LifecycleError, match="bounded"):
            experiments.execute_experiment(conn, run.id)
    assert repeated[4] == []


def test_restart_marks_every_unfinished_repetition_failed_without_retry(repeated):
    with db.connect(repeated[1]) as conn:
        experiment = experiments.create_diagnostic_experiment(conn, repeated[2],
            candidate_version_id=repeated[3], investigation_id=None,
            client_request_id="interrupted", adapter="tokenfactory", public_repetitions=2)
        orchestrator.reconcile_interrupted(conn)
        view = experiments.experiment_view(conn, experiment.id)
        assert view["state"] == "FAILED", "restart must terminate the whole diagnostic"
        assert all(trial["state"] == "FAILED" for trial in view["trials"])
        assert view["repetition_summary"] is None
    assert repeated[4] == []


def test_summary_refuses_missing_capture_instead_of_calling_it_a_model_miss(repeated):
    created = reserve(repeated)
    assert created.status_code == 202, created.text
    with db.connect(repeated[1]) as conn:
        experiment = repo.get_experiment(conn, created.json()["id"])
        run = experiments.experiment_run(conn, experiment.id)
        conn.execute("DELETE FROM run_outputs WHERE run_id = ?", (run.id,))
        conn.commit()
        with pytest.raises(orchestrator.LifecycleError, match="retained"):
            experiments.repetition_summary(conn, experiment)


def test_changed_frozen_count_is_refused_even_if_storage_is_modified(repeated):
    created = reserve(repeated)
    assert created.status_code == 202, created.text
    with db.connect(repeated[1]) as conn:
        experiment = repo.get_experiment(conn, created.json()["id"])
        context = repo.get_execution_context(conn, experiment.context_id)
        conn.execute("UPDATE execution_contexts SET resource_limits_json = ? WHERE id = ?",
            (json.dumps({**context.resource_limits_json, "public_repetitions": 1}), context.id))
        conn.commit()
        with pytest.raises(orchestrator.LifecycleError, match="changed"):
            experiments.repetition_count(conn, experiment)


def test_meter_refuses_the_next_call_operation_and_overspend():
    from shiftwork.live_budget import LiveDiagnosticBudget
    budget = LiveDiagnosticBudget("nano", Decimal("1"), Decimal("1"),
        max_operations=2, max_calls=2, max_projected_usd=Decimal("1"))
    budget.preflight(model="nano", repetitions=2, requests=1)
    for _ in range(2):
        budget.before_operation()
        budget.before_inference("nano")
    with pytest.raises(ValueError, match="operation ceiling"):
        budget.before_operation()
    with pytest.raises(ValueError, match="call ceiling"):
        budget.before_inference("nano")
    assert budget.calls == 2 and budget.operations == 2
    unaffordable = LiveDiagnosticBudget("nano", Decimal("1000"), Decimal("1000"),
        max_operations=2, max_calls=2, max_projected_usd=Decimal("0.01"))
    with pytest.raises(ValueError, match="spend"):
        unaffordable.before_inference("nano")
    assert unaffordable.calls == 0, "spend must be refused before a call is sent"


def test_meter_preflight_refuses_wrong_model_and_unaffordable_batch():
    from shiftwork.live_budget import LiveDiagnosticBudget
    budget = LiveDiagnosticBudget("nano", Decimal("1"), Decimal("1"),
        max_operations=2, max_calls=2, max_projected_usd=Decimal("1"))
    with pytest.raises(ValueError, match="unverified"):
        budget.preflight(model="other-model", repetitions=2, requests=1)
    budget.max_projected_usd = Decimal("0.01")
    with pytest.raises(ValueError, match="spend"):
        budget.preflight(model="nano", repetitions=2, requests=1)
    assert budget.calls == 0 and budget.operations == 0


@pytest.mark.parametrize("offline_binding", ["recorded", "tokenfactory"])
def test_recorded_capture_replays_exact_rows_without_credentials_or_eligibility(repeated, tmp_path,
                                                                             monkeypatch, offline_binding):
    from shiftwork import diagnostic_recording
    created = reserve(repeated)
    assert created.status_code == 202, created.text
    with db.connect(repeated[1]) as conn:
        recording = diagnostic_recording.export_recording(conn, created.json()["id"])
    path = tmp_path / "saved-captures.json"
    path.write_text(json.dumps(recording))
    monkeypatch.setenv("SHIFTWORK_DIAGNOSTIC_RECORDING", str(path))
    fresh = tmp_path / "offline.db"
    with TestClient(create_app(str(fresh), executor=offline_binding)) as client:
        shift = client.post("/api/engagements/bookshop/shifts").json()["id"]
        monkeypatch.delenv("NEBIUS_API_KEY")
        monkeypatch.delenv("NEBIUS_PROJECT_ID")
        with db.connect(fresh) as conn:
            run = orchestrator.start_run(conn, shift, executor="recorded", client_request_id="replay")
            orchestrator.execute_run(conn, run.id)
            view = experiments.experiment_view(conn, run.experiment_id)
            assert view["context_evidence_class"] == "RECORDED_INSPECTION"
            assert {trial["evidence_mode"] for trial in view["trials"]} == {"RECORDED_INSPECTION"}
            assert [trial["outputs"] for trial in view["trials"]] == [
                trial["outputs"] for trial in recording["trials"]]
            assert next(row for row in view["repetition_summary"]["tasks"]
                        if row["task_id"] == "alternative")["misses"] == 1
            assert view["eligible"] is False
            assert conn.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM rotation_draws").fetchone()[0] == 0
    assert len(repeated[4]) == 2, "recorded replay must make no executor/provider calls"


@pytest.mark.parametrize("fault", ["digest", "source", "starter", "mission", "missing_trial", "extra_trial", "duplicate_trial", "unfinished_trial"])
def test_recording_rejects_incomplete_or_mismatched_provenance(repeated, tmp_path, fault):
    from shiftwork import diagnostic_recording
    created = reserve(repeated)
    assert created.status_code == 202, created.text
    with db.connect(repeated[1]) as conn:
        recording = diagnostic_recording.export_recording(conn, created.json()["id"])
    if fault == "digest":
        recording["digest"] = "0" * 64
    else:
        if fault == "source": recording["source_evidence_mode"] = "TRUSTED_LOCAL"
        if fault == "starter":
            from shiftwork.domain import canonical
            from shiftwork.domain.models import ArtifactVersion
            recording["version"]["files"]["service.py"] += "\n# changed"
            version = ArtifactVersion.model_validate(recording["version"])
            recording["version"]["content_hash"] = canonical.artifact_content_hash(
                version.files, canonical.contract_params_json(version.contract), version.contract_catalog_hash)
        if fault == "mission": recording["context"]["mission_hash"] = "0" * 64
        if fault == "missing_trial": recording["trials"].pop()
        if fault == "extra_trial": recording["trials"].append(recording["trials"][0])
        if fault == "duplicate_trial": recording["trials"][-1] = recording["trials"][0]
        if fault == "unfinished_trial": recording["trials"][0]["state"] = "RESERVED"
        recording["digest"] = diagnostic_recording.recording_digest(recording)
    path = tmp_path / "bad-recording.json"
    path.write_text(json.dumps(recording))
    with pytest.raises(orchestrator.LifecycleError, match="recording"):
        diagnostic_recording.load_recording(path)


def test_recorded_replay_reuses_context_and_idempotency_but_keeps_the_two_slot_cap(repeated, tmp_path, monkeypatch):
    from shiftwork import diagnostic_recording
    created = reserve(repeated)
    assert created.status_code == 202, created.text
    with db.connect(repeated[1]) as conn:
        recording = diagnostic_recording.export_recording(conn, created.json()["id"])
    path = tmp_path / "replays.json"
    path.write_text(json.dumps(recording))
    monkeypatch.setenv("SHIFTWORK_DIAGNOSTIC_RECORDING", str(path))
    fresh = tmp_path / "replay-budget.db"
    with TestClient(create_app(str(fresh), executor="recorded")):
        pass
    with db.connect(fresh) as conn:
        shift = orchestrator.open_next_shift(conn, "bookshop", executor_name="recorded")
        first = orchestrator.start_run(conn, shift.id, executor="recorded", client_request_id="first")
        orchestrator.execute_run(conn, first.id)
        again = orchestrator.start_run(conn, shift.id, executor="recorded", client_request_id="first")
        assert again.id == first.id
        assert repo.count_runs_all(conn) == 2
        second = orchestrator.start_run(conn, shift.id, executor="recorded", client_request_id="second")
        orchestrator.execute_run(conn, second.id)
        assert second.context_id == first.context_id
        with pytest.raises(orchestrator.LifecycleError, match="budget"):
            orchestrator.start_run(conn, shift.id, executor="recorded", client_request_id="third")
        assert repo.count_runs_all(conn) == 4
