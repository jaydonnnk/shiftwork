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
