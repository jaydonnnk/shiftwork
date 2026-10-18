"""S28 hosting wiring. All provider/control-plane traffic is replaced offline."""

from decimal import Decimal
import json

from contree_client.httpx import ContreeAsyncClient
from contree_client.models import WhoAmIResponse
from fastapi.testclient import TestClient
import pytest

from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.assist.gateway import LiveAssistGateway
from shiftwork.live_budget import LiveComparisonBudget, LiveOperationBudget
from tests.orchestrator.test_selection_operation import (
    selected_migrated, _FakeTokenFactoryAdapter, _candidate,
)
from demos.final_pivot import create_v5_sample
from shiftwork import comparison_flow
from shiftwork.store import db, repo
from tests.orchestrator import pivot_flow
from tests.packs.material import staged_material
from threading import Barrier, Thread

PERMISSIONS = ('cancel', 'import', 'list', 'set_image_tag', 'spawn', 'spawn_disposable')


@pytest.fixture
def hosted_environment(monkeypatch):
    monkeypatch.setenv('RENDER', 'true')
    monkeypatch.setenv('NEBIUS_API_KEY', 'S28_SYNTHETIC_PROVIDER_CANARY')
    monkeypatch.setenv('NEBIUS_PROJECT_ID', 'aiproject-S28-SYNTHETIC')
    permissions = dict.fromkeys(PERMISSIONS, True)

    async def whoami(_self):
        return WhoAmIResponse(token_uuid='S28_SYNTHETIC_ID', token_expiration=None,
                             permissions=permissions, operations_stat={}, limits={})

    monkeypatch.setattr(ContreeAsyncClient, 'whoami', whoami)
    return permissions


def startup_result(app):
    try:
        with TestClient(app) as client:
            response = client.get('/api/runtime')
            return response.status_code, response.json()
    except RuntimeError as exc:
        return 'rejected', str(exc)


def test_both_credentials_enable_live_and_its_assistance(hosted_environment, tmp_path):
    app = create_app(str(tmp_path / 'live.db'))
    assert app.state.executor == 'tokenfactory', 'both credentials must enable live execution'
    assert isinstance(app.state.assist_gateway, LiveAssistGateway), 'live help must be configured'
    status, runtime = startup_result(app)
    assert status == 200
    assert runtime.get('configured_executor') == 'tokenfactory'
    assert runtime.get('preflight_permissions') == dict.fromkeys(PERMISSIONS, True)


@pytest.mark.parametrize('missing', ['NEBIUS_API_KEY', 'NEBIUS_PROJECT_ID', 'both'])
def test_missing_credential_serves_labelled_recorded_fallback(hosted_environment, monkeypatch, tmp_path, missing):
    for name in ('NEBIUS_API_KEY', 'NEBIUS_PROJECT_ID'):
        if missing in (name, 'both'):
            monkeypatch.delenv(name)
    try:
        app = create_app(str(tmp_path / 'fallback.db'))
        status, runtime = startup_result(app)
    except (RuntimeError, ValueError):
        status, runtime = 'rejected', {}
    assert status == 200, 'fallback must serve without a provider'
    assert app.state.executor == 'recorded', 'fallback must never execute trusted local code as recorded'
    assert runtime.get('configured_executor') == 'recorded', 'fallback must be labelled recorded'
    assert 'recorded' in runtime.get('notice', '').lower()
    assert app.state.assist_gateway is None, 'partial credentials cannot enable assistance'
    assert app.state.live_operation_budget is None
    assert app.state.live_comparison_budget is None


@pytest.mark.parametrize('name,value', [
    ('NEBIUS_API_KEY', ' S28_SYNTHETIC_PROVIDER_CANARY'),
    ('NEBIUS_PROJECT_ID', 'aiproject-S28-SYNTHETIC '),
    ('NEBIUS_PROJECT_ID', 'project-S28-SYNTHETIC'),
])
def test_invalid_present_credentials_fail_closed(hosted_environment, monkeypatch, tmp_path, name, value):
    monkeypatch.setenv(name, value)
    try:
        status, _ = startup_result(create_app(str(tmp_path / 'invalid.db')))
    except RuntimeError:
        status = 'rejected'
    assert status == 'rejected', 'invalid credential configuration must stop startup'


