"""Audit S23 continuation preservation while exposing the incoming ignore exception."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
OLD = OUT.parent / "slice23-preflight-2026-10-07"
DOCS = {
    "MISTAKES.md",
    "docs/SHIFTWORK_PLAN.md", "docs/plans/shiftwork/00-status.md",
    "docs/plans/shiftwork/slice23-gtm-review-inventory.json",
    "docs/plans/shiftwork/slice23-gtm-operator-review-packet.md",
    "docs/plans/shiftwork/slice23-offline-checkpoint-2026-10-07.md",
    "docs/plans/shiftwork/slice23-handoff-2026-10-07.md",
    "docs/plans/shiftwork/slice23-architecture-review-2026-10-07.md",
}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def main(receipt_name):
    incoming = json.loads((OUT / "incoming.json").read_bytes())
    entry = json.loads((OLD / "entry.json").read_bytes())
    repair = json.loads((OUT / "lf-repair.json").read_bytes())
    repaired = {row["path"]: row for row in repair["files"]}
    historical = {path: sha((ROOT / path).read_bytes()) for path in entry["prior_evidence"]}
    assert historical == entry["prior_evidence"], "pre-S23 evidence changed"
    reviewed = {path: sha((ROOT / "shiftwork" / path).read_bytes()) for path in entry["reviewed_pins"]}
    assert reviewed == entry["reviewed_pins"], "existing reviewed bytes changed"
    observed_changes = []
    for path, expected in incoming["files"].items():
        raw = (ROOT / path).read_bytes()
        if sha(raw) != expected:
            observed_changes.append(path)
            assert path in DOCS or path in repaired, ("unexpected continuation change", path)
            if path in repaired:
                assert sha(raw) == repaired[path]["repaired_sha256"]
                original = (OUT / "preimages" / path).read_bytes()
                assert sha(original) == expected and original.replace(b"\r\n", b"\n") == raw
            elif path == "MISTAKES.md":
                original = (OUT / "preimages" / path).read_bytes()
                assert sha(original) == expected and raw.startswith(original)
            elif path in {"docs/SHIFTWORK_PLAN.md", "docs/plans/shiftwork/00-status.md",
                          "docs/plans/shiftwork/slice23-offline-checkpoint-2026-10-07.md",
                          "docs/plans/shiftwork/slice23-handoff-2026-10-07.md",
                          "docs/plans/shiftwork/slice23-architecture-review-2026-10-07.md"}:
                original_path = OUT / "preimages" / path
                # All three historical checkpoints are untracked; captured document
                # preimages are retained explicitly before current notices are prepended.
                assert original_path.is_file() and sha(original_path.read_bytes()) == expected
                assert raw.endswith(original_path.read_bytes()), "historical document suffix changed"
    assert set(repaired).issubset(observed_changes)
    for path in incoming["historical_evidence_paths"]:
        assert sha((ROOT / path).read_bytes()) == incoming["files"][path], path
    assert sha((ROOT / ".gitignore").read_bytes()) == incoming["gitignore_sha256"]
    spec = importlib.util.spec_from_file_location("s23_retained_controls", ROOT / "tests/packs/gtm_mutation_proofs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    latest, rejected = {}, []
    for folder in ("mutations-first", "mutations-repaired", "mutations-final"):
        for row in json.loads((OLD / folder / "results.json").read_bytes()):
            latest[row["name"]] = (folder, row)
            if row["status"] != "FAIL_CAUGHT":
                rejected.append({"folder": folder, "name": row["name"]})
    assert len({c["name"] for c in module.CASES}) == len(module.CASES)
    assert set(latest) == {c["name"] for c in module.CASES}
    controls = []
    for case in module.CASES:
        folder, row = latest[case["name"]]
        assert row["status"] == "FAIL_CAUGHT" and row["restored"]
        assert row["errors"] == 0 and row["failures"] == 1
        assert sha((ROOT / case["file"]).read_bytes()) == row["source_sha256"]
        module.anchor((ROOT / case["file"]).read_bytes(), case)
        for kind in ("log", "xml"):
            assert sha((OLD / folder / (case["name"] + "." + kind)).read_bytes()) == row[kind + "_sha256"]
        nodes = list(ET.parse(OLD / folder / (case["name"] + ".xml")).getroot().iter("testcase"))
        assert len(nodes) == 1 and nodes[0].get("name") == case["node"].split("::", 1)[1]
        failures = nodes[0].findall("failure")
        assert len(failures) == 1 and not nodes[0].findall("error")
        assert failures[0].get("message", "") == row["message"]
        controls.append({"name": case["name"], "folder": folder, "source_sha256": row["source_sha256"]})
    assert len(controls) == 106 and len(rejected) == 5
    current_changes = subprocess.check_output(["git", "diff", "--name-only"], cwd=ROOT, text=True).splitlines()
    assert set(current_changes) == set(incoming["tracked_changes"])
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == incoming["head"]
    assert subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip() == incoming["branch"]
    assert sha(subprocess.check_output(["git", "ls-files", "--stage"], cwd=ROOT)) == incoming["index_entries_sha256"]
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    material = incoming["material"]
    needle = re.compile(rb"sk-[A-Za-z0-9]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
    assert not any(needle.search((ROOT / p).read_bytes()) for p in set(current_changes + untracked + material))
    hidden = subprocess.run(["git", "check-ignore", "--no-index", "--",
            *(p for p in material if "/requests/" in p)], cwd=ROOT, capture_output=True, text=True)
    assert hidden.returncode == 0 and len(hidden.stdout.splitlines()) == 8
    machine = json.loads((ROOT / "docs/plans/shiftwork/slice23-gtm-review-inventory.json").read_bytes())
    assert machine == json.loads((OUT / "review-inventory.json").read_bytes())
    packet = (ROOT / "docs/plans/shiftwork/slice23-gtm-operator-review-packet.md").read_text()
    assert machine["approval_digest"] in packet
    for row in machine["application_sources"]:
        assert sha((ROOT / row["path"]).read_bytes()) == row["preimage_sha256"]
        assert sha((OUT / "proposed-application" / row["path"]).read_bytes()) == row["proposed_sha256"]
        assert row["preimage_sha256"] in packet and row["proposed_sha256"] in packet
    for row in machine["files"]:
        assert sha((ROOT / "shiftwork" / row["path"]).read_bytes()) == row["sha256"]
        assert row["sha256"] in packet and row["proposed_sha256"] in packet
        if row["sha256"] != row["proposed_sha256"]:
            assert sha((OUT / "proposed-application/shiftwork" / row["path"]).read_bytes()) == row["proposed_sha256"]
    from shiftwork import config
    from shiftwork.packs import registry
    assert registry.resolve_pack("gtm").reviewed_pins == ()
    assert not any(k.startswith("gtm_") for k in config.TRUSTED_LOCAL_FIXTURES)
    for path in ("fixtures/requests/gtm_compare_manifest.json", "sealed/cases/gtm_pipeline_ownership.json"):
        draft = json.loads((ROOT / "shiftwork" / path).read_bytes())
        assert draft["review_status"] == "DRAFT" and draft["sealed_payload_sha256"] is None
    if receipt_name == "continuation-preservation.json":
        new_docs = {"docs/plans/shiftwork/slice23-lf-repair-checkpoint-2026-10-07.md",
                    "docs/plans/shiftwork/slice23-lf-repair-architecture-preflight-2026-10-07.md"}
        assert set(untracked) - set(incoming["untracked"]) == new_docs
        assert "READY FOR OPERATOR MATERIAL REVIEW" in packet and "FULL REGRESSION PENDING" not in packet
        closeout = json.loads((OUT / "closeout.json").read_bytes())
        assert closeout["full_suite_exit_code"] == 0 and closeout["approval_digest"] == machine["approval_digest"]
    else:
        new_docs = set()
    result = {"status": "PASS_WITH_PREEXISTING_EXCEPTION", "continuation_changes": observed_changes,
        "pre_s23_evidence_byte_exact": len(historical), "incoming_evidence_byte_exact": len(incoming["historical_evidence_paths"]),
        "existing_reviewed_material_byte_exact": len(reviewed), "retained_guard_controls_verified": len(controls),
        "guard_controls_rerun": False, "rejected_controls_retained": rejected,
        "exception": {"path": ".gitignore", "ownership": "unverified", "preserved_sha256": incoming["gitignore_sha256"],
                      "hidden_request_drafts_explicitly_inventoried": hidden.stdout.splitlines(),
                      "original_final_state_hold_resolved": False},
        "source_unchanged_since_handoff": True, "head_and_index_unchanged": True,
        "production_gtm_pins_or_seals_applied": False,
        "current_document_sha256": {path: sha((ROOT / path).read_bytes()) for path in sorted(DOCS | new_docs)},
        "controls": controls}
    assert receipt_name in {"pre-document-preservation.json", "continuation-preservation.json"}
    with (OUT / receipt_name).open("xb") as stream:
        stream.write((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps({k: v for k, v in result.items() if k != "controls"}))

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", choices=("pre-document-preservation.json", "continuation-preservation.json"),
                        default="continuation-preservation.json")
    main(parser.parse_args().receipt)
