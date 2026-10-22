# S38 checkpoint, 2026-10-22

S38 (render recipe and the light Bellwether room) started on `shiftwork/slice-38` from main `32f05f1` after the user's words "yes, go ahead on shiftwork/slice-38".
Three sessions did the work on 2026-10-22; nothing is committed.
No download, deployment, credential or live call occurred.
One unauthorized install ran by mistake: see "Known limits and failures".
The user ACCEPTED S38 on 2026-10-22 ("Yep i accept s38"). The user then approved the 13.8 wording update and authorized committing and pushing to main. S39 has no go-ahead.

## What the learner sees

- Bellwether is a warm, light bookshop: cream walls, light wood floor, wooden shelves, navy trim on the cut wall edges and skirting.
- All three rooms use one perspective pose (30 degree field of view, 45 degree azimuth, 39 degree elevation), ACES filmic tone mapping, linear fog and, on the standard tier, a first-party PMREM studio environment.
- Furniture has rounded edges on the standard tier and plain boxes on compact.
- Each Bellwether station has a small glowing lamp whose colour matches its tag's lamp dot and words.
- Stonebridge and Northline get the shared renderer settings with their existing palettes and no lamps (their lamps are S42).
- From 761px to 960px wide, each station tag shows its status words under its name, so tags fit side by side next to the inspector.
- From 761px to 1280px wide, with the inspector open or closed, no station tag covers another.

## Files

- `workplace-scene.js`: perspective camera, ACES tone mapping, fog, `buildStudioEnvironment` (PMREM, standard only), `tierPixelRatio` with the 1,850,000-pixel backing-store cap, `roundedBox` with a shared geometry cache, static lamp meshes (`MeshBasicMaterial`, `toneMapped: false`, one material per colour), disposal of the environment target, cache and lamps.
- `workplace-rooms.js`: Bellwether palette, navy trim, lamp anchors, the shared `studioPose`, roughness and metalness from visual-spec 11.3 for all rooms.
- `workplace-assets.json`: rows for `rounded-geometry-builder`, `studio-environment` and `status-lamps`; digests refreshed after code freeze for `app.js`, `styles.css`, `workplace-scene.js`, `workplace-rooms.js` and the three new rows.
- `app.js` `placeStationTags`: the fallback ranks overlap with already placed tags before overlap with panels, and the search reaches six rows and 1.2 tag widths.
- `styles.css`: one rule stacking tag status words under the name at 761px to 960px. This file is outside the S38 file list and the user's tag decision named only `placeStationTags`; it is raised for review below.
- Tests: `workplace_fullscreen.mjs` (`renderer_matches_tier_recipe`, `lamps_reflect_state_with_text`, the four-cell `inspector_keeps_stations_readable`, new faults), `workplace_browser.mjs` (anchors, probes, S38 receipt root), `workplace_faults.mjs` (environment and cache disposal controls, receipt root), `workplace_perf.mjs` (13.8 budgets, DPR 2 tier, compact DPR 3 tier), `workplace_view.test.mjs` (13.8 budget mutations).
- `03-program-design.md`: the 13.8, 13.6 and 13.9 backtracks below.

## Decisions taken with the user, 2026-10-22

- Gate 3 section 13.8: the first measurement drew a 2560x1140 backing store at 1280x720 and DPR 2, estimated at 144.1MiB against the 96MiB budget. The user chose "Lower pixel cap (Recommended)": 4,200,000 to 1,850,000 pixels, antialiasing kept. The user re-approved the edited text ("Re-approve 13.8").
- Gate 3 sections 13.6 and 13.9: the perspective pose made the S37 fault `overlap-fallback` unreachable at 1280x720 and introduced a Bellwether `evaluator/pipeline` overlap at 1024x720. The user chose "Fix in S38 (Recommended)" and re-approved the backtrack text ("Re-approve 13.6/13.9"): tags never cover tags from 761px to 1280px, and the check gains 1024x720 cells open and closed.

