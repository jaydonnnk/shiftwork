"""S17: an explicit exact-version choice follows stored comparison evidence."""

import shutil
import time

import pytest
from fastapi.testclient import TestClient

from demos.final_pivot import create_v5_sample
from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain.errors import InvalidSealedCase
from shiftwork.sealed import store as sealed_store
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
        "client_request_id": f"investigate-{shift_id}",
    })
    assert investigation.status_code == 201, investigation.text
    a, b = (_candidate(client, shift_id, label) for label in ("A", "B"))
    created = client.post(f"/api/shifts/{shift_id}/experiments", json={
        "kind": "QUALIFYING_COMPARISON",
        "investigation_id": investigation.json()["id"],
        "candidate_a_version_id": a["id"],
        "candidate_b_version_id": b["id"],
        "declared_treatment": "A chooses lowest price; B chooses highest stock",
        "client_request_id": f"compare-{shift_id}",
    })
    assert created.status_code == 202, created.text
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        view = client.get(f"/api/experiments/{created.json()['id']}").json()
        if view["state"] in ("FINALIZED", "FAILED"):
            break
        time.sleep(0.05)
    assert view["outcome"]["status"] == "COMPLETE", view
    assert all(item["eligible"] for item in view["outcome"]["eligibility"])
    return a, b, view


def _choice(comparison, version, prior, key="choice-1", rationale="A answers the required tasks"):
    return {
        "comparison_id": comparison["id"],
        "selected_version_id": version["id"],
        "rationale": rationale,
        "expected_prior_selection_id": prior,
        "client_request_id": key,
    }


def test_exact_choice_revalidates_and_never_changes_on_save_or_retry(session):
    source = session.attempt()
    assert source["state"] == "FINALIZED"
    a, b, comparison = _comparison(session.client, session.shift_id, source["id"])
    prior = session.board()["operating_selection"]["id"]
    path = f"/api/shifts/{session.shift_id}/selections"
    body = _choice(comparison, a, prior)
    assert session.client.post(path, json={**body, "expected_prior_selection_id": None}).status_code == 409
    assert session.client.post(path, json={**body, "selected_version_id": source["artifact_version_id"]}).status_code == 409
    assert session.client.post(path, json={**body, "rationale": "  "}).status_code == 409
    assert len(session.client.get("/api/engagements/bookshop/selections").json()) == 1

    chosen = session.client.post(path, json=body)
    assert chosen.status_code == 201, chosen.text
    selected = chosen.json()
    assert selected["selected_version_id"] == a["id"]
    assert selected["selected_content_hash"] == a["content_hash"]
    assert selected["retained_alternative_version_id"] == b["id"]
    assert selected["comparison_id"] == comparison["id"]
    assert selected["prior_selection_id"] == prior
    assert len(selected["requirement_set_hash"]) == 64
    assert session.client.post(path, json=body).json() == selected
    assert session.client.post(path, json={**body, "rationale": "different"}).status_code == 409
    board = session.board()
    assert board["operating_status"] == "SELECTED"
    assert board["operating_selection"]["id"] == selected["id"]
    assert board["latest_shift"]["operation_allowed"] is True
    assert len(session.client.get("/api/engagements/bookshop/selections").json()) == 2

    session.edit()
    frozen = session.freeze()
    after = session.board()
    assert after["latest_saved_version_id"] == frozen["id"]
    assert after["operating_selection"]["id"] == selected["id"]
    assert after["operating_selection"]["selected_version_id"] == a["id"]

    conn = db.connect(session.db_file)
    try:
        reservation = repo.get_exposure_reservation_for_experiment(conn, comparison["id"])
        orchestrator.retire_comparison_exposure(conn, reservation.id)
    finally:
        conn.close()
    invalid = session.board()
    assert invalid["operating_status"] == "INVALIDATED"
    assert invalid["operating_selection"]["id"] == selected["id"]
    assert invalid["latest_shift"]["operation_allowed"] is False
    assert session.client.post(f"/api/shifts/{session.shift_id}/runs").status_code == 409
    assert session.client.get("/api/engagements/bookshop/selections").json()[-1]["state"] == "INVALIDATED"


