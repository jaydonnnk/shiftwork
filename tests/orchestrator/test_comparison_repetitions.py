"""S45 public repetitions. These are offline fixture checks, never model evidence."""

import json
import base64
from datetime import datetime, timezone
from pathlib import Path

import pytest

from shiftwork import comparison_flow, experiments, orchestrator
from shiftwork.domain.models import ExperimentKind, RunState, ExecutorFailure, ExecutionObservation, ObservationKind, RunOutput
from shiftwork.store import db, repo
from test_experiment_lifecycle import _comparison_session, TREATMENT


@pytest.fixture()
def comparison_session(session):
    a, b, investigation = _comparison_session(session)
    return session, a, b, investigation


def reserve(prepared, count=3, key="s45"):
    session, a, b, investigation = prepared
    return session.client.post(f"/api/shifts/{session.shift_id}/experiments", json={
        "kind": "QUALIFYING_COMPARISON", "candidate_a_version_id": a["id"],
        "candidate_b_version_id": b["id"], "investigation_id": investigation["id"],
        "declared_treatment": TREATMENT, "client_request_id": key,
        "public_repetitions": count})


def view(prepared, experiment_id):
    response = prepared[0].client.get(f"/api/experiments/{experiment_id}")
    assert response.status_code == 200, response.text
    return response.json()


def reserve_raw(prepared, count=3, adapter="local_process"):
    session, a, b, investigation = prepared
    with db.connect(session.db_file) as conn:
        return comparison_flow.create_qualifying_comparison(conn, session.shift_id,
            candidate_a_version_id=a["id"], candidate_b_version_id=b["id"],
            investigation_id=investigation["id"], declared_treatment=TREATMENT,
            client_request_id="s45-raw", adapter=adapter, public_repetitions=count)


def test_all_repetitions_are_reserved_before_any_result(comparison_session):
    experiment = reserve_raw(comparison_session)
    with db.connect(comparison_session[0].db_file) as conn:
        context = repo.get_execution_context(conn, experiment.context_id)
        assert context.resource_limits_json["public_repetitions"] == 3, "the repetition declaration must be frozen before results"
        slots = repo.list_trial_slots(conn, experiment.id)
        runs = [run for slot in slots for run in repo.list_slot_runs(conn, slot.id)]
        assert len(runs) == 18, "all declared public runs must be reserved atomically before any result"
        assert all(run.state is RunState.QUEUED for run in runs)
        assert all(len(repo.list_slot_runs(conn, slot.id)) == 3 for slot in slots)


def test_three_public_repetitions_keep_exact_runs_and_one_protected_phase(comparison_session, monkeypatch):
    from shiftwork.executor.local_process import LocalProcessAdapter
    execute = LocalProcessAdapter.execute
    calls = []
    states = []

    async def observed(adapter, request):
        calls.append(request)
        states.append(Path(request.shop_snapshot_ref).read_bytes())
        return await execute(adapter, request)

    monkeypatch.setattr(LocalProcessAdapter, "execute", observed)
    with db.connect(comparison_session[0].db_file) as conn:
        ledger_before = [tuple(row) for row in conn.execute("SELECT * FROM ledger_events ORDER BY seq")]
    created = reserve(comparison_session)
    assert created.status_code == 202, "S45 must admit three public repetitions"
    result = view(comparison_session, created.json()["id"])
    assert result["public_repetitions"] == 3
    assert len(calls) == 24, "three public workspaces and one protected workspace per slot"
    assert [r.single_request_ordinal for r in calls] == [None, None, None, 3] * 6, (
        "the protected phase must run once after all frozen public repetitions")
    assert len({r.shop_snapshot_ref for r in calls}) == 24, "every phase must use a fresh workspace"
    for offset in range(0, 24, 4):
        assert len({r.request_batch_bytes for r in calls[offset:offset + 3]}) == 1, "every public repetition must use the same frozen batch"
        assert states[offset] == states[offset + 1] == states[offset + 2], "public starting state must reset identically"
    assert result["shared_public_denominator_requests"] == 18, "only public repetitions enter the public denominator"
    assert result["protected_denominator_requests_per_candidate"] == 3
    assert result["outcome"]["status"] == "COMPLETE"
    assert all(row["eligible"] for row in result["outcome"]["eligibility"])
    retained = [r for trial in result["trials"] for r in trial["repetitions"]]
    assert len(retained) == len({r["run_id"] for r in retained}) == 18, (
        "each declared repetition must retain its own exact run")
    assert all(r["state"] == "COMPLETE" and len(r["outputs"]) == 2 for r in retained)
    assert all(len(r["task_assessments"]) >= 4 for r in retained)
    assert all(len(trial["repetitions"]) == 3 for trial in result["trials"])
    for candidate in result["repetition_summary"]["candidates"]:
        assert (candidate["passed"], candidate["retained"], candidate["declared"]) == (9, 9, 9), (
            "the displayed pass rate must count all retained mandatory assessments")
    with db.connect(comparison_session[0].db_file) as conn:
        slots = repo.list_trial_slots(conn, result["id"])
        assert len(slots) == 6
        for slot in slots:
            assert len(repo.list_outputs(conn, slot.run_id)) == 3
        assert [tuple(row) for row in conn.execute("SELECT * FROM ledger_events ORDER BY seq")] == ledger_before


