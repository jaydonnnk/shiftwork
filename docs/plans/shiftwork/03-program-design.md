# Program Design: Shiftwork — first bookshop engagement (+ away-shift config)

Gate: 3 — Program Design (APPROVED 2026-09-16; BACKTRACKED to in progress 2026-09-17 —
test 33 close-semantics ambiguity and a missing credential-reachability test
specification; RE-APPROVED 2026-09-17). Written 2026-09-15; revised 2026-09-16 and
2026-09-17.
Scope: the approved architecture (`02-architecture.md`) concretized to the file,
type, call-stack, test and configuration level. **No implementation code** — types
and signatures only. Nothing here authorizes implementation; slices start after
Gate 4 approval.

Design stance: the deterministic core is specified against the executor adapter
boundary and is fully testable offline. The real Token Factory sandbox adapter is a
Gate 4 slice gated on the capability spike (§9), which is specified here but **not
run** — Token Factory credentials are not authorized.

## 1. Confirmations of open architecture items

| Architecture item | Decision made here |
|---|---|
| §16.7 — one loopback HTTP service per artifact | **Confirmed.** The learner artifact is exactly one HTTP JSON service on loopback. No other execution surface is supported. |
| Artifact template | Python **stdlib only** (`http.server`). Reason: no runtime package install, because sandbox egress is unverified (architecture §16 item 3). The template scaffolds; the learner owns the code. |
| Structured response contract | Confirmed as a requirement (brief §5, learner decision 3). The service answers with a small JSON envelope (§3.2, `ServiceResponse`): action, typed claims, evidence refs, record age. Deterministic evaluation needs structured claims, not free text. |
| §3 endpoint names | Finalized in §4: same shapes as the architecture, plus shift close, safe assist-event listing and patch accept/reject. |
| §12 env var names | Finalized in §7.3. |
| §18.6 attempt / rotation numbers | §7.1: fresh variant per family per attempt; inventory covers two bookshop shifts. |
| §20 deferred items | File layout §2; types/signatures §3; tests §6; limits/rotation §7.1; reason-code wording §7.2. Gate 4 and separately authorized work remain in §11. |
| New tables beyond architecture §4 | `engagement_config` (away-shift assist/check-family config) and `rotation_draws` (durable exposure record — no in-memory authority across restarts). Everything else matches the §4 table list. |

The six mockups stay the UI source of truth. Free-text visible checks become a
structured builder (§10.2); known limitations stay free text, stored but not evaluated
(§10.11). These mappings do not establish that all UI promises are implemented.
Screen 02's "May: Recommend with a clear label" is fixed scenario copy, not an
editable input; the bookshop client displays it without inventing another learner
choice. The away shift's editable "May estimate when" maps to `may_estimate_when`.

## 2. Files

Repository root gains two trees; nothing existing is modified.

```
shiftwork/
  app.py                 FastAPI factory; lifespan: DB open, ensure_schema, mount client; adapter selection
  config.py              Pinned constants: limits, total assist budgets, reason-code render map, model ids, image ref. No secrets.
  api/
    routes.py            HTTP handlers only; parse/validate, delegate, map typed errors to status codes
    schemas.py           Request/response pydantic models (frozen, extra="forbid")
  domain/
    models.py            Every durable type in §3.2 (pydantic, frozen)
    canonical.py         canonical_bytes() + content_hash(): the ONLY place canonical serialization/hashing exists
    contract_catalog.py  Immutable, versioned contract-option catalogs and evaluator-rule bindings
    customer_answer.py   Deterministic customer-text rendering from validated structured responses
    errors.py            Typed error taxonomy: executor failures, budget, rotation, validation
  store/
    schema.sql           DDL for the architecture §4 tables + engagement_config + rotation_draws
    db.py                Connection factory (one per request/thread), pragmas, ensure_schema (user_version)
    repo.py              Raw parameterized SQL functions, one group per table; rows validated into models
    seed.py              Seeds engagements, request batches, shop snapshots, check templates
  evaluator/
    evaluator.py         Controller-only sealed loader plus pure evaluate(); no network or LLM.
  ledger/
    reducer.py           Pure reduce(...) -> unchained event drafts (§3.4)
    chain.py             Event hash assignment + verify_chain(); used inside the finalization transaction
  executor/
    base.py              ExecutorAdapter Protocol, RunRequest/RunResult, shared capture normalization
    local_process.py     Trusted pinned-fixture subprocess adapter; rejects arbitrary learner code (§3.3)
    recorded.py          Transcript replay adapter: deterministic captures from recorded fixtures
    tokenfactory.py      Real sandbox adapter — lands in Gate 4 after the spike (§9). Same Protocol.
  sealed/
    store.py             Sealed case specs + expected values accessor; rotation draws delegate to rotation.py
    rotation.py          Draw-without-replacement policy, cycle accounting, exhaustion handling
    cases/               Sealed case data (bookshop + bike co-op). Never mounted into a sandbox, never in a prompt.
  assist/
    gateway.py           Bounded Nemotron roles; every call logged; permission checks per engagement config
  curation/
    pipeline.py          Offline Tavily curation CLI (discover → human verify → freeze fixture). Never imported by app.py.
    ablation.py          Three-arm historical-replay protocol and pre-registered Tavily kill thresholds
  orchestrator.py        Shift/run lifecycle; budget enforcement; idempotent finalization; startup reconciliation
  client/                Static HTML/CSS/vanilla JS implementing the six mockups; no framework, no build step
  fixtures/
    catalogs/            Immutable versioned contract catalogs; used versions are never rewritten
    requests/            Fixed request batches, literal bytes, reused verbatim by every adapter
    runs/                Recorded run transcripts used by offline determinism tests
  templates/artifact/    Stdlib-only learner service scaffold (server, response contract, contract file)
tests/                   Mirrors the package layout; shared adapter conformance cases in tests/executor/conformance.py
```

## 3. Types & signatures

No bodies. Pydantic v2 style: domain models `frozen=True, extra="forbid"`.
Ids are opaque strings; timestamps are UTC. `ContractParams` and `ServiceResponse`
mirror what the learner actually authors in screens 02/04/06.

### 3.1 Content addressing

```python
# domain/canonical.py
HASH_VERSION = 1

type Id = str                     # opaque id (uuid4 hex or engagement-prefixed ordinal)
type Slug = str                   # engagement slug
type JsonValue = str | int | bool | None | list[JsonValue] | dict[str, JsonValue]

class ArtifactHashEnvelope(TypedDict):
    hash_version: int
    files_base64: dict[str, str]          # sorted relative path → base64 exact bytes
    contract_json: dict[str, JsonValue]   # ContractParams model dump
    contract_catalog_hash: str

def canonical_bytes(value: JsonValue) -> bytes:
    """Deterministic JSON: sorted keys, compact separators, UTF-8, NFC.
    Floats are rejected — hashed payloads may not contain them."""

def content_hash(value: JsonValue) -> str:
    """sha256 of HASH_VERSION prefix + canonical_bytes(value), hex."""
```

### 3.2 Durable domain models (`domain/models.py`)

