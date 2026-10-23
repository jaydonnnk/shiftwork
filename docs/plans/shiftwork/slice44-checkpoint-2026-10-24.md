# S44 verified result, pending acceptance

S44 ran one live diagnostic experiment with ten frozen repetitions of
`bellwether-collection-001`. Both required tasks were missing in five runs.
All five failures were empty replies with `finish_reason=length`, 1,024 reported
output tokens and `SCHEMA_INVALID`. All five valid plans named collection and
alternative, and their service outputs passed the independent required checks.
This demonstrates an output-budget incident. It does not establish semantic task
omission or a general Nano failure rate.

## Authority and Git

On 2026-10-24 the user said "Yes it has my go ahead", then:
"GO ahead and the spend ceiling is roughly 5 bucks i have 27 bucks in token factory call count is based on call spending so go ahead and start s44 for reals".
The latest instruction delegates the count to spending. The plan fixed ten calls
and ten Sandbox operations for the pinned mission's one public request, with no
retries and a $5 maximum inference allowance. The old six-request estimate did
not describe the pinned workload.

The user located credentials with "they are in .env.local". A local launcher
loaded only relevant assignments into the controller environment, without
printing values, installing dotenv or executing the file as shell code. The
AI-project format and all six Sandbox permissions passed. The controller still
reads credentials through its environment. Other live actions were disabled.

Branch: `shiftwork/slice-44`, created from clean main at `1c2a6a2` after verifying
origin/main at the same commit. No commit, merge or push is authorized. S45 has
not started. Mission v2 and starter hashes still match the operator-reviewed
pins; no protected material, dependency or lockfile changed.

## Retained live evidence

- Experiment: `experiment-bookshop-shift-01-d1`, `DIAGNOSTIC`, `FINALIZED`.
- Configured and reported model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`.
- Frozen settings: temperature 0, maximum output 1,024 tokens, one call per request.
- Ten `ISOLATED_LIVE` runs, ten captures and ten retained provider replies.
- Thirty task assessments, including the optional price task.
- Misses: runs 0001, 0003, 0004, 0005 and 0009. Both collection and alternative
  have `REQUIRED_TASK_MISSING` and zero useful request completions in those runs.
- Runs 0002, 0006, 0007, 0008 and 0010 have valid plans and complete the request.
- Ten provider calls and ten Sandbox operations. No retry, protected draw or
  ledger event. No version became eligible or selected.
- Reported usage: 2,620 input tokens and 8,932 output tokens.
- Token-cost projection: $0.00230088 at the existing project rates of $0.06 and
  $0.24 per million input and output tokens. Those are projection rates, not a
  verified current vendor quote. Actual provider billing and Sandbox cost remain
  unknown. The conservative reserved-token projection for ten calls was $0.0221184.
- The stop rule did not trigger because five runs missed required tasks. No new
  request shape or alternate defect was introduced.

The raw package is gitignored at
`docs/plans/shiftwork/evidence/slice44-live-recording-2026-10-24.json`.
Its digest is `f2e1b32f5046b87d37ea89632f9984820124907e724eaf1e917442d8853714b7`.
The source database is `/tmp/shiftwork-s44-live/live.db`. The export preserves
frozen mission, artifact and public-state bytes, all outputs, original log refs,
provider responses, plans, parse failures and assessments. The checksum binds
package bytes; it is not an independent provider-authenticity signature.

## Offline replay and room

The same package was replayed in a fresh recorded controller with no provider
credentials. Ten output, public assessment and observation payload sets match
the source exactly, including raw provider payloads and log bytes. The miss
summary is identical. Replay observation timestamps are new; the original
timestamps remain in the retained source package. Every replayed run and context
say `RECORDED_INSPECTION`. Eligibility stays false; no ledger or protected draw
is created. The selected starter remains separate from the inspected version.

Local review URL: <http://127.0.0.1:8446/?board=bookshop#investigate>.
The database is `/tmp/shiftwork-s44-offline/replay.db`. This controller uses
`SHIFTWORK_DIAGNOSTIC_RECORDING` to locate the retained package. A stock offline
build is not regenerated, and the raw receipt is not published or committed.

The actual replayed room passes in installed Chrome at CSS viewports 1280x800
and 390x844, with no horizontal page overflow, no JavaScript exception and no
evidence-binding conflict. This is not physical-device or audible-AT proof. It guides
the learner to explain the cause. No learner investigation entry was fabricated.
Screenshots and equality proof are retained under `/tmp/shiftwork-s44-offline/`.
The live controller at port 8445 and the fixture preview at port 8444 are stopped.
Only the recorded review controller at port 8446 remains available.

## Verification and cleanup

- Isolated `1c2a6a2` baseline: 1,513 passed, one skipped, two known failures.
- The full S44 suite retains only `test_conformance_suite_recorded_local[port_dead]`
  and `test_clean_env_install_and_run` with its baseline native-panel assertion.
  The final rerun has 1,544 passed, one skipped and those two failures.
- S43 mutation harness: 27 mutations killed, zero survivors.
- S44 mutation harness: 29 named faults, including the actual trial-version
  binding. Each requires an assertion failure, byte-identical restoration and a
  passing clean control. Crashes and timeouts do not count.
- Node unit checks: 286 passed. Two served UI faults independently corrupt the
  shown rate and source fallback; each fails its named assertion and passes clean.
- The first overlapping baseline, rejected mutation checks, driver failures and
  asset-provenance regression remain recorded in MISTAKES.md and are not counted
  as passing evidence. The live batch was never repeated to repair its driver.
- Architect cleanup found no unused added module or fixture. CLI proof and
  demonstration files are deliberate entry points. The edited HTML and
  JavaScript retain matching digests in the approved source-provenance inventory;
  styles.css is unchanged. Historical and future fixtures remain in place.
- Final diff and protected-material checks are recorded in 00-status. No stale
  scaffold or temporary receipt was added to tracked source.

Proof entry points are `.venv/bin/python -m pytest -q`,
`.venv/bin/python tests/s43_mutation_proofs.py`,
`.venv/bin/python tests/s44_mutation_proofs.py` and
`node --test tests/client/*.test.mjs`. Rendering controls are
`tests/client/s44_preview.py` and `tests/client/s44_browser.mjs`.
`tests/client/s44_room_run.mjs` provides both demonstration and read-only
inspection modes. The live allowance above is already consumed; its live mode
does not authorize a new batch.

The bounded working result is ready for the user's acceptance decision. No
learning gain, broad model quality, real customer outcome or deployment claim
follows from these ten fictional requests.

## Wording fix, 2026-10-24

Changed checks, old text kept here:
- `tests/client/s44_browser.mjs` fault needle was `'${row.task_id} task missed in ${misses} of ${count} runs'`, replacement `'${row.task_id} task missed in ${misses + 1} of ${count} runs'`, and the rendered assertion was `text.includes('alternative task missed in 1 of 2 runs')`.
- `tests/client/diagnostic_rates.test.mjs` expected `['request-1: alternative task missed in 1 of 2 runs']`.
- `shiftwork/client/app.js` incident text was "Observed incident: investigate a retained missed task."
The rendering fixture in `tests/client/s44_preview.py` now carries the plan parsed from its own operator-authored reply, so its line attributes the omission; it is still labelled as no model call.
