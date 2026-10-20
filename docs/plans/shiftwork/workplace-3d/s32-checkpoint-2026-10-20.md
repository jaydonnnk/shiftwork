# S32 local implementation and evidence checkpoint

Updated: 2026-10-20 Asia/Singapore.

**Status: S32 ACCEPTED on local evidence, 2026-10-20. Publication in progress.**
The user supplied the S32 handoff prompt on 2026-10-20, authorizing local
implementation, tests and disposable evidence on `shiftwork/slice-32` from main
`b7dff05` under `/tmp/shiftwork-s32-*`. That authorization did not cover commits,
pushes, merges, deployment, credentials, provider calls, protected fixtures,
CI/lint/lockfile/packaging changes, gate reopenings or S33. The user then accepted
S32 with "Okay yea i accept it please commit the changes and push to main" and
authorized the working-tree commits and the push to main. The branch was created
from the main tip `b7dff05`. The publication commit range is recorded at the end
of this checkpoint after the fast-forward.

## Scope and delivered contract

The S32 contract is in [04-slices.md](04-slices.md), "S32: operate the selection
and explain recorded consequences". This round delivers its bounded scope:

- the Bellwether consequence wall distinguishes QUEUED and RUNNING (pending),
  FAILED, FINALIZED with failed mandatory checks, FINALIZED without independent
  checks, and a fully linked success;
- the wall shows chain status, count agreement, type-histogram agreement,
  totals, and off-allowlist events as text-only;
- wall events carry source (current, historical, administrative), link state
  (linked, incomplete, conflict, historical, none), meaning, version, reason
  code, contradiction reason and incident joins;
- failed partial operations preserve their confirmed negative events and
  incidents without success styling, and a failed run with no captures invents
  no consequence;
- the selected evidence bridge labels current, historical and administrative
  events and negative meanings;
- one new current linked synthetic event from the exact operating
  selection/version/shift/run produces at most one `linked-consequence`
  transition, one 320ms scene trace and one "Recorded evidence added" label;
- duplicates, removals, history, conflicts, context changes, administrative
  events, missing routes and non-operation runs stay quiet;
- the host retains its last consistent view across reset and conflict, advances
  it only on a consistent accepted view, and replays at most one arrival across
  a remount; the label fires only when the scene actually starts the trace;
- the room has a wall panel and a plate-to-wall trace line; wall colour is
  neutral for conflict, red for current negative or pending evidence, green for
  a linked current event and blue otherwise;
- no reducer, grading, endpoint, operation worker or second-board behaviour
  changed. S33 inheritance has not started.

## Production changes (uncommitted)

- `shiftwork/client/workplace-view.js`: count and histogram agreement fields,
  incident open and resolution joins, run failure/output/check counts, wall event
  projection with source/link/meaning fields, and the linked-consequence diff
  eligibility (new identity, current source, linked route, synthetic event,
  operation purpose, current shift, exact selection and version).
- `shiftwork/client/workplace-host.js`: keeps the last consistent reference
  across reset and conflict, computes transitions at mount, applies them once,
  and fires `onConsequence` only when the scene starts a trace.
- `shiftwork/client/workplace-scene.js`: wall panel, trace line, wall colour
  rules and the 320ms trace with reduced-motion, suspension and disposal
  settlement; `apply` reports whether it started a consequence.
- `shiftwork/client/workplace-rooms.js`: wall board, rail, four paper cards,
  `anchors.wall` and `stationAnchors.ledger`.
- `shiftwork/client/app.js`, `shiftwork/client/index.html` and
  `shiftwork/client/styles.css`: consequence wall status, totals, event rows,
  trace label, incident join data, selected-evidence labels, wall row colours
  and line breaks.
- `shiftwork/client/workplace-assets.json`: refreshed digests for all changed
  client files. All ten manifest rows match their current files.

## Test changes (uncommitted)

- `tests/client/workplace_view.test.mjs`: 95 checks, including wall labels and
  joins, count and histogram agreement, incident resolution, link
  contradictions, arrival guards, quiet cases and three host continuity checks.
- `tests/client/workplace_faults.mjs`: 89 source controls, adding host conflict
  reference, reset reference, mount replay, consequence started and consequence
  emitted.