```python
class EngagementConfig(BaseModel):      # one row per engagement (new table, §1)
    slug: Slug
    business_kind: Literal["bookshop", "bike_coop"]
    assist_level: AssistLevel            # FULL | REDUCED
    allowed_assist_roles: tuple[AssistRole, ...]
    total_assist_budget_per_shift: int   # every completed model interaction, all roles combined
    enabled_check_families: tuple[str, ...]
    attempt_limit: int
    rotation_group_size: int

class AssistLevel(StrEnum): FULL, REDUCED
class AssistRole(StrEnum): STAKEHOLDER_DIALOGUE, SCAFFOLDING, HINT, DIAGNOSIS, PATCH_PROPOSAL

class ContractDimension(StrEnum):
    MUST_NEVER, STANCE, CLARIFY_WHEN, ESCALATE_WHEN, MAY_ESTIMATE_WHEN, REPEAT_REQUEST_RULE

class ContractOptionId(StrEnum):
    NEVER_INVENT_PRICE_STOCK_POLICY, VERIFY_EXACT_CLAIMS_NOW,
    USE_NEWEST_RECORD_WITH_AGE, HARD_CHECK_HIGH_RISK_ONLY,
    CLARIFY_TITLE_OR_EDITION, CLARIFY_ANY_UNCERTAIN_FACT, CLARIFY_HIGH_RISK_FACT,
    NEVER_UNSAFE_CONTINUATION, ESTIMATE_ONLY_WITH_EVIDENCE,
    ESCALATE_UNSAFE_REPAIR, DEDUPLICATE_BOOKING_BY_REQUEST_ID

class ContractOption(BaseModel):        # immutable once its catalog version has been used
    id: ContractOptionId
    dimension: ContractDimension
    learner_label: str
    evaluator_rule_id: str              # stable deterministic rule; never an LLM instruction

class ContractCatalog(BaseModel):
    engagement_slug: Slug
    version: int
    content_hash: str
    options: tuple[ContractOption, ...]
    frozen_at: datetime

class ContractParams(BaseModel):        # frozen into an ArtifactVersion; drives parameterized checks
    catalog_version: int
    must_never: tuple[ContractOptionId, ...]
    selections: dict[ContractDimension, ContractOptionId]
    response_time_limit_ms: Literal[1000, 3000, 8000]
    declared_limits: tuple[str, ...]    # "known limitation to declare" (free text, stored not evaluated)

class CaseShapeId(StrEnum):
    MISSING_REFRESH_TIME, STALE_STOCK, AMBIGUOUS_TITLE, POLICY_EXCEPTION,
    HOSTILE_CATALOG, FUTURE_COMMITMENT, UNSAFE_REQUEST, RETRIED_BOOKING

class VisibleCheck(BaseModel):          # structured builder realization of the mockup's Given/When/Then
    id: Id
    shift_id: Id
    case_shape: CaseShapeId
    then_expectation: Literal["ANSWER_WITH_EVIDENCE", "ASK", "DECLINE", "ESCALATE"]
    authored_by: Literal["learner"]

class Claim(BaseModel):                 # typed claims the evaluator compares deterministically
    kind: Literal["price", "stock", "availability", "policy_answer", "booking", "none"]
    value: JsonValue                    # exact value as answered (floats forbidden — use integers/minor units)

class ServiceResponse(BaseModel):       # the structured response contract (captured bytes must validate)
    action: Literal["answer", "ask", "decline", "escalate"]
    claims: tuple[Claim, ...]
    evidence_refs: tuple[str, ...]      # refs into the frozen shop snapshot the service consumed
    record_age_ms: int | None           # asserted age; evaluator recomputes it from cited records

class Draft(BaseModel):                 # the single mutable working copy per shift
    shift_id: Id
    files_ref: str
    updated_at: datetime

class AssistanceSummary(BaseModel):     # aggregate snapshot at version freeze; no proposal-to-version links
    total_interactions: int
    interactions_by_role: dict[AssistRole, int]
    patch_proposals: int
    accepted_patch_proposals: int
    learner_declared_generated_patch_use: bool
    captured_through: datetime

class ArtifactVersion(BaseModel):       # immutable, content-hashed snapshot
    id: Id
    shift_id: Id
    parent_id: Id | None
    content_hash: str                   # hash of files + ContractParams + frozen ContractCatalog hash
    storage_ref: str
    contract: ContractParams            # frozen with the version; changing it requires a new version
    contract_catalog_hash: str
    assistance_summary: AssistanceSummary
    created_by: Literal["template", "learner"]

class RunState(StrEnum): QUEUED, RUNNING, CAPTURED, FINALIZED, FAILED

class Run(BaseModel):
    id: Id
    shift_id: Id
    artifact_version_id: Id
    request_batch_ref: Id               # frozen learner-visible stimuli selected for this run
    shop_snapshot_ref: Id
    attempt_number: int                 # 1..attempt_limit, controller-assigned inside start_run
    state: RunState
    adapter: Literal["local_process", "recorded", "tokenfactory"]
    sandbox_ref: str | None
    failure_kind: ExecutorFailure | None
    started_at: datetime
    ended_at: datetime | None

class RunOutput(BaseModel):             # append-only raw capture per request
    id: Id
    run_id: Id
    request_ordinal: int
    http_status: int | None
    body: bytes                         # raw bytes exactly as captured; never pre-parsed
    elapsed_ms: int | None
    transport_error: ExecutorFailure | None
    log_ref: str | None

class ExecutorFailure(StrEnum):         # shared taxonomy — both adapters emit only these
    PROVISION_FAILED, SERVICE_UNREACHABLE, REQUEST_TIMEOUT, CAPTURE_TRUNCATED,
    CAPTURE_NON_UTF8, SANDBOX_TERMINATED, INTERNAL

class CheckDef(BaseModel):
    id: Id
    kind: Literal["invariant", "contract_conformance", "sealed_acceptance", "regression"]
    visibility: Literal["learner", "sealed"]
    family: str
    rotation_group: str | None
    authored_by: Literal["learner", "operator"]
    created_shift_id: Id | None

class ReasonCode(StrEnum):              # §7.2 — the final learner-visible failure vocabulary
    INVENTED_FACT, STALE_BEYOND_RULE, MISSING_EVIDENCE, WRONG_ACTION,
    UNSAFE_CONTINUATION, DUPLICATE_COMMITMENT, LATENCY_BUDGET, MALFORMED_RESPONSE, REGRESSION

class CheckResult(BaseModel):           # append-only
    id: Id
    run_id: Id
    check_id: Id
    verdict: Literal["pass", "fail", "error"]
    observed_ref: str
    expected_ref: str | None            # opaque id into the sealed store; never a renderable value
    reason_code: ReasonCode | None

class LedgerEventType(StrEnum):
    SALE_COMPLETED, REFUND_REQUIRED, BOOKING_COMMITTED, ESCALATION_TO_HUMAN,
    INCIDENT_OPENED, INCIDENT_RESOLVED, BACKLOG_RECORDED, LIMIT_DECLARED

class LedgerEventDraft(BaseModel):      # reducer output; no chain fields yet
    event_type: LedgerEventType
    cause_refs: tuple[str, ...]         # run / output / check_result / incident ids
    payload: dict[str, JsonValue]       # floats forbidden; weights come from mission fixtures
    synthetic: Literal[True] = True     # business consequences are labelled scenario state

class LedgerEvent(LedgerEventDraft):    # after chain.append assigns seq and hashes
    seq: int
    prev_hash: str
    hash: str

class IncidentState(StrEnum): OPEN, RESOLVED, CLOSED_UNRESOLVED

class Incident(BaseModel):
    id: Id                              # e.g. BWB-01 (engagement prefix + ordinal)
    engagement_slug: Slug
    shift_id: Id
    opening_run_id: Id
    failing_output_ref: str
    check_result_id: Id
    reason_code: ReasonCode
    opened_event_seq: int
    state: IncidentState
    resolving_version_id: Id | None
    resolved_event_seq: int | None

class AssistEvent(BaseModel):
    id: Id
    shift_id: Id
    role: AssistRole
    request_ref: str
    response_ref: str
    model_id: str
    accepted: bool | None               # patch proposals only; null otherwise
    created_at: datetime

class MissionSource(BaseModel):
    id: Id
    url: str
    fetched_at: datetime
    content_hash: str
    tavily_query: str | None
    human_verifier: str | None           # required only after verification
    fixture_ref: str | None              # required only when frozen
    status: Literal["quarantined", "verified", "frozen", "rejected"]

class RotationDraw(BaseModel):          # append-only; durable exposure record (new table, §1)
    id: Id
    engagement_slug: Slug
    family: str
    variant_ref: str                    # opaque; never reusable for this engagement
    run_id: Id
    cycle: int                          # operator-authored inventory generation; never resets exposure history
    drawn_at: datetime

class Shift(BaseModel):
    id: Id
    engagement_slug: Slug
    seq: int
    state: Literal["open", "closed"]
    opened_at: datetime
    closed_at: datetime | None
```

Catalog semantics are immutable within a version. Once any artifact references a
catalog version, its option ids, learner labels and `evaluator_rule_id` bindings cannot
change; a correction creates a new catalog version. The catalog hash and version are
part of the artifact hash envelope. For legitimate tradeoffs, sealed cases check
**consistency with the learner's selected option**, not whether they chose a hidden
"right" option. Fixed invariants (for example, never inventing a factual claim) remain
independent of learner choice. If no option expresses the learner's intent, they may
record it as a free-text declared limitation, but a required executable dimension still
needs a supported option before the artifact can run.

The learner service returns structured fields only. The evaluator treats every field as
untrusted: it resolves evidence refs, recomputes record age and validates claims before
any customer-facing sentence is produced. The controller then renders the displayed
answer deterministically from that validated structure; there is no separately authored
`reply_text` that can contradict the scored claims.

