"""One comparison's or one selected operation's controller-owned live ceiling.

Both meters are separate from candidate metrics and count failed attempts.
"""

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

    def preflight(self, *, model: str, slots: int, requests: int,
                  public_repetitions: int = 1,
                  requests_per_slot: tuple[int, ...] = (2, 2, 2, 2, 2, 2)) -> None:
        if (model != self.model or slots != 6 or type(public_repetitions) is not int
                or not 1 <= public_repetitions <= 3 or len(requests_per_slot) != slots
                or any(type(count) is not int or not 1 <= count <= 4 for count in requests_per_slot)
                or requests != sum(count * public_repetitions + 1 for count in requests_per_slot)
                or self.operations or self.calls
                or self.max_operations < slots * (public_repetitions + 1) or self.max_calls < requests
                or self.input_usd_per_million < 0 or self.output_usd_per_million < 0
                or self.reserved_input_tokens_per_call < 8192
                or self.reserved_output_tokens_per_call < 1024):
            raise ValueError("live comparison shape, model or rate ceiling is unverified")
        if (self.input_usd_per_million * self.reserved_input_tokens_per_call
                + self.output_usd_per_million * self.reserved_output_tokens_per_call
                ) * requests / 1_000_000 > self.max_projected_usd:
            raise ValueError("live comparison projected inference spend exceeds its ceiling")
        self.max_operations = slots * (public_repetitions + 1)
        self.max_calls = requests

    def before_operation(self) -> None:
        if self.operations >= self.max_operations:
            raise ValueError("live comparison Sandbox operation ceiling reached")
        self.operations += 1  # Count a failed spawn attempt; never refund it.

    def before_inference(self, model: str) -> None:
        if model != self.model or self.calls >= self.max_calls:
            raise ValueError("live comparison inference call ceiling reached")
        next_projection = self.projected_usd + (
            self.input_usd_per_million * self.reserved_input_tokens_per_call
            + self.output_usd_per_million * self.reserved_output_tokens_per_call) / 1_000_000
        if next_projection > self.max_projected_usd:
            raise ValueError("live comparison projected inference spend ceiling reached")
        self.calls += 1  # Count a failed provider request; never refund it.


@dataclass
class LiveOperationBudget:
    """One selected operation's controller-owned live ceiling.

    The selected operation runs exactly one frozen Sandbox operation over its
    one-request operational workload, so the ceilings are one spawn and one
    inference call. The class is deliberately separate from
    :class:`LiveComparisonBudget`: neither meter can satisfy the other's frozen
    shape preflight, so a comparison ceiling can never silently cover an
    operation or the reverse.
    """

    model: str
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    max_operations: int = 1
    max_calls: int = 1
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

    def preflight(self, *, model: str, requests: int) -> None:
        if (model != self.model or requests != 1
                or self.max_operations != 1 or self.max_calls != 1
                or self.input_usd_per_million < 0 or self.output_usd_per_million < 0
                or self.reserved_input_tokens_per_call < 8192
                or self.reserved_output_tokens_per_call < 1024):
            raise ValueError("live operation shape, model or rate ceiling is unverified")
        if (self.input_usd_per_million * self.reserved_input_tokens_per_call
                + self.output_usd_per_million * self.reserved_output_tokens_per_call
                ) * self.max_calls / 1_000_000 > self.max_projected_usd:
            raise ValueError("live operation projected inference spend exceeds $0.10")

    def before_operation(self) -> None:
        if self.operations >= self.max_operations:
            raise ValueError("live operation Sandbox operation ceiling reached")
        self.operations += 1  # Count a failed spawn attempt; never refund it.

    def before_inference(self, model: str) -> None:
        if model != self.model or self.calls >= self.max_calls:
            raise ValueError("live operation inference call ceiling reached")
        self.calls += 1  # Count a failed provider request; never refund it.
        if self.projected_usd > self.max_projected_usd:
            raise ValueError("live operation projected inference spend ceiling reached")


@dataclass
class LiveDiagnosticBudget(LiveOperationBudget):
    """One frozen public batch. Failed attempts are charged and never retried."""

    max_operations: int = 10
    max_calls: int = 40

    def preflight(self, *, model: str, repetitions: int, requests: int) -> None:
        if (model != self.model or type(repetitions) is not int
                or not 1 <= repetitions <= 10 or not 1 <= requests <= 4
                or self.operations or self.calls
                or repetitions > self.max_operations
                or repetitions * requests > self.max_calls
                or self.input_usd_per_million < 0 or self.output_usd_per_million < 0
                or self.reserved_input_tokens_per_call < 8192
                or self.reserved_output_tokens_per_call < 1024):
            raise ValueError("live diagnostic shape, model or rates are unverified")
        if self._cost(repetitions * requests) > self.max_projected_usd:
            raise ValueError("live diagnostic projected inference spend ceiling reached")
        self.max_operations = repetitions
        self.max_calls = repetitions * requests

    def _cost(self, calls: int) -> Decimal:
        return calls * (self.input_usd_per_million * self.reserved_input_tokens_per_call
                        + self.output_usd_per_million * self.reserved_output_tokens_per_call) / 1_000_000

    def before_inference(self, model: str) -> None:
        if model != self.model or self.calls >= self.max_calls:
            raise ValueError("live diagnostic inference call ceiling reached")
        if self._cost(self.calls + 1) > self.max_projected_usd:
            raise ValueError("live diagnostic projected inference spend ceiling reached")
        self.calls += 1


LiveInferenceMeter = LiveComparisonBudget | LiveOperationBudget | LiveDiagnosticBudget
