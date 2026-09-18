"""Pure reducer: observed check results to unchained ledger drafts (S3.4).

Slice 2 reduces ONE failing ``stale_information`` check into ONE
``BACKLOG_RECORDED`` draft. The reducer is pure: it reads the run, its check
results and the mission fixtures and emits ``LedgerEventDraft`` values with no
seq or hash. ``ledger.chain`` seals them afterward. Business consequences are
deterministic reductions of observed outputs and are labelled synthetic.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from shiftwork.domain.models import (
    CheckResult,
    JsonValue,
    LedgerEventDraft,
    LedgerEventType,
    ReasonCode,
    Run,
)

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class MissionConsequence(BaseModel):
    """Maps one failing reason code to a synthetic business consequence."""

    model_config = _FROZEN

    reason_code: ReasonCode
    event_type: LedgerEventType
    payload_template: dict[str, JsonValue]


class MissionFixtures(BaseModel):
    model_config = _FROZEN

    description: str | None = None
    engagement_slug: str
    version: int
    consequences: tuple[MissionConsequence, ...]


def load_mission(path: Path) -> MissionFixtures:
    data = json.loads(path.read_text(encoding="utf-8"))
    return MissionFixtures.model_validate(data)


def _consequence_for(
    mission: MissionFixtures, reason_code: ReasonCode
) -> MissionConsequence | None:
    return next(
        (item for item in mission.consequences if item.reason_code == reason_code),
        None,
    )


def reduce_run(
    mission: MissionFixtures,
    run: Run,
    check_results: list[CheckResult],
) -> list[LedgerEventDraft]:
    """Deterministically reduce failing checks into ledger event drafts."""
    drafts: list[LedgerEventDraft] = []
    for result in check_results:
        if result.verdict != "fail" or result.reason_code is None:
            continue
        consequence = _consequence_for(mission, result.reason_code)
        if consequence is None:
            continue
        drafts.append(
            LedgerEventDraft(
                event_type=consequence.event_type,
                cause_refs=(run.id, result.id, result.observed_ref),
                payload=dict(consequence.payload_template),
            )
        )
    return drafts
