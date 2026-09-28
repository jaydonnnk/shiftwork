# Architecture: Shiftwork final pivot

**Current Gate 2 state: RE-APPROVED 2026-09-28.** The user approved the repaired
section 8.1 together with Gates 3 and 4 and ADR 0006 after the review round
recorded below. Fixture review, sealing and live execution remain separate.

**Gate 2: RE-APPROVED 2026-09-24 after the legacy first-choice backtrack.**
The earlier final-pivot approval and commits remain historical. An adversarial
review found that a closed v5 shift with no learner selection could not open the
shift needed for its first comparison. The user explicitly approved this revised
path and requested Gate 3 next. It is architecture, not implemented behavior or
approval of Gates 3 and 4.
Gate 1's records were merged/pushed as `821a24c`. Old Slice 10 remains suspended.

Prior approvals: 2026-09-15, then 2026-09-19 for orchestration-owned sealed loading
and pure evaluator inputs. Those decisions and their evidence retain their original
scope. The pre-pivot architecture remains available in Git at `fb73c78`. This revision
retains its section numbers so dependent documents can be reconciled explicitly.
That 2026-09-24 revision changed no runtime code, fixtures, credentials,
packages, deployment or ADR.

**SCOPED BACKTRACK RE-APPROVED, 2026-09-26:** the user approved the section 13
file readback rule after the Slice 12 checkpoint mismatch. Gate 3's matching
correction was separately re-approved on 2026-09-26. Neither approval supplies
a live capability verdict or implementation authority. See `00-status.md` for
current authority.

**GATE 2 SCOPED BACKTRACK RE-APPROVED, 2026-09-28:** Slice 15 review found that
the present protected inventory supplied six labels over the same public
requests and state, without distinct hidden stimuli. Section 8.1 now specifies
the protected phase: each variant carries its own request, task spec and
additive-only state delta; it reaches both candidates of its pair as a separate
protected phase after the public batch, frozen with the public batch before any
run and never projected to learner-facing surfaces. The user approved this
revision in chat on 2026-09-28 and asked for Gate 3 next. The present Slice 15
protected inventory and candidate bytes remain unsealed and ineligible until
the Gate 3 reconciliation, fixture authoring and a separate operator review.
This approval changes no runtime behavior, sealed material or historical
approval above, and supplies no implementation authority by itself.

**GATE 2 SCOPED BACKTRACK, IN PROGRESS 2026-09-28:** an independent adversarial
review of that section 8.1 revision returned STOP with 2 BLOCKER, 6 MAJOR, 10
MINOR and 2 NIT findings across Gate 2 and Gate 3, recorded in `00-status.md`.
Two concerned this document. First, section 8.1 mounts sealed-derived stimulus
into a candidate sandbox, which ADR 0001 forbids in terms and no gate superseded;
item 3 now cites `docs/adr/0006-protected-comparison-stimulus-boundary.md`, which
splits a sealed comparison case into stimulus that may reach a workspace and
controller-held assessment inputs that may not, and names the resulting bounded leak channel
rather than denying it. Second, item 5 released aggregate protected counts
against ADR 0001's bar on hidden counts; ADR 0006 Decision 4 records why those
counts are not hidden counts, since each equals the comparison's already-public
pair count or a partition of it. Item 5 is also corrected internally: it
previously listed the protected request and resolved state as controller-only
while item 3 requires streaming both into the candidate workspace. Section 8's
shared denominator is qualified as public, and section 19 carries the ADR 0006
row. At this backtrack point, ADR 0006 was PROPOSED and not in force. The
re-approval recorded at the top supersedes that pending state. No
implementation, operator review, seal, live run, install, commit or push was
implied by the backtrack repair.

## 1. Fit

Keep the implemented Python/FastAPI controller, SQLite store, static HTML/CSS/
vanilla-JavaScript client and operational room. Do not restart the application or
introduce a framework, separate database, task queue or microservice deployment.

Source inspection on 2026-09-24, not a new test run:

| Existing mechanism | Evidence | Pivot change |
| --- | --- | --- |
| Immutable files + contract + catalog hash | `shiftwork/orchestrator.py:197`, `shiftwork/store/repo.py:171` | Retain; use explicit candidate IDs rather than the newest version |
| Latest-version inheritance/start/close | `shiftwork/orchestrator.py:147`, `shiftwork/orchestrator.py:238`, `shiftwork/orchestrator.py:587` | Replace with an explicit operating selection |
| Captures automatically enter operational finalization | `shiftwork/orchestrator.py:315`, `:518` | Separate experimental assessment from operational consequences |
| Each attempt draws a new workload | `shiftwork/orchestrator.py:269` | Freeze a shared comparison workload across both candidates and repetitions |
| Checks establish support/freshness, not requested-task completion | `shiftwork/evaluator/evaluator.py:174`, `:194` | Add independent request/entity/task assessment |
| Exact consumed shop bytes are retained, other inputs are partly transient | `shiftwork/orchestrator.py:329`, `:352`, `shiftwork/store/schema.sql:55` | Persist the complete execution and assessment context |
| Recorded replay and pinned trusted-local execution | `shiftwork/executor/recorded.py:17`, `shiftwork/executor/local_process.py:74` | Keep offline paths; add verified isolated execution with mediated service inference later |

