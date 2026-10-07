"""Enumerate reviewable S23 publication paths without touching the Git index."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
MANIFEST = "docs/plans/shiftwork/slice23-publication-inventory-2026-10-07.json"


def git_paths(*args):
    return {p for p in subprocess.check_output(["git", *args, "-z"], cwd=ROOT).decode().split("\0") if p}


def main():
    expected_tracked = {
        ".gitattributes", "MISTAKES.md", "docs/SHIFTWORK_PLAN.md", "docs/plans/shiftwork/00-status.md",
        "shiftwork/api/schemas.py", "shiftwork/comparison_flow.py", "shiftwork/config.py",
        "shiftwork/domain/customer_answer.py", "shiftwork/domain/models.py", "shiftwork/domain/task_contract.py",
        "shiftwork/evaluator/evaluator.py", "shiftwork/experiments.py", "shiftwork/orchestrator.py",
        "shiftwork/packs/registry.py", "shiftwork/sealed/store.py", "tests/api/test_pivot_routes.py",
        "tests/api/test_workplace_boards.py", "tests/assist/test_gateway.py", "tests/executor/test_conformance.py",
        "tests/orchestrator/test_fde_deployment.py", "tests/packs/test_northline_review.py",
        "tests/packs/test_registry.py", "tests/store/test_pivot_migration.py",
    }
    tracked = git_paths("diff", "--name-only", "HEAD")
    assert tracked - {".gitignore", "AGENTS.md"} == expected_tracked, ("unexpected tracked scope", tracked)
    inventory = json.loads((ROOT / "docs/plans/shiftwork/slice23-gtm-review-inventory.json").read_bytes())
    material = {"shiftwork/" + row["path"] for row in inventory["files"]}
    visible = git_paths("ls-files", "--others", "--exclude-standard")
    candidates = set(expected_tracked) | material
    for path in visible:
        if path == MANIFEST:
            continue
        assert (path in material or path in {"demos/gtm_review.py", "demos/gtm_reviewed.py",
                "tests/orchestrator/test_gtm_pipeline.py", "tests/orchestrator/test_gtm_guards.py",
                "tests/packs/gtm_material.py", "tests/packs/gtm_mutation_proofs.py"}
                or path.startswith("docs/plans/shiftwork/slice23-")), ("unclassified untracked path", path)
        candidates.add(path)
    selected_receipts = [p for p in OUT.rglob("*") if p.is_file() and "preimages" not in p.relative_to(OUT).parts
                         and "__pycache__" not in p.parts
                         and p.name not in {"northline-test-pre-fix.py", "final-preservation.json"}]
    for folder in ("slice23-lf-repair-2026-10-07", "slice23-approval-handoff-2026-10-07",
                   "slice23-preflight-2026-10-07"):
        prior = ROOT / "docs/plans/shiftwork/evidence" / folder
        selected_receipts += [p for p in prior.rglob("*") if p.is_file()
                              and "preimages" not in p.relative_to(prior).parts
                              and "__pycache__" not in p.parts and not p.name.endswith("-prefix.bin")]
    candidates.update(p.relative_to(ROOT).as_posix() for p in selected_receipts)
    candidates.discard(MANIFEST)
    rows = []
    ignore_input = ("\0".join(sorted(candidates)) + "\0").encode()
    ignore_result = subprocess.run(["git", "check-ignore", "--stdin", "-z", "--no-index"], cwd=ROOT,
                                   input=ignore_input, capture_output=True)
    assert ignore_result.returncode in {0, 1}
    ignored_paths = {p for p in ignore_result.stdout.decode().split("\0") if p}
    for path in sorted(candidates):
        raw = (ROOT / path).read_bytes()
        ignored = path in ignored_paths
        group = ("approved-material" if path in material else
                 "verification-receipts" if path.startswith("docs/plans/shiftwork/evidence/") else
                 "acceptance-documents" if path.startswith("docs/") else
                 "admission-tests" if path.startswith("tests/") else "implementation-and-byte-policy")
        rows.append({"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                     "group": group, "explicit_force_inclusion_required": ignored})
    hidden_requests = [row["path"] for row in rows if row["path"] in material
                       and row["path"].startswith("shiftwork/fixtures/requests/") and row["explicit_force_inclusion_required"]]
    assert len(hidden_requests) == 8
    assert ".gitignore" not in candidates
    entry = json.loads((OUT / "entry.json").read_bytes())
    assert hashlib.sha256((ROOT / ".gitignore").read_bytes()).hexdigest() == entry["incoming_gitignore_sha256"]
    assert hashlib.sha256(subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=ROOT)).hexdigest() == entry["index_entries_sha256"]
    result = {"schema_version": 1, "status": "REVIEWABLE_PUBLICATION_INVENTORY_ONLY",
              "head": entry["head"], "branch": entry["branch"], "files": rows,
              "also_include_manifest": MANIFEST,
              "also_include_final_preservation_receipt": "docs/plans/shiftwork/evidence/slice23-application-2026-10-07/final-preservation.json",
              "manifest_hash_location": "final-preservation.json records this manifest hash without self-reference",
              "required_material_files": 19, "hidden_required_requests": hidden_requests,
              "excluded_incoming_change": {"path": ".gitignore", "sha256": entry["incoming_gitignore_sha256"],
                  "reason": "unverified ownership; preserved exact; never stage as part of S23"},
              "excluded_external_change": {"path": "AGENTS.md", "sha256": hashlib.sha256((ROOT / "AGENTS.md").read_bytes()).hexdigest(),
                  "reason": "context threshold changed outside this agent edits; ownership unverified; preserved and excluded"},
              "retained_local_only": ["entry preimages", "northline-test-pre-fix.py", "older unselected raw history"],
              "commit_grouping": "separate implementation, approved material/bindings, admission tests, evidence and closeout documents",
              "index_modified": False, "publication_authorized": False, "acceptance": "PENDING_USER_DECISION"}
    (ROOT / MANIFEST).write_bytes((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps({"publication_files": len(rows), "manifest_also_required": True,
                      "ignored_required_requests": len(hidden_requests), "unowned_gitignore_excluded": True,
                      "index_modified": False}))


if __name__ == "__main__":
    main()
