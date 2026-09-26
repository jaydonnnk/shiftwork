"""Customer-answer derivation (program design S6 test 42, full at Slice 4).

The displayed customer text is derived deterministically from the validated
structure; there is no separately authored reply_text that could contradict the
scored claims. A false age, an invalid evidence ref or a malformed claim produces
no customer sentence and a failure. The rendered sentences below are hand-pinned
specifications, not recorded evaluator output.
"""

import inspect
import json
import re

import pytest
from pydantic import ValidationError

from shiftwork import config
from shiftwork.domain import task_contract
from shiftwork.domain.customer_answer import (
    ServiceResponseInvalid,
    render_customer_text,
    render_task_customer_text,
    validate_service_response,
)
from shiftwork.domain.errors import TaskEnvelopeInvalid
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


# ---------------------------------------------------------------------------
# Slice 11: task-aware rendering (Gate 3 obligation 14)
# ---------------------------------------------------------------------------

PIVOT_DATE = "2026-09-26"
PIVOT_REQUESTED = "book:salt-roads:paperback"
PIVOT_ALTERNATIVE = "book:harbour-atlas:paperback"
POUND = "\u00a3"


@pytest.fixture(scope="module")
def pivot_mission():
    return task_contract.load_mission(config.PIVOT_MISSION)


@pytest.fixture(scope="module")
def pivot_snapshot():
    return task_contract.load_public_state(config.PIVOT_PUBLIC_STATE)


@pytest.fixture(scope="module")
def pivot_spec(pivot_mission):
    return pivot_mission.request_specs[0]


def _pivot_envelope(spec, task_results, evidence_refs=()):
    body = json.dumps(
        {
            "request_id": spec.id,
            "task_results": task_results,
            "evidence_refs": list(evidence_refs),
            "uncertainty_codes": [],
        },
        separators=(",", ":"),
    ).encode("utf-8")
    return task_contract.validate_response_envelope(spec, body)


def _price_result():
    return {
        "task_id": "price",
        "status": "COMPLETED",
        "entity_ref": PIVOT_REQUESTED,
        "claims": [
            {
                "kind": "price",
                "entity_ref": PIVOT_REQUESTED,
                "value": 1800,
                "evidence_refs": ["public:salt-roads:paperback:price"],
            }
        ],
        "commitment_ref": None,
        "explanation_code": None,
    }


def _complete_results():
    return [
        _price_result(),
        {
            "task_id": "collection",
            "status": "COMPLETED",
            "entity_ref": PIVOT_REQUESTED,
            "claims": [
                {
                    "kind": "availability",
                    "entity_ref": PIVOT_REQUESTED,
                    "value": {"collection_date": PIVOT_DATE, "can_collect": False},
                    "evidence_refs": ["public:salt-roads:paperback:collection"],
                }
            ],
            "commitment_ref": None,
            "explanation_code": None,
        },
        {
            "task_id": "alternative",
            "status": "COMPLETED",
            "entity_ref": PIVOT_ALTERNATIVE,
            "claims": [
                {
                    "kind": "price",
                    "entity_ref": PIVOT_ALTERNATIVE,
                    "value": 1600,
                    "evidence_refs": ["public:harbour-atlas:paperback:price"],
                },
                {
                    "kind": "stock",
                    "entity_ref": PIVOT_ALTERNATIVE,
                    "value": 3,
                    "evidence_refs": ["public:harbour-atlas:paperback:stock"],
                },
                {
                    "kind": "availability",
                    "entity_ref": PIVOT_ALTERNATIVE,
                    "value": {"collection_date": PIVOT_DATE, "can_collect": True},
                    "evidence_refs": ["public:harbour-atlas:paperback:collection"],
                },
            ],
            "commitment_ref": None,
            "explanation_code": None,
        },
    ]


COMPLETE_REFS = [
    "public:salt-roads:paperback:price",
    "public:salt-roads:paperback:collection",
    "public:harbour-atlas:paperback:price",
    "public:harbour-atlas:paperback:stock",
    "public:harbour-atlas:paperback:collection",
]


def _render(spec, mission, snapshot, response):
    return render_task_customer_text(
        spec=spec, mission=mission, snapshot=snapshot, response=response
    )


