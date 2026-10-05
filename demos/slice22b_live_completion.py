"""Prepare and rehearse a new S22b completion packet; execute only its approval.

The historical starter/diagnostic allowances are consumed. This runner uses
fresh copies and fresh ceilings, never retries a failed or incomplete phase.
"""
import argparse
import base64
from contextlib import closing
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3

from fastapi.testclient import TestClient
from demos.final_pivot import create_v5_sample
from demos.slice22b_completion_candidates import candidate_files
from demos.slice22b_live_starter import IMAGE, MODEL, NoInferenceOperationBudget, load_authorized_credentials, preflight as material_preflight
from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.assist.gateway import AssistRejected, AssistReply, LiveAssistGateway
from shiftwork.domain import canonical
from shiftwork.domain.models import AssistRole
from shiftwork.executor.local_process import LocalProcessAdapter
from shiftwork.gateway.redaction import serialized_contains
from shiftwork.ledger import chain
from shiftwork.live_budget import LiveComparisonBudget
from shiftwork.store import repo

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/plans/shiftwork/evidence'
SOURCE = EVIDENCE / 'slice22b-live-starter-2026-10-05/starter.db'
SOURCE_SHA = 'f23188694006f3b514297f69267a95b97b8ed8f384e04ef46f1ec1cec42f265b'
LIVE_OUT = EVIDENCE / 'slice22b-live-completion-2026-10-05'
TREATMENT = 'A allocates provisionally after stock, rolls back before final confirmation; B reads both dependencies before one final write. Both retain same-intent final references.'

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

class NoInferenceComparisonBudget(LiveComparisonBudget):
    def before_inference(self, model):
        raise ValueError('this packet authorizes no in-service inference')

class OneHintGateway:
    def __init__(self, delegate):
        self.delegate, self.calls = delegate, 0
    def generate(self, *, model_id, role, prompt):
        if model_id != MODEL or role is not AssistRole.HINT or self.calls >= 1:
            raise AssistRejected('ASSIST_GATEWAY_FAILED')
        self.calls += 1
        return self.delegate.generate(model_id=model_id, role=role, prompt=prompt)

def preflight():
    inherited = material_preflight()['manifest']
    if sha(SOURCE.read_bytes()) != SOURCE_SHA or any(Path(str(SOURCE) + s).exists() for s in ('-wal', '-shm')):
        raise RuntimeError('immutable starter database differs or has active sidecars')
    with closing(readonly(SOURCE)) as conn:
        source = repo.get_run(conn, 'run-0001')
        assert source.state.value == 'FINALIZED' and source.purpose.value == 'OPERATION'
        version = repo.get_version(conn, source.artifact_version_id)
        contract = version.contract.model_dump(mode='json')
        catalog_hash = version.contract_catalog_hash
    candidates = {}
    for label in ('A', 'B'):
        files = candidate_files(label)
        compile(files['service.py'], 'service.py', 'exec')
        candidates[label] = {'files_sha256': {name: sha(text.encode()) for name, text in files.items()},
                             'artifact_content_hash': canonical.artifact_content_hash(files, contract, catalog_hash)}
    runtime = dict(inherited['runtime'])
    for path in (Path(__file__), ROOT / 'demos/slice22b_completion_candidates.py', ROOT / 'demos/slice22b_completion_audit.py', ROOT / 'demos/final_pivot.py'):
        runtime[str(path.relative_to(ROOT)).replace('\\', '/')] = sha(path.read_bytes())
    manifest = {'action': 'S22B_COMPARISON_PILOT_BOOTSTRAP_ONE_HINT', 'date': '2026-10-05 Asia/Singapore',
                'model': MODEL, 'image': IMAGE, 'runtime': runtime, 'reviewed_pins': inherited['reviewed_pins'],
                'source_database_sha256': SOURCE_SHA, 'contract': contract, 'candidates': candidates,
                'candidate_authorship': 'operator/coding-assistant verification fixture; not learner evidence',
                'declared_treatment': TREATMENT, 'sandbox_operations_max': 14,
                'comparison_operations_max': 12, 'pilot_operations_max': 1, 'bootstrap_operations_max': 1,
                'in_service_inference_max': 0, 'assist_provider_calls_max': 1,
                'assist_role': 'HINT', 'assist_input_bytes_max': 8192, 'assist_output_tokens_max': 1024,
                'assist_deadline_seconds': 20, 'assist_input_usd_per_million': '0.06',
                'assist_output_usd_per_million': '0.24', 'assist_projected_usd_ceiling': '0.01',
                'pricing_source': 'https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference',
                'sandbox_charge': 'unverified; no zero total-cost claim', 'spawn_timeout_seconds': 45,
                'layer_bytes_max': 16777216, 'captures_max': 20, 'comparison_slots': 6,
                'comparison_requests': 18, 'selected_candidate': 'B only if independently eligible',
                'output_destination': str(LIVE_OUT.relative_to(ROOT)).replace('\\', '/'),
                'retries': 'none; stop on any failed phase, no new reservation or top-up'}
    return {'manifest': manifest, 'manifest_sha256': sha(canonical.canonical_bytes(manifest))}

