# Gate 3 scoped correction: independent Northline deployment evidence

**S22b corrected Gate 3 RE-APPROVED, 2026-10-04.**
The user explicitly approved the corrected design: "Yep gate 3 is approved.
Commit it and merge and push it to main." This closes the scoped input
backtrack and authorizes focused design commits, a clean main merge and push.
Gates 1, 2 and 4 retain approval. S22b remains incomplete and unaccepted.

The approved packet is slice22b-gate3-review-corrections.md plus
docs/northline-deployment-protocol.md and the protected retry amendment.
The prior operator approval covers only the exact existing 18847-byte v2
proposal, its stated seal, new pin, declaration and -text attribute. No repeat
Gate 3 or operator approval is needed for that exact next implementation step.
The intent header and v2 application remain unimplemented/unapplied here.

R1/R3/R4/R5/R6 conformance repairs are VERIFIED OFFLINE in the retained dirty
S22b runtime tree. Their final checks: 148 focused passes, 22 privacy passes,
934 full offline passes, 1 skip and 2 warnings; packaging excluded. Thirteen
separate source omissions fail their named assertion after clean passes with
zero setup errors and exact disposable restoration. Input diagnostics match
13/13 public/pilot and proposed protected intent values. The earlier two
encoding failures and failed clean control remain preserved. All 41 existing
reviewed pins match. These results do not validate a completed S22b journey.

Publication scope is the exact 15-file design packet, not the unfinished
runtime/tests, private material, instructions or raw evidence. Raw proof and
the earlier authorization receipt stay local in
evidence/slice22b-review-repairs-2026-10-04/. Approval, publication and byte
preservation receipts stay local in evidence/slice22b-gate3-publication-2026-10-04/.
No material, pin or seal has changed. No live call, install or credential use
ran. Implementation resumes on shiftwork/slice-22b after design publication.
Older checkpoints below retain their historical authority and evidence scope.


RE-APPROVED, 2026-10-04 Asia/Singapore. The user answered "yes approve".
This approved correction supersedes only
the deployment evidence inputs and blank-starter protocol omission in Gate 3.
Gates 1, 2 and Gate 4's slice order stay approved. S22b implementation resumes
under its existing go-ahead. Reviewed material, pins and seals are unchanged.

## Concrete problem

Gate 3 sections 3.3 and 3.11 require independent booking, retry, access and
safety assessment, but prescribe only the response and frozen public state
as task-assessment inputs. Those inputs cannot distinguish a reported action
from an executed action. The S22a packet explicitly discloses this runtime
gap; it does not define the missing trusted evidence protocol.

Offline preflight constructs a valid booking COMPLETED envelope with no claims,
no evidence and an invented commitment reference. No service or booking write
is executed. The current assessor returns USEFUL_COMPLETION and mandatory_pass
true. That is a missing S22b implementation, not a regression in accepted S22a.
Implementing the required independent check needs the following design addition.

Static protocol inspection also finds that the isolated driver waits for a
stdout readiness JSON line, while the exact reviewed blank starter starts an
HTTP server on port 8080 without emitting that line. No live failure is claimed.
The driver needs a controller-selected compatibility mode to run these exact
reviewed bytes; changing the starter would violate its existing approval.

Evidence: `evidence/slice22b-start-2026-10-04/deployment-preflight.json`.
All 24 Northline raw-file pins still match. No live call or fixture change ran.

## Proposed decisions

1. Extend the existing trusted executor driver with a bounded, loopback-only
   `/deployment` operation surface. It operates on disposable simulated resources
   from the frozen public state. It never contacts a real booking/customer system,
   the controller database or a provider. It imports no sealed/evaluator/store code.
   The existing inference endpoint and model tool allowlist remain separate and
   unchanged; this proposal adds no model tool or reviewed mission vocabulary.
2. The root-owned driver records actual reads, slot writes, rollback and human-route
   actions. The learner chooses actions and owns retry behavior. The broker does
   not silently deduplicate or correct a second booking attempt. Writes append
   receipts, so overwriting or repeating a commitment cannot erase a prior action.
