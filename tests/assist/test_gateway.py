"""S14 assistance through the real API, controller and SQLite store.

The model is a recorded double. These checks authorize no provider call.
"""

import json
import sqlite3
import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from shiftwork.app import create_app
from shiftwork.assist.gateway import (
    AssistRejected,
    AssistReply,
    DEADLINE_S,
    LiveAssistGateway,
    PROVIDER_URL,
)
import shiftwork.assist.gateway as assist_gateway_module
from shiftwork.domain.models import AssistRole
from shiftwork import orchestrator
from shiftwork.packs import registry
from shiftwork.store import db, repo


class RecordedGateway:
    model_id = "recorded-assist-double"
    def __init__(self, replies=None):
        self.calls = []
        self.replies = iter(replies or [])

    def generate(self, *, model_id, role, prompt):
        self.calls.append((model_id, role.value, prompt))
        default = (json.dumps({"old": "import json", "new": "# Coach test proposal\nimport json"})
                   if role is AssistRole.PATCH_PROPOSAL else "Check the collection task against your public test.")
        reply = next(self.replies, AssistReply(default, output_tokens=20))
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture()
def session(tmp_path):
    path = tmp_path / "assist.db"
    gateway = RecordedGateway()
    with TestClient(create_app(str(path), assist_gateway=gateway)) as client:
        shift = client.post("/api/engagements/bookshop/shifts").json()
        run = client.post(f"/api/shifts/{shift['id']}/runs")
        assert run.status_code == 202, run.text
        assert client.get(f"/api/runs/{run.json()['id']}/outputs").json()
        yield client, path, shift["id"], run.json()["id"], gateway


def entry(client, shift_id, run_id, **fields):
    body = dict(source_run_id=run_id, source_request_ordinal=1,
                cause="The router answered price only.",
                falsifier="A request without a price question still omits collection.",
                public_test="Check every required task in the public request.",
                client_request_id="first-investigation")
    body.update(fields)
    return client.post(f"/api/shifts/{shift_id}/investigations", json=body)


def assist(client, shift_id, investigation_id, role="HINT", request_id="help-1", **fields):
    body = dict(investigation_id=investigation_id, role=role,
                message="What evidence should I check?", client_request_id=request_id)
    body.update(fields)
    return client.post(f"/api/shifts/{shift_id}/assist", json=body)


@pytest.mark.parametrize("missing", ["cause", "falsifier", "public_test"])
def test_diagnostic_help_requires_every_learner_commitment_field(session, missing):
    client, _, shift_id, run_id, gateway = session
    assert assist(client, shift_id, None).status_code == 409
    assert entry(client, shift_id, run_id, **{missing: " "}).status_code == 409
    assert gateway.calls == []
    view = client.get(f"/api/shifts/{shift_id}/investigations").json()
    assert view["assist_used"] == 0
    assert view["orientation"]["source"] == "deterministic_copy"


def test_mixed_role_budget_patch_cap_and_idempotency(session):
    client, path, shift_id, run_id, gateway = session
    investigation_id = entry(client, shift_id, run_id).json()["id"]
    conn = db.connect(path)
    try:
        before = tuple(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in
                       ("artifact_versions", "experiments", "check_results", "operating_selections", "ledger_events"))
    finally:
        conn.close()
    first = assist(client, shift_id, investigation_id).json()
    assert first["state"] == "COMPLETE"
    assert first["role"] == "HINT"
    assert first["model_id"] == "recorded-assist-double"
    assert "Learner cause:" in first["request_text"]
    assert "Observed service response:" in first["request_text"]
    assert "Do you still have the hardback of Dune on the shelf?" in first["request_text"]
    assert len(gateway.calls) == 1
    assert assist(client, shift_id, investigation_id).json()["id"] == first["id"]
    assert len(gateway.calls) == 1
    patch = assist(client, shift_id, investigation_id, "PATCH_PROPOSAL", "help-2").json()
    assert patch["proposed_patch"] == patch["response_text"]
    assert patch["accepted"] is None
    assert assist(client, shift_id, investigation_id, "PATCH_PROPOSAL", "help-3").status_code == 409
    assert assist(client, shift_id, investigation_id, "DIAGNOSIS", "help-3").status_code == 200
    assert assist(client, shift_id, investigation_id, "HINT", "help-4").status_code == 409
    assert len(gateway.calls) == 3
    view = client.get(f"/api/shifts/{shift_id}/investigations").json()
    assert (view["assist_used"], view["assist_limit"], view["assist_available"]) == (3, 3, False)
    accepted = client.post(f"/api/assist-events/{patch['id']}/decision", json={"accepted": True})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["accepted"] is True
    assert client.post(f"/api/assist-events/{first['id']}/decision", json={"accepted": False}).json()["accepted"] is False
    assert client.post(f"/api/assist-events/{patch['id']}/decision", json={"accepted": False}).status_code == 409
    conn = db.connect(path)
    try:
        after = tuple(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in
                      ("artifact_versions", "experiments", "check_results", "operating_selections", "ledger_events"))
        assert after == before, "help decisions must not edit, freeze, grade, select or write business history"
        assert conn.execute("SELECT total_assist_budget_per_shift FROM engagement_assist_policy "
                            "WHERE slug = 'bookshop'").fetchone()[0] == 3
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE assist_events SET request_text = 'rewritten' WHERE id = ?", (patch["id"],))
        conn.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="cannot be deleted"):
            conn.execute("DELETE FROM assist_events WHERE id = ?", (patch["id"],))
    finally:
        conn.close()


