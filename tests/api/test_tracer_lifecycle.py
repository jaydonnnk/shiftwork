"""Slice 2 lifecycle route-surface check: every route is wired, rows persist, state carries.

Originally the Slice 1 tracer smoke check; updated to the real thin path. It now
asserts the real content-hashed freeze, the one captured output, the one real
CheckResult and the one real hash-chained ledger event across the full HTTP route
surface, plus restart persistence. Fails if any route is unwired, a row is not
persisted, or a step is still mocked. The focused thin-path smoke check and the
clause-level partials live in tests/api/test_thin_path.py.
"""

import base64
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from shiftwork import config
from shiftwork.app import create_app

CONTRACT = {
    "catalog_version": 1,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
    "response_time_limit_ms": 3000,
    "declared_limits": ["Answers one fixed shelf-stock request per shift."],
}


def _ok(response, expected: int = 200):
    assert response.status_code == expected, response.text
    return response.json()


@pytest.fixture()
def client(tmp_path):
    db_file = tmp_path / "thin.db"
    # The shipped controller default serves the repair arc (Slice 8); this
    # route-surface check pins the thin path and selects its profile explicitly.
    with TestClient(create_app(str(db_file), shop_snapshot=config.THIN_SNAPSHOT)) as test_client:
        yield test_client, db_file


def _drive_to_run(test_client) -> tuple[str, str]:
    shift = _ok(test_client.post("/api/engagements/bookshop/shifts"), 201)
    test_client.put(
        f"/api/shifts/{shift['id']}/artifact",
        json={"files": {"service.py": "# learner revision\n"}},
    )
    _ok(
        test_client.post(
            f"/api/shifts/{shift['id']}/artifact/versions", json={"contract": CONTRACT}
        ),
        201,
    )
    run = _ok(test_client.post(f"/api/shifts/{shift['id']}/runs"), 202)
    return shift["id"], run["id"]


