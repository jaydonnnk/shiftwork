"""Prepare a new preservation receipt destination without rewriting old evidence."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
source = OUT.parent / "continuation/audit.py"
raw = source.read_bytes()
old = b'OUT = ROOT / "docs/plans/shiftwork/evidence/slice24-offline-2026-10-08/continuation"'
new = b'OUT = ROOT / "docs/plans/shiftwork/evidence/slice24-offline-2026-10-08/completion"'
read = b'INCOMING = json.loads((OUT / "entry.json").read_bytes())'
replacement = b'INCOMING = json.loads((OUT.parent / "continuation/entry.json").read_bytes())'
assert raw.count(old) == raw.count(read) == 1
destination = OUT / "audit_preservation.py"
assert not destination.exists()
destination.write_bytes(raw.replace(old, new, 1).replace(read, replacement, 1))
assert source.read_bytes() == raw
(OUT / "preservation-launch-stall.json").write_bytes((json.dumps({
    "status": "STALLED_PREPARATION_TERMINATED",
    "process_id": 31948,
    "observation": "Zero reported CPU and no destination file; no audit executed.",
    "cause": "UNCONFIRMED",
    "recovery": "Only the task-owned stalled launcher was stopped; preparation moved to this saved script."
}, indent=2) + "\n").encode())
print("New preservation audit prepared; historical audit bytes retained")
