# Shiftwork — working brief and adjudication register

Updated: 2026-09-19.

**State:** selected by the user as the sole active hackathon direction.
**Gate state:** Gate 1 — Product RE-APPROVED 2026-09-18 (first approved 2026-09-15;
backtracked and revised the same day for the explicit junior applied AI engineer
role framing and the selected isometric operational-room visual direction); Gate 2 -
Architecture RE-APPROVED 2026-09-19 after the scoped backtrack (originally APPROVED
2026-09-15; orchestration-owned sealed loading and pure evaluator inputs explicitly
approved); Gate 3 - Program Design RE-APPROVED 2026-09-19 after the scoped fourth
backtrack for loader/signature/call-stack, purity/import checks and opaque-ref/
public-identity projection reconciliation; the user approved the revised document
in chat.
Prior Gate 3 history: APPROVED 2026-09-17 (re-approved a second time after the S2
packaging backtrack - `pyproject.toml`,
`requirements.lock`, `demos/`, test 51; history: first backtrack re-approved
2026-09-17, originally approved 2026-09-16; BACKTRACKED a third time 2026-09-18,
scoped to one S5.6 sentence after the independent Slice 5 review found "never
`expected_ref`" contradicted test 13's opaque-ref assertion; the reconciled
wording permits `expected_ref` only as the opaque `sealed:` digest, no behavior
change, RE-APPROVED a third time 2026-09-18); Gate 4 — Slice Plan RE-APPROVED
2026-09-19 after the scoped reconciliation revision (first approved 2026-09-17; the
2026-09-18 reopen was scoped to the rewritten Slice 9 to 11 requirements; the
2026-09-19 revision moved the revised test 11/13/17 checks into the Slice 6 repair,
added snapshot pairing to Slice 7, restart recovery to Slice 8, prompt/real-provisioning
mapping to Slices 12/14 and the ADR check to slice completion; a same-day follow-up
revision assigns the leak-response invalidation to Slice 7 and the remaining
scoring-input alignment to Slice 10, and was approved by the user in chat on
2026-09-19). Gate 2's ownership revision
and Gate 3's fourth-backtrack revision were re-approved by the user on 2026-09-19;
both scoped backtracks are closed. Gate 4's scoped revision was re-approved by the
user on 2026-09-19; the approvals do not authorize implementation during this hold. Slice 6's repair is implemented 2026-09-19
and the same-day adversarial review round's findings are resolved (error-response
scanning, containment normalization, import-guard forms plus a sealed-path rule,
scanner decoder coverage; see the 00-status repair review-round section);
a fresh-session independent re-review returned PASS on 2026-09-19 (fourteen probes
each failing the named guard with content-identical restores; suites and demos
reproduced verbatim), and the user's same-day instruction accepted the slice.
Slice 7 is in progress on `shiftwork/slice-7`.
The approved ownership split is controller orchestration -> sealed loader ->
cases passed to pure evaluation, not evaluator-owned file loading. ADR 0001
supersession and the ADR 0002/0003 implementation-status notes were recorded
2026-09-19 after the gate decisions.
With the gates re-approved, slice work proceeds under `04-slices.md` S10;
credentials, installs, spike runs, external services, deployment, outreach and
ADR #4 each remain separately authorized. Backtrack an earlier gate only for a concrete blocker.
Slices 1 (tracer bullet, 2026-09-17), 2 (thin real vertical path, 2026-09-18) and
3 (recorded/local_process executor conformance, 2026-09-18) are implemented,
reviewed and merged to main; verbatim Slice 3 evidence is recorded in
`docs/plans/shiftwork/00-status.md`. Slice 4 (contract-parameterized evaluator
and the first sealed family) is implemented and demonstrated, and the user
reviewed and sealed the six `stale_information` cases as-is on 2026-09-18.
Slice 5 (reducer, hash chain, idempotent
finalization, ledger hardening) is implemented and demonstrated 2026-09-18; an
independent review returned 2 MAJOR and 2 MINOR findings plus a Gate 3 wording
escalation, and all fixes landed the same day (evidence in `00-status.md`).
Slice 6's completion/coverage claims were rejected on
2026-09-19: four deliberately introduced provisioning/projection/client faults
passed all 133 authorized tests, and stdout/import probes exposed further test
blind spots. These are injected faults, not observed leaks in the restored app.
The repair and the adversarial review round resolved the findings, and an
independent re-review returned PASS on 2026-09-19; Slice 6 is accepted and
Slice 7 is in progress. The original report is historical.
**Latest verdict before selection:** `REVISE SHIFTWORK BEFORE ADOPTION`.
**Evidence state:** the Slice 2 thin real path remains (canonical hashing, one
recorded replay, one sealed case scored, one hash-chained ledger event). Slice 3
adds real loopback trusted-fixture execution, seven-case replay/local conformance,
exact-byte artifact guards and a pinned child environment. Capture-time equality
uses an injected clock, not equal measured performance. Tests 28, 30 and 31 land;
test 50 is partial (offline environment/log clauses only), and test 29 is explicitly
skipped until Slice 14. This is not hostile-code isolation. Slice 4 adds the
contract-parameterized offline evaluator and completes the six-variant
`stale_information` sealed family; tests 11-15 and 42 land fully and the test 44
evaluator clause completes. The user sealed those six cases on 2026-09-18;
further agent-authored acceptance cases still require user review. Slice 5 ledger
hardening is implemented; Slice 6 is repaired, re-reviewed PASS and accepted
(2026-09-19; fourteen-probe re-review with suites and demos reproduced), and
Slice 7 is in progress. The 2026-09-19
audit verified 133 passing tests and one skip with packaging excluded because
installation was prohibited, not a full-suite result. No Token Factory Sandbox
execution, learner study, transfer result, Tavily ablation, prize merit or score
is demonstrated.
**Working forecast:** current 27/40; pre-evidence cap 31/40; conditional best
case 35/40. Potential Impact remains at most 4.0 in that best case.

