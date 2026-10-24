# S45 offline audit, 2026-10-24

S45 is unaccepted and uncommitted. No new live call, candidate replacement,
selection, publication or deadline change has occurred in this audit.

## Plan and authority

1. Reverify Git, receipts and protected material; diagnose the stopped action.
2. Put the demo-fit decision to the user before preparing a different pair.
3. Audit repetition policy, public evidence, mutations and rendered output.
4. Repair the reproduced port_dead failure; run proportional regression and
   architecture cleanup. Keep acceptance separate from publication.

The user chose preparation of a different pair only after the offline diagnosis,
with two learner-style repairs, equal deadline conditions and source review
before any live approval. This permits preparation, not a live action.
The user also approved showing the existing owner line only after every planned
repetition ran with equal counts. Catalogue text must remain unchanged.

## Entry state and preservation

[verified 2026-10-24] Branch shiftwork/slice-45; HEAD, local main and local
origin/main equal fc0d21d32a21d23534943ebec9bb2518126e8413. No fetch was performed.
Entry inventory: 28 modified tracked files, 19 untracked files, empty index.
All entry files are preserved. Audit additions and repairs extend that inventory.

The receipt, original private live.db and public stop package match the hashes
in the handoff. All 106 entries in /tmp/shiftwork-s45-material-baseline.json
match. Initial git diff --check passes. The one-shot marker remains intact.
The original private database is inspected using SQLite mode=ro only.
Audit receipts are under /tmp/shiftwork-s45-audit-20261024/.

## Offline stop diagnosis

[verified 2026-10-24] The failed live run is run-0011, the first public A batch
of experiment-bookshop-shift-01-c1. The receipt records STOPPED, INCOMPLETE,
45,831 ms, two inference reservations and one Sandbox operation. There are no
verified run-0011 customer captures. No B or protected execution occurred.
The two provider replies finish with stop, not length, and contain parsed plans.

Retained controller records establish this sequence:

1. The first provider request returns in 11,105 ms, with 280 input and 1,016
   output tokens.
2. The adapter processes the first capture_written announcement and records
   inference_meter_complete for request 1. This establishes an announcement,
   not checkpoint readback or a verified customer response.
3. The second provider request returns in 6,356 ms, with 280 input and 619
   output tokens.
4. No second capture_written marker, terminal completion or checkpoint-readback
   record is retained. The adapter returns REQUEST_TIMEOUT and zero captures.

The adapter has exactly two REQUEST_TIMEOUT return sites: an expired wait for
operation events, or expiry of its loop without observing a terminal event.
Both occur before checkpoint capture readback. The records do not distinguish
those two sites. They also do not prove whether the second reply was delivered
to Sandbox stdin before the stop.

The known provider time totals 17,461 ms. Subtracting it from the driver's
45,831 ms total leaves 28,370 ms unattributed. The total includes reservation,
uploads, startup, event polls, stdin delivery, service/tool work and cancellation.
There are no retained durations for those stages. The observation measured_at
timestamps were assigned during persistence after execute returned, not at each
network event. The retained spawn manifest has a 45-second timeout but no stage
timestamps. Neither live.log nor the public package supplies the missing times.

[unknown] Which stage consumed those 28,370 ms, whether Sandbox itself reached
its timeout, and whether this pair would systematically time out. Two provider
durations below 20 seconds do not establish a gateway failure. One stopped
workspace cannot establish a systematic latency confound. A's 1,635 total output
tokens and B's separate 73-token sample do not provide comparable workspace
timings. No live probe was used to fill these gaps.

### LifecycleError origin and queued rows

[verified 2026-10-24] execute_comparison_slot retains the adapter's failure and
marks the active slot FAILED. execute_comparison explicitly raises LifecycleError
with "live comparison stopped after a driver failure; no retry" when a live
slot returns FAILED. Its outer handler marks the experiment FAILED and rethrows.
The one-shot launcher catches that error and records its class. This is the
intended stop signal, not evidence of a second exception inside the Sandbox.
The fresh stop_failed_phase and stop_failed_slot mutations each reach their
named no-further-send assertion, with restored passing controls.

Only run-0011 was sent. The two additional repetitions of its active slot,
run-0012 and run-0013, are FAILED without execution evidence. Fifteen runs in
the five untouched slots remain QUEUED in the immutable live database. They are
unexecuted reservations, not failed model replies or completed repetitions.
The public view must show A 1 retained of 9 and B 0 retained of 9, with neither
candidate eligible. No run is retried or inferred to have completed.

