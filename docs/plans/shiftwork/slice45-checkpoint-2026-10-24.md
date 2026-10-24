# S45 stopped for handoff, not accepted

The final section supersedes earlier pre-call and pending-comparison statements.

## Authority and preserved state

On 2026-10-24 the user said: "I approve s45, and the token spend ceiling shdt
exceed usd 5" and "Okay plaese proceeed with s45".
This authorizes the S45 branch and offline implementation. The inference-spend
ceiling is US$5. The separately approved five-call probe later stopped on its
first attempt, as recorded below. Further calls need fresh approval after that
stop. The final comparison still needs its exact candidates, count and ceiling
approved before sending. No commit, merge,
push, deployment, installation, protected edit or later slice is authorized.

The user's decisions, quoted from chat:

- G1: "keep the rules as they are. The 1,024-token limit stays, with no system
  prompt and no retry." They proposed "a small, separately approved test of
  about 5 calls" before requesting any provider reasoning-option gate change.
- G3: "the gates allow it, but keep it out of the demo comparison." A learner
  code-only repair must be labelled "no model call".
- G4: "allow it as a learner choice in the product, clearly labelled. Keep the
  demo pair to two repairs that still depend on the model." Excluding a fallback
  from this demonstration does not prove it is worse. The user's suggested
  9-of-9 expectation is a hypothesis, not a measurement.
- G13: "yes, for public runs only and never for the protected step"; full text
  behind a toggle labelled "model's reasoning, as returned by the provider".
  "the reasoning never reaches the evaluator, and it must pass the
  public-surface scanner with a scanner self-test." They authorize mitigations
  that preserve the core boundaries, and say not to proceed if they break them.

Interpretation against Gate 2 section 10: labelled learner-authored fallback is
an ordinary-code repair. It cannot be silently supplied in a starter or called
model-dependent if it completes omitted tasks. Starter and reviewed fixture
bytes stay unchanged. Provider text is evidence of the returned text, never an
authoritative account of internal reasoning or an assessment oracle.
S44 reports total completion tokens and no reasoning-token breakdown. The UI
must distinguish total output tokens from reasoning character count.

Git was clean on `shiftwork/slice-44` at `fc0d21d`, with local main and
origin/main at the same commit. Created `shiftwork/slice-45` from main under the
user's approval. The earlier handoff's claim that main was checked out was stale.

## Verified baseline

- `.venv/bin/python -m pytest -q`: 1,544 passed, one skipped, two failed in
  184.30 seconds. Failures: `test_conformance_suite_recorded_local[port_dead]`
  and `test_clean_env_install_and_run`. Full output is retained at
  `/tmp/shiftwork-s45-baseline-pytest.log`.
- Node: all 287 tests passed. Output at `/tmp/shiftwork-s45-baseline-node.log`.
- S43 and S44 mutation controls have zero survivors. Final isolated runs killed
  27 and 29 faults respectively; the exact evidence limits are recorded below.
- S44 package digest recomputed as
  `f2e1b32f5046b87d37ea89632f9984820124907e724eaf1e917442d8853714b7`.
  Five empty replies end with `length` and 1,024 completion tokens; five plans
  include collection and alternative. Reasoning text is retained; its token
  count is not. This confirms the bounded output-budget incident, not semantic
  omission or the effectiveness of any repair.
- Mission and starter match their reviewed SHA-256 pins
  `9defd8e35e2afc59b993095c706935a130f4dd70a3051ec484f5d38161fdd9d4`
  and `7736c38410ce24b52ba610b4062b228856aaad228c8a59a1eb0040e06185bdc1`.
- `_read_comparison_workloads` accepts the sealed public manifest with mission
  v2. Each of its three public batches contains two requests. Public task ids
  are within v2's vocabulary. The no-network v2 wiring test verifies both
  candidates receive the v2 task/tool policy in all public and protected phases.
  Its authored replies do not establish model effectiveness.

## Cost and live boundary

At three public repetitions, the pinned workload needs
`2 candidates * 3 pairs * (2 public requests * 3 repetitions + 1 protected)`
= 42 maximum model calls and `2 * 3 * (3 + 1)` = 24 Sandbox operations.
The handoff's planning estimate of 110 calls does not match these frozen bytes.
At repository projection rates, reserving 32,768 input and 1,024 output tokens
per call projects US$0.09289728 for 42 calls, or US$0.0110592 for five probe
calls. Actual provider billing and Sandbox operation cost are unknown.
The user approved the exact proposal in chat: "Approve the 5-call probe".
The allowance is five direct Nano gateway calls, zero Sandbox operations,
one frozen `/no_think, return only JSON` wording, no retry, and a reserved
projection ceiling of US$0.0110592 within US$5. It is not eligibility evidence.
The prompt and five scheduled identities are retained before the first send.
The final 42-call comparison remains unauthorized pending candidate approval.

### Probe stop, 2026-10-24

The no-network dry run exercised all five sends with frozen provider parameters,
then proved the sixth is refused. The live probe stopped at attempt one with
`GatewayRejected`, public code `PROVIDER_TRANSPORT_FAILED`. No model response
or usage was retained. Four scheduled calls remain NOT_SENT. Zero Sandbox
operations ran. The inference reservation counts the attempted call and is not
refunded. Reserved projection consumed: US$0.00221184. Actual billing is unknown.
There was no retry and no wording change. This does not test reasoning-off text.

The receipt's UTC wall timestamps are 2026-10-23 20:33:03.096057 and
20:48:23.582002, both 2026-10-24 in Singapore. They span 920.486 seconds.
No monotonic duration or underlying transport exception type was retained,
so the delay's cause and whether it represents request duration are unknown.
The record does not prove the 20-second deadline held. No provider/network
diagnostic call was made after the stop. The S44 launcher uses the same default
gateway transport; neither the current environment nor .env.local names a
proxy or certificate override. That read-only check does not establish a cause.

Files under `/tmp/shiftwork-s45-probe-20261024/`:
- `run_probe.py`, SHA-256
  `fc2ef8d4e94ce3aa6ca4b450288be10536f3c491746c06f95160bcdc37e340d9`.
- `live-receipt.json`, SHA-256
  `dcef26da5029f13f5cf8b40143d24366a64f6ab2a7bc6990125399a41e58e8ae`.
- `dry-run-receipt.json`, `dry-run.log` and `live.log`.

The original live receipt is preserved and the driver refuses an existing
receipt path. Any new attempt requires fresh user approval after this recorded
stop, with its own count and reserved ceiling. S45 acceptance and selection
remain pending.

## Implementation plan

Existing test text changed, retained before editing:
- `tests/client/workplace_fullscreen.mjs` receipt-root expression was
  `/^\/(?:private\/)?tmp\/shiftwork-s(?:3[6789]|40|41|42|44)-[^/]+(?:\/|$)/`.
  S45 adds only `45` to this owned temporary-root allowlist.
