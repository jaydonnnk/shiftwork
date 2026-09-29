"""One authorized, bounded S15/S16 live comparison. Never retry this script."""

import argparse
import hashlib
import json
import os
import time
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from shiftwork import config
from shiftwork.app import create_app
from shiftwork.live_budget import LiveComparisonBudget
from shiftwork.store import db, repo


MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
RUN_DIR = Path("artifacts/slice16-live-2026-09-29")


def _load_local_credentials() -> None:
    # This file is ignored. Never print, log or persist either value.
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() in ("NEBIUS_API_KEY", "NEBIUS_PROJECT_ID"):
            os.environ.setdefault(key.strip(), value.strip().strip('"\''))
    if not os.environ.get("NEBIUS_API_KEY") or not os.environ.get("NEBIUS_PROJECT_ID"):
        raise RuntimeError("local Nebius credentials are unavailable")


def _wait_for_run(client: TestClient, run_id: str) -> dict:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        view = client.get(f"/api/runs/{run_id}").json()
        if view["state"] in ("FINALIZED", "FAILED"):
            return view
        time.sleep(0.1)
    raise RuntimeError("local source run did not terminate")


def main(*, preflight_only: bool = False) -> int:
    # Rates were checked against the public model card on 2026-09-29. The
    # one-shot date guard forces a fresh rate check for any later attempt.
    if time.strftime("%Y-%m-%d", time.gmtime()) != "2026-09-29":
        raise RuntimeError("live rates require a fresh same-day preflight")
    if config.SERVICE_MODEL != MODEL:
        raise RuntimeError("configured model differs from the checked rate card")
    meter = LiveComparisonBudget(MODEL, Decimal("0.06"), Decimal("0.24"))
    meter.preflight(model=config.SERVICE_MODEL, slots=6, requests=18)
    sealed_hashes = {
        config.PIVOT_COMPARE_MANIFEST:
            "2391255db772f42577ad2676c16a39b85b5867923334155f5dd129e8f5930e3f",
        config.SEALED_CASES_DIR / "bookshop_task_completion.json":
            "170dd925880b035c3a999512c982aaccaa2deda96e8d55950f4b7c14f0ce9a24",
    }
    if any(hashlib.sha256(path.read_bytes()).hexdigest() != expected
           for path, expected in sealed_hashes.items()):
        raise RuntimeError("operator-sealed fixture bytes changed")
    _load_local_credentials()
    if (RUN_DIR / "once.marker").exists():
        raise RuntimeError("the authorized one-shot run is already marked; no retry")
    if preflight_only:
        print(json.dumps({"preflight": "PASS", "slots": 6,
                          "max_sandbox_operations": 12, "max_inference_calls": 18,
                          "max_projected_inference_usd": "0.10",
                          "full_reservation_usd": str(
                              (meter.input_usd_per_million * meter.reserved_input_tokens_per_call
                               + meter.output_usd_per_million * meter.reserved_output_tokens_per_call)
                              * meter.max_calls / 1_000_000)}))
        return 0
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    marker = RUN_DIR / "once.marker"
    with marker.open("x", encoding="utf-8") as file:
        file.write("one authorized six-slot run; do not retry\n")
    db_file = RUN_DIR / "comparison.db"

    with TestClient(create_app(str(db_file), executor="local_process")) as client:
        shift = client.post("/api/engagements/bookshop/shifts")
        assert shift.status_code == 201, shift.text
        shift_id = shift.json()["id"]
        starter = client.post(f"/api/shifts/{shift_id}/artifact/versions",
                              json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
        assert starter.status_code == 201, starter.text
        source = client.post(f"/api/shifts/{shift_id}/runs")
        assert source.status_code == 202, source.text
        source_view = _wait_for_run(client, source.json()["id"])
        if source_view["state"] != "FINALIZED":
            raise RuntimeError("local diagnostic source failed")
        investigation = client.post(f"/api/shifts/{shift_id}/investigations", json={
            "source_run_id": source.json()["id"], "source_request_ordinal": 1,
            "cause": "the starter omits a required collection task",
            "falsifier": "the reviewed collection request still lacks that task result",
            "public_test": "require every declared task result",
            "revision_of_id": None, "client_request_id": "s16-live-investigation",
        })
        assert investigation.status_code == 201, investigation.text
        candidates = {}
        for label in ("A", "B"):
            saved = client.put(f"/api/shifts/{shift_id}/artifact",
                               json={"files": config.comparison_candidate_files(label)})
            assert saved.status_code == 200, saved.text
            frozen = client.post(f"/api/shifts/{shift_id}/artifact/versions",
                                 json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
            assert frozen.status_code == 201, frozen.text
            candidates[label] = frozen.json()
            if candidates[label]["content_hash"] != config.TRUSTED_LOCAL_FIXTURES[
                f"compare_candidate_{label.lower()}"][0]:
                raise RuntimeError("candidate bytes drifted from the reviewed pair")

    with TestClient(create_app(str(db_file), executor="tokenfactory",
                               live_comparison_budget=meter)) as client:
        created = client.post(f"/api/shifts/{shift_id}/experiments", json={
            "kind": "QUALIFYING_COMPARISON", "investigation_id": investigation.json()["id"],
            "candidate_a_version_id": candidates["A"]["id"],
            "candidate_b_version_id": candidates["B"]["id"],
            "declared_treatment": "A chooses lowest price; B chooses highest stock",
            "client_request_id": "s16-live-comparison-once",
        })
        if created.status_code != 202:
            raise RuntimeError(f"comparison reservation failed with HTTP {created.status_code}")
        experiment_id = created.json()["id"]
        view = client.get(f"/api/experiments/{experiment_id}").json()
    conn = db.connect(db_file)
    try:
        slots = repo.list_trial_slots(conn, experiment_id)
        evidence = {
            "experiment_id": experiment_id,
            "state": view["state"],
            "outcome": view["outcome"],
            "slot_states": [slot.state for slot in slots],
            "sandbox_operation_attempts": meter.operations,
            "inference_call_attempts": meter.calls,
            "projected_inference_usd": str(meter.projected_usd),
            "limit": {"slots": 6, "sandbox_operations": 12,
                      "inference_calls": 18, "projected_inference_usd": "0.10"},
            "source": "one authorized live run; no retry or top-up",
        }
    finally:
        conn.close()
    (RUN_DIR / "summary.json").write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({key: evidence[key] for key in (
        "state", "slot_states", "sandbox_operation_attempts", "inference_call_attempts",
        "projected_inference_usd")}, sort_keys=True))
    return 0 if view["state"] == "FINALIZED" else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    raise SystemExit(main(preflight_only=args.preflight_only))
