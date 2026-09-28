# ADR 0006: Protected comparison stimulus boundary

- Status: Accepted 2026-09-28. The user explicitly re-approved the revised
  Gate 2 S8.1, Gate 3 and Gate 4 together with this record after the repair
  round. ADR 0001 is narrowed only as mapped below.
- Authority: `docs/plans/shiftwork/02-architecture.md` S8.1 items 3 and 5;
  `docs/plans/shiftwork/03-program-design.md` S3.9 and S6.4.
- Raised by: the independent adversarial review of 2026-09-28, findings F2
  (BLOCKER) and F6 (MAJOR), recorded in
  `docs/plans/shiftwork/00-status.md`.
- Number 0004 remains reserved for the separately authorized integration and
  delivery decision. This record does not approve that decision.

## Context

The revised Gate 2 S8.1 adds a protected phase to each of the six comparison
trial slots. After a pair's public batch runs, one sealed-derived customer
request streams into a fresh sandbox workspace, under a shop state resolved from
the frozen comparison state plus that variant's sealed additive delta.

Two accepted clauses of ADR 0001 contradict that design in terms, and no gate
superseded them:

1. `docs/adr/0001-sealed-evaluator-isolation.md:24-25` states that sealed cases
   "are never mounted into a sandbox and never placed in an inference prompt".
   The protected phase mounts sealed-derived stimulus as the workspace shop
   snapshot and streams a sealed-derived request line to the candidate service.
2. `docs/adr/0001-sealed-evaluator-isolation.md:28-29` states that learner-visible
   surfaces expose "never case text, expected values or hidden counts". Gate 3
   S3.9 bullet 3 and Gate 2 S8.1 item 5 release aggregate per-candidate counts of
   reserved, captured and missing protected steps.

ADR 0005's supersession map explicitly retains ADR 0001's "safe projections" and
narrows only exposure scoping, gateway isolation and invalidation enforcement, so
neither clause was superseded by the pivot. ADR 0001's own 2026-09-19 update note
reaffirms that "sealed material never enters a sandbox or a prompt".

The contradiction is real but it is a boundary-drawing problem, not a design
error. ADR 0001 was written for a single-phase evaluation in which every sealed
case was assessment material: its request, its expected block and its verdict all
had to stay controller-side because the evaluator read them and the service never
did. The protected phase splits a sealed case into stimulus the candidate must
consume in order to answer at all, and assessment material that decides whether
the answer was right. ADR 0001 draws no line between those two, so read literally
it forbids any hidden-input test.

## Decision

1. **Split a sealed comparison case into stimulus and controller-held assessment inputs.**
   For an enabled comparison family, the stimulus is its protected request row
   (request id, customer text, entity ref) and the state resolved from the frozen
   comparison state plus its additive delta. The controller-held assessment inputs are
   its public-shaped task specification, expected block, expected acceptance
   aspect, case id, variant ref and rule or check identities. The task
   specification is public in shape but states the hidden request's requirements;
   the evaluator needs it and the candidate service does not. The service reads
   the request text and its workspace state. The controller produces task
   assessments after execution. The protected response and service logs are
   execution artifacts created inside the candidate workspace, then retained as
   restricted controller captures. They are never learner-facing, but cannot be
   described as never entering that workspace.

2. **Stimulus may enter the sandbox; controller-held assessment inputs may not.** The protected
   request row and the resolved protected state are the only sealed-derived bytes
   that reach a candidate workspace or a service prompt, and they reach it only
   inside the protected phase, in a fresh workspace, after the public phase is
   complete. The task specification, the expected block, the authored delta, the
   derivation rule that maps a delta to a resolved state, the variant identity and
   the controller's assessment never enter a sandbox, a prompt, a learner-facing
   payload, an error, a log line or a client bootstrap. Protected execution
   artifacts may exist in the candidate workspace while the phase runs; their
   retained captures are restricted and never projected.

3. **The residual channel is named, bounded and invalidating, not denied.** The
   resolved state is derived from sealed material, and the candidate service is
   learner-authored code that can read its own workspace snapshot. A learner who
   wrote a service to exfiltrate that snapshot therefore has a channel to observe
   one unexposed variant's added entities and records. Three properties bound it:
   the delta carries only public-shaped values (a price, stock or availability
   record over a book entity) and no authored expected block or rule, although
   a reader may infer the right answer from that state and the public rules; the
   protected phase's retained captures, observations, logs and assessments are
   restricted and never projected through the app, although learner-authored code
   can observe its own transient outputs; and any suspected protected leak retires
   the affected rotation group and invalidates dependent comparison and
   operational evidence under Gate 2 S8.1 item 6. This channel is a reason to
   keep exposure bounded and rotation unexposed, and it is not evidence that the
   protected phase is leak-free.

4. **The released protected counts are not hidden counts.** ADR 0001's prohibition
   exists because a count of hidden cases reveals the size and shape of a sealed
   inventory. The aggregate protected counts released by S3.9 bullet 3 do not: each
   candidate's reserved count equals the comparison's pair count, which is already
   public through the three frozen workloads and six trial slots; the captured and
   missing counts partition that same public number. Releasing them therefore
   discloses no inventory size, no variant identity, no expected value and no case
   text. The counts stay gated on the experiment being terminal, so a learner
   cannot use a mid-run protected count as a feedback channel.

5. **What stays absolute.** ADR 0001's prohibitions on learner-facing case text,
   expected values, inventory size, evaluator internals and promotion control
   are unchanged and are not narrowed by this record. Evaluation stays
   deterministic, controller-side and LLM-free. No model reads authored
   assessment inputs. The import-graph boundary is
   unchanged: the stimulus types live in `domain/task_contract.py`, which the
   evaluator already imports, so housing them creates no new edge into the sealed
   store.

## Supersession map

| Earlier record | Retained | Superseded or extended |
| --- | --- | --- |
| ADR 0001 | Controller-held assessment inputs, pure LLM-free evaluator, bounded probing, import-graph isolation, invalidation and rotation, the bar on learner-facing case text and expected values | The flat clause "sealed cases are never mounted into a sandbox and never placed in an inference prompt" is narrowed to controller-held assessment inputs, per Decision 2. The flat clause "never hidden counts" is narrowed to counts that reveal inventory size or shape, per Decision 4 |
| ADR 0002 | Canonical serialization, append-only chain, atomic and idempotent writes | Nothing. This record adds no serialization rule |
| ADR 0005 | Frozen comparison inputs, immutable run purpose, explicit operating selection, comparison-scoped exposure | Nothing. This record supplies the sealed-boundary detail that S8.1's protected phase needs and ADR 0005 left to Gate 3 |

## Consequences

- The protected phase becomes designable without contradicting an accepted ADR, and
  Gate 2 S8.1 items 3 and 5 and Gate 3 S3.9 cite this record as their boundary
  authority.
- The narrowing costs a real property. Before this record, "no sealed bytes in a
  sandbox" was checkable by scanning a workspace for any sealed needle. After it,
  the scanner must distinguish stimulus needles from assessment needles, so a
  leak test that only proves sealed bytes are absent is no longer sufficient. Gate
  3 tests 50 to 54 own that proof and none of them exists yet.
- Substring scanning cannot establish provenance for short or shared values.
  Gate 3 test 53 therefore pairs distinctive-needle self-tests with public
  source and ordinal checks; a legitimate public scalar such as 1 must remain
  servable.
- Decision 3 is a stated risk, not a mitigation that has been tested. No probe has
  attempted to exfiltrate a resolved protected state through a candidate service.
- No implementation, operator review, seal, live run, installation, credential use,
  deployment or publication is authorized or established by this record.