- `tests/client/workplace_s32.mjs` (new): seven fresh-preview modes (journey,
  queued, failed, missing, partial, motion, conflict) with public-record
  comparisons, screenshots and trace assertions.
- `tests/client/workplace_s32_faults.mjs` (new): eight browser fault rows with
  clean, fault and restored phases plus source digest checks.
- `tests/client/workplace_browser.mjs`: S32 instrumentation and faults for the
  wall trace, label, callback, conflict and reset references, mount replay and
  settlement.
- `tests/client/browser.mjs`: the bookshop operation journey now asserts the
  wall event and board totals.

## Verified evidence, 2026-10-20

All receipts are disposable local artifacts under `/tmp/shiftwork-s32-*`. The
retained `http://127.0.0.1:8898` preview was never used, replaced or restarted.
No live provider, deployment, hosted mutation or protected fixture was used.

### Node and source faults

- `node --test tests/client/workplace_view.test.mjs`: 95 pass, 0 fail, 0
  skipped.
- `node tests/client/workplace_faults.mjs /tmp/shiftwork-s32-s32a/source-faults`:
  89 of 89 PASS, production unchanged. Receipt
  `/tmp/shiftwork-s32-s32a/source-faults/faults.json`.

### S32 fresh-preview controls

Receipts in `/tmp/shiftwork-s32-s32a/controls/*/out` and
`/tmp/shiftwork-s32-s32a/controls-summary.json`. Seven of seven passed on the
final source.

- `journey`: run-0009 FINALIZED on ver-0002 and sel-0002; public ledger seq 5
  SALE_COMPLETED linked; wall trace count 1 at 320ms with one arrival; totals and
  incident joins match the public records; quiet counts unchanged and zero
  traces after reload; 1280px, 390px and graphics-failure screenshots captured.
- `queued`: run-0009 QUEUED and RUNNING with pending text and no current
  consequence; the final FINALIZED view added one linked event and one 320ms
  trace. `queued.json`.
- `failed`: FINALIZED with 3 failed mandatory checks; two current negative
  INCIDENT_OPENED events for BWB-04 and BWB-05, no sale; one 320ms trace with
  two arrivals; the selected evidence shows three fail checks. `failed.json`.
- `missing`: FAILED SERVICE_UNREACHABLE with 0 outputs and 0 checks, no new
  event; the wall keeps 3 historical incidents and LIMIT_DECLARED; no trace.
  `missing.json`.
- `partial`: FAILED internal after confirmation; two current negative events
  remain; one 320ms trace with two arrivals; totals agree. `partial.json`.
- `motion`: reduced motion starts no trace; an active trace is cancelled and its
  wall emphasis settles; a duplicate view replays nothing. `motion.json`.
- `conflict`: a conflict view starts no trace and does not clear the consistent
  reference; the confirmed linked view produces one trace; a reset plus remount
  produces exactly one more 320ms trace for the confirmed event.
  `conflict.json`.

### S32 browser faults

`node tests/client/workplace_s32_faults.mjs /tmp/shiftwork-s32-s32a/faults`:
8 of 8 PASS, production unchanged. Each row ran clean, fault and restored
phases on a fresh browser; the fault phase failed its named assertion:

- trace label omitted: "The trace label text is missing".
- trace omitted: "The confirmed linked consequence did not start a trace".
- trace shortened: "The evidence trace did not use 320ms".
- callback omitted: "The consequence callback did not fire exactly once".
- conflict reference cleared: "The confirmed linked consequence did not start a
  trace".
- reset reference cleared: "The reset and remount lost the confirmed arrival".
- mount replay omitted: "The reset and remount lost the confirmed arrival".
- settlement omitted: "Reduced motion did not cancel the evidence trace".

Receipt `/tmp/shiftwork-s32-s32a/faults/browser-faults.json`.

### Assets

`pytest tests/packaging/test_client_asset_closure.py -q`: 9 passed, 2 existing
warnings. The manifest has 10 rows and no mismatch. The full packaging install
suite was not authorized and was not run.

### Existing S30 and S31 controls

