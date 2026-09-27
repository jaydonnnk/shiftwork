# Program Design: Shiftwork final pivot

**Current Gate 3 state: RE-APPROVED (2026-09-27), scoped to the S13 Sandbox
SDK dependency below.**

**Gate 3: RE-APPROVED 2026-09-24 after the scoped Northline selection backtrack.**

Gates 1, 2 and 4 are approved. Gate 2's scoped file-readback correction was
re-approved on 2026-09-26; the user separately re-approved this Gate 3
correction on 2026-09-26.
This document replaces the pre-pivot program
design with exact contracts for investigation, fair experiments, explicit
operating selection and operational consequences. The previous design remains
available in Git at `e1a3a91`. The earlier pivot design was approved and
committed as `de250b9`; that approval is historical after the legacy first-choice
Gate 2 backtrack. The user separately approved the reconciled working-tree
revision, which was committed and merged locally as `aedc97f` and `ab5ab9c`
without a co-author footer. Gate 4 review then exposed a further gap: the
comparison loader named only Bellwether workloads, leaving no qualifying
selection path for edited Northline code. The user approved this scoped
correction and authorized committing and pushing it to main without a co-author
footer. Gate 4 is separately approved. Neither approval is implementation
authority.

This is design, not runtime evidence. At the original 2026-09-24 Gate 3
approval, no package was installed, no migration or test was run, no credential
was used and no live model or sandbox was called. Later Slice 12 observations
are recorded in `00-status.md` and its evidence report. Existing Slices 1 to 9
and their historical evidence remain intact.

**SCOPED BACKTRACK RE-APPROVED, 2026-09-26:** section 8 and the
gateway/isolation test plan add file-capture verification after the Slice 12
checkpoint mismatch. This approval does not establish a reliable live capture
route or complete Slice 12. See `00-status.md` for current authority.

## 1. Decisions fixed at this gate

| Question | Decision |
| --- | --- |
| Existing stack | Keep the Python/FastAPI controller, SQLite store and plain HTML/CSS/vanilla-JavaScript client. No framework, task queue or second service is introduced. |
| Run authority | Every run has an immutable purpose: experiment or operation. Recorded inspection is an evidence mode, never fresh execution. |
| Investigation gate | The learner must append a cause, falsifier and chosen public test before diagnostic hints, diagnosis or patch help. Orientation is deterministic UI copy and is allowed earlier. |
| Comparison shape | One qualifying comparison has two frozen candidate versions and three predeclared paired workloads. Each workload is executed once per candidate, for six trial slots total. This is demonstration evidence, not statistical confidence. |
| Fairness | Both candidates share requirements, starting business state, public data, protected workload identities, model/settings and resource ceilings unless one field is the declared treatment. Unplanned drift makes the comparison not comparable. |
| Eligibility | All six slots must terminate with complete evidence. Every mandatory task, correctness and safety rule must pass. No average score can hide a mandatory failure. |
| Selection | The learner explicitly appends a choice of one eligible exact version plus rationale and retained alternative. Save, freeze, test and close never select implicitly. |
| Operation | Only a run bound to the latest valid operating selection can create ledger events or change incidents. Experimental finalization cannot call the reducer. |
| Inheritance | The next shift restores the selected version, rationale, alternative, visible tests, limits and unresolved incidents. It never chooses the latest saved version. |
| Service AI | Learner code may call a controller-mediated, run-bound Nemotron gateway. It never receives a provider credential or general controller/network access. Feasibility remains a capability-spike stop condition. |
| Assistance | Assist and service inference have different grants, records and budgets. Neither can read sealed material, grade work or select a version. |
| Historical evidence | Schema v5 rows remain byte-preserved and are labelled legacy evidence. Migration never invents an experiment, comparison or learner choice. |
| Legacy first choice | A closed v5 engagement with no selection opens a controller-labelled requalification shift for investigation and comparison. It has no operating pointer or selected-contract close until the learner makes a valid explicit choice. |
| Workload binding | The controller freezes three reviewed request batches with exact bytes, hashes and parsed request counts. Each pair's A and B slots reference the same batch; there is no generic six-slot batch. |
| Gateway tool policy | The controller derives a run-scoped tool allowlist from frozen policy. Learner code cannot widen it by request field or prompt text. |
| Clarification | A captured clarification is assessed and reported separately from completion, refusal, referral and missing output. Its acceptability follows a public task rule, not the service's own label. |
| Curriculum ownership | Bellwether has an executable failing starter plus reviewed incident/workload data. Northline has a distinct blank learner scaffold, mission, incident requests, three paired workloads with a reviewed manifest, state and protected assessment owned outside learner code. File contents and catalog identity require review before use. |
| UI | The operational room remains the shell. The client must visibly separate investigation, experiment, selected version and operational history. |

The three comparison pairs are the smallest approved product demonstration that
can show repeated stochastic outcomes without pretending to estimate a stable
population rate. If the live spike shows six trials are unaffordable or too slow,
Gate 3 must be backtracked. Do not silently lower the count or substitute replay.

## 2. Exact file map

Files not listed here are preserved. Gate 4 may split these changes into smaller
vertical slices, but it may not silently change their ownership.

### Existing production files to change

| File | Responsibility after reconciliation |
| --- | --- |
| `shiftwork/app.py` | Wire the revised configuration, gateway boundary, schema migration, reviewed Northline engagement seeding and startup reconciliation. |
| `shiftwork/config.py` | Named experiment, operation, inference and assist ceilings; model/image config names; controller-owned per-engagement fixture and tool policy and reason render map. No secret values. |
| `shiftwork/domain/models.py` | Durable shift opening mode, investigation, context, experiment, trial, gateway-event, selection and revised run types. |
| `shiftwork/domain/canonical.py` | Versioned canonical hashes for complete execution contexts and assessment snapshots, while retaining old artifact hashes. |
| `shiftwork/domain/customer_answer.py` | Render customer text only from the validated task-aware envelope and public records. |
| `shiftwork/domain/contract_catalog.py` | Keep the immutable per-engagement catalog loader; refuse a missing or incompatible reviewed Northline catalog rather than borrowing Bellwether options or guessing a version. |
| `shiftwork/domain/errors.py` | Stable conflict, incomplete-evidence, invalid-selection, drift, budget and gateway failure kinds. |
| `shiftwork/api/schemas.py` | Strict request models and safe public projections defined in section 3.7. |
| `shiftwork/api/routes.py` | Final routes in section 5; handlers only validate, delegate and map typed failures. |
| `shiftwork/store/schema.sql` | Fresh-database schema including the new pivot records and constraints. |
| `shiftwork/store/db.py` | Transactional v5 to v6 migration and refusal of unknown versions. |
| `shiftwork/store/repo.py` | Parameterized reads/writes for every new record and idempotent engagement seeding; no policy decisions. |
| `shiftwork/evaluator/evaluator.py` | Pure assessment from explicit captured inputs, including entity and required-task checks. No loader or model access. |
| `shiftwork/ledger/reducer.py` | Accept only an `OperationalAssessment`; reject experimental inputs by type and runtime guard. |
| `shiftwork/executor/base.py` | Purpose/context-bound execution request, slot-selected workload and trusted request/tool driver, observation stream and trusted measurement fields. Required file-backed capture carries readback byte count/digest or an incomplete-evidence failure. |
| `shiftwork/executor/local_process.py` | Retain byte-pinned trusted-fixture restriction and implement the revised adapter protocol. |
| `shiftwork/executor/recorded.py` | Retain transcript inspection and label it `RECORDED_INSPECTION`; never emit fresh eligibility. |
| `shiftwork/sealed/store.py` | Orchestration-only loader for exact reserved protected workload refs. |
| `shiftwork/sealed/rotation.py` | Comparison-scoped paired reservation and separate operational reservation policy. |
| `shiftwork/orchestrator.py` | Investigation, experiment, selection and operation lifecycles; the only caller of the sealed loader. |
| `shiftwork/client/index.html` | One accessible application shell for the approved six-station journey. |
| `shiftwork/client/app.js` | State and interactions for investigation, comparison, selection, operation and inheritance. |
| `shiftwork/client/evidence.js` | Pure formatting of public evidence, metrics and reason codes. |
| `shiftwork/client/styles.css` | Existing room direction plus clear purpose/status hierarchy and mobile access. |
| `shiftwork/client/room.svg` | Keep the accepted room composition; add only state hooks needed by the approved stations. |

### New production files