```python
# domain/customer_answer.py
class ValidatedServiceResponse(BaseModel):
    action: Literal["answer", "ask", "decline", "escalate"]
    claims: tuple[Claim, ...]
    evidence_refs: tuple[str, ...]
    verified_record_age_ms: int | None

def validate_service_response(
    response: ServiceResponse,
    public_records: dict[str, JsonValue],
) -> ValidatedServiceResponse: ...

def render_customer_text(response: ValidatedServiceResponse) -> str: ...
```

### 3.3 Executor adapter

```python
# executor/base.py
class ArtifactSnapshotRef(BaseModel):
    files: dict[str, bytes]                  # path -> exact bytes from the frozen version
    manifest_hash: str                       # content_hash of files + contract + catalog hash

class BatchRef(BaseModel):
    path_ref: str                            # literal request batch bytes in fixtures/requests/
    content_hash: str

class InferenceGrant(BaseModel):             # only if the learner service calls inference at runtime
    endpoint: str
    scoped_key_ref: str                      # minted by the controller; never logged
    token_budget: int

class RunRequest(BaseModel):
    artifact_snapshot: ArtifactSnapshotRef   # files + manifest from the frozen version
    request_batch: BatchRef                  # literal bytes, shared by every adapter
    shop_snapshot_ref: str                   # frozen shop data the service may consume
    harness_ref: str
    image_ref: str
    deadline_s: int
    inference_grant: InferenceGrant | None   # provisioning mechanism unverified (architecture §16 item 4)

class RawCapture(BaseModel):
    request_ordinal: int
    http_status: int | None
    body: bytes
    elapsed_ms: int | None
    transport_error: ExecutorFailure | None
    log_ref: str | None

class RunResult(BaseModel):
    captures: tuple[RawCapture, ...]
    executor_ref: str | None                 # sandbox id only for tokenfactory; null for recorded/local
    failure: ExecutorFailure | None
    wall_ms: int

class ExecutorAdapter(Protocol):
    name: str
    async def execute(self, request: RunRequest) -> RunResult: ...

# executor/base.py, shared by every adapter — the only place bytes become captures
def normalize_captures(raw: Iterable[RawCapture], deadline_s: int) -> tuple[RunOutput, ...]: ...
```

Adapter rules (enforced by the conformance suite, §6.G): raw bytes only; identical
typed failure kinds for identical injected faults; nothing reads back from the executor
except captures and logs. `local_process` is restricted to operator-authored test
fixtures whose content hashes are pinned by the test suite; it must reject arbitrary
learner submissions. An empty temporary working directory is **not isolation**: a
subprocess with the same OS account can still access host files and environment.
`recorded` executes nothing and is labelled transcript replay. Neither adapter proves
hostile-code isolation; learner code requires the verified sandbox path.

### 3.4 Evaluator and reducer

```python
# evaluator/evaluator.py
class SealedCase(BaseModel):
    id: Id
    schema_version: Literal[1]
    family: str
    check_id: Id
    request_ordinals: tuple[int, ...]
    expected: dict[str, JsonValue]

class SealedCaseSet(BaseModel):          # loaded controller-side; expected values never render
    cases: tuple[SealedCase, ...]

class MissionFixtures(BaseModel):        # inspectable scenario rules (brief §5: weights must be inspectable)
    weights: dict[str, int]
    transitions: tuple[str, ...]         # symbolic transition rules resolved by the reducer

class CloseShiftFacts(BaseModel):
    shift_id: Id
    declared_limits: tuple[str, ...]
    unresolved_incident_ids: tuple[Id, ...]
    committed_contract: ContractParams

def load_drawn_cases(run_id: Id) -> SealedCaseSet: ...

def evaluate(
    outputs: Sequence[RunOutput],
    check_defs: Sequence[CheckDef],
    visible_checks: Sequence[VisibleCheck],
    sealed_cases: SealedCaseSet,
    contract: ContractParams,
) -> list[CheckResult]: ...

# ledger/reducer.py — pure
def reduce(
    fixtures: MissionFixtures,
    raw_outputs: Sequence[RunOutput],
    check_results: Sequence[CheckResult],
    committed_contract: ContractParams,
) -> list[LedgerEventDraft]: ...

def reduce_close(
    fixtures: MissionFixtures,
    facts: CloseShiftFacts,
) -> list[LedgerEventDraft]: ...
```

The architecture's `reduce(...) -> events` is realized as: the reducer returns
**unchained drafts**; `reduce_close` does the same for shift-close facts without
manufacturing run outputs. `ledger/chain.py` assigns `seq`, `prev_hash`, `hash` inside
the same finalization or close transaction (§5.5, §5.8). Same inputs must replay to
identical drafts and identical hashes.

### 3.5 Ledger chain

```python
# ledger/chain.py
class ChainStatus(StrEnum): VALID, BROKEN

def append(drafts: Sequence[LedgerEventDraft], prev_hash: str, start_seq: int) -> list[LedgerEvent]: ...
def verify_chain(events: Sequence[LedgerEvent]) -> ChainStatus: ...   # runs on every ledger read
```

`BROKEN` aborts the read with a hard error; no unverified events or board counters
are served. `LedgerView.chain_status` is `VALID` on successful responses.

### 3.6 Orchestrator

```python
# orchestrator.py
class DraftFiles(BaseModel):
    files: dict[str, str]                              # allow-listed UTF-8 relative paths → editable text

class FreezeVersionRequest(BaseModel):
    contract: ContractParams
    learner_declared_generated_patch_use: bool         # version-level disclosure; no proposal id linkage

def open_next_shift(slug: Slug) -> Shift: ...                 # seeds from inheritance (§5.1)
def get_draft(shift_id: Id) -> DraftFiles: ...
def save_draft(shift_id: Id, files: DraftFiles) -> Draft: ...
def freeze_version(shift_id: Id, request: FreezeVersionRequest) -> ArtifactVersion: ...   # §5.2
def start_run(shift_id: Id) -> Run: ...                       # budget + rotation enforced here (§5.3)
async def execute_run(run_id: Id) -> None: ...                # background task (§5.4)
def finalize_run(run_id: Id, result: RunResult) -> None: ...  # single transaction (§5.5)
def close_shift(shift_id: Id) -> Shift: ...                   # atomic + idempotent (§5.8)
def reconcile_interrupted() -> None: ...                      # startup recovery (§6.B.9)
```

Startup marks QUEUED, RUNNING and CAPTURED runs FAILED, keeps every completed output
and draw reservation, and emits no checks or events. FINALIZED runs remain unchanged.

### 3.7 Assist gateway

```python
# assist/gateway.py
class AssistRequest(BaseModel):
    role: AssistRole
    message: str

class AssistReply(BaseModel):
    role: AssistRole
    text: str
    proposed_patch: str | None          # sanitized labelled diff; never an internal storage ref
    assist_event_id: Id

class AssistDecision(BaseModel):
    accepted: bool

def assist(shift_id: Id, request: AssistRequest) -> AssistReply: ...
def record_patch_decision(event_id: Id, decision: AssistDecision) -> AssistEvent: ...
    # refuses roles not in the engagement's allowed_assist_roles (away shift: no patch
    # proposals, no scaffolding); atomically reserves one unit from the total shift
    # budget before a model call; refuses sealed refs; logs every call to assist_events
```

There is deliberately no proposal-to-version foreign key. At freeze time the controller
stores the aggregate `AssistanceSummary` through that moment plus the learner's single
version-level disclosure of generated-patch use. The nullable accept/reject flag remains
because the approved product asks whether generated patches caused success; aggregate
counts alone cannot distinguish seeing a proposal from using one.

### 3.8 Curation (offline CLI, never imported by `app.py`)

```python
# curation/pipeline.py
def discover(queries: Sequence[str]) -> list[MissionSource]: ...   # Tavily discovery, quarantined
def verify(source_id: Id, human_verifier: str) -> MissionSource: ...  # human checks primary source
def freeze(source_id: Id, fixture_path: str) -> MissionSource: ...    # becomes an executable fixture

# curation/ablation.py
class ChangeTopology(StrEnum): KNOWN_PAGE, STRUCTURAL
class DiscoveryArm(StrEnum): FROZEN, KNOWN_PAGE_POLLING, TAVILY

class AblationEvent(BaseModel):
    id: Id
    domain: Literal["cpsc.gov", "gov.uk", "ec.europa.eu", "productsafety.gov.au"]
    published_at: datetime
    topology: ChangeTopology
    pre_change_known_urls: tuple[str, ...]
    before_ref: str
    after_ref: str
    canonical_constraint_ref: str

class AblationManifest(BaseModel):
    frozen_at: datetime
    window_start: datetime
    window_end: datetime
    events: tuple[AblationEvent, ...]      # exactly 12; three/domain, 2 known + 1 structural
    query_templates: tuple[str, ...]
    minimum_structural_wins: Literal[2]
    minimum_structural_win_domains: Literal[2]
    maximum_candidates_per_fixture: Literal[10]
    maximum_median_review_minutes: Literal[30]

class AblationOutcome(BaseModel):
    arm: DiscoveryArm
    event_id: Id
    candidates_reviewed: int
    review_minutes: int
    verified_constraint_ids: tuple[Id, ...]
    frozen_fixture_ids: tuple[Id, ...]

def validate_ablation_manifest(manifest: AblationManifest) -> None: ...
def adjudicate_ablation(
    manifest: AblationManifest,
    outcomes: Sequence[AblationOutcome],
) -> Literal["KEEP_TAVILY_CLAIM", "DROP_TAVILY_CLAIM"]: ...
```

