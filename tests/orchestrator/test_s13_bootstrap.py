"""A copied no-run v5 shift gets one public source, never an implicit choice."""

import base64
import json

from fastapi.testclient import TestClient

from demos.final_pivot import create_v5_sample
from shiftwork import config
from shiftwork.app import create_app
from shiftwork.domain import task_contract
from shiftwork.executor.base import RawCapture, RunResult
from shiftwork.executor.tokenfactory import TokenFactoryAdapter
from shiftwork.gateway.protocol import InferencePolicy
from shiftwork.store import db, repo


RESPONSE = {
    "request_id": "bellwether-collection-001",
    "task_results": [{"task_id": "price", "status": "COMPLETED",
        "entity_ref": "book:salt-roads:paperback", "claims": [{
            "kind": "price", "entity_ref": "book:salt-roads:paperback", "value": 1800,
            "evidence_refs": ["public:salt-roads:paperback:price"]}],
        "commitment_ref": None, "explanation_code": None}],
    "evidence_refs": ["public:salt-roads:paperback:price"], "uncertainty_codes": [],
}


def _open_and_freeze(client):
    opened = client.post("/api/engagements/bookshop/shifts")
    assert opened.status_code == 201, opened.text
    shift_id = opened.json()["id"]
    frozen = client.post(f"/api/shifts/{shift_id}/artifact/versions",
        json={"contract": config.REPAIR_ARC_CONTRACT_JSON})
    assert frozen.status_code == 201, frozen.text
    return shift_id, frozen.json()["id"]


def _bootstrap(client, shift_id, version_id, key="first-public-source"):
    return client.post(f"/api/shifts/{shift_id}/experiments", json={
        "kind": "DIAGNOSTIC", "investigation_id": None,
        "candidate_a_version_id": version_id, "client_request_id": key,
    })


def test_no_run_legacy_bootstrap_creates_owned_source_without_business_writes(tmp_path, monkeypatch):
    copied = tmp_path / "copied-v5.db"
    create_v5_sample(copied, with_run=False)
    monkeypatch.setenv("NEBIUS_API_KEY", "TEST_PROVIDER_TOKEN")
    monkeypatch.setenv("NEBIUS_PROJECT_ID", "aiproject-test")

    async def fake_execute(self, _request):
        return RunResult(captures=(RawCapture(request_ordinal=1, http_status=200,
            body=json.dumps(RESPONSE).encode(), elapsed_ms=21, transport_error=None,
            log_ref=None),), executor_ref="fake-operation", failure=None, wall_ms=25)

    monkeypatch.setattr(TokenFactoryAdapter, "execute", fake_execute)
    with TestClient(create_app(str(copied), executor="tokenfactory")) as client:
        shift_id, version_id = _open_and_freeze(client)
        station = client.get(f"/api/shifts/{shift_id}/investigations").json()
        assert station["bootstrap_available"] is True
        created = _bootstrap(client, shift_id, version_id)
        assert created.status_code == 202, created.text
        view = client.get(f"/api/experiments/{created.json()['id']}").json()
        assert view["investigation_id"] is None
        assert view["context_evidence_class"] == "ISOLATED_LIVE"
        assert view["trials"][0]["evidence_mode"] == "ISOLATED_LIVE"
        assert view["trials"][0]["state"] == "COMPLETE"
        assert view["trials"][0]["outputs"][0]["request_text"].startswith("Can I collect")
        assert view["eligible"] is False
        run_id = view["trials"][0]["run_id"]
        investigation = client.post(f"/api/shifts/{shift_id}/investigations", json={
            "source_run_id": run_id, "source_request_ordinal": 1,
            "cause": "the old router misses collection", "falsifier": "a collection answer appears",
            "public_test": "check required tasks", "revision_of_id": None,
            "client_request_id": "investigate-source"})
        assert investigation.status_code == 201, investigation.text
        assert investigation.json()["source_run_id"] == run_id
        repeated = _bootstrap(client, shift_id, version_id, key="another-source")
        assert repeated.status_code == 409
        conn = db.connect(copied)
        try:
            assert repo.count_operation_runs(conn, shift_id) == 0
            assert repo.count_operating_selections(conn) == 0
            assert repo.list_ledger_events(conn, config.BOOKSHOP_SLUG) == []
            assert repo.list_incidents(conn, config.BOOKSHOP_SLUG) == []
            assert repo.get_execution_context(conn, repo.get_experiment(conn, view["id"]).context_id).protected_reservation_id is None
        finally:
            conn.close()
        assert client.post(f"/api/shifts/{shift_id}/runs").status_code == 409
        assert client.post(f"/api/shifts/{shift_id}/close", json={}).status_code == 409


