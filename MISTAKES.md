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
