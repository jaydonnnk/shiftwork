"""S11: the public diagnostic experiment and its hard boundaries.

Test 21 of the Gate 3 plan: a diagnostic may run a pinned trusted fixture but can
never reserve a protected case, make a version eligible, write business state,
open assist access or spend the operation budget. Every test drives the real HTTP
surface against a real database, and every assertion reads the same stored rows a
public projection reads.
"""

import base64
import hashlib
import json
import copy
import runpy
import sqlite3
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest
from conftest import BookshopShift

from shiftwork import config, orchestrator
from shiftwork.domain import canonical, task_contract
from shiftwork.domain.errors import BootstrapBlocked
from shiftwork.domain.models import (
    ExecutionObservation, ExecutorFailure, ExperimentKind, ObservationKind,
    RunOutput, RunState,
)
from shiftwork.evaluator import evaluator
from shiftwork.executor import base as executor_base
from shiftwork.store import db, repo
from shiftwork.sealed import store as sealed_store
from shiftwork.sealed import rotation
from shiftwork.domain.errors import RotationMisconfigured

_REVIEW_GATE = orchestrator._require_reviewed_comparison_material
_REVIEWED_FAMILY = sealed_store.load_reviewed_comparison_family


@pytest.fixture(autouse=True)
def _synthetic_comparison_review(monkeypatch):
    """Only this offline test module can exercise the draft comparison mechanics."""
    monkeypatch.setattr(orchestrator, "_require_reviewed_comparison_material", lambda *_: None)
    monkeypatch.setattr(sealed_store, "load_reviewed_comparison_family", sealed_store.load_family)

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


# --- S15: the qualifying comparison ----------------------------------------

TREATMENT = (
    "candidate A favors the cheapest qualifying alternative; candidate B favors "
    "the greatest current shelf stock, breaking ties by lower price"
)
WORKLOAD_FILES = tuple(
    f"bookshop_compare_pair_{ordinal:02d}{suffix}"
    for ordinal in (1, 2, 3)
    for suffix in (".jsonl", "_specs.json")
)


def _freeze_candidate(session, label: str) -> dict:
    """Freeze one reviewed comparison candidate as this shift's own version."""
    saved = session.client.put(
        f"/api/shifts/{session.shift_id}/artifact",
        json={"files": config.comparison_candidate_files(label)},
    )
    assert saved.status_code == 200, saved.text
    frozen = session.client.post(
        f"/api/shifts/{session.shift_id}/artifact/versions",
        json={"contract": config.PIVOT_STARTER_CONTRACT_JSON},
    )
    assert frozen.status_code == 201, frozen.text
    version = frozen.json()
    assert version["content_hash"] == config.TRUSTED_LOCAL_FIXTURES[f"compare_candidate_{label.lower()}"][0], (
        "the frozen candidate no longer matches its reviewed pin"
    )
    return version


def _comparison_session(session):
    """Two frozen reviewed candidates plus one owned investigation entry."""
    candidate_a = _freeze_candidate(session, "A")
    candidate_b = _freeze_candidate(session, "B")
    investigation = _append_investigation(session, session.attempt()["id"])
    return candidate_a, candidate_b, investigation


def _create_comparison(
    session, candidate_a, candidate_b, investigation, key: str = "cmp-1", treatment: str = TREATMENT
):
    return session.client.post(
        f"/api/shifts/{session.shift_id}/experiments",
        json={
            "kind": "QUALIFYING_COMPARISON",
            "investigation_id": investigation["id"],
            "candidate_a_version_id": candidate_a["id"],
            "candidate_b_version_id": candidate_b["id"],
            "declared_treatment": treatment,
            "client_request_id": key,
        },
    )


def _reserve_comparison(session, candidate_a, candidate_b, investigation, key: str = "cmp-raw"):
    """Reserve through the orchestrator so nothing executes yet."""
    conn = db.connect(session.db_file)
    try:
        experiment = orchestrator.create_qualifying_comparison(
            conn,
            session.shift_id,
            candidate_a_version_id=candidate_a["id"],
            candidate_b_version_id=candidate_b["id"],
            investigation_id=investigation["id"],
            declared_treatment=TREATMENT,
            client_request_id=key,
        )
        view = orchestrator.experiment_view(conn, experiment.id)
        return experiment, view
    finally:
        conn.close()


