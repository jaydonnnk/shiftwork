"""Pure reading of one frozen six-slot comparison.

The caller supplies stored evidence. This module never loads a case, database,
file, model or current fixture. Protected task results stay in TrialReading and
only aggregate counts and public rule IDs leave the controller.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from shiftwork.domain import task_contract
from shiftwork.domain.models import (
    EvidenceMode, ExecutionContext, ExecutionObservation, Experiment,
    FrozenWorkload, ObservationKind, Run, RunAssessment, RunOutput, RunPurpose,
    RunState, TrialSlot,
)
from shiftwork.domain.task_contract import TaskAssessment, TaskOutcome
from shiftwork.evaluator.evaluator import SealedCase, request_usefully_completed

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class CandidateMetrics(BaseModel):
    model_config = _FROZEN

    candidate_label: str
    candidate_version_id: str
    public_denominator_requests: int
    useful_completions: int
    incorrect_outputs: int
    justified_refusals: int
    justified_referrals: int
    justified_clarifications: int
    unjustified_refusals: int
    unjustified_referrals: int
    unjustified_clarifications: int
    missing_outputs: int
    protected_denominator: int
    protected_passed: int
    protected_failed: int
    protected_missing: int
    service_calls: int
    input_tokens: int | None
    output_tokens: int | None
    service_latency_ms: int | None
    provisioning_latency_ms: int | None
    cost_minor_units: int | None


class CandidateEligibility(BaseModel):
    model_config = _FROZEN

    candidate_label: str
    candidate_version_id: str
    eligible: bool
    blocking_reason_codes: tuple[str, ...]


class ComparisonOutcome(BaseModel):
    model_config = _FROZEN

    experiment_id: str
    status: Literal["INCOMPLETE", "NOT_COMPARABLE", "COMPLETE"]
    shared_public_denominator_requests: int
    candidate_metrics: tuple[CandidateMetrics, CandidateMetrics]
    eligibility: tuple[CandidateEligibility, CandidateEligibility]
    drift_fields: tuple[str, ...]
    noncompletion_incidence_non_additive: bool = True


@dataclass(frozen=True)
class TrialReading:
    slot: TrialSlot
    run: Run | None
    assessment: RunAssessment | None
    public_specs: tuple[task_contract.CustomerRequestSpec, ...]
    task_assessments: tuple[TaskAssessment, ...]
    outputs: tuple[RunOutput, ...]
    observations: tuple[ExecutionObservation, ...]
    protected_pass: bool | None
    protected_rule_ids: tuple[str, ...]


_ASPECT_OUTCOMES = {
    "supported_negative_collection_is_a_completed_answer": ("collection", TaskOutcome.USEFUL_COMPLETION),
    "conflicting_necessary_collection_records_require_referral": ("collection", TaskOutcome.JUSTIFIED_REFERRAL),
    "collection_answer_creates_no_commitment": ("collection", TaskOutcome.USEFUL_COMPLETION),
}


def protected_acceptance(case: SealedCase, assessments: tuple[TaskAssessment, ...]) -> bool:
    """Check the reserved aspect against controller-assessed task outcomes."""
    if case.stimulus is None:
        return False
    spec = case.stimulus.task_spec
    by_id = {entry.task_id: entry for entry in assessments}
    if len(by_id) != len(spec.tasks) or any(
        by_id.get(task.id) is None or by_id[task.id].request_id != spec.id
        or by_id[task.id].request_ordinal != case.stimulus.request.ordinal
        or not by_id[task.id].mandatory_pass for task in spec.tasks
    ):
        return False
    aspect = case.expected.get("aspect")
    if aspect == "every_required_task_returns_a_result":
        return all(by_id[task.id].outcome is not TaskOutcome.MISSING_OUTPUT
                   for task in spec.tasks if task.required)
    if aspect == "fixed_task_claims_name_the_requested_entity_and_edition":
        return bool(by_id.get("collection") and
                    by_id["collection"].outcome is TaskOutcome.USEFUL_COMPLETION)
    if aspect == "completed_alternative_meets_strict_budget":
        # This authored case has no valid under-budget alternative. A justified
        # refusal is correct; a completed at-boundary item fails in assess_request.
        return bool(by_id.get("alternative") and by_id["alternative"].outcome in (
            TaskOutcome.USEFUL_COMPLETION, TaskOutcome.JUSTIFIED_REFUSAL,
        ))
    target = _ASPECT_OUTCOMES.get(aspect) if type(aspect) is str else None
    return bool(target and by_id.get(target[0])
                and by_id[target[0]].outcome is target[1])


_OUTCOME_FIELDS = {
    TaskOutcome.INCORRECT_OUTPUT: "incorrect_outputs",
    TaskOutcome.JUSTIFIED_REFUSAL: "justified_refusals",
    TaskOutcome.JUSTIFIED_REFERRAL: "justified_referrals",
    TaskOutcome.JUSTIFIED_CLARIFICATION: "justified_clarifications",
    TaskOutcome.UNJUSTIFIED_REFUSAL: "unjustified_refusals",
    TaskOutcome.UNJUSTIFIED_REFERRAL: "unjustified_referrals",
    TaskOutcome.UNJUSTIFIED_CLARIFICATION: "unjustified_clarifications",
    TaskOutcome.MISSING_OUTPUT: "missing_outputs",
}

_BUDGET_METRICS = frozenset({
    "service_calls", "input_tokens", "output_tokens", "service_latency_ms",
    "provisioning_latency_ms", "cost_minor_units",
})


def _known_sum(values: list[object], expected: int) -> int | None:
    if len(values) != expected or any(type(value) is not int or value < 0 for value in values):
        return None
    return sum(values)


def _metrics(candidate_label: str, candidate_version_id: str,
             readings: tuple[TrialReading, ...],
             workloads: tuple[FrozenWorkload, ...]) -> CandidateMetrics:
    counts = {name: 0 for name in _OUTCOME_FIELDS.values()}
    useful = 0
    protected_passed = protected_failed = protected_missing = 0
    calls = 0
    token_in: list[object] = []
    token_out: list[object] = []
    latencies: list[object] = []
    by_pair = {item.slot.pair_ordinal: item for item in readings}
    for workload in workloads:
        reading = by_pair.get(workload.ordinal)
        if reading is None:
            counts["missing_outputs"] += workload.request_count
            protected_missing += 1
            continue
        slot = reading.slot
        by_ordinal: dict[int, list[TaskAssessment]] = {}
        for assessment in reading.task_assessments:
            if assessment.request_ordinal <= slot.request_count:
                by_ordinal.setdefault(assessment.request_ordinal, []).append(assessment)
        captured = {output.request_ordinal for output in reading.outputs
                    if output.transport_error is None and bool(output.body)}
        for ordinal in range(1, slot.request_count + 1):
            assessments = by_ordinal.get(ordinal, [])
            required_ids = ({task.id for task in reading.public_specs[ordinal - 1].tasks if task.required}
                            if ordinal <= len(reading.public_specs) else set())
            outcomes = {item.outcome for item in assessments
                        if item.outcome is not TaskOutcome.MISSING_OUTPUT or item.task_id in required_ids}
            if ordinal not in captured or not assessments:
                outcomes.add(TaskOutcome.MISSING_OUTPUT)
            if ordinal <= len(reading.public_specs) and ordinal in captured and request_usefully_completed(
                reading.public_specs[ordinal - 1], assessments
            ):
                useful += 1
            for outcome, name in _OUTCOME_FIELDS.items():
                if outcome in outcomes:
                    counts[name] += 1
        if reading.protected_pass is True:
            protected_passed += 1
        elif reading.protected_pass is False:
            protected_failed += 1
        else:
            protected_missing += 1
        # Protected work is a separate denominator and cannot enter public
        # efficiency or cost counters, even when its model usage is recorded.
        public_observations = tuple(item for item in reading.observations
                                    if 1 <= item.request_ordinal <= slot.request_count)
        calls += sum(item.kind is ObservationKind.INFERENCE_REQUEST for item in public_observations)
        for item in public_observations:
            if item.kind is ObservationKind.INFERENCE_RESULT:
                token_in.append(item.public_payload_json.get("input_tokens"))
                token_out.append(item.public_payload_json.get("output_tokens"))
                latencies.append(item.public_payload_json.get("elapsed_ms"))
    # Zero recorded calls is absent instrumentation, not a measured zero, so the
    # usage and latency it would report stays unknown. service_calls remains the
    # count of recorded rows, which is a record count rather than a measurement.
    measured = bool(calls)
    return CandidateMetrics(
        candidate_label=candidate_label,
        candidate_version_id=candidate_version_id,
        public_denominator_requests=sum(item.request_count for item in workloads),
        useful_completions=useful, **counts,
        protected_denominator=len(workloads), protected_passed=protected_passed,
        protected_failed=protected_failed, protected_missing=protected_missing,
        service_calls=calls,
        input_tokens=_known_sum(token_in, calls) if measured else None,
        output_tokens=_known_sum(token_out, calls) if measured else None,
        service_latency_ms=_known_sum(latencies, calls) if measured else None,
        provisioning_latency_ms=None, cost_minor_units=None,
    )


def _reading_complete(reading: TrialReading) -> bool:
    slot, run = reading.slot, reading.run
    if (slot.state != "COMPLETE" or run is None or run.state is not RunState.FINALIZED
            or reading.assessment is None or reading.assessment.expected_request_count != slot.request_count
            or reading.assessment.context_hash == "" or reading.protected_pass is None):
        return False
    outputs = {item.request_ordinal for item in reading.outputs
               if item.transport_error is None and bool(item.body)}
    if outputs != set(range(1, slot.executed_request_count + 1)):
        return False
    expected_tasks = {(ordinal, task.id, spec.id)
                      for ordinal, spec in enumerate(reading.public_specs, 1)
                      for task in spec.tasks}
    actual_tasks = {(item.request_ordinal, item.task_id, item.request_id)
                    for item in reading.task_assessments
                    if item.request_ordinal <= slot.request_count}
    public_rows = [item for item in reading.task_assessments
                   if item.request_ordinal <= slot.request_count]
    return (len(reading.public_specs) == slot.request_count
            and len(public_rows) == len(expected_tasks) and actual_tasks == expected_tasks)


def compare(
    experiment: Experiment, context: ExecutionContext,
    readings: tuple[TrialReading, ...], drift_fields: tuple[str, ...] = (),
) -> ComparisonOutcome:
    """Read status and metrics without selecting or ranking either candidate."""
    drift = set(drift_fields)
    budget_limits = getattr(context, "resource_limits_json", {}).get("mandatory_budget_metrics", {})
    if (type(budget_limits) is not dict or any(
        key not in _BUDGET_METRICS or type(limit) is not int or limit < 0
        for key, limit in budget_limits.items()
    )):
        drift.add("mandatory_budget_config")
        budget_limits = {}
    if len(readings) != 6:
        drift.add("slot_schedule")
    candidates = {item.label: item for item in experiment.candidates}
    if set(candidates) != {"A", "B"}:
        drift.add("candidates")
    expected_adapter = {
        EvidenceMode.TRUSTED_LOCAL: "local_process",
        EvidenceMode.ISOLATED_LIVE: "tokenfactory",
    }.get(context.executor_class)
    if expected_adapter is None:
        drift.add("executor_class")
    workloads: dict[int, FrozenWorkload] = {item.ordinal: item for item in context.workloads}
    for reading in readings:
        slot = reading.slot
        run = reading.run
        if run is not None and (run.evidence_mode != context.executor_class
                                or run.adapter != expected_adapter
                                or run.purpose is not RunPurpose.EXPERIMENT):
            drift.add("run_evidence_class")
        candidate = candidates.get(slot.candidate_label)
        workload = workloads.get(slot.pair_ordinal)
        if (candidate is None or workload is None or slot.artifact_version_id != candidate.artifact_version_id
                or slot.workload_id != workload.id or slot.request_batch_hash != workload.request_batch_hash
                or slot.request_count != workload.request_count
                or slot.executed_request_count != slot.request_count + 1):
            drift.add("slot_binding")
    if sorted((item.slot.pair_ordinal, item.slot.candidate_label) for item in readings) != [
        (pair, label) for pair in (1, 2, 3) for label in ("A", "B")
    ]:
        drift.add("slot_schedule")
    complete = (len(readings) == 6 and experiment.state == "FINALIZED"
                and all(_reading_complete(item) for item in readings))
    status = "NOT_COMPARABLE" if drift else "COMPLETE" if complete else "INCOMPLETE"
    # A declared label that is absent is already recorded as candidates drift, so
    # it resolves to an empty version rather than raising before the verdict.
    metrics = tuple(_metrics(
        label,
        candidates[label].artifact_version_id if label in candidates else "",
        tuple(item for item in readings if item.slot.candidate_label == label),
        context.workloads,
    ) for label in ("A", "B"))
    eligibility = []
    for label, item in zip(("A", "B"), metrics, strict=True):
        candidate_readings = tuple(reading for reading in readings
                                   if reading.slot.candidate_label == label)
        blockers = []
        if status != "COMPLETE":
            blockers.append(status)
        if any(reading.assessment is None or not reading.assessment.mandatory_pass
               for reading in candidate_readings):
            blockers.append("mandatory_public_rule")
        for reading in candidate_readings:
            if reading.protected_pass is False:
                blockers.extend(reading.protected_rule_ids)
        for metric_name, limit in budget_limits.items():
            value = getattr(item, metric_name)
            if value is None:
                blockers.append(f"unknown_mandatory_budget:{metric_name}")
            elif value > limit:
                blockers.append(f"mandatory_budget_exceeded:{metric_name}")
        eligibility.append(CandidateEligibility(
            candidate_label=label,
            candidate_version_id=item.candidate_version_id,
            eligible=not blockers,
            blocking_reason_codes=tuple(dict.fromkeys(blockers)),
        ))
    return ComparisonOutcome(
        experiment_id=experiment.id, status=status,
        shared_public_denominator_requests=sum(item.request_count for item in context.workloads),
        candidate_metrics=metrics, eligibility=tuple(eligibility),
        drift_fields=tuple(sorted(drift)),
    )
