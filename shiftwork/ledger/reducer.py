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
from shiftwork.domain.task_contract import DeploymentTrace, MissionSpec, TaskAssessment, TaskKind
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
    *, consequence_rules: dict[str, JsonValue] | None = None,
    weights: dict[str, int] | None = None,
    deployment_traces: tuple[DeploymentTrace, ...] = (),
) -> list[LedgerEventDraft]:
    """Derive labelled synthetic order and incident drafts from one selected run."""
    if (run.purpose is not RunPurpose.OPERATION or run.selection_id is None
            or assessment.purpose is not RunPurpose.OPERATION
            or assessment.selection_id != run.selection_id
            or assessment.run_id != run.id):
        raise ValueError("business reduction requires the selected operational run")
    if consequence_rules is not None:
        return _reduce_pack_operation(run, assessment, mission, task_assessments, checks,
                                      consequence_rules, weights or {}, deployment_traces)
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


def _reduce_pack_operation(run, assessment, mission, task_assessments, checks,
                           rules, weights, traces) -> list[LedgerEventDraft]:
    """Reduce frozen pack rules; a rollout arm never publishes partial pilot state."""
    by_check = {check.check_id: check for check in checks}
    expected = {f"task:{spec.id}:{task.id}" for spec in mission.request_specs for task in spec.tasks}
    rows_by_request = {index: tuple(row for row in task_assessments if row.request_ordinal == index)
                       for index in range(1, len(mission.request_specs) + 1)}
    full_acceptance = (
        assessment.mandatory_pass
        and assessment.expected_request_count == len(mission.request_specs)
        and assessment.complete_request_count == len(mission.request_specs)
        and len(checks) == len(by_check) and set(by_check) == expected
        and all(check.verdict == "pass" for check in checks)
        and len(task_assessments) == len(expected)
        and all({row.task_id for row in rows_by_request[index]} == {task.id for task in spec.tasks}
                and all(row.request_id == spec.id for row in rows_by_request[index])
                and evaluator.request_usefully_completed(spec, rows_by_request[index])
                for index, spec in enumerate(mission.request_specs, 1))
    )
    rollout = rules["rollout_event"]
    allow_success = rollout is None or full_acceptance
    base = {"mission_version": mission.version, "rule_version": assessment.rule_version,
            "catalog_version": mission.contract_catalog_version}
    drafts: list[LedgerEventDraft] = []

    def declared(rule, source):
        event, key = rule.split()
        weight = weights[key]
        if type(weight) is not int:
            raise ValueError("consequence weight must be an integer")
        return LedgerEventDraft(event_type=LedgerEventType(event),
            cause_refs=(run.id, source.id, source.observed_ref),
            payload={**base, "consequence": key, "weight": weight})

    for index, spec in enumerate(mission.request_specs, 1):
        rows = rows_by_request[index]
        required = {task.id for task in spec.tasks if task.required}
        if allow_success and required and evaluator.request_usefully_completed(spec, rows):
            source = by_check[f"task:{spec.id}:{sorted(required)[0]}"]
            for rule in rules["success_events"]:
                # A mechanic route cannot be presented as a booking.
                if rule.startswith("BOOKING_COMMITTED ") and not any(
                        task.required and task.kind is TaskKind.CREATE_BOOKING for task in spec.tasks):
                    continue
                drafts.append(declared(rule, source))
            if any(task.required and task.kind is TaskKind.ROUTE_SAFETY_QUESTION for task in spec.tasks):
                drafts.append(LedgerEventDraft(event_type=LedgerEventType.ESCALATION_TO_HUMAN,
                    cause_refs=(run.id, source.id, source.observed_ref), payload=dict(base)))
            trace = next((trace for trace in traces if trace.request_ordinal == index), None)
            rollbacks = [a for a in trace.actions if a.kind == "ROLLBACK"] if trace else []
            if rollbacks:
                drafts.append(LedgerEventDraft(event_type=LedgerEventType.COUNTER_FOLLOWUP_RECORDED,
                    cause_refs=(run.id, source.id, source.observed_ref),
                    payload={**base, "request_id": spec.id,
                             "rollback_receipts": [a.details["receipt"] for a in rollbacks]}))
        # Failed required tasks and independent failed checks stay incidents.
        failed = {f"task:{row.request_id}:{row.task_id}" for row in rows
                  if row.task_id in required and not row.mandatory_pass}
        failed.update(check.check_id for check in checks
                      if check.check_id.startswith(f"task:{spec.id}:") and check.verdict == "fail")
        for check_id in sorted(failed):
            source = by_check[check_id]
            drafts.append(LedgerEventDraft(event_type=LedgerEventType.INCIDENT_OPENED,
                cause_refs=(run.id, source.id, source.observed_ref),
                payload={**base, "reason_code": (source.reason_code or ReasonCode.REQUIRED_TASK_MISSING).value}))
    if rollout is not None and full_acceptance:
        source = checks[0]
        drafts.append(declared(rollout, source))
    return drafts


def reduce_close(
    mission: MissionFixtures | MissionSpec,
    facts: CloseShiftFacts,
    *, handover_record_required: bool = False,
) -> list[LedgerEventDraft]:
    """Reduce shift-close facts into LIMIT_DECLARED drafts (S5.8).

    Only ``declared_limits`` produce events; unresolved incidents are inherited
    as incident rows by the close transaction, never as LIMIT_DECLARED events.
    """
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
    if handover_record_required:
        if facts.handover_runbook_version_id is None:
            raise ValueError("required handover runbook reference missing")
        drafts.append(LedgerEventDraft(event_type=LedgerEventType.HANDOVER_DECLARED,
            cause_refs=(facts.shift_id, facts.handover_runbook_version_id),
            payload={"runbook_version_id": facts.handover_runbook_version_id,
                     "declared_limits": list(facts.declared_limits),
                     "unresolved_incident_ids": list(facts.unresolved_incident_ids),
                     "mission_version": mission.version}))
    return drafts
