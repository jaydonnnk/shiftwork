# Shiftwork Pivot 1: incident apprenticeship and engineering decision lab

Recorded: 2026-09-23.

## S1. Status and authority

**Status: exploration and review only; not an approved pivot or implementation plan.**

This document consolidates the discussion, primary-source research, scoring and
second opinion about steering Shiftwork after Slice 9. The user expressed interest
in the direction and requested this record, not approval to implement it.

- `docs/plans/shiftwork/00-status.md` remains authoritative for gate and slice state.
- Existing gate approvals describe the existing direction, not this proposal.
- This document does not reopen, revise or approve a gate, authorize Slice 10 work,
  or authorize installs, credentials, external-service execution, deployment or Git operations.
- No pivot implementation, experiment, learner study or new runtime proof was
  performed during this discussion. Review findings include static code inspection.
- Reviewer opinions and scores are judgments, not independent proof of correctness,
  novelty, educational impact or likely prize outcomes.

## S2. The consolidated core

> Shiftwork lets students fix an actual AI program, compare different fixes, and
> see what their chosen repair causes in later shifts.

The audience remains aspiring applied-AI/software engineers with basic coding
knowledge. The learner maintains one versioned service for a fictional client
across successive shifts.

A conventional debugging exercise asks, "Can you fix this?" This proposal asks,
"Why should this fix work, what does it cost, and when would you choose differently?"

### Learning loop

| Step | Learner action | Evidence or consequence |
| --- | --- | --- |
| Inherit | Resume the service, prior decisions and unresolved incidents | Persistent artifact and operational state |
| Investigate | Inspect a failure using requests, retrieved information, tool calls and outputs | Observed execution, not a narrated incident |
| Predict | State a testable explanation before assistance supplies the diagnosis | A recorded prediction that the experiment can support or contradict |
| Design | Choose a test that distinguishes competing explanations | Learner-owned visible tests and an experiment protocol |
| Compare | Implement candidate repairs from a common starting point | Comparable correctness, coverage/escalation, cost and latency results |
| Decide | Select a repair and explain the tradeoff | Explicit choice of the implementation to carry forward |
| Return | Operate that implementation under a later relevant condition | Consequences derived from execution and transparent rules |

The product must connect **the student's prediction, the experiment's result and
its later consequence**, rather than simply put a debugger inside a fictional room.

There need not be one universally best repair. Two candidates may both meet the
requirements while differing in operating costs, speed or how often they ask for
help. Mandatory correctness and safety requirements cannot be traded away for a
better aggregate score.

### Ownership and presentation

- Students own the important code, hypotheses, visible tests, experiment design,
  repair directions and final decisions.
- Nemotron powers the actual service being investigated, rather than merely an
  optional tutoring chatbot or fictional shopkeeper.
- Assistance may help explain public evidence, but must not diagnose everything,
  write the entire repair and choose the winner while the student watches.
- Evaluator rules, protected expected cases, credentials and promotion remain
  outside learner and model control.
- The operational room can remain an explanatory interface. Remove its visuals
  and useful code, tests, experiment evidence and retained work must remain.
- Business consequences remain labelled synthetic. They are not real revenue,
  customer trust, employer validation or proof of job-readiness.

## S3. Illustrative engagement

**This is a hypothetical teaching example, not an observed experiment or an
approved scenario specification.**

Bellwether Books' AI assistant promises a book that is unavailable. The student
suspects stale information rather than insufficient model capability.

1. Inspect the request, retrieved records and response.
2. Predict that changing the model alone will not resolve stale source data.
3. Compare a model change with a retrieval-freshness change under a common contract
   and comparable workload.
4. Check whether either repair actually satisfies the request and inspect its
   coverage, cost and latency.
5. Select a repair and explain why its tradeoff is acceptable.
6. A later shift introduces an unavailable information source, exposing reliance
   on always-live retrieval.

Important limitations of this example:

- Inventory lookup itself may be better solved with ordinary code. It does not
  establish that the wider service genuinely needs an LLM.
- "Use a bigger model or refresh the stale database" can become an obvious quiz.
  The actual curriculum needs defensible alternatives and experiments that can
  genuinely distinguish explanations.
- A later outage must not be an arbitrary punishment for the student's selection.
  Scenario rules and public requirements must support the consequence.
- No comparison result is assumed. A valid experiment may be inconclusive.

## S4. What changes and what can be retained

