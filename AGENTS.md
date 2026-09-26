# Shiftwork: project and execution instructions

These instructions combine Shiftwork's product constraints with the repository's
execution rules. Project authority and evidence boundaries always take precedence
over generic workflow convenience.

## 1. Operating principles

- Honesty, accuracy and epistemic humility matter more than agreeableness. Never
  invent numbers, quotes, sources, test results, adoption evidence or tool state.
- Lead with the answer. Be brief. Explain complex choices in short, concrete steps
  suitable for a reader who benefits from extra structure and low cognitive load.
- For layman-terms or ADHD-friendly explanations of tasks, decisions, reviews or
  technical findings, invoke the user-level `layman-explain` skill
  (`C:/Users/jayd0/.qoder/skills/layman-explain/SKILL.md`) and follow its shape:
  one everyday sentence for what the thing is, literal examples with real values,
  scannable bullets and tables, no abstract or poetic framing, and the concrete
  ask stated last.
- Push back when the user's logic is weak. Lead with blockers, falsifiers, failure
  modes and uncertainty instead of softening a critique.
- Prefer the simplest complete solution. Find the root cause, change the narrowest
  responsible layer and avoid temporary fixes, unnecessary abstractions and side effects.
- Challenge non-trivial work before presenting it: is there a simpler or more
  coherent solution, and would a senior reviewer accept the evidence?
- The latest explicit user instruction overrides older notes. Never infer approval
  for implementation, external services or a later software-factory gate.

## 2. Read order and authority

Before working on Shiftwork, read:

1. `HACKATHON_REQUIREMENTS.md` — official-rule checklist; keep product opinions out.
2. `docs/SHIFTWORK_PLAN.md` — current direction, adjudication, hypotheses, risks
   and evidence plan.
3. `docs/plans/shiftwork/00-status.md` and every existing file beneath that folder
   — approved software-factory decisions, mockups, evidence and actual gate state.
4. `C:/Users/jayd0/.agents/skills/software-factory/SKILL.md` when the task concerns
   a product gate, feature, architecture, program design, slice plan or implementation.
5. `MISTAKES.md` — logged agent errors, root causes and prevention rules. Check
   before working to avoid repeating known mistakes.
6. `docs/HATCHERY_PLAN.md` and `docs/plans/hatchery/` only when historical context
   or an imported Hatchery mechanism is relevant. Hatchery is not active scope.

Approved gate documents supersede provisional choices in `docs/SHIFTWORK_PLAN.md`.
When a gate changes a durable decision, update the supporting brief so the documents
remain consistent. Current official rules and primary sources supersede stored
summaries when a time-sensitive external claim is being made.

## 3. Current direction and authorization

