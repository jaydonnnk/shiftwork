"""Northline material integrity and real refusal of disposable unreviewed drafts.

The approved production seals are checked without deployment success assessment.
Draft refusal remains a separate disposable stimulus, never an admission bypass.
"""
import ast
import hashlib
import json
from pathlib import Path
import shutil

import pytest
from pydantic import ValidationError

from shiftwork import config, orchestrator
from shiftwork.domain import contract_catalog, task_contract
from shiftwork.domain.comparison import AcceptanceAspect, validate_acceptance_aspect
from shiftwork.domain.errors import InvalidSealedCase, MissionSpecInvalid
from shiftwork.evaluator import evaluator
from shiftwork.evaluator.evaluator import SealedCase
from shiftwork.packs import registry
from shiftwork.sealed import store as sealed_store
from shiftwork.store import db


def read(relative):
    return json.loads((config.PACKAGE_DIR / relative).read_bytes())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def test_northline_draft_mission_catalog_and_state_have_owning_bindings():
    pack = registry.resolve_pack("northline")
    mission = task_contract.load_mission(config.PACKAGE_DIR / pack.mission_path)
    catalog = contract_catalog.load_catalog("northline", mission.contract_catalog_version)
    assert mission.engagement_slug == catalog.engagement_slug == "northline"
    assert mission.contract_catalog_hash == catalog.content_hash
    for path in (pack.public_state_path, pack.comparison_state_path):
        state = task_contract.load_public_state(config.PACKAGE_DIR / path)
        assert state.engagement_slug == "northline"
        assert state.review_status == "DRAFT"
        assert not any(entity.startswith("book:") for entity in state.entities)
    assert mission.review_status == "DRAFT"
    assert "deployment.no_double_booking" in mission.public_rules
    assert "deployment.safety_escalation" in mission.public_rules
    assert "deployment.commitments_honored" in mission.public_rules
    assert "deployment.access_boundaries" in mission.public_rules


