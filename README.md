# Shiftwork

1. **Read the failure:** [open Shiftwork](https://shiftwork.onrender.com), choose Bellwether Books, open a shift, and select **Guided first run**.
2. **Explain it:** inspect the retained evidence, then write your cause and a test that could prove your explanation wrong.
3. **Compare repairs:** edit and save two repairs, then test them under the same requirements and conditions. Fresh hosted runs consume Token Factory credits.
4. **Choose:** explicitly select an eligible, exact tested version. A newer save does not replace that selection.
5. **Next shift:** operate the selection, close the shift, and inspect what the next shift inherits. Use **Technical details** to reveal the underlying IDs and evidence codes.

## Model, Sandbox and Token Factory

Shiftwork is a practice environment for diagnosing and maintaining an AI service.
Bellwether Books, Stonebridge, and Northline are fictional workplaces. Their
sales, bookings, ownership, and incidents are synthetic.

The service model is `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, served through
Nebius Token Factory. Under the live executor, Bellwether's current starter
depends on Nemotron's structured task plan to decide which public-record tools
to use. Missing or invalid model output can fail the service checks. The
controller owns evaluation, eligibility, selection, and the operating ledger.
Optional diagnostic help uses a separate call allowance.

Token Factory supplies inference and Sandboxes for the isolated execution path.
The controller freezes source, requests, and permissions, executes a bounded run,
and retains outputs and provider observations. Recorded inspections replay
captured bytes. Trusted-local runs execute byte-pinned operator fixtures.
Neither mode proves fresh inference or safe arbitrary local code execution.
Fresh learner-code execution uses the separately authorized isolated route.
See [the evidence labels and limits](#evidence-modes-and-limits).

**Track:** Best Apps and Agents, confirmed by Jaydon on 2026-10-15.
**License:** [MIT](LICENSE). Dependencies retain their own licenses.

## Hosted practice demo

[Open the shared practice demo](https://shiftwork.onrender.com).
S48's published runtime is `37f1394`. Hosted checks match all 18 client files,
show the guided path at three viewport sizes, and record one completed live
smoke diagnostic. After 16 minutes without owned polling, a wake request took
32.54 seconds and the database reset. Public visitor traffic was uncontrolled.
The smoke is closed with no retry. The user accepted S48 on 2026-10-26.
See [the release evidence and limits](docs/plans/shiftwork/slice48-release-checkpoint-2026-10-26.md#hosted-verification-and-acceptance-boundary).

The hosted database is shared, has no private learner accounts, and can change
when another visitor acts. The recorded free-hosting behavior includes sleep,
a wake delay, and a fresh database after sleep, restart, or redeploy.
Use the local build to retain your own history. Free hosting is not an
availability guarantee. See [the retained S28 hosted evidence](docs/plans/shiftwork/slice28-hosted-evidence-2026-10-19.md).

[Download the S48 runtime source](https://codeload.github.com/jaydonnnk/shiftwork/zip/37f13945a0c073d9b3a31935bd170d09483d5b1e)
to run the guided build locally. [The public repository](https://github.com/jaydonnnk/shiftwork)
contains current source and subsequent release documentation. See [the moved slice history](docs/README_HISTORY.md) for older
measurements and [S47 publication](docs/plans/shiftwork/workplace-3d/s47-publication-2026-10-25.md)
for the accepted local source proof.

## Start locally

Use Python 3.12 or 3.13. Retained packaging evidence used macOS and Python 3.13.
The current [S48 package result](docs/plans/shiftwork/slice48-release-checkpoint-2026-10-26.md#resumed-offline-result)
passes a fresh isolated clean installation and all three offline browser journeys.
All 371 product, test and configuration files match that tested package.
Final documentation was checked separately. The package is offline evidence;
the hosted smoke is a separate single-call result. Broader OS compatibility
remains unverified.
No Node, browser automation library, Docker, API key or GPU is needed to serve
the app or run the offline Python demonstrations.

From the extracted source directory, create an environment with an installed
supported Python, then install **only the pinned lockfile**:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install --no-deps -r requirements.lock
```

This install needs network access. On Windows use `py -3.13 -m venv .venv` and
`.venv\Scripts\python.exe` in place of `.venv/bin/python`. These Windows commands
are instructions, not a fresh S27 Windows test result. On macOS, the venv CLI
uses symlinks; copying this machine's managed interpreter breaks library lookup.

Start the persistent local controller with a new database path:

```sh
SHIFTWORK_EXECUTOR_ADAPTER=recorded SHIFTWORK_DB_PATH=./practice.db \
  .venv/bin/python -m uvicorn shiftwork.app:create_app --factory \
  --host 127.0.0.1 --port 8009
```

Open `http://127.0.0.1:8009`. Choose a workplace and open a shift. Stop the server
with Ctrl+C; restarting with the same database retains history. Use a different
new database filename to start over. Keep this persistent local controller
on loopback. The hosted practice demo above uses an ephemeral shared database. On Windows set the two environment variables in the
shell before running the same uvicorn arguments.

For a disposable Bellwether preview with labelled recorded help:

```sh
SHIFTWORK_EXECUTOR_ADAPTER=recorded \
  .venv/bin/python -m demos.client --port 8009 --recorded-assist
```

Use another free port if 8009 is occupied. This preview is deleted when it stops.
It is not the persistent database above.

## Reproduce the offline pivot

The existing inheritance walkthrough performs the full Bellwether offline loop:
inspect the starter, record a cause and falsifier, freeze two pinned repairs,
run six comparison slots, explicitly choose A, inherit that exact choice,
operate it under a **staged** outage, and test the retained alternative without
rewriting the prior history.

```sh
SHIFTWORK_EXECUTOR_ADAPTER=recorded \
  .venv/bin/python -m demos.final_pivot --stage inheritance
```

Expect `PASS_OFFLINE_POLICY`, six `COMPLETE` later-condition slots and
`prior_bytes_identical: true`. The initial source is recorded; comparison and
operation execute trusted local fixtures. The outage is a disposable scenario
derivation, not a newly reviewed fixture. The script's operator-authored cause,
repairs and choice are demonstrations, not evidence of a human learning outcome.

GTM's separate reviewed offline journey includes exact choice, operation,
restart, inherited reprocessing, later comparison and captured-input replay:

```sh
.venv/bin/python -m demos.gtm_operation --out /tmp/shiftwork-gtm-demo
```

The output directory must not exist. Expect `PRODUCTION_REVIEWED_TRUSTED_LOCAL`
and `replay: IDENTICAL`. Northline's separate test-controlled journey is:

```sh
.venv/bin/python -m pytest \
  tests/orchestrator/test_fde_deployment.py::test_fde_later_alternative_diagnostic_preserves_pilot_and_handover -q
```

Northline's offline repair candidates are test-only fixtures admitted inside
that test process. They are not production-approved arbitrary local execution.
These three offline journeys are separate, not one live end-to-end chain.

## Packaging and regression checks

These commands have different side effects. The clean-environment test installs
locked dependencies and needs network access. Authorize that work separately.
It extracts an isolated source copy and reports `OFFLINE_SKIP` for live inference.

```sh
.venv/bin/python -m pytest tests/packaging/test_clean_env_install_and_run.py -q
.venv/bin/python -m pytest tests -q \
  --deselect=tests/packaging/test_clean_env_install_and_run.py::test_clean_env_install_and_run
```

The existing `verify_three_browser_journeys(source, python, out)` helper in
`tests/packaging/test_clean_env_install_and_run.py` also accepts an existing
interpreter without installation. It exercises all three offline journeys,
actual rooms, and Northline's graphics-failure workbench with external assets
blocked. This is source-delivery evidence, not a clean installation or live run.
Browser checks need existing Node and Chrome installations. The environment
helper accepts `SHIFTWORK_PYTHON` and `CHROME_PATH`.

Current release results and exclusions are in
[S48 release proof](docs/plans/shiftwork/slice48-release-checkpoint-2026-10-26.md).
[S47 final proof](docs/plans/shiftwork/workplace-3d/s47-final-offline-2026-10-25.md)
retains the earlier local presentation evidence.
Dated suite counts and deferred device/accessibility checks remain in
[the evidence history](docs/README_HISTORY.md). Do not treat older failures or
passing counts as a fresh test of a different revision.

## Evidence modes and limits

| Label | Evidence |
| --- | --- |
| `RECORDED_INSPECTION` | Replays captured response bytes. No fresh inference. |
| `TRUSTED_LOCAL` | Executes byte-pinned operator fixtures. No arbitrary learner-code isolation claim. |
| `ISOLATED_LIVE` | Executes a separately authorized isolated run and retains observations. No general model-quality claim. |

The controller keeps credentials, protected checks, and selection decisions.
Source distributions include controller fixtures for reproduction. They do not
prevent inspection by someone who owns the controller filesystem.

S44's retained ten-run incident concerns output-budget failures, not a general
Nano failure rate. S45's recorded comparison and selected operation are bounded
live evidence. S48 verifies the guided presentation on the host through GET-only checks.
Read [S44's observations](docs/plans/shiftwork/slice44-checkpoint-2026-10-24.md),
[S45 publication](docs/plans/shiftwork/slice45-publication-2026-10-25.md), and
[S47's final proof](docs/plans/shiftwork/workplace-3d/s47-final-offline-2026-10-25.md).
This source includes S46, which is CLOSED INCOMPLETE and unaccepted. Its
[retained coach proposal failed compilation](docs/plans/shiftwork/slice46-coach-deadline-60-live-result-2026-10-26.md).
No successful coach repair, learner improvement, real business impact,
production readiness, or total Sandbox-cost claim follows. The S48 smoke proves
one diagnostic route and response, without a full live repair-to-inheritance chain.

For a fresh live demonstration, first approve a bounded packet with a model,
call count, and spend ceiling. Provision `NEBIUS_API_KEY` and
`NEBIUS_PROJECT_ID` privately in the controller environment. Historical call
allowances do not renew automatically. Never put credentials in source, learner
inputs, captures, or logs. Record a failure before diagnosis and obtain new
authority before another call. Video publication and submission remain separate.

S26 ended in `DROP_TAVILY_CLAIM`. No discovery-benefit claim enters this pitch.
The Tavily bonus answer and submission feedback remain the entrant's decisions.