def test_the_recorded_starter_renders_only_the_price_it_answered(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """Hand-pinned expected text, not recorded renderer output."""
    response = _pivot_envelope(
        pivot_spec, [_price_result()], ["public:salt-roads:paperback:price"]
    )
    assert _render(pivot_spec, pivot_mission, pivot_snapshot, response) == (
        f"Salt Roads (paperback) costs {POUND}18.00."
    )


def test_a_complete_answer_renders_every_task_in_order(
    pivot_spec, pivot_mission, pivot_snapshot
):
    response = _pivot_envelope(pivot_spec, _complete_results(), COMPLETE_REFS)
    assert _render(pivot_spec, pivot_mission, pivot_snapshot, response) == (
        f"Salt Roads (paperback) costs {POUND}18.00. "
        f"Salt Roads (paperback) is not confirmed for collection on {PIVOT_DATE}. "
        f"Harbour Atlas (paperback) is a same-genre alternative at {POUND}16.00, "
        f"available for collection on {PIVOT_DATE}."
    )


def test_a_fallback_renders_the_missions_own_public_text(
    pivot_spec, pivot_mission, pivot_snapshot
):
    response = _pivot_envelope(
        pivot_spec,
        [
            {
                "task_id": "collection",
                "status": "REFERRED",
                "entity_ref": PIVOT_REQUESTED,
                "claims": [],
                "commitment_ref": None,
                "explanation_code": "PUBLIC_DATA_UNAVAILABLE",
            }
        ],
    )
    rendered = _render(pivot_spec, pivot_mission, pivot_snapshot, response)
    assert rendered == pivot_mission.explanation_codes["PUBLIC_DATA_UNAVAILABLE"].customer_text


def test_not_applicable_renders_the_vocabulary_sentence(
    pivot_spec, pivot_mission, pivot_snapshot
):
    response = _pivot_envelope(
        pivot_spec,
        [
            {
                "task_id": "alternative",
                "status": "NOT_APPLICABLE",
                "entity_ref": PIVOT_REQUESTED,
                "claims": [],
                "commitment_ref": None,
                "explanation_code": None,
            }
        ],
    )
    assert _render(pivot_spec, pivot_mission, pivot_snapshot, response) == (
        pivot_mission.render_vocabulary["not_applicable"]
    )


def test_an_empty_envelope_says_so_rather_than_inventing_an_answer(
    pivot_spec, pivot_mission, pivot_snapshot
):
    response = _pivot_envelope(pivot_spec, [])
    assert _render(pivot_spec, pivot_mission, pivot_snapshot, response) == (
        "The service returned no answer for this request."
    )


@pytest.mark.parametrize("field", ["customer_text", "answer", "prose"])
def test_contradictory_prose_is_rejected_before_any_rendering(
    pivot_spec, pivot_mission, pivot_snapshot, field
):
    """Obligation 14: prose that contradicts the scored claims never reaches text.

    The rejection happens in envelope validation, so there is no envelope to hand
    the renderer and no code path where the service's own sentence could display.
    """
    contradiction = "Yes, your paperback is ready for collection tomorrow."
    payload = {
        "request_id": pivot_spec.id,
        "task_results": [_price_result()],
        "evidence_refs": ["public:salt-roads:paperback:price"],
        "uncertainty_codes": [],
        field: contradiction,
    }
    with pytest.raises(TaskEnvelopeInvalid) as excinfo:
        task_contract.validate_response_envelope(
            pivot_spec, json.dumps(payload, separators=(",", ":")).encode("utf-8")
        )
    assert contradiction not in excinfo.value.message


def test_the_renderer_takes_no_log_or_prose_input():
    """The signature is the guard: service logs cannot become the customer answer."""
    parameters = set(inspect.signature(render_task_customer_text).parameters)
    assert parameters == {"spec", "mission", "snapshot", "response"}
    assert not any(
        banned in parameters for banned in ("logs", "log_ref", "text", "prose", "answer")
    )


def test_every_rendered_sentence_comes_from_the_mission_vocabulary(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """No sentence is authored in the renderer; each is a template or a public code."""
    response = _pivot_envelope(pivot_spec, _complete_results(), COMPLETE_REFS)
    rendered = _render(pivot_spec, pivot_mission, pivot_snapshot, response)
    allowed = set(pivot_mission.render_vocabulary.values()) | {
        explanation.customer_text for explanation in pivot_mission.explanation_codes.values()
    }
    for sentence in rendered.split(". "):
        normalized = sentence if sentence.endswith(".") else sentence + "."
        assert any(
            _matches_template(normalized, template) for template in allowed
        ), f"sentence was not derived from the vocabulary: {sentence!r}"


def _matches_template(sentence, template):
    """True when a sentence is some substitution of a vocabulary template.

    Placeholders become lazy wildcards rather than dot-free ones, because a
    formatted price legitimately contains a decimal point.
    """
    pattern = re.escape(template)
    for placeholder in ("title", "edition", "collection_date", "formatted_price"):
        pattern = pattern.replace(re.escape("{" + placeholder + "}"), ".+?")
    return re.fullmatch(pattern, sentence) is not None


def test_an_unknown_entity_fails_closed_instead_of_leaking_its_ref(
    pivot_spec, pivot_mission, pivot_snapshot
):
    """A raw entity ref is internal naming and must not reach a customer surface."""
    unknown = pivot_snapshot.model_copy(
        update={
            "entities": {
                key: value
                for key, value in pivot_snapshot.entities.items()
                if key != PIVOT_REQUESTED
            }
        }
    )
    response = _pivot_envelope(
        pivot_spec, [_price_result()], ["public:salt-roads:paperback:price"]
    )
    with pytest.raises(ServiceResponseInvalid) as excinfo:
        _render(pivot_spec, pivot_mission, unknown, response)
    assert "does not define" in excinfo.value.message


def test_an_unrenderable_completion_fails_closed(pivot_spec, pivot_mission, pivot_snapshot):
    """A completed task with no renderable claim raises rather than emitting prose."""
    response = _pivot_envelope(
        pivot_spec,
        [
            {
                "task_id": "price",
                "status": "COMPLETED",
                "entity_ref": PIVOT_REQUESTED,
                "claims": [
                    {
                        "kind": "policy_answer",
                        "entity_ref": PIVOT_REQUESTED,
                        "value": "collect any time",
                        "evidence_refs": [],
                    }
                ],
                "commitment_ref": None,
                "explanation_code": None,
            }
        ],
    )
    with pytest.raises(ServiceResponseInvalid, match="no claim the vocabulary can render"):
        _render(pivot_spec, pivot_mission, pivot_snapshot, response)
