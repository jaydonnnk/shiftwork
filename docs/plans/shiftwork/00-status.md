# Status: Shiftwork

- Gate 1 — Product: APPROVED 2026-09-15
- Gate 2 — Architecture: APPROVED 2026-09-15
- Gate 3 — Program Design: APPROVED 2026-09-17 (re-approved a second time after the
  §2 packaging backtrack was revised with `pyproject.toml`, `requirements.lock`, the
  `demos/` tree, `tests/packaging/` and test 51; the earlier approvals and both
  backtracks remain the historical record — see Approval history).
- Gate 4 — Slice plan: APPROVED 2026-09-17 (after three 2026-09-17 review rounds —
  BLOCK, then REVISE — every accepted fix and all three consistency corrections are
  applied to `04-slices.md`; the reviewer reported no remaining blocking defect in
  the 17-slice sequence)

## Slices

Gate 4 APPROVED 2026-09-17. Build order (one slice at a time; after each slice:
demo evidence run and shown, slice checked off here, then "Continue to slice N+1,
or re-steer?"):

- [ ] Slice 1 — Tracer bullet: full lifecycle, all mocked (`python -m demos.lifecycle` + browser)
- [ ] Slice 2 — Thin real vertical path: artifact → request → sealed case → evaluator result → ledger event
- [ ] Slice 3 — Executor conformance (recorded + local_process), deepening Slice 2 execution
- [ ] Slice 4 — Contract-parameterized evaluator + first sealed family, deepening Slice 2 evaluation
- [ ] Slice 5 — Reducer + hash chain + idempotent finalization, hardening the Slice 2 ledger
- [ ] Slice 6 — Isolation and leakage hardening
- [ ] Slice 7 — Budget + rotation + incidents + repair
- [ ] Slice 8 — Close → inheritance + Test 1 offline pre-proof
- [ ] Slice 9 — Client: board + customer-shift screens (01, 03)
- [ ] Slice 10 — Client: contract + repair screens (02, 04)
- [ ] Slice 11 — Client: inherited + away screens (05, 06) + away config
- [ ] Slice 12 — Nemotron assist gateway (+ model-feedback evidence pack)
- [ ] Slice 13 — Token Factory capability spike (credential-gated)
- [ ] Slice 14 — Real tokenfactory adapter + full Test 1 verdict (depends on Slice 13)
- [ ] Slice 15 — Tavily curation + ablation (prize-conditional)
- [ ] Slice 16 — Submission packaging: test build + demo video
- [ ] Slice 17 — Hosted deployment (conditional: only if Option B selected at the Slice 13 exit)

No slice is implemented. Slice work proceeds only under `04-slices.md` §10 —
credentials, installs, spike runs, external services, deployment, outreach and
ADR #4 each remain separately authorized.

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
- 2026-09-15 Gate 3 (in progress): the user approved a drafting plan that decided the
  five open questions. (1) Stack confirmed concretized: Python 3.12+, FastAPI, SQLite
  via stdlib `sqlite3` + raw parameterized SQL (no ORM/Alembic), pydantic v2
  (`frozen=True`), pytest, plain-HTML/vanilla-JS static client; learner artifact is one
  loopback HTTP JSON service with a stdlib-only template. (2) Spike framing confirmed:
  the deterministic core is designed against a fake/local executor; the real sandbox
  adapter is a Gate 4 slice gated on the capability spike, which is specified but NOT
  run (credentials unauthorized). (3) Config numbers proposed as provisional defaults
  in `03-program-design.md` §7 for the user to challenge. (4) Original study verdict:
  no powered study before the 2026-10-30 deadline; no impact claim at submission.
  The original estimate and claim of a frozen protocol were corrected on 2026-09-16
  (see below and `03-program-design.md` §8). (5) ADRs #1–#3 created in `docs/adr/`
  (sealed-evaluator isolation; deterministic ledger ownership and replay; artifact
  versioning and restoration); ADR #4 (execution topology) remains deferred until spike
  evidence. Delivered: `03-program-design.md` (files, types & signatures, call stack, a
  39-test plan, config appendix, study decision, spike protocol, least-confident
  decisions) and the three ADR files. The Gate 3 document records two new tables
  (`engagement_config`, `rotation_draws`) and two endpoint additions (`POST
  /api/shifts/{id}/close`, `GET /api/engagements/{slug}/assist-events`) beyond
  architecture §3/§4. Also fixed the stale Gate 2 "draft, not approved" header in
  `02-architecture.md` and the stale gate-state lines in `docs/SHIFTWORK_PLAN.md`.
  Gate 3 is NOT approved; the user's explicit decision is pending. No implementation
  code, spike run, installs, credentials, commits or deployment occurred.
- 2026-09-16 Gate 3 review corrections (documentation only): user authorized applying
  fixes and reporting manual needs, not gate approval or implementation. Rotation now
  draws one fresh variant per family per attempt, atomically with the run; reservations
  survive failures/restarts. Six variants per bookshop family cover two three-attempt
  shifts; the bike co-op keeps three per family (27 proposed cases total). Refills need
  newly authored variants, never a reset of exposure history. Defined `ChainStatus`,
  five response projections and `SealedCase`; clarified fixed bookshop "May" copy,
  public-versus-sealed comparisons, decision records and unresolved-incident inheritance.
  Reconciled assist roles, deferral references and architecture §19's stale ADR note.
  The test plan now has 41 named specifications, including full-budget cross-shift
  holdouts and rendered synthetic labels; these are not implemented or passing tests.
  The prior review's study arithmetic was wrong: the two-independent-arm approximation
  is about 93 participants/arm (186 total), not 47. No impact claim at submission remains
  the plan; the comparison requirements are not a complete frozen study protocol.
  Removed the false temp-directory isolation claim: local execution is trusted-fixture-
  only. Restored gate backtracking for spike failures that invalidate approved decisions.
  Delta verification: `git diff --check` and inline Node assertions passed for document
  whitespace/fences, gate state, ADR status, defined API types, 41 unique numbered test
  specifications, nine reason-code mappings, rotation capacity (old inventory fails)
  and the corrected power arithmetic. A second bounded, read-only agent check found
  missing current request text and visible-check correlation in the new projections;
  both fields and their test assertions were added and the document checks rerun.
  This is static documentation verification, not runtime, security, rendering, human
  or learning evidence, and neither LLM review is an independent oracle. The earlier
  broad PASS subclaims are not a correctness certificate. Gate 3 remains NOT approved;
  Gate 4 has not started. Next manual step is review of the revised Gate 3 document
  and an explicit approval decision; credentials and participant work are not needed
  for this documentation pass. No build, install, spike, external service use, commit
  or push occurred. `AGENTS.md` retains an older gate-state snapshot; this status file
  records the later approvals, and no project instruction file was edited.
- 2026-09-16 Gate 3 adversarial follow-up (documentation only): the review returned
  **STILL NEEDS ATTENTION** with seven specification blockers. The user selected the
  recommended fixes with two refinements: contract catalogs are immutable/versioned and
  evaluated for consistency with learner choices (not a hidden correct stance); Tavily
  remains in scope with a pre-registered, falsifiable ablation. The revised design now
  derives customer text from validated structured output; hashes files + contract +
  catalog version together; defines safe draft/public API projections; uses a shared
  total assist cap (bookshop 6, away shift 2); records aggregate version-level assistance
  without proposal-to-version links while retaining the minimal accepted/rejected signal
  required by the approved authorship measure; makes shift close atomic/idempotent and
  hash-chained; freezes versioned contract option ids with free-text declared limits as
  a non-scored pressure valve; and specifies the Tavily corpus, selection rule and kill
  thresholds. The test plan now contains 49 named specifications. Public official-source
  pages were read to sanity-check the Tavily domain classes; no Tavily API, credentials,
  build, test, spike, deployment, implementation, commit or push occurred. **Gate 3 is
  still NOT approved** and Gate 4 has not started; explicit user approval remains next.
- 2026-09-16 Gate 3 approval: the user explicitly **APPROVED Gate 3** after the seven-blocker
  revision. The approving pass was a full in-session document review of `03-program-design.md`,
  `00-status.md` and `SHIFTWORK_PLAN.md` §9: every blocker has design text plus a named test
  specification that can fail against the pre-revision behavior — customer text derived from
  validated structure (test 42); file bytes + contract + catalog hash in the version
  fingerprint (tests 21/43); safe draft/public projections with no internal refs (20/41/45);
  one shared assist cap per shift (38/46); atomic idempotent close (33); immutable versioned
  catalogs with consistency-not-correctness and a non-scored free-text limit valve (14/22/43/44);
  pre-registered Tavily corpus and kill thresholds (48/49). Both user refinements to the
  earlier review advice were accepted: the minimal accepted/rejected patch signal stays with
  no proposal-to-version link (aggregate counts cannot answer the approved authorship
  question), and the Tavily bar is two cross-domain structural discoveries at 10-candidate /
  30-minute review caps. Verified this session: 49 sequential test specifications;
  `SHIFTWORK_PLAN.md` §9 matches §8.1; ADRs 0001–0003 exist; working tree is docs-only — no
  implementation, no commit. Limits: static document review only — not runtime, security,
  human or learning evidence; no LLM review is an independent oracle; the 12-event Tavily
  corpus is not assembled and no API call occurred. Gate 3 approval covers the program-design
  document only; it does not authorize Gate 4 drafting, implementation, installs, credentials,
  spike runs, commits, deployment or outreach. Gate 4 has not started. The `AGENTS.md` §3
  gate-state snapshot was updated the same day (explicit user instruction) to record Gates
  1–3 approved.
- 2026-09-16 Gate 4 (in progress): the user explicitly authorized **drafting** the
  Gate 4 vertical-slice plan (`04-slices.md`) and nothing more. Gate 4 approval,
  implementation, installs, credentials, spike runs, external services, commits,
  pushes, deployment and outreach each still need separate explicit authorization.
- 2026-09-16 Gate 4 draft + independent cross-check: `04-slices.md` drafted (16 slices,
  4 phases; Test 1 executable at Slice 8, conditional on the offline executor and re-run
  at Slice 14; documented disagreement with the literal "proof first" reading of
  SHIFTWORK_PLAN §12; Option A test-build demo baseline). The user-requested independent
  adversarial review returned **REVISE — GATE 4** with two blockers, both test-coverage
  bookkeeping: (B1) tests 9/10/18/23/44 and the prompt/assist arms of 16/17 were marked
  fully landed in slices where some specified clauses cannot yet execute; (B2) three
  test-41 clauses (nested sentinel injection, incident-view label, empty/error states)
  were orphaned. Revisions applied: partial-completion annotations with named completing
  slices (Slice 5 now also opens incidents per Gate 3 §5.5, resolving an internal
  contradiction; Slice 10 declares test 41 complete; Slice 12 re-runs 16/17
  non-vacuously), plus the review's non-blocking notes (Option A interpretation risk,
  Test 2 deliberately not sliced per Gate 3 §8, permanent-conditionality sentence in
  risk 1, checklist note in §2, keyboard traversal in the client browser matrix). No
  backtracking of Gates 1–3 was found necessary. Limits: both the draft and the review
  are static document work by LLMs — not runtime, security, human or learning evidence,
  and neither is an independent oracle. **Gate 4 remains NOT approved**; the user's
  explicit decision is pending. No implementation, installs, credentials, spike,
  external service, commit or push occurred.
