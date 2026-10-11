"""S24 independent defect regressions, using fresh selected operational history.

History corruption is confined to disposable database copies. Replay reader
faults bypass SQLite's duplicate-ordinal constraint deliberately. No source,
reviewed fixture, seal or pin is faulted by these tests.
"""
import base64
import hashlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from shiftwork import config, experiments, orchestrator
from shiftwork.app import create_app
from shiftwork.domain import canonical
from shiftwork.domain.errors import ShiftworkDomainError
from shiftwork.domain.models import ExecutorFailure, LedgerEventDraft, LedgerEventType, RunState
from shiftwork.executor.local_process import LocalProcessAdapter
from shiftwork.ledger import chain
from shiftwork.store import db, repo
from tests.orchestrator import test_gtm_pipeline as gtm
from tests.packs.material import apply_staged_material, staged_material


@pytest.fixture(scope="module")
def operated_history(tmp_path_factory):
    path = tmp_path_factory.mktemp("s24-history") / "healthy.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        flow = gtm.qualify_gtm(client)
        shift = gtm.gtm_next_shift(client, flow["shift_id"])
        started = client.post(f"/api/shifts/{shift['id']}/runs",
                              json={"client_request_id": "s24-repair-healthy"})
        assert started.status_code == 202, started.text
        run = gtm.pivot_flow.wait_run(client, started.json()["id"])
        assert run["state"] == "FINALIZED", run
    return path, run["id"], shift["id"]


def copy_database(source_path, path):
    source = sqlite3.connect(source_path.resolve().as_uri() + "?mode=ro", uri=True)
    target = sqlite3.connect(path)
    try:
        source.backup(target)
    finally:
        source.close()
        target.close()
    return path


@pytest.fixture
def history(operated_history, tmp_path):
    source_path, run_id, shift_id = operated_history
    path = copy_database(source_path, tmp_path / "copy.db")
    conn = db.connect(path)
    try:
        yield conn, repo.get_run(conn, run_id), repo.get_shift(conn, shift_id)
    finally:
        conn.rollback()
        conn.close()


def rows(conn):
    return tuple(conn.iterdump())


def rebind_context(conn, context_id):
    """Keep overall identity valid to isolate a component binding guard.

    These are the historical producer's identity fields, excluding retention-only
    bytes, DB IDs, schema/default fields and timestamps. Do not use current fixtures.
    """
    context = repo.get_execution_context(conn, context_id)
    names = ("engagement_slug", "workloads", "mission_hash", "public_data_hash",
             "starting_business_state_hash", "requirement_set_id", "requirement_set_hash",
             "visible_check_set_hash", "condition", "evaluator_version", "reducer_version",
             "executor_class", "harness_hash", "image_ref", "service_model",
             "service_model_settings_json", "resource_limits_json")
    view = context.model_dump(mode="json")
    digest = canonical.content_hash({name: view[name] for name in names})
    conn.execute("UPDATE execution_contexts SET content_hash=? WHERE id=?", (digest, context_id))
    conn.commit()


@pytest.mark.parametrize("damage", ["context_identity", "spec_hash", "spec_bytes",
    "spec_mission_disagreement", "request_count", "requirement_hash", "condition_hash"])
