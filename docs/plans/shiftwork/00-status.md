# Status: Shiftwork

- Gate 1 — Product: APPROVED 2026-09-15
- Gate 2 — Architecture: APPROVED 2026-09-15
- Gate 3 — Program Design: APPROVED 2026-09-17 (re-approved a second time after the
  S2 packaging backtrack was revised with `pyproject.toml`, `requirements.lock`, the
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

- [x] Slice 1 — Tracer bullet: full lifecycle, all mocked (`python -m demos.lifecycle` + browser); implemented and demonstrated 2026-09-17 (evidence in Notes for a fresh session)
- [x] Slice 2 — Thin real vertical path: artifact → request → sealed case → evaluator result → ledger event; implemented and demonstrated 2026-09-18 (`python -m demos.thin_path`; evidence in Notes)
- [x] Slice 3: Executor conformance (recorded + local_process); implemented, demonstrated, reviewed (PASS) and merged to main 2026-09-18 (verbatim evidence below; test 50 partial, test 29 skipped)
- [x] Slice 4: Contract-parameterized evaluator + first sealed family; implemented and demonstrated 2026-09-18 (evidence below; the new sealed cases await the user's review)
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

Slices 1, 2 and 3 are implemented, reviewed and merged to main (2026-09-17 and
2026-09-18; Slice 3 published as commit `8df3d6b`, `--no-ff` merge `1f38220`);
Slice 4 is implemented and demonstrated on `shiftwork/slice-4` and awaits the
user's review of the new sealed cases (evidence below; the change set is
distinguishable from the reviewed Slice 3 baseline at commit `1e4e6c1` by
`git diff`); slices 5-17 are not implemented. Slice work proceeds only under
`04-slices.md` S10; credentials, installs, spike runs, external services,
deployment, outreach and ADR #4 each remain separately authorized.

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
  session for internal consistency, fit against `AGENTS.md` S8 evidence boundaries and
  the Gate 2 template, and five primary sources were re-fetched to spot-check the S16
  "Verified" claims (sandbox overview, Nemotron service page, `contree` CLI page,
  Serverless overview, inference quickstart) — all held. One correction was applied:
  S1 Fit now lists `shiftwork_vs_hatchery.md` among the top-level docs. Non-blocking
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
  in `03-program-design.md` S7 for the user to challenge. (4) Original study verdict:
  no powered study before the 2026-10-30 deadline; no impact claim at submission.
  The original estimate and claim of a frozen protocol were corrected on 2026-09-16
  (see below and `03-program-design.md` S8). (5) ADRs #1–#3 created in `docs/adr/`
  (sealed-evaluator isolation; deterministic ledger ownership and replay; artifact
  versioning and restoration); ADR #4 (execution topology) remains deferred until spike
  evidence. Delivered: `03-program-design.md` (files, types & signatures, call stack, a
  39-test plan, config appendix, study decision, spike protocol, least-confident
  decisions) and the three ADR files. The Gate 3 document records two new tables
  (`engagement_config`, `rotation_draws`) and two endpoint additions (`POST
  /api/shifts/{id}/close`, `GET /api/engagements/{slug}/assist-events`) beyond
  architecture S3/S4. Also fixed the stale Gate 2 "draft, not approved" header in
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
  Reconciled assist roles, deferral references and architecture S19's stale ADR note.
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
  `00-status.md` and `SHIFTWORK_PLAN.md` S9: every blocker has design text plus a named test
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
  `SHIFTWORK_PLAN.md` S9 matches S8.1; ADRs 0001–0003 exist; working tree is docs-only — no
  implementation, no commit. Limits: static document review only — not runtime, security,
  human or learning evidence; no LLM review is an independent oracle; the 12-event Tavily
  corpus is not assembled and no API call occurred. Gate 3 approval covers the program-design
  document only; it does not authorize Gate 4 drafting, implementation, installs, credentials,
  spike runs, commits, deployment or outreach. Gate 4 has not started. The `AGENTS.md` S3
  gate-state snapshot was updated the same day (explicit user instruction) to record Gates
  1–3 approved.
- 2026-09-16 Gate 4 (in progress): the user explicitly authorized **drafting** the
  Gate 4 vertical-slice plan (`04-slices.md`) and nothing more. Gate 4 approval,
  implementation, installs, credentials, spike runs, external services, commits,
  pushes, deployment and outreach each still need separate explicit authorization.
- 2026-09-16 Gate 4 draft + independent cross-check: `04-slices.md` drafted (16 slices,
  4 phases; Test 1 executable at Slice 8, conditional on the offline executor and re-run
  at Slice 14; documented disagreement with the literal "proof first" reading of
  SHIFTWORK_PLAN S12; Option A test-build demo baseline). The user-requested independent
  adversarial review returned **REVISE — GATE 4** with two blockers, both test-coverage
  bookkeeping: (B1) tests 9/10/18/23/44 and the prompt/assist arms of 16/17 were marked
  fully landed in slices where some specified clauses cannot yet execute; (B2) three
  test-41 clauses (nested sentinel injection, incident-view label, empty/error states)
  were orphaned. Revisions applied: partial-completion annotations with named completing
  slices (Slice 5 now also opens incidents per Gate 3 S5.5, resolving an internal
  contradiction; Slice 10 declares test 41 complete; Slice 12 re-runs 16/17
  non-vacuously), plus the review's non-blocking notes (Option A interpretation risk,
  Test 2 deliberately not sliced per Gate 3 S8, permanent-conditionality sentence in
  risk 1, checklist note in S2, keyboard traversal in the client browser matrix). No
  backtracking of Gates 1–3 was found necessary. Limits: both the draft and the review
  are static document work by LLMs — not runtime, security, human or learning evidence,
  and neither is an independent oracle. **Gate 4 remains NOT approved**; the user's
  explicit decision is pending. No implementation, installs, credentials, spike,
  external service, commit or push occurred.
- 2026-09-17 Gate 3 BACKTRACK (documentation only): a second, fully cold independent
  architect review of `04-slices.md` returned **BLOCK — BACKTRACK GATE 3** with seven
  findings. Adjudication (verified line-by-line against the sources): findings 1–2 are
  genuine Gate 3 defects — (1) test 33 said unresolved incidents "become inherited
  limits with `LIMIT_DECLARED` events", contradicting S5.8/`CloseShiftFacts`, which
  keep declared limits and incidents as separate inheritances; (2) Test 1's
  "credentials are reachable" kill condition had no named test — test 20 covers
  learner-visible payloads, not the executed artifact's environment, while
  architecture S7 requires learner execution without controller credentials.
  Findings 3–7 are Gate 4 revisions (incomplete clause repairs: test 18's prompt arm
  orphaned, test 43's ledger-resolution and test 44's evaluator-rule clauses claimed
  while those layers are mocked; Slice 8's "Test 1" label overclaims on offline
  adapters; Slice 2 does not match the literal software-factory "real happy path"
  rule; prose demo evidence lacks runnable entry points; the submission-compliance
  path lacks a hard no-go and Slice 16 omits YouTube/availability obligations).
  Applied now (Gate 3 only): test 33 revised; S5.8 clarified (`LIMIT_DECLARED`
  derives from declared limits only); new test 50
  `test_executor_env_exposes_no_controller_credentials` appended without renumbering
  1–49 (user decision). Gate 3 set to in progress here and mirrored in
  `SHIFTWORK_PLAN.md` and `AGENTS.md` S3. User decisions recorded: (A) Slice 2 will
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
- 2026-09-17 Gate 4 S11 decisions (documentation only): the user answered all four open
  questions in `04-slices.md` S11. (1) `NEBIUS_API_KEY`: a bounded early availability
  smoke check (key valid, model reachable) is authorized to run once a key is provided,
  retiring the submission-critical access unknown early; the full live assist-gateway
  demonstration still lands at Slice 12, which builds against recorded responses until
  then. (2) Demo baseline: Option A (downloadable test build) confirmed as the committed
  plan of record; hosted Option B stays strictly optional, pursued only if the Slice 13
  spike verifies a Nebius service can host the app. (3) Config numbers: attempt_limit 3,
  bookshop rotation 6/family, assist budgets 6/2 accepted as starting values; still
  challengeable at Slices 2/7/11/12, but changes after inventory authoring are expensive
  (capacity invariant, Gate 3 S7.1). (4) Sealed-inventory authorship: the agent drafts
  all 27 cases + fixtures; the user reviews every case and expected answer before
  sealing — the agent's review is not evidence (not an independent oracle). Applied to
  `04-slices.md`: S11 rewritten as resolved decisions, with matching edits in the Slice
  2 authoring note, Slice 12 authorization, S8, S9 risk 1 and S10. **Gate 4 remains NOT
  approved**; user review and an explicit approval decision are next. No credential was
  used; no implementation, installs, spike run, external service, commit or push
  occurred. The `docs/SHIFTWORK_PLAN.md` and `AGENTS.md` S3 gate-state snapshots still
  describe the revisions as "being applied" and were left unedited pending user
  instruction.
