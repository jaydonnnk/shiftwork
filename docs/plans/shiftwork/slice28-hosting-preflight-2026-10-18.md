# S28 hosting preflight, 2026-10-18 Asia/Singapore

S28 is incomplete. This checkpoint records local verification and platform
research. No product source, approved gate, existing evidence or package changed.
No hosting account was created, service deployed, provider request sent, branch
pushed or main merged. Local focused commits are authorized by the S28 handoff.

## Repository and package

At entry, `shiftwork/slice-28`, local main and origin/main were all
`81245f040eced5b7a36b1e201f29f68eedf98c3b`; the tree was clean.
`git ls-remote origin refs/heads/main refs/heads/shiftwork/slice-27
refs/heads/shiftwork/slice-28` confirmed main at that hash, S27 at
`0e0f25749de37b8f5637845f3526c5e32e2c1578`, and no remote S28 branch.
The interpreter is `.venv/bin/python`, Python 3.13.12 on arm64.

The existing downloadable zip is still 9,416,208 bytes with SHA-256
`f2f4f26eb467e9418c7db7f3587f9a42c6622aac5846848c42dfa05105dde0b8`.
This is a new size/hash check, not another extraction test or upload.
Its absolute path is in the receipt below.

## Baseline before changes

Commands ran from `/Users/jayd0/Desktop/shiftwork`:

```sh
.venv/bin/python -m pytest tests -q
.venv/bin/python -m pytest tests/packaging/test_clean_env_install_and_run.py -q
.venv/bin/python -m demos.gateway_spike --phase preflight
```

- Full suite: exit 1, 1 failed, 1,430 passed, 1 skipped, 2 warnings in
  192.90 seconds. The only failure is
  `tests/executor/test_conformance.py::test_conformance_suite_recorded_local[port_dead]`.
  Observed REQUEST_TIMEOUT, wall 5,010 ms; recorded SERVICE_UNREACHABLE, 55 ms.
- Separate packaging run: exit 0, 7 passed in 19.29 seconds; mechanism
  `stdlib venv + pip`, three-board offline pivot PASS, live result `OFFLINE_SKIP`.
- Preflight: exit 3, `{"probe":"sandbox_whoami","result":"missing_environment"}`.
  Both required Nebius variables were absent from the process environment.
  No provider request was made. No credential value was printed or retained.
- Northline's known 390px reach failure remains carried. Browser journeys have
  not been repeated in this session. No browser or deployed-access PASS is claimed.

Receipts are under [evidence/slice28-hosting-2026-10-18/](evidence/slice28-hosting-2026-10-18/).
Gzip log receipts preserve the exact pytest output; raw local copies remain
ignored. Both round trips match the hashes in `environment-log-scan.json`.
The two pytest logs passed an in-memory scan for raw, JSON-escaped, base64 and
URL-encoded sensitive environment values before copying. This bounded scan is
not a new repository/history secret audit. No new product guard or mutation
coverage is claimed.

## Render terms checked today

Render remains a candidate for the approved route. These are vendor statements,
not measurements of a deployed Shiftwork service:

- [Deploy for Free](https://render.com/docs/free): Free web services sleep after
  15 idle minutes. The vendor describes wake-up as about one minute. Local file
  changes, including SQLite, are lost on sleep, restart and redeploy. Free
  instances cannot attach a persistent disk. A workspace has 750 free instance
  hours per calendar month. Without a payment method, exhausted bandwidth
  suspends free services and exhausted pipeline minutes stop new builds.
  Free services may also be restarted or suspended for high outgoing traffic.
- [Render's free-tier article](https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026):
  no credit card is required. Whether this account encounters an additional
  verification requirement is [unknown]. Stop if a paid tier or card is required.
- [Python version settings](https://render.com/docs/python-version): explicitly
  choose a supported 3.13 version. The documented current default is outside
  this project's `>=3.12,<3.14` range. Render supports released Python versions
  via `PYTHON_VERSION` or `.python-version`; 3.13.12 matches this local run.
- [Web services](https://render.com/docs/web-services): managed HTTPS and a
  long-lived Python process fit this architecture. Bind to `0.0.0.0` and the
  supplied `PORT`, with exactly one uvicorn worker. A native Render install of
  this lockfile, cold-start duration and service resource fit remain [unknown].

The proposed SQLite path is an app-local `practice.db` on ephemeral storage.
A fresh database after a platform restart is the approved deterministic reset.
Do not delete an existing local database to imitate that evidence. No reset,
restart, availability guarantee, uptime monitor or deployed URL is established.

## Startup gap demonstrated without a provider call

`startup-probe.json` records a fresh temporary database served by TestClient
using `create_app(..., executor="tokenfactory")`. All three boards were
AVAILABLE in declaration order: bookshop, gtm, northline. Opening a Bellwether
shift succeeded. POSTing its run returned HTTP 409 with
`live operation requires a bounded run budget`.

[The app factory](../../../shiftwork/app.py) initializes live operation and
comparison budgets, and the assist gateway, to None unless the caller supplies
them. [The routes](../../../shiftwork/api/routes.py) refuse live runs and
comparisons without their respective budgets. Setting credentials and
`SHIFTWORK_EXECUTOR_ADAPTER=tokenfactory` alone does not supply those objects.
[The existing budget types](../../../shiftwork/live_budget.py) have different
frozen shapes: one operation/call for an operation, twelve operations/eighteen
calls for one Bellwether comparison. They are mutable, consumed instances.
The historical S20 and S25 runners supply them explicitly at stage boundaries.

This is a deployment-readiness gap, not permission to remove a guard, raise a
ceiling, reuse the wrong meter or silently reset a consumed allowance. The S25
GTM live-comparison shape limitation also remains intact.

The narrow proposed resolution is hosted startup wiring around the existing
FastAPI app: choose tokenfactory only with both credentials, otherwise label
recorded fallback; configure the existing assistance gateway; supply the
existing operation and comparison meters with explicit lifetimes for their
respective actions. A single reused meter eventually blocks later actions.
Allocating fresh meters needs deliberate route integration and fail-capable
proof, rather than claiming environment-only deployment works. Resolve whether
this wiring is allowed by S28's "unchanged controller" wording before changing
product code. No gate has been reopened or re-approved by this checkpoint.

## Pending prerequisites and next work

Jaydon performs the hosting signup/login and connects the public GitHub repo.
Use a free Hobby workspace with no payment method. Service creation is pending
verified startup settings. The service URL and account readiness are [unknown].

Jaydon provisions `NEBIUS_API_KEY` and the `aiproject-...` `NEBIUS_PROJECT_ID`
privately in the host's secret settings or in `~/.zshenv` with mode 600. Never
paste them into chat or add a repo `.env`. Token Factory credit expiry and the
current balance are [unknown]; the handoff's $27 is a historical user report.
Current vendor model rates are also [unknown]: both the model catalog URL and
prices page were inaccessible through today's web reader. Historical rate
constants are not a verified current rate card.

After resolving startup wiring and provisioning, rerun entitlement preflight;
require the expected six permissions before a single bounded service probe.
Retain failure evidence and diagnose before another call. Then deploy, measure
restart/reset and cold start, verify judge access and monitoring, make the bounded
hosted model-backed action, and repeat deployed browser/package checks. Keep the
downloadable build and both red rows visible. Update README and the judge path
only with a real verified URL. Post-slice architect-reviewer cleanup and S28
acceptance remain pending. Push, main integration, paid services and submission
remain outside this checkpoint's authority.
