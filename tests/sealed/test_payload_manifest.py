"""Test 18 (program design S6.D): the sandbox payload manifest is exact.

The provisioning file list must equal the pinned allowlist - artifact snapshot,
current request batch, harness, frozen shop snapshot - and sealed specs and
expectations must be absent from the manifest and from every API response.

The check is deliberately three-way, because any single pair can agree by accident:

    pinned allowlist  ==  declared manifest  ==  bytes actually written

The third link is observed on the REAL adapter path: the workspace inventory
(paths and bytes) is read from the filesystem the moment provisioning returns and
before the subprocess starts, so the assertion is about what entered the sandbox
regardless of which writing API produced it, not about what a helper function
says it would write. Adding an undeclared file to the sandbox fails here even if
the manifest is left untouched.

Containment is asserted separately: a declared path is a filename rule, so
traversal, absolute and ambiguous destinations and cross-category collisions are
refused before the writer runs, and a refused manifest writes nothing.

Needle sets differ by surface (see ``leakscan``): the frozen shop snapshot is
public data that legitimately shares record ids with the sealed cases, so the
payload and API scans use ``sealed_identity_strings`` - operator notes, sealed case
and check identities, superseded refs and the sealed file path - which can never
legitimately appear. Test 16 covers expected values rigorously with a unique
injected sentinel.

Slice 6 scope, deferred clauses NOT claimed here:
  * "absent from every prompt before, during and after execution" is VACUOUS until
    the assist gateway exists; it re-runs non-vacuously at Slice 12.
  * the real-provisioning arm (``tokenfactory``) completes at Slice 14.
  * "future customer stimuli stay absent until their run" needs per-run variant
    selection and completes at Slice 7.
"""

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from leakscan import all_sealed_strings, decoded_surfaces, leaks_in, sealed_identity_strings
from shiftwork import config
from shiftwork.app import create_app
from shiftwork.executor import base as executor_base
from shiftwork.executor.base import provision_workspace, provisioning_manifest
from shiftwork.executor.local_process import LocalProcessAdapter
from shiftwork.executor.recorded import RecordedAdapter

CONTRACT = {
    "catalog_version": 1,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
    "response_time_limit_ms": 3000,
    "declared_limits": ["NO_SAME_DAY_DELIVERY_PROMISE"],
}

INCIDENT_TRANSCRIPT = config.FIXTURE_DIR / "runs" / "missing_evidence.json"


def test_pinned_allowlist_is_the_four_approved_categories() -> None:
    assert config.SANDBOX_PAYLOAD_ALLOWLIST == (
        "artifact_snapshot",
        "request_batch",
        "harness",
        "shop_snapshot",
    )


def test_manifest_categories_equal_the_pinned_allowlist(local_request) -> None:
    manifest = provisioning_manifest(local_request())
    assert set(manifest.categories) == set(config.SANDBOX_PAYLOAD_ALLOWLIST)
    assert set(manifest.provisioned) == {"artifact_snapshot", "shop_snapshot"}
    assert set(manifest.controller_side) == {"request_batch", "harness"}


def test_files_written_equal_the_declared_manifest(local_request, sandbox_only) -> None:
    """The third link: what really entered the sandbox, observed on the live path."""
    request = local_request()
    declared = provisioning_manifest(request)

    result = asyncio.run(LocalProcessAdapter().execute(request))
    assert result.failure is None, f"fixture run failed: {result.failure}"

    root, written = sandbox_only()
    assert sorted(written) == sorted(declared.paths), (
        f"sandbox payload {sorted(written)} != declared manifest {sorted(declared.paths)}"
    )
    expected_paths = sorted([*request.artifact_snapshot.files, executor_base.SANDBOX_SHOP_SNAPSHOT_NAME])
    assert sorted(written) == expected_paths

    for name, body in request.artifact_snapshot.files.items():
        assert written[name] == body, f"{name} was provisioned with different bytes"
    assert written[executor_base.SANDBOX_SHOP_SNAPSHOT_NAME] == Path(request.shop_snapshot_ref).read_bytes()
    assert root.is_absolute()


def test_manifest_rejects_a_category_outside_the_allowlist(local_request, monkeypatch) -> None:
    """Dropping a category from the allowlist makes the declared payload illegal."""
    request = local_request()
    monkeypatch.setattr(
        config,
        "SANDBOX_PAYLOAD_ALLOWLIST",
        tuple(c for c in config.SANDBOX_PAYLOAD_ALLOWLIST if c != "shop_snapshot"),
    )
    with pytest.raises(ValueError, match=r"outside the allowlist.*shop_snapshot"):
        provisioning_manifest(request)


