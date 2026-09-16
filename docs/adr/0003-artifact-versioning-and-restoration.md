# ADR 0003 — Artifact versioning and restoration semantics

- Status: Accepted (decision approved within Gate 2 on 2026-09-15; recorded as an ADR
  during Gate 3 drafting on 2026-09-15)
- Sources: `docs/plans/shiftwork/02-architecture.md` §6, §19 candidate 3;
  `docs/plans/shiftwork/03-program-design.md` §3.2, §3.6, §5.1, §5.2, §6.E

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
