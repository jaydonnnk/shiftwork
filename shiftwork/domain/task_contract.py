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

from pydantic import BaseModel, ConfigDict, ValidationError, Field, StrictBool, StrictInt, model_validator

from shiftwork.domain.errors import (
    MissionSpecInvalid,
    PublicStateInvalid,
    TaskEnvelopeInvalid,
)
from shiftwork.domain.models import Id, JsonValue, ReasonCode
from shiftwork.domain import canonical

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class TaskKind(StrEnum):
    ANSWER_FACT = "ANSWER_FACT"
    CONFIRM_COLLECTION = "CONFIRM_COLLECTION"
    SUGGEST_ALTERNATIVE = "SUGGEST_ALTERNATIVE"
    CREATE_BOOKING = "CREATE_BOOKING"
    EXPLAIN_LIMIT = "EXPLAIN_LIMIT"
    # S22a material schema; independent safety assessment belongs to S22b.
    ROUTE_SAFETY_QUESTION = "ROUTE_SAFETY_QUESTION"
    QUALIFY_SIGNAL = "QUALIFY_SIGNAL"
    ASSIGN_OWNER = "ASSIGN_OWNER"
    WRITE_PIPELINE_RECORD = "WRITE_PIPELINE_RECORD"
    HANDOFF_TO_REVIEW = "HANDOFF_TO_REVIEW"


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

    kind: Literal["price", "stock", "availability", "policy_answer", "booking", "none", "safety_route",
                  "qualification", "owner_assignment", "pipeline_write", "handoff"]
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

    @model_validator(mode="after")
    def complete_pipeline_spec(self):
        kinds = {TaskKind.QUALIFY_SIGNAL, TaskKind.ASSIGN_OWNER,
                 TaskKind.WRITE_PIPELINE_RECORD, TaskKind.HANDOFF_TO_REVIEW}
        if not any(task.kind in kinds for task in self.tasks):
            return self
        if (len(self.tasks) != 4 or {task.kind for task in self.tasks} != kinds
                or len({task.id for task in self.tasks}) != 4
                or len(self.requested_entities) != 1
                or any(task.requested_entity_ref != self.requested_entities[0] for task in self.tasks)):
            raise ValueError("pipeline request needs four distinct tasks for one signal")
        for task in self.tasks:
            condition = task.condition_json
            decisions = condition.get("expected_decisions")
            if (set(condition) != {"expected_decisions", "qualified_owner", "review_owner", "repeat_of"}
                    or not isinstance(decisions, list) or not decisions
                    or any(not isinstance(value, str) or value not in {"QUALIFIED", "REVIEW", "DISQUALIFIED"}
                           for value in decisions)
                    or len(decisions) != len(set(decisions))
                    or not isinstance(condition.get("qualified_owner"), str) or not condition["qualified_owner"]
                    or condition.get("review_owner") != "revenue-review"
                    or (condition["repeat_of"] is not None and
                        (not isinstance(condition["repeat_of"], str) or not condition["repeat_of"]))
                    or task.required != (task.kind is TaskKind.QUALIFY_SIGNAL)):
                raise ValueError("invalid pinned pipeline decision conditions")
        if any(task.condition_json != self.tasks[0].condition_json for task in self.tasks):
            raise ValueError("pipeline task conditions disagree")
        required_rules = {"task.required_results", "gtm.qualification", "gtm.pinned_routing",
                          "gtm.exactly_once", "gtm.human_handoff", "response.structured_only"}
        if not required_rules.issubset(self.mandatory_rule_ids):
            raise ValueError("pipeline request cannot waive a mandatory rule")
        return self


class SignalEntity(BaseModel):
    model_config = _FROZEN
    company_name: str = Field(min_length=1)
    domain: str = Field(min_length=1)


class SignalFacts(BaseModel):
    """Synthetic public inputs, never an expected answer or observed live prediction."""
    model_config = _FROZEN
    account_domain: str = Field(min_length=1)
    region: Literal["APAC", "EMEA", "AMER", "UNKNOWN"]
    product: Literal["platform", "analytics", "UNKNOWN"]
    employee_count: StrictInt = Field(ge=0)
    suppressed: StrictBool
    intent_label: Literal["BUYING", "RESEARCH", "AMBIGUOUS"]
    confidence: StrictInt = Field(ge=0, le=100)
    note: str = Field(min_length=1)
    existing_owner: str | None
    existing_record_ref: str | None

    @model_validator(mode="after")
    def existing_record_is_complete(self):
        if (self.existing_owner is None) != (self.existing_record_ref is None):
            raise ValueError("existing synthetic record needs owner and reference together")
        if self.existing_owner == "" or self.existing_record_ref == "":
            raise ValueError("existing synthetic record fields cannot be empty")
        return self