- **2026-09-24 current authority:** Gate 1 is RE-APPROVED after the final-pivot
  backtrack. The user approved the revised product and six plain HTML mockups
  without human sessions, and authorized publishing `shiftwork/slice-10`, merging
  and pushing main, then proceeding through Gates 2 to 4. Publication and merge
  are complete (`821a24c` on main). Gate 2 was re-approved and committed as
  `f048949` and `3799dfc`, then backtracked on 2026-09-24: a closed v5 shift
  with no selection had no path to make its first choice. The user explicitly
  re-approved the revised Gate 2 architecture and requested Gate 3. Gate 3's
  prior re-approval and commit `de250b9` remain historical. The user separately
  re-approved the reconciled Gate 3 working tree; `aedc97f` and `ab5ab9c` were
  committed without co-author footers and fast-forwarded to local main, without
  a push. Gate 4 review then found that Northline could not qualify an edited
  version for selection or operation because Gate 3 loaded Bellwether-only
  comparison workloads. Gate 3 was backtracked for that scoped correction, and the
  user then approved Gate 3 and Gate 4 together, asked for a final gap check and
  authorized committing and pushing both to main without a co-author footer. All
  four gates are now approved. The gap check was static only and repaired four
  documentation defects; no runtime, install, credential, external call or human
  session followed. Gate 4 approval authorizes planning one slice at a time, not
  implementation: each slice still needs its own explicit go-ahead, and installs,
  credentials, external calls, the capability spike, fixture authoring,
  sealed-case contents, outreach, deployment, publication, submission and ADR #4
  each remain separately authorized. Slice 10 is accepted and merged to main as
  `f0a1e81..0432cbd`, pushed 2026-09-25. Slice 11 is accepted (2026-09-26), pushed
  on `shiftwork/slice-11` as `add85b1..6832486`, and merged to main as
  `36adbf4..973f5ce` on 2026-09-26. Gate 2 and Gate 3 carry a documentation-only
  credential-name correction that the user re-approved on 2026-09-26: the stale
  `CONTREE_SESSION` name is replaced by the documented `CONTREE_TOKEN`,
  `CONTREE_PROJECT` and `NEBIUS_AI_PROJECT` aliases, with `NEBIUS_PROJECT_ID` in
  the Gate 3 configuration list. Slice 12 received its own go-ahead on 2026-09-26
  on `shiftwork/slice-12`. Its live entitlement preflight initially used the
  wrong `Project` header; the support-provided AI project ID now returns all
  Sandbox permissions true. The partial live matrix then stopped on a successful
  operation whose checkpoint silently lacked a reported file write. Slice 12 is
  unchecked; Gate 2's scoped file-readback rule and Gate 3's matching
  program-design correction were separately re-approved 2026-09-26. S13 onward
  stays stopped. One separately authorized no-inference Sandbox diagnostic then
  read back a 14-byte checkpoint file exactly under the normal 16 MiB cap, but
  the earlier 2 MiB loss under a 1 MiB cap remains unexplained. Neither gate
  approval nor that one-pass result establishes a live capability verdict or
  authorizes further probes.
  Do not implement the pivot under historical approvals.
- Approved product focus: evidence-led diagnosis of a real AI service, a short cause and
  falsifier before diagnostic help, fair repair comparisons, explicit selection of
  the exact tested version and inherited operational consequences. Experiments,
  selection and operation are separate; later testing of the retained alternative
  must not rewrite history. Keep the selected room and completed foundation.
- Current pivot forecast: 32/40 assuming competent delivery, not today's build,
  measured learning or predicted judging. Verdict: revise, then pursue. No automatic
  score increase for refinements and no claim of a proven exclusive category.
- The external software-factory guide was unavailable during the initial
  2026-09-24 revision. It was subsequently loaded through the `software-factory`
  skill in the same-day approval session; no replacement was installed. Follow
  that guide and the explicit repository gate rules.
- The following pre-pivot approval history retains its original scope. The Gates 2
  to 4 pivot reconciliation is complete, so nothing below authorizes pivot slice
  work; that follows the approved `04-slices.md` and its per-slice go-ahead.
