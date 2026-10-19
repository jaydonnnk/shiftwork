# S30 local implementation and evidence checkpoint

Updated: 2026-10-20 Asia/Singapore.

**Status: S30 ACCEPTED on local evidence, 2026-10-20; commits and main
publication are recorded below after the push.** The user answered "Start S30
(Recommended)" on 2026-10-20, which authorized local implementation, tests and
disposable evidence on `shiftwork/slice-30`. The user then accepted S30 with
"Yep i accept and do the cleanup and hen commit the working tree and push to
main if u havent already", authorizing the two cleanup findings, focused commits
and publication to main. The earlier go-ahead did not cover deployment,
credentials, provider calls, protected fixtures, browser installation, outreach
or any change to the narrowed evidence scope. S31 has not started and still
requires its own go-ahead.

The branch was created from the S29 publication tip `272321c` and confirmed with
`git branch --show-current`. The commit and publication range is recorded after
the push.

## Scope and delivered contract

The S30 contract is in [04-slices.md](04-slices.md), "S30: form a prediction and
inspect a diagnostic". This round delivers its bounded scope:

- the failed customer request stays visible in the Investigate station;
- the learner records a cause, falsifier and public test with the existing
  investigation handler and the existing saved version;
- the diagnosis desk and paired test bench exist in the room;
- reported RESERVED/RUNNING/COMPLETE/FAILED states and missing evidence are the
  only diagnostic states rendered;
- a diagnostic can never qualify selection or derive a ledger event;
- every owned initial and polled diagnostic assignment is published before the
  final refresh;
- expanded work uses `host.setExpanded(expanded)` around the same workbench node
  and preserves editor value, focus and caret;
- the 160ms test-bench emphasis is driven by real polling continuity and cancels
  on reduced motion, suspension and disposal.

No hint quality, provider call, qualifying comparison, automatic hypothesis,
automatic choice, new route, new environment name, bundler, asset loader or
second editor was added. S31 and later did not start.

## Production changes (uncommitted)

- `shiftwork/client/workplace-view.js`: purpose guards for diagnostic,
  comparison and later kinds; `missing_evidence` projected from
  `trial.missing_evidence.length`; continuous `test-update` diffing keyed on
  experiment, trial, run and missing evidence; duplicate and removed diagnostics
  stay quiet; history or inspection changes stay quiet; a diagnostic cannot be
  the selection comparison and diagnostic trial runs cannot derive ledger
  events.
- `shiftwork/client/workplace-host.js`: the ready message names intake, console,
  diagnosis and assessment; the same message survives a consistency conflict.
- `shiftwork/client/workplace-rooms.js`: diagnosis desk at `(0, -2.5)` with two
  worksheet parts and pure station references; paired test bench at `(0.7, 3)`
  with a public indicator panel; anchors `investigate [0, 1.05, -2.5]` and
  `compare [0.7, 1.1, 3]`; no commands.
- `shiftwork/client/workplace-scene.js`: 160ms emissive emphasis on a real
  `test-update` transition; indicator colours for RESERVED, RUNNING, COMPLETE and
  FAILED; pulse settles on suspend, reduced motion and dispose; no catch-up
  frame.
- `shiftwork/client/index.html`: failed-request section with its synthetic label,
  the prediction heading, the 44px expand-work control and the diagnostic test
  tag.
- `shiftwork/client/styles.css`: 44px expand target, diagnostic state colours and
  the expanded one-column layout capped at 1120 CSS pixels.
- `shiftwork/client/app.js`: failed-request rendering with run, request ordinal,
  executed version, reported verdicts and a no-validated-answer fallback;
  reported-state gating for trial state and missing evidence; diagnostic
  generation/intent context/inspection owner and publication guard; history
  inspection preserved across refresh instead of falling back to
  `board.latest_run`; expanded work with same-node focus and caret restoration.

`shiftwork/client/workplace-assets.json` was refreshed only for the seven changed
client sources. All ten manifest rows match their current files.

## Test changes (uncommitted)

- `tests/client/workplace_view.test.mjs`: 61 projection and host checks, including
  diagnostic purpose, non-qualification, ledger isolation, continuous updates,
  duplicate/removal/history quietness, expanded reference advancement and loading
  baseline retention.
- `tests/client/workplace_faults.mjs`: the scratch-root assertion now accepts
  `/tmp/shiftwork-s29-*` and `/tmp/shiftwork-s30-*`; 11 new source fault rows
  (nine view, two host) bring the batch to 53.
- `tests/client/workplace_s30.mjs` (new, 313 lines): `journey`, `ownership`,
  `expanded` and `motion` modes with named fault injections;