## Interpretations made in this slice, for the user's review

- A lamp whose station has no known tone uses the idle colour.
- Visual-spec 11.3 roughness and metalness apply to all three rooms, not only Bellwether.
- Navy trim was added as cap rails and skirting; desk plinths use the navy trim colour as "console bodies". The art self-review found the plinths heavy.
- Console enamel uses navy with roughness 0.55.
- Stacking tag status words under the name at 761px to 960px is a layout reading of visual-spec 11.2 ("name, status words and a small lamp dot"); placement alone could not fit ten one-line tags in the roughly 370px left beside the inspector at 761px and 850px.

## Changes to existing checks, with old text

The original files are kept at `/tmp/shiftwork-s38-notes/orig/`.

- `inspector_keeps_stations_readable` (13.9, backtracked): was one 1280x720 inspector-open cell. Now 1280x720 and 1024x720, each closed then open; centring stays at 1280x720 only. Old final assertion: `assert.deepEqual(covered, [], 'inspector_keeps_stations_readable: a station tag covers another station tag');`. New text appends ` at <width>x<height> <closed|open>`; the fault expectation is a prefix, so it still matches.
- `overlap-fallback` needle (anchor changed with the production statement): old `      ?? inside.reduce((best, spot) => overlap(box(spot)) < overlap(box(best)) ? spot : best, inside[0] ?? candidates[0]);`, new `      ?? inside.reduce((best, spot) => less(box(spot), box(best)) < 0 ? spot : best, inside[0] ?? candidates[0]);`.
- Fault-run output gains `message` (the first line of the failing assertion) so the failing cell is recorded.
- Receipt roots: old `shiftwork-s(?:29|...|37)-` in `workplace_browser.mjs` and `workplace_faults.mjs`, and `shiftwork-s3[67]-` with "S36 and S37 receipts must use /tmp/shiftwork-s36-* or /tmp/shiftwork-s37-*" in `workplace_fullscreen.mjs`; S38 is added (old text in `/tmp/shiftwork-s38-notes/old-roots.txt`).
- `workplace_perf.mjs` budgets (13.8 replaces section 9): old triangles `compact?20000:45000`, calls `compact?45:90`, bytes `compact?24:48` MiB, one DPR 1 tier per width; new 120,000/40,000, 120/60, 96/24 MiB and three tiers (1280 DPR 1, 1280 DPR 2, 390 DPR 3).
- `workplace_view.test.mjs` budget mutations: old `maxTriangles=45001`, `maxCalls=91`, `estimatedBytes=49*1024**2`; new values one step past the 13.8 budgets.
- `workplace_browser.mjs` served-source anchors on the scene's resource and render statements were updated to the new statements and re-proven.

## Verification on the final source