- Pre-pivot gate state: Gate 1 - Product RE-APPROVED 2026-09-18 (first approved
  2026-09-15; backtracked and revised the same day for the explicit junior applied
  AI engineer role framing and the selected isometric operational-room visual
  direction); Gate 2 - Architecture RE-APPROVED 2026-09-19 after the scoped
  backtrack (originally APPROVED 2026-09-15; orchestration-owned sealed loading
  and pure evaluator inputs explicitly approved); Gate 3 - Program Design
  RE-APPROVED 2026-09-19 after the scoped fourth backtrack for
  loader/signature/call-stack, purity/import checks and opaque-ref/public-identity
  projection reconciliation; the user approved the revised document in chat. Prior
  Gate 3 approval history: APPROVED
  2026-09-17 (re-approved a second time after the S2 packaging backtrack -
  `pyproject.toml`, `requirements.lock`, `demos/`, test 51; history: first backtrack
  re-approved 2026-09-17, originally approved 2026-09-16; BACKTRACKED a third time
  2026-09-18, scoped to one S5.6 sentence: the independent Slice 5 review found
  "never `expected_ref`" contradicted test 13's opaque-ref assertion, and the
  reconciled wording permits `expected_ref` only as the opaque `sealed:` digest
  with no behavior change; RE-APPROVED a third time 2026-09-18; the plain
  HTML/CSS/vanilla-JS client baseline is unchanged, and framework or rendering
  engine changes are outside this Gate 3 backtrack); Gate 4 - Slice Plan
  RE-APPROVED 2026-09-19 after the scoped reconciliation revision (first approved
  2026-09-17 after three review rounds; the 2026-09-18 reopen was scoped to the
  rewritten Slice 9 to 11 requirements; the 2026-09-19 revision re-homed the revised
  test 11/13/17 runtime checks and the audit's Slice 6 gaps, added snapshot pairing to
  Slice 7, restart recovery to Slice 8, prompt/real-provisioning mapping to Slices
  12/14 and the affected-ADR check to slice completion; the user approved it in chat
  on 2026-09-19; a same-day follow-up revision (Slice 7 leak-response invalidation;
  Slice 10 scoring-input alignment; Slice 6 repair scope unchanged) was approved by
  the user in chat on 2026-09-19.
  Slice work proceeds one slice at a time under `04-slices.md` S10; installs,
  credentials, external services, spike runs, deployment, outreach and ADR #4 remain
  separately authorized). Slices 1 (tracer bullet, 2026-09-17),
  2 (thin real vertical path, 2026-09-18) and 3 (recorded/local_process executor
  conformance, 2026-09-18) are implemented, reviewed and merged to main; verbatim
  Slice 3 evidence is recorded in `docs/plans/shiftwork/00-status.md`. Slice 4
  (contract-parameterized evaluator + first sealed family, 2026-09-18) is
  implemented and demonstrated; the user reviewed and sealed the six
  `stale_information` cases as-is on 2026-09-18. Slice 5
  (reducer + hash chain + idempotent finalization, 2026-09-18) is
  implemented and demonstrated; its independent review's fixes (a failing-capable
  chain-linkage test, route-level BROKEN 409 tests, corrected deferral and
  snapshot wording) landed the same day. Slice 6 (isolation and leakage
  hardening) was repaired 2026-09-19: its four previously invisible injected faults
  and two probes now each fail the suite, and the same-day adversarial review round
  reproduced those rows and resolved its MAJOR-1 (error responses scanned),
  MINOR-1/2/3 items (containment normalization, import-guard forms plus a
  sealed-path rule, scanner decoder coverage) and the NITs, each with a
  failing-capable proof (evidence in the 00-status Slice 6 repair and review-round
  sections); a fresh-session independent re-review returned PASS on 2026-09-19
  (fourteen probes each failing the named guard and restored content-identically;
  suites and demos reproduced verbatim; evidence in the 00-status Slice 6 re-review
  and acceptance section), and the user's same-day instruction accepted the slice.
  Test 19's pinned map is supported; the tests 16-18, 20 and 45 gaps are closed and
  re-verified.
  Prompt/assist and real-sandbox surfaces remain deferred to Slices 12/14; future
  stimuli require Slice 7. Exact remaining clause ownership was reconciled and
  re-approved at Gate 4 (2026-09-19), not silently treated as delivered. The removal of the sealed
  `CheckResultView.check_id` is retained; ledger `check_id` values are public result
  IDs, not sealed identities. Numbered sealed IDs expose identity/numbering, not
  necessarily the entire inventory size. Slice 7 (budget + rotation + incidents +
  repair) is implemented and demonstrated, its report adjudication's findings
  repaired with failing-capable proofs, and its evidence recorded in
  `00-status.md` (2026-09-20). Slice 8 (close and inheritance restoration, restart
  reconciliation and the Test 1 offline pre-proof) is implemented and merged to
  main (`8032aaf`, 2026-09-20). Slice 9 (client isometric room shell plus board and
  customer-shift stations) is implemented on `shiftwork/slice-9` (2026-09-21), its
  independent review round adjudicated and repaired, its post-slice cleanup scan
  recorded, and it is merged to main (`4d5539a`, 2026-09-21, fast-forward) and
  pushed, with the user's visual acceptance marked by that merge. Under this
  pre-pivot numbering Slices 10-17 were not implemented, and that numbering is
  historical. Under the approved pivot, Slice 10 (v5 history to v6 with no
  invented choice) is implemented, was accepted by the user on 2026-09-25 and is
  merged to main as `f0a1e81..0432cbd` and pushed; Slices 11-25 are not
  implemented.
  Gate 2, Gate 3 and Gate 4 are re-approved; all scoped backtracks are closed. The
  Gate 4 reconciliation revision is approved; a same-day follow-up revision (Slice 7
  leak-response invalidation; Slice 10 scoring-input alignment) was approved by the
  user in chat on 2026-09-19. Slice 6 is repaired, re-reviewed PASS and accepted
  (2026-09-19); the review round's findings were resolved the same day. The revised
  test 11/13/17 clauses are specifications, not new passing evidence; Gate 4 mapped
  their current-runtime checks into the Slice 6 repair and preserved later
  prerequisites (re-approved 2026-09-19). ADR reconciliation is recorded (2026-09-19; see `docs/adr/`); ADR #4 still
  requires Slice 13 evidence and separate authorization. Test 50 is partial (offline
  environment clauses only); test 29 is explicitly skipped until Slice 14. The
  2026-09-19 audit excluded packaging test 51 because installs were prohibited;
  its full-suite claim remains unverified. This is a trusted-fixture execution
  guard, not hostile-code isolation. Current evidence is in `00-status.md` under
  "Slice 6 independent re-review and acceptance: 2026-09-19".