Schema version is currently 5 (`shiftwork/store/db.py:7`). `Run` has no purpose or
selection reference (`shiftwork/domain/models.py:187`). Assist, experiment and
selection storage/routes do not exist. Current execution supplies no inference
grant (`shiftwork/orchestrator.py:365`). Slices 1 to 9 are the recorded foundation,
not proof that the approved pivot works.

## 2. Runtime and module boundaries

One controller owns durable truth. An executor workspace is disposable and never
authoritative for assessment, selection or business history.

| Boundary | Responsibility | Excluded authority |
| --- | --- | --- |
| Web client / API | Station views, learner input, public evidence; API validates and delegates | Cannot supply trusted verdicts, operating pointers, protected paths or provider credentials |
| Controller orchestration | Investigation, experiment, selection and operation lifecycles; sealed loading; transactional writes | Does not delegate eligibility or history writes to models or learner code |
| Artifact/persistence layer | Mutable draft, immutable versions, captured contexts, append-only evidence and selection history | Never imports the sealed loader or infers selection from save order |
| Executor adapter and trusted request driver | Provision exact version and public data, stream permitted requests, observe outputs and enforce limits | Cannot read sealed cases, grading rules, ledger internals or provider secrets |
| Learner service | Code, request interpretation, allowed information/tool selection and responses | Cannot choose authoritative request identities, grading, eligibility or operational mutations |
| Service inference gateway | Controller-side, bounded Nemotron calls for service behavior; trusted usage/timing capture | No sealed loader, evaluator/ledger access, arbitrary URL proxy or provider secret in returned data |
| Assist gateway | Optional attributable orientation, hints and patch proposals | No diagnostic help before learner cause/falsifier; no silent selection or self-grading |
| Pure evaluator / comparison policy | Independent task/correctness checks and evidence eligibility from explicit inputs | No files, database, network or model calls; no automatic winner |
| Pure ledger reducer | Operational captures and checks to synthetic event drafts | No experiments or selections as business results |
| Sealed store | Protected cases and historical assessment material, loaded only by orchestration | No browser, learner, executor, gateway or curation access |
| Curation tool | Offline, human-reviewed mission-source discovery | No runtime customer answering or live grading |

Retain the controller-owned request-driver boundary in the implemented executor
manifest (`shiftwork/executor/base.py:111`). Stream only the current permitted
request to the service; do not provision a future workload or protected expectations.
Real transport and hostile-code isolation remain subject to a separately
authorized capability spike and live-adapter proof, not assumed from the trusted
local adapter. These are module boundaries, not new hosted services.

## 3. Endpoints

Retain existing routes in `shiftwork/api/routes.py:37-140`. Proposed additions and
changed semantics are below; request/response schemas belong to Gate 3.

| Route | Verb | Purpose / status |
| --- | --- | --- |
| `/` | GET | Existing static client and room |
| `/api/engagements/{slug}/board` | GET | Existing; project operating selection separately from draft/candidates and latest experiments |
| `/api/engagements/{slug}/shifts` | POST | Existing; normally inherit the selected version. For an existing engagement whose latest v5 shift is closed and which has no selection, the controller instead opens a labelled non-operational requalification shift for first-choice work. The caller cannot request this exception or turn it into operation. |
| `/api/shifts/{id}/artifact` | GET/PUT | Existing mutable draft; saving cannot select or operate |
| `/api/shifts/{id}/artifact/versions` | POST | Existing freeze; record explicit parent/version ancestry, not promotion |
| `/api/artifact-versions/{id}` | GET | New: retrieve owned candidate source/contract with safe logical filenames, never host paths |
| `/api/shifts/{id}/investigations` | POST | New: append cause, falsifier and chosen public test; revisions link to prior entries |
| `/api/investigations/{id}` | GET | New: original prediction, revisions, evidence and attributed help |
| `/api/shifts/{id}/experiments` | POST | New: freeze diagnostic or paired-comparison plan and reserve its bounded execution schedule |
| `/api/experiments/{id}` | GET | New: public conditions, every trial, comparability, eligibility and missing evidence |
| `/api/shifts/{id}/selections` | POST | New: explicitly select a tested version from a completed eligible comparison; retain rationale and alternative |
| `/api/engagements/{slug}/selections` | GET | New: selection history and current validity, including original decision context |
| `/api/shifts/{id}/runs` | POST | Existing, narrowed to operation of the current operating selection or a labelled initial starter on a newly seeded engagement; no operation in a no-choice requalification shift |
| `/api/runs/{id}` | GET | Existing; include immutable purpose, execution mode, version and experiment/selection linkage |
| `/api/runs/{id}/outputs` | GET | Existing; retain bytes and add observed interpretation, tool/inference events and input provenance |
| `/api/runs/{id}/checks` | GET | Existing safe check projection; no protected expected content |
| `/api/engagements/{slug}/ledger` | GET | Existing operational history only |
| `/api/incidents/{id}` | GET | Existing operational evidence and resolution linkage |
| `/api/shifts/{id}/close` | POST | Existing; close from the selected contract/limits, not an unselected candidate |
| `/api/shifts/{id}/assist` | POST | Planned, not implemented: controller-enforced prediction and assistance-budget checks |

