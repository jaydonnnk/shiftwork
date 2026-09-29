"""One comparison's controller-owned live ceiling, separate from candidate metrics."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class LiveComparisonBudget:
    model: str
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    max_operations: int = 12
    max_calls: int = 18
    max_projected_usd: Decimal = Decimal("0.10")
    reserved_input_tokens_per_call: int = 32768
    reserved_output_tokens_per_call: int = 1024
    operations: int = 0
    calls: int = 0

    @property
    def projected_usd(self) -> Decimal:
        per_call = (self.input_usd_per_million * self.reserved_input_tokens_per_call
                    + self.output_usd_per_million * self.reserved_output_tokens_per_call) / 1_000_000
        return per_call * self.calls

    def preflight(self, *, model: str, slots: int, requests: int) -> None:
        if (model != self.model or slots != 6 or requests != 18
                or self.max_operations != 12 or self.max_calls != 18
                or self.input_usd_per_million < 0 or self.output_usd_per_million < 0
                or self.reserved_input_tokens_per_call < 8192
                or self.reserved_output_tokens_per_call < 1024):
            raise ValueError("live comparison shape, model or rate ceiling is unverified")
        if (self.input_usd_per_million * self.reserved_input_tokens_per_call
                + self.output_usd_per_million * self.reserved_output_tokens_per_call
                ) * self.max_calls / 1_000_000 > self.max_projected_usd:
            raise ValueError("live comparison projected inference spend exceeds $0.10")

    def before_operation(self) -> None:
        if self.operations >= self.max_operations:
            raise ValueError("live comparison Sandbox operation ceiling reached")
        self.operations += 1  # Count a failed spawn attempt; never refund it.

    def before_inference(self, model: str) -> None:
        if model != self.model or self.calls >= self.max_calls:
            raise ValueError("live comparison inference call ceiling reached")
        self.calls += 1  # Count a failed provider request; never refund it.
        if self.projected_usd > self.max_projected_usd:
            raise ValueError("live comparison projected inference spend ceiling reached")
