# Vertical Slice Plan: Shiftwork

Gate: 4 — Vertical Slices (APPROVED 2026-09-17). Written 2026-09-16; revised
2026-09-17 (three rounds). Round 1 applied the edits queued behind the Gate 3 re-approval:
Slice 2 is restructured into a thin real vertical path (user decision A), Slices 3–5
are re-scoped to conformance / variants / hardening that deepen it, every test landing
is re-mapped at clause level, Slice 8 is renamed an offline pre-proof, and Slice 16
gains a hard submission no-go criterion; the user also resolved the four original §11
questions. Round 2 (after an independent Gate 4 review) put Slices 13–14 on the
mandatory packaging path, made every demo command a checked-in `demos/` entry point
(PowerShell where an HTTP command is unavoidable), added test 51 plus the Slice 12
model-feedback evidence pack, added the conditional Slice 17, and recorded §11
decisions 5–6. Round 3 applied the review's three consistency corrections (Python
bound `>=3.12,<3.14`; Gate 3 header record; neutral Tavily checklist), and the user
approved this plan the same day.
Scope: the approved architecture (`02-architecture.md`) and program design
(`03-program-design.md`) turned into a build order of visible, working, testable
slices. This is the approved build order: slice work proceeds one slice at a time
under §10. Credentials, installs, spike runs, external services, deployment,
outreach and ADR #4 each remain separately authorized.

Build stance: the deterministic core is buildable offline with zero credentials and
is the product's differentiator, so it is front-loaded. The Nemotron assist gateway
is the minimum path that satisfies the hackathon's runtime-inference + NVIDIA-model
requirement, so it is on the submission critical path even though it builds after the
core. The real Token Factory sandbox adapter is on the submission critical path too —
only the verified Sandbox path can execute learner-edited artifacts (Gate 3 §3.3) —
and is gated on credentials that do not exist yet; the Tavily ablation and any hosted
demo remain evidence-gated and optional.

## 1. How to read this plan

Each slice below lists, in the same order:

- **Delivers** — the one capability the slice adds.
- **Demo evidence** — the exact command(s) the user will run and what they will see.
  This is the "prove it works" step; nothing is claimed until it is shown. Convention:
  every command is a checked-in runnable entry point — either a `python -m demos.<name>`
  module committed in that slice or an exact `pytest` node id — never a prose
  description of a step. Angle-bracket placeholders (`<id>`, `<port>`) are substituted at
  run time and reported. `python -m demos.<name>` and `pytest` node ids are the canonical,
  shell-independent evidence path; wherever an HTTP command is unavoidable it is supplied
  as a tested PowerShell command (a Git-Bash equivalent is optional).
- **Still mocked / missing** — what stays fake, so no slice over-claims.
- **Tests landed** — `03-program-design.md` §6 specification numbers that become real,
  failing-capable tests in this slice.
- **Authoring / config decisions** — content the operator must create, or provisional
  numbers the user may challenge, before the slice can pass.
- **Authorization** — what (if anything) beyond Gate 4 approval this slice needs.

After **every** slice the workflow is: run the demo evidence, show the user the actual
result, check the slice off in `00-status.md`, then ask **"Continue to slice N+1, or
re-steer?"** No slice is "done" on a green test alone; the user sees it run.

Rules honored throughout (software-factory §Gate 4): Slice 1 is a tracer bullet wired
end to end with mocks. Slice 2 replaces the mocks with a **thin real end-to-end happy
path** — one artifact frozen under a real content hash, one customer request really
executed, one sealed case really evaluated into a `CheckResult`, one real hash-chained
ledger event — narrow but real at every step, which is the literal software-factory
"Slice 2 = real happy path" rule satisfied by a thin vertical slice (user decision A).
Slices 3–5 then each **deepen one concern** of that path rather than being the first
time a layer is real: Slice 3 generalizes execution into the full executor conformance
suite, Slice 4 generalizes evaluation into the contract-parameterized evaluator and the
first sealed family, Slice 5 hardens the ledger into the pure reducer + chain +
idempotent finalization. Later slices add one capability each; no horizontal layering
(no "all the DB, then all the API, then all the UI"). Every slice ends in a runnable,
testable state.

## 2. Build order at a glance

| # | Slice | Phase | Authorization beyond Gate 4 |
|---|---|---|---|
| 1 | Tracer bullet — full lifecycle, all mocked | A. Deterministic core | none |
| 2 | Thin real vertical path: artifact → request → sealed case → evaluator result → ledger event | A | none |
| 3 | Executor conformance (recorded + local_process) — deepens Slice 2 execution | A | none |
| 4 | Contract-parameterized evaluator + first sealed family — deepens Slice 2 evaluation | A | none |
| 5 | Reducer + hash chain + idempotent finalization — hardens Slice 2 ledger | A | none |
| 6 | Isolation and leakage hardening | A | none |
| 7 | Budget + rotation + incidents + repair | A | none |
| 8 | Close → inheritance + **Test 1 offline pre-proof** | A | none |
| 9 | Client: board + customer-shift screens (01, 03) | B. Client | none |
| 10 | Client: contract + repair screens (02, 04) | B | none |
| 11 | Client: inherited + away screens (05, 06) + away config | B | none |
| 12 | Nemotron assist gateway | C. External-gated | `NEBIUS_API_KEY` (live calls) |
| 13 | Token Factory capability spike | C | `NEBIUS_API_KEY` / `CONTREE_SESSION` |
| 14 | Real tokenfactory adapter + full Test 1 verdict | C | depends on Slice 13 |
| 15 | Tavily curation + ablation | C | `TAVILY_API_KEY` |
| 16 | Submission packaging — test build + demo video | D. Submission | deployment / external-action authorization |
| 17 | Hosted deployment — **conditional**: only if Option B is selected at the Slice 13 exit (§8) | D. Submission | deployment / external-action authorization |

Phase A (1–8) is the critical path to the central-mechanism proof and needs no
credentials. Phase B (9–11) makes the proof legible as a product rather than a
console. Phase C (12–15) is gated on credentials. Phase D (16–17) is the submission
shape. **Dependency note: Slice 16 depends on Slices 1–14** — the offline core, the
client, the Nemotron assist gateway (the hackathon's runtime-inference + NVIDIA-model
compliance path) and the real sandbox adapter, because only the verified Sandbox path
can execute learner-edited artifacts (Gate 3 §3.3): without it the shipped product
cannot run the core learner loop. **Slices 13–14 (spike + real tokenfactory adapter)
are on the mandatory packaging path; Slice 15 (Tavily ablation) remains
prize-conditional** and can be dropped without affecting compliance. The conditional
Slice 17 exists only if Option B survives the Slice 13 exit (§8). On Gate 4 approval
this table becomes the slice checklist in `00-status.md`.

Test 2 (reduced-assistance transfer) is deliberately **not sliced**: Gate 3 §8 defers
it past the 2026-10-30 deadline and no impact claim is made at submission.

## 3. Interpretation of "execute the central-mechanism proof first"

`docs/SHIFTWORK_PLAN.md` §12 records a preference to execute the central-mechanism
proof (its §9 Test 1) first. I agree with the priority and have ordered the whole
plan to serve it, but I want to surface a disagreement with the literal reading
"Test 1 is the first thing executed," because following it literally would produce a
false proof.

