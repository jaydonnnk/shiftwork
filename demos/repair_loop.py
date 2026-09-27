"""Slice 7 evidence: budget, rotation draws, incidents and the repair loop.

Drives one bookshop shift through three attempts entirely over HTTP against the
real controller and database:

  attempt 1  the shipped version fails every enabled family's first variant
             (MISSING_EVIDENCE) and opens one incident per family, carrying
             reason codes only;
  repair     the learner edits the artifact and freezes a NEW version;
  attempt 2  the run re-scores the incidents' linked regressions together with
             the drawn second variants; every incident resolves, each with a
             hash-chained INCIDENT_RESOLVED event;
  attempt 3  a third distinct attempt draws the third variant per family.

Prints the draw table (family, variant ref, cycle), the incident states and the
final chain status. Offline and deterministic: the controller's shipped run
binding resolves each attempt's authored transcript from the batch and snapshot
that run persisted (Slice 8), with no config or environment mutation anywhere in
this demo.

Run from the repository root: python -m demos.repair_loop
"""

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
from shiftwork.store import db, repo  # noqa: E402

TERMINAL_RUN_STATES = {"FINALIZED", "FAILED"}
CONTRACT = {
    "catalog_version": 2,
    "must_never": ["NEVER_INVENT_PRICE_STOCK_POLICY"],
    "selections": {"STANCE": "USE_NEWEST_RECORD_WITH_AGE"},
    "response_time_limit_ms": 3000,
    "declared_limits": [],
}


def _call(client: TestClient, method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    body = response.json()
    if response.status_code >= 400:
        raise SystemExit(f"{method} {path} -> {response.status_code}: {body}")
    return response.status_code, body


def _poll_run(client: TestClient, run_id: str) -> dict:
    run = _call(client, "GET", f"/api/runs/{run_id}")[1]
    while run["state"] not in TERMINAL_RUN_STATES:
        time.sleep(0.05)
        run = _call(client, "GET", f"/api/runs/{run_id}")[1]
    return run


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="shiftwork-repair-") as workdir:
        db_file = str(Path(workdir) / "repair.db")
        with TestClient(create_app(db_file)) as client:
            _, shift = _call(client, "POST", "/api/engagements/bookshop/shifts")
            shift_id = shift["id"]
            _call(
                client,
                "POST",
                f"/api/shifts/{shift_id}/artifact/versions",
                json={"contract": CONTRACT},
            )

            # Attempt 1: the shipped version fails every family's first variant.
            _, started = _call(client, "POST", f"/api/shifts/{shift_id}/runs")
            run_one = _poll_run(client, started["id"])
            assert run_one["state"] == "FINALIZED", run_one

            _, board = _call(client, "GET", "/api/engagements/bookshop/board")
            opened = board["incidents"]
            assert len(opened) == 3, f"expected one incident per enabled family, got {opened}"
            assert all(incident["reason_code"] == "MISSING_EVIDENCE" for incident in opened)

            # Repair: edit the artifact and freeze a new version.
            _, draft = _call(client, "GET", f"/api/shifts/{shift_id}/artifact")
            files = dict(draft["files"])
            files["service.py"] += "\n# repair: cite evidence with every factual claim\n"
            _call(client, "PUT", f"/api/shifts/{shift_id}/artifact", json={"files": files})
            status, version = _call(
                client,
                "POST",
                f"/api/shifts/{shift_id}/artifact/versions",
                json={"contract": CONTRACT},
            )
            assert status == 201, version

            # Attempt 2: regressions and the drawn second variants all pass.
            _, started = _call(client, "POST", f"/api/shifts/{shift_id}/runs")
            run_two = _poll_run(client, started["id"])
            assert run_two["state"] == "FINALIZED", run_two
            _, board = _call(client, "GET", "/api/engagements/bookshop/board")
            assert board["incidents"] == [], f"incidents did not resolve: {board['incidents']}"

            # Attempt 3: a third distinct attempt draws a third variant per family.
            _, started = _call(client, "POST", f"/api/shifts/{shift_id}/runs")
            run_three = _poll_run(client, started["id"])
            assert run_three["state"] == "FINALIZED", run_three

            _, ledger = _call(client, "GET", "/api/engagements/bookshop/ledger")
            assert ledger["chain_status"] == "VALID", ledger["chain_status"]
            _, board = _call(client, "GET", "/api/engagements/bookshop/board")
            assert board["attempts_used"] == 3 and board["attempts_remaining"] == 0

        conn = db.connect(db_file)
        try:
            draws = repo.list_rotation_draws(conn, config.BOOKSHOP_SLUG)
            incidents = repo.list_incidents(conn, config.BOOKSHOP_SLUG)
            runs = repo.list_runs(conn, config.BOOKSHOP_SLUG)
        finally:
            conn.close()

    by_family: dict[str, list] = {}
    for draw in draws:
        by_family.setdefault(draw.family, []).append(draw)
    assert sorted(len(group) for group in by_family.values()) == [3, 3, 3], (
        f"expected three draws per enabled family, got {by_family}"
    )
    for family, group in sorted(by_family.items()):
        refs = [draw.variant_ref for draw in group]
        assert len(set(refs)) == 3, f"{family} redrew an exposed variant: {refs}"
        assert [draw.cycle for draw in group] == [1, 1, 1], f"{family} cycle drifted: {group}"
    assert all(incident.state.value == "RESOLVED" for incident in incidents), incidents
    assert all(incident.resolving_version_id == version["id"] for incident in incidents)
    resolution_events = [event for event in ledger["events"] if event["event_type"] == "INCIDENT_RESOLVED"]
    assert len(resolution_events) == 3, f"expected three resolution events, got {resolution_events}"

    print("draws per attempt (family, variant, cycle):")
    for run in runs:
        refs = sorted(
            f"{draw.family}={draw.variant_ref}" for draw in draws if draw.run_id == run.id
        )
        print(f"  {run.id} attempt {run.attempt_number} batch {run.request_batch_ref}: " + ", ".join(refs))
    for incident in incidents:
        print(
            f"  incident {incident.id} {incident.reason_code.value} state={incident.state.value} "
            f"resolving_version={incident.resolving_version_id} event_seq={incident.resolved_event_seq}"
        )
    print(f"  board attempts_used={board['attempts_used']} remaining={board['attempts_remaining']} chain={board['chain_status']}")
    print(
        f"repair-loop evidence complete: run {run_one['id']} failed every first variant and opened "
        f"{len(opened)} incidents (reason codes only), repair froze {version['id']}, run {run_two['id']} "
        f"passed the three linked regressions and the three drawn second variants and resolved all "
        f"incidents with {len(resolution_events)} hash-chained INCIDENT_RESOLVED events, run "
        f"{run_three['id']} drew the third distinct variant per family, chain "
        f"{ledger['chain_status']} with {len(ledger['events'])} events"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
