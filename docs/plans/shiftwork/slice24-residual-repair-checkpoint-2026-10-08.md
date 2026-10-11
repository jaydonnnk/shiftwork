# S24 residual repair checkpoint: 2026-10-08 Asia/Singapore

**Scope.** This is the continuing agent's repair of the two residual findings (R1
and R2) from the second independent review of the repaired S24 work. The first
review's F1 to F4 repairs stay exactly as recorded in
[slice24-review-repair-checkpoint-2026-10-08.md](slice24-review-repair-checkpoint-2026-10-08.md).
No gate, reviewed material, seal, pin, install, credential, live call, spending,
publication or S25 authority changed. The reviewer's evidence directory was only
read. No source fault ran in the shared OneDrive tree.

## R1: missing required results cannot present a no-action assurance

The review omitted the owner result, the write result or both from a captured GTM
qualification response through the real API, directly in the captured bytes. The
assessment marked exactly the omitted tasks `REQUIRED_TASK_MISSING`, reduction
created one `INCIDENT_OPENED` with the complete decision trace, and the raw
faulty bytes stayed exact. The projection still rendered "No additional owner,
record or handoff is required." because the rejection verdict was computed only
from the task rows the response happened to carry
(`output_evidence_for`, shiftwork/orchestrator.py).

Repair: the verdict now also derives from the complete stored assessment for the
request (any assessment row with `mandatory_pass` false), so a required result
absent from the response cannot leave the generic NOT_APPLICABLE sentence in the
derived text. Partial failure removes unaccepted task text as before, keeps
accepted claims available and appends the existing rejection label. Assessment
rows, raw captured bytes and incident-only reduction are unchanged.

## R2: unreadable retained bindings return a replay evidence verdict

The review demonstrated three persistable valid-JSON corruptions of the retained
execution context: `request_specs_hash` removed from the workload JSON,
`content_hash` removed from the condition JSON, and `request_count` replaced with
the text `corrupted-count`. The unmodified copy replays IDENTICAL; after the edit
`replay_assessment` raised pydantic `ValidationError` while reconstructing the
context, before entering the block that converts expected input failures into the
`UNKNOWN_MISSING_INPUTS` verdict.

Repair: the retained-input loading boundary (`repo.get_execution_context`,
`repo.get_run_snapshot_bytes`, `repo.list_outputs`) converts expected
deserialization failures (`ValueError`, `TypeError`) into the
`UNKNOWN_MISSING_INPUTS` verdict and writes nothing. The assessment and reduction
section stays outside that conversion, so the verified F4 behavior is unchanged:
reducer `ValueError` and `RuntimeError` still propagate, invalid capture
inventories still return the verdict, and healthy replay still returns IDENTICAL.
Malformed JSON beyond SQLite's `json_valid` CHECK constraints cannot persist, so
it stays outside the failure model, matching the review's excluded setup.

## Shipped regression cases and failing-capable proof

Six cases were added to `tests/orchestrator/test_gtm_review_repairs.py`:

- `test_gtm_missing_required_task_cannot_present_no_action_assurance`,
  parametrized owner/write/both, asserting the assessment rows and
  `REQUIRED_TASK_MISSING` reasons, raw faulty byte preservation, incident-only
  drafts, zero projection writes, the no-action sentence absent, the rejection
  label present and the accepted-claim kinds;
- `test_gtm_unreadable_retained_binding_returns_evidence_verdict`, parametrized
  spec_binding_absent / condition_binding_absent / workload_count_type, asserting
  the corruption persists as valid JSON, the verdict is `UNKNOWN_MISSING_INPUTS`
  and zero rows change.

Against the pre-repair orchestrator the cases fail on the intended sites: the
three projection cases fail the no-action text assertion and the three valid-JSON
binding cases leak the `ValidationError`. An initially included malformed-JSON
variant was rejected by SQLite's CHECK constraint at setup, is not persistable
and was removed, matching the review's excluded setup. After the repair the
module passes 39 tests (33 earlier repair cases plus 6 new).

## Verification on the repaired tree

