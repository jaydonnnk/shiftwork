"""S43 per-shift mission binding (Gate 3 S2 clarification, 2026-10-23).

A new Bellwether engagement binds mission v2 and the task-plan starter only
under the tokenfactory executor; recorded and local executors keep mission v1
and its starter. Later shifts inherit their predecessor's mission, and an open
shift never changes with the executor configuration.

The operator reviewed and pinned mission v2 and its starter on 2026-10-24.
The unpinned-refusal test removes those two pins to prove the guard still holds.
"""

import base64
import hashlib

import pytest
from fastapi.testclient import TestClient

from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain import task_contract
from shiftwork.packs import registry
from shiftwork.store import db, repo

V1 = "fixtures/mission/bookshop_pivot_v1.json"
V2 = "fixtures/mission/bookshop_pivot_v2.json"
V2_STARTER = "fixtures/artifacts/bookshop/task_plan_starter_service.py"


def _sha(name):
    return hashlib.sha256((config.PACKAGE_DIR / name).read_bytes()).hexdigest()


@pytest.fixture()
def v2_unpinned(monkeypatch):
    packs = registry.registered_packs()
    bookshop = next(pack for pack in packs if pack.slug == "bookshop")
    unpinned = bookshop.model_copy(update={"reviewed_pins": tuple(
        pin for pin in bookshop.reviewed_pins if pin.path not in (V2, V2_STARTER))})
    monkeypatch.setattr(registry, "_PACKS", tuple(unpinned if p.slug == "bookshop" else p for p in packs))


@pytest.fixture()
def seeded(tmp_path):
    path = tmp_path / "binding.db"
    with TestClient(create_app(str(path), executor="recorded")):
        pass
    conn = db.connect(path)
    yield conn
    conn.close()


def _starter_files(conn, shift):
    selection = repo.get_latest_operating_selection(conn, shift.engagement_slug)
    return repo.get_version(conn, selection.selected_version_id).files


@pytest.mark.parametrize("executor_name,mission,starter", [
    ("tokenfactory", V2, V2_STARTER),
    ("recorded", V1, "fixtures/artifacts/bookshop/pivot_starter_failure_service.py"),
    ("local_process", V1, "fixtures/artifacts/bookshop/pivot_starter_failure_service.py"),
    (None, V1, "fixtures/artifacts/bookshop/pivot_starter_failure_service.py"),
])
def test_new_bellwether_shift_binds_v2_only_under_tokenfactory(seeded, executor_name,
                                                               mission, starter):
    shift = orchestrator.open_next_shift(seeded, "bookshop", executor_name=executor_name)
    assert repo.get_shift_mission_binding(seeded, shift.id) == (mission, _sha(mission))
    assert _starter_files(seeded, shift) == {
        "service.py": (config.PACKAGE_DIR / starter).read_text(encoding="utf-8")}
    context = orchestrator.freeze_diagnostic_context(seeded, shift)
    assert base64.b64decode(context.mission_bytes_base64) == (config.PACKAGE_DIR / mission).read_bytes()


def test_unpinned_v2_is_refused_and_leaves_no_shift(seeded, v2_unpinned):
    with pytest.raises(orchestrator.LifecycleError, match="awaits operator review"):
        orchestrator.open_next_shift(seeded, "bookshop", executor_name="tokenfactory")
    assert repo.get_latest_shift(seeded, "bookshop") is None


def test_open_shift_keeps_its_mission_when_the_executor_changes(tmp_path):
    path = tmp_path / "restart.db"
    with TestClient(create_app(str(path), executor="recorded")):
        pass
    conn = db.connect(path)
    try:
        shift = orchestrator.open_next_shift(conn, "bookshop", executor_name="tokenfactory")
    finally:
        conn.close()
    # A restart under the recorded executor reads the same binding.
    with TestClient(create_app(str(path), executor="recorded")):
        pass
    conn = db.connect(path)
    try:
        context = orchestrator.freeze_diagnostic_context(conn, shift)
        assert context.mission_hash == _sha(V2)
    finally:
        conn.close()


