# Slice 8 adversarial review: close to inheritance plus Test 1 offline pre-proof

Date: 2026-09-20
Reviewer role: cold, adversarial, independent. The author of the code also wrote the
documents describing it, so every documentary claim below was treated as a hypothesis
and falsified or reproduced by execution.
Branch: `shiftwork/slice-8`, HEAD `a481479`, plus the author's uncommitted close and
inheritance work. Nothing was committed, pushed, stashed, discarded, reverted or staged.

## Verdict

**REVISE.**

Strongest single reason: the Test 1 offline pre-proof is the first proof slice, and
`04-slices.md:538-540` makes it the go/no-go for the central mechanism, yet two of the
five kill-condition PASS verdicts rest on evidence sentences the code never computes.
Kill condition 5's "the same sealed stimuli at the same request ordinal, with only the
artifact changed" is a hardcoded f-string (`demos/test1.py:329-333`); the verdict itself
checks only the two verdict strings (`demos/test1.py:322-328`). Kill condition 3's "the
board's event totals equal a replay of the stored events" compares a value to a
recomputation of the same rows from the same reader (`demos/test1.py:541` against
`demos/test1.py:506-508` and `shiftwork/orchestrator.py:754-756`). Both underlying claims
happen to be true, and I verified that independently, but the PASS verdicts do not depend
on them, so the pre-proof would still print PASS if either became false.

No CRITICAL finding. The production logic I attacked held on every item, and all 38
mutation rows reproduce at assertion level. The defects are in the evidence layer and in
two coverage gaps, which is exactly the class this project's own `MISTAKES.md` has logged
four times and graduated into `AGENTS.md` S6.

## Commands run and verbatim results

All commands used `.venv/Scripts/python.exe`. Bare `python` was never used.
`mutation_proofs.py` was never killed mid-run; all four invocations completed and each
left the worktree byte-identical.

Baseline, author's worktree unmodified:

```
git branch --show-current            -> shiftwork/slice-8
git log --oneline -1                 -> a481479 Record the Slice 8 run-binding seam evidence
git diff --check                     -> no whitespace errors (3 CRLF advisories only)
git status --short                   -> 32 entries (24 modified, 8 untracked)
pytest tests -q                      -> 192 passed, 1 skipped, 2 warnings in 46.93s
tests/mutation_proofs.py             -> assertion-level catches: 38/38   (exit 0)
```

Demos, all exit 0:

```
demos.test1 --adapter local_process  -> PRE-PROOF PASS (conditional on the offline executor:
                                        kill condition 2 deferred to Slice 14)
                                        surfaces scanned: 87 (leaks: 0)
                                        ledger: 37 events, chain VALID; resolutions 18
                                        re-scored offline: 6 runs, 36 stored / 36 rescored,
                                        identical=True
demos.thin_path                      -> run-0001 FINALIZED, content_hash 44abb79897239264...,
                                        3 CheckResults (fail/STALE_BEYOND_RULE first),
                                        3 BACKLOG_RECORDED seq 1-3, chain VALID
demos.lifecycle                      -> 3 events, chain VALID, 3 open incidents
demos.finalize_run                   -> 3 events, 3 incidents opened, finalize twice nets zero
demos.repair_loop                    -> attempts 1-3 FINALIZED, 3 incidents opened then resolved,
                                        6 events, chain VALID
demos.evaluate_transcript passing    -> 6 pass / 0 fail, sockets blocked
demos.evaluate_transcript failing    -> 0 pass / 6 fail, sockets blocked
```

Evidence-file reproducibility. I ran the demo with `--evidence` pointed at a temp path so
the author's file would not be clobbered, then diffed:

```
diff "$TEMP/rev-test1.md" docs/plans/shiftwork/evidence/test1-central-mechanism.md | wc -l
-> 0
```

The committed evidence file is byte-identical to a fresh regeneration.

Committed seam, verified in a detached temp worktree at `a481479` (created and removed;
`.git/worktrees` pruned; main worktree never touched):

```
pytest tests -q          -> 179 passed, 1 skipped, 2 warnings in 43.81s
tests/mutation_proofs.py -> assertion-level catches: 27/27   (exit 0, worktree clean after)
```

After my single test-file change (see the rewrite table):

```
pytest tests -q                          -> 1 failed, 191 passed, 1 skipped, 2 warnings in 940.75s
                                            FAILED tests/packaging/test_clean_env_install_and_run.py
                                               ::test_clean_env_install_and_run
pytest tests -q --ignore=tests/packaging -> 191 passed, 1 skipped, 2 warnings in 37.00s
tests/mutation_proofs.py                 -> assertion-level catches: 38/38   (exit 0)
```

The one failure is not a Slice 8 regression and not caused by my edit. Test 51 performs a
real network install into a fresh venv with `timeout=900`
(`tests/packaging/test_clean_env_install_and_run.py:128-131`); the 940.75s wall time is
that timeout expiring. It passed in the 46.93s baseline run (warm pip cache) and failed on
rerun (cold or slow network). My edit touched only
`tests/orchestrator/test_close_inheritance.py`, which the packaging test never imports.
Reported as flaky and environment-dependent, per `AGENTS.md` S6; see MAJOR-6.