Later-condition comparisons use the experiment endpoint with a reference to an
already-observed operational context. There is no endpoint to turn an experimental
run into an operational run or copy its consequences into the ledger. The service
inference channel is executor-controlled, not a new public/browser proxy route.

## 4. Data

Keep one relational store. Names below describe proposed additions/changes, not
DDL or a migration implementation. Gate 3 owns fields, constraints and signatures.

| Record | Data retained | Main reads/writes |
| --- | --- | --- |
| Existing engagements/config/shifts | Scenario identity, active requirements, separate execution/exposure/assist ceilings, and an explicit non-operational requalification state for legacy no-choice shifts | Resolve active policy; atomically open/close shifts and lift the operation block only with a valid explicit choice, never from a draft |
| Existing drafts/artifact versions | Exact source, explicit parent, committed contract/catalog, attributable authorship | Save draft; freeze; retrieve by ID/hash, not latest for operation |
| `investigations` | Cause, falsifier, public test, source run/request, revision parent and author/time | Append original/revision; gate diagnostic assistance |
| `experiments` | Diagnostic vs comparison intent; candidate IDs; immutable shared context; declared treatment; complete trial schedule; optional observed-later-context ref | Reserve once; fetch all scheduled/completed/failed slots; derive status |
| Existing runs | Immutable purpose; experiment/slot or selection ref; exact context; adapter and execution mode; terminal outcome | Allocate a slot once; bind operation atomically; restart recovery |
| Existing outputs/check results + execution events | Raw responses; task checks; observed tool/inference requests/responses; trusted usage, timing, missingness and provenance | Inspect by run/request/version; reproduce assessment from captured inputs |
| `operating_selections` | Exact version/hash, comparison evidence, retained alternative, rationale, prior selection and original requirements | Append a deliberate choice; resolve the latest explicit selection and its validity, never fall back to an older choice |
| Existing rotation draws/exposure records | Comparison- or operation-scoped reservation; family/cycle; invalidation; linkage to all dependent trials | Reserve unexposed inventory atomically; never recycle exposure |
| Existing ledger/incidents | Operational event chain, run/output/check causes, incident state and selected resolving version | Operational finalization only; close retains explicit limit declarations |
| `assist_events` | Role, prediction ref, prompt/response evidence, acceptance/rejection, consumed shared budget | Append calls; audit authorship without affecting eligibility |
| `mission_sources` | Frozen source content/provenance and human verification | Operator curation only, as previously planned |

A captured context includes exact request bytes/order, public data and dependency
condition, starting synthetic business state, contract/catalog/mandatory-policy
identity, visible tests, protected assessment-set identity, evaluator/reducer
version, executor/harness/image identity, model/prompt settings and resource limits.
Store reconstructible content as well as hashes; a hash plus mutable pathname is
not sufficient. Protected material stays in the restricted store, not in public
manifests. Exact storage layout and historical scorer retention belong to Gate 3.

The service receives only data it may legitimately consume. Authoritative records
and independently authored expectations can intentionally differ from stale service
data. Bind both layers to the trial; never reconstruct old evidence from today's
incident state or currently installed fixtures.

Migration must preserve every old capture, event, incident, catalog and version hash.
Old runs are labelled legacy operational/replay evidence, not invented experiments
or selections. Missing historical inputs remain unknown. Legacy engagements without
a recorded choice require a fresh qualifying comparison and explicit selection
before pivot operation resumes; migration must not manufacture learner consent.
Opening the requalification shift records its limited purpose, not a selection or
an operating version. It uses the last owned immutable version only as the draft's
starting source and ancestry; the historical version and closed shift are not
rewritten. New engagements explicitly install a labelled starter operating version.
That starter exception never applies to migrated engagements. Northline retains its
separate engagement and blank learner artifact, not bookshop inheritance.

## 5. Flow

### Legacy first-choice bootstrap

1. After migration, a closed v5 shift and absent selection leave the board in a
   labelled `Needs first choice` state. Existing captures, incidents and ledger
   remain inspectable with their original evidence labels; missing inputs stay
   unknown. There is no implied starter, learner choice or operating pointer.
2. The existing shift-open route atomically checks that this is an existing
   engagement with no open shift and no selection, then opens one non-operational
   requalification shift. It seeds an editable draft from the last owned immutable
   version, if present, solely for repair work. If no such version exists, only
   that engagement's approved initial draft may seed editing (Northline remains
   blank), still without operation.
   This server-derived branch is not a caller-supplied mode or consent flag.
3. In that shift the learner can inspect inherited evidence, record a cause and
   falsifier, edit/freeze candidates, run permitted experiments and append an
   explicit eligible first selection. Those activities cannot write operational
   events or resolve incidents. They retain the same protected-case, trial and
   assistance limits; opening a shift does not refund prior exposure.
4. Until the first selection is durably appended and revalidated, run start and
   selected-contract close refuse. The selection transaction lifts the shift's
   operation block; the same shift may then operate only the chosen exact version
   under the ordinary operation rules. A failed or
   incomplete comparison leaves the path non-operational; Gate 3 must specify
   bounded recovery without inventing consent or recycling exposure.

