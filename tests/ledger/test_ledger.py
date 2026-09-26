"""Slice 5 ledger hardening: reducer purity/replay, chain break, corrections,
idempotent finalization, interrupted-finalization rollback and projection
equality (Gate 3 S6 tests 4-10 partial), plus the test 23 ledger-reconstruction
clause and the test 43 ledger-resolution-after-re-version clause.

Clause-level honesty: test 9's reservation-retention clause completes at Slice 7
and its restart-marks-FAILED / capture-retention clauses complete at Slice 8 with
``reconcile_interrupted`` (see ``test_restart_reconciles_nonterminal_runs_keeping_captures_and_draws``
and ``test_restart_keeps_a_committed_finalized_run``); test 9's fault injection
runs from the CAPTURED state only. Test 10's inheritance-seeds-match clause
completes at Slice 8 in ``tests/orchestrator/test_close_inheritance.py``.
"""

import base64
import builtins
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain.models import (
    CheckResult,
    ContractParams,
    ExecutorFailure,
    LedgerEventType,
    ReasonCode,
    RunOutput,
    RunState,
)
from shiftwork.ledger import chain, reducer
from shiftwork.store import db, repo

REPO_ROOT = Path(__file__).resolve().parents[2]

CONTRACT_FIXTURE = config.FIXTURE_DIR / "artifacts" / "bookshop" / "contract_stale_family.json"


def _contract() -> ContractParams:
    return ContractParams.model_validate_json(CONTRACT_FIXTURE.read_bytes())


def _mission() -> reducer.MissionFixtures:
    return reducer.load_mission(config.BOOKSHOP_MISSION)


def _output(ordinal: int = 1, body: bytes = b'{"action":"answer","claims":[]}') -> RunOutput:
    return RunOutput(
        id=f"run-0001-out-{ordinal}",
        run_id="run-0001",
        request_ordinal=ordinal,
        request_text=f"question {ordinal}",
        http_status=200,
        body=body,
        elapsed_ms=1,
    )


def _check(check_id: str, reason: ReasonCode) -> CheckResult:
    return CheckResult(
        id=check_id,
        run_id="run-0001",
        check_id=f"chk-{check_id}",
        verdict="fail",
        observed_ref="run-0001-out-1",
        expected_ref="sealed:" + "0" * 64,
        reason_code=reason,
    )


def _results() -> list[CheckResult]:
    return [
        _check("cr-0001", ReasonCode.STALE_BEYOND_RULE),
        _check("cr-0002", ReasonCode.INVENTED_FACT),
        _check("cr-0003", ReasonCode.MISSING_EVIDENCE),
    ]


def _invented_output(run_id: str) -> RunOutput:
    """One captured answer whose stock claim contradicts the runtime snapshot.

    Finalization evaluates against the snapshot the run consumed (Slice 7), which
    under the shipped binding is the fuller bookshop snapshot; this claim is
    contradicted by the cited record and scores INVENTED_FACT, which the mission
    transitions map to INCIDENT_OPENED.
    """
    body = json.dumps(
        {
            "action": "answer",
            "claims": [{"kind": "stock", "value": "out_of_stock"}],
            "evidence_refs": ["catalog:9780441013593"],
            "record_age_ms": 5400000,
        }
    ).encode("utf-8")
    return RunOutput(
        id=f"{run_id}-out-1",
        run_id=run_id,
        request_ordinal=1,
        request_text="Is Dune hardback in stock?",
        http_status=200,
        body=body,
        elapsed_ms=1,
        log_ref=f"{run_id}-out-1.log",
    )


def _seed_run_with_outputs(conn, tmp_path) -> str:
    """Open a shift, freeze, start a run, then attach one captured output as CAPTURED."""
    shift = orchestrator.open_next_shift(conn)
    orchestrator.freeze_version(conn, shift.id, _contract())
    run = orchestrator.start_run(conn, shift.id)
    repo.insert_output(conn, _invented_output(run.id))
    repo.update_run(conn, run.id, RunState.CAPTURED)
    conn.commit()
    return run.id


# --- test 4: reducer replay equality -------------------------------------------------