def test_failed_call_consumes_budget_without_raw_error_or_private_output(tmp_path, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "S14_PRIVATE_TOKEN_NEVER_PUBLIC")
    gateway = RecordedGateway([AssistRejected("ASSIST_TRANSPORT_FAILED"),
                               AssistReply("S14_PRIVATE_TOKEN_NEVER_PUBLIC", output_tokens=5)])
    with TestClient(create_app(str(tmp_path / "fail.db"), assist_gateway=gateway)) as client:
        shift_id = client.post("/api/engagements/bookshop/shifts").json()["id"]
        run_id = client.post(f"/api/shifts/{shift_id}/runs").json()["id"]
        investigation_id = entry(client, shift_id, run_id).json()["id"]
        first_response = assist(client, shift_id, investigation_id)
        second_response = assist(client, shift_id, investigation_id, request_id="help-2")
        assert first_response.status_code == 200, first_response.text
        assert second_response.status_code == 200, second_response.text
        first = first_response.json()
        second = second_response.json()
        assert first["failure_code"] == "ASSIST_TRANSPORT_FAILED"
        assert second["failure_code"] == "ASSIST_PRIVATE_OUTPUT"
        third = assist(client, shift_id, investigation_id, request_id="help-3").json()
        assert third["state"] == "COMPLETE"
        assert assist(client, shift_id, investigation_id, request_id="help-4").status_code == 409
        assert all(event["state"] == "FAILED" and not event["response_text"]
                   for event in (first, second))
        view = client.get(f"/api/shifts/{shift_id}/investigations").json()
        assert view["assist_used"] == 3
        assert "S14_PRIVATE_TOKEN_NEVER_PUBLIC" not in json.dumps(view)
        assert "S14_PRIVATE_TOKEN_NEVER_PUBLIC" not in json.dumps(first)
        assert "S14_PRIVATE_TOKEN_NEVER_PUBLIC" not in json.dumps(second)


def test_live_gateway_request_is_bounded_and_sends_no_controller_capabilities():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"model": "served-test-model",
                                          "choices": [{"message": {"content": "Try the public test."}}],
                                          "usage": {"prompt_tokens": 12, "completion_tokens": 6}})

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        reply = LiveAssistGateway("LOCAL_TEST_TOKEN", http=http).generate(
            model_id="test-model", role=AssistRole.HINT, prompt="Role: HINT\nLearner cause: routing")
    assert reply.text == "Try the public test."
    assert (reply.reported_model_id, reply.input_tokens, reply.output_tokens) == ("served-test-model", 12, 6)
    assert isinstance(reply.elapsed_ms, int)
    assert len(requests) == 1
    assert str(requests[0].url) == PROVIDER_URL
    assert requests[0].headers["Authorization"] == "Bearer LOCAL_TEST_TOKEN"
    body = json.loads(requests[0].content)
    assert body["max_tokens"] == 1024
    assert "Treat the learner cause as a hypothesis" in body["messages"][0]["content"]
    assert "service repair" in body["messages"][0]["content"]
    assert "LOCAL_TEST_TOKEN" not in json.dumps(body)
    assert not any(word in json.dumps(body).lower() for word in ("sealed/cases", "expected_ref", "promotion_token"))

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        with pytest.raises(AssistRejected, match="ASSIST_ROLE_INVALID"):
            LiveAssistGateway("LOCAL_TEST_TOKEN", http=http).generate(
                model_id="test-model", role="HINT", prompt="Role: HINT")
    assert len(requests) == 1, "invalid role must fail before transport"


