# S31 local implementation and evidence checkpoint

Updated: 2026-10-20 Asia/Singapore.

**Status: S31 ACCEPTED on local evidence, 2026-10-20. Publication in progress.**
The user answered "Start S31" on 2026-10-20, authorizing local implementation,
tests and disposable evidence on `shiftwork/slice-31` under `/tmp/shiftwork-s31-*`.
That authorization did not cover commits, pushes, merges, deployment,
credentials, provider calls, protected fixtures, browser installation, outreach
or any scope change. The user then accepted S31 with "Yep accepted" and
authorized the working-tree commits, the two approved cleanup deletions and the
push to main. The branch was created from the main tip `f4e794e`. The
publication commit range is recorded at the end of this checkpoint after the
fast-forward.

## Scope and delivered contract

The S31 contract is in [04-slices.md](04-slices.md), "S31: compare repairs and
choose the exact operating version". This round delivers its bounded scope:

- two equal A/B stands show the exact frozen candidate versions and content
  hashes, the shared condition and denominators, each candidate's blockers and
  the missing-slot count;
- neither candidate is preselected and no winner is derived; eligibility is
  public outcome data, not an aggregate score;
- a completed comparison does not change the operating selection or plate;
- an explicit eligible A or B choice with a rationale is submitted through the
  existing server guard and accepted refresh;
- the operating plate, the selection note and the board summary bind the exact
  selected version, selected content hash and retained alternative;
- both the initial and every polled `runComparison()` assignment are published,
  and a stale assignment is suppressed when ownership changes;
- saving and freezing through the accepted refresh leave the prior selection
  unchanged;
- comparison updates and selection updates produce separate 160ms and 180ms
  scene acknowledgements, cancelled by reduced motion, suspension and disposal;
- side-by-side comparison stays readable at 1280px and stacks at 640px and
  390px.

No new eligibility calculation, action handler, automatic winner, operation,
consequence or inheritance was added. S32 has not started.

## Production changes (uncommitted)

- `shiftwork/client/workplace-rooms.js`: public anchors `candidateA`,
  `candidateB` and `plate` in the bookshop room. No commands.
- `shiftwork/client/workplace-scene.js`: two candidate stand markers and one
  operating plate; candidate colours only from public eligibility, plate colour
  only from the operating selection; 160ms comparison and 180ms selection
  emissive pulses; one frame loop for any active pulse; settlement on suspend,
  reduced motion and dispose.
- `shiftwork/client/workplace-view.js`: `publicMetrics` preserves unknown costs
  as null; candidate-label uniqueness and trial-to-candidate version binding
  guards; missing-slot and incomparable derivation; condition label and shared
  denominators; selection membership, content-hash and retained-alternative
  guards against the comparison; distinct continuous `comparison-update` and
  `selection-update` transitions that stay quiet on duplicates and removals.
- `shiftwork/client/app.js`: comparison owner snapshot and publication guard for
  slug, loaded shift, experiment shift, generation, intent, inspection and
  loading; every initial and polled assignment flows through the guard; the
  comparison panel shows missing slots, a denial for invalidated or incomparable
  evidence, explicit blocking reasons and exact candidate identities; the
  selection note names the recorded choice, selected version, selected hash and
  retained alternative.
- `shiftwork/client/workplace-assets.json`: refreshed only the four changed
  source digests. All ten manifest rows match their current files.

## Test changes (uncommitted)

- `tests/client/workplace_view.test.mjs`: 78 checks, adding 17 comparison and
  selection projection checks for public metrics, unknown costs, missing slots,
  blockers, incomparability, no default winner, candidate/trial binding,
  selection identity guards, continuous updates, duplicates, removals,
  first-load quietness and diagnostic non-qualification.
- `tests/client/workplace_faults.mjs`: the scratch-root assertion accepts
  `/tmp/shiftwork-s31-*`; 12 new source fault rows bring the batch to 65.
- `tests/client/workplace_s31.mjs` (new): `journey` with A/B complete, blocked,
  incomparable and missing modes; `ownership` with nine hold/direct scenarios;
  `selection`; and `failure` recovery. It asserts exact identities, pulses,
  layouts, command counts and replayed-choice absence.
- `tests/client/workplace_browser.mjs`: S31 instrumentation and fault
  injections for initial/polled publication omission, eight ownership guards,
  selection failure and comparison/selection scene state. The CDP and script
  waits were extended to tolerate the host's external load.
- `tests/client/browser.mjs`: the existing bookshop comparison demo now checks
  shared denominators, missing slots, candidate versions and hashes, and the
  selection acknowledgement's recorded choice and exact identities.

## Verified evidence, 2026-10-20

All receipts are disposable local artifacts under `/tmp/shiftwork-s31-*`. The
retained `http://127.0.0.1:8898/#customers` preview was never used, replaced or
restarted. The host was under heavy external load during the round; several
harness deadlines were extended and one control was rerun. No product byte
changed after the final asset refresh.

