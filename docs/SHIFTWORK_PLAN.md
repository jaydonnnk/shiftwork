# Shiftwork — working brief and adjudication register

Updated: 2026-09-15.

**State:** selected by the user as the sole active hackathon direction.
**Gate state:** Gate 1 — Product APPROVED 2026-09-15; Gate 2 — Architecture
pending. A requested final independent Gate 1 review may backtrack only for a
concrete product-level blocker.
**Latest verdict before selection:** `REVISE SHIFTWORK BEFORE ADOPTION`.
**Evidence state:** no application, Sandbox execution, learner study, transfer
result, Tavily ablation, prize merit or score has been demonstrated.
**Working forecast:** current 27/40; pre-evidence cap 31/40; conditional best
case 35/40. Potential Impact remains at most 4.0 in that best case.

This supporting brief holds research, technical hypotheses and evidence boundaries.
It is not a gate approval or implementation specification. Approved documents in
`plans/shiftwork/` supersede provisional choices here.

## 1. Product thesis

Shiftwork is a persistent applied-AI-engineering learning environment for people
with basic coding knowledge. The learner maintains one real service for a fictional
business across successive operational shifts. Later shifts inherit the learner's
artifact, decisions, incidents and business state rather than resetting into an
unrelated exercise.

Primary job: **applied-AI-engineering education**. Career exploration supplies
context, not the core outcome. Employer proof is excluded until an employer or
credible external reviewer accepts the evidence.

Initial scope: one applied-AI role and one bookshop engagement. The learner must
make meaningful decisions about what the service must get right, how it should
handle uncertainty, how it should be tested, and how an observed failure should
be repaired. A town may make inherited state legible, but it is not differentiation.

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
  service-workbench redesign. If the requested final independent review finds no
  concrete product-level blocker, Gate 2 drafting may begin. Gate 2 approval and
  implementation remain unauthorized.
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
and hint budget. Use structurally equivalent bookshop and bike-cooperative tasks and
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

1. Gate 1: approved 2026-09-15. The requested final independent review may
   backtrack only for a concrete product-level blocker.
2. Gate 2: after that review passes, inspect the repository and decide system
   boundaries, execution path, persistence, model role, deployment and external
   services.
3. Gate 3: define interfaces, authority enforcement, sealed-case isolation, metrics
   and the three test protocols before implementation bodies.
4. Gate 4: approve visible end-to-end slices; execute the central-mechanism proof first.

Unknowns include Token Factory Sandbox access, available Nemotron models, Tavily
access, runtime cost and latency, public deployment behaviour, learner recruitment,
curriculum validity and whether target learners want persistent responsibility.
No API key is needed during Gate 1.
