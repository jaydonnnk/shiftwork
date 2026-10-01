# S20 stretch decision and SSE recovery: 2026-10-01

The user delegated the pending A/B/C decision in chat: "for the pending decision
i give u autonomy to decide". Decision A is selected: repair the known adapter
failure offline, then execute one fresh linked live attempt after verification
and a same-day preflight. Retrying unchanged leaves a known transport defect;
dropping the stretch now would end it before its 2026-10-20 drop point despite
a bounded repair being available. This does not accept S20, authorize a later
slice, or authorize commits or pushes.

## Boundaries

- One fresh chain only, under `artifacts/slice20-live-chain-resume-2026-10-01/`.
  Its marker is created exclusively before Phase A. The failed first attempt,
  its database, marker and every prior evidence file remain intact.
- Existing caps: comparison 12 Sandbox operations and 18 inference attempts;
  selected operation 1 Sandbox operation and 1 inference attempt. Worst-case
  inference reservation is USD 0.03981312 + 0.00221184 = 0.04202496.
- Reconnecting an event stream continues the same operation. It never respawns,
  retries a provider request or resets any budget. Three reconnects per operation,
  with 0.25/0.5/1 second backoff, remain inside the original run deadline.
- Stop and record any nontrivial live failure. No further chain run is authorized
  by this decision. No failed historical row may be reconciled by editing it.

## Mechanism and repair

The pinned `contree-client[httpx]==0.4.0` decoder raises builtin ConnectionError
with `last_event_id` metadata for its `sse_error` frame. Both sync and async
`follow_operation_events` provide reconnection; the handoff's sync-only claim
was incorrect. The adapter uses non-follow polling so it can deliver inference
and next-request replies between polls. The repair retains that flow and catches
only the decoder's metadata-bearing ConnectionError in the event iterator.

Events yielded before an error are processed before reconnecting. The next poll
uses the last processed event ID, and duplicate event IDs are ignored. Split
stdout lines survive the reconnect. A received completion event proceeds to
status and verified checkpoint readback. A blocked poll is cancelled at the
existing deadline; repeated SSE failures exhaust the reconnect allowance and
cancel the same operation.

All failure returns flush pending gateway observations, once per gateway. Error
messages are bounded to 512 characters in internal raw observations, after
redacting the configured token and project. Public projections contain only
allowlisted flags/type names. No Sandbox status or stdout claim substitutes for
byte-count and SHA256 checkpoint readback.

## Current preflight sources

