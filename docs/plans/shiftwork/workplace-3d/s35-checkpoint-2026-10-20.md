# S35 local implementation checkpoint, 2026-10-20

## S35 ACCEPTED by the user, 2026-10-21

The user approved S35 after their own manual testing and directed closure. The
harness has no qualifying native 200% receipt. All 413 visible observer records
are `dirty: false`, none is 378x413 CSS pixels, focus is empty in the late
manual attempt, and that attempt ran full-screen at 125% zoom with two product
commands. The native 200% effect is accepted on the user's manual test, not
passed by the harness. The accepted archive's exact size and SHA-256 are in
`/tmp/shiftwork-s35-postcss-20261020-3/archive-accepted.json`. The work remains
uncommitted on `shiftwork/slice-35`; no commit, push, installation, publication,
deployment, credential or live call occurred.

## USER-REQUESTED STOP AND HANDOFF: 2026-10-20

This section supersedes all earlier completion/preview statements in this file.
The user requested a copy-paste handoff while native 200% checks were unfinished.
S35 remains INCOMPLETE, unaccepted and unpublished on `shiftwork/slice-35`, HEAD
`cd532d6aba76486f1d48cb3798d8a95b5ace2fe6`. Nothing was staged or committed.
All inherited unstaged/untracked work remains. Exact entry bytes and hashes are
`/tmp/shiftwork-s35-continuation-20261020-2/entry-work.zip` and `entry-hashes.json`.

### Verified before the last native CSS repair

- 206 Node checks; 152 projection/host controls; 35 served renderer/label/wheel
  controls, each with clean/intended-failure/restored proof; nine asset and six
  environment checks. The full non-packaging repeat retains 1454 passes, the
  known port_dead failure, one skip and two warnings.
- Forty-eight actual-content keyboard/touch/zoom/graphics observations pass.
  Northline content scrolls into reach with panel focus and dirty caret/text kept.
- Thirty actual-room switches, complete geometry/material accounting, partial
  construction cleanup, double disposal, nine failure workbenches and four final
  retry modes pass. Both full performance tiers, compact cap and latency pass.
- r6 extraction passes all three complete journeys and rooms, Northline fallback,
  network-block self-tests and 12-asset HTTP/MIME/hash/license/provenance closure.
- The later Northline diagnostic executes new `ver-0005` with retained `ver-0003`
  content; choice `sel-0002` / `ver-0002` and pilot/handover ledger/DOM stay unchanged.
  This is a test-control DIAGNOSTIC, not a paired later-condition comparison.
- Freeze completion now restores Diagnostic controls. Operational history excludes
  EXPERIMENT and preserves both OPERATION and LEGACY_OPERATION. A real migrated
  v5 successor has direct RED/GREEN proof. Fresh reviews closed findings in those
  changes and the packaging timeout/URL/checkpoint handling.

### Latest change and incomplete proof

Native Safari 26.5 build 21624.2.5.11.4 rendered the actual WebGL2 workshop. It then
reproduced a genuine 200% layout failure at 378x413 CSS pixels: root scrollWidth
410, owned by the role picker, despite all element/text bounds fitting. The
observed select-control override reduced scrollWidth to 378. The same narrow
repair is now in production `styles.css:59`: `overflow: hidden; text-overflow:
ellipsis` on the select only, not the page. `workplace_browser.mjs:118` has the
updated zoom-fault anchor, and workplace-assets.json hashes were refreshed.

The production repair has three passing native keyboard cases at 100%, actual
756x827, for Acceptance/Rollout/Handover, with real WebGL2, panel focus, controls
at least 44px, no overflow, zero product commands and preserved dirty node/text/
caret. Receipts are `native-safari/acceptance-1.json`, `rollout-1.json`,
`handover-1.json`, each `good: true`, with PNGs. The final production 200% page
was measured at 378x413 with no overflow, but the three settled keyboard/content
cases did NOT finish. There are no passing final `*-2.json` receipts.

Native automation had hidden-page suspension, Page Menu/AX errors and explicit
"user changed Safari" interruptions. These are retained attempts. Coordinate and
scroll calls returned noWindowsAvailable. Ctrl+Cmd+F twice made the owned private
window visible while restoring 756x827. A true `hidden: false` observation is
required; old pixels or a later pass do not erase failed attempts. Native zoom was
set through the actual Page Menu percentage selector. No audible AT claim exists.