The available evidence bounds the stop to waiting for post-reply operation
progress before checkpoint readback. It does not establish the underlying
latency cause. A fresh live run cannot be presented as a confirmed timeout fix.

## Demo-fit decision

The stopped pair is one wording change with a reasoning-configuration toggle.
It does not demonstrate two distinct learner-style repairs or explicit selection
of an eligible candidate. B's single compatibility response added stock outside
the request contract and failed offline useful completion; B did not run in the
comparison. That is a risk signal, not a measured B comparison failure rate.

The user chose a new proposal after seeing the diagnosis, preserving the stopped
pair and its records. Any proposed sources remain operator-authored examples of
learner-editable repairs. They are not learner work, model-authored patches,
learning evidence, measured repair quality or approved live candidates.

## Fresh verification

- Fresh complete source matrix: 109 unique names and 109 unique edits, all with
  named assertion failures, byte-identical restoration and passing clean controls.
  Log: /tmp/shiftwork-s45-audit-20261024/source-mutations.log.
  The two message-less assertions were also checked at their actual failing
  source locations, rather than counting matching traceback context alone.
  The inherited S43 vocabulary fault was freshly re-proved at its vocabulary
  assertion, with a passing clean control and restored bytes, at
  inherited-vocabulary-proof.log. Its historical invalid-double crash is not
  counted as proof or as an additional S45 fault.
- port_dead reproduces before repair. A bound, non-listening socket on this Mac
  times out at connect. The local adapter previously merged connect and response
  timeouts. The repair distinguishes connection establishment from response wait;
  no fixture bytes change. Focused conformance now has 55 passes and one existing
  separately authorized live-only skip. Two separate connect/response mutations
  fail the intended cause assertion and pass after byte-identical restoration.
  Log: timeout-mutations.log in the audit receipt directory.
- An independent gateway defect was reproduced and repaired. HTTPX phase/idle
  limits were the only provider wait bound. asyncio.timeout now enforces the
  existing absolute 20-second ceiling. Two client-path controls and a real HTTPX
  local trickling-response control pass. Removing that guard lets the real local
  reply arrive after the total deadline and fails its named assertion; restoration
  passes. The seven existing gateway faults were also re-proved on this code.
  Logs: gateway-green.log, gateway-mutations.log, gateway-real-http-control.log
  and gateway-real-http-mutation.log. This repair does not explain the old stop,
  whose two retained provider replies each returned in less than 20 seconds.
- Full Python regression: 1,703 passed, one skipped, one deselected, two existing
  deprecation warnings, 226.79 seconds. Command: PYTHONDONTWRITEBYTECODE=1 with
  a fresh PYTHONPYCACHEPREFIX, .venv/bin/python -B -m pytest -q --deselect
  tests/packaging/test_clean_env_install_and_run.py::test_clean_env_install_and_run.
  Log: regression-final.log. The skip is the separately authorized live Sandbox
  conformance check; clean installation is excluded, not passed. No installation
  occurred in this audit. The earlier 1,702-pass run predates the additional real
  HTTPX control and remains separately retained at regression.log.
- Full Node regression: 310 passed, zero failed/skipped, at
  node-regression-final-v2.log. This includes owner_lines_never_suggest and its
  scanner self-tests, plus ten distinct owner-line mutations. Incomplete and
  complete states fail separate faults. Missing raw counts, missing reduced
  counts, zero counts, wrong labels, unequal retention, unexecuted rows and
  empty evidence are also covered. The catalogue literal is byte-identical to
  HEAD. Initial anchor, transition-key and missing-count mistakes are retained
  in MISTAKES.md and their failed logs, not counted as successful proof.
- Fourteen client-rate faults: zero survivors, restored bytes and passing clean
  controls, client-rate-mutations.log. Nine distinct served browser faults each
  failed their named assertion and passed a fresh clean control,
  browser-fixture-mutations.log. The authored fixture on port 8454 establishes
  rendering only, never live rates, learner work or model quality.
- Actual stopped comparison on port 8453: final source passes desktop 1280x720,
  mobile 390x844 and native 200% at both sizes. The PLANNED wording is verified;
  the owner fairness line is absent; A has one retained repetition and B zero;
  choice controls are disabled; the exact failed-run link works; reasoning is
  collapsed; no mutation request or JavaScript exception occurs. Log:
  browser-stop-final.log, with screenshots under browser-stop-final-1x and
  browser-stop-final-2x. Screenshots at mobile 100% and desktop 200% were visually
  inspected. These are Chromium viewport checks with WebGL disabled by the
  evidence harness, not physical-device, renderer-performance or AT evidence.
  A final actual-stop reproof explicitly requires "Step 4 of 7" and a hidden,
  empty owner bubble. Removing the owner gate in the served source fails that
  named bubble assertion; fresh restored 100% and 200% controls pass. This avoids
  mistaking an unknown guide or CSS-hidden text for successful state gating.
  Log: browser-owner-setup.log.
