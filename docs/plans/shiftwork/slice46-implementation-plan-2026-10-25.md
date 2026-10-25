**Current stop: second action approved, executed once and comparison incomplete.**
No live allowance remains. See [the current handoff](slice46-continuation-2026-10-25.md).
The original plan and checkpoints below retain their earlier state.

# S46 implementation plan

Status: offline implementation verified; first live action stopped; S46 incomplete.

Goal: one labelled coach patch, one isolated public diagnostic, learner-controlled
draft acceptance, explicit save with attribution, and an ordinary S45 comparison.

Authority: user S46 go-ahead on 2026-10-25. Live calls and spending up to US$5
preapproved, covering all charges; Sandbox pricing must be verified before execution. Contract:
Gate 3 section 3.2 and obligations 64 to 67; Gate 4 S46. The approved correction
is in `slice46-gate3-correction-2026-10-25.md`. The user also approved the named model/call/action limits.

## Preservation and baseline

- [x] Native managed worktree created at
  `/Users/jayd0/.codex/worktrees/shiftwork-s46/shiftwork`.
- [x] Branch `shiftwork/slice-46`, based on published S45
  `087585ff690194e6fde5d67be9827d732474879e`. Local and remote S45 match.
  Main and remote main remain `fc0d21d32a21d23534943ebec9bb2518126e8413`.
- [x] Original checkout's untracked S47 handoff left untouched. S47 has its own
  managed worktree. No S47 file or branch changed by this agent.
- [x] All 106 protected-material and 66 older-evidence hashes in the accepted
  S45 revised-live manifest match. All four named receipt directories exist.
  Gate 3 hash matches the handoff exactly.
- [x] Python baseline: 1,732 passed, one live-only skip, one installation test
  deselected, two existing deprecation warnings, 224.55 seconds. Used the existing
  macOS interpreter, no installation, fresh bytecode root.
- [!] Node initial baseline: 10 inherited S45 mutation cases require the old
  branch and fail before their behavioral assertion. One performance test cannot
  find the interpreter in the new worktree. Set `SHIFTWORK_PYTHON` explicitly and
  repair branch-only provenance without weakening any behavioral assertion.
- [x] Authenticated model-list lookup confirms Super. Public rates verified.
  No inference call or Sandbox operation made.

Receipts: `/tmp/shiftwork-s46-20261025/`. Preserve initial failures. Never rerun
the closed S45 live runners or open their stores with normal app reconciliation.

## Implementation after Gate 3 approval

- [x] Apply approved correction and synchronize the supporting brief/status.
- [x] Write and observe failing API/storage tests for the new behavior, with
  existing helper signatures copied from current source.
- [x] Implement bounded patch parsing, frozen proposal storage and attribution.
  Verify shared assist budget and forbidden roles remain enforced.
- [x] Reuse diagnostic reservation/execution with a transient proposal identity,
  atomic once-only linkage, independent isolated-executor guards and no eligibility.
- [x] Implement atomic draft acceptance and explicit version disclosure.
  Verify no acceptance-created version, freeze, selection or ledger mutation.
- [x] Add plain JS proposal/run/accept controls and deterministic report links.
- [x] Prove the required obligation guards with its own assertion-bound mutation and fresh clean and
  restored controls. Include leak scanner positive controls on serialized data.
- [x] Run Python and Node regressions, inspect the diff and run git diff --check.
- [x] Resolve the first model/call-count and Sandbox spending boundary, freeze
  one action and execute without retry. It STOPPED before a usable coach proposal.
- [ ] Obtain approval for the separately prepared corrected action, or retain S46
  as incomplete. No failed coach call is retried under the first allowance.
- [ ] Inspect actual desktop/mobile rendering at 100% and 200%, retain receipts,
  record proof limits and run the required architecture cleanup review.
- [ ] Present the actual result for explicit S46 acceptance. Stop before operation,
  publication, main integration, deployment or another slice.

Current state and exact proof limits: [S46 checkpoint](slice46-checkpoint-2026-10-25.md).
