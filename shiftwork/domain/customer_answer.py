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
