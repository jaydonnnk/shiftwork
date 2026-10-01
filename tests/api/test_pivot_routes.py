"""S10 route contract: old history can requalify without inferred consent."""

import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from demos.final_pivot import create_v5_sample
from shiftwork import orchestrator
from shiftwork.app import create_app
from shiftwork.store import db, repo


def _migrated_client(tmp_path, *, with_run=True):
    original = tmp_path / "original-v5.db"
    copied = tmp_path / "copy-for-api.db"
    create_v5_sample(original, with_run=with_run)
    shutil.copy2(original, copied)
    # A removed guard must fail an assertion as a status code, not escape as an
    # incidental server exception that proves nothing about the named clause.
    return TestClient(create_app(str(copied)), raise_server_exceptions=False), copied


def _count(path, table):
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def test_closed_v5_shift_opens_first_choice_without_invented_selection(tmp_path):
    client, path = _migrated_client(tmp_path)
    with client:
        before = client.get("/api/engagements/bookshop/board")
        assert before.status_code == 200, before.text
        assert before.json()["operating_status"] == "NEEDS_FIRST_CHOICE"
        assert before.json()["operating_selection"] is None
        assert before.json()["latest_run"]["purpose"] == "LEGACY_OPERATION"
        assert before.json()["latest_run"]["evidence_mode"] == "RECORDED_INSPECTION"
        output = client.get("/api/runs/run-v5-0001/outputs")
        assert output.status_code == 200, output.text
        assert output.json()[0]["body_base64"]
        assert output.json()[0]["public_shop_record"] is None
        assert output.json()[0]["public_shop_snapshot_hash"] is None

        opened = client.post("/api/engagements/bookshop/shifts")
        assert opened.status_code == 201, opened.text  # detects rejected shift-open fault
        shift = opened.json()
        assert shift["opening_mode"] == "LEGACY_FIRST_CHOICE"
        assert _count(path, "operating_selections") == 0  # detects starter insertion fault
        assert shift["operation_allowed"] is False
        assert shift["seq"] == 2
        assert _count(path, "shifts") == 2
        assert _count(path, "experiments") == 0
        assert _count(path, "runs") == 1
        assert _count(path, "ledger_events") == 1
        assert _count(path, "incidents") == 1

        draft = client.get(f"/api/shifts/{shift['id']}/artifact")
        assert draft.status_code == 200, draft.text
        assert "service.py" in draft.json()["files"]
        board = client.get("/api/engagements/bookshop/board").json()
        assert board["operating_status"] == "NEEDS_FIRST_CHOICE"
        assert board["operating_selection"] is None
        assert board["latest_shift"]["opening_mode"] == "LEGACY_FIRST_CHOICE"
        assert board["latest_shift"]["operation_allowed"] is False

        run = client.post(f"/api/shifts/{shift['id']}/runs")
        close = client.post(f"/api/shifts/{shift['id']}/close")
        assert run.status_code == 409, run.text
        assert close.status_code == 409, close.text
        assert client.post("/api/engagements/bookshop/shifts").status_code == 409
        assert _count(path, "runs") == 1
        assert _count(path, "ledger_events") == 1
        assert _count(path, "operating_selections") == 0

    with TestClient(create_app(str(path))) as restarted:
        board = restarted.get("/api/engagements/bookshop/board")
        assert board.status_code == 200, board.text
        assert board.json()["latest_shift"]["opening_mode"] == "LEGACY_FIRST_CHOICE"
        assert board.json()["operating_status"] == "NEEDS_FIRST_CHOICE"
        assert restarted.post("/api/engagements/bookshop/shifts").status_code == 409
        assert restarted.post(f"/api/shifts/{shift['id']}/runs").status_code == 409
        assert restarted.post(f"/api/shifts/{shift['id']}/close").status_code == 409
    assert _count(path, "shifts") == 2
    assert _count(path, "operating_selections") == 0


def test_latest_draft_and_freeze_never_promote_a_legacy_choice(tmp_path):
    client, path = _migrated_client(tmp_path)
    with client:
        opened = client.post("/api/engagements/bookshop/shifts")
        assert opened.status_code == 201, opened.text
        shift_id = opened.json()["id"]
        original_files = client.get(f"/api/shifts/{shift_id}/artifact").json()["files"]
        files = dict(original_files)
        files["service.py"] += "\n# candidate only\n"
        saved = client.put(f"/api/shifts/{shift_id}/artifact", json={"files": files})
        assert saved.status_code == 200, saved.text
        contract = {
            "catalog_version": 1,
            "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
            "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
            "response_time_limit_ms": 3000,
            "declared_limits": ["Still a candidate, not operating."],
        }
        frozen = client.post(
            f"/api/shifts/{shift_id}/artifact/versions", json={"contract": contract}
        )
        assert frozen.status_code == 201, frozen.text
        board = client.get("/api/engagements/bookshop/board").json()
        assert board["latest_version"]["id"] == frozen.json()["id"]
        assert board["operating_selection"] is None  # detects latest-draft promotion fault
        assert board["operating_status"] == "NEEDS_FIRST_CHOICE"
        assert client.post(f"/api/shifts/{shift_id}/runs").status_code == 409
        assert client.post(f"/api/shifts/{shift_id}/close").status_code == 409
        assert _count(path, "operating_selections") == 0
        assert _count(path, "runs") == 1


