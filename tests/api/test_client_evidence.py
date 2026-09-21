"""Slice 9 output evidence: real API runs, exact bytes and public-only provenance."""

import base64
import json

import pytest
from fastapi.testclient import TestClient

from leakscan import decoded_surfaces, host_leaks
from shiftwork import config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain import canonical
from shiftwork.domain.models import RunOutput, RunState
from shiftwork.store import db, repo

STOCK = {
    "record_id": "catalog:9780441013593",
    "kind": "stock",
    "title": "Dune",
    "edition": "hardback",
    "value": "out_of_stock",
    "record_age_ms": 120000,
}
PRICE = {
    "record_id": "catalog:9780441013593:price",
    "kind": "price",
    "title": "Dune",
    "edition": "hardback",
    "value": 2345,
    "record_age_ms": 60000,
}
FUTURE = {
    "record_id": "catalog:9780525559474",
    "kind": "stock",
    "title": "UNEXECUTED_RECORD_TITLE_SENTINEL",
    "edition": "paperback",
    "value": "UNEXECUTED_RECORD_VALUE_SENTINEL",
    "record_age_ms": 300000,
}
SOURCE_NOTE = "SOURCE_DESCRIPTION_MUST_NOT_REACH_OUTPUT"
RECORD_NOTE = "NON_ALLOWLIST_RECORD_FIELD_MUST_NOT_REACH_OUTPUT"


def _ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json()


def _hash(raw):
    return canonical.content_hash(base64.b64encode(raw).decode("ascii"))


def _snapshot(path, records):
    # Intentionally noncanonical JSON bytes: hashing the parsed object or
    # read_text's newline-normalized value is NOT this snapshot's provenance.
    raw = json.dumps({"description": SOURCE_NOTE, "records": records}, indent=3)
    path.write_bytes((raw.replace("\n", "\r\n") + "\r\n").encode("utf-8"))
    return path


def _body(record=STOCK, *, cite=True, action="answer"):
    return json.dumps({
        "action": action,
        "claims": [{"kind": record["kind"], "value": record["value"]}],
        "evidence_refs": [record["record_id"]] if cite else [],
        "record_age_ms": record["record_age_ms"] if cite else None,
    }, indent=2).encode("utf-8") + b"\r\n"


def _replay(monkeypatch, tmp_path, snapshot, bodies, *, log=b""):
    """Register a temp transcript, not a mocked executor or projection.

    The production recorded adapter checks both input hashes, then the real
    controller captures, persists, scores and finalizes through POST /runs.
    Non-UTF-8 bytes produce a real typed transport failure.
    """
    batch_number = len(bodies)
    batch_ref = f"bookshop_attempt_{batch_number:02d}.jsonl"
    batch = config.FIXTURE_DIR / "requests" / batch_ref
    transcript = tmp_path / f"{snapshot.stem}-{batch_number}-replay.json"
    transcript.write_bytes(json.dumps({
        "request_batch_hash": _hash(batch.read_bytes()),
        "shop_snapshot_hash": _hash(snapshot.read_bytes()),
        "captures": [
            {
                "request_ordinal": ordinal,
                "http_status": 200,
                "body_base64": base64.b64encode(body).decode("ascii"),
                "elapsed_ms": 17 + ordinal,
                "transport_error": None,
                "log_base64": base64.b64encode(log).decode("ascii") if log else None,
            }
            for ordinal, body in enumerate(bodies, 1)
        ],
        "failure": None,
        "wall_ms": 42,
    }).encode("utf-8"))
    monkeypatch.setitem(
        config.RECORDED_TRANSCRIPTS,
        (batch_ref, _hash(snapshot.read_bytes())),
        str(transcript),
    )


def _freeze(client):
    shift = _ok(client.post("/api/engagements/bookshop/shifts"), 201)
    version = _ok(client.post(
        f"/api/shifts/{shift['id']}/artifact/versions",
        json={"contract": config.REPAIR_ARC_CONTRACT_JSON},
    ), 201)
    return shift["id"], version


def _run(client, shift_id, state="FINALIZED"):
    started = _ok(client.post(f"/api/shifts/{shift_id}/runs"), 202)
    # TestClient completes the real background task before returning the POST.
    run = _ok(client.get(f"/api/runs/{started['id']}"))
    assert run["state"] == state, run
    return run["id"]


def _outputs(client, run_id):
    return _ok(client.get(f"/api/runs/{run_id}/outputs"))


