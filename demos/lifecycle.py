"""Full-route walkthrough: drive the whole HTTP lifecycle and print every record.

Walks the broader route surface (board, draft read/write, freeze, run, outputs,
checks, ledger, board, close) against the shipped controller default. Under the
shipped run binding (Slice 8) the recorded adapter replays the repair arc's first
attempt, so the run opens one incident per enabled family; the focused thin-path
evidence demo is demos.thin_path.

Run from the repository root: python -m demos.lifecycle
"""

import base64
import json
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from shiftwork.app import create_app  # noqa: E402

TERMINAL_RUN_STATES = {"FINALIZED", "FAILED"}

CONTRACT = {
    "catalog_version": 1,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
    "response_time_limit_ms": 3000,
    "declared_limits": ["Answers one fixed shelf-stock request per shift."],
}


def _show(label: str, payload) -> None:
    print(f"--- {label} ---")
    print(json.dumps(payload, indent=2, sort_keys=True))
    print()


def _call(client: TestClient, method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    body = response.json()
    if response.status_code >= 400:
        raise SystemExit(f"{method} {path} -> {response.status_code}: {body}")
    return response.status_code, body


def _poll_run(client: TestClient, run_id: str) -> dict:
    run = _call(client, "GET", f"/api/runs/{run_id}")[1]
    while run["state"] not in TERMINAL_RUN_STATES:
        time.sleep(0.05)
        run = _call(client, "GET", f"/api/runs/{run_id}")[1]
    return run


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="shiftwork-lifecycle-") as workdir:
        app = create_app(str(Path(workdir) / "lifecycle.db"))
        with TestClient(app) as client:
            status, board = _call(client, "GET", "/api/engagements/bookshop/board")
            _show(f"GET board (before) -> {status}", board)

            status, shift = _call(client, "POST", "/api/engagements/bookshop/shifts")
            _show(f"POST shift -> {status}", shift)
            shift_id = shift["id"]

            status, draft = _call(client, "GET", f"/api/shifts/{shift_id}/artifact")
            _show(f"GET artifact -> {status}", draft)

            files = dict(draft["files"])
            files["service.py"] += "\n# learner edit recorded by the lifecycle demo\n"
            status, saved = _call(
                client, "PUT", f"/api/shifts/{shift_id}/artifact", json={"files": files}
            )
            _show(
                f"PUT artifact -> {status}",
                {
                    "shift_id": saved["shift_id"],
                    "updated_at": saved["updated_at"],
                    "files": {name: f"<{len(text)} chars>" for name, text in saved["files"].items()},
                },
            )

            status, version = _call(
                client,
                "POST",
                f"/api/shifts/{shift_id}/artifact/versions",
                json={"contract": CONTRACT},
            )
            _show(f"POST freeze -> {status}", version)

            status, started = _call(client, "POST", f"/api/shifts/{shift_id}/runs")
            _show(f"POST run -> {status} (queued; execution runs off the request path)", started)
            run_id = started["id"]

            run = _poll_run(client, run_id)
            _show("GET run (after polling)", run)
            if run["state"] != "FINALIZED":
                raise SystemExit(f"run ended in unexpected state: {run['state']}")

            status, outputs = _call(client, "GET", f"/api/runs/{run_id}/outputs")
            decoded = [
                {**output, "body_text": base64.b64decode(output["body_base64"]).decode("utf-8")}
                for output in outputs
            ]
            _show(f"GET outputs -> {status}", decoded)

            status, checks = _call(client, "GET", f"/api/runs/{run_id}/checks")
            _show(f"GET checks -> {status}", checks)

            status, ledger = _call(client, "GET", "/api/engagements/bookshop/ledger")
            _show(f"GET ledger -> {status}", ledger)

            status, board = _call(client, "GET", "/api/engagements/bookshop/board")
            _show(f"GET board (after run) -> {status}", board)

            status, closed = _call(client, "POST", f"/api/shifts/{shift_id}/close")
            _show(f"POST close -> {status}", closed)

            print(
                f"lifecycle evidence complete: run {run_id} FINALIZED, ledger chain "
                f"{ledger['chain_status']} with {len(ledger['events'])} events, "
                f"{len(board['open_incidents'])} open incidents from the shipped "
                f"repair-arc replay"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
