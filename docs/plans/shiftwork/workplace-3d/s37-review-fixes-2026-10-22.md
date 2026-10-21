# S37 review fixes, 2026-10-22

## Authority and scope

The user authorized fixes F3 to F6, F7 instrumentation, the two Gate 3 section 13.5 corrections, guard repairs on a separate branch, commits and merging all changes into main. Push and S38 remain unauthorized.

F1 rule 3a was approved as written. F2 option (b) met the user's stop condition: sealed rotation determines each attempt's outcome, and the existing journey needs the starter's second run. The user then approved option (a)'s exact text, retaining visible unresolved complaints under STARTER_BASELINE. Both corrections are recorded in Gate 3 section 13.5.

F8: the user explicitly approved the `runZoom` and `runExactViewports` assertion reorder identified in the S37 checkpoint, item 8. The station-text escape assertion precedes page overflow, so each zoom fault reaches its own assertion. Neither assertion was weakened or removed. This closes that checkpoint's request for user review.

## Changes

- F1: an inherited learner choice with no operation in this shift guides to step 6.
- F2: unresolved starter complaints keep the queue and service at attention and appear in the step 1 owner line. This changes no recorded run or sealed case.
- F3: disabled Run explains a recorded operation or an exhausted attempt budget and points to Next shift.
- F4: static Bellwether tags stack their name and status, and avoid each other and floating panels at 1280x720. Northline Handover sits above the collapsed log.
- F5: the 1280px status row fits on each board, including Change shift, with 320px graphics controls.
- F6: the step chip changes its live-region text only when the text changes.
- F7: WebGL readiness errors include width, graphics state/text, room state and canvas presence. The original load-flake cause remains [unknown].
- Guard branch: freeze the initial comparison attempt before polling, check it before the broader polled assertion, and target the page-cache focus line with a unique multiline anchor.

## Changed checks and their old text

These are changes relative to main `f3d0f7a`. New checks have no old assertion.

1. `workplace_story.test.mjs`, guide cases `experiment run` and `operation run of an earlier shift`: old expected `1, 'customers', 'ready'`; now `6, 'service', 'ready'` under approved rule 3a. The old lookup `const blocked = api.guideStep(GUIDE_CASES[7][1], {});` now finds the case by name.
2. Same file, lamp row: old `['no run', view(), { customers: ['idle', 'No recorded requests'], service: ['attention', 'Live, not yet run'], ledger: ['fail', '1 open'], compare: ['idle', 'Not started'] }]`. The no-run fixture now resolves its incident and expects ledger `None open`; separate starter-open rows assert the approved behavior.
3. Same file, owner catalogue: old `assert.equal(lines.length, 8, ...)`; now 9 with `openComplaints`. Old `assert.equal(api.ownerLine(view(), { step: 1 }), null, ...)` now uses a resolved-incident view. Separate assertions cover unresolved complaints.
4. `workplace_fullscreen.mjs`: old `await expectStep(STORY_STEPS[0], 'next shift with the inherited choice');` and comment `open shift 2 (step 1)` now use `STORY_STEPS[5]` and step 6. Added Run-help, chip-mutation, static-room clipping/pair/panel and status-row assertions retain the old journey checks.
5. `workplace_browser.mjs`: old messages `Real WebGL2 room did not become ready` and `Actual WebGL2 context missing` now append width and graphics diagnostics. Conditions are unchanged.
6. `workplace_s31.mjs`: old order was `assert.ok(accepts.length >= 2, 'The comparison published no polled assignment');` then `assert.equal(attempts[0]?.state, initial.state, 'The initial comparison assignment was not published');` then `assert.equal(attempts[0]?.allowed, true, 'The initial comparison assignment was suppressed');`. The initial assertions now read the snapshot `initialAttempt` and precede the polled assertion. A later poll with the same state cannot impersonate the initial attempt.
7. Page-cache fault: old needle `editor.focus({ preventScroll: true });` matched two locations. The fault now matches that line plus the following `editor.setSelectionRange(focus.start, focus.end, focus.direction);`, omitting only focus in the pageshow handler. The product and expected continuity assertion are unchanged.
8. The runner reorder was already merged in `f3d0f7a`; its old assertion text and reason remain in the S37 checkpoint, item 8. Approval is recorded above.

9. Full-matrix repair: the owner fault's old expected text was `main_view_shows_one_of_each: investigating shows 2 owner`; now it creates one duplicate and expects `fresh shift shows 2 owner`, since the approved starter line exists on first load. The chip-leak needle and replacement used `text('step-chip-name', ...)`; both now use `announce('step-chip-name', ...)`. The `const clean = await act(controls);` snapshot now precedes the F6 typing probe instead of following it. The original count/disabled assertions are unchanged. The first full matrix's three rejected controls remain in `/tmp/shiftwork-s37-close-final/summary.txt`.

## Focused evidence

