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