def test_gtm_replay_validates_identity_and_spec_bindings_independently(history, damage):
    conn, run, _ = history
    before = rows(conn)
    assert orchestrator.replay_assessment(conn, run.id).status == "IDENTICAL"
    assert rows(conn) == before
    context = repo.get_execution_context(conn, run.context_id)
    specs_bytes = base64.b64decode(context.workloads[0].request_specs_bytes_base64)
    assert hashlib.sha256(specs_bytes).hexdigest() == context.workloads[0].request_specs_hash
    batch_bytes = base64.b64decode(context.workloads[0].request_batch_bytes_base64)
    assert canonical.content_hash(base64.b64encode(batch_bytes).decode()) == context.workloads[0].request_batch_hash
    if damage == "context_identity":
        conn.execute("UPDATE execution_contexts SET content_hash=? WHERE id=?", ("1" * 64, context.id))
    elif damage == "requirement_hash":
        conn.execute("UPDATE execution_contexts SET requirement_set_hash=? WHERE id=?", ("2" * 64, context.id))
    elif damage == "condition_hash":
        condition = context.condition.model_dump(mode="json")
        condition["content_hash"] = "3" * 64
        conn.execute("UPDATE execution_contexts SET condition_json=? WHERE id=?", (json.dumps(condition), context.id))
    else:
        workloads = [item.model_dump(mode="json") for item in context.workloads]
        if damage == "spec_hash":
            workloads[0]["request_specs_hash"] = "2" * 64
            conn.execute("UPDATE execution_contexts SET visible_check_set_hash=? WHERE id=?", ("2" * 64, context.id))
        elif damage == "request_count": workloads[0]["request_count"] += 1
        else:
            specs = json.loads(specs_bytes)
            if damage == "spec_mission_disagreement": specs[0]["text"] += " changed specification"
            # For spec_bytes, only the retained serialization changes. The
            # decoded specs still equal the mission, isolating the byte hash.
            changed = json.dumps(specs, indent=2).encode()
            workloads[0]["request_specs_bytes_base64"] = base64.b64encode(changed).decode()
            if damage == "spec_mission_disagreement":
                workloads[0]["request_specs_hash"] = hashlib.sha256(changed).hexdigest()
                conn.execute("UPDATE execution_contexts SET visible_check_set_hash=? WHERE id=?", (workloads[0]["request_specs_hash"], context.id))
        conn.execute("UPDATE execution_contexts SET workloads_json=? WHERE id=?", (json.dumps(workloads), context.id))
    conn.commit()
    if damage != "context_identity": rebind_context(conn, context.id)
    before = rows(conn); changes = conn.total_changes
    report = orchestrator.replay_assessment(conn, run.id)
    assert report.status == "UNKNOWN_MISSING_INPUTS", "corrupt captured binding was reported verified"
    assert not report.wrote_rows and conn.total_changes == changes and rows(conn) == before


@pytest.mark.parametrize("damage", ["transport", "duplicate", "foreign_run", "missing", "extra_ordinal"])
def test_gtm_invalid_replay_capture_inventory_returns_evidence_verdict(history, monkeypatch, damage):
    conn, run, _ = history
    assert orchestrator.replay_assessment(conn, run.id).status == "IDENTICAL"
    outputs = repo.list_outputs(conn, run.id)
    original = repo.list_outputs
    if damage == "transport":
        conn.execute("UPDATE run_outputs SET transport_error='SERVICE_UNREACHABLE' WHERE run_id=?", (run.id,))
        conn.commit()
    else:
        faulty = (outputs + [outputs[0].model_copy(update={"id": "duplicate"})] if damage == "duplicate" else
                  [outputs[0].model_copy(update={"run_id": "foreign"})] if damage == "foreign_run" else
                  [] if damage == "missing" else
                  outputs + [outputs[0].model_copy(update={"id": "extra", "request_ordinal": 2})])
        monkeypatch.setattr(repo, "list_outputs", lambda c, r: faulty if r == run.id else original(c, r))
    before = rows(conn); changes = conn.total_changes
    report = orchestrator.replay_assessment(conn, run.id)
    assert report.status == "UNKNOWN_MISSING_INPUTS", "invalid replay inventory lacks an evidence verdict"
    assert not report.wrote_rows and conn.total_changes == changes and rows(conn) == before


@pytest.mark.parametrize("error", [ValueError, RuntimeError])
def test_gtm_replay_does_not_swallow_programming_errors(history, monkeypatch, error):
    conn, run, _ = history
    def bug(*args, **kwargs): raise error("unexpected reducer bug")
    monkeypatch.setattr(orchestrator.reducer, "reduce_operation", bug)
    before = rows(conn)
    with pytest.raises(error, match="unexpected reducer bug"):
        orchestrator.replay_assessment(conn, run.id)
    assert rows(conn) == before


@pytest.mark.parametrize("damage", ["missing_clock", "duplicate_clock", "wrong_clock_owner",
    "foreign_owner_run", "foreign_owner_check", "foreign_owner_output", "foreign_clock_cause",
    "missing_owner", "missing_both", "wrong_trace", "duplicate_owner"])
