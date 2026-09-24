# Shiftwork: working brief and adjudication register

Updated: 2026-09-24.

**Direction:** Shiftwork remains the sole active project. The user requested Gate 1
revision around `../shiftwork_final_pivot.md`: diagnose a real AI service, compare
repairs fairly, explicitly choose one and maintain its later consequences.
**Gate state:** Gate 1 IN PROGRESS, backtracked 2026-09-24; revised product and
mockups await explicit re-approval. The request to revise is not approval.
**Later gates:** prior Gates 2, 3 and 4 approvals remain historical for the old
design. Their pivot-affected decisions require separate revision and approval,
in order, after Gate 1. No further implementation is authorized by those old
approvals while the product backtrack is open.

**Build baseline:** Slices 1 through 9 are recorded as implemented; Slice 9 was
merged to main as `4d5539a` and pushed on 2026-09-21, with user visual acceptance.
Slices 10 through 17 are not implemented. Preserve that foundation and its evidence;
it does not demonstrate the new prediction, comparison or selection workflow.
The full approval history and verbatim evidence remain in
`plans/shiftwork/00-status.md`. This summary does not re-run or re-certify them.

**Forecast for the focused pivot:** 32/40, assuming a competently delivered
demonstration; not a score for today's build, a judging prediction or learning
result. The pivot's verdict is **revise, then pursue**, not a confident 35+.
Earlier 27/40, 31/40 and conditional 35/40 forecasts are historical, not current caps
or achieved scores. No human learning/transfer result, qualifying live integration,
Tavily ablation or prize merit is established by this planning revision.

This brief supports the gate documents; it does not replace or approve them.
The draft `plans/shiftwork/01-product.md` expresses the proposed product. Approved
gate decisions remain authoritative within their original scope, not as permission
to implement conflicting pivot behavior. No installs, credentials, external calls,
spike runs, purchases, outreach, deployment, branches, commits, tags, pushes or
ADR #4 are authorized by this revision.

## 1. Product thesis

Shiftwork helps aspiring applied AI engineers practice evidence-led diagnosis,
experiment design and maintenance. A learner with basic coding knowledge plays a
junior applied AI engineer for a fictional client, initially Bellwether Books.
They return to the same service, selected code, decisions, incidents and limits.

The change is not merely "fix the service": **explain why a repair makes sense,
compare it fairly with another repair, and maintain the one you explicitly choose.**
The learner's prediction, test, code change, selection and later outcome form one
guided workflow. AI behavior inside the service is an object of investigation,
not just the voice supplying help. Ordinary code may replace unnecessary AI.

The role is fictional framing, not certification or job-readiness. Persistent
synthetic business state is not real revenue, customer trust or employer evidence.
A strong course combined with an existing debugger could reproduce much of the
workflow. Integration and reduced learner burden are hypotheses to prove, not
claims of an exclusive category.

## 2. Decisions and authority

- 2026-09-15: the user scrapped Hatchery as active scope and selected Shiftwork.
  Hatchery remains historical evidence and a mechanism donor.
- 2026-09-15 to 2026-09-19: the four gates were approved and revised as recorded in
  `plans/shiftwork/00-status.md`. Gate 1's last approval was 2026-09-18; Gates 2,
  3 and 4 were last re-approved 2026-09-19 within their documented scopes.
- 2026-09-18: the user selected the fixed isometric operational room and explicit
  junior applied AI engineer framing. Retain both through the pivot.
- 2026-09-21: Slice 9 merge/push marked the user's visual acceptance of that slice,
  not acceptance of later work or the subsequent pivot.
- 2026-09-23: `SHIFTWORK_PIVOT2.md` recorded an unapproved product-direction review;
  `shiftwork_final_pivot.md` consolidated the recommended final direction.
- 2026-09-24: the user requested reading the repository rules and starting Gate 1
  revision. Scope is revised product, static mockups and supporting gate records,
  followed by explicit re-approval. It does not approve Gate 1 or later gates.

The external software-factory guide at the recorded
`C:/Users/jayd0/.agents/skills/software-factory/SKILL.md` path was unavailable during
this revision, including a bounded lookup in local resource locations. The explicit
repository gate rules are being followed; full compliance with an unread guide is
not claimed. No tool or skill was installed to replace it.

## 3. Revised learning loop

