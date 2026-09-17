"""Tracer smoke check: every lifecycle route is wired, rows persist, state carries.

Lands at Slice 1 (04-slices.md). Fails if any route in the documented lifecycle
is unwired, a row is not persisted, or the stub finalization drifts.
"""

import base64
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from shiftwork import config
from shiftwork.app import create_app


def _ok(response, expected: int = 200):
    assert response.status_code == expected, response.text
    return response.json()


@pytest.fixture()
def client(tmp_path):
    db_file = tmp_path / "tracer.db"
    with TestClient(create_app(str(db_file))) as test_client:
        yield test_client, db_file


def _drive_to_run(test_client) -> tuple[str, str]:
    shift = _ok(test_client.post("/api/engagements/bookshop/shifts"), 201)
    test_client.put(
        f"/api/shifts/{shift['id']}/draft",
        json={"files": {"service.py": "# learner revision\n"}},
    )
    _ok(test_client.post(f"/api/shifts/{shift['id']}/artifact/versions"), 201)
    run = _ok(test_client.post(f"/api/shifts/{shift['id']}/runs"), 202)
    return shift["id"], run["id"]


def test_tracer_lifecycle_persists_and_returns_rows(client):
    test_client, db_file = client

    root = test_client.get("/")
    assert root.status_code == 200
    assert "text/html" in root.headers["content-type"]

    board = _ok(test_client.get("/api/engagements/bookshop/board"))
    assert board["latest_shift"] is None
    assert board["ledger_event_count"] == 0
    assert board["chain_status"] == "VALID"

    shift = _ok(test_client.post("/api/engagements/bookshop/shifts"), 201)
    assert shift["state"] == "open"
    assert shift["seq"] == 1
    shift_id = shift["id"]

    draft = _ok(test_client.get(f"/api/shifts/{shift_id}/draft"))
    assert "service.py" in draft["files"]
    files = dict(draft["files"])
    files["service.py"] += "\n# edited by the learner\n"
    updated = _ok(test_client.put(f"/api/shifts/{shift_id}/draft", json={"files": files}))
    assert updated["files"]["service.py"].endswith("# edited by the learner\n")

    version = _ok(test_client.post(f"/api/shifts/{shift_id}/artifact/versions"), 201)
    assert version["content_hash"] == "placeholder-1"
    assert version["created_by"] == "learner"

    started = _ok(test_client.post(f"/api/shifts/{shift_id}/runs"), 202)
    assert started["state"] == "QUEUED"
    assert started["attempt_number"] == 1
    run_id = started["id"]

    run = _ok(test_client.get(f"/api/runs/{run_id}"))
    assert run["state"] == "FINALIZED"

    outputs = _ok(test_client.get(f"/api/runs/{run_id}/outputs"))
    assert [output["request_ordinal"] for output in outputs] == [1, 2, 3]
    first_body = json.loads(base64.b64decode(outputs[0]["body_base64"]))
    assert first_body["action"] == "answer"
    assert {"kind": "price", "value": 1250} in first_body["claims"]

    checks = _ok(test_client.get(f"/api/runs/{run_id}/checks"))
    assert len(checks) == 1
    assert checks[0]["verdict"] == "fail"
    assert checks[0]["reason_code"] == "STALE_BEYOND_RULE"
    assert checks[0]["public_check_id"] is None

    ledger = _ok(test_client.get("/api/engagements/bookshop/ledger"))
    assert ledger["chain_status"] == "VALID"
    assert [event["event_type"] for event in ledger["events"]] == [
        "SALE_COMPLETED",
        "INCIDENT_OPENED",
    ]
    assert ledger["events"][0]["prev_hash"] == config.GENESIS_HASH
    assert ledger["events"][1]["prev_hash"] == ledger["events"][0]["hash"]
    assert ledger["events"][1]["seq"] == 2

    incident = _ok(test_client.get("/api/incidents/BWB-01"))
    assert incident["state"] == "OPEN"
    assert incident["reason_code"] == "STALE_BEYOND_RULE"
    assert incident["opened_event_seq"] == 2
    assert incident["opening_run_id"] == run_id

    board = _ok(test_client.get("/api/engagements/bookshop/board"))
    assert board["requests_run"] == 3
    assert board["attempts_used"] == 1
    assert board["attempt_limit"] == 3
    assert board["attempts_remaining"] == 2
    assert board["ledger_totals"] == {"SALE_COMPLETED": 1, "INCIDENT_OPENED": 1}
    assert [open_incident["id"] for open_incident in board["open_incidents"]] == ["BWB-01"]

    closed = _ok(test_client.post(f"/api/shifts/{shift_id}/close"))
    assert closed["state"] == "closed"
    assert _ok(test_client.post(f"/api/shifts/{shift_id}/close"))["state"] == "closed"

    assert test_client.get("/api/runs/run-9999").status_code == 404
    assert test_client.get("/api/incidents/BWB-99").status_code == 404
    assert test_client.post("/api/shifts/none-such/runs").status_code == 404
    assert test_client.get("/api/engagements/no-such-shop/board").status_code == 404

    conn = sqlite3.connect(db_file)
    try:
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "shifts",
                "artifact_versions",
                "runs",
                "run_outputs",
                "check_results",
                "incidents",
                "ledger_events",
            )
        }
        assert counts == {
            "shifts": 1,
            "artifact_versions": 1,
            "runs": 1,
            "run_outputs": 3,
            "check_results": 1,
            "incidents": 1,
            "ledger_events": 2,
        }
        assert conn.execute("SELECT state FROM runs").fetchone()[0] == "FINALIZED"
    finally:
        conn.close()


def test_board_state_survives_restart(tmp_path):
    db_file = tmp_path / "persist.db"
    with TestClient(create_app(str(db_file))) as test_client:
        _drive_to_run(test_client)

    with TestClient(create_app(str(db_file))) as restarted:
        board = _ok(restarted.get("/api/engagements/bookshop/board"))
        assert board["latest_shift"]["state"] == "open"
        assert board["latest_run"]["state"] == "FINALIZED"
        assert board["requests_run"] == 3
        assert board["ledger_event_count"] == 2
        assert [open_incident["id"] for open_incident in board["open_incidents"]] == ["BWB-01"]
