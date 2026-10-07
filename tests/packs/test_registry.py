"""S22a pack declarations and admission, using disposable content for faults."""

import ast
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from shiftwork import config, orchestrator
from shiftwork.packs import registry
from shiftwork.sealed import rotation
from shiftwork.sealed import store as sealed_store


def test_declaration_order_and_unregistered_slug():
    assert tuple(pack.slug for pack in registry.registered_packs()) == (
        "bookshop", "gtm", "northline",
    )
    assert registry.resolve_pack("gtm").display.employer == "Stonebridge Software"
    assert registry.resolve_pack("gtm").display.client == "Revenue team"
    with pytest.raises(registry.PackNotFound):
        registry.resolve_pack("not-registered")


def test_workplace_refuses_unreviewed_packs(monkeypatch):
    packs = registry.registered_packs()
    monkeypatch.setattr(registry, "_PACKS", (packs[0], *(pack.model_copy(update={"reviewed_pins": ()}) for pack in packs[1:])))
    boards = orchestrator.workplace_boards()
    assert tuple(board.availability for board in boards) == (
        "AVAILABLE", "AWAITING_OPERATOR_REVIEW", "AWAITING_OPERATOR_REVIEW",
    )
    assert set(boards[0].model_dump()) == {"engagement_slug", "display", "availability"}


@pytest.fixture
def material(tmp_path, monkeypatch):
    original = config.PACKAGE_DIR
    root = tmp_path / "package"
    for pin in registry.resolve_pack("bookshop").reviewed_pins:
        path = root / pin.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((original / pin.path).read_bytes())
    monkeypatch.setattr(config, "PACKAGE_DIR", root)
    monkeypatch.setattr(config, "CATALOG_DIR", root / "fixtures/catalogs")
    monkeypatch.setattr(config, "SEALED_CASES_DIR", root / "sealed/cases")
    return root


def repin(monkeypatch, root, path):
    pack = registry.resolve_pack("bookshop")
    pins = tuple(pin.model_copy(update={"sha256": hashlib.sha256((root/path).read_bytes()).hexdigest()})
                 if pin.path == path else pin for pin in pack.reviewed_pins)
    monkeypatch.setattr(registry, "_PACKS", (pack.model_copy(update={"reviewed_pins": pins}),
                                           *registry.registered_packs()[1:]))


