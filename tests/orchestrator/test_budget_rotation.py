"""Budget controller-side, atomic reservation, rotation draws and exhaustion (tests 24-27).

Spec source: program design S6.F and the Slice 7 requirements. Every assertion here
reads the database or the API after real HTTP requests; no run is mocked and no
draw is fabricated. The leak-response clause (ADR 0001): retiring a compromised
rotation group invalidates its dependent attempts by state change, nothing is
deleted, and a refill proves nothing.
"""

import sqlite3
import threading

import pytest
from fastapi.testclient import TestClient

from conftest import ATTEMPT_TRANSCRIPTS, STALE_ANSWER, family_cases, retarget
from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain.errors import RotationMisconfigured
from shiftwork.evaluator.evaluator import expected_ref_for
from shiftwork.sealed import rotation
from shiftwork.sealed import store as sealed_store
from shiftwork.store import db, repo


@pytest.fixture(name="session")
def selected_session(session, select_version_for_test):
    """Run historical budget checks against their frozen learner version.

    The test-only choice supplies the S10 prerequisite; S17 owns eligibility.
    """
    select_version_for_test(session.db_file, session.shift_id, session.versions[-1])
    return session


def _rows(db_file, sql: str) -> list[sqlite3.Row]:
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def _counts(db_file, *tables: str) -> tuple[int, ...]:
    return tuple(
        _rows(db_file, f"SELECT COUNT(*) AS n FROM {table}")[0]["n"] for table in tables
    )


def _draws_of(db_file, run_id: str) -> list[sqlite3.Row]:
    return _rows(
        db_file,
        f"SELECT family, variant_ref, cycle, state FROM rotation_draws WHERE run_id = '{run_id}' ORDER BY family",
    )


def test_budget_enforced_controller_side(session):
    # Test 24: the (limit+1)th run POST is refused with 409 and inserts no run
    # row. The limit is the seeded engagement config's, not a client-supplied
    # number, so the UI cannot talk the controller past it.
    limit = session.board()["attempt_limit"]
    assert limit == 3
    for index, transcript in enumerate(ATTEMPT_TRANSCRIPTS, start=1):
        run = session.attempt(transcript)
        assert run["state"] == "FINALIZED", run
        assert run["attempt_number"] == index

    runs_before, draws_before = _counts(session.db_file, "runs", "rotation_draws")
    refused = session.client.post(f"/api/shifts/{session.shift_id}/runs")
    assert refused.status_code == 409, refused.text
    assert "budget" in refused.json()["detail"], refused.text

    assert _counts(session.db_file, "runs", "rotation_draws") == (runs_before, draws_before)
    assert runs_before == limit
    assert draws_before == limit * len(config.BOOKSHOP_FAMILIES)
    assert session.board()["attempts_remaining"] == 0


def test_reservation_fault_rolls_back_the_whole_reservation(session, monkeypatch):
    # Test 25, clause 2: a fault between the run insertion and the draw insertion
    # leaves no run row and no partial draws. The reservation is one transaction.
    conn = db.connect(session.db_file)
    try:
        original = repo.insert_rotation_draw
        calls = []

        def explode(connection, draw):
            calls.append(draw)
            raise RuntimeError("injected fault between run insertion and draw insertion")

        monkeypatch.setattr(repo, "insert_rotation_draw", explode)
        with pytest.raises(RuntimeError, match="injected fault"):
            orchestrator.start_run(conn, session.shift_id)
        assert calls, "the fault did not fire; this check would be vacuous"
        assert not conn.in_transaction, "the failed reservation left a transaction open"
        # The connection still works: the rollback left no poisoned state.
        assert conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM rotation_draws").fetchone()[0] == 0
    finally:
        monkeypatch.setattr(repo, "insert_rotation_draw", original)
        conn.close()

    assert _counts(session.db_file, "runs", "rotation_draws") == (0, 0)
    assert session.board()["attempts_remaining"] == 3
    # The same reservation then succeeds unchanged: the fault was the only cause.
    run = session.attempt()
    assert run["state"] == "FINALIZED"
    assert len(_draws_of(session.db_file, run["id"])) == len(config.BOOKSHOP_FAMILIES)


