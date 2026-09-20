import asyncio
import base64
import importlib
import importlib.util
import itertools
import json
import sqlite3
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from conformance import CASES, FIXTURE_LOG, STOCK_BODY
from shiftwork import config
from shiftwork.domain import canonical, contract_catalog
from shiftwork.domain.models import ContractParams, ExecutorFailure, RunOutput


@pytest.fixture()
def executor():
    for name in ("base", "local_process"):
        assert importlib.util.find_spec(f"shiftwork.executor.{name}") is not None, f"missing executor module: {name}"
    return SimpleNamespace(
        base=importlib.import_module("shiftwork.executor.base"),
        local=importlib.import_module("shiftwork.executor.local_process"),
        recorded=importlib.import_module("shiftwork.executor.recorded"),
    )


def request_for(executor, case_name="happy_path", deadline_s=5):
    root = config.FIXTURE_DIR / "artifacts" / "bookshop"
    files = {
        "service.py": (root / "service.py").read_bytes(),
        "learner_service.py": (config.PACKAGE_DIR / "templates" / "artifact" / "service.py").read_bytes(),
        "fixture.json": (root / f"{case_name}.json").read_bytes(),
    }
    batch = config.FIXTURE_DIR / "requests" / "bookshop.jsonl"
    return executor.base.RunRequest(
        artifact_snapshot=executor.base.ArtifactSnapshotRef(
            files=files, manifest_hash=config.TRUSTED_LOCAL_FIXTURES[case_name][0],
        ),
        request_batch=executor.base.BatchRef(
            path_ref="bookshop.jsonl",
            content_hash=canonical.content_hash(base64.b64encode(batch.read_bytes()).decode("ascii")),
        ),
        shop_snapshot_ref=str(config.BOOKSHOP_SNAPSHOT),
        harness_ref="stdlib-loopback-v1",
        image_ref="local-python-stdlib",
        deadline_s=deadline_s,
        inference_grant=None,
    )


def execute(adapter, request):
    return asyncio.run(adapter.execute(request))


def log_bytes(result):
    refs = {capture.log_ref for capture in result.captures if capture.log_ref is not None}
    return b"".join(base64.b64decode(ref.removeprefix("data:application/octet-stream;base64,"), validate=True) for ref in sorted(refs))


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_conformance_suite_recorded_local(executor, monkeypatch, capsys, case):
    request = request_for(executor, case.name, case.deadline_s)
    ticks = itertools.count(0, case.elapsed_ms * 1_000_000)
    monkeypatch.setattr(executor.local.time, "perf_counter_ns", lambda: next(ticks))
    local = execute(executor.local.LocalProcessAdapter(), request)
    recorded = execute(executor.recorded.RecordedAdapter(config.FIXTURE_DIR / "runs" / f"{case.name}.json"), request)

    assert local.failure is recorded.failure is case.failure
    assert tuple(c.http_status for c in local.captures) == case.statuses
    assert tuple(c.body for c in local.captures) == case.bodies
    assert tuple(c.transport_error for c in local.captures) == case.errors
    assert tuple(c.request_ordinal for c in local.captures) == tuple(range(1, len(case.bodies) + 1))
    assert all(c.elapsed_ms == case.elapsed_ms for c in local.captures)
    assert local.executor_ref is recorded.executor_ref is None
    assert log_bytes(local) == log_bytes(recorded) == FIXTURE_LOG
    normalized = executor.base.normalize_captures(local.captures, request.deadline_s)
    replay = executor.base.normalize_captures(recorded.captures, request.deadline_s)
    assert normalized == replay
    assert len(normalized) == len(case.bodies) > 0
    assert all(isinstance(c, RunOutput) and type(c.body) is bytes for c in normalized)
    assert tuple(c.body for c in normalized) == case.bodies
    with capsys.disabled():
        print(f"{case.name}: captures={len(normalized)} bytes/status/ordinal/time/logs=identical failure={case.failure or 'NONE'} (injected capture clock; real sockets/deadline)")


