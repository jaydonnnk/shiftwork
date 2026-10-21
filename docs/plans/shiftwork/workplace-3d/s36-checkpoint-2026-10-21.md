# S36 local implementation checkpoint, 2026-10-21

**Accepted by the user, 2026-10-21.** Asked "Is S36 accepted, or what should change?", the user answered "U make the call. Then publish the branch and merge to main and then start s37".
That answer authorized publishing `shiftwork/slice-36`, merging it to main and starting S37.

S36 (full-screen room with inspector, status bar and shift log) is implemented on `shiftwork/slice-36` from main `d43dad1`.
Nothing is staged, committed or pushed.
No install, download, deployment, credential or live call occurred.
Every receipt below lives under `/tmp/shiftwork-s36-*`, `/tmp/shiftwork-s32-*` or `/tmp/shiftwork-s33-*` and is disposable.

## What changed

- `index.html`, `styles.css`, `app.js`: the layout A grid is replaced by a full-screen room under the hosting row, a status bar (client, shift, live version, open incidents, attempts left, "Synthetic scenario"), a navy inspector that hosts the existing `#station-panel`, and a collapsed `shift.log`.
- New `workplace-story.js`: only `logEntries` and the status-bar values, as Gate 4 S36 scopes it.
- `workplace-host.js` and `workplace-scene.js`: `setInspector`, a view offset on the existing orthographic camera, `anchorPositions` and `onAnchors`.
- Station tags reuse the existing `[data-station]` buttons and sit above their projected anchors.
- `#expand-work` and `main[data-expanded]` are kept.
- `workplace-assets.json`: digests updated for `index.html`, `app.js`, `styles.css`, `workplace-host.js` and `workplace-scene.js`; new row for `workplace-story.js` (origin `shiftwork-original`, MIT, board shared).
- New `tests/client/workplace_fullscreen.mjs`; planned and user-approved edits to `workplace_browser.mjs`, `workplace_faults.mjs` and `workplace_s31.mjs`.

## User decisions recorded, 2026-10-21

(a) The `workplace_browser.mjs` status-bar assertion is replaced.
Old text:
`assert.ok(await b.evaluate(()=>document.getElementById('workplace-state').getBoundingClientRect().top < document.getElementById('workplace-canvas').getBoundingClientRect().top),'Operating identity is below the optional room');`

(b) The shift log is collapsed at all widths.

(c) `inspector_keeps_stations_readable` has two faults: skip the view offset (`skip-offset`) and drop the inspector clamp (`no-clamp`).

(d) The inspector is a navy frame holding an `.inspector-sheet` paper sheet.
The existing topbar is kept as a recorded deviation from the v2 mockups.

(e) `runLifecycle` opens `[data-station="customers"]` before the 390px offscreen step, because the narrow inspector is closed until a station opens.
Lines were added; nothing was removed.

(f) New assertion "<200% zoom|Exact viewport> station tag text escapes its control" in `runZoom` and `runExactViewports`.
The `zoom-omit-station-column` row in `workplace_faults.mjs` now expects '200% zoom station tag text escapes its control'.
Old text:
`...['picker','station-column'].map(owner=>({name:`zoom-omit-${owner}`,expected:'200% zoom causes horizontal page scrolling',zoom:true})),`

Gate 3 section 13.9 planned edit, `workplace_s31.mjs` `assertLayout`: the 1280px layout A `sideBySide` check is replaced by the `inspector_keeps_stations_readable` assertion at 1280x720.
Old message: 'The 1280px comparison layout is not readable side by side'.
The 640px and 390px `stacked`, two-card and overflow assertions stay.

## Defects found and repaired in this continuation

1. The earlier S36 session dropped the narrow `.journey a { white-space: normal; }` rule.
Narrow tag text escaped its control while page `scrollWidth` stayed equal to the viewport, so only decision (f) exposed it.
The rule is restored (`styles.css` line 268); `MISTAKES.md` records the cause and prevention.
2. At 1280x720 with the Bellwether inspector open, the "Next shift" tag covered "Incident & ledger wall".
`placeStationTags` fell back to its first candidate, ignoring overlap, when no free spot existed.
It now takes the in-bounds spot with the least overlap.
`inspector_keeps_stations_readable` gained the assertion "a station tag covers another station tag" with fault `overlap-fallback`, which restores the old fallback.
3. Two fullscreen faults (`skip-offset`, `stack-overflow`) also break tag spacing, so the new assertion masked their own.
A fault run now executes only the check its expected assertion names, and the overlap assertion runs after the centring assertion.

## Verification

All runs below are on the final source, after the tag-overlap repair, unless marked otherwise.

