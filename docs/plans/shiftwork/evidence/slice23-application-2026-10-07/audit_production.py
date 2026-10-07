"""Read-only cross-check of the retained trusted-local database and API receipt."""
import hashlib
import json
from pathlib import Path
import sqlite3

OUT = Path(__file__).resolve().parent


def main():
    proof = json.loads((OUT / "production-retained.json").read_bytes())
    database = OUT / "production-retained.db"
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    assert before == proof["database_sha256"], "retained database binding drift"
    assert proof["mode"] == "PRODUCTION_REVIEWED_TRUSTED_LOCAL"
    assert proof["production_sealed"] is True and proof["production_admitted"] is True
    conn = sqlite3.connect(database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only=ON")
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        comparison = proof["comparison"]
        experiment = conn.execute("SELECT * FROM experiments WHERE id=?", (comparison["id"],)).fetchone()
        assert experiment["state"] == "FINALIZED" and comparison["outcome"]["status"] == "COMPLETE"
        context = conn.execute("SELECT * FROM execution_contexts WHERE id=?", (experiment["context_id"],)).fetchone()
        assert context["engagement_slug"] == "gtm" and context["content_hash"] == comparison["context_hash"]
        workloads = json.loads(context["workloads_json"])
        assert [w["request_count"] for w in workloads] == [3, 3, 3]
        slots = conn.execute("SELECT * FROM trial_slots WHERE experiment_id=? ORDER BY execution_ordinal", (experiment["id"],)).fetchall()
        assert len(slots) == 6
        assert [(s["pair_ordinal"], s["candidate_label"]) for s in slots] == [(1, "A"), (1, "B"), (2, "B"), (2, "A"), (3, "A"), (3, "B")]
        candidate_pins = proof["production_fixture_pins"]
        for pair in (1, 2, 3):
            a, b = [s for s in slots if s["pair_ordinal"] == pair]
            assert a["request_batch_hash"] == b["request_batch_hash"] == workloads[pair - 1]["request_batch_hash"]
            assert a["protected_variant_refs_json"] == b["protected_variant_refs_json"]
            assert len(json.loads(a["protected_variant_refs_json"])) == 1
        for slot in slots:
            assert slot["state"] == "COMPLETE" and slot["request_count"] == 3 and slot["executed_request_count"] == 4
            run = conn.execute("SELECT * FROM runs WHERE id=?", (slot["run_id"],)).fetchone()
            assert run["state"] == "FINALIZED" and run["adapter"] == "local_process" and run["purpose"] == "EXPERIMENT"
            assert run["context_id"] == context["id"] and run["artifact_version_id"] == slot["artifact_version_id"]
            version = conn.execute("SELECT * FROM artifact_versions WHERE id=?", (run["artifact_version_id"],)).fetchone()
            assert version["content_hash"] == candidate_pins["gtm_compare_candidate_" + slot["candidate_label"].lower()][0]
            outputs = conn.execute("SELECT * FROM run_outputs WHERE run_id=? ORDER BY request_ordinal", (run["id"],)).fetchall()
            assert [row["request_ordinal"] for row in outputs] == [1, 2, 3, 4]
            assert all(row["http_status"] == 200 and row["transport_error"] is None for row in outputs)
        snapshots = conn.execute("SELECT * FROM protected_case_snapshots").fetchall()
        assert len(snapshots) == len({row["variant_ref"] for row in snapshots}) == 3
        assert {row["variant_ref"] for row in snapshots} == {ref for slot in slots for ref in json.loads(slot["protected_variant_refs_json"])}
        assert all(item["eligible"] for item in comparison["outcome"]["eligibility"])
        assert [(item["public_denominator_requests"], item["protected_denominator"], item["protected_passed"])
                for item in comparison["outcome"]["candidate_metrics"]] == [(9, 3, 3), (9, 3, 3)]
        assert proof["business_rows_before"] == proof["business_rows_after"]
        for table, rows in proof["business_rows_after"].items():
            assert [list(row) for row in conn.execute("SELECT * FROM " + table + " ORDER BY rowid")] == rows
        starter = proof["starter"]["id"]
        assert {(row["task_id"], tuple(json.loads(row["reason_codes_json"]))) for row in conn.execute(
            "SELECT task_id,reason_codes_json FROM task_assessments WHERE run_id=? AND mandatory_pass=0", (starter,))} == {
                ("owner", ("WRONG_ACTION",)), ("write", ("WRONG_ACTION",))}
        events = conn.execute("SELECT * FROM assist_events ORDER BY created_at").fetchall()
        assert [row["role"] for row in events] == proof["assist_roles"] == ["HINT", "DIAGNOSIS"]
        assert all(row["state"] == "COMPLETE" and row["proposed_patch"] is None and row["reported_model_id"] is None for row in events)
        assert proof["assist_gateway"] == "FAKE_NO_MODEL_CALL"
        assert conn.execute("SELECT count(*) FROM run_outputs").fetchone()[0] == 25
    finally:
        conn.close()
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    result = {"status": "PASS", "database_sha256": before, "database_unchanged": True,
              "fair_paired_slots": 6, "public_requests_per_candidate": 9,
              "shared_protected_variants": 3, "verified_captures": 25,
              "both_candidates_eligible": True, "business_rows_unchanged": True,
              "starter_failure_tasks": ["owner", "write"], "assist_roles": ["HINT", "DIAGNOSIS"],
              "live_model_calls": 0, "external_crm_actions": 0}
    with (OUT / "production-audit.json").open("xb") as stream:
        stream.write((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps(result))


if __name__ == "__main__":
    main()
