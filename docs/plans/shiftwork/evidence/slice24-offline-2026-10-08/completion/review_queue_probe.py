"""Retained controller proof of the human review branch on synthetic state."""
import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[6] / "tests"))

from fastapi.testclient import TestClient

from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.ledger import chain
from shiftwork.store import db, repo
from tests.orchestrator import test_gtm_pipeline as gtm
from tests.packs.material import apply_staged_material, staged_material


def test_review_queue_operation_and_inheritance(tmp_path, monkeypatch):
    gtm.reviewed_inventory()
    mission = gtm.material_json("fixtures/mission/gtm_pipeline_v1.json")
    for task in mission["request_specs"][0]["tasks"]:
        task["condition_json"]["expected_decisions"] = ["QUALIFIED", "REVIEW"]
    with staged_material(monkeypatch, tmp_path / "operator-review-mission", {
            "fixtures/mission/gtm_pipeline_v1.json": json.dumps(mission).encode()}):
        with monkeypatch.context() as review_binding:
            exercise_review_queue(tmp_path, review_binding)


def exercise_review_queue(tmp_path, monkeypatch):
    out = Path(os.environ["SHIFTWORK_QUEUE_OUT"])
    out.mkdir(exist_ok=False)
    path = tmp_path / "review-queue.db"
    world = gtm.material_json("fixtures/state/gtm_pipeline_public_state.json")
    world["records"][0]["value"]["confidence"] = 50
    with TestClient(create_app(str(path), executor="local_process")) as client:
        flow = gtm.qualify_gtm(client)
        second = gtm.gtm_next_shift(client, flow["shift_id"])
        apply_staged_material(monkeypatch, tmp_path / "synthetic-review-state", {
            "fixtures/state/gtm_pipeline_public_state.json": json.dumps(world).encode()})
        started = client.post(f"/api/shifts/{second['id']}/runs", json={"client_request_id": "review-queue-operation"})
        assert started.status_code == 202, started.text
        operation = gtm.pivot_flow.wait_run(client, started.json()["id"])
        assert operation["state"] == "FINALIZED", operation
        conn = db.connect(path)
        try:
            run = repo.get_run(conn, operation["id"])
            drafts = orchestrator._stored_operation_drafts(conn, run, "gtm")
            assert [row["event_type"] for row in drafts] == ["OWNER_ASSIGNED", "SLA_CLOCK_STARTED", "HANDOFF_ESCALATED"]
            assert all(row["synthetic"] and row["payload"]["owner"] == "revenue-review" for row in drafts)
            assert drafts[-1]["payload"]["terminal_action"] == "HUMAN_HANDOFF"
            assert repo.get_run_assessment(conn, run.id).mandatory_pass
            assert orchestrator.replay_assessment(conn, run.id).status == "IDENTICAL"
            gtm.assert_pipeline_surface_safe(drafts)
            output = repo.list_outputs(conn, run.id)[0]
            projection = orchestrator.output_evidence_for(conn, output, run)
            gtm.assert_pipeline_surface_safe(projection)
            assert "prepared for human handling" in projection["customer_answer"]["display_text"]
        finally:
            conn.close()
        third = gtm.gtm_next_shift(client, second["id"])
    with TestClient(create_app(str(path), executor="local_process")) as client:
        started = client.post(f"/api/shifts/{third['id']}/runs", json={"client_request_id": "review-queue-reprocessing"})
        assert started.status_code == 202, started.text
        repeated = gtm.pivot_flow.wait_run(client, started.json()["id"])
        assert repeated["state"] == "FINALIZED", repeated
        conn = db.connect(path)
        try:
            assert repo.get_run_assessment(conn, repeated["id"]).mandatory_pass
            assert orchestrator._stored_operation_drafts(conn, repo.get_run(conn, repeated["id"]), "gtm") == []
            assert chain.verify_chain(repo.list_ledger_events(conn, "gtm")) is chain.ChainStatus.VALID
            assert orchestrator.replay_assessment(conn, operation["id"]).status == "IDENTICAL"
            database = out / "journey.db"
            saved = sqlite3.connect(database)
            try:
                conn.backup(saved)
            finally:
                saved.close()
            proof = {"mode": "TRUSTED_LOCAL_DISPOSABLE_OPERATOR_MISSION_AND_REVIEW_STATE", "confidence": 50,
                     "expected_decisions": ["QUALIFIED", "REVIEW"],
                     "operation": operation, "reprocessing": repeated, "projection": projection,
                     "drafts": drafts,
                     "database_sha256": hashlib.sha256(database.read_bytes()).hexdigest()}
            (out / "journey.json").write_bytes((json.dumps(proof, indent=2) + "\n").encode())
        finally:
            conn.close()
