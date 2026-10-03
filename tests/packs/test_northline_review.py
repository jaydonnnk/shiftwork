"""S22a admitted material, preserved history and trusted-local failure reproduction.

No comparison, selection, operation, deployment success or isolated run is proved.
"""
import base64
import hashlib
import http.client
import json
import runpy
import shutil
import sqlite3
from http.server import HTTPServer
from threading import Thread

import pytest
from fastapi.testclient import TestClient

from demos.final_pivot import _bytes, create_v5_sample, snapshot_v5_rows

from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain import task_contract
from shiftwork.domain.models import ReasonCode
from shiftwork.evaluator import evaluator
from shiftwork.packs import registry
from shiftwork.sealed import store
from shiftwork.store import db
from packs.material import apply_staged_material


def test_actual_northline_material_is_admitted_with_all_reviewed_bindings():
    pack = registry.resolve_pack("northline")
    assert len(pack.reviewed_pins) == 24, "all reviewed Northline material must be bound"
    assert len(pack.documents) == 6, "every Northline station needs its reviewed document"
    assert orchestrator.admit_pack("northline") == pack, "real Northline admission must pass"
    assert [b.availability for b in orchestrator.workplace_boards()] == [
        "AVAILABLE", "AWAITING_OPERATOR_REVIEW", "AVAILABLE"]
    family = store.load_declared_family(pack.families[0], slug=pack.slug)
    assert len(family.cases) == 6
    assert {doc.station for doc in pack.documents} == set(pack.display.station_labels)
    pins = {p.path: p.sha256 for p in pack.reviewed_pins}
    for doc in pack.documents:
        assert pins[doc.path] == doc.sha256
    assert registry.resolve_pack("gtm").reviewed_pins == ()


@pytest.mark.parametrize("path", [pin.path for pin in registry.resolve_pack("northline").reviewed_pins])
def test_every_northline_reviewed_file_drift_refuses_before_seed(tmp_path, monkeypatch, path):
    original = config.PACKAGE_DIR
    root = tmp_path / "package"
    apply_staged_material(monkeypatch, root, {})
    target = root / path
    target.write_bytes(target.read_bytes() + b" ")
    # Leave the literal reviewed pin intact so this is actual pin drift.
    with pytest.raises(registry.PackUnavailable):
        orchestrator.admit_pack("northline")
    conn = db.connect(tmp_path / "blocked.db")
    try:
        db.ensure_schema(conn)
        orchestrator.seed_registered_engagements(conn)
        assert [row[0] for row in conn.execute("SELECT slug FROM engagements")] == ["bookshop"], "drifted material must not seed Northline"
        assert conn.execute("SELECT count(*) FROM shifts").fetchone()[0] == 0
    finally:
        conn.close()
    assert (original / path).read_bytes() != target.read_bytes()


@pytest.mark.parametrize("path,field", [
    ("fixtures/requests/northline_compare_manifest.json", "review_status"),
    ("fixtures/requests/northline_compare_manifest.json", "sealed_payload_sha256"),
    ("sealed/cases/northline_deployment.json", "review_status"),
    ("sealed/cases/northline_deployment.json", "sealed_payload_sha256"),
], ids=["manifest_status", "manifest_digest", "family_status", "family_digest"])
def test_unsealed_northline_refuses_even_with_matching_disposable_pin(tmp_path, monkeypatch, path, field):
    raw = json.loads((config.PACKAGE_DIR / path).read_bytes())
    raw[field] = "DRAFT" if field == "review_status" else "0" * 64
    apply_staged_material(monkeypatch, tmp_path / "package", {path: json.dumps(raw).encode()})
    with pytest.raises(registry.PackUnavailable):
        orchestrator.admit_pack("northline")


def rows(conn, table):
    return tuple(tuple(row) for row in conn.execute("SELECT * FROM " + table + " ORDER BY rowid"))


@pytest.mark.parametrize("doc_id", [doc.doc_id for doc in registry.resolve_pack("northline").documents])
def test_each_northline_document_must_match_its_reviewed_pin(monkeypatch, doc_id):
    packs = registry.registered_packs()
    pack = packs[2]
    documents = tuple(doc.model_copy(update={"sha256": "0" * 64}) if doc.doc_id == doc_id else doc
                      for doc in pack.documents)
    monkeypatch.setattr(registry, "_PACKS", (*packs[:2], pack.model_copy(update={"documents": documents})))
    with pytest.raises(registry.PackUnavailable):
        orchestrator.admit_pack("northline")


def test_real_northline_seed_is_idempotent_and_preserves_existing_bellwether(tmp_path, monkeypatch):
    path = tmp_path / "seed.db"
    conn = db.connect(path)
    try:
        db.ensure_schema(conn)
        packs = registry.registered_packs()
        with monkeypatch.context() as before_northline:
            before_northline.setattr(registry, "_PACKS", (packs[0], packs[1], packs[2].model_copy(update={"reviewed_pins": ()})))
            orchestrator.seed_registered_engagements(conn)
        conn.execute("UPDATE engagements SET display_name = 'historical Bellwether' WHERE slug = 'bookshop'")
        conn.execute("UPDATE engagement_config SET assist_level = 'historical level', total_assist_budget_per_shift = 7 WHERE slug = 'bookshop'")
        conn.commit()
        tables = ("engagements", "engagement_config", "engagement_assist_policy")
        history = {table: rows(conn, table) for table in tables}
        orchestrator.seed_registered_engagements(conn)
        assert [row[0] for row in conn.execute("SELECT slug FROM engagements ORDER BY slug")] == ["bookshop", "northline"], "admitted Northline must seed once"
        for table in tables:
            assert set(history[table]).issubset(set(rows(conn, table))), "seeding must preserve historical Bellwether values"
        current = conn.execute("SELECT * FROM engagement_assist_policy WHERE slug = 'northline'").fetchone()
        assert current["assist_level"] == "reduced"
        assert json.loads(current["allowed_assist_roles_json"]) == ["HINT"]
        assert current["total_assist_budget_per_shift"] == 1
        after = {table: rows(conn, table) for table in tables}
        for _ in range(3):
            orchestrator.seed_registered_engagements(conn)
        assert after == {table: rows(conn, table) for table in tables}, "repeat seeding must leave every value unchanged"
        for table in ("shifts", "artifact_versions", "exposure_items", "operating_selections", "ledger_events", "incidents"):
            assert conn.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
    finally:
        conn.close()
    with TestClient(create_app(str(path))):
        pass
    conn = db.connect(path)
    try:
        assert after == {table: rows(conn, table) for table in tables}, "app restart must preserve admitted engagement rows"
    finally:
        conn.close()


