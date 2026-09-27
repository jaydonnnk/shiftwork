"""S11: the investigation lifecycle, the prediction gate and the two denials.

Gate 3 obligations 5 and 6 plus the Slice 11 clauses that deny a null-investigation
bootstrap and any diagnostic help before the learner has committed a diagnosis.
Every test drives the real orchestrator against a real database through the shared
HTTP session fixture, so the guards are exercised on the shipped path rather than
against a stub.
"""

import json

import pytest
from conftest import BookshopShift
from pydantic import ValidationError

from shiftwork import orchestrator
from shiftwork.domain.errors import (
    AssistGatewayUnavailable,
    BootstrapBlocked,
    InvestigationIncomplete,
)
from shiftwork.domain.models import AssistRole, Investigation, InvestigationRequest
from shiftwork.store import db, repo

CAUSE = "the keyword router treats the pound symbol as a price question"
FALSIFIER = "a request with no currency symbol still omits the collection task"
PUBLIC_TEST = "assert a result exists for every required task in the frozen request"


@pytest.fixture()
def run_id(session):
    """One real executed run in the open shift, so a source ordinal exists."""
    return session.attempt()["id"]


def _request(run_id, ordinal=1, **overrides):
    fields = {
        "source_run_id": run_id,
        "source_request_ordinal": ordinal,
        "cause": CAUSE,
        "falsifier": FALSIFIER,
        "public_test": PUBLIC_TEST,
        "revision_of_id": None,
        "client_request_id": f"client-{run_id}-{ordinal}",
    }
    fields.update(overrides)
    return InvestigationRequest(**fields)


def _append(session, request):
    conn = db.connect(session.db_file)
    try:
        return orchestrator.append_investigation(conn, session.shift_id, request)
    finally:
        conn.close()


def test_orientation_is_available_before_any_investigation(session):
    """Gate 3 S1: orientation is deterministic copy, allowed before the prediction."""
    view = orchestrator.orientation(session.shift_id)
    assert view["source"] == "deterministic_copy"
    assert view["steps"] == list(orchestrator.ORIENTATION_COPY)
    assert len(view["steps"]) >= 3

    conn = db.connect(session.db_file)
    try:
        assert repo.count_investigations(conn) == 0
        full = orchestrator.investigation_view(conn, session.shift_id)
    finally:
        conn.close()
    assert full["orientation"]["steps"] == list(orchestrator.ORIENTATION_COPY)
    assert full["investigations"] == []
    assert full["latest_investigation_id"] is None


def test_appending_persists_the_learners_own_entry(session, run_id):
    appended = _append(session, _request(run_id))
    assert isinstance(appended, Investigation)
    assert appended.authored_by == "learner"
    assert (appended.cause, appended.falsifier, appended.public_test) == (
        CAUSE,
        FALSIFIER,
        PUBLIC_TEST,
    )
    assert appended.source_run_id == run_id
    assert appended.revision_of_id is None

    conn = db.connect(session.db_file)
    try:
        stored = repo.get_investigation(conn, appended.id)
    finally:
        conn.close()
    assert stored == appended


def test_investigation_revision_preserves_original(session, run_id):
    """Obligation 6: both rows exist and the linkage is real."""
    parent = _append(session, _request(run_id))
    revision = _append(
        session,
        _request(
            run_id,
            cause="the router never inspects the collection records at all",
            revision_of_id=parent.id,
            client_request_id="client-revision",
        ),
    )

    assert revision.id != parent.id
    assert revision.revision_of_id == parent.id

    conn = db.connect(session.db_file)
    try:
        entries = repo.list_investigations_for_shift(conn, session.shift_id)
        stored_parent = repo.get_investigation(conn, parent.id)
    finally:
        conn.close()

    assert [entry.id for entry in entries] == [parent.id, revision.id]
    assert stored_parent.cause == CAUSE, "the revision overwrote its parent"
    assert stored_parent.revision_of_id is None
    assert revision.cause != stored_parent.cause


