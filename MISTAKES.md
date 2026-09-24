# Mistakes Log

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
  conclusion about the code.

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
  `.venv/Scripts/python.exe` explicitly for repository commands.

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
