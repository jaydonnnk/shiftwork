"""Bounded read-only architecture and source-reference inventory for S24."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent


def imports(raw):
    tree = ast.parse(raw)
    return sorted({node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} |
                  {name.name for node in ast.walk(tree) if isinstance(node, ast.Import) for name in node.names})


def main():
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")[:-1]
    new = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")[:-1]
    parsed = []
    for path in sorted((ROOT / "shiftwork").rglob("*.py")):
        relative = path.relative_to(ROOT).as_posix()
        current = path.read_bytes()
        baseline = subprocess.check_output(["git", "show", "HEAD:" + relative], cwd=ROOT)
        before, after = imports(baseline), imports(current)
        parsed.append({"path": relative, "sha256": hashlib.sha256(current).hexdigest(),
                       "added_import_modules": sorted(set(after) - set(before)),
                       "removed_import_modules": sorted(set(before) - set(after))})
    needles = ("apply_pipeline_history", "_reduce_pipeline_operation", "pipeline_outputs",
               "operation-ledger-v3", "gtm_operation", "gtm_operation_mutation_proofs")
    references = {needle: [] for needle in needles}
    for name in tracked + new:
        if not name.endswith((".py", ".md", ".toml", ".html", ".mjs", ".json")):
            continue
        text = (ROOT / name).read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), 1):
            for needle in needles:
                if needle in line:
                    references[needle].append({"path": name, "line": number})
    result = {"tracked_inventory": tracked, "untracked_inventory": new,
              "production_modules": parsed, "symbol_references": references,
              "deletions_proposed": [], "scope": "S24 changes plus existing production import inventory"}
    destination = OUT / "architecture-inventory.json"
    assert not destination.exists()
    destination.write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps({"parsed_production_modules": len(parsed), "tracked_files": len(tracked),
                      "untracked_files": len(new), "import_changes": [row for row in parsed
                       if row["added_import_modules"] or row["removed_import_modules"]],
                      "reference_counts": {key: len(value) for key, value in references.items()}}))


if __name__ == "__main__":
    main()
