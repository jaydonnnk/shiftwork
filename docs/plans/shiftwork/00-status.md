# Status: Shiftwork

- Gate 1 — Product: APPROVED 2026-09-15
- Gate 2 — Architecture: APPROVED 2026-09-15
- Gate 3 — Program Design: pending
- Gate 4 — Slice plan: pending

## Slices

No slices approved or implemented. Define the checklist at Gate 4.

## Notes for a fresh session

- 2026-09-15: user explicitly scrapped Hatchery as active scope and selected
  Shiftwork for software-factory planning. Hatchery remains historical evidence
  and a mechanism donor; do not resume it without an explicit user instruction.
- At project selection, authorization covered Gate 1 creation and review only; it
  did not itself approve Gate 1, architecture, implementation, credential use,
  deployment or outreach.
- 2026-09-15 Gate 1 review: automated artifact checks pass (six screens, links,
  labels, no scripts or external resources, CSS breakpoint). Two credibility concerns
  were found and revised: the decision screens felt quiz-like (preselected contract,
  strawman repairs) and the away shift only renamed the domain. Screens 02/04/06 now
  show competing tradeoffs and new question families. Manual learner tests: not run.
- 2026-09-15 user decisions: the 20-point transfer target is retained as an unproven
  north star — no impact claim until a sufficiently powered study; sample size and
  feasibility decided at Gate 3. Chosen path: revise the artifacts, then run the
  5-person manual tests if recruitment is feasible (user-run; project outreach stays
  unauthorized). At that point, Gate 1 approval was expected to follow the results
  or an explicit user decision to skip them.
- 2026-09-15 (later): user chose to automate the kit with deployed agents instead of
  running the 5-person kit. The human kit (`gate1-manual-test-kit.md`) therefore
  REMAINS UNRUN and every participant threshold in it is unmet; nothing may be
  recorded as human evidence. A labelled agent review of the original grayscale
  mockups found quiz-like decisions, no visible learner artifact/action, maker-facing
  language, guarded return intent, an ambiguous away-shift task and one 3 px overflow.
  Those findings drove the later copy and layout revisions. The separate simulated
  review file and its 12 pre-redesign screenshots are not retained because they cover
  a superseded UI; this summary is historical rationale, not current or human evidence.
- 2026-09-15 UI steering: the user did not approve Gate 1 and said the UI "kinda
  sucks." The six mockups were redesigned as a coloured service workbench. The
  learner-owned artifact is now visible on every screen; screen 02 contains usable
  contract inputs and a visible-check authoring area; screen 03 links an exact sample
  output to an external comparison and synthetic ledger event; screen 04 shows the
  repair workspace; screen 05 keeps the unseen case sealed; screen 06 removes
  study-design language and replaces the disputed compatibility row with a genuinely
  different state-changing, retry-safe booking problem. This material revision
  invalidated the earlier render evidence. The agent findings summarized above remain
  historical rationale for the redesign, not validation of the revised screens.
- 2026-09-15 post-redesign verification: served the current six mockups locally on
  port 8792 and inspected them in a real in-app browser. All six had no document
  overflow at 1280, 640 or 390 px; the active journey step remains visible at every
  tested width after changing the narrow/tablet navigation to a two-row grid. Screen
  02 radio, select, text and visible-check inputs were operated successfully. Screen
  03 keyboard focus traversed the six journey links and both actions in logical order,
  each with a visible 3 px focus outline. Representative desktop/mobile screenshots
  were inspected live for screens 01–06; console returned no warnings or errors.
  Static checks found six screens, no missing links, no scripts, no external URLs and
  none of the flagged study-design phrases. `git diff --check` passed except expected
  LF-to-CRLF notices. Browser controls did not change zoom, so 200% zoom remains NOT
  verified. No human test or simulated-persona rerun occurred; every human threshold
  remains unmet. No saved screenshot is retained as evidence of the current UI.
