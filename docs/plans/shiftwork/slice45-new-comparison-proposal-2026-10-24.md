# S45 prompt and schema comparison proposal, 2026-10-24

The approved action STOPPED with an INCOMPLETE outcome after 23 calls and 13
Sandbox operations. Neither candidate is eligible. The allowance is closed.
See [the actual result](evidence/slice45-prompt-schema-live-2026-10-24.md).
The approval and pre-call proposal below do not authorize any further send.

State: APPROVED_EXPERIMENTAL, 2026-10-24. The user replied "Approved" to the
exact sources, one fresh comparison, 42 model calls, 24 Sandbox operations and
US$0.09289728 reserved inference, unchanged deadlines and no automatic selection.
Approval includes the described zero-call preparation and freeze. Sandbox cost
remains unknown. S45 remains INCOMPLETE, unaccepted and uncommitted.
The proposal text below retains its pre-approval wording and evidence scope.

## Exact experimental sources

A is the compact prompt repair:

- Source: `/tmp/shiftwork-s45-repair-proposals-20261024/prompt/service.py`.
- SHA-256: `1b90992e792b069cc3e67732b5eb3b3d378aca67df1eab14c15ce0498fd5ebf6`.

B is the schema-guidance and structural-validation repair:

- Source: `/tmp/shiftwork-s45-repair-proposals-20261024/schema/service.py`.
- SHA-256: `8924cb5d8fffa1c4990cc97c5257e86d444b34bf0f06a6959aecf23678168b84`.

Both are operator-authored examples of learner-editable repairs. Neither is
learner work, a model-authored patch, learning evidence or an eligible version.
The schema is guidance in the user prompt, not provider-enforced structured
output. Its validator checks structure, tool compatibility, uniqueness and
collection-before-alternative ordering. It does not verify customer-contract
completeness. Independent assessment still rejects omissions and extra tasks.

The supplied review recommends both as experimental candidates with no blocking
source defect. Its 41-check count is user-reported, without a supplied command
or receipt. This continuation does not claim to reproduce that count.
No candidate approval has been inferred from the recommendation.

## Shared conditions and declared treatment

Both use `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `enable_thinking=false`,
temperature 0, one user message and one model call per customer request.
Both retain zero retries, 1,024 output tokens, 8 KiB input, a 20-second gateway
deadline and a 45-second workspace deadline. Neither adds omitted tasks,
repairs a model reply, substitutes a deterministic answer or uses hidden rescue.

The declared treatment is A's compact task/tool prompt against B's schema
guidance plus local structural rejection. Their prompts also differ, so the
result compares these exact repair packages. It cannot isolate validation's
effect. Live effectiveness remains unknown, and neither candidate may qualify.
The original stop's latency cause remains unknown. A new run is not a confirmed
timeout fix.

The existing sealed public manifest pins three pairs with two public requests
per pair. Each candidate runs three public batch repetitions per pair, then
one unchanged protected phase per pair in its own workspace.

- Each candidate has nine planned public batch repetitions, covering 18 public
  customer responses. Each individual public request repeats three times.
- Maximum model calls: `2 * 3 * (2 * 3 + 1) = 42`.
- Maximum Sandbox operations: `2 * 3 * (3 + 1) = 24`.
- Protected variants, seals, inventory and Gate 2 section 8.1 are unchanged.
- Every mandatory check must pass in every repetition and protected phase.
  Efficiency follows correctness. Missing or unequal retained counts keep
  the comparison INCOMPLETE. Every retained repetition remains inspectable.

These are the existing [S45 contract](04-slices.md#slice-45-repairs-compared-on-pass-rates)
and Gate 3 obligations 50 to 54, 68 and 69, not new gate decisions.

## Inference reservation and unknown costs

The current repository rates are US$0.06 per million input tokens and US$0.24
per million output tokens. These are projection inputs, not verified current
vendor prices. The meter conservatively reserves 32,768 input tokens and 1,024
output tokens per call despite the separate 8 KiB input limit.

Per-call reservation: `(32768 * 0.06 + 1024 * 0.24) / 1000000 = US$0.00221184`.
For 42 calls, the requested inference reservation is **US$0.09289728**.
The previous eight S45 attempts reserved US$0.01769472. Adding this proposed
allowance gives US$0.11059200 in inference reservations against the existing
US$5 inference ceiling. Reservations are not actual token usage or billing.
Actual vendor billing and Sandbox operation cost remain unknown. This proposal
does not claim a known total price for 24 Sandbox operations.

## One new action after explicit approval

The proposed action directory is
`/tmp/shiftwork-s45-prompt-schema-live-20261024/`, with a new `live.db`.
That directory does not exist at this preflight. No new candidate version,
freeze, comparison reservation or live runner was created in this continuation.

After approval, zero-call preparation opens a new v2-bound shift in that fresh
store. It uses the retained S44 recording only as RECORDED_INSPECTION and labels
every investigation field operator-performed. The exact A and B sources become
template-authored versions, with artifact hashes derived from their contract.
The source bytes, including their existing comments, stay unchanged.

Before execution, verify the real new shift has zero comparisons and choices,
read back both version hashes, and record the ledger hash. The new one-shot
runner must bind these sources and the frozen schedule, use a fresh bounded
meter and refuse existing action receipts or markers. Preparation and its
offline refusal controls must pass before sending anything.

Execution reserves one comparison using the existing production path. It stops
on the first driver failure and retains the failure, partial evidence and spent
reservations. There is no retry, unused-allowance reuse, extra probe, tuning or
automatic selection. Export only the scanned public projection. Restricted
captures remain private. Record actual retained counts, failures and unknown
usage truthfully, then show the real comparison in the browser.

The original `/tmp/shiftwork-s45-live-20261024/` store, frozen A/B versions,
receipts and `once.marker` remain untouched. Never execute its runner again.
Explicit selection, operational execution, S45 acceptance, publication,
deployment and S46 remain separate boundaries.

## Fresh offline evidence

Receipts are under `/tmp/shiftwork-s45-new-comparison-proposal-20261024/`.

- `proposal-tests.log`: 21 passed. Command:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/shiftwork-s45-new-comparison-proposal-20261024/cache-tests .venv/bin/python -B -m pytest -q tests/executor/test_s45_repair_proposals.py`.
- `preflight.py`, `preflight.json` and `preflight.log`: reviewed source hashes
  match the generator, all 106 material hashes and eight original evidence
  files match, the original ledger is unchanged and LEARNER_CHOICE count is zero.
  The simulated meter refuses operation 25 and call 43 after the exact bound.
  Four authored-reply controls show the independent assessment rejects missing
  alternative and extra stock for both sources, although schema validation
  accepts those plans. These controls are not model outputs or live runs.
  Reproduce with `PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/shiftwork-s45-new-comparison-proposal-20261024/cache-preflight-v2 .venv/bin/python -B /tmp/shiftwork-s45-new-comparison-proposal-20261024/preflight.py`.
- The first read-only SQLite setup failed before these assertions because it
  omitted sqlite3.Row. The corrected preflight passes. The failed setup is
  excluded from proof and logged in MISTAKES.md.

No implementation or reviewed source changed. The earlier full regression,
mutation and browser results remain retained audit evidence, not fresh runs
in this continuation. No credential was read, and no live action occurred.

## Requested decision

Approve the exact A prompt and B schema sources above as experimental candidates
and one new comparison capped at 42 model calls, 24 Sandbox operations and
US$0.09289728 reserved inference, under the existing US$5 inference ceiling.
Sandbox cost remains unknown. Approval would include the described zero-call
preparation and freeze, with unchanged deadlines and no automatic selection.