- Reviewer acceptance probes, run from a disposable copy at
  `C:\swi24-repairs-20261008-1`: `test_missing_task_projection.py` 3 passed,
  `test_binding_decode_review.py` 3 passed with fresh observations showing
  `UNKNOWN_MISSING_INPUTS` and zero writes, and the surrounding additional-review
  file passes with its documented malformed-JSON setup deselected (13 passed,
  2 skipped, 1 deselected). Fresh observation bytes live in that copy directory.
- Fresh full non-packaging regression, repaired tree: 1,379 passed, one
  live-only skip, two existing warnings, exit 0 (482.33s).
- Healthy behavior unchanged: `demos.gtm_operation` completes with replay
  IDENTICAL; the healthy finalized projection still renders the full
  qualification/owner/record/no-action text with no rejection label;
  `demos.gtm_reviewed` reports PASS with approval digest
  `8d87c2dc279f31f3206ec389e0f72b34b50e038c59bc764ef60c13489b62d1fa`.
- Mutation controls: all 55 S24 and 106 S23 anchors preflight unique on the
  repaired tree (`--check-anchors`), and the full inventories re-ran against a
  9,221-file disposable physical copy: 55 of 55 and 106 of 106 `FAIL_CAUGHT`,
  zero setup errors, every faulted file restored, and the whole copy verified
  byte-exact against the workspace afterward (9,221 of 9,221).

## Remaining limits

- The six new cases are finite controls, not branch coverage; the reviewer's
  next round re-verifies the inventory independently.
- No new reviewed material is approved. The human-review workload remains a
  disposable operator mission/state, not shipped material.
- Packaging, installation, live Sandbox conformance (the explicit skip), the S25
  browser journey, model quality, learner gain, hostile isolation and production
  readiness remain unverified and unchanged.
- History-verification cost remains unmeasured; the earlier checkpoint's limits
  carry over unchanged.

S24 remains unaccepted, unstaged and uncommitted. No process remains running at
closeout. Await user instructions; do not stage, commit, publish or continue.

## Addendum 2026-10-09: R2 inheritance gap and guard proofs

A fresh session re-verified the R1/R2 repair above instead of trusting it. R1 held.
R2 was incomplete: the conversion sat at the replay call site, not the loading
boundary. GTM inheritance (`freeze_diagnostic_context` via
`_verify_pipeline_history`) loads the same retained contexts outside that catch, so
the reviewer's three valid-JSON corruptions still leaked pydantic `ValidationError`
when starting the next GTM operation, instead of a conflict refusal.

- Repair: `_pipeline_history_context` (shiftwork/orchestrator.py) loads each
  retained context for history verification and converts `ValueError`/`TypeError`
  into `LifecycleError("conflict", "pipeline history has unreadable retained
  inputs")`. Assessment and reduction stay outside every conversion.
- New regression: `test_gtm_inheritance_refuses_unreadable_retained_binding`
  (three cases) failed 3/3 with the leaked `ValidationError` on the pre-fix tree,
  then passed. Corruption setup is shared through `corrupt_retained_binding`.
  Replay and inheritance tests now turn a leaked `ValueError` into a named
  `pytest.fail`, so a regression lands on an assertion site.
- Three named S24 faults added (`missing_task_assurance`,
  `unreadable_replay_binding`, `unreadable_history_binding`); 58 anchors unique.
  Run in disposable copy `C:/swr24-r12` (9,222 files): 3 of 3 `FAIL_CAUGHT`, zero
  errors, source restored. The earlier 55 S24 and 106 S23 controls were not rerun.
- Repair module: 42 passed. Full non-packaging suite: 1,382 passed, one live-only
  skip, two existing warnings, exit 0 (589.89s). It collected the inheritance tests
  before their `pytest.fail` wording change; the module was rerun after (42 passed).
- Not covered: the other `repo.get_execution_context` readers (projections and
  display, 16 more call sites) still raise on an unreadable context. No GTM
  diagnostic-experiment text path (`experiments._diagnostic_customer_text`) was
  assessed for R1-style assurance; it renders unassessed service output.

## Addendum 2026-10-10: full fault rerun on the repaired tree

The complete S24 and S23 inventories were rerun against the tree carrying the
2026-10-09 repair, closing the "earlier controls not rerun" gap above.

