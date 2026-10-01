"""One authorized, linked S20 live chain: model repair, selection, operation, inheritance.

One-shot by design. The date guard and the ``once.marker`` force every live
attempt to be its own same-day decision: the rates were checked against the
public model card on 2026-10-01 ($0.06 per million input tokens, $0.24 per
million output tokens; the Sandboxes page states runs are free while in beta).
Run ``--preflight-only`` first; it checks the guards, prints and spends nothing.
``--offline-rehearsal`` runs the same API sequence against the pinned A/B pair
under the local executor and writes only under its own rehearsal directory; it
proves the flow and never the live path. Run from the repository root with
``.venv313/Scripts/python.exe -m demos.slice20_live_chain``.

The chain: a local starter operation opens incidents, an investigation cites it,
the model-calling candidate (A) and the reviewed repair B freeze, the qualifying
comparison runs under the Token Factory adapter with a bounded meter, the learner
selects A by exact version and hash, the next shift operates that exact version
live, and the shift after it inherits the selection and the sale.
"""

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
from shiftwork.domain.models import LedgerEventType, ObservationKind
from shiftwork.live_budget import LiveComparisonBudget, LiveOperationBudget
from shiftwork.store import db, repo

MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
INPUT_USD_PER_MILLION = Decimal("0.06")
OUTPUT_USD_PER_MILLION = Decimal("0.24")
RUN_DIR = Path("artifacts/slice20-live-chain-resume-2026-10-01")
REHEARSAL_DIR = Path("artifacts/slice20-live-chain-rehearsal-2026-10-01")
MODEL_CANDIDATE = config.FIXTURE_DIR / "artifacts" / "bookshop" / "compare_repair_model_service.py"
MODEL_CANDIDATE_SHA256 = "fd770c1d86707ae8b69043939316a5e44fedc721641ab86ff529033290f26248"
SEALED_GUARDS = {
    config.PIVOT_COMPARE_MANIFEST:
        "2391255db772f42577ad2676c16a39b85b5867923334155f5dd129e8f5930e3f",
    config.SEALED_CASES_DIR / "bookshop_task_completion.json":
        "170dd925880b035c3a999512c982aaccaa2deda96e8d55950f4b7c14f0ce9a24",
}


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_static_guards() -> dict:
    guards = {
        str(path): {"expected": expected, "actual": _sha256_path(path)}
        for path, expected in SEALED_GUARDS.items()
    }
    guards[str(MODEL_CANDIDATE)] = {
        "expected": MODEL_CANDIDATE_SHA256, "actual": _sha256_path(MODEL_CANDIDATE),
    }
    if any(item["expected"] != item["actual"] for item in guards.values()):
        raise RuntimeError("guarded bytes changed; refusing the chain")
    return guards


def _load_local_credentials() -> None:
    # This file is ignored. Never print, log or persist either value.
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        key = key.strip()
        if separator and key in ("NEBIUS_API_KEY", "NEBIUS_PROJECT_ID"):
            value = value.strip().strip("\"'")
            if not os.environ.get(key):
                os.environ[key] = value
    if not os.environ.get("NEBIUS_API_KEY") or not os.environ.get("NEBIUS_PROJECT_ID"):
        raise RuntimeError("local Nebius credentials are unavailable")
    # The support-provided AI project id is an aiproject-... value; the local
    # project-... id authenticates but lacks Sandbox permissions (2026-09-26).
    if not os.environ["NEBIUS_PROJECT_ID"].startswith("aiproject-"):
        raise RuntimeError("NEBIUS_PROJECT_ID is not the support-provided AI project id")


