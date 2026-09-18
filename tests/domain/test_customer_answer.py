"""Customer-answer derivation (program design S6 test 42, full at Slice 4).

The displayed customer text is derived deterministically from the validated
structure; there is no separately authored reply_text that could contradict the
scored claims. A false age, an invalid evidence ref or a malformed claim produces
no customer sentence and a failure. The rendered sentences below are hand-pinned
specifications, not recorded evaluator output.
"""

import pytest
from pydantic import ValidationError

from shiftwork import config
from shiftwork.domain.customer_answer import (
    ServiceResponseInvalid,
    render_customer_text,
    validate_service_response,
)
from shiftwork.domain.models import Claim, ServiceResponse

RECORDS = {
    "catalog:9780441013593": {
        "record_id": "catalog:9780441013593",
        "kind": "stock",
        "value": "in_stock",
        "record_age_ms": 5400000,
    },
    "catalog:9780441013593:price": {
        "record_id": "catalog:9780441013593:price",
        "kind": "price",
        "value": 1999,
        "record_age_ms": 5400000,
    },
    "catalog:9780525559474": {
        "record_id": "catalog:9780525559474",
        "kind": "stock",
        "value": "out_of_stock",
        "record_age_ms": 300000,
    },
}


def _response(**overrides) -> ServiceResponse:
    base = {
        "action": "answer",
        "claims": (Claim(kind="stock", value="in_stock"),),
        "evidence_refs": ("catalog:9780441013593",),
        "record_age_ms": 5400000,
    }
    base.update(overrides)
    return ServiceResponse(**base)


def test_valid_structured_response_renders_the_pinned_sentence():
    validated = validate_service_response(_response(), RECORDS)
    assert validated.verified_record_age_ms == 5400000
    assert render_customer_text(validated) == "Answer: stock = in_stock (record age 5400000 ms)."
    # Deterministic: the same validated structure renders the same sentence.
    assert render_customer_text(validated) == render_customer_text(validated)

    two_claims = validate_service_response(
        _response(
            claims=(Claim(kind="price", value=1999), Claim(kind="stock", value="in_stock")),
            evidence_refs=("catalog:9780441013593", "catalog:9780441013593:price"),
        ),
        RECORDS,
    )
    assert render_customer_text(two_claims) == (
        "Answer: price = 1999; stock = in_stock (record age 5400000 ms)."
    )

    assert render_customer_text(
        validate_service_response(_response(action="ask", claims=(), evidence_refs=(), record_age_ms=None), RECORDS)
    ) == "Ask: I need more information from you before I can answer."
    assert render_customer_text(
        validate_service_response(_response(action="decline", claims=(), evidence_refs=(), record_age_ms=None), RECORDS)
    ) == "Decline: I cannot answer that from the shop records."
    assert render_customer_text(
        validate_service_response(_response(action="escalate", claims=(), evidence_refs=(), record_age_ms=None), RECORDS)
    ) == "Escalate: a person from the shop should handle this request."

    # The recomputed age is the newest cited record's age, not the asserted one.
    newest = validate_service_response(
        _response(
            claims=(Claim(kind="stock", value="out_of_stock"),),
            evidence_refs=("catalog:9780525559474", "catalog:9780441013593"),
            record_age_ms=300000,
        ),
        RECORDS,
    )
    assert newest.verified_record_age_ms == 300000


def test_false_age_invalid_ref_or_malformed_claim_fails_without_a_sentence():
    # A false age: the record is 5400000 ms old, the response attests 1000.
    with pytest.raises(ServiceResponseInvalid):
        validate_service_response(_response(record_age_ms=1000), RECORDS)
    # An invalid evidence ref: it resolves to no public record.
    with pytest.raises(ServiceResponseInvalid):
        validate_service_response(_response(evidence_refs=("catalog:not-a-record",)), RECORDS)
    # An age attestation with no evidence at all is contradictory.
    with pytest.raises(ServiceResponseInvalid):
        validate_service_response(_response(claims=(), evidence_refs=(), record_age_ms=1000), RECORDS)
    # References without an age attestation cannot be validated either.
    with pytest.raises(ServiceResponseInvalid):
        validate_service_response(_response(record_age_ms=None), RECORDS)
    # A malformed claim never becomes a ServiceResponse at all.
    with pytest.raises(ValidationError):
        ServiceResponse.model_validate_json(
            b'{"action":"answer","claims":[{"kind":"stock"}],"evidence_refs":[],"record_age_ms":null}'
        )


def test_no_reply_text_field_or_source_anywhere():
    # Test 42's structural clause: there is no authored-text input to contradict.
    assert "reply_text" not in ServiceResponse.model_fields
    for path in sorted(config.PACKAGE_DIR.rglob("*.py")):
        assert "reply_text" not in path.read_text(encoding="utf-8"), path
