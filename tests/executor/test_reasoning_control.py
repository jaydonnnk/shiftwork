"""Approved S45 reasoning control. All provider replies here are authored doubles."""
import asyncio
from types import SimpleNamespace

import pytest

from shiftwork.executor import tokenfactory
from shiftwork.gateway.protocol import InferencePolicy
from shiftwork.gateway.service_inference import GatewayRejected, ServiceInferenceGateway
from tests.executor.test_task_plan_gateway import FakeHTTP, plan_json
from tests.executor.test_gateway_isolation import MultiRequestSandbox, _two_request_batch

MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
PLAN = plan_json(("collection", "public_record_lookup"))


def gateway(*, permission=True, model=MODEL, http=None):
    base = InferencePolicy(run_id="run", operation_id="operation", model=model,
        allowed_tool_names=("public_record_lookup",), task_vocabulary=("collection",))
    policy = SimpleNamespace(**{**vars(base), "allow_reasoning_off": permission})
    return ServiceInferenceGateway("test-only-token", policy, http=http or FakeHTTP(PLAN))


def request(bound, **extra):
    try:
        return asyncio.run(bound.infer("operation", {
            "request_ordinal": 1, "input_text": "public request", **extra}))
    except GatewayRejected as error:
        return {"error": error.code}


def test_strict_false_adds_only_the_approved_provider_flag_and_observation():
    http = FakeHTTP(PLAN)
    bound = gateway(http=http)
    reply = request(bound, enable_thinking=False)
    assert reply.get("plan_failure") is None and reply.get("plan") == [
        {"task_type": "collection", "tool_name": "public_record_lookup"}], "approved false must return the provider plan"
    assert http.calls == [{"model": MODEL, "messages": [{"role": "user", "content": "public request"}],
        "temperature": 0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": False}}], "only the admitted flag may change the provider body"
    assert bound.observations[0][1].get("enable_thinking") is False, "the controller must retain the requested false setting"
    assert request(bound, enable_thinking=False) == {"error": "GATEWAY_CALL_LIMIT"}
    assert len(http.calls) == 1, "reasoning control cannot create a second call"


def test_omission_keeps_the_original_provider_body():
    http = FakeHTTP(PLAN)
    bound = gateway(http=http, permission=False)
    assert request(bound).get("plan_failure") is None
    assert http.calls == [{"model": MODEL, "messages": [{"role": "user", "content": "public request"}],
        "temperature": 0, "max_tokens": 1024}], "omission must preserve the original wire body"
    assert "enable_thinking" not in bound.observations[0][1]


@pytest.mark.parametrize("value", [True, None, 0, 1, "false", {}, []], ids=["true", "null", "zero", "one", "string", "object", "array"])
def test_only_a_strict_false_value_is_admitted(value):
    http = FakeHTTP(PLAN)
    assert request(gateway(http=http), enable_thinking=value) == {"error": "INFERENCE_REQUEST_INVALID"}, "non-false values must be refused before provider access"
    assert http.calls == []


@pytest.mark.parametrize("permission,model", [(False, MODEL), (1, MODEL), (True, "other-model")], ids=["permission", "nonboolean-permission", "model"])
def test_reasoning_off_needs_frozen_permission_and_the_exact_model(permission, model):
    http = FakeHTTP(PLAN)
    assert request(gateway(permission=permission, model=model, http=http), enable_thinking=False) == {
        "error": "REASONING_OFF_NOT_ALLOWED"}, "reasoning-off needs the exact frozen permission and model"
    assert http.calls == []


@pytest.mark.parametrize("extra", [{"chat_template_kwargs": {"enable_thinking": False}}, {"extra_body": {}}, {"system": "x"}, {"max_tokens": 2048}])
def test_reasoning_control_never_opens_an_arbitrary_provider_dictionary(extra):
    http = FakeHTTP(PLAN)
    assert request(gateway(http=http), enable_thinking=False, **extra) == {"error": "INFERENCE_REQUEST_INVALID"}
    assert http.calls == []


def test_permission_reaches_every_gateway_in_a_multi_request_operation(tmp_path, monkeypatch):
    policies = []
    class RecordingGateway:
        def __init__(self, token, policy):
            policies.append(policy)
            self.policy = policy
            self.call_count, self.observations = 0, []
        def close(self):
            pass
    monkeypatch.setattr(tokenfactory, "ServiceInferenceGateway", RecordingGateway)
    frozen, _, _, captures = _two_request_batch(tmp_path)
    adapter = tokenfactory.TokenFactoryAdapter(run_id="run", allowed_tool_names=("public_record_lookup",),
        token="test-only-token", project="test-only-project", model=MODEL, client=MultiRequestSandbox(captures))
    adapter.allow_reasoning_off = True
    result = asyncio.run(adapter.execute(frozen))
    assert result.failure is None
    assert getattr(policies[0], "allow_reasoning_off", False) is True, "the first gateway must receive the frozen permission"
    assert getattr(policies[1], "allow_reasoning_off", False) is True, "the next gateway must receive the frozen permission"
