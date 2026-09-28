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
from shiftwork.domain.task_contract import (
    FALLBACK_STATUSES,
    CustomerRequestSpec,
    MissionSpec,
    ProtectedStimulus,
    RequiredTask,
    ShopSnapshot,
    TaskAssessment,
    TaskKind,
    TaskOutcome,
    TaskResult,
    TaskStatus,
    fallback_outcome,
    resolve_collection_facts,
    resolve_record_group,
)
from shiftwork.domain.task_contract import FACTUAL_CLAIM_KINDS as TASK_FACTUAL_KINDS
from shiftwork.domain.task_contract import ServiceResponse as TaskServiceResponse

_FROZEN = ConfigDict(frozen=True, extra="forbid")

RULE_NEVER_INVENT = "invariant.never_invent_fact"
RULE_NEWEST_WITH_AGE = "freshness.use_newest_with_age"
RULE_HARD_CHECK_HIGH_RISK = "stance.hard_check_high_risk"
RULE_VERIFY_EXACT_NOW = "stance.verify_exact_now"

# Names the task-aware rule set a RunAssessment was produced under, so a rule
# change that alters an outcome invalidates comparability instead of silently
# relabelling stored evidence (Gate 3 S3.4).
RULE_VERSION = "task-contract.v1"

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
    stimulus: ProtectedStimulus | None = None


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


# ---------------------------------------------------------------------------
# Task-aware assessment (Gate 3 S3.3, Slice 11)
#
# A separate assessor for the pivot envelope. It does not touch the sealed-case
# path above: those cases are authored against the older action/claims envelope
# and ADR 0001 makes sealed material immutable. Like `evaluate`, everything here
# is pure and receives its inputs explicitly. No file, database, environment,
# network or model access.
#
# The rules implemented are the mission's own `public_rules` text, which the
# learner can read. Nothing here is a hidden grading rule.
# ---------------------------------------------------------------------------

#: Reason codes that make a mandatory rule fail. Their presence, not the
#: outcome label, decides `mandatory_pass`, so an optional task answered with an
#: unsupported claim still fails the invariant.
MANDATORY_FAILING_CODES: frozenset[ReasonCode] = frozenset(
    {
        ReasonCode.WRONG_ENTITY,
        ReasonCode.REQUIRED_TASK_MISSING,
        ReasonCode.UNSUPPORTED_CLAIM,
        ReasonCode.INVALID_COMMITMENT,
        ReasonCode.UNJUSTIFIED_REFUSAL,
        ReasonCode.UNJUSTIFIED_REFERRAL,
        ReasonCode.UNJUSTIFIED_CLARIFICATION,
        ReasonCode.MISSING_EXECUTION_EVIDENCE,
    }
)

_AVAILABILITY_KINDS = (TaskKind.CONFIRM_COLLECTION, TaskKind.SUGGEST_ALTERNATIVE)


def assess_request(
    *,
    spec: CustomerRequestSpec,
    request_ordinal: int,
    mission: MissionSpec,
    snapshot: ShopSnapshot,
    response: TaskServiceResponse | None,
) -> tuple[TaskAssessment, ...]:
    """Assess every task the frozen request declares, in declared order.

    ``response`` is None when the run produced no usable capture. Missing
    execution evidence is MISSING_OUTPUT for every task, never a refusal, a
    referral or a clarification: a timeout cannot become an answer the service
    did not give.
    """
    if response is None:
        return tuple(
            TaskAssessment(
                request_id=spec.id,
                request_ordinal=request_ordinal,
                task_id=task.id,
                outcome=TaskOutcome.MISSING_OUTPUT,
                mandatory_pass=False,
                reason_codes=(ReasonCode.MISSING_EXECUTION_EVIDENCE,),
            )
            for task in spec.tasks
        )

    results = {result.task_id: result for result in response.task_results}
    assessments = []
    for task in spec.tasks:
        result = results.get(task.id)
        if result is None:
            assessments.append(_assess_absent(spec, request_ordinal, task))
        else:
            assessments.append(
                _assess_task(
                    spec=spec,
                    request_ordinal=request_ordinal,
                    task=task,
                    result=result,
                    mission=mission,
                    snapshot=snapshot,
                )
            )
    return tuple(assessments)


def request_usefully_completed(
    spec: CustomerRequestSpec,
    assessments: Sequence[TaskAssessment],
) -> bool:
    """True only when every required task usefully completed and no mandatory rule failed.

    A justified fallback satisfies its mandatory rule but never counts here, and a
    supported optional answer cannot carry the request: the recorded starter
    returns a true price and still fails this check.
    """
    if any(assessment.mandatory_pass is False for assessment in assessments):
        return False
    outcomes = {assessment.task_id: assessment.outcome for assessment in assessments}
    return all(
        outcomes.get(task.id) is TaskOutcome.USEFUL_COMPLETION
        for task in spec.tasks
        if task.required
    )


