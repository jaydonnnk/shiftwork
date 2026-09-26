"""Test 45 (program design S6.L): the artifact working copy round-trips and projections carry no internal refs.

Two clauses:

1. ``GET /shifts/{id}/artifact`` returns exactly the saved filenames and text, and
   ``PUT`` round-trips them. ``DraftView`` is the sole browser path for editable
   file contents (Gate 3 S3.9), so a lossy or merging round-trip would be a product
   defect, not just a projection defect.
2. Every public projection omits injected storage, host, sandbox, request and
   response refs.

Clause 2 is tested by INJECTION, not by inspection: the shop snapshot is relocated
to a marker-named directory, the database to a marker-named path and the sandbox
temp parent to a marker-named directory, so the runtime ``shop_snapshot_ref``, DB
path and sandbox workspace path carry unique tokens. The request refs are the real
batch path and hash the lifecycle constructs and the response ref is the real log
data-URI prefix a local-adapter run constructs; a capability self-test proves every
needle can match a serialized surface before any absence is asserted.
"""

import asyncio
import json
import tempfile

import pytest
from fastapi.testclient import TestClient

from leakscan import decoded_surfaces, host_leaks
from shiftwork import config
from shiftwork.api.schemas import RunOutputView
from shiftwork.app import create_app
from shiftwork.executor import base as executor_base
from shiftwork.executor.local_process import LocalProcessAdapter
from shiftwork.store import db, repo

CONTRACT = {
    "catalog_version": 1,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
    "response_time_limit_ms": 3000,
    "declared_limits": ["NO_SAME_DAY_DELIVERY_PROMISE"],
}

SNAPSHOT_MARKER = "sw6-host-marker-dir"
DB_MARKER = "sw6-db-marker-dir"
SANDBOX_MARKER = "sw6-sandbox-marker-parent"
LOG_URI_PREFIX = "data:application/octet-stream;base64,"

LEARNER_FILES = {
    "service.py": "# learner edit\nprint('handled by the learner')\n",
    "contract.json": json.dumps({"stance": "USE_NEWEST_RECORD_WITH_AGE"}, indent=2),
    "notes.md": "# Decisions\n\n- cited the newest shelf record with its true age\n",
}

REVISED_FILES = {"service.py": "# learner edit, second save\nprint('revised')\n"}


@pytest.fixture()
def injected_hosts(tmp_path, monkeypatch):
    """Relocate the snapshot and the DB so their real paths carry unique markers."""
    snapshot_dir = tmp_path / SNAPSHOT_MARKER
    snapshot_dir.mkdir()
    snapshot = snapshot_dir / "snapshot.json"
    snapshot.write_bytes(config.BOOKSHOP_SNAPSHOT.read_bytes())
    monkeypatch.setattr(config, "BOOKSHOP_SNAPSHOT", snapshot)

    db_dir = tmp_path / DB_MARKER
    db_dir.mkdir()
    return {"snapshot": snapshot, "db_path": db_dir / "shiftwork.db"}


def _internal_ref_needles(injected, storage_ref: str) -> dict[str, str]:
    """Real internal ref values that must never reach a public projection.

    Every entry is a value the runtime genuinely constructs or the fixture
    injected. Field names are deliberately not needles: a name is not a ref, and
    asserting its absence would prove nothing about the value it labels.
    """
    return {
        "storage_ref scheme": "inline:",
        "storage_ref value": storage_ref,
        "host snapshot path": str(injected["snapshot"]),
        "host snapshot marker": SNAPSHOT_MARKER,
        "database path": str(injected["db_path"]),
        "database marker": DB_MARKER,
        "package path": str(config.PACKAGE_DIR),
        "sealed store path": str(config.SEALED_CASES_DIR),
        "request batch path_ref": "thin.jsonl",
        "request batch hash": config.THIN_BATCH_HASH,
        "harness ref": "stdlib-loopback-v1",
        "image ref": "local-python-stdlib",
        "sandbox workspace prefix": "shiftwork-fixture-",
    }


