"""Retained public S44 captures, replayed only as recorded diagnosis.

The checksum binds the package bytes. It is not independent proof of provider
authenticity: only the controller/operator supplies this file, never the learner.
"""

import base64
import hashlib
import json
import os
from pathlib import Path

from shiftwork import config, experiments, orchestrator
from shiftwork.domain import canonical
from shiftwork.domain.models import (ArtifactVersion, CandidateRef, EvidenceMode,
    ExecutionContext, Experiment, ExperimentKind, Run, RunPurpose, RunState)
from shiftwork.executor.base import RawCapture, RawObservation, RunResult
from shiftwork.gateway.redaction import assert_public_safe
from shiftwork.packs import registry
from shiftwork.store import repo


def recording_path() -> Path | None:
    configured = os.environ.get("SHIFTWORK_DIAGNOSTIC_RECORDING")
    path = Path(configured) if configured else config.FIXTURE_DIR / "runs" / "s44_task_plan.json"
    return path if configured or path.is_file() else None


def recording_digest(recording: dict) -> str:
    return canonical.content_hash({key: value for key, value in recording.items() if key != "digest"})


def export_recording(conn, experiment_id: str) -> dict:
    experiment = repo.get_experiment(conn, experiment_id)
    summary = experiments.repetition_summary(conn, experiment)
    view = experiments.experiment_view(conn, experiment_id)
    context = repo.get_execution_context(conn, experiment.context_id)
    if (context.executor_class is not EvidenceMode.ISOLATED_LIVE
            or any(trial["evidence_mode"] != "ISOLATED_LIVE" for trial in view["trials"])):
        raise orchestrator.LifecycleError("conflict", "recording requires retained isolated live evidence")
    version = repo.get_version(conn, experiment.candidates[0].artifact_version_id)
    trials = []
    for trial in view["trials"]:
        observations = repo.list_observations(conn, trial["run_id"])
        trials.append({**trial, "retained_observations": [row.model_dump(mode="json") for row in observations],
                       "log_refs": {str(row.request_ordinal): row.log_ref
                                    for row in repo.list_outputs(conn, trial["run_id"])}})
    payload = {"schema_version": 1, "source_evidence_mode": "ISOLATED_LIVE",
               "source_experiment_id": experiment_id, "source_context_hash": context.content_hash,
               "context": context.model_dump(mode="json"), "version": version.model_dump(mode="json"),
               "public_repetitions": summary["retained_repetitions"], "trials": trials}
    payload["version"]["storage_ref"] = "retained-public-starter"
    assert_public_safe(payload, orchestrator._private_public_needles(conn))
    payload["digest"] = recording_digest(payload)
    return payload


def load_recording(path: Path) -> dict:
    try:
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("recording exceeds byte limit")
        payload = json.loads(path.read_bytes())
        if payload["digest"] != recording_digest(payload):
            raise ValueError("recording digest mismatch")
        context = ExecutionContext.model_validate(payload["context"])
        version = ArtifactVersion.model_validate(payload["version"])
        pack = registry.resolve_pack("bookshop")
        pins = {pin.path: pin.sha256 for pin in pack.reviewed_pins}
        mission_pin = pins["fixtures/mission/bookshop_pivot_v2.json"]
        starter_pin = pins["fixtures/artifacts/bookshop/task_plan_starter_service.py"]
        if (payload["schema_version"] != 1 or payload["source_evidence_mode"] != "ISOLATED_LIVE"
                or context.executor_class is not EvidenceMode.ISOLATED_LIVE
                or experiments.diagnostic_context_hash(context) != context.content_hash
                or payload["source_context_hash"] != context.content_hash
                or context.protected_reservation_id is not None
                or context.mission_hash != mission_pin
                or hashlib.sha256(base64.b64decode(context.mission_bytes_base64)).hexdigest() != mission_pin
                or hashlib.sha256(base64.b64decode(context.public_data_bytes_base64)).hexdigest() != context.public_data_hash
                or set(version.files) != {"service.py"}
                or hashlib.sha256(version.files["service.py"].encode()).hexdigest() != starter_pin
                or canonical.artifact_content_hash(version.files, canonical.contract_params_json(version.contract),
                                                   version.contract_catalog_hash) != version.content_hash):
            raise ValueError("recording source, mission or starter mismatch")
        count = context.resource_limits_json.get("public_repetitions", 1)
        if (type(count) is not int or not 1 <= count <= 10
                or payload["public_repetitions"] != count or len(payload["trials"]) != count
                or len({trial["run_id"] for trial in payload["trials"]}) != count):
            raise ValueError("recording retained denominator mismatch")
        for trial in payload["trials"]:
            if (trial["state"] != "COMPLETE" or trial["evidence_mode"] != "ISOLATED_LIVE"
                    or len(trial["outputs"]) != context.workloads[0].request_count
                    or any(row["transport_error"] is not None for row in trial["outputs"])
                    or not any(row["kind"] == "INFERENCE_RESULT" for row in trial["retained_observations"])):
                raise ValueError("recording lacks a complete live reply and capture")
        return payload
    except (OSError, ValueError, KeyError, TypeError):
        raise orchestrator.LifecycleError("conflict", "invalid diagnostic recording") from None


