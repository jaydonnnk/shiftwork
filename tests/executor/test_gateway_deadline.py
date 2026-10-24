"""The 20-second gateway ceiling is a total wait, not separate HTTP phase caps."""

import asyncio
import json

import httpx
import pytest

from shiftwork.gateway import service_inference
from shiftwork.gateway.protocol import InferencePolicy


@pytest.mark.parametrize('client_source', ['injected', 'owned'])
def test_provider_wait_has_an_absolute_deadline_and_consumes_its_call(monkeypatch, client_source):
    class WaitingHTTP:
        calls = 0
        cancelled = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, *_args, **_kwargs):
            self.calls += 1
            try:
                await asyncio.Event().wait()
            finally:
                self.cancelled = True

    http = WaitingHTTP()
    monkeypatch.setattr(service_inference.httpx, 'AsyncClient', lambda **_kwargs: http)
    policy = InferencePolicy(run_id='test-run', operation_id='test-operation', model='test-model',
        allowed_tool_names=('public_record_lookup',), deadline_s=0.02)
    bound = service_inference.ServiceInferenceGateway('test-only-token', policy,
        http=http if client_source == 'injected' else None)

    async def result():
        try:
            await asyncio.wait_for(bound.infer('test-operation', {'request_ordinal': 1, 'input_text': 'public input'}), timeout=0.25)
        except service_inference.GatewayRejected as error:
            return error.code
        except TimeoutError:
            return 'OUTER_TEST_LIMIT_ONLY'

    assert asyncio.run(result()) == 'PROVIDER_TRANSPORT_FAILED', 'the gateway must enforce its own total provider deadline'
    assert http.calls == bound.call_count == 1 and http.cancelled, 'deadline expiry must cancel the only provider wait'
    assert bound.observations[-1][1]['failure'] == 'PROVIDER_TRANSPORT_FAILED'
    assert bound.observations[-1][2]['provider_request']['messages'] == [{'role': 'user', 'content': 'public input'}]


def test_real_httpx_trickling_local_reply_cannot_outlive_the_total_deadline(monkeypatch):
    async def local_control():
        handlers = set()

        async def serve(reader, writer):
            handlers.add(asyncio.current_task())
            try:
                headers = await reader.readuntil(b'\r\n\r\n')
                size = int(next(line.split(b':', 1)[1] for line in headers.split(b'\r\n') if line.lower().startswith(b'content-length:')))
                await reader.readexactly(size)
                body = json.dumps({'choices': [{'message': {'content': 'public_record_lookup'}, 'finish_reason': 'stop'}],
                    'usage': {'prompt_tokens': 1, 'completion_tokens': 1}}).encode()
                writer.write(b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(body)).encode() + b'\r\nConnection: close\r\n\r\n')
                # Each read arrives within HTTPX's 150 ms idle timeout, but the
                # whole response takes longer than the gateway's 150 ms ceiling.
                for offset in range(0, len(body), 16):
                    writer.write(body[offset:offset + 16])
                    await writer.drain()
                    await asyncio.sleep(0.03)
            except ConnectionError:
                pass
            finally:
                writer.close()
                await writer.wait_closed()

        async with await asyncio.start_server(serve, '127.0.0.1', 0) as server:
            port = server.sockets[0].getsockname()[1]
            monkeypatch.setattr(service_inference, 'PROVIDER_URL', f'http://127.0.0.1:{port}/authored-local-control')
            async with httpx.AsyncClient(timeout=0.15, trust_env=False) as http:
                policy = InferencePolicy(run_id='local-test', operation_id='local-test', model='authored-local-reply',
                    allowed_tool_names=('public_record_lookup',), deadline_s=0.15)
                bound = service_inference.ServiceInferenceGateway('test-only-token', policy, http=http)
                try:
                    await bound.infer('local-test', {'request_ordinal': 1, 'input_text': 'authored local control'})
                    result = 'REPLY_RETURNED_AFTER_TOTAL_DEADLINE'
                except service_inference.GatewayRejected as error:
                    result = error.code
            await asyncio.gather(*handlers, return_exceptions=True)
            return result, bound.call_count

    assert asyncio.run(local_control()) == ('PROVIDER_TRANSPORT_FAILED', 1), 'a real trickling HTTP reply must stop at the total deadline'