def test_repetition_count_changed_after_results_is_refused(comparison_session):
    first = reserve(comparison_session)
    assert first.status_code == 202, "S45 comparison repetitions must be admitted"
    changed = reserve(comparison_session, 2)
    assert changed.status_code == 409, "a published comparison count cannot change under its request key"
    with db.connect(comparison_session[0].db_file) as conn:
        before = repo.count_runs_all(conn)
    replay = reserve(comparison_session)
    assert replay.status_code == 202
    with db.connect(comparison_session[0].db_file) as conn:
        assert repo.count_runs_all(conn) == before, "idempotent replay must not reserve new repetitions"


@pytest.mark.parametrize("count", [0, 4, 10, True, 1.5])
def test_comparison_repetition_bounds_reserve_nothing(comparison_session, count):
    with db.connect(comparison_session[0].db_file) as conn:
        before = repo.count_experiments_for_shift(conn, comparison_session[0].shift_id, ExperimentKind.QUALIFYING_COMPARISON)
    response = reserve(comparison_session, count)
    assert response.status_code == 422
    with db.connect(comparison_session[0].db_file) as conn:
        assert repo.count_experiments_for_shift(conn, comparison_session[0].shift_id, ExperimentKind.QUALIFYING_COMPARISON) == before


def test_unequal_retained_repetition_counts_are_incomplete(comparison_session):
    created = reserve(comparison_session)
    assert created.status_code == 202, "S45 comparison repetitions must be admitted"
    result = view(comparison_session, created.json()["id"])
    target = result["trials"][0]["repetitions"][-1]["run_id"]
    with db.connect(comparison_session[0].db_file) as conn:
        conn.execute("UPDATE runs SET trial_slot_id = NULL WHERE id = ?", (target,))
        conn.commit()
    changed = view(comparison_session, result["id"])
    assert changed["outcome"]["status"] == "INCOMPLETE", "unequal counts cannot qualify either candidate"
    assert not any(row["eligible"] for row in changed["outcome"]["eligibility"])
    rates = changed["repetition_summary"]["candidates"]
    assert sorted(row["retained"] for row in rates) == [8, 9]


def test_one_failed_repetition_blocks_eligibility(comparison_session, monkeypatch):
    from shiftwork.executor.local_process import LocalProcessAdapter
    execute = LocalProcessAdapter.execute
    public_calls = 0

    async def one_failure(adapter, request):
        nonlocal public_calls
        result = await execute(adapter, request)
        if request.single_request_ordinal is None:
            public_calls += 1
            if public_calls == 2:
                captures = list(result.captures)
                body = json.loads(captures[0].body)
                body["task_results"] = [r for r in body["task_results"] if r["task_id"] != "collection"]
                captures[0] = captures[0].model_copy(update={"body": json.dumps(body).encode()})
                result = result.model_copy(update={"captures": tuple(captures)})
        return result

    monkeypatch.setattr(LocalProcessAdapter, "execute", one_failure)
    created = reserve(comparison_session)
    assert created.status_code == 202, "S45 comparison repetitions must be admitted"
    result = view(comparison_session, created.json()["id"])
    assert result["outcome"]["status"] == "COMPLETE"
    eligibility = {r["candidate_label"]: r for r in result["outcome"]["eligibility"]}
    assert eligibility["A"]["eligible"] is False, "one failed mandatory repetition must block its candidate"
    assert eligibility["B"]["eligible"] is True, "the fully passing alternative remains eligible"
    rates = {r["candidate_label"]: r for r in result["repetition_summary"]["candidates"]}
    assert rates["A"]["passed"] == 8 and rates["B"]["passed"] == 9, (
        "the shown rate must count the failed retained repetition")


