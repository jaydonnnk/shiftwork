"""Repeated later-condition comparisons preserve the original operation."""

import pytest
from fastapi.testclient import TestClient

from shiftwork import comparison_flow, orchestrator
from shiftwork.app import create_app
from shiftwork.store import db, repo
from tests.orchestrator import pivot_flow
from tests.packs.material import staged_material


def test_later_comparison_repetitions_freeze_and_never_rewrite_history(tmp_path, monkeypatch):
    path = tmp_path / "later-repeated.db"
    with TestClient(create_app(str(path))) as client:
        original = pivot_flow.qualified_shift(client)
        successor = pivot_flow.open_successor(client)
        shift = successor["id"]
        outage = pivot_flow.staged_outage_state(tmp_path)
        with staged_material(monkeypatch, tmp_path / "observed-package", {
            "fixtures/shop/bookshop_pivot_public_state.json": outage.read_bytes()}):
            started = client.post(f"/api/shifts/{shift}/runs", json={"client_request_id": "s45-observed-operation"})
            assert started.status_code == 202
            operation = pivot_flow.wait_run(client, started.json()["id"])
        assert operation["state"] == "FINALIZED"
        with db.connect(path) as conn:
            before = repo.list_ledger_events(conn, "bookshop")
            selection = repo.get_latest_operating_selection(conn, "bookshop")
            with pytest.raises(orchestrator.LifecycleError, match="comparison public repetitions must be from 1 to 3"):
                comparison_flow.create_later_condition_comparison(conn, shift,
                    operation_run_id=operation["id"], declared_treatment="Same observed outage, repeated public checks",
                    client_request_id="s45-later-bound", public_repetitions=4)
        body = {"kind": "LATER_CONDITION_COMPARISON", "observed_run_id": operation["id"],
            "declared_treatment": "Same observed outage, repeated public checks", "public_repetitions": 3,
            "client_request_id": "s45-later-repeated"}
        response = client.post(f"/api/shifts/{shift}/experiments", json=body)
        assert response.status_code == 202, "later comparisons must admit the frozen repetition count"
        later = pivot_flow.wait_experiment(client, response.json()["id"])
        assert later["state"] == "FINALIZED" and later["public_repetitions"] == 3
        assert later["observed_run_id"] == operation["id"]
        assert later["shared_public_denominator_requests"] == 18
        assert all(len(trial["repetitions"]) == 3 for trial in later["trials"])
        changed = client.post(f"/api/shifts/{shift}/experiments", json={**body, "public_repetitions": 2})
        assert changed.status_code == 409, "a later comparison's count cannot change after results"
        replay = client.post(f"/api/shifts/{shift}/experiments", json=body)
        assert replay.status_code == 202 and replay.json()["id"] == later["id"]
        with db.connect(path) as conn:
            assert repo.list_ledger_events(conn, "bookshop") == before
            assert repo.get_latest_operating_selection(conn, "bookshop") == selection
            assert repo.get_run(conn, operation["id"]).artifact_version_id == original["selected_version_id"]
