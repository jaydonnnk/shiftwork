"""Raw parameterized SQL, one group per table. Rows are validated into domain models.

Slice 2 replaces this tracer repository with the approved schema and repo groups.
"""

import json
import sqlite3
from datetime import datetime

from shiftwork.domain import canonical
from shiftwork.domain.errors import VersionTampered
from shiftwork.domain.models import (
    ArtifactVersion,
    CheckResult,
    ContractParams,
    DrawState,
    EvidenceMode,
    Incident,
    IncidentState,
    LedgerEvent,
    LedgerEventType,
    OperatingSelection,
    ReasonCode,
    RotationDraw,
    Run,
    RunOutput,
    RunPurpose,
    RunState,
    Shift,
)


def _dump(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _load(raw: str):
    return json.loads(raw)


# --- engagements -----------------------------------------------------------


def seed_engagement(conn: sqlite3.Connection, slug: str, business_kind: str, display_name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO engagements (slug, business_kind, display_name) VALUES (?, ?, ?)",
        (slug, business_kind, display_name),
    )
    conn.commit()


def get_engagement(conn: sqlite3.Connection, slug: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM engagements WHERE slug = ?", (slug,)).fetchone()


# --- engagement_config -----------------------------------------------------


def seed_engagement_config(
    conn: sqlite3.Connection,
    slug: str,
    *,
    business_kind: str,
    assist_level: str,
    allowed_assist_roles: tuple[str, ...],
    total_assist_budget_per_shift: int,
    enabled_check_families: tuple[str, ...],
    attempt_limit: int,
    rotation_group_size: int,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO engagement_config (slug, business_kind, assist_level, "
        "allowed_assist_roles_json, total_assist_budget_per_shift, enabled_check_families_json, "
        "attempt_limit, rotation_group_size) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            slug,
            business_kind,
            assist_level,
            _dump(list(allowed_assist_roles)),
            total_assist_budget_per_shift,
            _dump(list(enabled_check_families)),
            attempt_limit,
            rotation_group_size,
        ),
    )
    conn.commit()


def get_engagement_config(conn: sqlite3.Connection, slug: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM engagement_config WHERE slug = ?", (slug,)).fetchone()


# --- shifts ----------------------------------------------------------------


def _shift(conn: sqlite3.Connection, row: sqlite3.Row) -> Shift:
    selection = get_latest_operating_selection(conn, row["engagement_slug"])
    return Shift(
        id=row["id"],
        engagement_slug=row["engagement_slug"],
        seq=row["seq"],
        state=row["state"],
        opened_at=row["opened_at"],
        closed_at=row["closed_at"],
        opening_mode=row["opening_mode"],
        operation_allowed=(
            row["state"] == "open" and selection is not None and selection.state == "VALID"
        ),
    )


def insert_shift(conn: sqlite3.Connection, shift: Shift) -> None:
    conn.execute(
        "INSERT INTO shifts (id, engagement_slug, seq, state, opened_at, closed_at, opening_mode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            shift.id,
            shift.engagement_slug,
            shift.seq,
            shift.state,
            shift.opened_at.isoformat(),
            shift.closed_at.isoformat() if shift.closed_at else None,
            shift.opening_mode.value if shift.opening_mode else None,
        ),
    )


def get_shift(conn: sqlite3.Connection, shift_id: str) -> Shift | None:
    row = conn.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
    return _shift(conn, row) if row else None


def get_latest_shift(conn: sqlite3.Connection, slug: str) -> Shift | None:
    row = conn.execute(
        "SELECT * FROM shifts WHERE engagement_slug = ? ORDER BY seq DESC LIMIT 1", (slug,)
    ).fetchone()
    return _shift(conn, row) if row else None


def max_shift_seq(conn: sqlite3.Connection, slug: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) AS n FROM shifts WHERE engagement_slug = ?", (slug,)
    ).fetchone()
    return int(row["n"])


def close_shift(conn: sqlite3.Connection, shift_id: str, closed_at: datetime) -> None:
    conn.execute(
        "UPDATE shifts SET state = 'closed', closed_at = ? WHERE id = ?",
        (closed_at.isoformat(), shift_id),
    )


# --- draft_artifacts -------------------------------------------------------


def upsert_draft(
    conn: sqlite3.Connection,
    shift_id: str,
    files: dict[str, str],
    updated_at: datetime,
    base_version_id: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO draft_artifacts (shift_id, files_json, updated_at, base_version_id) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(shift_id) DO UPDATE SET files_json = excluded.files_json, updated_at = excluded.updated_at",
        (shift_id, _dump(files), updated_at.isoformat(), base_version_id),
    )


def get_draft(conn: sqlite3.Connection, shift_id: str) -> tuple[dict[str, str], str] | None:
    row = conn.execute(
        "SELECT files_json, updated_at FROM draft_artifacts WHERE shift_id = ?", (shift_id,)
    ).fetchone()
    if row is None:
        return None
    return _load(row["files_json"]), row["updated_at"]


def get_draft_base_version_id(conn: sqlite3.Connection, shift_id: str) -> str | None:
    row = conn.execute(
        "SELECT base_version_id FROM draft_artifacts WHERE shift_id = ?", (shift_id,)
    ).fetchone()
    return row["base_version_id"] if row else None


# --- artifact_versions -----------------------------------------------------


def _contract_from_json(raw: str) -> ContractParams:
    return ContractParams.model_validate(_load(raw))


def _version(row: sqlite3.Row) -> ArtifactVersion:
    files = _load(row["files_json"])
    contract = _contract_from_json(row["contract_json"])
    contract_catalog_hash = row["contract_catalog_hash"]
    recorded_hash = row["content_hash"]
    recomputed = canonical.artifact_content_hash(
        files, canonical.contract_params_json(contract), contract_catalog_hash
    )
    if recomputed != recorded_hash:
        raise VersionTampered(
            f"artifact version {row['id']} no longer reproduces its recorded content hash"
        )
    return ArtifactVersion(
        id=row["id"],
        shift_id=row["shift_id"],
        parent_id=row["parent_id"],
        content_hash=recorded_hash,
        storage_ref=row["storage_ref"],
        files=files,
        contract=contract,
        contract_catalog_hash=contract_catalog_hash,
        created_by=row["created_by"],
        created_at=row["created_at"],
    )


def insert_version(conn: sqlite3.Connection, version: ArtifactVersion) -> None:
    conn.execute(
        "INSERT INTO artifact_versions (id, shift_id, parent_id, content_hash, storage_ref, "
        "files_json, contract_json, contract_catalog_hash, created_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            version.id,
            version.shift_id,
            version.parent_id,
            version.content_hash,
            version.storage_ref,
            _dump(version.files),
            _dump(canonical.contract_params_json(version.contract)),
            version.contract_catalog_hash,
            version.created_by,
            version.created_at.isoformat(),
        ),
    )