def _assess_absent(
    spec: CustomerRequestSpec,
    request_ordinal: int,
    task: RequiredTask,
) -> TaskAssessment:
    """A required task with no result fails even when every supplied claim is true."""
    codes = (ReasonCode.REQUIRED_TASK_MISSING,) if task.required else ()
    return TaskAssessment(
        request_id=spec.id,
        request_ordinal=request_ordinal,
        task_id=task.id,
        outcome=TaskOutcome.MISSING_OUTPUT,
        mandatory_pass=not task.required,
        reason_codes=codes,
    )


def _assess_task(
    *,
    spec: CustomerRequestSpec,
    request_ordinal: int,
    task: RequiredTask,
    result: TaskResult,
    mission: MissionSpec,
    snapshot: ShopSnapshot,
) -> TaskAssessment:
    def build(outcome: TaskOutcome, codes: Sequence[ReasonCode]) -> TaskAssessment:
        return TaskAssessment(
            request_id=spec.id,
            request_ordinal=request_ordinal,
            task_id=task.id,
            outcome=outcome,
            mandatory_pass=not any(code in MANDATORY_FAILING_CODES for code in codes),
            reason_codes=tuple(dict.fromkeys(codes)),
        )

    if result.status is TaskStatus.NOT_APPLICABLE:
        return _assess_not_applicable(task, result, mission, snapshot, build)
    if result.status in FALLBACK_STATUSES:
        return _assess_fallback(task, result, mission, snapshot, build)
    return _assess_completed(task, result, mission, snapshot, build)


def _assess_not_applicable(task, result, mission, snapshot, build):
    """NOT_APPLICABLE is justified only for an independently inactive condition.

    A service declaring a task away is not evidence that the task was inactive.
    Gate 3's outcome vocabulary has no NOT_APPLICABLE member, so a justified
    inactive condition is recorded as JUSTIFIED_REFUSAL: a justified
    non-completion. This is a known vocabulary gap, recorded as an S11 limitation.
    """
    if task.kind is not TaskKind.SUGGEST_ALTERNATIVE or not _is_conditional(task):
        return build(
            TaskOutcome.INCORRECT_OUTPUT,
            (ReasonCode.REQUIRED_TASK_MISSING,) if task.required else (),
        )
    date = _collection_date(task)
    if date is None or not _collection_independently_confirmed(
        snapshot, mission, task.requested_entity_ref, date
    ):
        return build(
            TaskOutcome.INCORRECT_OUTPUT,
            (ReasonCode.REQUIRED_TASK_MISSING,) if task.required else (),
        )
    return build(TaskOutcome.JUSTIFIED_REFUSAL, ())


def _assess_fallback(task, result, mission, snapshot, build):
    justified_code, unjustified_outcome, unjustified_reason = fallback_outcome(result.status)
    explanation = mission.explanation_codes.get(result.explanation_code or "")
    if explanation is None or TaskStatus(explanation.status) is not result.status:
        return build(unjustified_outcome, (unjustified_reason,))
    if task.kind not in explanation.allowed_task_kinds:
        return build(unjustified_outcome, (unjustified_reason,))
    if not _fallback_condition_holds(task, explanation.code, mission, snapshot):
        return build(unjustified_outcome, (unjustified_reason,))
    return build(justified_code, ())


def _fallback_condition_holds(task, code, mission, snapshot) -> bool:
    """Independently check an explanation code's stated condition.

    The service's own label is never proof: each condition is re-derived from the
    frozen public state and the frozen request.
    """
    if code == "MISSING_ENTITY_DETAIL":
        return False
    if code == "MISSING_COLLECTION_DATE":
        return _collection_date(task) is None
    if code == "PUBLIC_DATA_UNAVAILABLE":
        return _necessary_data_unavailable(task, mission, snapshot)
    if code == "NO_MATCHING_ALTERNATIVE":
        return _no_matching_alternative_is_provable(task, mission, snapshot)
    return False


def _assess_completed(task, result, mission, snapshot, build):
    codes: list[ReasonCode] = []
    if result.commitment_ref is not None and task.kind in _AVAILABILITY_KINDS:
        codes.append(ReasonCode.INVALID_COMMITMENT)

    if task.kind is TaskKind.SUGGEST_ALTERNATIVE:
        codes.extend(_check_alternative(task, result, mission, snapshot))
    else:
        codes.extend(_check_same_entity(task, result))
        if task.kind is TaskKind.CONFIRM_COLLECTION:
            codes.extend(_check_collection(task, result, mission, snapshot))

    codes.extend(_check_claims_supported(result, mission, snapshot))

    if codes:
        return build(TaskOutcome.INCORRECT_OUTPUT, codes)
    return build(TaskOutcome.USEFUL_COMPLETION, ())