def test_closed_v5_without_source_run_keeps_bootstrap_unreserved(tmp_path):
    client, path = _migrated_client(tmp_path, with_run=False)
    with client:
        opened = client.post("/api/engagements/bookshop/shifts")
        assert opened.status_code == 201, opened.text
        shift_id = opened.json()["id"]
        assert opened.json()["opening_mode"] == "LEGACY_FIRST_CHOICE"
        assert opened.json()["operation_allowed"] is False
        assert client.get(f"/api/shifts/{shift_id}/artifact").status_code == 200
        assert client.post(f"/api/shifts/{shift_id}/runs").status_code == 409
        assert client.post(f"/api/shifts/{shift_id}/close").status_code == 409
        assert _count(path, "runs") == 0
        assert _count(path, "experiments") == 0
        assert _count(path, "operating_selections") == 0
        assert _count(path, "ledger_events") == 0


def test_first_choice_prechoice_run_guard_is_controller_enforced(tmp_path):
    client, path = _migrated_client(tmp_path)
    with client:
        opened = client.post("/api/engagements/bookshop/shifts")
        assert opened.status_code == 201, opened.text
        shift_id = opened.json()["id"]
    conn = db.connect(path)
    try:
        with pytest.raises(orchestrator.LifecycleError, match="selection"):
            orchestrator.start_run(conn, shift_id)
        assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0] == 1
    finally:
        conn.close()


def test_first_choice_shift_open_is_atomic_and_caller_cannot_choose_mode(tmp_path):
    client, path = _migrated_client(tmp_path)
    with client:
        forged = client.post(
            "/api/engagements/bookshop/shifts", json={"opening_mode": "STANDARD"}
        )
        assert forged.status_code == 422, forged.text
        assert _count(path, "shifts") == 1

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(
                lambda _: client.post("/api/engagements/bookshop/shifts"), range(2)
            ))
        assert sorted(response.status_code for response in responses) == [201, 409]
        assert [response.json()["opening_mode"] for response in responses if response.status_code == 201] == [
            "LEGACY_FIRST_CHOICE"
        ]
        assert _count(path, "shifts") == 2
        assert _count(path, "operating_selections") == 0


def test_failed_first_shift_open_leaves_no_partial_state(tmp_path):
    """One atomic shift-open, faulted deterministically rather than by racing.

    The concurrency check above only detects a missing write transaction when the
    two requests happen to overlap, so it can pass by luck. This faults the same
    transaction every time: an engagement with no reviewed starter raises after
    its shift row is inserted, and nothing may survive that raise.
    """
    path = tmp_path / "atomic-open.db"
    with TestClient(create_app(str(path))):
        pass
    conn = db.connect(path)
    try:
        repo.seed_engagement(conn, "northline", "bike_cooperative", "Northline Bike Cooperative")
        assert conn.execute("SELECT COUNT(*) FROM shifts").fetchone()[0] == 0
        with pytest.raises(orchestrator.LifecycleError, match="reviewed initial starter"):
            orchestrator.open_next_shift(conn, "northline")
        assert conn.execute("SELECT COUNT(*) FROM shifts").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM operating_selections").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM artifact_versions").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM draft_artifacts").fetchone()[0] == 0
    finally:
        conn.close()


def test_fresh_engagement_has_separate_starter_baseline(tmp_path):
    path = tmp_path / "fresh-v6.db"
    with TestClient(create_app(str(path))) as client:
        opened = client.post("/api/engagements/bookshop/shifts")
        assert opened.status_code == 201, opened.text
        shift = opened.json()
        assert shift["opening_mode"] == "STANDARD"
        assert shift["operation_allowed"] is True
        board = client.get("/api/engagements/bookshop/board")
        assert board.status_code == 200, board.text
        assert board.json()["operating_status"] == "STARTER_BASELINE"
        assert board.json()["operating_selection"]["kind"] == "STARTER_BASELINE"
        assert board.json()["operating_selection"]["selected_version_id"]
        assert _count(path, "operating_selections") == 1
        assert _count(path, "artifact_versions") == 1


