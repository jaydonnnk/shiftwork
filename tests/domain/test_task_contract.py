"""S11: the public task contract, mission rubric and task-aware envelope.

These tests bind the assessor's inputs to the exact reviewed public bytes and
prove the envelope validator rejects a malformed response without judging whether
the answer was good. Every rejection is asserted on a named condition, so a
validator that stopped rejecting still fails here.
"""

import hashlib
import json

import pytest
from pydantic import ValidationError

from shiftwork import config
from shiftwork.domain import task_contract as tc
from shiftwork.domain.errors import (
    MissionSpecInvalid,
    PublicStateInvalid,
    TaskEnvelopeInvalid,
)

# Raw SHA-256 of the reviewed public bytes, transcribed from the pin table in
# docs/plans/shiftwork/00-status.md. A fixture edit that was not re-reviewed fails
# the pin test below rather than silently changing what the assessor grades.
PINNED_PUBLIC_FIXTURE_HASHES = {
    config.PIVOT_MISSION: "aebe89555a72688eedfb564088f57b78328c184d0a4e378918c46d13d1e6c12a",
    config.PIVOT_PUBLIC_STATE: "6bc17d69f43b24aa6048fdead7747e5820cd5740e47ba03a4a004d9ddea3c32c",
    config.PIVOT_COMPARE_STATE: "4abe54462600ade9793c1d7dc32978c427d4f0b0a5e5b121830cfc3b478a2f6f",
    config.PIVOT_INCIDENT_REQUESTS: "e9ae58c7d352f3f21b1f0edacbfcabf73a7c0edc0f551e7eb0bea8ae829cc399",
}

REQUEST_ID = "bellwether-collection-001"
REQUESTED_ENTITY = "book:salt-roads:paperback"
ALTERNATIVE_ENTITY = "book:harbour-atlas:paperback"
HARDBACK_ENTITY = "book:salt-roads:hardback"
COLLECTION_DATE = "2026-09-26"


@pytest.fixture(scope="module")
def mission():
    return tc.load_mission(config.PIVOT_MISSION)


@pytest.fixture(scope="module")
def snapshot():
    return tc.load_public_state(config.PIVOT_PUBLIC_STATE)


@pytest.fixture(scope="module")
def spec(mission):
    return mission.request_specs[0]


