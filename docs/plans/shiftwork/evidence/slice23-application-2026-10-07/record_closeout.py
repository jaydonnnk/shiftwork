"""Record completed checks only after the final full offline suite succeeds."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
DOCS = ROOT / "docs/plans/shiftwork"


def write(name, content):
    path = DOCS / name
    assert not path.exists(), name
    path.write_bytes(content.encode())


def main():
    result = json.loads((OUT / "full-offline-verified-result.json").read_bytes())
    assert result["exit_code"] == result["failures"] == result["errors"] == 0
    passed = result["tests"] - result["skipped"]
    assert passed == 1281 and result["skipped"] == 1
    prefix = """**S23 APPROVED APPLICATION AND OFFLINE PROOFS COMPLETE; ACCEPTANCE PENDING, 2026-10-07 Asia/Singapore.**

The approved digest `8d87c2dc279f31f3206ec389e0f72b34b50e038c59bc764ef60c13489b62d1fa`
was applied as four exact replacements: 19 material files, two seals, 19 pins,
three document bindings and three literal offline fixture pins now verify.
Post-application regression: 1281 passed, 1 skipped, 2 warnings, exit 0;
packaging excluded and live conformance skipped. All 106 retained fault controls
were rerun, each caught by its intended assertion with zero setup errors and
exact source restoration. The five rejected historical controls remain excluded.
Production-reviewed offline proof: actual admission, idempotent seeding, GTM v5
preservation, starter owner/write failures, six fair slots and 25 verified
captures; both candidates eligible, business rows unchanged. Assistance uses
two fake HINT/DIAGNOSIS calls, with excess and patch requests refused.

The publication inventory explicitly includes all eight ignored GTM requests.
The incoming unowned `.gitignore` change remains exact and excluded. An external
AGENTS.md context-threshold change was observed, retained and excluded; ownership
is unverified. The old failed whole-tree audit remains unresolved history.
The prepared packet and inventory still retain historical NOT APPROVED labels;
separate authorization and application receipts establish the later decision.
The first new full run caught a copied sentinel test in entry preimages. Its
bytes were retained in a verified lossless archive, the original guard stayed
unchanged, and six focused sentinel checks plus the final full suite passed.

Current CHECKPOINT_LINK. APPLICATION_ROOT contains raw logs, JUnit, the retained
comparison database, fault receipts and final preservation receipt. Earlier
notices below remain byte-exact historical states. S23 is unaccepted, unstaged
and uncommitted. No Git publication, live call, credentials, installations,
spending, S24 or S25 were authorized or performed.

"""
    for relative, link, evidence in (
        ("docs/plans/shiftwork/00-status.md", "[application checkpoint](slice23-application-checkpoint-2026-10-07.md)", "`evidence/slice23-application-2026-10-07/`"),
        ("docs/SHIFTWORK_PLAN.md", "[application checkpoint](plans/shiftwork/slice23-application-checkpoint-2026-10-07.md)", "`plans/shiftwork/evidence/slice23-application-2026-10-07/`"),
    ):
        path = ROOT / relative
        original = (OUT / "preimages" / relative).read_bytes()
        assert path.read_bytes() == original
        path.write_bytes(prefix.replace("CHECKPOINT_LINK", link).replace("APPLICATION_ROOT", evidence).replace("\n", "\r\n").encode() + original)
    write("slice23-application-architecture-review-2026-10-07.md", """# S23 application architecture and preservation review

PASS within the authorized offline scope. Acceptance remains the user's decision.
This closing scan uses architect-reviewer in the current session, not an independent agent.