- `tests/domain/test_comparison.py`'s minimal context fixture began
  `context = NS(workloads=workloads, content_hash="frozen-context",`.
  It now explicitly supplies the real ExecutionContext's already-required
  `resource_limits_json={}`. No assertion or accepted input is weakened.
- The S44 mutation runner's check was
  `assert subprocess.check_output(["git", "branch", "--show-current"], text=True).strip() == "shiftwork/slice-44"`.
  Only the branch literal was adapted to S45 in memory; its file is unchanged.

Build on the existing six-slot comparison and frozen resource limits. Preserve
the protected request ordinal, one protected phase per candidate/pair, restricted
captures and the sealed material. Every public repetition must have its own
retained run identity and a fresh workspace. No new dependency or schema migration
is planned; existing run-to-slot bindings can retain repetitions.

1. [x] Finish baseline mutation controls and protected/v2 compatibility proof.
2. [x] Add failing API/service tests for frozen comparison counts, every public
   repetition retained, unequal/missing counts INCOMPLETE, a failed mandatory
   repetition blocking only its candidate, and retained-row rate changes.
3. [x] Implement repeated public execution, pure eligibility/metrics reading,
   bounded metering and public projections. Keep protected counts separate.
   Relevant files: `comparison_flow.py`, `domain/comparison.py`, `store/repo.py`,
   `api/schemas.py`, `api/routes.py`, `live_budget.py` and `hosted.py`.
4. [x] Add public-only provider-reasoning projection after privacy scanning,
   with needle injection self-tests and no evaluator dependency. Reuse the
   existing observation/evidence UI and render text safely.
5. [x] Extend the choose screen with retained-only pass rates, cause split,
   exact repetition links and small-sample limits. Check 1280x720, 390x844 and
   native 200% zoom. Refresh changed client source digests.
6. [x] Kill each new guard independently at its named assertion, restore its
   source byte-identically and pass its clean control. Re-run obligations
   50 to 54 with repetitions, the full Python and Node suites, diff and fixture
   preservation checks. Inspect existing test text before editing and retain it
   here if the S45 browser receipt allowlist changes.
7. [x] The first probe attempt stopped with no reply. The user separately
   approved the four remaining identities, and all four replies were retained.
   This wording did not suppress reasoning. Results and the next unapproved
   decision are recorded below. No further inference is authorized.
8. [ ] Run the approved comparison once, retain every result or a truthful stop,
   and obtain the user's explicit eligible selection or record none eligible.
9. [ ] Record live evidence and limits, complete post-slice cleanup,
   then ask "Is S45 accepted, or what should change?"

New tests live in `tests/orchestrator/test_comparison_repetitions.py`, focused
domain/client tests and `tests/s45_mutation_proofs.py`. Proofs must assert named
behavior; crashes, timeouts and mere test collection are not mutation kills.

## Offline result and verification, 2026-10-24

S45 is implemented offline, with the live comparison, selection and acceptance
still pending. The six frozen slots now each retain up to three public runs,
followed by their unchanged single protected phase. Each public result commits
before assessment and before the next phase. An error cannot erase an earlier
capture. Live driver errors stop later phases without retries. Every run's
context, version, experiment, adapter, evidence mode and purpose are checked
before execution. An unequal or missing repetition count makes the outcome
INCOMPLETE; any mandatory failure blocks that candidate. Public rates come from
current retained captures and task assessments, while protected failures remain
separate and still block eligibility. No experiment writes operational history.

Public reasoning is projected only after checking the public ordinal, extracting
the provider's reasoning field and running the existing private-needle scanner.
Unsafe text is withheld. Malformed or absent evidence stays unknown. Scanner
positive controls cover raw, JSON-escaped and slash-normalized needles. Provider
text never enters comparison assessment, and changing it leaves the outcome
unchanged. The UI renders it with textContent under a collapsed disclosure.
It reports total output tokens and reasoning characters, not an invented count
of reasoning tokens. The repair declaration asks learners to label fallbacks
and code-only behavior. Zero-call evidence is scoped to public repetitions.

Final evidence:

- Python: 1,643 passed, one skipped, one deselected, one failed in 219.94 seconds.
  The failure is the existing
  `test_conformance_suite_recorded_local[port_dead]`. Command: a fresh
  PYTHONPYCACHEPREFIX, PYTHONDONTWRITEBYTECODE=1 and `.venv/bin/python -B -m
  pytest -q --deselect
  tests/packaging/test_clean_env_install_and_run.py::test_clean_env_install_and_run`.
  Receipt: `/tmp/shiftwork-s45-final-source-pytest-2.log`.
- The clean-install test is excluded, not passing. Its baseline failed. The
  initial requested baseline invoked its dependency installation before I
  inspected setup, contrary to the no-install boundary. This is retained in
  MISTAKES.md; no later install run was performed.
- Node: 299 passed, zero failed or skipped.
  `/tmp/shiftwork-s45-final-node-verified.log`.
- Asset closure after the final CSS edit: nine passed.
  `/tmp/shiftwork-s45-final-asset-closure.log`.
- Obligations 50 to 54: ten passing cases across one and three public
  repetitions, also passing in the final regression.
  `/tmp/shiftwork-s45-obligations-50-54.log`.
- S45 source proofs: 80 unique faults, all killed at their named assertions,
  byte-identical restoration and a passing clean control for each. The first
  79 are in `/tmp/shiftwork-s45-mutations-isolated.log`. The final primary-slot
  lookup fix adds one fault and reruns the affected child-slot fault:
  `/tmp/shiftwork-s45-slot-boundary-proofs.log`. These are not 81 unique faults.
- Client rate proofs: 14 named faults, zero survivors and passing restored
  controls. `/tmp/shiftwork-s45-client-mutations.log`.
- Browser: 1280x720 and 390x844, plus native 200% zoom; desktop CSS viewport
  verified as 640x360 at 200%. Every one of the 18 public repetition links
  opens its exact run, including inspection from the choice dialog without a
  selection request. Nine served faults each fail at their named assertion,
  then pass clean; source bytes stay unchanged.
  `/tmp/shiftwork-s45-browser-final-proof.log` and
  `/tmp/shiftwork-s45-browser-final-faults/`.
  The small-sample warning's low contrast was reproduced before fixing its
  colors: `/tmp/shiftwork-s45-contrast-red.log`. Independent warning and
  evidence-label contrast faults both fail the browser check.
- S43: 27 faults, zero survivors; S44: 29 faults, zero survivors.
  `/tmp/shiftwork-s45-final-s43.log` and
  `/tmp/shiftwork-s45-final-s44.log`. The inherited S43 runner's proof shape
  differs from the stricter S45 assertion-and-control runner.
