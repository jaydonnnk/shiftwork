"""Public diagnostic reservation, repetitions and retained evidence."""

import asyncio
import base64
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from shiftwork import config
from shiftwork import orchestrator
# Adapter classes resolve via orchestrator at call time so monkeypatch replacements stay effective.
from shiftwork.assist.gateway import AssistGateway
from shiftwork.comparison_flow import comparison_view
from shiftwork.domain import canonical, customer_answer, task_contract
from shiftwork.domain.errors import BootstrapBlocked, ShiftworkDomainError, TaskEnvelopeInvalid
from shiftwork.domain.models import (
    CandidateRef,
    EvidenceMode,
    ExecutionContext,
    ExecutionObservation,
    ExecutorFailure,
    Experiment,
    ExperimentKind,
    ObservationKind,
    Run,
    RunAssessment,
    RunPurpose,
    RunState,
)
from shiftwork.evaluator import evaluator
from shiftwork.executor import base as executor
from shiftwork.gateway.redaction import assert_public_safe
from shiftwork.orchestrator import (
    DIAGNOSTIC_DEADLINE_S,
    DIAGNOSTIC_EVALUATOR_VERSION,
    DIAGNOSTIC_EXPERIMENTS_PER_SHIFT,
    DIAGNOSTIC_HARNESS_REF,
    DIAGNOSTIC_IMAGE_REF,
    DIAGNOSTIC_TREATMENT,
    LifecycleError,
    _encode,
    _now,
    _private_public_needles,
    _require_open_shift,
    freeze_diagnostic_context,
    investigation_view,
    reserve_bootstrap_diagnostic,
)
from shiftwork.store import db, repo
from shiftwork.public_evidence import public_observation