- 2026-09-17 Gate 3 BACKTRACK (documentation only): a second, fully cold independent
  architect review of `04-slices.md` returned **BLOCK — BACKTRACK GATE 3** with seven
  findings. Adjudication (verified line-by-line against the sources): findings 1–2 are
  genuine Gate 3 defects — (1) test 33 said unresolved incidents "become inherited
  limits with `LIMIT_DECLARED` events", contradicting §5.8/`CloseShiftFacts`, which
  keep declared limits and incidents as separate inheritances; (2) Test 1's
  "credentials are reachable" kill condition had no named test — test 20 covers
  learner-visible payloads, not the executed artifact's environment, while
  architecture §7 requires learner execution without controller credentials.
  Findings 3–7 are Gate 4 revisions (incomplete clause repairs: test 18's prompt arm
  orphaned, test 43's ledger-resolution and test 44's evaluator-rule clauses claimed
  while those layers are mocked; Slice 8's "Test 1" label overclaims on offline
  adapters; Slice 2 does not match the literal software-factory "real happy path"
  rule; prose demo evidence lacks runnable entry points; the submission-compliance
  path lacks a hard no-go and Slice 16 omits YouTube/availability obligations).
  Applied now (Gate 3 only): test 33 revised; §5.8 clarified (`LIMIT_DECLARED`
  derives from declared limits only); new test 50
  `test_executor_env_exposes_no_controller_credentials` appended without renumbering
  1–49 (user decision). Gate 3 set to in progress here and mirrored in
  `SHIFTWORK_PLAN.md` and `AGENTS.md` §3. User decisions recorded: (A) Slice 2 will
  be restructured into a thin real vertical path (one artifact, request, sealed case,
  evaluator result, ledger event) with Slices 3–5 adding conformance, variants and
  hardening — this Gate 4 revision, and all other `04-slices.md` edits, are QUEUED
  and must not be applied until Gate 3 is explicitly re-approved. Limits: both
  reviews are static LLM document work — not runtime, security, human or learning
  evidence, and neither is an independent oracle. No implementation, installs,
  credentials, spike, external service, commit or push occurred. The QUEUED
  constraint is now satisfied — see the re-approval entry below.
