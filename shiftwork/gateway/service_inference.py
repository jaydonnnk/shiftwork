"""One bounded Nemotron call, owned by the controller and bound to a Sandbox operation.

The Sandbox receives no provider credential. An operation event is only a request
for this gateway to act; the controller verifies its operation identity and frozen
policy before it can call the provider. Raw response bodies are retained for the
run, while public observations contain only allowlisted measurements and choices.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx
from pydantic import ValidationError

from shiftwork.gateway.protocol import InferencePolicy, InferenceRequest
from shiftwork.live_budget import LiveComparisonBudget

PROVIDER_URL = "https://api.tokenfactory.nebius.com/v1/chat/completions"


class GatewayRejected(Exception):
    """A policy or provider failure. Its code is safe for public projection."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class ServiceInferenceGateway:
    def __init__(self, token: str, policy: InferencePolicy, *, http: httpx.AsyncClient | None = None,
                 live_budget: LiveComparisonBudget | None = None):
        if not token or not policy.operation_id or not policy.run_id:
            raise ValueError("gateway credentials and run binding are required")
        if policy.max_calls != 1 or not 1 <= policy.request_ordinal <= 4 or not 0 < policy.max_output_tokens <= 1024:
            raise ValueError("unsupported service inference ceiling")
        if not policy.allowed_tool_names or len(set(policy.allowed_tool_names)) != len(policy.allowed_tool_names):
            raise ValueError("a frozen unique tool policy is required")
        self._token = token
        self.policy = policy
        self._http = http
        self._live_budget = live_budget
        self._calls = 0
        self._closed = False
        self._expires_at = time.monotonic() + policy.deadline_s
        self.observations: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    @property
    def call_count(self) -> int:
        """Controller-owned count, including calls whose provider request failed."""
        return self._calls

    def close(self) -> None:
        self._closed = True

    def _reject(self, code: str, raw: dict[str, Any] | None = None) -> None:
        self.observations.append(("INFERENCE_RESULT", {"source": "controller_verified", "failure": code}, raw or {}))
        raise GatewayRejected(code)

    async def infer(self, operation_id: str, request_payload: object) -> dict[str, Any]:
        if self._closed or operation_id != self.policy.operation_id:
            self._reject("RUN_CAPABILITY_INVALID")
        if time.monotonic() >= self._expires_at:
            self._reject("RUN_CAPABILITY_EXPIRED")
        try:
            request = InferenceRequest.model_validate(request_payload)
        except ValidationError:
            self._reject("INFERENCE_REQUEST_INVALID")
        if request.request_ordinal != self.policy.request_ordinal:
            self._reject("REQUEST_ORDINAL_OUTSIDE_FROZEN_WORKLOAD")
        raw_input = request.input_text.encode("utf-8")
        if len(raw_input) > self.policy.max_input_bytes:
            self._reject("GATEWAY_INPUT_LIMIT")
        if self._calls >= self.policy.max_calls:
            self._reject("GATEWAY_CALL_LIMIT")
        if self._live_budget is not None:
            try:
                self._live_budget.before_inference(self.policy.model)
            except ValueError:
                self._reject("LIVE_COMPARISON_BUDGET_EXHAUSTED")
        self._calls += 1  # A provider failure still consumes the one call.
        self.observations.append((
            "INFERENCE_REQUEST",
            {"source": "controller_verified", "request_ordinal": request.request_ordinal,
             "model": self.policy.model, "input_bytes": len(raw_input),
             "input_sha256": hashlib.sha256(raw_input).hexdigest(),
             "allowed_tool_names": list(self.policy.allowed_tool_names)},
            {"input_text": request.input_text},
        ))
        provider_request = {
            "model": self.policy.model,
            "messages": [{"role": "user", "content": request.input_text}],
            "temperature": 0,
            "max_tokens": self.policy.max_output_tokens,
        }
        started = time.monotonic()
        try:
            if self._http is None:
                async with httpx.AsyncClient(timeout=self.policy.deadline_s) as http:
                    response = await http.post(PROVIDER_URL, headers={"Authorization": "Bearer " + self._token}, json=provider_request)
            else:
                response = await self._http.post(PROVIDER_URL, headers={"Authorization": "Bearer " + self._token}, json=provider_request)
        except (httpx.TimeoutException, httpx.RequestError):
            self._reject("PROVIDER_TRANSPORT_FAILED", {"provider_request": provider_request})
        elapsed_ms = round((time.monotonic() - started) * 1000)
        if response.status_code != 200:
            self._reject("PROVIDER_HTTP_FAILED", {"http_status": response.status_code, "body": response.text[:65536]})
        if len(response.content) > 262144:
            self._reject("PROVIDER_RESPONSE_LIMIT")
        try:
            body = response.json()
            choice = body["choices"][0]
            content = choice["message"].get("content") or ""
            usage = body.get("usage") or {}
            finish_reason = choice.get("finish_reason")
        except (ValueError, TypeError, KeyError, IndexError):
            self._reject("PROVIDER_RESPONSE_INVALID", {"body": response.text[:65536]})
        selected_tool = content.strip()
        public = {
            "source": "controller_verified", "model": body.get("model"),
            "selected_tool": selected_tool if selected_tool in self.policy.allowed_tool_names else None,
            "finish_reason": finish_reason, "elapsed_ms": elapsed_ms,
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
        }
        self.observations.append(("INFERENCE_RESULT", public, {"provider_response": body}))
        if selected_tool not in self.policy.allowed_tool_names:
            raise GatewayRejected("MODEL_TOOL_NOT_ALLOWED")
        if isinstance(usage.get("completion_tokens"), int) and usage["completion_tokens"] > self.policy.max_output_tokens:
            raise GatewayRejected("GATEWAY_OUTPUT_LIMIT")
        return {"kind": "inference_reply", "selected_tool": selected_tool}
