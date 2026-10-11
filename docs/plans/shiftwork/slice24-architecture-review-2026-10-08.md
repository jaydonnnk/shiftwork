# S24 architecture and cleanup review

PASS within the authorized offline scope. S24 acceptance remains the user's
decision. This is the current agent's closing review, not an independent review.
No file deletion is proposed.

| Area | Finding and evidence | Action |
| --- | --- | --- |
| Runtime ownership | Selection, operation, finalization and replay remain controller-owned. GTM reduction dispatches through operation-ledger-v3; earlier reducers retain their prior paths. Full offline regression passes 1,340 tests. | Keep |
| Pure reduction | The GTM reducer consumes controller-assessed tasks, checks and captured envelopes. Owner, clock and handoff causes bind the corresponding check and output. Failed records retain a complete assessment trace. S24 controls separately fault these bindings and event classes. | Keep |
| Inheritance | apply_pipeline_history derives a captured public snapshot from verified synthetic ownership. It preserves the reviewed source file. Chain verification and duplicate-owner refusal precede inheritance. Restart and reprocessing retain the exact selected version and produce no duplicate state. | Keep |
| Later experiments | Candidate pins resolve through the owning pack. The dependency-only comparison uses the captured ownership overlay and checks its hash. Six later slots retain both versions without changing prior business rows or selection. | Keep |
| Module boundaries | All 56 production Python modules parse. Only the reducer adds import modules, shiftwork.domain and shiftwork.domain.errors. Both are existing domain dependencies. There is no new external dependency, storage layer, endpoint, framework or UI. | Keep |
| Referenced helpers | apply_pipeline_history is called by operation freezing and later comparison. The new reducer is called by the versioned dispatcher. The operation demo and fault runner are referenced by the S24 plan/checkpoints. The reference inventory is retained. | Keep |
| Fixtures and authority | The 19 approved material files, three document bindings, three artifact pins and original approval digest still verify. New review/outage observations are disposable operator state. The extra positive human-review proof also binds a disposable mission before selection. It is not a new production material approval. | Keep |
| Tests | Same-signal conflict tests and archived-signal history tests exercise different validation contexts. No removal is justified by their apparent input overlap. All 55 S24 and 106 refreshed S23 controls reach their intended named assertions with zero setup errors and exact restoration. This does not establish exhaustive branch coverage. | Keep |
| Historical records | Retain both prior handoffs, interrupted/excluded controls, restoration recovery, rejected probes and signed S23 evidence. New notices supersede their current-state labels while preserving historical bytes. | Keep |
| ADRs | ADRs 0002, 0003, 0005 and 0006 remain consistent: deterministic replay, exact selected-version inheritance, experiment/business separation and controller-owned protected comparison. No durable architectural decision changed; no ADR rewrite is needed. | Keep |

The shipped-material demo processes the qualified operational signal. A separate
controller probe demonstrates the human-review branch using a consistent,
disposable operator mission and confidence-50 state. Its earlier state-only probe
correctly produced an incident because the shipped spec permits QUALIFIED only.
Do not read the positive probe as a shipped review workload or additional material
approval. Its setup errors and rejected premise remain in the evidence.

Known limits remain: trusted-local execution, synthetic pipeline consequences,
packaging excluded, live conformance skipped, no browser journey, no fresh clean
checkout of S24, and no measured model quality, learner gain, cost, real CRM action
or production readiness. GTM browser work and any live-capable journey belong to
separately authorized S25. No cleanup finding blocks the authorized offline result.

Evidence directory: evidence/slice24-offline-2026-10-08/completion/.
Key receipts: architecture-inventory.json, proof-source-bindings.json,
fault-audit.json, s23-assertion-audit.json, demo-audit.json, copy-restoration.json,
full-receipt.json and the final preservation.json.

## Refresh 2026-10-11: storage boundary, shared assessed text and demos

PASS within the authorized offline scope, with two non-blocking RISK items and one
stale status document. This refresh supersedes the summary above for current
state; the rows above keep their historical text, and their counts (1,340 tests,
55 S24 controls) are superseded below. It is the current agent's closing review,
not an independent review. Acceptance remains the user's decision. No deletion is
proposed.

Scope: changes since the review above. These are the R2 inheritance repair
(2026-10-09), the F1, F3, F4 and F6 repairs with the `RetainedRecordUnreadable`
storage boundary, and the F2 shared helper `render_assessed_task_customer_text`
(both 2026-10-11). Evidence: `C:/swr24-acc-20261011`, outside the repository.

