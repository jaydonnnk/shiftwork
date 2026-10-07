"""Record the completed regression result and the user's requested safe stop."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
DOCS = ROOT / "docs/plans/shiftwork"


def main():
    log = (OUT / "full-offline.log").read_text(encoding="utf-8-sig")
    summary = next(row for row in reversed(log.splitlines()) if "passed" in row and "warnings" in row)
    failures = [node for node in ET.parse(OUT / "full-offline.xml").getroot().iter("testcase") if node.find("failure") is not None or node.find("error") is not None]
    assert failures and {node.get("name") for node in failures} == {"test_byte_addressed_fixtures_match_lf_checkout"}, "record any different outcome manually before handoff"
    entry = json.loads((OUT / "entry.json").read_bytes())
    preservation = json.loads((OUT / "final-preservation.json").read_bytes())
    inventory = json.loads((DOCS / "slice23-gtm-review-inventory.json").read_bytes())
    affected = ["fixtures/requests/gtm_compare_manifest.json", "fixtures/requests/gtm_compare_pair_01_specs.json", "fixtures/requests/gtm_compare_pair_02_specs.json"]
    for path in affected: assert b"\r\n" in (ROOT / "shiftwork" / path).read_bytes()
    result = {"summary": summary, "failed_test": failures[0].get("name"), "guard_controls": 106,
        "production_applied": False, "slice_complete": False, "packet_ready_for_approval": False,
        "repair_applied": False, "user_requested_handoff": True, "affected_draft_files": affected,
        "current_unapproved_digest": inventory["approval_digest"]}
    (OUT / "handoff-result.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())
    mistakes = """

## 2026-10-07 S23 helper contracts and inspection paths

- **What happened:** retained first-focused/second-journey failures assumed files in frozen-version JSON and used the wrong investigation URL. Direct nested authoring invocation failed imports; runpy worked. Several guessed read paths and PowerShell expressions failed, including this continuation's inferred executor/reducer/conftest paths.
- **Root cause:** conceptual helper/file names were reused without copying the actual response, route, source path or launch context.
- **Prevention rule:** discover exact paths with rg --files, inspect the current signature/model/route and copy a compatible call before invoking. Existing AGENTS.md already graduates this repeated pattern; preserve that rule rather than adding a duplicate.

## 2026-10-07 S23 malformed membership inputs

- **What happened:** malformed decision and decision-trace objects exposed unhashable membership checks during the prior draft session. Both guards were corrected; focused negative tests retain these shapes.
- **Root cause:** vocabulary membership was attempted before confirming a hashable string shape.
- **Prevention rule:** validate structural type before set membership and exercise malformed JSON objects, not only incorrect strings.

## 2026-10-07 S23 isolated baseline checked a sanitized error

- **What happened:** guards-first retained five failed assertions because admit_pack replaces internal error details with a public generic message. The implementation refused as intended. Isolated tests now exercise _verify_pack_material for the internal guard and keep the public refusal tests separately.
- **Root cause:** an internal error regex was asserted through the sanitized public wrapper.
- **Prevention rule:** isolate at the responsible layer; check public safe messages only at the public boundary. Preserve the failed baseline.

## 2026-10-07 S23 omission controls crashed or overlapped

- **What happened:** mutations-first rejected snapshot_type and trace_short crashes, a review-owner omission masked by condition agreement and a wrong-batch omission that indexed an empty list. All four original rows remain rejected; repaired controls produce named assertion failures with zero setup errors and exact restoration.
- **Root cause:** removing a guard also violated another prerequisite or made a later access unsafe.
- **Prevention rule:** supply all later fields and indices correctly while varying only the targeted predicate. Match review conditions across all tasks. Fault the batch equality predicate rather than the empty-workload cardinality predicate. Retain the rejected controls.

## 2026-10-07 S23 no-reason aspect used the enum member name as its value