def test_changed_retained_repetition_changes_the_shown_rate(comparison_session):
    created = reserve(comparison_session)
    assert created.status_code == 202, "S45 comparison repetitions must be admitted"
    original = view(comparison_session, created.json()["id"])
    run = original["trials"][0]["repetitions"][-1]["run_id"]
    with db.connect(comparison_session[0].db_file) as conn:
        conn.execute("UPDATE task_assessments SET mandatory_pass = 0 WHERE run_id = ? AND task_id = 'collection'", (run,))
        conn.commit()
    changed = view(comparison_session, original["id"])
    assert changed["repetition_summary"]["candidates"][0]["passed"] == 8, (
        "the shown rate must come from retained rows, not a cached summary")
    assert not changed["eligible"], "tampered assessments must fail deterministic re-assessment"


def test_direct_comparison_bound_refuses_before_reservation(comparison_session):
    with pytest.raises(orchestrator.LifecycleError, match="comparison public repetitions must be from 1 to 3"):
        reserve_raw(comparison_session, 4)


def test_protected_failure_keeps_public_rate_and_blocks_only_its_candidate(comparison_session, monkeypatch):
    from shiftwork.executor.local_process import LocalProcessAdapter
    execute = LocalProcessAdapter.execute
    count = 0

    async def fail_protected(adapter, request):
        nonlocal count
        result = await execute(adapter, request)
        if request.single_request_ordinal is not None:
            count += 1
            if count == 1:
                capture = result.captures[0]
                body = json.loads(capture.body)
                body["task_results"] = []
                result = result.model_copy(update={"captures": (capture.model_copy(update={"body": json.dumps(body).encode()}),)})
        return result

    monkeypatch.setattr(LocalProcessAdapter, "execute", fail_protected)
    response = reserve(comparison_session)
    assert response.status_code == 202
    result = view(comparison_session, response.json()["id"])
    assert [row["passed"] for row in result["repetition_summary"]["candidates"]] == [9, 9], "protected failure cannot alter a public pass rate"
    assert [row["eligible"] for row in result["outcome"]["eligibility"]] == [False, True]
    assert [row["protected_failed"] for row in result["outcome"]["candidate_metrics"]] == [1, 0]


@pytest.mark.parametrize("field", ["artifact_version_id", "context_id", "experiment_id", "state", "adapter", "evidence_mode", "purpose", "count", "primary-order"])
def test_changed_queued_repetition_binding_sends_no_executor_call(comparison_session, monkeypatch, field):
    experiment = reserve_raw(comparison_session)
    with db.connect(comparison_session[0].db_file) as conn:
        slot = repo.list_trial_slots(conn, experiment.id)[0]
        runs = repo.list_slot_runs(conn, slot.id)
        if field == "artifact_version_id": replacement = comparison_session[2]["id"]
        elif field == "context_id":
            foreign = repo.get_execution_context(conn, runs[0].context_id).model_copy(update={"id": "context-foreign", "content_hash": "0" * 64})
            repo.insert_execution_context(conn, foreign)
            replacement = foreign.id
        elif field == "experiment_id":
            foreign = experiment.model_copy(update={"id": "experiment-foreign", "client_request_id": "foreign", "content_hash": "0" * 64})
            repo.insert_experiment(conn, foreign)
            replacement = foreign.id
        elif field == "adapter": replacement = "recorded"
        elif field == "evidence_mode": replacement = "RECORDED_INSPECTION"
        elif field == "purpose": replacement = "OPERATION"
        else: replacement = RunState.FINALIZED.value
        if field == "count": conn.execute("UPDATE runs SET trial_slot_id = NULL WHERE id = ?", (runs[-1].id,))
        elif field == "primary-order": repo.update_trial_slot(conn, slot.id, run_id=runs[-1].id)
        else: conn.execute(f"UPDATE runs SET {field} = ? WHERE id = ?", (replacement, runs[-1].id))
        conn.commit()
        slot = repo.get_trial_slot(conn, slot.id)
        called = []
        class InstrumentedCall(Exception):
            pass
        async def no_network(adapter, request):
            called.append(request)
            raise InstrumentedCall("stop the spy after the observed forbidden invocation")
        monkeypatch.setattr(orchestrator.LocalProcessAdapter, "execute", no_network)
        try:
            comparison_flow.execute_comparison_slot(conn, slot)
        except InstrumentedCall:
            pass
        assert called == [], "a changed queued repetition binding must be refused before execution"


