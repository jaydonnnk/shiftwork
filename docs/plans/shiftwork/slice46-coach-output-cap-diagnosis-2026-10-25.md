# S46 coach output-cap diagnosis, scoped Gate 3 amendment and offline proof

Status: APPROVED and IMPLEMENTED OFFLINE, 2026-10-25 Asia/Singapore. No provider
call, Sandbox operation, installation or spending occurred in this investigation.
This document grants no live authority.

All four historical actions and every unused remainder stay CLOSED. S46 remains
INCOMPLETE and UNACCEPTED.

## 1. Measured root cause

Two retained Super coach calls on the same model, the same `max_tokens` and the
same provider endpoint differ in exactly one respect: the size of the supplied
context. The approved [context correction](slice46-coach-context-correction-2026-10-25.md)
more than doubled the input, and the unchanged 1,024 output cap then could not
hold the longer reasoning that input induced.

| Measured value | Action 2, thin context | Action 4, corrected context |
| --- | --- | --- |
| Source | `/tmp/shiftwork-s46-20261025/proposed-live-v2/coach-metadata.json` | `continuation-01a17207/live-proposal-v2/coach-metadata.json` |
| Model | `nvidia/nemotron-3-super-120b-a12b` | `nvidia/nemotron-3-super-120b-a12b` |
| Requested `max_tokens` | 1024 | 1024 |
| Input tokens | 697 | 1,485 |
| Output tokens | 734 | 1,024 (at the cap) |
| `finish_reason` | `stop` | `length` |
| Reasoning characters | 2,817 | 4,699 |
| `content` | string, 146 bytes | null |
| Elapsed ms | 5,493 | 6,453 |
| App record | valid patch retained | `ASSIST_PROVIDER_RESPONSE_INVALID` |

Action 2's 146 content bytes are exactly the patch JSON:

```json
{
  "old": "return reply.get(\"plan\"), reply.get(\"plan_failure\")",
  "new": "return reply.get(\"plan\") or [], reply.get(\"plan_failure\")"
}
```

That is roughly 55 tokens, so action 2 spent about 679 tokens on 2,817 reasoning
characters, a density near 4.15 characters per token. Applying that density to
action 4 gives about 1,132 reasoning tokens against a 1,024 cap. The whole budget
was accounted for by reasoning, so `content` was never emitted and the provider
returned `finish_reason: length` with `content: null`. Whether the reasoning
itself had reached its natural end at that point is not established by the
receipt, and this diagnosis does not depend on that.

The gateway is not at fault. `shiftwork/assist/gateway.py:184` rejects a
non-string `content`, which is the correct response to a null content field. No
parsing bug, transport fault or privacy guard caused this event.

Both samples also confirm that the provider counts reasoning inside
`completion_tokens`, so `max_tokens` is one combined budget rather than a
content-only allowance. Action 2 emitted 2,817 reasoning characters plus 146
content bytes, about 2,963 characters, and reported 734 output tokens, near 4.0
characters per token. Action 4 emitted 4,699 reasoning characters and no content
and reported exactly 1,024, near 4.6 characters per token. Two independent
samples at a plausible density for this kind of text are consistent with a single
shared budget, and inconsistent with reasoning being billed or capped separately.

The causal chain is therefore: the approved correction added the four exact
source definitions, the historical identity and the controller-verified inference
result; input rose 697 to 1,485 tokens; Super's reasoning rose 2,817 to at least
4,699 characters; the retained 1,024 output cap absorbed all of it as reasoning;
no patch could be emitted. The correction succeeded at supplying context and
failed at the unchanged output budget.

## 2. Why this needs approval

The approved context correction states: "Retain the exact Super and Nano models,
the 8 KiB input cap, 1,024 output-token cap and 20-second coach deadline. Add no
coach reasoning-off option, retry, larger limit, lexical fallback, hidden task
completion or second-model oracle."

Every correction that could resolve the measured cause is inside that prohibition.
This is a hard boundary, so no source change was made. Gate 3's limits table also
carries the shared row "Gateway output per call, 1,024 tokens, provider request
and local guard" at `docs/plans/shiftwork/03-program-design.md:2557`.