def test_northline_draft_manifest_pins_exact_public_bytes_and_specs():
    pack = registry.resolve_pack("northline")
    manifest = read(pack.manifest_path)
    assert manifest["engagement_slug"] == "northline"
    assert manifest["review_status"] == "OPERATOR_SEALED"
    assert manifest["sealed_payload_sha256"] == digest(json.dumps(manifest["workloads"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
    assert manifest["comparison_state_sha256"] == digest((config.PACKAGE_DIR / pack.comparison_state_path).read_bytes())
    assert [w["ordinal"] for w in manifest["workloads"]] == [1, 2, 3]
    for workload in manifest["workloads"]:
        base = config.PACKAGE_DIR / Path(pack.manifest_path).parent
        raw = (base / workload["request_file"]).read_bytes()
        rows = [json.loads(line) for line in raw.splitlines() if line]
        specs = json.loads((base / workload["task_spec_file"]).read_bytes())
        assert workload["request_bytes_sha256"] == digest(raw)
        assert workload["request_bytes_length"] == len(raw)
        assert workload["request_count"] == len(rows) == len(specs) == 2
        assert [r["ordinal"] for r in rows] == [1, 2]
        assert [r["request_id"] for r in rows] == [s["id"] for s in specs]
        assert [r["text"] for r in rows] == [s["text"] for s in specs]
        parsed = [task_contract.CustomerRequestSpec.model_validate(s).model_dump(mode="json") for s in specs]
        assert parsed == specs
        canonical = json.dumps(specs, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        assert workload["task_specs_sha256"] == digest(canonical)
    first = read("fixtures/requests/northline_compare_pair_01_specs.json")
    assert first[0]["id"] != first[1]["id"]
    assert first[0]["tasks"][0]["condition_json"]["idempotency_key"] == first[1]["tasks"][0]["condition_json"]["idempotency_key"]


def test_northline_draft_safety_vocabulary_parses():
    specs = read("fixtures/requests/northline_compare_pair_02_specs.json")
    assert specs[0]["tasks"][0]["kind"] == "ROUTE_SAFETY_QUESTION"
    parsed = task_contract.CustomerRequestSpec.model_validate(specs[0])
    assert parsed.model_dump(mode="json") == specs[0]
    assert parsed.tasks[0].kind is task_contract.TaskKind.ROUTE_SAFETY_QUESTION
    # Schema recognition never accepts an arbitrary future kind.
    specs[0]["tasks"][0]["kind"] = "UNIMPLEMENTED_FUTURE_TASK"
    with pytest.raises(ValidationError) as failure:
        task_contract.CustomerRequestSpec.model_validate(specs[0])
    assert any(error["loc"] == ("tasks", 0, "kind") and error["type"] == "enum" for error in failure.value.errors())


@pytest.mark.parametrize("status", ["no_response", "missing_task", *task_contract.TaskStatus])
def test_northline_safety_assessment_refuses_until_s22b(status):
    spec = task_contract.CustomerRequestSpec.model_validate(
        read("fixtures/requests/northline_compare_pair_02_specs.json")[0])
    mission = task_contract.load_mission(config.PACKAGE_DIR / registry.resolve_pack("northline").mission_path)
    snapshot = task_contract.load_public_state(config.PACKAGE_DIR / registry.resolve_pack("northline").comparison_state_path)
    response = None
    if status != "no_response":
        results = () if status == "missing_task" else (task_contract.TaskResult(
            task_id=spec.tasks[0].id, status=status,
            entity_ref=spec.tasks[0].requested_entity_ref, claims=(),
        ),)
        response = task_contract.ServiceResponse(request_id=spec.id, task_results=results,
                                                evidence_refs=(), uncertainty_codes=())
    # Recognition is material validation only. The old generic completed-task
    # branch must never turn a claimed safety route into deployment acceptance.
    with pytest.raises(MissionSpecInvalid, match="safety task assessment awaits S22b"):
        evaluator.assess_request(spec=spec, request_ordinal=1, mission=mission,
                                 snapshot=snapshot, response=response)


def test_northline_draft_six_typed_aspects_and_additive_state_are_well_formed():
    family = read("sealed/cases/northline_deployment.json")
    assert family["family"] == "deployment"
    assert family["review_status"] == "OPERATOR_SEALED"
    assert family["sealed_payload_sha256"] == digest(json.dumps(family["cases"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
    assert len(family["cases"]) == 6
    assert len({case["id"] for case in family["cases"]}) == 6
    assert len({case["stimulus"]["request"]["text"] for case in family["cases"]}) == 6
    state = (config.PACKAGE_DIR / "fixtures/state/northline_compare_state_v1.json").read_bytes()
    for case in family["cases"]:
        aspect = AcceptanceAspect.model_validate(case["expected"]["aspect"])
        spec = case["stimulus"]["task_spec"]
        if aspect.task_id:
            assert aspect.task_id in {task["id"] for task in spec["tasks"]}
        assert case["request_ordinals"] == [3]
        assert case["stimulus"]["request"]["ordinal"] == 3
        assert case["stimulus"]["request"]["request_id"] == spec["id"]
        assert case["stimulus"]["request"]["text"] == spec["text"]
        delta = task_contract.ProtectedStateDelta.model_validate(case["stimulus"]["state_delta"])
        task_contract.resolve_protected_state(state, delta)
        parsed_case = SealedCase.model_validate(case)
        assert validate_acceptance_aspect(parsed_case, engagement_slug="northline") == aspect


def test_northline_draft_blank_scaffold_contains_no_solution():
    source = (config.PACKAGE_DIR / "templates/artifact/northline_blank_service.py").read_bytes()
    module = ast.parse(source)
    answer = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "answer")
    assert len(answer.body) == 1 and isinstance(answer.body[0], ast.Return)
    result = answer.body[0].value
    assert isinstance(result, ast.Dict)
    assert [ast.literal_eval(key) for key in result.keys] == ["request_id", "task_results", "evidence_refs", "uncertainty_codes"]
    assert ast.dump(result.values[0]) == ast.dump(ast.parse('request["request_id"]', mode="eval").body)
    assert all(isinstance(value, ast.List) and value.elts == [] for value in result.values[1:])
    compile(source, "northline_blank_service.py", "exec")
    template_root = config.PACKAGE_DIR / "templates/artifact/northline"
    assert json.loads((template_root / "permissions.json").read_bytes()) == {"reads": [], "writes": []}
    for name in ("discovery.md", "acceptance_tests.py", "runbook.md"):
        assert (template_root / name).read_text(encoding="utf-8").strip()


@pytest.fixture
def unreviewed_northline(tmp_path, monkeypatch):
    root = tmp_path / "draft-package"
    assert not root.resolve().is_relative_to(config.PACKAGE_DIR.resolve())
    for directory in ("fixtures", "sealed/cases", "templates"):
        shutil.copytree(config.PACKAGE_DIR / directory, root / directory)
    path = root / "sealed/cases/northline_deployment.json"
    data = json.loads(path.read_bytes())
    data["review_status"] = "DRAFT"
    data["sealed_payload_sha256"] = None
    path.write_bytes(json.dumps(data).encode())
    packs = registry.registered_packs()
    monkeypatch.setattr(registry, "_PACKS", (*packs[:2], packs[2].model_copy(update={"reviewed_pins": ()})))
    monkeypatch.setattr(config, "PACKAGE_DIR", root)
    monkeypatch.setattr(config, "CATALOG_DIR", root / "fixtures/catalogs")
    monkeypatch.setattr(config, "SEALED_CASES_DIR", root / "sealed/cases")


def test_northline_draft_real_admission_and_family_seal_refuse(unreviewed_northline):
    assert registry.resolve_pack("northline").reviewed_pins == ()
    with pytest.raises(registry.PackUnavailable):
        orchestrator.admit_pack("northline")
    pack = registry.resolve_pack("northline")
    with pytest.raises(InvalidSealedCase, match="awaits operator review and sealing"):
        sealed_store.load_declared_family(pack.families[0], slug="northline")
    assert [board.availability for board in orchestrator.workplace_boards()] == ["AVAILABLE", "AWAITING_OPERATOR_REVIEW", "AWAITING_OPERATOR_REVIEW"]


def test_northline_draft_startup_still_seeds_only_bellwether(tmp_path, unreviewed_northline):
    conn = db.connect(tmp_path / "draft-refusal.db")
    try:
        db.ensure_schema(conn)
        orchestrator.seed_registered_engagements(conn)
        assert [row[0] for row in conn.execute("SELECT slug FROM engagements ORDER BY slug")] == ["bookshop"]
        assert conn.execute("SELECT COUNT(*) FROM shifts").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM exposure_items").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM operating_selections").fetchone()[0] == 0
    finally:
        conn.close()


@pytest.mark.parametrize("fault", ["request_bytes", "retry_intent", "aspect_task", "solution"])
def test_northline_draft_guards_catch_each_disposable_fault(tmp_path, monkeypatch, fault):
    original = config.PACKAGE_DIR
    root = tmp_path / "draft-package"
    assert not root.resolve().is_relative_to(original.resolve())
    for directory in ("fixtures", "sealed/cases", "templates"):
        for path in (original / directory).rglob("northline*"):
            if path.is_file():
                target = root / path.relative_to(original)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
    # Worksheet files have no northline prefix and need explicit copying.
    shutil.copytree(original / "templates/artifact/northline", root / "templates/artifact/northline")
    monkeypatch.setattr(config, "PACKAGE_DIR", root)
    monkeypatch.setattr(config, "CATALOG_DIR", root / "fixtures/catalogs")

    if fault == "request_bytes":
        path = root / "fixtures/requests/northline_compare_pair_01.jsonl"
        path.write_bytes(path.read_bytes().replace(b"counter visit V-11", b"counter visit V-99"))
        guard = test_northline_draft_manifest_pins_exact_public_bytes_and_specs
    elif fault == "retry_intent":
        path = root / "fixtures/requests/northline_compare_pair_01_specs.json"
        specs = json.loads(path.read_bytes())
        specs[1]["tasks"][0]["condition_json"]["idempotency_key"] = "wrong-new-intent"
        path.write_bytes(json.dumps(specs).encode())
        manifest_path = root / "fixtures/requests/northline_compare_manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["workloads"][0]["task_specs_sha256"] = digest(json.dumps(specs, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
        manifest["sealed_payload_sha256"] = digest(json.dumps(manifest["workloads"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
        manifest_path.write_bytes(json.dumps(manifest).encode())
        guard = test_northline_draft_manifest_pins_exact_public_bytes_and_specs
    elif fault == "aspect_task":
        path = root / "sealed/cases/northline_deployment.json"
        family = json.loads(path.read_bytes())
        family["cases"][3]["expected"]["aspect"]["task_id"] = "missing-task"
        family["sealed_payload_sha256"] = digest(json.dumps(family["cases"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode())
        path.write_bytes(json.dumps(family).encode())
        guard = test_northline_draft_six_typed_aspects_and_additive_state_are_well_formed
    else:
        path = root / "templates/artifact/northline_blank_service.py"
        raw = path.read_bytes()
        assert raw.count(b'    return {"request_id":') == 1
        path.write_bytes(raw.replace(b'    return {"request_id":', b'    booking = "authored-solution"\n    return {"request_id":'))
        guard = test_northline_draft_blank_scaffold_contains_no_solution
    with pytest.raises(AssertionError):
        guard()