def test_gtm_inheritance_refuses_corrupt_consequences_and_provenance(history, damage):
    conn, run, shift = history
    original = repo.list_ledger_events(conn, "gtm")
    drafts = []
    for event in original:
        draft = LedgerEventDraft.model_validate(event.model_dump(exclude={"seq", "prev_hash", "hash"}))
        if event.event_type is LedgerEventType.SLA_CLOCK_STARTED:
            if damage in ("missing_clock", "missing_both"): continue
            if damage == "duplicate_clock": drafts.append(draft)
            if damage == "wrong_clock_owner": draft = draft.model_copy(update={"payload": dict(draft.payload, owner="owner-amer-platform")})
            if damage == "foreign_clock_cause": draft = draft.model_copy(update={"cause_refs": (run.id, "foreign-check", "foreign-output")})
        if event.event_type is LedgerEventType.OWNER_ASSIGNED:
            if damage in ("missing_owner", "missing_both"): continue
            if damage == "duplicate_owner": drafts.append(draft)
            if damage.startswith("foreign_owner_"):
                causes = list(draft.cause_refs)
                causes[{"foreign_owner_run": 0, "foreign_owner_check": 1, "foreign_owner_output": 2}[damage]] = "foreign-ref"
                draft = draft.model_copy(update={"cause_refs": tuple(causes)})
            if damage == "wrong_trace": draft = draft.model_copy(update={"payload": dict(draft.payload, decision_trace=[])})
        drafts.append(draft)
    modified = chain.append(drafts, prev_hash=config.GENESIS_HASH, start_seq=1)
    assert chain.verify_chain(modified) is chain.ChainStatus.VALID
    conn.execute("DELETE FROM ledger_events WHERE engagement_slug='gtm'")
    for event in modified: repo.insert_ledger_event(conn, "gtm", event)
    conn.commit()
    before = rows(conn); changes = conn.total_changes
    with pytest.raises(orchestrator.LifecycleError, match="pipeline history"):
        orchestrator.freeze_diagnostic_context(conn, shift, operation=True)
    assert conn.total_changes == changes and rows(conn) == before, "invalid inheritance wrote new state"


def test_gtm_healthy_history_reprocessing_and_chain_remain_separate(history):
    conn, run, shift = history
    assert chain.verify_chain(repo.list_ledger_events(conn, "gtm")) is chain.ChainStatus.VALID
    business = gtm.business_rows(conn)
    context = orchestrator.freeze_diagnostic_context(conn, shift, operation=True)
    assert context.starting_business_state_json["pipeline_records"] == {
        "signal:incident-apac": {"owner": "owner-apac-platform", "record_ref": "pipeline:signal:incident-apac"}}
    assert gtm.business_rows(conn) == business
    before = rows(conn)
    assert orchestrator.replay_assessment(conn, run.id).status == "IDENTICAL"
    assert rows(conn) == before
    event = repo.list_ledger_events(conn, "gtm")[-1]
    conn.execute("UPDATE ledger_events SET prev_hash=? WHERE engagement_slug='gtm' AND seq=?", ("0" * 64, event.seq))
    conn.commit()
    assert chain.verify_chain(repo.list_ledger_events(conn, "gtm")) is chain.ChainStatus.BROKEN
    assert orchestrator.replay_assessment(conn, run.id).status == "IDENTICAL"


def test_gtm_archived_ownership_uses_historical_captures_not_current_rules(history, tmp_path, monkeypatch):
    conn, run, shift = history
    world = gtm.material_json("fixtures/state/gtm_compare_state_v1.json")
    world["records"] = [r for r in world["records"] if r["entity_ref"] != "signal:incident-apac"]
    mission = gtm.material_json("fixtures/mission/gtm_pipeline_v1.json")
    mission["weights"].update(owner=999, sla=999, handoff=999)
    assert "signal:incident-apac" not in {r["entity_ref"] for r in world["records"]}
    before = gtm.business_rows(conn)
    with staged_material(monkeypatch, tmp_path / "changed-current-material", {
        "fixtures/state/gtm_pipeline_public_state.json": json.dumps(world).encode(),
        "fixtures/mission/gtm_pipeline_v1.json": json.dumps(mission).encode(),
    }):
        context = orchestrator.freeze_diagnostic_context(conn, shift, operation=True)
    assert context.starting_business_state_json["pipeline_records"]["signal:incident-apac"]["owner"] == "owner-apac-platform"
    assert gtm.business_rows(conn) == before
    assert orchestrator.replay_assessment(conn, run.id).status == "IDENTICAL"


@pytest.fixture(scope="module")
def review_history(tmp_path_factory):
    """Disposable operator mission/state; not shipped-material review approval."""
    directory = tmp_path_factory.mktemp("s24-human-review")
    path = directory / "review.db"
    mission = gtm.material_json("fixtures/mission/gtm_pipeline_v1.json")
    for task in mission["request_specs"][0]["tasks"]:
        task["condition_json"]["expected_decisions"] = ["QUALIFIED", "REVIEW"]
    world = gtm.material_json("fixtures/state/gtm_pipeline_public_state.json")
    world["records"][0]["value"]["confidence"] = 50
    with pytest.MonkeyPatch.context() as binding:
        with staged_material(binding, directory / "operator-mission", {
            "fixtures/mission/gtm_pipeline_v1.json": json.dumps(mission).encode(),
        }):
            with binding.context() as state_binding:
                with TestClient(create_app(str(path), executor="local_process")) as client:
                    flow = gtm.qualify_gtm(client)
                    shift = gtm.gtm_next_shift(client, flow["shift_id"])
                    apply_staged_material(state_binding, directory / "operator-state", {
                        "fixtures/state/gtm_pipeline_public_state.json": json.dumps(world).encode(),
                    })
                    started = client.post(f"/api/shifts/{shift['id']}/runs", json={"client_request_id": "repair-review"})
                    assert started.status_code == 202, started.text
                    run = gtm.pivot_flow.wait_run(client, started.json()["id"])
                    assert run["state"] == "FINALIZED", run
    return path, run["id"], shift["id"]


