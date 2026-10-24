"""Frozen reasoning permission and selected-version inheritance, no network."""
import base64
import json
from types import SimpleNamespace

import pytest

from shiftwork import comparison_flow, config, experiments, orchestrator
from shiftwork.store import db, repo
from test_selection_operation import selected_migrated
from test_comparison_repetitions import comparison_session, reserve_raw

MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"


def credentials(monkeypatch, model=MODEL):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-only-token")
    monkeypatch.setenv("NEBIUS_PROJECT_ID", "test-only-project")
    monkeypatch.setattr(config, "SERVICE_MODEL", model)


@pytest.mark.parametrize("model,isolated,expected", [(MODEL, True, True), (MODEL, False, False), ("other-model", True, False)], ids=["nano", "local", "other-model"])
def test_new_diagnostic_context_freezes_only_the_admitted_permission(session, monkeypatch, model, isolated, expected):
    credentials(monkeypatch, model)
    with db.connect(session.db_file) as conn:
        shift = repo.get_shift(conn, session.shift_id)
        context = orchestrator.freeze_diagnostic_context(conn, shift, isolated=isolated)
        assert context.resource_limits_json.get("allow_reasoning_off", False) is expected, "diagnostic permission must be frozen only for isolated Nano"
        assert repo.get_execution_context(conn, context.id).content_hash == context.content_hash
        assert experiments.diagnostic_context_hash(context) == context.content_hash


@pytest.mark.parametrize("model,adapter,expected", [(MODEL, "tokenfactory", True), (MODEL, "local_process", False), ("other-model", "tokenfactory", False)], ids=["nano", "local", "other-model"])
def test_new_comparison_context_freezes_permission_before_execution(comparison_session, monkeypatch, model, adapter, expected):
    credentials(monkeypatch, model)
    experiment = reserve_raw(comparison_session, adapter=adapter)
    with db.connect(comparison_session[0].db_file) as conn:
        context = repo.get_execution_context(conn, experiment.context_id)
        assert context.resource_limits_json.get("allow_reasoning_off", False) is expected, "comparison permission must be frozen before results"
        bindings = comparison_flow._reserved_protected_bindings(conn, context.protected_reservation_id)
        assert comparison_flow._frozen_comparison_context_hash(context, bindings) == context.content_hash
        for slot in repo.list_trial_slots(conn, experiment.id):
            run = repo.get_run(conn, slot.run_id)
            if adapter == "tokenfactory":
                mission = orchestrator.task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))
                bound = orchestrator.service_adapter(run, mission, context)
                assert getattr(bound, "allow_reasoning_off", False) is expected, "both candidates and protected phases need their frozen permission"


@pytest.fixture
def selected_permission(request, monkeypatch):
    """Operator-authored policy fixture frozen before the local comparison runs."""
    permission = request.param
    original = comparison_flow._comparison_context_fields
    def fields(*args, **kwargs):
        result = original(*args, **kwargs)
        if permission is not False:
            result['resource_limits_json']['allow_reasoning_off'] = permission
        return result
    monkeypatch.setattr(comparison_flow, '_comparison_context_fields', fields)
    return request.getfixturevalue('selected_migrated'), permission


@pytest.mark.parametrize("selected_permission", [False, True, 1], indirect=True, ids=["historical-denial", "admitted", "nonboolean"])
def test_selected_operation_inherits_permission_and_exact_version(selected_permission, monkeypatch):
    retained, permission = selected_permission
    _, path, shift_id, selected, _, version, _ = retained
    credentials(monkeypatch)
    with db.connect(path) as conn:
        run = orchestrator.start_run(conn, shift_id, executor='tokenfactory', client_request_id='reasoning-operation')
        context = repo.get_execution_context(conn, run.context_id)
        assert context.resource_limits_json.get('allow_reasoning_off', False) is (permission is True), "operation must preserve the tested permission, including historical denial"
        assert run.artifact_version_id == version['id'] == selected['selected_version_id'], "permission cannot change the selected exact version"
        replay = orchestrator.start_run(conn, shift_id, executor='tokenfactory', client_request_id='reasoning-operation')
        assert replay.id == run.id and replay.context_id == context.id


def test_selected_operation_refuses_changed_permission_before_reservation(selected_migrated, monkeypatch):
    _, path, shift_id, _, _, _, compared = selected_migrated
    credentials(monkeypatch)
    with db.connect(path) as conn:
        source = repo.get_experiment(conn, compared['id']).context_id
        conn.execute("UPDATE execution_contexts SET resource_limits_json = json_set(resource_limits_json, '$.allow_reasoning_off', json('true')) WHERE id = ?", (source,))
        conn.commit()
        with pytest.raises(orchestrator.LifecycleError, match='selected reasoning permission changed'):
            orchestrator.start_run(conn, shift_id, executor='tokenfactory', client_request_id='reasoning-drift')


def test_selected_operation_refuses_a_rehashed_permission_upgrade(selected_migrated, monkeypatch):
    _, path, shift_id, _, _, _, compared = selected_migrated
    credentials(monkeypatch)
    with db.connect(path) as conn:
        experiment = repo.get_experiment(conn, compared['id'])
        source = repo.get_execution_context(conn, experiment.context_id)
        limits = {**source.resource_limits_json, 'allow_reasoning_off': True}
        changed = source.model_copy(update={'resource_limits_json': limits})
        bindings = comparison_flow._reserved_protected_bindings(conn, source.protected_reservation_id)
        digest = comparison_flow._frozen_comparison_context_hash(changed, bindings)
        conn.execute('UPDATE execution_contexts SET resource_limits_json = ?, content_hash = ? WHERE id = ?', (json.dumps(limits), digest, source.id))
        conn.commit()
        before = repo.count_runs_all(conn)
        with pytest.raises(orchestrator.LifecycleError, match='selected comparison permission was not tested'):
            orchestrator.start_run(conn, shift_id, executor='tokenfactory', client_request_id='reasoning-rehashed-drift')
        assert repo.count_runs_all(conn) == before


def test_selected_permission_requires_its_retained_context(selected_migrated, monkeypatch):
    _, path, _, _, _, _, _ = selected_migrated
    with db.connect(path) as conn:
        selection = repo.get_latest_operating_selection(conn, 'bookshop')
        monkeypatch.setattr(repo, 'get_execution_context', lambda *args: None)
        with pytest.raises(orchestrator.LifecycleError, match='selected reasoning permission is unavailable'):
            orchestrator._selected_reasoning_permission(conn, selection)


def test_starter_has_no_invented_comparison_permission():
    assert orchestrator._selected_reasoning_permission(None, SimpleNamespace(comparison_id=None)) is False, "a starter cannot invent a selected comparison permission"


def test_inherited_permission_cannot_move_to_another_model(session, monkeypatch):
    credentials(monkeypatch, 'other-model')
    with db.connect(session.db_file) as conn:
        with pytest.raises(orchestrator.LifecycleError, match='requires the exact Nano model'):
            orchestrator.freeze_diagnostic_context(conn, repo.get_shift(conn, session.shift_id),
                isolated=True, allow_reasoning_off=True)
