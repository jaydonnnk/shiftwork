# Shiftwork

Practice diagnosing an AI service, comparing repairs, choosing an exact tested
version, and maintaining its consequences across shifts. Three fictional
workplaces cover a bookshop service, a bicycle-repair deployment, and a revenue
operations workflow. Sales, bookings, ownership and incidents are **synthetic**.

**Submission track:** Best Apps and Agents, confirmed by Jaydon on 2026-10-15.
**License:** [MIT](LICENSE). Dependencies retain their own licenses.

## Start locally

Use Python 3.12 or 3.13. The current packaging verification runs on macOS with
Python 3.13; this is not a promise of compatibility with every OS or Python build.
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
new database filename to start over. Do not expose this single-user controller
on a public interface. On Windows set the two environment variables in the
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

```sh
.venv/bin/python -m pytest tests/packaging/test_clean_env_install_and_run.py -q
.venv/bin/python -m pytest tests --ignore=tests/packaging -q
```

The first command creates a clean environment and downloads the locked
dependencies. It tests an isolated source copy, all three offline journeys,
three-board availability and served assets. Credentials and host adapter
settings are excluded. Its live-demo result is `OFFLINE_SKIP`, never a live PASS.

The non-packaging entry baseline on macOS is **1,423 passed, 1 failed, 1 skipped**.
The known failure is `test_conformance_suite_recorded_local[port_dead]`: a bound
but non-listening socket times out instead of producing the recorded unreachable
result. Northline's 390px browser reach assertion is also a previously deferred
failure. Neither is hidden or fixed by packaging. Current measurements and
package verification are in [the S27 record](docs/plans/shiftwork/00-status.md).
Browser checks additionally need an existing Node and Chrome installation;
`tests/client/env.mjs` accepts `SHIFTWORK_PYTHON` and `CHROME_PATH`.

## Evidence modes and limits

| Label | What it proves | What it does not prove |
| --- | --- | --- |
| `RECORDED_INSPECTION` | Reads captured response bytes | Fresh inference or eligibility for edited code |
| `TRUSTED_LOCAL` | Executes byte-pinned operator fixtures | Safe execution of arbitrary learner repairs |
| `ISOLATED_LIVE` | Separately authorized isolated execution with retained observations | Learning gain, production readiness or a universal model-quality score |

The default UI does not turn an edited arbitrary file into a locally executable
repair. Fresh learner-code execution requires the verified isolated route and
operator authorization. The controller owns credentials, protected cases,
evaluation and selection eligibility. Source distributions include controller
fixtures so judges can reproduce the system; they are not an anti-cheating
boundary against someone who owns the controller filesystem.

## Judge path and model use

Read [the judge evidence and video-script draft](docs/plans/shiftwork/slice27-judge-evidence.md).
It links the **single successful S20 chain**, including ten observed Nemotron
calls, an exact selected version, its checked synthetic sale and inheritance.
The first failed attempt remains separate. The available summaries and audits
are historical evidence, not a fresh live run or a retained recording of the UI.

Observed model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` through Nebius Token
Factory, for bounded service tool selection and optional diagnostic help. No
fine-tuning or other-model benchmark is claimed. Numeric feedback ratings remain
unfilled where observed evidence does not support a score. S25's two live
Sandbox operations made **zero inference calls**.

**The public repository at `https://github.com/jaydonnnk/shiftwork` was made
public on 2026-10-15; no fresh live demo recording is supplied.** For a
supervised live demonstration, ask the operator to prepare a fresh bounded
packet, verify current model access, rates and Sandbox permissions, and obtain
explicit call/spend approval. Only then provision `NEBIUS_API_KEY` and
`NEBIUS_PROJECT_ID` through the controller environment. Do not send credentials
to a learner, place them in source, or rerun date-pinned historical runners as if
their old allowances were current. S28 hosting is not part of this package.

S26 ended in `DROP_TAVILY_CLAIM`; no discovery-benefit claim enters this pitch.
The Tavily bonus answer remains Jaydon's submission-time decision. Learning
improvement, general model superiority, real business impact and total Sandbox
compute cost are unproven. The repository was pushed and made public on
2026-10-15; a public video and the Devpost submission remain separate authorized
actions, not consequences of running these commands.
