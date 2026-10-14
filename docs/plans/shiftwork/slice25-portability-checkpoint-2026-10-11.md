# S25 prerequisite: macOS portability repair checkpoint

2026-10-11 Asia/Singapore. User authorization: `setup whatever environment u need
and then start s25`. Branch `shiftwork/slice-25`, entry main `b5a9b95`, entry
worktree clean.

This checkpoint covers the portability batch the user approved ahead of the GTM
client. S25's own room, journey and fault work has not started. No gate, reviewed
material, seal, pin, credential, live call, spend, commit, push or publication
changed. The `port_dead` fixture bytes and every `TRUSTED_LOCAL_FIXTURES` pin are
untouched.

## 1. Environment built on this machine

The repository was cloned fresh onto macOS 26.5.1 (arm64) on 2026-10-11 with no
virtual environment and no Node.js. Both were built under the setup authorization:

- `.venv` from CPython 3.13.12 at
  `/Users/jayd0/.workbuddy-ai/binaries/python/versions/3.13.12/bin/python3.13`,
  installed with `uv pip install -r requirements.lock`. `shiftwork` imports from
  this tree. No `--link-mode=copy` was needed; that constraint was OneDrive-specific
  and is dead on macOS.
- Node.js v24.21.0 (npm 11.19.0) installed to `~/.local/node` and linked into
  `~/.local/bin`. Node 24 supplies the global `WebSocket` the CDP harnesses use.
