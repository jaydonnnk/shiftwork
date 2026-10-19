# Status: Shiftwork 3D workplace after S28

Updated: 2026-10-19, Asia/Singapore.

- Gate 1 Product: APPROVED 2026-10-19. Persistent-workbench layout A.
- Gate 2 Architecture: APPROVED 2026-10-19. Self-hosted Three.js presentation.
- Gate 3 Program Design: APPROVED 2026-10-19, including the visual specification.
- Gate 4 Vertical Slice Plan: PENDING, unwritten. Not requested in this turn.
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
main. That later authorization covers Git publication of this planning packet.
Dependency acquisition, implementation and deployment remain unauthorized.
Gate 4 is not requested or authorized by this publication instruction.

S28 remains complete and accepted. Its existing evidence and limits are preserved.
The approved plan ends at S28. This folder owns the proposed extension, without
renumbering historical slices. The first new implementation slice would follow
S28, but its number, scope and exit contract belong to the later Gate 4 decision.

Entry checkout: `shiftwork/slice-28`, `1a943d9`, clean. No branch was created.
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
4. At Gate 4, plan end-to-end slices after S28. Each slice must have a visible
   outcome, evidence and its own implementation go-ahead. Establish one complete
   Bellwether journey before extending the treatment to the other boards.

Do not treat this sequence as an approved slice plan. Gate 3 proposes a fixed
r180 engine release, not acquisition or a measured compatibility result. No
delivery date, effort estimate or implementation slice count is promised.

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

## Stop boundary

Gates 1 to 3 are approved. The current instruction authorizes focused commits
and a main push of this planning packet, then reporting the result. Gate 4
remains unwritten and no post-S28 implementation slice is assigned or authorized.
Dependency acquisition, implementation and deployment remain outside scope.
Stop after Git publication and verification.
