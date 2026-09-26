"""Deterministic customer-text rendering from validated structured responses (S3.2).

The learner service returns structured fields only. Every field is untrusted:
this module resolves evidence refs against the frozen public records, recomputes
the record age from the cited records and raises ``ServiceResponseInvalid``
before any customer-facing sentence exists. ``render_customer_text`` is a pure
function of the validated structure, so no separately authored text can
contradict the scored claims (program design S6 test 42).
"""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict

from shiftwork.domain.errors import ServiceResponseInvalid
from shiftwork.domain.models import Claim, JsonValue, ServiceResponse
from shiftwork.domain.task_contract import (
    CustomerRequestSpec,
    MissionSpec,
    ShopEntity,
    ShopSnapshot,
    TaskResult,
    TaskStatus,
)
from shiftwork.domain.task_contract import Claim as TaskClaim
from shiftwork.domain.task_contract import ServiceResponse as TaskServiceResponse

_FROZEN = ConfigDict(frozen=True, extra="forbid")

FACTUAL_CLAIM_KINDS = ("stock", "price", "availability")

_ACTION_TEXT = {
    "ask": "Ask: I need more information from you before I can answer.",
    "decline": "Decline: I cannot answer that from the shop records.",
    "escalate": "Escalate: a person from the shop should handle this request.",
}


class ValidatedServiceResponse(BaseModel):
    """A structured response whose refs resolved and whose age was recomputed."""

    model_config = _FROZEN

    action: Literal["answer", "ask", "decline", "escalate"]
    claims: tuple[Claim, ...]
    evidence_refs: tuple[str, ...]
    verified_record_age_ms: int | None


def validate_service_response(
    response: ServiceResponse,
    public_records: dict[str, JsonValue],
) -> ValidatedServiceResponse:
    """Resolve every cited record and recompute the asserted age.

    Raises ``ServiceResponseInvalid`` when a ref resolves to no record, when an
    age is attested with no evidence, when evidence is cited with no age
    attestation, or when the attested age does not equal the newest cited
    record's age. A claim value contradicted by the cited records is not a
    validation error; the evaluator reports it as INVENTED_FACT or
    MISSING_EVIDENCE (evaluator/evaluator.py).
    """
    resolved: list[dict] = []
    for ref in response.evidence_refs:
        record = public_records.get(ref)
        if not isinstance(record, dict):
            raise ServiceResponseInvalid(f"evidence ref {ref!r} resolves to no public record")
        resolved.append(record)

    if resolved:
        if response.record_age_ms is None:
            raise ServiceResponseInvalid("a cited record requires a record_age_ms attestation")
        ages: list[int] = []
        for record in resolved:
            age = record.get("record_age_ms")
            if isinstance(age, bool) or not isinstance(age, int) or age < 0:
                raise ServiceResponseInvalid("a cited record carries no valid record_age_ms")
            ages.append(age)
        verified_age = min(ages)
        if response.record_age_ms != verified_age:
            raise ServiceResponseInvalid(
                f"attested record_age_ms {response.record_age_ms} does not match the newest "
                f"cited record ({verified_age} ms)"
            )
    else:
        if response.record_age_ms is not None:
            raise ServiceResponseInvalid("a record age was attested with no evidence")
        verified_age = None

    return ValidatedServiceResponse(
        action=response.action,
        claims=response.claims,
        evidence_refs=response.evidence_refs,
        verified_record_age_ms=verified_age,
    )


def render_customer_text(response: ValidatedServiceResponse) -> str:
    """Render the displayed sentence from the validated structure alone."""
    if response.action != "answer":
        return _ACTION_TEXT[response.action]
    claims = "; ".join(
        f"{claim.kind} = {_render_value(claim.value)}" for claim in response.claims
    )
    text = f"Answer: {claims or 'no claims are asserted'}"
    if response.verified_record_age_ms is not None:
        text += f" (record age {response.verified_record_age_ms} ms)"
    return text + "."


def _render_value(value: JsonValue) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Task-aware rendering (Gate 3 S3.3, Slice 11)
#
# A second renderer for the pivot envelope, beside the sealed path's above. Gate 3
# names both ``render_customer_text``; one module cannot export that name twice,
# so the task-aware one is ``render_task_customer_text``. It also takes the mission
# and the frozen public state rather than a bare record dict, because the render
# vocabulary and currency divisor live in the mission and the title and edition
# live in the state's entity table.
# ---------------------------------------------------------------------------