- **What happened:** guards-complete retained one failed test using NO_TASK_HAS_REASON_CODE as serialized kind; the actual enum value is NO_TASK_REASON_CODE. Corrected guards-verified passes all 80 tests.
- **Root cause:** a familiar member name was guessed as its wire value.
- **Prevention rule:** read enum values and copy current serialization before authoring a fixture or asserting an API vocabulary.

## 2026-10-07 S23 ledger fault inserted zero rows

- **What happened:** mutations-repaired's experiment_ledger_write control passed because INSERT SELECT copied an empty GTM ledger. It is not counted as proof. A literal synthetic insertion in mutations-final reaches the intended unchanged-business-rows assertion.
- **Root cause:** the fault assumed the failing S23 starter had already produced a ledger row; GTM consequence reduction is S24 scope.
- **Prevention rule:** verify the initial row inventory and inject a guaranteed valid write that changes exactly the tested surface. Preserve empty/no-op fault controls as rejected evidence.

## 2026-10-07 S23 regression found CRLF in unreviewed request drafts

- **What happened:** the final full offline suite fails test_byte_addressed_fixtures_match_lf_checkout on the GTM manifest and pair 01/02 spec files. The focused suite did not cover this repository-wide LF guard. No repair or seal followed because the user requested a context handoff.
- **Root cause:** draft request edits did not retain the existing LF-only byte-addressed fixture contract. The proposed -text attributes preserve the current bytes, including this defect.
- **Prevention rule:** normalize only unreviewed affected drafts to LF, retain preimages and regenerate every changed inventory/seal/pin proposal before seeking approval. Reproduce the named guard and full suite without weakening them.
"""
    path = ROOT / "MISTAKES.md"
    prefix = (OUT / "mistakes-prefix.bin").read_bytes()
    assert path.read_bytes() == prefix and hashlib.sha256(prefix).hexdigest() == entry["tracked"]["MISTAKES.md"]
    path.write_bytes(prefix + mistakes.replace("\n", "\r\n").encode())
    notice = f"""**S23 OFFLINE IMPLEMENTATION DRAFTED; REGRESSION BLOCKED, 2026-10-07 Asia/Singapore.**

The user authorized S23 offline implementation, draft material and concrete
operator-review preparation, then requested a handoff near the 200k context
boundary. S23 remains incomplete, unaccepted, unstaged and uncommitted on
`shiftwork/slice-23` at `3e02f1e`. This notice supersedes older S23 authorization
notices; their historical bytes and scope remain intact below.

Resumed focused baseline: 128 passed. Final focused group: 232 passed; the
expanded isolated guard/typed-family group passes 80 tests. The retained matrix
verifies 106 distinct source faults, each reaching its named assertion with
zero setup errors and exact restoration. Five rejected controls stay separate.
The disposable API/local-process rehearsal completes six fair slots with A and
B eligible, preserves business/selection rows and enforces two HINT/DIAGNOSIS
calls with no patch. This is hypothetical policy proof, not production approval.

Full offline regression: **{summary}**. The one LF-only fixture guard rejects
the unreviewed GTM manifest and pair 01/02 spec files containing CRLF. The repair
has not been applied. Repairing those drafts invalidates the current proposal
digest and requires fresh inventory, seal/source proposals and verification.
The concrete packet exists but is BLOCKED, NOT READY FOR APPROVAL.

All 4803 historical evidence files and 42 existing reviewed pins remain byte
exact; unchanged source lines retain their entry line endings. GTM pins are
empty and both seals remain null/DRAFT. No production GTM admission, real
reviewed comparison, live call, credential, install, spend, Git publication,
S24 or S25. The architecture scan records later retry/live-shape limits.

Current records: [offline checkpoint](LINK_CHECKPOINT),
[operator packet](LINK_PACKET), [handoff](LINK_HANDOFF).