def get_version(conn: sqlite3.Connection, version_id: str) -> ArtifactVersion | None:
    row = conn.execute("SELECT * FROM artifact_versions WHERE id = ?", (version_id,)).fetchone()
    return _version(row) if row else None


def get_latest_version(conn: sqlite3.Connection, shift_id: str) -> ArtifactVersion | None:
    row = conn.execute(
        "SELECT * FROM artifact_versions WHERE shift_id = ? ORDER BY rowid DESC LIMIT 1", (shift_id,)
    ).fetchone()
    return _version(row) if row else None


def get_latest_version_for_engagement(conn: sqlite3.Connection, slug: str) -> ArtifactVersion | None:
    row = conn.execute(
        "SELECT v.* FROM artifact_versions v JOIN shifts s ON s.id = v.shift_id "
        "WHERE s.engagement_slug = ? ORDER BY v.rowid DESC LIMIT 1",
        (slug,),
    ).fetchone()
    return _version(row) if row else None


def count_versions(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) AS n FROM artifact_versions").fetchone()["n"])


# --- operating selections --------------------------------------------------


def _operating_selection(row: sqlite3.Row) -> OperatingSelection:
    return OperatingSelection(
        id=row["id"],
        engagement_slug=row["engagement_slug"],
        shift_id=row["shift_id"],
        kind=row["kind"],
        selected_version_id=row["selected_version_id"],
        selected_content_hash=row["selected_content_hash"],
        comparison_id=row["comparison_id"],
        retained_alternative_version_id=row["retained_alternative_version_id"],
        rationale=row["rationale"],
        requirement_set_hash=row["requirement_set_hash"],
        prior_selection_id=row["prior_selection_id"],
        state=row["state"],
        client_request_id=row["client_request_id"],
        created_at=row["created_at"],
    )


