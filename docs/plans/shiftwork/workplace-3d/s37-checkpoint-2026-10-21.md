# S37 checkpoint, 2026-10-21

S37 (Bellwether story layer) started on `shiftwork/slice-37` from main `4727c82` after the user's words "U make the call. Then publish the branch and merge to main and then start s37".
The continuation session finished the slice on 2026-10-21 under the user's extension to a 300k context budget.
No install, download, deployment, credential or live call occurred.
The user ACCEPTED S37 on 2026-10-21 ("Yep i accept slice 37 please merge the other branch to main(if theres nothing else left to do), and push to main") and authorized the merge and push.

## What the learner sees

- A first-time visitor (no board parameter and no station link) sees the shift picker: the seven steps and one card per client with its question, what the shift teaches and a "Start shift" button. "Change shift" in the status bar reopens it. Choosing a station or a journey link closes it, because that keeps the current shift.
- In Bellwether, a step chip below the status bar reads "Step N of 7" and the step name from recorded state. One next-action button, labelled with the step name, opens the guide's station and sends no request.
- The owner's line sits in a bubble near the owner desk, and the customer's recorded request in a bubble near the queue. On screens 760px and narrower both bubbles follow the station tag list.
- Station tags show a lamp dot and lamp words; the attention station has an amber outline.
- Plain labels: "Live version" (was "Operating choice"), "Backup version" (was "Retained alternative") and "What would prove you wrong" (was "Falsifier").
- Stonebridge and Northline show the active station's existing title in the next-action panel and no chip.
- While the inspector is open at 761px and wider, its footer replaces the next-action panel.

## Files

- `workplace-story.js`: `STEP_NAMES`, `guideStep`, `planSlips`, `lampStates`, `OWNER_LINES`, `ownerLine`, `customerBubble`, `SHIFT_CARDS`. Imports only `selectEvidence`.
- `workplace-view.js`: `projectWorkplace` adds `slips`, `attention` and `lamps`.
- `app.js`: `renderGuide`, `placeBubbles`, the picker (`showPicker`, `startShift` through `switchWorkplace()`), next-action and draft listeners, plain labels, explicit selection-summary field keys, finer tag placement steps.
- `index.html`: `#shift-picker`, `#change-shift`, `#step-chip`, `#next-action` with `#next-action-go`, `#story-layer` bubbles, lamp spans on Bellwether tags, plain labels.
- `styles.css`: story layer, picker, status-bar spacing, inspector top below the chip, narrow order.
- `workplace-assets.json`: digests refreshed for `index.html`, `app.js`, `styles.css`, `workplace-story.js` and `workplace-view.js` after code freeze.
- New `tests/client/workplace_story.test.mjs`; S37 checks added to `tests/client/workplace_fullscreen.mjs`.

## Decisions taken with the user, 2026-10-21

- Picker trigger: "No board, no hash". The picker shows only when the URL has neither a board parameter nor a station hash, and from "Change shift".
- Gate 3 section 13.5 rule 4: "Outcome status COMPLETE". The guide reads the comparison outcome status.
- `view.slips`: "Keep in S37" as data only; S41 still owns replay and its checks-accepted guard.
- Gate 3 backtrack, rule 2: a browser smoke on the fresh demo showed "Step 7 of 7" for a first-time visitor, because the starter version's own operation run of shift 1 is already `FINALIZED`. The user chose "Learner choice only", the revised rule 2 text was shown, and the user re-approved it in chat ("Re-approve"). `guideStep` and `guide_step_follows_recorded_state` were changed only after that; the new case "starter operation run" and the fault `starter-ends-shift` prove it.

## Interpretations made in this slice, for the user's review

- Stonebridge and Northline: the next-action panel shows the active station's title and no button, since they have no guide.
- In the demo world a new choice can operate only in the next shift (the starter already operated shift 1), so the guide goes: choose (step 6 at Your service, where the run button stays disabled with its own help text), close (step 7 at Next shift), open shift 2 (step 1), run (step 7 at the wall). The v2 mockups show the run in shift 1. The guide follows recorded state and never decides whether a command is allowed.
- On the fresh demo the starter's two recorded requests pass their checks, so step 1 shows "No complaints" and no owner line (the step 1 line needs a count above zero).

## Changes to existing checks, with old text

1. `tests/client/workplace_view.test.mjs`, `projection_whitelists_scene_fields_and_detaches_arrays`: adds the three Gate 3 section 13.4 fields to the exact key set.
Old text: `assert.deepEqual(Object.keys(v).sort(), ['schemaVersion','context','station','shiftState','operating','saved','run','evidence','investigation','tests','consequences','inheritance','consistency'].sort());`
2. `tests/client/workplace_faults.mjs` `run()`: rewrites the view's new `./workplace-story.js` import to a file URL like `./evidence.js`.
Old text: `  const inline=row.host?bytes:bytes.replace("'./evidence.js'",JSON.stringify(new URL('../../shiftwork/client/evidence.js',import.meta.url).href));`
3. `tests/client/workplace_faults.mjs` receipt root, adds 37.
Old text: `assert.ok(/^\/tmp\/shiftwork-s(?:29|30|31|32|33|34|35|36)-/.test(out ?? ''));`
4. `tests/client/workplace_browser.mjs` receipt root, adds 37.
Old text: `shiftwork-s(?:29|30|31|32|33|34|35|36)-[^/]+`
5. `tests/client/workplace_fullscreen.mjs` receipt root accepts S36 and S37.
Old text: `assert.ok(/^\/(?:private\/)?tmp\/shiftwork-s36-[^/]+(?:\/|$)/.test(path.resolve(out)), 'S36 receipts must use /tmp/shiftwork-s36-*');`
6. `tests/client/workplace_fullscreen.mjs` `MAIN_VIEW` now serializes the step chip, next action and bubbles as Gate 3 section 13.6 requires.
Old text: `const nodes = [document.getElementById('status-bar'), ...document.querySelectorAll('.room-hotspots:not([hidden]) [data-station]')];`
7. Renamed labels, same commit as the rename. `tests/client/browser.mjs` fault `inheritAlternative` needle and replacement, old text `['Retained alternative', 'retained-alternative', ...]`; `browser.mjs` investigation row label, old text `['Falsifier', latest.falsifier]`; `tests/client/gtm_browser.mjs` fault `inheritance` needle and replacement, old text `[\'Operating choice\', \'operating-choice\', ...]`.
8. Not listed in Gate 3 section 13.9: `tests/client/workplace_browser.mjs` `runZoom` and `runExactViewports` now check "station tag text escapes its control" before "causes horizontal page scrolling". With the lamp dot, the `zoom-omit-station-column` fault made tag text cross the page edge by 2px, so the broad scroll assertion caught it first. No assertion was removed or weakened; both faults are again caught by their own assertion. This needs the user's review because it is an unplanned edit.