- Anchor preflight in the shared tree (`--check-anchors`, no writes): 58 S24 and
  106 S23 anchors unique.
- Fresh disposable physical copy `C:/swr24-r13`, outside OneDrive, verified
  byte-exact against the workspace before the run (9,227 of 9,227 files; top-level
  `.claude`, `.env`, `.git`, `.venv`, `.venv313` and every `__pycache__` excluded).
  `shiftwork/` preimages archived to `C:/sw24-r13-receipts/preimage-shiftwork`
  before any fault. Imports resolved to the copy (`C:\swr24-r13\shiftwork`).
- Results (receipts in `C:/sw24-r13-receipts/s24` and `s23`, audit in
  `audit.json`): 58 of 58 and 106 of 106 `FAIL_CAUGHT`, zero errors, exactly one
  failure per control, every faulted file restored. All 58 S24 receipts match
  their named assertion text. Both runners exited 0; total 8m59s.
- After the run: the shared workspace is byte-identical to its pre-run manifest
  (9,227 files, no missing, extra or changed); the copy differs from it only in
  `.pytest_cache/v/cache/lastfailed` and `nodeids`; the preimage archive matches.
- Interpreter: Windows Application Control blocked `.venv313/Scripts/python.exe`
  this session. The round used the venv's own base interpreter (uv CPython
  3.13.14) with `PYTHONPATH` set to `.venv313/Lib/site-packages` and
  `PYTHONNOUSERSITE=1`; the venv has no `.pth` files, and pytest 9.1.1 and
  pydantic 2.13.5 loaded from it. See `MISTAKES.md`, 2026-10-10.
- Still open: independent re-review of the R1/R2 repair. The S23 runner checks
  for one assertion failure per control, not named assertion text. Counts are
  finite controls, not branch coverage. The "Not covered" limits above stand.

S24 remains unaccepted, unstaged and uncommitted.

## Addendum 2026-10-10 (second session): S23 named assertions, rerun and limit triage

- AGENTS.md section 6 "While working" now names the base-interpreter fallback and
  its preconditions (no `.pth` files in the venv, `shiftwork` imports from the
  intended tree). This graduates the fourth Application Control incident.
- `tests/packs/gtm_mutation_proofs.py` now requires named assertion text for all
  106 S23 controls, as S24 does. `EXPECTED_ASSERTIONS` holds 141 needles in 25
  groups, derived by script from the observed messages in
  `C:/sw24-r13-receipts/s23/results.json`, not written from memory. Each needle
  names the custom assertion text, the compared values, the `DID NOT RAISE`
  exception class, or the asserting generator or function (memory addresses
  excluded). A module-level check requires one entry per control. `named_run`
  applies only to the S23 entry point; `main(runner=None)` keeps the S24 runner's
  patched `run`, so same-named controls in the two harnesses cannot collide.
  Self-test against r13: 106 of 106 match, a bare `assert False` matches none.
  Three needle groups without custom text are substrings of a group that has it
  (`assert [] == ['owner']`, `assert [] == ['write']`, `assert (200 == 409)`);
  each still names the assertion its own node fails.
- Anchor preflight in the workspace: 106 S23 and 58 S24 anchors unique.
- Fresh copy `C:/swr24-r14`, verified byte-exact before the run (9,227 of 9,227
  files, same exclusions as r13); `shiftwork/` preimage archived to
  `C:/sw24-r14-receipts/preimage-shiftwork`; imports resolved to
  `C:\swr24-r14\shiftwork`, pytest 9.1.1, pydantic 2.13.5, base interpreter as in
  AGENTS.md. Results (receipts and `audit.json` in `C:/sw24-r14-receipts`):
  58 of 58 S24 and 106 of 106 S23 `FAIL_CAUGHT`, zero errors, exactly one failure
  per control, every file restored, all 164 receipts match their named assertion
  text. Both runners exited 0; 517 s. Workspace byte-identical to its pre-run
  manifest; the copy differs only in `.pytest_cache/v/cache/lastfailed` and
  `nodeids`; the preimage archive matches.

### Triage, not fixed: unreadable contexts at other readers