def test_bootstrap_blocks_history_with_an_owned_source_and_missing_executor(tmp_path, monkeypatch):
    copied = tmp_path / "copied-v5-with-run.db"
    create_v5_sample(copied, with_run=True)
    monkeypatch.setenv("NEBIUS_API_KEY", "TEST_PROVIDER_TOKEN")
    monkeypatch.setenv("NEBIUS_PROJECT_ID", "aiproject-test")
    with TestClient(create_app(str(copied), executor="tokenfactory")) as client:
        shift_id, version_id = _open_and_freeze(client)
        refused = _bootstrap(client, shift_id, version_id)
        assert refused.status_code == 409
        assert "owned source request already exists" in refused.json()["detail"]
        conn = db.connect(copied)
        try:
            assert repo.list_experiments_for_shift(conn, shift_id) == []
        finally:
            conn.close()
    no_credential = tmp_path / "copied-v5-no-credential.db"
    create_v5_sample(no_credential, with_run=False)
    monkeypatch.delenv("NEBIUS_API_KEY")
    with TestClient(create_app(str(no_credential), executor="tokenfactory")) as client:
        shift_id, version_id = _open_and_freeze(client)
        refused = _bootstrap(client, shift_id, version_id)
        assert refused.status_code == 409
        assert "unavailable" in refused.json()["detail"]


def _fake_capture_result():
    return RunResult(captures=(RawCapture(request_ordinal=1, http_status=200,
        body=json.dumps(RESPONSE).encode(), elapsed_ms=21, transport_error=None,
        log_ref=None),), executor_ref="fake-operation", failure=None, wall_ms=25)


def _reserve_bootstrap_and_read_context(tmp_path, monkeypatch, database_name: str,
                                        capture: dict | None = None):
    copied = tmp_path / database_name
    create_v5_sample(copied, with_run=False)
    monkeypatch.setenv("NEBIUS_API_KEY", "TEST_PROVIDER_TOKEN")
    monkeypatch.setenv("NEBIUS_PROJECT_ID", "aiproject-test")

    async def fake_execute(self, _request):
        if capture is not None:
            capture["allowed_tool_names"] = tuple(self.allowed_tool_names)
        return _fake_capture_result()

    monkeypatch.setattr(TokenFactoryAdapter, "execute", fake_execute)
    with TestClient(create_app(str(copied), executor="tokenfactory")) as client:
        shift_id, version_id = _open_and_freeze(client)
        created = _bootstrap(client, shift_id, version_id)
        assert created.status_code == 202, created.text
        conn = db.connect(copied)
        try:
            experiment = repo.get_experiment(conn, created.json()["id"])
            return repo.get_execution_context(conn, experiment.context_id)
        finally:
            conn.close()


def test_reserved_isolated_context_records_the_approved_provider_ceiling(tmp_path, monkeypatch):
    """The frozen record must name the same ceiling the gateway will execute."""
    context = _reserve_bootstrap_and_read_context(tmp_path, monkeypatch, "copied-v5-ceiling.db")
    assert context.service_model_settings_json == {"temperature": 0, "max_tokens": 1024}
    runtime_policy = InferencePolicy(run_id="run", operation_id="operation",
        model=context.service_model, allowed_tool_names=("public_record_lookup",))
    assert context.service_model_settings_json["max_tokens"] == runtime_policy.max_output_tokens


def test_isolated_execution_binds_the_grant_to_the_frozen_mission_policy(tmp_path, monkeypatch):
    """The executed tool allowlist must equal the reviewed frozen mission vocabulary."""
    capture: dict = {}
    context = _reserve_bootstrap_and_read_context(tmp_path, monkeypatch, "copied-v5-grant.db", capture)
    mission = task_contract.load_mission_bytes(config.PIVOT_MISSION.read_bytes())
    assert capture["allowed_tool_names"] == tuple(mission.allowed_tool_vocabulary)
    assert context.mission_bytes_base64 == base64.b64encode(
        config.PIVOT_MISSION.read_bytes()).decode("ascii")


def test_reserved_isolated_context_records_the_configured_image(tmp_path, monkeypatch):
    """The frozen record must name the image the adapter gate will accept."""
    configured = "ffffffff-1111-2222-3333-444444444444"
    monkeypatch.setattr(config, "TOKEN_FACTORY_IMAGE", configured)
    context = _reserve_bootstrap_and_read_context(tmp_path, monkeypatch, "copied-v5-image.db")
    assert context.image_ref == configured
