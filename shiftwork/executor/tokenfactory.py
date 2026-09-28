"""One disposable learner service run with controller-mediated inference.

The host owns the provider key and operation ID. A root-owned driver inside the
network-disabled Sandbox runs learner code as an unprivileged child, serves only
the frozen public lookup policy on loopback, and writes a capture file. The host
downloads that file from the checkpoint and verifies its bytes before accepting
the response. No Sandbox status or stdout claim substitutes for readback.
"""

from __future__ import annotations

import asyncio
import base64
import dataclasses
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from contree_client.httpx import ContreeAsyncClient
from contree_client.models import ClosableStreamRepr, FileSpec, InstanceNetworking, InstanceResourcesLimits

from shiftwork import config
from shiftwork.domain.models import ExecutorFailure
from shiftwork.executor.base import RawCapture, RawObservation, RunRequest, RunResult, load_batch, load_single_request, provisioning_manifest
from shiftwork.gateway.protocol import InferencePolicy
from shiftwork.gateway.service_inference import GatewayRejected, ServiceInferenceGateway


MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
MAX_BODY_BYTES = 1024 * 1024
MAX_LAYER_BYTES = 16 * 1024 * 1024

# This is controller code uploaded as a root-owned file, not part of the
# learner-editable artifact. The learner process drops to uid/gid 65534 and
# receives only the public shop snapshot and local gateway port.
DRIVER_SOURCE = r'''
import base64
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path('/work')
MAX_BODY = 1024 * 1024
MAX_LOG = 8192
config = json.loads(sys.stdin.readline())
allowed = tuple(config['allowed_tool_names'])
public_state = json.loads((ROOT / 'shop.json').read_bytes())
events = []
infer_lock = threading.Lock()

def send_line(value):
    print(json.dumps(value, separators=(',', ':')), flush=True)

class GatewayHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, value):
        body = json.dumps(value, separators=(',', ':')).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8192:
                return self.reply(413, {'error': 'INPUT_LIMIT'})
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                return self.reply(422, {'error': 'REQUEST_INVALID'})
            if self.path == '/infer':
                if not infer_lock.acquire(blocking=False):
                    return self.reply(429, {'error': 'CALL_LIMIT'})
                try:
                    send_line({'kind': 'inference_request', 'request': body})
                    answer = json.loads(sys.stdin.readline())
                    if answer.get('kind') != 'inference_reply' or answer.get('error'):
                        return self.reply(503, {'error': 'INFERENCE_UNAVAILABLE'})
                    choice = answer.get('selected_tool')
                    if choice not in allowed:
                        return self.reply(403, {'error': 'TOOL_NOT_ALLOWED'})
                    events.append({'kind': 'inference_result', 'selected_tool': choice})
                    return self.reply(200, {'selected_tool': choice})
                finally:
                    infer_lock.release()
            if self.path == '/tool':
                name = body.get('tool')
                if name not in allowed:
                    events.append({'kind': 'tool_rejected', 'tool': str(name)[:80]})
                    return self.reply(403, {'error': 'TOOL_NOT_ALLOWED'})
                if name == 'public_record_lookup':
                    entity = body.get('entity_ref')
                    kind = body.get('record_kind')
                    if not isinstance(entity, str) or not isinstance(kind, str):
                        return self.reply(422, {'error': 'REQUEST_INVALID'})
                    records = [r for r in public_state['records'] if r['entity_ref'] == entity and r['kind'] == kind]
                    events.append({'kind': 'tool_result', 'tool': name, 'record_ids': [r['record_id'] for r in records]})
                    return self.reply(200, {'records': records})
                if name == 'public_catalog_search':
                    genre = body.get('genre')
                    if not isinstance(genre, str):
                        return self.reply(422, {'error': 'REQUEST_INVALID'})
                    entities = [key for key, item in public_state['entities'].items() if item.get('genre') == genre]
                    events.append({'kind': 'tool_result', 'tool': name, 'entity_refs': entities})
                    return self.reply(200, {'entity_refs': entities})
                return self.reply(403, {'error': 'TOOL_NOT_ALLOWED'})
            return self.reply(404, {'error': 'NO_SUCH_OPERATION'})
        except (ValueError, KeyError, UnicodeDecodeError):
            return self.reply(422, {'error': 'REQUEST_INVALID'})

def drop_privileges():
    os.setgroups([])
    os.setgid(65534)
    os.setuid(65534)

def drain(stream, output):
    while True:
        chunk = stream.read(4096)
        if not chunk:
            return
        if len(output) < MAX_LOG:
            output.extend(chunk[:MAX_LOG - len(output)])

server = ThreadingHTTPServer(('127.0.0.1', 0), GatewayHandler)
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()
child = None
stderr = bytearray()
try:
    env = {'PATH': '/usr/local/bin:/usr/bin', 'SHIFTWORK_GATEWAY_PORT': str(server.server_port)}
    child = subprocess.Popen(['/usr/local/bin/python', '-I', '-B', '-u', '/work/service.py'],
        cwd='/work', env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, preexec_fn=drop_privileges)
    threading.Thread(target=drain, args=(child.stderr, stderr), daemon=True).start()
    ready = json.loads(child.stdout.readline())
    port = ready.get('port')
    if type(port) is not int or not 0 < port < 65536:
        raise ValueError('SERVICE_NOT_READY')
    for ordinal in range(1, config['request_count'] + 1):
        if ordinal > 1:
            config = json.loads(sys.stdin.readline())
        if config.get('kind') != 'current_request' or config.get('request_ordinal') != ordinal:
            raise ValueError('REQUEST_ORDER_INVALID')
        events = []
        request_body = base64.b64decode(config['body_base64'], validate=True)
        if not request_body or len(request_body) > 65536:
            raise ValueError('FROZEN_REQUEST_INVALID')
        request_started = time.monotonic()
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=35)
        try:
            connection.request('POST', '/', body=request_body, headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            output = response.read(MAX_BODY + 1)
        finally:
            connection.close()
        if len(output) > MAX_BODY:
            raise ValueError('CAPTURE_LIMIT')
        output.decode('utf-8')
        capture = {
            'request_ordinal': ordinal, 'http_status': response.status,
            'body_base64': base64.b64encode(output).decode('ascii'),
            'elapsed_ms': round((time.monotonic() - request_started) * 1000),
            'driver_events': events, 'service_stderr_base64': base64.b64encode(stderr).decode('ascii'),
        }
        raw = json.dumps(capture, sort_keys=True, separators=(',', ':')).encode()
        with open('/work/capture-%d.json' % ordinal, 'wb') as target:
            target.write(raw)
            target.flush()
            os.fsync(target.fileno())
        send_line({'kind': 'capture_written', 'request_ordinal': ordinal,
                   'byte_count': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
except Exception as exc:
    send_line({'kind': 'driver_failure', 'code': type(exc).__name__})
finally:
    if child is not None:
        child.terminate()
        child.wait(timeout=2)
    server.shutdown()
'''.encode("utf-8")