def _check_same_entity(task, result) -> list[ReasonCode]:
    """A hardback cannot answer a paperback question, however true its price is."""
    if result.entity_ref != task.requested_entity_ref:
        return [ReasonCode.WRONG_ENTITY]
    return [
        ReasonCode.WRONG_ENTITY
        for claim in result.claims
        if claim.entity_ref != task.requested_entity_ref
    ]


def _check_claims_supported(result, mission, snapshot) -> list[ReasonCode]:
    codes: list[ReasonCode] = []
    for claim in result.claims:
        if claim.kind not in TASK_FACTUAL_KINDS:
            continue
        if not claim.evidence_refs:
            codes.append(ReasonCode.UNSUPPORTED_CLAIM)
            continue
        if not _claim_is_supported(claim, mission, snapshot):
            codes.append(ReasonCode.UNSUPPORTED_CLAIM)
    return codes


def _claim_is_supported(claim, mission, snapshot) -> bool:
    """A claim is supported only by an agreed current record group.

    Citing the newest record of a conflicting group does not help: the group has
    no single value to support.
    """
    collection_date = None
    if claim.kind == "availability" and isinstance(claim.value, dict):
        value = claim.value.get("collection_date")
        collection_date = value if isinstance(value, str) else None
    group = resolve_record_group(
        snapshot,
        claim.entity_ref,
        claim.kind,
        max_record_age_ms=mission.max_record_age_ms,
        collection_date=collection_date,
    )
    if group.status != "AGREED":
        return False
    if group.value != claim.value:
        return False
    return all(ref in group.record_ids for ref in claim.evidence_refs)


def _check_collection(task, result, mission, snapshot) -> list[ReasonCode]:
    date = _collection_date(task)
    if date is None:
        return [ReasonCode.REQUIRED_TASK_MISSING]
    facts = resolve_collection_facts(
        snapshot, task.requested_entity_ref, date, max_record_age_ms=mission.max_record_age_ms
    )
    if facts.conflicting:
        # Contradictory necessary information cannot be answered either way; the
        # supported response is a referral, so a COMPLETED result is incorrect.
        return [ReasonCode.UNSUPPORTED_CLAIM]

    availability_claims = [
        claim
        for claim in result.claims
        if claim.kind == "availability"
        and isinstance(claim.value, dict)
        and claim.value.get("collection_date") == date
    ]
    if not availability_claims:
        return [ReasonCode.REQUIRED_TASK_MISSING]
    if any(claim.value.get("can_collect") is True for claim in availability_claims):
        stock = facts.stock
        quantity = stock.value
        if stock.status != "AGREED" or not isinstance(quantity, int) or quantity <= 0:
            return [ReasonCode.UNSUPPORTED_CLAIM]
        if not any(claim.kind == "stock" for claim in result.claims):
            return [ReasonCode.UNSUPPORTED_CLAIM]
    return []


def _check_alternative(task, result, mission, snapshot) -> list[ReasonCode]:
    condition = task.condition_json
    requested = task.requested_entity_ref
    proposed = result.entity_ref
    if condition.get("exclude_requested_entity") and proposed == requested:
        return [ReasonCode.WRONG_ENTITY]
    if proposed not in snapshot.entities or requested not in snapshot.entities:
        return [ReasonCode.WRONG_ENTITY]
    if condition.get("same_genre_as_requested_entity") and (
        snapshot.entities[proposed].genre != snapshot.entities[requested].genre
    ):
        return [ReasonCode.WRONG_ENTITY]

    limit = condition.get("price_less_than_minor_units")
    date = _collection_date(task)
    if not isinstance(limit, int) or date is None:
        return [ReasonCode.REQUIRED_TASK_MISSING]

    by_kind = {claim.kind: claim for claim in result.claims if claim.entity_ref == proposed}
    if set(by_kind) != {"price", "stock", "availability"}:
        return [ReasonCode.REQUIRED_TASK_MISSING]

    price = by_kind["price"]
    stock = by_kind["stock"]
    availability = by_kind["availability"]
    if not isinstance(price.value, int) or price.value >= limit:
        return [ReasonCode.UNSUPPORTED_CLAIM]
    if not isinstance(stock.value, int) or stock.value <= 0:
        return [ReasonCode.UNSUPPORTED_CLAIM]
    if not isinstance(availability.value, dict):
        return [ReasonCode.UNSUPPORTED_CLAIM]
    if availability.value.get("collection_date") != date:
        return [ReasonCode.WRONG_ENTITY]
    if availability.value.get("can_collect") is not True:
        return [ReasonCode.UNSUPPORTED_CLAIM]
    return []