Lifecycle validation forbids placeholder provenance: `quarantined` may have neither
verifier nor fixture; `verified` requires `human_verifier`; `frozen` requires both;
`rejected` never has a fixture. State transitions are append-audited.

### 3.9 Response projections (`api/schemas.py`)

```python
class DraftView(BaseModel):
    shift_id: Id
    files: dict[str, str]                 # editable contents; never a storage ref or host path
    updated_at: datetime

class ShiftView(BaseModel):
    id: Id
    engagement_slug: Slug
    seq: int
    state: Literal["open", "closed"]
    opened_at: datetime
    closed_at: datetime | None

class ArtifactVersionView(BaseModel):
    id: Id
    shift_id: Id
    parent_id: Id | None
    content_hash: str
    contract: ContractParams
    contract_catalog_hash: str
    assistance_summary: AssistanceSummary

class RunView(BaseModel):
    id: Id
    shift_id: Id
    artifact_version_id: Id
    attempt_number: int
    state: RunState
    adapter: Literal["local_process", "recorded", "tokenfactory"]
    failure_kind: ExecutorFailure | None
    started_at: datetime
    ended_at: datetime | None

class CustomerAnswerView(BaseModel):
    action: Literal["answer", "ask", "decline", "escalate"]
    display_text: str                    # controller-rendered from validated structured fields
    claims: tuple[Claim, ...]
    evidence_refs: tuple[Id, ...]
    verified_record_age_ms: int | None

class RunOutputView(BaseModel):
    id: Id
    run_id: Id
    request_ordinal: int
    request_text: str
    http_status: int | None
    body_base64: str
    customer_answer: CustomerAnswerView | None
    elapsed_ms: int | None
    transport_error: ExecutorFailure | None
    log_base64: str | None               # sanitized captured log bytes; no internal path/ref

class CheckResultView(BaseModel):
    id: Id
    run_id: Id
    public_check_id: Id | None
    verdict: Literal["pass", "fail", "error"]
    observed_ref: Id
    reason_code: ReasonCode | None

class IncidentView(BaseModel):
    id: Id
    state: IncidentState
    opening_run_id: Id
    failing_output: RunOutputView
    comparison: CheckResultView
    public_shop_record: dict[str, JsonValue] | None
    public_shop_record_ref: Id | None
    resolving_version_id: Id | None
    opened_event_seq: int
    resolved_event_seq: int | None
    synthetic: Literal[True] = True

class LedgerEventView(BaseModel):
    event_type: LedgerEventType
    seq: int
    prev_hash: str
    hash: str
    public_cause_refs: tuple[Id, ...]
    payload: dict[str, JsonValue]        # outbound allowlist applied recursively
    synthetic: Literal[True] = True

class LedgerView(BaseModel):
    events: tuple[LedgerEventView, ...]
    chain_status: Literal[ChainStatus.VALID]
    synthetic: Literal[True] = True

class BoardView(BaseModel):
    engagement_slug: Slug
    shift: ShiftView | None
    artifact_version_id: Id | None
    artifact_content_hash: str | None
    artifact_files: tuple[str, ...]
    decisions: tuple[str, ...]
    visible_checks: tuple[VisibleCheck, ...]
    requests_run: int
    incidents: tuple[IncidentView, ...]
    unresolved_limits: tuple[str, ...]
    ledger_totals: dict[LedgerEventType, int]
    attempts_remaining: int
    synthetic: Literal[True] = True

class AssistEventView(BaseModel):
    id: Id
    shift_id: Id
    role: AssistRole
    model_id: str
    accepted: bool | None
    created_at: datetime
```

`body_base64` round-trips arbitrary capture bytes, including malformed UTF-8.
`customer_answer` exists only after structured validation; malformed or contradictory
fields produce a failed check and no customer-facing sentence. `DraftView` is the sole
browser path for editable file contents. Durable `storage_ref`, `request_ref`,
`response_ref`, `shop_snapshot_ref`, `sandbox_ref` and sealed refs never appear in a
public projection.
`request_text` is read from this run's frozen request batch at `request_ordinal`, only
for an executed request; no future batch lookup is exposed. `public_check_id` links
only a learner-visible check definition (the builder's `VisibleCheck.id` is retained
when creating its `CheckDef`); it is null for sealed results. Thus the client can show
the current customer request and "Visible check passed" without a sealed check id.
Public refs resolve only to permitted evidence, never filesystem paths or sealed
store keys. `CheckResult.expected_ref`, rotation identities and expectations have no
fields in these projections. Ledger payloads and cause refs must also pass the same
outbound allowlist; wrapping an internal row does not make its nested fields safe.

A mismatch pair may use an independently published shop record, with its own
provenance, never a value copied from the sealed store. When no public record exists,
`public_shop_record` and its ref are null and the UI shows only the reason code.
Screens 03/04's illustrative exact record comparison requires such public evidence;
a sealed failure alone is not authority to disclose the expected count.

Board decision counts come from learner-authored entries in the versioned change-log
file, not inferred from saves, runs or assistant text. Repair direction and rationale
are recorded there before freezing; visible checks live in the artifact's check file.
Freezing retains both files, and restoration reloads them. `incidents` includes OPEN
and CLOSED_UNRESOLVED records until a later passing repair resolves them. Derived
ledger totals count event types after verification; every business-state component
must visibly render "Synthetic scenario", not just carry a JSON boolean.

## 4. API surface (final names)

| Route | Verb | Request → Response | Notes |
|---|---|---|---|
| `/` | GET | — → static client | Six screens per mockups |
| `/api/engagements/{slug}/board` | GET | — → `BoardView` | Artifact state, decisions/requests counts, open incidents, unresolved limits, ledger summary, attempts remaining (screens 01/05) |
| `/api/engagements/{slug}/shifts` | POST | — → `ShiftView` | Opens next shift, seeded from inheritance (409 if a shift is open) |
| `/api/shifts/{id}/artifact` | GET | — → `DraftView` | Loads allow-listed UTF-8 filenames and editable contents; never an internal ref |
| `/api/shifts/{id}/artifact` | PUT | `DraftFiles` → `DraftView` | Saves and returns the mutable working copy; freezing creates immutability |
| `/api/shifts/{id}/artifact/versions` | POST | `FreezeVersionRequest` → `ArtifactVersionView` | Freezes files + contract + catalog hash + aggregate assistance summary (409 on invalid contract) |
| `/api/shifts/{id}/runs` | POST | — → `RunView` (202) | Budget + rotation enforced server-side; 409 `BudgetExhausted` / `RotationUnavailable` |
| `/api/runs/{id}` | GET | — → `RunView` | Polling, mirrors sandbox async pattern; no executor-internal refs |
| `/api/runs/{id}/outputs` | GET | — → `RunOutputView[]` | Raw captures, timing, log refs |
| `/api/runs/{id}/checks` | GET | — → `CheckResultView[]` | Sealed cases surface as consequences only — reason codes and opaque refs, never expectations |
| `/api/shifts/{id}/close` | POST | — → `ShiftView` | Atomic and idempotent; records unresolved incidents/limits once; refuses while a run is in flight |
| `/api/engagements/{slug}/ledger` | GET | — → `LedgerView` | Events + derivation links + `chain_status` (verify on read) |
| `/api/incidents/{id}` | GET | — → `IncidentView` | Mismatch pair, linked version, repair state (screen 04) |
| `/api/shifts/{id}/assist` | POST | `AssistRequest` → `AssistReply` | Bounded, logged, attributed; 403 for disallowed roles |
| `/api/assist-events/{id}/decision` | POST | `AssistDecision` → `AssistEventView` | Records one accept/reject decision for a patch proposal; no version link |
| `/api/engagements/{slug}/assist-events` | GET | — → `AssistEventView[]` | Safe attribution log (operator surface; see §10.9) |