def test_lifecycle_persists_and_returns_real_rows(client):
    test_client, db_file = client

    root = test_client.get("/")
    assert root.status_code == 200
    assert "text/html" in root.headers["content-type"]

    board = _ok(test_client.get("/api/engagements/bookshop/board"))
    assert board["latest_shift"] is None
    assert board["ledger_event_count"] == 0
    assert board["chain_status"] == "VALID"
    assert board["attempt_limit"] == config.DEFAULT_ATTEMPT_LIMIT

    shift = _ok(test_client.post("/api/engagements/bookshop/shifts"), 201)
    assert shift["state"] == "open"
    assert shift["seq"] == 1
    shift_id = shift["id"]

    draft = _ok(test_client.get(f"/api/shifts/{shift_id}/artifact"))
    assert "service.py" in draft["files"]
    files = dict(draft["files"])
    files["service.py"] += "\n# edited by the learner\n"
    updated = _ok(test_client.put(f"/api/shifts/{shift_id}/artifact", json={"files": files}))
    assert updated["files"]["service.py"].endswith("# edited by the learner\n")

    version = _ok(
        test_client.post(
            f"/api/shifts/{shift_id}/artifact/versions", json={"contract": CONTRACT}
        ),
        201,
    )
    assert len(version["content_hash"]) == 64
    assert "placeholder" not in version["content_hash"]
    assert version["created_by"] == "learner"
    assert version["contract"]["declared_limits"] == CONTRACT["declared_limits"]
    assert len(version["contract_catalog_hash"]) == 64

    started = _ok(test_client.post(f"/api/shifts/{shift_id}/runs"), 202)
    assert started["state"] == "QUEUED"
    assert started["attempt_number"] == 1
    run_id = started["id"]

    run = _ok(test_client.get(f"/api/runs/{run_id}"))
    assert run["state"] == "FINALIZED"

    outputs = _ok(test_client.get(f"/api/runs/{run_id}/outputs"))
    assert [output["request_ordinal"] for output in outputs] == [1]
    body = json.loads(base64.b64decode(outputs[0]["body_base64"]))
    assert body.get("action") == "answer"
    assert {"kind": "stock", "value": "in_stock"} in body.get("claims", [])
    assert body.get("record_age_ms") == 5400000

    # One drawn case per enabled family, each bound to the shared ordinal 1 and
    # each failing the stale answer with the same reason code.
    checks = _ok(test_client.get(f"/api/runs/{run_id}/checks"))
    assert len(checks) == len(config.BOOKSHOP_FAMILIES) == 3
    assert {check["verdict"] for check in checks} == {"fail"}
    assert {check["reason_code"] for check in checks} == {"STALE_BEYOND_RULE"}
    assert {check["public_check_id"] for check in checks} == {None}
    assert len({check["expected_ref"] for check in checks}) == 3

    families = len(config.BOOKSHOP_FAMILIES)
    ledger = _ok(test_client.get("/api/engagements/bookshop/ledger"))
    assert ledger["chain_status"] == "VALID"
    assert [event["event_type"] for event in ledger["events"]] == ["BACKLOG_RECORDED"] * families
    assert [event["seq"] for event in ledger["events"]] == list(range(1, families + 1))
    assert ledger["events"][0]["prev_hash"] == config.GENESIS_HASH
    assert ledger["events"][1]["prev_hash"] == ledger["events"][0]["hash"]

    # Slice 2 opens no incident; the incident route still 404s cleanly.
    assert test_client.get("/api/incidents/BWB-01").status_code == 404

    board = _ok(test_client.get("/api/engagements/bookshop/board"))
    assert board["requests_run"] == 1
    assert board["attempts_used"] == 1
    assert board["attempt_limit"] == config.DEFAULT_ATTEMPT_LIMIT
    assert board["attempts_remaining"] == config.DEFAULT_ATTEMPT_LIMIT - 1
    assert board["ledger_totals"] == {"BACKLOG_RECORDED": families}
    assert board["incidents"] == []

    closed = _ok(test_client.post(f"/api/shifts/{shift_id}/close"))
    assert closed["state"] == "closed"
    assert _ok(test_client.post(f"/api/shifts/{shift_id}/close"))["state"] == "closed"

    assert test_client.get("/api/runs/run-9999").status_code == 404
    assert test_client.get("/api/incidents/BWB-99").status_code == 404
    assert test_client.post("/api/shifts/none-such/runs").status_code == 404
    assert test_client.get("/api/engagements/no-such-shop/board").status_code == 404

    conn = sqlite3.connect(db_file)
    try:
        families = len(config.BOOKSHOP_FAMILIES)
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
                "rotation_draws",
            )
        }
        assert counts == {
            "shifts": 1,
            "artifact_versions": 2,  # immutable starter plus the learner freeze
            "runs": 1,
            "run_outputs": 1,
            "check_results": families,
            "incidents": 0,
            # The close appended one LIMIT_DECLARED event for the contract's
            # declared limit (Slice 8, program design S5.8).
            "ledger_events": families + 1,
            "rotation_draws": families,
        }
        event_types = [
            row[0]
            for row in conn.execute("SELECT event_type FROM ledger_events ORDER BY seq").fetchall()
        ]
        assert event_types == ["BACKLOG_RECORDED"] * families + ["LIMIT_DECLARED"]
        assert conn.execute("SELECT state FROM runs").fetchone()[0] == "FINALIZED"
    finally:
        conn.close()


def test_board_state_survives_restart(tmp_path):
    db_file = tmp_path / "persist.db"
    with TestClient(create_app(str(db_file), shop_snapshot=config.THIN_SNAPSHOT)) as test_client:
        _drive_to_run(test_client)

    with TestClient(create_app(str(db_file), shop_snapshot=config.THIN_SNAPSHOT)) as restarted:
        board = _ok(restarted.get("/api/engagements/bookshop/board"))
        assert board["latest_shift"]["state"] == "open"
        assert board["latest_run"]["state"] == "FINALIZED"
        assert board["requests_run"] == 1
        assert board["ledger_event_count"] == len(config.BOOKSHOP_FAMILIES)
        assert board["chain_status"] == "VALID"
        assert board["incidents"] == []
