# S50 isolated recording host proposal

Status: PROPOSED, NOT APPROVED. This is the next hosting/access-boundary decision,
not approval to record, deploy, publish code or spend credits. Existing product
gates remain approved for their existing scope. This proposed recording-only
extension needs the applicable scoped architecture and program-design review.

## Why the existing host is not ready for this action

The current source composes a public shared FastAPI/SQLite practice application.
It has no operator ownership or exclusive recording-session access control.
A browser profile cannot isolate its database. Its current deployment, boot,
availability and store have not been contacted or verified in this continuation.
No existing state can be claimed, reset or replaced on that basis.

[Render's free-service documentation](https://render.com/docs/free) confirms
that a free service can restart and loses local file changes on spin-down or
redeploy. It has no SSH access or persistent disk. A second unadvertised public
URL would still need real access control. A separate hostname alone is insufficient.

## One proposed arrangement

Use one separate Render web service with requested name
`shiftwork-s50-recording-20261027`, one FastAPI process and one newly owned SQLite
database. The actual service ID and URL are not allocated or verified. Keep
`shiftwork.onrender.com`, its configuration and its database untouched.

The recording service needs an operator-only admission wrapper. It must protect
both static files and API requests, deny mutations by default, and permit only
the frozen S50 controller's one-time sequence after approval. Authentication is
real access control, not a hidden URL. Secrets stay in private process configuration
and out of request logs, footage, source bundles and evidence exports.

This wrapper is not implemented or deployed. It adds a boundary beyond the
current approved composition. Review the scoped architecture first, then exact
program design and fail-capable tests before implementation. The existing
offline controller is useful reference code, not proof of hosted protection.

The application remains a single FastAPI/SQLite controller. No Postgres,
multi-worker server, learner permissions, evaluator changes or S49 substitute
are proposed. The coach stays excluded.

## Required controls before a recording packet can be executable

1. Freeze the reviewed wrapper and existing runtime source, deploy method,
   actual build, served assets, executor and SDK versions. Use only a separately
   approved delivery method. No Git, registry publication or deployment is
   implied by this design.
2. Create one fresh owned database without touching any existing store. Refuse
   an existing target path. Bind its initial snapshot, actual boot, board,
   mission, exact starter baseline and history. A restart invalidates the grant;
   it cannot recreate or re-arm the recording automatically.
3. Prove authenticated reads, denied unauthenticated access, denied extra writes,
   exact source/state checks and the complete live-mode sequence offline. The
   current rehearsal uses recorded mode and is insufficient for this step.
4. Bind one diagnostic, one six-slot comparison with three public repetitions,
   one eligible explicit choice, one selected operation and inheritance. Freeze
   the actual source bytes, conditions, requests and canonical task specifications.
   Do not preselect B merely because it worked historically.
5. Reserve the full per-action envelope before dispatch. The re-derived shape is
   44 inference reservations and 26 Sandbox spawn attempts. Count failures and
   close unused allowance on a stop. Keep provider/spawn retries at zero. Existing
   same-operation event polling and bounded SSE resumes are separate control-plane
   requests and must be explicitly accounted for in the final transport policy.
6. Prove hard send/time limits in the actual transport, failure closure and
   retained partial evidence. The local prototype checks its deadline immediately
   before transport but does not cancel an already running upstream operation.
   A hosted adapter still needs its own cancellation and deadline proof.
7. Name at most one startup permission check separately. A readiness request can
   wake the service and run this check. No such request is authorized now.
8. Review current rates, available credits, hosting terms and unknown Sandbox/
   control-plane charges before proposing spend. The old USD 0.10 projection and
   all historical allowances are excluded. No all-in charge ceiling is established.

## Recording and retained outputs

The eventual proposal will name one operator-labelled continuous capture before
the first live action, with no attributed learner statement or invented user input.
Assistant-authored captions remain labelled as demo material. Preserve the complete
original, frame timestamps, safe identifiers, state snapshots and all failed receipts.
Use real source-to-shot times, label compressed waits, review the entire original
and export, then measure the export strictly below 180 seconds.

The prepared native encoder successfully encoded only a synthetic 3-second test.
No actual recording mechanism, full playback review, original S50 recording or
finished export has been proved. Any browser-capture bridge must be tested before
the live packet is presented for approval.

Suggested retained root for a later approved action is a newly owned directory
under `/Users/jayd0/Documents/Codex/2026-10-27/`. Existing rehearsal and failed
directories are never reused. Its exact name, frozen identities and limits must
be in that action's approval packet.

## Decision boundary

The immediate decision is whether to pursue this isolated, access-controlled
recording-host design. It is not yet an executable live recording packet.
If adopted, complete its scoped design and offline transport/capture proof, then
obtain separately named deployment/startup authority. Once the actual protected
target and state are frozen, present one complete live-recording approval packet.

The tested local recorded path is available for a separately approved fallback
capture. It uses the older recorded mission, pinned fixture repairs and authored
text. It would provide a useful local video, not satisfy the live-hosted S50
contract. S49 remains incomplete on its unchanged five-consenting-human contract.
Public YouTube upload, rule acceptance, Devpost submission and Git publication
remain later named decisions.

## Current offline evidence

[Session-control record](slice50-session-controls-2026-10-27.md) links the
executable kit, full recorded rehearsal, fault proofs, source audit and UI views.
No new service was created or contacted to prepare this proposal.
