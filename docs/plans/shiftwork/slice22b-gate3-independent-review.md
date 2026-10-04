# S22b Gate 3 independent review, 2026-10-04

**Verdict: ISSUES FOUND. The current packet is not ready for approval or publication.**

Review scope: the current Gate 3 deployment correction, protected retry amendment,
S22b implementation plan, status, implementing source and raw checkpoint evidence.
This is an offline review by a fresh session, not a second-model correctness oracle,
live Sandbox proof, isolation acceptance or S22b acceptance.

Branch and HEAD verified: `shiftwork/slice-22b`,
`c7fd5c0e5e825f9fb7c036271cb2cef4f842115e`. Local main and remote main have that
same SHA; main ancestry passes. The entry index has no staged changes. All 24
existing dirty/untracked paths were preserved before the review documentation
updates. Runtime files remain byte-identical to the checkpoint.

## Findings

| ID | Priority | Finding and concrete proof | Source anchor |
| --- | --- | --- | --- |
| R1 | P1 | Learner files can run during trusted-driver imports. The fake adapter admits `secrets.py` to `/work`, launches the driver without isolated import mode, and the exact startup import header executes a harmless learner marker before driver initialization and privilege-drop code. The new `import secrets` makes this directly relevant to request-token and trace authority. | `shiftwork/executor/tokenfactory.py:53`, `:309`, `:359`; `shiftwork/orchestrator.py:662` |
| R2 | P1 | Public pair 1 requires the exact action key `northline-intent-V11`; the actual requests contain only `visit V-11`. Neither the received state nor the developer-facing reviewed policy defines that encoding. An otherwise matching write with the input-derived key `V-11` fails `INVALID_COMMITMENT`; supplying the controller condition's literal passes. The variant 02 proposal fixes its prior reference, but leaves this separate service-input contract unspecified. | `shiftwork/fixtures/requests/northline_compare_pair_01_specs.json:17`, `:60`; `shiftwork/evaluator/evaluator.py:467`; `tests/executor/test_deployment_evidence.py:69` |
| R3 | P1 | A valid first final booking can be rolled back during its retry and still receive `USEFUL_COMPLETION`, `mandatory_pass=true`. Both receipts pass host binding verification and the actual kernel write is `rolled_back=true`. The retry branch returns before rollback validation and considers earlier final writes without their subsequent withdrawal. | `shiftwork/evaluator/evaluator.py:449`, `:455`, `:472` |
| R4 | P2 | A valid booking write can accompany a `booking` claim naming `2099-01-01` and a different, unexecuted commitment reference, with no evidence refs, and still pass envelope validation and mandatory assessment. Booking checks validate claim kind/entity, but not claim value or support. | `shiftwork/evaluator/evaluator.py:483`; `shiftwork/domain/task_contract.py:604` |
| R5 | P2 | Replay reports `IDENTICAL` after each of ten trace-binding substitutions and after omission of the verified trace on the exact blank operation. The semantic binding helper rejects each altered trace, but converts the error into `{}`; the missing-task path then produces the same failure assessment and replay reports identical evidence. | `shiftwork/orchestrator.py:2577`, `:2608`, `:1266`; `shiftwork/evaluator/evaluator.py:339`, `:356` |
| R6 | P2 | The distinctive protected prior-reference literal is allowed on an injected serialized public surface because the structural needle reader omits condition values. Extending only the active/historical file inventory does not close that omission. In a disposable v2 declaration switch, old retry text also passes raw JSON, nested JSON and base64 scans despite retaining its reviewed pin; new retry text is refused. The amendment already requires the historical-reader fix, correctly, but needs separate fragment controls and omission faults too. | `shiftwork/sealed/store.py:101`; `shiftwork/orchestrator.py:2348`; `slice22b-protected-retry-amendment.md:69` |

