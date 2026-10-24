"""Exact request and policy types for one run-bound service inference call."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Gate 3 section 7: gateway output per call, a fixed product ceiling shared by the
# provider request and the local guard. The frozen diagnostic context records this
# same constant, so the recorded settings and the executed request cannot drift.
GATEWAY_MAX_OUTPUT_TOKENS = 1024
REASONING_OFF_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"


class InferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_ordinal: int = Field(ge=1, le=4)
    input_text: str
    enable_thinking: Literal[False] | None = None

    @field_validator("enable_thinking", mode="before")
    @classmethod
    def strict_reasoning_off(cls, value):
        if value is not False:
            raise ValueError("enable_thinking must be omitted or strict false")
        return value


class TaskPlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    task_type: str
    tool_name: str


class TaskPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    plan: tuple[TaskPlanStep, ...] = Field(min_length=1)


@dataclass(frozen=True)
class InferencePolicy:
    run_id: str
    operation_id: str
    model: str
    allowed_tool_names: tuple[str, ...]
    request_ordinal: int = 1
    # Gate 3 section 3.5 (S43): a non-empty frozen task vocabulary selects plan
    # mode; empty keeps the historical single-tool-name reply.
    task_vocabulary: tuple[str, ...] = ()
    max_calls: int = 1
    max_input_bytes: int = 8192
    max_output_tokens: int = GATEWAY_MAX_OUTPUT_TOKENS
    deadline_s: int = 20
    allow_reasoning_off: bool = False