@pytest.mark.parametrize("damage", ["healthy", "missing_handoff", "foreign_handoff", "wrong_terminal"])
def test_gtm_human_review_inheritance_requires_bound_terminal_handoff(review_history, tmp_path, damage):
    path, run_id, shift_id = review_history
    conn = db.connect(tmp_path / "review-copy.db")
    source = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        source.backup(conn)
    finally:
        source.close()
    try:
        assert orchestrator.replay_assessment(conn, run_id).status == "IDENTICAL"
        drafts = []
        for event in repo.list_ledger_events(conn, "gtm"):
            draft = LedgerEventDraft.model_validate(event.model_dump(exclude={"seq", "prev_hash", "hash"}))
            if event.event_type is LedgerEventType.HANDOFF_ESCALATED:
                assert draft.payload["owner"] == "revenue-review" and draft.payload["terminal_action"] == "HUMAN_HANDOFF"
                if damage == "missing_handoff": continue
                if damage == "foreign_handoff": draft = draft.model_copy(update={"cause_refs": (run_id, "foreign-check", "foreign-output")})
                if damage == "wrong_terminal": draft = draft.model_copy(update={"payload": dict(draft.payload, terminal_action="SENT_MESSAGE")})
            drafts.append(draft)
        events = chain.append(drafts, prev_hash=config.GENESIS_HASH, start_seq=1)
        assert chain.verify_chain(events) is chain.ChainStatus.VALID
        conn.execute("DELETE FROM ledger_events WHERE engagement_slug='gtm'")
        for event in events: repo.insert_ledger_event(conn, "gtm", event)
        conn.commit()
        before = rows(conn); business = gtm.business_rows(conn)
        if damage == "healthy":
            context = orchestrator.freeze_diagnostic_context(conn, repo.get_shift(conn, shift_id), operation=True)
            assert context.starting_business_state_json["pipeline_records"]["signal:incident-apac"]["owner"] == "revenue-review"
            assert gtm.business_rows(conn) == business
        else:
            with pytest.raises(orchestrator.LifecycleError, match="pipeline history"):
                orchestrator.freeze_diagnostic_context(conn, repo.get_shift(conn, shift_id), operation=True)
            assert rows(conn) == before
    finally:
        conn.close()


@pytest.mark.parametrize("fault", [False, True])
def test_gtm_derived_text_matches_assessment_and_keeps_raw_capture(tmp_path, monkeypatch, fault):
    path = tmp_path / "projection.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        flow = gtm.qualify_gtm(client)
        shift = gtm.gtm_next_shift(client, flow["shift_id"])
        original = LocalProcessAdapter.execute
        async def capture(self, request):
            result = await original(self, request)
            if not fault: return result
            raw = json.loads(result.captures[0].body)
            raw["task_results"][1]["claims"][0]["value"] = "owner-amer-platform"
            raw["task_results"][2]["claims"][0]["value"]["owner"] = "owner-amer-platform"
            return result.model_copy(update={"captures": (result.captures[0].model_copy(update={"body": json.dumps(raw).encode()}),)})
        monkeypatch.setattr(LocalProcessAdapter, "execute", capture)
        started = client.post(f"/api/shifts/{shift['id']}/runs", json={"client_request_id": "s24-projection"})
        assert started.status_code == 202, started.text
        view = gtm.pivot_flow.wait_run(client, started.json()["id"])
        assert view["state"] == "FINALIZED", view
        conn = db.connect(path)
        try:
            run = repo.get_run(conn, view["id"]); output = repo.list_outputs(conn, run.id)[0]
            before = rows(conn); raw_bytes = output.body
            customer = client.get(f"/api/runs/{run.id}/outputs").json()[0]["customer_answer"]
            drafts = orchestrator._stored_operation_drafts(conn, run, "gtm")
            if fault:
                assert b"owner-amer-platform" in raw_bytes, "fault needle never reached captured bytes"
                assert [d["event_type"] for d in drafts] == ["INCIDENT_OPENED"]
                rejected = [r for r in repo.list_task_assessment_models(conn, run.id) if not r.mandatory_pass]
                assert {r.task_id for r in rejected} == {"owner", "write"}
                assert all("WRONG_ACTION" in [code.value for code in r.reason_codes] for r in rejected)
                assert "owner-amer-platform" not in customer["display_text"], "derived text presents a rejected owner"
                assert "record prepared" not in customer["display_text"], "derived text presents a rejected write"
                assert "No additional owner" not in customer["display_text"]
                assert [claim["kind"] for claim in customer["claims"]] == ["qualification"]
            else:
                assert "Synthetic owner: owner-apac-platform." in customer["display_text"]
                assert "record prepared" in customer["display_text"]
                assert [d["event_type"] for d in drafts] == ["OWNER_ASSIGNED", "SLA_CLOCK_STARTED"]
            assert repo.list_outputs(conn, run.id)[0].body == raw_bytes and rows(conn) == before
        finally:
            conn.close()


