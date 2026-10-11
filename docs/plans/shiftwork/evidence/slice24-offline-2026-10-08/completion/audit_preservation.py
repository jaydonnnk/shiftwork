"""Read-only S24 preservation audit; run from the repository root."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess

ROOT = Path.cwd()
OUT = ROOT / "docs/plans/shiftwork/evidence/slice24-offline-2026-10-08/completion"
ENTRY = json.loads((OUT.parent / "entry.json").read_bytes())
INCOMING = json.loads((OUT.parent / "continuation/entry.json").read_bytes())
ALLOWED = {"MISTAKES.md", "docs/SHIFTWORK_PLAN.md", "docs/plans/shiftwork/00-status.md",
    "shiftwork/comparison_flow.py", "shiftwork/domain/task_contract.py", "shiftwork/ledger/reducer.py",
    "shiftwork/orchestrator.py", "tests/orchestrator/test_gtm_guards.py",
    "tests/orchestrator/test_gtm_pipeline.py", "tests/packs/gtm_mutation_proofs.py"}
CONTINUATION_ALLOWED = {"MISTAKES.md", "docs/SHIFTWORK_PLAN.md", "docs/plans/shiftwork/00-status.md",
    "shiftwork/orchestrator.py", "tests/orchestrator/test_gtm_pipeline.py",
    "docs/plans/shiftwork/slice24-implementation-plan.md"}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def drift(bindings, allowed=()):
    return [name for name, expected in bindings.items() if name not in allowed and
        (not (ROOT / name).is_file() or digest((ROOT / name).read_bytes()) != expected)]


def command(argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    return {"argv": argv, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def retained_boundary(raw, expected, prefix):
    ends = [0]
    offset = 0
    for line in raw.splitlines(keepends=True):
        offset += len(line)
        ends.append(offset)
    for offset in ends:
        part = raw[:offset] if prefix else raw[offset:]
        if digest(part) == expected:
            return {"retained_bytes": len(part), "boundary": offset, "sha256": expected}
    raise AssertionError("historical byte boundary does not match its entry hash")


def main():
    historical_path = ROOT / "docs/plans/shiftwork/evidence/slice23-publication-2026-10-08/premerge-preservation.json"
    historical = json.loads(historical_path.read_bytes())["files"]
    protected = {p: h for p, h in historical.items() if p.startswith((
        "docs/plans/shiftwork/evidence/", "shiftwork/fixtures/", "shiftwork/sealed/cases/"))}
    source_lines = []
    for name in sorted(ALLOWED):
        if not name.endswith(".py"):
            continue
        blob = subprocess.check_output(["git", "show", "HEAD:" + name], cwd=ROOT)
        candidates = [blob, blob.replace(b"\r\n", b"\n"), blob.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")]
        original = next((raw for raw in candidates if digest(raw) == ENTRY["tracked_sha256"][name]), None)
        assert original is not None, "entry source reconstruction is unproved: " + name
        before = original.splitlines(keepends=True)
        after = (ROOT / name).read_bytes().splitlines(keepends=True)
        matcher = difflib.SequenceMatcher(a=[line.rstrip(b"\r\n") for line in before],
            b=[line.rstrip(b"\r\n") for line in after], autojunk=False)
        preserved = 0
        for tag, a, b, c, d in matcher.get_opcodes():
            if tag == "equal":
                assert before[a:b] == after[c:d], "unchanged source line bytes differ: " + name
                preserved += b - a
        source_lines.append({"path": name, "entry_sha256": digest(original), "unchanged_lines_exact": preserved})
    history = {name: retained_boundary((ROOT / name).read_bytes(), ENTRY["tracked_sha256"][name], prefix=name == "MISTAKES.md")
        for name in ("MISTAKES.md", "docs/SHIFTWORK_PLAN.md", "docs/plans/shiftwork/00-status.md")}
    tracked_drift = drift(ENTRY["tracked_sha256"], ALLOWED)
    incoming_drift = drift(INCOMING["files_sha256"], CONTINUATION_ALLOWED)
    historical_drift = drift(protected)
    branch = command(["git", "branch", "--show-current"])
    head = command(["git", "rev-parse", "HEAD"])
    staged = command(["git", "diff", "--cached", "--name-only"])
    whitespace = command(["git", "diff", "--check"])
    new_whitespace = [command(["git", "-c", "core.autocrlf=false", "diff", "--no-index", "--check", "--", "/dev/null", str(p.relative_to(ROOT))])
        for p in (ROOT / "demos/gtm_operation.py", ROOT / "tests/orchestrator/test_gtm_operation_guards.py",
                  ROOT / "tests/packs/gtm_operation_mutation_proofs.py", ROOT / "docs/plans/shiftwork/slice24-continuation-handoff-2026-10-08.md",
                  ROOT / "docs/plans/shiftwork/slice24-offline-checkpoint-2026-10-08.md",
                  ROOT / "docs/plans/shiftwork/slice24-architecture-review-2026-10-08.md") if p.is_file()]
    result = {"tracked_entry_files": len(ENTRY["tracked_sha256"]), "tracked_unchanged_exact": len(ENTRY["tracked_sha256"]) - len(ALLOWED),
        "allowed_tracked_changes": sorted(ALLOWED), "unexpected_tracked_drift": tracked_drift,
        "continuation_entry_files": len(INCOMING["files_sha256"]), "unexpected_incoming_drift": incoming_drift,
        "historical_protected_files": len(protected), "historical_protected_drift": historical_drift,
        "history_boundaries": history, "source_lines": source_lines,
        "branch": branch, "head": head, "staged": staged, "whitespace": whitespace, "new_whitespace": new_whitespace}
    result["status"] = "PASS" if not any((tracked_drift, incoming_drift, historical_drift, staged["stdout"],
        whitespace["returncode"], branch["stdout"].strip() != ENTRY["branch"], head["stdout"].strip() != ENTRY["head"])) and all(
        row["returncode"] in (0, 1) and not row["stdout"] and not row["stderr"] for row in new_whitespace) else "FAIL"
    (OUT / "preservation.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps({key: result[key] for key in ("status", "tracked_unchanged_exact", "unexpected_tracked_drift",
        "unexpected_incoming_drift", "historical_protected_files", "historical_protected_drift")}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
