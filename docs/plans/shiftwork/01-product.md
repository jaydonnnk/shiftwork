# Product: Shiftwork

**Gate state:** IN PROGRESS, backtracked 2026-09-24 at the user's request to
revise Gate 1 around `shiftwork_final_pivot.md`. Awaiting explicit re-approval.
The approvals of 2026-09-15 and 2026-09-18 remain historical; they do not approve
this revision. This document and its six static mockups describe proposed product
behavior, not new implementation or evidence. Later gates require separate revision
and approval before implementation resumes.

## Problem

Proposed learner need, not a participant quote:

> I can follow an AI tutorial, but when the program fails I do not know which
> explanation to trust, how to compare repairs fairly, or whether my chosen repair
> will still make sense when conditions change.

The learner knows basic coding and wants practice diagnosing and maintaining an
actual AI program, not just completing prescribed fixes. They play a **junior
applied AI engineer** responsible for a fictional client's service. Bellwether
Books is the first client; the same service, decisions and unresolved incidents
return across shifts.

The job is engineering judgment: explain a failure, try to disprove the explanation,
compare real code changes and maintain the selected solution. The fictional role
is not a credential, certification, job-readiness or employer-validation claim.
The room makes the work understandable; it is not the reason the product is useful.

## Success metric

**Retained north star, not an achieved result:** at least a **20 percentage-point
increase in independently completed transfer tasks** against a strong matched
static tutorial, without increasing median time or the hint budget.

Completion alone does not establish sound reasoning. The comparison must separately
record whether the learner can:

- link a suspected cause to the actual request, information, tool use and output;
- name a result that would disprove that explanation and design a test for it;
- compare eligible repairs under the same requirements and starting conditions;
- justify a choice using completion, mistakes, human referrals, cost and delay;
- explain what changed later without judging the original decision by hindsight.

Retain learner-authored explanations, visible tests, code changes and choices;
distinguish optional assistance and accepted generated patches. Record voluntary
return and whether the workflow feels like useful investigation or paperwork.
Passing service tests alone is not a measure of diagnosis quality. A model's opinion
is not authoritative evidence of learning.

A small manual mockup test is formative only. No learning-improvement claim is
allowed without a sufficiently powered study. Rubric, sample size, repetition
requirements and feasibility belong to the revised Gate 3, with execution planned
at Gate 4 and outreach separately authorized. Existing study plans are not silently
updated or treated as evidence for the pivot.

## Product decisions proposed for re-approval

### S1. A continuing service, not a sequence of coding quizzes

- Start Bellwether with an inspectable starter AI service and a concrete incident.
  The learner owns subsequent code, tests, explanations and repair choices.
- AI performs meaningful work inside the service, such as interpreting varied
  requests and identifying the information needed. It is not merely a fictional
  shopkeeper or an assistant telling the learner the answer.
- Exact prices, stock and commitment rules must remain enforceable independently
  of model confidence. Replacing unnecessary AI behavior with ordinary code is a
  valid engineering choice, not a penalty.
- Keep service versions, execution evidence, incidents, synthetic business history
  and the operational-room interface. This is substantial steering, not a restart
  or a cosmetic comparison screen.

### S2. Explain and test before accepting a diagnosis

- Show the customer's complete request, the service's recorded interpretation and
  information/tool use, the records it consumed and its exact output.
- Ask two short questions before diagnostic hints: "What do you think caused this?"
  and "What result would show that explanation is wrong?" Let the learner choose a
  distinguishing test. Do not demand polished prose or grade writing style.
- Separate observations from explanations. Do not title the incident with an
  unproven root cause or let a confident assistant settle it.
- Preserve the original prediction and later correction. A passing repair does not
  prove the proposed diagnosis, and changing one's explanation in response to
  evidence is legitimate progress.
- Offer basic orientation without supplying a diagnosis. Requested diagnostic
  help and labelled patch proposals follow the initial learner prediction; record
  their use. The learner chooses experiments and the final repair.

### S3. Separate experiment, choose and operate

