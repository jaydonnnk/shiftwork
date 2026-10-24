# S46 continuation background, 2026-10-25

This is the copy-paste background for a new agent working in /Users/jayd0/Desktop/shiftwork on macOS arm64. It describes the accepted S45 and the approved S46 contract. AGENTS.md and the current gate documents take precedence. This chat published S45 and prepared this handoff; it did not start S46.

1. Published starting point and authority

S45 is COMPLETE and ACCEPTED. The user explicitly answered "Select B and accept S45", then requested: "I accept. Please commit and push, and then give a copy paste handoff prompt for another agent to begin s46."

The S45 implementation, tests, approved gate amendments, authority records and public evidence were committed in 16 focused commits ending at b7babdd572978e4b1a91ca6ea74a56587211f92d and pushed to origin/shiftwork/slice-45. A subsequent documentation-only commit records publication and adds this handoff. The current final tip is obtained from Git and the remote, rather than assuming it still equals b7babdd. At publication, main and origin/main remained fc0d21d32a21d23534943ebec9bb2518126e8413. S45 was not merged to main and no deployment was performed or verified. There is no claimed CI run; this repository has no .github/workflows directory.

S46 has not started, its branch has not been created, and no coach model or live allowance is approved. Under the per-slice rule, implementation requires the user's explicit S46 go-ahead. The handoff itself does not authorize provider calls, installation, protected-fixture changes, publication, deployment or the next slice. If S46 is authorized, its branch is shiftwork/slice-46. Its base must include the accepted published S45 tip. Old main alone lacks S45. Main integration remains a separate Git decision.

2. Product and S46's place

Shiftwork is a persistent applied-AI-engineering learning environment. The learner investigates a real AI-service failure, records a cause and falsifier, tests repairs under shared requirements, explicitly selects an eligible exact version and later operates it. Experiments cannot rewrite operational history. The junior-engineer role, clients and business consequences are fictional; passing service checks is not learning-gain or job-readiness evidence.

S45 added repeated paired comparisons and exact-version choice. S46 adds a coach-generated proposal and one isolated diagnostic execution before the learner decides whether to copy that proposal into the draft. It must preserve the learner's authorship, independent assessment and explicit selection.

3. S46's approved contract

The authority is docs/plans/shiftwork/04-slices.md, "Slice 46: coach proposes one patch and runs it once in isolation", and 03-program-design.md section 3.2 and obligations 64 to 67.

After a complete investigation, Bellwether's PATCH_PROPOSAL role returns a labelled patch. run_assist_proposal executes the exact proposal bytes once as a DIAGNOSTIC experiment, against public tests and public records only, using the configured isolated executor. The report comes from deterministic checks. The run consumes a diagnostic slot. A second run of the same proposal, an incomplete investigation or an exhausted diagnostic allowance must be refused before executor work.

RecordedAdapter and LocalProcessAdapter must never execute a coach proposal. There is no trusted-local fallback, protected-case reservation, eligibility, selection or business-ledger effect from that diagnostic run.

Accepting a proposal copies it into the learner's draft only. It creates no version, freeze or selection. The next saved version increments VersionAuthorship.generated_patch_accepted_count by one. A coach-authored version becomes eligible only through the existing S45 comparison and a separate explicit choice.

The visible demo is: recorded cause and falsifier, labelled coach proposal, one isolated diagnostic result with its pass rate, learner accepts, saves and compares. S45's operator-written examples are not coach-generated S46 evidence. S46 is the first slice to cut if time runs short; do not weaken the contract to avoid a cut.

4. Open model and spending decision

Gate 4 explicitly leaves the larger Nemotron model and its current Token Factory rate unverified. shiftwork/config.py currently defaults BOTH SHIFTWORK_SERVICE_MODEL and SHIFTWORK_ASSIST_MODEL to nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B. That default is not approval of a larger coach model.

Before a live action, the actual served model and rate need verification, followed by approval of the coach model, exact call count and ceiling. An authenticated model-list lookup is itself external-service and credential use, so its authority must be clear. Public documentation research and a billed inference call are different actions. Missing prices and Sandbox cost remain unknown, never zero.

Bellwether's three assist calls are shared across HINT, DIAGNOSIS and PATCH_PROPOSAL, with at most one patch proposal. The pack declaration owns those limits. Other packs do not silently gain PATCH_PROPOSAL. The proposal run's service calls and a later comparison's calls must be counted separately from the coach call. S45's 42-call comparison bound is not an S46 allowance. All S45 live allowances are exhausted or closed, including their unsent remainders. The existing US$5 inference ceiling does not authorize another action.

