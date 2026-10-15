# S27 judge evidence and public-video script draft

Date: 2026-10-15. Documentation deliverable only, not a gate revision or release.

## 1. Submission decisions and claim boundary

- **Track: Best Apps and Agents**, explicitly confirmed by the user today.
- **License decision: MIT, copyright Jaydon Kua**, explicitly approved today.
  Permission is not verification that the package contains the license.
- Applied-engineering practice: investigate a service, compare repairs, choose an exact tested version, then inherit consequences.
- The strongest linked live evidence is the single successful S20 recovery chain: operator/coding-assistant-authored in the learner role, not an observed learner discovering a repair.
- Learning, reduced-assistance transfer, voluntary return, business impact, job readiness and production readiness remain unproven. Synthetic events are not real sales, bookings, trust or revenue.
- Neither vendor exclusivity nor advantage over ordinary code or other models is demonstrated. Independent deterministic assessment, not a second model, determines task outcomes and synthetic consequences.
- The user separately authorized a clean locked install; the parent owns all runtime verification. No install, application runtime, credential read, network call, recording, upload, publication, commit or submission was performed for this file.
- Recording, upload and publication are **not authorized** by this document. The
  repository was separately pushed and made public on 2026-10-15 (see
  `00-status.md`); build access and judging-period availability beyond that
  public repository remain unverified, not inferred from historical branch
  publication.
- [Requirements][rules] are a stored checklist checked 2026-09-11, with form fields supplied 2026-09-17. Current official rules were not re-fetched.

## 2. Observed model-use inventory

