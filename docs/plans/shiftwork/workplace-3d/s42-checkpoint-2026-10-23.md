# S42 checkpoint, 2026-10-23

S42 (robot crew on three boards) on `shiftwork/slice-42` from main `465c3df`, after the user's go-ahead: "Yes, start S42 on shiftwork/slice-42."
Accepted by the user on 2026-10-23: "Okay can u commit and push s42 to main i accept it" Committed in focused batches, fast-forwarded into main and pushed, no co-author trailer. The walk-length and bot-size limits below were accepted as recorded, unchanged.
No install, download, credential, provider call, deployment or protected-fixture edit occurred.
The crew is original code built from core Three.js primitives; nothing is taken from agentic-factory or any model file.

## What changed

- `workplace-crew.js` (new): `createCrew({ THREE, room, tier, reducedMotion, register })` and the pure `routeBetween(graph, from, to)` (Gate 3 section 14.1).
Every bot box is an instance of one unit cube, every light an instance of a second cube, every shadow disc an instance of one circle: three instanced meshes and five registered resources per crew, at any bot count.
- `workplace-rooms.js`: `crew` for Bellwether (owner and three customers), Stonebridge (revenue owner and one requester) and Northline (co-op owner and one rider), each with home, nodes, hand-checked edges and one stand per station.
- `workplace-scene.js`: crew tick in the single RAF, a walk counts as active motion, `setOpenStation(id, { settled })`, `crewAnchors()`, crew settle on suspend, reduced motion and dispose; walk-only frames report crew points with null stations.
- `workplace-host.js`: forwards `setOpenStation`, remounts with `{ settled: true }`, adds `crew` to the `onAnchors` payload.
- `app.js`, `index.html`, `styles.css`: the "You" chip inside `#workplace-canvas`, shown only when graphics are ready; the narrator bubble sits above its speaker bot; `openStationId` is set by a learner's station choice and cleared on inspector close.
- `workplace-assets.json`: `workplace-crew.js` row; every source digest recomputed after code freeze.

## Proof

Receipts: `/tmp/shiftwork-s42-20261023/`.
Each browser run used a fresh preview database on port 8371.
Numbers are this Mac's headless Chrome only.

| Check | Result |
|---|---|
| Node unit suite | 283/283 (S41 266 + 6 checks + 11 faults) |
| `workplace_crew.test.mjs` | `crew_routes_stay_clear`, `bot_walks_only_on_learner_choice`, `crew_settles_without_motion`, `crew_motion_within_limits`, `crew_disposed_once`, `crew_carries_no_result_text` pass; 11 faults each fail their own assertion |
| `workplace_crew_browser.mjs` | three boards pass (`crew-final`); 9 served faults each fail their own assertion (`crewfaults.summary`) |
| `workplace_fullscreen.mjs` | bookshop, gtm, northline pass, including 1280x720, 640x900 and 390x844 at zoom 1 and 2 |
| Fullscreen faults | 63 of 63 each fail their own assertion (`fsfaults.summary`, `fsf3-two-owner-lines`), including S41's `calm_room` faults; `two-owner-lines` needed the repair below |
| `workplace_browser.mjs` room suite | pass |
| `workplace_faults.mjs --browser` | 152 source controls, 35 browser controls |
| `workplace_s32_faults.mjs`, `workplace_s33_controls.mjs` | pass |
| Journeys | bookshop, gtm, northline pass |
| `workplace_perf.mjs` | no budget misses on three boards (table below) |
| Renderer suite | 39 of 50 as expected; the failing `baseline (inherit, no fault)` row and the 10 wrong-failure fault rows are the same 11 rows as S41 (summary lines diffed against `/tmp/shiftwork-s41-20261023/render.log`; per-row messages were not re-diffed) |
| Python `pytest --ignore=tests/packaging` | 1 failed (`port_dead`, known), 1454 passed, 1 skipped, same as S41 |
| Asset closure | 9 passed |
| `git diff --check` | clean; untracked files have no trailing whitespace |
| Post-slice cleanup scan | nothing stale; `crewMotion` is exported with no outside importer and kept as the one statement of the rule 5 limits |

### Perf with the crew

| Board | Cell | Triangles | Draw calls | Estimated bytes | Misses |
|---|---|---|---|---|---|
| Bellwether | 1280 DPR 1 / 2 | 35,776 | 84 (S41: 80) | 46,030,848 / 99,736,416 | none |
| Bellwether | 390 DPR 3 (compact) | 6,468 | 30 (S41: 27) | 1,907,776 | none |
| Stonebridge | 1280 DPR 1 / 2 | 8,772 | 53 | as above | none |
| Stonebridge | 390 DPR 3 | 1,428 | 20 | 1,907,776 | none |
| Northline | 1280 DPR 1 / 2 | 7,668 | 43 | as above | none |
| Northline | 390 DPR 3 | 2,112 | 19 | 1,907,776 | none |

