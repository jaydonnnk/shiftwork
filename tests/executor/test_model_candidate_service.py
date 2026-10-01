"""The model-routing candidate: per-process ordinals, real tool routing, passing checks.

The fixture is a frozen artifact source, executed here in-process against a stub
controller gateway. The stub plays the controller's role: it verifies nothing
(the real gateway does), but it records the exact payloads the service sent, so
a service that read the request body's ordinal instead of counting served
requests is caught here.
"""

import http.client
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from shiftwork import config
from shiftwork.domain import task_contract
from shiftwork.evaluator import evaluator

FIXTURE = config.FIXTURE_DIR / "artifacts" / "bookshop" / "compare_repair_model_service.py"

PROTECTED_BODY = {
    "ordinal": 3,
    "request_id": "bellwether-protected-01",
    "text": ("For my coastal weekend, can I collect the Salt Roads paperback tomorrow? "
             "If not, suggest something similar under \u00a320."),
    "entity_ref": "book:salt-roads:paperback",
}


class StubGateway(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        self.server.calls.append((self.path, payload))
        if self.path == "/infer":
            if self.server.infer_status != 200:
                body = json.dumps({"error": "refused"}).encode()
                self.send_response(self.server.infer_status)
            else:
                body = json.dumps({"selected_tool": self.server.selected_tool}).encode()
                self.send_response(200)
        elif self.path == "/tool":
            snapshot = self.server.snapshot
            if payload.get("tool") == "public_catalog_search":
                entities = [key for key, item in snapshot["entities"].items()
                            if item.get("genre") == payload.get("genre")]
                body = json.dumps({"entity_refs": entities}).encode()
            else:
                records = [record for record in snapshot["records"]
                           if record["entity_ref"] == payload.get("entity_ref")
                           and record["kind"] == payload.get("record_kind")]
                body = json.dumps({"records": records}).encode()
            self.send_response(200)
        else:
            body = b"{}"
            self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def stub_gateway(monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), StubGateway)
    server.calls = []
    server.selected_tool = "public_record_lookup"
    server.infer_status = 200
    server.snapshot = json.loads(config.PIVOT_PUBLIC_STATE.read_bytes())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("SHIFTWORK_GATEWAY_PORT", str(server.server_port))
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)


def load_module():
    spec = importlib.util.spec_from_file_location("compare_repair_model_service", FIXTURE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def protected_spec_snapshot_mission():
    """The drawn-family protected case 01, whose empty delta leaves the reviewed compare state.

    Returns the spec, the raw snapshot the service reads (as it reads shop.json),
    the parsed snapshot the evaluator uses, and the mission.
    """
    cases = json.loads(
        (config.SEALED_CASES_DIR / "bookshop_task_completion.json").read_text(encoding="utf-8")
    )["cases"]
    case = next(item for item in cases if item["id"] == "bookshop-task-completion-01")
    spec = task_contract.CustomerRequestSpec.model_validate(case["stimulus"]["task_spec"])
    snapshot_dict = json.loads(config.PIVOT_COMPARE_STATE.read_bytes())
    snapshot = task_contract.load_public_state_bytes(config.PIVOT_COMPARE_STATE.read_bytes())
    mission = task_contract.load_mission_bytes(config.PIVOT_MISSION.read_bytes())
    return spec, snapshot_dict, snapshot, mission


def assert_usefully_completed(spec, snapshot, mission, envelope, request_ordinal):
    response = task_contract.validate_response_envelope(spec, json.dumps(envelope).encode())
    rows = evaluator.assess_request(spec=spec, request_ordinal=request_ordinal, mission=mission,
                                    snapshot=snapshot, response=response)
    assert rows and all(row.mandatory_pass for row in rows), rows
    assert evaluator.request_usefully_completed(spec, rows)


def test_protected_batch_ordinal_comes_from_the_served_request_counter(stub_gateway):
    """A protected one-request batch carries stimulus ordinal 3; the gateway policy ordinal is 1."""
    module = load_module()
    spec, snapshot_dict, snapshot, mission = protected_spec_snapshot_mission()
    envelope = module.answer(PROTECTED_BODY, snapshot_dict)
    infer_calls = [payload for path, payload in stub_gateway.calls if path == "/infer"]
    assert [payload["request_ordinal"] for payload in infer_calls] == [1]
    assert infer_calls[0]["input_text"].endswith(PROTECTED_BODY["text"])
    assert envelope["request_id"] == PROTECTED_BODY["request_id"]
    assert_usefully_completed(spec, snapshot, mission, envelope, request_ordinal=3)


@pytest.mark.parametrize("selected_tool", ["public_record_lookup", "public_catalog_search"])
def test_model_choice_routes_a_real_tool_call_and_still_passes(stub_gateway, selected_tool):
    stub_gateway.selected_tool = selected_tool
    module = load_module()
    spec, snapshot_dict, snapshot, mission = protected_spec_snapshot_mission()
    envelope = module.answer(PROTECTED_BODY, snapshot_dict)
    tool_calls = [payload for path, payload in stub_gateway.calls if path == "/tool"]
    assert tool_calls and tool_calls[0]["tool"] == selected_tool
    if selected_tool == "public_catalog_search":
        assert tool_calls[0]["genre"] == "coastal_travel"
    else:
        assert tool_calls[0]["entity_ref"] == "book:salt-roads:paperback"
    assert_usefully_completed(spec, snapshot, mission, envelope, request_ordinal=1)


def test_gateway_failure_falls_back_to_the_pinned_lookup_and_still_passes(stub_gateway):
    stub_gateway.infer_status = 503
    module = load_module()
    spec, snapshot_dict, snapshot, mission = protected_spec_snapshot_mission()
    envelope = module.answer(PROTECTED_BODY, snapshot_dict)
    methods = [path for path, _ in stub_gateway.calls]
    assert "/infer" in methods
    assert_usefully_completed(spec, snapshot, mission, envelope, request_ordinal=1)


def test_served_requests_number_consecutively_across_a_batch(stub_gateway):
    """Two served requests send ordinals 1 and 2 even when the bodies say 3 and 4."""
    module = load_module()
    snapshot_dict = json.loads(config.PIVOT_COMPARE_STATE.read_bytes())
    first = dict(PROTECTED_BODY)
    second = {**PROTECTED_BODY, "ordinal": 4, "request_id": "bellwether-protected-02"}
    module.answer(first, snapshot_dict)
    module.answer(second, snapshot_dict)
    infer_calls = [payload for path, payload in stub_gateway.calls if path == "/infer"]
    assert [payload["request_ordinal"] for payload in infer_calls] == [1, 2]


def test_http_handler_serves_the_envelope_over_the_real_wire(stub_gateway):
    """The shipped handler answers a POST with the validated envelope."""
    module = load_module()
    server = ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
    server.snapshot = json.loads(config.PIVOT_COMPARE_STATE.read_bytes())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
        connection.request("POST", "/", body=json.dumps(PROTECTED_BODY).encode(),
                           headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        body = json.loads(response.read())
        connection.close()
        assert response.status == 200
        spec, _, _, _ = protected_spec_snapshot_mission()
        task_contract.validate_response_envelope(spec, json.dumps(body).encode())
    finally:
        server.shutdown()
        thread.join(timeout=5)