- Google Chrome 155.0.8059.40 was already present at
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`. No browser was
  installed.
- `uv` 0.13.0 and `gh` 2.102.0 were already present in `~/.local/bin`.

The Windows-era interpreter rule in `AGENTS.md` section 6 (`.venv313/Scripts/python.exe`
plus the Application Control fallback) does not apply on this machine and was not
followed. Correcting that instruction file is a separate decision and is recorded
as an open question rather than edited here.

## 2. Entry baseline

`.venv/bin/python -m pytest tests -q --ignore=tests/packaging`:
**6 failed, 1393 passed, 1 skipped, 2 warnings in 159.07s**.

All six failures are consequences of the migration to macOS, not S25 regressions
and not product regressions on the previously supported platform. Five are repaired
below. Each repair was proven failing-capable by mutating the guard it protects and
requiring a real failure on a named assertion, and every mutated file was restored
byte-exactly, verified by SHA-256.

## 3. Repairs

### 3.1 Child environment allowlist is now platform-aware

`shiftwork/executor/local_process.py` pinned `CHILD_ENV_ALLOWLIST = ("SYSTEMROOT",
"WINDIR")`. Measured directly: a macOS child spawned with `env={}` still reports
`LC_CTYPE` and `__CF_USER_TEXT_ENCODING`, because CoreFoundation and libc set them
in the child whatever mapping spawn receives. They cannot be suppressed and are not
controller state reaching learner code.

Added `OS_INJECTED_ENV`, pinned to those two names on Darwin and empty elsewhere, so
the passthrough list stays exactly `("SYSTEMROOT", "WINDIR")` on every platform. Two
assertions were widened to the union: the projection scan at
`tests/api/test_host_path_env_isolation.py:159`, and the conformance comparison at
`tests/executor/test_conformance.py:423`.

The conformance comparison was also restructured. It previously read
`observed_env == spawn_envs[0]`; it now compares the child-reported environment
against the spawn environment with the pinned OS names set aside, as one equality
that covers an extra key, a missing key and a changed value together. An earlier
two-assertion form was rejected because its value arm was unreachable on macOS,
where no allowlist key is present in `os.environ`, so the mutation that should have
caught it did not fire.

Proof. Control 20a from the recorded mutation inventory, a credential name added to
`CHILD_ENV_ALLOWLIST`, still fires, on two named assertions: the pin at
`test_conformance.py:408` and `env value for NEBIUS_API_KEY reached a
learner-visible projection`. Two further limbs were mutated independently: emptying
`OS_INJECTED_ENV` fires the new equality at `test_conformance.py:424` and the
allowlist bound at `test_host_path_env_isolation.py:160`; injecting an unpinned
`SHIFTWORK_LEAKED` key into `child_env` fires the spawn-env bound at
`test_conformance.py:413`.

The informational `credential-guard` line now prints the resolved allowlist. On
Windows it renders byte-identically to the historical evidence string
`spawn env and child-reported env match SYSTEMROOT/WINDIR allowlist`.

### 3.2 Host-path scanner self-tests no longer depend on the checkout's path shape

Two self-tests derived their escaping hazard from `str(config.BOOKSHOP_SNAPSHOT)`.
`test_host_path_scan_detects_a_json_escaped_path` opened with `assert "\\" in
needle`, and `test_host_path_scan_detects_forward_slash_and_nested_json_forms`
asserted that a raw nested form does not match. Both are unsatisfiable on a POSIX
checkout, where the host path contains no backslash, so the escaping and
double-escaping branches were unproven rather than merely red.

Added `WINDOWS_SHAPED_PATH`, a literal backslash-bearing locator, and both tests now
run their detection loop over that literal and the real host path. The hazard belongs
to a needle's shape, not to the host platform, so synthesizing the shape keeps the
branch proven everywhere instead of skipping it. No assertion was weakened or
removed.

The nested limb needed a second correction. Looping both needles through it made the
assertion vacuous on POSIX, because a forward-slash path stays visible in the raw
envelope and the first-level string decode already exposes it, so the assertion
passed without any decoding. Mutating `decoded_surfaces` to disable its recursive
walk confirmed this: the test stayed green. The limb is now stated for the
backslash-shaped needle only, excludes the envelope by asserting against
`surfaces[1:]`, and adds `len(surfaces) > 1` so a decoder that returns the envelope
alone cannot pass. The deeper recursive-walk limb is owned by
`tests/sealed/test_leakscan_self_tests.py:54`, which fails when that walk is
disabled, so the two tests do not overlap.

Proof. Four independent mutations of `tests/leakscan.py`, each caught on a named
assertion: dropping the backslash-unescape form from `path_forms` fires
`test_host_path_env_isolation.py:112`; dropping needle-side normalization from
`host_leaks` fires `:134`; making `decoded_surfaces` return only the envelope fires
the new vacuity guard at `:144`; disabling the recursive walk fires
`test_leakscan_self_tests.py:54`.

### 3.3 The sealed-locator needle arm was vacuous, and is now capable on both platforms

`tests/sealed/test_payload_manifest.py:208` scans the provisioning manifest and the
run request with `all_sealed_strings()`. That set included `str(path)` for every
sealed family file, expanded into 25-character fragments. Two defects followed from
one needle.

The arm was vacuous on Windows. `leaks_in` is a plain substring scan with no
normalization, and a JSON envelope doubles every backslash, so an absolute Windows
path needle could never match a serialized payload. `sealed_identity_strings`
already documents exactly this hazard at `tests/leakscan.py:142` and masks it with
slash-free twins, and `test_leakscan_self_tests.py:73` pins that masking.
`all_sealed_strings` had no equivalent treatment and no equivalent pin.

The arm was a false positive on POSIX. Forward slashes are not escaped by JSON, so
the fragments matched immediately, and the leading fragments are the checkout's own
prefix, shared with every other host path in the same payload. The reported matches
were all windows over `/Users/jayd0/Desktop/shiftwork/`, taken from the run
request's own legitimate fixture paths.

Replaced the absolute path with `sealed_locators(path)`, the repository-relative
locator in both separator forms, for example
`shiftwork/sealed/cases/bookshop_stale_information.json`. The relative locator names
the sealed store itself rather than the checkout, so it catches an absolute or a
relative leak on any platform and cannot collide with an unrelated host path.
`sealed_identity_strings` was deliberately left alone: it already carries a
non-vacuity proof, and changing it would disturb the pinned `sealed/cases` mask.

Added two pins to `tests/sealed/test_leakscan_self_tests.py`, mirroring the identity
set's existing proof. One requires every `all_sealed_strings` needle that a
serialized surface cannot carry to have a capable twin in the set. The other injects
the locator into a representative serialized payload alongside an ordinary fixture
path and requires detection of the first and silence on the second, and pins that
the locator is host-prefix-free.

Proof. Four independent mutations, each caught on a distinct named assertion:
returning the absolute path from `sealed_locators` fires `unexpected locator shape`;
dropping the locator arm from `all_sealed_strings` fires `is not a needle; the arm is
absent`; adding an incapable needle with no twin fires `no capable twin`; making
`leaks_in` return an empty list fires `an injected sealed locator was not detected`.

### 3.4 Client harnesses resolve their interpreter and browser portably

Six hardcoded Windows paths made S25's two mandated node tests unrunnable on any
other platform. `tests/client/browser.mjs` used `CHROME_PATH ?? chrome.exe` at line
141 and `.venv313/Scripts/python.exe` with no override at line 234.
`tests/client/northline_browser.mjs` hardcoded `chrome.exe` at line 14 with no
override, and the same interpreter at line 172. `tests/client/northline_faults.mjs`
line 37 and `tests/client/render_faults.mjs` line 23 hardcoded the interpreter.

Added `tests/client/env.mjs`, one small resolver shared by all four harnesses and
available to the S25 GTM harness. It exports `repoRoot`, `pythonPath` and
`chromePath`. The interpreter resolves `SHIFTWORK_PYTHON`, then
`.venv313/Scripts/python.exe`, then `.venv/Scripts/python.exe`, then
`.venv/bin/python`, and raises a named error rather than silently running a wrong
interpreter if none exists. The Windows candidate is tried first so an existing
checkout resolves exactly what it always did. The browser resolves `CHROME_PATH`,
then the Darwin application path, then the historical Windows literal, so Windows
behavior is unchanged.

This follows the portable pattern `demos/gtm_operation.py` already uses. The
remaining `.venv313/Scripts/python.exe` literals in `demos/final_pivot.py`,
`demos/gateway_spike_live.py` and `demos/slice20_live_chain.py` were left alone:
they are outside S25's mandated tests and two of them are live-credential paths.

Proof. `node tests/client/render_faults.mjs --port 8471 --artifact-dir
/tmp/s25-harness-proof --only baseline-transient` reports
`baseline (transient surfaces) PASS harness green against the unmutated client` and
`render-fault rows: 1 of 1 as expected`. That row exercises the whole chain on macOS:
the resolver, a spawned uvicorn preview, headless Chrome over CDP, and the
Python-side DOM needle scanner. All six harness modules pass `node --check`.

The full suite was then run to completion: `node tests/client/render_faults.mjs
--port 8473 --artifact-dir /tmp/s25-renderfaults-full`, 7 baselines plus 40 fault
rows. Result: **43 of 47 as expected, exit 1**. All 7 baselines passed and 36 fault
rows were caught on their named assertions. Four rows are red, and the cause is not
this batch; see section 3.5.

### 3.5 Four pre-existing red render-fault rows, found by the full run

| Row | Reported failure |
| --- | --- |
| `event` | `Fault event must match exactly one production behavior` |
| `candidateReset` | `Fault candidateReset must match exactly one production behavior` |
| `requirementVersion` | `CDP timeout: Runtime.evaluate` |
| `unsavedFreeze` | `DOM scanner timed out` |

The first two are attributed with certainty. `shiftwork/client/app.js` is unmodified
in this batch, `git diff tests/client/browser.mjs` is three lines (one import and the
two path swaps), and the `FAULTS` map and its anchor-uniqueness check are untouched.
Counting occurrences in the working-tree bytes gives exactly two for each anchor:
`humanize(event.event_type)` appears twice and `state.candidates = { A: null, B: null };`
appears twice, where the harness requires one. That count is platform-independent, so
these rows would fail on Windows as well. They are stale anchors left by an earlier
slice, most likely S22b's Northline additions to the shared `app.js`.

This is an evidence gap rather than a new defect: the full render-fault suite does not
appear to have been re-run since the duplicate anchors landed, so earlier green claims
for it predate the duplication.

The other two are timing-shaped and are not yet diagnosed. `requirementVersion` timed
out inside CDP and `unsavedFreeze` timed out in the Python DOM scanner. They may be
macOS scheduling differences, genuine defects, or flaky. One clean rerun of just those
two rows would separate the three possibilities, and that has not been done.

None of the four is caused by this batch, but S25 must not report the render-fault
suite as green while they stand. Repairing the two stale anchors means deciding which
occurrence each fault should target, or splitting each into two board-specific
faults, which changes the recorded S21 fault inventory and wants its own decision.

**Correction, 2026-10-12.** The duplicate-anchor attribution above is falsified by
direct measurement and must not be relied on. The harness needles are the full strings
`humanize(event.event_type)), element('small'` and
`state.candidates = { A: null, B: null };\n    }`, not the truncated forms counted
above, and each full needle occurs exactly once in `shiftwork/client/app.js` at entry
commit `b5a9b95` and exactly once in the S25 worktree. All 40 `browser.mjs` FAULTS
entries are `{needle, replacement, expect}` objects, so the destructure at
`browser.mjs:478` is sound and the uniqueness assertion at `:479` could not have fired
at entry. The "exactly two" counts above came from the truncated substrings
(`humanize(event.event_type)` and `state.candidates = { A: null, B: null };`, two
occurrences each at entry), so the claims that these rows "would fail on Windows as
well" and that the suite "has not been re-run since the duplication landed" are
unsupported. In the S25 regression run of 2026-10-12 both rows are CAUGHT on their
intended assertions, and the two timing rows with them; see section 7.

## 4. Deferred with its root cause proven

`tests/executor/test_conformance.py::test_conformance_suite_recorded_local[port_dead]`
still fails. It is the one baseline failure not repaired, deliberately.

The fixture realizes a dead port at `shiftwork/fixtures/artifacts/bookshop/service.py:51`
by binding a socket and never listening. Measured directly on this machine, a connect
to a bound-but-not-listening loopback port from a separate process does not fail:
it hangs and raises `TimeoutError` after 5.001 seconds, because macOS drops the SYN
where Linux and Windows answer with RST. The adapter therefore reports
`REQUEST_TIMEOUT` with `wall_ms=5004` instead of the pinned `SERVICE_UNREACHABLE`.

The adapter's classification is correct. This is a fixture realization defect: the
fixture does not produce a dead port on macOS, so it cannot produce the pinned
conformance outcome, and the recorded and local adapters legitimately disagree.

The correct repair is to close the socket so the port is genuinely dead on every
platform, then re-pin `TRUSTED_LOCAL_FIXTURES["port_dead"]` at
`shiftwork/config.py:264`. Re-pinning is the designed workflow, since a guard test
recomputes every pin from the fixture files, and these are trusted local fixtures
rather than operator-sealed comparison material. It was not bundled into this batch
because it changes fixture bytes quoted by historical S3 conformance evidence and
wants its own pass. The alternative, making the conformance expectation
platform-aware, was rejected: it would weaken the recorded-versus-local equivalence
that is the entire purpose of the test.

This is not a blocker for S25, whose mandated tests are `browser.mjs`,
`render_faults.mjs` and `test_pivot_projection.py`.

## 5. State after this batch

`.venv/bin/python -m pytest tests/sealed tests/api tests/executor -q`:
**1 failed, 336 passed, 1 skipped, 2 warnings in 46.09s**, the single failure being
the deferred `port_dead` row above. `git diff --check` is clean.

Changed: `shiftwork/executor/local_process.py`, `tests/api/test_host_path_env_isolation.py`,
`tests/client/browser.mjs`, `tests/client/northline_browser.mjs`,
`tests/client/northline_faults.mjs`, `tests/client/render_faults.mjs`,
`tests/executor/test_conformance.py`, `tests/leakscan.py`,
`tests/sealed/test_leakscan_self_tests.py`. Added: `tests/client/env.mjs`.
Nothing is staged or committed.

## 6. What S25 still requires

Scoped from `docs/plans/shiftwork/04-slices.md:879` against the current tree. The
GTM client surface does not exist: `shiftwork/client/app.js` and `index.html`
contain no `gtm` or `stonebridge` reference at all, and the only board branch is
`const northline = () => state.slug === 'northline';` at `app.js:7`. All four named
stations are missing. The pack is registered as slug `gtm` with room id `gtm` and
five station labels at `shiftwork/packs/registry.py:275`, and the client never reads
`station_labels`. Two collisions need care: `data-station="pipeline"` at
`index.html:59` is Bellwether's evidence path, not the GTM pipeline wall, and
`styles.css` has `body[data-board="northline"]` overrides but no `gtm` arm.

The pipeline wall needs no new endpoint. Owners, clocks and escalations are produced
by `shiftwork/ledger/reducer.py:230` and served by
`GET /api/engagements/gtm/ledger` at `shiftwork/api/routes.py:161`; incidents arrive
on `BoardView.incidents` and `GET /api/incidents/{id}`.

The S22b precedent is two separate harness files per board, so S25 adds
`gtm_browser.mjs`, `gtm_faults.mjs` and a GTM preview rather than extending the
Bellwether pair. `render_faults.mjs` covers Bellwether only. Note that the approved
S25 test list names `browser.mjs` and `render_faults.mjs` but no driver for the
"GTM served-source fault assertions", so that driver has to be named explicitly.
`tests/api/test_pivot_projection.py` has only a Bellwether arm and its docstring
says other boards remain future obligations. Obligation 39 at
`docs/plans/shiftwork/04-slices.md:1019` already names S25 and needs its
satisfied-by column closed.

The live arm of S25 needs its own credentials and spend authorization and was not
attempted.

## 7. S25 client build, regression batch and corrections (2026-10-12)

S25 built and verified the GTM revenue floor client offline on this machine. No gate,
reviewed material, seal, pin, credential, live call, spend, commit, push or publication
changed. Everything below is offline evidence.

### 7.1 Station names resolved from the Gate 1 mockup

The client renders exactly four stations, in order: Signal intake, Qualification rules,
Workflow bench and Pipeline wall, from `shiftwork/client/app.js:97` through a shared
`buildStations()` helper that Northline now uses as well. Three sources agree on that
set and order: `docs/plans/shiftwork/mockups/06-revenue-floor.html:19-22` and `46-49`,
`docs/plans/shiftwork/client-visual-direction.md:74-77`, and `04-slices.md:882`.

The registry's five `station_labels` at `shiftwork/packs/registry.py:279` (Signal inbox,
Workflow, Comparison bench, Pipeline wall, Handoff queue) are a separate `/api/boards`
projection. `grep -rn station_labels shiftwork/client/` returns nothing, so the client
never reads them, and the Northline precedent settles which set the client renders:
`northline_browser.mjs` asserts the visual-direction names, not the registry labels. The
registry is untouched. Whether to reconcile the two name sets is an open product
decision for the user, not S25 scope.

### 7.2 Journey and served-source fault evidence

Journey: `node tests/client/gtm_browser.mjs` against `tests/client/gtm_preview.py` on
port 8495, artifacts in `/tmp/gtm-snap`. `browser/journey.json` records starter
`run-0001` (shift `gtm-shift-01`, `ver-0001`, FINALIZED), comparison
`experiment-gtm-shift-01-c1` (QUALIFYING_COMPARISON, investigation `inv-0001`), choice
`sel-0002` (LEARNER_CHOICE selecting `ver-0002`, retaining `ver-0003`), operation
`run-0008` (shift `gtm-shift-02`, `ver-0002`, FINALIZED) and a ledger with
`chain_status` VALID carrying INCIDENT_OPENED, OWNER_ASSIGNED, SLA_CLOCK_STARTED and
INCIDENT_RESOLVED `BWB-01`. The same directory holds `comparison.db`, `closed.db`, six
screenshots at 1280, 640 and 390 px, and 13 `dom-scan-*.json` files each reporting 4406
needles with `controls` true and `clean` true.

Served-source faults: `node tests/client/gtm_faults.mjs /tmp/gtm-faults /tmp/gtm-snap
8496` wrote `/tmp/gtm-faults/results.json` with 60 rows, all valid and zero invalid; its
log ends `{"pairs":30,"intended_assertion_failures":30,"source_preserved":true}` and
`EXIT=0`. `gtm_faults.mjs:20` asserts each of its 30 needles occurs exactly once in the
served `app.js` on every invocation. `/tmp` is ephemeral; both artifact sets are
regenerable with the preview, journey and fault commands named in the session handoff.

### 7.3 Projection arm and obligation discharge

`tests/api/test_pivot_projection.py` gained a GTM arm and reports 5 passed. Obligation
39's S25 GTM client surface and obligation 56's "the GTM entry completes at S25" are
discharged by the client surface plus this arm. The discharge is recorded here and in
`00-status.md`; the `04-slices.md` table is deliberately not edited.

### 7.4 Anchor uniqueness after the client edits

All 40 `browser.mjs` needles and all 23 `northline_browser.mjs` needles occur exactly
once in the S25 `shiftwork/client/app.js`, checked by extracting each FAULTS map and
counting occurrences. The 30 GTM needles are asserted unique by `gtm_faults.mjs:20` on
every run. This check is mandatory after any `app.js` edit: the S25 event and
candidateReset collisions logged in `MISTAKES.md` came from exactly this.

### 7.5 Northline unreviewed-switch repair and why it was necessary

The old row asserted that a programmatic switch to `gtm` was refused because the GTM
board was AWAITING_OPERATOR_REVIEW. The S23 seal (`fde011c`) made board 2 AVAILABLE at
the API, so that premise went stale and the row would have failed against the real
workplace list. The repair fabricates one AWAITING_OPERATOR_REVIEW row for `gtm` by
intercepting `/api/boards`, asserts the refusal against the fabricated row, runs
`verifyRoom()` while the fabricated list is live, then restores the real fetch and waits
for the real list to return. `gtm_browser.mjs` mirrors the same technique with northline
fabricated.

Regression for the edited guards, against the fresh journey's `comparison.db`: the
comparison snapshot passes clean (exit 0), and `dirtySwitch`, `unreviewedSwitch` and
`availability` each exit 1 on their named assertions with `"exceptions":[]`.

### 7.6 Bellwether render-fault suite is green

`node tests/client/render_faults.mjs --port 8473 --artifact-dir
/tmp/s25-renderfaults-final` reported 7 baselines PASS and 40 faults CAUGHT, "47 of 47 as
expected", EXIT=0. `/tmp/s25-renderfaults-final/sources.json` digests match the worktree
bytes of `app.js`, `browser.mjs` and `render_faults.mjs` exactly. All four rows red at
section 3.5 (`event`, `candidateReset`, `requirementVersion`, `unsavedFreeze`) are
CAUGHT here on their intended assertions. `requirementVersion` and `unsavedFreeze` were
flagged flaky under full-suite load on this machine; both passed inside this full run,
so no flake was observed and none is claimed away.

### 7.7 Two pre-existing red rows found by this batch, both deferred

Northline mobile reach. The journey completes every functional step and writes both
checkpoints, then fails `verifyReach` at `tests/client/northline_browser.mjs:255` on the
first 390px station (`brief`): all six 1280px DOM scans complete, no 390px scan exists,
and the failure screenshot shows the page at the top with the panel far below the fold.
The same assertion fails against the pre-S25 client extracted from `b5a9b95` into
`/tmp/s25-head` and run with the same harness in `SHIFTWORK_SNAPSHOT=reach` mode, a path
in which the unreviewed-switch repair never executes. It is therefore neither an S25
client regression nor a harness-repair regression; it is a pre-existing macOS
headless-Chrome scroll-follow defect at the S25 entry commit. A standalone geometry
probe that mirrors `verifyReach`'s width loop and touch steps does not reproduce it, so
it depends on prior harness state such as expanded record details and carried scroll
position. Its repair is deferred with this measurement, in the same category as
`port_dead`. No recorded green run of the 23-pair northline fault suite was found in
`docs/plans/shiftwork/evidence` or `00-status.md`, so its macOS status was unmeasured
before this session; the full suite is known red here at the reach row and running it
was left to a user decision.

`port_dead` remains deferred from section 4 with its root cause proven there.

### 7.8 Suites after S25

`.venv/bin/python -m pytest tests -q --ignore=tests/packaging`: 1 failed, 1401 passed,
1 skipped in 171.34s, the single failure being the deferred `port_dead` row, matching
the post-portability baseline. `tests/sealed tests/api tests/executor`: 337 passed,
1 failed, 1 skipped. `git diff --check` is clean. Nothing is staged or committed.

### 7.9 Limits recorded verbatim, not fixed

- The reviewed GTM operational mission has exactly one request spec
  (gtm-incident-001) whose handoff task is NOT_APPLICABLE, so no operational
  HANDOFF_ESCALATED is reachable offline. The pipeline wall's escalation group is
  proven by equality with the empty API set and by the escalationHonesty fault
  (a fabricated escalation claim fails), not by a real escalation row.
- The later-condition experiment is not exercised in the browser (it needs staged
  outage material); the "history did not change" statements are asserted in the
  compare-evidence history field and the next-experiment help text. S24 owns the
  later-condition proof.
- The live arm of S25 needs its own credentials and spend authorization; untouched.
- board.incidents excludes RESOLVED incidents while total_incidents counts them;
  INCIDENT_RESOLVED carries incident_id in its payload and the incident id in
  cause_refs[2]. The wall joins open incidents by opened_event_seq.
- GTM incident ids carry the BWB- prefix on the GTM board (pre-existing cosmetic
  defect in id generation, not S25 scope).
- port_dead re-pin pass remains deferred from the portability checkpoint.
- AGENTS.md section 6 interpreter rule is Windows-only; editing it needs user approval.

## 8. S25 live-arm authorization packet (2026-10-12, decisions only, nothing run)

The user asked for the live-arm decisions to be settled before any credential spend.
Everything below is a decision or a code-measured constraint. No call, credential,
installation or spend was used to write it, and the live arm still needs its own
explicit go-ahead on top of these numbers.

### 8.1 Ceilings are frozen by the code, not chosen here

`shiftwork/live_budget.py` already fixes the shapes, so there is no free choice:

- A qualifying comparison must be exactly 6 slots and 18 requests, with
  `max_operations = 12`, `max_calls = 18` and projected inference spend at or under
  $0.10. `LiveComparisonBudget.preflight` raises unless the shape, the model and the
  rate ceiling all match.
- A selected operation must be exactly 1 Sandbox operation and 1 inference call, under
  `LiveOperationBudget`, whose preflight requires `requests == 1`. The two meters are
  deliberately incompatible, so a comparison ceiling cannot silently cover an operation.
- Both meters count a failed spawn or a failed provider request and never refund it.

At the reviewed rates used by the S16 precedent ($0.06 per million input, $0.24 per
million output, 32768 reserved input tokens and 1024 reserved output tokens per call),
the projection is $0.00221184 per call: $0.0398 for one comparison, $0.0022 for one
operation. The whole GTM live arm below projects at roughly $0.0442, hard-capped by the
meters rather than by a budget note.

Assist is metered separately by the pack policy, not by these two classes: the GTM
registry sets `total_calls_per_shift = 2` and the orchestrator refuses a third. The S22b
precedent wraps the live gateway in `OneHintGateway`, and the GTM journey already
asserts a third call is refused.

### 8.2 Decisions

1. Rates. Re-check the public model card on the day of the run and pin that date in a
   guard that refuses on any other day, exactly as `demos/slice16_live_comparison.py:44-49`
   does. The check is a prerequisite of the run, not of this packet.
2. Model. `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, already the default of
   `config.SERVICE_MODEL` and the model the S16 rate card was checked against. No
   override: the demo asserts `config.SERVICE_MODEL` equals it and refuses otherwise.