- A stale timestamp-based bytecode cache retained an inherited S43 mutation
  despite restored source. The poisoned cache and source/cache digests are
  retained at `/tmp/shiftwork-s45-cache-evidence/`. The identified caches were
  regenerated from checked source; final tests and mutation controls use
  isolated caches with writes disabled. A positive-control regression proves
  the S45 runner imports restored source despite a same-size poisoned cache.

The fixture-only preview is
`http://127.0.0.1:8452/?board=bookshop#compare`, from
`tests/client/s45_preview.py` and disposable
`/tmp/shiftwork-s45-preview-20261024/render-verified.db`. It labels its authored
outputs and reasoning as rendering fixtures. Its 8-of-9 and 9-of-9 values are
not live results, learner work or a choice. Tests intentionally disable WebGL
to exercise the usable workbench; they do not prove the 3D renderer, a physical
mobile device or audible assistive technology. Screenshots were inspected at
all three requested sizes. Older owned S45 previews on 8450 and 8451 were stopped.

### Existing test edits and architecture cleanup

Additional retained old test text:

- `tests/api/test_hosted.py` expected
  `('live_comparison_budget', LiveComparisonBudget, 12, 18)`; the approved
  factory maximum is now 24 operations and 42 calls. Exhaustion and fresh-meter
  assertions remain, and a separate test keeps the one-repetition action at 12/18.
- `tests/client/workplace_fullscreen.mjs` used
  `querySelectorAll('button,textarea')` twice in dialogJourney. It now includes
  visible links and summary controls, matching the extended choice dialog.
- `tests/orchestrator/test_experiment_lifecycle.py`'s pre-edit copy is
  `/tmp/shiftwork-s45-experiment-lifecycle-before.py`, SHA-256
  `6c9a4aad728d7c93517dd3140dd811381c9118b74abc64cb0d27e6b9e01934d0`.
  Obligations 50 to 54 now run at both repetition counts. Its observation probe
  filters its own two probe records and independently requires one public-status
  record. Its usage-boundary injection appends after existing observation
  ordinals and asserts the prior count plus four, preserving its route checks.

The architect-reviewer skill was applied in cleanup mode to the offline work.
Repository inventory is retained at `/tmp/shiftwork-s45-cleanup-inventory.txt`.
The public projection has production callers in comparison_flow and experiments;
the run-to-slot lookup is used by execution and public-output boundaries. New
tests are collected by pytest or Node. The proof, preview, browser and candidate
scripts are deliberate CLI entry points referenced here, not abandoned scaffolds.
An AST scan of all 14 new Python sources found no unused imports. No fixture,
dependency, evaluator, migration or framework was added. No existing file was
recommended for deletion. The count correction in 04-slices.md changes only
wording, preserving every frozen workload and schedule rule. Final cleanup
after the live demonstration and acceptance remains pending.

### Proposed examples and remaining live authority

`demos/s45_repairs.py` generates two operator-authored proposals. Their ASTs
differ from the pinned starter only in user-prompt text and an authorship comment.
Both depend on the model and add no fallback. A preserves the original descriptive
prompt with the frozen probe prefix; B uses a compact task-to-tool table with the
same prefix. Neither has measured effectiveness, and neither is learner work.
They have not been tuned against provider results. Generated source and metadata
are in `/tmp/shiftwork-s45-candidates-20261024/`:

- A service SHA-256:
  `8492b3cd6aa5681df477d692be2bfb09c08398fb534673e3bd0b56d4edd9fe7b`;
  artifact hash `dd977957968efd5675a32f73af49f0cc205960e8a26123ed96c1de4fd1be1bf4`.
- B service SHA-256:
  `ad6e47fffc27a6d71b7a2c543675a9a2feee0853ffcca44c847579d840ab9b19`;
  artifact hash `7e3269ba21e5a4932c3c6b1fb2d5a06fe81fdd0b91761129e18fb8dd7de60ddb`.

The four unsent probe identities have a proposed driver, not live execution:
`/tmp/shiftwork-s45-probe-20261024/resume_probe.py`, SHA-256
`bbb69e13031a7da8b7af4268a96fcfb3755b010d253973eb44123150bc60f248`, and
`resume_probe_child.py`, SHA-256
`1a2bad871ebe84d328a8759dd6d35008fa8ba55ded8806c138c96fd01162bb79`.
The no-network dry run retained four explicitly authored replies; the outer-stop
self-test terminates a stalled local child. Each live child would allow one
call and a 20-second outer stop; the parent stops at the first error. Original
receipt and wording digests are checked before sending. Four calls reserve at
most US$0.00884736 and zero Sandbox operations. Transport delivery and billing
remain unknown on a timeout. The user subsequently approved this exact
four-attempt continuation on 2026-10-24: "Approve the 4 remaining attempts".
This approval was recorded in 00-status.md before sending. The original driver,
child and stopped-receipt digests were rechecked, and all four live continuation
receipt paths were absent. The original prompt and provider settings remain
frozen. No additional call or main comparison is authorized by this approval.

The main comparison still needs the user's named approval of A/B, exactly 42
maximum calls, 24 Sandbox operations and the US$0.09289728 reserved projection.
It must run once without tuning or reruns, with every returned repetition retained.
Then the user must explicitly select an eligible exact version, or the record
must state that none is eligible. No S45 acceptance, commit or publication is
implied by the offline evidence.

Final preservation audit: `/tmp/shiftwork-s45-final-audit.json`. Branch remains
`shiftwork/slice-45`, HEAD `fc0d21d32a21d23534943ebec9bb2518126e8413`, with
an empty index, 21 modified files and 17 new files. All 106 checked fixture and
sealed-source digests, every client manifest digest and the original stopped
probe receipt match. `git diff --check` passes. Added text contains neither an
em dash nor the section sign, and the credential-shaped literal scan found none.
Only the fixture preview on port 8452 remains among owned S45 controllers; no
probe process is running. Final corrected modal screenshots were inspected at
`/tmp/shiftwork-s45-final-visual-1/choose.png` and
`/tmp/shiftwork-s45-final-visual-2/choose.png`.

## Approved probe continuation result, 2026-10-24

The user approved the exact proposal: "Approve the 4 remaining attempts".
The approval, count, US$0.00884736 reserved ceiling and zero Sandbox operations
were recorded in 00-status.md before sending. The reviewed driver and original
receipt hashes matched. It executed identities 2 through 5 once each and stopped
normally with all four replies retained. No outer deadline fired and no retry,
wording change, model change or extra inference occurred.

The requested and provider-returned model is
`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` in every reply. Temperature is 0,
max_tokens is 1,024, and every call uses the same frozen single user message.
Each reply reports 280 input tokens:

- Identity 2: length, 1,024 output tokens, zero answer characters,
  4,891 reasoning characters, SCHEMA_INVALID.
- Identity 3: stop, 841 output tokens, 151 answer characters,
  3,732 reasoning characters, valid plan naming collection and alternative.
- Identity 4: stop, 788 output tokens, 144 answer characters,
  3,537 reasoning characters, valid plan naming collection and alternative.
- Identity 5: length, 1,024 output tokens, zero answer characters,
  4,852 reasoning characters, SCHEMA_INVALID.

The four provider calls took 11,082, 8,719, 7,868 and 10,547 monotonic
milliseconds respectively, inside the prepared parent's 20-second stops.
These are direct gateway probes, not sandbox service executions. No task
evaluator ran, so two valid plans are not two demonstrated completed services.
The model still returned reasoning in all four replies. This frozen wording did
not switch it off. Four replies from one model on one public request cannot
establish a general reliability rate, prove an improvement over S44, or rule out
other wording repairs. The original transport-failed identity has no reply and
stays unknown.

Reported usage is 1,120 input and 3,677 output tokens across the four replies.
At repository rates of US$0.06 and US$0.24 per million, the usage projection is
US$0.00094968. Actual billing is unknown, including the original failed attempt.
The continuation reserves US$0.00884736; together with the earlier US$0.00221184
reservation, all five scheduled attempts reserve US$0.01105920 within US$5.
Zero Sandbox operations ran. Reasoning-token counts remain null/unknown.

The retained gitignored package is
`evidence/slice45-wording-probe-2026-10-24.json`, SHA-256
`738cd5d55d09a98c87c750ae2cf3863a54d92615c885486b1249e4c23b416070`.
It carries base64 copies of the six exact source receipts with independently
verified SHA-256 digests. It is a DIRECT_PUBLIC_WORDING_PROBE_EVIDENCE package,
not a diagnostic recording, service run, learner work or eligibility evidence.
Inspect it with a script rather than printing provider reasoning.
The parent continuation receipt is `/tmp/shiftwork-s45-probe-20261024/resume-live.json`,
SHA-256 `f46a1dc683e0990710200efd4b3c70086cddd1bb0cdec2480e5149bae449b084`.
The original stopped receipt is unchanged. No live probe process remains and
the approved five identities are exhausted. Further calls need a new allowance.

### Scoped Gate 2/3 change, approved and implemented 2026-10-24

The user had requested a narrow option if the wording probe failed to suppress
reasoning. The user then said "Approve Gate 2/3 change and one-call check" to
the exact proposal below. Gate 2 section 7 and Gate 3 sections 3.5 and 7 now
record that amendment. This approval covers implementation and one bounded
compatibility call after offline proof, not the 42-call comparison:

1. Permit one optional learner service-gateway setting, `enable_thinking: false`.
   Omission preserves the provider default. Reject true, non-boolean values,
   additional template keys and arbitrary provider dictionaries. Admit the
   setting only for the explicitly allowed Nano model.
2. The trusted controller translates that one value to the provider request's
   top-level `chat_template_kwargs: {"enable_thinking": false}`. The learner
   still supplies only one user message. Temperature 0, the 1,024-token cap,
   8 KiB input cap, 20-second deadline and one-call/no-retry rule remain enforced.
3. Freeze permission for this setting in the comparison context, with old
   contexts retaining their original permission. Keep the exact learner source
   that requests it in the tested artifact snapshot. Record the requested setting
   in controller-owned observations. Both candidates receive the same permission;
   their declared repair may choose the setting. The protected phase executes
   the same exact candidate code under the same gateway permission. Selection
   and later operation must preserve that tested permission and version.
4. Prove refusal of each other setting, frozen/replayed permission identity,
   public/protected wiring, exact-version inheritance, unchanged call/token
   bounds and absence of provider reasoning from assessment before live use.
   Give every new guard a named mutation failure and restored clean control.
5. After offline proof, permit exactly one additional public compatibility call
   using the already frozen probe prompt and only this added provider flag.
   It reserves at most US$0.00221184, zero Sandbox operations, under US$5, with
   no retry and an outer 20-second stop. Retain an ignored parameter, a rejected
   request or a missing answer as a result, then stop. This is not approval for
   the 42-call comparison, a new demo pair or repeated tuning.

Evidence for the candidate flag: NVIDIA's own
[Nano model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16)
documents enable_thinking=False and shows the top-level chat_template_kwargs
request shape for vLLM. This supports proposing that flag; it does not establish
the behavior of Nebius's hosted endpoint. The
[Nebius chat-completion reference](https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion)
does not name enable_thinking or chat_template_kwargs in the inspected text.
Hosted support and actual suppression therefore remain unknown until an
explicitly authorized verification call. No fallback field or retry is proposed.

Before approval, the alternative was to retain G1 and request the original A/B
comparison, accepting that neither might qualify. The user chose the narrow
amendment above. No successful demonstration is implied by that decision.

## Reasoning amendment offline proof and pre-call freeze, 2026-10-24

The approved option is implemented in the gateway protocol and mediation,
TokenFactoryAdapter, diagnostic/comparison context freezing and selected-operation
inheritance. Missing permission denies the option. Only strict false is accepted
from learner code; the exact Nano model and a true frozen permission are required
before reserving a call. Omission preserves the original provider body and request
observation. First and subsequent gateways receive the same permission. The
new wiring assertion covers all public repetitions and protected phases.

The selected context is checked against its frozen material and the selected
experiment's original canonical hash, including the retained slot schedule.
The review found that a context self-hash alone allowed an untested upgrade;
the real operation reservation reproduced that at DID NOT RAISE before repair.
Positive fixtures now freeze their authored permission before comparison and
selection. Context-only drift and a rehashed permission upgrade have separate
named refusal proofs. A source-less selection explicitly denies permission.
The reviewer then found no remaining concrete gap in this bounded repair; that
review used authored doubles and is not independent correctness evidence.

Evidence before the compatibility call:

- Corrected pre-change behavior: nine named failures and 18 passes at
  `/tmp/shiftwork-s45-reasoning-red3.log`. Earlier setup errors are retained in
  MISTAKES.md and are not behavioral proofs.
- The rehashed-upgrade regression: one named failure and 13 passes before repair,
  `/tmp/shiftwork-s45-reasoning-integrity-red.log`.
- Focused gateway, adapter and selection checks: 124 passed in the first green
  run; the expanded integrity/comparison group then passed 119 checks.
  `/tmp/shiftwork-s45-reasoning-green.log` and
  `/tmp/shiftwork-s45-reasoning-integrity-green.log`.
