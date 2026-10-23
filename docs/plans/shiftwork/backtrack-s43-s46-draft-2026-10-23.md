# Scoped Gate 2 and Gate 3 backtrack for S43 and S46: draft, 2026-10-23

**Status: APPROVED 2026-10-23 (Parts A, B and C) and applied to `02-architecture.md` and `03-program-design.md`.** The text below is the reviewed draft as approved; the gate documents are now authoritative. Design text only.
Once approved, the text below would be applied to `02-architecture.md` and `03-program-design.md`, each with a dated revision notice.
Until then those approved documents stay unchanged and authoritative.
Approving this draft would approve design text only.
It would not approve implementation, fixture authoring, sealing, live calls, spend, deployment or a Gate 4 slice entry.
Source plan: [path-to-15-slice-plan-draft-2026-10-23.md](path-to-15-slice-plan-draft-2026-10-23.md).

## 1. Why a backtrack, and why it is narrow

Gate 2 section 10 already requires Nemotron to do "meaningful behavior inside the starter service, such as interpreting requests and proposing information/tool selection".
The delivered design does not meet that intent:

| Evidence | Where |
|---|---|
| The gateway accepts only a bare tool name as the whole reply | `shiftwork/gateway/service_inference.py:113-129` |
| The Bellwether model candidate offers two tools and its guard code completes every task "whether or not the model call succeeds" | `shiftwork/fixtures/artifacts/bookshop/compare_repair_model_service.py:1-12` |
| All ten calls in the successful S20 chain chose `public_record_lookup` | `docs/plans/shiftwork/evidence/slice20-sse-live-summary-2026-10-01.json`, per the S27 judge evidence |
| Gate 3 section 7 allows zero inference calls, and no clause forbids guard code from silently completing what the model missed | `03-program-design.md` section 7 |

So most of S43 is a Gate 3 correction under an unchanged Gate 2 intent.
S46 is new authority for the assist gateway: it may cause one isolated diagnostic run of its own proposal.
That changes a Gate 2 boundary row and Gate 2 section 10.

**Part C is outside the requested scope but blocks the plan.**
S44 and S45 as drafted (k = 10 repetitions) exceed the Gate 3 section 7 limits.
Part C proposes the smallest limit change, flagged for a separate decision.
Approve A and B without C, and S44 and S45 must be redrafted inside today's limits.

## 2. Part A: S43, Nemotron interprets the request and the service depends on it

### A1. Gate 2 section 10, replace the first paragraph

Current:

> Nemotron performs meaningful behavior inside the starter service, such as interpreting
> requests and proposing information/tool selection. Learner code owns the control flow
> and exact transaction/stock rules. Ordinary code may replace unnecessary AI work.

Proposed:

> Nemotron performs meaningful behavior inside the starter service: it interprets each
> customer request into a structured task plan and proposes the information/tool steps
> for it. Learner code owns the control flow, validation and exact transaction/stock
> rules. Ordinary code may replace unnecessary AI work, but only as a labelled repair
> the learner authors and compares. A shipped starter or reviewed candidate that
> presents model-dependent behavior must not contain hidden code that completes tasks
> the model omitted. When the model's plan is wrong, the visible checks must be able
> to fail.

The rest of section 10 is unchanged.

### A2. Gate 3 section 3.5, replace `InferenceReply`

Current:

```python
class InferenceReply(BaseModel):
    text: str
    proposed_tool_names: tuple[str, ...]
    input_tokens: int | None
    output_tokens: int | None
```

Proposed:

```python
class TaskPlanStep(BaseModel):
    task_type: str            # member of the frozen mission task vocabulary
    tool_name: str            # member of the grant's allowed_tool_names

class InferenceReply(BaseModel):
    text: str                 # raw model content, retained privately
    plan: tuple[TaskPlanStep, ...] | None   # None when the content fails the schema
    plan_failure: Literal["SCHEMA_INVALID", "TOOL_NOT_ALLOWED", "TASK_TYPE_UNKNOWN"] | None
    input_tokens: int | None
    output_tokens: int | None
```

Add after the existing gateway paragraph:

> The gateway parses the model content as JSON against the frozen task-plan schema.
> It returns the parsed plan, or `plan = None` with one `plan_failure` code. A plan
> failure is service behavior, not a gateway error: the call still counts, the run
> continues, and the service receives the failure so its own code decides what to
> do. The gateway never repairs, completes or reorders a plan. The task vocabulary
> and tool allowlist are both derived from the frozen mission policy, never from
> the learner request or the prompt. Tool execution stays with the trusted request
> driver, which still refuses any unlisted tool.

### A3. Gate 3 section 3.10, extend the mission policy

Add `task_vocabulary: dict[str, str]` beside `allowed_tool_vocabulary` in the mission declaration.
Bellwether declares four or five public tools and its task types (for example collection, conditional alternative, price, stock).
The exact names belong to S43 fixture authoring and its operator review, not to this design.

### A4. Gate 3 section 2, file map

| File | Change |
|---|---|
| `shiftwork/gateway/protocol.py` | `TaskPlanStep`, revised `InferenceReply` |
| `shiftwork/gateway/service_inference.py` | JSON schema parse and the three `plan_failure` codes; no repair |
| `shiftwork/executor/tokenfactory.py` | The driver forwards the plan or failure to the service |
| `shiftwork/fixtures/mission/bookshop_pivot_v1.json` | `task_vocabulary`, enlarged tool vocabulary (new mission version, old one kept for history) |
| `shiftwork/fixtures/artifacts/bookshop/` new starter | Model-dependent starter with no rescue code; contents and pin come from S43 authoring and review |

The existing `pivot_starter_failure_service.py`, its recorded baseline and every earlier run stay as history under their original contract.
New Bellwether shifts bind the new mission version.
Earlier shifts are not migrated.

### A5. Gate 3 section 7, one limit row changes

| Limit | Current | Proposed |
|---|---|---|
| Service inference calls per customer request | 1 maximum; zero is valid when ordinary code handles the request | 1 maximum. A new Bellwether starter must make exactly 1. A learner repair may make 0 if it is labelled as code-only. |

Gateway input, output and deadline limits are unchanged.

### A6. Gate 3 section 9, new tests

61. `test_gateway_returns_plan_or_one_failure_code_and_never_repairs` feeds valid JSON, invalid JSON, an unlisted tool and an unknown task type.
Each case must give the expected plan or code.
A mutation that fills a missing step or drops an invalid one must fail.
62. `test_starter_omitting_a_required_task_fails_the_visible_check` replays a labelled reply that omits one required task.
The matching deterministic check must fail and the run must not count as useful completion.
A mutation that re-adds guard completion must make this test fail.
63. `test_task_vocabulary_and_tool_allowlist_come_only_from_frozen_mission` injects a wider vocabulary through the request body and through prompt text.
Each must be refused before any provider call, as test 36 does for tools.

## 3. Part B: S46, the coach proposes a patch and runs it once in isolation

### B1. Gate 2 section 2, replace the assist gateway row

Current:

> | Assist gateway | Optional attributable orientation, hints and patch proposals | No diagnostic help before learner cause/falsifier; no silent selection or self-grading |

Proposed:

> | Assist gateway | Optional attributable orientation, hints and patch proposals; may request one isolated diagnostic run of its own proposal against the learner's public tests | No diagnostic help before learner cause/falsifier; no protected cases, evaluator or credentials; no trusted-local execution; no freeze, eligibility, selection or self-grading |

### B2. Gate 2 section 10, add after the second paragraph

> A patch proposal may be tested once before the learner decides. The controller,
> not the model, runs the proposed source as a diagnostic public experiment in the
> same isolation class as learner code. It uses only the learner's public tests and
> public records, never protected cases. The report is the deterministic check
> result, not model prose. The run consumes one of the shift's diagnostic
> experiment slots and can never create eligibility. If the learner accepts, the
> proposal is copied into the learner's draft and counted in that version's
> authorship record. Only the
> learner can save, freeze, compare and choose it.

### B3. Gate 3 section 3.2, changes

Add to `AssistEvent`:

```python
    diagnostic_run_id: Id | None      # the one isolated run of proposed_patch, if requested
    proposal_source_sha256: str | None
```

Add:

```python
def run_assist_proposal(conn, shift_id: Id, event_id: Id) -> ExperimentRun: ...
```

Replace the paragraph's last two sentences:

> Accepting a patch records attribution only. It does not edit code, freeze a
> version, prove a cause or affect eligibility.

with:

> `run_assist_proposal` is allowed once per patch proposal. It reuses the `DIAGNOSTIC`
> experiment path (6.4) with the proposal bytes as a transient candidate, under the
> configured isolated executor only. Under the recorded or trusted-local executor it
> is refused with no run. Accepting a patch copies the proposal into the learner's
> draft, and the next saved version counts it in the existing
> `VersionAuthorship.generated_patch_accepted_count` (3.6). It does not freeze a
> version, prove a cause or affect eligibility. A coach-authored version is
> compared and chosen exactly like any other version.

### B4. Gate 3 section 3.10 and section 7

The assist model may differ from the service model through the existing `SHIFTWORK_ASSIST_MODEL`.
Which larger Nemotron model is served, and at what rate, is unverified and must be checked before S46's go-ahead.

| Limit | Current | Proposed |
|---|---|---|
| Assist model calls per shift | Declared per pack; Bellwether 3 shared, one patch proposal maximum | Unchanged |
| Isolated runs of a patch proposal | Not allowed | 1 per patch proposal; consumes one diagnostic experiment slot (existing cap of 2 per shift) |

No new budget is created.
Go-To-Market and FDE declare no patch proposal, so they are unaffected.

### B5. Gate 3 section 9, new tests

64. `test_assist_proposal_run_refused_before_investigation_twice_or_without_slot` covers: no complete investigation, a second run of one proposal, and no diagnostic slot left.
Each is refused with no executor call.
65. `test_assist_proposal_never_runs_trusted_local_or_recorded` sets each non-isolated executor and requires refusal.
A mutation that falls back to `LocalProcessAdapter` must fail.
66. `test_assist_proposal_run_sees_no_protected_material_and_cannot_qualify` scans the run's inputs and every public surface with test 39's needles (with a scanner self-test), and requires the run to be absent from eligibility.
67. `test_accepted_proposal_is_draft_only_and_attributed` checks that accepting changes only the draft, creates no version, freeze or selection, and that the next saved version's `generated_patch_accepted_count` rises by one.

### B6. ADR check

ADR 0005 (experiments and operating selection) is affected: a model-initiated diagnostic run must stay outside eligibility.
ADR 0001 (sealed evaluator isolation) is affected only by test 66.
Both get a dated note on approval.
No ADR is superseded.

## 4. Part C: repetitions for S44 and S45 (flagged, separate decision)

Today's limits allow 2 diagnostic experiments per shift and one comparison of three pairs (six slots).
That cannot show "missed in 7 of 10 trials".

Proposed Gate 3 section 7 changes:

| Limit | Current | Proposed |
|---|---|---|
| Public repetitions per diagnostic experiment | 1 | Up to 10, fixed before results |
| Public repetitions per comparison slot | 1 | Up to 3, fixed in the frozen context; each repetition is a fresh public workspace |
| Executor operations per trial slot | 2 | Public repetitions + 1 protected |
| Protected variants per family per comparison | 3 | Unchanged (protected phase stays once per pair) |

With 3 repetitions, each candidate gets 9 public runs per request across 3 pairs.
The protected inventory, seals and section 8.1 rules are unchanged.
Eligibility still needs every mandatory check passed in every repetition (Gate 2 section 8 already says "across required trials").
Sandbox operations per comparison rise from 12 to 24.
Their cost is unmeasured, so a fresh cost estimate is required before any live comparison.
New tests would be 68 (a repetition count changed after results is refused) and 69 (one failed repetition blocks eligibility).

## 5. Decisions for the reviewer

1. Approve Part A (S43)?
2. Approve Part B (S46)?
3. Approve Part C, or redraft S44 and S45 inside today's limits?
4. Should earlier Bellwether shifts stay on the old mission version (proposed) or be re-run?
