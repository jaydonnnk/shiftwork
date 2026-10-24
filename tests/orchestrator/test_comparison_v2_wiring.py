"""Offline adapter double: verify frozen v2 policy wiring, not model behavior."""

import base64
import json

from fastapi.testclient import TestClient

from shiftwork import config, hosted, orchestrator
from shiftwork.app import create_app
from shiftwork.domain import task_contract
from shiftwork.executor.base import RawCapture, RunResult, load_batch, load_single_request
from shiftwork.store import db, repo


def test_v2_comparison_preserves_pinned_workloads_and_delivers_policy_to_both_candidates(tmp_path, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-only-token")
    monkeypatch.setenv("NEBIUS_PROJECT_ID", "test-only-project")
    calls = []

    async def no_network(adapter, request):
        calls.append((request.artifact_snapshot.manifest_hash, request.single_request_ordinal,
            adapter.task_vocabulary, adapter.allowed_tool_names, adapter.allow_reasoning_off))
        batch = (load_batch(request.request_batch, request.request_batch_bytes)
            if request.single_request_ordinal is None else
            (load_single_request(request.request_batch, request.request_batch_bytes, request.single_request_ordinal),))
        captures = tuple(RawCapture(request_ordinal=row.ordinal, http_status=200,
            body=json.dumps({"request_id": json.loads(row.body)["request_id"], "task_results": [],
                "evidence_refs": [], "uncertainty_codes": []}).encode(),
            elapsed_ms=1, transport_error=None, log_ref=None) for row in batch)
        return RunResult(captures=captures, observations=(), executor_ref=None, failure=None, wall_ms=1)

    monkeypatch.setattr(orchestrator.TokenFactoryAdapter, "execute", no_network)
    path = tmp_path / "v2-wiring.db"
    app = create_app(str(path), executor="tokenfactory", live_diagnostic_budget=hosted.diagnostic_budget,
                     live_comparison_budget=hosted.comparison_budget)
    with TestClient(app) as client:
        shift = client.post("/api/engagements/bookshop/shifts").json()["id"]
        frozen = client.post(f"/api/shifts/{shift}/artifact/versions", json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
        assert frozen.status_code == 201, frozen.text
        a = frozen.json()
        source = client.post(f"/api/shifts/{shift}/experiments", json={"kind": "DIAGNOSTIC",
            "candidate_a_version_id": a["id"], "client_request_id": "v2-source"})
        assert source.status_code == 202, source.text
        source_run = client.get(f'/api/experiments/{source.json()["id"]}').json()["trials"][0]["run_id"]
        entry = client.post(f"/api/shifts/{shift}/investigations", json={
            "source_run_id": source_run, "source_request_ordinal": 1,
            "cause": "Operator-authored test entry; the fake adapter returns no task results.",
            "falsifier": "The fake adapter would return a required task result.",
            "public_test": "Every required task has a result.", "client_request_id": "v2-investigation"})
        assert entry.status_code == 201, entry.text
        files = client.get(f"/api/shifts/{shift}/artifact").json()["files"]
        files["service.py"] += "\n# Operator-authored wiring test, never learner work.\n"
        assert client.put(f"/api/shifts/{shift}/artifact", json={"files": files}).status_code == 200
        frozen = client.post(f"/api/shifts/{shift}/artifact/versions", json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
        assert frozen.status_code == 201
        b = frozen.json()
        comparison = client.post(f"/api/shifts/{shift}/experiments", json={
            "kind": "QUALIFYING_COMPARISON", "candidate_a_version_id": a["id"], "candidate_b_version_id": b["id"],
            "investigation_id": entry.json()["id"], "declared_treatment": "Operator-authored wiring test, no model call or learner evidence.",
            "client_request_id": "v2-comparison", "public_repetitions": 3})
        assert comparison.status_code == 202, comparison.text
        result = client.get(f'/api/experiments/{comparison.json()["id"]}').json()
        assert result["state"] == "FINALIZED" and result["outcome"]["status"] == "COMPLETE"
        assert len(calls) == 25, "one source diagnostic plus exactly 24 comparison phases"
        assert {row[0] for row in calls[1:]} == {a["content_hash"], b["content_hash"]}
        with db.connect(path) as conn:
            experiment = repo.get_experiment(conn, result["id"])
            context = repo.get_execution_context(conn, experiment.context_id)
            mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))
            assert mission.version == 2, "a v2-bound shift must freeze mission v2 in its comparison"
            assert all(set(row[2]) == set(mission.task_vocabulary) for row in calls[1:]), "every repetition and protected phase must receive the frozen task vocabulary"
            assert all(set(row[3]) == set(mission.allowed_tool_vocabulary) for row in calls[1:]), "both candidates must receive the same frozen public tools"
            assert all(row[4] is True for row in calls[1:]), "every public repetition and protected phase needs the frozen reasoning permission"
            assert [w.request_count for w in context.workloads] == [2, 2, 2]
            assert len(repo.list_protected_case_snapshots(conn, context.protected_reservation_id)) == 3
