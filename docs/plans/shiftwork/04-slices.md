# Vertical Slice Plan: Shiftwork final pivot

**Gate 4: APPROVED 2026-09-24 for the final pivot. Not implementation authority.**
Gates 1, 2 and 3 are approved for `shiftwork_final_pivot.md`. Gate 3 was approved
and locally merged, then backtracked when this Gate 4 review found no qualifying
Northline selection path; that scoped correction is now re-approved and the
dependency order below reflects it. The 2026-09-19 Gate 4 approval
applies to the old design only and is historical. Slices 10 through 12 were
implemented and accepted by the user by 2026-09-27; Slice 13 onward is unbuilt.

This is a build order, not new runtime evidence. Approval authorizes planning one
slice at a time under the repository process. Each slice still needs its own
explicit go-ahead, and the separately authorized items named in every slice's
Authorization line stay separate.

## 1. Authority, baseline and exit rule

Slices 1 to 9 are completed historical work. Preserve their code, checked status,
verbatim evidence and limitations in `00-status.md`. Their former descriptions
are available in Git before this revision. In brief: Slices 1 to 8 delivered the
tracer, trusted local execution, sealed evaluation, ledger, repair and offline
pre-proof; Slice 9 delivered the accepted room shell, board and customer evidence.
The offline pre-proof does not establish fresh AI behavior or hostile-code
isolation. Historical tests with the same number as Gate 3 section 9 are not
automatically the new tests.

Each slice below has a user-visible output through an existing API and
room, a runnable demo, or the spike's raw evidence report. At completion: run its
named tests, demonstrate the exact result, record actual output and remaining
limits in `00-status.md`, check affected ADRs, then ask whether to continue. A
green check without a demonstrated result is insufficient. Do not check any
slice before its own demonstration. Do not weaken historical tests to accept
schema v6.

All `python -m ...` commands below are planned checked-in entry points, not
commands run while writing this plan. `demos.final_pivot` is the Gate 3 offline
walkthrough; its staged views are not live evidence. For room demonstrations,
start `python -m uvicorn shiftwork.app:create_app --factory --port 8000`, open
`http://127.0.0.1:8000/`, and report the actual URL/port used. Use the project's
approved interpreter. Every guard test needs a valid, behavior-changing
mutation that fails at its named assertion. Gate 3 section 9 has **49 numbered
obligations with multiple assertion clauses**, not 49 single-clause tests. Section
4 maps the clauses and names where partial coverage becomes complete.

**Stop rule:** if a slice falsifies an approved Gate 2 or Gate 3 decision, stop
dependent work, backtrack that gate and obtain explicit re-approval. In particular,
do not reduce three pairs, inject a provider key into learner code, replace fresh
trials with replay, relax trusted-local pins or add a dependency without Gate 3
backtracking. No mailbox transport is approved; the spike must establish a safe
run-bound channel before the adapter implements one.

## 2. Proposed dependency order

| Slice | New working result | Depends on |
| --- | --- | --- |
| 10 | Closed v5 history opens a non-operational first-choice shift under v6, with no invented choice | Slices 1 to 9 |
| 11 | An executable task-relevant Bellwether failure can be investigated and publicly retested | 10 |
| 12 | Bounded real Sandbox/inference capability spike gives a pass/fail decision | 11; separate credentials and spike authority |
| 13 | One learner-owned service request runs with mediated inference and safe public evidence | 12 PASS |
| 14 | Prediction-gated, attributable assistance works in the room | 11, 13 |
| 15 | Two frozen candidates execute three reviewed paired workloads in six slots | 11 to 14; reviewed and sealed material |
| 16 | The six-slot result shows fair eligibility, exposure invalidation and crash recovery | 15 |
| 17 | The learner explicitly selects one eligible exact version | 16 |
| 18 | Only operating that version changes the synthetic ledger and incidents | 17 |
| 19 | Captured operational evidence supports read-only semantic replay | 18 |
| 20 | A next shift inherits the choice and can test the retained alternative without rewriting history | 19 |
| 21 | The Bellwether room completes its five-station live journey | 20 |
| 22 | Northline runs a distinct executable reduced-help transfer journey, completing the sixth station | 21; reviewed Northline material, paired manifest and compatible catalog |
| 23 | Optional reviewed Tavily curation and ablation | 22; separate Tavily authority if live |
| 24 | Reproducible full-pivot test build and submission evidence | 22, and 23 only if claimed |
| 25 | Conditional hosted demo, only if spike and delivery decision support it | 12, 24; separate deployment authority |

S12 is before S13 or any other live-dependent product implementation or claim.
S10 and S11 are offline policy and investigation slices; their recorded/trusted
local results are explicitly labelled. S12 is a bounded integration proof, not a
substitute for the later learner journey. S15's **six trial slots** mean one A
and one B execution for each of three paired workloads. Each workload is a frozen
batch of up to four customer requests. Six slots do not mean six customer
requests; metrics use the same actual request denominator for both candidates.

## 3. Slice exit contracts

### Slice 10: v5 history to v6 without invented choice

- **Working result and demo:** `python -m demos.final_pivot --stage migration`
  opens a copied v5 Bellwether database, migrates once, and shows the board
  with its old captures, events, incidents and original hashes preserved
  byte-for-byte. Old runs say `LEGACY_OPERATION`
  with their recorded/trusted-local evidence mode. The room labels missing old
  context as unknown. Opening its next shift creates one server-labelled
  `LEGACY_FIRST_CHOICE` shift with an editable draft, null selection and null
  operating pointer. Operation and selected-contract close return 409 before
  a qualifying comparison and explicit choice. A new engagement retains its
  separate labelled `STARTER_BASELINE`, not eligible repair evidence.
  Restart/reopen and rerun migration change no historical bytes or shift mode.