R1 is an offline import/provisioning reproduction. It does **not** establish a live
root exploit in Sandbox. The unsafe launcher predates the current change; adding
trusted action traces depends on correcting that existing boundary.
R2 is an undocumented encoding requirement, rather than a mathematical claim that
no programmer could guess the literal. The full task-spec conditions are not runtime
service inputs. Existing unit controls read them directly, so their green results
do not prove a generic service can derive the values legitimately.
R3 and R4 use the existing controller key solely to isolate those assessor defects;
they are kernel/receipt controls, not successful candidate executions.
R5 substitutes the private observation reader in a disposable process. The real
database's append-only update guard rejects direct mutation. No production or stored
historical observation was altered. This demonstrates a replay completeness gap,
not an API path for rewriting history or falsely accepting the blank operation.
R6 is an injected positive control and a disposable declaration simulation, not an
observed public-route leak or an applied fixture switch. Generic public part, slot,
route, outcome and reason vocabulary must remain usable.

## Independent checks

- Rehashed every checkpoint source pin and all 41 reviewed material pins against
  current bytes. Checked all retained trace-fault JUnit names, failures and zero
  setup errors against the four source mutations and their raw logs. The five
  intended assertion failures are real. That is partial guard coverage.
- Verified the recorded full offline JUnit has 899 collected tests, 898 passes,
  one skip, zero failures/errors. Its raw log matches 898 passed, 1 skipped,
  2 warnings in 405.21s. Focused retained logs match 74, 61 and 29 passes.
  Those are preserved checkpoint runs, not fresh full-suite results.
- Fresh existing focused suite: **83 passed, 2 warnings in 12.28s, exit 0**.
  Files: `tests/executor/test_deployment_evidence.py`,
  `tests/orchestrator/test_fde_deployment.py`, `tests/api/test_workplace_boards.py`,
  `tests/api/test_pivot_projection.py`, `tests/packs/test_projection_inventory.py`.
  This suite covers booking, public retry, safety receipt, denied access, same-visit
  rollback, byte/digest/order guards and capture transaction rollback; R1 to R6
  show why that green result is insufficient.
- Independently parsed the six old/proposed typed cases and compared every field.
  Only case 02 request text and matching task-spec text change. Proposed bytes:
  18847; raw SHA-256 `c1f3c8d3369b6eeca61f8fba8a4ab4829a248a9887e14c4257d5b30a6ab56798`;
  canonical cases digest `31cab9afaeed92d6421a045f49b33ae48079ef08ca2a682f7cc6b4a9647fbcfe`.
  Original raw SHA-256 remains
  `d2f67e0655267698c3ac78458502d5e7e2aa582dfcf0755fcf9f348a4f6d04d6`.
- Both families retain cycle 1. All six opaque `expected_ref` values are unchanged;
  the five unchanged cases retain exact `variant_ref` values. Case 02 gets a new
  content-bound variant ref as the proposal discloses. Marking every old ref exposed
  makes no unchanged case eligible again. The corrected case alone has a different
  ref; it is not a new six-case refill, an exposure refund or a budget increase.
  All six resolved-state byte strings remain identical. The proposal is absent
  from executable inventory. Historical reservation application/replay under an
  admitted v2 remains unrun, pending design and separate operator approval.
- An additional unapplied-v2 control extracts the prior reference and intent only
  from the received customer text. Its empty kernel trace passes the current retry
  assessor; changing the reference or adding a booking write fails. This confirms
  the narrow variant 02 input repair while leaving R2's public key problem open.
  It is an offline input/assessment control, not a successful candidate service.
- The current checkpoint and docs clearly distinguish offline, trusted-local,
  simulated driver, live, isolation, design approval and slice acceptance. No
  current live success, hostile-code isolation or completed S22b claim is supported.

Fresh raw controls, commands, source preservation and receipts:
`evidence/slice22b-gate3-review-2026-10-04/`. Old failed/interrupted receipts and
one-shot document updater scripts remain untouched and were not re-executed.
The first additional-review helper stopped on the append-only observation trigger;
its failed preimage and tool-output receipt are retained. The corrected helper
uses a read substitution, preserving the actual database guard.

## Required disposition before approval