def _assert_needles_can_match(needles: dict[str, str]) -> None:
    """Capability self-test: every needle must be detectable in a serialized surface."""
    for name, value in needles.items():
        assert host_leaks(json.dumps({"probe": value}), {name: value}), (
            f"needle {name!r} cannot match a serialized surface; its absence proves nothing"
        )


def test_draft_round_trip_preserves_filenames_and_text(injected_hosts) -> None:
    with TestClient(create_app(str(injected_hosts["db_path"]))) as client:
        shift = client.post("/api/engagements/bookshop/shifts")
        assert shift.status_code == 201, shift.text
        shift_id = shift.json()["id"]

        seeded = client.get(f"/api/shifts/{shift_id}/artifact")
        assert seeded.status_code == 200, seeded.text
        # Slice 11 ships the reviewed failing starter as the new engagement's draft,
        # so the seeded file set is the pinned starter's, not the old scaffold's.
        assert set(seeded.json()["files"]) == set(config.PIVOT_STARTER_ARTIFACT_PATHS)

        written = client.put(f"/api/shifts/{shift_id}/artifact", json={"files": LEARNER_FILES})
        assert written.status_code == 200, written.text
        assert written.json()["files"] == LEARNER_FILES

        read_back = client.get(f"/api/shifts/{shift_id}/artifact")
        assert read_back.json()["files"] == LEARNER_FILES, "GET did not return the saved filenames and text"
        assert read_back.json()["shift_id"] == shift_id

        # A later save replaces the set; it does not merge stale filenames in.
        revised = client.put(f"/api/shifts/{shift_id}/artifact", json={"files": REVISED_FILES})
        assert revised.status_code == 200, revised.text
        after = client.get(f"/api/shifts/{shift_id}/artifact").json()
        assert after["files"] == REVISED_FILES
        assert "notes.md" not in after["files"], "a removed file survived the round-trip"

        # Non-ASCII and newline-bearing text survives byte for byte.
        unicode_files = {"service.py": "print('café — naïve')\nline2\r\nline3\ttab\n"}
        client.put(f"/api/shifts/{shift_id}/artifact", json={"files": unicode_files})
        assert client.get(f"/api/shifts/{shift_id}/artifact").json()["files"] == unicode_files


