# S22b pilot and handover offline checkpoint

Verified 2026-10-05 Asia/Singapore. Work began 2026-10-04 under the existing
S22b go-ahead and approved Gate 3 design. This closes the bounded offline
pilot/rollout and handover proof. S22b remains incomplete, unaccepted,
uncommitted and unpublished.

## What is established

- The real HTTP/LocalProcessAdapter journey uses the owning Northline material,
  six qualifying slots, exact explicit choice and selected next-shift operation.
  A failed blank starter records an incident with no pilot state. The successful
  reviewed pilot records BOOKING_COMMITTED and exactly one ROLLOUT_APPROVED;
  its original incident resolves separately. Events are synthetic.
- Operational consequence rules are retained in the existing hashed frozen
  context. Weights come from retained mission bytes. Semantic replay reads no
  current pack/fixture replacements, includes the pilot event types and writes
  no rows. Historical operation-ledger-v1 contexts retain their prior behavior.
- Pure acceptance controls refuse partial pilot state on failed summary flags,
  incomplete counts, failed/missing/duplicate checks, incomplete/misowned task
  rows, a justified fallback instead of required completion, and mandatory
  required or optional task failure. Every check and required completion gates
  the rollout arm; a failed required task/check still produces an incident.
- A real public safety-route capture reduces to escalation rather than booking
  in a pure control. A separate real trusted-local comparison/choice/operation
  executes provisional write, same-request rollback and final confirmation;
  reduction records COUNTER_FOLLOWUP_RECORDED rather than a missed commitment.
- Close refuses absent, empty or whitespace-only selected runbook content. It
  records one HANDOVER_DECLARED with the exact selected version, declared limits,
  unresolved incident IDs and owning mission version. A newer saved version
  cannot replace that reference. Inherited CLOSED_UNRESOLVED incidents remain
  in subsequent handovers; a repeated close adds nothing.
- Six operation-finalization and three close write-boundary faults roll back
  checks, assessments, incident changes, events and close state as applicable.
  A later executed alternative diagnostic preserves pilot, handover and choice
  history. Separate deliberate rollout and handover rewrites fail its assertion.

## Verification and falsifiers

| Receipt | Result |
| --- | --- |
| Existing operation/close/FDE/replay/ledger baseline | 115 passed |
| Pre-change new HTTP checks | 5 intended failures |
| Final focused FDE plus existing atomic controls | 75 passed, 38 deselected, 2 warnings |
| Final full offline | 1050 passed, 1 skipped, 2 warnings, exit 0, 434.40 seconds |
| Separate counted clean/fault source pairs | 32 intended assertion failures; zero setup errors; exact restoration |
| Real HTTP demo | Booking and one rollout, handover, IDENTICAL replay, VALID chain |

The source controls cover aggregate acceptance, check and task inventory,
ownership/usefulness, partial-success and rollout gates, booking/safety/follow-up
classification, required runbook/handover, inherited unresolved incidents,
frozen rules/hash, replay event types, nine transaction boundaries and two
later-history rewrites. Task-coverage policy holds the independent usefulness
guard fixed; the missing-check policy preserves required provenance and removes
an optional check. Those controls isolate the claimed guard rather than credit
an independent lookup or reader for catching its omission.

The earlier missing-check mutation raised KeyError at a later source lookup and
was rejected. Its raw streams, XML and original harness remain. Earlier safety
provenance and HTTP-contract test errors, a demo import failure, and the first
full suite's old forwarding-wrapper TypeError remain retained. The wrapper now
forwards keywords to the real reducer; its injected fault and rollback
assertions are unchanged. The final suite covers that repair.

Raw evidence: `evidence/slice22b-pilot-2026-10-04/`. Start with `summary.json`,
`final-focused.log/xml`, `full-offline-final.log/xml`, `mutations-final/results.json`,
`history-write-controls/results.json`, `pilot-receipt.json` and
`final-preservation.json`. Old evidence helpers/publication scripts were not rerun.

Full command:

```text
.venv313/Scripts/python.exe -m pytest tests --ignore=tests/packaging -q --tb=short
```

## Preservation and limits

All 42 reviewed pins, the exact 18847-byte v2 packet/seal, v1 and original
Northline pins remain exact. All 2964 prior evidence files captured on entry
are preserved. AGENTS.md is unchanged, MISTAKES.md retains its entry prefix,
the index is empty, and HEAD/main/origin/main remain
`157505ecd2f04ddc3fc86c0593771043af0d8325`. Diff check passes.

Runtime changes are limited to `domain/models.py`, `ledger/reducer.py` and
`orchestrator.py`; existing dirty work elsewhere is preserved. Tests changed
in `test_fde_deployment.py` and the two-line forwarding wrapper in
`test_selection_operation.py`. Planning notices, the new plan/checkpoint and
append-only mistake entries accompany the raw receipts.

The reviewed operational batch contains one booking request. The safety
classification control uses an experimental capture in memory, and the
counter-follow-up service/pins are test-only. These do not add reviewed pilot
workloads, production reference repairs or evidence that a customer-declared
prior reference corresponds to an earlier executed booking. Pure two-request
acceptance controls are synthetic reducer inputs, not new sealed material.

This is TRUSTED_LOCAL evidence. Inference tokens are zero; monetary cost is
unknown. It proves no live isolation, model quality, real booking or learning.
No live calls, credential use, install, runtime publication or later slice ran.

## Next work

Workplace selection, native six-station Northline UI, desktop/390px mobile
journey, served-source value faults and final architect cleanup remain.
Whole-slice verification, a concrete bounded live packet and separately
authorized live proof remain. Executed isolated v5 bootstrap is still unproved.
Gate 3 and exact operator v2 approvals remain granted and need no repeat approval.

Continue on `shiftwork/slice-22b` in
`C:\Users\jayd0\OneDrive\Desktop\nebius_nvidia`. Preserve all dirty runtime
and raw evidence. Evidence demos with fixed database paths are one-shot;
use a fresh destination. Preview configuration is SHIFTWORK_DB_PATH.