def _is_conditional(task) -> bool:
    return task.condition_json.get("unless_collection_confirmed") is True


def _collection_date(task) -> str | None:
    date = task.condition_json.get("collection_date")
    return date if isinstance(date, str) else None


def _collection_independently_confirmed(snapshot, mission, entity_ref, date) -> bool:
    facts = resolve_collection_facts(
        snapshot, entity_ref, date, max_record_age_ms=mission.max_record_age_ms
    )
    if facts.conflicting or facts.availability.status != "AGREED":
        return False
    value = facts.availability.value
    if not isinstance(value, dict) or value.get("can_collect") is not True:
        return False
    if facts.stock.status != "AGREED":
        return False
    quantity = facts.stock.value
    return isinstance(quantity, int) and not isinstance(quantity, bool) and quantity > 0


def _necessary_data_unavailable(task, mission, snapshot) -> bool:
    """Whether information this task needs is missing, stale, unavailable or conflicting."""
    max_age = mission.max_record_age_ms
    if task.kind is TaskKind.ANSWER_FACT:
        kind = task.condition_json.get("claim_kind")
        if not isinstance(kind, str):
            return False
        return (
            resolve_record_group(snapshot, task.requested_entity_ref, kind, max_record_age_ms=max_age).status
            != "AGREED"
        )
    if task.kind is TaskKind.CONFIRM_COLLECTION:
        date = _collection_date(task)
        if date is None:
            return False
        facts = resolve_collection_facts(snapshot, task.requested_entity_ref, date, max_record_age_ms=max_age)
        return facts.conflicting or facts.availability.status != "AGREED"
    if task.kind is TaskKind.SUGGEST_ALTERNATIVE:
        return _alternative_has_unresolvable_candidate(task, mission, snapshot)
    return False


def _candidate_classifications(task, mission, snapshot):
    date = _collection_date(task)
    limit = task.condition_json.get("price_less_than_minor_units")
    currency = task.condition_json.get("currency")
    requested = task.requested_entity_ref
    if date is None or not isinstance(limit, int) or requested not in snapshot.entities:
        return {}
    wanted_genre = snapshot.entities[requested].genre
    classified: dict[str, str] = {}
    for entity_ref, entity in snapshot.entities.items():
        if entity_ref == requested:
            continue
        if entity.genre != wanted_genre:
            classified[entity_ref] = "DISQUALIFIED"
            continue
        classified[entity_ref] = _classify_candidate(
            snapshot, mission, entity_ref, date, limit, currency
        )
    return classified


def _classify_candidate(snapshot, mission, entity_ref, date, limit, currency) -> str:
    max_age = mission.max_record_age_ms
    price = resolve_record_group(snapshot, entity_ref, "price", max_record_age_ms=max_age)
    stock = resolve_record_group(snapshot, entity_ref, "stock", max_record_age_ms=max_age)
    availability = resolve_record_group(
        snapshot, entity_ref, "availability", max_record_age_ms=max_age, collection_date=date
    )
    if "NO_CURRENT_RECORD" in (price.status, stock.status, availability.status):
        return "UNKNOWN"
    if "CONFLICT" in (price.status, stock.status, availability.status):
        return "UNKNOWN"
    record = next(
        (item for item in snapshot.records if item.entity_ref == entity_ref and item.kind == "price"),
        None,
    )
    if currency is not None and record is not None and record.currency != currency:
        return "DISQUALIFIED"
    value = availability.value
    quantity = stock.value
    if (
        isinstance(value, dict)
        and value.get("can_collect") is True
        and isinstance(price.value, int)
        and price.value < limit
        and isinstance(quantity, int)
        and not isinstance(quantity, bool)
        and quantity > 0
    ):
        return "QUALIFIES"
    return "DISQUALIFIED"


def _alternative_has_unresolvable_candidate(task, mission, snapshot) -> bool:
    """Referral is justified only when no alternative is confirmed and a possibly
    qualifying candidate cannot be ruled in or out.

    A different candidate's data problem cannot justify referral when an
    independently confirmed qualifying alternative exists.
    """
    classifications = _candidate_classifications(task, mission, snapshot)
    if not classifications:
        return False
    if "QUALIFIES" in classifications.values():
        return False
    return "UNKNOWN" in classifications.values()


def _no_matching_alternative_is_provable(task, mission, snapshot) -> bool:
    """Refusal needs a complete, consistent catalog with no qualifying candidate."""
    classifications = _candidate_classifications(task, mission, snapshot)
    if not classifications:
        return False
    return all(value == "DISQUALIFIED" for value in classifications.values())