3. Stages that run live. Phase A proves the whole journey with a test-double adapter
   under the same frozen meters and the same request shapes at zero spend, writing
   `proof_scope: TRUSTED_LOCAL_TEST_DOUBLE`, following the S22b offline arm. Phase B then
   runs once each: one qualifying comparison (6 slots, 18 calls), the shift-1 HINT and
   DIAGNOSIS assist calls (2, pack policy), and the two operations, the starter
   diagnostic in shift 1 and the inherited selected operation in shift 2, each under its
   own one-spawn one-call meter. Selection, close and inheritance stay controller-side
   and offline. Phase B is the only spending phase and runs once, with no retry and no
   top-up.
4. Evidence. `docs/plans/shiftwork/evidence/slice25-live-<date>/` holding `once.marker`,
   `receipt.json` with the per-endpoint HTTP receipts and the `proof_scope`, `meter.json`
   with operations, calls and projected spend for each meter, `journey.db`, and the
   privacy receipt proving no credential value or private needle reached a response
   payload.

### 8.3 Credentials: `.env` works for scripts, not for the browser

`.env` is ignored by Git (`.gitignore:2-3`) and the S16 demo hand-parses it into
`os.environ` (`slice16_live_comparison.py:23-30`), so a `.env` file is safe and works for
a script-driven run. It is not enough for the browser journey: nothing under
`shiftwork/` loads `.env`, so `create_app` and the preview read only the real process
environment. Two acceptable paths, both requiring the values to stay out of the repo and
out of any log:

