"""Bounded Slice 12 live capability probes. Credentials stay in this process.

The F3 repair: a captured checkpoint is accepted only after its file is
downloaded and its SHA-256 compared, so a stdout marker alone can never pass or
fail a write. The F4 repair: every absence assertion carries a positive control,
and a control that did not fire records `unproven` rather than passing. Each run
writes its own timestamped evidence file and stamps every record with a UTC time
and the producing source hash, so a later revision cannot silently inherit an
earlier run's records.
"""

from __future__ import annotations

import asyncio
import base64
import dataclasses
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

import httpx
from contree_client.exceptions import APIStatusError
from contree_client.httpx import ContreeAsyncClient
from contree_client.models import ClosableStreamRepr, FileSpec, InstanceNetworking, InstanceResourcesLimits


MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
IMAGE = "c7ad32fe-8621-3cd2-9022-521c6da02ac1"  # public python:3.11-slim
MAX_INPUT_BYTES = 8192
MAX_OUTPUT_TOKENS = 256  # below the Gate 3 ceiling of 1,024
MODEL_INPUT_USD_PER_MILLION = 0.06
MODEL_OUTPUT_USD_PER_MILLION = 0.24
MAX_SPIKE_USD = 3.00
EVIDENCE_DIR = Path("docs/plans/shiftwork/evidence")
EVIDENCE_SINK: Path | None = None
SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

CAPTURE_PASS = "PASS_CAPTURE_INTACT"
CAPTURE_EMPTY = "STOP_CAPTURE_EMPTY"
CAPTURE_TRUNCATED = "STOP_CAPTURE_TRUNCATED"
CAPTURE_DIGEST_MISMATCH = "STOP_CAPTURE_DIGEST_MISMATCH"
CAPTURE_UNAVAILABLE = "STOP_CAPTURE_UNAVAILABLE"
CAPTURE_WRITE_UNACKNOWLEDGED = "STOP_CAPTURE_WRITE_NOT_ACKNOWLEDGED"

PAIR_STABLE = "PASS_PAIR_CAPTURE_STABLE"
PAIR_LOSS_UNDER_CAP = "STOP_PAIR_LOSS_REPRODUCED_UNDER_CAP"
PAIR_CONTROL_UNRELIABLE = "STOP_PAIR_CONTROL_UNRELIABLE"
PAIR_EVIDENCE_UNAVAILABLE = "STOP_PAIR_EVIDENCE_UNAVAILABLE"
PAIR_TREATMENT_UNACKNOWLEDGED = "INCONCLUSIVE_PAIR_TREATMENT_NOT_ACKNOWLEDGED"

ABSENCE_PASS = "PASS_ABSENCE_CONTROLS_FIRED"
ABSENCE_LEAK = "STOP_ABSENCE_LEAK_DETECTED"
ABSENCE_UNPROVEN = "UNPROVEN_POSITIVE_CONTROL_UNAVAILABLE"
ABSENCE_INCONCLUSIVE = "STOP_ABSENCE_CHECK_INCONCLUSIVE"

ABSENCE_CONTROL_KEYS = (
    "positive_control_env_lookup",
    "positive_control_sentinel_present",
    "positive_control_loopback_connect",
)
ABSENCE_TARGET_KEYS = (
    "canary_name_present",
    "canary_value_present",
    "provider_env_present",
    "controller_file_present",
    "arbitrary_https",
    "metadata_ip",
    "controller_loopback",
)


def classify_capture(*, expected_size: int, expected_sha256: str,
                     downloaded: bytes | None, write_acknowledged: bool) -> str:
    intact = (
        downloaded is not None
        and len(downloaded) == expected_size
        and hashlib.sha256(downloaded).hexdigest() == expected_sha256
    )
    if intact:
        return CAPTURE_PASS
    if not write_acknowledged:
        return CAPTURE_WRITE_UNACKNOWLEDGED
    if downloaded is None:
        return CAPTURE_UNAVAILABLE
    if not downloaded:
        return CAPTURE_EMPTY
    if len(downloaded) != expected_size:
        return CAPTURE_TRUNCATED
    return CAPTURE_DIGEST_MISMATCH


