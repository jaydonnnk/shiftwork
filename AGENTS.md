# Shiftwork: project and execution instructions

These instructions combine Shiftwork's product constraints with the repository's
execution rules. Project authority and evidence boundaries always take precedence
over generic workflow convenience.

## 1. Operating principles

- Honesty, accuracy and epistemic humility matter more than agreeableness. Never
  invent numbers, quotes, sources, test results, adoption evidence or tool state.
- Lead with the answer. Be brief. Explain complex choices in short, concrete steps
  suitable for a reader who benefits from extra structure and low cognitive load.
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

- Current gate state: Gate 1 — Product APPROVED 2026-09-15; Gate 2 — Architecture
  APPROVED 2026-09-15; Gate 3 — Program Design APPROVED 2026-09-17 (re-approved a
  second time after the S2 packaging backtrack — `pyproject.toml`, `requirements.lock`,
  `demos/`, test 51; history: first backtrack re-approved 2026-09-17, originally
  approved 2026-09-16); Gate 4 — Slice Plan APPROVED 2026-09-17 (after three review
  rounds the same day; slice work proceeds one slice at a time under `04-slices.md`
  S10; installs, credentials, external services, spike runs, deployment, outreach
  and ADR #4 remain separately authorized). Slices 1 (tracer bullet, 2026-09-17),
  2 (thin real vertical path, 2026-09-18) and 3 (recorded/local_process executor
  conformance, 2026-09-18) are implemented, reviewed and merged to main; verbatim
  Slice 3 evidence is recorded in `docs/plans/shiftwork/00-status.md`. Test 50 is partial
  (offline environment clauses only); test 29 is explicitly skipped until Slice 14.
  This is a trusted-fixture execution guard, not hostile-code isolation. Slices
  4-17 are not implemented.
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
- Current forecast: 27/40; defensible pre-evidence cap: 31/40; conditional best
  case: 35/40. These are subjective forecasts, not achieved scores. No capability,
  learning gain, prize merit or working central mechanism has been demonstrated.
  Potential Impact remains capped at 4.0 without stronger evidence.

## 4. Product definition and scope filters

- Shiftwork is a persistent applied-AI-engineering learning environment. A learner
  keeps one real system working for a fictional business across successive shifts;
  later shifts inherit the learner's artifact, decisions, incidents and business state.
- Primary job: applied-AI-engineering education for people with basic coding
  knowledge. Career exploration is context. Employer proof is not a current claim.
- Initial scope: one role and one bookshop engagement. The learner defines the
  correctness contract, makes architecture and repair decisions, and owns visible
  tests. Do not expand to multiple careers, a large town or an employer marketplace
  before the central mechanism survives its tests.
- Central mechanic: a learner's versioned service receives fixed customer requests;
  independently authored checks reduce its real outputs into an append-only,
  transparent business ledger that the next shift must inherit.
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
- After each slice, show the actual result, update `00-status.md`, and ask whether
  to continue or re-steer. Do not build horizontal layers that cannot run end to end.
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
- Do not create branches, commits, tags or pushes unless the user has authorized
  that Git operation. Never stage everything implicitly.
- Commit in coherent batches, never one bulk snapshot. When committing or
  publishing a branch, stage one concern at a time (roughly a few related files
  per commit, for example five files out of thirty) and give each commit a
  specific message naming what changed and why. One commit covering an entire
  slice with a generic message such as "implement slice 1" is not acceptable;
  several focused, reviewable commits with meaningful messages are the standard.
- Do not modify CI, lint configuration or lockfiles unless the task requires it.
- Never store secrets, tokens or credentials in repository notes or logs.
- Do not use em dashes whatsover, or S. It should be S1 for example instead of S

### Mistake logging

- After making a coding error (broken build, failed test, wrong output, reverted
  change), append an entry to `MISTAKES.md` with: what happened, root cause, and a
  prevention rule.
- Before starting work, scan `MISTAKES.md` for entries relevant to the current task
  and follow their prevention rules.
- When a failure pattern repeats 4+ times, graduate it from `MISTAKES.md` into a
  permanent rule in this file and remove the log entry.

### Verification

- A step is complete only when its result matches the request and the relevant
  tests, build, lint, type checks or rendered output have been verified in proportion
  to the change's risk.
- Tests must be capable of failing against the broken or pre-change behavior. Never
  delete, skip, weaken or silence a check merely to obtain green output.
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
- Nemotron may provide bounded stakeholder dialogue, scaffolding after the learner
  commits to an approach, requested hints, failure diagnosis and labelled patch
  proposals. The learner owns requirements, tradeoffs, visible tests and repair direction.
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
