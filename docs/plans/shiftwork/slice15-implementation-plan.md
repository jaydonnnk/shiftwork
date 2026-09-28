# Slice 15: paired candidate execution

Status: implementation started 2026-09-27 on `shiftwork/slice-15` under the
user's explicit Slice 15 go-ahead. The draft fixtures below are **not sealed and
not operator-reviewed**; the slice's authorization line requires a separate
review of the three public workloads, the visible requirements and at least six
protected variants per enabled family before sealing, and a separate
authorization for live execution credentials and cost. Neither has happened yet.

**Current authority, 2026-09-28:** Gate 2 S8.1, Gate 3 and Gate 4 were
re-approved together and ADR 0006 was accepted. The Scope and earlier results
below describe the existing public-only Slice 15 draft. The approved remaining
contract is Gate 4 Slice 15 and Gate 3 S3.9/S6.3/S6.4/tests 50 to 54: a
separate reviewed comparison state, a meaningful candidate B preference,
distinct stimulus-bearing protected variants, and public then protected phases
in fresh workspaces with separate denominators and restricted captures. The
revised exact fixture bytes still require operator review and a separate seal;
live execution, credentials and cost remain separately authorized. The offline
baseline when this approval landed was 518 passed, 1 skipped and 77 of 77
mutation proofs; the later protected-phase proof round and its `528 passed,
1 skipped` suite and 97-row mutation run are recorded at the end of this file.

## Scope

