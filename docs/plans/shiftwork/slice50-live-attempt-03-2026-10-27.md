# S50 live attempt 03: one clean pass, then provider transport failure

S50 remains incomplete. Attempt 03 ran on a fresh host process with the deployed
v7 overlay. Repetition 1 of the 5-repetition diagnostic completed and passed;
repetition 2's single inference call then closed the transport with
`UPSTREAM_TRANSPORT_FAILED`, so the experiment never finalized and the recording
verifier stopped the chain at two completed steps.

## Repetition 1, the only retained model result

- Plan: `collection` plus `alternative`, `plan_failure` null, `finish_reason`
  stop, 887 output tokens.
- Collection and alternative both `USEFUL_COMPLETION`, mandatory pass.
- Price optional `MISSING_OUTPUT`, not a mandatory failure.
- No mandatory failure, so this repetition is another pass on the frozen easy
  request. Combined with attempt 01, completed live repetitions of this request
  have passed 2 of 2. The S44-era 5-of-10 truncation rate did not reproduce.

## Repetition 2 and closure

- One Sandbox spawn bound, then the second inference reservation closed the gate
  with `UPSTREAM_TRANSPORT_FAILED`; the operation was cancelled and acknowledged.
- Runs 0002 to 0005 are `FAILED`; the diagnostic experiment is `FAILED`, not
  `FINALIZED`. The verifier requires a finalized experiment, so the host stopped
  and the controller closed at two steps.
- Two spawns and two inference reservations were used of the 44/26 ceilings.
- Terminal export retained, 58,354 bytes, SHA-256
  `9fdc4f78825b5cf04bc5e327de57d3bb33c4ee43aaf7ba8f19da4bb2e87ed772`.
- Capture bridge retained 84 frames.
- Marker `shiftwork-s50-live-once-attempt-03` consumed; unused allowance closed;
  no retry, fallback, coach or replacement ran. Zero ledger events.

## Interpretation

Two independent blockers now stand between S50 and a complete chain:

1. The frozen easy request has not produced an observed miss in any completed
   live repetition, so repetition alone is unlikely to supply one.
2. Render-to-Nebius inference transport failed on two of three attempts, at call
   1 and call 2. This is an egress or provider reliability problem, not a
   product or control-kit defect. Earlier successful live runs were launched
   locally, not from Render.

Further attempts from this host are a gamble on both fronts. The honest route to
submission now is the retained public demo and S45/S44 evidence with S50 labelled
incomplete. Completing S50 later needs a harder operator-reviewed request shape
under a scoped Gate 3 amendment and a more reliable egress, each separately
approved.
