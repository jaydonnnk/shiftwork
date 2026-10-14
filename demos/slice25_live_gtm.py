"""One bounded S25 GTM live arm: the two selected operations only.

Phase A rehearses the whole journey with a test-double adapter under the same
frozen meters at zero spend, writing proof_scope TRUSTED_LOCAL_TEST_DOUBLE.
Phase B is the only spending phase and runs once: the shift-1 starter operation
and the shift-2 inherited selected operation, each under its own
LiveOperationBudget (one spawn, one call ceiling, preflight requests == 1). The
qualifying comparison, the selection, the close and the inheritance stay
TRUSTED_LOCAL. Any failure consumes the run directory; never retry.

The reviewed GTM workflows make no inference call, so the meters authorize one
call each and are expected to spend zero; the per-call projection stays the
approved worst-case ceiling, not a claim of spend.
"""
import argparse
import base64
import hashlib
import json
import os
from contextlib import closing
from decimal import Decimal
from pathlib import Path
import sqlite3
import time

from fastapi.testclient import TestClient

from demos.gtm_reviewed import reviewed_inventory
from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain import canonical
from shiftwork.executor.local_process import LocalProcessAdapter
from shiftwork.gateway.redaction import serialized_contains
from shiftwork.ledger import chain
from shiftwork.live_budget import LiveOperationBudget
from shiftwork.store import repo

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/plans/shiftwork/evidence'
RATE_CHECK_DAY = '2026-10-14'  # Rates re-checked this day (evidence/slice25-live-2026-10-14/preflight.md).
LIVE_OUT = EVIDENCE / ('slice25-live-' + RATE_CHECK_DAY)
MODEL = 'nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B'
INPUT_USD = Decimal('0.06')
OUTPUT_USD = Decimal('0.24')
CANDIDATE_PATHS = {
    'A': config.PACKAGE_DIR / 'fixtures/artifacts/gtm/gtm_compare_repair_a_workflow.py',
    'B': config.PACKAGE_DIR / 'fixtures/artifacts/gtm/gtm_compare_repair_b_workflow.py',
}
TREATMENT = 'Rules-first review versus recorded-confidence routing.'
INVESTIGATION = {
    'cause': 'The starter ignores the region/product owner map.',
    'falsifier': 'The captured APAC demo output already names its APAC owner.',
    'public_test': 'Compare the captured owner and record with the frozen route.',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def readonly(path):
    conn = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA query_only=ON')
    return conn


def business(conn):
    return {name: [tuple(row) for row in conn.execute('SELECT * FROM ' + name + ' ORDER BY rowid')]
            for name in ('ledger_events', 'incidents', 'operating_selections')}


def privacy_needles():
    return (*orchestrator._private_public_needles(),
            *(os.environ.get(key, '') for key in ('NEBIUS_API_KEY', 'NEBIUS_PROJECT_ID')))


def assert_privacy(payload, context):
    if any(needle and serialized_contains(payload, needle) for needle in privacy_needles()):
        raise RuntimeError('public privacy failed: ' + context)


def version_pin(view):
    file_hash = canonical.content_hash({name: base64.b64encode(text.encode()).decode()
                                        for name, text in view['files'].items()})
    return (view['content_hash'], file_hash)


def assert_version_pin(view, key):
    assert version_pin(view) == config.TRUSTED_LOCAL_FIXTURES[key], 'frozen version differs from its reviewed pin: ' + key


def preflight():
    if time.strftime('%Y-%m-%d', time.gmtime()) != RATE_CHECK_DAY:
        raise RuntimeError('live rates require a same-day check; today is not ' + RATE_CHECK_DAY)
    if config.SERVICE_MODEL != MODEL:
        raise RuntimeError('configured model differs from the checked rate card')
    reviewed = reviewed_inventory()
    meters = {}
    for name in ('starter_operation', 'inherited_operation'):
        meter = LiveOperationBudget(MODEL, INPUT_USD, OUTPUT_USD)
        meter.preflight(model=MODEL, requests=1)
        meters[name] = meter
    per_call = (INPUT_USD * meters['starter_operation'].reserved_input_tokens_per_call
                + OUTPUT_USD * meters['starter_operation'].reserved_output_tokens_per_call) / 1_000_000
    manifest = {
        'action': 'S25_GTM_TWO_BOUNDED_LIVE_OPERATIONS',
        'date': RATE_CHECK_DAY + ' Asia/Singapore',
        'model': MODEL,
        'image': config.TOKEN_FACTORY_IMAGE,
        'live_stages': ['shift-1 starter diagnostic operation', 'shift-2 inherited selected operation'],
        'trusted_local_stages': ['investigation', 'candidate freezes', 'qualifying comparison',
                                 'selection', 'close', 'inheritance'],
        'meter_shape': {'meters': 2, 'operations_per_meter': 1, 'calls_per_meter': 1,
                        'requests_required': 1,
                        'input_usd_per_million': str(INPUT_USD), 'output_usd_per_million': str(OUTPUT_USD),
                        'per_call_projected_usd': str(per_call),
                        'worst_case_two_meter_ceiling_usd': str(per_call * 2)},
        'rate_check': {
            'day': RATE_CHECK_DAY,
            'note': 'the vendor pricing table could not be read; the raised 0.06 and 0.24 pins stay a conservative upper bound, recorded in evidence/slice25-live-2026-10-14/preflight.md'},
        'reviewed_material_approval_digest': reviewed['approval_digest'],
        'gtm_fixture_pins': {
            key: list(config.TRUSTED_LOCAL_FIXTURES[key])
            for key in ('gtm_starter', 'gtm_compare_candidate_a', 'gtm_compare_candidate_b')},
        'operational_workload': 'fixtures/requests/gtm_pipeline_incident.jsonl (one request: gtm-incident-001)',
        'inference_calls_expected': 'the reviewed GTM workflows make no inference call; the meters cap one call each',
        'sandbox_charge': 'unverified; no zero total-cost claim',
        'output_destination': str(LIVE_OUT.relative_to(ROOT)).replace(os.sep, '/'),
        'retries': 'none; stop on any failed phase, no new reservation or top-up',
    }
    return {'manifest': manifest, 'manifest_sha256': sha(canonical.canonical_bytes(manifest))}


def checked(client, receipt, method, path, expected=200, **kwargs):
    response = client.request(method, path, **kwargs)
    payload = response.json()
    assert_privacy(payload, method + ' ' + path)
    receipt['http'].append({'method': method, 'path': path, 'status': response.status_code, 'body': payload})
    assert response.status_code == expected, f'{method} {path}: expected {expected}, got {response.status_code}'
    return payload


def terminal_run(client, receipt, run_id):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        response = client.get('/api/runs/' + run_id)
        view = response.json()
        assert_privacy(view, 'GET /api/runs/' + run_id)
        if view['state'] in ('FINALIZED', 'FAILED'):
            receipt['http'].append({'method': 'GET', 'path': '/api/runs/' + run_id,
                                    'status': response.status_code, 'body': view})
            return view
        time.sleep(0.5)
    raise RuntimeError('run did not reach a terminal state: ' + run_id)


def adapters(offline):
    if not offline:
        return orchestrator.TokenFactoryAdapter

    class TestDoubleAdapter:
        name = 'tokenfactory'

        def __init__(self, **kwargs):
            self.live_budget = kwargs.get('live_budget')

        async def execute(self, request):
            # Consume the same frozen meter the live adapter would, then run the
            # pinned production artifacts through the trusted-local executor.
            self.live_budget.before_operation()
            local = request.model_copy(update={'harness_ref': 'stdlib-loopback-v1',
                                               'image_ref': 'local-python-stdlib'})
            return await LocalProcessAdapter().execute(local)

    return TestDoubleAdapter


def meter_document(meters):
    per_call = (INPUT_USD * meters['starter_operation'].reserved_input_tokens_per_call
                + OUTPUT_USD * meters['starter_operation'].reserved_output_tokens_per_call) / 1_000_000
    return {
        'pinned_rates': {'input_usd_per_million': str(INPUT_USD), 'output_usd_per_million': str(OUTPUT_USD),
                         'rate_check_day': RATE_CHECK_DAY},
        'per_call_projected_usd': f'{per_call:f}',
        'worst_case_two_meter_ceiling_usd': f'{per_call * 2:f}',
        'meters': {name: {'model': meter.model, 'operations': meter.operations, 'calls': meter.calls,
                          'projected_usd': f'{meter.projected_usd:f}',
                          'max_operations': meter.max_operations, 'max_calls': meter.max_calls,
                          'max_projected_usd': str(meter.max_projected_usd)}
                   for name, meter in meters.items()},
        'note': 'projected_usd is computed from spent calls; failed attempts are never refunded and the ceiling is the approved worst case',
        'sandbox_charge': 'unverified; no zero total-cost claim',
    }


def journey(out, receipt, meter1, meter2):
    db_path = out / 'journey.db'
    # Phase app 1: the isolated executor runs only the shift-1 starter operation.
    with TestClient(create_app(str(db_path), executor='tokenfactory', live_operation_budget=meter1)) as client:
        opened = checked(client, receipt, 'POST', '/api/engagements/gtm/shifts', 201)
        shift1 = opened['id']
        assert shift1 == 'gtm-shift-01'
        board = checked(client, receipt, 'GET', '/api/engagements/gtm/board')
        starter_selection = board['operating_selection']
        assert starter_selection['kind'] == 'STARTER_BASELINE' and starter_selection['state'] == 'VALID'
        starter_version = checked(client, receipt, 'GET',
                                  '/api/artifact-versions/' + starter_selection['selected_version_id'])
        assert_version_pin(starter_version, 'gtm_starter')
        started = checked(client, receipt, 'POST', '/api/shifts/' + shift1 + '/runs', 202,
                          json={'client_request_id': 's25-live-starter'})
        starter_run = terminal_run(client, receipt, started['id'])
        assert starter_run['purpose'] == 'OPERATION' and starter_run['state'] == 'FINALIZED'
        assert starter_run['adapter'] == 'tokenfactory' and starter_run['evidence_mode'] == 'ISOLATED_LIVE'
        assert starter_run['artifact_version_id'] == starter_selection['selected_version_id']
        starter_outputs = checked(client, receipt, 'GET', '/api/runs/' + starter_run['id'] + '/outputs')
        assert len(starter_outputs) == 1 and starter_outputs[0]['transport_error'] is None
        starter_checks = checked(client, receipt, 'GET', '/api/runs/' + starter_run['id'] + '/checks')
        failing = [row for row in starter_checks if row['verdict'] == 'fail']
        assert failing and {row['reason_code'] for row in failing} == {'WRONG_ACTION'}, \
            'the reviewed starter must fail its named task checks'
        ledger_starter = checked(client, receipt, 'GET', '/api/engagements/gtm/ledger')
        assert ledger_starter['chain_status'] == 'VALID'
        assert [row['event_type'] for row in ledger_starter['events']] == ['INCIDENT_OPENED']
        assert ledger_starter['events'][0]['cause_refs'][0] == starter_run['id']
    # Phase app 2: the trusted-local executor runs the investigation, both
    # candidate freezes, the comparison, the selection, the close and the inherit.
    with TestClient(create_app(str(db_path), executor='local_process')) as client:
        investigation = checked(client, receipt, 'POST', '/api/shifts/' + shift1 + '/investigations', 201, json={
            'source_run_id': starter_run['id'], 'source_request_ordinal': 1,
            'cause': INVESTIGATION['cause'], 'falsifier': INVESTIGATION['falsifier'],
            'public_test': INVESTIGATION['public_test'],
            'client_request_id': 's25-live-investigation'})
        versions = {}
        files_by_label = {}
        for label in ('A', 'B'):
            files = {'service.py': CANDIDATE_PATHS[label].read_text(encoding='utf-8')}
            files_by_label[label] = files
            checked(client, receipt, 'PUT', '/api/shifts/' + shift1 + '/artifact', json={'files': files})
            frozen = checked(client, receipt, 'POST', '/api/shifts/' + shift1 + '/artifact/versions', 201,
                             json={'contract': config.GTM_STARTER_CONTRACT_JSON})
            source = checked(client, receipt, 'GET', '/api/artifact-versions/' + frozen['id'])
            assert source['files'] == files
            assert source['content_hash'] == frozen['content_hash']
            assert_version_pin(source, 'gtm_compare_candidate_' + label.lower())
            versions[label] = frozen
        with closing(readonly(db_path)) as conn:
            before_business = business(conn)
        created = checked(client, receipt, 'POST', '/api/shifts/' + shift1 + '/experiments', 202, json={
            'kind': 'QUALIFYING_COMPARISON', 'investigation_id': investigation['id'],
            'candidate_a_version_id': versions['A']['id'], 'candidate_b_version_id': versions['B']['id'],
            'declared_treatment': TREATMENT, 'client_request_id': 's25-live-comparison'})
        comparison = checked(client, receipt, 'GET', '/api/experiments/' + created['id'])
        assert comparison['state'] == 'FINALIZED' and comparison['outcome']['status'] == 'COMPLETE'
        assert len(comparison['trials']) == 6 and all(row['state'] == 'COMPLETE' for row in comparison['trials'])
        assert all(row['eligible'] for row in comparison['outcome']['eligibility'])
        assert comparison['context_evidence_class'] == 'TRUSTED_LOCAL'
        assert all(row['evidence_mode'] == 'TRUSTED_LOCAL' for row in comparison['trials'])
        with closing(readonly(db_path)) as conn:
            assert business(conn) == before_business, 'the comparison wrote business history'
        choice = checked(client, receipt, 'POST', '/api/shifts/' + shift1 + '/selections', 201, json={
            'comparison_id': comparison['id'], 'selected_version_id': versions['A']['id'],
            'expected_prior_selection_id': starter_selection['id'],
            'rationale': 'Choose the independently eligible rules-first repair.',
            'client_request_id': 's25-live-choice'})
        assert choice['kind'] == 'LEARNER_CHOICE'
        assert choice['selected_version_id'] == versions['A']['id']
        assert choice['retained_alternative_version_id'] == versions['B']['id']
        with closing(readonly(db_path)) as conn:
            after_choice = business(conn)
        checked(client, receipt, 'POST', '/api/shifts/' + shift1 + '/selections', 409, json={
            'comparison_id': comparison['id'], 'selected_version_id': versions['B']['id'],
            'expected_prior_selection_id': 'stale-selection',
            'rationale': 'Stale prior control; must be refused.',
            'client_request_id': 's25-live-stale-choice'})
        checked(client, receipt, 'POST', '/api/shifts/' + shift1 + '/runs', 409,
                json={'client_request_id': 's25-live-second-starter'})
        with closing(readonly(db_path)) as conn:
            assert business(conn) == after_choice, 'a refused action wrote business history'
        checked(client, receipt, 'POST', '/api/shifts/' + shift1 + '/close')
        opened2 = checked(client, receipt, 'POST', '/api/engagements/gtm/shifts', 201)
        shift2 = opened2['id']
        board2 = checked(client, receipt, 'GET', '/api/engagements/gtm/board')
        assert board2['operating_selection']['id'] == choice['id']
        inherited = checked(client, receipt, 'GET', '/api/shifts/' + shift2 + '/artifact')
        assert inherited['files'] == files_by_label['A'], 'the next shift did not inherit every selected file'
    # Phase app 3: the isolated executor runs only the inherited selected operation.
    with TestClient(create_app(str(db_path), executor='tokenfactory', live_operation_budget=meter2)) as client:
        fresh_board = checked(client, receipt, 'GET', '/api/engagements/gtm/board')
        assert fresh_board['operating_selection']['id'] == choice['id']
        draft = checked(client, receipt, 'GET', '/api/shifts/' + shift2 + '/artifact')
        assert draft['files'] == files_by_label['A']
        started2 = checked(client, receipt, 'POST', '/api/shifts/' + shift2 + '/runs', 202,
                           json={'client_request_id': 's25-live-selected'})
        op_run = terminal_run(client, receipt, started2['id'])
        assert op_run['purpose'] == 'OPERATION' and op_run['state'] == 'FINALIZED'
        assert op_run['adapter'] == 'tokenfactory' and op_run['evidence_mode'] == 'ISOLATED_LIVE'
        assert op_run['artifact_version_id'] == versions['A']['id'] and op_run['selection_id'] == choice['id']
        op_outputs = checked(client, receipt, 'GET', '/api/runs/' + op_run['id'] + '/outputs')
        assert len(op_outputs) == 1 and op_outputs[0]['transport_error'] is None
        op_checks = checked(client, receipt, 'GET', '/api/runs/' + op_run['id'] + '/checks')
        assert op_checks and all(row['verdict'] == 'pass' for row in op_checks), \
            'the selected operation failed its checks'
        ledger = checked(client, receipt, 'GET', '/api/engagements/gtm/ledger')
        assert ledger['chain_status'] == 'VALID'
        with closing(readonly(db_path)) as conn:
            events = repo.list_ledger_events(conn, 'gtm')
            assert chain.verify_chain(events).value == 'VALID'
            generated = [row for row in events if row.cause_refs and row.cause_refs[0] == op_run['id']]
            kinds = [row.event_type.value for row in generated if row.event_type.value != 'INCIDENT_RESOLVED']
            assert kinds == ['OWNER_ASSIGNED', 'SLA_CLOCK_STARTED']
            assert all(row.payload['signal_ref'] == 'signal:incident-apac'
                       and row.payload['owner'] == 'owner-apac-platform'
                       for row in generated if row.event_type.value != 'INCIDENT_RESOLVED')
            assert orchestrator.replay_assessment(conn, op_run['id']).status == 'IDENTICAL'
            assert [row.state.value for row in repo.list_incidents(conn, 'gtm')] == ['RESOLVED']
    receipt.update(
        starter_operation=starter_run,
        starter_check_verdicts=sorted(row['verdict'] for row in starter_checks),
        investigation={'id': investigation['id'], 'cause': investigation['cause'],
                       'falsifier': investigation['falsifier'], 'public_test': investigation['public_test']},
        candidates={label: {'id': view['id'], 'content_hash': view['content_hash']}
                    for label, view in versions.items()},
        comparison={'id': comparison['id'], 'state': comparison['state'],
                    'outcome_status': comparison['outcome']['status'],
                    'evidence_class': comparison['context_evidence_class'],
                    'trials': len(comparison['trials'])},
        selection={'id': choice['id'], 'kind': choice['kind'], 'selected_version_id': choice['selected_version_id'],
                   'selected_content_hash': choice['selected_content_hash'],
                   'retained_alternative_version_id': choice['retained_alternative_version_id']},
        inherited_shift=shift2,
        inherited_operation=op_run,
        ledger_event_types=[row['event_type'] for row in ledger['events']],
    )
    assert meter1.operations == 1 and meter2.operations == 1
    assert meter1.calls == 0 == meter2.calls, 'the pinned GTM workflows make no inference call'


def run(out, *, packet, offline=False):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'once.marker').write_text('One bounded run only. Any failure consumes it. Never retry.\n',
                                     encoding='utf-8')
    meter1 = LiveOperationBudget(MODEL, INPUT_USD, OUTPUT_USD)
    meter2 = LiveOperationBudget(MODEL, INPUT_USD, OUTPUT_USD)
    meter1.preflight(model=MODEL, requests=1)
    meter2.preflight(model=MODEL, requests=1)
    saved_env = {key: os.environ.get(key) for key in ('NEBIUS_API_KEY', 'NEBIUS_PROJECT_ID')}
    original_adapter = orchestrator.TokenFactoryAdapter
    if offline:
        os.environ['NEBIUS_API_KEY'] = 'TEST_ONLY_NO_PROVIDER'
        os.environ['NEBIUS_PROJECT_ID'] = 'aiproject-TEST_ONLY_NO_PROVIDER'
    active_needles = privacy_needles()
    receipt = {'status': 'INCOMPLETE',
               'proof_scope': 'TRUSTED_LOCAL_TEST_DOUBLE' if offline else 'LIVE',
               'mode': 'operations only; comparison, selection, close and inheritance stayed TRUSTED_LOCAL',
               'manifest': packet['manifest'], 'manifest_sha256': packet['manifest_sha256'],
               'http': []}
    try:
        orchestrator.TokenFactoryAdapter = adapters(offline)
        journey(out, receipt, meter1, meter2)
        receipt['status'] = 'PASS'
    finally:
        orchestrator.TokenFactoryAdapter = original_adapter
        if offline:
            for key, value in saved_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        meters = {'starter_operation': meter1, 'inherited_operation': meter2}
        receipt.update(
            adapter_operation_attempts={name: meter.operations for name, meter in meters.items()},
            live_operations=0 if offline else meter1.operations + meter2.operations,
            inference_calls=meter1.calls + meter2.calls,
        )
        if any(needle and serialized_contains(receipt, needle) for needle in active_needles):
            raise RuntimeError('run receipt failed public privacy; databases retained')
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        (out / 'meter.json').write_text(json.dumps(meter_document(meters), indent=2), encoding='utf-8')
    print(json.dumps({'status': receipt['status'], 'proof_scope': receipt['proof_scope'],
                      'live_operations': receipt['live_operations'],
                      'inference_calls': receipt['inference_calls'],
                      'out': str(out)}))