def test_repetition_driver_error_terminalizes_its_pending_runs(comparison_session, monkeypatch):
    from shiftwork.executor.local_process import LocalProcessAdapter
    execute = LocalProcessAdapter.execute
    count = 0

    async def broken(adapter, request):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("operator-injected driver fault")
        return await execute(adapter, request)

    experiment = reserve_raw(comparison_session)
    monkeypatch.setattr(LocalProcessAdapter, "execute", broken)
    with db.connect(comparison_session[0].db_file) as conn:
        slot = repo.list_trial_slots(conn, experiment.id)[0]
        with pytest.raises(RuntimeError, match="operator-injected driver fault"):
            comparison_flow.execute_comparison(conn, experiment.id)
        assert len(repo.list_outputs(conn, slot.run_id)) == 2, "a completed public result must survive the next driver's exception"
        assert repo.get_run_assessment(conn, slot.run_id) is not None
        assert all(run.state is RunState.FAILED for run in repo.list_slot_runs(conn, slot.id)), (
            "a stopped repetition must leave no pending or RUNNING run in its failed slot")
        assert count == 2, "a driver error must stop before any further phase"
        projected = experiments.experiment_view(conn, experiment.id)
        assert projected["repetition_summary"]["candidates"][0]["retained"] == 1, (
            "unexecuted failed reservations cannot count as retained evidence")


def test_protected_transport_failure_does_not_lower_a_completed_public_rate(comparison_session, monkeypatch):
    from shiftwork.executor.local_process import LocalProcessAdapter
    from shiftwork.executor.base import RunResult
    execute = LocalProcessAdapter.execute
    failed = False

    async def protected_failure(adapter, request):
        nonlocal failed
        if request.single_request_ordinal is not None and not failed:
            failed = True
            return RunResult(captures=(), observations=(), executor_ref=None,
                failure=ExecutorFailure.CAPTURE_TRUNCATED, wall_ms=1)
        return await execute(adapter, request)

    monkeypatch.setattr(LocalProcessAdapter, "execute", protected_failure)
    created = reserve(comparison_session)
    assert created.status_code == 202
    result = view(comparison_session, created.json()["id"])
    assert [row["passed"] for row in result["repetition_summary"]["candidates"]] == [9, 9], (
        "a protected transport failure cannot lower a fully retained public pass rate")
    assert result["protected_counts"]["A"]["missing"] == 1
    assert result["outcome"]["status"] == "INCOMPLETE" and not result["eligible"]


def test_repeated_live_slot_requires_a_meter_before_execution(comparison_session, monkeypatch):
    from shiftwork.executor.base import RunResult
    monkeypatch.setenv("NEBIUS_API_KEY", "test-only-token")
    monkeypatch.setenv("NEBIUS_PROJECT_ID", "test-only-project")
    experiment = reserve_raw(comparison_session, adapter="tokenfactory")
    called = []

    class NoNetworkAdapter:
        async def execute(self, request):
            called.append(request)
            return RunResult(captures=(), observations=(), executor_ref=None,
                failure=ExecutorFailure.CAPTURE_TRUNCATED, wall_ms=1)

    monkeypatch.setattr(orchestrator, "service_adapter", lambda *args: NoNetworkAdapter())
    with db.connect(comparison_session[0].db_file) as conn:
        slot = repo.list_trial_slots(conn, experiment.id)[0]
        with pytest.raises(orchestrator.LifecycleError, match="repeated live comparison requires a bounded meter"):
            comparison_flow.execute_comparison_slot(conn, slot)
    assert called == [], "an unmetered repeated comparison must send no executor call"