- Starting Git state matched the handoff. Node baseline and integrated source both pass 228 checks.
- Asset closure: 9 passed, two dependency deprecation warnings. Only `app.js`, `styles.css` and `workplace-story.js` digests needed refreshing.
- Northline RED: `/tmp/shiftwork-s37-fix-layout-red-northline.log` fails `fallback_tags_clear_of_panels` with `shift-log/handover`.
- All three fallback and inspector checks pass in `/tmp/shiftwork-s37-fix-layout-green-{bookshop,gtm,northline}.log`, with 10, 4 and 6 tags respectively.
- `fallback-clip`, `fallback-overlap`, `fallback-under-chip` and `status-wraps` each print their named caught assertion and exit 0 under `/tmp/shiftwork-s37-fix-layout-<fault>/run.log`.
- F7 status-first clean: `/tmp/shiftwork-s37-fix-status-first.log`, 1/1 as expected.
- Initial-publication RED hit the broader polled assertion: `/tmp/shiftwork-s37-fix-guard-initial-red.json`. Clean and both omit controls now pass their intended expectations in `guard-initial-green.log`; the restored journey passes in `guard-initial-restored.log`, all with prefix `/tmp/shiftwork-s37-fix-`.
- Page-cache RED stopped before ready. Clean and restored runs report persisted cache and dirty-editor continuity; the fault now fails `Page-cache return changed editor continuity or graphics ownership`. Receipts: `/tmp/shiftwork-s37-fix-cache-{red,clean,fault,restored}.log`.

## Full regression and final state

The code and guards are verified. The review branch contains the guard branch through merge `4dea99c`; client bytes were frozen at `725866f`. The user authorized a local main merge. Push and S38 still need named authorization.

| Check | Result | Receipt |
|---|---|---|
| Node suite | 228 passed, including the four added story faults | `/tmp/shiftwork-s37-close-node-final.log` |
| Fullscreen | Three clean boards; 27 of 27 faults caught on their named assertions; restored clean pass | `/tmp/shiftwork-s37-close-final-restored/summary.txt` |
| Source and complete browser mutation suite | 152 source controls and 27 browser controls pass; clean/fault/restored phases | `/tmp/shiftwork-s37-close-suites/workplace-faults-{source,browser}` |
| Separate browser controls | 26 of 26 pass | `/tmp/shiftwork-s37-close-rest/browser-faults.json` |
| S31 | 34 of 34 as expected; no unexpected row | `/tmp/shiftwork-s37-close-drv/controls-summary.json` |
| S32, S33, S34, S35 | All pass; S34 uses the fresh journey's closed GTM database | `/tmp/shiftwork-s37-close-suites` |
| Renderer faults | 39 of 50 as expected; all eleven complete failure strings equal the review receipt | `/tmp/shiftwork-s37-close-drv/render-comparison.json` |
| Pytest, excluding packaging | 1454 passed, one skipped, known `port_dead` failure, two warnings | `/tmp/shiftwork-s37-close-pytest/run.log` |
| Asset closure and offline environment | 9 and 6 passed respectively | `/tmp/shiftwork-s37-fix-asset.log`, `/tmp/shiftwork-s37-close-environment.log` |
| Performance and contrast | Current section 9 budgets pass at both tiers; five cold starts and three real motion samples per tier, zero idle frames, no budget misses. Local headless scope only | `/tmp/shiftwork-s37-close-suites/{perf,contrast-bookshop}` |
| Extracted archive | All three complete journeys and actual rooms pass; external-asset blocking self-tested, import origin canonicalized and verified | `/tmp/shiftwork-s37-close-drv/extracted-rerun.log`, `/tmp/shiftwork-s37-close-extracted/archive.json` |
| Screenshots | All 18 cells have no horizontal overflow; representative desktop/mobile and all three fallback images inspected | `/tmp/shiftwork-s37-close-shots`, `/tmp/shiftwork-s37-close-visuals/review.html` |

The first fullscreen matrix's three stale controls are preserved in `close-final`; the corrected matrix is `close-final-restored`. The archive preflight's rejected path-alias comparison remains in `extracted-preflight-red.log`. The final rerun exits 0. No preview remains running at verification completion. No clean installation, provider call, deployment or push occurred.

The baseline renderer rows remain: inheritance baseline, verdict, event, stationFocus, incidentFocus, inheritObservedRun, inheritSeparation, inheritLaterSelection, inheritStaleLater, outcomeBlocker and requirementVersion. They were not repaired or waived by this work. The original status-first load flake remains historically flaky even though the new serial clean runs pass; its cause is still [unknown].

## Scoped architecture cleanup

The production changes stay in story projection, existing help text and layout. Guidance still does not authorize commands. The new fallback helper is called by `runAll`; the story module remains imported by app and projection and is in the asset inventory. Removed the obsolete full-attempt-array return from the private comparison helper after verifying all four callers. No fixture, vendor, lockfile, CI or renderer change; no file deletion. Historical checkpoints remain evidence, with current state linked from the two status documents.

## Limits

Manual visual sign-off of fallback and status layout remains the user's check. The 1024x768 Bellwether fallback has a previously measured customer-bubble overlap with Your service of about 10px; this is outside the required 1280x720 cell. No new human-comprehension, native assistive-technology, clean-install or exact-browser-version evidence is claimed. Synthetic scenarios are not real customers, revenue or learning outcomes.
