"""Serve an isolated client preview backed by pinned recorded inspections."""

import argparse
import os
import tempfile
from pathlib import Path

import uvicorn
from fastapi.testclient import TestClient

from shiftwork import config
from shiftwork.app import create_app
from shiftwork.assist.gateway import AssistReply, LiveAssistGateway


class RecordedAssistGateway:
    """Visible offline demonstration, never a model-quality claim."""

    model_id = "recorded-assist-double"

    def generate(self, *, model_id, role, prompt):
        if role.value == "PATCH_PROPOSAL":
            return AssistReply("Proposal for learner review only: check collection and alternative tasks separately before composing the answer.")
        if role.value == "DIAGNOSIS":
            return AssistReply("Possible diagnosis to test: the service routed on price and omitted other requested tasks. Your public test could disprove this.")
        return AssistReply("Check the collection and alternative tasks against the exact public request and your falsifier.")


def _execute_attempts(client: TestClient, shift_id: str, count: int = 2) -> None:
    """Start ``count`` operational attempts and require each one to finalize."""
    for _ in range(count):
        started = client.post(f"/api/shifts/{shift_id}/runs")
        started.raise_for_status()
        run = client.get(f"/api/runs/{started.json()['id']}").json()
        if run["state"] != "FINALIZED":
            raise RuntimeError(f"Preview fixture did not finalize: {run['state']}")


def create_preview(db_path: str, *, empty: bool = False, selection_factory=None,
                   recorded_assist: bool = False, live_assist: bool = False):
    """Build an isolated preview database and return its app.

    The shipped preview (no factory) opens the first Bellwether shift: Slice 11
    seeds the reviewed failing starter as the operating baseline, so two attempts
    replay the pinned recorded inspections the room shows and the Investigate
    station cites as its source. That run path writes no learner choice.

    ``selection_factory(db_path, shift_id, version_id)`` is a test-layer hook for
    the Slice 8 executed-fixture scenario: it freezes the pre-repair candidate,
    installs the test-only selection and really executes it twice under
    ``local_process``. The shipped CLI passes nothing, so no ``LEARNER_CHOICE``
    row is written outside a test.
    """
    if Path(db_path).exists():
        raise ValueError("Preview requires a new database; existing work is never overwritten.")
    if recorded_assist and live_assist:
        raise ValueError("choose one assist mode")
    if live_assist and not os.environ.get("NEBIUS_API_KEY"):
        raise ValueError("NEBIUS_API_KEY is required for --live-assist")
    gateway = (RecordedAssistGateway() if recorded_assist else
               LiveAssistGateway(os.environ["NEBIUS_API_KEY"]) if live_assist else None)
    app = create_app(db_path, executor="local_process" if selection_factory else None,
                     assist_gateway=gateway)
    with TestClient(app) as client:
        if not empty:
            shift = client.post("/api/engagements/bookshop/shifts")
            shift.raise_for_status()
            shift_id = shift.json()["id"]
            if selection_factory is not None:
                saved = client.put(
                    f"/api/shifts/{shift_id}/artifact",
                    json={"files": config.repair_arc_artifact_files("pre")},
                )
                saved.raise_for_status()
                frozen = client.post(
                    f"/api/shifts/{shift_id}/artifact/versions",
                    json={"contract": config.REPAIR_ARC_CONTRACT_JSON},
                )
                frozen.raise_for_status()
                selection_factory(db_path, shift_id, frozen.json()["id"])
            _execute_attempts(client, shift_id, 2)
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8009)
    parser.add_argument("--empty", action="store_true")
    parser.add_argument("--recorded-assist", action="store_true",
                        help="Enable labelled recorded help for an offline UI demonstration")
    parser.add_argument("--live-assist", action="store_true",
                        help="Enable up to three live help calls using NEBIUS_API_KEY; requires separate authorization")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="shiftwork-client-") as directory:
        app = create_preview(str(Path(directory) / "preview.db"), empty=args.empty,
                             recorded_assist=args.recorded_assist, live_assist=args.live_assist)
        print(f"Preview: http://127.0.0.1:{args.port}", flush=True)
        print("Isolated temporary scenario. Service inspections are recorded. Ctrl+C stops it.", flush=True)
        print("The reviewed failing starter is the operating baseline; the Investigate station runs it against its pinned incident request.", flush=True)
        if args.recorded_assist:
            print("Assist is a recorded double; no model call or model-quality evidence is produced.", flush=True)
        if args.live_assist:
            print("Assist uses live Token Factory inference on learner request; up to three calls per shift.", flush=True)
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
