# S46 stopped-comparison polling correction

The user authorized continuing the offline fixes on 2026-10-25, until half
context. The runtime reports an 828,400-token window; the current continuation
uses a 414,200-token ceiling under that explicit instruction. The first native
usage check reported 186,926 input tokens. Work stops earlier if complete.

The existing summary correction is preserved. S46 stays INCOMPLETE and
UNACCEPTED. Both live actions and all remainders remain closed. No original
database, queued row, protected fixture, S47 checkout or Git index is changed.

## Plan

1. Add failing regressions against the real refresh function and lamp projection.
   A matching stopped comparison must stop polling its queued child; active or
   unrelated parents must preserve existing polling.
2. Correct the client polling decision and comparison lamp. Clarify the planned
   request and missing-output counts after the browser review exposed their
   ambiguous frozen-denominator meaning. Refresh client provenance. No executor,
   persistence, grade or gate decision changes.
3. Prove each new guard with a separate source fault. Recheck the actual stopped
   snapshot for stable display, truthful lamps, disabled choices and native zoom.
4. Run relevant regression, audit preservation, update current records and leave
   a handoff if the context boundary approaches.

Private baseline, source copies and receipts:
`/tmp/shiftwork-s46-polling-20261025/`. The baseline contains 2,007 file hashes,
the unchanged HEAD and empty index. All 317 existing Node tests pass before edits.

## Verified correction

The real `refresh` function now stops scheduling polls only when the loaded run
is an experiment and the qualifying comparison has the same experiment ID and
shift ID and a FINALIZED, FAILED or INVALIDATED state. A queued child remains
QUEUED in the displayed and stored evidence. Active parents, unrelated experiments,
other shifts, diagnostics, operations, unknown parent states and unmatched history
retain normal polling. Prior timers are still cleared.

The room's comparison lamp now derives Running from the parent's PLANNED or
RUNNING state. Reserved or running children cannot make a stopped comparison
appear active. This restores truthful state presentation; no choice or executor
permission changes. The existing terminal-parent and identity guards retain
loading, error and historical presentation behavior.

The outcome table now has a full-width note: "Public requests are planned totals.
Missing outputs includes planned requests that never ran." The domain's `_metrics`
intentionally includes absent planned slots/repetitions in that count. The table
retains its short labels and the exact recorded values, including
18 planned requests and 16 missing outputs for each stopped candidate. Those
16 are not relabelled as measured execution failures.

## Failing proof and fault controls

The new `tests/client/stopped_comparison.test.mjs` invokes the actual refresh
function and actual lamp projection. Against pre-fix source, nine checks fail:
three stopped-parent polling cases and six stopped-parent/child lamp combinations.
The remaining controls preserve active/unrelated polling. All 23 final new cases
pass, including absent and terminal runs and the original one-second interval.

Eleven separate source edits fail their intended assertions: bypassed parent
stop, run purpose, comparison kind, experiment identity, shift identity, terminal
run handling, each of the three stopped parent states, stale-child lamp activity
and active-parent lamp activity. Clean and restored controls pass. Twelve earlier
proposal-summary source faults were also rerun against the current client and
still trigger their intended assertions. Both fault runners use disposable source
copies and leave working source unchanged.

Final fault receipts are under `verified-poll-faults/` and `verified-summary-faults/`
inside the private polling receipt directory. They are 23 new UI fault proofs,
not an addition to the historical implementation matrix as unique backend proof.

## Actual stopped-snapshot review

The existing read-only terminal review remains
`http://127.0.0.1:54137/?board=bookshop#compare`. Its copied database uses read-only
connections, skips startup reconciliation and rejects HTTP mutations. No original
store is opened by normal app startup.

The actual stopped comparison now stays loaded throughout each 4.2-second
observation at 1440x1000 and 390x844, at native Chrome 100% and 200%. Each cell
records only the initial board read, one stable ready observation, an Incomplete
lamp, INCOMPLETE outcome, three retained and six missing public batches per
candidate and both choices disabled. No mutation request or runtime exception
occurs. The count clarification preserves both recorded values. Screenshots
are retained and inspected.

Native zoom uses Chrome's existing profile page-zoom preference, with viewport
metrics kept in desktop mode to preserve that zoom. The 390px target at 200%
has 195 CSS pixels, DPR 2, pinch scale 1 and CSS body zoom 1. There is no
document-width overflow. This is a mobile-sized desktop Chrome test, not a
physical-phone or assistive-technology test. Private personal-browser state is
unchanged. Receipts: `browser-review.txt`, `browser/results.json` and screenshots.

An earlier clarification used a long metric label. Its native-200% screenshot
exposed excessive word splitting in the narrow table, so that layout is excluded
and retained under `browser-long-label-excluded/`. The explanation now occupies
its own full-width paragraph; the metric labels and counts retain their existing
shape. The verification failure and correction are recorded in MISTAKES.md.

The review uses the exact stopped evidence with its twelve queued rows. It does
not prove a continuous generation/run/accept/save/compare browser journey, a causal
customer-facing repair or learner gain. Both live allowances remain closed.

## Final regression and preservation

Fresh full Python regression passes 1,761 tests with one live-only skip, one
installation function deselected by exact node ID and two existing warnings.
The full Node suite passes 340 tests. The nine asset-closure cases pass again
after the final copy/provenance edit; they are a subset of Python coverage, not
nine extra distinct tests. Syntax and `git diff --check` pass.

```sh
SHIFTWORK_PYTHON=/Users/jayd0/Desktop/shiftwork/.venv/bin/python /Users/jayd0/.local/bin/node --test tests/client/*.test.mjs
/Users/jayd0/Desktop/shiftwork/.venv/bin/python -m pytest -q --deselect=tests/packaging/test_clean_env_install_and_run.py::test_clean_env_install_and_run
/Users/jayd0/Desktop/shiftwork/.venv/bin/python -m pytest -q tests/packaging/test_client_asset_closure.py
```

Receipts: `full-node.txt`, `full-python.txt`, `final-asset-closure.txt`,
`focused-green.txt` and `red.txt` in the private polling directory.

The 2,007-file continuation baseline has exactly nine scoped file changes and
1,998 unchanged files. All 106 protected-material and 66 older-evidence hashes
match. Both original actions' databases, intermediate checkpoints, closures and
receipts are unchanged. All twelve queued runs remain queued without outputs or
observations. Fresh read-only reconciliation reproduces the provider deadline,
skipped protected capture, unchanged operational ledger and unchanged selections.
Current provenance matches both changed client files. Branch and HEAD are
unchanged and the index is empty. Audit: `preservation.py` and
`final-preservation.json` in the private polling directory.

Only these files changed in this continuation: `app.js` polling and count note;
`workplace-story.js` parent-state lamp; their `workplace-assets.json` hashes;
`MISTAKES.md`; the supporting brief and status; the S46 continuation, second-result
and earlier UI records. New files are this correction record and
`tests/client/stopped_comparison.test.mjs`. The earlier proposal tests and every
Python production file are unchanged by this continuation. No deletion, dependency,
framework, executor, grade, fixture or stored evidence change was needed.

The known offline UI defects are corrected. S46 remains INCOMPLETE and
UNACCEPTED. No new provider call, Sandbox operation, installation, selection,
operation, acceptance, commit, merge, push or deployment occurred. No live
allowance or unused remainder is reopened by this result.
