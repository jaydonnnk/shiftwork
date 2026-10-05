# S22b session handoff: 2026-10-04

Completed: received-input intent header, public workbench protocol and exact approved v2 application are verified offline. S22b remains incomplete and unaccepted.

Decisions: intent metadata comes from received inputs, while original bodies remain byte-identical. V2 adds one pin and preserves v1 as private historical material. Test packages include explicitly pinned history rather than weakening privacy.

Working agreement: already-granted Gate 3/operator approvals are not requested again. Runtime publication and live work are outside this step.

Files changed this session, excluding prior dirty work:

- `shiftwork/executor/deployment.py:18-41`: received-input derivation; retained kernel
- `shiftwork/executor/tokenfactory.py:73; 206-214`: trusted function loading, deployment header, original-body delivery
- `shiftwork/client/index.html:123-127`: public protocol before editor
- `shiftwork/packs/registry.py:193; 274`: one new literal pin; deployment family points to v2
- `.gitattributes:48`: exact v2 -text path
- `tests/executor/test_deployment_evidence.py:18; 74-75`: intent helper derives from received request rather than task conditions
- `tests/packs/test_projection_inventory.py:22`: draft fault targets active family
- `tests/packs/test_northline_review.py:33; 71-72`: 25 pins and active v2 seal controls
- `tests/packs/test_seeding.py:33-40`: historical sealed pins included in disposable privacy package
- `tests/sealed/test_sentinel_leak.py:107-114`: active/historical inventory copied before sentinel injection
- `tests/api/test_workplace_boards.py:39-43`: missing-review fault targets current declared family
- `tests/orchestrator/test_fde_deployment.py:117; 163; 230`: active family binding in typed-aspect and draft faults
- `shiftwork/client/northline-deployment-protocol.html:1-35`: new file: public protocol, exact approved packet or regression proof
- `shiftwork/sealed/cases/northline_deployment_v2.json:1-527`: new file: public protocol, exact approved packet or regression proof
- `tests/executor/test_deployment_intent.py:1-162`: new file: public protocol, exact approved packet or regression proof
- `tests/packs/test_northline_v2.py:1-191`: new file: public protocol, exact approved packet or regression proof
- `docs/plans/shiftwork/00-status.md:3-12`: current applied/verified checkpoint prepended; historical text retained
- `docs/plans/shiftwork/03-program-design.md:3-12`: current applied/verified checkpoint prepended; historical text retained
- `docs/plans/shiftwork/slice22b-implementation-plan.md:3-12`: current applied/verified checkpoint prepended; historical text retained
- `docs/plans/shiftwork/slice22b-protected-retry-amendment.md:3-12`: current applied/verified checkpoint prepended; historical text retained
- `docs/plans/shiftwork/slice22b-gate3-review-corrections.md:3-12`: current applied/verified checkpoint prepended; historical text retained
- `docs/SHIFTWORK_PLAN.md:3-7`: supporting brief updated
- `docs/northline-deployment-protocol.md:3-7; 27-30`: header/application status reflects implementation
- `MISTAKES.md:1938-1976`: new diagnosed failures appended; prior bytes preserved
- `docs/plans/shiftwork/slice22b-intent-v2-offline-checkpoint.md`: complete bounded report; raw receipts live in its referenced new evidence directory.

Open work and traps are recorded in the copy-paste prompt below. Preview was served at http://127.0.0.1:8022/northline-deployment-protocol.html; a future session must verify that process is still available.

## Prompt for New Chat

