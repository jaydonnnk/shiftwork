# Mistakes Log

## 2026-09-29 S17 stale station label and ambiguous test patch

- What happened: the service station's activation handler overwrote the new
  selected-version label with the latest saved version and called it a baseline.
  A later test edit also placed failed-comparison assertions inside another
  test's `finally` block; inspection caught that before a run.
- Root cause: I changed one render path without checking the second writer, and
  used a patch anchor that matched a generic `finally` block.
- Prevention rule: search every writer of a changed UI label and inspect the
  rendered result; use function-specific patch context and read the edited
  block before testing.

## 2026-09-29 S17 Compare panel crashed before the first board load

- What happened: the browser check stayed in `loading` because `renderCompare()`
  treated two absent optional IDs as an existing selection, then read a property
  from the null board. The browser's page exception identified the line.
- Root cause: optional chaining returned `undefined` for both values, and
  `undefined === undefined` was true.
- Prevention rule: when comparing optional IDs for identity, require the owning
  object to exist before comparing. Exercise the initial empty render in the
  browser, not only the loaded state.

## 2026-09-28 Slice 15 render-fault run could not tell its preview from a foreign server

- What happened: the first `render_faults.mjs` run after the protected-phase
  client change reported `0 of 12 as expected`; every row failed at page load
  with `Expected ready, got undefined`. The preview script prints its banner
  line before uvicorn binds the port, so a port already held by another local
  application is indistinguishable from a healthy preview at start time, and
  the browser talks to whatever answers. A foreign app (an unrelated
  WorkBuddy/CareRelay service) was found listening on the fixed default port
  8137 minutes later; the same checks pass against a manually started preview
  and on a free port.
- Root cause: the harness treated the banner line as proof of reachability, and
  the fixed default port let a collision with an unrelated local application
  misattribute every row's failure to the product.
- Prevention rule: after spawning a server whose banner precedes its bind,
  poll that server's own endpoint until it answers before running any check
  (now `waitReachable()` in `render_faults.mjs`), and run preview checks on a
  port verified free when the default is in doubt; a port collision is a
  harness-environment failure, never a red product row.

## 2026-09-28 Slice 15 compare-demo harness kept the pre-protected copy assertion

- What happened: the first `--compare-demo` run after the protected-phase round
  exited 1 at `Slot 1 renders the wrong frozen batch size`. The slot row copy
  had changed to `N public requests + M protected steps`, while the harness
  still asserted the old `N request` substring, so the assertion could no
  longer match a correct render. The harness was updated to the rendered copy
  and gained a protected-step limb with its own served-source fault row
  (`slotProtectedCount`); the rerun passed.
- Root cause: the client copy changed during the protected-phase round without
  its browser assertion being updated in the same change, and the browser check
  was deferred, so the staleness surfaced only when it was finally run (the
  same client-untested-with-shell-contract pattern as the 2026-09-26 Slice 11
  entry).
- Prevention rule: when a client rendering change alters value-bearing copy
  that a browser assertion reads, update that assertion and add its fault row
  in the same change; run the browser check before claiming the tree complete
  rather than leaving it as a pending item across a round boundary.

## 2026-09-28 Slice 15 protected-phase guards masked four older proof rows

- What happened: the protected-phase round added a cluster of guards on the
  comparison path (a frozen context-hash re-verification, a protected-ordinal
  tie, a readback that raises on a missing snapshot) and rebuilt its own proof
  rows, but the first full run under the hardened driver found four older rows
  had silently lost proof-grade status: the snapshot write-removal row was
  `CAUGHT_INCIDENTAL` (the reservation readback raises `InvalidSealedCase`
  before any assertion), and the manifest count row and both slot-binding rows
  were `NOT_CAUGHT` (the frozen context-hash re-verification catches every
  context tamper globally, and the count tamper also trips the protected-ordinal
  tie). Focused per-round checks had stayed green because each row still ran.
- Root cause: a new guard placed earlier in a shared path changes which
  mechanism catches an old row's tamper; the row's named assertion no longer
  observes anything, and a focused run cannot distinguish a row that proves its
  guard from a row whose tamper is caught elsewhere.
- Prevention rule: after adding a guard on a path that existing rows anchor
  onto, re-run the full harness on the settled tree and treat any previously
  green row that flips to `NOT_CAUGHT` or `CAUGHT_INCIDENTAL` as masking to be
  re-anchored. Re-anchor the row onto its own guard's limb with a tamper that
  only that limb catches (here `[slot_hash]` for the slot binding,
  `[extra_request_with_recomputed_pin]` for the count check and
  `[wrong_request_id_with_recomputed_pin]` for the request-line identity), and
  give the masking guard its own row so it is proven too.

## 2026-09-28 Slice 15 two proof shapes measured unprovable

- What happened: repair attempts produced two fault shapes that cannot reach an
  assertion-level catch. (1) A remove-the-write mutation for the protected-case
  snapshot write reads as the reservation readback's `InvalidSealedCase` under
  every reachable shape (`CAUGHT_INCIDENTAL`), so no assertion observes the
  write. (2) The slot-count limb
  (`workload.request_count != slot.request_count`) has no failing-capable
  tamper: with the limb removed, the `[slot_count]` update is caught only by
  the comparison view's private-material guard raising `LifecycleError`
  ("public comparison evidence contains private material", measured
  `CAUGHT_INCIDENTAL`). (3) The original count-check tamper
  (`wrong_claimed_count`) set `request_count` to 1, which trips both the
  recomputed count check and the protected-ordinal tie, so it could prove
  neither.
- Root cause: each shape was chosen for what it removes, not for the unique
  divergence it produces; overlapping guards meant the tamper's first
  observable failure was never the limb under test.
- Prevention rule: before claiming a row, construct the tamper so the limb
  under test is the only reachable divergence (recompute every other pin, keep
  every other check satisfied) and measure the candidate shape; when a removal
  stays green or turns incidental, record the limb as unproven (or retire the
  row onto a provable limb) instead of counting the red run as coverage.

## 2026-09-28 Slice 15 mutation run crashed at row 95 and left a stranded mutation

- What happened: the 96-row mutation proof run crashed while restoring
  `shiftwork/orchestrator.py` after the `s15_protected_counts_before_terminal`
  row: `OSError: [Errno 22] Invalid argument` on the restore write. The mutated
  file stayed on disk (the mutation is valid Python, so it still compiled), and
  because stdout was block-buffered into a redirected log, the crash discarded
  every completed row's output, so the run produced no usable result table. The
  stranded mutation was found by re-running the anchor check over all 96 rows
  (exactly one anchor broken), reverted byte-precisely, and the focused tests
  passed again.
- Root cause: two compounding hazards. (1) a Windows write to this
  OneDrive-synced tree can transiently fail with `EINVAL`, and the shared
  runner's restore has no retry, so the row's own `finally` died. (2) the
  runner prints per-row progress with `end=" "` and the final table only; when a
  crash happens mid-list, buffered per-row evidence is lost along with the run.
- Prevention rule: run the mutation harness with per-row flushed output and a
  results file appended after each row, so any crash preserves the completed
  rows and names the failing one. After a crashed or interrupted run, never
  trust the tree: re-check every row anchor against the working tree, compile
  every target, revert the identified stranded mutation byte-precisely, and
  treat the run as not a pass.

## 2026-09-28 Slice 15 reservation fault test assumed the wrong SQLite error class

- What happened: the new fault test correctly reached the reservation-link
  UPDATE but failed because the SQLite trigger raised `IntegrityError` while
  the assertion expected `OperationalError`.
- Root cause: the test assumed all injected database faults share one SQLite
  exception subtype, despite `RAISE(ABORT, ...)` using an integrity error.
- Prevention rule: match the distinctive injected message and the `sqlite3.Error`
  family when the proof spans both Python-raised and trigger-raised faults.

## 2026-09-28 Slice 15 execution claim: stale fault and mutation targets

- What happened: after moving the comparison's `RUNNING` transition from
  reservation to the worker claim, the focused suite still injected a fault
  into the removed reservation-time state update and failed. The first mutation
  run also had one exact-byte anchor that no longer matched mixed line endings
  and one `expect` field written as an assertion message instead of a test ID.
- Root cause: I changed the write boundary without updating its fault target
  and proof metadata in the same edit, and I did not inspect the mutation
  runner's exact-byte and test-selector rules before editing the rows.
- Prevention rule: when moving a durable write across a lifecycle boundary,
  remap its fault injection to a real write at that boundary and remeasure the
  source bytes used by mutation anchors. The runner's `expect` names the
  failing test, not the message. Run the full proof and retain its exit status.

## 2026-09-27 Slice 15 browser proof: a wait condition true on the initial render hides a swallowed click

- What happened: `node tests/client/browser.mjs ... --compare-demo` exited 1 with
  `CDP timeout: Runtime.evaluate`. Byte-level instrumentation of the page function
  showed `wait('candidate A freeze')` returning at 0.00s while the candidate list
  still read `not frozen yet`: its condition `textContent.includes('Candidate A')`
  is true from the first render, and `'Candidate A\nnot frozen'` never matches
  because the row renders `Candidate Anot frozen yet`. The script therefore clicked
  freeze B while `state.pending` had disabled the button; the click was swallowed and
  candidate B never froze.
- Root cause: the wait asserted a substring the initial render already satisfies
  instead of the state the click is supposed to produce. A wait that can pass before
  its action completes is not a wait.
- Prevention rule: a wait condition must be false immediately before the action it
  follows and true only after that action's rendered effect; read the initial
  render's text before choosing the condition. Gate every click on the control being
  enabled, and make each in-page wait name its own limb when it times out.

## 2026-09-27 Slice 15 browser proof: a transport timer shorter than the page deadline replaced the real error

- What happened: the harness's CDP send timer (20s) fired before the page function's
  own 60s polling deadline, so three separate page-level defects all reported the same
  opaque `CDP timeout: Runtime.evaluate`; the last written screenshot was the only
  clue to where execution stopped.
- Root cause: the transport backstop was shorter than the longest in-page deadline, so
  the transport always failed first and hid the page's own error message.
- Prevention rule: a transport-level timeout must be strictly greater than the longest
  deadline of any page function it awaits (now `CDP_TIMEOUT_MS = 90000` against a 60s
  in-page ceiling). When a timeout message names only the transport method, treat the
  real error as hidden and instrument the page function before choosing a fix.

## 2026-09-27 Slice 15 browser proof: rendered rows matched on an identity that duplicates

