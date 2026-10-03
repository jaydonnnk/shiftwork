"""Draft privacy protection must not depend on executable task vocabulary."""
import base64
import json
import shutil

from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain.errors import InvalidSealedCase
from shiftwork.packs import registry
from shiftwork.sealed import store


@pytest.fixture
def draft(tmp_path, monkeypatch):
    cases = tmp_path / "cases"
    shutil.copytree(config.SEALED_CASES_DIR, cases)
    monkeypatch.setattr(config, "SEALED_CASES_DIR", cases)
    path = cases / "northline_deployment.json"
    data = json.loads(path.read_bytes())
    data["review_status"] = "DRAFT"
    data["sealed_payload_sha256"] = None
    path.write_text(json.dumps(data), encoding="utf-8")
    packs = registry.registered_packs()
    monkeypatch.setattr(registry, "_PACKS", (*packs[:2], packs[2].model_copy(update={"reviewed_pins": ()})))
    return path, data


def test_bellwether_board_survives_unsupported_unadmitted_draft(tmp_path, draft):
    path, data = draft
    data["cases"][2]["stimulus"]["task_spec"]["tasks"][0]["kind"] = "UNIMPLEMENTED_FUTURE_TASK"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValidationError):
        store.load_family("deployment", slug="northline")
    with TestClient(create_app(str(tmp_path / "fresh.db"))) as client:
        response = client.get("/api/engagements/bookshop/board")
        assert response.status_code == 200, "draft task vocabulary blocked Bellwether board"
        assert response.json()["latest_shift"] is None
        assert client.get("/api/engagements/northline/board").status_code == 404
    assert orchestrator.workplace_boards()[2].availability == "AWAITING_OPERATOR_REVIEW"


# Each raw field is injected separately, with unique private content, so one
# identity or duplicate request/task text cannot mask another missing branch.
FIELDS = (
    ("id",), ("check_id",), ("expected", "note"),
    ("stimulus", "request", "request_id"), ("stimulus", "request", "text"),
    ("stimulus", "task_spec", "id"), ("stimulus", "task_spec", "text"),
    ("stimulus", "state_delta", "description"), ("expected", "aspect", "kind"),
)


@pytest.mark.parametrize("field", FIELDS, ids=lambda field: ".".join(field))
def test_each_draft_private_field_is_blocked_as_serialized(draft, field):
    path, data = draft
    needle = "PRIVATE_DRAFT_" + "_".join(field) + "_UNIQUE_SENTINEL"
    parent = data["cases"][0]
    for part in field[:-1]:
        parent = parent[part]
    parent[field[-1]] = needle
    path.write_text(json.dumps(data), encoding="utf-8")
    orchestrator.assert_public_projection(json.dumps({"detail": "ordinary public content"}))
    surfaces = (
        json.dumps({"detail": needle}),
        json.dumps(json.dumps({"detail": needle})),
        json.dumps({"log_base64": base64.b64encode(needle.encode()).decode()}),
    )
    for surface in surfaces:
        with pytest.raises(orchestrator.LifecycleError, match="private material"):
            orchestrator.assert_public_projection(surface)
    assert orchestrator.workplace_boards()[2].availability == "AWAITING_OPERATOR_REVIEW"


@pytest.mark.parametrize("damage", ("root", "cases", "identity", "stimulus", "request", "schema", "aspect"))
def test_malformed_privacy_inventory_fails_closed(draft, damage):
    path, data = draft
    if damage == "root":
        data = []
    elif damage == "cases":
        data["cases"] = {}
    elif damage == "identity":
        data["cases"][0]["id"] = 42
    elif damage == "stimulus":
        data["cases"][0]["stimulus"] = []
    elif damage == "request":
        del data["cases"][0]["stimulus"]["request"]["text"]
    elif damage == "schema":
        data["cases"][0]["schema_version"] = 999
    else:
        data["cases"][0]["expected"]["aspect"] = []
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises((InvalidSealedCase, store.UnsupportedSealedSchema)):
        orchestrator.assert_public_projection({"detail": "ordinary public content"})


def test_existing_bellwether_and_draft_needles_are_all_retained():
    needles = set(orchestrator._private_public_needles())
    for pack in registry.registered_packs():
        for family in pack.families:
            path = config.SEALED_CASES_DIR / family.case_file.rsplit("/", 1)[-1]
            if not path.exists():
                continue
            for case in json.loads(path.read_bytes())["cases"]:
                values = [case["id"], case["check_id"]]
                note = case["expected"].get("note")
                if isinstance(note, str) and len(note) >= 25:
                    values.append(note)
                stimulus = case.get("stimulus")
                if stimulus:
                    values.extend([stimulus["request"]["request_id"], stimulus["request"]["text"],
                                   stimulus["task_spec"]["id"], stimulus["task_spec"]["text"],
                                   stimulus["state_delta"]["description"]])
                    aspect = case["expected"].get("aspect")
                    values.append(aspect["kind"] if isinstance(aspect, dict) else aspect)
                for value in values:
                    if isinstance(value, str) and len(value) >= 8:
                        assert value in needles, "existing private field lost from inventory"
                        with pytest.raises(orchestrator.LifecycleError, match="private material"):
                            orchestrator.assert_public_projection(json.dumps({"probe": value}))