- `tests/client/workplace_browser.mjs`: extended with the S30 page-cache,
  lifecycle and exact-viewport assertions.
- `tests/client/browser.mjs`: the existing bookshop journey now expects the
  additive `failed-request` synthetic region in the Investigate label list. This
  is the only change to the existing journey and it keeps its other assertions.

## Verified evidence, 2026-10-20

All receipts are disposable local artifacts under `/tmp/shiftwork-s30-*`. The
retained `http://127.0.0.1:8898/#customers` preview was never used, replaced or
restarted.

### Fast baseline

- `node --check` on every modified JavaScript and module file: clean.
- `node --test tests/client/workplace_view.test.mjs`: 61 pass, 0 fail, 0 skipped.
- `node tests/client/workplace_faults.mjs /tmp/shiftwork-s30-PtdHf2/faults`:
  53 of 53 PASS, production unchanged. Receipt:
  `/tmp/shiftwork-s30-PtdHf2/faults/faults.json`.

### S30 browser controls

The fresh-preview driver ran 21 controls, one fresh database and port each. All
21 result receipts pass:

- clean: journey, ownership-generation, ownership-intent, ownership-history,
  ownership-context, ownership-inspection, expanded, motion, page-cache,
  lifecycle, exact-viewports.
- expected failures: journey-omit-initial, journey-omit-polled,
  ownership-generation-mutation, ownership-intent-mutation,
  ownership-context-mutation, ownership-inspection-mutation, expanded-omit-suspend,
  expanded-escape-mutation, expanded-pointer-focus-mutation,
  motion-omit-settle-mutation.

The named mutation failures are:

- `The initial RESERVED state was not observed`;
- `The diagnostic did not report COMPLETE or FAILED`;
- `generation ownership published a stale diagnostic update`;
- `intent ownership published a stale diagnostic update`;
- `context ownership published a stale diagnostic update`;
- `inspection ownership published a stale diagnostic update`;
- `Expanded work kept drawing`;
- `Escape did not restore the workbench`;
- the same-node value/focus/caret comparison with focus false;
- `An active motion preference change did not cancel the emphasis`.

Provenance note: the original `controls-summary.json` was overwritten by a later
filtered rerun and now holds one row. Every per-control `result.json` survives.
`controls-summary-rebuilt.json` was regenerated from those 21 receipts and
records that provenance; it is an aggregate, not new evidence.

### Clean journey

Receipt: `/tmp/shiftwork-s30-PtdHf2/controls/journey-clean/out/journey.json`.

- Accepts were RESERVED with 1 missing evidence, then COMPLETE with the reported
  test tag.
- Selection, recorded events, ledger and totals were identical before and after:
  three events and ledger 3, all INCIDENT_OPENED.
- The after capture omits the assist text field; assist was checked separately as
  `Diagnostic help is available.`.
- The only submitted commands were
  `/api/shifts/bookshop-shift-01/investigations`,
  `/api/shifts/bookshop-shift-01/artifact` and
  `/api/shifts/bookshop-shift-01/experiments`.
- No uncaught exception and no external request.

### Ownership

Clean receipt: `/tmp/shiftwork-s30-PtdHf2/controls/ownership-*/out/ownership.json`.

Generation, intent, history, context and inspection clean modes pass. Generation,
intent, context and inspection mutations each publish a stale diagnostic and fail
with the exact message above. The history scenario is covered by the inspection
guard mutation; there is no separate history mutation and none is claimed.

### Expanded work

Receipt: `/tmp/shiftwork-s30-PtdHf2/controls/expanded-clean/out/expanded.json`.

- Width 1120 CSS pixels, the same DOM editor node, dirty bytes, focus and caret
  5..23 backward preserved.
- Zero frames while expanded, pulse false, newest applied state retained.
- Resize to 640x900 keeps continuity; Escape restores; one settle frame after
  restore.
- Context loss retains the editor; explicit retry rebuilds the room.
- Escape inside the editor stays native.

### Motion

Receipt: `/tmp/shiftwork-s30-PtdHf2/controls/motion-clean/out/motion.json`.

The accepted test update starts a pulse at 0.8 emissive. Emulated
`prefers-reduced-motion: reduce` cancels it to 0 with 0 further frames. The
mutation fails with the named message above.

### Page cache and lifecycle

Receipt: `/tmp/shiftwork-s30-PtdHf2/controls/page-cache-clean/out/page-cache.json`.

The same document and editor node survive a persisted page cache return with
dirty value, focus and caret 5..19 backward, one canvas and the old context lost.
The lifecycle receipt records eight checks: loading continuity and uncovered
geometry, error reset, expanded drawing stop, expanded restore settle, synthetic
hidden stop, observed offscreen stop, thirty switches releasing old resources and
idempotent full teardown.

