"""Intent is derived from received bytes; controller conditions are assertions only."""

import base64
import hashlib
import http.client
import json
import secrets
import textwrap
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from shiftwork import config
from shiftwork.executor import deployment
from shiftwork.packs import registry


def derive(request_id, text):
    function = getattr(deployment, "derive_intent_key", None)
    assert callable(function), "received-input intent derivation is missing"
    return function(request_id, text)


def received_inputs():
    pack = registry.resolve_pack("northline")
    rows = []
    for pair in (1, 2, 3):
        requests = [json.loads(line) for line in (config.FIXTURE_DIR / "requests" /
            f"northline_compare_pair_{pair:02d}.jsonl").read_bytes().splitlines()]
        specs = json.loads((config.FIXTURE_DIR / "requests" /
            f"northline_compare_pair_{pair:02d}_specs.json").read_bytes())
        rows.extend((f"public-{pair}-{row['ordinal']}", row,
                     spec["tasks"][0]["condition_json"]["idempotency_key"])
                    for row, spec in zip(requests, specs, strict=True))
    row = json.loads((config.PACKAGE_DIR / pack.incident_request_path).read_bytes())
    mission = json.loads((config.PACKAGE_DIR / pack.mission_path).read_bytes())
    rows.append(("pilot", row, mission["request_specs"][0]["tasks"][0]["condition_json"]["idempotency_key"]))
    for index, case in enumerate(json.loads((config.PACKAGE_DIR / pack.families[0].case_file).read_bytes())["cases"], 1):
        stimulus = case["stimulus"]
        rows.append((f"protected-{index}", stimulus["request"],
                     stimulus["task_spec"]["tasks"][0]["condition_json"]["idempotency_key"]))
    assert len(rows) == 13
    return rows


@pytest.mark.parametrize("name,row,expected", received_inputs(), ids=lambda value: value if isinstance(value, str) else None)
def test_all_reviewed_inputs_derive_intent_without_controller_conditions(name, row, expected):
    assert derive(row["request_id"], row["text"]) == expected, name


@pytest.mark.parametrize("text,expected", [
    ("Book visit V-11.", "northline-intent-V11"),
    ("Retry visit V-11!", "northline-intent-V11"),
    ("counter intent ABC_12-3, please.", "ABC_12-3"),
    ("counter intent A and counter intent A.", "A"),
    ("visit V-11 and counter intent northline-intent-V11.", "northline-intent-V11"),
    ("No shared identifier supplied.", "received-row-7"),
    ("counter intent " + "a" * 256 + ".", "a" * 256),
], ids=["visit_first", "visit_retry", "explicit", "repeat", "both", "fallback", "maximum"])
def test_protocol_tokens_and_precedence(text, expected):
    assert derive("received-row-7", text) == expected


@pytest.mark.parametrize("text", [
    "counter intent", "counter intent -bad", "counter intent _bad", "counter intent é",
    "counter intent abc/def", "counter intent abcé", "counter intent " + "a" * 257,
    "counter intent A and counter intent B", "visit V-11 and visit V-12",
    "visit V-x", "visit V-１２", "visit V-11x", "visit V-" + "1" * 256,
    "visit V-11 and counter intent wrong",
], ids=["missing", "leading_dash", "leading_underscore", "nonascii", "slash", "suffix_nonascii",
        "overlong", "explicit_conflict", "visit_conflict", "visit_letters", "visit_nonascii",
        "visit_suffix", "visit_overlong", "cross_conflict"])
def test_malformed_ambiguous_or_overlong_tokens_fail_closed(text):
    with pytest.raises(ValueError):
        derive("received-row-7", text)


@pytest.mark.parametrize("request_id,text", [("", "fallback"), ("bad/header", "fallback"),
    ("x" * 257, "fallback"), (None, "fallback"), ("one", None)], ids=["empty", "slash", "overlong", "id_type", "text_type"])
def test_invalid_received_fields_fail_closed(request_id, text):
    with pytest.raises(ValueError):
        derive(request_id, text)


def deliver_driver_request(body, phase):
    """Execute the actual driver's delivery block against real loopback HTTP.

    Linux privilege/startup/checkpoint operations are outside this offline proof.
    """
    from shiftwork.executor.tokenfactory import DRIVER_SOURCE
    observed = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            received = self.rfile.read(int(self.headers["Content-Length"]))
            observed.append((received, dict(self.headers)))
            response = b'{"request_id":"driver-response"}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    state = (config.PACKAGE_DIR / registry.resolve_pack("northline").comparison_state_path).read_bytes()
    kernel = deployment.DeploymentKernel(state, {"run_id": "driver-unit", "context_hash": "0" * 64,
        "artifact_hash": "1" * 64, "state_hash": hashlib.sha256(state).hexdigest(),
        "batch_hash": "2" * 64, "phase": phase or "PUBLIC", "allowed_resources": []}) if phase else None
    source = DRIVER_SOURCE.decode()
    start = source.index("        events = []", source.index("    for ordinal in range"))
    end = source.index("        raw = json.dumps(capture", start)
    fragment = textwrap.dedent(source[start:end])
    namespace = {"base64": base64, "hashlib": hashlib, "http": http, "json": json,
        "secrets": secrets, "time": time, "deployment_lock": threading.Lock(),
        "deployment": kernel, "derive_intent_key": deployment.derive_intent_key,
        "config": {"body_base64": base64.b64encode(body).decode(),
                   "logical_request_ordinal": 3 if phase == "PROTECTED" else 1,
                   "idempotency_key": "CONTROLLER_VALUE_MUST_BE_IGNORED"},
        "ordinal": 1, "port": server.server_address[1], "MAX_BODY": 1024 * 1024, "stderr": b""}
    try:
        exec(compile(fragment, "trusted-driver-delivery", "exec"), namespace)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert not thread.is_alive()
    return observed, namespace["capture"]


@pytest.mark.parametrize("name,row,expected", received_inputs(), ids=lambda value: value if isinstance(value, str) else None)
def test_driver_delivers_derived_header_and_exact_original_body(name, row, expected):
    # Deliberately noncanonical body to catch accidental serialization changes.
    body = ("  " + json.dumps(row, indent=2) + "\n").encode()
    observed, capture = deliver_driver_request(body, "PROTECTED" if name.startswith("protected") else "PUBLIC")
    assert observed[0][0] == body, "trusted driver rewrote the original received body"
    headers = observed[0][1]
    assert headers.get("X-Shiftwork-Intent-Key") == expected, "trusted driver omitted or changed received-input intent"
    assert len(headers["X-Shiftwork-Request-Token"]) == 64
    trace = capture["deployment_trace"]
    assert trace["request_sha256"] == hashlib.sha256(body).hexdigest()
    assert trace["request_id"] == row["request_id"]
    assert trace["request_ordinal"] == (3 if name.startswith("protected") else 1)


def test_other_pack_request_wire_retains_body_and_has_no_deployment_header():
    body = b'{"request_id":"legacy-exact-wire"}'
    observed, capture = deliver_driver_request(body, None)
    assert observed[0][0] == body
    assert "X-Shiftwork-Intent-Key" not in observed[0][1]
    assert "deployment_trace" not in capture


def test_header_never_includes_customer_prose_after_valid_token():
    row = {"request_id": "one", "text": "counter intent A\r\nInjected: header"}
    observed, _ = deliver_driver_request(json.dumps(row).encode(), "PUBLIC")
    assert observed[0][1].get("X-Shiftwork-Intent-Key") == "A", "trusted driver omitted received-input intent"
    assert "Injected" not in observed[0][1]
