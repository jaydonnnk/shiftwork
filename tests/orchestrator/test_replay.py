"""S19: semantic replay of captured operation evidence (Gate 3 tests 42 to 44).

Every test drives the real HTTP surface against a real database, replays one
finalized operation through the orchestration function using only the run's
captured inputs, and proves zero writes by serializing every table's rows
before and after.
"""

import json
import time

import pytest
from fastapi.testclient import TestClient

from demos.final_pivot import assert_v5_rows_preserved, create_v5_sample, snapshot_v5_rows
from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.ledger import chain
from shiftwork.store import db, repo


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
        "client_request_id": f"replay-investigate-{shift_id}",
    })
    assert investigation.status_code == 201, investigation.text
    a, b = (_candidate(client, shift_id, label) for label in ("A", "B"))
    created = client.post(f"/api/shifts/{shift_id}/experiments", json={
        "kind": "QUALIFYING_COMPARISON",
        "investigation_id": investigation.json()["id"],
        "candidate_a_version_id": a["id"],
        "candidate_b_version_id": b["id"],
        "declared_treatment": "A chooses lowest price; B chooses highest stock",
        "client_request_id": f"replay-compare-{shift_id}",
    })
    assert created.status_code == 202, created.text
    deadline = time.monotonic() + 90
    view = created.json()
    while time.monotonic() < deadline:
        view = client.get(f"/api/experiments/{created.json()['id']}").json()
        if view["state"] in ("FINALIZED", "FAILED"):
            break
        time.sleep(0.05)
    assert view["outcome"]["status"] == "COMPLETE", view
    assert all(item["eligible"] for item in view["outcome"]["eligibility"])
    return a, b, view


@pytest.fixture()
def operated(tmp_path):
    """One finalized S18 operation over a migrated first-choice shift."""
    db_file = tmp_path / "replay.db"
    create_v5_sample(db_file)
    with TestClient(create_app(str(db_file))) as client:
        opened = client.post("/api/engagements/bookshop/shifts")
        assert opened.status_code == 201, opened.text
        shift_id = opened.json()["id"]
        a, _, comparison = _comparison(client, shift_id, "run-v5-0001")
        choice = client.post(f"/api/shifts/{shift_id}/selections", json={
            "comparison_id": comparison["id"],
            "selected_version_id": a["id"],
            "rationale": "A completed the required tasks under the shared conditions.",
            "expected_prior_selection_id": None,
            "client_request_id": "replay-choice",
        })
        assert choice.status_code == 201, choice.text
        started = client.post(f"/api/shifts/{shift_id}/runs",
                              json={"client_request_id": "replay-operation"})
        assert started.status_code == 202, started.text
        finished = client.get(f"/api/runs/{started.json()['id']}").json()
        assert finished["state"] == "FINALIZED", finished
    conn = db.connect(db_file)
    try:
        run = repo.get_run(conn, started.json()["id"])
        assert run.purpose.value == "OPERATION" and run.context_id is not None
        yield conn, db_file, run
    finally:
        conn.close()


def _own_events(conn, run):
    return [event for event in repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
            if event.cause_refs and event.cause_refs[0] == run.id]


def test_semantic_replay_uses_original_inputs_and_writes_nothing(
    operated, monkeypatch, tmp_path
):
    conn, _, run = operated
    before = snapshot_v5_rows(conn)
    report = orchestrator.replay_assessment(conn, run.id)
    assert report.status == "IDENTICAL"
    assert report.check_differences == ()
    assert report.event_draft_differences == ()
    assert report.wrote_rows is False
    assert_v5_rows_preserved(conn, before)

    # Edited current files and today's incident state cannot change the replay:
    # it reads the captured mission bytes, captured public state and captured
    # outputs, never the live fixture files or present incident rows.
    decoy_mission = tmp_path / "mission-decoy.json"
    decoy_mission.write_text('{"not": "the captured mission"}', encoding="utf-8")
    decoy_state = tmp_path / "state-decoy.json"
    decoy_state.write_text('{"not": "the captured state"}', encoding="utf-8")
    decoy_requests = tmp_path / "requests-decoy.jsonl"
    decoy_requests.write_text("decoy\n", encoding="utf-8")
    monkeypatch.setattr(config, "PIVOT_MISSION", decoy_mission)
    monkeypatch.setattr(config, "PIVOT_PUBLIC_STATE", decoy_state)
    monkeypatch.setattr(config, "PIVOT_INCIDENT_REQUESTS", decoy_requests)
    incidents = repo.list_incidents(conn, config.BOOKSHOP_SLUG)
    assert incidents, "the migrated history must carry its incident row"
    conn.execute("UPDATE incidents SET state = 'OPEN'")
    conn.commit()
    assert all(item.state.value == "OPEN" for item in repo.list_incidents(conn, config.BOOKSHOP_SLUG))
    mutated = snapshot_v5_rows(conn)

    repeat = orchestrator.replay_assessment(conn, run.id)
    assert repeat.status == "IDENTICAL"
    assert repeat.check_differences == ()
    assert repeat.event_draft_differences == ()
    assert repeat.wrote_rows is False
    assert_v5_rows_preserved(conn, mutated)


