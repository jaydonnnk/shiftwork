"""Slice 8 run binding: the run row is the single source of execution identity.

The controller persists the executor and shop snapshot it is configured with at
``start_run``, and ``execute_run`` resolves the adapter from the run alone. These
checks are failing-capable per branch: they turn red if the resolution ignores the
run row (falls back to the configured default), if an unmapped recorded pairing is
silently replayed, or if an adapter without an implementation is treated as
executable. The authored pairing map itself is guarded against the fixture files.
"""

import base64
import json

from fastapi.testclient import TestClient

from conftest import CONTRACT
from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain import canonical
from shiftwork.store import db


def _drive_to_frozen(client: TestClient) -> str:
    shift = client.post("/api/engagements/bookshop/shifts").json()
    frozen = client.post(
        f"/api/shifts/{shift['id']}/artifact/versions", json={"contract": CONTRACT}
    )
    assert frozen.status_code == 201, frozen.text
    return shift["id"]


def _wait(client: TestClient, run_id: str) -> dict:
    import time

    deadline = time.monotonic() + 10
    while True:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["state"] in {"FINALIZED", "FAILED"} or time.monotonic() > deadline:
            return run
        time.sleep(0.02)


def test_snapshot_pins_and_authored_pairings_match_the_fixtures():
    """Guard the authored map: pins must match the files and the transcripts
    must declare exactly the batch and snapshot hashes they are keyed under, so a
    mis-keyed or re-pinned entry cannot quietly change which run replays what."""
    for snapshot, pinned in (
        (config.BOOKSHOP_SNAPSHOT, config.BOOKSHOP_SNAPSHOT_HASH),
        (config.THIN_SNAPSHOT, config.THIN_SNAPSHOT_HASH),
    ):
        computed = canonical.content_hash(base64.b64encode(snapshot.read_bytes()).decode("ascii"))
        assert computed == pinned, f"{snapshot.name} no longer matches its pinned hash"
    assert config.BOOKSHOP_SNAPSHOT_HASH != config.THIN_SNAPSHOT_HASH

    assert config.RECORDED_TRANSCRIPTS, "the authored pairing map is empty"
    for (batch_ref, snapshot_hash), transcript in config.RECORDED_TRANSCRIPTS.items():
        batch = config.FIXTURE_DIR / "requests" / batch_ref
        assert batch.is_file(), f"pairing cites an unknown batch: {batch_ref}"
        batch_hash = canonical.content_hash(base64.b64encode(batch.read_bytes()).decode("ascii"))
        declared = json.loads((config.FIXTURE_DIR / "runs" / transcript).read_bytes())
        assert declared["request_batch_hash"] == batch_hash, (
            f"{transcript} is keyed under {batch_ref} but declares another batch"
        )
        assert declared["shop_snapshot_hash"] == snapshot_hash, (
            f"{transcript} is keyed under a snapshot hash it does not declare"
        )


def test_run_row_adapter_is_load_bearing(session):
    # A run persisted as local_process must be executed by the local_process
    # adapter, which refuses a learner artifact that is not a pinned trusted
    # fixture: FAILED with a typed PROVISION_FAILED and no captures. The run's own
    # (batch, snapshot) pairing exists in the authored map, so a resolution that
    # ignored run.adapter and used the configured recorded default would have
    # replayed a transcript and FINALIZED this run instead.
    conn = db.connect(session.db_file)
    try:
        run = orchestrator.start_run(conn, session.shift_id, executor="local_process")
        assert run.adapter == "local_process"
        assert (run.request_batch_ref, config.BOOKSHOP_SNAPSHOT_HASH) in config.RECORDED_TRANSCRIPTS
    finally:
        conn.close()

    orchestrator.execute_run_task(str(session.db_file), run.id)
    finished = session.run(run.id)
    assert finished["state"] == "FAILED", finished
    assert finished["failure_kind"] == "PROVISION_FAILED", finished
    assert finished["adapter"] == "local_process"
    assert session.client.get(f"/api/runs/{run.id}/outputs").json() == []
    assert session.client.get(f"/api/runs/{run.id}/checks").json() == []
    assert session.client.get("/api/engagements/bookshop/ledger").json()["events"] == []
    assert session.board()["attempts_used"] == 1, "a failed run must still consume its reservation"


