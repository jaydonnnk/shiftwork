"""Record the user's exact application approval; no production application."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PROPOSALS = OUT.parent / "slice23-lf-repair-2026-10-07/proposed-application"
sys.path.insert(0, str(ROOT))
from shiftwork.domain import canonical

APPROVED = "8d87c2dc279f31f3206ec389e0f72b34b50e038c59bc764ef60c13489b62d1fa"
STATEMENT = "I approve the application but put the approval in the copy paste handoff prompt"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write_new(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)

def main():
    assert not (OUT / "authorization.json").exists()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    assert head == "3e02f1e5176cd34d6dc355bbc4529234fa51fe62" and branch == "shiftwork/slice-23"
    index = subprocess.check_output(["git", "ls-files", "--stage"], cwd=ROOT)
    inventory_raw = (ROOT / "docs/plans/shiftwork/slice23-gtm-review-inventory.json").read_bytes()
    inventory = json.loads(inventory_raw)
    signed = dict(inventory)
    assert signed.pop("approval_digest") == APPROVED
    assert sha(canonical.canonical_bytes(signed)) == APPROVED
    assert inventory["production_reviewed"] is False and inventory["production_sealed"] is False
    files = {}
    for row in inventory["files"]:
        path = "shiftwork/" + row["path"]
        assert sha((ROOT / path).read_bytes()) == row["sha256"]
        files[path] = row["sha256"]
    application = list(inventory["application_sources"])
    for row in inventory["files"]:
        if row["sha256"] != row["proposed_sha256"]:
            application.append({"path": "shiftwork/" + row["path"], "preimage_sha256": row["sha256"],
                                "proposed_sha256": row["proposed_sha256"], "proposed_bytes": row["proposed_bytes"]})
    assert {row["path"] for row in application} == {
        "shiftwork/config.py", "shiftwork/packs/registry.py",
        "shiftwork/fixtures/requests/gtm_compare_manifest.json", "shiftwork/sealed/cases/gtm_pipeline_ownership.json"}
    for row in application:
        assert sha((ROOT / row["path"]).read_bytes()) == row["preimage_sha256"]
        proposal = (PROPOSALS / row["path"]).read_bytes()
        assert sha(proposal) == row["proposed_sha256"] and len(proposal) == row["proposed_bytes"]
        files[row["path"]] = row["preimage_sha256"]
    packet_raw = (ROOT / "docs/plans/shiftwork/slice23-gtm-operator-review-packet.md").read_bytes()
    assert sha(packet_raw) == "e5510402a78e260af8d5784c47d71d3fe4411f97444318df51522e9ac5a1b3ab"
    receipt = {"schema_version": 1, "date": "2026-10-07", "timezone": "Asia/Singapore",
        "authorization_source": "direct user message in this chat", "user_statement": STATEMENT,
        "authorization_context": "reply to request to approve the refreshed S23 application packet",
        "approval_digest": APPROVED, "machine_inventory_sha256": sha(inventory_raw),
        "prepared_packet_sha256": sha(packet_raw), "head": head, "branch": branch,
        "approved_material_files": 19, "approved_seals": 2, "approved_material_pins": 19,
        "approved_document_bindings": 3, "approved_offline_fixture_pins": 3,
        "approved_production_replacements": application,
        "application_authorized": True, "application_deferred_for_handoff": True,
        "application_completed": False, "s23_accepted": False,
        "offline_verification": "existing S23 offline authority; described packet validation remains unrun",
        "not_authorized": ["live calls", "credentials", "installations", "spending", "Git staging/commits/pushes", "S24", "S25"],
        "gitignore_ownership": "unverified; unchanged; not approved by this packet"}
    write_new(OUT / "authorization.json", (json.dumps(receipt, indent=2) + "\n").encode())
    notice = (
        "**S23 EXACT PACKET APPLICATION APPROVED, NOT YET APPLIED, 2026-10-07 Asia/Singapore.**\n\n"
        "The user said: `I approve the application but put the approval in the copy paste handoff prompt`.\n"
        f"This approves the refreshed inventory digest `{APPROVED}`\n"
        "and its four exact proposed production replacements, while all preimage/proposal\n"
        "bindings match. Application is deferred to the next chat at the user's request.\n"
        "The prepared packet and inventory retain their original bytes and historical\n"
        "NOT APPROVED labels; the separate authorization receipt records this later decision.\n"
        "Seals/pins remain unapplied, production review verification is unrun, and S23\n"
        "remains incomplete and unaccepted. No live, credential, install, spend, Git\n"
        "publication or S24/S25 authority is added. The ignore-rule exception is unchanged.\n\n"
    )
    documents = {}
    for relative in ("docs/plans/shiftwork/00-status.md", "docs/SHIFTWORK_PLAN.md"):
        path = ROOT / relative
        original = path.read_bytes()
        write_new(OUT / "preimages" / relative, original)
        prefix = "plans/shiftwork/" if relative == "docs/SHIFTWORK_PLAN.md" else ""
        links = (f"Current [approved application handoff]({prefix}slice23-approved-application-handoff-2026-10-07.md).\n"
                 f"Authorization: `{prefix}evidence/slice23-approval-handoff-2026-10-07/authorization.json`.\n\n")
        path.write_bytes((notice + links).encode() + original)
        assert path.read_bytes().endswith(original)
        documents[relative] = {"preimage_sha256": sha(original), "current_sha256": sha(path.read_bytes()),
                               "historical_suffix_preserved": True}
    assert sha((ROOT / "docs/plans/shiftwork/slice23-gtm-review-inventory.json").read_bytes()) == sha(inventory_raw)
    assert (ROOT / "docs/plans/shiftwork/slice23-gtm-operator-review-packet.md").read_bytes() == packet_raw
    for path, digest in files.items():
        assert sha((ROOT / path).read_bytes()) == digest
    assert subprocess.check_output(["git", "ls-files", "--stage"], cwd=ROOT) == index
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    outcome = {"status": "PASS", "application_authorized_but_unapplied": True,
        "prepared_packet_and_inventory_unchanged": True, "production_material_and_source_preimages_unchanged": len(files),
        "document_suffix_preservation": documents, "head_and_index_unchanged": True,
        "scope": "approval documentation only; no test rerun or production application"}
    write_new(OUT / "documentation-preservation.json", (json.dumps(outcome, indent=2) + "\n").encode())
    print(json.dumps(outcome))

if __name__ == "__main__":
    main()
