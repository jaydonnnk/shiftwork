import asyncio
import base64
import http.client
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from shiftwork import config
from shiftwork.domain import canonical
from shiftwork.domain.models import ExecutorFailure
from shiftwork.executor.base import RawCapture, RunRequest, RunResult, load_batch, provision_workspace


CHILD_ENV_ALLOWLIST = ("SYSTEMROOT", "WINDIR")
MAX_BODY_BYTES = 1024 * 1024


def _request(port: int, ordinal: int, body: bytes, deadline: float) -> RawCapture:
    started = time.perf_counter_ns()
    status = None
    captured = bytearray()
    error = None
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=max(0.001, deadline - time.monotonic()))
    try:
        connection.request("POST", "/", body=body, headers={"Content-Type": "application/json"})
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
        error = ExecutorFailure.REQUEST_TIMEOUT
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


class LocalProcessAdapter:
    name = "local_process"

    async def execute(self, request: RunRequest) -> RunResult:
        started = time.monotonic()
        captures = []
        failure = None
        try:
            files = dict(request.artifact_snapshot.files)
            file_hash = canonical.content_hash({path: base64.b64encode(body).decode("ascii") for path, body in files.items()})
            if (request.artifact_snapshot.manifest_hash, file_hash) not in config.TRUSTED_LOCAL_FIXTURES.values():
                raise ValueError("artifact is not a pinned trusted fixture")
            if request.inference_grant is not None or request.harness_ref != "stdlib-loopback-v1" or request.image_ref != "local-python-stdlib":
                raise ValueError("unsupported offline execution request")
            batch = load_batch(request.request_batch, request.request_batch_bytes)
            snapshot = Path(request.shop_snapshot_ref).read_bytes()
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
            try:
                process = await asyncio.create_subprocess_exec(
                    sys.executable, "-I", "-B", "-u", "service.py",
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
                    capture = await asyncio.to_thread(_request, port, stimulus.ordinal, stimulus.body, deadline)
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
        )
