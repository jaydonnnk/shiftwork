# S21 independent-review repairs: 2026-10-02

Offline closeout complete, 2026-10-03 Asia/Singapore: all three authorized repairs
are implemented and verified within the limits below. The combined audit confirms
seven clean baselines and 40 intended raw fault assertions, unique anchors,
scanner controls, exact journey IDs and preserved source/evidence bytes.
Stable-source offline tests passed 644 with one existing live-only skip and two
warnings; named API checks passed 24. The user separately authorized focused
commits and publication to main on 2026-10-03, without co-author footers. Shipment
uses this offline evidence. This note qualifies earlier claims without replacing
historical receipts.
One preview server log contains a Windows socket callback reset, recorded below;
the intended browser fault assertion was reached and its browser stderr is empty.

## Authority and checkout

The user explicitly authorized fixing the three findings in
`artifacts/s21-independent-review-20261002/review.md`, with failing-capable proofs.
The reviewed range was `926d269..5039b7b`. At entry, main, HEAD and the existing
`shiftwork/slice-21` branch all resolved to
`5039b7b225b23a6d2cde526d09d474936dfbdcf2`. There were no subsequent commits.
The only tracked modification was the pre-existing orchestration incident in
`MISTAKES.md`. The authorized branch was switched to without creating a commit;
`git merge-base --is-ancestor main HEAD` returned 0.

The initial repair authority excluded commits and pushes. The user's 2026-10-03
publication instruction supersedes those two restrictions only. No install,
credential use, live provider/Sandbox call, fixture/seal change, S22a work or
inherited pre-comparison A/B reload change is part of this publication.

## Repairs and falsification

1. Candidate ownership now uses the last successfully loaded shift identity,
   which survives loading/error clears. The winning refresh resolves its current
   comparison before applying state, rechecks generation after the asynchronous
   comparison read, clears prior-shift candidates and restores current compared
   candidates. Same-shift refresh and reconnect retain frozen candidates.
2. The browser scanner captures and scans serialized DOM at the exercised loading,
   refresh-error, empty, malformed-output, assistance-denial and save-error
   boundaries, as well as initial/final state. Every needle's raw, JSON-escaped
   and slash-form control is injected into that captured serialized surface.
   This repairs test coverage; the review did not observe a production secret leak.
3. A dirty-only `beforeunload` handler asks the browser to warn on page reload or
   departure. Native mouse input and text insertion establish Chrome user
   activation. The proof observes an actual `beforeunload` dialog with a browser
   handler, dismisses it and checks retained dirty text. Clean reload after native
   activation, successful save and discard must navigate without a dialog.
   This is warning protection only, with no browser-local draft persistence.

The new reload and candidate-race checks both failed against the reviewed client
before production edits, exit 1, at their intended assertions. The race delayed
only the opening board GET by 400 ms. After the continuous selected journey,
`bookshop-shift-03` froze `ver-0004`; shift 4 incorrectly retained it with no
latest save, including after ordinary refresh. The repaired targeted baseline
clears both candidates, preserving same-shift refresh and reconnect.

Three permanent served-source faults target these guards independently:
`candidateRace`, `transientErrorLeak` and `unloadWarning`. The targeted round
returned three clean baselines PASS and all three mutations CAUGHT at the named
assertion, exit 0. The transient sentinel is rejected specifically at
`Client DOM contains private material (refresh-error)` before recovery.
Fault classification alone is not proof: raw child output, exit codes, captured
DOM/scanner results and failure screenshots are retained for inspection.

## Receipts and verification

All new outputs are under `artifacts/s21-review-fixes-20261002/`:

- `before.json`: SHA-256 snapshot of 1,343 pre-existing tracked/artifact files.
- `prechange/`: red reload and overlapping-transition regressions against the
  reviewed production client; original stdout/stderr, exits and screenshots.
- `targeted/`: three matching clean baselines and three intended caught faults.
- `final-matrix/`: final client/source digests and per-row browser/preview raw
  stdout/stderr, exits, DOM/scanner receipts, reports and screenshots.
- `*-result.json`, `*-stdout.txt`, `*-stderr.txt`: command/exit/time and raw bytes
  saved by the no-overwrite `receipt.py` wrapper.

Baseline named API checks: **24 passed, 2 warnings in 7.11s**, exit 0. Final
named API checks: **24 passed, 2 warnings in 9.91s**, exit 0.
The first post-repair offline suite returned **644 passed, 1 skipped, 2 warnings
in 355.62s**, exit 0. The final stable-source suite after the comparison application
ordering was tightened returned **644 passed, 1 skipped, 2 warnings in 407.66s**,
exit 0. The complete browser runner reported **47/47 as expected**: seven clean
baselines and 40 faults (the original 37 plus three new faults), exit 0. This
classification is now confirmed by the combined per-row raw audit: every fault
reached its intended assertion with a unique production anchor and empty browser
stderr. Classifier exit 0 alone was not used as proof.