| Activity | Learner action | Effect on ongoing history |
| --- | --- | --- |
| Experiment | Edit and test candidate repairs against comparable requests. | Keep experiment evidence, but do not create operational sales, resolve incidents or alter the inherited version. |
| Choose | Explicitly select an eligible tested version and explain the tradeoff. | Bind that exact version and retain the alternative and reasoning; selection itself creates no business result. |
| Operate | Run the chosen version against the shift's requests. | Record independently checked, explicitly synthetic consequences and carry them forward. |

Saving, freezing or testing another candidate never silently replaces the chosen
version. Before the first choice, identify the starter service as the operating
version. If a candidate changes after testing, the older results do not establish
that the changed version is eligible. Operational incidents remain open until
operational evidence satisfies their resolution rule; an experimental pass cannot
resolve them.

### S4. Make a comparison fair and useful

- Both candidates obey the same visible mandatory task, correctness and safety
  requirements. Learner preferences can add constraints, not waive those rules.
  Changing the contract requires a new comparison of both candidates.
- Check whether the answer addresses the actual request, not merely whether it
  contains true facts. Correctly quoting a price does not answer a collection query.
- Match workloads, public information, starting business state, relevant model
  settings and resource limits. State the intended difference between candidates;
  label uncontrolled or incompatible results **Not comparable**.
- Distinguish inspecting a recorded run from freshly executing changed code or AI
  behavior. Replaying yesterday's output is not a measurement of a new repair.
- Show repetition counts, individual trial outcomes and variation where fresh AI
  execution matters. Do not select one lucky trial or silently discard failures.
  Incomplete evidence is incomplete, not a pass; unavailable cost is not zero.
- Reject mandatory correctness or safety failures before considering efficiency.
  Compare useful answers, wrong answers, justified refusals and human referrals
  separately, with the same denominator. Refusing everything is not success.
- Show cost and delay alongside completion and mistakes, without an aggregate score
  that hides forbidden behavior or automatically picks a winner.
- Independent checks own assessment; neither learner code nor assistance may alter
  expected answers, grading rules or promotion eligibility. Protected assessment
  content remains unavailable to either actor. Product feedback must remain useful
  without revealing protected answers.

### S5. Make later consequences causal without hindsight grading

- The next shift inherits the explicitly selected code, decision rationale, tests,
  incidents and unresolved limits, not whichever file was saved last.
- Introduce understandable changes such as a data update or unavailable dependency.
  State known dependency risks during the original choice, but do not reveal future
  protected requests or expected answers while repairing.
- Assess the original decision against the requirements and evidence available at
  that time. A later outage does not retroactively make a reasonable choice wrong.
- Once a later condition has occurred, let the learner test the retained alternative
  under that same condition as a separate experiment. Use comparable fresh trials
  where needed, not replay dressed up as a measured alternative outcome.
- The later experiment cannot rewrite the operational ledger, original choice or
  incident history. Choosing a different operating version is a new explicit action.
- Show the resulting difference and ask whether the tradeoff is still acceptable.
  Narrative can explain an observed consequence, never substitute for execution.

### S6. Keep the scope narrow

One role and two fictional clients remain the product boundary: Bellwether first,
then a reduced-assistance Northline Bike Cooperative engagement. The first proof
should cover one complete Bellwether diagnosis, fair repair comparison, explicit
choice and inherited consequence, including the retained alternative experiment.
Northline tests fresh reasoning about future commitments, safety escalation and
retry-safe bookings, not memorized bookshop answers. It starts with a blank learner
artifact and a new brief, not copied bookshop solutions.

No arbitrary personal projects, multi-agent teams, autonomy school, marketplaces,
AI-generated challenges, automatic permission growth or extra careers. Additional
roles remain future scope requiring a new decision. No XP, competence meters, pets
or cosmetic upgrades as substitutes for engineering progress. Synthetic orders,
refunds and backlog never establish real revenue, customer trust or learning impact.

## Concrete Bellwether example

**Illustration, not a measured run or an approved executable curriculum fixture.**

