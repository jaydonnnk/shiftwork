# Slice 15 operator review packet

**Decision recorded, 2026-09-29:** The operator reviewed and sealed both
comparison files with their exact canonical payload digests. The user then
accepted the full Slice 15 on offline and sealed evidence. No live comparison
has run; this decision is not live service-quality evidence. The draft status
below describes the packet before the operator decision.

Status: DRAFT, 2026-09-28 (protected-phase revision). Gate 2 S8.1, Gate 3 and
Gate 4 were re-approved together and ADR 0006 was accepted after the repair
round. See the approval, review, repair and proof-round sections in
`docs/plans/shiftwork/00-status.md`. This packet presents agent-authored
material for a human decision. Nothing here records operator review, sealing,
acceptance, a live run, or permission to use credentials. Every file below
still says `AWAITING_OPERATOR_REVIEW`; production reservation refuses them.

## What changed since the previous revision

The previous revision presented candidates that differed mainly in optional
price content and six protected entries that were labels over identical
stimuli, and it recommended a revision before sealing. Under the approved Gate
2 S8.1 and the reconciled Gate 3, this revision authored new bytes:

- A separate comparison state `bookshop_compare_state_v1.json` that keeps the
  accepted Slice 11 state and its pins byte-unchanged and adds one cheaper,
  same-genre, collectible paperback (`book:tidal-paths:paperback`, 1,400 GBP
  minor units, stock 1) so request 011 separates the candidates.
- Candidate B now implements the declared greatest-shelf-stock preference,
  breaking ties by lower price; candidate A keeps the lowest-price preference.
- Six protected variants that each carry their own request row, public task
  spec and additive-only state delta, bound to the protected step at request
  ordinal 3.

## Exact public material

The visible rubric is `shiftwork/fixtures/mission/bookshop_pivot_v1.json`
(10,214 bytes, SHA-256
`aebe89555a72688eedfb564088f57b78328c184d0a4e378918c46d13d1e6c12a`).
The rubric resolves "tomorrow" against the snapshot's `observed_at`, producing
2026-09-26, rather than against the live wall clock. It requires a result for
each required task, exact title and edition, current consistent cited records,
date-specific collection, strictly under-budget same-genre alternatives when
collection cannot be confirmed, justified fallback only, no commitment and
the structured response envelope only. Optional price does not compensate for
a missing required task. The full rules and explanation conditions are in the
rubric file; the table below names each workload's tasks and conditions.

The comparison state is
`shiftwork/fixtures/shop/bookshop_compare_state_v1.json` (4,261 bytes,
SHA-256
`4abe54462600ade9793c1d7dc32978c427d4f0b0a5e5b121830cfc3b478a2f6f`).
It is the snapshot a comparison runs against: the accepted Slice 11
investigation state
`shiftwork/fixtures/shop/bookshop_pivot_public_state.json` (3,227 bytes,
SHA-256
`6bc17d69f43b24aa6048fdead7747e5820cd5740e47ba03a4a004d9ddea3c32c`)
with one added entity, `book:tidal-paths:paperback`, and its three added
price, stock and availability records, and no changed or removed records
(verified 2026-09-28).

The ordinal map is
`shiftwork/fixtures/requests/bookshop_compare_manifest.json` (1,762 bytes,
SHA-256
`aacb1fff1d7973a2b61b412c774e24da42cbea4156270c26c4ecf61dcac20ebe`).
Its canonical `workloads` payload digest for later operator sealing is
`6e21937b65606e489b3768d3cd15347eff778ca6ee90f883dd68b318d8d66317`,
computed as
`sha256(json.dumps(workloads, sort_keys=True, separators=(",", ":"), ensure_ascii=False))`.
The controller recomputes exactly this digest and requires
`review_status: OPERATOR_SEALED` plus a matching `sealed_payload_sha256`
before a reservation exists. It also pins the comparison state with
`comparison_state_sha256` and requires the manifest's engagement to be
`bookshop`. Each workload's `task_specs_sha256` is the SHA-256 of
`canonical_bytes([spec.model_dump(mode="json") for spec in specs])` over the
parsed `CustomerRequestSpec` list. Every pin and digest above was recomputed
from the current bytes on 2026-09-28. Each pair's A and B slots consume the
same frozen batch and task specs.