def test_legacy_replay_reports_unknown_missing_inputs(tmp_path, monkeypatch):
    db_file = tmp_path / "legacy.db"
    create_v5_sample(db_file)
    conn = db.connect(db_file)
    try:
        db.ensure_schema(conn)
        before = snapshot_v5_rows(conn)
        decoy = tmp_path / "mission-decoy.json"
        decoy.write_text('{"not": "the captured mission"}', encoding="utf-8")
        monkeypatch.setattr(config, "PIVOT_MISSION", decoy)
        try:
            report = orchestrator.replay_assessment(conn, "run-v5-0001")
        except Exception as error:  # replaying un-captured history must never raise its way to a guess
            pytest.fail(f"legacy replay raised {type(error).__name__}: {error}")
        assert report.status == "UNKNOWN_MISSING_INPUTS"
        assert report.check_differences == ()
        assert report.event_draft_differences == ()
        assert report.wrote_rows is False
        assert_v5_rows_preserved(conn, before)
    finally:
        conn.close()


def test_replay_reports_unknown_when_the_captured_context_is_gone(operated):
    conn, _, run = operated
    conn.execute("UPDATE runs SET context_id = 'context-gone' WHERE id = ?", (run.id,))
    conn.commit()
    before = snapshot_v5_rows(conn)
    try:
        report = orchestrator.replay_assessment(conn, run.id)
    except Exception as error:
        pytest.fail(f"a vanished capture reported {type(error).__name__} instead of unknown inputs: {error}")
    assert report.status == "UNKNOWN_MISSING_INPUTS"
    assert report.check_differences == ()
    assert report.event_draft_differences == ()
    assert_v5_rows_preserved(conn, before)


def test_chain_verification_and_semantic_replay_fail_independently(operated):
    conn, _, run = operated
    slug = config.BOOKSHOP_SLUG

    # A hash-only chain tamper breaks chain verification while the semantic
    # replay, which compares content fields, still reports IDENTICAL.
    events = repo.list_ledger_events(conn, slug)
    target = events[-1]
    original_prev = target.prev_hash
    conn.execute("UPDATE ledger_events SET prev_hash = ? WHERE seq = ?", ("0" * 64, target.seq))
    conn.commit()
    assert chain.verify_chain(repo.list_ledger_events(conn, slug)) is chain.ChainStatus.BROKEN
    assert orchestrator.replay_assessment(conn, run.id).status == "IDENTICAL"
    conn.execute("UPDATE ledger_events SET prev_hash = ? WHERE seq = ?", (original_prev, target.seq))
    conn.commit()
    assert chain.verify_chain(repo.list_ledger_events(conn, slug)) is chain.ChainStatus.VALID

    # A semantic divergence in a stored check breaks only the replay: the chain
    # still verifies because no event row changed.
    checks = repo.list_check_results(conn, run.id)
    assert checks
    changed = checks[0]
    original_verdict = changed.verdict
    conn.execute("UPDATE check_results SET verdict = ? WHERE id = ?",
                 ("fail" if original_verdict == "pass" else "pass", changed.id))
    conn.commit()
    assert chain.verify_chain(repo.list_ledger_events(conn, slug)) is chain.ChainStatus.VALID
    diverged = orchestrator.replay_assessment(conn, run.id)
    assert diverged.status == "DIFFERENT"
    assert diverged.check_differences
    assert diverged.event_draft_differences == ()
    assert any(item.get("check_id") == changed.check_id
               for item in diverged.check_differences)
    conn.execute("UPDATE check_results SET verdict = ? WHERE id = ?", (original_verdict, changed.id))
    conn.commit()
    assert chain.verify_chain(repo.list_ledger_events(conn, slug)) is chain.ChainStatus.VALID
    assert orchestrator.replay_assessment(conn, run.id).status == "IDENTICAL"


def test_stored_event_draft_divergence_reports_different(operated):
    conn, _, run = operated
    own = _own_events(conn, run)
    assert own, "the finalized operation must have written at least one consequence"
    target = own[0]
    original_payload = conn.execute(
        "SELECT payload_json FROM ledger_events WHERE seq = ?", (target.seq,)
    ).fetchone()[0]
    conn.execute(
        "UPDATE ledger_events SET payload_json = ? WHERE seq = ?",
        ('{"synthetic_orders": 999, "mission_version": 1, "rule_version": "tampered"}', target.seq),
    )
    conn.commit()
    report = orchestrator.replay_assessment(conn, run.id)
    assert report.status == "DIFFERENT"
    assert report.event_draft_differences
    assert report.check_differences == ()
    conn.execute("UPDATE ledger_events SET payload_json = ? WHERE seq = ?",
                 (original_payload, target.seq))
    conn.commit()
    assert orchestrator.replay_assessment(conn, run.id).status == "IDENTICAL"