@pytest.mark.parametrize("missing,expected_claims", [
    (("owner",), ["qualification", "pipeline_write"]),
    (("write",), ["qualification", "owner_assignment"]),
    (("owner", "write"), ["qualification"]),
], ids=["owner", "write", "both"])
def test_gtm_missing_required_task_cannot_present_no_action_assurance(
        tmp_path, monkeypatch, missing, expected_claims):
    path = tmp_path / "missing-task.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        flow = gtm.qualify_gtm(client)
        shift = gtm.gtm_next_shift(client, flow["shift_id"])
        original = LocalProcessAdapter.execute
        faulty = []
        async def omit(self, request):
            result = await original(self, request)
            raw = json.loads(result.captures[0].body)
            raw["task_results"] = [row for row in raw["task_results"]
                                   if row["task_id"] not in missing]
            raw_bytes = json.dumps(raw).encode()
            faulty.append(raw_bytes)
            return result.model_copy(update={"captures": (
                result.captures[0].model_copy(update={"body": raw_bytes}),)})
        monkeypatch.setattr(LocalProcessAdapter, "execute", omit)
        started = client.post(f"/api/shifts/{shift['id']}/runs",
                              json={"client_request_id": "s24-missing-task"})
        assert started.status_code == 202, started.text
        view = gtm.pivot_flow.wait_run(client, started.json()["id"])
        assert view["state"] == "FINALIZED", view
        conn = db.connect(path)
        try:
            run = repo.get_run(conn, view["id"])
            output = repo.list_outputs(conn, run.id)[0]
            assert output.body == faulty[0], "raw faulty capture bytes were not preserved"
            rejected = [row for row in repo.list_task_assessment_models(conn, run.id)
                        if not row.mandatory_pass]
            assert {row.task_id for row in rejected} == set(missing)
            assert all("REQUIRED_TASK_MISSING" in [code.value for code in row.reason_codes]
                       for row in rejected)
            drafts = orchestrator._stored_operation_drafts(conn, run, "gtm")
            assert [d["event_type"] for d in drafts] == ["INCIDENT_OPENED"]
            before = rows(conn); changes = conn.total_changes
            customer = client.get(f"/api/runs/{run.id}/outputs").json()[0]["customer_answer"]
            assert conn.total_changes == changes and rows(conn) == before
            assert "No additional owner, record or handoff is required." not in customer["display_text"], \
                "derived text claims no action despite a required task failure"
            assert "rejected by the independent assessment" in customer["display_text"], \
                "derived text omits the required task failure"
            assert [claim["kind"] for claim in customer["claims"]] == expected_claims
        finally:
            conn.close()


BINDINGS = ["spec_binding_absent", "condition_binding_absent", "workload_count_type", "mission_bytes_text"]


def typed_refusal(action, label):
    """Return the typed conflict ``action`` raises; an untyped leak fails by name."""
    try:
        action()
    except (orchestrator.LifecycleError, ShiftworkDomainError) as exc:
        assert exc.kind == "conflict", f"{label} refused as {exc.kind}"
        return exc
    except (ValueError, TypeError) as exc:  # pydantic ValidationError is a ValueError
        pytest.fail(f"{label} escaped as {exc!r}")
    pytest.fail(f"{label} was accepted")


@pytest.mark.parametrize("damage", BINDINGS)
def test_gtm_unreadable_retained_binding_returns_evidence_verdict(history, damage):
    conn, run, _ = history
    assert orchestrator.replay_assessment(conn, run.id).status == "IDENTICAL"
    corrupt_retained_binding(conn, run.context_id, damage)
    before = rows(conn); changes = conn.total_changes
    try:
        report = orchestrator.replay_assessment(conn, run.id)
    except (ValueError, TypeError) as exc:  # pydantic ValidationError is a ValueError
        pytest.fail(f"unreadable retained binding escaped replay as {exc!r}")
    assert report.status == "UNKNOWN_MISSING_INPUTS", \
        "unreadable retained binding escaped without an evidence verdict"
    assert not report.wrote_rows and conn.total_changes == changes and rows(conn) == before