- 2026-09-17 Gate 3 RE-APPROVED: the user reviewed the revised `03-program-design.md`
  and approved Gate 3 (re-approval of the backtracked document). The 2026-09-16
  approval and the 2026-09-17 backtrack both remain the historical record. This
  unblocks the queued Gate 4 revisions: decision A (restructure Slice 2 into a thin
  real vertical path — one artifact, one request, one sealed case, one evaluator
  result, one real ledger event — with conformance, variants and hardening pushed to
  Slices 3–5) and edits S4-2..S4-14, each with clause-level test re-mapping per the
  `MISTAKES.md` prevention rule. Those `04-slices.md` edits are now being applied;
  Gate 4 is still NOT approved and will be presented separately. Limits: both prior
  reviews are static LLM document work — not runtime, security, human or learning
  evidence, and neither is an independent oracle. Gate 3 approval does not authorize
  implementation, installs, credentials, spike runs, commits, deployment or outreach.
- 2026-09-17 Gate 4 §11 decisions (documentation only): the user answered all four open
  questions in `04-slices.md` §11. (1) `NEBIUS_API_KEY`: a bounded early availability
  smoke check (key valid, model reachable) is authorized to run once a key is provided,
  retiring the submission-critical access unknown early; the full live assist-gateway
  demonstration still lands at Slice 12, which builds against recorded responses until
  then. (2) Demo baseline: Option A (downloadable test build) confirmed as the committed
  plan of record; hosted Option B stays strictly optional, pursued only if the Slice 13
  spike verifies a Nebius service can host the app. (3) Config numbers: attempt_limit 3,
  bookshop rotation 6/family, assist budgets 6/2 accepted as starting values; still
  challengeable at Slices 2/7/11/12, but changes after inventory authoring are expensive
  (capacity invariant, Gate 3 §7.1). (4) Sealed-inventory authorship: the agent drafts
  all 27 cases + fixtures; the user reviews every case and expected answer before
  sealing — the agent's review is not evidence (not an independent oracle). Applied to
  `04-slices.md`: §11 rewritten as resolved decisions, with matching edits in the Slice
  2 authoring note, Slice 12 authorization, §8, §9 risk 1 and §10. **Gate 4 remains NOT
  approved**; user review and an explicit approval decision are next. No credential was
  used; no implementation, installs, spike run, external service, commit or push
  occurred. The `docs/SHIFTWORK_PLAN.md` and `AGENTS.md` §3 gate-state snapshots still
  describe the revisions as "being applied" and were left unedited pending user
  instruction.