- **Tests:** `python -m pytest tests/store/test_pivot_migration.py tests/api/test_pivot_routes.py -q`;
  Gate 3 obligations 1, 3, 4 and S10's clauses of 2. Inject a mid-DDL fault and
  reject unknown schema
  versions. Assert one atomic shift-open, no caller-controlled mode, no fictional
  legacy selection or operating pointer, and both pre-choice 409 guards. Fault
  starter insertion, latest-draft promotion and rejected shift-open separately;
  each must fail a named assertion. Include a closed v5 shift with no source
  run: its future bootstrap allowance is preserved, but S10 reserves no
  experiment and creates no choice or operation. S13 tests the bootstrap's
  public-only budget and investigation linkage after safe execution exists;
  S17 completes the first valid choice and unlock path. The legacy replay
  `UNKNOWN_MISSING_INPUTS` assertion completes
  at S19, when semantic replay exists.
- **Limits:** no new task assessment, experiment, service AI or learner-code
  isolation. Historical `tokenfactory` labels gain no new proof.
- **Authorization:** Gate 4 approval and the normal one-slice go-ahead; no install,
  migration of the user's live database, commit or push is implied. Demo uses a
  copy. A real database migration needs a reviewed backup and separate go-ahead.

### Slice 11: investigate a task-relevant failure

- **Working result and demo:** `python -m demos.final_pivot --stage investigation` and the
  Investigate station execute the reviewed learner-editable Bellwether failing
  starter against its pinned incident request and public state, then show the
  full request, observed interpretation/tool/data use when present, exact output,
  and independently assessed required tasks. A supported price alone fails the
  collection-plus-alternative request. The learner
  appends cause, falsifier and a public distinguishing test; revising retains the
  original. A public diagnostic experiment can run a pinned trusted fixture but
  cannot reserve protected cases or make a candidate eligible. For a legacy
  first-choice shift with no inherited source run, show the blocked operation
  and the reviewed initial request required for its later bootstrap. S11 does
  not run the arbitrary inherited draft or reserve its diagnostic slot. S13
  produces that source through the verified isolated adapter, after which the
  learner records cause, falsifier and public test before diagnostic help.
  Deterministic orientation works before the prediction; diagnostic help remains denied until
  S14 supplies the gateway.
- **Tests:** `python -m pytest tests/domain/test_task_contract.py tests/evaluator/test_evaluator.py tests/orchestrator/test_investigation_assist.py tests/orchestrator/test_experiment_lifecycle.py -q`;
  offline-policy clauses of obligations 5 to 6, 9 to 15 and 21 to 22. Show
  wrong entity, missing task/capture, justified refusal/referral, justified and
  unjustified clarification, blanket or unneeded clarification, unsupported
  claim and contradictory prose failures. A swap to the old stock-only arc or
  stubbed success must fail the requested-task assertion. Prove pure evaluator and
  orchestration-only sealed loading. Deny null-investigation bootstrap before a
  safe executor and reviewed initial request exist; fault auto-choice, business
  write and help before the learner's entry. S13 completes the bootstrap and
  live missing-capture meaning; S14 completes the help-access half of 5.
- **Limits:** human review and byte pins for the starter, incident request,
  public state, public task rubric and any compatible catalog are required;
  the illustrative mockup is not an executable fixture. Results are
  `TRUSTED_LOCAL` or `RECORDED_INSPECTION`, never fresh model or hostile-code
  proof. No new protected case is sealed here.
- **Authorization:** separate operator review of the public workload/rubric
  before use; no credentials or external call.

### Slice 12: capability spike and hard stop

- **Working result and demo:** after separate authorization, run
  `python -m demos.gateway_spike` with a minimal learner service. Save the raw
  probe matrix in `docs/plans/shiftwork/evidence/`: exact model/image/settings,
  real request interpretation/tool choice, file transfer, request streaming,
  output/capture retrieval, cleanup, six-trial latency/usage/cost estimate,
  dependency outage, reset, crash, deadlines/resources/egress, and a reproducible
  judge delivery route. Try cross-run grant reuse, model/limit escape, access to
  provider credentials, controller/database/host/protected files and arbitrary
  URLs, and secret leakage through normal/error/log surfaces. Record pass/fail and
  raw observations per probe. Test transport without presupposing mailbox, public
  ingress or any SDK.
- **Tests:** Gate 3 obligation 49 and each section 8 hostile probe, with an
  explicit stop verdict. Subsequent S13 real-adapter conformance and public
  scanner tests must repeat the applicable probes; a spike PASS alone is not
  product acceptance.
- **Limits:** a spike has no learner eligibility, selection, operation or learning
  result. If any trust probe succeeds, or the model cannot do meaningful service
  work under the fixed ceilings, stop S13 onward and backtrack Gate 2/3. If six
  trials are infeasible, backtrack Gate 3 rather than shrinking the schedule.
- **Authorization:** credentials, live Nebius/Sandbox use, spend and the spike
  run need separate explicit authorization. No new package/lockfile change or
  ADR #4 follows automatically.

### Slice 13: one fresh, isolated service request

- **Working result and demo:** with the room running at the reported local URL,
  start a public diagnostic experiment for a reviewed request through the real
  adapter and run-bound service-inference
  gateway. The room shows exact request, observed interpretation/tool events,
  consumed records, validated envelope, customer text, independent task checks,
  trusted usage/timing and `ISOLATED_LIVE`. A code-only path may use zero model
  calls; a separate real Nemotron path demonstrates meaningful interpretation or
  information selection. All raw captures precede safe projections; failed
  transport shows missing evidence, not a customer refusal or synthetic sale.
  A copied closed v5 shift with no source run now freezes its draft and may use
  the one public bootstrap diagnostic: orchestration freezes that engagement's
  reviewed initial request, task spec, mission and state, then runs arbitrary
  inherited code only in the verified isolated adapter. Its response shows a
  null investigation ID and no eligibility, selection or business write. A
  missing/cross-engagement request or unavailable safe executor blocks
  reservation; the learner then uses the captured source for an investigation.