def test_live_transport_has_an_absolute_call_deadline(monkeypatch):
    calls = []
    original_async_client = httpx.AsyncClient

    async def slow_response(request):
        calls.append(request)
        await asyncio.sleep(0.05)
        return httpx.Response(200, json={"choices": [{"message": {"content": "too late"}}]})

    def async_client(*args, **kwargs):
        return original_async_client(transport=httpx.MockTransport(slow_response), **kwargs)

    def wrong_sync_client(*args, **kwargs):
        raise AssertionError("the live gateway must use the bounded async transport")

    monkeypatch.setattr(assist_gateway_module, "DEADLINE_S", 0.01)
    monkeypatch.setattr(assist_gateway_module.httpx, "AsyncClient", async_client)
    monkeypatch.setattr(assist_gateway_module.httpx, "Client", wrong_sync_client)
    with pytest.raises(AssistRejected, match="ASSIST_TRANSPORT_FAILED"):
        LiveAssistGateway("LOCAL_TEST_TOKEN").generate(
            model_id="test-model", role=AssistRole.HINT, prompt="Role: HINT"
        )
    assert len(calls) == 1


def test_live_transport_returns_response_under_deadline(monkeypatch):
    calls = []
    original_async_client = httpx.AsyncClient

    async def reply(request):
        calls.append(request)
        return httpx.Response(200, json={
            "model": "served-test-model",
            "choices": [{"message": {"content": "Check the observed response."}}],
            "usage": {"prompt_tokens": 15, "completion_tokens": 6},
        })

    def async_client(*args, **kwargs):
        return original_async_client(transport=httpx.MockTransport(reply), **kwargs)

    monkeypatch.setattr(assist_gateway_module.httpx, "AsyncClient", async_client)
    result = LiveAssistGateway("LOCAL_TEST_TOKEN").generate(
        model_id="test-model", role=AssistRole.HINT, prompt="Role: HINT"
    )
    assert result.text == "Check the observed response."
    assert (result.reported_model_id, result.input_tokens, result.output_tokens) == (
        "served-test-model", 15, 6
    )
    assert len(calls) == 1


def test_injected_client_cannot_bypass_the_call_deadline():
    """S14 review repair: an injected test/demo client carries the same bounded
    per-request timeout, so only the default path's absolute wrapper is unique."""
    seen = {}

    def respond(request):
        seen["timeout"] = request.extensions.get("timeout")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        reply = LiveAssistGateway("LOCAL_TEST_TOKEN", http=http).generate(
            model_id="test-model", role=AssistRole.HINT, prompt="Role: HINT")
    assert reply.text == "ok"
    assert seen["timeout"] == {"connect": DEADLINE_S, "read": DEADLINE_S,
                               "write": DEADLINE_S, "pool": DEADLINE_S}


def test_injected_client_timeout_is_a_safe_transport_failure():
    """The bounded injected path surfaces a real client timeout as the safe code,
    never as a raw transport error or a partial reply."""

    def hang(request):
        raise httpx.ReadTimeout("simulated read timeout", request=request)

    with httpx.Client(transport=httpx.MockTransport(hang)) as http:
        with pytest.raises(AssistRejected, match="ASSIST_TRANSPORT_FAILED"):
            LiveAssistGateway("LOCAL_TEST_TOKEN", http=http).generate(
                model_id="test-model", role=AssistRole.HINT, prompt="Role: HINT")


