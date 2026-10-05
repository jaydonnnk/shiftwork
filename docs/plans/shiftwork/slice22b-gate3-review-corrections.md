# S22b Gate 3 corrections for R1 to R6

**S22b intent/v2 offline step APPLIED, 2026-10-04.**

The approved received-input derivation and trusted intent header are implemented.
The exact 18847-byte v2 packet, literal pin, seal, deployment declaration and
`-text` attribute are applied. V1, original pins and existing raw evidence are
preserved. Current verification and limits: [intent/v2 checkpoint](slice22b-intent-v2-offline-checkpoint.md).
S22b remains incomplete, unaccepted and unpublished. Older unimplemented/unapplied
notices below describe their original checkpoints. Final full offline verification:
997 passed, 1 skipped, 2 warnings; packaging excluded. No live call, credential,
install, later slice or Git publication follows.


2026-10-04 Asia/Singapore. Corrected Gate 3 design RE-APPROVED.
The user explicitly states: "Yep gate 3 is approved. Commit it and merge and
push it to main." The prior operator approval separately covers the exact v2
packet below. Both approvals are now recorded; no repeated approval is needed
for the approved intent header and exact material application. Those steps
remain unimplemented/unapplied and resume after this design publication.
Gates 1, 2 and 4 remain approved. S22b remains incomplete and unaccepted.

## Decisions

| Finding | Concrete correction | Evidence and remaining boundary |
| --- | --- | --- |
| R1 | Launch the trusted driver with `-I -B -u`. Load only the root-owned `deployment_kernel.py` through an explicit file loader. Do not insert the learner directory into `sys.path`; standard-library imports and kernel dependencies use isolated import resolution. Keep reserved trusted filenames and the existing learner privilege drop. | Actual startup-prefix subprocess controls admit harmless learner `secrets.py`, `hmac.py` and `unicodedata.py` modules and require their markers not to execute. Offline only. |
| R2 | Publish the deterministic intent rule in `docs/northline-deployment-protocol.md`: explicit counter intent, otherwise normalized visit token, otherwise received request ID. Derive only from the current received row, never controller conditions. The driver will supply `X-Shiftwork-Intent-Key` beside the request token; exact original body hashes remain unchanged. Reject ambiguous or invalid tokens. | Check all six public deliveries, the pilot/incident input and all six proposed protected inputs. Controller conditions are comparison assertions only. Header implementation and protected v2 application follow Gate 3 approval. |
| R3 | Inspect ordered writes and rollbacks over prior and current verified traces before retry, completion or justified fallback. Any final withdrawal fails. A provisional rollback must target a preceding write in the same request; retain existing same-visit-before-confirmation checks. Retry success requires one matching earlier final write, never a duplicate or withdrawn write. | Separate current-retry withdrawal, earlier withdrawal, cross-request provisional rollback, and refusal concealment controls. |
| R4 | Optional booking claims must assert exactly the requested date and returned commitment reference, identify the observed slot, and cite exactly its actual final-write receipt. Check first delivery and retry identically. A customer-declared prior reference with no executed receipt supports the top-level reference only. | Independent date, reference, absent receipt, wrong receipt and extra-field controls, each after a matching claim succeeds. Existing response envelope still rejects unlisted evidence. |
| R5 | Require complete verified evidence at operation finalization and replay before response assessment, including absent-task and invalid-output paths. Preserve the permissive helper only for failure assessment on non-finalizing paths. Missing, duplicate or invalid receipt/binding prevents finalization and returns `UNKNOWN_MISSING_INPUTS` on replay. Never rewrite stored historical verdicts. | Every ten trace binding substitutions, omitted/duplicate/malformed traces, zero replay writes, and transaction refusal before assessments or business effects. |
| R6 | Extend the structural privacy reader to protected `condition_json.idempotency_key` and `prior_commitment_ref` strings. Collect active families plus explicit historical reviewed sealed-file pins. A historical reader verifies its pin and schema but grants no execution or family admission. | Separate active, historical and per-field controls, with raw, escaped, slash, nested JSON and base64 needles. Shared public slots, dates, routes, outcomes and reason codes remain usable. |

## Signatures and ownership

```python
# Approved R2 addition, implementation pending:
def derive_intent_key(request_id: str, text: str) -> str: ...

# Existing conformance repairs:
def deployment_assessment_inputs(
    conn, run, spec, ordinal, state_bytes, batch_bytes,
    *, phase="PUBLIC", require_complete=False,
) -> dict: ...

def load_pinned_privacy_needles(case_file: str, *, slug: str) -> tuple[str, ...]: ...
```