def test_a_revision_cannot_reference_another_shift(session, run_id):
    """The engagement opens one shift at a time, so the second shift is reached by
    closing the first.

    The second shift gets its own run first. Without that, the run-ownership guard
    fires before the revision guard and the two catch the same fault, proving
    neither.
    """
    parent = _append(session, _request(run_id))
    closed = session.client.post(f"/api/shifts/{session.shift_id}/close")
    assert closed.status_code == 200, closed.text
    opened = session.client.post("/api/engagements/bookshop/shifts")
    assert opened.status_code == 201, opened.text

    second = BookshopShift(session.client, session.db_file, session.monkeypatch)
    second.shift_id = opened.json()["id"]
    assert second.shift_id != session.shift_id
    second.freeze()
    second_run_id = second.attempt()["id"]

    conn = db.connect(session.db_file)
    try:
        with pytest.raises(orchestrator.LifecycleError) as excinfo:
            orchestrator.append_investigation(
                conn,
                second.shift_id,
                _request(
                    second_run_id,
                    revision_of_id=parent.id,
                    client_request_id="client-cross",
                ),
            )
        assert excinfo.value.kind == "conflict"
        assert "same shift" in excinfo.value.message
        assert repo.count_investigations(conn) == 1, "the refused revision must not be stored"
        assert repo.get_investigation(conn, parent.id).cause == CAUSE

        own = orchestrator.append_investigation(
            conn,
            second.shift_id,
            _request(second_run_id, client_request_id="client-own"),
        )
        assert own.revision_of_id is None
    finally:
        conn.close()


def test_the_storage_layer_also_refuses_a_cross_shift_revision(session, run_id):
    """The trigger is the backstop if an orchestrator check is ever removed."""
    parent = _append(session, _request(run_id))
    conn = db.connect(session.db_file)
    try:
        with pytest.raises(Exception) as excinfo:
            conn.execute(
                "INSERT INTO investigations (id, shift_id, source_run_id,"
                " source_request_ordinal, cause, falsifier, public_test,"
                " revision_of_id, created_at)"
                " VALUES ('inv-raw-cross', 'bookshop-shift-99', ?, 1, ?, ?, ?, ?,"
                " '2026-09-25T09:00:00+00:00')",
                (run_id, CAUSE, FALSIFIER, PUBLIC_TEST, parent.id),
            )
        assert "same shift" in str(excinfo.value)
    finally:
        conn.close()


@pytest.mark.parametrize("field", ["cause", "falsifier", "public_test"])
@pytest.mark.parametrize("blank", ["", "   "])
def test_appending_requires_cause_falsifier_and_public_test(session, run_id, field, blank):
    """Obligation 5's entry half: each field fails independently.

    The gate lives on the append, not on the assist call. A stored investigation
    can never carry a blank field, because this path refuses one and the table is
    append-only behind non-empty CHECK constraints.
    """
    conn = db.connect(session.db_file)
    try:
        with pytest.raises(InvestigationIncomplete) as excinfo:
            orchestrator.append_investigation(
                conn,
                session.shift_id,
                _request(run_id, client_request_id=f"client-{field}", **{field: blank}),
            )
        assert field in excinfo.value.message
        assert repo.count_investigations(conn) == 0, "a rejected entry must not be stored"
    finally:
        conn.close()


def test_the_storage_layer_also_refuses_a_blank_field(session, run_id):
    """The append-only table's own CHECK constraint, independent of the orchestrator."""
    conn = db.connect(session.db_file)
    try:
        with pytest.raises(Exception) as excinfo:
            conn.execute(
                "INSERT INTO investigations (id, shift_id, source_run_id,"
                " source_request_ordinal, cause, falsifier, public_test, created_at)"
                " VALUES ('inv-raw', ?, ?, 1, '', ?, ?, '2026-09-25T09:00:00+00:00')",
                (session.shift_id, run_id, FALSIFIER, PUBLIC_TEST),
            )
        assert "CHECK constraint failed" in str(excinfo.value)
    finally:
        conn.close()


