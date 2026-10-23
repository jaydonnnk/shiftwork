"""Rendering fixtures only. No reply here is observed model behavior."""
import argparse
import base64
import copy

import uvicorn

from demos import s43_task_plan
from shiftwork import config, experiments, orchestrator
from shiftwork.domain import task_contract
from shiftwork.gateway.service_inference import parse_task_plan
from shiftwork.app import create_app
from shiftwork.store import db


def fixture(shift_id):
    mission = task_contract.load_mission(config.PACKAGE_DIR / "fixtures/mission/bookshop_pivot_v2.json")
    trials = []
    for ordinal, (_, reply) in enumerate(s43_task_plan.CASES[:2], 1):
        body = s43_task_plan.run_starter_offline(reply)["responses"][0]["body"]
        assessments, _ = s43_task_plan.assess(body)
        plan, plan_failure = parse_task_plan(reply, tuple(mission.task_vocabulary),
                                             tuple(mission.allowed_tool_vocabulary))
        trials.append({"execution_ordinal": ordinal, "candidate_label": "A", "workload_id": "render-fixture",
            "artifact_version_id": "fixture-starter", "artifact_content_hash": "render-fixture",
            "request_batch_hash": "render-fixture", "request_count": 1, "run_id": f"fixture-run-{ordinal}",
            "state": "COMPLETE", "evidence_mode": "OPERATOR_AUTHORED_TEST_REPLY",
            "task_assessments": [row.model_dump(mode="json") for row in assessments],
            "observations": [{"kind": "INFERENCE_RESULT", "public_payload_json": {
                "label": "Operator-authored rendering fixture. No model call.", "reply_text": reply,
                "request_ordinal": 1, "plan": plan, "plan_failure": plan_failure}}],
            "outputs": [{"request_ordinal": 1, "request_text": "Rendering fixture: collect Salt Roads, or suggest an alternative under £20.",
                "http_status": 200, "body_base64": base64.b64encode(body.encode()).decode(),
                "elapsed_ms": 10, "transport_error": None}],
            "customer_text": "Operator-authored test reply, not model output.", "missing_evidence": [], "metrics": None})
    return {"id": "render-fixture", "shift_id": shift_id, "kind": "DIAGNOSTIC", "investigation_id": None,
        "declared_treatment": "Operator-authored rendering fixture. No model call or recorded live evidence.",
        "context_hash": "render-fixture", "context_evidence_class": "OPERATOR_AUTHORED_TEST_REPLY",
        "workloads": [{"id": "render-fixture", "ordinal": 1, "request_batch_hash": "render-fixture", "request_count": 1}],
        "candidates": [{"label": "A", "artifact_version_id": "fixture-starter", "artifact_content_hash": "render-fixture"}],
        "trials": trials, "eligible": False, "eligibility_reason": "A rendering fixture cannot qualify a version.",
        "state": "FINALIZED", "public_repetitions": 2, "summary_refusal": None,
        "repetition_summary": {"retained_repetitions": 2, "run_ids": ["fixture-run-1", "fixture-run-2"],
            "limits": "Operator-authored test replies, not model output. Live results cover one model, one request set and a small sample.",
            "stop_rule_triggered": False, "tasks": [
                {"request_id": "bellwether-collection-001", "task_id": "collection", "misses": 0, "total": 2, "miss_run_ids": []},
                {"request_id": "bellwether-collection-001", "task_id": "alternative", "misses": 1, "total": 2, "miss_run_ids": ["fixture-run-2"]}]}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    conn = db.connect(args.database)
    db.ensure_schema(conn)
    orchestrator.seed_registered_engagements(conn)
    shift = orchestrator.open_next_shift(conn, "bookshop", executor_name="recorded")
    conn.close()
    sample = fixture(shift.id)
    original = experiments.investigate_station

    def station(*args, **kwargs):
        result = original(*args, **kwargs)
        result["latest_diagnostic"] = copy.deepcopy(sample)
        return result

    experiments.investigate_station = station
    app = create_app(args.database, executor="recorded")
    app.state.hosted_runtime = {"hosted": False, "configured_executor": "recorded",
        "notice": "S44 RENDERING TEST: operator-authored replies. No model calls or recorded live evidence."}
    print(f"Rendering fixture only: http://127.0.0.1:{args.port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="error", access_log=False)


if __name__ == "__main__":
    main()