| File | Responsibility |
| --- | --- |
| `shiftwork/domain/task_contract.py` | Pure validation of public requested entities/tasks and the structured service response envelope. |
| `shiftwork/domain/comparison.py` | Pure completeness, comparability, eligibility and metric derivation. Never selects a winner. |
| `shiftwork/store/migrations/v6.sql` | Additive v5 to v6 migration described in section 4. |
| `shiftwork/gateway/__init__.py` | Package boundary only. |
| `shiftwork/gateway/protocol.py` | Run capability, request/response and observation types. |
| `shiftwork/gateway/service_inference.py` | Controller-side Nemotron mediation with bounded model, calls, bytes, tokens, deadline, controller-owned tool allowlist and redaction. |
| `shiftwork/assist/__init__.py` | Package boundary only. |
| `shiftwork/assist/gateway.py` | Prediction-gated, attributable Nemotron help with a separate budget. |
| `shiftwork/executor/tokenfactory.py` | Real isolated adapter behind the existing protocol, added only after the capability spike passes and credentials are separately authorized. Read saved checkpoint files before returning file-backed capture evidence; outer operation status and process stdout cannot supply file bytes. |
| `pyproject.toml` | Declare the controller-side Sandbox SDK selected after the verified S12 transport, with the HTTPX extra and an exact version pin. The learner artifact never imports or receives it. |
| `requirements.lock` | Resolve that exact SDK declaration for reproducible clean installs while retaining the existing HTTPX pin. |
| `shiftwork/curation/__init__.py` | Package boundary only; never imported by the runtime application. |
| `shiftwork/curation/pipeline.py` | Operator-only Tavily discovery, human verification and frozen-fixture lifecycle. |
| `shiftwork/curation/ablation.py` | Frozen, known-page polling and Tavily comparison with the retained DROP rule. |
| `shiftwork/fixtures/mission/bookshop_pivot_v1.json` | Public mandatory tasks, visible requirements, allowed information/tool vocabulary and deterministic render vocabulary for Bellwether. |
| `shiftwork/fixtures/artifacts/bookshop/pivot_starter_failure_service.py` | Executable learner-editable Bellwether starter whose reviewed incident request exposes the task-completion failure. It must use the approved executor protocol; its contents and pin are not supplied by this design. |
| `shiftwork/fixtures/requests/bookshop_pivot_incident.jsonl` | Reviewed public Bellwether failure request for the first investigation, distinct from protected cases and the three paired workloads. |
| `shiftwork/fixtures/shop/bookshop_pivot_public_state.json` | Reviewed public records and dependency condition needed to reproduce that failure; exact bytes are captured with the run. |
| `shiftwork/fixtures/runs/bookshop_pivot_incident_recorded.json` | Optional labelled offline inspection capture for the same pinned starter/request/state; never fresh eligibility or a substitute for the live service. |
| `shiftwork/fixtures/requests/bookshop_compare_pair_01.jsonl` | First paired public workload. Exact contents require review and sealing. |
| `shiftwork/fixtures/requests/bookshop_compare_pair_02.jsonl` | Second paired public workload. Exact contents require review and sealing. |
| `shiftwork/fixtures/requests/bookshop_compare_pair_03.jsonl` | Third paired public workload. Exact contents require review and sealing. |
| `shiftwork/fixtures/requests/bookshop_compare_manifest.json` | Operator-reviewed ordinal 1/2/3 mapping with independently pinned file hashes, parsed request counts and task-spec hashes; created only after the three actual batches are reviewed. |
| `shiftwork/sealed/cases/bookshop_task_completion.json` | Protected task/entity/completion cases with at least six variants. Exact cases require a separate sealing review. |
| `shiftwork/templates/artifact/northline_blank_service.py` | Executable minimal service scaffold with no authored transfer solution; the away learner owns its logic and starts from a blank artifact. |
| `shiftwork/fixtures/mission/northline_transfer.json` | Operator-reviewed public future-commitment, safety-escalation and retry-safe booking rules, allowed information/tool vocabulary and deterministic synthetic transitions. No Bellwether rules are borrowed. |
| `shiftwork/fixtures/requests/northline_transfer.jsonl` | Operator-reviewed public away requests and required-task specifications, captured as exact bytes for execution. |
| `shiftwork/fixtures/state/northline_start.json` | Reviewed public starting booking/dependency state, restored between trials. |
| `shiftwork/fixtures/requests/northline_compare_pair_01.jsonl` | First reviewed public Northline qualifying workload, distinct from the initial transfer request. |
| `shiftwork/fixtures/requests/northline_compare_pair_02.jsonl` | Second reviewed public Northline qualifying workload. |
| `shiftwork/fixtures/requests/northline_compare_pair_03.jsonl` | Third reviewed public Northline qualifying workload. |
| `shiftwork/fixtures/requests/northline_compare_manifest.json` | Operator-reviewed ordinal 1/2/3 mapping with independently pinned file hashes, parsed request counts and task-spec hashes. |
| `shiftwork/sealed/cases/northline_transfer.json` | Operator-authored protected transfer acceptance cases, loaded only by orchestration and passed as explicit inputs to the pure evaluator; no case contents are set here. |
| `demos/final_pivot.py` | Canonical offline walkthrough: inspect, predict, compare, choose, operate, inherit and test retained alternative. |
| `demos/gateway_spike.py` | Separately authorized capability-spike driver. It is not part of normal offline verification. |

### Tests to add or change

| File | Scope |
| --- | --- |
| `tests/store/test_pivot_migration.py` | v5 preservation, v6 constraints and no invented history. |
| `tests/domain/test_task_contract.py` | Request/entity/task envelope validation and customer rendering inputs. |
| `tests/domain/test_comparison.py` | Completeness, comparability, eligibility and metric denominators. |
| `tests/evaluator/test_evaluator.py` | Extend pure evaluator coverage for requested-task completion and mandatory rules. |
| `tests/orchestrator/test_investigation_assist.py` | Prediction gate, revisions, attribution and assist budget. |
| `tests/orchestrator/test_experiment_lifecycle.py` | Frozen context, paired schedule, exposure, drift, failure and idempotency. |
| `tests/orchestrator/test_selection_operation.py` | Exact selection, operation-only consequences, retry rules, inheritance and invalidation. |
| `tests/orchestrator/test_northline_transfer.py` | Blank-scaffold ownership, reviewed mission/request/state/catalog/paired-workload/protected prerequisites, reduced help, cross-engagement substitution rejection and the qualifying comparison to explicit selection and selected-version operation path. |
| `tests/orchestrator/test_replay.py` | Historical semantic replay, unknown legacy inputs and zero mutation. |
| `tests/executor/conformance.py` | Revised adapter contract shared by recorded, trusted-local and live adapters. |
| `tests/executor/test_gateway_isolation.py` | Run binding, expiry, model allowlist, network boundary, credential absence and redaction probes. |
| `tests/api/test_pivot_routes.py` | Status codes, idempotency and route-level ownership checks. |
| `tests/api/test_pivot_projection.py` | Public allowlists and serialized leak detection for every new surface. |
| `tests/client/pivot-browser.mjs` | Native keyboard/touch journey on desktop and narrow viewports. |
| `tests/client/pivot-render-faults.mjs` | One served-source mutation for every substantive displayed purpose, status, candidate, metric and selection value. |
| `tests/assist/test_gateway.py` | Role permission, initial-prediction requirement, attribution, rejection and redaction. |
| `tests/curation/test_ablation.py` | Retained Tavily protocol and DROP behavior. |
| `tests/mutation_proofs.py` | Add named, valid, assertion-level mutations for every new policy guard. |
| `tests/packaging/test_clean_env_install_and_run.py` | Include the final offline pivot demo; live extras remain separately gated. |

Known existing callers also change where their old latest-version or automatic-
consequence assumptions would otherwise fail: `demos/lifecycle.py`,
`demos/repair_loop.py`, `demos/test1.py`, `tests/conftest.py`,
`tests/api/test_tracer_lifecycle.py`, `tests/api/test_thin_path.py`,
`tests/api/test_client_evidence.py`, `tests/api/test_client_preview.py`,
`tests/ledger/test_ledger.py`, `tests/orchestrator/conftest.py`,
`tests/orchestrator/test_budget_rotation.py`,
`tests/orchestrator/test_close_inheritance.py`,
`tests/orchestrator/test_run_binding.py`,
`tests/orchestrator/test_test1_preproof.py`, `tests/store/test_restore.py`,
`tests/store/test_versions.py`, `tests/sealed/test_import_graph.py`,
`tests/sealed/test_payload_manifest.py` and `tests/sealed/test_sentinel_leak.py`.
They retain their historical assertions where still true and add explicit setup for
purpose, context and selection. They may not be weakened merely to accept v6.

**Scoped S13 dependency correction, re-approved 2026-09-27.**
The accepted S12 spike used `contree-client[httpx]==0.4.0` for real Sandbox
spawn, file transfer, operation streaming and checkpoint readback. S13's production
adapter uses that same SDK in the trusted controller process; writing a second
Sandbox HTTP client with the already installed `httpx` would duplicate the
transport and its failure handling. Add `contree-client[httpx]==0.4.0` to
`pyproject.toml` and regenerate `requirements.lock` with pin parity after this
correction is approved. `httpx==0.28.1` is already in the lock. Do not add the
other SDK transport extras. The SDK and the provider credential remain outside
the learner artifact and Sandbox. The clean-install packaging check and S13
adapter tests must exercise the locked dependency. This approval is confined to
the dependency correction and does not authorize ADR #4, fixtures or publication.

The file map assigns ownership, not permission to invent executable contents.
Current source has the old bookshop template, mission and catalog, plus the trusted
Slice 8 repair-arc fixtures; none is the pivot starter or Northline transfer.
The Northline catalog must be reviewed and frozen through the existing loader's
`{slug}_v{version}.json` convention before any transfer execution. This design
assigns no version or case content. If no compatible catalog is approved, Northline
execution and any transfer claim stop. The same review and byte pins apply to the
new Bellwether starter, incident request, public state and three paired workloads.
Northline's three separate comparison batches and manifest also require review,
byte pins and enough protected variants under the same reservation policy before
its learner-edited version can qualify. The initial `northline_transfer.jsonl`
request supports the starter and later operational run, never comparison
eligibility by itself.
No placeholder hash or request count is treated as approved fixture data.

## 3. Types and signatures

Signatures have no implementation bodies. Domain and API models use Pydantic v2
with `frozen=True, extra="forbid"`. IDs are opaque strings and timestamps are UTC.

### 3.1 Identity, purpose and captured context

```python
type Id = str
type Slug = str
type Sha256 = str

class RunPurpose(StrEnum):
    EXPERIMENT = "EXPERIMENT"
    OPERATION = "OPERATION"
    LEGACY_OPERATION = "LEGACY_OPERATION"

class EvidenceMode(StrEnum):
    RECORDED_INSPECTION = "RECORDED_INSPECTION"
    TRUSTED_LOCAL = "TRUSTED_LOCAL"
    ISOLATED_LIVE = "ISOLATED_LIVE"

class ExperimentKind(StrEnum):
    DIAGNOSTIC = "DIAGNOSTIC"
    QUALIFYING_COMPARISON = "QUALIFYING_COMPARISON"
    LATER_CONDITION_COMPARISON = "LATER_CONDITION_COMPARISON"

class ShiftOpeningMode(StrEnum):
    STANDARD = "STANDARD"
    LEGACY_FIRST_CHOICE = "LEGACY_FIRST_CHOICE"

class ContextCondition(BaseModel):
    id: Id
    kind: Literal["normal", "data_update", "dependency_unavailable"]
    public_label: str
    exact_bytes_base64: str
    content_hash: Sha256

class FrozenWorkload(BaseModel):
    id: Id
    ordinal: int
    request_batch_bytes_base64: str
    request_batch_hash: Sha256
    request_specs_bytes_base64: str
    request_specs_hash: Sha256
    request_count: int

class ExecutionContext(BaseModel):
    id: Id
    schema_version: Literal[1]
    engagement_slug: Slug
    workloads: tuple[FrozenWorkload, ...]
    mission_bytes_base64: str
    mission_hash: Sha256
    public_data_bytes_base64: str
    public_data_hash: Sha256
    starting_business_state_json: dict[str, JsonValue]
    starting_business_state_hash: Sha256
    requirement_set_id: Id
    requirement_set_hash: Sha256
    visible_check_set_hash: Sha256
    protected_reservation_id: Id | None
    condition: ContextCondition
    evaluator_version: str
    reducer_version: str
    executor_class: EvidenceMode
    harness_hash: Sha256
    image_ref: str | None
    service_model: str | None
    service_model_settings_json: dict[str, JsonValue]
    resource_limits_json: dict[str, JsonValue]
    created_at: datetime
    content_hash: Sha256

def context_hash(context: ExecutionContext) -> Sha256: ...
```