Test 1's kill conditions include "hidden cases or credentials are reachable" and
"semantic replays disagree." Those cannot be adjudicated until the real evaluator,
the pure reducer + hash chain, the sealed store, the rotation draw-without-replacement
and the leakage/isolation suite actually exist and pass. Running Test 1 against the
mocked tracer bullet would "pass" vacuously and prove nothing.

So the faithful reading is: **front-load everything Test 1 depends on; defer assist,
Tavily and visual polish until after it.** That is what this plan does. The **Test 1
offline pre-proof** becomes executable at the end of Slice 8, and Slices 1–8 are all on
its critical path. The tracer bullet (Slice 1) is the same loop, mocked — it
demonstrates the *shape* of the causal chain (real output → independent check →
deterministic ledger → inherited next shift) so the user can see the skeleton before the
logic is real; Slice 2 then makes that chain real but thin, and Slices 3–8 deepen and
harden it until the pre-proof can run.

Slice 8 is a **pre-proof, not the full Test 1 verdict**, because running offline imposes
three structural limits that no amount of offline work can retire:

1. **Hostile-code isolation is untestable offline.** `local_process` runs trusted
   fixtures only (Gate 3 §3.3), so the "hidden cases reachable" *case* arm is only
   partially adjudicated — a genuinely hostile artifact is never executed offline.
2. **The credential arm is only fully adjudicated at Slice 14.** Test 50 offline covers
   `recorded` (no environment at all) and `local_process` (child env scrubbed to a pinned
   allowlist), but the "credentials are reachable" limb is only fully tested against a
   real provisioned sandbox env in test 50's `tokenfactory` arm at Slice 14.
3. **"Consequence caused by execution" requires `local_process`.** The `recorded` adapter
   executes nothing — it replays captured bytes — so it cannot demonstrate that a repaired
   artifact *causes* a different outcome. The causal comparison (pre-repair fixture fails,
   repaired fixture passes, same held-out stimuli) therefore runs on `local_process`,
   never on `recorded`.

The full Test 1 PASS/FAIL verdict is **reserved for Slice 14**, re-run on the real
adapter with the same protocol. A FAILED Slice 8 pre-proof still triggers the
software-factory backtracking rule — it is a real go/no-go on the offline mechanism, just
not the final word on isolation.

## 4. Phase A — deterministic core (offline, no credentials)

### Slice 1 — Tracer bullet (full lifecycle, all mocked)

- **Delivers:** the app boots, mounts the static client, opens SQLite, and the entire
  HTTP lifecycle persists and returns data: open shift → get/put draft → freeze version
  → start run → poll → outputs → checks → ledger → board → close. The `recorded`
  adapter returns a checked-in transcript. Hashing, evaluator verdicts, reducer logic
  and sealed cases are hardcoded/stubbed. One stub HTML page (not the six mockups)
  renders the board so the loop is visible in a browser.
- **Demo evidence:**
  - `python -m demos.lifecycle` → drives the full HTTP lifecycle (open shift → draft →
    freeze version with a placeholder hash → run → FINALIZED → outputs, checks, ledger)
    and prints each returned record; this is the canonical evidence command.
  - Start the app with `python -m uvicorn shiftwork.app:create_app --factory --port 8000`
    (actual port reported at run time); the browser at the reported `localhost` port
    shows the stub board with artifact, an incident and a ledger total.
- **Still mocked / missing:** canonical hash (placeholder), evaluator (hardcoded
  verdicts), reducer (hardcoded events), sealed store (empty), rotation (none), budget
  (none), assist (absent), the six real screens (one stub page).
- **Tests landed:** none of tests 1–50 from §6 (this is the wiring skeleton); a smoke
  check asserts the lifecycle returns persisted rows and can fail if a route is
  unwired, and **test 51** (clean-environment install-and-run) lands here — the
  packaging skeleton is part of this slice — and re-runs at Slice 16.
- **Authoring / config:** the packaging skeleton: `pyproject.toml` (bounded
  `requires-python`, pinned runtime/test dependency set), the generated
  `requirements.lock`, and `demos/lifecycle.py`.
- **Authorization:** none beyond Gate 4.

### Slice 2 — Thin real vertical path (one artifact → request → sealed case → evaluator result → ledger event)

- **Delivers:** the tracer's loop made **real but minimal at every step** — the
  software-factory "real happy path" as a narrow vertical slice (user decision A).
  `domain/canonical.py` (`canonical_bytes`, `content_hash`, floats rejected, golden
  vectors pinned); `freeze_version` produces ONE immutable content-hashed version whose
  hash covers files + `ContractParams` + catalog hash; the `recorded` adapter replays ONE
  checked-in transcript into real captures; the real evaluator scores ONE sealed case into
  a real `CheckResult` (reason code + opaque ref, no expected value); the real reducer +
  chain produce ONE real hash-chained `LedgerEvent`; evidence rendering returns that one
  real event. Real `schema.sql` DDL and `repo.py` groups replace the tracer's stub
  persistence. Nothing here is a layer built in isolation — one shift's data flows real
  end to end.
- **Demo evidence:**
  - `python -m demos.thin_path` → for one bookshop shift prints the frozen version's real
    `content_hash`, the one executed request's captured output bytes, the one sealed
    case's `CheckResult` (reason code + opaque `expected_ref`), and the one hash-chained
    ledger event with `chain_status: VALID`.
  - `python -m pytest tests/domain tests/store -q` green.
  - freeze identical inputs twice → identical `content_hash`; change one file byte (or the
    contract, or the catalog version) → different hash; attempt to mutate a frozen version
    → refused; restart the process → `GET .../artifact` and the version hash reconstruct
    from tables.
- **Still mocked / missing:** each concern is real but minimal, and each is deepened by a
  later slice. Executor: only `recorded` replay of one transcript — no `ExecutorAdapter`
  Protocol, no `normalize_captures` single-conversion-point, no `local_process`, no
  conformance/fault suite (Slice 3). Evaluator: one hardcoded sealed case — no
  `SealedCaseSet`, no contract-parameterization across catalog options, no negative
  control, no unknown-schema alarm, only one of six `stale_information` variants (Slice
  4). Ledger: one event — no purity/replay-equality proofs, no chain-break detection, no
  fault injection, no idempotent finalize, no incident opening (Slice 5). Rotation,
  budget, incidents, inheritance, the rest of the sealed inventory, assist and the six
  screens are absent.
- **Tests landed:** 1, 2, 3 (canonical hashing — full); 21 (version immutability — full);
  22 (freeze-requires-valid-contract — full); 23 (partial: latest version hash + draft
  reconstruct from tables with no executor checkpoint; the ledger-reconstruction clause
  completes at Slice 5 and the incident-reconstruction clause at Slice 7); 43 (partial:
  changing a used option's label or rule id is refused; the ledger-resolution-after-re-
  version clause completes at Slice 5); 44 (partial: a declared limit is stored and never
  scored — it does not appear in the one real `CheckResult` or ledger event; the "cannot
  satisfy a required executable dimension or silently become an evaluator rule" clause
  completes at Slice 4 and the "and inherited" clause at Slice 8). Plus a thin-path smoke
  check asserting the one real `CheckResult` and the one real hash-chained event are
  produced and persisted, which fails if any step is still mocked. The §6
  evaluator/reducer robustness suites (4–15, 42) are deliberately **not** claimed here —
  their full assertion sets need the deepened Slices 4–5, and claiming them against a
  one-case/one-event path would repeat the clause-level over-claim in `MISTAKES.md`.