| Existing or already planned | Proposed steering |
| --- | --- |
| Versioned learner artifacts, incidents and inherited shifts | Retain these foundations; they are not newly invented by this pivot |
| Recorded execution evidence and deterministic reductions | Retain where valid, but extend correctness coverage to the actual request |
| Repair followed by unseen related cases | Add explicit predictions and controlled comparisons of competing implementations |
| Planned bounded Nemotron assistance | Put meaningful Nemotron behaviour inside the service under investigation |
| Operational attempts with rotating protected cases | Distinguish exploratory comparisons from authoritative assessment and operational runs |
| Latest-version inheritance | Explicitly inherit the learner-selected candidate rather than the last candidate saved |
| Operational-room presentation | Guide the student through a decision, not expose a professional debugger dashboard |

This is not a restart, but it is also not merely a new comparison screen. The
experiment lifecycle, model role, grading and selected-version semantics require
substantive design work.

At the time of discussion, Slice 9 was recorded as implemented and accepted, while
live assistance, the Token Factory capability spike and the real sandbox adapter
remained later slices. The current local execution evidence concerns trusted
fixtures, not validated isolation for arbitrary learner code.

Evidence: `docs/plans/shiftwork/00-status.md:98`,
`docs/plans/shiftwork/00-status.md:101`, and
`shiftwork/orchestrator.py:122`.

## S5. Against the user's requirements

| Requirement | Assessment | Reason and boundary |
| --- | --- | --- |
| Cannot be built without organiser technology | Fails literal vendor exclusivity; capability dependence remains to be established | Another capable model and execution provider could substitute; meaningful inference and controlled execution can still be essential to the product |
| Be early | Partial | Incident labs, agent debugging, experiments and generated evaluations already exist; the opportunity is their student-centred continuity, not inventing those tools |
| Align with Best Apps and Agents | Strong, conditional on the actual implementation | A useful learning app centred on real Nemotron-powered behaviour fits better than an optional chatbot attached to exercises |
| Be ambitious | Strong | Controlled experiments and persistent operational consequences form a substantial product; ambition alone is not a scoring penalty |
| Retain education for aspiring engineers | Strong conceptual fit | The loop addresses diagnosis, test design, maintenance and tradeoff selection, without claiming measured learning gains |
| Differentiate from games | Meaningful product distinction, not technical exclusivity | Useful engineering artifacts remain without the room; Roblox could nevertheless display the same external backend |
| Steer rather than restart | Achievable with material changes | Reuse the evidence and persistence foundations while changing important learning and execution semantics |

### Organiser dependence

Distinguish two questions:

1. **Could another vendor replace Nebius or Tavily?** Yes, potentially. No reviewed
   capability establishes an exclusive-vendor claim.
2. **Would removing inference or controlled execution remove an important learning
   problem or capability?** Potentially, if the service actually needs varied
   language understanding or tool selection and learners execute their own code.

It must remain legitimate for a student to replace an unnecessary LLM subtask with
ordinary code. Forcing poor engineering solely to preserve an API call would
undermine the educational purpose.

The wider service still needs a genuine model-dependent problem. Making students
inspect a model that never needed to be there is not a convincing solution.

### Official-rule boundary

The live official rules were accessed during this discussion. Best Apps and Agents
requires a useful app or agent powered by Nemotron on Nebius through Token Factory.
The track does not require vendor exclusivity. Serverless deployment is encouraged,
not mandatory, and sandbox execution is not itself a main-track requirement.

Tavily is optional for the main track. The separate bonus requires a functional,
runtime Tavily API call as part of the solution. Qualification and product value
are different questions: a qualifying call is not automatically a good integration.

A possible Tavily role is discovering relevant official changes that alter the
engineering problem, followed by review and freezing before assessment. If static
fixtures or monitoring already-known pages suffice, do not invent extra value.
The existing approved curation design remains unchanged by this proposal.

## S6. What is good about the idea

1. **Reasoning is visible.** The student explains a likely cause, designs a test
   and revisits the prediction after seeing the result.
2. **Choices can have defensible tradeoffs.** Correctness, coverage, cost and speed
   need not point to one universal winner.
3. **Work persists.** A decision affects the same maintained system later, rather
   than disappearing when a disconnected exercise ends.
4. **AI can do substantive work.** Actual model errors, evidence use and tool
   choices become things the student must understand and engineer around.
5. **The value survives without the artwork.** Code, tests, results and engineering
   decisions remain useful objects.
6. **Existing foundations have a purpose.** Captures, immutable versions, incidents
   and inheritance can support the learning mechanism rather than be discarded.

These are design strengths, not demonstrated educational outcomes.

## S7. Material findings and challenges

### S7.1 Task relevance is a prerequisite for trustworthy assessment