Reconstructible public mission rules and inputs are stored as bytes plus hashes.
The protected reservation points to controller-only material and is never
projected. A mutable
path, current fixture or current incident state cannot reconstruct old evidence.
The controller parses each frozen request batch once and requires a nonzero count
of at most four requests, matching the same number of frozen public task specs.
A qualifying comparison has exactly three ordered workloads; a diagnostic or
operational context has one. The context hash covers the frozen mission bytes/hash
and each workload's exact bytes, hashes, count and order. Future workload bytes
remain controller-held and are not
provisioned to a learner service before each permitted request is streamed.

### 3.2 Investigation and assistance

```python
class Investigation(BaseModel):
    id: Id
    shift_id: Id
    source_run_id: Id
    source_request_ordinal: int
    cause: str
    falsifier: str
    public_test: str
    revision_of_id: Id | None
    authored_by: Literal["learner"]
    created_at: datetime

class InvestigationRequest(BaseModel):
    source_run_id: Id
    source_request_ordinal: int
    cause: str
    falsifier: str
    public_test: str
    revision_of_id: Id | None
    client_request_id: str

class AssistRole(StrEnum):
    HINT = "HINT"
    DIAGNOSIS = "DIAGNOSIS"
    PATCH_PROPOSAL = "PATCH_PROPOSAL"

class AssistEvent(BaseModel):
    id: Id
    shift_id: Id
    investigation_id: Id
    role: AssistRole
    model_id: str
    request_text: str
    response_text: str
    proposed_patch: str | None
    accepted: bool | None
    created_at: datetime

class AssistRequest(BaseModel):
    investigation_id: Id
    role: AssistRole
    message: str

class AssistDecision(BaseModel):
    accepted: bool

def request_assist(conn, shift_id: Id, request: AssistRequest) -> AssistEvent: ...
def record_assist_decision(conn, event_id: Id, decision: AssistDecision) -> AssistEvent: ...
```

An investigation revision never overwrites its parent. Every non-orientation
assist role requires a complete investigation owned by the shift. Accepting a
patch records attribution only. It does not edit code, freeze a version, prove a
cause or affect eligibility.

### 3.3 Public task contract and service response

```python
class TaskKind(StrEnum):
    ANSWER_FACT = "ANSWER_FACT"
    CONFIRM_COLLECTION = "CONFIRM_COLLECTION"
    SUGGEST_ALTERNATIVE = "SUGGEST_ALTERNATIVE"
    CREATE_BOOKING = "CREATE_BOOKING"
    EXPLAIN_LIMIT = "EXPLAIN_LIMIT"

class RequiredTask(BaseModel):
    id: Id
    kind: TaskKind
    requested_entity_ref: str
    condition_json: dict[str, JsonValue]
    required: bool

class CustomerRequestSpec(BaseModel):
    id: Id
    text: str
    requested_entities: tuple[str, ...]
    tasks: tuple[RequiredTask, ...]
    mandatory_rule_ids: tuple[str, ...]

class VisibleCheck(BaseModel):
    id: Id
    request: CustomerRequestSpec
    observable_expectation: str
    authored_by: Literal["learner"]

class Claim(BaseModel):
    kind: Literal["price", "stock", "availability", "policy_answer", "booking", "none"]
    entity_ref: str
    value: JsonValue
    evidence_refs: tuple[str, ...]

class TaskResult(BaseModel):
    task_id: Id
    status: Literal[
        "COMPLETED", "NEEDS_CLARIFICATION", "REFUSED", "REFERRED", "NOT_APPLICABLE"
    ]
    entity_ref: str
    claims: tuple[Claim, ...]
    commitment_ref: str | None
    explanation_code: str | None

class ServiceResponse(BaseModel):
    request_id: Id
    task_results: tuple[TaskResult, ...]
    evidence_refs: tuple[str, ...]
    uncertainty_codes: tuple[str, ...]

class TaskAssessment(BaseModel):
    request_id: Id
    request_ordinal: int
    task_id: Id
    outcome: Literal[
        "USEFUL_COMPLETION", "INCORRECT_OUTPUT", "JUSTIFIED_REFUSAL",
        "JUSTIFIED_REFERRAL", "JUSTIFIED_CLARIFICATION",
        "UNJUSTIFIED_REFUSAL", "UNJUSTIFIED_REFERRAL",
        "UNJUSTIFIED_CLARIFICATION",
        "MISSING_OUTPUT"
    ]
    mandatory_pass: bool
    reason_codes: tuple[ReasonCode, ...]

def validate_response_envelope(
    request: CustomerRequestSpec,
    response_bytes: bytes,
) -> ServiceResponse: ...

def render_customer_text(
    request: CustomerRequestSpec,
    response: ServiceResponse,
    public_records: dict[str, JsonValue],
) -> str: ...
```

The service emits no independent free-text customer answer. The controller renders
text only from a validated envelope, so unassessed prose cannot contradict the
structured result. A response that supplies the correct price but omits collection
and alternative task results fails the required-task checks.

`NEEDS_CLARIFICATION` must name a public `explanation_code` tied to a missing
detail for the requested entity. The independent task rule, not the service,
decides whether the clarification is justified. A justified clarification is
reported separately and is not useful completion; it satisfies a mandatory
task only when that task's frozen public rule explicitly permits asking for the
missing detail. Unnecessary or blanket clarification is unjustified and cannot
pass a required completion task. Missing execution evidence cannot become a
clarification.

Mandatory reason codes added to the existing vocabulary are:

```text
WRONG_ENTITY
REQUIRED_TASK_MISSING
UNSUPPORTED_CLAIM
INVALID_COMMITMENT
UNJUSTIFIED_REFUSAL
UNJUSTIFIED_REFERRAL
UNJUSTIFIED_CLARIFICATION
MISSING_EXECUTION_EVIDENCE
CONTEXT_DRIFT
EXPOSURE_INVALIDATED
GATEWAY_LIMIT_EXCEEDED
```

### 3.4 Evaluator and comparison policy

```python
class AssessmentInput(BaseModel):
    run: Run
    context: ExecutionContext
    outputs: tuple[RunOutput, ...]
    observations: tuple[ExecutionObservation, ...]
    request_specs: tuple[CustomerRequestSpec, ...]
    visible_checks: tuple[VisibleCheck, ...]
    protected_cases: tuple[SealedCase, ...]
    contract: ContractParams
    public_records: dict[str, JsonValue]

class RunAssessment(BaseModel):
    run_id: Id
    context_hash: Sha256
    check_results: tuple[CheckResult, ...]
    task_assessments: tuple[TaskAssessment, ...]
    complete_request_count: int
    expected_request_count: int
    mandatory_pass: bool

class OperationalAssessment(RunAssessment):
    purpose: Literal[RunPurpose.OPERATION]
    selection_id: Id

class CandidateMetrics(BaseModel):
    candidate_version_id: Id
    denominator_requests: int
    useful_completions: int
    incorrect_outputs: int
    justified_refusals: int
    justified_referrals: int
    justified_clarifications: int
    unjustified_refusals: int
    unjustified_referrals: int
    unjustified_clarifications: int
    missing_outputs: int
    service_calls: int
    input_tokens: int | None
    output_tokens: int | None
    service_latency_ms: int | None
    provisioning_latency_ms: int | None
    cost_minor_units: int | None

class CandidateEligibility(BaseModel):
    candidate_version_id: Id
    eligible: bool
    blocking_reason_codes: tuple[ReasonCode, ...]

class ComparisonOutcome(BaseModel):
    experiment_id: Id
    status: Literal["INCOMPLETE", "NOT_COMPARABLE", "COMPLETE"]
    shared_denominator_requests: int
    candidate_metrics: tuple[CandidateMetrics, CandidateMetrics]
    eligibility: tuple[CandidateEligibility, CandidateEligibility]
    drift_fields: tuple[str, ...]

def evaluate(input: AssessmentInput) -> RunAssessment: ...
def compare(
    experiment: Experiment,
    trials: tuple[TrialSlot, ...],
    assessments: tuple[RunAssessment, ...],
) -> ComparisonOutcome: ...
```

`evaluate` and `compare` are pure, deterministic and LLM-free. They do not read
files, databases, environment variables or the network. Unknown usage or cost stays
`None`. An unknown mandatory budget measure blocks eligibility. Metrics have one
shared request denominator, and every failed or missing slot remains visible.
Clarifications keep distinct assessed and reported counters in the public
comparison and task-detail views. Neither category increments useful completion,
refusal or referral. The denominator is the sum of the three frozen workload
request counts per candidate, including requests with missing outputs.
`useful_completions` counts a request only when all required tasks are completed;
the other counters count requests containing at least one assessed outcome of
their named kind. One multi-task request can appear in several non-completion
categories, so these incidence counts are labelled non-additive and are never
presented as shares that sum to the denominator.

### 3.5 Experiments, runs, observations and gateway

```python
class CandidateRef(BaseModel):
    label: Literal["A", "B"]
    artifact_version_id: Id
    artifact_content_hash: Sha256

class Experiment(BaseModel):
    id: Id
    shift_id: Id
    kind: ExperimentKind
    investigation_id: Id | None
    candidates: tuple[CandidateRef, ...]
    declared_treatment: str
    context_id: Id
    content_hash: Sha256
    trial_count_per_candidate: Literal[1, 3]
    state: Literal["PLANNED", "RUNNING", "FINALIZED", "FAILED", "INVALIDATED"]
    client_request_id: str
    created_at: datetime

class TrialSlot(BaseModel):
    id: Id
    experiment_id: Id
    pair_ordinal: int
    execution_ordinal: int
    candidate_label: Literal["A", "B"]
    artifact_version_id: Id
    workload_id: Id
    request_batch_hash: Sha256
    request_count: int
    run_id: Id | None
    protected_variant_refs: tuple[str, ...]
    state: Literal["RESERVED", "RUNNING", "COMPLETE", "FAILED"]

class ExperimentRequest(BaseModel):
    kind: ExperimentKind
    investigation_id: Id | None
    candidate_a_version_id: Id
    candidate_b_version_id: Id | None
    declared_treatment: str
    later_condition_run_id: Id | None
    client_request_id: str

class Run(BaseModel):
    id: Id
    shift_id: Id
    artifact_version_id: Id
    purpose: RunPurpose
    evidence_mode: EvidenceMode
    context_id: Id | None
    experiment_id: Id | None
    trial_slot_id: Id | None
    selection_id: Id | None
    attempt_number: int
    state: RunState
    adapter: Literal["recorded", "local_process", "tokenfactory"]
    failure_kind: ExecutorFailure | None
    started_at: datetime
    ended_at: datetime | None

class ObservationKind(StrEnum):
    INTERPRETATION = "INTERPRETATION"
    TOOL_REQUEST = "TOOL_REQUEST"
    TOOL_RESULT = "TOOL_RESULT"
    INFERENCE_REQUEST = "INFERENCE_REQUEST"
    INFERENCE_RESULT = "INFERENCE_RESULT"
    USAGE = "USAGE"

class ExecutionObservation(BaseModel):
    id: Id
    run_id: Id
    request_ordinal: int
    ordinal: int
    kind: ObservationKind
    public_payload_json: dict[str, JsonValue]
    raw_payload_ref: str
    measured_at: datetime

class InferenceGrant(BaseModel):
    grant_id: Id
    run_id: Id
    audience: Literal["service-inference"]
    allowed_model: str
    allowed_tool_names: tuple[str, ...]
    max_calls: int
    max_input_bytes: int
    max_output_tokens: int
    deadline_ms: int
    expires_at: datetime

class InferenceRequest(BaseModel):
    grant: str
    request_ordinal: int
    input_text: str

class InferenceReply(BaseModel):
    text: str
    proposed_tool_names: tuple[str, ...]
    input_tokens: int | None
    output_tokens: int | None

class ExecutorAdapter(Protocol):
    async def execute(self, request: RunRequest) -> RunResult: ...

class ServiceInferenceGateway(Protocol):
    async def infer(self, request: InferenceRequest) -> InferenceReply: ...
```