def test_reducer_replay_equality():
    mission = _mission()
    outputs = [_output()]
    results = _results()
    contract = _contract()

    first = reducer.reduce(mission, outputs, results, contract)
    second = reducer.reduce(mission, outputs, results, contract)
    assert first == second
    serialized = [draft.model_dump_json() for draft in first]
    assert serialized == [draft.model_dump_json() for draft in second]
    assert len(first) == 3

    script = (
        "import json,sys;"
        f"sys.path.insert(0, {str(REPO_ROOT)!r});"
        "from shiftwork import config;"
        "from shiftwork.ledger import reducer;"
        "from shiftwork.domain.models import CheckResult, ReasonCode;"
        "import importlib;"
        "mod = importlib.import_module('tests.ledger.test_ledger');"
        "print(json.dumps([d.model_dump_json() for d in reducer.reduce("
        "mod._mission(), [mod._output()], mod._results(), mod._contract())]))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=True,
    )
    assert json.loads(proc.stdout.strip()) == serialized


# --- test 5: reducer purity / no I/O -------------------------------------------------


def _closure_sources() -> list[Path]:
    seen: dict[str, Path] = {}
    pending = [REPO_ROOT / "shiftwork" / "ledger" / "reducer.py"]
    while pending:
        path = pending.pop()
        key = str(path)
        if key in seen or not path.exists():
            continue
        seen[key] = path
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("from shiftwork") or line.startswith("import shiftwork"):
                target = line.split()[1].split(".")[1] if line.startswith("from") else "shiftwork"
                candidate = REPO_ROOT / "shiftwork" / (target.replace(".", "/") + ".py")
                pending.append(candidate)
    return list(seen.values())


def test_reducer_is_pure_no_io(monkeypatch):
    forbidden = ("socket", "urllib", "requests", "httpx", "subprocess", "http.client")
    sources = _closure_sources()
    assert REPO_ROOT / "shiftwork" / "ledger" / "reducer.py" in sources
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert f"import {token}" not in text, path

    def _boom(*_args, **_kwargs):
        raise AssertionError("reducer touched the network")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
    monkeypatch.setattr(socket, "getaddrinfo", _boom)

    real_open = builtins.open

    def _no_write(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            raise AssertionError(f"reducer attempted a file write: {file}")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _no_write)
    monkeypatch.setattr(Path, "write_text", lambda *a, **k: _boom())
    monkeypatch.setattr(Path, "write_bytes", lambda *a, **k: _boom())

    drafts = reducer.reduce(_mission(), [_output()], _results(), _contract())
    assert len(drafts) == 3


# --- test 6: chain break detection ---------------------------------------------------


def test_chain_break_detection():
    drafts = reducer.reduce(_mission(), [_output()], _results(), _contract())
    events = chain.append(drafts, prev_hash=config.GENESIS_HASH, start_seq=1)
    assert chain.verify_chain(events) is chain.ChainStatus.VALID

    tampered_payload = events[0].model_copy(update={"payload": {**events[0].payload, "weight": 99}})
    assert chain.verify_chain([tampered_payload, *events[1:]]) is chain.ChainStatus.BROKEN

    tampered_hash = events[0].model_copy(update={"hash": "f" * 64})
    assert chain.verify_chain([tampered_hash, *events[1:]]) is chain.ChainStatus.BROKEN

    tampered_prev = events[1].model_copy(update={"prev_hash": "f" * 64})
    assert chain.verify_chain([events[0], tampered_prev, *events[2:]]) is chain.ChainStatus.BROKEN

    tampered_seq = events[1].model_copy(update={"seq": 5})
    assert chain.verify_chain([events[0], tampered_seq, *events[2:]]) is chain.ChainStatus.BROKEN

    reordered = [events[1], events[0], events[2]]
    assert chain.verify_chain(reordered) is chain.ChainStatus.BROKEN

    # The tampered prev_hash above is caught by hash recomputation (the digest
    # covers prev_hash). This splice is the linkage-only case: a forged event
    # whose own hash is self-consistent over its bogus prev_hash, so ONLY the
    # prev-hash linkage check in verify_chain can catch it.
    forged = chain.seal_draft(drafts[0], seq=2, prev_hash="f" * 64)
    assert forged.hash == chain.event_hash(
        seq=forged.seq,
        prev_hash=forged.prev_hash,
        event_type=forged.event_type.value,
        cause_refs=forged.cause_refs,
        payload=forged.payload,
        synthetic=forged.synthetic,
    )
    assert forged.payload != events[1].payload
    assert chain.verify_chain([events[0], forged, *events[2:]]) is chain.ChainStatus.BROKEN

    assert chain.verify_chain(events[:2]) is chain.ChainStatus.VALID


# --- test 7: corrections append referencing events, never edit -----------------------