def test_two_concurrent_boundary_posts_reserve_exactly_once(session, monkeypatch):
    # Test 25, clause 1: two concurrent POSTs at the boundary create exactly one
    # run row and one draw per enabled family - no orphan reservations, no
    # double-spend of the last attempt.
    session.attempt()
    session.attempt()
    assert session.board()["attempts_remaining"] == 1

    second = TestClient(create_app(str(session.db_file)))
    barrier = threading.Barrier(2)
    results: dict[str, tuple[int, str]] = {}

    def post(name: str, client: TestClient) -> None:
        barrier.wait(timeout=10)
        response = client.post(f"/api/shifts/{session.shift_id}/runs")
        results[name] = (response.status_code, response.text)

    with second:
        threads = [
            threading.Thread(target=post, args=(name, client))
            for name, client in (("a", session.client), ("b", second))
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
            assert not thread.is_alive(), "a boundary POST did not return"

    assert sorted(status for status, _ in results.values()) == [202, 409], results
    assert _counts(session.db_file, "runs", "rotation_draws") == (
        3,
        3 * len(config.BOOKSHOP_FAMILIES),
    )
    latest = _rows(session.db_file, "SELECT attempt_number, state FROM runs ORDER BY attempt_number")
    assert [row["attempt_number"] for row in latest] == [1, 2, 3]
    assert session.board()["attempts_remaining"] == 0


def test_rotation_draws_unexposed_variant(session, tmp_path, restart, monkeypatch):
    # Test 26: all three attempts consume distinct variants per family; a failed
    # run still consumes its committed reservation; a restart cannot redraw an
    # exposed variant, and evaluation uses only the saved identities.
    first = session.attempt()
    assert first["state"] == "FINALIZED"
    # A run that fails at execute still consumed its reservation: the override
    # replays a transcript authored for the thin snapshot on a run bound to the
    # fuller one, so the recorded adapter's own hash check refuses it.
    failed = session.attempt(config.FIXTURE_DIR / "runs" / "thin_stale.json")
    assert failed["state"] == "FAILED", failed
    assert failed["failure_kind"] == "PROVISION_FAILED", failed
    third = session.attempt()
    assert third["state"] == "FINALIZED"

    runs = session.board()["latest_run"]
    assert runs["attempt_number"] == 3
    per_family: dict[str, list[str]] = {}
    for run_id in (first["id"], failed["id"], third["id"]):
        draws = _draws_of(session.db_file, run_id)
        assert len(draws) == len(config.BOOKSHOP_FAMILIES), draws
        assert all(draw["state"] == "active" for draw in draws), draws
        for draw in draws:
            per_family.setdefault(draw["family"], []).append(draw["variant_ref"])
    for family, refs in per_family.items():
        assert len(refs) == 3 and len(set(refs)) == 3, f"{family} redrew a variant: {refs}"

    # Each run executed the stimulus prefix of the ordinal its draws bind, so
    # later stimuli stayed absent until their run.
    batches = _rows(
        session.db_file, "SELECT attempt_number, request_batch_ref FROM runs ORDER BY attempt_number"
    )
    assert [row["request_batch_ref"] for row in batches] == list(config.BOOKSHOP_ATTEMPT_BATCHES[:3])
    assert [row["request_batch_ref"] for row in batches] != ["thin.jsonl"] * 3

    # Restart: the draws are read back, never re-selected, and the recorded
    # checks carry the opaque digest of exactly the drawn variants.
    restarted = restart(session.db_file)
    conn = db.connect(session.db_file)
    try:
        loaded = sealed_store.load_drawn_cases(conn, first["id"])
        index = sealed_store.case_index()
        expected_refs = {expected_ref_for(case) for case in loaded.cases}
        stored = repo.list_check_results(conn, first["id"])
        assert {result.expected_ref for result in stored} == expected_refs
        assert {draw.variant_ref for draw in repo.list_rotation_draws_for_run(conn, first["id"])} == {
            rotation.variant_ref(case) for case in loaded.cases
        }, "the evaluated cases are not the persisted draws"

        # A fresh selection after the restart skips every exposed variant,
        # including the failed run's draws.
        exposed = {draw.variant_ref for draw in repo.list_rotation_draws(conn, config.BOOKSHOP_SLUG)}
        assert len(exposed) == 3 * len(config.BOOKSHOP_FAMILIES)
        for family in config.BOOKSHOP_FAMILIES:
            chosen = rotation.select_variant(family, sealed_store.load_family(family).cases, exposed)
            assert rotation.variant_ref(chosen) not in exposed
    finally:
        conn.close()
        assert index  # the index the digest comparison used is real

    # The restart's own attempt draws the next unexposed variants only, so a
    # restart cannot redraw what the closed app already exposed.
    session.client.post(f"/api/shifts/{session.shift_id}/close")
    refused = restarted.client.post(f"/api/shifts/{session.shift_id}/runs")
    assert refused.status_code == 409, refused.text


def test_rotation_exhaustion_fail_closed(session, sealed_inventory):
    # Test 27: one exhausted family refuses the whole run without rows or
    # partial draws; a refill rejects reused identities, appends new variants
    # and increments the cycle without deleting prior exposure records.
    all_cases = family_cases(sealed_store.POLICY_EXCEPTION)
    assert len(all_cases) == 6, "the checked-in family changed size; update this test"
    limited = all_cases[:1]
    sealed_inventory["publish"](sealed_store.POLICY_EXCEPTION, limited, cycle=1)
    assert sealed_store.family_cycle(sealed_store.POLICY_EXCEPTION) == 1

    first = session.attempt()
    assert first["state"] == "FINALIZED", first
    draws = _draws_of(session.db_file, first["id"])
    assert len(draws) == len(config.BOOKSHOP_FAMILIES)
    assert {draw["cycle"] for draw in draws} == {1}
    before = _counts(session.db_file, "runs", "rotation_draws")

    # The other two families still have unexposed variants; the run is refused
    # whole, and no family receives a partial draw.
    refused = session.client.post(f"/api/shifts/{session.shift_id}/runs")
    assert refused.status_code == 409, refused.text
    assert "never-exposed variant" in refused.json()["detail"], refused.text
    assert _counts(session.db_file, "runs", "rotation_draws") == before

    # A refill that reuses an exposed identity is rejected, so a relabelled copy
    # can never count as a new holdout.
    exposed = {draw["variant_ref"] for draw in _rows(session.db_file, "SELECT variant_ref FROM rotation_draws")}
    refill = [
        sealed_store.load_family(sealed_store.POLICY_EXCEPTION).cases[0],  # the exposed variant
        *[case for case in _refill_cases(all_cases[1:])],
    ]
    with pytest.raises(RotationMisconfigured, match="reuses the exposed identity"):
        rotation.validate_refill(refill, exposed)
    repeated = _refill_cases(all_cases[1:2])
    with pytest.raises(RotationMisconfigured, match="repeats the identity"):
        rotation.validate_refill([*repeated, *repeated], exposed)

    # A genuine refill: the remaining authored variants appended, cycle bumped.
    genuine = _refill_cases(all_cases[1:])
    rotation.validate_refill(genuine, exposed)
    sealed_inventory["publish"](sealed_store.POLICY_EXCEPTION, all_cases, cycle=2)
    assert sealed_store.family_cycle(sealed_store.POLICY_EXCEPTION) == 2

    second = session.attempt()
    assert second["state"] == "FINALIZED", second
    refilled = _draws_of(session.db_file, second["id"])
    assert {draw["family"]: draw["cycle"] for draw in refilled}[sealed_store.POLICY_EXCEPTION] == 2
    new_refs = {
        draw["variant_ref"]
        for draw in refilled
        if draw["family"] == sealed_store.POLICY_EXCEPTION
    }
    assert new_refs and not (new_refs & exposed), "the refill redrew an exposed variant"
    # Prior exposure records are retained, unchanged, next to the new draw.
    retained = _rows(
        session.db_file,
        f"SELECT variant_ref, cycle, state FROM rotation_draws WHERE family = '{sealed_store.POLICY_EXCEPTION}' ORDER BY rowid",
    )
    assert len(retained) == 2
    assert retained[0]["variant_ref"] in exposed and retained[0]["cycle"] == 1
    assert retained[0]["state"] == "active"


def _refill_cases(raw_cases: list[dict]):
    from shiftwork.evaluator.evaluator import SealedCase

    return [SealedCase.model_validate(raw) for raw in raw_cases]


def test_retired_rotation_group_invalidates_without_deleting(session):
    # Leak response (ADR 0001, Slice 7): retiring a compromised group invalidates
    # its dependent attempts by state change. Rows, captures and the run itself
    # stay readable; a refill is not proof of invalidation.
    run = session.attempt()
    conn = db.connect(session.db_file)
    try:
        before_rows = _rows(session.db_file, "SELECT id, variant_ref, state FROM rotation_draws ORDER BY rowid")
        outputs_before = [
            (row["id"], row["body"], row["request_text"]) for row in _rows(session.db_file, "SELECT id, body, request_text FROM run_outputs")
        ]
        retired = repo.invalidate_rotation_group(conn, config.BOOKSHOP_SLUG, sealed_store.STALE_INFORMATION)
        conn.commit()
        assert retired == 1, "the retired group's active draws were not invalidated"
        after_rows = repo.list_rotation_draws(conn, config.BOOKSHOP_SLUG)
        assert repo.invalidated_run_ids(conn, config.BOOKSHOP_SLUG) == [run["id"]]
        assert repo.get_run(conn, run["id"]) is not None

        # Nothing deleted: every row still exists, exactly one changed state.
        assert len(after_rows) == len(before_rows)
        changed = [
            draw for draw in after_rows if (draw.variant_ref, draw.state.value) == (
                next(row["variant_ref"] for row in before_rows if row["id"] == draw.id),
                "invalidated",
            )
        ]
        assert len(changed) == 1
        assert {draw.state.value for draw in after_rows if draw.family != sealed_store.STALE_INFORMATION} == {"active"}

        # Captures and the injected refill are not proof of invalidation: the
        # invalidated draw stays invalidated after a new variant is drawn.
        assert [
            (row["id"], row["body"], row["request_text"]) for row in _rows(session.db_file, "SELECT id, body, request_text FROM run_outputs")
        ] == outputs_before
        session.attempt()
        assert repo.invalidated_run_ids(conn, config.BOOKSHOP_SLUG) == [run["id"]]
        refilled = repo.list_rotation_draws_for_run(
            conn, _rows(session.db_file, "SELECT id FROM runs ORDER BY rowid")[-1]["id"]
        )
        assert len(refilled) == len(config.BOOKSHOP_FAMILIES)
        assert all(draw.state.value == "active" for draw in refilled)
    finally:
        conn.close()


def test_invalidate_rotation_group_retires_only_active_draws(session):
    # The state filter is load-bearing: a family that already carries an
    # invalidated draw and has since drawn a new active variant retires exactly
    # the active row. Without the filter the call re-retires the invalidated row
    # too, and the returned count stops meaning "draws retired by this call".
    family = sealed_store.STALE_INFORMATION
    first = session.attempt()

    conn = db.connect(session.db_file)
    try:
        assert repo.invalidate_rotation_group(conn, config.BOOKSHOP_SLUG, family) == 1
        conn.commit()
    finally:
        conn.close()

    second = session.attempt()
    conn = db.connect(session.db_file)
    try:
        states = [
            row["state"]
            for row in _rows(
                session.db_file,
                f"SELECT state FROM rotation_draws WHERE family = '{family}' ORDER BY rowid",
            )
        ]
        assert states == ["invalidated", "active"], (
            f"premise failed: expected one invalidated draw plus one fresh active draw, got {states}"
        )
        retired = repo.invalidate_rotation_group(conn, config.BOOKSHOP_SLUG, family)
        conn.commit()
        assert retired == 1, (
            f"the state filter must scope to active draws only: retired {retired} rows, expected 1"
        )
        states_after = [
            row["state"]
            for row in _rows(
                session.db_file,
                f"SELECT state FROM rotation_draws WHERE family = '{family}' ORDER BY rowid",
            )
        ]
        assert states_after == ["invalidated", "invalidated"]
        untouched = {
            row["state"]
            for row in _rows(
                session.db_file,
                f"SELECT state FROM rotation_draws WHERE family != '{family}'",
            )
        }
        assert untouched == {"active"}, "other families' draws were touched"
        assert sorted(repo.invalidated_run_ids(conn, config.BOOKSHOP_SLUG)) == sorted(
            [first["id"], second["id"]]
        )
        assert repo.get_run(conn, first["id"]) is not None
        assert repo.get_run(conn, second["id"]) is not None
    finally:
        conn.close()


def test_repair_resolution_same_version_never_resolves(session):
    # Test 34 negative 1: re-running the same artifact version never resolves an
    # incident, even when the regression and drawn acceptance both pass. The
    # resolution gate requires a NEW version (program design S5.7).
    run_one = session.attempt()
    assert run_one["state"] == "FINALIZED"
    board = session.board()
    assert len(board["incidents"]) == 3, board["incidents"]

    # Attempt 2 with the SAME version (no edit, no freeze): regressions and
    # drawn cases pass, but the version gate blocks resolution.
    run_two = session.attempt()
    assert run_two["state"] == "FINALIZED"
    board = session.board()
    assert len(board["incidents"]) == 3, (
        f"same-version run resolved incidents: {board['incidents']}"
    )
    assert run_two["artifact_version_id"] == run_one["artifact_version_id"]


def test_repair_resolution_failing_acceptance_never_resolves(
    session, tmp_path, select_version_for_test
):
    # Test 34 negative 2: a new version that passes the linked regression but
    # FAILS the drawn (never-exposed) acceptance case never resolves the incident.
    run_one = session.attempt()
    assert run_one["state"] == "FINALIZED"
    assert len(session.board()["incidents"]) == 3

    # Freeze a new version (the repair).
    session.edit()
    repaired = session.freeze()
    select_version_for_test(session.db_file, session.shift_id, repaired["id"])

    # Attempt 2 with a transcript where ordinal 1 passes (regression) but
    # ordinal 2 fails (the drawn acceptance case): MISSING_EVIDENCE on ordinal 2.
    broken = retarget(
        tmp_path,
        ATTEMPT_TRANSCRIPTS[1],
        {2: STALE_ANSWER},
        "repair_02_fail_ordinal_2.json",
    )
    run_two = session.attempt(broken)
    assert run_two["state"] == "FINALIZED"
    board = session.board()
    # The original incidents from run_one must still be OPEN: the failing
    # acceptance case blocked resolution. New incidents may also have opened
    # from the failing ordinal 2, so check the originals specifically.
    original_ids = {inc["id"] for inc in session.board()["incidents"] if inc["opening_run_id"] == run_one["id"]}
    assert len(original_ids) == 3, (
        f"failing acceptance resolved incidents from run_one: {original_ids}"
    )
    assert run_two["artifact_version_id"] != run_one["artifact_version_id"]


def test_future_stimuli_absent_until_their_run(session):
    # Test 18 clause: later customer stimuli stay absent until their run. Attempt k
    # executes the prefix 1..k; ordinal k+1 must not appear in attempt k's outputs.
    run_one = session.attempt()
    assert run_one["state"] == "FINALIZED"
    outputs_one = _rows(session.db_file, f"SELECT request_ordinal FROM run_outputs WHERE run_id = '{run_one['id']}'")
    assert [row["request_ordinal"] for row in outputs_one] == [1]

    run_two = session.attempt()
    assert run_two["state"] == "FINALIZED"
    outputs_two = _rows(session.db_file, f"SELECT request_ordinal FROM run_outputs WHERE run_id = '{run_two['id']}'")
    assert [row["request_ordinal"] for row in outputs_two] == [1, 2]

    run_three = session.attempt()
    assert run_three["state"] == "FINALIZED"
    outputs_three = _rows(session.db_file, f"SELECT request_ordinal FROM run_outputs WHERE run_id = '{run_three['id']}'")
    assert [row["request_ordinal"] for row in outputs_three] == [1, 2, 3]

    # No run ever carries an ordinal beyond its attempt number.
    all_outputs = _rows(session.db_file, "SELECT run_id, request_ordinal FROM run_outputs ORDER BY run_id, request_ordinal")
    for row in all_outputs:
        run_row = _rows(session.db_file, f"SELECT attempt_number FROM runs WHERE id = '{row['run_id']}'")[0]
        assert row["request_ordinal"] <= run_row["attempt_number"], (
            f"run {row['run_id']} (attempt {run_row['attempt_number']}) carries ordinal {row['request_ordinal']}"
        )


def test_incident_reconstruction_after_restart(session, restart):
    # Test 23 clause: after a restart, incidents and draws reconstruct from
    # tables, not from in-memory state. A fresh app instance over the same
    # database sees the same incidents, draws and board counters.
    run_one = session.attempt()
    assert run_one["state"] == "FINALIZED"
    board_before = session.board()
    assert len(board_before["incidents"]) == 3

    restarted = restart(session.db_file)
    board_after = restarted.board()
    assert len(board_after["incidents"]) == 3
    assert board_after["attempts_used"] == board_before["attempts_used"]
    assert board_after["attempts_remaining"] == board_before["attempts_remaining"]
    assert board_after["ledger_event_count"] == board_before["ledger_event_count"]
    assert board_after["chain_status"] == "VALID"

    # The draws are read back from the table, not re-selected.
    conn = db.connect(session.db_file)
    try:
        draws = repo.list_rotation_draws_for_run(conn, run_one["id"])
        assert len(draws) == len(config.BOOKSHOP_FAMILIES)
        incidents = repo.list_incidents(conn, config.BOOKSHOP_SLUG)
        assert len(incidents) == 3
        assert all(inc.state.value == "OPEN" for inc in incidents)
        # Each incident links to a real check result and run.
        for inc in incidents:
            assert repo.get_run(conn, inc.opening_run_id) is not None
            results = repo.list_check_results(conn, inc.opening_run_id)
            assert any(r.id == inc.check_result_id for r in results), (
                f"incident {inc.id} links to check_result {inc.check_result_id} which its run does not carry"
            )
    finally:
        conn.close()


def test_select_variant_ordinal_tie_prefers_earlier_file_order():
    # Behavior spec: among unexposed cases sharing the lowest ordinal, the
    # earlier one in the cases sequence wins. The explicit cases.index(case)
    # tiebreak term is redundant for removal (min() keeps the first minimum over
    # the order-preserving filter) but load-bearing for reversal, which is the
    # behavior this test fails on.
    from shiftwork.evaluator.evaluator import SealedCase

    case_a = SealedCase.model_validate({
        "id": "tiebreak-a", "check_id": "chk-tiebreak-a", "family": "test_family",
        "schema_version": 1, "request_ordinals": [3],
        "expected": {"action": "answer", "claims": [], "evidence_refs": []},
    })
    case_b = SealedCase.model_validate({
        "id": "tiebreak-b", "check_id": "chk-tiebreak-b", "family": "test_family",
        "schema_version": 1, "request_ordinals": [3],
        "expected": {"action": "answer", "claims": [], "evidence_refs": []},
    })
    cases = [case_a, case_b]
    chosen = rotation.select_variant("test_family", cases, set())
    assert chosen.id == "tiebreak-a", f"tiebreak did not use file order: got {chosen.id}"
    # With case_a exposed, case_b wins.
    exposed = {rotation.variant_ref(case_a)}
    chosen2 = rotation.select_variant("test_family", cases, exposed)
    assert chosen2.id == "tiebreak-b"


def test_select_variant_excludes_exposed_variants():
    # The policy half of draw-without-replacement: every exposed ref is skipped,
    # so a variant the engagement already consumed can never come back. The
    # database's UNIQUE (engagement_slug, variant_ref) constraint is the second,
    # louder guard behind this one.
    from shiftwork.evaluator.evaluator import SealedCase

    case_a = SealedCase.model_validate({
        "id": "exposed-a", "check_id": "chk-exposed-a", "family": "test_family",
        "schema_version": 1, "request_ordinals": [1],
        "expected": {"action": "answer", "claims": [], "evidence_refs": []},
    })
    case_b = SealedCase.model_validate({
        "id": "exposed-b", "check_id": "chk-exposed-b", "family": "test_family",
        "schema_version": 1, "request_ordinals": [2],
        "expected": {"action": "answer", "claims": [], "evidence_refs": []},
    })
    exposed = {rotation.variant_ref(case_a)}
    assert rotation.unexposed_cases([case_a, case_b], exposed) == (case_b,)
    assert rotation.select_variant("test_family", [case_a, case_b], exposed).id == "exposed-b"


def test_repair_resolution_failing_regression_never_resolves(
    session, tmp_path, select_version_for_test
):
    # Test 34 negative 3: a new version whose drawn acceptance passes but whose
    # linked REGRESSION fails never resolves the incident. The resolution gate
    # requires both to pass (program design S5.7).
    run_one = session.attempt()
    assert run_one["state"] == "FINALIZED"
    assert len(session.board()["incidents"]) == 3

    # Freeze a new version (the repair).
    session.edit()
    repaired = session.freeze()
    select_version_for_test(session.db_file, session.shift_id, repaired["id"])

    # Attempt 2 with a transcript where ordinal 1 FAILS (the regression) but
    # ordinal 2 passes (the drawn acceptance): the regression gate blocks.
    broken = retarget(
        tmp_path,
        ATTEMPT_TRANSCRIPTS[1],
        {1: STALE_ANSWER},
        "repair_02_fail_ordinal_1.json",
    )
    run_two = session.attempt(broken)
    assert run_two["state"] == "FINALIZED"
    # The original incidents must still be OPEN: the failing regression blocked
    # resolution even though the acceptance passed and the version is new.
    original_open = [
        inc for inc in session.board()["incidents"]
        if inc["opening_run_id"] == run_one["id"]
    ]
    assert len(original_open) == 3, (
        f"failing regression resolved incidents: {original_open}"
    )
    assert run_two["artifact_version_id"] != run_one["artifact_version_id"]


def test_shared_ordinal_rejects_mismatched_draws():
    # shared_ordinal raises RotationMisconfigured when drawn variants bind
    # different request ordinals; the misconfiguration is never silently
    # resolved. The exact type is asserted: a crash from the same missing guard
    # is also a failure, so this test catches incidental exceptions too.
    from shiftwork.evaluator.evaluator import SealedCase

    case_a = SealedCase.model_validate({
        "id": "ord-a", "check_id": "chk-ord-a", "family": "fam_a",
        "schema_version": 1, "request_ordinals": [1],
        "expected": {"action": "answer", "claims": [], "evidence_refs": []},
    })
    case_b = SealedCase.model_validate({
        "id": "ord-b", "check_id": "chk-ord-b", "family": "fam_b",
        "schema_version": 1, "request_ordinals": [2],
        "expected": {"action": "answer", "claims": [], "evidence_refs": []},
    })
    raised: Exception | None = None
    try:
        rotation.shared_ordinal({"fam_a": case_a, "fam_b": case_b})
    except Exception as exc:
        raised = exc
    assert isinstance(raised, RotationMisconfigured), (
        f"expected RotationMisconfigured, got {raised!r}"
    )
    assert "share exactly one request ordinal" in str(raised)


def test_shared_ordinal_rejects_multi_ordinal_variant():
    # A drawn variant that binds several request ordinals cannot be scored
    # against one stimulus prefix: shared_ordinal raises instead of silently
    # picking the first ordinal.
    from shiftwork.evaluator.evaluator import SealedCase

    case = SealedCase.model_validate({
        "id": "ord-multi", "check_id": "chk-ord-multi", "family": "fam_a",
        "schema_version": 1, "request_ordinals": [1, 2],
        "expected": {"action": "answer", "claims": [], "evidence_refs": []},
    })
    raised: Exception | None = None
    try:
        rotation.shared_ordinal({"fam_a": case})
    except Exception as exc:
        raised = exc
    assert isinstance(raised, RotationMisconfigured), (
        f"expected RotationMisconfigured, got {raised!r}"
    )
    assert "binds several request ordinals" in str(raised)


def test_resolved_incident_regression_excluded_from_later_run(
    session, select_version_for_test
):
    # load_drawn_cases includes open-incident regressions but EXCLUDES resolved
    # ones: once an incident resolves, repeating its old stimulus is not part of
    # a later run's evidence (program design S5.3).
    run_one = session.attempt()
    assert run_one["state"] == "FINALIZED"
    assert len(session.board()["incidents"]) == 3

    # Repair: new version, attempt 2 resolves all incidents.
    session.edit()
    repaired = session.freeze()
    select_version_for_test(session.db_file, session.shift_id, repaired["id"])
    run_two = session.attempt()
    assert run_two["state"] == "FINALIZED"
    assert session.board()["incidents"] == []

    # Attempt 3: load_drawn_cases must NOT include the resolved incidents'
    # regression cases (ordinal 1 variants from run_one's draws).
    run_three = session.attempt()
    assert run_three["state"] == "FINALIZED"

    conn = db.connect(session.db_file)
    try:
        drawn_three = sealed_store.load_drawn_cases(conn, run_three["id"])
        drawn_refs_three = {rotation.variant_ref(case) for case in drawn_three.cases}
        # The draws for run_three are ordinal-3 variants only (no regressions).
        persisted_draws = repo.list_rotation_draws_for_run(conn, run_three["id"])
        persisted_refs = {draw.variant_ref for draw in persisted_draws}
        assert drawn_refs_three == persisted_refs, (
            f"load_drawn_cases included extra cases beyond the persisted draws: "
            f"{drawn_refs_three - persisted_refs}"
        )
        # Confirm the resolved incidents' cases are NOT in the drawn set.
        run_one_draws = repo.list_rotation_draws_for_run(conn, run_one["id"])
        run_one_refs = {draw.variant_ref for draw in run_one_draws}
        assert not (drawn_refs_three & run_one_refs), (
            f"resolved incident regressions leaked into run_three: {drawn_refs_three & run_one_refs}"
        )
    finally:
        conn.close()