@pytest.mark.skip(reason="Test 29: tokenfactory conformance requires the real adapter and authorized sandbox access in Slice 14")
def test_conformance_suite_tokenfactory():
    pass


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_adapters_emit_raw_bytes_only(executor, monkeypatch, case):
    request = request_for(executor, case.name)
    def no_normalization(*args, **kwargs):
        raise AssertionError("adapters must not produce durable RunOutput objects")
    monkeypatch.setattr(executor.base, "normalize_captures", no_normalization)
    for adapter in (
        executor.local.LocalProcessAdapter(),
        executor.recorded.RecordedAdapter(config.FIXTURE_DIR / "runs" / f"{case.name}.json"),
    ):
        result = execute(adapter, request)
        assert result.captures
        assert all(type(c) is executor.base.RawCapture and type(c.body) is bytes for c in result.captures)
        assert tuple(c.body for c in result.captures) == case.bodies


@pytest.mark.parametrize("body", [{"action": "answer"}, [1], "parsed text", bytearray(b"x")])
def test_raw_capture_rejects_non_bytes(executor, body):
    with pytest.raises(ValidationError):
        executor.base.RawCapture(request_ordinal=1, http_status=200, body=body, elapsed_ms=1, transport_error=None, log_ref=None)


def test_normalization_preserves_bytes_timing_logs_and_orders(executor):
    raw = tuple(executor.base.RawCapture(
        request_ordinal=ordinal, http_status=200, body=body, elapsed_ms=55,
        transport_error=error, log_ref="data:application/octet-stream;base64,bG9n",
    ) for ordinal, body, error in ((2, b"\xff", ExecutorFailure.CAPTURE_NON_UTF8), (1, b'{"x":', ExecutorFailure.CAPTURE_TRUNCATED)))
    normalized = executor.base.normalize_captures(iter(raw), 2)
    assert tuple(c.request_ordinal for c in normalized) == (1, 2)
    for output, capture in zip(normalized, reversed(raw)):
        for field in ("http_status", "body", "elapsed_ms", "transport_error", "log_ref"):
            assert getattr(output, field) == getattr(capture, field)
    with pytest.raises(ValueError, match="ordinal"):
        executor.base.normalize_captures((raw[0], raw[0]), 2)


@pytest.mark.parametrize("change", ["unknown_hash", "modified_bytes", "extra_file", "path_escape"])
def test_local_process_rejects_untrusted_artifacts(executor, monkeypatch, capsys, change):
    request = request_for(executor)
    files = dict(request.artifact_snapshot.files)
    manifest = request.artifact_snapshot.manifest_hash
    if change == "unknown_hash":
        manifest = "0" * 64
    elif change == "modified_bytes":
        files["service.py"] += b"\nprint('modified')\n"
    elif change == "extra_file":
        files["sitecustomize.py"] = b"raise AssertionError('must never execute')"
    else:
        files["../outside.py"] = files.pop("service.py")
    request = request.model_copy(update={"artifact_snapshot": executor.base.ArtifactSnapshotRef(files=files, manifest_hash=manifest)})
    starts = []
    async def forbidden_start(*args, **kwargs):
        starts.append(args)
        raise AssertionError("untrusted artifact reached subprocess start")
    monkeypatch.setattr(executor.local.asyncio, "create_subprocess_exec", forbidden_start)
    result = execute(executor.local.LocalProcessAdapter(), request)
    assert result.failure is ExecutorFailure.PROVISION_FAILED
    assert result.captures == ()
    assert starts == []
    with capsys.disabled():
        print(f"trusted-guard {change}: PROVISION_FAILED; subprocess starts=0")


