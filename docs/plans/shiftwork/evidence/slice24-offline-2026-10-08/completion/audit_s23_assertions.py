"""Compare refreshed S23 named assertions with their retained reviewed catches."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
HISTORY = ROOT / "docs/plans/shiftwork/evidence/slice23-application-2026-10-07/mutations-reviewed/results.json"


def main():
    prior = {row["name"]: row for row in json.loads(HISTORY.read_bytes())}
    current = json.loads((OUT / "faults23/results.json").read_bytes())
    assert len(prior) == len(current) == 106
    matched = []
    for row in current:
        first = row["message"].splitlines()[0]
        if row["name"] == "gtm_operation_rules_frozen":
            expected = "AssertionError: GTM frozen consequence rules omitted"
            assert row["node"] == "tests/orchestrator/test_gtm_guards.py::test_gtm_operation_freezes_declared_rules_before_execution"
        else:
            old = prior[row["name"]]
            expected = old["message"].splitlines()[0]
            assert row["node"] == old["node"]
        assert first == expected, "unexpected assertion site: " + row["name"]
        matched.append({"name": row["name"], "node": row["node"], "intended_assertion": expected})
    result = {"status": "PASS", "matched_controls": len(matched),
              "unchanged_reviewed_assertions": 105, "explicit_S24_transition_assertions": 1,
              "historical_receipt_sha256": hashlib.sha256(HISTORY.read_bytes()).hexdigest(), "rows": matched,
              "boundary": "Assertion sites verified; this is not exhaustive branch coverage."}
    path = OUT / "s23-assertion-audit.json"
    assert not path.exists()
    path.write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps({key: result[key] for key in ("status", "matched_controls", "unchanged_reviewed_assertions", "explicit_S24_transition_assertions")}))


if __name__ == "__main__":
    main()
