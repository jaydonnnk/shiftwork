"""Read-only frozen capture and assessment audit for the completion packet."""
import argparse
import base64
from contextlib import closing
import json
import os
from pathlib import Path
import socket
import sys

from demos.slice22b_live_completion import SOURCE, readonly, sha
from demos.slice22b_live_starter import load_authorized_credentials
from shiftwork import orchestrator
from shiftwork.domain import canonical, task_contract
from shiftwork.evaluator import evaluator
from shiftwork.executor.base import BatchRef, load_batch, load_single_request
from shiftwork.gateway.redaction import serialized_contains
from shiftwork.sealed import store as sealed_store
from shiftwork.store import repo

def verify_live_meters(meters, bounds, output_ordinals, *, comparison):
    # Inference gateways close per request; Sandbox instances bind per phase.
    assert len(meters) == len(output_ordinals), 'missing or duplicate per-request inference meters'
    assert {o.request_ordinal for o in meters} == set(output_ordinals), 'inference meter request coverage differs'
    assert len(bounds) == (2 if comparison else 1), 'Sandbox operation binding count differs'
    assert all(o.public_payload_json['service_calls'] == 0 for o in meters), 'in-service inference occurred'

def audit(directory):
    receipt = json.loads((directory / 'receipt.json').read_bytes())
    packet = json.loads((directory / 'packet.json').read_bytes())
    assert receipt['status'] == 'PASS'
    assert sha(canonical.canonical_bytes(packet['manifest'])) == packet['manifest_sha256']
    is_live = receipt['proof_scope'] == 'LIVE'
    assert receipt['live_operations'] == (14 if is_live else 0)
    assert receipt['assist_provider_calls'] == (1 if is_live else 0)
    assert receipt['in_service_inference_calls'] == 0
    paths = [directory / 'journey.db', directory / 'legacy.db', SOURCE]
    before = {str(path): sha(path.read_bytes()) for path in paths}
    rows = []
    for filename, run_ids in (
        ('journey.db', [t['run_id'] for t in receipt['comparison']['trials']] + [receipt['pilot']['id']]),
        ('legacy.db', [receipt['bootstrap']['trials'][0]['run_id']]),
    ):
        with closing(readonly(directory / filename)) as conn:
            for run_id in run_ids:
                run = repo.get_run(conn, run_id)
                context = repo.get_execution_context(conn, run.context_id)
                version = repo.get_version(conn, run.artifact_version_id)
                assert run.state.value == 'FINALIZED' and run.evidence_mode.value == 'ISOLATED_LIVE'
                assert version.content_hash in {p['artifact_content_hash'] for p in packet['manifest']['candidates'].values()}
                mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64, validate=True))
                state = base64.b64decode(context.public_data_bytes_base64, validate=True)
                assert sha(state) == context.public_data_hash
                outputs = {o.request_ordinal: o for o in repo.list_outputs(conn, run_id)}
                observations = repo.list_observations(conn, run_id)
                assert not any(o.kind.value.startswith('INFERENCE_') for o in observations)
                traces = [o for o in observations if o.public_payload_json.get('deployment_trace_verified') is True]
                assert len(traces) == len(outputs)
                if is_live:
                    readbacks = [o for o in observations if o.public_payload_json.get('checkpoint_readback') is True]
                    meters = [o for o in observations if o.public_payload_json.get('inference_meter_complete') is True]
                    bounds = [o for o in observations if o.public_payload_json.get('operation_bound') is True]
                    assert len(readbacks) == len(outputs)
                    verify_live_meters(meters, bounds, outputs, comparison=bool(run.trial_slot_id))
                if run.trial_slot_id:
                    slot = repo.get_trial_slot(conn, run.trial_slot_id)
                    workload = next(w for w in context.workloads if w.id == slot.workload_id)
                    specs = tuple(task_contract.CustomerRequestSpec.model_validate(p) for p in json.loads(base64.b64decode(workload.request_specs_bytes_base64)))
                else:
                    workload, specs = context.workloads[0], mission.request_specs
                batch = base64.b64decode(workload.request_batch_bytes_base64, validate=True)
                batch_hash = canonical.content_hash(base64.b64encode(batch).decode())
                assert batch_hash == workload.request_batch_hash
                stimuli = load_batch(BatchRef(path_ref='frozen:public', content_hash=batch_hash), batch)
                limbs = [(stimulus.ordinal, stimulus, spec, state, batch, 'PUBLIC') for stimulus, spec in zip(stimuli, specs, strict=True)]
                if run.trial_slot_id:
                    reserved = next(c for c in sealed_store.load_reserved_comparison_cases(conn, context.protected_reservation_id) if c.pair_ordinal == slot.pair_ordinal)
                    line = task_contract.protected_request_bytes(reserved.case.stimulus.request)
                    ref = BatchRef(path_ref='sealed:protected', content_hash=canonical.content_hash(base64.b64encode(line).decode()))
                    stimulus = load_single_request(ref, line, slot.executed_request_count)
                    limbs.append((slot.executed_request_count, stimulus, reserved.case.stimulus.task_spec, reserved.resolved_state_bytes, line, 'PROTECTED'))
                recomputed = []
                for ordinal, stimulus, spec, state_bytes, batch_bytes, phase in limbs:
                    output = outputs[ordinal]
                    assert output.http_status == 200 and output.transport_error is None
                    trace = repo.get_deployment_trace(conn, run_id, ordinal)
                    observation = next(o for o in traces if o.request_ordinal == ordinal)
                    prefix = 'data:application/json;base64,'
                    assert observation.raw_payload_ref.startswith(prefix)
                    wrapper = json.loads(base64.b64decode(observation.raw_payload_ref[len(prefix):], validate=True))
                    raw = base64.b64decode(wrapper['capture_base64'], validate=True)
                    assert len(raw) == wrapper['byte_count'] and sha(raw) == wrapper['sha256']
                    captured = json.loads(raw)
                    assert captured['deployment_trace'] == trace.model_dump(mode='json')
                    assert base64.b64decode(captured['body_base64'], validate=True) == output.body
                    assert trace.run_id == run_id and trace.context_hash == context.content_hash
                    assert trace.artifact_hash == version.content_hash and trace.state_hash == sha(state_bytes)
                    assert trace.batch_hash == canonical.content_hash(base64.b64encode(batch_bytes).decode())
                    assert trace.phase == phase and trace.request_ordinal == ordinal
                    assert trace.request_id == json.loads(stimulus.body)['request_id']
                    assert trace.request_sha256 == sha(stimulus.body) and trace.response_sha256 == sha(output.body)
                    assert trace.complete
                    if is_live:
                        readback = next(o for o in readbacks if o.request_ordinal == ordinal)
                        assert readback.public_payload_json['capture_sha256'] == sha(raw)
                        assert readback.public_payload_json['capture_bytes'] == len(raw)
                    response = task_contract.validate_response_envelope(spec, output.body)
                    recomputed.extend(evaluator.assess_request(spec=spec, request_ordinal=ordinal, mission=mission,
                        snapshot=task_contract.load_public_state_bytes(state_bytes), response=response,
                        **orchestrator.deployment_assessment_inputs(conn, run, spec, ordinal, state_bytes, batch_bytes, phase=phase, require_complete=True)))
                    # Protected request content/identities remain private. Only digests are retained here.
                    rows.append({'database': filename, 'run_id': run_id, 'ordinal': ordinal, 'phase': phase,
                                 'capture_sha256': sha(raw), 'capture_bytes': len(raw), 'bindings_verified': 10})
                stored = repo.list_task_assessment_models(conn, run_id)
                key = lambda a: (a.request_ordinal, a.task_id)
                assert [a.model_dump(mode='json') for a in sorted(recomputed, key=key)] == [a.model_dump(mode='json') for a in sorted(stored, key=key)]
                assert all(a.mandatory_pass for a in recomputed)
            assert conn.total_changes == 0
    assert len(rows) == 20
    if is_live:
        load_authorized_credentials()
    sys.path.insert(0, str(Path.cwd() / 'tests'))
    from leakscan import sealed_identity_strings
    needles = set((*orchestrator._private_public_needles(), *sealed_identity_strings(),
                   *(os.environ.get(k, '') for k in ('NEBIUS_API_KEY', 'NEBIUS_PROJECT_ID')))) - {''}
    for needle in needles:
        forms = (needle, needle.replace('\\', '/'), json.dumps(needle)[1:-1], base64.b64encode(needle.encode()).decode())
        assert all(serialized_contains({'control': form}, needle) for form in forms)
        assert not serialized_contains(receipt, needle)
    assert all(sha(path.read_bytes()) == before[str(path)] for path in paths)
    report = {'status': 'PASS', 'proof_scope': 'READ_ONLY_AUDIT_OF_' + receipt['proof_scope'], 'captures': rows,
              'assessment_recomputation': 'IDENTICAL', 'privacy_needles': len(needles), 'forms_per_needle': 4,
              'database_bytes_unchanged': True, 'database_rows_written': 0, 'outbound_connections': 0}
    with (directory / 'audit.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != 'captures'}))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    def refuse_network(*args, **kwargs):
        raise AssertionError('read-only capture audit attempted a network connection')
    socket.socket.connect = refuse_network
    socket.create_connection = refuse_network
    audit(args.directory.resolve())

if __name__ == '__main__':
    main()