def test_manifest_rejects_an_unprovisioned_allowlist_category(local_request, monkeypatch) -> None:
    """The allowlist cannot be widened silently: a new category must actually provision."""
    request = local_request()
    monkeypatch.setattr(
        config,
        "SANDBOX_PAYLOAD_ALLOWLIST",
        (*config.SANDBOX_PAYLOAD_ALLOWLIST, "sealed_expectations"),
    )
    with pytest.raises(ValueError, match=r"missing allowlisted categories.*sealed_expectations"):
        provisioning_manifest(request)


def _with_extra_file(request, name: str, body: bytes):
    files = {**request.artifact_snapshot.files, name: body}
    return request.model_copy(
        update={
            "artifact_snapshot": executor_base.ArtifactSnapshotRef(
                files=files, manifest_hash=request.artifact_snapshot.manifest_hash
            )
        }
    )


def test_manifest_rejects_paths_that_leave_the_workspace(local_request, tmp_path) -> None:
    """Containment: traversal, absolute and ambiguous destinations are refused.

    ``../escape.txt`` is not made safe by being declared under an allowlisted
    category, and a Windows drive or separator form must not slip past a POSIX
    containment check. The writer is asserted too: a refused manifest writes nothing.
    """
    bad_paths = (
        "../escape.txt",
        "nested/../escape.txt",
        "/absolute.txt",
        "C:drive.txt",
        "back\\slash.txt",
        "",
    )
    for index, bad in enumerate(bad_paths):
        request = _with_extra_file(local_request(), bad, b"payload")
        with pytest.raises(ValueError, match=r"sandbox payload path"):
            provisioning_manifest(request)
        root = tmp_path / f"workspace-{index}"
        root.mkdir()
        with pytest.raises(ValueError, match=r"sandbox payload path"):
            provision_workspace(root, request, b"snapshot")
        assert list(root.iterdir()) == [], "a rejected manifest must write nothing"


def test_manifest_rejects_a_colliding_path(local_request) -> None:
    """A category cannot silently overwrite another category's payload file."""
    request = _with_extra_file(
        local_request(), executor_base.SANDBOX_SHOP_SNAPSHOT_NAME, b"collide"
    )
    with pytest.raises(ValueError, match=r"path collision"):
        provisioning_manifest(request)


def test_manifest_rejects_names_the_platform_would_collapse(local_request, tmp_path) -> None:
    """Two declared paths NTFS resolves to one file are refused, not silently merged.

    NTFS is case-insensitive and strips trailing dots and spaces from a final
    component, so a literal string comparison accepts ``SHOP.JSON`` beside
    ``shop.json`` and writes one file twice while the other stays unwritten.
    """
    for index, colliding in enumerate(
        ("SHOP.JSON", "shop.json.", "shop.json ", "SERVICE.PY", "fixture.json ")
    ):
        request = _with_extra_file(local_request(), colliding, b"payload")
        with pytest.raises(ValueError, match=r"path collision"):
            provisioning_manifest(request)
        root = tmp_path / f"collapse-{index}"
        root.mkdir()
        with pytest.raises(ValueError, match=r"path collision"):
            provision_workspace(root, request, b"snapshot")
        assert list(root.iterdir()) == [], "a refused manifest must write nothing"


def test_manifest_rejects_reserved_device_names_and_directory_components(local_request) -> None:
    """A reserved device name or a directory component is refused, not provisioned.

    ``NUL`` and ``CON.txt`` are resolved by Win32 to devices, so the declared path
    never materializes as a payload file; a directory component cannot be created by
    the writer and would let a junction inside the workspace redirect a nested write.
    """
    for bad in ("NUL", "con", "Com1", "LPT9.TXT", "nul ", "sub/dir.py", "dir/"):
        request = _with_extra_file(local_request(), bad, b"payload")
        with pytest.raises(ValueError, match=r"sandbox payload path"):
            provisioning_manifest(request)


def test_no_sealed_material_in_manifest_or_request_payload(local_request) -> None:
    request = local_request()
    needles = all_sealed_strings()
    for label, payload in (
        ("manifest", provisioning_manifest(request).model_dump_json()),
        ("run request", request.model_dump_json()),
    ):
        found = leaks_in(payload, needles)
        assert not found, f"sealed material in the {label}: {found[:3]}"