def _event_text(data: Any) -> str:
    if isinstance(data, dict):
        value = data.get("value", "")
        encoding = data.get("encoding", "ascii")
    else:
        value = getattr(data, "value", "")
        encoding = getattr(data, "encoding", "ascii")
    if encoding == "base64":
        return base64.b64decode(value).decode("utf-8", errors="replace")
    return str(value)


class TokenFactoryAdapter:
    name = "tokenfactory"

    def __init__(self, *, run_id: str, allowed_tool_names: tuple[str, ...], token: str, project: str,
                 model: str = MODEL, client: ContreeAsyncClient | None = None):
        self.run_id = run_id
        self.allowed_tool_names = allowed_tool_names
        self.token = token
        self.project = project
        self.model = model
        self.client = client

    async def execute(self, request: RunRequest) -> RunResult:
        started = time.monotonic()
        observations: list[RawObservation] = []
        captures: list[RawCapture] = []
        operation_id: str | None = None
        client = self.client
        terminal = False
        gateway: ServiceInferenceGateway | None = None

        def failure(kind: ExecutorFailure) -> RunResult:
            return RunResult(captures=tuple(captures), executor_ref=operation_id, failure=kind,
                             wall_ms=round((time.monotonic() - started) * 1000),
                             observations=tuple(observations))

        try:
            if not self.token or not self.project or not self.allowed_tool_names:
                return failure(ExecutorFailure.PROVISION_FAILED)
            if client is None:
                client = ContreeAsyncClient(self.token, project=self.project, timeout=20)
            if (request.harness_ref != "sandbox-driver-v1"
                    or request.image_ref != config.TOKEN_FACTORY_IMAGE):
                return failure(ExecutorFailure.PROVISION_FAILED)
            manifest = provisioning_manifest(request)
            artifact_files = request.artifact_snapshot.files
            if ("service.py" not in artifact_files
                    or {"driver.py", "shop.json", *(f"capture-{n}.json" for n in range(1, 5))} & set(artifact_files)
                    or sum(len(raw) for raw in artifact_files.values()) > MAX_BODY_BYTES):
                return failure(ExecutorFailure.PROVISION_FAILED)
            batch = ((load_single_request(request.request_batch, request.request_batch_bytes,
                                          request.single_request_ordinal),)
                     if request.single_request_ordinal is not None else
                     load_batch(request.request_batch, request.request_batch_bytes))
            if not 1 <= len(batch) <= 4:
                return failure(ExecutorFailure.PROVISION_FAILED)
            shop = Path(request.shop_snapshot_ref).read_bytes()
            if not shop:
                return failure(ExecutorFailure.PROVISION_FAILED)
            files = dict(artifact_files)
            files["shop.json"] = shop
            files["driver.py"] = DRIVER_SOURCE
            uploaded = {}
            for name, raw in files.items():
                uploaded[name] = await client.upload_file(raw)
                if uploaded[name].sha256 != hashlib.sha256(raw).hexdigest():
                    return failure(ExecutorFailure.PROVISION_FAILED)
            spawn_files = {"/work/" + name: FileSpec(uuid=uploaded[name].uuid, mode="0644") for name in files}
            def current_request(ordinal: int) -> dict[str, Any]:
                return {"kind": "current_request", "request_ordinal": ordinal,
                        "body_base64": base64.b64encode(batch[ordinal - 1].body).decode("ascii")}

            initial = {**current_request(1), "request_count": len(batch),
                       "allowed_tool_names": list(self.allowed_tool_names)}
            instance = await client.spawn_instance(
                command="/usr/local/bin/python", image=config.TOKEN_FACTORY_IMAGE,
                args=["-u", "/work/driver.py"],
                disposable=False, networking=InstanceNetworking(enabled=False),
                resources_limits=InstanceResourcesLimits(max_layer_bytes=MAX_LAYER_BYTES),
                stdin=ClosableStreamRepr(value=json.dumps(initial) + "\n", encoding="ascii", close=False),
                files=spawn_files, timeout=45, truncate_output_at=65536,
            )
            operation_id = instance.uuid
            gateway = ServiceInferenceGateway(self.token, InferencePolicy(
                run_id=self.run_id, operation_id=operation_id, model=self.model,
                allowed_tool_names=self.allowed_tool_names, request_ordinal=1,
            ))
            gateway_observations_recorded = False
            observations.append(RawObservation(kind="INTERPRETATION",
                public_payload={"source": "controller_verified", "operation_bound": True,
                                "artifact_sha256": request.artifact_snapshot.manifest_hash,
                                "networking_enabled": False},
                raw_payload={"operation_id": operation_id, "manifest": dataclasses.asdict(instance)
                             if dataclasses.is_dataclass(instance) else {}}))
            seen: int | None = None
            stdout = ""
            processed_lines = 0
            capture_summaries: list[dict[str, Any]] = []
            gateway_failure = False
            while time.monotonic() - started < request.deadline_s:
                batch_events = [event async for event in client.iter_operation_events(
                    operation_id, follow=False, last_event_id=seen)]
                for event in batch_events:
                    seen = event.id
                    if event.type == "stdout":
                        stdout += _event_text(event.data)
                        if len(stdout) > 65536:
                            return failure(ExecutorFailure.CAPTURE_TRUNCATED)
                    if event.type == "completion":
                        terminal = True
                lines = stdout.split("\n")
                while processed_lines < len(lines) - 1:
                    line = lines[processed_lines]
                    processed_lines += 1
                    try:
                        event_body = json.loads(line)
                    except (ValueError, TypeError):
                        return failure(ExecutorFailure.CAPTURE_TRUNCATED)
                    if event_body.get("kind") == "inference_request":
                        try:
                            reply = await gateway.infer(operation_id, event_body.get("request"))
                        except GatewayRejected as exc:
                            gateway_failure = True
                            reply = {"kind": "inference_reply", "error": exc.code}
                        await client.operation_subprocess_stdin(operation_id, 1, json.dumps(reply) + "\n", close=False)
                    elif event_body.get("kind") == "capture_written":
                        ordinal = event_body.get("request_ordinal")
                        if ordinal != len(capture_summaries) + 1 or ordinal > len(batch):
                            return failure(ExecutorFailure.CAPTURE_TRUNCATED)
                        capture_summaries.append(event_body)
                        for kind, public, raw in gateway.observations:
                            observations.append(RawObservation(kind=kind,
                                public_payload={**public, "request_ordinal": gateway.policy.request_ordinal},
                                raw_payload=raw))
                        gateway.close()
                        gateway_observations_recorded = True
                        if ordinal < len(batch):
                            await client.operation_subprocess_stdin(
                                operation_id, 1, json.dumps(current_request(ordinal + 1)) + "\n", close=False
                            )
                            gateway = ServiceInferenceGateway(self.token, InferencePolicy(
                                run_id=self.run_id, operation_id=operation_id, model=self.model,
                                allowed_tool_names=self.allowed_tool_names, request_ordinal=ordinal + 1,
                            ))
                            gateway_observations_recorded = False
                    elif event_body.get("kind") == "driver_failure":
                        observations.append(RawObservation(kind="INTERPRETATION",
                            public_payload={"source": "controller_verified",
                                            "request_ordinal": len(capture_summaries) + 1,
                                            "driver_failure": event_body.get("code")},
                            raw_payload=event_body))
                if terminal:
                    break
                await asyncio.sleep(0.25)
            if gateway is not None and not gateway_observations_recorded:
                for kind, public, raw in gateway.observations:
                    observations.append(RawObservation(kind=kind,
                        public_payload={**public, "request_ordinal": gateway.policy.request_ordinal},
                        raw_payload=raw))
            if not terminal:
                return failure(ExecutorFailure.REQUEST_TIMEOUT)
            status = await client.get_operation_status(operation_id)
            observations.append(RawObservation(kind="USAGE",
                public_payload={"source": "controller_verified", "sandbox_status": str(status.status),
                                "wall_ms": round((time.monotonic() - started) * 1000)},
                raw_payload={"status": dataclasses.asdict(status)}))
            if str(status.status) != "SUCCESS":
                return failure(ExecutorFailure.SANDBOX_TERMINATED)
            checkpoint = status.result_image_uuid
            if not checkpoint:
                return failure(ExecutorFailure.CAPTURE_TRUNCATED)
            for ordinal, summary in enumerate(capture_summaries, start=1):
                try:
                    raw_capture = await client.inspect_image_download(checkpoint, f"/work/capture-{ordinal}.json")
                except (OSError, ValueError):
                    return failure(ExecutorFailure.CAPTURE_TRUNCATED)
                if (not raw_capture or len(raw_capture) != summary.get("byte_count")
                        or hashlib.sha256(raw_capture).hexdigest() != summary.get("sha256")):
                    observations.append(RawObservation(kind="INTERPRETATION",
                        public_payload={"source": "controller_verified", "request_ordinal": ordinal,
                                        "checkpoint_readback": False, "expected_bytes": summary.get("byte_count"),
                                        "actual_bytes": len(raw_capture), "expected_sha256": summary.get("sha256"),
                                        "actual_sha256": hashlib.sha256(raw_capture).hexdigest()}, raw_payload={}))
                    return failure(ExecutorFailure.CAPTURE_TRUNCATED)
                capture = json.loads(raw_capture)
                if capture.get("request_ordinal") != ordinal or not isinstance(capture.get("http_status"), int):
                    return failure(ExecutorFailure.CAPTURE_TRUNCATED)
                body = base64.b64decode(capture["body_base64"], validate=True)
                if not body or len(body) > MAX_BODY_BYTES:
                    return failure(ExecutorFailure.CAPTURE_TRUNCATED)
                body.decode("utf-8")
                observations.append(RawObservation(kind="INTERPRETATION",
                    public_payload={"source": "controller_verified", "request_ordinal": ordinal,
                                    "capture_bytes": len(raw_capture),
                                    "capture_sha256": hashlib.sha256(raw_capture).hexdigest(),
                                    "checkpoint_readback": True}, raw_payload={"checkpoint": checkpoint}))
                for driver_event in capture.get("driver_events", []):
                    name = driver_event.get("kind")
                    kind = ("TOOL_RESULT" if name == "tool_result" else
                            "INTERPRETATION" if name == "inference_result" else "TOOL_REQUEST")
                    observations.append(RawObservation(kind=kind,
                        public_payload={"source": "driver_verified", **driver_event,
                                        "request_ordinal": ordinal},
                        raw_payload=driver_event))
                captures.append(RawCapture(request_ordinal=ordinal, http_status=capture["http_status"],
                    body=body, elapsed_ms=capture.get("elapsed_ms", 0), transport_error=None,
                    log_ref="data:application/octet-stream;base64," + capture.get("service_stderr_base64", "")))
            if len(captures) != len(batch):
                return failure(ExecutorFailure.CAPTURE_TRUNCATED)
            if gateway_failure:
                return failure(ExecutorFailure.SANDBOX_TERMINATED)
            return RunResult(captures=tuple(captures),
                executor_ref=operation_id,
                failure=None, wall_ms=round((time.monotonic() - started) * 1000),
                observations=tuple(observations))
        except (OSError, ValueError, KeyError, UnicodeDecodeError, TypeError) as exc:
            observations.append(RawObservation(kind="INTERPRETATION",
                public_payload={"source": "controller_verified", "adapter_error_type": type(exc).__name__},
                raw_payload={}))
            return failure(ExecutorFailure.PROVISION_FAILED)
        except Exception as exc:
            observations.append(RawObservation(kind="INTERPRETATION",
                public_payload={"source": "controller_verified", "adapter_error_type": type(exc).__name__},
                raw_payload={}))
            return failure(ExecutorFailure.INTERNAL)
        finally:
            if gateway is not None:
                gateway.close()
            if operation_id is not None and not terminal:
                try:
                    await client.cancel_operation(operation_id)
                except Exception:
                    pass