_CURRENCY_SYMBOLS = {"GBP": "\u00a3"}


def render_task_customer_text(
    *,
    spec: CustomerRequestSpec,
    mission: MissionSpec,
    snapshot: ShopSnapshot,
    response: TaskServiceResponse,
) -> str:
    """Render the customer-facing answer from a validated envelope alone.

    Only task status, validated claims and the mission's public explanation text
    and render vocabulary are consulted. The service's logs, its uncertainty codes
    and any prose it tried to carry are not inputs, so unassessed text cannot
    contradict the scored result.
    """
    requested = spec.requested_entities[0] if spec.requested_entities else None
    sentences = [
        _render_task_result(mission, snapshot, requested, result)
        for result in response.task_results
    ]
    if not sentences:
        return "The service returned no answer for this request."
    return " ".join(sentences)


def _render_task_result(
    mission: MissionSpec,
    snapshot: ShopSnapshot,
    requested_entity: str | None,
    result: TaskResult,
) -> str:
    if result.status is not TaskStatus.COMPLETED:
        return _render_fallback(mission, result)

    claims = {claim.kind: claim for claim in result.claims}
    entity = _entity(snapshot, result.entity_ref)
    availability = claims.get("availability")

    if availability is not None:
        value = availability.value
        date = value.get("collection_date") if isinstance(value, dict) else None
        if not isinstance(date, str):
            raise ServiceResponseInvalid(
                f"task {result.task_id!r} completed without a collection date to render"
            )
        if result.entity_ref != requested_entity:
            return _fill(
                mission.render_vocabulary["alternative"],
                mission=mission,
                snapshot=snapshot,
                entity=entity,
                collection_date=date,
                price_claim=claims.get("price"),
            )
        template = (
            mission.render_vocabulary["collection_available"]
            if value.get("can_collect") is True
            else mission.render_vocabulary["collection_unavailable"]
        )
        return _fill(
            template, mission=mission, snapshot=snapshot, entity=entity, collection_date=date
        )

    price = claims.get("price")
    if price is None:
        raise ServiceResponseInvalid(
            f"task {result.task_id!r} completed with no claim the vocabulary can render"
        )
    return _fill(
        mission.render_vocabulary["price"],
        mission=mission,
        snapshot=snapshot,
        entity=entity,
        price_claim=price,
    )


def _render_fallback(mission: MissionSpec, result: TaskResult) -> str:
    if result.status is TaskStatus.NOT_APPLICABLE:
        return mission.render_vocabulary["not_applicable"]
    explanation = mission.explanation_codes.get(result.explanation_code or "")
    if explanation is None:
        raise ServiceResponseInvalid(
            f"task {result.task_id!r} cites explanation code {result.explanation_code!r} "
            "the reviewed mission does not define"
        )
    return explanation.customer_text


def _entity(snapshot: ShopSnapshot, entity_ref: str) -> ShopEntity:
    entity = snapshot.entities.get(entity_ref)
    if entity is None:
        raise ServiceResponseInvalid(
            f"the response names entity {entity_ref!r}, which the frozen public state does not define"
        )
    return entity


def _fill(
    template: str,
    *,
    mission: MissionSpec,
    snapshot: ShopSnapshot,
    entity: ShopEntity,
    collection_date: str | None = None,
    price_claim: TaskClaim | None = None,
) -> str:
    fields: dict[str, str] = {"title": entity.title, "edition": entity.edition}
    if collection_date is not None:
        fields["collection_date"] = collection_date
    if price_claim is not None:
        fields["formatted_price"] = _format_price(mission, snapshot, price_claim)
    try:
        return template.format(**fields)
    except (KeyError, IndexError) as exc:
        raise ServiceResponseInvalid(
            f"the render vocabulary needs a field this response cannot supply: {exc}"
        ) from exc


def _format_price(mission: MissionSpec, snapshot: ShopSnapshot, claim: TaskClaim) -> str:
    value = claim.value
    if not isinstance(value, int) or isinstance(value, bool):
        raise ServiceResponseInvalid("a price claim must carry an integer minor-unit value")
    divisor = mission.minor_units_per_gbp
    if divisor <= 0:
        raise ServiceResponseInvalid("the mission declares a non-positive currency divisor")
    symbol = _CURRENCY_SYMBOLS.get(snapshot.currency, "")
    units, remainder = divmod(value, divisor)
    return f"{symbol}{units}.{remainder:02d}"