@pytest.mark.parametrize("fault_at", [1, 2])
def test_live_driver_failure_stops_remaining_phases(comparison_session, monkeypatch, fault_at):
    from shiftwork.executor.base import RawCapture, RunResult
    from shiftwork.hosted import comparison_budget
    monkeypatch.setenv("NEBIUS_API_KEY", "test-only-token")
    monkeypatch.setenv("NEBIUS_PROJECT_ID", "test-only-project")
    experiment = reserve_raw(comparison_session, adapter="tokenfactory")
    called = []

    class NoNetworkAdapter:
        async def execute(self, request):
            called.append(request)
            if len(called) == fault_at:
                return RunResult(captures=(), observations=(), executor_ref=None,
                    failure=ExecutorFailure.CAPTURE_TRUNCATED, wall_ms=1)
            from shiftwork.executor.base import load_batch, load_single_request
            batch = (load_batch(request.request_batch, request.request_batch_bytes)
                if request.single_request_ordinal is None else
                (load_single_request(request.request_batch, request.request_batch_bytes, request.single_request_ordinal),))
            captures = tuple(RawCapture(request_ordinal=row.ordinal, http_status=200,
                body=json.dumps({"request_id": json.loads(row.body)["request_id"], "task_results": [],
                    "evidence_refs": [], "uncertainty_codes": []}).encode(),
                elapsed_ms=1, transport_error=None, log_ref=None)
                for row in batch)
            return RunResult(captures=captures, observations=(), executor_ref=None, failure=None, wall_ms=1)

    monkeypatch.setattr(orchestrator, "service_adapter", lambda *args: NoNetworkAdapter())
    with db.connect(comparison_session[0].db_file) as conn:
        with pytest.raises(orchestrator.LifecycleError, match="live comparison stopped after a driver failure"):
            comparison_flow.execute_comparison(conn, experiment.id, comparison_budget())
        assert len(called) == fault_at, "a live driver failure must stop before any further send"
        assert repo.get_experiment(conn, experiment.id).state == "FAILED"


def test_public_reasoning_changes_the_view_but_never_the_outcome(comparison_session, monkeypatch):
    from shiftwork.gateway.redaction import serialized_contains
    created = reserve(comparison_session)
    assert created.status_code == 202
    result = view(comparison_session, created.json()["id"])
    run_id = result["trials"][0]["repetitions"][1]["run_id"]
    marker = "reasoning-oracle-counterexample"

    def raw(text):
        return "data:application/json;base64," + base64.b64encode(json.dumps({
            "provider_response": {"choices": [{"message": {"reasoning": text, "content": "{}"}}]}}).encode()).decode()

    with db.connect(comparison_session[0].db_file) as conn:
        repo.insert_observation(conn, ExecutionObservation(id=f"{run_id}-reasoning-test", run_id=run_id,
            request_ordinal=1, ordinal=100, kind=ObservationKind.INFERENCE_RESULT,
            public_payload_json={"source": "operator-authored test observation"},
            raw_payload_ref=raw("public-provider-evidence-before"), measured_at=datetime.now(timezone.utc)))
        conn.commit()
    before = view(comparison_session, result["id"])
    original = repo.list_observations

    def changed(conn, requested_run):
        return [row.model_copy(update={"raw_payload_ref": raw(marker)})
                if row.id == f"{run_id}-reasoning-test" else row
                for row in original(conn, requested_run)]

    monkeypatch.setattr(repo, "list_observations", changed)
    after = view(comparison_session, result["id"])
    assert serialized_contains({"public_payload_json": {"reasoning_text": marker}}, marker), (
        "the serialized-surface scanner must detect the oracle-test marker")
    assert serialized_contains(after["trials"][0]["repetitions"][1]["observations"], marker), (
        "the metamorphic test must change real projected public reasoning")
    assert before["outcome"] == after["outcome"], "provider reasoning must never set correctness, eligibility or metrics"