@pytest.mark.parametrize("first,later,expected", [("tokenfactory", "recorded", V2),
                                                  ("recorded", "tokenfactory", V1)])
def test_later_shift_inherits_its_predecessors_mission(seeded, first, later, expected):
    shift = orchestrator.open_next_shift(seeded, "bookshop", executor_name=first)
    orchestrator.close_shift(seeded, shift.id)
    following = orchestrator.open_next_shift(seeded, "bookshop", executor_name=later)
    assert following.seq == 2
    assert repo.get_shift_mission_binding(seeded, following.id)[0] == expected


def test_v2_starter_baseline_never_replays_the_v1_capture(seeded):
    shift = orchestrator.open_next_shift(seeded, "bookshop", executor_name="tokenfactory")
    with pytest.raises(orchestrator.LifecycleError, match="no reviewed capture"):
        orchestrator.start_run(seeded, shift.id, client_request_id="v2-baseline",
                               executor="tokenfactory")
    assert repo.count_runs_all(seeded) == 0


def test_task_vocabulary_and_tool_allowlist_come_only_from_frozen_mission(seeded):
    # Obligation 63, mission-derivation arm: the plan vocabulary and tool list a
    # bound v2 shift freezes are mission v2's, and a v1 shift freezes none.
    v2_shift = orchestrator.open_next_shift(seeded, "bookshop", executor_name="tokenfactory")
    frozen = task_contract.load_mission_bytes(base64.b64decode(
        orchestrator.freeze_diagnostic_context(seeded, v2_shift).mission_bytes_base64))
    reviewed = task_contract.load_mission(config.PACKAGE_DIR / V2)
    assert tuple(frozen.task_vocabulary) == ("collection", "alternative", "price", "stock")
    assert frozen.task_vocabulary == reviewed.task_vocabulary
    assert frozen.allowed_tool_vocabulary == reviewed.allowed_tool_vocabulary
    v1 = task_contract.load_mission(config.PACKAGE_DIR / V1)
    assert v1.task_vocabulary == {}


@pytest.mark.parametrize("name,vocabulary", [(V2, ("collection", "alternative", "price", "stock")), (V1, ())])
def test_service_adapter_takes_vocabulary_and_tools_from_the_frozen_mission(seeded, name, vocabulary):
    # Obligation 63, adapter arm: every isolated run builds its adapter here, so
    # the gateway policy can only carry the frozen mission's lists.
    mission = task_contract.load_mission(config.PACKAGE_DIR / name)
    run = type("Run", (), {"id": "run-0001"})()
    context = type("Context", (), {"service_model": "pinned-model", "resource_limits_json": {}})()
    adapter = orchestrator.service_adapter(run, mission, context)
    assert adapter.task_vocabulary == vocabulary
    assert adapter.allowed_tool_names == tuple(mission.allowed_tool_vocabulary)


def test_pinned_later_mission_must_keep_the_graded_requests(monkeypatch):
    original = task_contract.load_mission

    def drifted(path):
        mission = original(path)
        if str(path).endswith("bookshop_pivot_v2.json"):
            spec = mission.request_specs[0]
            return mission.model_copy(update={"request_specs": (
                spec.model_copy(update={"text": spec.text + " Also gift wrap it."}),)})
        return mission

    monkeypatch.setattr(task_contract, "load_mission", drifted)
    with pytest.raises(registry.PackUnavailable):
        orchestrator.admit_pack("bookshop")


def test_first_mission_version_must_be_the_pack_mission():
    bookshop = registry.resolve_pack("bookshop")
    with pytest.raises(ValueError, match="first mission version"):
        registry.EngagementPack.model_validate({**bookshop.model_dump(), "mission_versions": (V2, V1)})
