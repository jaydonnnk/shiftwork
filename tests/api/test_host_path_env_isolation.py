"""Test 20 (program design S6.D): host paths and env values never reach the learner.

Scope note against test 50: test 50 (landed partial at Slice 3, ``tests/executor/``)
asserts on the SPAWN boundary - the ``env`` mapping handed to
``create_subprocess_exec`` and the pinned ``CHILD_ENV_ALLOWLIST``. This test asserts
one layer out, on the LEARNER-VISIBLE PROJECTIONS: the ``RunOutputView`` built from a
real local-adapter run, and every API response from a full lifecycle. A controller
that scrubs the child env correctly but then echoes a host path or an env value into a
response would pass test 50 and fail here.

The leak vector is real, not hypothetical: the ``env_probe`` trusted fixture prints
its entire child environment to stderr, and those bytes are captured into ``log_ref``
and projected as ``log_base64``. So the scan below runs against a log that genuinely
contains an environment dump.

The scanner itself is self-tested before it is trusted: a JSON-escaped path, a
forward-slash path and a path buried in a nested JSON string must each be detected,
because each form has silently defeated a naive ``needle in surface`` scan.

The only host-derived values that may legitimately appear are the two pinned
allowlist OS variables, which the child needs to start; that bound is asserted
explicitly rather than assumed.
"""

import asyncio
import base64
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from leakscan import decoded_surfaces, host_leaks
from shiftwork import config
from shiftwork.api.schemas import RunOutputView
from shiftwork.app import create_app
from shiftwork.executor import base as executor_base
from shiftwork.executor.local_process import CHILD_ENV_ALLOWLIST, LocalProcessAdapter

REPO_ROOT = config.PACKAGE_DIR.parent
DB_MARKER = "sw6-env-marker-db"

ENV_NAMES = (
    "NEBIUS_API_KEY",
    "CONTREE_SESSION",
    "TAVILY_API_KEY",
    "SHIFTWORK_DB_PATH",
    "SHIFTWORK_SEALED_STORE_ACCESS",
    "SHIFTWORK_LEARNER_INFERENCE_KEY",
    "UNLISTED_VARIABLE",
    "PYTHONPATH",
    "HTTP_PROXY",
)


@pytest.fixture()
def env_markers(monkeypatch):
    """Unique tokens injected into the controller environment for every watched name."""
    markers = {name: f"SW6ENVMARK{index}XQ9" for index, name in enumerate(ENV_NAMES)}
    for name, marker in markers.items():
        monkeypatch.setenv(name, marker)
    for name, marker in markers.items():
        assert os.environ[name] == marker, f"{name} was not injected"
    return markers


@pytest.fixture()
def marker_db(tmp_path):
    db_dir = tmp_path / DB_MARKER
    db_dir.mkdir()
    return db_dir / "shiftwork.db"


def _host_path_needles() -> dict[str, str]:
    return {
        "package path": str(config.PACKAGE_DIR),
        "repository path": str(REPO_ROOT),
        "interpreter path": sys.executable,
        "shop snapshot path": str(config.BOOKSHOP_SNAPSHOT),
        "sealed store path": str(config.SEALED_CASES_DIR),
        "fixture directory": str(config.FIXTURE_DIR),
        "sandbox workspace prefix": "shiftwork-fixture-",
        "database marker": DB_MARKER,
    }


def _scan(label: str, surfaces: list[str], needles: dict[str, str]) -> None:
    leaks = [(name, value) for surface in surfaces for name, value in host_leaks(surface, needles)]
    assert not leaks, f"{label} exposed host material: {leaks[:5]}"


def test_host_path_scan_detects_a_json_escaped_path() -> None:
    """Guards the scanner itself.

    A Windows absolute path is backslash-escaped inside a JSON response, so a naive
    ``needle in surface`` scan never matches and passes vacuously. This check fails
    if that escaping is ever unhandled again.
    """
    needle = str(config.BOOKSHOP_SNAPSHOT)
    assert "\\" in needle, "expected a Windows path; the escaping form would be untested"
    surface = json.dumps({"path": needle})
    assert needle not in surface, "precondition: the raw path must not match the escaped surface"
    assert host_leaks(surface, {"snapshot": needle}), "host_leaks missed a JSON-escaped host path"
    assert not host_leaks(json.dumps({"path": "unrelated"}), {"snapshot": needle})


