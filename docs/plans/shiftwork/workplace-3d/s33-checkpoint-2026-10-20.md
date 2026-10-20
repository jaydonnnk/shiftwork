# S33 local implementation and evidence checkpoint

Updated: 2026-10-20 Asia/Singapore.

**Status: S33 ACCEPTED on local evidence and published on main, 2026-10-20.**
The user answered "Start S33 now" on 2026-10-20, authorizing local
implementation, fail-capable tests and disposable evidence under
`/tmp/shiftwork-s33-*`. That authorization did not cover commits, pushes,
merges, deployment, credentials, provider calls, protected fixtures, CI, lint,
lockfile or packaging changes, gate reopenings, comprehension sessions or S34
and S35. The user then accepted S33 with "Okay yea i accept it please commit the
changes and push to main and then the copy paste prompt for slice 34, pls
reference this prompt". This authorized the working-tree commits, the
fast-forward to main and the push. S34 remains unstarted and needs its own
go-ahead.

## Scope delivered

The contract is in [04-slices.md](04-slices.md), "S33: inherit the choice and
test the retained alternative later".

- The Bellwether room now includes the owner desk, the read-only incident
  review tray and the handover shelf from visual-spec sections 5 and 6.
- The handover shelf shows the original selection, rationale, selected content
  hash, retained alternative, frozen requirement hashes, declared limits and
  unresolved incidents.
- Historical incidents open through an explicit history mode. The workbench
  shows the historical run identity and a labelled "Return to current shift"
  control. Ordinary polling does not leave history mode. Closing or opening a
  shift requires current mode.
- A later-condition experiment is bound to the original selected and retained
  versions and to its observed operation. It cannot reuse the original
  comparison identity, bind a different version, omit its observed run or call a
  trial run its observation.
- The later-condition panel states that the test does not replace the choice.
  Leaving the shift clears the previous later identities from the new shift.
- Saving a newer draft does not change the operating selection, rationale,
  retained alternative or the inherited shelf.
- No reducer, grading, endpoint, operation worker, provider path or protected
  fixture changed.

## Production changes

- `shiftwork/client/workplace-rooms.js`: owner desk, incident tray and handover
  shelf geometry; anchors for the owner, repair and next stations; handover and
  later markers.
- `shiftwork/client/workplace-scene.js`: handover and later materials, inherited
  shelf state, later marker state, and the later experiment on the A/B bench
  without changing the operating plate or consequence wall.
- `shiftwork/client/workplace-view.js`: later-experiment binding to the selected
  and retained versions and to a non-trial observed operation.
- `shiftwork/client/app.js`: explicit inspection bar and return action,
  ownership-checked incident inspection, read-only repair tray, owner
  requirements folder, handover incident list, current-only shift actions and
  stale later-identity cleanup.
- `shiftwork/client/index.html` and `shiftwork/client/styles.css`: the owner
  folder, incident tray, inspection controls, handover history, wrapping file
  tabs at 200% zoom and the new station composition.
- `shiftwork/client/workplace-assets.json`: refreshed digests for all changed
  client files.

## Test changes

- `tests/client/workplace_view.test.mjs`: 101 checks, including five later
  binding controls and the existing non-replacement controls.
- The later binding guards were each removed independently: same comparison
  identity, wrong versions, missing observed run and observed run reused as a
  trial. The common selection-absence case is already covered by the version
  binding, so it does not claim a separate guard.
- `tests/client/workplace_faults.mjs`: 93 source controls, adding the four later
  binding guards with its own clean, fault and restored phase.
- `tests/client/workplace_s33.mjs` and
  `tests/client/workplace_s33_controls.mjs`: fresh-preview complete journey and
  inherited later controls, including current/history return, polling
  continuity, newer-save non-replacement, new-shift inheritance, browser-cache
  return and graphics fallback.
- `tests/client/browser.mjs`: the inheritance journey now opens a historical
  incident, returns to current explicitly and checks the later selection fields.
