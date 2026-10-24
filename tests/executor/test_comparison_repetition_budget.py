"""S45 reserves all calls at the full cap, including failed attempts."""

from decimal import Decimal

import pytest

from shiftwork import hosted
from shiftwork.live_budget import LiveComparisonBudget


def test_comparison_meter_reserves_42_calls_and_24_operations():
    meter = hosted.comparison_budget()
    accepted = True
    try:
        meter.preflight(model=meter.model, slots=6, requests=42, public_repetitions=3)
    except ValueError:
        accepted = False
    assert accepted, "the meter must admit the frozen 42-call, 24-operation shape"
    assert (meter.max_calls, meter.max_operations) == (42, 24), "meter must freeze the exact repeated shape"
    for _ in range(24):
        meter.before_operation()
    for _ in range(42):
        meter.before_inference(meter.model)
    assert meter.projected_usd == Decimal("0.09289728"), "reserve the full token cap for every call"
    with pytest.raises(ValueError, match="Sandbox operation ceiling"):
        meter.before_operation()
    with pytest.raises(ValueError, match="inference call ceiling"):
        meter.before_inference(meter.model)


def test_comparison_meter_refuses_reuse_and_mismatched_frozen_shape():
    meter = hosted.comparison_budget()
    with pytest.raises(ValueError, match="shape"):
        meter.preflight(model=meter.model, slots=6, requests=18, public_repetitions=3)
    assert meter.calls == meter.operations == 0
    meter.preflight(model=meter.model, slots=6, requests=42, public_repetitions=3)
    meter.before_operation()
    with pytest.raises(ValueError, match="shape"):
        meter.preflight(model=meter.model, slots=6, requests=42, public_repetitions=3)


def test_comparison_meter_refuses_reserved_spend_before_any_call():
    meter = hosted.comparison_budget()
    meter.max_projected_usd = Decimal("0.09")
    with pytest.raises(ValueError, match="spend"):
        meter.preflight(model=meter.model, slots=6, requests=42, public_repetitions=3)
    assert meter.calls == meter.operations == 0


@pytest.mark.parametrize("field,value", [("repetitions", 0), ("repetitions", 4), ("repetitions", True),
    ("slot-count", 5), ("request-count", 0), ("request-count", 5), ("request-count", True),
    ("max-operations", 23), ("max-calls", 41), ("used-operations", 1), ("used-calls", 1)])
def test_meter_shape_guards_are_independent(field, value):
    meter = LiveComparisonBudget(hosted.config.SERVICE_MODEL, hosted.INPUT_RATE, hosted.OUTPUT_RATE,
        max_calls=200, max_operations=60, max_projected_usd=Decimal("5"))
    repetitions = value if field == "repetitions" else 3
    counts = (2, 2, 2, 2, 2) if field == "slot-count" else (value, 2, 2, 2, 2, 2) if field == "request-count" else (2,) * 6
    if field == "max-operations": meter.max_operations = value
    if field == "max-calls": meter.max_calls = value
    if field == "used-operations": meter.operations = value
    if field == "used-calls": meter.calls = value
    with pytest.raises(ValueError, match="shape"):
        meter.preflight(model=meter.model, slots=6,
            requests=sum(count * repetitions + 1 for count in counts),
            public_repetitions=repetitions, requests_per_slot=counts)


def test_spend_refusal_does_not_reserve_an_unsent_call():
    meter = hosted.comparison_budget()
    meter.preflight(model=meter.model, slots=6, requests=42, public_repetitions=3)
    meter.calls = 40
    meter.max_projected_usd = Decimal("0.09")
    with pytest.raises(ValueError, match="spend"):
        meter.before_inference(meter.model)
    assert meter.calls == 40, "a spend refusal must happen before reserving an unsent call"