def test_correction_events_only(tmp_path):
    db_file = tmp_path / "corr.db"
    conn = db.connect(db_file)
    try:
        db.ensure_schema(conn)
        repo.seed_engagement(conn, config.BOOKSHOP_SLUG, "bookshop", "Shop")
        drafts = reducer.reduce(_mission(), [_output()], _results(), _contract())
        original = chain.append(drafts, prev_hash=config.GENESIS_HASH, start_seq=1)
        for event in original:
            repo.insert_ledger_event(conn, config.BOOKSHOP_SLUG, event)
        conn.commit()
        before = conn.execute(
            "SELECT seq, event_type, cause_refs_json, payload_json, prev_hash, hash "
            "FROM ledger_events ORDER BY seq"
        ).fetchall()

        from shiftwork.domain.models import LedgerEventDraft, LedgerEventType

        correction_draft = LedgerEventDraft(
            event_type=LedgerEventType.BACKLOG_RECORDED,
            cause_refs=(original[0].hash,),
            payload={"consequence": "correction", "weight": 1, "catalog_version": 2},
        )
        appended = chain.append(
            [correction_draft],
            prev_hash=original[-1].hash,
            start_seq=original[-1].seq + 1,
        )
        for event in appended:
            repo.insert_ledger_event(conn, config.BOOKSHOP_SLUG, event)
        conn.commit()

        after = conn.execute(
            "SELECT seq, event_type, cause_refs_json, payload_json, prev_hash, hash "
            "FROM ledger_events ORDER BY seq"
        ).fetchall()
        assert after[: len(before)] == before
        assert len(after) == len(before) + 1
        assert original[0].hash in json.loads(after[-1][2])
        assert not hasattr(repo, "update_ledger_event")
        assert not hasattr(repo, "delete_ledger_event")
    finally:
        conn.close()


# --- tests 8/9/10 + 23/43 over a real finalized run ------------------------------------


def _seeded_conn(db_file: Path):
    """Let create_app seed schema + engagement_config, then open a direct conn."""
    with TestClient(create_app(str(db_file))):
        pass
    return db.connect(db_file)


@pytest.fixture()
def finalized(tmp_path):
    db_file = tmp_path / "finalize.db"
    conn = _seeded_conn(db_file)
    try:
        run_id = _seed_run_with_outputs(conn, tmp_path)
        run = orchestrator.finalize_run(conn, run_id)
        yield {"db_file": db_file, "conn": conn, "run_id": run_id, "run": run}
    finally:
        conn.close()


def test_finalization_idempotent(finalized):
    conn = finalized["conn"]
    run_id = finalized["run_id"]
    assert finalized["run"].state is RunState.FINALIZED

    events_before = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
    incidents_before = repo.list_incidents(conn, config.BOOKSHOP_SLUG)
    checks_before = repo.list_check_results(conn, run_id)
    assert events_before, "the failing transcript must reduce to real events"
    assert incidents_before, "INVENTED_FACT/MISSING_EVIDENCE must open incidents"

    again = orchestrator.finalize_run(conn, run_id)
    assert again.state is RunState.FINALIZED
    assert repo.list_ledger_events(conn, config.BOOKSHOP_SLUG) == events_before
    assert repo.list_incidents(conn, config.BOOKSHOP_SLUG) == incidents_before
    assert repo.list_check_results(conn, run_id) == checks_before


def test_interrupted_finalization_writes_no_events(tmp_path):
    db_file = tmp_path / "interrupt.db"
    conn = _seeded_conn(db_file)
    try:
        run_id = _seed_run_with_outputs(conn, tmp_path)

        for victim in (
            "insert_check_result",
            "insert_ledger_event",
            "insert_incident",
        ):
            original = getattr(repo, victim)

            def _fail(*args, __original=original, **kwargs):
                raise RuntimeError("injected commit-boundary fault")

            setattr(repo, victim, _fail)
            try:
                with pytest.raises(RuntimeError):
                    orchestrator.finalize_run(conn, run_id)
            finally:
                setattr(repo, victim, original)

            assert repo.list_check_results(conn, run_id) == []
            assert repo.list_ledger_events(conn, config.BOOKSHOP_SLUG) == []
            assert repo.list_incidents(conn, config.BOOKSHOP_SLUG) == []
            assert repo.get_run(conn, run_id).state is RunState.FAILED
            repo.update_run(conn, run_id, RunState.CAPTURED)
            conn.commit()

        recovered = orchestrator.finalize_run(conn, run_id)
        assert recovered.state is RunState.FINALIZED
        events = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
        assert chain.verify_chain(events) is chain.ChainStatus.VALID
        assert events[0].prev_hash == config.GENESIS_HASH

        reopened = db.connect(db_file)
        try:
            assert repo.get_run(reopened, run_id).state is RunState.FINALIZED
            assert len(repo.list_ledger_events(reopened, config.BOOKSHOP_SLUG)) == len(events)
        finally:
            reopened.close()
    finally:
        conn.close()