def _counts(conn) -> dict:
    return {
        "experiments": int(
            conn.execute("SELECT COUNT(*) AS n FROM experiments").fetchone()["n"]
        ),
        "runs": int(conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"]),
        "contexts": repo.count_execution_contexts(conn),
        "reservations": repo.count_exposure_reservations(conn),
        "items": int(conn.execute("SELECT COUNT(*) AS n FROM exposure_items").fetchone()["n"]),
        "slots": int(conn.execute("SELECT COUNT(*) AS n FROM trial_slots").fetchone()["n"]),
    }


def _wait_comparison(session, experiment_id: str, deadline_s: float = 90) -> dict:
    import time

    deadline = time.monotonic() + deadline_s
    while True:
        view = session.client.get(f"/api/experiments/{experiment_id}").json()
        if view["state"] in ("FINALIZED", "FAILED") or time.monotonic() > deadline:
            return view
        time.sleep(0.05)


def test_draft_material_cannot_reserve_a_production_comparison(session, monkeypatch, tmp_path):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    # The shipped manifest carries an operator seal, so this builds the draft the
    # guard exists to refuse: the same bytes with the seal withdrawn. Constructing
    # it keeps the proof independent of where the fixture lifecycle happens to be,
    # and still exercises the real gate against the real request batch files.
    reviewed = json.loads(config.PIVOT_COMPARE_MANIFEST.read_bytes().decode("utf-8"))
    draft = dict(reviewed, review_status="AWAITING_OPERATOR_REVIEW")
    draft.pop("sealed_payload_sha256", None)
    draft_path = tmp_path / "draft_compare_manifest.json"
    draft_path.write_bytes(json.dumps(draft, indent=2, ensure_ascii=False).encode("utf-8"))
    monkeypatch.setattr(config, "PIVOT_COMPARE_MANIFEST", draft_path)
    monkeypatch.setattr(orchestrator, "_require_reviewed_comparison_material", _REVIEW_GATE)
    monkeypatch.setattr(sealed_store, "load_reviewed_comparison_family", _REVIEWED_FAMILY)
    conn = db.connect(session.db_file)
    try:
        before = _counts(conn)
    finally:
        conn.close()
    response = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert response.status_code == 409, response.text
    assert "awaits operator review and sealing" in response.json()["detail"]
    conn = db.connect(session.db_file)
    try:
        assert _counts(conn) == before
    finally:
        conn.close()


def test_a_status_label_without_an_exact_seal_cannot_admit_material(monkeypatch, tmp_path):
    # The shipped material carries an operator seal, so each limb withdraws it from
    # a copy. That keeps the proof independent of the fixture lifecycle and lets it
    # assert the stronger property its name claims: the digest must match exactly,
    # not merely be present beside the label.
    manifest = json.loads(config.PIVOT_COMPARE_MANIFEST.read_text(encoding="utf-8"))
    manifest["review_status"] = "OPERATOR_SEALED"
    manifest.pop("sealed_payload_sha256", None)
    with pytest.raises(orchestrator.LifecycleError, match="awaits operator review"):
        _REVIEW_GATE(manifest, "comparison workload manifest", "workloads")
    manifest["sealed_payload_sha256"] = "0" * 64
    with pytest.raises(orchestrator.LifecycleError, match="awaits operator review"):
        _REVIEW_GATE(manifest, "comparison workload manifest", "workloads")
    sealed_dir = tmp_path / "sealed_cases"
    sealed_dir.mkdir()
    family_name = sealed_store._FAMILY_FILES[sealed_store.TASK_COMPLETION]
    family = json.loads((config.SEALED_CASES_DIR / family_name).read_text(encoding="utf-8"))
    family["review_status"] = "OPERATOR_SEALED"
    family.pop("sealed_payload_sha256", None)
    (sealed_dir / family_name).write_text(json.dumps(family, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(config, "SEALED_CASES_DIR", sealed_dir)
    with pytest.raises(Exception, match="awaits operator review"):
        _REVIEWED_FAMILY("task_completion")


def test_three_available_variants_are_not_a_six_variant_inventory():
    cases = sealed_store.load_family("task_completion").cases
    with pytest.raises(RotationMisconfigured, match="at least six"):
        rotation.select_pair_variants("task_completion", cases[:3], ())


def test_comparison_variant_identity_cannot_be_refreshed_by_renaming_its_id():
    case = sealed_store.load_family("task_completion").cases[0]
    renamed = case.model_copy(update={"id": case.id + "-new"})
    assert rotation.variant_ref(renamed) == rotation.variant_ref(case)
    with pytest.raises(RotationMisconfigured, match="reuses the exposed identity"):
        rotation.validate_refill((renamed,), (rotation.variant_ref(case),))


def test_each_initial_protected_aspect_applies_to_its_assigned_pair():
    cases = sealed_store.load_family("task_completion").cases
    drawn = rotation.select_pair_variants("task_completion", cases, ())
    assert [case.expected["aspect"] for case in drawn] == [
        "every_required_task_returns_a_result",
        "fixed_task_claims_name_the_requested_entity_and_edition",
        "supported_negative_collection_is_a_completed_answer",
    ]
    assert [case.stimulus.request.ordinal for case in drawn] == [3, 3, 3]
    assert len({case.stimulus.request.request_id for case in cases}) == 6
    assert len({canonical.content_hash(case.stimulus.model_dump(mode="json")) for case in cases}) == 6
    specs = [json.loads((config.PIVOT_COMPARE_REQUEST_DIR /
        f"bookshop_compare_pair_{ordinal:02d}_specs.json").read_text(encoding="utf-8"))
        for ordinal in (1, 2, 3)]
    assert any("Salt Roads paperback" in spec["text"] and "collect" in spec["text"]
               for spec in specs[0])
    assert any("Salt Roads hardback" in spec["text"] for spec in specs[1])
    assert all(any(task["required"] for task in spec["tasks"]) for spec in specs[2])


def test_candidates_make_a_measured_price_versus_stock_choice_on_request_011():
    snapshot = json.loads(config.PIVOT_COMPARE_STATE.read_text(encoding="utf-8"))
    results = []
    for label, function in (("A", "alternative_outcome"), ("B", "plan_alternative")):
        source = config.PIVOT_COMPARE_CANDIDATE_SOURCES[label]
        module = runpy.run_path(str(source))
        results.append(module[function](snapshot, "book:salt-roads:paperback", "2026-09-26", 2000))
    assert [result["entity_ref"] for result in results] == [
        "book:tidal-paths:paperback", "book:harbour-atlas:paperback"]
    assert [next(claim["value"] for claim in result["claims"] if claim["kind"] == "price")
            for result in results] == [1400, 1600]


def test_every_protected_spec_accepts_both_declared_candidate_envelopes():
    """A permitted optional price cannot fail A before the protected rule is read."""
    cases = sealed_store.load_family("task_completion").cases
    base = config.PIVOT_COMPARE_STATE.read_bytes()
    mission = task_contract.load_mission_bytes(config.PIVOT_MISSION.read_bytes())
    from shiftwork.domain.comparison import protected_acceptance
    for label, function in (("a", "answer"), ("b", "envelope")):
        module = runpy.run_path(str(config.PIVOT_COMPARE_CANDIDATE_SOURCES[label.upper()]))
        responder = module[function]
        responder.__globals__["observe"] = lambda *_args, **_kwargs: None
        for case in cases:
            spec = case.stimulus.task_spec
            price = next((task for task in spec.tasks if task.id == "price"), None)
            assert price is not None and price.required is False
            assert price.requested_entity_ref == case.stimulus.request.entity_ref
            snapshot = json.loads(task_contract.resolve_protected_state(
                base, case.stimulus.state_delta
            ))
            output = responder(case.stimulus.request.model_dump(mode="json"), snapshot)
            response = task_contract.validate_response_envelope(
                spec, json.dumps(output).encode("utf-8")
            )
            assessed = evaluator.assess_request(
                spec=spec, request_ordinal=case.stimulus.request.ordinal,
                mission=mission, snapshot=task_contract.load_public_state_bytes(
                    task_contract.resolve_protected_state(base, case.stimulus.state_delta)
                ), response=response,
            )
            assert protected_acceptance(case, assessed), (label, case.check_id)


def test_a_comparison_freezes_two_candidates_three_workloads_and_six_slots_before_results(session):
    """Obligation 16: the whole reservation exists before any slot runs."""
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, view = _reserve_comparison(session, candidate_a, candidate_b, investigation)

    assert experiment.kind is ExperimentKind.QUALIFYING_COMPARISON
    assert experiment.trial_count_per_candidate == 3
    assert [(candidate.label, candidate.artifact_content_hash) for candidate in experiment.candidates] == [
        ("A", candidate_a["content_hash"]),
        ("B", candidate_b["content_hash"]),
    ]
    assert [trial["state"] for trial in view["trials"]] == ["RESERVED"] * 6
    assert all(trial["outputs"] == [] and trial["task_assessments"] == [] for trial in view["trials"])
    assert [trial["execution_ordinal"] for trial in view["trials"]] == [1, 2, 3, 4, 5, 6]
    assert [trial["pair_ordinal"] for trial in view["trials"]] == [1, 1, 2, 2, 3, 3]
    assert [trial["workload_id"] for trial in view["trials"]] == [
        "workload-01", "workload-01", "workload-02", "workload-02", "workload-03", "workload-03",
    ]
    conn = db.connect(session.db_file)
    try:
        context = repo.get_execution_context(conn, experiment.context_id)
        reservation = repo.get_exposure_reservation_for_experiment(conn, experiment.id)
        items = repo.list_exposure_items(conn, reservation.id)
        slots = repo.list_trial_slots(conn, experiment.id)
    finally:
        conn.close()
    assert [workload.ordinal for workload in context.workloads] == [1, 2, 3]
    assert context.starting_business_state_json["ledger_event_count"] > 0
    assert context.starting_business_state_json["ledger_head_hash"]
    assert context.starting_business_state_json["chain_status"] == "VALID"
    assert context.starting_business_state_json["unresolved_incidents"]
    assert context.starting_business_state_json["unresolved_limits"] == []
    assert context.starting_business_state_hash == canonical.content_hash(
        context.starting_business_state_json
    )
    assert len(context.workloads) == 3
    assert context.protected_reservation_id == reservation.id
    assert context.executor_class.value == "TRUSTED_LOCAL"
    assert reservation.state == "ACTIVE" and reservation.scope == "comparison"
    assert [item.pair_ordinal for item in items] == [1, 2, 3]
    assert len({item.variant_ref for item in items}) == 3
    conn = db.connect(session.db_file)
    try:
        snapshots = sealed_store.load_reserved_comparison_cases(conn, reservation.id)
    finally:
        conn.close()
    assert [(item.family, item.pair_ordinal) for item in snapshots] == [
        ("task_completion", 1), ("task_completion", 2), ("task_completion", 3)]
    assert [rotation.variant_ref(item.case) for item in snapshots] == [
        item.variant_ref for item in items]
    for slot in slots:
        pair_refs = [item.variant_ref for item in items if item.pair_ordinal == slot.pair_ordinal]
        assert slot.protected_variant_refs == tuple(pair_refs)
        assert slot.executed_request_count == slot.request_count + 1 == 3
    assert all(slot.run_id is not None for slot in slots)
    # The six run rows exist queued, and the experiment schedules its own slots only.
    conn = db.connect(session.db_file)
    try:
        runs = [repo.get_run(conn, slot.run_id) for slot in slots]
    finally:
        conn.close()
    assert all(run.state is RunState.QUEUED and run.experiment_id == experiment.id for run in runs)
    assert {run.trial_slot_id for run in runs} == {slot.id for slot in slots}


def test_reserved_protected_cases_survive_later_edits_to_the_authored_file(
    session, monkeypatch, tmp_path,
):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, _ = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    conn = db.connect(session.db_file)
    try:
        reservation = repo.get_exposure_reservation_for_experiment(conn, experiment.id)
        stored_count = conn.execute(
            "SELECT COUNT(*) FROM protected_case_snapshots s JOIN exposure_items e "
            "ON s.exposure_item_id = e.id WHERE e.reservation_id = ?",
            (reservation.id,),
        ).fetchone()[0]
        assert stored_count == 3, "reservation omitted exact protected case snapshots"
        before = sealed_store.load_reserved_comparison_cases(conn, reservation.id)
        row = conn.execute(
            "SELECT exposure_item_id, payload_json FROM protected_case_snapshots LIMIT 1"
        ).fetchone()
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute(
                "UPDATE protected_case_snapshots SET payload_json = ? WHERE exposure_item_id = ?",
                ("{}", row["exposure_item_id"]),
            )
        conn.rollback()
        proposed = json.loads(
            (config.SEALED_CASES_DIR / "bookshop_task_completion.json").read_text(encoding="utf-8")
        )
        proposed["cases"][0]["expected"]["aspect"] = "later-author-edit"
        (tmp_path / "bookshop_task_completion.json").write_text(
            json.dumps(proposed), encoding="utf-8"
        )
        monkeypatch.setattr(config, "SEALED_CASES_DIR", tmp_path)
        assert sealed_store.load_family("task_completion").cases[0] != before[0][2]
        assert sealed_store.load_reserved_comparison_cases(conn, reservation.id) == before
    finally:
        conn.close()


def test_each_pair_shares_one_workload_and_the_reviewed_bytes_are_pinned(session):
    """Obligation 17: the frozen bindings match the reviewed files, not a path."""
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, view = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    manifest = json.loads(config.PIVOT_COMPARE_MANIFEST.read_bytes().decode("utf-8"))
    entries = {entry["ordinal"]: entry for entry in manifest["workloads"]}
    conn = db.connect(session.db_file)
    try:
        context = repo.get_execution_context(conn, experiment.context_id)
    finally:
        conn.close()
    for workload in context.workloads:
        entry = entries[workload.ordinal]
        raw = (config.PIVOT_COMPARE_REQUEST_DIR / entry["request_file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["request_bytes_sha256"]
        assert len(raw) == entry["request_bytes_length"]
        assert base64.b64decode(workload.request_batch_bytes_base64) == raw
        assert workload.request_batch_hash == canonical.content_hash(
            base64.b64encode(raw).decode("ascii")
        )
        assert workload.request_count == entry["request_count"] == len(
            [line for line in raw.splitlines() if line.strip()]
        )
        specs = [
            task_contract.CustomerRequestSpec.model_validate(item)
            for item in json.loads(
                base64.b64decode(workload.request_specs_bytes_base64).decode("utf-8")
            )
        ]
        assert len(specs) == workload.request_count
        assert hashlib.sha256(canonical.canonical_bytes(
            [spec.model_dump(mode="json") for spec in specs]
        )).hexdigest() == entry["task_specs_sha256"] == workload.request_specs_hash
        assert manifest["comparison_state_sha256"] == hashlib.sha256(
            config.PIVOT_COMPARE_STATE.read_bytes()).hexdigest()
    for pair in (1, 2, 3):
        trials = [trial for trial in view["trials"] if trial["pair_ordinal"] == pair]
        assert {trial["candidate_label"] for trial in trials} == {"A", "B"}
        assert {trial["workload_id"] for trial in trials} == {f"workload-{pair:02d}"}, (
            "a pair was bound to another pair's workload"
        )
        assert {trial["workload_ordinal"] for trial in trials} == {pair}
        assert len({trial["request_batch_hash"] for trial in trials}) == 1
        assert len({trial["request_count"] for trial in trials}) == 1
    conn = db.connect(session.db_file)
    try:
        items = repo.list_exposure_items(
            conn, repo.get_exposure_reservation_for_experiment(conn, experiment.id).id
        )
        slots = {slot.candidate_label + str(slot.pair_ordinal): slot for slot in repo.list_trial_slots(conn, experiment.id)}
    finally:
        conn.close()
    for pair in (1, 2, 3):
        left, right = slots[f"A{pair}"], slots[f"B{pair}"]
        assert left.workload_id == right.workload_id == f"workload-{pair:02d}"
        assert (left.workload_id, left.request_batch_hash, left.request_count) == (
            right.workload_id, right.request_batch_hash, right.request_count
        )
        assert left.protected_variant_refs == right.protected_variant_refs
        assert left.protected_variant_refs == tuple(
            item.variant_ref for item in items if item.pair_ordinal == pair
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "swap_ordinals",
        "drop_request",
        "edit_task_spec",
        "cross_engagement",
        "remove_file",
        "wrong_claimed_hash",
        "wrong_claimed_length",
        "wrong_claimed_specs_hash",
        "wrong_claimed_count",
        "bad_ordinal_with_recomputed_pin",
        "wrong_request_id_with_recomputed_pin",
        "wrong_text_with_recomputed_pin",
        "extra_request_with_recomputed_pin",
    ],
)
def test_a_manifest_mismatch_fails_closed_and_reserves_nothing(session, tmp_path, monkeypatch, mutation):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    directory = tmp_path / "workloads"
    directory.mkdir()
    for name in ("bookshop_compare_manifest.json", *WORKLOAD_FILES):
        (directory / name).write_bytes((config.PIVOT_COMPARE_REQUEST_DIR / name).read_bytes())
    manifest_path = directory / "bookshop_compare_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mutation == "swap_ordinals":
        first, second = manifest["workloads"][0], manifest["workloads"][1]
        first["request_file"], second["request_file"] = second["request_file"], first["request_file"]
    elif mutation == "drop_request":
        path = directory / manifest["workloads"][1]["request_file"]
        lines = [line for line in path.read_bytes().splitlines() if line.strip()]
        path.write_bytes(b"\n".join(lines[:1]) + b"\n")
    elif mutation == "edit_task_spec":
        path = directory / manifest["workloads"][0]["task_spec_file"]
        specs = json.loads(path.read_text(encoding="utf-8"))
        specs[0]["text"] = specs[0]["text"] + " Edited after review."
        path.write_text(json.dumps(specs, indent=2), encoding="utf-8")
    elif mutation == "cross_engagement":
        manifest["engagement_slug"] = "northline"
    elif mutation == "remove_file":
        (directory / manifest["workloads"][2]["request_file"]).unlink()
    elif mutation == "wrong_claimed_hash":
        # Only the recomputed raw-bytes hash can catch this: the file, its length,
        # its specs and its ids all still match every other check.
        manifest["workloads"][0]["request_bytes_sha256"] = "0" * 64
    elif mutation == "wrong_claimed_length":
        manifest["workloads"][0]["request_bytes_length"] = 999
    elif mutation == "wrong_claimed_specs_hash":
        manifest["workloads"][0]["task_specs_sha256"] = "0" * 64
    elif mutation == "wrong_claimed_count":
        manifest["workloads"][0]["request_count"] = 1
    elif mutation in {
        "bad_ordinal_with_recomputed_pin",
        "wrong_request_id_with_recomputed_pin",
        "wrong_text_with_recomputed_pin",
    }:
        entry = manifest["workloads"][0]
        path = directory / entry["request_file"]
        requests = [json.loads(line) for line in path.read_bytes().splitlines()]
        if mutation == "bad_ordinal_with_recomputed_pin":
            requests[0]["ordinal"] = 2
        elif mutation == "wrong_request_id_with_recomputed_pin":
            requests[0]["request_id"] = "different-request-id"
        else:
            requests[0]["text"] += " Changed after review."
        raw = b"".join(
            json.dumps(request, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
            for request in requests
        )
        path.write_bytes(raw)
        entry["request_bytes_sha256"] = hashlib.sha256(raw).hexdigest()
        entry["request_bytes_length"] = len(raw)
    elif mutation == "extra_request_with_recomputed_pin":
        # Every pin is recomputed, so only the recomputed count check can catch it.
        entry = manifest["workloads"][0]
        batch_path = directory / entry["request_file"]
        specs_path = directory / entry["task_spec_file"]
        requests = [json.loads(line) for line in batch_path.read_bytes().splitlines()]
        specs = json.loads(specs_path.read_text(encoding="utf-8"))
        extra = dict(requests[0])
        extra["ordinal"] = 3
        extra["request_id"] += "-extra"
        requests.append(extra)
        extra_spec = dict(specs[0])
        extra_spec["id"] = extra["request_id"]
        specs.append(extra_spec)
        raw = b"".join(
            json.dumps(request, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
            for request in requests
        )
        batch_path.write_bytes(raw)
        specs_path.write_text(json.dumps(specs, indent=2), encoding="utf-8")
        entry["request_bytes_sha256"] = hashlib.sha256(raw).hexdigest()
        entry["request_bytes_length"] = len(raw)
        entry["task_specs_sha256"] = hashlib.sha256(
            orchestrator._canonical_specs_bytes(
                tuple(task_contract.CustomerRequestSpec.model_validate(item) for item in specs)
            )
        ).hexdigest()
    if mutation != "remove_file":
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    monkeypatch.setattr(config, "PIVOT_COMPARE_REQUEST_DIR", directory)
    monkeypatch.setattr(config, "PIVOT_COMPARE_MANIFEST", manifest_path)

    conn = db.connect(session.db_file)
    try:
        before = _counts(conn)
        with pytest.raises(orchestrator.LifecycleError) as excinfo:
            orchestrator.create_qualifying_comparison(
                conn,
                session.shift_id,
                candidate_a_version_id=candidate_a["id"],
                candidate_b_version_id=candidate_b["id"],
                investigation_id=investigation["id"],
                declared_treatment=TREATMENT,
                client_request_id=f"cmp-{mutation}",
            )
        assert excinfo.value.kind == "conflict"
        assert _counts(conn) == before
    finally:
        conn.close()


def test_executor_incompatible_blank_line_fails_before_exposure(session, tmp_path, monkeypatch):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    directory = tmp_path / "workloads"
    directory.mkdir()
    for name in ("bookshop_compare_manifest.json", *WORKLOAD_FILES):
        (directory / name).write_bytes((config.PIVOT_COMPARE_REQUEST_DIR / name).read_bytes())
    manifest_path = directory / "bookshop_compare_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    entry = manifest["workloads"][0]
    batch_path = directory / entry["request_file"]
    raw = batch_path.read_bytes() + b"\n"
    batch_path.write_bytes(raw)
    entry["request_bytes_sha256"] = hashlib.sha256(raw).hexdigest()
    entry["request_bytes_length"] = len(raw)
    manifest_path.write_bytes(json.dumps(manifest).encode("utf-8"))
    monkeypatch.setattr(config, "PIVOT_COMPARE_REQUEST_DIR", directory)
    monkeypatch.setattr(config, "PIVOT_COMPARE_MANIFEST", manifest_path)

    conn = db.connect(session.db_file)
    try:
        before = _counts(conn)
        with pytest.raises(orchestrator.LifecycleError, match="malformed|unusable"):
            orchestrator.create_qualifying_comparison(
                conn, session.shift_id,
                candidate_a_version_id=candidate_a["id"],
                candidate_b_version_id=candidate_b["id"],
                investigation_id=investigation["id"],
                declared_treatment=TREATMENT,
                client_request_id="cmp-blank-line",
            )
        assert _counts(conn) == before
    finally:
        conn.close()


@pytest.mark.parametrize(
    "target",
    [
        "insert_exposure_reservation",
        "insert_exposure_item",
        "insert_protected_case_snapshot",
        "insert_execution_context",
        "insert_experiment",
        "experiment_link_update",
        "insert_trial_slot",
        "insert_run",
        "update_trial_slot",
    ],
)
def test_a_fault_mid_reservation_leaves_no_partial_comparison(session, monkeypatch, target):
    """Obligation 16: the reservation is all-or-nothing on every write."""
    candidate_a, candidate_b, investigation = _comparison_session(session)

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("injected reservation write fault")

    original = None if target == "experiment_link_update" else getattr(repo, target)
    if original is not None:
        monkeypatch.setattr(repo, target, fail)
    conn = db.connect(session.db_file)
    try:
        if target == "experiment_link_update":
            conn.execute(
                "CREATE TRIGGER reject_experiment_link BEFORE UPDATE OF experiment_id "
                "ON exposure_reservations BEGIN SELECT RAISE(ABORT, 'injected reservation write fault'); END"
            )
            conn.commit()
        before = _counts(conn)
        with pytest.raises(sqlite3.Error, match="injected reservation write fault"):
            orchestrator.create_qualifying_comparison(
                conn,
                session.shift_id,
                candidate_a_version_id=candidate_a["id"],
                candidate_b_version_id=candidate_b["id"],
                investigation_id=investigation["id"],
                declared_treatment=TREATMENT,
                client_request_id=f"cmp-fault-{target}",
            )
        assert _counts(conn) == before, "a faulted reservation left a partial row behind"
    finally:
        if target == "experiment_link_update":
            conn.execute("DROP TRIGGER reject_experiment_link")
            conn.commit()
        conn.close()
    if original is not None:
        monkeypatch.setattr(repo, target, original)
    # The faulted attempt consumed nothing: the same shift can still reserve.
    experiment, view = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    assert [trial["state"] for trial in view["trials"]] == ["RESERVED"] * 6
    conn = db.connect(session.db_file)
    try:
        assert repo.get_experiment(conn, experiment.id) is not None
    finally:
        conn.close()


@pytest.mark.parametrize("injected_write", [None, "ledger", "incident"])
def test_comparison_writes_no_business_state_and_guard_detects_an_insert(
    session, monkeypatch, injected_write,
):
    candidate_a, candidate_b, investigation = _comparison_session(session)

    def business_rows():
        conn = db.connect(session.db_file)
        try:
            return {
                "ledger": [tuple(row) for row in conn.execute(
                    "SELECT * FROM ledger_events WHERE engagement_slug = 'bookshop' ORDER BY seq"
                )],
                "incident": [tuple(row) for row in conn.execute(
                    "SELECT * FROM incidents WHERE engagement_slug = 'bookshop' ORDER BY id"
                )],
            }
        finally:
            conn.close()

    before = business_rows()
    assert before["ledger"] and before["incident"], "the positive controls need existing rows"
    if injected_write is not None:
        original = repo.insert_trial_slot
        inserted = False

        def insert_with_fault(conn, slot):
            nonlocal inserted
            original(conn, slot)
            if inserted:
                return
            inserted = True
            if injected_write == "ledger":
                conn.execute(
                    "INSERT INTO ledger_events SELECT engagement_slug, seq + 1000, event_type, "
                    "cause_refs_json, payload_json, synthetic, prev_hash, hash "
                    "FROM ledger_events WHERE engagement_slug = 'bookshop' "
                    "ORDER BY seq DESC LIMIT 1"
                )
            else:
                conn.execute(
                    "INSERT INTO incidents SELECT 'injected-comparison-incident', engagement_slug, "
                    "shift_id, opening_run_id, failing_output_ref, check_result_id, reason_code, "
                    "opened_event_seq, state, resolving_version_id, resolved_event_seq "
                    "FROM incidents WHERE engagement_slug = 'bookshop' LIMIT 1"
                )

        monkeypatch.setattr(repo, "insert_trial_slot", insert_with_fault)

    experiment, _ = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    if injected_write is None:
        orchestrator.execute_comparison_task(str(session.db_file), experiment.id)
    after = business_rows()

    def assert_no_business_write():
        assert after["ledger"] == before["ledger"], "comparison wrote a ledger event"
        assert after["incident"] == before["incident"], "comparison wrote an incident"

    if injected_write is None:
        assert_no_business_write()
    else:
        assert inserted
        with pytest.raises(AssertionError, match=f"comparison wrote an {injected_write}|comparison wrote a {injected_write}"):
            assert_no_business_write()


def test_a_repeated_comparison_worker_cannot_execute_reserved_slots_twice(session, monkeypatch):
    """A same-key retry must not start another worker while the first is in a slot."""
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, _ = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    from shiftwork.executor.local_process import LocalProcessAdapter

    entered = threading.Event()
    release = threading.Event()
    errors = []

    class BlockingFirst(LocalProcessAdapter):
        calls = 0

        async def execute(self, request):
            type(self).calls += 1
            if type(self).calls == 1:
                entered.set()
                if not release.wait(15):
                    raise TimeoutError("first comparison worker was never released")
            return await super().execute(request)

    def work():
        try:
            orchestrator.execute_comparison_task(str(session.db_file), experiment.id)
        except Exception as exc:
            errors.append(exc)

    monkeypatch.setattr(orchestrator, "LocalProcessAdapter", BlockingFirst)
    first = threading.Thread(target=work)
    second = threading.Thread(target=work)
    first.start()
    try:
        assert entered.wait(5), "the first worker never entered its first slot"
        second.start()
        second.join(5)
        assert not second.is_alive(), "the duplicate worker did not return promptly"
        assert BlockingFirst.calls == 1, "a duplicate worker ran a reserved slot"
    finally:
        release.set()
        first.join(20)
        if second.ident is not None:
            second.join(20)
    assert not errors, errors
    conn = db.connect(session.db_file)
    try:
        assert repo.get_experiment(conn, experiment.id).state == "FINALIZED"
        assert all(slot.state == "COMPLETE" for slot in repo.list_trial_slots(conn, experiment.id))
    finally:
        conn.close()


def test_two_same_key_http_posts_dispatch_only_one_comparison_worker(session, monkeypatch):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    from shiftwork.executor.local_process import LocalProcessAdapter

    entered = threading.Event()
    release = threading.Event()
    responses = []
    errors = []

    class BlockingFirst(LocalProcessAdapter):
        calls = 0

        async def execute(self, request):
            type(self).calls += 1
            if type(self).calls == 1:
                entered.set()
                if not release.wait(15):
                    raise TimeoutError("first HTTP worker was never released")
            return await super().execute(request)

    def post():
        try:
            responses.append(_create_comparison(
                session, candidate_a, candidate_b, investigation, key="cmp-concurrent-http"
            ))
        except Exception as exc:
            errors.append(exc)

    monkeypatch.setattr(orchestrator, "LocalProcessAdapter", BlockingFirst)
    conn = db.connect(session.db_file)
    try:
        before = _counts(conn)
    finally:
        conn.close()
    first = threading.Thread(target=post)
    second = threading.Thread(target=post)
    first.start()
    try:
        assert entered.wait(5), "the first HTTP worker never entered its first slot"
        second.start()
        second.join(5)
        assert not second.is_alive(), "the duplicate HTTP POST did not return promptly"
        assert BlockingFirst.calls == 1, "the duplicate POST dispatched another slot"
    finally:
        release.set()
        first.join(30)
        if second.ident is not None:
            second.join(30)
    assert not errors, errors
    assert len(responses) == 2 and all(response.status_code == 202 for response in responses)
    assert len({response.json()["id"] for response in responses}) == 1
    experiment_id = responses[0].json()["id"]
    conn = db.connect(session.db_file)
    try:
        after = _counts(conn)
        slots = repo.list_trial_slots(conn, experiment_id)
        assert repo.get_experiment(conn, experiment_id).state == "FINALIZED"
        assert len(slots) == 6 and all(slot.state == "COMPLETE" for slot in slots)
    finally:
        conn.close()
    assert after["experiments"] == before["experiments"] + 1
    assert after["reservations"] == before["reservations"] + 1
    assert after["items"] == before["items"] + 3
    assert after["slots"] == before["slots"] + 6
    assert BlockingFirst.calls == 12, "each of six slots needs one public and one protected operation"


def test_two_http_posts_can_dispatch_workers_before_claim_without_duplicate_execution(
    session, monkeypatch,
):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    from shiftwork.executor.local_process import LocalProcessAdapter

    both_dispatched = threading.Event()
    release = threading.Event()
    lock = threading.Lock()
    dispatches = []
    responses = []
    errors = []
    original_task = orchestrator.execute_comparison_task

    class CountingAdapter(LocalProcessAdapter):
        calls = 0

        async def execute(self, request):
            type(self).calls += 1
            return await super().execute(request)

    def held_task(db_path, experiment_id):
        with lock:
            dispatches.append(experiment_id)
            if len(dispatches) == 2:
                both_dispatched.set()
        if not release.wait(15):
            raise TimeoutError("the two HTTP workers were not released")
        return original_task(db_path, experiment_id)

    def post():
        try:
            responses.append(_create_comparison(
                session, candidate_a, candidate_b, investigation, key="cmp-before-claim"
            ))
        except Exception as exc:
            errors.append(exc)

    monkeypatch.setattr(orchestrator, "execute_comparison_task", held_task)
    monkeypatch.setattr(orchestrator, "LocalProcessAdapter", CountingAdapter)
    first = threading.Thread(target=post)
    second = threading.Thread(target=post)
    first.start()
    second.start()
    try:
        assert both_dispatched.wait(10), "both same-key HTTP requests did not dispatch workers"
        assert len(set(dispatches)) == 1
    finally:
        release.set()
        first.join(30)
        second.join(30)
    assert not errors, errors
    assert len(responses) == 2 and all(response.status_code == 202 for response in responses)
    assert len({response.json()["id"] for response in responses}) == 1
    experiment_id = responses[0].json()["id"]
    conn = db.connect(session.db_file)
    try:
        assert repo.get_experiment(conn, experiment_id).state == "FINALIZED"
        assert len(repo.list_trial_slots(conn, experiment_id)) == 6
        assert repo.count_exposure_reservations(conn) == 1
        assert repo.count_experiments_for_shift(
            conn, session.shift_id, ExperimentKind.QUALIFYING_COMPARISON
        ) == 1
    finally:
        conn.close()
    assert CountingAdapter.calls == 12


@pytest.mark.parametrize("boundary", ["reserved", "claimed", "mid_slot"])
def test_restart_terminalizes_comparison_without_retry_and_keeps_capture(
    session, restart, boundary,
):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, _ = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    conn = db.connect(session.db_file)
    try:
        slots = repo.list_trial_slots(conn, experiment.id)
        reservation = repo.get_exposure_reservation_for_experiment(conn, experiment.id)
        exposure = repo.list_exposure_items(conn, reservation.id)
        assert len(slots) == 6 and len(exposure) == 3
        if boundary != "reserved":
            assert repo.claim_comparison_execution(conn, experiment.id)
        if boundary == "mid_slot":
            run = repo.get_run(conn, slots[0].run_id)
            repo.update_run(conn, run.id, RunState.RUNNING)
            repo.update_trial_slot(conn, slots[0].id, state="RUNNING")
            repo.insert_output(conn, RunOutput(
                id=f"{run.id}-retained", run_id=run.id, request_ordinal=1,
                request_text="retained first request", http_status=200,
                body=b'{"retained":true}', elapsed_ms=11,
            ))
            for ordinal, kind, payload in (
                (1, ObservationKind.INFERENCE_REQUEST, {}),
                (2, ObservationKind.INFERENCE_RESULT,
                 {"input_tokens": 7, "output_tokens": 9, "elapsed_ms": 13}),
            ):
                repo.insert_observation(conn, ExecutionObservation(
                    id=f"{run.id}-usage-{ordinal}", run_id=run.id,
                    request_ordinal=1, ordinal=ordinal, kind=kind,
                    public_payload_json=payload, raw_payload_ref="",
                    measured_at=datetime.now(timezone.utc),
                ))
        conn.commit()
    finally:
        conn.close()

    restarted = restart(session.db_file)
    response = restarted.client.get(f"/api/experiments/{experiment.id}")
    assert response.status_code == 200, response.text
    view = response.json()
    assert view["state"] == "FAILED", "GET left an unclaimable comparison nonterminal"
    assert [trial["state"] for trial in view["trials"]] == ["FAILED"] * 6
    assert view["outcome"]["status"] == "INCOMPLETE"
    assert all(not item["eligible"] for item in view["outcome"]["eligibility"])
    assert view["outcome"]["candidate_metrics"][0]["protected_missing"] == 3
    if boundary == "mid_slot":
        metrics = view["outcome"]["candidate_metrics"][0]
        assert (metrics["service_calls"], metrics["input_tokens"],
                metrics["output_tokens"], metrics["service_latency_ms"]) == (1, 7, 9, 13)
    conn = db.connect(session.db_file)
    try:
        assert all(repo.get_run(conn, slot.run_id).state is RunState.FAILED for slot in slots)
        assert all(repo.get_run(conn, slot.run_id).failure_kind is ExecutorFailure.INTERNAL for slot in slots)
        assert repo.get_exposure_reservation(conn, reservation.id).state == "ACTIVE"
        assert repo.list_exposure_items(conn, reservation.id) == exposure
        retained = repo.list_outputs(conn, slots[0].run_id)
        assert len(retained) == (1 if boundary == "mid_slot" else 0)
        if retained:
            assert retained[0].body == b'{"retained":true}'
            assert [item.kind for item in repo.list_observations(conn, slots[0].run_id)] == [
                ObservationKind.INFERENCE_REQUEST, ObservationKind.INFERENCE_RESULT,
            ]
    finally:
        conn.close()
    orchestrator.execute_comparison_task(str(session.db_file), experiment.id)
    assert restarted.client.get(f"/api/experiments/{experiment.id}").json() == view


def test_an_unexpected_slot_error_fails_the_comparison_without_retry(session, monkeypatch):
    """An exception must leave a terminal, inspectable comparison and spent slot."""
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, _ = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    from shiftwork.executor.local_process import LocalProcessAdapter

    class RaisingFirst(LocalProcessAdapter):
        calls = 0

        async def execute(self, request):
            type(self).calls += 1
            raise RuntimeError("injected slot error")

    monkeypatch.setattr(orchestrator, "LocalProcessAdapter", RaisingFirst)
    with pytest.raises(RuntimeError, match="injected slot error"):
        orchestrator.execute_comparison_task(str(session.db_file), experiment.id)
    conn = db.connect(session.db_file)
    try:
        view = orchestrator.experiment_view(conn, experiment.id)
        assert view["state"] == "FAILED", "a background error stranded the comparison in RUNNING"
        assert view["trials"][0]["state"] == "FAILED"
        assert all(trial["state"] == "RESERVED" for trial in view["trials"][1:])
        assert repo.get_run(conn, view["trials"][0]["run_id"]).failure_kind is ExecutorFailure.INTERNAL
    finally:
        conn.close()
    orchestrator.execute_comparison_task(str(session.db_file), experiment.id)
    assert RaisingFirst.calls == 1, "a repeated worker retried the failed slot"


def test_a_pre_adapter_slot_error_fails_the_touched_slot_without_retry(session, monkeypatch):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, _ = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    original = repo.set_run_snapshot_bytes
    calls = 0

    def fail_before_adapter(conn, run_id, snapshot):
        nonlocal calls
        calls += 1
        raise RuntimeError("injected pre-adapter slot error")

    monkeypatch.setattr(repo, "set_run_snapshot_bytes", fail_before_adapter)
    with pytest.raises(RuntimeError, match="injected pre-adapter slot error"):
        orchestrator.execute_comparison_task(str(session.db_file), experiment.id)
    conn = db.connect(session.db_file)
    try:
        view = orchestrator.experiment_view(conn, experiment.id)
        assert view["state"] == "FAILED"
        assert view["trials"][0]["state"] == "FAILED", "the touched slot still looks unattempted"
        assert all(trial["state"] == "RESERVED" for trial in view["trials"][1:])
        run = repo.get_run(conn, view["trials"][0]["run_id"])
        assert run.state is RunState.FAILED and run.failure_kind is ExecutorFailure.INTERNAL
    finally:
        conn.close()
    monkeypatch.setattr(repo, "set_run_snapshot_bytes", original)
    orchestrator.execute_comparison_task(str(session.db_file), experiment.id)
    assert calls == 1, "a repeated worker retried the touched slot"


def test_the_precommitted_schedule_is_stored_executed_once_and_not_reorderable(session, monkeypatch):
    """Obligation 18: pair 3 order is derived before results and never rewritten."""
    candidate_a, candidate_b, investigation = _comparison_session(session)
    calls: list[tuple[int, str]] = []
    original = orchestrator.execute_comparison_slot

    def spy(conn, slot):
        calls.append((slot.pair_ordinal, slot.candidate_label))
        return original(conn, slot)

    monkeypatch.setattr(orchestrator, "execute_comparison_slot", spy)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    view = _wait_comparison(session, created.json()["id"])
    assert view["state"] == "FINALIZED"
    conn = db.connect(session.db_file)
    try:
        experiment = repo.get_experiment(conn, view["id"])
        context = repo.get_execution_context(conn, experiment.context_id)
        slots = repo.list_trial_slots(conn, experiment.id)
    finally:
        conn.close()
    assert [(slot.pair_ordinal, slot.candidate_label) for slot in slots[:2]] == [(1, "A"), (1, "B")]
    assert [(slot.pair_ordinal, slot.candidate_label) for slot in slots[2:4]] == [(2, "B"), (2, "A")]
    decision = hashlib.sha256(
        f"{context.content_hash}:{candidate_a['content_hash']}:{candidate_b['content_hash']}".encode("utf-8")
    ).digest()
    expected_third = ("A", "B") if decision[-1] & 1 == 0 else ("B", "A")
    assert (slots[4].candidate_label, slots[5].candidate_label) == expected_third
    assert calls == [(slot.pair_ordinal, slot.candidate_label) for slot in slots], (
        "the six slots did not execute in the stored precommitted order"
    )


def test_a_stored_slot_is_immutable_except_its_run_and_state(session):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, _view = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    conn = db.connect(session.db_file)
    try:
        slot = repo.list_trial_slots(conn, experiment.id)[0]
        for column, value in (
            ("execution_ordinal", 6),
            ("pair_ordinal", 3),
            ("candidate_label", "B"),
            ("workload_id", "workload-03"),
            ("request_count", 3),
            ("request_batch_hash", "0" * 64),
            ("artifact_version_id", "ver-0001"),
            ("protected_variant_refs_json", '["var-0000000000000000"]'),
            ("experiment_id", "experiment-other"),
        ):
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(f"UPDATE trial_slots SET {column} = ? WHERE id = ?", (value, slot.id))
            conn.rollback()
        assert repo.get_trial_slot(conn, slot.id) == slot
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM trial_slots WHERE id = ?", (slot.id,))
        conn.rollback()
        assert repo.get_trial_slot(conn, slot.id) == slot
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO trial_slots (id, experiment_id, pair_ordinal, execution_ordinal, "
                "candidate_label, artifact_version_id, workload_id, request_batch_hash, "
                "request_count, protected_variant_refs_json, run_id, state) "
                "VALUES ('slot-dup', ?, ?, 6, ?, ?, 'workload-01', ?, 2, '[]', NULL, 'RESERVED')",
                (slot.experiment_id, slot.pair_ordinal, slot.candidate_label, slot.artifact_version_id,
                 slot.request_batch_hash),
            )
        conn.rollback()
    finally:
        conn.close()


def test_a_failed_slot_stays_visible_and_the_comparison_is_never_refunded(session, monkeypatch):
    """Obligation 20: a missing slot blocks completion and keeps its exposure."""
    candidate_a, candidate_b, investigation = _comparison_session(session)
    from shiftwork.executor.local_process import LocalProcessAdapter

    class FailingFifth(LocalProcessAdapter):
        calls = 0

        async def execute(self, request):
            type(self).calls += 1
            if type(self).calls == 9:
                return executor_base.RunResult(
                    captures=(), executor_ref=None,
                    failure=ExecutorFailure.SERVICE_UNREACHABLE, wall_ms=0,
                )
            return await super().execute(request)

    monkeypatch.setattr(orchestrator, "LocalProcessAdapter", FailingFifth)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    view = _wait_comparison(session, created.json()["id"])
    assert view["state"] == "FAILED"
    assert [trial["state"] for trial in view["trials"]] == [
        "COMPLETE", "COMPLETE", "COMPLETE", "COMPLETE", "FAILED", "COMPLETE",
    ]
    failed = view["trials"][4]
    assert failed["outputs"] == []
    assert any("execution failure" in entry for entry in failed["missing_evidence"])
    conn = db.connect(session.db_file)
    try:
        failed_run = repo.get_run(conn, failed["run_id"])
        reservation = repo.get_exposure_reservation_for_experiment(conn, view["id"])
        items = repo.list_exposure_items(conn, reservation.id)
        slots = repo.list_trial_slots(conn, view["id"])
    finally:
        conn.close()
    assert failed_run.state is RunState.FAILED
    assert failed_run.failure_kind is ExecutorFailure.SERVICE_UNREACHABLE
    assert len(items) == 3 and all(item.state.value == "active" for item in items)
    monkeypatch.setattr(orchestrator, "LocalProcessAdapter", LocalProcessAdapter)
    orchestrator.execute_comparison_task(str(session.db_file), view["id"])
    conn = db.connect(session.db_file)
    try:
        after = repo.list_trial_slots(conn, view["id"])
        outputs = repo.list_outputs(conn, failed["run_id"])
    finally:
        conn.close()
    assert [slot.state for slot in after] == [slot.state for slot in slots], (
        "re-running the comparison retried a terminal slot"
    )
    assert outputs == [], "the failed slot was refunded a capture it never produced"
    refused = _create_comparison(session, candidate_a, candidate_b, investigation, key="cmp-retake")
    assert refused.status_code == 409, refused.text
    assert "already reserved its qualifying comparison" in refused.json()["detail"]


def test_success_flag_without_captures_fails_the_slot_without_refunding_exposure(session, monkeypatch):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    from shiftwork.executor.local_process import LocalProcessAdapter

    class MissingCapture(LocalProcessAdapter):
        calls = 0

        async def execute(self, request):
            type(self).calls += 1
            if type(self).calls == 9:
                return executor_base.RunResult(captures=(), executor_ref=None, failure=None, wall_ms=0)
            return await super().execute(request)

    monkeypatch.setattr(orchestrator, "LocalProcessAdapter", MissingCapture)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    view = _wait_comparison(session, created.json()["id"])
    assert view["state"] == "FAILED"
    assert view["trials"][4]["state"] == "FAILED"
    assert view["trials"][4]["outputs"] == []
    conn = db.connect(session.db_file)
    try:
        run = repo.get_run(conn, view["trials"][4]["run_id"])
        reservation = repo.get_exposure_reservation_for_experiment(conn, view["id"])
        items = repo.list_exposure_items(conn, reservation.id)
        assert run.state is RunState.FAILED
        assert run.failure_kind is ExecutorFailure.CAPTURE_TRUNCATED
        assert len(items) == 3 and all(item.state.value == "active" for item in items)
    finally:
        conn.close()


def test_comparison_persists_the_second_requests_observation_ordinal(session, monkeypatch):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    from shiftwork.executor.local_process import LocalProcessAdapter

    class ObservedSecond(LocalProcessAdapter):
        async def execute(self, request):
            result = await super().execute(request)
            observation = executor_base.RawObservation(kind="INTERPRETATION",
                public_payload={"source": "controller_verified", "request_ordinal": 2,
                                "probe": "second_request"}, raw_payload={})
            return result.model_copy(update={"observations": (*result.observations, observation)})

    monkeypatch.setattr(orchestrator, "LocalProcessAdapter", ObservedSecond)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    view = _wait_comparison(session, created.json()["id"])
    assert view["state"] == "FINALIZED"
    conn = db.connect(session.db_file)
    try:
        observations = repo.list_observations(conn, view["trials"][0]["run_id"])
    finally:
        conn.close()
    assert [(item.request_ordinal, item.public_payload_json["probe"])
            for item in observations] == [(2, "second_request"), (3, "second_request")]


@pytest.mark.parametrize("tamper", ["swap_bytes", "wrong_count", "slot_hash", "slot_count"])
def test_a_tampered_workload_binding_fails_the_slot_instead_of_running_another_batch(
    session, tamper
):
    """A slot never silently executes a batch other than the one it froze."""
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, _view = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    conn = db.connect(session.db_file)
    try:
        if tamper in ("slot_hash", "slot_count"):
            # The DB guard blocks slot-row edits; drop it to simulate a slot
            # binding that no longer matches the frozen context.
            conn.execute("DROP TRIGGER trial_slots_guard_update")
            if tamper == "slot_hash":
                conn.execute(
                    "UPDATE trial_slots SET request_batch_hash = ? WHERE experiment_id = ?",
                    ("0" * 64, experiment.id),
                )
            else:
                conn.execute(
                    "UPDATE trial_slots SET request_count = ? WHERE experiment_id = ?",
                    (3, experiment.id),
                )
        else:
            context = repo.get_execution_context(conn, experiment.context_id)
            workloads = [workload.model_dump(mode="json") for workload in context.workloads]
            stolen = dict(workloads[0])
            stolen["id"] = workloads[1]["id"]
            if tamper == "wrong_count":
                stolen = dict(workloads[1])
                stolen["request_count"] = 1
            workloads[1] = stolen
            conn.execute(
                "UPDATE execution_contexts SET workloads_json = ? WHERE id = ?",
                (json.dumps(workloads), context.id),
            )
        conn.commit()
    finally:
        conn.close()
    orchestrator.execute_comparison_task(str(session.db_file), experiment.id)
    conn = db.connect(session.db_file)
    try:
        view = orchestrator.experiment_view(conn, experiment.id)
        slots = repo.list_trial_slots(conn, experiment.id)
        assert {slot.state for slot in slots} == {"FAILED"}, (
            "a tampered binding fails every slot closed instead of running another batch"
        )
        assert view["state"] == "FAILED"
        for trial in view["trials"]:
            run = repo.get_run(conn, trial["run_id"])
            assert run.failure_kind is ExecutorFailure.PROVISION_FAILED
            assert repo.list_outputs(conn, trial["run_id"]) == [], (
                "the tampered slot ran a batch it never froze"
            )
            assert trial["task_assessments"] == []
    finally:
        conn.close()


def test_every_slot_gets_its_own_fresh_reset_workspace(session, monkeypatch):
    """A cache, booking or process sentinel cannot survive into the next slot."""
    candidate_a, candidate_b, investigation = _comparison_session(session)
    created: list[str] = []
    removed: list[str] = []
    original = tempfile.TemporaryDirectory

    class RecordingDirectory(original):
        """Record only the comparison's own slot workspaces, not the adapter's."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if "shiftwork-compare-" in self.name:
                created.append(self.name)

        def __exit__(self, *args):
            if "shiftwork-compare-" in self.name:
                removed.append(self.name)
            return super().__exit__(*args)

    monkeypatch.setattr(orchestrator.tempfile, "TemporaryDirectory", RecordingDirectory)
    created_experiment = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created_experiment.status_code == 202, created_experiment.text
    view = _wait_comparison(session, created_experiment.json()["id"])
    assert view["state"] == "FINALIZED"
    assert len(created) == 6, "the comparison did not give every slot its own workspace"
    assert len(set(created)) == 6, "a workspace was reused across slots"
    assert all(name in removed for name in created), "a slot workspace was left behind"
    prefixes = {name.rsplit("shiftwork-compare-", 1)[-1].split("-")[0] for name in created}
    assert prefixes == {"1", "2", "3"}, "a slot workspace is not bound to its own pair"


def test_a_sentinel_left_by_one_execution_is_invisible_to_the_next(session, monkeypatch):
    """The executor never reuses a workspace, so a written sentinel cannot leak."""
    import asyncio

    from shiftwork.domain import canonical as canonical_module
    from shiftwork.executor import base as executor_module
    from shiftwork.executor.local_process import LocalProcessAdapter

    sentinel_source = (
        "import json\n"
        "from pathlib import Path\n"
        "from http.server import BaseHTTPRequestHandler, HTTPServer\n"
        "SENTINEL = Path('sentinel.json')\n"
        "SEEN = SENTINEL.exists()\n"
        "SENTINEL.write_text('slot-local')\n"
        "class Handler(BaseHTTPRequestHandler):\n"
        "    protocol_version = 'HTTP/1.1'\n"
        "    def do_POST(self):\n"
        "        length = int(self.headers.get('Content-Length', '0'))\n"
        "        request = json.loads(self.rfile.read(length))\n"
        "        body = json.dumps({'request_id': request['request_id'], 'task_results': [],\n"
        "            'evidence_refs': [], 'uncertainty_codes': ['sentinel_seen' if SEEN else 'sentinel_absent']}).encode()\n"
        "        self.send_response(200)\n"
        "        self.send_header('Content-Length', str(len(body)))\n"
        "        self.end_headers()\n"
        "        self.wfile.write(body)\n"
        "    def log_message(self, *args):\n"
        "        pass\n"
        "if __name__ == '__main__':\n"
        "    with HTTPServer(('127.0.0.1', 0), Handler) as server:\n"
        "        print(json.dumps({'port': server.server_port}), flush=True)\n"
        "        server.serve_forever()\n"
    )
    files = {"service.py": sentinel_source.encode("utf-8")}
    file_hash = canonical_module.content_hash(
        {"service.py": base64.b64encode(files["service.py"]).decode("ascii")}
    )
    monkeypatch.setitem(config.TRUSTED_LOCAL_FIXTURES, "sentinel_probe", ("0" * 64, file_hash))
    batch_bytes = b'{"ordinal":1,"request_id":"probe-1","text":"probe","entity_ref":"book:salt-roads:paperback"}\n'
    batch_ref = executor_module.BatchRef(
        path_ref="sentinel_probe.jsonl",
        content_hash=canonical_module.content_hash(
            base64.b64encode(batch_bytes).decode("ascii")
        ),
    )
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        snapshot_path = Path(directory) / "public_state.json"
        snapshot_path.write_bytes(config.PIVOT_PUBLIC_STATE.read_bytes())
        request = executor_module.RunRequest(
            artifact_snapshot=executor_module.ArtifactSnapshotRef(
                files=files, manifest_hash="0" * 64
            ),
            request_batch=batch_ref,
            shop_snapshot_ref=str(snapshot_path),
            harness_ref="stdlib-loopback-v1",
            image_ref="local-python-stdlib",
            deadline_s=10,
            inference_grant=None,
            request_batch_bytes=batch_bytes,
        )
        adapter = LocalProcessAdapter()
        first = asyncio.run(adapter.execute(request))
        second = asyncio.run(adapter.execute(request))
    assert first.failure is None and second.failure is None
    assert b"sentinel_absent" in first.captures[0].body
    assert b"sentinel_absent" in second.captures[0].body, (
        "the second execution saw the sentinel the first one wrote"
    )


def test_the_request_driver_never_provisions_future_customer_wording(session, monkeypatch):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    from shiftwork.executor import local_process

    provisioned: list[bytes] = []
    original = local_process.provision_workspace

    def record(root, request, shop_snapshot):
        manifest = original(root, request, shop_snapshot)
        for path in manifest.paths:
            provisioned.append(Path(root, path).read_bytes())
        return manifest

    monkeypatch.setattr(local_process, "provision_workspace", record)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    view = _wait_comparison(session, created.json()["id"])
    assert view["state"] == "FINALIZED"
    assert len(provisioned) == 24, "each slot provisions two fresh artifact and state pairs"
    texts = [
        json.loads(line)["text"]
        for entry in json.loads(config.PIVOT_COMPARE_MANIFEST.read_bytes().decode("utf-8"))["workloads"]
        for line in (config.PIVOT_COMPARE_REQUEST_DIR / entry["request_file"]).read_bytes().splitlines()
        if line.strip()
    ]
    for blob in provisioned:
        for text in texts:
            assert text.encode("utf-8") not in blob, (
                "future customer wording entered a slot's workspace payload"
            )
        assert b"compare_pair" not in blob


def test_the_workload_summary_exposes_no_future_request_bytes_or_protected_refs(session):
    """Obligation 40: before a slot runs, only safe ids, hashes and counts."""
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, view = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    serialized = json.dumps(view, default=str)

    def escaped(value: str) -> str:
        return json.dumps(value)[1:-1]

    manifest = json.loads(config.PIVOT_COMPARE_MANIFEST.read_bytes().decode("utf-8"))
    future_texts = [
        json.loads(line)["text"]
        for entry in manifest["workloads"]
        for line in (config.PIVOT_COMPARE_REQUEST_DIR / entry["request_file"]).read_bytes().splitlines()
        if line.strip()
    ]
    conn = db.connect(session.db_file)
    try:
        reservation = repo.get_exposure_reservation_for_experiment(conn, experiment.id)
        refs = [item.variant_ref for item in repo.list_exposure_items(conn, reservation.id)]
    finally:
        conn.close()
    needles = {
        "future_request_text": future_texts[0],
        "workload_filename": manifest["workloads"][0]["request_file"],
        "task_spec_filename": manifest["workloads"][0]["task_spec_file"],
        "protected_ref": refs[0],
        "reservation_id": reservation.id,
        "sealed_path": str(config.SEALED_CASES_DIR),
        "variant_ref_key": "variant_ref",
        "expected_block": "expected",
        "batch_base64": "request_batch_bytes_base64",
    }
    # Capability self-test: every needle must be detectable inside this exact
    # serialized shape once injected, or the absence checks below prove nothing.
    for name, needle in needles.items():
        injected = json.loads(json.dumps(view, default=str))
        injected["trials"][0]["probe"] = needle
        dumped = json.dumps(injected, default=str)
        assert needle in dumped or escaped(needle) in dumped, f"needle {name!r} cannot match"
    for name, needle in needles.items():
        assert needle not in serialized, f"the pre-execution comparison view leaked {name}"
        assert escaped(needle) not in serialized, f"the pre-execution comparison view leaked {name} (escaped)"
    assert [trial["state"] for trial in view["trials"]] == ["RESERVED"] * 6
    assert all(set(workload) == {"id", "ordinal", "request_batch_hash", "request_count"} for workload in view["workloads"])
    assert view["eligible"] is False and "no winner" in view["eligibility_reason"].lower()
    assert all(trial["metrics"] is None for trial in view["trials"])


def test_the_compare_station_shows_all_six_slots_without_a_winner(session):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    view = _wait_comparison(session, created.json()["id"])
    assert view["state"] == "FINALIZED"
    assert len(view["trials"]) == 6
    for trial in view["trials"]:
        assert trial["state"] == "COMPLETE"
        assert trial["artifact_version_id"] in (candidate_a["id"], candidate_b["id"])
        assert trial["run_id"] is not None and trial["evidence_mode"] == "TRUSTED_LOCAL"
        assert trial["request_count"] == 2
        assert len(trial["outputs"]) == 2
        assert {entry["request_ordinal"] for entry in trial["outputs"]} == {1, 2}
        assert trial["missing_evidence"] == []
        assert trial["metrics"] is None
    by_pair = {pair: [t for t in view["trials"] if t["pair_ordinal"] == pair] for pair in (1, 2, 3)}
    assert all(len(entries) == 2 for entries in by_pair.values())
    assert {pair: len(entries[0]["task_assessments"]) for pair, entries in by_pair.items()} == {
        1: 6,  # two collection requests, three declared tasks each
        2: 5,  # one collection request and one two-task facts request
        3: 5,
    }
    # The outcome reports candidate eligibility separately and selects neither.
    outcome = view["outcome"]
    assert outcome["status"] == "COMPLETE"
    assert outcome["shared_public_denominator_requests"] == 6
    assert [item["public_denominator_requests"] for item in outcome["candidate_metrics"]] == [6, 6]
    assert [item["protected_denominator"] for item in outcome["candidate_metrics"]] == [3, 3]
    assert all(item["protected_missing"] == 0 for item in outcome["candidate_metrics"])
    assert all(item["cost_minor_units"] is None for item in outcome["candidate_metrics"])
    assert view["eligible"] == any(item["eligible"] for item in outcome["eligibility"])
    assert "no winner" in view["eligibility_reason"].lower()
    assert "winner" not in json.dumps(view["trials"], default=str).lower()
    # The candidate difference is visible per assessed request, not in a score.
    optional = {
        trial["candidate_label"]: [
            entry["outcome"] for entry in trial["task_assessments"] if entry["task_id"] == "price"
        ]
        for trial in view["trials"] if trial["pair_ordinal"] == 1
    }
    assert optional["A"] == ["USEFUL_COMPLETION", "USEFUL_COMPLETION"]
    assert optional["B"] == ["MISSING_OUTPUT", "MISSING_OUTPUT"]


def test_every_claim_defining_context_field_blocks_a_stale_outcome(session):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    experiment_id = created.json()["id"]
    assert _wait_comparison(session, experiment_id)["outcome"]["status"] == "COMPLETE"
    conn = db.connect(session.db_file)
    try:
        experiment = repo.get_experiment(conn, experiment_id)
        row = conn.execute("SELECT * FROM execution_contexts WHERE id = ?",
                           (experiment.context_id,)).fetchone()
        condition = json.loads(row["condition_json"])
        condition["public_label"] = "tampered condition"
        workloads = json.loads(row["workloads_json"])
        workloads[0]["request_count"] += 1
        state = json.loads(row["starting_business_state_json"])
        state["ledger_event_count"] += 1
        settings = json.loads(row["service_model_settings_json"])
        settings["temperature"] = 1
        limits = json.loads(row["resource_limits_json"])
        limits["deadline_s"] += 1
        changes = {
            "mission_bytes": row["mission_bytes"] + b" ",
            "mission_hash": "0" * 64,
            "public_data_bytes": row["public_data_bytes"] + b" ",
            "public_data_hash": "0" * 64,
            "starting_business_state_json": json.dumps(state),
            "starting_business_state_hash": "0" * 64,
            "requirement_set_id": "tampered-rubric",
            "requirement_set_hash": "0" * 64,
            "visible_check_set_hash": "0" * 64,
            "condition_json": json.dumps(condition),
            "workloads_json": json.dumps(workloads),
            "evaluator_version": "tampered-evaluator",
            "reducer_version": "tampered-reducer",
            "executor_class": "ISOLATED_LIVE",
            "harness_hash": "0" * 64,
            "image_ref": "tampered-image",
            "service_model": "tampered-model",
            "service_model_settings_json": json.dumps(settings),
            "resource_limits_json": json.dumps(limits),
            "protected_reservation_id": None,
            "content_hash": "0" * 64,
        }
        for column, altered in changes.items():
            conn.execute(f"UPDATE execution_contexts SET {column} = ? WHERE id = ?",
                         (altered, experiment.context_id))
            conn.commit()
            response = session.client.get(f"/api/experiments/{experiment_id}")
            assert response.status_code == 200, (column, response.text)
            result = response.json()["outcome"]
            assert result["status"] == "NOT_COMPARABLE", column
            assert all(not item["eligible"] for item in result["eligibility"]), column
            conn.execute(f"UPDATE execution_contexts SET {column} = ? WHERE id = ?",
                         (row[column], experiment.context_id))
            conn.commit()
            assert session.client.get(f"/api/experiments/{experiment_id}").json()["outcome"]["status"] == "COMPLETE", column
    finally:
        conn.close()


def test_the_investigate_station_projects_a_comparison_only_as_a_comparison(session, diagnostic):
    """R1: `latest_diagnostic` carries the shift's latest diagnostic only, so the
    diagnostic panel can never assert a comparison's candidate eligibility while
    `latest_experiment` still seeds the Compare station."""
    candidate_a = _freeze_candidate(session, "A")
    candidate_b = _freeze_candidate(session, "B")
    created = _create_comparison(session, candidate_a, candidate_b,
                                 diagnostic["investigation"], key="cmp-r1")
    assert created.status_code == 202, created.text
    comparison = _wait_comparison(session, created.json()["id"])
    assert comparison["state"] == "FINALIZED", comparison["state"]
    assert comparison["outcome"]["status"] == "COMPLETE"
    assert comparison["eligible"] is True, "this repair premise needs an eligible comparison"

    response = session.client.get(f"/api/shifts/{session.shift_id}/investigations")
    assert response.status_code == 200, response.text
    view = response.json()
    assert view["latest_experiment"]["kind"] == "QUALIFYING_COMPARISON"
    assert view["latest_experiment"]["eligible"] is True
    latest = view["latest_diagnostic"]
    assert latest is not None, "a completed diagnostic no longer reaches the panel"
    assert latest["id"] == diagnostic["experiment_id"]
    assert latest["kind"] == "DIAGNOSTIC"
    assert latest["eligible"] is False


def _recompute_frozen_context_hash(conn, context_id: str) -> str:
    """Recompute the stored frozen context hash over an already-tampered row.

    A named guard whose input also feeds `_frozen_comparison_context_hash` can
    only be isolated by recomputing the stored hash, so the frozen context check
    stays silent and the named guard reports the drift itself.
    """
    context = repo.get_execution_context(conn, context_id)
    bindings = orchestrator._reserved_protected_bindings(
        conn, context.protected_reservation_id
    )
    return orchestrator._frozen_comparison_context_hash(context, bindings)


def test_each_named_readback_drift_guard_reports_its_own_field(session):
    """R4: every named guard in `_comparison_outcome` reports its own drift field.

    The twenty-column context test asserts only the resulting status, so a guard
    whose tamper is also caught by the recomputed frozen context hash can be
    deleted unnoticed. Each tamper below is the smallest one that makes the named
    guard the reporter of its own field, and the assertion names that field, so
    deleting the guard fails this test even where a sibling guard still blocks the
    verdict. Measured co-firing, which is expected rather than a defect: a tamper
    of `public_data_bytes` also trips `condition`, because that guard requires the
    condition bytes to equal the public bytes; and every tamper that recomputes
    `execution_contexts.content_hash` also trips `assessment_context` and
    `experiment_schedule`, because both pin that stored value. `experiment_schedule`,
    `candidate_A` and `run_binding` are isolated with no sibling.
    """
    candidate_a, candidate_b, investigation = _comparison_session(session)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    experiment_id = created.json()["id"]
    assert _wait_comparison(session, experiment_id)["outcome"]["status"] == "COMPLETE"
    conn = db.connect(session.db_file)
    try:
        experiment = repo.get_experiment(conn, experiment_id)
        context_id = experiment.context_id
        context_row = conn.execute("SELECT * FROM execution_contexts WHERE id = ?",
                                   (context_id,)).fetchone()
        first_run_id = repo.list_trial_slots(conn, experiment_id)[0].run_id
        reported: dict[str, list[str]] = {}

        def probe(guard: str, tamper, undo) -> None:
            tamper()
            response = session.client.get(f"/api/experiments/{experiment_id}")
            assert response.status_code == 200, (guard, response.text)
            outcome = response.json()["outcome"]
            reported[guard] = sorted(outcome["drift_fields"])
            assert outcome["status"] == "NOT_COMPARABLE", (guard, reported[guard])
            assert guard in outcome["drift_fields"], (guard, reported[guard])
            assert all(not item["eligible"] for item in outcome["eligibility"]), guard
            undo()
            conn.commit()
            assert session.client.get(f"/api/experiments/{experiment_id}").json()[
                "outcome"]["status"] == "COMPLETE", (guard, "tamper was not reverted")

        def context_column(column: str, value, guard: str, *, recompute: bool = False) -> None:
            def tamper() -> None:
                conn.execute(f"UPDATE execution_contexts SET {column} = ? WHERE id = ?",
                             (value, context_id))
                if recompute:
                    conn.execute("UPDATE execution_contexts SET content_hash = ? WHERE id = ?",
                                 (_recompute_frozen_context_hash(conn, context_id), context_id))
                conn.commit()

            def undo() -> None:
                conn.execute(f"UPDATE execution_contexts SET {column} = ? WHERE id = ?",
                             (context_row[column], context_id))
                conn.execute("UPDATE execution_contexts SET content_hash = ? WHERE id = ?",
                             (context_row["content_hash"], context_id))

            probe(guard, tamper, undo)

        def other_column(table: str, column: str, key_column: str, key, value,
                         guard: str) -> None:
            original = conn.execute(
                f"SELECT * FROM {table} WHERE {key_column} = ?", (key,)
            ).fetchone()

            def tamper() -> None:
                conn.execute(f"UPDATE {table} SET {column} = ? WHERE {key_column} = ?",
                             (value, key))
                conn.commit()

            def undo() -> None:
                conn.execute(f"UPDATE {table} SET {column} = ? WHERE {key_column} = ?",
                             (original[column], key))

            probe(guard, tamper, undo)

        condition = json.loads(context_row["condition_json"])
        condition["exact_bytes_base64"] = base64.b64encode(b"{}").decode("ascii")
        workloads = json.loads(context_row["workloads_json"])
        workloads[0]["request_batch_bytes_base64"] = base64.b64encode(b"[]").decode("ascii")

        context_column("public_data_bytes", context_row["public_data_bytes"] + b" ",
                       "public_data_bytes_hash")
        context_column("condition_json", json.dumps(condition), "condition", recompute=True)
        context_column("visible_check_set_hash", "0" * 64, "visible_check_set",
                       recompute=True)
        context_column("workloads_json", json.dumps(workloads),
                       f"workload_{workloads[0]['ordinal']}", recompute=True)
        context_column("content_hash", "0" * 64, "assessment_context")
        other_column("experiments", "declared_treatment", "id", experiment_id,
                     "tampered treatment", "experiment_schedule")
        other_column("artifact_versions", "content_hash", "id", candidate_a["id"],
                     "0" * 64, "candidate_A")
        other_column("runs", "experiment_id", "id", first_run_id,
                     "tampered-experiment", "run_binding")
    finally:
        conn.close()


def test_public_and_protected_assessment_tampering_blocks_outcome(session):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    experiment_id = created.json()["id"]
    assert _wait_comparison(session, experiment_id)["outcome"]["status"] == "COMPLETE"
    conn = db.connect(session.db_file)
    try:
        slot = repo.list_trial_slots(conn, experiment_id)[0]
        for request_ordinal in (1, slot.executed_request_count):
            row = conn.execute(
                "SELECT id, mandatory_pass FROM task_assessments "
                "WHERE run_id = ? AND request_ordinal = ? LIMIT 1",
                (slot.run_id, request_ordinal),
            ).fetchone()
            assert row is not None
            conn.execute(
                "UPDATE task_assessments SET mandatory_pass = ? WHERE id = ?",
                (1 - row["mandatory_pass"], row["id"]),
            )
            conn.commit()
            outcome = session.client.get(f"/api/experiments/{experiment_id}").json()["outcome"]
            assert outcome["status"] == "NOT_COMPARABLE", request_ordinal
            assert all(not item["eligible"] for item in outcome["eligibility"])
            conn.execute(
                "UPDATE task_assessments SET mandatory_pass = ? WHERE id = ?",
                (row["mandatory_pass"], row["id"]),
            )
            conn.commit()
            assert session.client.get(f"/api/experiments/{experiment_id}").json()[
                "outcome"
            ]["status"] == "COMPLETE"
    finally:
        conn.close()


def test_recorded_inspection_or_wrong_run_mode_cannot_qualify_on_readback(session):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    experiment_id = created.json()["id"]
    assert _wait_comparison(session, experiment_id)["outcome"]["status"] == "COMPLETE"
    conn = db.connect(session.db_file)
    try:
        slot = repo.list_trial_slots(conn, experiment_id)[0]
        row = conn.execute(
            "SELECT adapter, evidence_mode, purpose FROM runs WHERE id = ?", (slot.run_id,)
        ).fetchone()
        for column, altered in (
            ("adapter", "recorded"),
            ("evidence_mode", "RECORDED_INSPECTION"),
            ("purpose", "OPERATION"),
        ):
            conn.execute(f"UPDATE runs SET {column} = ? WHERE id = ?", (altered, slot.run_id))
            conn.commit()
            response = session.client.get(f"/api/experiments/{experiment_id}")
            assert response.status_code == 200, (column, response.text)
            outcome = response.json()["outcome"]
            assert outcome["status"] == "NOT_COMPARABLE", column
            assert "run_evidence_class" in outcome["drift_fields"], column
            assert all(not item["eligible"] for item in outcome["eligibility"]), column
            conn.execute(f"UPDATE runs SET {column} = ? WHERE id = ?",
                         (row[column], slot.run_id))
            conn.commit()
            assert session.client.get(f"/api/experiments/{experiment_id}").json()[
                "outcome"
            ]["status"] == "COMPLETE", column
    finally:
        conn.close()


def test_persisted_protected_usage_stays_out_of_public_efficiency_and_route(session):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    experiment_id = created.json()["id"]
    assert _wait_comparison(session, experiment_id)["outcome"]["status"] == "COMPLETE"
    conn = db.connect(session.db_file)
    try:
        slot = repo.list_trial_slots(conn, experiment_id)[0]
        for ordinal, request_ordinal, kind, payload in (
            (1, 1, ObservationKind.INFERENCE_REQUEST, {}),
            (2, 1, ObservationKind.INFERENCE_RESULT,
             {"input_tokens": 7, "output_tokens": 9, "elapsed_ms": 11}),
            (3, slot.executed_request_count, ObservationKind.INFERENCE_REQUEST, {}),
            (4, slot.executed_request_count, ObservationKind.INFERENCE_RESULT,
             {"input_tokens": 973121, "output_tokens": 973122,
              "elapsed_ms": 973123, "protected_marker": "PRIVATE_USAGE_MARKER_S16"}),
        ):
            repo.insert_observation(conn, ExecutionObservation(
                id=f"{slot.run_id}-usage-boundary-{ordinal}", run_id=slot.run_id,
                request_ordinal=request_ordinal, ordinal=ordinal, kind=kind,
                public_payload_json=payload, raw_payload_ref="",
                measured_at=datetime.now(timezone.utc),
            ))
        conn.commit()
        assert len(repo.list_observations(conn, slot.run_id)) == 4
    finally:
        conn.close()
    response = session.client.get(f"/api/experiments/{experiment_id}")
    assert response.status_code == 200, response.text
    assert "PRIVATE_USAGE_MARKER_S16" not in response.text
    metrics = response.json()["outcome"]["candidate_metrics"][0]
    assert (metrics["service_calls"], metrics["input_tokens"],
            metrics["output_tokens"], metrics["service_latency_ms"]) == (1, 7, 9, 11)


def test_retiring_a_compromised_comparison_keeps_evidence_and_blocks_reuse(session):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    experiment_id = created.json()["id"]
    before = _wait_comparison(session, experiment_id)
    assert before["outcome"]["status"] == "COMPLETE"
    conn = db.connect(session.db_file)
    try:
        reservation = repo.get_exposure_reservation_for_experiment(conn, experiment_id)
        slots = repo.list_trial_slots(conn, experiment_id)
        captures = {slot.id: [(out.request_ordinal, out.body)
                              for out in repo.list_outputs(conn, slot.run_id)] for slot in slots}
        ledger_before = tuple(repo.list_ledger_events(conn, config.BOOKSHOP_SLUG))
        orchestrator.retire_comparison_exposure(conn, reservation.id)
        orchestrator.retire_comparison_exposure(conn, reservation.id)
        assert repo.get_exposure_reservation(conn, reservation.id).state == "INVALIDATED"
        assert all(item.state.value == "invalidated"
                   for item in repo.list_exposure_items(conn, reservation.id))
        assert {slot.id: [(out.request_ordinal, out.body)
                          for out in repo.list_outputs(conn, slot.run_id)] for slot in slots} == captures
        assert tuple(repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)) == ledger_before
    finally:
        conn.close()
    after = session.client.get(f"/api/experiments/{experiment_id}").json()
    assert after["state"] == "INVALIDATED"
    assert after["outcome"]["status"] == "NOT_COMPARABLE"
    assert all(not item["eligible"] for item in after["outcome"]["eligibility"])
    assert [item["protected_passed"] for item in after["outcome"]["candidate_metrics"]] == [
        item["protected_passed"] for item in before["outcome"]["candidate_metrics"]
    ]
    orchestrator.execute_comparison_task(str(session.db_file), experiment_id)
    assert session.client.get(f"/api/experiments/{experiment_id}").json() == after


def test_a_repeated_comparison_key_returns_the_original_reservation(session):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    first = _create_comparison(session, candidate_a, candidate_b, investigation, key="cmp-repeat")
    assert first.status_code == 202, first.text
    _wait_comparison(session, first.json()["id"])
    conn = db.connect(session.db_file)
    try:
        reserved = _counts(conn)
    finally:
        conn.close()
    second = _create_comparison(session, candidate_a, candidate_b, investigation, key="cmp-repeat")
    assert second.status_code == 202, second.text
    assert second.json()["id"] == first.json()["id"]
    conn = db.connect(session.db_file)
    try:
        assert _counts(conn) == reserved
    finally:
        conn.close()
    changed = _create_comparison(
        session, candidate_a, candidate_b, investigation, key="cmp-repeat",
        treatment="a different declared treatment for the same key",
    )
    assert changed.status_code == 409, changed.text
    other = _create_comparison(session, candidate_a, candidate_b, investigation, key="cmp-other")
    assert other.status_code == 409, other.text
    assert "already reserved its qualifying comparison" in other.json()["detail"]


def test_the_database_constraints_reject_duplicate_keys_not_just_the_controller(session):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    created = _create_comparison(session, candidate_a, candidate_b, investigation)
    assert created.status_code == 202, created.text
    _wait_comparison(session, created.json()["id"])
    conn = db.connect(session.db_file)
    try:
        row = conn.execute("SELECT * FROM experiments WHERE id = ?", (created.json()["id"],)).fetchone()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO experiments (id, shift_id, kind, investigation_id, candidates_json, "
                "declared_treatment, context_id, content_hash, trial_count_per_candidate, state, "
                "client_request_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("experiment-duplicate-key", row["shift_id"], row["kind"], row["investigation_id"],
                 row["candidates_json"], row["declared_treatment"], row["context_id"], row["content_hash"],
                 row["trial_count_per_candidate"], "PLANNED", row["client_request_id"], row["created_at"]),
            )
        conn.rollback()
        item = conn.execute("SELECT * FROM exposure_items LIMIT 1").fetchone()
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO exposure_items (id, reservation_id, engagement_slug, family, cycle, "
                "variant_ref, pair_ordinal, state, drawn_at) VALUES (?, ?, ?, ?, ?, ?, 1, 'active', ?)",
                ("item-duplicate", item["reservation_id"], item["engagement_slug"], item["family"],
                 item["cycle"], item["variant_ref"], item["drawn_at"]),
            )
        conn.rollback()
        # Each trial-slot key is proved on its own: a probe row that duplicates
        # only the pair key must fail, and a second that duplicates only the
        # execution ordinal must fail, or one constraint would hide the other.
        conn.execute(
            "INSERT INTO experiments (id, shift_id, kind, investigation_id, candidates_json, "
            "declared_treatment, context_id, content_hash, trial_count_per_candidate, state, "
            "client_request_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("experiment-slot-probe", row["shift_id"], row["kind"], row["investigation_id"],
             row["candidates_json"], row["declared_treatment"], row["context_id"], row["content_hash"],
             row["trial_count_per_candidate"], "PLANNED", "probe-slot-key", row["created_at"]),
        )
        holder = (
            "INSERT INTO trial_slots (id, experiment_id, pair_ordinal, execution_ordinal, "
            "candidate_label, artifact_version_id, workload_id, request_batch_hash, request_count, "
            "executed_request_count, protected_variant_refs_json, run_id, state) VALUES (?, 'experiment-slot-probe', ?, ?, ?, "
            "?, 'workload-01', ?, 2, 3, '[]', NULL, 'RESERVED')"
        )
        conn.execute(holder, ("probe-slot-1", 1, 1, "A", candidate_a["id"], "0" * 64))
        conn.execute(holder, ("probe-slot-4", 2, 3, "A", candidate_a["id"], "0" * 64))
        # A constraint failure rolls back the statement, not the transaction, so
        # the two probe rows stay visible to the second, isolated check below.
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(holder, ("probe-slot-2", 1, 2, "A", candidate_a["id"], "0" * 64))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(holder, ("probe-slot-3", 2, 3, "B", candidate_a["id"], "0" * 64))
        conn.rollback()
    finally:
        conn.close()


def test_a_comparison_requires_two_distinct_reviewed_candidates_and_an_owned_entry(session):
    starter = _freeze_starter(session)
    candidate_a, candidate_b, investigation = _comparison_session(session)

    def attempt(key: str, first: str, second: str, investigation_id: str | None):
        return session.client.post(
            f"/api/shifts/{session.shift_id}/experiments",
            json={
                "kind": "QUALIFYING_COMPARISON",
                "investigation_id": investigation_id,
                "candidate_a_version_id": first,
                "candidate_b_version_id": second,
                "declared_treatment": TREATMENT,
                "client_request_id": key,
            },
        )

    same = attempt("cmp-same", candidate_a["id"], candidate_a["id"], investigation["id"])
    assert same.status_code == 409, same.text
    assert "two distinct candidate versions" in same.json()["detail"]
    unpinned = attempt("cmp-unpinned", starter["id"], candidate_a["id"], investigation["id"])
    assert unpinned.status_code == 409, unpinned.text
    assert "only the two pinned reviewed candidates" in unpinned.json()["detail"]
    null_entry = attempt("cmp-null", candidate_a["id"], candidate_b["id"], None)
    assert null_entry.status_code == 409, null_entry.text
    assert "requires an owned investigation" in null_entry.json()["detail"]
    blank_treatment = session.client.post(
        f"/api/shifts/{session.shift_id}/experiments",
        json={
            "kind": "QUALIFYING_COMPARISON",
            "investigation_id": investigation["id"],
            "candidate_a_version_id": candidate_a["id"],
            "candidate_b_version_id": candidate_b["id"],
            "declared_treatment": "   ",
            "client_request_id": "cmp-blank",
        },
    )
    assert blank_treatment.status_code == 422, blank_treatment.text
    conn = db.connect(session.db_file)
    try:
        assert repo.count_experiments_for_shift(
            conn, session.shift_id, ExperimentKind.QUALIFYING_COMPARISON
        ) == 0
        assert repo.count_exposure_reservations(conn) == 0
    finally:
        conn.close()

    # A diagnostic and a comparison never share a slot, and the comparison
    # cannot cite a diagnostic run as its trial.
    diagnostic = _create_experiment(session, starter["id"], investigation["id"], key="exp-before-cmp")
    assert diagnostic.status_code == 202, diagnostic.text
    diagnostic_view = session.client.get(f"/api/experiments/{diagnostic.json()['id']}").json()
    created = _create_comparison(session, candidate_a, candidate_b, investigation, key="cmp-after-diagnostic")
    assert created.status_code == 202, created.text
    comparison_view = _wait_comparison(session, created.json()["id"])
    diagnostic_runs = {trial["run_id"] for trial in diagnostic_view["trials"]}
    assert diagnostic_runs.isdisjoint({trial["run_id"] for trial in comparison_view["trials"]})
    assert comparison_view["investigation_id"] == investigation["id"]
    unchanged = session.client.get(f"/api/experiments/{diagnostic.json()['id']}").json()
    assert unchanged == diagnostic_view, "the comparison rewrote the diagnostic's own evidence"

    # A comparison in another shift cannot cite this shift's investigation.
    closed = session.client.post(f"/api/shifts/{session.shift_id}/close")
    assert closed.status_code == 200, closed.text
    opened = session.client.post("/api/engagements/bookshop/shifts")
    assert opened.status_code == 201, opened.text
    second = BookshopShift(session.client, session.db_file, session.monkeypatch)
    second.shift_id = opened.json()["id"]
    elsewhere = session.client.post(
        f"/api/shifts/{second.shift_id}/experiments",
        json={
            "kind": "QUALIFYING_COMPARISON",
            "investigation_id": investigation["id"],
            "candidate_a_version_id": candidate_a["id"],
            "candidate_b_version_id": candidate_b["id"],
            "declared_treatment": TREATMENT,
            "client_request_id": "cmp-elsewhere",
        },
    )
    assert elsewhere.status_code == 409, elsewhere.text
    assert "owned by this shift" in elsewhere.json()["detail"]


# --- S15 protected phase, approved obligations 50 to 54 --------------------


def test_slot_runs_public_phase_then_protected_phase_in_frozen_order(session, monkeypatch):
    """Test 50: one run identity, two fresh executor operations, exact frozen bytes."""
    from shiftwork.executor.local_process import LocalProcessAdapter

    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, _ = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    seen = []

    class RecordingAdapter(LocalProcessAdapter):
        async def execute(self, request):
            phase = "protected" if request.single_request_ordinal is not None else "public"
            root = Path(request.shop_snapshot_ref).parent
            assert not (root / "phase-sentinel").exists()
            seen.append((phase, root, Path(request.shop_snapshot_ref).read_bytes(),
                         request.request_batch_bytes, request.single_request_ordinal))
            (root / "phase-sentinel").write_text("public phase only")
            return await super().execute(request)

    monkeypatch.setattr(orchestrator, "LocalProcessAdapter", RecordingAdapter)
    orchestrator.execute_comparison_task(str(session.db_file), experiment.id)
    conn = db.connect(session.db_file)
    try:
        context = repo.get_execution_context(conn, experiment.context_id)
        slots = repo.list_trial_slots(conn, experiment.id)
        cases = {item.pair_ordinal: item.case for item in
                 sealed_store.load_reserved_comparison_cases(
                     conn, context.protected_reservation_id)}
        states = {pair: sealed_store.load_reserved_protected_state(
            conn, context.protected_reservation_id, pair) for pair in (1, 2, 3)}
        view = orchestrator.experiment_view(conn, experiment.id)
        assert view["state"] == "FINALIZED"
        assert len(seen) == 12
        for index, slot in enumerate(slots):
            public, protected = seen[2 * index:2 * index + 2]
            assert (public[0], protected[0]) == ("public", "protected")
            assert public[1] != protected[1], "a slot reused the public workspace"
            assert public[2] == config.PIVOT_COMPARE_STATE.read_bytes()
            assert protected[2] == states[slot.pair_ordinal]
            assert public[3] == base64.b64decode(context.workloads[slot.pair_ordinal - 1].request_batch_bytes_base64)
            assert protected[3] == task_contract.protected_request_bytes(
                cases[slot.pair_ordinal].stimulus.request)
            assert protected[4] == slot.executed_request_count == slot.request_count + 1
            assert [item.request_ordinal for item in repo.list_outputs(conn, slot.run_id)] == [1, 2, 3]
            assert [item["request_ordinal"] for item in view["trials"][index]["outputs"]] == [1, 2]
    finally:
        conn.close()

    row = cases[1].stimulus.request
    raw = task_contract.protected_request_bytes(row)
    ref = executor_base.BatchRef(path_ref="sealed:protected",
                                 content_hash=canonical.content_hash(base64.b64encode(raw).decode("ascii")))
    assert executor_base.load_single_request(ref, raw, 3).body == raw
    with pytest.raises(ValueError, match="consecutive from 1"):
        executor_base.load_batch(ref, raw)
    with pytest.raises(ValueError, match="exactly one"):
        doubled = raw + raw
        executor_base.load_single_request(executor_base.BatchRef(
            path_ref="sealed:protected", content_hash=canonical.content_hash(
                base64.b64encode(doubled).decode("ascii"))), doubled, 3)
    with pytest.raises(ValueError, match="ordinal mismatch"):
        executor_base.load_single_request(ref, raw, 4)
    with pytest.raises(ValueError, match="missing or mismatched"):
        executor_base.load_single_request(ref, None, 3)


def test_protected_variant_is_bound_and_snapshotted_before_any_result(session):
    """Test 51: restricted bytes and context hash survive exact readback."""
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, view = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    conn = db.connect(session.db_file)
    try:
        context = repo.get_execution_context(conn, experiment.context_id)
        bindings = orchestrator._reserved_protected_bindings(conn, context.protected_reservation_id)
        rows = repo.list_protected_case_snapshots(conn, context.protected_reservation_id)
        assert len(rows) == len(bindings) == 3
        assert orchestrator._frozen_comparison_context_hash(context, bindings) == context.content_hash
        for row, binding in zip(rows, bindings, strict=True):
            assert hashlib.sha256(row["payload_json"].encode()).hexdigest() == row["payload_sha256"]
            assert hashlib.sha256(row["resolved_state_bytes"]).hexdigest() == binding.protected_state_hash
            assert row["variant_ref"] == binding.variant_ref
            assert binding.request_ordinal == 3
        assert all(trial["outputs"] == [] for trial in view["trials"])
    finally:
        conn.close()
    first = sealed_store.load_family("task_completion").cases[0].stimulus
    assert hashlib.sha256(task_contract.protected_request_bytes(first.request)).hexdigest() == (
        "a6b87de50af1affe327d5a8fa0e2c82d862df20c7fba86c1ee519dec62a6caaa")
    assert hashlib.sha256(task_contract.resolve_protected_state(
        config.PIVOT_COMPARE_STATE.read_bytes(), first.state_delta)).hexdigest() == (
        "765834743b0445295d4e1df66b9952a2ab1b5aca92dd2cdcad14ea6cfde902f4")
    decomposed = first.request.model_copy(update={"text": "Cafe\u0301 collection"})
    encoded = task_contract.protected_request_bytes(decomposed)
    assert b"Cafe\xcc\x81" not in encoded and b"Caf\xc3\xa9" in encoded
    assert canonical.content_hash(decomposed.model_dump(mode="json")) == canonical.content_hash(
        json.loads(encoded))


@pytest.mark.parametrize("collision", ["entity", "record"])
def test_protected_delta_collision_is_rejected_before_exposure(session, monkeypatch, collision):
    candidate_a, candidate_b, investigation = _comparison_session(session)
    cases = list(sealed_store.load_family("task_completion").cases)
    stimulus = cases[0].stimulus
    delta = stimulus.state_delta
    if collision == "entity":
        delta = delta.model_copy(update={"add_entities": {
            "book:salt-roads:paperback": task_contract.ProtectedEntityDelta(
                title="Changed", edition="paperback", genre="coastal_travel")}})
    else:
        duplicate = task_contract.ProtectedRecordDelta(
            record_id="public:salt-roads:paperback:price", entity_ref="book:salt-roads:paperback",
            kind="price", value=1, record_age_ms=0, dependency="catalog", currency="GBP")
        delta = delta.model_copy(update={"add_records": (duplicate,)})
        public_data = json.loads(config.PIVOT_COMPARE_STATE.read_bytes())
        public_data["records"].append(duplicate.model_dump(mode="json", exclude_none=True))
        assert task_contract.load_public_state_bytes(json.dumps(public_data).encode()), (
            "the public-state parser itself does not detect duplicate record ids")
    cases[0] = cases[0].model_copy(update={"stimulus": stimulus.model_copy(update={"state_delta": delta})})
    monkeypatch.setattr(sealed_store, "load_reviewed_comparison_family",
                        lambda _family: evaluator.SealedCaseSet(cases=tuple(cases)))
    conn = db.connect(session.db_file)
    try:
        before = _counts(conn)
    finally:
        conn.close()
    with pytest.raises(Exception, match="collides"):
        _reserve_comparison(session, candidate_a, candidate_b, investigation)
    conn = db.connect(session.db_file)
    try:
        assert _counts(conn) == before
    finally:
        conn.close()


def test_each_pair_shares_one_identical_protected_stimulus(session):
    """Test 52: each A/B pair uses one binding and no pair borrows another's."""
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, _ = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    conn = db.connect(session.db_file)
    try:
        context = repo.get_execution_context(conn, experiment.context_id)
        slots = repo.list_trial_slots(conn, experiment.id)
        bindings = orchestrator._reserved_protected_bindings(conn, context.protected_reservation_id)
        assert [binding.pair_ordinal for binding in bindings] == [1, 2, 3]
        assert len({binding.variant_ref for binding in bindings}) == 3
        assert len({binding.stimulus_hash for binding in bindings}) == 3
        for binding in bindings:
            pair_slots = [slot for slot in slots if slot.pair_ordinal == binding.pair_ordinal]
            assert {slot.candidate_label for slot in pair_slots} == {"A", "B"}
            assert all(slot.protected_variant_refs == (binding.variant_ref,) for slot in pair_slots)
            assert all(slot.executed_request_count == binding.request_ordinal == 3 for slot in pair_slots)
            resolved = sealed_store.load_reserved_protected_state(
                conn, context.protected_reservation_id, binding.pair_ordinal)
            assert hashlib.sha256(resolved).hexdigest() == binding.protected_state_hash
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE trial_slots SET protected_variant_refs_json = '[]' WHERE id = ?",
                         (slots[0].id,))
        conn.rollback()
    finally:
        conn.close()


def test_public_and_protected_counts_reconcile_without_merging(session):
    """Test 54: public six and protected three remain separate per candidate."""
    candidate_a, candidate_b, investigation = _comparison_session(session)
    experiment, before = _reserve_comparison(session, candidate_a, candidate_b, investigation)
    assert before["shared_public_denominator_requests"] == 6
    assert before["protected_denominator_requests_per_candidate"] == 3
    assert before["protected_counts"] is None
    assert all(trial["request_count"] == 2 and trial["protected_request_count"] == 1
               for trial in before["trials"])
    orchestrator.execute_comparison_task(str(session.db_file), experiment.id)
    conn = db.connect(session.db_file)
    try:
        after = orchestrator.experiment_view(conn, experiment.id)
        assert after["state"] == "FINALIZED"
        assert after["shared_public_denominator_requests"] == 6
        assert after["protected_denominator_requests_per_candidate"] == 3
        assert after["protected_counts"] == {
            "A": {"reserved": 3, "captured": 3, "missing": 0},
            "B": {"reserved": 3, "captured": 3, "missing": 0},
        }
        for trial in after["trials"]:
            assert len(trial["outputs"]) == trial["request_count"] == 2
            assert len(repo.list_outputs(conn, trial["run_id"])) == 3
    finally:
        conn.close()



def test_protected_content_and_captures_never_reach_public_surfaces(tmp_path, monkeypatch):
    """Test 53: short private values use source and ordinal checks, not global needles."""
    from fastapi.testclient import TestClient
    from shiftwork.app import create_app
    from shiftwork.executor import base as base
    from shiftwork.gateway.redaction import serialized_contains

    original_load = sealed_store.load_family
    original_cases = original_load("task_completion").cases
    captures = []
    public_views = []

    class DeterministicAdapter:
        name = "local_process"

        def __init__(self, **_kwargs):
            pass

        async def execute(self, request):
            if request.single_request_ordinal is None:
                batch = base.load_batch(request.request_batch, request.request_batch_bytes)
            else:
                batch = (base.load_single_request(request.request_batch,
                         request.request_batch_bytes, request.single_request_ordinal),)
            raw = []
            for stimulus in batch:
                parsed = json.loads(stimulus.body)
                body = json.dumps({"request_id": parsed["request_id"], "task_results": [],
                                   "evidence_refs": [], "uncertainty_codes": []},
                                  sort_keys=True).encode()
                if request.single_request_ordinal is not None:
                    body += b" protected-capture-marker"
                raw.append(base.RawCapture(request_ordinal=stimulus.ordinal, http_status=200,
                                           body=body, elapsed_ms=1, transport_error=None,
                                           log_ref="data:application/octet-stream;base64," +
                                           base64.b64encode(b"protected-log-marker").decode()
                                           if request.single_request_ordinal is not None else None))
            observations = ()
            if request.single_request_ordinal is not None:
                observations = (base.RawObservation(kind="INTERPRETATION",
                    public_payload={"request_ordinal": request.single_request_ordinal,
                                    "protected_trace": "protected-observation-marker"},
                    raw_payload={"protected_trace": "protected-observation-marker"}),)
            return base.RunResult(captures=tuple(raw), executor_ref=None, failure=None,
                                  wall_ms=1, observations=observations)

    monkeypatch.setattr(orchestrator, "LocalProcessAdapter", DeterministicAdapter)
    class DeterministicTokenAdapter(DeterministicAdapter):
        name = "tokenfactory"

    monkeypatch.setattr(orchestrator, "TokenFactoryAdapter", DeterministicTokenAdapter)
    for marker in (1, 2):
        cases = list(original_cases)
        first = cases[0]
        delta = first.stimulus.state_delta.model_copy(update={"add_records": (
            task_contract.ProtectedRecordDelta(
                record_id="x" if marker == 1 else "y",
                entity_ref="book:salt-roads:paperback", kind="stock", value=marker,
                record_age_ms=0, dependency="inventory"),)})
        stimulus = first.stimulus.model_copy(update={"state_delta": delta})
        cases[0] = first.model_copy(update={
            "stimulus": stimulus,
            "expected": {"aspect": "x" if marker == 1 else "y", "rule_ids": [],
                         "note": "x" if marker == 1 else "y"},
        })
        case_set = evaluator.SealedCaseSet(cases=tuple(cases))
        monkeypatch.setattr(sealed_store, "load_family",
                            lambda family, current=case_set: current if family == "task_completion"
                            else original_load(family))
        monkeypatch.setattr(sealed_store, "load_reviewed_comparison_family",
                            lambda _family, current=case_set: current)
        db_file = tmp_path / f"protected-{marker}.db"
        with TestClient(create_app(str(db_file))) as client:
            current = BookshopShift(client, db_file, monkeypatch)
            current.open()
            current.freeze()
            candidate_a, candidate_b, investigation = _comparison_session(current)
            experiment, before = _reserve_comparison(current, candidate_a, candidate_b, investigation)
            assert before["protected_counts"] is None
            before_route = client.get(f"/api/experiments/{experiment.id}")
            assert before_route.status_code == 200, before_route.text
            if marker == 2:
                conn = db.connect(db_file)
                try:
                    conn.execute("UPDATE runs SET adapter = 'tokenfactory' WHERE experiment_id = ?",
                                 (experiment.id,))
                    conn.commit()
                finally:
                    conn.close()
            conn = db.connect(db_file)
            try:
                first_slot = repo.list_trial_slots(conn, experiment.id)[0]
                orchestrator.execute_comparison_slot(conn, first_slot)
                during = orchestrator.experiment_view(conn, experiment.id)
                assert during["protected_counts"] is None
                assert [item["request_ordinal"] for item in during["trials"][0]["outputs"]] == [1, 2]
            finally:
                conn.close()
            orchestrator.execute_comparison_task(str(db_file), experiment.id)
            after_route = client.get(f"/api/experiments/{experiment.id}")
            assert after_route.status_code == 200, after_route.text
            after = after_route.json()
            assert after["state"] == "FINALIZED"
            run_id = after["trials"][0]["run_id"]
            outputs_route = client.get(f"/api/runs/{run_id}/outputs")
            checks_route = client.get(f"/api/runs/{run_id}/checks")
            board_route = client.get("/api/engagements/bookshop/board")
            station_route = client.get(f"/api/shifts/{current.shift_id}/investigations")
            ledger_route = client.get("/api/engagements/bookshop/ledger")
            error_route = client.get("/api/runs/absent/outputs")
            bootstrap_route = client.get("/")
            assert all(result.status_code == 200 for result in (
                outputs_route, checks_route, board_route, station_route, ledger_route,
                bootstrap_route)), [result.status_code for result in (
                outputs_route, checks_route, board_route, station_route, ledger_route,
                bootstrap_route)]
            assert error_route.status_code == 404
            assert [output["request_ordinal"] for output in outputs_route.json()] == [1, 2]
            assert [output["request_ordinal"] for output in after["trials"][0]["outputs"]] == [1, 2]
            assert all(item["request_ordinal"] <= 2 for item in after["trials"][0]["task_assessments"])
            assert all(item["public_payload_json"].get("request_ordinal", 1) <= 2
                       for item in after["trials"][0]["observations"])
            surfaces = (before_route.json(), after, outputs_route.json(), checks_route.json(),
                        board_route.json(), station_route.json(), ledger_route.json(),
                        error_route.json(), bootstrap_route.text)
            conn = db.connect(db_file)
            try:
                stored = repo.list_outputs(conn, run_id)
                assert [item.request_ordinal for item in stored] == [1, 2, 3]
                stored_observations = repo.list_observations(conn, run_id)
                assert any(item.request_ordinal == 3 for item in stored_observations), (
                    "the protected capture produced no stored observation to filter")
                assert repo.get_run_snapshot_bytes(conn, run_id) == config.PIVOT_COMPARE_STATE.read_bytes()
                assert b"protected-capture-marker" in stored[2].body
                assert "protected-log-marker" in base64.b64decode(stored[2].log_ref.split(",", 1)[1]).decode()
                binding = orchestrator._reserved_protected_bindings(conn,
                    repo.get_execution_context(conn, experiment.context_id).protected_reservation_id)[0]
                protected_state = sealed_store.load_reserved_protected_state(
                    conn, repo.get_execution_context(conn, experiment.context_id).protected_reservation_id, 1)
                baseline_shop = outputs_route.json()[0]
                assert baseline_shop["public_shop_record"] is not None
                assert baseline_shop["public_shop_record_ref"] == "public:salt-roads:paperback:stock"
                assert baseline_shop["public_shop_snapshot_hash"] == canonical.content_hash(
                    base64.b64encode(config.PIVOT_COMPARE_STATE.read_bytes()).decode("ascii"))
                with monkeypatch.context() as fault:
                    fault.setattr(orchestrator, "_snapshot_bytes_for_run", lambda _conn, _run: protected_state)
                    changed = orchestrator.output_evidence_for(conn, stored[0], repo.get_run(conn, run_id))
                    assert changed["public_shop_snapshot_hash"] != baseline_shop["public_shop_snapshot_hash"]
                with monkeypatch.context() as fault:
                    fault.setattr(orchestrator, "list_outputs", repo.list_outputs)
                    leaked_route = client.get(f"/api/runs/{run_id}/outputs")
                    assert leaked_route.status_code == 409, (
                        "the route scanner must reject a projected protected output")
                with monkeypatch.context() as fault:
                    leaky_log = stored[1].model_copy(update={
                        "log_ref": "data:application/octet-stream;base64," + base64.b64encode(
                            stimulus.request.text.encode("utf-8")).decode("ascii")})
                    fault.setattr(orchestrator, "list_outputs", lambda _conn, _run_id: [leaky_log])
                    leaked_log_route = client.get(f"/api/runs/{run_id}/outputs")
                    assert leaked_log_route.status_code == 409, (
                        "the route scanner must reject a public log carrying protected wording")
                needles = orchestrator._private_public_needles(conn)
                for needle in (stimulus.request.request_id, stimulus.request.text,
                               stimulus.state_delta.description, binding.protected_state_hash):
                    assert needle in needles
                    assert all(not serialized_contains(surface, needle) for surface in surfaces)
                    assert serialized_contains({"probe": needle}, needle)
                    assert serialized_contains({"probe": json.dumps(needle)[1:-1]}, needle)
                    assert serialized_contains({"probe": needle.replace("\\", "/")}, needle)
                for forbidden in ("protected-capture-marker", "protected-log-marker",
                                  "protected-observation-marker"):
                    assert all(not serialized_contains(surface, forbidden) for surface in surfaces)
                assert not any(len(needle) < 8 for needle in needles)
                assert not any(needle in ("x", "y", "1", "2") for needle in needles)
                assert not serialized_contains({"pair_ordinal": 1}, "private-nonexistent-marker")
                assert serialized_contains({"pair_ordinal": 1}, "1")
                orchestrator.assert_public_projection({"pair_ordinal": 1}, conn)
            finally:
                conn.close()
            public_views.append((after["trials"][0]["outputs"],
                                 after["trials"][0]["task_assessments"],
                                 [{k: row.get(k) for k in (
                                     "request_ordinal", "request_text", "body_base64",
                                     "public_shop_record", "public_shop_record_ref",
                                     "public_shop_snapshot_hash")}
                                  for row in outputs_route.json()]))
    assert public_views[0] == public_views[1], (
        "public request, output, task and shop evidence changed with a short protected value")
