**Follow-up offline corrections verified, 2026-10-25.** The user subsequently
authorized fixing the refresh loop and lamp. Those corrections and the count
clarification are in [the current polling record](slice46-polling-correction-2026-10-25.md).
The unchanged-polling statements below describe this earlier summary-only phase.
Current regression is 1,761 Python passes and 340 Node passes; S46 remains
INCOMPLETE and UNACCEPTED. Both live allowances stay closed.

# S46 offline UI correction verified

The user authorized this continuation through the pasted handoff on 2026-10-25.
S46 remains INCOMPLETE and UNACCEPTED. Both live actions and all remainders stay
closed. Work is local and uncommitted on `shiftwork/slice-46` at
`087585ff690194e6fde5d67be9827d732474879e`; the inherited index is empty.

## Plan and boundaries

1. Reproduce the misleading proposal request summary with a failing behavioral
   test of the actual client renderer. Reuse the diagnostic projection only when
   its experiment, shift, run and proposal identities match the loaded request.
2. Correct the client summary and refresh its asset provenance. Preserve saved
   version summaries, executor behavior, grades and original evidence bytes.
3. Run focused checks, separate identity fault proofs and relevant full suites.
   Use the installed macOS Python and Node. Exclude the installation test and
   retain the live-only skip. No installation or live execution is authorized.
4. Inspect the actual copied checkpoints at desktop/mobile 100% and native 200%.
   Diagnose repeated refresh without changing stored queued rows. Distinguish
   the unreconciled snapshot from normal startup and report any remaining limits.
5. Update S46 records with reconciled evidence and verified correction results.
   Keep private receipts in `/tmp/shiftwork-s46-ui-20261025/`.

Original `live.db`, `terminal.db` and intermediate checkpoints under
`/tmp/shiftwork-s46-20261025/proposed-live-v2/` must never receive normal app
startup. Existing review servers use read-only copied databases, disable startup
reconciliation and reject mutation requests. Do not execute generated service
code on the host. Do not accept S46, select, operate, publish, merge or deploy.

## Baseline

Fresh verification matched all 2,006 preflight file hashes, the recorded HEAD
and empty index. The seven focused Node checks pass before the correction.
Receipts: `resumed-baseline-node.txt` and the inherited `baseline.json` in the
private UI receipt directory. The newer read-only reconciliation is
`/tmp/shiftwork-s46-readonly-20261025/review.md`.

## Correction and failing proof

`renderFailedRequest` used the nullable saved-version ID and the legacy output
projection for run-0011. The legacy API intentionally leaves `customer_answer`
unset for this diagnostic, while the diagnostic trial retains the rendered answer
and deterministic task assessments. No API or executor change was needed.

The summary now says `executed coach proposal assist-bookshop-shift-01-1`. It
uses the diagnostic customer text and request-specific task assessments only if
the diagnostic kind, experiment, shift, run and proposal match. Saved-version
summaries retain their existing output/check behavior. An unrelated or absent
report produces an explicit missing-report message. No new grade is computed.

The new behavioral renderer tests fail against the original summary, including
the literal `executed null`, absent answer and incomplete-evidence messages.
They pass after the correction. Tests also cover eight independent identity
conditions, failed/missing task evidence, another request's tasks, the viewed
report and the latest report, and unchanged saved-version output/check behavior.

Twelve separate edits to a disposable source copy each trigger their intended
assertion: eight identity conditions, the proposal label, retained customer text,
task verdict and request-specific task selection. Clean and restored controls
pass, and the working source is unchanged by the fault runner. These are the
new UI proofs, not a rerun or addition to the earlier 22 implementation checks.

## Fresh regression

- Focused Node: 12 pass, zero fail. The earlier resumed baseline had seven.
- Full Node: 317 pass, zero fail or skip.
- Python: 1,755 pass, one live-only skip and seven deselections in the main run;
  six omitted offline environment cases then pass with only the installation
  function deselected. Combined coverage is 1,761 distinct passing cases, one
  live-only skip and one excluded installation case. Two existing deprecation
  warnings remain. No installation was attempted.
- `node --check shiftwork/client/app.js` and `git diff --check` pass.

Commands, from the S46 checkout, used the installed Python and Node:

```sh
/Users/jayd0/.local/bin/node --test tests/client/proposal.test.mjs tests/client/evidence.test.mjs tests/client/diagnostic_rates.test.mjs
SHIFTWORK_PYTHON=/Users/jayd0/Desktop/shiftwork/.venv/bin/python /Users/jayd0/.local/bin/node --test tests/client/*.test.mjs
/Users/jayd0/Desktop/shiftwork/.venv/bin/python -m pytest -q -k 'not test_clean_env_install_and_run'
/Users/jayd0/Desktop/shiftwork/.venv/bin/python -m pytest -q tests/packaging/test_clean_env_install_and_run.py --deselect=tests/packaging/test_clean_env_install_and_run.py::test_clean_env_install_and_run
/Users/jayd0/Desktop/shiftwork/.venv/bin/python /tmp/shiftwork-s46-ui-20261025/summary_faults.py
```

The first pytest filter matched the module as well as the installation function.
Its seven deselections were checked and the six offline cases were restored to
coverage by the second command. Future runs should use the exact installation
node ID for deselection. Receipts: `summary-red.txt`, `summary-green.txt`,
`summary-faults.json`, `full-node.txt`, `full-python.txt` and
`python-environment-supplement.txt` in the private UI receipt directory.

## Actual browser review

The existing review servers still serve byte-identical, read-only checkpoint
copies with startup reconciliation disabled and HTTP mutations refused:

- Generated: `http://127.0.0.1:54134/?board=bookshop#investigate`.
- Tested: `http://127.0.0.1:54135/?board=bookshop#investigate`.
- Accepted and B saved: `http://127.0.0.1:54136/?board=bookshop#investigate`.
- Stopped: `http://127.0.0.1:54137/?board=bookshop#compare`.

Ten checkpoint/viewport cells pass. Generated and accepted snapshots were
inspected at 1440x1000 and 100%. Tested and terminal snapshots were inspected at
1440x1000 and 390x844 at 100% and native 200%. The browser compares the tested
summary and detailed report with the actual retained diagnostic JSON. There is
no document-width overflow or runtime exception, and no mutation request is sent.
Both visible choice controls remain disabled in the terminal snapshot.

The private runner adapts the existing `workplace_browser.mjs` harness only for
its absolute environment import and S46 receipt root. Chrome's profile page-zoom
preference establishes 200%; the viewport override retains native zoom with
`mobile:false`. At the 390x844 target, the observed viewport is 195x422 CSS pixels,
DPR 2, pinch scale 1 and CSS body zoom 1. At 1440x1000 it is 720x500 CSS pixels.
This is desktop Chrome at a mobile-sized viewport, not a physical-phone test.
The browser uses a private disposable profile and leaves personal Chrome zoom
unchanged. Screenshots were inspected, including scrolled task checks and both
visible disabled choices at the narrow native-200% target.

The first browser setup queried an absent body; its failure is retained and
excluded. An initial scroll check selected a hidden modal button and accepted a
zero-height rectangle. That observation is excluded; the corrected check requires
positive size on the visible Choose controls. Both verification defects are
logged in MISTAKES.md. No product change was made to satisfy either runner.

Private receipts: `browser-review.txt`, `browser/results.json`,
`narrow-scroll/results.json` and their screenshots. These are separate actual
checkpoints. They do not prove a smooth generation/run/accept/save/compare browser
journey, assistive-technology behavior, learner gain or a causal repair.

## Repeated refresh investigation

The stopped snapshot's latest run is run-0029, still QUEUED, while its parent
comparison is FAILED. During a 4.2-second observation, two loading episodes clear
the comparison and then reload it. No mutation request is sent. The source chain
is `refresh` calling `clearData` before its reads, then polling the nonterminal
loaded run after one second. `lampStates` in `workplace-story.js` also treats a
reserved child trial as Running even when its parent comparison is FAILED.

Receipt: `refresh/observations.json`. Polling and lamps are unchanged because
this continuation authorized investigation of that behavior. All twelve queued
rows retain their original bytes and have no outputs or observations. Normal app
startup calls `reconcile_interrupted`, which changes nonterminal rows; it was
deliberately disabled here. This review proves the unreconciled snapshot behavior
and does not establish normal-startup behavior or rule out the same state in a
still-running process. No normal app was opened on the original databases.

## Reconciled live evidence and stop boundary

Run-0017 is B, pair 1, public repetition 3. Request 2 hit a provider deadline at
20,004 ms. The Sandbox reports SUCCESS and both captures pass checkpoint readback.
The adapter's gateway-failure branch supplies SANDBOX_TERMINATED. Run-0015's
public repetition completed; its later CAPTURE_TRUNCATED records the skipped
protected phase after run-0017 failed. Twelve later queued runs have no execution.
The retained sequence supports stopping at the first actual execution failure.
The provider's underlying latency cause remains unknown.

The earlier private scan passed the five named export files, with all 30 injected
serialized credential controls detected. No new public JSON was copied or
published. The original private reconciliation and scan receipts remain in
`/tmp/shiftwork-s46-readonly-20261025/`.

Neither candidate is eligible. Each has zero passing public batches of nine
planned and three retained. Six missing batches each are missing evidence, not
measured failures. No source tuning, new call, selection or operation occurred.
Second-action usage stays one Super call, 14 Nano calls and eight Sandbox
operations, reserving US$0.04171776 inference. Both actions reserve US$0.05468160;
billing is unknown. Both allowances and all remainders stay closed.

The coach's `or []` precedes a caller already using `plan or []`; no customer-facing
causal repair is established. Generated service code was never run on the host.
S46 is still INCOMPLETE and UNACCEPTED. This correction does not authorize retry,
resume, selection, operation, publication, merge, deployment or a later slice.

## Final scope and preservation

The correction changes eight pre-existing files: `app.js`, its provenance entry,
`tests/client/proposal.test.mjs`, MISTAKES.md, the supporting brief, status,
continuation and second-result records. This document is the only new repository
file in this continuation. The 1,998 other baseline files are byte-identical.
All 106 protected-material and 66 older-evidence hashes match. Both original S46
actions, all original databases, intermediate checkpoints and action receipts are
unchanged. The twelve queued runs still have no outputs or observations.

Fresh read-only reconciliation reproduces the deadline, skipped protected capture,
usage counts and unchanged operational ledger/selections. The provenance hash
matches current `app.js`; branch, HEAD and empty index are unchanged.
`git diff --check` passes. Receipt: `final-preservation.json`; rerunnable audit:
`preservation.py`, both in the private UI receipt directory.

Targeted final review found no new production helper, module, import or dependency;
the correction stays in the existing renderer. No file is proposed for deletion.
The known polling/lamp defect and incomplete live/browser journey remain above.
This is not the final acceptance or post-slice cleanup review of completed S46.
The pre-existing read-only review servers remain available for the operator.