Configured model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` on Nebius Token Factory.
S12/S13 responses, S14's record and every persisted S20 result report that identity;
S22b records configured/reported agreement. These are not model benchmarks.

Count attempts separately from retained results, Sandbox operations, request meters,
reservations, tool calls and assessments. Summary/audit repetitions are not new calls.
Identity includes source attempt, run and request ordinal: S20's fresh databases
reuse run IDs, so run ID alone cannot deduplicate the two attempts.

| Source | Observed calls/results | What the observation supports |
| --- | --- | --- |
| [S12 original JSONL][s12-original] | 2 `nemotron_inference` rows | At 64 output tokens: `length`, empty content. At 256: `stop`, `STOCK`, service `stock_lookup`. |
| [S12 escape JSONL][s12-escape] | 1 full inference row plus 1 separate partial direct-call result | Both hit 256 tokens with empty content. The second is `escape_limit_probe`, not another full usage record. No observed tool escape; purposeful refusal is unproved. |
| [S12 trials JSONL][s12-trials] | 6 inference rows, also repeated in one verdict summary | All six returned `STOCK`/`stop` for identical text at temperature 0. Six samples of one shape, not six independent workloads. |
| [S12 confirming JSONL][s12-service] | 1 inference row | `STOCK`/`stop`; whole provider payload retained after archive repair. 45 input, 104 output tokens. |
| [S12 outage JSONL][s12-outage] | Separate transport failure and invalid-model HTTP 404 probe | Failure-path evidence, not configured-model completions. No returned usage does not establish zero billed cost. |
| [S13 first model JSONL][s13-first] | 1 provider response | 85 input, 256 output tokens; `length`, no selected tool, FAILED and no capture. |
| [S13 second model JSONL][s13-second] | 1 provider response | 85 input, 287 output tokens; `stop`, `public_catalog_search`; COMPLETE execution, but required collection/alternative results missing. |
| [S14 assist record][s14] | 3 completed calls: HINT, DIAGNOSIS, PATCH_PROPOSAL | Transport succeeded; advice repeated a mismatched premise and the patch proposal did not repair the service. Original raw replies are unavailable. |
| [S20 failed first chain][s20-first] | 8 attempts, 7 persisted results | Four complete slots, two failed; no eligible candidate or later linked operation. The eighth observation was lost. |
| [S20 successful recovery chain][s20-summary] | Comparison 9 attempts/results; operation 1 attempt/result | All ten retained results have `stop`, no failure and `public_record_lookup`. B made no model call. Audit rows are corroboration, not additional calls. |
| [S22b completion checkpoint][s22b] and [packet][s22b-packet] | 1 actual HINT; zero in-service inference | 318 input, 464 output tokens; model identity matched. Advice partly confused a claimed response with proof of an action. Raw completion directory absent here. |
| [S25 receipt][s25-receipt] and [meters][s25-meter] | 0 inference calls across 2 live operations | Rule-based workflows executed in Sandboxes. Configured model and one-call ceilings are not calls spent. |

S12 has ten full inference rows plus one partial direct-call result across the four
model-bearing files. Reservations/spend bounds are not attempts. No grand total.
S16 records twelve operations and zero inference ([status][status], S16 acceptance).
Offline proofs and test doubles are not additional live model observations.

### Feedback fields for the submission form

| Field | Evidence-based draft or unresolved input |
| --- | --- |
| How used | S12 bounded tool-choice spike; S13 in-service public information selection; S14/S22b optional diagnostic assistance; S20 first-action routing inside the compared and selected service. |
| Quality, 1-10 | **Unassigned.** Requires the user's judgment. Successful narrow routing and failed advice are both retained; no representative quality study. |
| Recommend, 1-10 | **Unassigned.** No invented endorsement or score. |
| Experience, 1-10 | **Unassigned.** User must assess the experience, including integration failures and recoveries. |
| Adaptation | Prompt-engineered: constrained tool vocabulary, task framing, temperature 0 and bounded output. No fine-tuning evidence or training run is recorded. |
| Other-model comparison | No controlled other-model benchmark. S20 B is ordinary code, not another model; there is no measured model superiority. |
| Improvements wanted | Clearer reasoning/output-token budgeting, better premise checking and response-versus-action reasoning; explicit capture failure diagnostics, stream-resume guidance and billing units. These requests follow the observations, not a general ranking. |

S12's pre-repair archives omit reasoning text; the confirming response retains
`message.reasoning`, but does not recover prior missing text. S13 first exhausted
256 tokens; its later call ran under 1,024 while the frozen context still said
256. [S13's repair record][s13-status] preserves that mismatch rather than rewriting it.
S14 input/output tokens were 196/559, 198/387 and 203/558; elapsed times were
3,757/2,919/4,358 ms. The probe paired a shelf question with reasoning about other
tasks, and omitted the captured response. Its prompt repair was tested offline,
not live in S14. S22b later supplies one real hint observation, not proof that all
three revised assistance roles became useful; its `accepted` field stayed null.

## 3. The one successful S20 chain, not a splice

Primary retained evidence: [summary][s20-summary], [audit][s20-audit],
[resume audit][s20-resume] and [recovery narrative][s20-recovery].
Attempt window: **2026-10-01 15:55:08 to 15:56:56 UTC**.
Verdicts: `CHAIN_COMPLETE` and `VERIFIED_LINKED_LIVE_CHAIN`.

| Link | Exact retained identity and result |
| --- | --- |
| Starting evidence | `bookshop-shift-01`, `run-0001`, RECORDED_INSPECTION; three incident events and no sale for that run. Not a fresh AI starter execution. |
| Investigation/repairs | `inv-0001`; A `ver-0003`, model-routed first public action plus deterministic guards; B `ver-0004`, ordinary-code alternative. |
| Qualifying comparison | `experiment-bookshop-shift-01-c1`; `run-0002` through `run-0007`, six COMPLETE slots; both candidates eligible; zero comparison business writes. |
| Explicit choice | `sel-0002`, prior `sel-0001`; selects `ver-0003`, retains `ver-0004`. |
| Selected operation | `bookshop-shift-02`, `run-0008`, `sel-0002`, `ver-0003`; FINALIZED / ISOLATED_LIVE; all three checks passed. |
| Synthetic consequence | Sale sequence 5; cause refs `run-0008`, `cr-0006`, `run-0008-out-1`; synthetic=true, VALID ledger chain. |
| Inheritance | `bookshop-shift-03`; draft equals selected artifact files; sale sequence 5 remains. |

Selected artifact: `fad72798c92b2b483084b08fb13bbbea72c8ea19d6e4f5de91b897042f9a0dfd`.
Sale hash: `e1d4f3117777d3c0361cecbb0ea5d775f515bce0eaa93d5435bca57425a443d2`.
Audited database: `cc3e36f12cc205b83fc8bdd076f53c6b21df4330e404e182b7fe6d992b8f0691`.
The database digest is historical, not newly verified in this checkout.

- Twelve comparison operations plus one selected operation; nineteen verified checkpoint readbacks. Ten inference results report 968 input/1,451 output tokens.
- Token arithmetic: USD 0.00040632 at then-checked rates, not a bill. Reservation-based usage: USD 0.02211840; combined ceiling: USD 0.04202496. Do not add these quantities.
- Per candidate: six public requests, four useful completions and two justified refusals, separate from three protected passes. The [review packet][s15] counts an unneeded conditional alternative as justified refusal, limiting the four-of-six interpretation.
- One real stream break: `run-0008-obs-2`, last event ID 3. The same operation resumed and finalized with one verified readback, without respawn or repeated inference.
- [Recovery][s20-recovery] bounds reconnects to three with 0.25/0.5/1-second backoff inside the original deadline; it preserves partial lines, ignores duplicate IDs and flushes pending observations on failure. Budgets do not reset. Repeated-break/duplicate/split-line cases are offline proofs, not additional live incidents.
- The [first attempt][s20-first], 15:16:10 to 15:17:38 UTC, stays ERROR: ten Sandbox attempts, four COMPLETE/two FAILED slots, eight inference attempts and seven results. No later choice/operation/inheritance completes that attempt.
- [Runner][s20-runner] prewrites the investigation and A rationale. [Candidate source][s20-code] requests and executes a first tool choice, but deterministic guards independently establish claims even if inference fails. Success does not prove AI necessity, stronger answers or learner reasoning.
- Original directories `artifacts/slice20-live-chain-2026-10-01/` and `artifacts/slice20-live-chain-resume-2026-10-01/` are absent here, including raw observations and databases. Retained summaries/audits are **HISTORICAL evidence**, not fresh inference UI or a newly repeated audit.

## 4. Actual Nebius capabilities, limits and S26 disposition

- Token Factory inference API returned model/tool decisions, finish reasons and
  usage. The controller holds provider credentials; sandboxed service code receives
  a bounded gateway, not the provider key. This enabled the measured tool-choice loop.
- Sandboxes executed uploaded service code with networking disabled, public image
  `python:3.11-slim`, image UUID `c7ad32fe-8621-3cd2-9022-521c6da02ac1`,
  stdin/stdout request transport and checkpoint download plus size/SHA-256 checks.
- [S12][s12] demonstrated normal-cap capture, reset and failure handling. Outer
  SUCCESS also accompanied inner exit 7 or timeout signal 9: inspect inner results.
  The original 2 MiB write yielding zero bytes under a 1 MiB cap remains unexplained.
  Normal 16 MiB-cap readbacks passed; smaller-cap capture is not established.
- S12's six repeated requests took 3,601-4,136 ms end to end, mean 3,898.7 ms;
  inference alone averaged 1,864.7 ms. This is one shape, not production latency.
- [S25 preflight][s25-preflight] reports all six permissions true and account limits
  of 50 concurrent instances, 3,600 seconds and 12 GiB layers. Limits reported by
  `whoami` are not exercised scaling capacity, GPU benchmarks or an availability SLA.
- No GPU instance rental, AI Cloud Serverless Job/Endpoint, DevPod deployment,
  public Sandbox ingress or hosted judge access is established by these records.
  Public ingress is unproved, not declared impossible. No development-speed benchmark.
- Historical beta notices and currency-less Sandbox `resources.cost` fields do not
  establish account charges. S25's vendor pricing table was unreadable; the operator
  retained 0.06/0.24 USD per million input/output as a conservative bound, not newly
  verified current prices. Every future live run needs its own authorization/preflight.
- [S22b][s22b] reports fourteen operations, twenty captures and one hint, with no
  service inference. Its raw completion and review directories are absent here;
  the checkpoint/packet remain historical summaries, not re-audited captures.
- [S25][s25] has two live operations, zero inference, with TRUSTED_LOCAL comparison,
  selection, close and inheritance. GTM's six 3-public-plus-1-protected slots hit
  the fresh-slot guard's 2-plus-1 pin before budget preflight. No full live GTM comparison.
- **S26: DROP_TAVILY_CLAIM. No discovery pitch.** [Status][status] and the retained
  [manifest][s26] record eight query calls, eighty raw results, sixty-six quarantined
  sources, fourteen duplicate drops, zero reviews and zero frozen changes. None of
  four preregistered structural events was discovered: zero useful discoveries and
  zero domains against thresholds of two each. Four other checks pass vacuously.
  This says nothing about general index coverage or review efficiency. The shipped
  operator CLI made functional calls, but bonus qualification is interpretive:
  **the submission-time bonus answer remains the user's call**, with DROP attached.

## 5. All Gate 4 section 5 no-go conditions

This is a condition-by-condition historical evidence assessment, not a blanket PASS
or a fresh security certification. [Gate 4][slices] owns the conditions. Current
runtime, packaging and browser checks belong to the parent S27 task.

| # | No-go condition | Evidence and remaining caveat |
| --- | --- | --- |
| 1 | Closed v5 cannot open a labelled no-choice shift, gains implicit starter/pointer, or operates/closes before first eligible choice | [S10][s10-status] records separate insertion/open/promotion/run/close guard faults; [S17][s17-status] records the first eligible null-prior choice unlock. Synthetic migration proof, not migration of a real learner's database today. |
| 2 | No-source v5 bootstrap is unsafe, unreviewed, exceeds public-only budget or creates eligibility/operation | [S13][s13-status] records isolated owned-source bootstrap; [S22b][s22b] records null investigation, no protected/selection/business effects and repeated-bootstrap/operation/close 409s. S22b raw evidence unavailable here; failed S13 attempt remains failed. |
| 3 | Any section 8 isolation/gateway probe succeeds: credential/controller/host/protected/other-run access; grant/model/limit/URL escape; normal/error/log secret leak; lost crash evidence/unpaid retry; dirty reset | [S12][s12] has bounded negative probes with controls, crash retention and reset; protected-fixture limb N/A. [S13][s13-status] reports product canary and exact grant guards. [S15][s15-plan] records paired reset/privacy proofs. S20 first attempt did lose one observation; [repair][s20-recovery] adds failure flushing and bounded resume, not retroactive recovery. No universal hostile-code-isolation claim. |
| 4 | Request/prompt widens controller-frozen tool policy | S12 escape maps undeclared output to none; [S13][s13-status] records exact-grant fault and injected-field 422/no-call proof. Harder S12 prompts exhausted tokens; no proof of model intent or exhaustive prompt resistance. |
| 5 | Meaningful in-service interpretation/tool choice cannot fit fixed ceilings | S12 STOCK and S13 catalog selection occurred; S20 has ten first-action choices. S13's first ceiling failed; S20 guard fallback means success does not prove dependence on the model. |
| 6 | Six-trial cost/latency forces replay or hidden dropped slots; twelve phase operations omitted | S16 records twelve operations/eighteen captures; S20 recovery records all six slots/twelve operations, plus separately metered operation. Failed first slots remain visible. S25 GTM live comparison is blocked, not silently reduced. Costs are estimates, not bills. |
| 7 | Reviewed Bellwether starter fails to reproduce incident, or supported irrelevant fact passes | [S11][s11-status] records price success but collection/alternative missing and whole-request failure. S13 live capture likewise remains task-incomplete. S20 starter is recorded inspection; no fresh starter inference claim. |
| 8 | Clarification counts as completion/referral, unnecessary clarification passes, timeout becomes clarification | [S16][s16-plan] records category/denominator fault proofs; S13 failed capture remains MISSING_OUTPUT. S20 has zero clarification cases, so its success does not independently exercise every category. |
| 9 | Three reviewed batches are not frozen to exact A/B bytes, hashes, counts and task specs | [S15][s15-plan] records phase/binding/swap/drop faults and [sealed packet][s15] exact pair material. S20 six slots completed. Historical policy proofs, not a fresh mutation audit of current code. |
| 10 | Experimental finalization mutates reducer/incident state | S11 diagnostic counts unchanged; [S18][s18-status] records purpose/reducer guards; S20 audit records zero comparison business writes; S22b reports unchanged experimental history. No inference that tests alone resolved an incident. |
| 11 | Invalidated evidence remains selectable or operable | S16 retirement, [S17][s17-status] invalidated-choice refusal/no fallback and [S18][s18-status] run-start revalidation are recorded. S20 successful valid-choice chain is not itself an invalidation probe. |
| 12 | Room hides selected version/history on desktop/mobile | S21/S22b historical browser proofs and [S25][s25-checkpoint] GTM journey/faults support visible values. **Open:** Northline 390px reach fails on macOS; full 23-pair rerun deferred. Earlier Windows evidence does not clear this defect. |
| 13 | FDE mission, initial/paired requests, manifest, state, catalog or protected inventory lacks review; Bellwether is substituted; edited code operates without owning comparison/choice; same rule for GTM | [S22b][s22b] binds reviewed Northline material, six owning slots, exact B and inherited files. [S23 application][s23] records GTM approval/pins and admission; S25 uses eligible exact A after trusted-local comparison. No real booking/CRM action or fully live GTM comparison claim. |
| 14 | Curriculum has an obvious prescribed repair | [S15 packet][s15] discloses two legal preferences but only one public separator; protected cases do not distinguish the pair. S20 A and its rationale are prewritten. Operator sealing is not learner-discovery evidence; pedagogical openness remains unproven, not PASS. |

Recorded inspection reads captures. TRUSTED_LOCAL executes pinned fixtures, not arbitrary learner code.
TRUSTED_LOCAL_TEST_DOUBLE is rehearsal even if simulated rows use live-looking labels.
Only verified ISOLATED_LIVE supports fresh execution claims, only for the recorded run.
Later trials cannot rewrite operational history. S20's offline later-condition proof
is separate from its live chain; no later live trial is implied.

## 6. Public-video SCRIPT draft, target 2:40

**Not recorded or authorized for recording/upload/publication.** Target 160 seconds.
Narration: **300 words**, counting hyphenated words as one; ceiling 320. At 120 words/minute,
allow 150 seconds of speech and 10 seconds of pauses. Only the six quoted blocks are spoken.
Final timed delivery must stay below three minutes. This document creates no video
or screenshot; a script is not proof of a functioning-device video.

Visual rule: only own app/content and plain source-backed text cards. No music,
third-party logos, trademarks, model/vendor names, browser branding, editor chrome,
notifications, protected fixtures, credentials or host paths in narration/visuals.
Text submission may describe vendor/model IDs above. Crop source views to relevant
functions and redact excluded identifiers. Never alter a result or hide its mode.

### 0:00-0:25 | What the app does

Proposed desktop app navigation, only after parent verification and separate recording
permission. Label any staged path OFFLINE DEMO. No invented screenshot placeholder.

> Shiftwork lets you practise maintaining a service across shifts. You inspect a
> failure, compare repairs, choose one tested version, and keep its consequences.
> This demonstration was authored by the operator with coding assistance in the
> learner role. It is not evidence that a learner discovered the repair.

### 0:25-0:50 | Failure and repair

Show a labelled recorded incident, then the owned repair source's task/record guards.
Use a separate HISTORICAL SOURCE label, not staged typing presented as original work.

> The recorded starter returned a price but missed required collection
> and alternative results. A true fact was not enough. The operator recorded a
> cause and test, then supplied two repairs. One asks a model for its first public
> information action. Both use code to check claims against records.

### 0:50-1:15 | Real inference, historical evidence

Show sanitized retained S20 summary rows, persistent HISTORICAL: 2026-10-01 label.
Do not show provider UI or animate a fresh response. Original database is unavailable.

> These retained records describe one linked live chain, not inference
> happening on screen now. Its comparison completed six slots under shared
> conditions. Nine model calls selected a public record lookup. Both candidates
> qualified. The earlier failed attempt remains separate, including its missing
> observation. We have not erased that failure.

### 1:15-1:40 | Exact choice

Show summary phase C: sel-0002, ver-0003, retained ver-0004, full selected hash.
Keep HISTORICAL visible. A read-only evidence card is not the original selection UI.

> The recorded choice selects version three and retains version four. Saving
> another version does not change what operates. This was an explicit operator
> choice, not a claim that the model-backed repair was better. The ordinary-code
> alternative also qualified, and the code can still establish claims if inference fails.

### 1:40-2:10 | Operation and inherited consequence

Show summary phase E, audit sale refs and phase F in sequence, HISTORICAL throughout.
Use actual run-0008, sale 5 and bookshop-shift-03 text, not fabricated room footage.

> The next shift operated that exact chosen version. One more real model call
> completed, all three checks passed, and the controller recorded one synthetic
> sale. A broken event stream resumed the same operation without another model
> request. The following shift inherited the selected files and kept the sale.
> Comparison runs wrote no business events.

### 2:10-2:40 | Limits and next step

Own-text limits card; if returning to current app, label OFFLINE DEMO again. Show
no download/public URL until publication is separately approved and access verified.

> That is one bounded technical chain. It does not prove learning gain, general
> answer quality, real revenue or production readiness. The original raw run
> files are unavailable in this checkout, so these are retained historical
> summaries. A current offline demonstration must stay labelled offline. Fresh
> execution and public access require separate preparation and permission.

## 7. Remaining submission blockers and evidence gaps

- Quality/recommend/experience scores remain blank; no fine-tuning, other-model benchmark, learner study or production-readiness evidence.
- S12 partial archives, S13 ceiling mismatch, S14 missing replies and S20/S22b absent raw directories remain gaps.
- Parent S27 verification completed 2026-10-15: the approved-lock clean-environment
  packaging test passed (7 tests; full offline pivot; labelled `OFFLINE_SKIP` for
  excluded credentials), the final suite ran 1,430 passed with only the known
  `port_dead` failure and the known live skip, the browser baselines were
  Bellwether PASS, GTM PASS and Northline's known 390px reach failure, and the
  source zip's scan/extraction receipts are in `evidence/slice27-package-2026-10-15/`;
  exact commands and limits are in `00-status.md`. Historical S26 packaging aborted
  in `ensurepip`; `port_dead` and Northline mobile reach remain recorded red rows,
  not fixed by this document.
- Missing live credentials require an explicit offline skip, not a live PASS. An offline-only package is not claimed as the approved qualifying demonstration ([Gate 4][slices]).
- Confirm packaged license/source/assets/setup instructions, test-build access and judging availability; no release or hosted-access claim here.
- Script needs permitted recording, timing and rights review, then separately authorized upload/public visibility/submission. No fabricated media or guessed URL.

## Local source register

Local retained evidence only; counts do not repeat provider calls. Historical acceptance-pending labels remain in older packets; later [status][status] records supersede those labels, not the underlying observations.

[rules]: ../../../HACKATHON_REQUIREMENTS.md
[slices]: 04-slices.md
[status]: 00-status.md
[s12]: evidence/slice12-capability-2026-09-26.md
[s12-original]: evidence/slice12-live-2026-09-26.jsonl
[s12-escape]: evidence/slice12-escape-20260926T135803Z.jsonl
[s12-trials]: evidence/slice12-trials-20260926T174521Z.jsonl
[s12-service]: evidence/slice12-service-20260927T000314Z.jsonl
[s12-outage]: evidence/slice12-outage-20260926T135627Z.jsonl
[s13-first]: evidence/slice13-model-20260927T063410Z.jsonl
[s13-second]: evidence/slice13-model-20260927T063601Z.jsonl
[s13-status]: 00-status.md#slice-13-cross-check-gap-repairs-and-stress-test-2026-09-27
[s14]: evidence/slice14-assist-live-2026-09-27.md
[s15]: slice15-operator-review-packet.md
[s15-plan]: slice15-implementation-plan.md
[s16-plan]: slice16-implementation-plan.md
[s10-status]: 00-status.md#slice-10-implementation-and-verification-2026-09-25
[s11-status]: 00-status.md#slice-11-implementation-and-local-verification-2026-09-26
[s17-status]: 00-status.md#slice-17-implemented-and-demonstrated-offline-2026-09-29
[s18-status]: 00-status.md#slice-18-offline-implementation-awaiting-acceptance-2026-09-29
[s20-first]: evidence/slice20-chain-live-summary-2026-10-01.json
[s20-summary]: evidence/slice20-sse-live-summary-2026-10-01.json
[s20-audit]: evidence/slice20-sse-live-audit-2026-10-01.json
[s20-resume]: evidence/slice20-sse-live-resume-audit-2026-10-01.json
[s20-recovery]: evidence/slice20-sse-recovery-2026-10-01.md
[s20-runner]: ../../../demos/slice20_live_chain.py
[s20-code]: ../../../shiftwork/fixtures/artifacts/bookshop/compare_repair_model_service.py
[s22b]: slice22b-live-completion-checkpoint-2026-10-05.md
[s22b-packet]: slice22b-live-completion-packet-2026-10-05.md
[s23]: slice23-application-checkpoint-2026-10-07.md
[s25]: evidence/slice25-live-2026-10-14/live-run.md
[s25-checkpoint]: slice25-portability-checkpoint-2026-10-11.md
[s25-preflight]: evidence/slice25-live-2026-10-14/preflight.md
[s25-receipt]: evidence/slice25-live-2026-10-14/receipt.json
[s25-meter]: evidence/slice25-live-2026-10-14/meter.json
[s26]: evidence/test3-manifest.json