The disposable observer lives in
`/Users/jayd0/Documents/Codex/2026-10-20/background-shiftwork-s35-has-local-implementation/work/s35_native_preview.py`
with prior variants beside it. It injects observation only into a disposable
served HTML copy and posts JSON to a local test endpoint. Its final version uses
an invisible output, real DOM geometry, scroll owners and product-command counts.
`native-observations.jsonl` records all attempts; source port distinguishes them.
8376 used a test-only CSS override; 8377 used the repaired production stylesheet.
No production test hook or protected fixture was edited. Native dirty comments
were never saved to an artifact or sent to an executor.

### Post-repair layout and fault checks: 2026-10-20

Receipt root `/tmp/shiftwork-s35-postcss-20261020-3`. The preview ran on 8380
against a copy of the open comparison database and was stopped after these
checks.

- The official four-cell exact-viewport matrix (Northline, 640x900 and 390x844
  at 100%/200%) passes. Root scrollWidth equals innerWidth in every cell: 640,
  320, 390 and 195.
- A disposable three-board picker matrix covers bookshop, Northline and GTM at
  756x827 100%/200% (378x413 CSS pixels) and 390x844 200% (195x422). All nine
  cells pass: scrollWidth equals innerWidth (378 or 195), the select stays inside
  the viewport, and the repaired style computes `overflow: clip` with
  `text-overflow: ellipsis`.
- The official `zoom-omit-picker` fault fails the exact assertion at
  `tests/client/workplace_browser.mjs:807` with a 195px viewport and 266px root
  scrollWidth. The check is fail-capable.
- A faithful pre-repair control temporarily served the exact selector
  `width: 100%` without the clip and ellipsis declarations. In Chrome the 378px
  geometry still measured 378, so the layout assertion did not fail; only the
  declaration assertion failed. Chrome does not reproduce the native Safari
  overflow. The file was restored byte-identically, SHA-256
  `f869201783703f37545611304e03ca6370600b1d99c70193ced1a5f38edbf44e`, and the
  restored CSS passes all nine cells again. Native 200% remains the only proof
  that the repair changes real layout.
- Fresh checks: 206 Node, 152 source controls with production unchanged, 35
  served controls with production byte-identical, nine asset checks, six offline
  environment controls. The non-packaging regression is 1454 passed, the known
  `port_dead` failure, one skip and two warnings in 159.17 s. `git diff --check`
  passes.

An independent review of the CSS repair raised three points. Two are closed.
First, the narrow-picker checks did not assert the repaired declarations, so
deleting them could stay green in Chrome. `workplace_browser.mjs:809` now
requires the narrow select to compute hidden-or-clip overflow with ellipsis.
Serving the exact pre-repair selector fails that guard
(`exact-prebuild-picker.log`), and the restored CSS passes. Second, the
registered `zoom-omit-picker` path goes through `runZoom`, not the exact-viewport
runner. `zoom-clean-bookshop.log` passes 640/320/195 and `zoom-fault-bookshop.log`
fails the intended assertion at `workplace_browser.mjs:741`. The third point is
not closed: Chrome still measures 378/378 for the pre-repair selector, so the
layout effect at the native 378x413 geometry is tied only to the native Safari
run, which is still pending.

The accepted source archive is `/tmp/shiftwork-s35-postcss-20261020-3/
shiftwork-s35-source-final.zip`, with its exact size and SHA-256 recorded in
`archive-accepted.json`. Its proven source and test bytes pass a fresh extraction
of all three complete journeys and rooms with external assets blocked, and 16
assets pass HTTP/MIME/hash/license/provenance closure with imports resolving
inside the extraction. No installation occurred. This archive supersedes r6 and
is rebuilt after the final record edits.

Native manual attempt: the observer page opened at 756x827 in an owned Safari
window, but it ended full-screen at 125% zoom. All 413 visible records are
`dirty: false`, none is 378x413 CSS pixels, and the final attempt has empty focus
and two product commands. There is no passing harness case. The user accepted
this gap on 2026-10-21 based on their own manual test.

### Archive, environment and stop state