- On 2026-09-15 the user explicitly scrapped Hatchery as the active project and
  selected Shiftwork for software-factory planning. Do not resume Hatchery or
  general idea shopping unless the user explicitly reopens it.
- On 2026-09-15 the user explicitly approved Shiftwork Gate 1 after the
  service-workbench redesign; the requested final independent review later returned
  PASS, and Gate 2 was drafted and approved the same day. On 2026-09-16 the user
  approved Gate 3 after the seven-blocker revision; on 2026-09-17 it was backtracked
  twice (first: test 33 close-semantics and the credential-reachability test; second:
  the S2 packaging file-map omission) and re-approved the same day after each
  revision. On 2026-09-17 the user also approved Gate 4 after three review rounds;
  slice work proceeds one slice at a time under `04-slices.md` S10. Gate backtracking
  follows S5.
- Gate 1 approval does not approve Gate 2, a technology stack, implementation,
  installs, credentials, participant outreach, purchases, external service use,
  deployment, commits or pushes.
- The latest independent verdict before selection was `REVISE SHIFTWORK BEFORE
  ADOPTION`. Selection did not prove the technical, learning, Tavily or organiser-
  dependence claims.
- Historical pre-pivot forecast: 27/40; pre-evidence cap: 31/40; conditional best
  case: 35/40, with Potential Impact capped at 4.0 without stronger evidence.
  These are prior subjective forecasts, not current caps or achieved scores; the
  final-pivot forecast above does not establish learning gain or prize merit.

## 4. Product definition and scope filters

- Shiftwork is a persistent applied-AI-engineering learning environment. A learner
  is cast explicitly as a junior applied AI engineer on shift and keeps one real
  system working for a fictional client across successive shifts; later shifts
  inherit the learner's artifact, decisions, incidents and business state.
- Primary job: applied-AI-engineering education for people with basic coding
  knowledge. The engineer role is fiction that makes the work legible, not a
  credential. Employer proof is not a current claim and the simulated title is never
  presented as job-readiness.