def _assert_no_leaks(response_text, needles):
    # Every needle must detect an injected leak in a representative serialized
    # output, including its Windows-path escaping and nested/base64 surfaces.
    for needle in needles:
        for injected in (
            {"public_shop_record": {"title": needle}},
            {"body_base64": base64.b64encode(needle.encode("utf-8")).decode("ascii")},
        ):
            assert any(
                host_leaks(surface, {"needle": needle})
                for surface in decoded_surfaces(json.dumps([injected]))
            ), f"scanner cannot detect {needle!r}"
    for surface in decoded_surfaces(response_text):
        assert not host_leaks(surface, {str(i): value for i, value in enumerate(needles)})


def test_api_projects_validated_answer_and_exact_capture_bytes(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path / "public.json", [STOCK])
    body = _body()
    log = b"exact log\x00\xff\r\n"
    _replay(monkeypatch, tmp_path, snapshot, [body], log=log)
    with TestClient(create_app(str(tmp_path / "answer.db"), shop_snapshot=snapshot)) as client:
        shift_id, _ = _freeze(client)
        run_id = _run(client, shift_id)
        output, = _outputs(client, run_id)
        assert "customer_answer" in output, "approved structured answer projection is missing"
        assert output["customer_answer"] == {
            "action": "answer",
            "display_text": "Answer: stock = out_of_stock (record age 120000 ms).",
            "claims": [{"kind": "stock", "value": "out_of_stock"}],
            "evidence_refs": [STOCK["record_id"]],
            "verified_record_age_ms": 120000,
        }
        assert base64.b64decode(output["body_base64"], validate=True) == body
        assert base64.b64decode(output["log_base64"], validate=True) == log
        assert output["elapsed_ms"] == 18
        assert output["http_status"] == 200
        assert output["transport_error"] is None
        assert output["public_shop_record"] == STOCK
        assert output["public_shop_record_ref"] == STOCK["record_id"]
        assert output["public_shop_snapshot_hash"] == _hash(snapshot.read_bytes())
        assert set(output) == {
            "id", "run_id", "request_ordinal", "request_text", "http_status", "body_base64",
            "elapsed_ms", "transport_error", "log_base64", "customer_answer",
            "public_shop_record", "public_shop_record_ref", "public_shop_snapshot_hash",
        }


@pytest.mark.parametrize("body", [
    pytest.param(b"{not json", id="invalid-json"),
    pytest.param(b"{}", id="missing-structured-fields"),
    pytest.param(_body().replace(b"120000", b"7"), id="false-attested-age"),
    pytest.param(_body().replace(STOCK["record_id"].encode(), b"unknown-public-ref"), id="unknown-ref"),
    pytest.param(json.dumps({**json.loads(_body()), "display_text": "authored lie"}).encode(), id="authored-text"),
    pytest.param(bytes(range(256)) + b"\r\n\x00\xff", id="arbitrary-non-utf8"),
])
def test_malformed_output_has_no_answer_but_keeps_raw_bytes_and_public_record(
    tmp_path, monkeypatch, body,
):
    snapshot = _snapshot(tmp_path / "malformed.json", [STOCK])
    _replay(monkeypatch, tmp_path, snapshot, [body])
    non_utf8 = body.startswith(bytes(range(256)))
    with TestClient(create_app(str(tmp_path / "malformed.db"), shop_snapshot=snapshot)) as client:
        shift_id, _ = _freeze(client)
        run_id = _run(client, shift_id, "FAILED" if non_utf8 else "FINALIZED")
        output, = _outputs(client, run_id)
        assert "customer_answer" in output, "approved answer field is missing"
        assert output["customer_answer"] is None
        assert base64.b64decode(output["body_base64"], validate=True) == body
        assert output["public_shop_record"] == STOCK
        assert output["public_shop_record_ref"] == STOCK["record_id"]
        assert output["public_shop_snapshot_hash"] == _hash(snapshot.read_bytes())
        checks = _ok(client.get(f"/api/runs/{run_id}/checks"))
        if non_utf8:
            assert output["transport_error"] == "CAPTURE_NON_UTF8"
            assert checks == []
        else:
            assert {check["reason_code"] for check in checks} == {"MALFORMED_RESPONSE"}
            assert {check["observed_ref"] for check in checks} == {output["id"]}