`shiftwork/` has 17 `repo.get_execution_context` call sites: 11 in
`orchestrator.py`, 4 in `comparison_flow.py`, 2 in `experiments.py`. Two convert
unreadable rows (`replay_assessment`, `_pipeline_history_context`). This count
finds 15 unconverted sites, not the 16 recorded on 2026-10-09. No API route
writes or edits a context row, so every case needs an out-of-band database edit
or storage corruption. Each read raises before any commit in its function, so no
partial write follows; the effect is the failure shape:

- Controller actions, HTTP 500 instead of 409: `append_selection` (selection),
  `create_later_condition_comparison` (observed operation context).
- Background executors read before their failure-marking `try`, so the run or
  slot stays `QUEUED`/`RESERVED` instead of `FAILED`: `execute_selected_operation`,
  `experiments.execute_experiment`, `execute_comparison_slot`, and the live path
  of `execute_comparison`. `finalize_selected_operation` (two reads) is inside its
  `except Exception`, which marks `FAILED`/`INTERNAL` and re-raises.
- Display, HTTP 500: `board_snapshot` (board, via the selection's comparison
  context), `output_evidence_for` and `_stimulus_record` (run outputs),
  `comparison_view` and `_diagnostic_experiment_view` (`GET /experiments/{id}`
  and the Investigate station).
- `deployment_assessment_inputs` (two reads) reloads the caller's own context, so
  it adds no failure beyond its caller's read.

Scope: outside the S24 exit contract as written. Gate 4 S24 names consequence,
capture, trace, idempotence, selection and experiment faults; R2 targeted the
verification consumers (replay, inheritance), which are converted. These readers
are shared by all engagements, the S24 plan requires non-GTM behavior preserved,
and display robustness falls to S25's room. The selection, operation and
later-condition reads are on the S24 demo path and fail closed, so a reviewer may
still class them with R2.

Proposed fix: one loading boundary for every non-replay reader that converts
`ValueError`/`TypeError` into `LifecycleError("conflict", ...)`; move the
executor reads inside their failure-marking blocks so runs end `FAILED`; keep
replay's `UNKNOWN_MISSING_INPUTS` verdict. One falsifier per consumer through
`corrupt_retained_binding`, plus a named fault per conversion.

### Triage, not fixed: diagnostic customer text

From code reading, not executed. GTM diagnostics are reachable:
`POST /shifts/{id}/experiments` without a comparison creates one for the
learner's candidate, and `GET /experiments/{id}` and the Investigate station's
`latest_diagnostic` return `customer_text` from `_diagnostic_customer_text`. It
renders every task in the validated envelope without consulting the task
assessments. A permitted but wrong owner therefore renders as the customer
answer, and an omitted required task leaves the other sentences, including a
`not_applicable` sentence, with no rejection note, while the same view lists
`mandatory_pass: false`. The pipeline renderer never emits sent-message, revenue
or service prose, and diagnostics write no ledger state or eligibility.

Scope: outside the S24 exit contract. Its "no surface presents a sent message or
a revenue quantity" clause holds here; R1 repaired the operational projection
(`output_evidence_for`); the diagnostic projection predates S24 (Gate 3 S3.3,
S3.7). S25's workflow bench would expose it, so it should close before S25.

Proposed fix: move the GTM accepted-task filter and rejection sentence out of
`output_evidence_for` into one helper used by both projections, with a falsifier
for a missing required task and a wrong owner in a diagnostic, and a named fault
on the shared helper.

Both fixes await user instruction. Still open: independent re-review of R1/R2.
S24 remains unaccepted, unstaged and uncommitted.

## Addendum 2026-10-11: review findings F1, F3, F4 and F6 repaired; F5 counts corrected

An independent adversarial review of R1/R2 (evidence in `C:\swrev24` and
`C:\swrev24-tools`, only read here) reported six findings. This round repairs F1,
F3, F4 and F6, corrects the F5 counts, and leaves F2 for a user ruling.

### Repair: one storage boundary for retained evidence rows

- `shiftwork/domain/errors.py`: `RetainedRecordUnreadable`, a `ShiftworkDomainError`
  with kind `conflict` (the existing API handler returns 409) that is also a
  `ValueError`, so every degrade path that already caught the underlying validation
  failure behaves as before.
