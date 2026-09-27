"""S13 source projection and serialized private-needle controls."""

import base64
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.gateway.redaction import serialized_contains
from shiftwork.orchestrator import LifecycleError
from shiftwork.store import db, repo


def test_source_route_exposes_owned_files_without_storage_locator(tmp_path):
    with TestClient(create_app(str(tmp_path / "source.db"))) as client:
        shift = client.post("/api/engagements/bookshop/shifts").json()
        frozen = client.post(f"/api/shifts/{shift['id']}/artifact/versions",
            json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
        assert frozen.status_code == 201, frozen.text
        source = client.get(f"/api/artifact-versions/{frozen.json()['id']}")
        assert source.status_code == 200, source.text
        payload = source.json()
        assert set(payload) == {"id", "parent_id", "content_hash", "files", "contract", "authorship"}
        assert payload["authorship"] == "learner"
        assert "service.py" in payload["files"]
        assert "storage_ref" not in json.dumps(payload)
        assert str(Path.cwd()) not in json.dumps(payload)


def test_serialized_scanner_fires_for_raw_escaped_slash_and_embedded_base64(monkeypatch):
    needle = r"C:\controller\private\token.txt"
    surfaces = [
        {"error": "prefix " + needle + " suffix"},
        {"error": "prefix " + needle.replace("\\", "/") + " suffix"},
        {"event": json.dumps({"path": needle})},
        {"body_base64": base64.b64encode(("prefix " + needle + " suffix").encode()).decode()},
    ]
    assert all(serialized_contains(surface, needle) for surface in surfaces)
    assert not serialized_contains({"result": "public record only"}, needle)
    monkeypatch.setenv("NEBIUS_API_KEY", "S13_TEST_PROVIDER_SECRET")
    with pytest.raises(LifecycleError, match="private material"):
        orchestrator.assert_public_projection({"body_base64": base64.b64encode(
            b"before S13_TEST_PROVIDER_SECRET after").decode()})


def test_injected_experiment_request_field_returns_422_without_a_run(tmp_path):
    """Gate 3 test 36: a learner-frozen field cannot widen the controller policy."""
    database = tmp_path / "injected-field.db"
    with TestClient(create_app(str(database))) as client:
        shift = client.post("/api/engagements/bookshop/shifts").json()
        frozen = client.post(f"/api/shifts/{shift['id']}/artifact/versions",
            json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
        assert frozen.status_code == 201, frozen.text
        injected = client.post(f"/api/shifts/{shift['id']}/experiments", json={
            "kind": "DIAGNOSTIC", "investigation_id": None,
            "candidate_a_version_id": frozen.json()["id"],
            "client_request_id": "injected-field",
            "allowed_tool_names": ["public_record_lookup"],
        })
        assert injected.status_code == 422, injected.text
        conn = db.connect(str(database))
        try:
            assert repo.list_experiments_for_shift(conn, shift["id"]) == []
            assert repo.list_runs_for_shift(conn, shift["id"]) == []
        finally:
            conn.close()