@pytest.mark.parametrize('permission', PERMISSIONS)
def test_each_missing_permission_stops_live_startup(hosted_environment, tmp_path, permission):
    hosted_environment[permission] = False
    status, _ = startup_result(create_app(str(tmp_path / 'denied.db')))
    assert status == 'rejected', 'every required Sandbox permission must be true'


@pytest.mark.parametrize('value', [None, 1])
def test_preflight_requires_explicit_boolean_permission(hosted_environment, tmp_path, value):
    hosted_environment['spawn'] = value
    status, _ = startup_result(create_app(str(tmp_path / 'strict.db')))
    assert status == 'rejected', 'missing or non-boolean permissions cannot authorize live execution'


def test_preflight_error_is_sanitized_and_stops_startup(hosted_environment, monkeypatch, tmp_path):
    async def broken(_self):
        raise RuntimeError('S28_SYNTHETIC_PROVIDER_CANARY')
    monkeypatch.setattr(ContreeAsyncClient, 'whoami', broken)
    status, detail = startup_result(create_app(str(tmp_path / 'error.db')))
    assert status == 'rejected', 'failed entitlement verification must stop startup'
    assert detail == 'Hosted Sandbox preflight failed', 'startup errors must not echo provider details'


def test_hosted_meters_are_fresh_and_preserve_consumed_allowances(hosted_environment, tmp_path):
    app = create_app(str(tmp_path / 'meters.db'))
    for name, cls, operations, calls in (
        ('live_operation_budget', LiveOperationBudget, 1, 1),
        ('live_comparison_budget', LiveComparisonBudget, 12, 18),
    ):
        factory = getattr(app.state, name)
        assert callable(factory), 'hosted actions need meter factories'
        first, second = factory(), factory()
        assert isinstance(first, cls) and isinstance(second, cls), 'each action needs its correct meter type'
        assert first is not second, 'independent actions must not share a meter'
        for _ in range(operations):
            first.before_operation()
        for _ in range(calls):
            first.before_inference(config.SERVICE_MODEL)
        rejected = False
        try:
            first.before_operation()
        except ValueError:
            rejected = True
        assert rejected, 'consumed allowances must stay consumed'
        assert second.operations == second.calls == 0, 'the next action needs an untouched meter'
        assert (second.max_operations, second.max_calls, second.max_projected_usd) == (operations, calls, Decimal('0.10'))


def test_explicit_demo_executor_is_preserved_on_render(hosted_environment, tmp_path):
    app = create_app(str(tmp_path / 'explicit.db'), executor='local_process')
    assert app.state.executor == 'local_process'
    assert app.state.assist_gateway is None


def test_local_default_does_not_enable_provider_from_credentials(hosted_environment, monkeypatch, tmp_path):
    monkeypatch.delenv('RENDER')
    app = create_app(str(tmp_path / 'local.db'))
    assert app.state.executor == config.EXECUTOR_ADAPTER, 'local defaults must remain unchanged'


def test_runtime_is_safe_and_reports_reset_and_distinct_boots(hosted_environment, tmp_path):
    first = startup_result(create_app(str(tmp_path / 'one.db')))[1]
    second = startup_result(create_app(str(tmp_path / 'two.db')))[1]
    assert first.get('boot_id') and first.get('boot_id') != second.get('boot_id'), 'each boot needs its own observable marker'
    assert 'fresh practice database' in first.get('notice', '')
    assert 'shared' in first.get('notice', '').lower()
    serialized = json.dumps(first)
    for needle in ('S28_SYNTHETIC_PROVIDER_CANARY', 'aiproject-S28-SYNTHETIC', 'S28_SYNTHETIC_ID'):
        assert needle not in serialized
        injected = json.dumps({**first, 'injected': needle})
        assert needle in injected, 'privacy control must match the serialized surface'


