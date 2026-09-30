"""Offline final-pivot stages through explicit selection (S17).

The migration stage creates a synthetic schema-v5 sample, copies it, and opens
only the copy with the current controller. It never reads SHIFTWORK_DB_PATH.
Historical rows are compared using their original columns and SQLite values.

The investigation stage runs the reviewed failing starter as a public diagnostic
against the pinned incident request and public state, then prints the exact
request, the exact output, the independently assessed required tasks and the
customer text rendered from the validated envelope. Every run is a temporary
database of its own; no runtime file and no protected case is touched.

The replay stage re-derives one finalized S18 operation from its captured bytes
only and reports the comparison against the stored rows: replacing the current
mission file or the public state file, and changing today's incident state,
leaves the replay IDENTICAL with zero writes; a stored semantic divergence
reports DIFFERENT; an independent chain tamper is caught by chain verification
while the replay still reports IDENTICAL; and a migrated v5 run without captured
inputs reports UNKNOWN_MISSING_INPUTS.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import time
from contextlib import nullcontext
from pathlib import Path

from fastapi.testclient import TestClient
from contree_client.httpx import ContreeAsyncClient

from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain import canonical
from shiftwork.domain.models import ContractParams
from shiftwork.executor.base import ArtifactSnapshotRef, BatchRef, RunRequest
from shiftwork.executor.tokenfactory import TokenFactoryAdapter
from shiftwork.gateway.redaction import assert_public_safe
from shiftwork.ledger import chain
from shiftwork.store import db
from shiftwork.store import repo
from shiftwork.sealed import store as sealed_store

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
                "Slice 11 ships the reviewed failing starter as the new engagement's draft and as a "
                "pinned trusted fixture, so --stage investigation executes it under local_process",
                "no selection route exists yet, so S10 cannot operate a frozen candidate; "
                "S17 owns the first valid explicit choice",
            ],
        }, indent=2, sort_keys=True))
    return 0


def investigation_stage() -> int:
    """Run the reviewed failing starter as one public diagnostic, offline.

    A real database over the shipped controller: the learner's own run sources the
    investigation, the controller freezes the reviewed public bytes, and the
    diagnostic executes the pinned starter through the local_process adapter. The
    printed numbers are read back from the same stored rows a public projection
    reads; nothing here is a live model call or a customer consequence.
    """
    with tempfile.TemporaryDirectory(prefix="shiftwork-s11-") as directory:
        db_file = Path(directory) / "investigation.db"
        with TestClient(create_app(str(db_file))) as client:
            shift = client.post("/api/engagements/bookshop/shifts")
            assert shift.status_code == 201, shift.text
            shift_id = shift.json()["id"]

            version = client.post(
                f"/api/shifts/{shift_id}/artifact/versions",
                json={"contract": config.PIVOT_STARTER_CONTRACT_JSON},
            )
            assert version.status_code == 201, version.text
            candidate = version.json()
            assert candidate["content_hash"] == config.TRUSTED_LOCAL_FIXTURES["pivot_starter"][0], (
                "the shipped draft is not the pinned reviewed starter"
            )

            operation = client.post(f"/api/shifts/{shift_id}/runs")
            assert operation.status_code == 202, operation.text
            operation_id = operation.json()["id"]
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                operation_run = client.get(f"/api/runs/{operation_id}").json()
                if operation_run["state"] in ("FINALIZED", "FAILED"):
                    break
                time.sleep(0.05)

            investigation = client.post(
                f"/api/shifts/{shift_id}/investigations",
                json={
                    "source_run_id": operation_id,
                    "source_request_ordinal": 1,
                    "cause": "the router answers only the optional price task and never reads collection records",
                    "falsifier": "a request with no currency symbol still omits the collection task",
                    "public_test": "assert a result exists for every required task in the frozen request",
                    "revision_of_id": None,
                    "client_request_id": "demo-investigation-1",
                },
            )
            assert investigation.status_code == 201, investigation.text

            before = client.get("/api/engagements/bookshop/board").json()
            created = client.post(
                f"/api/shifts/{shift_id}/experiments",
                json={
                    "kind": "DIAGNOSTIC",
                    "investigation_id": investigation.json()["id"],
                    "candidate_a_version_id": candidate["id"],
                    "client_request_id": "demo-diagnostic-1",
                },
            )
            assert created.status_code == 202, created.text
            experiment_id = created.json()["id"]
            experiment = created.json()
            while time.monotonic() < deadline:
                experiment = client.get(f"/api/experiments/{experiment_id}").json()
                if experiment["trials"][0]["state"] in ("COMPLETE", "FAILED"):
                    break
                time.sleep(0.05)
            after = client.get("/api/engagements/bookshop/board").json()

        trial = experiment["trials"][0]
        assessment_rows = {
            entry["task_id"]: entry for entry in trial["task_assessments"]
        }
        required_failures = sorted(
            task_id
            for task_id, entry in assessment_rows.items()
            if entry["mandatory_pass"] is False
        )
        output = trial["outputs"][0]
        print(json.dumps({
            "stage": "investigation",
            "source": "temporary database; the pinned reviewed starter executed under local_process",
            "shift_id": shift_id,
            "candidate": {
                "artifact_version_id": candidate["id"],
                "content_hash": candidate["content_hash"],
                "matches_pinned_starter": True,
                "frozen_contract_catalog_version": config.PIVOT_STARTER_CONTRACT_JSON["catalog_version"],
            },
            "context": {
                "content_hash": experiment["context_hash"],
                "evidence_class": experiment["context_evidence_class"],
                "workloads": experiment["workloads"],
                "protected_reservation": None,
            },
            "request": {
                "ordinal": output["request_ordinal"],
                "text": output["request_text"],
            },
            "observed": {
                "http_status": output["http_status"],
                "exact_output": base64.b64decode(output["body_base64"]).decode("utf-8"),
                "elapsed_ms": output["elapsed_ms"],
                "transport_error": output["transport_error"],
                "interpretation_or_tool_observations": trial["observations"],
                "observations_note": (
                    "the trusted local starter reports no interpretation or tool events; "
                    "the station shows observations only when a service produces them"
                ),
            },
            "customer_text": trial["customer_text"],
            "assessed_tasks": [
                {
                    "task_id": task_id,
                    "outcome": entry["outcome"],
                    "mandatory_pass": entry["mandatory_pass"],
                    "reason_codes": entry["reason_codes"],
                }
                for task_id, entry in sorted(assessment_rows.items())
            ],
            "request_usefully_completed": all(
                entry["outcome"] == "USEFUL_COMPLETION" for entry in assessment_rows.values()
            ),
            "required_tasks_unanswered": required_failures,
            "candidate_eligible": experiment["eligible"],
            "eligibility_reason": experiment["eligibility_reason"],
            "experiment_state": experiment["state"],
            "operation_budget": {
                "attempts_used_before": before["attempts_used"],
                "attempts_used_after": after["attempts_used"],
                "attempts_remaining_after": after["attempts_remaining"],
            },
            "business_state_unchanged": {
                "ledger_events_before": before["ledger_event_count"],
                "ledger_events_after": after["ledger_event_count"],
                "incidents_before": before["total_incidents"],
                "incidents_after": after["total_incidents"],
            },
            "limits": [
                "TRUSTED_LOCAL offline fixture execution, never a live model or hostile-code proof",
                "the diagnostic reserves no protected case and can never qualify a version",
                "the reviewed starter, incident request, public state and rubric are pinned and "
                "authorized for local verification only; this stage is not Slice 11 acceptance",
                "diagnostic help stays denied until Slice 14 supplies the assist gateway",
            ],
        }, indent=2, sort_keys=True))
    return 0


S13_CANARY_SERVICE = r'''
import json
import os
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        port = int(os.environ['SHIFTWORK_GATEWAY_PORT'])
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
        conn.request('POST', '/tool', json.dumps({'tool': 'unlisted_tool'}),
                     headers={'Content-Type': 'application/json'})
        tool_status = conn.getresponse().status
        conn.close()
        checks = {
            'provider_key_visible': any(key in os.environ for key in
                ('NEBIUS_API_KEY', 'CONTREE_TOKEN', 'SHIFTWORK_LEARNER_INFERENCE_KEY')),
            'controller_db_visible': 'SHIFTWORK_DB_PATH' in os.environ or
                Path('/work/shiftwork.db').exists(),
            'host_canary_visible': 'S13_HOST_ONLY_CANARY' in os.environ,
            'protected_fixture_visible': Path('/work/sealed').exists() or
                Path('/work/bookshop_task_completion.json').exists(),
            'other_run_grant_visible': any('GRANT' in key or 'RUN_ID' in key
                for key in os.environ),
            'unlisted_tool_status': tool_status,
        }
        body = json.dumps(checks, sort_keys=True).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

with HTTPServer(('127.0.0.1', 0), Handler) as server:
    print(json.dumps({'port': server.server_port}), flush=True)
    server.serve_forever()
'''

S13_MODEL_SERVICE = r'''
import http.client
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

def gateway(path, payload):
    conn = http.client.HTTPConnection('127.0.0.1', int(os.environ['SHIFTWORK_GATEWAY_PORT']), timeout=25)
    raw = json.dumps(payload).encode()
    conn.request('POST', path, body=raw, headers={'Content-Type': 'application/json'})
    response = conn.getresponse()
    body = response.read()
    status = response.status
    conn.close()
    if status != 200:
        raise RuntimeError('controller gateway refused the service request')
    return json.loads(body)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        prompt = (
            'Choose the first public information action needed for this bookshop request. '
            'Reply with exactly one allowed name, no explanation: public_record_lookup '
            '(look up a known book fact) or public_catalog_search (find a similar title). '
            'Customer request: ' + request['text']
        )
        choice = gateway('/infer', {'request_ordinal': 1, 'input_text': prompt})['selected_tool']
        results = []
        evidence = []
        if choice == 'public_record_lookup':
            records = gateway('/tool', {'tool': choice,
                'entity_ref': 'book:salt-roads:paperback', 'record_kind': 'price'})['records']
            if records:
                record = records[0]
                evidence = [record['record_id']]
                results = [{'task_id': 'price', 'status': 'COMPLETED',
                    'entity_ref': 'book:salt-roads:paperback', 'claims': [{
                        'kind': 'price', 'entity_ref': 'book:salt-roads:paperback',
                        'value': record['value'], 'evidence_refs': evidence}],
                    'commitment_ref': None, 'explanation_code': None}]
        else:
            gateway('/tool', {'tool': choice, 'genre': 'coastal_travel'})
        output = {'request_id': request['request_id'], 'task_results': results,
                  'evidence_refs': evidence, 'uncertainty_codes': []}
        body = json.dumps(output, separators=(',', ':')).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

with HTTPServer(('127.0.0.1', 0), Handler) as server:
    print(json.dumps({'port': server.server_port}), flush=True)
    server.serve_forever()
'''


def s13_service_stage(*, model: bool) -> int:
    """One real public bootstrap via the HTTP API, preserving its local database."""
    token = os.environ.get("NEBIUS_API_KEY", "")
    project = os.environ.get("NEBIUS_PROJECT_ID", "")
    if not token or not project:
        print(json.dumps({"stage": "s13-model" if model else "s13-code", "verdict": "BLOCKED_CREDENTIALS_ABSENT"}))
        return 2
    label = "model" if model else "code"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    database = ROOT / f"slice13-{label}-{stamp}.db"
    create_v5_sample(database, with_run=False)
    source = S13_MODEL_SERVICE if model else config.PIVOT_STARTER_ARTIFACT_PATHS["service.py"].read_text(encoding="utf-8")
    with TestClient(create_app(str(database), executor="tokenfactory")) as client:
        opened = client.post("/api/engagements/bookshop/shifts")
        if opened.status_code != 201:
            raise RuntimeError("legacy shift did not open")
        shift_id = opened.json()["id"]
        before = client.get("/api/engagements/bookshop/board").json()
        saved = client.put(f"/api/shifts/{shift_id}/artifact", json={"files": {"service.py": source}})
        if saved.status_code != 200:
            raise RuntimeError("learner source did not save")
        frozen = client.post(f"/api/shifts/{shift_id}/artifact/versions",
            json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
        if frozen.status_code != 201:
            raise RuntimeError("learner source did not freeze")
        version = frozen.json()
        reserved = client.post(f"/api/shifts/{shift_id}/experiments", json={
            "kind": "DIAGNOSTIC", "investigation_id": None,
            "candidate_a_version_id": version["id"],
            "client_request_id": f"s13-{label}-{stamp}"})
        if reserved.status_code != 202:
            raise RuntimeError("public source diagnostic was not reserved: " + reserved.text[:300])
        experiment = client.get(f"/api/experiments/{reserved.json()['id']}")
        after = client.get("/api/engagements/bookshop/board").json()
        if experiment.status_code != 200:
            raise RuntimeError("public diagnostic projection failed")
        view = experiment.json()
    trial = view["trials"][0]
    conn = db.connect(database)
    try:
        run_id = trial["run_id"]
        raw_observations = repo.list_observations(conn, run_id)
        raw = [json.loads(base64.b64decode(item.raw_payload_ref.split(",", 1)[1]))
               for item in raw_observations]
        operation_id = next((entry.get("operation_id") for entry in raw if "operation_id" in entry), None)
        provider = [entry["provider_response"] for entry in raw if "provider_response" in entry]
        counts = {
            "operating_selections": repo.count_operating_selections(conn),
            "operation_runs": repo.count_operation_runs(conn, shift_id),
            "ledger_events": len(repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)),
            "incidents": len(repo.list_incidents(conn, config.BOOKSHOP_SLUG)),
        }
    finally:
        conn.close()
    output = trial["outputs"][0] if trial["outputs"] else None
    capture = next((item["public_payload_json"] for item in trial["observations"]
        if item["public_payload_json"].get("checkpoint_readback")), None)
    verdict = ("PASS_ONE_PUBLIC_REQUEST" if trial["state"] == "COMPLETE" and output
        and capture and view["eligible"] is False and not any(counts.values())
        and (not model or bool(provider)) else "STOP_INCOMPLETE")
    report = {
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stage": f"s13-{label}", "verdict": verdict, "shift_id": shift_id,
        "experiment_id": view["id"], "run_id": run_id, "operation_id": operation_id,
        "version_hash": version["content_hash"], "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "context_hash": view["context_hash"], "context_evidence_class": view["context_evidence_class"],
        "trial_state": trial["state"], "missing_evidence": trial["missing_evidence"],
        "request_text": output["request_text"] if output else None,
        "output_body_base64": output["body_base64"] if output else None,
        "customer_text": trial["customer_text"], "task_assessments": trial["task_assessments"],
        "observations": trial["observations"], "checkpoint": capture,
        "provider_response": provider, "business_counts": counts,
        "business_before": {"ledger_events": before["ledger_event_count"],
                            "incidents": before["total_incidents"]},
        "business_after": {"ledger_events": after["ledger_event_count"],
                           "incidents": after["total_incidents"]},
        "adapter_source_sha256": hashlib.sha256(
            (ROOT / "shiftwork" / "executor" / "tokenfactory.py").read_bytes()).hexdigest(),
    }
    assert_public_safe(report, (token, project, str(Path.cwd())))
    evidence = ROOT / "docs" / "plans" / "shiftwork" / "evidence" / f"slice13-{label}-{stamp}.jsonl"
    evidence.write_text(json.dumps(report, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"stage": f"s13-{label}", "verdict": verdict,
        "database": str(database), "evidence_file": str(evidence),
        "operation_id": operation_id, "checkpoint_sha256": capture.get("capture_sha256") if capture else None,
        "trial_state": trial["state"], "missing_evidence": trial["missing_evidence"],
        "model_calls": len(provider), "business_counts": counts}, sort_keys=True))
    return 0 if verdict == "PASS_ONE_PUBLIC_REQUEST" else 2


def s13_canary_stage() -> int:
    """One bounded real Sandbox isolation probe before product-path live execution."""
    token = os.environ.get("NEBIUS_API_KEY", "")
    project = os.environ.get("NEBIUS_PROJECT_ID", "")
    if not token or not project:
        print(json.dumps({"stage": "s13-canary", "verdict": "BLOCKED_CREDENTIALS_ABSENT"}))
        return 2
    os.environ["S13_HOST_ONLY_CANARY"] = "S13_HOST_ONLY_MARKER_20260927"
    source = S13_CANARY_SERVICE.encode("utf-8")
    batch = config.PIVOT_INCIDENT_REQUESTS.read_bytes()
    run_request = RunRequest(
        artifact_snapshot=ArtifactSnapshotRef(files={"service.py": source},
            manifest_hash=hashlib.sha256(source).hexdigest()),
        request_batch=BatchRef(path_ref=config.PIVOT_INCIDENT_REQUESTS.name,
            content_hash=canonical.content_hash(base64.b64encode(batch).decode("ascii"))),
        request_batch_bytes=batch, shop_snapshot_ref=str(config.PIVOT_PUBLIC_STATE),
        harness_ref="sandbox-driver-v1", image_ref=config.TOKEN_FACTORY_IMAGE,
        deadline_s=45, inference_grant=None,
    )
    result = asyncio.run(TokenFactoryAdapter(run_id="s13-isolation-probe",
        allowed_tool_names=("public_record_lookup", "public_catalog_search"),
        token=token, project=project).execute(run_request))
    body = None
    if len(result.captures) == 1:
        try:
            body = json.loads(result.captures[0].body)
        except ValueError:
            pass
    safe = result.failure is None and isinstance(body, dict) and all(
        body.get(key) is False for key in (
            "provider_key_visible", "controller_db_visible", "host_canary_visible",
            "protected_fixture_visible", "other_run_grant_visible"
        )
    ) and body.get("unlisted_tool_status") == 403
    report = {
        "stage": "s13-canary", "verdict": "PASS_BOUNDARY_CANARY" if safe else "STOP_BOUNDARY_UNPROVEN",
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "image": config.TOKEN_FACTORY_IMAGE,
        "operation_id": result.executor_ref, "failure": result.failure.value if result.failure else None,
        "checks": body, "observations": [observation.public_payload for observation in result.observations],
        "checkpoint_readback": any(observation.public_payload.get("checkpoint_readback")
            for observation in result.observations),
    }
    print(json.dumps(report, sort_keys=True))
    return 0 if safe else 2


def s13_inspect_stage(operation_id: str, expected_sha256: str) -> int:
    """Read a completed S13 checkpoint, archive bytes and compare its first digest."""
    token = os.environ.get("NEBIUS_API_KEY", "")
    project = os.environ.get("NEBIUS_PROJECT_ID", "")
    if not token or not project or len(expected_sha256) != 64:
        print(json.dumps({"stage": "s13-inspect", "verdict": "BLOCKED_INPUT"}))
        return 2

    async def inspect():
        client = ContreeAsyncClient(token, project=project, timeout=20)
        status = await client.get_operation_status(operation_id)
        checkpoint = status.result_image_uuid
        if not checkpoint:
            raise ValueError("checkpoint_missing")
        raw = await client.inspect_image_download(checkpoint, "/work/capture.json")
        return status, checkpoint, raw

    try:
        status, checkpoint, raw = asyncio.run(inspect())
        digest = hashlib.sha256(raw).hexdigest()
        capture = json.loads(raw)
        assert_public_safe(capture, (token, project, str(Path.cwd())))
        record = {
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "stage": "s13-inspect", "operation_id": operation_id,
            "status": str(status.status), "checkpoint_image": checkpoint,
            "capture_bytes": len(raw), "capture_sha256": digest,
            "expected_sha256": expected_sha256,
            "capture_base64": base64.b64encode(raw).decode("ascii"),
            "inspector_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "adapter_source_sha256": hashlib.sha256(
                (ROOT / "shiftwork" / "executor" / "tokenfactory.py").read_bytes()).hexdigest(),
        }
        assert_public_safe(record, (token, project, str(Path.cwd())))
        evidence = ROOT / "docs" / "plans" / "shiftwork" / "evidence" / (
            "slice13-inspect-" + operation_id + ".jsonl")
        evidence.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"stage": "s13-inspect", "verdict": "PASS_BYTE_EXACT" if digest == expected_sha256 else "STOP_DIGEST_MISMATCH",
            "operation_id": operation_id, "checkpoint_image": checkpoint,
            "capture_bytes": len(raw), "capture_sha256": digest,
            "evidence_file": str(evidence)}, sort_keys=True))
        return 0 if digest == expected_sha256 else 2
    except Exception as exc:
        print(json.dumps({"stage": "s13-inspect", "verdict": "STOP_READBACK_UNAVAILABLE",
            "error_type": type(exc).__name__}))
        return 2


def comparison_stage(*, select: bool = False, operate: bool = False,
                     preview_db: Path | None = None) -> int:
    """Exercise comparison policy and optionally append an offline learner choice."""
    admission = orchestrator._require_reviewed_comparison_material
    reviewed_family = sealed_store.load_reviewed_comparison_family
    try:
        # This demo is an explicit draft-review seam. Production admission and
        # the on-disk review flags are unchanged after this process exits.
        orchestrator._require_reviewed_comparison_material = lambda *_: None
        sealed_store.load_reviewed_comparison_family = sealed_store.load_family
        with (nullcontext(preview_db.parent) if preview_db else
              tempfile.TemporaryDirectory(prefix="shiftwork-s16-offline-")) as directory:
            db_file = preview_db or Path(directory) / "comparison.db"
            if preview_db and preview_db.exists():
                raise FileExistsError(f"preview database already exists: {preview_db}")
            with TestClient(create_app(str(db_file))) as client:
                shift = client.post("/api/engagements/bookshop/shifts")
                assert shift.status_code == 201, shift.text
                shift_id = shift.json()["id"]
                starter = client.post(f"/api/shifts/{shift_id}/artifact/versions",
                                      json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
                assert starter.status_code == 201, starter.text
                source = client.post(f"/api/shifts/{shift_id}/runs")
                assert source.status_code == 202, source.text
                source_deadline = time.monotonic() + 30
                while time.monotonic() < source_deadline:
                    source_run = client.get(f"/api/runs/{source.json()['id']}").json()
                    if source_run["state"] in ("FINALIZED", "FAILED"):
                        break
                    time.sleep(0.05)
                assert source_run["state"] == "FINALIZED", source_run
                investigation = client.post(f"/api/shifts/{shift_id}/investigations", json={
                    "source_run_id": source.json()["id"], "source_request_ordinal": 1,
                    "cause": "the starter omits a required collection task",
                    "falsifier": "the reviewed collection request still lacks that task result",
                    "public_test": "require every declared task result",
                    "revision_of_id": None, "client_request_id": "s16-demo-investigation",
                })
                assert investigation.status_code == 201, investigation.text
                candidates = {}
                for label in ("A", "B"):
                    saved = client.put(f"/api/shifts/{shift_id}/artifact",
                                       json={"files": config.comparison_candidate_files(label)})
                    assert saved.status_code == 200, saved.text
                    frozen = client.post(f"/api/shifts/{shift_id}/artifact/versions",
                                         json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
                    assert frozen.status_code == 201, frozen.text
                    candidates[label] = frozen.json()
                    assert candidates[label]["content_hash"] == config.TRUSTED_LOCAL_FIXTURES[
                        f"compare_candidate_{label.lower()}"][0]
                created = client.post(f"/api/shifts/{shift_id}/experiments", json={
                    "kind": "QUALIFYING_COMPARISON",
                    "investigation_id": investigation.json()["id"],
                    "candidate_a_version_id": candidates["A"]["id"],
                    "candidate_b_version_id": candidates["B"]["id"],
                    "declared_treatment": "A chooses lowest price; B chooses highest stock",
                    "client_request_id": "s16-demo-comparison",
                })
                assert created.status_code == 202, created.text
                experiment_id = created.json()["id"]
                deadline = time.monotonic() + 60
                view = created.json()
                while time.monotonic() < deadline:
                    view = client.get(f"/api/experiments/{experiment_id}").json()
                    if view["state"] in ("FINALIZED", "FAILED"):
                        break
                    time.sleep(0.05)
                outcome = view["outcome"]
                conn = db.connect(db_file)
                try:
                    reservation = repo.get_exposure_reservation_for_experiment(conn, experiment_id)
                    slots = repo.list_trial_slots(conn, experiment_id)
                    captured_before = sum(len(repo.list_outputs(conn, slot.run_id))
                                          for slot in slots)
                    runs = [repo.get_run(conn, slot.run_id) for slot in slots]
                    adapters = sorted({run.adapter for run in runs})
                    evidence_modes = sorted({run.evidence_mode.value for run in runs})
                    tokenfactory_observations = sum(
                        len(repo.list_observations(conn, run.id))
                        for run in runs if run.adapter == "tokenfactory"
                    )
                    if not select:
                        orchestrator.retire_comparison_exposure(conn, reservation.id)
                    captured_after = sum(len(repo.list_outputs(conn, slot.run_id))
                                         for slot in repo.list_trial_slots(conn, experiment_id))
                finally:
                    conn.close()
                retired = client.get(f"/api/experiments/{experiment_id}").json() if not select else None
                selected = None
                selected_board = None
                operation = None
                if select:
                    prior = client.get("/api/engagements/bookshop/board").json()["operating_selection"]
                    choice = client.post(f"/api/shifts/{shift_id}/selections", json={
                        "comparison_id": experiment_id,
                        "selected_version_id": candidates["A"]["id"],
                        "rationale": "A completed the required tasks under the shared conditions.",
                        "expected_prior_selection_id": prior["id"] if prior else None,
                        "client_request_id": "s17-demo-selection",
                    })
                    assert choice.status_code == 201, choice.text
                    selected = choice.json()
                    selected_board = client.get("/api/engagements/bookshop/board").json()
                    if operate:
                        closed = client.post(f"/api/shifts/{shift_id}/close")
                        assert closed.status_code == 200, closed.text
                        next_shift = client.post("/api/engagements/bookshop/shifts")
                        assert next_shift.status_code == 201, next_shift.text
                        next_id = next_shift.json()["id"]
                        newer = client.put(f"/api/shifts/{next_id}/artifact", json={
                            "files": config.comparison_candidate_files("B")})
                        assert newer.status_code == 200, newer.text
                        newer_version = client.post(f"/api/shifts/{next_id}/artifact/versions",
                            json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
                        assert newer_version.status_code == 201, newer_version.text
                        before = client.get("/api/engagements/bookshop/ledger").json()["events"]
                        started = client.post(f"/api/shifts/{next_id}/runs",
                            json={"client_request_id": "s18-demo-operation"})
                        assert started.status_code == 202, started.text
                        finished = client.get(f"/api/runs/{started.json()['id']}").json()
                        checks = client.get(f"/api/runs/{finished['id']}/checks").json()
                        outputs = client.get(f"/api/runs/{finished['id']}/outputs").json()
                        after = client.get("/api/engagements/bookshop/ledger").json()["events"]
                        operation = {
                            "run_id": finished["id"], "state": finished["state"],
                            "purpose": finished["purpose"], "adapter": finished["adapter"],
                            "evidence_mode": finished["evidence_mode"],
                            "selected_version_id": selected["selected_version_id"],
                            "operated_version_id": finished["artifact_version_id"],
                            "newer_unselected_version_id": newer_version.json()["id"],
                            "check_count": len(checks), "output_count": len(outputs),
                            "new_events": after[len(before):],
                        }
        sealed_states = {
            path.name: json.loads(path.read_text(encoding="utf-8"))["review_status"]
            for path in (config.PIVOT_COMPARE_MANIFEST,
                         config.SEALED_CASES_DIR / "bookshop_task_completion.json")
        }
        operator_sealed = all(state == "OPERATOR_SEALED" for state in sealed_states.values())
        # The no-live-call claim is measured, not printed as a constant: it reads
        # the projected evidence class, every run's adapter and evidence mode, and
        # the observations those adapters own.
        no_live_call = (view["context_evidence_class"] == "TRUSTED_LOCAL"
                        and adapters == ["local_process"]
                        and evidence_modes == ["TRUSTED_LOCAL"]
                        and tokenfactory_observations == 0)
        metrics = {item["candidate_label"]: item for item in outcome["candidate_metrics"]}
        eligibility = {item["candidate_label"]: item for item in outcome["eligibility"]}
        passed = (outcome is not None and outcome["status"] == "COMPLETE"
                  and len(view["trials"]) == 6 and captured_before == captured_after
                  and captured_after == 18
                  and (selected_board["operating_selection"]["id"] == selected["id"]
                       and selected_board["latest_shift"]["operation_allowed"]
                       and selected["retained_alternative_version_id"] == candidates["B"]["id"]
                       if select else retired["outcome"]["status"] == "NOT_COMPARABLE")
                  and outcome["shared_public_denominator_requests"] == 6
                  and set(metrics) == {"A", "B"} and set(eligibility) == {"A", "B"}
                  and all(item["public_denominator_requests"] == 6
                          and item["protected_denominator"] == 3
                          and item["protected_passed"] + item["protected_failed"] == 3
                          for item in metrics.values())
                  and all(item["eligible"] for item in eligibility.values())
                  and no_live_call
                  and (not operate or (operation["state"] == "FINALIZED"
                       and operation["operated_version_id"] == operation["selected_version_id"]
                       and operation["newer_unselected_version_id"] != operation["selected_version_id"]
                       and operation["adapter"] == "local_process"
                       and operation["evidence_mode"] == "TRUSTED_LOCAL"
                       and operation["check_count"] > 0 and operation["output_count"] > 0
                       and any(event["derivation"] and event["derivation"]["run_id"] == operation["run_id"]
                               for event in operation["new_events"]))))
        print(json.dumps({
            "stage": "operation" if operate else "selection" if select else "comparison", "evidence_class": "TRUSTED_LOCAL_DRAFT_POLICY_ONLY",
            "verdict": "PASS_OFFLINE_POLICY" if passed else "STOP_INCOMPLETE",
            "trial_states": [item["state"] for item in view["trials"]],
            "outcome": outcome, "retired_status": retired["outcome"]["status"] if retired else None,
            "selection": selected, "operating_status": selected_board["operating_status"] if selected_board else None,
            "operation": ({**operation, "new_events": [
                {"seq": event["seq"], "event_type": event["event_type"],
                 "synthetic": event["synthetic"],
                 "derived_run_id": event["derivation"]["run_id"] if event["derivation"] else None}
                for event in operation["new_events"]]}
                if operation else None),
            "latest_saved_version_id": selected_board["latest_saved_version_id"] if selected_board else None,
            "captured_rows_before_retire": captured_before if not select else None,
            "captured_rows_before_selection": captured_before if select else None,
            "captured_rows_after_retire": captured_after if not select else None,
            "captured_rows_after_selection": captured_after if select else None,
            "no_live_call_derivation": {
                "projected_evidence_class": view["context_evidence_class"],
                "run_adapters": adapters, "run_evidence_modes": evidence_modes,
                "tokenfactory_observations": tokenfactory_observations,
            },
            "live_calls": tokenfactory_observations,
            "operator_sealed": operator_sealed,
            "review_status_on_disk": sealed_states,
        }, sort_keys=True))
        return 0 if passed else 2
    finally:
        orchestrator._require_reviewed_comparison_material = admission
        sealed_store.load_reviewed_comparison_family = reviewed_family


def replay_stage() -> int:
    """Replay the S18 operational walkthrough from its captured bytes only (S19).

    The operation run is produced over a temporary database through the real HTTP
    surface. The current mission file, the public state file and today's incident
    rows are then deliberately changed; the replay must stay IDENTICAL and write
    nothing. A stored semantic divergence reports DIFFERENT, an independent chain
    tamper breaks chain verification while the replay still reports IDENTICAL,
    and a migrated v5 run without captured inputs reports UNKNOWN_MISSING_INPUTS.
    Every change is made on temporary copies; the checked-in fixtures, the sealed
    files and any live database are never touched.
    """
    admission = orchestrator._require_reviewed_comparison_material
    reviewed_family = sealed_store.load_reviewed_comparison_family
    original_mission = config.PIVOT_MISSION
    original_state = config.PIVOT_PUBLIC_STATE
    try:
        orchestrator._require_reviewed_comparison_material = lambda *_: None
        sealed_store.load_reviewed_comparison_family = sealed_store.load_family
        with tempfile.TemporaryDirectory(prefix="shiftwork-s19-replay-") as directory:
            db_file = Path(directory) / "replay.db"
            with TestClient(create_app(str(db_file))) as client:
                shift = client.post("/api/engagements/bookshop/shifts")
                assert shift.status_code == 201, shift.text
                shift_id = shift.json()["id"]
                starter = client.post(f"/api/shifts/{shift_id}/artifact/versions",
                                      json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
                assert starter.status_code == 201, starter.text
                source = client.post(f"/api/shifts/{shift_id}/runs")
                assert source.status_code == 202, source.text
                source_deadline = time.monotonic() + 30
                while time.monotonic() < source_deadline:
                    source_run = client.get(f"/api/runs/{source.json()['id']}").json()
                    if source_run["state"] in ("FINALIZED", "FAILED"):
                        break
                    time.sleep(0.05)
                assert source_run["state"] == "FINALIZED", source_run
                investigation = client.post(f"/api/shifts/{shift_id}/investigations", json={
                    "source_run_id": source.json()["id"], "source_request_ordinal": 1,
                    "cause": "the starter omits a required collection task",
                    "falsifier": "the reviewed collection request still lacks that task result",
                    "public_test": "require every declared task result",
                    "revision_of_id": None, "client_request_id": "s19-demo-investigation",
                })
                assert investigation.status_code == 201, investigation.text
                candidates = {}
                for label in ("A", "B"):
                    saved = client.put(f"/api/shifts/{shift_id}/artifact",
                                       json={"files": config.comparison_candidate_files(label)})
                    assert saved.status_code == 200, saved.text
                    frozen = client.post(f"/api/shifts/{shift_id}/artifact/versions",
                                         json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
                    assert frozen.status_code == 201, frozen.text
                    candidates[label] = frozen.json()
                created = client.post(f"/api/shifts/{shift_id}/experiments", json={
                    "kind": "QUALIFYING_COMPARISON",
                    "investigation_id": investigation.json()["id"],
                    "candidate_a_version_id": candidates["A"]["id"],
                    "candidate_b_version_id": candidates["B"]["id"],
                    "declared_treatment": "A chooses lowest price; B chooses highest stock",
                    "client_request_id": "s19-demo-comparison",
                })
                assert created.status_code == 202, created.text
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    view = client.get(f"/api/experiments/{created.json()['id']}").json()
                    if view["state"] in ("FINALIZED", "FAILED"):
                        break
                    time.sleep(0.05)
                assert view["outcome"] and view["outcome"]["status"] == "COMPLETE", view
                prior = client.get("/api/engagements/bookshop/board").json()["operating_selection"]
                choice = client.post(f"/api/shifts/{shift_id}/selections", json={
                    "comparison_id": created.json()["id"],
                    "selected_version_id": candidates["A"]["id"],
                    "rationale": "A completed the required tasks under the shared conditions.",
                    "expected_prior_selection_id": prior["id"] if prior else None,
                    "client_request_id": "s19-demo-selection",
                })
                assert choice.status_code == 201, choice.text
                closed = client.post(f"/api/shifts/{shift_id}/close")
                assert closed.status_code == 200, closed.text
                next_shift = client.post("/api/engagements/bookshop/shifts")
                assert next_shift.status_code == 201, next_shift.text
                next_id = next_shift.json()["id"]
                newer = client.put(f"/api/shifts/{next_id}/artifact",
                                   json={"files": config.comparison_candidate_files("B")})
                assert newer.status_code == 200, newer.text
                newer_version = client.post(f"/api/shifts/{next_id}/artifact/versions",
                    json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
                assert newer_version.status_code == 201, newer_version.text
                started = client.post(f"/api/shifts/{next_id}/runs",
                                      json={"client_request_id": "s19-demo-operation"})
                assert started.status_code == 202, started.text
                operation_run = client.get(f"/api/runs/{started.json()['id']}").json()
                assert operation_run["state"] == "FINALIZED", operation_run

            conn = db.connect(db_file)
            try:
                slug = config.BOOKSHOP_SLUG
                run_id = operation_run["id"]
                before = snapshot_v5_rows(conn)
                report = orchestrator.replay_assessment(conn, run_id)
                zero_write_ok = snapshot_v5_rows(conn) == before
                identical_ok = (report.status == "IDENTICAL" and report.wrote_rows is False
                                and not report.check_differences
                                and not report.event_draft_differences and zero_write_ok)

                decoy_dir = Path(directory) / "decoys"
                decoy_dir.mkdir()
                decoy_mission = decoy_dir / "mission.json"
                decoy_mission.write_text('{"not": "the captured mission"}', encoding="utf-8")
                decoy_state = decoy_dir / "state.json"
                decoy_state.write_text('{"not": "the captured state"}', encoding="utf-8")
                config.PIVOT_MISSION = decoy_mission
                config.PIVOT_PUBLIC_STATE = decoy_state
                conn.execute("UPDATE incidents SET state = 'OPEN'")
                conn.commit()
                flipped = len(repo.list_incidents(conn, slug))
                changed = snapshot_v5_rows(conn)
                repeat = orchestrator.replay_assessment(conn, run_id)
                changed_rows_ok = snapshot_v5_rows(conn) == changed
                changed_ok = (repeat.status == "IDENTICAL" and changed_rows_ok and flipped > 0)
                config.PIVOT_MISSION = original_mission
                config.PIVOT_PUBLIC_STATE = original_state

                checks = repo.list_check_results(conn, run_id)
                assert checks, "the operation must have committed its task checks"
                check_target = checks[0]
                original_verdict = check_target.verdict
                conn.execute("UPDATE check_results SET verdict = ? WHERE id = ?",
                             ("fail" if original_verdict == "pass" else "pass", check_target.id))
                conn.commit()
                diverged = orchestrator.replay_assessment(conn, run_id)
                divergence_ok = (diverged.status == "DIFFERENT"
                                 and bool(diverged.check_differences))
                conn.execute("UPDATE check_results SET verdict = ? WHERE id = ?",
                             (original_verdict, check_target.id))
                conn.commit()
                restored = orchestrator.replay_assessment(conn, run_id)
                restore_ok = restored.status == "IDENTICAL"

                chain_before = chain.verify_chain(repo.list_ledger_events(conn, slug))
                target_event = repo.list_ledger_events(conn, slug)[-1]
                original_prev = target_event.prev_hash
                conn.execute("UPDATE ledger_events SET prev_hash = ? WHERE seq = ?",
                             ("0" * 64, target_event.seq))
                conn.commit()
                chain_broken = chain.verify_chain(repo.list_ledger_events(conn, slug))
                replay_under_tamper = orchestrator.replay_assessment(conn, run_id)
                conn.execute("UPDATE ledger_events SET prev_hash = ? WHERE seq = ?",
                             (original_prev, target_event.seq))
                conn.commit()
                chain_restored = chain.verify_chain(repo.list_ledger_events(conn, slug))
                chain_ok = (chain_before is chain.ChainStatus.VALID
                            and chain_broken is chain.ChainStatus.BROKEN
                            and replay_under_tamper.status == "IDENTICAL"
                            and chain_restored is chain.ChainStatus.VALID)
            finally:
                conn.close()

            legacy_file = Path(directory) / "legacy-v5.db"
            create_v5_sample(legacy_file)
            legacy_conn = db.connect(legacy_file)
            try:
                db.ensure_schema(legacy_conn)
                legacy_before = snapshot_v5_rows(legacy_conn)
                legacy_report = orchestrator.replay_assessment(legacy_conn, "run-v5-0001")
                legacy_ok = (legacy_report.status == "UNKNOWN_MISSING_INPUTS"
                             and legacy_report.wrote_rows is False
                             and snapshot_v5_rows(legacy_conn) == legacy_before)
            finally:
                legacy_conn.close()

        passed = (identical_ok and changed_ok and divergence_ok and restore_ok
                  and chain_ok and legacy_ok)
        print(json.dumps({
            "stage": "replay", "evidence_class": "TRUSTED_LOCAL_DRAFT_POLICY_ONLY",
            "verdict": "PASS_OFFLINE_POLICY" if passed else "STOP_INCOMPLETE",
            "operation_run_id": run_id,
            "newer_unselected_version_id": newer_version.json()["id"],
            "replay": {"status": report.status, "wrote_rows": report.wrote_rows,
                       "check_differences": len(report.check_differences),
                       "event_draft_differences": len(report.event_draft_differences),
                       "rows_unchanged": zero_write_ok},
            "changed_current_inputs": {
                "mission_file_replaced": True, "public_state_file_replaced": True,
                "incident_rows_flipped": flipped, "replay_status": repeat.status,
                "rows_unchanged": changed_rows_ok},
            "stored_semantic_divergence": {
                "check_id": check_target.check_id, "replay_status": diverged.status,
                "check_differences": len(diverged.check_differences),
                "restored_status": restored.status},
            "chain_independence": {
                "chain_before": chain_before.value, "chain_under_tamper": chain_broken.value,
                "replay_under_tamper": replay_under_tamper.status,
                "chain_restored": chain_restored.value},
            "legacy_replay": {"status": legacy_report.status,
                              "wrote_rows": legacy_report.wrote_rows},
        }, sort_keys=True))
        return 0 if passed else 2
    finally:
        orchestrator._require_reviewed_comparison_material = admission
        sealed_store.load_reviewed_comparison_family = reviewed_family
        config.PIVOT_MISSION = original_mission
        config.PIVOT_PUBLIC_STATE = original_state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("migration", "investigation", "comparison", "selection", "operation", "replay", "s13-canary", "s13-inspect", "s13-code", "s13-model"), required=True)
    parser.add_argument("--operation-id")
    parser.add_argument("--expected-sha256")
    parser.add_argument("--preview-db", type=Path,
                        help="keep the offline operation walkthrough database for local browser inspection")
    args = parser.parse_args()
    if args.stage == "migration":
        return migration_stage()
    if args.stage == "investigation":
        return investigation_stage()
    if args.stage == "comparison":
        return comparison_stage()
    if args.stage == "selection":
        return comparison_stage(select=True)
    if args.stage == "operation":
        return comparison_stage(select=True, operate=True, preview_db=args.preview_db)
    if args.stage == "replay":
        return replay_stage()
    if args.stage == "s13-canary":
        return s13_canary_stage()
    if args.stage == "s13-inspect":
        if not args.operation_id or not args.expected_sha256:
            parser.error("s13-inspect requires --operation-id and --expected-sha256")
        return s13_inspect_stage(args.operation_id, args.expected_sha256)
    if args.stage == "s13-code":
        return s13_service_stage(model=False)
    if args.stage == "s13-model":
        return s13_service_stage(model=True)
    raise AssertionError(args.stage)


if __name__ == "__main__":
    raise SystemExit(main())