The rendered public [exact model card](https://tokenfactory.nebius.com/models/catalog/text2text/nvidia%2FNVIDIA-Nemotron-3-Nano-30B-A3B)
was checked in the in-app browser on 2026-10-01. Its public
endpoint lists USD 0.06 per million input tokens and USD 0.24 per million output
tokens, matching the runner. The rendered [Sandbox beta notice](https://tokenfactory.nebius.com/sandboxes/about)
states that beta runs do not consume credits. No login, provider request or
Sandbox operation was used for those read-only checks.

## Offline proof and live result

- Pre-change nearest suite: 35 passed in 5.01s. The added fault tests then
  measured five failures and one preservation pass against the broken adapter.
  The stalled fixture was subsequently corrected to yield a real terminal event.
- Repaired focused suite: 42 passed in 7.81s, including seven new cases. The
  recovery cases cover a break before the first event, after an inference event,
  and inside a split stdout line; they require exactly one spawn/provider call/
  stdin reply and successful verified capture readback.
- Targeted mutation proof: 11/11 FAIL_CAUGHT, exit 0, source restored with
  before/after SHA256 `3ea43335556925b0dda35053c837e14a4bc6f3a6d49b69f2d70cf59c273ca2e5`.
  Full injected patches, named tests and assertion output are preserved in
  `slice20-sse-mutation-round2-2026-10-01.txt`. The aborted first round caught
  one row then stopped on a CRLF anchor mismatch; its partial output and
  verified restore remain in `slice20-sse-mutation-2026-10-01.txt`.
- Full offline command: `.venv313/Scripts/python.exe -m pytest tests
  --ignore=tests/packaging -q`, exit 0: 643 passed, 1 skipped, 2 existing
  deprecation warnings in 312.20s. Evidence:
  `slice20-sse-full-suite-2026-10-01.txt`. Packaging remains excluded because it
  performs install/network behavior; no dependencies were installed.
- `python -m demos.final_pivot --stage inheritance` exited 0 with
  PASS_OFFLINE_POLICY. Its JSON stdout line is byte-identical to the previous
  record with SHA256 `82c64ef9e335ebe57039f43423533bfc7187ce8edc9ee4badaa5e8dd3ebef651`.
  Evidence: `slice20-sse-inheritance-demo-2026-10-01.txt`. The initial wrapper
  compared that line with the full historical evidence note and exited 1;
  the corrected check extracted both JSON lines and confirmed identity.
- Fresh `--preflight-only`: PASS, exit 0, both meters zero, exact model and
  candidate/sealed hashes match, credentials available without values being
  emitted, new marker absent. Evidence:
  `slice20-sse-live-preflight-2026-10-01.txt`.
- Preservation baseline hashes 35 files from the first run directory and its
  prior chain, stretch and post-change evidence:
  `slice20-sse-preservation-before-2026-10-01.json`.
- The prior six-harness 232-row round is historical evidence. It was not rerun:
  this patch changes no old mutation anchor; the new 11-row round targets the
  SSE repair directly, and the full suite covers the affected existing tests.
- The fresh live attempt completed; its result and read-only audit follow.

## Live result and stored-record verification

**VERIFIED_LINKED_LIVE_CHAIN.** The runner exited 0 with CHAIN_COMPLETE, from
2026-10-01 15:55:08 to 15:56:56 UTC. Stored-record verification completed on
2026-10-02 in Asia/Singapore; evidence filenames retain the UTC attempt date.

| Link | Stored result |
| --- | --- |
| Qualifying comparison | `experiment-bookshop-shift-01-c1`, FINALIZED / COMPLETE; all six slots `run-0002` through `run-0007` COMPLETE; both candidates eligible |
| Explicit selection | `sel-0002` selects `ver-0003`, retains `ver-0004`; selected artifact hash recomputed as `fad72798c92b2b483084b08fb13bbbea72c8ea19d6e4f5de91b897042f9a0dfd` |
| Selected operation | `run-0008`, same version and selection, FINALIZED / ISOLATED_LIVE, three checks passed |
| Checked synthetic consequence | Sale seq 5, synthetic=true, cause refs `run-0008`, `cr-0006`, `run-0008-out-1`; hash `e1d4f3117777d3c0361cecbb0ea5d775f515bce0eaa93d5435bca57425a443d2` |
| Inheritance | `bookshop-shift-03` draft equals the selected artifact files; sale remains in the VALID hash chain |
| Experiment/history separation | No comparison run ID occurs in a business event's cause refs |

One genuine SSE error occurred in the selected operation (`run-0008-obs-2`),
with last event ID 3. The adapter resumed the same operation and finalized it;
one checkpoint readback passed for that operation. The retained internal
diagnostic is 40 characters. The audit records its digest without reproducing
the server text in a repository note.

- Sandbox operation attempts: comparison 12 of 12, selected operation 1 of 1.
- Inference attempts/results: comparison 9, operation 1; all 10 persisted,
  successful, `public_record_lookup`, with stop finish reasons. B uses ordinary
  code and makes no inference call.
- Verified checkpoint readbacks: 19 across comparison and selected operation.
- Recorded tokens: 968 input, 1451 output. Their calculation at the checked
  rates is USD 0.00040632. This is not a provider billing receipt. Reserved
  projection usage is USD 0.01990656 + 0.00221184 = 0.02211840, below the
  combined 0.04202496 ceiling. Sandbox beta runs do not consume credits under
  the observed notice; new checkpoint images were not separately enumerated.
- All 35 baseline file hashes remain unchanged, including the failed first
  database, marker and every earlier chain/stretch/post-change evidence file.
- Live database SHA256 after read-only verification:
  `cc3e36f12cc205b83fc8bdd076f53c6b21df4330e404e182b7fe6d992b8f0691`.

Receipts: `slice20-sse-live-2026-10-01.txt`,
`slice20-sse-live-summary-2026-10-01.json`,
`slice20-sse-live-audit-2026-10-01.json` and
`slice20-sse-live-resume-audit-2026-10-01.json`.
The source database, raw provider evidence, marker and full summary remain in
`artifacts/slice20-live-chain-resume-2026-10-01/`.

Limits: this is one guided code/model tool-choice chain under reviewed
synthetic workloads. The starter remains RECORDED_INSPECTION. Customer-task
eligibility, operation and inheritance pass; broader answer quality, learner
authorship, learning/transfer, real revenue and new hostile isolation probes
were not established. One live recovery proves one observed SSE interruption;
the retry limit, repeated failure, split-line and duplicate cases remain offline
proofs. The first attempt's failed slots and lost eighth inference record stay
unchanged. No further live attempt follows from this decision.

## Scoped architect-reviewer check and Git state

Static post-repair review found the new aclosing import, reconnect constant and
gateway/diagnostic helpers used by the adapter. The model candidate is referenced
by the runner and its tests; new evidence files are referenced by this record or
the status file. No stale file or duplicate fixture requires deletion in this
repair. No new schema, API or UI change was introduced by the SSE patch; no
browser product review or fresh whole-repository architecture audit was run.

During the run another session created four prior-evidence commits, advancing
local S20 HEAD from `651592f` to `50d3a02`. Inspection of `651592f..HEAD` shows
only earlier evidence files, with no source change. Remote main is still
`651592f` and remote S20 is still `0520141`. This session performed no Git write.
Its code, decision records and fresh evidence remain uncommitted, with no staged
changes. Commits and pushes require a separate user instruction.

## Subsequent housekeeping and publication authority: 2026-10-02

The Git paragraph above is the historical recovery-session snapshot. The user
subsequently instructed: "Do the housekeeping fix and then publish the branch
and merge/push to main". The two mutation harnesses now use fresh output paths
and exclusive log creation, refusing existing evidence before any mutation.
Fresh-output and refusal checks passed; an in-memory replacement with the old
truncating write fails the byte-preservation assertion for each harness.
Both archived post-change logs remain unchanged. No production source edit,
real mutation round, live call or install followed from this housekeeping fix.
Receipt: `slice20-publication-housekeeping-2026-10-02.txt`. Publication is in
progress; `../00-status.md` will record the verified publication refs.

Staging the original mutation transcripts exposed 49 trailing-whitespace
diagnostics (5 aborted, 44 completed), exit 2; the earlier unstaged check did
not include those new files. The raw proof is preserved, and every other staged
file passes the strict check. The status and MISTAKES record this formatting
exception explicitly.
