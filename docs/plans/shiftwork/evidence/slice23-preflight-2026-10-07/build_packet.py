"""Local packet/report preparation. Never applies production pins or seals."""
import difflib
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from demos.gtm_review import draft_inventory, proposed_application_sources
from shiftwork import config

OUT = Path(__file__).resolve().parent
DOCS = ROOT / "docs/plans/shiftwork"


def main():
    inventory = draft_inventory()
    stale = (DOCS / "slice23-gtm-review-inventory.json").read_bytes()
    first = (OUT / "first-draft-inventory.json").read_bytes()
    if json.loads(stale)["approval_digest"] != inventory["approval_digest"]:
        if stale != first:
            with (OUT / "superseded-review-inventory.json").open("xb") as stream: stream.write(stale)
        (DOCS / "slice23-gtm-review-inventory.json").write_bytes((json.dumps(inventory, indent=2) + "\n").encode())
    lines = ["# S23 Stonebridge exact-byte operator review packet", "",
        "2026-10-07 Asia/Singapore. Branch `shiftwork/slice-23`; HEAD `3e02f1e`.",
        "Status: PREPARED, NOT APPROVED OR APPLIED. S23 remains incomplete.", "",
        "Approval is limited to these 19 fictional material files, two proposed seals,",
        "19 GTM material pins, three document bindings and three trusted-local fixture pins.",
        "Application changes four production files: the manifest, protected family, registry",
        "and configuration. All other material bytes stay exact. No live model, CRM,",
        "customer message, credential, installation, spend, commit, push or S24/S25.", "",
        "## Material decision", "",
        "The starter incorrectly routes an APAC platform demo to the AMER owner. A uses",
        "rules-first routing and conservative human review. B uses hand-authored synthetic",
        "intent/confidence for direct routing. B has made no model call. Both plausible",
        "decisions on the confident non-explicit buying signal are accepted; neither is ranked.", "",
        "Suppressed accounts and companies below 50 employees are disqualified. Stale",
        "enrichment (older than 3600000 ms), provider outage, unknown region/product,",
        "ambiguous intent or confidence below 80 requires review. Current confident research",
        "is disqualified. Explicit demo, pricing or security-review buying notes qualify.",
        "Qualified owner follows the frozen six-entry region/product map; review uses",
        "`revenue-review`. Disqualified signals create no owner, write or handoff.",
        "Each first processed signal has one synthetic owner and record. Review requires a",
        "human-handoff record. Retries preserve the captured decision and produce no second",
        "owner, record or handoff. Outputs do not establish any external CRM action.", "",
        "Rules: [qualification and routing](../../../shiftwork/fixtures/documents/gtm/qualification_routing_rules.md).",
        "Three public workloads each contain three requests. One unseen variant is reserved",
        "per pair and shared by A/B; one comparison uses three of the six variants.", "",
        "## Six protected expected decisions", "",
        "This section is operator material. It must not enter learner responses or prompts.", "",
        "| Variant | Condition | Decision | Owner and record | Handoff |",
        "|---|---|---|---|---|"]
    descriptions = ("APAC platform demo", "EMEA analytics demo", "Ambiguous, confidence 35",
                    "Suppressed account", "Stale enrichment", "Frozen existing-record retry")
    family = json.loads((config.PACKAGE_DIR / "sealed/cases/gtm_pipeline_ownership.json").read_bytes())
    for index, (case, description) in enumerate(zip(family["cases"], descriptions, strict=True), 1):
        condition = case["stimulus"]["task_spec"]["tasks"][0]["condition_json"]
        decision = condition["expected_decisions"][0]
        owner = "revenue-review" if decision == "REVIEW" else condition["qualified_owner"]
        action = "No owner or record" if decision == "DISQUALIFIED" else "Retain existing APAC owner; no second write" if index == 6 else owner + "; one record"
        lines.append(f"| {index:02d} | {description} | {decision} | {action} | {'One review record' if decision == 'REVIEW' else 'None'} |")
    lines += ["", "The `qualified_owner` field pins the qualified route only. In variants 03/05 the",
        "actual review owner is `revenue-review`; in variant 04 there is no owner.", "",
        "## Exact approval binding", "",
        f"Approval digest (SHA-256 of canonical inventory without this digest): `{inventory['approval_digest']}`.",
        "Machine packet: [current inventory](slice23-gtm-review-inventory.json). The first",
        "[draft inventory](evidence/slice23-preflight-2026-10-07/first-draft-inventory.json)",
        "is superseded and must never be applied.", "",
        "| Material path beneath shiftwork | Current SHA-256 | Proposed SHA-256 |",
        "|---|---|---|"]
    lines += [f"| {row['path']} | `{row['sha256']}` | `{row['proposed_sha256']}` |" for row in inventory["files"]]
    lines += ["", "Only the manifest/family bytes change: `review_status` becomes `OPERATOR_SEALED`",
        "and the null seal becomes the exact canonical payload digest. Other draft metadata",
        "stays byte-identical; review authority is the operator decision and literal pins.", "",
        f"Workloads canonical seal: `{inventory['workloads_payload_sha256']}`.",
        f"Cases canonical seal: `{inventory['cases_payload_sha256']}`.",
        f"Catalog content hash (repository canonical format): `{inventory['catalog_hash']}`.", "",
        "## Proposed source application", "",
        "| File | Current SHA-256 | Proposed SHA-256 |",
        "|---|---|---|"]
    lines += [f"| {row['path']} | `{row['preimage_sha256']}` | `{row['proposed_sha256']}` |" for row in inventory["application_sources"]]
    for path, raw in proposed_application_sources(inventory).items():
        destination = OUT / "proposed-application" / path
        assert destination.read_bytes() == raw, "refresh proposals before preparing packet"
        diff = "".join(difflib.unified_diff((ROOT / path).read_text().splitlines(keepends=True), raw.decode().splitlines(keepends=True),
                                       fromfile=path, tofile=path + " (proposed)"))
        (OUT / (Path(path).stem + "-application.diff")).write_bytes(diff.encode())
    lines += ["", "Read-only proposed files: [application directory](evidence/slice23-preflight-2026-10-07/proposed-application/).",
        "Source diffs: [registry](evidence/slice23-preflight-2026-10-07/registry-application.diff),",
        "[config](evidence/slice23-preflight-2026-10-07/config-application.diff).", "",
        "| Document ID | Station | Material path | SHA-256 |", "|---|---|---|---|"]
    lines += [f"| {row['doc_id']} | {row['station']} | {row['path']} | `{row['sha256']}` |" for row in inventory["documents"]]
    lines += ["", "| Offline fixture key | Artifact content hash | Files hash |", "|---|---|---|"]
    lines += [f"| {row['key']} | `{row['artifact_content_hash']}` | `{row['files_hash']}` |" for row in inventory["offline_fixture_pins"]]
    lines += ["", "Starter contract is bound in the inventory: catalog 1, 3000 ms limit,",
        "NEVER_UNOWNED_OR_DUPLICATE_SIGNAL, REVIEW_AMBIGUOUS_SIGNAL and",
        "DEDUPLICATE_PIPELINE_BY_SIGNAL. Exact declared limits disclose synthetic outputs.", "",
        "## Verification and application boundary", "",
        "The [offline checkpoint](slice23-offline-checkpoint-2026-10-07.md) records focused,",
        "source-omission, regression, architecture and byte-preservation receipts.",
        "The disposable rehearsal proves mechanics only. It is not the reviewed S23 exit.", "",
        "After explicit approval, recheck this entire inventory and all application preimages,",
        "retain the exact user authorization, apply only the four proposed byte sequences and",
        "verify the 19 pins, three document bindings and three fixture pins. Refuse any drift.",
        "Then check actual admission/idempotent seeding, reproduce the reviewed starter and",
        "run the six-slot trusted-local comparison with production pins. Record that comparison,",
        "the unchanged comparison-time business rows and bounded assistance proof before",
        "requesting S23 acceptance. S24 selection/operation and S25 live work remain separate.", ""]
    (DOCS / "slice23-gtm-operator-review-packet.md").write_bytes("\n".join(lines).encode())
    print(json.dumps({"approval_digest": inventory["approval_digest"], "production_applied": False}))


if __name__ == "__main__": main()
