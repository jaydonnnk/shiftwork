"""Exact approved correction, frozen historical loading and never-reuse proofs."""

import base64
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from shiftwork import comparison_flow, config, orchestrator
from shiftwork.app import create_app
from shiftwork.domain import task_contract as tc
from shiftwork.domain.comparison import validate_acceptance_aspect
from shiftwork.domain.errors import RotationUnavailable
from shiftwork.domain.models import DrawState, ExposureItem, ExposureReservation
from shiftwork.evaluator import evaluator
from shiftwork.executor.deployment import DeploymentKernel, derive_intent_key
from shiftwork.packs import registry
from shiftwork.sealed import rotation, store
from shiftwork.store import db, repo


V1 = "sealed/cases/northline_deployment.json"
V2 = "sealed/cases/northline_deployment_v2.json"
V1_HASH = "d2f67e0655267698c3ac78458502d5e7e2aa582dfcf0755fcf9f348a4f6d04d6"
V2_HASH = "c1f3c8d3369b6eeca61f8fba8a4ab4829a248a9887e14c4257d5b30a6ab56798"
V2_SEAL = "31cab9afaeed92d6421a045f49b33ae48079ef08ca2a682f7cc6b4a9647fbcfe"


def families():
    old = json.loads((config.PACKAGE_DIR / V1).read_bytes())
    new = json.loads((config.PACKAGE_DIR / V2).read_bytes())
    return tuple(store._parse_family("deployment", raw, comparison_family=True, slug="northline")
                 for raw in (old, new))