@pytest.mark.parametrize("role", list(AssistRole))
def test_diagnostic_help_needs_an_investigation_and_is_denied_anyway(session, run_id, role):
    """Obligation 5's help half: the prediction gate fires before the gateway denial."""
    conn = db.connect(session.db_file)
    try:
        with pytest.raises(InvestigationIncomplete) as gated:
            orchestrator.request_assist(conn, session.shift_id, None, role)
        assert gated.value.message == orchestrator.ASSIST_GATE_REASON

        appended = _append(session, _request(run_id, client_request_id=f"client-{role.value}"))
        with pytest.raises(AssistGatewayUnavailable) as denied:
            orchestrator.request_assist(conn, session.shift_id, appended.id, role)
        assert role.value in denied.value.message
        assert denied.value.message != orchestrator.ASSIST_GATE_REASON
    finally:
        conn.close()


def test_help_is_denied_for_a_different_shifts_investigation(session, run_id):
    appended = _append(session, _request(run_id))
    conn = db.connect(session.db_file)
    try:
        with pytest.raises(orchestrator.LifecycleError) as excinfo:
            orchestrator.request_assist(conn, "bookshop-shift-99", appended.id, AssistRole.HINT)
    finally:
        conn.close()
    assert excinfo.value.kind == "not_found"


def test_help_with_another_open_shifts_investigation_is_refused_before_the_gateway(session, run_id):
    """The ownership check runs before the absent-gateway denial: an open shift
    asking for help with another open shift's investigation is a conflict, not a
    gateway denial, and never an allowed request."""
    appended = _append(session, _request(run_id))
    closed = session.client.post(f"/api/shifts/{session.shift_id}/close")
    assert closed.status_code == 200, closed.text
    opened = session.client.post("/api/engagements/bookshop/shifts")
    assert opened.status_code == 201, opened.text
    conn = db.connect(session.db_file)
    try:
        outcome = "allowed"
        try:
            orchestrator.request_assist(conn, opened.json()["id"], appended.id, AssistRole.HINT)
        except AssistGatewayUnavailable:
            outcome = "gateway-denied"
        except orchestrator.LifecycleError as error:
            outcome = f"lifecycle:{error.kind}"
    finally:
        conn.close()
    assert outcome == "lifecycle:conflict", (
        "help with another open shift's investigation must be refused as a conflict "
        "before the absent-gateway denial"
    )


def test_authored_by_is_not_caller_controlled(session, run_id):
    """No caller field can attribute an investigation to anyone but the learner."""
    assert "authored_by" not in InvestigationRequest.model_fields
    assert InvestigationRequest.model_config.get("extra") == "forbid"
    with pytest.raises(ValidationError):
        InvestigationRequest(
            source_run_id=run_id,
            source_request_ordinal=1,
            cause=CAUSE,
            falsifier=FALSIFIER,
            public_test=PUBLIC_TEST,
            client_request_id="client-spoof",
            authored_by="assist",
        )
    assert Investigation.model_fields["authored_by"].default == "learner"


def test_an_investigation_cannot_cite_a_run_it_does_not_own(session, run_id):
    conn = db.connect(session.db_file)
    try:
        with pytest.raises(orchestrator.LifecycleError) as unknown:
            orchestrator.append_investigation(
                conn, session.shift_id, _request("run-9999", client_request_id="client-unknown")
            )
        assert unknown.value.kind == "not_found"

        with pytest.raises(orchestrator.LifecycleError) as absent:
            orchestrator.append_investigation(
                conn, session.shift_id, _request(run_id, ordinal=99, client_request_id="client-ordinal")
            )
        assert absent.value.kind == "conflict"
        assert repo.count_investigations(conn) == 0
    finally:
        conn.close()


def test_bootstrap_diagnostic_is_denied_without_a_safe_executor(session):
    """S11 constructs the denial; S13 supplies the executor that lifts it."""
    conn = db.connect(session.db_file)
    try:
        with pytest.raises(BootstrapBlocked):
            orchestrator.reserve_bootstrap_diagnostic(conn, session.shift_id)
        assert repo.count_investigations(conn) == 0
    finally:
        conn.close()


