# ADR 0002 — Deterministic ledger ownership and replay

- Status: Accepted (decision approved within Gate 2 on 2026-09-15; recorded as an ADR
  during Gate 3 drafting on 2026-09-15)
- Sources: `docs/plans/shiftwork/02-architecture.md` S9, S19 candidate 2;
  `docs/plans/shiftwork/03-program-design.md` S3.1, S3.4, S3.5, S6.A, S6.B
- Implementation status 2026-09-19: accepted, partially implemented; see the status
  note at the end.

## Context

The product's inheritance mechanism depends on business consequences being reproducible:
the next shift must inherit the same artifact, incidents and synthetic business state
regardless of process restarts, machines or timing. The ledger is also the visible
evidence chain a learner inspects, so an unreproducible or silently repaired history
would undermine the product's central claim. Business consequences are synthetic
scenario state and must remain labelled as such.

## Decision

- The ledger is append-only and hash-chained (`prev_hash` → `hash` per event). Only the
  controller writes; learner, harness and model cannot.
- Derivation is a pure function: `reduce(fixtures, raw_outputs, check_results,
  committed_contract) → unchained event drafts`; `chain.append` assigns `seq` and hashes
  inside the same finalization transaction. Same inputs must replay to identical events
  and identical hashes.
- Corrections are new events referencing the corrected event; history is never rewritten
  or deleted. Chain verification runs on every read; a broken chain is a hard failure
  surfaced to the operator, never silently repaired.
- Canonical serialization (sorted keys, compact separators, UTF-8, NFC, floats rejected)
  is defined in exactly one module and pinned by golden hash vectors.

## Consequences

- All state must be reconstructible from durable rows (`artifact_versions`, `runs`,
  `run_outputs`, `check_results`, `ledger_events`); no in-memory state is authoritative.
- Finalization must be a single transaction and idempotent; interrupted finalization
  writes no check results and no events.
- Hashing discipline bounds what may enter hashed payloads (no floats; canonical
  encoding only), which constrains future schema changes and requires explicit hash
  versioning if the format ever changes.

## Implementation status 2026-09-19

Accepted, partially implemented. Landed: Slice 5 (2026-09-18, implemented,
demonstrated and independently reviewed) delivered the pure reducer, the hash chain
with verification on every read, correction events that reference rather than
rewrite, and idempotent single-transaction finalization with fault-injection probes
and a failing-capable chain-linkage test. Pending: restart reconstruction rules (a
run left RUNNING across a restart is reconciled to FAILED with captures and draws
retained) complete at Slice 8. Correction-event representation already uses the
production chain and persistence primitives in `tests/ledger`; no operator workflow
for correction events is implemented and none is assigned. The Gate 4 re-approval
(2026-09-19) keeps these mappings in `04-slices.md`.