The sandbox may read only a short-lived run capability, not the provider key. The
gateway derives run identity from the capability, never from a caller-supplied ID.
The controller derives the grant's immutable `allowed_tool_names` from the frozen
mission policy and exact run context. The learner request cannot provide or widen
that list. The gateway rejects model proposals outside the grant's allowlist;
the trusted request driver separately refuses execution of any unlisted tool,
even when prompt text asks for it. It exposes one inference operation and an
allow-listed tool vocabulary, not a URL proxy. It
records trusted request/response/usage observations before returning.
The grant is revoked when the run ends. The capability, provider headers and raw
provider errors must be removed from captures, logs and every public projection.

### 3.6 Selection, ancestry and orchestration

```python
class VersionAuthorship(BaseModel):
    learner_edited: bool
    generated_patch_seen_count: int
    generated_patch_accepted_count: int
    learner_declared_generated_patch_use: bool

class ArtifactVersion(BaseModel):
    id: Id
    shift_id: Id
    parent_id: Id | None
    restored_from_id: Id | None
    content_hash: Sha256
    files: dict[str, str]
    contract: ContractParams
    contract_catalog_hash: Sha256
    authorship: VersionAuthorship
    created_at: datetime

class OperatingSelection(BaseModel):
    id: Id
    engagement_slug: Slug
    shift_id: Id
    kind: Literal["STARTER_BASELINE", "LEARNER_CHOICE"]
    selected_version_id: Id
    selected_content_hash: Sha256
    comparison_id: Id | None
    retained_alternative_version_id: Id | None
    rationale: str
    requirement_set_hash: Sha256
    prior_selection_id: Id | None
    state: Literal["VALID", "INVALIDATED"]
    client_request_id: str
    created_at: datetime

class SelectionRequest(BaseModel):
    comparison_id: Id
    selected_version_id: Id
    rationale: str
    expected_prior_selection_id: Id | None
    client_request_id: str

class FreezeVersionRequest(BaseModel):
    contract: ContractParams
    learner_declared_generated_patch_use: bool

class ReplayReport(BaseModel):
    run_id: Id
    status: Literal["IDENTICAL", "DIFFERENT", "UNKNOWN_MISSING_INPUTS"]
    check_differences: tuple[dict[str, JsonValue], ...]
    event_draft_differences: tuple[dict[str, JsonValue], ...]
    wrote_rows: Literal[False]

def append_investigation(conn, shift_id: Id, request: InvestigationRequest) -> Investigation: ...
def seed_reviewed_northline(conn) -> None: ...
def open_next_shift(conn, slug: Slug) -> Shift: ...
def freeze_version(conn, shift_id: Id, request: FreezeVersionRequest) -> ArtifactVersion: ...
def create_experiment(conn, shift_id: Id, request: ExperimentRequest) -> Experiment: ...
async def execute_experiment(db_path: str, experiment_id: Id) -> None: ...
def finalize_experiment_run(conn, run_id: Id) -> RunAssessment: ...
def append_selection(conn, shift_id: Id, request: SelectionRequest) -> OperatingSelection: ...
def start_operation(conn, shift_id: Id, client_request_id: str) -> Run: ...
async def execute_run(run_id: Id) -> None: ...
def finalize_operation(conn, run_id: Id) -> OperationalAssessment: ...
def restore_version_to_draft(conn, shift_id: Id, version_id: Id) -> Draft: ...
def close_shift(conn, shift_id: Id, client_request_id: str) -> Shift: ...
def reconcile_interrupted(conn) -> tuple[Id, ...]: ...
def replay_assessment(conn, run_id: Id) -> ReplayReport: ...
```

`parent_id` is the draft base actually edited. Restoring A after saving B sets
`restored_from_id=A`; the next freeze has `parent_id=A`, not the newest timestamp.
Identical content hashes remain the same behavior candidate even when version IDs
differ. Authorship is evidence, not a score.

### 3.7 Public API projections

```python
class ArtifactSourceView(BaseModel):
    id: Id
    parent_id: Id | None
    content_hash: Sha256
    files: dict[str, str]
    contract: ContractView
    authorship: VersionAuthorship

class AssistEventView(BaseModel):
    id: Id
    role: AssistRole
    model_id: str
    response_text: str
    proposed_patch: str | None
    accepted: bool | None
    created_at: datetime

class InvestigationView(BaseModel):
    id: Id
    source_run_id: Id
    source_request_ordinal: int
    cause: str
    falsifier: str
    public_test: str
    revision_of_id: Id | None
    assist_events: tuple[AssistEventView, ...]
    created_at: datetime

class FrozenWorkloadView(BaseModel):
    id: Id
    ordinal: int
    request_batch_hash: Sha256
    request_count: int

class TrialView(BaseModel):
    id: Id
    pair_ordinal: int
    candidate_label: Literal["A", "B"]
    workload_id: Id
    request_batch_hash: Sha256
    request_count: int
    run_id: Id | None
    state: Literal["RESERVED", "RUNNING", "COMPLETE", "FAILED"]
    evidence_mode: EvidenceMode | None
    task_assessments: tuple[TaskAssessment, ...]
    metrics: CandidateMetrics | None
    missing_evidence: tuple[str, ...]

class ExperimentView(BaseModel):
    id: Id
    kind: ExperimentKind
    investigation_id: Id | None
    declared_treatment: str
    context_hash: Sha256
    workloads: tuple[FrozenWorkloadView, ...]
    candidates: tuple[CandidateRef, ...]
    trials: tuple[TrialView, ...]
    outcome: ComparisonOutcome | None

class SelectionView(BaseModel):
    id: Id
    kind: Literal["STARTER_BASELINE", "LEARNER_CHOICE"]
    selected_version_id: Id
    selected_content_hash: Sha256
    comparison_id: Id | None
    retained_alternative_version_id: Id | None
    rationale: str
    state: Literal["VALID", "INVALIDATED"]
    created_at: datetime

class RunView(BaseModel):
    id: Id
    artifact_version_id: Id
    purpose: RunPurpose
    evidence_mode: EvidenceMode
    context_hash: Sha256 | None
    experiment_id: Id | None
    selection_id: Id | None
    state: RunState
    failure_kind: ExecutorFailure | None
    started_at: datetime
    ended_at: datetime | None

class BoardView(BaseModel):
    engagement_slug: Slug
    shift: ShiftView | None
    operating_status: Literal[
        "NEEDS_FIRST_CHOICE", "STARTER_BASELINE", "SELECTED", "INVALIDATED"
    ]
    draft_base_version_id: Id | None
    latest_saved_version_id: Id | None
    operating_selection: SelectionView | None
    latest_experiment_id: Id | None
    incidents: tuple[IncidentView, ...]
    unresolved_limits: tuple[str, ...]
    ledger_totals: dict[str, int]
    chain_status: Literal["VALID"]
    synthetic: Literal[True]
```

Extend the existing `ShiftView` with the immutable
`opening_mode: ShiftOpeningMode | None` (`None` means a historical v5 shift) and
derived `operation_allowed: bool`. A requalification shift keeps its opening
mode for audit after choice; its operation permission changes only when the
selection transaction appends and revalidates a valid first choice. The board
never projects a draft, legacy version or absent selection as the operating
selection. Workload views expose IDs, hashes and counts, not future request bytes
or protected variants. Completed run views may expose the requests actually sent.

Public projections may expose learner-owned source through `ArtifactSourceView` but
never `storage_ref`, host paths, protected IDs, protected texts, provider credentials,
capabilities or raw provider headers. `expected_ref`, if retained, is only the
existing `sealed:` digest. Every new JSON/error/log surface passes the same recursive
allowlist and leak scanner. Client text renders with text nodes, never executable HTML.

### 3.8 Curation, offline only

```python
class MissionSourceState(StrEnum):
    QUARANTINED = "QUARANTINED"
    VERIFIED = "VERIFIED"
    FROZEN = "FROZEN"
    REJECTED = "REJECTED"

class MissionSource(BaseModel):
    id: Id
    source_url: str
    official_domain: str
    fetched_at: datetime
    content_hash: Sha256
    state: MissionSourceState
    human_verifier: str | None
    frozen_fixture_ref: str | None
    tavily_provenance_json: dict[str, JsonValue] | None

def discover(queries: Sequence[str]) -> tuple[MissionSource, ...]: ...
def verify(source_id: Id, human_verifier: str) -> MissionSource: ...
def freeze(source_id: Id, fixture_ref: str) -> MissionSource: ...
def adjudicate_ablation(manifest, outcomes) -> Literal[
    "KEEP_TAVILY_CLAIM", "DROP_TAVILY_CLAIM"
]: ...
```

Curation is an operator CLI. It is not imported by `app.py`, does not answer
customer requests, cannot load protected assessment and cannot decide pass/fail.
Retrieved text is quarantined data, never executable instructions. The historical
pre-registered ablation thresholds remain unchanged until Gate 4 reconciliation.

## 4. Storage and migration

Schema version becomes 6. `migrations/v6.sql` runs with `BEGIN IMMEDIATE`; the
version marker changes only in the same successful transaction.