1. Reserve one qualifying comparison per shift atomically: two frozen learner
   candidate versions with distinct content hashes, one declared treatment,
   shared requirements, the reviewed mission and public state, three reviewed
   workload batches, three never-exposed protected variants (one per pair,
   shared by that pair's A and B slots) and all six ordered trial slots before
   any result exists.
2. Bind pair 1 to workload 1, pair 2 to workload 2 and pair 3 to workload 3 by
   exact frozen bytes, hash and parsed request count, verified against the
   controller-owned reviewed manifest, never against a mutable path.
3. Execute the six slots in the precommitted order (pair 1 A/B, pair 2 B/A,
   pair 3 hash-derived) with a fresh reset workspace and the slot's frozen
   workload per slot. A failed or incomplete slot stays visible and is never
   refunded or retried.
4. Show the Compare station every slot, run identity, batch request count, exact
   version and missingness without a winner; expose only safe workload
   id/hash/count before a slot runs, never future request bytes or protected
   refs.

## Draft fixtures awaiting review

| File | What it is |
| --- | --- |
| `shiftwork/fixtures/requests/bookshop_compare_pair_0{1,2,3}.jsonl` | The three public workloads, two requests each, frozen from the reviewed public state. |
| `shiftwork/fixtures/requests/bookshop_compare_pair_0{1,2,3}_specs.json` | The public task specs (required/optional tasks, conditions, rule ids) each workload is assessed against. |
| `shiftwork/fixtures/requests/bookshop_compare_manifest.json` | The ordinal map with raw-bytes sha256, byte length, request count and task-spec sha256 per workload. |
| `shiftwork/sealed/cases/bookshop_task_completion.json` | Six protected task/entity/completion variants, one acceptance aspect each. |
| `shiftwork/fixtures/artifacts/bookshop/compare_repair_{a,b}_service.py` | The two draft candidate repairs the isolated offline comparison tests execute; distinct code and optional-evidence content, pending operator fairness review. |

Both candidates are labelled trusted-local fixtures for offline verification
only. They prove the reservation, pairing and projection mechanisms; they do not
prove learner-code isolation, fresh model behavior or a ranking between repairs.

## Offline proof

- Reservation: all-or-nothing writes, duplicate-key races, idempotent retry,
  one comparison per shift, owned investigation required, distinct content
  hashes required, manifest mismatch (file swap, count swap, dropped request,
  cross-engagement substitution) failing closed.
- Fairness: per-pair A/B equality of workload bytes, hash, count, task specs and
  protected refs; predeclared order immutable after the first result; fresh
  workspace per slot with no cross-candidate cache/booking/process carryover.
- Failure: a failed slot keeps its exposure and blocks completion; no refund, no
  automatic retry.
- Projection: every slot's identity, version, count, state and missingness
  without a winner; workload summary before execution exposes only id, hash and
  count.

## Verified offline results (2026-09-27)

- Full suite, packaging excluded (it installs): `.venv313/Scripts/python.exe -B
  -m pytest tests --ignore=tests/packaging -p no:cacheprovider -q` returned
  `488 passed, 1 skipped, 2 warnings in 105.23s`. The skip is the pre-existing
  live adapter conformance test. Slice 14's baseline was 454 passed.
- Two suite failures found and repaired in this round: the trusted-fixture pin
  guard did not yet skip the two comparison candidate pins, and the sealed-family
  needle self-test still compared the family file map against the three rotation
  families only. Both now cover the comparison family; the second failure was a
  genuine missing-coverage catch, not a test edit to obtain green output.
- Mutation proofs: `.venv313/Scripts/python.exe -B tests/pivot_mutation_proofs.py`
  exited 0 with 63 of 63 rows `FAIL_CAUGHT restored=True`. Twenty-one are new
  Slice 15 rows; six stale S11 anchors were re-anchored to the current diagnostic
  text (four had silently stopped matching at HEAD, two became ambiguous because
  the comparison slot repeats the same lines) and all six still fault their
  original named assertions.
- Browser proof resolved 2026-09-27; the failure was three harness defects, not
  product defects. (1) `wait('candidate A freeze')` was true from the initial
  render (`textContent.includes('Candidate A')`, and `'Candidate A\nnot frozen'`
  never matches because the row renders `Candidate Anot frozen yet`), so the page
  function clicked freeze B while `state.pending` had disabled the button and the
  click was swallowed; instrumented output showed the A wait returning at 0.00 s
  with the list still reading `not frozen yet` and the B click landing on a
  disabled button. (2) The harness's 20 s CDP send timer was shorter than the page
  function's 60 s polling deadline, so every page-level failure surfaced as the
  opaque `CDP timeout: Runtime.evaluate`; the send timer is now
  `CDP_TIMEOUT_MS = 90000`, strictly above the longest in-page deadline. (3) The
  six-slot wait compared the rendered `humanize`d state (lowercase) against
  `'FINALIZED'`, and slot task rows were matched on `task_id` plus verdict only,
  which collides because a two-request workload assesses each task once per
  request; the slot row now carries `data-request-ordinal` and the harness asserts
  the displayed ordinal as well as the dataset.
- Server-boundary evidence that ruled out product slowness first: a read-only HTTP
  probe against a disposable preview on a real uvicorn server (not TestClient)
  completed investigation, two freezes, the comparison POST and six-slot
  FINALIZED in 2.531 s with every slot COMPLETE and the precommitted order
  `1A 1B 2B 2A 3A 3B`.
- Repaired proof (verbatim): `node tests/client/browser.mjs
  http://127.0.0.1:8159 --compare-demo` exited 0. `compareDemo` reported
  `experiment-bookshop-shift-01-c1`, `FINALIZED` and slots
  `1:1A/workload-01/2 2:1B/workload-01/2 3:2B/workload-02/2 4:2A/workload-02/2
  5:3A/workload-03/2 6:3B/workload-03/2`; `uncaughtExceptions` 0. The screenshots
  `artifacts/slice9/compare-1280.png` and `artifacts/slice9/compare-390.png` were
  inspected: every slot shows its pair, candidate, step, workload, request count,
  version, run and trusted-local mode with the frozen request texts, and the
  panel states that the station never picks a winner.
- Failing-capability (verbatim): `node tests/client/render_faults.mjs` printed
  `render-fault rows: 11 of 11 as expected` and exited 0. The baseline row now
  runs `--compare-demo`, and the three new rows each failed their own named
  assertion: `candidateFreeze` at `Timed out waiting for candidate A freeze`,
  `slotOrdinalText` at `Slot 1 does not display the request ordinal for price`
  and `slotOrdinalKey` at `Slot 1 renders no price request 1 row with the payload
  verdict`.
- Offline suite after the client and harness repairs: `488 passed, 1 skipped,
  2 warnings in 75.89s`, unchanged from the Slice 15 baseline above.
- Mutation proofs re-run after the same repairs: `tests/pivot_mutation_proofs.py`
  exited 0 with 63 of 63 rows `FAIL_CAUGHT restored=True` and no `SKIP`,
  `NOT_CAUGHT` or `INCIDENTAL` row, matching the baseline above.

## Authorizations still needed

- Operator review of the three public workloads, the visible requirements and
  the six protected variants before sealing (the manifest and family file are
  marked `AWAITING_OPERATOR_REVIEW`).
- Live execution credentials and cost if a live six-slot comparison is wanted.
  The offline path uses only the byte-pinned trusted-local adapter.

## 2026-09-28 completion checks and remaining gates

- A repeat comparison POST could dispatch a second worker during the first
  slot. A failing concurrent test observed six adapter calls before worker one
  was released, where one was expected. The comparison now starts `PLANNED`;
  one worker atomically claims it as `RUNNING`. Running or terminal replays do
  not dispatch again. An unexpected slot exception leaves the experiment
  `FAILED`, the failed slot spent and the other slots visible as reserved.
- After the repair, the full offline suite returned `503 passed, 1 skipped,
  2 warnings in 69.73s` with packaging excluded. A fresh draft-review preview
  at `http://127.0.0.1:8173` passed `--compare-demo`: `FINALIZED`, six ordered
  slots, zero uncaught exceptions. The preview was stopped. The mutation rows
  returned `74 of 74 FAIL_CAUGHT restored=True`, exit 0, using per-row output.
  A previous direct invocation stopped on a Windows file-write error; the
  source file remained intact and compiled, and that attempt is not a pass.
- The architect-reviewer cleanup scan found no orphan among the new fixture
  and helper files and no exact duplicate test files. The draft preview helper
  remains referenced by `tests/client/render_faults.mjs`; exposure invalidation
  helpers are assigned to Slice 16. No deletion is recommended.
- Material review recommendation: revise before sealing. Candidate A and B
  intentionally share the mandatory repair and differ mainly in optional
  price content. The present rubric does not measure a meaningful preference
  between them. The six protected variants encode distinct public-rule
  aspects, but their semantic independence needs an operator decision.
- Still unstarted: the independent review round and operator review. The
  manifest and protected family remain `AWAITING_OPERATOR_REVIEW`. Slice 15 is
  unaccepted and uncommitted; no live six-slot execution was authorized.

## 2026-09-28 adversarial review repair and Gate 2 hold

The review reproduced and repaired restart terminalization at three boundaries,
the blank-line reservation/executor parser split, and a pre-adapter slot error.
Same-key HTTP POSTs were tested with both background workers held before claim.
The reservation fault matrix now includes every observed write, including the
protected-case snapshot and experiment-link UPDATE. A before/after business
state guard has separate injected ledger and incident positive controls.

Final offline suite: `518 passed, 1 skipped, 2 warnings` with packaging
excluded. Final mutation run: 77 of 77 `FAIL_CAUGHT` with every target restored
byte-identically. `git diff --check` passed. The review found that the current
candidate outputs differ only on unmeasured optional price and that protected
cases are labels over identical stimuli. Gate 2 is now in progress for the
scoped design proposal in `02-architecture.md` section 8.1. Gate 3 and Gate 4
needed reconciliation after Gate 2 re-approval. That hold was closed by the
2026-09-28 joint re-approval recorded at the top. The active fixture bytes
remain unreviewed and unsealed; Slice 15 remains unaccepted.

## 2026-09-28 protected-phase proof round and mutation repair

After the joint re-approval, this round implemented the approved Gate 2 S8.1,
Gate 3 S3.9/S6.3/S6.4 and trace rows 50 to 54 behavior on top of the existing
draft, and then rebuilt the proof evidence for it:

- New mutation rows (19) for the protected phase: phase skipped, protected
  before public, swapped phase state, reused workspace, protected line through
  `load_batch`, multiline and wrong-ordinal protected batches, pair variant
  leaked, a second variant in one slot, a mismatched ordinal, the readback
  binding hash, delta collision acceptance, both protected canonicalizers
  (request bytes and resolved state), the response and observation ordinal
  filters, a merged public denominator, protected counts before terminal, and
  candidate B preferring lowest price.
- Three drifted rows were re-anchored to the current source: the comparison
  missing-capture line, the diagnostic mission load (its region has mixed line
  endings, so the anchor encodes them exactly), and the manifest
  engagement/state-pin condition.
- Two rows were repaired after their first fault shape tripped recorder or
  adapter exceptions instead of a product assertion: the phase-order swap now
  builds the adapter first (assertion: `("protected", "public")`), and the
  state swap now feeds the protected state to the public phase (assertion:
  the public state binding).
- Test 53 gained a fourth fault arm (a public output whose log carries the
  protected request text must be refused with 409) and a stored-observation
  positive control, so the response, observation and log surfaces each have
  their own fault evidence alongside the public shop derivation arm.

Verified: all 19 new rows individually `FAIL_CAUGHT`; the full offline suite
before the test-file edits `525 passed, 1 skipped, 2 warnings` (packaging
excluded); the focused lifecycle file after the edits `79 passed`.

The first full 96-row run was not a pass, for two separate reasons. The
driver crashed at row 95 (`s15_protected_counts_before_terminal`) when its
restore write hit `OSError: [Errno 22] Invalid argument` on
`shiftwork/orchestrator.py`; the stranded mutation was located by re-checking
all anchors (exactly one broken), reverted byte-precisely, and the buffered
run output was lost with the crash (recorded in `MISTAKES.md`, same date). The
rerun ran under a crash-proof driver: per-row flushed output, a results file
appended after every row, a `CRASH` record naming the row that dies, and
retried target writes (the restore sha256 assert unchanged). That run reported
92 of 96 rows `FAIL_CAUGHT` and exit 1 because four older rows had silently
lost proof-grade status when the protected-phase guards landed (also recorded
in `MISTAKES.md`).

Diagnosis and repair, one row at a time:

- Row 4 (`s15_protected_snapshot_write_removed`) was `CAUGHT_INCIDENTAL`: the
  reservation readback refuses any missing snapshot with `InvalidSealedCase`,
  so no assertion observes the removed write. Re-anchored and renamed
  `s15_protected_snapshot_immutability_removed`, faulting the
  `protected_case_snapshots_no_update` trigger in
  `shiftwork/store/migrations/v6_tables.sql` against the same named test.
- Row 59 (`s15_manifest_count_not_recomputed`) was `NOT_CAUGHT`: the old
  `wrong_claimed_count` shape trips both the recomputed count check and the
  protected-ordinal tie
  (`stimulus.request.ordinal != workload.request_count + 1`), so it proved
  neither. The test gained `extra_request_with_recomputed_pin` (appends a
  request and its spec to workload-01 with every pin recomputed), which only
  the count check can catch; the row names it.
- Rows 68 and 69 (`s15_slot_binding_not_reverified`,
  `s15_slot_count_binding_not_reverified`) were `NOT_CAUGHT` for every context
  tamper because the round's frozen context-hash re-verification
  (`_frozen_comparison_context_hash(context, bindings) != context.content_hash`)
  catches the whole tampered context globally. Row 68 now faults only the
  slot-hash limb and names the new `[slot_hash]` parameter. Row 69 was renamed
  `s15_request_line_identity_unchecked` (faulting
  `parsed_line.get("request_id") != spec.id`) and names
  `[wrong_request_id_with_recomputed_pin]`. The `[slot_count]` limb was
  measured unprovable: with it removed, the only reachable divergence is
  caught by the comparison view's private-material guard as an incidental
  `LifecycleError`, so `[slot_count]` stays a fail-closed scenario with no row
  of its own. The measurements and exclusions are recorded in the harness
  docstring.
- New row 97, `s15_frozen_context_hash_not_reverified`, faults the
  context-hash check itself against `[swap_bytes]`, so the masking guard is
  proven too.

The tamper test gained three parameters in total:
`extra_request_with_recomputed_pin`, and `slot_hash` and `slot_count` (they
drop `trial_slots_guard_update` before updating all six slot rows, because a
plain `UPDATE trial_slots` hits the immutability trigger).

Verified after the repairs: all 97 anchors present exactly once; each repaired
or new row (4, 59, 68, 69, 97) individually `FAIL_CAUGHT restored=True`; the
four touched parameters pass on the unmutated tree; the full 97-row run
exited 0 with 97 of 97 `FAIL_CAUGHT` and every target restored
byte-identically. Evidence:
`docs/plans/shiftwork/evidence/slice15-mutation-rerun-2026-09-28.txt`; the
preserved 92-of-96 run is `...-pre-repair.txt`.

Follow-on checks on the same tree (2026-09-28):

- Full offline suite after the test edits: `528 passed, 1 skipped, 2 warnings
  in 95.21s` with packaging excluded, exit 0. The +3 over the pre-edit 525 are
  the new tamper parameters; the skip remains the live adapter conformance
  test.
- Browser `--compare-demo` against a fresh draft-review preview on
  `http://127.0.0.1:8175`: the first run exited 1 at `Slot 1 renders the wrong
  frozen batch size` because the compare row copy changed to
  `N public requests + M protected steps` while the harness still asserted the
  old `N request` substring. The harness assertion was updated to the rendered
  copy and gained a protected-step limb with its own served-source fault row
  (`slotProtectedCount`). The repaired run exited 0 with `FINALIZED`, the six
  ordered slots
  `1:1A/workload-01/2 2:1B/workload-01/2 3:2B/workload-02/2 4:2A/workload-02/2
  5:3A/workload-03/2 6:3B/workload-03/2` and `uncaughtExceptions` 0. The
  screenshots `artifacts/slice9/compare-1280.png` and
  `artifacts/slice9/compare-390.png` were inspected: every slot shows its
  pair, candidate, step, workload, `N public requests + M protected steps`,
  version, artifact hash, run id and trusted-local mode with the frozen
  request texts.
- Failing capability: `node tests/client/render_faults.mjs --port 8471` exited
  0 with `render-fault rows: 12 of 12 as expected`. The baseline row ran
  `--compare-demo` green, and every fault row failed at its own named
  assertion, including the new `slotProtectedCount` row (`Slot 1 renders the
  wrong protected step count`). The first attempt of this run reported `0 of
  12` because an unrelated local application held the fixed default port 8137
  while the preview banner prints before the bind, so every row talked to the
  foreign server; `render_faults.mjs` now polls the preview's board endpoint
  (`waitReachable`) so a port collision fails loudly instead of surfacing as a
  page-load error. Both harness repairs are recorded in `MISTAKES.md`.
- Operator packet rewritten to the revised exact bytes; all 18 digests in it
  were recomputed from the current files and verified, and the file was
  normalized to its CRLF line endings.

Remaining before this slice can be shown as complete: nothing offline, and
the `00-status.md` record and the architect-reviewer post-slice scan are both
written (scan outcome in `00-status.md`; no orphan, duplicate test file or
stale scaffolding to remove). Operator review, sealing, live execution and
acceptance all remain outstanding approvals.

Exact hashes for the packet rewrite, computed 2026-09-28: comparison state
`bookshop_compare_state_v1.json` 4,261 bytes / `4abe54462600ade9793c1d7dc32978c427d4f0b0a5e5b121830cfc3b478a2f6f`;
manifest `bookshop_compare_manifest.json` 1,762 bytes / `aacb1fff1d7973a2b61b412c774e24da42cbea4156270c26c4ecf61dcac20ebe`
(canonical `workloads` digest `6e21937b65606e489b3768d3cd15347eff778ca6ee90f883dd68b318d8d66317`);
protected family `bookshop_task_completion.json` 19,977 bytes / `5d0f5af5b5cfd13e50ab5f68b36cf6e34757847439da31916bdab0cb0a2fe5cd`
(canonical `cases` digest `da93870aee735f1291c8b333bf38c8ce2cf12c33ad4511763e65b4414327d55e`);
candidate A `compare_repair_a_service.py` 9,148 bytes / `7497195129f70481940670cd5ce6eb7782dcfcafefe5e5b0a8459e263d3e6b71`;
candidate B `compare_repair_b_service.py` 8,395 bytes / `b4674218d44abdab011c9201f5f0dcff1a4b302a281623f189376ed5784e0342`.
Measured candidate behavior over the six public requests and the comparison
state: both complete every required task; the only rubric-bearing difference is
request 011, where A returns `book:tidal-paths:paperback` at 1,400 and B returns
`book:harbour-atlas:paperback` at 1,600; A also emits an optional price on the
four collection requests where B omits it, which the rubric does not measure.
