"""Record a verified LF repair without granting production review authority."""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
DOCS = ROOT / "docs/plans/shiftwork"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write_new(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)

def main():
    incoming = json.loads((OUT / "incoming.json").read_bytes())
    result = json.loads((OUT / "full-offline-result.json").read_bytes())
    assert result["exit_code"] == 0
    for kind in ("log", "xml"):
        assert sha((OUT / ("full-offline." + kind)).read_bytes()) == result[kind + "_sha256"]
    suites = list(ET.parse(OUT / "full-offline.xml").getroot().iter("testsuite"))
    assert len(suites) == 1
    suite = suites[0]
    assert suite.get("tests") == "1279" and suite.get("failures") == "0"
    assert suite.get("errors") == "0" and suite.get("skipped") == "1"
    nodes = list(suite.iter("testcase"))
    assert len(nodes) == 1279
    skipped = [{"classname": n.get("classname"), "name": n.get("name"), "reason": s.get("message")}
               for n in nodes for s in n.findall("skipped")]
    log = (OUT / "full-offline.log").read_text()
    summary = re.search(r"1278 passed, 1 skipped, 2 warnings in .+", log)
    assert summary is not None
    summary = summary.group(0).strip()
    verification = json.loads((OUT / "packet-verification.json").read_bytes())
    assert verification["status"] == "PASS"
    inventory = json.loads((DOCS / "slice23-gtm-review-inventory.json").read_bytes())
    assert inventory["approval_digest"] == verification["approval_digest"]
    digest = inventory["approval_digest"]
    preservation = json.loads((OUT / "pre-document-preservation.json").read_bytes())
    assert preservation["status"] == "PASS_WITH_PREEXISTING_EXCEPTION"
    checkpoint = f"""# S23 LF repair checkpoint, 2026-10-07

Status: LF blocker repaired. Exact packet ready for operator material review,
with the incoming ignore-rule exception disclosed. NOT APPROVED OR APPLIED.
S23 remains incomplete, unaccepted, unstaged and uncommitted.

Branch `shiftwork/slice-23`; HEAD `3e02f1e5176cd34d6dc355bbc4529234fa51fe62`.
The user's `Go` resumed offline implementation and packet preparation only.

## Verified repair

- `lf-before.log/xml`: the unchanged repository LF guard reproduced one failed
  assertion identifying the GTM manifest and pair 01/02 task-spec JSON.
- `lf-repair.json`: replaced only 36, 225 and 221 CRLF sequences respectively.
  Every parsed JSON value is identical; manifest/family remain DRAFT/null.
  Original bytes are retained under this continuation's `preimages/`.
- `lf-after.log/xml`: 2 passed, 2 warnings, including the existing LF guard and
  packet preimage/proposed-seal check. No test or assertion was weakened.
- `full-offline.log/xml`: **{summary}**, exit 0. JUnit confirms 1279
  cases, zero failures, zero errors and one skip. Packaging was excluded because
  installation is unauthorized. The skip is the separately authorized live
  Token Factory conformance arm. The two deprecation warnings remain.

## Refreshed packet

Approval digest: `{digest}`.

Current records: [operator packet](slice23-gtm-operator-review-packet.md) and
[machine inventory](slice23-gtm-review-inventory.json).
Fresh proposal files and narrow source diffs are in
`evidence/slice23-lf-repair-2026-10-07/proposed-application/` and its parent.
`packet-verification.json` verifies all 19 material preimages, two seal-only
JSON edits, 19 proposed material pins, three document bindings and three offline
fixture pins. AST comparison confines source edits to GTM declarations and
the three fixture entries. All matching registry/config lines retain their
exact bytes and line endings. All 19 effective Git text attributes are unset.
Canonical workload/case seals and artifact fixture hashes did not change.
The seven changed hash fields and new digest are in `packet-refresh-changes.json`.
The original first-draft and pre-repair proposals remain preserved and superseded.

## Preservation and limits

`pre-document-preservation.json` verifies 4803 pre-S23 historical evidence
files, all 5065 incoming evidence files and 42 existing reviewed material files.
All incoming production source and tests are unchanged. The 106 retained
source-fault controls were audited against their exact source hashes, unique
anchors, named raw JUnit assertions and log hashes; they were not rerun.
Five rejected controls remain excluded. The full suite reruns ordinary guard,
material and hypothetical comparison checks. Earlier disposable six-slot
evidence remains hypothetical and is not the production-reviewed S23 exit.

The incoming `.gitignore` SHA-256 remains
`{incoming['gitignore_sha256']}`. Ownership of its request-directory rule is
unverified. All eight hidden GTM request drafts are explicitly inventoried.
The earlier post-document audit remains a failed historical receipt. This
continuation's checks disclose the preserved incoming exception and do not
claim that the original whole-tree hold is resolved. Final document/scope
verification is recorded separately in `continuation-preservation.json`;
read that receipt for its actual verdict.

No production pins/seals, actual GTM admission, credentials, installs, live
calls, spending, Git staging/commits/pushes, S24 or S25. Retry scaling and the
existing live two-request preflight remain later-slice limits.

## Next authorized boundary

The operator must approve the exact 19-file material packet, its four proposed
production replacements and the offline admission/starter/six-slot comparison.
Retain that explicit authorization and refuse preimage/digest drift before
application. Only then may production review authority be applied. Complete
the actual reviewed comparison and post-slice architecture cleanup before
requesting S23 acceptance. Live work and later slices remain separately gated.

Post-approval verification must also transition the prereview-only tests and
disposable helper in `test_gtm_pipeline.py` and `gtm_material.py` to the exact
approved inventory. They currently require DRAFT/null production material.
Keep the draft inventory CLI draft-only, retain the reviewed receipt, preserve
all refusal/fault guards, and rerun the full suite before acceptance. The current
green suite is pre-application evidence, not evidence of that later state.
"""
    checkpoint_path = DOCS / "slice23-lf-repair-checkpoint-2026-10-07.md"
    write_new(checkpoint_path, checkpoint.encode())
    packet_path = DOCS / "slice23-gtm-operator-review-packet.md"
    raw = packet_path.read_bytes()
    old_status = b"Status: PREPARED; FULL REGRESSION PENDING. NOT APPROVED OR APPLIED."
    assert raw.count(old_status) == 1
    raw = raw.replace(old_status,
        b"Status: READY FOR OPERATOR MATERIAL REVIEW, WITH DISCLOSED IGNORE-RULE EXCEPTION.\n"
        b"NOT APPROVED OR APPLIED. S23 remains incomplete.", 1)
    boundary = b"## Verification and application boundary"
    assert raw.count(boundary) == 1
    evidence_line = (f"Full offline suite: {summary}, exit 0. Packaging excluded.\n"
                     "Packet preimage/proposal verification: PASS. Original failed receipts remain.\n\n").encode()
    raw = raw.replace(boundary, boundary + b"\n\n" + evidence_line, 1)
    raw += (b"\nPost-approval verification includes transitioning prereview-only test assertions\n"
            b"and disposable helpers to strict approved-inventory checks, preserving all\n"
            b"refusal/fault guards and rerunning the full offline suite before acceptance.\n"
            b"The current suite is pre-application evidence; the review CLI remains draft-only.\n")
    packet_path.write_bytes(raw)
    shared_notice = (
        "**S23 LF REPAIR VERIFIED; AWAITING OPERATOR MATERIAL REVIEW, 2026-10-07 Asia/Singapore.**\n\n"
        f"The continuation repaired only three unreviewed CRLF drafts. Full offline\n"
        f"regression: {summary}, exit 0; packaging excluded.\n"
        "Production GTM pins remain absent and both seals remain DRAFT/null. The\n"
        "fresh exact packet is ready for material review with the incoming `.gitignore`\n"
        "exception disclosed. Its ownership remains unverified and its bytes preserved;\n"
        "all eight hidden request drafts are explicitly inventoried. S23 is incomplete\n"
        "and unaccepted. No application, live work, Git publication or later slice.\n\n"
        "The notices below describe the earlier handoff state and are superseded only\n"
        "for this LF repair and packet refresh. Their bytes and failed receipts remain.\n"
    )
    for relative in ("docs/SHIFTWORK_PLAN.md", "docs/plans/shiftwork/00-status.md",
                     "docs/plans/shiftwork/slice23-offline-checkpoint-2026-10-07.md",
                     "docs/plans/shiftwork/slice23-handoff-2026-10-07.md",
                     "docs/plans/shiftwork/slice23-architecture-review-2026-10-07.md"):
        path = ROOT / relative
        original = path.read_bytes()
        assert sha(original) == incoming["files"][relative]
        backup = OUT / "preimages" / relative
        if backup.is_file():
            assert backup.read_bytes() == original
        else:
            write_new(backup, original)
        prefix = "plans/shiftwork/" if relative == "docs/SHIFTWORK_PLAN.md" else ""
        links = (f"Current [repair checkpoint]({prefix}slice23-lf-repair-checkpoint-2026-10-07.md)\n"
                 f"and [operator packet]({prefix}slice23-gtm-operator-review-packet.md).\n\n")
        if path.name == "slice23-handoff-2026-10-07.md":
            links += "The fenced prompts below describe the superseded blocked state; use the current checkpoint for continuation.\n\n"
        path.write_bytes((shared_notice + links).encode() + original)
        assert path.read_bytes().endswith(original)
    architecture = """# S23 LF repair architecture preflight

2026-10-07 Asia/Singapore. Material review preparation only; S23 not accepted.
Uses the architect-reviewer scope and cleanup principles.

| Category | Verdict | Evidence and decision |
|---|---|---|
| Narrow repair | PASS | Three CRLF-only changes; parsed JSON identical. No runtime source or test changes. |
| Existing patterns | PASS within prior scope | Incoming pack/evaluator/comparison source hashes unchanged; full offline suite and retained guard receipts verify the same implementation. This is not a new broad architecture review. |
| Proposal scope | PASS | Packet AST comparison: GTM pins/documents and three fixture pins only. Seals/pins remain unapplied. |
| Historical preservation | PASS with incoming exception | Pre-document audit retains historical bytes and existing pins. `.gitignore` ownership remains unverified; final receipt must be checked. |
| Retry scale and live evolution | RISK, later scope | Prior retry recursion remains bounded only by current short batches; live preflight still assumes two public requests. Address in separately authorized S24/S25. |

Keep the original packet/inventories, CRLF preimages, original failed audit,
rejected controls and old proposal files as historical evidence. Current docs
point to the fresh packet and checkpoint. No file deletion, refactor, dependency,
framework, CI or lockfile change is proposed. Actual production-reviewed proof
and the acceptance cleanup remain pending after separate operator approval.
"""
    write_new(DOCS / "slice23-lf-repair-architecture-preflight-2026-10-07.md", architecture.encode())
    final = {"status": "READY_FOR_OPERATOR_MATERIAL_REVIEW_WITH_INCOMING_EXCEPTION",
             "full_suite_summary": summary, "full_suite_exit_code": 0, "skipped": skipped,
             "approval_digest": digest, "production_application": False,
             "s23_complete": False, "s23_accepted": False, "gitignore_ownership": "unverified"}
    write_new(OUT / "closeout.json", (json.dumps(final, indent=2) + "\n").encode())
    print(json.dumps(final))

if __name__ == "__main__":
    main()