- **Authoring / config:** the **bookshop contract catalog v1** — immutable option ids,
  learner labels and `evaluator_rule_id` bindings (§3.2 `ContractOptionId` set) — must be
  authored; the `engagement_config` row (attempt_limit, rotation_group_size, total assist
  budget) is created from §7.1 defaults; and the **minimal real fixtures** the thin path
  needs must be authored — one pinned trusted fixture artifact (or recorded transcript),
  one fixed customer request (literal bytes), the frozen shop snapshot records that
  request touches, and **one sealed case** (the first `stale_information` variant) with
  its expected value. The other five variants of that family are authored in Slice 4.
  **The user accepted these as starting values on 2026-09-17** (attempt_limit 3; bookshop
  rotation_group_size 6; total assist budget 6). They remain challengeable here and at
  Slices 7/11/12, but changing them after inventory is authored is not cheap (capacity
  invariant, §7.1). All sealed cases and fixtures are agent-drafted with the user's
  review required before sealing (§11 decision 4).
- **Authorization:** none.

### Slice 3 — Executor conformance (recorded + local_process)

- **Delivers:** generalizes Slice 2's single `recorded` replay into the full executor
  layer: the `ExecutorAdapter` Protocol, `RunRequest`/`RunResult`, and `normalize_captures`
  as the single bytes→captures conversion point; the `recorded` transcript-replay adapter
  and the `local_process` trusted-fixture subprocess adapter; the shared conformance case
  table; `local_process` rejects any artifact not on the pinned trusted-fixture hash list
  and scrubs the child environment to a pinned allowlist before the subprocess starts.
- **Demo evidence:**
  - `python -m pytest tests/executor -q` green, including identical normalized captures
    and identical typed `ExecutorFailure` kinds for injected faults (port dead, timeout,
    truncated body, non-UTF-8 body, connection refused, kill mid-batch) across both
    adapters; a modified copy of a trusted fixture is refused before any subprocess
    starts; injected credential markers are absent from the `local_process` child env.
- **Still mocked / missing:** the evaluator, reducer and chain are still the minimal
  Slice 2 versions — captures from this slice are not yet scored by the full evaluator
  (Slice 4) nor reduced by the hardened ledger (Slice 5). `tokenfactory` adapter absent
  (Slice 14). This is an execution guard, not host isolation.
- **Tests landed:** 28 (conformance recorded/local — full), 30 (raw bytes only — full),
  31 (local_process rejects untrusted artifacts — full), 50 (partial: `recorded` exposes
  no environment at all; `local_process` scrubs the child env to a pinned allowlist and
  unique markers injected for `NEBIUS_API_KEY`, `CONTREE_SESSION`, `TAVILY_API_KEY`,
  `SHIFTWORK_DB_PATH` and sealed-store access appear in no executed env and no captured
  log; the `tokenfactory` provisioned-sandbox arm completes at Slice 14). Test 29
  (tokenfactory conformance) is explicitly **skipped, not silenced**, until Slice 14.
- **Authoring / config:** the **learner artifact template** (`templates/artifact/`,
  stdlib-only loopback HTTP service), the **pinned trusted fixture artifact(s)**, the
  **fixed request batch** (literal bytes in `fixtures/requests/`), the **frozen shop
  snapshot**, and the **recorded run transcripts** (`fixtures/runs/`) must be authored,
  generalizing the single fixture/transcript/request authored for Slice 2. These are
  reused verbatim by every later adapter and by Test 1. The pinned `local_process`
  child-env allowlist is fixed here.
- **Authorization:** none.

### Slice 4 — Contract-parameterized evaluator + first sealed family

- **Delivers:** generalizes Slice 2's single hardcoded case into the full evaluator:
  `domain/customer_answer.py` (validate structured response, render customer text
  deterministically; no `reply_text` to contradict); `evaluator/evaluator.py`
  (`SealedCase`/`SealedCaseSet`, `load_drawn_cases`, deterministic LLM-free/network-free
  `evaluate`); contract-parameterized checks (consistency with the learner's chosen
  option, not a hidden right stance); `CheckResult` carries only reason codes and opaque
  refs. Completes the **first sealed family** (`stale_information`, the remaining five of
  six variants).
- **Demo evidence:**
  - `python -m demos.evaluate_transcript --fixture fixtures/runs/passing_stale.json` →
    `CheckResult[]` with `ReasonCode`s and opaque `expected_ref`; the same command with
    `--fixture fixtures/runs/failing_stale.json` → failing verdicts; both run with sockets
    blocked.
  - `python -m pytest tests/evaluator -q` green: a deliberately broken transcript yields
    failing verdicts (negative control), the same transcript passes or fails by committed
    catalog option exactly where the contract allows both, results and payloads contain no
    expected values, an unknown sealed schema version is a hard error.
- **Still mocked / missing:** the reducer/chain are still the minimal Slice 2 version —
  events are not yet hardened (Slice 5); rotation/budget absent; incidents absent. Only
  one of three bookshop families exists.
- **Tests landed:** 11, 12, 13, 14, 15 (evaluator import closure, negative control, no
  expected values, contract-parameterized, unknown-schema alarm — all full); 42 (customer
  text is derived, not authored — full). Completes the test 44 evaluator-rule clause: a
  declared limit cannot satisfy a required executable dimension or silently become an
  evaluator rule.
- **Authoring / config:** **sealed family 1** — `stale_information`: the remaining five
  case specs + expected values + the matching request ordinals and snapshot records (the
  first variant was authored in Slice 2). Requires operator review for semantic
  independence. The §7.2 **reason-code render map** wording is fixed here (it is pinned by
  test 19 in Slice 6); any wording change revises Gate 3 §7.2.
- **Authorization:** none.

### Slice 5 — Reducer + hash chain + idempotent finalization

- **Delivers:** hardens Slice 2's single ledger event into the full ledger layer:
  `ledger/reducer.py` (`reduce`, `reduce_close`, pure, no I/O) and `ledger/chain.py`
  (`append` assigns seq + hashes, `verify_chain` runs on every read, `BROKEN` aborts the
  read); `finalize_run` becomes one idempotent transaction (evaluate → reduce → chain →
  insert events → open incidents on failing checks → set FINALIZED), matching Gate 3
  §5.5; incident **resolution** via the repair loop lands in Slice 7; evidence rendering
  (`get_run_outputs`/`get_run_checks`/`get_ledger`) replaces the thin Slice 2 single-event
  rendering and resolves derivation links and catalog-version references to raw records.
- **Demo evidence:**
  - `python -m pytest tests/ledger -q` green: same inputs replay to identical drafts and
    identical hashes in-process and in a subprocess; reducer runs with sockets disabled
    and writes nothing; a tampered event makes `verify_chain` a hard failure; corrections
    append referencing events, never edit; finalize twice nets zero new events; a fault
    injected at each commit boundary writes no orphan rows; board-from-tables equals
    `replay(events)`.
  - `python -m demos.finalize_run` → a real run finalizes into hash-chained `LedgerEvent`s
    with `chain_status: VALID`; `GET ledger` shows derivation links and catalog-version
    references resolving to raw records.
