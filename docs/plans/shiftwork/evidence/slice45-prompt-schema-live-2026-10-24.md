# S45 prompt/schema comparison stop, 2026-10-24

The approved comparison STOPPED. Its outcome is INCOMPLETE, both candidates
are ineligible, no selection occurred and the ledger is unchanged.
S45 remains incomplete, unaccepted and uncommitted. The live allowance is
closed. The remaining 19 calls and 11 operations cannot be reused.

## Authority and exact versions

The user replied "Approved" to the [exact proposal](../slice45-new-comparison-proposal-2026-10-24.md):
one new comparison, at most 42 calls, 24 Sandbox operations and US$0.09289728
reserved inference, unchanged deadlines and no automatic selection. Preparation
and source freeze were included. Actual billing and Sandbox cost were unknown.

The new private action is `/tmp/shiftwork-s45-prompt-schema-live-20261024/`.
It has its own store, one-shot marker and receipts. Original S45 evidence in
`/tmp/shiftwork-s45-live-20261024/` is unchanged. Identifiers repeat between
these separate stores and must never be used to merge their histories.

A is the approved prompt source, template-authored ver-0003 in the new store.
Its source SHA-256 is
`1b90992e792b069cc3e67732b5eb3b3d378aca67df1eab14c15ce0498fd5ebf6`.
B is the approved schema source, template-authored ver-0004 in the new store.
Its source SHA-256 is
`8924cb5d8fffa1c4990cc97c5257e86d444b34bf0f06a6959aecf23678168b84`.
Neither source byte changed after approval. Both used reasoning off and the
approved Nano model, message, token, call and 20/45-second deadline limits.
They are operator-authored examples, not learner work or learning evidence.
The investigation source was retained S44 RECORDED_INSPECTION, not a new call.

## Retained results

- A: zero of nine planned public batch repetitions pass mandatory checks.
  Four repetitions are retained and five are missing or unfinished. Three
  completed batches have invalid plans; one retained batch has an execution
  failure. One protected capture is retained and fails. Two are missing.
- B: four of nine planned public batch repetitions pass mandatory checks.
  Six repetitions are retained and three are missing. Two completed batches
  fail other mandatory checks. Two protected captures pass. One is missing.

The counts are incomplete and unequal, so they cannot establish a fair winner.
Protected evidence remains separate and only its terminal aggregates are public.
The schedule was A1, B1, B2, A2, B3, A3. The first three slots completed execution.
The action stopped during A2's first public repetition, run-0020.
Its two pending siblings were marked FAILED without execution evidence.
The six public repetitions in pair 3 remain unexecuted reservations.

A's six public replies in pair 1 all returned the unknown task type
`conditional_alternative`, while the frozen vocabulary requires `alternative`.
The gateway recorded TASK_TYPE_UNKNOWN and returned no plan. All six finished
with stop rather than length. This is an invalid-plan failure, not truncation.
The compact prompt does not explicitly enumerate accepted task-type strings.
That is a plausible contributor, not an experimentally isolated cause.

B's two failed completed batches returned extra task results. One added stock
to a request that did not allow it; the other added collection. Structural
validation accepted those plans, and independent response-envelope assessment
rejected the extra results. They remain failures. No task was removed or
silently added to improve the recorded rate. The four passing batches do not
establish general reliability or overall eligibility.

## Why execution stopped

In A2's first public repetition, the first request recorded
PROVIDER_TRANSPORT_FAILED. The second provider reply succeeded. The Sandbox
reported SUCCESS, and both customer captures passed checkpoint readback.
The adapter then returned SANDBOX_TERMINATED because its gateway-failure flag
was set. The comparison orchestrator deliberately raised LifecycleError to
stop further sends. That exception is not another Sandbox exception.

The adapter code has a separate SANDBOX_TERMINATED branch for unsuccessful
Sandbox status. The retained SUCCESS status and two verified captures identify
the gateway-failure branch here. The failed workspace's measured wall time is
28,359 ms. The complete comparison action took 250,850 ms.

The transport guard merges deadline, HTTPX timeout and HTTPX request errors
into PROVIDER_TRANSPORT_FAILED. Its retained record omits the underlying
exception and failed-call duration. Whether this was the 20-second deadline,
an HTTPX phase timeout or another transport error remains unknown. No live
probe, retry, deadline change, candidate revision or new comparison followed.

## Calls, cost and retained artifacts

The action reserved 23 calls and 13 Sandbox operations. Its conservative
inference reservation is US$0.05087232. Twenty-two replies report 6,730 input
and 2,547 output tokens, projecting US$0.00101508 at repository rates.
Usage for the failed provider request, actual billing and Sandbox cost are
unknown. Earlier S45 reservations plus this action total 31 attempts and
US$0.06856704 reserved inference. These amounts are not vendor bills.

The [scanned public stop package](slice45-prompt-schema-stop-2026-10-24.json)
has SHA-256 `8542522e52adf5402140c2aa31ba1c6598d196b15a244d0341d70af7e6da84fd`.
Private live.db has SHA-256
`f21e543f46303ea0ba73f21f01ed8ee49cf183d08c4605519e75d11a2e7d5bb0`.
Private live-receipt.json has SHA-256
`e0ba5940d0ada96224a42291bc469dcbe7c1b34edf7c25469e3359e67e2d3464`.
Restricted captures remain in the private store, never the public package.

The existing .gitignore excludes this evidence directory. This report and its
public JSON package are local ignored files, not tracked or staged publication.
Preserve both through handoff. Any later authorized publication must include
them deliberately. The first final-inventory check assumed they were untracked
and failed; that setup error is logged and excluded from passing proof.

Private audit.json independently checks one real comparison, zero choices,
unchanged ledger, exact retained counts, original evidence and all 106 material
hashes. The prepared versions, source bytes and runtime hash pins match.
The runner's pre-call meter and separate marker/receipt faults passed their
clean, named-failure and restored controls. No installation occurred.

## Actual browser result and stop boundary

The read-only review copy is
http://127.0.0.1:8455/?board=bookshop#compare. It has no live budget, refuses
mutations and disables startup reconciliation so unsent runs remain unchanged.
It displays captured live results, not an authored rendering fixture or replay.

Fresh browser checks pass at 1280x720 and 390x844, at native 100% and 200%.
They verify exact rates and cause splits, all ten retained run links, disabled
choices, Step 4, an empty hidden owner bubble, collapsed reasoning, no horizontal
overflow, zero mutation requests and zero JavaScript exceptions. Mobile 100%
and desktop 200% screenshots were visually inspected. The checks use Chromium
with WebGL disabled and do not establish physical-device or AT behavior.
Receipts are browser-1x.log, browser-2x.log and their screenshot directories.
The terminal live database remains unchanged by this review.

No product implementation changed during this action. The earlier full
regression and mutation evidence remains retained, not rerun. A different-family
review model was unavailable, so the local decision trail has no independent
model review. Direct source, receipt, browser and preservation checks supply
the stated evidence.

Do not select either version, reuse this allowance or rerun either stopped
action. Candidate revision, another live action, an explicit closure exception,
S45 acceptance and publication require their applicable separate authority.
