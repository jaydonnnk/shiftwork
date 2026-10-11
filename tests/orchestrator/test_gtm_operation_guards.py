"""S24 capture provenance and frozen synthetic-history refusal controls."""
import base64
import copy
import json
from types import SimpleNamespace

import pytest

from shiftwork import config, orchestrator
from shiftwork.domain import canonical, task_contract
from shiftwork.domain.errors import PublicStateInvalid
from shiftwork.domain.models import RunPurpose
from shiftwork.ledger import reducer
from tests.orchestrator import test_gtm_pipeline as gtm


@pytest.mark.parametrize("damage", ["extra_check", "duplicate_check", "extra_row",
    "extra_output", "transport", "wrong_request", "wrong_verdict", "assessment_purpose",
    "assessment_run", "foreign_mission", "missing_rules"])
def test_pipeline_reduction_refuses_inconsistent_controller_evidence(damage):
    run, summary, mission, rows, checks, kwargs = gtm.pipeline_reduction_inputs()
    if damage == "extra_check":
        checks += (checks[0].model_copy(update={"check_id": "unrelated-check"}),)
    elif damage == "duplicate_check":
        checks += (checks[0],)
    elif damage == "extra_row":
        rows += (rows[0].model_copy(update={"request_ordinal": 4}),)
    elif damage == "extra_output":
        kwargs["pipeline_outputs"] += (kwargs["pipeline_outputs"][0].model_copy(update={"request_ordinal": 4}),)
    elif damage == "transport":
        kwargs["pipeline_outputs"] = (kwargs["pipeline_outputs"][0].model_copy(update={"transport_error": "failed"}), *kwargs["pipeline_outputs"][1:])
    elif damage == "wrong_request":
        rows = (rows[0].model_copy(update={"request_id": "unrelated-request"}), *rows[1:])
    elif damage == "wrong_verdict":
        checks = (checks[0].model_copy(update={"verdict": "fail"}), *checks[1:])
    elif damage == "assessment_purpose":
        summary = summary.model_copy(update={"purpose": RunPurpose.EXPERIMENT})
    elif damage == "assessment_run":
        summary = summary.model_copy(update={"run_id": "another-run"})
    elif damage == "foreign_mission":
        mission = mission.model_copy(update={"engagement_slug": "northline"})
    else:
        kwargs["consequence_rules"] = None
    with pytest.raises(ValueError):
        reducer.reduce_operation(run, summary, mission, rows, checks, **kwargs)


def test_accepted_pipeline_capture_must_still_parse_as_its_request_envelope():
    args = gtm.pipeline_reduction_inputs()
    kwargs = dict(args[5])
    kwargs["pipeline_outputs"] = (kwargs["pipeline_outputs"][0].model_copy(update={"body": b"{}"}), *kwargs["pipeline_outputs"][1:])
    with pytest.raises(ValueError, match="accepted pipeline capture is not a valid envelope"):
        reducer.reduce_operation(*args[:5], **kwargs)


@pytest.mark.parametrize("damage", ["wrong_ref", "empty_owner", "extra_field", "owner_not_text", "signal_prefix"])
def test_inherited_records_are_validated_even_when_not_in_current_batch(damage):
    raw = (config.PACKAGE_DIR / "fixtures/state/gtm_pipeline_public_state.json").read_bytes()
    record = {"owner": "owner-apac-platform", "record_ref": "pipeline:signal:archived"}
    signal = "signal:archived"
    if damage == "wrong_ref": record["record_ref"] = "pipeline:other"
    elif damage == "empty_owner": record["owner"] = ""
    elif damage == "extra_field": record["sent_message"] = True
    elif damage == "owner_not_text": record["owner"] = 42
    else:
        signal = "archived"
        record["record_ref"] = "pipeline:archived"
    with pytest.raises(PublicStateInvalid, match="invalid inherited pipeline record"):
        task_contract.apply_pipeline_history(raw, {signal: record})


@pytest.mark.parametrize("damage", ["foreign_pack", "history_hash", "boolean_handoff"])
def test_pipeline_rule_resolution_refuses_wrong_owner_or_unbound_history(damage):
    starting = {"consequence_rules": gtm.registry.resolve_pack("gtm").consequences.model_dump(mode="json")}
    mission = copy.deepcopy(gtm.material_json("fixtures/mission/gtm_pipeline_v1.json"))
    if damage == "boolean_handoff": mission["weights"]["handoff"] = True
    context = SimpleNamespace(reducer_version="operation-ledger-v3", engagement_slug="gtm",
        starting_business_state_json=starting, starting_business_state_hash=canonical.content_hash(starting),
        mission_bytes_base64=base64.b64encode(json.dumps(mission).encode()))
    if damage == "foreign_pack": context.engagement_slug = "northline"
    elif damage == "history_hash": context.starting_business_state_hash = "0" * 64
    with pytest.raises(orchestrator.LifecycleError, match="frozen operational consequence rules"):
        orchestrator.operation_consequence_inputs(context)