@pytest.mark.parametrize("damage", BINDINGS)
def test_gtm_inheritance_refuses_unreadable_retained_binding(history, damage):
    conn, run, shift = history
    orchestrator.freeze_diagnostic_context(conn, shift, operation=True)
    conn.rollback()
    corrupt_retained_binding(conn, run.context_id, damage)
    before = rows(conn); changes = conn.total_changes
    refusal = typed_refusal(lambda: orchestrator.freeze_diagnostic_context(conn, shift, operation=True),
                            "inheritance over an unreadable retained binding")
    assert "unreadable" in str(refusal), str(refusal)
    assert conn.total_changes == changes and rows(conn) == before, "invalid inheritance wrote new state"


@pytest.mark.parametrize("table,column,value", [
    ("run_outputs", "transport_error", "NOT_A_FAILURE"),
    ("check_results", "reason_code", "NOT_A_CODE"),
    ("check_results", "verdict", "maybe"),
    ("ledger_events", "event_type", "NOT_A_TYPE"),
], ids=["output_failure", "check_reason", "check_verdict", "ledger_event_type"])
def test_gtm_unreadable_retained_row_returns_verdict_and_refuses_inheritance(history, table, column, value):
    conn, run, shift = history
    assert orchestrator.replay_assessment(conn, run.id).status == "IDENTICAL"
    if table == "ledger_events":
        key = conn.execute("SELECT MIN(seq) FROM ledger_events WHERE engagement_slug='gtm'").fetchone()[0]
        where = "engagement_slug='gtm' AND seq=?"
    else:
        key = conn.execute(f"SELECT MIN(rowid) FROM {table} WHERE run_id=?", (run.id,)).fetchone()[0]
        where = "rowid=?"
    # No CHECK constraint guards these columns, so the edit persists as stored text.
    conn.execute(f"UPDATE {table} SET {column}=? WHERE {where}", (value, key))
    conn.commit()
    assert conn.execute(f"SELECT {column} FROM {table} WHERE {where}", (key,)).fetchone()[0] == value
    before = rows(conn); changes = conn.total_changes
    try:
        report = orchestrator.replay_assessment(conn, run.id)
    except (ValueError, TypeError) as exc:
        pytest.fail(f"unreadable retained {table} row escaped replay as {exc!r}")
    assert report.status == "UNKNOWN_MISSING_INPUTS", f"unreadable retained {table} row lacks an evidence verdict"
    assert not report.wrote_rows and conn.total_changes == changes and rows(conn) == before
    typed_refusal(lambda: orchestrator.freeze_diagnostic_context(conn, shift, operation=True),
                  f"inheritance over an unreadable {table} row")
    assert conn.total_changes == changes and rows(conn) == before, "invalid inheritance wrote new state"


@pytest.mark.parametrize("operation", [False, True], ids=["diagnostic", "operation"])
def test_gtm_freeze_refuses_reused_unreadable_context(history, operation):
    conn, _, shift = history
    context = orchestrator.freeze_diagnostic_context(conn, shift, operation=operation)
    conn.commit()
    assert orchestrator.freeze_diagnostic_context(conn, shift, operation=operation).id == context.id, \
        "the second freeze did not reuse the stored context"
    corrupt_retained_binding(conn, context.id, "spec_binding_absent")
    before = rows(conn); changes = conn.total_changes
    typed_refusal(lambda: orchestrator.freeze_diagnostic_context(conn, shift, operation=operation),
                  "freeze over a reused unreadable context")
    assert conn.total_changes == changes and rows(conn) == before, "refused freeze wrote new state"


@pytest.fixture(scope="module")
def next_shift(tmp_path_factory):
    """A qualified GTM pipeline with its next shift open and no operation reserved."""
    path = tmp_path_factory.mktemp("s24-next-shift") / "next.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        flow = gtm.qualify_gtm(client)
        shift = gtm.gtm_next_shift(client, flow["shift_id"])
    return path, shift["id"]