def classify_pair(*, control: str, treatment: str) -> str:
    if control == CAPTURE_UNAVAILABLE or treatment == CAPTURE_UNAVAILABLE:
        return PAIR_EVIDENCE_UNAVAILABLE
    if control != CAPTURE_PASS:
        return PAIR_CONTROL_UNRELIABLE
    if treatment == CAPTURE_PASS:
        return PAIR_STABLE
    if treatment == CAPTURE_WRITE_UNACKNOWLEDGED:
        return PAIR_TREATMENT_UNACKNOWLEDGED
    return PAIR_LOSS_UNDER_CAP


def classify_absence_controls(checks: dict[str, object]) -> str:
    if any(checks.get(name) is True for name in ABSENCE_TARGET_KEYS):
        return ABSENCE_LEAK
    if any(checks.get(name) is not True for name in ABSENCE_CONTROL_KEYS):
        return ABSENCE_UNPROVEN
    if any(checks.get(name) is not False for name in ABSENCE_TARGET_KEYS):
        return ABSENCE_INCONCLUSIVE
    return ABSENCE_PASS


def build_record(probe: str, fields: dict[str, object]) -> dict[str, object]:
    return {
        "probe": probe,
        "recorded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_sha256": SOURCE_SHA256,
        **fields,
    }


def new_evidence_sink(phase: str, *, directory: Path = EVIDENCE_DIR,
                      now: datetime | None = None) -> Path:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"slice12-{phase}-{stamp}.jsonl"
    if path.exists():
        raise RuntimeError("evidence_run_file_exists: " + str(path))
    return path