@pytest.mark.parametrize("field", ["artifact_version_id", "context_id", "evidence_mode", "adapter", "experiment_id", "purpose"])
def test_retained_repetition_binding_drift_blocks_eligibility(comparison_session, field):
    created = reserve(comparison_session)
    assert created.status_code == 202
    result = view(comparison_session, created.json()["id"])
    run_id = result["trials"][0]["repetitions"][1]["run_id"]
    with db.connect(comparison_session[0].db_file) as conn:
        if field == "artifact_version_id": replacement = comparison_session[2]["id"]
        elif field == "context_id":
            context = repo.get_execution_context(conn, repo.get_run(conn, run_id).context_id)
            repo.insert_execution_context(conn, context.model_copy(update={"id": "retained-foreign-context", "content_hash": "0" * 64}))
            replacement = "retained-foreign-context"
        elif field == "adapter": replacement = "recorded"
        elif field == "experiment_id":
            original = repo.get_experiment(conn, result["id"])
            foreign = original.model_copy(update={"id": "retained-foreign-experiment", "client_request_id": "retained-foreign", "content_hash": "0" * 64})
            repo.insert_experiment(conn, foreign)
            replacement = foreign.id
        elif field == "purpose": replacement = "OPERATION"
        else: replacement = "RECORDED_INSPECTION"
        conn.execute(f"UPDATE runs SET {field} = ? WHERE id = ?", (replacement, run_id))
        conn.commit()
    changed = view(comparison_session, result["id"])
    assert changed["outcome"]["status"] == "NOT_COMPARABLE", "every retained repetition must keep its frozen identity and executor"
    assert not changed["eligible"]


def test_additional_run_output_route_keeps_its_public_ordinal_boundary(comparison_session, monkeypatch):
    from shiftwork.gateway.redaction import serialized_contains
    created = reserve(comparison_session)
    assert created.status_code == 202
    result = view(comparison_session, created.json()["id"])
    run_id = result["trials"][0]["repetitions"][1]["run_id"]
    needle = "test-only-protected-ordinal-marker-s45"
    assert serialized_contains({"body_base64": base64.b64encode(needle.encode()).decode()}, needle), (
        "the serialized route scanner must detect this capture needle")
    monkeypatch.setenv("NEBIUS_API_KEY", needle)
    with db.connect(comparison_session[0].db_file) as conn:
        repo.insert_output(conn, RunOutput(id=f"{run_id}-injected-private-output", run_id=run_id,
            request_ordinal=3, request_text=needle, http_status=200, body=needle.encode(), elapsed_ms=1))
        conn.commit()
    response = comparison_session[0].client.get(f"/api/runs/{run_id}/outputs")
    assert response.status_code == 200, "an additional run must resolve its slot before projecting captures"
    assert [row["request_ordinal"] for row in response.json()] == [1, 2]
    assert not serialized_contains(response.json(), needle), "an additional run cannot publish the protected ordinal"


def test_comparison_schedule_copy_does_not_claim_unexecuted_repetitions_ran(comparison_session):
    experiment = reserve_raw(comparison_session)
    with db.connect(comparison_session[0].db_file) as conn:
        result = comparison_flow.comparison_view(conn, experiment)
    assert [row["retained"] for row in result["repetition_summary"]["candidates"]] == [0, 0]
    assert "6 public requests planned for 3 repetitions per version" in result["repetition_summary"]["limits"], (
        "unexecuted repetitions must be labelled as planned")


def test_primary_output_boundary_survives_a_missing_run_back_reference(comparison_session):
    created = reserve(comparison_session)
    assert created.status_code == 202
    result = view(comparison_session, created.json()["id"])
    run_id = result["trials"][0]["run_id"]
    with db.connect(comparison_session[0].db_file) as conn:
        assert len(repo.list_outputs(conn, run_id)) == 3, "positive control needs the real restricted capture"
        conn.execute("UPDATE runs SET trial_slot_id = NULL WHERE id = ?", (run_id,))
        conn.commit()
    response = comparison_session[0].client.get(f"/api/runs/{run_id}/outputs")
    assert response.status_code == 200, "the primary slot pointer must preserve its public output boundary"
    assert [row["request_ordinal"] for row in response.json()] == [1, 2]


