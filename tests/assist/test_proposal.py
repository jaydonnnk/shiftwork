"""S46 API/storage behavior. Executor and coach replies are labelled test doubles."""

import base64
import hashlib
import json
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from shiftwork import config, experiments, orchestrator
from shiftwork.app import create_app
from shiftwork.assist.gateway import AssistReply
from shiftwork.domain.models import ExperimentKind
from shiftwork.executor.base import RawCapture, RunResult, load_batch
from shiftwork.gateway.redaction import assert_public_safe
from shiftwork.hosted import diagnostic_budget
from shiftwork.store import db, repo


class CoachDouble:
    model_id = "s46-coach-test-double"

    def __init__(self):
        self.calls = []
        self.reply = ""

    def generate(self, **request):
        self.calls.append(request)
        return AssistReply(self.reply, output_tokens=40)


@pytest.fixture()
def proposal(tmp_path, monkeypatch, request):
    monkeypatch.setenv("NEBIUS_API_KEY", "S46_TEST_TOKEN_PRIVATE")
    monkeypatch.setenv("NEBIUS_PROJECT_ID", "S46_TEST_PROJECT_PRIVATE")
    path = tmp_path / "proposal.db"
    coach = CoachDouble()
    app = create_app(str(path), executor="recorded", assist_gateway=coach,
                     live_diagnostic_budget=diagnostic_budget)
    calls = []
    adapters = []

    async def execute(adapter, request):
        calls.append(request)
        adapters.append(adapter.name)
        return RunResult(captures=tuple(RawCapture(request_ordinal=row.ordinal,
            http_status=200, body=b"{}", elapsed_ms=1, transport_error=None,
            log_ref=None) for row in load_batch(request.request_batch, request.request_batch_bytes)),
            executor_ref=None, failure=None, wall_ms=1)

    monkeypatch.setattr(orchestrator.TokenFactoryAdapter, "execute", execute)
    monkeypatch.setattr(orchestrator.LocalProcessAdapter, "execute", execute)
    with TestClient(app) as client:
        shift = client.post("/api/engagements/bookshop/shifts").json()["id"]
        source = client.post(f"/api/shifts/{shift}/runs")
        assert source.status_code == 202, source.text
        inv = client.post(f"/api/shifts/{shift}/investigations", json={
            "source_run_id": source.json()["id"], "source_request_ordinal": 1,
            "cause": "The plan omits part of the customer's request.",
            "falsifier": "A complete plan still fails the same public check.",
            "public_test": "Require each requested task in the public response.",
            "client_request_id": "s46-investigation"})
        assert inv.status_code == 201, inv.text
        original = client.get(f"/api/shifts/{shift}/artifact").json()["files"]
        if getattr(request, "param", {}).get("unicode_base"):
            original["notes.md"] = "Café"
            assert client.put(f"/api/shifts/{shift}/artifact", json={"files": original}).status_code == 200
            assert client.post(f"/api/shifts/{shift}/artifact/versions", json={"contract": config.PIVOT_STARTER_CONTRACT_JSON}).status_code == 201
        old = original["service.py"].splitlines(keepends=True)[0]
        assert original["service.py"].count(old) == 1
        coach.reply = json.dumps({"old": old, "new": "# Coach test proposal\n" + old})
        reply = client.post(f"/api/shifts/{shift}/assist", json={
            "investigation_id": inv.json()["id"], "role": "PATCH_PROPOSAL",
            "message": "Propose one reviewable change.", "client_request_id": "s46-proposal"})
        assert reply.status_code == 200, reply.text
        assert reply.json()["state"] == "COMPLETE", reply.text
        app.state.executor = "tokenfactory"
        expected = dict(original)
        expected["service.py"] = "# Coach test proposal\n" + expected["service.py"]
        yield SimpleNamespace(client=client, app=app, path=path, shift=shift,
            event=reply.json()["id"], investigation=inv.json()["id"],
            original=original, expected=expected, coach=coach, calls=calls, adapters=adapters)


def run_proposal(p):
    return p.client.post(f"/api/shifts/{p.shift}/assist-events/{p.event}/run")