"""
    for relative, links in (("docs/plans/shiftwork/00-status.md", ("slice23-offline-checkpoint-2026-10-07.md", "slice23-gtm-operator-review-packet.md", "slice23-handoff-2026-10-07.md")),
                            ("docs/SHIFTWORK_PLAN.md", ("plans/shiftwork/slice23-offline-checkpoint-2026-10-07.md", "plans/shiftwork/slice23-gtm-operator-review-packet.md", "plans/shiftwork/slice23-handoff-2026-10-07.md"))):
        path = ROOT / relative
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["tracked"][relative]
        (OUT / (path.stem + "-prefix.bin")).write_bytes(raw)
        text = notice.replace("LINK_CHECKPOINT", links[0]).replace("LINK_PACKET", links[1]).replace("LINK_HANDOFF", links[2])
        path.write_bytes(text.encode() + raw)
    packet = DOCS / "slice23-gtm-operator-review-packet.md"
    packet.write_bytes(("**REGRESSION BLOCKED, 2026-10-07. NOT READY FOR APPROVAL.**\n\n"
        "The full offline suite rejects CRLF in three unreviewed GTM request files.\n"
        "No repair or application occurred before the requested handoff. The inventory\n"
        "below still matches those current bytes, but must be superseded after repair.\n"
        "No operator approval is being requested.\n\n").encode() + packet.read_bytes())
    architecture = DOCS / "slice23-architecture-review-2026-10-07.md"
    architecture.write_bytes(("**Regression hold:** the full suite found three CRLF request drafts.\n"
        "S23 and its packet remain blocked on that repair; no current readiness claim.\n\n").encode() + architecture.read_bytes())
    checkpoint = f"""# S23 offline checkpoint, 2026-10-07

Status: REGRESSION BLOCKED. Stopped at the user's requested context handoff.
Production GTM remains unavailable; S23 is incomplete and not accepted.

- Pre-change 1070-pass baseline is from the incoming handover; this continuation did not rerun pre-change bytes.
- Reproduced S23 baseline: 128 passed, two warnings, resumed-focused.log/xml.
- Final API/material/registry group: 232 passed, two warnings, final-focused.log/xml.
- Expanded isolated branch, all-six-variant A/B and typed-family group: 80 passed, two warnings, guards-verified.log/xml.
- 106 distinct omission/write controls verified from raw JUnit and log hashes, exact named assertions, no setup errors and byte restoration. Latest accepted rows combine mutations-first, mutations-repaired and mutations-final. Five rejected rows remain explicitly excluded in final-preservation.json.
- Full offline suite: **{summary}**. Packaging excluded because it installs dependencies. Raw receipt: full-offline.log/xml. No post-failure repair or rerun.
- Failure: tests/executor/test_conformance.py::test_byte_addressed_fixtures_match_lf_checkout. Affected new drafts: GTM manifest and pair 01/02 spec JSON. Existing byte-addressed fixture LF guard is valid and unchanged.
- Disposable comparison proof: disposable-comparison-proof.json. Six slots COMPLETE; both candidates eligible; A REVIEW and B QUALIFIED on the recorded-intent signal; before/after business rows identical; two fake assist roles. This is hypothetical review/pins, not the production-reviewed S23 exit.
- Raw preservation: 4803 prior evidence files, 42 existing pins, unchanged tracked files and unchanged source lines verified. Branch/HEAD/index unchanged. Final post-document audit remains in final-preservation.json.
- Architecture preflight records bounded recursive retry re-assessment and the existing two-public-request live preflight as later S24/S25 limits. No cleanup deletion.

Evidence directory: `evidence/slice23-preflight-2026-10-07/`.
The current unapplied packet digest is `{inventory['approval_digest']}`. It must not
be approved as ready: LF repair changes its manifest/spec hashes and source pin
proposal. Current proposed-application files, current-proposal-inventory.json and
source diffs are historical pre-repair proposals. build_packet.py hardcodes their
directory and assumes its bytes match the current inventory; it needs a fresh
proposal destination after repair. gtm_review.py --out and --proposal-dir refuse
overwrite, preserving the preimages.

