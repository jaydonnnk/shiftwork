"""Pure S45 policy checks, with no database or model inference."""

from dataclasses import replace

import pytest

from shiftwork.domain.comparison import compare
from test_comparison import _fixture, _as_live, _metered


def fixture(live=False):
    experiment, context, readings = _fixture()
    if live:
        _as_live(context, readings)
        readings = [_metered(row, (0, 0)) for row in readings]
    context.resource_limits_json = {"public_repetitions": 3}
    readings = [replace(row, repetitions=tuple(replace(row, outputs=row.outputs[:2],
        protected_pass=None) for _ in range(2))) for row in readings]
    return experiment, context, readings


def test_repetition_metrics_count_public_evidence_and_protection_once():
    experiment, context, readings = fixture()
    result = compare(experiment, context, tuple(readings))
    assert result.status == "COMPLETE"
    assert result.shared_public_denominator_requests == 18, "the frozen public denominator includes all repetitions"
    assert [row.useful_completions for row in result.candidate_metrics] == [18, 18], "every retained repetition contributes its actual completion count"
    assert [row.protected_passed for row in result.candidate_metrics] == [3, 3], "public repetitions must never multiply protected draws"


@pytest.mark.parametrize("fault", ["run", "assessment", "output", "task"])
def test_an_incomplete_public_repetition_cannot_look_complete(fault):
    experiment, context, readings = fixture()
    children = list(readings[0].repetitions)
    child = children[-1]
    if fault == "run": child = replace(child, run=None)
    elif fault == "assessment": child = replace(child, assessment=None)
    elif fault == "output": child = replace(child, outputs=child.outputs[:1])
    else: child = replace(child, task_assessments=child.task_assessments[:1])
    children[-1] = child
    readings[0] = replace(readings[0], repetitions=tuple(children))
    result = compare(experiment, context, tuple(readings))
    assert result.status == "INCOMPLETE", "every public repetition needs complete capture and assessment evidence"
    assert not any(row.eligible for row in result.eligibility)


def test_missing_public_repetition_stays_in_the_frozen_denominator():
    experiment, context, readings = fixture()
    readings[0] = replace(readings[0], repetitions=readings[0].repetitions[:1])
    result = compare(experiment, context, tuple(readings))
    assert result.status == "INCOMPLETE", "unequal public repetition counts must remain incomplete"
    assert result.candidate_metrics[0].missing_outputs == 2, "missing repetitions must retain their request denominator"
    assert result.candidate_metrics[0].public_denominator_requests == 18
    assert result.candidate_metrics[0].protected_denominator == 3


@pytest.mark.parametrize("count", [0, 4, True, 2.5])
def test_invalid_frozen_repetition_count_is_not_comparable(count):
    experiment, context, readings = fixture()
    context.resource_limits_json["public_repetitions"] = count
    result = compare(experiment, context, tuple(readings))
    assert result.status == "NOT_COMPARABLE" and "public_repetitions" in result.drift_fields, (
        "invalid frozen repetition counts must be refused by the pure policy")


def test_each_live_repetition_needs_its_own_complete_usage_meter():
    experiment, context, readings = fixture(live=True)
    context.resource_limits_json["mandatory_budget_metrics"] = {"service_calls": 0}
    clean = compare(experiment, context, tuple(readings))
    assert [row.service_calls for row in clean.candidate_metrics] == [0, 0]
    assert all(row.eligible for row in clean.eligibility)
    children = list(readings[0].repetitions)
    children[-1] = replace(children[-1], observations=())
    readings[0] = replace(readings[0], repetitions=tuple(children))
    missing = compare(experiment, context, tuple(readings))
    assert missing.candidate_metrics[0].service_calls is None, "a missing repetition meter is unknown, never zero"
    assert [row.eligible for row in missing.eligibility] == [False, True]