Errors are typed: every non-2xx maps to a `domain/errors.py` kind rendered with a
stable `error_code` string. View models (`BoardView`, `LedgerView`, …) are response-only
projections so no sealed ref or internal row shape leaks by accident.

## 5. Call stack

Format: `caller → callee`. Repo/store functions are named per table and are illustrative
at that layer only.

### 5.1 Open shift
`routes.open_shift → orchestrator.open_next_shift → repo.get_engagement + repo.get_config`
→ seed inputs: latest `ArtifactVersion` (or template for shift 1 / away shift),
`repo.list_unresolved_incidents` (OPEN and CLOSED_UNRESOLVED),
`repo.list_unresolved_limits`, `repo.ledger_summary`
→ `repo.insert_shift` (seq = max+1) → `repo.copy_version_to_draft` → `Shift`.

### 5.2 Submit → freeze version
`routes.freeze → orchestrator.freeze_version → load immutable ContractCatalog version`
→ validate required dimensions and option ids (no preselection; no hidden "right" stance)
→ snapshot aggregate assist counts + accepted-patch count + learner's generated-patch-use
disclosure → build `ArtifactHashEnvelope(files_base64, contract_json,
contract_catalog_hash) → canonical_bytes → content_hash`
→ `repo.insert_artifact_version (parent_id = latest)` → immutable; the draft remains the
working copy for further edits. Any code, contract, or catalog-version change changes
the hash; identical inputs reproduce it.

### 5.3 Start run (budget + rotation)
`routes.start_run → orchestrator.start_run → begin immediate transaction → require open
shift and a frozen version → repo.count_runs(shift) vs config.attempt_limit` (409
`BudgetExhausted`) → select **one never-exposed variant per enabled family for this
attempt** → `repo.insert_run(state=QUEUED, attempt_number, artifact_version_id,
request_batch_ref, shop_snapshot_ref)` → insert one `RotationDraw` per family → commit
→ schedule `execute_run` → 202 `Run`. Missing inventory returns 409
`RotationUnavailable` and rolls back the entire reservation.

Variant selection binds the checks to pre-authored customer stimuli and frozen data;
it never swaps unrelated expectations onto an unchanged output. The resulting request
batch is fixed before execution, has stable ordinals, and is identical across adapters
for that run. Only its customer requests and service-consumable snapshot enter the
executor, never case specs, rotation metadata or expected outcomes. Future-shift
requests are not returned by the board, artifact or assist surfaces before their run.

Reservation uses durable exposure history across **all shifts and cycles** for the
engagement. Uniqueness covers `(shift_id, attempt_number)`, `(run_id, family)` and
`(engagement_slug, variant_ref)`. A committed reservation consumes its attempt and
variants even if provisioning fails or the controller crashes. A retry needs a new
reservation; the evaluator loads exactly the persisted draws, not a fresh draw or
an entire group. Inventory and exhaustion rules are specified in §7.1.

### 5.4 Execute run (async)
`orchestrator.execute_run → executor adapter .execute(RunRequest)` → local process /
recorded / tokenfactory (Gate 4) → **raw bytes only** → `normalize_captures` →
`repo.insert_run_outputs` (append-only, state=RUNNING→CAPTURED) → `orchestrator.finalize_run`.
Failure → state=FAILED + `failure_kind`; outputs stay as evidence; no checks, no events.

### 5.5 Finalize: evaluate → reduce → chain (one transaction)
`orchestrator.finalize_run → evaluator.load_drawn_cases(run_id) →
evaluator.evaluate(outputs, checks, visible_checks, drawn_cases, contract)` →
`CheckResult[]` → `repo.insert_check_results`
→ `reducer.reduce(fixtures, outputs, results, contract)` → drafts → `chain.append(drafts,
prev_hash, start_seq)` → `repo.insert_ledger_events` → open/resolve incidents →
`repo.set_run_state(FINALIZED)`. All of it commits together; a failure anywhere writes
no check results and no events (run stays unfinalized; §6.B.9). A partial capture set
(a run that failed mid-batch) is finalized as FAILED with the completed prefix — no
invented captures.

### 5.6 Render evidence
`routes.get_run_outputs → repo.get_outputs(run) → parse ServiceResponse →
validate_service_response against public records → render_customer_text → RunOutputView`
(§3.2, §3.9). Invalid fields or false `record_age_ms` produce a failed check and no
customer answer; the exact raw body remains available as `body_base64`.
`routes.get_run_checks → repo.get_check_results → CheckResultView` → reason codes and
public evidence refs only, never `expected_ref` or variant ids.
`routes.get_ledger → repo.read_events → chain.verify_chain` → `LedgerView` only on
`VALID`; `BROKEN` returns a hard error without events or derived board counters.
The output → public comparison → synthetic event chain follows §3.9.

### 5.7 Repair
`routes.get_incident → repo.get_incident + failing output + check_result` → learner edits
draft and records repair direction/rationale (`PUT artifact`) → `freeze_version`
(new version) → `start_run` (next attempt, fresh rotation draw) → `finalize_run`.
A later run must pass the incident's linked regression and the current unseen
acceptance check for that failure family before it resolves. Repeating an old
regression does not count as an unexposed rotation draw. Set `Incident.state → RESOLVED`
with `resolving_version_id`; otherwise keep OPEN or CLOSED_UNRESOLVED as appropriate.

### 5.8 Close → inherit
`routes.close_shift → orchestrator.close_shift → begin immediate transaction → if already
closed, return the existing Shift without writes → refuse if a run is in flight`
→ capture `CloseShiftFacts` → `reduce_close(fixtures, facts)` → unchained drafts →
`chain.append(prev_hash, start_seq)` → insert `LIMIT_DECLARED` events (derived from
`CloseShiftFacts.declared_limits` only) → unresolved OPEN incidents become
`CLOSED_UNRESOLVED` and are inherited as incident rows, never as `LIMIT_DECLARED`
events → `repo.close_shift` → commit once.
Concurrent or retried close requests serialize on the shift row and cannot append a
second event set; a fault at any boundary rolls the entire close back.
Next shift seed = latest version, decisions/check files, all unresolved incidents
(including CLOSED_UNRESOLVED), limits and verified ledger summary. Closing cannot
hide an unresolved incident from inheritance. The new run consumes fresh variants
from the remaining inventory (§7.1); no future customer wording is released before
execution, and sealed specs/expectations are never released at any time (§6.D, §6.K).

### 5.9 Assist call
`routes.assist → assist.gateway.assist → begin immediate transaction → check role against
EngagementConfig (away shift: stakeholder dialogue, hint and diagnosis only) → count all
prior model interactions against total_assist_budget_per_shift → reserve one interaction
→ commit → build bounded prompt (no sealed refs, no evaluator internals) → Nemotron call
→ complete AssistEvent → AssistReply`. Every model call consumes one unit even if it
fails after reservation; rejected requests that never reach the model are logged but do
not consume budget. Patch proposals return labelled diffs. The learner may record one
accept/reject decision, but no proposal id is linked to a version; §5.2 snapshots only
aggregate counts and the version-level generated-patch-use disclosure.

### 5.10 Curation (offline)
`curation.pipeline.discover (Tavily, quarantined) → verify(human) → freeze` →
`repo.insert_mission_source` + frozen fixture file. Runtime imports of `curation` are
forbidden (§6.J.39); Tavily never appears in any runtime path.

## 6. Test plan

Named tests; each must be able to fail against broken behavior. Deterministic tests run
offline against `recorded` / `local_process`; test 29 is the explicit future sandbox
conformance gate and rendered client assertions run in their Gate 4 browser slice.

### A. Canonical hashing (`tests/domain/`)
1. `test_canonical_bytes_key_order_invariance` — same content, different key order and
   whitespace → identical bytes and hash (golden vectors file pinned).
2. `test_canonical_rejects_floats` — a float anywhere in a hashed payload raises.
3. `test_golden_hash_vectors` — fixed payloads → pinned hashes; any change requires an
   explicit vector update (guards silent hash drift across machines).

### B. Ledger reducer + chain (`tests/ledger/`)
4. `test_reducer_replay_equality` — same fixtures/outputs/results/contract → identical
   drafts, in-process twice and in a subprocess.
5. `test_reducer_is_pure_no_io` — reducer module runs with sockets disabled and performs
   no file writes (import closure + no-I/O assertion).
6. `test_chain_break_detection` — tampered event → `verify_chain` hard failure.
7. `test_correction_events_only` — corrections append new events referencing the old;
   no row is ever updated or deleted.