def counts(p):
    with db.connect(p.path) as conn:
        return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                for name in ("artifact_versions", "operating_selections", "ledger_events",
                             "rotation_draws", "protected_case_snapshots")}


def test_proposal_executes_retained_bytes_once_without_saving_a_version(proposal):
    p = proposal
    before = counts(p)
    response = run_proposal(p)
    assert response.status_code == 202, response.text
    view = p.client.get(f'/api/experiments/{response.json()["id"]}').json()
    assert len(p.calls) == 1, "the proposal must execute exactly once"
    assert p.adapters == ["tokenfactory"], "a coach proposal fell back to a trusted local executor"
    assert p.calls[0].artifact_snapshot.files == {k: v.encode() for k, v in p.expected.items()}, "executed proposal bytes differ"
    assert p.client.get(f"/api/shifts/{p.shift}/artifact").json()["files"] == p.original
    assert counts(p) == before, "diagnostics must not save, qualify, select or operate"
    assert view["kind"] == "DIAGNOSTIC" and view["eligible"] is False
    assert view["candidates"][0]["artifact_version_id"] is None
    assert view["candidates"][0]["proposal_event_id"] == p.event
    assert view["trials"][0]["artifact_version_id"] is None
    assert view["trials"][0]["task_assessments"]
    assert any(not row["mandatory_pass"] for row in view["trials"][0]["task_assessments"]), "invalid test reply must fail deterministic checks"
    with db.connect(p.path) as conn:
        event = repo.get_assist_event(conn, p.event)
        assert event.diagnostic_run_id == view["trials"][0]["run_id"]
        assert event.proposal_source_sha256 == hashlib.sha256(p.expected["service.py"].encode()).hexdigest()
        assert repo.count_experiments_for_shift(conn, p.shift, ExperimentKind.DIAGNOSTIC) == 1
    assert run_proposal(p).status_code == 409, "a second proposal run must refuse"
    assert len(p.calls) == 1, "a second proposal run reached the executor"


@pytest.mark.parametrize("field", ["cause", "falsifier", "public_test"])
def test_assist_proposal_run_requires_complete_investigation(proposal, monkeypatch, field):
    p = proposal
    original = repo.get_investigation
    monkeypatch.setattr(repo, "get_investigation", lambda conn, ident:
        original(conn, ident).model_copy(update={field: " "}))
    response = run_proposal(p)
    assert response.status_code == 409, "incomplete investigation allowed proposal execution"
    assert not p.calls, "incomplete investigation reached the executor"


def test_assist_proposal_run_requires_a_diagnostic_slot(proposal, monkeypatch):
    monkeypatch.setattr(experiments, "DIAGNOSTIC_EXPERIMENTS_PER_SHIFT", 0)
    response = run_proposal(proposal)
    assert response.status_code == 409, "exhausted diagnostic budget allowed proposal execution"
    assert not proposal.calls, "exhausted diagnostic budget reached the executor"


@pytest.mark.parametrize("adapter", ["recorded", "local_process"])
def test_assist_proposal_never_runs_trusted_local_or_recorded(proposal, adapter):
    proposal.app.state.executor = adapter
    response = run_proposal(proposal)
    assert response.status_code == 409, "unsafe executor allowed a coach proposal"
    assert not proposal.calls, "unsafe executor performed work"


