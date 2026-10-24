"""Private diagnostics retain safe categories, never provider exception text."""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from shiftwork.gateway import service_inference
from shiftwork.gateway.protocol import InferencePolicy
from shiftwork.gateway.redaction import assert_public_safe, serialized_contains


@pytest.mark.parametrize('error_type, category', [
    (TimeoutError, 'deadline'),
    (httpx.ConnectTimeout, 'connect_timeout'),
    (httpx.ReadTimeout, 'read_timeout'),
    (httpx.WriteTimeout, 'write_timeout'),
    (httpx.PoolTimeout, 'pool_timeout'),
    (httpx.TimeoutException, 'httpx_timeout'),
    (httpx.ConnectError, 'request_error'),
])
def test_transport_failure_keeps_safe_private_category_and_elapsed_time(monkeypatch, error_type, category):
    needles = ('PRIVATE_TEST_TOKEN', '/private/controller/example', 'PRIVATE_REQUEST_HEADER')

    class FailedHTTP:
        calls = 0

        async def post(self, *_args, **_kwargs):
            self.calls += 1
            raise error_type(' '.join(needles))

    http = FailedHTTP()
    bound = service_inference.ServiceInferenceGateway(needles[0], InferencePolicy(
        run_id='test', operation_id='test', model='test', allowed_tool_names=('public_record_lookup',)), http=http)
    clock = iter((100.0, 100.0, 100.125))
    monkeypatch.setattr(service_inference, 'time', SimpleNamespace(monotonic=lambda: next(clock)))
    bound._expires_at = 120.0
    with pytest.raises(service_inference.GatewayRejected, match='^PROVIDER_TRANSPORT_FAILED$'):
        asyncio.run(bound.infer('test', {'request_ordinal': 1, 'input_text': 'Public customer request'}))

    _kind, public, private = bound.observations[-1]
    assert private.get('transport_failure') == {'category': category, 'elapsed_ms': 125}, 'private transport category and measured failure duration must survive'
    assert public == {'source': 'controller_verified', 'failure': 'PROVIDER_TRANSPORT_FAILED'}, 'private transport details must not change the public failure contract'
    assert private['provider_request']['messages'] == [{'role': 'user', 'content': 'Public customer request'}]
    assert http.calls == bound.call_count == 1, 'a failed provider request consumes exactly one call without retry'
    # Prove every sensitive needle matches the serialized scanner input first.
    for needle in needles:
        with pytest.raises(ValueError):
            assert_public_safe(json.loads(json.dumps({'message': needle})), needles)
    assert not any(serialized_contains(bound.observations, needle) for needle in needles), 'provider exception text must never reach retained records'
    assert_public_safe(json.loads(json.dumps(bound.observations)), needles)


def test_real_deadline_keeps_private_cause_and_duration():
    class WaitingHTTP:
        async def post(self, *_args, **_kwargs):
            await asyncio.Event().wait()

    bound = service_inference.ServiceInferenceGateway('TEST_ONLY', InferencePolicy(
        run_id='test', operation_id='test', model='test', allowed_tool_names=('public_record_lookup',), deadline_s=0.02), http=WaitingHTTP())
    with pytest.raises(service_inference.GatewayRejected, match='^PROVIDER_TRANSPORT_FAILED$'):
        asyncio.run(bound.infer('test', {'request_ordinal': 1, 'input_text': 'Public request'}))
    detail = bound.observations[-1][2].get('transport_failure', {})
    assert detail.get('category') == 'deadline', 'actual total-deadline expiry must retain its cause'
    assert type(detail.get('elapsed_ms')) is int and detail['elapsed_ms'] >= 10, 'actual failed provider wait must retain elapsed milliseconds'
    assert bound.call_count == 1


def test_invalid_model_plan_returns_plan_failure_instead_of_transport_error():
    class InvalidPlanHTTP:
        async def post(self, *_args, **_kwargs):
            return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({
                'plan': [{'task_type': 'conditional_alternative', 'tool_name': 'public_catalog_search'}]})}, 'finish_reason': 'stop'}]}, request=httpx.Request('POST', 'https://example.invalid'))

    bound = service_inference.ServiceInferenceGateway('TEST_ONLY', InferencePolicy(
        run_id='test', operation_id='test', model='test', allowed_tool_names=('public_catalog_search',), task_vocabulary=('alternative',)), http=InvalidPlanHTTP())
    error = None
    reply = None
    try:
        reply = asyncio.run(bound.infer('test', {'request_ordinal': 1, 'input_text': 'Public request'}))
    except service_inference.GatewayRejected as exc:
        error = exc.code
    assert error is None, 'an invalid model plan must return evidence, not become a transport exception'
    assert reply == {'kind': 'inference_reply', 'plan': None, 'plan_failure': 'TASK_TYPE_UNKNOWN'}
    assert bound.call_count == 1
