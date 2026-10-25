# S46 coach context correction

Status: APPROVED, 2026-10-25 Asia/Singapore.
The user replied "Yep, I approve." to this scoped Gate 3 correction and its
offline implementation/proof. Gate 3 is re-approved for this context change.
No new live or spending authority is granted. All three old actions stay closed.
The earlier approved S46 implementation remains in place. The approved context correction is now implemented offline, with proof
still incomplete at the current context checkpoint. See
[the implementation record](slice46-coach-context-progress-2026-10-25.md). No provider setting changed.

## Approved implementation checkpoint

The native receipt reported 164,157 context input tokens before the next phase,
near this checkout's 175k working limit. The session records approval and leaves
implementation unstarted rather than entering an unbounded proof phase.
The earlier 300k extension is historical and does not apply to this session.

The approved work remains:

- [x] Refresh preservation and the focused baseline in fresh owned receipt/cache
  directories. Existing audit receipts remain unchanged.
- [x] Add failing behavioral tests of the actual outbound coach request for exact
  source definitions, bound whitelisted trace, unavailable states and byte caps.
- [x] Correct `proposal_source_excerpt` in `shiftwork/assist/gateway.py` and
  PATCH_PROPOSAL prompt assembly in `shiftwork/orchestrator.py`. The existing
  `repo.list_observations(conn, run_id)` returns ordered ExecutionObservation
  models. No API, database, executor or client change is proposed.
- [x] Prove every new guard with an independent source fault, its intended
  assertion, byte-identical restoration and a passing restored control. Extend
  `tests/assist/test_proposal.py`, `tests/assist/test_gateway.py` and
  `tests/assist/proposal_mutations.py` as needed, preserving inherited cases.
- [x] Run focused and full offline Python/Node checks with the exact installation
  node deselection. Preserve the live-only skip and original evidence stores.
- [x] Prove the continuous browser workflow with authored doubles at desktop/mobile
  100%/200%, without executing service code on the host.
- [x] Complete a separate zero-call live preparation before requesting fresh live
  authority. No prior call, spending ceiling or unused balance is reusable.

These steps implement the approved scope. No additional generic confirmation is
needed. A changed gate decision or a new live action still requires approval.

## What the retained evidence establishes

The second action's proposal event is `assist-bookshop-shift-01-1` in
`/tmp/shiftwork-s46-20261025/proposed-live-v2/proposal-generated.db`.
Its investigation references `run-0001`, request ordinal 1, in that store.
These IDs must never join another store's history.

The captured HTTP 200 response contains no task results. Its controller-verified
INFERENCE_RESULT records `plan=null`, `plan_failure=SCHEMA_INVALID`, finish reason
`length` and 1,024 output tokens. Both collection and alternative assessments
record REQUIRED_TASK_MISSING. This establishes that the controller supplied no
valid task plan for the source request. It does not explain why the provider
failed, or prove failure under today's service protocol.

The retained coach request supplies that empty HTTP response, the operator's
cause and falsifier, and only `ask_for_plan`. It omits the verified plan failure,
the task/tool definitions referenced by the function and its `answer` caller.
The request also tells the coach to propose a small planning-function repair.

The actual patch changes `return reply.get("plan"), ...` to
`return reply.get("plan") or [], ...`. The omitted caller already iterates
`plan or []`. Static inspection establishes those expressions, not execution
equivalence. No generated service code ran on the host. Neither the passing
diagnostic nor the later comparison proves that this patch repaired the failure.
Whether the missing context caused the weak proposal remains a hypothesis.

## Proposed correction

Keep the one-patch product, frozen draft, exact old/new JSON application, once-only
isolated diagnostic, deterministic assessment, draft-only acceptance, explicit
save, authorship disclosure and ordinary S45 qualification unchanged.

For PATCH_PROPOSAL, supply these additional public inputs:

1. Exact top-level `TASK_VOCABULARY`, `TOOLS`, `ask_for_plan` and `answer`
   definitions from the frozen draft's `service.py`, in source order. Preserve
   their original bytes and label all other source unavailable. Use AST only to
   locate boundaries, never to evaluate, import, normalize or execute source.
2. The historical source run ID, saved version ID and artifact hash, explicitly
   distinguished from the current frozen draft. Reuse the existing investigation
   ownership and source-request binding before reading observations.
3. A fixed whitelist from the matching controller-verified INFERENCE_RESULT:
   `source`, `request_ordinal`, `model`, `plan`, `plan_failure`, `finish_reason`
   and `output_tokens`. Match both stored and payload request ordinals, the exact
   source run, observation kind and controller provenance. Never read or forward
   `raw_payload_ref`, provider response text, reasoning, grades, protected checks
   or other observation fields into this context.

When the source has no unique complete set of those top-level definitions,
supply the entire source only if it fits. Otherwise refuse before any call.
Never silently omit a selected definition or truncate text to fit. When the
historical inference observation is absent, ambiguous or malformed, label it
unavailable with a fixed controller message. Do not select an arbitrary row,
substitute another request or infer a plan from the HTTP response.

Amend the trusted PATCH_PROPOSAL instruction to permit the supplied public source
and verified public inference result as evidence, and to state that a successful
diagnostic does not prove a repair. Keep HINT and other roles' evidence authority
unchanged. Continue treating learner text as untrusted and the cause as a
hypothesis. The coach supplies a proposal, never a grade or eligibility verdict.