### Investigate and experiment

1. Open the board and inspect an operational failure using its exact request,
   version, interpretation/tool observations, public records and output.
2. Append the learner's cause and falsifier before diagnostic help. A revision
   preserves the original; orientation can precede it without suggesting a cause.
3. Save/freeze candidates. A diagnostic experiment can vary a learner-visible test
   or allowed public input; it produces evidence but cannot establish eligibility.
4. For repair comparison, freeze both versions, shared requirements and context,
   the declared difference and full repetition schedule. Orchestration reserves
   protected exposure and execution capacity before any trial begins.
5. Execute each scheduled trial in a new workspace from the same captured starting
   state. Capture observations and gateway usage; missing/failed slots stay visible.
6. Orchestration supplies the pure evaluator with complete pinned inputs. Experimental
   finalization writes only experimental captures/checks/status, never ledger events,
   incident changes, declared limits or an operating selection.
7. The comparison policy derives shared comparability/completeness and each
   candidate's eligibility from all required evidence. An observed mandatory failure
   disqualifies that candidate, not a fully evidenced passing alternative. The UI
   shows Not comparable, Incomplete, Ineligible or Eligible as applicable, not a winner.

### Choose and operate

1. The learner names an eligible version and rationale from a completed paired
   comparison. The controller revalidates ownership, hashes, shared current
   requirements, complete evidence and non-invalidated exposure in one transaction.
2. Append the selection and retain the other candidate and original evidence. Saving,
   freezing, passing tests or closing the shift never performs this action implicitly.
3. Operation binds the current selection/version and starting business state before
   execution; a later save cannot change either. The initial starter on a newly
   seeded engagement is labelled as an unqualified baseline, not a learner-selected
   passing repair. A migrated engagement has no such operating starter.
4. Execute the operating version against the current shift's controller-selected
   workload. Independently assess the captures and atomically derive operational
   events and incident changes. Selection alone cannot resolve an incident.
5. Close inherits the selected version, rationale, alternative, unresolved incidents
   and limits. Closing can record limit declarations, never synthetic sales or a
   claim that the service was repaired. Restore reconstructs from controller state.
6. Once a later condition has occurred, a new experiment compares the retained
   candidates with fresh trials under that observed context. It cannot replace the
   operational run, edit the prior choice, resolve an incident or rewrite the ledger.
   Switching versions afterward requires a new eligible comparison and explicit choice.

## 6. Versioning, selection, restart and restoration

One mutable draft per shift remains sufficient. Two immutable version references
supply A/B candidates; no Git-style workspace/branch service is needed. Restoring a
candidate into the draft records its actual parent. Content changes require another
freeze and new evidence; a different version ID with identical content is not proof
of repair. Same code may behave differently under a changed context, which must be
recorded as the changed factor rather than attributed to a code repair.

The operating selection is separate from the artifact timeline. Its original
comparison, requirements and rationale stay immutable. Later outages or requirement
changes can expose new failures without retroactively rewriting that decision.
Operation uses current mission conditions and mandatory policy, both pinned on the
new run; the original selection never claims to satisfy every future condition.

Serialize operational starts per engagement. Selection and close refuse while an
operation is in flight; selection checks the expected prior selection to reject a
stale browser action. Experiments remain isolated from the current operational state.
Repeated requests cannot allocate duplicate trial slots, selections or consequences.
The requalification shift is explicitly non-operational until the first valid
choice. An incomplete comparison never promotes its draft or a historical version.

Restart marks interrupted runs failed, retains partial evidence, exposure and usage,
and performs no automatic paid retry. Incomplete comparisons cannot be selected.
Finalized trials remain finalized; recovery cannot route experiments into operational
finalization. Close refuses nonterminal work, retaining the existing startup-only
recovery limitation until its separately specified implementation is revised.

## 7. Evaluator, credential and sealed-case isolation

Preserve orchestration-owned sealed loading and a pure, LLM-free evaluator. API,
executor, persistence, domain, ledger, client, service/assist gateways and curation
must not import/call the loader. Public projections contain no protected case text,
identities, expected answers or host locators. Public result IDs remain usable for
cause links; an opaque expected digest is correlatable, not proof of secrecy.

Task assessment is independently authored, not the service model grading its own
interpretation. Match requested entity, each required task and applicable conditional
branch against validated structured outputs and cited records. For the illustrative
collection-and-alternative request, a true price alone cannot pass. A claim of
completion in a trace is not evidence of completion. Keep customer text derived from
the validated response envelope; do not allow unassessed free text to contradict it.
Gate 3 must define the envelope, visible obligations, task-check rules and missing-
output behavior. Existing price/stock fixtures do not prove these new checks.

Mandatory task/correctness/safety rules apply regardless of learner preferences.
Learner tests/constraints may add requirements, not waive mandatory ones. Unsupported
claims, wrong entities, unmet required tasks and invalid commitments disqualify the
candidate. Report useful completion, incorrect output, justified refusal, clarification
and human referral separately. Public completion requirements must make blanket
refusal/referral ineligible; exact thresholds and bounded task rubrics belong to Gate 3.