- What happened: after the first two repairs the run failed `Slot 1 task row does not
  match the API payload for alternative`. A two-request workload assesses each task
  once per request, so `task_id='alternative'` appeared twice with the same verdict
  (`pass`) and different outcomes; the finder matched task_id plus verdict and
  returned the ordinal-1 row for both payload entries.
- Root cause: the rendered row's identity (task_id + verdict) was not unique for the
  data it displays. The diagnostic path assesses one pinned request per task, so the
  collision never appeared there.
- Prevention rule: before matching rendered rows to payload entries, check that the
  payload's identifying keys are unique per row for the widest input the surface
  accepts (here more than one request per workload), and expose any missing key as
  both a dataset attribute and displayed text so each limb is failing-capable.
## 2026-09-27 Slice 14: live assist probe used a mismatched investigation

- What happened: all three authorized live assist calls used a source request about Dune shelf availability, while the submitted learner cause asserted a price, collection and alternatives failure. The model repeated or expanded the unsupported tasks.
- Root cause: I copied a generic test investigation into the live probe without first reading the chosen recorded request and response.
- Prevention rule: before spending an authorized live-call budget, read the exact source request and capture, then write a probe investigation about that evidence; keep model agreement with a bad premise as a separate quality finding.

## 2026-09-27 Slice 14: assist test expected the wrong run status

- What happened: the first assist suite stopped in setup because POST runs returned 202 Accepted and the new fixture asserted 201.
- Root cause: I assumed the route's status instead of checking the existing API contract before writing the fixture.
- Prevention rule: read the route's declared status or reproduce it in a small request before asserting it in a new integration fixture.

## 2026-09-27 Slice 14: gateway unit test kept an invalid role argument

- What happened: after the gateway began enforcing the AssistRole enum, its direct-call test still passed a string and failed with ASSIST_ROLE_INVALID.
- Root cause: I tightened the gateway contract without updating the direct test call in the same edit.
- Prevention rule: when adding an input type guard, update direct callers and add a separate test that the rejected type actually fails before any transport call.

## 2026-09-27 Slice 14: old absence guards failed after the assist package landed

- What happened: the offline suite reported two failures because Slice 6 guards still asserted that shiftwork/assist did not exist.
- Root cause: I added the new package before replacing the deferred import and prompt arms with tests against the real S14 surfaces.
- Prevention rule: when a deferred directory or route lands, find its absence guards in the same edit and replace them with non-vacuous tests that inject a detectable fault.

## 2026-09-27 Slice 14: reply metadata changed positional argument meaning

- What happened: adding reported-model metadata made two recorded test replies pass a numeric token count as the model ID. The tests still passed because they asserted other fields.
- Root cause: optional metadata fields were positional in a dataclass that grew during implementation.
- Prevention rule: make optional reply metadata keyword-only and name token counts explicitly in test fixtures.

When a coding error occurs, log it below with: what happened, root cause, and prevention rule.
When a failure pattern repeats 4+ times, graduate it into a permanent rule in `agents.md`.

---

## 2026-09-16 — Gate 4 slice plan mapped tests by number, not by clause

- **What happened:** `04-slices.md` marked tests 9, 10, 18, 23, 44 and the prompt/assist
  arms of 16/17 as fully "landed" in slices where some of their specified assertions
  cannot execute yet (e.g., test 9's reservation-retention clause needs `rotation_draws`,
  which lands two slices later), and orphaned three clauses of test 41. Caught by the
  user-requested independent review (verdict: REVISE — GATE 4), not by my own checks —
  my coverage check counted test numbers, not clauses.
- **Root cause:** I verified coverage at the test-number level ("all 49 appear in some
  slice") instead of decomposing each test specification into its assertion clauses and
  checking that every clause's prerequisites (tables, modules, flows) exist in the slice
  where it is claimed.
- **Prevention rule:** when mapping a numbered test/spec plan onto slices or milestones,
  enumerate each test's individual clauses and verify each clause's dependencies exist at
  the claiming step; annotate partial landings explicitly ("partial: X clause completes at
  step N") and name the step that completes every partial. A count-level coverage check is
  not sufficient evidence of coverage.
## 2026-09-17 — Clause-level coverage repair verified only the clauses a reviewer named

- **What happened:** after the first Gate 4 review fixed the named partial-landing
  tests, both the drafter's repair and the reviewer's re-check missed test 18's
  "absent from every prompt" arm (still orphaned), test 43's ledger-resolution
  clause and test 44's evaluator-rule clause (claimed while those layers were
  mocked). A second cold review caught all three, plus two real Gate 3 defects
  (test 33 close-semantics ambiguity; no test for Test 1's credential-reachability
  kill condition) that two prior review rounds had passed.
- **Root cause:** the repair and its verification were scoped to the findings list
  instead of re-decomposing the full specification text of every affected test and
  every kill condition; "previous reviewer passed it" was treated as evidence.
- **Prevention rule:** when annotating partials or verifying a coverage repair,
  re-decompose the FULL spec text of every annotated test (and every kill condition
  of every proof) at both the claiming and the completing step — not only the
  clauses a reviewer named. A prior PASS is not evidence for clauses it never
  enumerated. (Second occurrence of the clause-mapping pattern; at 4 occurrences
  graduate into agents.md.)
## 2026-09-17 Slice 1 test 51: logged a transient, unreproduced OS-policy block as a standing fact

- **What happened:** the Slice 1 evidence note and this log recorded that test 51's
  stdlib-venv path "is blocked on this machine by Windows Application Control
  (WinError 4551)" and that the test "exercised its uv fallback." A re-run on
  2026-09-17 (`pytest tests/packaging -q -s`) printed `clean-env mechanism:
  stdlib venv + pip` and `1 passed in 21.47s`, and a direct probe of a freshly
  created stdlib venv returned exit 0. The stdlib path works and is selected; the
  uv fallback never ran. An independent review caught the false claim, not my own
  checks.
- **Root cause:** I recorded a single transient `WinError 4551` observation as a
  durable machine property, and asserted which code path executed without
  capturing the test's own `clean-env mechanism:` line. The note also contradicted
  itself: "no install ran this session" alongside "test 51 passed," when test 51
  performs a clean-env install into a fresh temp venv by construction.
- **Prevention rule:** when an evidence note states which mechanism, branch or
  fallback ran, quote the program's own verbatim output (the mechanism line and the
  pass/skip/fail count) instead of inferring it. Treat a one-off OS or policy error
  as transient until reproduced; never log it as a standing property. A test that
  installs into a fresh environment is an install: do not write "no install ran" in
  the same note that records it passing. Packaging checks may still probe a fresh
  interpreter and keep a uv fallback for genuinely blocked machines, but record the
  fallback as exercised only when the probe actually failed.
## 2026-09-18 Slice 2 evidence note asserted a runtime shiftwork.db that never existed

- **What happened:** the Slice 2 evidence note recorded "the runtime `shiftwork.db` were
  left untouched" and described "a stale git-ignored dev `shiftwork.db` left at version
  1", implying an existing file. No `*.db` file exists anywhere in the tree or in git
  history, and none was created; the demos and tests point `create_app` at temp paths.
  An independent hostile review caught it, not my own checks.
