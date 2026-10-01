"""Slice 8 close and inheritance: program design S5.1/S5.8, tests 32 and 33,
the test 44 "and inherited" clause and the test 10 inheritance-seeds-match clause.

Every check drives the real HTTP surface over a real database on the shipped
recorded binding. Test 33's clauses are split into their own failing-capable
checks: exact-once LIMIT_DECLARED events, the two distinct inheritances on the
next board, in-flight refusal, concurrent and repeated closes, and a fault at
each close boundary. Closing retires unresolved OPEN incidents as
CLOSED_UNRESOLVED rows; the next shift inherits them as incidents and resolves
them on a later passing run of a new version (program design S3.9, S5.7).
"""

import threading
import time

import pytest
from fastapi.testclient import TestClient

from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain.models import IncidentState, RunState
from shiftwork.ledger import chain
from shiftwork.store import db, repo
from tests.orchestrator import pivot_flow

DECLARED = (
    "Shelf stock, price and availability answers only; no delivery or reservation promises.",
    "Answers one request per shift until the batch grows.",
)
CONTRACT = {
    "catalog_version": 2,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
    "response_time_limit_ms": 3000,
    "declared_limits": list(DECLARED),
}
TERMINAL = {"FINALIZED", "FAILED"}


def _call(client: TestClient, method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    assert response.status_code < 400, f"{method} {path} -> {response.status_code}: {response.text}"
    return response.json()


def _open(client: TestClient) -> str:
    shift = _call(client, "POST", "/api/engagements/bookshop/shifts")
    return shift["id"]


def _freeze(client: TestClient, shift_id: str, contract: dict = CONTRACT) -> dict:
    return _call(
        client,
        "POST",
        f"/api/shifts/{shift_id}/artifact/versions",
        json={"contract": contract},
    )


def _attempt(client: TestClient, shift_id: str) -> dict:
    started = _call(client, "POST", f"/api/shifts/{shift_id}/runs")
    deadline = time.monotonic() + 10
    while True:
        run = _call(client, "GET", f"/api/runs/{started['id']}")
        if run["state"] in TERMINAL or time.monotonic() > deadline:
            return run
        time.sleep(0.02)


def _board(client: TestClient, slug: str = "bookshop") -> dict:
    return _call(client, "GET", f"/api/engagements/{slug}/board")


def _ledger(client: TestClient, slug: str = "bookshop") -> dict:
    return _call(client, "GET", f"/api/engagements/{slug}/ledger")


def _events_of(db_file, event_type: str) -> list:
    conn = db.connect(db_file)
    try:
        return [
            event
            for event in repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
            if event.event_type.value == event_type
        ]
    finally:
        conn.close()


@pytest.fixture()
def driven(tmp_path, select_version_for_test):
    """One open shift, one frozen version, one failing attempt: three unresolved incidents."""
    db_file = tmp_path / "close.db"
    with TestClient(create_app(str(db_file))) as client:
        shift_id = _open(client)
        # The learner edits before freezing, so the inherited version is not the
        # shipped template: without this, seeding from inheritance is
        # indistinguishable from seeding the template and test 32's draft
        # assertion cannot fail.
        draft = _call(client, "GET", f"/api/shifts/{shift_id}/artifact")
        files = dict(draft["files"])
        files["service.py"] = files["service.py"] + "\n# shift 1: learner-edited draft\n"
        _call(client, "PUT", f"/api/shifts/{shift_id}/artifact", json={"files": files})
        assert files != {
            name: path.read_text(encoding="utf-8")
            for name, path in sorted(config.PIVOT_STARTER_ARTIFACT_PATHS.items())
        }, (
            "the frozen version must differ from the shipped starter, or seeding "
            "from inheritance cannot be told apart from seeding that starter"
        )
        frozen = _freeze(client, shift_id)
        # Historical executor assertions require this exact test-only choice.
        select_version_for_test(db_file, shift_id, frozen["id"])
        failing = _attempt(client, shift_id)
        assert failing["state"] == "FINALIZED", failing
        board = _board(client)
        assert [incident["state"] for incident in board["incidents"]] == ["OPEN"] * len(
            config.BOOKSHOP_FAMILIES
        ), board["incidents"]
        yield {"client": client, "db_file": db_file, "shift_id": shift_id}


def test_unresolved_limits_follow_the_latest_close(driven, select_version_for_test):
    # A declared limit stays in force until a later close stops declaring it: the
    # projection is the most recent close's set, so a learner who removes the
    # limitation sees it leave the board while the ledger keeps every event.
    client, db_file, shift_id = driven["client"], driven["db_file"], driven["shift_id"]
    _call(client, "POST", f"/api/shifts/{shift_id}/close")
    second = _open(client)
    assert _board(client)["unresolved_limits"] == list(DECLARED)

    dropped = DECLARED[:1]
    reduced = _freeze(client, second, {**CONTRACT, "declared_limits": list(dropped)})
    select_version_for_test(db_file, second, reduced["id"])
    _call(client, "POST", f"/api/shifts/{second}/close")
    third = _open(client)
    board = _board(client)
    assert board["latest_shift"]["id"] == third
    assert board["unresolved_limits"] == list(dropped), (
        "a limit the latest close stopped declaring must leave the projection"
    )

    # Append-only: the dropped limit's original declaration is still in the
    # ledger, and only the retained limit was declared by the second close.
    declared = _events_of(db_file, "LIMIT_DECLARED")
    counts: dict[str, int] = {}
    for event in declared:
        limit = event.payload["declared_limit"]
        counts[limit] = counts.get(limit, 0) + 1
    assert counts == {DECLARED[0]: 2, DECLARED[1]: 1}
    assert {event.cause_refs for event in declared} == {(shift_id,), (second,)}


def test_close_declares_the_inherited_limits_when_a_shift_never_froze(driven):
    # A shift that closes without freezing its own version still declares the
    # limits of the artifact in force, so an inherited limitation cannot silently
    # drop off the board at the next close.
    client, db_file, shift_id = driven["client"], driven["db_file"], driven["shift_id"]
    _call(client, "POST", f"/api/shifts/{shift_id}/close")

    second = _open(client)
    assert _board(client)["unresolved_limits"] == list(DECLARED)
    _call(client, "POST", f"/api/shifts/{second}/close")

    conn = db.connect(db_file)
    try:
        versions = conn.execute(
            "SELECT COUNT(*) AS n FROM artifact_versions WHERE shift_id = ?", (second,)
        ).fetchone()["n"]
        assert versions == 0, "this shift froze a version; the inherited-limit path was not exercised"
    finally:
        conn.close()
    declared = [
        event for event in _events_of(db_file, "LIMIT_DECLARED") if event.cause_refs == (second,)
    ]
    assert sorted(event.payload["declared_limit"] for event in declared) == sorted(DECLARED)
    third = _open(client)
    assert _board(client)["latest_shift"]["id"] == third
    assert _board(client)["unresolved_limits"] == list(DECLARED)


def test_close_shift_records_unresolved_limits(driven):
    # Test 33: LIMIT_DECLARED for the version's declared limits exactly once;
    # unresolved OPEN incidents become CLOSED_UNRESOLVED rows inherited as
    # incidents, never as LIMIT_DECLARED events; the next board shows the two
    # distinct inheritances.
    client, db_file, shift_id = driven["client"], driven["db_file"], driven["shift_id"]
    before = _ledger(client)
    assert [event["event_type"] for event in before["events"]].count("LIMIT_DECLARED") == 0

    closed = _call(client, "POST", f"/api/shifts/{shift_id}/close")
    assert closed["state"] == "closed"
    assert closed["closed_at"] is not None

    declared = _events_of(db_file, "LIMIT_DECLARED")
    assert sorted(event.payload["declared_limit"] for event in declared) == sorted(DECLARED), (
        "closing must declare the version's declared limits exactly once each"
    )
    assert len(declared) == len(DECLARED), "a repeated declaration multiplied a limit"
    for event in declared:
        assert event.cause_refs == (shift_id,)
        assert event.payload["catalog_version"] == CONTRACT["catalog_version"]

    # No incident became a declared limit, and no LIMIT_DECLARED event cites one.
    conn = db.connect(db_file)
    try:
        incidents = repo.list_incidents(conn, config.BOOKSHOP_SLUG)
        assert incidents, "the failing run produced no incident; the close proved nothing"
        assert all(incident.state is IncidentState.CLOSED_UNRESOLVED for incident in incidents)
        incident_ids = {incident.id for incident in incidents}
        for event in declared:
            assert not (set(event.cause_refs) & incident_ids)
    finally:
        conn.close()
    ledger = _ledger(client)
    assert ledger["chain_status"] == "VALID"
    conn = db.connect(db_file)
    try:
        assert (
            chain.verify_chain(repo.list_ledger_events(conn, config.BOOKSHOP_SLUG))
            is chain.ChainStatus.VALID
        ), "the close's events must extend the verified chain"
    finally:
        conn.close()
    assert [event["seq"] for event in ledger["events"]] == list(
        range(1, len(ledger["events"]) + 1)
    )

    # Idempotent: repeating the close returns the closed shift and writes nothing.
    events_before = ledger["events"]
    again = _call(client, "POST", f"/api/shifts/{shift_id}/close")
    assert again["state"] == "closed"
    assert _ledger(client)["events"] == events_before

    # The next shift's board shows declared limits in unresolved_limits and the
    # incidents in incidents: two distinct inheritances.
    next_shift = _open(client)
    board = _board(client)
    assert board["latest_shift"]["id"] == next_shift
    assert board["unresolved_limits"] == list(DECLARED)
    assert {incident["state"] for incident in board["incidents"]} == {"CLOSED_UNRESOLVED"}
    assert len(board["incidents"]) == len(config.BOOKSHOP_FAMILIES)
    assert board["attempts_used"] == 0 and board["attempts_remaining"] == config.DEFAULT_ATTEMPT_LIMIT
    assert board["ledger_event_count"] == len(events_before)


def test_open_shift_seeds_from_inheritance(driven):
    # Test 32: the board after open equals the prior version, the unresolved
    # incidents, the unresolved limits and the ledger summary; the new draft is
    # the inherited version's files; a second open while one shift is open is a
    # conflict.
    client, db_file, shift_id = driven["client"], driven["db_file"], driven["shift_id"]

    # Opening while a shift is open is a conflict (program design S4).
    refusal = client.request("POST", "/api/engagements/bookshop/shifts")
    assert refusal.status_code == 409, refusal.text
    assert "still open" in refusal.json()["detail"]

    _call(client, "POST", f"/api/shifts/{shift_id}/close")
    conn = db.connect(db_file)
    try:
        inherited = repo.get_latest_version_for_engagement(conn, config.BOOKSHOP_SLUG)
        incident_ids = {incident.id for incident in repo.list_incidents(conn, config.BOOKSHOP_SLUG)}
        events = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
    finally:
        conn.close()

    next_shift = _open(client)
    board = _board(client)
    draft = _call(client, "GET", f"/api/shifts/{next_shift}/artifact")

    assert board["latest_version"] is not None, (
        "the board showed no inherited version for the freshly opened shift; the "
        "inherited-version fallback did not fire"
    )
    assert board["latest_version"]["id"] == inherited.id
    assert board["latest_version"]["content_hash"] == inherited.content_hash
    assert draft["files"] == inherited.files
    assert board["unresolved_limits"] == list(DECLARED)
    assert {incident["id"] for incident in board["incidents"]} == incident_ids
    replay_totals: dict[str, int] = {}
    for event in events:
        replay_totals[event.event_type.value] = replay_totals.get(event.event_type.value, 0) + 1
    assert board["ledger_totals"] == replay_totals
    assert board["chain_status"] == "VALID"
    assert board["latest_run"] is None and board["requests_run"] == 0

    # The inherited shift is open too, so a further open is refused the same way.
    second = client.request("POST", "/api/engagements/bookshop/shifts")
    assert second.status_code == 409, second.text


def test_close_refuses_while_a_run_is_in_flight(driven):
    client, db_file, shift_id = driven["client"], driven["db_file"], driven["shift_id"]
    closed_before = _call(client, "POST", f"/api/shifts/{shift_id}/close")
    assert closed_before["state"] == "closed"
    assert _board(client)["latest_shift"]["state"] == "closed"

    # A run that is reserved but not executed must hold the close off; the
    # reservation is real state a close may not abandon silently.
    conn = db.connect(db_file)
    try:
        shift2 = orchestrator.open_next_shift(conn, config.BOOKSHOP_SLUG)
        run = orchestrator.start_run(conn, shift2.id)
        assert run.state is RunState.QUEUED
    finally:
        conn.close()

    refusal = client.request("POST", f"/api/shifts/{shift2.id}/close")
    assert refusal.status_code == 409, refusal.text
    assert "run in flight" in refusal.json()["detail"]
    conn = db.connect(db_file)
    try:
        assert repo.get_shift(conn, shift2.id).state == "open"
        assert [
            event
            for event in repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
            if event.cause_refs == (shift2.id,)
        ] == []
    finally:
        conn.close()


def test_concurrent_closes_write_one_event_set(tmp_path, select_version_for_test):
    db_file = tmp_path / "concurrent.db"
    with TestClient(create_app(str(db_file))) as client:
        shift_id = _open(client)
        frozen = _freeze(client, shift_id)
        select_version_for_test(db_file, shift_id, frozen["id"])
        _attempt(client, shift_id)
        barrier = threading.Barrier(2)
        results: list = []

        def close() -> None:
            conn = db.connect(db_file)
            try:
                barrier.wait(timeout=10)
                results.append(orchestrator.close_shift(conn, shift_id))
            finally:
                conn.close()

        threads = [threading.Thread(target=close) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert len(results) == 2, "a concurrent close raised instead of serializing"
        assert {shift.state for shift in results} == {"closed"}
        assert {shift.closed_at for shift in results} == {results[0].closed_at}, (
            "the two closes recorded different close times; the second one wrote"
        )

    declared = _events_of(db_file, "LIMIT_DECLARED")
    assert len(declared) == len(DECLARED), (
        f"concurrent closes appended a second event set: {len(declared)} LIMIT_DECLARED events"
    )
    conn = db.connect(db_file)
    try:
        assert [event.seq for event in repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)] == list(
            range(1, 1 + len(repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)))
        )
    finally:
        conn.close()