def _prepare_live() -> dict:
    if time.strftime("%Y-%m-%d", time.gmtime()) != "2026-10-01":
        raise RuntimeError("live rates require a fresh same-day preflight")
    if config.SERVICE_MODEL != MODEL:
        raise RuntimeError("configured model differs from the checked rate card")
    comparison = LiveComparisonBudget(MODEL, INPUT_USD_PER_MILLION, OUTPUT_USD_PER_MILLION)
    comparison.preflight(model=config.SERVICE_MODEL, slots=6, requests=18)
    operation = LiveOperationBudget(MODEL, INPUT_USD_PER_MILLION, OUTPUT_USD_PER_MILLION)
    operation.preflight(model=config.SERVICE_MODEL, requests=1)
    guards = _check_static_guards()
    _load_local_credentials()
    if (RUN_DIR / "once.marker").exists():
        raise RuntimeError("the authorized one-shot run is already marked; no retry")
    return {"comparison": comparison, "operation": operation, "guards": guards}


def _expect(response, status: int, what: str) -> None:
    if response.status_code != status:
        raise RuntimeError(f"{what} failed with HTTP {response.status_code}: {response.text[:400]}")


def _wait_run(client: TestClient, run_id: str, *, deadline_s: float = 600.0) -> dict:
    deadline = time.monotonic() + deadline_s
    while True:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["state"] in ("FINALIZED", "FAILED") or time.monotonic() > deadline:
            return run
        time.sleep(0.2)


def _wait_experiment(client: TestClient, experiment_id: str, *, deadline_s: float = 3600.0) -> dict:
    deadline = time.monotonic() + deadline_s
    while True:
        view = client.get(f"/api/experiments/{experiment_id}").json()
        if view["state"] in ("FINALIZED", "FAILED", "INVALIDATED") or time.monotonic() > deadline:
            return view
        time.sleep(0.2)


def _inference_rows(conn, run_ids: list[str]) -> list[dict]:
    rows = []
    for run_id in run_ids:
        for observation in repo.list_observations(conn, run_id):
            if observation.kind is not ObservationKind.INFERENCE_RESULT:
                continue
            payload = dict(observation.public_payload_json)
            rows.append({
                "run_id": run_id, "request_ordinal": observation.request_ordinal,
                "model": payload.get("model"), "selected_tool": payload.get("selected_tool"),
                "failure": payload.get("failure"), "input_tokens": payload.get("input_tokens"),
                "output_tokens": payload.get("output_tokens"),
                "finish_reason": payload.get("finish_reason"),
            })
    return rows


def _meter_record(meter) -> dict:
    per_call = (meter.input_usd_per_million * meter.reserved_input_tokens_per_call
                + meter.output_usd_per_million * meter.reserved_output_tokens_per_call) / 1_000_000
    return {
        "sandbox_operations": meter.operations,
        "inference_call_attempts": meter.calls,
        "projected_inference_usd": str(meter.projected_usd),
        "reservation_ceiling_usd": str(per_call * meter.max_calls),
    }