def test_exact_v2_packet_pin_seal_declaration_and_original_are_bound():
    pack = orchestrator.admit_pack("northline")
    assert len(pack.families) == 1 and pack.families[0].case_file == V2
    assert pack.families[0].cycle == 1
    pins = {p.path: p.sha256 for p in pack.reviewed_pins}
    assert len(pins) == 25 and pins[V1] == V1_HASH and pins[V2] == V2_HASH
    for path, digest in ((V1, V1_HASH), (V2, V2_HASH)):
        raw = (config.PACKAGE_DIR / path).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
    raw = (config.PACKAGE_DIR / V2).read_bytes()
    assert len(raw) == 18847
    data = json.loads(raw)
    assert data["review_status"] == "OPERATOR_SEALED"
    assert data["sealed_payload_sha256"] == V2_SEAL
    assert hashlib.sha256(json.dumps(data["cases"], sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode()).hexdigest() == V2_SEAL
    attributes = (config.PACKAGE_DIR.parent / ".gitattributes").read_text()
    assert "shiftwork/" + V1 + " -text" in attributes.splitlines()
    assert "shiftwork/" + V2 + " -text" in attributes.splitlines()


def test_only_variant_two_request_and_spec_text_change_and_all_other_bindings_survive():
    old, new = families()
    assert store.load_declared_family(registry.resolve_pack("northline").families[0], slug="northline") == new
    assert len(old.cases) == len(new.cases) == 6
    state = (config.PACKAGE_DIR / registry.resolve_pack("northline").comparison_state_path).read_bytes()
    for index, (before, after) in enumerate(zip(old.cases, new.cases, strict=True)):
        assert validate_acceptance_aspect(before, engagement_slug="northline") == validate_acceptance_aspect(after, engagement_slug="northline")
        assert evaluator.expected_ref_for(before) == evaluator.expected_ref_for(after)
        assert tc.resolve_protected_state(state, before.stimulus.state_delta) == tc.resolve_protected_state(state, after.stimulus.state_delta)
        row, spec = after.stimulus.request, after.stimulus.task_spec
        assert row.request_id == spec.id and row.text == spec.text and row.ordinal == 3
        if index == 1:
            expected = before.model_dump(mode="json")
            expected["stimulus"]["request"]["text"] = row.text
            expected["stimulus"]["task_spec"]["text"] = row.text
            assert before.stimulus.request.text != row.text
            assert expected == after.model_dump(mode="json")
            assert rotation.variant_ref(before) != rotation.variant_ref(after)
        else:
            assert before == after
            assert rotation.variant_ref(before) == rotation.variant_ref(after)


def test_no_write_retry_uses_received_reference_and_rejects_changed_ref_or_new_write():
    _, new = families()
    case = new.cases[1]
    received = json.loads(tc.protected_request_bytes(case.stimulus.request))
    # Generic extraction from customer prose; expected conditions are assessor-only.
    reference = re.search(r"existing stable commitment reference is ([A-Za-z0-9_-]+)\.", received["text"]).group(1)
    intent = derive_intent_key(received["request_id"], received["text"])
    pack = registry.resolve_pack("northline")
    state = tc.resolve_protected_state((config.PACKAGE_DIR / pack.comparison_state_path).read_bytes(), case.stimulus.state_delta)
    kernel = DeploymentKernel(state, {"run_id": "retry-input", "context_hash": "0" * 64,
        "artifact_hash": "1" * 64, "state_hash": hashlib.sha256(state).hexdigest(),
        "batch_hash": "2" * 64, "phase": "PROTECTED", "allowed_resources": ["repair_slots"]})
    token = "request-token-" + "x" * 64
    body = tc.protected_request_bytes(case.stimulus.request)
    kernel.begin(3, body, token)
    answer = tc.ServiceResponse(request_id=received["request_id"], task_results=(tc.TaskResult(
        task_id="booking", status="COMPLETED", entity_ref=received["entity_ref"], claims=(), commitment_ref=reference),),
        evidence_refs=(), uncertainty_codes=())
    trace = tc.DeploymentTrace.model_validate(kernel.finish(answer.model_dump_json().encode()))
    mission = tc.load_mission(config.PACKAGE_DIR / pack.mission_path)
    def assess(output, observed):
        return evaluator.assess_request(spec=case.stimulus.task_spec, request_ordinal=3, mission=mission,
            snapshot=tc.load_public_state_bytes(state), response=output, deployment_trace=observed)[0]
    assert assess(answer, trace).mandatory_pass and not kernel.writes
    changed = answer.model_copy(update={"task_results": (answer.task_results[0].model_copy(update={"commitment_ref": reference + "-wrong"}),)})
    assert not assess(changed, trace).mandatory_pass
    kernel.begin(3, body, token)
    kernel.act(token, {"operation": "WRITE_SLOT", "resource": "repair_slots", "entity_ref": received["entity_ref"],
        "part_ref": "part:brake-pad", "booking_date": "2026-10-04", "stage": "FINAL", "intent_key": intent,
        "commitment_ref": reference})
    duplicate = tc.DeploymentTrace.model_validate(kernel.finish(answer.model_dump_json().encode()))
    assert not assess(answer, duplicate).mandatory_pass
    assert len(kernel.writes) == 1, "write fault never executed"


@pytest.mark.parametrize("state", [DrawState.ACTIVE, DrawState.INVALIDATED])
def test_v1_snapshots_replay_after_v2_admission_with_zero_writes_and_no_inventory_reuse(tmp_path, monkeypatch, state):
    old, new = families()
    pack = orchestrator.admit_pack("northline")
    source_state = (config.PACKAGE_DIR / pack.comparison_state_path).read_bytes()
    conn = db.connect(tmp_path / "historical.db")
    try:
        db.ensure_schema(conn)
        orchestrator.seed_registered_engagements(conn)
        now = datetime.now(timezone.utc)
        for reservation_id in ("historical-v1-1", "historical-v1-2", "reuse-control"):
            repo.insert_exposure_reservation(conn, ExposureReservation(id=reservation_id, engagement_slug="northline",
                scope="comparison", experiment_id=None, state="ACTIVE" if state is DrawState.ACTIVE else "INVALIDATED", created_at=now))
        for index, case in enumerate(old.cases, 1):
            ref = rotation.variant_ref(case)
            item = ExposureItem(id=f"v1-case-{index}", reservation_id=f"historical-v1-{1 if index <= 3 else 2}", engagement_slug="northline",
                family="deployment", cycle=1, variant_ref=ref, pair_ordinal=(index - 1) % 3 + 1, state=state, drawn_at=now)
            repo.insert_exposure_item(conn, item)
            payload = case.model_dump_json()
            resolved = tc.resolve_protected_state(source_state, case.stimulus.state_delta)
            repo.insert_protected_case_snapshot(conn, item.id, ref, payload, hashlib.sha256(payload.encode()).hexdigest(),
                resolved, hashlib.sha256(resolved).hexdigest())
        conn.commit()
        def snapshot():
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {t: tuple(tuple(r) for r in conn.execute('SELECT * FROM "' + t + '" ORDER BY rowid')) for t in tables}
        before, changes = snapshot(), conn.total_changes
        monkeypatch.setattr(store, "load_family", lambda *a, **k: pytest.fail("historical replay consulted current inventory"))
        replayed = (*store.load_reserved_comparison_cases(conn, "historical-v1-1"),
                    *store.load_reserved_comparison_cases(conn, "historical-v1-2"))
        assert tuple(row.case for row in replayed) == old.cases
        assert replayed[1].case.stimulus.request.text != new.cases[1].stimulus.request.text
        for row in replayed:
            assert row.resolved_state_bytes == tc.resolve_protected_state(source_state, row.case.stimulus.state_delta)
        spent = comparison_flow._exposure_refs(conn, "northline", "deployment")
        assert spent == {rotation.variant_ref(case) for case in old.cases}
        assert rotation.unexposed_cases(new.cases, spent) == (new.cases[1],)
        with pytest.raises(RotationUnavailable):
            rotation.select_pair_variants("deployment", new.cases, spent)
        assert snapshot() == before and conn.total_changes == changes, "replay or refusal changed historical bytes"
        # The storage uniqueness guard also retains historical exposure after invalidation.
        with pytest.raises(sqlite3.IntegrityError, match="engagement_slug.*family.*cycle.*variant_ref"):
            repo.insert_exposure_item(conn, item.model_copy(update={"id": "reused-history", "reservation_id": "reuse-control"}))
        conn.rollback()
        assert snapshot() == before
    finally:
        conn.close()


@pytest.mark.parametrize("version", [V1, V2])
def test_old_and_new_retry_text_detected_on_serialized_public_surfaces(version):
    data = json.loads((config.PACKAGE_DIR / version).read_bytes())
    needle = data["cases"][1]["stimulus"]["request"]["text"]
    surfaces = (json.dumps({"detail": needle}), json.dumps(json.dumps({"detail": needle})),
                json.dumps({"base64": base64.b64encode(needle.encode()).decode()}))
    assert needle in orchestrator._private_public_needles()
    for surface in surfaces:
        with pytest.raises(orchestrator.LifecycleError, match="private material"):
            orchestrator.assert_public_projection(surface)


def test_public_protocol_is_served_and_linked_before_candidate_editing(tmp_path):
    with TestClient(create_app(str(tmp_path / "protocol.db"))) as client:
        index = client.get("/")
        assert index.status_code == 200
        assert index.text.index('id="deployment-protocol"') < index.text.index('id="draft-source"')
        assert 'href="/northline-deployment-protocol.html"' in index.text
        protocol = client.get("/northline-deployment-protocol.html")
        assert protocol.status_code == 200
        for phrase in ("X-Shiftwork-Intent-Key", "counter intent TOKEN", "visit V-11", "northline-intent-V11",
                       "request_id", "256", "WRITE_SLOT", "commitment_ref", "evidence_refs", "provisional"):
            assert phrase in protocol.text
        orchestrator.assert_public_projection(protocol.text)
