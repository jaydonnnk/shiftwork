"""Contract-parameterized sealed-case evaluator (program design S3.4).

Slice 4 generalizes the Slice 2 single hardcoded case into the full first
family: the ``stale_information`` inventory (six independently authored
variants) loads as a ``SealedCaseSet`` and is scored by a pure ``evaluate`` that
receives every input explicitly. There is no LLM, no network and no file or
database access inside this module (program design S6 test 11).

Rules are keyed by the committed catalog option's ``evaluator_rule_id`` mirror,
so a case is judged against the stance the learner actually committed to, not a
hidden correct stance (test 14). Every constant a rule uses is stated in the
committed option's learner-visible label (bookshop catalog v2); sealed cases
supply scenario data only, never rule parameters:

- ``invariant.never_invent_fact`` (from a MUST_NEVER option): every factual
  claim must be supported by a cited record; a factual claim with no evidence is
  MISSING_EVIDENCE, and a claim supported by nothing or only by a superseded
  record is INVENTED_FACT. Fixed invariant: independent of the chosen stance.
- ``freshness.use_newest_with_age``: a hard answer asserting a stock, price or
  availability claim from a record older than the one-hour limit fails with
  STALE_BEYOND_RULE. The v2 label states the limit.
- ``stance.hard_check_high_risk``: the same staleness failure, but only for
  price claims, the high-risk kind named in the v2 label; stock and
  availability are answered from the newest cached record whatever its age.
- ``stance.verify_exact_now``: no extra evaluator rule. Its v2 label states no
  refusal threshold, so citing the newest record with its true age is a
  legitimate permissive tradeoff; the invariant still bounds it.

Expectations stay sealed: a CheckResult carries only an opaque ``expected_ref``.
"""

from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from shiftwork.domain import canonical
from shiftwork.domain.customer_answer import (
    FACTUAL_CLAIM_KINDS,
    ValidatedServiceResponse,
    validate_service_response,
)
from shiftwork.domain.errors import ServiceResponseInvalid
from shiftwork.domain.models import (
    CheckResult,
    ContractOptionId,
    ContractParams,
    Id,
    JsonValue,
    ReasonCode,
    RunOutput,
    ServiceResponse,
)

_FROZEN = ConfigDict(frozen=True, extra="forbid")

RULE_NEVER_INVENT = "invariant.never_invent_fact"
RULE_NEWEST_WITH_AGE = "freshness.use_newest_with_age"
RULE_HARD_CHECK_HIGH_RISK = "stance.hard_check_high_risk"
RULE_VERIFY_EXACT_NOW = "stance.verify_exact_now"

# Fixed semantics of the committed options, mirrored from the bookshop catalog
# v2 learner labels ("records older than one hour", "high-risk claims (price)").
# tests/evaluator pins these constants against the v2 label text, so a label
# change that redefines a rule fails loudly. Only v1's labels are frozen
# history without the constants; new committed contracts use v2.
FRESHNESS_LIMIT_MS = 3_600_000
HIGH_RISK_KINDS = ("price",)

# Mirror of the catalog evaluator_rule_id bindings for the options this
# evaluator implements (identical across bookshop v1 and v2). tests/evaluator
# asserts this mirror against both catalog files, so a catalog correction that
# rebinds an option fails loudly instead of silently changing evaluation
# behavior.
_RULE_BY_OPTION: Mapping[ContractOptionId, str] = {
    ContractOptionId.NEVER_INVENT_PRICE_STOCK_POLICY: RULE_NEVER_INVENT,
    ContractOptionId.USE_NEWEST_RECORD_WITH_AGE: RULE_NEWEST_WITH_AGE,
    ContractOptionId.HARD_CHECK_HIGH_RISK_ONLY: RULE_HARD_CHECK_HIGH_RISK,
    ContractOptionId.VERIFY_EXACT_CLAIMS_NOW: RULE_VERIFY_EXACT_NOW,
}


class SealedCase(BaseModel):
    """One independently authored acceptance case (program design S3.4).

    ``expected`` is sealed: it carries scenario data (record ids, superseded
    refs, the scenario's expected claim, an operator note) and is hashed into
    ``expected_ref`` so it never leaves the evaluator as a renderable value. It
    deliberately carries no rule parameters: thresholds and claim-kind
    classifications live in the committed option's learner-visible label, so a
    case cannot change a verdict by hidden data (test 14).
    """

    model_config = _FROZEN

    id: Id
    schema_version: Literal[1]
    family: str
    check_id: Id
    request_ordinals: tuple[int, ...]
    expected: dict[str, JsonValue]


class SealedCaseSet(BaseModel):
    """The sealed cases available to one run; loaded controller-side only."""

    model_config = _FROZEN

    cases: tuple[SealedCase, ...]


def expected_ref_for(case: SealedCase) -> str:
    """Opaque pointer to the sealed expected block; never the value itself."""
    return "sealed:" + canonical.content_hash(
        {"case_id": case.id, "expected": case.expected}
    )


