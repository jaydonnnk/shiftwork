"""Fail-capable controls for the new separately authorized completion runner."""
import json
import sys
import types
from decimal import Decimal
import pytest
from demos import slice22b_live_completion as packet
from demos.slice22b_completion_candidates import candidate_files
from shiftwork import config
from shiftwork.assist.gateway import AssistRejected, AssistReply
from shiftwork.domain.models import AssistRole
from shiftwork.executor.deployment import DeploymentKernel

def service(label):
    module = types.ModuleType('verification_' + label)
    exec(compile(candidate_files(label)['service.py'], 'service.py', 'exec'), module.__dict__)
    return module

def test_candidate_tradeoff_and_retry_use_real_resource_actions():
    state = (config.FIXTURE_DIR / 'state/northline_compare_state_v1.json').read_bytes()
    requests = [json.loads(line) for line in (config.FIXTURE_DIR / 'requests/northline_compare_pair_01.jsonl').read_bytes().splitlines()]
    for label, kinds in (('A', ['READ', 'WRITE_SLOT', 'READ', 'ROLLBACK', 'WRITE_SLOT']), ('B', ['READ', 'READ', 'WRITE_SLOT'])):
        candidate = service(label)
        kernel = DeploymentKernel(state, {'state_hash': packet.sha(state), 'allowed_resources': ['parts_availability', 'mechanic_schedule', 'repair_slots']})
        references = []
        for ordinal, request in enumerate(requests, 1):
            token = str(ordinal) * 64
            body = json.dumps(request).encode()
            kernel.begin(ordinal, body, token)
            answer = candidate.respond(request, candidate.received_intent(request), lambda op: kernel.act(token, op))
            trace = kernel.finish(json.dumps(answer).encode())
            assert [a['kind'] for a in trace['actions']] == (kinds if ordinal == 1 else [])
            references.append(answer['task_results'][0]['commitment_ref'])
        assert references[0] == references[1] and references[0]
        assert sum(w['stage'] == 'FINAL' and not w['rolled_back'] for w in kernel.writes) == 1

@pytest.mark.parametrize('text', ['counter intent a counter intent b', 'counter intent !', 'visit V-11 counter intent other'])
def test_candidate_rejects_ambiguous_received_intent(text):
    with pytest.raises(ValueError):
        service('B').received_intent({'request_id': 'delivery', 'text': text})

def test_one_hint_wrapper_consumes_failure_and_blocks_second_call():
    class FailingProvider:
        calls = 0
        def generate(self, **kwargs):
            self.calls += 1
            raise AssistRejected('ASSIST_TRANSPORT_FAILED')
    provider = FailingProvider()
    gateway = packet.OneHintGateway(provider)
    for _ in range(2):
        with pytest.raises(AssistRejected):
            gateway.generate(model_id=packet.MODEL, role=AssistRole.HINT, prompt='Public-only test')
    assert gateway.calls == provider.calls == 1

@pytest.mark.parametrize('model,role', [('unapproved-model', AssistRole.HINT), (packet.MODEL, AssistRole.PATCH_PROPOSAL)])
def test_one_hint_wrapper_refuses_before_provider(model, role):
    class Trap:
        def generate(self, **kwargs):
            pytest.fail('unapproved provider call')
    gateway = packet.OneHintGateway(Trap())
    with pytest.raises(AssistRejected):
        gateway.generate(model_id=model, role=role, prompt='Public-only test')
    assert gateway.calls == 0

def test_zero_inference_comparison_and_pilot_meters():
    for meter in (packet.NoInferenceComparisonBudget(packet.MODEL, Decimal('0'), Decimal('0')),
                  packet.NoInferenceOperationBudget(packet.MODEL, Decimal('0'), Decimal('0'))):
        with pytest.raises(ValueError):
            meter.before_inference(packet.MODEL)
        assert meter.calls == 0

def test_wrong_approval_refuses_before_credentials_and_destination(monkeypatch, tmp_path):
    destination = tmp_path / 'wrong-approval'
    monkeypatch.setattr(packet, 'preflight', lambda: {'manifest_sha256': 'exact'})
    monkeypatch.setattr(packet, 'load_authorized_credentials', lambda: pytest.fail('unapproved credentials'))
    monkeypatch.setattr(sys, 'argv', ['runner', '--execute', '--out', str(destination), '--approved-manifest-sha256', 'wrong'])
    with pytest.raises(RuntimeError, match='explicit approval must bind'):
        packet.main()
    assert not destination.exists()

def test_http_projection_failure_cannot_print_pass(monkeypatch):
    monkeypatch.setattr(packet.orchestrator, '_private_public_needles', lambda: ())
    class Response:
        status_code = 409
        def json(self):
            return {'detail': 'failed projection'}
    class Client:
        def request(self, *args, **kwargs):
            return Response()
    receipt = {'http': []}
    with pytest.raises(AssertionError, match='expected 200, got 409'):
        packet.checked(Client(), receipt, 'GET', '/api/experiments/test')
    assert receipt['http'][0]['status'] == 409

@pytest.mark.parametrize('comparison,ordinals,operation_count', [(True, (1, 2, 3), 2), (False, (1,), 1)])
def test_live_audit_counts_request_meters_separately_from_operations(comparison, ordinals, operation_count):
    from demos.slice22b_completion_audit import verify_live_meters
    meters = [types.SimpleNamespace(request_ordinal=i, public_payload_json={'service_calls': 0}) for i in ordinals]
    verify_live_meters(meters, [object()] * operation_count, ordinals, comparison=comparison)

@pytest.mark.parametrize('fault', ['duplicate_meter', 'duplicate_ordinal', 'extra_operation', 'inference'])
def test_live_audit_rejects_incomplete_meter_or_operation_evidence(fault):
    from demos.slice22b_completion_audit import verify_live_meters
    meters = [types.SimpleNamespace(request_ordinal=i, public_payload_json={'service_calls': 0}) for i in (1, 2, 3)]
    bounds = [object(), object()]
    if fault == 'duplicate_meter':
        meters.append(meters[-1])  # Ordinal coverage stays complete; isolate count.
    elif fault == 'duplicate_ordinal':
        meters[1].request_ordinal = 1
    elif fault == 'extra_operation':
        bounds.append(object())
    else:
        meters[1].public_payload_json['service_calls'] = 1
    with pytest.raises(AssertionError):
        verify_live_meters(meters, bounds, (1, 2, 3), comparison=True)
