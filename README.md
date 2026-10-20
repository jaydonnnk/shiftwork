# Shiftwork

Practice diagnosing an AI service, comparing repairs, choosing an exact tested
version, and maintaining its consequences across shifts. Three fictional
workplaces cover a bookshop service, a bicycle-repair deployment, and a revenue
operations workflow. Sales, bookings, ownership and incidents are **synthetic**.

**Submission track:** Best Apps and Agents, confirmed by Jaydon on 2026-10-15.
**License:** [MIT](LICENSE). Dependencies retain their own licenses.

## Local 3D workplaces

The S35 working tree adds the Northline workshop alongside Bellwether and
Stonebridge. The user accepted S35 on 2026-10-21. The exact narrow Chromium
content checks cover Acceptance, Rollout and Handover with keyboard, touch and
native 200% zoom, including an unsaved draft and graphics failure. Native Safari
rendered the actual WebGL2 room at 100%, but no qualifying native 200% harness
receipt exists; the user accepted that recorded gap on their own manual test.
Exact Chrome .84 and the separately authorized clean locked installation remain
unproved. See the [S35 checkpoint](docs/plans/shiftwork/workplace-3d/s35-checkpoint-2026-10-20.md)
for evidence and limits. The hosted demo remains S28.

The source-delivery helper `verify_three_browser_journeys` in
`tests/packaging/test_clean_env_install_and_run.py` exercises all three complete
browser journeys, the three actual rooms and a Northline graphics-failure
workbench with external asset requests blocked. It accepts an explicit existing
interpreter and does not install dependencies. The clean-install test invokes
the same helper after its separately authorized locked installation.

The S29 working tree adds a locally served WebGL2 Bellwether room beside the
existing workbench. Intake, the operating console and independent assessment
open existing panels. Three.js r180 is pinned locally with its MIT notice;
there is no CDN, frontend build step or second application server.
Graphics failures retain the complete HTML workbench and recorded evidence.

S29 is accepted and published on main under the approved narrowed scope. The
scope is Gate 3 section 9: headless Chromium 155 on this macOS build at the
exact 1280x720, 640x900 and 390x844 viewports, plus the recorded native Safari
26.5 observations. The hosted demo remains S28. See the
[S29 checkpoint](docs/plans/shiftwork/workplace-3d/s29-checkpoint-2026-10-19.md)
for measured local evidence and limits. The hosted demo remains S28.

Local S29 checks now cover exact narrow viewports at 100% and 200% zoom,
focus/retry and partial initialization. All three browser journeys and 16 fresh
packaging checks pass. The full offline suite retains its known port_dead
failure. Windows and Edge, Firefox, previous-stable Safari, physical iPhone and
Pixel, audible VoiceOver and NVDA, and comprehension evidence are unverified
and unclaimed by this scope.

## S33 handover and later test

The local Bellwether room now includes the owner desk, read-only incident review
tray and handover shelf. The workbench shows the inherited selection, rationale,
requirement hashes, limits and unresolved incidents. A historical incident opens
an explicit history view with a visible "Return to current shift" control.
Ordinary polling does not leave that view. A later-condition experiment on the
A/B bench is bound to the original selected and retained versions and to its
observed operation. It does not replace the selection, and a newer save or a new
shift cannot promote a different version.

The existing offline walkthrough remains the reproducible full journey:

```sh
SHIFTWORK_EXECUTOR_ADAPTER=recorded \
  .venv/bin/python -m demos.final_pivot --stage inheritance
```

Expect `PASS_OFFLINE_POLICY`, `prior_bytes_identical: true`, six COMPLETE later
slots and both the original selected and retained versions unchanged. The
browser receipts use `/tmp/shiftwork-s33-*`; `workplace_s33_controls.mjs` drives
the complete normal journey and the inherited later world:

```sh
node tests/client/workplace_s33_controls.mjs /tmp/shiftwork-s33-controls
``` The later preview's
outage is a staged test derivation, not reviewed product material. Local
headless Chrome evidence does not prove physical-device, named screen-reader or
comprehension outcomes. See the
[S33 checkpoint](docs/plans/shiftwork/workplace-3d/s33-checkpoint-2026-10-20.md)
for measured limits.

## S34 Stonebridge work accepted on local evidence

Stonebridge has its own signal rack, qualification board, routing table and
ownership lanes. One exact synthetic owner assignment moves a labelled marker;
recorded clock starts are not countdowns and handoff markers send no messages.
The handoff and code-review findings have failing-capable repairs. Both graphics
tiers, exact Chromium narrow/zoom checks, native Safari rendering and 200%
navigation, and all three complete extracted offline browser journeys pass.
Extraction reuses installed dependencies. The known `port_dead` suite failure
and the approved native/device/AT evidence limits remain visible. The user
accepted S34 on 2026-10-20. Its six focused commits `80f8818..88cf0f6` are
fast-forwarded and published on main. See the
[S34 checkpoint](docs/plans/shiftwork/workplace-3d/s34-checkpoint-2026-10-20.md).

## Hosted practice demo

Open [Shiftwork on Render](https://shiftwork.onrender.com). This is one shared
fictional practice database. Other visitors can change the same shift; it has no
private learner accounts. Use the downloadable/local build to retain your own
history. A [public source build at the tested S28 code revision](https://codeload.github.com/jaydonnnk/shiftwork/zip/9f0adba1a966ffa944dbadc6794157bfb127041e)
is available without a login; its clean-environment packaging check passed.

The free service sleeps after 15 idle minutes. Render describes wake-up as about
one minute; actual observations and current S28 limits are in the
[S28 hosted evidence](docs/plans/shiftwork/slice28-hosted-evidence-2026-10-19.md).
Sleep, restart or redeploy starts a fresh practice database. The next visit
shows all three boards with no shift; choose a board and open a new shift.
Free hosting is not an availability guarantee.

With both provider credentials present, startup checks Sandbox permissions and
enables Token Factory diagnostics, eligible selected operations and help. Each
operation/comparison receives its own existing bounded meter. Bellwether's
first baseline stays a labelled saved inspection under its original contract;
its edited diagnostics and later eligible choices can execute in isolation.
The runtime notice reports configuration; each action reports its actual
`RECORDED_INSPECTION`, `TRUSTED_LOCAL` or `ISOLATED_LIVE` evidence separately.

Without either credential, the service labels its recorded fallback. Saved
inspections replay captures; comparisons and selected operations may execute
byte-pinned fixtures as `TRUSTED_LOCAL`. No live inference is claimed. Credentials
belong only in Render's secret settings, never in source, a database or logs.
GTM's previously recorded live-comparison request-shape limitation remains;
S28 does not raise its ceiling. The known port_dead and Northline 390px red rows
also remain visible. S28 was accepted by Jaydon on 2026-10-19, with the recorded limits intact. The controlled wake request took 43.438 seconds after 16 idle minutes and returned a fresh database.

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
their old allowances were current. The separate S28 hosted practice demo is linked above; the S27 source zip remains an offline download with its recorded limits.

S26 ended in `DROP_TAVILY_CLAIM`; no discovery-benefit claim enters this pitch.
The Tavily bonus answer remains Jaydon's submission-time decision. Learning
improvement, general model superiority, real business impact and total Sandbox
compute cost are unproven. The repository was pushed and made public on
2026-10-15; a public video and the Devpost submission remain separate authorized
actions, not consequences of running these commands.