def committed_rule_ids(contract: ContractParams) -> frozenset[str]:
    """The evaluator rule ids implied by a committed contract.

    Options whose rules this slice does not implement yet (the clarify,
    escalate and estimate bindings) contribute no evaluator rule; family rules
    that do not apply to the drawn case's kinds also cannot fire.
    """
    committed = set(contract.must_never) | set(contract.selections.values())
    return frozenset(_RULE_BY_OPTION[option] for option in committed if option in _RULE_BY_OPTION)


def evaluate(
    outputs: Sequence[RunOutput],
    sealed_cases: SealedCaseSet,
    contract: ContractParams,
    public_records: dict[str, JsonValue],
) -> list[CheckResult]:
    """Score every sealed case that has a scorable captured output.

    Pure function: every input is passed in, nothing is read or written.
    A case whose request ordinals have no executed output is not scored because
    its stimuli were not part of this run's batch. Captures with a transport
    failure are not scored here either: a run that failed at the executor level
    never reaches finalization (program design S5.4).
    """
    rules = committed_rule_ids(contract)
    results: list[CheckResult] = []
    for case in sealed_cases.cases:
        for output in sorted(outputs, key=lambda item: item.request_ordinal):
            if output.request_ordinal not in case.request_ordinals:
                continue
            if output.transport_error is not None:
                continue
            results.append(_score_case(case, output, rules, public_records))
    return results


def _score_case(
    case: SealedCase,
    output: RunOutput,
    rules: frozenset[str],
    public_records: dict[str, JsonValue],
) -> CheckResult:
    verdict, reason_code = _score(case, output.body, rules, public_records)
    return CheckResult(
        id=f"cr-{case.check_id}-{output.request_ordinal}",
        run_id=output.run_id,
        check_id=case.check_id,
        verdict=verdict,
        observed_ref=output.id,
        expected_ref=expected_ref_for(case),
        reason_code=reason_code,
    )


def _score(
    case: SealedCase,
    body: bytes,
    rules: frozenset[str],
    public_records: dict[str, JsonValue],
) -> tuple[Literal["pass", "fail"], ReasonCode | None]:
    try:
        response = ServiceResponse.model_validate_json(body)
    except ValidationError:
        return ("fail", ReasonCode.MALFORMED_RESPONSE)
    try:
        validated = validate_service_response(response, public_records)
    except ServiceResponseInvalid:
        return ("fail", ReasonCode.MALFORMED_RESPONSE)
    violation = _first_violation(case, validated, rules, public_records)
    if violation is not None:
        return ("fail", violation)
    return ("pass", None)


def _first_violation(
    case: SealedCase,
    response: ValidatedServiceResponse,
    rules: frozenset[str],
    public_records: dict[str, JsonValue],
) -> ReasonCode | None:
    """The first rule violation in deterministic priority order."""
    superseded = _string_list(case.expected.get("superseded_refs"))
    if RULE_NEVER_INVENT in rules:
        violation = _invariant_violation(response, superseded, public_records)
        if violation is not None:
            return violation
    if RULE_NEWEST_WITH_AGE in rules and _is_stale_hard_assert(response, FACTUAL_CLAIM_KINDS):
        return ReasonCode.STALE_BEYOND_RULE
    if RULE_HARD_CHECK_HIGH_RISK in rules and _is_stale_hard_assert(response, HIGH_RISK_KINDS):
        return ReasonCode.STALE_BEYOND_RULE
    return None


def _invariant_violation(
    response: ValidatedServiceResponse,
    superseded_refs: tuple[str, ...],
    public_records: dict[str, JsonValue],
) -> ReasonCode | None:
    for claim in response.claims:
        if claim.kind not in FACTUAL_CLAIM_KINDS:
            continue
        if not response.evidence_refs:
            return ReasonCode.MISSING_EVIDENCE
        supported = False
        for ref in response.evidence_refs:
            if ref in superseded_refs:
                continue
            record = public_records.get(ref)
            if (
                isinstance(record, dict)
                and record.get("kind") == claim.kind
                and record.get("value") == claim.value
            ):
                supported = True
                break
        if not supported:
            return ReasonCode.INVENTED_FACT
    return None


def _is_stale_hard_assert(
    response: ValidatedServiceResponse,
    kinds: tuple[str, ...],
) -> bool:
    """A hard answer asserting one of ``kinds`` from a record past the limit.

    ``kinds`` is a fixed rule input (all factual kinds for
    ``freshness.use_newest_with_age``, ``HIGH_RISK_KINDS`` for
    ``stance.hard_check_high_risk``), never read from the sealed case.
    Strictly greater than the limit fails; the boundary itself passes.
    """
    if response.action != "answer" or response.verified_record_age_ms is None:
        return False
    if response.verified_record_age_ms <= FRESHNESS_LIMIT_MS:
        return False
    return any(claim.kind in kinds for claim in response.claims)


def _string_list(value: JsonValue) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))
