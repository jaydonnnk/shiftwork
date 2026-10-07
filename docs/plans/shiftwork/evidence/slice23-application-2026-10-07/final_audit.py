"""Read-only closeout verification; writes one new final receipt, never Git state."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from demos.gtm_reviewed import reviewed_inventory


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    receipt = OUT / "final-preservation.json"
    assert not receipt.exists(), "retain prior receipts instead of overwriting"
    entry = json.loads((OUT / "entry.json").read_bytes())
    inventory = reviewed_inventory()
    application = json.loads((OUT / "application.json").read_bytes())
    for row in application["production_replacements"]:
        assert sha(ROOT / row["path"]) == row["proposed_sha256"]
        assert sha(OUT / "preimages" / row["path"]) == row["preimage_sha256"]
    for path in entry["historical_evidence_paths"]:
        assert sha(ROOT / path) == entry["files"][path], path
    older = json.loads((ROOT / "docs/plans/shiftwork/evidence/slice23-preflight-2026-10-07/entry.json").read_bytes())
    for path, expected in older["prior_evidence"].items():
        assert sha(ROOT / path) == expected, path
    for path, expected in entry["prior_reviewed_pins"].items():
        assert sha(ROOT / "shiftwork" / path) == expected, path
    sources = json.loads((OUT / "proof-source-bindings.json").read_bytes())
    for path, expected in sources.items():
        assert sha(ROOT / path) == expected, path
    allowed = {".gitattributes", "MISTAKES.md", "docs/SHIFTWORK_PLAN.md", "docs/plans/shiftwork/00-status.md",
               "docs/plans/shiftwork/slice23-application-plan-2026-10-07.md",
               "tests/api/test_pivot_routes.py", "tests/api/test_workplace_boards.py", "tests/assist/test_gateway.py",
               "tests/executor/test_conformance.py", "tests/orchestrator/test_fde_deployment.py",
               "tests/orchestrator/test_gtm_pipeline.py", "tests/packs/gtm_material.py",
               "tests/packs/gtm_mutation_proofs.py", "tests/packs/test_northline_review.py",
               "tests/packs/test_registry.py", "tests/store/test_pivot_migration.py"}
    allowed.update(row["path"] for row in application["production_replacements"])
    observed = json.loads((OUT / "unowned-agents-diff-confirmed.json").read_bytes())
    assert sha(ROOT / "AGENTS.md") == observed["current_sha256"]
    assert entry["files"]["AGENTS.md"] == observed["entry_sha256"]
    changed = []
    for path, expected in entry["files"].items():
        if sha(ROOT / path) != expected:
            assert path in allowed or path == "AGENTS.md", path
            changed.append(path)
    for path in (".gitattributes", "MISTAKES.md"):
        assert (ROOT / path).read_bytes().startswith((OUT / "preimages" / path).read_bytes()), path
    for path in ("docs/SHIFTWORK_PLAN.md", "docs/plans/shiftwork/00-status.md"):
        assert (ROOT / path).read_bytes().endswith((OUT / "preimages" / path).read_bytes()), path
    assert sha(ROOT / ".gitignore") == entry["incoming_gitignore_sha256"]
    assert git("rev-parse", "HEAD").decode().strip() == entry["head"]
    assert git("branch", "--show-current").decode().strip() == entry["branch"]
    assert hashlib.sha256(git("ls-files", "--stage", "-z")).hexdigest() == entry["index_entries_sha256"]
    for name in ("sentinel-repair", "admission-verified", "production-retained", "full-offline-verified"):
        result = json.loads((OUT / (name + "-result.json")).read_bytes())
        assert result["exit_code"] == result["failures"] == result["errors"] == 0, name
        assert sha(OUT / (name + ".log")) == result["log_sha256"]
        assert sha(OUT / (name + ".xml")) == result["xml_sha256"]
    full = json.loads((OUT / "full-offline-verified-result.json").read_bytes())
    assert full["tests"] == 1282 and full["skipped"] == 1
    faults = json.loads((OUT / "mutations-reviewed/results.json").read_bytes())
    assert len(faults) == len({row["name"] for row in faults}) == 106
    for row in faults:
        assert row["status"] == "FAIL_CAUGHT" and row["restored"]
        assert row["failures"] == 1 and row["errors"] == 0
        base = OUT / "mutations-reviewed" / row["name"]
        assert sha(base.with_suffix(".log")) == row["log_sha256"]
        assert sha(base.with_suffix(".xml")) == row["xml_sha256"]
        cases = list(ET.parse(base.with_suffix(".xml")).getroot().iter("testcase"))
        assert len(cases) == 1 and len(cases[0].findall("failure")) == 1 and not cases[0].findall("error")
    production = json.loads((OUT / "production-audit.json").read_bytes())
    assert production["status"] == "PASS" and production["business_rows_unchanged"]
    assert sha(OUT / "production-retained.db") == production["database_sha256"]
    manifest_path = ROOT / "docs/plans/shiftwork/slice23-publication-inventory-2026-10-07.json"
    publication = json.loads(manifest_path.read_bytes())
    paths = {row["path"] for row in publication["files"]}
    assert len(paths) == len(publication["files"])
    assert ".gitignore" not in paths and "AGENTS.md" not in paths
    assert {"shiftwork/" + row["path"] for row in inventory["files"]} <= paths
    assert len(publication["hidden_required_requests"]) == 8
    filtered = 0
    filtered_paths = []
    encoded_paths = ("\0".join(sorted(paths)) + "\0").encode()
    ignored_result = subprocess.run(["git", "check-ignore", "--stdin", "-z", "--no-index"], cwd=ROOT,
                                    input=encoded_paths, capture_output=True)
    assert ignored_result.returncode in {0, 1}
    ignored_paths = {p for p in ignored_result.stdout.decode().split("\0") if p}
    for row in publication["files"]:
        path = row["path"]
        assert sha(ROOT / path) == row["sha256"] and (ROOT / path).stat().st_size == row["bytes"], path
        ignored = path in ignored_paths
        assert ignored == row["explicit_force_inclusion_required"], path
        if row["group"] in {"approved-material", "verification-receipts"} or path in {"shiftwork/config.py", "shiftwork/packs/registry.py"} or path.endswith(("slice23-gtm-review-inventory.json", "slice23-gtm-operator-review-packet.md")):
            filtered_paths.append(path)
            filtered += 1
    attr_input = ("\0".join(filtered_paths) + "\0").encode()
    attrs = subprocess.check_output(["git", "check-attr", "--stdin", "-z", "text"], cwd=ROOT, input=attr_input).decode().split("\0")
    assert len(attrs) == filtered * 3 + 1
    assert all(attrs[i + 2] == "unset" for i in range(0, len(attrs) - 1, 3))
    hash_input = ("\n".join(filtered_paths) + "\n").encode()
    raw_hashes = subprocess.check_output(["git", "hash-object", "--no-filters", "--stdin-paths"], cwd=ROOT, input=hash_input).splitlines()
    clean_hashes = subprocess.check_output(["git", "hash-object", "--stdin-paths"], cwd=ROOT, input=hash_input).splitlines()
    assert len(raw_hashes) == filtered and raw_hashes == clean_hashes
    diff_check = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
    assert diff_check.returncode == 0, diff_check.stdout + diff_check.stderr
    final = {"status": "PASS_WITH_DISCLOSED_UNOWNED_AGENTS_CHANGE", "approval_digest": inventory["approval_digest"],
             "production_replacements_exact": 4, "approved_material_files": 19,
             "historical_evidence_files_preserved": len(entry["historical_evidence_paths"]),
             "pre_s23_evidence_files_preserved": len(older["prior_evidence"]),
             "prior_reviewed_files_preserved": len(entry["prior_reviewed_pins"]),
             "source_bindings_verified": len(sources), "allowed_changed_entry_files": changed,
             "unowned_change_observation": observed, "gitignore_preserved_and_excluded": True,
             "index_head_branch_unchanged": True, "git_diff_check": "PASS",
             "full_offline": full, "faults_rerun": 106, "production_audit": production,
             "publication_files": len(paths), "byte_preserving_clean_filters_verified": filtered,
             "publication_manifest_sha256": sha(manifest_path), "acceptance": "PENDING_USER_DECISION",
             "publication_authorized": False, "fresh_checkout_reproduction": "NOT_RUN"}
    with receipt.open("xb") as stream:
        stream.write((json.dumps(final, indent=2) + "\n").encode())
    print(json.dumps({key: final[key] for key in ("status", "publication_files", "source_bindings_verified", "index_head_branch_unchanged")}))


if __name__ == "__main__":
    main()
