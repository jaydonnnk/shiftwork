# Live comparison cost and latency estimate, revised for twelve executor operations

Status: a projection, not a measurement. No live call, credential use, sandbox
operation or reservation was made to produce this document. It discharges the
obligation to revise the Slice 12 single-operation feasibility figures for the
two-phase slot before any live comparison is authorized. It does not authorize
one. The comparison workload manifest and the protected family both remain
`AWAITING_OPERATOR_REVIEW` and unsealed.

The obligation is recorded in three places: `03-program-design.md:1614` fixes
executor operations per trial slot at 2 and requires the revision;
`03-program-design.md:2086` to `2090` names protected phase cost as open item 9
and says to backtrack rather than drop the protected phase or shrink the schedule
if twelve operations are infeasible; `04-slices.md:655` carries the matching
falsifier row; and `00-status.md:787` states that the accepted Slice 12 verdict
covers six single-operation trials only. The filename keeps the 2026-09-28 date
of that obligation. This document was composed on 2026-09-29 during the Slice 16
repair round.

## What a live comparison actually executes

Every count below was read from the frozen bytes and the code path, not assumed.

| Quantity | Value | Source |
| --- | ---: | --- |
| Frozen workloads | 3, ordinals 1, 2 and 3 | `bookshop_compare_manifest.json`, `review_status` `AWAITING_OPERATOR_REVIEW`, `version` 1 |
| Public requests per workload | 2 | manifest `request_count` 2 on all three, matched by the actual `bookshop_compare_pair_01` to `03.jsonl` line counts |
| Protected steps per slot | 1 | `orchestrator.py:2454` sets `executed_request_count = request_count + 1`; `:2590` requires `protected_variant_refs` to equal a one-element tuple; `:2598` to `:2601` load a single protected request |
| Trial slots | 6 | `orchestrator.py:2426` and `:2442` build the schedule over 3 pair ordinals and 2 candidate labels |
| Executor operations per slot | 2 | `orchestrator.py:2632` runs the public phase in its own temporary directory opened at `:2616`, and `:2651` runs the protected phase in a separate one opened at `:2642` |

So one full six-slot comparison is **12 executor operations**, carrying **12
public requests** and **6 protected steps**. At the Gate 3 ceiling of one service
inference call per customer request (`03-program-design.md:1612`, where zero is
valid when ordinary code handles the request), that is **at most 18 inference
calls**. Per candidate the denominators are 6 public and 3 protected, which
matches the denominators the offline demo and the operator packet already report.

The browser harness run of 2026-09-29 confirms the same shape independently: its
six FINALIZED slots read `1:1A/workload-01/2 2:1B/workload-01/2 3:2B/workload-02/2
4:2A/workload-02/2 5:3B/workload-03/2 6:3A/workload-03/2`, so every slot carries
`request_count` 2.

## The measured basis, and the rate card derived from it

The only live measurements available are the six Slice 12 trials at
`slice12-capability-2026-09-26.md` lines 472 to 499. Each was one executor
operation carrying one public request.

- End-to-end per trial: 4,136 / 4,006 / 3,944 / 3,983 / 3,601 / 3,722 ms. Sum
  23,392 ms, mean **3,898.7 ms**, min 3,601, max 4,136, spread 535 ms.
- Inference HTTP latency alone: 1,932 / 1,618 / 1,977 / 2,110 / 1,727 / 1,824 ms.
  Sum 11,188 ms, mean **1,864.7 ms**, which is 47.8 percent of a trial.
- The **2,034.0 ms** remainder is upload, spawn, event polling and capture.
- Usage: `prompt_tokens` 45 on all six, sum 270; `completion_tokens`
  127 / 103 / 126 / 143 / 103 / 104, sum 706, mean 117.7. All six returned
  `finish_reason: stop`, so none reached the 256-token ceiling.
- Estimated inference cost per trial: 3.318e-05 / 2.742e-05 / 3.294e-05 /
  3.702e-05 / 2.742e-05 / 2.766e-05 USD, sum **0.00018564**.
- Worst-case reservation taken before that loop: **0.00331776** for six calls.
- Sandbox `resources.cost` across the six operations: **0.00383704**. The API
  states no currency for that field, so it is not counted as dollars.
- `prior_inference_spend` across all `slice12-*.jsonl`: **0.00803670 USD** against
  the 3.00 USD cap.

Those six cost rows are exactly reproducible from a two-number rate card, which
makes the projection auditable rather than a guess. Solving any two rows gives
**0.060000 USD per 1M prompt tokens** and **0.240000 USD per 1M completion
tokens**, and all six rows then reproduce to within 1e-12. The reservation is
likewise exact: 8,192 prompt tokens at 0.06 plus 256 completion tokens at 0.24 is
**0.00055296 USD per call**, and 0.00055296 times 6 is the recorded 0.00331776.
The 8,192 figure is the Gate 3 gateway input ceiling of 8 KiB read as tokens, so
the reservation already prices the worst permitted request, not the measured one.