- The four production replacements match the approved proposals exactly. Runtime imports are unchanged across 43 parsed modules; 155 proof-source hashes bind the executed source.
- The existing orchestrator, evaluator, sealed loader, comparison and trusted-local executor boundaries remain in use. No new storage layer, dependency, UI or runtime architecture was introduced by application.
- The new demos/gtm_reviewed.py checker is referenced by admission tests and disposable fault helpers. It verifies immutable material, seals, catalog, documents and literal fixture pins; tests no longer invent seals or repin arbitrary candidate bytes.
- All 19 material files are bound by the registered inventory. The three paired public workloads and six protected family variants remain distinct. The retained comparison executes three shared protected variants across six slots, not all six variants in one comparison.
- All 106 fault controls retain distinct named assertions and exact restoration. The previous five rejected controls are history, not counted proof. No redundant test removal is justified.
- Keep the signed packet, superseded proposals, rejected logs, original failed preservation audit and draft review CLI as historical evidence. The old preflight build_packet.py still targets superseded pre-repair proposals; it is not an application helper. No historical file deletion is proposed.
- Latest notices supersede earlier draft-only status without rewriting their bytes. The unowned ignore rule and externally observed AGENTS.md change remain disclosed. Publication uses explicit paths rather than whole-tree staging.

Limits remain: trusted-local/fake assistance, no hostile isolation claim, no live CRM or provider call, no model or learning-quality proof, no fresh-checkout reproduction. Retry/budget growth belongs to later operational work; the live preflight's two-public-request assumption requires review before GTM's three-request live workload. S24/S25 remain outside this authorization.

Evidence: application.json, architecture-inventory.json, proof-source-bindings.json, production-audit.json, fault-audit.json and full-offline-verified-result.json beneath evidence/slice23-application-2026-10-07/.
""")
    write("slice23-application-checkpoint-2026-10-07.md", """# S23 applied packet and offline completion checkpoint

2026-10-07. Verdict: ready for the user's offline acceptance review. S23 remains unaccepted, unstaged and uncommitted; publication is unauthorized.

Branch shiftwork/slice-23; HEAD 3e02f1e5176cd34d6dc355bbc4529234fa51fe62.
Approved digest: 8d87c2dc279f31f3206ec389e0f72b34b50e038c59bc764ef60c13489b62d1fa.
The user authorized the unchanged application, offline proofs and publication inventory. Four replacements match approved bytes; 19 material pins, two seals, three document bindings and three literal offline fixture pins verify. Signed packet/proposals remain unchanged.

| Proof | Observed result |
|---|---|
| Final full offline suite | 1281 passed, 1 skipped, 2 warnings; exit 0; packaging excluded |
| Actual admission and legacy-byte preservation | 5 focused checks passed; real GTM admission and idempotent seeding |
| Production-reviewed offline comparison | 6 fair AB/BA/AB slots, 25 verified captures including starter; both candidates eligible |
| Starter incident | Owner and write tasks fail WRONG_ACTION |
| Business rows | Ledger events, incidents and operating selections unchanged during comparison |
| Assistance | Fake HINT then DIAGNOSIS; third call and PATCH_PROPOSAL refused |
| Fault controls | 106 rerun; 106 intended assertion failures; 0 setup errors; source restored exactly |
| Sentinel repair | 6 focused checks passed; original guard unchanged; duplicate own backup losslessly archived |
| Publication scope | Exact candidate paths and hashes; hidden 8 requests explicit; index untouched |

Raw evidence root: evidence/slice23-application-2026-10-07/. production-retained.db is independently audited read-only and bound to SHA256 f8f64acce9ee5a7c29b84b92ceda4f2076cb723dd4e80b653640a7673ab59194.
The first post-application full run had 1 failure, 1280 passes and 1 skip because an entry backup duplicated the sentinel test. Earlier transition failures are also retained and excluded from successful proof. The final passing suite follows the repairs; no failures are hidden or receipts overwritten.

The final preservation receipt verifies 5148 incoming evidence files, including all 4803 pre-S23 evidence files, and 42 prior reviewed material files. It checks current signed bytes, source bindings, index/HEAD/branch and publication filters. It discloses the externally observed AGENTS.md context-limit change rather than claiming whole-tree byte identity.
The incoming .gitignore remains byte-exact, with unverified ownership, and is excluded from publication. Eight ignored requests and ignored evidence require explicit path inclusion under a later Git authorization. The original failed whole-tree audit is retained as unresolved history.