def test_close_fault_leaves_neither_partial_close_nor_partial_events(driven, monkeypatch):
    client, db_file, shift_id = driven["client"], driven["db_file"], driven["shift_id"]
    original_events = _ledger(client)["events"]

    for victim in ("insert_ledger_event", "close_unresolved_incidents", "close_shift"):
        original = getattr(repo, victim)

        def _fail(*args, __original=original, **kwargs):
            raise RuntimeError("injected close-boundary fault")

        monkeypatch.setattr(repo, victim, _fail)
        try:
            with pytest.raises(RuntimeError):
                conn = db.connect(db_file)
                try:
                    orchestrator.close_shift(conn, shift_id)
                finally:
                    conn.close()
        finally:
            monkeypatch.setattr(repo, victim, original)

        conn = db.connect(db_file)
        try:
            assert repo.get_shift(conn, shift_id).state == "open", (
                f"a fault in {victim} still closed the shift"
            )
            assert [
                incident
                for incident in repo.list_incidents(conn, config.BOOKSHOP_SLUG)
                if incident.state is not IncidentState.OPEN
            ] == [], f"a fault in {victim} retired incidents without closing"
        finally:
            conn.close()
        assert _ledger(client)["events"] == original_events, f"a fault in {victim} appended events"


def test_inherited_unresolved_incident_resolves_on_a_later_passing_run(
    driven, select_version_for_test
):
    # A close retires unresolved incidents as CLOSED_UNRESOLVED; the next shift
    # inherits them and a later passing run of a new version resolves them
    # (program design S3.9, S5.7). Without that path the inherited incident would
    # be inert forever.
    client, db_file, shift_id = driven["client"], driven["db_file"], driven["shift_id"]
    _call(client, "POST", f"/api/shifts/{shift_id}/close")
    next_shift = _open(client)
    assert {incident["state"] for incident in _board(client)["incidents"]} == {"CLOSED_UNRESOLVED"}

    # The repair: a new version of the artifact.
    draft = _call(client, "GET", f"/api/shifts/{next_shift}/artifact")
    files = dict(draft["files"])
    files["service.py"] = files["service.py"] + "\n# repair: cite evidence with every claim\n"
    _call(client, "PUT", f"/api/shifts/{next_shift}/artifact", json={"files": files})
    version = _freeze(client, next_shift)
    select_version_for_test(db_file, next_shift, version["id"])

    run = _attempt(client, next_shift)
    assert run["state"] == "FINALIZED", run
    board = _board(client)
    assert board["incidents"] == [], f"inherited incidents did not resolve: {board['incidents']}"

    conn = db.connect(db_file)
    try:
        incidents = repo.list_incidents(conn, config.BOOKSHOP_SLUG)
        assert incidents
        assert all(incident.state is IncidentState.RESOLVED for incident in incidents)
        assert {incident.resolving_version_id for incident in incidents} == {version["id"]}
        resolved = [
            event
            for event in repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
            if event.event_type.value == "INCIDENT_RESOLVED"
        ]
        assert len(resolved) == len(incidents)
        # The inherited regression was re-scored in this same run, not assumed.
        results = repo.list_check_results(conn, run["id"])
        assert results and {result.verdict for result in results} == {"pass"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Slice 20: inheritance of the exact selection, restore ancestry and the
# close-does-not-select clause.
# ---------------------------------------------------------------------------


def test_next_shift_inherits_selection_rationale_alternative_tests_and_limits(tmp_path):
    """Obligation 33: exact IDs and hashes, not counts, survive close and open.

    The retained alternative is deliberately the newest saved version, so the
    inheritance proof would fail if the next shift took the latest save instead
    of the exact selection, and the base ancestry is asserted directly.
    """
    db_file = tmp_path / "inherit-selection.db"
    with TestClient(create_app(str(db_file))) as client:
        flow = pivot_flow.qualified_shift(client)
        before = _board(client)
        assert before["latest_saved_version_id"] == flow["retained_version_id"], (
            "the retained alternative must be the newest saved version for this proof"
        )
        assert before["operating_selection"]["id"] == flow["choice"]["id"]
        assert before["inherited_requirements"] is not None

        closed = _call(client, "POST", f"/api/shifts/{flow['shift_id']}/close")
        assert closed["state"] == "closed"
        closed_ledger = _ledger(client)["events"]
        successor = _call(client, "POST", "/api/engagements/bookshop/shifts")
        board = _board(client)
        selection = board["operating_selection"]

        assert board["latest_shift"]["id"] == successor["id"]
        assert selection["id"] == flow["choice"]["id"]
        assert selection["kind"] == "LEARNER_CHOICE"
        assert selection["selected_version_id"] == flow["selected_version_id"]
        assert selection["selected_content_hash"] == flow["candidates"][
            flow["chosen_label"]]["content_hash"]
        assert selection["comparison_id"] == flow["comparison"]["id"]
        assert selection["retained_alternative_version_id"] == flow["retained_version_id"]
        assert selection["rationale"] == flow["choice"]["rationale"]
        assert selection["prior_selection_id"] == flow["choice"]["prior_selection_id"]
        assert selection["state"] == "VALID"
        assert selection["requirement_set_hash"] == flow["choice"]["requirement_set_hash"]

        inherited = board["inherited_requirements"]
        assert inherited == before["inherited_requirements"]
        assert inherited["comparison_id"] == flow["comparison"]["id"]
        assert inherited["requirement_set_id"].startswith("public-rubric:bookshop:v")
        assert len(inherited["requirement_set_hash"]) == 64
        assert len(inherited["visible_check_set_hash"]) == 64

        draft = _call(client, "GET", f"/api/shifts/{successor['id']}/artifact")
        assert draft["files"] == config.comparison_candidate_files(flow["chosen_label"])
        assert board["draft_base_version_id"] == flow["selected_version_id"], (
            "the inherited draft must descend from the exact selection, not the newest save"
        )
        # The newest saved version in the engagement is the retained alternative,
        # so a latest-save substitution would visibly seed the draft from it; the
        # successor itself has saved nothing.
        assert board["latest_version"]["id"] == flow["retained_version_id"]
        assert board["latest_saved_version_id"] is None

        assert board["unresolved_limits"] == list(
            config.PIVOT_STARTER_CONTRACT_JSON["declared_limits"]
        )
        assert board["operating_status"] == "SELECTED"
        assert board["chain_status"] == "VALID"
        # Opening the successor appends nothing: the ledger after the open is
        # byte-identical to the ledger after the close.
        assert _ledger(client)["events"] == closed_ledger
        assert {incident["id"] for incident in board["incidents"]} == {
            incident["id"] for incident in before["incidents"]}
        assert {incident["state"] for incident in board["incidents"]} <= {"CLOSED_UNRESOLVED"}


def test_close_declares_limits_without_selecting_or_selling(tmp_path):
    """Obligation 26's close clause: closing never selects and writes no sale."""
    db_file = tmp_path / "close-no-select.db"
    with TestClient(create_app(str(db_file))) as client:
        flow = pivot_flow.qualified_shift(client)
        selections_before = _call(client, "GET", "/api/engagements/bookshop/selections")
        ledger_before = _ledger(client)["events"]

        closed = _call(client, "POST", f"/api/shifts/{flow['shift_id']}/close")
        assert closed["state"] == "closed"

        selections_after = _call(client, "GET", "/api/engagements/bookshop/selections")
        assert selections_after == selections_before, "closing the shift appended a selection"
        events = _ledger(client)["events"]
        assert events[: len(ledger_before)] == ledger_before
        appended = events[len(ledger_before):]
        assert {event["event_type"] for event in appended} == {"LIMIT_DECLARED"}
        assert len(appended) == len(config.PIVOT_STARTER_CONTRACT_JSON["declared_limits"])
        assert all(event["synthetic"] is True for event in appended)

        successor = _open(client)
        board = _board(client)
        assert board["latest_shift"]["id"] == successor
        assert board["operating_selection"]["id"] == flow["choice"]["id"], (
            "the next shift must inherit the prior selection; close made none"
        )
        assert board["unresolved_limits"] == list(
            config.PIVOT_STARTER_CONTRACT_JSON["declared_limits"]
        )


def test_freeze_ancestry_follows_the_draft_base_and_explicit_restore(tmp_path):
    """The Gate 3 S3.6 ancestry rule when A is restored after B was saved."""
    db_file = tmp_path / "ancestry.db"
    with TestClient(create_app(str(db_file))) as client:
        flow = pivot_flow.qualified_shift(client)
        successor = pivot_flow.open_successor(client)
        board = _board(client)
        assert board["latest_shift"]["id"] == successor["id"]
        assert board["draft_base_version_id"] == flow["selected_version_id"]
        # The pinned candidates were frozen under this contract; a frozen hash
        # covers the contract too, so the restore proof must use the same one.
        contract = config.PIVOT_STARTER_CONTRACT_JSON

        inherited = _freeze(client, successor["id"], contract)
        assert inherited["parent_id"] == flow["selected_version_id"], (
            "an inherited freeze must descend from the exact selection"
        )
        conn = db.connect(db_file)
        try:
            version = repo.get_version(conn, inherited["id"])
            assert version.restored_from_id == flow["selected_version_id"], (
                "the inherited freeze must record the exact selection as its restore source"
            )
        finally:
            conn.close()

        # Editing the same draft further chains from the version just frozen.
        _call(client, "PUT", f"/api/shifts/{successor['id']}/artifact", json={
            "files": config.comparison_candidate_files(flow["retained_label"])})
        saved = _freeze(client, successor["id"], contract)
        assert saved["parent_id"] == inherited["id"]
        conn = db.connect(db_file)
        try:
            assert repo.get_version(conn, saved["id"]).restored_from_id == inherited["id"]
        finally:
            conn.close()

        # Restoring A after B was saved and frozen: the next freeze descends from
        # A, not from the newest stored version (B's frozen copy).
        conn = db.connect(db_file)
        try:
            restored = orchestrator.restore_version_to_draft(
                conn, successor["id"], flow["selected_version_id"])
        finally:
            conn.close()
        assert restored["files"] == config.comparison_candidate_files(flow["chosen_label"])
        after_restore = _freeze(client, successor["id"], contract)
        assert after_restore["content_hash"] == flow["candidates"][flow["chosen_label"]][
            "content_hash"]
        assert after_restore["parent_id"] == flow["selected_version_id"], (
            "restoring A after saving B must record A as the parent, not the newest version"
        )
        conn = db.connect(db_file)
        try:
            version = repo.get_version(conn, after_restore["id"])
            assert version.restored_from_id == flow["selected_version_id"]
            assert repo.get_latest_version(conn, successor["id"]).id == after_restore["id"]
        finally:
            conn.close()

        # An unknown version is refused before the draft is touched.
        conn = db.connect(db_file)
        try:
            with pytest.raises(orchestrator.LifecycleError):
                orchestrator.restore_version_to_draft(conn, successor["id"], "ver-missing")
        finally:
            conn.close()

        # A closed shift's draft is history: a restore is refused, and the
        # refused call leaves the stored base exactly where it was.
        _call(client, "POST", f"/api/shifts/{successor['id']}/close")
        conn = db.connect(db_file)
        try:
            base_before = repo.get_draft_base_version_id(conn, successor["id"])
            assert base_before == after_restore["id"]
            with pytest.raises(orchestrator.LifecycleError, match="closed"):
                orchestrator.restore_version_to_draft(
                    conn, successor["id"], flow["retained_version_id"])
            assert repo.get_draft_base_version_id(conn, successor["id"]) == base_before, (
                "a refused restore moved the draft base"
            )
        finally:
            conn.close()