This supporting brief holds research, technical hypotheses and evidence boundaries.
It is not a gate approval or implementation specification. Approved documents in
`plans/shiftwork/` supersede provisional choices here.

## 1. Product thesis

Shiftwork is a persistent applied-AI-engineering learning environment for people
with basic coding knowledge. The learner is cast explicitly as a **junior applied AI
engineer on shift** and maintains one real service for a fictional client across
successive operational shifts. Later shifts inherit the learner's artifact,
decisions, incidents and business state rather than resetting into an unrelated
exercise.

Primary job: **applied-AI-engineering education**. The engineer role is the fiction
that makes the work legible, not a credential. Employer proof is excluded until an
employer or credible external reviewer accepts the evidence, and nothing may present
the simulated title as job-readiness.

Initial scope: one applied-AI-engineer role and two client engagements (Bellwether
Books, then the Northline Bike Cooperative away shift). The learner must
make meaningful decisions about what the service must get right, how it should
handle uncertainty, how it should be tested, and how an observed failure should
be repaired. A town may make inherited state legible, but it is not differentiation.

Future scope, recorded but not built: the role framing is the scalability seam.
Further engagement packs for emerging roles people rarely see simulated (for example
forward deployed engineer, GTM engineer) would reuse the same shift loop. Expansion
waits until the central mechanism survives its tests and a new gate decision.

Final central-mechanic hypothesis:

> A learner's versioned service receives fixed customer requests; independently
> authored checks reduce its real outputs into an append-only, transparent business
> ledger that the next shift must inherit.

The consequence is causal only when it comes from the learner's observed service
outputs and fixed rules. An LLM-authored story about what happened does not count.

## 2. What the user decided

- On 2026-09-15 the user explicitly scrapped Hatchery as active scope and selected
  Shiftwork for the software-factory workflow.
- The user asked to retain Hatchery components that strengthen Shiftwork and to
  preserve the independent verdict, bookshop engagement, authority boundary and
  missed risks as durable context.
- At project selection, authorization covered Shiftwork Gate 1 preparation and
  review only; it did not itself approve any gate or authorize implementation,
  installs, paid services, participant outreach, credential use, commits, pushes
  or deployment.