Net test-count change from my edit: zero. No test was added, deleted, renamed or skipped.

## Findings

### MAJOR-1: kill condition 5's evidence sentence is not computed

`demos/test1.py:329-333`

Defect: the sentence "the pre-repair artifact fails and the repaired artifact passes the
same sealed stimuli at the same request ordinal, with only the artifact changed" is a
constant f-string. The only interpolated value is `len(comparison)`. The PASS condition at
`demos/test1.py:322-328` is:

```python
"PASS" if comparison and all(
    row["pre_verdict"] == "fail" and row["post_verdict"] == "pass" for row in comparison
) else "FAIL"
```

Neither request ordinal, nor request text, nor snapshot identity, nor output-body
difference is compared anywhere in the demo. `_causal_rows` (`demos/test1.py:154-198`)
collects `pre_request`, `post_request`, `pre_body` and `post_body` and nothing reads them.
The markdown table at `demos/test1.py:360-364` prints only check id, run, version and
verdict. So kill condition 5 would print PASS on a comparison of different stimuli.

Falsifier attempted, and the claim survives on the facts. I rebuilt the arc and compared
the two sides of all nine rows directly:

```
PROBE C causal rows: 9
  chk-hostile-instruction-01: same_text=True same_ordinal=True pre_ord=1 post_ord=1 same_body=False pre_batch=bookshop_attempt_01.jsonl post_batch=bookshop_attempt_04.jsonl same_snapshot=True
  chk-hostile-instruction-02: same_text=True same_ordinal=True pre_ord=2 post_ord=2 same_body=False pre_batch=bookshop_attempt_02.jsonl post_batch=bookshop_attempt_04.jsonl same_snapshot=True
  chk-hostile-instruction-03: same_text=True same_ordinal=True pre_ord=3 post_ord=3 same_body=False pre_batch=bookshop_attempt_03.jsonl post_batch=bookshop_attempt_04.jsonl same_snapshot=True
  (policy-exception-01..03 and stale-information-01..03 identical in shape)
  rows with differing request text: 0 | differing ordinal: 0
```