The perf harness measures pulse and camera motion, not a crew walk.
The crew browser check adds `crew_walk_frames`: during the first second of a walk, frame intervals were median 16.7ms and p95 at most 16.8ms on each board, inside the 16.7ms / 33.4ms standard budget; fault `walk-janks` (40ms busy wait per walking tick) fails it.
The compact tier never shows a walk, so it has no walk-interval receipt.
The DPR 2 byte estimate (95.1MiB of 96MiB) is the backing store, unchanged by the crew.
The mesh merge fallback in Gate 3 section 14.3 was not needed.

### Walk durations

At 2.6 units per second, the longest home-to-stand walk is 3.27s (Stonebridge home to qualification rules); the unit check asserts at most 3.5s for these.
A learner who picks a second station while the inspector is open walks stand to stand: the longest is 5.31s (Stonebridge pipeline wall to qualification rules), then 4.77s (Bellwether compare to ledger) and 4.37s (Northline system map to rollout).
Gate 3 section 14.2 rule 3 says "a walk takes at most about 3 seconds"; stand-to-stand walks do not meet that sentence. This is an open decision for the user, not repaired.

## Defect found and repaired in this session

A hidden tab about 800ms into a walk, then shown again, left the "You" chip 166px from the bot, which had already been settled at its stand.
`setSuspended(true)` settled the crew but did not mark the crew anchors dirty.
The first version of the check hid the tab 150ms into the walk, while the camera ease was still running, and settling the camera refreshed every anchor, which masked the gap.
Repair: `crewDirty=true` in `setSuspended`.
Proof: the check failed before the repair (`crew-repro2`), passes after (`crew-fixed`, `crew-final`), and fault `resume-stale-chip` restores the old line and fails on "chip left behind after a hidden tab".
Logged in `MISTAKES.md`.

## Existing-check changes (old text)

```javascript
// tests/client/workplace_browser.mjs: motion-omit-settle needle and replacement now also carry the crew settle
'setReducedMotion(value) { reducedMotion=value; if(value) { settleAllPulses(); settleAmbient(); settleCamera(); } requestFrame(); }'
// receipt-root guards admit s42
/^\/(?:private\/)?tmp\/shiftwork-s(?:3[6789]|40|41)-[^/]+(?:\/|$)/                          // workplace_fullscreen.mjs
/^\/(?:private\/)?tmp\/shiftwork-s(?:29|...|38|39|40|41)-[^/]+(?:\/|$)/                      // workplace_browser.mjs
/^\/tmp\/shiftwork-s(?:29|...|38|39|40|41)-/                                                // workplace_faults.mjs
/^\/tmp\/shiftwork-s(?:32|40|41)-/  and  /^\/tmp\/shiftwork-s(?:33|40|41)-/                   // s32 faults, s33 controls
// tests/client/workplace_view.test.mjs: the fake scene gains a recorder after 'setInspector(){},'
setOpenStation(...args){(h.openStations??=[]).push(args);}
```

```javascript
// tests/client/workplace_fullscreen.mjs: fault two-owner-lines, broken since S41 commit 40bfad5 (not run in S41)
needle: "  text('owner-bubble-text', owner ?? '');\n",
replacement: "  text('owner-bubble-text', owner ?? '');\n  if (owner && ...",
expect: 'main_view_shows_one_of_each: fresh shift shows 2 owner'
```

S41 rewrote the line to `said('owner')?.text`, so the needle matched nothing and the fault reported a harness error instead of being caught.
The needle and replacement now follow the current line.
Since S41's single narrator, a fresh shift shows the customer's request rather than an owner line, so the duplicate first appears at "investigating"; the expected text says so.
The guard is unchanged: it still fails when two owner bubbles show.

No existing assertion was removed or weakened.
The 30-switch disposal control in `workplace_browser.mjs` already counts crew resources through its `geometries`/`materials` registration pattern.

## Additive deviations to record

- `setOpenStation(stationId, { settled })`: the host remount passes `settled: true`, so a remount shows the bot at the open station with no walk.
- `crew.state()`: test-only observation hook, never shown on screen.
- The chest light repeats the bot's antenna (lamp) colour rather than green, so no bot light can read as a verdict.
- `crew_motion_within_limits` (Node) and `crew_walk_frames` (browser) are extra checks beyond Gate 3 section 14.4.

## Limits and open decisions

- Stand-to-stand walks exceed "about 3 seconds" (above).
- Idle crew motion stops 20 seconds after the last input, as approved in Gate 3 section 14.5; kept unchanged.
- Bots use the visual-spec 1.1-unit height; mockup 17 rendered them at 1.3 to 1.6 scale, so they read small at 1280px. Art review is the user's.
- `app.js` also calls `setOpenStation(openStationId)` right after creating a host, to carry the open station into a fresh mount; the host applies it settled on mount, so it never starts a walk by itself.
- Proof is this Mac's headless Chromium, not physical devices or an audible screen reader.
- The five-question comprehension target remains unmeasured.