def _save_unselected_candidate(client, shift_id):
    files = dict(client.get(f"/api/shifts/{shift_id}/artifact").json()["files"])
    files["service.py"] += "\n# unselected candidate\n"
    saved = client.put(f"/api/shifts/{shift_id}/artifact", json={"files": files})
    assert saved.status_code == 200, saved.text
    contract = {
        "catalog_version": 1,
        "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
        "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
        "response_time_limit_ms": 3000,
        "declared_limits": ["Candidate limit must not be committed."],
    }
    frozen = client.post(
        f"/api/shifts/{shift_id}/artifact/versions", json={"contract": contract}
    )
    assert frozen.status_code == 201, frozen.text
    return frozen.json()


def test_fresh_starter_run_uses_selected_version_after_unselected_freeze(tmp_path):
    path = tmp_path / "starter-run.db"
    with TestClient(create_app(str(path))) as client:
        shift = client.post("/api/engagements/bookshop/shifts").json()
        starter_id = client.get("/api/engagements/bookshop/board").json()[
            "operating_selection"
        ]["selected_version_id"]
        candidate = _save_unselected_candidate(client, shift["id"])
        assert candidate["id"] != starter_id
        started = client.post(f"/api/shifts/{shift['id']}/runs")
        assert started.status_code == 202, started.text
        assert started.json()["artifact_version_id"] == starter_id
        assert started.json()["selection_id"]


def test_fresh_starter_close_uses_selected_contract_after_unselected_freeze(tmp_path):
    path = tmp_path / "starter-close.db"
    with TestClient(create_app(str(path))) as client:
        shift = client.post("/api/engagements/bookshop/shifts").json()
        _save_unselected_candidate(client, shift["id"])
        closed = client.post(f"/api/shifts/{shift['id']}/close")
        assert closed.status_code == 200, closed.text
        events = client.get("/api/engagements/bookshop/ledger").json()["events"]
        limits = [
            event["payload"]["declared_limit"]
            for event in events if event["event_type"] == "LIMIT_DECLARED"
        ]
        assert limits
        assert "Candidate limit must not be committed." not in limits


def test_later_condition_experiment_shape_is_controller_enforced(tmp_path):
    """Slice 20 route shape: the kind's request carries no candidates of its own.

    The controller derives both candidates from the operating selection, so a
    caller-supplied candidate, a missing observed run, a missing treatment and an
    observed run on any other kind are all rejected before the handler runs and
    before any experiment row exists.
    """
    path = tmp_path / "later-shape.db"
    with TestClient(create_app(str(path)), raise_server_exceptions=False) as client:
        shift = client.post("/api/engagements/bookshop/shifts")
        assert shift.status_code == 201, shift.text
        shift_id = shift.json()["id"]
        base = {
            "kind": "LATER_CONDITION_COMPARISON",
            "observed_run_id": "run-missing",
            "declared_treatment": "Re-test both candidates under the observed outage",
            "client_request_id": "shape-1",
        }

        forged = client.post(f"/api/shifts/{shift_id}/experiments", json={
            **base, "candidate_a_version_id": "ver-0001", "candidate_b_version_id": "ver-0002"})
        assert forged.status_code == 422, forged.text
        no_run = client.post(f"/api/shifts/{shift_id}/experiments", json={
            **base, "observed_run_id": None})
        assert no_run.status_code == 422, no_run.text
        no_treatment = client.post(f"/api/shifts/{shift_id}/experiments", json={
            **base, "declared_treatment": None})
        assert no_treatment.status_code == 422, no_treatment.text
        blank_treatment = client.post(f"/api/shifts/{shift_id}/experiments", json={
            **base, "declared_treatment": "   "})
        assert blank_treatment.status_code == 422, blank_treatment.text
        qualifying_with_run = client.post(f"/api/shifts/{shift_id}/experiments", json={
            "kind": "QUALIFYING_COMPARISON",
            "investigation_id": "inv-x",
            "candidate_a_version_id": "ver-0001",
            "candidate_b_version_id": "ver-0002",
            "observed_run_id": "run-0001",
            "declared_treatment": "treatment",
            "client_request_id": "shape-2",
        })
        assert qualifying_with_run.status_code == 422, qualifying_with_run.text
        assert _count(path, "experiments") == 0, "a rejected shape still reserved an experiment"

        # Shape-valid on a starter baseline: refused by the controller rule that a
        # later-condition comparison needs an explicit learner choice.
        refused = client.post(f"/api/shifts/{shift_id}/experiments", json=base)
        assert refused.status_code == 409, refused.text
        assert "learner choice" in refused.json()["detail"]
        assert _count(path, "experiments") == 0
