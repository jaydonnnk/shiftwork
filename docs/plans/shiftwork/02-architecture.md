# Architecture: Shiftwork — first bookshop engagement

Gate: 2 - Architecture (RE-APPROVED 2026-09-19 after the scoped backtrack;
originally APPROVED 2026-09-15). Written 2026-09-15; scoped revision 2026-09-19
explicitly re-approved by the user. Gate 3 requires its own approval.
Sources accessed 2026-09-15; no external source was re-checked in this revision.
ADRs 0001-0003 were promoted from S19 candidates during Gate 3 drafting
(2026-09-15); candidate #4 stays deferred until spike evidence and separate authorization.

### Scoped backtrack re-approved: sealed-store access ownership

The Slice 6 verification found that the prior S2, S7 and S13 reserved sealed-store
reads for an evaluator module, but controller orchestration calls the sealed loader
and passes its data to a pure scorer. The user re-approved that explicit split in
S2, S5, S7 and S13: controller orchestration owns loading; evaluation receives its
inputs and does not load files. No implementation is changed by this revision.

The earlier co-located loader and pure scoring function were feasible. The prior
Gate 3 test 11 prohibited network/LLM dependencies, not a loader's file access;
impossibility is not the reason for this change. The approved split makes the
existing ownership explicit without widening learner or model access. Exact
imports, signatures and their test requirements are now under separate Gate 3
revision; they are NOT approved by the Gate 2 decision. ADR 0001's prior-ownership
sentence is superseded by the dated note recorded later the same day (2026-09-19),
with the original text kept as history. ADRs and Gate 4 were unchanged by this
documentation step; the Gate 4 follow-up revision of 2026-09-19 is separate.

All other architecture decisions remain unchanged. Statements about the repository
before implementation retain their 2026-09-15 planning context; current delivery
and the Slice 6 repair hold are recorded in `00-status.md`. This revision does not
approve execution topology, credentials, installs, external calls or later slices.

Scope: only the first bookshop engagement and the central loop -
learner-owned versioned service → fixed request batch → isolated execution evidence →
independently authored checks → deterministic append-only synthetic ledger →
inherited next shift. Nothing here authorizes implementation; implementation starts
after Gate 4.

## 1. Fit

- **No runtime application exists.** The repository contains only documentation
  (`AGENTS.md`, `HACKATHON_REQUIREMENTS.md`, `shiftwork_vs_hatchery.md`, `docs/`),
  the Tavily doc mirror (`.tavily_llms.txt`, `.tv/`) and `.gitignore`. Gate 2
  introduces the first runtime; nothing existing is modified.
- The current six mockups (`docs/plans/shiftwork/mockups/`) stay the UI source of
  truth and are implemented later against this architecture, not now.
- The controller (see S2) is a new local application. It does not replace or wrap
  any existing service.
- `.gitignore` already excludes `.env*` and key material; secrets must never enter
  the repository (S12).

## 2. Runtime and module boundaries

One process owns truth; all execution is disposable.

| Module | Responsibility | Trust zone |
|---|---|---|
| **Web client** | Renders the six screens (shift board, contract, run, repair, return, away) | Untrusted (learner-editable browser) |
| **Controller API** | HTTP surface, session and public evidence rendering; delegates lifecycle operations to controller orchestration | Trusted |
| **Controller orchestration** | Shift/run lifecycle, artifact drafts and snapshots; sole caller outside the sealed store of its loader; supplies evaluator inputs | Trusted (controller-side) |
| **Artifact store** | Immutable, content-hashed versions + one mutable draft per shift | Trusted (controller-side) |
| **Executor adapter** | Single interface for "run this artifact snapshot against this batch"; production implementation = Token Factory Sandbox; test implementation = fake/in-process | Trusted boundary; sandbox is untrusted |
| **In-sandbox harness** | Starts the learner service on loopback, sends the fixed batch, captures raw outputs + logs | Untrusted (runs inside sandbox) |
| **Deterministic evaluator** | Pure scoring of supplied captures, sealed cases, public records and committed contract; emits check results without loading stored data | Trusted; controller-side only |
| **Ledger reducer** | Pure function: check results + raw outputs → ledger events; append-only, hash-chained | Trusted; controller-side only |
| **Assist service** | Bounded Nemotron roles (stakeholder dialogue, hints, diagnosis, labelled patch proposals); every call logged | Trusted gateway; model itself untrusted output |
| **Curation tool** | Offline Tavily-assisted mission-fixture review; operator-run, human-verified | Trusted; not part of runtime |
| **Sealed store** | Controller-only loader of sealed case specs + expected outcomes; called only by controller orchestration outside the store itself | Trusted, most restricted |