class ProtectedRequestRow(BaseModel):
    model_config = _FROZEN

    ordinal: int
    request_id: Id
    text: str
    entity_ref: str


class ProtectedEntityDelta(BaseModel):
    model_config = _FROZEN

    title: str
    edition: str
    genre: str


class ProtectedRecordDelta(BaseModel):
    model_config = _FROZEN

    record_id: str
    entity_ref: str
    kind: Literal["price", "stock", "availability", "signal"]
    value: JsonValue
    record_age_ms: int
    dependency: str
    currency: str | None = None


class ProtectedStateDelta(BaseModel):
    model_config = _FROZEN

    description: str
    add_entities: dict[str, ProtectedEntityDelta | SignalEntity]
    add_records: tuple[ProtectedRecordDelta, ...]


class ProtectedStimulus(BaseModel):
    model_config = _FROZEN

    request: ProtectedRequestRow
    task_spec: CustomerRequestSpec
    state_delta: ProtectedStateDelta


class ProtectedBinding(BaseModel):
    model_config = _FROZEN

    pair_ordinal: int
    variant_ref: str
    request_ordinal: int
    stimulus_hash: str
    protected_state_hash: str


def protected_request_bytes(row: ProtectedRequestRow) -> bytes:
    return canonical.canonical_bytes(row.model_dump(mode="json")) + b"\n"


def resolve_protected_state(base_bytes: bytes, delta: ProtectedStateDelta) -> bytes:
    """Apply a strictly additive delta to the reviewed comparison state."""
    base = load_public_state_bytes(base_bytes)
    base_data = json.loads(base_bytes)
    existing_entities = set(base.entities)
    existing_records = {record.record_id for record in base.records}
    added_entities = set(delta.add_entities)
    added_records = [record.record_id for record in delta.add_records]
    if (existing_entities & added_entities or existing_records & set(added_records)
            or len(added_records) != len(set(added_records))):
        raise PublicStateInvalid("protected delta collides with comparison state")
    for record in delta.add_records:
        if record.entity_ref not in existing_entities | added_entities:
            raise PublicStateInvalid("protected record cites an unknown entity")
        if record.dependency not in base.dependencies:
            raise PublicStateInvalid("protected record cites an unknown dependency")
        expected_dependency = {"price": "catalog", "stock": "inventory", "availability": "collection", "signal": "enrichment"}[record.kind]
        if record.dependency != expected_dependency or record.record_age_ms < 0:
            raise PublicStateInvalid("protected record has an invalid public dependency or age")
        if record.kind == "signal":
            if base.engagement_slug != "gtm" or record.currency is not None:
                raise PublicStateInvalid("signal delta requires the GTM public state")
            try:
                SignalFacts.model_validate(record.value)
            except ValidationError as exc:
                raise PublicStateInvalid("invalid protected signal facts") from exc
        elif record.kind in ("price", "stock"):
            if type(record.value) is not int or record.value < 0:
                raise PublicStateInvalid("protected price and stock must be nonnegative integers")
            if record.currency != (base.currency if record.kind == "price" else None):
                raise PublicStateInvalid("protected record currency differs from the public shape")
        elif (not isinstance(record.value, dict)
              or set(record.value) != {"collection_date", "can_collect"}
              or not isinstance(record.value["collection_date"], str)
              or type(record.value["can_collect"]) is not bool
              or record.currency is not None):
            raise PublicStateInvalid("protected availability has an invalid public shape")
    base_data["entities"].update({
        key: value.model_dump(mode="json") for key, value in delta.add_entities.items()
    })
    base_data["records"].extend(record.model_dump(mode="json", exclude_none=True)
                                for record in delta.add_records)
    base_data["description"] = delta.description
    resolved = canonical.canonical_bytes(base_data)
    parsed = load_public_state_bytes(resolved)
    entity_ids = list(parsed.entities)
    record_ids = [record.record_id for record in parsed.records]
    if (set(entity_ids) != existing_entities | added_entities
            or len(entity_ids) != len(set(entity_ids))
            or set(record_ids) != existing_records | set(added_records)
            or len(record_ids) != len(set(record_ids))):
        raise PublicStateInvalid("protected state is not an additive resolution")
    return resolved