def checked(client, receipt, method, path, expected=200, **kwargs):
    response = client.request(method, path, **kwargs)
    payload = response.json()
    needles = (*orchestrator._private_public_needles(), *(os.environ.get(k, '') for k in ('NEBIUS_API_KEY', 'NEBIUS_PROJECT_ID')))
    if any(n and serialized_contains(payload, n) for n in needles):
        raise RuntimeError('endpoint failed public privacy')
    receipt['http'].append({'method': method, 'path': path, 'status': response.status_code, 'body': payload})
    assert response.status_code == expected, f'{method} {path}: expected {expected}, got {response.status_code}'
    return payload

def freeze(client, receipt, shift_id, label, contract):
    files = candidate_files(label)
    checked(client, receipt, 'PUT', f'/api/shifts/{shift_id}/artifact', json={'files': files})
    frozen = checked(client, receipt, 'POST', f'/api/shifts/{shift_id}/artifact/versions', 201, json={'contract': contract})
    return frozen

def adapters(bootstrap_meter, *, offline):
    base = orchestrator.TokenFactoryAdapter
    if offline:
        class FixtureAdapter:
            name = 'tokenfactory'
            def __init__(self, **kwargs):
                self.meter = kwargs.get('live_budget') or bootstrap_meter
            async def execute(self, request):
                self.meter.before_operation()
                snapshot = request.artifact_snapshot
                fixture_hash = canonical.content_hash({n: base64.b64encode(b).decode() for n, b in snapshot.files.items()})
                config.TRUSTED_LOCAL_FIXTURES['completion-offline-' + snapshot.manifest_hash] = (snapshot.manifest_hash, fixture_hash)
                local = request.model_copy(update={'harness_ref': 'stdlib-loopback-v1', 'image_ref': 'local-python-stdlib'})
                return await LocalProcessAdapter().execute(local)
        return FixtureAdapter
    class BoundedAdapter(base):
        def __init__(self, **kwargs):
            kwargs.setdefault('live_budget', bootstrap_meter)
            super().__init__(**kwargs)
    return BoundedAdapter