def get_latest_operating_selection(
    conn: sqlite3.Connection, slug: str
) -> OperatingSelection | None:
    row = conn.execute(
        "SELECT * FROM operating_selections WHERE engagement_slug = ? "
        "ORDER BY rowid DESC LIMIT 1",
        (slug,),
    ).fetchone()
    return _operating_selection(row) if row else None


def count_operating_selections(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) AS n FROM operating_selections").fetchone()["n"])


def insert_operating_selection(conn: sqlite3.Connection, selection: OperatingSelection) -> None:
    conn.execute(
        "INSERT INTO operating_selections "
        "(id, engagement_slug, shift_id, kind, selected_version_id, "
        "selected_content_hash, comparison_id, retained_alternative_version_id, "
        "rationale, requirement_set_hash, prior_selection_id, state, "
        "client_request_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            selection.id,
            selection.engagement_slug,
            selection.shift_id,
            selection.kind,
            selection.selected_version_id,
            selection.selected_content_hash,
            selection.comparison_id,
            selection.retained_alternative_version_id,
            selection.rationale,
            selection.requirement_set_hash,
            selection.prior_selection_id,
            selection.state,
            selection.client_request_id,
            selection.created_at.isoformat(),
        ),
    )


# --- runs ------------------------------------------------------------------


def _run(row: sqlite3.Row) -> Run:
    return Run(
        id=row["id"],
        shift_id=row["shift_id"],
        artifact_version_id=row["artifact_version_id"],
        request_batch_ref=row["request_batch_ref"],
        shop_snapshot_ref=row["shop_snapshot_ref"],
        attempt_number=row["attempt_number"],
        state=RunState(row["state"]),
        adapter=row["adapter"],
        failure_kind=row["failure_kind"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        purpose=RunPurpose(row["purpose"]),
        evidence_mode=EvidenceMode(row["evidence_mode"]) if row["evidence_mode"] else None,
        selection_id=row["selection_id"],
    )


def insert_run(conn: sqlite3.Connection, run: Run) -> None:
    conn.execute(
        "INSERT INTO runs (id, shift_id, artifact_version_id, request_batch_ref, shop_snapshot_ref, "
        "attempt_number, state, adapter, failure_kind, started_at, ended_at, purpose, "
        "evidence_mode, selection_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run.id,
            run.shift_id,
            run.artifact_version_id,
            run.request_batch_ref,
            run.shop_snapshot_ref,
            run.attempt_number,
            run.state.value,
            run.adapter,
            run.failure_kind.value if run.failure_kind else None,
            run.started_at.isoformat(),
            run.ended_at.isoformat() if run.ended_at else None,
            run.purpose.value,
            run.evidence_mode.value if run.evidence_mode else None,
            run.selection_id,
        ),
    )


def update_run(
    conn: sqlite3.Connection,
    run_id: str,
    state: RunState,
    failure_kind=None,
    ended_at: datetime | None = None,
) -> None:
    conn.execute(
        "UPDATE runs SET state = ?, failure_kind = ?, ended_at = ? WHERE id = ?",
        (
            state.value,
            failure_kind.value if failure_kind else None,
            ended_at.isoformat() if ended_at else None,
            run_id,
        ),
    )


def get_run(conn: sqlite3.Connection, run_id: str) -> Run | None:
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return _run(row) if row else None


def set_run_snapshot_bytes(conn: sqlite3.Connection, run_id: str, snapshot_bytes: bytes) -> None:
    """Persist the shop snapshot bytes the run executes against (Slice 9).

    Captured once, before the adapter runs, so every later read - transcript
    selection, scoring and the client's historical comparison - resolves the same
    bytes even if the configured source path is edited or removed afterwards.
    """
    conn.execute("UPDATE runs SET shop_snapshot_bytes = ? WHERE id = ?", (snapshot_bytes, run_id))


def get_run_snapshot_bytes(conn: sqlite3.Connection, run_id: str) -> bytes | None:
    """The run's captured snapshot bytes, or None for runs that predate the capture."""
    row = conn.execute("SELECT shop_snapshot_bytes FROM runs WHERE id = ?", (run_id,)).fetchone()
    return row["shop_snapshot_bytes"] if row else None


