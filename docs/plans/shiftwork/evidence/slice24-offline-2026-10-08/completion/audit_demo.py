"""Read-only audit of the retained shipped-material and operator-review demos."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3

from shiftwork import orchestrator
from shiftwork.domain.models import LedgerEventType, RunPurpose
from shiftwork.ledger import chain
from shiftwork.store import repo

OUT = Path(__file__).resolve().parent


def audit(directory, operator_review):
    proof = json.loads((directory / "journey.json").read_bytes())
    database = directory / "journey.db"
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    assert before == proof["database_sha256"]
    conn = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    try:
        events = repo.list_ledger_events(conn, "gtm")
        assert chain.verify_chain(events) is chain.ChainStatus.VALID
        assert all(event.synthetic for event in events)
        runs = {row["id"]: dict(row) for row in conn.execute("SELECT * FROM runs")}
        outputs = {row["id"]: dict(row) for row in conn.execute("SELECT * FROM run_outputs")}
        checks = {row["id"]: dict(row) for row in conn.execute("SELECT * FROM check_results")}
        business_types = {LedgerEventType.OWNER_ASSIGNED, LedgerEventType.SLA_CLOCK_STARTED,
                          LedgerEventType.HANDOFF_ESCALATED, LedgerEventType.INCIDENT_OPENED,
                          LedgerEventType.INCIDENT_RESOLVED}
        for event in events:
            if event.event_type not in business_types:
                continue
            run = runs[event.cause_refs[0]]
            assert run["purpose"] == RunPurpose.OPERATION.value
            check = checks[event.cause_refs[1]]
            assert check["run_id"] == run["id"]
            if event.event_type is not LedgerEventType.INCIDENT_RESOLVED:
                output = outputs[event.cause_refs[2]]
                assert output["run_id"] == run["id"] and check["observed_ref"] == output["id"]
            if event.event_type is LedgerEventType.INCIDENT_OPENED:
                assert event.payload["reason_code"] == check["reason_code"]
                trace = event.payload["decision_trace"]
                assert [row["task_id"] for row in trace] == ["qualification", "owner", "write", "handoff"]
                assert event.payload["failed_task_ids"]
        operation_id = proof["operation"]["id"]
        repeated_id = proof["reprocessing" if operator_review else "inherited_reprocessing"]["id"]
        operation = repo.get_run(conn, operation_id)
        repeated = repo.get_run(conn, repeated_id)
        assert operation.artifact_version_id == repeated.artifact_version_id
        assert operation.selection_id == repeated.selection_id
        replay = {run_id: orchestrator.replay_assessment(conn, run_id).model_dump(mode="json")
                  for run_id in (operation_id, repeated_id)}
        assert all(row["status"] == "IDENTICAL" and not row["wrote_rows"] for row in replay.values())
        assert orchestrator._stored_operation_drafts(conn, repeated, "gtm") == []
        operation_events = orchestrator._stored_operation_drafts(conn, operation, "gtm")
        expected = ["OWNER_ASSIGNED", "SLA_CLOCK_STARTED"] + (["HANDOFF_ESCALATED"] if operator_review else [])
        assert [row["event_type"] for row in operation_events if row["event_type"] != "INCIDENT_RESOLVED"] == expected
        if not operator_review:
            later = proof["later_comparison"]
            assert len(later["trials"]) == 6 and all(row["state"] == "COMPLETE" for row in later["trials"])
            assert {row["artifact_version_id"] for row in later["candidates"]} == {
                proof["selected_version_id"], proof["retained_version_id"]}
        assert conn.total_changes == 0
        result = {"status": "PASS", "mode": proof["mode"], "database_sha256": before,
                  "runs": len(runs), "captured_outputs": len(outputs), "checks": len(checks),
                  "event_counts": dict(Counter(event.event_type.value for event in events)),
                  "selected_operation": operation_id, "reprocessing": repeated_id,
                  "replays": replay, "source_rows_written": conn.total_changes}
    finally:
        conn.close()
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    return result


def main():
    result = {"shipped_material": audit(OUT / "demo", False),
              "disposable_operator_review": audit(OUT / "queue-consistent-demo", True)}
    destination = OUT / "demo-audit.json"
    assert not destination.exists()
    destination.write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps({key: {field: row[field] for field in ("status", "runs", "captured_outputs", "event_counts")}
                      for key, row in result.items()}))


if __name__ == "__main__":
    main()
