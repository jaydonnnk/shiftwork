"""Failure-capable policy checks for the pure six-slot outcome reading."""

from types import SimpleNamespace as NS

import pytest

from shiftwork.domain.comparison import TrialReading, compare, protected_acceptance
from shiftwork.domain.models import EvidenceMode, ObservationKind, RunPurpose, RunState
from shiftwork.domain.task_contract import TaskAssessment, TaskOutcome
from shiftwork.sealed import store as sealed_store


def _task(ordinal, task_id="collection", outcome=TaskOutcome.USEFUL_COMPLETION,
          mandatory_pass=True):
    return TaskAssessment(
        request_id=f"request-{ordinal}", request_ordinal=ordinal, task_id=task_id,
        outcome=outcome, mandatory_pass=mandatory_pass, reason_codes=(),
    )


def _fixture():
    workloads = tuple(NS(id=f"workload-{pair}", ordinal=pair, request_count=2,
                         request_batch_hash=f"batch-{pair}") for pair in (1, 2, 3))
    context = NS(workloads=workloads, content_hash="frozen-context",
                 executor_class=EvidenceMode.TRUSTED_LOCAL)
    candidates = tuple(NS(label=label, artifact_version_id=f"version-{label}")
                       for label in ("A", "B"))
    experiment = NS(id="comparison-1", state="FINALIZED", candidates=candidates)
    readings = []
    for pair in (1, 2, 3):
        for label in ("A", "B"):
            specs = tuple(NS(id=f"request-{ordinal}", tasks=(NS(id="collection", required=True),))
                          for ordinal in (1, 2))
            slot = NS(pair_ordinal=pair, candidate_label=label,
                      artifact_version_id=f"version-{label}", workload_id=f"workload-{pair}",
                      request_batch_hash=f"batch-{pair}", request_count=2,
                      executed_request_count=3, state="COMPLETE")
            run = NS(state=RunState.FINALIZED, evidence_mode=EvidenceMode.TRUSTED_LOCAL,
                     adapter="local_process", purpose=RunPurpose.EXPERIMENT)
            assessment = NS(expected_request_count=2, context_hash="frozen-context",
                            mandatory_pass=True)
            outputs = tuple(NS(request_ordinal=ordinal, transport_error=None, body=b"{}")
                            for ordinal in (1, 2, 3))
            readings.append(TrialReading(
                slot=slot, run=run, assessment=assessment, public_specs=specs,
                task_assessments=(_task(1), _task(2)), outputs=outputs, observations=(),
                protected_pass=True, protected_rule_ids=("task.required_results",),
            ))
    return experiment, context, readings


def test_public_and_protected_denominators_and_unknown_cost_are_separate():
    experiment, context, readings = _fixture()
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.status == "COMPLETE"
    assert outcome.shared_public_denominator_requests == 6
    assert [item.public_denominator_requests for item in outcome.candidate_metrics] == [6, 6]
    assert [item.protected_denominator for item in outcome.candidate_metrics] == [3, 3]
    assert [item.protected_passed for item in outcome.candidate_metrics] == [3, 3]
    assert all(item.useful_completions == 6 and item.cost_minor_units is None
               for item in outcome.candidate_metrics)
    assert all(item.eligible for item in outcome.eligibility)


def test_trusted_local_without_a_gateway_proves_zero_model_usage():
    experiment, context, readings = _fixture()
    assert all(item.observations == () for item in readings)
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.status == "COMPLETE"
    for metrics in outcome.candidate_metrics:
        assert metrics.service_calls == 0
        assert metrics.input_tokens == 0
        assert metrics.output_tokens == 0
        assert metrics.service_latency_ms == 0
        assert metrics.cost_minor_units is None
        assert metrics.provisioning_latency_ms is None


def _as_live(context, readings):
    context.executor_class = EvidenceMode.ISOLATED_LIVE
    for index, reading in enumerate(readings):
        run = NS(**{**reading.run.__dict__, "evidence_mode": EvidenceMode.ISOLATED_LIVE,
                    "adapter": "tokenfactory"})
        readings[index] = TrialReading(**{**reading.__dict__, "run": run})