@pytest.mark.parametrize("action,display_text", [
    ("ask", "Ask: I need more information from you before I can answer."),
    ("decline", "Decline: I cannot answer that from the shop records."),
    ("escalate", "Escalate: a person from the shop should handle this request."),
])
def test_valid_non_answer_actions_use_controller_text(tmp_path, monkeypatch, action, display_text):
    snapshot = _snapshot(tmp_path / "action.json", [STOCK])
    body = json.dumps({"action": action, "claims": [], "evidence_refs": [], "record_age_ms": None}).encode()
    _replay(monkeypatch, tmp_path, snapshot, [body])
    with TestClient(create_app(str(tmp_path / "action.db"), shop_snapshot=snapshot)) as client:
        shift_id, _ = _freeze(client)
        output, = _outputs(client, _run(client, shift_id))
        assert "customer_answer" in output, "approved answer field is missing"
        assert output["customer_answer"] == {
            "action": action, "display_text": display_text, "claims": [],
            "evidence_refs": [], "verified_record_age_ms": None,
        }
        assert output["public_shop_record"] == STOCK


def test_public_record_uses_executed_ordinal_not_citation_or_array_position(tmp_path, monkeypatch):
    # Reverse the snapshot order and cite the other request's record on purpose.
    # Neither citation selection nor snapshot[index] can pass this assertion.
    snapshot = _snapshot(tmp_path / "ordinal.json", [FUTURE, PRICE, {**STOCK, "note": RECORD_NOTE}])
    _replay(monkeypatch, tmp_path, snapshot, [_body(PRICE)])
    _replay(monkeypatch, tmp_path, snapshot, [_body(PRICE), _body(STOCK, cite=False)])
    db_file = tmp_path / "ordinal.db"
    with TestClient(create_app(str(db_file), shop_snapshot=snapshot)) as client:
        shift_id, _ = _freeze(client)
        first_id = _run(client, shift_id)
        first_output, = _outputs(client, first_id)
        assert "public_shop_record" in first_output, "independent public comparison is missing"
        assert first_output["public_shop_record"] == STOCK
        run_id = _run(client, shift_id)
        response = client.get(f"/api/runs/{run_id}/outputs")
        outputs = _ok(response)
        assert [out["request_ordinal"] for out in outputs] == [1, 2]
        assert [out["public_shop_record"] for out in outputs] == [STOCK, PRICE]
        assert [out["public_shop_record_ref"] for out in outputs] == [STOCK["record_id"], PRICE["record_id"]]
        assert {out["public_shop_snapshot_hash"] for out in outputs} == {_hash(snapshot.read_bytes())}
        assert outputs[1]["customer_answer"]["evidence_refs"] == []
        conn = db.connect(db_file)
        try:
            run = repo.get_run(conn, run_id)
            assert run.request_batch_ref == "bookshop_attempt_02.jsonl"
            assert run.shop_snapshot_ref == str(snapshot)
            batch = [json.loads(line) for line in (config.FIXTURE_DIR / "requests" / run.request_batch_ref).read_bytes().splitlines()]
            assert [out["request_text"] for out in outputs] == [entry["text"] for entry in batch]
        finally:
            conn.close()
        future_batch = [json.loads(line) for line in (config.FIXTURE_DIR / "requests" / "bookshop_attempt_03.jsonl").read_bytes().splitlines()]
        _assert_no_leaks(response.text, [
            SOURCE_NOTE, RECORD_NOTE, FUTURE["record_id"], FUTURE["title"], FUTURE["value"],
            future_batch[2]["text"], str(snapshot), str(config.BOOKSHOP_SNAPSHOT),
        ])
        checks = _ok(client.get(f"/api/runs/{run_id}/checks"))
        assert any(check["reason_code"] == "MISSING_EVIDENCE" and check["observed_ref"] == outputs[1]["id"] for check in checks)