- **Tests:** `python -m pytest tests/executor tests/executor/test_gateway_isolation.py tests/api/test_pivot_projection.py tests/sealed -q`;
  obligations 13, 15, 35 to 39 and the source-projection arm of 40, plus
  non-vacuous live arms of 9 to 14. Each
  serialized needle has a scanner self-test for raw, JSON-escaped and slash
  forms; scan success/error responses, observations, logs and bootstrap. A real
  canary attempts provider key, controller, host, protected and other-run access.
  Bind the grant's exact tool list to frozen controller policy. An injected
  `allowed_tool_names` request field returns 422 with no gateway call; prompt
  override, changed grant, unlisted model proposal and unlisted tool execution
  each fail a distinct policy assertion before any unapproved tool runs.
  Complete the Bellwether no-run v5 bootstrap arm of obligations 2 and 21:
  assert one ordinary diagnostic slot, public-only context, null ID in POST/GET
  views, owned source linkage, and named failures for repeat/ordinary null ID,
  missing or cross-engagement request, protected exposure, assist, eligibility,
  operation and business writes.
- **Limits:** one live request is not a six-slot comparison or eligible repair;
  existing `recorded` and byte-pinned `local_process` retain their narrower modes.
- **Authorization:** S12 PASS, separate credentials/live calls and any required
  provider spend. A newly necessary dependency triggers Gate 3 backtracking.

### Slice 14: optional assistance after learner commitment

- **Working result and demo:** at the reported local URL, submit an incomplete
  cause/falsifier/public test in the Investigate station and receive no
  diagnostic role. A complete entry allows a
  bounded hint, diagnosis or labelled patch proposal; the event records model,
  prompt/reply and accept/reject attribution. Accepting a patch does not edit,
  freeze, grade or select code. Bellwether shares three assist calls with one
  patch proposal maximum; Northline permits one hint only. Show the counters and
  original/revised learner reasoning in the room.
- **Tests:** `python -m pytest tests/assist/test_gateway.py tests/orchestrator/test_investigation_assist.py tests/api/test_pivot_projection.py -q`;
  complete obligations 5, 7, 8 and the assist-prompt/import arms of 15 and 39.
  Test mixed-role budget, rejected/accepted patch, protected-data attempts,
  authorization at API and gateway, and serialized prompt/error leakage.
- **Limits:** help is advice, never assessment or an independent oracle.
  Recorded assist doubles prove policy only; a real model-feedback pack requires
  authorized calls with observed model/settings, usage, latency and failures.
- **Authorization:** separate live inference credentials/calls. No new provider
  dependency or changed assist ceiling without Gate 3 backtracking.

### Slice 15: paired candidate execution

- **Working result and demo:** at the reported local URL, freeze two distinct
  candidate content hashes, one declared treatment, common requirements, frozen
  reviewed mission bytes/hash, starting state, public records, model/settings,
  ceilings and three reviewed workload
  batches. The independently reviewed manifest pins each batch's raw bytes,
  hash, parsed request count and public task-spec hash. Pair 1 uses batch 01,
  pair 2 batch 02 and pair 3 batch 03; each pair's A/B slots bind the same
  frozen bytes and count, not a mutable path. Reserve three unexposed protected
  variants per enabled family, each
  shared by A/B in its pair, and all six ordered slots before releasing any
  result. Execute A/B, B/A and the precommitted hash-derived order in fresh reset
  workspaces. The Compare station shows every slot, run identity, batch request
  count, exact version and missingness without a winner. The request driver
  streams only the current request; a pre-run payload or earlier public surface
  cannot expose future customer wording. Diagnostic runs remain public-only and
  cannot appear in this comparison.
- **Tests:** `python -m pytest tests/orchestrator/test_experiment_lifecycle.py tests/executor/conformance.py -q`;
  obligations 16 to 18, 20 to 22. Fault each reservation write, race duplicate
  keys, mutate order after first result, replace a file after reservation,
  swap whole pair assignments, swap only pair 2's B batch or count, drop one
  request, leak a cache/booking/process sentinel across candidates and fail
  one of six slots. Every mismatch fails against the independently pinned
  manifest and frozen slot context. Prove failed/exposed slots are not refunded.
  Complete Gate 3 obligation 40's workload-summary projection: before a slot
  runs, public views expose only safe ID/hash/count, never future request bytes
  or protected pair refs. S16 completes eligibility/invalidation readback.
- **Limits:** raw paired execution alone does not rank candidates or prove
  stable statistics. Each slot may contain up to four customer requests; show the
  frozen per-slot batch size and actual shared denominator.
- **Authorization:** separate review of all three public workloads, visible
  requirements and at least six semantically independent protected task variants
  per enabled family before sealing; separate live execution credentials/cost.
  Cases are not inferred from mockup numbers. If both repairs cannot be defensible
  under the same rules, stop and revise the incident before building farther.

### Slice 16: fair outcome, invalidation and recovery

- **Working result and demo:** `python -m demos.final_pivot --stage comparison`
  shows the offline policy; the live Compare station displays all six
  trials, shared request denominator, useful completion, incorrect output,
  justified/unjustified refusals and referrals, missing output, service calls,
  token/latency/cost fields (unknown stays unknown), eligibility and explicit
  `INCOMPLETE` or `NOT_COMPARABLE`. A mandatory failure blocks that candidate
  before cost comparison. Unplanned context drift blocks comparison. Retiring a
  leaked reservation invalidates dependent evidence without deleting it. Kill a
  run mid-trial, restart, and show retained capture/usage/exposure, failed slot
  and no automatic paid retry. Report justified and unjustified clarification
  separately from useful completion, refusal and referral. A justified
  clarification is not a completed task, and an unnecessary one fails its
  public rule. Multi-task outcomes retain `(request_ordinal, task_id)` identities;
  non-completion incidence categories are labelled non-additive.
