# S50 protected host implementation

The user's 2026-10-27 approval covers the separate host design, deployment,
bounded provider calls and recording. Existing credits only, no paid hosting or
top-ups. This scoped design implements that direction. It does not reopen the
product gates or grant publication, submission or legal-acceptance authority.

## Plan and files

New executable work and receipts live in the fresh owned directory
`/Users/jayd0/Documents/Codex/2026-10-27/shiftwork-s50-protected-host-v1/`.
The frozen session-controls kit and all prior stores remain immutable.

1. Verify preservation and the existing hosted/budget tests before changes.
2. Implement `s50_host.py`, an ASGI admission wrapper over `create_app` with an
   explicit tokenfactory executor. Do not call `create_hosted_app`. Boot has no
   network side effect. Never configure the coach. Keep the original application
   and shared host untouched.
3. Implement `s50_transport.py`, one session's cumulative transport guard and
   SDK/inference adapters. Inspect the pinned SDK interfaces before use. Prove
   no SDK retries, hard deadlines, retained failed sends and bounded cleanup.
4. Test the authenticated reads, frozen writes, boot/state/build identity,
   concurrency, restart and failure boundaries independently. Then prove the
   complete task-plan live composition offline with authored upstream doubles.
5. Implement and test the browser capture bridge in a new output directory.
6. Freeze a deployable source overlay, exact transport policy and capture setup.
   Verify private credit-only treatment before dispatch. Freeze the actual
   deployment and boot before admitting the sole recording sequence.
7. Retain the full original, verify the same-store chain independently, review
   all media, edit below 180 seconds and prepare evidence-grounded submission copy.

## Access and ownership

One process, one fresh SQLite path, one lifetime admission. Refuse an existing
output/database directory. Every boot starts locked and has a random boot ID.
An external durable controller marker binds the admitted boot and cannot re-arm
after a restart. No automatic startup permission call exists in this composition.
At most one explicitly admitted whoami check is allowed after capture starts.

Protect static files and API reads with a viewer secret in a Secure, HttpOnly,
SameSite=Strict cookie, or a dedicated header for the capture bridge. The local
offline proof uses a synthetic secret. A distinct controller secret is required
for admission and every mutation. Reject ambiguous/duplicate auth headers,
cross-origin mutations, query secrets and unsupported protocols. No secrets go
in URLs, source, logs, evidence or footage. Secure credential setup remains an
owner action when no private reuse route is available.

`GET /s50/status` is controller-only and exposes safe build/boot/state digests,
step and counter state. `POST /s50/admit` accepts only the frozen packet matching
the actual boot, build and logical database snapshot. A controller mutation must
match the next exact method, path and resolved JSON payload. Browser writes,
coach, reset and all unlisted mutations are denied. A valid controller denial
closes its session; an unauthenticated visitor cannot consume an action.

The wrapper buffers the response until the application's background work finishes,
then verifies final state. It journals reservation before invoking the inner app.
It binds each result and new snapshot before the next mutation. A second writer
or state/build drift closes the action. Selection remains an explicit choice
after actual eligibility; no candidate is preselected by the rehearsal.

## Types and call stack

```python
def file_pin(path: Path) -> dict: ...
def database_digest(path: Path) -> str: ...
class ProtectedSession:
    def __init__(self, root: Path, identity: dict, observe): ...
    def admit(self, packet: dict) -> None: ...
    async def __call__(self, scope, receive, send) -> None: ...
class SessionTransport:
    def reserve(self, category: str, operation: str | None = None) -> float: ...
    async def request(self, category: str, send, *, operation=None): ...
```

Authenticated admission -> exact identity/state check -> durable frozen packet ->
one-time session arm. Mutation -> match frozen step -> reserve full action envelope
-> inner existing route -> real executor and gateway through cumulative transport
-> independent result verification -> durable response/state snapshot -> next step.

## Transport policy to prove before live use

Whole session ceilings are 44 inference reservations and 26 spawn attempts.
At most one whoami request is separate. No provider or spawn retries, fallback,
replacement store or coach. Existing 20-second inference, 20-second SDK HTTP and
45-second workspace deadlines remain ceilings, each clamped to the session's
remaining wall time. A session may last at most 1,800 seconds.

Proposed control-plane policy: at most 200 same-operation event requests per
spawned operation and 5,500 ordinary Sandbox HTTP requests across the session.
Same-operation stream resumes stay within these bounds and the existing maximum
of three stream-error resumes. A stream error is preserved; a new spawn is never
a resume. Terminal cancellation has a separate allowance of one attempt per
known nonterminal operation, at most 26, with five seconds per cleanup request.
Cleanup cannot upload, spawn or infer. These numeric bounds need tests and SDK
path classification proof before deployment, not just journal reservations.

The installed SDK retries only when a RetryPolicy is supplied. The recording
composition explicitly selects `RetryPolicy(max_attempts=1)` and proves one HTTP send on
429/500. A timeout cancels the local pending transport; remote termination needs
a retained cancellation receipt and is never inferred from a client timeout.

The control must cover both SDK request and streaming transports, plus every
inference gateway created by the executor. ASGI cancellation alone does not stop
the synchronous background task's worker thread. The transport checks and clamps
the absolute deadline within that thread's event loop. Its own client handles
must be closed and cancellation results retained even though the existing adapter
swallows cancellation failures. Zero stream-error resumes are admitted by the
initial implementation; ordinary same-operation event polling stays bounded.

## Remaining owner/setup constraints

Render dashboard access is available. Its new-service draft was changed to Free
and manual deployment, with no service created. The dashboard initially selected
the paid USD 7 plan, so the Free selection must be reverified before creation.
No Render/Docker installation is needed for dashboard inspection.

Token Factory Payments displayed USD 27.22 on this date. This is an observed
account balance, not proof of grant type, Sandbox pricing, tax, no overage or an
all-in execution cap. Those remain hard dispatch blockers until verified.
No old dollar projection or earlier slice's allowance applies.

Render accepts Git or image sources. Git/registry publication is excluded. A
private, verified source overlay delivered as service configuration may avoid
publication, but must be proved end to end before treating it as deployable.
Free filesystem loss means retained host state must be exported before idle or
restart. A restart stops the recording; it never grants another attempt.

## Evidence limits

The entry receipt matches all 272 kit, 1,840 protected, 1,882 prior preparation
and 2,808 frozen pins, plus seven worktree references/indexes. It also matches
2,032 current inherited target file pins. No live action or recording follows
from these checks. All implementation and proof items above are pending until
their actual receipts exist. S50 and S49 remain incomplete; S46 stays excluded.