- Initial scope: one applied-AI-engineer role and two client engagements (Bellwether
  Books, then the Northline Bike Cooperative away shift). The learner defines the
  correctness contract, makes architecture and repair decisions, and owns visible
  tests. The role framing is the intended scalability seam: further engagement packs
  for emerging roles people rarely see simulated (for example forward deployed
  engineer, GTM engineer) are recorded as future scope only. Do not expand to
  multiple careers, a large town or an employer marketplace before the central
  mechanism survives its tests.
- Approved central mechanic under the Gate 1 revision: the learner explains an
  AI-service failure, tests a falsifiable prediction, compares code repairs under
  shared requirements and conditions, and explicitly selects an eligible tested
  version. Only operating that version creates independently checked synthetic
  ledger consequences; neither experiments nor later alternative trials rewrite
  operational history. Saving another candidate does not change inheritance.
- Require answers to address the customer's task, not just cite true facts. Reject
  mandatory correctness/safety failures before efficiency comparisons; distinguish
  useful completion from refusals and human referrals. Recorded inspection is not
  fresh AI execution, and repeated trials must show variation and missing evidence.
- Build a whole product with persistent objects, repeat usefulness and a visible
  before/after. Do not ship a developer console disguised as a learning product.
- The town is an explanatory layer, not the differentiator. Progress must be caused
  by the learner's working system and inherited consequences, not XP or animation.
- Label synthetic business consequences. Determinism makes them reproducible, not
  equivalent to real revenue, customer trust, learning impact or employer validation.

### Hatchery mechanisms that may be imported

Import only mechanisms that strengthen Shiftwork's causal learning loop:

- versioned artifacts, branchable practice and retained incident history;
- independently authored sealed acceptance cases and regression checks;
- one necessary correction preventing a later unseen failure;
- separation of factual updates from procedural failures;
- useful scaffolding before asking the learner to teach or correct;
- immutable evaluator, credential, promotion and permission boundaries; and
- visible remaining limits and reduced-assistance transfer to a fresh setting.

Exclude Hatchery's household-assistant product, AI pet, XP, automatic permission
growth, background personal automation and decorative practice worlds.

## 5. Required software-factory process

Use `C:/Users/jayd0/.agents/skills/software-factory/SKILL.md` for product work.
Workflow documents live in `docs/plans/shiftwork/`; `docs/SHIFTWORK_PLAN.md` is a
supporting brief, not a substitute for the four gate documents.

1. Product
2. Architecture
3. Program Design
4. Vertical Slice Plan

Rules:

- Write and review each gate separately. Obtain explicit approval at every gate.
- Resume from the first unapproved gate in `00-status.md`. Do not redo an approved
  gate unless the user requests it or later evidence invalidates it.
- Gate 1 contains the user problem, measurable success, short announcement and
  plain HTML screen mockups. Keep implementation choices out of Gate 1.
- For Gate 1 UI, create one plain `.html` file per screen with no framework or
  build step. More generally, create visualization files as `.html`, never `.tsx`.
- At a Gate 1 approval or re-approval pause, ask exactly:
  `Approve Gate 1, or what should change?`
- No implementation code may exist before Gate 4 approval. Direction selection,
  context updates, research and evidence plans are not gate approval.
- Record approvals and completed slices in `00-status.md`. If later work exposes a
  concrete earlier-gate error, stop, backtrack that gate, revise it and obtain
  explicit re-approval.
- After Gate 4 approval, implement one vertical slice at a time. Each slice must end
  in a visible, working, testable result; record the evidence before continuing.
- After each slice, show the actual result, update `00-status.md`, then invoke the
  `architect-reviewer` skill (post-slice cleanup mode) to scan for stale or redundant
  files before asking whether to continue or re-steer. Do not build horizontal layers
  that cannot run end to end.
- Documentation-only maintenance, instruction consolidation and other small changes
  that do not alter product behavior do not create a new product gate.