## Verification on the final source

| Check | Result | Receipt |
|---|---|---|
| `node --test tests/client/*.test.mjs` | 224 pass, 0 fail | terminal |
| `workplace_story.test.mjs` | 6 checks, 10 faults each caught by its named assertion, source digest unchanged | same run |
| `workplace_fullscreen.mjs` clean, three boards | PASS (inspector, identifiers, narrow at 100% and 200% including 1280x720 at 200%; Bellwether also picker and the nine-state story journey) | `/tmp/shiftwork-s37-final/clean-*` |
| `workplace_fullscreen.mjs` faults | 20 of 20 caught by their named assertion (9 S36, 11 S37) | `/tmp/shiftwork-s37-final/summary.txt` |
| Three extracted journeys and actual rooms | PASS, external asset block self-tested | `/tmp/shiftwork-s37-journeys` |
| `workplace_faults.mjs` source | 152 controls PASS, production unchanged | `/tmp/shiftwork-s37-suites/workplace-faults-source` |
| `workplace_faults.mjs --browser` | Fails only on `page-cache-omit-focus`, the main baseline | `/tmp/shiftwork-s37-suites/workplace-faults-browser` |
| Disposal rows (`omit-*`, 7) | clean, caught, restored | `/tmp/shiftwork-s37-rest/browser-faults.json` |
| `render_faults.mjs` | 39 of 50 as expected; the same 11 rows as S36, inherit baseline with the same message | `/tmp/shiftwork-s37-suites/render-faults` |
| S32 faults, S33, S35 controls | PASS | `/tmp/shiftwork-s37-suites` |
| S34 controls (seed `/tmp/shiftwork-s37-journeys/gtm-input/closed.db`, as S36) | PASS | same |
| Fallback with the static room (Bellwether fresh; Stonebridge and Northline seeded from the journey `comparison.db`) | PASS at 390px | `fallback-*` |
| Contrast (`--contrast`) | exit 0 | `contrast-bookshop` |
| Performance (`workplace_perf.mjs`, section 9 budgets) | exit 0; cold ready 2816 to 2900ms at 1280 and 390; idle frames 0; no misses | `perf` |
| S31 controls (`run-controls.py`) | 32 of 34 as expected; `journey-omit-initial` is the main baseline; `status-first-clean` failed once and passed 9 reruns (flaky, below) | `/tmp/shiftwork-s37-controls/controls-summary-run1.json` |
| Zoom faults | each of the three caught by its own assertion in `runZoom` and `runExactViewports`; exact viewports clean and restored PASS | `/tmp/shiftwork-s37-zoom` |
| Asset closure | 9 passed | pytest |
| pytest `--ignore=tests/packaging` | 1454 passed, 1 failed `port_dead`, 1 skipped, the baseline | `/tmp/shiftwork-s37-pytest/run.log` |
| `git diff --check` | clean | terminal |
| Screenshots, 18 cells | `scrollWidth` equals `innerWidth` in every cell | `/tmp/shiftwork-s37-shots` |

## Known limits and failures

- `runZoom` clean fails at "Zoomed keyboard station ... at 1280px did not reach and focus its panel" on this branch (5 of 5) and on extracted main (3 of 3) in this session; the station varies. A separate session traced it to the runner sending Enter before its instant scroll settled, and fixed it in `workplace_browser.mjs` on `shiftwork/zoom-keyboard-settle` (merged with S37).
- `focus-guard-*` rows in `faults-rest.mjs` stop at "Focus guard workbench unavailable" on this branch and on extracted main alike. S36 never reached these rows. The same session found a stale fault anchor (`generation === state.generation` now matches three times) and fixed it on that branch.
- `status-first-clean` (`workplace_browser.mjs` default run) failed once at "Actual WebGL2 context missing" and passed the next 9 runs. The failing receipt was overwritten by the reruns, so its cause is [unknown].
- Northline's long client name wraps "Change shift" onto a second status-bar row at 1280px.
- The five-question target and the owner-line catalogue's effect on learners remain unmeasured. A word list cannot prove a line does not hint; the user accepted the slice after the catalogue and picker copy were shown in chat.
- The guide's demo journey runs on synthetic scenario state. No outcome here is a real customer, revenue or learning result.
- Post-slice cleanup scan: no orphaned or scratch files in the tree, every new export and CSS class has a consumer, no TODO or debug lines in the diff.