def test_replay_refuses_experimental_and_unfinalized_runs(operated):
    conn, _, run = operated
    conn.execute("UPDATE runs SET purpose = 'EXPERIMENT' WHERE id = ?", (run.id,))
    conn.commit()
    try:
        orchestrator.replay_assessment(conn, run.id)
    except orchestrator.LifecycleError as error:
        assert "operational runs" in str(error)
    except Exception as error:
        pytest.fail(f"wrong failure type {type(error).__name__}: {error}")
    else:
        pytest.fail("an experimental run replayed as if it were an operational one")
    conn.execute("UPDATE runs SET purpose = 'OPERATION', state = 'CAPTURED' WHERE id = ?", (run.id,))
    conn.commit()
    try:
        orchestrator.replay_assessment(conn, run.id)
    except orchestrator.LifecycleError as error:
        assert "finalized" in str(error)
    except Exception as error:
        pytest.fail(f"wrong failure type {type(error).__name__}: {error}")
    else:
        pytest.fail("an unfinalized run replayed as if its assessment were committed")


def test_replay_refuses_unknown_runs(operated):
    conn, _, _ = operated
    try:
        orchestrator.replay_assessment(conn, "run-does-not-exist")
    except orchestrator.LifecycleError as error:
        assert "unknown run" in str(error)
    except Exception as error:
        pytest.fail(f"wrong failure type {type(error).__name__}: {error}")
    else:
        pytest.fail("an unknown run id produced a replay report")


def test_replay_reports_unknown_when_capture_integrity_is_broken(operated):
    conn, _, run = operated
    mission = json.loads(config.PIVOT_MISSION.read_text(encoding="utf-8"))
    mission["version"] = mission["version"] + 1
    tampered = json.dumps(mission, sort_keys=True, separators=(",", ":")).encode("utf-8")
    conn.execute("UPDATE execution_contexts SET mission_bytes = ? WHERE id = ?",
                 (tampered, run.context_id))
    conn.commit()
    before = snapshot_v5_rows(conn)
    try:
        report = orchestrator.replay_assessment(conn, run.id)
    except Exception as error:
        pytest.fail(f"a corrupted capture raised {type(error).__name__} instead of unknown inputs: {error}")
    assert report.status == "UNKNOWN_MISSING_INPUTS"
    assert report.check_differences == ()
    assert report.event_draft_differences == ()
    assert_v5_rows_preserved(conn, before)


def test_replay_reports_unknown_when_captured_outputs_do_not_cover_the_workload(operated):
    conn, _, run = operated
    row = conn.execute("SELECT workloads_json FROM execution_contexts WHERE id = ?",
                       (run.context_id,)).fetchone()
    workloads = json.loads(row["workloads_json"])
    workloads[0]["request_count"] = workloads[0]["request_count"] + 1
    conn.execute("UPDATE execution_contexts SET workloads_json = ? WHERE id = ?",
                 (json.dumps(workloads), run.context_id))
    conn.commit()
    before = snapshot_v5_rows(conn)
    try:
        report = orchestrator.replay_assessment(conn, run.id)
    except Exception as error:
        pytest.fail(f"an incomplete capture raised {type(error).__name__} instead of unknown inputs: {error}")
    assert report.status == "UNKNOWN_MISSING_INPUTS"
    assert report.check_differences == ()
    assert report.event_draft_differences == ()
    assert_v5_rows_preserved(conn, before)


def test_stored_check_inventory_divergence_reports_both_directions(operated):
    conn, _, run = operated
    checks = repo.list_check_results(conn, run.id)
    assert checks
    conn.execute("DELETE FROM check_results WHERE run_id = ?", (run.id,))
    conn.execute(
        "INSERT INTO check_results (id, run_id, check_id, verdict, observed_ref,"
        " expected_ref, reason_code)"
        " VALUES ('cr-decoy', ?, 'task:ghost:task', 'fail', 'output-decoy', NULL,"
        " 'REQUIRED_TASK_MISSING')",
        (run.id,),
    )
    conn.commit()
    try:
        report = orchestrator.replay_assessment(conn, run.id)
    except Exception as error:
        pytest.fail(f"a changed check inventory raised {type(error).__name__} instead of differences: {error}")
    assert report.status == "DIFFERENT"
    kinds = {(item.get("check_id"), item.get("difference"))
             for item in report.check_differences}
    assert ("task:ghost:task", "extra_stored") in kinds
    assert all((check.check_id, "missing_stored") in kinds for check in checks)
    assert report.event_draft_differences