class DeploymentAction(BaseModel):
    model_config = _FROZEN
    sequence: StrictInt = Field(ge=1, le=64)
    kind: Literal["READ", "WRITE_SLOT", "ROLLBACK", "ROUTE_HUMAN", "DENIED"]
    resource: str
    entity_ref: str
    intent_key: str | None
    commitment_ref: str | None
    details: dict[str, JsonValue]

    @model_validator(mode="after")
    def exact_details(self):
        fields = {
            "READ": {"record_ids", "records_sha256"},
            "WRITE_SLOT": {"slot_ref", "part_ref", "booking_date", "stage", "receipt", "before_sha256", "after_sha256"},
            "ROLLBACK": {"target_receipt", "receipt", "before_sha256", "after_sha256"},
            "ROUTE_HUMAN": {"route", "receipt"},
            "DENIED": {"operation", "reason"},
        }[self.kind]
        if set(self.details) != fields or not self.resource:
            raise ValueError("deployment action has an invalid detail shape")
        for key, value in self.details.items():
            if key == "record_ids":
                if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
                    raise ValueError("invalid returned record identities")
            elif not isinstance(value, str) or not value:
                raise ValueError("deployment detail must be nonempty text")
            if key.endswith("sha256") and (not isinstance(value, str) or len(value) != 64
                                            or any(c not in "0123456789abcdef" for c in value)):
                raise ValueError("invalid deployment digest")
        if self.kind == "WRITE_SLOT" and self.details["stage"] not in {"PROVISIONAL", "FINAL"}:
            raise ValueError("invalid commitment stage")
        if self.kind == "ROUTE_HUMAN" and self.details["route"] != "human_mechanic":
            raise ValueError("invalid human route")
        return self


class DeploymentExecutionBinding(BaseModel):
    model_config = _FROZEN
    run_id: Id
    context_hash: str
    artifact_hash: str
    state_hash: str
    batch_hash: str
    phase: Literal["PUBLIC", "PROTECTED"]
    allowed_resources: tuple[str, ...]


class DeploymentTrace(BaseModel):
    model_config = _FROZEN
    run_id: Id
    context_hash: str
    artifact_hash: str
    state_hash: str
    batch_hash: str
    phase: Literal["PUBLIC", "PROTECTED"]
    request_ordinal: StrictInt = Field(ge=1)
    request_id: Id
    request_sha256: str
    response_sha256: str
    actions: tuple[DeploymentAction, ...]
    complete: Literal[True]

    @model_validator(mode="before")
    @classmethod
    def strict_completion(cls, data):
        if not isinstance(data, dict) or data.get("complete") is not True:
            raise ValueError("deployment trace completion must be true")
        return data

    @model_validator(mode="after")
    def ordered_actions(self):
        if len(self.actions) > 64 or [a.sequence for a in self.actions] != list(range(1, len(self.actions) + 1)):
            raise ValueError("deployment action order is incomplete")
        for value in (self.context_hash, self.artifact_hash, self.state_hash, self.batch_hash,
                      self.request_sha256, self.response_sha256):
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("invalid deployment trace binding digest")
        return self


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
    # S43 (Gate 3 section 3.5): frozen task types the service's model may plan;
    # empty for missions that predate plan mode.
    task_vocabulary: dict[str, str] = {}


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


class SignalRecord(BaseModel):
    model_config = _FROZEN
    record_id: str = Field(min_length=1)
    entity_ref: str = Field(min_length=1)
    kind: Literal["signal"]
    value: dict[str, JsonValue]
    record_age_ms: StrictInt = Field(ge=0)
    dependency: Literal["enrichment"]

    @model_validator(mode="after")
    def usable_signal(self):
        SignalFacts.model_validate(self.value)
        return self


class PipelineSnapshot(BaseModel):
    model_config = _FROZEN
    engagement_slug: Literal["gtm"]
    display_name: str
    snapshot_version: StrictInt = Field(ge=1)
    review_status: str
    description: str
    observed_at: datetime
    timezone: str
    dependencies: dict[str, Literal["available", "unavailable"]]
    routing_rules: dict[str, str]
    entities: dict[str, SignalEntity]
    records: tuple[SignalRecord, ...]

    @model_validator(mode="after")
    def signal_inventory(self):
        routes = {region + "/" + product for region in ("APAC", "EMEA", "AMER")
                  for product in ("platform", "analytics")}
        if set(self.routing_rules) != routes or any(not owner or owner == "revenue-review" for owner in self.routing_rules.values()):
            raise ValueError("pipeline needs six explicit qualified routes")
        if set(self.dependencies) != {"enrichment"}:
            raise ValueError("pipeline dependency vocabulary must be enrichment")
        if len({r.record_id for r in self.records}) != len(self.records) or len({r.entity_ref for r in self.records}) != len(self.records):
            raise ValueError("pipeline signal identities must be unique")
        for record in self.records:
            entity = self.entities.get(record.entity_ref)
            facts = SignalFacts.model_validate(record.value)
            if entity is None or entity.domain != facts.account_domain:
                raise ValueError("signal evidence must bind its company domain")
            if facts.existing_record_ref is not None and facts.existing_record_ref != "pipeline:" + record.entity_ref:
                raise ValueError("existing pipeline reference must bind the signal")
        return self