| Check | Result | Receipt |
|---|---|---|
| Three extracted journeys and three actual rooms | PASS, external asset block self-tested | `/tmp/shiftwork-s36-run8` |
| Node unit tests | 207 pass, 0 fail | `node --test tests/client/*.test.mjs` |
| `workplace_fullscreen.mjs` clean, three boards | PASS | `/tmp/shiftwork-s36-controls/fullscreen` |
| `workplace_fullscreen.mjs` faults | 24 of 30 rows as expected: clean on all three boards, all ten Bellwether faults caught by their named assertion; `no-clamp`, `overlap-fallback` and `leak-selection` not reachable on Stonebridge or Northline | `fullscreen-run3.log` |
| S31 browser controls (`run-controls.py`) | 33 of 34 as expected; `journey-omit-initial` is the main baseline failure | `/tmp/shiftwork-s36-controls/controls` |
| Lifecycle offscreen guard, decision (e) | Clean PASS; in-memory fault (served `workplace-host.js` with `visible=true;`) fails with 'Offscreen room allowed graphics frames' | `controls/lifecycle-offscreen-fault` |
| `workplace_faults.mjs` source | 152 controls PASS, production unchanged | `/tmp/shiftwork-s36-suites/workplace-faults-source` |
| `workplace_faults.mjs --browser` | Fails only on `page-cache-omit-focus`, the main baseline failure | `workplace-faults-browser/run.log` |
| S32 faults, S33, S34 (seed `run8/gtm-input/closed.db`), S35 controls | PASS | `/tmp/shiftwork-s36-suites` |
| Fallback with the static room, three boards | PASS at 390px | `fallback-*` |
| Contrast (`--contrast`) | Exit 0; station tags 15.4 text, 5.5 border | `contrast-bookshop` |
| Asset closure (`tests/packaging/test_client_asset_closure.py`) | 9 passed | pytest |
| Zoom faults, decision (f) | All three caught in `runZoom` and `runExactViewports`; clean and restored pass (before the tag-overlap repair) | `/tmp/shiftwork-s36-controls/zoom-faults.mjs` |
| Disposal `omit-*` rows | 7 clean, caught, restored (before the tag-overlap repair) | earlier S36 run |
| pytest `--ignore=tests/packaging` | 1454 passed, 1 failed `port_dead`, 1 skipped, the baseline; rerun on the final source | `/tmp/shiftwork-s36-pytest/run.log` |
| Screenshots, 18 cells (three boards at 1280x720 open and closed, 640x900 and 390x844 at 100% and 200%) | `scrollWidth` equals `innerWidth` in every cell; the 1280 open Bellwether overlap was found here and repaired | `/tmp/shiftwork-s36-shots` |

Further final-source runs:

- Performance, `workplace_perf.mjs` alone on a Bellwether preview: both tiers PASS, no frame misses, idle 0, cold starts 2807 to 2896 ms (`/tmp/shiftwork-s36-perf/out2`).
- Zoom faults rerun: `zoom-omit-picker`, `zoom-omit-station-column` and `zoom-omit-navigation` each caught by their named assertion in `runZoom` and `runExactViewports`; clean and restored PASS (`/tmp/shiftwork-s36-zoom/final`).
- `workplace_faults.mjs --browser` rows before `page-cache-omit-focus` (four listener rows, `omit-shadow`, `omit-dispose-raf`, `omit-suspend-raf`): clean, caught, restored.
- `render_faults.mjs`: 39 of 50 rows as expected (`/tmp/shiftwork-s36-suites/render-faults`).
The `inherit` baseline fails with "The recorded-history region does not point its missing newest run at the hypothetical experiment", and the main extract fails it identically.
The `verdict`, `event`, `stationFocus`, `incidentFocus`, `outcomeBlocker` and `requirementVersion` rows fail their exactly-once anchor check; each needle occurs 0 or 2 times in main's `app.js` as well.
The inherit fault rows depend on the failing inherit baseline.
These failures predate S36.

## Known limits and pre-existing failures

- On main (extracted to `/tmp/shiftwork-s36-main`), `journey-omit-initial` and `workplace_faults --browser page-cache-omit-focus` fail the same way as on this branch.
They were broken before S36 and are not attributed to it.
- Because `page-cache-omit-focus` aborts that suite, its later rows never run on main or on this branch.
Run directly from a scratch copy without that row, `focus-guard-generation` fails with "Focus guard workbench unavailable" on both, so the focus-guard, partial-initialization and host-retry rows remain unproven on both.
- `render_faults.mjs` pre-existing failures are listed under Verification.
- Post-slice cleanup scan: `.panel-symbol` (`styles.css` line 163) lost its only element when S36 rewrote the inspector heading and is now dead CSS. The user answered "U make the call"; the rule was deleted, the `styles.css` digest in `workplace-assets.json` refreshed, and asset closure (9 passed), node unit tests (207 pass) and `workplace_faults.mjs` source (152 PASS) rerun on that source.
The `gtm-*` and `northline-*` position classes were already unused on main.
No orphan file, unused export or scratch file is in the tree.
- `no-clamp`, `overlap-fallback` and `leak-selection` are not caught on Stonebridge or Northline, because those boards never reach the state each fault needs (no tag anchored under the inspector, no tag without a free spot, no operating selection).
They are caught on Bellwether.
- One-off failures, recorded and not repeated on rerun: `status-not-first` once failed with "Actual WebGL2 context missing" under load and was caught when run alone; the `runZoom` clean run once failed on keyboard focus at 1280px.
These are possible flakes, not clean proof.
- Contrast: the `--contrast` receipt measures the status bar, graphics controls and station tags only.
Navy inspector heading ratios are computed from the opaque `#121b27` panel: `h2` 15.4, eyebrow 8.4, close button border 8.4.
The heading rule (1.5) is decorative.
- The `-full` screenshots at 200% zoom render at half scale; this is a capture artifact, and `scrollWidth` equals `innerWidth` in every cell.
- Perf ran on a host with unrelated desktop-app Node processes active.
- Not checked: native Safari, physical devices, assistive technology and any reviewer comprehension.