### Exact viewports

Receipt: `/tmp/shiftwork-s30-PtdHf2/controls/exact-viewports-clean/out/exact-viewports.json`.

1280x720, 640x900 and 390x844 at 100% and 200% zoom have exact inner sizes, DPR,
pinch and scroll values with no body zoom.

### Performance

Receipt: `/tmp/shiftwork-s30-PtdHf2/perf-run-1792426905/out/performance.json`.

Host: macOS 26.5.1 build 25F80, arm64, AC power. Browser: Chrome 155.0.8059.84
headless, ANGLE Metal renderer on Apple M4 Pro. This is synthetic local
measurement, not physical-device, power or native performance proof.

- 1280x720 at DPR 1: five cold starts 2849.9 to 2905.9ms against a 3000ms
  budget; three 30-second samples had median 16.7ms, p95 17.5 to 17.9ms,
  2112 triangles and 18 draw calls; idle frames 0; estimated allocation
  21,840,384 bytes against 48MiB. No budget misses.
- 390x844 at DPR 1: five cold starts 2824.3 to 2976.0ms against a 4000ms
  budget; three 30-second samples had median 33.3ms, p95 33.8 to 34.4ms,
  1068 triangles and 10 draw calls; idle frames 0; estimated allocation
  1,907,776 bytes against 24MiB. No budget misses.

Allocation is an estimate. The richer scene measures 2112 triangles and 18 draw
calls at desktop, up from S29's 1788 and 17. Lifecycle and exact-viewport checks
were rerun on fresh previews in this round with exit 0.

### Assets and journeys

- Every manifest digest matches. `pytest tests/packaging/test_client_asset_closure.py -q`:
  9 passed, 2 existing warnings, 0.24s.
- Three existing board journeys against fresh disposable state:
  `bookshop`, `gtm` and `northline` each exited 0. Receipt:
  `/tmp/shiftwork-s30-PtdHf2/journeys2-1792427286/results.json`.
- The first journey attempt failed only on the additive `failed-request` label
  list in `browser.mjs`; the test expectation was corrected and the rerun passed.

### Full non-packaging suite

Command: `.venv/bin/python -m pytest tests --ignore=tests/packaging -q`.
Result: **1454 passed, 1 failed, 1 skipped, 2 warnings in 179.10s**. The one
failure is the known
`tests/executor/test_conformance.py::test_conformance_suite_recorded_local[port_dead]`
mismatch: REQUEST_TIMEOUT where SERVICE_UNREACHABLE is expected. This matches
the S29 baseline exactly and is retained as evidence, not suppressed. Log:
`/tmp/shiftwork-s30-PtdHf2/full-suite.log`.

## Acceptance and cleanup, 2026-10-20

The user accepted S30 with "Yep i accept and do the cleanup and hen commit the
working tree and push to main if u havent already". The two architect-reviewer
findings were applied:

- the stale test name `S29_focus_is_the_only_transition_and_history_is_quiet`
  became `station_focus_is_the_only_transition_without_a_diagnostic_update` with
  no assertion change;
- the [plan brief](../../../SHIFTWORK_PLAN.md) top notice now records S30
  acceptance instead of saying S30 needs a go-ahead. Older notices stay
  historical.

The acceptance and publication notices in the root status and the workplace
status were updated in the same round. The test rename was re-verified with the
61-check unit file. No production byte changed after the performance, asset,
journey or full-suite runs, so those receipts remain valid for the committed
tree.

## Limits and unclaimed targets

- Evidence stays Mac-only headless Chromium 155 on macOS 26.5.1 plus the
  previously recorded native Safari 26.5 observations. S30 did not rerun native
  Safari, Windows, Edge, Firefox, previous-stable Safari or physical devices.
- Audible VoiceOver/NVDA, physical performance and power, minimum Intel hardware
  and comprehension sessions remain unmeasured and unclaimed.
- The performance receipt is a synthetic local measurement with an estimated
  allocation. It is not native performance certification.
- These controls prove the local UI and publication contract only. They do not
  measure hint quality, learning gain, model quality, employer value or
  commercial outcomes.
- The diagnostic is non-qualifying by construction. No comparison, selection,
  operation or inheritance behaviour is claimed.
- The full packaging run, including a fresh locked install, was not authorized
  or run. Only the nine non-installing asset checks ran.
- No commit, push, merge, deployment or publication followed.

## Stop boundary

S30 is accepted on the evidence above. S31 requires its own go-ahead and has not
started. Focused commits and the main publication are recorded after the push;
no deployment, credential, provider call or protected fixture follows.