- `shiftwork/store/repo.py`: `_retained(label)` wraps the deserializers of the five
  retained row types the review attacked: execution contexts (by id and by content
  hash), run outputs, check results, ledger events and task assessments. Only a
  deserialization `ValueError` or `TypeError` converts.
- `shiftwork/orchestrator.py`: `replay_assessment` reads the context, snapshot,
  outputs, stored checks and stored ledger drafts in one block that catches only
  `RetainedRecordUnreadable` and returns `UNKNOWN_MISSING_INPUTS`. Assessment and
  reduction stay outside, so reducer `ValueError`/`RuntimeError` still propagate.
  `_pipeline_history_context` is removed: both history loops read through the
  boundary and refuse unreadable history with the typed conflict.
  `output_evidence_for` presents no derived GTM answer when the request has no
  stored assessment.

Deviation from the proposal above: the proposal converted to
`LifecycleError("conflict", ...)`. The repository cannot raise the orchestrator's
type, so the boundary raises the domain conflict, which the API maps to the same
409 `{"kind": "conflict"}`. The reviewer's probes count anything but
`LifecycleError` as a leak, so they label these refusals LEAK.

### Per finding

- F1: a retry after a failed attempt whose reused context is unreadable returns 409
  and reserves no run (was 500). Diagnostic and operation freezes refuse with the
  typed conflict and write nothing. The comparison by-hash readers
  (`comparison_flow.py`, two sites) inherit the boundary; they were not executed.
- F3: an unknown `ledger_events.event_type`, `check_results.reason_code` or
  `verdict` gives replay `UNKNOWN_MISSING_INPUTS` and a typed inheritance refusal,
  with zero writes. An unknown task-assessment reason code returns 409 from the
  outputs view (was 500). This is a typed refusal, not a degraded answer.
- F4: shipped cases now kill a dropped `TypeError` arm (`mission_bytes_text` in
  replay and inheritance), each replay read moved outside the conversion, and each
  decorated row type. The reviewer's "second history loop uses the raw loader"
  fault no longer exists, because both loops read through the same boundary.
- F6: a captured GTM run with no assessment rows returns `customer_answer: null`,
  rendered by the client as "No validated customer answer. Inspect the captured
  bytes below." It no longer claims "returned no answer" or an assessment rejection.
- F2: not repaired. Awaits the user's ruling on scope.

### F5: count correction

Byte-identical faults were counted as separate controls. Preflight of the current
inventories: S24 69 controls are 65 distinct source faults, S23 106 are 102, and
the union of 175 is 165. The duplicates are the same source edit checked at two
test nodes (two S24/S23 groups shared across inventories, two within S24, two
within S23). This round's 13 rows are each distinct, so the earlier inventories were
58 controls = 54 distinct (S24), 106 = 102 (S23) and 164 = 154 (union), matching
the review. 33 S24 controls match only the generic needle `Failed: DID NOT RAISE`;
the 13 rows added here each match custom assertion text. Earlier entries in this
file state control counts without these caveats.

### Evidence

Interpreter: base uv CPython 3.13.14 with `-B`, `PYTHONPATH=.venv313/Lib/site-packages`
and `PYTHONNOUSERSITE=1` (AGENTS.md section 6); the venv has no `.pth` files,
`shiftwork` imported from the intended tree, pytest 9.1.1, pydantic 2.13.5.

- Red first: on the unrepaired source, the new and strengthened cases gave 9 failed
  and 10 passed. Each failure landed on its named assertion: three replay escapes
  (`check_reason`, `check_verdict`, `ledger_event_type`), two freeze escapes
  (diagnostic, operation), two retries returning 500, the outputs view returning
  500, and "unassessed capture claims an assessment rejection". The passing ten are
  the existing R2 behavior, `output_failure` (already converted, kept to guard
  placement) and the `healthy` retry control, which shows the retry reuses the
  failed attempt's frozen context.
- Green: `tests/orchestrator/test_gtm_review_repairs.py` 55 passed (42 earlier plus
  13 new or strengthened). Full non-packaging suite 1,395 passed, one live-only skip,
  two existing warnings, exit 0 (396.70s).
