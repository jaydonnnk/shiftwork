import asyncio
import base64
import http.client
import json
import os
import sys
import tempfile
import time
import hashlib
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from shiftwork import config
from shiftwork.domain import canonical
from shiftwork.domain.models import ExecutorFailure
from shiftwork.executor.base import RawCapture, RunRequest, RunResult, load_batch, load_single_request, provision_workspace, deployment_observation
from shiftwork.executor.deployment import DeploymentKernel
from shiftwork.packs import registry


CHILD_ENV_ALLOWLIST = ("SYSTEMROOT", "WINDIR")
# macOS CoreFoundation and libc set these in every child process whatever env mapping
# spawn receives, so they cannot be suppressed and are not controller state leaking.
OS_INJECTED_ENV = ("LC_CTYPE", "__CF_USER_TEXT_ENCODING") if sys.platform == "darwin" else ()
MAX_BODY_BYTES = 1024 * 1024


def _request(port: int, ordinal: int, body: bytes, deadline: float, token: str | None = None) -> RawCapture:
    started = time.perf_counter_ns()
    status = None
    captured = bytearray()
    error = None
    connected = False
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=max(0.001, deadline - time.monotonic()))
    try:
        connection.connect()
        connected = True
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["X-Shiftwork-Request-Token"] = token
        connection.request("POST", "/", body=body, headers=headers)
        response = connection.getresponse()
        status = response.status
        expected_length = response.length
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(min(65536, MAX_BODY_BYTES + 1 - len(captured)))
            if not chunk:
                break
            captured.extend(chunk)
            if len(captured) > MAX_BODY_BYTES:
                del captured[MAX_BODY_BYTES:]
                error = ExecutorFailure.CAPTURE_TRUNCATED
                break
        if expected_length is not None and len(captured) < expected_length:
            error = ExecutorFailure.CAPTURE_TRUNCATED
        if error is None:
            try:
                captured.decode("utf-8")
            except UnicodeDecodeError:
                error = ExecutorFailure.CAPTURE_NON_UTF8
    except TimeoutError:
        error = ExecutorFailure.REQUEST_TIMEOUT if connected else ExecutorFailure.SERVICE_UNREACHABLE
    except http.client.IncompleteRead as exc:
        captured.extend(exc.partial)
        error = ExecutorFailure.CAPTURE_TRUNCATED
    except (ConnectionError, OSError):
        error = ExecutorFailure.SERVICE_UNREACHABLE
    except http.client.HTTPException:
        error = ExecutorFailure.CAPTURE_TRUNCATED
    finally:
        connection.close()
    return RawCapture(
        request_ordinal=ordinal, http_status=status, body=bytes(captured),
        elapsed_ms=(time.perf_counter_ns() - started) // 1_000_000,
        transport_error=error, log_ref=None,
    )


def _is_reviewed_blank(request, files):
    if request.service_protocol != "FIXED_HTTP_8080" or request.deployment_binding is None:
        return False
    pack = registry.resolve_pack("northline")
    paths = {"service.py": "templates/artifact/northline_blank_service.py", **{
        name: "templates/artifact/northline/" + name
        for name in ("discovery.md", "permissions.json", "acceptance_tests.py", "runbook.md")}}
    pins = {pin.path: pin.sha256 for pin in pack.reviewed_pins}
    return (set(files) == set(paths) and all(
        hashlib.sha256(files[name]).hexdigest() == pins.get(path) for name, path in paths.items()))


