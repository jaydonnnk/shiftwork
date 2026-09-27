"""S11: the public diagnostic experiment and its hard boundaries.

Test 21 of the Gate 3 plan: a diagnostic may run a pinned trusted fixture but can
never reserve a protected case, make a version eligible, write business state,
open assist access or spend the operation budget. Every test drives the real HTTP
surface against a real database, and every assertion reads the same stored rows a
public projection reads.
"""

import base64
import json

import pytest
from conftest import BookshopShift

from shiftwork import config, orchestrator
from shiftwork.domain import task_contract
from shiftwork.domain.errors import BootstrapBlocked
from shiftwork.domain.models import ExperimentKind
from shiftwork.evaluator import evaluator
from shiftwork.executor import base as executor_base
from shiftwork.store import db, repo

CAUSE = "the router answers only the optional price task and never reads collection records"
FALSIFIER = "a request with no currency symbol still omits the collection task"
PUBLIC_TEST = "assert a result exists for every required task in the frozen request"


def _append_investigation(session, run_id: str, client_request_id: str = "inv-1"):
    response = session.client.post(
        f"/api/shifts/{session.shift_id}/investigations",
        json={
            "source_run_id": run_id,
            "source_request_ordinal": 1,
            "cause": CAUSE,
            "falsifier": FALSIFIER,
            "public_test": PUBLIC_TEST,
            "revision_of_id": None,
            "client_request_id": client_request_id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _freeze_starter(session) -> dict:
    """Freeze the shipped reviewed starter as this shift's own candidate version."""
    response = session.client.post(
        f"/api/shifts/{session.shift_id}/artifact/versions",
        json={"contract": config.PIVOT_STARTER_CONTRACT_JSON},
    )
    assert response.status_code == 201, response.text
    version = response.json()
    assert version["content_hash"] == config.TRUSTED_LOCAL_FIXTURES["pivot_starter"][0], (
        "the draft no longer matches the pinned reviewed starter"
    )
    return version


def _create_experiment(session, version_id: str, investigation_id: str | None, key: str = "exp-1"):
    return session.client.post(
        f"/api/shifts/{session.shift_id}/experiments",
        json={
            "kind": "DIAGNOSTIC",
            "investigation_id": investigation_id,
            "candidate_a_version_id": version_id,
            "client_request_id": key,
        },
    )


@pytest.fixture()
def diagnostic(session):
    """One executed diagnostic over the pinned starter, plus its ids."""
    version = _freeze_starter(session)
    run_id = session.attempt()["id"]
    investigation = _append_investigation(session, run_id)
    created = _create_experiment(session, version["id"], investigation["id"])
    assert created.status_code == 202, created.text
    experiment_id = created.json()["id"]
    response = session.client.get(f"/api/experiments/{experiment_id}")
    assert response.status_code == 200, response.text
    return {
        "experiment_id": experiment_id,
        "view": response.json(),
        "version": version,
        "investigation": investigation,
        "operation_run_id": run_id,
    }


def test_the_pinned_starter_fails_the_request_where_it_actually_fails(session, diagnostic):
    """Obligations 9 to 15: the starter's true price does not carry the request."""
    trial = diagnostic["view"]["trials"][0]
    assert trial["state"] == "COMPLETE"
    assert trial["evidence_mode"] == "TRUSTED_LOCAL"
    outcomes = {entry["task_id"]: entry for entry in trial["task_assessments"]}
    assert outcomes["price"]["outcome"] == "USEFUL_COMPLETION"
    assert outcomes["price"]["mandatory_pass"] is True
    for task_id in ("collection", "alternative"):
        assert outcomes[task_id]["outcome"] == "MISSING_OUTPUT", outcomes[task_id]
        assert outcomes[task_id]["mandatory_pass"] is False
        assert "REQUIRED_TASK_MISSING" in outcomes[task_id]["reason_codes"]

    conn = db.connect(session.db_file)
    try:
        assessment = repo.get_run_assessment(conn, trial["run_id"])
    finally:
        conn.close()
    assert (assessment.complete_request_count, assessment.expected_request_count) == (0, 1)
    assert assessment.mandatory_pass is False
    assert assessment.rule_version == evaluator.RULE_VERSION
    assert assessment.context_hash == diagnostic["view"]["context_hash"]


def test_a_supported_stock_only_answer_cannot_complete_the_request():
    """The old stock-only arc and a stubbed success fail the requested-task assertion.

    The stub is a fully valid envelope: the frozen request id, one completed
    optional price task, no fallback, every claim backed by a current matching
    public record. It still fails, because two required tasks went unanswered.
    """
    mission = task_contract.load_mission(config.PIVOT_MISSION)
    snapshot = task_contract.load_public_state(config.PIVOT_PUBLIC_STATE)
    spec = mission.request_specs[0]
    price_record = next(
        record
        for record in snapshot.records
        if record.entity_ref == "book:salt-roads:paperback" and record.kind == "price"
    )
    body = json.dumps(
        {
            "request_id": spec.id,
            "task_results": [
                {
                    "task_id": "price",
                    "status": "COMPLETED",
                    "entity_ref": "book:salt-roads:paperback",
                    "claims": [
                        {
                            "kind": "price",
                            "value": price_record.value,
                            "entity_ref": "book:salt-roads:paperback",
                            "evidence_refs": [price_record.record_id],
                        }
                    ],
                    "explanation_code": None,
                    "commitment_ref": None,
                }
            ],
            "evidence_refs": [price_record.record_id],
            "uncertainty_codes": [],
        }
    ).encode("utf-8")
    response = task_contract.validate_response_envelope(spec, body)
    assessments = evaluator.assess_request(
        spec=spec, request_ordinal=1, mission=mission, snapshot=snapshot, response=response
    )
    assert evaluator.request_usefully_completed(spec, assessments) is False
    assert [entry.outcome.value for entry in assessments] == [
        "USEFUL_COMPLETION",
        "MISSING_OUTPUT",
        "MISSING_OUTPUT",
    ]


def test_the_frozen_context_pins_the_reviewed_bytes_and_reserves_nothing(session, diagnostic):
    conn = db.connect(session.db_file)
    try:
        experiment = repo.get_experiment(conn, diagnostic["experiment_id"])
        context = repo.get_execution_context(conn, experiment.context_id)
    finally:
        conn.close()
    assert context.protected_reservation_id is None
    assert context.executor_class.value == "TRUSTED_LOCAL"
    assert len(context.workloads) == 1
    workload = context.workloads[0]
    assert workload.request_count == 1
    assert base64.b64decode(workload.request_batch_bytes_base64) == (
        config.PIVOT_INCIDENT_REQUESTS.read_bytes()
    )
    assert context.mission_bytes_base64 == base64.b64encode(
        config.PIVOT_MISSION.read_bytes()
    ).decode("ascii")
    assert context.public_data_bytes_base64 == base64.b64encode(
        config.PIVOT_PUBLIC_STATE.read_bytes()
    ).decode("ascii")
    assert context.content_hash
    assert experiment.candidates[0].artifact_content_hash == (
        config.TRUSTED_LOCAL_FIXTURES["pivot_starter"][0]
    )


def test_the_diagnostic_cannot_be_eligible_or_write_business_state(session, diagnostic):
    """Test 21: no eligibility, no protected material, no customer consequence."""
    conn = db.connect(session.db_file)
    try:
        before_events = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
        before_incidents = repo.list_incidents(conn, config.BOOKSHOP_SLUG)
        before_selections = repo.count_operating_selections(conn)
        before_draws = conn.execute("SELECT COUNT(*) AS n FROM rotation_draws").fetchone()["n"]
    finally:
        conn.close()
    view = diagnostic["view"]
    assert view["eligible"] is False
    assert "never qualify" in view["eligibility_reason"]
    conn = db.connect(session.db_file)
    try:
        assert repo.list_ledger_events(conn, config.BOOKSHOP_SLUG) == before_events
        assert repo.list_incidents(conn, config.BOOKSHOP_SLUG) == before_incidents
        assert repo.count_operating_selections(conn) == before_selections
        assert (
            conn.execute("SELECT COUNT(*) AS n FROM rotation_draws").fetchone()["n"]
            == before_draws
        )
    finally:
        conn.close()


def test_the_diagnostic_does_not_spend_the_operation_budget(session, diagnostic):
    conn = db.connect(session.db_file)
    try:
        assert repo.count_runs(conn, session.shift_id) == 2, "the operation run and the diagnostic"
        assert repo.count_operation_runs(conn, session.shift_id) == 1
        experiment_run = repo.get_run(conn, diagnostic["view"]["trials"][0]["run_id"])
        assert experiment_run.purpose.value == "EXPERIMENT"
        assert experiment_run.context_id is not None
        assert experiment_run.selection_id is None
    finally:
        conn.close()
    board = session.board()
    assert board["attempts_used"] == 1
    assert board["attempt_limit"] - board["attempts_used"] == board["attempts_remaining"]

    second = session.attempt()
    assert second["state"] == "FINALIZED"
    assert second["attempt_number"] == 3, "numbering counts every run, so numbers stay unique"


def test_only_the_pinned_reviewed_starter_is_executable(session):
    """An edited artifact is not a reviewed fixture, so it is refused before reserving."""
    session.edit("\n# learner edit\n")
    edited = session.freeze()
    investigation = _append_investigation(session, session.attempt()["id"])
    refused = _create_experiment(session, edited["id"], investigation["id"])
    assert refused.status_code == 409, refused.text
    assert "pinned reviewed starter" in refused.json()["detail"]
    conn = db.connect(session.db_file)
    try:
        assert repo.list_experiments_for_shift(conn, session.shift_id) == []
        assert repo.count_execution_contexts(conn) == 0, "a refused reservation froze a context"
    finally:
        conn.close()


def test_the_controller_does_not_choose_a_version_for_the_learner(session):
    """Faulting auto-choice: the cited candidate is reserved, never the newest save."""
    starter = _freeze_starter(session)
    session.edit("\n# learner edit\n")
    newer = session.freeze()
    assert newer["id"] != starter["id"]
    investigation = _append_investigation(session, session.attempt()["id"])
    created = _create_experiment(session, starter["id"], investigation["id"])
    assert created.status_code == 202, created.text
    assert created.json()["candidates"] == [
        {
            "label": "A",
            "artifact_version_id": starter["id"],
            "artifact_content_hash": starter["content_hash"],
        }
    ]
    assert created.json()["trials"][0]["candidate_label"] == "A"


def test_the_diagnostic_budget_is_two_per_shift(session):
    version = _freeze_starter(session)
    investigation = _append_investigation(session, session.attempt()["id"])
    first = _create_experiment(session, version["id"], investigation["id"], key="exp-a")
    assert first.status_code == 202, first.text
    second = _create_experiment(session, version["id"], investigation["id"], key="exp-b")
    assert second.status_code == 202, second.text
    third = _create_experiment(session, version["id"], investigation["id"], key="exp-c")
    assert third.status_code == 409, third.text
    assert "budget exhausted" in third.json()["detail"]
    conn = db.connect(session.db_file)
    try:
        assert (
            repo.count_experiments_for_shift(conn, session.shift_id, ExperimentKind.DIAGNOSTIC)
            == 2
        )
    finally:
        conn.close()


def test_a_failed_diagnostic_still_consumes_its_slot(session, monkeypatch):
    """The reservation is the durable budget: an evidence failure is not refunded."""

    async def failing_execute(self, request):
        return executor_base.RunResult(
            captures=(),
            executor_ref=None,
            failure=executor_base.ExecutorFailure.PROVISION_FAILED,
            wall_ms=1,
        )

    monkeypatch.setattr(orchestrator.LocalProcessAdapter, "execute", failing_execute)
    version = _freeze_starter(session)
    investigation = _append_investigation(session, session.attempt()["id"])
    first = _create_experiment(session, version["id"], investigation["id"], key="exp-fail-a")
    assert first.status_code == 202, first.text
    failed = session.client.get(f"/api/experiments/{first.json()['id']}").json()
    assert failed["trials"][0]["state"] == "FAILED"
    assert failed["state"] == "FAILED"
    second = _create_experiment(session, version["id"], investigation["id"], key="exp-fail-b")
    assert second.status_code == 202, second.text
    third = _create_experiment(session, version["id"], investigation["id"], key="exp-fail-c")
    assert third.status_code == 409, third.text
    conn = db.connect(session.db_file)
    try:
        assert (
            repo.count_experiments_for_shift(conn, session.shift_id, ExperimentKind.DIAGNOSTIC)
            == 2
        ), "a failed diagnostic must stay on the ledger of spent slots"
    finally:
        conn.close()


def test_reusing_a_client_request_id_returns_the_original_reservation(session):
    version = _freeze_starter(session)
    investigation = _append_investigation(session, session.attempt()["id"])
    first = _create_experiment(session, version["id"], investigation["id"], key="same-key")
    assert first.status_code == 202, first.text
    replay = _create_experiment(session, version["id"], investigation["id"], key="same-key")
    assert replay.status_code in (200, 202), replay.text
    assert replay.json()["id"] == first.json()["id"]
    conn = db.connect(session.db_file)
    try:
        assert repo.list_experiments_for_shift(conn, session.shift_id) == [
            repo.get_experiment(conn, first.json()["id"])
        ]
    finally:
        conn.close()


def test_a_null_investigation_bootstrap_is_denied_and_reserves_nothing(session):
    """An ordinary shift cannot use the legacy no-source bootstrap exception."""
    version = _freeze_starter(session)
    refused = _create_experiment(session, version["id"], None, key="exp-bootstrap")
    assert refused.status_code == 409, refused.text
    assert "only for a legacy first-choice shift" in refused.json()["detail"]
    conn = db.connect(session.db_file)
    try:
        assert repo.list_experiments_for_shift(conn, session.shift_id) == []
        assert repo.count_execution_contexts(conn) == 0
        with pytest.raises(BootstrapBlocked):
            orchestrator.reserve_bootstrap_diagnostic(conn, session.shift_id)
    finally:
        conn.close()


def test_an_investigation_from_another_shift_cannot_authorise_a_diagnostic(session):
    version = _freeze_starter(session)
    investigation = _append_investigation(session, session.attempt()["id"])
    closed = session.client.post(f"/api/shifts/{session.shift_id}/close")
    assert closed.status_code == 200, closed.text
    opened = session.client.post("/api/engagements/bookshop/shifts")
    assert opened.status_code == 201, opened.text
    second = BookshopShift(session.client, session.db_file, session.monkeypatch)
    second.shift_id = opened.json()["id"]
    second.freeze()
    refused = _create_experiment(second, version["id"], investigation["id"])
    assert refused.status_code == 409, refused.text
    assert "owned by this shift" in refused.json()["detail"]


def test_the_run_assessment_is_immutable_and_written_once(session, diagnostic):
    run_id = diagnostic["view"]["trials"][0]["run_id"]
    conn = db.connect(session.db_file)
    try:
        stored = repo.get_run_assessment(conn, run_id)
        with pytest.raises(Exception) as excinfo:
            conn.execute(
                "UPDATE run_assessments SET mandatory_pass = 1 WHERE run_id = ?", (run_id,)
            )
        assert "immutable" in str(excinfo.value)
        assert repo.get_run_assessment(conn, run_id) == stored
        assert repo.count_task_assessments(conn) == 3
    finally:
        conn.close()


def test_the_public_projections_leak_no_path_sealed_identity_or_raw_ref(
    tmp_path, session, diagnostic
):
    station = session.client.get(f"/api/shifts/{session.shift_id}/investigations").json()
    payload = {"station": station, "experiment": diagnostic["view"]}
    serialized = json.dumps(payload, default=str)

    needles = {
        "host_path": str(tmp_path),
        "db_path": str(session.db_file),
        "sealed_word": "sealed",
        "expected_ref": "expected_ref",
        "check_id": "check_id",
        "windows_root": "C:\\",
        "venv": ".venv",
        "protected": "protected_reservation",
        "raw_ref": "raw_payload_ref",
        "context_path": "frozen-context:",
    }
    # Capability self-test: each needle must be detectable once injected into this
    # exact projection shape. A JSON dump backslash-escapes Windows paths, so a
    # path needle has to match both its raw and its escaped form, and the absence
    # check below has to test both forms too or a real leak would pass.
    def escaped(value: str) -> str:
        return json.dumps(value)[1:-1]

    for name, needle in needles.items():
        injected = json.loads(json.dumps(payload, default=str))
        injected["station"]["probe"] = {"value": needle}
        injected["experiment"]["trials"][0]["probe"] = {"value": needle}
        dumped = json.dumps(injected, default=str)
        assert needle in dumped or escaped(needle) in dumped, f"needle {name!r} cannot match"
    for name, needle in needles.items():
        assert needle not in serialized, f"the public projection leaked {name}"
        assert escaped(needle) not in serialized, f"the public projection leaked {name} (escaped)"

    assert CAUSE in serialized, "the learner's own diagnosis must be visible to them"
    assert "Salt Roads" in serialized, "the exact customer-facing answer must be visible"


def test_a_fixture_edit_after_reservation_cannot_rewrite_the_assessment(
    session, tmp_path, monkeypatch
):
    """The run assesses the bytes it froze, not the fixture as it reads later."""
    version = _freeze_starter(session)
    investigation = _append_investigation(session, session.attempt()["id"])
    conn = db.connect(session.db_file)
    try:
        experiment = orchestrator.create_diagnostic_experiment(
            conn,
            session.shift_id,
            candidate_version_id=version["id"],
            investigation_id=investigation["id"],
            client_request_id="exp-frozen",
        )
        reserved = orchestrator.experiment_run(conn, experiment.id)
    finally:
        conn.close()

    tampered = json.loads(config.PIVOT_MISSION.read_text(encoding="utf-8"))
    tampered["request_specs"][0]["tasks"] = [
        task for task in tampered["request_specs"][0]["tasks"] if task["id"] != "alternative"
    ]
    edited = tmp_path / config.PIVOT_MISSION.name
    edited.write_text(json.dumps(tampered), encoding="utf-8")
    monkeypatch.setattr(config, "PIVOT_MISSION", edited)

    orchestrator.execute_experiment_task(str(session.db_file), reserved.id)
    conn = db.connect(session.db_file)
    try:
        view = orchestrator.experiment_view(conn, experiment.id)
    finally:
        conn.close()
    assert {entry["task_id"] for entry in view["trials"][0]["task_assessments"]} == {
        "price",
        "collection",
        "alternative",
    }, "the stored assessment followed the edited fixture instead of the frozen bytes"
