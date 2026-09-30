"""Pure reducer: observed check results to unchained ledger drafts (S3.4).

The reducer is pure: it reads the run, its check results, the mission fixtures
and the committed contract and emits ``LedgerEventDraft`` values with no seq or
hash. ``ledger.chain`` seals them afterward inside the same finalization or
close transaction (S5.5, S5.8). Same inputs replay to identical drafts.

Mission fixtures are inspectable scenario rules (brief S5): ``weights`` are
integer weights per consequence key and ``transitions`` are symbolic rules of
the form ``"<REASON_CODE> -> <EVENT_TYPE> <consequence_key>"`` that the reducer
resolves. Business consequences are deterministic reductions of observed
outputs and are labelled synthetic.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from shiftwork.domain.models import (
    CheckResult,
    CloseShiftFacts,
    ContractParams,
    JsonValue,
    LedgerEventDraft,
    LedgerEventType,
    OperationalAssessment,
    ReasonCode,
    Run,
    RunPurpose,
    RunOutput,
)
from shiftwork.domain.task_contract import MissionSpec, TaskAssessment
from shiftwork.evaluator import evaluator

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class MissionFixtures(BaseModel):
    model_config = _FROZEN

    description: str | None = None
    engagement_slug: str
    version: int
    weights: dict[str, int]
    transitions: tuple[str, ...]


class MissionTransition(BaseModel):
    """One resolved symbolic transition rule."""

    model_config = _FROZEN

    reason_code: ReasonCode
    event_type: LedgerEventType
    consequence_key: str


def load_mission(path: Path) -> MissionFixtures:
    data = json.loads(path.read_text(encoding="utf-8"))
    return MissionFixtures.model_validate(data)


def resolve_transitions(mission: MissionFixtures) -> tuple[MissionTransition, ...]:
    """Parse every symbolic transition line; unknown codes/types are hard errors."""
    resolved: list[MissionTransition] = []
    for line in mission.transitions:
        head, _, tail = line.partition("->")
        if not _:
            raise ValueError(f"malformed mission transition (missing '->'): {line!r}")
        parts = tail.strip().split()
        if len(parts) != 2:
            raise ValueError(f"malformed mission transition body: {line!r}")
        event_type, consequence_key = parts
        resolved.append(
            MissionTransition(
                reason_code=ReasonCode(head.strip()),
                event_type=LedgerEventType(event_type),
                consequence_key=consequence_key,
            )
        )
    return tuple(resolved)


def _weight(mission: MissionFixtures, key: str) -> int:
    if key not in mission.weights:
        raise ValueError(f"mission transition references unknown weight key: {key!r}")
    return mission.weights[key]


def transition_for(
    mission: MissionFixtures, reason_code: ReasonCode
) -> MissionTransition | None:
    return next(
        (item for item in resolve_transitions(mission) if item.reason_code == reason_code),
        None,
    )


def _draft_for(
    mission: MissionFixtures,
    transition: MissionTransition,
    cause_refs: tuple[str, ...],
    catalog_version: int,
) -> LedgerEventDraft:
    payload: dict[str, JsonValue] = {
        "consequence": transition.consequence_key,
        "weight": _weight(mission, transition.consequence_key),
        "catalog_version": catalog_version,
    }
    return LedgerEventDraft(
        event_type=transition.event_type,
        cause_refs=cause_refs,
        payload=payload,
    )


def reduce(
    mission: MissionFixtures,
    raw_outputs: list[RunOutput] | tuple[RunOutput, ...],
    check_results: list[CheckResult] | tuple[CheckResult, ...],
    committed_contract: ContractParams,
) -> list[LedgerEventDraft]:
    """Deterministically reduce failing checks into unchained ledger drafts."""
    del raw_outputs  # drafts derive from check results; outputs stay as evidence refs
    drafts: list[LedgerEventDraft] = []
    for result in check_results:
        if result.verdict != "fail" or result.reason_code is None:
            continue
        transition = transition_for(mission, result.reason_code)
        if transition is None:
            continue
        drafts.append(
            _draft_for(
                mission,
                transition,
                (result.run_id, result.id, result.observed_ref),
                committed_contract.catalog_version,
            )
        )
    return drafts


def reduce_operation(
    run: Run, assessment: OperationalAssessment, mission: MissionSpec,
    task_assessments: tuple[TaskAssessment, ...], checks: tuple[CheckResult, ...],
) -> list[LedgerEventDraft]:
    """Derive labelled synthetic order and incident drafts from one selected run."""
    if (run.purpose is not RunPurpose.OPERATION or run.selection_id is None
            or assessment.purpose is not RunPurpose.OPERATION
            or assessment.selection_id != run.selection_id
            or assessment.run_id != run.id):
        raise ValueError("business reduction requires the selected operational run")
    drafts: list[LedgerEventDraft] = []
    by_task = {check.check_id: check for check in checks}
    for index, spec in enumerate(mission.request_specs, start=1):
        required = {task.id for task in spec.tasks if task.required}
        rows = [row for row in task_assessments if row.request_ordinal == index]
        if required and evaluator.request_usefully_completed(spec, rows):
            source = by_task[f"task:{spec.id}:{sorted(required)[0]}"]
            drafts.append(LedgerEventDraft(
                event_type=LedgerEventType.SALE_COMPLETED,
                cause_refs=(run.id, source.id, source.observed_ref),
                payload={"synthetic_orders": 1, "mission_version": mission.version,
                         "rule_version": assessment.rule_version},
            ))
        else:
            for row in rows:
                if row.task_id in required and not row.mandatory_pass:
                    source = by_task[f"task:{row.request_id}:{row.task_id}"]
                    drafts.append(LedgerEventDraft(
                        event_type=LedgerEventType.INCIDENT_OPENED,
                        cause_refs=(run.id, source.id, source.observed_ref),
                        payload={"reason_code": (row.reason_codes[0].value if row.reason_codes
                                                  else ReasonCode.REQUIRED_TASK_MISSING.value),
                                 "mission_version": mission.version,
                                 "rule_version": assessment.rule_version},
                    ))
    return drafts


def reduce_close(
    mission: MissionFixtures,
    facts: CloseShiftFacts,
) -> list[LedgerEventDraft]:
    """Reduce shift-close facts into LIMIT_DECLARED drafts (S5.8).

    Only ``declared_limits`` produce events; unresolved incidents are inherited
    as incident rows by the close transaction, never as LIMIT_DECLARED events.
    """
    del mission  # close drafts carry no consequence weight
    drafts: list[LedgerEventDraft] = []
    for limit in facts.declared_limits:
        drafts.append(
            LedgerEventDraft(
                event_type=LedgerEventType.LIMIT_DECLARED,
                cause_refs=(facts.shift_id,),
                payload={
                    "declared_limit": limit,
                    "catalog_version": facts.committed_contract.catalog_version,
                },
            )
        )
    return drafts
