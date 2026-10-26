# S48 offline release preparation, 2026-10-25

**Current continuation, 2026-10-26 Asia/Singapore.** Installation, existing-free-
Render deployment and the bounded one-inference/one-Sandbox smoke/wake packet
are authorized. Do not reconfirm those actions. Attempt-g passes the exact
isolated clean-install node, all three browser journeys, actual rooms and
Northline fallback. This is uncommitted overlay proof. The local repaired bytes
and README have not been published or deployed. Git publication is the separate
unresolved authority. See the [resumed checkpoint](slice48-release-checkpoint-2026-10-26.md#resumed-offline-result)
for the capture-selector diagnosis, responsive readiness repair and failed
attempts. S46 stays CLOSED INCOMPLETE and its compile guard stays unapproved.
The preparation procedures and older notices below retain their dated scope.

S48 is incomplete. This packet prepares the README and a release procedure.
No install, credential read, entitlement preflight, provider request, Sandbox
operation, deployment, publication, or live-host check ran for this preparation.

## Pin the release scope

Updated 2026-10-26 Asia/Singapore. The S48 and S50 branches fast-forwarded to
`42ffc2eb8487ee36f3cc567848a5abda7070d7ab`, matching the fetched `origin/main`.
The original preparation base was `7d156b4541a0774cfc0e4196912c10a0e2e6e7e1`.
Its 2026-10-25 ref observations are historical. The current source revision
does not contain these uncommitted preparation documents or select a release.
The [S47 publication record](workplace-3d/s47-publication-2026-10-25.md) and
[final local proof](workplace-3d/s47-final-offline-2026-10-25.md) cover accepted
S47 and its accepted S45 ancestry. The README changes in this worktree are
uncommitted, so that candidate does not yet contain this documentation.

The authorized integration includes S46 source. S46 is CLOSED INCOMPLETE and
UNACCEPTED. Its [retained result](slice46-coach-deadline-60-live-result-2026-10-26.md)
records a non-compiling coach patch at line 73, no service start and no service
inference. Empty stdout resulted from that coach failure. Coach-only limits are
4096 tokens/60 seconds; service output stays 1024 with deadlines 5/10/45. The
proposed pre-reservation compile guard is unapproved and unimplemented. Every
closed live action, once marker, store and pristine seed remains untouched.
Source integration does not establish S46 acceptance or a successful coach repair.

The approved [S48 exit contract](04-slices.md#slice-48-redeploy-current-main-and-rewrite-the-judge-path)
requires current main on the existing free Render service, the guided path,
one live smoke diagnostic, a recorded wake, existing hosted checks, and an
isolated-source packaging check. Offline preparation satisfies none of the
hosted or clean-install evidence requirements.

## Resolve the named authorities

Before the dependent step, record explicit authority for each remaining action.

- Review the exact eventual release revision with S46's closure limits attached.
  The branch integration is complete; no S46 takeover or live action follows.
- Approve coherent Git publication of this reviewed packet and identify the exact
  resulting main commit. Publication can trigger an existing host auto-deploy,
  so coordinate it with deployment authority before pushing.
- Authorize access to Render and its private controller settings, credential
  validation, startup entitlement checks, and the deployment of that exact commit.
- Confirm the existing free service and usable Token Factory credits. Do not add
  a payment method, use a paid tier, or spend through Nebius Console.
- Authorize the locked clean installation and its network access in disposable
  directories. The existing packaging test installs even when dependencies exist.
- Approve the one-diagnostic packet below, including its call count and spend cap.
- Authorize the hosted reads and controlled idle/wake observation. A wake can
  trigger the app's startup Sandbox permission check.

S49 outreach, consent, session calls, S50 video publication, and submission each
retain their separate authority. Gate changes and protected-fixture edits are
outside this packet.

## Check the existing configuration

Source inspection, not a live configuration check, establishes the following.

- `shiftwork.app:create_app` selects `create_hosted_app` only when `RENDER=true`
  and the caller has not supplied an explicit executor. One FastAPI process and
  SQLite remain the architecture.
- `shiftwork/hosted.py` enables live execution only with both `NEBIUS_API_KEY`
  and `NEBIUS_PROJECT_ID`. It requires the AI-project format and six explicit
  permission values: `cancel`, `import`, `list`, `set_image_tag`, `spawn`, and
  `spawn_disposable`. Missing credentials produce a labelled recorded fallback.
- Startup checks permissions, not inference. Each action receives a fresh
  existing meter. Duplicate workers must claim the queued run atomically.
- Current hosted comparison construction allows at most 24 operations and 42
  calls before frozen-shape preflight narrows it. S28's earlier 12/18 figures
  are historical. Diagnostic preflight narrows its existing 10-operation,
  40-call maximum to the frozen repetitions and request count. Its inference
  projection cap remains USD 0.10. No ceiling changes are proposed.
- The Nano defaults, image, and gateway configuration remain source-owned.
  Do not substitute a larger coach model or claim S46 from an environment edit.
- No Render blueprint is present. Read the actual service settings only after
  authorization. The retained S28 build command is
  `pip install --no-deps -r requirements.lock`. The explicit start command is
  `python -m uvicorn shiftwork.app:create_app --factory --host 0.0.0.0 --port "$PORT" --workers 1`.
  S28 recorded Python 3.13.12. Check the candidate's supported Python range
  and actual host runtime before release.

Configuration names to review privately are `RENDER`, `PORT`, `PYTHON_VERSION`,
`SHIFTWORK_DB_PATH`, `SHIFTWORK_EXECUTOR_ADAPTER`, `SHIFTWORK_SERVICE_MODEL`,
`SHIFTWORK_ASSIST_MODEL`, `SHIFTWORK_TOKEN_FACTORY_IMAGE`,
`SHIFTWORK_GATEWAY_AUDIENCE`, `NEBIUS_API_KEY`, and `NEBIUS_PROJECT_ID`.
Local verification also uses `SHIFTWORK_PYTHON`, `CHROME_PATH`, `PYTHONPATH`,
`PYTHONDONTWRITEBYTECODE`, `TMPDIR`, and `XDG_CACHE_HOME`.
These are names only. Do not export or print credential values.

## Prepare an isolated source package

The following commands are deferred. Set `S48_APPROVED_RELEASE_REVISION` to the
exact eventual committed release revision containing the reviewed README, history,
and this runbook. No commit is authorized now. The entry candidate does not contain
these edits and must not be used to prove their delivery. Run these commands from
the reviewed repository. The archive and byte comparisons require the committed
documents to match the reviewed working files. Repin after any S46 integration.
The `s47-s48` receipt prefix satisfies the unchanged browser helper allowlist.
Every directory here is newly created and S48-owned. No S47 receipt is reused.

```sh
set -eu
s48_release_revision=${S48_APPROVED_RELEASE_REVISION:?Set the approved committed release revision including reviewed docs}
test "$s48_release_revision" != 7d156b4541a0774cfc0e4196912c10a0e2e6e7e1
git cat-file -e "$s48_release_revision:docs/README_HISTORY.md"
git cat-file -e "$s48_release_revision:docs/plans/shiftwork/slice48-offline-preparation-2026-10-25.md"
s48_release_root=$(mktemp -d /tmp/shiftwork-s47-s48-release.XXXXXX)
mkdir -p "$s48_release_root/source" "$s48_release_root/tmp" "$s48_release_root/cache"
git archive --format=tar "$s48_release_revision" > "$s48_release_root/source.tar"
tar -xf "$s48_release_root/source.tar" -C "$s48_release_root/source"
cmp README.md "$s48_release_root/source/README.md"
cmp docs/README_HISTORY.md "$s48_release_root/source/docs/README_HISTORY.md"
cmp docs/plans/shiftwork/slice48-offline-preparation-2026-10-25.md \
  "$s48_release_root/source/docs/plans/shiftwork/slice48-offline-preparation-2026-10-25.md"
```

After separate installation authority, run the existing exact test node from
that extracted source. It creates another isolated source archive, installs the
lockfile, checks dependencies and assets, runs all three offline journeys, and
checks actual rooms and fallback delivery.

```sh
cd "$s48_release_root/source"
env -i PATH=/Users/jayd0/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin \
  PYTHONPATH="$s48_release_root/source:$s48_release_root/source/tests/packaging" \
  PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  SHIFTWORK_PYTHON=/Users/jayd0/Desktop/shiftwork/.venv/bin/python \
  TMPDIR="$s48_release_root/tmp" XDG_CACHE_HOME="$s48_release_root/cache" \
  /Users/jayd0/Desktop/shiftwork/.venv/bin/python -B -m pytest \
  tests/packaging/test_clean_env_install_and_run.py::test_clean_env_install_and_run \
  -q -p no:cacheprovider --basetemp="$s48_release_root/install-proof"
```

An existing-dependency browser proof is available without installation. Its
fresh S48 result is recorded below. Repeat it for the eventual committed release. The inspected signature is
`verify_three_browser_journeys(source: Path, python: Path, out: Path)`.
Its caller is the clean-install test above. Use a new output root and the
same extracted source to avoid shared stores, profiles, caches, and receipts.

```sh
env -i PATH=/Users/jayd0/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin \
  PYTHONPATH="$s48_release_root/source:$s48_release_root/source/tests/packaging" \
  PYTHONDONTWRITEBYTECODE=1 \
  SHIFTWORK_PYTHON=/Users/jayd0/Desktop/shiftwork/.venv/bin/python \
  TMPDIR="$s48_release_root/tmp" XDG_CACHE_HOME="$s48_release_root/cache" \
  /Users/jayd0/Desktop/shiftwork/.venv/bin/python -B - \
  "$s48_release_root/source" "$s48_release_root/existing-dependency-browser" <<'PY'
from pathlib import Path
import sys
from tests.packaging.test_clean_env_install_and_run import verify_three_browser_journeys
print(verify_three_browser_journeys(
    Path(sys.argv[1]), Path('/Users/jayd0/Desktop/shiftwork/.venv/bin/python'), Path(sys.argv[2])))
PY
```

The helper blocks external browser assets and runs all three journeys, actual
rooms, and a Northline graphics-failure workbench. It does not prove a clean
installation. The package's live result must remain `OFFLINE_SKIP`. Record
archive hash, exact revision, interpreter, command, exit status, and receipts.

## Deploy and check the exact bytes

After the named authorities are recorded, perform these steps in order.

1. Record the actual previous successful Render deployment ID and revision,
   current service settings, boot ID, and board state without secret values.
   The last retained hosted revision is S28 `9f0adba1a966ffa944dbadc6794157bfb127041e`.
   The current deployed revision is unknown until checked.
2. Deploy the approved exact main commit to the existing free service. Preserve
   the single-worker start command and existing environment names and limits.
3. Retain `/api/runtime` and `/api/boards` responses. Require configured executor
   `tokenfactory`, all six permissions true, the expected runtime, and three
   available boards. These are startup facts, not fresh inference evidence.
4. Compare served bytes with the candidate's complete 18-file client pin,
   including `workplace-assets.json`. Require every served hash to match the
   pinned release source before counting a browser receipt.
5. Inspect the guided path at 1440x900, 1280x720, and 390x844. Record all five
   panels, Technical details reveal, full-workbench exit, focus, and visible
   evidence labels. Existing S28 checks alone do not prove the guided contract.
6. Run the read-only S28 browser command below. It checks 12 representative
   views at widths 1440 and 390, three board reads, notice/API equality, and
   JavaScript exceptions. It does not click an inference action or prove all
   station reach, physical-device, assistive-technology, or comprehension claims.
7. Run the approved single smoke diagnostic. Retain failures without a retry.
8. Stop every owned request source, wait at least 16 minutes without polling,
   then record the first wake request's elapsed time, response, new boot ID,
   board reset, runtime, and permissions. Public visitor traffic is uncontrolled.
   If sleep cannot be established, report the observation as inconclusive.

Prepare a fresh root with `tmp` and `cache` directories before this deferred
command. Replace the output root with the release's retained receipt directory.

```sh
env -i PATH=/Users/jayd0/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin \
  SHIFTWORK_PYTHON=/Users/jayd0/Desktop/shiftwork/.venv/bin/python \
  PYTHONDONTWRITEBYTECODE=1 TMPDIR="$s48_release_root/tmp" \
  XDG_CACHE_HOME="$s48_release_root/cache" \
  /Users/jayd0/.local/bin/node tests/client/hosted_browser.mjs \
  https://shiftwork.onrender.com "$s48_release_root/hosted-browser"
```

A local proof and a hosted proof count separately. Retain the configured
executor and each action's actual evidence mode. Update the README's host and
archive claims only after verifying that release. Its first judge step can then
read: **Read the failure:** [open Shiftwork](https://shiftwork.onrender.com),
choose Bellwether Books, open a shift, and select **Guided first run**. Until
that URL serves the verified guided release, keep the local-first opening.

## Approve one smoke diagnostic

Proposed packet, not authorization or an executed result:

- Use one fresh hosted Bellwether mission-v2 shift and its reviewed starter.
  Resolve the actual starter version ID from that shift. Do not reuse an S28
  mission-v1 shift or invent an ID, cause, or investigation.
- Reserve one bootstrap source `DIAGNOSTIC` through
  `POST /api/shifts/{shift_id}/experiments`, with
  `candidate_a_version_id` set to that reviewed starter, a fresh
  `client_request_id`, and `public_repetitions=1`. Leave investigation unset
  only for the existing bootstrap diagnostic path. Preflight the frozen
  context's one public request `bellwether-collection-001` before send.
- Use the existing Nano service model and frozen source-owned settings.
  Maximum: one Sandbox operation and one provider inference request. No
  assist, coach, comparison, protected draw, selection, or operation is included.
- Cap projected inference spend at USD 0.10 under the existing meter. The
  source's historical USD 0.06/0.24 per million-token rates imply a conservative
  one-call reservation of USD 0.00221184. Those are not current vendor quotes
  or an observed debit. Verify rates and usable credits privately before approval.
  Sandbox cost is unknown and must be included in the explicit spend decision.
- Retain exact source/context hashes, experiment and run IDs, reservation,
  evidence mode, terminal state, captures, provider reply, usage, parse result,
  deterministic checks, and meter counts. Confirm no eligibility or ledger write.
- Stop after that attempt, including a timeout, empty reply, wrong plan, or
  unsuccessful operation. Preserve the complete failure and diagnose offline.
  A second call requires new authority. A successful smoke proves this route
  and response only, not a stable miss rate, learner gain, or the full live loop.

## Roll back without rewriting history

If startup, source hashes, labels, or a release check fails, stop all owned live
actions and preserve the failed deployment's evidence. Do not fix settings by
raising a ceiling, changing a model, enabling fallback, or retrying inference.
With rollback authority, redeploy the previous successful deployment ID captured
before release. Confirm its revision, runtime, hashes, and labels. If that ID
cannot be established, stop for an explicit rollback target decision.

A rollback restarts the ephemeral practice database. Do not claim to restore
learner history or merge previous and new stores. Retain the failed and restored
boot IDs and observed reset. S28's old code and old smoke are historical evidence,
not an automatic rollback approval or proof of the rolled-back host today.

## Branch refresh checks, 2026-10-26

Both S48 and S50 now resolve to `42ffc2eb8487ee36f3cc567848a5abda7070d7ab`.
Each branch passed 233 focused Python checks and all 361 Node client checks,
exit zero. Python reported the same two Starlette/AnyIO deprecation warnings.
The Python set covers assist/proposals, investigation assistance, API projection,
hosted wiring, host-path isolation, asset closure and service gateway isolation,
deadline and task-plan behavior. It includes the coach's real 21-second wait.
The existing interpreter ran with `-B`, a clean environment, fresh owned temp
and cache directories, and no pytest cache. No installation test was selected.
The exact commands, JUnit results and logs are in this continuation's
`outputs/coordinator/branch-refresh-2026-10-26/`.

This is fresh focused integration proof. The 2026-10-25 browser receipts below
remain historical proof of the earlier source, not the merged source. No new
browser journey, full Python suite, clean installation or hosted check ran.
S48 remains incomplete. The eventual committed release, installation, deployment,
hosted guided path, bounded smoke and sleep/wake evidence are still pending.

## Historical offline checks, 2026-10-25

This preparation changed documentation only. The proportionate command used the
existing Python interpreter with `-B`, a clean environment, disabled bytecode,
owned temporary/cache roots, and no pytest cache. It ran `tests/api/test_hosted.py`,
all six cases of `test_offline_environment_ignores_host_execution_settings`, and
`tests/packaging/test_client_asset_closure.py`: 46 passed, two existing
Starlette/AnyIO deprecation warnings, exit 0. Hosted tests replace every
provider/control-plane operation with offline doubles.

The unchanged `verify_three_browser_journeys` helper also exited zero in a
new physical source copy at
`/tmp/shiftwork-s47-s48-source-delivery-20261025-a/source`.
`browser/complete-browser-results.json` records PASS for all three complete
journeys, all three actual rooms, and self-tested external-asset blocking.
`browser/northline-fallback.log` records the graphics-failure workbench proof.
The helper used the existing interpreter and installed Node/Chrome. No installer,
provider, or Sandbox was used. `source-identity.json` pins the base archive and
three explicit documentation overlay hashes. `process-result.json` records exit
0 and the exact invocation. This is an uncommitted overlay proof, not a release
commit or clean-install result.

The first attempt under
`/tmp/shiftwork-s48-offline-20261025-a/existing-dependency` passed Bellwether's
native journey, then the actual-room driver rejected the S48 receipt prefix
before browser startup. Preserve `bookshop-room.log` and `process-result.json`
as rejected setup evidence. The unchanged driver's allowlist accepts S47.
The rerun's script calls `mkdir()` without `exist_ok`, so it refuses an existing
root. All source, stores, profiles, ports, and receipts were fresh and S48-owned.
No S47 original was reused. The incident is logged in `MISTAKES.md`.
After the helper exited, this runbook gained the result paragraphs. A final
manifest records that documentation-only update. Product/client bytes remain
those tested by the helper. No browser guarantee is inferred from document hashes.

The local-link audit checked 25 relative links and their Markdown anchors with
zero errors. It also confirmed exactly five opening judge steps. External URLs
were not requested. Shell blocks passed `bash -n`; embedded Python parsed with
`ast.parse`. Those checks validate syntax only, not deferred command outcomes.
`git diff --check` passed, including whitespace checks of the new documents. No product code, tests, budgets, lockfile, or fixture changed.
Authority notices are maintained separately by the coordinator.

Skipped checks are explicit: installation test, eventual committed-release
package verification, full Python and Node suites, fresh business journeys, deployed S28 browser check,
hosted guided screenshots, complete served-byte comparison, current host revision
and settings, credential/entitlement/rate/credit checks, live smoke, controlled
idle/wake, rollback rehearsal, device or named
assistive-technology checks, learner sessions, video, and submission.
S48 remains incomplete until its authorized hosted and packaging evidence exists.