**Credential decision:** use controller-side service-inference mediation, not a
provider key injected into learner code. Provider/provisioning credentials stay in
trusted gateways/control processes; Tavily credentials stay in operator curation.
The sandbox, learner/browser, prompts, captures and model outputs receive none.
The old conditional `InferenceGrant`/scoped-key approach is not the pivot design.

The executor supplies a run-bound channel to the service gateway. Trusted transport
binds the run identity, allowed model, request size, token/call/deadline ceilings
and lifetime; a caller-supplied run ID cannot grant access to another run. The gateway
is not an arbitrary HTTP proxy and cannot expose controller APIs, filesystem access
or hidden assessment. Separate workspaces have no access to controller/host networks
except the verified restricted channel. Close/termination revokes it. The safe
transport is an explicit spike obligation; if it cannot be verified, fail closed
rather than injecting a key or running arbitrary learner code locally.

## 8. Fair comparison and repeated-probing controls

A comparison freezes both candidates before any protected result is released. Both
receive the same workload, public records, starting state, requirements, visible
checks, dependency conditions, execution class and resource ceilings. Model/settings
are matched unless the declared treatment intentionally changes them; record the
actual settings and flag any other drift. Prompt/code differences are frozen in the
candidate identity. Do not pretend stochastic model outputs can be made identical.

Reserve one protected case set for the whole bounded comparison, with explicit
trial membership and a predeclared paired/interleaved order. Reset service/cache/
booking state between trials. Reuse within that frozen comparison is planned exposure,
not a fresh holdout per repetition. Changing either candidate, requirements or plan
creates a new comparison with a new reservation; never adapt one candidate to interim
results while retaining the other's original score. Operational draws stay separate.
Diagnostic public tests cannot read protected inventory or create eligibility.

Count all allocated trials, attempts and gateway usage against durable budgets.
Failures, abandoned comparisons and restart do not refund exposed cases. Fixed
repetitions and retry rules are chosen before viewing results; there is no rerun-
until-pass selection. Gate 3 must choose feasible limits and inventory sizes rather
than inheriting the old three-run budget or mockup's illustrative three repeats.

Eligibility requires comparable, complete, non-invalidated execution evidence for
the exact versions and all mandatory checks passing across required trials. A
comparison is not complete merely because its successful rows passed. Show every
trial and one shared public denominator per candidate, with the section 8.1
protected step accounted on its own denominator that is never merged into the
public one; account for skipped/missing requests explicitly in both.

Recorded inspection is never fresh execution or new repair eligibility. Fresh
trusted-fixture checks establish only labelled offline pre-proof, not eligibility
for arbitrary learner code or real-model behavior. Code-only repairs remain valid
when freshly executed through the same approved isolation class. No AI call is
required merely to satisfy a metric if ordinary code solves the task correctly.

Store trusted elapsed time and provider usage separately from learner claims.
Unknown cost is unknown, not zero; do not rank on an unavailable metric. If that
metric is a mandatory budget constraint, unknown evidence blocks eligibility.
Keep service latency, provisioning overhead, calls and model usage distinguishable.
No aggregate score may conceal a mandatory failure or automatically choose a repair.

### 8.1 Protected task stimuli: distinct phases, frozen together, never public

The current Slice 15 reservation stores a protected case identity and a rule
aspect per pair, but executes only the two public requests in each pair. Six
different case labels cannot establish six independent task variants when the
request and state remain identical. Treat that draft as unsealed and ineligible.

Revised decision, drafted 2026-09-28 for explicit re-approval: each protected
variant carries its own controller-held customer request, its own public task
specification and a bounded additive public-state delta. It reaches both
candidates of its pair as a separate protected phase that follows the pair's
public batch, so the reviewed public workloads always execute against the
reviewed comparison state and no hidden delta can change a public request's
expected answer. The design:

1. **Separate comparison state.** A comparison binds its own reviewed public
   state. The accepted Slice 11 state (`bookshop_pivot_public_state.json`) and
   its byte pins are unchanged and stay attached to the investigation path.
   Gate 3 fixes the comparison state file, its pin and the guard that re-verifies
   both.

2. **Protected variant content.** Each sealed variant of the enabled comparison
   family carries its own request row (distinct request id, text and entity),
   its own task specification, and an additive-only state delta over the frozen
   comparison state. A delta may add entities and records; it may never rewrite,
   re-date or remove the frozen state's records, so the public requests'
   expectations are provably untouched. Gate 3 owns the exact schema, bounds and
   validation for variant and delta.

3. **Delivery and order.** A slot executes as two phases over one run identity.
   The public phase streams exactly the frozen public batch under the frozen
   comparison state. The protected phase streams exactly one hidden request at
   its predeclared ordinal (the public count plus one) under the frozen state
   resolved from the comparison state plus its variant's delta, in a fresh
   workspace with no carryover from the public phase. Within a pair, A and B
   receive byte-identical public batches and byte-identical protected stimuli in
   the same order and under the same ceilings; only the declared treatment may
   differ between them. A missing, mismatched, reordered or unavailable stimulus
   fails that slot closed: no refund, no retry, and the failure stays visible.
   Sealed-derived bytes therefore reach a candidate workspace by design, which
   ADR 0001 forbade in terms; the boundary that permits it is
   `docs/adr/0006-protected-comparison-stimulus-boundary.md`, and only the
   request row and the resolved state cross it. The candidate service is
   learner-authored code that can read its own workspace snapshot, so this is a
   named and bounded leak channel, not a denied one: ADR 0006 Decision 3 states
   its three bounds and item 6 below states its invalidation consequence.