- Faults: preflight in the workspace, read-only: 69 S24 and 106 S23 anchors unique,
  every faulted file compiles. Fresh copy `C:/swr24-f1`, verified byte-exact before
  the run (9,227 of 9,227 files, r13/r14 exclusions); `shiftwork/` preimage archived
  to `C:/swr24-f1-receipts/preimage-shiftwork`; imports resolved to the copy.
  Results: 69 of 69 S24 and 106 of 106 S23 `FAIL_CAUGHT`, exactly one failure and
  zero errors per control, every file restored, every receipt matching its named
  needle (`audit.json`). Both runners exited 0; 502 s. Needles for the 13 rows
  were taken from observed exception text, not memory. After the run: the copy
  differs from the workspace only in `.pytest_cache/v/cache/lastfailed` and
  `nodeids`, the preimage archive matches, and the workspace is byte-identical to
  its pre-run manifest.
- Reviewer probes, run in the copy after the audit: the API retry probe passes
  (409), as do the check-row and output-row replay probes. The freeze, ledger-inherit,
  projection and TypeError-inherit probes read LEAK only because they classify
  `RetainedRecordUnreadable` as a leak (see the deviation above). The F2 diagnostic
  probes fail as expected, and the unassessed-capture probe crashes on its own
  `customer_answer["display_text"]` index because the answer is now `null`.

### Remaining limits

- Only the five retained row types convert. Other deserializers (runs, shifts,
  versions, incidents, experiments, trial slots, observations) still raise untyped
  errors on out-of-band edits.
- Background executors still read before their failure-marking `try`, so an
  unreadable row leaves a run `QUEUED`. Display readers of the five types
  (`board_snapshot`, ledger view, `comparison_view`, `_diagnostic_experiment_view`)
  now return 409 instead of 500 but have no dedicated case.
- F2 (diagnostic customer text) is open. Counts remain finite controls, not branch
  coverage. Packaging, live conformance, model quality and learner gain are unchanged.

S24 remains unaccepted, unstaged and uncommitted.

## Addendum 2026-10-11 (second session): F2 repaired

The user ruled on 2026-10-11 that F2 is repaired in S24. One shared helper now
decides GTM customer text for both the operational and the diagnostic projection.

### Repair: one shared assessed-text helper

- `shiftwork/domain/customer_answer.py`: `render_assessed_task_customer_text`
  takes the request's spec, mission, snapshot, validated envelope, request ordinal
  and the run's stored assessments. It returns None when the request has no
  assessment row. Otherwise it returns the rendered text and the accepted task ids
  (mandatory pass and `USEFUL_COMPLETION`). A partial failure, meaning a failed
  row or a response task with no passing row, renders only the accepted tasks plus
  "Some workflow task outputs were rejected by the independent assessment." The
  display filter is now `shown = accepted if rejected else passed`, equivalent to
  the former two-condition filter because every accepted task also passed.
- `shiftwork/orchestrator.py` `output_evidence_for`: the GTM branch calls the
  helper. The claims filter line is byte-identical, and no assessment still gives
  `customer_answer: null` (F6).
- `shiftwork/experiments.py` `_diagnostic_customer_text`: a GTM diagnostic calls
  the same helper. Other engagements render as before. `GET /experiments/{id}` and
  the Investigate station's `latest_diagnostic` both read this one function.

Observed by execution before the repair, on a diagnostic of the pinned starter:

| Case | Assessment | `customer_text` before | After |
|---|---|---|---|
| Starter as-is | owner, write `WRONG_ACTION` | `Synthetic qualification: QUALIFIED. Synthetic owner: owner-amer-platform. Synthetic pipeline record prepared for human handling. No additional owner, record or handoff is required.` | `Synthetic qualification: QUALIFIED. Some workflow task outputs were rejected by the independent assessment.` |
| Owner and write omitted | both `REQUIRED_TASK_MISSING` | `Synthetic qualification: QUALIFIED. No additional owner, record or handoff is required.` | same as above |

### Evidence

Interpreter: base uv CPython 3.13.14 with `-B`, `PYTHONPATH=.venv313/Lib/site-packages`
and `PYTHONNOUSERSITE=1` (AGENTS.md section 6); the venv has no `.pth` files,
`shiftwork` imported from the intended tree, pytest 9.1.1, pydantic 2.13.5.