- **Tests:** `python -m pytest tests/domain/test_comparison.py tests/orchestrator/test_experiment_lifecycle.py tests/orchestrator/test_selection_operation.py tests/orchestrator/test_replay.py -q`;
  obligations 19, 20, 23, 24 and the experimental arm of 41. Mutate each
  context field, including the mission bytes/hash, each metric
  denominator/missingness/unknown field, both
  clarification counts and task identity, and the interrupted experiment state.
  The denominator equals the sum of all three frozen batch counts for each
  candidate. A request counts as useful only when every required task completes;
  faults that credit one task in a multi-task request or force overlapping
  non-completion categories to sum to the denominator must fail. S17 and S18
  complete invalidation enforcement at selection and run start; S18 completes
  interrupted-operation restart.
- **Limits:** no candidate is selected merely because it is eligible. Three pairs
  show within-demo variation, not statistical confidence or learning gain.
- **Authorization:** live reruns need separate credentials and cost; deterministic
  comparison/restart tests do not.

### Slice 17: choose an eligible exact version

- **Working result and demo:** from the live Compare station and in the offline
  `python -m demos.final_pivot --stage selection` walkthrough, explicitly
  select eligible A or B with a rationale and expected prior selection.
  The board shows selected version/hash, retained alternative, comparison and
  original requirement hash separately from latest saved. A changed-after-test
  version, incomplete/incompatible comparison, invalidated exposure, stale prior
  selection or unselected candidate returns 409. Save, freeze and test leave the
  selection history unchanged; a later invalid latest choice blocks without
  falling back to an older choice. In the S10 first-choice shift,
  `expected_prior_selection_id=None` and one complete eligible comparison
  append the first learner choice; only that atomic action unlocks operation.
- **Tests:** `python -m pytest tests/orchestrator/test_selection_operation.py tests/api/test_pivot_routes.py -q`;
  obligations 25, 27 and save/freeze/test clauses of 26. Recompute eligibility
  atomically and test same-key retry versus changed-body conflict. Fault
  implicit choice on open/freeze and a valid choice that leaves operation
  blocked. A failed first-choice comparison retains exposure and the operation
  block, with no automatic retake, refund or new shift. S18 completes run-start
  invalidation enforcement; S20 completes close's no-selection clause.
- **Limits:** choice itself creates no order, refund, incident resolution or
  operational evidence. No auto-winner is selected.
- **Authorization:** none beyond Gate 4 and the per-slice go-ahead.

### Slice 18: operate only the selected service

- **Working result and demo:** `python -m demos.final_pivot --stage operation`
  shows offline policy; at the reported local URL save an unselected newer
  candidate, then run the exact selected version under current conditions.
  The Customer and ledger stations join request/output/independent assessment to
  hash-chained, labelled synthetic orders/incidents. An experiment with identical
  output writes no business row. Incident resolution requires an operational
  selected-version regression against the pinned rule. A partially outputting
  failed operation cannot take the zero-output retry; one successful operational
  finalization is allowed per shift. Gateway/provisioning failure retains evidence
  and writes no invented consequence.
- **Tests:** `python -m pytest tests/orchestrator/test_selection_operation.py tests/ledger tests/api/test_pivot_routes.py -q`;
  obligations 28 to 32 and business-effect clause of 38. Fault checks, events,
  incidents and terminal writes; prove one atomic/idempotent result, reducer
  purpose/type guard, one in-flight operation, exact selected hash, retry rules
  and no experimental incident mutation. Kill an operation mid-flight and
  restart: retain raw capture, usage and exposure, mark the run failed, and
  perform no automatic paid retry or business write. Complete S16's run-start
  invalidation and Gate 3 obligation 41's operation arm. Once operational events
  exist, run Gate 3 obligation 39's serialized-event scanner self-test and scan
  both normal and error event projections.
- **Limits:** one operation does not prove later inheritance or alternate-history
  behavior. All business amounts remain synthetic.
- **Authorization:** live operations need separately authorized service execution;
  offline doubles prove state/policy only.

### Slice 19: semantic replay of captured consequences

- **Working result and demo:** `python -m demos.final_pivot --stage replay` reads an S18 run's
  original bytes, context with captured mission bytes/hash, rule versions and
  protected refs, re-assesses and reduces in memory, and reports `IDENTICAL`
  with zero writes. Changing the current mission file, other fixture or incident
  state cannot change the replay. Deliberate stored
  semantic divergence reports `DIFFERENT`; independent chain damage trips chain
  verification. A v5 run lacking inputs reports `UNKNOWN_MISSING_INPUTS`.
- **Tests:** `python -m pytest tests/orchestrator/test_replay.py tests/ledger tests/store/test_pivot_migration.py -q`;
  obligations 42 to 44 and the legacy-replay completion from S10. Mutation
  probes distinguish semantic derivation from hash-chain integrity.
- **Limits:** replay re-evaluates captures; it is not fresh inference, a second
  customer outcome or an authority to edit historical rows.
- **Authorization:** none beyond Gate 4; no live call needed for replay.

### Slice 20: inherit and test the retained alternative later

- **Working result and demo:** `python -m demos.final_pivot --stage inheritance`
  shows the offline history rule; at the reported local URL close and open the next
  Bellwether shift from the exact selection, and displays original rationale,
  retained alternative, visible tests, incidents, limits and historical ledger.
  Under a newly observed dependency outage, operate the selected version, then
  reserve a **separate** later-condition comparison and execute both the selected
  and retained candidate versions in fresh matched A/B slots under that observed
  condition. The preceding operational run is never one side of the experiment.
  Compare all prior selection, operation, incident and
  ledger bytes before/after that experiment: identical. Switching afterward
  requires a new eligible comparison and explicit choice. The Next shift station
  separates the real operational history from the hypothetical experiment. Record
  a per-no-go full central-mechanism verdict from the live run, including the
  S12/S13 isolation probes; the S8 offline pre-proof remains a separate label.