**Verified static finding; already recorded as an inherited limitation.**

The current evaluator checks support for factual claims and freshness, but the
reviewed path does not establish that the response answers the executed question.
A supported price answer can therefore pass the relevant checks for a stock question.

Sources: `docs/plans/shiftwork/00-status.md:2694`,
`shiftwork/evaluator/evaluator.py:194`, and
`shiftwork/evaluator/evaluator.py:213`.

The second reviewer identified this, and the main agent inspected the relevant
code directly. No new runtime reproduction was performed in the pivot discussion.

If retained, this would invalidate repair comparisons: students could optimize
for a true but irrelevant answer. The revised design needs request-specific
obligations, including the correct entity, requested information and any permitted
action. Unrestricted prose correctness cannot simply be handed to another model
and treated as authoritative PASS/FAIL.

### S7.2 Operational runs are not controlled comparison trials

**Verified current behaviour; a design conflict with the proposed pivot, not
necessarily a defect in the existing approved lifecycle.**

- `start_run` chooses the latest version: `shiftwork/orchestrator.py:263`.
- Attempts select previously unexposed variants:
  `shiftwork/orchestrator.py:277` and `shiftwork/orchestrator.py:279`.
- A new shift seeds its draft from the latest engagement version:
  `shiftwork/orchestrator.py:171`.

A fair comparison needs a common baseline and comparable workload. A sequence of
ordinary attempts cannot be assumed to provide that comparison when its scenarios
change. Repeated experiments must not indiscriminately consume or reveal the
protected assessment inventory.

Experimental trials also need separation from authoritative operational
consequences. Saving candidate B after candidate A must not silently make B the
selected implementation for the next shift.

### S7.3 Repeated inference complicates evidence

The same model can answer differently on repeated runs. One successful attempt is
not proof that a repair is reliable.

The experiment design must distinguish:

- captured-output replay, which can help inspect and re-score a historical run;
- fresh inference, which is required to evaluate changed model behaviour;
- changes to prompts, models, tool data, initial state, budgets and settings.

Reusing an old completion does not prove what a changed prompt or model would do.
Changing several uncontrolled inputs at once makes attribution weak. Experiments
need sufficient repetition and visible variability for their claims; no sample
size, latency, price or success rate has been established here.

### S7.4 Student agency can be superficial

The choices must not conceal a prescribed answer. A hypothesis form is not enough
if the scenario makes one repair obviously correct, or the assistant supplies all
the reasoning before the learner acts.

Students need guidance through the process without being handed the conclusion.
This is the principal unresolved product-design challenge behind the differing
forecasts in S9.

### S7.5 Safety and access remain delivery dependencies

Real learner execution requires validated isolation, protected credentials,
controlled resource use and suitable limits on tool actions. Existing trusted
local fixtures do not establish those guarantees.

Nebius documents sandbox isolation and checkpoint capabilities, but documentation
is not proof of this project's access or successful integration. Neither public
service ingress nor operational performance should be assumed without an authorized
capability check.

These are engineering dependencies, not permission to run a spike or install tools.

### S7.6 A guided course could reproduce much of the experience

The strongest unresolved competitive question is:

> What does Shiftwork teach meaningfully better than a well-designed course using
> an existing agent debugger?

The second review's answer was "potentially, but not automatically." The strongest
candidate advantage is automatically preserving the connection between a student's
prediction, chosen implementation and later executable consequences. A course could
also provide this, but would need to coordinate that continuity.

One prescribed repair followed by one canned outage would not demonstrate a strong
advantage. The project should not confuse curriculum scripting with an automatically
meaningful consequence.

## S8. Relevant prior art and timing

The following sources were examined during the discussion and review. They establish
overlapping capabilities, not an identical competitor or the absence of one.

| Source | Relevant overlap | What it does not establish |
| --- | --- | --- |
| SadServers | Real-environment troubleshooting practice | That the exact proposed persistent AI-engineering learning loop already exists |
| LangSmith Studio | Agent inspection, prompt iteration, dataset experiments and time-travel debugging | A student-centred apprenticeship with learning ownership and inherited decisions |
| DiLLS, February 2026 | Structured diagnosis of agent behaviour | Educational effectiveness or the exact Shiftwork curriculum |
| AGDebugger, March 2025 | Interactive inspection, editing and resetting of agent message histories | The proposed longitudinal student learning product |
| Anthropic Bloom, December 2025 | Automated generation and execution of behavioural evaluations | A human learning platform; it is especially relevant to the excluded AI-challenger branch |