## Latency projection

The model separates per-operation overhead from per-request inference, holds the
overhead flat at the measured 2,034.0 ms, and multiplies inference by the request
count each phase actually carries.

| Phase | Requests | Arithmetic | Projected |
| --- | ---: | --- | ---: |
| Public operation | 2 | 2,034.0 + 2 x 1,864.7 | **5,763 ms** |
| Protected operation | 1 | 2,034.0 + 1 x 1,864.7 | **3,899 ms** |
| One slot | 3 | 5,763 + 3,899 | **9,662 ms** |
| Six slots, serial | 18 | 6 x 9,662 | **57,972 ms, about 58 s** |

That 58 s is inference and executor time only, assuming the slots run strictly
serially with no queueing, no retry and no cold provisioning. Endpoint creation
is documented on a minutes scale, and a cold endpoint is not inside the measured
2,034 ms remainder. If a live comparison has to create an endpoint, wall-clock
time is dominated by provisioning and this figure understates it badly.

## Cost projection

| Basis | Per call | 18 calls | Share of the 3.00 USD cap |
| --- | ---: | ---: | ---: |
| Measured token shape, actual | 0.00003094 | **0.00055692 USD** | 0.0186 percent |
| Reserved worst case, 8,192 in and 256 out | 0.00055296 | **0.00995328 USD** | **0.3318 percent** |
| Reserved worst case at the Gate 3 1,024-token output ceiling | 0.00073728 | 0.01327104 USD | 0.4424 percent |

The reservation is 17.87 times the measured actual, because it prices the 8 KiB
input ceiling against a spike that really sent 45 prompt tokens. The third row is
a sensitivity, not the recorded figure: Slice 12 reserved at a 256-token output
ceiling while `03-program-design.md:1616` states the gateway output ceiling as
1,024 tokens, so a live comparison reserving at the Gate 3 ceiling costs about a
third more and is still under half a percent of the cap.

Sandbox `resources.cost` for 12 operations, at the eight-decimal per-operation
mean of 0.00063951, is **0.00767412**. Doubling the measured six-operation sum
without rounding gives 0.00767408, so the two readings differ by 4e-08 purely
from rounding the mean. As in every prior run the API states no currency for that
field, so it is reported and **not** added to the dollar figures or the cap.

Against the budget: `prior_inference_spend` 0.00803670 plus the 0.00995328
reservation is **0.01798998 USD**, leaving **2.98201002** of the 3.00 USD cap.
The reservation for one full comparison is allowed with that prior spend already
recorded.

## Assumptions that could break this, and their falsifiers

1. **Flat 2,034 ms overhead per operation.** Measured on one-request operations.
   A two-request public phase plausibly carries more capture and event polling, so
   5,763 ms should be read as a floor. Falsifier: a measured public operation
   materially above 5,763 ms.
2. **The Slice 12 token shape transfers.** Those trials ran a minimal learner
   service at 45 prompt tokens. The comparison candidates are larger service
   files, so prompt tokens will differ. The exposure is bounded, because the
   8 KiB preflight rejects anything above 8,192 tokens before a provider call and
   the reservation already prices exactly that.
3. **At most one inference call per request.** This is the Gate 3 ceiling, so 18
   is an upper bound on call count, not an expectation. A candidate that answers
   from ordinary code makes fewer calls and costs less.
4. **Serial execution, warm endpoint, no retry.** Gate 3 records no automatic
   retry, so a failed slot is a failed slot and its spend is still incurred; the
   58 s figure does not budget for a re-run.
5. **`resources.cost` scales flat per operation.** If it is runtime-proportional,
   the two-request public operation costs more than the one-request protected one
   and 0.00767412 understates it. This cannot be settled offline and is not
   counted as dollars either way.
6. **Sample size.** Six trials of one request shape, spread 535 ms. This is a
   projection from that sample, not a measurement of a live comparison.

## Verdict

Twelve executor operations across six slots are feasible within the frozen
ceilings on these figures. The worst-case reservation for one full live
comparison is 0.3318 percent of the 3.00 USD cap, or 0.4424 percent at the Gate 3
1,024-token output ceiling, and about 58 s of serial executor time on a warm
endpoint. Cost is therefore not the binding constraint, and nothing here indicates
the backtrack that `03-program-design.md:2089` requires if twelve operations were
infeasible. The protected phase and the six-slot schedule can both stand as
designed.

What this does not establish: it is not live evidence, not a service-quality or
model-behavior claim, and not permission to run anything. The projection inherits
every limit of the Slice 12 verdict, including that its six trials cover one
request shape and that its pre-repair inference records omit the model's reasoning
text. A live comparison still needs the operator to review and seal both fixture
files, and its own explicit authorization.
