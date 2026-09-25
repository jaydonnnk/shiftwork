"""Offline final-pivot stages. S10 currently implements only ``migration``.

The migration stage creates a synthetic schema-v5 sample, copies it, and opens
only the copy with the current controller. It never reads SHIFTWORK_DB_PATH.
Historical rows are compared using their original columns and SQLite values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from shiftwork import config
from shiftwork.app import create_app
from shiftwork.domain import canonical
from shiftwork.domain.models import ContractParams
from shiftwork.ledger import chain
from shiftwork.store import db

ROOT = Path(__file__).resolve().parents[1]
V5_SCHEMA = ROOT / "tests" / "store" / "schema_v5.sql"
OPENED_AT = "2026-09-20T10:00:00+00:00"
CLOSED_AT = "2026-09-20T11:00:00+00:00"


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def create_v5_sample(path: Path, *, with_run: bool = True) -> None:
    """Build representative closed v5 Bellwether history, including raw evidence.

    The no-run variant has an owned immutable version but no source request/run.
    This is a test/demo sample, not a new reviewed product fixture.
    """
    if path.exists():
        raise FileExistsError(path)
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(V5_SCHEMA.read_text(encoding="utf-8"))
        conn.execute("PRAGMA user_version = 5")
        files = config.repair_arc_artifact_files("pre")
        contract = ContractParams.model_validate(config.REPAIR_ARC_CONTRACT_JSON)
        contract_json = canonical.contract_params_json(contract)
        catalog_hash = "a" * 64
        version_hash = canonical.artifact_content_hash(files, contract_json, catalog_hash)
        conn.execute(
            "INSERT INTO engagements VALUES (?, ?, ?)",
            (config.BOOKSHOP_SLUG, config.BOOKSHOP_BUSINESS_KIND, config.BOOKSHOP_DISPLAY_NAME),
        )
        conn.execute(
            "INSERT INTO engagement_config VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                config.BOOKSHOP_SLUG,
                config.BOOKSHOP_BUSINESS_KIND,
                "scaffolded",
                _json(["hint", "diagnose"]),
                config.BOOKSHOP_TOTAL_ASSIST_BUDGET,
                _json(list(config.BOOKSHOP_FAMILIES)),
                config.DEFAULT_ATTEMPT_LIMIT,
                config.BOOKSHOP_ROTATION_GROUP_SIZE,
            ),
        )
        conn.execute(
            "INSERT INTO shifts VALUES (?, ?, ?, ?, ?, ?)",
            ("bookshop-shift-01", config.BOOKSHOP_SLUG, 1, "closed", OPENED_AT, CLOSED_AT),
        )
        conn.execute(
            "INSERT INTO draft_artifacts VALUES (?, ?, ?)",
            ("bookshop-shift-01", _json(files), CLOSED_AT),
        )
        conn.execute(
            "INSERT INTO artifact_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "version-v5-0001", "bookshop-shift-01", None, version_hash,
                "legacy:version-v5-0001", _json(files), _json(contract_json),
                catalog_hash, "learner", OPENED_AT,
            ),
        )
        if with_run:
            body = b'{"action":"answer","claims":[],"evidence_refs":[]}'
            conn.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "run-v5-0001", "bookshop-shift-01", "version-v5-0001",
                    "thin.jsonl", str(config.THIN_SNAPSHOT), None, 1, "FINALIZED",
                    "recorded", None, OPENED_AT, CLOSED_AT,
                ),
            )
            conn.execute(
                "INSERT INTO run_outputs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "output-v5-0001", "run-v5-0001", 1,
                    "Is this paperback in stock?", 200, body, 17, None, None,
                ),
            )
            conn.execute(
                "INSERT INTO check_results VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    "check-v5-0001", "run-v5-0001", "legacy-public-check", "fail",
                    "output-v5-0001", "sealed:legacy-digest", "STALE_BEYOND_RULE",
                ),
            )
            cause_refs = ["run-v5-0001", "check-v5-0001", "output-v5-0001"]
            payload = {"count": 1, "catalog_version": 1}
            event_hash = chain.event_hash(
                seq=1, prev_hash=config.GENESIS_HASH, event_type="BACKLOG_RECORDED",
                cause_refs=cause_refs, payload=payload, synthetic=True,
            )
            conn.execute(
                "INSERT INTO ledger_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    config.BOOKSHOP_SLUG, 1, "BACKLOG_RECORDED", _json(cause_refs),
                    _json(payload), 1, config.GENESIS_HASH, event_hash,
                ),
            )
            conn.execute(
                "INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "BWB-v5-01", config.BOOKSHOP_SLUG, "bookshop-shift-01", "run-v5-0001",
                    "output-v5-0001", "check-v5-0001", "STALE_BEYOND_RULE", 1,
                    "CLOSED_UNRESOLVED", None, None,
                ),
            )
            conn.execute(
                "INSERT INTO rotation_draws VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "draw-v5-0001", config.BOOKSHOP_SLUG, "freshness", "sealed:legacy-digest",
                    "run-v5-0001", 1, OPENED_AT, "active",
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _bytes(value: object) -> bytes:
    if value is None:
        return b"n"
    if isinstance(value, bytes):
        return b"b" + len(value).to_bytes(8, "big") + value
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return b"t" + len(raw).to_bytes(8, "big") + raw
    if isinstance(value, int):
        return b"i" + str(value).encode("ascii") + b";"
    raise TypeError(type(value))


def snapshot_v5_rows(conn: sqlite3.Connection) -> dict[str, tuple[tuple[str, ...], tuple[bytes, ...]]]:
    """Serialize each original column value, including BLOBs, in rowid order."""
    snapshot = {}
    names = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    for table in names:
        columns = tuple(row[1] for row in conn.execute(f"PRAGMA table_info({table})"))
        rows = conn.execute(f"SELECT {', '.join(columns)} FROM {table} ORDER BY rowid").fetchall()
        serialized = tuple(
            b"".join(_bytes(value) for value in row) for row in rows
        )
        snapshot[table] = columns, serialized
    return snapshot


def assert_v5_rows_preserved(
    conn: sqlite3.Connection,
    before: dict[str, tuple[tuple[str, ...], tuple[bytes, ...]]],
) -> None:
    for table, (columns, expected) in before.items():
        current = tuple(
            b"".join(_bytes(value) for value in row)
            for row in conn.execute(f"SELECT {', '.join(columns)} FROM {table} ORDER BY rowid")
        )
        assert current == expected, f"historical {table} bytes changed"


def migration_stage() -> int:
    with tempfile.TemporaryDirectory(prefix="shiftwork-s10-") as directory:
        root = Path(directory)
        original = root / "original-v5.db"
        copied = root / "migration-copy.db"
        create_v5_sample(original)
        original_file_hash = hashlib.sha256(original.read_bytes()).hexdigest()
        shutil.copy2(original, copied)
        source = sqlite3.connect(original)
        try:
            before = snapshot_v5_rows(source)
        finally:
            source.close()

        with TestClient(create_app(str(copied))) as client:
            board_before = client.get("/api/engagements/bookshop/board")
            assert board_before.status_code == 200, board_before.text
            board_before_json = board_before.json()
            shift_response = client.post("/api/engagements/bookshop/shifts")
            assert shift_response.status_code == 201, shift_response.text
            shift = shift_response.json()
            shift_id = shift["id"]
            board_after = client.get("/api/engagements/bookshop/board")
            assert board_after.status_code == 200, board_after.text
            run_denied = client.post(f"/api/shifts/{shift_id}/runs")
            close_denied = client.post(f"/api/shifts/{shift_id}/close")
            assert run_denied.status_code == close_denied.status_code == 409
            assert client.post("/api/engagements/bookshop/shifts").status_code == 409
            old_run = client.get("/api/runs/run-v5-0001")
            assert old_run.status_code == 200, old_run.text
            old_outputs = client.get("/api/runs/run-v5-0001/outputs")
            assert old_outputs.status_code == 200, old_outputs.text
            old_ledger = client.get("/api/engagements/bookshop/ledger")
            assert old_ledger.status_code == 200, old_ledger.text

        migrated = db.connect(copied)
        try:
            assert migrated.execute("PRAGMA user_version").fetchone()[0] == 6
            for table, (columns, expected) in before.items():
                rows = tuple(
                    b"".join(_bytes(value) for value in row)
                    for row in migrated.execute(
                        f"SELECT {', '.join(columns)} FROM {table} WHERE "
                        + ("seq = 1" if table == "shifts" else "1 = 1")
                        + " ORDER BY rowid"
                    )
                )
                if table == "draft_artifacts":
                    rows = rows[: len(expected)]
                assert rows[: len(expected)] == expected, table
            assert migrated.execute("SELECT COUNT(*) FROM operating_selections").fetchone()[0] == 0
            assert migrated.execute("SELECT COUNT(*) FROM experiments").fetchone()[0] == 0
            counts = {table: len(rows) for table, (_, rows) in before.items()}
            history_hash = hashlib.sha256(
                b"".join(row for _, rows in before.values() for row in rows)
            ).hexdigest()
            db.ensure_schema(migrated)
            assert migrated.execute("PRAGMA user_version").fetchone()[0] == 6
        finally:
            migrated.close()
        assert hashlib.sha256(original.read_bytes()).hexdigest() == original_file_hash

        # A newly seeded engagement takes the separate starter branch and never a
        # legacy first-choice shift. Its starter is reported as-is, including that
        # the offline scaffold is not yet a pinned executable trusted fixture.
        fresh = root / "fresh-v6.db"
        with TestClient(create_app(str(fresh))) as fresh_client:
            fresh_shift = fresh_client.post("/api/engagements/bookshop/shifts")
            assert fresh_shift.status_code == 201, fresh_shift.text
            fresh_shift_json = fresh_shift.json()
            fresh_board = fresh_client.get("/api/engagements/bookshop/board").json()
            starter_selection = fresh_board.get("operating_selection")
            starter_run = fresh_client.post(f"/api/shifts/{fresh_shift_json['id']}/runs")
            starter_run_json = (
                fresh_client.get(f"/api/runs/{starter_run.json()['id']}").json()
                if starter_run.status_code == 202
                else {}
            )

        print(json.dumps({
            "stage": "migration",
            "source": "synthetic v5 sample; only a temporary copy migrated",
            "schema_version": 6,
            "historical_row_counts": counts,
            "historical_serialized_sha256": history_hash,
            "historical_rows_preserved": True,
            "old_run": {
                "purpose": old_run.json().get("purpose"),
                "evidence_mode": old_run.json().get("evidence_mode"),
                "output_body_base64": old_outputs.json()[0]["body_base64"],
                "ledger_hash": old_ledger.json()["events"][0]["hash"],
            },
            "old_context": "unknown: original request and execution context bytes were not captured",
            "before_open": board_before_json.get("operating_status"),
            "shift": {
                "id": shift_id,
                "opening_mode": shift.get("opening_mode"),
                "operation_allowed": shift.get("operation_allowed"),
            },
            "after_open": board_after.json().get("operating_status"),
            "selection": board_after.json().get("operating_selection"),
            "operation_status": run_denied.status_code,
            "close_status": close_denied.status_code,
            "new_engagement_starter": {
                "opening_mode": fresh_shift_json.get("opening_mode"),
                "operating_status": fresh_board.get("operating_status"),
                "selection_kind": (starter_selection or {}).get("kind"),
                "selected_version_id": (starter_selection or {}).get("selected_version_id"),
                "is_eligible_repair_evidence": False,
                "starter_run_status_code": starter_run.status_code,
                "starter_run_state": starter_run_json.get("state"),
                "starter_run_purpose": starter_run_json.get("purpose"),
                "starter_run_adapter": starter_run_json.get("adapter"),
                "starter_run_evidence_mode": starter_run_json.get("evidence_mode"),
                "starter_run_failure_kind": starter_run_json.get("failure_kind"),
            },
            "original_file_unchanged": True,
            "migration_rerun_noop": True,
            "limits": [
                "recorded inspection and trusted local foundation only",
                "no semantic replay or live AI execution",
                "the new-engagement starter is a labelled baseline, not eligible repair evidence",
                "the starter run above used the shipped default recorded adapter, so it replayed a "
                "pinned transcript and never executed the starter artifact; its FINALIZED state is "
                "RECORDED_INSPECTION, not evidence that the starter works",
                "under the local_process adapter the same starter fails closed as PROVISION_FAILED "
                "because the offline scaffold is not a pinned trusted fixture; S11 supplies the "
                "reviewed failing starter",
                "no selection route exists yet, so S10 cannot operate a frozen candidate; "
                "S17 owns the first valid explicit choice",
            ],
        }, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("migration",), required=True)
    args = parser.parse_args()
    if args.stage == "migration":
        return migration_stage()
    raise AssertionError(args.stage)


if __name__ == "__main__":
    raise SystemExit(main())