4. **Freezing.** The reservation records one drawn variant per pair (existing
   exposure items), stores the canonical variant payload behind the restricted
   reservation, and stores the resolved protected state bytes with their digest.
   The comparison context covers the public batch and the protected bindings
   (pair ordinal, variant ref, request ordinal, stimulus and state digests) in
   its content hash before either candidate runs. The bytes that execute are the
   bytes reserved: execution reconstructs them from the restricted reservation,
   never from a mutable file or the current inventory.

5. **Privacy.** Protected material stays off every learner-facing surface, but
   its classes differ in where they may go. Controller-held assessment inputs stay
   controller-side and never enter a workspace or a prompt: the task
   specification, the authored delta, the expected block and variant identities.
   The per-request assessment is produced controller-side. The raw protected
   response and service logs originate in the candidate workspace, then become
   restricted controller captures; they cannot be classified as never entering it.
   Stimulus reaches the candidate workspace inside the protected phase only, as
   item 3 requires, and is still never projected: the protected request row and
   the resolved protected state. No learner-facing payload, error, log line or
   client bootstrap carries the stimulus, assessment inputs or retained
   execution artifacts, and no route serves a protected capture. The
   classification is ADR 0006 Decisions 1 and 2. Public
   evidence stays bounded by the frozen public workload count: before a slot runs,
   projections expose only counts; after the comparison is terminal, only
   aggregate protected counts and missingness may be released. Those aggregates
   are not hidden counts in ADR 0001's sense, because each equals the
   comparison's already-public pair count or a partition of it, so they disclose
   no inventory size, variant identity or expected value; ADR 0006 Decision 4
   records that reasoning and the terminal-only gate that keeps the count from
   becoming a mid-run feedback channel. The separately specified acceptance
   reading (Gate 3, Slice 16) may add aggregate pass/fail counts and an
   eligibility blocker naming only the public rule id; it may not release stimulus
   content or captured protected bytes. Gate 3 fixes the projector source and
   ordinal filters, then uses distinctive scanner needles only where
   substring matching can be meaningful; Gate 4 assigns the proof.

6. **Failure and leakage.** A suspected protected leak retires the affected group
   and invalidates all dependent comparison and operational evidence for future
   use. Recheck invalidation at selection and run start: a compromised selection
   blocks further operation until requalified, without silently choosing another
   version. Preserve prior choices, outcomes and ledger bytes; append any
   authorized correction, never roll history back. Existing invalidation
   readback is not this enforcement (`docs/adr/0001-sealed-evaluator-isolation.md:77`).

The present protected inventory is a draft of labels over identical public
stimuli and remains unsealed and ineligible. Its replacement (six variants with
distinct request or state stimuli and a concrete failure each) is authored,
validated and sealed only after this Gate 2 approval and the Gate 3
reconciliation it names.

## 9. Deterministic ledger ownership and replay

Only operational finalization can write service consequences or open/resolve an
operational incident. A distinct close transaction may retain limit declarations
and closed-unresolved status. Experiment and selection paths have no reducer/ledger
mutation authority, even if they reuse capture storage and the pure evaluator.

Keep pure reduction, centralized canonical hashing, hash-chain verification on read,
atomic/idempotent finalization and corrective events rather than edits. Resolution
requires operational regression evidence against the pinned incident rule and exact
operating version; a changed version ID or experimental pass is insufficient.

Replay means re-assessing the original captured inputs with the recorded rule version
and reproducing check/event derivation, not executing yesterday's model output again
or changing existing rows. Chain/hash verification alone does not establish semantic
reducer replay. Preserve both proof obligations for Gate 3. All business quantities
remain explicitly synthetic, never revenue, trust, competence or learning evidence.

## 10. Nemotron responsibilities and learner authorship

Nemotron performs meaningful behavior inside the starter service, such as interpreting
requests and proposing information/tool selection. Learner code owns the control flow
and exact transaction/stock rules. Ordinary code may replace unnecessary AI work.
Observed model outputs and tool calls are investigation evidence, not authoritative
explanations of the model's internal reasoning.

Optional assistance is a separate role/budget from service inference. Orientation can
explain controls; hints, diagnoses and labelled patch proposals require the learner's
initial cause/falsifier. Gate this in the controller, not only by hiding a button.
Record original reasoning, chosen tests, authored source and accepted/rejected help.
Models never own requirements, experiments, grading, promotion or the final choice.

The deterministic controller/evaluator remains testable offline. That does not make
recorded transcripts an adequate demonstration of the pivot's AI-service learning
loop. Neither vendor exclusivity nor a measured learning-dependence claim is assumed.

## 11. Tavily mission-curation boundary