def create_diagnostic_experiment(
    conn: sqlite3.Connection,
    shift_id: str,
    *,
    candidate_version_id: str,
    investigation_id: str | None,
    client_request_id: str,
    adapter: str = "local_process",
    public_repetitions: int = 1,
) -> Experiment:
    """Reserve one public diagnostic and queue its frozen public repetitions.

    The controller chooses the workload, the executor and the treatment; the caller
    names only a candidate version and the investigation it belongs to. The
    trusted-local path stays pinned; the isolated path can execute the learner's
    frozen code. Neither path reserves a protected case or qualifies a version.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        shift = _require_open_shift(conn, shift_id)
        if type(public_repetitions) is not int or not 1 <= public_repetitions <= 10:
            raise LifecycleError("conflict", "public repetitions must be from 1 to 10")
        isolated = adapter == orchestrator.TokenFactoryAdapter.name
        if adapter not in (orchestrator.LocalProcessAdapter.name, orchestrator.TokenFactoryAdapter.name):
            raise LifecycleError("conflict", "no safe diagnostic executor is configured")
        if isolated and (not os.environ.get("NEBIUS_API_KEY") or not os.environ.get("NEBIUS_PROJECT_ID")):
            raise BootstrapBlocked("the verified isolated executor and its controller credentials are unavailable")
        if investigation_id is None:
            investigation = None
        else:
            investigation = repo.get_investigation(conn, investigation_id)
            if investigation is None:
                raise LifecycleError("not_found", f"unknown investigation: {investigation_id}")
        if investigation is not None and investigation.shift_id != shift.id:
            raise LifecycleError(
                "conflict", "a diagnostic must cite an investigation owned by this shift"
            )
        version = repo.get_version(conn, candidate_version_id)
        if version is None:
            raise LifecycleError("not_found", f"unknown artifact version: {candidate_version_id}")
        if version.shift_id != shift.id:
            raise LifecycleError("conflict", "a diagnostic candidate must belong to this shift")
        replay = repo.get_experiment_by_client_request_id(conn, client_request_id)
        if replay is not None:
            candidate = replay.candidates[0] if replay.candidates else None
            if (
                replay.shift_id == shift.id
                and replay.kind is ExperimentKind.DIAGNOSTIC
                and replay.investigation_id == (investigation.id if investigation else None)
                and candidate is not None
                and candidate.artifact_version_id == version.id
                and repetition_count(conn, replay) == public_repetitions
            ):
                conn.rollback()
                return replay
            raise LifecycleError(
                "conflict", "client_request_id was already used for a different experiment"
            )
        if investigation_id is None:
            reserve_bootstrap_diagnostic(conn, shift_id, adapter=adapter)
        starter_key = config.offline_fixture_keys(shift.engagement_slug)[0]
        starter_pin = config.TRUSTED_LOCAL_FIXTURES.get(starter_key)
        if not isolated and (starter_pin is None or version.content_hash != starter_pin[0]):
            raise LifecycleError(
                "conflict",
                "only the pinned reviewed starter is executable as a public diagnostic candidate",
            )
        used = repo.count_experiments_for_shift(conn, shift_id, ExperimentKind.DIAGNOSTIC)
        if used >= DIAGNOSTIC_EXPERIMENTS_PER_SHIFT:
            raise LifecycleError(
                "conflict",
                f"diagnostic budget exhausted for this shift ({used} of "
                f"{DIAGNOSTIC_EXPERIMENTS_PER_SHIFT} used)",
            )
        context = freeze_diagnostic_context(conn, shift, isolated=isolated,
                                            public_repetitions=public_repetitions)
        ordinal = used + 1
        treatment = (
            f"Run this frozen learner-owned service {public_repetitions} time(s) in the isolated Sandbox "
            "against the reviewed initial public request and state; no protected "
            "case, eligibility or business consequence is reserved."
            if isolated else DIAGNOSTIC_TREATMENT
        )
        candidates = (
            CandidateRef(
                label="A",
                artifact_version_id=version.id,
                artifact_content_hash=version.content_hash,
            ),
        )
        experiment = Experiment(
            id=f"experiment-{shift.id}-d{ordinal}",
            shift_id=shift.id,
            kind=ExperimentKind.DIAGNOSTIC,
            investigation_id=investigation.id if investigation else None,
            candidates=candidates,
            declared_treatment=treatment,
            context_id=context.id,
            content_hash=canonical.content_hash(
                {
                    "shift_id": shift.id,
                    "kind": ExperimentKind.DIAGNOSTIC.value,
                    "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
                    "context_hash": context.content_hash,
                    "trial_count_per_candidate": 1,
                    "declared_treatment": treatment,
                }
            ),
            trial_count_per_candidate=1,
            state="PLANNED",
            client_request_id=client_request_id,
            created_at=_now(),
        )
        repo.insert_experiment(conn, experiment)
        for _ in range(public_repetitions):
            run = Run(
                id=f"run-{repo.count_runs_all(conn) + 1:04d}",
                shift_id=shift.id,
                artifact_version_id=version.id,
                request_batch_ref=Path(orchestrator.pack_registry.resolve_pack(
                    shift.engagement_slug).incident_request_path).name,
                shop_snapshot_ref=f"frozen-context:{context.id}",
                attempt_number=repo.count_runs(conn, shift.id) + 1,
                state=RunState.QUEUED,
                adapter=adapter,
                started_at=_now(),
                purpose=RunPurpose.EXPERIMENT,
                evidence_mode=EvidenceMode.ISOLATED_LIVE if isolated else EvidenceMode.TRUSTED_LOCAL,
                context_id=context.id,
                experiment_id=experiment.id,
            )
            repo.insert_run(conn, run)
        repo.update_experiment_state(conn, experiment.id, "RUNNING")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return experiment


def execute_experiment(conn: sqlite3.Connection, run_id: str, live_budget=None) -> Run:
    """Execute one reserved diagnostic and assess it against the frozen rubric.

    The frozen context is the only source of the mission, the public state and the
    workload hash, so the bytes that were reserved are the bytes that execute and
    the bytes the assessment reads. Assessment is the pure evaluator over the
    validated envelope: it opens no sealed case and writes no ledger event,
    incident, selection or business state.
    """
    run = repo.get_run(conn, run_id)
    if run is None:
        raise LifecycleError("not_found", f"unknown run: {run_id}")
    if run.purpose is not RunPurpose.EXPERIMENT:
        raise LifecycleError("conflict", "only an experiment run is executed by this path")
    if run.state is not RunState.QUEUED:
        return run
    context = repo.get_execution_context(conn, run.context_id) if run.context_id else None
    version = repo.get_version(conn, run.artifact_version_id)
    if context is None or version is None or not context.workloads:
        repo.update_run(conn, run_id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED, _now())
        _update_diagnostic_state(conn, run.experiment_id)
        conn.commit()
        return repo.get_run(conn, run_id)

    experiment = repo.get_experiment(conn, run.experiment_id)
    if (run.adapter == orchestrator.TokenFactoryAdapter.name
            and repetition_count(conn, experiment) > 1 and live_budget is None):
        raise LifecycleError("conflict", "live repetitions require a bounded diagnostic budget")

    workload = context.workloads[0]
    try:
        snapshot_bytes = base64.b64decode(context.public_data_bytes_base64)
        mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))
        snapshot = task_contract.load_public_state_bytes(snapshot_bytes)
        request = executor.RunRequest(
            artifact_snapshot=executor.ArtifactSnapshotRef(
                files={path: text.encode("utf-8") for path, text in version.files.items()},
                manifest_hash=version.content_hash,
            ),
            request_batch=executor.BatchRef(
                path_ref=run.request_batch_ref,
                content_hash=workload.request_batch_hash,
            ),
            shop_snapshot_ref="",
            harness_ref="sandbox-driver-v1" if run.adapter == orchestrator.TokenFactoryAdapter.name else DIAGNOSTIC_HARNESS_REF,
            image_ref=context.image_ref if run.adapter == orchestrator.TokenFactoryAdapter.name else DIAGNOSTIC_IMAGE_REF,
            deadline_s=45 if run.adapter == orchestrator.TokenFactoryAdapter.name else DIAGNOSTIC_DEADLINE_S,
            inference_grant=None,
            request_batch_bytes=base64.b64decode(workload.request_batch_bytes_base64),
        )
    except (ValueError, ShiftworkDomainError):
        repo.update_run(conn, run_id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED, _now())
        _update_diagnostic_state(conn, run.experiment_id)
        conn.commit()
        return repo.get_run(conn, run_id)

    if not repo.claim_run_execution(conn, run_id):
        conn.rollback()
        return repo.get_run(conn, run_id)
    repo.set_run_snapshot_bytes(conn, run_id, snapshot_bytes)
    conn.commit()
    try:
        result = None
        with tempfile.TemporaryDirectory(prefix="shiftwork-diagnostic-") as directory:
            snapshot_path = Path(directory) / "public_state.json"
            snapshot_path.write_bytes(snapshot_bytes)
            request = request.model_copy(update={"shop_snapshot_ref": str(snapshot_path)})
            request = orchestrator.bind_deployment_request(request, run, context, version, mission, snapshot_bytes)
            if run.adapter == orchestrator.TokenFactoryAdapter.name:
                adapter = orchestrator.service_adapter(run, mission, context, live_budget=live_budget)
            elif run.adapter == orchestrator.LocalProcessAdapter.name:
                adapter = orchestrator.LocalProcessAdapter()
            elif run.adapter == "recorded" and run.evidence_mode is EvidenceMode.RECORDED_INSPECTION:
                from shiftwork.diagnostic_recording import RecordingAdapter
                ordinal = [row.id for row in diagnostic_runs(conn, experiment)].index(run.id)
                adapter = RecordingAdapter(context, ordinal)
            else:
                raise LifecycleError("conflict", "reserved diagnostic has no safe executor")
            result = asyncio.run(adapter.execute(request))

        for ordinal, observation in enumerate(result.observations, start=1):
            raw = json.dumps(observation.raw_payload, sort_keys=True, default=str).encode("utf-8")
            repo.insert_observation(conn, ExecutionObservation(
                id=f"{run.id}-obs-{ordinal}", run_id=run.id,
                request_ordinal=observation.public_payload.get("request_ordinal", 1),
                ordinal=ordinal, kind=ObservationKind(observation.kind),
                public_payload_json=observation.public_payload,
                raw_payload_ref="data:application/json;base64," + base64.b64encode(raw).decode("ascii"),
                measured_at=_now(),
            ))

        outputs = []
        if result.captures:
            batch = {entry.ordinal: entry for entry in executor.load_batch(request.request_batch, request.request_batch_bytes)}
            for output in executor.normalize_captures(result.captures, request.deadline_s):
                output = output.model_copy(update={
                    "id": f"{run.id}-out-{output.request_ordinal}",
                    "run_id": run.id,
                    "request_text": batch[output.request_ordinal].text,
                })
                repo.insert_output(conn, output)
                outputs.append(output)

        # Preserve the raw capture and trusted observations before assessment.
        conn.commit()

        captured = {output.request_ordinal: output for output in outputs}
        completed = 0
        mandatory_pass = True
        for index, spec in enumerate(mission.request_specs, start=1):
            output = captured.get(index)
            response = None
            if output is not None and output.transport_error is None:
                try:
                    response = task_contract.validate_response_envelope(spec, output.body)
                except TaskEnvelopeInvalid:
                    # An envelope the contract refuses is missing execution evidence,
                    # never a refusal the service did not make (S3.3).
                    response = None
            request_assessments = evaluator.assess_request(
                spec=spec,
                request_ordinal=index,
                mission=mission,
                snapshot=snapshot,
                response=response,
                **orchestrator.deployment_assessment_inputs(conn, run, spec, index, snapshot_bytes,
                    base64.b64decode(workload.request_batch_bytes_base64)),
            )
            for assessment in request_assessments:
                repo.insert_task_assessment(
                    conn,
                    assessment_id=f"{run.id}-a{index}-{assessment.task_id}",
                    run_id=run.id,
                    assessment=assessment,
                    assessed_at=_now(),
                )
            if any(assessment.mandatory_pass is False for assessment in request_assessments):
                mandatory_pass = False
            if evaluator.request_usefully_completed(spec, request_assessments):
                completed += 1
        repo.insert_run_assessment(
            conn,
            RunAssessment(
                run_id=run.id,
                context_hash=context.content_hash,
                complete_request_count=completed,
                expected_request_count=len(mission.request_specs),
                mandatory_pass=mandatory_pass,
                rule_version=DIAGNOSTIC_EVALUATOR_VERSION,
                assessed_at=_now(),
            ),
        )
        if result.failure is not None:
            repo.update_run(conn, run_id, RunState.FAILED, result.failure, _now())
            _update_diagnostic_state(conn, run.experiment_id)
        else:
            repo.update_run(conn, run_id, RunState.FINALIZED, None, _now())
            _update_diagnostic_state(conn, run.experiment_id)
        conn.commit()
    except Exception:
        conn.rollback()
        repo.update_run(conn, run_id, RunState.FAILED, ExecutorFailure.INTERNAL, _now())
        _update_diagnostic_state(conn, run.experiment_id)
        conn.commit()
        raise
    return repo.get_run(conn, run_id)


def execute_experiment_task(db_path: str, run_id: str, live_budget=None) -> None:
    conn = db.connect(db_path)
    try:
        execute_diagnostic_batch(conn, run_id, live_budget)
    finally:
        conn.close()


def execute_diagnostic_batch(conn, run_id: str, live_budget=None) -> None:
    first = repo.get_run(conn, run_id)
    experiment = repo.get_experiment(conn, first.experiment_id)
    context = repo.get_execution_context(conn, experiment.context_id)
    runs = diagnostic_runs(conn, experiment)
    if first.adapter == orchestrator.TokenFactoryAdapter.name:
        if repetition_count(conn, experiment) > 1 and live_budget is None:
            raise LifecycleError("conflict", "live repetitions require a bounded diagnostic budget")
        if live_budget is not None:
            live_budget.preflight(model=context.service_model,
                repetitions=repetition_count(conn, experiment),
                requests=context.workloads[0].request_count)
    for run in runs:
        execute_experiment(conn, run.id, live_budget=live_budget)


def experiment_run(conn: sqlite3.Connection, experiment_id: str) -> Run | None:
    """The first run of a reserved diagnostic, or None before reservation."""
    experiment = repo.get_experiment(conn, experiment_id)
    if experiment is None:
        return None
    return next(
        (
            run
            for run in repo.list_runs_for_shift(conn, experiment.shift_id)
            if run.experiment_id == experiment.id
        ),
        None,
    )


def _diagnostic_customer_text(
    conn: sqlite3.Connection, context: ExecutionContext, run_id: str
) -> str | None:
    """The customer text for the run's first validated envelope, else None.

    Rendered from the validated envelope plus the frozen mission and public state
    alone, so no prose the service tried to carry can reach a customer surface
    (Gate 3 S3.3). A GTM diagnostic also consults the run's stored assessments, as
    the operational projection does, so a rejected or missing workflow task never
    reads as the customer answer (S24 review, finding F2).
    """
    outputs = repo.list_outputs(conn, run_id)
    if not outputs:
        return None
    output = outputs[0]
    if output.transport_error is not None:
        return None
    try:
        mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))
        snapshot = task_contract.load_public_state_bytes(
            base64.b64decode(context.public_data_bytes_base64)
        )
        if not 1 <= output.request_ordinal <= len(mission.request_specs):
            return None
        spec = mission.request_specs[output.request_ordinal - 1]
        response = task_contract.validate_response_envelope(spec, output.body)
    except (ShiftworkDomainError, ValueError):
        return None
    if mission.engagement_slug == "gtm":
        assessed = customer_answer.render_assessed_task_customer_text(
            spec=spec, mission=mission, snapshot=snapshot, response=response,
            request_ordinal=output.request_ordinal,
            assessments=repo.list_task_assessment_models(conn, run_id))
        return assessed[0] if assessed is not None else None
    return customer_answer.render_task_customer_text(
        spec=spec, mission=mission, snapshot=snapshot, response=response
    )


def experiment_view(conn: sqlite3.Connection, experiment_id: str) -> dict[str, Any]:
    """The public experiment projection, dispatched by experiment kind."""
    experiment = repo.get_experiment(conn, experiment_id)
    if experiment is None:
        raise LifecycleError("not_found", f"unknown experiment: {experiment_id}")
    if experiment.kind in (
        ExperimentKind.QUALIFYING_COMPARISON, ExperimentKind.LATER_CONDITION_COMPARISON
    ):
        return comparison_view(conn, experiment)
    return _diagnostic_experiment_view(conn, experiment)


def diagnostic_runs(conn: sqlite3.Connection, experiment: Experiment) -> list[Run]:
    return [run for run in repo.list_runs_for_shift(conn, experiment.shift_id)
            if run.experiment_id == experiment.id]


def diagnostic_context_hash(context: ExecutionContext) -> str:
    names = ("engagement_slug", "workloads", "mission_hash", "public_data_hash",
             "starting_business_state_hash", "requirement_set_id", "requirement_set_hash",
             "visible_check_set_hash", "condition", "evaluator_version", "reducer_version",
             "executor_class", "harness_hash", "image_ref", "service_model",
             "service_model_settings_json", "resource_limits_json")
    frozen = context.model_dump(mode="json")
    return canonical.content_hash({name: frozen[name] for name in names})


def repetition_count(conn: sqlite3.Connection, experiment: Experiment) -> int:
    context = repo.get_execution_context(conn, experiment.context_id)
    count = context.resource_limits_json.get("public_repetitions", 1)
    if type(count) is not int or not 1 <= count <= 10:
        raise LifecycleError("conflict", "invalid retained repetition declaration")
    if "public_repetitions" in context.resource_limits_json:
        if diagnostic_context_hash(context) != context.content_hash:
            raise LifecycleError("conflict", "retained repetition declaration changed after reservation")
    return count


def _update_diagnostic_state(conn: sqlite3.Connection, experiment_id: str) -> None:
    experiment = repo.get_experiment(conn, experiment_id)
    runs = diagnostic_runs(conn, experiment)
    state = ("RUNNING" if any(run.state in (RunState.QUEUED, RunState.RUNNING) for run in runs)
             else "FAILED" if any(run.state is RunState.FAILED for run in runs)
             else "FINALIZED")
    repo.update_experiment_state(conn, experiment_id, state)


def _has_retained_reply(observation: ExecutionObservation) -> bool:
    if not observation.raw_payload_ref.startswith("data:application/json;base64,"):
        return False
    try:
        raw = json.loads(base64.b64decode(observation.raw_payload_ref.split(",", 1)[1], validate=True))
        message = raw["provider_response"]["choices"][0]["message"]
        return isinstance(message, dict) and "content" in message
    except (ValueError, KeyError, IndexError, TypeError):
        return False


def repetition_summary(conn: sqlite3.Connection, experiment: Experiment) -> dict[str, Any]:
    """A complete retained denominator, or a refusal. Never extrapolate a rate."""
    count = repetition_count(conn, experiment)
    context = repo.get_execution_context(conn, experiment.context_id)
    mission = task_contract.load_mission_bytes(base64.b64decode(context.mission_bytes_base64))
    runs = diagnostic_runs(conn, experiment)
    expected = {(ordinal, task.id) for ordinal, spec in enumerate(mission.request_specs, 1)
                for task in spec.tasks}
    rows = []
    if len(runs) != count:
        raise LifecycleError("conflict", "summary refused: retained repetitions differ from declaration")
    for run in runs:
        outputs = repo.list_outputs(conn, run.id)
        assessments = repo.list_task_assessment_models(conn, run.id)
        if mission.task_vocabulary:
            replies = [row for row in repo.list_observations(conn, run.id)
                       if row.kind is ObservationKind.INFERENCE_RESULT]
            if len(replies) != len(mission.request_specs) or any(
                    not _has_retained_reply(row) for row in replies):
                raise LifecycleError("conflict", "summary refused: missing retained model reply")
        if (run.state is not RunState.FINALIZED or run.context_id != experiment.context_id
                or run.artifact_version_id != experiment.candidates[0].artifact_version_id
                or {output.request_ordinal for output in outputs} != set(range(1, len(mission.request_specs) + 1))
                or any(output.transport_error is not None for output in outputs)
                or {(row.request_ordinal, row.task_id) for row in assessments} != expected):
            raise LifecycleError("conflict", "summary refused: incomplete retained repetition evidence")
        rows.append((run, assessments))
    tasks = []
    for ordinal, spec in enumerate(mission.request_specs, 1):
        for task in spec.tasks:
            if not task.required:
                continue
            matches = [(run, next(row for row in assessments
                                  if row.request_ordinal == ordinal and row.task_id == task.id))
                       for run, assessments in rows]
            misses = [run.id for run, row in matches
                      if any(code.value == "REQUIRED_TASK_MISSING" for code in row.reason_codes)]
            tasks.append({"request_id": spec.id, "task_id": task.id, "required": task.required,
                          "misses": len(misses), "total": count, "miss_run_ids": misses,
                          "mandatory_failures": sum(not row.mandatory_pass for _, row in matches)})
    return {"retained_repetitions": count, "tasks": tasks,
            "run_ids": [run.id for run in runs],
            "limits": "One model, one request set and a small sample. Synthetic scenario; no general model claim.",
            "stop_rule_triggered": not any(task["misses"] for task in tasks if task["required"])}


def _diagnostic_experiment_view(conn: sqlite3.Connection, experiment: Experiment) -> dict[str, Any]:
    runs = diagnostic_runs(conn, experiment)
    payload = _diagnostic_run_view(conn, experiment, runs[0] if runs else None)
    trials = []
    for ordinal, run in enumerate(runs, 1):
        trial = _diagnostic_run_view(conn, experiment, run)["trials"][0]
        trial["execution_ordinal"] = ordinal
        trials.append(trial)
    payload["trials"] = trials
    payload["public_repetitions"] = repetition_count(conn, experiment)
    payload["repetition_summary"] = None
    payload["summary_refusal"] = None
    if payload["public_repetitions"] > 1:
        try:
            payload["repetition_summary"] = repetition_summary(conn, experiment)
        except LifecycleError as exc:
            payload["summary_refusal"] = exc.message
    assert_public_safe(payload, _private_public_needles(conn))
    return payload


def _diagnostic_run_view(conn: sqlite3.Connection, experiment: Experiment, run: Run | None) -> dict[str, Any]:
    """The public diagnostic projection.

    It carries the frozen workload identity, the candidate, the trial's public
    assessments and the exact output the learner's own service produced. Raw
    observation payload refs, sealed identities, host paths and the protected
    reservation never appear, and eligibility stays false: a public diagnostic
    cannot qualify a version (Gate 3 S3.7, test 21).
    """
    context = repo.get_execution_context(conn, experiment.context_id)
    if context is None:
        raise LifecycleError("not_found", f"unknown context: {experiment.context_id}")
    workload = context.workloads[0]
    assessments: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    customer_text = None
    missing_evidence: list[str] = []
    if run is not None:
        assessments = [
            {
                "request_id": assessment.request_id,
                "request_ordinal": assessment.request_ordinal,
                "task_id": assessment.task_id,
                "outcome": assessment.outcome.value,
                "mandatory_pass": assessment.mandatory_pass,
                "reason_codes": [code.value for code in assessment.reason_codes],
            }
            for assessment in repo.list_task_assessment_models(conn, run.id)
        ]
        outputs = [
            {
                "request_ordinal": output.request_ordinal,
                "request_text": output.request_text,
                "http_status": output.http_status,
                "body_base64": _encode(output.body),
                "elapsed_ms": output.elapsed_ms,
                "transport_error": output.transport_error.value if output.transport_error else None,
            }
            for output in repo.list_outputs(conn, run.id)
        ]
        observations = [
            public_observation(observation, public_count=workload.request_count,
                               needles=orchestrator._private_public_needles(conn))
            for observation in repo.list_observations(conn, run.id)
            if observation.request_ordinal <= workload.request_count
        ]
        customer_text = _diagnostic_customer_text(conn, context, run.id)
        if run.failure_kind is not None:
            missing_evidence.append(f"execution failure: {run.failure_kind.value}")
        if not outputs:
            missing_evidence.append("no capture was produced for the frozen request")
    else:
        missing_evidence.append("the reserved diagnostic run has not been executed")
    trial_state = {
        RunState.QUEUED: "RESERVED",
        RunState.RUNNING: "RUNNING",
        RunState.CAPTURED: "RUNNING",
        RunState.FINALIZED: "COMPLETE",
        RunState.FAILED: "FAILED",
    }[run.state] if run is not None else "RESERVED"
    payload = {
        "id": experiment.id,
        "shift_id": experiment.shift_id,
        "kind": experiment.kind.value,
        "investigation_id": experiment.investigation_id,
        "declared_treatment": experiment.declared_treatment,
        "context_hash": context.content_hash,
        "context_evidence_class": context.executor_class.value,
        "workloads": [
            {
                "id": workload.id,
                "ordinal": workload.ordinal,
                "request_batch_hash": workload.request_batch_hash,
                "request_count": workload.request_count,
            }
        ],
        "candidates": [
            {
                "label": candidate.label,
                "artifact_version_id": candidate.artifact_version_id,
                "artifact_content_hash": candidate.artifact_content_hash,
            }
            for candidate in experiment.candidates
        ],
        "trials": [
            {
                "pair_ordinal": 1,
                "candidate_label": experiment.candidates[0].label,
                "artifact_version_id": run.artifact_version_id if run is not None else None,
                "artifact_content_hash": experiment.candidates[0].artifact_content_hash,
                "workload_id": workload.id,
                "request_batch_hash": workload.request_batch_hash,
                "request_count": workload.request_count,
                "run_id": run.id if run is not None else None,
                "state": trial_state,
                "evidence_mode": run.evidence_mode.value if run and run.evidence_mode else None,
                "task_assessments": assessments,
                "observations": observations,
                "outputs": outputs,
                "customer_text": customer_text,
                "missing_evidence": missing_evidence,
                "metrics": None,
            }
        ],
        "eligible": False,
        "eligibility_reason": (
            "A public diagnostic reserves no protected case and compares no "
            "candidates, so it can never qualify a version."
        ),
        "state": experiment.state,
    }
    try:
        assert_public_safe(payload, _private_public_needles(conn))
    except ValueError as exc:
        raise LifecycleError("conflict", "public diagnostic evidence contains private material") from exc
    return payload


def investigate_station(
    conn: sqlite3.Connection, shift_id: str, *, adapter: str = "local_process",
    assist_gateway: AssistGateway | None = None,
) -> dict[str, Any]:
    """The Investigate station: the learner's entries, the denials and the latest
    public diagnostic, composed from the two narrower projections.

    Deterministic orientation is available before any investigation exists (Gate 3
    S1), and the station shows attributable assist events when a gateway is configured.
    """
    view = investigation_view(conn, shift_id, adapter=adapter, assist_gateway=assist_gateway)
    experiments = repo.list_experiments_for_shift(conn, shift_id)
    view["latest_experiment"] = (
        experiment_view(conn, experiments[-1].id) if experiments else None
    )
    # The diagnostic panel reads this field only. A comparison carries candidate
    # eligibility, which a diagnostic can never assert, so it is never projected
    # here even when it is the shift's latest experiment.
    diagnostics = [item for item in experiments if item.kind is ExperimentKind.DIAGNOSTIC]
    view["latest_diagnostic"] = (
        experiment_view(conn, diagnostics[-1].id) if diagnostics else None
    )
    try:
        assert_public_safe(view, _private_public_needles(conn))
    except ValueError as exc:
        raise LifecycleError("conflict", "public investigation evidence contains private material") from exc
    return view