The current output `shiftwork-s35-source.zip` is the r6 PRE-NATIVE-CSS snapshot,
11,300,677 bytes, SHA-256
`383c4ffae9d4703337df7cb151d5a88a9ed03cf758b159659f55f563c4a354af`.
It predates the last select CSS, zoom-fault anchor and manifest edits. Its earlier
closure/journey/performance receipts must NOT be called verification of a new
final archive. The output is at
`/Users/jayd0/Documents/Codex/2026-10-20/background-shiftwork-s35-has-local-implementation/outputs/shiftwork-s35-source.zip`.
Updated focused layout/fault checks, final native 200% cases, review of the last
CSS change and a rebuilt/reverified archive remain open. Earlier renderer and
performance evidence retains its exact source/timing limits.

Installed Chrome is 155.0.8059.85; the contract names .84. Exact .84 is unproved,
not silently substituted. Clean locked installation remains required and separately
unauthorized. Publication, deployment, credentials, live calls and protected-fixture
edits remain unauthorized. No requirement was waived and no S36 is assigned.

All manually owned previews at 8363 and 8372-8377 were stopped for handoff. Earlier
8364-8371 previews were already stopped. Packaging helper previews exited through
its cleanup. The owned Safari private window may remain open at a stopped preview;
its UI/AX state is not assumed current. `handoff-stop.json` records the stop.
`git diff --check` passed at the user-requested stop. No new tests ran after that
stop request. The earlier full regression predates the last narrow UI changes.

### Files changed this continuation

- app.js:1292-1297 history purpose guard/copy; 1367 freeze completion;
  1565-1579 selected-content scroll targets.
- styles.css:59 select overflow repair; 329 selected-content scroll margins.
- workplace-assets.json current public-source hashes.
- workplace_browser.mjs:47-70 label observation; 322-360 marker/wheel faults;
  447-455 complete allocation observation; 791 onward layouts, real incident
  identity/cache-refresh proof and Northline latency targets.
- workplace_s35.mjs:7 workshop/guard probes; 61 legacy history; 76 content reach.
  workplace_s35_controls.mjs contains 35 isolated served controls.
- northline_browser.mjs:63 editing preconditions; 251 reach; 291 later diagnostic
  and pilot/handover separation. northline_preview.py restores disposable pins
  and gates its exact-B diagnostic test control at line 95.
- test_clean_env_install_and_run.py:151 owns timeout descendants; 166 supplies
  reusable extracted three-journey/room/fallback proof, using comparison snapshots.
- README, MISTAKES, root/scoped status, brief, plan/checkpoint/handoff record scope
  and evidence. Inherited scene/room/host/view/index and source-control bytes were
  unchanged during this continuation, as recorded before the last CSS repair.

### Prompt for handoff review

Adversarially review the uncommitted S35 continuation against workplace-3d/04-slices.md
S35 and visual-spec section 8. The latest user-requested-stop sections above are
current. Assume the work may be flawed; stress-test actual code and evidence, not
claims. Assess weak assertions, hidden assumptions, scope creep, resource ownership,
experiment/operational/legacy separation and the latest Safari select-overflow fix.
Do not pass tests for the sake of passing. Native 200% cases and final archive
revalidation remain unfinished; no acceptance is claimed. Installation, publication,
providers and protected fixture edits remain unauthorized. Report PASS / ISSUES
FOUND / FAIL with exact paths, lines and outputs. Deliver your verdict and wait
for instructions.


## Second continuation, 2026-10-20, final source checks

The final source candidate is 11,300,677 bytes, SHA-256
`383c4ffae9d4703337df7cb151d5a88a9ed03cf758b159659f55f563c4a354af`.
`archive-r6.json` records its output path and `/tmp/shiftwork-s35-continuation-20261020-2/extracted-r6`.
`extracted-proof-r6/complete-browser-results.json` passes all three complete
product journeys and all three actual rooms. Each journey blocks external asset
requests and self-tests that interception. Northline's extracted constructor-failure
workbench also passes. `extracted-r6-assets.log` passes all 12 assets with exact
HTTP/MIME/hash/license/provenance closure, with imports asserted inside extraction.
Installed dependencies were reused. No clean installation occurred.

The extracted Northline later proof completes diagnostic
`experiment-northline-shift-03-d1` against `ver-0005`, a newly frozen copy of
retained `ver-0003` with identical content. The selected version remains
`sel-0002` / `ver-0002`. Its source operation is `run-0009`; pilot/handover ledger
and displayed record payloads stay unchanged. This is a test-control diagnostic,
not a paired later-condition comparison or inference proof. Actual incident
inspection and synthetic persisted-pageshow retention use each open comparison
checkpoint, because the successful pilot resolved its starter incident.

