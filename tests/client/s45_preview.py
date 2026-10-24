"""Offline S45 rendering fixture. No model call and no learner evidence."""

import argparse
import json
from pathlib import Path
import sys

import uvicorn
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "orchestrator"))
from conftest import BookshopShift
from test_experiment_lifecycle import _comparison_session
from test_comparison_repetitions import reserve

from shiftwork.app import create_app
from shiftwork.executor.base import RawObservation
from shiftwork.executor.local_process import LocalProcessAdapter


REASONING = "Operator-authored display fixture: <script>globalThis.s45Unsafe=true</script>"


def seed(database):
    execute = LocalProcessAdapter.execute
    public_calls = 0

    async def rendering_fixture(adapter, request):
        nonlocal public_calls
        result = await execute(adapter, request)
        public = request.single_request_ordinal is None
        if public:
            public_calls += 1
        failed = public and public_calls == 2
        captures = list(result.captures)
        if failed:
            body = json.loads(captures[0].body)
            body["task_results"] = [row for row in body["task_results"] if row["task_id"] != "collection"]
            captures[0] = captures[0].model_copy(update={"body": json.dumps(body).encode()})
        observations = []
        for capture in captures:
            payload = {"source": "operator-authored rendering fixture; no model call",
                "request_ordinal": capture.request_ordinal, "output_tokens": 1024 if failed else 128,
                "finish_reason": "length" if failed else "stop",
                "plan_failure": "SCHEMA_INVALID" if failed else None, "plan": [] if failed else None}
            observations.append(RawObservation(kind="INFERENCE_RESULT", public_payload=payload,
                raw_payload={"provider_response": {"choices": [{"message": {
                    "content": "" if failed else "{}", "reasoning": REASONING if public else "PROTECTED-ONLY-S45-REASON"}}]}}))
        return result.model_copy(update={"captures": tuple(captures), "observations": tuple(observations)})

    LocalProcessAdapter.execute = rendering_fixture
    try:
        with TestClient(create_app(database, executor="recorded")) as client:
            session = BookshopShift(client, Path(database))
            session.open()
            prepared = (session, *_comparison_session(session))
            response = reserve(prepared)
            assert response.status_code == 202, response.text
            print("S45 rendering fixture seeded. Operator-authored outputs, no model call.", flush=True)
    finally:
        LocalProcessAdapter.execute = execute


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    assert not Path(args.database).exists(), "Use a fresh disposable rendering database"
    seed(args.database)
    app = create_app(args.database, executor="recorded")
    app.state.hosted_runtime = {"hosted": False, "configured_executor": "recorded",
        "notice": "S45 RENDERING TEST. Operator-authored outputs and reasoning text; no model call or learner evidence."}
    print(f"Rendering fixture only: http://127.0.0.1:{args.port}/?board=bookshop#compare", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="error", access_log=False)


if __name__ == "__main__":
    main()