- **Still mocked / missing:** rotation/budget absent; incident resolution and the repair
  loop (Slice 7); inheritance/close (Slice 8); sealed inventory is still one family; the
  six screens are still the stub page.
- **Tests landed:** 4, 5, 6, 7 (reducer replay equality, purity, chain-break detection,
  correction-events-only); 8 (finalize idempotent: zero net new events and no duplicate
  incident openings); 9 (partial: fault injection at each commit boundary, no orphan
  rows or missing hash parents, FINALIZED runs keep events across restart; the
  reservation-retention clause completes at Slice 7; the restart-marks-FAILED and
  capture-retention clauses complete at Slice 8 with `reconcile_interrupted`); 10
  (partial: projection-vs-replay
  equivalence; the "inheritance seeds match" clause completes at Slice 8); 23
  (completes the ledger-reconstruction clause); 43 (completes the ledger-resolution-after-
  re-version clause: a new catalog version may change wording/semantics while old ledger
  entries still resolve against their original catalog version).
- **Authoring / config:** the **mission fixtures** (`MissionFixtures` weights + symbolic
  transitions) must be authored and are inspectable (brief §5: weights must be
  inspectable). Synthetic-consequence labels are wired here.
- **Authorization:** none.

### Slice 6 — Isolation and leakage hardening

- **Delivers:** the structural isolation that ADR 0001 requires and that Test 1's
  "hidden cases or credentials reachable" kill condition depends on: sealed import-graph
  enforcement, sandbox-payload manifest allowlist, sentinel-leak scanning of every
  outbound surface, reason-code render-map leak lint, host-path/env non-exposure, and
  draft round-trip with no internal refs.
- **Demo evidence:**
  - `python -m pytest tests/sealed tests/api -q` green: a unique sentinel placed in a
    sealed case appears in no sandbox payload, no prompt, no API response and no log;
    `executor/`, `assist/`, `api/`, `client` never import `shiftwork.sealed`; the
    provisioning manifest equals the allowlist exactly; reason-code strings contain no
    numbers, case text or hidden counts; injected host markers never reach a
    learner-visible payload; `GET`/`PUT .../artifact` round-trips with no internal refs.
- **Still mocked / missing:** rotation/budget, incident resolution/repair and
  inheritance still absent (Slices 7/8); assist gateway not yet built (its
  sealed-isolation test 37 lands in Slice 12).
- **Tests landed:** 16 (partial: sentinel absent from every sandbox payload, API
  response and log; the "no prompt" clause is vacuous until the assist gateway exists
  and must re-run non-vacuously at Slice 12); 17 (partial: sealed import graph over
  `executor/`, `api/`, `client`; the `assist/` arm completes at Slice 12); 18 (partial:
  manifest equals the allowlist and sealed specs/expectations are absent from the manifest
  and every API response; the "absent from every prompt before, during and after
  execution" clause is vacuous until the assist gateway exists and re-runs non-vacuously
  at Slice 12 and against real provisioning at Slice 14; the "future customer stimuli
  stay absent until their run" clause completes at Slice 7 once per-run variant selection
  exists); 19, 20 (render-map pinned, host paths/env never reach learner); 45
  (draft round-trip has no internal refs).
- **Authoring / config:** none new (uses Slice 3/4 fixtures + sentinels).
- **Authorization:** none.

### Slice 7 — Budget + rotation + incidents + repair

- **Delivers:** `orchestrator.start_run` enforces the attempt limit and draws one
  never-exposed variant per enabled family atomically (`rotation_draws`), fail-closed on
  exhaustion; incidents open on a failing check and resolve only when a later run of a new
  version passes the linked regression and the current unseen acceptance check; the repair
  loop (edit → freeze → run → resolve). Authors the **remaining two bookshop families**.
- **Demo evidence:**
  - `python -m pytest tests/orchestrator tests/api -q` green: the (limit+1)th run POST is
    409 with no run row; two concurrent boundary POSTs create exactly one run + one draw
    per family; all three attempts consume distinct variants and failed/interrupted runs
    still consume reservations; an exhausted family refuses the whole run; an incident
    resolves only on a passing later run of the new version.
  - CLI: run a failing artifact → incident opens with a reason code; repair → new version
    → new attempt → incident resolves; a third distinct attempt draws a third variant.
- **Still mocked / missing:** inheritance/close (Slice 8); the six screens still the stub;
  assist absent.
- **Tests landed:** 24, 25, 26, 27 (budget controller-side, budget atomic under race,
  rotation draws unexposed variant, rotation exhaustion fail-closed), 34 (repair resolves
  only on passing later run). Completes earlier partials: 9 (reservation-retention
  clause — failed and interrupted runs still consume committed reservations), 18
  (future-stimuli clause), 23 (incident-reconstruction clause).
- **Authoring / config:** **sealed families 2 and 3** (`policy_exception`,
  `hostile_instruction`), 6 variants each, completing the 18-case bookshop inventory.
  Capacity invariant check (§7.1) must pass: 6 variants/family cover two bookshop shifts
  at attempt_limit 3. Operator reviews semantic independence of newly authored variants.
- **Authorization:** none.

### Slice 8 — Close → inheritance + **Test 1 offline pre-proof**

- **Delivers:** `close_shift` (atomic, idempotent; writes hash-chained `LIMIT_DECLARED`
  events derived from `CloseShiftFacts.declared_limits` only; unresolved OPEN incidents
  become `CLOSED_UNRESOLVED` rows inherited as incidents, never as `LIMIT_DECLARED`
  events; refuses in-flight runs); `open_next_shift` seeds from inheritance (latest
  version, decision/check files, unresolved incidents, declared limits, verified ledger
  summary); startup reconciliation (`reconcile_interrupted`). Then **executes the Test 1
  offline pre-proof** (SHIFTWORK_PLAN §9) on the `local_process` adapter — a recorded
  pre-proof, not the full Test 1 verdict (see §3).
- **Demo evidence:**
  - `python -m pytest tests/api tests/orchestrator -q` green: board after open equals the
    prior version + open incidents + unresolved limits + ledger summary; closing writes
    `LIMIT_DECLARED` events for declared limits and turns unresolved OPEN incidents into
    `CLOSED_UNRESOLVED` rows — the next board shows them as two distinct inheritances
    (`unresolved_limits` and `incidents`) — and is idempotent under concurrency and
    injected faults. A restart injected after a partial capture marks the run FAILED
    while its captured bytes and rotation draws remain byte-for-byte intact and zero
    checks/events are written.
  - **Test 1 offline pre-proof:** `python -m demos.test1 --adapter local_process`
    drives two consecutive bookshop shifts end to end — shift 1 consumes its attempts, hits
    an incident, repairs, closes; shift 2 inherits the same artifact, decisions and
    unresolved incidents and then draws a **still-unexposed** related case over its own
    attempts. The causal comparison (pre-repair fixture fails, repaired fixture passes,
    same held-out stimuli) runs on `local_process`, **never on `recorded`**, because
    `recorded` executes nothing and cannot show the artifact *caused* the outcome (§3 limit
    3). The process is **restarted** mid-arc and reconstructs artifact + state from tables.
    Every first-shift outbound surface is scanned for future customer wording — none
    appears. The command writes a **per-kill-condition verdict table** to
    `docs/plans/shiftwork/evidence/test1-central-mechanism.md` with the raw run, ledger
    replay and scan output, recording the result as **PRE-PROOF PASS / FAIL, conditional on
    the offline executor** — the isolation and provisioned-credential limbs are explicitly
    marked "deferred to Slice 14" (§3 limits 1–2). This is the offline go/no-go for the
    central mechanism; the full Test 1 verdict is recorded at Slice 14.