That flow reproduced a second production defect: `renderNext` placed the diagnostic
run under operational history. `history-diagnostic-red.log` is the direct failure;
`history-diagnostic-green.log` and the extracted journey exclude it after repair.
The final guard admits OPERATION and LEGACY_OPERATION and retains the prior
later-trial exclusion. My first guard omitted legacy operation; the migrated
v5 successor in `legacy-migrated-red.log` reproduces that omission and
`legacy-migrated-green/legacy-history.json` passes the final guard with
`run-v5-0001` and its explicit legacy label. The first legacy preview was an
ordinary operation and correctly failed its precondition, not the guard.

Final focused checks: 206 Node checks and 15 asset/environment checks, the latter
comprising nine asset checks and six environment controls with two warnings.
`source-controls.log` passes all 152 isolated projection/host controls with source
unchanged. `regressions-r2.log` retains 1454 passes, one skip, two warnings and the
known port_dead failure. That repeat preceded the final legacy-only UI correction;
backend bytes did not change, and the final client has the extracted journey,
focused Node/asset and migrated-browser evidence above. Fresh bounded reviews
found and resolved timeout cleanup and legacy-purpose omissions. No remaining
review finding is open in those reviewed changes.

The installed environment is Chrome 155.0.8059.85, Safari 26.5 build
21624.2.5.11.4, macOS 26.5.1 build 25F80, Apple M4 Pro and 24 GiB RAM, on battery.
The compatibility contract names Chrome 155.0.8059.84. That exact patch remains
unproved; the .85 evidence is not silently substituted as an .84 pass.
Native Safari still lacks actual 3D and exact zoom proof. Native coordinate and
scroll operations returned `noWindowsAvailable`, including in a new private window.
An asynchronous request asks the user to foreground Safari. No answer or waiver
is inferred. Performance completed as recorded below.

The earlier first-candidate source archives and all rejected attempts are retained
in the receipt root. Two extraction failures came from a wrong base URL and a
resolved-incident world; comparison checkpoints now preserve the real failure
precondition. Later corrections followed actual failed assertions. No assertion
was removed to obtain a green result.


This section supersedes the earlier next-check summary. Branch and HEAD remain
`shiftwork/slice-35` and `cd532d6`. Entry work is preserved in
`/tmp/shiftwork-s35-continuation-20261020-2/entry-work.zip` with exact hashes.
No installation, publication, deployment, credential, live call or protected
fixture edit is authorized or performed. S35 remains incomplete and unaccepted.

- Actual content reach reproduced six 200% zoom failures. The Northline narrow
  selection now retains panel focus and scrolls the captured request, pilot action
  or runbook into reach, with an 8px margin. `content-final/content-reach.json`
  and `content-fallback/content-reach.json` each contain 24 passing keyboard/touch
  observations over 640x900 and 390x844 at native 100%/200% zoom. Unsaved editor
  node, text and caret survive. The first repaired attempt clipped fractional
  pixels and is retained as `content-green`; `content-red` retains the original.
- `exact-final` and `contrast` pass the shared viewport, editing and contrast checks.
- `renderer-controls-final/results.json` records 35 served controls, each clean,
  intended assertion and restored, with production bytes unchanged. Marker types,
  boolean/synthetic/link/conflict/count guards, declaration source/version, both
  limit labels and TorusGeometry disposal are isolated. The first control run
  rejected an inaccurate expected assertion for the declaration type fault.
- `graphics-faults.log` passes all nine Northline graphics failures with the HTML
  workbench, evidence, dirty editing, caret/focus and a valid offline save retained.
- `lifecycle-all-resources` passes thirty actual-room switches, one context,
  stable warm allocations, partial construction cleanup and double disposal.
  Resource instrumentation now counts every registered geometry/material, not
  just the first matching local name. `lifecycle.log` also passes four retry modes.
- A later browser flow reproduced a disabled Diagnostic button after freezing.
  `freeze-diagnostic-red.log` is the direct failure. `freezeCandidate` now rerenders
  investigation controls after clearing pending state. A fresh reviewer found the
  repair narrow and safe. The later journey is still being verified; its earlier
  edit timing, snapshot pin and diagnostic trial-field mistakes remain receipts.