- The final reasoning mutation group kills 32 faults: 25 new controls and seven
  existing reasoning-publication controls. Every fault fails its named assertion,
  restores bytes exactly and passes a restored control.
  `/tmp/shiftwork-s45-reasoning-mutations-final.log`.
  The later explicit source-less denial is independently reproved at
  `/tmp/shiftwork-s45-reasoning-starter-mutation-final.log`.
- Example controls kill three new faults and reprove the two existing example
  guards, with byte restoration and clean controls.
  `/tmp/shiftwork-s45-example-control-mutations.log` and
  `/tmp/shiftwork-s45-example-a-default-mutation.log`.
  Together with the original 80, S45 now has 108 unique source faults. Repeated
  controls are not additional unique faults.
- S43 and S44 again have zero survivors, 27 and 29 faults respectively, with
  isolated bytecode and S44's branch-only adaptation kept in memory.
  `/tmp/shiftwork-s45-amendment-legacy-proofs.log`.
- The install-free full regression is running before the one-call check. Its
  result will be recorded below; no full-suite success is claimed at this point.

The existing v2 wiring test previously collected
`(request.artifact_snapshot.manifest_hash, request.single_request_ordinal,
adapter.task_vocabulary, adapter.allowed_tool_names)`. It now retains the fifth
value, adapter.allow_reasoning_off, and independently requires true in every
comparison phase. Prior assertions and the 25-phase count remain.

The original compact-table B proposal remains untouched in
`/tmp/shiftwork-s45-candidates-20261024/`. A revised, unapproved demo pair is frozen
before the compatibility result at
`/tmp/shiftwork-s45-reasoning-candidates-20261024/`. A is unchanged. B keeps exactly
the same prompt as A and adds only enable_thinking=false to its infer request.
AST comparison allows only the prompt and that strict false field; other code
changes or rescue logic fail the guard. Both are operator-authored, model-dependent
proposals, not learner work. No proposed candidate was tuned after a successful
provider result:

- A source SHA-256 remains
  `8492b3cd6aa5681df477d692be2bfb09c08398fb534673e3bd0b56d4edd9fe7b`,
  artifact hash `dd977957968efd5675a32f73af49f0cc205960e8a26123ed96c1de4fd1be1bf4`.
- Revised B source SHA-256:
  `0fb026d05fdf0e5ae484429be10bfa29a4f4119ea9ff0611a846dc7665dad940`,
  artifact hash `0d3a7888b5a29c9aa7a6c8f036bd9f8e430cc64b2c9e012f251aca811b2c4654`.

The one-call driver is frozen under
`/tmp/shiftwork-s45-reasoning-off-check-20261024/`:
`run_check.py`, SHA-256
`c371ffd5c6a2289cfa61996b173b864cb26a0d8a5bada56f0a2b8fc6d0210d4b`,
and `compatibility_child.py`, SHA-256
`364527c6e3ba90c7d70f491cac36e879c967f3dbf515f776b232735380b9212e`.
Its dry run checks the exact provider body with only the added false flag and
proves that a second call is refused. A local stalled-child control exercises
the outer stop. A repeated dry invocation is refused before any child starts,
with both prior dry receipts unchanged. These authored controls are not model
output. The approved live call is still unused at this pre-call checkpoint.

The first amendment regression retained 1,673 passes, one skip, one deselection
and three failures: the known port_dead failure plus two old mission-wiring
doubles missing required resource_limits_json. Receipt:
`/tmp/shiftwork-s45-amendment-final-pytest.log`. Their original fixture was
`type("Context", (), {"service_model": "pinned-model"})()`; it now supplies
`"resource_limits_json": {}` as the real context requires, preserving all
vocabulary and tool assertions. A new full regression follows before the live call.

The inherited S43 runner's earlier adapter_drops_vocabulary result in that
amendment run is invalid as a vocabulary-guard proof: its target was failing
because of the same incomplete double. Its reported zero survivors alone does
not establish that guard. It will be reproved at its actual named assertion
with a passing clean control after the corrected full regression.

Final amendment regression: 1,675 passed, one skipped, one deselected, only the
known port_dead failure, 225.57 seconds. Receipt:
`/tmp/shiftwork-s45-amendment-final-pytest-2.log`. The affected inherited fault
was then reproved at `assert adapter.task_vocabulary == vocabulary`, with
byte-identical restoration and clean controls before and after the fault:
`/tmp/shiftwork-s45-amendment-vocabulary-strict-proof.log` and
`/tmp/shiftwork-s45-amendment-vocabulary-fault.log`. The earlier setup-error
result is not counted as its guard proof.

The authorized one-call compatibility check is now attempted once. Its parent
and child hashes, frozen prompt, pre-call A/B sources, absent live receipt paths
and US$0.00221184/zero-operation ceiling were rechecked before sending.

## One-call compatibility result, 2026-10-24

The approved call completed once. The Nano provider returned the requested model,
280 input tokens, 73 output tokens, finish_reason=stop, zero returned reasoning
characters and 270 answer characters. Gateway monotonic time was 1,591 ms;
the parent's outer duration was 2,361 ms. There was no retry, deadline stop or
Sandbox operation. The gateway's controller-owned request observation retains
enable_thinking=false. The returned plan is valid against the gateway's mission
vocabulary and names collection, price, stock and alternative.

The public request's contract requires collection and alternative, permits price
as optional and contains no stock task. This distinction was checked before
assessment. Offline replay fed the exact retained provider content through the
existing local harness's provider double, pinned starter and trusted request
driver. The service returned collection, price, stock and alternative. The
deterministic contract validator rejected it with
`response returns a result for unknown task 'stock'`; useful completion was false.
The harness's generic authored-test-reply label is explicitly disclaimed in the
replay wrapper. This was retained model content replayed offline, with no fresh
model execution, learner work, Sandbox call, ledger write or eligibility.

This one reply supports compatibility with the flag and reports no reasoning
text. It does not prove reasoning suppression across future requests, establish
a general pass rate or show that the repair is correct. The old S44 finding
remains truncation, with no observed semantic omission in its ten replies. This
new reply instead demonstrates a possible extra-task failure. B is not retuned
after this observation, and neither candidate is claimed eligible.

Reported-usage projection for this reply is US$0.00003432 at repository rates.
Its reserved projection is US$0.00221184. All six S45 attempted identities reserve
US$0.01327104. The five retained replies report 1,400 input and 3,750 output
tokens, projecting US$0.00098400; the original transport failure's usage is
unknown. Actual billing remains unknown for every projection. Zero Sandbox
operations have run in S45. All separately authorized probe allowances are spent.

Retained package: `evidence/slice45-reasoning-off-check-2026-10-24.json`, SHA-256
`f775a946f16c2219934e3fea6b5ea0c711f31386071b4a70e6aac782a8857f88`.
It includes exact base64 source receipts and independent digest checks:

- `/tmp/shiftwork-s45-reasoning-off-check-20261024/live.json`, SHA-256
  `7f53c811e5bbf0c52e8dd94ba765478394b3aa873868ae8b3cd5805d6d93d8d9`.
- `live-child.json`, SHA-256
  `7ed5da72c8fd4c7986859a67399142d6a836ced8b929e7789c95022306e77927`.
- `offline-plan-replay.json`, labelled RECORDED_PROVIDER_PLAN_OFFLINE_REPLAY.

The revised A/B files and hashes above were frozen before this compatibility
result and remain unchanged. The original compact-table proposal is retained
separately. The next required user decision is the exact demo pair and live
comparison allowance: at most 42 Nano calls, 24 Sandbox operations and
US$0.09289728 reserved inference projection within US$5. Sandbox operation cost
remains unknown. This comparison may leave neither candidate eligible, especially
given B's retained replay failure. No rerun, extra probe, implicit selection,
commit, merge or push is authorized. The explicit selection or none-eligible
record and S45 acceptance remain pending.

The amendment cleanup found no unused imports in the changed gateway, executor
or demo modules. The shared experiment-hash helper has both outcome and selection
readers; it introduces no new persistence or evaluator dependency. There is no
fixture, migration, framework or dependency change. No deletion was proposed.
The original public/protected material and client source digests are unchanged.

Final amendment audit: `/tmp/shiftwork-s45-reasoning-final-audit.json`. HEAD is
still fc0d21d on shiftwork/slice-45, with 28 modified files, 19 new files and an
empty index. All 106 material digests, every client manifest digest, the S44
recording digest, both S45 evidence packages and the pre-call candidate source
hashes match. Added text passes the forbidden-punctuation and credential-shaped
literal scans; git diff --check passes. No probe process remains. An explicit
approval request for the unchanged A/B pair, 42 calls, 24 operations and the
US$0.09289728 reserved inference ceiling is pending. No comparison has been
reserved or executed, and no eligible choice or S45 acceptance is claimed.

## Live comparison approval and preparation, 2026-10-24

The user said "Approve A/B: 42 calls, 24 operations, US$0.09289728" in reply
to the exact frozen pair and the explicit warning that neither may qualify.
The allowance is one comparison, retaining every returned repetition, stopping
on a driver fault, with no retry, tuning, extra probe or automatic selection.
Sandbox operation cost is unknown. The US$5 inference ceiling remains.
Approval was recorded in 00-status.md before any comparison reservation or call.

The zero-call preparation is retained at `/tmp/shiftwork-s45-live-20261024/`.
It opens a v2-bound shift and replays the original S44 package only as
RECORDED_INSPECTION. The operator-performed investigation explicitly says so in
every field. Its fixed authored_by value names the learner role in the existing
schema, not actual learner authorship; the controller notice and receipts must
continue to disclose operator performance and no learning evidence.
Both repair versions are seeded as template-authored examples from their first
stored rows. A is ver-0003 and B is ver-0004, with the exact approved artifact
hashes. No case, mission, starter or candidate byte changed.

`prepared.json`, SHA-256
`de145b2e454143d7b4632848f0ad3c0a1feaea7a7af5f652f16c2829a06ea686`,
records the source mode, version hashes and ledger hash before comparison.
The actual shift has zero qualifying comparisons, zero learner choices and no
live marker at this pre-call check. An invented-ID lookup in the first draft
was removed as an empty check and is not proof.

The one-run driver is `run_comparison.py`, SHA-256
`2d46a82364eb14740827d74ad422c37932dec27be998267f60b194a23801d33b`.
Its authored meter control reserves 24 operations and 42 calls, then refuses
both next attempts without a provider or Sandbox call. Execution creates a
refuse-existing marker before reservation, uses a fresh bounded comparison
meter and records each reservation atomically in live-receipt.json. It runs in
the foreground, with no background Bash job. The controller database retains
public and restricted evidence; only its scanned public comparison view is
exported. No source model call, selected operation or automatic choice is included.


## Live stop and user-requested handoff, 2026-10-24

The user said: "Um ure definitely hallucinating, prepare a copy paste handoff
for the next agent to continue s45thanjs". Feature work and live calls stopped.
The next agent must audit this session's claims rather than adopt them.

### Actual comparison and evidence boundary

The approved one-shot driver ran once. Experiment
`experiment-bookshop-shift-01-c1` is FAILED and its outcome is INCOMPLETE.
The first A operation stopped with REQUEST_TIMEOUT after 45,831 milliseconds,
under its frozen 45-second executor deadline. The gateway deadline remains
20 seconds. No underlying timeout stage or cause was established.

Two calls were reserved and two provider replies retained: 280 input / 1,016
output tokens, finish_reason=stop, and 280 input / 619 output tokens,
finish_reason=stop. Both contain reasoning and valid task plans. There are
zero verified customer-response captures. Neither reply proves a completed
service request. No protected request, B run or later public repetition ran.
The first run is failed; pending siblings were terminalized without evidence.
Reserved or queued rows are not executed repetitions. Neither version is
eligible, learner_choice_count is zero and the ledger hash is unchanged.

The comparison spent one Sandbox operation and two inference reservations,
US$0.00442368 reserved projection. Its reported-usage projection is US$0.000426.
All S45 attempts together reserve eight calls, US$0.01769472. Seven provider
replies are retained and the original failed probe has unknown usage. Known
reported usage is 1,960 input and 5,385 output tokens, projecting US$0.00141000.
These are repository-rate projections, not actual billing. Sandbox cost is
unknown. The unused numeric capacity does not authorize resumption after G8's
stop. Fresh named approval is required before any further live attempt.

Private original receipt:
`/tmp/shiftwork-s45-live-20261024/live-receipt.json`, SHA-256
`eb8c6ce96debd3123c11cc9803cda8955c8031f21616bc49d4730b615bab2e78`.
Private original database:
`/tmp/shiftwork-s45-live-20261024/live.db`, SHA-256
`e5f0203be863efd00a03d6f76f0f7c32ee0d7de77df496d60b5a097ca8a5d167`.
The source database includes restricted material and must stay private.
Scanned public stop package:
`docs/plans/shiftwork/evidence/slice45-live-stop-2026-10-24.json`, SHA-256
`75bb4a4c22bbc503e61cdf4fd063d098e23e2ea2ea9a0a943cb4d27b2be2f406`.
It retains public observations and receipt copies. Inspect packages by script,
not full dumps. The original comparison export remains unchanged.

### Browser truth and remaining gaps