def test_accepted_proposal_is_draft_only_and_attributed(proposal):
    p = proposal
    before = counts(p)
    response = p.client.post(f"/api/assist-events/{p.event}/decision", json={"accepted": True})
    assert response.status_code == 200, response.text
    assert p.client.get(f"/api/shifts/{p.shift}/artifact").json()["files"] == p.expected, "acceptance must copy the exact proposal into the draft"
    assert counts(p) == before, "acceptance created a version, selection or business effect"
    for _ in range(2):
        saved = p.client.post(f"/api/shifts/{p.shift}/artifact/versions", json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
        assert saved.status_code == 201, saved.text
        assert saved.json()["authorship"]["generated_patch_accepted_count"] == 1, "acceptance must be counted once on explicit save"
        assert saved.json()["authorship"]["learner_edited"] is False, "coach-only source was credited as a learner edit"
        assert saved.json()["authorship"]["learner_declared_generated_patch_use"] is False
    with TestClient(create_app(str(p.path), executor="recorded")) as restarted:
        again = restarted.post(f"/api/assist-events/{p.event}/decision", json={"accepted": True})
        assert again.status_code == 409, "restart allowed a second acceptance"
        assert restarted.get(f"/api/shifts/{p.shift}/artifact").json()["files"] == p.expected


def test_acceptance_refuses_to_overwrite_a_later_draft_edit(proposal):
    p = proposal
    edited = dict(p.original, **{"change_log.md": "A later learner edit."})
    assert p.client.put(f"/api/shifts/{p.shift}/artifact", json={"files": edited}).status_code == 200
    response = p.client.post(f"/api/assist-events/{p.event}/decision", json={"accepted": True})
    assert response.status_code == 409, "acceptance overwrote a later learner edit"
    assert p.client.get(f"/api/shifts/{p.shift}/artifact").json()["files"] == edited
    with db.connect(p.path) as conn:
        assert repo.get_assist_event(conn, p.event).accepted is None


def test_assist_proposal_run_sees_no_protected_material_and_cannot_qualify(proposal):
    p = proposal
    response = run_proposal(p)
    assert response.status_code == 202, response.text
    surfaces = [response.json(), p.client.get(f'/api/experiments/{response.json()["id"]}').json(),
                p.client.get(f"/api/shifts/{p.shift}/investigations").json(),
                p.coach.calls, {"files": {k: v.decode() for k, v in p.calls[0].artifact_snapshot.files.items()},
                                "batch": base64.b64encode(p.calls[0].request_batch_bytes).decode()}]
    with db.connect(p.path) as conn:
        needles = orchestrator._private_public_needles(conn)
    for surface in surfaces:
        assert_public_safe(surface, needles)
        for needle in needles:
            with pytest.raises(ValueError):
                assert_public_safe({"serialized": json.dumps(surface, default=str), "injected": needle}, needles)
    assert surfaces[1]["eligible"] is False, "a proposal diagnostic qualified a version"


def test_retained_proposal_survives_later_draft_edits_and_restart(proposal):
    p = proposal
    edited = dict(p.original)
    edited["service.py"] += "\n# Later learner edit\n"
    assert p.client.put(f"/api/shifts/{p.shift}/artifact", json={"files": edited}).status_code == 200
    assert run_proposal(p).status_code == 202
    assert p.calls[0].artifact_snapshot.files["service.py"] == p.expected["service.py"].encode(), "a later draft edit changed the proposal being tested"
    with TestClient(create_app(str(p.path), executor="tokenfactory", live_diagnostic_budget=diagnostic_budget)) as restarted:
        response = restarted.post(f"/api/shifts/{p.shift}/assist-events/{p.event}/run")
        assert response.status_code == 409, "restart allowed a second proposal run"
    assert len(p.calls) == 1


@pytest.mark.parametrize("adapter", ["local_process", "recorded"])
def test_queued_proposal_rejects_an_unsafe_adapter_before_dispatch(proposal, monkeypatch, adapter):
    p = proposal
    monkeypatch.setattr(experiments, "execute_experiment_task", lambda *args: None)
    response = run_proposal(p)
    assert response.status_code == 202, response.text
    run_id = response.json()["trials"][0]["run_id"]
    original = repo.get_run
    monkeypatch.setattr(repo, "get_run", lambda conn, ident:
        original(conn, ident).model_copy(update={"adapter": adapter}) if ident == run_id else original(conn, ident))
    with db.connect(p.path) as conn:
        result = experiments.execute_experiment(conn, run_id)
    assert result.state.value == "FAILED", "unsafe queued proposal did not fail closed"
    assert not p.calls, "unsafe queued proposal dispatched executor work"


@pytest.mark.parametrize("field", ["base_hash", "artifact_content_hash", "proposal_source_sha256"])
def test_proposal_hash_damage_refuses_before_execution(proposal, monkeypatch, field):
    p = proposal
    original = repo.get_assist_proposal

    def damaged(conn, ident):
        row = dict(original(conn, ident))
        row[field] = "0" * 64
        return row

    monkeypatch.setattr(repo, "get_assist_proposal", damaged)
    response = run_proposal(p)
    assert response.status_code == 409, "changed proposal identity allowed execution"
    assert not p.calls, "changed proposal identity reached the executor"


def test_public_run_and_board_identify_the_proposal_not_its_contract_base(proposal):
    p = proposal
    response = run_proposal(p)
    assert response.status_code == 202, response.text
    run_id = response.json()["trials"][0]["run_id"]
    for value in (p.client.get(f"/api/runs/{run_id}").json(),
                  p.client.get("/api/engagements/bookshop/board").json()["latest_run"]):
        assert value["artifact_version_id"] is None, "public proposal falsely claims to have tested its contract base"
        assert value["proposal_event_id"] == p.event
        assert value["experiment_id"] == response.json()["id"]


def test_rejection_preserves_draft_and_generated_accept_count(proposal):
    p = proposal
    response = p.client.post(f"/api/assist-events/{p.event}/decision", json={"accepted": False})
    assert response.status_code == 200
    assert p.client.get(f"/api/shifts/{p.shift}/artifact").json()["files"] == p.original
    saved = p.client.post(f"/api/shifts/{p.shift}/artifact/versions", json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
    assert saved.status_code == 201, saved.text
    assert saved.json()["authorship"]["generated_patch_seen_count"] == 1
    assert saved.json()["authorship"]["generated_patch_accepted_count"] == 0


@pytest.mark.parametrize("text", ["pseudocode only", '{"old":"","new":"x"}',
    '{"old":"not in the source","new":"x"}', '{"old":"x","new":"x"}',
    '{"old":"a","new":"b","path":"service.py"}',
    '{"old":"import json","old":"a","new":"b"}'])
def test_inapplicable_proposal_is_refused_instead_of_guessed(text):
    from shiftwork.assist.gateway import AssistRejected, apply_proposal
    with pytest.raises(AssistRejected, match="ASSIST_PROPOSAL_INVALID"):
        apply_proposal(text, {"service.py": "import json\n"})


def test_patch_only_changes_one_exact_service_fragment():
    from shiftwork.assist.gateway import apply_proposal
    original = {"service.py": "import json\nprint(1)\n", "checks.json": "[]"}
    assert apply_proposal('{"old":"print(1)","new":"print(2)"}', original) == {
        "service.py": "import json\nprint(2)\n", "checks.json": "[]"}
    assert original["service.py"] == "import json\nprint(1)\n"


def test_proposal_can_use_an_inherited_contract_base(proposal):
    p = proposal
    p.app.state.executor = "recorded"
    closed = p.client.post(f"/api/shifts/{p.shift}/close")
    assert closed.status_code == 200, closed.text
    opened = p.client.post("/api/engagements/bookshop/shifts")
    assert opened.status_code == 201, opened.text
    shift = opened.json()["id"]
    source = p.client.post(f"/api/shifts/{shift}/runs")
    assert source.status_code == 202, source.text
    investigation = p.client.post(f"/api/shifts/{shift}/investigations", json={
        "source_run_id": source.json()["id"], "source_request_ordinal": 1,
        "cause": "The inherited service still omits a requested task.",
        "falsifier": "The same failure with every requested task present.",
        "public_test": "Require all the customer's requested tasks.",
        "client_request_id": "inherited-investigation"})
    assert investigation.status_code == 201, investigation.text
    response = p.client.post(f"/api/shifts/{shift}/assist", json={
        "investigation_id": investigation.json()["id"], "role": "PATCH_PROPOSAL",
        "message": "Propose one change.", "client_request_id": "inherited-proposal"})
    assert response.status_code == 200 and response.json()["state"] == "COMPLETE", response.text
    accepted = p.client.post(f'/api/assist-events/{response.json()["id"]}/decision', json={"accepted": True})
    assert accepted.status_code == 200, "an inherited contract base wrongly blocked proposal acceptance: " + accepted.text


@pytest.mark.parametrize("proposal", [{"unicode_base": True}], indirect=True)
def test_acceptance_preserves_a_byte_distinct_unicode_draft_edit(proposal):
    p = proposal
    edited = dict(p.original, **{"notes.md": "Cafe\u0301"})
    assert p.client.put(f"/api/shifts/{p.shift}/artifact", json={"files": edited}).status_code == 200
    response = p.client.post(f"/api/assist-events/{p.event}/decision", json={"accepted": True})
    assert response.status_code == 409, "NFC-equivalent learner bytes were silently overwritten"
    assert p.client.get(f"/api/shifts/{p.shift}/artifact").json()["files"] == edited


def test_proposal_preview_exposes_the_exact_retained_public_source(proposal):
    p = proposal
    events = p.client.get(f"/api/shifts/{p.shift}/investigations").json()["assist_events"]
    assert events[0].get("proposal_source") == p.expected["service.py"], "the learner cannot review the exact proposed source"
    assert hashlib.sha256(events[0]["proposal_source"].encode()).hexdigest() == events[0]["proposal_source_sha256"]


def test_saving_source_and_authorship_is_atomic_with_acceptance(proposal, monkeypatch):
    from shiftwork.domain.models import ContractParams
    p = proposal
    original = repo.get_draft
    attempted = []

    def competing_acceptance(conn, shift_id):
        result = original(conn, shift_id)
        if not attempted:
            attempted.append(True)
            with db.connect(p.path) as rival:
                rival.execute("PRAGMA busy_timeout = 0")
                try:
                    rival.execute("BEGIN IMMEDIATE")
                except sqlite3.OperationalError as error:
                    assert "locked" in str(error)
                else:
                    rival.rollback()
                    orchestrator.record_assist_decision(rival, p.event, True)
        return result

    monkeypatch.setattr(repo, "get_draft", competing_acceptance)
    with db.connect(p.path) as conn:
        version = orchestrator.freeze_version(conn, p.shift, ContractParams.model_validate(config.PIVOT_STARTER_CONTRACT_JSON))
    assert version.files == p.original
    assert version.authorship.generated_patch_accepted_count == 0, "a concurrent acceptance attributed a coach patch to different saved bytes"


# Authored source text only. These definitions are never imported or executed.
CONTEXT_DEFINITIONS = (
    'def answer(request):\r\n    return "café", ask_for_plan(request)\r\n',
    'TASK_VOCABULARY = ("collection", "alternative")\r\n',
    'def ask_for_plan(request):\r\n    return None  # authored planner\r\n',
    'TOOLS = ("catalogue", "stock")\r\n',
)
CONTEXT_SOURCE = '# frozen draft\r\n' + '\r\n# OMITTED_SOURCE\r\n'.join(CONTEXT_DEFINITIONS)
TRACE = dict(source="controller_verified", request_ordinal=1, model="historical-nano",
             plan=None, plan_failure="SCHEMA_INVALID", finish_reason="length", output_tokens=1024)
TRACE_LABEL = "\nController-verified public inference result: "
UNAVAILABLE_TRACE = "Unavailable: no unique valid controller-verified inference result for the historical source request."


@pytest.fixture()
def coach_context(tmp_path, monkeypatch):
    import httpx
    from shiftwork.assist.gateway import LiveAssistGateway
    from shiftwork.domain.models import ExecutionObservation
    from datetime import datetime, timezone

    monkeypatch.setenv("NEBIUS_API_KEY", "S46_CONTEXT_PRIVATE_TOKEN")
    path = tmp_path / "context.db"
    outbound = []

    def respond(request):
        outbound.append(json.loads(request.content))
        patch = json.dumps({"old": "# frozen draft", "new": "# authored coach double"})
        return httpx.Response(200, json={"choices": [{"message": {"content": patch}}]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        app = create_app(str(path), executor="recorded",
                         assist_gateway=LiveAssistGateway("S46_CONTEXT_PRIVATE_TOKEN", http=http))
        with TestClient(app) as client:
            shift = client.post("/api/engagements/bookshop/shifts").json()["id"]
            source_run = client.post(f"/api/shifts/{shift}/runs").json()["id"]
            inv = client.post(f"/api/shifts/{shift}/investigations", json={
                "source_run_id": source_run, "source_request_ordinal": 1,
                "cause": "The planner omits a task.", "falsifier": "A complete plan also fails.",
                "public_test": "Check both customer tasks.", "client_request_id": "context-inv"}).json()
            with db.connect(path) as conn:
                run = repo.get_run(conn, source_run)
                version = repo.get_version(conn, run.artifact_version_id)
                output = repo.list_outputs(conn, source_run)[0]
            rows = [ExecutionObservation(id="authored-trace", run_id=source_run,
                request_ordinal=1, ordinal=100, kind="INFERENCE_RESULT",
                public_payload_json=dict(TRACE), raw_payload_ref="RAW_PROVIDER_PRIVATE",
                measured_at=datetime.now(timezone.utc))]
            reads = []
            def observations(conn, run_id):
                reads.append(run_id)
                return rows
            monkeypatch.setattr(repo, "list_observations", observations)
            files = client.get(f"/api/shifts/{shift}/artifact").json()["files"]
            def set_source(source):
                files["service.py"] = source
                saved = client.put(f"/api/shifts/{shift}/artifact", json={"files": files})
                assert saved.status_code == 200, saved.text
            set_source(CONTEXT_SOURCE)
            frozen = client.post(f"/api/shifts/{shift}/artifact/versions", json={"contract": config.PIVOT_STARTER_CONTRACT_JSON})
            assert frozen.status_code == 201, frozen.text
            def ask(role="PATCH_PROPOSAL", message="Propose a public repair."):
                return client.post(f"/api/shifts/{shift}/assist", json={
                    "investigation_id": inv["id"], "role": role, "message": message,
                    "client_request_id": "context-help"})
            yield SimpleNamespace(client=client, app=app, path=path, shift=shift,
                run=run, version=version, output=output, rows=rows, outbound=outbound,
                reads=reads, ask=ask, set_source=set_source)


def trace_from_request(p):
    return p.outbound[0]["messages"][1]["content"].split(TRACE_LABEL)[1].split("\n", 1)[0]


def test_coach_receives_exact_definitions_and_historical_identity(coach_context):
    p = coach_context
    response = p.ask()
    assert response.status_code == 200, response.text
    prompt = p.outbound[0]["messages"][1]["content"]
    for definition in CONTEXT_DEFINITIONS:
        assert definition in prompt, "an exact public definition is missing from the outbound request"
    assert [prompt.index(d) for d in CONTEXT_DEFINITIONS] == sorted(prompt.index(d) for d in CONTEXT_DEFINITIONS), "source order changed"
    assert "OMITTED_SOURCE" not in prompt, "unselected source escaped the excerpt"
    assert "Omitted source is unavailable" in prompt
    identity = json.loads(prompt.split("\nHistorical source (distinct from current frozen draft): ")[1].split("\n", 1)[0])
    assert identity == dict(run_id=p.run.id, artifact_version_id=p.version.id,
                            artifact_content_hash=p.version.content_hash), "historical identity was replaced by current draft identity"
    assert json.loads(trace_from_request(p)) == TRACE, "the bound public inference result is missing or altered"
    assert p.reads == [p.run.id]
    assert f"Observed service response: HTTP {p.output.http_status}; {p.output.body.decode()}" in prompt
    assert "Learner cause: The planner omits a task." in prompt
    assert "Learner falsifier: A complete plan also fails." in prompt
    assert "Learner public test: Check both customer tasks." in prompt
    system = p.outbound[0]["messages"][0]["content"]
    assert "public service.py source and controller-verified public inference result" in system, "patch role lacks authority for its supplied public evidence"
    assert "successful diagnostic does not prove a repair" in system, "a diagnostic was treated as proof of repair"
    assert p.outbound[0]["max_tokens"] == 1024 and p.outbound[0]["temperature"] == 0


@pytest.mark.parametrize("mismatch", ["run", "stored_ordinal", "payload_ordinal", "kind", "provenance"])
def test_coach_excludes_unbound_trace(coach_context, mismatch):
    p = coach_context
    changes = {"run": {"run_id": "foreign-run"}, "stored_ordinal": {"request_ordinal": 2},
               "payload_ordinal": {"public_payload_json": {**TRACE, "request_ordinal": 2}},
               "kind": {"kind": "USAGE"},
               "provenance": {"public_payload_json": {**TRACE, "source": "service_reported"}}}
    p.rows[:] = [p.rows[0].model_copy(update=changes[mismatch])]
    response = p.ask()
    assert response.status_code == 200, response.text
    assert trace_from_request(p) == UNAVAILABLE_TRACE, "an unbound trace reached the coach"


@pytest.mark.parametrize("damage", ["absent", "duplicate", "missing_field", "plan", "plan_step", "model", "finish_reason", "plan_failure", "output_tokens", "negative_tokens", "ordinal_bool", "plan_value", "plan_scalar_step"])
def test_coach_labels_unavailable_trace(coach_context, damage):
    p = coach_context
    if damage == "absent":
        p.rows.clear()
    elif damage == "duplicate":
        p.rows.append(p.rows[0].model_copy(update={"id": "duplicate"}))
    else:
        payload = dict(TRACE)
        if damage == "missing_field":
            del payload["plan_failure"]
        else:
            field, value = {"plan": ("plan", "not-a-plan"), "plan_step": ("plan", [{"task_type": "collection", "tool_name": "stock", "raw": "PRIVATE"}]),
                "model": ("model", {}), "finish_reason": ("finish_reason", []),
                "plan_failure": ("plan_failure", {}), "output_tokens": ("output_tokens", True),
                "ordinal_bool": ("request_ordinal", True), "negative_tokens": ("output_tokens", -1),
                "plan_value": ("plan", [{"task_type": {}, "tool_name": "stock"}]),
                "plan_scalar_step": ("plan", [42])}[damage]
            payload[field] = value
        p.rows[:] = [p.rows[0].model_copy(update={"public_payload_json": payload})]
    response = p.ask()
    assert response.status_code == 200, response.text
    assert trace_from_request(p) == UNAVAILABLE_TRACE, "a missing, ambiguous or malformed trace was presented as evidence"


def test_coach_forwards_valid_plan_without_other_observation_fields(coach_context):
    p = coach_context
    plan = [{"task_type": "collection", "tool_name": "stock"}]
    payload = {**TRACE, "plan": plan, "plan_failure": None}
    needles = ("RAW_PROVIDER_PRIVATE", "PROVIDER_REASONING_PRIVATE", "PROTECTED_GRADE_PRIVATE", r"C:\private\sealed.json")
    p.rows[:] = [p.rows[0].model_copy(update={"public_payload_json": {
        **payload, "provider_response": needles[0], "reasoning": needles[1], "grades": needles[2], "expected_ref": needles[3]}})]
    response = p.ask()
    assert response.status_code == 200, response.text
    surfaces = (json.dumps(p.outbound), response.text, p.client.get(f"/api/shifts/{p.shift}/investigations").text)
    for needle in needles:
        variants = {needle, needle.replace("\\", "/")}
        for _ in range(3):
            variants |= {json.dumps(value)[1:-1] for value in variants}
        def detected(surface):
            return any(value in surface for value in variants)
        for surface in surfaces:
            assert not detected(surface), f"private observation content escaped into a serialized context: {needle}"
        for variant in variants:
            assert detected('{"injected": "' + variant + '"}'), "serialized needle positive control failed"

    assert json.loads(trace_from_request(p)) == payload, "public plan or whitelist changed"



@pytest.mark.parametrize("source", ["# frozen draft\nnot python !", "# frozen draft\nTASK_VOCABULARY = ()\n", CONTEXT_SOURCE + '\r\ndef answer(request):\r\n    pass\r\n'], ids=["syntax", "missing", "duplicate"])
def test_coach_falls_back_to_complete_source(coach_context, source):
    p = coach_context
    p.set_source(source)
    response = p.ask()
    assert response.status_code == 200, response.text
    prompt = p.outbound[0]["messages"][1]["content"]
    assert prompt.endswith(source), "incomplete or ambiguous definitions silently dropped source"


@pytest.mark.parametrize("source", [CONTEXT_SOURCE.replace('return None', 'return "' + '界' * 3000 + '"'), '# frozen draft\n' + '# x\n' * 3000], ids=['selected', 'fallback'])
def test_coach_context_cap_refuses_without_reservation(coach_context, source):
    p = coach_context
    p.set_source(source)
    response = p.ask()
    assert response.status_code == 409, "oversized complete coach context was admitted"
    assert not p.outbound, "oversized context reached provider transport"
    with db.connect(p.path) as conn:
        assert not repo.list_assist_for_shift(conn, p.shift), "oversized context reserved assist budget"


def test_coach_private_whitelisted_value_refuses_without_reservation(coach_context):
    p = coach_context
    p.rows[:] = [p.rows[0].model_copy(update={"public_payload_json": {**TRACE, "model": "S46_CONTEXT_PRIVATE_TOKEN"}})]
    response = p.ask()
    assert response.status_code == 409, "private inference context passed the public guard"
    assert not p.outbound
    assert "S46_CONTEXT_PRIVATE_TOKEN" not in response.text
    with db.connect(p.path) as conn:
        assert not repo.list_assist_for_shift(conn, p.shift)


@pytest.mark.parametrize("role", ["HINT", "DIAGNOSIS"])
def test_other_assist_roles_keep_their_evidence_authority(coach_context, role):
    from shiftwork.assist.gateway import ASSIST_SYSTEM_MESSAGE
    p = coach_context
    response = p.ask(role)
    assert response.status_code == 200, response.text
    assert not p.reads, "another assist role read inference observations"
    system, user = p.outbound[0]["messages"]
    assert system["content"] == ASSIST_SYSTEM_MESSAGE
    assert TRACE_LABEL not in user["content"] and "TASK_VOCABULARY" not in user["content"]


@pytest.mark.parametrize("identity", ["run", "version"])
def test_coach_refuses_missing_historical_identity(coach_context, monkeypatch, identity):
    p = coach_context
    getter = "get_run" if identity == "run" else "get_version"
    original = getattr(repo, getter)
    missing_id = p.run.id if identity == "run" else p.version.id
    monkeypatch.setattr(repo, getter, lambda conn, row_id: None if row_id == missing_id else original(conn, row_id))
    response = p.ask()
    assert response.status_code == 409, "missing historical identity allowed a coach call"
    assert not p.outbound and not p.reads


def test_coach_keeps_large_omitted_source_out_of_the_request(coach_context):
    p = coach_context
    p.set_source(CONTEXT_SOURCE + '\n# OMITTED_LARGE_SOURCE ' + '界' * 3000 + '\n')
    response = p.ask()
    assert response.status_code == 200, "unselected source exhausted the bounded public context"
    assert "OMITTED_LARGE_SOURCE" not in p.outbound[0]["messages"][1]["content"]


@pytest.mark.parametrize('separator', ['\u2028', '\u2029', '\v', '\f'])
def test_coach_source_preserves_unicode_physical_lines(separator):
    from shiftwork.assist.gateway import proposal_source_excerpt
    definitions = ('TASK_VOCABULARY = ("a' + separator + 'b",)\r\n',
                   'TOOLS = ("stock",)\r\n',
                   'def ask_for_plan(request):\r\n    return None\r\n',
                   'def answer(request):\r\n    return "café"\r\n')
    excerpt = proposal_source_excerpt('# omitted\r\n' + '\r\n'.join(definitions))
    assert all(d in excerpt for d in definitions), 'Unicode physical lines changed exact definition bytes'


def test_coach_source_excludes_same_line_unselected_statement():
    from shiftwork.assist.gateway import proposal_source_excerpt
    source = CONTEXT_SOURCE.replace('TASK_VOCABULARY = ("collection", "alternative")',
        'TASK_VOCABULARY = ("collection", "alternative"); OMITTED = "unselected content"')
    excerpt = proposal_source_excerpt(source)
    assert 'OMITTED' not in excerpt, 'a same-line unselected statement reached the excerpt'
    assert 'TASK_VOCABULARY = ("collection", "alternative")' in excerpt


@pytest.mark.parametrize('rebinding', ['TASK_VOCABULARY, TOOLS = ("changed",), ("different",)\n',
    'TASK_VOCABULARY = TOOLS = ()\n', 'def TOOLS():\n    pass\n'])
def test_coach_source_rebinding_uses_whole_source(rebinding):
    from shiftwork.assist.gateway import proposal_source_excerpt
    source = CONTEXT_SOURCE + '\n' + rebinding
    assert proposal_source_excerpt(source) == source, 'a duplicate top-level binding was silently omitted'