def test_operation_factory_is_resolved_before_execution(selected_migrated, monkeypatch):
    _, database, shift_id, *_ = selected_migrated
    monkeypatch.setenv('NEBIUS_API_KEY', 'S28_SYNTHETIC_PROVIDER_CANARY')
    monkeypatch.setenv('NEBIUS_PROJECT_ID', 'aiproject-S28-SYNTHETIC')
    monkeypatch.setattr(orchestrator, 'TokenFactoryAdapter', _FakeTokenFactoryAdapter)
    meter = LiveOperationBudget(config.SERVICE_MODEL, Decimal('0.06'), Decimal('0.24'))
    with TestClient(create_app(str(database), executor='tokenfactory', live_operation_budget=lambda: meter)) as client:
        started = client.post(f'/api/shifts/{shift_id}/runs', json={'client_request_id': 's28-factory-operation'})
        assert started.status_code == 202
        run = client.get('/api/runs/' + started.json()['id']).json()
        assert run.get('state') == 'FINALIZED', 'the route must pass the resolved operation meter'
    assert meter.operations == meter.calls == 1


@pytest.mark.parametrize('kind', ['QUALIFYING_COMPARISON', 'LATER_CONDITION_COMPARISON'])
def test_comparison_factory_handoff_uses_one_action_meter(tmp_path, monkeypatch, kind):
    database = tmp_path / 'comparison.db'
    if kind == 'QUALIFYING_COMPARISON':
        create_v5_sample(database)
    with TestClient(create_app(str(database), executor='recorded')) as client:
        if kind == 'QUALIFYING_COMPARISON':
            shift_id = client.post('/api/engagements/bookshop/shifts').json()['id']
            investigation = client.post(f'/api/shifts/{shift_id}/investigations', json={
                'source_run_id': 'run-v5-0001', 'source_request_ordinal': 1,
                'cause': 'the starter omits tasks', 'falsifier': 'all required tasks complete',
                'public_test': 'check the task results', 'client_request_id': 's28-investigation',
            })
            assert investigation.status_code == 201
            candidates = [_candidate(client, shift_id, label) for label in ('A', 'B')]
            body = {'kind': kind, 'investigation_id': investigation.json()['id'],
                    'candidate_a_version_id': candidates[0]['id'],
                    'candidate_b_version_id': candidates[1]['id']}
        else:
            pivot_flow.qualified_shift(client)
            shift_id = pivot_flow.open_successor(client)['id']
            outage = pivot_flow.staged_outage_state(tmp_path)
            with staged_material(monkeypatch, tmp_path / 'outage-package', {
                'fixtures/shop/bookshop_pivot_public_state.json': outage.read_bytes(),
            }):
                run = client.post(f'/api/shifts/{shift_id}/runs', json={'client_request_id': 's28-outage'})
                assert run.status_code == 202
            body = {'kind': kind, 'observed_run_id': run.json()['id']}
    monkeypatch.setenv('NEBIUS_API_KEY', 'S28_SYNTHETIC_PROVIDER_CANARY')
    monkeypatch.setenv('NEBIUS_PROJECT_ID', 'aiproject-S28-SYNTHETIC')
    created, received = [], []

    def factory():
        meter = LiveComparisonBudget(config.SERVICE_MODEL, Decimal('0.06'), Decimal('0.24'))
        created.append(meter)
        return meter

    def bounded_worker(database, experiment_id, meter=None):
        received.append(meter)

    monkeypatch.setattr(comparison_flow, 'execute_comparison_task', bounded_worker)
    body.update(declared_treatment='compare the two exact repairs', client_request_id='s28-comparison')
    with TestClient(create_app(str(database), executor='tokenfactory', live_comparison_budget=factory)) as client:
        response = client.post(f'/api/shifts/{shift_id}/experiments', json=body)
        assert response.status_code == 202, response.text
        view = client.get('/api/experiments/' + response.json()['id']).json()
        assert view.get('state') == 'PLANNED' and len(view.get('trials', [])) == 6
    assert len(created) == len(received) == 1, 'resolve exactly one meter for this comparison'
    assert received[0] is created[0], 'pass the resolved comparison meter into its worker'