8. `test_finalization_idempotent` — finalize twice → zero net new events and no
   duplicate incidents.
9. `test_interrupted_finalization_writes_no_events` — fault injected at each commit
   boundary and in QUEUED, RUNNING and CAPTURED states: no orphan rows or missing hash
   parents; restart marks nonterminal runs FAILED with captures and reservations retained.
   A committed FINALIZED run keeps its events and state across restart.
10. `test_projection_vs_replay_equivalence` — board state from tables equals
    `replay(events)` after every scenario; inheritance seeds match.

### C. Evaluator (`tests/evaluator/`)
11. `test_evaluator_import_closure_no_network_no_llm` — transitive imports contain no
    HTTP client, no assist module, no socket use; full evaluation passes with sockets blocked.
12. `test_evaluator_negative_control` — a deliberately broken artifact transcript yields
    failing verdicts (protects against an always-pass evaluator).
13. `test_check_results_never_contain_expected_values` — results and API payloads contain
    only reason codes and opaque refs.
14. `test_contract_parameterized_checks` — the same transcript passes or fails depending
    on committed catalog options exactly where the contract legitimately allows both;
    the evaluator checks consistency with the chosen stance rather than rewarding one
    hidden stance. Fixed invariants are unaffected by contract choice.
15. `test_unknown_sealed_schema_version_alarms` — unknown sealed case version → hard
    error, never a silent skip.

### D. Isolation and leakage (`tests/sealed/`, `tests/api/`)
16. `test_sentinel_sealed_string_never_leaves_controller` — a unique sentinel value placed
    in a sealed case appears in no sandbox payload, no prompt, no API response, no log
    (scan of every serialized outbound surface).
17. `test_sealed_import_graph` — `executor/`, `assist/`, `api/`, `client` never import
    `shiftwork.sealed`; only `evaluator` does.
18. `test_sandbox_payload_manifest_exact` — provisioning file list equals the allowlist
    (artifact snapshot, current request batch, harness, frozen shop snapshot). Sealed
    specs/expectations are absent from the manifest, every API response and every prompt
    before, during and after execution. Future customer stimuli stay absent until their run.
19. `test_reason_code_render_map_pinned` — render strings match the pinned list; no
    numbers, case text or hidden counts (lint-style leak check over the render map).
20. `test_host_paths_and_env_never_reach_learner` — learner-visible payloads from a
    local-adapter run containing injected markers do not expose host paths or env values.

### E. Artifacts and versions (`tests/store/`)
21. `test_version_immutability` — a submitted version cannot be mutated; stored files,
    contract and catalog hash reproduce the recorded `content_hash` on read. Changing
    code only, contract only, catalog version only, or all three changes the hash.
22. `test_freeze_requires_valid_contract` — missing required dimensions, option ids from
    another engagement/catalog, or a mutated previously used catalog version are rejected.
23. `test_restore_reprovisions_not_resets` — fresh process: latest version hash, draft,
    incidents and ledger all reconstruct from tables; no executor checkpoint is used.

### F. Budget and rotation (`tests/orchestrator/`)
24. `test_budget_enforced_controller_side` — the (limit+1)th run POST returns 409 and
    inserts no run row (UI-independent).
25. `test_budget_atomic_under_race` — two concurrent run POSTs at the boundary → exactly
    one run row and one draw per enabled family; no orphan reservations. Inject a fault
    between run insertion and draw insertion: the entire reservation rolls back.
26. `test_rotation_draws_unexposed_variant` — all three attempts consume distinct variants
    per family; failed and interrupted runs still consume committed reservations.
    Restart cannot redraw them, and evaluation uses only the saved variant identities.
27. `test_rotation_exhaustion_fail_closed` — one exhausted family refuses the whole run
    without rows or partial draws. A refill rejects reused identities, appends newly
    authored variants and increments `cycle` without deleting prior exposure records.

### G. Executor adapters (`tests/executor/`)
28. `test_conformance_suite_recorded_local` — shared case table: happy path, process-up
    but port dead, request timeout, truncated body, non-UTF-8 body, connection refused,
    kill mid-batch → identical normalized captures and identical typed failure kinds.
29. `test_conformance_suite_tokenfactory` — same suite, **skipped until the real adapter
    exists** (explicit skip, not silent); must pass before the Gate 4 sandbox slice closes.
30. `test_adapters_emit_raw_bytes_only` — no adapter path can emit parsed objects;
    normalization is the single conversion point.
31. `test_local_process_rejects_untrusted_artifacts` — an artifact absent from the pinned
    trusted fixture hash list is refused before a subprocess starts, including a modified
    copy of a trusted fixture. This is an execution guard, not a host-isolation test.

### H. Flows (`tests/api/`)
32. `test_open_shift_seeds_from_inheritance` — board after open equals prior version,
    open incidents, unresolved limits, ledger summary.
33. `test_close_shift_records_unresolved_limits` — closing writes hash-chained
    `LIMIT_DECLARED` events for the version's declared limits
    (`CloseShiftFacts.declared_limits`) exactly once; unresolved OPEN incidents become
    `CLOSED_UNRESOLVED` incident rows and are inherited that way, never as
    `LIMIT_DECLARED` events. The next shift's seeded board shows declared limits in
    `unresolved_limits` and the incidents in `incidents`, as two distinct inheritances.
    Closing during an in-flight run is refused. Repeated and concurrent closes return
    one closed shift and one event set; injected faults at every boundary leave neither
    a partial close nor partial events.
34. `test_repair_resolves_only_on_passing_later_run` — incident resolves only when a
    later run of the new version passes the linked check.
35. `test_away_shift_has_no_inherited_artifact` — bike co-op starts from template with
    its own families and reduced assist config.

### I. Assist (`tests/assist/`)
36. `test_assist_logged_and_attributed` — every call writes an `assist_events` row with
    timestamp, role, model id and optional patch acceptance. Version freeze records only
    aggregate counts by role, accepted-patch count and learner-declared patch use; no
    proposal-to-version foreign key exists.
37. `test_assist_cannot_touch_sealed_or_evaluator` — requests referencing sealed refs,
    expected values or evaluator logic are refused; prompts contain no sealed paths.
38. `test_away_shift_role_restrictions` — `PATCH_PROPOSAL` and `SCAFFOLDING` roles are
    403 for the bike co-op engagement. Every permitted role shares one total budget;
    concurrent calls at the boundary cannot exceed it, and failed post-reservation model
    calls still consume their unit.

### J. Curation (`tests/curation/`)
39. `test_curation_never_imported_by_runtime` — `app.py` import closure excludes
    `curation`; quarantined sources may have no verifier/fixture, verified sources require
    a human verifier, and only verified sources with a fixture can become `frozen`.

### K. Review regression cases (`tests/orchestrator/`, `tests/api/`, client checks)
40. `test_full_budget_preserves_unseen_inherited_case` — consume three bookshop attempts
    across every family, repair, close and restart. The next shift retains the version,
    decisions, visible checks and unresolved incidents, but draws three still-unexposed
    variants per family over its three attempts. Run the pre-repair and repaired trusted
    fixture artifacts against the same held-out stimuli in an operator-only comparison:
    the former fails and the latter passes. Scan every first-shift outbound surface for
    future customer wording; none may appear. Renaming an expectation over the same
    repeated customer input does not satisfy the unseen-stimulus assertion. This test
    must fail against the old three-variant bookshop inventory.
41. `test_synthetic_labels_and_public_evidence_projections` — board, run, incident and
    ledger client views visibly display "Synthetic scenario", including empty and error
    states. Removing the label must fail the rendered check. Public record comparisons
    retain provenance; sealed-only failures show reason codes without an expected value.
    Inject sealed sentinels into nested ledger payloads, incident records and logs and
    assert they never serialize. Assert base64-decoded output bodies equal original bytes.
    Assert each displayed customer text matches the executed batch ordinal, no future
    customer text is returned, visible verdicts link to the learner's check id and
    every sealed result has a null `public_check_id`.

### L. Gate 3 correction regressions (`tests/domain/`, `tests/api/`, `tests/curation/`)
42. `test_customer_text_is_derived_not_authored` — a valid structured response produces
    the pinned rendered sentence; a false age, invalid evidence ref or malformed claim
    produces no customer sentence and fails. There is no `reply_text` input to contradict.
43. `test_contract_catalog_history_is_stable` — changing a used option's label or rule id
    is refused; a new version may change wording/semantics while old ledger entries still
    resolve against their original catalog version.
44. `test_free_text_limit_is_not_scored` — an unsupported intent may be saved as a
    declared limitation and inherited, but cannot satisfy a required executable dimension
    or silently become an evaluator rule.
