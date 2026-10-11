"""Audit raw singleton assertion receipts against named controls and source hashes."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from tests.packs import gtm_mutation_proofs as s23
from tests.packs import gtm_operation_mutation_proofs as s24

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent


def audit(module, count, directory, intended):
    cases = {case["name"]: case for case in module.CASES}
    rows = json.loads((directory / "results.json").read_bytes())
    assert len(rows) == len(cases) == count and len({row["name"] for row in rows}) == count
    assert set(cases) == {row["name"] for row in rows}
    audited = []
    for row in rows:
        case = cases[row["name"]]
        log = directory / (row["name"] + ".log")
        xml = directory / (row["name"] + ".xml")
        assert hashlib.sha256(log.read_bytes()).hexdigest() == row["log_sha256"]
        assert hashlib.sha256(xml.read_bytes()).hexdigest() == row["xml_sha256"]
        assert hashlib.sha256((ROOT / case["file"]).read_bytes()).hexdigest() == row["source_sha256"]
        nodes = list(ET.parse(xml).getroot().iter("testcase"))
        assert len(nodes) == 1 and not list(ET.parse(xml).getroot().iter("error"))
        failures = nodes[0].findall("failure")
        assert len(failures) == 1 and nodes[0].get("name") == case["node"].split("::")[-1]
        message = failures[0].get("message", "")
        assert message == row["message"] and message.startswith(("assert", "AssertionError", "Failed:"))
        assert row["status"] == "FAIL_CAUGHT" and row["restored"] is True and row["errors"] == 0
        if intended:
            expected = s24.EXPECTED_ASSERTIONS.get(row["name"], ["Failed: DID NOT RAISE"])
            assert expected == row["expected_assertions"] and all(needle in message for needle in expected)
            assert row["assertion_matches"] is True
        audited.append({"name": row["name"], "node": case["node"], "file": case["file"],
                        "message": message, "source_sha256": row["source_sha256"],
                        "log_sha256": row["log_sha256"], "xml_sha256": row["xml_sha256"]})
    return {"status": "PASS", "controls": count, "setup_errors": 0,
            "named_assertion_matches": intended, "rows": audited}


def main():
    result = {"S24": audit(s24, 55, OUT / "faults24", True),
              "S23_refreshed": audit(s23, 106, OUT / "faults23", False)}
    path = OUT / "fault-audit.json"
    assert not path.exists()
    path.write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps({name: {key: row[key] for key in ("status", "controls", "setup_errors", "named_assertion_matches")}
                      for name, row in result.items()}))


if __name__ == "__main__":
    main()