@pytest.mark.parametrize("damage", ["healthy", "spec_binding_absent", "mission_bytes_text"])
def test_gtm_retry_refuses_reused_unreadable_context(next_shift, tmp_path, damage):
    source_path, shift_id = next_shift
    path = copy_database(source_path, tmp_path / "retry.db")
    conn = db.connect(path)
    try:
        failed = orchestrator.start_run(conn, shift_id, executor="local_process",
                                        client_request_id="s24-failed-attempt")
        # The executor's provisioning-failure branch leaves exactly this state.
        repo.update_run(conn, failed.id, RunState.FAILED, ExecutorFailure.PROVISION_FAILED, orchestrator._now())
        conn.commit()
        if damage != "healthy":
            corrupt_retained_binding(conn, failed.context_id, damage)
    finally:
        conn.close()
    with TestClient(create_app(str(path), executor="local_process"), raise_server_exceptions=False) as client:
        retry = client.post(f"/api/shifts/{shift_id}/runs", json={"client_request_id": "s24-retry"})
    conn = db.connect(path)
    try:
        reserved = conn.execute("SELECT context_id FROM runs WHERE client_request_id='s24-retry'").fetchall()
    finally:
        conn.close()
    if damage == "healthy":
        assert retry.status_code == 202, retry.text
        assert [row["context_id"] for row in reserved] == [failed.context_id], "retry did not reuse the frozen context"
        return
    assert retry.status_code == 409, f"retry over an unreadable reused context returned {retry.status_code}"
    assert retry.json()["kind"] == "conflict", retry.text
    assert reserved == [], "refused retry reserved a run"


def test_gtm_unreadable_task_assessment_is_a_typed_conflict(history):
    conn, run, _ = history
    path = conn.execute("PRAGMA database_list").fetchone()[2]
    with TestClient(create_app(path, executor="local_process"), raise_server_exceptions=False) as client:
        healthy = client.get(f"/api/runs/{run.id}/outputs")
        assert healthy.status_code == 200 and healthy.json()[0]["customer_answer"]["display_text"], healthy.text
        conn.execute("UPDATE task_assessments SET reason_codes_json=? WHERE run_id=? AND task_id='owner'",
                     ('["NOT_A_CODE"]', run.id))
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM task_assessments WHERE run_id=? AND reason_codes_json=?",
                            (run.id, '["NOT_A_CODE"]')).fetchone()[0] == 1
        broken = client.get(f"/api/runs/{run.id}/outputs")
    assert broken.status_code == 409, f"unreadable task assessment returned {broken.status_code}"
    assert broken.json()["kind"] == "conflict", broken.text


def test_gtm_unassessed_capture_presents_no_derived_answer(next_shift, tmp_path, monkeypatch):
    source_path, shift_id = next_shift
    path = copy_database(source_path, tmp_path / "unassessed.db")
    # Hold the run between capture and assessment, as an in-flight or failed finalization does.
    monkeypatch.setattr(orchestrator, "finalize_selected_operation",
                        lambda conn, run_id: repo.get_run(conn, run_id))
    with TestClient(create_app(str(path), executor="local_process")) as client:
        started = client.post(f"/api/shifts/{shift_id}/runs", json={"client_request_id": "s24-unassessed"})
        assert started.status_code == 202, started.text
        conn = db.connect(path)
        try:
            run = repo.get_run(conn, started.json()["id"])
            assert run.state is RunState.CAPTURED, run.state
            assert repo.list_task_assessment_models(conn, run.id) == []
            assert b"task_results" in repo.list_outputs(conn, run.id)[0].body, "the service capture is absent"
        finally:
            conn.close()
        outputs = client.get(f"/api/runs/{run.id}/outputs")
    assert outputs.status_code == 200, outputs.text
    answer = outputs.json()[0]["customer_answer"]
    text = (answer or {}).get("display_text") or ""
    assert "rejected by the independent assessment" not in text, "unassessed capture claims an assessment rejection"
    assert "returned no answer" not in text, "unassessed capture claims the service returned no answer"
    assert answer is None, answer


REJECTED = "Some workflow task outputs were rejected by the independent assessment."
NO_ACTION = "No additional owner, record or handoff is required."


@pytest.fixture(scope="module")
def diagnostic_flow(tmp_path_factory):
    """A GTM shift with a real investigation of the pinned starter's failing run."""
    path = tmp_path_factory.mktemp("s24-diagnostic") / "flow.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        flow = gtm.prepare_flow(client, None)
    return path, flow["shift_id"], flow["starter"]["selected_version_id"], flow["investigation_id"]


@pytest.mark.parametrize("missing", [(), ("owner",), ("owner", "write")],
                         ids=["wrong_owner", "missing_owner", "missing_both"])