@pytest.mark.parametrize('wrong', [None, 'comparison'])
def test_missing_or_wrong_operation_factory_refuses_before_reservation(selected_migrated, monkeypatch, wrong):
    _, database, shift_id, *_ = selected_migrated
    monkeypatch.setenv('NEBIUS_API_KEY', 'S28_SYNTHETIC_PROVIDER_CANARY')
    monkeypatch.setenv('NEBIUS_PROJECT_ID', 'aiproject-S28-SYNTHETIC')
    value = None if wrong is None else LiveComparisonBudget(config.SERVICE_MODEL, Decimal('0.06'), Decimal('0.24'))
    with TestClient(create_app(str(database), executor='tokenfactory', live_operation_budget=lambda: value)) as client:
        before = client.get('/api/engagements/bookshop/board').json().get('latest_run')
        response = client.post(f'/api/shifts/{shift_id}/runs', json={'client_request_id': 's28-invalid-meter'})
        assert response.status_code == 409, 'invalid action wiring must refuse before reservation'
        assert client.get('/api/engagements/bookshop/board').json().get('latest_run') == before


def test_selected_operation_claim_is_atomic_for_duplicate_live_requests(selected_migrated, monkeypatch):
    _, database, shift_id, *_ = selected_migrated
    monkeypatch.setenv('NEBIUS_API_KEY', 'S28_SYNTHETIC_PROVIDER_CANARY')
    monkeypatch.setenv('NEBIUS_PROJECT_ID', 'aiproject-S28-SYNTHETIC')
    claim = getattr(repo, 'claim_run_execution', None)
    assert callable(claim), 'live operation execution needs an atomic queued claim'
    conn = db.connect(database)
    run = orchestrator.start_run(conn, shift_id, executor='tokenfactory', client_request_id='s28-duplicate')
    conn.close()
    barrier = Barrier(2)

    def competing_claim(conn, run_id):
        barrier.wait(timeout=10)
        return claim(conn, run_id)

    monkeypatch.setattr(repo, 'claim_run_execution', competing_claim)
    _FakeTokenFactoryAdapter.calls = []
    monkeypatch.setattr(orchestrator, 'TokenFactoryAdapter', _FakeTokenFactoryAdapter)
    errors = []

    def execute():
        conn = db.connect(database)
        try:
            orchestrator.execute_run(conn, run.id, LiveOperationBudget(config.SERVICE_MODEL, Decimal('0.06'), Decimal('0.24')))
        except Exception as exc:
            errors.append(type(exc).__name__)
        finally:
            conn.close()

    threads = [Thread(target=execute) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)
    assert len(_FakeTokenFactoryAdapter.calls) == 1, 'duplicate requests must not spawn twice using fresh meters'
    assert not errors, 'the losing worker must return the existing run without failing it'


def test_run_claim_cannot_reclaim_a_running_action(selected_migrated):
    _, database, shift_id, *_ = selected_migrated
    claim = getattr(repo, 'claim_run_execution', None)
    assert callable(claim), 'run claims must be conditional on QUEUED'
    conn = db.connect(database)
    try:
        run = orchestrator.start_run(conn, shift_id, client_request_id='s28-claim')
        assert claim(conn, run.id) is True
        conn.commit()
        assert claim(conn, run.id) is False, 'a consumed action must never be reclaimed'
    finally:
        conn.close()