class _DeploymentHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        status = 200
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if self.path != "/deployment" or not 0 < size <= 8192:
                raise ValueError("invalid deployment request")
            body = json.loads(self.rfile.read(size))
            with self.server.deployment_lock:
                result = self.server.kernel.act(self.headers.get("X-Shiftwork-Request-Token"), body)
        except PermissionError:
            status, result = 403, {"error": "DEPLOYMENT_NOT_PERMITTED"}
        except (ValueError, TypeError):
            status, result = 422, {"error": "DEPLOYMENT_INVALID"}
        encoded = json.dumps(result).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class LocalProcessAdapter:
    name = "local_process"

    async def execute(self, request: RunRequest) -> RunResult:
        started = time.monotonic()
        captures = []
        observations = []
        failure = None
        try:
            files = dict(request.artifact_snapshot.files)
            file_hash = canonical.content_hash({path: base64.b64encode(body).decode("ascii") for path, body in files.items()})
            if ((request.artifact_snapshot.manifest_hash, file_hash) not in config.TRUSTED_LOCAL_FIXTURES.values()
                    and not _is_reviewed_blank(request, files)):
                raise ValueError("artifact is not a pinned trusted fixture")
            if request.inference_grant is not None or request.harness_ref != "stdlib-loopback-v1" or request.image_ref != "local-python-stdlib":
                raise ValueError("unsupported offline execution request")
            batch = ((load_single_request(request.request_batch, request.request_batch_bytes,
                                          request.single_request_ordinal),)
                     if request.single_request_ordinal is not None else
                     load_batch(request.request_batch, request.request_batch_bytes))
            snapshot = Path(request.shop_snapshot_ref).read_bytes()
            kernel = DeploymentKernel(snapshot, request.deployment_binding.model_dump(mode="json")) if request.deployment_binding else None
        except (OSError, ValueError, KeyError):
            return RunResult(captures=(), executor_ref=None, failure=ExecutorFailure.PROVISION_FAILED, wall_ms=int((time.monotonic() - started) * 1000))

        deadline = started + request.deadline_s
        with tempfile.TemporaryDirectory(prefix="shiftwork-fixture-") as workspace:
            root = Path(workspace)
            try:
                provision_workspace(root, request, snapshot)
            except (OSError, ValueError, KeyError):
                return RunResult(captures=(), executor_ref=None, failure=ExecutorFailure.PROVISION_FAILED, wall_ms=int((time.monotonic() - started) * 1000))
            child_env = {key: os.environ[key] for key in CHILD_ENV_ALLOWLIST if key in os.environ}
            process = None
            stdout_task = None
            stderr_task = None
            logs = b""
            broker = None
            try:
                if kernel is not None:
                    broker = ThreadingHTTPServer(("127.0.0.1", 0), _DeploymentHandler)
                    broker.kernel = kernel
                    broker.deployment_lock = threading.Lock()
                    threading.Thread(target=broker.serve_forever, daemon=True).start()
                    child_env["SHIFTWORK_GATEWAY_PORT"] = str(broker.server_port)
                args = [sys.executable, "-I", "-B", "-u", "service.py"]
                if request.service_protocol == "FIXED_HTTP_8080":
                    # Execute the exact template through a trusted ephemeral-port shim.
                    # This is trusted-local fixture evidence, never isolation evidence.
                    shim = ("import http.server,json,runpy; original=http.server.HTTPServer; "
                            "exec('class AdapterServer(original):\\n def __init__(self,address,handler):\\n"
                            "  super().__init__((address[0],0),handler)\\n"
                            "  print(json.dumps({\\\"port\\\":self.server_port}),flush=True)'); "
                            "http.server.HTTPServer=AdapterServer; runpy.run_path('service.py',run_name='__main__')")
                    args = [sys.executable, "-I", "-B", "-u", "-c", shim]
                process = await asyncio.create_subprocess_exec(
                    *args,
                    cwd=workspace, env=child_env,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                stderr_task = asyncio.create_task(process.stderr.read())
                ready = await asyncio.wait_for(process.stdout.readline(), max(0.001, deadline - time.monotonic()))
                port = json.loads(ready)["port"]
                if type(port) is not int or not 0 < port < 65536:
                    raise ValueError("invalid loopback port")
                stdout_task = asyncio.create_task(process.stdout.read())
                for stimulus in batch:
                    token = secrets.token_hex(32)
                    if kernel is not None:
                        with broker.deployment_lock:
                            kernel.begin(stimulus.ordinal, stimulus.body, token)
                    capture = await asyncio.to_thread(_request, port, stimulus.ordinal, stimulus.body, deadline, token)
                    if kernel is not None and capture.transport_error is None:
                        with broker.deployment_lock:
                            trace = kernel.finish(capture.body)
                        receipt = json.dumps({"request_ordinal": stimulus.ordinal,
                            "http_status": capture.http_status, "body_base64": base64.b64encode(capture.body).decode(),
                            "deployment_trace": trace}, sort_keys=True).encode()
                        observations.append(deployment_observation(request, stimulus, receipt,
                            byte_count=len(receipt), sha256=hashlib.sha256(receipt).hexdigest()))
                    if capture.transport_error in (ExecutorFailure.SERVICE_UNREACHABLE, ExecutorFailure.CAPTURE_TRUNCATED):
                        if process.returncode is None:
                            try:
                                await asyncio.wait_for(process.wait(), 0.1)
                            except TimeoutError:
                                pass
                        if process.returncode is not None:
                            failure = ExecutorFailure.SANDBOX_TERMINATED
                            if capture.body:
                                captures.append(capture)
                            break
                    captures.append(capture)
                    if capture.transport_error is not None:
                        failure = capture.transport_error
                        break
            except TimeoutError:
                failure = ExecutorFailure.REQUEST_TIMEOUT
            except (OSError, ValueError, KeyError):
                failure = ExecutorFailure.PROVISION_FAILED
            finally:
                if broker is not None:
                    broker.shutdown()
                    broker.server_close()
                if process is not None:
                    if process.returncode is None:
                        try:
                            process.terminate()
                        except ProcessLookupError:
                            pass
                    await process.wait()
                    if stdout_task is not None:
                        logs += await stdout_task
                    if stderr_task is not None:
                        logs += await stderr_task
        log_ref = "data:application/octet-stream;base64," + base64.b64encode(logs).decode("ascii") if logs else None
        return RunResult(
            captures=tuple(c.model_copy(update={"log_ref": log_ref}) for c in captures),
            executor_ref=None, failure=failure, wall_ms=int((time.monotonic() - started) * 1000),
            observations=tuple(observations),
        )