def test_gtm_diagnostic_text_matches_assessment(diagnostic_flow, tmp_path, monkeypatch, missing):
    source_path, shift_id, starter_id, investigation_id = diagnostic_flow
    path = copy_database(source_path, tmp_path / "diagnostic.db")
    original = LocalProcessAdapter.execute
    async def omit(self, request):
        result = await original(self, request)
        raw = json.loads(result.captures[0].body)
        raw["task_results"] = [row for row in raw["task_results"] if row["task_id"] not in missing]
        return result.model_copy(update={"captures": (
            result.captures[0].model_copy(update={"body": json.dumps(raw).encode()}),)})
    monkeypatch.setattr(LocalProcessAdapter, "execute", omit)
    conn = db.connect(path)
    try:
        experiment = experiments.create_diagnostic_experiment(
            conn, shift_id, candidate_version_id=starter_id, investigation_id=investigation_id,
            client_request_id="s24-diagnostic")
        experiments.execute_experiment(conn, experiments.experiment_run(conn, experiment.id).id)
    finally:
        conn.close()
    with TestClient(create_app(str(path), executor="local_process")) as client:
        view = client.get(f"/api/experiments/{experiment.id}")
        station = client.get(f"/api/shifts/{shift_id}/investigations")
    assert view.status_code == 200 and station.status_code == 200, (view.text, station.text)
    trial = view.json()["trials"][0]
    assert trial["state"] == "COMPLETE", trial["state"]
    rejected = {row["task_id"]: row["reason_codes"] for row in trial["task_assessments"]
                if not row["mandatory_pass"]}
    assert set(rejected) == {"owner", "write"}, rejected
    assert all(rejected[task] == ["REQUIRED_TASK_MISSING"] for task in missing), rejected
    text = trial["customer_text"] or ""
    assert "owner-amer-platform" not in text, "diagnostic text presents a rejected owner"
    assert "record prepared" not in text, "diagnostic text presents a rejected write"
    assert NO_ACTION not in text, "diagnostic text claims no action despite a rejected required task"
    assert REJECTED in text, "diagnostic text omits the rejected required task"
    assert text == "Synthetic qualification: QUALIFIED. " + REJECTED, text
    assert station.json()["latest_diagnostic"]["trials"][0]["customer_text"] == text, \
        "the Investigate station diverges from the experiment view"


def test_gtm_response_task_without_assessment_row_is_rejected(history):
    conn, run, _ = history
    path = conn.execute("PRAGMA database_list").fetchone()[2]
    with TestClient(create_app(path, executor="local_process")) as client:
        healthy = client.get(f"/api/runs/{run.id}/outputs").json()[0]["customer_answer"]["display_text"]
        assert "Synthetic owner: owner-apac-platform." in healthy and REJECTED not in healthy, healthy
        # Partial storage: the response carries the owner task, its assessment row is gone.
        conn.execute("DELETE FROM task_assessments WHERE run_id=? AND task_id='owner'", (run.id,))
        conn.commit()
        text = client.get(f"/api/runs/{run.id}/outputs").json()[0]["customer_answer"]["display_text"]
    assert "Synthetic owner" not in text, "derived text presents an unassessed owner"
    assert NO_ACTION not in text, "an unassessed response task left the no-action assurance"
    assert REJECTED in text, "derived text omits the unassessed response task"


def corrupt_retained_binding(conn, context_id, damage):
    """Persist a retained context that no longer deserializes.

    JSON damages stay valid JSON, which SQLite's json_valid CHECK admits; the
    mission damage stores TEXT where the BLOB column expects bytes, which the
    column affinity admits.
    """
    context = repo.get_execution_context(conn, context_id)
    if damage == "condition_binding_absent":
        value = context.condition.model_dump(mode="json")
        del value["content_hash"]
        conn.execute("UPDATE execution_contexts SET condition_json=? WHERE id=?",
                     (json.dumps(value), context.id))
    elif damage == "mission_bytes_text":
        conn.execute("UPDATE execution_contexts SET mission_bytes=? WHERE id=?", ("not-bytes", context.id))
    else:
        value = [item.model_dump(mode="json") for item in context.workloads]
        if damage == "spec_binding_absent": del value[0]["request_specs_hash"]
        else: value[0]["request_count"] = "corrupted-count"
        conn.execute("UPDATE execution_contexts SET workloads_json=? WHERE id=?",
                     (json.dumps(value), context.id))
    conn.commit()
    stored = conn.execute("SELECT json_valid(workloads_json), json_valid(condition_json), typeof(mission_bytes) "
                          "FROM execution_contexts WHERE id=?", (context.id,)).fetchone()
    assert tuple(stored) == (1, 1, "text" if damage == "mission_bytes_text" else "blob"), \
        "corruption did not persist as intended"