def run(out, *, packet, offline=False):
    out.mkdir(parents=True, exist_ok=False)
    (out / 'once.marker').write_text('One new packet only. Any failure consumes the phase. Never retry.\n')
    (out / 'packet.json').write_text(json.dumps(packet, indent=2), encoding='utf-8')
    for label in ('A', 'B'):
        folder = out / ('candidate-' + label)
        folder.mkdir()
        for name, content in candidate_files(label).items():
            (folder / name).write_text(content, encoding='utf-8', newline='')
    comparison_meter = NoInferenceComparisonBudget(MODEL, Decimal('0'), Decimal('0'))
    pilot_meter = NoInferenceOperationBudget(MODEL, Decimal('0'), Decimal('0'))
    bootstrap_meter = NoInferenceOperationBudget(MODEL, Decimal('0'), Decimal('0'))
    comparison_meter.preflight(model=MODEL, slots=6, requests=18)
    for meter in (pilot_meter, bootstrap_meter):
        meter.preflight(model=MODEL, requests=1)
    class RecordedHint:
        def generate(self, **kwargs):
            return AssistReply('Recorded control: verify both dependencies before final confirmation; inspect matching action receipts.', reported_model_id='recorded-control')
    hint = OneHintGateway(RecordedHint() if offline else LiveAssistGateway(os.environ['NEBIUS_API_KEY']))
    original_adapter, original_pins = orchestrator.TokenFactoryAdapter, dict(config.TRUSTED_LOCAL_FIXTURES)
    saved_env = {k: os.environ.get(k) for k in ('NEBIUS_API_KEY', 'NEBIUS_PROJECT_ID')}
    receipt = {'status': 'INCOMPLETE', 'proof_scope': 'TRUSTED_LOCAL_TEST_DOUBLE' if offline else 'LIVE',
               'candidate_authorship': packet['manifest']['candidate_authorship'], 'http': []}
    source_before = sha(SOURCE.read_bytes())
    try:
        if offline:
            os.environ['NEBIUS_API_KEY'] = 'TEST_ONLY_NO_PROVIDER'
            os.environ['NEBIUS_PROJECT_ID'] = 'aiproject-TEST_ONLY_NO_PROVIDER'
        orchestrator.TokenFactoryAdapter = adapters(bootstrap_meter, offline=offline)
        path = out / 'journey.db'
        shutil.copyfile(SOURCE, path)
        with TestClient(create_app(str(path), executor='tokenfactory', live_comparison_budget=comparison_meter,
                                   live_operation_budget=pilot_meter, assist_gateway=hint)) as client:
            shift_id = 'northline-shift-01'
            before_board = checked(client, receipt, 'GET', '/api/engagements/northline/board')
            prior = before_board['operating_selection']
            investigation = checked(client, receipt, 'POST', f'/api/shifts/{shift_id}/investigations', 201, json={
                'source_run_id': 'run-0001', 'source_request_ordinal': 1,
                'cause': 'The blank service has no required booking result and performs no resource action.',
                'falsifier': 'The captured blank result already contains an independently verified final commitment.',
                'public_test': 'Compare current dependency reads, final writes and retry receipts for the public requests.',
                'client_request_id': 's22b-completion-investigation'})
            versions = {label: freeze(client, receipt, shift_id, label, packet['manifest']['contract']) for label in ('A', 'B')}
            for label in ('A', 'B'):
                assert versions[label]['content_hash'] == packet['manifest']['candidates'][label]['artifact_content_hash']
            with closing(readonly(path)) as conn:
                before_business = business(conn)
            created = checked(client, receipt, 'POST', f'/api/shifts/{shift_id}/experiments', 202, json={
                'kind': 'QUALIFYING_COMPARISON', 'investigation_id': investigation['id'],
                'candidate_a_version_id': versions['A']['id'], 'candidate_b_version_id': versions['B']['id'],
                'declared_treatment': TREATMENT, 'client_request_id': 's22b-completion-comparison'})
            view = checked(client, receipt, 'GET', f'/api/experiments/{created["id"]}')
            assert view['state'] == 'FINALIZED' and view['outcome']['status'] == 'COMPLETE'
            assert len(view['trials']) == 6 and all(t['state'] == 'COMPLETE' for t in view['trials'])
            assert all(e['eligible'] for e in view['outcome']['eligibility'])
            assert comparison_meter.operations == 12 and comparison_meter.calls == 0
            action_counts = {}
            with closing(readonly(path)) as conn:
                assert business(conn) == before_business, 'comparison wrote business history'
                for trial in view['trials']:
                    actions = [a.kind for ordinal in (1, 2) for a in repo.get_deployment_trace(conn, trial['run_id'], ordinal).actions]
                    action_counts[f'{trial["candidate_label"]}{trial["pair_ordinal"]}'] = actions
                assert action_counts['A1'] == ['READ', 'WRITE_SLOT', 'READ', 'ROLLBACK', 'WRITE_SLOT']
                assert action_counts['B1'] == ['READ', 'READ', 'WRITE_SLOT']
            receipt.update(comparison=view, public_action_kinds=action_counts, experimental_business_unchanged=True)
            # One real public hint is attributable to the authored investigation.
            event = checked(client, receipt, 'POST', f'/api/shifts/{shift_id}/assist', json={
                'investigation_id': investigation['id'], 'role': 'HINT',
                'message': 'One hint about evidence needed to falsify my cause; do not give a worked repair.',
                'client_request_id': 's22b-completion-hint'})
            assert event['state'] == 'COMPLETE' and event['role'] == 'HINT' and event['proposed_patch'] is None
            checked(client, receipt, 'POST', f'/api/shifts/{shift_id}/assist', 409, json={
                'investigation_id': investigation['id'], 'role': 'HINT', 'message': 'Second hint control.',
                'client_request_id': 's22b-completion-second-hint-refused'})
            assert hint.calls == 1
            selected = checked(client, receipt, 'POST', f'/api/shifts/{shift_id}/selections', 201, json={
                'comparison_id': view['id'], 'selected_version_id': versions['B']['id'],
                'expected_prior_selection_id': prior['id'], 'client_request_id': 's22b-completion-choice',
                'rationale': 'Operator verification choice: both pass; B avoids the provisional write and rollback. No latency superiority or learner-authorship claim.'})
            checked(client, receipt, 'POST', f'/api/shifts/{shift_id}/runs', 409, json={'client_request_id': 's22b-completion-first-shift-refusal'})
            checked(client, receipt, 'POST', f'/api/shifts/{shift_id}/close')
            next_shift = checked(client, receipt, 'POST', '/api/engagements/northline/shifts', 201)
            inherited = checked(client, receipt, 'GET', f'/api/shifts/{next_shift["id"]}/artifact')
            assert inherited['files'] == candidate_files('B'), 'next shift did not inherit every selected file'
            started = checked(client, receipt, 'POST', f'/api/shifts/{next_shift["id"]}/runs', 202, json={'client_request_id': 's22b-completion-pilot'})
            pilot = checked(client, receipt, 'GET', f'/api/runs/{started["id"]}')
            assert pilot['state'] == 'FINALIZED' and pilot['evidence_mode'] == 'ISOLATED_LIVE'
            assert pilot['artifact_version_id'] == selected['selected_version_id'] == versions['B']['id']
            checked(client, receipt, 'GET', f'/api/runs/{pilot["id"]}/outputs')
            checked(client, receipt, 'GET', f'/api/runs/{pilot["id"]}/checks')
            checked(client, receipt, 'POST', f'/api/shifts/{next_shift["id"]}/close')
            ledger = checked(client, receipt, 'GET', '/api/engagements/northline/ledger')
            with closing(readonly(path)) as conn:
                events = repo.list_ledger_events(conn, 'northline')
                assert sum(e.event_type.value == 'ROLLOUT_APPROVED' for e in events) == 1
                assert sum(e.event_type.value == 'BOOKING_COMMITTED' for e in events) == 1
                assert sum(e.event_type.value == 'HANDOVER_DECLARED' and e.cause_refs[0] == next_shift['id'] for e in events) == 1
                handover = next(e for e in events if e.event_type.value == 'HANDOVER_DECLARED' and e.cause_refs[0] == next_shift['id'])
                assert handover.payload['runbook_version_id'] == selected['selected_version_id']
                assert orchestrator.replay_assessment(conn, pilot['id']).status == 'IDENTICAL'
                assert chain.verify_chain(events).value == 'VALID'
            receipt.update(selected=selected, pilot=pilot, ledger=ledger, inherited_all_selected_files=True,
                           pilot_replay='IDENTICAL', chain='VALID', hint=event)
        # Construct a distinct representative old Northline database with no source run.
        legacy = out / 'legacy.db'
        create_v5_sample(legacy, with_run=False)
        with sqlite3.connect(legacy) as conn:
            for table, field in (('engagements', 'slug'), ('engagement_config', 'slug'), ('shifts', 'engagement_slug')):
                conn.execute('UPDATE ' + table + ' SET ' + field + "='northline'")
            tables = ('artifact_versions', 'draft_artifacts', 'shifts')
            columns = {t: ','.join(row[1] for row in conn.execute('PRAGMA table_info(' + t + ')')) for t in tables}
            old_rows = {t: conn.execute('SELECT ' + columns[t] + ' FROM ' + t).fetchall() for t in tables}
        with TestClient(create_app(str(legacy), executor='tokenfactory', live_operation_budget=bootstrap_meter)) as client:
            opened = checked(client, receipt, 'POST', '/api/engagements/northline/shifts', 201)
            sid = opened['id']
            assert opened['opening_mode'] == 'LEGACY_FIRST_CHOICE' and opened['operation_allowed'] is False
            with closing(readonly(legacy)) as conn:
                assert repo.count_operating_selections(conn) == 0
                assert conn.execute('SELECT COUNT(*) FROM runs').fetchone()[0] == 0
                for table in tables:
                    rows = [tuple(row) for row in conn.execute('SELECT ' + columns[table] + ' FROM ' + table)]
                    assert all(row in rows for row in old_rows[table]), 'legacy migration rewrote original bytes'
                initial_business = business(conn)
            version = freeze(client, receipt, sid, 'B', packet['manifest']['contract'])
            boot = checked(client, receipt, 'POST', f'/api/shifts/{sid}/experiments', 202, json={
                'kind': 'DIAGNOSTIC', 'investigation_id': None, 'candidate_a_version_id': version['id'],
                'client_request_id': 's22b-completion-v5-bootstrap'})
            projection = checked(client, receipt, 'GET', f'/api/experiments/{boot["id"]}')
            assert projection['state'] == 'FINALIZED' and projection['investigation_id'] is None and projection['eligible'] is False
            assert projection['trials'][0]['state'] == 'COMPLETE'
            with closing(readonly(legacy)) as conn:
                assert business(conn) == initial_business, 'bootstrap wrote business history'
                run = repo.get_run(conn, projection['trials'][0]['run_id'])
                context = repo.get_execution_context(conn, run.context_id)
                assert context.protected_reservation_id is None and repo.count_operating_selections(conn) == 0
                orchestrator.admit_pack('northline')
                from shiftwork.packs import registry
                owning = registry.resolve_pack('northline')
                assert base64.b64decode(context.workloads[0].request_batch_bytes_base64) == (config.PACKAGE_DIR / owning.incident_request_path).read_bytes()
            checked(client, receipt, 'POST', f'/api/shifts/{sid}/experiments', 409, json={
                'kind': 'DIAGNOSTIC', 'investigation_id': None, 'candidate_a_version_id': version['id'],
                'client_request_id': 's22b-completion-v5-second-refused'})
            checked(client, receipt, 'POST', f'/api/shifts/{sid}/runs', 409, json={'client_request_id': 's22b-completion-v5-operation-refused'})
            checked(client, receipt, 'POST', f'/api/shifts/{sid}/close', 409)
            receipt.update(bootstrap=projection, original_v5_rows_preserved=True, bootstrap_business_unchanged=True)
        assert pilot_meter.operations == bootstrap_meter.operations == 1
        assert sum(m.calls for m in (comparison_meter, pilot_meter, bootstrap_meter)) == 0
        receipt['status'] = 'PASS'
    finally:
        receipt.update(adapter_operation_attempts={'comparison': comparison_meter.operations, 'pilot': pilot_meter.operations, 'bootstrap': bootstrap_meter.operations},
                       live_operations=0 if offline else comparison_meter.operations + pilot_meter.operations + bootstrap_meter.operations,
                       in_service_inference_calls=sum(m.calls for m in (comparison_meter, pilot_meter, bootstrap_meter)), assist_provider_calls=0 if offline else hint.calls,
                       recorded_hint_calls=hint.calls if offline else 0, source_database_unchanged=sha(SOURCE.read_bytes()) == source_before)
        orchestrator.TokenFactoryAdapter = original_adapter
        config.TRUSTED_LOCAL_FIXTURES.clear()
        config.TRUSTED_LOCAL_FIXTURES.update(original_pins)
        if offline:
            for key, value in saved_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        needles = (*orchestrator._private_public_needles(), *(os.environ.get(k, '') for k in ('NEBIUS_API_KEY', 'NEBIUS_PROJECT_ID')))
        if any(n and serialized_contains(receipt, n) for n in needles):
            raise RuntimeError('completion receipt failed privacy; retain databases only')
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        assert receipt['source_database_unchanged'], 'consumed source database changed'
    print(json.dumps({k: receipt[k] for k in ('status', 'proof_scope', 'live_operations', 'assist_provider_calls', 'adapter_operation_attempts')}))

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
        parser.error('fresh --out is required')
    if args.execute:
        if args.approved_manifest_sha256 != packet['manifest_sha256']:
            raise RuntimeError('explicit approval must bind these exact packet bytes')
        if args.out.resolve() != LIVE_OUT or args.out.exists():
            raise RuntimeError('live destination differs or was consumed')
        load_authorized_credentials()
    run(args.out.resolve(), packet=packet, offline=args.offline_rehearsal)

if __name__ == '__main__':
    main()