- **Root cause:** I wrote a file-state claim from assumption instead of running a check;
  no command output backed the existence claim, and guard behavior ("a database left at
  version 1 raises ...") was allowed to read as an observed file.
- **Prevention rule:** every file-state claim in an evidence note ("exists", "left
  untouched", "pre-existing", "created") must be backed by the command that shows it
  (`git status --porcelain`, `find . -name '*.db'`, `git ls-files`). When the evidence is
  a counterfactual guard, say the database was constructed for the check. Second
  occurrence of the unverified-state-as-fact pattern (first: the 2026-09-17 WinError
  4551 entry); at 4 occurrences graduate into `agents.md`.

## 2026-09-18 Slice 3: environment trap broke the test runner

- **What happened:** the first executor suite ended with `8 failed, 17 passed, 1 skipped, 11 errors in 17.62s`; the recorded-adapter test replaced global `os.environ` while asyncio created its loop and pytest reported results, causing `TypeError: 'types.SimpleNamespace' object is not subscriptable` and masking conformance diagnostics.
- **Root cause:** a process-global fault injection outlived the boundary under test, and the replacement did not implement the mapping protocol.
- **Prevention rule:** create framework resources before a global trap, scope the trap to the adapter call with guaranteed restoration, and restore normal state before framework teardown or reporting.

## 2026-09-18 Slice 3: fixture log bytes depended on Windows newline translation

- **What happened:** the isolated conformance check reported `1 failed, 1 passed in 1.09s`; live logs were `b'trusted fixture ready\r\n'` while the authored transcript pinned `b'trusted fixture ready\n'`.
- **Root cause:** the fixture used text-mode stderr without pinning newline encoding, so the OS changed the emitted bytes.
- **Prevention rule:** fix fixture output encoding at the producer; preserve captured bytes and exact-equality assertions rather than normalizing away evidence differences. Recompute fixture pins only after reviewing the producer change.

## 2026-09-18 Slice 3: refusal fixture deadline expired before Winsock refused

- **What happened:** executor checks reported `2 failed, 28 passed, 1 skipped in 17.87s`; port-dead and connection-refused cases timed out instead of observing refusal.
- **Root cause:** their 2-second whole-run deadline was shorter than the measured OS refusal delay. A direct 8-second-timeout loopback probe printed `bound_not_listening ConnectionRefusedError winerror= 10061 elapsed_ms= 2047` and `closed ConnectionRefusedError winerror= 10061 elapsed_ms= 2014`.
- **Prevention rule:** separate the deliberate timeout case from refusal tests; allow refusal tests enough time to observe the real socket error. Keep typed expectations unchanged and retain a short real deadline for the timeout case.

## 2026-09-18 Slice 3: trusted sources hidden by a build-output ignore rule

- **What happened:** `git check-ignore -v shiftwork/fixtures/artifacts/bookshop/service.py` printed `.gitignore:23:artifacts/\tshiftwork/fixtures/artifacts/bookshop/service.py`; the new executable fixtures existed locally but were absent from the reviewable untracked-file inventory.
- **Root cause:** the pre-existing unanchored build-output rule also matched the approved source-fixture directory.
- **Prevention rule:** check ignore status for new source directories and add a narrow source exception before treating the diff as reproducible.

## 2026-09-18 Slice 3: snapshot pin depended on pre-checkout CRLF bytes

- **What happened:** the checkout-format regression printed `1 failed in 0.83s`; the byte probe found `thin_stale.json` and `bookshop_snapshot.json` still using CRLF. The snapshot's current hash was `ad18bf6fce6b2742b963d728ce60b0988b4d954b903d638cb1777ec7c42cdf12`, but the declared LF checkout would hash to `bd66a4136c8dc1156ff50645195d437328cb3ea18206be9eba976d3ea168933f`.
- **Root cause:** exact-byte pins were computed before aligning existing fixture files with the new `.gitattributes` LF rule; local green tests did not prove checkout reproducibility.
- **Prevention rule:** assert byte-addressed source files already use their declared checkout newlines before freezing hashes; correct source bytes and explicit pins, never normalize captured response evidence.

## 2026-09-18 Slice 3: replay trusted contradictory transport metadata

- **What happened:** the adversarial review reproduced a replay with no HTTP status reaching FINALIZED and a ledger event; unmarked non-UTF-8 bytes instead reached evaluation, raised and lost their captured evidence on rollback. Invalid log base64 and conflicting failure kinds were also accepted.
- **Root cause:** request/snapshot hashes and capture order were checked, but transport metadata was trusted independently of body/log bytes and run failure state.
- **Prevention rule:** test malformed replay metadata as well as golden transcripts; validate transport consistency before success and retain unmarked non-UTF-8 bytes through the typed executor-failure path, never business evaluation.

## 2026-09-18 Slice 3: migration DDL committed before its version marker

- **What happened:** a review probe denied the version-write statement after adding `log_ref`; reopening left schema version 2 with the new column, and the next startup failed with `duplicate column name: log_ref`.
- **Root cause:** SQLite committed the ALTER TABLE independently because no explicit transaction enclosed both the DDL and schema version update; the original test covered only uninterrupted repetition.
- **Prevention rule:** commit migration DDL and its version marker atomically; inject a failure between them, reopen the database and assert unchanged data plus a successful retry.

## 2026-09-18 Slice 4 sealed family enforced a freshness limit no learner-visible artifact stated

- **What happened:** the `stale_information` evaluator keyed its stance failures off
  `max_record_age_ms`, `stale_assert_kinds` and `high_risk_kinds` stored only in the
  sealed case block. Failing-transcript request 1 answered from the newest Dune
  record with its true age (90 minutes), exactly what the committed
  `USE_NEWEST_RECORD_WITH_AGE` label instructs, and was still scored
  `fail/STALE_BEYOND_RULE` against a hidden 3600000 ms limit. An independent
  execution review caught it (MAJOR-1); the family could not be sealed until the
  user chose a fix route (catalog v2 whose labels state the constants).
- **Root cause:** I treated the sealed `expected` block as a free parameter bag, so
  rule constants that change verdicts lived outside every learner-visible artifact,
  contradicting the approved rule that sealed cases check consistency with the
  learner's chosen option (03-program-design S3.2). The Slice 2 case note had
  attributed the limit to "the contract selected"; the six-case reshape dropped the
  attribution without noticing the number had no visible owner.
- **Prevention rule:** every sealed-case parameter that can change a verdict must be
  stated in a learner-visible artifact (catalog label, contract, snapshot) or be
  derived from one; keep rule constants in the visible artifact and pin them with a
  guard test (`test_v2_labels_declare_the_rule_constants`,
  `test_sealed_expected_blocks_carry_no_rule_parameters`).

## 2026-09-18 Slice 4 probe injection silently no-opped on CRLF worktree bytes

- **What happened:** to prove the revised test 11 closure scan was failing-capable, I
  injected `import socket` into `domain/canonical.py` with a byte replace on
  `b"import base64\n"`. The tracked file's worktree bytes are CRLF
  (`core.autocrlf=true`), so nothing was replaced and the probe ran green; the
  helper's "probe injected" line had been printed unconditionally. The mismatch
  surfaced when the probe removal also failed to match; I re-ran the probe with
  verified bytes and captured the real failure.
- **Root cause:** the probe asserted neither the mutated bytes nor the expected
  failing behavior, and its success message was not derived from the observed state.
- **Prevention rule:** a mutation probe must verify the mutation landed (bytes or
  behavior) before its result is trusted, and it must print the observed state, not
  a constant. On this machine, tracked-file worktree bytes are CRLF, so byte-level
  edits, pins and probes must match `\r\n` or normalize explicitly.

## 2026-09-18 Client visual brief patch omitted an added-line marker

- **What happened:** the first combined `apply_patch` call failed validation before
  changing any file because one wrapped line in the new-file hunk did not begin with
  `+`.
- **Root cause:** a large multi-file patch was assembled as one string without first
  checking every line of the add-file section for a patch marker.
- **Prevention rule:** create new files in a separate patch, keep multi-file patches
  small, and verify every line in an add-file hunk begins with `+` before applying it.

## 2026-09-18 Slice 5 test 6 claimed FULL while the linkage clause was not failing-capable

- **What happened:** the Slice 5 evidence claimed test 6 FULL for "every tamper
  (payload, hash, prev_hash, seq, reorder) is BROKEN", but the independent review
  removed `verify_chain`'s prev-hash linkage check (`chain.py:88-89`, byte-verified
  mutation) and the test still passed: the prev_hash tamper case is caught by hash
  recomputation (the digest covers prev_hash), so the load-bearing linkage check had
  zero failing-capable coverage. The reviewer proved linkage is load-bearing with a
  forged-but-self-consistent spliced event that only linkage catches.
- **Root cause:** clause coverage was claimed per named tamper input, not per
  verifying code path; two independent checks can catch the same injected fault, and
  a mutation probe on only the producer side (`append`) left the verifier clause
  unprobed. Third occurrence of the count-level-not-clause-level pattern
  (2026-09-16, 2026-09-17, this entry); at 4 occurrences graduate into `agents.md`.
- **Prevention rule:** when a test asserts a guard fires, mutate EACH guard branch
  independently and require a failure per branch; a tamper input that two checks can
  catch proves neither. For hash-chain verifiers, include a forged-but-self-consistent
  splice case alongside field-tamper cases.

## 2026-09-18 Slice 5 status claimed a per-run snapshot pairing that does not exist

- **What happened:** the Slice 5 evidence note said `finalize_run` "evaluates against
  the snapshot the run consumed". The independent review found no pairing mechanism:
  `finalize_run` reads the module global `config.BOOKSHOP_SNAPSHOT`, `execute_run`
  hardcodes the same constant into `shop_snapshot_ref`, and `Run` has no snapshot
  field. The actual fix shipped was making test/demo inputs cite that snapshot's
  records. A latent bug follows: a run consuming `bookshop_stale_snapshot.json` would
  finalize against the wrong snapshot.
- **Root cause:** the note described the intended invariant instead of the mechanism
  in the code; no read of `finalize_run`'s inputs backed the "the run consumed"
  phrasing. Third occurrence of the unverified-state-as-fact pattern (WinError 4551,
  Slice 2 runtime-db claim, this entry); at 4 occurrences graduate into `agents.md`.
- **Prevention rule:** evidence notes must describe the code path that exists
  (name the constant, field or function actually used), not the invariant it
  happens to satisfy today; when inputs coincide by configuration rather than by
  mechanism, say so and record the decoupling as a latent-bug note.

## 2026-09-18 Slice 6 host-path leak scan could never match the surface it scanned

- **What happened:** test 20's host-path needles were raw Windows absolute paths
  (`str(config.BOOKSHOP_SNAPSHOT)`, the package dir, the interpreter path), but a
  FastAPI JSON response backslash-escapes them (`C:\\Users\\...`), so
  `needle in surface` never matched. Six of the eight needles were vacuous and the
  test passed against a real leak: mutation probe 20b wired
  `str(config.BOOKSHOP_SNAPSHOT)` into a projected `request_text` and test 20 stayed
  green. Only test 45 caught it, and only because it also carried a
  backslash-free marker token. My own non-vacuity checks passed, because they
  counted surfaces scanned rather than proving any needle could match.
- **Root cause:** I wrote the absence assertion against the in-memory value without
  checking how that value is serialized on the surface being scanned, and I treated
  "the scan covered N surfaces" as evidence that each individual needle was capable
  of failing.
- **Prevention rule:** every absence/leak assertion needs a scanner self-test that
  injects the needle into a representative serialized surface and requires
  detection; a count of surfaces scanned is not evidence that a needle can match.
  Compare against the surface's serialized form, not the in-memory value. Fourth
  occurrence of the coverage-claimed-not-proven pattern (2026-09-16 clause mapping,
  2026-09-17 repair scoping, 2026-09-18 Slice 5 guard branches, this entry), so it
  is graduated into `AGENTS.md` S6 Verification. The graduated entries are kept
  here as incident history, per the AGENTS.md mistake-logging rule (user decision,
  2026-09-19).

## 2026-09-19 Slice 6 repair fixture written with CRLF by write_text

- **What happened:** the new `missing_evidence` transcript fixture was written with
  `Path.write_text` on Windows, which translated `\n` to `\r\n`; the LF-pinned
  fixture check in `tests/executor/test_conformance.py` failed on it.
- **Root cause:** text-mode writes on Windows apply `os.linesep` translation, and
  the repository pins fixture files as LF bytes.
- **Prevention rule:** write byte-pinned text fixtures with `write_bytes(...)` or
  `write_text(..., newline="\n")`, never default `write_text`, on Windows.

## 2026-09-19 Slice 6 review round: a self-test parametrized by the constant it tests

- **What happened:** the new UTF-16 decoder self-test was parametrized over
  `BASE64_DECODINGS`, the same constant it exists to guard. My failing-capability
  probe narrowed that constant to `("utf-8",)` and the probe reported
  `1 passed`: the utf-16 cases had disappeared instead of failing. The guard was
  vacuous for exactly the inputs it claimed, and only the probe's own expectation
  (a passing probe is a red flag) exposed it.
- **Root cause:** the test's input list came from the implementation artifact rather
  than from the requirement, so weakening the implementation weakened the evidence
  in the same step. Same class as counting surfaces scanned instead of proving a
  needle can match (the graduated AGENTS.md S6 rule).
- **Prevention rule:** a failing-capability check enumerates the requirement's
  literal inputs (the three encodings), never a constant read from the code under
  test, and asserts each input is still covered; when a mutation probe passes,
  treat the probe or the check as broken before concluding the guard is unnecessary.

## 2026-09-19 Slice 6 review round: the getattr rule rebuilt an AST call and lost lineno

- **What happened:** the `getattr(importlib, "import_module")` branch of
  `_dynamic_import_findings` replaced the original call node with a synthetic
  `ast.Call` built from the remaining arguments, so the "without a target argument"
  message raised `AttributeError: 'Call' object has no attribute 'lineno'` and the
  scanner self-test failed.
- **Root cause:** a node was reconstructed to drop its first argument without
  copying the source-location attributes.
- **Prevention rule:** never rebuild an AST node to drop arguments; keep the
  original node for locations and carry the remaining argument list separately.

## 2026-09-19 Slice 7: check-result-id ordinal double-counted within one transaction

- **What happened:** `finalize_run` assigned each CheckResult an id of
  `cr-{repo.count_check_results(conn) + len(check_results) + 1:04d}`. Because
  `count_check_results` queries the same connection inside the uncommitted
  transaction, it already sees the rows inserted earlier in the loop. Adding
  `len(check_results)` double-counted every result after the first, producing
  ids like cr-0001, cr-0003, cr-0006 instead of cr-0001, cr-0002, cr-0003.
  The bug was invisible while only one family was enabled (one result per run);
  it surfaced when Slice 7 enabled three families and the second result's id
  skipped.
- **Root cause:** I treated `count_check_results` as seeing only committed state
  (pre-transaction), but SQLite's default isolation lets a connection read its
  own uncommitted writes. The `len(check_results)` term was a redundant
  compensator for a problem that did not exist.
- **Prevention rule:** when an ordinal is derived from a COUNT on the same
  connection inside an open transaction, the count already includes this
  transaction's earlier inserts; do not add a local accumulator on top. Verify
  by checking the second iteration's id, not just the first.

## 2026-09-20 Slice 7 review round: a vacuous mutation proof and a harness that could not tell a crash from an assertion

- **What happened:** the `invalidate_state_filter_removed` proof dropped the SQL
  state clause but left the fourth bound parameter, so SQLite raised
  `ProgrammingError: Incorrect number of bindings supplied` on every call. The
  harness counted any non-zero pytest exit as FAIL_CAUGHT, so the row looked
  green. The reviewer corrected the mutation to valid SQL and the whole 27-test
  orchestrator+api suite passed: the state-scoping clause of
  `invalidate_rotation_group` was covered by no failing-capable test, because
  the only scenario exercised had exactly one active draw for the family, where
  the rowcount is 1 with or without the filter. Two more rows were caught only
  by incidental exceptions (ValueError from the removed shared-ordinal guard,
  a UNIQUE-constraint integrity error from the removed exposure filter), and
  the second `shared_ordinal` raise ("binds several request ordinals") had no
  test at all.
- **Root cause:** two compounding errors. First, a mutation that made the
  program invalid (binding-count mismatch) rather than changing behavior, which
  is the exact "require one real failure per branch, not a parse error" failure
  the verification rules warn about. Second, a catch signal (`returncode != 0`
  with `--tb=no`) that cannot distinguish an AssertionError, a collection
  error, or a runtime crash, so the proof could not detect its own vacuity. The
  suite also lacked the mixed-state scenario (one invalidated plus one active
  draw for the same family) that makes the filter load-bearing.
- **Prevention rule:** a mutation proof requires (1) a valid, behavior-changing
  mutation, (2) a named expected test that must fail, and (3) an
  assertion-level failure (AssertionError or pytest's `Failed: DID NOT RAISE`)
  parsed from the junit report, with vacuous, incidental and wrong-test catches
  failing the proof run. When a guard filters rows on state, seed both states
  in the test so the rowcount is observable, and verify a new or changed proof
  harness against known-vacuous and known-crashing mutations before trusting a
  green table.

## 2026-09-20 Slice 8: the offline replay rebuilt inputs from current state

- **What happened:** the first version of `demos/test1.py`'s offline re-scoring
  re-derived each run's sealed case set with `sealed_store.load_drawn_cases`, which
  reflects the incident state *today*. By the time the demo replayed shift 1, the
  incidents were resolved, so the regression cases were no longer loaded: the replay
  produced 18 CheckResults against 36 stored ones, `identical=False`, and the demo
  reported `PRE-PROOF FAIL` on a mechanism that was working. Loading the case set the
  run actually recorded (its stored check ids resolved through the sealed index)
  reproduced all 36 exactly.
- **Root cause:** I treated a live-selection helper as if it were a historical
  accessor. `load_drawn_cases` deliberately follows the current incident state (a
  resolved incident's stimulus is not re-scored), which is correct for a new run and
  wrong for replaying an old one.
- **Prevention rule:** when a check claims "the same inputs replay identically", the
  replay must reconstruct the exact inputs the run consumed - the rows the run wrote -
  never re-derive them with a selector that reads present state. Verify by comparing
  counts first (stored vs re-derived) before interpreting a mismatch as a mechanism
  failure.

## 2026-09-20 Slice 8: an invalid mutation written into the proof table

- **What happened:** the `limits_projection_unions_all_declarations` row replaced a
  comprehension's filter line with `if True:  # MUTATION`, which is a `SyntaxError`
  inside a comprehension. The run reported `NOT_CAUGHT` with `SyntaxError: invalid
  syntax` instead of a green row - the harness caught it, but the row itself was the
  defect, exactly the class of error the 2026-09-20 Slice 7 entry logged.
- **Root cause:** I wrote the mutation as if the target line were a statement, without
  re-reading the surrounding expression (a set comprehension).
- **Prevention rule:** before adding a mutation row, reproduce the mutated file in a
  scratch copy and require it to import/compile; a mutation must change behavior
  without changing syntax validity. When the target is inside a comprehension or
  expression, mutate only the expression itself.

## 2026-09-20 Slice 8: an edit inserted a block in the middle of a dict literal

- **What happened:** adding the `repair_arc_*` entries to
  `config.TRUSTED_LOCAL_FIXTURES` was done with an edit whose replacement re-declared
  the dict head, leaving the original entries after a closing brace - an invalid file.
  It was caught by reading the file after the edit, before any test ran.
- **Root cause:** the edit's old string ended at the dict's opening line, so the new
  string re-created that line while the original body stayed in place.
- **Prevention rule:** when an edit adds entries to a literal, replace the whole
  literal (head through closing bracket), not just its head; after any structural
  edit, re-read the region before running checks.

## 2026-09-20 Slice 8: verification re-run used the wrong Python interpreter

- **What happened:** a re-run of the full verification chain (`pytest`,
  `mutation_proofs.py`, `demos.test1`) used bare `python`, which on this shell
  resolves to a hermes-agent venv without pytest. The log showed
  `No module named pytest` instead of the expected suite result; the run was
  stopped and re-issued with `.venv/Scripts/python.exe`.
- **Root cause:** assumed the shell PATH's `python` is the project interpreter;
  in this environment it is not.
- **Prevention rule:** always invoke this repository's checks with
  `.venv/Scripts/python.exe` (or an activated `.venv`); a command that reports a
  missing tool or module is treated as a harness error to diagnose before any
  conclusion about the code. **Superseded 2026-09-26:** the `.venv` trampoline is
  blocked by Windows Application Control on this machine; use
  `.venv313/Scripts/python.exe` (see the 2026-09-26 interpreter-block entry).

## 2026-09-20 Slice 8: a killed mutation run left a mutation applied (false regression)

- **What happened:** the background verification chain (full suite -> mutation proofs
  -> pre-proof demo) was killed while its mutation phase was running. The harness was
  killed between mutating `orchestrator.start_run` and restoring it, so the worktree
  kept the `start_run_ignores_the_inherited_version` mutation. The next full suite
  reported 3 failures (one close test, both pre-proof tests) that looked like real
  regressions; the next mutation run then reported that exact row as
  `SKIP: pattern not found` plus one INCIDENTAL catch, which identified the stuck
  mutation. After restoring the two lines the suite was 192 passed, 1 skipped and the
  pre-proof passed again.
- **Root cause:** `mutation_proofs.py` mutates real worktree files and restores them
  after each row; a kill mid-row leaves the mutated bytes. No step in the routine
  checks that the tree is in its intended (unmutated) state before running checks, so
  the false failures were first read as product regressions.
- **Prevention rule:** never kill `mutation_proofs.py` mid-run; if it is interrupted,
  before trusting any test result verify all 38 row patterns are present exactly once
  (with the harness's CRLF fallback), and treat a row's `pattern not found` as a
  signal that the worktree, not the code under test, is wrong.

## 2026-09-21 Slice 9: baseline used the unrelated PATH interpreter

- **What happened:** the first baseline command used bare `python`, resolved to the
  Hermes 3.11 environment and failed because pytest was absent. The project venv
  baseline subsequently returned 192 passed, 1 skipped.
- **Root cause:** resumed execution before recovering the environment constraint
  from the interrupted required-context read.
- **Prevention rule:** finish required-context recovery before issuing checks; use
  `.venv/Scripts/python.exe` explicitly for repository commands. **Superseded
  2026-09-26:** use `.venv313/Scripts/python.exe`; the `.venv` trampoline is
  blocked by Windows Application Control on this machine.

## 2026-09-21 Slice 9: nested labels hid a rendered-test blind spot

- **What happened:** removing the run region's synthetic label survived the first
  browser assertion because it found the nested ledger event's label instead.
- **Root cause:** the selector searched all descendants without verifying ownership
  of the matching label.
- **Prevention rule:** require the label's closest synthetic region to equal the
  region being checked; remove each owned label independently and require failure.

## 2026-09-21 Slice 9: incomplete native Enter event in the browser harness

- **What happened:** the first keyboard probe left the evaluator unselected even
  though it was focused; a CDP Enter event without its character did not perform
  native button activation.
- **Root cause:** the harness sent only key metadata, omitting the Enter text.
- **Prevention rule:** send a complete native key sequence and verify both focus
  and the resulting application state instead of substituting a programmatic click.

## 2026-09-21 Slice 9: repair activation and room drawing needed correction

- **What happened:** browser inspection found the repair bench could activate
  without an incident, and shelf slabs visually occluded the authored book spines.
- **Root cause:** station selection lacked an incident-state guard; the SVG painter
  order hid the front book faces behind later slabs.
- **Prevention rule:** test incident-dependent controls against an empty real view;
  inspect rendered artwork rather than assuming correct geometry from source.
  The repair regression failed before the guard and passed after it; book fronts
  were repainted in front of the slabs and inspected in fresh screenshots.

## 2026-09-21 Slice 9: review exposed navigation, callback and focus regressions

- **What happened:** five browser assertions reproduced three review findings:
  station changes left journey hashes stale; skip links changed the selected view;
  refresh lost the away placeholder; customer Enter removed the focused button;
  and an obsolete incident callback overrode a newer selection.
- **Root cause:** URL, station and deferred-view state were not synchronized;
  request-generation protection stopped at the refresh function instead of its
  caller; rebuilding the customer list discarded native focus.
- **Prevention rule:** preserve one selected view during refresh, distinguish
  navigation intent from request generation, require an accepted refresh before
  applying async selection, and test native Enter followed by Tab after a rerender.
  All five assertions failed against the pre-fix client before the corrections.

## 2026-09-21 Slice 9: the browser harness asserted identity and counts, not rendered values

- **What happened:** the independent review served mutated copies of `app.js` to
  the browser, one production rendering change per run (customer answer text,
  public-record value, check verdict, event type). All four faults rendered and
  all four browser runs still exited 0: the rendered-evidence assertions checked
  the request quote, metadata, byte equality, provenance-hash presence and element
  counts, and the ordinal mutation only edited a DOM dataset, so no substantive
  displayed value was ever compared against the API payload.
- **Root cause:** the harness proved that the page bound the right RECORDS to the
  panel but never that it displayed the right VALUES; a passing count of linked
  rows was treated as evidence that the rendering was correct. Same class as the
  graduated AGENTS.md verification rule (prove coverage, do not count it), now
  applied to rendered evidence instead of leak scanners.
- **Prevention rule:** every rendered evidence surface asserts its displayed value
  and identity against an independently fetched payload (answer text, record
  title/value/age, per-check verdict rows, per-event rows), and each assertion is
  proven failing-capable by a served-source fault row
  (`tests/client/render_faults.mjs`, `SHIFTWORK_FAULT` mode in
  `tests/client/browser.mjs`): the baseline must be green and every fault row must
  fail at the named assertion.

## 2026-09-21 Slice 9: historical provenance was re-derived from the mutable source path

- **What happened:** the independent review replaced a run's snapshot file at the
  same pathname after finalization; the historical outputs endpoint then reported
  the NEW record value, a NEW "run snapshot" hash and a NEW comparison while the
  captures, checks and events stayed original, so the UI could show a historical
  comparison that disagreed with what the run consumed. Deleting the source made
  the whole outputs response 500 and lose the retained raw bytes.
- **Root cause:** Slice 7/8 persisted the snapshot as a pathname
  (`shop_snapshot_ref`) and every later read (transcript selection, scoring,
  retrieval) re-read that path, so "the snapshot this run consumed" was only true
  while the file stayed byte-identical. The Slice 5 note about inputs coinciding
  by configuration was recorded as a latent-bug note but not fixed, and Slice 9's
  public comparison made the consequence user-visible.
- **Prevention rule:** a claim that a run consumed an input must persist the
  consumed identity, not a locator: capture the bytes once at execution, store
  them with the run, and resolve every later read from the capture (path reads
  only for rows that predate the capture). Retrieval must degrade optional
  enrichment to nulls when a source is unavailable and never fail the response
  that carries the retained capture.

## 2026-09-21 Slice 9: navigation checks covered the happy path only

- **What happened:** the review found that activating an incident with native
  Enter dropped keyboard focus to BODY, and that on narrow layouts a station
  selection left its detail panel entirely below the viewport (390x900: panel top
  around y=955) with focus still on the station control. The session's own
  browser checks exercised customer focus and page overflow, not incident focus
  or whether the selected content was actually reachable.
- **Root cause:** the checks verified that navigation CHANGED the view, not that
  the user could reach the changed content: no focus assertion for the
  incident-to-evidence path and no viewport-reach assertion after a station tap.
- **Prevention rule:** for each navigation action assert where focus lands and, at
  narrow widths, that the selected panel is inside the viewport after a native
  touch; drive the interaction with real key/touch events and require the
  assertion to fail when the focus/scroll behavior is removed (both rows exist in
  `tests/client/render_faults.mjs`).

## 2026-09-21 Slice 9: the new degradation test exercised the capture branch, not the guard branch

- **What happened:** the new mutation row for the retrieval-degradation guard
  removed the `except (OSError, ValueError)` fallback and the named test still
  passed (NOT_CAUGHT): the test deleted the source file for a run executed under
  the current controller, which resolves the persisted capture and never reads
  the path, so the fallback never fired. The replacement test (a legacy row with
  no capture whose recorded path is gone) then failed INCIDENTAL, because an
  unhandled route exception propagates through TestClient instead of returning
  the 500 a real client sees; only with `raise_server_exceptions=False` did the
  mutation produce an assertion-level "assert 500 == 200".
- **Root cause:** the test was written for the user-visible scenario instead of
  the guard branch's preconditions, so it proved the capture branch twice; and
  the first replacement asserted through a harness whose failure shape
  (propagated exception) is not the production failure shape (HTTP 500). The
  mutation harness did its job both times and is the reason neither error
  survived.
- **Prevention rule:** a test for a new guard branch must construct that branch's
  own preconditions (the legacy/no-capture state here), not the adjacent happy
  path; when the guard protects an HTTP surface, assert through a client that
  surfaces the crash as a status code so the removed guard fails with an
  assertion, never an incidental exception. Run the mutation row for every new
  guard before claiming it is covered.

## 2026-09-24 Gate 1 preview: assumed WebSocket existed in the REPL

- **What happened:** the browser verification setup raised `ReferenceError: WebSocket
  is not defined` after launching its isolated Chrome process; no mockup test ran.
- **Root cause:** the REPL's exposed globals were assumed to match the installed Node
  executable used by the existing browser harness.
- **Prevention rule:** check required globals in the actual execution context; use
  the installed Node process for protocol transport when the REPL lacks WebSocket.
  Reuse and close the already-started browser rather than leaving duplicate processes.

## 2026-09-24 Gate 1 preview: assumed the allowlist was an array

- **What happened:** resumed browser verification called `.filter` on a Set, stopping
  the check before any page was tested. Converting it with `Array.from` repaired the harness.
- **Root cause:** the resumed session relied on a variable name without checking its type.
- **Prevention rule:** inspect persistent helper types before reusing them after context
  recovery; do not infer collection methods from a summary.

## 2026-09-24 Gate 1 preview: compared cross-context prototypes

- **What happened:** `deepStrictEqual` rejected equal browser-result arrays in the
  REPL before the choice checks ran; serialized value comparison passed.
- **Root cause:** a value check also compared prototypes from different execution contexts.
- **Prevention rule:** normalize browser protocol values before comparing nested data;
  report harness failures separately from product failures.

## 2026-09-25 Slice 10: fresh v6 schema broke historical migration fixture setup

- **What happened:** three existing v2/v3 migration tests failed before migration
  because their fixture derives old table shapes from the current `schema.sql`,
  then inserts positional v5 rows into tables that now have v6 columns.
- **Root cause:** I changed the fresh schema without checking that historical test
  fixtures treated it as a template for older schema versions.
- **Prevention rule:** when adding schema columns, find every fixture derived from
  the live schema first. Pin historical fixtures to their actual old schema shape
  and retain their original assertions before treating upgrade tests as green.

## 2026-09-25 Slice 10: starter draft exposed a protected phrase

- **What happened:** the first starter draft copied the Slice 8 repair-arc pre
  artifact, and the serialized draft API contained text also present in a sealed
  case note. The existing API leak scanner caught it; the starter was changed to
  the safe three-file scaffold before completion.
- **Root cause:** an internal trusted-fixture artifact was reused as public
  learner-editable source without first scanning its serialized API projection.
- **Prevention rule:** when seeding public draft/source material, run the serialized
  leak scanner on GET and PUT surfaces before calling the starter safe.

## 2026-09-25 Slice 10: reported a run state without its evidence mode

- **What happened:** extending the migration demo to show the new-engagement
  `STARTER_BASELINE`, the first version printed `starter_run_state: FINALIZED` on
  its own. That reads as "the starter ran and worked". It did not run at all:
  `config.EXECUTOR_ADAPTER` defaults to `recorded`, so the run replayed a pinned
  transcript. The same starter under `executor="local_process"` fails closed as
  `PROVISION_FAILED` because the scaffold is not in `TRUSTED_LOCAL_FIXTURES`.
- **Root cause:** I treated a terminal run state as the whole claim and read the
  demo's default adapter as the one I had been testing with, after my own repro had
  explicitly passed `local_process`. Two different adapters, one label.
- **Prevention rule:** never record or display a run's `state` as evidence without
  its `adapter`, `evidence_mode` and `purpose` beside it. A FINALIZED recorded
  replay proves the transcript is readable, not that any artifact executes. When a
  result contradicts an earlier repro, isolate the differing parameter before
  reasoning about either one.

## 2026-09-25 Slice 11 public draft: incomplete review-hash transcription

- **What happened:** the first status-table edit contained two incomplete hash
  strings. The first correction also mismatched its search text; the next exact
  edit replaced both with the actual computed digests before presentation.
- **Root cause:** manual transcription of byte evidence without an immediate
  file-to-record equality check.
- **Prevention rule:** verify every recorded hash against its file bytes and
  require a full 64-character digest before presenting a fixture review pack.

## 2026-09-25 Slice 11 verification: incomplete success substitution

- **What happened:** the first in-memory capture fault labelled as success added
  collection but omitted the alternative. It was not a complete-success probe;
  the corrected probe completed both required tasks and failed the named capture assertion.
- **Root cause:** the probe checked its changed task without checking the complete
  required-task set.
- **Prevention rule:** before counting a success-substitution proof, assert that
  every required task is present and complete in the injected response.

## 2026-09-26 Interpreter block cost the session's verification; the OneDrive hardlink install failed before the copy-mode fix

- **What happened:** the project `.venv` trampoline raised
  `OSError: [WinError 4551] An Application Control policy has blocked this file`
  on every invocation, and the CPython 3.12 interpreter it points at returned
  `Permission denied`; no retry cleared it. The system 3.11.9 cannot run the
  suite (the models use PEP 695 type aliases) and the existing 3.13 interpreters
  could not load the venv's cp312 compiled dependencies, so verification was
  impossible until a fresh `.venv313` was built from the uv-managed CPython
  3.13.14. Creating that venv succeeded, but the first dependency install with
  `uv pip install -r requirements.lock` failed on this workspace because uv's
  default hardlink strategy does not survive the OneDrive-synced tree; the same
  install succeeded with `--link-mode=copy`, and `INSTALLER` in the resulting
  `site-packages` records `uv`.
- **Root cause:** the machine's Application Control policy is a recurring,
  non-transient hazard for this checkout (second occurrence after 2026-09-17),
  and the workspace lives under OneDrive, where hardlinked installs are not
  reliable. The earlier note treated the first occurrence as transient and
  planned no fallback interpreter, so a blocked 3.12 meant zero verification.
- **Prevention rule:** verification commands run with
  `.venv313/Scripts/python.exe` (git-ignored, built from the uv-managed 3.13
  interpreter); when 4551 appears, do not retry the blocked interpreter and do
  not run `uv run` as a probe (it tried to rebuild `.venv` on 2026-09-26 and
  produced an untracked `uv.lock`). Install dependencies into a fresh venv with
  `uv pip install --link-mode=copy -r requirements.lock`; never hardlink into
  this OneDrive tree. Report a blocked interpreter plainly instead of reporting
  post-block work as passing.

## 2026-09-26 Slice 11: three mutation rows had been silently skipped since the Slice 10 refactor

- **What happened:** the main harness, `tests/mutation_proofs.py`, carried three
  Slice 8 rows whose byte patterns no longer existed:
  `close_version_fallback_removed`, `start_run_ignores_the_inherited_version` and
  `snapshot_capture_bypassed_for_the_mutable_path`. Slice 10 replaced the
  inherited-version fallbacks with `_selected_operating_version` and grew a
  legacy branch inside `_snapshot_bytes_for_run`, so each row printed
  `SKIP: pattern not found` and proved nothing. The loss went unnoticed because
  the main harness was not re-run after the Slice 10 refactor; the pivot harness
  was re-run, and its output was read as the whole story.
- **Root cause:** a mutation row is an anchor into exact source bytes; a refactor
  silently breaks the anchor, and the harness reports the miss as SKIP rather
  than as a failure, so a run that nobody re-executed cannot correct it. The
  Slice 10 verification recorded the pivot harness counts without re-running
  the main harness.
- **Prevention rule:** after any refactor of a function a mutation row anchors
  onto, re-run that harness and treat every `SKIP` as a coverage loss that must
  be re-anchored or explicitly retired, never as a neutral result. A harness run
  is evidence only when every row reports `FAIL_CAUGHT` with `restored=True`.
  Re-anchored rows must fault branches the other rows do not already fault; two
  rows that fault the same branch prove neither. Repaired 2026-09-26 as recorded
  in `00-status.md`; the harness now runs subprocesses under `sys.executable`
  instead of a hardcoded interpreter path.

## 2026-09-26 Slice 11 client: the new station was added without its served-shell contract test

- **What happened:** the Slice 11 client work added the `investigate` station and
  the `source` and `diagnostic` labelled regions, but
  `tests/api/test_client_shell.py` still pinned the old 7-station set. The first
  full-suite run of 2026-09-26 returned
  `1 failed, 360 passed, 1 skipped, 2 warnings in 48.57s` with
  `Extra items in the left set: 'investigate'`; the test was updated to the
  shipped contract and the re-run returned
  `361 passed, 1 skipped, 2 warnings in 45.75s`.
- **Root cause:** the client change was verified in the browser harness (which
  asserts 8 stations) and in the preview test, but the smaller shell contract
  test was not run or updated in the same pass, so the suite was left red.
- **Prevention rule:** when a client change alters the served shell (stations,
  labelled regions, assets), update and run the shell contract test in the same
  change, not only the browser harness; before reporting a slice's suite as
  green, run the full suite, not the focused files.

## 2026-09-26 Slice 12 preflight shell loader attempted an empty variable

- **What happened:** the first PowerShell `.env` loader passed a blank line to
  `SetEnvironmentVariable`, which emitted an exception before the preflight
  still ran. A corrected command filtered to the two expected variable names
  and produced clean output with the same denied-entitlement result.
- **Root cause:** the loader assumed every `.env` line contained `name=value`.
- **Prevention rule:** filter `.env` input to expected variable names before
  setting process environment variables; keep the credential values out of
  command output and evidence files.

## 2026-09-26 Slice 12 entitlement misdiagnosis from wrong project header

- **What happened:** `whoami` authenticated under the local `project-...`
  header but returned every Sandbox permission false. I reported missing
  entitlement. A Nebius Support reply supplied the correct `aiproject-...`
  header; with the same key, all six permissions were true and image listing
  succeeded.
- **Root cause:** I treated an authenticated token's denied permissions as a
  project-wide entitlement verdict without verifying the exact `Project`
  header against the support-provided AI project ID.
- **Prevention rule:** before concluding access is unavailable, verify the
  token and project-header pairing against the provider's exact project ID;
  retain both responses when a corrected header changes the verdict.

## 2026-09-26 Slice 12 first live probe produced a false leak alarm and no model answer

- **What happened:** the first live service run completed, but the 64-token
  Nemotron limit ended with `finish_reason=length` and empty content. The leak
  scanner returned false even though a read-only rescan of the saved operation
  found no token, canary or host path.
- **Root cause:** the scanner's positive control searched for a Windows path in
  JSON without accounting for escaped backslashes. The output limit also left
  too little room for this reasoning model to emit its answer.
- **Prevention rule:** validate needles against the serialized form, including
  escaped and forward-slash path forms. Inspect `finish_reason`, content and usage
  before treating an inference request as meaningful service behavior; stay below
  Gate 3's 1,024-token ceiling when adjusting the spike limit.

## 2026-09-26 Slice 12 layer-cap result was diagnosed before checkpoint readback

- **What happened:** a 2 MiB file filled with repeated `x` bytes completed under
  a 1 MiB `max_layer_bytes` setting. I first called it a cap bypass, then
  attributed the 26,866-byte image to compression. A second run wrote random
  bytes and also reported success with the same image size. Read-only inspection
  found the supposedly written file had zero bytes in both checkpoints.
- **Root cause:** the probe trusted process stdout and image size without reading
  the saved file. Neither showed whether the checkpoint retained the written bytes.
- **Prevention rule:** check the checkpoint file's exact size and contents before
  diagnosing compression or limit enforcement. Treat successful execution with
  silently lost state as a stop condition for snapshot-dependent comparison.

## 2026-09-26 Slice 12 checkpoint verdict rested on an unarchived readback and a verifier that could not distinguish its cases

- **What happened:** the STOP verdict's decisive observation (a checkpoint
  listing `/tmp/slice12-large.bin` at zero bytes) appeared only in prose. The
  redacted JSONL held no listing or download record, no timestamp and no code
  revision, and its records cannot be emitted by any current script revision
  (`layer_cap_did_not_block_large_write` appears in no `.py` file; `WROTE_2MB`
  versus the current `WROTE_2MB_RANDOM`). The current cap check hard-stops on
  outer `SUCCESS` plus the stdout marker without downloading bytes or
  comparing a digest, so an intact 2 MiB listing would still emit
  `successful_run_snapshot_lost_written_bytes`. An independent review found
  both; a separately authorized read-only re-inspection then confirmed the
  zero-byte file in both recorded images and archived the raw records.
- **Root cause:** the probe trusted process stdout and image size without
  retrieving the saved file, the archive was appended across evolving script
  revisions without per-record revision or timestamp stamps, and the readback
  that produced the quoted observation ran outside the archived record set.
- **Prevention rule:** archive the raw record of any observation a verdict
  depends on, in the artifact set it is quoted from, with a UTC timestamp and
  source revision per record; a checker must download the artifact and compare
  a digest, and never branch on a success marker alone; after a script changes,
  new runs write to a new file with stamped records rather than appending to an
  unversioned one.

## 2026-09-26 Spike mutation rows were proven by crashes, not by assertions

- **What happened:** the first run of `tests/spike/mutation_proofs_spike.py`
  reported `assertion-level catches: 20/23` and exit 1. Three stamping rows
  (`record_utc_stamp_removed`, `record_source_hash_removed`,
  `emit_stamp_bypass`) failed with `KeyError`: the tests indexed
  `record["source_sha256"]` and `record["recorded_utc"]` directly, so removing
  the stamp raised before any assertion could run. The harness classified them
  `CAUGHT_INCIDENTAL`, which is not a proof.
- **Root cause:** an assertion that reads a required key raises instead of
  failing, so a deleted field looks like a crash and the guard stays unproven
  even though every test reports red.
- **Prevention rule:** in mutation-proven checks, read the field with `.get()`
  and compare it explicitly, so a missing or altered value fails as an
  assertion. Before citing a harness count, require `FAIL_CAUGHT` per row; a
  crash, a collection error or a timeout proves nothing about the guard.

## 2026-09-26 An appended MISTAKES block was written with literal escape sequences

- **What happened:** the new Slice 12 mutation-proof entry was appended to this file
  through an edit whose new text carried the characters backslash-r-backslash-n and
  backslash-double-quote as escape sequences. The file received them literally, so the
  whole entry landed on one unreadable line. The corruption was caught while verifying
  the appended block before the commit and repaired in place with a byte-level script;
  only the appended text changed, and the prefix stayed byte-identical.
- **Root cause:** this file is CRLF, and the edit argument encoded newlines as escapes
  instead of real line breaks, which made the escaping ambiguous between the tool, the
  shell and the file.
- **Prevention rule:** append to a CRLF file with a byte-level write that sets the line
  endings explicitly, then read the region back with `Read` and confirm the block renders
  as separate lines before committing. Never encode line breaks as escape sequences in a
  tool argument.
## 2026-09-26 Slice 12 escape run archived only the service-path inference observation

- **What happened:** the new `escape` phase calls `infer()` twice, once through the
  service path and once directly for the token-ceiling probe. The live evidence file
  held the first call's full observation but not the second's, because the
  `nemotron_inference` emit sat in the service request loop rather than inside
  `infer()`. The second call's cost, prompt tokens and latency were never archived;
  only the derived `escape_limit_probe` fields survived.
- **Root cause:** the measurement was archived at one call site instead of where it is
  produced, so the first new caller silently omitted it.
- **Prevention rule:** emit a measurement where it is produced, not at a caller, and
  guard the one emit site with a source-level test plus a mutation that duplicates the
  emit at a call site. `test_inference_calls_are_archived_from_one_emit_site` now
  requires exactly one `nemotron_inference` emit and requires it inside `infer()`.

## 2026-09-27 Slice 12 trials run archived the inference content but not the tokens that produced it

- **What happened:** all six trials passed, but each reported 103 to 143
  `completion_tokens` while the archived `content` was the six characters
  `\nSTOCK`. `infer()` builds its observation from `choices[0].message.content`
  plus `usage`, `finish_reason` and its own timing, and reads no other field the
  provider returns, so roughly 100 to 140 billed completion tokens per call are
  absent from the evidence and the run cannot say what they were. The same blind
  spot is why the escape run's two empty completions at `finish_reason: length`
  cannot be told apart from a purposeful refusal using archived data alone.
- **Root cause:** the fix for the escape archiving defect moved the emit inside
  `infer()` so that no caller could omit the record, but it archived a
  hand-picked field list instead of the provider response. Its guard asserts the
  emit count and its location, so proving that a record exists was mistaken for
  proving that the observation is complete.
- **Prevention rule:** when archiving an external observation, archive the whole
  response payload minus an explicit redaction list, not an allow-list of fields
  the author expected to matter. Every field counted in `usage` must be either
  archived or explicitly recorded as deliberately dropped with a reason. A guard
  on "the record was emitted" is not coverage of "the observation was captured".
- **Repair 2026-09-27:** `infer()` now archives the whole provider response body
  under `provider_response`, minus an explicit `REDACTED_RESPONSE_FIELDS` list whose
  dropped keys are recorded in `redacted_fields`, and the single emit site is
  unchanged. Two offline guards (a fake-client round trip of every field, and a
  forced redaction that must be named) plus two mutation rows fail against the
  pre-fix code; the spike table is 58/58 with byte-identical restoration. An
  authorized confirming call archived `message.reasoning` (438 characters) beside
  `content`, so the invisible completion tokens were the provider's `reasoning`
  field. Records archived before the repair stay incomplete; the repair is
  forward-looking.

## 2026-09-27 S13 Investigate route passed a new adapter argument to an old helper signature

- **What happened:** the first focused S13 test run had two failures; the public
  Investigate GET raised `TypeError` because the route passed `adapter=` to
  `investigate_station` before that helper accepted it. The other failure was
  an old denial-message assertion that needs the newly specified ordinary-shift
  null-ID wording.
- **Root cause:** I changed the route and the lower `investigation_view` helper
  but missed the composing `investigate_station` function between them.
- **Prevention rule:** when adding a parameter through a route, trace every
  intermediate call signature and run the route-level focused check immediately.

## 2026-09-27 S13 adapter parsed a Sandbox stdout event as text instead of value

- **What happened:** a real-shape fake event made the adapter mark a successful
  checkpoint run `SANDBOX_TERMINATED`; the test failed before the fix. The SDK
  stream carries `value` and `encoding`, including a base64 option, not `text`.
- **Root cause:** the first fake client used my invented event shape, so its
  passing result did not exercise the S12-observed SDK wire shape.
- **Prevention rule:** build transport fakes from archived provider records or
  installed SDK models, and test both plain and encoded event values before a
  live call.

## 2026-09-27 S13 scanner missed a JSON string nested inside a JSON response

- **What happened:** the serialized scanner self-test caught raw, slash and
  base64 path forms, but missed a path inside a JSON string that was itself
  serialized into a response. The focused test failed, then passed after the
  scanner checked successive JSON escape layers.
- **Root cause:** I checked one escape layer while the event payload can be
  serialized twice.
- **Prevention rule:** self-test each actual serialized surface shape, including
  nested JSON strings and base64 bodies, before interpreting an absence scan.

## 2026-09-27 S13 live model response exhausted the initial output allowance

- **What happened:** the first model-backed diagnostic made one provider call, but
  its 256 completion tokens ended during reasoning with no final tool name. The
  service had no response capture, so the trial correctly stayed failed and
  incomplete. No business state changed.
- **Root cause:** I chose a 256-token default without checking whether the
  reasoning model could finish this bounded choice inside it. The approved
  gateway ceiling is 1,024 tokens.
- **Prevention rule:** set the frozen provider allowance from the approved
  ceiling and inspect actual `finish_reason`, final content and token usage in a
  separate failed run before retrying. Preserve the failed run as evidence.

## 2026-09-27 S13 projection scanner crossed the sealed path boundary

- **What happened:** the first full suite failed its sealed storage import guard
  because the new orchestrator scanner referenced `SEALED_CASES_DIR` directly.
  The other 437 tests passed.
- **Root cause:** I used a private path as a leak needle without tracing the
  existing rule that only the sealed loader may name that location.
- **Prevention rule:** obtain sealed path needles through the sealed loader and
  run `tests/sealed/test_import_graph.py` when changing projection boundaries.

## 2026-09-27 Slice 13 frozen context kept the old 256-token ceiling after the runtime change

- **What happened:** the runtime gateway ceiling was raised to the approved
  1,024 tokens after the first live model attempt, but the frozen execution
  context still hardcoded `max_tokens: 256`. The archived successful run
  therefore records 256 while its provider call returned 287 completion tokens.
  The Slice 13 cross-check found it by re-reading the preserved run database.
- **Root cause:** the same ceiling had two owners, the `InferencePolicy` default
  and a literal in `freeze_diagnostic_context`, and no assertion tied the frozen
  record to the executed value.
- **Prevention rule:** a fixed ceiling has exactly one named constant; every
  recorded copy imports it, and a test asserts the frozen record equals the
  runtime policy value before a live claim is made.

## 2026-09-27 Slice 13 claims implied Gate 3 test 36 and 38 arms that no test pinned

- **What happened:** the completion summary implied the injected-field 422 clause
  and transport-failure retention were covered; the suite pinned neither. The
  cross-check found both against the approved test text.
- **Root cause:** the slice's test list was read as covering whole obligation
  groups, and the missing arms were never named as required assertions.
- **Prevention rule:** before claiming a spec clause is covered, name the test
  that fails when that clause's behavior breaks; if no such test exists, the
  clause stays open in the completion record.

## 2026-09-27 Slice 13 image UUID kept a second literal, making the documented override inert

- **What happened:** `SHIFTWORK_TOKEN_FACTORY_IMAGE` is a documented configuration
  name, but the Token Factory adapter compared `image_ref` against its own
  hardcoded literal, so setting the override made an isolated run fail closed
  with `PROVISION_FAILED` instead of executing the named image. The S13
  cross-check found it and recorded it as a residual; the user then instructed
  the repair. No live run used the override and the archived evidence is
  unaffected.
- **Root cause:** the same fixed value had two owners, `config.TOKEN_FACTORY_IMAGE`
  and a literal in the adapter, the same shape as the 256-token ceiling found in
  the same cross-check.
- **Prevention rule:** a fixed value has exactly one named constant; every copy,
  including the frozen-context record and the adapter gate, reads it, and a test
  drives an override through both sites with one failing-capable mutation per
  site.

## 2026-09-27 Slice 14 stranded an assist event between reserve and finish

- **What happened:** a crash after the committed assist reservation left a
  PENDING event that counted against the three-call budget, refused every
  decision and told the learner to refresh for a result that could never
  arrive. The S14 review found it; the repair fails stranded events at startup
  with the controller-side `ASSIST_INTERRUPTED` code.
- **Root cause:** the reserve-before-call design paired no-refund counting with
  a terminal-outcome write a process death can skip, and only runs had restart
  reconciliation at the one startup recovery point.
- **Prevention rule:** every reserve-then-finish pair needs a resolvable
  terminal state for each reserved row, a startup reconciliation, and panel
  copy that stays true in every state the row can rest in.

## 2026-09-27 Slice 14's injected gateway client bypassed the call deadline

- **What happened:** the 20-second bounded transport existed only on the
  default provider path, so the injected `httpx.Client` used by tests and
  demos made an unbounded call. The S14 review found it; the injected path now
  carries the same per-request timeout and a transport-level test pins it.
- **Root cause:** one claim-defining bound lived in a single branch of a
  two-branch call, and the test/demo seam silently dropped it.
- **Prevention rule:** apply a claim-defining bound on every call path
  including injection seams, and pin it with a test that fails when the seam
  bypasses the bound.

## 2026-09-28 Slice 15 ledger-state test guessed the chain label

- **What happened:** the first focused run failed one new assertion because it expected VERIFIED; the ledger verifier actually records VALID.
- **Root cause:** I guessed an enum value instead of checking the existing chain contract before writing the assertion.
- **Prevention rule:** read the declared enum or a stored baseline value before asserting exact status text, then run the focused check immediately.

## 2026-09-28 Slice 15 review repairs initially failed focused tests

- **What happened:** a new variant identity passed a tuple to the canonical hasher, which accepts JSON-shaped lists, and an edited candidate B no longer matched its frozen source pin. Two focused tests failed before both were corrected.
- **Root cause:** I changed content-bearing data without checking the hasher's accepted input shape or regenerating the pin in the same edit.
- **Prevention rule:** use JSON-shaped values at canonical hash boundaries and recompute candidate pins immediately after any source edit, then run the focused reservation and pin checks.

## 2026-09-28 Slice 15 case reorder introduced CRLF into a byte-addressed fixture

- **What happened:** the focused conformance run found CRLF in the new protected case JSON after a Windows text rewrite; 129 tests passed and one failed. I normalized that file to LF before rerunning.
- **Root cause:** a text writer applied Windows newline translation to a file whose exact bytes are part of the authored evidence.
- **Prevention rule:** write byte-addressed fixtures as bytes or explicitly force LF, then check newline counts and content hashes before running conformance.

## 2026-09-28 Slice 15 edits overlapped mutation proof restoration

- **What happened:** I started a mutation proof run as a baseline and edited source before it finished. Its restore step overwrote an orchestrator patch and left the mutation result contaminated by an in-progress evaluator edit. The 77-row run exited 1 and is not a valid baseline.
- **Root cause:** the mutation harness rewrites and restores production files, so edits and the run cannot safely overlap.
- **Prevention rule:** complete and inspect a mutation run before editing any file it can target; after an overlap, recheck touched bytes and rerun proofs only on a settled tree.

## 2026-09-28 Slice 15 spec-hash assertion was indented one level too deep

- **What happened:** the first focused rerun stopped at collection with an `IndentationError` in the revised workload pin assertion.
- **Root cause:** a patch carried indentation from the inner spec list while replacing an assertion at the outer workload level.
- **Prevention rule:** compile a touched Python test file before starting a long focused run, then inspect the exact edited lines after a multiline patch.

## 2026-09-28 Slice 15 scanner call added an undefined connection

- **What happened:** the full suite found five assist failures because `assist_event_view` called `assert_public_projection(view, conn)` even though that function has no `conn` argument.
- **Root cause:** a broad replacement matched the assist view while changing scanner calls for experiment routes.
- **Prevention rule:** anchor scanner edits to the owning function, inspect every changed call site, and run the focused assist route test before the full suite.

## 2026-09-28 S16 outcome route omitted its strict response schema

- **What happened:** the first lifecycle run had 16 failures because comparison_view added `outcome`, but `ExperimentView` rejected it as an extra field. A concurrent route test then timed out before entering its worker because the POST response failed validation.
- **Root cause:** I changed the orchestrator projection without tracing the strict API schema at the route boundary.
- **Prevention rule:** when a public projection gains a field, update its response model in the same edit and run one POST and one GET route check before the broad lifecycle file.

## 2026-09-28 S16 protected predicate guessed the strict-budget outcome

- **What happened:** the first acceptance predicate required the budget-boundary case to complete an alternative, so both correct candidates failed that undrawn case. The frozen state has no item strictly under the budget, and both candidates correctly make a justified no-match refusal. A retirement test also guessed that A and B had each passed 3/3 before checking the first outcome; A's old 0/3 was an actual draft-spec mismatch.
- **Root cause:** I inferred the expected task status from the aspect name and asserted a fixed pass count before inspecting the exact case, response envelope and pre-retirement evidence.
- **Prevention rule:** inspect each authored aspect against its frozen state and both captured candidate envelopes. For preservation tests, compare post-action evidence to the measured pre-action value, then test the expected absolute value separately only after its basis is established.

## 2026-09-28 S16 mutation row kept a stale usage anchor

- **What happened:** after filtering protected observations from public metrics, the second mutation run reported 22 caught faults and one SKIP because the service-call row still named the old iterable.
- **Root cause:** a source change moved the exact mutation anchor from all observations to public-only observations, and the proof case was not updated before rerun.
- **Prevention rule:** after editing a mutation target, inspect and update every proof anchor in that file before treating the rerun as coverage; require zero SKIP rows.

## 2026-09-29 S16 harness CRLF fallback could not match a mixed-ending anchor

- **What happened:** `tests/pivot_mutation_proofs.py` returned 89 FAIL_CAUGHT and 8 SKIP instead of the recorded 97 of 97, which read as a possible false evidence claim. Measured: `core.autocrlf=true` with no `.gitattributes` entry for `shiftwork/orchestrator.py`, so HEAD stores pure LF (3157 LF, 0 CRLF) while the worktree is pure CRLF (3407 CRLF, 0 bare LF). Four anchors had been authored with mixed endings inside one string, faithfully recording a then-mixed worktree. The runner's fallback did `old.replace(b"\n", b"\r\n")` without normalising first, turning an authored `\r\n` into `\r\r\n` (16 CR-CR-LF sequences in two of them), so those anchors could match neither regime. `orchestrator.py` is the same blob `b9af29da` at 60a378e, 224afd4, b1dabef and HEAD, so the file the harness was re-anchored against is HEAD's file. With line endings normalised on both sides, all eight anchors match HEAD exactly once and the recorded 97-of-97 is genuine.
- **Root cause:** the fallback assumed an anchor is uniformly LF, and reported a line-ending mismatch as `pattern not found`, which is indistinguishable from a guard that no longer exists. The 2026-09-20 Slice 8 prevention rule told me to verify anchors "with the harness's CRLF fallback", so the broken tool was trusted to audit itself.
- **Prevention rule:** the runner now tries the authored bytes, then the LF-normalised form, then the CRLF-normalised form, so an anchor may be authored in any shape and still matches a uniform file in either regime. Treat `SKIP pattern not found` as unadjudicated, never as coverage and never as proof of a false claim: normalise line endings on both sides and re-measure before concluding a guard is gone. Do not use a fallback as the oracle for whether the fallback works.

## 2026-09-29 mutation harness truncated a committed evidence file on every run

- **What happened:** running `tests/pivot_mutation_proofs.py` rewrote `docs/plans/shiftwork/evidence/slice15-mutation-rerun-2026-09-28.txt` in place, replacing the recorded 97-of-97 S15 evidence with the current 89-of-97 run and leaving a tracked file modified in an uncommitted tree.
- **Root cause:** `RESULTS_LOG` pointed at a committed evidence file and `main()` begins with `RESULTS_LOG.write_text("")`, so the harness owned and destroyed a record it was only meant to reproduce. Nothing warned that the target was tracked.
- **Prevention rule:** a harness results log must point at an uncommitted path for the round in progress, never at committed evidence. Before running any harness, check whether its output path is tracked (`git ls-files --error-unmatch`); if it is, repoint it first. The 89/8 bytes are preserved with their diagnosis in `docs/plans/shiftwork/evidence/slice16-anchor-rot-run-2026-09-29.txt`, and the S15 record was restored from HEAD and re-verified at 97 FAIL_CAUGHT, 0 SKIP.

## 2026-09-29 S16 repair round ran an unauthorized install inside the offline suite

- **What happened:** verifying the repair round with the command .venv313/Scripts/python.exe -m pytest tests -q executed tests/packaging/test_clean_env_install_and_run.py::test_clean_env_install_and_run (Test 51), which creates a fresh venv under tmp_path and runs pip install -r requirements.lock unconditionally at lines 128 to 131, and whose own docstring says it requires network access for the installer. Installs are not authorized by this go-ahead. Measured evidence: pip wrote 26 HTTP cache entries under %LOCALAPPDATA%/pip/cache at 01:02:43, sixteen seconds before that run's log closed at 01:02:59, while the follow-up --ignore=tests/packaging run at 01:09 wrote none, which isolates the cause. The prior session's recorded 561-passed run installed the same way. Impact was contained: the venv lived in tmp_path and is gone, no repository file changed, orchestrator.py kept sha256 f3ae145c, and requirements.lock and pyproject.toml are untouched in git status.
- **Root cause:** I repeated a command a handoff recorded as verified green without checking what it collects. pytest tests and pytest tests --ignore=tests/packaging are not the same command, and only the wider one performs a network install. AGENTS.md section 6 already said installs need authorization and that the 2026-09-19 audit excluded Test 51 for exactly that reason, so the repository convention was on record and I did not apply it.
- **Prevention rule:** offline verification for this repository is .venv313/Scripts/python.exe -m pytest tests --ignore=tests/packaging -q unless an install is explicitly authorized. Before running any handed-off test command, compare its collected set against the recorded one with --collect-only -q and check whether it collects tests/packaging. A test count is not comparable across two different commands, and a command that touches the network is not an offline check.

## 2026-09-29 S16 repair round accepted a false adjudication of a test-count discrepancy

- **What happened:** a handoff recorded that 561 passed was the true figure and that an earlier 560 was a stale mis-measurement taken before a 23:55 edit, adding that this could not be proven directly because the pre-edit content is uncommitted and unrecoverable. I wrote that adjudication into 00-status.md before testing it. It is false and was provable in one command: 560 and 561 are both correct, for --ignore=tests/packaging and for tests respectively, and the single test of difference is packaging Test 51. tests/packaging collects exactly 1 test, tests --ignore=tests/packaging collects 561 and tests collects 562. The dismissed plus-4 was also real, since the recorded 556 under --ignore=tests/packaging plus the four tests this round added is exactly 560.
- **Root cause:** the adjudication reasoned about mtimes, collection filters and arithmetic consistency while never comparing the two commands that produced the two numbers. I then treated a handed-off conclusion as settled fact because it was written confidently and labelled adjudicated, instead of re-deriving it from a measurement I could run.
- **Prevention rule:** a claimed discrepancy between two measured numbers is not adjudicated until the exact command, filter and collected set behind each number are compared. The phrase this could not be proven directly is a prompt to find the direct proof, not a licence to record an inference as a finding. Never transcribe a handed-off verdict into a status document before reproducing it, and when a reproduction contradicts the handoff, correct the record and name the prior claim that was wrong.

## 2026-09-29 backticks inside a double-quoted python -c string executed as shell commands

- **What happened:** appending the two entries above was attempted with .venv313/Scripts/python.exe -c and the entry text in a double-quoted shell string. That text contained Markdown backticks around commands such as pytest tests -q, and Git Bash performs command substitution on backticks inside double quotes, so the shell ran those commands instead of passing them to Python. One of them was the full suite under the correct interpreter, which executed Test 51 again and caused a second unauthorized install: 30 pip cache entries carry mtimes at 01:14:25 to 01:14:26, during that substitution. Two others ran a bare pytest resolved against an older interpreter and aborted with a PEP 695 SyntaxError on the type statement in shiftwork/domain/models.py line 14, which is why conftest import errors appeared in the task output. The Python append itself never ran, so MISTAKES.md stayed at 90719 bytes and no partial write was left behind. The task was stopped, and no stray pytest or pip process remained.
- **Root cause:** a documentation string was passed through a shell quoting layer that gives backticks meaning. The command also exceeded the two minute tool timeout and was moved to the background, so the substituted commands kept running after the call appeared to fail.
- **Prevention rule:** never put prose containing backticks, dollar signs or parentheses inside a double-quoted shell -c argument. Write the text to a scratch file with the Write tool and execute that file, or use a byte-level append from a script, then delete the scratch file. Prefer single quotes for any inline shell string, and treat a command that silently moves to the background as still running until it is stopped and its side effects are measured.

## 2026-09-29 a staged read-all-then-write-all doc script clobbered its own edits

- **What happened:** applying nine documentation corrections across six files, a scratch script first looped over every edit reading each file into a staging list, then looped again writing them. Two files carried more than one edit, and each write used the original bytes captured at staging time, so every write replaced the whole file with original-plus-its-own-edit and discarded the edits already applied. Three of the nine edits were silently lost: the operator packet's status line, its introduction paragraph, and a dated note in slice15-implementation-plan.md. The script reported success for all nine and printed byte deltas that made the loss visible only on inspection, since all three packet writes started from the same 18370 bytes. Caught by grepping for each expected string afterwards rather than by the script's own output.
- **Root cause:** the read phase was separated from the write phase to validate every anchor before touching anything, which is a good instinct, but the staged payload was the original file content rather than a running accumulator. Validating all anchors first and applying them cumulatively are two different designs, and this mixed them. The script also verified only that its own replacement occurred, never that the previously applied replacements survived.
- **Prevention rule:** when a script applies several edits to one file, re-read the file before each edit and write it back immediately, or accumulate into a single buffer and write once. Never stage original bytes and write them more than once per file. A multi-edit script must verify its result by checking that every expected new string is present in the file afterwards, not by trusting a per-edit success message, and identical starting byte counts across writes to one file are the signature of this bug.

## 2026-09-29 S16 follow-up tests exposed incompatible helper signatures

- **What happened:** the first route-drift test used an invalid candidate label and failed during model validation rather than at the intended route KeyError. Later, adding an optional live budget positional argument broke three focused tests whose spies and fake gateway still used the original two-argument interfaces.
- **Root cause:** the drift fixture did not preserve the domain model's label constraint, and the new optional dependency changed call shapes even when it was absent.
- **Prevention rule:** make fault fixtures valid at every layer before the target guard. When adding optional execution controls, keep the original invocation shape on the default path and test existing fakes and spies before wider verification.