@pytest.mark.parametrize("fault", ["duplicate-task", "task-identity", "missing-capture", "empty-capture", "failed-run"])
def test_retained_rate_needs_complete_unambiguous_public_rows(comparison_session, monkeypatch, fault):
    created = reserve(comparison_session)
    assert created.status_code == 202
    result = view(comparison_session, created.json()["id"])
    run_id = result["trials"][0]["repetitions"][1]["run_id"]
    tasks = repo.list_task_assessment_models
    outputs = repo.list_outputs
    observations = repo.list_observations

    def changed_tasks(conn, requested):
        rows = tasks(conn, requested)
        if requested == run_id:
            if fault == "duplicate-task": return rows + rows[:1]
            if fault == "task-identity": return [rows[0].model_copy(update={"task_id": "unassessed-task"}), *rows[1:]]
        return rows

    def changed_outputs(conn, requested):
        rows = outputs(conn, requested)
        if requested == run_id:
            if fault == "missing-capture": return rows[:1]
            if fault == "empty-capture": return [rows[0].model_copy(update={"body": b""}), *rows[1:]]
        return rows

    monkeypatch.setattr(repo, "list_task_assessment_models", changed_tasks)
    monkeypatch.setattr(repo, "list_outputs", changed_outputs)
    if fault == "failed-run":
        def failed_public_status(conn, requested):
            return [row.model_copy(update={"public_payload_json": {
                **row.public_payload_json, "public_repetition_complete": False}})
                if requested == run_id and row.id == f"{run_id}-public-status" else row
                for row in observations(conn, requested)]
        monkeypatch.setattr(repo, "list_observations", failed_public_status)
        with db.connect(comparison_session[0].db_file) as conn:
            conn.execute("UPDATE runs SET state = 'FAILED' WHERE id = ?", (run_id,))
            conn.commit()
    changed = view(comparison_session, result["id"])
    assert changed["repetition_summary"]["candidates"][0]["passed"] == 8, (
        "a repetition with incomplete or ambiguous retained rows must not count as passing")
    assert not changed["eligible"]


def test_public_raw_capture_survives_an_assessment_error(comparison_session, monkeypatch):
    from shiftwork.evaluator import evaluator
    experiment = reserve_raw(comparison_session)

    def broken_assessment(**kwargs):
        raise RuntimeError("operator-injected assessment error")

    monkeypatch.setattr(evaluator, "assess_request", broken_assessment)
    with db.connect(comparison_session[0].db_file) as conn:
        slot = repo.list_trial_slots(conn, experiment.id)[0]
        with pytest.raises(RuntimeError, match="operator-injected assessment error"):
            comparison_flow.execute_comparison(conn, experiment.id)
        assert len(repo.list_outputs(conn, slot.run_id)) == 2, "raw public captures must commit before assessment can fail"
        assert repo.get_run_assessment(conn, slot.run_id) is None


def test_child_assessment_keeps_the_frozen_context_hash(comparison_session, monkeypatch):
    created = reserve(comparison_session)
    assert created.status_code == 202
    result = view(comparison_session, created.json()["id"])
    run_id = result["trials"][0]["repetitions"][1]["run_id"]
    get = repo.get_run_assessment

    def changed(conn, requested):
        assessment = get(conn, requested)
        return assessment.model_copy(update={"context_hash": "0" * 64}) if requested == run_id else assessment

    monkeypatch.setattr(repo, "get_run_assessment", changed)
    changed_view = view(comparison_session, result["id"])
    assert changed_view["outcome"]["status"] == "NOT_COMPARABLE", "each repetition assessment must retain its exact context"
    assert not changed_view["eligible"]


@pytest.mark.parametrize("kind", ["observation", "capture"])
def test_additional_public_run_rejects_out_of_workload_ordinals(comparison_session, monkeypatch, kind):
    from shiftwork.executor.local_process import LocalProcessAdapter
    from shiftwork.executor.base import RawObservation
    execute = LocalProcessAdapter.execute
    count = 0

    async def wrong_ordinal(adapter, request):
        nonlocal count
        count += 1
        result = await execute(adapter, request)
        if count == 2:
            if kind == "observation":
                result = result.model_copy(update={"observations": (RawObservation(kind="INTERPRETATION",
                    public_payload={"request_ordinal": 0}, raw_payload={}),)})
            else:
                result = result.model_copy(update={"captures": (result.captures[0].model_copy(
                    update={"request_ordinal": 0}), *result.captures[1:])})
        return result

    experiment = reserve_raw(comparison_session)
    monkeypatch.setattr(LocalProcessAdapter, "execute", wrong_ordinal)
    with db.connect(comparison_session[0].db_file) as conn:
        with pytest.raises(ValueError, match=f"public repetition {kind} outside frozen workload"):
            comparison_flow.execute_comparison(conn, experiment.id)
