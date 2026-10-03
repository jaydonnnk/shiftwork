"""Test 16 (program design S6.D): a sealed sentinel never leaves the controller.

A unique sentinel is placed inside a real sealed ``expected`` block - in the operator
note, the cited record id and the expected claim value - and the full lifecycle is
driven against it. The sentinel is then scanned for on every serialized outbound
surface: the API responses (envelope and decoded bodies, success and error bodies
both driven), the served client HTML,
the outbound executor payload, the provisioned sandbox files, the captured
execution logs, the controller log and the controller stdout/stderr.

Why a sentinel rather than the real inventory: the sealed notes and expected values
legitimately share text with public fixtures (record ids live in the shop snapshot,
and a passing run echoes the expected claim in the learner's own output), so a scan
over the real values cannot distinguish a leak from a correct answer. A token that
exists nowhere else in the repository has no innocent explanation. Test 18 covers
the real inventory's identities.

Non-vacuity is asserted explicitly: the sentinel must provably have been inside the
sealed cases the evaluator actually scored, shown by the opaque ``expected_ref``
digest changing relative to the un-sentinelized family, and the stdout/stderr
capture is probed with the sentinel before the lifecycle so the scan cannot pass
against a mechanism that observes nothing. Without those checks a silently
ineffective monkeypatch would make every scan below pass for free.

Slice 14 exercises the assist-prompt clause against the real gateway request
using a local HTTP double. No provider call is made.
"""

import asyncio
import base64
import hashlib
import json
import logging
import shutil
import sys
from pathlib import Path

import pytest
import httpx
from fastapi.testclient import TestClient

from leakscan import decoded_surfaces
from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.assist.gateway import LiveAssistGateway
from shiftwork.gateway.redaction import serialized_contains
from shiftwork.evaluator.evaluator import expected_ref_for
from shiftwork.executor.local_process import LocalProcessAdapter
from shiftwork.sealed import store as sealed_store
from shiftwork.packs import registry

# Must exist nowhere else in the repository; asserted below before use.
SENTINEL = "qZ7xSw6SeNtInElK4mP9wR2"

CONTRACT = {
    "catalog_version": 1,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
    "response_time_limit_ms": 3000,
    "declared_limits": ["NO_SAME_DAY_DELIVERY_PROMISE"],
}

REPO_ROOT = config.PACKAGE_DIR.parent


def _family_path():
    return config.SEALED_CASES_DIR / sealed_store._FAMILY_FILES[sealed_store.STALE_INFORMATION]


def _baseline_refs() -> dict[str, str]:
    """Opaque expected refs for the real, un-sentinelized sealed inventory."""
    cases = sealed_store.load_family(sealed_store.STALE_INFORMATION).cases
    assert cases, "the real sealed inventory is empty; the non-vacuity check cannot run"
    return {case.check_id: expected_ref_for(case) for case in cases}