def _metered(reading, calls_by_ordinal):
    observations = []
    for ordinal, count in enumerate(calls_by_ordinal, 1):
        if count:
            observations.extend((
                NS(kind=ObservationKind.INFERENCE_REQUEST, request_ordinal=ordinal,
                   public_payload_json={"source": "controller_verified"}),
                NS(kind=ObservationKind.INFERENCE_RESULT, request_ordinal=ordinal,
                   public_payload_json={"input_tokens": 7, "output_tokens": 9,
                                        "elapsed_ms": 11}),
            ))
        observations.append(NS(
            kind=ObservationKind.INTERPRETATION, request_ordinal=ordinal,
            public_payload_json={"source": "controller_verified",
                                 "inference_meter_complete": True, "service_calls": count},
        ))
    return TrialReading(**{**reading.__dict__, "observations": tuple(observations)})


def test_live_missing_meter_cannot_beat_a_measured_candidate_on_a_mandatory_call_budget():
    experiment, context, readings = _fixture()
    _as_live(context, readings)
    context.resource_limits_json = {"mandatory_budget_metrics": {"service_calls": 0}}
    for index, reading in enumerate(readings):
        if reading.slot.candidate_label == "A":
            readings[index] = _metered(reading, (1, 0) if index == 0 else (0, 0))
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.status == "COMPLETE"
    assert outcome.candidate_metrics[0].service_calls == 1
    assert outcome.candidate_metrics[1].service_calls is None
    assert outcome.eligibility[0].blocking_reason_codes == (
        "mandatory_budget_exceeded:service_calls",)
    assert outcome.eligibility[1].blocking_reason_codes == (
        "unknown_mandatory_budget:service_calls",)
    assert not any(item.eligible for item in outcome.eligibility)


def test_live_controller_meter_proves_zero_and_missing_one_marker_restores_unknown():
    experiment, context, readings = _fixture()
    _as_live(context, readings)
    context.resource_limits_json = {"mandatory_budget_metrics": {"service_calls": 0}}
    readings[:] = [_metered(reading, (0, 0)) for reading in readings]
    outcome = compare(experiment, context, tuple(readings))
    assert [item.service_calls for item in outcome.candidate_metrics] == [0, 0]
    assert all(item.eligible for item in outcome.eligibility)
    first = readings[0]
    readings[0] = TrialReading(**{**first.__dict__, "observations": first.observations[:1]})
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.candidate_metrics[0].service_calls is None
    assert outcome.eligibility[0].blocking_reason_codes == (
        "unknown_mandatory_budget:service_calls",)


def test_a_declared_candidate_set_that_is_not_exactly_a_and_b_returns_a_verdict():
    experiment, context, readings = _fixture()
    experiment.candidates = tuple(
        candidate for candidate in experiment.candidates if candidate.label == "A"
    )
    try:
        outcome = compare(experiment, context, tuple(readings))
    except KeyError as exc:
        pytest.fail(f"the candidates drift branch raised instead of returning a verdict: {exc!r}")
    assert outcome.status == "NOT_COMPARABLE"
    assert "candidates" in outcome.drift_fields
    assert [item.candidate_label for item in outcome.candidate_metrics] == ["A", "B"]
    assert [item.candidate_version_id for item in outcome.candidate_metrics] == [
        "version-A", "",
    ]
    assert [item.candidate_label for item in outcome.eligibility] == ["A", "B"]
    assert all(not item.eligible for item in outcome.eligibility)


def test_one_completed_task_cannot_credit_a_multi_task_request():
    experiment, context, readings = _fixture()
    first = readings[0]
    specs = list(first.public_specs)
    specs[0] = NS(id="request-1", tasks=(NS(id="collection", required=True),
                                          NS(id="alternative", required=True)))
    assessed = (_task(1), _task(1, "alternative", TaskOutcome.MISSING_OUTPUT, False), _task(2))
    readings[0] = TrialReading(**{**first.__dict__, "public_specs": tuple(specs),
                                  "task_assessments": assessed,
                                  "assessment": NS(expected_request_count=2,
                                                   context_hash="frozen-context", mandatory_pass=False)})
    outcome = compare(experiment, context, tuple(readings))
    a = outcome.candidate_metrics[0]
    assert a.useful_completions == 5
    assert a.missing_outputs == 1
    assert outcome.eligibility[0].eligible is False
    assert outcome.eligibility[1].eligible is True