def test_investigating_a_closed_shift_is_refused(session, run_id):
    closed = session.client.post(f"/api/shifts/{session.shift_id}/close")
    assert closed.status_code == 200, closed.text
    conn = db.connect(session.db_file)
    try:
        with pytest.raises(orchestrator.LifecycleError) as excinfo:
            orchestrator.append_investigation(
                conn, session.shift_id, _request(run_id, client_request_id="client-closed")
            )
        assert excinfo.value.kind == "conflict"
        assert repo.count_investigations(conn) == 0
    finally:
        conn.close()


def test_the_public_view_leaks_no_path_sealed_identity_or_assist_text(session, run_id, tmp_path):
    appended = _append(session, _request(run_id))
    conn = db.connect(session.db_file)
    try:
        view = orchestrator.investigation_view(conn, session.shift_id)
    finally:
        conn.close()

    assert view["latest_investigation_id"] == appended.id
    assert view["assist_available"] is False
    assert view["bootstrap_available"] is False

    serialized = json.dumps(view, default=str)
    for needle in (
        str(tmp_path),
        str(session.db_file),
        "sealed",
        "expected_ref",
        "check_id",
        "C:\\",
        ".venv",
        "protected_reservation",
    ):
        assert needle not in serialized, f"the public view leaked {needle!r}"
    assert appended.cause in serialized, "the learner's own entry must be visible to them"


def test_appending_twice_creates_two_rows_and_never_updates_one(session, run_id):
    first = _append(session, _request(run_id, client_request_id="client-a"))
    second = _append(session, _request(run_id, client_request_id="client-b"))
    assert first.id != second.id

    conn = db.connect(session.db_file)
    try:
        assert repo.count_investigations(conn) == 2
        assert repo.latest_investigation_for_shift(conn, session.shift_id).id == second.id
        assert repo.get_investigation(conn, first.id).cause == CAUSE
    finally:
        conn.close()


class _CrashingGateway:
    """A provider call that dies with the process: a BaseException skips finish."""

    model_id = "crash-double"

    def generate(self, *, model_id, role, prompt):
        raise KeyboardInterrupt("simulated interruption between reserve and finish")


def test_a_stranded_assist_is_failed_at_the_next_startup(session, run_id, restart):
    """S14 review repair: a crash between reserve and finish must not leave a
    PENDING event whose panel copy promises a refresh can never deliver.

    The next startup fails it with the controller-side ASSIST_INTERRUPTED code:
    the call keeps its budget slot, refuses a decision, and a second restart
    leaves the row untouched (idempotent)."""
    appended = _append(session, _request(run_id))
    conn = db.connect(session.db_file)
    try:
        with pytest.raises(KeyboardInterrupt):
            orchestrator.request_assist(
                conn, session.shift_id, appended.id, AssistRole.HINT,
                client_request_id="crash-1", gateway=_CrashingGateway(),
            )
        assert [event.state for event in repo.list_assist_for_shift(conn, session.shift_id)] == ["PENDING"], (
            "the crash must leave the reserved event unresolved"
        )
    finally:
        conn.close()

    restarted = restart(session.db_file)
    view = restarted.client.get(f"/api/shifts/{restarted.shift_id}/investigations").json()
    (event,) = view["assist_events"]
    assert (event["state"], event["failure_code"], event["response_text"]) == (
        "FAILED", "ASSIST_INTERRUPTED", "",
    )
    assert (view["assist_used"], view["assist_limit"]) == (1, 3), (
        "an interrupted call must keep its budget slot"
    )
    refused = restarted.client.post(f"/api/assist-events/{event['id']}/decision", json={"accepted": True})
    assert refused.status_code == 409, refused.text

    again = restart(session.db_file)
    second_view = again.client.get(f"/api/shifts/{again.shift_id}/investigations").json()
    assert second_view["assist_events"] == view["assist_events"], "reconciliation must be idempotent"
