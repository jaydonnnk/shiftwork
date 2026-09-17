"""Canonical Slice 1 evidence: drive the full HTTP lifecycle and print every record.

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
    with tempfile.TemporaryDirectory(prefix="shiftwork-tracer-") as workdir:
        app = create_app(str(Path(workdir) / "tracer.db"))
        with TestClient(app) as client:
            status, board = _call(client, "GET", "/api/engagements/bookshop/board")
            _show(f"GET board (before) -> {status}", board)

            status, shift = _call(client, "POST", "/api/engagements/bookshop/shifts")
            _show(f"POST shift -> {status}", shift)
            shift_id = shift["id"]

            status, draft = _call(client, "GET", f"/api/shifts/{shift_id}/draft")
            _show(f"GET draft -> {status}", draft)

            files = dict(draft["files"])
            files["service.py"] += "\n# learner edit recorded by the tracer demo\n"
            status, saved = _call(
                client, "PUT", f"/api/shifts/{shift_id}/draft", json={"files": files}
            )
            _show(
                f"PUT draft -> {status}",
                {
                    "shift_id": saved["shift_id"],
                    "updated_at": saved["updated_at"],
                    "files": {name: f"<{len(text)} chars>" for name, text in saved["files"].items()},
                },
            )

            status, version = _call(
                client, "POST", f"/api/shifts/{shift_id}/artifact/versions"
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
            if not board["open_incidents"]:
                raise SystemExit("board shows no open incident after the run")
            incident_id = board["open_incidents"][0]["id"]

            status, incident = _call(client, "GET", f"/api/incidents/{incident_id}")
            _show(f"GET incident {incident_id} -> {status}", incident)

            status, closed = _call(client, "POST", f"/api/shifts/{shift_id}/close")
            _show(f"POST close -> {status}", closed)

            print(
                f"lifecycle evidence complete: run {run_id} FINALIZED, incident {incident_id} "
                f"{incident['state']}, ledger chain {ledger['chain_status']} with "
                f"{len(ledger['events'])} events"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