- Native Safari reached Northline and changed station, but remained on static
  art with "Refreshing recorded state". Reload did not establish actual 3D.
  Native scroll calls also returned `noWindowsAvailable`; keyboard scrolling
  worked. This is unresolved, not Safari 3D or zoom acceptance. The owned tab closed.
- `verify_three_browser_journeys` adds repeatable extracted-source checks without
  installing. Review found that a timed-out Node runner could orphan Chrome.
  Owned process groups now terminate descendants; `timeout-cleanup.log` proves it.

Packaging, complete later/history proof, both performance tiers, fresh regressions
and final review/cleanup remain in progress. Clean locked installation remains
required and separately unauthorized. Earlier S35 notices are historical.


## Continuation checkpoint, 2026-10-20

This section supersedes the earlier suspected-edge and 144-check summary below.
S35 remains INCOMPLETE, unaccepted and unpublished on `shiftwork/slice-35`,
HEAD `cd532d6aba76486f1d48cb3798d8a95b5ace2fe6`. The user's "Please proceed"
resumed local work. The existing dirty/untracked work was preserved, with its
entry bytes archived in `entry-work.zip` under the new receipt root.

Receipt root: `/tmp/shiftwork-s35-continuation-20261020-1`.

- Fresh entry baseline: 143 Node checks. The earlier 144 count was not reproduced.
- `boundary-red.log`: 28 named failures reproduced absent-run crashes and truthy
  non-boolean synthetic admission across Northline and GTM outcomes.
- `final-node.log`: 206 checks pass. Run presence now precedes dereferencing,
  synthetic admission requires boolean true, and absent-run historical records
  remain visible and quiet. Redundant link-presence checks were removed because
  linked/historical state already requires derivation.
- `source-faults-final/faults.json`: all 152 in-memory source/host controls pass
  clean, intended assertion, restored. Production view and host stayed unchanged
  throughout this sweep. The first two attempts retain the masked handover
  scalar-reference fault and ambiguous station-anchor error. The scalar test now
  keeps cause-version equality intact while testing scalar type.
- `northline-journey-repaired.log`: full post-change existing Northline UI journey
  passes with TRUSTED_LOCAL pins, explicit selection, pilot, inheritance and close.
  The initial attempt failed an obsolete static-art-only assertion. Ready graphics
  now require real WebGL2; actual unavailable graphics retain the fallback check.
  This journey does not yet exercise later-alternative/history separation.
- `labels-red.log` and `handover-label-red.log`: independent browser failures
  preceded the permission-map and administrative-handover wording repairs.
  `labels-green/workshop.json` and `labels-green.log` pass actual two-wheel/five-
  marker rendering, negative marker inputs, aggregate counts and both visible
  limits. SceneViews in these marker checks are synthetic. Served-source renderer
  mutation proof remains pending.
- `final-assets.log`: nine asset checks pass with two existing warnings.
- `room-navigation/browser.json`: real Northline room and native canvas station
  picks pass at 1280, 640 and 390px, including recorded failure inspection.
- `exact-initial/exact-viewports.json`: 640x900 and 390x844, each at 100% and
  native-profile 200% zoom, pass keyboard/touch panel focus, target size, overflow,
  WebGL and editor Escape checks. This helper still lacks actual selected-content
  reach assertions. It does not close the carried Acceptance/Rollout/Handover case.
- The shared helper now admits Northline station navigation and tracks wheel
  geometry. Its 30-switch expectation now requires three real rooms. Northline
  is admitted in the performance runner. Those lifecycle/performance changes
  have syntax checks only; their full execution remains pending.
- `cleanup-scan.json`: bounded changed-file scan, no deletion. Inherited scene,
  room, host and CSS bytes match session entry. Full final review/cleanup is open.
- `git diff --check` passes. The 8361 and 8362 owned previews were stopped.
  The closed pilot database is `northline.db`. The open comparison copy is
  `open.db`; `northline-input/comparison.db` is its untouched source checkpoint.

The runtime log reported 170444 input tokens at the phase-boundary check.
New work stopped near the 175k limit; only running checks and consistent handoff
records were finished. Full regression outcome is recorded separately below.
No installation, Git publication, deployment, credential, live call, backend,
lockfile, CI or protected-fixture edit occurred. No acceptance target was waived.