- **Tests:** `python -m pytest tests/orchestrator/test_selection_operation.py tests/orchestrator/test_close_inheritance.py tests/api/test_pivot_routes.py -q`;
  obligations 33, 34 and close clause of 26. Verify ancestry when A is restored
  after B, exact selected hash and no latest-save substitution. Close refuses
  nonterminal work and adds only declared limits, not synthetic sales.
- **Limits:** a later outage cannot retroactively mark the original decision
  wrong. A new experiment neither resolves old incidents nor proves how an
  unchosen version would have operated in the past.
- **Authorization:** fresh later-condition live trials need separate credentials
  and spend; deterministic history tests do not.

### Slice 21: complete the Bellwether room journey

- **Working result and demo:** serve the same fixed room across Shift board,
  Requirements, Investigate, Compare and choose, and Next shift. Every Bellwether
  station uses real public API state and no illustrative mockup numbers. Browser
  checks at 1280, 640 and 390 px use native keyboard/touch, verify focus and
  selected-panel reachability, no horizontal overflow and reduced motion. One
  real request/version ID binds room selection, workbench, output, checks and
  operational event. Experiment views visibly state that history did not change.
- **Tests:** Bellwether assertions in `node tests/client/pivot-browser.mjs` and
  `node tests/client/pivot-render-faults.mjs`, plus
  `python -m pytest tests/api/test_pivot_projection.py -q`. Each served-source
  fault must fail a value assertion against independently fetched API data,
  including purpose, evidence mode, context, trial values, blocker, selected
  version and synthetic label. Gate 3 obligations 39, 45 and 46 remain partial
  until the distinct Away shift is executed and inspected at S22.
- **Limits:** browser mechanics do not prove learner comprehension or transfer.
  Five moderated sessions and any study/outreach remain separately authorized;
  a pilot cannot justify the 20-point learning claim.
- **Authorization:** no framework or rendering-engine change is assumed.

### Slice 22: execute the distinct Northline transfer journey

- **Working result and demo:** the Away shift starts with its reviewed Northline
  mission, initial and three paired public request files, reviewed ordinal
  manifest, starting booking/dependency state, compatible frozen catalog,
  orchestration-owned protected inventory and executable blank learner scaffold.
  Idempotent operator-reviewed seeding creates the distinct engagement. The
  scaffold has no authored solution. In its first shift, operate only that
  labelled starter to expose the initial failure, record the learner's cause and
  falsifier, edit/freeze two distinct learner-owned versions, execute six
  Northline A/B slots, and explicitly choose one eligible exact version. Close
  and open the next shift before operating the chosen version, because the
  starter used the first shift's successful-operation allowance. A second
  successful operation in that shift must return 409 even after selection. Run a real
  future-commitment, safety-escalation and retry-safe booking request through
  the approved isolated path, then show exact output, independent task checks,
  one-hint-only policy and deterministic synthetic consequences in the Northline
  workshop. An experiment creates no such consequence. Bellwether mission,
  catalog, manifest and source cannot substitute. Complete the native
  keyboard/touch six-station journey with real public API values on desktop and
  390px mobile.
- **Tests:** `python -m pytest tests/orchestrator/test_northline_transfer.py tests/api/test_pivot_projection.py -q`,
  `node tests/client/pivot-browser.mjs` and
  `node tests/client/pivot-render-faults.mjs`. Fault each missing or unreviewed
  mission, initial/paired requests, manifest, state, catalog and protected
  inventory prerequisite; swap Bellwether mission/source/manifest; inject
  solution code into the blank scaffold; widen Northline assist beyond one
  hint; choose without a complete eligible comparison or with a stale/null prior
  selection ID instead of the labelled starter ID; allow a second successful
  operation in the starter shift; run unselected edited
  code; or let an experimental pass write business history. Each must fail a
  named assertion. A separate existing v5 Northline no-run case must receive no
  starter, use only a reviewed Northline initial request for its isolated public
  bootstrap, then require investigation and eligible choice. Check both new
  engagement shifts and the exact inherited selected hash.
  Served-source faults must also catch wrong Northline request, outcome, evidence
  mode and synthetic label. Complete Northline arms of obligations 16, 17, 23,
  25, 28, 29 and 40, plus obligations 39, 45 and 46 here.
- **Limits:** a representative executable away run proves software behavior,
  not reduced-assistance human learning or the 20-point transfer target.
- **Authorization:** operator review and sealing of the actual
  Northline files, protected inventory and compatible catalog precede execution.
  If any prerequisite is missing,
  stop Northline execution and any transfer claim. Participant contact/consent,
  live credentials and spend each remain separately authorized.

### Slice 23: optional Tavily curation

- **Working result and demo:** the planned operator CLI
  `python -m shiftwork.curation.pipeline discover --manifest docs/plans/shiftwork/evidence/test3-manifest.json`
  makes a separately authorized live call; then
  `python -m shiftwork.curation.ablation --manifest docs/plans/shiftwork/evidence/test3-manifest.json`
  prints quarantined discovery, human source
  verification, frozen executable change, and a pre-registered frozen/known-page
  polling/Tavily comparison. Polling keeps known URLs. Retain the historical
  preregistered 2025-08-01 to 2026-07-31 UTC window, four official domains
  (`cpsc.gov`, `gov.uk`, `ec.europa.eu`, `productsafety.gov.au`), 12 dated
  events with two known-page and one structural event per domain, and earliest
  qualifying publication-time selection. The Tavily arm must find at least two
  useful structural changes across two domains missed by polling, with at most
  ten reviewed candidates per useful frozen fixture and median review time at
  most 30 minutes, while zero unverified/non-allow-listed content affects a
  fixture or score. Freeze the manifest before comparator output. The report says
  `KEEP_TAVILY_CLAIM` only if the prior thresholds and executable-change rule pass;
  otherwise `DROP_TAVILY_CLAIM`. Runtime application imports no curation code.
