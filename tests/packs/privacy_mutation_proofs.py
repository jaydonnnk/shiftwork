"""Run isolated privacy-reader faults; never mutate the working source tree."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/plans/shiftwork/evidence/slice22a-privacy-2026-10-03/mutations-final"
TEST = "tests/packs/test_projection_inventory.py"
STORE = "shiftwork/sealed/store.py"
CASES = [
    ("case_id", STORE, 'text(case.get("id"))', '"masked"', "id"),
    ("check_id", STORE, 'text(case.get("check_id"))', '"masked"', "check_id"),
    ("note", STORE, "            needles.add(note)", "            pass", "expected.note"),
    ("request_id", STORE, 'text(request.get("request_id"))', '"masked"', "stimulus.request.request_id"),
    ("request_text", STORE, 'text(request.get("text"))', '"masked"', "stimulus.request.text"),
    ("spec_id", STORE, 'text(spec.get("id"))', '"masked"', "stimulus.task_spec.id"),
    ("spec_text", STORE, 'text(spec.get("text"))', '"masked"', "stimulus.task_spec.text"),
    ("delta_description", STORE, 'text(delta.get("description"))', '"masked"', "stimulus.state_delta.description"),
    ("typed_kind", STORE, "                needles.add(kind)", "                pass", "expected.aspect.kind"),
]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def run(package, name, argv, expected=None):
    env = dict(os.environ, PYTHONPATH=str(package), PYTHONDONTWRITEBYTECODE="1")
    xml = OUT / (name + ".xml")
    command = [sys.executable, "-m", "pytest", *argv, "-q", "--tb=short", "--junitxml=" + str(xml)]
    result = subprocess.run(command, cwd=package, env=env, capture_output=True, timeout=90)
    for stream, raw in (("stdout", result.stdout), ("stderr", result.stderr)):
        (OUT / (name + "." + stream + ".log")).write_bytes(raw)
    nodes = ET.parse(xml).getroot().findall(".//testcase")
    failed = [node for node in nodes if node.find("failure") is not None]
    errors = [node for node in nodes if node.find("error") is not None]
    row = {"name": name, "argv": command, "exit": result.returncode,
           "stdout_sha256": digest(result.stdout), "stderr_sha256": digest(result.stderr),
           "failed_tests": [node.attrib["name"] for node in failed], "errors": len(errors)}
    if expected:
        failures = [node for node in failed if node.attrib["name"] == expected]
        row["intended_failure"] = (result.returncode == 1 and len(failures) == 1 and not errors
                                  and "Failed: DID NOT RAISE LifecycleError" in failures[0].find("failure").text)
    else:
        row["baseline_passed"] = result.returncode == 0 and not failed and not errors
    (OUT / (name + ".json")).write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(row))
    return row


if __name__ == "__main__":
    assert not OUT.exists(), "do not overwrite earlier mutation evidence"
    OUT.mkdir()
    sources = {name: (ROOT / name).read_bytes() for name in (STORE, "shiftwork/orchestrator.py")}
    rows = []
    with tempfile.TemporaryDirectory(prefix="s22a-private-faults-") as directory:
        package = Path(directory)
        for name in ("shiftwork", "tests"):
            shutil.copytree(ROOT / name, package / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        rows.append(run(package, "baseline", [TEST]))
        assert rows[-1]["baseline_passed"]
        for name, file, old, new, field in CASES:
            target = package / file
            raw = target.read_bytes()
            # Preserve CRLF source bytes in every disposable patch.
            anchor = old.encode()
            assert raw.count(anchor) == 1, name
            target.write_bytes(raw.replace(anchor, new.encode(), 1))
            try:
                expected = "test_each_draft_private_field_is_blocked_as_serialized[" + field + "]"
                row = run(package, name, [TEST + "::" + expected], expected)
                rows.append(row)
            finally:
                target.write_bytes(raw)
            assert target.read_bytes() == raw, name
            row["source_restored"] = True
            assert row["intended_failure"], name
    assert all((ROOT / name).read_bytes() == raw for name, raw in sources.items())
    (OUT / "summary.json").write_text(json.dumps({"rows": rows, "working_sources_unchanged": True}, indent=2) + "\n", encoding="utf-8")