| # | Area | Verdict | Evidence | Action |
| --- | --- | --- | --- | --- |
| 1 | Storage boundary | PASS | `RetainedRecordUnreadable` (`shiftwork/domain/errors.py:162`) is a `ShiftworkDomainError` of kind `conflict` and a `ValueError`. `_retained` (`shiftwork/store/repo.py:57`) wraps exactly five deserializers: run output, check result, ledger event, task assessment and execution context (lines 581, 624, 831, 1160, 1262). It converts only a `ValueError` or `TypeError` raised while building the model. `replay_assessment` catches only this type around its reads (`shiftwork/orchestrator.py:1296`) and returns `UNKNOWN_MISSING_INPUTS`; assessment and reduction stay outside. The store depends on the domain, never the reverse. | Keep |
| 2 | Boundary reach | RISK, carried | Other deserializers (runs, shifts, versions, incidents, experiments, trial slots, observations) still raise untyped errors on out-of-band edits. Background executors read before their failure-marking `try`, so an unreadable row leaves a run `QUEUED`. Display readers of the five types return 409 with no dedicated case. Every case needs an out-of-band database edit. Outside the S24 exit contract per the 2026-10-10 triage. | User ruling: close before S25 or carry |
| 3 | Shared assessed text | PASS | `render_assessed_task_customer_text` (`shiftwork/domain/customer_answer.py:161`) is a pure domain function with exactly two production callers: `output_evidence_for` (`orchestrator.py:1891`) and `_diagnostic_customer_text` (`experiments.py:402`). Both projections now take GTM acceptance from this one function. It renders through `render_task_customer_text`, unchanged since HEAD. Callers fetch the assessments; the domain module imports no storage. | Keep |
| 4 | Removed helper | PASS | `_pipeline_history_context` has no remaining reference in `shiftwork/`, `tests/` or `demos/`. Both history loops in `_verify_pipeline_history` (`orchestrator.py:2564`) read through the boundary. | None needed |
| 5 | Module boundaries | PASS | All 56 production modules parse. Import delta against HEAD: the reducer adds `shiftwork.domain` and `shiftwork.domain.errors` (as on 2026-10-08), and the repository adds stdlib `functools`; nothing else. Every new definition has a caller. No new external dependency, storage layer, endpoint, framework or UI (`architecture-inventory.json`). | Keep |
| 6 | Unused imports, pre-S24 | Keep, out of scope | `orchestrator.py` imports `CandidateRef`, `Experiment`, `ExposureItem`, `LiveComparisonBudget`, `RunAssessment` and `TrialSlot`, each named only on its import line. Identical at HEAD and present since the 2026-10-02 subsystem split (`76b8467`). Not S24 work. | Later cleanup candidate |
| 7 | Healthy behavior | PASS | Demos rerun on this tree. `journey.json` differs from the 2026-10-08 R1/R2 record only in timestamps, the database hash and `elapsed_ms`. All four operation runs give identical projection text and IDENTICAL replay with zero writes, under both the current code and the pre-2026-10-11 `shiftwork/` preimage, on both databases. The reviewed-material checker passes with the original digest. | Keep |
| 8 | Inherited reprocessing text | RISK, cosmetic | `run-0009` (owner, write and handoff all `NOT_APPLICABLE` and passing) renders "No additional owner, record or handoff is required." three times, once per task, because `render_task_customer_text` emits one sentence per task. The pre-2026-10-11 code renders the same text, so this is not a regression. No S24 assertion reads this text. | User ruling: fix in S24 or carry to S25 |
| 9 | Tests and controls | PASS, finite | Repair module 59 passed; full non-packaging suite 1,399 passed, one live-only skip, two existing warnings (2026-10-11, F2 round). Every source and test file is byte-identical to the F2 fault copy `C:/swr24-f2`; only the checkpoint and `MISTAKES.md`, written after that run, differ. S24 has 73 controls (69 distinct faults), S23 106 (102). 33 of the 73 S24 controls match only the generic needle `Failed: DID NOT RAISE`. No skip, xfail or TODO marker in any S24 file. Duplicate faults are documented (F5); no test file is redundant. | Keep |
| 10 | Fixtures and authority | PASS | No fixture, seal or pin file changed. `demos.gtm_reviewed`: 19 material files, three document bindings, three offline fixture pins, digest `8d87c2dc...62d1fa`. | Keep |
| 11 | Status documents | Stale | `docs/SHIFTWORK_PLAN.md` still leads with the 2026-10-08 F1-F4 notice and lacks the R1/R2 and later rounds. `00-status.md` is refreshed this round. Earlier checkpoint addenda keep superseded counts as history, with the F5 caveat recorded. | User ruling: mirror the status notice |
| 12 | ADRs | PASS | ADR 0002 (replay reports IDENTICAL, DIFFERENT or UNKNOWN_MISSING_INPUTS with zero writes, line 69) and ADR 0005 (refuse an unreadable world, line 92) match the boundary. No durable decision changed; no ADR rewrite is needed. | Keep |

Cleanup result: delete none, rename none, keep all. No item blocks the authorized
offline result. Items 2, 8 and 11 await the user's ruling; none was changed here.

Limits added since the section above: the helper's request filter (ordinal and
id) has no fault, because a GTM run holds one request; counts are finite controls,
not branch coverage; and no independent review of the F1 to F6 repairs has run.
The earlier known limits stand.

Evidence files: `demo/` (journey JSON, database, log and JUnit XML),
`reviewed.log`, `demo-compare.json` (current code), `demo-compare-r13code.json`
(pre-2026-10-11 preimage), `architecture-inventory.json`,
`workspace-before.json`, `workspace-after.json` and `f2-copy-manifest.json`.