def main():
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--offline-rehearsal', action='store_true')
    modes.add_argument('--execute', action='store_true')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--approved-manifest-sha256')
    args = parser.parse_args()
    packet = preflight()
    if not args.offline_rehearsal and not args.execute:
        print(json.dumps(packet, indent=2))
        return
    if args.out is None:
        parser.error('a fresh --out directory is required')
    out = args.out.resolve()
    if args.execute:
        if args.approved_manifest_sha256 != packet['manifest_sha256']:
            raise RuntimeError('explicit approval must bind these exact manifest bytes')
        if out != LIVE_OUT.resolve():
            raise RuntimeError('the live run writes only the approved evidence destination: ' + str(LIVE_OUT))
        for name in ('once.marker', 'receipt.json', 'meter.json', 'journey.db'):
            if (out / name).exists():
                raise RuntimeError('the approved destination already holds run evidence; never retry: ' + name)
        if (not os.environ.get('NEBIUS_API_KEY')
                or not os.environ.get('NEBIUS_PROJECT_ID', '').startswith('aiproject-')):
            raise RuntimeError('export NEBIUS_API_KEY and NEBIUS_PROJECT_ID in this shell first; never pass them on the command line')
    else:
        if out == LIVE_OUT.resolve():
            raise RuntimeError('a rehearsal may not write the curated live evidence destination')
        if out.exists():
            raise RuntimeError('a fresh --out directory is required')
    run(out, packet=packet, offline=args.offline_rehearsal)


if __name__ == '__main__':
    main()
