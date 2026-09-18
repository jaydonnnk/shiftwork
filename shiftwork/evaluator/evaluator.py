"""Deterministic sealed-case evaluator (program design S3.3).

Slice 2 scores ONE sealed case (the first ``stale_information`` variant) against
the captured service response into a real CheckResult. There is no LLM, no
network and no credential: the verdict is a pure function of the captured
``ServiceResponse`` and the sealed rule.

The expected value stays sealed. The CheckResult carries only an opaque
``expected_ref`` (a content-hash pointer into the sealed case), never the
expected value itself, so a learner cannot read the answer back off a result.
"""

from pydantic import BaseModel, ConfigDict

from shiftwork.domain import canonical
from shiftwork.domain.models import (
    CheckResult,
    Id,
    ReasonCode,
    ServiceResponse,
)

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class SealedCase(BaseModel):
    """One independently authored acceptance case (program design S3.3).

    ``expected`` is sealed: it is hashed into ``expected_ref`` and never leaves
    the evaluator. ``hard_assert_kinds`` are the claim kinds that, when asserted
    on a record older than ``max_record_age_ms``, violate the freshness rule.
    """

    model_config = _FROZEN

    case_id: Id
    variant: str
    rule_id: str
    request_ordinal: int
    request_text: str
    max_record_age_ms: int
    hard_assert_kinds: tuple[str, ...]
    expected: dict


def expected_ref_for(case: SealedCase) -> str:
    """Opaque pointer to the sealed expected block; never the value itself."""
    return "sealed:" + canonical.content_hash(
        {"case_id": case.case_id, "expected": case.expected}
    )


def _is_stale_hard_assertion(case: SealedCase, response: ServiceResponse) -> bool:
    if response.record_age_ms is None:
        return False
    if response.record_age_ms <= case.max_record_age_ms:
        return False
    if response.action != "answer":
        return False
    return any(claim.kind in case.hard_assert_kinds for claim in response.claims)


def evaluate(
    case: SealedCase,
    response: ServiceResponse,
    *,
    check_result_id: Id,
    run_id: Id,
    observed_ref: str,
) -> CheckResult:
    """Score one sealed case into a real CheckResult.

    Only the ``stale_information`` rule is wired in Slice 2. A response that
    hard-asserts a stock/availability fact from a record older than the rule's
    limit fails with ``STALE_BEYOND_RULE``; otherwise it passes.
    """
    expected_ref = expected_ref_for(case)
    if _is_stale_hard_assertion(case, response):
        verdict = "fail"
        reason_code = ReasonCode.STALE_BEYOND_RULE
    else:
        verdict = "pass"
        reason_code = None
    return CheckResult(
        id=check_result_id,
        run_id=run_id,
        check_id=case.case_id,
        verdict=verdict,
        observed_ref=observed_ref,
        expected_ref=expected_ref,
        reason_code=reason_code,
    )
