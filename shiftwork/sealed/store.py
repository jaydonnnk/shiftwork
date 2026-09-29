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
family on 2026-09-18, and sealed the ``policy_exception`` and ``hostile_instruction``
families on 2026-09-20.
"""

import json
import hashlib
import sqlite3
from typing import NamedTuple

from shiftwork import config
from shiftwork.domain.errors import InvalidSealedCase, UnsupportedSealedSchema
from shiftwork.domain.models import IncidentState, RunPurpose
from shiftwork.domain import task_contract
from shiftwork.evaluator.evaluator import SealedCase, SealedCaseSet
from shiftwork.sealed import rotation
from shiftwork.store import repo

STALE_INFORMATION = "stale_information"
POLICY_EXCEPTION = "policy_exception"
HOSTILE_INSTRUCTION = "hostile_instruction"
# The comparison-scoped family (Slice 15). Its variants are not attempt stimuli:
# a qualifying comparison reserves one never-exposed variant per pair and both
# candidate slots in that pair share it. It is listed here so the loader, the
# cycle reader and the projection needles cover it like any other family.
TASK_COMPLETION = "task_completion"

_FAMILY_FILES = {
    STALE_INFORMATION: "bookshop_stale_information.json",
    POLICY_EXCEPTION: "bookshop_policy_exception.json",
    HOSTILE_INSTRUCTION: "bookshop_hostile_instruction.json",
    TASK_COMPLETION: "bookshop_task_completion.json",
}
SUPPORTED_SCHEMA_VERSIONS = (1,)


def private_storage_locator() -> str:
    """A private path needle for controller projection checks, never for clients."""
    return str(config.SEALED_CASES_DIR)


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
    if family != TASK_COMPLETION and any(case.stimulus is not None for case in cases):
        raise InvalidSealedCase("attempt family cannot carry protected comparison stimulus")
    return SealedCaseSet(cases=tuple(cases))


def load_reviewed_comparison_family(family: str) -> SealedCaseSet:
    """Admit a comparison family only after its exact cases have an operator seal."""
    data = _raw_family(family)
    cases = data.get("cases")
    digest = hashlib.sha256(
        json.dumps(cases, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if data.get("review_status") != "OPERATOR_SEALED" or data.get("sealed_payload_sha256") != digest:
        raise InvalidSealedCase(f"comparison family {family!r} awaits operator review and sealing")
    loaded = load_family(family)
    if any(case.stimulus is None for case in loaded.cases):
        raise InvalidSealedCase("reviewed comparison case lacks protected stimulus")
    request_ids = [case.stimulus.request.request_id for case in loaded.cases]
    if len(set(request_ids)) != len(request_ids):
        raise InvalidSealedCase("reviewed comparison variants reuse a protected request id")
    return loaded


def family_cycle(family: str) -> int:
    """The family's inventory generation; a refill appends variants and bumps this."""
    return int(_raw_family(family).get("cycle", 1))


class ReservedProtectedCase(NamedTuple):
    family: str
    pair_ordinal: int
    case: SealedCase
    resolved_state_bytes: bytes
    resolved_state_sha256: str


def load_reserved_comparison_cases(
    conn: sqlite3.Connection, reservation_id: str,
) -> tuple[ReservedProtectedCase, ...]:
    """Reconstruct exact protected cases from the reservation, never an editable file."""
    rows = repo.list_protected_case_snapshots(conn, reservation_id)
    if not rows:
        raise InvalidSealedCase(f"comparison reservation {reservation_id!r} has no protected cases")
    result = []
    for row in rows:
        payload = row["payload_json"]
        if payload is None or row["variant_ref"] != row["exposure_ref"]:
            raise InvalidSealedCase("comparison reservation has a missing or mismatched case snapshot")
        if hashlib.sha256(payload.encode("utf-8")).hexdigest() != row["payload_sha256"]:
            raise InvalidSealedCase("comparison case snapshot digest mismatch")
        case = SealedCase.model_validate(json.loads(payload))
        if case.family != row["family"] or rotation.variant_ref(case) != row["variant_ref"]:
            raise InvalidSealedCase("comparison case snapshot identity mismatch")
        if case.stimulus is None or row["resolved_state_bytes"] is None:
            raise InvalidSealedCase("comparison case snapshot lacks protected stimulus")
        if hashlib.sha256(row["resolved_state_bytes"]).hexdigest() != row["resolved_state_sha256"]:
            raise InvalidSealedCase("comparison resolved state digest mismatch")
        result.append(ReservedProtectedCase(
            row["family"], row["pair_ordinal"], case,
            row["resolved_state_bytes"], row["resolved_state_sha256"],
        ))
    return tuple(result)


def load_reserved_protected_state(conn: sqlite3.Connection, reservation_id: str,
                                  pair_ordinal: int) -> bytes:
    rows = [row for row in repo.list_protected_case_snapshots(conn, reservation_id)
            if row["pair_ordinal"] == pair_ordinal]
    if len(rows) != 1:
        raise InvalidSealedCase("comparison pair has no unique protected snapshot")
    row = rows[0]
    if hashlib.sha256(row["resolved_state_bytes"]).hexdigest() != row["resolved_state_sha256"]:
        raise InvalidSealedCase("comparison resolved state digest mismatch")
    task_contract.load_public_state_bytes(row["resolved_state_bytes"])
    return row["resolved_state_bytes"]


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
    """The cases this run evaluates: its persisted draws plus unresolved regressions.

    The draws are read back from ``rotation_draws`` - never re-selected - so a
    restart cannot redraw an exposed variant (program design S5.3, test 26). A
    regression case is included while its incident is unresolved (OPEN or the
    CLOSED_UNRESOLVED state a close leaves it in): the inherited incident still
    waits on that regression, and a resolved incident's stimulus is not part of
    a later run's evidence (program design S3.9, S5.7).
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
        if incident.state is IncidentState.RESOLVED:
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
            opening = repo.get_run(conn, incident.opening_run_id)
            if opening is not None and opening.purpose is RunPurpose.LEGACY_OPERATION:
                # Historical v5 checks have no current sealed case. Keep the
                # incident unresolved rather than inventing a passing regression.
                continue
            raise InvalidSealedCase(
                f"incident {incident.id} links to sealed check {failing.check_id!r}, which no family file provides"
            )
        add(case)

    return SealedCaseSet(cases=tuple(cases))
