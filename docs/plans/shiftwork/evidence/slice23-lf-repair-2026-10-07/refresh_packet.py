"""Refresh current review records; retain incoming packet and old proposals."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
DOCS = ROOT / "docs/plans/shiftwork"

def main():
    inventory_path = DOCS / "slice23-gtm-review-inventory.json"
    packet_path = DOCS / "slice23-gtm-operator-review-packet.md"
    old_inventory_raw = (OUT / "preimages/docs/plans/shiftwork/slice23-gtm-review-inventory.json").read_bytes()
    old_packet_raw = (OUT / "preimages/docs/plans/shiftwork/slice23-gtm-operator-review-packet.md").read_bytes()
    assert inventory_path.read_bytes() == old_inventory_raw
    assert packet_path.read_bytes() == old_packet_raw
    new_inventory_raw = (OUT / "review-inventory.json").read_bytes()
    old, new = json.loads(old_inventory_raw), json.loads(new_inventory_raw)
    assert old["workloads_payload_sha256"] == new["workloads_payload_sha256"]
    assert old["cases_payload_sha256"] == new["cases_payload_sha256"]
    changes = []
    replacements = {old["approval_digest"]: new["approval_digest"]}
    for key, fields in (("files", ("sha256", "proposed_sha256")),
                        ("application_sources", ("preimage_sha256", "proposed_sha256"))):
        for before, after in zip(old[key], new[key], strict=True):
            assert before["path"] == after["path"]
            for field in fields:
                if before[field] != after[field]:
                    if before[field] in replacements:
                        assert replacements[before[field]] == after[field]
                    replacements[before[field]] = after[field]
                    changes.append({"path": before["path"], "field": field,
                                    "before": before[field], "after": after[field]})
    text = old_packet_raw.decode()
    marker = "# S23 Stonebridge exact-byte operator review packet"
    assert text.count(marker) == 1
    text = marker + text.split(marker, 1)[1]
    for before, after in replacements.items():
        assert before in text
        text = text.replace(before, after)
    text = text.replace("Status: PREPARED, NOT APPROVED OR APPLIED. S23 remains incomplete.",
                        "Status: PREPARED; FULL REGRESSION PENDING. NOT APPROVED OR APPLIED.")
    text = text.replace("Each first processed signal has one synthetic owner and record.",
                        "Each first processed qualified or review signal has one synthetic owner and record.")
    history_anchor = ("Machine packet: [current inventory](slice23-gtm-review-inventory.json). The first\n"
                      "[draft inventory](evidence/slice23-preflight-2026-10-07/first-draft-inventory.json)\n"
                      "is superseded and must never be applied.")
    assert text.count(history_anchor) == 1
    text = text.replace(history_anchor,
                        "Machine packet: [current inventory](slice23-gtm-review-inventory.json).\n"
                        "The first-draft and pre-repair inventories/proposals are superseded. Their\n"
                        "bytes remain preserved in the original evidence and continuation preimages.")
    text = text.replace("evidence/slice23-preflight-2026-10-07/proposed-application/",
                        "evidence/slice23-lf-repair-2026-10-07/proposed-application/")
    for stem in ("registry", "config"):
        text = text.replace(f"evidence/slice23-preflight-2026-10-07/{stem}-application.diff",
                            f"evidence/slice23-lf-repair-2026-10-07/{stem}-application.diff")
    text = text.replace("slice23-offline-checkpoint-2026-10-07.md", "slice23-lf-repair-checkpoint-2026-10-07.md")
    text += ("\r\n## Incoming ignore-rule exception\r\n\r\n"
             "The unexpected `/shiftwork/fixtures/requests/` ignore rule remains byte-exact\r\n"
             "from the incoming handoff, with unverified ownership. The eight GTM request\r\n"
             "drafts are explicitly included in this inventory despite being hidden from\r\n"
             "ordinary status. This packet does not approve that rule or Git publication.\r\n"
             "The old final-state preservation hold remains a historical failure; the\r\n"
             "continuation reports its preservation checks with this exception explicit.\r\n")
    assert old["approval_digest"] not in text
    assert "FULL REGRESSION PENDING" in text
    inventory_path.write_bytes(new_inventory_raw)
    packet_path.write_bytes(text.encode())
    with (OUT / "packet-refresh-changes.json").open("xb") as stream:
        stream.write((json.dumps({"status": "PREPARED_REGRESSION_PENDING", "changes": changes,
                     "canonical_seals_unchanged": True, "production_application": False}, indent=2) + "\n").encode())
    print(json.dumps({"approval_digest": new["approval_digest"], "changed_hash_fields": len(changes),
                      "regression": "PENDING", "production_application": False}))

if __name__ == "__main__":
    main()