## 3. Proposed smallest correction

Raise the coach output cap only, from 1,024 to 4,096 tokens.

Rejected alternatives and why:

- Reasoning-off for the coach. Explicitly prohibited, and it would defeat the
  reason Super was chosen. The existing reasoning-off permission is bound to the
  exact Nano model at `shiftwork/gateway/protocol.py:12` and to the service
  protocol; extending it to Super would conflate service and coach protocols,
  which the approved contract also forbids.
- Retry. Prohibited, and it multiplies spend without addressing the cause.
- Lexical fallback over the reasoning text. Prohibited, and it would use provider
  reasoning that the approved whitelist forbids forwarding.
- A different coach model. Prohibited by "retain the exact Super and Nano models".
- Shrinking the supplied context back toward 697 tokens. That reverts the
  approved correction whose purpose was to stop weak proposals. Action 2 is the
  evidence: a thin context produced a patch the caller already tolerated, because
  `plan or []` was already iterated downstream.

Why 4,096:

- The measured floor is about 1,132 reasoning tokens plus about 55 content tokens.
  The receipt does not establish that the action 4 reasoning had finished, so the
  natural total is unknown and at least that floor.
- 4,096 leaves roughly 3.4 times the measured floor. A 2,048 cap would leave
  under 900 tokens of margin on a single sample, which is too tight to justify
  another paid action.
- Cost at the retained public Super rates of 0.30 input and 0.90 output USD per
  million tokens: 4,096 output tokens is US$0.003686 and 1,485 input tokens is
  US$0.000446, so one worst-case coach call is about US$0.0041. That is inside
  any reasonable ceiling and barely above the US$0.01075200 the closed action
  reserved.

## 4. Exact change surface

Corrected during implementation. This section originally claimed one production
constant and two test pins. That claim was wrong: the controller enforces the same
cap a second time, from a hardcoded literal rather than the gateway constant, so
raising only the gateway would have left the approved change inert.

Two production points and two test pins:

- `shiftwork/assist/gateway.py:16`, `MAX_OUTPUT_TOKENS = 1024` to `4096`. Its only
  two uses are the provider request at line 148 and the local output guard at
  line 186, so the request and that guard move together.
- `shiftwork/orchestrator.py:2485`, an independent controller guard that read
  `not 0 <= reply.output_tokens <= 1024` as a literal. This is the guard that
  actually decides whether a returned proposal is accepted, and it would have
  refused any reply reporting more than 1,024 output tokens even with a larger
  request cap. It now reads `MAX_OUTPUT_TOKENS`, imported beside the existing
  `MAX_INPUT_BYTES` import from the same module, so the request and both guards
  are single-sourced and cannot drift.
- `tests/assist/test_gateway.py:181` and `tests/assist/test_proposal.py:450`,
  which assert the outbound `max_tokens` equals 1024.

`shiftwork/live_budget.py` also carries `reserved_output_tokens_per_call = 1024`,
but its three validators reject only values below 1024, so they are floors on the
service meters and are unchanged. Those meters are driven by
`ServiceInferenceGateway.before_inference`; `LiveAssistGateway` takes no budget
parameter, so the coach call was never metered by them. Its reservation is owned
by the live runner, which a new proposal must re-pin at the higher cap.

Unchanged, with reasons:

- `GATEWAY_MAX_OUTPUT_TOKENS` at `shiftwork/gateway/protocol.py:11` stays 1024. It
  is a separate constant, so the service gateway, `comparison_flow.py:288`,
  `orchestrator.py:2933`, the frozen diagnostic context and the pins in
  `tests/executor/test_gateway_isolation.py`, `tests/executor/test_reasoning_control.py`
  and `tests/orchestrator/test_s13_bootstrap.py` all stay byte-identical.
- The 8 KiB coach input cap, the 20-second deadline, the 8,192-byte content guard
  at line 188 and the 262,144-byte response guard at line 173 are unchanged.
  Action 4's 4,699 reasoning characters produced a 10,675-byte response, so even
  four times that reasoning stays far under the response guard.
- The models, the prompt text, the role vocabulary, the assist call budget, the
  once-only proposal run and every S46 obligation are unchanged.
