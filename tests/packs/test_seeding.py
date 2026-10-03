"""Registered-pack seeding: real admission, disposable material, no execution."""

import hashlib
import json
import base64
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from shiftwork import comparison_flow, config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain import contract_catalog, task_contract
from shiftwork.domain.comparison import acceptance_aspect
from shiftwork.evaluator.evaluator import SealedCase
from shiftwork.domain.models import Shift
from shiftwork.gateway.redaction import assert_public_safe
from shiftwork.packs import registry
from shiftwork.sealed import store as sealed_store
from shiftwork.store import db, repo


@pytest.fixture
def reviewed_disposable_pack(tmp_path, monkeypatch):
    """A second, distinct test pack; production Northline remains untouched."""
    original = config.PACKAGE_DIR
    root = tmp_path / "package"
    bookshop = registry.resolve_pack("bookshop")
    for pin in bookshop.reviewed_pins:
        target = root / pin.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((original / pin.path).read_bytes())

    def renamed(path):
        return path.replace("bookshop", "disposable")

    for pin in bookshop.reviewed_pins:
        path = root / renamed(pin.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (original / pin.path).read_bytes()
        if pin.path.endswith(".json"):
            data = json.loads(raw)
            if "engagement_slug" in data:
                data["engagement_slug"] = "disposable"
            if "cases" in data:
                data["family"] = "disposable_" + data["family"]
                for case in data["cases"]:
                    if case.get("stimulus") is not None:
                        case["expected"]["aspect"] = acceptance_aspect(
                            SealedCase.model_validate(case)).model_dump(mode="json")
                    case["family"] = data["family"]
                    case["id"] = "disposable-" + case["id"]
                    case["check_id"] = "disposable-" + case["check_id"]
                if "sealed_payload_sha256" in data:
                    data["sealed_payload_sha256"] = hashlib.sha256(json.dumps(
                        data["cases"], sort_keys=True, separators=(",", ":"),
                        ensure_ascii=False).encode()).hexdigest()
            if "workloads" in data:
                for entry in data["workloads"]:
                    for field in ("request_file", "task_spec_file"):
                        entry[field] = renamed(entry[field])
                data["sealed_payload_sha256"] = hashlib.sha256(json.dumps(
                    data["workloads"], sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False).encode()).hexdigest()
            if "options" in data:
                data["content_hash"] = contract_catalog.compute_catalog_hash(data)
            raw = json.dumps(data).encode()
        path.write_bytes(raw)
    catalog = json.loads((root / "fixtures/catalogs/disposable_v3.json").read_bytes())
    mission_path = root / renamed(bookshop.mission_path)
    mission = json.loads(mission_path.read_bytes())
    mission["contract_catalog_hash"] = catalog["content_hash"]
    mission_path.write_bytes(json.dumps(mission).encode())
    manifest_path = root / renamed(bookshop.manifest_path)
    manifest = json.loads(manifest_path.read_bytes())
    manifest["comparison_state_sha256"] = hashlib.sha256(
        (root / renamed(bookshop.comparison_state_path)).read_bytes()).hexdigest()
    manifest_path.write_bytes(json.dumps(manifest).encode())
    pins = tuple(registry.ReviewedPin(path=renamed(pin.path), sha256=hashlib.sha256(
        (root / renamed(pin.path)).read_bytes()).hexdigest()) for pin in bookshop.reviewed_pins)
    declaration = bookshop.model_copy(update={
        "slug": "disposable",
        "display": registry.resolve_pack("northline").display,
        "assist": registry.resolve_pack("northline").assist,
        **{field: renamed(getattr(bookshop, field)) for field in (
            "mission_path", "public_state_path", "comparison_state_path",
            "incident_request_path", "manifest_path")},
        "families": tuple(f.model_copy(update={
            "family": "disposable_" + f.family, "case_file": renamed(f.case_file)
        }) for f in bookshop.families),
        "reviewed_pins": pins,
    })
    monkeypatch.setattr(config, "PACKAGE_DIR", root)
    monkeypatch.setattr(config, "CATALOG_DIR", root / "fixtures/catalogs")
    monkeypatch.setattr(config, "SEALED_CASES_DIR", root / "sealed/cases")
    monkeypatch.setattr(registry, "_PACKS", (*registry.registered_packs(), declaration))
    assert orchestrator.admit_pack("disposable") == declaration
    return root, declaration


def rows(conn, table):
    return [tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY slug")]


def test_startup_seeds_only_admitted_packs_idempotently(tmp_path, reviewed_disposable_pack):
    path = tmp_path / "seeding.db"
    app = create_app(str(path))
    with TestClient(app):
        pass
    conn = db.connect(str(path))
    try:
        assert [row["slug"] for row in conn.execute("SELECT slug FROM engagements ORDER BY slug")] == [
            "bookshop", "disposable"], "startup must seed every admitted pack and no unavailable pack"
        pack = registry.resolve_pack("disposable")
        engagement = repo.get_engagement(conn, pack.slug)
        assert engagement["business_kind"] == pack.slug
        assert engagement["display_name"] == pack.display.client
        current = repo.get_engagement_assist_policy(conn, pack.slug)
        assert current["assist_level"] == "reduced"
        assert json.loads(current["allowed_assist_roles_json"]) == ["HINT"]
        assert current["total_assist_budget_per_shift"] == 1
        assert json.loads(repo.get_engagement_config(conn, pack.slug)["enabled_check_families_json"]) == [
            f.family for f in pack.families if f.family_class is registry.FamilyClass.ATTEMPT]
        assert conn.execute("SELECT count(*) FROM shifts").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM artifact_versions").fetchone()[0] == 0
        conn.execute("UPDATE engagements SET display_name = 'historical display' WHERE slug = 'bookshop'")
        conn.execute("UPDATE engagement_config SET assist_level = 'historical level', "
                     "total_assist_budget_per_shift = 7 WHERE slug = 'bookshop'")
        conn.commit()
        before = {t: rows(conn, t) for t in ("engagements", "engagement_config", "engagement_assist_policy")}
    finally:
        conn.close()
    with TestClient(app):
        pass
    conn = db.connect(str(path))
    try:
        assert {t: rows(conn, t) for t in before} == before, "restart must retain all existing row values"
    finally:
        conn.close()


def test_public_context_reads_owning_pack(tmp_path, reviewed_disposable_pack, monkeypatch):
    root, pack = reviewed_disposable_pack
    conn = db.connect(str(tmp_path / "context.db"))
    try:
        db.ensure_schema(conn)
        orchestrator.seed_registered_engagements(conn)
        shift = Shift(id="disposable-shift-01", engagement_slug=pack.slug, seq=1,
                      state="open", opened_at=datetime.now(timezone.utc))
        for field in ("PIVOT_MISSION", "PIVOT_PUBLIC_STATE", "PIVOT_INCIDENT_REQUESTS"):
            monkeypatch.setattr(config, field, root / "nonexistent-global-material")
        context, failure = None, None
        try:
            context = orchestrator.freeze_diagnostic_context(conn, shift)
        except Exception as exc:
            failure = exc
        assert context is not None, f"owning-pack context was refused: {failure}"
        assert context.engagement_slug == pack.slug
        assert base64.b64decode(context.mission_bytes_base64) == (root / pack.mission_path).read_bytes()
        assert base64.b64decode(context.public_data_bytes_base64) == (root / pack.public_state_path).read_bytes()
        assert base64.b64decode(context.workloads[0].request_batch_bytes_base64) == (
            root / pack.incident_request_path).read_bytes()
        assert context.protected_reservation_id is None
        assert conn.execute("SELECT count(*) FROM exposure_reservations").fetchone()[0] == 0
    finally:
        conn.close()


def test_comparison_workloads_read_owning_manifest(reviewed_disposable_pack, monkeypatch):
    root, pack = reviewed_disposable_pack
    mission = task_contract.load_mission(root / pack.mission_path)
    snapshot_bytes = (root / pack.comparison_state_path).read_bytes()
    monkeypatch.setattr(config, "PIVOT_COMPARE_MANIFEST", root / "nonexistent-global-manifest")
    monkeypatch.setattr(config, "PIVOT_COMPARE_REQUEST_DIR", root / "nonexistent-global-requests")
    workloads, failure = None, None
    try:
        workloads = comparison_flow._read_comparison_workloads(pack.slug, mission, snapshot_bytes)
    except Exception as exc:
        failure = exc
    assert workloads is not None, f"owning-pack workloads were refused: {failure}"
    manifest = json.loads((root / pack.manifest_path).read_bytes())
    assert [w.ordinal for w in workloads] == [1, 2, 3]
    for workload, entry in zip(workloads, manifest["workloads"], strict=True):
        assert base64.b64decode(workload.request_batch_bytes_base64) == (
            root / pack.manifest_path).parent.joinpath(entry["request_file"]).read_bytes()


@pytest.mark.parametrize("fault", ("missing", "stale_pin", "unsealed"))
def test_unavailable_pack_never_seeds_and_existing_history_survives(
    tmp_path, reviewed_disposable_pack, fault,
):
    root, pack = reviewed_disposable_pack
    assert callable(getattr(orchestrator, "seed_registered_engagements", None)), "registered seeding is absent"
    conn = db.connect(str(tmp_path / "blocked.db"))
    try:
        db.ensure_schema(conn)
        orchestrator.seed_registered_engagements(conn)
        before = {t: rows(conn, t) for t in ("engagements", "engagement_config", "engagement_assist_policy")}
        path = root / pack.families[-1].case_file
        if fault == "missing":
            path.unlink()
        elif fault == "stale_pin":
            path.write_bytes(path.read_bytes() + b" ")
        else:
            data = json.loads(path.read_bytes())
            data["review_status"] = "DRAFT"
            path.write_bytes(json.dumps(data).encode())
        with pytest.raises(registry.PackUnavailable):
            orchestrator.admit_pack(pack.slug)
        orchestrator.seed_registered_engagements(conn)
        assert {t: rows(conn, t) for t in before} == before, "missing material must never rewrite history"
        fresh = db.connect(str(tmp_path / "fresh-blocked.db"))
        try:
            db.ensure_schema(fresh)
            orchestrator.seed_registered_engagements(fresh)
            assert repo.get_engagement(fresh, pack.slug) is None, "unavailable pack was seeded"
            assert repo.get_engagement_config(fresh, pack.slug) is None
            assert repo.get_engagement_assist_policy(fresh, pack.slug) is None
            assert repo.get_engagement(fresh, "bookshop") is not None
        finally:
            fresh.close()
    finally:
        conn.close()


@pytest.mark.parametrize("kind", ("qualifying", "later"))
def test_comparison_admits_owning_pack_before_any_write(tmp_path, monkeypatch, kind):
    packs = registry.registered_packs()
    monkeypatch.setattr(registry, "_PACKS", (*packs[:2], packs[2].model_copy(update={"reviewed_pins": ()})))
    conn = db.connect(str(tmp_path / "reservation.db"))
    try:
        db.ensure_schema(conn)
        shift = Shift(id="northline-shift-01", engagement_slug="northline", seq=1,
                      state="open", opened_at=datetime.now(timezone.utc))
        monkeypatch.setattr(comparison_flow, "_require_open_shift", lambda *_: shift)
        failure = None
        try:
            if kind == "qualifying":
                comparison_flow.create_qualifying_comparison(
                    conn, shift.id, candidate_a_version_id="unused-a", candidate_b_version_id="unused-b",
                    investigation_id="unused", declared_treatment="admission control", client_request_id="unused")
            else:
                comparison_flow.create_later_condition_comparison(
                    conn, shift.id, operation_run_id="unused", declared_treatment="admission control",
                    client_request_id="unused")
        except Exception as exc:
            failure = exc
        assert isinstance(failure, registry.PackUnavailable), f"reservation did not check owning admission: {failure}"
        assert not conn.in_transaction
        for table in ("experiments", "exposure_reservations", "exposure_items", "protected_case_snapshots"):
            assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    finally:
        conn.close()


def test_registered_families_supply_serialized_scanner_needles(reviewed_disposable_pack):
    _, pack = reviewed_disposable_pack
    cases = sealed_store.load_declared_family(pack.families[-1], slug=pack.slug).cases
    needles = orchestrator._private_public_needles()
    for case in cases:
        assert case.id in needles, "registered protected identity omitted from scanner"
        serialized = json.dumps({"message": case.id})
        with pytest.raises(ValueError):
            assert_public_safe(serialized, needles)
        if isinstance(case.expected.get("aspect"), dict):
            assert case.expected["aspect"]["kind"] in needles, "typed expectation kind omitted from scanner"
            with pytest.raises(ValueError):
                assert_public_safe(json.dumps({"message": case.expected["aspect"]}), needles)
    assert_public_safe(json.dumps({"message": "ordinary public text"}), needles)


def test_family_index_resolves_owning_pack(reviewed_disposable_pack):
    _, pack = reviewed_disposable_pack
    index, failure = None, None
    try:
        index = sealed_store.case_index(slug=pack.slug)
    except Exception as exc:
        failure = exc
    assert index is not None, f"owning family lookup was refused: {failure}"
    for declaration in pack.families:
        for case in sealed_store.load_declared_family(declaration, slug=pack.slug).cases:
            assert index[case.check_id] == case
            assert "disposable-" in case.id
