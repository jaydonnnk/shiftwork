# ADR 0005: Experiments, operating selection and retained evidence

- Status: Accepted architecture, approved in Gate 2 on 2026-09-24; recorded during
  Gate 3 reconciliation. Gate 3 program contracts and the Gate 4 slice plan were
  approved on 2026-09-24, including Gate 3's scoped Northline selection
  correction. Implementation remains unauthorized; each slice needs its own
  go-ahead.
- Authority: `docs/plans/shiftwork/02-architecture.md` S4 to S10 and S19.
- Supersedes the conflicting pre-pivot semantics identified below in ADRs 0001 to
  0003. Those files and their dated implementation evidence remain historical.
- Number 0004 remains reserved for the separately authorized integration/delivery
  decision. This record does not approve that decision or claim spike evidence.

## Context

A saved repair is not necessarily the repair a learner chose. A test run is not
an operational shift. The approved pivot requires a fair comparison, an explicit
choice of tested code, and later consequences from operating that code. Existing
latest-version inheritance and shared run finalization do not make those distinctions.

## Decision

1. Freeze complete comparison inputs and both candidate versions before protected
   results are released. Reserve bounded exposure and the full trial schedule once.
   Retain failures, missing evidence and trusted usage; recorded inspection is not
   fresh execution or new eligibility.
2. Give runs an immutable purpose. Experimental finalization may retain captures,
   checks and comparison status, but never mutate the business ledger, operational
   incidents, declared limits or operating selection. Only operational finalization
   creates service consequences. A separate close transaction records limits.
3. Append explicit operating selections with the exact version, qualifying evidence,
   rationale, original requirements and retained alternative. Resolve the latest
   explicit choice and validate it; never fall back to an older choice or the latest
   saved version. Selection itself has no business consequence.
4. Preserve complete captured inputs and recorded rule identities for assessment and
   semantic replay. Verify ledger hashes separately from reproducing derivation.
   Old captures and hashes remain unchanged; missing historical inputs remain unknown.
   Migration must not invent a learner choice.
5. Keep sealed loading in controller orchestration and evaluation pure and LLM-free.
   Protect expectations from learner code, executors and both AI roles. Task completion
   is independently assessed; a supported fact alone does not establish an answer
   to the customer's request.
6. Mediate service inference in the controller. No provider key enters learner code,
   its workspace, a prompt or a public response. A run-bound restricted channel and
   hostile-code isolation need separate capability evidence. Failure to verify them
   blocks live learner-code execution rather than allowing credential injection or
   arbitrary local execution.
7. Invalidate all evidence dependent on compromised exposure for future eligibility
   and operation. Preserve previous choices and ledger bytes. Later-condition trials
   are separate experiments, not replacements for original decisions or outcomes.

## Supersession map

| Earlier record | Retained | Superseded or extended |
| --- | --- | --- |
| ADR 0001 | Controller loader ownership, pure evaluator, bounded probing, safe projections | Exposure becomes comparison- or operation-scoped; gateway surfaces join isolation checks; invalidation must block future selection/use, not only read back a flag |
| ADR 0002 | Canonical serialization, append-only chain, atomic/idempotent writes | Only operational finalization and declared-limit close may write business history; captured-input semantic replay is a separate obligation |
| ADR 0003 | Immutable source/contracts, single draft, controller restoration | Latest-version operation/start/close semantics in the 2026-09-20 note are replaced by explicit selection; full context extends the 2026-09-21 snapshot capture |

## Consequences and evidence limits

The existing controller, store, room, recorded adapter and pinned trusted-local
fixtures remain the foundation. Their historical evidence does not prove the new
workflow. Gates 3 and 4 have since specified and approved the exact contracts and
vertical changes, so implementation may resume one approved slice at a time under
its own go-ahead. No live integration, learning result,
installation, credential use, deployment or publication is
established by this record.

## Implementation note 2026-09-30 (Slice 20)

Decision 7's later-condition limb and decision 3's inheritance projection landed
offline. No decision body above changed.

- `orchestrator.observed_condition(state_bytes, dependencies)` derives a
  `ContextCondition` from the public bytes one operational run actually consumed,
  and persists it on that run's execution context. All-available dependencies
  yield `condition-normal`, so a run that observed no change can never be cited
  as the basis of a later-condition comparison.
- `orchestrator.create_later_condition_comparison` re-tests the current operating
  selection's exact selected version and its retained alternative in fresh matched
  A/B slots under those observed bytes. It requires a `LEARNER_CHOICE` selection,
  a `FINALIZED` `OPERATION` run of this shift under this selection, and an observed
  condition whose kind is not `normal`; it is capped at one per shift and replays
  idempotently on its client request key. The preceding operational run is never
  one side of the experiment, since every slot is a new run, and a later-condition
  comparison can never back a selection.
- The comparison's workloads are read from the reviewed manifest against the
  `config.PIVOT_COMPARE_STATE` bytes, while its context and exposure use the
  observed world bytes. `_require_dependency_only_variation` permits only
  dependency availability to differ between the two, names every other changed key
  in the refusal, and refuses an unreadable or differently shaped world, so the
  reviewed workloads stay valid under the observed condition.
- The observed reference is durable and immutable: `experiment_observed_contexts`
  carries no-update and no-delete triggers, is written once by
  `repo.insert_observed_context`, and is read back on the experiment select as
  `observed_run_id` and `observed_context_id`. The table is added in
  `v6_tables.sql` rather than `v6.sql`, so an already-v6 database gains it on
  reopen instead of needing a column SQLite cannot add idempotently.
- `board_snapshot` projects `inherited_requirements` (the selection's comparison
  id plus its requirement set id, requirement set hash and visible check set hash)
  so a successor shift shows the contract it inherited rather than only the version
  it inherited. The client's Next shift station keeps recorded operational history
  and the hypothetical later-condition experiment in separate regions, and a board
  whose `latest_run` is a later-experiment slot run excludes that run from
  operational history.

Evidence limit: this is offline policy proof through local doubles and the
recorded executor. It is not model answer quality, Sandbox isolation or
live-service evidence, and no later-condition trial has run against a live
dependency outage. The linked `ISOLATED_LIVE` chain that decisions 1, 2, 3 and 6
would need for end-to-end evidence (recorded Nemotron calls in a qualifying
comparison, explicit selection of that exact version, a recorded Nemotron call as
that selected version in operation, and exact-version inheritance) remains an
unachieved stretch target with its own credential and spend authorization; see
`docs/plans/shiftwork/04-slices.md` Slice 20. Failing-capable proofs:
`tests/orchestrator/test_selection_operation.py`
(`test_later_alternative_experiment_does_not_rewrite_original_history`,
`test_later_condition_needs_an_observed_change_and_its_own_world`,
`test_a_fault_mid_later_reservation_leaves_no_partial_comparison`),
`tests/orchestrator/test_close_inheritance.py`
(`test_next_shift_inherits_selection_rationale_alternative_tests_and_limits`,
`test_close_declares_limits_without_selecting_or_selling`),
`tests/api/test_pivot_routes.py`,
`tests/store/test_pivot_migration.py`
(`test_observed_context_references_reject_update_and_delete`) and the twenty
`tests/s20_mutation_proofs.py` rows. The offline verification is recorded in
`docs/plans/shiftwork/00-status.md`; acceptance is a separate user decision.