No production seals/pins, live calls, credentials, installs, spending, commits,
pushes or later slices were authorized or performed. Acceptance and the real
reviewed comparison remain pending after a corrected concrete packet and its
separate operator approval.
"""
    (DOCS / "slice23-offline-checkpoint-2026-10-07.md").write_bytes(checkpoint.encode())
    prompt = f"""Background handover for Shiftwork S23, stopped at the user's request on 2026-10-07 near the 200k context boundary.

Workspace: C:\\Users\\jayd0\\OneDrive\\Desktop\\nebius_nvidia
Branch: shiftwork/slice-23
HEAD: 3e02f1e5176cd34d6dc355bbc4529234fa51fe62
All changes are S23 session work, unstaged/uncommitted. No test process remains running.

Authorization covers offline implementation, draft material and preparing an operator packet. Production seals/pins, live calls, credentials, installations, spending, commits/pushes and S24/S25 remain unauthorized.

The GTM pack draft, pure assessor, starter, two candidates, three public batches of three requests and six protected variants are implemented. B uses hand-authored recorded confidence; no model call or external CRM action. Production pins remain empty; manifest/family remain DRAFT with null seals.

Verified in this continuation: 128 resumed focused tests, 232 final focused tests and 80 expanded guard/typed-family tests. There are 106 verified distinct source faults with named assertion failures, zero setup errors and exact restoration. Five rejected controls are retained separately. Disposable API/local-process comparison completes six slots with both candidates eligible and no comparison-time business/selection writes. All six protected variants also pass A/B answer-function checks. These are hypothetical reviewed-copy mechanics, not production approval or the reviewed S23 exit.

Full offline regression: {summary}. The failure is test_byte_addressed_fixtures_match_lf_checkout: the unreviewed GTM manifest and pair 01/02 spec JSON contain CRLF. No repair was applied. The existing LF guard is valid. LF repair changes material hashes and invalidates the current packet/proposals; the original first-draft and pre-repair proposals remain preserved. No approval of any packet was given.

All 4803 historical evidence files, 42 existing reviewed pins, unchanged tracked files and source-line endings were verified. Status, supporting brief, mistakes, architecture review and the blocked operator packet are recorded. The exact final audit is final-preservation.json in docs/plans/shiftwork/evidence/slice23-preflight-2026-10-07. Full logs/JUnit, source faults, proposal inventory/source diffs and disposable comparison receipt are there.

Current checkpoint: docs/plans/shiftwork/slice23-offline-checkpoint-2026-10-07.md.
Detailed handoff/review prompt: docs/plans/shiftwork/slice23-handoff-2026-10-07.md.
The read-only demos/gtm_review.py generates fresh inventory and unapplied source/seal files with exclusive output paths. build_packet.py is a retained one-off helper bound to the pre-repair proposal directory; replaying it after LF repair without updating its directory will fail. artifacts/slice23/generate_drafts.py is a historical shorter-batch authoring snapshot and refuses overwrite.

Remaining work is the LF repair, refreshed exact packet and verification, then separate operator approval/application and the real reviewed six-slot comparison. S23 remains incomplete and unaccepted.