def _envelope(task_results, evidence_refs=(), request_id=REQUEST_ID, uncertainty_codes=()):
    return json.dumps(
        {
            "request_id": request_id,
            "task_results": task_results,
            "evidence_refs": list(evidence_refs),
            "uncertainty_codes": list(uncertainty_codes),
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _result(task_id, status, entity_ref=REQUESTED_ENTITY, claims=(), commitment_ref=None, explanation_code=None):
    return {
        "task_id": task_id,
        "status": status,
        "entity_ref": entity_ref,
        "claims": list(claims),
        "commitment_ref": commitment_ref,
        "explanation_code": explanation_code,
    }


def _claim(kind, value, entity_ref=REQUESTED_ENTITY, evidence_refs=()):
    return {
        "kind": kind,
        "entity_ref": entity_ref,
        "value": value,
        "evidence_refs": list(evidence_refs),
    }


def _with_extra_record(snapshot, **fields):
    return snapshot.model_copy(update={"records": snapshot.records + (tc.PublicRecord(**fields),)})


# --- reviewed bytes ----------------------------------------------------------


def test_pinned_public_fixtures_match_the_reviewed_bytes():
    for path, pinned in PINNED_PUBLIC_FIXTURE_HASHES.items():
        assert len(pinned) == 64, f"{path.name} pin is not a full digest"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == pinned, f"{path.name} changed from its reviewed bytes"


def test_mission_declares_the_reviewed_public_scenario(mission, spec):
    assert mission.engagement_slug == config.BOOKSHOP_SLUG
    assert mission.review_status == "AUTHORIZED_FOR_LOCAL_VERIFICATION"
    assert spec.text == (
        "Can I collect the Salt Roads paperback tomorrow? "
        "If not, suggest something similar under \u00a320."
    )
    assert spec.requested_entities == (REQUESTED_ENTITY,)
    assert [(task.id, task.kind, task.required) for task in spec.tasks] == [
        ("price", tc.TaskKind.ANSWER_FACT, False),
        ("collection", tc.TaskKind.CONFIRM_COLLECTION, True),
        ("alternative", tc.TaskKind.SUGGEST_ALTERNATIVE, True),
    ]
    assert mission.max_record_age_ms == 3_600_000
    assert mission.minor_units_per_gbp == 100


def test_every_mandatory_rule_id_has_public_rule_text(mission, spec):
    assert spec.mandatory_rule_ids, "the request must carry mandatory rules"
    assert set(spec.mandatory_rule_ids) <= set(mission.public_rules)
    assert all(text.strip() for text in mission.public_rules.values())


def test_alternative_budget_is_a_public_constant_not_a_hidden_rule(mission, spec):
    alternative = next(task for task in spec.tasks if task.id == "alternative")
    condition = alternative.condition_json
    assert condition["price_less_than_minor_units"] == 2000
    assert condition["currency"] == "GBP"
    assert condition["same_genre_as_requested_entity"] is True
    assert condition["exclude_requested_entity"] is True
    assert condition["collection_date"] == COLLECTION_DATE
    assert condition["unless_collection_confirmed"] is True


def test_incident_request_names_the_frozen_request(spec):
    lines = [
        json.loads(line)
        for line in config.PIVOT_INCIDENT_REQUESTS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) == 1, "the public incident is a single reviewed request"
    assert lines[0]["request_id"] == spec.id
    assert lines[0]["ordinal"] == 1
    assert lines[0]["text"] == spec.text
    assert lines[0]["entity_ref"] == REQUESTED_ENTITY


# --- envelope validation -----------------------------------------------------


def test_recorded_starter_envelope_validates_and_omits_both_required_tasks(spec):
    """The real captured starter response is well formed and still incomplete.

    This is the failure Slice 11 exists to make visible: validation passing is
    not the answer being right, so the two required tasks are asserted absent
    here and assessed as MISSING_OUTPUT in tests/evaluator.
    """
    body = _envelope(
        [
            _result(
                "price",
                "COMPLETED",
                claims=[_claim("price", 1800, evidence_refs=["public:salt-roads:paperback:price"])],
            )
        ],
        evidence_refs=["public:salt-roads:paperback:price"],
    )
    response = tc.validate_response_envelope(spec, body)
    assert [result.task_id for result in response.task_results] == ["price"]
    answered = {result.task_id for result in response.task_results}
    assert [task.id for task in spec.tasks if task.required and task.id not in answered] == [
        "collection",
        "alternative",
    ]


def test_complete_envelope_validates(spec):
    body = _envelope(
        [
            _result(
                "price",
                "COMPLETED",
                claims=[_claim("price", 1800, evidence_refs=["public:salt-roads:paperback:price"])],
            ),
            _result(
                "collection",
                "COMPLETED",
                claims=[
                    _claim(
                        "availability",
                        {"collection_date": COLLECTION_DATE, "can_collect": False},
                        evidence_refs=["public:salt-roads:paperback:collection"],
                    )
                ],
            ),
            _result(
                "alternative",
                "COMPLETED",
                entity_ref=ALTERNATIVE_ENTITY,
                claims=[
                    _claim("price", 1600, ALTERNATIVE_ENTITY, ["public:harbour-atlas:paperback:price"]),
                    _claim("stock", 3, ALTERNATIVE_ENTITY, ["public:harbour-atlas:paperback:stock"]),
                    _claim(
                        "availability",
                        {"collection_date": COLLECTION_DATE, "can_collect": True},
                        ALTERNATIVE_ENTITY,
                        ["public:harbour-atlas:paperback:collection"],
                    ),
                ],
            ),
        ],
        evidence_refs=[
            "public:salt-roads:paperback:price",
            "public:salt-roads:paperback:collection",
            "public:harbour-atlas:paperback:price",
            "public:harbour-atlas:paperback:stock",
            "public:harbour-atlas:paperback:collection",
        ],
    )
    response = tc.validate_response_envelope(spec, body)
    assert len(response.task_results) == 3


@pytest.mark.parametrize("field", ["customer_text", "answer", "prose", "summary"])
def test_independent_prose_field_is_rejected(spec, field):
    payload = json.loads(
        _envelope([_result("price", "COMPLETED")], evidence_refs=[]).decode("utf-8")
    )
    payload[field] = "SENTINEL_PROSE_THE_CUSTOMER_SHOULD_NEVER_SEE"
    with pytest.raises(TaskEnvelopeInvalid) as excinfo:
        tc.validate_response_envelope(spec, json.dumps(payload).encode("utf-8"))
    assert "extra_forbidden" in excinfo.value.message
    assert "SENTINEL_PROSE_THE_CUSTOMER_SHOULD_NEVER_SEE" not in excinfo.value.message


def test_rejection_message_never_echoes_the_submitted_value(spec):
    """A captured envelope is service-authored output; it must not reach a public
    error surface verbatim.

    The control matters: pydantic's own rendering does include ``input_value``, so
    without it this assertion could pass vacuously against a message that never
    carried the needle.
    """
    sentinel = "SENTINEL_KIND_9f3c1a"
    body = _envelope(
        [_result("price", "COMPLETED", claims=[_claim(sentinel, 1800)])],
        evidence_refs=[],
    )
    with pytest.raises(TaskEnvelopeInvalid) as excinfo:
        tc.validate_response_envelope(spec, body)
    assert sentinel not in excinfo.value.message
    assert "literal_error" in excinfo.value.message

    with pytest.raises(ValidationError) as raw:
        tc.ServiceResponse.model_validate(json.loads(body.decode("utf-8")))
    assert sentinel in str(raw.value), (
        "control failed: pydantic no longer echoes submitted values, so the "
        "assertion above proves nothing"
    )


def test_response_for_a_different_request_is_rejected(spec):
    body = _envelope([_result("price", "COMPLETED")], request_id="some-other-request")
    with pytest.raises(TaskEnvelopeInvalid, match="not the frozen"):
        tc.validate_response_envelope(spec, body)


def test_unknown_and_duplicated_task_ids_are_rejected(spec):
    with pytest.raises(TaskEnvelopeInvalid, match="unknown task"):
        tc.validate_response_envelope(spec, _envelope([_result("invented", "COMPLETED")]))
    with pytest.raises(TaskEnvelopeInvalid, match="two results"):
        tc.validate_response_envelope(
            spec, _envelope([_result("price", "COMPLETED"), _result("price", "COMPLETED")])
        )


def test_status_and_explanation_code_must_agree(spec):
    with pytest.raises(TaskEnvelopeInvalid, match="COMPLETED but carries explanation"):
        tc.validate_response_envelope(
            spec,
            _envelope([_result("collection", "COMPLETED", explanation_code="PUBLIC_DATA_UNAVAILABLE")]),
        )
    for status in ("REFUSED", "REFERRED", "NEEDS_CLARIFICATION"):
        with pytest.raises(TaskEnvelopeInvalid, match="without a public explanation code"):
            tc.validate_response_envelope(spec, _envelope([_result("collection", status)]))


def test_not_applicable_carries_no_code_claim_or_commitment(spec):
    with pytest.raises(TaskEnvelopeInvalid, match="NOT_APPLICABLE but carries an explanation"):
        tc.validate_response_envelope(
            spec, _envelope([_result("alternative", "NOT_APPLICABLE", explanation_code="NO_MATCHING_ALTERNATIVE")])
        )
    with pytest.raises(TaskEnvelopeInvalid, match="NOT_APPLICABLE but asserts claims"):
        tc.validate_response_envelope(
            spec,
            _envelope(
                [_result("alternative", "NOT_APPLICABLE", claims=[_claim("price", 1600)])],
                evidence_refs=["public:harbour-atlas:paperback:price"],
            ),
        )
    with pytest.raises(TaskEnvelopeInvalid, match="NOT_APPLICABLE but creates a commitment"):
        tc.validate_response_envelope(
            spec, _envelope([_result("alternative", "NOT_APPLICABLE", commitment_ref="bk-1")])
        )


def test_claim_must_cite_evidence_the_response_listed(spec):
    body = _envelope(
        [_result("price", "COMPLETED", claims=[_claim("price", 1800, evidence_refs=["public:unlisted"])])],
        evidence_refs=["public:salt-roads:paperback:price"],
    )
    with pytest.raises(TaskEnvelopeInvalid, match="did not list"):
        tc.validate_response_envelope(spec, body)


@pytest.mark.parametrize("body", [b"", b"not json", b'{"request_id":', b"\xff\xfe"])
def test_unparseable_bytes_are_rejected(spec, body):
    with pytest.raises(TaskEnvelopeInvalid):
        tc.validate_response_envelope(spec, body)


# --- public record resolution ------------------------------------------------


def test_agreed_group_cites_the_newest_matching_record(mission, snapshot):
    group = tc.resolve_record_group(
        snapshot, REQUESTED_ENTITY, "price", max_record_age_ms=mission.max_record_age_ms
    )
    assert group.status == "AGREED"
    assert group.value == 1800
    assert group.newest_record_id == "public:salt-roads:paperback:price"


def test_conflicting_values_are_unsupported_even_when_the_newest_is_cited(mission, snapshot):
    """Selective citation and array order cannot resolve a conflict."""
    conflicted = _with_extra_record(
        snapshot,
        record_id="public:salt-roads:paperback:price:newer",
        entity_ref=REQUESTED_ENTITY,
        kind="price",
        value=1999,
        currency="GBP",
        record_age_ms=0,
        dependency="catalog",
    )
    group = tc.resolve_record_group(
        conflicted, REQUESTED_ENTITY, "price", max_record_age_ms=mission.max_record_age_ms
    )
    assert group.status == "CONFLICT"
    assert group.value is None
    assert group.newest_record_id is None
    assert set(group.record_ids) == {
        "public:salt-roads:paperback:price",
        "public:salt-roads:paperback:price:newer",
    }


def test_conflicting_price_currencies_conflict(mission, snapshot):
    conflicted = _with_extra_record(
        snapshot,
        record_id="public:salt-roads:paperback:price:eur",
        entity_ref=REQUESTED_ENTITY,
        kind="price",
        value=1800,
        currency="EUR",
        record_age_ms=0,
        dependency="catalog",
    )
    group = tc.resolve_record_group(
        conflicted, REQUESTED_ENTITY, "price", max_record_age_ms=mission.max_record_age_ms
    )
    assert group.status == "CONFLICT", "the same number in two currencies is not one fact"


def test_agreeing_duplicates_stay_agreed(mission, snapshot):
    duplicated = _with_extra_record(
        snapshot,
        record_id="public:salt-roads:paperback:price:copy",
        entity_ref=REQUESTED_ENTITY,
        kind="price",
        value=1800,
        currency="GBP",
        record_age_ms=0,
        dependency="catalog",
    )
    group = tc.resolve_record_group(
        duplicated, REQUESTED_ENTITY, "price", max_record_age_ms=mission.max_record_age_ms
    )
    assert group.status == "AGREED"
    assert group.value == 1800


def test_a_record_past_the_age_limit_is_not_current(mission, snapshot):
    stale = snapshot.model_copy(
        update={
            "records": tuple(
                record.model_copy(update={"record_age_ms": mission.max_record_age_ms + 1})
                if record.kind == "price" and record.entity_ref == REQUESTED_ENTITY
                else record
                for record in snapshot.records
            )
        }
    )
    group = tc.resolve_record_group(
        stale, REQUESTED_ENTITY, "price", max_record_age_ms=mission.max_record_age_ms
    )
    assert group.status == "NO_CURRENT_RECORD"

    boundary = snapshot.model_copy(
        update={
            "records": tuple(
                record.model_copy(update={"record_age_ms": mission.max_record_age_ms})
                if record.kind == "price" and record.entity_ref == REQUESTED_ENTITY
                else record
                for record in snapshot.records
            )
        }
    )
    assert (
        tc.resolve_record_group(
            boundary, REQUESTED_ENTITY, "price", max_record_age_ms=mission.max_record_age_ms
        ).status
        == "AGREED"
    ), "the age limit is inclusive at the boundary"


def test_an_unavailable_dependency_hides_its_records(mission, snapshot):
    degraded = snapshot.model_copy(
        update={"dependencies": {**snapshot.dependencies, "inventory": "unavailable"}}
    )
    group = tc.resolve_record_group(
        degraded, REQUESTED_ENTITY, "stock", max_record_age_ms=mission.max_record_age_ms
    )
    assert group.status == "NO_CURRENT_RECORD"


def test_availability_is_grouped_by_collection_date(mission, snapshot):
    requested = tc.resolve_record_group(
        snapshot,
        REQUESTED_ENTITY,
        "availability",
        max_record_age_ms=mission.max_record_age_ms,
        collection_date=COLLECTION_DATE,
    )
    assert requested.status == "AGREED"
    assert requested.value == {"collection_date": COLLECTION_DATE, "can_collect": False}

    other_date = tc.resolve_record_group(
        snapshot,
        REQUESTED_ENTITY,
        "availability",
        max_record_age_ms=mission.max_record_age_ms,
        collection_date="2026-09-27",
    )
    assert other_date.status == "NO_CURRENT_RECORD", "another date cannot confirm the requested one"


def test_true_collection_with_zero_stock_is_conflicting_necessary_information(mission, snapshot):
    contradicted = snapshot.model_copy(
        update={
            "records": tuple(
                record.model_copy(
                    update={"value": {"collection_date": COLLECTION_DATE, "can_collect": True}}
                )
                if record.record_id == "public:salt-roads:paperback:collection"
                else record
                for record in snapshot.records
            )
        }
    )
    facts = tc.resolve_collection_facts(
        contradicted, REQUESTED_ENTITY, COLLECTION_DATE, max_record_age_ms=mission.max_record_age_ms
    )
    assert facts.availability.value["can_collect"] is True
    assert facts.stock.value == 0
    assert facts.conflicting is True


def test_false_collection_with_zero_stock_is_a_known_negative_answer(mission, snapshot):
    facts = tc.resolve_collection_facts(
        snapshot, REQUESTED_ENTITY, COLLECTION_DATE, max_record_age_ms=mission.max_record_age_ms
    )
    assert facts.availability.value["can_collect"] is False
    assert facts.stock.value == 0
    assert facts.conflicting is False, "zero stock does not contradict a false collection answer"


def test_positive_stock_with_confirmed_collection_is_not_a_conflict(mission, snapshot):
    facts = tc.resolve_collection_facts(
        snapshot, ALTERNATIVE_ENTITY, COLLECTION_DATE, max_record_age_ms=mission.max_record_age_ms
    )
    assert facts.availability.value["can_collect"] is True
    assert facts.stock.value == 3
    assert facts.conflicting is False


def test_conflicting_records_never_produce_a_collection_conflict_flag(mission, snapshot):
    """A conflicting group is unsupported, not a can_collect/stock contradiction."""
    conflicted = _with_extra_record(
        snapshot,
        record_id="public:salt-roads:paperback:stock:other",
        entity_ref=REQUESTED_ENTITY,
        kind="stock",
        value=5,
        record_age_ms=0,
        dependency="inventory",
    )
    facts = tc.resolve_collection_facts(
        conflicted, REQUESTED_ENTITY, COLLECTION_DATE, max_record_age_ms=mission.max_record_age_ms
    )
    assert facts.stock.status == "CONFLICT"
    assert facts.conflicting is False


def test_the_reviewed_alternative_qualifies_and_the_hardback_does_not(mission, snapshot):
    limit = 2000

    def qualifies(entity_ref):
        facts = tc.resolve_collection_facts(
            snapshot, entity_ref, COLLECTION_DATE, max_record_age_ms=mission.max_record_age_ms
        )
        price = tc.resolve_record_group(
            snapshot, entity_ref, "price", max_record_age_ms=mission.max_record_age_ms
        )
        if facts.conflicting or facts.availability.status != "AGREED" or price.status != "AGREED":
            return False
        if facts.availability.value["can_collect"] is not True:
            return False
        if facts.stock.status != "AGREED" or facts.stock.value <= 0:
            return False
        if price.value >= limit:
            return False
        return (
            snapshot.entities[entity_ref].genre == snapshot.entities[REQUESTED_ENTITY].genre
            and entity_ref != REQUESTED_ENTITY
        )

    assert qualifies(ALTERNATIVE_ENTITY) is True
    assert qualifies(HARDBACK_ENTITY) is False, "the hardback is over the customer's limit"
    assert qualifies(REQUESTED_ENTITY) is False, "the requested entity is excluded"


# --- fail-closed loaders -----------------------------------------------------


def test_a_mission_citing_an_undefined_mandatory_rule_is_refused(tmp_path):
    data = json.loads(config.PIVOT_MISSION.read_text(encoding="utf-8"))
    data["request_specs"][0]["mandatory_rule_ids"].append("rule.that_does_not_exist")
    path = tmp_path / "mission.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(MissionSpecInvalid, match="does not define"):
        tc.load_mission(path)


def test_a_mission_with_no_required_task_is_refused(tmp_path):
    data = json.loads(config.PIVOT_MISSION.read_text(encoding="utf-8"))
    for task in data["request_specs"][0]["tasks"]:
        task["required"] = False
    path = tmp_path / "mission.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(MissionSpecInvalid, match="no required task"):
        tc.load_mission(path)


def test_a_mission_repeating_a_task_id_is_refused(tmp_path):
    data = json.loads(config.PIVOT_MISSION.read_text(encoding="utf-8"))
    data["request_specs"][0]["tasks"].append(dict(data["request_specs"][0]["tasks"][0]))
    path = tmp_path / "mission.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(MissionSpecInvalid, match="repeats a task id"):
        tc.load_mission(path)


def test_a_mission_that_justifies_completion_is_refused(tmp_path):
    data = json.loads(config.PIVOT_MISSION.read_text(encoding="utf-8"))
    data["explanation_codes"]["PUBLIC_DATA_UNAVAILABLE"]["status"] = "COMPLETED"
    path = tmp_path / "mission.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(MissionSpecInvalid):
        tc.load_mission(path)


def test_missing_mission_file_is_refused(tmp_path):
    with pytest.raises(MissionSpecInvalid):
        tc.load_mission(tmp_path / "absent.json")


def test_public_state_citing_an_unknown_entity_is_refused(tmp_path):
    data = json.loads(config.PIVOT_PUBLIC_STATE.read_text(encoding="utf-8"))
    data["records"][0]["entity_ref"] = "book:not-in-the-catalog:paperback"
    path = tmp_path / "state.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(PublicStateInvalid, match="does not define"):
        tc.load_public_state(path)


def test_public_state_citing_an_unknown_dependency_is_refused(tmp_path):
    data = json.loads(config.PIVOT_PUBLIC_STATE.read_text(encoding="utf-8"))
    data["records"][0]["dependency"] = "telepathy"
    path = tmp_path / "state.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(PublicStateInvalid, match="does not declare"):
        tc.load_public_state(path)


def test_public_state_error_message_does_not_echo_its_contents(tmp_path):
    data = json.loads(config.PIVOT_PUBLIC_STATE.read_text(encoding="utf-8"))
    data["description"] = "SENTINEL_DESCRIPTION_77aa"
    del data["display_name"]
    path = tmp_path / "state.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(PublicStateInvalid) as excinfo:
        tc.load_public_state(path)
    assert "SENTINEL_DESCRIPTION_77aa" not in excinfo.value.message