def test_restart_reconciles_nonterminal_runs_keeping_captures_and_draws(tmp_path):
    # Test 9's restart-marks-FAILED and capture-retention clauses (Slice 8):
    # a restart reconciles QUEUED, RUNNING and CAPTURED runs to FAILED while a
    # partial capture's bytes and every rotation draw stay intact, and no checks
    # or events are written. A committed FINALIZED run is untouched.
    db_file = tmp_path / "reconcile.db"
    conn = _seeded_conn(db_file)
    try:
        shift = orchestrator.open_next_shift(conn)
        orchestrator.freeze_version(conn, shift.id, _contract())
        queued = orchestrator.start_run(conn, shift.id)
        running = orchestrator.start_run(conn, shift.id)
        captured = orchestrator.start_run(conn, shift.id)
        repo.update_run(conn, running.id, RunState.RUNNING)
        repo.insert_output(conn, _invented_output(running.id))
        repo.update_run(conn, captured.id, RunState.CAPTURED)
        repo.insert_output(conn, _invented_output(captured.id))
        conn.commit()
        outputs_before = {
            run.id: [
                (row.id, row.request_ordinal, bytes(row.body), row.request_text, row.http_status, row.elapsed_ms, row.log_ref, row.transport_error)
                for row in repo.list_outputs(conn, run.id)
            ]
            for run in (running, captured)
        }
        draws_before = {
            run.id: [
                (draw.id, draw.family, draw.variant_ref, draw.run_id, draw.cycle, draw.state)
                for draw in repo.list_rotation_draws_for_run(conn, run.id)
            ]
            for run in (queued, running, captured)
        }
        assert outputs_before[running.id] and draws_before[queued.id]

        reconciled = orchestrator.reconcile_interrupted(conn)
        assert set(reconciled) == {queued.id, running.id, captured.id}
        for run in (queued, running, captured):
            stored = repo.get_run(conn, run.id)
            assert stored.state is RunState.FAILED
            assert stored.failure_kind is ExecutorFailure.INTERNAL
            assert repo.list_check_results(conn, run.id) == []
            assert [
                (draw.id, draw.family, draw.variant_ref, draw.run_id, draw.cycle, draw.state)
                for draw in repo.list_rotation_draws_for_run(conn, run.id)
            ] == draws_before[run.id], "a reconciliation changed the run's rotation draws"
        assert repo.list_ledger_events(conn, config.BOOKSHOP_SLUG) == []
        for run in (running, captured):
            assert [
                (row.id, row.request_ordinal, bytes(row.body), row.request_text, row.http_status, row.elapsed_ms, row.log_ref, row.transport_error)
                for row in repo.list_outputs(conn, run.id)
            ] == outputs_before[run.id], "a partial capture did not survive the reconciliation"
        assert orchestrator.reconcile_interrupted(conn) == [], "reconciliation is not idempotent"
        # The close is no longer blocked by the failed runs.
        assert orchestrator.close_shift(conn, shift.id).state == "closed"
        close_events = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
        assert all(event.event_type is LedgerEventType.LIMIT_DECLARED for event in close_events)
    finally:
        conn.close()

    with TestClient(create_app(str(db_file))):
        pass  # the lifespan's reconciliation runs against the same database
    reopened = db.connect(db_file)
    try:
        for run in (queued, running, captured):
            assert repo.get_run(reopened, run.id).state is RunState.FAILED
        assert repo.list_ledger_events(reopened, config.BOOKSHOP_SLUG) == close_events
    finally:
        reopened.close()


def test_restart_keeps_a_committed_finalized_run(finalized):
    conn = finalized["conn"]
    run_id = finalized["run_id"]
    events_before = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
    checks_before = repo.list_check_results(conn, run_id)
    assert events_before and checks_before
    conn.close()

    with TestClient(create_app(str(finalized["db_file"]))):
        pass  # the lifespan's reconciliation must leave a committed run alone

    reopened = db.connect(finalized["db_file"])
    try:
        assert repo.get_run(reopened, run_id).state is RunState.FINALIZED
        assert repo.list_check_results(reopened, run_id) == checks_before
        assert repo.list_ledger_events(reopened, config.BOOKSHOP_SLUG) == events_before
    finally:
        reopened.close()