- Later on 2026-09-15, the user explicitly approved Gate 1 after the
  service-workbench redesign, the requested final independent review passed, and the
  user explicitly approved Gate 2 (the architecture document) on 2026-09-15. On
  2026-09-16 the user approved Gate 3 (the program-design document) after the
  seven-blocker revision; implementation, installs, credentials, commits, deployment
  and outreach remain unauthorized.
- On 2026-09-18 the user selected a fixed isometric operational-room composition for
  the Phase B client. `plans/shiftwork/client-visual-direction.md` and its stored
  reference image now define the acceptance target for Slices 9 through 11. The room
  visualizes the existing request-to-output-to-check-to-ledger loop; it does not add
  free-roam gameplay or change the product authority split. The existing plain
  HTML/CSS/vanilla-JavaScript baseline remains unless Gate 3 is explicitly reopened.
  Because the selection rewrote the Slice 9 to 11 requirements in an approved gate
  document, Gate 4 is reopened pending explicit re-approval.
- On 2026-09-18 the user directed that the learner is explicitly cast as a **junior
  applied AI engineer on shift**, with each engagement framed as a fictional client
  (Bellwether Books first, Northline Bike Cooperative away). The role is fiction, not
  a credential: employer proof stays excluded and the simulated title is never
  presented as job-readiness. The user also stated the scalability intent behind the
  role framing: later engagement packs for emerging roles people rarely see simulated
  (for example forward deployed engineer, GTM engineer). That expansion is future
  scope only; shipped scope remains one role and two clients. `01-product.md` and the
  six mockups are revised accordingly, which reopened Gate 1 pending explicit
  re-approval.
- Hatchery remains historical evidence and a mechanism donor. Do not merge the
  household-assistant product into Shiftwork.

## 3. Adjudicated verdict and its limits

The comparison returned `REVISE SHIFTWORK BEFORE ADOPTION`, not an unconditional
win. Shiftwork was favoured because its claimed learning loop is narrower, safer
and easier to falsify than Hatchery's real household automation. The user has now
selected that revised direction, but selection supplies no new evidence.

Reasons Shiftwork still needs proof:

- KodeKloud Engineer, DeployU, FDE, TENTROPY, Forage, Bitburner and Screeps cover
  substantial parts of professional simulation, executable work or persistent
  programming worlds. The complete combination is a hypothesis, not verified novelty.
- Deterministic business state is reproducible simulation, not validated revenue,
  customer trust, employability or educational impact.
- Maintaining an inherited application may teach more deeply, or it may merely
  add maintenance work to a conventional lab.
- The central deterministic lab still works without Nemotron. Its architectural
  contribution must produce measurable learner value rather than decoration.
- No current evidence supports Potential Impact 4.5.

## 4. Hatchery mechanisms retained

Retain:

1. Versioned procedures and artifacts with branchable practice.
2. Independently authored sealed cases and regression protection.
3. A visible correction that prevents a later unseen failure.
4. Separation of factual updates from procedural failures. New stock is data;
   fabricating availability despite the data is a procedural failure.
5. Useful scaffolding before demanding learner correction or teaching.
6. Immutable evaluator, credential, promotion and permission boundaries.
7. Visible uncertainty, limits and provenance.
8. Reduced-assistance transfer to a fresh business.

Exclude:

- the household-assistant audience and workflows;
- pets, XP, competence meters and decorative practice worlds;
- automatic permission growth or self-promotion;
- background personal automation;
- practice whose output never runs against the learner's real artifact.

## 5. First engagement: the bookshop

The learner is responsible for a service that answers customer questions about a
small bookshop's inventory and policies. The engagement should expose real applied-AI
tradeoffs without pretending to reproduce an entire company.

### Learner decisions

1. Define the correctness contract: what must never be wrong, what may be approximate,
   when the service must cite evidence, and when it must refuse.
2. Decide how the service finds and refreshes book and policy information.
3. Choose a structured response contract and an explicit response-time budget.
4. Write visible examples before the first shift.
5. Review customer incidents and choose the repair direction.
6. Decide which repaired component is worth carrying into the next engagement.

### Proposed scenario families

- exact price and availability;
- out-of-stock refusal or alternative;
- returns with an applicable policy exception;
- ambiguous multi-book requests;
- inventory rotation that makes old information stale;
- hostile instructions embedded in catalog or policy content;
- repeat requests and duplicate delivery;
- an explicit response-time budget selected before execution.