- export `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` in the shell that launches the run, or
- keep a file outside the repository, for example `~/.config/shiftwork/live.env` with
  mode 600, and `set -a; source` it before launching.

Either way the demo must never print, log or persist a value, and the response-payload
privacy check must include both values as needles.

### 8.4 Not yet done

The bounded demo itself is not written. It is new slice work and belongs on its own
branch with its own go-ahead, in the two-phase shape above, and the entitlement question
in the session handoff (whether the S12 project ID still returns Sandbox permissions)
is still open.

### 8.5 Blocker found by measurement on 2026-10-14: the live comparison cannot run

The entitlement preflight passed the same day (all six permissions true, exit 0, one
control-plane call, no spawn and no inference). New key, correct `aiproject-...` project
ID. While preparing the demo, a second check falsified decision 3's comparison stage.

`LiveComparisonBudget.preflight` requires exactly `slots == 6` and `requests == 18`, and
`comparison_flow.py:1322-1323` calls it with `slots=len(slots)` and
`requests=sum(slot.executed_request_count)`. Measured from the two recorded comparison
databases:

| Board | slots | executed requests per slot | sum | frozen requirement |
| --- | --- | --- | --- | --- |
| northline | 6 | 3 | 18 | matches |
| gtm | 6 | 4 | 24 | does not match |

