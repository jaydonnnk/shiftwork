# S46 transient proposal and patch format correction

Status: APPROVED by the user on 2026-10-25. The named live action is also approved.
The US$5 ceiling covers all charges, so Sandbox pricing must be verified before execution.
The official beta pricing statement was subsequently verified. The first named
action stopped before a usable coach proposal. Its allowance is closed; see
[s46 checkpoint](slice46-checkpoint-2026-10-25.md). The approved design below stays in force.

## Why the approved program design needs this correction

The S46 product contract stays unchanged. The following implementation contracts
do not yet express it:

- `Run.artifact_version_id` and its database foreign key require a saved version.
  `create_diagnostic_experiment` loads that version before reserving a run.
  S46 instead requires a transient proposal, without saving a learner version.
- `CandidateRef` requires an artifact version ID. Reporting the base version as
  the tested proposal would misidentify the executed source.
- `request_assist` stores the whole free-form model response as `proposed_patch`.
  The gateway explicitly permits pseudocode. There is no patch format, source
  snapshot, application rule or API route for the approved proposal-run method.
- `authorship_json` exists, but the domain, repository and version API do not yet
  implement the approved `VersionAuthorship` object. The source API currently
  uses `authorship` for the legacy template/learner label.

These are design gaps, not failed live evidence. No inference or Sandbox
operation has been attempted for S46.

## Proposed Gate 3 additions

### 1. A bounded patch against frozen public source

For `PATCH_PROPOSAL`, the controller freezes the learner's current draft and its
existing base version before calling the coach. The base supplies the contract,
not the proposal's source identity. No artifact version is created.

The coach receives the existing public investigation and captured request/reply,
plus a labelled public source excerpt. For the current Bellwether service the
excerpt is its `ask_for_plan` function. The prompt identifies the omitted source
as unavailable to the coach. Other learner code must fit the existing input cap
or the request refuses before a call; source is never silently truncated.

The reply is strict JSON with exactly `old` and `new` string fields. It requests
one exact replacement inside `service.py`. `old` must be nonempty and occur
exactly once in the frozen source. No path, shell command, host import, patch
library, model-written application code or fuzzy match is used by the controller.
`new` must change the source. Other draft files are preserved byte for byte.
The controller applies that one replacement deterministically and retains the
resulting files. Malformed or inapplicable replies fail visibly, consume the
assist call, and never receive a retry or fallback.

The UI labels both the proposed change and the resulting source as coach output.
`proposal_source_sha256` hashes the resulting UTF-8 `service.py` bytes. The
artifact hash covers all resulting files and the existing contract/catalog.
The exact retained resulting bytes execute and, on acceptance, enter the draft.
Model text supplies no grade or eligibility decision.

The existing 8 KiB input, 1,024 output-token and 20-second assist limits remain.
No reasoning-off option is added to the coach protocol.

### 2. Supplemental storage that preserves historical rows

Add idempotent tables in `shiftwork/store/migrations/v6_tables.sql`:

| Table | Stored contract |
| --- | --- |
| `assist_proposal_snapshots` | One row per patch event. Event ID primary/foreign key, base version ID, frozen base files and their hash, resulting files and artifact/source hashes. The base is immutable; result fields can complete once. |
| `assist_proposal_runs` | Event ID primary key and run ID unique foreign key. Inserted once in the same transaction as the diagnostic reservation. Immutable thereafter. |

`AssistEvent.diagnostic_run_id` and `proposal_source_sha256` are loaded through
these relations. No ALTER, backfill or update of accepted historical event,
version, run, selection or ledger rows is needed. Old prose proposals remain
historical and cannot be treated as runnable patches.

### 3. Reuse diagnostic execution without inventing a saved version

Extend `CandidateRef` to identify exactly one saved version or one proposal
event. A proposal has `artifact_version_id=null`, its event ID and its retained
artifact hash. Saved-version serialization and canonical hashing retain their
existing byte shape, with no added null field in old candidate payloads.

The internal run retains the existing base-version foreign key solely for its
contract. Proposal execution resolves the retained proposal files, verifies both
hashes, constructs a transient artifact in memory and uses the existing
diagnostic executor and deterministic assessment. Its public candidate and trial
references identify the proposal, never claim that the base version was tested.