### Transparent consequences

The synthetic ledger may record orders completed, incidents opened, refunds
required, unresolved backlog and known limitations. Its weights and transition
rules must be inspectable. Do not claim real money, trust or employer validation.

### Inherited follow-up

The next bookshop shift loads the same artifact, decision record, unresolved
incidents and ledger. A later stock rotation exercises an unseen case from the
corrected failure family. A separate bike-cooperative engagement tests reduced-
assistance transfer with new data and policies.

## 6. Authority boundary — hypothesis for Gate 2 and Gate 3

| Actor | May control | Must not control |
| --- | --- | --- |
| Learner | Requirements, tradeoffs, visible tests, repair direction, deployment choice and reusable extraction | Sealed cases or ledger scoring |
| Nemotron | Bounded stakeholder dialogue from frozen facts, scaffolding after learner commitment, requested hints, failure diagnosis and labelled patch proposals | Credentials, sealed cases, promotion, scoring or self-approval |
| Deterministic evaluator | Requests, sealed suites, reducer, ledger, version gates and mission transitions | Product decisions or generated narrative |
| Operator | Credentials, test secrets, Tavily review/freeze and public deployment | Silent alteration of learner outcomes |

Repeated probing may leak hidden contracts even if files are isolated. Later gates
must address holdout rotation, attempt limits, trace retention and whether learner
code can reach evaluator resources.

## 7. Organiser technology and track fit

Literal vendor exclusivity fails: another model and isolated execution provider
could substitute. Architectural dependence is still a hypothesis.

Working track recommendation: **Best Apps and Agents**. It is the safer fit while
the learner owns the application. Claim **Coding and Agentic Engineering** only if
a Nemotron-powered agent meaningfully writes, runs and tests code in Token Factory
Sandboxes without taking the important decisions away from the learner.

Proposed Nemotron contribution:

- grounded bookshop-owner and customer interaction from frozen facts;
- bounded scaffolding after the learner commits to an approach;
- requested hints and failure diagnosis from actual evidence;
- optional labelled patch proposals that remain learner-selected;
- varied language around canonical scenario intents without owning expected results.

Removing Nemotron must measurably worsen useful completion, feedback quality or
transfer at a comparable budget before architectural dependence can be claimed.

Token Factory Sandboxes are proposed for isolated execution and evidence. Public
ingress is not documented; that does not prove an internal request harness is
impossible. A later bounded spike must establish actual entitlement and behaviour.

## 8. Tavily role

Tavily should operate in a reviewed mission-curation workflow, not directly decide
customer answers or hidden scores.

1. Search allow-listed official product or policy domains for a relevant change.
2. Quarantine retrieved text and treat it as untrusted.
3. A human verifies authority, applicability, freshness and reuse rights.
4. Convert the approved constraint into a versioned, frozen fixture.
5. Run that fixture against the learner's service.

Compare frozen curriculum, polling already-known pages and Tavily discovery. Let
polling retain URLs Tavily already discovered. Tavily earns a serious claim only
when it repeatedly finds applicable constraints the realistic polling baseline
misses, changes executable behaviour, and imposes acceptable review burden.

No Tavily API key is needed until the applicable post-Gate-4 proof slice. Search
links or refreshed prose do not justify the integration.

## 9. Three justification tests

These tests must be specified at Gate 3, sliced at Gate 4 and executed only after
Gate 4 approval.

### Test 1 — central mechanism

Smallest proof: one learner service, one real request batch, one external sealed
suite, one deterministic ledger update, one correction, one unseen related case,
and one restart that preserves artifact and state.

Kill the mechanism if evaluation requires LLM judgement; hidden cases or credentials
are reachable; semantic replays disagree; artifact/state do not carry forward; or
the later consequence is narrated instead of caused by execution.

### Test 2 — reduced-assistance transfer

Compare Shiftwork with a strong static tutorial using matched time, visible tests
and total assistance budget. Use structurally equivalent bookshop and bike-cooperative tasks and
counterbalance their order. Record independently passed cases, time, hints, generated
patch use, learner explanation, learner-authored decisions and voluntary return.

