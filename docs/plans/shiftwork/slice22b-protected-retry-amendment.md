# S22b protected retry input correction

**S22b intent/v2 offline step APPLIED, 2026-10-04.**

The approved received-input derivation and trusted intent header are implemented.
The exact 18847-byte v2 packet, literal pin, seal, deployment declaration and
`-text` attribute are applied. V1, original pins and existing raw evidence are
preserved. Current verification and limits: [intent/v2 checkpoint](slice22b-intent-v2-offline-checkpoint.md).
S22b remains incomplete, unaccepted and unpublished. Older unimplemented/unapplied
notices below describe their original checkpoints. Final full offline verification:
997 passed, 1 skipped, 2 warnings; packaging excluded. No live call, credential,
install, later slice or Git publication follows.


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


Scoped Gate 3 RE-APPROVED. Exact operator material approval GRANTED.
2026-10-04 Asia/Singapore. No reviewed file, pin or seal has changed.

## Reproduced blocker

Protected deployment variant 02 requires the response's commitment reference
to equal a private task-condition literal. The executor receives only its
request row and resolved public state in a fresh workspace. Neither carries
that reference; its state delta is empty, and the broker starts with zero writes.
Thus a service cannot recover the expected previous commitment from its inputs.
Copying the private expected value into a candidate would conceal the defect.

The offline diagnostic uses a real empty kernel trace and zero service executions.
A service-chosen reference returns DUPLICATE_COMMITMENT; supplying the private
literal in a unit control passes. This proves the input gap, not a successful
deployment or an earlier persisted booking.
Receipts: `evidence/slice22b-traces-2026-10-04/retry-visibility.json` and its helper.

Gate 3's approved trace correction decision 6 retains a simulated prior-reference
check, but omitted how the service receives that prior reference. This narrow
decision needs correction. Other trace decisions remain approved.

## Exact proposed input

Create a versioned protected family at
`shiftwork/sealed/cases/northline_deployment_v2.json`. Preserve the complete
original `northline_deployment.json` bytes and its existing reviewed pin.
Only variant 02's request text and matching task-spec text change to:

> Retry the previously confirmed protected 10:00 brake-pad repair for counter intent northline-protected-retry-intent. Its existing stable commitment reference is northline-protected-existing-commitment. Return that reference without a new booking write.

Every condition, expected aspect, ID, ordinal, state delta and other case stays
identical. Cycle remains 1: this is a correction of the same inventory, not a
refill or permission to expose old variants again. Unchanged variants retain
their opaque refs and the existing never-reuse exposure rule. Old reservations
retain their original payload/state snapshots and verdicts; none is rewritten.

The corrected request is a customer-provided simulated prior reference. The
controller still checks the returned reference and the absence of a new write
independently. Actual repeated-delivery persistence evidence remains public pair 1.
Do not claim the protected case proves that an earlier booking really occurred.
The protected task spec, conditions and expected aspect remain controller-only.

## Concrete unapplied operator packet

The complete proposed file is
`evidence/slice22b-traces-2026-10-04/northline_deployment_v2.proposed.json`.
It is a local proposal outside the executable sealed inventory.

| Binding | Proposed value |
| --- | --- |
| File bytes | 18847 |
| Raw file SHA-256 | c1f3c8d3369b6eeca61f8fba8a4ab4829a248a9887e14c4257d5b30a6ab56798 |
| Canonical cases seal | 31cab9afaeed92d6421a045f49b33ae48079ef08ca2a682f7cc6b4a9647fbcfe |
| Original file retained SHA-256 | d2f67e0655267698c3ac78458502d5e7e2aa582dfcf0755fcf9f348a4f6d04d6 |

The latest operator approval authorizes exactly: copy the proposed bytes to the new
path; apply their stated seal; add one literal ReviewedPin while retaining the
original 24 pins; point only Northline's deployment FamilyDeclaration to v2;
add the new exact path to `.gitattributes` with `-text`; and update binding tests
to exercise active v2 while retaining v1 preservation assertions. Preserve
authorization/application receipts and prove the proposed bytes under a
disposable Windows-style checkout before any separately authorized publication.
No other material, pin, seal, family, mission, request batch or state changes.

Retained protected history remains private. The serialized projection inventory
must include both active and historical reviewed sealed-file pins, rather than
reading only the active FamilyDeclaration. Extend the existing structural
privacy reader and orchestration inventory for those explicit pinned paths;
never admit a historical file as a second executable family. Test old and new
retry text separately with serialized positive controls and omission faults.

## Required proof after approval

Validate all six typed aspects, exact source/request/spec equality, one changed
case and unchanged non-text fields. Resolve the same state bytes for both
versions. Test a generic no-write retry using the reference from the received
request, and reject a changed reference or any new write. Prove old snapshot
replay and never-reuse refs remain unchanged. Re-run admission, public/protected
privacy self-tests, focused execution checks and the full offline suite.

## Boundary

This packet is reviewable, not applied. Gate 3 is in progress only for the
prior-reference and public intent correction. The S22b journey remains incomplete. The
current trusted trace implementation is retained and verified as a partial
checkpoint. No installs, credentials, live calls/spend, commits, pushes,
publication, outreach, deployment or later-slice work is authorized by this packet.

Historical checkpoint verification, 2026-10-04: full offline suite 898 passed, 1 skipped,
2 warnings in 405.21s, exit 0; packaging excluded. Focused group 74 passed,
2 warnings; existing selection/operation group 61 passed, 2 warnings; gateway
group 29 passed. Four disposable trace faults reach five intended failures.
All 41 reviewed pins remain exact. Proposed v2 is validated but unapplied.
S22b is incomplete; scoped Gate 3 and material approval remain pending.