A customer asks: "Can I collect the Salt Roads paperback tomorrow? If not, suggest
something similar under £20." The service replies only that the paperback costs
£18. That price may be supported while the requested collection and alternative
questions remain unanswered. The learner inspects interpretation, selected tools,
records and output to distinguish a routing problem from a data or response problem.

A distinguishing experiment could provide current inventory information while
holding the request and other conditions fixed. If the reply still gives only a
price, stale information alone does not explain the failure. This is a testable
prediction, not an assistant-declared diagnosis.

Two repairs can both respect "never promise unconfirmed stock":

- **A:** broad verification for every request. Simpler coverage and fewer ambiguous
  cases referred to staff, but more calls, delay and dependence on inventory access.
- **B:** request-specific verification with conservative referral for ambiguous
  requests. Fewer calls and less delay, but more referrals and a routing boundary
  the learner must maintain.

Neither name denotes the right answer. Later, inventory access becomes unavailable.
The learner sees the chosen version's observed consequences and compares the
retained alternative separately. The original choice is judged using what was
knowable then, not the later event.

## Visual direction and screen journey

Retain the selected fixed isometric operational room and station-based interaction
in `client-visual-direction.md`. The service remains central; requests, inspected
evidence and operational consequences stay linked. Add an unmistakable distinction
between experiment results, a chosen version and actual operational history.

The six plain HTML mockups are navigable storyboards, not a working service. Native
inputs and disclosure controls illustrate interaction but do not save, test or
select an operating version. Every sample run, number and later history is labelled
illustrative. Three-trial examples show how variation could be displayed; they are
not an approved trial count, measured benchmark or study design. Separate A/B
history previews must not pretend to reflect an unsaved radio choice.

| Screen | Product question and primary work |
| --- | --- |
| [Shift board](mockups/01-shift-board.html) | What service and unfinished responsibility am I inheriting? |
| [Requirements](mockups/02-owner-brief.html) | What must both repairs satisfy, and which test and tradeoff matter to me? |
| [Investigate](mockups/03-customer-shift.html) | What happened, what might explain it, and what test could disprove that explanation? |
| [Compare and choose](mockups/04-incident-review.html) | Are these trials comparable and eligible, and which exact repair will I retain? |
| [Next shift](mockups/05-inherited-shift.html) | What did my chosen version cause, and how does the retained alternative behave now? |
| [Away shift](mockups/06-away-shift.html) | Can I apply the reasoning to new commitments and failure modes with less help? |

Use the same room for Bellwether returns, a distinct Northline workshop, keyboard
reachable stations and readable desktop/mobile evidence. Progressive disclosure
should reduce initial load without hiding comparison validity or mandatory failures.

## Announcement: the blog post before the feature

**Aspirational launch copy; the revised workflow is not built or demonstrated.**

Meet Shiftwork, a place to practice engineering judgment on a continuing AI service.
As a junior applied AI engineer for a fictional bookshop, inspect what a customer
asked and what your program actually did. Test your explanation, compare repairs
fairly and choose the code you will maintain. Return when conditions change to see
what your choice caused, then test whether the alternative would behave differently
without rewriting history. Take what you can explain to a new client with less
help. Your work persists; the role is a simulation, not a credential.

## Open product hypotheses and evidence questions

1. Does a short prediction change the learner's experiment, or become paperwork?
2. Are competing explanations and repairs plausible enough to require judgment,
   rather than an obvious "refresh the data" quiz?
3. Can a beginner distinguish experiments, version selection and operational history?
4. Can they distinguish safe refusal from useful completion and cite the tradeoff?
5. Does the retained-alternative comparison teach anything beyond a saved project?
6. Does the room help evidence comprehension rather than hide it?
7. Does the integrated workflow improve on a strong course plus an existing debugger?
8. Does Northline test fresh reasoning, and is the retained transfer target feasible?

The differentiation is a guided, connected workflow, not a proven exclusive category.
Technology selection, execution isolation, credential protection, persistence
mechanisms, evaluators and study methods belong to separately revised Gates 2 and 3;
slice sequencing belongs to Gate 4. This revision authorizes none of them.