As of this discussion, "AI debugging," "branching experiments" and "AI-generated
tests" are not sufficient early-mover claims. The educational combination remains
a hypothesis worth examining. Existing components do not, by themselves, make a
product unoriginal or poorly implemented.

## S9. Scores and independent-review record

### Scoring basis

- Use the four official equally weighted judging criteria, normalized to /10 each
  for the requested /40 comparison. This is an internal presentation scale.
- These are subjective forecasts for a competently delivered working demonstration
  of the specified core, not achieved scores for the current Slice 9 build.
- No credit is given for excluded branches or unspecified capabilities.
- The user's instruction excludes user studies, adoption numbers, interviews and
  real-user testing as additional scoring criteria or automatic impact deductions.
- Potential Impact can still consider the audience, problem and logic of the
  learning mechanism. It must not claim measured learning gains without evidence.
- Missing implementation is not deducted twice when the forecast already assumes
  successful delivery, but unresolved assumptions must remain visible.
- Do not inflate a score to reach 35. Do not penalize ambition merely because the
  work is substantial. Avoid counting component familiarity as both a novelty and
  an automatic implementation penalty.

### Main-agent forecast versus fresh second opinion

| Criterion | Main-agent stronger-core forecast | Fresh reviewer forecast |
| --- | ---: | ---: |
| Technological Implementation | 9 | 8.5 |
| Design | 9 | 8 |
| Potential Impact | 8 | 8 |
| Quality of the Idea | 8 | 8 |
| Total | **34/40** | **32.5/40** |

The main agent also forecast **32/40** for the less developed, straightforward
blend. The **34/40** forecast referred to the stronger core with explicit
predictions, controlled comparisons and inherited consequences, without the
optional product branches.

The fresh review was a read-only general-purpose agent review. The main agent's
numerical forecast was withheld from its brief to reduce anchoring. The reviewer
checked repository code and primary sources; no tests were executed. Its verdict
was **Pursue**, not product-gate approval.

Reviewer rationale:

- **Technology, 8.5:** live inference, controlled comparisons and traceable
  consequences form a substantial integrated system.
- **Design, 8:** the journey is coherent, but making code, uncertainty and tradeoffs
  understandable to basic coders without replacing their judgment remains difficult.
- **Impact, 8:** the audience and problem are specific; authored scenarios can
  constrain breadth and repeat usefulness. This was not a user-study penalty.
- **Idea, 8:** investigating AI rather than receiving AI tutoring is a strong
  framing, but the individual mechanisms have substantial prior art.

The reviewer described approximately two points of overall uncertainty, not a
statistical confidence interval.

### Main-agent adjudication after review

- The relevance and lifecycle findings were checked directly against the source.
- The earlier Design 9 assumed an excellent guided experience that the proposal
  had not yet adequately specified; the main agent acknowledged that optimism.
- Familiar components alone should not automatically lower Technology; originality
  belongs primarily under Quality of the Idea.
- The review did not establish that 32.5 is objectively correct or that 34 is
  impossible. Neither forecast warrants calling this a confident 35+ proposition.
- No replacement numeric consensus score was adopted after the review.

### Scope of earlier branch scores

These were historical brainstorm forecasts, not ingredients added to the core:

| Separate direction | Technology | Design | Impact | Idea | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| AI challenges the student's explanation | 9 | 8 | 8 | 8 | 33/40 |
| Learn where agent autonomy should stop | 9 | 8 | 8 | 9 | 34/40 |
| Apprenticeship around the student's own project | 9 | 8 | 9 | 8 | 34/40 |

In particular, **33/40 was not the stronger core's score**. It referred to the
separate explanation-challenger direction. These branch forecasts are not the
fresh reviewer's evaluation of the core.

## S10. Smallest proposed refinement

The second reviewer proposed adding one explicit falsifier alongside the student's
explanation:

> What result would show that your explanation is wrong?

Example:

> If fresh inventory still produces the wrong availability answer, stale
> information alone cannot explain this failure.

This sharpens the existing student-designed experiment. It does not require an
AI challenger or automatically generated personalized cases. It remains a proposed
refinement, not an approved implementation requirement.

## S11. Excluded branches and claims

The current proposal does not include:

- an AI that generates personalized counterexamples to the student's explanation;
- a separate autonomy/delegation school;
- arbitrary bring-your-own-project support;
- multi-agent team apprenticeships;
- shared research marketplaces or evidence commons;
- a new career marketplace, employer credential or job-readiness claim;
- free-roam gameplay, XP or cosmetic progression as the core value;
- live unreviewed web material determining protected assessment outcomes.