The standard selected journey still reports `ver-0002`, retained `ver-0003`,
`run-0010`, `sel-0002`, event 5 and `bookshop-shift-03`, with TRUSTED_LOCAL
execution and 40 native navigation activations. The separate race adds a freeze
in shift 3 and overlapping transition to shift 4. It does not change the standard
journey's identities.

The render runner now accepts a fresh `--artifact-dir` and optional `--only`
row list. It refuses a reused root before launching a preview. A deliberate
reuse of `targeted/` returned EEXIST, exit 1, without overwriting its receipts.
Browser directories also refuse reuse. Raw child output is buffered as bytes,
preserving CRLF, UTF-8 and terminal spaces.

The final combined audit returned exit 0 and created `audit.json`. It inspected
all 40 raw intended fault assertions, all seven baseline exits and reports, the
two pre-change intended failures, unique anchors and exact journey identities.
The refresh-error pair has 4,406 needles with successful serialized detection
controls in both rows: the clean DOM is clean and the injected DOM is rejected
before recovery. The captured injected serialized DOM contains the sentinel.
All 1,337 pre-existing files outside the six edited paths retain their SHA-256
bytes, no file is missing, and all three final matrix source digests still match.
Original `MISTAKES.md` bytes, including the pre-existing orchestration incident,
remain the exact prefix; only repair and closeout-helper incident entries follow.

The supplemental closeout check verifies all 50 captured clean scanner snapshots
across the seven baselines, the three targeted matching baseline/fault pairs and
the final raw assertion failures. The candidate mutation shows stale `ver-0004`;
the reload mutation shows the missing-dialog assertion, `0 !== 1`. Failure
screenshots remain. All 1,409 repair artifact files pinned in `closeout-entry.json`
retain their bytes, including the prior handoff, raw receipts and screenshots.
The historical bodies of `00-status.md` and `SHIFTWORK_PLAN.md` match HEAD after
its checkout CRLF conversion; their current CRLF and terminal spaces are retained.

Final tracked `git diff --check`, the explicit untracked-document check, Git
scope and staged-state checks pass. Added content has no matches to the fixed
high-confidence credential patterns used by the helper; this is not a general
secret-detection guarantee. The diff contains the three scoped source/harness
repairs, completion records and appended mistake entries. Nothing is staged.
The desktop candidate-reset and 390 px comparison captures were re-inspected.
No repair preview listener remains on 18821/18822. Port 8143 was untouched;
no listener was observed there during closeout. No server kill was needed.
Source and test files were unchanged in this closeout, so the passing suites and
browser matrix were reused after digest/receipt inspection, without rerunning them.

Closeout-helper receipts remain separate. `closeout-preflight` failed because its
new-file check incorrectly required exit 0: the raw Git no-index command returned
1 for differing files with no whitespace diagnostics. This helper error is logged
in `MISTAKES.md`; the check now requires exit 0 or 1, no whitespace output and no
unexpected stderr. `closeout-preflight-2` then surfaced the actual server diagnostic
below. It was inspected and preserved as a limit, not erased or called clean.
`closeout-preflight-3` passed; the final check after these documentation edits is
recorded in `closeout-final-result.json`, stdout and stderr. All labels are fresh.
The prior `handoff.md` remains unchanged as a historical pending-work snapshot.

Final matrix command:

```text
node tests/client/render_faults.mjs --port 18822 --artifact-dir artifacts/s21-review-fixes-20261002/final-matrix
```

Final full suite command:

```text
.venv313/Scripts/python.exe -m pytest tests --ignore=tests/packaging -q
```

Combined audit command (exit 0):

```text
.venv313/Scripts/python.exe artifacts/s21-review-fixes-20261002/receipt.py final-audit node artifacts/s21-review-fixes-20261002/audit.mjs
```

Final closeout check:

```text
.venv313/Scripts/python.exe artifacts/s21-review-fixes-20261002/receipt.py closeout-final .venv313/Scripts/python.exe artifacts/s21-review-fixes-20261002/closeout_checks.py final
```

## Current claim corrections and limits

Exactly one of the 47 preview server logs, `invalidatedPolling/preview-stderr.txt`,
contains `ConnectionResetError: [WinError 10054]` in the Windows asyncio
`_ProactorBasePipeTransport._call_connection_lost` callback. Its preserved digest is
`47467c7e7577e135b5d73b7a2eafe9d6a76f2728f95eaaae16a8faca0d2ac652`.
The row's browser stdout reached the intended terminal-polling assertion and its
browser stderr is empty; the matching blocked baseline passed. The server log
has no timestamp proving when the callback fired, so its timing/cause remain
unproven. There is no claim that all preview server stderr is clean, and this
diagnostic was not replaced by a rerun.