def apply_pipeline_history(snapshot_bytes: bytes, owned: dict[str, JsonValue]) -> bytes:
    """Overlay verified synthetic ownership without changing reviewed source files."""
    snapshot = load_public_state_bytes(snapshot_bytes)
    if not isinstance(snapshot, PipelineSnapshot):
        raise PublicStateInvalid("pipeline history requires GTM state")
    for signal, record in owned.items():
        if (not isinstance(signal, str) or not signal.startswith("signal:")
                or not isinstance(record, dict) or set(record) != {"owner", "record_ref"}
                or not isinstance(record["owner"], str) or not record["owner"]
                or record["record_ref"] != "pipeline:" + signal):
            raise PublicStateInvalid("invalid inherited pipeline record")
    data = json.loads(snapshot_bytes)
    changed = False
    for record in data["records"]:
        prior = owned.get(record["entity_ref"])
        if prior is None:
            continue
        facts = record["value"]
        if facts["existing_owner"] is not None and (facts["existing_owner"] != prior["owner"]
                or facts["existing_record_ref"] != prior["record_ref"]):
            raise PublicStateInvalid("observed pipeline ownership contradicts history")
        facts.update(existing_owner=prior["owner"], existing_record_ref=prior["record_ref"])
        changed = True
    if not changed:
        return snapshot_bytes
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    load_public_state_bytes(encoded)
    return encoded


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
        raw = path.read_bytes()
    except OSError as exc:
        raise MissionSpecInvalid(f"mission {path.name} is not readable JSON: {exc}") from exc
    return load_mission_bytes(raw, label=path.name)


def load_mission_bytes(raw: bytes, *, label: str = "frozen mission bytes") -> MissionSpec:
    """The same fail-closed parse over bytes, for a context's frozen rubric.

    A run assesses against the bytes it froze, so the loader that guards the
    live file must also guard the frozen copy rather than a second, weaker parser.
    """
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionSpecInvalid(f"mission {label} is not readable JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise MissionSpecInvalid(f"mission {label} is not a JSON object")

    try:
        specs = tuple(
            CustomerRequestSpec.model_validate(item) for item in data["request_specs"]
        )
        codes = {
            code: ExplanationCode.model_validate({"code": code, **body})
            for code, body in data["explanation_codes"].items()
        }
        constants = data["constants"]
        if "task_vocabulary" in data and not data["task_vocabulary"]:
            raise MissionSpecInvalid(f"mission {label} declares an empty task vocabulary")
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
            task_vocabulary=data.get("task_vocabulary", {}),
            render_vocabulary=data["render_vocabulary"],
            evidence_limits=tuple(data["evidence_limits"]),
        )
    except ValidationError as exc:
        raise MissionSpecInvalid(
            f"mission {label} is not a usable rubric: {_validation_summary(exc)}"
        ) from exc
    except (KeyError, TypeError) as exc:
        raise MissionSpecInvalid(f"mission {label} is not a usable rubric: missing {exc}") from exc

    _check_mission(label, mission)
    return mission


def _check_mission(label: str, mission: MissionSpec) -> None:
    if not mission.request_specs:
        raise MissionSpecInvalid(f"mission {label} declares no request specs")
    if mission.max_record_age_ms <= 0:
        raise MissionSpecInvalid(f"mission {label} has a non-positive max_record_age_ms")
    if not mission.render_vocabulary:
        raise MissionSpecInvalid(f"mission {label} has no render vocabulary")

    seen_request_ids: set[str] = set()
    for spec in mission.request_specs:
        if spec.id in seen_request_ids:
            raise MissionSpecInvalid(f"mission {label} repeats request id {spec.id!r}")
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


def load_public_state(path: Path) -> ShopSnapshot | PipelineSnapshot:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PublicStateInvalid(f"public state {path.name} is not readable JSON: {exc}") from exc
    return load_public_state_bytes(raw, label=path.name)


def load_public_state_bytes(raw: bytes, *, label: str = "frozen public state bytes") -> ShopSnapshot | PipelineSnapshot:
    """The same fail-closed parse over bytes, for a context's frozen public state."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicStateInvalid(f"public state {label} is not readable JSON: {exc}") from exc
    try:
        model = PipelineSnapshot if isinstance(data, dict) and data.get("engagement_slug") == "gtm" else ShopSnapshot
        snapshot = model.model_validate(data)
    except ValidationError as exc:
        raise PublicStateInvalid(
            f"public state {label} is not usable: {_validation_summary(exc)}"
        ) from exc
    if not snapshot.records:
        raise PublicStateInvalid(f"public state {label} carries no records")
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
