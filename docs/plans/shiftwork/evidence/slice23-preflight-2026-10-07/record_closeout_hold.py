"""Record the unexpected preservation hold without changing product files."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
DOCS = ROOT / "docs/plans/shiftwork"

entry = json.loads((OUT / "entry.json").read_bytes())
ignore_bytes = (ROOT / ".gitignore").read_bytes()
hold = {
    "status": "BLOCKED",
    "phase": "post-document preservation audit",
    "audit_exit_code": 1,
    "reason": "unexpected tracked .gitignore change outside the audit allowed set",
    "observed_addition": "/shiftwork/fixtures/requests/",
    "ownership": "unverified; left untouched",
    "gitignore_entry_sha256": entry["tracked"][".gitignore"],
    "gitignore_current_sha256": hashlib.sha256(ignore_bytes).hexdigest(),
    "last_completed_preservation_receipt": "final-preservation.json",
    "last_completed_receipt_scope": "before closeout documentation changes",
    "final_preservation_pass_claimed": False,
    "pytest_processes_running": False,
    "repair_applied": False,
}
with (OUT / "post-document-preservation-blocked.json").open("xb") as stream:
    stream.write((json.dumps(hold, indent=2) + "\n").encode())

notice = (
    "**FINAL CLOSEOUT HOLD, 2026-10-07.**\n\n"
    "The post-document preservation audit exited 1 on an unexpected `.gitignore`\n"
    "addition: `/shiftwork/fixtures/requests/`. Its ownership is unverified; it was\n"
    "left untouched. This rule hides new request drafts from ordinary git status.\n"
    "`final-preservation.json` is the last successful pre-document audit, not a\n"
    "final-state PASS. `post-document-preservation-blocked.json` supersedes any\n"
    "final-state preservation claim below. No repair or further phase followed.\n\n"
)
for relative in (
    "docs/SHIFTWORK_PLAN.md",
    "docs/plans/shiftwork/00-status.md",
    "docs/plans/shiftwork/slice23-offline-checkpoint-2026-10-07.md",
    "docs/plans/shiftwork/slice23-handoff-2026-10-07.md",
    "docs/plans/shiftwork/slice23-gtm-operator-review-packet.md",
    "docs/plans/shiftwork/slice23-architecture-review-2026-10-07.md",
):
    path = ROOT / relative
    raw = path.read_bytes()
    if path.name == "slice23-handoff-2026-10-07.md":
        old = b"All changes are S23 session work, unstaged/uncommitted. No test process remains running."
        assert raw.count(old) == 1
        raw = raw.replace(old, (
            "Known implementation changes are S23 session work, unstaged/uncommitted. "
            "An unexpected .gitignore addition /shiftwork/fixtures/requests/ has unverified ownership "
            "and was left untouched; it hides new request drafts from ordinary git status. "
            "No test process remains running."
        ).encode())
        old = b"The exact final audit is final-preservation.json in docs/plans/shiftwork/evidence/slice23-preflight-2026-10-07."
        assert raw.count(old) == 1
        raw = raw.replace(old, (
            "The last successful audit, before closeout documentation, is final-preservation.json "
            "in docs/plans/shiftwork/evidence/slice23-preflight-2026-10-07. The post-document audit "
            "exited 1 because of that unexpected .gitignore change; post-document-preservation-blocked.json "
            "records the hold. Final-state preservation is not claimed."
        ).encode())
        marker = b"## Files\n\n"
        assert raw.count(marker) == 1
        line_count = len(ignore_bytes.splitlines())
        raw = raw.replace(marker, marker + (
            f"- `.gitignore:1-{line_count}`: unexpected addition ignores the request fixture directory; ownership unverified and unchanged by closeout.\n"
        ).encode())
        old = b"Audit final-preservation.json against entry.json and the named log/JUnit hashes."
        assert raw.count(old) == 1
        raw = raw.replace(old, b"Audit the pre-document final-preservation.json against entry.json and the named log/JUnit hashes, and inspect post-document-preservation-blocked.json plus the unexpected .gitignore change. Final-state preservation is unverified.")
    path.write_bytes(notice.encode() + raw)

path = ROOT / "MISTAKES.md"
incident = (
    "\r\n\r\n## 2026-10-07 S23 final preservation audit stopped on unexpected ignore change\r\n\r\n"
    "- **What happened:** the post-document audit exited 1 because .gitignore contained a new /shiftwork/fixtures/requests/ rule outside the allowed tracked changes. It also hides new request drafts from ordinary git status.\r\n"
    "- **Root cause:** ownership and origin are unverified. The prior successful audit predates this observed change and closeout documentation.\r\n"
    "- **Prevention rule:** leave the unexpected change untouched, retain the blocked receipt and do not present the prior audit as final-state PASS. Resolve attribution and inventory completeness in a fresh authorized session.\r\n"
)
path.write_bytes(path.read_bytes() + incident.encode())
path = OUT / "handoff-result.json"
result = json.loads(path.read_bytes())
result.update({"post_document_preservation": "BLOCKED", "unexpected_gitignore_change_ownership": "unverified", "final_state_preservation_pass": False})
path.write_bytes((json.dumps(result, indent=2) + "\n").encode())
print(json.dumps(hold))