def test_unmapped_pairing_fails_closed_without_invoking_an_adapter(session, monkeypatch):
    # With this attempt's pairing removed from the authored map, the run must fail
    # closed and never reach an adapter. A fallback that picked any other
    # transcript would invoke the recording below; a fallback that happened to
    # pair would finalize the run.
    invoked: list = []
    recorded_adapter = orchestrator.RecordedAdapter

    class Recording(recorded_adapter):
        async def execute(self, request):
            invoked.append(request)
            return await super().execute(request)

    monkeypatch.setattr(orchestrator, "RecordedAdapter", Recording)
    monkeypatch.delitem(
        config.RECORDED_TRANSCRIPTS,
        ("bookshop_attempt_01.jsonl", config.BOOKSHOP_SNAPSHOT_HASH),
    )
    assert ("bookshop_attempt_01.jsonl", config.THIN_SNAPSHOT_HASH) in config.RECORDED_TRANSCRIPTS

    run = session.attempt()
    assert run["state"] == "FAILED", run
    assert run["failure_kind"] == "PROVISION_FAILED", run
    assert invoked == [], "an adapter was invoked for an unmapped pairing"
    assert session.client.get(f"/api/runs/{run['id']}/outputs").json() == []
    assert session.client.get(f"/api/runs/{run['id']}/checks").json() == []
    assert session.board()["attempts_used"] == 1, "a failed run must still consume its reservation"


def test_unimplemented_adapter_fails_closed_before_execution(session):
    # tokenfactory is a valid persisted adapter name but has no implementation
    # before Slice 14: resolving it must fail closed with a typed PROVISION_FAILED
    # and write no captures, never fall back to another adapter.
    conn = db.connect(session.db_file)
    try:
        run = orchestrator.start_run(conn, session.shift_id, executor="tokenfactory")
        assert run.adapter == "tokenfactory"
    finally:
        conn.close()

    orchestrator.execute_run_task(str(session.db_file), run.id)
    finished = session.run(run.id)
    assert finished["state"] == "FAILED", finished
    assert finished["failure_kind"] == "PROVISION_FAILED", finished
    assert finished["adapter"] == "tokenfactory"
    assert session.client.get(f"/api/runs/{run.id}/outputs").json() == []
    assert session.client.get(f"/api/runs/{run.id}/checks").json() == []
    assert session.client.get("/api/engagements/bookshop/ledger").json()["events"] == []


def test_route_persists_the_controller_configured_adapter(tmp_path):
    # The route takes the executor from the app's controller configuration, never
    # from the request body. Configured for local_process, the run row persists
    # local_process and is executed by it (failing closed on the untrusted learner
    # artifact); a route that ignored the app configuration would persist
    # 'recorded', pair batch 1 with its transcript and FINALIZE.
    db_file = tmp_path / "binding.db"
    with TestClient(create_app(str(db_file), executor="local_process")) as client:
        shift_id = _drive_to_frozen(client)
        started = client.post(f"/api/shifts/{shift_id}/runs")
        assert started.status_code == 202, started.text
        run_id = started.json()["id"]
        assert started.json()["adapter"] == "local_process", started.json()
        run = _wait(client, run_id)
        assert run["state"] == "FAILED", run
        assert run["failure_kind"] == "PROVISION_FAILED", run
        assert run["adapter"] == "local_process", run
        assert client.get(f"/api/runs/{run_id}/outputs").json() == []
        assert client.get(f"/api/runs/{run_id}/checks").json() == []
        assert client.get("/api/engagements/bookshop/ledger").json()["events"] == []