Publication inventory: slice23-publication-inventory-2026-10-07.json. Its manifest and final-preservation.json are separately included to avoid a self-hash cycle. The final receipt records the manifest hash. Implementation, approved material/bindings, admission tests, evidence and closeout documents are separate proposed commit concerns.

Evidence is trusted-local/offline. The comparison covers three frozen protected variants, not all six in that run. No model-quality, CRM action, learner gain, production readiness or fresh-checkout claim follows. Live conformance remains skipped; packaging remains unrun. No live, credential, installation, spend, Git publication, S24 or S25 work occurred.

The historical packet/inventory still say NOT APPROVED and draft production status. Those signed bytes are intentional; separate authorization.json and application.json establish the actual later state. The draft-only review CLI and old pre-repair build_packet.py must not be used to regenerate this applied packet.
""")
    ranges = []
    entry = json.loads((OUT / "entry.json").read_bytes())
    tracked = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=ROOT).decode().splitlines()
    paths = [p for p in tracked if p not in {".gitignore", "AGENTS.md"}]
    paths += ["demos/gtm_reviewed.py", "tests/packs/gtm_material.py", "tests/packs/gtm_mutation_proofs.py", "tests/orchestrator/test_gtm_pipeline.py", "tests/orchestrator/test_gtm_guards.py", "demos/gtm_review.py"]
    for relative in sorted(set(paths)):
        current = (ROOT / relative).read_text().splitlines()
        backup = OUT / "preimages" / relative
        old = backup.read_text().splitlines() if backup.exists() else []
        spans = [[j1 + 1, max(j1 + 1, j2)] for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, current).get_opcodes() if tag != "equal"]
        ranges.append({"path": relative, "application_session_changed_ranges": spans,
                       "entry_bound": relative in entry["files"], "current_sha256": hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()})
    (OUT / "changed-lines.json").write_bytes((json.dumps(ranges, indent=2) + "\n").encode())
    files = "\n".join("- " + row["path"] + ": " + (", ".join(str(a) + "-" + str(b) for a, b in row["application_session_changed_ranges"]) or "incoming implementation unchanged this session") for row in ranges)
    write("slice23-application-handoff-2026-10-07.md", """# Session Transfer

## Completed

Exact approved application, reviewed-state admission/test transition, actual offline starter/comparison proof, 106 rerun fault controls and full suite: 1281 passed, 1 skipped, 2 warnings. Publication inventory and final preservation receipt bind the closing state.

## Decisions

Literal approved fixture pins replace dynamic test pinning. Disposable unreviewed declarations retain historical refusal checks. Explicit publication paths preserve the unowned ignore change without including it. The sentinel-bearing backup is losslessly archived; the original uniqueness guard stays unchanged.

## Traps

Old build_packet.py targets superseded pre-repair proposals; the draft-only gtm_review CLI is not the applied-state verifier. Historical NOT APPROVED packet labels are immutable history, superseded by separate receipts. Failed transition/full runs and five rejected historical controls are retained, not successful proof. Entry preimages are local backups, not a second source tree.

## Working Agreements

The user requested completion, then a handover, and reserved S23 acceptance for their own decision. The unchanged application was already approved; repeating approval is unnecessary. Publication and later slices remain unauthorized.

## Files Changed

Application-session ranges follow; incoming S23 implementation is identified explicitly. changed-lines.json retains current hashes. The publication inventory enumerates material, evidence and closeout documents separately.

""" + files + """

## Open Work

User acceptance and any later staging/commit/push authority remain pending. Fresh-checkout reproduction, packaging and live conformance are unrun. S24/S25 are unstarted. Ignore ownership and the old failed whole-tree audit remain unresolved history. An external AGENTS.md context threshold changed from 200k to 175k during this session; its origin is unverified, bytes untouched, excluded from publication and bound in unowned-agents-diff-confirmed.json. All recorded incoming evidence and prior reviewed material remain exact.

## Prompt for New Chat

