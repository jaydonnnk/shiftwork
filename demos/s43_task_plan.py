"""S43 offline demo: the Bellwether task-plan starter acts only on the returned plan.

The starter runs as a subprocess against the real trusted driver handler and
the real plan-mode gateway. The provider is replaced by a local test stand-in
that returns operator-authored test replies; nothing here calls a model, and
no reply is model output or a RECORDED_INSPECTION. Each answer is assessed by
the deterministic evaluator against mission v2 and the reviewed public state.

Run: ``python -m demos.s43_task_plan``.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

from shiftwork import config
from shiftwork.domain import task_contract
from shiftwork.evaluator import evaluator
from shiftwork.executor.tokenfactory import DRIVER_SOURCE
from shiftwork.gateway.protocol import InferencePolicy
from shiftwork.gateway.service_inference import GatewayRejected, ServiceInferenceGateway

MISSION = config.FIXTURE_DIR / "mission" / "bookshop_pivot_v2.json"
STARTER = config.bellwether_starter_files("fixtures/mission/bookshop_pivot_v2.json")["service.py"]
TEST_REPLY_LABEL = "test reply (operator-authored fixture, not model output)"


def _plan(*steps: tuple[str, str]) -> str:
    return json.dumps({"plan": [{"task_type": task, "tool_name": tool} for task, tool in steps]})


# Operator-authored test replies. Each stands in for one provider reply.
CASES = (
    ("full plan", _plan(("collection", "public_availability_lookup"),
                        ("alternative", "public_catalog_search"), ("price", "public_price_lookup"))),
    ("omits the conditional alternative", _plan(("collection", "public_availability_lookup"),
                                                ("price", "public_price_lookup"))),
    ("names an unlisted tool", _plan(("collection", "web_search"),
                                     ("alternative", "public_catalog_search"))),
)


class _TestReplyProvider:
    """Stands in for the provider HTTP client; returns one fixed test reply."""

    def __init__(self, content: str):
        self.content = content

    async def post(self, url, *, headers, json):
        body = {"model": json["model"], "choices": [{"message": {"content": self.content},
                                                     "finish_reason": "stop"}],
                "usage": {"prompt_tokens": None, "completion_tokens": None}}
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))


_DRIVER_TAIL = '''
server = ThreadingHTTPServer(('127.0.0.1', 0), GatewayHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()
service = subprocess.Popen([sys.executable, '-I', '-B', str(ROOT / 'service.py')], cwd=str(ROOT),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env={'SHIFTWORK_GATEWAY_PORT': str(server.server_port)})
port = json.loads(service.stdout.readline())['port']
for line in (ROOT / 'requests.jsonl').read_text().splitlines():
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=30)
    conn.request('POST', '/', body=line.encode(), headers={'Content-Type': 'application/json'})
    response = conn.getresponse()
    send_line({'kind': 'service_response', 'status': response.status,
               'body': response.read().decode('utf-8', 'replace')})
service.terminate()
send_line({'kind': 'done', 'events': events,
           'service_log': service.stderr.read().decode('utf-8', 'replace')})
'''


def run_starter_offline(reply: str, *, starter_source: str | None = None) -> dict:
    """Run the starter once over the incident request with one test reply per request."""
    mission = task_contract.load_mission(MISSION)
    tools = tuple(mission.allowed_tool_vocabulary)
    vocabulary = tuple(mission.task_vocabulary)
    head = DRIVER_SOURCE.decode().split("def drop_privileges():", 1)[0]
    gateway_codes = []
    responses = []
    with tempfile.TemporaryDirectory(prefix="shiftwork-s43-demo-") as directory:
        root = Path(directory)
        (root / "shop.json").write_bytes(config.PIVOT_PUBLIC_STATE.read_bytes())
        (root / "requests.jsonl").write_bytes(config.PIVOT_INCIDENT_REQUESTS.read_bytes())
        (root / "service.py").write_text(starter_source or STARTER.read_text(encoding="utf-8"), encoding="utf-8")
        (root / "driver.py").write_text(
            head.replace("ROOT = Path('/work')", "ROOT = Path(" + repr(str(root)) + ")") + _DRIVER_TAIL,
            encoding="utf-8")
        driver = subprocess.Popen([sys.executable, "-I", "-B", str(root / "driver.py")],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        driver.stdin.write(json.dumps({"allowed_tool_names": list(tools)}) + "\n")
        driver.stdin.flush()
        ordinal = 0
        try:
            for line in driver.stdout:
                event = json.loads(line)
                if event["kind"] == "inference_request":
                    ordinal += 1
                    gateway = ServiceInferenceGateway("TEST_GATEWAY_NO_PROVIDER", InferencePolicy(
                        run_id="s43-demo", operation_id="s43-demo-op", model="test-reply-stand-in",
                        allowed_tool_names=tools, task_vocabulary=vocabulary, request_ordinal=ordinal,
                    ), http=_TestReplyProvider(reply))
                    try:
                        answer = asyncio.run(gateway.infer("s43-demo-op", event["request"]))
                    except GatewayRejected as exc:
                        answer = {"kind": "inference_reply", "error": exc.code}
                    gateway_codes.append(answer.get("plan_failure") or answer.get("error"))
                    driver.stdin.write(json.dumps(answer) + "\n")
                    driver.stdin.flush()
                elif event["kind"] == "service_response":
                    responses.append(event)
                elif event["kind"] == "done":
                    done = event
                    break
        finally:
            driver.kill()
            driver.wait()
    return {"responses": responses, "gateway_codes": gateway_codes, **done}


def assess(response_body: str) -> tuple[tuple[evaluator.TaskAssessment, ...], bool]:
    """Assess one captured answer against mission v2 and the reviewed public state."""
    mission = task_contract.load_mission(MISSION)
    snapshot = task_contract.load_public_state(config.PIVOT_PUBLIC_STATE)
    spec = mission.request_specs[0]
    try:
        response = task_contract.validate_response_envelope(spec, response_body.encode("utf-8"))
    except task_contract.TaskEnvelopeInvalid:
        response = None
    assessments = evaluator.assess_request(spec=spec, request_ordinal=1, mission=mission,
                                           snapshot=snapshot, response=response)
    return assessments, evaluator.request_usefully_completed(spec, assessments)


def main() -> int:
    print("S43 offline demo. Every reply below is a " + TEST_REPLY_LABEL + ".")
    print("No model is called; nothing here is RECORDED_INSPECTION or fresh execution.")
    for name, reply in CASES:
        outcome = run_starter_offline(reply)
        print(f"\n== {name} ==")
        print(f"test reply: {reply}")
        print(f"gateway plan_failure: {outcome['gateway_codes'][0]}")
        for captured in outcome["responses"]:
            assessments, useful = assess(captured["body"])
            print(f"service answer: {captured['body']}")
            for item in assessments:
                codes = ",".join(code.value for code in item.reason_codes) or "-"
                print(f"  check {item.task_id}: {item.outcome.value} mandatory_pass={item.mandatory_pass} reasons={codes}")
            print(f"  request usefully completed: {useful}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