## 6. Execution discipline

### Before editing

- Inspect `git status`. Treat existing changes as the user's work unless proven
  otherwise. Never stash, discard, rewrite or stage unrelated changes.
- For a non-trivial task outside the gate workflow, write a short actionable plan
  before editing. Re-plan when evidence invalidates the approach. Skip process
  ceremony for a small, obvious, one-file change.
- Establish a baseline proportional to risk. For implementation, run the relevant
  existing checks before changing behavior when practical and record pre-existing
  failures. Documentation-only changes do not require a full test suite.
- Do not install tools or dependencies merely because they are missing. Record the
  unavailable check unless the user has authorized installation.

### While working

- Keep the change inside the user's requested scope and preserve existing behavior
  outside it. Once the applicable gate authority exists, fix in-scope bugs directly
  from logs, failing tests and reproducible evidence instead of asking for step-by-step
  guidance.
- After a user correction, revise the active plan and any in-scope durable decision
  record that would otherwise repeat the mistake. Do not create generic lessons files
  or widen the diff merely to document a correction.
- Use subagents only when the user explicitly requests them or the active runtime
  policy allows them, and only for bounded, independent work. Give each agent one
  focused task. A second LLM is never an independent oracle for correctness.
- Prefer non-interactive commands. Never launch an editor, interactive rebase,
  login flow or confirmation prompt during an unattended run.
- On Windows/PowerShell, prefer `rg`, `Get-Content`, `npm.cmd` and `npx.cmd`. Do not
  assume `rtk` exists or that PowerShell permits `.ps1` npm shims.
- Run repository checks with `.venv313/Scripts/python.exe`. The `.venv` trampoline
  is blocked by Windows Application Control on this machine, and installs into a
  fresh venv need `uv pip install --link-mode=copy` because the tree is OneDrive-synced
  (see `MISTAKES.md`, 2026-09-26).
- Do not create branches, commits, tags or pushes unless the user has authorized
  that Git operation. Never stage everything implicitly.
- Before starting work on each slice, check the current branch with
  `git branch --show-current`. If the branch name does not match the slice being
  started, create and switch to a branch named `shiftwork/slice-N` where N is the
  slice number. Do not begin slice implementation on main or on a branch for a
  different slice.
- Commit in coherent batches, never one bulk snapshot. When committing or
  publishing a branch, stage one concern at a time (roughly a few related files
  per commit, for example five files out of thirty) and give each commit a
  specific message naming what changed and why. One commit covering an entire
  slice with a generic message such as "implement slice 1" is not acceptable;
  several focused, reviewable commits with meaningful messages are the standard.
- Do not modify CI, lint configuration or lockfiles unless the task requires it.
- Never store secrets, tokens or credentials in repository notes or logs.
- Do not use em dashes whatsover, or S. It should be S1 for example instead of S

### Context budget and handoff

- Treat half of this session's context window as the working limit (for example
  200k of a 400k-token window). Use the reported usage indicator when the runtime
  shows one, and a conservative estimate otherwise. When usage reaches about that
  point, stop starting new work even if the task is unfinished.
- Do not run the session on to automatic compaction. Finish only the current step
  and leave it at a safe point: the tree consistent, no half-applied edits and no
  unrecorded failing results.
- In the same reply, give the user one copy-pasteable continuation prompt in chat
  for a fresh session. Invoke the `transfer-context` skill when it is available;
  otherwise write an equivalent single fenced block headed `Prompt for New Chat`
  that carries the task and its constraints, what is done and verified, the exact
  files touched, decisions and rejected alternatives, traps and open questions,
  and the next concrete step.
- Report the halt and the approximate usage in one line, then stop until the user
  runs that prompt in a new session. Only an explicit user instruction extends a
  session past this limit.

### Mistake logging

- After making a coding error (broken build, failed test, wrong output, reverted
  change), append an entry to `MISTAKES.md` with: what happened, root cause, and a
  prevention rule.
