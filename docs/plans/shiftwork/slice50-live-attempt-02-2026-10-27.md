# S50 live attempt 02: provider transport failure at first inference

S50 remains incomplete. The second authorized live attempt stopped on a provider
transport error before any model output was retained. It is a different failure
from attempt 01, which stopped because the model produced no mandatory failure.

## What ran

- Fresh v7 control kit at
  `/Users/jayd0/Documents/Codex/2026-10-27/shiftwork-s50-session-controls-v7`,
  deployed through `deploy-03` on the separate Free service
  `srv-dbg6h9mc6qcc73eggr20`.
- New boot `040af851-dae6-4e6b-9214-2380d1c7ee3f`, origin
  `https://shiftwork-s50-recording-20261027.onrender.com`.
- The freeze-starter contract fix landed: catalog version 3, hash
  `d9f18ddafd0cd7f791bd13b58b72b165954c1c51df824c96127ad4796bf7736a`.
- Diagnostic reserved 5 repetitions, 5 inference and 5 spawn attempts, under the
  retained 44/26 ceilings.

## What failed

- Repetition 1 uploaded 3 files, bound 1 Sandbox spawn, polled events 3 times and
  reserved 1 inference call, then the transport closed with
  `UPSTREAM_TRANSPORT_FAILED` and the operation was cancelled and acknowledged.
- Runs 0001 to 0005 are `FAILED` (`PROVISION_FAILED` then `INTERNAL`). The
  diagnostic experiment is `FAILED`, not `FINALIZED`.
- No `INFERENCE_RESULT` observations exist, so no model plan or output was
  retained. All task rows are `MISSING_OUTPUT` because nothing ran.
- The recording verifier requires a `FINALIZED` experiment, so the host stopped
  with `MUTATION_FAILED` and the controller closed at 2 completed steps.
- This is the same failure class as the S45 five-call probe stop
  (`PROVIDER_TRANSPORT_FAILED`). It is a provider or network transport failure,
  not a model miss and not a no-miss outcome.

## Preserved evidence and closures

- Terminal export retained, 51,300 bytes, SHA-256
  `ac51f2dcba66b979456e21c202dbb37b2fe3435389bde226d00646bec47708ef`.
- Capture bridge PASS with 75 frames.
- New one-use marker
  `/Users/jayd0/Documents/Codex/2026-10-27/shiftwork-s50-live-once-20261028-v7`
  is consumed. The old marker and the old attempt folders remain untouched.
- Zero ledger events; only the `STARTER_BASELINE` selection exists.
- Unused allowance closed; no retry, fallback, coach or replacement ran.
- Raw receipts remain in the external kit under `live-original-01`.

## Consequence

A retest needs a fresh deployment cycle, a fresh one-use marker and a fresh
explicit approval, because the current host transport is closed and cannot
re-arm. The transport failure is not fixable offline; a rerun may hit it again.
S50 stays incomplete until a run retains an actual model result.