def test_local_process_types_a_provisioning_failure(executor, monkeypatch, capsys):
    """A fault on the writer path is a typed PROVISION_FAILED result, never a raised exception.

    The writer runs after the trust gate, so no pinned fixture reaches it with an
    invalid manifest today; the arm exists because the real-provisioning adapter
    (Slice 14) wires the writer differently, and an untyped OSError escaping
    ``execute()`` would break the adapter contract.
    """
    request = request_for(executor)

    def failing_provision(root, request, shop_snapshot):
        raise OSError("probe: provisioning fault after the trust gate")

    monkeypatch.setattr(executor.local, "provision_workspace", failing_provision)
    result = execute(executor.local.LocalProcessAdapter(), request)
    assert result.failure is ExecutorFailure.PROVISION_FAILED
    assert result.captures == ()
    with capsys.disabled():
        print("provisioning-fault: PROVISION_FAILED; captures=0")


def test_byte_addressed_fixtures_match_lf_checkout():
    roots = [config.ARTIFACT_TEMPLATE_DIR, config.SEALED_CASES_DIR] + [
        config.FIXTURE_DIR / name for name in ("artifacts/bookshop", "requests", "shop", "runs")
    ]
    files = [path for root in roots for path in root.iterdir() if path.is_file()]
    assert files
    assert [str(path) for path in files if b"\r\n" in path.read_bytes()] == []


def test_pinned_fixture_hashes_match_exact_bytes(executor):
    root = config.FIXTURE_DIR / "artifacts" / "bookshop"
    contract = ContractParams.model_validate_json((root / "contract.json").read_bytes())
    catalog = contract_catalog.load_catalog("bookshop", 1)
    assert set(config.TRUSTED_LOCAL_FIXTURES) == {c.name for c in CASES} | {"env_probe"}
    for name, (manifest_hash, files_hash) in config.TRUSTED_LOCAL_FIXTURES.items():
        request = request_for(executor, name)
        files = request.artifact_snapshot.files
        assert canonical.content_hash({path: base64.b64encode(body).decode("ascii") for path, body in files.items()}) == files_hash
        assert canonical.artifact_content_hash({path: body.decode("utf-8") for path, body in files.items()}, canonical.contract_params_json(contract), catalog.content_hash) == manifest_hash


@pytest.mark.parametrize("adapter_name", ["recorded", "local_process"])
def test_executor_env_exposes_no_controller_credentials(executor, monkeypatch, capsys, adapter_name):
    import os
    import subprocess
    names = ("NEBIUS_API_KEY", "CONTREE_SESSION", "TAVILY_API_KEY", "SHIFTWORK_DB_PATH", "SHIFTWORK_SEALED_STORE_ACCESS", "UNLISTED_ENV", "PYTHONPATH", "HTTP_PROXY")
    markers = {name: f"SLICE3_TEST_MARKER_{index}_NOT_A_CREDENTIAL" for index, name in enumerate(names)}
    for name, marker in markers.items():
        monkeypatch.setenv(name, marker)
    request = request_for(executor, "env_probe" if adapter_name == "local_process" else "happy_path")
    if adapter_name == "recorded":
        def forbidden(*args, **kwargs):
            raise AssertionError("recorded replay attempted execution or environment access")
        monkeypatch.setattr(subprocess, "Popen", forbidden)
        monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
        class NoEnvironment:
            __getattribute__ = forbidden
            __getitem__ = forbidden
            __iter__ = forbidden
            __contains__ = forbidden
        loop = asyncio.new_event_loop()
        try:
            with monkeypatch.context() as trap:
                trap.setattr(os, "environ", NoEnvironment())
                result = loop.run_until_complete(executor.recorded.RecordedAdapter(config.FIXTURE_DIR / "runs" / "happy_path.json").execute(request))
        finally:
            loop.close()
        assert result.failure is None and len(result.captures) == 2
    else:
        assert executor.local.CHILD_ENV_ALLOWLIST == ("SYSTEMROOT", "WINDIR")
        spawn_envs = []
        original = executor.local.asyncio.create_subprocess_exec
        async def observed_start(*args, **kwargs):
            spawn_envs.append(dict(kwargs["env"]))
            assert set(kwargs["env"]) <= set(executor.local.CHILD_ENV_ALLOWLIST)
            assert all(marker not in str(kwargs) for marker in markers.values())
            return await original(*args, **kwargs)
        monkeypatch.setattr(executor.local.asyncio, "create_subprocess_exec", observed_start)
        result = execute(executor.local.LocalProcessAdapter(), request)
        assert result.failure is None and len(result.captures) == 2
        assert len(spawn_envs) == 1
        logs = log_bytes(result)
        env_line = next(line for line in logs.splitlines() if line.startswith(b"child-env "))
        observed_env = json.loads(env_line.removeprefix(b"child-env "))
        assert observed_env == spawn_envs[0]
    captured = b"".join(c.body for c in result.captures) + log_bytes(result)
    assert all(marker.encode() not in captured for marker in markers.values())
    with capsys.disabled():
        print(f"credential-guard {adapter_name}: captures=2; injected markers absent from bodies/logs; " + ("no process or environment access" if adapter_name == "recorded" else "spawn env and child-reported env match SYSTEMROOT/WINDIR allowlist"))


