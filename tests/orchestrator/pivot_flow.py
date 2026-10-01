"""Shared HTTP flow builders for the Slice 17/18/20 pivot orchestrator suites.

Every builder drives the real routes over a real database. The staged observed
condition is a test/demo-only derivation of the reviewed comparison state: one
dependency is flipped to ``unavailable`` so the controller can freeze an
observed outage without shipping new reviewed material. No checked-in fixture is
modified, and the staged bytes are labelled as such wherever they are printed.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from shiftwork import config

TERMINAL = {"FINALIZED", "FAILED"}


def wait_run(client: TestClient, run_id: str, *, deadline_s: float = 90) -> dict:
    deadline = time.monotonic() + deadline_s
    while True:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["state"] in TERMINAL or time.monotonic() > deadline:
            return run
        time.sleep(0.02)


def wait_experiment(client: TestClient, experiment_id: str, *, deadline_s: float = 90) -> dict:
    deadline = time.monotonic() + deadline_s
    while True:
        view = client.get(f"/api/experiments/{experiment_id}").json()
        if view["state"] in TERMINAL or time.monotonic() > deadline:
            return view
        time.sleep(0.02)


def freeze_candidate(client: TestClient, shift_id: str, label: str) -> dict:
    saved = client.put(
        f"/api/shifts/{shift_id}/artifact",
        json={"files": config.comparison_candidate_files(label)},
    )
    assert saved.status_code == 200, saved.text
    frozen = client.post(
        f"/api/shifts/{shift_id}/artifact/versions",
        json={"contract": config.PIVOT_STARTER_CONTRACT_JSON},
    )
    assert frozen.status_code == 201, frozen.text
    return frozen.json()


def qualified_shift(client: TestClient, *, choose: str = "A", prefix: str = "s20-flow") -> dict:
    """One shift through comparison and an explicit choice of the pinned candidates.

    The reviewed starter is frozen and run as the public source, the investigation
    cites that run, both pinned candidates freeze, the qualifying comparison runs
    its six slots, and the learner explicitly chooses ``choose`` with the other
    candidate retained. Returns the exact IDs the later clauses compare against.
    """
    shift = client.post("/api/engagements/bookshop/shifts")
    assert shift.status_code == 201, shift.text
    shift_id = shift.json()["id"]
    starter = client.post(
        f"/api/shifts/{shift_id}/artifact/versions",
        json={"contract": config.PIVOT_STARTER_CONTRACT_JSON},
    )
    assert starter.status_code == 201, starter.text
    source = client.post(f"/api/shifts/{shift_id}/runs")
    assert source.status_code == 202, source.text
    source_run = wait_run(client, source.json()["id"])
    assert source_run["state"] == "FINALIZED", source_run
    investigation = client.post(f"/api/shifts/{shift_id}/investigations", json={
        "source_run_id": source_run["id"], "source_request_ordinal": 1,
        "cause": "the starter omits a required collection task",
        "falsifier": "the reviewed collection request still lacks that task result",
        "public_test": "require every declared task result",
        "revision_of_id": None, "client_request_id": f"{prefix}-investigation",
    })
    assert investigation.status_code == 201, investigation.text
    candidates = {label: freeze_candidate(client, shift_id, label) for label in ("A", "B")}
    created = client.post(f"/api/shifts/{shift_id}/experiments", json={
        "kind": "QUALIFYING_COMPARISON",
        "investigation_id": investigation.json()["id"],
        "candidate_a_version_id": candidates["A"]["id"],
        "candidate_b_version_id": candidates["B"]["id"],
        "declared_treatment": "A chooses lowest price; B chooses highest stock",
        "client_request_id": f"{prefix}-comparison",
    })
    assert created.status_code == 202, created.text
    comparison = wait_experiment(client, created.json()["id"])
    assert comparison["outcome"]["status"] == "COMPLETE", comparison
    assert all(item["eligible"] for item in comparison["outcome"]["eligibility"]), comparison
    retained = "B" if choose == "A" else "A"
    prior = client.get("/api/engagements/bookshop/board").json()["operating_selection"]
    choice = client.post(f"/api/shifts/{shift_id}/selections", json={
        "comparison_id": comparison["id"],
        "selected_version_id": candidates[choose]["id"],
        "rationale": "A completed the required tasks under the shared conditions.",
        "expected_prior_selection_id": prior["id"] if prior else None,
        "client_request_id": f"{prefix}-choice",
    })
    assert choice.status_code == 201, choice.text
    return {
        "shift_id": shift_id,
        "starter": starter.json(),
        "source_run": source_run,
        "candidates": candidates,
        "comparison": comparison,
        "choice": choice.json(),
        "chosen_label": choose,
        "retained_label": retained,
        "selected_version_id": candidates[choose]["id"],
        "retained_version_id": candidates[retained]["id"],
    }


def open_successor(client: TestClient) -> dict:
    """Close the current shift and open the next one from the exact selection."""
    board = client.get("/api/engagements/bookshop/board").json()
    closed = client.post(f"/api/shifts/{board['latest_shift']['id']}/close")
    assert closed.status_code == 200, closed.text
    opened = client.post("/api/engagements/bookshop/shifts")
    assert opened.status_code == 201, opened.text
    return opened.json()


def staged_outage_state(
    tmp_path: Path, *, dependency: str = "collection", source: Path | None = None
) -> Path:
    """A derived public state with one dependency observed unavailable.

    The bytes come from the reviewed comparison state so the derived state keeps
    its records and entities; only the named dependency's observed availability
    changes. This stages an operator-side world change for tests and demos and is
    never presented as reviewed product material.
    """
    base = source or config.PIVOT_COMPARE_STATE
    data = json.loads(base.read_bytes().decode("utf-8"))
    data["dependencies"] = {**data["dependencies"], dependency: "unavailable"}
    path = tmp_path / f"observed-outage-{dependency}-{base.stem}.json"
    path.write_bytes(json.dumps(data, indent=2, sort_keys=True).encode("utf-8"))
    return path


PRIOR_HISTORY_TABLES = (
    "operating_selections",
    "runs",
    "run_outputs",
    "check_results",
    "run_assessments",
    "task_assessments",
    "incidents",
    "ledger_events",
    "exposure_reservations",
    "exposure_items",
)


def snapshot_rows(conn, tables=PRIOR_HISTORY_TABLES) -> dict:
    """Serialized rows of the durable history tables, in rowid order."""
    from demos.final_pivot import snapshot_v5_rows

    full = snapshot_v5_rows(conn)
    return {table: full[table] for table in tables}


def assert_prefix_unchanged(conn, before: dict) -> None:
    """Every row that existed before is still byte-identical, and none vanished."""
    from demos.final_pivot import _bytes

    for table, (columns, expected) in before.items():
        rows = conn.execute(f"SELECT {', '.join(columns)} FROM {table} ORDER BY rowid").fetchall()
        serialized = tuple(b"".join(_bytes(value) for value in row) for row in rows)
        assert len(serialized) >= len(expected), f"rows disappeared from {table}"
        assert serialized[: len(expected)] == expected, f"historical {table} bytes changed"
