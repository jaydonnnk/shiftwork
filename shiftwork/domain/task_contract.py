"""Public task contract, mission rubric and the task-aware service envelope (S3.3).

Slice 11 adds the pivot's task-aware response contract beside the sealed path's
older ``action``/``claims`` envelope rather than replacing it. The three sealed
families the user reviewed are authored against that older envelope and ADR 0001
makes sealed material immutable, so this module owns a separate vocabulary and
``models.ServiceResponse`` keeps serving the sealed evaluator.

Two pure jobs live here and neither reads a database, the environment or the
network:

- ``validate_response_envelope`` decides whether captured bytes are a well-formed
  envelope at all. It never decides whether the answer was good.
- ``resolve_record_group`` and ``resolve_collection_facts`` implement the
  ``claim.public_support`` and ``collection.confirmed_only`` record rules, so the
  assessor asks the frozen public state a question instead of re-deriving policy.

Assessment, which turns a validated envelope plus these resolved facts into
``TaskAssessment`` outcomes, lives in ``evaluator.py`` per the Gate 3 file map.
"""

import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from shiftwork.domain.errors import (
    MissionSpecInvalid,
    PublicStateInvalid,
    TaskEnvelopeInvalid,
)
from shiftwork.domain.models import Id, JsonValue, ReasonCode

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class TaskKind(StrEnum):
    ANSWER_FACT = "ANSWER_FACT"
    CONFIRM_COLLECTION = "CONFIRM_COLLECTION"
    SUGGEST_ALTERNATIVE = "SUGGEST_ALTERNATIVE"
    CREATE_BOOKING = "CREATE_BOOKING"
    EXPLAIN_LIMIT = "EXPLAIN_LIMIT"


class TaskStatus(StrEnum):
    COMPLETED = "COMPLETED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    REFUSED = "REFUSED"
    REFERRED = "REFERRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class TaskOutcome(StrEnum):
    USEFUL_COMPLETION = "USEFUL_COMPLETION"
    INCORRECT_OUTPUT = "INCORRECT_OUTPUT"
    JUSTIFIED_REFUSAL = "JUSTIFIED_REFUSAL"
    JUSTIFIED_REFERRAL = "JUSTIFIED_REFERRAL"
    JUSTIFIED_CLARIFICATION = "JUSTIFIED_CLARIFICATION"
    UNJUSTIFIED_REFUSAL = "UNJUSTIFIED_REFUSAL"
    UNJUSTIFIED_REFERRAL = "UNJUSTIFIED_REFERRAL"
    UNJUSTIFIED_CLARIFICATION = "UNJUSTIFIED_CLARIFICATION"
    MISSING_OUTPUT = "MISSING_OUTPUT"


# The three fallback statuses a justification rule can bless. A justified
# fallback satisfies its mandatory rule but never counts as useful completion.
FALLBACK_STATUSES = (
    TaskStatus.NEEDS_CLARIFICATION,
    TaskStatus.REFUSED,
    TaskStatus.REFERRED,
)

_STATUS_TO_OUTCOME: dict[TaskStatus, tuple[TaskOutcome, TaskOutcome, ReasonCode]] = {
    TaskStatus.REFUSED: (
        TaskOutcome.JUSTIFIED_REFUSAL,
        TaskOutcome.UNJUSTIFIED_REFUSAL,
        ReasonCode.UNJUSTIFIED_REFUSAL,
    ),
    TaskStatus.REFERRED: (
        TaskOutcome.JUSTIFIED_REFERRAL,
        TaskOutcome.UNJUSTIFIED_REFERRAL,
        ReasonCode.UNJUSTIFIED_REFERRAL,
    ),
    TaskStatus.NEEDS_CLARIFICATION: (
        TaskOutcome.JUSTIFIED_CLARIFICATION,
        TaskOutcome.UNJUSTIFIED_CLARIFICATION,
        ReasonCode.UNJUSTIFIED_CLARIFICATION,
    ),
}

FACTUAL_CLAIM_KINDS = ("price", "stock", "availability")