def test_host_path_scan_detects_forward_slash_and_nested_json_forms() -> None:
    """Guards the other two escaping forms that silently defeated earlier scans.

    A forward-slash host path matches neither the raw nor the backslash needle, and
    a path inside a nested JSON string is escaped twice, so the needle must be
    normalized on both sides and the serialized surface must be decoded.
    """
    needle = str(config.BOOKSHOP_SNAPSHOT)
    forward = json.dumps({"debug_path": needle.replace("\\", "/")})
    assert host_leaks(forward, {"snapshot": needle}), "host_leaks missed a forward-slash host path"

    nested = json.dumps({"log": json.dumps({"path": needle})})
    assert not host_leaks(nested, {"snapshot": needle}), (
        "precondition: the raw nested form must not match; the decoded walk is what closes it"
    )
    surfaces = decoded_surfaces(nested)
    assert any(host_leaks(surface, {"snapshot": needle}) for surface in surfaces), (
        "host_leaks missed a host path inside a nested JSON string"
    )

    for name, value in _host_path_needles().items():
        assert host_leaks(json.dumps({"probe": value}), {name: value}) or value in json.dumps(
            {"probe": value}
        ), f"needle {name!r} cannot match a serialized surface; its absence proves nothing"


def test_local_adapter_projection_exposes_no_env_value_or_host_path(
    local_request, env_markers
) -> None:
    request = local_request("env_probe")
    result = asyncio.run(LocalProcessAdapter().execute(request))
    assert result.failure is None, f"env_probe fixture run failed: {result.failure}"
    assert result.captures, "no captures; the projection arm is vacuous"

    outputs = executor_base.normalize_captures(result.captures, request.deadline_s)
    views = [RunOutputView.of(output) for output in outputs]
    assert views, "no projections were built"

    surfaces: list[str] = []
    for view in views:
        surfaces.extend(decoded_surfaces(view.model_dump_json()))

    # Non-vacuity: the projected log really is an environment dump from the child.
    logged = "".join(
        base64.b64decode(view.log_base64).decode("utf-8", errors="replace")
        for view in views
        if view.log_base64
    )
    assert "child-env " in logged, "the env_probe fixture did not dump its environment"
    dumped = json.loads(logged.split("child-env ", 1)[1].splitlines()[0])
    assert set(dumped) <= set(CHILD_ENV_ALLOWLIST), (
        f"child environment exceeded the pinned allowlist: {sorted(set(dumped) - set(CHILD_ENV_ALLOWLIST))}"
    )

    _scan("RunOutputView", surfaces, _host_path_needles())
    for name, marker in env_markers.items():
        for surface in surfaces:
            assert marker not in surface, f"env value for {name} reached a learner-visible projection"


def test_api_responses_expose_no_env_value_or_host_path(env_markers, marker_db) -> None:
    # The shipped default (Slice 8) replays attempt 1 against the fuller snapshot,
    # which opens incidents natively; the incident surfaces below are scanned for
    # that real failure, not a redirected one.
    surfaces: list[tuple[str, str]] = []
    called: set[str] = set()

    contract = {
        "catalog_version": 1,
        "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
        "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
        "response_time_limit_ms": 3000,
        "declared_limits": ["NO_SAME_DAY_DELIVERY_PROMISE"],
    }

    with TestClient(create_app(str(marker_db))) as client:
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
        record("get", f"/api/shifts/{shift_id}/artifact")
        version = record(
            "post", f"/api/shifts/{shift_id}/artifact/versions", json={"contract": contract}
        )
        assert version.status_code == 201, version.text
        started = record("post", f"/api/shifts/{shift_id}/runs")
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

        record("post", f"/api/shifts/{shift_id}/close")

        # An error response is a learner-visible surface too: one 404, one 409
        # and one 422 after the finalized run, all scanned like the others.
        not_found = record("get", "/api/runs/run-does-not-exist")
        assert not_found.status_code == 404, not_found.text
        record("get", "/api/engagements/not-an-engagement/board")
        closed = record("post", f"/api/shifts/{shift_id}/runs")
        assert closed.status_code == 409, closed.text
        invalid = record("put", f"/api/shifts/{shift_id}/artifact", json={"files": 123})
        assert invalid.status_code == 422, invalid.text

    assert checks.json(), "no check results; the projection scan proved nothing"
    assert len(surfaces) >= len(called), f"{len(surfaces)} surfaces from {len(called)} calls"

    needles = _host_path_needles()
    for label, surface in surfaces:
        found = host_leaks(surface, needles)
        assert not found, f"{label} exposed host material: {found[:5]}"
        for name, marker in env_markers.items():
            assert marker not in surface, f"{label} exposed the env value for {name}"


def test_error_details_carry_no_host_path(env_markers, marker_db) -> None:
    """A 409/404 body is built from a typed error, not from an exception repr."""
    with TestClient(create_app(str(marker_db))) as client:
        shift = client.post("/api/engagements/bookshop/shifts")
        shift_id = shift.json()["id"]
        # A closed shift refuses a run with a typed conflict, even with a starter.
        closed = client.post(f"/api/shifts/{shift_id}/close")
        assert closed.status_code == 200, closed.text
        refused = client.post(f"/api/shifts/{shift_id}/runs")
        assert refused.status_code == 409, refused.text
        for surface in decoded_surfaces(refused.text):
            found = host_leaks(surface, _host_path_needles())
            assert not found, f"the error body exposed host material: {found}"
            for marker in env_markers.values():
                assert marker not in surface, "the error body exposed an env value"
        assert Path(str(marker_db)).name not in refused.text
