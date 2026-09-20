"""Test 40 (Slice 8): the Test 1 offline pre-proof, driven on ``local_process``.

Two consecutive bookshop shifts run end to end on the shipped controller with
the pre-proof's trusted fixture artifacts: shift 1 consumes its three attempts
with the pre-repair artifact, the learner freezes the repaired successor, the
shift closes with unresolved incidents and a declared limit, the process
restarts, and shift 2 inherits the version, decisions, visible checks,
unresolved incidents and limits and then draws three still-unexposed variants per
family. The operator-only comparison scores the pre-repair and repaired
artifacts' real outputs against the same held-out stimuli: the former fails and
the latter passes, so the later consequence is caused by execution, not narrated.
Every first-shift outbound surface is scanned for future customer wording.
"""

import base64
import time

from fastapi.testclient import TestClient

from conftest import family_cases
from shiftwork import config
from shiftwork.app import create_app
from shiftwork.sealed import store as sealed_store
from shiftwork.store import db, repo

CONTRACT = config.REPAIR_ARC_CONTRACT_JSON
OPERATOR = {"adapter": "local_process"}
HELD_OUT = (1, 2, 3)
FUTURE = (4, 5, 6)
TERMINAL = {"FINALIZED", "FAILED"}
# Every failing check opens one incident: attempt k scores k stimuli per family,
# so three attempts open sum(1..3) * families incidents.
INCIDENTS = sum(range(1, len(HELD_OUT) + 1)) * len(config.BOOKSHOP_FAMILIES)