Next concrete unresolved check is actual selected-content reach for Acceptance,
Rollout and Handover at the exact keyboard/touch/zoom matrix, followed by served
renderer/label/cleanup mutations. Nine graphics failures, partial initialization,
retry/double disposal, thirty real-room switches, both full performance tiers,
native Safari, later/history, the other two post-change product journeys, fresh
extracted delivery and separately authorized locked installation remain open.


Status: INCOMPLETE, unaccepted and unpublished. The user's "Please proceed with
s35 thanks" authorized local slice work and its disposable proofs. No install,
commit, push, deployment, credential, live call or protected-fixture edit occurred.

## Verified entry and stop

Entry was clean main. HEAD, origin/main and live remote main were all
`cd532d6aba76486f1d48cb3798d8a95b5ace2fe6`. The authorized branch
`shiftwork/slice-35` was created from that commit. HEAD remains there; changes
are unstaged, with the new plan and browser runner untracked.

The runtime session log reported `last_token_usage.input_tokens: 195398`, beyond
AGENTS.md's 175k stop limit. This was checked too late after broad document
reads. New implementation stopped; only manifest consistency, focused checks
and this checkpoint/handoff were completed afterward. No budget extension exists.

Session log:
`/Users/jayd0/.codex/sessions/2026/10/20/rollout-2026-10-20T20-09-59-01a15937-eb78-7542-a37a-85ce656a9530.jsonl`.

## Implemented locally

- Northline projection admits booking, escalation, counter followup and rollout
  records through purpose, synthetic and derivation-state guards. Existing exact
  output/check/ordinal joins and selection/shift checks still apply.
- Handover copies only the declared runbook version when its two cause refs,
  synthetic flag, absent derivation and payload version agree. It remains an
  administrative declaration with no arrival motion.
- Northline diagnostic and selection transitions target `bench`; consequences
  target `rollout`. No command path changed.
- The host admits Northline and labels it as its workshop.
- The room has an original counter, separated map lanes/boundary, integration
  bench, bicycle on a stand, independent fixture, slot rail and runbook shelf.
- The existing instanced builder now supports authored wheel geometry and
  rotations. Wheel geometry is owned by the existing disposal set. Five marker
  meshes represent recorded booking, approval, declaration, escalation and
  followup, with an aggregate count rather than invented appointments.
- Northline CSS exposes the real canvas, normal station list, graphics controls,
  identity and expand control. Asset hashes match the edited source.
- The browser harness narrowly admits S35 receipt roots/modes and observes real
  wheel geometry and marker visibility without production test hooks.

These changes have focused evidence only. Labels, motion, exact joins, resource
cleanup and access obligations have not been fully proved for S35.

## Fresh evidence

Receipt root: `/tmp/shiftwork-s35-20261020-1`.

- `baseline-node.log`: 118 Node checks passed before production changes.
- `baseline-browser.log`: complete existing Northline UI journey passed on a
  fresh trusted-local preview before production changes. Its database is now
  consumed and closed. It is not a starter fixture.
- `projection-red.log`: named failures exposed missing Northline admission,
  declaration identity, station mappings, workshop geometry and host admission.
  Positive mapping/history assertions already passed and need isolated faults.
- `projection-green.log` and `stop-node.log`: 144 Node checks passed after edits.
- `room-red.log`: browser assertion `Northline graphics did not mount` failed
  before Northline canvas CSS and scene implementation.
- `room-green/workshop.json`: real WebGL2 workshop, two rendered TorusGeometry
  wheels and five independently selected marker types passed. Zero commands and
  zero JS exceptions in this inspection. This injects synthetic SceneViews,
  not production booking events or complete guard proof.
- `room-green/workshop.png`: visually inspected at desktop size. The bicycle,
  map lanes, separate bench/fixture, slot rail and shelf are visible. This is
  one screenshot after synthetic marker tests, not full art/access acceptance.
- `stop-assets.log`: nine asset checks passed, two existing deprecation warnings.
- `git diff --check`: passed at stop.

Preview was `http://127.0.0.1:8360`. Its owned process was stopped for handoff.
No 8898 execution. S27/S28 archives, backend, protected fixtures, lockfiles and CI
were not edited. No full non-packaging regression ran in this session; S34's
known `port_dead` failure remains historical, not newly rerun evidence.