def test_projection_vs_replay_equivalence(finalized):
    conn = finalized["conn"]
    events = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
    replay_totals: dict[str, int] = {}
    for event in events:
        replay_totals[event.event_type.value] = replay_totals.get(event.event_type.value, 0) + 1

    snapshot = orchestrator.board_snapshot(conn, config.BOOKSHOP_SLUG)
    assert snapshot["ledger_totals"] == replay_totals
    assert snapshot["ledger_event_count"] == len(events)
    assert snapshot["chain_status"] == "VALID"
    assert snapshot["total_incidents"] == len(repo.list_incidents(conn, config.BOOKSHOP_SLUG))


def test_ledger_reconstructs_from_tables_on_fresh_connection(finalized):
    db_file = finalized["db_file"]
    finalized["conn"].close()
    conn = db.connect(db_file)
    try:
        events = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
        assert events
        assert chain.verify_chain(events) is chain.ChainStatus.VALID
        payload = orchestrator.ledger(conn, config.BOOKSHOP_SLUG)
        assert payload["chain_status"] == "VALID"
        assert len(payload["events"]) == len(events)
    finally:
        conn.close()


def test_old_ledger_entries_resolve_against_their_original_catalog_version(
    finalized, monkeypatch, tmp_path
):
    conn = finalized["conn"]
    events = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
    shipped = config.PIVOT_STARTER_CONTRACT_JSON["catalog_version"]
    assert all(event.payload["catalog_version"] == shipped for event in events)

    catalog_dir = tmp_path / "catalogs"
    catalog_dir.mkdir()
    recorded = json.loads(
        (config.CATALOG_DIR / f"bookshop_v{shipped}.json").read_text(encoding="utf-8")
    )
    (catalog_dir / f"bookshop_v{shipped}.json").write_text(json.dumps(recorded), encoding="utf-8")
    newer_record = json.loads(json.dumps(recorded))
    newer_record["version"] = shipped + 1
    for option in newer_record["options"]:
        if option["id"] == "USE_NEWEST_RECORD_WITH_AGE":
            option["learner_label"] = "REWRITTEN NEWER LABEL"
    (catalog_dir / f"bookshop_v{shipped + 1}.json").write_text(
        json.dumps(newer_record), encoding="utf-8"
    )
    monkeypatch.setattr(config, "CATALOG_DIR", catalog_dir)

    resolved = orchestrator._resolve_catalog(config.BOOKSHOP_SLUG, events[0])
    assert resolved["catalog_version"] == shipped
    assert "REWRITTEN" not in json.dumps(resolved["catalog_record"])


def test_broken_chain_aborts_ledger_and_board_reads(finalized):
    conn = finalized["conn"]
    conn.execute("UPDATE ledger_events SET payload_json = '{\"tampered\": true}' WHERE seq = 1")
    conn.commit()
    with pytest.raises(orchestrator.LifecycleError):
        orchestrator.ledger(conn, config.BOOKSHOP_SLUG)
    with pytest.raises(orchestrator.LifecycleError):
        orchestrator.board_snapshot(conn, config.BOOKSHOP_SLUG)


def test_broken_chain_returns_409_on_ledger_and_board_routes(finalized):
    conn = finalized["conn"]
    conn.execute("UPDATE ledger_events SET payload_json = '{\"tampered\": true}' WHERE seq = 1")
    conn.commit()
    with TestClient(create_app(str(finalized["db_file"]))) as client:
        ledger_response = client.get("/api/engagements/bookshop/ledger")
        assert ledger_response.status_code == 409
        assert ledger_response.json() == {
            "kind": "conflict",
            "detail": "ledger chain is BROKEN; refusing unverified events",
        }
        board_response = client.get("/api/engagements/bookshop/board")
        assert board_response.status_code == 409
        assert board_response.json() == {
            "kind": "conflict",
            "detail": "ledger chain is BROKEN; refusing board counters",
        }


def test_ledger_view_resolves_derivation_and_catalog_links(finalized):
    db_file = finalized["db_file"]
    with TestClient(create_app(str(db_file))) as client:
        response = client.get("/api/engagements/bookshop/ledger")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["chain_status"] == "VALID"
        event = payload["events"][0]
        derivation = event["derivation"]
        assert derivation is not None
        assert derivation["run_id"] == finalized["run_id"]
        assert base64.b64decode(derivation["output_body_base64"])
        assert derivation["verdict"] == "fail"
        assert event["catalog"]["catalog_version"] == config.PIVOT_STARTER_CONTRACT_JSON["catalog_version"]
        assert event["catalog"]["catalog_record"]["version"] == config.PIVOT_STARTER_CONTRACT_JSON["catalog_version"]

        outputs = client.get(f"/api/runs/{finalized['run_id']}/outputs").json()
        assert any(
            item["customer_answer"] and item["customer_answer"]["display_text"]
            for item in outputs
        )