- **Tests:** obligation 48, including DROP for each unmet threshold, and import
  isolation from Gate 3 section 3.8. Run
  `python -m pytest tests/curation/test_ablation.py -q` separately. The historical corpus rules need source
  verification before the ablation, not tuning after results.
- **Limits:** optional to the core loop. A live Tavily call or bonus answer is
  claimed only if it actually ships and qualifies; a link-only change is a DROP.
- **Authorization:** separate Tavily credentials/calls and human source review.

### Slice 24: full-pivot package and honest judge evidence

- **Working result and demo:** `python -m pytest tests/packaging/test_clean_env_install_and_run.py -q`
  installs only the approved lock in a clean environment and runs the **full
  offline pivot demo**. A downloadable test build includes source/assets,
  license, README, setup/run instructions, mode labels, limits and a judge path
  to a separately authorized live demo if available. Assemble model feedback
  from observed S12 to S22 calls, never invented ratings. Record the required
  model use, selected track, actual Nebius capabilities, and public video script
  showing real inference, learner repair, choice and inheritance.
- **Tests:** obligation 47 completes here; run the relevant full suite and
  browser journey before packaging. Missing credentials produce a labelled
  offline skip, not a live PASS. The complete central-mechanism verdict requires
  real S13 to S22 evidence and all hard no-go checks in section 5.
- **Limits:** packaging cannot substitute an offline fixture for a working
  learner-code product or prove prize/learning impact. A download URL is the
  baseline; hosting remains conditional.
- **Authorization:** a clean-environment install, release/tag/push, public
  repository/build/video, YouTube upload and submission each require their own
  authorization. None is performed by Gate 4 approval alone.

### Slice 25: conditional hosted demo

- **Working result and demo:** only if S12 proves a suitable delivery route and
  the user selects hosting, show a public HTTPS controller/client, restart it,
  verify persistent state or an explicitly documented deterministic reset, check
  monitoring and judge access, and keep the downloadable build available.
- **Tests:** repeat package and representative six-screen/browser checks against
  the deployed URL, with actual restart evidence. No Gate 3 numbered obligation
  depends on hosting.
- **Limits:** public multi-user auth/database redesign is not approved. If safe
  hosting needs one, backtrack Gate 2/3 or use the downloadable build. Funded
  availability and hackathon submission claims require separate review.
- **Authorization:** explicit deployment, spend and publication authority.

## 4. Gate 3 assertion-clause trace

The numbers refer only to `03-program-design.md` section 9. A slice may add a
guard earlier but **coverage is complete only at the named completing slice**.
Every row includes the assertion clauses, not merely a test name.