- `tests/client/render_faults.mjs`: three new inheritance faults for explicit
  return, later selection binding and stale later identity.
- `tests/client/workplace_browser.mjs`: owner, repair and next composition
  checks; 30-switch GTM static-view usability; later and handover scene probes;
  new stations in the keyboard, touch, zoom and exact-viewport sweeps.

## Evidence, 2026-10-20

All receipts are disposable local artifacts under `/tmp/shiftwork-s33-*`. The
retained `http://127.0.0.1:8898` preview was not used. No live provider,
deployment, hosted mutation or protected fixture was used.

### Full offline journey

`SHIFTWORK_EXECUTOR_ADAPTER=recorded .venv/bin/python -m demos.final_pivot
--stage inheritance --preview-db /tmp/shiftwork-s33-inherit-full.db` returned
exit 0 with `PASS_OFFLINE_POLICY`, `prior_bytes_identical: true`, six COMPLETE
later slots and `operational_run_is_a_trial: false`. The selected version stayed
`ver-0003`, the retained alternative stayed `ver-0004`, the later experiment
re-tested those exact versions under `run-0008`, and a switch citing the later
comparison returned 409. This is the existing offline walkthrough, not a fresh
human learning run.

### Node and source faults

- `node --test tests/client/workplace_view.test.mjs`: 101 pass, 0 fail, 0
  skipped.
- `node tests/client/workplace_faults.mjs /tmp/shiftwork-s33-source-final`: 93
  of 93 PASS, production unchanged. Every new later guard failed its own
  assertion when removed. The source file was byte-identical after the clean
  phases restored it.

### S33 fresh-preview controls

`node tests/client/workplace_s33_controls.mjs /tmp/shiftwork-s33-controls-final3`
returned exit 0.

- Complete normal journey: `run-0009` FINALIZED, five public events, one 320ms
  trace and the selected version operated. It also captured inspection, the
  selection before operation and the consequence wall at 1280 and 390.
- Inherited world: shift 2 showed `sel-0002` and `ver-0003`; the later
  experiment was `experiment-bookshop-shift-02-later-1` with observed run
  `run-0008`; the historical incident opened `run-0001`; ordinary polling kept
  history mode; the explicit return restored current mode with zero traces.
- A newer draft saved in shift 3 did not change `sel-0002`, `ver-0003` or
  `ver-0004`.
- The new shift showed the inherited choice and cleared the prior later
  experiment identity and observed run. The browser-cache return stayed quiet.
- The screenshots include the handover shelf, the visible later experiment, the
  owner requirements folder, the read-only incident tray, historical inspection
  and the inherited new shift at 1280 and 390.

### Bellwether journey and rendered faults

- The final render-fault round ran the inheritance baseline and three mutations
  against fresh inherited previews: 4 of 4 as expected. The baseline exited 0.
  Each fault failed at its named assertion: explicit return timeout, wrong later
  selection, and stale later identity after the new shift. Receipt
  `/tmp/shiftwork-s33-render-faults-final`.
- The blocked comparison baseline passed on its own fresh preview. Receipt
  `/tmp/shiftwork-s33-blocked`.
- The earlier direct inheritance browser run also exited 0 with
  `historicalRun: run-0001`,
  `historicalPollingStayedHistorical: true`, later observed run `run-0008` and
  the exact 409 refusal.

### Composition, lifecycle and access

- The final `runBrowser` passed at 1280, 640 and 390 with actual WebGL2. Native
  canvas picks opened Requirements, Repair review and Next shift; the owner
  folder had six requirement rows, the tray had no editable controls and the
  handover shelf had both inherited identity and incident history.
- The final `runLifecycle` passed all eight checks, including 30 board switches,
  GTM static-view usability and old Bellwether resource release. Warm resources
  finished at one context, one geometry and eleven materials; double disposal
  released them.