1. Inherit the starter or explicitly selected service and unresolved responsibility.
2. Inspect the request, interpretation, information/tool use and actual output.
3. State a suspected cause and a result that would disprove it before diagnostic help.
4. Choose a distinguishing test and implement competing code repairs.
5. Compare eligible candidates under the same requirements and controlled conditions.
6. Select an exact tested version and explain its accepted tradeoff.
7. Operate that version and inherit its independently checked synthetic consequences.
8. After a later change, test the retained alternative separately without rewriting
   operational history, then reconsider the choice using the new evidence.

| Activity | Persistent evidence | Does not do |
| --- | --- | --- |
| Experiment | Candidate versions, predictions, trial inputs/results and comparison | Resolve operational incidents, write business consequences or replace the selected version |
| Choose | Exact tested version, rationale and retained alternative | Claim that merely choosing a repair fixed the client's incident |
| Operate | Executed outputs, independent checks and synthetic consequences | Silently substitute the latest saved candidate |

## 4. Bellwether: a less predetermined incident

Illustration, not an executed scenario or a newly sealed fixture:

> "Can I collect the Salt Roads paperback tomorrow? If not, suggest something
> similar under £20."

The service returns only the supported price, £18. The learner must distinguish
request interpretation, tool selection, data freshness and response construction
rather than assuming a larger model fixes missing information. A current stock
record alone may not repair a system that still answers the wrong question.

Both candidate repairs obey the same mandatory rules, including addressing the
requested tasks and never promising unconfirmed stock. Broad verification can
serve more ambiguous cases at greater cost, delay and dependency exposure;
request-specific verification can be faster but refer more ambiguity to staff and
require maintenance of the routing boundary. Neither is a designated quiz answer.

A later inventory outage exposes a known class of dependency risk. Assess the
original choice using the evidence and requirements then available, not hindsight.
After the outage occurs, comparing the retained alternative answers whether the
choice materially changed behavior; it cannot erase the chosen version's history.

## 5. Comparison and evidence requirements

- Task completion must be checked separately from factual support. A true price
  does not by itself answer a stock, collection or alternative request.
- Both candidates share visible requirements, workload, public records, starting
  business state and relevant execution settings/resource limits. Identify the
  changed factor; otherwise report Not comparable rather than rank results.
- A recorded inspection is not a fresh test of a changed prompt, model or code.
  Repeat fresh AI executions where needed and show counts, variation and failures.
- Mandatory correctness/safety failures disqualify a candidate before efficiency
  tradeoffs. Missing or incompatible evidence cannot create eligibility.
- Report useful completion, wrong answers, refusals, human referrals, cost and delay
  separately. Blanket refusal is not useful completion, and unknown cost is not zero.
- A model may help interpret evidence but cannot own protected expectations,
  assessment, selection or promotion. A second model is not an independent oracle.
- Protect the student's authorship: preserve predictions and revisions, chosen tests,
  code changes and accepted help. Passing service tests does not prove sound reasoning.

The review in `SHIFTWORK_PIVOT2.md:82` identified source-level mismatches involving
request relevance, changing operational workloads, latest-version inheritance and
experiment side effects. These are review findings, not new runtime reproductions.
Their repair belongs to revised Gates 2 through 4, not this document-only pass.

## 6. Authority boundary for subsequent gate revision

| Actor | Proposed responsibility | Excluded authority |
| --- | --- | --- |
| Learner | Requirements within mandatory bounds, hypotheses, tests, candidate code and explicit choice | Protected expected answers, assessment rules, credentials or self-declared eligibility |
| Service AI | Meaningful interpretation and information/tool selection within the application | Protected assessment, credentials, promotion or ledger rules |
| Optional assistance | Attributable hints, explanations and labelled proposals after learner commitment | Silent ownership of core decisions or approval of its own answers |
| Independent assessment | Check observed outputs and reduce operational consequences under visible rules | Invent success from narrative or confidence |
| Operator | Controlled execution, credential custody and reviewed scenario material | Silent changes to a learner's outcomes |

The old bounded-assistant design does not by itself authorize inference inside
learner code. Secure mediation, isolation and provenance require explicit Gate 2/3
revision. Repeated probing, protected-case leakage, rotation and budgets remain
constraints; filesystem hiding alone is insufficient.

## 7. Organiser technology and track hypothesis

The final pivot recommends meaningful Nemotron behavior inside the service on
Nebius Token Factory, not merely fictional stakeholder dialogue. Controlled
execution should run learner-written repairs and retain inspectable evidence.
Actual access, networking, credential protection, latency and costs remain unverified.
The existing trusted local fixtures are not arbitrary-learner-code isolation.

**Best Apps and Agents** remains the recommended track, subject to real qualifying
use. Do not claim Coding and Agentic Engineering without a qualifying code-writing,
running and testing agent that preserves learner authorship. The hackathon checklist
remains in `../HACKATHON_REQUIREMENTS.md`; no new official-rule claim is made here.