| # | Assertion clauses and prerequisite landing | Complete |
| --- | --- | --- |
| 1 | S10 snapshot old serialized blobs, hashes and row counts; require byte identity after migration | S10 |
| 2 | S10 preserve closed v5 bytes, open one server-labelled first-choice shift with null selection/operating pointer, reject operation and close with 409, and fault starter insertion, latest-draft promotion and shift-open rejection; S13 safely executes the no-source-run public bootstrap and pins its reviewed initial request, null ID and owned source; S17 proves first valid explicit choice unlocks operation | S17 (partial S10, S13) |
| 3 | S10 mid-DDL fault leaves version 5; successful retry commits once; rerun no-ops | S10 |
| 4 | S10 unknown schema version refuses startup without mutation | S10 |
| 5 | S11 each cause/falsifier/public-test omission denies diagnostic help and orientation remains deterministic; S14 real assist path obeys gate | S14 (partial S11) |
| 6 | S11 revision row retains original text, linkage, shift ownership and order | S11 |
| 7 | S14 mixed assist roles consume one budget; patch proposal cap is one | S14 |
| 8 | S14 deny assist edits/freezes/grading/selection and protected imports/calls; scan every assist success/error surface | S14 |
| 9 | S11 reviewed executable Bellwether starter/request/state yields the task-relevant failure; old stock-only fixture and stubbed success fail; S13 repeats on a real envelope | S13 (partial S11) |
| 10 | S11 supported claim for wrong entity fails; S13 repeat on live output | S13 (partial S11) |
| 11 | S11 blanket refusal and unneeded clarification are not useful completion; S16 metrics retain separate refusal and clarification categories | S16 (partial S11) |
| 12 | S11 frozen public rule distinguishes justified refusal, referral, justified clarification and unjustified clarification; S16 reports each without crediting clarification as completion or referral | S16 (partial S11) |
| 13 | S11 missing capture is missing evidence, never refusal or clarification; S13 live timeout and S16 missing slot keep that meaning | S16 (partial S11, S13) |
| 14 | S11 validated envelope alone renders customer text; contradictory/free prose rejected; S13 live projection repeats | S13 (partial S11) |
| 15 | S11 pure evaluator and orchestrator-only loader, including import/runtime I/O traps; S13/S14 new gateway/assist imports repeat | S14 (partial S11, S13) |
| 16 | S15 Bellwether and S22 Northline atomically freeze both versions, their own reviewed mission bytes/hash and three reviewed request batches with raw bytes, hashes, parsed counts and task-spec hashes, context, protected reservation and all six slots before result; fault every write, missing batch, caller-selected/cross-engagement manifest and mutable-path substitution | S22 (partial S15) |
| 17 | S15 Bellwether and S22 Northline independently pinned manifests map each engagement's file 01/02/03 to pair 1/2/3; each pair's A/B slots share exact bytes/hash/count/task-spec hash and protected ref; whole-pair swap, B-only swap/count, dropped request, cross-engagement fallback and cache/booking/process leakage fail | S22 (partial S15) |
| 18 | S15 predeclared A/B, B/A, hash-derived third order cannot change after first result | S15 |
| 19 | S16 mutate candidates and every context field separately, including frozen mission bytes/hash, model/settings, requirements and starting state; all drift is Not comparable | S16 |
| 20 | S15 failure retains slot/exposure; S16 each missing/failed slot blocks complete status without refund | S16 (partial S15) |
| 21 | S11 ordinary public diagnostic cannot reserve protected material, open assist, write business state or become eligible; S13 safely runs one null-investigation legacy source bootstrap with public-only inputs, null POST/GET ID and no protected/business/help effect, rejecting repeat/ordinary null IDs; S15 repeats the guard against comparison reservation | S15 (partial S11, S13) |
| 22 | S11 recorded inspection cannot earn fresh eligibility; S16 comparison rejects its mode | S16 (partial S11) |
| 23 | S16 Bellwether and S22 Northline candidate denominators equal their own three frozen batch request counts; missing output counts, unknown usage/cost stays unknown, mandatory unknown budget blocks eligibility; justified/unjustified clarification have separate counts; `(request_ordinal, task_id)` stays distinct, useful completion needs all required tasks, and overlapping non-completion incidence is labelled non-additive, with faults for each arm | S22 (partial S16) |
| 24 | S16 mandatory task/correctness/safety failure blocks candidate before efficiency; no aggregate score conceals it | S16 |
| 25 | S17 Bellwether and S22 Northline choices bind an exact eligible version/hash, current requirements, uninvalidated exposure and expected prior selection atomically; null prior choice is valid only for an eligible first choice, while Northline's prior ID must be its labelled starter selection | S22 (partial S17) |
| 26 | S10/S11 no-choice requalification cannot select implicitly; S17 save/freeze/test and failed comparison retain block/exposure without auto retake; S20 close does not select | S20 (partial S10, S11, S17) |
| 27 | S17 invalid latest choice blocks without prior-choice fallback; S18 run start rechecks | S18 (partial S17) |
| 28 | S11 public diagnostic, S15 Bellwether pairs and S22 Northline pairs cannot write ledger/incidents; S18 establishes import/call and reducer purpose/type/runtime traps | S22 (partial S11, S15, S18) |
| 29 | S18 faults Bellwether checks/events/incidents/terminal writes, changes the current mission after run start without changing pinned check/event derivation, and retries one atomic finalization; S22 proves distinct Northline starter and selected-version operations across two shifts, rejecting a second successful operation in the starter shift | S22 (partial S18) |
| 30 | S18 saves newer unselected source, runs exact selected version/hash | S18 |
| 31 | S18 only zero accepted outputs and zero reducer writes permit second operation; reject changed selection/context | S18 |
| 32 | S18 experimental pass and unselected passing version cannot resolve; selected operational pinned regression can | S18 |
| 33 | S20 next shift restores exact selection/rationale/alternative/tests/limits IDs and hashes | S20 |
| 34 | S20 fresh matched trials for both selected and retained candidates use a new later-condition reservation; the prior operation is not a trial; all original selection/ledger/incident bytes remain unchanged | S20 |
| 35 | S12 probes; S13 capability-derived run identity rejects spoofing, expiry and cross-run reuse separately | S13 (partial S12) |
| 36 | S12 probes; S13 model, call, byte, token, deadline and controller-derived exact tool policy each fail independently; injected request field returns 422/no call, while prompt override, changed grant, unlisted model proposal and tool execution each fail a named assertion | S13 (partial S12) |
| 37 | S12 real isolation probes; S13 real adapter canary cannot reach key, controller, host, sealed or other run | S13 (partial S12) |
| 38 | S13 provider/transport failure retains raw evidence and usage; S18 proves zero business effect after finalizer exists | S18 (partial S13) |
| 39 | S13 needle self-tests plus success/error/log/observation/bootstrap scans in raw, escaped and slash forms; S14 assist prompts; S18 operational event self-test and normal/error projections; S21 Bellwether client and S22 Northline client surfaces | S22 (partial S13, S14, S18, S21) |
| 40 | S13 safe owned source and nested public views contain no internal locator; S15 Bellwether and S22 Northline reserved workload summaries expose only safe ID/hash/count before trial, never future bytes or protected refs | S22 (partial S13, S15) |
| 41 | S16 restart fails an interrupted experiment; S18 separately fails an interrupted operation, retaining each capture/usage/exposure with no paid retry/refund | S18 (partial S16) |
| 42 | S19 original bytes/context, including frozen mission, and rules drive semantic replay despite changed current mission/other files/state; zero writes | S19 |
| 43 | S10 preserves missing legacy inputs; S19 reports UNKNOWN_MISSING_INPUTS, never guessed replay | S19 (partial S10) |
| 44 | S19 independent semantic divergence and chain-tamper faults prove both checks separately | S19 |
| 45 | S11/S14/S15/S17/S18/S20 progressively wire Bellwether stations; S21 verifies five-station mechanics; S22 seeds reviewed Northline material, runs its blank starter, six A/B slots, explicit selection and next-shift operation, and separately proves an existing v5 Northline no-run shift gets no starter and bootstraps only its own reviewed request under isolation; faults missing mission/requests/manifest/state/catalog/protected review and Bellwether substitution, then completes the native six-station desktop/390px journey | S22 (partial S11 to S21) |
| 46 | S13/S15/S16/S17/S18/S20 add real values; S21 Bellwether and S22 Northline served-source faults each fail independently fetched purpose, context, trial, blocker, choice, mode, outcome and synthetic-label assertions | S22 (partial S13 to S21) |
| 47 | S10 retains old package skeleton; S24 approved-lock clean install and full offline pivot demo; missing live credentials labelled skip | S24 (partial S10) |
| 48 | S23 frozen/polling/Tavily ablation, retained known URLs and DROP on every unmet pre-registered threshold | S23 |
| 49 | S12 raw capability matrix records exact model/image/settings, trials, latency, usage, failures and every trust probe | S12 |

