"""Append this continuation's measured proof errors without rewriting history."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
entry = b"""\n\n## 2026-10-08 S24 completion review-probe setup contracts

- **What happened:** the extra retained human-review probe first failed collection
  because its evidence-folder launch did not load the tests directory import path.
  The next run failed with AttributeError because the stored operation draft helper
  returns serialized dictionaries, not LedgerEventDraft models. Both rejected logs,
  JUnit and lossless source preimages remain in completion/. Neither is behavioral proof.
- **Root cause:** the external proof reused a test module without its collection
  context and guessed an internal helper return shape instead of inspecting it.
- **Prevention rule:** inspect the imported module's prerequisites and the helper's
  current return contract before launching a nested proof. Use serialized keys when
  the stored-event helper returns dictionaries. The existing graduated call-contract
  rule applies; no additional duplicate AGENTS.md rule is needed.

## 2026-10-08 S24 completion review-probe changed only state

- **What happened:** after setup repair, lowering a public signal's confidence to
  50 produced one traced incident rather than the three expected success events.
  The shipped operation spec allows QUALIFIED only, so the independent assessor
  correctly rejected REVIEW. queue-corrected.log/xml and its source preimage remain.
- **Root cause:** the probe changed the observation without binding a matching
  operator workload before comparison and selection. This was a false positive
  test premise, not an observed product defect.
- **Prevention rule:** for a positive synthetic operator scenario, bind its complete
  mission before selecting, then retain the same observation across reprocessing.
  Keep production reviewed material and pins exact. Report this path as disposable
  operator mission/state proof, separately from the shipped-material API demo.
"""
path = ROOT / "MISTAKES.md"
raw = path.read_bytes()
assert b"## 2026-10-08 S24 completion review-probe setup contracts" not in raw
path.write_bytes(raw + entry)
assert path.read_bytes() == raw + entry
print("Appended two proof-premise entries; prior bytes exact")