Mentioning tool permissions as a safety constraint does not silently add the
separate autonomy-school branch. Comparing two repair candidates is part of the
core; it is distinct from the optional product directions above.

## S12. Open decisions before adoption

1. Which concrete service task genuinely needs Nemotron while still allowing
   independently checkable outcomes?
2. What can students decide that is not an obvious author-selected repair?
3. What request-specific correctness contract closes the current relevance gap
   without pretending all open-ended prose can be graded deterministically?
4. How are matched exploratory comparisons separated from protected assessment,
   operational consequences and attempt budgets?
5. How is the chosen version explicitly carried into the next shift?
6. How does the interface guide a basic coder without supplying the diagnosis,
   experiment and decision on their behalf?
7. What does this integrated learning loop provide beyond a course and an existing
   debugger, without claiming unmeasured learning gains?
8. Which proposed execution and inference capabilities can actually be validated
   under separately authorized access and spending limits?

If the direction is adopted, the affected product journey, architecture boundaries,
program semantics and slice ownership need scoped revision through the existing
approval process. Likely affected gates are Product, Architecture, Program Design
and Slice Plan; this document does not itself backtrack or approve any of them.

**Consolidated position:** promising enough to develop further, but not yet a
confident 35+ proposition. The strongest value is teaching students to defend
engineering decisions and handle their later consequences. The greatest challenges
are trustworthy assessment, meaningful experiments and a distinct, usable learning
experience rather than a debugger with lessons attached.

## S13. Sources and evidence boundaries

### Repository sources

- `HACKATHON_REQUIREMENTS.md:57`: Best Apps and Agents summary.
- `HACKATHON_REQUIREMENTS.md:105`: Tavily submission qualification and the existing
  curation decision; this proposal does not change that decision.
- `HACKATHON_REQUIREMENTS.md:150`: the four equally weighted judging criteria.
- `docs/SHIFTWORK_PLAN.md`: existing supporting brief and historical forecasts,
  which must not be mistaken for this pivot's approval or score.
- `docs/plans/shiftwork/01-product.md:50`: existing learning purpose and scope.
- `docs/plans/shiftwork/00-status.md:98`: accepted Slice 9 and later-slice status.
- `docs/plans/shiftwork/00-status.md:2694`: recorded evaluator relevance limitation.
- `shiftwork/evaluator/evaluator.py:194`: reviewed grading rule selection.
- `shiftwork/evaluator/evaluator.py:213`: factual-support checks.
- `shiftwork/orchestrator.py:171`: latest-version inheritance.
- `shiftwork/orchestrator.py:263`: latest-version selection for an operational run.
- `shiftwork/orchestrator.py:277`: exposure tracking and subsequent variant selection.

Line references identify the state checked during this discussion and can move
with later edits. Approved gate documents and current code remain authoritative for
implementation; this file records a proposal and its review.

### Primary external sources

- [Official hackathon rules](https://nebiusglobalaihackathon.devpost.com/rules):
  track requirements, equal-weight criteria and Tavily bonus qualification;
  accessed successfully through the browser after text fetching returned no content.
- [Nebius Token Factory Sandboxes](https://docs.tokenfactory.nebius.com/sandboxes/overview):
  documented isolation and checkpoint capabilities, not verified project access.
- [Nemotron on Token Factory](https://nebius.com/services/token-factory/nemotron):
  organiser model offering, not measured results for this application.
- [Roblox HttpService](https://create.roblox.com/docs/reference/engine/classes/HttpService):
  external HTTP/API access, contradicting literal "impossible in Roblox" claims.
- [LangSmith Studio](https://docs.langchain.com/langsmith/studio): existing agent
  inspection and experiment capabilities.
- [SadServers individual learning](https://sadservers.com/solutions/individual):
  hands-on troubleshooting practice.
- [DiLLS](https://arxiv.org/html/2602.05446v1): February 2026 agent-diagnosis research.
- [AGDebugger](https://arxiv.org/abs/2503.02068): March 2025 interactive agent-debugging research.
- [Anthropic Bloom](https://www.anthropic.com/research/bloom): December 2025 automated
  behavioural evaluations; relevant prior art, not the proposed human learning product.
- [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents):
  repeated trials, outcome checks and evaluation-design considerations.
- [Tavily and Nebius at GTC 2026](https://www.tavily.com/blog/tavily-nvidia-gtc-2026-agentic-ai-search):
  existing agent-search integration context, not proof that Shiftwork needs Tavily.

External product descriptions and research papers are evidence about their stated
capabilities, not independent validation of Shiftwork's novelty, learning outcomes
or performance.
