"""Thin real vertical path smoke check (Slice 2) + declared-limit test 44 PARTIAL.

The smoke check drives one shift's data real end to end over HTTP and asserts the
ONE real CheckResult and the ONE real hash-chained LedgerEvent are produced and
persisted. It fails if any step is still mocked: a placeholder content_hash, a
placeholder chain hash, a missing row, or a chain that does not verify.

Test 44 (partial): a declared limit is stored on the frozen contract and never
scored - it does not appear in the one real CheckResult or the one real ledger
event. Deferred clauses (NOT claimed here): "a declared limit cannot satisfy a
required executable dimension or silently become an evaluator rule" completes at
Slice 4, and the "and inherited" clause completes at Slice 8.
"""

import base64
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from shiftwork import config
from shiftwork.app import create_app
from shiftwork.ledger import chain
from shiftwork.store import db, repo

DECLARED_LIMIT = "NO_SAME_DAY_DELIVERY_PROMISE"

CONTRACT = {
    "catalog_version": 1,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
    "response_time_limit_ms": 3000,
    "declared_limits": [DECLARED_LIMIT],
}


def _ok(response, expected: int = 200):
    assert response.status_code == expected, response.text
    return response.json()


@pytest.fixture()
def driven(tmp_path):
    db_file = tmp_path / "thin.db"
    with TestClient(create_app(str(db_file))) as client:
        shift = _ok(client.post("/api/engagements/bookshop/shifts"), 201)
        version = _ok(
            client.post(
                f"/api/shifts/{shift['id']}/artifact/versions", json={"contract": CONTRACT}
            ),
            201,
        )
        started = _ok(client.post(f"/api/shifts/{shift['id']}/runs"), 202)
        run = _ok(client.get(f"/api/runs/{started['id']}"))
        yield {
            "client": client,
            "db_file": db_file,
            "version": version,
            "run": run,
            "run_id": started["id"],
        }


def test_thin_path_produces_one_real_check_and_one_real_chained_event(driven):
    client = driven["client"]
    run_id = driven["run_id"]
    version = driven["version"]

    assert driven["run"]["state"] == "FINALIZED"

    # A real content-addressed hash, not the tracer placeholder.
    assert len(version["content_hash"]) == 64
    assert "placeholder" not in version["content_hash"]

    outputs = _ok(client.get(f"/api/runs/{run_id}/outputs"))
    assert len(outputs) == 1
    body = json.loads(base64.b64decode(outputs[0]["body_base64"]))
    assert body["action"] == "answer"
    assert body["record_age_ms"] == 5400000

    checks = _ok(client.get(f"/api/runs/{run_id}/checks"))
    assert len(checks) == 1
    check = checks[0]
    assert check["verdict"] == "fail"
    assert check["reason_code"] == "STALE_BEYOND_RULE"
    assert check["expected_ref"].startswith("sealed:")
    assert check["public_check_id"] is None
    # The opaque ref must not leak the sealed expected value.
    assert "in_stock" not in check["expected_ref"]
    assert "ask" not in check["expected_ref"]

    ledger = _ok(client.get("/api/engagements/bookshop/ledger"))
    assert ledger["chain_status"] == "VALID"
    assert len(ledger["events"]) == 1
    event = ledger["events"][0]
    assert event["event_type"] == "BACKLOG_RECORDED"
    assert event["seq"] == 1
    assert event["prev_hash"] == config.GENESIS_HASH
    assert len(event["hash"]) == 64
    assert "placeholder" not in event["hash"]
    assert event["synthetic"] is True


def test_thin_path_persists_real_rows_and_chain_verifies_from_tables(driven):
    db_file = driven["db_file"]

    raw = sqlite3.connect(db_file)
    try:
        assert raw.execute("SELECT COUNT(*) FROM check_results").fetchone()[0] == 1
        assert raw.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0] == 1
        assert raw.execute("SELECT COUNT(*) FROM run_outputs").fetchone()[0] == 1
        # Slice 2 opens no incident; that is Slice 5/7.
        assert raw.execute("SELECT COUNT(*) FROM incidents").fetchone()[0] == 0
        assert raw.execute("SELECT state FROM runs").fetchone()[0] == "FINALIZED"
    finally:
        raw.close()

    conn = db.connect(db_file)
    try:
        events = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
        assert chain.verify_chain(events) is chain.ChainStatus.VALID
    finally:
        conn.close()


def test_declared_limit_is_stored_but_never_scored(driven):
    client = driven["client"]
    run_id = driven["run_id"]

    # Stored on the frozen contract.
    assert DECLARED_LIMIT in driven["version"]["contract"]["declared_limits"]

    # Never scored: absent from the one real CheckResult and the one real event.
    checks = _ok(client.get(f"/api/runs/{run_id}/checks"))
    assert len(checks) == 1
    assert DECLARED_LIMIT.lower() not in json.dumps(checks).lower()
    ledger = _ok(client.get("/api/engagements/bookshop/ledger"))
    assert len(ledger["events"]) == 1
    assert DECLARED_LIMIT.lower() not in json.dumps(ledger["events"]).lower()