def test_private_source_response_is_refused_before_gateway_call(session, monkeypatch):
    client, _, shift_id, run_id, gateway = session
    investigation_id = entry(client, shift_id, run_id).json()["id"]
    real_list = orchestrator.repo.list_outputs

    def private_output(conn, source_run_id):
        outputs = real_list(conn, source_run_id)
        return [row.model_copy(update={"body": b"S14_PRIVATE_SOURCE_SENTINEL"})
                for row in outputs]

    monkeypatch.setattr(orchestrator.repo, "list_outputs", private_output)
    monkeypatch.setenv("NEBIUS_API_KEY", "S14_PRIVATE_SOURCE_SENTINEL")
    with pytest.raises(ValueError):
        orchestrator.assert_public_safe(
            {"prompt": "S14_PRIVATE_SOURCE_SENTINEL"}, orchestrator._private_public_needles()
        )
    response = assist(client, shift_id, investigation_id)
    assert response.status_code == 409
    assert gateway.calls == []
    assert "S14_PRIVATE_SOURCE_SENTINEL" not in response.text


def test_system_plus_prompt_limit_refuses_before_reserving_budget(session):
    client, _, shift_id, run_id, gateway = session
    investigation = entry(client, shift_id, run_id, cause="C" * 1850,
                          falsifier="F" * 1850, public_test="T" * 1850)
    assert investigation.status_code == 201
    response = assist(client, shift_id, investigation.json()["id"], message="Q" * 1850)
    assert response.status_code == 409
    assert gateway.calls == []
    assert client.get(f"/api/shifts/{shift_id}/investigations").json()["assist_used"] == 0


def test_unreviewed_northline_refuses_help_before_gateway(session, monkeypatch):
    packs = registry.registered_packs()
    monkeypatch.setattr(registry, "_PACKS", (*packs[:2], packs[2].model_copy(update={"reviewed_pins": ()})))
    client, path, shift_id, run_id, gateway = session
    investigation_id = entry(client, shift_id, run_id).json()["id"]
    conn = db.connect(path)
    try:
        assert repo.get_engagement(conn, "northline") is not None
        conn.execute("UPDATE shifts SET engagement_slug = 'northline' WHERE id = ?", (shift_id,))
        policy = registry.resolve_pack("northline").assist
        repo.seed_engagement_config(conn, "northline", business_kind="northline",
                                    assist_level=policy.level_label,
                                    allowed_assist_roles=tuple(role.value for role in policy.allowed_roles),
                                    total_assist_budget_per_shift=policy.total_calls_per_shift,
                                    enabled_check_families=(), attempt_limit=2, rotation_group_size=6)
        repo.seed_engagement_assist_policy(conn, "northline", assist_level=policy.level_label,
                                          allowed_assist_roles=tuple(role.value for role in policy.allowed_roles),
                                          total_assist_budget_per_shift=policy.total_calls_per_shift)
        conn.commit()
    finally:
        conn.close()
    assert assist(client, shift_id, investigation_id, "DIAGNOSIS").status_code == 409
    assert assist(client, shift_id, investigation_id, "PATCH_PROPOSAL").status_code == 409
    assert assist(client, shift_id, investigation_id, "HINT").status_code == 409
    assert assist(client, shift_id, investigation_id, "HINT", "help-2").status_code == 409
    assert gateway.calls == []


def install_policy(monkeypatch, path, policy):
    """Exercise declared levels on reviewed Bellwether test material only.

    This does not admit Northline/GTM material or claim a board journey.
    """
    bookshop = registry.resolve_pack("bookshop").model_copy(update={"assist": policy})
    monkeypatch.setattr(registry, "_PACKS", (bookshop, *registry.registered_packs()[1:]))
    conn = db.connect(path)
    try:
        conn.execute("UPDATE engagement_assist_policy SET assist_level = ?, allowed_assist_roles_json = ?, "
                     "total_assist_budget_per_shift = ? WHERE slug = 'bookshop'",
                     (policy.level_label, json.dumps([role.value for role in policy.allowed_roles]),
                      policy.total_calls_per_shift))
        conn.commit()
    finally:
        conn.close()