def test_local_process_uses_literal_requests_and_snapshot(executor):
    request = request_for(executor, "env_probe")
    result = execute(executor.local.LocalProcessAdapter(), request)
    assert result.failure is None
    request_lines = (config.FIXTURE_DIR / "requests" / "bookshop.jsonl").read_bytes().splitlines(keepends=True)
    logged_lines = [line.removeprefix(b"request-bytes ") for line in log_bytes(result).splitlines() if line.startswith(b"request-bytes ")]
    assert len(logged_lines) == len(request_lines) == 2
    assert [base64.b64decode(line) for line in logged_lines] == request_lines
    assert result.captures[0].body == STOCK_BODY
    assert all(c.elapsed_ms is not None and 0 <= c.elapsed_ms <= result.wall_ms for c in result.captures)


@pytest.mark.parametrize("adapter_name", ["recorded", "local_process"])
def test_bad_batch_hash_refused_before_execution(executor, monkeypatch, adapter_name):
    request = request_for(executor)
    request = request.model_copy(update={"request_batch": request.request_batch.model_copy(update={"content_hash": "0" * 64})})
    async def forbidden_start(*args, **kwargs):
        raise AssertionError("invalid batch reached subprocess start")
    monkeypatch.setattr(executor.local.asyncio, "create_subprocess_exec", forbidden_start)
    adapter = executor.local.LocalProcessAdapter() if adapter_name == "local_process" else executor.recorded.RecordedAdapter(config.FIXTURE_DIR / "runs" / "happy_path.json")
    result = execute(adapter, request)
    assert result.failure is ExecutorFailure.PROVISION_FAILED
    assert result.captures == ()