def test_historical_projection_uses_its_run_snapshot_not_new_controller_default(tmp_path, monkeypatch):
    first = _snapshot(tmp_path / "first.json", [STOCK, PRICE])
    changed_stock = {**STOCK, "value": "in_stock", "record_age_ms": 9000}
    second = _snapshot(tmp_path / "second.json", [changed_stock, PRICE])
    _replay(monkeypatch, tmp_path, first, [_body()])
    _replay(monkeypatch, tmp_path, second, [_body(changed_stock), _body(PRICE)])
    app = create_app(str(tmp_path / "history.db"), shop_snapshot=first)
    with TestClient(app) as client:
        shift_id, _ = _freeze(client)
        first_run = _run(client, shift_id)
        before = _outputs(client, first_run)
        assert "public_shop_snapshot_hash" in before[0], "public snapshot provenance is missing"
        app.state.shop_snapshot = str(second)
        second_run = _run(client, shift_id)
        after = _outputs(client, first_run)
        assert after == before
        assert after[0]["public_shop_record"] == STOCK
        assert after[0]["customer_answer"]["verified_record_age_ms"] == 120000
        assert after[0]["public_shop_snapshot_hash"] == _hash(first.read_bytes())
        newer = _outputs(client, second_run)[0]
        assert newer["public_shop_record"] == changed_stock
        assert newer["customer_answer"]["verified_record_age_ms"] == 9000
        assert newer["public_shop_snapshot_hash"] == _hash(second.read_bytes())
        assert newer["public_shop_snapshot_hash"] != after[0]["public_shop_snapshot_hash"]
        assert _hash(first.read_bytes()) != config.BOOKSHOP_SNAPSHOT_HASH
        assert _hash(second.read_bytes()) != config.BOOKSHOP_SNAPSHOT_HASH


def test_historical_projection_binds_the_bytes_the_run_consumed_not_the_current_file(tmp_path, monkeypatch):
    """Replace the source snapshot's contents at the SAME pathname after the run.

    The historical projection must keep describing the bytes the run consumed: a
    retrieval that re-reads the mutable pathname changes the public record and the
    provenance hash while the run's captures stay untouched.
    """
    snapshot = _snapshot(tmp_path / "consumed.json", [STOCK, PRICE])
    _replay(monkeypatch, tmp_path, snapshot, [_body()])
    with TestClient(create_app(str(tmp_path / "same-path.db"), shop_snapshot=snapshot)) as client:
        shift_id, _ = _freeze(client)
        run_id = _run(client, shift_id)
        before = _outputs(client, run_id)
        consumed_hash = before[0]["public_shop_snapshot_hash"]
        _snapshot(snapshot, [{**STOCK, "value": "in_stock", "record_age_ms": 9000}, PRICE])
        assert _hash(snapshot.read_bytes()) != consumed_hash, "replacement did not change the source bytes"
        after = _outputs(client, run_id)
        assert after == before
        assert after[0]["public_shop_record"] == STOCK
        assert after[0]["customer_answer"]["verified_record_age_ms"] == 120000
        assert after[0]["public_shop_snapshot_hash"] == consumed_hash


@pytest.mark.parametrize("body", [
    pytest.param(None, id="finalized-run"),
    pytest.param(bytes(range(256)) + b"\r\n\x00\xff", id="failed-non-utf8-run"),
])
def test_outputs_keep_capture_bytes_when_the_snapshot_source_is_missing(tmp_path, monkeypatch, body):
    """A missing comparison source must never abort the captured output response.

    The run consumed the snapshot at execution time; when the source file is gone
    the retained capture, its bytes and its execution-time comparison must stay
    retrievable. Enrichment failure may only drop optional comparison evidence,
    never the raw response.
    """
    snapshot = _snapshot(tmp_path / "gone.json", [STOCK])
    transmitted = body if body is not None else _body()
    _replay(monkeypatch, tmp_path, snapshot, [transmitted])
    with TestClient(create_app(str(tmp_path / "gone.db"), shop_snapshot=snapshot)) as client:
        shift_id, _ = _freeze(client)
        run_id = _run(client, shift_id, "FINALIZED" if body is None else "FAILED")
        before = _outputs(client, run_id)
        snapshot.unlink()
        response = client.get(f"/api/runs/{run_id}/outputs")
        output, = _ok(response)
        assert output == before[0]
        assert base64.b64decode(output["body_base64"], validate=True) == transmitted
        assert output["public_shop_record"] == STOCK
        assert output["public_shop_snapshot_hash"] == before[0]["public_shop_snapshot_hash"]


