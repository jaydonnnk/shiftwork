# ADR 0001 — Sealed-evaluator isolation

- Status: Accepted (decision approved within Gate 2 on 2026-09-15; recorded as an ADR
  during Gate 3 drafting on 2026-09-15)
- Sources: `docs/plans/shiftwork/02-architecture.md` S7, S8, S19 candidate 1;
  `docs/plans/shiftwork/03-program-design.md` S3.4, S6.C, S6.D

## Context

Shiftwork evaluates a learner-owned service against sealed acceptance cases whose
expected outcomes must stay outside any learner- or model-readable environment. Repeated
probing can leak hidden contracts even when files are isolated on disk, so filesystem
hiding alone is explicitly insufficient. The evaluation contract also has to be
trustworthy for the product's core mechanism: a second LLM can propose, diagnose or
explain, but it can never be an independent oracle.

## Decision

- Sealed case specs and expected values live controller-side only. The read path is the
  evaluator module; no other module (executor, assist, api, client) may import the
  sealed store, and sealed cases are never mounted into a sandbox and never placed in
  an inference prompt.
- Evaluation is deterministic and LLM-free. Verdicts, ledger events and pass
  declarations come only from the controller-side evaluator and reducer.
- Learner-visible surfaces expose consequences and a minimal reason-code vocabulary —
  never case text, expected values or hidden counts.
- Probing is bounded structurally: rotation groups draw unexposed variants, attempt
  limits are enforced controller-side, and every request/response and assist
  interaction is retained for after-the-fact audit.

## Consequences

- The migration risk is contained: a leak is detectable (sentinel scans, import-graph
  checks) and recoverable by rotating the affected group and invalidating dependent
  attempts; nothing is deleted.
- Nemotron can never be load-bearing for correctness, which also means Nemotron
  dependence on learner outcomes remains a separate, unproven question (ablation).
- Any feature that would let learner code or a model read evaluation internals is
  rejected by design, even if convenient.