```text
This is background context for Shiftwork S22b, not a new approval.

Workspace: C:\Users\jayd0\OneDrive\Desktop\nebius_nvidia
Branch: shiftwork/slice-22b
HEAD, local main and origin/main: 157505ecd2f04ddc3fc86c0593771043af0d8325
Gate 3's 15-file design packet is published. Runtime work remains dirty, uncommitted and unpublished. S22b is incomplete and unaccepted. Gate 3 and exact operator material approval are already granted; that scope needs no repeat approval.

The latest completed offline step implemented derive_intent_key(request_id, text), wired X-Shiftwork-Intent-Key through the root-owned deployment kernel, and exposed the public action protocol before the workbench editor. Derivation uses received inputs only. All 13 public/pilot/protected inputs, original body bytes and hashes, malformed/conflicting tokens and unchanged Bellwether wire were verified.

The approved v2 packet is applied at shiftwork/sealed/cases/northline_deployment_v2.json:
18847 bytes; SHA-256 c1f3c8d3369b6eeca61f8fba8a4ab4829a248a9887e14c4257d5b30a6ab56798
Canonical seal: 31cab9afaeed92d6421a045f49b33ae48079ef08ca2a682f7cc6b4a9647fbcfe
Its literal pin, deployment declaration and -text attribute are applied. V1 and all original 24 Northline pins are retained. Cycle stays 1. Only case 02 request/spec text changes. Frozen v1 reservations and exposure history remain intact; unchanged variants cannot be reused. The protected prior reference is customer-provided simulation, not proof of an earlier booking.

Current records:
- AGENTS.md and its required documents
- docs/plans/shiftwork/00-status.md
- docs/plans/shiftwork/slice22b-intent-v2-offline-checkpoint.md
- docs/plans/shiftwork/slice22b-implementation-plan.md
- docs/plans/shiftwork/slice22b-gate3-review-corrections.md
- docs/northline-deployment-protocol.md
- docs/plans/shiftwork/slice22b-protected-retry-amendment.md

Latest raw receipts: docs/plans/shiftwork/evidence/slice22b-intent-v2-2026-10-04/
summary.json, application.json, windows-checkout.json and preservation.json contain the bounded results. Earlier R1/R3/R4/R5/R6 and publication evidence remains unchanged.

Verification: 234 focused passes; 90 shared-fixture regression passes; final full offline suite 997 passed, 1 skipped, 2 warnings in 430.03s. Packaging excluded. Sixteen separate omission controls reach intended assertions after clean passes, with exact restoration. All 42 reviewed Windows-checkout hashes match. Serialized active/historical privacy, frozen v1 loading, zero replay writes and never-reuse were verified. Desktop 1440px and mobile 390px protocol rendering were inspected. git diff --check passed; index remains empty.

Full command:
.venv313/Scripts/python.exe -m pytest tests --ignore=tests/packaging -q --tb=short

Traps: the first expanded full suite had 4 failures from stale active-family and incomplete historical privacy fixtures; their corrected tests pass. Failed raw receipts remain. Removing -text inherits text eol=lf and may preserve today's LF bytes; do not invent a conversion failure. Actual preview key is SHIFTWORK_DB_PATH. One-shot recording/publication scripts were not rerun and must remain retained. The current implementation-plan checklist has historical unchecked entries despite partial delivery; the new checkpoint is authoritative for this completed step.

The next unfinished offline proof is the owning-pack six-slot comparison, exact prior-starter selection, experimental zero-business-effect, starter-shift operation limit and next-shift inheritance. Pilot/rollout, handover, workplace selector, native six-station UI, served-source journey faults and final architect cleanup remain incomplete. Live calls, credentials, installs, runtime publication and later slices remain separately authorized. Existing dirty source, tests, instructions, reviewed bytes and raw evidence require preservation.

Wait for instructions before taking any action.
```

## Prompt for Handoff Review

```text
Review only the completed S22b intent-header and exact v2 application checkpoint in C:\Users\jayd0\OneDrive\Desktop\nebius_nvidia on shiftwork/slice-22b. HEAD/main/origin/main remain 157505ecd2f04ddc3fc86c0593771043af0d8325. The runtime is dirty and unpublished; S22b completion and acceptance are not claimed.

Be unbiased, thorough and honest. Assume the work may be flawed. Measure it against AGENTS.md, the approved Gate 3 corrections, public deployment protocol and protected-retry amendment. Inspect the actual changes and receipts in docs/plans/shiftwork/evidence/slice22b-intent-v2-2026-10-04/. Re-run proportional offline tests and independently challenge received-only intent derivation, exact body binding, all 13 inputs, exact v2 bytes/seal/pin/declaration/attribute, preserved v1/pins, frozen historical loading, never-reuse and serialized privacy. Verify that omission controls fail for the intended reason. Green output is not proof; do not pass tests for the sake of passing. Flag weak assertions, shortcuts, hidden assumptions and scope creep.

The claimed final suite is 997 passed, 1 skipped, 2 warnings, packaging excluded; 16 omission controls and 42 checkout pins are claimed. Earlier failed receipts are retained. Preserve dirty work and historical evidence; no live calls, credentials, installs, material changes or publication are authorized by this review.

Report PASS / ISSUES FOUND / FAIL with precise files, line numbers and reproducible evidence. Deliver your verdict and wait for instructions.
```