- No assist setting is recorded in `service_model_settings_json`, which carries
  only service settings, so no frozen context or retained evidence is invalidated.
- Comparability under `03-program-design.md:2568` concerns the model, image and
  provider settings a comparison candidate runs under. The coach proposal call is
  not a comparison candidate, and both candidates keep the 1024 service ceiling,
  so comparability is preserved.
- The reasoning field is never read by the gateway, so a longer reasoning budget
  adds no new leak surface. The approved whitelist still forbids forwarding
  reasoning, raw payload references or provider response text.

## 5. Honest limits of this proposal

- Raising the cap removes the measured truncation cause. It does not guarantee a
  valid patch, an applicable patch or a patch that improves the service. Action 2
  proves Super can emit valid content under a cap; it also proves that content can
  be a weak repair.
- Exactly one enriched-context sample exists. The natural reasoning length for
  this prompt is unmeasured, so 4,096 is a reasoned margin, not a measured
  requirement. A second truncation at 4,096 is possible.
- Establishing the outcome needs one live coach call under fresh named approval.
  No historical allowance is reusable.
- No generated service code ran on the host during this investigation. All reads
  were of retained receipts, repository source and public pricing already on disk.

## 6. Approval record

The user selected "Approve 1,024 to 4,096" for this scoped Gate 3 amendment on
2026-10-25, and separately directed that the combined browser verification proceed.
The approval covers the coach output cap and the change surface in section 4, and
nothing else.

The amendment was presented as one constant plus two test pins. Implementation
found the second controller guard described in section 4. That guard is the same
cap on the same coach path, and leaving it at 1,024 would have made the approved
change inert, so it is included here as a correction to the proposal rather than a
widening of it. The service ceiling, the input cap, the deadline, the models, the
prompt text and every other retained limit are unchanged.

This approval is not live authority, not spending authority, not acceptance of S46
and not authorization to replay any closed action. All four historical actions and
every unused remainder stay CLOSED.

## 7. Offline implementation and proof

Implemented on `shiftwork/slice-46-continuation` from verified main `1533cc4`.

Three checks were written first and each failed against unchanged source at its own
intended assertion:

- `test_live_gateway_output_guard_refuses_one_token_above_the_coach_cap` pins the
  constant at 4,096 and proves the gateway guard accepts a reply reporting 4,096
  and refuses 4,097 with `ASSIST_OUTPUT_LIMIT`. That guard had no coverage before
  this change.
- `test_controller_output_guard_tracks_the_coach_cap` drives the real API with a
  double that bypasses `LiveAssistGateway`, so only the orchestrator guard can
  accept the at-cap reply. Its counts are literals, not the constant, because a
  hardcoded 1024 left in the orchestrator must fail here while the gateway pin
  still passes. It first failed pre-change with `assert 'FAILED' == 'COMPLETE'`.
- The two existing `max_tokens` pins, which failed pre-change with
  `assert 1024 == 4096`.

An earlier symbolic form of the controller check passed against unchanged source,
because both its replies were expressed relative to the constant and so moved with
it. That version proved nothing and was replaced. This is recorded because a check
that names the constant it is meant to police cannot fail when the constant is
wrong.

Four independent source faults were then injected one at a time, each requiring its
own intended assertion, with byte-identical restoration verified by SHA-256 and a
passing restored control:

| Fault | Intended catch | Verdict |
| --- | --- | --- |
| Controller guard reverted to the literal 1024 | `the controller guard did not move with the coach cap` | PROVEN |
| Controller guard upper bound removed | over-cap reply wrongly accepted, `assert 'COMPLETE' == 'FAILED'` | PROVEN |
| Gateway guard upper bound removed | `ASSIST_OUTPUT_LIMIT` no longer raised | PROVEN |
| Gateway cap lowered to 1024 | `assert body["max_tokens"] == 4096` | PROVEN |

The first two faults are caught only by the controller check and the third only by
the gateway check, because each test exercises one enforcement point and bypasses
the other. No fault is caught by both, so neither check masks the other.

