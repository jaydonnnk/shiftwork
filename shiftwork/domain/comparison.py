"""Pure reading of one frozen six-slot comparison.

The caller supplies stored evidence. This module never loads a case, database,
file, model or current fixture. Protected task results stay in TrialReading and
only aggregate counts and public rule IDs leave the controller.
"""

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from shiftwork.domain import task_contract
from shiftwork.domain.models import (
    EvidenceMode, ExecutionContext, ExecutionObservation, Experiment,
    FrozenWorkload, ObservationKind, Run, RunAssessment, RunOutput, RunPurpose,
    RunState, TrialSlot, ReasonCode,
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
    service_calls: int | None
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
    repetitions: tuple["TrialReading", ...] = ()


class AcceptanceAspectKind(StrEnum):
    EVERY_REQUIRED_TASK_RETURNS_A_RESULT = "EVERY_REQUIRED_TASK_RETURNS_A_RESULT"
    NAMED_TASK_OUTCOMES = "NAMED_TASK_OUTCOMES"
    NO_TASK_REASON_CODE = "NO_TASK_REASON_CODE"


class AcceptanceAspect(BaseModel):
    model_config = _FROZEN
    kind: AcceptanceAspectKind
    task_id: str | None = Field(default=None, min_length=1)
    expected_outcomes: tuple[TaskOutcome, ...] = ()
    reason_code: ReasonCode | None = None

    @model_validator(mode="after")
    def kind_parameters(self):
        if self.kind is AcceptanceAspectKind.NAMED_TASK_OUTCOMES:
            if not self.task_id or not self.expected_outcomes or self.reason_code is not None:
                raise ValueError("named task aspect requires task/outcomes and forbids reason_code")
        elif self.kind is AcceptanceAspectKind.NO_TASK_REASON_CODE:
            if self.reason_code is None or self.task_id is not None or self.expected_outcomes:
                raise ValueError("no-task reason aspect requires reason_code and forbids task parameters")
        elif self.task_id is not None or self.expected_outcomes or self.reason_code is not None:
            raise ValueError("every-required-task aspect forbids parameters")
        return self


# Exact complete model payload SHA-256 pins, not aspect-name aliases or variant
# prefixes. These are historical metadata and are never derived from live files.
_LEGACY_ASPECT_PINS = {
    "e454f3cb8d18a6fd74d68d99fe1010de214f454fbaf5a8a20dd512b16c00822b":
        (AcceptanceAspectKind.EVERY_REQUIRED_TASK_RETURNS_A_RESULT, None, ()),
    "c048d7a330b0f8e4d2b6596308ec55ecd69f387a130be0f618d7c0d5b73a7c61":
        (AcceptanceAspectKind.NAMED_TASK_OUTCOMES, "collection", (TaskOutcome.USEFUL_COMPLETION,)),
    "719580f9cce15a976b67c9264474f94c90cd9b535fffc175f38655061817abbc":
        (AcceptanceAspectKind.NAMED_TASK_OUTCOMES, "collection", (TaskOutcome.USEFUL_COMPLETION,)),
    "5010122383875854893b638fd281a87a40e1f3370b5fbab69f6a7827fa527b3b":
        (AcceptanceAspectKind.NAMED_TASK_OUTCOMES, "alternative",
         (TaskOutcome.USEFUL_COMPLETION, TaskOutcome.JUSTIFIED_REFUSAL)),
    "4218f96809a382d3d757a4b9ce82a2e62b8c135cfa4af8249d636ecc25eb4ef3":
        (AcceptanceAspectKind.NAMED_TASK_OUTCOMES, "collection", (TaskOutcome.JUSTIFIED_REFERRAL,)),
    "e5f82f389eb25b5a1940ae253ef8e042455f8bf2079a619d4942786ad877ac92":
        (AcceptanceAspectKind.NAMED_TASK_OUTCOMES, "collection", (TaskOutcome.USEFUL_COMPLETION,)),
}


def _payload_sha256(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


# Three original payloads omit optional record fields that the model
# includes as defaults in historical reservation snapshots. Admit only these
# exact source encodings and their exact normalized snapshot encodings.
_LEGACY_SOURCE_TO_SNAPSHOT = {
    **{pin: pin for pin in _LEGACY_ASPECT_PINS},
    "b73118cf02e729145bbc0fba34380397b623afe084cc97801422b9cf67a7502b":
        "719580f9cce15a976b67c9264474f94c90cd9b535fffc175f38655061817abbc",
    "c34452998c0b16119a4bf57d1ac92ad71686b0b6a7066be65cda2dd20538e56c":
        "5010122383875854893b638fd281a87a40e1f3370b5fbab69f6a7827fa527b3b",
    "5ec04467126c5dcaee364abbd63696e84df4b0747463881bb247a41dc9eeab00":
        "4218f96809a382d3d757a4b9ce82a2e62b8c135cfa4af8249d636ecc25eb4ef3",
}


def validate_legacy_payload(raw: dict, case: SealedCase) -> None:
    if _LEGACY_SOURCE_TO_SNAPSHOT.get(_payload_sha256(raw)) != _payload_sha256(case.model_dump(mode="json")):
        raise ValueError("legacy acceptance payload is not exactly pinned")


def acceptance_aspect(case: SealedCase) -> AcceptanceAspect:
    """Pure typed assessment view; never modifies the identity-bearing case."""
    raw = case.expected.get("aspect")
    if isinstance(raw, str):
        pinned = _LEGACY_ASPECT_PINS.get(_payload_sha256(case.model_dump(mode="json")))
        if pinned is None or case.family != "task_completion":
            raise ValueError("legacy acceptance payload is not exactly pinned")
        kind, task_id, outcomes = pinned
        aspect = AcceptanceAspect(kind=kind, task_id=task_id, expected_outcomes=outcomes)
    else:
        aspect = AcceptanceAspect.model_validate(raw)
    if case.stimulus is None:
        raise ValueError("acceptance aspect requires its own protected task spec")
    if (aspect.kind is AcceptanceAspectKind.NAMED_TASK_OUTCOMES
            and aspect.task_id not in {task.id for task in case.stimulus.task_spec.tasks}):
        raise ValueError("acceptance aspect names an unknown task")
    return aspect


def validate_acceptance_aspect(case: SealedCase, *, engagement_slug: str) -> AcceptanceAspect:
    """Controller admission binds historical compatibility to the owning pack."""
    if isinstance(case.expected.get("aspect"), str) and engagement_slug != "bookshop":
        raise ValueError("legacy acceptance payload belongs only to Bellwether")
    return acceptance_aspect(case)


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
    aspect = acceptance_aspect(case)
    if aspect.kind is AcceptanceAspectKind.EVERY_REQUIRED_TASK_RETURNS_A_RESULT:
        return all(by_id[task.id].outcome is not TaskOutcome.MISSING_OUTPUT
                   for task in spec.tasks if task.required)
    if aspect.kind is AcceptanceAspectKind.NAMED_TASK_OUTCOMES:
        return by_id[aspect.task_id].outcome in aspect.expected_outcomes
    return all(aspect.reason_code not in entry.reason_codes for entry in assessments)


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


def public_repetition_count(context: ExecutionContext) -> int:
    count = context.resource_limits_json.get("public_repetitions", 1)
    if type(count) is not int or not 1 <= count <= 3:
        raise ValueError("invalid frozen comparison repetition count")
    return count


def _known_sum(values: list[object], expected: int) -> int | None:
    if len(values) != expected or any(type(value) is not int or value < 0 for value in values):
        return None
    return sum(values)


def _metrics(candidate_label: str, candidate_version_id: str,
             readings: tuple[TrialReading, ...],
             workloads: tuple[FrozenWorkload, ...],
             evidence_mode: EvidenceMode, repetitions: int = 1) -> CandidateMetrics:
    counts = {name: 0 for name in _OUTCOME_FIELDS.values()}
    useful = 0
    protected_passed = protected_failed = protected_missing = 0
    calls = 0
    meter_complete = True
    token_in: list[object] = []
    token_out: list[object] = []
    latencies: list[object] = []
    by_pair = {item.slot.pair_ordinal: item for item in readings}
    for workload in workloads:
        reading = by_pair.get(workload.ordinal)
        if reading is None:
            counts["missing_outputs"] += workload.request_count * repetitions
            protected_missing += 1
            meter_complete = False
            continue
        if reading.protected_pass is True:
            protected_passed += 1
        elif reading.protected_pass is False:
            protected_failed += 1
        else:
            protected_missing += 1
        public_readings = (reading,) + reading.repetitions
        counts["missing_outputs"] += max(0, repetitions - len(public_readings)) * workload.request_count
        if len(public_readings) != repetitions:
            meter_complete = False
        for reading in public_readings:
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
            # Protected work is a separate denominator and cannot enter public
            # efficiency or cost counters, even when its model usage is recorded.
            public_observations = tuple(item for item in reading.observations
                                        if 1 <= item.request_ordinal <= slot.request_count)
            if evidence_mode is EvidenceMode.ISOLATED_LIVE:
                for ordinal in range(1, slot.request_count + 1):
                    observed = sum(item.kind is ObservationKind.INFERENCE_REQUEST
                                   for item in public_observations if item.request_ordinal == ordinal)
                    meters = [item.public_payload_json for item in public_observations
                              if item.kind is ObservationKind.INTERPRETATION
                              and item.request_ordinal == ordinal
                              and item.public_payload_json.get("inference_meter_complete") is True]
                    if (len(meters) != 1 or meters[0].get("source") != "controller_verified"
                            or type(meters[0].get("service_calls")) is not int
                            or meters[0]["service_calls"] != observed):
                        meter_complete = False
            calls += sum(item.kind is ObservationKind.INFERENCE_REQUEST for item in public_observations)
            for item in public_observations:
                if item.kind is ObservationKind.INFERENCE_RESULT:
                    token_in.append(item.public_payload_json.get("input_tokens"))
                    token_out.append(item.public_payload_json.get("output_tokens"))
                    latencies.append(item.public_payload_json.get("elapsed_ms"))
    # The local fixture has no inference grant. For a live run, every public
    # request needs a controller-owned terminal meter, including explicit zeroes.
    measured = evidence_mode is EvidenceMode.TRUSTED_LOCAL or meter_complete
    known_calls = calls if measured else None
    return CandidateMetrics(
        candidate_label=candidate_label,
        candidate_version_id=candidate_version_id,
        public_denominator_requests=sum(item.request_count for item in workloads) * repetitions,
        useful_completions=useful, **counts,
        protected_denominator=len(workloads), protected_passed=protected_passed,
        protected_failed=protected_failed, protected_missing=protected_missing,
        service_calls=known_calls,
        input_tokens=_known_sum(token_in, calls) if measured else None,
        output_tokens=_known_sum(token_out, calls) if measured else None,
        service_latency_ms=_known_sum(latencies, calls) if measured else None,
        provisioning_latency_ms=None, cost_minor_units=None,
    )


def _reading_complete(reading: TrialReading, protected_required: bool = True) -> bool:
    slot, run = reading.slot, reading.run
    if (slot.state != "COMPLETE" or run is None or run.state is not RunState.FINALIZED
            or reading.assessment is None or reading.assessment.expected_request_count != slot.request_count
            or reading.assessment.context_hash == "" or (protected_required and reading.protected_pass is None)):
        return False
    outputs = {item.request_ordinal for item in reading.outputs
               if item.transport_error is None and bool(item.body)}
    count = slot.executed_request_count if protected_required else slot.request_count
    if outputs != set(range(1, count + 1)):
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
    try:
        repetitions = public_repetition_count(context)
    except ValueError:
        repetitions = 1
        drift.add("public_repetitions")
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
                and all(_reading_complete(item) and len(item.repetitions) == repetitions - 1
                        and all(_reading_complete(rep, False) for rep in item.repetitions)
                        for item in readings))
    status = "NOT_COMPARABLE" if drift else "COMPLETE" if complete else "INCOMPLETE"
    # A declared label that is absent is already recorded as candidates drift, so
    # it resolves to an empty version rather than raising before the verdict.
    metrics = tuple(_metrics(
        label,
        candidates[label].artifact_version_id if label in candidates else "",
        tuple(item for item in readings if item.slot.candidate_label == label),
        context.workloads,
        context.executor_class, repetitions,
    ) for label in ("A", "B"))
    eligibility = []
    for label, item in zip(("A", "B"), metrics, strict=True):
        candidate_readings = tuple(reading for reading in readings
                                   if reading.slot.candidate_label == label)
        blockers = []
        if status != "COMPLETE":
            blockers.append(status)
        if any(rep.assessment is None or not rep.assessment.mandatory_pass
               for reading in candidate_readings for rep in (reading,) + reading.repetitions):
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
        shared_public_denominator_requests=sum(item.request_count for item in context.workloads) * repetitions,
        candidate_metrics=metrics, eligibility=tuple(eligibility),
        drift_fields=tuple(sorted(drift)),
    )