Background handover for Shiftwork S23, 2026-10-07. Workspace C:\\Users\\jayd0\\OneDrive\\Desktop\\nebius_nvidia; branch shiftwork/slice-23; HEAD 3e02f1e5176cd34d6dc355bbc4529234fa51fe62. The user approved application and then authorized offline proofs and publication inventory. The unchanged digest 8d87c2dc279f31f3206ec389e0f72b34b50e038c59bc764ef60c13489b62d1fa is applied exactly. S23 remains unaccepted, unstaged and uncommitted.

The current checkpoint is docs/plans/shiftwork/slice23-application-checkpoint-2026-10-07.md; detailed handoff is slice23-application-handoff-2026-10-07.md. Raw application, authorization, logs, JUnit, production database, mutation and preservation receipts are in evidence/slice23-application-2026-10-07/. Final suite: 1281 passed, 1 skipped, 2 warnings, exit 0; packaging excluded. All 106 intended fault controls were rerun with zero setup errors and exact restoration. Actual reviewed admission, starter owner/write failure and six fair slots are verified offline: 25 captures, both candidates eligible, unchanged business rows, two fake assist roles. No live/model/CRM/learning-quality proof follows.

Publication inventory is slice23-publication-inventory-2026-10-07.json; final-preservation.json binds its hash. All 19 material files and eight hidden requests are explicit. Incoming .gitignore is exact and excluded. The externally observed AGENTS.md change is disclosed and excluded. All 5148 incoming evidence files, 4803 pre-S23 evidence files and 42 prior reviewed files are preserved. The old failed whole-tree audit remains unresolved history.

The signed packet/inventory retain historical draft labels. Separate receipts establish approval/application. Old pre-repair proposals and build_packet.py are superseded; gtm_review is draft-only and gtm_reviewed verifies applied state. Failed logs remain; the copied sentinel backup is losslessly archived. No process remains running. Git publication, live calls, credentials, installs, spending and S24/S25 remain unauthorized. Acceptance is reserved for the user.

Wait for instructions before taking any action.

## Prompt for Handoff Review

Independently and adversarially review the applied Shiftwork S23 offline work in C:\\Users\\jayd0\\OneDrive\\Desktop\\nebius_nvidia on shiftwork/slice-23 at HEAD 3e02f1e5176cd34d6dc355bbc4529234fa51fe62. Assume the work may be flawed. Be unbiased, thorough and honest; assess quality, shortcuts, scope creep and hidden assumptions. Do not pass tests for the sake of passing. Green output is not proof.

The claimed result is exact application of digest 8d87c2dc279f31f3206ec389e0f72b34b50e038c59bc764ef60c13489b62d1fa, strict reviewed-state tests, actual admission/starter/six-slot offline comparison, 106 intended assertion fault controls, 1281-pass full suite with one skip, preserved history and complete explicit publication inventory. No acceptance, publication or live execution is claimed. Relevant criteria are 04-slices.md S23 and its tests 16,17,20,23,39,40,55,57,60. Changed paths/ranges are in slice23-application-handoff-2026-10-07.md and evidence/slice23-application-2026-10-07/changed-lines.json; candidate hashes are in slice23-publication-inventory-2026-10-07.json.

Inspect actual diffs, all four approved replacements, 19 pins, two seals, three document bindings and three fixture pins. Rerun appropriate offline checks with .venv313/Scripts/python.exe, excluding packaging. Verify fault controls genuinely catch their intended branches with zero setup errors and exact restoration; probe edge cases without changing signed material or historical evidence. Check the retained SQLite database independently, shared snapshots/AB-BA-AB fairness, both eligibility outcomes, unchanged business rows, assist refusals, privacy/scanner positive controls and legacy-byte preservation. Check receipt/hash and publication completeness, including eight ignored requests and exclusion of unowned .gitignore/AGENTS changes. Flag any trivially satisfied, weakened or unverified claim. Retain failures honestly. No live calls, installations, credentials, spending or Git writes are authorized.

Report PASS / ISSUES FOUND / FAIL with concrete file/line evidence, command outputs, limitations and acceptance implications. Deliver your verdict and wait for instructions.
""")
    print(json.dumps({"docs_written": 3, "status_and_brief_prepended": True, "final_suite_passed": passed}))


if __name__ == "__main__":
    main()