## 5. No-go conditions and evidence boundaries

| Gate 3 condition | First decisive slice; completion/response |
| --- | --- |
| Closed v5 engagement cannot open a labelled no-choice shift, gains an implicit starter/pointer, or operates/closes before the first eligible explicit choice | S10 rejects the state and route defects; S17 proves the first choice unlock. Stop and backtrack Gate 2/3 rather than inventing consent or refunding exposure. |
| Closed v5 shift has no source run, and a bootstrap either uses unsafe execution, lacks a reviewed initial request, bypasses the public-only budget or creates eligibility/operation | S10 constructs the no-source state; S11 denies premature reservation; S13 permits one reviewed, safely isolated public source diagnostic before investigation. Failed bootstrap remains blocked. No implicit starter or protected case. |
| Real isolation or gateway section 8 probe succeeds: credential/controller/host/protected/other-run access; grant/model/limit/URL escape; secret on normal/error/log surface; lost crash evidence or unpaid retry; dirty trial reset | S12 spike is stop; S13 repeats product path, S15 repeats paired reset. Backtrack Gate 2/3 before live learner execution. |
| Learner request or prompt widens the controller-frozen gateway tool policy | S12 probes the channel; S13 exact-grant and injected-field tests stop before any unapproved tool executes. Backtrack Gate 3 if the fixed boundary cannot be enforced. |
| Model cannot do meaningful in-service interpretation/tool selection within the fixed ceilings | S12 stop; S13 demonstrates real behavior. Backtrack Gate 3 if infeasible. |
| Six-trial cost/latency forces replay or hidden dropped slots | S12 feasibility stop; S15/S16 retain all six slots and failures. Backtrack Gate 3, never relabel replay. |
| Reviewed executable Bellwether starter fails to reproduce the task-relevant incident, or the evaluator passes a supported but request-irrelevant fact | S11 fails the pinned starter/request/state and task assessment; S13 proves the live output path. Stop and revise the public incident/rubric before further comparisons. |
| Clarification is counted as completion/referral, unnecessary clarification passes, or a timeout is labelled clarification | S11 checks exact public task outcomes; S13 tests live missing capture; S16 checks distinct counts and non-additive task incidence. Stop and repair the assessor/metrics within Gate 3 or backtrack if the contract is wrong. |
| Three reviewed batches are not frozen to their pair's exact A/B bytes, hashes, counts and task specs | S15 manifest, slot and swap/drop-request faults stop before eligibility. No mutable-path or generic six-slot batch fallback. |
| Experiment finalization reaches reducer/incident mutation | S11 public diagnostic is the first path; S15 repeats paired trials and S18 completes purpose/type and ledger proof. Stop on any write, backtrack Gate 2/3. |
| Invalidated evidence remains selectable or operable | S16 invalidates, S17 selection rechecks, S18 operation rechecks; stop at first failure. |
| Room hides selected version or operational history on desktop/mobile | S17/S18 expose values; S21 Bellwether and S22 six-station browser/rendered-fault acceptance complete. Rework client within approved Gates if possible; backtrack if a Gate 3 contract must change. |
| Northline mission, initial or paired requests, manifest, state, compatible catalog or protected inventory lacks review; Bellwether material is substituted; or edited code operates without Northline comparison and choice | S22 refuses execution and a transfer claim until all distinct material is reviewed/frozen and its seed, pair, selection and blank-scaffold guards pass. No invented catalog version or protected case. |
| Curriculum has an obvious prescribed repair | S11 public rubric review and S15 case sealing/paired review; stop and revise incident before more UI. |

Recorded inspection means reading captured bytes only. Trusted-local means executing
byte-pinned operator fixtures, never arbitrary learner repairs. Only the verified
`ISOLATED_LIVE` path may support fresh learner-code and Nemotron claims. A static
review, test double, attractive room or second LLM cannot certify isolation,
business impact or learning. Protected expectations stay controller-owned; a
safe public reason is not a leaked answer. The selected version and consequences
remain distinguishable from hypothetical later trials. Synthetic ledger values
are not real sales, trust or skill.

Tavily is optional. S24 depends on S23 only if a Tavily claim is made. Hosted
S25 is conditional; the baseline is a downloadable test build with honest live
requirements. If S12/S13 cannot support a safe working learner service, an
offline-only package is not presented as the approved product or a qualifying
hackathon demonstration. Public release, judging availability, video upload and
participant studies each require separate authorization.

## 6. Approval boundary

This plan preserves historical Slices 1 to 9 and changes only the unbuilt
Slices 10 to 25. The user approved it on 2026-09-24 together with the scoped
Gate 3 Northline correction, and authorized committing and pushing both to main
without a co-author footer. That authorization covers these documents only.

Gate 4 approval authorizes planning one slice at a time under the repository
process. It does not authorize installs, credentials, external calls, the spike
run, fixture authoring, sealed-case contents, ADR #4, participant contact,
deployment, publication, submission or any further commit or push. Each slice
still needs its own explicit go-ahead, and Slice 12, 13, 14, 22, 23, 24 and 25
keep the separate authorizations named in their own Authorization lines.

The next planned slice is Slice 13 under section 3. Slices 10 through 12 are
accepted; Slice 13 still needs its own go-ahead and live authorizations. See
`00-status.md` for the completion evidence and current gate state.