- Before starting work, scan `MISTAKES.md` for entries relevant to the current task
  and follow their prevention rules.
- When a failure pattern repeats 4+ times, graduate it from `MISTAKES.md` into a
  permanent rule in this file. Graduated entries stay in `MISTAKES.md` as incident
  history unless the user asks for their removal.

### Verification

- A step is complete only when its result matches the request and the relevant
  tests, build, lint, type checks or rendered output have been verified in proportion
  to the change's risk.
- Tests must be capable of failing against the broken or pre-change behavior. Never
  delete, skip, weaken or silence a check merely to obtain green output.
- Prove coverage, do not count it. A check that names every input it tries is not
  evidence that every guard branch fires: mutate each branch independently and
  require one real failure per branch, and treat a fault two checks can both catch
  as proof of neither.
- For every absence or leak assertion, prove the needle can match the surface as
  serialized, not as held in memory. Add a scanner self-test that injects the needle
  into a representative serialized surface and requires detection. A count of
  surfaces scanned is not evidence that any individual needle is capable of failing.
  On Windows a JSON response backslash-escapes absolute paths, so path needles must
  be checked in raw, unescaped and forward-slash forms.
- If a test is invalid, explain why and preserve the evidence. If it fails once and
  passes on rerun, report it as flaky; do not treat one rerun as clean proof.
- For implementation, run focused checks while iterating and the relevant full suite
  before final completion. Compare with the baseline; any new failure is yours.
- Inspect the final diff for accidental scope, secrets, generated noise and line-
  ending damage. Run `git diff --check`.
- For local previews, report the actual URL and port. For UI, inspect representative
  desktop and mobile views rather than relying on CSS values alone.

## 7. Long unattended runs

Apply this section only when the user explicitly asks for work to run without them
watching. Do not create `PROGRESS.md` for short interactive work or small edits.

### Progress state

- If `PROGRESS.md` exists for the active task and contains unchecked work, read it
  fully, re-verify the last completed step and resume from the first unchecked step.
  Do not restart completed work.
- Otherwise create `PROGRESS.md` with the goal, dependency-ordered checklist,
  relevant dirty-worktree state and a dated run log. Put risky independent checks
  early so blockers surface before broad edits.
- Use `[ ]` for pending, `[x]` for done and verified, and `[!]` for blocked with a
  one-line reason. After each step, record only the facts needed to resume.
- Keep `PROGRESS.md` concise, under roughly 150 lines. Include assumptions, failures,
  exact verification commands, skipped scope and a final Result section.
- `PROGRESS.md` is operational memory only. It may never record or imply a product
  gate approval. `docs/plans/shiftwork/00-status.md` remains authoritative for gates
  and slices, and approved gate documents remain authoritative for decisions.
- Never commit `PROGRESS.md` or any other file unless commits are explicitly authorized.

### Autonomy and hard stops

- Execute reversible steps clearly covered by the request without waiting. If a
  harmless ambiguity remains, choose the reading a careful colleague would choose,
  record the assumption and continue.
- If one part is impossible, unsafe or contradicted by evidence, complete independent
  in-scope work and record why that part was skipped.
- Stop for missing authority, destructive or irreversible ambiguity, a required
  product decision, credentials, payment, outreach, deployment, or any software-
  factory approval. Unattended mode never widens authorization.
- After three materially different failed attempts at the same step, record the
  outputs, mark it blocked and move to an independent step. Mark dependent steps
  blocked with the same cause. If no independent work remains, finish with a clear
  blocked result instead of guessing.

### Context and output hygiene

- Treat files as durable context. Update progress after each verified step and before
  a likely compaction so a fresh session can continue without chat history.
- The context budget and handoff rule in Execution discipline applies here as well:
  halt at half the window, update `PROGRESS.md`, and close the final reply with the
  continuation prompt.