def write_family(root, data):
    name = "sealed/cases/bookshop_task_completion.json"
    data["sealed_payload_sha256"] = hashlib.sha256(json.dumps(
        data["cases"], sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()
    (root/name).write_text(json.dumps(data), encoding="utf-8")
    return name


@pytest.mark.parametrize("field", ("mission_path", "assist", "display", "families", "manifest_path"))
def test_incomplete_declaration_is_refused(field, monkeypatch):
    data = registry.resolve_pack("bookshop").model_dump(mode="json")
    del data[field]
    with pytest.raises(ValidationError):
        registry.EngagementPack.model_validate(data)


def test_duplicate_family_name_is_refused():
    data = registry.resolve_pack("bookshop").model_dump(mode="json")
    data["families"].append(data["families"][0])
    with pytest.raises(ValidationError, match="duplicate family name"):
        registry.EngagementPack.model_validate(data)


def test_comparison_minimum_below_six_is_refused():
    data = registry.resolve_pack("northline").families[0].model_dump(mode="json")
    data["min_variants"] = 5
    with pytest.raises(ValidationError, match="at least six"):
        registry.FamilyDeclaration.model_validate(data)


@pytest.mark.parametrize("fault,needle", (
    ("missing", "No such file"),
    ("unsealed", "awaits operator review"),
    ("short", "insufficient distinct variants"),
    ("duplicate", "duplicate or insufficient"),
    ("cycle", "cycle mismatch"),
    ("family", "family name"),
    ("case_family", "case belongs to another declared family"),
))
def test_declared_family_fault_refuses_whole_pack(material, monkeypatch, fault, needle):
    name = "sealed/cases/bookshop_task_completion.json"
    path = material/name
    if fault == "missing":
        path.unlink()
    else:
        data = json.loads(path.read_bytes())
        if fault == "unsealed":
            data["review_status"] = "DRAFT"
        elif fault == "short":
            data["cases"] = data["cases"][:5]
        elif fault == "duplicate":
            data["cases"][-1] = data["cases"][0]
        elif fault == "cycle":
            data["cycle"] = 2
        elif fault == "family":
            data["family"] = "another_family"
        elif fault == "case_family":
            data["cases"][0]["family"] = "another_family"
        write_family(material, data)
        repin(monkeypatch, material, name)
    with pytest.raises(registry.PackUnavailable) as error:
        orchestrator.admit_pack("bookshop")
    assert needle in str(error.value.__cause__), f"wrong admission guard for {fault}"
    assert orchestrator.workplace_boards()[0].availability == "AWAITING_OPERATOR_REVIEW"


@pytest.mark.parametrize("name", tuple(pin.path for pin in registry.resolve_pack("bookshop").reviewed_pins))
def test_each_reviewed_pin_is_verified(material, name):
    assert orchestrator.admit_pack("bookshop").slug == "bookshop"
    with (material/name).open("ab") as file:
        file.write(b" ")
    with pytest.raises(registry.PackUnavailable) as error:
        orchestrator.admit_pack("bookshop")
    assert "reviewed content pin mismatch" in str(error.value.__cause__)


def test_missing_required_pin_is_refused(material, monkeypatch):
    pack = registry.resolve_pack("bookshop")
    monkeypatch.setattr(registry, "_PACKS", (pack.model_copy(update={"reviewed_pins": pack.reviewed_pins[1:]}),))
    with pytest.raises(registry.PackUnavailable) as error:
        orchestrator.admit_pack("bookshop")
    assert "awaits operator review" in str(error.value.__cause__)


def test_unsealed_manifest_is_refused(material, monkeypatch):
    name = "fixtures/requests/bookshop_compare_manifest.json"
    data = json.loads((material/name).read_bytes())
    data["review_status"] = "DRAFT"
    (material/name).write_text(json.dumps(data), encoding="utf-8")
    repin(monkeypatch, material, name)
    with pytest.raises(registry.PackUnavailable) as error:
        orchestrator.admit_pack("bookshop")
    assert "manifest awaits operator review" in str(error.value.__cause__)


def test_mission_from_another_engagement_is_refused(material, monkeypatch):
    name = "fixtures/mission/bookshop_pivot_v1.json"
    data = json.loads((material/name).read_bytes())
    data["engagement_slug"] = "northline"
    (material/name).write_text(json.dumps(data), encoding="utf-8")
    repin(monkeypatch, material, name)
    with pytest.raises(registry.PackUnavailable) as error:
        orchestrator.admit_pack("bookshop")
    assert "mission belongs to another engagement" in str(error.value.__cause__)


def test_two_packs_cannot_claim_same_variant_refs(material, monkeypatch):
    from shiftwork.domain.comparison import acceptance_aspect
    from shiftwork.evaluator.evaluator import SealedCase
    name = "sealed/cases/bookshop_task_completion.json"
    data = json.loads((material / name).read_bytes())
    for case in data["cases"]:
        case["expected"]["aspect"] = acceptance_aspect(SealedCase.model_validate(case)).model_dump(mode="json")
    write_family(material, data)
    repin(monkeypatch, material, name)
    bellwether = registry.resolve_pack("bookshop")
    other = registry.resolve_pack("northline").model_copy(update={"families": (bellwether.families[-1],)})
    monkeypatch.setattr(registry, "_PACKS", (bellwether, other))
    with pytest.raises(registry.PackUnavailable, match="packs share variant refs"):
        orchestrator.admit_pack("bookshop")
    assert orchestrator.workplace_boards()[0].availability == "AWAITING_OPERATOR_REVIEW"


def test_comparison_identity_binds_content_without_renaming_legacy_cases():
    cases = sealed_store.load_family("task_completion").cases
    # Verified preflight identities are a test invariant; a fresh checkout must
    # not depend on the operator's ignored raw evidence folder.
    assert [rotation.variant_ref(case) for case in cases] == [
        "var-1e0ab09a26ce1433", "var-81ddbb45a81a2a26", "var-67cd7c292ed6cdc6",
        "var-5abf392cba5975d8", "var-3faca6a51ddd1445", "var-ffa478cf74a4ceea",
    ]
    case = cases[0].model_copy(update={"family": "deployment"})
    changed = case.model_copy(update={"expected": {**case.expected, "note": "changed"}})
    assert rotation.variant_ref(case) != rotation.variant_ref(changed)


def test_registry_imports_no_loader_store_evaluator_or_network():
    source = Path(registry.__file__).read_text(encoding="utf-8")
    imports = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert set(imports) == {"enum", "typing", "pydantic", "shiftwork.domain.errors", "shiftwork.domain.models"}


@pytest.mark.parametrize("path", ("sealed/cases/nested/file.json", "sealed/cases/../file.json",
                                  "/sealed/cases/file.json", "fixtures/file.json"))
def test_declared_family_cannot_select_another_storage_location(path):
    data = registry.resolve_pack("northline").families[0].model_dump(mode="json")
    data["case_file"] = path
    with pytest.raises(ValidationError, match="controller sealed storage"):
        registry.FamilyDeclaration.model_validate(data)


def test_assist_policies_cover_all_three_declared_levels():
    assert [(tuple(role.value for role in pack.assist.allowed_roles),
             pack.assist.total_calls_per_shift, pack.assist.max_patch_proposals)
            for pack in registry.registered_packs()] == [
        (("HINT", "DIAGNOSIS", "PATCH_PROPOSAL"), 3, 1),
        (("HINT", "DIAGNOSIS"), 2, 0), (("HINT",), 1, 0),
    ]