def test_no_sealed_material_in_the_provisioned_sandbox_payload(
    local_request, sandbox_only
) -> None:
    request = local_request()
    result = asyncio.run(LocalProcessAdapter().execute(request))
    assert result.failure is None

    _, written = sandbox_only()
    assert written, "the sandbox was provisioned empty; the scan proved nothing"
    needles = sealed_identity_strings()
    for name, data in written.items():
        text = data.decode("utf-8", errors="replace")
        found = leaks_in(text, needles)
        assert not found, f"sealed material provisioned into {name}: {found[:3]}"


def test_recorded_adapter_provisions_no_sandbox_payload(
    local_request, sandbox_inventory
) -> None:
    """Replay executes nothing, so it must write nothing into a sandbox."""
    request = local_request()
    result = asyncio.run(
        RecordedAdapter(config.FIXTURE_DIR / "runs" / "happy_path.json").execute(request)
    )
    assert result.failure is None
    assert sandbox_inventory == [], f"recorded replay wrote into a sandbox workspace: {sandbox_inventory}"


def test_sealed_absent_from_every_api_response(tmp_path, monkeypatch) -> None:
    """Drive the full incident-producing lifecycle and scan every response.

    Error bodies are learner-visible surfaces too: the client renders the error
    detail, so a 404, a 409 and a 422 are driven after the run finalized and their
    decoded bodies enter the same scan as the success responses and served HTML.
    """
    monkeypatch.setattr(config, "THIN_TRANSCRIPT", INCIDENT_TRANSCRIPT)
    needles = sealed_identity_strings()
    surfaces: list[tuple[str, str]] = []
    called: set[str] = set()

    with TestClient(create_app(str(tmp_path / "manifest.db"))) as client:
        def record(method: str, url: str, **kwargs):
            response = getattr(client, method)(url, **kwargs)
            called.add(f"{method.upper()} {url}")
            for surface in decoded_surfaces(response.text):
                surfaces.append((f"{method.upper()} {url}", surface))
            return response

        shift = record("post", "/api/engagements/bookshop/shifts")
        assert shift.status_code == 201, shift.text
        shift_id = shift.json()["id"]
        record("get", "/")

        draft = record("get", f"/api/shifts/{shift_id}/artifact")
        assert draft.status_code == 200, draft.text
        record("put", f"/api/shifts/{shift_id}/artifact", json={"files": draft.json()["files"]})

        version = record("post", f"/api/shifts/{shift_id}/artifact/versions", json={"contract": CONTRACT})
        assert version.status_code == 201, version.text

        started = record("post", f"/api/shifts/{shift_id}/runs")
        assert started.status_code == 202, started.text
        run_id = started.json()["id"]

        run = record("get", f"/api/runs/{run_id}")
        assert run.json()["state"] == "FINALIZED", run.text
        record("get", f"/api/runs/{run_id}/outputs")
        checks = record("get", f"/api/runs/{run_id}/checks")
        record("get", "/api/engagements/bookshop/ledger")
        board = record("get", "/api/engagements/bookshop/board")

        incidents = board.json()["open_incidents"]
        assert incidents, "no incident was produced; the incident projection was not scanned"
        for incident in incidents:
            record("get", f"/api/incidents/{incident['id']}")

        record("post", f"/api/shifts/{shift_id}/close")

        missing = record("get", f"/api/runs/{run_id}-missing")
        assert missing.status_code == 404, missing.text
        closed = record("post", f"/api/shifts/{shift_id}/runs")
        assert closed.status_code == 409, closed.text
        invalid = record("put", f"/api/shifts/{shift_id}/artifact", json={"files": 123})
        assert invalid.status_code == 422, invalid.text

    # Non-vacuity: the run really was evaluated, so the scanned surfaces carry results,
    # and every route driven through the lifecycle contributed a scanned surface.
    assert checks.json(), "no check results were produced; the response scan proved nothing"
    assert any(check["expected_ref"].startswith("sealed:") for check in checks.json())
    scanned_routes = {label for label, _ in surfaces}
    assert scanned_routes == called, f"routes never scanned: {sorted(called - scanned_routes)}"
    assert len(surfaces) >= len(called), (
        f"{len(surfaces)} surfaces from {len(called)} calls; a response was not decoded"
    )

    leaks = [
        (label, found)
        for label, surface in surfaces
        if (found := leaks_in(surface, needles))
    ]
    assert not leaks, "\n".join(f"{label}: {found[:3]}" for label, found in leaks[:10])