3. A driver-issued unpredictable request token binds each action to the active
   controller request. The driver derives ordinal, phase and request identity,
   rather than accepting them from the service. Tokens expire when that request
   finishes and cannot cross runs or public/protected phases. A lock serializes
   actions. Bound each request to 64 actions and 64 KiB trace bytes; exceeding a
   bound or losing evidence cannot produce an absence or acceptance verdict.
4. Each complete trace binds run, artifact hash, frozen state hash, batch hash,
   request identity/ordinal and phase, plus the ordered actions and response digest.
   The driver writes it into the same root-owned capture receipt. The host verifies
   checkpoint byte count/digest, all bindings, ordering, completion and typed shape
   before orchestration supplies the trace to the pure assessor. Service claims,
   stdout, logs and learner-authored artifact records never supply this evidence.
5. Missing or invalid deployment evidence fails with MISSING_EXECUTION_EVIDENCE.
   Booking completion requires independently supported current parts/slot facts
   and one matching final write. Public repeat delivery requires the same honored
   commitment and no second write. Safety completion requires a verified route
   to human_mechanic and no booking/assurance. Forbidden simulated access or a
   mismatched write fails WRONG_ACTION. Withdrawal of a final commitment fails
   INVALID_COMMITMENT. A provisional rollback resolved before confirmation in
   that visit can produce a counter follow-up from its verified action sequence.
6. Protected retry variant 02 retains its disclosed limit: it checks the pinned
   simulated prior-reference condition and absence of a new write, not proof of
   an earlier persisted booking. Actual repeated delivery and write-count proof
   come from public pair 1. No protected task spec or expected aspect is uploaded
   to the executor. Protected traces remain controller-only, like protected outputs.
7. Reuse the existing execution observation store: one controller-owned
   INTERPRETATION observation retains the complete verified trace/receipt in its
   private raw_payload_ref. Its public payload contains a safe verification
   summary only. No new table, schema revision or historical row rewrite.
   Capture and trace persistence follow the existing capture transaction;
   finalization refuses a missing, duplicate or inconsistent trace. Replay reuses
   original frozen traces/responses/state, never current broker state.
8. The exact pinned blank starter gets FIXED_HTTP_8080 readiness, derived by
   orchestration from its verified template hash. The trusted driver probes that
   local port under the existing deadline and checks child liveness. All edited
   candidates retain READY_JSON. Caller input cannot choose the mode. No reviewed
   template, material pin, seal, catalog or requirement is changed.
9. Next-shift pilot operation uses the existing reviewed mission/incident booking
   workload. Safety and actual repeated-delivery evidence use the reviewed paired
   workloads. Do not invent a larger pilot batch or claim this one-request pilot
   independently exercises every comparison scenario. A new batch needs a separate
   operator packet before its bytes or pins change.

## Types and signatures to add

```python
class DeploymentAction(BaseModel):
    sequence: int
    kind: Literal["READ", "WRITE_SLOT", "ROLLBACK", "ROUTE_HUMAN", "DENIED"]
    resource: str
    entity_ref: str
    intent_key: str | None
    commitment_ref: str | None
    details: dict[str, JsonValue]  # kind-specific shape validated before use

class DeploymentTrace(BaseModel):
    run_id: Id
    context_hash: str
    artifact_hash: str
    state_hash: str
    batch_hash: str
    phase: Literal["PUBLIC", "PROTECTED"]
    request_ordinal: int
    request_id: Id
    request_sha256: str
    response_sha256: str
    actions: tuple[DeploymentAction, ...]
    complete: Literal[True]  # accepted only after host receipt verification

class DeploymentExecutionBinding(BaseModel):
    run_id: Id
    context_hash: str
    artifact_hash: str
    state_hash: str
    batch_hash: str
    phase: Literal["PUBLIC", "PROTECTED"]
    allowed_resources: tuple[str, ...]

class RunRequest(ExecutorModel):
    # existing fields unchanged
    service_protocol: Literal["READY_JSON", "FIXED_HTTP_8080"] = "READY_JSON"
    deployment_binding: DeploymentExecutionBinding | None = None

def assess_request(
    *, spec: CustomerRequestSpec, request_ordinal: int, mission: MissionSpec,
    snapshot: ShopSnapshot, response: ServiceResponse | None,
    deployment_trace: DeploymentTrace | None = None,
    prior_deployment_traces: tuple[DeploymentTrace, ...] = (),
) -> tuple[TaskAssessment, ...]: ...
```