### New tables

| Table | Required constraints |
| --- | --- |
| `investigations` | Append-only; `revision_of_id` references the same shift; source run/request must exist. |
| `execution_contexts` | Immutable `content_hash UNIQUE`; reviewed mission bytes/hash plus exact public and request-spec bytes retained for one or three ordered `FrozenWorkload` records; protected reservation remains an internal ref. |
| `experiments` | `client_request_id UNIQUE`; exactly one or two candidates according to kind; immutable after reservation except terminal state. `investigation_id` may be null only for one public bootstrap diagnostic in a `LEGACY_FIRST_CHOICE` shift with no owned source run. |
| `trial_slots` | `UNIQUE(experiment_id, pair_ordinal, candidate_label)` and `UNIQUE(run_id)` when assigned; each slot pins a workload ID, request-batch hash and parsed request count matching its context. |
| `exposure_reservations` | One comparison or operation scope; invalidation is a state change, never deletion. |
| `exposure_items` | `UNIQUE(engagement_slug, family, cycle, variant_ref)`; one item can bind both candidate slots in the same pair only. |
| `execution_observations` | Append-only; `UNIQUE(run_id, request_ordinal, ordinal)`; raw ref internal, public payload sanitized. |
| `run_assessments` | One immutable row per terminal assessed run with context hash, completeness, mandatory result and rule version. |
| `task_assessments` | `UNIQUE(run_id, request_ordinal, task_id)`; request identity, exact outcome and reason codes, never model-authored grading. |
| `operating_selections` | `client_request_id UNIQUE`; immutable decision fields; only `VALID` to `INVALIDATED` may mutate. |
| `assist_events` | Append-only except one nullable accept/reject decision; separate shift budget. |
| `idempotency_records` | `UNIQUE(scope_id, action, client_request_id)` with request hash and result ref; same key plus different input is a conflict. |

### Existing-table changes

- `shifts` gains nullable immutable `opening_mode`; old v5 rows remain `NULL`.
  New standard and first-choice shifts record `STANDARD` or
  `LEGACY_FIRST_CHOICE`. Operation permission is derived from the latest valid
  selection, never stored as inferred consent.
- `draft_artifacts` gains nullable `base_version_id` and `restored_from_id`.
- `artifact_versions` gains `restored_from_id` and `authorship_json`.
- `runs` gains `purpose`, `evidence_mode`, `context_id`, `experiment_id`,
  `trial_slot_id`, `selection_id` and `client_request_id`.
- `rotation_draws` remains byte-preserved legacy exposure evidence. New pivot
  reservations use `exposure_reservations` and `exposure_items`; policy reads both.

### v5 migration rules

1. Copy no row and rewrite no blob, hash, event, incident, output or draw.
2. Existing runs become `LEGACY_OPERATION`. Recorded adapters become
   `RECORDED_INSPECTION`; local-process rows become `TRUSTED_LOCAL`; the historical
   `tokenfactory` label remains the label already stored and gains no new claim.
3. New context, experiment, trial and selection references remain null for legacy
   rows. Missing historical inputs remain unknown.
4. Existing Bellwether and Northline engagements receive no learner selection,
   starter baseline or operating pointer. A closed v5 shift has `opening_mode=NULL`;
   the next shift may open in `LEGACY_FIRST_CHOICE` mode for investigation,
   candidate work and comparison. Pivot operation and selected-contract close are
   blocked until a qualifying comparison and explicit valid choice in that shift.
5. A newly seeded engagement may append one labelled `STARTER_BASELINE` selection.
   This is not eligible repair evidence and cannot resolve an incident.
6. Re-running migration is a no-op. A failure leaves `user_version=5` and all old
   bytes readable by the old build.

## 5. Final API surface

Every mutating POST requires a stable `client_request_id` in its body or the
`Idempotency-Key` header where the body is empty. Reusing a key with different
content returns 409. Reusing it with identical content returns the original result.

| Route | Verb | Request to response | Rules |
| --- | --- | --- | --- |
| `/api/engagements/{slug}/board` | GET | none to `BoardView` | Separates latest saved, selected and latest experiment; a legacy no-choice engagement says `NEEDS_FIRST_CHOICE`. |
| `/api/engagements/{slug}/shifts` | POST | key to `ShiftView` | For a reviewed newly seeded engagement with no shift, atomically open a standard initial shift with its own immutable starter and labelled `STARTER_BASELINE`; Northline's starter is the blank scaffold. With a valid prior selection, inherit it. With a closed v5 shift and no selection, open one non-operational first-choice shift. Caller cannot choose mode. Existing open shift or invalid selection returns 409. |
| `/api/shifts/{id}/artifact` | GET/PUT | existing draft models | Save never selects. |
| `/api/shifts/{id}/artifact/restorations` | POST | version ID + key to `DraftView` | Restores owned exact source and records ancestry. |
| `/api/shifts/{id}/artifact/versions` | POST | frozen contract/authorship disclosure to `ArtifactVersionView` | New evidence required after any content change. |
| `/api/artifact-versions/{id}` | GET | none to `ArtifactSourceView` | Learner-owned safe logical files only. |
| `/api/shifts/{id}/investigations` | POST | cause/falsifier/test to `InvestigationView` | Append original or explicit revision. |
| `/api/investigations/{id}` | GET | none to `InvestigationView` | Includes links, not assistant-authored cause. |
| `/api/shifts/{id}/experiments` | POST | `ExperimentRequest` to `ExperimentView` (202) | First-choice shifts may compare. Only a no-source-run `LEGACY_FIRST_CHOICE` shift may start one public bootstrap diagnostic with null investigation; it consumes the ordinary diagnostic budget, creates no eligibility and cannot grant help. A qualifying comparison still requires an investigation. The controller freezes three reviewed workload bytes/hashes/counts and all A/B slot bindings before protected results; queues execution. |
| `/api/experiments/{id}` | GET | none to `ExperimentView` | Shows every slot, missing evidence, drift and eligibility. |
| `/api/shifts/{id}/selections` | POST | `SelectionRequest` to `SelectionView` (201) | Atomic revalidation and append; a first valid choice lifts a legacy shift's operation block without changing its historical opening mode. |
| `/api/engagements/{slug}/selections` | GET | none to `SelectionView[]` | History includes invalidated choices, never fallback. |
| `/api/shifts/{id}/runs` | POST | key to `RunView` (202) | Operation only; exact latest valid selection or the separately labelled new-engagement starter. No operation from a migrated no-choice shift; no candidate ID in request. |
| `/api/runs/{id}` | GET | none to `RunView` | Purpose and evidence mode are always visible. |
| `/api/runs/{id}/outputs` | GET | none to existing extended output views | Exact captures plus safe observations/provenance. |
| `/api/runs/{id}/checks` | GET | none to existing check views | No protected identity/text. |
| `/api/shifts/{id}/close` | POST | key to `ShiftView` | Uses selected contract; refuses nonterminal work and legacy first-choice shifts without a valid explicit selection. |
| `/api/shifts/{id}/assist` | POST | `AssistRequest` to public assist reply | Requires investigation for all diagnostic roles. |
| `/api/assist-events/{id}/decision` | POST | `AssistDecision` to safe assist view | Attribution only. |
| `/api/engagements/{slug}/ledger` | GET | none to existing `LedgerView` | Operational history only. |
| `/api/incidents/{id}` | GET | none to existing extended `IncidentView` | Original operation and selected resolving version remain linked. |

409 is used for state, budget, idempotency, incomplete evidence and invalid-selection
conflicts. 404 is used only for absent public resources. 422 is schema validation.
503 is a trusted executor/gateway availability failure and never a task verdict.

## 6. Call stacks and transactions

### 6.0 Open a legacy first-choice shift

`routes.open_shift -> BEGIN IMMEDIATE -> load latest shift and latest explicit
selection -> if latest is a closed v5 row and no selection exists, insert a new
LEGACY_FIRST_CHOICE shift and an editable draft based on the last owned immutable
version (or this engagement's approved initial draft) -> commit -> ShiftView`.

This branch has no caller-supplied mode. It does not create a selection, run,
experiment, ledger event, incident transition or new v5 history row. Board reads
return `NEEDS_FIRST_CHOICE`, historical captures and a null operating selection.
The shift may investigate, freeze and compare, including an investigation linked
to an owned request in the closed shift. The first selection requires
`expected_prior_selection_id=None`; in the same transaction it makes operation
permissible for that exact valid version. Run start and selected-contract close
return 409 before then, including after a save, freeze, diagnostic pass or
incomplete comparison. An invalidated first choice blocks operation without
falling back to the legacy draft or a new-engagement starter.

If the closed v5 history contains no owned source run/request, the learner first
freezes the seeded editable draft and may reserve exactly one public bootstrap
`DIAGNOSTIC` experiment with `investigation_id=None`. It consumes one of the two
diagnostic slots, uses no protected cases, cannot establish eligibility, cannot
create business consequences and does not unlock diagnostic help. Its captured
request/run supplies an owned source for the learner's cause, falsifier and public
test. A missing source, exhausted budget or failed bootstrap leaves the shift
non-operational; no automatic retry, starter selection or exposure refund occurs.
This exception is not available to ordinary or already evidenced shifts and
does not permit a qualifying comparison without an investigation.

For this one bootstrap, orchestration selects the engagement's separately
reviewed initial incident request, mission and public starting state. It freezes
that request's exact bytes/hash, public task spec, mission bytes/hash and state in
a one-workload `ExecutionContext`; the caller cannot supply a path or substitute
another engagement's request. Missing review or compatible catalog blocks
reservation. The frozen draft may contain arbitrary learner code: execute it
only after the isolated live adapter passes section 8. `TRUSTED_LOCAL` and
`RECORDED_INSPECTION` cannot create the missing run. The bootstrap's
public `ExperimentView` shows `investigation_id=null` and no eligibility.
No bootstrap is reserved while the required safe executor is unavailable.

Only one qualifying comparison is reserved in that shift. Missing or failed
slots keep it non-operational and retain exposure; no automatic retake, new
shift, refund or administrative choice exists in this design. A later retake
requires an explicit Gate 2/3 policy revision with exposure capacity reviewed
before implementation. This is a bounded fail-closed recovery rule, not consent.

### 6.1 Investigate

`routes.create_investigation -> orchestrator.append_investigation -> require owned
source run/request -> validate nonblank bounded fields -> repo.insert_investigation
-> commit -> InvestigationView`.

A revision points to its prior entry. Nothing updates the old explanation. Assist
authorization reads the latest complete learner-authored revision but retains the
original in the public history.