The earlier S21 candidate-reset proof covered sequential transitions; overlapping
refresh reset was defective until this repair. Scanner controls proved detection
capability, while the earlier browser run missed transient error DOM. Unsaved
text survived in-app Refresh and a save 503; browser reload previously discarded
it silently and now warns after user activation. Accepting departure still loses
unsaved text. Browser prompts may be suppressed without user activation or during
forced termination; this proof is desktop Chrome, not every browser/mobile lifecycle.
The overlap proof delays the opening board GET. The optional cached-comparison
reread's generation check was inspected but has no separate delayed-read mutation.
DOM scan coverage is limited to the named exercised snapshots, not every possible
browser error path.

The old evidence note's unqualified diff-check-pass sentence concerned source and
documentation. `git diff --check 926d269..5039b7b` reported 95 whitespace lines in
three byte-preserved raw receipts; excluding the raw S21 transcripts passed.
No historical transcript is normalized or replaced here.

Packaging remains excluded because it installs dependencies. The live Sandbox
skip and the existing Starlette/httpx and AnyIO warnings remain. These proofs are
offline browser/trusted-local evidence. Authorized publication does not establish
live model quality, learning, transfer or hostile-code isolation. Gate 3 obligations
39, 45 and 46 remain partial beyond Bellwether's exercised surfaces.

The scoped architect-reviewer scan found all literal client DOM IDs in the shell
and no unreferenced named client function. The existing room, public APIs,
immutable versions, explicit selection and controller evidence boundaries remain
consistent with ADRs 0001, 0003, 0005 and 0006. The closeout scan reconfirmed
literal DOM IDs and named-function references against the unchanged final source.
No deletion, new architecture layer or ADR change is required. Historical
fixtures, evidence and gate documents stay. Offline closeout is complete.
Publication is separately authorized on the existing `shiftwork/slice-21`.

## Repository receipt package: 2026-10-03

The publication package is `slice21-review-fixes-2026-10-03/` beside this note.
Its `receipt-manifest.json` pins the copied API, offline suite, matrix, combined
audit, closeout and preview-reset receipts by size and SHA-256. Git attributes
preserve every file in that package byte-for-byte, including native CRLF and
terminal spaces. The fixed raw whitespace is intentional; strict source and
document checks exclude this package, and every diagnostic header is confined
to its byte-preserved transcripts.

`raw-browser-audit.json` losslessly bundles stdout/stderr from 47 final matrix
rows, six targeted rows and two pre-change regressions using base64 with sizes
and hashes. It also retains the baseline reports, regression state, scanner
receipts and clean/injected refresh-error DOM pair. Decoding all 55 rows and the
DOM pair reproduces their original hashes. The published package does not contain
local screenshots, helper scripts or the full starting snapshots; those remain
under the ignored artifacts root. The published final-matrix source digests are
the exercised working-file bytes, not a claim that Git normalized source blobs
have the same CRLF representation.

The publication helper first parsed a transcript source-location line as a Git
whitespace diagnostic, then used a total commit file count for a narrower receipt
folder. Both failed checks are logged in MISTAKES. The browser evidence commit
was created before the first helper finished, but no push followed. The corrected
check subsequently verified all four committed package blobs and all 55 decoded
raw rows before further commits. These helper failures are not product test
failures and do not erase the earlier passing offline proof.

Two commit attempts, the initial client commit and the completion-record commit,
failed to write Git's index without advancing HEAD. No index lock or running Git
process was observed afterward; both retries succeeded. Their cause remains
unproven. Publication records actual commit/push results separately from the
preserved closeout receipts at the old HEAD.

## Publication and main integration: 2026-10-03

Seven focused core commits (`f6df2cb..aee1fe5`) were pushed on `shiftwork/slice-21`.
Local main was fast-forwarded with an ancestor check and a compare-and-swap against
its original `5039b7b` ref, preserving the dirty worktree, then pushed. Both remote
heads were verified at `aee1fe5246f8114ccdf8133a25f20d1e7fe72e99` before this
publication record; this record follows the core commits. There are no co-author
footers. The original six-line MISTAKES orchestration incident remains unstaged
and outside the published changes.

Publication checks verify all 15 package files against their Git blobs and all
55 decoded browser output pairs against the local originals. The raw transcript
range retains 155 whitespace diagnostics from its original CRLF/terminal spaces;
all headers are confined to this receipt package. The strict source/document
check passes. All 1,336 old files outside the seven authorized edited paths and
all 1,409 pinned repair artifacts remain byte-identical. Source digests still
match the exercised final matrix, so no passing suite was rerun for publication.
The user's publication instruction authorizes shipment on that offline evidence;
it creates no live, learning, transfer, install, fixture/seal or S22a authority.
