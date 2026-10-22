# S41 checkpoint, 2026-10-23

S41 (calm Bellwether room) on `shiftwork/slice-41` from main `ba75498`, after the user's same-day re-approval of Gates 1 to 4 and S41 go-ahead.
Accepted by the user on 2026-10-23: "I accept and commit pls push to main." Committed in focused batches, fast-forwarded into main and pushed, no co-author trailer.
No install, download, credential, provider call, deployment or protected-fixture edit occurred.

## What changed

- `workplace-story.js`: pure `restingTags(view, guide, lamps)` and `narrator(view, guide, output)` (Gate 3 section 14.2 rules 1 and 2).
- `app.js`: one narrator bubble; each bubble names its station and lamp text; Bellwether tags carry `data-resting` (`true`, `false` or `speaker`); scene hover sets `data-hover` on the matching tag.
- `styles.css`: at 761px and wider over the drawn room, `false` and `speaker` tags fade out (180ms, none under reduced motion) and take no pointer events until hovered or keyboard-focused; an open station's own tag shows unless that station is speaking; the ready-state room description moves off screen for assistive technology, so the hint card keeps only its controls.
- `index.html`: `#customer-bubble-station` and `#owner-bubble-station`.
- `workplace-scene.js`: `onHover` from an owned `pointermove`/`pointerleave` raycast (mouse and pen only); camera fit uses the floor footprint, so wall tops may crop.
- `workplace-host.js`: forwards `onHover`.
- `workplace-assets.json`: refreshed source digests; no new asset.

Interpretation for review: Gate 3 section 14.2 rule 1 says an open station shows its tag; when that station is also the speaker (the customer queue at step 1), the tag stays hidden because the bubble already names it. This removed a duplicate "Customer queue · 3 open complaints" seen in the 1280x720 review.

Result at 1280x720 on a fresh shift: one tag (Incident & ledger wall, 3 open) and one bubble (the customer's recorded request, naming Customer queue) rest visible. S40 showed ten tags and two bubbles.

## Proof

Receipts: `/tmp/shiftwork-s41-20261023/` and `/tmp/shiftwork-s41-faults/`. Each browser run used a fresh preview database (`run.sh`, `fresh.sh`).

| Check | Result |
|---|---|
| Node unit suite | 266/266 (baseline 260 + 2 checks + 4 faults) |
| `resting_tags_show_next_and_one_failure`, `one_narrator_bubble` (Node) | pass; faults `resting-every-failure`, `resting-drops-guide`, `narrator-request-every-step`, `narrator-owner-at-queue` each fail their own assertion |
| `calm_room` browser check (counts, bubble, reachability, open station) | pass; faults `resting-all-visible`, `speaker-tag-shows`, `two-bubbles`, `focus-stays-hidden`, `hidden-leaves-tab-order`, `open-tag-hidden` each fail their own assertion |
| `workplace_fullscreen.mjs` | bookshop, gtm, northline pass (gtm and northline ran before the final `speaker` edit, which touches only Bellwether tags and one CSS selector) |
| `workplace_browser.mjs` room suite | pass |
| `workplace_faults.mjs --browser` | 152 source controls, 35 browser controls (31 + 4 new listener controls) |
| Journeys | bookshop, gtm, northline pass |
| `workplace_perf.mjs` | no budget misses |
| Python `pytest --ignore=tests/packaging` | 1 failed (`port_dead`, known), 1454 passed, 1 skipped, same as S40 |
| Asset closure | 9 passed |
| `git diff --check` | clean |

## Existing-check changes (old text)

```javascript
// tests/client/workplace_browser.mjs: host observation anchor, updated for the new onHover parameter
const needle='export function createWorkplaceHost({container,fallback,status,onStation,onConsequence,onAnchors}) {';
// tests/client/workplace_browser.mjs (3 places) and workplace_faults.mjs (2 places): listener type lists, extended with pointermove and pointerleave
['pointerdown','pointerup','pointercancel','webglcontextlost']
// receipt-root guards admit s41 alongside s40
/^\/(?:private\/)?tmp\/shiftwork-s(?:29|30|31|32|33|34|35|36|37|38|39|40)-[^/]+(?:\/|$)/   // workplace_browser.mjs
/^\/(?:private\/)?tmp\/shiftwork-s(?:3[6789]|40)-[^/]+(?:\/|$)/                          // workplace_fullscreen.mjs
/^\/tmp\/shiftwork-s(?:29|30|31|32|33|34|35|36|37|38|39|40)-/                            // workplace_faults.mjs
/^\/tmp\/shiftwork-s(?:32|40)-/  and  /^\/tmp\/shiftwork-s(?:33|40)-/                      // s32 faults, s33 controls
```

No existing assertion was removed or weakened. The Gate 3 section 14.4 note about moving S37 bubble assertions from two to one was not needed: the existing story journey already counted one owner or one customer bubble per step.

## Limits

- Hover reveal was checked by hand in the local browser; no automated pointer-hover assertion exists, because tag rectangles do not expose their 3D anchor point.
- Renderer suite (`render_faults.mjs`, full run): 39 of 50 as expected. The 10 wrong-failure fault rows and the failing `baseline (inherit, no fault)` row are the same 11 inherited records as S40, with line-identical messages (`/tmp/shiftwork-s40-20261022/suites/render-faults/run.log` against `/tmp/shiftwork-s41-20261023/render.log`). S40's additional `baseline (transient surfaces)` 778px overflow passed in this one run; its frequency is still unknown, and this is not a claim that it is fixed.
- Proof is this Mac's headless Chromium, not physical devices or an audible screen reader.
- The five-question comprehension target remains unmeasured.