- 2026-09-15: user explicitly approved Gate 1 after reviewing the redesigned UI.
  Approval rests on the product document, six current HTML mockups, the user's review,
  applied review fixes and post-redesign browser checks; the human kit remains unrun
  and every human threshold remains unmet. The user requested one final independent
  review. If it finds no concrete Gate 1 blocker, Gate 2 may be set to `in progress`
  and drafted. If it finds a product-level blocker, apply the software-factory
  backtracking rule instead. This authorizes Gate 2 drafting only—not Gate 2 approval,
  implementation, installs, credentials, deployment, purchases or outreach.
- 2026-09-15 final independent review: **PASS — GATE 1 FINAL REVIEW**. Checkout verified
  on branch `shiftwork/gate-2-architecture` (`git merge-base --is-ancestor main HEAD`
  passed, worktree clean); `docs/adr/` does not exist. Checks performed: (1) document/
  screen consistency between `01-product.md` and screens 01–06; (2) static scans — no
  scripts, external URLs, inline `src`, `url()` in CSS, or preselected radio/checkboxes,
  all 42 local hrefs resolve, all `for`/`id` pairs match; (3) live browser matrix of all
  six screens at 1280/640/390 px (18 combinations) with no horizontal overflow, active
  journey step visible and correct media-query branch in each; (4) all six journey links
  clicked through to the correct screen and active step; (5) keyboard/control check —
  logical tab order, visible 3 px `#f0bd4f` focus outline, radios/selects/text input/
  checkbox all operable; (6) clean browser console; (7) visual screenshot inspection
  including narrow-width collapse of the screen 03 trace; (8) claim hygiene — ledger
  labelled synthetic, prototype/evidence disclaimers present, no real-outcome claims.
  Minor non-blocking findings recorded, not fixed (Gate 1 artifacts are approved):
  `wireframe.css:423-432` stretches the three `06-away-shift.html:71-73` checkboxes to
  full width (cosmetic; operable, labelled, keyboard-accessible); page `<title>`s
  contain "Gate 1"; screen 06's yellow strip and screen 04's "prior screen" line are
  static-mockup wording. `docs/plans/shiftwork/evidence/` is empty — no screenshot
  images exist on disk or in git history, so nothing was available to inspect; the
  pre-redesign screenshots were already recorded as not retained. Evidence limitations:
  the five-person manual kit remains UNRUN and every human threshold unmet — this
  review is agent/browser inspection, not human or learning evidence; literal 200%
  browser zoom was NOT verifiable (the in-app browser exposes no zoom control), so
  viewport-equivalent reflow at 640 px and 390 px was substituted; rendering was
  exercised in one Chromium engine (DPR 2) via same-origin iframes, with no second
  engine. Metadata alignment: `01-product.md:3` and `docs/SHIFTWORK_PLAN.md` lines
  6–8, 55–59 and 272 already match the recorded approval — no edit was required. Gate
  1 state is unchanged (APPROVED); Gate 2 was set to `in progress` and drafting began.
- 2026-09-15 Gate 2: `02-architecture.md` **drafted, not approved**. The draft covers
  the bookshop central loop only: controller/sandbox split (controller owns all durable
  state; sandboxes are disposable), artifact versioning and restart restoration,
  evaluator/credential/sealed-case isolation, repeated-probing leakage controls,
  deterministic append-only hash-chained ledger with pure-reducer replay, bounded
  Nemotron assist roles with authorship preservation, the Tavily
  curation-only boundary, env var names only, observability, local dev path,
  verified/proposed/unverified claims with primary-source links, least-confident
  decisions, failure containment and rollback. Four ADR candidates are listed inside
  the document (sealed-evaluator isolation; deterministic ledger ownership and replay;
  artifact versioning and restoration; execution topology — promotable only after the
  bounded sandbox capability spike). **No ADR files were created** and `docs/adr/`
  does not exist.