In both boards the per-slot executed count is the manifest's declared `request_count`
plus one, so the frozen 18 is the Northline and Bellwether realized shape, not a general
one. The GTM comparison therefore calls a preflight that raises
`live comparison shape, model or rate ceiling is unverified`, and the reservation fails
closed before any spend. The frozen operation ceiling may bind as well: 6 slots at the
S22b ratio imply more than the 12 permitted operations, though that was not measured.

**Correction, 2026-10-14.** The sentence above attributing the GTM refusal to the
preflight is falsified and must not be relied on. `execute_comparison` refuses the
reservation earlier: the fresh-slot guard at `comparison_flow.py:1314-1321` pins
every slot to `request_count == 2` and `executed_request_count == 3`
(`comparison_flow.py:1317`), so the GTM reservation's recorded 3-and-4 slots raise
`live comparison reservation does not have six fresh bound slots`
(`comparison_flow.py:1321`), and the preflight call at `comparison_flow.py:1322-1323`
is never reached. The preflight's own `requests == 18` clause can never see 24 while
that pin stands, because six pinned slots always sum to 18. Reproduced 2026-10-14
against a copy of the recorded GTM journey database
(`evidence/slice25-live-2026-10-14/journey.db`): the guard raised at line 1321, a
preflight spy recorded zero calls, and slot execution never ran. The refusal still
fails closed before any spend, so the operations-only decision and the consequences
below are unchanged. A future widening of the frozen shape must change the per-slot
pins at `comparison_flow.py:1314-1321`, not only the preflight numbers.

The live operations are unaffected. The GTM operational workload is exactly one request
(`gtm-incident-001` in `fixtures/requests/gtm_pipeline_incident.jsonl`), which is what
`LiveOperationBudget` requires, so a live selected operation is runnable today under a
one-spawn one-call ceiling.

Consequence: the live arm as scoped in 8.2 cannot run end to end. Either the live stages
are reduced to the operations, keeping the comparison TRUSTED_LOCAL, or the frozen
comparison shape is widened for GTM, which changes a reviewed S16 and S22b control and
needs its own decision and review rather than a quiet edit. Nothing was spent.

Decisions taken 2026-10-14: the live arm is reduced to the **operations only**, with the
comparison, selection, close and inheritance staying TRUSTED_LOCAL, and the pinned
$0.06 and $0.24 rates are kept as a conservative upper bound after the vendor pricing
table could not be read. Two live operations project at $0.0044 in total. Both decisions
and the verbatim preflight output are recorded in
[evidence/slice25-live-2026-10-14/preflight.md](evidence/slice25-live-2026-10-14/preflight.md).