Focused control after the change: 124 passes in `tests/assist` and
`tests/orchestrator/test_investigation_assist.py`, against a 122-pass baseline,
with the same two existing deprecation warnings. The restored control after the
fault matrix also passes 124.

## 8. Combined-tree regression and browser verification

Branch `shiftwork/slice-46-continuation` from verified main `1533cc4`, with the
approved cap change applied. No commit was made; publication is not authorized by
this approval.

Full offline regression: 1,804 Python passes, one live-only skip, the exact
installation deselection and two existing deprecation warnings, against main's
1,802. The two added passes are this amendment's new checks. Node: 361 passes,
zero failures, matching the published combined-tree count.

### S46 proposal journey on the integrated tree

Four uninterrupted authored-double journeys passed, one per cell:

| Cell | Viewport | Native zoom | CSS width | devicePixelRatio | pinch | body zoom | overflow |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1440x1000 | 100% | 1440 | 1 | 1 | 1 | none |
| 1 | 390x844 | 100% | 390 | 1 | 1 | 1 | none |
| 2 | 1440x1000 | 200% | 720 | 2 | 1 | 1 | none |
| 3 | 390x844 | 200% | 195 | 2 | 1 | 1 | none |

Each cell ran the seven stages `initial`, `saved-A`, `generated`, `tested`,
`accepted-draft`, `explicitly-saved-B` and `compared`, and asserted: the coach
request carries `TASK_VOCABULARY`, `TOOLS`, `def ask_for_plan`, `def answer`, the
historical source identity and the controller-verified inference result; the
reviewable proposed source equals the retained snapshot `service.py` byte for byte;
the rendered report belongs to the same experiment as the retained run, shows the
exact output body `e30=` and the `price`, `collection`, `alternative` task rows and
reads Not eligible with mandatory task fails; viewing the report did not rerun the
proposal and a second run returned 409; acceptance changed only the draft and
created no version; the explicit save raised `generated_patch_accepted_count` to 1
with `learner_edited` false; the comparison reached COMPLETE; both choose buttons
stayed disabled with the neither-candidate-eligible refusal; ledger and selection
rows were identical at every stage; no `/selections` or `/operations` request was
sent; exactly one coach call occurred; and there were zero JavaScript exceptions.

Receipts: `/tmp/shiftwork-s46cont-browser-20261025/browser-task-plan/results.json`
and each cell's `receipts/steps.json`, `diagnostic.png`, `diagnostic-report.json`
and `comparison.png`.

The seed store was a copy of the retained `prepared.db`. The original is mode 0444
and its SHA-256 was `7bd6538756f372a6f23ae884a7f154ef7c0d39ef19d8c604e3fe944ea4428d04`
before and after the run, so the closed action's evidence is unchanged.

### S47 navigation and disclosure on the same tree

The committed `tests/client/first_run_journey.mjs` passed on a fresh S47-owned
comparison store: explicit guided choice, separate offline operation, consequence
review, explicit closure and exact inheritance, with the choice not operating and
both choose buttons disabled afterwards.

The committed `tests/client/first_run_browser.mjs` passed at 1440x900, 1280x720 and
390x844 with five guided panels each, one panel visible at a time, navigation
sending no command, and technical hash text hidden by default.

### Harness repairs and rejected attempts

The copied private harness hardcoded the pre-integration S46 checkout in four
places: its `ROOT`, its seed-store relative path, its `tests/client/env.mjs` import
and its receipt-root allowlist. All four were repointed to this continuation
worktree and the new receipt root. Two earlier run attempts failed on setup, one
from the stale allowlist and one from a missing `SHIFTWORK_PYTHON`; both stopped
before any product assertion and are recorded as setup errors, not results.
`tests/client/env.mjs` resolves no interpreter in a fresh worktree, so every Node
browser command needs `SHIFTWORK_PYTHON` explicitly. No repository test helper was
modified to admit an S46 receipt root.

### Limits

These are UI mechanics against authored coach and executor doubles. No provider
call, Sandbox operation, credential use or installation occurred, and no generated
service code ran on the host. They are not real inference, repair efficacy,
learning-gain, physical-device, renderer-performance or assistive-technology
evidence, and a completed journey does not show that any patch improves the
service.