- 2026-09-15 Gate 2 review and approval: the draft was independently reviewed this
  session for internal consistency, fit against `AGENTS.md` §8 evidence boundaries and
  the Gate 2 template, and five primary sources were re-fetched to spot-check the §16
  "Verified" claims (sandbox overview, Nemotron service page, `contree` CLI page,
  Serverless overview, inference quickstart) — all held. One correction was applied:
  §1 Fit now lists `shiftwork_vs_hatchery.md` among the top-level docs. Non-blocking
  notes carried to later gates: `HACKATHON_REQUIREMENTS.md` says "DevPods" but the live
  Nebius docs name it "Devlabs" (the architecture uses the correct current name; the
  requirements file is stale — do not edit it without authorization); the away-shift
  transfer (the north-star metric) has no per-engagement assist/check-family config yet
  (Gate 3); and the local-first design must still satisfy the hackathon's hosted-demo
  obligation (Gate 4). The user then explicitly **APPROVED Gate 2** on 2026-09-15.
  Gate 2 approval covers the architecture document only; it does not authorize Gate 3
  drafting, implementation, installs, credentials, ADR file creation, commits,
  deployment or outreach. Gate 3 has not started and no implementation exists.
- Read `../../../AGENTS.md`, `../../SHIFTWORK_PLAN.md`,
  `../../../HACKATHON_REQUIREMENTS.md` and every file in this folder before continuing.
- Apply `C:/Users/jayd0/.agents/skills/software-factory/SKILL.md`.
- Current product hypothesis: applied-AI-engineering education for people with
  basic coding knowledge. One bookshop engagement; later work inherits the learner's
  artifact, decisions, incidents and transparent synthetic business state.
- Central mechanic: real learner output -> independently authored check ->
  deterministic ledger update -> inherited next shift.
- Current Gate 1 artifacts: `01-product.md`, six plain HTML service-workbench mockups
  with `wireframe.css`, and `gate1-manual-test-kit.md` (prepared, never run).
- Retained Hatchery mechanisms: versioning, branchable practice, sealed and
  regression cases, correction-to-unseen-case transfer, factual-versus-procedural
  separation, useful-first scaffolding and immutable evaluator boundaries.
- Preserve the authority split: learner owns important decisions; Nemotron may
  scaffold or diagnose but cannot own sealed cases, credentials, scoring or promotion.
- Preserve adjudication warnings: KodeKloud overlap; synthetic consequences are not
  real impact; public Sandbox ingress remains unknown; hidden cases can leak through
  probing; Nemotron architectural dependence is unproven; employer proof is excluded.
- Three justification tests remain unapproved future proof slices: central mechanism,
  reduced-assistance transfer against a strong static tutorial, and Tavily ablation.
- No API keys are required during Gate 1. Actual Token Factory, Nemotron and Tavily
  access remain unverified.
- Conditional scores only: current 27/40, pre-evidence cap 31/40, best case 35/40.
  No capability, learning benefit, prize merit or score has been demonstrated.
- Protect unrelated dirty-worktree changes. No installs, commits, pushes, purchases
  or participant outreach are authorized by Gate 1.

## Approval history

- Gate 1 — Product: approved by the user on 2026-09-15 after the service-workbench
  redesign. The final independent review remains a requested safeguard, not human
  evidence and not Gate 2 approval.
- Gate 1 — Product: final independent review completed 2026-09-15 with verdict
  **PASS — GATE 1 FINAL REVIEW**. No backtrack. Gate 1 remains APPROVED; Gate 2
  drafting authorized and started.
- Gate 2 — Architecture: approved by the user on 2026-09-15 after an independent
  review of `02-architecture.md` (internal consistency, `AGENTS.md` §8 boundaries,
  Gate 2 template fit) and a re-fetch of five primary sources confirming the §16
  "Verified" claims. One correction applied (§1 Fit enumeration). Approval covers the
  architecture document only; it does not authorize Gate 3, implementation, ADR file
  creation, installs, credentials, commits, deployment or outreach.