- 2026-09-17 Devpost form fold (documentation only): at the user's instruction the
  live submission-form fields the user provided (35 MB file upload, model/Nemotron
  feedback questions, Tavily runtime-call qualification clause, the illustrative
  "GPU instance types" wording, Builders & Brews dropdown) were added to
  `HACKATHON_REQUIREMENTS.md` under "Submission form fields (live Devpost form)".
  The Tavily runtime-call clause conflicts with the approved offline curation-only
  boundary (architecture §11; Gate 3 test 39) — recording it is a factual fold, not
  a design change. No gate state changed; Gate 4 remains NOT approved. No
  implementation, installs, credentials, external service, commit or push occurred.
- 2026-09-17 Gate 4 review round 2 (BLOCK) + Gate 3 backtrack #2: an independent
  static review of the Gate 4 documents returned BLOCK with five blockers and three
  revisions — G4-01 (the "optional" Slices 13–14 Sandbox path is actually
  product-critical: offline adapters cannot execute learner-edited code), G4-02 (§2
  file map omits `pyproject.toml`, a dependency lock, `demos/` and the clean-env
  install check), G4-03 (test 9's capture-retention clause has no owning slice),
  G4-04 (Slice 14 overclaims a full isolation verdict without a hostile canary),
  G4-05 (model-feedback form answers have no evidence protocol), G4-06 (stale gate
  snapshots), G4-07 (Git-Bash-only demo commands), G4-08 (no deployment slice if
  hosting is chosen). The user accepted the fix list and decided the Tavily
  question: pursue the prize via the shipped operator-run curation CLI (Slice 15's
  live `discover()` call); no runtime-path change, no architecture §11 / test 39
  backtrack, no organizer clarification; the form is answered "yes" only after the
  call has actually shipped. Applied now (Gate 3 only): §2 gains `pyproject.toml`,
  `requirements.lock`, the `demos/` tree and `tests/packaging/`; §6 gains appended
  test 51 `test_clean_env_install_and_run` without renumbering 1–50; the tests
  preface notes test 51 re-runs at the packaging slice. Gate 3 set to in progress
  here and mirrored in `SHIFTWORK_PLAN.md` and `AGENTS.md` §3. All `04-slices.md`
  edits (G4-01/03/04/05/07/08 + the §11 Tavily decision) are QUEUED and must not be
  applied until Gate 3 is explicitly re-approved. Limits: this review is static LLM
  document work — not runtime, security, human or learning evidence, and not an
  independent oracle. No implementation, installs, credentials, spike, external
  service, commit or push occurred.
- 2026-09-17 Gate 3 RE-APPROVED (second time) + Gate 4 revision round 2 applied: the
  user reviewed the packaging revision of `03-program-design.md` (§2 file map now
  carries `pyproject.toml`, `requirements.lock`, the `demos/` tree and
  `tests/packaging/`; §6 test 51 appended) and approved Gate 3. That released the
  queued round-2 edits, all now applied to `04-slices.md`: G4-01 (Slices 13–14 on the
  mandatory packaging path; Slice 16 depends on Slices 1–14; sandbox no-go wording in
  §9/§10), G4-03 (test 9 capture-retention clause named and demonstrated at Slice 8),
  G4-04 (Slice 14 re-runs tests 16–18 against the real adapter plus a canary hostile
  artifact), G4-05 (Slice 12 model-feedback evidence pack written to
  `evidence/model-feedback.md`; Slice 16 assembles form answers from it), G4-06 (this
  entry; `SHIFTWORK_PLAN.md` and `AGENTS.md` §3 snapshots updated), G4-07 (`demos/`
  modules are the canonical shell-independent evidence path; PowerShell where HTTP is
  unavoidable) and G4-08 (conditional Slice 17 + §8 five-condition Option B exit
  gate). §11 decisions 5–6 recorded (Tavily via the shipped curation CLI's live
  `discover()` call; execution path submission-critical with a pre-authorized early
  sandbox entitlement/I-O smoke check). **Gate 4 remains NOT approved**; it is now
  presented for the user's review and the explicit software-factory approval
  question. Limits: every review and edit is static LLM document work — not runtime,
  security, human or learning evidence, and no LLM is an independent oracle. No
  credential was used; no implementation, installs, spike run, external service,
  commit or push occurred.
- 2026-09-17 Gate 4 review round 3 (user verdict REVISE — three consistency
  corrections; documentation only): (1) the provisional Python bound in
  `03-program-design.md` §2 was tightened from `>=3.11,<3.14` to `>=3.12,<3.14` to
  match the approved 3.12+ stack decision — test 51's clean-env install would
  otherwise create an unintended Python 3.11 support obligation; (2) the Gate 3
  header now records its second backtrack/re-approval (packaging, test 51) plus the
  bound correction — the record it previously omitted; (3) the
  `HACKATHON_REQUIREMENTS.md` Tavily checklist was made neutral (whether a shipped
  operator-run curation CLI's live `discover()` call satisfies "functional, runtime
  call ... as part of its solution" is an interpretation question) and now points to
  the decision of record (`04-slices.md` §11 decision 5). The reviewer reported no
  remaining blocking defect in the 17-slice sequence. Limits: static LLM document
  work — not runtime, security, human or learning evidence, and not an independent
  oracle. Gate 3 remains APPROVED (the bound correction is a user-directed
  consistency fix, recorded in the document header and Approval history). **Gate 4
  remains NOT approved**; the explicit approval decision is next. No credential was
  used; no implementation, installs, spike run, external service, commit or push
  occurred.
- 2026-09-17 Gate 4 APPROVED: the user explicitly approved Gate 4 after the round-3
  corrections. Recorded in the gate line above, the Slice checklist (now
  authoritative here, per `04-slices.md` §2) and Approval history; the
  `04-slices.md` header is marked APPROVED the same day. Approval authorizes
  building the 17 slices in order, one at a time, each ending with the demonstrated
  demo evidence, a check-off here and the "Continue to slice N+1, or re-steer?"
  pause — and nothing else: installs, credentials, external services, the Slice 13
  spike, the Slice 15 ablation, deployment, outreach and ADR #4 remain separately
  authorized (`04-slices.md` §10). Separately the same day, the user authorized
  documentation Git operations only: commit of the approved gate documents on this
  branch, publish of the branch and merge to main (no co-author trailers); that
  authorization covers documentation commits, not slice work. Limits: static
  document work — no implementation, installs, credentials, spike run, external
  service use, deployment or outreach occurred. Scores remain conditional forecasts.
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
- Gate 3 — Program Design: approved by the user on 2026-09-16 after the adversarial
  follow-up revision resolved all seven specification blockers and a full document review
  of the revised design found no blockers. Approval covers `03-program-design.md` only;
  it does not authorize Gate 4 drafting, implementation, installs, credentials, spike
  runs, commits, deployment or outreach.
- Gate 3 — Program Design: BACKTRACKED to in progress on 2026-09-17 after a cold
  independent review found two concrete Gate 3 defects (test 33 close-semantics
  ambiguity; no test for Test 1's credential-reachability kill condition). Revisions
  applied the same day (revised test 33, clarified §5.8, appended test 50). The
  2026-09-16 approval above remains the historical record; explicit re-approval of
  the revised document is pending and must precede any Gate 4 revision or approval.
- Gate 3 — Program Design: RE-APPROVED by the user on 2026-09-17 after reviewing the
  revised `03-program-design.md`. This satisfies the precondition above and unblocks
  the queued Gate 4 revisions (decision A Slice 2 thin-real-path restructure plus
  edits S4-2..S4-14, with clause-level test re-mapping). Approval covers
  `03-program-design.md` only; it does not approve Gate 4, and does not authorize
  implementation, installs, credentials, spike runs, commits, deployment or outreach.
- Gate 3 — Program Design: BACKTRACKED a second time on 2026-09-17 after the Gate 4
  review round 2 found §2's file map omitted packaging (`pyproject.toml`, dependency
  lock, `demos/`, clean-env install test). Revisions applied the same day (§2 file
  map + §6 test 51); the earlier approvals and the first backtrack remain the
  historical record.
- Gate 3 — Program Design: RE-APPROVED a second time by the user on 2026-09-17 after
  reviewing the packaging revision. This released queued Gate 4 revision round 2
  (G4-01/03/04/05/07/08 fixes plus §11 decisions 5–6), now applied to
  `04-slices.md`. Approval covers `03-program-design.md` only; it does not approve
  Gate 4, and does not authorize implementation, installs, credentials, spike runs,
  commits, deployment or outreach.
- Gate 3 — Program Design: consistency correction (user-directed, 2026-09-17, during
  the Gate 4 review round 3) — the provisional Python bound in §2 was tightened from
  `>=3.11,<3.14` to `>=3.12,<3.14` (test 51 would otherwise carry an unintended
  Python 3.11 support obligation), and the document header now records the second
  backtrack/re-approval it had omitted. Approval state unchanged.
- Gate 4 — Vertical Slices: approved by the user on 2026-09-17 after three review
  rounds the same day (independent review BLOCK with G4-01–G4-08; fixes applied;
  follow-up REVISE with three consistency corrections; corrections applied; no
  remaining blocking defect found in the 17-slice sequence). Approval covers the
  17-slice build order in `04-slices.md` and authorizes slice work one at a time
  under its §10; it does not authorize installs, dependencies, credentials,
  external services, spike runs, deployment, outreach or ADR #4.