The pure standard-library intent derivation belongs in `executor/deployment.py`.
The driver calls it on the current received request, then forwards the result
as request metadata. It reads no fixture or task spec. Protocol documentation
must be available in the workbench before a learner writes a candidate. Tests
derive service-side intent from received rows, then separately compare it to
controller expectations. Do not retain unit tests that silently supply a
private intent literal as evidence of legitimate candidate input derivation.

Conformance fixes touch `executor/tokenfactory.py`, `evaluator/evaluator.py`,
`orchestrator.py`, `sealed/store.py` and the relevant executor/privacy tests.
They implement the already approved driver trust, honored-commitment,
supported-claim, complete-trace and serialized-privacy requirements. No new
storage table, schema, technology, mission or inference permission is added.

## Exact operator packet already approved

The latest user instruction includes "I authroize the git authorization and
the operator material approval". Its material target is the already presented
`slice22b-protected-retry-amendment.md` packet:

| Item | Exact value |
| --- | --- |
| Local proposed file | `evidence/slice22b-traces-2026-10-04/northline_deployment_v2.proposed.json` |
| Applied destination after Gate 3 approval | `shiftwork/sealed/cases/northline_deployment_v2.json` |
| Bytes | 18847 |
| Raw SHA-256 | c1f3c8d3369b6eeca61f8fba8a4ab4829a248a9887e14c4257d5b30a6ab56798 |
| Canonical cases seal | 31cab9afaeed92d6421a045f49b33ae48079ef08ca2a682f7cc6b4a9647fbcfe |

Apply exactly those bytes, retain v1 and every original reviewed pin, add the
one new literal pin and `-text` attribute, and point only the deployment family
to v2. Retain application receipts. The v2 control changes only case 02 request
and matching spec text. Cycle, expected refs, all state deltas and five other
variant refs remain unchanged. No inventory refill, exposure refund or budget
increase follows. Historical reservations stay on frozen snapshots. Never
reopen or rewrite their records, outcomes or history. After application, verify
admission, historical snapshot replay, never-reuse behavior and checkout bytes.

No further operator material permission is needed for this exact packet. Any
additional reviewed fixture change remains outside that approval.

## Publication and acceptance boundaries

Explicit Gate 3 approval now authorizes the focused design commits,
merge and main push. The candidate list in the original
independent review gains exactly these design artifacts:

- `docs/northline-deployment-protocol.md`
- `docs/plans/shiftwork/slice22b-gate3-review-corrections.md`
- `docs/plans/shiftwork/slice22b-review-repair-plan.md`
- `docs/plans/shiftwork/evidence/slice22b-review-repairs-2026-10-04/publication-summary.json`

Unfinished S22b runtime/tests, private fixtures, instructions and raw evidence
remain outside that design publication scope. Preserve the index and unrelated
dirty bytes; use a separate clean checkout for publication. Recheck the exact
staged list, main divergence and remote result. No bulk staging or co-author.

Five conformance repairs and deterministic input diagnostics are offline proof.
Gate 3 approval is design approval. Exact material application, full S22b
completion, user acceptance, live inference, Sandbox isolation and learning
transfer remain distinct. No live calls, installs, credential use, outreach,
deployment or later-slice work follows from this correction.

## Verification at this checkpoint

Final full offline suite: 934 passed, 1 skipped, 2 warnings; packaging
excluded. Focused source checks: 148 passed; privacy group: 22 passed.
Thirteen clean controls pass and thirteen separate source omission faults
each reach one named assertion failure with zero setup errors and exact
restoration. Input diagnostics match 13/13 received-input intent values
and observe one public first/retry write. All 41 reviewed pins match.

The initial expanded full run returned 2 failed, 932 passed, 1 skipped.
Both failures came from slash-form path needles inside base64. The final
scanner adds that encoded form; the failed full run and failed clean
mutation control remain retained. No result is labelled flaky.

Raw proof and authorization: `evidence/slice22b-review-repairs-2026-10-04/`.
These local receipts are excluded from the design publication except for
its bounded publication-summary.json. Gate 3 approval is recorded above.
The 934-pass suite applies to the retained dirty runtime tree, outside this
design-only publication. Publication receipts remain local in
evidence/slice22b-gate3-publication-2026-10-04/.
