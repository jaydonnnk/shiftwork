"""Read-only audit of the one-shot comparison database; prints public counts only."""

import json
from pathlib import Path

from shiftwork.store import db, repo


def main() -> int:
    root = Path("artifacts/slice16-live-2026-09-29")
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    conn = db.connect(root / "comparison.db")
    try:
        slots = repo.list_trial_slots(conn, summary["experiment_id"])
        runs = [repo.get_run(conn, slot.run_id) for slot in slots]
        observations = [item for run in runs for item in repo.list_observations(conn, run.id)]
        outputs = [item for run in runs for item in repo.list_outputs(conn, run.id)]
        operations = [item for item in observations if item.public_payload_json.get("operation_bound") is True]
        meters = [item for item in observations if item.public_payload_json.get("inference_meter_complete") is True]
        calls = [item for item in observations if item.kind.value == "INFERENCE_REQUEST"]
        readbacks = [item for item in observations if item.public_payload_json.get("checkpoint_readback") is True]
        counts = {
            "slots": len(slots), "complete_slots": sum(slot.state == "COMPLETE" for slot in slots),
            "sandbox_operations_recorded": len(operations),
            "controller_meters": len(meters), "inference_requests_recorded": len(calls),
            "captures": len(outputs), "verified_checkpoint_readbacks": len(readbacks),
            "metered_service_calls": sum(item.public_payload_json["service_calls"] for item in meters),
        }
        passed = (counts == {"slots": 6, "complete_slots": 6, "sandbox_operations_recorded": 12,
                             "controller_meters": 18, "inference_requests_recorded": 0,
                             "captures": 18, "verified_checkpoint_readbacks": 18,
                             "metered_service_calls": 0}
                  and summary["sandbox_operation_attempts"] == 12
                  and summary["inference_call_attempts"] == 0
                  and all(run.adapter == "tokenfactory" and run.evidence_mode.value == "ISOLATED_LIVE"
                          for run in runs))
        print(json.dumps({"verdict": "PASS" if passed else "FAIL", **counts}, sort_keys=True))
        return 0 if passed else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