### 6.2 Freeze candidates

`routes.freeze_version -> orchestrator.freeze_version -> resolve draft base and
catalog -> validate contract -> snapshot authorship disclosure -> artifact hash ->
repo.insert_version(parent_id=actual base) -> commit`.

Restoring candidate A after candidate B sets the draft base to A. Freeze does not
change selection, experiments, incidents or the ledger.

### 6.3 Create a qualifying comparison

`routes.create_experiment -> BEGIN IMMEDIATE -> require open shift + investigation
-> load exact A/B versions -> reject equal content hashes -> validate shared current
requirements -> select the controller-owned reviewed comparison manifest by the
engagement slug, never by caller input -> load that engagement's three reviewed
workload files in ordinal order -> verify the reviewed ordinal/hash/count/task-spec
manifest -> validate and capture each batch's exact bytes, hash, public task-spec
bytes/hash and parsed request count -> capture the engagement's reviewed mission
bytes/hash and freeze the other public context inputs -> reserve three
unexposed protected variants per enabled family -> finish and hash the
ExecutionContext with the internal reservation ID -> create six TrialSlots with
pair 1 bound to workload 1, pair 2 to workload 2 and pair 3 to workload 3, each
with one A and one B slot sharing that workload ID/hash/count and protected pair
refs -> insert experiment/context/reservation/slots -> commit -> queue
execute_experiment`.

| Pair | Bellwether reviewed source | Northline reviewed source | Slots bound to the same frozen bytes/hash/count/task spec |
| --- | --- | --- | --- |
| 1 | `bookshop_compare_pair_01.jsonl` | `northline_compare_pair_01.jsonl` | 1/A and 1/B |
| 2 | `bookshop_compare_pair_02.jsonl` | `northline_compare_pair_02.jsonl` | 2/A and 2/B |
| 3 | `bookshop_compare_pair_03.jsonl` | `northline_compare_pair_03.jsonl` | 3/A and 3/B |

The controller selects only the manifest belonging to the shift's engagement.
Missing review, cross-engagement fallback or a Bellwether source in a Northline
context fails before exposure reservation. The bytes, hashes, task-spec hashes
and request counts are checked against that independently reviewed manifest;
no value is invented in this document. The resulting context and slot records,
not these pathnames, govern execution and replay.

Pair 1 runs A then B, pair 2 runs B then A, and pair 3 order is derived before any
result from the low bit of a decision hash over the context hash and the two candidate
content hashes. The experiment content hash is computed after that schedule is fixed.
The stored order is the authority. It is not changed after a failure. Candidate code,
settings or context drift creates `NOT_COMPARABLE`, never an automatic rerun.
The slot binding, not a mutable fixture pathname or executor-selected batch,
determines the requests sent. The same exact bytes are reconstructed for both
members of a pair. A slot with a mismatched hash/count or a request omitted from
the frozen batch fails closed. Each candidate's denominator is the sum of the
three pair request counts, including failed and missing responses.

Diagnostic experiments use one candidate, public tests only and one trial. They
cannot reserve protected cases or produce eligibility. The only null-investigation
exception is the single public source bootstrap in section 6.0; all other
diagnostics and every comparison require an owned investigation. That exception
uses its pinned initial incident request and public task spec as the test input;
it does not infer a test from an absent investigation.

### 6.4 Execute and finalize an experimental trial

`execute_experiment -> for each stored TrialSlot in execution order -> create fresh
workspace -> resolve only that slot's frozen workload from the context -> verify
the pinned bytes/hash/count -> bind exact candidate/workload/shared state/grant ->
stream only each current permitted request -> adapter.execute -> append raw
outputs and trusted observations -> pure evaluator -> BEGIN IMMEDIATE -> verify
purpose EXPERIMENT and slot identity -> insert assessment -> terminalize run/slot
-> commit`.

After every slot is terminal, `comparison.compare` derives status, metrics and
eligibility from all six slots. This transaction has no import or call path to the
ledger reducer, incident mutators, selection writes or close logic.

### 6.5 Select

`routes.create_selection -> BEGIN IMMEDIATE -> require open shift and expected prior
selection -> load completed comparison -> recompute comparison outcome from stored
inputs -> require chosen exact version eligible + non-invalidated exposure + current
requirements hash -> append OperatingSelection with retained alternative -> derive
operation permission from that valid selection -> commit`.

The latest explicit selection is authoritative even if invalidated later. Operation
blocks on that invalid choice and never falls back to an older valid selection.

### 6.6 Operate and finalize consequences

`routes.start_run -> BEGIN IMMEDIATE -> require latest selection VALID -> require no
in-flight operation -> bind selected exact version, current conditions, requirements
and starting business state, including reviewed mission bytes/hash -> reserve
separate operational exposure -> insert Run
purpose OPERATION -> commit -> execute_run`.

`execute_run -> adapter.execute -> append captures/observations -> evaluator.evaluate
-> require OperationalAssessment -> BEGIN IMMEDIATE -> recheck selection, context,
exposure and idempotency -> insert checks -> reducer.reduce -> chain.append -> insert
events -> open/resolve incidents -> terminalize run -> commit`.

Evaluation and reduction use the captured mission from that run's context; neither
re-reads a mutable mission pathname or today's engagement rules at finalization.

No experimental assessment can construct `OperationalAssessment`. The reducer also
checks purpose at runtime. Incident resolution requires a passing operational check
against the pinned incident rule and the exact selected version.

### 6.7 Close and inherit

`routes.close_shift -> BEGIN IMMEDIATE -> require no nonterminal work -> load latest
explicit selection and selected contract -> require selection VALID -> reduce_close
for declared limits only -> append chain -> mark unresolved incidents closed-unresolved
-> close shift -> commit`.

`open_next_shift -> if a reviewed newly seeded engagement has no shift, atomically
insert its STANDARD initial shift, immutable starter version and labelled
STARTER_BASELINE; otherwise load latest explicit selection -> if latest is a closed
v5 no-choice shift, use section 6.0; otherwise block if absent/invalid -> copy
selected source to draft with base_version_id -> project rationale, retained
alternative, tests, incidents and limits -> insert next shift -> commit`.
The initial branch never applies to an existing v5 engagement.

Later testing of the retained alternative creates a new experiment with the observed
later condition. It does not update the earlier selection, operation or ledger. A
subsequent change of operating version requires another explicit qualifying selection.

### 6.8 Restart and replay

Startup marks interrupted runs and trial slots failed, retains outputs, observations,
usage and exposure, and performs no retry. A comparison with any failed slot remains
incomplete. A failed operation writes no invented consequence.

`replay_assessment` loads the exact captured context, including mission bytes/hash,
outputs, rule versions and protected refs, re-runs pure assessment/reduction in
memory and returns differences. It never reads the current mission file or
current engagement rules in place of the capture.
It writes nothing. Legacy runs missing required context return
`UNKNOWN_MISSING_INPUTS`. `chain.verify_chain` remains a separate byte-integrity
check; neither proof substitutes for the other.

### 6.9 Northline transfer ownership

Startup asks orchestration to idempotently seed a Northline engagement and its
one-hint config only after an operator has reviewed its mission, initial and
three paired public request files, ordinal manifest, starting state, catalog, blank
scaffold and protected inventory. The existing `repo.seed_engagement` and
`repo.seed_engagement_config` calls are used with Northline values; no public
engagement-creation route or caller-selected fixture is added. Missing review
leaves Northline unavailable while Bellwether remains usable. If a previously
seeded Northline package later goes missing or changes, new execution fails
closed without rewriting its history. Only orchestration checks the sealed
inventory; startup and persistence do not import the sealed loader. Existing
v5 Northline engagements keep the no-choice migration path and never receive
a new `STARTER_BASELINE` from this seed step.

For that newly seeded engagement only, its first
`/api/engagements/northline/shifts` call atomically creates a standard shift,
immutable blank starter version and labelled `STARTER_BASELINE` selection. An
engagement that arrived through v5 migration takes the section 6.0 first-choice
branch instead and receives no starter.
The scaffold has no solution code and is not eligible repair evidence. Run that
starter once against the reviewed initial request to capture a task-relevant
failure; the learner then records a cause, falsifier and public test against
that source run. Edit and freeze two distinct learner-owned
versions, compare them in six A/B slots using only Northline's reviewed batches
and protected reservation, then explicitly select an eligible exact version with
`expected_prior_selection_id` set to the labelled starter selection's ID.
No diagnostic trial or experimental pass selects it or writes business history.
The starter's one successful operational finalization uses that shift's operation
allowance; close and open the next shift before operating the chosen version.
The next shift inherits only the explicit choice, not the latest saved source.
Only operational runs of the labelled starter or later exact learner selection
may derive Northline's deterministic synthetic booking, commitment and
escalation consequences. Experiments cannot.

The Northline away shift uses its own reviewed mission, public requests, starting
state and compatible contract catalog, not Bellwether source or inventory. No
catalog version is assigned here. Orchestration owns the sealed-case loader and
passes approved protected cases as explicit inputs to the pure evaluator.
Reduced assistance remains controller policy; learner code owns the response
and retry-safe behavior. A human, blinded to study condition, owns the learning-
transfer rubric in section 10; service output or a model never grades that
rubric. Missing mission, request, state, catalog, manifest or sealed review
blocks execution and any transfer claim.

## 7. Budgets and fixed limits

These are product ceilings, not measured vendor performance.

| Limit | Value | Enforcement |
| --- | --- | --- |
| Diagnostic public experiments per shift | 2 | Reserved durably; no protected cases; failures consume the slot. A no-source-run legacy bootstrap consumes one and cannot be repeated automatically. |
| Qualifying comparisons per shift | 1 | Two candidates x three pairs = six trial slots. |
| Protected variants consumed per family/comparison | 3 | One variant per pair shared by A/B; minimum inventory is 6 variants per family per cycle. |
| Unplanned comparison retries | 0 | Any missing/failed slot makes evidence incomplete; create a new shift/comparison only under a new reservation. |
| Operational reservations per shift | 2 maximum | Second allowed only when the first failed with zero accepted customer outputs and zero reducer writes; same selection/context only. |
| Successful operational finalizations per shift | 1 | Unique database constraint. |
| Service inference calls per customer request | 1 maximum | Zero is valid when ordinary code handles the request. |
| Customer requests per trial | 4 maximum | Exact denominator is frozen in context. |
| Gateway input per call | 8 KiB UTF-8 | Reject before provider call. |
| Gateway output per call | 1,024 tokens | Provider request and local guard. |
| Gateway deadline per call | 20 seconds | Trusted gateway measurement. |
| Assist model calls per shift | 3 | Shared across hint, diagnosis and patch proposal; one patch proposal maximum. |
| Public learner text fields | 2,000 Unicode scalar values each | API validation before storage/model use. |

