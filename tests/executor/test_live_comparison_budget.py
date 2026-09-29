"""The one-run spend ceiling counts both phases, including failed attempts."""

import asyncio
from decimal import Decimal

import pytest

from shiftwork.gateway.protocol import InferencePolicy
from shiftwork.gateway.service_inference import GatewayRejected, ServiceInferenceGateway
from shiftwork.live_budget import LiveComparisonBudget


MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"


def budget() -> LiveComparisonBudget:
    return LiveComparisonBudget(MODEL, Decimal("0.06"), Decimal("0.24"))


def test_live_budget_counts_both_phases_and_rejects_a_thirteenth_operation():
    meter = budget()
    meter.preflight(model=MODEL, slots=6, requests=18)
    for _ in range(12):
        meter.before_operation()
    for _ in range(18):
        meter.before_inference(MODEL)
    assert meter.operations == 12
    assert meter.calls == 18
    assert meter.projected_usd == Decimal("0.03981312")
    with pytest.raises(ValueError, match="Sandbox operation ceiling"):
        meter.before_operation()
    with pytest.raises(ValueError, match="inference call ceiling"):
        meter.before_inference(MODEL)


def test_live_budget_preflight_fails_closed_on_shape_or_rate():
    meter = budget()
    with pytest.raises(ValueError, match="shape"):
        meter.preflight(model=MODEL, slots=6, requests=12)
    meter.input_usd_per_million = Decimal("1")
    with pytest.raises(ValueError, match="spend"):
        meter.preflight(model=MODEL, slots=6, requests=18)
    assert meter.operations == meter.calls == 0


def test_gateway_budget_rejects_before_provider_request():
    class FakeHTTP:
        calls = 0

        async def post(self, *_args, **_kwargs):
            self.calls += 1
            raise AssertionError("provider must not be reached")

    meter = budget()
    meter.preflight(model=MODEL, slots=6, requests=18)
    meter.calls = 18
    http = FakeHTTP()
    gateway = ServiceInferenceGateway("test-token", InferencePolicy(
        run_id="r", operation_id="o", model=MODEL,
        allowed_tool_names=("public_record_lookup",),
    ), http=http, live_budget=meter)
    with pytest.raises(GatewayRejected, match="LIVE_COMPARISON_BUDGET_EXHAUSTED"):
        asyncio.run(gateway.infer("o", {"request_ordinal": 1, "input_text": "choose"}))
    assert http.calls == 0