- The final exact viewport control passed 640x900 and 390x844 at 100% and 200%
  zoom, with scroll width equal to inner width. The owner panel exposed and fixed
  a real file-tab overflow at 195 CSS pixels. Receipts
  `/tmp/shiftwork-s33-workplace-final`.

### Performance

`node tests/client/workplace_perf.mjs` on the final room returned no budget
misses. Host macOS 26.5.1 build 25F80, arm64, AC power, headless Chrome 155,
ANGLE Metal on Apple M4 Pro. This is a synthetic local measurement, not physical
device or native performance proof.

- 1280x720: cold starts 2834.2 to 2885.8ms against 3000ms; median 16.7ms, p95
  17.3 to 17.6ms, 2712 triangles, 24 draw calls, idle frames 0.
- 390x844: cold starts 2812.8 to 2871.1ms against 4000ms; median 33.3ms, p95
  33.9 to 34.3ms, 1404 triangles, 16 draw calls, idle frames 0.

### Assets and full suite

- `pytest tests/packaging/test_client_asset_closure.py -q`: 9 passed, 2
  warnings; all ten manifest rows match.
- Full non-packaging suite:
  `.venv/bin/python -m pytest tests --ignore=tests/packaging -q` returned
  **1454 passed, 1 failed, 1 skipped, 2 warnings in 190.41s**. The failure is the
  known `test_conformance_suite_recorded_local[port_dead]` REQUEST_TIMEOUT
  mismatch. It matches the S30 to S32 baseline and was not changed.
- `node --test tests/client/evidence.test.mjs`: 1 pass.

## Visual review: seven Bellwether beats

| Beat | S33 review |
|---|---|
| Inspect failure | The initial board and the historical customer-evidence screenshot show the exact request, executed version, failed check, incident source and the explicit return control. |
| Cause and falsifier | The diagnosis and test journey passed with RESERVED then COMPLETE and the failed request stayed visible. This used the accepted S30 rendering; S33 did not add prose to the scene. |
| Test | The diagnostic test state is shown only on the test bench; the scene's later marker does not alter the operating plate or wall. |
| Compare repairs | The full journey ran the paired comparison and a blocked comparison baseline remained green. |
| Select exact version | The full journey recorded `sel-0002` and displayed `ver-0003`; the selection before operation screenshot shows the operating identity without an operation. |
| Operate | `run-0009` produced one linked synthetic event, one 320ms trace and a FINALIZED wall. |
| Inherit and test later | Shift 2 preserved the exact selection and rationale, opened a real historical incident, returned to current explicitly, kept `run-0008` as the observed operation and kept the later test on the bench without changing selection or history. |

## Limits

- The later world uses the existing staged dependency outage and trusted local
  fixtures. It does not measure model quality, real revenue, customer trust or
  learning.
- The browser evidence is headless Chrome only. No physical device, named screen
  reader, Windows, Edge, Firefox, previous-stable Safari or comprehension session
  was tested. Audible assistive output remains unclaimed.
- The complete offline walkthrough is a scripted operator journey. The browser
  controls cover the UI stages separately; they do not form a single live
  provider chain.
- The old S30/S31/S32 phase receipts remain the accepted visual evidence for
  their own beats. This round reran the shared normal journey, the blocked
  comparison baseline and the new S33 states, but did not regenerate every
  historical screenshot.
- A `port_dead` socket timing failure remains carried and is not fixed here.

## Acceptance and publication, 2026-10-20

The user accepted S33 with "Okay yea i accept it please commit the changes and
push to main and then the copy paste prompt for slice 34, pls reference this
prompt". The work is committed on `shiftwork/slice-33` in three focused commits,
fast-forwarded to main and pushed as `6500175..259ace9`. This publication note
is the following docs commit on main.

**Stop boundary.** S33 is accepted. S34 remains unstarted and requires its own
go-ahead. No deployment follows.