## Open work and suspected edges

All remaining S35 obligations remain unchecked in the implementation plan:
independent source/served mutations and exact restoration; full evidence labels;
permission/declaration wording; Acceptance/Rollout/Handover actual-content reach
at exact widths/zoom with native keys/taps; dirty continuity; nine graphics
faults; partial initialization/retry/double disposal; 30 actual-room switches;
both complete budget measurements; native Safari; later-alternative and history
journey; all three post-change product journeys; full offline regressions;
fresh zip, extracted journeys/rooms, external blocking, closure, size and digest;
fresh review and post-slice cleanup scan.

The clean locked installation remains required and separately unauthorized.
No new archive has been produced. No S35 acceptance claim is made.

Suspected, untested edge: the new operational branch uses
`link?.run_id === run?.id && run.purpose !== 'OPERATION'`. Both optional IDs
can be undefined when the run and derivation are absent. That case may throw.
Its synthetic guard currently uses truthiness, while renderer admission uses
`=== true`. Both deserve boundary tests before any completion claim. This is
a source-review suspicion, not a reproduced failure.

Shared browser helpers still have Bellwether/GTM-only station assumptions.
`runLifecycle` still expects Northline fallback; `workplace_perf.mjs` admits only
bookshop/GTM. Exact-viewports currently checks panel focus, not selected Northline
content. The older Northline reach runner still checks panel top and reduced
motion. Existing assertions must remain meaningful when extending them.

Untracked files cannot safely be restored through Git. Mutations belong in
served source or disposable copies. The baseline preview's
`baseline-input/comparison.db` is an open comparison checkpoint, while
`baseline-input/closed.db` and `baseline.db` contain closed pilot state. Copy a
checkpoint into a fresh owned root before mutating it. Current helper signatures
must be inspected before use.

## Continuation full-regression result

`regressions.log` records `.venv/bin/python -m pytest --ignore=tests/packaging -q`:
1454 passed, one skipped, two warnings and the retained failure
`tests/executor/test_conformance.py::test_conformance_suite_recorded_local[port_dead]`.
The local adapter returned REQUEST_TIMEOUT rather than the recorded
SERVICE_UNREACHABLE. This reproduces the documented known-red case; the suite is
not all green. Runtime was 157.58 seconds. No repair or repeat was attempted.

The last measured input usage during final bookkeeping was 183774 tokens.
New implementation had stopped after the 170444 phase-boundary reading; the
remaining work only collected running results, stopped previews and updated
consistent records. No context-budget extension or S35 acceptance is inferred.

## Second continuation performance result

`performance/performance.json` passes the full recorded standard and compact
recipes. Each tier has five distinct cold starts, a five-second warm-up, three
30-second synthetic navigation samples and ten seconds with zero idle frames.
Standard cold starts are 2837.3 to 2895.4 ms; compact cold starts are 2833.5 to
2901 ms. Standard sample medians are 16.7 ms, with worst p95 18.2 ms; compact
medians are 33.3 ms, with worst p95 34.9 ms. Standard maxima are 2604 triangles
and 25 calls; compact maxima are 1344 triangles and 16 calls. Estimated owned
allocations are 21,840,384 and 1,907,776 bytes. These are estimates, not VRAM.
All individual samples pass; no miss was averaged away. These are .85 headless
navigation-stress measurements on the recorded battery-powered M4 Pro, not
physical-device certification or a general performance guarantee.

`compact-cap.log` records 33 drawings in the 1.1-second cap control.
`final-runtime-controls/latency/latency.json` records synchronous DOM startup of
3.0 and 0.9 ms, and station-paint upper-bound p95 of 34.2 and 34.4 ms at 1280
and 390px. `final-runtime-controls.log` reruns all four retry modes with the
complete resource instrumentation and passes them. Final archive client bytes
match the checkout; `final-scope.json` records the equality and unchanged inherited
scene, room, host, view, index and source-test bytes. No deletion occurred.

The user has now answered the foreground request. Native Safari then showed the
real workshop. A disposable observed preview on 8372 is recording native viewport,
WebGL2, focus, selected-content geometry and dirty-editor state. Native zoom and
keyboard proof are still in progress. Earlier hidden-page attempts remain failed
observations, not passes. Source archive bytes are unchanged.
