"""Sealed-case loader (program design S3.3/S3.4/S5.3).

Controller-side only. ``load_drawn_cases`` is the approved run-scoped accessor:
it resolves the run's persisted rotation draws to exactly those variants, plus
the variants linked to still-open incidents, so a later run can re-score the
regression that an incident waits on. Draw selection itself is
``sealed.rotation`` policy; this module does the file and database reads.

A case file or individual case declaring an unknown schema version raises
``UnsupportedSealedSchema`` rather than being skipped, and a case whose
``request_ordinals`` list is empty or duplicated raises ``InvalidSealedCase``
rather than silently never scoring (program design S6 test 15). The bookshop
cases are agent-drafted; the user reviewed and sealed the ``stale_information``
family on 2026-09-18, and families 2 and 3 await the same operator review.
"""

import json
import sqlite3

from shiftwork import config
from shiftwork.domain.errors import InvalidSealedCase, UnsupportedSealedSchema
from shiftwork.domain.models import IncidentState
from shiftwork.evaluator.evaluator import SealedCase, SealedCaseSet
from shiftwork.sealed import rotation
from shiftwork.store import repo

STALE_INFORMATION = "stale_information"
POLICY_EXCEPTION = "policy_exception"
HOSTILE_INSTRUCTION = "hostile_instruction"

_FAMILY_FILES = {
    STALE_INFORMATION: "bookshop_stale_information.json",
    POLICY_EXCEPTION: "bookshop_policy_exception.json",
    HOSTILE_INSTRUCTION: "bookshop_hostile_instruction.json",
}
SUPPORTED_SCHEMA_VERSIONS = (1,)


def _raw_family(family: str) -> dict:
    path = config.SEALED_CASES_DIR / _FAMILY_FILES[family]
    data = json.loads(path.read_text(encoding="utf-8"))
    file_version = data.get("schema_version")
    if file_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnsupportedSealedSchema(
            f"sealed family {family!r} declares unsupported file schema_version {file_version!r}"
        )
    return data


def load_family(family: str) -> SealedCaseSet:
    data = _raw_family(family)
    cases = []
    for raw in data["cases"]:
        version = raw.get("schema_version")
        if version not in SUPPORTED_SCHEMA_VERSIONS:
            raise UnsupportedSealedSchema(
                f"sealed case {raw.get('id')!r} declares unsupported schema_version {version!r}"
            )
        ordinals = raw.get("request_ordinals")
        if (
            not isinstance(ordinals, list)
            or not ordinals
            or any(isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1 for ordinal in ordinals)
            or len(set(ordinals)) != len(ordinals)
        ):
            raise InvalidSealedCase(
                f"sealed case {raw.get('id')!r} needs a non-empty, duplicate-free list of "
                f"positive request ordinals; got {ordinals!r}"
            )
        cases.append(SealedCase.model_validate(raw))
    return SealedCaseSet(cases=tuple(cases))


def family_cycle(family: str) -> int:
    """The family's inventory generation; a refill appends variants and bumps this."""
    return int(_raw_family(family).get("cycle", 1))


def case_index() -> dict[str, SealedCase]:
    """Every case across the inventory, keyed by variant ref and by check id."""
    index: dict[str, SealedCase] = {}
    for family in _FAMILY_FILES:
        for case in load_family(family).cases:
            index[rotation.variant_ref(case)] = case
            index[case.check_id] = case
    return index


def case_for_check_id(check_id: str) -> SealedCase | None:
    return case_index().get(check_id)


def load_drawn_cases(conn: sqlite3.Connection, run_id: str) -> SealedCaseSet:
    """The cases this run evaluates: its persisted draws plus open-incident regressions.

    The draws are read back from ``rotation_draws`` - never re-selected - so a
    restart cannot redraw an exposed variant (program design S5.3, test 26). A
    regression case is included only while its incident is OPEN: once resolved,
    repeating the old stimulus is not part of a later run's evidence.
    """
    index = case_index()
    cases: list[SealedCase] = []
    seen: set[str] = set()

    def add(case: SealedCase) -> None:
        if case.check_id not in seen:
            seen.add(case.check_id)
            cases.append(case)

    for draw in repo.list_rotation_draws_for_run(conn, run_id):
        case = index.get(draw.variant_ref)
        if case is None:
            raise InvalidSealedCase(
                f"rotation draw {draw.id} references variant {draw.variant_ref!r}, "
                "which no sealed family file provides"
            )
        add(case)

    run = repo.get_run(conn, run_id)
    if run is None:
        raise InvalidSealedCase(f"unknown run: {run_id}")
    engagement_slug = run.shift_id.rsplit("-shift-", 1)[0]
    for incident in repo.list_incidents(conn, engagement_slug):
        if incident.state is not IncidentState.OPEN:
            continue
        failing = next(
            (
                result
                for result in repo.list_check_results(conn, incident.opening_run_id)
                if result.id == incident.check_result_id
            ),
            None,
        )
        if failing is None:
            raise InvalidSealedCase(
                f"incident {incident.id} links to check result {incident.check_result_id!r}, which its run does not carry"
            )
        case = index.get(failing.check_id)
        if case is None:
            raise InvalidSealedCase(
                f"incident {incident.id} links to sealed check {failing.check_id!r}, which no family file provides"
            )
        add(case)

    return SealedCaseSet(cases=tuple(cases))