class Claim(BaseModel):
    """A task-aware factual claim, attributed to an entity and its evidence."""

    model_config = _FROZEN

    kind: Literal["price", "stock", "availability", "policy_answer", "booking", "none"]
    entity_ref: str
    value: JsonValue
    evidence_refs: tuple[str, ...]


class TaskResult(BaseModel):
    model_config = _FROZEN

    task_id: Id
    status: TaskStatus
    entity_ref: str
    claims: tuple[Claim, ...]
    commitment_ref: str | None = None
    explanation_code: str | None = None


class ServiceResponse(BaseModel):
    """The pivot envelope. ``extra="forbid"`` is the ``response.structured_only``
    rule: an independent ``customer_text``, ``answer`` or prose field is rejected
    here, so unassessed prose can never reach a customer surface."""

    model_config = _FROZEN

    request_id: Id
    task_results: tuple[TaskResult, ...]
    evidence_refs: tuple[str, ...]
    uncertainty_codes: tuple[str, ...]


class RequiredTask(BaseModel):
    model_config = _FROZEN

    id: Id
    kind: TaskKind
    requested_entity_ref: str
    condition_json: dict[str, JsonValue]
    required: bool


class CustomerRequestSpec(BaseModel):
    model_config = _FROZEN

    id: Id
    text: str
    requested_entities: tuple[str, ...]
    tasks: tuple[RequiredTask, ...]
    mandatory_rule_ids: tuple[str, ...]


class VisibleCheck(BaseModel):
    """A learner-authored public test over one frozen request."""

    model_config = _FROZEN

    id: Id
    request: CustomerRequestSpec
    observable_expectation: str
    authored_by: Literal["learner"] = "learner"


class TaskAssessment(BaseModel):
    model_config = _FROZEN

    request_id: Id
    request_ordinal: int
    task_id: Id
    outcome: TaskOutcome
    mandatory_pass: bool
    reason_codes: tuple[ReasonCode, ...]


class ExplanationCode(BaseModel):
    """A public fallback the service may cite. Only a fallback status is
    representable, so a rubric that tried to justify a COMPLETED result fails at
    parse time instead of silently blessing an incomplete answer."""

    model_config = _FROZEN

    code: str
    status: Literal["NEEDS_CLARIFICATION", "REFUSED", "REFERRED"]
    allowed_task_kinds: tuple[TaskKind, ...]
    condition: str
    customer_text: str


class MissionSpec(BaseModel):
    """The reviewed public rubric. Frozen task specifications plus the rule text
    the learner can read; nothing here is a hidden grading rule.

    ``evidence_limits`` travels with the rubric so a room surface can label the
    scenario honestly next to the result it displays.
    """

    model_config = _FROZEN

    engagement_slug: str
    version: int
    review_status: str
    description: str
    contract_catalog_version: int
    contract_catalog_hash: str
    request_specs: tuple[CustomerRequestSpec, ...]
    public_rules: dict[str, str]
    max_record_age_ms: int
    minor_units_per_gbp: int
    tomorrow_basis: str
    explanation_codes: dict[str, ExplanationCode]
    allowed_tool_vocabulary: dict[str, str]
    render_vocabulary: dict[str, str]
    evidence_limits: tuple[str, ...]


class ShopEntity(BaseModel):
    model_config = _FROZEN

    title: str
    edition: str
    genre: str


class PublicRecord(BaseModel):
    model_config = _FROZEN

    record_id: str
    entity_ref: str
    kind: Literal["price", "stock", "availability"]
    value: JsonValue
    record_age_ms: int
    dependency: str
    currency: str | None = None


class ShopSnapshot(BaseModel):
    model_config = _FROZEN

    engagement_slug: str
    display_name: str
    snapshot_version: int
    review_status: str
    description: str
    observed_at: datetime
    timezone: str
    currency: str
    dependencies: dict[str, str]
    entities: dict[str, ShopEntity]
    records: tuple[PublicRecord, ...]


