# ADR 0002 — Deterministic ledger ownership and replay

- Status: Accepted (decision approved within Gate 2 on 2026-09-15; recorded as an ADR
  during Gate 3 drafting on 2026-09-15)
- Sources: `docs/plans/shiftwork/02-architecture.md` §9, §19 candidate 2;
  `docs/plans/shiftwork/03-program-design.md` §3.1, §3.4, §3.5, §6.A, §6.B

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