Retain operator-run discovery from allow-listed official sources, human verification
and freezing into executable mission material. Curation does not load protected
assessment or decide pass/fail; operator case authoring is a separate restricted step.
Tavily is absent from the learner answer path. Retrieved material is untrusted input,
not instructions or live assessment. Keep source rights, applicability and timestamps.

Retain the frozen/polling/discovery comparison, including polling's retained known
URLs. The historical Gate 4 bonus decision remains historical until reconciliation.
Claim no bonus or centrality without a shipped qualifying call and the applicable
KEEP verdict; remove the claim if discovery adds only links/prose or fails its ablation.

## 12. External services and configuration

Only proposed live dependencies: Nebius Token Factory inference/Sandboxes; optional
Tavily in curation. No new external service, webhook or hosted deployment is introduced.

Environment names only: existing `SHIFTWORK_DB_PATH`; provider-auth names are
`NEBIUS_API_KEY` (the IAM token, also accepted as `CONTREE_TOKEN`), `NEBIUS_PROJECT_ID`
(sent as the `Project` header; client aliases `CONTREE_PROJECT` and `NEBIUS_AI_PROJECT`)
and `TAVILY_API_KEY`. Exact SDK/auth wiring, service/assist model configuration,
resource ceilings and image pins belong to Gate 3 plus verified capability evidence.
Do not create or inject `SHIFTWORK_LEARNER_INFERENCE_KEY`. No actual key, current model
availability or credential authorization is implied here.

## 13. Observability and execution evidence

Keep one navigable chain per run/request/version: exact request, observed interpretation,
tool/data use, output, independent checks, and operational consequences where applicable.
Every view names its purpose and evidence mode. A later comparison has its own identity,
not a replacement row in an old run. Original-choice and later-condition views remain
separate. Missing observations are visible; uninstrumented service claims are labelled
as such rather than treated as trusted tool/usage evidence.

Persist raw service and gateway evidence before derived views. Trusted executor/gateway
boundaries own measurements and observed request/response events. Limit and validate
untrusted payload size/shape; render as text, never executable HTML. Keep provider
transport headers, secrets, protected inputs and host paths out of all learner-facing
logs/errors as well as normal responses. Gate 3 must specify and prove each serialized
surface scanner can actually detect its needle.

**Approved capture correction:** an outer Sandbox operation `SUCCESS` and process
stdout are insufficient evidence that a checkpoint retained written artifacts.
Before any file-backed capture is accepted, the controller must read the saved
file, record its actual byte count and digest, and compare it with trusted
expected bytes when the run manifest defines them. It may not substitute a
process's claim about a file for the retrieved bytes. A missing file, failed
readback or mismatch with a declared expected artifact marks the run incomplete
and prevents comparison eligibility, selection and operation. A layer-limit or
snapshot failure may not silently produce accepted evidence. The Slice 12 spike
must establish a reliable transport/capture route before live learner code is
admitted; otherwise stop.

## 14. Local development and delivery boundary

Retain `recorded` for transcript inspection and `local_process` for byte-pinned trusted
fixtures only. Never relax those pins to run arbitrary learner repairs without the
verified isolation boundary. Offline doubles can exercise experiment/selection state
and policy but cannot earn live-execution or AI-repair claims.

Keep one learner and a loopback local controller as the initial delivery boundary.
A public multi-user service, authentication scheme or hosted operational database is
not implicitly approved. Submission delivery remains the Gate 4/spike decision, with
separate deployment authority. Do not silently drop the required live-inference and
real learner-code evidence to make packaging easier.

## 15. Track fit and evidence limits

Best Apps and Agents remains the primary hypothesis, now supported by proposed
Nemotron behavior inside the service rather than assistance alone. Actual qualifying
use must be demonstrated; no fresh official-rule or vendor-availability claim is made
here. `../../../HACKATHON_REQUIREMENTS.md` remains the checklist.

Coding and Agentic Engineering requires a qualifying agent that writes, runs and tests
code without erasing learner authorship; it is not claimed. Synthetic performance,
passing checks, an attractive room and this architecture do not establish human
learning, job-readiness, product uniqueness or prize merit.

## 16. Verified foundation and unverified integration

Verified here means source-inspected, not executed: S1's cited lifecycle, schema v5,
recorded/trusted-local adapters and absence of a working service-inference path.
Historical test/browser evidence remains in `00-status.md` with its original limits.
No suite, human study, fresh inference call or sandbox spike ran during this draft.

Earlier vendor research is dated: the pre-pivot architecture recorded sources on
2026-09-15; `../../../SHIFTWORK_PIVOT2.md` recorded additional documentation on
2026-09-23, including runtime networking/environment support. Neither establishes
this project's entitlements or a safe credential boundary. Do not repeat the older
absence-of-documentation statements as current facts or equate documented networking
with verified isolation. No primary source was fetched again in this drafting pass.

A separately authorized capability spike must verify:

- exact artifact/data transfer, request streaming, capture retrieval and cleanup;
- safe run-bound inference mediation without credentials or controller/host access
  from learner code, including attempted channel/identity misuse;
- real Nemotron request interpretation/tool behavior, model identity/settings,
  observed usage, latency, failure modes and feasible trial budgets;