@pytest.mark.parametrize("policy_slug", ("bookshop", "gtm", "northline"))
def test_assist_policy_is_declared_per_pack(session, monkeypatch, policy_slug):
    client, path, shift_id, run_id, gateway = session
    investigation_id = entry(client, shift_id, run_id).json()["id"]
    policy = registry.resolve_pack(policy_slug).assist
    install_policy(monkeypatch, path, policy)
    for role in set(AssistRole) - set(policy.allowed_roles):
        refused = assist(client, shift_id, investigation_id, role.value, f"deny-{role.value}")
        assert refused.status_code == 409, "an undeclared role reached the assist gateway"
    assert gateway.calls == []
    for ordinal in range(policy.total_calls_per_shift):
        role = policy.allowed_roles[ordinal % len(policy.allowed_roles)]
        response = assist(client, shift_id, investigation_id, role.value, f"allowed-{ordinal}")
        assert response.status_code == 200, response.text
    refused = assist(client, shift_id, investigation_id, "HINT", "over-budget")
    assert refused.status_code == 409, "the pack's shared assistance budget was widened"
    assert len(gateway.calls) == policy.total_calls_per_shift
    view = client.get(f"/api/shifts/{shift_id}/investigations").json()
    assert view["assist_limit"] == policy.total_calls_per_shift
    assert view["assist_used"] == policy.total_calls_per_shift
    assert view["assist_available"] is False
    assert view["assist_allowed_roles"] == [role.value for role in policy.allowed_roles]


@pytest.mark.parametrize("field,value", (
    ("assist_level", "widened"),
    ("allowed_assist_roles_json", '["HINT"]'),
    ("total_assist_budget_per_shift", 9),
    ("allowed_assist_roles_json", "malformed-json"),
))
def test_assist_projection_mismatch_refuses_route_view_and_startup(session, field, value):
    client, path, shift_id, run_id, gateway = session
    investigation_id = entry(client, shift_id, run_id).json()["id"]
    conn = db.connect(path)
    try:
        conn.execute(f"UPDATE engagement_assist_policy SET {field} = ? WHERE slug = 'bookshop'", (value,))
        conn.commit()
        before = conn.execute("SELECT * FROM engagement_assist_policy WHERE slug = 'bookshop'").fetchone()
        before = tuple(before)
    finally:
        conn.close()
    assert assist(client, shift_id, investigation_id).status_code == 409, "mismatched projection allowed a call"
    assert client.get(f"/api/shifts/{shift_id}/investigations").status_code == 409
    assert gateway.calls == []
    with pytest.raises(orchestrator.LifecycleError, match="assist policy projection"):
        with TestClient(create_app(str(path), assist_gateway=gateway)):
            pass
    conn = db.connect(path)
    try:
        assert tuple(conn.execute("SELECT * FROM engagement_assist_policy WHERE slug = 'bookshop'").fetchone()) == before
        assert conn.execute("SELECT COUNT(*) FROM assist_events").fetchone()[0] == 0
    finally:
        conn.close()


def test_patch_limit_comes_from_declaration(session, monkeypatch):
    client, path, shift_id, run_id, gateway = session
    investigation_id = entry(client, shift_id, run_id).json()["id"]
    policy = registry.resolve_pack("bookshop").assist.model_copy(update={"max_patch_proposals": 0})
    install_policy(monkeypatch, path, policy)
    response = assist(client, shift_id, investigation_id, "PATCH_PROPOSAL")
    assert response.status_code == 409, "zero declared patch proposals allowed a model call"
    assert gateway.calls == []


def test_disallowed_diagnosis_is_refused_before_gateway(session, monkeypatch):
    client, path, shift_id, run_id, gateway = session
    investigation_id = entry(client, shift_id, run_id).json()["id"]
    install_policy(monkeypatch, path, registry.resolve_pack("northline").assist)
    response = assist(client, shift_id, investigation_id, "DIAGNOSIS")
    assert response.status_code == 409, "undeclared diagnosis reached the gateway"
    assert gateway.calls == []


def test_failed_help_consumes_the_declared_reduced_budget(session, monkeypatch):
    client, path, shift_id, run_id, gateway = session
    investigation_id = entry(client, shift_id, run_id).json()["id"]
    install_policy(monkeypatch, path, registry.resolve_pack("northline").assist)
    gateway.replies = iter([AssistRejected("ASSIST_TRANSPORT_FAILED")])
    first = assist(client, shift_id, investigation_id).json()
    assert first["state"] == "FAILED"
    assert assist(client, shift_id, investigation_id, request_id="after-failure").status_code == 409
    assert len(gateway.calls) == 1