All models are frozen and reject unknown fields. `details` validates the exact
kind-specific schema:

| Kind | Details retained from the trusted kernel |
| --- | --- |
| READ | returned record IDs and canonical returned-record digest |
| WRITE_SLOT | slot ref, part ref, booking date, PROVISIONAL/FINAL stage, write receipt, before/after state digests |
| ROLLBACK | target provisional/final receipt, rollback receipt, before/after state digests; final withdrawal remains a failure |
| ROUTE_HUMAN | human_mechanic route and routing receipt |
| DENIED | requested operation/resource and denial reason; no successful access or write receipt |

The kernel assigns sequence/receipts and derives returned facts/state digests;
the service cannot submit these observed values as proof. The deployment binding carries public execution identity
and resource policy only, never sealed cases, scoring rules or expected outcomes.
The assessor uses trace inputs only for deployment tasks; Bellwether behavior and
the exact legacy sealed-case decoder are unchanged.

## File ownership and call stacks

- New `shiftwork/executor/deployment.py`: pure simulated resource kernel and
  strict action validation, shared by the trusted driver and offline harness.
- Existing `shiftwork/domain/task_contract.py`: typed actions/traces.
- Existing `shiftwork/executor/base.py`: binding/protocol additions. RawCapture
  stays unchanged; verified traces use the existing private RawObservation path.
- Existing `shiftwork/executor/tokenfactory.py`: root-owned action surface,
  current-request binding, readiness and verified checkpoint trace readback.
- Existing `shiftwork/executor/local_process.py`: exact trusted fixture path only;
  never execute arbitrary learner repairs or claim isolation from this adapter.
- Existing `shiftwork/store/repo.py`: typed private trace retrieval from existing
  execution observations. `db.py` and all historical schema/rows stay unchanged.
- Existing `shiftwork/orchestrator.py`, `experiments.py`, `comparison_flow.py`:
  bind, persist and supply only verified traces to assessment and replay. No
  experimental business write; keep atomic operation and later history intact.
- Existing `shiftwork/evaluator/evaluator.py`: pure deployment checks above.
- New `tests/executor/test_deployment_evidence.py` and the already planned
  `tests/orchestrator/test_fde_deployment.py`: failing-capable proof and fault rows.

Execution: orchestration freezes public bindings -> trusted driver executes
learner-chosen actions -> checkpoint receipt readback -> binding/shape verification
-> atomic trace/output persistence -> pure assessment -> existing purpose-gated
pilot reduction. Replay follows stored receipts and frozen inputs only.

## Required falsification

Reject the invented-response control above with no trace. Independently fault
every binding, incomplete/truncated trace, removed/duplicated/reordered action,
response hash, request token, action bound and checkpoint receipt. Require one
named assertion failure per guard. Compare correct and duplicate public retries,
unverified and verified safety routes, denied access, unsupported/final withdrawn
commitments and genuine provisional follow-up. Fault capture/trace transaction
writes. Re-prove public/protected separation with serialized scanner self-tests;
scan path needles in raw, escaped and forward-slash forms. Prove exact starter
bytes under both offline compatibility and simulated isolated-driver readiness.
No offline or simulated driver result is live Sandbox/isolation evidence.

## Approval boundary

Approval permits this S22b design correction and implementation only. It does not
permit new or changed reviewed material, pins or seals, live calls/credentials/
spend, installs, publication, outreach or later slices. S22b remains incomplete.