- enforceable deadlines/resources/egress, dependency-outage simulation, clean trial
  resets and retained evidence after crashes; and
- a reproducible judge delivery path. Public ingress is neither assumed necessary
  nor asserted impossible. ADR #4 stays deferred to this evidence and authorization.

## 17. Failure containment

Incomplete, failed or drifted experiments retain evidence and cannot be promoted.
Selection checks and append are atomic; source edits cannot change a frozen version.
One in-flight operation prevents state/selection races. Provisioning or transport
failure retains available captures and writes no invented business result. Gate 3
must distinguish observed service refusal/outage behavior from missing execution
evidence; a timeout is not automatically a verified customer consequence.

Operational finalization is one transaction for checks, events, incident changes and
terminal state. Experimental finalization is a separate transaction with no business
writes. Interrupted work is not replayed as fresh inference; budgets/exposure persist.
Broken chains fail loudly. Leak invalidation blocks future eligibility/use while
preserving prior history. No automatic rollback, silent version substitution or
operator mutation surface is added merely to hide a failure.

## 18. Decisions to challenge before approval

| Choice | Rejected alternative | Tradeoff / unresolved evidence |
| --- | --- | --- |
| Reuse captures/evaluator, separate lifecycle authority | A UI-only experiment flag over the current finalizer | Requires durable purpose and transaction guards, but no duplicate execution engine |
| Frozen paired comparisons with bounded shared exposure | Compare sequential operational runs | Needs revised budgets/inventory; operational runs have different workloads and side effects |
| Explicit immutable selection history | Inherit latest saved or latest passing version | Adds one deliberate action; prevents silent promotion and retains the rejected alternative |
| Controller-mediated inference | Inject a scoped provider key into learner code | Adds a restricted channel whose feasibility must be proven; avoids readable provider secrets |
| Keep one draft and immutable candidates | New branching/workspace platform | Less simultaneous editing convenience, fewer moving parts |

Main uncertainties: curriculum/task-rubric quality, feasible repetitions under cost
and exposure limits, secure sandbox mediation, and whether the prediction/comparison
workflow improves learning rather than adding paperwork. Gate 1 remains approved;
these are engineering/evidence questions, not automatic product-score changes.

## 19. ADR reconciliation

Gate 2 is re-approved; reconcile the affected records with dated superseding
decisions in the appropriate later-gate work. Preserve original ADRs and their
evidence:

- ADR 0001: preserve loader ownership/purity; reconcile comparison-scoped exposure,
  gateway isolation and enforcement of invalidated evidence. Two of its Decision
  clauses are narrowed for the section 8.1 protected phase by ADR 0006; the
  narrowing was proposed during backtracking and took effect when the user
  re-approved this gate and Gate 3 S3.9 on 2026-09-28.
- ADR 0002: preserve chain/reducer rules; make experiment exclusion and semantic replay
  obligations explicit without rewriting old event history.
- ADR 0003: preserve immutable artifacts/restoration; supersede latest-version
  inheritance with explicit selection and extend captured execution context.
- ADR 0006: the section 8.1 protected-stimulus boundary. Splits a sealed
  comparison case into stimulus that may reach a candidate workspace and
  controller-held assessment inputs that may not, names the resulting bounded leak channel
  rather than denying it, and records why the released aggregate protected counts
  are not hidden counts. Gate 3 S3.9 and S6.4 carry the mechanism.
- ADR #4: still unapproved, dependent on the authorized integration spike.

## 20. Handoff to the next gates

**Gate 3, only after Gate 2 approval:** exact file map, types/signatures, route and
response contracts, task-aware envelope/evaluator, two finalization call stacks,
immutable context and historical replay format, migration from schema v5, trial/
exposure/inference budgets, idempotency/concurrency, safe gateway channel and trust
probes, reason/metric vocabulary, ancestry/authorship, revised learner-study rubric
and clause-level tests. Specify the section 8.1 protected phase exactly: the
separate comparison state file and pins, the variant request/spec/delta schema,
restricted storage, the two-phase execution order, the public projector filters
and scanner needles, the public and protected denominators, and the failing tests
for each. Specify the requalification shift state, legacy route and
board projection, first-choice transition, bounded failed-comparison recovery and
failing-capable tests that a closed v5 engagement can reach its first choice while
every no-choice operation and implicit promotion is rejected. New curriculum cases
require review/sealing; old evidence and catalog semantics are not silently repurposed.

**Gate 4, only after Gate 3 approval:** sequence visible vertical changes over the
completed Slices 1 to 9; map every old outstanding and new test clause to a real
prerequisite; schedule the bounded integration proof before dependent live claims.
Do not carry old Slice 10 to 17 numbering forward as an implementation instruction
without reconciliation. Preserve submission, transfer, curation and packaging
obligations, with separate authorization for installs, credentials, external runs,
outreach and deployment.

The user explicitly re-approved the earlier Gate 2 revision on 2026-09-24:
"i approve gate 2, commit to main, and then go to gate 3". After the legacy
first-choice backtrack, the user separately replied "Yep i approve gate 2,
start with gate 3 now". Gate 3 is next and requires its own approval.