def test_overlapping_noncompletion_counts_are_not_a_partition():
    experiment, context, readings = _fixture()
    first = readings[0]
    specs = list(first.public_specs)
    specs[0] = NS(id="request-1", tasks=(NS(id="collection", required=True),
                                          NS(id="alternative", required=True)))
    assessed = (_task(1, "collection", TaskOutcome.INCORRECT_OUTPUT, False),
                _task(1, "alternative", TaskOutcome.JUSTIFIED_REFERRAL), _task(2))
    readings[0] = TrialReading(**{**first.__dict__, "public_specs": tuple(specs),
                                  "task_assessments": assessed,
                                  "assessment": NS(expected_request_count=2,
                                                   context_hash="frozen-context", mandatory_pass=False)})
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.candidate_metrics[0].incorrect_outputs == 1
    assert outcome.candidate_metrics[0].justified_referrals == 1
    assert outcome.candidate_metrics[0].useful_completions == 5
    assert outcome.noncompletion_incidence_non_additive is True


@pytest.mark.parametrize("category,field", [
    (TaskOutcome.JUSTIFIED_CLARIFICATION, "justified_clarifications"),
    (TaskOutcome.UNJUSTIFIED_CLARIFICATION, "unjustified_clarifications"),
    (TaskOutcome.JUSTIFIED_REFUSAL, "justified_refusals"),
    (TaskOutcome.UNJUSTIFIED_REFUSAL, "unjustified_refusals"),
])
def test_fallback_categories_never_become_useful_completion(category, field):
    experiment, context, readings = _fixture()
    first = readings[0]
    readings[0] = TrialReading(**{**first.__dict__,
                                  "task_assessments": (_task(1, outcome=category), _task(2))})
    metrics = compare(experiment, context, tuple(readings)).candidate_metrics[0]
    assert getattr(metrics, field) == 1
    assert metrics.useful_completions == 5


def test_missing_optional_answer_does_not_erase_completed_required_work():
    experiment, context, readings = _fixture()
    first = readings[0]
    specs = list(first.public_specs)
    specs[0] = NS(id="request-1", tasks=(NS(id="collection", required=True),
                                          NS(id="price", required=False)))
    readings[0] = TrialReading(**{**first.__dict__, "public_specs": tuple(specs),
                                  "task_assessments": (_task(1),
                                                       _task(1, "price", TaskOutcome.MISSING_OUTPUT),
                                                       _task(2))})
    metrics = compare(experiment, context, tuple(readings)).candidate_metrics[0]
    assert metrics.useful_completions == 6
    assert metrics.missing_outputs == 0


def test_missing_slot_stays_in_both_frozen_denominators():
    experiment, context, readings = _fixture()
    readings.pop(0)
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.status == "NOT_COMPARABLE"
    assert outcome.candidate_metrics[0].public_denominator_requests == 6
    assert outcome.candidate_metrics[0].protected_denominator == 3
    assert outcome.candidate_metrics[0].missing_outputs == 2
    assert outcome.candidate_metrics[0].protected_missing == 1


def test_interrupted_slot_is_incomplete_and_cannot_be_eligible():
    experiment, context, readings = _fixture()
    first = readings[0]
    readings[0] = TrialReading(**{**first.__dict__, "slot": NS(**{**first.slot.__dict__,
                                                                   "state": "FAILED"}),
                                  "run": NS(**{**first.run.__dict__, "state": RunState.FAILED}),
                                  "protected_pass": None})
    experiment.state = "FAILED"
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.status == "INCOMPLETE"
    assert all(not item.eligible for item in outcome.eligibility)
    assert outcome.candidate_metrics[0].protected_missing == 1


def test_failed_slot_cannot_be_called_complete_even_if_experiment_state_is_finalized():
    experiment, context, readings = _fixture()
    first = readings[0]
    readings[0] = TrialReading(**{**first.__dict__, "slot": NS(**{**first.slot.__dict__,
                                                                   "state": "FAILED"})})
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.status == "INCOMPLETE"
    assert outcome.eligibility[0].eligible is False


