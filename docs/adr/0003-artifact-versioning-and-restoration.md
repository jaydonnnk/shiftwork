# ADR 0003 — Artifact versioning and restoration semantics

- Status: Accepted (decision approved within Gate 2 on 2026-09-15; recorded as an ADR
  during Gate 3 drafting on 2026-09-15)
- Sources: `docs/plans/shiftwork/02-architecture.md` S6, S19 candidate 3;
  `docs/plans/shiftwork/03-program-design.md` S3.2, S3.6, S5.1, S5.2, S6.E
- Implementation status 2026-09-19: accepted, partially implemented; see the status
  note at the end.

## Context

Persistent responsibility across shifts is the product's core mechanism: later shifts
inherit the learner's artifact, decisions, incidents and unresolved limits. If versions
could be mutated, or if restoration depended on a running process or executor
checkpoint, the learner's history and the audit trail of what was actually executed
would become unreliable. The learner's committed contract must be part of the frozen
artifact, because checks are parameterized by it.

## Decision

- A version is an immutable, content-hashed snapshot (files + declared contract
  parameters) with a parent link. A draft is the single mutable working copy per shift.
  Submitting freezes; it never mutates a version.
- Restoration re-provisions from the controller store only — never from a sandbox
  checkpoint and never as a history reset. After any crash, state reconstructs from
  tables; an interrupted run is marked failed on restart and produces no events.
- Attempt budgets are counted from durable `runs` rows and enforced controller-side,
  not just in the UI.

## Consequences

- Learner corrections always create new versions; nothing is deleted, so prior evidence
  stays intact and the change log is real.
- The artifact store is a trusted controller-side component; the sandbox is disposable
  and never a source of truth.
- Storage grows monotonically (append-only); acceptable at single-learner scale, and the
  natural place to revisit if the product ever becomes multi-tenant.

## Implementation status 2026-09-19

Accepted, partially implemented. Landed: Slice 2 (2026-09-18) froze immutable
content-hashed versions (files plus declared contract parameters) with real hashing,
and the artifact plus version hash reconstruct from tables after a process restart.
The draft round-trip landed in Slice 6 and is part of the Slice 6 repair (test 45 is
not FULL). Pending: attempt budgets counted from durable `runs` rows land in Slice
7; close and inheritance restoration, plus interrupted-run handling on restart,
land in Slice 8. The Gate 4 re-approval (2026-09-19) keeps these mappings in
`04-slices.md`.

Update 2026-09-20: the attempt-budget limb landed in Slice 7. `start_run` counts
prior runs from the durable `runs` rows, refuses the over-limit reservation, and
commits the run row, its batch and snapshot refs and one draw per enabled family in
one `BEGIN IMMEDIATE` transaction (`tests/orchestrator/test_budget_rotation.py`; the
route maps the refusal to 409). The 2026-09-19 sentence listing budgets as pending
is superseded.

Update 2026-09-20 (Slice 8): close and inheritance restoration landed.
`open_next_shift` seeds the new draft byte-for-byte from the inherited version's
files (the template applies only when no version exists), and the artifact
version, unresolved incidents, declared limits and ledger summary carry forward
as engagement rows the board reads; `start_run` and `close_shift` use the version
in force (this shift's own latest version or the inherited one). `close_shift` is
one atomic, idempotent transaction that refuses while a run is in flight, appends
the hash-chained `LIMIT_DECLARED` events for the version's declared limits exactly
once and retires unresolved OPEN incidents as `CLOSED_UNRESOLVED` rows.
Interrupted-run reconciliation landed with `reconcile_interrupted`, called from the
app lifespan: a run a restart left QUEUED, RUNNING or CAPTURED is marked FAILED
with its completed captures and rotation draws retained and zero checks or events
written (`tests/ledger/test_ledger.py`,
`tests/orchestrator/test_close_inheritance.py`, `tests/orchestrator/test_test1_preproof.py`).
The 2026-09-19 "remain Slice 8 as stated" sentence is superseded; the decision body
above is unchanged.

Update 2026-09-21 (Slice 9 review round): the run's consumed shop snapshot is now
durable execution identity, not a pathname. `execute_run` reads the configured
snapshot once, persists the exact bytes on the run row (`shop_snapshot_bytes`,
schema v5; legacy rows stay NULL and fall back to a best-effort path read) and
provisions the adapter from a controller-owned copy of those bytes, so transcript
selection, scoring and the client's historical comparison all resolve the bytes
the run consumed even if the source file is later edited or removed. Run rows
persisted before the capture keep the pathname behaviour. Failing-capable tests:
`tests/api/test_client_evidence.py` (same-path replacement keeps the historical
projection identical; a deleted source keeps the captured bytes retrievable for
both FINALIZED and FAILED runs), `tests/executor/test_conformance.py` (the v2/v3/v4
to v5 upgrades add the column without inventing bytes for legacy rows) and
`tests/orchestrator/test_run_binding.py` (unchanged binding). The 2026-09-20
sentence "commits the run row, its batch and snapshot refs" remains true for the
reservation transaction; the capture is the execution-time addition.

Update 2026-09-25 (Slice 10): the live schema is now v6 and this ADR's decision
body is unchanged. Two evidence pointers above move with it. First, the
`shop_snapshot_bytes` column and its NULL legacy fallback are now v5 rows read
under v6, not the current schema version. Second, the v2/v3/v4 upgrade tests in
`tests/executor/test_conformance.py` no longer derive their old table shapes from
the live `schema.sql`, because that file now carries v6 columns and the derived
fixture inserted positional v5 rows into them. They read a frozen
`tests/store/schema_v5.sql` snapshot instead, and their fragment-strip assertions
are retained verbatim, so they still fail if the snapshot stops being an older
shape. ADR 0005 owns the v6 additions (`opening_mode`, `operating_selections`,
`experiments`, run purpose and evidence mode) and supersedes this file's
latest-version inheritance semantics.

Update 2026-09-30 (Slice 20): explicit restoration and freeze ancestry landed,
and this ADR's decision body is unchanged. `orchestrator.restore_version_to_draft`
replaces one open shift's draft with a stored version's bytes and records that
version as the draft's new base through `repo.set_draft_base_version`. It refuses
a closed shift, refuses a version owned by another engagement, and re-verifies the
stored bytes on read, so a restore cannot seed the draft from a tampered or
foreign version. `freeze_version` now reads `repo.get_draft_base_version_id` and
records that base as both `parent_id` and the new `restored_from_id` column on
`artifact_versions`; before this slice `parent_id` came from the newest stored
version, so restoring A after saving B froze a version that descended from B.
Ancestry therefore follows the draft the learner is actually working from.
Restoration stays controller-store only: no sandbox checkpoint is consulted and
no history is reset, since a restore writes a draft base and never edits a frozen
version. ADR 0005's explicit operating selection remains the authority for which
version is operated and inherited by the next shift; this update changes only how
a freeze inside one open shift records its parent. Failing-capable proofs:
`tests/orchestrator/test_close_inheritance.py::test_freeze_ancestry_follows_the_draft_base_and_explicit_restore`
and the `tests/s20_mutation_proofs.py` rows `inherit_base_from_newest_save`,
`restore_base_not_set` and `restore_closed_shift_allowed`. The offline
verification is recorded in `docs/plans/shiftwork/00-status.md`; acceptance is a
separate user decision.
