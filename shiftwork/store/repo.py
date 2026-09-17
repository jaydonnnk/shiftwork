"""Raw parameterized SQL, one group per table. Rows are validated into domain models.

Slice 2 replaces this tracer repository with the approved schema and repo groups.
"""

import json
import sqlite3
from datetime import datetime

from shiftwork.domain.models import (
    ArtifactVersion,
    CheckResult,
    Incident,
    IncidentState,
    LedgerEvent,
    LedgerEventType,
    ReasonCode,
    Run,
    RunOutput,
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


# --- shifts ----------------------------------------------------------------


def _shift(row: sqlite3.Row) -> Shift:
    return Shift(
        id=row["id"],
        engagement_slug=row["engagement_slug"],
        seq=row["seq"],
        state=row["state"],
        opened_at=row["opened_at"],
        closed_at=row["closed_at"],
    )


def insert_shift(conn: sqlite3.Connection, shift: Shift) -> None:
    conn.execute(
        "INSERT INTO shifts (id, engagement_slug, seq, state, opened_at, closed_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            shift.id,
            shift.engagement_slug,
            shift.seq,
            shift.state,
            shift.opened_at.isoformat(),
            shift.closed_at.isoformat() if shift.closed_at else None,
        ),
    )


def get_shift(conn: sqlite3.Connection, shift_id: str) -> Shift | None:
    row = conn.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
    return _shift(row) if row else None


def get_latest_shift(conn: sqlite3.Connection, slug: str) -> Shift | None:
    row = conn.execute(
        "SELECT * FROM shifts WHERE engagement_slug = ? ORDER BY seq DESC LIMIT 1", (slug,)
    ).fetchone()
    return _shift(row) if row else None


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


def upsert_draft(conn: sqlite3.Connection, shift_id: str, files: dict[str, str], updated_at: datetime) -> None:
    conn.execute(
        "INSERT INTO draft_artifacts (shift_id, files_json, updated_at) VALUES (?, ?, ?) "
        "ON CONFLICT(shift_id) DO UPDATE SET files_json = excluded.files_json, updated_at = excluded.updated_at",
        (shift_id, _dump(files), updated_at.isoformat()),
    )


def get_draft(conn: sqlite3.Connection, shift_id: str) -> tuple[dict[str, str], str] | None:
    row = conn.execute(
        "SELECT files_json, updated_at FROM draft_artifacts WHERE shift_id = ?", (shift_id,)
    ).fetchone()
    if row is None:
        return None
    return _load(row["files_json"]), row["updated_at"]


# --- artifact_versions -----------------------------------------------------


def _version(row: sqlite3.Row) -> ArtifactVersion:
    return ArtifactVersion(
        id=row["id"],
        shift_id=row["shift_id"],
        parent_id=row["parent_id"],
        content_hash=row["content_hash"],
        contract=_load(row["contract_json"]),
        created_by=row["created_by"],
        created_at=row["created_at"],
    )


def insert_version(conn: sqlite3.Connection, version: ArtifactVersion) -> None:
    conn.execute(
        "INSERT INTO artifact_versions (id, shift_id, parent_id, content_hash, contract_json, created_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            version.id,
            version.shift_id,
            version.parent_id,
            version.content_hash,
            _dump(version.contract),
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


# --- runs ------------------------------------------------------------------


def _run(row: sqlite3.Row) -> Run:
    return Run(
        id=row["id"],
        shift_id=row["shift_id"],
        artifact_version_id=row["artifact_version_id"],
        attempt_number=row["attempt_number"],
        state=RunState(row["state"]),
        adapter=row["adapter"],
        failure_kind=row["failure_kind"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
    )


def insert_run(conn: sqlite3.Connection, run: Run) -> None:
    conn.execute(
        "INSERT INTO runs (id, shift_id, artifact_version_id, attempt_number, state, adapter, failure_kind, started_at, ended_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run.id,
            run.shift_id,
            run.artifact_version_id,
            run.attempt_number,
            run.state.value,
            run.adapter,
            run.failure_kind.value if run.failure_kind else None,
            run.started_at.isoformat(),
            run.ended_at.isoformat() if run.ended_at else None,
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


def get_latest_run(conn: sqlite3.Connection, shift_id: str) -> Run | None:
    row = conn.execute(
        "SELECT * FROM runs WHERE shift_id = ? ORDER BY attempt_number DESC LIMIT 1", (shift_id,)
    ).fetchone()
    return _run(row) if row else None


def count_runs(conn: sqlite3.Connection, shift_id: str) -> int:
    return int(
        conn.execute("SELECT COUNT(*) AS n FROM runs WHERE shift_id = ?", (shift_id,)).fetchone()["n"]
    )


def count_runs_all(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"])


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
    )


def insert_output(conn: sqlite3.Connection, output: RunOutput) -> None:
    conn.execute(
        "INSERT INTO run_outputs (id, run_id, request_ordinal, request_text, http_status, body, elapsed_ms, transport_error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            output.id,
            output.run_id,
            output.request_ordinal,
            output.request_text,
            output.http_status,
            output.body,
            output.elapsed_ms,
            output.transport_error.value if output.transport_error else None,
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