def test_choice_rejects_incomplete_drifted_and_changed_requirements(session, tmp_path, monkeypatch):
    source = session.attempt()
    a, _, comparison = _comparison(session.client, session.shift_id, source["id"])
    prior = session.board()["operating_selection"]["id"]
    path = f"/api/shifts/{session.shift_id}/selections"
    body = _choice(comparison, a, prior)

    conn = db.connect(session.db_file)
    try:
        conn.execute("UPDATE experiments SET state = 'PLANNED' WHERE id = ?", (comparison["id"],))
        conn.commit()
    finally:
        conn.close()
    assert session.client.post(path, json=body).status_code == 409
    conn = db.connect(session.db_file)
    try:
        conn.execute("UPDATE experiments SET state = 'FINALIZED' WHERE id = ?", (comparison["id"],))
        # This 409 is reached at the completeness guard: a changed content hash is
        # already candidate_A drift, so the comparison is NOT_COMPARABLE first.
        conn.execute("UPDATE artifact_versions SET content_hash = ? WHERE id = ?", ("f" * 64, a["id"]))
        conn.commit()
    finally:
        conn.close()
    assert session.client.post(path, json=body).status_code == 409
    conn = db.connect(session.db_file)
    try:
        conn.execute("UPDATE artifact_versions SET content_hash = ? WHERE id = ?", (a["content_hash"], a["id"]))
        conn.commit()
    finally:
        conn.close()
    new_mission = tmp_path / "changed-mission.json"
    new_mission.write_bytes(config.PIVOT_MISSION.read_bytes() + b"\n")
    monkeypatch.setattr(config, "PIVOT_MISSION", new_mission)
    assert session.client.post(path, json=body).status_code == 409
    assert len(session.client.get("/api/engagements/bookshop/selections").json()) == 1


def test_failed_first_choice_comparison_keeps_exposure_and_operation_block(tmp_path):
    original = tmp_path / "original.db"
    copied = tmp_path / "copy.db"
    create_v5_sample(original)
    shutil.copy2(original, copied)
    with TestClient(create_app(str(copied))) as client:
        shift_id = client.post("/api/engagements/bookshop/shifts").json()["id"]
        a, b, comparison = _comparison(client, shift_id, "run-v5-0001")
        conn = db.connect(copied)
        try:
            reservation = repo.get_exposure_reservation_for_experiment(conn, comparison["id"])
            before = repo.count_exposure_reservations(conn)
            orchestrator.retire_comparison_exposure(conn, reservation.id)
        finally:
            conn.close()
        refused = client.post(f"/api/shifts/{shift_id}/selections", json=_choice(comparison, a, None))
        assert refused.status_code == 409, refused.text
        assert client.post(f"/api/shifts/{shift_id}/runs").status_code == 409
        assert client.post("/api/engagements/bookshop/shifts").status_code == 409
        assert client.get("/api/engagements/bookshop/selections").json() == []
        retry = client.post(f"/api/shifts/{shift_id}/experiments", json={
            "kind": "QUALIFYING_COMPARISON",
            "investigation_id": client.get(f"/api/shifts/{shift_id}/investigations").json()["latest_investigation_id"],
            "candidate_a_version_id": a["id"],
            "candidate_b_version_id": b["id"],
            "declared_treatment": "try again",
            "client_request_id": "new-comparison-after-failure",
        })
        assert retry.status_code == 409
        conn = db.connect(copied)
        try:
            assert repo.count_exposure_reservations(conn) == before
            assert repo.get_exposure_reservation(conn, reservation.id).state == "INVALIDATED"
        finally:
            conn.close()


def test_new_operation_with_unknown_sealed_check_still_fails_closed(session):
    source = session.attempt()
    conn = db.connect(session.db_file)
    try:
        incident = repo.list_incidents(conn, config.BOOKSHOP_SLUG)[0]
        conn.execute("UPDATE check_results SET check_id = ? WHERE id = ?",
                     ("unknown-new-check", incident.check_result_id))
        conn.commit()
        with pytest.raises(InvalidSealedCase, match="no family file provides"):
            sealed_store.load_drawn_cases(conn, source["id"])
    finally:
        conn.close()