def get_latest_run(conn: sqlite3.Connection, shift_id: str) -> Run | None:
    row = conn.execute(
        "SELECT * FROM runs WHERE shift_id = ? ORDER BY attempt_number DESC LIMIT 1", (shift_id,)
    ).fetchone()
    return _run(row) if row else None


def count_runs(conn: sqlite3.Connection, shift_id: str) -> int:
    return int(
        conn.execute("SELECT COUNT(*) AS n FROM runs WHERE shift_id = ?", (shift_id,)).fetchone()["n"]
    )


def list_runs(conn: sqlite3.Connection, slug: str) -> list[Run]:
    rows = conn.execute(
        "SELECT r.* FROM runs r JOIN shifts s ON s.id = r.shift_id "
        "WHERE s.engagement_slug = ? ORDER BY r.rowid",
        (slug,),
    ).fetchall()
    return [_run(row) for row in rows]


def count_runs_all(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"])


def list_runs_for_shift(conn: sqlite3.Connection, shift_id: str) -> list[Run]:
    rows = conn.execute(
        "SELECT * FROM runs WHERE shift_id = ? ORDER BY attempt_number", (shift_id,)
    ).fetchall()
    return [_run(row) for row in rows]


def list_nonterminal_runs(conn: sqlite3.Connection) -> list[Run]:
    """Every run the controller has not finished with (startup recovery, S6.B.9)."""
    rows = conn.execute(
        "SELECT * FROM runs WHERE state NOT IN (?, ?) ORDER BY rowid",
        (RunState.FINALIZED.value, RunState.FAILED.value),
    ).fetchall()
    return [_run(row) for row in rows]


# --- run_outputs -----------------------------------------------------------


def _output(row: sqlite3.Row) -> RunOutput:
    return RunOutput(
        id=row["id"],
        run_id=row["run_id"],
        request_ordinal=row["request_ordinal"],
        request_text=row["request_text"],
        http_status=row["http_status"],
        body=row["body"],
        elapsed_ms=row["elapsed_ms"],
        transport_error=row["transport_error"],
        log_ref=row["log_ref"],
    )


def insert_output(conn: sqlite3.Connection, output: RunOutput) -> None:
    conn.execute(
        "INSERT INTO run_outputs (id, run_id, request_ordinal, request_text, http_status, body, elapsed_ms, transport_error, log_ref) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            output.id,
            output.run_id,
            output.request_ordinal,
            output.request_text,
            output.http_status,
            output.body,
            output.elapsed_ms,
            output.transport_error.value if output.transport_error else None,
            output.log_ref,
        ),
    )


def list_outputs(conn: sqlite3.Connection, run_id: str) -> list[RunOutput]:
    rows = conn.execute(
        "SELECT * FROM run_outputs WHERE run_id = ? ORDER BY request_ordinal", (run_id,)
    ).fetchall()
    return [_output(row) for row in rows]


# --- check_results ---------------------------------------------------------


def _check_result(row: sqlite3.Row) -> CheckResult:
    return CheckResult(
        id=row["id"],
        run_id=row["run_id"],
        check_id=row["check_id"],
        verdict=row["verdict"],
        observed_ref=row["observed_ref"],
        expected_ref=row["expected_ref"],
        reason_code=ReasonCode(row["reason_code"]) if row["reason_code"] else None,
    )


def insert_check_result(conn: sqlite3.Connection, check_result: CheckResult) -> None:
    conn.execute(
        "INSERT INTO check_results (id, run_id, check_id, verdict, observed_ref, expected_ref, reason_code) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            check_result.id,
            check_result.run_id,
            check_result.check_id,
            check_result.verdict,
            check_result.observed_ref,
            check_result.expected_ref,
            check_result.reason_code.value if check_result.reason_code else None,
        ),
    )


def list_check_results(conn: sqlite3.Connection, run_id: str) -> list[CheckResult]:
    rows = conn.execute("SELECT * FROM check_results WHERE run_id = ? ORDER BY rowid", (run_id,)).fetchall()
    return [_check_result(row) for row in rows]


def count_check_results(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) AS n FROM check_results").fetchone()["n"])


# --- incidents -------------------------------------------------------------


