"""Apply the four already approved byte sequences, refusing any binding drift."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from shiftwork.domain import canonical


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    docs = ROOT / "docs/plans/shiftwork"
    raw_inventory = (docs / "slice23-gtm-review-inventory.json").read_bytes()
    inventory = json.loads(raw_inventory)
    auth = json.loads((docs / "evidence/slice23-approval-handoff-2026-10-07/authorization.json").read_bytes())
    entry = json.loads((OUT / "entry.json").read_bytes())
    signed = dict(inventory)
    digest = signed.pop("approval_digest")
    assert digest == auth["approval_digest"] == sha(canonical.canonical_bytes(signed))
    assert digest == "8d87c2dc279f31f3206ec389e0f72b34b50e038c59bc764ef60c13489b62d1fa"
    assert sha(raw_inventory) == auth["machine_inventory_sha256"]
    assert sha((docs / "slice23-gtm-operator-review-packet.md").read_bytes()) == auth["prepared_packet_sha256"]
    assert auth["application_authorized"] is True
    assert len(inventory["files"]) == len(inventory["reviewed_pins"]) == 19
    assert len(inventory["documents"]) == len(inventory["offline_fixture_pins"]) == 3
    for row in inventory["files"]:
        raw = (ROOT / "shiftwork" / row["path"]).read_bytes()
        assert (len(raw), sha(raw)) == (row["bytes"], row["sha256"]), row["path"]
    expected = {
        "shiftwork/fixtures/requests/gtm_compare_manifest.json",
        "shiftwork/sealed/cases/gtm_pipeline_ownership.json",
        "shiftwork/packs/registry.py", "shiftwork/config.py",
    }
    proposals = docs / "evidence/slice23-lf-repair-2026-10-07/proposed-application"
    assert {p.relative_to(proposals).as_posix() for p in proposals.rglob("*") if p.is_file()} == expected
    assert {row["path"] for row in auth["approved_production_replacements"]} == expected
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip() == entry["head"]
    assert sha(subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=ROOT)) == entry["index_entries_sha256"]
    replacements = []
    for row in auth["approved_production_replacements"]:
        target = ROOT / row["path"]
        before = target.read_bytes()
        after = (proposals / row["path"]).read_bytes()
        assert sha(before) == row["preimage_sha256"] == entry["files"][row["path"]]
        assert (len(after), sha(after)) == (row["proposed_bytes"], row["proposed_sha256"])
        if target.suffix == ".py":
            compile(after, row["path"], "exec")
        else:
            old, new = json.loads(before), json.loads(after)
            assert {k for k in old if old[k] != new[k]} == {"review_status", "sealed_payload_sha256"}
            assert old["review_status"] == "DRAFT" and old["sealed_payload_sha256"] is None
            assert new["review_status"] == "OPERATOR_SEALED"
        replacements.append((target, before, after, row))
    # Every preimage and proposal is validated before the first production write.
    applied = []
    try:
        for target, before, after, row in replacements:
            target.write_bytes(after)
            applied.append((target, before))
            assert target.read_bytes() == after
        for row in inventory["files"]:
            assert sha((ROOT / "shiftwork" / row["path"]).read_bytes()) == row["proposed_sha256"]
    except BaseException:
        for target, before in reversed(applied):
            target.write_bytes(before)
        raise
    result = {"status": "APPLIED_EXACT_APPROVED_BYTES", "approval_digest": digest,
              "production_replacements": [row for _, _, _, row in replacements],
              "material_pins_verified": 19, "acceptance": "PENDING_USER_DECISION",
              "index_unchanged": True, "live_calls": 0}
    with (OUT / "application.json").open("xb") as stream:
        stream.write((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps(result))


if __name__ == "__main__":
    main()