The service gateway still has one call per customer request, no retry, 8 KiB input, 1,024 output tokens and a 20-second deadline; workspaces have the existing 45-second ceiling. Its optional reasoning-off permission is bound to the exact Nano model and frozen tested context. It is not arbitrary provider configuration or a larger-coach permission. AssistGateway has its own existing trusted system message and limits. Service and coach protocols must not be conflated.

5. Actual code before S46

The existing request_assist in shiftwork/orchestrator.py handles role, investigation and shared-budget guards and retains proposed_patch for PATCH_PROPOSAL. record_assist_decision currently stores an accept/reject decision only; it does not copy proposal bytes into the draft. There is no run_assist_proposal implementation in shiftwork.

The current domain AssistEvent lacks the diagnostic_run_id and proposal_source_sha256 fields already specified in Gate 3. Those missing implementation pieces are S46 work, not permission to invent a different contract.

Relevant existing modules are shiftwork/assist/gateway.py, shiftwork/orchestrator.py, shiftwork/experiments.py, shiftwork/comparison_flow.py, shiftwork/domain/models.py, shiftwork/api/routes.py, shiftwork/api/schemas.py and shiftwork/store/repo.py. Existing assistance tests are in tests/assist and tests/orchestrator. Actual helper signatures and call patterns need inspection before reuse. The approved file map and schema ownership in Gate 3 settle placement.

6. Required S46 proof

Obligation 64, test_assist_proposal_run_refused_before_investigation_twice_or_without_slot: no complete investigation, a second run and no diagnostic slot each refuse without an executor call. These are three guards, not one shared mutation proof.

Obligation 65, test_assist_proposal_never_runs_trusted_local_or_recorded: both non-isolated adapters refuse. A local fallback fault must reach a real behavioral assertion.

Obligation 66, test_assist_proposal_run_sees_no_protected_material_and_cannot_qualify: the run's inputs and every public serialized surface pass the obligation-39 leak boundary, with positive scanner controls, and its result cannot qualify a version. Protected material, provider credentials and hidden assessment never enter proposal input or code execution.

Obligation 67, test_accepted_proposal_is_draft_only_and_attributed: acceptance changes only the draft, creates no version/freeze/selection, and the next saved version has one additional accepted generated patch. Attribution and once-only behavior must survive real API/storage execution.

Existing obligations 5, 7 and 8 remain passing: complete cause/falsifier/public-test before diagnostic help, shared assist budget and one patch cap, and no assistant authority to edit/freeze/grade/select/read protected material. Each new guard needs its own fault, intended assertion failure, byte-identical restoration and a passing clean/restored control. A setup crash or old branch assertion is not proof. Model prose is never the assessment oracle.

7. What accepted S45 actually proved

The complete revised live action used exactly 42 Nano calls and 24 Sandbox operations. Both candidates retained nine public batches and passed three protected phases. A passed seven public batches and was ineligible; B passed all nine and was eligible. A's two failures added unrequested collection and omitted stock on a price-and-stock request. They were retained semantic failures, not transport failures or lost captures.

B had 12 useful completions and six justified refusals across 18 public responses. Thus nine passing batches do not mean 18 useful completions. This is a small frozen workload, not general reliability, learner work, a learning study or proof that validation alone caused B's result.

The user-selected B is sel-0002, ver-0004, in /tmp/shiftwork-s45-revised-live-20261024/live.db only. Its artifact hash is a71808a838c2df4cfa62883ea992d50bb942ab29beb0f6821162ccc9fbf41667. Source SHA-256 is 7d08d2833130cf3f6de155d3ecd925e9d1e7bff0d670d3b936b91ad4fdee628f. A remains ver-0003. IDs repeat in separate stores and cannot join their histories. The default application database is not assumed to contain this choice.

Selection added one operating_selections row and changed no pre-existing row or operational ledger. No operation followed that choice. The original comparison-terminal.db snapshot preserves the pre-selection database bytes. All 106 protected-material hashes and 66 older evidence hashes were preserved.

All 42 replies reported 18,241 input and 1,877 output tokens, projecting US$0.00154494 at repository rates. The action reserved US$0.09289728 inference. All earlier S45 reservations plus this action total US$0.16146432. These are not bills; actual billing and Sandbox cost remain unknown.

8. Verification and artifacts

Fresh pre-publication Python regression on 2026-10-25: 1,732 passed, one live-only skip, one deselected installation test and two existing deprecation warnings, 226.35 seconds. The exact command was PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=<fresh disposable path> .venv/bin/python -B -m pytest -q --deselect tests/packaging/test_clean_env_install_and_run.py::test_clean_env_install_and_run. This is not a passing installation check. No installation is authorized merely to run that excluded test. The local macOS interpreter is .venv/bin/python; Windows-only paths in historic notes do not describe this checkout.