Port 8452 was an operator-authored rendering fixture showing A 8/9 and B 9/9.
Those values are not model output, learner work or live comparison evidence.
That server is stopped. Actual stop review:
`http://127.0.0.1:8453/?board=bookshop#compare`, a read-only recorded controller
on a separate review.db copy with mutation requests refused and no live budget.
The original database hash remained unchanged after review startup.

Actual-stop browser controls passed at 1280x720, 390x844 and native 200% before
the latest planned-count copy edit. Logs are browser-review-1.log,
browser-review-2.log and browser-review-proofs.log under the live directory.
Two served faults failed their named assertions and restored controls passed.
The final copy now explicitly says six requests are planned for three
repetitions; retained counts show completion. That edit has source and mutation
proof at planned-copy-mutation.log, but no subsequent browser receipt.
The older fixture browser proofs establish rendering only. Do not conflate them.

The existing owner dialogue says both versions get the same requests and the
comparison is fair. That approved catalog wording was not changed. Its use on
an incomplete comparison needs review against the frozen workplace story
contract; do not silently edit the catalog or claim the live comparison was fair.

### Final regression and preservation

The regression already running at the handoff request finished with 1,676
passed, one skipped, one deselected and the existing port_dead failure in
223.36 seconds. Log: /tmp/shiftwork-s45-live-20261024/final-pytest.log.
The clean-install test was explicitly deselected because installs are not
authorized. This does not establish a passing packaging check. Earlier Node
verification retained 299 passes; no new Node run followed the user stop.

The S45 source mutation matrix now defines 109 faults, with proof spread over
multiple logs, not one fresh 109-fault run. The prior 108 proofs and new
planned-copy fault need count/assertion audit. The inherited S43 vocabulary
fault previously died in invalid setup; its separate strict reproof is retained
at /tmp/shiftwork-s45-amendment-vocabulary-strict-proof.log. Do not count the
setup crash as a kill. No independent model review establishes correctness.

At handoff, branch is shiftwork/slice-45, HEAD, local main and local origin/main
all equal fc0d21d32a21d23534943ebec9bb2518126e8413. The index is empty. There
are 28 modified tracked files and 19 untracked S45 files, all preserved.
All 106 material hashes in /tmp/shiftwork-s45-material-baseline.json match.
S45 has no acceptance, commit, publication or additional live authorization.
Offline audit and continuation remain within the original slice go-ahead.

## Fresh offline continuation and source-review boundary, 2026-10-24

The [fresh audit](slice45-offline-audit-2026-10-24.md) supersedes the earlier
pending-audit and regression notices above. The stop is before terminal
completion and checkpoint readback after two provider replies. Their measured
round trips total 17,461 ms; 28,370 ms of the 45,831 ms action remain
unattributed because no stage durations were retained. LifecycleError is the
deliberate stop-after-failed-slot signal. No specific underlying latency cause
or confirmed live timeout fix is claimed.

The user chose preparation of a new learner-style pair after the diagnosis,
with identical deadline conditions and source review before any live approval.
The prompt and schema-validation sources under
/tmp/shiftwork-s45-repair-proposals-20261024/ are PROPOSED_UNAPPROVED, produced by
demos/s45_repair_proposals.py. They share the exact Nano model, reasoning off,
temperature 0, one call, no retry, 1,024 output tokens, 8 KiB input and the
unchanged 20/45-second deadlines. Twenty-one authored-reply checks pass. No
model repair quality, live eligibility or learner work is established. The old
frozen A/B pair and stop are unchanged.

The user also approved gating the existing owner line on COMPLETE/FINALIZED
and every planned repetition retained equally, hiding it when counts are
missing or unequal. Catalogue text is byte-identical to HEAD. Ten separate
owner-line mutations pass, including absence/presence, and the final actual
stopped comparison passes desktop, mobile and native 200% browser checks with
the latest PLANNED copy. The real stop stays at port 8453, A one retained and
B zero, no choice available and no mutation request sent.

port_dead is fixed by distinguishing connect from response timeout, without
fixture edits. Each cause has its own failing-capable mutation. A separate
gateway defect is fixed by enforcing an absolute deadline around the provider
await, without changing the 20-second ceiling. A real local HTTPX trickling
response exceeds the total deadline when the guard is removed; the named
assertion fails and the restored control passes. It does not explain the
sub-20-second provider replies in the original stopped action.

Fresh final regression: 1,703 Python passes, one live-only skip, one deselected
install test and two existing deprecation warnings. Node: 310 passes. The
109-fault source matrix, 14 client-rate faults and nine served rendering
faults were reproduced with zero survivors and passing restored controls.
The gateway's seven existing faults were re-proved after the absolute-deadline
change; one new deadline guard and two local-timeout guards have separate
proofs. The ten obligation-50-to-54 cases pass for one/three repetitions; asset
closure has nine passes. Audit receipts stay private under
/tmp/shiftwork-s45-audit-20261024/. Invalid setup runs and corrected mistakes
remain logged and are excluded from proof.

The scoped architect-reviewer cleanup scan recommends no deletion or rename.
All protected material, original live evidence and original candidate hashes
are preserved; the index and HEAD remain unchanged. The actual ledger hash
matches preparation and the LEARNER_CHOICE count is zero. S45 remains
INCOMPLETE, unaccepted and uncommitted. Candidate approval, a new bounded live
action, explicit eligible selection, acceptance and publication remain separate.

## New comparison proposal continuation, 2026-10-24

The supplied handoff reports a favourable experimental-candidate review.
Its 41-check count is user-reported without a supplied command or receipt.
Both actual source hashes still match, and the manifest remains
PROPOSED_UNAPPROVED. No approval or freeze was inferred.

The [new comparison proposal](slice45-new-comparison-proposal-2026-10-24.md)
specifies the exact A prompt and B schema packages, identical reasoning-off
settings and unchanged 20/45-second deadlines. One fresh store is proposed
under /tmp/shiftwork-s45-prompt-schema-live-20261024/, with at most 42 model
calls and 24 Sandbox operations. Its reserved inference projection is
US$0.09289728 at repository rates. Actual billing and Sandbox cost are unknown.
The original stopped store and its one-shot marker remain untouched.

Fresh verification has 21 passing proposal tests and four separate authored
missing-alternative/extra-stock controls. The latter confirm structural
validation accepts those plans while independent assessment rejects both
candidates' resulting answers. The simulated meter refuses operation 25 and
call 43. All 106 material hashes, eight original evidence files and the original
ledger match; LEARNER_CHOICE count is zero. Receipts and the rerunnable offline
preflight are in /tmp/shiftwork-s45-new-comparison-proposal-20261024/.
The initial SQLite row-factory setup error is logged and excluded from proof.

This continuation changes documentation only. It does not rerun the retained
full regression or browser suites. No new candidate version, freeze, comparison
reservation, credential read or live action occurred. S45 stays INCOMPLETE,
unaccepted and uncommitted, pending explicit candidate and live authorization.