def test_public_projections_omit_injected_internal_refs(injected_hosts) -> None:
    # The marker snapshot is a byte copy of the shipped default, so the run's
    # authored pairing (Slice 8) resolves and the incident surfaces are real.
    surfaces: list[tuple[str, str]] = []
    called: set[str] = set()

    with TestClient(create_app(str(injected_hosts["db_path"]))) as client:
        def record(method: str, url: str, **kwargs):
            response = getattr(client, method)(url, **kwargs)
            called.add(f"{method.upper()} {url}")
            for surface in decoded_surfaces(response.text):
                surfaces.append((f"{method.upper()} {url}", surface))
            return response

        shift = record("post", "/api/engagements/bookshop/shifts")
        shift_id = shift.json()["id"]
        record("get", "/")
        record("get", f"/api/shifts/{shift_id}/artifact")
        record("put", f"/api/shifts/{shift_id}/artifact", json={"files": LEARNER_FILES})
        version = record("post", f"/api/shifts/{shift_id}/artifact/versions", json={"contract": CONTRACT})
        assert version.status_code == 201, version.text
        started = record("post", f"/api/shifts/{shift_id}/runs")
        run_id = started.json()["id"]
        run = record("get", f"/api/runs/{run_id}")
        assert run.json()["state"] == "FINALIZED", run.text
        record("get", f"/api/runs/{run_id}/outputs")
        checks = record("get", f"/api/runs/{run_id}/checks")
        record("get", "/api/engagements/bookshop/ledger")
        board = record("get", "/api/engagements/bookshop/board")
        record("get", f"/api/shifts/{shift_id}/artifact")
        record("post", f"/api/shifts/{shift_id}/close")

        incidents = board.json()["incidents"]
        assert incidents, "no incident was produced; the incident projection was not scanned"
        for incident in incidents:
            record("get", f"/api/incidents/{incident['id']}")

        # Error bodies are learner-visible surfaces too: a 404, a 409 and a 422
        # driven after the finalized run enter the same projection scan.
        missing = record("get", f"/api/runs/{run_id}-missing")
        assert missing.status_code == 404, missing.text
        closed = record("post", f"/api/shifts/{shift_id}/runs")
        assert closed.status_code == 409, closed.text
        invalid = record("put", f"/api/shifts/{shift_id}/artifact", json={"files": 123})
        assert invalid.status_code == 422, invalid.text

    # The run really executed and produced results, so the projections carry content.
    assert checks.json(), "no check results; the projection scan proved nothing"

    # storage_ref is durable-only: read it straight from the table, never from a response.
    conn = db.connect(str(injected_hosts["db_path"]))
    try:
        stored = repo.get_version(conn, version.json()["id"])
    finally:
        conn.close()
    assert stored is not None
    assert stored.storage_ref.startswith("inline:"), (
        f"the fixture storage_ref changed shape: {stored.storage_ref!r}"
    )

    needles = _internal_ref_needles(injected_hosts, stored.storage_ref)
    _assert_needles_can_match(needles)
    leaks = [
        (label, name, value)
        for label, surface in surfaces
        for name, value in host_leaks(surface, needles)
    ]
    assert not leaks, "\n".join(f"{label} leaked {name}={value!r}" for label, name, value in leaks[:12])

    # Non-vacuity: the scan covered the whole lifecycle and the needles are real values.
    assert len(surfaces) >= len(called), f"{len(surfaces)} surfaces from {len(called)} calls"
    assert stored.storage_ref not in json.dumps(version.json()), "sanity: version view must not carry storage_ref"
    assert needles["request batch hash"] == config.THIN_BATCH_HASH
    assert needles["host snapshot marker"] == SNAPSHOT_MARKER


def test_injected_sandbox_and_response_refs_stay_out_of_local_projections(
    tmp_path, monkeypatch, local_request, sandbox_only
) -> None:
    """Clause 2 for the sandbox and response refs, on the run that really constructs them.

    The recorded lifecycle path carries no sandbox and no log bytes, so the
    injection happens where those refs exist: the sandbox temp parent is relocated
    to a marker-named directory and the local adapter run produces a real log
    data-URI. Both values are then asserted absent from every projection built
    from that run.
    """
    marker_dir = tmp_path / SANDBOX_MARKER
    marker_dir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(marker_dir))

    request = local_request("env_probe")
    result = asyncio.run(LocalProcessAdapter().execute(request))
    assert result.failure is None, f"env_probe fixture run failed: {result.failure}"

    root, written = sandbox_only()
    assert SANDBOX_MARKER in str(root), "the sandbox path marker was not injected"
    assert root.name.startswith("shiftwork-fixture-"), f"unexpected workspace name: {root.name}"
    assert written, "the sandbox was provisioned empty; the sandbox-ref arm is vacuous"

    log_refs = [capture.log_ref for capture in result.captures if capture.log_ref]
    assert log_refs, "no log ref was constructed; the response-ref arm is vacuous"
    assert all(ref.startswith(LOG_URI_PREFIX) for ref in log_refs)

    outputs = executor_base.normalize_captures(result.captures, request.deadline_s)
    views = [RunOutputView.of(output) for output in outputs]
    assert any(view.log_base64 for view in views), "no log payload survived projection"
    surfaces = [surface for view in views for surface in decoded_surfaces(view.model_dump_json())]

    needles = {
        "sandbox workspace path": str(root),
        "sandbox workspace marker": SANDBOX_MARKER,
        "sandbox workspace prefix": "shiftwork-fixture-",
        "response ref scheme": LOG_URI_PREFIX,
    }
    _assert_needles_can_match(needles)
    leaks = [
        (name, value)
        for surface in surfaces
        for name, value in host_leaks(surface, needles)
    ]
    assert not leaks, f"a local-adapter projection exposed internal refs: {leaks[:5]}"
