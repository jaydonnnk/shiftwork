"""Test 1 offline pre-proof driver (Slice 8), run on the ``local_process`` adapter.

Drives two consecutive bookshop shifts end to end on the shipped controller: shift 1
consumes its three attempts with the pre-repair trusted fixture artifact and opens
incidents, the learner freezes the repaired successor, closes (declaring the
contract's limits), the process restarts, and shift 2 inherits the version, the
decision and visible-check files, the unresolved incidents and the limits, then
draws three still-unexposed variants per family over its own attempts. The
inherited incidents resolve on shift 2's first passing run of the repaired version.

The causal comparison runs on ``local_process`` and never on ``recorded``: the same
held-out sealed stimuli are scored against outputs the pre-repair artifact produced
and outputs the repaired artifact produced, so the later consequence is caused by
execution rather than narrated (SHIFTWORK_PLAN S9, Test 1 kill condition 5).

The command writes a per-kill-condition verdict table to
``docs/plans/shiftwork/evidence/test1-central-mechanism.md``. The verdict is
PRE-PROOF PASS/FAIL, conditional on the offline executor: hostile-code isolation
and the provisioned-sandbox credential arm are deferred to Slice 14.

Run from the repository root:
  python -m demos.test1 --adapter local_process
"""

import argparse
import base64
import json
import socket
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from shiftwork import config  # noqa: E402
from shiftwork.app import create_app  # noqa: E402
from shiftwork.evaluator import evaluator  # noqa: E402
from shiftwork.ledger import chain  # noqa: E402
from shiftwork.sealed import store as sealed_store  # noqa: E402
from shiftwork.store import db, repo  # noqa: E402

CONTRACT = config.REPAIR_ARC_CONTRACT_JSON
HELD_OUT = (1, 2, 3)
FUTURE = (4, 5, 6)
TERMINAL = {"FINALIZED", "FAILED"}
EVIDENCE_PATH = REPO_ROOT / "docs" / "plans" / "shiftwork" / "evidence" / "test1-central-mechanism.md"