Kill the learning claim if the static tutorial ties or wins; Shiftwork consumes
more time or assistance without better transfer; generated patches cause most
successes; or learners remember the story but cannot explain or repair the system.

### Test 3 — Tavily ablation

Compare frozen sources, polling known pages and allow-listed Tavily discovery.
Record valid new constraints, false positives, review time and executable fixtures
changed. Kill Tavily centrality if it finds nothing useful beyond polling, changes
only prose, lets unverified content affect scoring, or creates more review burden
than manual maintenance. This can kill the Tavily prize strategy without killing Shiftwork.

Gate 3 pre-registers the bounded historical replay in `03-program-design.md` S8.1:
12 dated events across four official domains in a fixed 2025-08-01–2026-07-31
window, method-blind chronological selection within known-page/structural strata,
and fail-closed thresholds. Tavily must produce at least two useful structural
discoveries across two domains, with at most 10 reviewed candidates and a median
30 review minutes per useful frozen fixture. These are proposed falsifiers, not results.

## 10. What both comparison agents missed or overstated

- KodeKloud Engineer is a direct professional-simulation precursor.
- No documented public Sandbox URL does not mean no internal executable request loop.
- A literal 20-second public deployment was not supported by the reviewed endpoint guidance.
- Synthetic sealed checks do not establish employer acceptance.
- Deterministic fictional revenue or trust remains authored simulation.
- Hidden suites can leak through repeated probing, not only direct file access.
- Neither comparison made Nemotron load-bearing to a measured learner outcome.
- Tavily is safer as reviewed runtime mission maintenance than in live customer answers.
- The 45-day window makes multiple careers, a large town and employer validation
  incompatible with proving the core mechanism.

## 11. Scope and score boundaries

| Product state | Technology | Design | Impact | Idea | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current proposal | 3.5 | 3.0 | 3.0 | 4.0 | 27/40 |
| Defensible pre-evidence cap | 4.0 | 4.0 | 3.5 | 4.0 | 31/40 |
| Conditional best case | 4.5 | 4.5 | 4.0 | 4.5 | 35/40 |

These are subjective internal forecasts, not official grades or achieved evidence.
Do not compensate for weak impact by adding features.

Scope cuts that fund proof:

- one role and one bookshop, not a full town;
- one inherited follow-up and one transfer case;
- one judge-facing deployment, not redeployment theatre after every shift;
- no employer marketplace, certification or hiring claim;
- no XP, pet, generated economy or unrelated minigames;
- no live web content inside sealed evaluation;
- no autonomous agent ownership of the learner's core decisions.

## 12. Gate sequence and immediate unknowns

1. Gate 1: re-approved 2026-09-18; unchanged by this recovery.
2. Gate 2: RE-APPROVED 2026-09-19 after the scoped sealed-loader ownership
   backtrack; all other architecture decisions retain their prior scope.
3. Gate 3: RE-APPROVED 2026-09-19 after the scoped fourth backtrack for
   loader/signature/call-stack, purity/import checks and opaque-ref/public-identity
   projections; the user approved the revised document in chat. The prior
   2026-09-18 re-approval is historical.
4. Gate 4: RE-APPROVED 2026-09-19 after the scoped reconciliation revision
   (Slice 6 repair ownership of the revised test 11/13/17 checks and the audit gaps,
   snapshot pairing in Slice 7, restart recovery in Slice 8, prompt/real-provisioning
   mapping in Slices 12/14, ADR check in slice completion). A same-day follow-up
   revision (Slice 7 leak-response invalidation; Slice 10 scoring-input alignment)
   was approved by the user in chat on 2026-09-19.

Slice 6 is accepted: the repair and the adversarial review round resolved the
findings on 2026-09-19, an independent re-review returned PASS the same day
(fourteen probes, suites and demos reproduced), and Slice 7 implementation is in
progress under the user's instruction. The Gate 4 clause ownership is reconciled
and approved.

Unknowns include Token Factory Sandbox access, available Nemotron models, Tavily
access, runtime cost and latency, public deployment behaviour, learner recruitment,
curriculum validity and whether target learners want persistent responsibility.
No API key is needed during Gate 1.