def test_legacy_run_without_capture_degrades_when_the_source_is_missing(tmp_path):
    """A run row that predates the Slice 9 capture re-reads its recorded path.

    When that path is gone, the response must still carry the retained bytes and
    the stored answer, and null only the optional comparison fields; removing the
    degradation guard turns this into a 500 and loses the capture. The client
    surfaces that crash as the HTTP 500 a real consumer sees, so the removal
    fails this test with an assertion, not with an incidental exception."""
    snapshot = _snapshot(tmp_path / "legacy.json", [STOCK])
    body = _body()
    db_file = tmp_path / "legacy.db"
    with TestClient(create_app(str(db_file), shop_snapshot=snapshot), raise_server_exceptions=False) as client:
        shift_id, _ = _freeze(client)
        conn = db.connect(db_file)
        try:
            run = orchestrator.start_run(conn, shift_id, shop_snapshot=snapshot)
            assert repo.get_run_snapshot_bytes(conn, run.id) is None, "reservation must not fabricate a capture"
            repo.insert_output(conn, RunOutput(
                id=f"{run.id}-out-1", run_id=run.id, request_ordinal=1,
                request_text="Is the Dune hardback on the shelf?", http_status=200,
                body=body, elapsed_ms=5,
            ))
            repo.update_run(conn, run.id, RunState.CAPTURED)
            conn.commit()
        finally:
            conn.close()
        before = _outputs(client, run.id)
        assert before[0]["public_shop_record"] == STOCK, "legacy projection needs the live source"
        snapshot.unlink()
        response = client.get(f"/api/runs/{run.id}/outputs")
        output, = _ok(response)
        assert base64.b64decode(output["body_base64"], validate=True) == body
        assert output["customer_answer"] is None
        assert {name: output[name] for name in (
            "public_shop_record", "public_shop_record_ref", "public_shop_snapshot_hash",
        )} == {"public_shop_record": None, "public_shop_record_ref": None, "public_shop_snapshot_hash": None}


@pytest.mark.parametrize("records", [[], [PRICE]])
def test_absent_independent_record_nulls_comparison_and_provenance(tmp_path, monkeypatch, records):
    # A price record cannot stand in for the stock request.
    snapshot = _snapshot(tmp_path / "no-stock.json", records)
    _replay(monkeypatch, tmp_path, snapshot, [_body(cite=False)])
    with TestClient(create_app(str(tmp_path / "absent.db"), shop_snapshot=snapshot)) as client:
        shift_id, _ = _freeze(client)
        run_id = _run(client, shift_id)
        response = client.get(f"/api/runs/{run_id}/outputs")
        output, = _ok(response)
        assert "public_shop_record" in output, "null comparison fields are missing"
        assert {name: output[name] for name in (
            "public_shop_record", "public_shop_record_ref", "public_shop_snapshot_hash",
        )} == {"public_shop_record": None, "public_shop_record_ref": None, "public_shop_snapshot_hash": None}
        checks = _ok(client.get(f"/api/runs/{run_id}/checks"))
        assert {check["reason_code"] for check in checks} == {"MISSING_EVIDENCE"}
        assert {check["public_check_id"] for check in checks} == {None}
        assert all(check["expected_ref"].startswith("sealed:") and len(check["expected_ref"]) == 71 for check in checks)
        _assert_no_leaks(response.text, [SOURCE_NOTE, str(snapshot), PRICE["record_id"]])


def test_board_filenames_come_only_from_latest_immutable_version(tmp_path):
    with TestClient(create_app(str(tmp_path / "board.db"))) as client:
        board = _ok(client.get("/api/engagements/bookshop/board"))
        assert "artifact_files" in board, "immutable artifact filenames are missing"
        assert board["artifact_files"] == []
        shift_id, version = _freeze(client)
        frozen_files = _ok(client.get(f"/api/shifts/{shift_id}/artifact"))["files"]
        draft_files = {"draft_only.py": "DRAFT_CONTENT_MUST_NOT_LEAK_TO_BOARD"}
        _ok(client.put(f"/api/shifts/{shift_id}/artifact", json={"files": draft_files}))
        board_response = client.get("/api/engagements/bookshop/board")
        board = _ok(board_response)
        assert board["artifact_files"] == sorted(frozen_files)
        assert board["latest_version"]["id"] == version["id"]
        _assert_no_leaks(board_response.text, [*draft_files, *draft_files.values(), *frozen_files.values()])
        latest = _ok(client.post(f"/api/shifts/{shift_id}/artifact/versions", json={"contract": config.REPAIR_ARC_CONTRACT_JSON}), 201)
        assert _ok(client.get("/api/engagements/bookshop/board"))["artifact_files"] == ["draft_only.py"]
        _ok(client.post(f"/api/shifts/{shift_id}/close"))
        _ok(client.post("/api/engagements/bookshop/shifts"), 201)
        inherited = _ok(client.get("/api/engagements/bookshop/board"))
        assert inherited["latest_version"]["id"] == latest["id"]
        assert inherited["artifact_files"] == ["draft_only.py"]
