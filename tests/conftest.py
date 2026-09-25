"""Test bootstrap: make the repository root importable as the package root."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import base64  # noqa: E402  (import order follows the sys.path bootstrap above)
from datetime import datetime, timezone  # noqa: E402

import pytest  # noqa: E402

from shiftwork import config  # noqa: E402
from shiftwork.domain import canonical  # noqa: E402
from shiftwork.executor import base as executor_base  # noqa: E402
from shiftwork.executor import local_process  # noqa: E402
from shiftwork.domain.models import OperatingSelection  # noqa: E402
from shiftwork.store import db, repo  # noqa: E402


@pytest.fixture()
def local_request():
    """Factory for a real trusted-fixture request, shaped as the conformance suite builds it.

    Shared by the executor-conformance, isolation and leakage tests so every adapter
    assertion runs against the same production-shaped ``RunRequest``.
    """

    def build(case_name: str = "happy_path") -> executor_base.RunRequest:
        root = config.FIXTURE_DIR / "artifacts" / "bookshop"
        files = {
            "service.py": (root / "service.py").read_bytes(),
            "learner_service.py": (config.PACKAGE_DIR / "templates" / "artifact" / "service.py").read_bytes(),
            "fixture.json": (root / f"{case_name}.json").read_bytes(),
        }
        batch = config.FIXTURE_DIR / "requests" / "bookshop.jsonl"
        return executor_base.RunRequest(
            artifact_snapshot=executor_base.ArtifactSnapshotRef(
                files=files, manifest_hash=config.TRUSTED_LOCAL_FIXTURES[case_name][0]
            ),
            request_batch=executor_base.BatchRef(
                path_ref="bookshop.jsonl",
                content_hash=canonical.content_hash(base64.b64encode(batch.read_bytes()).decode("ascii")),
            ),
            # Pinned to pair with the checked-in recorded transcripts this suite
            # replays (authored against the thin snapshot); the controller's own
            # default run binding is covered by the api and orchestrator suites.
            shop_snapshot_ref=str(config.THIN_SNAPSHOT),
            harness_ref="stdlib-loopback-v1",
            image_ref="local-python-stdlib",
            deadline_s=5,
            inference_grant=None,
        )

    return build


WORKSPACE_PREFIX = "shiftwork-fixture-"


@pytest.fixture()
def select_version_for_test():
    """Install a test-only choice so pre-pivot execution checks keep their subject.

    This bypasses comparison eligibility on purpose: S17 owns the production
    selection transaction. These older tests assert executor/ledger behavior for
    a chosen version, not that a learner can make a qualifying choice today.
    """

    def select(db_path, shift_id: str, version_id: str):
        conn = db.connect(db_path)
        try:
            shift = repo.get_shift(conn, shift_id)
            version = repo.get_version(conn, version_id)
            assert shift is not None and version is not None
            prior = repo.get_latest_operating_selection(conn, shift.engagement_slug)
            ordinal = repo.count_operating_selections(conn) + 1
            repo.insert_operating_selection(
                conn,
                OperatingSelection(
                    id=f"test-selection-{ordinal:04d}",
                    engagement_slug=shift.engagement_slug,
                    shift_id=shift_id,
                    kind="LEARNER_CHOICE",
                    selected_version_id=version_id,
                    selected_content_hash=version.content_hash,
                    rationale="Test-only selected-version prerequisite; eligibility is not asserted.",
                    requirement_set_hash=canonical.content_hash(
                        {"version": version.content_hash}
                    ),
                    prior_selection_id=prior.id if prior else None,
                    state="VALID",
                    client_request_id=f"test-selection:{shift_id}:{version_id}:{ordinal}",
                    created_at=datetime.now(timezone.utc),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    return select


@pytest.fixture()
def sandbox_inventory(monkeypatch):
    """(root, {relative posix path: bytes}) captured per real provisioning call.

    The inventory is read from the filesystem the moment ``provision_workspace``
    returns, before the subprocess starts, so any writing API is observed rather
    than only ``Path.write_bytes``.
    """
    recorded: list[tuple[Path, dict[str, bytes]]] = []
    original = local_process.provision_workspace

    def recording(root, request, shop_snapshot):
        manifest = original(root, request, shop_snapshot)
        inventory = {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }
        recorded.append((root, inventory))
        return manifest

    monkeypatch.setattr(local_process, "provision_workspace", recording)
    return recorded


@pytest.fixture()
def sandbox_only(sandbox_inventory):
    """Extract the single live sandbox workspace and its written files."""

    def extract():
        assert sandbox_inventory, (
            "no sandbox provisioning was recorded; the observer is not on the real provisioning path"
        )
        roots = {root for root, _ in sandbox_inventory}
        assert len(roots) == 1, f"expected one sandbox workspace, saw {len(roots)}"
        root = roots.pop()
        merged: dict[str, bytes] = {}
        for _, inventory in sandbox_inventory:
            merged.update(inventory)
        return root, merged

    return extract
