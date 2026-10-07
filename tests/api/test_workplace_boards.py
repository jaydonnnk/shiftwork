"""S22b workplace projection over real registration and serialized HTTP data."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from shiftwork import orchestrator
from shiftwork.app import create_app
from shiftwork.packs import registry
from shiftwork.sealed import store


def test_workplace_projects_only_approved_fields_in_declaration_order(tmp_path):
    with TestClient(create_app(str(tmp_path / "boards.db"))) as client:
        response = client.get("/api/boards")
        assert response.status_code == 200, "workplace route is missing"
        boards = response.json()
        packs = registry.registered_packs()
        assert [board["engagement_slug"] for board in boards] == [pack.slug for pack in packs]
        for board, pack in zip(boards, packs, strict=True):
            assert set(board) == {"engagement_slug", "role_name", "employer", "client",
                                  "room_id", "station_labels", "availability"}
            assert {key: board[key] for key in registry.BoardDisplay.model_fields} == pack.display.model_dump(mode="json")
        assert [board["availability"] for board in boards] == [
            "AVAILABLE", "AVAILABLE", "AVAILABLE"]
        assert len(boards[2]["station_labels"]) == 6
        orchestrator.assert_public_projection(response.json())


def test_workplace_availability_does_not_advance_with_learner_progress(tmp_path):
    with TestClient(create_app(str(tmp_path / "progress.db"))) as client:
        before = client.get("/api/boards")
        assert before.status_code == 200
        opened = client.post("/api/engagements/bookshop/shifts")
        assert opened.status_code == 201, opened.text
        assert client.get("/api/boards").json() == before.json()


@pytest.mark.parametrize("path", (
    "fixtures/mission/northline_deployment_v1.json",
    "fixtures/state/northline_start.json",
    "fixtures/catalogs/northline_v1.json",
    registry.resolve_pack("northline").families[0].case_file,
))
def test_workplace_never_partially_offers_a_pack_with_missing_review(tmp_path, monkeypatch, path):
    with TestClient(create_app(str(tmp_path / "unavailable.db"))) as client:
        packs = registry.registered_packs()
        northline = packs[2]
        damaged = northline.model_copy(update={
            "reviewed_pins": tuple(pin for pin in northline.reviewed_pins if pin.path != path)})
        monkeypatch.setattr(registry, "_PACKS", (*packs[:2], damaged))
        response = client.get("/api/boards")
        assert response.status_code == 200, response.text
        assert response.json()[0]["availability"] == "AVAILABLE"
        assert response.json()[2]["availability"] == "AWAITING_OPERATOR_REVIEW"


def test_workplace_omits_unregistered_engagement_even_when_already_seeded(tmp_path, monkeypatch):
    with TestClient(create_app(str(tmp_path / "removed.db"))) as client:
        monkeypatch.setattr(registry, "_PACKS", registry.registered_packs()[:2])
        response = client.get("/api/boards")
        assert response.status_code == 200, response.text
        assert [board["engagement_slug"] for board in response.json()] == ["bookshop", "gtm"]


@pytest.mark.parametrize("needle_kind", ("bookshop", "northline", "host_path", "slash_path", "secret"))
def test_workplace_scanner_detects_private_values_in_the_serialized_payload(
    tmp_path, monkeypatch, needle_kind,
):
    with TestClient(create_app(str(tmp_path / "scanner.db"))) as client:
        assert client.get("/api/boards").status_code == 200
        if needle_kind in {"bookshop", "northline"}:
            pack = registry.resolve_pack(needle_kind)
            family = pack.families[0].family
            needle = next(value for value in store.load_privacy_needles(family, slug=pack.slug)
                          if len(value) >= 8 and "\\" not in value)
        elif needle_kind == "secret":
            needle = "workplace-scanner-test-secret"
            monkeypatch.setenv("NEBIUS_API_KEY", needle)
        else:
            needle = str(Path.cwd())
            if needle_kind == "slash_path":
                needle = needle.replace("\\", "/")
        boards = orchestrator.workplace_boards()
        injected = boards[0].model_copy(update={
            "display": boards[0].display.model_copy(update={"role_name": needle})})
        monkeypatch.setattr(orchestrator, "workplace_boards", lambda: (injected, *boards[1:]))
        response = client.get("/api/boards")
        assert response.status_code == 409, "serialized workplace leaked injected private material"
        assert response.json()["detail"] == "public evidence contains private material"
        assert needle not in response.text