- The mandatory read order still applies. After that, prefer targeted line ranges,
  `rg`, quiet test output and tailed logs. Avoid dependency trees, binary dumps,
  lockfile output and redundant full-file reads.
- Do not echo the full plan or progress log into chat. Give concise milestone updates.
- Run servers and watchers in a controllable background session with captured logs;
  record how to stop them and clean them up before completion unless still needed.

## 8. Technology and evidence boundaries for later gates

- Token Factory Sandboxes must execute the learner-owned artifact and produce
  inspectable evidence if sandbox execution is claimed. Public ingress is not
  documented; do not claim it is impossible or available until tested.
- Best Apps and Agents is the current safer primary-track hypothesis. Claim Coding
  and Agentic Engineering only if a Nemotron-powered agent meaningfully writes,
  runs and tests code in Token Factory Sandboxes without erasing learner authorship.
- The final pivot proposes meaningful Nemotron behavior inside the service, such
  as request interpretation and information/tool selection, not merely stakeholder
  dialogue. That change needs Gate 2/3 reconciliation; it is not runtime or
  credential authorization. Ordinary code may replace unnecessary AI subtasks.
- Optional diagnostic help follows the learner's initial cause and falsifier;
  hints and labelled patch proposals stay attributable. The learner owns hypotheses,
  experiment design, code, visible tests, requirements and the final repair choice.
- Nemotron and learner code must not control or read sealed cases, credentials,
  evaluator logic, ledger rules or promotion. A second LLM is not an independent oracle.
- Repeated probing can leak hidden contracts. Plan isolation, holdout rotation,
  attempt limits and raw-trace retention; filesystem hiding alone is insufficient.
- Business consequences must be deterministic reductions from observed outputs.
  Record orders, incidents, refunds and backlog as synthetic scenario state; never
  present them as real commercial outcomes.
- Tavily should discover changes in allow-listed official sources for a reviewed
  mission-curation workflow. A human verifies the primary source before the change
  becomes a frozen executable fixture. Compare frozen sources, known-page polling
  and Tavily discovery. If Tavily only adds prose or links, remove the prize claim.
- Preserve both organiser-dependence interpretations: literal vendor exclusivity
  fails; architectural dependence remains unproven. Measure whether removing
  inference or isolated execution materially weakens learner outcomes.
- Compare Shiftwork with a strong static tutorial at matched time, tests and hint
  budget. Measure reduced-assistance transfer, learner authorship and voluntary return.
- Actual Token Factory access, available Nemotron models, Tavily access, costs,
  latency and runtime compatibility remain unverified. No API keys are needed at Gate 1.

## 9. Adjudication warnings and proof boundaries

- KodeKloud Engineer is a direct professional-simulation precursor. DeployU, FDE,
  TENTROPY, Forage, Bitburner and Screeps cover other major components. Treat the
  combined causal-persistence gap as a hypothesis, not verified uniqueness.
- Lack of documented Sandbox public ingress does not prove that an internal request
  harness cannot exercise a service. Prove the exact loop with a bounded spike later.
- Nebius documents endpoint creation on a minutes-scale; never storyboard a literal
  20-second public deployment without measured evidence or a time-compression label.
- Employer proof requires employer acceptance. Sealed synthetic tests do not provide it.
- The three justification tests are proof slices after Gate 4 approval, not permission
  to bypass the gates: central mechanism, reduced-assistance transfer, Tavily ablation.

## 10. Repository history and closed directions

- Protect all unrelated dirty-worktree changes. Current authorization does not include
  installs, commits, pushes, purchases, participant outreach or deployment.
- Hatchery's files remain historical evidence and a mechanism donor. Its Gate 1 was
  stopped unapproved when the user selected Shiftwork on 2026-09-15.
- Treat Celeste, Aster, GRAFT/FormSwitch, Statement, Doc Rot Hunter and the other
  rejected detector, migration, code-health and generic-assistant directions as closed.