def _incident(row: sqlite3.Row) -> Incident:
    return Incident(
        id=row["id"],
        engagement_slug=row["engagement_slug"],
        shift_id=row["shift_id"],
        opening_run_id=row["opening_run_id"],
        failing_output_ref=row["failing_output_ref"],
        check_result_id=row["check_result_id"],
        reason_code=ReasonCode(row["reason_code"]),
        opened_event_seq=row["opened_event_seq"],
        state=IncidentState(row["state"]),
        resolving_version_id=row["resolving_version_id"],
        resolved_event_seq=row["resolved_event_seq"],
    )


def insert_incident(conn: sqlite3.Connection, incident: Incident) -> None:
    conn.execute(
        "INSERT INTO incidents (id, engagement_slug, shift_id, opening_run_id, failing_output_ref, "
        "check_result_id, reason_code, opened_event_seq, state, resolving_version_id, resolved_event_seq) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            incident.id,
            incident.engagement_slug,
            incident.shift_id,
            incident.opening_run_id,
            incident.failing_output_ref,
            incident.check_result_id,
            incident.reason_code.value,
            incident.opened_event_seq,
            incident.state.value,
            incident.resolving_version_id,
            incident.resolved_event_seq,
        ),
    )


def get_incident(conn: sqlite3.Connection, incident_id: str) -> Incident | None:
    row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    return _incident(row) if row else None


def list_incidents(conn: sqlite3.Connection, slug: str) -> list[Incident]:
    rows = conn.execute(
        "SELECT * FROM incidents WHERE engagement_slug = ? ORDER BY rowid", (slug,)
    ).fetchall()
    return [_incident(row) for row in rows]


def count_incidents(conn: sqlite3.Connection, slug: str) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) AS n FROM incidents WHERE engagement_slug = ?", (slug,)
        ).fetchone()["n"]
    )


def resolve_incident(
    conn: sqlite3.Connection,
    incident_id: str,
    resolving_version_id: str,
    resolved_event_seq: int,
) -> None:
    """The only incident mutation after opening: unresolved -> RESOLVED, and only here.

    Both unresolved states resolve: an incident a close retired as
    CLOSED_UNRESOLVED is inherited by the next shift and resolves when a later
    run of a new version passes its linked regression and the family's current
    unseen acceptance check (program design S3.9, S5.7). RESOLVED rows never
    change again.
    """
    conn.execute(
        "UPDATE incidents SET state = ?, resolving_version_id = ?, resolved_event_seq = ? "
        "WHERE id = ? AND state IN (?, ?)",
        (
            IncidentState.RESOLVED.value,
            resolving_version_id,
            resolved_event_seq,
            incident_id,
            IncidentState.OPEN.value,
            IncidentState.CLOSED_UNRESOLVED.value,
        ),
    )


def close_unresolved_incidents(conn: sqlite3.Connection, slug: str) -> int:
    """Retire the engagement's unresolved OPEN incidents as CLOSED_UNRESOLVED (S5.8).

    The state change is the only incident mutation at close; no ledger event is
    written, because the incident stays unresolved and is inherited as an
    incident row, never as a declared limit.
    """
    cursor = conn.execute(
        "UPDATE incidents SET state = ? WHERE engagement_slug = ? AND state = ?",
        (IncidentState.CLOSED_UNRESOLVED.value, slug, IncidentState.OPEN.value),
    )
    return int(cursor.rowcount)


# --- rotation_draws --------------------------------------------------------


def _draw(row: sqlite3.Row) -> RotationDraw:
    return RotationDraw(
        id=row["id"],
        engagement_slug=row["engagement_slug"],
        family=row["family"],
        variant_ref=row["variant_ref"],
        run_id=row["run_id"],
        cycle=row["cycle"],
        drawn_at=row["drawn_at"],
        state=DrawState(row["state"]),
    )


def insert_rotation_draw(conn: sqlite3.Connection, draw: RotationDraw) -> None:
    conn.execute(
        "INSERT INTO rotation_draws (id, engagement_slug, family, variant_ref, run_id, cycle, drawn_at, state) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            draw.id,
            draw.engagement_slug,
            draw.family,
            draw.variant_ref,
            draw.run_id,
            draw.cycle,
            draw.drawn_at.isoformat(),
            draw.state.value,
        ),
    )


def list_rotation_draws(conn: sqlite3.Connection, slug: str) -> list[RotationDraw]:
    rows = conn.execute(
        "SELECT * FROM rotation_draws WHERE engagement_slug = ? ORDER BY rowid", (slug,)
    ).fetchall()
    return [_draw(row) for row in rows]