| Pair | Exact customer requests, in order | Visible required work | Raw batch bytes / SHA-256 | Canonical task-spec SHA-256 |
| --- | --- | --- | --- | --- |
| 1 | 011: "Can I collect the Salt Roads paperback tomorrow? If not, suggest something similar under £20." 012: same wording with £15. | Collection on 2026-09-26 and conditional same-genre alternative strictly below 2,000 or 1,500 GBP minor units; price optional. | 394 / `749ea9360c55e8340ccd995234c3e333d66d0740cfb02e227223c60c9c406005` | `fa27937f6b590c50d54587402b7534aa1d0cc8c8da6f5c45123c1fea18a1a278` |
| 2 | 021: "Can I collect the Salt Roads hardback tomorrow? If not, suggest something similar under £20." 022: "How much is the Harbour Atlas paperback, and do you have it on the shelf?" | 021: collection plus conditional alternative, price optional. 022: price and stock for the paperback, both required. | 374 / `43b5e8275ceb4a4fb444e26232fde303c7e4feb35ae8976bb443a3c143a21de5` | `1440d3c63b80f7d0764b6f71ccdfe62a55b974e46d2deb4729640a8846a380e2` |
| 3 | 031: "How much is the Salt Roads paperback, and do you have it on the shelf?" 032: "Can I collect the Harbour Atlas paperback tomorrow? If not, suggest something similar under £20." | 031: price and stock, both required. 032: collection plus conditional alternative, price optional. | 376 / `c0e0ed996c2cc6f05971be34ceb68daadb36aa838d6a1344d2d3e13b1000bb0f` | `b553b9aac350d10944e86496b6e20a3f32435e6116d58b3e019017adaae5cdfe` |

Each batch has exactly two requests. The raw spec files beside the batches are
2,865 / `c6b5b4b09f71edf6480a4b88d026115029ff81d1dbfd02a9d1d155718da56c10`,
2,276 / `78294186d99b589ac577a282d6930978e02c9ae137836c1f57e0871ebb061c08` and
2,284 / `0a05eb2d8ccd74861119570c0269b20781036e62c89e2f0297039e37744005fe`.
The manifest hashes the canonical parsed specs, not these raw spec-file bytes.
The manifest description states the A/B preference split and names request 011
as the only public preference separator.

## Protected inventory requiring separate sealing

The file is `shiftwork/sealed/cases/bookshop_task_completion.json` (19,977
bytes, SHA-256
`5d0f5af5b5cfd13e50ab5f68b36cf6e34757847439da31916bdab0cb0a2fe5cd`).
It holds one enabled family, `task_completion`, cycle 1, with six variants.
Each variant carries its own request row, its own public task spec (the
collection task and the conditional alternative) and an additive-only state
delta, all bound to request ordinal 3, one above each workload's public
request count. Its canonical `cases` payload digest for sealing is
`da93870aee735f1291c8b333bf38c8ce2cf12c33ad4511763e65b4414327d55e`,
computed with the same stdlib recipe. Reservation persists the drawn case
payload and digest in restricted, immutable database rows so later file edits
cannot rewrite that exposure; the stimulus request row and its public task
spec are delivered to both candidates of its pair as a separate phase after
the public batch, and contents, expectations, deltas and captures never reach
learner-facing surfaces. The full expectations and notes are in the restricted
file. Do not copy them into a learner-facing view.

| Variant | Distinct stimulus (abridged) | Requested entity | State delta | Behavior to falsify | Public rule anchor |
| --- | --- | --- | --- | --- | --- |
| 01 | Collect the Salt Roads paperback; conditional alternative under £20. | `book:salt-roads:paperback` | none | Every required task returns a result | `task.required_results` |
| 02 | Same request, naming the hardback listing as a different edition. | `book:salt-roads:paperback` | none | Fact claims name the requested title and edition | `task.requested_entity` |
| 03 | Collect the Cove Trail paperback; conditional alternative under £20. | `book:cove-trail:paperback` | adds the entity at 1,900 with stock 3 and collection unavailable | A supported negative collection answer counts as an answer | `collection.confirmed_only` |
| 04 | Collect the Field Manual paperback; alternative under £15. | `book:field-manual:paperback` | adds the entity (1,700, stock 0, collection unavailable) and one same-genre alternative priced exactly 1,500 with stock 2 | A completed alternative must stay strictly under the budget | `alternative.same_genre_under_budget` |
| 05 | Collect the Quay History paperback "despite the empty shelf". | `book:quay-history:paperback` | adds the entity at 1,800 with stock 0 and collection available, a necessary-record conflict | Conflicting necessary records require the allowed referral | `collection.confirmed_only` |
| 06 | Collect the Harbour Atlas paperback and hold one copy. | `book:harbour-atlas:paperback` | none | An availability answer creates no commitment | `collection.confirmed_only` |