def reserve_recorded(conn, shift, path: Path, client_request_id: str | None) -> Run:
    """Called inside start_run's transaction. No operation, protected draw or choice."""
    payload = load_recording(path)
    key = client_request_id or f"recording-{shift.id}-{payload['digest']}"
    existing = repo.get_experiment_by_client_request_id(conn, key)
    if existing is not None:
        context = repo.get_execution_context(conn, existing.context_id)
        if (existing.shift_id != shift.id
                or context.resource_limits_json.get("recording_digest") != payload["digest"]):
            raise orchestrator.LifecycleError("conflict", "recording request key belongs to different evidence")
        return experiments.experiment_run(conn, existing.id)
    used = repo.count_experiments_for_shift(conn, shift.id, ExperimentKind.DIAGNOSTIC)
    if used >= orchestrator.DIAGNOSTIC_EXPERIMENTS_PER_SHIFT:
        raise orchestrator.LifecycleError("conflict", "recording diagnostic budget exhausted")
    source_context = ExecutionContext.model_validate(payload["context"])
    limits = {**source_context.resource_limits_json, "public_repetitions": payload["public_repetitions"],
              "recording_digest": payload["digest"], "source_context_hash": payload["source_context_hash"],
              "recorded_trials": [json.dumps(trial, sort_keys=True) for trial in payload["trials"]]}
    context = source_context.model_copy(update={
        "id": f"context-{repo.count_execution_contexts(conn) + 1:04d}",
        "executor_class": EvidenceMode.RECORDED_INSPECTION, "resource_limits_json": limits,
        "created_at": orchestrator._now()})
    context = context.model_copy(update={"content_hash": experiments.diagnostic_context_hash(context)})
    existing_context = repo.get_execution_context_by_hash(conn, context.content_hash)
    if existing_context is None:
        repo.insert_execution_context(conn, context)
    else:
        context = existing_context
    source_version = ArtifactVersion.model_validate(payload["version"])
    version = source_version.model_copy(update={"id": f"ver-{repo.count_versions(conn) + 1:04d}",
        "shift_id": shift.id, "parent_id": None, "restored_from_id": None,
        "created_at": orchestrator._now(), "storage_ref": "retained-public-starter", "created_by": "template"})
    repo.insert_version(conn, version)
    experiment = Experiment(id=f"experiment-{shift.id}-d{used + 1}", shift_id=shift.id,
        kind=ExperimentKind.DIAGNOSTIC, investigation_id=None,
        candidates=(CandidateRef(label="A", artifact_version_id=version.id,
                                 artifact_content_hash=version.content_hash),),
        declared_treatment="RECORDED_INSPECTION: replay retained S44 starter captures for diagnosis only. No fresh model execution or eligibility.",
        context_id=context.id, content_hash=canonical.content_hash({"recording": payload["digest"],
            "context": context.content_hash, "shift": shift.id}), trial_count_per_candidate=1,
        state="RUNNING", client_request_id=key, created_at=orchestrator._now())
    repo.insert_experiment(conn, experiment)
    for _ in payload["trials"]:
        run = Run(id=f"run-{repo.count_runs_all(conn) + 1:04d}", shift_id=shift.id,
            artifact_version_id=version.id, request_batch_ref="retained-s44-public",
            shop_snapshot_ref=f"frozen-context:{context.id}",
            attempt_number=repo.count_runs(conn, shift.id) + 1, state=RunState.QUEUED,
            adapter="recorded", started_at=orchestrator._now(), purpose=RunPurpose.EXPERIMENT,
            evidence_mode=EvidenceMode.RECORDED_INSPECTION, context_id=context.id,
            experiment_id=experiment.id)
        repo.insert_run(conn, run)
    return experiments.experiment_run(conn, experiment.id)


class RecordingAdapter:
    def __init__(self, context, ordinal: int):
        self.trial = json.loads(context.resource_limits_json["recorded_trials"][ordinal])

    async def execute(self, request) -> RunResult:
        captures = tuple(RawCapture(request_ordinal=row["request_ordinal"],
            http_status=row["http_status"], body=base64.b64decode(row["body_base64"]),
            elapsed_ms=row["elapsed_ms"], transport_error=row["transport_error"],
            log_ref=self.trial["log_refs"].get(str(row["request_ordinal"])))
            for row in self.trial["outputs"])
        observations = tuple(RawObservation(kind=row["kind"], public_payload=row["public_payload_json"],
            raw_payload=json.loads(base64.b64decode(row["raw_payload_ref"].split(",", 1)[1])))
            for row in self.trial["retained_observations"])
        return RunResult(captures=captures, observations=observations,
                         executor_ref=None, failure=None, wall_ms=0)
