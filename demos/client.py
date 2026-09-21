"""Serve an isolated client preview backed by executed Slice 8 trusted fixtures."""

import argparse
import tempfile
from pathlib import Path

import uvicorn
from fastapi.testclient import TestClient

from shiftwork import config
from shiftwork.app import create_app


def create_preview(db_path: str, *, empty: bool = False):
    if Path(db_path).exists():
        raise ValueError("Preview requires a new database; existing work is never overwritten.")
    app = create_app(db_path, executor="local_process")
    with TestClient(app) as client:
        if not empty:
            shift = client.post("/api/engagements/bookshop/shifts")
            shift.raise_for_status()
            shift_id = shift.json()["id"]
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
            for _ in range(2):
                started = client.post(f"/api/shifts/{shift_id}/runs")
                started.raise_for_status()
                run = client.get(f"/api/runs/{started.json()['id']}").json()
                if run["state"] != "FINALIZED":
                    raise RuntimeError(f"Trusted preview fixture did not finalize: {run['state']}")
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8009)
    parser.add_argument("--empty", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="shiftwork-client-") as directory:
        app = create_preview(str(Path(directory) / "preview.db"), empty=args.empty)
        print(f"Preview: http://127.0.0.1:{args.port}", flush=True)
        print("Isolated temporary scenario. Pinned trusted fixtures only; no live services. Ctrl+C stops it.", flush=True)
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