def test_pipeline_freeze_refuses_broken_chain_before_inheriting(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from shiftwork.app import create_app
    from shiftwork.ledger import chain
    from shiftwork.store import db, repo
    path = tmp_path / "broken-history.db"
    with TestClient(create_app(str(path))) as client:
        opened = client.post("/api/engagements/gtm/shifts")
        assert opened.status_code == 201, opened.text
        conn = db.connect(path)
        try:
            before = tuple(conn.execute("SELECT * FROM execution_contexts"))
            monkeypatch.setattr(chain, "verify_chain", lambda events: chain.ChainStatus.BROKEN)
            with pytest.raises(orchestrator.LifecycleError, match="refusing pipeline inheritance"):
                orchestrator.freeze_diagnostic_context(conn, repo.get_shift(conn, opened.json()["id"]), operation=True)
            assert tuple(conn.execute("SELECT * FROM execution_contexts")) == before
        finally:
            conn.close()


def test_pipeline_freeze_refuses_duplicate_owners_in_valid_chain(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from shiftwork.app import create_app
    from shiftwork.domain.models import LedgerEventDraft, LedgerEventType
    from shiftwork.ledger import chain
    from shiftwork.store import db, repo
    path = tmp_path / "duplicate-history.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        flow = gtm.qualify_gtm(client)
        shift = gtm.gtm_next_shift(client, flow["shift_id"])
        started = client.post(f"/api/shifts/{shift['id']}/runs", json={"client_request_id": "duplicate-owner-baseline"})
        assert started.status_code == 202, started.text
        run = gtm.pivot_flow.wait_run(client, started.json()["id"])
        assert run["state"] == "FINALIZED", run
        conn = db.connect(path)
        try:
            events = repo.list_ledger_events(conn, "gtm")
            assert orchestrator.replay_assessment(conn, run["id"]).status == "IDENTICAL"
            owner = next(event for event in events if event.event_type is LedgerEventType.OWNER_ASSIGNED)
            draft = LedgerEventDraft.model_validate(owner.model_dump(exclude={"seq", "prev_hash", "hash"}))
            duplicate = chain.append([draft], prev_hash=chain.next_prev_hash(events), start_seq=chain.next_seq(events))[0]
            repo.insert_ledger_event(conn, "gtm", duplicate)
            conn.commit()
            events = repo.list_ledger_events(conn, "gtm")
            assert chain.verify_chain(events) is chain.ChainStatus.VALID
            # Isolate the earlier owner-cardinality check. The later semantic
            # verifier independently rejects this same duplicate. Its complete
            # consequence/provenance cases remain in test_gtm_review_repairs.py.
            monkeypatch.setattr(orchestrator, "_verify_pipeline_history", lambda *args: None)
            before = tuple(conn.execute("SELECT * FROM execution_contexts"))
            with pytest.raises(orchestrator.LifecycleError, match="duplicate owner"):
                orchestrator.freeze_diagnostic_context(conn, repo.get_shift(conn, shift["id"]), operation=True)
            assert tuple(conn.execute("SELECT * FROM execution_contexts")) == before
            assert repo.list_ledger_events(conn, "gtm") == events
        finally:
            conn.close()



def test_gtm_finalized_operation_guard_precedes_retry_and_storage(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from shiftwork.app import create_app
    from shiftwork.store import db, repo
    path = tmp_path / "one-operation.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        flow = gtm.prepare_flow(client, monkeypatch)
        conn = db.connect(path)
        try:
            shift = repo.get_shift(conn, flow["shift_id"])
            selection, version = orchestrator._selected_operating_version(conn, shift)
            previous = repo.get_run(conn, flow["source_run"]["id"])
            context = repo.get_execution_context(conn, previous.context_id)
            before = gtm.business_rows(conn)
            # Neutralize only later retry checks to isolate the finalized-run guard.
            # Reserve directly, so the storage finalization constraint cannot catch it.
            monkeypatch.setattr(repo, "list_outputs", lambda *args: [])
            monkeypatch.setattr(repo, "list_ledger_events", lambda *args: [])
            monkeypatch.setattr(orchestrator, "freeze_diagnostic_context", lambda *args, **kwargs: context)
            with pytest.raises(orchestrator.LifecycleError, match="one successful operation"):
                orchestrator._reserve_selected_operation(conn, shift, selection, version,
                    "s24-independent-second-operation", adapter="local_process")
            assert gtm.business_rows(conn) == before
        finally:
            conn.rollback()
            conn.close()


def test_later_gtm_comparison_refuses_unbound_ownership_history(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from shiftwork import comparison_flow
    from shiftwork.app import create_app
    from shiftwork.store import db, repo
    from tests.packs.material import staged_material
    path = tmp_path / "unbound-later-history.db"
    with TestClient(create_app(str(path), executor="local_process")) as client:
        flow = gtm.qualify_gtm(client)
        successor = gtm.gtm_next_shift(client, flow["shift_id"])
        world = gtm.material_json("fixtures/state/gtm_compare_state_v1.json")
        world["dependencies"]["enrichment"] = "unavailable"
        with staged_material(monkeypatch, tmp_path / "synthetic-outage", {
                "fixtures/state/gtm_pipeline_public_state.json": json.dumps(world).encode()}):
            started = client.post(f"/api/shifts/{successor['id']}/runs", json={"client_request_id": "unbound-observation"})
            assert started.status_code == 202, started.text
            run = gtm.pivot_flow.wait_run(client, started.json()["id"])
            assert run["state"] == "FINALIZED", run
        conn = db.connect(path)
        try:
            before = gtm.pivot_flow.snapshot_rows(conn)
            observed = repo.get_execution_context(conn, repo.get_run(conn, run["id"]).context_id)
            get_context = repo.get_execution_context
            monkeypatch.setattr(repo, "get_execution_context", lambda connection, context_id:
                observed.model_copy(update={"starting_business_state_hash": "0" * 64})
                if context_id == observed.id else get_context(connection, context_id))
            with pytest.raises(orchestrator.LifecycleError, match="observed pipeline history differs"):
                comparison_flow.create_later_condition_comparison(conn, successor["id"], operation_run_id=run["id"],
                    declared_treatment="Unbound history must not reserve a comparison.", client_request_id="s24-unbound-history")
            gtm.pivot_flow.assert_prefix_unchanged(conn, before)
        finally:
            conn.close()