The live capability spike must measure whether these ceilings are feasible with the
available model and sandbox. Unknown usage and cost are displayed as unknown. A
model, image or provider setting change invalidates comparability unless it is the
declared treatment and both candidates receive the corresponding approved plan.

Configuration names:

```text
SHIFTWORK_DB_PATH
SHIFTWORK_EXECUTOR_ADAPTER
SHIFTWORK_SERVICE_MODEL
SHIFTWORK_ASSIST_MODEL
SHIFTWORK_TOKEN_FACTORY_IMAGE
SHIFTWORK_GATEWAY_AUDIENCE
NEBIUS_API_KEY
NEBIUS_PROJECT_ID
TAVILY_API_KEY
```

`NEBIUS_API_KEY` is the IAM token (the Sandboxes client also accepts `CONTREE_TOKEN`),
and `NEBIUS_PROJECT_ID` is sent as the `Project` header (client aliases
`CONTREE_PROJECT` and `NEBIUS_AI_PROJECT`).

Secret values never enter repository config, prompts, sandboxes, captures or public
errors. There is no `SHIFTWORK_LEARNER_INFERENCE_KEY`.

Bellwether allows the three assist roles within its shared budget. Northline allows
one `HINT` call and no `DIAGNOSIS` or `PATCH_PROPOSAL`; the API enforces that reduced
configuration even if a client submits a hidden role value.

## 8. Failure, invalidation and trust boundaries

- Provisioning, transport and gateway failures are evidence failures, not customer
  task failures and not synthetic business consequences.
- A service refusal is assessed only when a valid service response was actually
  captured. A timeout cannot be relabelled as a justified refusal.
- Partial experimental captures stay visible and block completeness. They are never
  removed from the denominator.
- Suspected protected-case leakage invalidates the whole reservation and every
  dependent comparison for future selection. It preserves old rows and ledger bytes.
- An invalidated current selection blocks operation. No prior selection is substituted.
- Experimental and operational finalization use distinct functions and transactions.
- One in-flight operation per engagement is enforced by a database constraint, not
  only an application check.
- Raw evidence is written before derived projections. Public views fail closed if
  allowlist or leak scanning fails.
- A Sandbox outer `SUCCESS` does not prove that the inner process succeeded or
  that a saved file contains its reported bytes. For every required file-backed
  capture, read back the checkpoint file and record the actual byte count and
  digest. Compare with trusted expected bytes when the manifest defines them;
  otherwise validate required content and request count against the frozen
  workload manifest. A zero-byte readback cannot satisfy a required nonempty
  capture. Never accept a process's claim about file content as readback proof.
  Missing files, failed readback, wrong bytes and missing required content remain
  visible as incomplete evidence and cannot be repaired by reusing stdout,
  granting a free retry or omitting the slot.
- Recorded inspection and trusted-local fixtures can prove state-machine behavior
  and deterministic policy only. They cannot establish arbitrary learner-code
  isolation, fresh AI behavior, vendor availability or prize qualification.

The separately authorized capability spike must falsify the live design if any of
these probes succeeds:

1. Learner code reads the provider credential, controller database, host filesystem,
   protected fixture or another run's grant.
2. A grant calls another model, exceeds call/token/byte/deadline limits, survives run
   termination or reaches an arbitrary URL/controller route.
3. A prompt, output, normal log or error response exposes a grant, provider header,
   protected text, protected identity or host path.
4. A crash loses completed captures/usage or permits an unpaid retry without a new
   durable reservation.
5. Trial reset leaves candidate-visible cache, booking or process state from the
   other candidate.
6. A required checkpoint file is absent, unreadable, empty when content is
   required, or differs from its trusted expected bytes while the outer operation
   reports success.

Any success is a stop condition for live learner-code execution. Do not fall back to
provider-key injection or arbitrary `local_process` execution.

## 9. Clause-level test plan

Every guard below needs a focused assertion and one valid behavior-changing mutation
that fails at the named assertion. Parse, import, fixture or incidental crashes do
not count as proof.

### Storage and migration

1. `test_v5_to_v6_preserves_every_legacy_blob_hash_and_row_count` snapshots old
   serialized bytes before migration and requires byte identity afterward,
   including the closed shift used to bootstrap first-choice work.
2. `test_v5_migration_creates_no_experiment_or_selection` rejects invented consent;
   on a migrated closed v5 engagement, open a labelled first-choice shift and
   assert null selection/operating pointer, preserved old bytes, and 409 for
   operation and selected-contract close. Faults that insert a starter choice,
   copy the latest draft into an operating pointer, or reject shift-open must
   each fail at a named assertion. For a closed no-run v5 shift, one budgeted
   public bootstrap diagnostic, after safe execution is available, yields an
   owned source for investigation but still no selection, eligibility or
   operation. Its response has `investigation_id=null`; a missing or
   cross-engagement initial request fails before reservation. A fault that permits a
   comparison without investigation must fail. A normal new engagement keeps
   its separately labelled starter path.
3. `test_v6_migration_is_atomic_and_idempotent` injects a mid-migration fault and
   requires `user_version=5`, then succeeds once and no-ops on rerun.
4. `test_unknown_schema_version_fails_closed` prevents destructive guessing.

### Investigation and assistance

5. `test_diagnostic_help_requires_cause_falsifier_and_public_test` fails each field
   independently and permits deterministic orientation only.
6. `test_investigation_revision_preserves_original` requires both rows and linkage.
7. `test_assist_budget_is_shared_and_patch_is_capped_once` exercises mixed roles.
8. `test_assist_cannot_edit_freeze_grade_select_or_read_protected_material` probes
   imports, calls and every serialized response/error surface.

### Task envelope and evaluator

9. `test_true_price_without_collection_or_alternative_fails_required_tasks` covers
   the approved Bellwether example and the reviewed executable starter plus
   incident request/public state. A fixture swap to the old stock-only repair
   arc or a stubbed success must fail the requested-task assertion; a recorded
   transcript alone cannot satisfy the executable-starter obligation.
10. `test_wrong_entity_supported_claim_fails` distinguishes truth from relevance.
11. `test_blanket_refusal_is_not_useful_completion` keeps refusal and blanket
   clarification separate from useful completion; change a required answer into
   an unneeded `NEEDS_CLARIFICATION` and require an assessment failure.
12. `test_justified_refusal_and_referral_are_distinct` also proves justified and
   unjustified clarification are two distinct outcomes under frozen public task
   rules. Mutating the assessor to count a justified clarification as completion
   or as a referral must fail its exact outcome and mandatory-rule assertions.
13. `test_missing_capture_is_missing_evidence_not_refusal` also forbids a timeout
   or absent response from being assessed as clarification.
14. `test_customer_text_is_derived_only_from_validated_envelope` injects contradictory
   prose and requires rejection.
15. `test_evaluator_is_pure_and_loader_is_orchestration_only` covers imports, runtime
   importer sets, filesystem, DB, network and model calls.

### Experiment reservation and fairness

16. `test_comparison_freezes_both_candidates_context_and_all_six_slots_before_results`
   faults after each write and requires all-or-nothing reservation. It freezes
   exactly three reviewed request batches with raw bytes, parsed counts and
   request-spec hashes before any result; a mutable-path substitution or missing
   workload must fail a content assertion for either engagement. The controller
   chooses the reviewed manifest by engagement, never from caller input.
17. `test_each_pair_shares_workload_and_resets_state` compares raw bytes, hashes,
   request counts, task-spec hashes and protected pair refs for A/B in each of
   pairs 1 to 3 against independently pinned reviewed files, plus sentinel
   state for both Bellwether and Northline. Pair 1 maps to that engagement's
   file 01, pair 2 to file 02 and pair 3 to file 03;
   swapping whole pair assignments, swapping only pair 2's B batch or count,
   dropping a request, substituting Bellwether files/manifest in Northline, or
   leaking cache/booking state must each fail a named assertion against the
   frozen context.
18. `test_predeclared_order_cannot_change_after_first_result` mutates order ownership.
19. `test_candidate_or_context_drift_is_not_comparable` mutates every context field
   separately, including frozen mission bytes/hash, model settings, requirements
   and starting state.
20. `test_failed_or_missing_slot_blocks_completion_without_refund` covers all six slots.
21. `test_diagnostic_experiment_cannot_reserve_protected_cases_or_be_eligible` proves
   the public-test boundary. Its no-source legacy bootstrap has null
   investigation only once, consumes a diagnostic slot and cannot release
   protected material, open assist access, write business state or qualify a
   version; ordinary and repeated null-investigation requests fail. The POST and
   GET projections preserve the null investigation ID without validation error.
22. `test_recorded_inspection_cannot_supply_fresh_eligibility` rejects replay labels.
23. `test_metrics_share_one_denominator_and_unknown_is_not_zero` mutates denominator,
   missing output, usage and cost independently. It also asserts per-candidate
   denominator equals the sum of all three frozen workload request counts and
   that justified/unjustified clarification each has a separate reported count;
   merging either with useful completion, refusal or referral must fail. A
   multi-task request retains distinct `(request_ordinal, task_id)` assessments;
   useful completion requires every required task while non-completion incidence
   categories may overlap and are labelled non-additive.
24. `test_mandatory_failure_blocks_candidate_before_efficiency_comparison` proves no
   aggregate score can conceal the failure.

### Selection, operation and inheritance

25. `test_selection_requires_exact_eligible_hash_and_expected_prior_selection` covers
   stale browser actions and changed-after-testing code. In a first-choice shift,
   `expected_prior_selection_id=None` plus a complete eligible comparison makes
   the first explicit choice atomically; only then does operation become allowed.
   Mutating that path to select on open/freeze or to leave it blocked after a
   valid choice must fail. In Northline, a labelled blank starter cannot
   promote edited code: only a complete Northline comparison and the learner's
   explicit choice with the starter selection's ID as expected prior may do so.
26. `test_save_freeze_test_and_close_never_select` asserts unchanged selection history
   after each action, including the closed v5 bootstrap and all no-choice
   requalification actions. An incomplete comparison leaves the shift blocked
   with exposure retained and no automatic retake or refund.
27. `test_invalid_latest_selection_blocks_without_fallback` keeps older choices historical.
28. `test_experimental_finalization_cannot_write_ledger_or_incidents` injects a reducer
   call and requires the purpose/type guard to fail for Bellwether and Northline.