Literal vendor exclusivity is false: other providers could substitute. Whether
removing meaningful inference or controlled execution weakens the learning workflow
is an evidence question. Let learners replace unnecessary AI subtasks with ordinary
code; do not manufacture dependence by forbidding good engineering.

## 8. Tavily is optional

Retain reviewed mission curation only when discovery changes an executable
engineering problem, not just its prose. Retrieved material is untrusted until a
human verifies authority, applicability, freshness and reuse rights and freezes it
into a scenario. Live web content must not determine protected assessment.

Compare frozen curriculum, realistic polling of known pages and discovery. Let
polling keep previously discovered URLs. Drop the prize/centrality claim if discovery
adds no useful constraints beyond polling or costs too much review effort. The old
Gate 3 historical-replay design and Gate 4 bonus decision are preserved in those
documents, not silently re-approved or executed for the pivot. Any change to them
must be reconciled in the corresponding later gate.

## 9. Evidence plan to revise at later gates

### Central mechanism

Retain the existing causal persistence proof and add the pivot obligations: a real
request, evidence-led diagnosis, comparable candidate executions, task-relevant
independent assessment, explicit tested-version selection and later operation of
that exact version. A separate later-condition alternative experiment must not
mutate operational history. Kill conditions include hidden-answer/credential access,
comparison contamination, wrong-version inheritance and narrative-only consequences.

### Reduced-assistance transfer

Retain the 20-percentage-point north star as an unproven target, with no extra median
time or hint budget against a strong matched static tutorial. Separately assess
learner reasoning, authored code/tests, accepted help and voluntary return. Northline
introduces commitments, safety escalation and retry-safe state changes. Study rubric,
feasibility and sufficient sample size require revised Gate 3 approval; human
recruitment remains separately authorized. The manual mockup kit is still unrun.

### Tavily ablation

Keep optional and fail closed on the centrality claim. A curation result cannot
substitute for proving the core repair/choice/inheritance mechanism.

## 10. Scope and prior evidence retained

Keep one role, Bellwether plus a Northline transfer engagement, a persistent service
and the selected operational room. First demonstrate one complete Bellwether loop.
Do not add careers, arbitrary projects, autonomy curricula, multi-agent teams,
marketplaces, AI-generated challenges or decorative progression to chase a score.

Useful Hatchery mechanisms remain versioned artifacts, branchable practice,
independently authored checks, regression protection, separation of data changes
from procedural failures, attributable scaffolding and fixed authority boundaries.
Hatchery's household assistant, pets, permission growth and background automation
remain excluded. Other closed directions stay closed.

Historical evidence recorded in `00-status.md` includes local/recorded execution,
sealed evaluation, deterministic ledger, isolation-guard repairs, rotation/repair,
close/inheritance/restart pre-proof and the accepted Slice 9 room. The Slice 6 audit
and repair history is preserved, including the rejected coverage claims and later
failing-capable re-review. Test 50 was partial, test 29 deferred, and the specified
2026-09-19 audit excluded packaging. Do not turn those dated reports into a claim
that today's pivot or a fresh full suite has passed.

No Token Factory Sandbox execution, learner study, transfer gain or Tavily ablation
is established by this revision. Existing acceptance does not prove the new workflow.

## 11. Forecast and adjudication history

| Forecast | Status |
| --- | --- |
| 27/40 current proposal, 31/40 pre-evidence cap, conditional 35/40 | Historical pre-pivot forecasts, not achieved scores |
| 32/40: Technology 8.5, Design 8.0, Impact 8.0, Idea 7.5 | Final-pivot working forecast assuming competent delivery, not today's build or judging prediction |

The earlier pre-selection verdict was `REVISE SHIFTWORK BEFORE ADOPTION`.
The pivot verdict is **revise, then pursue**. A course plus debugger remains a strong
substitute; no proven new category or learning gain is claimed. The optional
refinements do not earn automatic points and no deduction is invented for absent
user studies or adoption figures. Internal /40 scaling is not the official score
format; the four official criteria remain equally weighted.

## 12. Immediate next action

Finish and review Gate 1's product, six static screens, visual requirements and
manual test kit, then request explicit re-approval. After approval, revise Gate 2,
then Gate 3, then Gate 4, each with its own approval pause. Only then consider the
first authorized implementation slice. Preserve all completed code and evidence;
do not resume old Slice 10 or treat the pivot as a new comparison panel alone.