So the sentence is true today: same sealed check, same request ordinal, same request text,
same snapshot, different output body, opposite verdict. It is true by configuration, not by
mechanism, which is the exact defect `MISTAKES.md` logged on 2026-09-18 ("Slice 5 status
claimed a per-run snapshot pairing that does not exist"). Note also that the two runs
executed different batch files (`bookshop_attempt_01/02/03.jsonl` against
`bookshop_attempt_04.jsonl`), so "only the artifact changed" is true of the compared
request, not of the compared runs.

Partial mitigation: the pytest test does assert one of the three clauses,
`row["pre_request_text"] == row["post_request_text"]`
(`tests/orchestrator/test_test1_preproof.py:174-176`). It asserts neither the ordinal, nor
snapshot identity, nor that the bodies differ.

Minimal fix: in `_causal_rows`, assert `pre_output.request_ordinal ==
post_output.request_ordinal`, `pre_run.shop_snapshot_ref == post_run.shop_snapshot_ref` and
`pre_output.body != post_output.body`; add those three booleans to the evidence dict; build
the kill-5 sentence from them and gate the PASS on them.

### MAJOR-2: kill condition 3's "replay" is a value compared to a recomputation of itself

`demos/test1.py:541`, `demos/test1.py:506-508`, `shiftwork/orchestrator.py:754-756`

Defect: `board_matches_replay` is `board_two["ledger_totals"] == replay_totals`.
`replay_totals` is built by counting `event.event_type.value` over
`repo.list_ledger_events(conn, config.BOOKSHOP_SLUG)`. `board_two["ledger_totals"]` is
built by `board_snapshot` counting `event.event_type.value` over
`repo.list_ledger_events(conn, slug)` from the same table. There is no independent replay:
no reducer, no fold, no second projection. The comparison can only fail if the API schema
drops or renames the field.

Falsifier, executed. I patched the shared reader to silently drop the last event and
recomputed both sides:

```
PROBE D full event count: 37
  board_totals (truncated reader): {'INCIDENT_OPENED': 18, 'LIMIT_DECLARED': 1, 'INCIDENT_RESOLVED': 17}
  replay_totals (truncated reader): {'INCIDENT_OPENED': 18, 'LIMIT_DECLARED': 1, 'INCIDENT_RESOLVED': 17}
  still equal after silently dropping an event: True
```

A check that survives the loss of an event is not checking equivalence. This is the hollow
pattern the review mandate names explicitly ("assertions comparing a fixture's own return
value to itself or to a re-computation of the same expression").

The same shape is pre-existing in test 10's own test,
`tests/ledger/test_ledger.py:474-485`, and Slice 8 copied it into
`tests/orchestrator/test_close_inheritance.py:268-273`. So this is not new, but Slice 8
promoted it to evidence for a Test 1 kill condition, which raises its stakes.

Kill condition 3 is not wholly unsupported: `chain_valid` is a real hash-chain
verification and the version-pin checks at `demos/test1.py:566-572` are real and enforced by
`raise SystemExit`. Only the middle clause of the sentence is vacuous.

Minimal fix: either compute the board's business state by folding the stored events through
`reducer` and compare that to the table projection, or delete the clause from the sentence
and from the PASS condition and say what kill 3 actually rests on (chain verification plus
version-pin reproduction).

### MAJOR-3: the future-wording leak scan has no scanner self-test

`demos/test1.py:111-117`, `tests/orchestrator/test_test1_preproof.py:180-188`

Defect: `AGENTS.md` S6 carries a graduated rule from the 2026-09-18 Slice 6 incident: "For
every absence or leak assertion, prove the needle can match the surface as serialized...
Add a scanner self-test that injects the needle into a representative serialized surface and
requires detection." Neither the demo's `Surfaces.leaks` nor the pytest test's leak scan has
one. The test asserts `future_texts` is non-empty
(`tests/orchestrator/test_test1_preproof.py:181`) and that nothing leaked
(`:188`), which is the "count of surfaces scanned" shape the rule rejects.

I supplied the missing proof externally, and the scan survives it:

```
PROBE A future_texts: 3
  shift1 leaks (expected 0): 0
  shift2 leaks (positive control, expected >0): 10
  shift2 surfaces: 27
PROBE B inject into surface: board bookshop-shift-01 len 2176
  detected after injection: 1
  restored, leaks again: 0
```

The positive control matters: the ordinal 4, 5 and 6 customer sentences are legitimately
released once shift 2 executes them, and they do appear on 10 of shift 2's 27 serialized
surfaces. So the needles match the serialized form and the shift-1 zero is a real absence,
not the `needle in surface` mismatch that made six of eight Slice 6 needles vacuous. This is
a missing required proof, not a false claim.

Minimal fix: add three lines to the test. Take one collected surface, append
`future_texts[0]`, require `leaks` to return it, restore, require zero. That is the same
self-test shape PROBE B used.

### MAJOR-4: test 32's draft-seeding assertion was vacuous (fixed in this review)

`tests/orchestrator/test_close_inheritance.py:267`, guarding `shiftwork/orchestrator.py:173`

Defect as found: the `driven` fixture opened a shift and froze it without editing the draft,
so the frozen version's files were byte-identical to `orchestrator.BOOKSHOP_DRAFT_FILES`.
The assertion `draft["files"] == inherited.files` therefore could not distinguish "seeded
from the inherited version" from "seeded from the shipped template". No mutation row targets
`orchestrator.py:173`.

Falsifier, executed (mutation M3, byte-verified, restored to
`sha256 c91200cb55ad707b44785dd3016be199864ec90b0e73ec11ae6740c404c02cf7`):

```
M3 open_next_shift_seeds_the_template_not_the_inherited_version
  old: files = dict(inherited.files) if inherited is not None else BOOKSHOP_DRAFT_FILES
  new: files = dict(BOOKSHOP_DRAFT_FILES)
  pytest: 1 failed, 1 passed
  PASSED (still green under the mutation): test_open_shift_seeds_from_inheritance
  FAILED [assertion]: test_full_budget_preserves_unseen_inherited_case
```

So the production guard is covered, but by the pre-proof test, not by the test the slice plan
names for it. `04-slices.md:526` claims "32 (open seeds from inheritance - full)".

Action taken: I edited the `driven` fixture to PUT a learner edit before freezing and added
a fixture-level guard that the frozen files differ from the template. Re-probe after the edit,
same mutation, same byte restoration:

```
M3 re-probe: mutation landed: True
  pytest: 1 failed, 2 warnings in 0.75s
  FAILED [assertion]: assert {'contract.js..._forever()\n'} == {'contract.js...ited draft\n'}
  sha256 before: c91200cb55ad707b44785dd3016be199864ec90b0e73ec11ae6740c404c02cf7
  sha256 after : c91200cb55ad707b44785dd3016be199864ec90b0e73ec11ae6740c404c02cf7  restored= True
```

The assertion is now failing-capable. Suite and harness counts before and after are in the
rewrite table below.

### MAJOR-5: the board's inherited-version fallback has no mutation row and fails only incidentally

`shiftwork/orchestrator.py:741-744`

Defect: this is a new Slice 8 guard. It supplies the inherited version to the board when the
latest shift has frozen none, and it is load-bearing for test 32's headline assertion
(`tests/orchestrator/test_close_inheritance.py:265`) and for the demo's kill condition 4
(`demos/test1.py:513`). No mutation row in `tests/mutation_proofs.py` targets it.

Falsifier, executed (mutation M7, byte-verified, restored to the same sha256 as M3/M4/M5):

```
M7 board_snapshot_inherited_version_fallback_removed
  pytest: 2 failed, 2 warnings in 1.42s
  FAILED [INCIDENTAL/ERROR] test_open_shift_seeds_from_inheritance: TypeError: 'NoneType' object is not subscriptable
  FAILED [INCIDENTAL/ERROR] test_full_budget_preserves_unseen_inherited_case: TypeError: 'NoneType' object is not subscriptable
```

Both catches are a `TypeError` from subscripting `None`, not an assertion. The project's own
harness classifies that as `CAUGHT_INCIDENTAL` and fails the proof row
(`tests/mutation_proofs.py:458-469`), and `MISTAKES.md` 2026-09-20 records exactly this
failure mode from the Slice 7 review round. So a load-bearing new guard is proved only by a
crash that would equally fire if the assertion were wrong for an unrelated reason.

Minimal fix: assert `board["latest_version"] is not None` before subscripting in both tests,
and add a mutation row for `orchestrator.py:741-744` naming
`test_open_shift_seeds_from_inheritance`.

### MAJOR-6: the full-suite claim is not stably reproducible

`docs/plans/shiftwork/00-status.md:2518`

Defect: the section records `pytest tests -q -> 192 passed, 1 skipped` as verbatim evidence
re-run before recording. It reproduced exactly on my first run (46.93s). On my second run of
the same command it returned `1 failed, 191 passed, 1 skipped in 940.75s`, the failure being
test 51's clean-env install exceeding its 900s timeout
(`tests/packaging/test_clean_env_install_and_run.py:128-131`). The test docstring states
"Requires network access for the installer" (`:10`).

This is not a Slice 8 defect and not caused by my edit, but the evidence line as written
implies a stable full-suite result. `MISTAKES.md` 2026-09-17 already logged the related
error of recording one transient observation as a standing fact, and `00-status.md:1430`
region notes the 2026-09-19 audit excluded test 51 because installs were prohibited.

Minimal fix: record the command with its scope and wall time, for example
`pytest tests -q --ignore=tests/packaging -> 191 passed, 1 skipped in 37.00s`, and note test
51 separately as network-dependent with the observed outcome and duration.

### MINOR-1: "log bytes ... byte-for-byte" names a surface no test populates or compares

`docs/plans/shiftwork/00-status.md:2475`, `tests/ledger/test_ledger.py:404-408` and `:432-436`

The reconcile test snapshots each output as
`(row.id, row.request_ordinal, bytes(row.body), row.request_text)`. `RunOutput.log_ref`
exists (`shiftwork/domain/models.py:214`) but is never set by `_invented_output`
(`tests/ledger/test_ledger.py:83-107`) and never compared. `http_status`, `elapsed_ms` and
`transport_error` are likewise not compared. The claim is true by construction, since
`reconcile_interrupted` only calls `repo.update_run`
(`shiftwork/orchestrator.py:625-631`), but it is asserted rather than proven.
Fix: set a `log_ref` in `_invented_output` and widen the compared tuple to the whole row.

### MINOR-2: "resolved by the first passing run" is prose, not a computed value

`docs/plans/shiftwork/00-status.md:2532`, `demos/test1.py:511-528`,
`docs/plans/shiftwork/evidence/test1-central-mechanism.md:20` and `:49-50`

`inheritance["ok"]` requires every incident to be RESOLVED and the board to show none. It
never checks which run resolved them. The claim is true in the data: all 18
INCIDENT_RESOLVED events in the evidence file's ledger replay carry `cause_refs[0] =
"run-0004"`, which is shift 2 attempt 1 (`evidence/test1-central-mechanism.md:541-720`).
Fix: derive "first" from the minimum resolving seq, or drop the word.

### MINOR-3: kill condition 1's wording overstates the case set, and its PASS is vacuous at zero runs

`docs/plans/shiftwork/evidence/test1-central-mechanism.md:17`, `demos/test1.py:226` and `:257`

The sentence says "against their drawn sealed cases". The code rebuilds the case set from
every stored check id (`demos/test1.py:226`), which is the drawn variants plus the inherited
regression cases, so 36 results rather than 18 draws. The 00-status wording at `:2543-2546`
is accurate; the evidence file's is not. Separately, `identical` is
`all(... for run_id in run_ids)` (`:257`), which is vacuously True for an empty run list; the
demo prints the run count so a reader would notice, but nothing gates on it. Fix: say "their
stored scored case set", and require `run_ids` to be non-empty.

I verified the substance of kill condition 1 holds. The replay is a genuine recomputation
(the evaluator re-derives verdict, reason code, observed ref and expected digest from stored
output bytes), and the socket block is failing-capable:

```
PROBE E socket block fired SystemExit: network access attempted during scoring; the evaluator must run offline
  sockets restored: True
```

### MINOR-4: the causal rows carry body evidence that is never asserted

`demos/test1.py:192-193`, `tests/orchestrator/test_test1_preproof.py:316-317`

`pre_body` and `post_body` are base64-encoded into every row by both the demo and the test
and read by neither. PROBE C shows all nine pairs differ, which is the single most direct
proof that the artifact caused the outcome, and it is discarded. Fix: assert
`row["pre_body"] != row["post_body"]` (see MAJOR-1).

### MINOR-5: `test_next_shift_needs_the_six_variant_inventory` has no mutation row, and its natural mutation is caught incidentally

`tests/orchestrator/test_test1_preproof.py:193-227`

Mutating the guarded line (rotation exhaustion, `shiftwork/sealed/rotation.py:46-52`) to
reuse exposed variants produced an incidental catch, not an assertion:

```
M6 rotation_exhaustion_silently_reuses_exposed_variants
  pytest: 1 failed
  assertion: sqlite3.IntegrityError: UNIQUE constraint failed: rotation_draws.engagement_slug, rotation_draws.variant_ref
  PROBLEM: failed at incidental level, not assertion
  sha256 restored=True (13e4c85deb40db65a8aaf8fab3724980071da3d465a60a6594d4fc9105eb836b)
```

The test is nevertheless not vacuous: mutating the error's HTTP mapping so the refusal
returns 404 fails it at assertion level.

```
M6b RotationUnavailable.kind "conflict" to "not_found"
  FAILED test_next_shift_needs_the_six_variant_inventory [assertion]: assert 404 == 409
  FAILED test_rotation_exhaustion_fail_closed [assertion]: assert 404
  sha256 restored=True (02a0ee5c2c0cd10cdbef20e9f74e573d592b2690e69b931c36cc24bfc5d39fb4)
```

Fix: add a mutation row for the exhaustion raise and assert the refusal detail before the
status code, so the intended guard is what fires.

### MINOR-6: reconciliation happens only at startup, and the operational consequence is unstated

`shiftwork/app.py:39` is the only call site of `reconcile_interrupted` in the package
(verified by grep across `shiftwork/`). A run left QUEUED while the app keeps running, for
example one whose background task (`shiftwork/api/routes.py:96`) never executes, is never
reconciled, and `close_shift` refuses it indefinitely
(`shiftwork/orchestrator.py:575-581`) until the process restarts. That is defensible design,
since a reservation is real state, but `00-status.md:2473-2476` describes reconcile as
recovery without saying that startup is the only recovery point. Fix: one sentence in the
status note and in the `reconcile_interrupted` docstring.

### NIT-1: duplicated declared limits double the ledger events

`shiftwork/domain/models.py:131` declares `declared_limits: tuple[str, ...]` with no
uniqueness validation, and `reduce_close` emits one event per element
(`shiftwork/ledger/reducer.py:151-161`). Executed probe:

```
freeze duplicate declared_limits -> 201
close -> 200
LIMIT_DECLARED events for one distinct limit: 2
board unresolved_limits: ['SAME LIMIT']
```

The board projection dedups (`shiftwork/store/repo.py:670-677`), so nothing learner-visible
is wrong, and "exactly once" per declaration still holds literally. Fix if wanted: reject a
contract whose `declared_limits` contains duplicates at freeze.

### NIT-2: the demo's socket block has no self-test

`demos/test1.py:235-252`. PROBE E shows it fires. Test 11 owns injected scoring I/O
elsewhere, so this is a note, not a gap in Slice 8's scope.

## Mandate A: item-by-item result

Each item was attacked with a concrete counterexample or an executing probe before being
passed.

1. **close_shift** PASS. One `BEGIN IMMEDIATE` transaction with rollback on any exception
   (`shiftwork/orchestrator.py:569-611`). Idempotency: the closed-shift early return
   (`:572-574`) is load-bearing, proved by mutation row `close_idempotency_removed` and
   independently by my M4, which failed `test_concurrent_closes_write_one_event_set` at
   assertion level on "the two closes recorded different close times". In-flight refusal
   covers QUEUED, RUNNING and CAPTURED (`:575-581`), proved by row
   `close_in_flight_refusal_removed`. LIMIT_DECLARED exactly once per declaration, proved by
   rows `close_leaves_incidents_open` and the test's own `len(declared) == len(DECLARED)`.
   OPEN to CLOSED_UNRESOLVED retirement is engagement-wide and state-scoped
   (`shiftwork/store/repo.py:517-528`). Atomicity is genuinely proven: my M5 inserted a
   mid-transaction commit and `test_close_fault_leaves_neither_partial_close_nor_partial_events`
   caught it at assertion level with "a fault in close_shift retired incidents without
   closing". Two concurrent closes serialize and write one event set; the test asserts equal
   `closed_at` across both threads. See NIT-1 for the duplicate-limit edge.
2. **open_next_shift** PASS with MAJOR-4. Seeding is `dict(inherited.files)`
   (`shiftwork/orchestrator.py:172-174`), and the version reader re-verifies the recorded
   content hash on every read (`shiftwork/store/repo.py:171-194`), so a tampered version
   cannot seed. No version at all falls back to `BOOKSHOP_DRAFT_FILES`. Second open while one
   is open returns 409, proved at assertion level by my M8.
3. **start_run inherited-version fallback** PASS. The fallback cannot cross engagements.
   Executed probe with two seeded engagements:
   ```
   PROBE H bookshop version: ver-0001
     bookshop fallback: ver-0001
     northline fallback (must be None): None
     northline start_run refused: conflict freeze a version before starting a run
   ```
   The reader joins on `s.engagement_slug = ?` (`shiftwork/store/repo.py:229-235`). A shift
   cannot run a version it should not: the fallback only fires when the shift has frozen
   nothing, and only to the engagement's own latest version. Proved by row
   `start_run_ignores_the_inherited_version`.
4. **reconcile_interrupted** PASS with MINOR-1 and MINOR-6. `list_nonterminal_runs` excludes
   FINALIZED and FAILED in SQL (`shiftwork/store/repo.py:338-344`), so a FINALIZED run cannot
   be failed; proved by my M1, which made FINALIZED nonterminal and failed
   `test_restart_keeps_a_committed_finalized_run` at assertion level. Captures and draws are
   compared before and after and are untouched; idempotency is asserted directly. Log bytes
   are not compared (MINOR-1). Startup is the only call site (MINOR-6).
5. **list_unresolved_limits** PASS. The anchor is the latest closed shift by `seq DESC`
   (`shiftwork/store/repo.py:651-657`) and the coupling to `cause_refs[0]` is consistent with
   the producer, which sets `cause_refs=(facts.shift_id,)`
   (`shiftwork/ledger/reducer.py:155`). No closed shift returns `[]`. Ordering is
   first-appearance by seq and deduplicated (`:670-677`). A later close declaring zero limits
   empties the projection while the earlier event survives:
   ```
   PROBE G after close1 unresolved_limits: ['LIMIT-A']
     after close2 (zero limits) unresolved_limits: []
     LIMIT_DECLARED events still stored: 1
   ```
   Proved by row `limits_projection_unions_all_declarations`; that row's mutation is now
   syntactically valid (`if True` inside the set comprehension), so the
   `MISTAKES.md` 2026-09-20 SyntaxError defect is fixed.
6. **Inherited CLOSED_UNRESOLVED incidents** PASS. Resolve twice is impossible: the UPDATE is
   state-scoped to OPEN and CLOSED_UNRESOLVED (`shiftwork/store/repo.py:503-514`) and
   `_resolution_drafts` skips RESOLVED (`shiftwork/orchestrator.py:453-455`). Resolve without
   the drawn unseen variant passing is blocked at `:465-468`. Resolve against the opening
   version is blocked at `:462-464`. All three are proved by dedicated rows
   (`resolution_gate_acceptance_removed`, `resolution_gate_regression_removed`,
   `resolution_gate_version_removed`) plus the three new CLOSED_UNRESOLVED rows.
7. **Pre-proof demo and evidence file** REVISE. Kill 1 substance holds and its socket block
   is failing-capable (PROBE E); wording issues at MINOR-3. Kill 5 is MAJOR-1. Kill 3 is
   MAJOR-2. The demo cannot exit 0 on a FAIL verdict:
   ```
   PROBE F forced-fail result string: PRE-PROOF FAIL (conditional on the offline executor: kill condition 2 deferred to Slice 14)
     statuses: ['FAIL', 'DEFERRED TO SLICE 14 (offline partial)', 'PASS', 'PASS', 'FAIL']
     main() would return: 1
     empty comparison -> kill5: FAIL | result: PRE-PROOF FAIL (...)
   ```
   Every other sentence of the evidence file was checked against what the code computes and
   reproduced; the file regenerates byte-identically. The leak scan is MAJOR-3.
8. **The 11 new mutation rows and the 38/38 claim** PASS. The row list has exactly 38 unique
   names, and rows 28 to 38 match the 11 names in `00-status.md:2520-2524` one for one. The
   harness ran to completion twice, 38/38 both times, every row `sha256_restored=True`, no
   SKIP, NOT_CAUGHT or CAUGHT_INCIDENTAL. Each row's pattern matched exactly once, which the
   harness enforces (`tests/mutation_proofs.py:521-523`). No two rows mutate the same
   pattern. Three rows (32, 33, 34) name the same expected test, which is one test guarding
   three distinct branches in three files, not two checks catching one fault. The harness
   requires an assertion-level catch parsed from junit (`:458-469`, `:575-581`), so the
   Slice 7 vacuous-row defect class is structurally excluded.
9. **Every number in the two Slice 8 status sections** PASS except MAJOR-6. Reproduced
   exactly: 192 passed / 1 skipped; 38/38; the 11 row names; PRE-PROOF PASS with its
   conditional suffix; 36 stored / 36 rescored / identical=True; ledger VALID with 37 events;
   ver-0002 with 5 files; 18 incidents and 18 resolutions; 9 held-out rows; 87 surfaces and
   0 leaks. Seam section reproduced exactly at `a481479`: 179 passed / 1 skipped; 27/27;
   seven seam rows; and all five demo lines including the `44abb79897239264...` artifact hash
   and the 6 pass / 0 fail and 0 pass / 6 fail transcript results. The three pre-existing
   unused imports the cleanup scan reported are real: `DrawState` appears only at
   `shiftwork/orchestrator.py:37`, `Run` only at `shiftwork/ledger/reducer.py:28`, and
   `json` in `demos/repair_loop.py:24` is shadowed by `json=` keyword arguments at lines 52,
   76, 93 and 98.

## Mandate B: rewrite table

I deleted nothing. One assertion proved vacuous was strengthened rather than deleted,
because the test around it carries other assertions that are independently failing-capable
(M8 proved the 409 refusal, and rows 35 and 37 cover its limits and incidents assertions).
Deleting the test would have destroyed real coverage.

| Test | Proof it was vacuous | Action | Suite before | Suite after | Mutation before | Mutation after |
|---|---|---|---|---|---|---|
| `tests/orchestrator/test_close_inheritance.py::test_open_shift_seeds_from_inheritance`, assertion `draft["files"] == inherited.files` | Mutation M3 replaced `orchestrator.py:173` seeding with the shipped template; pytest reported `1 failed, 1 passed` and this test was the one that passed. The `driven` fixture froze the unedited template, so inherited files equalled template files. | Rewrote the `driven` fixture to PUT a learner edit before freezing, plus a fixture guard that the frozen files differ from `BOOKSHOP_DRAFT_FILES`. Production untouched. | 192 passed, 1 skipped (46.93s) | 191 passed, 1 skipped excluding packaging (37.00s); full suite 1 failed, 191 passed, 1 skipped, the failure being test 51's 900s install timeout | 38/38 | 38/38 |

Post-fix re-probe of the same mutation M3: `1 failed`, assertion-level, message
`assert {'contract.js..._forever()\n'} == {'contract.js...ited draft\n'}`, file restored to
`sha256 c91200cb55ad707b44785dd3016be199864ec90b0e73ec11ae6740c404c02cf7`.

No mutation row was deleted or re-homed; the change added no test and removed none, so every
row's expected test still exists and still fails at assertion level.

### Failing-capability map for every Slice 8 test

| Slice 8 test | Proof it can fail |
|---|---|
| `test_run_binding.py::test_snapshot_pins_and_authored_pairings_match_the_fixtures` | row `snapshot_pin_edited` |
| `test_run_binding.py::test_run_row_adapter_is_load_bearing` | row `resolution_ignores_run_row` |
| `test_run_binding.py::test_unmapped_pairing_fails_closed_without_invoking_an_adapter` | row `unmapped_pairing_falls_back_to_the_batch` |
| `test_run_binding.py::test_unimplemented_adapter_fails_closed_before_execution` | row `unimplemented_adapter_falls_through` |
| `test_run_binding.py::test_route_persists_the_controller_configured_adapter` | row `route_ignores_the_configured_executor` |
| `test_ledger.py::test_restart_reconciles_nonterminal_runs_keeping_captures_and_draws` | row `reconcile_marks_nothing` |
| `test_ledger.py::test_restart_keeps_a_committed_finalized_run` | no row; probe M1, assertion-level |
| `test_thin_path.py::test_declared_limit_is_inherited_and_never_becomes_an_evaluator_rule` | no row; probe M2, assertion-level |
| `test_close_inheritance.py::test_unresolved_limits_follow_the_latest_close` | row `limits_projection_unions_all_declarations` |
| `test_close_inheritance.py::test_close_declares_the_inherited_limits_when_a_shift_never_froze` | row `close_version_fallback_removed` |
| `test_close_inheritance.py::test_close_shift_records_unresolved_limits` | rows `close_idempotency_removed`, `close_leaves_incidents_open`, `board_hides_closed_unresolved` |
| `test_close_inheritance.py::test_open_shift_seeds_from_inheritance` | no row; 409 refusal proved by M8; draft seeding was vacuous, fixed, proved by M3 re-probe; board version assertion only incidental (MAJOR-5); ledger_totals assertion tautological (MAJOR-2 shape) |
| `test_close_inheritance.py::test_close_refuses_while_a_run_is_in_flight` | row `close_in_flight_refusal_removed` |
| `test_close_inheritance.py::test_concurrent_closes_write_one_event_set` | no row; probe M4, assertion-level |
| `test_close_inheritance.py::test_close_fault_leaves_neither_partial_close_nor_partial_events` | no row; probe M5, assertion-level |
| `test_close_inheritance.py::test_inherited_unresolved_incident_resolves_on_a_later_passing_run` | rows `resolution_ignores_closed_unresolved`, `drawn_cases_skip_closed_unresolved`, `resolve_incident_only_from_open` |
| `test_test1_preproof.py::test_full_budget_preserves_unseen_inherited_case` | row `start_run_ignores_the_inherited_version` and probe M3; its leak scan is unproved (MAJOR-3) |
| `test_test1_preproof.py::test_next_shift_needs_the_six_variant_inventory` | no row; M6 incidental, M6b assertion-level (MINOR-5) |

Hollow-pattern grep across the Slice 8 test files found no `assert isinstance`, no bare
`except:`, no `pytest.skip` or `xfail` without a slice assignment, and no loop whose body can
silently not run: every collection iterated in the new tests is guarded by a preceding
non-emptiness assertion (`assert declared`, `assert incidents`, `assert results`,
`assert len(results) == 2`, `assert future_texts`) or by a following equality that an empty
collection would break. The one exception is the `ledger_totals` comparison at
`tests/orchestrator/test_close_inheritance.py:268-273`, which would pass on an empty event
list; in the fixture the list is never empty because the failing run opened three incidents.
The three modified leak tests each kept and strengthened their non-emptiness guard
(`tests/api/test_host_path_env_isolation.py:211`, `tests/sealed/test_sentinel_leak.py:215`,
`tests/sealed/test_payload_manifest.py:284`), and the seam's edits to them dropped only the
`THIN_TRANSCRIPT` redirection and renamed `open_incidents` to `incidents`; no assertion was
removed.

## Could not verify

- `00-status.md:2430`, "baseline before the seam: 174 passed, 1 skipped". Verifying it needs
  a checkout of `7db53f8`. I verified the seam commit itself (179 / 1) in a detached temp
  worktree but did not extend that to its parent.
- `00-status.md:2562-2563`, "Two unused imports in the new test files were removed
  (`contextlib`, `pytest`)". Both files are untracked, so there is no diff to inspect.
  `test_close_inheritance.py:16` does import `pytest` and uses it at lines 89 and 366, and
  `test_test1_preproof.py` imports neither name, which is consistent with the claim but does
  not prove it.
- `00-status.md:2559-2567`, that the architect-reviewer post-slice cleanup scan actually ran.
  Its three concrete sub-claims about pre-existing unused imports I did verify as accurate
  (see Mandate A item 9); the scan itself leaves no artifact.
- Whether test 51's install failure is transient or persistent. One pass and one 900s timeout
  is not enough to characterize it, and each attempt is a real network install, which
  `AGENTS.md` S3 keeps separately authorized. Reported as flaky per `AGENTS.md` S6.
- Token Factory, Nemotron, Tavily and any real-sandbox behavior. Out of Slice 8 scope and
  correctly marked deferred in both the status section and the evidence file.

## What I tried that did not break

Recorded so the author does not redo it: two concurrent closes on separate connections; a
close with a QUEUED, a RUNNING and a CAPTURED run; a close whose shift never froze; a later
close declaring zero limits; a duplicated declared limit; cross-engagement version fallback
with a second seeded engagement; reconcile against a FINALIZED run; reconcile twice; a
mid-transaction commit injected into close; a fault at each of the three close boundaries;
removing the board's inherited-version fallback; removing the second-open refusal; removing
the open_next_shift seeding; removing the rotation-exhaustion raise; changing the
RotationUnavailable HTTP mapping; dropping an event from the shared ledger reader during the
board-versus-replay comparison; a forced FAIL verdict through `_verdict` and the exit-code
mapping; an empty causal comparison; injecting a future customer sentence into a collected
serialized surface; and a socket open inside the scoring phase. Every production guard held.
The only things that broke were evidence sentences and one test assertion.

## Worktree state left for the author

`git status --short` reports 32 entries, the same set as at the start of this review, plus
this file. The only content change I made is the `driven` fixture in
`tests/orchestrator/test_close_inheritance.py`. Every production file I mutated during
probing was restored and verified byte-identical by sha256:

```
OK   shiftwork/orchestrator.py c91200cb55ad707b44785dd3016be199864ec90b0e73ec11ae6740c404c02cf7
OK   shiftwork/store/repo.py   e0cd7d728891f1312c423cc5d9e8f33dad7206d99cf2247559fb952e81f1661a
OK   shiftwork/ledger/reducer.py 83b745e4d49b1ec5527a41b7c8fb9dca71f2f04bc6f21d9c2f85237bbadad93a
OK   shiftwork/sealed/rotation.py 13e4c85deb40db65a8aaf8fab3724980071da3d465a60a6594d4fc9105eb836b
OK   shiftwork/domain/errors.py 02a0ee5c2c0cd10cdbef20e9f74e573d592b2690e69b931c36cc24bfc5d39fb4
```

Nothing was committed, staged, stashed, pushed or discarded. The temp worktree used for the
seam verification was removed and `.git/worktrees` pruned; `git worktree list` shows only the
main worktree. The regenerated evidence file was written to a temp path, so
`docs/plans/shiftwork/evidence/test1-central-mechanism.md` is the author's original.