@pytest.mark.parametrize("with_run", [True, False])
def test_admitted_northline_startup_preserves_all_original_v5_bytes(tmp_path, with_run):
    original = tmp_path / "original-v5.db"
    copied = tmp_path / "admitted-startup.db"
    create_v5_sample(original, with_run=with_run)
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest()
    source = sqlite3.connect(original)
    try:
        before = snapshot_v5_rows(source)
    finally:
        source.close()
    shutil.copyfile(original, copied)
    for _ in range(2):
        with TestClient(create_app(str(copied))):
            pass
        conn = db.connect(copied)
        try:
            for table, (columns, expected) in before.items():
                current = tuple(b"".join(_bytes(value) for value in row) for row in conn.execute(
                    f"SELECT {', '.join(columns)} FROM {table} ORDER BY rowid"))
                if table in ("engagements", "engagement_config"):
                    assert current[:len(expected)] == expected, f"historical {table} bytes changed during admitted seeding"
                    assert len(current) == len(expected) + 1
                    assert conn.execute(f"SELECT count(*) FROM {table} WHERE slug = 'northline'").fetchone()[0] == 1
                else:
                    assert current == expected, f"historical {table} bytes changed during admitted seeding"
            assert conn.execute("SELECT count(*) FROM shifts WHERE engagement_slug = 'northline'").fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM operating_selections").fetchone()[0] == 0
            assert conn.execute("SELECT count(*) FROM exposure_items").fetchone()[0] == 0
        finally:
            conn.close()
    assert hashlib.sha256(original.read_bytes()).hexdigest() == original_hash


def capture_reviewed_blank():
    """Exercise the exact approved HTTP handler on loopback, not LocalProcessAdapter."""
    pack = orchestrator.admit_pack("northline")
    raw = (config.PACKAGE_DIR / "templates/artifact/northline_blank_service.py").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == next(p.sha256 for p in pack.reviewed_pins
                                                  if p.path == "templates/artifact/northline_blank_service.py")
    state_bytes = (config.PACKAGE_DIR / pack.public_state_path).read_bytes()
    request_bytes = (config.PACKAGE_DIR / pack.incident_request_path).read_bytes()
    request = json.loads(request_bytes.splitlines()[0])
    module = runpy.run_path(str(config.PACKAGE_DIR / "templates/artifact/northline_blank_service.py"), run_name="s22a_reviewed_blank")
    server = HTTPServer(("127.0.0.1", 0), module["Handler"])
    server.snapshot = json.loads(state_bytes)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
    try:
        connection.request("POST", "/", body=json.dumps(request).encode(), headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        status, body = response.status, response.read()
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert not thread.is_alive()
    mission = task_contract.load_mission(config.PACKAGE_DIR / pack.mission_path)
    spec = mission.request_specs[0]
    assert request["request_id"] == spec.id and request["text"] == spec.text
    envelope = task_contract.validate_response_envelope(spec, body)
    assessments = evaluator.assess_request(spec=spec, request_ordinal=request["ordinal"], mission=mission,
                                           snapshot=task_contract.load_public_state_bytes(state_bytes), response=envelope)
    return {"source_sha256": hashlib.sha256(raw).hexdigest(),
            "request_bytes_sha256": hashlib.sha256(request_bytes).hexdigest(),
            "public_state_sha256": hashlib.sha256(state_bytes).hexdigest(),
            "request_id": spec.id, "http_status": status, "body_base64": base64.b64encode(body).decode(),
            "response": envelope.model_dump(mode="json"),
            "assessments": [a.model_dump(mode="json") for a in assessments],
            "usefully_completed": evaluator.request_usefully_completed(spec, assessments),
            "evidence_mode": "TRUSTED_LOCAL_HTTP_HANDLER",
            "limits": "No deployment success, isolated executor, durable booking, selection or operation proof."}


def test_reviewed_blank_http_starter_reproduces_missing_booking_result():
    result = capture_reviewed_blank()
    assert result["http_status"] == 200, "reviewed blank handler must return a usable capture"
    assert result["request_id"] == "northline-incident-001"
    assert result["response"]["task_results"] == []
    assert len(result["assessments"]) == 1
    assessment = result["assessments"][0]
    assert assessment["task_id"] == "booking" and assessment["outcome"] == "MISSING_OUTPUT"
    assert assessment["mandatory_pass"] is False, "missing required booking must fail independently"
    assert assessment["reason_codes"] == [ReasonCode.REQUIRED_TASK_MISSING.value]
    assert result["usefully_completed"] is False