### Fast baseline

- `node --check` on every modified JavaScript and module file: clean.
- `node --test tests/client/workplace_view.test.mjs`: 78 pass, 0 fail, 0
  skipped.
- `node tests/client/workplace_faults.mjs /tmp/shiftwork-s31-s31a/faults`:
  65 of 65 PASS, production unchanged. Receipt:
  `/tmp/shiftwork-s31-s31a/faults/faults.json`.

The S31 fault rows each mutate one guard and fail its own named assertion:
duplicate candidate label, trial/candidate version mismatch, selection outside
the comparison, selection content-hash mismatch, wrong retained alternative,
missing-slot miscount, incomparable-as-comparable, unknown cost as a number,
duplicate comparison update, removed comparison update, duplicate selection
update and removed selection update.

### S31 browser controls

The fresh-preview driver ran 30 controls, one fresh database and port each. All
30 result receipts are as expected; the rebuilt aggregate is
`/tmp/shiftwork-s31-s31a/controls-summary-rebuilt.json`.

- Clean journeys: `journey-a-clean`, `journey-b-clean`, `blocked-clean`,
  `incomparable-clean`, `missing-clean`, `selection-clean`,
  `failure-recovery-clean`.
- Expected failures with their own messages: `journey-omit-initial`
  ("The initial comparison assignment was not published") and
  `journey-omit-polled` ("The comparison published no polled assignment").
- Ownership clean and mutation pairs: generation, intent, history, context,
  shift, experiment, inspection and loading. Every clean hold suppresses the
  stale assignment and every mutation fails with
  "`<mode>` ownership published a stale comparison update".
- Regression controls on the richer scene: `expanded-clean`, `motion-clean`,
  `page-cache-clean`, `lifecycle-clean`, `exact-viewports-clean`.

### Clean journeys and exact identities

Receipts: `/tmp/shiftwork-s31-s31a/controls/journey-*/out/journey.json`.

- Both A and B runs used the same six-slot comparison
  `experiment-bookshop-shift-01-c1`. The initial assignment was PLANNED; the
  A journey observed PLANNED, RUNNING, FINALIZED with zero missing slots.
- Candidate A is `ver-0002` with content hash
  `01df104ffd8fc974ae90e733e14ffb7e7af13260452a701f7567cd86b2342c82`.
  Candidate B is `ver-0003` with content hash
  `21b9733dbffab5d1845edc3f0b4e5c8cd9b26aafca3edb57778bdd51e3000105`.
- Both stands used the public eligible colour `8fbf9f`; neither was preselected.
  The prior operating selection and plate were unchanged before the choice.
- The valid comparisons produced comparison pulses at 160ms. The chosen version
  produced exactly one 180ms plate pulse.
- The A journey selected `ver-0002` and retained `ver-0003`; the B journey
  selected `ver-0003` and retained `ver-0002`. The selected content hash, the
  comparison id and the retained alternative matched the public records in the
  note, the board summary and the scene.
- The choice submitted exactly one `/api/shifts/bookshop-shift-01/selections`
  command and did not move the latest run, the ledger or incidents.
- After each choice, a full workbench page reload reconstructed the scene with
  the same operating selection id, version, content hash and selected plate.
  Closing and reopening the workbench alone did not change the recorded choice.

### Blocked, missing and incomparable evidence

Receipts: `/tmp/shiftwork-s31-s31a/controls/{blocked,incomparable,missing}-clean/out/journey.json`.

- The blocked and incomparable previews reached INVALIDATED with a
  NOT_COMPARABLE outcome, both cards marked ineligible with the public
  `NOT_COMPARABLE` blocker, and both stands coloured `d98a7a`.
- The missing preview reached FAILED with an INCOMPLETE outcome, one missing
  slot, candidate A carrying `mandatory_public_rule` plus INCOMPLETE, and both
  choice controls disabled.
- The denial text, blocker list and missing-slot count were rendered from the
  public outcome; unknown provisioning latency and cost stayed `unknown`.
- No blocked, missing or incomparable comparison changed the prior operating
  selection or plate.

### Selection failure recovery

Receipt: `/tmp/shiftwork-s31-s31a/controls/failure-recovery-clean/out/failure.json`.

The first selection POST was fulfilled with a 409. The workbench surfaced the
error, kept the prior operating choice (`sel-0001`), recorded no selection and
released the control. The explicit retry recorded exactly one new selection
(`sel-0002`, `ver-0002`) from two POSTs total. A later poll did not replay it.

### Ownership

Receipts: `/tmp/shiftwork-s31-s31a/controls/ownership-*/out/ownership.json`.

All eight clean hold modes reached the hold, observed `allowed: false` and
published no comparison update. All eight mutations removed their named clause
and failed at that mode's assertion. The generation, intent and history modes
hold the real initial POST; context, shift, experiment, inspection and loading
invoke the guard directly after a completed comparison.

### Layout and emphasis