- Red first: on the unrepaired source `test_gtm_diagnostic_text_matches_assessment`
  failed 3 of 3, each on its named assertion: `wrong_owner` "diagnostic text
  presents a rejected owner", `missing_owner` "diagnostic text presents a rejected
  write", `missing_both` "diagnostic text claims no action despite a rejected
  required task". The test also requires the Investigate station to show the same
  text. `test_gtm_response_task_without_assessment_row_is_rejected` passed on the
  unrepaired source: it guards moved behavior (a response task whose assessment
  row was deleted out of band) so the helper's second rejection arm has a falsifier.
- Green: `tests/orchestrator/test_gtm_review_repairs.py` 59 passed (55 plus 4).
  Full non-packaging suite (`pytest tests -q --ignore=tests/packaging -p
  no:cacheprovider`) 1,399 passed, one live-only skip, two existing warnings,
  exit 0 (374.35s).
- Inventory: two rows moved into the helper with unchanged nodes and needles
  (`missing_task_assurance`, `unassessed_projection`). Four are new:
  `unassessed_response_task` (second rejection arm), `rejected_fallback_shown`
  (the shown set under rejection), `rejection_sentence`, and
  `diagnostic_unfiltered` (the diagnostic's GTM dispatch). Preflight in the
  workspace, read-only: 73 S24 and 106 S23 anchors unique, every faulted file
  compiles in memory. S24 is 73 controls = 69 distinct source faults, S23 106 =
  102, union 179 = 169; each of the six helper rows is distinct and shared with no
  other control.
- Faults: fresh copy `C:/swr24-f2`, verified byte-exact before the run (9,227 of
  9,227 files, r13/r14 exclusions); `shiftwork/` preimage archived to
  `C:/swr24-f2-receipts/preimage-shiftwork`; imports and the runner root resolved
  to the copy. Results: 73 of 73 S24 and 106 of 106 S23 `FAIL_CAUGHT`, exactly one
  failure and zero errors per control, every file restored, every receipt matching
  its named needle (`audit.json`). The four new needles were predicted from the
  test's assertion order and each matches the text observed in its receipt. Both
  runners exited 0; 505 s. After the run: the workspace is byte-identical to its
  pre-run manifest, the copy differs only in `.pytest_cache/v/cache/lastfailed` and
  `nodeids`, and the preimage archive matches.
- Reviewer probes, run in the copy after the audit: the reviewer's probe file,
  byte-identical to the one in `C:/swr24-f1`, was copied in. Both F2 diagnostic
  probes pass (2 of 2; both failed in the previous round) and print the repaired
  text above (`probes-f2.log`, `probes-f2.xml`).
- This addendum and the `MISTAKES.md` update were written after the post-run
  manifests. Every edited file kept its pre-session line endings
  (`customer_answer.py` CRLF, the rest LF); `git diff --check` is clean.

### Remaining limits

- The helper's request filter (ordinal and id) has no fault: a GTM run holds one
  request, so no shipped case can tell it apart.
- A GTM diagnostic captured but not yet assessed now shows `customer_text: null`
  (client: "No customer answer was rendered for this trial."); before, it showed
  the unassessed text. Diagnostics capture and assess in one call, so this is
  visible only mid-execution.
- Non-GTM diagnostics are unchanged and were not examined for the same pattern.
- The limits of the previous addendum stand: only five retained row types
  convert, background executors read before their failure-marking `try`, and the
  display readers have no dedicated case. Counts remain finite controls, not branch
  coverage. Packaging, live conformance, model quality and learner gain are unchanged.

S24 remains unaccepted, unstaged and uncommitted.

## Addendum 2026-10-11 (third session): pre-acceptance demos and architecture refresh

This round ran implementation-plan steps 6 and 7 only. No source, test or fixture
file changed. Receipts are in `C:/swr24-acc-20261011`.

### Demos on the current tree

Neither demo had run since the 2026-10-09 R2 repair, the F1, F3, F4 and F6 repair
or the F2 repair.

- `demos.gtm_operation --out C:/swr24-acc-20261011/demo`: PASS, exit 0; the
  journey test 1 passed with the two existing warnings. Selected `ver-0002`,
  retained `ver-0003`, operation `run-0008`, inherited reprocessing `run-0009`,
  later comparison `experiment-gtm-shift-04-later-1`, replay IDENTICAL.
- `demos.gtm_reviewed`: PASS, exit 0, approval digest
  `8d87c2dc279f31f3206ec389e0f72b34b50e038c59bc764ef60c13489b62d1fa`, 19 material
  files, three document bindings, three offline fixture pins (`reviewed.log`).
- Against the 2026-10-08 R1/R2 demo record
  (`C:/swi24-repairs-20261008-1/demo-run`): `journey.json` has 21 differences, 6
  timestamps or the database hash and 15 `elapsed_ms` values. IDs, selection,
  ledger events and their hashes, the later comparison apart from `elapsed_ms`, and
  the replay report are identical. Both databases were copied to scratch and read.
  Every operation run (`run-0001`, `run-0008`, `run-0009`, `run-0010`) gives the
  same projection text and IDENTICAL replay on both, with zero connection changes;
  the evidence files' hashes are unchanged (`demo-compare.json`).
- The same comparison under the archived pre-2026-10-11 `shiftwork/` preimage
  (`C:/sw24-r13-receipts/preimage-shiftwork`, which carries the R1 projection
  repair) gives identical projections and replays (`demo-compare-r13code.json`).
  The F1 to F6 repairs left healthy output unchanged.
- Healthy projection, `run-0008`: "Synthetic qualification: QUALIFIED. Synthetic
  owner: owner-apac-platform. Synthetic pipeline record prepared for human
  handling. No additional owner, record or handoff is required." No rejection
  label; claims `qualification`, `owner_assignment`, `pipeline_write`. This matches
  the 2026-10-08 description. The starter `run-0001` and the outage `run-0010` carry
  the rejection label, as their assessments require.
- Recorded, not a regression: `run-0009` renders "No additional owner, record or
  handoff is required." three times, once per `NOT_APPLICABLE` task (owner, write,
  handoff, all passing). The preimage renders the same text.