RecordStatus = Literal["AGREED", "CONFLICT", "NO_CURRENT_RECORD"]


class RecordGroup(BaseModel):
    """All current available records for an entity and kind, resolved as a fact.

    ``CONFLICT`` means the frozen state cannot support any claim from this group,
    including a claim citing only the newest record: neither array order nor
    selective citation resolves a conflict.
    """

    model_config = _FROZEN

    entity_ref: str
    kind: str
    collection_date: str | None = None
    status: RecordStatus
    value: JsonValue = None
    newest_record_id: str | None = None
    record_ids: tuple[str, ...] = ()


class CollectionFacts(BaseModel):
    """The two records a collection answer depends on, plus their cross-conflict.

    ``conflicting`` is the ``collection.confirmed_only`` rule that current
    ``can_collect=true`` with current stock of zero or less is contradictory
    necessary information. The reverse is not a conflict: shelf stock alone does
    not guarantee collection, so positive stock with ``can_collect=false`` stands.
    """

    model_config = _FROZEN

    availability: RecordGroup
    stock: RecordGroup
    conflicting: bool


def load_mission(path: Path) -> MissionSpec:
    """Load a reviewed public rubric, refusing a malformed one outright.

    Fail-closed for the same reason the catalog loader is: a rubric that silently
    lost a required task or an explanation code would let an incomplete answer
    pass, which is worse than refusing to run.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MissionSpecInvalid(f"mission {path.name} is not readable JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise MissionSpecInvalid(f"mission {path.name} is not a JSON object")

    try:
        specs = tuple(
            CustomerRequestSpec.model_validate(item) for item in data["request_specs"]
        )
        codes = {
            code: ExplanationCode.model_validate({"code": code, **body})
            for code, body in data["explanation_codes"].items()
        }
        constants = data["constants"]
        mission = MissionSpec(
            engagement_slug=data["engagement_slug"],
            version=data["version"],
            review_status=data["review_status"],
            description=data["description"],
            contract_catalog_version=data["contract_catalog_version"],
            contract_catalog_hash=data["contract_catalog_hash"],
            request_specs=specs,
            public_rules=data["public_rules"],
            max_record_age_ms=constants["max_record_age_ms"],
            minor_units_per_gbp=constants["minor_units_per_gbp"],
            tomorrow_basis=constants["tomorrow_basis"],
            explanation_codes=codes,
            allowed_tool_vocabulary=data["allowed_tool_vocabulary"],
            render_vocabulary=data["render_vocabulary"],
            evidence_limits=tuple(data["evidence_limits"]),
        )
    except ValidationError as exc:
        raise MissionSpecInvalid(
            f"mission {path.name} is not a usable rubric: {_validation_summary(exc)}"
        ) from exc
    except (KeyError, TypeError) as exc:
        raise MissionSpecInvalid(f"mission {path.name} is not a usable rubric: missing {exc}") from exc

    _check_mission(path, mission)
    return mission


def _check_mission(path: Path, mission: MissionSpec) -> None:
    if not mission.request_specs:
        raise MissionSpecInvalid(f"mission {path.name} declares no request specs")
    if mission.max_record_age_ms <= 0:
        raise MissionSpecInvalid(f"mission {path.name} has a non-positive max_record_age_ms")
    if not mission.render_vocabulary:
        raise MissionSpecInvalid(f"mission {path.name} has no render vocabulary")

    seen_request_ids: set[str] = set()
    for spec in mission.request_specs:
        if spec.id in seen_request_ids:
            raise MissionSpecInvalid(f"mission {path.name} repeats request id {spec.id!r}")
        seen_request_ids.add(spec.id)
        if not spec.tasks:
            raise MissionSpecInvalid(f"request {spec.id} declares no tasks")
        if not spec.requested_entities:
            raise MissionSpecInvalid(f"request {spec.id} names no requested entity")
        task_ids = [task.id for task in spec.tasks]
        if len(set(task_ids)) != len(task_ids):
            raise MissionSpecInvalid(f"request {spec.id} repeats a task id")
        if not any(task.required for task in spec.tasks):
            raise MissionSpecInvalid(f"request {spec.id} has no required task")
        for rule_id in spec.mandatory_rule_ids:
            if rule_id not in mission.public_rules:
                raise MissionSpecInvalid(
                    f"request {spec.id} cites mandatory rule {rule_id!r} the mission does not define"
                )

    for code, explanation in mission.explanation_codes.items():
        if not explanation.allowed_task_kinds:
            raise MissionSpecInvalid(f"explanation code {code!r} allows no task kind")


def load_public_state(path: Path) -> ShopSnapshot:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicStateInvalid(f"public state {path.name} is not readable JSON: {exc}") from exc
    try:
        snapshot = ShopSnapshot.model_validate(data)
    except ValidationError as exc:
        raise PublicStateInvalid(
            f"public state {path.name} is not usable: {_validation_summary(exc)}"
        ) from exc
    if not snapshot.records:
        raise PublicStateInvalid(f"public state {path.name} carries no records")
    for record in snapshot.records:
        if record.entity_ref not in snapshot.entities:
            raise PublicStateInvalid(
                f"record {record.record_id} cites entity {record.entity_ref!r} the state does not define"
            )
        if record.dependency not in snapshot.dependencies:
            raise PublicStateInvalid(
                f"record {record.record_id} cites dependency {record.dependency!r} the state does not declare"
            )
    return snapshot


def validate_response_envelope(
    request: CustomerRequestSpec,
    response_bytes: bytes,
) -> ServiceResponse:
    """Validate captured bytes as an envelope, without judging the answer.

    Rejects unparseable bytes, any field the contract does not define, a request
    id that is not the frozen request's, an unknown or duplicated task id, a
    status whose explanation code is missing when a fallback needs one or present
    when completion forbids one, a ``NOT_APPLICABLE`` result carrying claims or a
    commitment, and a claim citing evidence the response did not list.
    """
    try:
        payload = json.loads(response_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TaskEnvelopeInvalid(f"captured response is not valid UTF-8 JSON ({type(exc).__name__})") from exc
    try:
        response = ServiceResponse.model_validate(payload)
    except ValidationError as exc:
        raise TaskEnvelopeInvalid(f"captured response is not a valid envelope: {_validation_summary(exc)}") from exc

    if response.request_id != request.id:
        raise TaskEnvelopeInvalid(
            f"response answers request {response.request_id!r}, not the frozen {request.id!r}"
        )

    known = {task.id: task for task in request.tasks}
    seen: set[str] = set()
    for result in response.task_results:
        if result.task_id not in known:
            raise TaskEnvelopeInvalid(f"response returns a result for unknown task {result.task_id!r}")
        if result.task_id in seen:
            raise TaskEnvelopeInvalid(f"response returns two results for task {result.task_id!r}")
        seen.add(result.task_id)
        _check_result_shape(result)

    listed = set(response.evidence_refs)
    for result in response.task_results:
        for claim in result.claims:
            unlisted = tuple(ref for ref in claim.evidence_refs if ref not in listed)
            if unlisted:
                raise TaskEnvelopeInvalid(
                    f"claim on task {result.task_id!r} cites evidence the response did not list: "
                    f"{', '.join(unlisted)}"
                )
    return response


def _check_result_shape(result: TaskResult) -> None:
    if result.status is TaskStatus.COMPLETED and result.explanation_code is not None:
        raise TaskEnvelopeInvalid(
            f"task {result.task_id!r} is COMPLETED but carries explanation code "
            f"{result.explanation_code!r}"
        )
    if result.status in FALLBACK_STATUSES and result.explanation_code is None:
        raise TaskEnvelopeInvalid(
            f"task {result.task_id!r} is {result.status.value} without a public explanation code"
        )
    if result.status is TaskStatus.NOT_APPLICABLE:
        if result.explanation_code is not None:
            raise TaskEnvelopeInvalid(
                f"task {result.task_id!r} is NOT_APPLICABLE but carries an explanation code"
            )
        if result.claims:
            raise TaskEnvelopeInvalid(f"task {result.task_id!r} is NOT_APPLICABLE but asserts claims")
        if result.commitment_ref is not None:
            raise TaskEnvelopeInvalid(f"task {result.task_id!r} is NOT_APPLICABLE but creates a commitment")


def _validation_summary(exc: ValidationError) -> str:
    """Field locators and error types only, never the submitted values.

    A captured envelope is learner-service output. Echoing it into an HTTP detail
    would put arbitrary service-authored bytes on a public error surface.
    """
    parts = [
        f"{'.'.join(str(item) for item in error['loc']) or '<root>'}:{error['type']}"
        for error in exc.errors()
    ]
    return ", ".join(parts[:8])


def resolve_record_group(
    snapshot: ShopSnapshot,
    entity_ref: str,
    kind: Literal["price", "stock", "availability"],
    *,
    max_record_age_ms: int,
    collection_date: str | None = None,
) -> RecordGroup:
    """Resolve every current available record for an entity and kind into a fact.

    A record counts only when it is within the age limit and its dependency is
    available. Availability records are grouped by ``collection_date`` when one is
    given, so a different date can never confirm the requested one. Distinct
    values, or distinct price currencies, make the whole group ``CONFLICT``.
    """
    current = [
        record
        for record in snapshot.records
        if record.entity_ref == entity_ref
        and record.kind == kind
        and record.record_age_ms <= max_record_age_ms
        and snapshot.dependencies.get(record.dependency) == "available"
    ]
    if kind == "availability" and collection_date is not None:
        current = [
            record
            for record in current
            if isinstance(record.value, dict)
            and record.value.get("collection_date") == collection_date
        ]

    if not current:
        return RecordGroup(
            entity_ref=entity_ref, kind=kind, collection_date=collection_date, status="NO_CURRENT_RECORD"
        )

    identities = {_record_identity(record) for record in current}
    record_ids = tuple(sorted(record.record_id for record in current))
    if len(identities) > 1:
        return RecordGroup(
            entity_ref=entity_ref,
            kind=kind,
            collection_date=collection_date,
            status="CONFLICT",
            record_ids=record_ids,
        )

    newest = min(current, key=lambda record: (record.record_age_ms, record.record_id))
    return RecordGroup(
        entity_ref=entity_ref,
        kind=kind,
        collection_date=collection_date,
        status="AGREED",
        value=newest.value,
        newest_record_id=newest.record_id,
        record_ids=record_ids,
    )


def resolve_collection_facts(
    snapshot: ShopSnapshot,
    entity_ref: str,
    collection_date: str,
    *,
    max_record_age_ms: int,
) -> CollectionFacts:
    availability = resolve_record_group(
        snapshot,
        entity_ref,
        "availability",
        max_record_age_ms=max_record_age_ms,
        collection_date=collection_date,
    )
    stock = resolve_record_group(
        snapshot, entity_ref, "stock", max_record_age_ms=max_record_age_ms
    )
    return CollectionFacts(
        availability=availability,
        stock=stock,
        conflicting=_collection_conflicts(availability, stock),
    )


def _collection_conflicts(availability: RecordGroup, stock: RecordGroup) -> bool:
    if availability.status != "AGREED" or stock.status != "AGREED":
        return False
    value = availability.value
    if not isinstance(value, dict) or value.get("can_collect") is not True:
        return False
    quantity = stock.value
    return isinstance(quantity, int) and not isinstance(quantity, bool) and quantity <= 0


def _record_identity(record: PublicRecord) -> str:
    if record.kind == "price":
        return json.dumps([record.value, record.currency], sort_keys=True, separators=(",", ":"))
    return json.dumps(record.value, sort_keys=True, separators=(",", ":"))


def fallback_outcome(
    status: TaskStatus,
) -> tuple[TaskOutcome, TaskOutcome, ReasonCode]:
    """The justified outcome, the unjustified outcome and the unjustified code."""
    return _STATUS_TO_OUTCOME[status]