def list_rotation_draws_for_run(conn: sqlite3.Connection, run_id: str) -> list[RotationDraw]:
    rows = conn.execute(
        "SELECT * FROM rotation_draws WHERE run_id = ? ORDER BY family", (run_id,)
    ).fetchall()
    return [_draw(row) for row in rows]


def invalidate_rotation_group(conn: sqlite3.Connection, slug: str, family: str) -> int:
    """Retire a compromised group by state change; rows are never deleted."""
    cursor = conn.execute(
        "UPDATE rotation_draws SET state = ? WHERE engagement_slug = ? AND family = ? AND state = ?",
        (DrawState.INVALIDATED.value, slug, family, DrawState.ACTIVE.value),
    )
    return int(cursor.rowcount)


def invalidated_run_ids(conn: sqlite3.Connection, slug: str) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT run_id FROM rotation_draws WHERE engagement_slug = ? AND state = ? ORDER BY run_id",
        (slug, DrawState.INVALIDATED.value),
    ).fetchall()
    return [row["run_id"] for row in rows]


# --- ledger_events ---------------------------------------------------------


def _ledger_event(row: sqlite3.Row) -> LedgerEvent:
    return LedgerEvent(
        event_type=LedgerEventType(row["event_type"]),
        cause_refs=tuple(_load(row["cause_refs_json"])),
        payload=_load(row["payload_json"]),
        synthetic=bool(row["synthetic"]),
        seq=row["seq"],
        prev_hash=row["prev_hash"],
        hash=row["hash"],
    )


def insert_ledger_event(conn: sqlite3.Connection, slug: str, event: LedgerEvent) -> None:
    conn.execute(
        "INSERT INTO ledger_events (seq, engagement_slug, event_type, cause_refs_json, payload_json, synthetic, prev_hash, hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            event.seq,
            slug,
            event.event_type.value,
            _dump(list(event.cause_refs)),
            _dump(event.payload),
            1,
            event.prev_hash,
            event.hash,
        ),
    )


def last_ledger_event(conn: sqlite3.Connection, slug: str) -> LedgerEvent | None:
    row = conn.execute(
        "SELECT * FROM ledger_events WHERE engagement_slug = ? ORDER BY seq DESC LIMIT 1", (slug,)
    ).fetchone()
    return _ledger_event(row) if row else None


def list_ledger_events(conn: sqlite3.Connection, slug: str) -> list[LedgerEvent]:
    rows = conn.execute(
        "SELECT * FROM ledger_events WHERE engagement_slug = ? ORDER BY seq", (slug,)
    ).fetchall()
    return [_ledger_event(row) for row in rows]


def list_unresolved_limits(conn: sqlite3.Connection, slug: str) -> list[str]:
    """Declared limits still in force, derived from LIMIT_DECLARED events (S5.1).

    A limit is declared at the engagement's most recent close and stays in force
    until a later close stops declaring it: the projection is exactly what that
    close declared, in first-appearance order, deduplicated so a repeated
    declaration cannot multiply a limit on the board. Events are append-only, so
    a limit the artifact no longer carries leaves the projection without any
    stored event being edited or deleted.
    """
    latest_closed = conn.execute(
        "SELECT id FROM shifts WHERE engagement_slug = ? AND state = 'closed' "
        "ORDER BY seq DESC LIMIT 1",
        (slug,),
    ).fetchone()
    if latest_closed is None:
        return []
    rows = conn.execute(
        "SELECT payload_json, cause_refs_json FROM ledger_events "
        "WHERE engagement_slug = ? AND event_type = ? ORDER BY seq",
        (slug, LedgerEventType.LIMIT_DECLARED.value),
    ).fetchall()
    declared_now = {
        value
        for row in rows
        if (_load(row["cause_refs_json"]) or [None])[0] == latest_closed["id"]
        for value in [_load(row["payload_json"]).get("declared_limit")]
        if isinstance(value, str)
    }
    limits: list[str] = []
    seen: set[str] = set()
    for row in rows:
        value = _load(row["payload_json"]).get("declared_limit")
        if isinstance(value, str) and value in declared_now and value not in seen:
            seen.add(value)
            limits.append(value)
    return limits