Retain the exact Super and Nano models, the 8 KiB input cap, 1,024 output-token
cap and 20-second coach deadline. Add no coach reasoning-off option, retry,
larger limit, lexical fallback, hidden task completion or second-model oracle.
All existing public privacy checks apply before reservation and transport.

## Offline size specimen and alternatives

The read-only audit reconstructs the actual patch and prompt from their retained
rows, verifies the source expressions with AST and writes an unapproved candidate
request. It executes no service code and makes no provider or Sandbox request.

- Existing request plus current system instruction: 2,950 UTF-8 bytes.
- Proposed specimen plus amended system instruction: 6,199 bytes, below 8,192.
- Existing investigation/question plus the whole source and current system
  instruction: 14,332 bytes, already over the cap.

These are one exact specimen's measurements, not a guarantee for arbitrary
learner drafts. Production must count the complete actual system and user text
before reservation and again at the gateway. The specimen keeps the historical
operator question; it is not an approved future live request.

Candidate user-text SHA-256:
`c2889f2764c7415b453efd6a18eacab3a9b38bcaa96a997d4906050117d8e3e9`.
The private audit also retains the exact candidate system text and its hash.

Keeping the planner-only context preserves the reproduced omissions. Sending
the entire source cannot fit this case. The proposed selection supplies the
referenced vocabulary and immediate caller while retaining the existing cap.
It may still produce an ineffective patch. No semantic no-op detector or model
judgment is added as a correctness gate.

## Implementation and proof after approval

Use `shiftwork/assist/gateway.py` for exact source extraction and trusted patch
instructions, and `shiftwork/orchestrator.py` for the bound public observation
and prompt assembly. Reuse `repo.list_observations` after inspecting its contract.
No table, API route, client, fixture, framework or executor change is proposed.
Extend the existing assist tests and mutation driver only where needed.

Before implementation, record the focused baseline. Then independently prove:

- The four original definitions and historical trace reach the actual gateway
  request, while the HTTP response and learner commitments remain unchanged.
- Each run, ordinal, kind and provenance mismatch excludes the unrelated trace.
  Missing, malformed and duplicate observations produce the explicit unavailable
  label. A failure at a different assertion is not proof of any of these guards.
- Syntax errors, missing definitions and duplicate names use the specified
  whole-source/refusal rule. Exact Unicode and newline anchors remain applicable.
- Exceeding 8 KiB refuses without a provider call or budget reservation. No
  partial context can pass through either input-size check.
- Protected values, credentials and raw provider content remain excluded from
  every serialized success/error context. Each needle has raw, escaped and
  forward-slash positive controls where applicable.

Each new production guard needs its own source fault, intended assertion,
byte-identical restoration and passing restored control. Existing obligations
5, 7, 8 and 64 to 67 remain required. Run proportional regression and preserve
all previous fault/evidence limits. A crash or timeout is not a fault proof.

## Continuous browser proof and later live authority

After the correction, first prove one uninterrupted browser journey on an owned
disposable store using explicitly authored coach and executor doubles. Enter the
investigation, request the proposal, run it, inspect the exact report, accept
into the draft, explicitly save and compare through the actual UI. Assert draft,
version and authorship changes at their separate steps. Verify desktop/mobile
100%/200%, disabled choices when neither candidate qualifies, one-run refusal,
no selection, no operation and unchanged ledger rows. Never execute the proposed
service on the host. This proves UI mechanics only, not live inference or repair.

A new live action remains unprepared and unauthorized. Finish its zero-call
runner and controls before requesting approval. Pin source, store, installed
runtime and request hashes, models/settings, maximum calls and Sandbox operations,
current public pricing, an all-in ceiling, once marker and stop rule. All three
old actions and every unused remainder remain closed. Preserve failures and
never repeat generation merely to obtain a better result.

The eventual live journey must retain exact proposal bytes, source identity,
verified plans and deterministic results through generation, diagnostic,
acceptance, save and comparison. Retain variation and failed repetitions. A
passing diagnostic alone cannot establish a causal customer-facing repair.
S46 remains INCOMPLETE and UNACCEPTED. The user retains acceptance authority.

## Verification and preservation in this investigation

Private receipts are in
`/Users/jayd0/Documents/Codex/2026-10-25/files-pasted-by-the-user-you/work/s46-coach-audit-gotv3_us/`.
`audit.py` reproduces the read-only investigation and size measurements.
`baseline.json` records 2,403 entry file hashes. Focused existing tests pass
56 Python cases with two existing warnings and 30 Node cases. Full suites and
mutation matrices were not rerun because no product or test source changed.

All 106 protected-material and 66 older-evidence hashes match. Original action
files remain preserved. No live call, credentialed request, installation, selection,
operation, S46 acceptance, Git staging/publication or other-slice edit occurred.
Final preservation matches 2,398 of the 2,403 entry hashes. Only five existing
instruction/status records changed, and this proposal is the sole new repository
file. Product/test source, all inherited Git status entries, branch, HEAD and
empty index remain unchanged. Both original live/terminal database pairs and the
third action's review copy retain their recorded hashes. `git diff --check` passes.

Approval recorded: this scoped Gate 3 context correction and its offline
implementation/proof only. No new live or spending authority is granted.