Boundary rules:

- The learner artifact is the only artifact that ever executes inside a sandbox.
- The sandbox is treated as hostile: nothing read back from it is trusted except
  captured outputs, and those are validated (size/shape) before storage.
- No module below the controller API may be reachable from the browser.

## 3. Endpoints

Proposed controller HTTP API (none of these exist yet; final names decided at
Gate 3):

| Route | Verb | Purpose |
|---|---|---|
| `/` | GET | Serves the static web client |
| `/api/engagements/{slug}/board` | GET | Shift board: artifact state, open incidents, unresolved limits, ledger summary |
| `/api/engagements/{slug}/shifts` | POST | Open a shift seeded from inherited state |
| `/api/shifts/{id}/artifact` | GET/PUT | Read or save the mutable working copy |
| `/api/shifts/{id}/artifact/versions` | POST | Freeze the working copy into an immutable content-hashed snapshot |
| `/api/shifts/{id}/runs` | POST | Execute a submitted version against the fixed request batch |
| `/api/runs/{id}` | GET | Run state and progress (polling; mirrors the async pattern of the sandbox API) |
| `/api/runs/{id}/outputs` | GET | Exact captured outputs, timing, logs |
| `/api/runs/{id}/checks` | GET | Check outcomes (sealed cases are reported as consequences, never as expectations) |
| `/api/engagements/{slug}/ledger` | GET | Append-only ledger events with derivation links and hash chain |
| `/api/incidents/{id}` | GET | Incident evidence (mismatch pair, linked version, repair state) |
| `/api/shifts/{id}/assist` | POST | Bounded assist request; response is logged and attributed |

## 4. Data

One relational store (proposed SQLite; single learner, low volume). Every table is
either append-only or single-row-mutable; nothing is hard-deleted.

| Table | Holds | Main queries |
|---|---|---|
| `engagements` | Business profile (bookshop) | Resolve board and seed data by slug |
| `shifts` | Shift instances, sequence, state | Open next shift (max seq + 1); shift history |
| `draft_artifacts` | One mutable working copy per shift | Get/put by shift |
| `artifact_versions` | Immutable snapshots: `content_hash`, `parent_id`, storage ref | Latest version; history/changelog; integrity check by hash; restore source for the next shift |
| `request_batch` | The fixed customer requests for the engagement (text, ordinal, visible evidence refs) | Ordered batch for a run |
| `runs` | One execution of one artifact version; state, sandbox ref, timing | Latest run per shift; attempt count per shift (budget enforcement) |
| `run_outputs` | Append-only per-request captures: status, body, timing, log ref | Evidence rendering; evaluator input |
| `check_defs` | Checks: kind (invariant / contract-conformance / sealed acceptance / regression), visibility (learner / sealed), author, rotation group | Active set for the evaluator; learner-visible list for UI |
| `check_results` | Append-only outcomes: verdict, observed ref, opaque expected ref, reason code | Per-run outcomes; regression trend across shifts |
| `ledger_events` | Append-only, hash-chained business events with cause refs | Replay from seq 0; chain verification; board counters |
| `incidents` | Mismatch records, state, resolving version | Open incidents; repair linkage |
| `assist_events` | Every assist call: role, request, response ref, accepted/rejected | Attribution; Nemotron ablation analysis |
| `mission_sources` | Frozen fixtures with URL, fetch time, content hash, human verifier, Tavily provenance | Fixture freshness and provenance audit |

Key semantics:

- **Two data layers, deliberately divergent.** The service under test receives a
  frozen shop-data snapshot inside the sandbox (the state it may legitimately
  consume). The evaluator holds the authoritative record and sealed expectations
  controller-side. The staleness between them is the scenario, not an accident.
