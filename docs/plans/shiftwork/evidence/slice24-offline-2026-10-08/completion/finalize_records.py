"""Prepend the measured completion state while retaining all historical bytes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
heading = "**S24 OFFLINE IMPLEMENTATION AND PROOFS COMPLETE; ACCEPTANCE PENDING, 2026-10-08 Asia/Singapore.**"
summary = """

The remaining offline evidence is complete: final implementation-tree regression
passed 1,340 tests, with one live-only skip and two existing warnings. All 55 S24
and 106 refreshed S23 controls reached their intended named assertions, with zero
setup errors. All 6,214 files in the disposable physical copy remain exact after
both runs. No source fault ran in the shared OneDrive tree this continuation.

The retained shipped-material API journey demonstrates exact selection, operation,
restart, idempotent reprocessing, six later-condition slots and IDENTICAL replay.
A separate human-review controller proof uses a consistent disposable operator
mission/state; it is not additional production material approval. Reviewed GTM
material, seals and pins still verify. Architecture cleanup proposes no deletion.

S24 remains unaccepted, unstaged and uncommitted. Packaging remains excluded.
No installs, credentials, live calls, spending, publication or S25 were authorized
or performed. Nothing from this continuation remains running. Earlier notices
below retain historical bytes and are superseded only for current completion state.

"""
bindings = {}
for name, link in (
    ("docs/plans/shiftwork/00-status.md", "slice24-offline-checkpoint-2026-10-08.md"),
    ("docs/SHIFTWORK_PLAN.md", "plans/shiftwork/slice24-offline-checkpoint-2026-10-08.md"),
):
    path = ROOT / name
    raw = path.read_bytes()
    assert heading.encode() not in raw
    notice = (heading + summary + "Current checkpoint: [S24 offline result](" + link + ").\n\n").encode()
    path.write_bytes(notice + raw)
    assert path.read_bytes() == notice + raw
    bindings[name] = {"historical_bytes": len(raw), "historical_sha256": hashlib.sha256(raw).hexdigest(),
                      "prefix_bytes": len(notice)}

path = ROOT / "MISTAKES.md"
raw = path.read_bytes()
entry = b"""\n\n## 2026-10-08 S24 evidence audit launch syntax

- **What happened:** python -m runpy was given a filesystem path, so it rejected
  module resolution before the read-only demo audit ran. The corrected
  runpy.run_path invocation audited both retained databases successfully.
- **Root cause:** runpy's module CLI was confused with its filesystem-path API.
- **Prevention rule:** execute a saved script directly when it has no root imports;
  for repository imports use python -c with runpy.run_path and run_name=__main__.
  Do not pass a filesystem path to python -m runpy.
"""
assert b"## 2026-10-08 S24 evidence audit launch syntax" not in raw
path.write_bytes(raw + entry)
assert path.read_bytes() == raw + entry
bindings["MISTAKES.md"] = {"historical_bytes": len(raw), "historical_sha256": hashlib.sha256(raw).hexdigest(),
                           "append_bytes": len(entry)}
destination = OUT / "closing-document-bindings.json"
assert not destination.exists()
destination.write_bytes((json.dumps(bindings, indent=2) + "\n").encode())
print("Current completion notices written; prior document and log bytes exact")