45. `test_draft_round_trip_has_no_internal_refs` — GET returns the saved filenames and
    text; PUT round-trips them; every public projection omits injected storage, host,
    sandbox, request and response refs.
46. `test_assist_budget_applies_across_roles` — dialogue, hint and diagnosis all consume
    the same total cap; switching role names cannot obtain extra calls.
47. `test_patch_decision_and_summary_are_minimal` — one patch decision is durable and
    idempotent; version summary counts it without storing a proposal-to-version link.
48. `test_tavily_ablation_manifest_is_preregistered` — the corpus manifest is rejected
    unless domain allowlist, time window, event-selection rule, budgets and kill thresholds
    are frozen before any comparator output exists.
49. `test_tavily_ablation_kill_rules_fail_closed` — fixtures cannot be marked Tavily-
    attributable unless they pass human verification and executable-change criteria;
    missing either effectiveness or review-burden threshold kills the prize claim.

### M. Executor credential isolation (`tests/executor/`)

50. `test_executor_env_exposes_no_controller_credentials` — the environment an adapter
    run executes in (subprocess env for `local_process`; provisioned sandbox env for
    `tokenfactory`; no environment at all for `recorded`) contains no controller
    credential material: unique markers injected into the controller env for
    `NEBIUS_API_KEY`, `CONTREE_SESSION`, `TAVILY_API_KEY`, `SHIFTWORK_DB_PATH` and
    sealed-store access appear in no executed environment, no in-sandbox reachable file
    and no captured log; `local_process` scrubs the child environment to a pinned
    allowlist before the subprocess starts; only the scoped `InferenceGrant` (when
    present) is reachable by the artifact. For `tokenfactory` this asserts the
    provisioning payload/env construction and is exercised live in the real-adapter
    slice alongside the spike's secret-injection probe. This is the credential arm of
    Test 1's "hidden cases or credentials are reachable" kill condition; tests 16–18
    are the case arm. Number 50 is appended without renumbering 1–49 to preserve
    existing cross-references.

These are test specifications, not implemented tests or passing results. Test 41's
rendered assertions require a browser during the applicable Gate 4 slice; test 50's
`tokenfactory` arm requires the real adapter slice.

## 7. Configuration appendix (provisional — challenge these)

### 7.1 Limits and inventory

| Knob | Default | Rationale |
|---|---|---|
| `attempt_limit` | 3 per shift (both engagements) | initial run + two repair cycles; exhaustion still allows closing with unresolved incidents inherited |
| `rotation_group_size` | bookshop: 6 variants per family; bike co-op: 3 | one fresh variant per family per attempt; covers two bookshop shifts and one away shift at their full budgets |
| Sealed inventory (initial) | bookshop: 3 families × 6 variants = 18; bike co-op: 3 families × 3 variants = 9; total 27 | bookshop: `stale_information`, `policy_exception`, `hostile_instruction`; bike co-op: `future_commitment`, `safety_escalation`, `retry_booking`; all provisional and unauthored |
| Total assist budget | bookshop 6 model interactions/shift; bike co-op 2/shift | one cap across every allowed role prevents relabelling a request as dialogue or diagnosis to evade a hint-only limit; provisional, not evidence-backed |
| Assist roles | bookshop: all five; bike co-op: `STAKEHOLDER_DIALOGUE`, `HINT`, `DIAGNOSIS` | away shift loses scaffolding and patch proposals |
| Response-time limits | learner chooses 1 s / 3 s / 8 s, no default | screen 02 input; latency measured by the harness |
| Executor selection | `recorded`, `local_process`, `tokenfactory` | local process accepts pinned trusted fixtures only (§3.3); real sandbox path needs separate authorization |
| Assist model candidate | `nvidia/nemotron-3-super-120b-a12b` | documented in architecture §16; actual availability and id rechecked by the spike |

Capacity invariant: variants per family must cover `attempt_limit × funded shifts`.
For each bookshop family, shift 1 can consume at most variants 1–3; shift 2 still has
3 never-exposed variants (4–6), even after all first-shift repair attempts. These
ordinals illustrate capacity, not published case identities. An early close does not
reset exposure history. Bike co-op draws from its own nine-case inventory.

Attempt exhaustion never blocks editing or closing. Rotation exhaustion refuses runs
and preserves the artifact, limits and history; it does not manufacture an "unseen"
case by resetting the cycle. Continuing beyond the funded shifts requires the operator
to author and review new variants. A refill increments `cycle`, appends new immutable
identities and keeps every prior draw. Relabelled copies of exposed cases do not count
as new holdouts. Automatic recycling and within-shift reuse are forbidden.

All knobs live in `config.py` + `engagement_config` rows (architecture §18 item 6).
Changing a budget requires the capacity check to pass before the config is activated;
these provisional counts bound opportunities to probe, not prove resistance to leakage.
Assist calls reserve against their total budget atomically and every role shares the cap.
The 6/2 defaults are deliberately challengeable: they make the away shift materially
lower-assistance, but no learner evidence shows either number is pedagogically correct.

### 7.2 Reason codes (learner-visible vocabulary)

Nine codes, 1:1 with `ReasonCode` (§3.2), rendered as one-line consequences without
numbers from sealed cases, without case text, without hidden counts:

| Code | Learner-facing meaning |
|---|---|
| `INVENTED_FACT` | The service stated something the shop records did not support. |
| `STALE_BEYOND_RULE` | The answer used a record older than the rule you committed to. |
| `MISSING_EVIDENCE` | The answer was not attached to the evidence it used. |
| `WRONG_ACTION` | The service answered, asked, declined or escalated against your own committed rule. |
| `UNSAFE_CONTINUATION` | Help continued where your rule required a human to take over. |
| `DUPLICATE_COMMITMENT` | A retried request created a second commitment. |
| `LATENCY_BUDGET` | The answer took longer than the limit you set. |
| `MALFORMED_RESPONSE` | The response contract was not produced correctly. |
| `REGRESSION` | A behavior that passed before now fails. |

This wording is the Gate 3 proposal, not a later implementation decision. Static
inspection finds no case values or counts in these strings; that is not proof against
inference from repeated outcomes. Tests 16, 19 and 41 must challenge the actual
serialized/rendered surfaces. Any necessary wording change revises this design.

### 7.3 Env var names (final)

Documented by primary sources: `NEBIUS_API_KEY`, `CONTREE_SESSION`, `TAVILY_API_KEY`.
Application names: `SHIFTWORK_DB_PATH`, `SHIFTWORK_EXECUTOR`,
`SHIFTWORK_SANDBOX_IMAGE`, `SHIFTWORK_LEARNER_INFERENCE_KEY`, `SHIFTWORK_ASSIST_MODEL`.
No values or credentials here; non-secret design defaults are listed in §7.1.

## 8. Transfer-study decision

**Planning verdict: not feasible under current constraints before October 30, 2026,
10:00 AM Pacific.** This is not proof that recruitment could never become feasible.

- Rough equal-size, independent two-arm calculation: assume one binary transfer outcome
  per learner, 50% → 70%, two-sided α = 0.05 and 80% power. Cohen's
  `h = 2 × (asin(sqrt(0.70)) − asin(sqrt(0.50))) ≈ 0.411517`.
  `n_per_arm ≈ 2 × (1.959964 + 0.841621)^2 / h^2 ≈ 92.70`, rounded to **93 per arm,
  186 total**, before attrition. The original 47-per-arm estimate omitted the
  two-independent-groups factor; the earlier LLM review incorrectly accepted it.
- This is an approximation, not a completed study plan. Multiple tasks per learner
  are correlated observations, not extra participants. Final power requires the
  analysis unit, baseline, correlation, attrition and test to be specified. A paired
  or within-subject design needs its own calculation; its savings are not known here.
- Current constraints: solo builder, recruitment/outreach unauthorized, manual kit
  unrun. Those constraints support the no-study submission plan independently of the
  corrected sample estimate.

Consequences recorded here:
- **No impact claim will be made at submission**, consistent with `01-product.md`
  "Success metric". The 20-point metric stays a north star, not an achieved result.
- The Test 2 comparison requirements remain fixed: matched time/tests/total assistance budget;
  counterbalanced bookshop and bike-cooperative tasks; independently passed cases,
  time, hints, generated patch use, learner explanation, authored decisions and
  voluntary return; brief §9 Test 2 kill criteria. These are protocol requirements,
  not a fully specified recruitment, randomization or analysis protocol. Execution
  waits until after the deadline, if ever, and needs separate authorization.