def test_first_choice_unlocks_migrated_shift_only_after_complete_comparison(tmp_path):
    original = tmp_path / "original.db"
    copied = tmp_path / "copy.db"
    create_v5_sample(original)
    original_bytes = original.read_bytes()
    shutil.copy2(original, copied)
    with TestClient(create_app(str(copied))) as client:
        opened = client.post("/api/engagements/bookshop/shifts")
        assert opened.status_code == 201, opened.text
        shift_id = opened.json()["id"]
        assert opened.json()["opening_mode"] == "LEGACY_FIRST_CHOICE"
        assert opened.json()["operation_allowed"] is False
        board = client.get("/api/engagements/bookshop/board").json()
        assert board["latest_run"] is not None, board
        assert board["latest_run"]["id"] == "run-v5-0001"
        assert board["latest_run"]["purpose"] == "LEGACY_OPERATION"
        assert board["requests_run"] == 1
        a, b, comparison = _comparison(client, shift_id, "run-v5-0001")
        assert client.get("/api/engagements/bookshop/board").json()["operating_selection"] is None
        body = _choice(comparison, b, None, key="first-choice", rationale="B passes the same requirements")
        selected = client.post(f"/api/shifts/{shift_id}/selections", json=body)
        assert selected.status_code == 201, selected.text
        assert selected.json()["prior_selection_id"] is None
        assert selected.json()["retained_alternative_version_id"] == a["id"]
        board = client.get("/api/engagements/bookshop/board").json()
        assert board["latest_shift"]["opening_mode"] == "LEGACY_FIRST_CHOICE"
        assert board["latest_shift"]["operation_allowed"] is True
        assert board["operating_selection"]["selected_version_id"] == b["id"]
        started = client.post(f"/api/shifts/{shift_id}/runs")
        assert started.status_code == 202, started.text
        assert started.json()["artifact_version_id"] == b["id"]
        assert started.json()["selection_id"] == selected.json()["id"]
        assert client.get(f"/api/runs/{started.json()['id']}").json()["state"] == "FINALIZED"
        assert client.get("/api/incidents/BWB-v5-01").json()["state"] == "CLOSED_UNRESOLVED"
        closed = client.post(f"/api/shifts/{shift_id}/close")
        assert closed.status_code == 200, closed.text
        assert closed.json()["state"] == "closed"
        replay = client.post(f"/api/shifts/{shift_id}/selections", json=body)
        assert replay.status_code == 201, replay.text
        assert replay.json() == selected.json()
        assert len(client.get("/api/engagements/bookshop/selections").json()) == 1
        changed = client.post(f"/api/shifts/{shift_id}/selections", json={
            **body, "rationale": "a different choice after close",
        })
        assert changed.status_code == 409, changed.text
        fresh = client.post(f"/api/shifts/{shift_id}/selections", json={
            **body, "client_request_id": "new-choice-after-close",
        })
        assert fresh.status_code == 409, fresh.text
        next_shift = client.post("/api/engagements/bookshop/shifts")
        assert next_shift.status_code == 201, next_shift.text
        foreign = client.post(
            f"/api/shifts/{next_shift.json()['id']}/selections", json=body)
        assert foreign.status_code == 409, foreign.text
    assert original.read_bytes() == original_bytes


def test_choice_refuses_an_ineligible_candidate_and_still_accepts_the_eligible_one(
    session, monkeypatch
):
    """Obligation 25's eligible arm, substituted only at the recompute boundary.

    Stored evidence cannot reach COMPLETE plus ineligible offline: editing a
    recorded assessment adds ``public_assessment`` drift and editing
    ``resource_limits_json`` adds ``frozen_context`` drift. Every stored row here
    is real; only the recomputed outcome reports A as mandatorily blocked.
    """
    source = session.attempt()
    a, b, comparison = _comparison(session.client, session.shift_id, source["id"])
    prior = session.board()["operating_selection"]["id"]
    path = f"/api/shifts/{session.shift_id}/selections"
    real_outcome = orchestrator._comparison_outcome

    def ineligible_a(conn, experiment, context, slots):
        outcome = real_outcome(conn, experiment, context, slots)
        if experiment.id != comparison["id"]:
            return outcome
        assert outcome.status == "COMPLETE", outcome.status
        return outcome.model_copy(update={"eligibility": tuple(
            item.model_copy(update={
                "eligible": False,
                "blocking_reason_codes": ("mandatory_public_rule",),
            }) if item.candidate_label == "A" else item
            for item in outcome.eligibility
        )})

    monkeypatch.setattr(orchestrator, "_comparison_outcome", ineligible_a)
    refused = session.client.post(
        path, json=_choice(comparison, a, prior, key="choice-ineligible"))
    assert refused.status_code == 409, refused.text
    assert len(session.client.get("/api/engagements/bookshop/selections").json()) == 1
    chosen = session.client.post(path, json=_choice(
        comparison, b, prior, key="choice-eligible", rationale="B answers the required tasks"))
    assert chosen.status_code == 201, chosen.text
    assert chosen.json()["selected_version_id"] == b["id"]
    assert chosen.json()["retained_alternative_version_id"] == a["id"]
    assert len(session.client.get("/api/engagements/bookshop/selections").json()) == 2