def test_task_identity_mismatch_cannot_look_like_a_complete_slot():
    experiment, context, readings = _fixture()
    first = readings[0]
    readings[0] = TrialReading(**{**first.__dict__,
                                  "task_assessments": (_task(1, task_id="other"), _task(2))})
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.status == "INCOMPLETE"
    assert outcome.eligibility[0].eligible is False


def test_context_drift_blocks_both_candidates_before_efficiency():
    experiment, context, readings = _fixture()
    outcome = compare(experiment, context, tuple(readings), ("mission_bytes_hash",))
    assert outcome.status == "NOT_COMPARABLE"
    assert outcome.drift_fields == ("mission_bytes_hash",)
    assert all(not item.eligible for item in outcome.eligibility)


def test_recorded_or_wrongly_bound_run_mode_cannot_qualify():
    experiment, context, readings = _fixture()
    run = readings[0].run
    for field, wrong in (
        ("adapter", "recorded"),
        ("evidence_mode", EvidenceMode.RECORDED_INSPECTION),
        ("purpose", RunPurpose.OPERATION),
    ):
        original = getattr(run, field)
        setattr(run, field, wrong)
        outcome = compare(experiment, context, tuple(readings))
        assert outcome.status == "NOT_COMPARABLE", field
        assert "run_evidence_class" in outcome.drift_fields, field
        assert all(not item.eligible for item in outcome.eligibility), field
        setattr(run, field, original)
    assert compare(experiment, context, tuple(readings)).status == "COMPLETE"
    context.executor_class = EvidenceMode.RECORDED_INSPECTION
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.status == "NOT_COMPARABLE"
    assert "executor_class" in outcome.drift_fields


def test_one_protected_mandatory_failure_blocks_only_that_candidate():
    experiment, context, readings = _fixture()
    first = readings[0]
    readings[0] = TrialReading(**{**first.__dict__, "protected_pass": False,
                                  "protected_rule_ids": ("collection.confirmed_only",)})
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.status == "COMPLETE"
    assert outcome.candidate_metrics[0].protected_failed == 1
    assert outcome.eligibility[0].blocking_reason_codes == ("collection.confirmed_only",)
    assert outcome.eligibility[0].eligible is False
    assert outcome.eligibility[1].eligible is True


def test_missing_usage_is_unknown_even_with_a_recorded_model_call():
    experiment, context, readings = _fixture()
    first = readings[0]
    observations = (
        NS(kind=ObservationKind.INFERENCE_REQUEST, request_ordinal=1, public_payload_json={}),
        NS(kind=ObservationKind.INFERENCE_RESULT,
           request_ordinal=1,
           public_payload_json={"input_tokens": None, "output_tokens": 13, "elapsed_ms": 21}),
    )
    readings[0] = TrialReading(**{**first.__dict__, "observations": observations})
    metrics = compare(experiment, context, tuple(readings)).candidate_metrics[0]
    assert metrics.service_calls == 1
    assert metrics.input_tokens is None
    assert metrics.output_tokens == 13
    assert metrics.service_latency_ms == 21
    assert metrics.cost_minor_units is None


def test_missing_result_for_a_model_call_keeps_usage_and_latency_unknown():
    experiment, context, readings = _fixture()
    first = readings[0]
    readings[0] = TrialReading(**{**first.__dict__, "observations": (
        NS(kind=ObservationKind.INFERENCE_REQUEST, request_ordinal=1, public_payload_json={}),
    )})
    metrics = compare(experiment, context, tuple(readings)).candidate_metrics[0]
    assert metrics.service_calls == 1
    assert metrics.input_tokens is None
    assert metrics.output_tokens is None
    assert metrics.service_latency_ms is None