- Test 1 (central mechanism) and Test 3 (Tavily ablation) remain possible pre-deadline
  proof slices **only after Gate 4 approval and required external-service authority**.
- The 5-person kit remains optional qualitative input. It is currently unrun: every
  human threshold is unmet and no human evidence exists. An authorized future human
  run could supply formative observations, never powered learning evidence.
- The away shift remains a product feature; its learning value is unproven and must
  be labelled unmeasured on learner-facing surfaces, as in mockup 06.

If recruitment were authorized later, the first step is the small manual kit, not
claiming that the powered study is ready to run.

### 8.1 Tavily ablation protocol (specified, not run)

Purpose: test whether allow-listed Tavily discovery finds executable mission constraints
that a strong known-page polling baseline misses, at an acceptable human-review cost.
This is a historical replay, not a live-runtime dependency and not evidence until run.

**Pre-registered corpus.** Before any comparator output is generated, freeze one manifest
containing:

- window: **2025-08-01 through 2026-07-31 UTC**;
- allow-listed official domains: `cpsc.gov`, `gov.uk`, `ec.europa.eu`, and
  `productsafety.gov.au`;
- **12 dated change events**, three per domain: two changes reachable from the frozen
  pre-change known-page set and one structural event on a new/out-of-set page;
- the exact pre-change page list, archived before/after evidence, canonical constraint,
  and whether the event is known-page or structural; and
- selection rule: within each domain/stratum, take the earliest qualifying events in the
  window by official publication timestamp. Do not include or exclude an event based on
  whether Tavily found it. If the manifest cannot supply all 12 with authoritative
  before/after evidence, the ablation does not run and no Tavily claim is made.

The structural stratum deliberately gives the discovery hypothesis a fair opportunity;
it does not guarantee a Tavily win because Tavily must still find the event. A structural
event counts only when no frozen known page exposes the change or a link to it during
replay. The source classes are grounded in dated official policy and product-safety
updates (for example, the CPSC recall index and GOV.UK consumer guidance); every selected
event still needs human verification and reuse review before freezing.

**Three arms under the same cutoff and reviewer rubric:**

1. Frozen curriculum: the pre-change fixture set receives no discovery.
2. Known-page polling: fetch every frozen known URL, diff content, extract newly linked
   same-domain pages one hop, and retain those URLs for later replay dates.
3. Tavily discovery: fixed query templates, the same domain allowlist and cutoff, with
   no answer-key terms, event titles or post-change URLs in prompts.

Normalize and shuffle candidates before one human reviewer sees them; method labels stay
hidden during relevance/authority/applicability review. Record candidates reviewed,
valid new constraints, false positives, review minutes and frozen executable fixtures.
A discovery counts as useful only when the reviewer verifies the primary source and the
constraint changes at least one executable fixture or expected service behavior.

**Pre-registered success and kill thresholds:**

- effectiveness: Tavily must produce at least **two** useful structural discoveries,
  across at least **two distinct domains**, that known-page polling misses;
- review burden: at most **10 human-reviewed candidates per useful frozen fixture** and
  median review time at most **30 minutes per useful frozen fixture**; and
- integrity: zero unverified or non-allow-listed content may affect a fixture, evaluator,
  sealed case or score.

If any threshold is missed, remove the Tavily best-use/prize claim. Shiftwork may remain;
Tavily is then optional curation convenience, not a central contribution. Passing this
small replay supports only the bounded discovery claim, not broad superiority.

## 9. Capability spike protocol (specified, not run)

Purpose: resolve architecture §16 items before any slice depends on the real sandbox.
Requires Token Factory credentials — **not authorized, not run**. When authorized:
bounded, single-purpose probes with raw evidence retained.

| # | Question (§16 item) | Observable evidence | Fails if |
|---|---|---|---|
| 1 | File transfer in/out of a sandbox (item 2) | artifact files in; captured bytes out; hashes match on both sides | no path to move arbitrary files in/out |
| 2 | Outbound networking from a sandbox (item 3) | in-sandbox service reaches the inference base URL | egress blocked and no documented alternative |
| 3 | Secret injection + scoping (item 4) | scoped key injected, usable in-sandbox, absent from logs/other paths | injection impossible → controller-side inference proxy fallback (§7 of architecture) |
| 4 | Timeouts and resource limits (item 5) | measured deadline behavior, limits discoverable | no enforceable deadline → harness redesign |
| 5 | Ingress posture (item 1) | whether any inbound request harness exists | not a failure — design does not require ingress |
| 6 | Cost, latency, entitlements (item 6) | recorded numbers for budget planning | never a silent assumption |

Kill handling: an adapter-local change may stay inside the approved boundary. A failed
probe that invalidates an approved isolation, inference or execution assumption stops
the dependent slice and triggers the software-factory backtracking rule; update the
affected gate document and obtain explicit re-approval before proceeding. An adapter
interface is not evidence that every fallback works. A proposed inference proxy must
itself demonstrate a reachable, authenticated, budget-enforced path before adoption.

## 10. Least confident decisions (challenge while free)

1. **Single-service + stdlib-only template.** Constrains learners to Python HTTP
   services with no third-party packages. It is honest about unverified egress, but may
   be too cramped for the "applied-AI-engineering" feel (no SDKs). Alternative: allow
   packages once egress is proven.
2. **Structured visible checks.** The mockup's Given/When/Then free text becomes an
   enumerated builder (§1). Executable and honest, but may read as less expressive than
   the mockup promises.
3. **Reason-code wording.** Nine codes are a guess between "useful" and "non-quotable";
   the hostile leak review may demand fewer or blander strings.
4. **Rotation exhaustion policy.** Runs stop until the operator authors new variants;
   cycle increments never permit repetition. This preserves the unseen-case requirement
   but creates curriculum maintenance work. Probing resistance remains untested.
5. **Fixture-lie boundary.** The conformance suite is only a plan and cannot establish
   real sandbox behavior. Local execution is trusted-fixture-only, not a sandbox.
6. **Sealed inventory authoring cost.** 27 cases (18 bookshop + 9 bike co-op) fund the
   two-shift bookshop arc and one away shift at three attempts each. Reducing inventory
   without reducing the corresponding attempt budget breaks the capacity invariant;
   semantic independence of newly authored variants needs operator review.
7. **Attempt limit = 3.** More repair attempts require additional never-exposed variants
   per family for every funded shift, not merely a larger attempt counter.
8. **Study infeasibility verdict.** Rests on the current constraints (solo, no
   recruitment authorization, deadline). It should be revisited if any constraint changes.
9. **Single-user operator surfaces.** Learner and operator are the same person locally;
   labeled operator data (attempt counts, rotation cycles, chain status) is visible to
   the learner. Acceptable now; a hosted demo may need separation.
10. **Sync handlers + single-writer SQLite** for the orchestration path (async executor,
    sync store facade). Adequate at this scale; architecture §18.4 already lists SQLite
    concurrency as the first component to revisit.
11. **Declared limitations.** Free text is retained verbatim as a learner declaration;
    recording or inheriting it never means an evaluator verified it. The client must
    distinguish a declared limitation from an observed incident, and it cannot satisfy
    a required executable contract dimension.
12. **Total assist budgets = 6/2.** The shared cap closes the role-switching loophole,
    but the actual numbers have no learner evidence and may be too generous or too tight.
13. **Contract catalog pressure.** Stable ids make deterministic evaluation possible,
    but a poor catalog can still turn judgement into a menu. Versioning preserves history;
    the declared-limit escape hatch preserves unsupported intent without pretending to score it.
14. **Tavily corpus and thresholds.** Twelve historical events, two cross-domain
    structural wins and a 10-candidate/30-minute review cap are pre-registered falsifiers,
    not evidence-backed universal thresholds. Failure removes the prize claim.

## 11. Explicitly deferred (not decided here)

- Slice order, tracer bullet, demo URL/hosting shape, hosted-demo obligation of the
  local-first design → Gate 4.
- Spike execution → an authorized Gate 4 proof slice; real `tokenfactory.py`
  implementation depends on its evidence, not the other way around.
- Tavily ablation execution and corpus-manifest population → an authorized Gate 4 proof
  slice. §8.1 already fixes the domains, window, selection rule and kill thresholds;
  implementation may not tune them after seeing comparator output.
- Implementing and browser-checking the client against the mockups → Gate 4 slices.
  Reason-code wording is decided in §7.2; hostile serialization tests verify that
  boundary during implementation rather than silently selecting new wording.
- Deployment, credentials, installs, purchases, outreach → separate explicit authorization.
- ADR #4 (execution topology) → only after spike evidence (architecture §19).