29. `test_operational_finalization_is_atomic_and_idempotent` faults at checks, events,
   incidents and terminal state, then retries the same request key. The Northline
   starter failure and subsequent selected-version operation occupy different
   shifts and have distinct, correctly linked synthetic events. Change the current
   mission file after run start but before finalization; checks and events still
   derive from captured mission bytes. A mutable-path reread must fail.
30. `test_operation_uses_selected_version_not_latest_saved_version` saves a newer
   unselected candidate before start.
31. `test_second_operation_is_only_zero_output_retry` covers partial output, existing
   events, different context and changed selection.
32. `test_incident_resolution_requires_operational_selected_regression` rejects an
   experimental pass and a passing unselected version.
33. `test_next_shift_inherits_selection_rationale_alternative_tests_and_limits` checks
   exact IDs and hashes, not counts.
34. `test_later_alternative_experiment_does_not_rewrite_original_history` compares
   all selection, ledger and incident bytes before and after.

### Gateway, isolation and projections

35. `test_gateway_derives_run_from_capability_and_rejects_spoof_expiry_and_reuse`
   attacks each claim independently.
36. `test_gateway_enforces_model_call_byte_token_deadline_and_tool_allowlists` mutates
   one limit at a time. The grant's tool list must equal the controller-frozen
   mission/context policy. An injected `allowed_tool_names` request field must
   return 422 with no gateway call; prompt-instruction override, changed grant
   list, unlisted model proposal and unlisted tool execution each need separate
   named policy assertions before the unapproved tool runs. A mutation that
   accepts a wider learner list must fail the controller-policy assertion.
37. `test_sandbox_cannot_reach_provider_key_controller_host_or_other_run` is required
   against the real isolation class before live execution is accepted.
38. `test_gateway_failure_retains_usage_and_raw_evidence_without_business_effect`
   injects provider and transport failures.
   `test_adapter_checkpoint_readback_blocks_missing_or_wrong_bytes` separately
   injects outer `SUCCESS` with zero-byte and wrong-byte checkpoint readbacks;
   each must fail the readback byte-count/digest check and block slot eligibility.
   The live spike repeats a deterministic artifact with a trusted expected
   digest through a size-capped non-disposable Sandbox run; any mismatch is a
   STOP result. A dynamic required output with no expected digest must still
   pass frozen request-count and content checks.
39. `test_every_public_surface_detects_each_secret_and_protected_needle` first injects
   raw, JSON-escaped and forward-slash path forms into representative serialized data,
   requires scanner detection, then scans success and error responses, logs, events,
   observations and client bootstrap payloads.
40. `test_public_views_expose_safe_source_but_no_internal_locator` checks nested
   fields and requires workload summaries to reveal only ID/hash/count before
   trial execution, never future request bytes or protected pair refs.

### Restart, replay and client

41. `test_restart_fails_interrupted_slots_without_retry_or_refund` covers experiment
   and operation states independently.
42. `test_semantic_replay_uses_original_inputs_and_writes_nothing` mutates current
   fixtures, including the current mission file, and current incident state after
   capture; replay still uses the frozen mission and writes nothing.
43. `test_legacy_replay_reports_unknown_missing_inputs` forbids reconstruction claims.
44. `test_chain_verification_and_semantic_replay_fail_independently` proves neither
   substitutes for the other.
45. `pivot-browser.mjs` exercises the six-station journey with native keyboard and
   touch at representative desktop and 390px mobile viewports, including focus and
   selected-panel reachability. `test_northline_transfer.py` independently refuses
   execution without reviewed Northline mission, initial and three paired public
   requests, ordinal manifest, starting state, compatible catalog and
   orchestration-owned protected inventory. It proves idempotent reviewed seeding,
   a blank `STARTER_BASELINE`, initial failure/investigation, six Northline A/B
   slots, explicit eligible selection and next-shift operation of the exact
   learner-edited version. It rejects a second successful operation in the
   starter's first shift after selection, then permits the selected-version
   operation in the next shift. Fault missing review, Bellwether mission/source or
   manifest substitution, unselected edited operation, implicit choice and
   experimental business writes separately at named assertions. The Northline
   learner artifact starts without solution code. A separate existing v5
   Northline no-run fixture must open a non-operational first-choice shift,
   receive no starter, and bootstrap only from Northline's reviewed initial
   request through the isolated adapter before investigation.
46. `pivot-render-faults.mjs` removes or swaps purpose labels, context hashes, trial
   values, eligibility blockers, selected version, evidence mode and synthetic labels
   one at a time; each named assertion must fail against independently fetched API data.

### Packaging, curation and evidence limits

47. `test_clean_env_install_and_run.py` installs only the approved lock and runs the
   offline pivot demo. Missing live credentials produce a labelled skip, not a pass.
48. `test_ablation.py` retains the historical frozen/polling/Tavily decision and must
   return DROP when any pre-registered threshold is unmet.
49. The capability-spike matrix records exact model/image/settings, trial counts,
   latency, usage, failures and every trust probe. A static PASS or LLM opinion is
   not acceptance evidence.

## 10. Learning and product evidence plan

The service checks above prove software behavior, not learning.

### Formative comprehension

Run five moderated sessions on the working pivot journey before claiming that the
room is understandable. Each participant must identify, without coaching:

- the original customer failure and what remains unexplained;
- their own cause, falsifier and distinguishing test;
- why experiment, selection and operation differ;
- why an ineligible candidate cannot be chosen; and
- why a later alternative experiment does not rewrite history.

Five sessions are a usability probe only. Any repeated confusion in two sessions is
a redesign signal, not a percentage estimate or learning claim.

### Transfer comparison

Primary outcome: independently complete the Northline transfer task without diagnosis
or patch assistance, scored blind to condition. Compare Shiftwork with a strong static
tutorial matched for time, visible requirements, tests and hint budget. Randomize only
after consent and preregister exclusions, rubric and analysis.

Rubric dimensions, each scored 0, 1 or 2 from retained artifacts:

1. Links the failure to request, observed interpretation/tool use and output.
2. States a falsifier and runs a test that can distinguish at least two explanations.
3. Compares exact candidate versions under shared conditions and notices missing/drifted evidence.
4. Rejects mandatory failures before weighing completion, referral, cost and delay.
5. Explains the later result without hindsight-grading the original choice.

Independent completion requires no mandatory dimension at 0 and a total of at least
8 out of 10. Two trained raters score a shared calibration set; disagreements are
retained and adjudicated. Model grading cannot be the primary score.

For planning only, a two-group binary comparison from 50% to 70%, two-sided alpha
0.05 and 80% power needs about 94 analyzable participants per arm by the standard
normal approximation, or about 111 recruited per arm with 15% attrition. The exact
number must be recalculated and preregistered from pilot assumptions before outreach.
That scale is unlikely inside the hackathon. An underpowered pilot may test feasibility
but cannot support the 20 percentage-point learning claim.

Outreach, consent, participant data collection and study execution remain separately
authorized work. No session has run.

## 11. Least confident decisions and no-go criteria

1. **Three comparison pairs.** It shows variation but is not statistical evidence.
   Backtrack if live latency/cost makes six trials infeasible; never replace them with replay.
2. **Structured task envelope.** It makes independent assessment possible but may
   over-constrain learner service design. A prototype must show that it still permits
   two genuinely different repairs.
3. **Controller-mediated inference.** The design is safer than provider-key injection,
   but the actual sandbox channel and network isolation are unverified.
4. **One draft plus immutable versions.** Simpler than branch workspaces, but restoring
   A/B must remain legible and preserve actual ancestry.
5. **Learning study scale.** A defensible confirmatory study is likely too large for
   the hackathon. The product must not imply measured learning from formative sessions.
6. **Curriculum quality.** Current examples are illustrations. If sealed authoring
   cannot produce two defensible repairs without a hidden preferred answer, stop and
   revise the incident before building more screens.
7. **Legacy failed comparison.** One comparison and zero automatic retakes keep
   exposure bounded but may strand a learner after a transport failure. Preserve
   the evidence and stop operation; any retake policy needs a Gate 2/3 backtrack
   with reviewed inventory and budget rather than an invisible reset.
8. **Northline material.** Its mission, catalog, initial request, three paired
   workloads and manifest, starting state and protected cases are not authored
   or reviewed by this document. The file map fixes ownership, not their
   contents or an executable transfer claim.

Hard no-go conditions before dependent live claims:

- any real-isolation or gateway probe in section 8 succeeds;
- a required file-backed capture cannot be read back and validated against its
  frozen manifest, even when the Sandbox operation reports `SUCCESS`;
- the available model cannot perform meaningful in-service interpretation/tool
  selection within the fixed ceilings;
- comparison cost/latency requires replay or hidden dropped trials;
- the evaluator cannot distinguish task completion from a supported but irrelevant fact;
- a closed v5 engagement cannot reach an explicit first choice without an
  invented selection or an operational run before consent;
- any A/B pair executes different request bytes/counts, or a slot takes its
  workload from a mutable path instead of the frozen context;
- Northline seeding bypasses reviewed material, uses a Bellwether manifest or
  operates edited code without its own qualifying comparison and explicit choice;
- learner input can widen a controller-owned gateway tool allowlist, or an
  unlisted model proposal reaches tool execution;
- clarification is counted as useful completion, refusal, referral or missing
  evidence instead of receiving a distinct independent assessment;
- experiment finalization can reach the reducer or incident mutation path;
- invalidated evidence can still be selected or operated;
- the UI cannot make selected version and operational history distinct on desktop
  and mobile; or
- the curriculum has one obviously correct repair rather than a real tradeoff.

Northline transfer also stops before execution if its reviewed mission, initial
and three paired requests, manifest, state, compatible catalog or protected
assessment is missing. This is an unmet prerequisite, not a reason to invent a
catalog version or sealed case.

## 12. Gate boundary

The prior Gate 3 revision was approved, committed and merged locally as
`aedc97f` and `ab5ab9c` without a co-author footer. The user then approved this
scoped Northline correction and authorized committing and pushing it to main,
also without a co-author footer. Gate 3 covers these file responsibilities,
contracts, budgets, transactions, migration rules and test obligations. It does
not approve implementation, installs, credentials, live calls, sealed-case
contents, fixture authoring, outreach, deployment, publication or submission.
That authorization is limited to these documents.

Gate 4 was separately approved on the same date over completed Slices 1 to 9.
Its clause trace maps every numbered obligation above to one prerequisite slice
and keeps the capability spike before any live-dependent implementation or
claim. The old Slice 10 to 17 instructions remain historical. Slice work
proceeds one slice at a time and each slice still needs its own go-ahead.