Wait for instructions before taking any action."""
    file_lines = []
    descriptions = {
        ".gitattributes": "appended 19 explicit GTM material -text rules; existing prefix preserved",
        "MISTAKES.md": "appended session errors, rejected controls and the CRLF regression; original prefix preserved",
        "docs/SHIFTWORK_PLAN.md": "prepended current S23 authorization, incomplete status and regression hold",
        "docs/plans/shiftwork/00-status.md": "prepended the same current authority/result; S23 stays unchecked",
        "shiftwork/domain/task_contract.py": "added GTM task/claim vocabulary, pinned request conditions, signal state and additive protected signal support",
        "shiftwork/evaluator/evaluator.py": "added pure qualification/owner/evidence/handoff/retry assessment from frozen inputs",
        "shiftwork/domain/models.py": "added three GTM contract options",
        "shiftwork/domain/customer_answer.py": "added bounded synthetic GTM rendering",
        "shiftwork/api/schemas.py": "added GTM public claim vocabulary without widening legacy sealed claim grammar",
        "shiftwork/config.py": "added GTM starter contract and owning-pack offline fixture-key selection; production GTM fixture pins remain absent",
        "shiftwork/orchestrator.py": "added GTM owning-material checks, starter opening, frozen retry inputs and S24 operation refusal",
        "shiftwork/experiments.py": "uses the GTM-specific starter fixture key",
        "shiftwork/comparison_flow.py": "uses GTM-specific candidate fixture keys",
        "shiftwork/sealed/store.py": "added protected GTM company/signal privacy needles",
        "demos/gtm_review.py": "expanded read-only inventory with document/material pins, fixture hashes and unapplied exact source/seal proposals",
        "tests/orchestrator/test_gtm_pipeline.py": "128 draft policy/API/local-process checks; expanded packet checks and isolated review-owner invalid inputs",
        "tests/orchestrator/test_gtm_guards.py": "80 isolated guard, all-six-variant A/B and typed-family/aspect checks",
        "tests/packs/gtm_material.py": "disposable hypothetical review/seal/pin helpers",
        "tests/packs/gtm_mutation_proofs.py": "106 source controls with exclusive raw logs/JUnit and exact restoration",
    }
    for path in (*sorted(preservation["tracked_changes"]), *preservation["untracked"]):
        absolute = ROOT / path
        if not absolute.is_file(): continue
        count = len(absolute.read_bytes().splitlines())
        description = descriptions.get(path, "new S23 draft material or current plan/review record; exact bytes bound by the inventory and diff")
        file_lines.append(f"- `{path}:1-{count}`: {description}.")
    review = """Independently and adversarially review the Shiftwork S23 uncommitted draft in C:\\Users\\jayd0\\OneDrive\\Desktop\\nebius_nvidia on shiftwork/slice-23 at 3e02f1e. Assume the work may be flawed. Be unbiased, thorough and honest. Gate 4 Slice 23 and obligations 16, 17, 20, 23, 39, 40, 55, 57 and 60 define the standard.

The current claim is 106 verified guard faults, passing disposable comparison/80 expanded guard tests and preserved historical bytes. S23 is explicitly incomplete: the full suite fails the LF fixture guard, production pins/seals remain absent and the packet is blocked. No live/model/CRM/learner-quality evidence is claimed.

Inspect the actual diff and raw receipts, re-run appropriate offline tests and stress-test independent guard capability, owning-pack inputs, retry evidence, no-send rendering, public/protected business isolation and assist policy. Audit final-preservation.json against entry.json and the named log/JUnit hashes. Assess implementation quality, hidden assumptions, scope creep and evidence gaps. Do not pass tests for the sake of passing; flag weak, overlapping, incidental or unverified proof. Green output is not approval or acceptance. Do not apply seals/pins, install, access credentials, call external services, publish or alter historical evidence.

Report PASS / ISSUES FOUND / FAIL with specific file/line and reproduced evidence per finding. Deliver your verdict and wait for instructions."""
    handoff = "# S23 session transfer, 2026-10-07\n\n" + checkpoint.split("\n", 1)[1] + "\n## Files\n\n" + "\n".join(file_lines) + "\n\n## Prompt for New Chat\n\n```text\n" + prompt + "\n```\n\n## Prompt for Handoff Review\n\n```text\n" + review + "\n```\n"
    (DOCS / "slice23-handoff-2026-10-07.md").write_bytes(handoff.encode())
    print(json.dumps(result))


if __name__ == "__main__": main()