All 30 fresh-preview controls passed as expected on the final source: 7 S31 clean
journeys, 2 expected failures with their own messages, 8 ownership clean and
mutation pairs, selection, failure recovery, expanded, motion, page-cache,
lifecycle and exact viewports. Receipt
`/tmp/shiftwork-s32-final2/controls-summary.json`.

### Board journeys

- `bookshop`, `gtm` and `northline` each exited 0 against fresh disposable
  previews. Receipt
  `/tmp/shiftwork-s32-final2/journeys-final/results.json`.
- The bookshop `--selection-demo --journey-demo` variant exited 0 and asserted
  wall event seq 5 against the public ledger and board totals; the plain variant
  also exited 0. Receipts
  `/tmp/shiftwork-s32-final2/bookshop-variants-final/results.json` and
  `selection-journey/out/browser/browser-report.json`.
- One failed bookshop attempt used the assist-enabled preview and the wrong
  event-row marker; both failures and their repairs are recorded in
  `MISTAKES.md`. The failed receipts are retained under
  `/tmp/shiftwork-s32-existing/journeys-2026-10-20*`.

### Performance

Receipt `/tmp/shiftwork-s32-final2/perf-final/out/performance.json`. Host macOS
26.5.1 build 25F80, arm64, AC power. Chrome 155.0.8059.84 headless, ANGLE Metal
on Apple M4 Pro. This is a synthetic local measurement, not physical-device,
power or native performance proof.

- 1280x720 at DPR 1: five cold starts 2840.6 to 2978.4ms against the 3000ms
  budget; three 30-second samples had median 16.7ms, p95 17.6ms, 2304 triangles,
  22 draw calls, idle frames 0 and estimated allocation 21,840,384 bytes against
  48MiB.
- 390x844 at DPR 1: five cold starts 2847.5 to 2961.9ms against the 4000ms
  budget; samples had median 33.3ms, p95 33.8 to 34.2ms, 1188 triangles, 14 draw
  calls, idle frames 0 and estimated allocation 1,907,776 bytes against 24MiB.
- No budget misses.

### Full non-packaging suite

Command: `.venv/bin/python -m pytest tests --ignore=tests/packaging -q`.
Result: **1454 passed, 1 failed, 1 skipped, 2 warnings in 182.27s**. The failure
is the known
`tests/executor/test_conformance.py::test_conformance_suite_recorded_local[port_dead]`
mismatch: REQUEST_TIMEOUT where SERVICE_UNREACHABLE is expected. It matches the
S30 and S31 baseline and is carried, not introduced. The full suite log is
`/tmp/shiftwork-s32-final2/full-suite.log`.

## Post-slice cleanup

The architect-reviewer scan found no orphaned files, fixtures, routes, handlers
or scratch files in the repository. It removed one unused helper,
`selections`, from the S32 control runner as the only dead test code. The new
projection fields and incident identity fields are retained because the tests
and the slice contract use them. The checkpoint, both status files, the plan
brief and MISTAKES.md were updated for this round. S33 has not started.

## Acceptance and publication, 2026-10-20

The user accepted S32 with "Okay yea i accept it please commit the changes and
push to main" and authorized the working-tree commits and the push to main. The
work is committed on `shiftwork/slice-32` in focused commits for the projection,
the consequence wall and trace, the unit and source fault coverage, the S32
control and fault runners, and the acceptance records. The publication range is
recorded at the end of this checkpoint after the fast-forward.

## Limits

- The failed, partial, missing and queued controls use disposable preview
  mutations around the production operation path. They prove the client
  projection and presentation, not a production failure-injection mechanism.
- The trace label is a status message that remains after the 320ms scene
  animation; the scene trace itself settles. The label is not a second
  animation.
- Incident resolution joins are covered by projection fixtures and source
  faults; the live S32 operation produced incident opens, not a resolution.
- The evidence is headless Chrome only. No physical device, named screen reader,
  Windows, Edge, Firefox, Safari, physical narrow viewport or comprehension
  session was tested.
- Queue and running timing uses deliberate disposable delays. It is not a
  network-latency or production-scheduler claim.
- No commit, push, merge, deployment, live provider call, protected fixture
  change, CI/lint/lockfile/packaging change or S33 work was performed.

**Stop boundary.** S32 is accepted on the evidence above and is being published
to main. S33 requires its own go-ahead and has not started. No deployment
follows.