| Check | Result | Receipt |
|---|---|---|
| Node unit tests | 228/228 | `node --test tests/client/*.test.mjs` |
| New check, before the tag fix | bookshop failed `covers another station tag at 1024x720 open` (`evaluator/pipeline`); gtm and northline passed | `/tmp/shiftwork-s38-tag/pre-*` |
| Tag sweep 761 to 1280 wide at 600, 720 and 900 tall, closed and open on every station | 0 overlaps on bookshop, gtm, northline (81 sizes) | `/tmp/shiftwork-s38-tag/sweep3-*.log` |
| Fullscreen checks, three boards clean | exit 0 each | `/tmp/shiftwork-s38-fsE/summary.txt` |
| Fullscreen faults | 50/50 caught on their named assertions; `overlap-fallback` at 1024x720 open, `tags-not-taken` at 1280x720 closed | same |
| Recipe and lamp faults | 15 recipe and 7 lamp rows among the 50 above, caught on the final source; the earlier recipe ordering repair is in `/tmp/shiftwork-s38-faults/summary.txt` | `/tmp/shiftwork-s38-fsE/summary.txt` |
| Board journeys | bookshop, gtm, northline PASS | `/tmp/shiftwork-s38-drv/master.log` |
| `workplace_faults.mjs` | 152 source and 31 browser controls PASS, including environment and cache disposal and both partial-failure rows | same |
| Renderer fault rows | 39 of 50 as expected; the 11 others match the S37 baseline failure text exactly (13 nonempty failure lines, identical hashes) | `/tmp/shiftwork-s38-suites/render-faults/run.log` |
| s32 faults, s33, s34 and s35 controls | PASS | `/tmp/shiftwork-s38-drv/master.log` |
| Contrast over the light Bellwether room | PASS | same |
| Graphics-failure fallback on three boards | PASS | same |
| Offline controls (`run-controls.py`) and remaining browser controls | all as expected; 26 browser controls PASS | same |
| Performance at 13.8 | `budgetMisses []` at all three tiers | `/tmp/shiftwork-s38-suites/perf/out/performance.json` |
| Asset closure | 9 passed; engine inventory still exactly `three.module.js` and `three.core.js` | `tests/packaging/test_client_asset_closure.py` |
| Pytest | 1469 passed, 1 skipped; failed: known `port_dead`, and the clean-install packaging test (see limits) | `/tmp/shiftwork-s38-evidence/pytest.log` |
| s34 clip | re-recorded; S37 and S38 `owner-marker.png` kept side by side | `/tmp/shiftwork-s38-evidence/s34-clips/` |

Performance on this Mac's headless Chrome (Chrome/155, ANGLE Metal, M4 Pro):

| Tier | Backing store | Estimated bytes | Triangles / calls | Median / p95 ms | Cold ms |
|---|---|---|---|---|---|
| 1280x720 DPR 1 standard | 1280x570 | 46,030,848 | 33,016 / 79 | 16.6-16.7 / 17.5-18.2 | 2,830-2,871 |
| 1280x720 DPR 2 standard | 2038x907 | 99,736,416 (budget 100,663,296) | 33,016 / 79 | 16.7 / 17.5-17.7 | 2,846-2,889 |
| 390 DPR 3 compact | capped at DPR 1 | 1,907,776 | 4,620 / 26 | 33.3 / 34.1-34.2 | 2,803-2,872 |

## Known limits and failures

- Performance margins are tight: the DPR 2 tier is 0.9MiB under its byte budget, medians sit at the 16.7ms vsync limit, and cold start is about 130ms under 3,000ms. Bytes are estimates, not GPU readings. Numbers are one Mac's headless Chrome, not real devices.
- At 1920x1080 and DPR 2 the cap draws at a ratio of 0.99.
- `test_clean_env_install_and_run` ran by mistake inside a full `pytest` run: it built a temporary venv and ran `pip`/`uv pip sync` from the lockfile, which S38 did not authorize. Whether it downloaded anything is [unknown]. It then failed on the browser receipt-root guard, because pytest's temporary directory is not an approved `/tmp/shiftwork-s*` root; S37 ran pytest with `--ignore=tests/packaging` and did not exercise it. Logged in `MISTAKES.md`.
- Pre-existing, not fixed: Bellwether bubbles cover station tags at every measured width (800 to 1440 at 720 tall), at HEAD `32f05f1` and now. Bubbles sit above tags, so a covered tag is hard to read or click.
- Pre-existing, made worse: the Stonebridge routing label (`.workplace-routing-label`, z-index 1) sits under station tags; at S37 the Workflow bench tag covered part of it, and with the new pose the Signal intake tag covers most of it.
- Art: Bellwether reads light and warm with labels hidden; the navy desk plinths look heavy; the room fills about 45% of the width at 1280x720 with labels hidden. Stonebridge and Northline keep their dark palettes. The user's art review of all three rooms is still open.
- Pending user sign-off: art review of all three rooms; the S37 fallback and status visual sign-off.
