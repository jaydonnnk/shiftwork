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