def test_choice_refuses_a_candidate_version_owned_by_another_shift(tmp_path):
    """The ownership arm of the changed-version guard, reached on its own.

    A content-hash change is already caught earlier as candidate drift, so only
    ``version.shift_id`` reaches this arm while the comparison stays COMPLETE.
    """
    original = tmp_path / "original.db"
    copied = tmp_path / "copy.db"
    create_v5_sample(original)
    shutil.copy2(original, copied)
    with TestClient(create_app(str(copied))) as client:
        shift_id = client.post("/api/engagements/bookshop/shifts").json()["id"]
        a, _, comparison = _comparison(client, shift_id, "run-v5-0001")
        path = f"/api/shifts/{shift_id}/selections"
        body = _choice(comparison, a, None, key="ownership")
        conn = db.connect(copied)
        try:
            conn.execute("UPDATE artifact_versions SET shift_id = 'bookshop-shift-01' WHERE id = ?",
                         (a["id"],))
            conn.commit()
        finally:
            conn.close()
        refused = client.post(path, json=body)
        assert refused.status_code == 409, refused.text
        assert client.get("/api/engagements/bookshop/selections").json() == []
        conn = db.connect(copied)
        try:
            conn.execute("UPDATE artifact_versions SET shift_id = ? WHERE id = ?",
                         (shift_id, a["id"]))
            conn.commit()
        finally:
            conn.close()
        assert client.post(path, json=body).status_code == 201


def test_legacy_investigation_exception_is_narrow(tmp_path):
    """The approved S6.0 exception admits only the prior closed v5 shift's own run.

    Each stored mutation falsifies exactly one conjunct, with the unmutated 201
    before and after as the positive control. Two conjuncts are not independently
    falsifiable offline: the public API cannot open a successor while its
    predecessor is still open, so ``state == "closed"`` never varies, and the v5
    sample holds one prior shift, so ``seq == shift.seq - 1`` never varies.
    """
    original = tmp_path / "original.db"
    copied = tmp_path / "copy.db"
    create_v5_sample(original)
    shutil.copy2(original, copied)
    with TestClient(create_app(str(copied))) as client:
        shift_id = client.post("/api/engagements/bookshop/shifts").json()["id"]
        path = f"/api/shifts/{shift_id}/investigations"

        def investigate(key):
            return client.post(path, json={
                "source_run_id": "run-v5-0001", "source_request_ordinal": 1,
                "cause": "the old response omits a required task",
                "falsifier": "the frozen request receives every required task result",
                "public_test": "check every required task independently",
                "client_request_id": key,
            })

        def mutate(sql, params):
            conn = db.connect(copied)
            try:
                conn.execute(sql, params)
                conn.commit()
            finally:
                conn.close()

        assert investigate("legacy-positive").status_code == 201
        mutate("UPDATE shifts SET opening_mode = 'STANDARD' WHERE id = 'bookshop-shift-01'", ())
        assert investigate("legacy-opening-mode").status_code == 409
        mutate("UPDATE shifts SET opening_mode = NULL WHERE id = 'bookshop-shift-01'", ())
        mutate("UPDATE runs SET purpose = 'OPERATION' WHERE id = 'run-v5-0001'", ())
        assert investigate("legacy-run-purpose").status_code == 409
        mutate("UPDATE runs SET purpose = 'LEGACY_OPERATION' WHERE id = 'run-v5-0001'", ())
        assert investigate("legacy-restored").status_code == 201
        conn = db.connect(copied)
        try:
            assert repo.count_investigations(conn) == 2
        finally:
            conn.close()