def test_local_process_reaps_child_after_timeout_and_cancellation(executor, monkeypatch):
    children = []
    original = executor.local.asyncio.create_subprocess_exec
    async def observed_start(*args, **kwargs):
        child = await original(*args, **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(executor.local.asyncio, "create_subprocess_exec", observed_start)
    result = execute(executor.local.LocalProcessAdapter(), request_for(executor, "timeout", deadline_s=1))
    assert result.failure is ExecutorFailure.REQUEST_TIMEOUT
    assert children and children[-1].returncode is not None
    async def cancel_run():
        task = asyncio.create_task(executor.local.LocalProcessAdapter().execute(request_for(executor, "timeout", deadline_s=5)))
        while len(children) < 2:
            await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(cancel_run())
    assert len(children) == 2 and children[-1].returncode is not None


def test_controller_normalizes_once_and_retains_failed_capture(executor, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from shiftwork import orchestrator
    from shiftwork.app import create_app
    from shiftwork.store import db, repo

    requests = []
    normalized = []
    capture = executor.base.RawCapture(
        request_ordinal=1, http_status=200, body=b"partial\xff", elapsed_ms=7,
        transport_error=ExecutorFailure.CAPTURE_NON_UTF8,
        log_ref="data:application/octet-stream;base64,bG9n",
    )
    class FailedAdapter:
        name = "recorded"
        async def execute(self, request):
            assert isinstance(request, executor.base.RunRequest)
            requests.append(request)
            return executor.base.RunResult(captures=(capture,), executor_ref=None, failure=ExecutorFailure.CAPTURE_NON_UTF8, wall_ms=7)
    original = executor.base.normalize_captures
    def observed(raw, deadline_s):
        normalized.append(tuple(raw))
        return original(normalized[-1], deadline_s)
    monkeypatch.setattr(orchestrator, "_adapter", lambda: FailedAdapter())
    monkeypatch.setattr(executor.base, "normalize_captures", observed)
    path = tmp_path / "executor.db"
    contract = json.loads((config.FIXTURE_DIR / "artifacts" / "bookshop" / "contract.json").read_bytes())
    with TestClient(create_app(str(path))) as client:
        shift = client.post("/api/engagements/bookshop/shifts").json()
        version = client.post(f"/api/shifts/{shift['id']}/artifact/versions", json={"contract": contract}).json()
        started = client.post(f"/api/shifts/{shift['id']}/runs")
        assert started.status_code == 202
        run_id = started.json()["id"]
        run = client.get(f"/api/runs/{run_id}").json()
        assert run["state"] == "FAILED"
        assert run["failure_kind"] == "CAPTURE_NON_UTF8"
        outputs = client.get(f"/api/runs/{run_id}/outputs").json()
        assert len(outputs) == 1
        assert base64.b64decode(outputs[0]["body_base64"]) == b"partial\xff"
        assert base64.b64decode(outputs[0]["log_base64"]) == b"log"
        assert outputs[0]["request_text"] == "Do you still have the hardback of Dune on the shelf?"
        assert client.get(f"/api/runs/{run_id}/checks").json() == []
        assert client.get("/api/engagements/bookshop/ledger").json()["events"] == []
    assert len(requests) == len(normalized) == 1
    assert requests[0].artifact_snapshot.manifest_hash == version["content_hash"]
    assert requests[0].artifact_snapshot.files["service.py"] == (config.ARTIFACT_TEMPLATE_DIR / "service.py").read_bytes()
    conn = db.connect(path)
    try:
        stored = repo.list_outputs(conn, run_id)
        assert len(stored) == 1 and stored[0].log_ref == capture.log_ref
        assert stored[0].body == capture.body
    finally:
        conn.close()


def _pre_rotation_schema(*, keep_log_ref: bool = False) -> str:
    """``schema.sql`` with the later additions stripped: the v2 or v3 shape.

    The default strips ``log_ref`` as well and yields the v2 shape;
    ``keep_log_ref`` yields the genuine v3 shape that shipped before rotation
    (log_ref present, rotation columns and table absent). Every strip is
    asserted, so this helper cannot silently stop producing an older schema and
    make the upgrade tests vacuous.
    """
    from shiftwork.store import db

    sql = db.SCHEMA_PATH.read_text(encoding="utf-8")
    fragments = [
        "    request_batch_ref TEXT NOT NULL,\n",
        "    shop_snapshot_ref TEXT NOT NULL,\n",
    ]
    if not keep_log_ref:
        fragments.append("    log_ref TEXT,\n")
    for fragment in fragments:
        assert fragment in sql, f"schema.sql no longer contains {fragment!r}"
        sql = sql.replace(fragment, "")
    marker = "CREATE TABLE IF NOT EXISTS rotation_draws ("
    start = sql.index(marker)
    sql = sql[:start] + sql[sql.index(");", start) + len(");\n") :]
    assert marker not in sql
    return sql


def _insert_legacy_run(conn) -> None:
    """One pre-rotation run row, so the v3 to v4 backfill is exercised."""
    conn.execute(
        "INSERT INTO shifts VALUES ('legacy-shift', 'retained', 1, 'open', "
        "'2026-09-18T00:00:00+00:00', NULL)"
    )
    conn.execute(
        "INSERT INTO artifact_versions VALUES ('legacy-ver', 'legacy-shift', NULL, 'hash', "
        "'inline:hash', '{}', '{}', 'catalog-hash', 'learner', '2026-09-18T00:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO runs (id, shift_id, artifact_version_id, attempt_number, state, adapter, started_at) "
        "VALUES ('legacy-run', 'legacy-shift', 'legacy-ver', 1, 'FINALIZED', 'recorded', "
        "'2026-09-18T00:00:00+00:00')"
    )


def test_existing_schema_two_gets_log_column_without_data_loss(executor, tmp_path):
    from shiftwork.store import db
    conn = db.connect(tmp_path / "schema-two.db")
    try:
        conn.executescript(_pre_rotation_schema())
        conn.execute("INSERT INTO engagements VALUES ('retained', 'bookshop', 'Retained row')")
        _insert_legacy_run(conn)
        conn.execute("PRAGMA user_version = 2")
        conn.commit()
        db.ensure_schema(conn)
        assert "log_ref" in {row["name"] for row in conn.execute("PRAGMA table_info(run_outputs)")}
        assert conn.execute("SELECT display_name FROM engagements WHERE slug = 'retained'").fetchone()[0] == "Retained row"
        # The v3 to v4 half of the same upgrade: columns added, legacy rows
        # backfilled with the refs the controller hardcoded before rotation.
        assert "request_batch_ref" in {row["name"] for row in conn.execute("PRAGMA table_info(runs)")}
        assert conn.execute("SELECT request_batch_ref, shop_snapshot_ref FROM runs WHERE id = 'legacy-run'").fetchone()[:] == ("thin.jsonl", "bookshop_snapshot.json")
        db.ensure_schema(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
    finally:
        conn.close()


def test_existing_schema_three_gets_rotation_columns_without_data_loss(tmp_path):
    from shiftwork.store import db
    conn = db.connect(tmp_path / "schema-three.db")
    try:
        conn.executescript(_pre_rotation_schema(keep_log_ref=True))
        conn.execute("INSERT INTO engagements VALUES ('retained', 'bookshop', 'Retained row')")
        _insert_legacy_run(conn)
        conn.execute("PRAGMA user_version = 3")
        conn.commit()
        # The fixture really is the v3 shape: log_ref present, rotation additions absent.
        assert "log_ref" in {row["name"] for row in conn.execute("PRAGMA table_info(run_outputs)")}
        assert "request_batch_ref" not in {row["name"] for row in conn.execute("PRAGMA table_info(runs)")}
        db.ensure_schema(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
        assert "request_batch_ref" in {row["name"] for row in conn.execute("PRAGMA table_info(runs)")}
        assert "log_ref" in {row["name"] for row in conn.execute("PRAGMA table_info(run_outputs)")}
        assert conn.execute("SELECT request_batch_ref, shop_snapshot_ref FROM runs WHERE id = 'legacy-run'").fetchone()[:] == ("thin.jsonl", "bookshop_snapshot.json")
        assert "rotation_draws" in {
            row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        assert conn.execute("SELECT display_name FROM engagements WHERE slug = 'retained'").fetchone()[0] == "Retained row"
        # Idempotent: bootstrapping an already-upgraded v3 database changes nothing.
        db.ensure_schema(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
    finally:
        conn.close()


@pytest.mark.parametrize("change", [
    "missing_status", "invalid_status", "invalid_log_base64", "contradictory_failure",
    "capture_after_failure", "non_utf8_label_on_utf8", "invalid_failure_value",
])
def test_recorded_rejects_inconsistent_transport_metadata(executor, tmp_path, change):
    transcript = json.loads((config.FIXTURE_DIR / "runs" / "happy_path.json").read_bytes())
    last = transcript["captures"][-1]
    if change == "missing_status":
        last["http_status"] = None
    elif change == "invalid_status":
        last["http_status"] = 600
    elif change == "invalid_log_base64":
        last["log_base64"] = "not base64!"
    elif change == "contradictory_failure":
        last["transport_error"] = "REQUEST_TIMEOUT"
        transcript["failure"] = "CAPTURE_NON_UTF8"
    elif change == "capture_after_failure":
        transcript["captures"][0]["transport_error"] = "REQUEST_TIMEOUT"
        transcript["failure"] = "REQUEST_TIMEOUT"
    elif change == "non_utf8_label_on_utf8":
        last["transport_error"] = "CAPTURE_NON_UTF8"
        transcript["failure"] = "CAPTURE_NON_UTF8"
    else:
        transcript["failure"] = False
    path = tmp_path / "invalid-transcript.json"
    path.write_text(json.dumps(transcript), encoding="utf-8")
    result = execute(executor.recorded.RecordedAdapter(path), request_for(executor))
    assert result.failure is ExecutorFailure.INTERNAL
    assert result.captures == ()


def test_recorded_derives_non_utf8_failure_without_losing_bytes(executor, tmp_path):
    transcript = json.loads((config.FIXTURE_DIR / "runs" / "happy_path.json").read_bytes())
    transcript["captures"][-1]["body_base64"] = base64.b64encode(b"partial\xff").decode("ascii")
    path = tmp_path / "non-utf8-transcript.json"
    path.write_text(json.dumps(transcript), encoding="utf-8")
    result = execute(executor.recorded.RecordedAdapter(path), request_for(executor))
    assert result.failure is ExecutorFailure.CAPTURE_NON_UTF8
    assert len(result.captures) == 2
    assert result.captures[0].body == STOCK_BODY
    assert result.captures[0].transport_error is None
    assert result.captures[1].body == b"partial\xff"
    assert result.captures[1].transport_error is ExecutorFailure.CAPTURE_NON_UTF8
    assert result.captures[1].http_status == 200
    assert result.captures[1].elapsed_ms == 55
    assert log_bytes(result) == FIXTURE_LOG


def test_recorded_preserves_termination_after_partial_response(executor, tmp_path):
    transcript = json.loads((config.FIXTURE_DIR / "runs" / "truncated_body.json").read_bytes())
    transcript["failure"] = "SANDBOX_TERMINATED"
    path = tmp_path / "terminated-transcript.json"
    path.write_text(json.dumps(transcript), encoding="utf-8")
    result = execute(executor.recorded.RecordedAdapter(path), request_for(executor))
    assert result.failure is ExecutorFailure.SANDBOX_TERMINATED
    assert len(result.captures) == 1
    assert result.captures[0].body == b'{"action":'
    assert result.captures[0].transport_error is ExecutorFailure.CAPTURE_TRUNCATED
    assert log_bytes(result) == FIXTURE_LOG


@pytest.mark.parametrize("change", ["missing_status", "unmarked_non_utf8"])
def test_recorded_failure_cannot_finalize_and_retains_valid_evidence(executor, monkeypatch, tmp_path, change):
    from fastapi.testclient import TestClient
    from shiftwork import orchestrator
    from shiftwork.app import create_app
    from shiftwork.store import db, repo

    transcript = json.loads(config.THIN_TRANSCRIPT.read_bytes())
    capture = transcript["captures"][0]
    capture["log_base64"] = base64.b64encode(b"log").decode("ascii")
    if change == "missing_status":
        capture["http_status"] = None
    else:
        capture["body_base64"] = base64.b64encode(b"partial\xff").decode("ascii")
    transcript_path = tmp_path / "transcript.json"
    transcript_path.write_text(json.dumps(transcript), encoding="utf-8")
    monkeypatch.setattr(orchestrator, "_adapter", lambda: executor.recorded.RecordedAdapter(transcript_path))
    path = tmp_path / "replay.db"
    contract = json.loads((config.FIXTURE_DIR / "artifacts" / "bookshop" / "contract.json").read_bytes())
    with TestClient(create_app(str(path))) as client:
        shift = client.post("/api/engagements/bookshop/shifts").json()
        frozen = client.post(f"/api/shifts/{shift['id']}/artifact/versions", json={"contract": contract})
        assert frozen.status_code == 201
        started = client.post(f"/api/shifts/{shift['id']}/runs")
        assert started.status_code == 202
        run_id = started.json()["id"]
        run = client.get(f"/api/runs/{run_id}").json()
        assert run["state"] == "FAILED"
        assert run["failure_kind"] == ("INTERNAL" if change == "missing_status" else "CAPTURE_NON_UTF8")
        assert client.get(f"/api/runs/{run_id}/checks").json() == []
        assert client.get("/api/engagements/bookshop/ledger").json()["events"] == []
        outputs = client.get(f"/api/runs/{run_id}/outputs").json()
        if change == "missing_status":
            assert outputs == []
        else:
            assert len(outputs) == 1
            assert base64.b64decode(outputs[0]["body_base64"]) == b"partial\xff"
            assert base64.b64decode(outputs[0]["log_base64"]) == b"log"
            assert outputs[0]["transport_error"] == "CAPTURE_NON_UTF8"
            assert outputs[0]["request_text"] == "Do you still have the hardback of Dune on the shelf?"
    conn = db.connect(path)
    try:
        stored = repo.list_outputs(conn, run_id)
        assert len(stored) == (0 if change == "missing_status" else 1)
        if stored:
            assert stored[0].body == b"partial\xff"
            assert stored[0].log_ref == "data:application/octet-stream;base64,bG9n"
    finally:
        conn.close()


def test_schema_two_upgrade_rolls_back_on_version_write_failure(tmp_path):
    from shiftwork.store import db

    path = tmp_path / "interrupted-upgrade.db"
    conn = db.connect(path)
    try:
        conn.executescript(_pre_rotation_schema())
        conn.execute("INSERT INTO engagements VALUES ('retained', 'bookshop', 'Retained row')")
        _insert_legacy_run(conn)
        conn.execute("PRAGMA user_version = 2")
        conn.commit()
        observed = []
        def deny_version_write(action, first, second, database, trigger):
            if action == sqlite3.SQLITE_PRAGMA and first == "user_version" and second is not None:
                observed.append(second)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        conn.set_authorizer(deny_version_write)
        with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
            db.ensure_schema(conn)
        assert observed == [str(db.SCHEMA_VERSION)]
        assert not conn.in_transaction
    finally:
        conn.close()
    conn = db.connect(path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 2
        assert "log_ref" not in {row["name"] for row in conn.execute("PRAGMA table_info(run_outputs)")}
        assert "request_batch_ref" not in {row["name"] for row in conn.execute("PRAGMA table_info(runs)")}
        # New tables come from the idempotent executescript, which commits before
        # the guarded transaction: an empty rotation_draws table survives the
        # rollback harmlessly, but the columns and the version marker do not.
        assert conn.execute("SELECT COUNT(*) FROM rotation_draws").fetchone()[0] == 0
        assert conn.execute("SELECT display_name FROM engagements WHERE slug = 'retained'").fetchone()[0] == "Retained row"
        db.ensure_schema(conn)
        db.ensure_schema(conn)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
        assert "log_ref" in {row["name"] for row in conn.execute("PRAGMA table_info(run_outputs)")}
        assert conn.execute("SELECT request_batch_ref, shop_snapshot_ref FROM runs WHERE id = 'legacy-run'").fetchone()[:] == ("thin.jsonl", "bookshop_snapshot.json")
        assert conn.execute("SELECT display_name FROM engagements WHERE slug = 'retained'").fetchone()[0] == "Retained row"
    finally:
        conn.close()