def test_fresh_hosted_bellwether_replays_its_labelled_baseline(hosted_environment, tmp_path, monkeypatch):
    _FakeTokenFactoryAdapter.calls = []
    monkeypatch.setattr(orchestrator, 'TokenFactoryAdapter', _FakeTokenFactoryAdapter)
    with TestClient(create_app(str(tmp_path / 'fresh-host.db'))) as client:
        shift = client.post('/api/engagements/bookshop/shifts')
        assert shift.status_code == 201
        board = client.get('/api/engagements/bookshop/board').json()
        started = client.post('/api/shifts/' + shift.json()['id'] + '/runs', json={'client_request_id': 's28-fresh-starter'})
        assert started.status_code == 202
        run = client.get('/api/runs/' + started.json()['id']).json()
        assert run.get('state') == 'FINALIZED', 'the legacy first inspection must remain runnable without relaxing its requirements'
        assert run.get('evidence_mode') == 'RECORDED_INSPECTION'
        assert run.get('artifact_version_id') == board['operating_selection']['selected_version_id']
        assert len(_FakeTokenFactoryAdapter.calls) == 0, 'the saved starter inspection must never be represented as fresh execution'
        shift_id = shift.json()['id']
        investigation = client.post(f'/api/shifts/{shift_id}/investigations', json={
            'source_run_id': run['id'], 'source_request_ordinal': 1,
            'cause': 'the starter omits a required task', 'falsifier': 'all required tasks complete',
            'public_test': 'check all task results', 'client_request_id': 's28-fresh-investigation',
        })
        assert investigation.status_code == 201
        candidate = _candidate(client, shift_id, 'A')
        diagnostic = client.post(f'/api/shifts/{shift_id}/experiments', json={
            'kind': 'DIAGNOSTIC', 'candidate_a_version_id': candidate['id'],
            'investigation_id': investigation.json()['id'], 'client_request_id': 's28-fresh-diagnostic',
        })
        assert diagnostic.status_code == 202
        latest = client.get('/api/engagements/bookshop/board').json()['latest_run']
        assert latest.get('state') == 'FINALIZED' and latest.get('evidence_mode') == 'ISOLATED_LIVE'
    assert len(_FakeTokenFactoryAdapter.calls) == 1, 'the edited diagnostic must execute through the isolated adapter'


def test_fallback_action_discloses_trusted_local_execution(hosted_environment, monkeypatch, tmp_path):
    monkeypatch.delenv('NEBIUS_API_KEY')
    with TestClient(create_app(str(tmp_path / 'fallback-action.db'))) as client:
        runtime = client.get('/api/runtime').json()
        assert 'TRUSTED_LOCAL' in runtime.get('notice', ''), 'fallback notice must disclose pinned local execution'
        shift = client.post('/api/engagements/gtm/shifts')
        assert shift.status_code == 201
        started = client.post('/api/shifts/' + shift.json()['id'] + '/runs', json={'client_request_id': 's28-offline-starter'})
        assert started.status_code == 202
        run = client.get('/api/runs/' + started.json()['id']).json()
        assert run.get('state') == 'FINALIZED' and run.get('evidence_mode') == 'TRUSTED_LOCAL'


def test_distinct_operations_receive_distinct_fresh_meters(selected_migrated, monkeypatch):
    _, database, shift_id, *_ = selected_migrated
    monkeypatch.setenv('NEBIUS_API_KEY', 'S28_SYNTHETIC_PROVIDER_CANARY')
    monkeypatch.setenv('NEBIUS_PROJECT_ID', 'aiproject-S28-SYNTHETIC')
    monkeypatch.setattr(orchestrator, 'TokenFactoryAdapter', _FakeTokenFactoryAdapter)
    _FakeTokenFactoryAdapter.calls = []
    meters = []
    def factory():
        meter = LiveOperationBudget(config.SERVICE_MODEL, Decimal('0.06'), Decimal('0.24'))
        meters.append(meter)
        return meter
    with TestClient(create_app(str(database), executor='tokenfactory', live_operation_budget=factory), raise_server_exceptions=False) as client:
        for index in (1, 2):
            if index == 2:
                shift_id = pivot_flow.open_successor(client)['id']
            started = client.post(f'/api/shifts/{shift_id}/runs', json={'client_request_id': f's28-distinct-{index}'})
            assert started.status_code == 202
            run = client.get('/api/runs/' + started.json()['id']).json()
            assert run.get('state') == 'FINALIZED', 'a later action must not inherit a consumed meter'
    assert len(meters) == len(_FakeTokenFactoryAdapter.calls) == 2
    assert meters[0] is not meters[1]
    assert all(adapter.kwargs.get('live_budget') is meter for adapter, meter in zip(_FakeTokenFactoryAdapter.calls, meters))
    assert [(meter.operations, meter.calls) for meter in meters] == [(1, 1), (1, 1)]