The six variants now differ by request and by controller state rather than by
label. Variants 01 and 02 share a requested entity but differ in request
wording; variants 03 to 05 add the requested entity and the records that carry
the behavior under test; variant 06 changes only the request. Whether these are
six semantically independent failures is the operator decision this table
supports, and it is not a code check.

## Candidate differences and fairness challenge

The test-only fixtures are
`shiftwork/fixtures/artifacts/bookshop/compare_repair_a_service.py` (9,148
bytes, SHA-256
`7497195129f70481940670cd5ce6eb7782dcfcafefe5e5b0a8459e263d3e6b71`) and
`shiftwork/fixtures/artifacts/bookshop/compare_repair_b_service.py` (8,395
bytes, SHA-256
`b4674218d44abdab011c9201f5f0dcff1a4b302a281623f189376ed5784e0342`). Their
frozen artifact pins live in `config.TRUSTED_LOCAL_FIXTURES` under
`compare_candidate_a` and `compare_candidate_b` and are recomputed from the
exact files by the guard in `tests/executor/test_conformance.py`.

- A is guard-first: resolve each task's records before claiming anything,
  answer the optional price fact whenever the requested edition has a current
  price, and choose the lowest-priced qualifying alternative
  (`compare_repair_a_service.py:149,151`).
- B is plan-first: build a fact plan, answer the optional price fact only when
  the request asks for a price, and choose the qualifying alternative with the
  greatest current shelf stock, breaking ties by lower price
  (`compare_repair_b_service.py:115,117`).

Measured over the six frozen public requests and the comparison state as a
function-level check of the authored fixtures on 2026-09-28 (not a Sandbox run
and not a live model comparison):

| Request | A | B | Rubric-bearing difference? |
| --- | --- | --- | --- |
| 011 collect Salt Roads paperback, alternative under £20 | alternative Tidal Paths, 1,400, stock 1 | alternative Harbour Atlas, 1,600, stock 3 | Yes, the single public separator |
| 012 collect Salt Roads paperback, alternative under £15 | alternative Tidal Paths | alternative Tidal Paths | No |
| 021 collect Salt Roads hardback (collectible) | collection completed | collection completed | No |
| 022 Harbour Atlas price and shelf | price 1,600 and stock 3 | price 1,600 and stock 3 | No |
| 031 Salt Roads paperback price and shelf | price 1,800 and stock 0 | price 1,800 and stock 0 | No |
| 032 collect Harbour Atlas paperback (collectible) | collection completed | collection completed | No |

Both candidates complete every required task on every request. A also emits an
optional price result on the four collection requests (011, 012, 021 and 032);
B omits it on all four. The visible rubric does not measure optional price, so
that content difference carries no score.

Operator judgements this packet supports:

- One distinguishing public request, 011, carries the whole observable
  difference; the other five show mandatory-rule parity. Weigh that as one
  request out of six and decide whether the comparison is meaningful enough to
  seal.
- Whether the six protected behaviors are six independent failures is an
  operator decision; the request and state deltas above are the evidence for
  it.
- The candidates are deterministic trusted-local fixtures authored for the
  demo. They do not show a learner discovering the repair, and they are not
  live Sandbox or live model evidence. A live six-slot comparison requires its
  own authorization, credentials and cost.

## Decision requested

The gate reconciliation is approved, and the offline mechanism, 97-row
mutation proof, full suite and browser checks are recorded in
`docs/plans/shiftwork/slice15-implementation-plan.md`. Sealing is a separate
operator act: set `review_status` to `OPERATOR_SEALED` and write each file's
`sealed_payload_sha256` to the canonical digest recorded above. The digests
cover only the `workloads` and `cases` payloads, so sealing does not change
them; any edit inside a sealed payload invalidates its digest and returns the
file to review. Live execution, credentials and cost require their own
explicit authorization after sealing, and Slice 15 acceptance is separate
again.
