# S35 implementation plan

Goal: inspect Northline permissions, acceptance, pilot records and handover in a
distinct workshop, with the existing HTML workbench and all three local rooms.

Architecture: extend the existing engine-free projection, room definitions,
scene and host. Keep one controller and editor. Scene picks navigate only.
Use HTML, CSS, vanilla JavaScript and the installed local Three.js r180.

Authority: the user said "Please proceed with s35 thanks" on 2026-10-20.
Work is local on `shiftwork/slice-35`, from `cd532d6`. Commits, publication,
deployment, installs, credentials, live calls and protected fixtures remain
excluded. Disposable receipts use `/tmp/shiftwork-s35-*`.

Spec: `04-slices.md` S35 and sections 3/5; `visual-spec.md` section 8;
`03-program-design.md` sections 4 through 10. Approved gates are not reopened.

## Constraints and review focus

- Keep saved, selected and executed versions separate, including later tests.
- Booking, rollout, escalation and followup require synthetic operation records
  and exact available run/check/output/ordinal links. Historical records settle
  quietly with their recorded identities. Missing evidence never means pass.
- Handover is a recorded administrative declaration, not receipt or acceptance.
- A permission map describes the selected declaration and cannot grant access.
- No change to backend, fixtures, lockfiles, CI or the retained S27/S28 archives.
- Test stale callbacks, incomplete links, false approval, later experiments,
  refresh errors and partial initialization. No implementation-only assertions.
- All nine graphics faults retain editing, evidence, a valid offline action,
  focus and caret. Thirty switches exercise three actual rooms and one context.
- Use the exact Chromium viewport/zoom matrix and both performance tiers. Native
  Safari observations remain separate. Deferred hardware/AT targets stay unclaimed.
- A newly produced source archive must be below 35,000,000 bytes. Clean locked
  installation remains a required separately authorized check.

## Tasks

- [x] Establish baseline with the existing Node checks and fresh Northline journey.
- [ ] Add failing projection/host/room tests in `workplace_view.test.mjs` for
  each Northline event, experiment exclusion, exact links, canonical station
  transitions, historical preservation and original workshop geometry.
- [ ] Extend `workplace-view.js` with event-specific admission and canonical
  Northline transition targets. Run tests and independently fault each guard.
- [ ] Author Northline counter, separated map lanes, integration bench, bicycle,
  independent check fixture, slot rail and runbook shelf in `workplace-rooms.js`.
  Extend `workplace-scene.js` with recorded markers and quiet declarations.
- [ ] Admit Northline in `workplace-host.js`; extend `app.js`, `index.html` and
  `styles.css` only for necessary captions, status and selected-content reach.
- [ ] Add served-source browser controls for each new rendering/label/cleanup
  guard, requiring named assertions in clean/fault/restored phases.
- [ ] Extend `northline_browser.mjs` for later-alternative/history separation;
  run all three complete journeys on fresh disposable worlds.
- [ ] Extend shared browser/performance helpers narrowly for Northline and S35
  receipt paths. Prove exact layouts, focus/content reach, picks, retry, partial
  initialization, nine failure workbenches and 30 real-room switches.
- [ ] Measure both Northline graphics tiers with the full approved recipe.
- [ ] Update provenance hashes, README delivery notes and packaging checks.
  Create a new archive; verify closure, three extracted journeys and actual
  rooms with external hosts blocked, plus a graphics-failure workbench.
- [ ] Run relevant full regressions and `git diff --check`; retain known-red
  results and failed/flaky attempts. Review the final diff with a fresh reviewer
  and apply in-scope repairs. Scan for stale/redundant files without deletion.
- [ ] Record verified evidence and outstanding checks in scoped/root status
  and a checkpoint. Present the result and request the required install authority
  only after its archive and exact command are reviewable. No S36 is assigned.

Checks follow RED, minimal implementation, GREEN and isolated mutation proof.
The plan is executed in this session under the existing S35 go-ahead. No extra
plan approval or Git publication is inferred.

Checkpoint: local source and focused rendering checks are implemented; all
unchecked tasks remain acceptance obligations. See the S35 checkpoint.

## Continuation evidence, 2026-10-20

The local continuation reproduced and fixed the null-run and synthetic-type
issues in Northline and GTM. Fresh evidence is 206 Node checks, 152 isolated
source controls, nine asset checks, the full existing Northline journey, real
room picks and exact panel-focus/zoom checks. Permission and handover wording
have browser RED-to-GREEN checks. Actual selected-content reach, served marker
mutations and lifecycle/performance executions remain pending. See the latest
section of the S35 checkpoint. The unchecked task list is not waived.

## User-requested handoff

The latest stop sections in the checkpoint/handoff are current. The final native select CSS repair and its updated zoom-fault anchor are saved, but final native 200% cases and post-repair archive validation remain unfinished. All owned previews are stopped. No requirement is waived.

## Post-repair layout and fault verification, 2026-10-20

Receipts are `/tmp/shiftwork-s35-postcss-20261020-3`. The official four-cell
exact-viewport matrix and a disposable nine-cell three-board picker matrix pass,
including 378x413 and 195x422. The official `zoom-omit-picker` control fails its
intended assertion. Fresh results are 206 Node, 152 source, 35 served, nine asset
and six environment checks, plus 1454 regression passes with the known `port_dead`
failure. Chrome did not reproduce the native 378px overflow under the exact
pre-repair selector, so the native 200% proof remains required. Product CSS was
restored byte-identically. Open: native 200%, CSS-repair review, archive rebuild.
No requirement is waived at that checkpoint.

## S35 acceptance, 2026-10-21

The user approved S35 after their own manual testing and directed closure. The
harness still has no qualifying native 200% receipt: no visible record is
378x413 CSS pixels and all 413 visible records are `dirty: false`. That effect is
accepted on the user's manual test, not passed by the harness. The accepted
archive size and SHA-256 are in `archive-accepted.json`. The work is merged to
main as `cd532d6..9e221bf` and pushed on 2026-10-21; the slice branch is pushed.
Installation, demo publication, deployment, credentials and live calls remain
excluded.