def emit(probe: str, **fields: object) -> None:
    if EVIDENCE_SINK is None:
        raise RuntimeError("evidence_sink_not_set")
    record = build_record(probe, fields)
    line = json.dumps(record, default=str, sort_keys=True, ensure_ascii=False)
    print(line, flush=True)
    EVIDENCE_SINK.parent.mkdir(parents=True, exist_ok=True)
    with EVIDENCE_SINK.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def prior_inference_spend(directory: Path) -> float:
    spent = 0.0
    for path in sorted(directory.glob("slice12-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record.get("probe") == "nemotron_inference":
                cost = record.get("estimated_usd_from_displayed_rate")
                if not isinstance(cost, (int, float)):
                    raise RuntimeError("unknown_prior_inference_cost")
                spent += cost
            if record.get("probe") == "inference_budget_reservation":
                spent += record["worst_case_usd"]
    return spent


def stream_text(data: Any) -> str:
    value = data.value if hasattr(data, "value") else data.get("value", "")
    encoding = data.encoding if hasattr(data, "encoding") else data.get("encoding", "ascii")
    if encoding == "base64":
        return base64.b64decode(value).decode("utf-8", errors="replace")
    return value


def no_secret_leak(surface: object, token: str, canary: str) -> bool:
    serialized = json.dumps(surface, default=str, sort_keys=True)
    needles = (token, canary, str(Path.cwd()))
    forms = [
        (needle, json.dumps(needle, ensure_ascii=False)[1:-1], needle.replace("\\", "/"))
        for needle in needles
    ]
    if any(form in serialized for variants in forms for form in variants if form):
        return False
    # Prove that each needle is detectable on the serialized surface.
    return all(
        any(form in json.dumps({"surface": needle}) for form in variants if form)
        for needle, variants in zip(needles, forms)
    )


async def infer(prompt: str, token: str) -> tuple[str, dict[str, object]]:
    if len(prompt.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("gateway_input_exceeds_8192_bytes")
    spent = prior_inference_spend(EVIDENCE_DIR)
    worst_next = (
        MAX_INPUT_BYTES * MODEL_INPUT_USD_PER_MILLION / 1_000_000
        + MAX_OUTPUT_TOKENS * MODEL_OUTPUT_USD_PER_MILLION / 1_000_000
    )
    if spent + worst_next > MAX_SPIKE_USD:
        raise RuntimeError("spike_budget_projection_exceeds_3_usd")
    emit("inference_budget_reservation", prior_estimate_usd=spent,
         worst_case_usd=worst_next, cap_usd=MAX_SPIKE_USD)
    request = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0,
    }
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=20) as http:
        response = await http.post(
            "https://api.tokenfactory.nebius.com/v1/chat/completions",
            headers={"Authorization": "Bearer " + token},
            json=request,
        )
    response.raise_for_status()
    body = response.json()
    usage = body.get("usage") or {}
    input_tokens = usage.get("prompt_tokens")
    output_tokens = usage.get("completion_tokens")
    cost = (
        input_tokens * MODEL_INPUT_USD_PER_MILLION / 1_000_000
        + output_tokens * MODEL_OUTPUT_USD_PER_MILLION / 1_000_000
        if isinstance(input_tokens, int) and isinstance(output_tokens, int)
        else None
    )
    observation = {
        "model": body.get("model"),
        "requested_model": MODEL,
        "settings": {"max_tokens": MAX_OUTPUT_TOKENS, "temperature": 0, "timeout_seconds": 20},
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "usage": usage,
        "estimated_usd_from_displayed_rate": cost,
        "finish_reason": (body.get("choices") or [{}])[0].get("finish_reason"),
    }
    content = (body.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    return content, observation


async def events(client: ContreeAsyncClient, operation_id: str, seen: int | None) -> list[Any]:
    return [event async for event in client.iter_operation_events(operation_id, follow=False, last_event_id=seen)]


async def service_probe(client: ContreeAsyncClient, token: str, canary: str) -> int:
    service = Path(__file__).with_name("slice12_service.py").read_bytes()
    uploaded = await client.upload_file(service)
    emit("file_upload", sha256=uploaded.sha256, size=uploaded.size, uuid=uploaded.uuid)
    request = {"request_id": "slice12-public-1", "text": "Can I collect Salt Roads tomorrow?"}
    started = time.monotonic()
    instance = await client.spawn_instance(
        command="/usr/local/bin/python",
        image=IMAGE,
        args=["-u", "/work/service.py"],
        disposable=True,
        networking=InstanceNetworking(enabled=False),
        resources_limits=InstanceResourcesLimits(max_layer_bytes=16 * 1024 * 1024),
        stdin=ClosableStreamRepr(value=json.dumps(request) + "\n", encoding="ascii", close=False),
        files={"/work/service.py": FileSpec(uuid=uploaded.uuid, mode="0644")},
        timeout=30,
        truncate_output_at=8192,
    )
    operation_id = instance.uuid
    emit("service_spawn", operation_id=operation_id, image=IMAGE, image_tag="python:3.11-slim", disposable=True,
         networking=False, timeout_seconds=30, max_layer_bytes=16 * 1024 * 1024)
    seen: int | None = None
    stdout = ""
    raw_events: list[dict[str, object]] = []
    inference_done = False
    terminal = False
    try:
        while time.monotonic() - started < 45:
            for event in await events(client, operation_id, seen):
                seen = event.id
                raw_events.append(dataclasses.asdict(event))
                if event.type == "stdout":
                    stdout += stream_text(event.data)
                if event.type == "completion":
                    terminal = True
            if not inference_done and "\n" in stdout:
                first = json.loads(stdout.split("\n", 1)[0])
                if first.get("kind") != "inference_request" or first.get("request_id") != request["request_id"]:
                    raise RuntimeError("unbound_or_malformed_service_request")
                content, observation = await infer(first["prompt"], token)
                emit("nemotron_inference", **observation, content=content)
                await client.operation_subprocess_stdin(
                    operation_id, 1, json.dumps({"choice": content}) + "\n", close=True
                )
                inference_done = True
            if terminal:
                break
            await asyncio.sleep(0.25)
        if not terminal:
            raise TimeoutError("service_operation_not_terminal_within_45_seconds")
        status = await client.get_operation_status(operation_id)
        result = status.metadata.result if hasattr(status.metadata, "result") else None
        safe = no_secret_leak(raw_events + [dataclasses.asdict(status)], token, canary)
        if not safe:
            emit("service_capture", operation_id=operation_id, serialized_secret_scan_pass=False,
                 result="STOP_POSSIBLE_LEAK")
            return 2
        emit("service_capture", operation_id=operation_id, status=str(status.status),
             elapsed_ms=round((time.monotonic()-started)*1000), stdout=stdout,
             result=dataclasses.asdict(result) if result else None,
             event_count=len(raw_events), serialized_secret_scan_pass=safe)
        return 0 if safe and inference_done and '"tool": "stock_lookup"' in stdout else 2
    finally:
        if not terminal:
            await client.cancel_operation(operation_id)
            emit("service_cleanup", operation_id=operation_id, action="cancelled_nonterminal")


async def one_shot(
    client: ContreeAsyncClient,
    token: str,
    canary: str,
    name: str,
    code: str,
    *,
    image: str = IMAGE,
    disposable: bool = True,
    timeout: int = 8,
    max_layer_bytes: int = 16 * 1024 * 1024,
    files: dict[str, FileSpec] | None = None,
) -> tuple[Any, str]:
    started = time.monotonic()
    spawn_files = {"files": files} if files else {}
    instance = await client.spawn_instance(
        command="/usr/local/bin/python", image=image, args=["-u", "-c", code],
        disposable=disposable, networking=InstanceNetworking(enabled=False),
        resources_limits=InstanceResourcesLimits(max_layer_bytes=max_layer_bytes),
        timeout=timeout, truncate_output_at=4096, **spawn_files,
    )
    operation_id = instance.uuid
    emit(name + "_spawn", operation_id=operation_id, image=image, disposable=disposable,
         networking=False, timeout_seconds=timeout, max_layer_bytes=max_layer_bytes)
    terminal = False
    try:
        status = await client.wait_operation(operation_id, timeout=timeout + 15)
        terminal = str(status.status) in ("SUCCESS", "FAILED", "CANCELLED")
        raw_events = [dataclasses.asdict(event) for event in await events(client, operation_id, None)]
        surface = [raw_events, dataclasses.asdict(status)]
        safe = no_secret_leak(surface, token, canary)
        if not safe:
            emit(name, operation_id=operation_id, serialized_secret_scan_pass=False,
                 result="STOP_POSSIBLE_LEAK")
            raise RuntimeError("possible_secret_leak")
        result = status.metadata.result if hasattr(status.metadata, "result") else None
        stdout = stream_text(result.stdout) if result and hasattr(result, "stdout") else ""
        emit(name, operation_id=operation_id, status=str(status.status),
             elapsed_ms=round((time.monotonic()-started)*1000),
             result_image_uuid=getattr(status, "result_image_uuid", None),
             stdout=stdout[:4096], result=dataclasses.asdict(result) if result else None,
             event_count=len(raw_events), event_types=[event.get("type") for event in raw_events],
             serialized_secret_scan_pass=True)
        return status, stdout
    finally:
        if not terminal:
            await client.cancel_operation(operation_id)
            emit(name + "_cleanup", operation_id=operation_id, action="cancelled_nonterminal")


async def controls_probe(client: ContreeAsyncClient, token: str, canary: str) -> int:
    sentinel_path = "/work/slice12-sentinel.txt"
    sentinel_content = "SLICE12_SENTINEL_PRESENT"
    sentinel = await client.upload_file(sentinel_content.encode("ascii"))
    # The canary sits only in this process's environment: if the runtime passes
    # the spawning environment into the Sandbox, the in-Sandbox check sees it.
    os.environ["SLICE12_HOST_ONLY_CANARY"] = canary
    access_code = "\n".join((
        "import json, os, socket",
        "def connect(host, port):",
        "    try:",
        "        socket.create_connection((host, port), timeout=2).close()",
        "        return True",
        "    except OSError:",
        "        return False",
        "def loopback_control():",
        "    server = socket.socket()",
        "    try:",
        "        server.bind(('127.0.0.1', 0))",
        "        server.listen(1)",
        "        return connect('127.0.0.1', server.getsockname()[1])",
        "    except OSError:",
        "        return False",
        "    finally:",
        "        server.close()",
        "def sentinel_present():",
        "    try:",
        f"        return open({sentinel_path!r}).read().strip() == {sentinel_content!r}",
        "    except OSError:",
        "        return False",
        "checks = {",
        " 'positive_control_env_lookup': 'PATH' in os.environ,",
        " 'positive_control_sentinel_present': sentinel_present(),",
        " 'positive_control_loopback_connect': loopback_control(),",
        " 'canary_name_present': any('CANARY' in key.upper() for key in os.environ),",
        " 'canary_value_present': any('SLICE12_HOST' in value for value in os.environ.values()),",
        " 'provider_env_present': any(k in os.environ for k in ('NEBIUS_API_KEY', 'CONTREE_TOKEN', 'NEBIUS_PROJECT_ID')),",
        " 'controller_file_present': any(os.path.exists(p) for p in ('/work/.env','/work/shiftwork.db','/work/protected.json','/run/secrets/NEBIUS_API_KEY')),",
        " 'arbitrary_https': connect('example.com', 443),",
        " 'metadata_ip': connect('169.254.169.254', 80),",
        " 'controller_loopback': connect('127.0.0.1', 8000),",
        "}",
        "print(json.dumps(checks))",
    ))
    _, stdout = await one_shot(
        client, token, canary, "access_egress", access_code,
        files={sentinel_path: FileSpec(uuid=sentinel.uuid, mode="0644")},
    )
    checks = json.loads(stdout)
    verdict = classify_absence_controls(checks)
    emit("access_egress_verdict", checks=checks, verdict=verdict,
         host_canary_in_spawn_environment=os.environ.get("SLICE12_HOST_ONLY_CANARY") == canary,
         sentinel_mounted=sentinel_path, sentinel_sha256=sentinel.sha256,
         scope_note="connect results show whether the disabled networking flag is honoured; they are not a host isolation proof")
    if verdict != ABSENCE_PASS:
        emit("hard_stop", reason="credential_or_egress_controls_failed", verdict=verdict, checks=checks)
        return 2
    crash_code = "import os; print('CAPTURE_BEFORE_CRASH', flush=True); os._exit(7)"
    crash_status, crash_stdout = await one_shot(client, token, canary, "crash_retention", crash_code)
    crash_result = crash_status.metadata.result
    if "CAPTURE_BEFORE_CRASH" not in crash_stdout or crash_result.state.exit_code != 7:
        emit("hard_stop", reason="crash_evidence_lost")
        return 2
    timeout_status, _ = await one_shot(client, token, canary, "deadline", "import time; time.sleep(3)", timeout=1)
    if not timeout_status.metadata.result.state.timed_out:
        emit("hard_stop", reason="deadline_not_enforced")
        return 2
    return 0


PAIR_PATH = "/tmp/slice12-large.bin"
PAIR_PAYLOAD = bytes(range(256)) * 8192  # 2 MiB, identical on any machine
PAIR_CAPS: tuple[tuple[str, int], ...] = (
    ("control", 16 * 1024 * 1024),
    ("treatment", 1024 * 1024),
)


async def inspect_listing(client: ContreeAsyncClient, checkpoint: object,
                          path: str) -> tuple[int | None, str | None]:
    if not isinstance(checkpoint, str):
        return None, "no_checkpoint"
    try:
        listing = await client.inspect_image_list(checkpoint, str(Path(path).parent))
    except Exception as exc:
        return None, type(exc).__name__
    expected_name = Path(path).name
    for listed in listing.files:
        if Path(str(listed.path)).name == expected_name:
            return listed.size, None
    return None, "path_not_listed"


async def pair_probe(client: ContreeAsyncClient, token: str, canary: str) -> int:
    expected_sha256 = hashlib.sha256(PAIR_PAYLOAD).hexdigest()
    uploaded = await client.upload_file(PAIR_PAYLOAD)
    emit("pair_payload", payload_path=PAIR_PATH, generator="bytes(range(256)) * 8192",
         expected_bytes=len(PAIR_PAYLOAD), expected_sha256=expected_sha256,
         upload_uuid=uploaded.uuid, upload_sha256=uploaded.sha256, upload_size=uploaded.size)
    code = (
        "import shutil; "
        f"shutil.copyfile('/work/pair_payload.bin', {PAIR_PATH!r}); "
        "print('WROTE_2MB_DETERMINISTIC', flush=True)"
    )
    verdicts: dict[str, str] = {}
    for label, cap in PAIR_CAPS:
        status, stdout = await one_shot(
            client, token, canary, "pair_" + label, code,
            disposable=False, max_layer_bytes=cap,
            files={"/work/pair_payload.bin": FileSpec(uuid=uploaded.uuid, mode="0644")},
        )
        checkpoint = getattr(status, "result_image_uuid", None)
        result = getattr(status.metadata, "result", None)
        state = getattr(result, "state", None)
        downloaded: bytes | None = None
        readback_error: str | None = None
        if str(status.status) == "SUCCESS" and isinstance(checkpoint, str):
            try:
                downloaded = await client.inspect_image_download(checkpoint, PAIR_PATH)
            except Exception as exc:
                readback_error = type(exc).__name__
        else:
            readback_error = "operation_not_success_or_missing_checkpoint"
        listing_size, listing_error = await inspect_listing(client, checkpoint, PAIR_PATH)
        exit_code = getattr(state, "exit_code", None)
        write_acknowledged = "WROTE_2MB_DETERMINISTIC" in stdout and exit_code == 0
        verdict = classify_capture(
            expected_size=len(PAIR_PAYLOAD), expected_sha256=expected_sha256,
            downloaded=downloaded, write_acknowledged=write_acknowledged,
        )
        verdicts[label] = verdict
        emit("pair_run", label=label, configured_max_layer_bytes=cap,
             operation_id=status.uuid, outer_status=str(status.status),
             inner_exit_code=exit_code, write_acknowledged=write_acknowledged,
             stdout_reported_write="WROTE_2MB_DETERMINISTIC" in stdout,
             checkpoint=checkpoint, snapshot_file_size=listing_size,
             listing_error=listing_error, expected_bytes=len(PAIR_PAYLOAD),
             expected_sha256=expected_sha256,
             actual_bytes=len(downloaded) if downloaded is not None else None,
             actual_sha256=hashlib.sha256(downloaded).hexdigest() if downloaded is not None else None,
             readback_error=readback_error, verdict=verdict)
    pair_verdict = classify_pair(control=verdicts["control"], treatment=verdicts["treatment"])
    emit("pair_verdict", control=verdicts["control"], treatment=verdicts["treatment"],
         verdict=pair_verdict, configured_max_layer_bytes=dict(PAIR_CAPS),
         cap_exceeded_without_capture_loss=verdicts["treatment"] == CAPTURE_PASS,
         note="cap_exceeded_without_capture_loss true means the 1 MiB cap did not limit a 2 MiB captured write, a capability finding rather than a capture failure; INCONCLUSIVE_PAIR_TREATMENT_NOT_ACKNOWLEDGED means the treatment process never reported a completed write, so its missing bytes are not a reproduced loss")
    return 0 if pair_verdict == PAIR_STABLE else 2


async def reset_probe(client: ContreeAsyncClient, token: str, canary: str) -> int:
    marker_path = "/tmp/slice12-reset-marker.txt"
    seed_status, _ = await one_shot(
        client, token, canary, "reset_seed",
        f"open({marker_path!r},'w').write('SLICE12_MARKER'); print('SEED_WRITTEN')",
        disposable=False,
    )
    checkpoint = seed_status.result_image_uuid
    if not checkpoint:
        emit("hard_stop", reason="reset_checkpoint_missing")
        return 2
    base_status, base_stdout = await one_shot(
        client, token, canary, "reset_from_base",
        f"import os; print(os.path.exists({marker_path!r}))",
    )
    checkpoint_status, checkpoint_stdout = await one_shot(
        client, token, canary, "checkpoint_readback",
        f"import os; print(os.path.exists({marker_path!r}))",
        image=checkpoint,
    )
    downloaded = await client.inspect_image_download(checkpoint, marker_path)
    emit("capture_file_download", checkpoint=checkpoint, path=marker_path,
         expected_bytes=downloaded == b"SLICE12_MARKER", size=len(downloaded))
    if base_stdout.strip() != "False" or checkpoint_stdout.strip() != "True" or downloaded != b"SLICE12_MARKER":
        emit("hard_stop", reason="trial_reset_or_capture_retrieval_failed")
        return 2
    try:
        await client.operation_subprocess_stdin(seed_status.uuid, 1, "reuse\n", close=True)
    except APIStatusError as exc:
        emit("terminated_stdin_reuse", operation_id=seed_status.uuid, rejected_status=exc.status)
    else:
        emit("hard_stop", reason="terminated_operation_stdin_reuse_succeeded")
        return 2
    return 0


async def readback_probe(client: ContreeAsyncClient, token: str, canary: str) -> int:
    marker_path = "/tmp/slice12-readback-marker.bin"
    expected = b"SLICE12_MARKER"
    expected_digest = hashlib.sha256(expected).hexdigest()
    code = (
        "from pathlib import Path; "
        f"Path({marker_path!r}).write_bytes({expected!r}); "
        "print('MARKER_WRITTEN', flush=True)"
    )
    status, stdout = await one_shot(
        client, token, canary, "marker_readback", code,
        disposable=False, max_layer_bytes=16 * 1024 * 1024,
    )
    result = getattr(status.metadata, "result", None)
    state = getattr(result, "state", None)
    exit_code = getattr(state, "exit_code", None)
    timed_out = getattr(state, "timed_out", None)
    checkpoint = getattr(status, "result_image_uuid", None)
    actual: bytes | None = None
    readback_error: str | None = None
    if str(status.status) == "SUCCESS" and exit_code == 0 and not timed_out and isinstance(checkpoint, str):
        try:
            actual = await client.inspect_image_download(checkpoint, marker_path)
        except Exception as exc:
            readback_error = type(exc).__name__
    else:
        readback_error = "operation_or_process_incomplete"
    actual_digest = hashlib.sha256(actual).hexdigest() if actual is not None else None
    matched = actual == expected
    emit(
        "marker_readback_verdict", operation_id=status.uuid,
        outer_status=str(status.status), inner_exit_code=exit_code,
        timed_out=timed_out, checkpoint=checkpoint,
        stdout_reported_write="MARKER_WRITTEN" in stdout,
        expected_bytes=len(expected), expected_sha256=expected_digest,
        actual_bytes=len(actual) if actual is not None else None,
        actual_sha256=actual_digest, readback_error=readback_error,
        result="PASS_ONE_SMALL_FILE_ONLY" if matched else "STOP_READBACK_MISMATCH",
    )
    if not matched:
        emit("hard_stop", reason="marker_checkpoint_readback_mismatch")
    try:
        whoami = dataclasses.asdict(await client.whoami())
        running = whoami.get("operations_stat", {}).get("running_instances")
        emit("marker_readback_cleanup", running_instances=running)
    except Exception as exc:
        emit("marker_readback_cleanup", result="verification_unavailable", error_type=type(exc).__name__)
        running = None
    return 0 if matched and running == 0 else 2


async def run(phase: str, token: str, project: str) -> int:
    global EVIDENCE_SINK
    canary = "SLICE12_HOST_ONLY_CANARY_20260926"
    EVIDENCE_SINK = new_evidence_sink(phase)
    client = ContreeAsyncClient(token, project=project, timeout=20)
    try:
        emit("run_start", phase=phase, evidence_sink=str(EVIDENCE_SINK))
        started = time.monotonic()
        whoami = dataclasses.asdict(await client.whoami())
        permissions = whoami.get("permissions", {})
        allowed = isinstance(permissions, dict) and permissions.get("spawn") is True
        emit("sandbox_whoami", result="ready" if allowed else "blocked_no_spawn_permission",
             elapsed_ms=round((time.monotonic()-started)*1000), permissions=permissions,
             limits=whoami.get("limits"), operations_stat=whoami.get("operations_stat"))
        if not allowed:
            return 2
        if phase == "preflight":
            return 0
        if phase == "service":
            return await service_probe(client, token, canary)
        if phase == "controls":
            return await controls_probe(client, token, canary)
        if phase == "pair":
            return await pair_probe(client, token, canary)
        if phase == "reset":
            return await reset_probe(client, token, canary)
        if phase == "readback":
            return await readback_probe(client, token, canary)
        raise ValueError("unknown_phase")
    finally:
        await client.close()
