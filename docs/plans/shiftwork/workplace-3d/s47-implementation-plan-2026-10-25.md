# S47 implementation plan

Goal: an offline five-panel first-run mode with exact public technical values
collapsed, while every existing command and all three workbenches still work.
Spec: s47-gate1-2026-10-25.md, re-approved by the user on 2026-10-25.
Execute inline in the S47 worktree. No publication or live authority.

## Design and files

Use existing HTML controls and handlers. Move their actual DOM nodes into the
active presentation groups and restore their original locations for Full
workbench. Do not clone inputs, copy command handlers or create workflow state.
Keep the existing seven-step guide; derive the recommended panel from it.
The browsed panel is local navigation only. A visible Guided first run button
and ?guide=1 enter the mode. Existing bookmarked workbench routes keep working.

- workplace-story.js: FIRST_RUN_PANELS and firstRunPanel(guide) map 1, 2/3,
  4, 5/6, 7 to the five approved groups. Unknown stays unknown.
- evidence.js: evidenceLabel(code), including unknown values without inference.
- app.js: presentation-only grouping, mode/navigation controls, exact technical
  text visibility, and the existing report opener. No new command/API path.
- index.html: labelled mode controls, guided heading/navigation and stable
  grouping anchors on existing sections. No duplicate controls or IDs.
- styles.css: guided layout, technical text visibility, keyboard and mobile access.
- workplace-assets.json: update only exact changed client digests.
- s45_owner_line.test.mjs: remove the obsolete branch-name prerequisite; preserve
  every fault, unique-anchor, named failure and source-preservation assertion.
- workplace_fullscreen.mjs: add only S47 to owned-root containment.
- first_run.test.mjs, first_run_browser.mjs: pure mapping/label tests and actual
  browser navigation, exact-value, outcome, geometry and keyboard checks.
- first_run_faults.mjs: independent pure and served faults with restored controls.
- first_run_journey.mjs: the recorded explicit choice, offline operation and
  inheritance demonstration. Preserve its completed receipts instead of rerunning it.
- first_run_preview.py: fresh S47-owned offline starter/comparison stores.
- first_run_regressions.mjs: review controls for dynamic station navigation,
  exact ordinary evidence prose and same-shift refresh continuity.

## Review focus

Unknown/conflicting state must not look completed. Visiting panel 5 must not
advance the guide. Choice and operation stay separate. Moving controls must
preserve unsaved text and their listeners. Public failures, missing evidence,
refusal/completion distinctions and unknown costs remain visible. A future mode
code must say evidence unknown and retain its exact public literal on reveal.
Provider reasoning stays separate, collapsed and text-only. Scene and station
controls remain usable in every mode and viewport.

## Tasks and checks

- [x] Record approval and establish fresh Node/Python baseline with install test
  explicitly deselected. Preserve the original 10 branch-name failures.
- [x] Write mapping/label tests, observe intended red assertions, then implement
  the pure functions. Test every mapping, unknown state and evidence code.
- [x] Write browser checks and observe missing first-run controls on the existing
  app. Add mode and grouping using actual existing DOM nodes. Check all five
  panels at 1440x900, 1280x720 and 390x844, including editor draft preservation,
  current recommendation versus browsing, full-workbench restoration, no request
  from navigation, visible outcomes and exact literal reveal.
- [x] Add independent served faults for each new guard, require its intended
  assertion, and require clean/restored controls. Keep source bytes unchanged
  across served faults. Self-test rendered-value absence scanners.
- [x] Run all three journeys, affected full-screen, room, replay and fault checks,
  S44/S45 browser/rate checks, full offline Python, Node and exact asset closure.
  Compare baseline failures, inspect representative screenshots, protect source
  material hashes and run git diff --check.
- [x] Record actual result and remaining limits, perform architect-reviewer
  cleanup without unauthorized deletion, and request explicit S47 acceptance.

No later slice, integration, install, provider call, protected fixture edit,
commit, push, merge or deployment is part of this plan. The combined S46/S47
result requires separate integration and its own verification.

## Final continuation, 2026-10-25

The user explicitly extended this continuation's context limit to 300k and asked
to finish S47 if possible. Existing gate and authority boundaries persist.
Fresh receipts: /tmp/shiftwork-s47-finish-20261025-a/.

1. Isolate the complete original focus opacity rule, retain the exact named
   assertion and complete the pending fullscreen controls selectively.
2. Reproduce the three fresh-review findings before changing production:
   dynamically created away-room stations, ordinary run-time prose and loading
   publications resetting the browsed panel. Keep each red receipt.
3. Repair only confirmed presentation defects, refresh the asset digest and prove
   each guard with a separate served fault and restored control.
4. Finish GTM/Northline faults, interrupted ambient checks, S44/S45 checks and
   final guided captures/controls with fresh owned stores, caches and profiles.
5. Inspect the actual images, finish cleanup review and preservation checks,
   record exact evidence and limits, then request explicit S47 acceptance.

The earlier primary-source and browser fault receipts remain preserved. A final
result must name which candidate bytes each carried receipt covers. No accepted
or stopped S45 store, primary checkout or S46 checkout may be started or edited.

## Halt checkpoint

Implementation exists but S47 is INCOMPLETE. The current fullscreen fallback is
red; the remaining checks above are not complete. The exact current state and
proof limits are in s47-checkpoint-2026-10-25.md. The user-approved scope persists.
The added first_run_preview.py and first_run_journey.mjs provide disposable setup
and explicit choice/operation/inheritance proof. GTM/Northline repeated-request
assertions were reconciled and their affected faults still need proof.

## Continuation evidence

The fallback regression is repaired and full clean fullscreen, room and source/browser fault checks pass. The fullscreen fault loop has a separate non-unique CSS mutation anchor. GTM faults are partial; Northline, replay, S44/S45, final guided proof and cleanup remain pending. See s47-resume-checkpoint-2026-10-25.md. The unfinished checklist is not a completion or acceptance claim.

## Offline verification complete

All implementation/check tasks above are verified. Explicit user acceptance remains pending. See [the final evidence](s47-final-offline-2026-10-25.md) for current versus carried source-byte limits, all rejected receipts, preservation and the stop boundary. The S44 browser readiness repair is test setup only and retains every rendering assertion.

## Review correction: final-byte proof complete

- [x] Fresh fullscreen: all 64 clean/fault/restored triples on pinned final bytes, with no carried rows.
- [x] Fresh affected-fullscreen: both triples on the same final bytes.
- [x] Fresh review-id-green: all eight triples on the same final bytes.
- [x] A fresh validator requires all acceptance proof sets to have zero changed client files.

The gap is closed by 222 fresh rows in /tmp/shiftwork-s47-finalbytes-20261025-a/.
All named faults and clean/restored controls pass. The validator rejects changed
client bytes for all eight acceptance sets and the three actual old stale
receipts. The fixed-port collision and early incomplete-packet validation remain
preserved separately. No product or test source changed in this verification
continuation. The user subsequently accepted S47, and its code packet is
published to the branch and main. See the final evidence and
[publication record](s47-publication-2026-10-25.md). S46 remains ongoing and separate.