- **Still mocked / missing:** assist, Tavily, the six screens (still the stub page), real
  sandbox isolation. Two of Test 1's kill-condition limbs (hostile-code isolation; the
  provisioned-sandbox credential arm) are only partially adjudicated offline and are
  reserved for Slice 14 (see §3).
- **Tests landed:** 32 (open seeds from inheritance — full); 33 (close semantics — full,
  matching the revised Gate 3 spec: `LIMIT_DECLARED` for declared limits exactly once,
  unresolved OPEN incidents → `CLOSED_UNRESOLVED` rows inherited as incidents and never as
  `LIMIT_DECLARED`, the two distinct inheritances on the next board, in-flight close
  refused, repeated/concurrent closes return one shift + one event set, injected faults
  leave neither a partial close nor partial events); 40 (full budget preserves unseen
  inherited case — must fail against the old three-variant inventory). Completes earlier
  partials: 9 (restart-marks-FAILED and capture-retention clauses via
  `reconcile_interrupted` — restart after a partial capture: captured bytes and rotation
  draws retained byte-for-byte, run marked FAILED, zero checks/events written), 10
  (inheritance-seeds-match clause), 44 (declared limit "and inherited" clause).
- **Authoring / config:** none new (uses the 18-case bookshop inventory from Slices 4/7).
- **Authorization:** none. **This is the first proof slice; if the pre-proof FAILS, stop
  and apply the software-factory backtracking rule** — a failed central mechanism
  invalidates the product/architecture, not just a slice.

## 5. Phase B — client (offline, no credentials)

The six approved mockups (`mockups/`) are the UI source of truth. The client is plain
HTML/CSS/vanilla JS, no framework, no build step, served by the same process. Each
client slice replaces part of the stub page and is browser-checked at desktop and narrow
widths, reporting the actual URL/port.

### Slice 9 — Client: board + customer-shift screens (01, 03)

- **Delivers:** `01-shift-board` and `03-customer-shift` against the real API: the
  learner-owned artifact, contract, visible checks, change log, open incidents,
  unresolved limits, ledger totals and attempts remaining; the customer queue, the exact
  sample output, its supporting public record and the output→comparison→synthetic-event
  evidence chain. Every business-state component visibly renders "Synthetic scenario".
- **Demo evidence:** browser at the reported `localhost` port, desktop (1280) and narrow
  (640, 390): board reflects a real run from Slice 8; screen 03 shows the exact output
  body (base64 round-trips to the original bytes), the public record comparison with
  provenance, and the linked synthetic ledger event; console clean; no horizontal
  overflow; keyboard traversal reaches every control with a visible focus outline (this
  browser matrix — widths, console, overflow, keyboard — applies to all client slices).
  Removing a synthetic label fails the rendered check.
- **Still mocked / missing:** contract-authoring and repair screens (Slice 10), inherited
  and away screens (Slice 11); assist UI absent (Slice 12).
- **Tests landed:** 41 (partial: synthetic labels render; public-evidence projections keep
  provenance; base64-decoded bodies equal originals; displayed customer text matches the
  executed batch ordinal; sealed-only failures show reason codes without an expected value).
- **Authoring / config:** none new.
- **Authorization:** none.

### Slice 10 — Client: contract + repair screens (02, 04)