def _call(client: TestClient, method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    assert response.status_code < 400, f"{method} {path} -> {response.status_code}: {response.text}"
    return response.json()


def _open(client: TestClient) -> str:
    return _call(client, "POST", "/api/engagements/bookshop/shifts")["id"]


def _attempt(client: TestClient, shift_id: str) -> dict:
    started = _call(client, "POST", f"/api/shifts/{shift_id}/runs")
    deadline = time.monotonic() + 30
    while True:
        run = _call(client, "GET", f"/api/runs/{started['id']}")
        if run["state"] in TERMINAL or time.monotonic() > deadline:
            return run
        time.sleep(0.02)


def _freeze_stage(client: TestClient, shift_id: str, stage: str) -> dict:
    files = config.repair_arc_artifact_files(stage)
    _call(client, "PUT", f"/api/shifts/{shift_id}/artifact", json={"files": files})
    version = _call(
        client, "POST", f"/api/shifts/{shift_id}/artifact/versions", json={"contract": CONTRACT}
    )
    assert version["content_hash"] == config.TRUSTED_LOCAL_FIXTURES[f"repair_arc_{stage}"][0], (
        f"the frozen {stage} stage does not reproduce its pin; local_process would refuse it"
    )
    return version


def _sweep(client: TestClient, shift_id: str, run_ids: list[str], incident_ids: list[str]):
    """Every learner-visible surface of a shift, as raw serialized text."""
    surfaces: list[tuple[str, str]] = []

    def record(label: str, path: str) -> None:
        response = client.get(path)
        assert response.status_code < 400, f"GET {path} -> {response.status_code}"
        surfaces.append((label, response.text))

    record("board", "/api/engagements/bookshop/board")
    record("ledger", "/api/engagements/bookshop/ledger")
    record("artifact", f"/api/shifts/{shift_id}/artifact")
    for run_id in run_ids:
        record(f"run {run_id}", f"/api/runs/{run_id}")
        record(f"outputs {run_id}", f"/api/runs/{run_id}/outputs")
        record(f"checks {run_id}", f"/api/runs/{run_id}/checks")
    for incident_id in incident_ids:
        record(f"incident {incident_id}", f"/api/incidents/{incident_id}")
    return surfaces


def test_full_budget_preserves_unseen_inherited_case(tmp_path):
    db_file = tmp_path / "preproof.db"
    with TestClient(create_app(str(db_file), executor="local_process")) as client:
        shift_one = _open(client)
        version_one = _freeze_stage(client, shift_one, "pre")

        run_ids = []
        for attempt in range(1, len(HELD_OUT) + 1):
            run = _attempt(client, shift_one)
            assert run["state"] == "FINALIZED", run
            assert run["artifact_version_id"] == version_one["id"]
            run_ids.append(run["id"])
            checks = _call(client, "GET", f"/api/runs/{run['id']}/checks")
            assert {check["verdict"] for check in checks} == {"fail"}
            assert {check["reason_code"] for check in checks} == {"MISSING_EVIDENCE"}
            draws = _draws(db_file, run["id"])
            assert [draw["variant_ref"] for draw in draws] and len(draws) == len(
                config.BOOKSHOP_FAMILIES
            )
            assert sorted(_ordinal_of(draw["variant_ref"]) for draw in draws) == [attempt] * len(
                config.BOOKSHOP_FAMILIES
            ), f"attempt {attempt} did not draw the {attempt}-ordinal variant per family"

        board = _call(client, "GET", "/api/engagements/bookshop/board")
        incidents = board["incidents"]
        assert len(incidents) == INCIDENTS, incidents
        assert {incident["state"] for incident in incidents} == {"OPEN"}
        first_surfaces = _sweep(
            client, shift_one, run_ids, [incident["id"] for incident in incidents]
        )
        assert board["attempts_remaining"] == 0

        # The repair, then the close: the version, the decisions and checks files
        # and every unresolved incident carry forward; limits are declared once.
        version_two = _freeze_stage(client, shift_one, "post")
        closed = _call(client, "POST", f"/api/shifts/{shift_one}/close")
        assert closed["state"] == "closed"
        board = _call(client, "GET", "/api/engagements/bookshop/board")
        assert {incident["state"] for incident in board["incidents"]} == {"CLOSED_UNRESOLVED"}
        assert board["unresolved_limits"] == [config.REPAIR_ARC_DECLARED_LIMIT]

    # Restart: a new process over the same database reconciles and reopens.
    with TestClient(create_app(str(db_file), executor="local_process")) as client:
        shift_two = _open(client)
        board = _call(client, "GET", "/api/engagements/bookshop/board")
        draft = _call(client, "GET", f"/api/shifts/{shift_two}/artifact")
        assert board["latest_version"]["id"] == version_two["id"]
        assert board["latest_version"]["content_hash"] == version_two["content_hash"]
        assert draft["files"] == config.repair_arc_artifact_files("post"), (
            "the next shift must inherit the version's files, including the "
            "learner's decision log and visible-check file"
        )
        assert board["unresolved_limits"] == [config.REPAIR_ARC_DECLARED_LIMIT]
        assert {incident["state"] for incident in board["incidents"]} == {"CLOSED_UNRESOLVED"}
        assert len(board["incidents"]) == INCIDENTS

        shift_two_runs = []
        drawn = []
        for attempt in range(1, len(HELD_OUT) + 1):
            run = _attempt(client, shift_two)
            assert run["state"] == "FINALIZED", run
            shift_two_runs.append(run["id"])
            draws = _draws(db_file, run["id"])
            assert len(draws) == len(config.BOOKSHOP_FAMILIES)
            drawn.append(sorted(_ordinal_of(draw["variant_ref"]) for draw in draws))
            assert drawn[-1] == [FUTURE[attempt - 1]] * len(config.BOOKSHOP_FAMILIES), (
                f"shift 2 attempt {attempt} did not draw a still-unexposed variant: {drawn[-1]}"
            )
            checks = _call(client, "GET", f"/api/runs/{run['id']}/checks")
            assert {check["verdict"] for check in checks} == {"pass"}, (
                f"the repaired artifact failed its own held-out stimuli: {checks}"
            )
        board = _call(client, "GET", "/api/engagements/bookshop/board")
        assert board["incidents"] == [], f"inherited incidents did not resolve: {board['incidents']}"
        assert board["attempts_remaining"] == 0

    # The operator-only comparison: same held-out stimuli, both trusted fixture
    # artifacts, real local_process outputs. The pre-repair artifact fails and the
    # repaired one passes every held-out case; only the artifact changed.
    comparison = _causal_rows(db_file, run_ids, shift_two_runs[0])
    assert len(comparison) == len(HELD_OUT) * len(config.BOOKSHOP_FAMILIES)
    for row in comparison:
        assert row["pre_verdict"] == "fail", row
        assert row["post_verdict"] == "pass", row
        assert row["pre_version"] == version_one["id"] and row["post_version"] == version_two["id"]
        assert row["pre_request_text"] == row["post_request_text"], (
            "the comparison must hold the stimulus fixed"
        )
        assert row["pre_ordinal"] == row["post_ordinal"], (
            "the comparison must hold the request ordinal fixed"
        )
        assert row["pre_snapshot"] == row["post_snapshot"], (
            "the comparison must hold the shop snapshot fixed"
        )
        assert row["pre_body"] != row["post_body"], (
            "the two artifacts must produce different output bodies, or the artifact "
            "did not cause the verdict change"
        )
        assert row["pre_reason_code"] == "MISSING_EVIDENCE"

    # No future customer wording appears on any first-shift surface.
    future_texts = _batch_texts(FUTURE)
    assert future_texts
    leaked = [
        (label, text)
        for label, surface in first_surfaces
        for text in future_texts
        if text in surface
    ]
    assert not leaked, f"future customer wording was released before its run: {leaked[:3]}"

    # Scanner self-test (AGENTS.md S6): the zero above is only a real absence if a
    # needle can match a surface as serialized. Inject one future sentence into a
    # copy of a collected surface and require the same scan to report it.
    assert first_surfaces, "no first-shift surface was collected to scan"
    self_test_label, self_test_surface = first_surfaces[0]
    injected_surfaces = [
        (self_test_label, self_test_surface + future_texts[0]),
        *first_surfaces[1:],
    ]
    injected_hits = [
        (label, text)
        for label, surface in injected_surfaces
        for text in future_texts
        if text in surface
    ]
    assert any(text == future_texts[0] for _, text in injected_hits), (
        "the leak scanner cannot match a future sentence injected into a serialized "
        "surface, so its zero-leak result is not evidence of absence"
    )
    executed = _executed_ordinals(db_file, run_ids)
    assert executed == {1, 2, 3}, f"shift 1 executed later stimuli than its attempts: {executed}"


def test_next_shift_needs_the_six_variant_inventory(tmp_path, sealed_inventory):
    # Test 40's inventory clause: with the old three-variant families, shift 1
    # consumes every variant and the next shift's first run is refused whole, so
    # the pre-proof's shift-2 assertion is failing-capable against that inventory.
    for family in config.BOOKSHOP_FAMILIES:
        cases = family_cases(family)
        assert len(cases) == 6, f"the checked-in {family} family changed size"
        sealed_inventory["publish"](family, cases[:3], cycle=1)

    db_file = tmp_path / "three-variant.db"
    with TestClient(create_app(str(db_file))) as client:
        shift_one = _open(client)
        _call(
            client,
            "POST",
            f"/api/shifts/{shift_one}/artifact/versions",
            json={
                "contract": {
                    "catalog_version": 2,
                    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
                    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
                    "response_time_limit_ms": 3000,
                    "declared_limits": [],
                }
            },
        )
        for _ in range(3):
            assert _attempt(client, shift_one)["state"] == "FINALIZED"
        _call(client, "POST", f"/api/shifts/{shift_one}/close")
        shift_two = _open(client)
        before = _counts(db_file)
        refusal = client.post(f"/api/shifts/{shift_two}/runs")
        detail = refusal.json()["detail"]
        assert "never-exposed variant" in detail, refusal.text
        assert refusal.status_code == 409, refusal.text
        assert _counts(db_file) == before, "the refused run left rows behind"


def test_kill5_gate_depends_on_the_computed_booleans():
    # MAJOR-1 self-test: the demo's kill-5 verdict must depend on the computed
    # ordinal, snapshot and body-difference booleans, not on a constant sentence.
    # Each false boolean and each flipped verdict must turn PASS into FAIL.
    from demos import test1 as demo

    good = {
        "pre_verdict": "fail",
        "post_verdict": "pass",
        "same_ordinal": True,
        "same_snapshot": True,
        "body_differs": True,
    }
    assert demo._kill5_pass([good]) is True
    assert demo._kill5_pass([]) is False, "an empty comparison must not demonstrate kill 5"
    for key in ("same_ordinal", "same_snapshot", "body_differs"):
        assert demo._kill5_pass([{**good, key: False}]) is False, f"kill 5 passed with {key}=False"
        assert demo._kill5_pass([good, {**good, key: False}]) is False, (
            f"kill 5 passed with one row carrying {key}=False"
        )
    assert demo._kill5_pass([{**good, "post_verdict": "fail"}]) is False
    assert demo._kill5_pass([{**good, "pre_verdict": "pass"}]) is False
    assert "0 held-out" in demo._kill5_evidence([], "local_process"), (
        "the empty-comparison sentence must not state a vacuous causal claim"
    )
    sentence = demo._kill5_evidence([good], "local_process")
    assert "same_ordinal=True" in sentence and "body_differs=True" in sentence


def _draws(db_file, run_id: str) -> list[dict]:
    conn = db.connect(db_file)
    try:
        return [
            {"family": draw.family, "variant_ref": draw.variant_ref, "cycle": draw.cycle}
            for draw in repo.list_rotation_draws_for_run(conn, run_id)
        ]
    finally:
        conn.close()


def _ordinal_of(variant_ref: str) -> int:
    """The held-out ordinal a drawn variant binds, read from the sealed index."""
    case = sealed_store.case_index().get(variant_ref)
    assert case is not None, f"unknown variant ref: {variant_ref}"
    return case.request_ordinals[0]


def _batch_texts(ordinals) -> list[str]:
    import json

    texts = []
    for ref in config.BOOKSHOP_ATTEMPT_BATCHES:
        for line in (config.FIXTURE_DIR / "requests" / ref).read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry["ordinal"] in ordinals:
                texts.append(entry["text"])
    return sorted(set(texts))


def _executed_ordinals(db_file, run_ids: list[str]) -> set[int]:
    conn = db.connect(db_file)
    try:
        return {
            output.request_ordinal
            for run_id in run_ids
            for output in repo.list_outputs(conn, run_id)
        }
    finally:
        conn.close()


def _causal_rows(db_file, pre_run_ids: list[str], post_run_id: str) -> list[dict]:
    """Same sealed case, both artifacts: the pre-repair and repaired verdicts.

    Each row holds the stimulus fixed (same sealed check, same request ordinal
    and identical request text) and reports the two verdicts, so the only thing
    that changed between them is the artifact that produced the executed answer.
    """
    conn = db.connect(db_file)
    try:
        post_run = repo.get_run(conn, post_run_id)
        pre: dict[str, list[tuple]] = {}
        for run_id in pre_run_ids:
            run = repo.get_run(conn, run_id)
            for result in repo.list_check_results(conn, run_id):
                pre.setdefault(result.check_id, []).append((run, result))

        def output_for(run_id: str, observed_ref: str):
            return next(
                (item for item in repo.list_outputs(conn, run_id) if item.id == observed_ref), None
            )

        rows = []
        for result in repo.list_check_results(conn, post_run_id):
            first = pre.get(result.check_id)
            if not first:
                continue
            pre_run, pre_result = first[0]  # the held-out stimulus's first execution
            if pre_run.artifact_version_id == post_run.artifact_version_id:
                continue
            pre_output = output_for(pre_run.id, pre_result.observed_ref)
            post_output = output_for(post_run_id, result.observed_ref)
            assert pre_output is not None and post_output is not None
            rows.append(
                {
                    "check_id": result.check_id,
                    "pre_version": pre_run.artifact_version_id,
                    "post_version": post_run.artifact_version_id,
                    "pre_verdict": pre_result.verdict,
                    "post_verdict": result.verdict,
                    "pre_reason_code": (
                        pre_result.reason_code.value if pre_result.reason_code else None
                    ),
                    "pre_request_text": pre_output.request_text,
                    "post_request_text": post_output.request_text,
                    "pre_ordinal": pre_output.request_ordinal,
                    "post_ordinal": post_output.request_ordinal,
                    "pre_snapshot": pre_run.shop_snapshot_ref,
                    "post_snapshot": post_run.shop_snapshot_ref,
                    "pre_body": base64.b64encode(pre_output.body).decode("ascii"),
                    "post_body": base64.b64encode(post_output.body).decode("ascii"),
                }
            )
        return rows
    finally:
        conn.close()


def _counts(db_file) -> dict[str, int]:
    conn = db.connect(db_file)
    try:
        return {
            table: conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
            for table in ("runs", "rotation_draws", "run_outputs", "check_results")
        }
    finally:
        conn.close()
