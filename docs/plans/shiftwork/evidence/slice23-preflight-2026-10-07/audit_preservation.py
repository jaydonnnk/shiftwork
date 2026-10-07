"""Read-only raw receipt, byte preservation and final scope audit."""
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
ALLOWED = {".gitattributes", "MISTAKES.md", "docs/SHIFTWORK_PLAN.md", "docs/plans/shiftwork/00-status.md",
    "shiftwork/api/schemas.py", "shiftwork/comparison_flow.py", "shiftwork/config.py",
    "shiftwork/domain/customer_answer.py", "shiftwork/domain/models.py", "shiftwork/domain/task_contract.py",
    "shiftwork/evaluator/evaluator.py", "shiftwork/experiments.py", "shiftwork/orchestrator.py", "shiftwork/sealed/store.py"}


def digest(raw): return hashlib.sha256(raw).hexdigest()


def main():
    entry = json.loads((OUT / "entry.json").read_bytes())
    spec = importlib.util.spec_from_file_location("gtm_mutations", ROOT / "tests/packs/gtm_mutation_proofs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    latest = {}
    rejected = []
    for folder in ("mutations-first", "mutations-repaired", "mutations-final"):
        for row in json.loads((OUT / folder / "results.json").read_bytes()):
            if row["status"] != "FAIL_CAUGHT": rejected.append({"folder": folder, **row})
            latest[row["name"]] = (folder, row)
    assert set(latest) == {case["name"] for case in module.CASES}
    controls = []
    for case in module.CASES:
        folder, row = latest[case["name"]]
        assert row["status"] == "FAIL_CAUGHT" and row["restored"] and row["errors"] == 0 and row["failures"] == 1
        assert digest((ROOT / case["file"]).read_bytes()) == row["source_sha256"]
        for kind in ("log", "xml"):
            raw = (OUT / folder / (case["name"] + "." + kind)).read_bytes()
            assert digest(raw) == row[kind + "_sha256"]
        nodes = list(ET.parse(OUT / folder / (case["name"] + ".xml")).getroot().iter("testcase"))
        assert len(nodes) == 1 and nodes[0].get("name") == case["node"].split("::", 1)[1]
        controls.append({"name": case["name"], "source": case["file"], "folder": folder, **row})
    historical = {path: digest((ROOT / path).read_bytes()) for path in entry["prior_evidence"]}
    assert historical == entry["prior_evidence"]
    reviewed = {path: digest((ROOT / "shiftwork" / path).read_bytes()) for path in entry["reviewed_pins"]}
    assert reviewed == entry["reviewed_pins"]
    changes = subprocess.check_output(["git", "diff", "--name-only"], cwd=ROOT, text=True).splitlines()
    assert set(changes).issubset(ALLOWED), changes
    unchanged = {path: digest((ROOT / path).read_bytes()) for path in entry["tracked"] if path not in changes}
    assert all(value == entry["tracked"][path] for path, value in unchanged.items())
    newline_rows = []
    for path in changes:
        current = (ROOT / path).read_bytes()
        if path.startswith("shiftwork/"):
            blob = subprocess.check_output(["git", "show", "HEAD:" + path], cwd=ROOT)
            old = next(raw for raw in (blob, blob.replace(b"\n", b"\r\n")) if digest(raw) == entry["tracked"][path])
            # Matching content lines must retain their original line terminator.
            before, after = old.splitlines(keepends=True), current.splitlines(keepends=True)
            matcher = difflib.SequenceMatcher(a=[row.rstrip(b"\r\n") for row in before], b=[row.rstrip(b"\r\n") for row in after], autojunk=False)
            preserved = 0
            for block in matcher.get_matching_blocks():
                assert before[block.a:block.a+block.size] == after[block.b:block.b+block.size]
                preserved += block.size
            newline_rows.append({"path": path, "unchanged_lines_byte_exact": preserved,
                "entry_crlf": old.count(b"\r\n"), "entry_lf": old.count(b"\n") - old.count(b"\r\n"),
                "current_crlf": current.count(b"\r\n"), "current_lf": current.count(b"\n") - current.count(b"\r\n")})
        elif path == "MISTAKES.md":
            prefix = (OUT / "mistakes-prefix.bin").read_bytes()
            assert digest(prefix) == entry["tracked"][path] and current.startswith(prefix)
        elif path == ".gitattributes":
            prefix = current[:current.index(b"\r\n# Preserve the exact proposed S23 GTM")]
            assert digest(prefix) == entry["tracked"][path]
        else:
            prefix = (OUT / (Path(path).stem + "-prefix.bin")).read_bytes()
            assert digest(prefix) == entry["tracked"][path] and current.endswith(prefix)
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == entry["head"]
    assert subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip() == "shiftwork/slice-23"
    assert not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True).strip()
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    needles = re.compile(rb"sk-[A-Za-z0-9]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
    assert not any(needles.search((ROOT / path).read_bytes()) for path in (*changes, *untracked))
    result = {"status": "PASS", "guard_controls": len(controls), "rejected_controls_retained": len(rejected),
        "historical_evidence_byte_exact": len(historical), "existing_reviewed_pins_byte_exact": len(reviewed),
        "unchanged_tracked_files_byte_exact": len(unchanged), "tracked_changes": changes, "untracked": untracked,
        "newline_preservation": newline_rows, "index_unchanged": True, "head_unchanged": True,
        "production_gtm_application": False, "controls": controls, "rejected_controls": rejected}
    (OUT / "final-preservation.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps({key: value for key, value in result.items() if not isinstance(value, list)}))


if __name__ == "__main__": main()