- **Checks are parameterized by the learner's committed contract** where the
  contract legitimately allows several correct behaviors (e.g. a chosen freshness
  rule implies its own acceptable staleness window). Invariant checks ("must
  never") are independent of learner choices. Sealed expected values are referenced
  by opaque id and never copied into learner-visible rows.
- `check_results.expected_ref` and `mission_sources.fixture_ref` point into the
  sealed store / fixture store; those files are not readable from any
  learner- or model-facing process.

## 5. Flow

Main path — one shift run:

1. Learner opens the board; controller seeds the shift from the previous shift's
   latest artifact version, open incidents, unresolved limits and ledger summary.
2. Learner edits the draft; each save is a mutable write. Nothing is evaluated yet.
3. Learner submits; controller hashes and stores an immutable `artifact_version`.
4. Controller provisions a sandbox from a pinned base image (content-addressed),
   copies in the artifact snapshot, the fixed request batch and the harness.
5. Harness starts the learner service on loopback inside the sandbox, sends the
   batch in fixed order, captures every response, status, timing and log.
6. Captures return to the controller; the sandbox is torn down (it is never a
   source of truth — see S6).
7. Controller orchestration loads applicable sealed cases through the sealed
   store, then supplies the captures, cases, public records and committed contract
   to the deterministic evaluator. The evaluator scores invariants,
   contract-conformance, sealed acceptance and prior-shift regression checks
   without loading files or using a database, network or LLM.
8. Ledger reducer derives the event set from check results with a pure function
   and hash-chains the new events (S10).
9. UI renders the run: exact outputs, check outcomes, incident openings, ledger
   deltas. No sealed expectation is rendered.
10. Learner repairs: edit → new version → new run. The incident links the failing
    run to the version that repairs it.
11. Shift closes. The next shift inherits artifact, decisions, incidents, open
    limits and ledger state; the new shift's sealed case is not materialized
    anywhere the learner or model can read before the run.

## 6. Artifact versioning, restart and restoration

- A **version** is an immutable, content-hashed snapshot (files + declared
  contract parameters) with a parent link; a **draft** is the single mutable
  working copy per shift. Submitting freezes; it never mutates a version.
- **Restore = re-provision from the controller store**, never a sandbox
  checkpoint and never a reset of history. Learner decisions, incidents and
  ledger state are reloaded from tables, not from any running process.
- **Restart safety:** after any crash, all state is reconstructible from
  `artifact_versions` + `runs` + `run_outputs` + `check_results` + `ledger_events`.
  No in-memory state is authoritative. An interrupted run is marked failed on
  restart; it produces no ledger events.
- Attempt budget: counted from `runs` per shift; must be enforced controller-side,
  not just in the UI.

## 7. Evaluator, credential and sealed-case isolation

- **Sealed cases never enter a sandbox or inference prompt.** They live in the
  controller-side sealed store. Within the runtime application, only controller
  orchestration outside that store may directly import or call its loader; it
  supplies cases to the pure evaluator. Executor, assist, API handlers, client,
  persistence, ledger, domain and curation modules must not directly import or
  call the sealed store. API handlers may delegate lifecycle operations to
  orchestration without receiving sealed cases. Operator-only case-authoring,
  verification tools and tests are not learner/model interfaces; this runtime
  importer rule does not prohibit their separately authorized inspection.
- The sandbox receives only the artifact snapshot, harness, fixed visible request
  batch and frozen shop-data snapshot from controller state. The module ownership
  rule does not establish hostile-code isolation for the trusted local adapter;
  real sandbox isolation still requires the separately authorized spike and tests.
- **Evaluation is deterministic and LLM-free.** The scoring function receives its
  inputs explicitly and performs no file/database access or network calls. A second
  language model is never an oracle. Nemotron can propose, diagnose or explain;
  it cannot compute check verdicts, ledger events or pass declarations.
- **Credential separation:**

  | Credential | Controller | Sandbox | Learner/browser |
  |---|---|---|---|
  | DB / internal state | yes | no | no |
  | Sandbox provisioning key | yes | no (injected by controller) | no |
  | Scoped inference key for the learner service | minted by controller | yes — scoped, budget-capped | never directly |
  | Sealed store access | controller orchestration through the sealed loader only; evaluator receives supplied cases | no | no |
  | Tavily key | curation tool only | no | no |

- Mechanisms for scoping and injecting the inference key (env at provision time,
  file transfer, egress rules) are documented as unverified in S16 and must be
  pinned by the capability spike before slices depend on them.
- The learner artifact must run with no controller credentials present; if the
  spike shows safe injection is impossible, a controller-side inference proxy on
  the harness path is the fallback — decided by spike evidence, not assumed now.

## 8. Repeated-probing leakage controls

- Sealed case text and expected values are never rendered to the learner, the
  model, or any log the learner can read; outcomes surface as business
  consequences and minimal, non-quotable reason codes.
- **Rotation:** sealed cases belong to rotation groups; each attempt set draws the
  variant not yet exposed. Attempt limits per shift are enforced controller-side.
- **Raw traces retained:** every request/response capture and assist interaction is
  stored, so extraction patterns (systematic boundary probing) are auditable after
  the fact.
- Filesystem hiding alone is insufficient; the isolation is structural
  (sealed store is never mounted into the sandbox, never in an inference prompt).
- If leakage is suspected: rotate the affected group, invalidate dependent
  attempts, keep all traces for operator review (append-only; nothing is deleted).

## 9. Deterministic ledger ownership and replay

- The ledger is **append-only and hash-chained** (`prev_hash` → `hash` per event).
  Controller owns writes; nothing else — learner, harness or model — can write.
- Reducer purity: `reduce(fixtures, raw_outputs, check_results, committed_contract)
  → events`. Same inputs must replay to identical events; replay is exercised in
  tests against recorded fixtures.
- Corrections are **new events** referencing the corrected event, never edits.
- Chain verification runs on read; a broken chain is a hard failure surfaced to
  the operator, not silently repaired.
- Business consequences are synthetic scenario state (orders, refunds, incidents,
  backlog) and must be labelled as such everywhere they are rendered.

## 10. Nemotron responsibilities and authorship boundaries

- **Allowed roles (controller-mediated, logged in `assist_events`):** bounded
  stakeholder dialogue (owner brief persona), scaffolding after the learner has
  committed to an approach, requested hints, failure diagnosis of the learner's
  service, and clearly labelled patch proposals the learner may accept or reject.
- **Forbidden roles:** reading sealed cases, expected outcomes, evaluator logic,
  ledger rules or credentials; declaring pass/fail; owning requirements,
  tradeoffs, visible tests or repair direction; acting as an independent check.
- **Authorship preservation:** original and assisted versions are both recorded;
  the accepted/rejected flag is part of the durable record.
- **No dependence claim:** the deterministic core (runs, checks, ledger,
  inheritance) must operate with all Nemotron features disabled. Whether removing
  Nemotron materially weakens learning outcomes is unmeasured — no architectural
  dependence on it is claimed until the ablation is run.

## 11. Tavily mission-curation boundary

- Tavily is used **only** in the offline mission-curation pipeline: discover
  changes in allow-listed official sources → human verifies the primary source →
  the verified change becomes a frozen executable fixture (`mission_sources`).
- Tavily is **absent from the runtime answer path** — the learner service never
  queries Tavily for customer answers, and Tavily never touches scoring, checks,
  ledger or sealed cases.
- If a later ablation shows Tavily adds only prose or links, the related prize
  claim must be removed rather than kept.

## 12. External services and configuration

Env var **names only**; values never appear in the repository or docs.

Documented by primary sources:
`NEBIUS_API_KEY` (Token Factory auth), `CONTREE_SESSION` (Sandbox CLI session),
`TAVILY_API_KEY`.

Proposed application names (final at Gate 3): `SHIFTWORK_DB_PATH`,
`SHIFTWORK_SANDBOX_IMAGE`, `SHIFTWORK_LEARNER_INFERENCE_KEY` (the scoped key the
controller mints and injects), `SHIFTWORK_ASSIST_MODEL`.

External systems: Nebius Token Factory (inference + Sandboxes), Tavily (curation
only). Nothing else. No webhooks; no public ingress into the sandboxes is required
by this design (S16 covers what remains unverified).

## 13. Observability and execution evidence

- Every run stores: exact request/response bodies, status, timing, service logs,
  harness logs, artifact version hash, sandbox reference.
- The UI renders the evidence chain the mockups describe: output → independent
  comparison → synthetic ledger event, with derivation links that resolve to raw
  records.
- Operator surfaces: attempt counts, assist log, chain-verification status,
  provenance of mission fixtures. Learners can inspect their own service's raw
  traces; runtime access to sealed expectations is confined to controller
  orchestration, the sealed loader and the evaluator, never learner/model surfaces
  or learner-readable logs.
- Nothing about the run is summarized away: the raw capture is retained even when
  derived views exist.

## 14. Local development path

- Controller runs locally (proposed: Python/FastAPI + SQLite, static client served
  by the same process). It needs no external service for the deterministic core.
- The deterministic core — evaluator, reducer, API, inheritance — must be fully
  testable offline against recorded fixtures. The executor adapter has a fake
  implementation for tests; the real sandbox implementation activates only when
  credentials and the verified spike path exist.
- Sandbox-dependent paths require Token Factory access and remain unverified until
  the spike; local development must not silently depend on them.
- Local previews report their actual URL/port; UI work follows the mockups at
  desktop and narrow widths.

## 15. Track fit (hackathon)

- **Best Apps and Agents remains the safer primary-track hypothesis.** The system
  is an end-user application whose bounded agent roles (stakeholder, hints,
  diagnosis) use an NVIDIA model — that fits without over-claiming.
- **Coding and Agentic Engineering stays conditional:** only if a Nemotron-powered
  agent meaningfully writes, runs and tests code in Token Factory Sandboxes
  without erasing learner authorship. Not claimed now; the spike and slices will
  produce or fail to produce that evidence.
- Hackathon obligations still require a real runtime call to Token Factory
  inference or execution on Nebius AI Cloud, plus at least one NVIDIA open-source
  model; the proposed design does both if the unverified items in S16 resolve
  favorably (and the ablation checks must survive regardless of track).

## 16. Verified facts, proposed architecture, unverified assumptions

**Verified (primary sources, accessed 2026-09-15):**

- Token Factory Sandboxes ("Contree"): VM-level isolation ("untrusted code cannot
  escape the sandbox"); OCI image import; checkpoint/fork with 180-day retention;
  async operations with polling; ≤50 simultaneous operations (beta).
  https://docs.tokenfactory.nebius.com/sandboxes/overview
- Sandbox CLI exists (`contree` CLI; `contree use` / `contree run`,
  `CONTREE_SESSION` session variable): https://docs.tokenfactory.nebius.com/sandboxes/cli
  (the overview page confirms the CLI exists but not individual commands).
- Sandboxed coding-agent workflows are a documented pattern:
  https://docs.tokenfactory.nebius.com/sandboxes/swe-agents
- Inference API: OpenAI-SDK-compatible, base URL `https://api.tokenfactory.nebius.com/v1/`,
  key in `NEBIUS_API_KEY`. https://docs.tokenfactory.nebius.com/quickstart
  (the Nemotron service page shows a regional host,
  `https://api.tokenfactory.us-central1.nebius.com/v1/` — exact host to be pinned
  at implementation against the quickstart.)
- Nemotron models available on Token Factory: Nemotron 3 Nano 30b, Nano Omni,
  Super 120b (`nvidia/nemotron-3-super-120b-a12b`), Ultra 550b.
  https://nebius.com/services/token-factory/nemotron
- Nebius Serverless: Endpoints expose a public URL, Jobs are non-interactive,
  Devlabs are browser IDEs. https://docs.nebius.com/serverless/overview
- Tavily API and key convention (`TAVILY_API_KEY`):
  https://docs.tavily.com/documentation/quickstart

**Proposed (this document; decided here, not yet verified against reality):**
everything in S2–S15 — the controller/sandbox split, tables, routes, reducer,
isolation model, local-dev path.

**Unverified (must not be assumed either way; resolve with a bounded capability
spike before slices depend on them):**

1. Sandbox inbound/ingress — the docs do not mention it. This design does not
   require it, and does not claim it is impossible.
2. File transfer in/out of a sandbox (artifact snapshot in, captures out) — not
   documented; the API reference page currently documents only image listing.
3. Outbound networking from a sandbox (needed if the learner service calls the
   inference API at runtime) — not documented.
4. Secret injection into a sandbox and egress/scoping enforcement — not documented.
5. Sandbox timeouts and resource limits — not documented.
6. Actual entitlements, cost, latency; Nemotron context/tool-calling specifics;
   whether any Nebius service hosts an arbitrary container web app for a demo URL.
7. Whether the learner artifact is reliably one loopback HTTP service (assumed
   from the mockups; confirmed at Gate 3).

## 17. Failure containment and rollback

- Sandbox failure mid-run: run marked failed, no ledger events, retry permitted
  within the attempt budget; the artifact version is untouched.
- Evaluator or reducer failure: run finalization is a single transaction; a
  partial run writes no check results and no events.
- Ledger mistakes: corrective events only; history is never rewritten. Chain
  verification failure is surfaced as a hard error.
- Sealed-case leak (suspected or confirmed): rotate group, invalidate affected
  attempts, retain everything for review.
- Bad artifact version: immutable; the learner submits a new version. Nothing is
  deleted, so prior evidence stays intact.
- No deployment exists in this gate; rollback scope is the local workspace and a
  single database file. Deployment risk decisions wait for a later gate.

## 18. Least-confident decisions

1. **Sandbox I/O without ingress** — the whole isolation story depends on file
   transfer and (likely) outbound networking that the docs do not currently
   document. This is the first spike target; if it fails, the executor adapter
   boundary absorbs the change but the demo shape changes.
2. **Contract-parameterized checks** — evaluating against the learner's committed
   contract is the honest reading of "no hidden correct stance," but it is harder
   than fixed expectations and could produce ambiguity the evaluator mishandles.
3. **Reason-code granularity** — enough detail to be useful, little enough to avoid
   leaking sealed expectations; wording needs hostile review before slices.
4. **SQLite single-writer** — adequate now; if the demo needs concurrency beyond
   one learner, this is the first component to revisit.
5. **Single-service assumption** — one loopback HTTP service per artifact is an
   assumption inherited from the mockups, not a product decision.
6. **Attempt-limit and rotation numbers** — enforcement belongs here; the actual
   numbers are Gate 3 configuration and should be easy to change.

## 19. ADR candidates

Candidates 1–3 were recorded as ADRs 0001–0003 in `docs/adr/` during Gate 3
drafting on 2026-09-15, after Gate 2 approval. Candidate 4 remains deferred until
spike evidence; recording the first three does not approve Gate 3 or the topology.

1. **Sealed-evaluator isolation** — expected outcomes and evaluator logic never
   enter any learner- or model-readable environment; evaluation is deterministic
   and controller-side. Reason: protects the evaluation contract against
   tampering and leakage; durable beyond this feature.
2. **Deterministic ledger ownership and replay** — append-only, hash-chained,
   pure-reducer derivation with replay equality. Reason: inheritance and the
   business-consequence model depend on reproducibility.
3. **Artifact versioning and restoration semantics** — immutable content-hashed
   snapshots; restore re-provisions from the store and never rewrites history.
   Reason: persistence across shifts is the product's core mechanism.
4. **Execution topology (in-sandbox harness, no public-ingress dependency)** —
   promotable only after the bounded capability spike verifies file transfer and
   the inference path; until then it is an unverified hypothesis, not an ADR.

Explicitly **not** ADR material: product scope decisions (Gate 1 owns them),
mockup/visual design, hackathon research targets, unverified technology
hypotheses (must be verified first), and Gate 3 details (files, signatures, test
plan) that will churn during implementation.

## 20. Explicitly deferred to later gates

- File layout, types/signatures, test plan → Gate 3.
- Slice order, tracer bullet, demo URL/hosting shape → Gate 4 (and after the
  capability spike for anything sandbox- or Serverless-dependent).
- Attempt limits, rotation sizes, reason-code wording → Gate 3 with config
  designed in this architecture.
- Any deployment, credential provisioning, install or external service use →
  separate explicit authorization; not covered by Gate 2.