def test_protected_model_usage_never_enters_public_efficiency_metrics():
    experiment, context, readings = _fixture()
    first = readings[0]
    readings[0] = TrialReading(**{**first.__dict__, "observations": (
        NS(kind=ObservationKind.INFERENCE_REQUEST, request_ordinal=1, public_payload_json={}),
        NS(kind=ObservationKind.INFERENCE_RESULT, request_ordinal=1,
           public_payload_json={"input_tokens": 7, "output_tokens": 9, "elapsed_ms": 11}),
        NS(kind=ObservationKind.INFERENCE_REQUEST, request_ordinal=3, public_payload_json={}),
        NS(kind=ObservationKind.INFERENCE_RESULT, request_ordinal=3,
           public_payload_json={"input_tokens": 101, "output_tokens": 202, "elapsed_ms": 303}),
    )})
    metrics = compare(experiment, context, tuple(readings)).candidate_metrics[0]
    assert (metrics.service_calls, metrics.input_tokens, metrics.output_tokens,
            metrics.service_latency_ms) == (1, 7, 9, 11)


def test_unknown_mandatory_cost_and_exceeded_call_budget_block_eligibility():
    experiment, context, readings = _fixture()
    context.resource_limits_json = {"mandatory_budget_metrics": {"cost_minor_units": 25}}
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.status == "COMPLETE"
    assert all(not item.eligible for item in outcome.eligibility)
    assert all(item.blocking_reason_codes == ("unknown_mandatory_budget:cost_minor_units",)
               for item in outcome.eligibility)

    context.resource_limits_json = {"mandatory_budget_metrics": {"service_calls": 0}}
    first = readings[0]
    readings[0] = TrialReading(**{**first.__dict__, "observations": (
        NS(kind=ObservationKind.INFERENCE_REQUEST, request_ordinal=1, public_payload_json={}),
    )})
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.eligibility[0].blocking_reason_codes == (
        "mandatory_budget_exceeded:service_calls",
    )
    assert outcome.eligibility[1].eligible is True


def test_invalid_mandatory_budget_config_is_not_comparable():
    experiment, context, readings = _fixture()
    context.resource_limits_json = {"mandatory_budget_metrics": {"cost_minor_units": True}}
    outcome = compare(experiment, context, tuple(readings))
    assert outcome.status == "NOT_COMPARABLE"
    assert outcome.drift_fields == ("mandatory_budget_config",)


def test_protected_aspect_needs_its_specific_task_outcome():
    cases = sealed_store.load_family("task_completion").cases
    referral = next(case for case in cases if case.expected["aspect"] ==
                    "conflicting_necessary_collection_records_require_referral")
    spec = referral.stimulus.task_spec
    ordinal = referral.stimulus.request.ordinal
    assessments = tuple(TaskAssessment(
        request_id=spec.id, request_ordinal=ordinal, task_id=task.id,
        outcome=(TaskOutcome.JUSTIFIED_REFERRAL if task.id == "collection"
                 else TaskOutcome.JUSTIFIED_REFUSAL), mandatory_pass=True, reason_codes=(),
    ) for task in spec.tasks)
    assert protected_acceptance(referral, assessments)
    wrong = tuple(item.model_copy(update={"outcome": TaskOutcome.USEFUL_COMPLETION})
                  if item.task_id == "collection" else item for item in assessments)
    assert protected_acceptance(referral, wrong) is False

    failed = tuple(item.model_copy(update={"mandatory_pass": False})
                   if item.task_id == "collection" else item for item in assessments)
    assert protected_acceptance(referral, failed) is False


def test_strict_budget_case_accepts_only_a_justified_no_match_or_valid_result():
    case = next(case for case in sealed_store.load_family("task_completion").cases
                if case.expected["aspect"] == "completed_alternative_meets_strict_budget")
    spec = case.stimulus.task_spec
    ordinal = case.stimulus.request.ordinal
    assessed = tuple(TaskAssessment(
        request_id=spec.id, request_ordinal=ordinal, task_id=task.id,
        outcome=(TaskOutcome.JUSTIFIED_REFUSAL if task.id == "alternative"
                 else TaskOutcome.USEFUL_COMPLETION), mandatory_pass=True, reason_codes=(),
    ) for task in spec.tasks)
    assert protected_acceptance(case, assessed)
    invalid = tuple(item.model_copy(update={"outcome": TaskOutcome.INCORRECT_OUTPUT,
                                     "mandatory_pass": False})
                    if item.task_id == "alternative" else item for item in assessed)
    assert protected_acceptance(case, invalid) is False