- Workspace manifest before and after both demos: 9,222 files, byte-identical
  (`.git`, the venvs, `.claude`, `.env`, `__pycache__` and `.pytest_cache`
  excluded). The demo's child pytest ran with `PYTHONDONTWRITEBYTECODE=1`.

### Suite and fault applicability

The full suite and the fault inventories were not rerun. Every source and test
file in the workspace is byte-identical to the F2 fault copy `C:/swr24-f2`. The
only differences are this checkpoint and `MISTAKES.md`, written after that run,
and the reviewer probe file present only in the copy (`f2-copy-manifest.json`).
The 2026-10-11 results above (1,399 passed; 73 of 73 S24 and 106 of 106 S23
`FAIL_CAUGHT`) therefore apply to the current source.

### Architecture refresh

Appended as "Refresh 2026-10-11" to
[slice24-architecture-review-2026-10-08.md](slice24-architecture-review-2026-10-08.md):
PASS within the offline scope, no deletion proposed. Three non-blocking items
await the user: untyped readers outside the five converted row types (carried),
the repeated no-action sentence above, and the stale S24 notice in
`docs/SHIFTWORK_PLAN.md`. Six unused imports in `orchestrator.py` predate S24
(present since `76b8467`) and are out of scope.

### Interpreter and document checks

Base uv CPython 3.13.14 with `-B`, `PYTHONPATH=.venv313/Lib/site-packages` and
`PYTHONNOUSERSITE=1` (AGENTS.md section 6). The venv has no `.pth` files,
`shiftwork` imported from the workspace, pytest 9.1.1, pydantic 2.13.5. Scripts
reading the demo databases also put `.` on `PYTHONPATH`. The three edited
documents kept LF line endings (Python byte counts), and `git diff --check` is
clean.

### Open decisions, all the user's

- Another independent review of the F1 to F6 repairs.
- Local commits to protect the work.
- S24 acceptance and publication (S23 precedent: `54f17f1`, focused commits,
  merge, push).
- Architecture refresh items 2, 8 and 11.

S24 remains unaccepted, unstaged and uncommitted.
