# S46 second action: proposal workflow passed; comparison incomplete

Status: STOPPED, INCOMPLETE and UNACCEPTED, 2026-10-25 Asia/Singapore.
The user approved the second action with "i approve2". It has now stopped and
its allowance, including unsent remainders, is CLOSED. No retry or resume follows.

## Verified result

Nemotron 3 Super returned a valid exact replacement patch. The response reported
the requested Super model, 697 input tokens and 734 output tokens. The observer
recorded HTTP 200, a stop finish reason, 146 content bytes and 2,817 reasoning
characters. These counts do not identify reasoning-token usage or actual billing.
The first action's invalid-reply cause remains unknown.

The patch changes:

```python
return reply.get("plan"), reply.get("plan_failure")
```

to:

```python
return reply.get("plan") or [], reply.get("plan_failure")
```

The caller already iterates `plan or []`. Static inspection therefore indicates
no customer-facing repair: an absent plan becomes an empty list earlier, and a
service-reported trace can differ. No equivalence execution of coach code was
performed on the host. The isolated diagnostic passing does not prove this patch
fixed the source failure, and comparison variation cannot establish that claim.

The exact retained proposal ran once as a DIAGNOSTIC, under Token Factory, against
the one public customer request. Its collection and alternative mandatory tasks
passed. It remained ineligible and reserved no protected cases.

Operator-demo acceptance copied the proposal into the draft without creating a
version. A separate explicit save created B, ver-0004, with one generated patch
seen and accepted, learner_edited=false and the operator's generated-use
declaration true. This was not learner work or a learning study.

Proposal source SHA-256:
`87c0a0b42851b75654820ca45bca15c8159d994114775cc061055a01b583ea59`.
B artifact hash:
`667d50c2384a1f0d7b136d1c48d540474f2d1206503ce2e977e288de3706ebc6`.
Its store is `/tmp/shiftwork-s46-20261025/proposed-live-v2/live.db`.
IDs in this store do not join histories in the first action or S45 stores.

## Comparison stop

The comparison is FAILED with an INCOMPLETE outcome. Both candidates have zero
passing public batches out of nine planned, with three retained each. Neither is
eligible. The six unretained planned batches per candidate are missing evidence,
not six measured failures.

The read-only reconciliation identifies run-0017 as B, pair 1, public repetition
3. Its second request records PROVIDER_TRANSPORT_FAILED, category `deadline`,
at 20,004 ms. The underlying latency cause is unknown. The Sandbox reported
SUCCESS and both captures passed checkpoint readback. SANDBOX_TERMINATED is the
adapter's gateway-failure label, not proof of a Sandbox infrastructure defect.

Run-0015's public repetition completed. It also parents B's protected phase,
which was skipped after run-0017 failed. Its later CAPTURE_TRUNCATED label records
that absent protected capture, not a second failed public execution. Twelve later
runs remain QUEUED without outputs or observations. The retained sequence supports
stopping at the first actual execution failure; earlier mandatory-check failures
are permitted retained evidence under the approved wording. No retry or new live
execution followed. Normal startup must not reconcile the original evidence store.

## Usage and preservation

- This action used one Super call, 14 Nano calls and eight Sandbox operations.
- Reserved inference is US$0.04171776. Combined with the first action, S46's
  reservations total US$0.05468160. Neither amount is a bill.
- The operational ledger and selection rows were unchanged. No operating choice
  or operation followed.
- Both stopped database snapshots are byte-preserved. All 106 protected-material
  and 66 older-evidence hashes still match.
- Offline implementation proof remains the previous 1,761 Python passes, one
  live-only skip, one excluded installation test, 312 Node passes and final 22
  source-fault checks across 21 distinct edits. Product source did not change in
  this approved execution turn. No new full regression was needed or claimed.

Private receipts and snapshots are in the action directory. The comparison view
was recovered read-only to `public-comparison-recovered.json` there. The subsequent
private scan passed for the five named export files against actual credential
values, with all 30 serialized detection controls firing. Receipt:
`/tmp/shiftwork-s46-readonly-20261025/credential-scan.json`. No second-action public
JSON was exported or published. The scan excludes browser screenshots.

The subsequent review inspected generated, tested, accepted and stopped checkpoint
copies. The misleading proposal summary was corrected offline using exact diagnostic
identity and evidence. Desktop and mobile-sized Chrome viewports pass at native
100% and 200%; the 390px target at 200% has 195 CSS pixels, DPR 2 and pinch scale 1.
The separate snapshots do not prove a smooth end-to-end browser journey. The
later authorized fix suppresses polling a queued child of an exactly matched
stopped qualifying comparison, and its lamp now follows the parent state. The
stopped result stays loaded at desktop/mobile-sized native 100%/200%; all queued
rows remain unchanged. See [the polling record](slice46-polling-correction-2026-10-25.md)
and [the summary record](slice46-ui-correction-2026-10-25.md) for verification,
receipts and remaining limits. Port 8466 is the first
failed action and remains unsuitable as evidence of this result.

## Earlier session boundary

The latest available runtime usage receipt reports 432,496 context input tokens,
above the user's 175k working limit. The session stops after recording this result.
That session stopped without further diagnosis or repair. The later authorized
offline correction and reconciliation are recorded above and in
[the current continuation](slice46-continuation-2026-10-25.md). Both live allowances
stay closed. S46 remains INCOMPLETE and UNACCEPTED.