- Final asset closure: nine passes, asset-closure-final.log. No dependency,
  CI configuration or lockfile change was made.
- Obligations 50 to 54 pass at both one and three repetitions, ten named cases
  at obligations-50-54.log. Obligations 68 and 69 are included in the 109-fault
  matrix and full regression. This retains protected-phase order, distinct
  workspaces, bound stimuli, scanner self-tests and separate denominators.

## Proposed pair for source review

Both sources are PROPOSED_UNAPPROVED, generated by
demos/s45_repair_proposals.py. The stopped demos/s45_repairs.py and original
frozen A/B files remain unchanged.

- Prompt repair: /tmp/shiftwork-s45-repair-proposals-20261024/prompt/service.py,
  SHA-256 1b90992e792b069cc3e67732b5eb3b3d378aca67df1eab14c15ce0498fd5ebf6.
  It replaces the descriptive plan prompt with compact task/tool guidance.
- Schema repair: /tmp/shiftwork-s45-repair-proposals-20261024/schema/service.py,
  SHA-256 8924cb5d8fffa1c4990cc97c5257e86d444b34bf0f06a6959aecf23678168b84.
  It supplies a task/tool schema in the user prompt and rejects malformed plans,
  duplicate tasks, incompatible tools and reversed collection/alternative order.
  It never adds a missing task, fills a result, retries or calls a substitute.

Both propose the exact Nano model, enable_thinking=false, temperature 0, one user
message, one call per request, no retry, 1,024 output tokens, 8 KiB input,
20-second gateway and 45-second workspace deadlines. Twenty-one offline tests
use authored replies through the trusted driver/gateway and independent public
assessment, and check that all starter behavior outside plan requesting and
validation is unchanged. Valid control plans complete the public incident;
missing or invalid plans remain unsuccessful. These controls are not live
eligibility, repaired model behavior or proof that either version will qualify.

G4 is consistent with S43 when kept scoped: a labelled learner-authored fallback
may be an ordinary-code repair; the starter and trusted gateway never supply
hidden rescue code. The demo pair must remain model-dependent. Both proposals
do so, and neither completes tasks omitted by the model. No comparison ranks
fallbacks as inherently worse. G13 reasoning text remains public-only display
evidence and never becomes an evaluator input.

## Cleanup, spend and remaining boundary

The architect-reviewer post-slice cleanup scan is scoped to S45 additions and
changed definitions. It inventories 484 repository files, checks import/launch
references, actual call sites for nine new top-level production functions,
unused imports in the new production/example modules and current authority
notices. The first identifier census incorrectly counted definitions as
references; it is excluded as evidence. The corrected actual-call scan finds
callers for all nine functions. Test files are discovered entry points, not
orphans. Protected fixtures, historical gate records and old examples stay.
No deletion or rename is recommended. Receipt: cleanup.json.

No new provider or Sandbox call occurred. The eight earlier S45 reservations
still project US$0.01769472. Seven replies report 1,960 input and 5,385 output
tokens, projecting US$0.00141000 at repository rates. Original failed-probe usage,
actual vendor billing and Sandbox cost remain unknown. No unused allowance is
treated as fresh authority.

The original live database, receipts, public packages, frozen candidate sources,
one-shot marker and all 106 protected-material digests are preserved. The ledger
hash matches preparation and the actual LEARNER_CHOICE count is zero. Final
Git/preservation details are recorded in preservation.json in the audit directory.
Branch and all three local refs remain at fc0d21d, with 33 tracked modifications,
24 untracked files and an empty index. All 49 files in the audit's pre-mutation
snapshot remain, including the inherited 47-file tree and the two initial
port_dead repair files. Only named authorized audit changes differ from that
snapshot; the 106 protected-material hashes match and git diff --check passes.
The owned authored-fixture preview is stopped after verification; the existing
read-only actual-stop review on port 8453 remains available.

S45 still lacks a completed live comparison and explicit eligible selection.
The user must review the proposed sources before approving a new frozen pair,
then separately authorize any live action with exact call/operation/spend limits.
The workspace latency cause remains unknown, so no rerun may be described as a
confirmed timeout fix. S45 acceptance and publication remain separate decisions.