def test_startup_seeds_declared_policy_idempotently(tmp_path, monkeypatch):
    policy = registry.resolve_pack("gtm").assist
    bookshop = registry.resolve_pack("bookshop").model_copy(update={"assist": policy})
    packs = registry.registered_packs()
    monkeypatch.setattr(registry, "_PACKS", (bookshop, *(pack.model_copy(update={"reviewed_pins": ()}) for pack in packs[1:])))
    path = tmp_path / "declared-policy.db"
    for _ in range(2):
        startup_failure = None
        try:
            with TestClient(create_app(str(path))):
                pass
        except orchestrator.LifecycleError as error:
            startup_failure = error
        assert startup_failure is None, "startup failed to seed the declared assistance projection"
        conn = db.connect(path)
        try:
            row = repo.get_engagement_assist_policy(conn, "bookshop")
            assert row["assist_level"] == policy.level_label
            assert json.loads(row["allowed_assist_roles_json"]) == [role.value for role in policy.allowed_roles]
            assert row["total_assist_budget_per_shift"] == policy.total_calls_per_shift
            assert [row["slug"] for row in conn.execute("SELECT slug FROM engagements")] == ["bookshop"]
            assert conn.execute("SELECT COUNT(*) FROM engagement_assist_policy").fetchone()[0] == 1
        finally:
            conn.close()


def test_missing_current_projection_refuses_help_and_view_without_historical_fallback(session):
    client, path, shift_id, run_id, gateway = session
    investigation_id = entry(client, shift_id, run_id).json()["id"]
    conn = db.connect(path)
    try:
        historical = tuple(repo.get_engagement_config(conn, "bookshop"))
        conn.execute("DELETE FROM engagement_assist_policy WHERE slug = 'bookshop'")
        conn.commit()
    finally:
        conn.close()
    assert assist(client, shift_id, investigation_id).status_code == 409, "absent projection allowed a call"
    assert client.get(f"/api/shifts/{shift_id}/investigations").status_code == 409, "absent projection allowed a view"
    assert gateway.calls == []
    conn = db.connect(path)
    try:
        assert repo.get_engagement_assist_policy(conn, "bookshop") is None, "per-use check seeded an absent row"
        assert tuple(repo.get_engagement_config(conn, "bookshop")) == historical
        assert conn.execute("SELECT COUNT(*) FROM assist_events").fetchone()[0] == 0
    finally:
        conn.close()


@pytest.mark.parametrize("damage", ["missing_unadmitted", "mismatch_admitted"])
def test_startup_verifies_every_seeded_engagement_projection(session, monkeypatch, damage):
    _, path, _, _, gateway = session
    conn = db.connect(path)
    try:
        assert repo.get_engagement(conn, "northline") is not None
        if damage == "missing_unadmitted":
            packs = registry.registered_packs()
            monkeypatch.setattr(registry, "_PACKS", (*packs[:2], packs[2].model_copy(update={"reviewed_pins": ()})))
            conn.execute("DELETE FROM engagement_assist_policy WHERE slug = 'northline'")
        else:
            conn.execute("UPDATE engagement_assist_policy SET total_assist_budget_per_shift = 2 WHERE slug = 'northline'")
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(orchestrator.LifecycleError, match="assist policy projection"):
        with TestClient(create_app(str(path), assist_gateway=gateway)):
            pass
    assert gateway.calls == []


@pytest.mark.parametrize("role", [AssistRole.HINT, AssistRole.PATCH_PROPOSAL])
def test_gateway_counts_complete_role_specific_utf8_input_before_transport(role):
    from shiftwork.assist.gateway import MAX_INPUT_BYTES, assist_system_message
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "authored double"}}]})
    remaining = MAX_INPUT_BYTES - len(assist_system_message(role).encode())
    prompt = "界" * (remaining // 3) + "x" * (remaining % 3)
    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        gateway = LiveAssistGateway("LOCAL_TEST_TOKEN", http=http)
        gateway.generate(model_id="test-model", role=role, prompt=prompt)
        refused = False
        try:
            gateway.generate(model_id="test-model", role=role, prompt=prompt + "x")
        except AssistRejected as exc:
            refused = exc.code == "ASSIST_INPUT_LIMIT"
    assert refused, "gateway admitted a complete UTF-8 request over its input cap"
    assert len(requests) == 1, "gateway sent oversized context to transport"