The S31 journey asserts 1280px side-by-side readability, actual stacked layouts
at 640x900 and 390x844 with no horizontal overflow, two outcome cards and a
visible comparison panel. It asserts the 160ms comparison duration and the
180ms selection duration from recorded scene state. The S30 expanded, motion,
page-cache and lifecycle controls all pass unchanged on the richer scene.

### Assets

- Changed digests: `app.js`, `workplace-view.js`, `workplace-rooms.js` and
  `workplace-scene.js`. The manifest has 10 rows and no mismatch.
- `pytest tests/packaging/test_client_asset_closure.py -q`: 9 passed, 2
  existing warnings, 2.09s.

The 16-check packaging suite, including a fresh locked install, was not
authorized and was not run.

### Board journeys

- The three existing journeys ran against fresh disposable state:
  `bookshop`, `gtm` and `northline` each exited 0. Receipt:
  `/tmp/shiftwork-s31-s31a/journeys-2026-10-20/results.json`.
- A separate fresh bookshop run with `--selection-demo` passed, exercising the
  new comparison-summary and selection-acknowledgement assertions in
  `browser.mjs`. Receipt:
  `/tmp/shiftwork-s31-s31a/bookshop-variants-2026-10-20/results.json`.
- The first bookshop attempt used the S31 assist-enabled preview, so its assist
  request correctly succeeded instead of producing the journey's expected 409.
  The failed receipt is retained; the journey rerun used the standard no-assist
  preview.
- A `--blocked-demo` variant also passed, but without `--compare-demo` it ran
  the plain journey and is not claimed as a blocked-denial test. The S31
  blocked, incomparable and missing controls carry that evidence.

### Performance

Receipt: `/tmp/shiftwork-s31-s31a/perf-run-2026-10-20b/out/performance.json`.

Host: macOS 26.5.1 build 25F80, arm64, AC power. Browser: Chrome 155.0.8059.84
headless, ANGLE Metal renderer on Apple M4 Pro. This is synthetic local
measurement, not physical-device, power or native performance proof.

- 1280x720 at DPR 1: five cold starts 2876.9 to 2968.6ms against the 3000ms
  budget; three 30-second samples had median 16.7ms, p95 17.5 to 18.3ms,
  2148 triangles and 21 draw calls; idle frames 0; estimated allocation
  21,840,384 bytes against 48MiB.
- 390x844 at DPR 1: five cold starts 2829.6 to 2913.0ms against the 4000ms
  budget; three 30-second samples had median 33.3ms, p95 33.6 to 35.0ms,
  1104 triangles and 13 draw calls; idle frames 0; estimated allocation
  1,907,776 bytes against 24MiB.
- No budget misses. The earlier run
  `/tmp/shiftwork-s31-s31a/perf-run-2026-10-20/` is retained: one desktop cold
  start measured 3087.9ms under external load while the other four measured
  2873.0 to 2957.5ms. The clean rerun above is the accepted measurement, not a
  reuse of S30 numbers.

### Full non-packaging suite

Command: `.venv/bin/python -m pytest tests --ignore=tests/packaging -q`.
Result: **1454 passed, 1 failed, 1 skipped, 2 warnings in 196.97s**. The one
failure is the known
`tests/executor/test_conformance.py::test_conformance_suite_recorded_local[port_dead]`
mismatch: REQUEST_TIMEOUT where SERVICE_UNREACHABLE is expected. This matches
the S29 and S30 baseline and is retained as evidence, not suppressed. Log:
`/tmp/shiftwork-s31-s31a/full-suite.log`.

## Cleanup scan, 2026-10-20

The post-slice architect-reviewer scan found no orphaned files, fixtures, routes,
handlers, production test hooks or unreferenced production helpers. It found two
record and harness items:

- Fixed: the historical S30 notices said S31 had not started. Both status files
  and the plan brief now point to the S31 notice above.
- Applied on acceptance: `__s31Latest` and `__s31Suppressed` in the S31 browser
  instrumentation were removed as the only redundant hooks. The
  `ownership-generation-clean` control still passed after removal.

## Limits and unclaimed targets

- Evidence stays Mac-only headless Chromium 155 on macOS 26.5.1. S31 did not
  rerun native Safari, Windows, Edge, Firefox, previous-stable Safari or
  physical devices.
- The host was under heavy external load for part of the round. Test harness
  deadlines were extended and one exact-viewport control was rerun after a CDP
  timeout. No product byte changed after the final asset refresh.
- The comparison shows public outcome data and exact identities; it does not
  measure diagnosis quality, hint quality, learning gain, model quality,
  employer value or commercial outcomes.
- No operation, consequence, inheritance, deployment, credential, provider
  call or protected fixture was exercised.
- The 16-check packaging suite and a fresh locked install were not authorized
  or run.

## Stop boundary

S31 is accepted on the evidence above and is being published to main. S32
requires its own go-ahead and has not started. No deployment follows.