def _run_chain(*, live: bool, meters: dict | None, guards: dict, summary: dict) -> str:
    prefix = "s20-live" if live else "s20-rehearsal"
    run_dir = RUN_DIR if live else REHEARSAL_DIR
    run_dir.mkdir(parents=True, exist_ok=True)
    if live:
        with (run_dir / "once.marker").open("x", encoding="utf-8") as handle:
            handle.write("one authorized linked live chain; do not retry\n")
    summary["guards"] = guards
    summary["ceilings"] = (
        {"comparison": _meter_record(meters["comparison"])["reservation_ceiling_usd"],
         "operation": _meter_record(meters["operation"])["reservation_ceiling_usd"]}
        if meters else {"comparison": None, "operation": None}
    )
    db_file = run_dir / ("live-chain.db" if live else "rehearsal.db")

    print(f"[{prefix}] phase A: starter operation, investigation, candidates", flush=True)
    # The starter source run uses the controller default (recorded): its reviewed
    # transcript replays the pinned starter failure and opens the shift's first
    # incidents. The local_process attempt path would instead run the legacy
    # family batch and record backlog events, which this chain does not want.
    with TestClient(create_app(str(db_file))) as client:
        shift = client.post("/api/engagements/bookshop/shifts")
        _expect(shift, 201, "open the first shift")
        shift_id = shift.json()["id"]
        if shift_id != "bookshop-shift-01":
            raise RuntimeError(f"unexpected first shift id: {shift_id}")
        prior = client.get("/api/engagements/bookshop/board").json()["operating_selection"]
        if prior is None or prior["id"] != "sel-0001" or prior["kind"] != "STARTER_BASELINE":
            raise RuntimeError("the starter baseline selection sel-0001 is missing")
        starter = client.post(f"/api/shifts/{shift_id}/artifact/versions",
                              json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
        _expect(starter, 201, "freeze the starter draft")
        if starter.json()["content_hash"] != config.TRUSTED_LOCAL_FIXTURES["pivot_starter"][0]:
            raise RuntimeError("frozen starter bytes differ from the reviewed pin")
        source = client.post(f"/api/shifts/{shift_id}/runs",
                             json={"client_request_id": f"{prefix}-starter-run"})
        _expect(source, 202, "start the starter operation")
        starter_run = _wait_run(client, source.json()["id"])
        if starter_run["state"] != "FINALIZED":
            raise RuntimeError(f"starter operation did not finalize: {starter_run['state']}")
        investigation = client.post(f"/api/shifts/{shift_id}/investigations", json={
            "source_run_id": starter_run["id"], "source_request_ordinal": 1,
            "cause": "the starter omits the required collection and alternative task results",
            "falsifier": "the reviewed collection request still lacks a collection outcome",
            "public_test": "require every declared required task result",
            "revision_of_id": None, "client_request_id": f"{prefix}-investigation",
        })
        _expect(investigation, 201, "append the investigation")
        if live:
            candidate_a_text = MODEL_CANDIDATE.read_bytes().decode("utf-8")
            if hashlib.sha256(candidate_a_text.encode("utf-8")).hexdigest() != MODEL_CANDIDATE_SHA256:
                raise RuntimeError("the model-candidate bytes differ from the guarded digest")
        else:
            candidate_a_text = config.comparison_candidate_files("A")["service.py"]
        saved = client.put(f"/api/shifts/{shift_id}/artifact",
                           json={"files": {"service.py": candidate_a_text}})
        _expect(saved, 200, "save candidate A")
        frozen_a = client.post(f"/api/shifts/{shift_id}/artifact/versions",
                               json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
        _expect(frozen_a, 201, "freeze candidate A")
        candidate_a = frozen_a.json()
        if not live and candidate_a["content_hash"] != config.TRUSTED_LOCAL_FIXTURES["compare_candidate_a"][0]:
            raise RuntimeError("offline candidate A bytes differ from the pinned pair")
        saved = client.put(f"/api/shifts/{shift_id}/artifact",
                           json={"files": config.comparison_candidate_files("B")})
        _expect(saved, 200, "save the retained alternative")
        frozen_b = client.post(f"/api/shifts/{shift_id}/artifact/versions",
                               json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
        _expect(frozen_b, 201, "freeze the retained alternative")
        candidate_b = frozen_b.json()
        if candidate_b["content_hash"] != config.TRUSTED_LOCAL_FIXTURES["compare_candidate_b"][0]:
            raise RuntimeError("candidate B bytes differ from the reviewed pin")

    conn = db.connect(str(db_file))
    try:
        events = repo.list_ledger_events(conn, "bookshop")
    finally:
        conn.close()
    opened = [event for event in events if event.event_type is LedgerEventType.INCIDENT_OPENED
              and starter_run["id"] in event.cause_refs]
    sales = [event for event in events if event.event_type is LedgerEventType.SALE_COMPLETED
             and starter_run["id"] in event.cause_refs]
    if not opened or sales:
        raise RuntimeError("the starter operation should open incidents and complete no sale")
    summary["phase_a"] = {
        "shift_id": shift_id, "starter_version_hash": starter.json()["content_hash"],
        "starter_run": {"id": starter_run["id"], "state": starter_run["state"],
                        "evidence_mode": starter_run["evidence_mode"]},
        "incident_events": [event.seq for event in opened], "sale_events_for_run": len(sales),
        "investigation_id": investigation.json()["id"],
        "candidate_a": {"version_id": candidate_a["id"], "content_hash": candidate_a["content_hash"],
                        "source": "model_candidate" if live else "pinned_offline_pair"},
        "candidate_b": {"version_id": candidate_b["id"], "content_hash": candidate_b["content_hash"]},
    }

    print(f"[{prefix}] phase B: qualifying comparison", flush=True)
    if live:
        app = create_app(str(db_file), executor="tokenfactory",
                         live_comparison_budget=meters["comparison"],
                         live_operation_budget=meters["operation"])
    else:
        app = create_app(str(db_file), executor="local_process")
    with TestClient(app) as client:
        created = client.post(f"/api/shifts/{shift_id}/experiments", json={
            "kind": "QUALIFYING_COMPARISON", "investigation_id": investigation.json()["id"],
            "candidate_a_version_id": candidate_a["id"],
            "candidate_b_version_id": candidate_b["id"],
            "declared_treatment": ("A routes its first public lookup through the frozen model "
                                   "gateway; B applies the guard rules only"),
            "client_request_id": f"{prefix}-comparison-once",
        })
        _expect(created, 202, "reserve the qualifying comparison")
        comparison = _wait_experiment(client, created.json()["id"])
        outcome = comparison.get("outcome") or {}
        eligibility = {item["candidate_label"]: item for item in outcome.get("eligibility", [])}
        conn = db.connect(str(db_file))
        try:
            slots = repo.list_trial_slots(conn, comparison["id"])
            inference_rows = (_inference_rows(conn, [slot.run_id for slot in slots if slot.run_id])
                              if live else [])
        finally:
            conn.close()
        phase_b = {
            "experiment_id": comparison["id"], "state": comparison["state"],
            "outcome_status": outcome.get("status"),
            "slot_states": [slot.state for slot in slots],
            "candidate_metrics": outcome.get("candidate_metrics"),
            "eligibility": outcome.get("eligibility"),
            "drift_fields": outcome.get("drift_fields"),
            "inference_results": inference_rows,
            "successful_inference_results": sum(
                1 for row in inference_rows if row["model"] and not row["failure"]),
        }
        if live:
            phase_b.update(_meter_record(meters["comparison"]))
        summary["phase_b"] = phase_b
        if comparison["state"] != "FINALIZED" or outcome.get("status") != "COMPLETE":
            raise RuntimeError(
                f"comparison did not complete: {comparison['state']}/{outcome.get('status')}")
        if not (eligibility.get("A") or {}).get("eligible"):
            raise RuntimeError("the model candidate is not eligible after the comparison")

        print(f"[{prefix}] phase C: explicit selection", flush=True)
        prior = client.get("/api/engagements/bookshop/board").json()["operating_selection"]
        if prior is None or prior["id"] != "sel-0001":
            raise RuntimeError("the prior selection is not sel-0001")
        choice = client.post(f"/api/shifts/{shift_id}/selections", json={
            "comparison_id": comparison["id"],
            "selected_version_id": candidate_a["id"],
            "rationale": ("A completed the required tasks under the shared conditions and routes "
                          "its first action through the frozen model gateway."),
            "expected_prior_selection_id": "sel-0001",
            "client_request_id": f"{prefix}-choice",
        })
        _expect(choice, 201, "append the selection")
        selection = choice.json()
        if (selection["selected_version_id"] != candidate_a["id"]
                or selection["selected_content_hash"] != candidate_a["content_hash"]):
            raise RuntimeError("the selection did not bind the exact candidate A version and hash")
        summary["phase_c"] = {
            "selection_id": selection["id"], "selected_version_id": selection["selected_version_id"],
            "selected_content_hash": selection["selected_content_hash"],
            "prior_selection_id": selection["prior_selection_id"],
            "retained_alternative_version_id": selection["retained_alternative_version_id"],
        }

        print(f"[{prefix}] phase D: close and inherit", flush=True)
        closed = client.post(f"/api/shifts/{shift_id}/close")
        _expect(closed, 200, "close the first shift")
        opened = client.post("/api/engagements/bookshop/shifts")
        _expect(opened, 201, "open the successor shift")
        shift_02 = opened.json()["id"]
        if shift_02 != "bookshop-shift-02":
            raise RuntimeError(f"unexpected successor shift id: {shift_02}")
        summary["phase_d"] = {"closed_shift": shift_id, "opened_shift": shift_02}

        print(f"[{prefix}] phase E: operate the exact selected version", flush=True)
        started = client.post(f"/api/shifts/{shift_02}/runs",
                              json={"client_request_id": f"{prefix}-operation-once"})
        _expect(started, 202, "start the selected operation")
        operation = _wait_run(client, started.json()["id"])
        conn = db.connect(str(db_file))
        try:
            checks = repo.list_check_results(conn, operation["id"])
            events = repo.list_ledger_events(conn, "bookshop")
            inference_rows = _inference_rows(conn, [operation["id"]])
        finally:
            conn.close()
        sale = next((event for event in events if event.event_type is LedgerEventType.SALE_COMPLETED
                     and operation["id"] in event.cause_refs), None)
        phase_e = {
            "run_id": operation["id"], "state": operation["state"],
            "adapter": operation["adapter"], "evidence_mode": operation["evidence_mode"],
            "artifact_version_id": operation["artifact_version_id"],
            "selection_id": operation["selection_id"],
            "checks_total": len(checks),
            "checks_passed": sum(1 for check in checks if check.verdict == "pass"),
            "sale_event_seq": sale.seq if sale else None,
            "sale_event_cause_refs": list(sale.cause_refs) if sale else None,
            "inference_results": inference_rows,
            "successful_inference_results": sum(
                1 for row in inference_rows if row["model"] and not row["failure"]),
        }
        if live:
            phase_e.update(_meter_record(meters["operation"]))
        summary["phase_e"] = phase_e
        if operation["state"] != "FINALIZED":
            raise RuntimeError(f"selected operation did not finalize: {operation['state']}")
        if live and operation["evidence_mode"] != "ISOLATED_LIVE":
            raise RuntimeError("the live operation did not record ISOLATED_LIVE evidence")
        if operation["artifact_version_id"] != selection["selected_version_id"]:
            raise RuntimeError("the operation ran a version other than the exact selection")
        if not checks or any(check.verdict != "pass" for check in checks):
            raise RuntimeError("the operation did not pass every customer task check")
        if sale is None:
            raise RuntimeError("the operation recorded no SALE_COMPLETED event")

        print(f"[{prefix}] phase F: the next shift inherits", flush=True)
        closed2 = client.post(f"/api/shifts/{shift_02}/close")
        _expect(closed2, 200, "close the second shift")
        opened2 = client.post("/api/engagements/bookshop/shifts")
        _expect(opened2, 201, "open the third shift")
        shift_03 = opened2.json()["id"]
        if shift_03 != "bookshop-shift-03":
            raise RuntimeError(f"unexpected third shift id: {shift_03}")
        draft = client.get(f"/api/shifts/{shift_03}/artifact").json()
        conn = db.connect(str(db_file))
        try:
            version = repo.get_version(conn, selection["selected_version_id"])
            events_after = repo.list_ledger_events(conn, "bookshop")
        finally:
            conn.close()
        sale_after = next((event for event in events_after
                           if event.event_type is LedgerEventType.SALE_COMPLETED
                           and operation["id"] in event.cause_refs), None)
        if draft["files"] != version.files:
            raise RuntimeError("the third shift's draft does not match the selected version")
        if sale_after is None or sale_after.seq != phase_e["sale_event_seq"]:
            raise RuntimeError("the inherited ledger no longer carries the operation's sale")
        summary["phase_f"] = {
            "closed_shift": shift_02, "opened_shift": shift_03,
            "draft_matches_selected_version": True, "sale_event_seq": sale_after.seq,
        }

    if not live:
        return "REHEARSAL_COMPLETE"
    if summary["phase_b"]["successful_inference_results"] < 1:
        return "NO-GO: the qualifying comparison recorded no successful inference"
    if summary["phase_e"]["successful_inference_results"] < 1:
        return "NO-GO: the selected operation recorded no successful inference"
    return "CHAIN_COMPLETE"


def _headline(summary: dict) -> dict:
    comparison = summary.get("phase_b") or {}
    operation = summary.get("phase_e") or {}
    return {
        "mode": summary["mode"],
        "verdict": summary.get("verdict"),
        "comparison": {
            "operations": comparison.get("sandbox_operations"),
            "calls": comparison.get("inference_call_attempts"),
            "projected_inference_usd": comparison.get("projected_inference_usd"),
            "reservation_ceiling_usd": (summary.get("ceilings") or {}).get("comparison"),
        },
        "operation": {
            "operations": operation.get("sandbox_operations"),
            "calls": operation.get("inference_call_attempts"),
            "projected_inference_usd": operation.get("projected_inference_usd"),
            "reservation_ceiling_usd": (summary.get("ceilings") or {}).get("operation"),
        },
        "per_call_model_outcomes": [
            {**row, "phase": "comparison"} for row in comparison.get("inference_results") or []
        ] + [
            {**row, "phase": "operation"} for row in operation.get("inference_results") or []
        ],
    }


def _finish(run_dir: Path, summary: dict, exit_code: int) -> int:
    summary["ended_utc"] = _utc_now()
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps(_headline(summary), sort_keys=True, default=str), flush=True)
    return exit_code


def main(args: argparse.Namespace) -> int:
    if args.preflight_only and args.offline_rehearsal:
        raise SystemExit("choose --preflight-only or --offline-rehearsal, not both")
    if args.offline_rehearsal:
        summary = {"mode": "rehearsal", "started_utc": _utc_now()}
        try:
            guards = _check_static_guards()
            verdict = _run_chain(live=False, meters=None, guards=guards, summary=summary)
        except Exception as exc:
            summary["verdict"] = "ERROR"
            summary["error"] = {"type": type(exc).__name__, "message": str(exc)[:2000]}
            return _finish(REHEARSAL_DIR, summary, 1)
        summary["verdict"] = verdict
        return _finish(REHEARSAL_DIR, summary, 0)
    prepared = _prepare_live()
    if args.preflight_only:
        print(json.dumps({
            "preflight": "PASS", "model": MODEL,
            "comparison": _meter_record(prepared["comparison"]),
            "operation": _meter_record(prepared["operation"]),
            "sealed_guards": prepared["guards"],
            "once_marker_absent": True,
        }, sort_keys=True), flush=True)
        return 0
    summary = {"mode": "live", "started_utc": _utc_now()}
    try:
        verdict = _run_chain(live=True, meters=prepared, guards=prepared["guards"],
                             summary=summary)
    except Exception as exc:
        summary["verdict"] = "ERROR"
        summary["error"] = {"type": type(exc).__name__, "message": str(exc)[:2000]}
        return _finish(RUN_DIR, summary, 1)
    summary["verdict"] = verdict
    return _finish(RUN_DIR, summary, 0 if verdict == "CHAIN_COMPLETE" else 2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--offline-rehearsal", action="store_true")
    raise SystemExit(main(parser.parse_args()))