Node regression: node --test tests/client/*.test.mjs, 310 passed, zero failed or skipped. The public packet was scanned against actual local credential values, including serialized and decoded-base64 positive controls, with zero hits. No secret value was printed or persisted by the scanner.

S45's earlier audit retains 109 source fault checks, 14 client-rate faults and nine served rendering faults. The follow-up retains 29 checks across 23 distinct edits, including repeated checks of existing gateway faults. They are separate matrices, not additive unique-fault totals. Controls use fresh bytecode-cache roots to prevent stale mutated .pyc files from pretending restored source is broken.

Actual live-result browser checks passed desktop 1280x720 and mobile 390x844 at native 100% and 200%, with all 18 retained links, exact rates, no mutation requests or JavaScript exceptions. Selected-state checks additionally verified the exact B choice and Step 6. WebGL was disabled; this is not physical-device, renderer-performance or AT proof.

Published public evidence is docs/plans/shiftwork/evidence/slice45-revised-live-2026-10-24.md, its .json comparison package, and slice45-selected-b-2026-10-24.json, plus the earlier public probe/stop packages. The evidence directory is ignored by default; the S45 publication deliberately included eight named public files. Private databases, restricted captures, credentials and raw receipts were not published.

Local receipts remain under /tmp/shiftwork-s45-audit-20261024/, /tmp/shiftwork-s45-followup-20261024/, /tmp/shiftwork-s45-revised-live-20261024/ and /tmp/shiftwork-s45-publication-20261025/. Presence must be rechecked. The selected-state read-only review was on http://127.0.0.1:8457/?board=bookshop#compare; port 8456 retains the pre-choice snapshot. Availability is not assumed in a new session.

9. Preservation and known traps

Neither /tmp/shiftwork-s45-live-20261024/ nor /tmp/shiftwork-s45-prompt-schema-live-20261024/ may be rerun. Their original transport causes remain unknown. The successful revised action did not explain those old failures. No allowance is reopened by new Git publication.

Normal app startup reconciles pending rows. Old stopped evidence must not be opened with ordinary startup; the review copies disabled reconciliation and refused mutations. S46 tests and demos need separate disposable state, not writes to an accepted evidence store. Private databases, restricted captures and frozen proposal sources remain protected. No submission media was modified.

S45's private snapshot validators pin old HEAD, branch and inventory. They intentionally stop matching after publication or new S46 work. That is not permission to weaken them or replay a live runner. The source-mutation runner also has branch and exact-anchor preconditions; any S46 adaptation needs explicit, preserved provenance and fresh bytecode isolation. Two false browser checks were retained as setup errors: a successful comparison needs Step 5, not the stopped action's Step 4; after selection both choose buttons are disabled and the guide is Step 6.

The architecture cleanup found callers for the current and historical generators and recommended no deletion. Historical examples and stopped evidence are not orphan cleanup candidates. MISTAKES.md contains the exact helper-contract, cache and state-specific-test lessons.

10. Read-first and completion boundary

AGENTS.md supplies the general execution rules and context limit. HACKATHON_REQUIREMENTS.md, docs/SHIFTWORK_PLAN.md, current docs/plans/shiftwork/00-status.md and the four gate files supply current authority. S46-specific anchors are Gate 4's S46 section, Gate 3 section 3.2, limits section 7, call stacks and obligations 5, 7, 8 and 64 to 67. The 2026-10-23 S43 to S46 backtrack and later S45 scoped amendments explain the current contract. Long documents are best read by heading and line range. The published Gate 3 program-design SHA-256 is a94a4e68108f707bed8cf27a0430b8dce0efc76a1ccacbc48ee24c618091ff4c; changes to approved decisions require the existing gate process.

The next session's initial read-only state check is branch, HEAD, status/index, local and remote S45/main refs, receipt availability and protected hashes. S46's first open decision is the coach model and rates, with explicit S46 and live authority still pending. Gate errors require the approved backtrack process; they are not silent implementation choices.

S46 completion means the actual labelled proposal/isolated-run/draft-acceptance journey, deterministic assessment, all required tests and separate mutations, actual browser evidence, attribution on the next saved version, no protected leakage, unchanged operational history, recorded proof limits, cleanup review and explicit user acceptance. It does not itself authorize operation, commit/push, deployment, protected-fixture editing or S47.

Wait for instructions before taking any action.
