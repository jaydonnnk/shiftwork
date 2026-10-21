**S37 review fixes verified locally, 2026-10-22.** The user approved the two Gate 3 section 13.5 corrections, F3 to F6, F7 instrumentation, F8's runner reorder, the separate guard repairs, commits and merging both branches into main. All requested guards now fail on their own named assertions and pass restored checks. Node 228, fullscreen faults 27/27, S31 34/34, complete browser controls 27/27 and separate browser controls 26/26 pass. Full regression retains the same eleven renderer failure strings and the known `port_dead` failure. See the [review-fix record](s37-review-fixes-2026-10-22.md) for all receipts, old check text and limits. Manual fallback/status visual sign-off remains open. Push and S38 have no go-ahead.

**S37 ACCEPTED, 2026-10-21.** The user answered "Yep i accept slice 37 please merge the other branch to main(if theres nothing else left to do), and push to main". The user's acceptance covers the owner-line and picker copy listed in the S37 checkpoint.

S36 was published, merged to main as `d43dad1..4727c82` and pushed; S37 started on `shiftwork/slice-37` under the same answer.
Gate 3 section 13.5 rule 2 was backtracked the same day: on the fresh demo the starter's own finished operation run sent a first-time visitor to step 7.
The user chose to limit rule 2 to a `LEARNER_CHOICE` selection and RE-APPROVED the revised rule in chat; the edit is recorded in [Gate 3 section 13](03-program-design.md#13-full-screen-workplace-revision-2026-10-21).
The user also confirmed three interpretations: the picker shows only with no board parameter and no station hash, rule 4 reads the comparison outcome status, and `view.slips` lands in S37 as data only.
The shift picker, step chip, next action, owner and customer bubbles, lamp tags and plain labels are built; every S37 check passes and each new guard fails under its own fault.
Evidence, the old text of every changed check (one of them unplanned), interpretations for review and known limits are in the [S37 checkpoint](s37-checkpoint-2026-10-21.md).
S37 is committed on `shiftwork/slice-37`, merged to main together with the `shiftwork/zoom-keyboard-settle` test-runner fix, and pushed.

**S36 ACCEPTED by the user, 2026-10-21.**

Asked "Is S36 accepted, or what should change?", the user answered "U make the call. Then publish the branch and merge to main and then start s37".
The dead `.panel-symbol` rule was deleted under that call.
The user authorized publishing `shiftwork/slice-36`, merging it to main and starting S37 on `shiftwork/slice-37`.
No co-author trailer; no install, download, deployment, credential or live call.

**Earlier, same day: S36 implemented locally.**

The user gave S36 its go-ahead on branch `shiftwork/slice-36` from main `d43dad1`.
The full-screen room, status bar, navy inspector and collapsed shift log are in place on all three boards.
Evidence, the user's six test-change decisions with old assertion text, the repaired defects and the pre-existing failures are in the [S36 checkpoint](s36-checkpoint-2026-10-21.md).
No install, download, deployment, credential or live call occurred.

**Gates 2 to 4 APPROVED by the user, 2026-10-21, in one batch.**

The user answered "Yes i approve gates 2 to four. Commit and push them to main and then let me see the build plan for the remaining slices again then we can start".
All four workplace-3d gates are now approved for the full-screen direction.
The user authorized committing these planning documents and pushing main, without a co-author trailer.
No slice has a go-ahead yet: S36 needs its own explicit start on branch `shiftwork/slice-36`.
No implementation, download, deployment, credential or live call is authorized by this approval.

**Earlier, same day: Gates 2 to 4 revision drafted.**

Drafted against the re-approved Gate 1, as the user asked:

- [Gate 2 section 11](02-architecture.md#11-revision-for-the-full-screen-workplace-2026-10-21): decisions R1 to R6 (full-screen room and inspector, perspective camera, three bounded motion classes, HTML narration and guidance, first-party rounded geometry and environment instead of new vendor files, focused dialogs). Everything else in Gate 2 is unchanged.
- [Gate 3 section 13](03-program-design.md#13-full-screen-workplace-revision-2026-10-21) and [visual-spec section 11](visual-spec.md#11-full-screen-workplace-revision-2026-10-21): files, signatures, call stacks, step-guide and lamp rules, replay eligibility, timings, revised budgets, 18 new and 2 extended fail-capable checks and the planned edits to existing S30 to S35 browser checks.
- [Gate 4 section 8](04-slices.md#8-full-screen-workplace-slices-s36-to-s42): S36 to S42. S36 to S38 are committed for the 2026-10-30 10:00 PT deadline (01:00 on 2026-10-31, Asia/Singapore) with a planning cutoff at the end of 2026-10-28, Asia/Singapore; S39 to S41 are stretch; S42 is not expected in time.

User decisions on the open questions, 2026-10-21, by questionnaire: all three boards get the full-screen shell in S36; the seven owner lines are OK as drafted; the budgets are provisional and S38 measures them first; the Stonebridge picker question is reworded to "What is going wrong?" (mockup screen 10 updated).

Verification: document review and source inspection only; `git diff --check` passes; no em dash or section sign was added.
Nothing was run, rendered or measured for the new direction; performance fit, existing-check breakage and art quality remain [unknown].
The engine-export claim in Gate 3 section 13.3 rests on a text search of the vendored modules, not execution.
No implementation, slice branch, test change, commit, push, download, deployment, credential or live call occurred.

**Gate 1 RE-APPROVED by the user, 2026-10-21. Gates 2 to 4 reconciliation in progress.**

After reviewing the revised [Gate 1 product](01-product.md) and [mockups/v2](mockups/v2/index.html), the user answered "Yep i approve, lets move on to gate 3 and gate 4. Then il approve all ar once".
Gate 1 is RE-APPROVED with the full-screen workplace direction.
The user asked for Gate 3 and Gate 4 to be revised next and intends to approve them together.
Gate 2 must also be checked against the revised Gate 1; any affected Gate 2 decision is presented in the same batch, never assumed approved.
Until that batch approval, the 2026-10-19 Gate 3 visual specification and Gate 4 plan are superseded drafts, not authority for new work.
No implementation, slice branch, commit, push, deployment, credential or live call is authorized.

**Earlier, same day: Gate 1 BACKTRACKED by the user, 2026-10-21; revision then in progress.**

Gate 1 Product is set back to IN PROGRESS.
The user reviewed the [visual overhaul proposal](visual-overhaul-proposal-2026-10-21.md) and answered "Yes i approve the backtrack".
That authorizes revising this folder's Gate 1 product document and its HTML mockups only.
The backtrack targets the presentation direction: the persistent-workbench layout A, the ban on recorded request-flow replays, ambient room life and narrated client voices, and the plain-language naming of the learner's steps.
The learning loop, evidence boundaries, learner authorship, explicit selection, operation and inheritance contracts are unchanged.
Gates 2 and 3 remain approved as historical decisions, but the visual specification and motion limits owned by Gate 3, and any Gate 2 asset or layout boundary the revised Gate 1 affects, must be reconciled and re-approved after Gate 1 re-approval.
No new slice is planned or authorized.
S36 and later need Gate 4 approval and their own go-ahead.
No implementation, commit, push, deployment, credential, live call or protected-fixture edit is authorized by this backtrack.
S29 to S35 remain accepted as implemented under the earlier direction.

Revised deliverables, 2026-10-21: the rewritten [Gate 1 product](01-product.md) and seven new screens plus a hub in [mockups/v2](mockups/v2/index.html).
The screens use the existing original `shiftwork/client/room.svg` as a stand-in for the 3D room; no third-party art or code was imported.
Verification, local Chromium in the Claude browser pane served from a loopback static server: all eight pages at forced iframe widths of 390, 640, 1280 and 1440 px (32 cells) had `scrollWidth` equal to `clientWidth`, no floating, modal, picker or hub element past the right edge, and a loaded room picture.
That check detected an injected 600px element at 390 px, so it can fail.
Desktop views at 1440x900 and narrow views at 390x844 were inspected by screenshot; defects found and fixed during review were mispositioned station tags, cause-suggesting placeholder text, a primary-styled default candidate, a ring disagreeing with the next action, a clipped tag, overlapping narrow tags, an art gap and modal text bleed-through.
Not checked: native Safari, physical devices, assistive technology and any reviewer comprehension.

**S35 ACCEPTED by the user, 2026-10-21, with one recorded evidence gap.**

The user approved S35 after their own manual testing and directed closure. The
harness has no qualifying native 200% receipt: all 413 visible observer records
are `dirty: false`, none is 378x413 CSS pixels, and the final manual attempt ran
full-screen at 125% zoom. The native 200% effect is therefore accepted on the
user's manual test, not passed by the harness. Chrome cannot reproduce the 378px
overflow under the pre-repair selector. The accepted source passes the four-cell
exact-viewport matrix, the nine-cell picker matrix, the fail-capable declaration
and zoom-fault controls, 206 Node, 152 source, 35 served, nine asset and six
environment checks, and a 1454-pass regression with the known `port_dead`
failure. A final archive with all three extracted journeys, rooms and 16-asset
closure is recorded in
`/tmp/shiftwork-s35-postcss-20261020-3/archive-accepted.json`. Exact Chrome .84
and clean locked installation remain unproved. Installation, demo publication,
deployment, credentials and live calls remain unauthorized. The work is merged
to main as `cd532d6..9e221bf` and pushed on 2026-10-21; the slice branch is
pushed as well.

**S35 second continuation: local verification, still INCOMPLETE, unaccepted and unpublished.**

Actual Northline content reach now passes 48 keyboard/touch/zoom/graphics cases.
Freeze completion restores Diagnostic availability, and operational history
excludes experiment runs while retaining legacy operations. Fresh evidence includes
35 served controls, 152 source controls, 206 Node checks, all nine failure
workbenches, full lifecycle and all three complete extracted journeys/rooms with
external assets blocked. The full regression retains the known port_dead failure,
1454 passes and one skip. Native Safari, exact Chrome .84 and separately authorized
clean locked installation remain unproved. Both recorded performance tiers, drawing cap and panel latency pass. Native foreground verification is continuing after the user answered Ready.
No installation, publication, deployment, credentials, live call or protected-fixture
edit occurred. No requirement was waived. The latest S35 checkpoint/handoff
sections and `/tmp/shiftwork-s35-continuation-20261020-2` supersede earlier next steps.

**S35 local continuation; INCOMPLETE, unaccepted and unpublished, 2026-10-20.**

The user's "Please proceed" resumed local S35 work on `shiftwork/slice-35` from
`cd532d6`. Absent-run crashes and non-boolean synthetic admission are repaired
with fresh RED-to-GREEN proof. Evidence now includes 206 Node checks, 152 isolated
source controls, nine asset checks, the full existing Northline journey, actual
WebGL room picks and exact panel-focus/zoom checks. Visible permission-map and
handover limits have browser failure/repair evidence. Actual selected-content
reach, served renderer mutations, lifecycle, performance, later/history and
extracted delivery remain incomplete. The full non-packaging regression has
1454 passes, the retained `port_dead` failure, one skip and two warnings. Clean locked installation remains required
and separately unauthorized. No acceptance, commit, publication, deployment,
credential, live call or protected-fixture edit. Work stopped near the 175k
context limit; owned previews are stopped. See [S35 checkpoint](s35-checkpoint-2026-10-20.md) for current receipts,
failed attempts and precise limits. Older S35 notices are historical.

**S34 ACCEPTED on local evidence and published on main, 2026-10-20.**

S34 was implemented on `shiftwork/slice-34` from `80f8818`. The user accepted
it with "Okay yea i accept it please commit the changes and push to main" and
authorized the S34 commits and publication to main. The inherited work is preserved. Both handoff findings and the review's rapid-arrival identity
finding have browser RED-to-GREEN repairs. The exact synthetic signal/owner
marker travels; failed refresh clears ownership text; overlapping arrivals
settle without borrowing another signal's motion. Fresh proof includes 118 Node
checks, 107 source faults, 14 new served-source fault controls, nine retained
routing controls, partial-label cleanup, four retry modes, exact Chromium layouts
and 30 switches. Both Stonebridge graphics tiers and startup/activation budgets
pass. Three complete extracted browser journeys, both extracted real rooms and
an extracted graphics-failure workbench pass with external assets blocked.
Native Safari shows the final room after reload, exact 200% page zoom, keyboard
navigation, panel focus/reach and recorded-clock/unsent-handoff wording. The
native functional viewport is not numerically recorded; no new exact 378x413,
device, audible-AT or Safari-performance claim follows. Nine asset checks pass.
The full non-packaging suite remains 1454 passed, the known `port_dead` failure,
one skip and two warnings. No code-review or cleanup finding remains open.
S34 is accepted on this bounded evidence. Six focused commits `80f8818..88cf0f6`
were fast-forwarded to main and pushed. Live `git ls-remote` and zero left/right
divergence verified publication. This documentation receipt records that result.
S35 implementation requires its own go-ahead; the requested prompt is not that
authorization.
See the [S34 checkpoint](s34-checkpoint-2026-10-20.md) for receipts and retained limits.

**S33 ACCEPTED on local evidence and published on main, 2026-10-20.**

The user answered "Start S33 now" on 2026-10-20, authorizing local
implementation, fail-capable tests and disposable evidence on
`shiftwork/slice-33` under `/tmp/shiftwork-s33-*`. The Bellwether room now
includes the owner desk, read-only incident review tray and handover shelf. The
handover shelf shows the original selection, rationale, requirement hashes,
declared limits and unresolved incidents. Historical inspection has an explicit
return to current, ordinary polling leaves it unchanged, and the later-condition
experiment is bound to the original selected and retained versions and its
observed operation. A newer save, a new shift and browser-cache return do not
promote a newer version. The full offline inheritance walkthrough passed with
`prior_bytes_identical: true`; the S33 later control preserved `sel-0002`,
`ver-0003` and `ver-0004` through history, the later test and a new shift. Fresh
evidence: 101 Node checks, 93 of 93 source faults with production unchanged, 4
of 4 render-fault rows including the inheritance baseline, the full S33 controls,
the full S30 diagnosis journey, the blocked-comparison baseline, composition,
30-switch lifecycle, exact 640 and 390 viewports at 100% and 200% zoom, nine
asset checks, both performance tiers within budget and the full non-packaging
suite at 1454 passed with the known port_dead failure, one skip and two
warnings. The [S33 checkpoint](s33-checkpoint-2026-10-20.md) records the receipts
and limits. S33 is accepted on local evidence, committed on
`shiftwork/slice-33` as `6500175..259ace9`, fast-forwarded to main and pushed as
`6500175..259ace9`. No deployment, credentials, provider call, protected fixture
change or S34 work followed.

**S32 ACCEPTED on local evidence and published on main, 2026-10-20.**

The S32 handoff prompt authorized local implementation, tests and disposable
evidence on `shiftwork/slice-32` from main `b7dff05`, under
`/tmp/shiftwork-s32-*`. The consequence wall now distinguishes pending, failed,
incomplete and linked operation states; the selected evidence bridge labels
source and meaning; one new linked synthetic event produces at most one 320ms
trace; and the host keeps continuity across reset, conflict and remount. Fresh
evidence: 95 Node checks, 89 of 89 source faults with production unchanged, 7 of
7 S32 fresh-preview controls, 8 of 8 S32 browser fault rows with clean, fault and
restored phases, 30 of 30 existing S30/S31 controls, nine asset checks, three
board journeys plus plain and selection-journey bookshop variants, both
performance tiers within budget, and the full non-packaging suite at 1454 passed
with the known port_dead failure, one skip and two warnings. The
[S32 checkpoint](s32-checkpoint-2026-10-20.md) carries receipts and limits. The
user accepted S32 with "Okay yea i accept it please commit the changes and push
to main" and authorized the working-tree commits and the push to main. The work
is committed on `shiftwork/slice-32` as `b7dff05..13c5526`, fast-forwarded to
main and pushed as `b7dff05..13c5526`. S33 subsequently received its own go-ahead
and local implementation; see the current S33 notice above. No deployment
follows.

**S31 ACCEPTED on local evidence, 2026-10-20 Asia/Singapore.**

The user answered "Start S31" on 2026-10-20, authorizing local implementation,
tests and disposable evidence on `shiftwork/slice-31` from main `f4e794e`, then
accepted S31 with "Yep accepted" and authorized the working-tree commits, the
approved cleanup deletions and the push to main. The
equal A/B stands, exact frozen versions and shared conditions, blocker and
missing-slot evidence, explicit eligible A/B choice, selection-bound plate and
publication ownership guards are implemented locally. Fresh checks: 78 Node,
65 of 65 source faults with production unchanged, 30 of 30 fresh-preview
browser controls, nine asset checks, three board journeys plus a passing
selection-demo journey, both performance tiers within budget, and the full
non-packaging suite at 1454 passed with the known port_dead failure, one skip
and two warnings. The [S31 checkpoint](s31-checkpoint-2026-10-20.md) carries
receipts, limits and the unclaimed targets. S31 is committed on `shiftwork/slice-31` as `dc73a5b..e4f6e20`,
fast-forwarded to main and pushed as `f4e794e..e4f6e20`. S32 requires its own
go-ahead.

**S30 ACCEPTED on local evidence, 2026-10-20 Asia/Singapore.**

The user answered "Start S30 (Recommended)" on 2026-10-20. The branch
`shiftwork/slice-30` was created from `272321c`. The user then accepted S30 with
"Yep i accept and do the cleanup and hen commit the working tree and push to
main if u havent already", authorizing the two cleanup findings, focused commits
and publication to main. The failed request, prediction and falsifier entry,
diagnosis desk, reported diagnostic states, non-qualifying guards, expanded
editing and 160ms polling continuity are implemented locally. Fresh checks:
61 Node, 53 of 53 source faults with production unchanged, 21 of 21
fresh-preview browser controls, nine asset checks, three existing board journeys
and the full non-packaging suite at 1454 passed with the one known port_dead
failure, one skip and two warnings. Both performance tiers met their budgets. The
[S30 checkpoint](s30-checkpoint-2026-10-20.md) carries receipts, limits and the
unclaimed targets. S30 is committed on `shiftwork/slice-30` as
`2a322bd..1662b81`, fast-forwarded to main and pushed as `272321c..1662b81`.
S30 is accepted and published; S31 has since received its own go-ahead and
is implemented locally, as recorded above.

**S29 ACCEPTED under the narrowed scope, 2026-10-19 Asia/Singapore.**

The user explicitly approved the narrowed Gate 3 and Gate 4 scope, reviewed the
acceptance package, and accepted S29. All narrowed required checks have
receipts. S29 is published on main as 25e3d14..7d6d68f. S30 remains blocked until its
own go-ahead. The known port_dead failure, the headless/emulated evidence limits
and every deferred target stay documented and unclaimed.

**Gate 3 and Gate 4 narrowed scope APPROVED, 2026-10-19 Asia/Singapore.**

The user selected the narrowed-contract path after the exact-viewport Chromium
evidence closed the Chromium half of the narrow-layout bullet, then explicitly
approved the revised text. Gate 3 section 9 and its Gate 4 section 5 copy now
define a Mac-only evidence scope: headless Chromium 155 on macOS 26.5.1 at exact
1280x720, 640x900 and 390x844 viewports, plus the recorded native Safari 26.5
observations. Windows and Edge, Firefox, previous-stable Safari, physical
iPhone/Pixel, minimum Intel hardware, audible VoiceOver/NVDA and comprehension
sessions are deferred and unclaimed. The README records the reduced claims. All
narrowed required checks have receipts; S29 was accepted and published on
2026-10-19. S30 remains gated separately.

**S29 exact narrow-viewport Chromium evidence recorded, 2026-10-19 Asia/Singapore.**

The Chromium half of the exact 640x900 and 390x844 narrow-layout bullet now
passes at 100% and 200% zoom with keyboard, touch, 44 CSS-pixel targets, dirty
editor continuity and three clean/fault/restored CSS omission controls. The
change is additive test code; no production byte changed. The WebKit half,
previous-stable browsers, native Safari/mobile/Windows hardware, audible AT and
comprehension evidence remain unmet, and the known port_dead failure remains.
S29 stays INCOMPLETE and unaccepted. The latest [S29 checkpoint](s29-checkpoint-2026-10-19.md)
section carries receipts and limits. No S30 or publication followed.

**S29 native Safari continuation recorded, 2026-10-19 Asia/Singapore.**

Native Safari exposed and verified repairs for narrow picker overflow and a
24px select target. Only production styles.css and its manifest digest changed.
Fresh checks: 50 Node, two native picker controls, three Chromium CSS controls,
16 packaging checks and all three existing browser journeys. The full suite
retains its one known port_dead failure. S29 remains INCOMPLETE and unaccepted.
The user restricted this continuation to this Mac; the approved matrix was not
relaxed. The latest S29 checkpoint and handoff carry receipts and the S29 to S35
sequence. No S30 or publication followed.

**S29 local continuation verified, 2026-10-19 Asia/Singapore.**

Local Bellwether 200% zoom, focus/retry and partial-initialization controls now
have passing receipts. Fresh results: 50 Node checks, 42 source controls, 27
browser controls, 16 packaging checks and all three complete browser journeys.
The full offline suite retains its one known port_dead failure. Required native
browser/device/audible-screen-reader and comprehension evidence remains unmet.
S29 stays INCOMPLETE and unaccepted. The latest local-continuation section in
[S29 checkpoint](s29-checkpoint-2026-10-19.md) supersedes older pending-local-check notices below.
No S30, publication, deployment, credentials, provider or protected-fixture work.

**S29 continuation checkpoint, 2026-10-19 Asia/Singapore.**

Actual page-cache focus loss is repaired and fail-capable. Fresh checks pass:
47 Node, nine assets, 39 source controls and eight isolated browser controls.
Explicit/cached-module retry has bounded local proof. Zoom is incomplete and
full regressions after the focus fix remain pending, along with the native
browser/device/audible-screen-reader matrix. S29 stays incomplete and unaccepted.
[S29 checkpoint](s29-checkpoint-2026-10-19.md) records exact receipts and limits. New work stopped near
the 175k context boundary. Existing approvals persist; no S30 or publication.
Earlier notices retain their historical scope.

**Execution halted at the context boundary, 2026-10-19 Asia/Singapore.**

The runtime session log reported approximately 414k tokens of context, beyond
AGENTS.md's 175k limit. This was discovered late; no budget extension was given.
New work stopped. S29 remains incomplete. The checkpoint and fresh-session
handoff record completed local evidence, pending checks and unchanged approvals.

**S29 local room implemented; acceptance INCOMPLETE. 2026-10-19 Asia/Singapore.**

The authorized branch and pinned local engine are in place. The Bellwether
WebGL2 inspection path, complete fallback, recorded failure and empty state work
locally. [S29 evidence and remaining checks](s29-checkpoint-2026-10-19.md) record
the fresh tests, rejected attempts, review repairs and preserved evidence limits.
Required browser/device/AT, zoom and remaining isolated lifecycle controls are
unproved. S29 is unaccepted and uncommitted. S30 and publication remain excluded.
Earlier preflight-only and pending-prerequisite notices are historical.

**S29 prerequisites APPROVED, 2026-10-19 Asia/Singapore.**

The user replied "approve" to the four concrete S29 prerequisites: create
and switch to `shiftwork/slice-29`, acquire and verify pinned Three.js
`0.180.0`, install existing locked dependencies in disposable environments,
and write disposable local preview/test artifacts under `/tmp/shiftwork-s29-*`.
S29 implementation may proceed on its branch. Earlier pending-prerequisite
notices below are historical. S30, Git publication, deployment, credentials,
provider calls and protected-fixture authoring remain unauthorized.

**Current authority: Gate 4 APPROVED; S29 go-ahead recorded. 2026-10-19 Asia/Singapore.**

The execution handoff records the user's instruction, "Okay start slice 29."
This approves the presented [Gate 4 sequence](04-slices.md) and authorizes S29
implementation only. Do not ask for either approval again. S29 implementation
has not started because the separately gated prerequisites remain pending.
S30 to S35 still require their own go-aheads.

Fresh preflight on macOS:

- Branch is `main`. HEAD, origin/main and remote main are
  `25e3d14b5a3ec0c09dcb2edd9f25af906783614f`.
  Remote S28 remains `1a943d946bc402f586677cf8bfc2bf60ffce5428`.
  No local or remote `shiftwork/slice-29` branch was found. The index is empty.
- The same six inherited planning-document changes are preserved, including
  the untracked approved `04-slices.md`. Only current notices are added here.
  Production modules, vendor files and proposed workplace tests remain absent.
- Existing project Python is `.venv/bin/python`, version 3.13.12.
  Its `shiftwork` import resolves to this checkout. pytest, FastAPI, uvicorn
  and httpx are discoverable. Node is `/Users/jayd0/.local/bin/node`,
  version 24.21.0. The existing `tests/client/env.mjs` resolves this interpreter
  and the installed Chrome executable.
- Installed-app metadata reports macOS 26.5.1 arm64, Chrome 155.0.8059.84 and
  Safari 26.5. Edge and Firefox were not found in standard application locations.
  This is availability inspection, not browser, WebGL2 or physical-device proof.
- Read the scoped packet and source-inspected all nine HTML studies, starting
  with the review hub and colour study. No new layout or focus evidence is claimed.
  The earlier flaky focus probe remains attached.
- No product preview, product test suite, test database, browser profile,
  engine acquisition, installation, provider call or S29 runtime baseline ran.

One bounded prerequisite request remains, under Gate 4 section 1:

1. Create and switch to `shiftwork/slice-29` from the verified current HEAD,
   preserving all inherited planning changes. No implementation on main.
2. Acquire only the pinned `three@0.180.0` tarball from the Gate 3 source.
   Review current advisories and syntax first, verify the recorded SHA-512,
   and retain only the two approved modules and LICENSE with actual file hashes.
3. Install the existing `requirements.lock` in disposable environments for S29
   clean-install packaging proof. No lockfile change or new runtime/browser tool.
4. Write S29 disposable local preview databases, source extractions/copies,
   test receipts, screenshots and browser profiles beneath uniquely owned
   `/tmp/shiftwork-s29-*` directories. Use recorded executors and existing
   public material. Apply faults only to served in-memory bytes or disposable
   copies. Do not modify existing user databases or protected fixtures.

These four actions are proposed, not approved or performed. The slice go-ahead
does not waive section 1's separate permissions. Physical-device and named
assistive-technology access remain unestablished and cannot be counted as passes.
S29 stays incomplete until its required exit checks pass. Do not begin S30.
No commits, merges, pushes, tags, deployment, credentials, provider calls,
protected-fixture authoring, purchases or participant outreach are authorized.

The checkpoint below is preserved byte-for-byte. Its DRAFT, awaiting-approval,
NOT AUTHORIZED and planning-only labels describe the earlier Gate 4 checkpoint.
This current notice supersedes those labels without changing the approved
contracts or historical evidence. S28 acceptance and all carried limits remain.

# Status: Shiftwork 3D workplace after S28

Updated: 2026-10-19, Asia/Singapore.

- Gate 1 Product: APPROVED 2026-10-19. Persistent-workbench layout A.
  BACKTRACKED 2026-10-21, then RE-APPROVED 2026-10-21 with the full-screen workplace direction.
- Gate 2 Architecture: APPROVED 2026-10-19. Self-hosted Three.js presentation.
- Gate 3 Program Design: APPROVED 2026-10-19, including the visual specification.
- Gate 4 Vertical Slice Plan: DRAFT 2026-10-19, awaiting approval. Proposed S29 to S35.
- Implementation: NOT AUTHORIZED. No post-S28 slice has been approved or started.

## Authorization and preserved baseline

The user requested a build plan based on the agentic-factory design study and
explicitly selected "Plan toward a 3D workplace" on 2026-10-19. This authorizes
planning and Gate 1 HTML mockups. The user then said "Srue lets move to gate 2
now", approving the presented Gate 1 proposal and directing Gate 2 planning.
The approved default is layout A, the room beside a persistent workbench.
The user then said "Sure i approve" to the presented Gate 2 architecture and
requested a copy-paste handoff. Three.js and the architecture boundaries are now
approved. That earlier session recorded approval and transferred context. The
subsequent request authorized Gate 3 planning only. Jaydon then said "seems good.
I approve." and authorized committing Gates 1 to 3 in focused batches and pushing
main. That publication request is completed. The current request authorizes
Gate 4 planning documents only. The [slice plan](04-slices.md) is drafted and
awaiting approval. Earlier stop-after-publication statements retain their
historical scope. No further Git publication, dependency acquisition,
implementation or deployment is authorized.

S28 remains complete and accepted. Its existing evidence and limits are preserved.
The approved baseline plan ends at S28. This folder owns the proposed extension,
without renumbering historical slices. Gate 4 proposes S29 to S35 after checking
current numbering and dependencies. None is approved for implementation.

Original Gate 1 entry: `shiftwork/slice-28`, `1a943d9`, clean.
Gate 4 entry: `main`, `25e3d14b5a3ec0c09dcb2edd9f25af906783614f`, clean;
equal to origin/main and remote main on a fresh read. Remote S28 remains
`1a943d946bc402f586677cf8bfc2bf60ffce5428`. No branch was created.
The root [status](../00-status.md) remains the project-wide authority.

The Gate 1 scope is presentation and interaction, not a new curriculum or new
agent autonomy. The three boards, learner authorship, protected assessment,
comparison, explicit selection, operation, inheritance and evidence boundaries
remain constraints. A later gate must identify and obtain approval for any
necessary change to an existing contract.

## Current deliverables

- [Product proposal](01-product.md).
- [Approved architecture](02-architecture.md).
- [Approved Gate 3 program design](03-program-design.md).
- [Draft Gate 4 slice plan](04-slices.md), awaiting approval.
- [Visual specification](visual-spec.md) and
  [static colour/composition study](mockups/08-visual-spec.html). These make
  the planned appearance concrete; they are not final artwork or working 3D.
- [Session handoff](handoff-2026-10-19.md), including remaining work and an
  optional separate review prompt.
- [HTML review hub](mockups/00-review.html), with two layout options and seven
  screen previews. All are standalone, static storyboards.
- Builder-check and browser evidence are recorded below.

The original eight mockups are grayscale structure studies. The ninth is an
approved colour/composition study. They show arrangement, appearance and state
distinctions, not final 3D art, working execution or performance proof. No
third-party code or artwork was imported.

## Planning sequence

1. Gate 1 is approved, including its scope, proposed success targets and the
   room-plus-workbench layout. Formative targets remain unmeasured.
2. Gate 2 is approved: local Three.js modules, a scene-only public-state view,
   the existing backend and workbench, explicit fallbacks and local delivery.
3. Gate 3 is approved with exact files, interfaces, publication sites, board
   mappings, release/asset records, motion, lifecycle, performance budgets and
   fail-capable check designs. Implementation and proof remain future work.
4. Gate 4 is drafted: inspect in real 3D, diagnose/test, compare/select, operate,
   inherit, then Stonebridge and Northline. Each proposed slice includes its
   visible outcome, proof and stop boundary. S33's complete Bellwether checkpoint
   precedes other-room expansion. Approval and slice go-aheads remain separate.

Do not treat this sequence as an approved slice plan. Gate 3 proposes a fixed
r180 engine release, not acquisition or a measured compatibility result. No
delivery date or effort estimate is promised. Seven slices are proposed for review.

## Carried evidence and known limits

- The preceding read-only design study inspected reference revision `607e77b`,
  its screenshots and Shiftwork's hosted first screen. It did not execute the
  reference application or benchmark its motion.
- That study measured the hosted 1280 by 720 layout: columns 926px and 354px.
  The hosting notice occupied the first grid cell, the room the second, and the
  workbench began at y=875px. This is retained prior-turn browser evidence,
  supported by the current source structure, not a fresh hosted observation here.
- S28's known `port_dead` failure, historical Northline 390px reach issue,
  frozen GTM comparison limit, shared ephemeral hosting and unknown actual costs
  remain carried. Planning does not repair or reclassify them.
- Existing source reading shows one-second active-run polling and a limited
  evidence-arrival animation. The current room is not wholly static.
- The earlier planning-only request did not authorize learner sessions, provider
  calls, credentials, installs, product runtime actions or publication. The later
  Git authorization above changes publication scope only; deployment is excluded.

## Review and verification

Completed 2026-10-19 for the proposal and mockups only:

- A fresh builder-check reviewer read the product, status and eight mockups.
  Verdict: "nothing important left". The reviewer found no conflict with learner
  authorship, explicit selection, separate operation or inherited history.
  This is a text/design review, not an independent runtime or correctness oracle.
- Eight mockups pass static checks for one main heading, unique identifiers,
  local navigation targets, illustrative labels and no active scripts, external
  assets or service calls. New planning documents contain no em dashes.
- In the in-app browser, every mockup was laid out at actual viewport widths
  1280px, 640px and 390px. All 24 page/width observations had matching document
  width and viewport width, a full-width hosting notice and no horizontal overflow.
  Neither comparison radio choice was preselected in the checked comparison views.
- Desktop screenshots of layout A and B and a mobile screenshot of Northline's
  selected work were inspected. At 390px, activating the Northline Acceptance
  anchor placed the workbench at y=16px and keyboard focus on `workbench`.
  This proves the static mockup anchor, not a repair to production Northline.
- The first generator invocation used an unsupported optional pathlib argument
  and stopped before writing a mockup. The first desktop preview also exposed a
  paragraph width cap on the notice. Both attempts were rejected, corrected and
  logged in `MISTAKES.md`; the accepted width observations above followed repair.
- Four baseline authority documents received only prefixed planning notices.
  Their prior bytes were preserved exactly. Production files, tests, dependencies,
  reviewed content and historical evidence were not edited. `git diff --check`
  passes. No product test suite was run for this documentation/mockup change.

Local preview: `http://127.0.0.1:8883/00-review.html`.
The standalone HTML hub also opens directly from disk with working relative links.
Browser viewport overrides were reset after inspection.

Not proved: final 3D appearance, frame rate, resource use, scene failure recovery,
runtime state mapping, full keyboard/touch journeys, learner comprehension or
learning gain. Those require the relevant later design, implementation and evidence.

## Gate 2 source and design review

Completed 2026-10-19 for the architecture proposal only:

- Traced the current client state, generation/intent guards, polling,
  navigation/focus, public schemas, evidence linkage and static asset delivery.
  Confirmed that latest-run completion is not sufficient operational evidence,
  and that the multi-read refresh is not an atomic server snapshot.
- Checked primary Three.js installation, WebGLRenderer, resource disposal and
  license documentation. The local module graph and release pin still require
  Gate 3 specification and authorized acquisition; no vendor bytes were fetched
  into the project or installed.
- A bounded architecture reviewer identified one ambiguity: routine refresh
  clearing could reset every animation baseline. Section 5 now separates loading
  from actual lost continuity and keeps one prior accepted presentation reference
  for diffing without giving stale state command authority. The reviewer rechecked
  that amendment and the current project status: resolved, with no substantive
  issue remaining in the bounded review. This is source/design review only.
- Gate 1 approval and layout A are recorded in the scoped product and status
  and in current notices in the project authority records. Earlier baseline bytes
  remain preserved. Local document links, no-em-dash checks and
  `git diff --check` pass. Gates 3 and 4 have not been written.
- Production, tests, dependencies and Gate 1 mockups are unchanged in this gate.
  No product suite, WebGL run, resource benchmark, model/Sandbox call, install,
  Git publication or deployment was performed. Runtime and learning claims remain
  unproved.

## Gate 3 design review and static verification before approval

Completed 2026-10-19 for the proposal and static colour study only:

- Wrote `03-program-design.md`, `visual-spec.md` and the original standalone
  `mockups/08-visual-spec.html`. Mapped the complete Bellwether story first,
  with distinct signal/ownership and permission/booking/handover rooms.
- Checked current client assignments, public schema fields, event projections,
  station aliases and packaging code. Selected r180/0.180.0 in the proposal.
  Read upstream release/source/license and npm metadata. The registry integrity
  is recorded; vendor bytes, per-file hashes and extracted closure are absent.
- The brainstorming skill's fresh builder check found three material design
  gaps: a static optional-host import could block startup, ledger status was
  absent from the input signature, and RAF ownership lacked an interface.
  Repaired all three and clarified literal-URL retry. The reviewer rechecked
  them as resolved with "nothing important left" in the bounded design review.
  This is a second design reading, not runtime certification.
- `/tmp/shiftwork-gate3-doc-check.py` passes for all nine HTML studies and new
  document links. It checks unique IDs, one h1, local targets and no script or
  external assets. Four isolated synthetic faults fail the validator. No new
  em dashes or Gate 4 file exist. `git diff --check` passes.
- The new colour study was inspected in the in-app browser at actual widths
  1280, 640 and 390px. Document width matched viewport width, hosting disclosure
  spanned the viewport, and labelled station targets were at least 44px high.
  The 1280px room/workbench widths were 700.43px and 507.56px. This is layout
  evidence for the static study, not production or WebGL proof.
- One focus probe was flaky. Separate 390px anchor observations showed
  focus on `selected-work` at y=15.98px. One batched resize/click/immediate-read
  probe showed no target focus and y=942.98px. A later accessibility-observed
  check passed on unchanged source. This timing-sensitive automation result is
  not clean reliable focus proof. Both receipts remain in
  `/tmp/shiftwork-gate3-browser.json` and
  `/tmp/shiftwork-gate3-settled-focus.json`; the mixed result is logged in
  `MISTAKES.md`. Production keyboard/touch proof remains future work.
- A rejected documentation patch repeated the absent-anchor mistake and changed
  no files. The corrected patch used verified text; the incident is logged.
- Eighteen inherited files were checked for exact-byte preservation as unchanged
  content, an original suffix beneath notices, or an original prefix before
  appended mistake entries. The eight approved grayscale studies and approved
  scoped product/architecture remain exact. Older handoff and authority bytes
  remain beneath explicit current notices.
- At draft verification, branch was `shiftwork/slice-28`, HEAD `1a943d9`. Product
  source, tests, dependencies and AGENTS.md were unchanged. No implementation,
  acquisition, product startup, provider call, install, commit, push or deployment
  occurred in that drafting session.
  No product suite, physical-device, screen-reader or graphics benchmark ran.

Static preview used `http://127.0.0.1:8891/mockups/08-visual-spec.html` only.
The temporary server is stopped after verification; the HTML remains usable
directly from disk. Final 3D appearance, nested acquired import closure, runtime
fallback/disposal, performance and learner comprehension remain unproved.

## Gates 1 to 3 approval and publication: 2026-10-19

Jaydon approved Gate 3 with "seems good. I approve." and separately requested
batch commits and a main push for Gates 1 to 3, then a report. Gates 1 and 2
retain their earlier approvals. This publication does not begin Gate 4.

Switched the existing checkout from `shiftwork/slice-28` to the equal local
`main` at `1a943d9`. Created six focused commits, with explicit file lists and
no co-author footers:

- `dafc66e`: approved product and core decision screens, five files.
- `7323e8d`: operation and board-specific structure studies, four files.
- `1f5041a`: approved Three.js architecture and historical handoff, two files.
- `b139365`: approved program design and visual treatment, three files.
- `6f4ae62`: product/architecture authority mirrors, four files.
- `f9f5589`: gate approvals, bounded evidence and planning incidents, four files.

The 22-file planning packet was pushed to main. Live `git ls-remote` verified
remote main at `f9f558928912314f3824b7ea25c9b55cf11c8b63`, equal to local
main and origin/main, with left/right counts `0 0` and a clean working tree.
Remote `shiftwork/slice-28` remained at
`1a943d946bc402f586677cf8bfc2bf60ffce5428`. This receipt is a separate follow-up
to that verified publication checkpoint, not a claim that its own commit was
already present in that earlier remote read.

Fresh document checks passed for nine HTML studies and scoped links, with four
isolated validator faults rejected. Approval state, absence of Gate 4 and
`git diff --check` passed. Committed bytes matched the reviewed packet. No
credential-pattern match was found in the packet. Product source, tests,
dependencies and AGENTS.md remain unchanged from `1a943d9`.

The earlier flaky focus probe and all S28/runtime/graphics evidence limits remain
attached. No product suite, new rendering proof, dependency acquisition, provider
call, implementation or deployment was performed for publication. Stop after
the receipt push and final remote verification.

## Gate 4 planning review and document verification: 2026-10-19

The current planning-only request produced `04-slices.md`, proposing S29 to S35.
The sequence follows visible learner decisions, tests import/failure risks in
the tracer and requires the complete Bellwether journey before other-room art.
Self-review traced all 20 named Gate 3 check designs to slice owners and kept
separate functional, visual, accessibility, packaging, physical-performance and
comprehension evidence. No concrete earlier-gate error was found requiring a
backtrack. This is planning review, not runtime proof or Gate 4 approval.

- Re-read the scoped packet, current slice numbering, relevant client/packaging
  contracts and planning mistakes. Inspected all nine HTML studies, starting
  with the review hub and colour study, through source and desktop browser views.
  This did not rerun or upgrade the earlier 640/390px or flaky focus observations.
- Static document checks passed for seven complete slice-contract entries,
  all 20 named check-design references, local links and the nine HTML studies.
  Four isolated in-memory validator faults were rejected: extra h1, missing local
  target, external script and duplicate ID. These test the document validator,
  not any future production guard.
- Approved scoped Gates 1 to 3, visual-spec and all nine HTML files remain exact.
  Root authority records and handoff retain their prior bytes beneath new notices;
  existing scoped evidence sections are preserved. Only six planning documents
  changed. Product code, tests, dependencies, protected fixtures, AGENTS.md and
  MISTAKES.md are unchanged. Whitespace and `git diff --check` checks passed.
- No product suite, product startup, graphics test, acquisition, install,
  provider call, credential use, branch, commit, push or deployment occurred.
  All carried S28 and graphics/access/device/comprehension limits remain.

Static preview used `http://127.0.0.1:8892/mockups/00-review.html` and the other
eight existing studies. The temporary server and browser tab are closed.
This is a safe planning boundary for a fresh session; resume from the Gate 4
draft and this status, not the historical publication or Gate 2 handoff prompts.

## Stop boundary

Gates 1 to 3 are approved. Gate 4 is drafted and awaiting approval. The current
request authorizes planning documents only, then presentation of the proposed
sequence. No implementation slice has started. Dependency acquisition, installs,
branches, protected-fixture authoring, provider calls, credentials, commits,
pushes and deployment remain outside scope. Stop for Gate 4 review. Approval
does not itself authorize S29; each slice needs its own implementation go-ahead.