- 2026-09-17 Devpost form fold (documentation only): at the user's instruction the
  live submission-form fields the user provided (35 MB file upload, model/Nemotron
  feedback questions, Tavily runtime-call qualification clause, the illustrative
  "GPU instance types" wording, Builders & Brews dropdown) were added to
  `HACKATHON_REQUIREMENTS.md` under "Submission form fields (live Devpost form)".
  The Tavily runtime-call clause conflicts with the approved offline curation-only
  boundary (architecture S11; Gate 3 test 39) — recording it is a factual fold, not
  a design change. No gate state changed; Gate 4 remains NOT approved. No
  implementation, installs, credentials, external service, commit or push occurred.
- 2026-09-17 Gate 4 review round 2 (BLOCK) + Gate 3 backtrack #2: an independent
  static review of the Gate 4 documents returned BLOCK with five blockers and three
  revisions — G4-01 (the "optional" Slices 13–14 Sandbox path is actually
  product-critical: offline adapters cannot execute learner-edited code), G4-02 (S2
  file map omits `pyproject.toml`, a dependency lock, `demos/` and the clean-env
  install check), G4-03 (test 9's capture-retention clause has no owning slice),
  G4-04 (Slice 14 overclaims a full isolation verdict without a hostile canary),
  G4-05 (model-feedback form answers have no evidence protocol), G4-06 (stale gate
  snapshots), G4-07 (Git-Bash-only demo commands), G4-08 (no deployment slice if
  hosting is chosen). The user accepted the fix list and decided the Tavily
  question: pursue the prize via the shipped operator-run curation CLI (Slice 15's
  live `discover()` call); no runtime-path change, no architecture S11 / test 39
  backtrack, no organizer clarification; the form is answered "yes" only after the
  call has actually shipped. Applied now (Gate 3 only): S2 gains `pyproject.toml`,
  `requirements.lock`, the `demos/` tree and `tests/packaging/`; S6 gains appended
  test 51 `test_clean_env_install_and_run` without renumbering 1–50; the tests
  preface notes test 51 re-runs at the packaging slice. Gate 3 set to in progress
  here and mirrored in `SHIFTWORK_PLAN.md` and `AGENTS.md` S3. All `04-slices.md`
  edits (G4-01/03/04/05/07/08 + the S11 Tavily decision) are QUEUED and must not be
  applied until Gate 3 is explicitly re-approved. Limits: this review is static LLM
  document work — not runtime, security, human or learning evidence, and not an
  independent oracle. No implementation, installs, credentials, spike, external
  service, commit or push occurred.
- 2026-09-17 Gate 3 RE-APPROVED (second time) + Gate 4 revision round 2 applied: the
  user reviewed the packaging revision of `03-program-design.md` (S2 file map now
  carries `pyproject.toml`, `requirements.lock`, the `demos/` tree and
  `tests/packaging/`; S6 test 51 appended) and approved Gate 3. That released the
  queued round-2 edits, all now applied to `04-slices.md`: G4-01 (Slices 13–14 on the
  mandatory packaging path; Slice 16 depends on Slices 1–14; sandbox no-go wording in
  S9/S10), G4-03 (test 9 capture-retention clause named and demonstrated at Slice 8),
  G4-04 (Slice 14 re-runs tests 16–18 against the real adapter plus a canary hostile
  artifact), G4-05 (Slice 12 model-feedback evidence pack written to
  `evidence/model-feedback.md`; Slice 16 assembles form answers from it), G4-06 (this
  entry; `SHIFTWORK_PLAN.md` and `AGENTS.md` S3 snapshots updated), G4-07 (`demos/`
  modules are the canonical shell-independent evidence path; PowerShell where HTTP is
  unavoidable) and G4-08 (conditional Slice 17 + S8 five-condition Option B exit
  gate). S11 decisions 5–6 recorded (Tavily via the shipped curation CLI's live
  `discover()` call; execution path submission-critical with a pre-authorized early
  sandbox entitlement/I-O smoke check). **Gate 4 remains NOT approved**; it is now
  presented for the user's review and the explicit software-factory approval
  question. Limits: every review and edit is static LLM document work — not runtime,
  security, human or learning evidence, and no LLM is an independent oracle. No
  credential was used; no implementation, installs, spike run, external service,
  commit or push occurred.
- 2026-09-17 Gate 4 review round 3 (user verdict REVISE — three consistency
  corrections; documentation only): (1) the provisional Python bound in
  `03-program-design.md` S2 was tightened from `>=3.11,<3.14` to `>=3.12,<3.14` to
  match the approved 3.12+ stack decision — test 51's clean-env install would
  otherwise create an unintended Python 3.11 support obligation; (2) the Gate 3
  header now records its second backtrack/re-approval (packaging, test 51) plus the
  bound correction — the record it previously omitted; (3) the
  `HACKATHON_REQUIREMENTS.md` Tavily checklist was made neutral (whether a shipped
  operator-run curation CLI's live `discover()` call satisfies "functional, runtime
  call ... as part of its solution" is an interpretation question) and now points to
  the decision of record (`04-slices.md` S11 decision 5). The reviewer reported no
  remaining blocking defect in the 17-slice sequence. Limits: static LLM document
  work — not runtime, security, human or learning evidence, and not an independent
  oracle. Gate 3 remains APPROVED (the bound correction is a user-directed
  consistency fix, recorded in the document header and Approval history). **Gate 4
  remains NOT approved**; the explicit approval decision is next. No credential was
  used; no implementation, installs, spike run, external service, commit or push
  occurred.
- 2026-09-17 Gate 4 APPROVED: the user explicitly approved Gate 4 after the round-3
  corrections. Recorded in the gate line above, the Slice checklist (now
  authoritative here, per `04-slices.md` S2) and Approval history; the
  `04-slices.md` header is marked APPROVED the same day. Approval authorizes
  building the 17 slices in order, one at a time, each ending with the demonstrated
  demo evidence, a check-off here and the "Continue to slice N+1, or re-steer?"
  pause — and nothing else: installs, credentials, external services, the Slice 13
  spike, the Slice 15 ablation, deployment, outreach and ADR #4 remain separately
  authorized (`04-slices.md` S10). Separately the same day, the user authorized
  documentation Git operations only: commit of the approved gate documents on this
  branch, publish of the branch and merge to main (no co-author trailers); that
  authorization covers documentation commits, not slice work. Limits: static
  document work — no implementation, installs, credentials, spike run, external
  service use, deployment or outreach occurred. Scores remain conditional forecasts.
- 2026-09-17 Slice 1 (tracer bullet) IMPLEMENTED and demonstrated: the full HTTP
  lifecycle runs end to end with stubbed persistence and stubbed evaluation. New
  files: `shiftwork/` (app.py factory, api/schemas.py + api/routes.py, domain/models.py,
  store/db.py + store/repo.py with an inline tracer schema, executor/recorded.py,
  orchestrator.py, config.py, client/index.html stub board), `demos/lifecycle.py`,
  `shiftwork/fixtures/runs/tracer_transcript.json`, `tests/conftest.py`,
  `tests/api/test_tracer_lifecycle.py` and `tests/packaging/test_clean_env_install_and_run.py`
  (test 51). Evidence run this session: (1) `python -m demos.lifecycle` exit 0: board
  -> open `bookshop-shift-01` -> draft round trip -> freeze `ver-0001`
  (`placeholder-1`) -> `run-0001` FINALIZED through the `recorded` adapter (3 captures)
  -> check `cr-0001` fail STALE_BEYOND_RULE -> chained ledger with genesis prev_hash
  (SALE_COMPLETED, INCIDENT_OPENED) -> incident `BWB-01` OPEN -> close, final line
  "lifecycle evidence complete ... FINALIZED ... chain VALID with 2 events";
  (2) `pytest tests/api -q` 2 passed (lifecycle smoke asserting every route status
  and persisted row counts, plus restart persistence); (3) browser check on port 8017
  showing the stub board with the artifact version, open incident and ledger totals;
  (4) `pytest tests/packaging -q -s` re-run 2026-09-17 printed
  `clean-env mechanism: stdlib venv + pip` and `1 passed in 21.82s`; a full
  `pytest tests -q` re-run printed `3 passed`. Environment notes: test 51 performs
  a clean-env install from `requirements.lock` into a fresh temporary venv, and
  that install did run (whether it reached PyPI or was served from pip's cache was
  not separately instrumented). The project `.venv` (Python 3.12.13) already
  matches `requirements.lock` exactly (22 packages, verified with `uv pip list`)
  and was not modified. The stdlib-venv path is the mechanism selected here; an
  earlier version of this note claimed the stdlib path "is blocked on this machine
  by Windows Application Control (WinError 4551)" and "exercised its uv fallback,"
  which was false as recorded and has been corrected in `MISTAKES.md` (the block
  was a one-off, not reproducible on re-test, and the uv fallback never ran). All
  tracer stubs (placeholder content hashes, hardcoded
  check result, placeholder chain hashes, hardcoded ledger events and incident,
  inline tracer schema) are documented Slice 2+ replacements; hashing, evaluation,
  reducer, sealed cases, budgets, rotation and inheritance are NOT yet real, so no
  hackathon capability, learning or prize claim follows from this evidence. The only
  network operation was test 51's clean-env package install from the lockfile; no
  credential use, Nebius or Tavily inference call, spike run, deployment, outreach
  or commit occurred.
- 2026-09-18 Slice 2 (thin real vertical path) IMPLEMENTED and demonstrated: one
  shift's data now flows real end to end: content-hashed freeze → recorded replay
  of one checked-in transcript → one sealed case scored by a real deterministic
  evaluator → one pure-reduced ledger draft sealed into one real hash-chained event.
  The tracer's stub persistence and stub finalization are gone. New files:
  `shiftwork/domain/canonical.py` (the only canonical-serialization/hash point;
  floats rejected), `shiftwork/domain/errors.py`, `shiftwork/domain/contract_catalog.py`,
  `shiftwork/evaluator/evaluator.py`, `shiftwork/sealed/store.py`,
  `shiftwork/ledger/reducer.py`, `shiftwork/ledger/chain.py`,
  `shiftwork/store/schema.sql` (real DDL, `PRAGMA user_version = 2`), the authored
  fixtures (`fixtures/catalogs/bookshop_v1.json`,
  `fixtures/runs/thin_stale.json`, `fixtures/shop/bookshop_snapshot.json`,
  `fixtures/mission/bookshop_mission_v1.json`,
  `sealed/cases/bookshop_stale_information.json`), `demos/thin_path.py`, and the tests
  `tests/domain/test_canonical.py`, `tests/domain/test_contract_catalog.py`,
  `tests/store/{conftest,test_versions,test_restore}.py`,
  `tests/api/test_thin_path.py`. Modified: `domain/models.py` (real ContractParams,
  ContractCatalog, Claim/ServiceResponse, ArtifactVersion with files/storage_ref/
  contract/contract_catalog_hash, split LedgerEventDraft/LedgerEvent), `config.py`,
  `store/db.py` (loads schema.sql; version-mismatch guard), `store/repo.py`
  (engagement_config group; artifact_versions persist files/storage_ref/contract/
  catalog hash and re-verify content_hash on read → VersionTampered),
  `orchestrator.py` (real freeze + real finalize, no incident), `api/routes.py`
  (freeze takes a contract body; domain-error handler), `api/schemas.py`
  (ContractView/FreezeVersionRequest; chain_status may be BROKEN), `app.py` (seeds
  engagement_config; registers the domain handler), `demos/lifecycle.py`, and
  `tests/api/test_tracer_lifecycle.py` (rewritten to the real path). Deleted
  `shiftwork/fixtures/runs/tracer_transcript.json` (staged via `git rm`, not committed).
  Verbatim evidence run this session under the project `.venv` (Python 3.12.13):
  (1) `python -m demos.thin_path` exit 0, final line:
  "thin-path evidence complete: run run-0001 FINALIZED, content_hash
  87fb5615fd5482f4a0c395a1f95fad7fa5fc4613d63c7b4e467b25b4bf714fb9, one CheckResult
  fail/STALE_BEYOND_RULE with opaque expected_ref, one BACKLOG_RECORDED event seq 1
  chained on genesis, chain_status VALID". The one captured output bytes were
  `{"action":"answer","claims":[{"kind":"stock","value":"in_stock"}],"evidence_refs":["catalog:9780441013593"],"record_age_ms":5400000}`;
  the one CheckResult was `cr-0001` verdict `fail` reason `STALE_BEYOND_RULE`
  `expected_ref` `sealed:b8c5e7bee8760ce8d8cae47eb88cebd55ee8150944b4f21d513a545b10822f4e`
  `public_check_id` null; the one event hash `c0099aec092c13ec0c79c9bb934e80ba3396a47788897dc90a6c608382f1d695`
  on genesis prev_hash, `contract_catalog_hash`
  `d3df268cc83863a75f465543de26ab712efd7be193200a5e82710093d235ced6`.
  (2) `python -m pytest tests/domain tests/store -q` → "26 passed in 2.19s".
  (3) `python -m pytest tests/api -q` → "5 passed".
  (4) `python -m pytest tests/domain tests/store tests/api -q` → "31 passed in 1.91s".
  (5) `python -m demos.lifecycle` exit 0, final line: "lifecycle evidence complete:
  run run-0001 FINALIZED, ledger chain VALID with 1 events, 0 open incidents (Slice 2
  opens none)". (6) `git diff --check` reported no whitespace errors. Freeze
  determinism/immutability/restore are asserted by `tests/store/test_versions.py`
  (identical inputs → identical hash; changed file/contract/catalog-hash → different
  hash; a stored version whose files are tampered raises VersionTampered) and
  `tests/store/test_restore.py` (version hash + draft reconstruct from tables on a
  fresh connection). The evaluator scoring path was separately verified to run with
  `socket.socket`/`socket.create_connection` patched to raise (offline, no credential).
  Tests landed, with clause-level honesty per the `MISTAKES.md` prevention rule:
  1, 2, 3 (canonical hashing, FULL); 21 (version immutability, FULL); 22
  (freeze-requires-valid-contract, FULL); 23 (PARTIAL: latest version hash + draft
  reconstruct from tables with no executor checkpoint; the ledger-reconstruction
  clause completes at Slice 5 and the incident-reconstruction clause at Slice 7);
  43 (PARTIAL: changing a used option's label or rule id is refused; the
  ledger-resolution-after-re-version clause completes at Slice 5); 44 (PARTIAL: a
  declared limit is stored and never scored, absent from the one CheckResult and the
  one ledger event; the "cannot satisfy a required executable dimension or silently
  become an evaluator rule" clause completes at Slice 4 and the "and inherited" clause
  at Slice 8); plus the thin-path smoke check (`tests/api/test_thin_path.py`) asserting
  the one real CheckResult and one real hash-chained event are produced and persisted,
  which fails if any step is still mocked. NOT claimed: tests 4–15 and 42 (the S6
  evaluator/reducer robustness suites need the deepened Slices 4–5), and none of the
  deferred partial clauses listed above. Still mocked/minimal (each deepened by a
  named later slice): executor is `recorded` replay of one transcript only: no
  ExecutorAdapter Protocol, no normalize_captures, no local_process, no
  conformance/fault suite (Slice 3); evaluator is one hardcoded sealed case: no
  SealedCaseSet, no contract-parameterization across catalog options, no negative
  control, no unknown-schema alarm, only one of six stale_information variants (Slice
  4); ledger is one event; verify_chain runs on every ledger/board read, but there
  are no purity/replay-equality proofs, no fault injection, no idempotent finalize and
  no incident opening (Slice 5); rotation, budget, incidents, inheritance, assist and
  the six screens are absent. Schema is now `user_version = 2`; a database left at
  version 1 raises a clear RuntimeError from `db.ensure_schema` rather than
  auto-migrating or auto-deleting (verified against a constructed version-1 database;
  no `*.db` file exists or was created, since demos and tests use temp paths). ALL sealed cases and fixtures authored
  here are AGENT-DRAFTED and require the user's review before they are treated as
  sealed acceptance authority (`04-slices.md` S11 decision 4), specifically
  `bookshop_v1.json` (catalog), `bookshop_stale_information.json` (the one sealed case
  and its expected value), `thin_stale.json`, `bookshop_snapshot.json` and
  `bookshop_mission_v1.json`. Limits: this is offline runtime evidence on one fixed
  request, not human, learning, security-isolation or prize evidence; no capability,
  learning-gain or prize claim follows. No commit, push, branch or tag was created; the
  pre-existing uncommitted `.gitignore` `*.db` rule was left untouched and no runtime
  `*.db` file exists or was created (demos and tests use temp paths); the only staged
  change is the `git rm` of the obsolete tracer transcript. `tests/packaging` (test 51) was deliberately NOT re-run this session
  because it performs a clean-env install from `requirements.lock`, which Slice 2's
  no-install authorization does not cover; its demo dependency `demos.lifecycle` was
  run directly under the existing `.venv` (exit 0, FINALIZED), so the demo half of test
  51 is exercised but the install/serve half was not re-verified. No credential use,
  Nebius or Tavily inference call, spike run, external service, deployment or outreach
  occurred.
- 2026-09-18 Slice 2 hostile review (independent, execution-based) and fixes: verdict
  **PASS** with 2 MINOR findings, no BLOCKER or MAJOR defect. The reviewer re-ran the
  recorded evidence under `.venv` (31 passed, both demos exit 0, `git diff --check`
  clean), recomputed every pinned hash from the raw fixtures with a standalone script
  that imports nothing from `shiftwork` (all 5 golden vectors, the catalog hash, the
  `expected_ref`, the artifact content hash and the ledger event hash matched the
  recorded values), mutation-tested the thin-path smoke check (a stubbed `_finalize`
  produced failures, so it is not vacuous) and the read-back tamper guard, confirmed
  `verify_chain` reports BROKEN when any of payload, seq, prev_hash, hash or
  event_type is mutated in the stored event on both `/ledger` and `/board`, dumped
  every table after a live run to confirm no sealed-case content is readable back
  through any endpoint or table, and re-ran the evaluator with external egress blocked
  (DNS and socket-connect patched to raise; offline, no credential; the only socket
  activity was asyncio's loopback self-pipe inside `TestClient`). Findings and fixes
  applied this session: (MINOR-1) the Slice 2 evidence note implied an existing runtime
  `shiftwork.db`; no `*.db` file exists anywhere. The note is corrected to describe
  the version-1 guard as verified behavior rather than an existing file, and the error
  class is logged in `MISTAKES.md`. (MINOR-2)
  `test_declared_limit_is_stored_but_never_scored` could pass vacuously when scoring
  is dropped; exact-count asserts are added before the absence assertions, and the fix
  was mutation-checked (a stubbed `_finalize` now fails it). The user approved
  including the pre-existing uncommitted `.gitignore` `*.db` rules in this slice's
  change set and authorized the standard slice publish flow (commit on
  `shiftwork/slice-2`, push, `--no-ff` merge to main, no co-author trailers). Post-fix
  re-run this session: `pytest tests/domain tests/store tests/api -q` -> "31 passed";
  `python -m demos.thin_path` exit 0 with the same content_hash
  87fb5615fd5482f4a0c395a1f95fad7fa5fc4613d63c7b4e467b25b4bf714fb9; `python -m
  demos.lifecycle` exit 0; `git diff --check` clean. Mirrors (`AGENTS.md` S3 and
  `docs/SHIFTWORK_PLAN.md`) were updated to Slice 2 in this session. Limits: the
  review is agent execution work, not human, learning or security-isolation evidence,
  and no LLM is an independent oracle; `tests/packaging` (test 51) was again not
  re-run (install boundary).
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

## Slice 3 evidence: 2026-09-18

Slice 3 is IMPLEMENTED, demonstrated, independently reviewed (PASS, 2026-09-18)
and published; the review and publication entry is below. Scope: executor protocol
and frozen request/result models; shared raw-capture normalization; generalized
recorded replay; local subprocess execution of pinned trusted fixtures only;
stdlib learner HTTP template, literal JSONL requests, frozen snapshot and authored
fault transcripts. The controller passes frozen artifact bytes through the new
interface, binds request text and identities after normalization, and stores typed
executor failures and captured evidence without scoring those failed runs.
`RunOutput.log_ref` persists inline captured bytes; the API exposes `log_base64`,
not an internal file path. Schema version 3 adds that nullable column, with a narrow
schema-2 upgrade tested against a constructed temporary database retaining a row.
No existing runtime database is presumed by that test.

### Clause-level coverage and limits

- Test 28: FULL for the approved offline case table. Happy path plus port dead,
  timeout, truncation, non-UTF-8, refused connection and mid-batch termination
  have equal normalized captures and typed failures across both adapters. Bodies,
  HTTP status, ordinals, log bytes and capture timing are compared. Capture timing
  uses an injected `perf_counter_ns` clock; real monotonic deadlines, real loopback
  sockets and real subprocesses remain active. This is NOT equality of measured
  performance or run wall time. A separate non-injected-clock check exercises
  elapsed-time collection and literal request bytes against the frozen snapshot.
- Test 30: FULL. Every case returns `RawCapture` with strict bytes, never parsed
  service objects. Dict, list, text and bytearray bodies are refused. The controller
  integration test spies on the single normalization call and verifies retained
  failed bytes/logs after reopening the database, with no checks or ledger events.
- Test 31: FULL. Unknown manifests, altered bytes with the original manifest,
  extra files and path escapes are refused before subprocess creation. Trust is
  based on a pinned manifest/file-byte hash pair using the existing canonical
  implementation, not the caller's manifest alone. This is an execution guard,
  NOT hostile-code isolation.
- Test 50: PARTIAL, exactly the offline clauses. Recorded replay starts no process
  and reads no execution environment. Local execution passes only `SYSTEMROOT`
  and `WINDIR`, checked at spawn and in child-reported environment. Synthetic
  markers for `NEBIUS_API_KEY`, `CONTREE_SESSION`, `TAVILY_API_KEY`,
  `SHIFTWORK_DB_PATH`, sealed-store access and additional unlisted variables are
  absent from those environments and captured logs/bodies, with two captures
  required before absence checks. No real credentials were used. Host-filesystem
  isolation, in-sandbox reachable-file checks, scoped grants and the live
  `tokenfactory` provisioning arm remain unproved and deferred to Slice 14.
- Test 29: explicitly SKIPPED until the real adapter and authorized Sandbox access
  exist; exact skip output is below.
- `recorded` still executes no learner code. The normal API path remains the
  one-request Slice 2 replay, not a claim that arbitrary edited artifacts run
  locally. Local execution accepts only the eight pinned fixtures.
- ALL new fixtures and transcripts are agent-authored synthetic expectations,
  not historical Sandbox captures or an independent oracle. User review remains
  required before acceptance authority. The new service scaffold reads records
  without implementing Slice 4 freshness decisions. Evaluator, sealed store,
  canonical implementation, reducer and chain remain the minimal Slice 2 versions.
- No Slice 4 evaluation, rotation, budget, incident, inheritance, client-screen or
  tokenfactory implementation was added. No UI change or browser evidence is claimed.
  No Sandbox, human, learning, transfer or prize evidence follows from these tests.
- No install, dependency change, credential use, external service or non-loopback
  network operation was performed. `tests/packaging` was NOT run: its clean-env
  install is outside this task's authorization. No branch, commit, tag or push was
  created; the user owns hostile review and publication. The state summaries in
  `AGENTS.md` S3 and `docs/SHIFTWORK_PLAN.md` were synced, not the gate decisions.

### Baseline and corrections

Baseline command: `.venv/Scripts/python.exe -m pytest tests/domain tests/store tests/api -q`.
Verbatim result line: `31 passed, 2 warnings in 2.58s`. The same FastAPI/Starlette
warnings remain in final verification; nothing was installed to remove them.

The failed environment trap, Windows log-newline mismatch, insufficient refusal
fixture deadline, ignored fixture source directory and CRLF snapshot pin were
corrected and recorded in `MISTAKES.md` with observed outputs and prevention rules.
The refusal tests now allow five seconds to observe Winsock refusal; the deliberate
timeout still uses a two-second real deadline. Assertions and failure kinds were
not weakened. LF source rules plus a byte-level regression prevent checkout from
changing the snapshot hash. Only source bytes were aligned; captured response
bytes, including truncation and invalid UTF-8, are never normalized away.

### Required executor command: verbatim output

`.venv/Scripts/python.exe -m pytest tests/executor -q`

```text
happy_path: captures=2 bytes/status/ordinal/time/logs=identical failure=NONE (injected capture clock; real sockets/deadline)
.port_dead: captures=1 bytes/status/ordinal/time/logs=identical failure=SERVICE_UNREACHABLE (injected capture clock; real sockets/deadline)
.timeout: captures=1 bytes/status/ordinal/time/logs=identical failure=REQUEST_TIMEOUT (injected capture clock; real sockets/deadline)
.truncated_body: captures=1 bytes/status/ordinal/time/logs=identical failure=CAPTURE_TRUNCATED (injected capture clock; real sockets/deadline)
.non_utf8_body: captures=1 bytes/status/ordinal/time/logs=identical failure=CAPTURE_NON_UTF8 (injected capture clock; real sockets/deadline)
.connection_refused: captures=2 bytes/status/ordinal/time/logs=identical failure=SERVICE_UNREACHABLE (injected capture clock; real sockets/deadline)
.kill_mid_batch: captures=1 bytes/status/ordinal/time/logs=identical failure=SANDBOX_TERMINATED (injected capture clock; real sockets/deadline)
.s............trusted-guard unknown_hash: PROVISION_FAILED; subprocess starts=0
.trusted-guard modified_bytes: PROVISION_FAILED; subprocess starts=0
.trusted-guard extra_file: PROVISION_FAILED; subprocess starts=0
.trusted-guard path_escape: PROVISION_FAILED; subprocess starts=0
...credential-guard recorded: captures=2; injected markers absent from bodies/logs; no process or environment access
.credential-guard local_process: captures=2; injected markers absent from bodies/logs; spawn env and child-reported env match SYSTEMROOT/WINDIR allowlist
.......                                       [100%]
============================== warnings summary ===============================
tests/executor/test_conformance.py::test_controller_normalizes_once_and_retains_failed_capture
  C:\Users\jayd0\OneDrive\Desktop\nebius_nvidia\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

tests/executor/test_conformance.py::test_controller_normalizes_once_and_retains_failed_capture
  C:\Users\jayd0\OneDrive\Desktop\nebius_nvidia\.venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
33 passed, 1 skipped, 2 warnings in 24.21s
```

### Required regression command: verbatim output

`.venv/Scripts/python.exe -m pytest tests/domain tests/store tests/api tests/executor -q`

```text
...............................happy_path: captures=2 bytes/status/ordinal/time/logs=identical failure=NONE (injected capture clock; real sockets/deadline)
.port_dead: captures=1 bytes/status/ordinal/time/logs=identical failure=SERVICE_UNREACHABLE (injected capture clock; real sockets/deadline)
.timeout: captures=1 bytes/status/ordinal/time/logs=identical failure=REQUEST_TIMEOUT (injected capture clock; real sockets/deadline)
.truncated_body: captures=1 bytes/status/ordinal/time/logs=identical failure=CAPTURE_TRUNCATED (injected capture clock; real sockets/deadline)
.non_utf8_body: captures=1 bytes/status/ordinal/time/logs=identical failure=CAPTURE_NON_UTF8 (injected capture clock; real sockets/deadline)
.connection_refused: captures=2 bytes/status/ordinal/time/logs=identical failure=SERVICE_UNREACHABLE (injected capture clock; real sockets/deadline)
.kill_mid_batch: captures=1 bytes/status/ordinal/time/logs=identical failure=SANDBOX_TERMINATED (injected capture clock; real sockets/deadline)
.s............trusted-guard unknown_hash: PROVISION_FAILED; subprocess starts=0
.trusted-guard modified_bytes: PROVISION_FAILED; subprocess starts=0
.trusted-guard extra_file: PROVISION_FAILED; subprocess starts=0
.trusted-guard path_escape: PROVISION_FAILED; subprocess starts=0
...credential-guard recorded: captures=2; injected markers absent from bodies/logs; no process or environment access
.credential-guard local_process: captures=2; injected markers absent from bodies/logs; spawn env and child-reported env match SYSTEMROOT/WINDIR allowlist
.......        [100%]
============================== warnings summary ===============================
.venv\Lib\site-packages\fastapi\testclient.py:1
  C:\Users\jayd0\OneDrive\Desktop\nebius_nvidia\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

.venv\Lib\site-packages\starlette\testclient.py:53
  C:\Users\jayd0\OneDrive\Desktop\nebius_nvidia\.venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
64 passed, 1 skipped, 2 warnings in 25.30s
```

### Deferred adapter: verbatim skip output

`.venv/Scripts/python.exe -m pytest tests/executor/test_conformance.py::test_conformance_suite_tokenfactory -q -rs`

```text
s                                                                        [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\executor\test_conformance.py:88: Test 29: tokenfactory conformance requires the real adapter and authorized sandbox access in Slice 14
1 skipped in 0.39s
```

### Thin-path regression demonstration

`.venv/Scripts/python.exe -m demos.thin_path` exited 0. Verbatim final line:

```text
thin-path evidence complete: run run-0001 FINALIZED, content_hash 44abb79897239264ac4d01a1f3688741cf9dd598019ab95e4f13813b02999158, one CheckResult fail/STALE_BEYOND_RULE with opaque expected_ref, one BACKLOG_RECORDED event seq 1 chained on genesis, chain_status VALID
```

The artifact hash changes because the inline scaffold was replaced with the three
on-disk template files. Canonical hashing and the original stale response outcome
are unchanged. The original event hash printed by the same demo is
`c0099aec092c13ec0c79c9bb934e80ba3396a47788897dc90a6c608382f1d695`.

### Source-scope and Git-state verification

An inline Python check compared `git diff --name-only` and
`git ls-files --others --exclude-standard` against canonical/evaluator/sealed/ledger,
client, dependency and packaging paths, scanned added lines/new files for em dashes,
and printed staged paths and HEAD. Verbatim output before the docs-only state sync:

```text
protected Slice 2/dependency/client/packaging paths changed: []
new em dashes: 0
staged paths: []
HEAD: 8eba305
```

`git ls-files --others --exclude-standard shiftwork/fixtures/artifacts` includes the
trusted sources after the narrow `.gitignore` exception; the previously hidden
source directory is now reviewable. The tests' exact-byte pins include those files.

After syncing the documentation, `git diff --check` plus assertions over the
three state summaries, added text and Git state printed:

```text
git diff --check: PASS
Slice 3 evidence and state mirrors: PASS; Slice 4 unchecked
new em dashes: 0
Git state: shiftwork/slice-3; HEAD 8eba305; no staged changes
```

### Adversarial review corrections: 2026-09-18

The execution-based review returned REVISE for two reproduced defects. The user
then authorized applying both fixes and rerunning the tests. `executor/recorded.py`
now rejects inconsistent transport metadata and invalid log base64, derives a
missing non-UTF-8 failure from the captured bytes, and retains those bytes/logs
through the controller's FAILED path without checks or ledger events. The valid
combination of process termination and a truncated final response remains allowed.
`store/db.py` now places the log-column ALTER TABLE and schema version update in
one explicit transaction. An injected version-write failure rolls back the column;
reopening and repeating the upgrade succeeds with the existing row preserved.

Twelve tests were added to `tests/executor/test_conformance.py`. Before the fixes,
the focused regression command (`-k "inconsistent_transport or derives_non_utf8 or
termination_after_partial or failure_cannot_finalize or rolls_back_on_version_write"`)
printed `11 failed, 1 passed, 34 deselected, 2 warnings in 3.81s`. Those were expected
pre-fix failures; the passing case protects the legitimate termination/truncation
combination. After the fixes, the replay-focused selection printed
`11 passed, 35 deselected, 2 warnings in 1.82s`, and the schema selection (`-k
"schema_two"`) printed `2 passed, 44 deselected in 0.58s`.

Final commands and verbatim result lines:

```text
.venv/Scripts/python.exe -m pytest tests/executor -q
45 passed, 1 skipped, 2 warnings in 24.00s

.venv/Scripts/python.exe -m pytest tests/domain tests/store tests/api tests/executor -q
76 passed, 1 skipped, 2 warnings in 25.56s

.venv/Scripts/python.exe -m pytest tests/executor/test_conformance.py::test_conformance_suite_tokenfactory -q -rs
SKIPPED [1] tests\executor\test_conformance.py:89: Test 29: tokenfactory conformance requires the real adapter and authorized sandbox access in Slice 14
1 skipped in 0.60s
```

Both existing warnings remain: Starlette's deprecated `httpx` TestClient use and
the deprecated `anyio.abc.BlockingPortal` alias. The thin-path demo exited 0 with
the same artifact hash and ledger event hash recorded above, FINALIZED and chain
VALID. The review's earlier combined run took `215.67s (0:03:35)` before passing;
its diagnostic rerun took `24.43s`. That unexplained timing anomaly is retained,
not erased by these faster post-fix runs.

No fixture pins, executor interfaces, local-process implementation, evaluator,
ledger, gate decisions or later-slice scope changed. The two error causes and
prevention rules are recorded in `MISTAKES.md`. Test 50 remains partial and test 29
remains deferred. Packaging was not run; no install, credential use, external
service, branch, commit, tag or push occurred. User fixture review and publication
are recorded separately in the next entry.

### Independent execution review and publication: 2026-09-18

An independent, execution-based review of the complete uncommitted Slice 3
implementation returned **PASS** with no acceptance-blocking defect. It covered
every tracked modification and untracked source, including the trusted fixtures
that the pre-existing `artifacts/` ignore rule had hidden, and traced frozen
artifact to adapter to raw captures to normalization to controller-owned
identities to persistence/API to finalization or typed failure. No project file
was edited during the review; the committed bytes are the reviewed bytes.

Re-run under `.venv`: `pytest tests/executor -q` printed `45 passed, 1 skipped,
2 warnings in 25.34s`; `pytest tests/domain tests/store tests/api tests/executor
-q` printed `76 passed, 1 skipped, 2 warnings in 26.40s`; the tokenfactory node
printed `1 skipped in 0.39s` with the explicit Slice 14 reason;
`python -m demos.thin_path` exited 0 with the run FINALIZED, content_hash
`44abb79897239264ac4d01a1f3688741cf9dd598019ab95e4f13813b02999158` and
chain_status VALID; `git diff --check` passed. Both known warnings remain
(Starlette/httpx TestClient; anyio BlockingPortal alias); nothing was installed
to suppress them. The earlier combined-run timing anomaly (215.67s) was not
reproduced and remains unexplained.

Independent probes beyond the suite: 8/8 malformed replay transcripts (invalid
JSON, wrong root type, null or wrongly shaped captures, invalid body base64,
negative timing, missing status, invalid log base64) returned INTERNAL with zero
accepted captures; changed snapshot, different valid batch and a path escape all
returned PROVISION_FAILED; a failed replay retained raw bytes, logs and
controller-owned identities after reopening the database with checks=0 and
events=0; an injected interruption of the actual schema-2 upgrade left version 2
without the column and every pre-existing row byte-identical, and the retry plus
repetition reached version 3; a real 1-second deadline returned at 1.031s;
cancellation during a real socket read propagated and cleaned up child and
workspace; live termination after a partial response produced SANDBOX_TERMINATED
with the truncated prefix, status and logs retained; four targeted in-memory
mutations of the two fixes were each detected by the existing regressions; a
source-only copy of the Git-visible files passed fixture pins, a live run and the
thin demo with no installation.

User fixture acceptance: after being asked to review it, the user accepted the
Slice 3 fixture and template set as a starting set. That acceptance is not
independent execution evidence, a learning result, or authority to seal Slice 4
cases; new sealed cases still require the user's review before sealing
(`04-slices.md` S11 decision 4).

Publication (user-authorized 2026-09-18): commit `8df3d6b` "Implement Slice 3
recorded/local_process executor conformance" (42 files) on `shiftwork/slice-3`,
pushed as `origin/shiftwork/slice-3`; `--no-ff` merge `1f38220` into main,
pushed; `shiftwork/slice-4` branch created from the merge. No co-author trailers.

Limits: this review is agent execution work, not human, learning, security or
hostile-code-isolation evidence, and no LLM is an independent oracle. Test 50
remains partial (offline clauses only); test 29 remains deferred;
`tests/packaging` was deliberately not run; no install, credential use, external
service, deployment or outreach occurred.

## Slice 4 evidence: 2026-09-18

Slice 4 is IMPLEMENTED and demonstrated; the user's review of the new sealed cases
is pending (not yet accepted, not sealed as acceptance authority). An independent
execution review of this change set returned REVISE on 2026-09-18; the corrections
it required are recorded in the corrections subsection at the end of this section,
and the evidence above stays as the first-pass record. Baseline:
branch `shiftwork/slice-4` at commit `1e4e6c1` with a clean tree, so the whole
Slice 4 change set is distinguishably `git diff` from the reviewed Slice 3 bytes;
no tag, branch, commit or push was created. Scope: the contract-parameterized
deterministic evaluator and the completed first sealed family
(`stale_information`, all six variants), deepening the Slice 2 evaluation.

New files: `shiftwork/domain/customer_answer.py` (validate structured responses
against public records, recompute the asserted age, render customer text
deterministically); `demos/evaluate_transcript.py` (approved demo entry point);
`tests/evaluator/test_evaluator.py`; `tests/domain/test_customer_answer.py`;
`shiftwork/fixtures/requests/stale_family.jsonl` (six requests, pin
`6055e2c82fe365447346de86940ab3ff450d4d4c1fe9c6103042ba45882e5990`);
`shiftwork/fixtures/shop/bookshop_stale_snapshot.json` (seven records including
one superseded pair, pin
`230d6f8aeb3eff61cb5d68ebaafe1fa5ce365aba4c9a9c0b96b85b8541cc0131`);
`shiftwork/fixtures/runs/passing_stale.json` and `failing_stale.json`
(hand-authored response bytes, both pinning the batch and snapshot hashes above).

Changed: `shiftwork/evaluator/evaluator.py` (new-shape `SealedCase` with
`schema_version`/`family`/`check_id`/`request_ordinals`/`expected`,
`SealedCaseSet`, pure `evaluate(outputs, sealed_cases, contract, public_records)`,
rule dispatch by the mirrored catalog rule ids, opaque `expected_ref`);
`shiftwork/sealed/store.py` (`load_family` plus `load_drawn_cases` returning the
family inventory because variant rotation lands at Slice 7;
`UnsupportedSealedSchema` hard alarm on unknown schema versions);
`shiftwork/domain/errors.py` (adds `ServiceResponseInvalid`,
`UnsupportedSealedSchema`); `shiftwork/orchestrator.py` (`_finalize` evaluates the
drawn case set under the frozen version contract against the run-consumed
snapshot's public records, then reduces and chains as before; persisted `cr-` ids
are still re-stamped sequentially per insert);
`shiftwork/sealed/cases/bookshop_stale_information.json` (the Slice 2 one-case file
reshaped into the six-case family inventory; the old one-case shape is
superseded).

Implemented rule semantics (documented in the evaluator module; the rule
constants were revised the same day, see the corrections subsection): the
`invariant.never_invent_fact` rule is stance-independent (a factual claim with no
evidence is `MISSING_EVIDENCE`; a claim supported by nothing, or only by a
case-listed superseded record, is `INVENTED_FACT`); `freshness.use_newest_with_age`
fails a hard answer asserting a stock, price or availability claim from a record
older than the one-hour limit stated in the catalog v2 label, with
`STALE_BEYOND_RULE`; `stance.hard_check_high_risk` applies that failure only to
price, the high-risk kind named in the v2 label; `stance.verify_exact_now` states
no refusal threshold (the permissive tradeoff its own label describes) and adds no
rule of its own. Parse or validation failures (unresolvable ref, false, missing or
evidence-less age attestation, malformed body) fail `MALFORMED_RESPONSE` and never
produce customer text; `render_customer_text` itself has no runtime consumer yet
(module contract only, see the corrections subsection).

### Failing-first and verification commands (verbatim)

Before the implementation existed, the new tests failed at collection:

```text
ERROR tests/evaluator/test_evaluator.py
ERROR tests/domain/test_customer_answer.py
!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!
2 warnings, 2 errors in 0.89s
```

(the evaluator module's ImportError for `UnsupportedSealedSchema`; the
customer-answer module was `ModuleNotFoundError: No module named
'shiftwork.domain.customer_answer'`).

Baseline before any edit, `.venv/Scripts/python.exe -m pytest tests/domain
tests/store tests/api tests/executor -q`: first run printed `1 failed, 75 passed,
1 skipped, 2 warnings in 86.98s` (one `happy_path` conformance failure in a run
over three times slower than the recorded 25s); the failing node printed
`1 passed in 0.49s` alone and the clean rerun printed `76 passed, 1 skipped,
2 warnings in 21.98s`. Recorded as a machine-load flake, not clean proof; the
Slice 3 timing anomaly (215.67s) was not reproduced by any Slice 4 run.

After implementation:

```text
.venv/Scripts/python.exe -m pytest tests/evaluator -q
8 passed, 2 warnings in 0.61s

.venv/Scripts/python.exe -m pytest tests/evaluator tests/domain/test_customer_answer.py -q
11 passed, 2 warnings in 0.84s

.venv/Scripts/python.exe -m pytest tests/domain tests/store tests/api tests/executor tests/evaluator -q
87 passed, 1 skipped, 2 warnings in 21.64s
```

### Approved demo evidence (verbatim summary lines, both exit 0)

```text
.venv/Scripts/python.exe -m demos.evaluate_transcript --fixture fixtures/runs/passing_stale.json
evaluate-transcript evidence complete: passing_stale.json -> 6 pass / 0 fail with reason codes and opaque expected_refs; sockets blocked; contract STANCE USE_NEWEST_RECORD_WITH_AGE

.venv/Scripts/python.exe -m demos.evaluate_transcript --fixture fixtures/runs/failing_stale.json
evaluate-transcript evidence complete: failing_stale.json -> 0 pass / 6 fail with reason codes and opaque expected_refs; sockets blocked; contract STANCE USE_NEWEST_RECORD_WITH_AGE
```

The failing transcript's reason codes in ordinal order: `STALE_BEYOND_RULE`,
`STALE_BEYOND_RULE`, `INVENTED_FACT`, `INVENTED_FACT`, `MISSING_EVIDENCE`,
`MALFORMED_RESPONSE`. The passing transcript's case 1 `expected_ref` is
`sealed:6c5e7d09c1599646e8c9867ffea26c7cad5d56d5d5957fd551bbf29393595a9d`.

Regression demos: `python -m demos.thin_path` exit 0 with the unchanged artifact
content_hash `44abb79897239264ac4d01a1f3688741cf9dd598019ab95e4f13813b02999158`,
one CheckResult fail/`STALE_BEYOND_RULE` (its `expected_ref` changed to the same
`sealed:6c5e7d09...` value because the case file shape changed; the verdict did
not), one `BACKLOG_RECORDED` event seq 1 chained on genesis, chain VALID;
`python -m demos.lifecycle` exit 0 with chain VALID and 0 open incidents
(Slice 4 opens none).

### Clause-level coverage and limits

- Test 11 FULL (revised): transitive import-closure scan over `evaluator/`,
  `sealed/` and `domain/customer_answer.py`, following every resolvable
  shiftwork import to a fixed point (the parsed set is asserted to include
  `domain/models.py`, `canonical.py` and `errors.py`) with no HTTP client,
  socket, SSL, assist, executor or curation imports anywhere in the closure,
  plus a full six-case evaluation with `socket.socket`, `create_connection` and
  `getaddrinfo` blocked. The block covers the scoring phase; the file-based
  replay's event loop creates its loopback self-pipe first (framework resources
  before a global trap, per `MISTAKES.md`).
- Test 12 FULL: the failing fixture yields 6/6 failing verdicts with the
  hand-derived reason codes; the passing fixture yields 6/6 passes.
- Test 13 FULL (revised): no scalar from any sealed expected block (record ids,
  superseded refs, claim values and notes; 25 tokens) appears in any serialized
  evaluator result or in the thin-path API payload, and every `expected_ref` is
  a distinct 64-hex opaque ref. The live API path does not yet carry the whole
  family (per-run draws land at Slice 7).
- Test 14 FULL: on the same failing transcript request 1 flips fail/pass/pass and
  request 2 flips fail/pass/fail across `USE_NEWEST_RECORD_WITH_AGE`,
  `VERIFY_EXACT_CLAIMS_NOW` and `HARD_CHECK_HIGH_RISK_ONLY`; the flips are
  dictated by the constants the committed v2 labels state (the one-hour limit,
  price as the high-risk kind), not by hidden case data; invariant failures
  (requests 4, 5, 6) are identical under every stance; the correct transcript
  passes under every stance. A binding-guard test pins the evaluator's rule-id
  mirror to both frozen catalog versions.
- Test 15 FULL (revised): `schema_version` 2 raises `UnsupportedSealedSchema` at
  the case level and at the file level; version 1 still loads all six cases. An
  empty or duplicated `request_ordinals` list raises `InvalidSealedCase` at
  load time.
- Test 42 FULL: pinned rendered sentences for answer (one and two claims), ask,
  decline and escalate; a false age, unresolvable ref, age-without-evidence and
  evidence-without-age all raise before any sentence exists; a malformed claim
  never parses; no `reply_text` field or source string exists in the package.
  `render_customer_text` has no runtime consumer yet; it is a module contract
  until the S3.9 projection lands with the client slices.
- Test 44 evaluator clause COMPLETE: rule-looking declared limits change no
  verdict and surface nowhere in results; a declared limit cannot satisfy the
  required STANCE dimension (refused by `validate_contract`).
- NOT implemented, each with no data path yet rather than a silent stub: visible
  checks and `CheckDef` evaluation (their data path lands with rotation/client
  slices), latency-budget evaluation, and the clarify/escalate/estimate rule
  bindings. `load_drawn_cases` returns the full family inventory while rotation
  does not exist; Slice 7 replaces the body with exactly the persisted draws.
- S7.2 render-map wording: reviewed against the implemented semantics and adopted
  unchanged, so no Gate 3 revision is required; the map itself is materialized
  where it is pinned (test 19, Slice 6).
- ALL six cases, both transcripts, the batch and the snapshot are AGENT-DRAFTED
  and require the user's review before they are treated as sealed acceptance
  authority (`04-slices.md` S11 decision 4). The earlier user acceptance of the
  Slice 3 fixture and template set does not cover them and is recorded above
  unchanged; nothing here claims publication or widened authority.
- Limits: offline runtime evidence on hand-authored fixtures only, not human,
  learning, security-isolation or prize evidence; no UI or browser evidence.
  Live-socket executor conformance cases stay load-sensitive by design: the
  recorded `happy_path` flake class was reproduced by the review on `port_dead`
  under CPU oversubscription (`REQUEST_TIMEOUT` against the real 5 s deadline),
  which does not mask a logic bug. No
  capability, learning-gain or prize claim follows. No install, dependency change,
  credential use, external service or non-loopback network operation occurred;
  `tests/packaging` was not run (its clean-env install is outside this task's
  authorization). No branch, commit, tag or push was created.
- Hygiene: `git diff --check` exit 0; no added line contains an em dash; every
  new file and the sealed case file are LF (`i/lf w/lf` under the new attribute
  rule); other edited tracked files show CRLF in this worktree only because
  `core.autocrlf=true`, and their index bytes are LF; no new or changed file is
  git-ignored; `git status` lists only the in-scope files. State summaries in
  `AGENTS.md` S3 and `docs/SHIFTWORK_PLAN.md` were
  synced; no gate decision changed.

### Independent review corrections: 2026-09-18

An independent, execution-based review of the uncommitted Slice 4 change set
returned **REVISE**. The user adjudicated the one blocking semantic decision
(create catalog v2 with the constants in the labels) and authorized the
revision. Every finding below was reproduced or independently re-verified before
this section was written.

MAJOR-1, hidden stance parameters (fixed by the v2 catalog): the evaluator
previously read `max_record_age_ms`, `stale_assert_kinds` and `high_risk_kinds`
from the sealed case block, so the failing transcript's request 1 was scored
`fail/STALE_BEYOND_RULE` for behavior the committed `USE_NEWEST_RECORD_WITH_AGE`
label endorses ("answer from the newest record you have and report how old it
is"), against a one-hour limit no learner-visible artifact stated. The approved
rule (03-program-design S3.2: sealed cases check consistency with the learner's
selected option, not a hidden right option) made this a sealing blocker.
`shiftwork/fixtures/catalogs/bookshop_v2.json` is a new catalog version (v1 stays
byte-frozen and replay-compatible) whose two freshness labels now state the
constants: `USE_NEWEST_RECORD_WITH_AGE` refuses stock, price or availability
claims from records older than one hour, and `HARD_CHECK_HIGH_RISK_ONLY` names
price as the high-risk kind and refuses a price from a record older than one
hour. The evaluator holds `FRESHNESS_LIMIT_MS` and `HIGH_RISK_KINDS` as fixed
rule constants mirrored from those labels, and the six sealed `expected` blocks
were reduced to scenario data only (`record_id`, `superseded_refs`,
`expected_claim`, `note`). This restores the provenance the Slice 2 case note
carried ("the one-hour freshness limit the contract selected") and the six-case
reshape had dropped; the owner is now a visible label rather than an unpublished
number. Every verdict in the recorded failing and passing matrices is unchanged;
only the `expected_ref` values changed with the shrunken expected blocks.
`VERIFY_EXACT_CLAIMS_NOW` remains the permissive stance its v2 label describes
(no refusal threshold), which test 14 exercises.

MAJOR-2, validation wiring (fixed by a regression test):
`test_validation_failure_through_evaluate_is_malformed_response` scores a
false-age body and an unresolvable-ref body through `evaluate` and asserts
`MALFORMED_RESPONSE`. Failing capability verified by mutation: replacing the
`validate_service_response` call in `_score` with a pass-through made the new
test fail (`assert 'pass' == 'fail'`); the real call was restored and the suite
re-ran green.

Corrections from the minor findings and the missed-items list:

- Test 11: the static scan is now a real transitive closure
  (`_transitive_imports` follows every resolvable shiftwork import to a fixed
  point and asserts `domain/models.py`, `canonical.py` and `errors.py` were
  parsed). Failing capability verified by planting `import socket` in
  `domain/canonical.py`, which the old one-level scan never parsed; the test
  failed with `forbidden import in the evaluation closure: socket`, the probe
  was removed and `git diff` for that file is empty.
- Test 13: the sealed token set now collects every scalar in every expected
  block (record ids, superseded refs, claim values, notes; 25 tokens). The live
  API arm commits the v2 contract fixture `contract_stale_family.json`.
- Test 15: the unknown-version alarm now also covers the file-level
  `schema_version` (the review's probe, file v2 with cases v1, previously loaded
  silently). A separate guard rejects an empty or duplicated `request_ordinals`
  list at load time with the new `InvalidSealedCase` error.
- New guards: `test_v2_labels_declare_the_rule_constants` pins the evaluator
  constants to the v2 label text; `test_sealed_expected_blocks_carry_no_rule_parameters`
  pins expected blocks to the four scenario keys so a hidden rule parameter
  cannot return without failing the suite; the binding guard now checks both
  catalog versions.
- `.gitattributes` adds `shiftwork/sealed/cases/* text eol=lf` and the LF
  checkout test now scans `SEALED_CASES_DIR`; the case file is LF.
- Wording: the demo line now says "sockets blocked during scoring" (the phase
  where the block holds by construction); `render_customer_text` is stated as a
  module contract with no runtime consumer yet; the `MALFORMED_RESPONSE` arms
  now exercised end to end are both the malformed body (case 6) and the
  validation failures (new test).
- Known untested edges, recorded for Slice 6/7 to pin before the data widens
  (review items i-iv): a supporting non-superseded ref wins over a contradicting
  ref; staleness is checked only for `action == "answer"`; the verified age is
  the minimum over cited records; duplicate or overlapping ordinals are now
  rejected at load time but not otherwise constrained.
- `check_id` keeps the sealed-file-derived `-01` ordinal format; the deliberate
  decision stays with Slice 6's leak lint (pre-existing at HEAD, learner-visible
  by design in S3.2).

Revised verification commands and verbatim result lines:

```text
.venv/Scripts/python.exe -m pytest tests/evaluator -q
12 passed, 2 warnings in 0.63s

.venv/Scripts/python.exe -m pytest tests/evaluator tests/domain/test_customer_answer.py -q
15 passed, 2 warnings in 0.78s

.venv/Scripts/python.exe -m pytest tests/domain tests/store tests/api tests/executor tests/evaluator -q
91 passed, 1 skipped, 2 warnings in 22.18s

mutation probe, validation wiring replaced by a pass-through:
1 failed, 11 deselected, 2 warnings in 0.62s  (assert 'pass' == 'fail')

mutation probe, `import socket` planted in domain/canonical.py:
1 failed, 11 deselected, 2 warnings in 0.50s  (forbidden import in the evaluation closure: socket)
```

Revised demo outputs (both exit 0):

```text
.venv/Scripts/python.exe -m demos.evaluate_transcript --fixture fixtures/runs/passing_stale.json
evaluate-transcript evidence complete: passing_stale.json -> 6 pass / 0 fail with reason codes and opaque expected_refs; sockets blocked during scoring; contract STANCE USE_NEWEST_RECORD_WITH_AGE

.venv/Scripts/python.exe -m demos.evaluate_transcript --fixture fixtures/runs/failing_stale.json
evaluate-transcript evidence complete: failing_stale.json -> 0 pass / 6 fail with reason codes and opaque expected_refs; sockets blocked during scoring; contract STANCE USE_NEWEST_RECORD_WITH_AGE
```

The failing transcript's reason codes in ordinal order are unchanged:
`STALE_BEYOND_RULE`, `STALE_BEYOND_RULE`, `INVENTED_FACT`, `INVENTED_FACT`,
`MISSING_EVIDENCE`, `MALFORMED_RESPONSE`. Case 1's new `expected_ref` is
`sealed:7fcb2d9e60a39568df300a08f8c3b556a3622eff832f67d0a26d0c1851b3b395` on
every surface (both transcript demos and the thin-path API check), replacing the
pre-revision `sealed:6c5e7d09...`.

Thin path and lifecycle regression demos re-ran after the revision:
`python -m demos.thin_path` exit 0 with the unchanged artifact content_hash
`44abb79897239264ac4d01a1f3688741cf9dd598019ab95e4f13813b02999158`, one
CheckResult fail/`STALE_BEYOND_RULE` (new `expected_ref` above), one
`BACKLOG_RECORDED` event seq 1 chained on genesis, chain VALID;
`python -m demos.lifecycle` exit 0 with chain VALID and 0 open incidents.

Scope and limits: the revision adds `bookshop_v2.json`,
`contract_stale_family.json`, the guard tests and the changes above; it touches
no gate document and changes no gate decision. It does not widen authorization:
`tests/packaging` was not run; no install, dependency change, credential use,
external service, branch, commit, tag or push occurred. The family, both
transcripts and the new v2 labels remain AGENT-DRAFTED and still require the
user's review before sealing (`04-slices.md` S11 decision 4); nothing here
claims publication or widened authority.

## Approval history

- Gate 1 — Product: approved by the user on 2026-09-15 after the service-workbench
  redesign. The final independent review remains a requested safeguard, not human
  evidence and not Gate 2 approval.
- Gate 1 — Product: final independent review completed 2026-09-15 with verdict
  **PASS — GATE 1 FINAL REVIEW**. No backtrack. Gate 1 remains APPROVED; Gate 2
  drafting authorized and started.
- Gate 2 — Architecture: approved by the user on 2026-09-15 after an independent
  review of `02-architecture.md` (internal consistency, `AGENTS.md` S8 boundaries,
  Gate 2 template fit) and a re-fetch of five primary sources confirming the S16
  "Verified" claims. One correction applied (S1 Fit enumeration). Approval covers the
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
  applied the same day (revised test 33, clarified S5.8, appended test 50). The
  2026-09-16 approval above remains the historical record; explicit re-approval of
  the revised document is pending and must precede any Gate 4 revision or approval.
- Gate 3 — Program Design: RE-APPROVED by the user on 2026-09-17 after reviewing the
  revised `03-program-design.md`. This satisfies the precondition above and unblocks
  the queued Gate 4 revisions (decision A Slice 2 thin-real-path restructure plus
  edits S4-2..S4-14, with clause-level test re-mapping). Approval covers
  `03-program-design.md` only; it does not approve Gate 4, and does not authorize
  implementation, installs, credentials, spike runs, commits, deployment or outreach.
- Gate 3 — Program Design: BACKTRACKED a second time on 2026-09-17 after the Gate 4
  review round 2 found S2's file map omitted packaging (`pyproject.toml`, dependency
  lock, `demos/`, clean-env install test). Revisions applied the same day (S2 file
  map + S6 test 51); the earlier approvals and the first backtrack remain the
  historical record.
- Gate 3 — Program Design: RE-APPROVED a second time by the user on 2026-09-17 after
  reviewing the packaging revision. This released queued Gate 4 revision round 2
  (G4-01/03/04/05/07/08 fixes plus S11 decisions 5–6), now applied to
  `04-slices.md`. Approval covers `03-program-design.md` only; it does not approve
  Gate 4, and does not authorize implementation, installs, credentials, spike runs,
  commits, deployment or outreach.
- Gate 3 — Program Design: consistency correction (user-directed, 2026-09-17, during
  the Gate 4 review round 3) — the provisional Python bound in S2 was tightened from
  `>=3.11,<3.14` to `>=3.12,<3.14` (test 51 would otherwise carry an unintended
  Python 3.11 support obligation), and the document header now records the second
  backtrack/re-approval it had omitted. Approval state unchanged.
- Gate 4 — Vertical Slices: approved by the user on 2026-09-17 after three review
  rounds the same day (independent review BLOCK with G4-01–G4-08; fixes applied;
  follow-up REVISE with three consistency corrections; corrections applied; no
  remaining blocking defect found in the 17-slice sequence). Approval covers the
  17-slice build order in `04-slices.md` and authorizes slice work one at a time
  under its S10; it does not authorize installs, dependencies, credentials,
  external services, spike runs, deployment, outreach or ADR #4.