def _call(client: TestClient, method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        raise SystemExit(f"{method} {path} -> {response.status_code}: {response.text}")
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
    pinned = config.TRUSTED_LOCAL_FIXTURES[f"repair_arc_{stage}"][0]
    if version["content_hash"] != pinned:
        raise SystemExit(f"the frozen {stage} stage does not reproduce its pin; local_process would refuse it")
    return version


class Surfaces:
    """Every learner-visible response of a shift, kept as raw serialized text."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.entries: list[tuple[str, str]] = []

    def record(self, label: str, path: str) -> None:
        response = self.client.get(path)
        if response.status_code >= 400:
            raise SystemExit(f"GET {path} -> {response.status_code}")
        self.entries.append((label, response.text))

    def sweep(self, shift_id: str, run_ids: list[str], incident_ids: list[str]) -> None:
        self.record(f"board {shift_id}", "/api/engagements/bookshop/board")
        self.record("ledger", "/api/engagements/bookshop/ledger")
        self.record(f"artifact {shift_id}", f"/api/shifts/{shift_id}/artifact")
        for run_id in run_ids:
            self.record(f"run {run_id}", f"/api/runs/{run_id}")
            self.record(f"outputs {run_id}", f"/api/runs/{run_id}/outputs")
            self.record(f"checks {run_id}", f"/api/runs/{run_id}/checks")
        for incident_id in incident_ids:
            self.record(f"incident {incident_id}", f"/api/incidents/{incident_id}")

    def leaks(self, needles: list[str]) -> list[tuple[str, str]]:
        return [
            (label, needle)
            for label, surface in self.entries
            for needle in needles
            if needle in surface
        ]


def _rows(db_file: Path, sql: str, params: tuple = ()) -> list:
    conn = db.connect(db_file)
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def _draw_rows(db_file: Path, run_id: str) -> list[dict]:
    conn = db.connect(db_file)
    try:
        return [
            {
                "family": draw.family,
                "variant_ref": draw.variant_ref,
                "cycle": draw.cycle,
                "ordinal": sealed_store.case_index()[draw.variant_ref].request_ordinals[0],
            }
            for draw in repo.list_rotation_draws_for_run(conn, run_id)
        ]
    finally:
        conn.close()


def _future_texts() -> list[str]:
    texts = []
    for ref in config.BOOKSHOP_ATTEMPT_BATCHES:
        for line in (config.FIXTURE_DIR / "requests" / ref).read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry["ordinal"] in FUTURE:
                texts.append(entry["text"])
    return sorted(set(texts))


def _causal_rows(db_file: Path, pre_run_ids: list[str], post_run_id: str) -> list[dict]:
    conn = db.connect(db_file)
    try:
        post_run = repo.get_run(conn, post_run_id)
        first_pre: dict[str, tuple] = {}
        for run_id in pre_run_ids:
            run = repo.get_run(conn, run_id)
            for result in repo.list_check_results(conn, run_id):
                first_pre.setdefault(result.check_id, (run, result))

        def output_for(run_id: str, observed_ref: str):
            return next(
                (item for item in repo.list_outputs(conn, run_id) if item.id == observed_ref), None
            )

        rows = []
        for result in repo.list_check_results(conn, post_run_id):
            entry = first_pre.get(result.check_id)
            if entry is None:
                continue
            pre_run, pre_result = entry
            if pre_run.artifact_version_id == post_run.artifact_version_id:
                continue
            pre_output = output_for(pre_run.id, pre_result.observed_ref)
            post_output = output_for(post_run_id, result.observed_ref)
            if pre_output is None or post_output is None:
                raise SystemExit(
                    f"kill 5: a comparable output is missing for {result.check_id}"
                )
            same_ordinal = pre_output.request_ordinal == post_output.request_ordinal
            same_snapshot = pre_run.shop_snapshot_ref == post_run.shop_snapshot_ref
            body_differs = pre_output.body != post_output.body
            assert same_ordinal, (
                f"kill 5 needs the same request ordinal on both sides of {result.check_id}"
            )
            assert same_snapshot, (
                f"kill 5 needs the same shop snapshot on both sides of {result.check_id}"
            )
            assert body_differs, (
                f"kill 5 needs the two artifacts to produce different bodies for {result.check_id}"
            )
            rows.append(
                {
                    "check_id": result.check_id,
                    "pre_run": pre_run.id,
                    "pre_version": pre_run.artifact_version_id,
                    "pre_verdict": pre_result.verdict,
                    "pre_reason": pre_result.reason_code.value if pre_result.reason_code else None,
                    "pre_request": pre_output.request_text,
                    "pre_ordinal": pre_output.request_ordinal,
                    "pre_snapshot": pre_run.shop_snapshot_ref,
                    "post_run": post_run.id,
                    "post_version": post_run.artifact_version_id,
                    "post_verdict": result.verdict,
                    "post_reason": result.reason_code.value if result.reason_code else None,
                    "post_request": post_output.request_text,
                    "post_ordinal": post_output.request_ordinal,
                    "post_snapshot": post_run.shop_snapshot_ref,
                    "same_ordinal": same_ordinal,
                    "same_snapshot": same_snapshot,
                    "body_differs": body_differs,
                    "pre_body": base64.b64encode(pre_output.body).decode("ascii"),
                    "post_body": base64.b64encode(post_output.body).decode("ascii"),
                }
            )
        return sorted(rows, key=lambda row: row["check_id"])
    finally:
        conn.close()


def _rescore_runs_offline(db_file: Path, run_ids: list[str]) -> dict:
    """Re-derive every run's CheckResults from stored bytes with sockets blocked.

    Kill condition 1 made concrete: the verdicts are a pure deterministic
    reduction of the captured bytes and the sealed cases, reproducible with no
    network available at all. The case set is the one the run recorded as
    evaluated (its stored check ids resolved through the sealed index), because
    re-selecting cases today would apply the current incident state, not the
    state the run actually scored.
    """
    from shiftwork.evaluator.evaluator import SealedCaseSet

    index = sealed_store.case_index()
    conn = db.connect(db_file)
    try:
        stored = {
            run_id: [
                (result.check_id, result.verdict, result.reason_code, result.observed_ref, result.expected_ref)
                for result in repo.list_check_results(conn, run_id)
            ]
            for run_id in run_ids
        }
        payload = {
            run_id: (
                repo.list_outputs(conn, run_id),
                SealedCaseSet(cases=tuple(index[check_id] for check_id, *_ in stored[run_id])),
                repo.get_version(conn, repo.get_run(conn, run_id).artifact_version_id),
                Path(repo.get_run(conn, run_id).shop_snapshot_ref).read_text(encoding="utf-8"),
            )
            for run_id in run_ids
        }
    finally:
        conn.close()

    real_socket = socket.socket
    real_connect = socket.create_connection
    real_gai = socket.getaddrinfo
    socket.socket = socket.create_connection = socket.getaddrinfo = _network_forbidden
    try:
        replay = {}
        for run_id, (outputs, cases, version, snapshot_json) in payload.items():
            records = json.loads(snapshot_json)
            public_records = {record["record_id"]: record for record in records["records"]}
            rescued = evaluator.evaluate(outputs, cases, version.contract, public_records)
            replay[run_id] = [
                (result.check_id, result.verdict, result.reason_code, result.observed_ref, result.expected_ref)
                for result in rescued
            ]
    finally:
        socket.socket = real_socket
        socket.create_connection = real_connect
        socket.getaddrinfo = real_gai
    if not run_ids:
        raise SystemExit("kill 1: no runs to re-score; the replay would be vacuously identical")
    return {
        "runs": list(run_ids),
        "stored": sum(len(rows) for rows in stored.values()),
        "rescored": sum(len(rows) for rows in replay.values()),
        "identical": bool(run_ids)
        and all(sorted(stored[run_id]) == sorted(replay[run_id]) for run_id in run_ids),
        "mismatches": [
            run_id
            for run_id in run_ids
            if sorted(stored[run_id]) != sorted(replay[run_id])
        ],
        "details": [
            {
                "run_id": run_id,
                "check_id": check_id,
                "verdict": verdict,
                "reason_code": reason.value if reason else None,
                "observed_ref": observed_ref,
                "expected_ref": expected_ref,
            }
            for run_id in run_ids
            for check_id, verdict, reason, observed_ref, expected_ref in sorted(replay[run_id])
        ],
    }


def _network_forbidden(*_args, **_kwargs):
    raise SystemExit("network access attempted during scoring; the evaluator must run offline")


def _kill5_pass(comparison: list[dict]) -> bool:
    """Kill 5 PASS depends on the computed booleans, never on a constant sentence.

    A row supports the causal claim only when the pre-repair artifact fails, the
    repaired artifact passes, both sides ran the same request ordinal against the
    same shop snapshot, and the two output bodies differ. An empty comparison is
    not a demonstration.
    """
    return bool(comparison) and all(
        row["pre_verdict"] == "fail"
        and row["post_verdict"] == "pass"
        and row["same_ordinal"]
        and row["same_snapshot"]
        and row["body_differs"]
        for row in comparison
    )


def _kill5_evidence(comparison: list[dict], adapter: str) -> str:
    """Build the kill-5 sentence from the values the comparison actually carries."""
    if not comparison:
        return (
            f"0 held-out case rows on {adapter}: no comparable pre/post pair was "
            "found, so kill condition 5 is not demonstrated"
        )
    same_ordinal = all(row["same_ordinal"] for row in comparison)
    same_snapshot = all(row["same_snapshot"] for row in comparison)
    body_differs = all(row["body_differs"] for row in comparison)
    return (
        f"{len(comparison)} held-out case rows on {adapter}: the pre-repair artifact fails "
        f"and the repaired artifact passes, with the same request ordinal on both sides of "
        f"every row (same_ordinal={same_ordinal}), the same shop snapshot "
        f"(same_snapshot={same_snapshot}), and a different output body per row "
        f"(body_differs={body_differs})"
    )


def _scan_self_test(surfaces: "Surfaces", needles: list[str]) -> dict:
    """Prove the leak scanner can match a needle on a serialized surface (AGENTS.md S6).

    Inject the first future sentence into one collected surface, require the
    scanner to report it, restore the surface byte-for-byte and require zero. A
    count of surfaces scanned is not evidence that a needle can match.
    """
    if not surfaces.entries or not needles:
        return {"ran": False, "ok": False, "reason": "no surface or needle to inject"}
    label, original = surfaces.entries[0]
    needle = needles[0]
    surfaces.entries[0] = (label, original + needle)
    try:
        detected = surfaces.leaks([needle])
    finally:
        surfaces.entries[0] = (label, original)
    after_restore = surfaces.leaks([needle])
    return {
        "ran": True,
        "ok": bool(detected) and not after_restore,
        "surface": label,
        "needle": needle,
        "detected_after_injection": len(detected),
        "leaks_after_restore": len(after_restore),
    }


def _verdict(adapter: str, evidence: dict) -> tuple[list[dict], str]:
    replay = evidence["replay"]
    comparison = evidence["comparison"]
    inheritance = evidence["inheritance"]
    rows = [
        {
            "kill_condition": "1. Evaluation requires LLM judgement",
            "status": "PASS" if replay["identical"] else "FAIL",
            "evidence": (
                f"re-scoring the stored captures of all {len(replay['runs'])} runs against the "
                f"sealed case set each run actually scored, with sockets blocked, reproduced all "
                f"{replay['stored']} CheckResults exactly (check id, verdict, reason code, opaque "
                "expected ref)"
            ),
        },
        {
            "kill_condition": "2. Hidden cases or credentials are reachable",
            "status": "DEFERRED TO SLICE 14 (offline partial)",
            "evidence": (
                "hostile-code isolation and the provisioned-sandbox credential arm need the real "
                "tokenfactory adapter; offline they are covered by tests 16-18, 45 and 50 and are "
                "not re-demonstrated here. The offline executor accepts only pinned trusted "
                "fixtures and scrubs the child environment."
            ),
        },
        {
            "kill_condition": "3. Semantic replays disagree",
            "status": (
                "PASS"
                if evidence["chain_valid"] and all(evidence["versions_reproduce_pins"])
                else "FAIL"
            ),
            "evidence": (
                f"the ledger hash chain verifies ({evidence['chain_status']}) over "
                f"{evidence['event_count']} events, and both frozen versions reproduce their pinned "
                f"content hash on freeze and again on read ({evidence['versions_reproduce_pins']})"
            ),
        },
        {
            "kill_condition": "4. Artifact and state do not carry forward",
            "status": "PASS" if inheritance["ok"] else "FAIL",
            "evidence": inheritance["detail"],
        },
        {
            "kill_condition": "5. The later consequence is narrated instead of caused by execution",
            "status": "PASS" if _kill5_pass(comparison) else "FAIL",
            "evidence": _kill5_evidence(comparison, adapter),
        },
    ]
    deferred = [row for row in rows if row["status"].startswith("DEFERRED")]
    failed = [row for row in rows if row["status"] == "FAIL"]
    result = "PRE-PROOF FAIL" if failed else "PRE-PROOF PASS"
    if deferred:
        result += " (conditional on the offline executor: kill condition 2 deferred to Slice 14)"
    return rows, result


def _markdown(evidence: dict, rows: list[dict], result: str) -> str:
    def block(title: str, payload) -> str:
        return f"### {title}\n\n```json\n{json.dumps(payload, indent=2, sort_keys=True)}\n```\n"

    table = "\n".join(
        f"| {row['kill_condition']} | {row['status']} | {row['evidence']} |" for row in rows
    )
    draws = "\n".join(
        f"| {run} | {', '.join(f'{d['family']}={d['variant_ref']} (ord {d['ordinal']}, cycle {d['cycle']})' for d in draws_of)} |"
        for run, draws_of in evidence["draws"].items()
    )
    runs = "\n".join(
        f"| {run['id']} | shift {run['shift']} | attempt {run['attempt']} | {run['version']} | "
        f"{run['batch']} | {run['state']} | {run['checks']} |"
        for run in evidence["runs"]
    )
    comparison = "\n".join(
        f"| {row['check_id']} | {row['pre_run']} ({row['pre_version']}) | {row['pre_verdict']} "
        f"({row['pre_reason']}) | {row['post_run']} ({row['post_version']}) | {row['post_verdict']} |"
        for row in evidence["comparison"]
    )
    return f"""# Test 1 offline pre-proof: central mechanism

Command: `python -m demos.test1 --adapter {evidence['adapter']}`
Date: {evidence['date']}
Result: **{result}**

This is the offline pre-proof, not the full Test 1 verdict: two of Test 1's kill
conditions are only partially adjudicated offline (S3 of the approved slice plan).
The pre-proof runs on the `local_process` adapter with operator-pinned trusted
fixture artifacts; `recorded` executes nothing and cannot show that the artifact
caused the outcome, so it is never used for the causal comparison.

## Per-kill-condition verdict

| Kill condition | Status | Evidence |
|---|---|---|
{table}

## The arc

Shift 1 runs the pre-repair fixture, repairs to the pinned successor version and
closes; the process restarts; shift 2 inherits and runs three attempts drawing
still-unexposed variants. Draws per attempt:

| run | draws |
|---|---|
{draws}

| run | shift | attempt | version | batch | state | checks |
|---|---|---|---|---|---|---|
{runs}

Inherited state on shift 2: the artifact version `{evidence['inheritance']['version']}` with
its files reproduced byte-for-byte ({evidence['inheritance']['files']}), the declared limit in
`unresolved_limits`, and {evidence['inheritance']['incidents']} unresolved incidents resolved by
run `{evidence['inheritance']['resolver']}` (shift 2 attempt {evidence['inheritance']['resolver_attempt']},
the first run to resolve any at ledger seq {evidence['inheritance']['resolver_seq']};
{evidence['resolutions']} INCIDENT_RESOLVED events).

## Causal comparison (operator-only, same held-out stimuli)

| sealed case | pre-repair run | verdict | repaired run | verdict |
|---|---|---|---|---|
{comparison}

{block('Re-scored CheckResults (offline replay)', evidence['replay']['details'])}
{block('Ledger replay', evidence['ledger_replay'])}
{block('Future-wording scan', evidence['scan'])}

## Deferred to Slice 14

- Hostile-code isolation: a genuinely hostile artifact is never executed offline.
- The provisioned-sandbox credential arm of test 50 (the `tokenfactory` arm).
The full Test 1 PASS/FAIL verdict is recorded at Slice 14 on the real adapter.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Test 1 offline pre-proof driver.")
    parser.add_argument(
        "--adapter",
        default="local_process",
        choices=("local_process", "recorded", "tokenfactory"),
        help="executor the controller is configured with",
    )
    parser.add_argument("--evidence", default=str(EVIDENCE_PATH), help="evidence markdown path")
    args = parser.parse_args()

    if args.adapter == "recorded":
        raise SystemExit(
            "recorded replays bytes and executes nothing, so it cannot show the artifact caused "
            "the outcome; the pre-proof runs on --adapter local_process"
        )
    if args.adapter == "tokenfactory":
        raise SystemExit("the tokenfactory adapter lands at Slice 14; run --adapter local_process")

    import datetime

    date = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
    workdir = tempfile.TemporaryDirectory(prefix="shiftwork-test1-")
    db_file = Path(workdir.name) / "test1.db"

    with TestClient(create_app(str(db_file), executor=args.adapter)) as client:
        surfaces = Surfaces(client)
        shift_one = _open(client)
        version_one = _freeze_stage(client, shift_one, "pre")
        runs = []
        for attempt in range(1, len(HELD_OUT) + 1):
            run = _attempt(client, shift_one)
            if run["state"] != "FINALIZED":
                raise SystemExit(f"shift 1 attempt {attempt} did not finalize: {run}")
            runs.append(("shift1", run))
            surfaces.sweep(shift_one, [item["id"] for _, item in runs], [])
        incidents = _call(client, "GET", "/api/engagements/bookshop/board")["incidents"]
        surfaces.sweep(shift_one, [item["id"] for _, item in runs], [i["id"] for i in incidents])
        version_two = _freeze_stage(client, shift_one, "post")
        _call(client, "POST", f"/api/shifts/{shift_one}/close")
        surfaces.sweep(shift_one, [item["id"] for _, item in runs], [i["id"] for i in incidents])
        shift_one_run_ids = [item["id"] for _, item in runs]

    # Shift 2's surfaces are collected after the scan's scope: the future-wording
    # assertion covers the first shift only, because these stimuli are legitimately
    # released once their own run executes them.
    with TestClient(create_app(str(db_file), executor=args.adapter)) as client:
        shifted_surfaces = Surfaces(client)
        shift_two = _open(client)
        second_runs = []
        for attempt in range(1, len(HELD_OUT) + 1):
            run = _attempt(client, shift_two)
            if run["state"] != "FINALIZED":
                raise SystemExit(f"shift 2 attempt {attempt} did not finalize: {run}")
            second_runs.append(("shift2", run))
            shifted_surfaces.sweep(shift_two, [item["id"] for _, item in second_runs], [])
        board_two = _call(client, "GET", "/api/engagements/bookshop/board")
        draft_two = _call(client, "GET", f"/api/shifts/{shift_two}/artifact")
        ledger = _call(client, "GET", "/api/engagements/bookshop/ledger")

    # --- evidence gathering (direct reads, operator-only) -------------------------
    comparison = _causal_rows(db_file, shift_one_run_ids, second_runs[0][1]["id"])
    replay = _rescore_runs_offline(db_file, shift_one_run_ids + [r[1]["id"] for r in second_runs])
    conn = db.connect(db_file)
    try:
        events = repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)
        status = chain.verify_chain(events)
        incidents_two = repo.list_incidents(conn, config.BOOKSHOP_SLUG)
        versions = [
            repo.get_version(conn, version_one["id"]),
            repo.get_version(conn, version_two["id"]),
        ]
        run_rows = [
            {
                "id": run.id,
                "shift": run.shift_id,
                "attempt": run.attempt_number,
                "version": run.artifact_version_id,
                "batch": run.request_batch_ref,
                "state": run.state.value,
                "checks": len(repo.list_check_results(conn, run.id)),
            }
            for run in repo.list_runs(conn, config.BOOKSHOP_SLUG)
        ]
    finally:
        conn.close()
    future_texts = _future_texts()
    leaks = surfaces.leaks(future_texts)
    scan_self_test = _scan_self_test(surfaces, future_texts)

    # MINOR-2: derive "the first passing run" from the ledger instead of asserting
    # it in prose. Every INCIDENT_RESOLVED event cites its resolving run as
    # cause_refs[0]; the first resolver is the one at the minimum resolving seq.
    resolving = [
        (event.seq, event.cause_refs[0])
        for event in events
        if event.event_type.value == "INCIDENT_RESOLVED" and event.cause_refs
    ]
    resolving_run_ids = sorted({ref for _, ref in resolving})
    first_resolving_seq = min((seq for seq, _ in resolving), default=None)
    first_resolving_run = next(
        (ref for seq, ref in resolving if seq == first_resolving_seq), None
    )
    run_by_id = {row["id"]: row for row in run_rows}
    resolver_row = run_by_id.get(first_resolving_run) if first_resolving_run else None
    resolver_attempt = resolver_row["attempt"] if resolver_row else None
    resolver_version = resolver_row["version"] if resolver_row else None
    shift_two_attempts = [row["attempt"] for row in run_rows if row["shift"] == shift_two]
    single_resolver = len(resolving_run_ids) == 1
    resolver_version_ok = resolver_version == version_two["id"]
    resolver_is_first_attempt = (
        resolver_row is not None
        and resolver_row["shift"] == shift_two
        and bool(shift_two_attempts)
        and resolver_attempt == min(shift_two_attempts)
    )

    if board_two["latest_version"] is None:
        raise SystemExit("kill 4: the board showed no inherited version after the restart")
    inheritance = {
        "ok": (
            board_two["latest_version"]["id"] == version_two["id"]
            and draft_two["files"] == config.repair_arc_artifact_files("post")
            and board_two["unresolved_limits"] == [config.REPAIR_ARC_DECLARED_LIMIT]
            and len(board_two["incidents"]) == 0
            and {incident.state.value for incident in incidents_two} == {"RESOLVED"}
            and single_resolver
            and resolver_version_ok
            and resolver_is_first_attempt
        ),
        "version": version_two["id"],
        "files": sorted(draft_two["files"]),
        "incidents": len(incidents_two),
        "resolver": first_resolving_run,
        "resolver_attempt": resolver_attempt,
        "resolver_version": resolver_version,
        "resolver_seq": first_resolving_seq,
        "detail": (
            f"after the restart, shift 2 shows the inherited version {version_two['id']} with its "
            f"{len(draft_two['files'])} files (decision log and visible-check file included), the "
            f"declared limit in unresolved_limits, and all {len(incidents_two)} inherited incidents "
            f"resolved by run {first_resolving_run} (shift 2 attempt {resolver_attempt}, version "
            f"{resolver_version}, the first run to resolve any at ledger seq {first_resolving_seq})"
        ),
    }
    evidence = {
        "adapter": args.adapter,
        "date": date,
        "version_one": version_one["id"],
        "version_two": version_two["id"],
        "runs": run_rows,
        "draws": {run_id: _draw_rows(db_file, run_id) for run_id in shift_one_run_ids + [r[1]["id"] for r in second_runs]},
        "comparison": comparison,
        "replay": replay,
        "chain_status": status.value,
        "chain_valid": status is chain.ChainStatus.VALID,
        "event_count": len(events),
        "ledger_replay": {
            "chain_status": status.value,
            "events": [
                {"seq": event.seq, "type": event.event_type.value, "cause_refs": list(event.cause_refs)}
                for event in events
            ],
            "board_totals": board_two["ledger_totals"],
        },
        "scan": {
            "surfaces": [label for label, _ in surfaces.entries],
            "future_texts": future_texts,
            "leaks": leaks,
            "self_test": scan_self_test,
        },
        "resolutions": sum(1 for event in events if event.event_type.value == "INCIDENT_RESOLVED"),
        "versions_reproduce_pins": [
            version_one["content_hash"] == config.TRUSTED_LOCAL_FIXTURES["repair_arc_pre"][0],
            version_two["content_hash"] == config.TRUSTED_LOCAL_FIXTURES["repair_arc_post"][0],
        ],
    }
    evidence["inheritance"] = inheritance
    rows, result = _verdict(args.adapter, evidence)

    if leaks:
        raise SystemExit(f"future customer wording leaked before its run: {leaks[:3]}")
    if not scan_self_test.get("ok"):
        raise SystemExit(f"the future-wording leak scanner failed its self-test: {scan_self_test}")
    if not all(evidence["versions_reproduce_pins"]):
        raise SystemExit("a frozen version did not reproduce its pinned content hash")
    if [version.content_hash for version in versions] != [
        config.TRUSTED_LOCAL_FIXTURES["repair_arc_pre"][0],
        config.TRUSTED_LOCAL_FIXTURES["repair_arc_post"][0],
    ]:
        raise SystemExit("a stored version no longer reproduces its pinned hash on read")

    for run in run_rows:
        print(
            f"  {run['id']} {run['shift']} attempt {run['attempt']} {run['batch']} "
            f"{run['state']} checks={run['checks']}"
        )
    for row in comparison:
        print(
            f"  causal {row['check_id']}: pre {row['pre_verdict']} ({row['pre_reason']}) -> "
            f"post {row['post_verdict']} on the same stimulus"
        )
    print("kill-condition verdicts:")
    for row in rows:
        print(f"  {row['status']:<38} {row['kill_condition']}")
    print(f"  surfaces scanned for future customer wording: {len(surfaces.entries)} (leaks: {len(leaks)})")
    print(
        "  leak scanner self-tested: injected future sentence detected="
        f"{scan_self_test.get('detected_after_injection')}, leaks after restore="
        f"{scan_self_test.get('leaks_after_restore')} (ok={scan_self_test.get('ok')})"
    )
    print(f"  ledger: {len(events)} events, chain {status.value}; resolutions {evidence['resolutions']}")
    print(
        f"  re-scored offline with sockets blocked: {len(replay['runs'])} runs, "
        f"{replay['stored']} stored / {replay['rescored']} rescored, identical={replay['identical']}"
    )

    evidence_path = Path(args.evidence)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(_markdown(evidence, rows, result), encoding="utf-8")
    print(f"  evidence written to {evidence_path}")
    print(f"test1 pre-proof complete: {result}")
    return 0 if result.startswith("PRE-PROOF PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