`run_assist_proposal` reserves one public repetition. Its transaction checks
complete owned investigation, complete applicable patch, isolated configuration,
no prior proposal run and a free diagnostic slot. It reserves the slot, context,
run and event/run link together before executor work. Failed execution consumes
both the run allowance and the diagnostic slot. Repeated requests refuse.

Execution independently rejects a proposal linked to `recorded` or
`local_process`, including a forged or changed queued adapter. There is no local
fallback. The existing guarded execution claim prevents duplicate execution.

Add `POST /api/shifts/{shift_id}/assist-events/{event_id}/run`, with no learner
executor/source override. It uses the configured executor and a fresh bounded
diagnostic meter. It queues the reserved run and returns the existing diagnostic
experiment view, extended with proposal references. Reads use the existing
experiment and run endpoints.

This run reserves no protected cases. It is always ineligible, cannot be chosen
or operated, and writes no business ledger. All obligation-39 leak checks and
positive serialized controls apply to its inputs, responses and errors.

### 4. Atomic draft-only acceptance and attribution

Acceptance validates an open shift and a complete applicable proposal. It checks
that the draft still matches the frozen base, then copies the retained resulting
files and records the one decision in a single transaction. A changed draft
refuses instead of overwriting later learner edits. Rejection changes no draft.
Acceptance before a diagnostic run is permitted by the existing contract; the
learner decides whether to run the proposal. No save, freeze or selection follows
automatically. A second decision refuses, including after process restart.

Implement `VersionAuthorship` in the domain and persist it in the existing
`artifact_versions.authorship_json` when the learner explicitly saves a version.
Count each applicable generated proposal seen/accepted once, carrying inherited
disclosure forward and avoiding another increment on repeated saves. Expose the
object on the version API and as `version_authorship` on the source API, preserving
that API's legacy `authorship` label. Historical null disclosure stays unknown.
The new freeze request can carry the approved learner declaration, default false.

Acceptance does not change `learner_declared_generated_patch_use` on behalf of the
learner. Seen/accepted counters come from stored events, not caller-provided counts.
The saved version must pass S45 comparison and a separate explicit choice.

## File ownership and proof

Use the approved existing files: assist gateway, domain models, repository,
`v6_tables.sql`, orchestrator, experiments, API schemas/routes and plain JS client.
No new framework, dependency, provider setting, protected fixture or host executor.
Add focused API/storage tests under `tests/assist`, including restart/concurrency
controls, and a bounded mutation driver under that test folder.

Obligations 64 to 67 each retain their specified assertions. Independently fault
investigation, once-only reservation, diagnostic cap, each unsafe adapter,
fallback, source/hash binding, leak refusal, ineligibility, draft-only acceptance
and attribution. Require intended assertion failures, fresh bytecode caches,
byte-identical restoration and passing clean/restored controls.
Existing obligations 5, 7 and 8 remain mandatory. Browser proof covers the actual
proposal, one diagnostic report, acceptance, explicit save and comparison at
desktop/mobile and 100%/200%. S47's parallel checkout remains untouched.

## Verified model and proposed live action

On 2026-10-25, the authenticated `GET /v1/models` returned
`nvidia/nemotron-3-super-120b-a12b`. The official
[Nemotron model page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference)
lists US$0.30 input and US$0.90 output per million tokens for Super, and US$0.06
input and US$0.24 output for the existing Nano service model.
The model list confirms availability, not inference success or actual billing.

The user approved S46 and preapproved live calls with a US$5 spending ceiling.
The proposed bounded demonstration is one Super coach call, two single-repetition
Nano diagnostics of two public requests each, and one S45-shape Nano comparison
with at most 42 calls and 24 Sandbox operations. Total: at most 47 inference calls
and 26 Sandbox operations, with no retry, tuning or automatic selection.

Using the existing conservative reservation of 32,768 input and 1,024 output
tokens per call, that reserves US$0.11249664 inference: US$0.010752 Super and
US$0.10174464 Nano. All failed attempts count. Actual billing and Sandbox rates
remain unknown. A US$5 all-in hard ceiling cannot be guaranteed without the
Sandbox rate. No billed action follows from this proposal while that distinction
and the scoped Gate 3 correction await approval.

Approval of this document applies the stated correction to Gate 3 and its
supporting brief. It does not approve publication, merge, deployment, operation,
S47 implementation, fixture changes or installation. S46 acceptance remains a
separate decision after evidence.