@pytest.fixture()
def sentinel_family(tmp_path, monkeypatch):
    """A real sealed family copy with SENTINEL injected into every expected block.

    The user-sealed ``stale_information`` inventory on disk is never modified: the
    sentinelized copy lives in ``tmp_path`` and the loader is pointed at it.
    """
    baseline = _baseline_refs()
    data = json.loads(_family_path().read_text(encoding="utf-8"))

    for index, case in enumerate(data["cases"]):
        expected = case["expected"]
        expected["note"] = f"{SENTINEL} operator note. {expected['note']}"
        if index == 0:
            expected["record_id"] = f"{SENTINEL}:{expected['record_id']}"
            claim = expected["expected_claim"]
            if isinstance(claim.get("value"), str):
                claim["value"] = f"{SENTINEL}-{claim['value']}"

    pack = registry.resolve_pack("bookshop")
    root = tmp_path / "package"
    for pin in pack.reviewed_pins:
        copied = root / pin.path
        copied.parent.mkdir(parents=True, exist_ok=True)
        copied.write_bytes((config.PACKAGE_DIR / pin.path).read_bytes())
    # Shared legacy-lifecycle and local-executor checks also use older catalogs
    # and the artifact template. Keep those support files in the disposable root.
    shutil.copytree(config.CATALOG_DIR, root / "fixtures/catalogs", dirs_exist_ok=True)
    shutil.copytree(config.PACKAGE_DIR / "templates", root / "templates")
    directory = root / "sealed/cases"
    path = directory / sealed_store._FAMILY_FILES[sealed_store.STALE_INFORMATION]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    # Only the disposable declaration pins its changed expectation bytes.
    # Admission still checks the complete package, locator, pins and seals.
    pins = tuple(pin.model_copy(update={"sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                 if pin.path == path.relative_to(root).as_posix() else pin for pin in pack.reviewed_pins)
    monkeypatch.setattr(registry, "_PACKS", (pack.model_copy(update={"reviewed_pins": pins}),
                                           *registry.registered_packs()[1:]))
    monkeypatch.setattr(config, "PACKAGE_DIR", root)
    monkeypatch.setattr(config, "CATALOG_DIR", root / "fixtures/catalogs")
    monkeypatch.setattr(config, "SEALED_CASES_DIR", directory)

    loaded = sealed_store.load_family(sealed_store.STALE_INFORMATION).cases
    assert loaded, "the sentinel family did not load; every scan below would be vacuous"
    assert all(SENTINEL in json.dumps(case.expected) for case in loaded), (
        "the sentinel is not inside every loaded expected block"
    )
    return {"path": path, "cases": loaded, "baseline_refs": baseline}


@pytest.fixture()
def observed_requests(monkeypatch):
    """Capture the RunRequest the controller actually hands to the adapter."""
    seen: list = []
    real_adapter = orchestrator.RecordedAdapter

    class Recording(real_adapter):
        async def execute(self, request):
            seen.append(request)
            return await super().execute(request)

    monkeypatch.setattr(orchestrator, "RecordedAdapter", Recording)
    return seen


def test_sentinel_is_unique_in_the_repository() -> None:
    """The scan only means something if the token exists nowhere else."""
    this_file = Path(__file__).resolve()
    skipped_parts = {"__pycache__", ".git", ".venv", "node_modules", ".pytest_cache"}
    hits = []
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file() or path.resolve() == this_file:
            continue
        if skipped_parts & set(path.parts) or path.suffix in {".db", ".pyc", ".lock"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if SENTINEL in text:
            hits.append(path.relative_to(REPO_ROOT).as_posix())
    assert not hits, f"sentinel already present in: {hits}"


def test_sentinel_changes_the_opaque_expected_ref(sentinel_family) -> None:
    """Non-vacuity: the sentinel really was inside the block the evaluator hashes."""
    baseline = sentinel_family["baseline_refs"]
    current = {case.check_id: expected_ref_for(case) for case in sentinel_family["cases"]}
    assert set(current) == set(baseline), "the sentinel family changed the case inventory"
    changed = [check_id for check_id in baseline if current[check_id] != baseline[check_id]]
    assert len(changed) == len(baseline), (
        f"only {len(changed)}/{len(baseline)} expected refs changed; the sentinel did not "
        "reach every expected block, so the outbound scans would be partly vacuous"
    )
    # The ref stays an opaque digest: the sentinel is hashed, never rendered.
    assert all(SENTINEL not in ref for ref in current.values())
    assert all(ref.startswith("sealed:") for ref in current.values())


def test_sentinel_absent_from_every_api_response_and_the_controller_streams(
    tmp_path, sentinel_family, observed_requests, caplog, capsys
) -> None:
    # The shipped default (Slice 8) replays attempt 1 against the fuller snapshot,
    # which fails every family's first variant and opens incidents; the incident
    # surfaces below are scanned for that real failure, not a redirected one.

    # The capture mechanisms are probed first: a scan of a surface nobody observes
    # would pass vacuously.
    print(f"stdout self-test {SENTINEL}")
    print(f"stderr self-test {SENTINEL}", file=sys.stderr)
    probe = capsys.readouterr()
    assert SENTINEL in probe.out and SENTINEL in probe.err, (
        "the stdout/stderr capture did not observe the injected sentinel"
    )

    surfaces: list[tuple[str, str]] = []
    called: set[str] = set()

    with caplog.at_level(logging.DEBUG):
        with TestClient(create_app(str(tmp_path / "sentinel.db"))) as client:
            def record(method: str, url: str, **kwargs):
                response = getattr(client, method)(url, **kwargs)
                called.add(f"{method.upper()} {url}")
                for surface in decoded_surfaces(response.text):
                    surfaces.append((f"{method.upper()} {url}", surface))
                return response

            record("get", "/")

            shift = record("post", "/api/engagements/bookshop/shifts")
            assert shift.status_code == 201, shift.text
            shift_id = shift.json()["id"]

            draft = record("get", f"/api/shifts/{shift_id}/artifact")
            assert draft.status_code == 200, draft.text
            record("put", f"/api/shifts/{shift_id}/artifact", json={"files": draft.json()["files"]})
            version = record(
                "post", f"/api/shifts/{shift_id}/artifact/versions", json={"contract": CONTRACT}
            )
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

            incidents = board.json()["incidents"]
            assert incidents, "no incident was produced; the incident surface was not scanned"
            for incident in incidents:
                record("get", f"/api/incidents/{incident['id']}")

            record("get", f"/api/shifts/{shift_id}/artifact")
            record("post", f"/api/shifts/{shift_id}/close")

            # Error bodies are learner-visible surfaces too: a 404, a 409 and a
            # 422 driven after the finalized run enter the same sentinel scan.
            missing = record("get", f"/api/runs/{run_id}-missing")
            assert missing.status_code == 404, missing.text
            closed = record("post", f"/api/shifts/{shift_id}/runs")
            assert closed.status_code == 409, closed.text
            invalid = record("put", f"/api/shifts/{shift_id}/artifact", json={"files": 123})
            assert invalid.status_code == 422, invalid.text

    # The sentinel-bearing cases really were evaluated into real results.
    results = checks.json()
    assert results, "no check results; the response scan proved nothing"
    assert all(check["expected_ref"].startswith("sealed:") for check in results)
    assert observed_requests, "the adapter was never called; the run was not executed"
    assert len(surfaces) >= len(called), f"{len(surfaces)} surfaces from {len(called)} calls"

    for label, surface in surfaces:
        assert SENTINEL not in surface, f"sealed sentinel leaked into {label}"
    assert SENTINEL not in caplog.text, "sealed sentinel leaked into the controller log"
    captured = capsys.readouterr()
    assert SENTINEL not in captured.out, "sealed sentinel leaked into controller stdout"
    assert SENTINEL not in captured.err, "sealed sentinel leaked into controller stderr"


def test_sentinel_absent_from_the_outbound_executor_payload(
    tmp_path, sentinel_family, observed_requests
) -> None:
    """What the controller sends to an adapter is an outbound surface too."""
    with TestClient(create_app(str(tmp_path / "sentinel-payload.db"))) as client:
        shift = client.post("/api/engagements/bookshop/shifts")
        shift_id = shift.json()["id"]
        client.post(f"/api/shifts/{shift_id}/artifact/versions", json={"contract": CONTRACT})
        started = client.post(f"/api/shifts/{shift_id}/runs")
        run_id = started.json()["id"]
        assert client.get(f"/api/runs/{run_id}").json()["state"] == "FINALIZED"

    assert observed_requests, "no RunRequest was captured; the arm is vacuous"
    for request in observed_requests:
        assert SENTINEL not in request.model_dump_json(), "sentinel in the outbound executor payload"
        assert SENTINEL not in str(request.shop_snapshot_ref), "sentinel in the snapshot ref"


def test_sentinel_absent_from_the_sandbox_payload_and_execution_logs(
    sentinel_family, local_request, sandbox_only
) -> None:
    """A real local_process run: nothing sealed enters the sandbox or its logs."""
    request = local_request()
    result = asyncio.run(LocalProcessAdapter().execute(request))
    assert result.failure is None, f"fixture run failed: {result.failure}"
    assert result.captures, "no captures; the execution arm is vacuous"

    _, written = sandbox_only()
    assert written, "the sandbox was provisioned empty; the arm is vacuous"
    for name, data in written.items():
        assert SENTINEL not in data.decode("utf-8", errors="replace"), f"sentinel provisioned into {name}"

    logged = b""
    for capture in result.captures:
        if capture.log_ref:
            logged += base64.b64decode(capture.log_ref.split(",", 1)[1])
        assert SENTINEL not in capture.body.decode("utf-8", errors="replace"), "sentinel in a captured body"
    assert logged, "the fixture emitted no log bytes; the log arm is vacuous"
    assert SENTINEL not in logged.decode("utf-8", errors="replace"), "sentinel in the execution log"


def test_sealed_sentinel_absent_from_real_assist_prompt_and_reply(tmp_path, sentinel_family) -> None:
    """A scored sealed expectation cannot reach the outbound assist request."""
    assert sentinel_family["cases"]
    assert serialized_contains({"messages": [{"content": SENTINEL}]}, SENTINEL), (
        "the prompt scanner must detect the needle in a serialized provider body"
    )
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={
            "model": "recorded-test-model", "choices": [{"message": {"content": "Check the public test."}}],
            "usage": {"prompt_tokens": 30, "completion_tokens": 6},
        })

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        gateway = LiveAssistGateway("LOCAL_TEST_TOKEN", http=http)
        with TestClient(create_app(str(tmp_path / "assist-sentinel.db"), assist_gateway=gateway)) as client:
            shift = client.post("/api/engagements/bookshop/shifts").json()
            shift_id = shift["id"]
            before = client.post(f"/api/shifts/{shift_id}/assist", json={
                "investigation_id": None, "role": "HINT", "client_request_id": "before-entry",
            })
            assert before.status_code == 409
            run = client.post(f"/api/shifts/{shift_id}/runs").json()
            checks = client.get(f"/api/runs/{run['id']}/checks").json()
            assert checks and all(row["expected_ref"].startswith("sealed:") for row in checks)
            sentinel_refs = {expected_ref_for(case) for case in sentinel_family["cases"]}
            assert any(row["expected_ref"] in sentinel_refs for row in checks), (
                "the executed run did not assess a sentinel-bearing sealed case"
            )
            investigation = client.post(f"/api/shifts/{shift_id}/investigations", json={
                "source_run_id": run["id"], "source_request_ordinal": 1,
                "cause": "The price router omitted collection.",
                "falsifier": "A nonprice request still omits collection.",
                "public_test": "Check the collection task in the public request.",
                "client_request_id": "assist-sentinel-investigation",
            })
            assert investigation.status_code == 201, investigation.text
            helped = client.post(f"/api/shifts/{shift_id}/assist", json={
                "investigation_id": investigation.json()["id"], "role": "HINT",
                "client_request_id": "assist-sentinel-call",
            })
            assert helped.status_code == 200, helped.text
            station = client.get(f"/api/shifts/{shift_id}/investigations")
            assert station.status_code == 200, station.text

    assert len(requests) == 1, "the provider request was never constructed"
    outbound = json.loads(requests[0].content)
    assert outbound["messages"][1]["content"].startswith("Role: HINT")
    for label, surface in (("provider prompt", outbound), ("help response", helped.text),
                           ("station view", station.text), ("pre-entry error", before.text)):
        assert not serialized_contains(surface, SENTINEL), f"sealed sentinel leaked into {label}"