## Prompt/schema approval and zero-call preparation, 2026-10-24

The user replied "Approved" to the exact new comparison proposal. This approves
both experimental sources, their freeze and one comparison with at most 42
model calls, 24 Sandbox operations and US$0.09289728 reserved inference under
the existing US$5 inference ceiling. Deadlines are unchanged. Sandbox cost is
unknown. No automatic selection, operation, acceptance or publication is covered.

The new action is /tmp/shiftwork-s45-prompt-schema-live-20261024/.
Its manifest is APPROVED_EXPERIMENTAL, SHA-256
6459786521aeb770428e25bbfc398e91af894652f0a01f43a59f69b63b74b8d6.
The original proposal-stage manifest is backed up there before its approval
metadata was updated. No reviewed service byte changed. The earlier preflight's
PROPOSED_UNAPPROVED assertion describes its pre-approval checkpoint.

Fresh zero-call preparation creates a new bookshop-shift-01 in that store only.
The S44 source is RECORDED_INSPECTION and every investigation field identifies
operator performance. A is template-authored ver-0003 with artifact hash
136c4a7bba2bb940a0608da4edc4fabe9ee9e9201e9c6c201e97b9a751915478.
B is template-authored ver-0004 with artifact hash
4a8816aa50a5052ad7a6114aeb6351ac23198bbf54bfa87fc3995e348c346764.
These IDs belong to the new store and do not replace the old pair's records.
Readback confirms both source hashes, zero real qualifying comparisons, zero
LEARNER_CHOICE rows and the prepared ledger hash. Calls and operations are zero.

prepared.json SHA-256 is
404270442c3753271051d72f3b624f2174307b6843dca5dce2704c3663268c63.
The one-shot runner SHA-256 is
5da767e696179278b9d46178d5c9ccedfbe7ca7c98523068af02b32b32a74845.
It pins runtime, material, source and original-evidence hashes. Its offline
meter control reaches 24 operations and 42 calls and refuses both next attempts.
Separate in-memory faults removing the marker and receipt refusal each fail
their named assertion and pass the restored control. No live marker exists
at this pre-call checkpoint. Receipts are self-test.log, one-shot-controls.json,
preparation.log and prepared.json in the action directory.

## Approved prompt/schema comparison stopped, 2026-10-24

The one approved action stopped after 23 inference reservations and 13 Sandbox
operations, with INCOMPLETE outcome. A has zero of nine planned public batches
passing and four retained. B has four of nine passing and six retained. Neither
is eligible. There are no choices or ledger changes. No retry or tuning followed.
The unused 19 calls and 11 operations are closed, not transferable authority.

The stop is A2's first public repetition, run-0020 in the new store. It records
PROVIDER_TRANSPORT_FAILED for request 1, a successful reply for request 2,
Sandbox SUCCESS and two verified checkpoint captures. The adapter's gateway
failure flag then returns SANDBOX_TERMINATED. This is not evidence of a Sandbox
crash. The underlying transport exception remains unknown. Public A1 failures
are six unknown conditional_alternative task names; B's two completed-batch
failures retain extra task results rejected by independent assessment.

The [full result](evidence/slice45-prompt-schema-live-2026-10-24.md) records
costs, exact hashes, terminal protected aggregates, proof limits and the scanned
public package. Current-action reserved inference is US$0.05087232. Twenty-two
known replies project US$0.00101508 at repository rates. Failed-request usage,
actual billing and Sandbox cost are unknown. All S45 reservations now total
31 attempts and US$0.06856704. The existing US$5 inference ceiling is unchanged.

The actual read-only review is http://127.0.0.1:8455/?board=bookshop#compare.
Fresh desktop/mobile 100% and native 200% checks pass with exact rates/causes,
all ten retained run links, disabled choices, Step 4, empty hidden owner bubble
and zero mutation requests or JavaScript exceptions. These are Chromium
workbench checks with WebGL disabled. Original evidence, reviewed sources,
runtime and all 106 material hashes are unchanged. No full suite was rerun
because no product implementation changed. S45 remains incomplete, unaccepted
and uncommitted. Further live work and publication need fresh authority.

The public result report and JSON package are ignored by the existing evidence
directory rule. They exist locally and must be preserved through handoff, then
included deliberately if publication is later authorized. Nothing was staged.
The initial final-inventory assertion assumed they would appear as untracked;
that setup error is logged in MISTAKES.md and excluded from passing proof.

## Revised comparison completed, 2026-10-24

After the authorized offline repairs, the user approved the exact revised pair
and one fresh action: 42 calls, 24 operations and US$0.09289728 reserved inference.
The action at /tmp/shiftwork-s45-revised-live-20261024/ completed all planned
execution with outcome COMPLETE. Both earlier stopped stores remain unchanged.
A passes seven of nine public batches; B passes nine of nine. Both retain nine
public batches and pass three of three protected phases. Only B is eligible.
No selection or operational ledger change occurred. The allowance is exhausted.

All 42 replies report 18,241 input and 1,877 output tokens, projecting
US$0.00154494 at repository rates. This is not billing. Actual billing and Sandbox
cost remain unknown. S45 inference reservations now total US$0.16146432.

The [actual result](evidence/slice45-revised-live-2026-10-24.md) records frozen
source identities, A's semantic failures, separate protected aggregates,
preservation and fresh actual browser proof. Desktop/mobile checks pass at
native 100% and 200%, including all 18 links, B eligibility, confirmation/cancel
and Step 5. The first copied Step 4 expectation is logged and excluded, not a
product failure. Review: http://127.0.0.1:8456/?board=bookshop#compare.

S45 awaits explicit selection of B from this action and acceptance. It remains
uncommitted. Operation, publication, deployment and S46 need separate authority.

## User selected B and accepted S45, 2026-10-24

The user replied "Select B and accept S45" to the completed live result.
The production append_selection path recorded VALID choice sel-0002 for B,
ver-0004, artifact hash
a71808a838c2df4cfa62883ea992d50bb942ab29beb0f6821162ccc9fbf41667,
in /tmp/shiftwork-s45-revised-live-20261024/. A, ver-0003, is retained.
Only that new selection row changed. All pre-existing rows, the operational
ledger, comparison captures and old stopped evidence are preserved. Selection
used zero additional provider calls and zero additional Sandbox operations.

S45 is COMPLETE and ACCEPTED. The [accepted evidence](evidence/slice45-revised-live-2026-10-24.md)
retains the bounded operator-demo limits. Current read-only selected-state
review is http://127.0.0.1:8457/?board=bookshop#compare; the earlier 8456 review
retains the pre-choice comparison. The slice is uncommitted. Publication,
operation, deployment and S46 remain separately authorized.