- **Delivers:** `02-owner-brief` (competing correctness stances, editable boundaries,
  structured visible-check builder, the fixed "May: Recommend with a clear label" copy
  displayed not editable) and `04-incident-review` (linked evidence, competing repair
  directions, the repair workspace, visible checks living in the artifact's check file).
- **Demo evidence:** browser at desktop and narrow widths: author a contract and one
  visible check on screen 02, freeze, run; trace an incident on screen 04 back to the
  customer request, choose a repair direction, edit the artifact, freeze, re-run; visible
  verdicts link to the learner's check id and every sealed result has a null
  `public_check_id`.
- **Still mocked / missing:** inherited and away screens (Slice 11); assist UI absent.
- **Tests landed:** 41 (partial: visible verdict links to learner check id; sealed results
  have null `public_check_id`; no future customer text returned; sealed sentinels injected
  into nested ledger payloads, incident records and logs never serialize; the incident
  view visibly renders "Synthetic scenario"; labels hold in empty and error states).
  **Test 41 is complete at Slice 10** — every clause of the §6 specification has landed
  across Slices 9–10.
- **Authoring / config:** none new (uses Slice 2 catalog).
- **Authorization:** none.

### Slice 11 — Client: inherited + away screens (05, 06) + away config

- **Delivers:** `05-inherited-shift` (restored artifact + history, the later case still
  sealed until execution) and `06-away-shift` (blank bike-cooperative artifact, reduced
  assistance, new families: future commitments, safety escalation, retried state-changing
  booking; learning value labelled unmeasured). Adds the **bike-cooperative
  `engagement_config`** and its away-shift assist/check-family configuration.
- **Demo evidence:** browser: screen 05 restores the same learner-owned artifact and
  history with the next case hidden until the run; screen 06 starts the bike co-op from
  the template with its own families and reduced assist config; the away shift has no
  inherited artifact.
- **Still mocked / missing:** live assist (Slice 12); real sandbox (Slice 14).
- **Tests landed:** 35 (away shift has no inherited artifact).
- **Authoring / config:** the **bike-cooperative contract catalog** and **9 sealed cases**
  (3 families × 3: `future_commitment`, `safety_escalation`, `retry_booking`), plus the
  away-shift `engagement_config` (total assist budget 2; allowed roles
  `STAKEHOLDER_DIALOGUE`, `HINT`, `DIAGNOSIS`). **Provisional assist budget 2 is
  challengeable here** (Gate 3 §10 item 12: no learner evidence backs 6/2).
- **Authorization:** none.

## 6. Phase C — external-service-gated (credentials separately authorized)

These slices need credentials that do not exist and are not authorized by Gate 4. They
are specified, not run, until the user separately authorizes the relevant key/service.

### Slice 12 — Nemotron assist gateway

- **Delivers:** `assist/gateway.py` bounded roles (stakeholder dialogue, scaffolding,
  hint, diagnosis, labelled patch proposal), every call logged to `assist_events`,
  permission checks per engagement config, atomic reservation against the shared total
  assist budget, patch accept/reject with no proposal-to-version link, refusal of sealed
  refs. The assist UI surfaces in the client. This is the **minimum path that satisfies
  the hackathon's runtime Token Factory inference call + NVIDIA open-source model
  requirement** (architecture §15, Best Apps and Agents track). It also produces the
  **model-feedback evidence pack** the submission form's model questions require:
  a rubric — correctness, usefulness, grounding, role adherence, boundary compliance —
  frozen **before** the first live call; for each recorded call the model ID, endpoint,
  date, prompt version, parameters, response, status, latency, errors/retries and usage;
  at least one representative and one adversarial case per claimed assist role (ten if
  all five roles are claimed — a reviewer-sufficiency threshold, not an organizer rule);
  comparison runs of the identical frozen cases on a named comparison model, or an
  honest "not compared"; and a separate builder-experience log (setup friction,
  documentation gaps, improvement wishes). Form answers are assembled only from this
  pack, never from memory.
- **Demo evidence:**
  - `python -m pytest tests/assist -q` green: every call writes an attributed
    `assist_events` row; version freeze records only aggregate counts + accepted-patch
    count + learner-declared patch use with no proposal-to-version FK; requests
    referencing sealed refs/expected values/evaluator logic are refused and prompts contain
    no sealed paths; `PATCH_PROPOSAL` and `SCAFFOLDING` are 403 for the bike co-op; all
    permitted roles share one total budget and concurrent boundary calls cannot exceed it;
    a failed post-reservation model call still consumes its unit; one patch decision is
    durable and idempotent.
  - Live (only with `NEBIUS_API_KEY` authorized): request a hint/diagnosis from a real
    Nemotron model on a bookshop incident and show the attributed, bounded reply. The
    live run writes the model-feedback evidence bundle to
    `docs/plans/shiftwork/evidence/model-feedback.md`; the submission form's 1–10
    ratings, comparison and experience answers are assembled from that bundle at
    Slice 16, never from memory. Until a key is authorized the gateway is demonstrated
    against recorded assist responses.
- **Still mocked / missing:** recorded assist responses until credentials are authorized;
  the model id (`nvidia/nemotron-3-super-120b-a12b`) and availability are rechecked live.
- **Tests landed:** 36, 37, 38 (assist logged/attributed, cannot touch sealed/evaluator,
  away-shift role restrictions), 46, 47 (budget applies across roles; patch decision +
  summary are minimal). Completes earlier partials non-vacuously: 16 (sentinel scan now
  includes real assist prompts), 17 (the `assist/` arm of the sealed import graph), 18
  (the prompt-arm clause — sealed specs/expectations absent from every assist prompt
  before, during and after execution — now re-runs non-vacuously; re-run again against
  real provisioning at Slice 14).
- **Authoring / config:** the bounded **assist prompts/role definitions** must be authored;
  no sealed content may enter any prompt. The **model-feedback rubric** and the named
  comparison model must be frozen before the first live call. **Assist budgets 6/2 are
  challengeable here.**
- **Authorization:** `NEBIUS_API_KEY` for live model calls; can be built and tested
  against recorded responses without it. Per the user's 2026-09-17 decision, a bounded
  early availability smoke check (key valid, model reachable) is pre-authorized to run
  once the user provides a key, with its raw result kept as evidence; the full live
  gateway demonstration still lands here.

### Slice 13 — Token Factory capability spike (specified, gated)

- **Delivers:** runs the bounded §9 spike probes and records raw evidence: file transfer
  in/out of a sandbox, outbound networking from a sandbox, secret injection + scoping,
  timeouts/resource limits, ingress posture, and cost/latency/entitlements. Resolves
  architecture §16 unverified items and decides whether **ADR #4 (execution topology)**
  can be promoted. Also informs the Slice 16 hosting decision (§16 item 6: whether any
  Nebius service hosts an arbitrary container web app for a demo URL).
- **Demo evidence:** a written spike report in `docs/plans/shiftwork/evidence/` with the
  raw probe output per §9 question and a PASS/FAIL per row; an explicit ADR #4
  promotable / not-promotable verdict.
- **Still mocked / missing:** this is a spike, not product code; no adapter is built here.
- **Tests landed:** none directly; produces the evidence Slice 14 and ADR #4 require.
- **Authoring / config:** none.
- **Authorization:** `NEBIUS_API_KEY` / `CONTREE_SESSION`. A bounded early sandbox
  entitlement/I-O smoke check (§11 decision 6) is pre-authorized to run once sandbox
  credentials are provided, retiring the execution-access unknown before the full spike.
  **Kill handling (Gate 3 §9):**
  a failed probe that invalidates an approved isolation/inference/execution assumption
  **stops the dependent slice and triggers backtracking** — update the affected gate
  document and obtain re-approval. ADR #4 is created only after this evidence and only
  with separate authorization (ADR file creation was not authorized at Gate 2).

### Slice 14 — Real tokenfactory executor adapter + full Test 1 verdict

- **Delivers:** `executor/tokenfactory.py` implementing the same `ExecutorAdapter`
  Protocol against the verified spike path; passes the shared conformance suite. **Re-runs
  the full Test 1** on the real adapter and records the **full Test 1 PASS/FAIL verdict**
  here, adjudicating the two limbs the Slice 8 offline pre-proof deferred — hostile-code
  isolation and the provisioned-sandbox credential arm. The suite includes a **canary
  hostile artifact** — a fixture that attempts to enumerate and read forbidden env vars,
  mounts, files and controller markers — which must produce zero findings before the
  slice verdict is recorded.
- **Demo evidence:** `python -m pytest tests/executor -q` with test 29 and test 50's
  `tokenfactory` arm no longer skipped and passing (same conformance behaviors as
  recorded/local against a real sandbox; the provisioned sandbox env exposes no controller
  credentials and only the scoped `InferenceGrant` is reachable), and tests 16–18 re-run
  against the real adapter (sentinel scan over real sandbox payloads, responses and logs;
  the canary probe log must be empty); `python -m demos.test1
  --adapter tokenfactory` appends the full Test 1 run to
  `docs/plans/shiftwork/evidence/test1-central-mechanism.md`, upgrading the Slice 8
  per-kill-condition table from PRE-PROOF to a FULL verdict.
- **Still mocked / missing:** none for the executor path; depends entirely on Slice 13.
- **Tests landed:** 29 (tokenfactory conformance — full, must pass before this slice
  closes); 50 (completes the `tokenfactory` provisioned-sandbox arm — the credential limb
  of Test 1's "hidden cases or credentials are reachable" kill condition is now fully
  adjudicated); 16, 17, 18 (re-run against the real adapter: sentinel scan over real
  sandbox payloads, responses and logs; sealed import graph; provisioning manifest), plus
  the canary hostile artifact described above. Records the **full Test 1 verdict** (the
  offline pre-proof was Slice 8).
- **Authoring / config:** none beyond what the spike dictates.
- **Authorization:** depends on Slice 13 credentials/evidence; deployment of any hosted
  artifact is separately authorized.

### Slice 15 — Tavily curation + ablation

- **Delivers:** the offline `curation/pipeline.py` (discover → human verify → freeze;
  never imported by `app.py`) and `curation/ablation.py` three-arm historical replay
  (frozen / known-page polling / Tavily) against the §8.1 pre-registered corpus, with the
  pre-registered kill thresholds. Produces the **Test 3** verdict. The shipped CLI's live
  `discover()` call is the qualifying functional Tavily call for the bonus (user decision,
  §11 decision 5): it runs, and the form is answered "yes", only after the mandatory
  product path; the Test 3 KEEP/DROP verdict governs the pitch, not the fact of the call.
- **Demo evidence:** `python -m pytest tests/curation -q` green: `app.py` import closure
  excludes `curation`; quarantined sources have no verifier/fixture, verified sources
  require a human verifier, only verified+fixture sources become frozen; the corpus
  manifest is rejected unless domains/window/selection-rule/budgets/kill-thresholds are
  frozen before any comparator output exists; fixtures cannot be marked
  Tavily-attributable without human verification + executable-change criteria. Then the
  ablation run outputs `KEEP_TAVILY_CLAIM` or `DROP_TAVILY_CLAIM` written to
  `docs/plans/shiftwork/evidence/test3-tavily-ablation.md`.
- **Still mocked / missing:** none; this is offline tooling. It can kill the Tavily prize
  claim without killing Shiftwork (brief §9 Test 3).
- **Tests landed:** 39 (curation never imported by runtime), 48, 49 (ablation manifest
  pre-registered; kill rules fail closed).
- **Authoring / config:** the **12-event Tavily corpus manifest** (3/domain across
  `cpsc.gov`, `gov.uk`, `ec.europa.eu`, `productsafety.gov.au`; 2 known-page + 1
  structural each) with archived before/after evidence and canonical constraints. §8.1
  fixes domains, window, selection rule and thresholds — **implementation may not tune
  them after seeing comparator output.** If the manifest cannot supply all 12 with
  authoritative evidence, the ablation does not run and no Tavily claim is made.
- **Authorization:** `TAVILY_API_KEY` for the discovery arm; human verification is
  operator work.

## 7. Phase D — submission

### Slice 16 — Submission packaging (test build + demo video)

- **Delivers:** the submission artifacts the rules require (HACKATHON_REQUIREMENTS): a URL
  to a working demo, hosted application, **or test build** — Option A's is a **direct
  downloadable test-build URL** (a tagged release archive a judge can fetch and run
  offline); a public GitHub/GitLab/Bitbucket repository for judging and testing; a
  top-level open-source license; a README with setup + run instructions; the Nemotron /
  Token Factory usage explanation; tool feedback whose model-quality, comparison,
  recommendation and experience answers derive strictly from the Slice 12 evidence bundle
  (the Nebius-capabilities answer uses actuals — Token Factory API access, model
  identifier, authentication setup, observed latency/reliability — never an invented GPU
  instance type); track selection; project description;
  and a **<3-minute demonstration video uploaded to YouTube, publicly visible and linked
  in the submission**. The project must remain **available to the Sponsor, Administrator
  and judges free of charge and without restriction until the judging period ends
  (2026-12-15 12:00 PM PT)**.
- **Demo evidence:** the packaged submission: a judge can fetch the tagged release archive
  (or follow the README) to run the offline deterministic core locally with Python +
  SQLite and no credentials, or reach a hosted URL if Slice 13 verified one is possible;
  the YouTube video is public, under three minutes, shows the central loop and
  inheritance, and is linked in the submission; the repo, license and testing instructions
  are present; if any part is private, login credentials are in the testing instructions.
- **Still mocked / missing:** depends on prior slices; a hosted URL is a stretch goal, not
  a guaranteed deliverable (see §8). The offline downloadable test build is the committed
  baseline.
- **Tests landed:** none new; runs the full suite green before packaging, including
  test 51 (clean-environment install-and-run) from a freshly created environment.
- **Authoring / config:** README, license, description, video script, the tagged release
  archive, and the YouTube upload.
- **Authorization:** any deployment / hosted URL is separately authorized; the public repo
  push, the YouTube video upload and making the build publicly downloadable are external
  actions requiring explicit go-ahead. The free-availability-until-2026-12-15 obligation
  is a submission commitment the user accepts at submission.

### Slice 17 — Hosted deployment (conditional: only if Option B is selected at the Slice 13 exit)

- **Delivers:** a container image of the controller + client deployed to the Nebius
  service the Slice 13 spike verifies can host an arbitrary container web app, reachable
  at a public HTTPS URL. Persistence/reset handled honestly: if the service removes
  endpoint container storage on stop/delete, the deployment uses mounted durable storage,
  or is explicitly documented as a resettable demo whose seeded state is restored on
  start. Restart testing (the app survives a service restart and reconstructs state from
  storage), basic monitoring/logging of the hosted instance, the downloadable build kept
  visible in the submission as fallback, and funded availability through 2026-12-15.
- **Demo evidence:** the public URL serves the client; a judge can open a shift, run the
  recorded path and see the board; a service restart leaves state intact (or exhibits the
  documented reset); the submission links both the hosted URL and the downloadable test
  build.
- **Still mocked / missing:** nothing mocked; this slice exists only if the spike proves
  feasibility. If it does not, Option A remains the whole submission and this slice is
  dropped, not stubbed.
- **Tests landed:** none new; test 51 re-run inside the container image.
- **Authoring / config:** the container build, the deployment configuration and the
  hosted-URL README section.
- **Authorization:** creating the container, deploying it, provisioning storage and any
  Nebius service action are external actions requiring explicit separate authorization.

## 8. Demo URL / hosting decision (Gate 3 §11 deferral)

The architecture is local-first; the hackathon requires "a URL to a working demo,
hosted application, **or test build**" (HACKATHON_REQUIREMENTS, Submission requirements).
Three options, in increasing risk and dependence on unverified facts:

- **Option A (committed baseline): downloadable test build.** Public repo + README + a
  **direct downloadable test-build URL** (a tagged release archive) + a public YouTube
  demo video; judges fetch the archive and run the offline deterministic core locally with
  Python + SQLite, no credentials. The rules accept "a URL to a working demo, hosted
  application, **or test build**" and separately require judge access "through a website,
  functioning demo, or test build" — packaging the test build behind a URL a judge can
  fetch directly satisfies the literal "URL ... or test build" wording and retires most of
  the interpretation risk; Option B exists to retire the rest.
  **User-confirmed as the plan of record on 2026-09-17.**
- **Option B (stretch): hosted controller on Nebius.** Only viable if Slice 13 verifies
  §16 item 6 (that some Nebius service hosts an arbitrary container web app). If it does,
  a hosted URL strengthens "working demo." If it does not, fall back to Option A — the
  design must not silently depend on it (architecture §14). Option B is selected at the
  Slice 13 exit only if all five hold: the container works without redesign; SQLite
  persistence (or a deterministic, documented reset) is proven; public HTTPS access
  survives restart testing; uptime is funded through 2026-12-15; and the downloadable
  build stays visible as fallback. Slice 17 then delivers it.
- **Option C (not planned): hosted learner sandboxes with public ingress.** Architecture
  §16 item 1 does not document public sandbox ingress and the design does not require it;
  not pursued unless the spike unexpectedly shows it is available and useful.

Decision point: after Slice 13. Until then Option A is the safe plan and no slice
silently assumes a hosted URL. **Conditional slice:** if the Slice 13 exit selects
Option B, Slice 17 (§7) becomes active and carries the container build, deployment,
persistence/restart handling, monitoring, fallback-to-downloadable and funded-
availability-through-2026-12-15 requirements; if not, Slice 17 is dropped and Option A
remains the whole submission.

## 9. Schedule, critical path, and top risks

Solo builder; deadline 2026-10-30 10:00 PT (≈6.5 weeks from 2026-09-16). Rough
sequencing, not a promise — each slice ends with the user re-steering:

- **Weeks 1–3:** Phase A (Slices 1–8), reaching the Test 1 offline pre-proof. No credentials needed.
  This is the highest-value, lowest-dependency work and is done first.
- **Weeks 3–4:** Phase B (Slices 9–11), the six screens against the proven core.
- **Weeks 4–6:** Phase C (Slices 12–15) **as credentials are authorized**. Slices 12–14
  (assist; spike + real adapter) are the submission-critical path — Slice 12 carries the
  hackathon's runtime-inference requirement and Slices 13–14 the only path that executes
  learner-edited artifacts. An unrun or failed Slices 13–14 is a submission no-go, not a
  schedule trim. Slice 15 (Tavily) is evidence-gated and may not fully resolve before the
  deadline.
- **Week 6:** Phase D (Slices 16–17), packaging against the Option A baseline; Slice 17
  only if the Slice 13 exit selected Option B.

Top risks, leading with blockers:

1. **Credentials are the hard gate on Phase C and the hackathon's tech requirement — and
   a hard no-go for submission.** The rules (HACKATHON_REQUIREMENTS, "What you must do")
   require the application to make **at least one runtime call to the Nebius Token Factory
   inference API, or run on Nebius AI Cloud compute** (Serverless Jobs/Endpoints or
   DevPods), **and use at least one NVIDIA open-source model**; Stage One is pass/fail on
   "reasonably apply[ing] the required hackathon APIs." The Slice 12 Nemotron assist call
   is that qualifying runtime inference call. **Hard no-go: without at least one recorded
   qualifying runtime Token Factory inference call (or Nebius AI Cloud compute execution)
   using an NVIDIA open-source model, the entry is non-compliant and FAILS Stage One — it
   is not merely a weaker submission.** That makes `NEBIUS_API_KEY` for the Slice 12 live
   call a submission blocker, not an enhancement. Equally a hard no-go: if Nebius
   sandbox / `CONTREE_SESSION` access is **never** authorized, the Slice 13–14 spike and
   real adapter do not run and no shipped component can execute learner-edited artifacts
   (Gate 3 §3.3: `recorded` replays bytes and executes nothing; `local_process` accepts
   only pinned operator fixtures). That is not a weaker story — it is not the working
   learning product, so the submission hard-stops or the product backtracks. **Resolved
   2026-09-17:** the user authorized bounded early availability smoke checks for both
   credentials (§11 decisions 1 and 6) once credentials are provided, with the full live
   call at Slice 12. The remaining action is to provide `NEBIUS_API_KEY` and
   `CONTREE_SESSION`; until then both submission-critical access unknowns (Token Factory
   inference access and sandbox execute/transfer access) stay unverified.
2. **The spike (Slice 13) may fail and force backtracking.** File transfer / egress /
   secret injection into a sandbox are unverified (architecture §16, §18 item 1). A
   failure that invalidates an approved isolation or execution assumption stops Slice 14
   and reopens Gate 2/3 — now a submission-level stop since Slices 13–14 sit on the
   mandatory packaging path, not just a code change.
3. **Sealed-inventory authoring is real, unautomated work.** 27 cases (18 bookshop across
   Slices 2/4/7, 9 bike co-op in Slice 11) plus request batches, shop snapshots, recorded
   transcripts, trusted fixtures, contract catalogs and mission fixtures must be authored
   and reviewed for semantic independence. This is the largest hidden cost in Phase A and
   gates Test 1.
4. **Tavily ablation may not complete or may kill the prize claim.** The 12-event corpus
   needs archived before/after evidence; if it cannot be assembled, no Tavily claim is made
   (Slice 15). This can remove a prize angle without removing Shiftwork.
5. **Provisional config numbers are unvalidated.** attempt_limit 3, assist budgets 6/2,
   rotation group sizes and response-time limits are challengeable at Slices 2/7/11/12;
   changing them after dependent inventory is authored breaks the capacity invariant.

## 10. What Gate 4 approval does and does not authorize

Approving this plan authorizes building the slices **in order, one at a time**, each
ending in the demonstrated result above, with `00-status.md` updated and a
"Continue to slice N+1, or re-steer?" pause after each. It does **not** authorize:
installs or dependencies; credentials or any external service (`NEBIUS_API_KEY`,
`CONTREE_SESSION`, `TAVILY_API_KEY`); running the Slice 13 spike or the Slice 15
ablation; commits, pushes, tags or branches; deployment or any hosted URL; participant
outreach or the manual learner kit; or ADR #4 file creation. Each of those remains a
separate explicit user authorization (the §11 decision 1 availability smoke check is one
such recorded authorization, conditional on the user providing a key). Scores remain
conditional forecasts (current 27/40); no slice may inflate them, and a FAILED Test 1
pre-proof at Slice 8 triggers backtracking, not a softened claim. If learner-edited
artifacts cannot execute safely, the submission hard-stops (or the product backtracks)
rather than presenting the offline fixture loop as the full product.

## 11. Resolved decisions (user answers, 2026-09-17)

The four original questions previously listed here were answered by the user on
2026-09-17, and decisions 5–6 were resolved during the same day's Gate 4 review round.
These answers shape the plan; they are not themselves Gate 4 approval, which the
user granted separately later the same day.

1. **Credential timing for Slice 12 (assist gateway).** The user authorized a bounded
   early availability smoke check (key valid, model reachable) to run once a key is
   provided, retiring the submission-critical access unknown early; the full live
   gateway demonstration still occurs at Slice 12. Until a key is provided, the gateway
   is built and tested against recorded responses only.
2. **Demo hosting.** Confirmed: Option A (downloadable test build) is the committed
   baseline plan of record. Option B (hosted URL) is strictly optional and pursued only
   if the Slice 13 spike verifies that a Nebius service can host the app; no slice
   silently assumes a hosted URL.
3. **Provisional config numbers.** Accepted as starting values: attempt_limit 3,
   bookshop rotation_group_size 6 per family, assist budgets 6 (bookshop) / 2 (away).
   They remain challengeable at Slices 2/7/11/12, but changing them after case inventory
   is authored is expensive (capacity invariant, Gate 3 §7.1).
4. **Sealed-inventory authorship.** The agent drafts all 27 sealed cases and their
   fixtures; the user reviews every case and expected answer before sealing. The
   agent's own review is not evidence — a second LLM is not an independent oracle, so
   the user is the only valid reviewer.
5. **Tavily prize (user decision, 2026-09-17).** The Tavily bonus is pursued through the
   already-planned operator-run curation CLI (Slice 15): its live `discover()` call is
   the qualifying functional runtime Tavily call. No architecture §11 / test 39 backtrack
   — the curation pipeline stays offline tooling, never imported by `app.py`, and the
   submission form is answered "yes" only after the call actually ships. The Test 3
   KEEP/DROP verdict governs the pitch, not the fact of the call. No organizer
   clarification email is sent.
6. **Execution path is submission-critical (user decision, 2026-09-17).** Only the
   verified Sandbox path can execute learner-edited artifacts (Gate 3 §3.3), so Slices
   13–14 sit on the mandatory packaging path and Slice 16 depends on Slices 1–14. A
   bounded early sandbox entitlement/I-O smoke check is pre-authorized to run once
   sandbox credentials are provided (mirroring decision 1); if execution access never
   materialises, the submission hard-stops or the product backtracks rather than
   presenting the offline fixture loop as the full product.