1. Define a public, deterministic intent-key contract from actual request/state
   inputs. Validate the entire public/protected input inventory against it. Do not
   copy sealed conditions into a candidate. Any additional reviewed material change
   requires a separately scoped operator packet; the current v2 bytes are retained.
2. Keep learner code out of all trusted startup imports. Use isolated driver imports
   and an explicit trusted-kernel load; independently test hostile sibling modules
   and imported dependencies. A filename blacklist alone is insufficient.
3. Assess the ordered booking state across request boundaries before retry success.
   Any final withdrawal fails; provisional rollback remains a same-visit follow-up.
4. Define and enforce booking claim value/evidence semantics. Unsupported or
   contradictory claims must fail even when the actual write is otherwise correct.
5. Require complete verified traces before deployment finalization/replay, including
   missing-task and invalid-output paths. Missing/invalid evidence cannot return an
   unqualified `IDENTICAL` replay. Preserve original historical results.
6. Finish active and historical inventory coverage, plus protected-only distinctive
   intent/reference fragments. Use serialized positive controls and separate source
   omission faults for active v2, retained v1 and each new field branch. Preserve
   raw, escaped, slash, nested JSON and base64 controls and structural provenance.

These are proposed corrective requirements, not a new approval receipt or a
silently revised fixture. Gates 1, 2 and 4 remain approved. The original trusted-trace
correction's approval remains historical authority for its scope. Gate 3's input
amendment remains IN PROGRESS; S22b remains incomplete and unaccepted.
Design omissions need a revised, reviewable Gate 3 packet and explicit user approval.
Implementation nonconformance must be repaired and falsified during S22b. No Gate 2
technology or storage boundary change is proposed by this review.

## Exact candidate publication scope

No file is staged or committed. This is the bounded candidate packet for a future
corrected and explicitly approved Gate 3 publication; it is not eligible today.
The user's current instruction already authorizes its focused commits, merge and
main push **once Gate 3 is approved**, so no repeat Git permission is required.
Recheck and finalize this list against the corrected packet before staging:

| Kind | Exact repository path |
| --- | --- |
| Design | `docs/plans/shiftwork/03-program-design.md` |
| Authority/status | `docs/plans/shiftwork/00-status.md` |
| Supporting brief | `docs/SHIFTWORK_PLAN.md` |
| Approved trace correction | `docs/plans/shiftwork/slice22b-gate3-deployment-evidence.md` |
| Pending input amendment | `docs/plans/shiftwork/slice22b-protected-retry-amendment.md` |
| Incomplete implementation plan | `docs/plans/shiftwork/slice22b-implementation-plan.md` |
| Independent review | `docs/plans/shiftwork/slice22b-gate3-independent-review.md` |
| Minimal initial diagnostic | `docs/plans/shiftwork/evidence/slice22b-start-2026-10-04/deployment-preflight.json` |
| Minimal retry diagnostic | `docs/plans/shiftwork/evidence/slice22b-traces-2026-10-04/retry-visibility.json` |
| Minimal proposal validation | `docs/plans/shiftwork/evidence/slice22b-traces-2026-10-04/amendment-preflight.json` |
| Reviewed evidence summary | `docs/plans/shiftwork/evidence/slice22b-gate3-review-2026-10-04/publication-review-summary.json` |

Raw capture/trace receipts, executable test helpers, private full proposed fixture,
all unfinished runtime/tests, `AGENTS.md` and `MISTAKES.md` stay outside that packet.
Raw evidence remains local and linked as such; do not imply every local raw link
resolves from a published checkout. Do not force-add the ignored evidence directory
as a whole. A future publication must verify the exact staged path set and retain
all unrelated working bytes, then use a separate clean checkout for the main merge
if switching this dirty checkout would endanger them. Verify remote divergence,
merge tree, push result and final remote SHA; return to `shiftwork/slice-22b`.

Operator approval for the proposed material, seal and pin is still separately
pending. Gate 3 publication will not supply it. After publication, resume the
approved S22b offline plan while dependent material work remains pending. No S23,
installation, credential use, live calls/spend or deployment follows from this review.
