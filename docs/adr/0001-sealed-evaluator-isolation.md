# ADR 0001 — Sealed-evaluator isolation

- Status: Accepted (decision approved within Gate 2 on 2026-09-15; recorded as an ADR
  during Gate 3 drafting on 2026-09-15)
- Sources: `docs/plans/shiftwork/02-architecture.md` S7, S8, S19 candidate 1;
  `docs/plans/shiftwork/03-program-design.md` S3.4, S6.C, S6.D
- Update 2026-09-19: the loader-ownership sentence is superseded (controller
  orchestration owns sealed loading); see the update note at the end. All other
  boundaries stand.
- Update 2026-09-28 (ACCEPTED): two Decision clauses are
  narrowed by `docs/adr/0006-protected-comparison-stimulus-boundary.md` for the
  Slice 15 protected comparison phase. The user re-approved Gate 2 S8.1,
  Gate 3 and Gate 4 together with ADR 0006 on 2026-09-28. See the narrow
  supersession map in the update note at the end.

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

## Update 2026-09-19: loader ownership superseded

Gate 2 was backtracked and re-approved on 2026-09-19: controller orchestration owns
sealed loading and evaluation receives explicit, pure inputs. The Gate 3
fourth-backtrack revision (RE-APPROVED 2026-09-19) aligned the file map, signatures
and call stack: the controller calls `sealed.store.load_drawn_cases` and passes the
drawn cases plus explicit `public_records` to the pure evaluator.

Superseded: the Decision sentence "The read path is the evaluator module". The
earlier co-located loader plus pure function was feasible; Gate 3 test 11 never
prohibited a loader's file access, so this is an ownership decision, not an
impossibility fix.

Everything else stands: sealed case specs and expected values stay controller-side,
no module outside the permitted loader path imports the sealed store, sealed
material never enters a sandbox or a prompt, and evaluation stays deterministic,
LLM-free and file-free.

Implementation status (2026-09-19): partial. The Slice 6 repair owns the revised
tests 11, 13 and 17 (Gate 4 re-approval, 2026-09-19). The remaining Gate 3 scoring
inputs (`check_defs`, `visible_checks`) and the exact loader/scorer call stack land
in Slice 10 under the Gate 4 follow-up revision (2026-09-19, RE-APPROVED by the
user in chat); the loader ownership itself is already as decided: `finalize_run`
calls `sealed.store.load_drawn_cases` and passes explicit inputs to the pure
scorer. The prior text above is kept as history; the current authority is the
re-approved Gate 2 and Gate 3 documents.

Recovery-mechanism status (2026-09-19): the Consequences line about rotating the
affected group and invalidating dependent attempts is a design target, not built
behavior. No operator workflow or attempt-invalidation mechanism exists, and no
refill proves invalidation; Slice 7 owns the requirement under the Gate 4 follow-up
revision (2026-09-19, RE-APPROVED by the user in chat).

Recovery-mechanism update (2026-09-20): Slice 7 landed the state-change half. A
compromised group is retired by setting its draws to `DrawState.INVALIDATED`
(`repo.invalidate_rotation_group`), the dependent attempts read back through
`repo.invalidated_run_ids`, rows and captures are retained, and a refill cannot
clear the state or reuse an exposed identity (`sealed.rotation.validate_refill`;
`tests/orchestrator/test_budget_rotation.py`). No operator surface was added, which
the Slice 7 requirement states explicitly; nothing in the runtime consumes the
invalidated state beyond that read-back. The 2026-09-19 "no attempt-invalidation
mechanism exists" sentence is superseded; the rest of the recovery target stands.

## Update 2026-09-28: two clauses narrowed for the protected comparison phase

The Slice 15 gate revisions (Gate 2 S8.1, Gate 3 S3.9 and S6.4, re-approved by the
user on 2026-09-28) add a protected phase to each comparison trial slot: after a
pair's public batch, one sealed-derived request streams into a fresh sandbox
workspace under a shop state resolved from the frozen comparison state plus that
variant's sealed additive delta. An independent adversarial review of those
revisions found that this design contradicts two clauses above and that no gate
superseded them (findings F2 and F6 in `docs/plans/shiftwork/00-status.md`).

ADR 0005 did not cover the gap: its supersession map explicitly retains this
record's "safe projections" and narrows only exposure scoping, gateway isolation
and invalidation enforcement.

Superseded, narrowly and only for a case of an enabled comparison family, by
`docs/adr/0006-protected-comparison-stimulus-boundary.md`:

- "sealed cases are never mounted into a sandbox and never placed in an inference
  prompt" becomes a prohibition on controller-held assessment inputs. A protected case's
  request row and its resolved state are stimulus the candidate service must
  consume in order to answer at all; its task specification, expected block,
  expected acceptance aspect, case id, variant ref and rule identities stay
  controller-side. Task assessments are produced controller-side. The protected
  response and service logs originate in the candidate workspace, then remain
  restricted controller captures.
- "never case text, expected values or hidden counts" is narrowed on counts only.
  The aggregate per-candidate protected counts released once an experiment is
  terminal equal the comparison's already-public pair count and its captured and
  missing partition, so they disclose no inventory size, variant identity or
  expected value.

Everything else stands without change, including the bar on learner-facing
case text and expected values, the deterministic LLM-free evaluator, the
import-graph boundary, bounded
probing, rotation and invalidation. The 2026-09-19 reaffirmation that "sealed
material never enters a sandbox or a prompt" is superseded to the same narrow
extent and no further.

Status of this update: ACCEPTED 2026-09-28 with the user's explicit approval
of Gate 2 S8.1, Gate 3, Gate 4 and ADR 0006.
No implementation, operator review, seal, live run, installation, credential use or
publication is authorized by this note.

**Dated note, 2026-10-23 (S43/S46 backtrack, approved).** The isolated run of
an assist patch proposal is inside this boundary: it receives no protected
cases, evaluator code or credentials, and Gate 3 obligation 66 scans its inputs
and public surfaces with the sealed needles. This decision is otherwise
unchanged and not superseded.
