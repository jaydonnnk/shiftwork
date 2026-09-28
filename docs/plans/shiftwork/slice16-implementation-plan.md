# Slice 16 implementation plan

Status: repair round complete and committed, 2026-09-29. Slice 16 has its own
user go-ahead, and the eight findings from the 2026-09-28 independent review are
repaired with failing-capable proofs. The Slice 15 comparison manifest and
protected family were reviewed and sealed by the operator on 2026-09-29, so
production reservations now admit those bytes; the two tests that prove the
review gate construct their own unsealed material rather than depending on the
shipped state. Offline tests may still inject a review gate. No live call, push,
Slice 16 acceptance or later-slice selection is authorized here, and sealing does
not authorize any of them.

The first acceptance reading found an S15 draft-fixture error: all six protected
task specs omitted the optional price task that candidate A returns and the
public specs permit. The byte-addressed draft now declares that task as
optional. The first A 0/3 protected result is preserved as a failed fairness
reading; after correction the local demo shows A and B at 3/3 on the drawn
variants. A separate S16 predicate correction accepts a justified no-match
refusal in the strict budget case. Neither repair seals the family.

## Result to build

1. Derive a pure outcome from all six frozen slots. Keep the public request
   denominator separate from three protected steps per candidate. Count a public
   request as useful only when every required task completed. Report overlapping
   non-completion categories as incidence, never as a partition.
2. Assess each protected capture controller-side against its reserved task spec,
   resolved state and public mission. Keep the raw capture, variant identity and
   exact protected task results out of the public outcome; release only terminal
   aggregate passed, failed and missing counts and public rule IDs for blockers.
3. Return `INCOMPLETE` for missing or failed slots, `NOT_COMPARABLE` for frozen
   context/candidate drift or invalidated exposure, and `COMPLETE` only for six
   comparable terminal slots. A mandatory public or protected failure blocks
   that candidate before efficiency metrics can influence any decision.
4. Retire a compromised reservation and its items by state change. Preserve all
   outputs, usage, slot rows and business history. An interrupted experiment must
   show failed slots, retained evidence and no automatic retry or refund.
5. Render the outcome in the Compare station and demonstrate the policy offline.
6. Keep protected model calls, tokens and latency out of public efficiency
   metrics while retaining their observations internally. If a frozen budget
   explicitly makes a metric mandatory, unknown or over-limit values block
   eligibility; the current draft has no mandatory service-cost cap.

## Verification

- Baseline: `.venv313/Scripts/python.exe -m pytest --ignore=tests/packaging -q`
  returned 528 passed, 1 skipped, 2 warnings before edits. Final same command:
  556 passed, 1 skipped, 2 warnings after edits.
- Add focused pure tests that fail on the old behavior, with independent faults
  for task identity, optional-task credit, overlapping incidences, clarification
  categories, unknown usage, protected denominator and every status transition.
- Add real database/route tests for frozen context drift, protected acceptance,
  invalidation, restart retention, and private-material projection guards. Replace
  S15's temporary no-outcome assertions with specific S16 assertions.
- Run the focused checks, relevant full offline suite, browser desktop/mobile
  check, `git diff --check`, and post-slice architect review. Record any failed
  first run and what it proved; do not count red-by-crash as coverage.
- Fault the outcome branches one at a time with byte-exact restoration. A
  skipped anchor, incidental crash or timeout does not prove the branch.

The final S16 mutation run caught 27/27 named faults at assertion level and
restored every target byte-identically. Browser fault rendering caught 11/11
deliberate faults after a clean baseline. The final offline demo returned
`PASS_OFFLINE_POLICY`, with zero live calls and no operator seal. See
`00-status.md` for the exact result and limits.

Those three figures are the implementation round's and are superseded by the
2026-09-28 review and the 2026-09-29 repair round. After the eight review repairs
the same commands return: `.venv313/Scripts/python.exe -m pytest tests
--ignore=tests/packaging -q` at 560 passed, 1 skipped, 2 warnings, exit 0, 561
collected, up from 556 because the round added four tests and deleted none;
`tests/slice16_mutation_proofs.py` at 38 of 38 FAIL_CAUGHT with zero SKIP and zero
`restored=False`, up from 27; `tests/pivot_mutation_proofs.py` at 97 of 97
FAIL_CAUGHT with zero SKIP after six moved anchors were re-anchored; `node
tests/client/render_faults.mjs --port 8163` at 15 of 15 rows as expected, up from
12, the three new rows covering the Compare outcome cards; and `node
tests/client/browser.mjs --compare-demo` green at exit 0 with zero uncaught
exceptions, now including a post-comparison reload check. Do not run `pytest tests`
without `--ignore=tests/packaging` under a no-install authorization: that collects
packaging Test 51, which installs from `requirements.lock` over the network. The
authoritative offline figure is therefore 560, not the 561 that the wider command
reports.

## Boundaries

Trusted-local fixtures prove policy and lifecycle only. The one public request
that separates A and B limits the fairness demonstration. No live inference or
Sandbox quality claim follows from an offline pass. Selection, operation and
their invalidation enforcement remain S17/S18 work.
