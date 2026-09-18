"""Canonical Slice 2 evidence: drive one shift's data real end to end and print every record.

For one bookshop shift this prints the frozen version's real content_hash, the one
executed request's captured output bytes, the one sealed case's CheckResult (reason
code + opaque expected_ref), and the one hash-chained ledger event with
chain_status VALID. Nothing is mocked: a placeholder hash or a missing row would
fail the assertions below.

Run from the repository root: python -m demos.thin_path
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

from shiftwork import config  # noqa: E402
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
    with tempfile.TemporaryDirectory(prefix="shiftwork-thin-") as workdir:
        app = create_app(str(Path(workdir) / "thin.db"))
        with TestClient(app) as client:
            status, shift = _call(client, "POST", "/api/engagements/bookshop/shifts")
            _show(f"POST shift -> {status}", shift)
            shift_id = shift["id"]

            status, version = _call(
                client,
                "POST",
                f"/api/shifts/{shift_id}/artifact/versions",
                json={"contract": CONTRACT},
            )
            _show(f"POST freeze -> {status}", version)
            content_hash = version["content_hash"]
            if len(content_hash) != 64 or "placeholder" in content_hash:
                raise SystemExit(f"freeze did not produce a real content hash: {content_hash!r}")

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
            _show(f"GET outputs -> {status} (the one captured request)", decoded)
            if len(outputs) != 1:
                raise SystemExit(f"expected exactly one captured output, got {len(outputs)}")

            status, checks = _call(client, "GET", f"/api/runs/{run_id}/checks")
            _show(f"GET checks -> {status} (the one real CheckResult)", checks)
            if len(checks) != 1:
                raise SystemExit(f"expected exactly one CheckResult, got {len(checks)}")
            check = checks[0]
            if not check["expected_ref"].startswith("sealed:"):
                raise SystemExit(f"expected_ref is not an opaque sealed ref: {check['expected_ref']!r}")

            status, ledger = _call(client, "GET", "/api/engagements/bookshop/ledger")
            _show(f"GET ledger -> {status} (the one hash-chained event)", ledger)
            if ledger["chain_status"] != "VALID":
                raise SystemExit(f"chain did not verify: {ledger['chain_status']}")
            if len(ledger["events"]) != 1:
                raise SystemExit(f"expected exactly one ledger event, got {len(ledger['events'])}")
            event = ledger["events"][0]
            if event["prev_hash"] != config.GENESIS_HASH or len(event["hash"]) != 64:
                raise SystemExit(f"event is not a real chained event: {event!r}")

            status, board = _call(client, "GET", "/api/engagements/bookshop/board")
            _show(f"GET board (after run) -> {status}", board)

            print(
                "thin-path evidence complete: run "
                f"{run_id} FINALIZED, content_hash {content_hash}, one CheckResult "
                f"{check['verdict']}/{check['reason_code']} with opaque expected_ref, one "
                f"{event['event_type']} event seq {event['seq']} chained on genesis, "
                f"chain_status {ledger['chain_status']}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
