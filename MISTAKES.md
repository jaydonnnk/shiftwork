# Mistakes Log

## 2026-10-20 S32 control servers: missing imports and middleware added after startup

- **What happened:** four scratch preview servers exited before serving. Three
  lacked `import sys`; the delayed server also registered `@app.middleware('http')`
  after `create_preview` returned. `create_preview` starts the app through
  `TestClient`, so Starlette rejected the late middleware. The driver reported
  only `preview exited with 1` until its preview log was read. A copied journey
  runner later hit the same missing `import sys`.
- **Root cause:** copied scratch scripts without re-checking imports and app
  lifecycle; assumed middleware could attach to an app already started by the
  preview factory.
- **Prevention rule:** before a scratch server batch, import-check and start each
  variant once and read its log on failure. Do not add middleware after
  `create_preview`; patch the run task or adapter with an explicit enable flag
  set after the app is built, and assert the anchor exists.

## 2026-10-20 S32 partial control: host discarded its consistent reference

- **What happened:** the partial consequence control intermittently recorded
  zero traces. Its publish log showed a reset followed by a conflict view
  carrying the new events while the scene remounted. The host cleared
  `previous` on reset and conflict and did not replay mount transitions, so the
  first linked view baselined the events and produced no arrival. Earlier runs
  passed only when no reset or conflict intervened.
- **Root cause:** treating a reset or conflict as a reason to forget the last
  consistent view instead of relying on `diffWorkplace`'s context, inspection
  and conflict guards, and mounting without applying transitions not yet seen.
- **Prevention rule:** retain the last consistent view across reset and conflict,
  advance it only on a consistent accepted view, and compute and apply
  transitions at mount. Fault each rule independently and repeat the real
  partial control, not once.

## 2026-10-20 S32 browser faults: stale anchor and non-distinguishing label

- **What happened:** after the host callback was gated on the scene starting a
  trace, the `operation-omit-arrival-callback` fault searched the old line, so
  the injected page failed to load instead of failing the named assertion. The
  `operation-omit-wall-label` fault survived because the idle label already said
  "Recorded evidence added"; removing the active text assignment was invisible.
- **Root cause:** changing an instrumented production line without updating the
  injection anchor, and using an idle message identical to the active message.
- **Prevention rule:** update every harness anchor with the instrumented line,
  make idle and active text distinct, and run each new fault row alone before
  the batch. Require the named AssertionError, not a load failure.

## 2026-10-20 S32 motion control: media emulation was not awaited

- **What happened:** the reduced-motion control started a trace after
  `Emulation.setEmulatedMedia` because publish ran before the media query and
  change listener reflected the emulation. The earlier test passed only because
  the scene did not apply the arrival at mount. Mount replay exposed the race.
- **Root cause:** treated a CDP command as synchronously effective for
  `matchMedia`.
- **Prevention rule:** after emulating reduced motion, wait until
  `matchMedia('(prefers-reduced-motion: reduce)').matches` reflects the requested
  value before publishing, then settle the scene before asserting.

## 2026-10-20 S32 bookshop journey: changed event row dropped a contract marker

- **What happened:** the new selected-evidence event row replaced
  `result ${check_id}` with `check ${check_id}`. The existing bookshop journey
  verifier required the `result` marker and failed. A copied journey runner also
  used the assist-enabled preview, so the standard denial check failed for the
  expected reason; the rerun used the plain preview.
- **Root cause:** treated a label change as cosmetic without rerunning the
  existing journey contract, and inherited the wrong preview mode in the
  scratch runner.
- **Prevention rule:** preserve every existing rendered contract marker or
  update its verifier deliberately, and run the bookshop journey after any
  selected-evidence change. Use the no-assist preview for the standard journey.

## 2026-10-02 S20 publication: checkout converted byte-hashed evidence endings

- **What happened:** the first post-merge preservation assertion failed for
  eight historical logs after Git's Windows checkout conversion. Six originally
  used LF; two mixed wrapper LF and native stdout CRLF. The command wrapper
  continued to a second check and returned its zero exit, and an uncommitted
  publication note prematurely said the hashes passed. No altered business
  record or failed live result was created. The note is corrected before commit.
- **Root cause:** byte-hashed evidence had no checkout-ending attributes, and
  the wrapper did not stop on the first verification failure.
- **Prevention rule:** pin byte-hashed transcript endings before switching Git
  branches. Restore only bytes verified against the prior manifest, and check
  every command's exit before writing dependent completion claims.

## 2026-10-02 S20 publication: unstaged diff checks omitted new evidence files

- **What happened:** readiness reported a clean `git diff --check`, but staging
  the previously untracked mutation transcripts exposed 49 trailing-whitespace
  diagnostics: 5 in the aborted SSE proof log and 44 in the completed round.
  The staged check exited 2. These are the original pytest traceback lines;
  the raw evidence is preserved. The check on every other staged file passed.
- **Root cause:** the unstaged check does not inspect untracked files, so its
  clean result was incorrectly treated as covering all publication files.
- **Prevention rule:** inspect untracked files and run the staged check before
  claiming publication-wide cleanliness. Report raw-transcript whitespace
  explicitly; do not reformat historical proof or call a scoped check universal.

## 2026-10-01 S20 demo proof: comparison included the evidence note wrapper

- **What happened:** the demo exited 0 with PASS_OFFLINE_POLICY and the expected
  JSON digest, while its wrapper check exited 1 because it compared that JSON
  line with the entire historical evidence note. Comparing the JSON line from
  both files confirms byte identity and digest `82c64ef9...`.
- **Root cause:** the comparison treated a recorded evidence note as raw stdout.
- **Prevention rule:** extract the same serialized surface from both artifacts
  before comparing bytes; report the command exit separately from its wrapper.
  A later read-only SQL probe also failed because shell-escaped double quotes
  broke its inline Python. Put nontrivial probes in a temporary .py file and
  bind SQL values instead of composing nested shell/SQL quoting. The corrected
  stored-record probe ran read-only and passed.

## 2026-10-01 S20 SSE proof runner: multiline anchors did not match CRLF source

- **What happened:** the targeted mutation runner caught its first fault, then
  stopped because its LF multiline anchor did not match the CRLF source. The
  finally block restored the original bytes. The aborted log is preserved and
  the corrected round uses a new log path.
- **Root cause:** single-line anchors matched raw decoded bytes, masking the
  newline mismatch until the first multiline anchor.
- **Prevention rule:** normalize newlines for mutation matching, retain original
  bytes for restoration, and verify the before/after digest. A partial round is
  not a passing round. Test stream fixtures must yield real events after their
  delay, so old behavior fails the intended deadline assertion, not an
  incidental AttributeError from a yielded None.

## 2026-10-01 S20 live chain: the comparison died on an SSE server-error frame the adapter cannot resume

- **What happened:** the single authorized live attempt completed four of six
  comparison slots, then slots 5 and 6 failed `PROVISION_FAILED` in their
  public phases. The preserved observations show both ended on a server-sent
  SSE `sse_error` frame, which `contree_client` surfaces as a builtin
  `ConnectionError` while the controller polls the operation event stream
  around the second request of the public batch. The vendor's own
  `iter_operation_events` documentation defines that frame as an in-band
  stream break to be handled with a brief wait and a Last-Event-Id reconnect,
  and the client's sync `follow_operation_events` implements exactly that; the
  controller adapter's catch-all classifies it as a fatal provisioning
  failure, abandons the operation to its cancel path and records only the
  exception type, so the server's one-line message and the resume event id are
  lost. One inference call that the provider answered before the stream broke
  left no persisted observation row (meter count 8, persisted rows 7).
- **Root cause:** the adapter treats every event-stream break as terminal
  instead of implementing the documented resume, and its failure observation
  discards the exception detail that a later read needs to diagnose the
  server side.
- **Prevention rule:** when a client library documents a resume protocol for an
  error frame, treat that frame as retryable control flow, not a fatal adapter
  error; every typed failure observation should retain a bounded excerpt of
  the exception message in the internal raw payload (never the public
  projection) so a failed run can be diagnosed without another live call.

## 2026-10-01 S20 chain runner: the local executor produced backlog events where the recipe said incidents

- **What happened:** the first offline rehearsal of `demos/slice20_live_chain.py`
  failed at its Phase A assertion "the starter operation should open incidents
  and complete no sale". With `executor="local_process"` (as the stretch handoff
  described), the fresh shift's starter run executes the legacy attempt batch
  `bookshop_attempt_01.jsonl` (a legacy stimulus without `request_id` or
  `entity_ref`), the pinned pivot starter answers HTTP 400, the legacy family
  checks record `MALFORMED_RESPONSE`, and the reducer writes three
  `BACKLOG_RECORDED` events instead of `INCIDENT_OPENED`. With the controller
  default executor `recorded` (what `demos/final_pivot.py` uses), the same run
  replays the reviewed S11 transcript and opens the three incidents, matching
  the recorded S20 demo evidence.
- **Root cause:** the executor was copied from the handoff text instead of
  reproduced from the flow: the handoff's stated expectation (incidents opened)
  and its stated executor (local_process) are mutually inconsistent, and only
  a real run can say which one is right.
- **Prevention rule:** before writing a flow assertion, reproduce the step under
  each candidate configuration with one throwaway run and derive the expectation
  from the observed evidence; when a handoff's expectation and its mechanism
  disagree, keep the expectation its recorded evidence proves.

## 2026-10-01 S20 stretch: test slips and a wrong-type meter crashed a guard

- **What happened:** three slips in the new live-operation tests and one in the
  code they exercised. (1) A test asserted `run.failure`; the frozen `Run` model
  field is `failure_kind`, so the assertion raised AttributeError. (2) The
  operation-spend preflight test set a $1 per-million rate and expected a spend
  refusal, but one call reserves only 32,768 tokens, so its projection cannot
  cross $0.10 below about $2.96 per million and the refusal never fired. (3) The
  first live-operation guard called `live_budget.preflight(...)` on whatever
  object it received, so a comparison-shaped meter (different signature) raised
  TypeError and crashed the run instead of failing it closed; an isinstance gate
  now marks the run FAILED PROVISION_FAILED.
- **Root cause:** field names and arithmetic expectations were written from
  memory of sibling code instead of the models and constants, and the guard
  assumed its caller's type instead of gating it.
- **Prevention rule:** derive assertion inputs from the models and constants
  (read the model field, compute the projection) before writing the assertion;
  a controller guard that receives an object must type-gate it and fail closed
  on any mismatch, so no wrong type ever crashes a run.

## 2026-10-01 S20 review: a demo boolean that could never be false

- **What happened:** the independent S20 review found `prior_bytes_identical` in
  `demos/final_pivot.py` computed from `all(appended.get(table, 0) >= 0 ...)`.
  The appended counts come from a loop that already asserted every table's byte
  prefix is unchanged, so each count is structurally >= 0 and the expression
  could never be false. The demo printed a byte-identity claim that no input
  could contradict.
- **Root cause:** the flag was derived from the counts the loop happened to
  compute instead of from the prefix comparisons themselves, and no one named an
  input that should make it False.
- **Prevention rule:** for every boolean a report, demo or gate prints, name the
  measured inputs that can make it False and derive the value from those inputs.
  A condition true in every reachable state is a restatement of the control
  flow, not evidence.

## 2026-10-01 S20 review: the record stated a mechanism and an attribution its captured evidence contradicts

- **What happened:** the S20 status entry claimed the S18 flake died because
  `_comparison`'s 90-second poll expired under load; the captured run shows the
  failure at `test_selection_operation.py:73` with `INCOMPLETE == COMPLETE` in a
  19.53s run, so the poll (line 67) cannot have expired. The same entry credited
  the Next-station history/experiment separation to a client-shell pin that only
  asserts attribute presence; the separation is proved by the browser
  `inheritSeparation` fault instead.
- **Root cause:** the mechanism was written from the shape of the failure rather
  than from the captured bytes, and a coverage attribution was carried over from
  an earlier draft without checking what the cited test actually asserts.
- **Prevention rule:** every mechanism or coverage sentence in an evidence
  record must cite the artifact that demonstrates it and name what would fail if
  the claim were wrong; re-derive the sentence from the cited evidence, never
  from the failure's appearance or an earlier round's prose.

## 2026-09-30 S18 mutation classifier missed bare pytest assertions

- What happened: the first stricter mutation run called six rows UNPROVEN even
  though their named tests failed at bare `assert` statements. Its 8-of-14
  summary was a classifier error, not a proof of eight remaining guards.
- Root cause: the harness recognized `AssertionError` and `DID NOT RAISE` but
  omitted pytest's common `E   assert ...` failure format.
- Prevention rule: classify bare asserts as assertion failures, require each
  mutation's expected assertion text and print the observed assertion. Do not
  count an incidental production exception as an assertion-level catch.

## 2026-09-29 S17 stale station label and ambiguous test patch

- What happened: the service station's activation handler overwrote the new
  selected-version label with the latest saved version and called it a baseline.
  A later test edit also placed failed-comparison assertions inside another
  test's `finally` block; inspection caught that before a run.
- Root cause: I changed one render path without checking the second writer, and
  used a patch anchor that matched a generic `finally` block.
- Prevention rule: search every writer of a changed UI label and inspect the
  rendered result; use function-specific patch context and read the edited
  block before testing.

## 2026-09-29 S17 Compare panel crashed before the first board load

- What happened: the browser check stayed in `loading` because `renderCompare()`
  treated two absent optional IDs as an existing selection, then read a property
  from the null board. The browser's page exception identified the line.
- Root cause: optional chaining returned `undefined` for both values, and
  `undefined === undefined` was true.
- Prevention rule: when comparing optional IDs for identity, require the owning
  object to exist before comparing. Exercise the initial empty render in the
  browser, not only the loaded state.

## 2026-09-28 Slice 15 render-fault run could not tell its preview from a foreign server

- What happened: the first `render_faults.mjs` run after the protected-phase
  client change reported `0 of 12 as expected`; every row failed at page load
  with `Expected ready, got undefined`. The preview script prints its banner
  line before uvicorn binds the port, so a port already held by another local
  application is indistinguishable from a healthy preview at start time, and
  the browser talks to whatever answers. A foreign app (an unrelated
  WorkBuddy/CareRelay service) was found listening on the fixed default port
  8137 minutes later; the same checks pass against a manually started preview
  and on a free port.
- Root cause: the harness treated the banner line as proof of reachability, and
  the fixed default port let a collision with an unrelated local application
  misattribute every row's failure to the product.
- Prevention rule: after spawning a server whose banner precedes its bind,
  poll that server's own endpoint until it answers before running any check
  (now `waitReachable()` in `render_faults.mjs`), and run preview checks on a
  port verified free when the default is in doubt; a port collision is a
  harness-environment failure, never a red product row.

## 2026-09-28 Slice 15 compare-demo harness kept the pre-protected copy assertion

- What happened: the first `--compare-demo` run after the protected-phase round
  exited 1 at `Slot 1 renders the wrong frozen batch size`. The slot row copy
  had changed to `N public requests + M protected steps`, while the harness
  still asserted the old `N request` substring, so the assertion could no
  longer match a correct render. The harness was updated to the rendered copy
  and gained a protected-step limb with its own served-source fault row
  (`slotProtectedCount`); the rerun passed.
- Root cause: the client copy changed during the protected-phase round without
  its browser assertion being updated in the same change, and the browser check
  was deferred, so the staleness surfaced only when it was finally run (the
  same client-untested-with-shell-contract pattern as the 2026-09-26 Slice 11
  entry).
- Prevention rule: when a client rendering change alters value-bearing copy
  that a browser assertion reads, update that assertion and add its fault row
  in the same change; run the browser check before claiming the tree complete
  rather than leaving it as a pending item across a round boundary.

## 2026-09-28 Slice 15 protected-phase guards masked four older proof rows

- What happened: the protected-phase round added a cluster of guards on the
  comparison path (a frozen context-hash re-verification, a protected-ordinal
  tie, a readback that raises on a missing snapshot) and rebuilt its own proof
  rows, but the first full run under the hardened driver found four older rows
  had silently lost proof-grade status: the snapshot write-removal row was
  `CAUGHT_INCIDENTAL` (the reservation readback raises `InvalidSealedCase`
  before any assertion), and the manifest count row and both slot-binding rows
  were `NOT_CAUGHT` (the frozen context-hash re-verification catches every
  context tamper globally, and the count tamper also trips the protected-ordinal
  tie). Focused per-round checks had stayed green because each row still ran.
- Root cause: a new guard placed earlier in a shared path changes which
  mechanism catches an old row's tamper; the row's named assertion no longer
  observes anything, and a focused run cannot distinguish a row that proves its
  guard from a row whose tamper is caught elsewhere.
- Prevention rule: after adding a guard on a path that existing rows anchor
  onto, re-run the full harness on the settled tree and treat any previously
  green row that flips to `NOT_CAUGHT` or `CAUGHT_INCIDENTAL` as masking to be
  re-anchored. Re-anchor the row onto its own guard's limb with a tamper that
  only that limb catches (here `[slot_hash]` for the slot binding,
  `[extra_request_with_recomputed_pin]` for the count check and
  `[wrong_request_id_with_recomputed_pin]` for the request-line identity), and
  give the masking guard its own row so it is proven too.

## 2026-09-28 Slice 15 two proof shapes measured unprovable

- What happened: repair attempts produced two fault shapes that cannot reach an
  assertion-level catch. (1) A remove-the-write mutation for the protected-case
  snapshot write reads as the reservation readback's `InvalidSealedCase` under
  every reachable shape (`CAUGHT_INCIDENTAL`), so no assertion observes the
  write. (2) The slot-count limb
  (`workload.request_count != slot.request_count`) has no failing-capable
  tamper: with the limb removed, the `[slot_count]` update is caught only by
  the comparison view's private-material guard raising `LifecycleError`
  ("public comparison evidence contains private material", measured
  `CAUGHT_INCIDENTAL`). (3) The original count-check tamper
  (`wrong_claimed_count`) set `request_count` to 1, which trips both the
  recomputed count check and the protected-ordinal tie, so it could prove
  neither.
- Root cause: each shape was chosen for what it removes, not for the unique
  divergence it produces; overlapping guards meant the tamper's first
  observable failure was never the limb under test.
- Prevention rule: before claiming a row, construct the tamper so the limb
  under test is the only reachable divergence (recompute every other pin, keep
  every other check satisfied) and measure the candidate shape; when a removal
  stays green or turns incidental, record the limb as unproven (or retire the
  row onto a provable limb) instead of counting the red run as coverage.

## 2026-09-28 Slice 15 mutation run crashed at row 95 and left a stranded mutation

- What happened: the 96-row mutation proof run crashed while restoring
  `shiftwork/orchestrator.py` after the `s15_protected_counts_before_terminal`
  row: `OSError: [Errno 22] Invalid argument` on the restore write. The mutated
  file stayed on disk (the mutation is valid Python, so it still compiled), and
  because stdout was block-buffered into a redirected log, the crash discarded
  every completed row's output, so the run produced no usable result table. The
  stranded mutation was found by re-running the anchor check over all 96 rows
  (exactly one anchor broken), reverted byte-precisely, and the focused tests
  passed again.
- Root cause: two compounding hazards. (1) a Windows write to this
  OneDrive-synced tree can transiently fail with `EINVAL`, and the shared
  runner's restore has no retry, so the row's own `finally` died. (2) the
  runner prints per-row progress with `end=" "` and the final table only; when a
  crash happens mid-list, buffered per-row evidence is lost along with the run.
- Prevention rule: run the mutation harness with per-row flushed output and a
  results file appended after each row, so any crash preserves the completed
  rows and names the failing one. After a crashed or interrupted run, never
  trust the tree: re-check every row anchor against the working tree, compile
  every target, revert the identified stranded mutation byte-precisely, and
  treat the run as not a pass.

## 2026-09-28 Slice 15 reservation fault test assumed the wrong SQLite error class

- What happened: the new fault test correctly reached the reservation-link
  UPDATE but failed because the SQLite trigger raised `IntegrityError` while
  the assertion expected `OperationalError`.
- Root cause: the test assumed all injected database faults share one SQLite
  exception subtype, despite `RAISE(ABORT, ...)` using an integrity error.
- Prevention rule: match the distinctive injected message and the `sqlite3.Error`
  family when the proof spans both Python-raised and trigger-raised faults.

## 2026-09-28 Slice 15 execution claim: stale fault and mutation targets

- What happened: after moving the comparison's `RUNNING` transition from
  reservation to the worker claim, the focused suite still injected a fault
  into the removed reservation-time state update and failed. The first mutation
  run also had one exact-byte anchor that no longer matched mixed line endings
  and one `expect` field written as an assertion message instead of a test ID.
- Root cause: I changed the write boundary without updating its fault target
  and proof metadata in the same edit, and I did not inspect the mutation
  runner's exact-byte and test-selector rules before editing the rows.
- Prevention rule: when moving a durable write across a lifecycle boundary,
  remap its fault injection to a real write at that boundary and remeasure the
  source bytes used by mutation anchors. The runner's `expect` names the
  failing test, not the message. Run the full proof and retain its exit status.

## 2026-09-27 Slice 15 browser proof: a wait condition true on the initial render hides a swallowed click

- What happened: `node tests/client/browser.mjs ... --compare-demo` exited 1 with
  `CDP timeout: Runtime.evaluate`. Byte-level instrumentation of the page function
  showed `wait('candidate A freeze')` returning at 0.00s while the candidate list
  still read `not frozen yet`: its condition `textContent.includes('Candidate A')`
  is true from the first render, and `'Candidate A\nnot frozen'` never matches
  because the row renders `Candidate Anot frozen yet`. The script therefore clicked
  freeze B while `state.pending` had disabled the button; the click was swallowed and
  candidate B never froze.
- Root cause: the wait asserted a substring the initial render already satisfies
  instead of the state the click is supposed to produce. A wait that can pass before
  its action completes is not a wait.
- Prevention rule: a wait condition must be false immediately before the action it
  follows and true only after that action's rendered effect; read the initial
  render's text before choosing the condition. Gate every click on the control being
  enabled, and make each in-page wait name its own limb when it times out.

## 2026-09-27 Slice 15 browser proof: a transport timer shorter than the page deadline replaced the real error

- What happened: the harness's CDP send timer (20s) fired before the page function's
  own 60s polling deadline, so three separate page-level defects all reported the same
  opaque `CDP timeout: Runtime.evaluate`; the last written screenshot was the only
  clue to where execution stopped.
- Root cause: the transport backstop was shorter than the longest in-page deadline, so
  the transport always failed first and hid the page's own error message.
- Prevention rule: a transport-level timeout must be strictly greater than the longest
  deadline of any page function it awaits (now `CDP_TIMEOUT_MS = 90000` against a 60s
  in-page ceiling). When a timeout message names only the transport method, treat the
  real error as hidden and instrument the page function before choosing a fix.

## 2026-09-27 Slice 15 browser proof: rendered rows matched on an identity that duplicates

- What happened: after the first two repairs the run failed `Slot 1 task row does not
  match the API payload for alternative`. A two-request workload assesses each task
  once per request, so `task_id='alternative'` appeared twice with the same verdict
  (`pass`) and different outcomes; the finder matched task_id plus verdict and
  returned the ordinal-1 row for both payload entries.
- Root cause: the rendered row's identity (task_id + verdict) was not unique for the
  data it displays. The diagnostic path assesses one pinned request per task, so the
  collision never appeared there.
- Prevention rule: before matching rendered rows to payload entries, check that the
  payload's identifying keys are unique per row for the widest input the surface
  accepts (here more than one request per workload), and expose any missing key as
  both a dataset attribute and displayed text so each limb is failing-capable.
## 2026-09-27 Slice 14: live assist probe used a mismatched investigation

- What happened: all three authorized live assist calls used a source request about Dune shelf availability, while the submitted learner cause asserted a price, collection and alternatives failure. The model repeated or expanded the unsupported tasks.
- Root cause: I copied a generic test investigation into the live probe without first reading the chosen recorded request and response.
- Prevention rule: before spending an authorized live-call budget, read the exact source request and capture, then write a probe investigation about that evidence; keep model agreement with a bad premise as a separate quality finding.

## 2026-09-27 Slice 14: assist test expected the wrong run status

- What happened: the first assist suite stopped in setup because POST runs returned 202 Accepted and the new fixture asserted 201.
- Root cause: I assumed the route's status instead of checking the existing API contract before writing the fixture.
- Prevention rule: read the route's declared status or reproduce it in a small request before asserting it in a new integration fixture.

## 2026-09-27 Slice 14: gateway unit test kept an invalid role argument

- What happened: after the gateway began enforcing the AssistRole enum, its direct-call test still passed a string and failed with ASSIST_ROLE_INVALID.
- Root cause: I tightened the gateway contract without updating the direct test call in the same edit.
- Prevention rule: when adding an input type guard, update direct callers and add a separate test that the rejected type actually fails before any transport call.

## 2026-09-27 Slice 14: old absence guards failed after the assist package landed

- What happened: the offline suite reported two failures because Slice 6 guards still asserted that shiftwork/assist did not exist.
- Root cause: I added the new package before replacing the deferred import and prompt arms with tests against the real S14 surfaces.
- Prevention rule: when a deferred directory or route lands, find its absence guards in the same edit and replace them with non-vacuous tests that inject a detectable fault.

## 2026-09-27 Slice 14: reply metadata changed positional argument meaning

- What happened: adding reported-model metadata made two recorded test replies pass a numeric token count as the model ID. The tests still passed because they asserted other fields.
- Root cause: optional metadata fields were positional in a dataclass that grew during implementation.
- Prevention rule: make optional reply metadata keyword-only and name token counts explicitly in test fixtures.

When a coding error occurs, log it below with: what happened, root cause, and prevention rule.
When a failure pattern repeats 4+ times, graduate it into a permanent rule in `agents.md`.

---

## 2026-09-16 — Gate 4 slice plan mapped tests by number, not by clause

- **What happened:** `04-slices.md` marked tests 9, 10, 18, 23, 44 and the prompt/assist
  arms of 16/17 as fully "landed" in slices where some of their specified assertions
  cannot execute yet (e.g., test 9's reservation-retention clause needs `rotation_draws`,
  which lands two slices later), and orphaned three clauses of test 41. Caught by the
  user-requested independent review (verdict: REVISE — GATE 4), not by my own checks —
  my coverage check counted test numbers, not clauses.
- **Root cause:** I verified coverage at the test-number level ("all 49 appear in some
  slice") instead of decomposing each test specification into its assertion clauses and
  checking that every clause's prerequisites (tables, modules, flows) exist in the slice
  where it is claimed.
- **Prevention rule:** when mapping a numbered test/spec plan onto slices or milestones,
  enumerate each test's individual clauses and verify each clause's dependencies exist at
  the claiming step; annotate partial landings explicitly ("partial: X clause completes at
  step N") and name the step that completes every partial. A count-level coverage check is
  not sufficient evidence of coverage.
## 2026-09-17 — Clause-level coverage repair verified only the clauses a reviewer named

- **What happened:** after the first Gate 4 review fixed the named partial-landing
  tests, both the drafter's repair and the reviewer's re-check missed test 18's
  "absent from every prompt" arm (still orphaned), test 43's ledger-resolution
  clause and test 44's evaluator-rule clause (claimed while those layers were
  mocked). A second cold review caught all three, plus two real Gate 3 defects
  (test 33 close-semantics ambiguity; no test for Test 1's credential-reachability
  kill condition) that two prior review rounds had passed.
- **Root cause:** the repair and its verification were scoped to the findings list
  instead of re-decomposing the full specification text of every affected test and
  every kill condition; "previous reviewer passed it" was treated as evidence.
- **Prevention rule:** when annotating partials or verifying a coverage repair,
  re-decompose the FULL spec text of every annotated test (and every kill condition
  of every proof) at both the claiming and the completing step — not only the
  clauses a reviewer named. A prior PASS is not evidence for clauses it never
  enumerated. (Second occurrence of the clause-mapping pattern; at 4 occurrences
  graduate into agents.md.)
## 2026-09-17 Slice 1 test 51: logged a transient, unreproduced OS-policy block as a standing fact

- **What happened:** the Slice 1 evidence note and this log recorded that test 51's
  stdlib-venv path "is blocked on this machine by Windows Application Control
  (WinError 4551)" and that the test "exercised its uv fallback." A re-run on
  2026-09-17 (`pytest tests/packaging -q -s`) printed `clean-env mechanism:
  stdlib venv + pip` and `1 passed in 21.47s`, and a direct probe of a freshly
  created stdlib venv returned exit 0. The stdlib path works and is selected; the
  uv fallback never ran. An independent review caught the false claim, not my own
  checks.
- **Root cause:** I recorded a single transient `WinError 4551` observation as a
  durable machine property, and asserted which code path executed without
  capturing the test's own `clean-env mechanism:` line. The note also contradicted
  itself: "no install ran this session" alongside "test 51 passed," when test 51
  performs a clean-env install into a fresh temp venv by construction.
- **Prevention rule:** when an evidence note states which mechanism, branch or
  fallback ran, quote the program's own verbatim output (the mechanism line and the
  pass/skip/fail count) instead of inferring it. Treat a one-off OS or policy error
  as transient until reproduced; never log it as a standing property. A test that
  installs into a fresh environment is an install: do not write "no install ran" in
  the same note that records it passing. Packaging checks may still probe a fresh
  interpreter and keep a uv fallback for genuinely blocked machines, but record the
  fallback as exercised only when the probe actually failed.
## 2026-09-18 Slice 2 evidence note asserted a runtime shiftwork.db that never existed

- **What happened:** the Slice 2 evidence note recorded "the runtime `shiftwork.db` were
  left untouched" and described "a stale git-ignored dev `shiftwork.db` left at version
  1", implying an existing file. No `*.db` file exists anywhere in the tree or in git
  history, and none was created; the demos and tests point `create_app` at temp paths.
  An independent hostile review caught it, not my own checks.
- **Root cause:** I wrote a file-state claim from assumption instead of running a check;
  no command output backed the existence claim, and guard behavior ("a database left at
  version 1 raises ...") was allowed to read as an observed file.
- **Prevention rule:** every file-state claim in an evidence note ("exists", "left
  untouched", "pre-existing", "created") must be backed by the command that shows it
  (`git status --porcelain`, `find . -name '*.db'`, `git ls-files`). When the evidence is
  a counterfactual guard, say the database was constructed for the check. Second
  occurrence of the unverified-state-as-fact pattern (first: the 2026-09-17 WinError
  4551 entry); at 4 occurrences graduate into `agents.md`.

## 2026-09-18 Slice 3: environment trap broke the test runner

- **What happened:** the first executor suite ended with `8 failed, 17 passed, 1 skipped, 11 errors in 17.62s`; the recorded-adapter test replaced global `os.environ` while asyncio created its loop and pytest reported results, causing `TypeError: 'types.SimpleNamespace' object is not subscriptable` and masking conformance diagnostics.
- **Root cause:** a process-global fault injection outlived the boundary under test, and the replacement did not implement the mapping protocol.
- **Prevention rule:** create framework resources before a global trap, scope the trap to the adapter call with guaranteed restoration, and restore normal state before framework teardown or reporting.

## 2026-09-18 Slice 3: fixture log bytes depended on Windows newline translation

- **What happened:** the isolated conformance check reported `1 failed, 1 passed in 1.09s`; live logs were `b'trusted fixture ready\r\n'` while the authored transcript pinned `b'trusted fixture ready\n'`.
- **Root cause:** the fixture used text-mode stderr without pinning newline encoding, so the OS changed the emitted bytes.
- **Prevention rule:** fix fixture output encoding at the producer; preserve captured bytes and exact-equality assertions rather than normalizing away evidence differences. Recompute fixture pins only after reviewing the producer change.

## 2026-09-18 Slice 3: refusal fixture deadline expired before Winsock refused

- **What happened:** executor checks reported `2 failed, 28 passed, 1 skipped in 17.87s`; port-dead and connection-refused cases timed out instead of observing refusal.
- **Root cause:** their 2-second whole-run deadline was shorter than the measured OS refusal delay. A direct 8-second-timeout loopback probe printed `bound_not_listening ConnectionRefusedError winerror= 10061 elapsed_ms= 2047` and `closed ConnectionRefusedError winerror= 10061 elapsed_ms= 2014`.
- **Prevention rule:** separate the deliberate timeout case from refusal tests; allow refusal tests enough time to observe the real socket error. Keep typed expectations unchanged and retain a short real deadline for the timeout case.

## 2026-09-18 Slice 3: trusted sources hidden by a build-output ignore rule

- **What happened:** `git check-ignore -v shiftwork/fixtures/artifacts/bookshop/service.py` printed `.gitignore:23:artifacts/\tshiftwork/fixtures/artifacts/bookshop/service.py`; the new executable fixtures existed locally but were absent from the reviewable untracked-file inventory.
- **Root cause:** the pre-existing unanchored build-output rule also matched the approved source-fixture directory.
- **Prevention rule:** check ignore status for new source directories and add a narrow source exception before treating the diff as reproducible.

## 2026-09-18 Slice 3: snapshot pin depended on pre-checkout CRLF bytes

- **What happened:** the checkout-format regression printed `1 failed in 0.83s`; the byte probe found `thin_stale.json` and `bookshop_snapshot.json` still using CRLF. The snapshot's current hash was `ad18bf6fce6b2742b963d728ce60b0988b4d954b903d638cb1777ec7c42cdf12`, but the declared LF checkout would hash to `bd66a4136c8dc1156ff50645195d437328cb3ea18206be9eba976d3ea168933f`.
- **Root cause:** exact-byte pins were computed before aligning existing fixture files with the new `.gitattributes` LF rule; local green tests did not prove checkout reproducibility.
- **Prevention rule:** assert byte-addressed source files already use their declared checkout newlines before freezing hashes; correct source bytes and explicit pins, never normalize captured response evidence.

## 2026-09-18 Slice 3: replay trusted contradictory transport metadata

- **What happened:** the adversarial review reproduced a replay with no HTTP status reaching FINALIZED and a ledger event; unmarked non-UTF-8 bytes instead reached evaluation, raised and lost their captured evidence on rollback. Invalid log base64 and conflicting failure kinds were also accepted.
- **Root cause:** request/snapshot hashes and capture order were checked, but transport metadata was trusted independently of body/log bytes and run failure state.
- **Prevention rule:** test malformed replay metadata as well as golden transcripts; validate transport consistency before success and retain unmarked non-UTF-8 bytes through the typed executor-failure path, never business evaluation.

## 2026-09-18 Slice 3: migration DDL committed before its version marker

- **What happened:** a review probe denied the version-write statement after adding `log_ref`; reopening left schema version 2 with the new column, and the next startup failed with `duplicate column name: log_ref`.
- **Root cause:** SQLite committed the ALTER TABLE independently because no explicit transaction enclosed both the DDL and schema version update; the original test covered only uninterrupted repetition.
- **Prevention rule:** commit migration DDL and its version marker atomically; inject a failure between them, reopen the database and assert unchanged data plus a successful retry.

## 2026-09-18 Slice 4 sealed family enforced a freshness limit no learner-visible artifact stated

- **What happened:** the `stale_information` evaluator keyed its stance failures off
  `max_record_age_ms`, `stale_assert_kinds` and `high_risk_kinds` stored only in the
  sealed case block. Failing-transcript request 1 answered from the newest Dune
  record with its true age (90 minutes), exactly what the committed
  `USE_NEWEST_RECORD_WITH_AGE` label instructs, and was still scored
  `fail/STALE_BEYOND_RULE` against a hidden 3600000 ms limit. An independent
  execution review caught it (MAJOR-1); the family could not be sealed until the
  user chose a fix route (catalog v2 whose labels state the constants).
- **Root cause:** I treated the sealed `expected` block as a free parameter bag, so
  rule constants that change verdicts lived outside every learner-visible artifact,
  contradicting the approved rule that sealed cases check consistency with the
  learner's chosen option (03-program-design S3.2). The Slice 2 case note had
  attributed the limit to "the contract selected"; the six-case reshape dropped the
  attribution without noticing the number had no visible owner.
- **Prevention rule:** every sealed-case parameter that can change a verdict must be
  stated in a learner-visible artifact (catalog label, contract, snapshot) or be
  derived from one; keep rule constants in the visible artifact and pin them with a
  guard test (`test_v2_labels_declare_the_rule_constants`,
  `test_sealed_expected_blocks_carry_no_rule_parameters`).

## 2026-09-18 Slice 4 probe injection silently no-opped on CRLF worktree bytes

- **What happened:** to prove the revised test 11 closure scan was failing-capable, I
  injected `import socket` into `domain/canonical.py` with a byte replace on
  `b"import base64\n"`. The tracked file's worktree bytes are CRLF
  (`core.autocrlf=true`), so nothing was replaced and the probe ran green; the
  helper's "probe injected" line had been printed unconditionally. The mismatch
  surfaced when the probe removal also failed to match; I re-ran the probe with
  verified bytes and captured the real failure.
- **Root cause:** the probe asserted neither the mutated bytes nor the expected
  failing behavior, and its success message was not derived from the observed state.
- **Prevention rule:** a mutation probe must verify the mutation landed (bytes or
  behavior) before its result is trusted, and it must print the observed state, not
  a constant. On this machine, tracked-file worktree bytes are CRLF, so byte-level
  edits, pins and probes must match `\r\n` or normalize explicitly.

## 2026-09-18 Client visual brief patch omitted an added-line marker

- **What happened:** the first combined `apply_patch` call failed validation before
  changing any file because one wrapped line in the new-file hunk did not begin with
  `+`.
- **Root cause:** a large multi-file patch was assembled as one string without first
  checking every line of the add-file section for a patch marker.
- **Prevention rule:** create new files in a separate patch, keep multi-file patches
  small, and verify every line in an add-file hunk begins with `+` before applying it.

## 2026-09-18 Slice 5 test 6 claimed FULL while the linkage clause was not failing-capable

- **What happened:** the Slice 5 evidence claimed test 6 FULL for "every tamper
  (payload, hash, prev_hash, seq, reorder) is BROKEN", but the independent review
  removed `verify_chain`'s prev-hash linkage check (`chain.py:88-89`, byte-verified
  mutation) and the test still passed: the prev_hash tamper case is caught by hash
  recomputation (the digest covers prev_hash), so the load-bearing linkage check had
  zero failing-capable coverage. The reviewer proved linkage is load-bearing with a
  forged-but-self-consistent spliced event that only linkage catches.
- **Root cause:** clause coverage was claimed per named tamper input, not per
  verifying code path; two independent checks can catch the same injected fault, and
  a mutation probe on only the producer side (`append`) left the verifier clause
  unprobed. Third occurrence of the count-level-not-clause-level pattern
  (2026-09-16, 2026-09-17, this entry); at 4 occurrences graduate into `agents.md`.
- **Prevention rule:** when a test asserts a guard fires, mutate EACH guard branch
  independently and require a failure per branch; a tamper input that two checks can
  catch proves neither. For hash-chain verifiers, include a forged-but-self-consistent
  splice case alongside field-tamper cases.

## 2026-09-18 Slice 5 status claimed a per-run snapshot pairing that does not exist

- **What happened:** the Slice 5 evidence note said `finalize_run` "evaluates against
  the snapshot the run consumed". The independent review found no pairing mechanism:
  `finalize_run` reads the module global `config.BOOKSHOP_SNAPSHOT`, `execute_run`
  hardcodes the same constant into `shop_snapshot_ref`, and `Run` has no snapshot
  field. The actual fix shipped was making test/demo inputs cite that snapshot's
  records. A latent bug follows: a run consuming `bookshop_stale_snapshot.json` would
  finalize against the wrong snapshot.
- **Root cause:** the note described the intended invariant instead of the mechanism
  in the code; no read of `finalize_run`'s inputs backed the "the run consumed"
  phrasing. Third occurrence of the unverified-state-as-fact pattern (WinError 4551,
  Slice 2 runtime-db claim, this entry); at 4 occurrences graduate into `agents.md`.
- **Prevention rule:** evidence notes must describe the code path that exists
  (name the constant, field or function actually used), not the invariant it
  happens to satisfy today; when inputs coincide by configuration rather than by
  mechanism, say so and record the decoupling as a latent-bug note.

## 2026-09-18 Slice 6 host-path leak scan could never match the surface it scanned

- **What happened:** test 20's host-path needles were raw Windows absolute paths
  (`str(config.BOOKSHOP_SNAPSHOT)`, the package dir, the interpreter path), but a
  FastAPI JSON response backslash-escapes them (`C:\\Users\\...`), so
  `needle in surface` never matched. Six of the eight needles were vacuous and the
  test passed against a real leak: mutation probe 20b wired
  `str(config.BOOKSHOP_SNAPSHOT)` into a projected `request_text` and test 20 stayed
  green. Only test 45 caught it, and only because it also carried a
  backslash-free marker token. My own non-vacuity checks passed, because they
  counted surfaces scanned rather than proving any needle could match.
- **Root cause:** I wrote the absence assertion against the in-memory value without
  checking how that value is serialized on the surface being scanned, and I treated
  "the scan covered N surfaces" as evidence that each individual needle was capable
  of failing.
- **Prevention rule:** every absence/leak assertion needs a scanner self-test that
  injects the needle into a representative serialized surface and requires
  detection; a count of surfaces scanned is not evidence that a needle can match.
  Compare against the surface's serialized form, not the in-memory value. Fourth
  occurrence of the coverage-claimed-not-proven pattern (2026-09-16 clause mapping,
  2026-09-17 repair scoping, 2026-09-18 Slice 5 guard branches, this entry), so it
  is graduated into `AGENTS.md` S6 Verification. The graduated entries are kept
  here as incident history, per the AGENTS.md mistake-logging rule (user decision,
  2026-09-19).

## 2026-09-19 Slice 6 repair fixture written with CRLF by write_text

- **What happened:** the new `missing_evidence` transcript fixture was written with
  `Path.write_text` on Windows, which translated `\n` to `\r\n`; the LF-pinned
  fixture check in `tests/executor/test_conformance.py` failed on it.
- **Root cause:** text-mode writes on Windows apply `os.linesep` translation, and
  the repository pins fixture files as LF bytes.
- **Prevention rule:** write byte-pinned text fixtures with `write_bytes(...)` or
  `write_text(..., newline="\n")`, never default `write_text`, on Windows.

## 2026-09-19 Slice 6 review round: a self-test parametrized by the constant it tests

- **What happened:** the new UTF-16 decoder self-test was parametrized over
  `BASE64_DECODINGS`, the same constant it exists to guard. My failing-capability
  probe narrowed that constant to `("utf-8",)` and the probe reported
  `1 passed`: the utf-16 cases had disappeared instead of failing. The guard was
  vacuous for exactly the inputs it claimed, and only the probe's own expectation
  (a passing probe is a red flag) exposed it.
- **Root cause:** the test's input list came from the implementation artifact rather
  than from the requirement, so weakening the implementation weakened the evidence
  in the same step. Same class as counting surfaces scanned instead of proving a
  needle can match (the graduated AGENTS.md S6 rule).
- **Prevention rule:** a failing-capability check enumerates the requirement's
  literal inputs (the three encodings), never a constant read from the code under
  test, and asserts each input is still covered; when a mutation probe passes,
  treat the probe or the check as broken before concluding the guard is unnecessary.

## 2026-09-19 Slice 6 review round: the getattr rule rebuilt an AST call and lost lineno

- **What happened:** the `getattr(importlib, "import_module")` branch of
  `_dynamic_import_findings` replaced the original call node with a synthetic
  `ast.Call` built from the remaining arguments, so the "without a target argument"
  message raised `AttributeError: 'Call' object has no attribute 'lineno'` and the
  scanner self-test failed.
- **Root cause:** a node was reconstructed to drop its first argument without
  copying the source-location attributes.
- **Prevention rule:** never rebuild an AST node to drop arguments; keep the
  original node for locations and carry the remaining argument list separately.

## 2026-09-19 Slice 7: check-result-id ordinal double-counted within one transaction

- **What happened:** `finalize_run` assigned each CheckResult an id of
  `cr-{repo.count_check_results(conn) + len(check_results) + 1:04d}`. Because
  `count_check_results` queries the same connection inside the uncommitted
  transaction, it already sees the rows inserted earlier in the loop. Adding
  `len(check_results)` double-counted every result after the first, producing
  ids like cr-0001, cr-0003, cr-0006 instead of cr-0001, cr-0002, cr-0003.
  The bug was invisible while only one family was enabled (one result per run);
  it surfaced when Slice 7 enabled three families and the second result's id
  skipped.
- **Root cause:** I treated `count_check_results` as seeing only committed state
  (pre-transaction), but SQLite's default isolation lets a connection read its
  own uncommitted writes. The `len(check_results)` term was a redundant
  compensator for a problem that did not exist.
- **Prevention rule:** when an ordinal is derived from a COUNT on the same
  connection inside an open transaction, the count already includes this
  transaction's earlier inserts; do not add a local accumulator on top. Verify
  by checking the second iteration's id, not just the first.

## 2026-09-20 Slice 7 review round: a vacuous mutation proof and a harness that could not tell a crash from an assertion

- **What happened:** the `invalidate_state_filter_removed` proof dropped the SQL
  state clause but left the fourth bound parameter, so SQLite raised
  `ProgrammingError: Incorrect number of bindings supplied` on every call. The
  harness counted any non-zero pytest exit as FAIL_CAUGHT, so the row looked
  green. The reviewer corrected the mutation to valid SQL and the whole 27-test
  orchestrator+api suite passed: the state-scoping clause of
  `invalidate_rotation_group` was covered by no failing-capable test, because
  the only scenario exercised had exactly one active draw for the family, where
  the rowcount is 1 with or without the filter. Two more rows were caught only
  by incidental exceptions (ValueError from the removed shared-ordinal guard,
  a UNIQUE-constraint integrity error from the removed exposure filter), and
  the second `shared_ordinal` raise ("binds several request ordinals") had no
  test at all.
- **Root cause:** two compounding errors. First, a mutation that made the
  program invalid (binding-count mismatch) rather than changing behavior, which
  is the exact "require one real failure per branch, not a parse error" failure
  the verification rules warn about. Second, a catch signal (`returncode != 0`
  with `--tb=no`) that cannot distinguish an AssertionError, a collection
  error, or a runtime crash, so the proof could not detect its own vacuity. The
  suite also lacked the mixed-state scenario (one invalidated plus one active
  draw for the same family) that makes the filter load-bearing.
- **Prevention rule:** a mutation proof requires (1) a valid, behavior-changing
  mutation, (2) a named expected test that must fail, and (3) an
  assertion-level failure (AssertionError or pytest's `Failed: DID NOT RAISE`)
  parsed from the junit report, with vacuous, incidental and wrong-test catches
  failing the proof run. When a guard filters rows on state, seed both states
  in the test so the rowcount is observable, and verify a new or changed proof
  harness against known-vacuous and known-crashing mutations before trusting a
  green table.

## 2026-09-20 Slice 8: the offline replay rebuilt inputs from current state

- **What happened:** the first version of `demos/test1.py`'s offline re-scoring
  re-derived each run's sealed case set with `sealed_store.load_drawn_cases`, which
  reflects the incident state *today*. By the time the demo replayed shift 1, the
  incidents were resolved, so the regression cases were no longer loaded: the replay
  produced 18 CheckResults against 36 stored ones, `identical=False`, and the demo
  reported `PRE-PROOF FAIL` on a mechanism that was working. Loading the case set the
  run actually recorded (its stored check ids resolved through the sealed index)
  reproduced all 36 exactly.
- **Root cause:** I treated a live-selection helper as if it were a historical
  accessor. `load_drawn_cases` deliberately follows the current incident state (a
  resolved incident's stimulus is not re-scored), which is correct for a new run and
  wrong for replaying an old one.
- **Prevention rule:** when a check claims "the same inputs replay identically", the
  replay must reconstruct the exact inputs the run consumed - the rows the run wrote -
  never re-derive them with a selector that reads present state. Verify by comparing
  counts first (stored vs re-derived) before interpreting a mismatch as a mechanism
  failure.

## 2026-09-20 Slice 8: an invalid mutation written into the proof table

- **What happened:** the `limits_projection_unions_all_declarations` row replaced a
  comprehension's filter line with `if True:  # MUTATION`, which is a `SyntaxError`
  inside a comprehension. The run reported `NOT_CAUGHT` with `SyntaxError: invalid
  syntax` instead of a green row - the harness caught it, but the row itself was the
  defect, exactly the class of error the 2026-09-20 Slice 7 entry logged.
- **Root cause:** I wrote the mutation as if the target line were a statement, without
  re-reading the surrounding expression (a set comprehension).
- **Prevention rule:** before adding a mutation row, reproduce the mutated file in a
  scratch copy and require it to import/compile; a mutation must change behavior
  without changing syntax validity. When the target is inside a comprehension or
  expression, mutate only the expression itself.

## 2026-09-20 Slice 8: an edit inserted a block in the middle of a dict literal

- **What happened:** adding the `repair_arc_*` entries to
  `config.TRUSTED_LOCAL_FIXTURES` was done with an edit whose replacement re-declared
  the dict head, leaving the original entries after a closing brace - an invalid file.
  It was caught by reading the file after the edit, before any test ran.
- **Root cause:** the edit's old string ended at the dict's opening line, so the new
  string re-created that line while the original body stayed in place.
- **Prevention rule:** when an edit adds entries to a literal, replace the whole
  literal (head through closing bracket), not just its head; after any structural
  edit, re-read the region before running checks.

## 2026-09-20 Slice 8: verification re-run used the wrong Python interpreter

- **What happened:** a re-run of the full verification chain (`pytest`,
  `mutation_proofs.py`, `demos.test1`) used bare `python`, which on this shell
  resolves to a hermes-agent venv without pytest. The log showed
  `No module named pytest` instead of the expected suite result; the run was
  stopped and re-issued with `.venv/Scripts/python.exe`.
- **Root cause:** assumed the shell PATH's `python` is the project interpreter;
  in this environment it is not.
- **Prevention rule:** always invoke this repository's checks with
  `.venv/Scripts/python.exe` (or an activated `.venv`); a command that reports a
  missing tool or module is treated as a harness error to diagnose before any
  conclusion about the code. **Superseded 2026-09-26:** the `.venv` trampoline is
  blocked by Windows Application Control on this machine; use
  `.venv313/Scripts/python.exe` (see the 2026-09-26 interpreter-block entry).

## 2026-09-20 Slice 8: a killed mutation run left a mutation applied (false regression)

- **What happened:** the background verification chain (full suite -> mutation proofs
  -> pre-proof demo) was killed while its mutation phase was running. The harness was
  killed between mutating `orchestrator.start_run` and restoring it, so the worktree
  kept the `start_run_ignores_the_inherited_version` mutation. The next full suite
  reported 3 failures (one close test, both pre-proof tests) that looked like real
  regressions; the next mutation run then reported that exact row as
  `SKIP: pattern not found` plus one INCIDENTAL catch, which identified the stuck
  mutation. After restoring the two lines the suite was 192 passed, 1 skipped and the
  pre-proof passed again.
- **Root cause:** `mutation_proofs.py` mutates real worktree files and restores them
  after each row; a kill mid-row leaves the mutated bytes. No step in the routine
  checks that the tree is in its intended (unmutated) state before running checks, so
  the false failures were first read as product regressions.
- **Prevention rule:** never kill `mutation_proofs.py` mid-run; if it is interrupted,
  before trusting any test result verify all 38 row patterns are present exactly once
  (with the harness's CRLF fallback), and treat a row's `pattern not found` as a
  signal that the worktree, not the code under test, is wrong.

## 2026-09-21 Slice 9: baseline used the unrelated PATH interpreter

- **What happened:** the first baseline command used bare `python`, resolved to the
  Hermes 3.11 environment and failed because pytest was absent. The project venv
  baseline subsequently returned 192 passed, 1 skipped.
- **Root cause:** resumed execution before recovering the environment constraint
  from the interrupted required-context read.
- **Prevention rule:** finish required-context recovery before issuing checks; use
  `.venv/Scripts/python.exe` explicitly for repository commands. **Superseded
  2026-09-26:** use `.venv313/Scripts/python.exe`; the `.venv` trampoline is
  blocked by Windows Application Control on this machine.

## 2026-09-21 Slice 9: nested labels hid a rendered-test blind spot

- **What happened:** removing the run region's synthetic label survived the first
  browser assertion because it found the nested ledger event's label instead.
- **Root cause:** the selector searched all descendants without verifying ownership
  of the matching label.
- **Prevention rule:** require the label's closest synthetic region to equal the
  region being checked; remove each owned label independently and require failure.

## 2026-09-21 Slice 9: incomplete native Enter event in the browser harness

- **What happened:** the first keyboard probe left the evaluator unselected even
  though it was focused; a CDP Enter event without its character did not perform
  native button activation.
- **Root cause:** the harness sent only key metadata, omitting the Enter text.
- **Prevention rule:** send a complete native key sequence and verify both focus
  and the resulting application state instead of substituting a programmatic click.

## 2026-09-21 Slice 9: repair activation and room drawing needed correction

- **What happened:** browser inspection found the repair bench could activate
  without an incident, and shelf slabs visually occluded the authored book spines.
- **Root cause:** station selection lacked an incident-state guard; the SVG painter
  order hid the front book faces behind later slabs.
- **Prevention rule:** test incident-dependent controls against an empty real view;
  inspect rendered artwork rather than assuming correct geometry from source.
  The repair regression failed before the guard and passed after it; book fronts
  were repainted in front of the slabs and inspected in fresh screenshots.

## 2026-09-21 Slice 9: review exposed navigation, callback and focus regressions

- **What happened:** five browser assertions reproduced three review findings:
  station changes left journey hashes stale; skip links changed the selected view;
  refresh lost the away placeholder; customer Enter removed the focused button;
  and an obsolete incident callback overrode a newer selection.
- **Root cause:** URL, station and deferred-view state were not synchronized;
  request-generation protection stopped at the refresh function instead of its
  caller; rebuilding the customer list discarded native focus.
- **Prevention rule:** preserve one selected view during refresh, distinguish
  navigation intent from request generation, require an accepted refresh before
  applying async selection, and test native Enter followed by Tab after a rerender.
  All five assertions failed against the pre-fix client before the corrections.

## 2026-09-21 Slice 9: the browser harness asserted identity and counts, not rendered values

- **What happened:** the independent review served mutated copies of `app.js` to
  the browser, one production rendering change per run (customer answer text,
  public-record value, check verdict, event type). All four faults rendered and
  all four browser runs still exited 0: the rendered-evidence assertions checked
  the request quote, metadata, byte equality, provenance-hash presence and element
  counts, and the ordinal mutation only edited a DOM dataset, so no substantive
  displayed value was ever compared against the API payload.
- **Root cause:** the harness proved that the page bound the right RECORDS to the
  panel but never that it displayed the right VALUES; a passing count of linked
  rows was treated as evidence that the rendering was correct. Same class as the
  graduated AGENTS.md verification rule (prove coverage, do not count it), now
  applied to rendered evidence instead of leak scanners.
- **Prevention rule:** every rendered evidence surface asserts its displayed value
  and identity against an independently fetched payload (answer text, record
  title/value/age, per-check verdict rows, per-event rows), and each assertion is
  proven failing-capable by a served-source fault row
  (`tests/client/render_faults.mjs`, `SHIFTWORK_FAULT` mode in
  `tests/client/browser.mjs`): the baseline must be green and every fault row must
  fail at the named assertion.

## 2026-09-21 Slice 9: historical provenance was re-derived from the mutable source path

- **What happened:** the independent review replaced a run's snapshot file at the
  same pathname after finalization; the historical outputs endpoint then reported
  the NEW record value, a NEW "run snapshot" hash and a NEW comparison while the
  captures, checks and events stayed original, so the UI could show a historical
  comparison that disagreed with what the run consumed. Deleting the source made
  the whole outputs response 500 and lose the retained raw bytes.
- **Root cause:** Slice 7/8 persisted the snapshot as a pathname
  (`shop_snapshot_ref`) and every later read (transcript selection, scoring,
  retrieval) re-read that path, so "the snapshot this run consumed" was only true
  while the file stayed byte-identical. The Slice 5 note about inputs coinciding
  by configuration was recorded as a latent-bug note but not fixed, and Slice 9's
  public comparison made the consequence user-visible.
- **Prevention rule:** a claim that a run consumed an input must persist the
  consumed identity, not a locator: capture the bytes once at execution, store
  them with the run, and resolve every later read from the capture (path reads
  only for rows that predate the capture). Retrieval must degrade optional
  enrichment to nulls when a source is unavailable and never fail the response
  that carries the retained capture.

## 2026-09-21 Slice 9: navigation checks covered the happy path only

- **What happened:** the review found that activating an incident with native
  Enter dropped keyboard focus to BODY, and that on narrow layouts a station
  selection left its detail panel entirely below the viewport (390x900: panel top
  around y=955) with focus still on the station control. The session's own
  browser checks exercised customer focus and page overflow, not incident focus
  or whether the selected content was actually reachable.
- **Root cause:** the checks verified that navigation CHANGED the view, not that
  the user could reach the changed content: no focus assertion for the
  incident-to-evidence path and no viewport-reach assertion after a station tap.
- **Prevention rule:** for each navigation action assert where focus lands and, at
  narrow widths, that the selected panel is inside the viewport after a native
  touch; drive the interaction with real key/touch events and require the
  assertion to fail when the focus/scroll behavior is removed (both rows exist in
  `tests/client/render_faults.mjs`).

## 2026-09-21 Slice 9: the new degradation test exercised the capture branch, not the guard branch

- **What happened:** the new mutation row for the retrieval-degradation guard
  removed the `except (OSError, ValueError)` fallback and the named test still
  passed (NOT_CAUGHT): the test deleted the source file for a run executed under
  the current controller, which resolves the persisted capture and never reads
  the path, so the fallback never fired. The replacement test (a legacy row with
  no capture whose recorded path is gone) then failed INCIDENTAL, because an
  unhandled route exception propagates through TestClient instead of returning
  the 500 a real client sees; only with `raise_server_exceptions=False` did the
  mutation produce an assertion-level "assert 500 == 200".
- **Root cause:** the test was written for the user-visible scenario instead of
  the guard branch's preconditions, so it proved the capture branch twice; and
  the first replacement asserted through a harness whose failure shape
  (propagated exception) is not the production failure shape (HTTP 500). The
  mutation harness did its job both times and is the reason neither error
  survived.
- **Prevention rule:** a test for a new guard branch must construct that branch's
  own preconditions (the legacy/no-capture state here), not the adjacent happy
  path; when the guard protects an HTTP surface, assert through a client that
  surfaces the crash as a status code so the removed guard fails with an
  assertion, never an incidental exception. Run the mutation row for every new
  guard before claiming it is covered.

## 2026-09-24 Gate 1 preview: assumed WebSocket existed in the REPL

- **What happened:** the browser verification setup raised `ReferenceError: WebSocket
  is not defined` after launching its isolated Chrome process; no mockup test ran.
- **Root cause:** the REPL's exposed globals were assumed to match the installed Node
  executable used by the existing browser harness.
- **Prevention rule:** check required globals in the actual execution context; use
  the installed Node process for protocol transport when the REPL lacks WebSocket.
  Reuse and close the already-started browser rather than leaving duplicate processes.

## 2026-09-24 Gate 1 preview: assumed the allowlist was an array

- **What happened:** resumed browser verification called `.filter` on a Set, stopping
  the check before any page was tested. Converting it with `Array.from` repaired the harness.
- **Root cause:** the resumed session relied on a variable name without checking its type.
- **Prevention rule:** inspect persistent helper types before reusing them after context
  recovery; do not infer collection methods from a summary.

## 2026-09-24 Gate 1 preview: compared cross-context prototypes

- **What happened:** `deepStrictEqual` rejected equal browser-result arrays in the
  REPL before the choice checks ran; serialized value comparison passed.
- **Root cause:** a value check also compared prototypes from different execution contexts.
- **Prevention rule:** normalize browser protocol values before comparing nested data;
  report harness failures separately from product failures.

## 2026-09-25 Slice 10: fresh v6 schema broke historical migration fixture setup

- **What happened:** three existing v2/v3 migration tests failed before migration
  because their fixture derives old table shapes from the current `schema.sql`,
  then inserts positional v5 rows into tables that now have v6 columns.
- **Root cause:** I changed the fresh schema without checking that historical test
  fixtures treated it as a template for older schema versions.
- **Prevention rule:** when adding schema columns, find every fixture derived from
  the live schema first. Pin historical fixtures to their actual old schema shape
  and retain their original assertions before treating upgrade tests as green.

## 2026-09-25 Slice 10: starter draft exposed a protected phrase

- **What happened:** the first starter draft copied the Slice 8 repair-arc pre
  artifact, and the serialized draft API contained text also present in a sealed
  case note. The existing API leak scanner caught it; the starter was changed to
  the safe three-file scaffold before completion.
- **Root cause:** an internal trusted-fixture artifact was reused as public
  learner-editable source without first scanning its serialized API projection.
- **Prevention rule:** when seeding public draft/source material, run the serialized
  leak scanner on GET and PUT surfaces before calling the starter safe.

## 2026-09-25 Slice 10: reported a run state without its evidence mode

- **What happened:** extending the migration demo to show the new-engagement
  `STARTER_BASELINE`, the first version printed `starter_run_state: FINALIZED` on
  its own. That reads as "the starter ran and worked". It did not run at all:
  `config.EXECUTOR_ADAPTER` defaults to `recorded`, so the run replayed a pinned
  transcript. The same starter under `executor="local_process"` fails closed as
  `PROVISION_FAILED` because the scaffold is not in `TRUSTED_LOCAL_FIXTURES`.
- **Root cause:** I treated a terminal run state as the whole claim and read the
  demo's default adapter as the one I had been testing with, after my own repro had
  explicitly passed `local_process`. Two different adapters, one label.
- **Prevention rule:** never record or display a run's `state` as evidence without
  its `adapter`, `evidence_mode` and `purpose` beside it. A FINALIZED recorded
  replay proves the transcript is readable, not that any artifact executes. When a
  result contradicts an earlier repro, isolate the differing parameter before
  reasoning about either one.

## 2026-09-25 Slice 11 public draft: incomplete review-hash transcription

- **What happened:** the first status-table edit contained two incomplete hash
  strings. The first correction also mismatched its search text; the next exact
  edit replaced both with the actual computed digests before presentation.
- **Root cause:** manual transcription of byte evidence without an immediate
  file-to-record equality check.
- **Prevention rule:** verify every recorded hash against its file bytes and
  require a full 64-character digest before presenting a fixture review pack.

## 2026-09-25 Slice 11 verification: incomplete success substitution

- **What happened:** the first in-memory capture fault labelled as success added
  collection but omitted the alternative. It was not a complete-success probe;
  the corrected probe completed both required tasks and failed the named capture assertion.
- **Root cause:** the probe checked its changed task without checking the complete
  required-task set.
- **Prevention rule:** before counting a success-substitution proof, assert that
  every required task is present and complete in the injected response.

## 2026-09-26 Interpreter block cost the session's verification; the OneDrive hardlink install failed before the copy-mode fix

- **What happened:** the project `.venv` trampoline raised
  `OSError: [WinError 4551] An Application Control policy has blocked this file`
  on every invocation, and the CPython 3.12 interpreter it points at returned
  `Permission denied`; no retry cleared it. The system 3.11.9 cannot run the
  suite (the models use PEP 695 type aliases) and the existing 3.13 interpreters
  could not load the venv's cp312 compiled dependencies, so verification was
  impossible until a fresh `.venv313` was built from the uv-managed CPython
  3.13.14. Creating that venv succeeded, but the first dependency install with
  `uv pip install -r requirements.lock` failed on this workspace because uv's
  default hardlink strategy does not survive the OneDrive-synced tree; the same
  install succeeded with `--link-mode=copy`, and `INSTALLER` in the resulting
  `site-packages` records `uv`.
- **Root cause:** the machine's Application Control policy is a recurring,
  non-transient hazard for this checkout (second occurrence after 2026-09-17),
  and the workspace lives under OneDrive, where hardlinked installs are not
  reliable. The earlier note treated the first occurrence as transient and
  planned no fallback interpreter, so a blocked 3.12 meant zero verification.
- **Prevention rule:** verification commands run with
  `.venv313/Scripts/python.exe` (git-ignored, built from the uv-managed 3.13
  interpreter); when 4551 appears, do not retry the blocked interpreter and do
  not run `uv run` as a probe (it tried to rebuild `.venv` on 2026-09-26 and
  produced an untracked `uv.lock`). Install dependencies into a fresh venv with
  `uv pip install --link-mode=copy -r requirements.lock`; never hardlink into
  this OneDrive tree. Report a blocked interpreter plainly instead of reporting
  post-block work as passing.

## 2026-09-26 Slice 11: three mutation rows had been silently skipped since the Slice 10 refactor

- **What happened:** the main harness, `tests/mutation_proofs.py`, carried three
  Slice 8 rows whose byte patterns no longer existed:
  `close_version_fallback_removed`, `start_run_ignores_the_inherited_version` and
  `snapshot_capture_bypassed_for_the_mutable_path`. Slice 10 replaced the
  inherited-version fallbacks with `_selected_operating_version` and grew a
  legacy branch inside `_snapshot_bytes_for_run`, so each row printed
  `SKIP: pattern not found` and proved nothing. The loss went unnoticed because
  the main harness was not re-run after the Slice 10 refactor; the pivot harness
  was re-run, and its output was read as the whole story.
- **Root cause:** a mutation row is an anchor into exact source bytes; a refactor
  silently breaks the anchor, and the harness reports the miss as SKIP rather
  than as a failure, so a run that nobody re-executed cannot correct it. The
  Slice 10 verification recorded the pivot harness counts without re-running
  the main harness.
- **Prevention rule:** after any refactor of a function a mutation row anchors
  onto, re-run that harness and treat every `SKIP` as a coverage loss that must
  be re-anchored or explicitly retired, never as a neutral result. A harness run
  is evidence only when every row reports `FAIL_CAUGHT` with `restored=True`.
  Re-anchored rows must fault branches the other rows do not already fault; two
  rows that fault the same branch prove neither. Repaired 2026-09-26 as recorded
  in `00-status.md`; the harness now runs subprocesses under `sys.executable`
  instead of a hardcoded interpreter path.

## 2026-09-26 Slice 11 client: the new station was added without its served-shell contract test

- **What happened:** the Slice 11 client work added the `investigate` station and
  the `source` and `diagnostic` labelled regions, but
  `tests/api/test_client_shell.py` still pinned the old 7-station set. The first
  full-suite run of 2026-09-26 returned
  `1 failed, 360 passed, 1 skipped, 2 warnings in 48.57s` with
  `Extra items in the left set: 'investigate'`; the test was updated to the
  shipped contract and the re-run returned
  `361 passed, 1 skipped, 2 warnings in 45.75s`.
- **Root cause:** the client change was verified in the browser harness (which
  asserts 8 stations) and in the preview test, but the smaller shell contract
  test was not run or updated in the same pass, so the suite was left red.
- **Prevention rule:** when a client change alters the served shell (stations,
  labelled regions, assets), update and run the shell contract test in the same
  change, not only the browser harness; before reporting a slice's suite as
  green, run the full suite, not the focused files.

## 2026-09-26 Slice 12 preflight shell loader attempted an empty variable

- **What happened:** the first PowerShell `.env` loader passed a blank line to
  `SetEnvironmentVariable`, which emitted an exception before the preflight
  still ran. A corrected command filtered to the two expected variable names
  and produced clean output with the same denied-entitlement result.
- **Root cause:** the loader assumed every `.env` line contained `name=value`.
- **Prevention rule:** filter `.env` input to expected variable names before
  setting process environment variables; keep the credential values out of
  command output and evidence files.

## 2026-09-26 Slice 12 entitlement misdiagnosis from wrong project header

- **What happened:** `whoami` authenticated under the local `project-...`
  header but returned every Sandbox permission false. I reported missing
  entitlement. A Nebius Support reply supplied the correct `aiproject-...`
  header; with the same key, all six permissions were true and image listing
  succeeded.
- **Root cause:** I treated an authenticated token's denied permissions as a
  project-wide entitlement verdict without verifying the exact `Project`
  header against the support-provided AI project ID.
- **Prevention rule:** before concluding access is unavailable, verify the
  token and project-header pairing against the provider's exact project ID;
  retain both responses when a corrected header changes the verdict.

## 2026-09-26 Slice 12 first live probe produced a false leak alarm and no model answer

- **What happened:** the first live service run completed, but the 64-token
  Nemotron limit ended with `finish_reason=length` and empty content. The leak
  scanner returned false even though a read-only rescan of the saved operation
  found no token, canary or host path.
- **Root cause:** the scanner's positive control searched for a Windows path in
  JSON without accounting for escaped backslashes. The output limit also left
  too little room for this reasoning model to emit its answer.
- **Prevention rule:** validate needles against the serialized form, including
  escaped and forward-slash path forms. Inspect `finish_reason`, content and usage
  before treating an inference request as meaningful service behavior; stay below
  Gate 3's 1,024-token ceiling when adjusting the spike limit.

## 2026-09-26 Slice 12 layer-cap result was diagnosed before checkpoint readback

- **What happened:** a 2 MiB file filled with repeated `x` bytes completed under
  a 1 MiB `max_layer_bytes` setting. I first called it a cap bypass, then
  attributed the 26,866-byte image to compression. A second run wrote random
  bytes and also reported success with the same image size. Read-only inspection
  found the supposedly written file had zero bytes in both checkpoints.
- **Root cause:** the probe trusted process stdout and image size without reading
  the saved file. Neither showed whether the checkpoint retained the written bytes.
- **Prevention rule:** check the checkpoint file's exact size and contents before
  diagnosing compression or limit enforcement. Treat successful execution with
  silently lost state as a stop condition for snapshot-dependent comparison.

## 2026-09-26 Slice 12 checkpoint verdict rested on an unarchived readback and a verifier that could not distinguish its cases

- **What happened:** the STOP verdict's decisive observation (a checkpoint
  listing `/tmp/slice12-large.bin` at zero bytes) appeared only in prose. The
  redacted JSONL held no listing or download record, no timestamp and no code
  revision, and its records cannot be emitted by any current script revision
  (`layer_cap_did_not_block_large_write` appears in no `.py` file; `WROTE_2MB`
  versus the current `WROTE_2MB_RANDOM`). The current cap check hard-stops on
  outer `SUCCESS` plus the stdout marker without downloading bytes or
  comparing a digest, so an intact 2 MiB listing would still emit
  `successful_run_snapshot_lost_written_bytes`. An independent review found
  both; a separately authorized read-only re-inspection then confirmed the
  zero-byte file in both recorded images and archived the raw records.
- **Root cause:** the probe trusted process stdout and image size without
  retrieving the saved file, the archive was appended across evolving script
  revisions without per-record revision or timestamp stamps, and the readback
  that produced the quoted observation ran outside the archived record set.
- **Prevention rule:** archive the raw record of any observation a verdict
  depends on, in the artifact set it is quoted from, with a UTC timestamp and
  source revision per record; a checker must download the artifact and compare
  a digest, and never branch on a success marker alone; after a script changes,
  new runs write to a new file with stamped records rather than appending to an
  unversioned one.

## 2026-09-26 Spike mutation rows were proven by crashes, not by assertions

- **What happened:** the first run of `tests/spike/mutation_proofs_spike.py`
  reported `assertion-level catches: 20/23` and exit 1. Three stamping rows
  (`record_utc_stamp_removed`, `record_source_hash_removed`,
  `emit_stamp_bypass`) failed with `KeyError`: the tests indexed
  `record["source_sha256"]` and `record["recorded_utc"]` directly, so removing
  the stamp raised before any assertion could run. The harness classified them
  `CAUGHT_INCIDENTAL`, which is not a proof.
- **Root cause:** an assertion that reads a required key raises instead of
  failing, so a deleted field looks like a crash and the guard stays unproven
  even though every test reports red.
- **Prevention rule:** in mutation-proven checks, read the field with `.get()`
  and compare it explicitly, so a missing or altered value fails as an
  assertion. Before citing a harness count, require `FAIL_CAUGHT` per row; a
  crash, a collection error or a timeout proves nothing about the guard.

## 2026-09-26 An appended MISTAKES block was written with literal escape sequences

- **What happened:** the new Slice 12 mutation-proof entry was appended to this file
  through an edit whose new text carried the characters backslash-r-backslash-n and
  backslash-double-quote as escape sequences. The file received them literally, so the
  whole entry landed on one unreadable line. The corruption was caught while verifying
  the appended block before the commit and repaired in place with a byte-level script;
  only the appended text changed, and the prefix stayed byte-identical.
- **Root cause:** this file is CRLF, and the edit argument encoded newlines as escapes
  instead of real line breaks, which made the escaping ambiguous between the tool, the
  shell and the file.
- **Prevention rule:** append to a CRLF file with a byte-level write that sets the line
  endings explicitly, then read the region back with `Read` and confirm the block renders
  as separate lines before committing. Never encode line breaks as escape sequences in a
  tool argument.
## 2026-09-26 Slice 12 escape run archived only the service-path inference observation

- **What happened:** the new `escape` phase calls `infer()` twice, once through the
  service path and once directly for the token-ceiling probe. The live evidence file
  held the first call's full observation but not the second's, because the
  `nemotron_inference` emit sat in the service request loop rather than inside
  `infer()`. The second call's cost, prompt tokens and latency were never archived;
  only the derived `escape_limit_probe` fields survived.
- **Root cause:** the measurement was archived at one call site instead of where it is
  produced, so the first new caller silently omitted it.
- **Prevention rule:** emit a measurement where it is produced, not at a caller, and
  guard the one emit site with a source-level test plus a mutation that duplicates the
  emit at a call site. `test_inference_calls_are_archived_from_one_emit_site` now
  requires exactly one `nemotron_inference` emit and requires it inside `infer()`.

## 2026-09-27 Slice 12 trials run archived the inference content but not the tokens that produced it

- **What happened:** all six trials passed, but each reported 103 to 143
  `completion_tokens` while the archived `content` was the six characters
  `\nSTOCK`. `infer()` builds its observation from `choices[0].message.content`
  plus `usage`, `finish_reason` and its own timing, and reads no other field the
  provider returns, so roughly 100 to 140 billed completion tokens per call are
  absent from the evidence and the run cannot say what they were. The same blind
  spot is why the escape run's two empty completions at `finish_reason: length`
  cannot be told apart from a purposeful refusal using archived data alone.
- **Root cause:** the fix for the escape archiving defect moved the emit inside
  `infer()` so that no caller could omit the record, but it archived a
  hand-picked field list instead of the provider response. Its guard asserts the
  emit count and its location, so proving that a record exists was mistaken for
  proving that the observation is complete.
- **Prevention rule:** when archiving an external observation, archive the whole
  response payload minus an explicit redaction list, not an allow-list of fields
  the author expected to matter. Every field counted in `usage` must be either
  archived or explicitly recorded as deliberately dropped with a reason. A guard
  on "the record was emitted" is not coverage of "the observation was captured".
- **Repair 2026-09-27:** `infer()` now archives the whole provider response body
  under `provider_response`, minus an explicit `REDACTED_RESPONSE_FIELDS` list whose
  dropped keys are recorded in `redacted_fields`, and the single emit site is
  unchanged. Two offline guards (a fake-client round trip of every field, and a
  forced redaction that must be named) plus two mutation rows fail against the
  pre-fix code; the spike table is 58/58 with byte-identical restoration. An
  authorized confirming call archived `message.reasoning` (438 characters) beside
  `content`, so the invisible completion tokens were the provider's `reasoning`
  field. Records archived before the repair stay incomplete; the repair is
  forward-looking.

## 2026-09-27 S13 Investigate route passed a new adapter argument to an old helper signature

- **What happened:** the first focused S13 test run had two failures; the public
  Investigate GET raised `TypeError` because the route passed `adapter=` to
  `investigate_station` before that helper accepted it. The other failure was
  an old denial-message assertion that needs the newly specified ordinary-shift
  null-ID wording.
- **Root cause:** I changed the route and the lower `investigation_view` helper
  but missed the composing `investigate_station` function between them.
- **Prevention rule:** when adding a parameter through a route, trace every
  intermediate call signature and run the route-level focused check immediately.

## 2026-09-27 S13 adapter parsed a Sandbox stdout event as text instead of value

- **What happened:** a real-shape fake event made the adapter mark a successful
  checkpoint run `SANDBOX_TERMINATED`; the test failed before the fix. The SDK
  stream carries `value` and `encoding`, including a base64 option, not `text`.
- **Root cause:** the first fake client used my invented event shape, so its
  passing result did not exercise the S12-observed SDK wire shape.
- **Prevention rule:** build transport fakes from archived provider records or
  installed SDK models, and test both plain and encoded event values before a
  live call.

## 2026-09-27 S13 scanner missed a JSON string nested inside a JSON response

- **What happened:** the serialized scanner self-test caught raw, slash and
  base64 path forms, but missed a path inside a JSON string that was itself
  serialized into a response. The focused test failed, then passed after the
  scanner checked successive JSON escape layers.
- **Root cause:** I checked one escape layer while the event payload can be
  serialized twice.
- **Prevention rule:** self-test each actual serialized surface shape, including
  nested JSON strings and base64 bodies, before interpreting an absence scan.

## 2026-09-27 S13 live model response exhausted the initial output allowance

- **What happened:** the first model-backed diagnostic made one provider call, but
  its 256 completion tokens ended during reasoning with no final tool name. The
  service had no response capture, so the trial correctly stayed failed and
  incomplete. No business state changed.
- **Root cause:** I chose a 256-token default without checking whether the
  reasoning model could finish this bounded choice inside it. The approved
  gateway ceiling is 1,024 tokens.
- **Prevention rule:** set the frozen provider allowance from the approved
  ceiling and inspect actual `finish_reason`, final content and token usage in a
  separate failed run before retrying. Preserve the failed run as evidence.

## 2026-09-27 S13 projection scanner crossed the sealed path boundary

- **What happened:** the first full suite failed its sealed storage import guard
  because the new orchestrator scanner referenced `SEALED_CASES_DIR` directly.
  The other 437 tests passed.
- **Root cause:** I used a private path as a leak needle without tracing the
  existing rule that only the sealed loader may name that location.
- **Prevention rule:** obtain sealed path needles through the sealed loader and
  run `tests/sealed/test_import_graph.py` when changing projection boundaries.

## 2026-09-27 Slice 13 frozen context kept the old 256-token ceiling after the runtime change

- **What happened:** the runtime gateway ceiling was raised to the approved
  1,024 tokens after the first live model attempt, but the frozen execution
  context still hardcoded `max_tokens: 256`. The archived successful run
  therefore records 256 while its provider call returned 287 completion tokens.
  The Slice 13 cross-check found it by re-reading the preserved run database.
- **Root cause:** the same ceiling had two owners, the `InferencePolicy` default
  and a literal in `freeze_diagnostic_context`, and no assertion tied the frozen
  record to the executed value.
- **Prevention rule:** a fixed ceiling has exactly one named constant; every
  recorded copy imports it, and a test asserts the frozen record equals the
  runtime policy value before a live claim is made.

## 2026-09-27 Slice 13 claims implied Gate 3 test 36 and 38 arms that no test pinned

- **What happened:** the completion summary implied the injected-field 422 clause
  and transport-failure retention were covered; the suite pinned neither. The
  cross-check found both against the approved test text.
- **Root cause:** the slice's test list was read as covering whole obligation
  groups, and the missing arms were never named as required assertions.
- **Prevention rule:** before claiming a spec clause is covered, name the test
  that fails when that clause's behavior breaks; if no such test exists, the
  clause stays open in the completion record.

## 2026-09-27 Slice 13 image UUID kept a second literal, making the documented override inert

- **What happened:** `SHIFTWORK_TOKEN_FACTORY_IMAGE` is a documented configuration
  name, but the Token Factory adapter compared `image_ref` against its own
  hardcoded literal, so setting the override made an isolated run fail closed
  with `PROVISION_FAILED` instead of executing the named image. The S13
  cross-check found it and recorded it as a residual; the user then instructed
  the repair. No live run used the override and the archived evidence is
  unaffected.
- **Root cause:** the same fixed value had two owners, `config.TOKEN_FACTORY_IMAGE`
  and a literal in the adapter, the same shape as the 256-token ceiling found in
  the same cross-check.
- **Prevention rule:** a fixed value has exactly one named constant; every copy,
  including the frozen-context record and the adapter gate, reads it, and a test
  drives an override through both sites with one failing-capable mutation per
  site.

## 2026-09-27 Slice 14 stranded an assist event between reserve and finish

- **What happened:** a crash after the committed assist reservation left a
  PENDING event that counted against the three-call budget, refused every
  decision and told the learner to refresh for a result that could never
  arrive. The S14 review found it; the repair fails stranded events at startup
  with the controller-side `ASSIST_INTERRUPTED` code.
- **Root cause:** the reserve-before-call design paired no-refund counting with
  a terminal-outcome write a process death can skip, and only runs had restart
  reconciliation at the one startup recovery point.
- **Prevention rule:** every reserve-then-finish pair needs a resolvable
  terminal state for each reserved row, a startup reconciliation, and panel
  copy that stays true in every state the row can rest in.

## 2026-09-27 Slice 14's injected gateway client bypassed the call deadline

- **What happened:** the 20-second bounded transport existed only on the
  default provider path, so the injected `httpx.Client` used by tests and
  demos made an unbounded call. The S14 review found it; the injected path now
  carries the same per-request timeout and a transport-level test pins it.
- **Root cause:** one claim-defining bound lived in a single branch of a
  two-branch call, and the test/demo seam silently dropped it.
- **Prevention rule:** apply a claim-defining bound on every call path
  including injection seams, and pin it with a test that fails when the seam
  bypasses the bound.

## 2026-09-28 Slice 15 ledger-state test guessed the chain label

- **What happened:** the first focused run failed one new assertion because it expected VERIFIED; the ledger verifier actually records VALID.
- **Root cause:** I guessed an enum value instead of checking the existing chain contract before writing the assertion.
- **Prevention rule:** read the declared enum or a stored baseline value before asserting exact status text, then run the focused check immediately.

## 2026-09-28 Slice 15 review repairs initially failed focused tests

- **What happened:** a new variant identity passed a tuple to the canonical hasher, which accepts JSON-shaped lists, and an edited candidate B no longer matched its frozen source pin. Two focused tests failed before both were corrected.
- **Root cause:** I changed content-bearing data without checking the hasher's accepted input shape or regenerating the pin in the same edit.
- **Prevention rule:** use JSON-shaped values at canonical hash boundaries and recompute candidate pins immediately after any source edit, then run the focused reservation and pin checks.

## 2026-09-28 Slice 15 case reorder introduced CRLF into a byte-addressed fixture

- **What happened:** the focused conformance run found CRLF in the new protected case JSON after a Windows text rewrite; 129 tests passed and one failed. I normalized that file to LF before rerunning.
- **Root cause:** a text writer applied Windows newline translation to a file whose exact bytes are part of the authored evidence.
- **Prevention rule:** write byte-addressed fixtures as bytes or explicitly force LF, then check newline counts and content hashes before running conformance.

## 2026-09-28 Slice 15 edits overlapped mutation proof restoration

- **What happened:** I started a mutation proof run as a baseline and edited source before it finished. Its restore step overwrote an orchestrator patch and left the mutation result contaminated by an in-progress evaluator edit. The 77-row run exited 1 and is not a valid baseline.
- **Root cause:** the mutation harness rewrites and restores production files, so edits and the run cannot safely overlap.
- **Prevention rule:** complete and inspect a mutation run before editing any file it can target; after an overlap, recheck touched bytes and rerun proofs only on a settled tree.

## 2026-09-28 Slice 15 spec-hash assertion was indented one level too deep

- **What happened:** the first focused rerun stopped at collection with an `IndentationError` in the revised workload pin assertion.
- **Root cause:** a patch carried indentation from the inner spec list while replacing an assertion at the outer workload level.
- **Prevention rule:** compile a touched Python test file before starting a long focused run, then inspect the exact edited lines after a multiline patch.

## 2026-09-28 Slice 15 scanner call added an undefined connection

- **What happened:** the full suite found five assist failures because `assist_event_view` called `assert_public_projection(view, conn)` even though that function has no `conn` argument.
- **Root cause:** a broad replacement matched the assist view while changing scanner calls for experiment routes.
- **Prevention rule:** anchor scanner edits to the owning function, inspect every changed call site, and run the focused assist route test before the full suite.

## 2026-09-28 S16 outcome route omitted its strict response schema

- **What happened:** the first lifecycle run had 16 failures because comparison_view added `outcome`, but `ExperimentView` rejected it as an extra field. A concurrent route test then timed out before entering its worker because the POST response failed validation.
- **Root cause:** I changed the orchestrator projection without tracing the strict API schema at the route boundary.
- **Prevention rule:** when a public projection gains a field, update its response model in the same edit and run one POST and one GET route check before the broad lifecycle file.

## 2026-09-28 S16 protected predicate guessed the strict-budget outcome

- **What happened:** the first acceptance predicate required the budget-boundary case to complete an alternative, so both correct candidates failed that undrawn case. The frozen state has no item strictly under the budget, and both candidates correctly make a justified no-match refusal. A retirement test also guessed that A and B had each passed 3/3 before checking the first outcome; A's old 0/3 was an actual draft-spec mismatch.
- **Root cause:** I inferred the expected task status from the aspect name and asserted a fixed pass count before inspecting the exact case, response envelope and pre-retirement evidence.
- **Prevention rule:** inspect each authored aspect against its frozen state and both captured candidate envelopes. For preservation tests, compare post-action evidence to the measured pre-action value, then test the expected absolute value separately only after its basis is established.

## 2026-09-28 S16 mutation row kept a stale usage anchor

- **What happened:** after filtering protected observations from public metrics, the second mutation run reported 22 caught faults and one SKIP because the service-call row still named the old iterable.
- **Root cause:** a source change moved the exact mutation anchor from all observations to public-only observations, and the proof case was not updated before rerun.
- **Prevention rule:** after editing a mutation target, inspect and update every proof anchor in that file before treating the rerun as coverage; require zero SKIP rows.

## 2026-09-29 S16 harness CRLF fallback could not match a mixed-ending anchor

- **What happened:** `tests/pivot_mutation_proofs.py` returned 89 FAIL_CAUGHT and 8 SKIP instead of the recorded 97 of 97, which read as a possible false evidence claim. Measured: `core.autocrlf=true` with no `.gitattributes` entry for `shiftwork/orchestrator.py`, so HEAD stores pure LF (3157 LF, 0 CRLF) while the worktree is pure CRLF (3407 CRLF, 0 bare LF). Four anchors had been authored with mixed endings inside one string, faithfully recording a then-mixed worktree. The runner's fallback did `old.replace(b"\n", b"\r\n")` without normalising first, turning an authored `\r\n` into `\r\r\n` (16 CR-CR-LF sequences in two of them), so those anchors could match neither regime. `orchestrator.py` is the same blob `b9af29da` at 60a378e, 224afd4, b1dabef and HEAD, so the file the harness was re-anchored against is HEAD's file. With line endings normalised on both sides, all eight anchors match HEAD exactly once and the recorded 97-of-97 is genuine.
- **Root cause:** the fallback assumed an anchor is uniformly LF, and reported a line-ending mismatch as `pattern not found`, which is indistinguishable from a guard that no longer exists. The 2026-09-20 Slice 8 prevention rule told me to verify anchors "with the harness's CRLF fallback", so the broken tool was trusted to audit itself.
- **Prevention rule:** the runner now tries the authored bytes, then the LF-normalised form, then the CRLF-normalised form, so an anchor may be authored in any shape and still matches a uniform file in either regime. Treat `SKIP pattern not found` as unadjudicated, never as coverage and never as proof of a false claim: normalise line endings on both sides and re-measure before concluding a guard is gone. Do not use a fallback as the oracle for whether the fallback works.

## 2026-09-29 mutation harness truncated a committed evidence file on every run

- **What happened:** running `tests/pivot_mutation_proofs.py` rewrote `docs/plans/shiftwork/evidence/slice15-mutation-rerun-2026-09-28.txt` in place, replacing the recorded 97-of-97 S15 evidence with the current 89-of-97 run and leaving a tracked file modified in an uncommitted tree.
- **Root cause:** `RESULTS_LOG` pointed at a committed evidence file and `main()` begins with `RESULTS_LOG.write_text("")`, so the harness owned and destroyed a record it was only meant to reproduce. Nothing warned that the target was tracked.
- **Prevention rule:** a harness results log must point at an uncommitted path for the round in progress, never at committed evidence. Before running any harness, check whether its output path is tracked (`git ls-files --error-unmatch`); if it is, repoint it first. The 89/8 bytes are preserved with their diagnosis in `docs/plans/shiftwork/evidence/slice16-anchor-rot-run-2026-09-29.txt`, and the S15 record was restored from HEAD and re-verified at 97 FAIL_CAUGHT, 0 SKIP.

## 2026-09-29 S16 repair round ran an unauthorized install inside the offline suite

- **What happened:** verifying the repair round with the command .venv313/Scripts/python.exe -m pytest tests -q executed tests/packaging/test_clean_env_install_and_run.py::test_clean_env_install_and_run (Test 51), which creates a fresh venv under tmp_path and runs pip install -r requirements.lock unconditionally at lines 128 to 131, and whose own docstring says it requires network access for the installer. Installs are not authorized by this go-ahead. Measured evidence: pip wrote 26 HTTP cache entries under %LOCALAPPDATA%/pip/cache at 01:02:43, sixteen seconds before that run's log closed at 01:02:59, while the follow-up --ignore=tests/packaging run at 01:09 wrote none, which isolates the cause. The prior session's recorded 561-passed run installed the same way. Impact was contained: the venv lived in tmp_path and is gone, no repository file changed, orchestrator.py kept sha256 f3ae145c, and requirements.lock and pyproject.toml are untouched in git status.
- **Root cause:** I repeated a command a handoff recorded as verified green without checking what it collects. pytest tests and pytest tests --ignore=tests/packaging are not the same command, and only the wider one performs a network install. AGENTS.md section 6 already said installs need authorization and that the 2026-09-19 audit excluded Test 51 for exactly that reason, so the repository convention was on record and I did not apply it.
- **Prevention rule:** offline verification for this repository is .venv313/Scripts/python.exe -m pytest tests --ignore=tests/packaging -q unless an install is explicitly authorized. Before running any handed-off test command, compare its collected set against the recorded one with --collect-only -q and check whether it collects tests/packaging. A test count is not comparable across two different commands, and a command that touches the network is not an offline check.

## 2026-09-29 S16 repair round accepted a false adjudication of a test-count discrepancy

- **What happened:** a handoff recorded that 561 passed was the true figure and that an earlier 560 was a stale mis-measurement taken before a 23:55 edit, adding that this could not be proven directly because the pre-edit content is uncommitted and unrecoverable. I wrote that adjudication into 00-status.md before testing it. It is false and was provable in one command: 560 and 561 are both correct, for --ignore=tests/packaging and for tests respectively, and the single test of difference is packaging Test 51. tests/packaging collects exactly 1 test, tests --ignore=tests/packaging collects 561 and tests collects 562. The dismissed plus-4 was also real, since the recorded 556 under --ignore=tests/packaging plus the four tests this round added is exactly 560.
- **Root cause:** the adjudication reasoned about mtimes, collection filters and arithmetic consistency while never comparing the two commands that produced the two numbers. I then treated a handed-off conclusion as settled fact because it was written confidently and labelled adjudicated, instead of re-deriving it from a measurement I could run.
- **Prevention rule:** a claimed discrepancy between two measured numbers is not adjudicated until the exact command, filter and collected set behind each number are compared. The phrase this could not be proven directly is a prompt to find the direct proof, not a licence to record an inference as a finding. Never transcribe a handed-off verdict into a status document before reproducing it, and when a reproduction contradicts the handoff, correct the record and name the prior claim that was wrong.

## 2026-09-29 backticks inside a double-quoted python -c string executed as shell commands

- **What happened:** appending the two entries above was attempted with .venv313/Scripts/python.exe -c and the entry text in a double-quoted shell string. That text contained Markdown backticks around commands such as pytest tests -q, and Git Bash performs command substitution on backticks inside double quotes, so the shell ran those commands instead of passing them to Python. One of them was the full suite under the correct interpreter, which executed Test 51 again and caused a second unauthorized install: 30 pip cache entries carry mtimes at 01:14:25 to 01:14:26, during that substitution. Two others ran a bare pytest resolved against an older interpreter and aborted with a PEP 695 SyntaxError on the type statement in shiftwork/domain/models.py line 14, which is why conftest import errors appeared in the task output. The Python append itself never ran, so MISTAKES.md stayed at 90719 bytes and no partial write was left behind. The task was stopped, and no stray pytest or pip process remained.
- **Root cause:** a documentation string was passed through a shell quoting layer that gives backticks meaning. The command also exceeded the two minute tool timeout and was moved to the background, so the substituted commands kept running after the call appeared to fail.
- **Prevention rule:** never put prose containing backticks, dollar signs or parentheses inside a double-quoted shell -c argument. Write the text to a scratch file with the Write tool and execute that file, or use a byte-level append from a script, then delete the scratch file. Prefer single quotes for any inline shell string, and treat a command that silently moves to the background as still running until it is stopped and its side effects are measured.

## 2026-09-29 a staged read-all-then-write-all doc script clobbered its own edits

- **What happened:** applying nine documentation corrections across six files, a scratch script first looped over every edit reading each file into a staging list, then looped again writing them. Two files carried more than one edit, and each write used the original bytes captured at staging time, so every write replaced the whole file with original-plus-its-own-edit and discarded the edits already applied. Three of the nine edits were silently lost: the operator packet's status line, its introduction paragraph, and a dated note in slice15-implementation-plan.md. The script reported success for all nine and printed byte deltas that made the loss visible only on inspection, since all three packet writes started from the same 18370 bytes. Caught by grepping for each expected string afterwards rather than by the script's own output.
- **Root cause:** the read phase was separated from the write phase to validate every anchor before touching anything, which is a good instinct, but the staged payload was the original file content rather than a running accumulator. Validating all anchors first and applying them cumulatively are two different designs, and this mixed them. The script also verified only that its own replacement occurred, never that the previously applied replacements survived.
- **Prevention rule:** when a script applies several edits to one file, re-read the file before each edit and write it back immediately, or accumulate into a single buffer and write once. Never stage original bytes and write them more than once per file. A multi-edit script must verify its result by checking that every expected new string is present in the file afterwards, not by trusting a per-edit success message, and identical starting byte counts across writes to one file are the signature of this bug.

## 2026-09-29 S16 follow-up tests exposed incompatible helper signatures

- **What happened:** the first route-drift test used an invalid candidate label and failed during model validation rather than at the intended route KeyError. Later, adding an optional live budget positional argument broke three focused tests whose spies and fake gateway still used the original two-argument interfaces.
- **Root cause:** the drift fixture did not preserve the domain model's label constraint, and the new optional dependency changed call shapes even when it was absent.
- **Prevention rule:** make fault fixtures valid at every layer before the target guard. When adding optional execution controls, keep the original invocation shape on the default path and test existing fakes and spies before wider verification.

## 2026-09-29 S18 routed legacy test selections into the new keyed operation

- **What happened:** the first full offline suite returned 24 failures and 11 errors because the S18 run-start branch treated old test-only `LEARNER_CHOICE` rows as qualifying S17 selections and demanded a new request key.
- **Root cause:** the dispatch checked the selection kind but ignored whether a completed comparison backed it. Historical tests deliberately use a selection row without a comparison to exercise the older execution path.
- **Prevention rule:** when adding a new lifecycle route for a reused enum value, dispatch on the full durable prerequisite and run the older route groups before the full suite. S18 now requires a comparison ID for the new path.

## 2026-09-29 S18 proof setup used stale assumptions

- **What happened:** one migrated S17 test first failed because the new selected-operation route requires a request key; a database constraint test expected an index name although SQLite reported `UNIQUE constraint failed: runs.shift_id`. The first mutation run also caught only four of eight cases because anchors had moved and the v5-copy test reads `v6_tables.sql`, not fresh `schema.sql`.
- **Root cause:** the tests and mutation targets were written from the intended design instead of the measured route, SQLite error and active migration path.
- **Prevention rule:** inspect the actual response and schema path for migrated databases, make assertions about stable failure semantics, and require zero skipped or unproven named mutations after every anchor change.

## 2026-09-29 S18 operation indexes broke pre-v5 upgrades

- **What happened:** the first final repository suite returned three legacy upgrade failures because the added `schema.sql` indexes referenced `runs.purpose` before the old fixture acquired that column.
- **Root cause:** I duplicated S18 constraints in the fresh schema despite its instruction to place later v6 DDL in `migrations/v6_tables.sql`, which also handles migrated databases.
- **Prevention rule:** add slice-owned v6 constraints only to the idempotent completion migration, then run the schema 2/3 upgrade tests before the broad suite.

## 2026-09-30 Gate 1 mobile captures cropped a wider layout instead of rendering at 390 px

- **What happened:** the three-board Gate 1 drafting session recorded "local headless Chrome renders at 1280 px and 390 px for screens 00, 01, 06 and 07" in `00-status.md`. Every 390-wide mobile capture it produced became a left-side crop of a wider layout (the review pass reproduced the same crop with its own first renders), the claimed 01 mobile capture was missing from the folder, and the 06/07 captures (5600 px tall) truncated pages that are about 6817 and 6963 px tall at that width, hiding the retained-alternative, inheritance and footer copy.
- **Root cause:** a direct `--headless=new --window-size=390` capture on this machine keeps the requested image width but lays the page out at a wider minimum window width (roughly 500 px), so the image crops instead of reflowing; `--hide-scrollbars` hides the overflow, and page heights were never compared with the capture height.
- **Prevention rule:** verify narrow viewports only with a method that forces the layout width (an iframe harness at a fixed width, or CDP device emulation), and before claiming a viewport was inspected, assert scrollWidth equals clientWidth and that the capture covers scrollHeight for every screen named in the claim.

## 2026-09-30 S19 static anchor check undercounted the harnesses and asserted uniqueness it had not measured

- **What happened:** the Slice 19 status entry recorded "all 154 rows across `tests/mutation_proofs.py`, `tests/slice16_mutation_proofs.py`, `tests/s18_mutation_proofs.py` and `tests/pivot_mutation_proofs.py` keep exactly one unique match against their target file before and after this change". The four harnesses hold 196 rows, not 154 (154 is exactly slice16 38 + s18 19 + pivot 97, the total a `CASES`-only enumeration produces while `tests/mutation_proofs.py`, which defines `MUTATIONS`, silently contributes zero), and six rows had already lost their unique anchor before Slice 19: `cycle_hardcoded_to_one` (long-known and documented as awaiting authorization), `zero_recorded_calls_is_not_a_measured_zero` (anchor line replaced by `7ce12b3`, 2026-09-29, and its named test later renamed), `s10_latest_saved_promoted_for_operation` and `s10_legacy_run_guard_removed` (a second `_selected_operating_version(conn, shift)` call landed in `42739d6`, S18, 2026-09-30), and `s15_protected_phase_executed_before_public` and `s15_protected_workspace_reused` (`75d37f9` inserted `live_budget=live_budget` inside the compared adapter construction, 2026-09-29). The same review measured that Slice 19's own diff changed no existing row's match count, so the "masked proof" conclusion was right while the count and the uniqueness claim were wrong.
- **Root cause:** the check reported an aggregate a script returned instead of enumerating each harness's own row structure, and it treated "found" as "uniquely matched". Running the harnesses was deferred as "counted, not run", so rows that would have reported SKIP were invisible, and neither the S16 round's `75d37f9` nor S18's `42739d6` re-ran the harnesses targeting the files they changed.
- **Prevention rule:** an anchor check must enumerate every row of every harness (both `CASES` and `MUTATIONS` shapes) and assert each row's match count equals its expected count, reporting the total it measured. When a diff touches a shared target file, either re-run every harness that names that file or measure each row with the harness's own matcher and list every row that does not match exactly once.

## 2026-09-30 S18 turned a passing mutation row's failure into a crash

- **What happened:** the full pivot re-run of the S19 anchor-repair round returned 96 FAIL_CAUGHT plus one CAUGHT_INCIDENTAL: `s10_unknown_schema_version_accepted` faults the unknown-schema guard in `db.ensure_schema`, and after `42739d6` (S18, 2026-09-30) the accepted version falls through to the v6 completion DDL's `runs.purpose` reference, so the named test failed with `sqlite3.OperationalError: no such column: purpose`. The runner classifies a crash as no proof, so the row had silently stopped being proof-grade. The row's anchor still matched exactly once, so no anchor check could have seen this.
- **Root cause:** the test proved the refusal only through `pytest.raises(RuntimeError)`, so when the fault's downstream consequence changed from "no raise" to "a different exception", the failure arrived as a crash rather than an assertion. The pivot harness had not been re-run since S18 landed.
- **Prevention rule:** a named assertion or `pytest.fail` must own the regression outcome so an unexpected exception cannot decide it, and a guard proof is only current when its harness has been re-run against the changed code. The S19 round hardened `test_unknown_schema_version_fails_closed` accordingly.

## 2026-09-30 S20 duplicated the qualifying comparison block and rotted six pivot harness anchors

- **What happened:** the first pivot harness round after the S20 orchestration change reported six rows unproven because their anchors were no longer unique: `create_later_condition_comparison` was written by adapting the existing qualifying-comparison slot setup, so the text those six rows match now appears twice, once in each function. The six rows had to be re-anchored onto qualifying-only context and re-proved. This is the same failure shape the S19 round repaired, triggered again by copying an existing block into a new function. The repair was still incomplete: the S20 verification round then found a seventh row, `s15_reservation_rollback_removed`, NOT_CAUGHT. Its anchor kept matching exactly once, so the count check passed, but it had **migrated** onto the new copy. The row disambiguated its four-line rollback guard (byte-identical in three reservation bodies) by naming the follower `def _comparison_run_request(`, and S20 inserted the new function between that guard and the follower, so the anchor silently re-bound to the copy while still naming the qualifying test, which cannot see the fault.
- **Root cause:** the new function was written from the existing body, and no anchor measurement ran between the copy and the first harness round. The harness's own matcher (exactly-one match) is the only thing that can see this, and only when measured. The second failure has a different root cause: a match **count** is not a match **location**. An anchor whose uniqueness comes from a neighbouring `def` re-binds whenever a function is inserted on the other side of it, and the exactly-one-match check reports that as healthy.
- **Prevention rule:** duplicating an existing orchestration block is an anchor-rot trigger. After such an edit, measure every row of every harness naming that file (42/38/19/16/97/16 rows for main/s16/s18/s19/pivot/s20) before the harness round and treat any count change as a repair obligation. Re-anchor onto context unique to the original site (for example the candidate dict and slot-loop lines), never onto text the copy shares. A count check alone is not sufficient: also verify each row still lands **inside the function it claims**. For harnesses with a scope column (`tests/s20_mutation_proofs.py`, and the `captured_mission` special case in `tests/s18_mutation_proofs.py`) the scope is checked, so add one; for the pivot and main harnesses, which have no scope, prefer an anchor line from inside the intended function over a neighbouring `def`, and when a neighbouring `def` is the only disambiguator available, re-verify it after any insertion between the anchor and that `def`. Where the duplicated guard is itself a policy guard, the copy needs its own row and its own test: the qualifying atomicity test cannot reach the later-condition rollback, so `later_reservation_rollback_removed` and `test_a_fault_mid_later_reservation_leaves_no_partial_comparison` now prove that branch separately. Follow-up 2026-10-01: the seventh row's repair still disambiguated itself by a neighbouring `def`; the independent review flagged it and the row now anchors from the qualifying-only candidate mapping through the slot loop to the guard, so no follower can re-bind it.

## 2026-09-30 a harness results path had been committed, so the next round would have truncated recorded evidence

- **What happened:** preparing the S20 verification round, `tests/pivot_mutation_proofs.py` and `tests/slice16_mutation_proofs.py` still wrote and truncated their RESULTS_LOG at `docs/plans/shiftwork/evidence/slice16-pivot-mutation-2026-09-29.txt` and `slice16-mutation-2026-09-28.txt`. Both files had since been committed as evidence, so one run of either harness would have truncated records that took a full harness round to produce. The standing rule (log path must stay uncommitted) held when the S19 round chose the paths; committing the logs silently invalidated it for the next round.
- **Root cause:** the rule was checked when the path was chosen, not when the round that truncates it was started. Tracked status is a property that changes when an evidence file is committed, and nothing in the harness checks it.
- **Prevention rule:** at the start of any round that runs a harness writing a results file, check the path against git ls-files and re-point it at a fresh, never-reused, dated path if it is tracked (this round: slice20-rerun-*-2026-09-30.txt). Never point a truncating writer at a path that a previous round's status entry records as evidence.

## 2026-10-01 the S20 Limits enumeration claimed completeness but omitted two later-path guards

- **What happened:** the fix round's new Limits bullet in `00-status.md` said "the remaining untested later-path guards are enumerated in one Limits bullet", but the later copy of the stimulus-contract check (`orchestrator.py:3371-3382`) and the orchestrator-level empty-treatment re-check (`orchestrator.py:3295`) were untested, had no mutation row and were not listed. The second independent review round found both by enumerating every fail-closed raise on the new paths against the bullet.
- **Root cause:** the enumeration was written from the guards the review's own findings happened to name, not from an enumeration of the code's fail-closed raises, so guards nobody had flagged stayed invisible to it.
- **Prevention rule:** an enumeration labelled complete must be built by listing every fail-closed raise site in the changed paths from the code, then marking each one as proven by test, proven by mutation row or listed with its reason. Never enumerate only the guards a finding named.

## 2026-10-02 S21 desktop focus changed an existing station keyboard path

- **What happened:** the first updated browser run failed the existing evaluator-to-ledger Tab assertion because activating a desktop room hotspot moved focus to the detail panel.
- **Root cause:** the new journey-navigation focus requirement was applied to every station activation, altering the desktop hotspot sequence.
- **Prevention rule:** scope new focus movement to journey navigation; retain desktop hotspot focus and the existing narrow-screen panel movement. Re-run both native journey and historical station keyboard checks.

## 2026-10-02 S21 patch anchors were incomplete

- **What happened:** five edit attempts were rejected before application because their contexts abbreviated a long initializer, omitted a ternary branch or named a standalone statement that only existed inline, or guessed a reload API call. No rejected patch changed source. The repeated anchor rule is now graduated into AGENTS.md.
- **Root cause:** patch context was reconstructed instead of copied from the current file.
- **Prevention rule:** use exact current lines for replacements; for whole-function removal, locate both measured function boundaries and verify syntax immediately.

## 2026-10-02 S21 browser retained a removed journey link

- **What happened:** the next browser run reached the investigation visibility check and failed on a null control because its historical return/away loop still queried removed top-navigation links.
- **Root cause:** the first harness update replaced the primary navigation checks but missed a second visibility check using the retired links.
- **Prevention rule:** search every navigation selector after changing the shell. Preserve the visibility assertion using the actual Compare and Next shift links.

## 2026-10-02 S21 orchestrator split: staying code referenced a moved constant

- **What happened:** the first focused run after the S21 split returned 38 failed and 31 errors, every one `NameError: name 'COMPARE_DEADLINE_S' is not defined` at `orchestrator.py:2377`; the staying `_comparison_run_request` reads the deadline constant that the move manifest sent to `comparison_flow.py`. The constant now stays in orchestrator next to that consumer and `comparison_flow` imports it.
- **Root cause:** every move census and the corrected plan's edge check covered moved functions only; nothing scanned staying code for references to moved module-level constants, so the plan's "only one staying-to-moving edge" claim was never tested against constants.
- **Prevention rule:** before running tests after a module move, run an unresolved-name scan over every touched module (Loads minus locals, module bindings and builtins) and require it clean; treat module constants as first-class movers in every reference census.

## 2026-10-02 S21 empty board entered candidate restoration

- **What happened:** both fresh browser baselines failed the empty-board check with `Cannot read properties of null (reading 'candidates')`. Candidate restoration now requires an existing comparison.
- **Root cause:** optional chaining on both comparison and shift produced equal undefined values, allowing the body to dereference a null comparison.
- **Prevention rule:** require the owning object before comparing optional IDs. Preserve the empty-board browser regression. A rejected multi-file repair also guessed the MISTAKES heading; no patch applied until the actual source anchor was read.

## 2026-10-02 S21 demos ignored offline candidate and operation boundaries

- **What happened:** the blocked browser scenario substituted the failing starter for reviewed candidate B and timed out after the production admission guard refused it. The selected journey also tried to operate in a shift whose starter operations were already complete. Both failures remain in the browser logs. A separate fresh blocked-only run reproduced the admission refusal.
- **Root cause:** the harness assumed any trusted starter could qualify as an offline comparison and treated the preview's recorded inspections as budget-free. Production permits only the two pinned comparison sources, and a chosen version must move into a new shift after completed operation history.
- **Prevention rule:** keep the reviewed candidates unchanged; exercise genuine nonempty blockers with the production exposure-retirement operation in a clearly labelled disposable controller fixture. Advance through the UI before operating the inherited exact choice. Do not weaken admission or rewrite history for a demo.

## 2026-10-02 S21 comparison polling omitted invalidation

- **What happened:** inspection while preparing the real invalidated comparison found that the client polling loop recognized FINALIZED and FAILED but would keep an invalidated comparison pending until its 180-second deadline. INVALIDATED is now terminal too.
- **Root cause:** the polling terminal list was narrower than the controller comparison lifecycle.
- **Prevention rule:** test that a production-invalidated comparison renders its actual blocker and releases the editor; mutate the invalidation terminal branch independently.

## 2026-10-02 S21 blocked fixture added middleware after startup

- **What happened:** the disposable invalidation preview crashed before binding because create_preview had already started its returned FastAPI instance during seeding. Middleware cannot be added after startup.
- **Root cause:** the helper reused the seeding app as the serving app.
- **Prevention rule:** seed the disposable database with the existing preview, then construct a fresh production app against those same bytes before attaching test-only middleware. Preserve the failed startup log.

## 2026-10-02 S21 operation proof read before capture refresh

- **What happened:** the journey reached a genuinely finalized operation but verified the customer panel while its asynchronous capture refresh was still loading, finding zero buttons for one API output.
- **Root cause:** the wait required the run ID in the UI, which was already present during QUEUED or RUNNING. It did not require the exact FINALIZED UI state or loaded captures.
- **Prevention rule:** wait for the API run to finalize and the public client to show that exact finalized run with ready captures before checking request identity. A server completion is not rendered completion.

## 2026-10-02 S21 independent review: candidate ownership depended on a cleared board

- **What happened:** overlapping refreshes across a shift transition retained the old frozen candidate; the reviewed client failed the new 400 ms board-GET regression. The repair now retains the successfully loaded shift identity independently of temporary loading/error clears.
- **Root cause:** the newer refresh captured an undefined shift ID after clearData nulled state.board, bypassing the truthy reset guard.
- **Prevention rule:** keep candidate ownership outside disposable projections; prove same-shift refresh, reconnect, sequential and overlapping transitions, and compared-candidate restoration separately.

## 2026-10-02 S21 independent review: transient serialized error DOM was never scanned

- **What happened:** a served-source provider sentinel appeared only during refresh error and survived the old harness because recovery erased it before the final scan. This was a coverage defect, not an observed production secret leak.
- **Root cause:** scanner needle controls were mistaken for coverage of every exercised lifecycle surface.
- **Prevention rule:** capture and scan exercised transient surfaces before recovery; pair each permanent mutation with a clean baseline and require the named serialized-surface failure, retaining raw output and exits.

## 2026-10-02 S21 independent review: page reload silently discarded dirty editor text

- **What happened:** browser reload replaced an unsaved edit with saved server text. The repair now requests a dirty-only unload warning; native Chrome activation proves the actual dialog and cancellation behavior.
- **Root cause:** the in-tab dirty guard did not cover page departure, and in-app Refresh preservation was broader in prose than its proven boundary.
- **Prevention rule:** distinguish in-app refresh, browser reload and persistence. Prove a real activated-browser dialog and warning removal after clean reload, save and discard; do not claim persistence for warning-only protection.

## 2026-10-02 S21 repair inspection: reset followed the winning comparison assignment

- **What happened:** the first ownership repair still cleared state.comparison after assigning the newly resolved current comparison. Static inspection caught that ordering defect before the final matrix; the redundant comparison clear was removed while keeping candidate reset.
- **Root cause:** the old reset block was carried over after moving comparison resolution ahead of state application.
- **Prevention rule:** apply a winning refresh as one coherent projection; reset only the old local assignments and retain a comparison resolved for the current shift.


## 2026-10-03 S21 closeout helper misclassified a new-file diff exit

- **What happened:** the closeout preflight stopped on the untracked evidence document because its Git no-index whitespace check returned 1 with no whitespace diagnostics. The raw command and failed preflight receipts remain preserved.
- **Root cause:** the helper assumed a no-index difference must return 0 when whitespace is clean. Git returned the ordinary difference exit instead.
- **Prevention rule:** inspect no-index diagnostics as well as the status: accept 0 or 1 only with no whitespace output and no unexpected stderr; reject actual check diagnostics. Keep new-document checks separate from the tracked working-tree diff.


## 2026-10-03 S21 publication helper parsed raw transcript content as a Git diagnostic

- **What happened:** the receipt whitespace helper treated a plus-prefixed source-location warning inside the preserved transcript as an out-of-scope Git diagnostic. The evidence commit then ran before that helper completed; no push followed. The raw diagnostic file is preserved and the committed receipt bytes are checked before further publication.
- **Root cause:** a loose colon-and-line-number match included added-content lines, and the tool orchestration did not stop dependent commands on a nonzero helper exit.
- **Prevention rule:** parse only Git diagnostic header lines, excluding plus-prefixed transcript content. Inspect every exit status and stop before any dependent commit or push when a verification command fails; verify already-created commits explicitly before continuing.

- **Count-check follow-up:** the next helper asserted five receipt files although the five-file commit includes `.gitattributes` outside the four-file receipt package. Derive expected path sets explicitly instead of copying a total commit count into a scoped check.


## 2026-10-03 S22a document verifier rejected a checkout-conversion warning

- **What happened:** the read-only new-document whitespace helper stopped on the first LF document with Git exit 1, no whitespace output and an LF-to-CRLF checkout warning on stderr. It did not complete the remaining checks; no document or runtime code was rewritten by the helper.
- **Root cause:** the helper required empty stderr although the repository's core.autocrlf setting emits a conversion warning for a clean new LF document.
- **Prevention rule:** run read-only document whitespace checks with command-scoped core.autocrlf=false, keep actual whitespace diagnostics fatal, and distinguish the no-index difference exit from a whitespace failure. Inspect the whole helper result before claiming all checks passed.


## 2026-10-03 S22a registry inspection: declared family locator allowed nested aliases

- **What happened:** the first declaration validator admitted a nested sealed path while the loader used only its basename. Static inspection caught the alias before closeout; the validator now requires exactly sealed/cases/<file>.json, and four path-refusal tests pass. No production family was substituted.
- **Root cause:** path containment was checked without verifying that the declared path and loader resolution named the same file.
- **Prevention rule:** preserve one exact mapping from a reviewed locator to its reader; reject nested/path aliases when the loader intentionally uses a flat directory.


## 2026-10-03 S22a registry metadata used an invented employer label

- **What happened:** final metadata review found the GTM declaration named Shiftwork Revenue Team as its employer. The approved memo specifies Stonebridge Software with the revenue team as client. The declaration was corrected and its exact employer/client fields are now asserted. The earlier full-suite receipt precedes this correction.
- **Root cause:** the declaration was authored from the schema and budget table without first checking the approved memo's role-fiction row.
- **Prevention rule:** copy role/employer/client identity from the approved product source before choosing display strings; schema-valid metadata can still contradict product authority.


## 2026-10-03 S22a closeout verifier applied new-file settings to tracked CRLF files

- **What happened:** the final helper ran the tracked diff with core.autocrlf=false and returned exit 2, reporting existing CRLF line endings as trailing whitespace. Its assertion printed a large diagnostic and stopped at the first check; new-file, final scope and closeout-JSON checks did not run. Earlier normal tracked diff checks and the final 688-test suite passed. The premature final-whitespace PASS wording was withdrawn.
- **Root cause:** a command-scoped setting intended for Git no-index checks of new LF files was also applied to the tracked checkout diff, disabling its normal checkout normalization. The document was updated before the dependent helper result was inspected.
- **Prevention rule:** use the repository checkout settings for tracked diffs and the documented command-scoped setting only for new-file no-index checks; save diagnostics instead of interpolating a whole result into an assertion. Record PASS only after every dependent verification actually finishes. At an unexpected failure near the context limit, preserve the failure and hand off.


## 2026-10-03 S22a resumed verifier treated CRLF receipt files as LF files

- **What happened:** the resumed new-file helper stopped on the historical registry mutation JSON receipt after applying the LF-only Git setting. No receipt bytes were changed. The repaired helper completed and created closeout.json.
- **Root cause:** untracked was used as a proxy for LF, although historical generated JSON receipts use CRLF.
- **Prevention rule:** inspect line endings before selecting no-index settings; use repository checkout settings for CRLF receipts and the documented scoped setting for LF files. Preserve historical bytes and require all dependent checks to finish before recording completion.


## 2026-10-03 S22a assistance projection omitted its strict HTTP schema field

- **What happened:** the first post-change focused suite returned 10 failures because InvestigateStationView rejected the new assist_allowed_roles projection as an extra field. No live provider was used.
- **Root cause:** the orchestration projection was changed without extending the strict response model consumed by the route.
- **Prevention rule:** trace new public fields through projection, response schema and route assertions before running integration checks; retain extra-field rejection and fix the owning schema rather than weakening it.


## 2026-10-03 S22a assistance mutation changed the event identifier as well as the budget

- **What happened:** 15 targeted assistance faults reached intended assertions; the failed-call filter fault then raised a duplicate event ID constraint instead of the budget assertion, so the harness rejected it and left the final startup fault unrun. Exact source bytes were restored. Raw receipts remain in slice22a-assist-2026-10-03.
- **Root cause:** filtering the shared event list also changed the event ID ordinal. The test could not distinguish the intended budget guard from that second effect.
- **Prevention rule:** mutate only the budget predicate when testing failed-event accounting; keep the identifier ordinal intact. Express startup seeding failure as an explicit assertion outcome so wrong seeded projections are caught as the intended failure, not a fixture exception.


## 2026-10-03 S22a assistance changes failed broader offline verification

- **What happened:** final focused checks passed 97 tests and the 17 targeted faults reached intended failures, but the full offline suite returned 15 failed, 644 passed, 1 skipped, 2 warnings, 40 errors in 187.87s (0:03:07), exit 1. Raw output and receipt are preserved. No acceptance or later integration followed.
- **Root cause:** not yet diagnosed. Focused assistance, registry and projection checks did not expose the failures exercised by the broader suite. The unexpected outcome arose at the half-context boundary, so diagnosis remains pending.
- **Prevention rule:** retain the full-suite failure as the current source verdict; reconcile its actual failing paths before checking off assistance integration. Do not weaken historical preservation tests or infer approval to rewrite archived snapshots or sealed material.


## 2026-10-03 S22a assistance final verifier stopped without saving new-file diagnostics

- **What happened:** the final audit passed its source, scope, preservation, receipt and tracked-whitespace steps, then stopped on the new-file whitespace check of slice22a-registry-2026-10-03.md. Assistance closeout.json was not created. The helper only reported the path; underlying Git diagnostics were not retained. Final hold documentation follows this partial audit.
- **Root cause:** the immediate checker condition failed; its underlying Git result is uninvestigated because the unexpected failure occurred at the half-context hold. The helper failed to save stdout/stderr before its assertion.
- **Prevention rule:** persist every no-index command result before asserting it. Do not imply final whitespace or closeout completion after a partial audit. Preserve historical bytes and investigate the stored failing command in a fresh session before resuming source edits.


## 2026-10-03 S22a verification resume rejected benign tracked conversion warnings

- **What happened:** the new helper saved the actual held-command diagnostics, then stopped on a tracked diff with exit 0, no stdout and LF-to-CRLF warnings. No source or historical bytes changed; both raw streams and exit are retained.
- **Root cause:** the tracked checker still required empty stderr despite the documented repository conversion warning behavior.
- **Prevention rule:** require a clean tracked exit and no whitespace stdout, accept only exact known conversion-warning lines on stderr, and save all streams before asserting. Validate mixed line endings with clean and failing whitespace controls without rewriting bytes.


## 2026-10-03 S22a verifier assumed one exact no-index whitespace exit

- **What happened:** the LF trailing-space positive control emitted the intended whitespace diagnostic but returned exit 3, causing the verifier to stop. The exact argv, streams and exit are saved; no historical file changed.
- **Root cause:** the control expected exit 2 and omitted the ordinary no-index difference bit that can produce exit 3.
- **Prevention rule:** require real whitespace diagnostics and accept either whitespace-error exit 2 or 3 for failing controls. Clean checks still require exit 0 or 1 with no diagnostics.


## 2026-10-03 S22a temporary verifier omitted repository import setup

- **What happened:** whitespace checks and all six controls passed, then reusing the prior preservation audit stopped at importing shiftwork. No source or historical evidence was changed.
- **Root cause:** the temporary script directory was Python's import root; the wrapper omitted the repository path expected by the reused audit.
- **Prevention rule:** make the repository import path explicit before reusing repository imports from a temporary helper; keep saved completed checks and do not infer preservation completion from them.


## 2026-10-03 S22a diagnosis helper omitted the test support import root

- **What happened:** the diagnosis helper stopped while importing the existing sentinel test because its leakscan support module was unavailable on the temporary script path. No diagnosis receipt or product edit followed.
- **Root cause:** repository imports were configured, but the test support path normally provided by pytest was omitted.
- **Prevention rule:** when importing tests outside pytest, include their established support root as well as the repository root, or run the test through pytest directly.


## 2026-10-03 S22a diagnosis helper left SQLite handles open on Windows

- **What happened:** the diagnostic controls reached temporary-directory cleanup, which failed with WinError 32 on fresh.db. The complete diagnosis receipt was not written, so the controls require a recorded rerun.
- **Root cause:** sqlite3's connection context commits or rolls back but does not close the handle; the temporary helper assumed it closed.
- **Prevention rule:** explicitly close every temporary SQLite handle, and save diagnostic control results as they finish before cleanup or later assertions.


## 2026-10-03 S22a repair check mixed conflicting pytest support roots

- **What happened:** the combined assistance, migration and route check stopped at collection because tests/store/conftest.py shadowed the orchestration BookshopShift helper. No runtime assertion was evaluated; raw output is in policy-repair/focused.stdout.log.
- **Root cause:** combining the store and orchestration test directories in this explicit order reused pytest's unqualified conftest module name.
- **Prevention rule:** run the established assistance/orchestration group separately from the store migration group; retain collection errors and do not interpret them as runtime verification or weaken test imports to hide them.


## 2026-10-03 S22a disposable sentinel package omitted legacy support files

- **What happened:** focused checks returned 2 failed and 103 passed: the legacy API scan could not load catalog v1 and the local-executor scan could not read the artifact template. All current-policy and mocked assistance checks passed. Raw output is in policy-repair/focused-assist.stdout.log.
- **Root cause:** copying only the declaration's admission pins omitted files used by other tests sharing the sentinel fixture when PACKAGE_DIR and CATALOG_DIR moved to the disposable root.
- **Prevention rule:** trace all users of a shared fixture before redirecting a package root; copy required legacy catalogs and templates as well as reviewed pack material. Preserve admission, scoring and scanner assertions and log the failed check before rerunning.


## 2026-10-03 S22a disposable seeding fixture omitted its changed state pin

- **What happened:** the pre-change seeding check returned four setup errors at real admission, before reaching seeding assertions. Raw output remains in slice22a-seeding-2026-10-03/pre-change.stdout.log.
- **Root cause:** the disposable clone reserialized public state but retained the manifest raw-state digest from the original bytes.
- **Prevention rule:** recompute every dependent raw-byte binding after a disposable fixture changes serialization, then require real admission before claiming a failing regression. Preserve the invalid first run separately.


## 2026-10-03 S22a new tests displaced a restart assertion block

- **What happened:** immediate source inspection found a new test inserted before the preceding test had finished its restart assertions. The block was restored before the new behavior was verified. The saved reads-pre-change run stopped on its intended assertions before reaching the displaced block.
- **Root cause:** a short finally/close patch anchor identified an interior function boundary instead of the complete test ending.
- **Prevention rule:** anchor additions on the next complete function definition or module end; inspect complete neighboring functions after inserting tests so preservation assertions stay inside their original test.


## 2026-10-03 S22a owning reads invalidated global-path fault setups

- **What happened:** the first broader execution check returned 20 failed and 129 passed. Manifest fault copies and observed outage/retry states were still assigned through global Bellwether constants, which the owning declarations no longer read; an extra admission read also changed the mission-race trigger. Raw streams and argv remain in slice22a-seeding-2026-10-03/execution-focused.*.
- **Root cause:** changing authority from globals to declarations without moving every existing fault stimulus to the new owning input left tests exercising obsolete controls.
- **Prevention rule:** stage explicit disposable files behind declaration paths and pins with the real admission implementation; reseal only disposable manifests when reaching deeper workload guards. Keep the same refusal, preservation and serialized-scanner assertions, and inspect race read ordering before claiming equivalence.


## 2026-10-03 S22a staging helper placed scratch inside its copy source

- **What happened:** execution-final returned 1 failed and 202 passed. The failing unchanged-world control passed a production fixture path to a helper that created scratch beside the source, then recursively copied a directory containing its own destination. TemporaryDirectory cleanup ran. Production file digests are checked again at closeout.
- **Root cause:** a request-world parent was used as a scratch directory without checking whether it belonged to the package being copied.
- **Prevention rule:** use the system temporary root for recursive fixture copies; verify the resolved destination is outside the copy source before creating it. Never treat a cleanup attempt as byte-preservation proof.


## 2026-10-03 S22a shape control expected a deeper guard after schema admission

- **What happened:** after the scratch-directory repair, world-final still failed on its expected error text. Removing description now correctly fails whole-pack public-state schema admission before the later-world shape check. Raw output remains in world-final.*.
- **Root cause:** the old integration assertion assigned the shape check responsibility for schema-invalid material, but new admission runs earlier.
- **Prevention rule:** keep the exact shape-guard assertion on its direct pure-policy input and retain the integration schema refusal, conflict kind and no-write assertions separately. Never bypass actual admission to reach a deeper guard.

## 2026-10-03 S22a exact legacy check initially rejected original omitted defaults

- **What happened:** inspection before the first post-change test found that three original Bellwether payloads omit optional record fields that historical model snapshots include as defaults. A raw/model equality guard would reject those originals. No sealed bytes changed.
- **Root cause:** exact source JSON and normalized model snapshots were assumed identical without comparing all six encodings first.
- **Prevention rule:** pin each original encoding and its historical snapshot encoding explicitly; verify exact JSON value types by digest before parsing can coerce values. Never rewrite legacy payloads to make a compatibility guard pass.
## 2026-10-03 S22a typed verification used wrong exception and nonexistent owning row

- **What happened:** typed-new returned 2 failed/27 passed: a test expected ValueError instead of InvalidSealedCase, and another changed a reservation owner to a missing engagement, tripping the foreign key before the compatibility guard. typed-integration returned 1 failed/214 passed because a historical test expected an edited legacy family to remain readable. All raw failures remain saved.
- **Root cause:** test setup did not follow the loader error taxonomy, relational ownership prerequisite or newly approved altered-payload refusal behavior.
- **Prevention rule:** assert the actual domain exception, establish a historical owning row without production admission, and preserve archived-read assertions while requiring mutable altered legacy files to fail loading. Do not bypass foreign keys or weaken snapshot immutability.
## 2026-10-03 S22a evidence ignore initially hid a test dependency

- **What happened:** static inspection after the user requested local-only raw evidence found one test still loaded the now-ignored preflight JSON. That file would be absent in a fresh published checkout. The six independently verified variant refs now live as explicit test invariants; raw evidence stays preserved locally.
- **Root cause:** the existing test treated a generated verification receipt as a required shipped fixture, and the first ignore edit did not audit consumers.
- **Prevention rule:** search source and tests for reads of each newly ignored artifact directory; retain required invariants in source/tests and keep raw receipts optional. Save any earlier suite before rerunning against the final test source.

## 2026-10-03 S22a Northline drafts failed broader offline verification

- **What happened:** the 24 draft material files and exact-byte review packet
  passed 55 focused checks with four disposable fault controls, but the full
  offline suite returned 138 failed, 597 passed, 1 skipped, 2 warnings, 54 errors
  in 172.44s (0:02:52), exit 1. Bellwether routes reported public evidence
  contains private material. The raw command streams, argv, exit and source
  pins are saved in evidence/slice22a-material-2026-10-03/. No draft service,
  production seal, admission, seed or incident reproduction ran.
- **Root cause:** not diagnosed. This unexpected regression arose at the
  half-context boundary, so no investigation or speculative repair follows
  in this session. Safety vocabulary/assessment limitations already known in
  the packet do not explain the broader failures without a causal check.
- **Prevention rule:** material authoring can affect global scanner inputs
  before a new pack is admitted. Treat the saved full-suite failure as the
  current verdict; establish the exact serialized collision and owning source
  in a fresh session before repairing it. Never weaken the privacy scanner,
  rewrite sealed Bellwether material or assume unreviewed means inert.

## 2026-10-03 S22a privacy mutation verifier misread pytest failure text

- **What happened:** the isolated case-id omission reached its named missing-refusal assertion, but the verifier rejected it and stopped after that control. Raw logs and JUnit remain in slice22a-privacy-2026-10-03/mutations/. Working source was never mutated.
- **Root cause:** the verifier expected AssertionError for pytest.raises, which reports Failed: DID NOT RAISE LifecycleError.
- **Prevention rule:** inspect actual JUnit failure text and require the exact named missing-refusal assertion with no setup or collection errors. Preserve the rejected receipt and rerun in a new output directory.

## 2026-10-03 S22a material regression diagnosis

- **What happened:** the saved material suite's privacy conflicts occurred before serialized scanning. Four disposable controls reproduce Bellwether 409, restore 200 by changing only the unsupported Northline task kind, and reproduce 409 after restoring exact draft bytes. No serialized needle matched and no scanner call occurred on the failing path.
- **Root cause:** privacy inventory construction used executable SealedCase parsing for every registered pack, including unadmitted drafts. ROUTE_SAFETY_QUESTION raised a ValidationError, which the projection wrapper mislabeled as a leak.
- **Prevention rule:** collect the same private string fields through a structural controller-only reader that protects drafts without executable task vocabulary. Keep complete semantic validation and real admission/seal guards on execution paths; prove each retained privacy field with serialized positive controls.

## 2026-10-03 S22a sealing exposed obsolete Northline assistance setup

- **What happened:** post-seal assistance compatibility returned 2 failed and 30 passed. Two tests inserted Northline manually and hit duplicate engagement keys because actual approved startup now seeds it. Raw logs and JUnit remain in evidence/slice22a-seal-2026-10-03/compatibility-assist.*.
- **Root cause:** setup assumed Northline remained unadmitted after production review, despite moving the other unreviewed-material controls to disposable declarations.
- **Prevention rule:** before changing admission state, inspect both absence assertions and manual engagement/policy inserts. Keep unreviewed refusal on explicit disposable unavailable declarations, reuse admitted rows, and preserve separate missing-unadmitted and mismatching-admitted startup checks.

## 2026-10-04 S22a closeout comparator rejected historical checkout line endings

- **What happened:** the new preservation verifier stopped on bookshop_v1.json when comparing raw checkout bytes with the HEAD blob. The saved diagnostic confirms 69 checkout CRLF sequences versus LF in HEAD, identical normalized content and identical Git-filtered blob hashes. No fixture bytes changed.
- **Root cause:** I extended the exact-byte check for the 17 pinned files to every historical tracked fixture without accounting for existing checkout conversion.
- **Prevention rule:** require exact entry-byte preservation for every historical file, exact HEAD-byte equality for pinned material, and repository-filtered Git blob equality for additional tracked material. Save a diagnostic before distinguishing checkout conversion from content drift.

## 2026-10-04 S22a document updater guessed a CRLF checklist anchor

- **What happened:** the closeout updater saved status, then stopped before writing the implementation plan because its checklist anchor assumed CRLF while the untracked plan uses LF. The remaining documents were untouched and no source changed.
- **Root cause:** I used a guessed multiline byte anchor and validated files one at a time after the first document write.
- **Prevention rule:** normalize proposed anchors to the measured target newline format and preflight every document replacement before writing any file. On resume, verify the already-applied document and preserve its current contents.

## 2026-10-04 S22a document retry inferred one newline format from a mixed file

- **What happened:** the updater retry again stopped at the same LF checklist anchor before any remaining document write. The plan contains both CRLF and LF; 68 CRLF sequences among 340 LF sequences are recorded.
- **Root cause:** checking whether any CRLF exists still guessed the anchor format in a mixed historical file.
- **Prevention rule:** measure the exact matching anchor bytes, permit precisely one existing LF or CRLF form, and derive replacement endings from that anchor. Never infer all line endings from one part of a mixed file.

## 2026-10-04 S22a publication preflight found checkout-sensitive material pins

- **What happened:** a disposable Git index and Windows autocrlf checkout preserved only 10 of the 24 approved Northline file hashes. Fourteen files changed checkout line endings before any publication. All working fixture bytes and the real index stayed unchanged. After explicit byte-preservation attributes, 24 of 24 checkout hashes match approval.
- **Root cause:** raw-byte-reviewed catalogs, documents, state, mission and nested artifact worksheets lacked Git checkout attributes. Root-worktree tests could not prove a fresh Windows checkout preserved those pins.
- **Prevention rule:** before publishing a new byte-pinned fixture pack, exercise a disposable autocrlf checkout of every reviewed file and require its exact approved hash. Protect new pinned paths explicitly without rewriting reviewed content.

## 2026-10-04 S22a publication clone name collided with historical scanner windows

- **What happened:** the fresh Windows-style clone returned 853 passed, 1 failed, 1 skipped and 2 warnings. Its long temporary parent name produced ten 25-character fragments common to sealed file paths and the legitimate public snapshot reference. Identical-commit controls fail that single manifest assertion at a long path and pass all nine checks, including eight scanner self-tests, at a short path. The failed suite and both controls remain preserved.
- **Root cause:** the historical test collector applies note_windows to absolute sealed paths as well as authored notes. A long shared parent component can be mistaken for leaked private material; root-worktree evidence had not exercised that path shape.
- **Prevention rule:** report this existing test-only portability limit and preserve its failing evidence. Use an ordinary short temporary checkout component for the full publication verification, keep all scanner code/assertions intact, and do not claim the long-name false positive is fixed or that any passing suite proves all filesystem locations.

## 2026-10-04 S22a merge verifier omitted the preserved-byte index refresh

- **What happened:** the fast-forward merge succeeded, but its verifier stopped before pushing when restored original checkout bytes appeared modified. All restored bytes matched the pre-merge snapshot and all Git clean-filter hashes matched HEAD. Explicitly refreshing those paths left every index entry unchanged and the tree clean.
- **Root cause:** the verifier assumed restoring LF or mixed historical bytes after an autocrlf checkout would also refresh Git's stat metadata.
- **Prevention rule:** preserve raw bytes, verify their clean-filter object IDs against HEAD, then refresh only those explicit paths and require unchanged index entries before asserting a clean tree.


## 2026-10-04 S22b workplace test guessed the GTM slug

- **What happened:** the first post-change workplace check returned 11 passed and 1 failed; the removal test expected stonebridge while the declaration uses gtm.
- **Root cause:** I confused the fictional employer with the registered engagement slug instead of reading the declaration.
- **Prevention rule:** copy identity values from current declarations and compare public display fields separately. Keep the failed log and fix the assertion without changing registration.


## 2026-10-04 S22b digest domains and response serialization differed

- **What happened:** initial kernel assessment checks compared returned-record transport SHA-256 with version-prefixed content_hash. Later receipt-fault controls failed their clean baseline because the trace used spaced JSON while the capture used compact JSON. Failed focused receipts remain in slice22b-traces-2026-10-04.
- **Root cause:** I treated distinct digest domains and semantically identical JSON as byte-identical receipts.
- **Prevention rule:** identify the digest domain and freeze exact response bytes. Compare plain SHA-256 with plain SHA-256 and verify each fault control's clean baseline before counting its failure.

## 2026-10-04 S22b call contracts were inferred instead of inspected

- **What happened:** the new tests used adapter instead of executor, read sqlite3.Row as a typed model, and omitted the selected-operation request key. Finalization referenced undefined batch_bytes. Replay passed keyword-only phase positionally and caused broad regressions. Failed receipts and the interrupted first full-run log remain; that interrupted run has no full-suite verdict.
- **Root cause:** I did not inspect the signature, required request key, return model and frozen-byte ownership at every call site.
- **Prevention rule:** inspect current call contracts, copy a compatible existing pattern, and exercise new and shared legacy paths before the full suite. Four distinct call-contract mistakes graduate this rule to AGENTS.md.

## 2026-10-04 S22b baseline reservation retained the legacy family route

- **What happened:** Northline STARTER_BASELINE fell through attempt-family selection even though this pack has only comparison families. The old atomic-open test also expected Northline to have no starter after S22b adds one.
- **Root cause:** starter creation changed without checking reservation dispatch and old unavailable-starter stimuli.
- **Prevention rule:** trace the new selection kind through reservation and finalization. Use explicit persistence faults to prove atomic opening independently of pack admission; retain old failed logs.

## 2026-10-04 S22b expanded the unchanged Bellwether request wire

- **What happened:** the exact-wire regression caught an extra logical_request_ordinal in Bellwether's current_request. The failing group retained 18 passes; its repaired group passes 29.
- **Root cause:** deployment-only metadata was added to every executor request.
- **Prevention rule:** add deployment metadata only with a controller deployment binding. Preserve exact-wire assertions for other packs.

## 2026-10-04 S22b diagnostic runner and test paths were guessed

- **What happened:** a nested evidence script could not import shiftwork when invoked directly; a reproduction command named nonexistent test_comparison_flow.py. Raw setup errors remain. Repository-cwd runpy and discovered test paths resolved setup.
- **Root cause:** I inferred Python import-path behavior and a test filename from the source module.
- **Prevention rule:** use a verified module or runpy entry point and discover paths with rg --files. Setup errors are not behavioral failures or mutation proof.


## 2026-10-04 S22b independent review helper attempted an append-only update

- **What happened:** the first disposable replay control stopped with
  sqlite3.IntegrityError: execution observations are append-only. Its failed
  source preimage and tool-output receipt are retained in
  evidence/slice22b-gate3-review-2026-10-04/. No row or production file changed.
- **Root cause:** I inspected observation read/write helpers but omitted
  their schema triggers before choosing a direct corruption method.
- **Prevention rule:** inspect schema-level immutability as well as helper
  signatures before corruption tests. For downstream replay faults, inject
  at the disposable read boundary and keep the actual append-only guard.

## 2026-10-04 S22b historical privacy control retained a duplicate active needle

- **What happened:** the first new review-regression run reached 31 intended
  failures, but the historical privacy row passed against the broken reader.
  Its raw log and JUnit remain in slice22b-review-repairs-2026-10-04.
- **Root cause:** the disposable active version changed request text while its
  matching task-spec text still contained the historical request verbatim.
- **Prevention rule:** remove every duplicate source of the target needle from
  the active fixture before testing historical coverage; require a failure
  against the pre-change historical reader before claiming the guard is proved.

## 2026-10-04 S22b expanded encoding controls lacked a final clean baseline

- **What happened:** after adding slash-form base64 to the privacy controls, the
  first disposable mutation run stopped at its clean private-intent control.
  Raw logs and JUnit remain; it is not counted as an intended fault failure.
- **Root cause:** the scanner encoded the original backslash needle but not
  its slash form. I started broader checks before running the newly expanded
  privacy controls on a clean source. Five other encoding shapes already matched.
- **Prevention rule:** verify every new serialization shape independently on
  clean source before mutation work. Keep any failed broader run and repeat the
  relevant full suite against the final source after an encoding repair.


## 2026-10-04 S22b historical replay test exceeded the reserved pair range

- **What happened:** the first intent/v2 focused run returned 2 failed and 140 passed. The new history test tried to put six variants into one three-pair reservation; SQLite rejected pair 4 before the replay assertions. Raw log and JUnit are retained in slice22b-intent-v2-2026-10-04.
- **Root cause:** I checked model/helper signatures but missed the pair_ordinal BETWEEN 1 AND 3 schema constraint.
- **Prevention rule:** inspect schema constraints before constructing historical rows. Represent six spent variants with two legal three-pair reservations; isolate variant uniqueness faults in a separate reservation so slot uniqueness cannot mask them.


## 2026-10-04 S22b checkout negative control overlooked inherited LF policy

- **What happened:** a disposable Windows-checkout helper verified all 42 pins, then incorrectly required removing the new -text rule to change the already-LF v2 bytes. The assertion failed.
- **Root cause:** the existing sealed-family wildcard also sets text eol=lf, so omission can preserve current LF bytes.
- **Prevention rule:** inspect the effective attribute policy before choosing a conversion fault. Require exact checkout hashes and a separate literal/effective -text omission assertion; do not claim byte drift where none occurs.

## 2026-10-04 S22b mutation anchor interpreted regex word boundaries as control characters

- **What happened:** the mutation helper passed its first three clean/fault pairs, then stopped at the malformed-explicit source-anchor preflight. Its log, partial results and failed script are preserved.
- **Root cause:** a Python string containing a regex word boundary used an ordinary literal, turning backslash-b into a backspace.
- **Prevention rule:** use raw literals for regex source anchors and preflight every anchor before any mutation execution. Source setup failures do not count as behavioral fault catches.


## 2026-10-04 S22b header omission test indexed a missing header

- **What happened:** the new clean header check passed, but omission raised KeyError rather than the required named assertion. The mutation validator refused to count it. Raw clean/fault output remains in mutations-final.
- **Root cause:** the assertion indexed a field that the mutation removes. A planned later node also omitted the generated row0 parameter identifier.
- **Prevention rule:** test optional/missing fields with get and an explicit assertion message. Discover exact collected pytest node IDs before invoking them. Keep rejected mutation evidence and require assertion-level failures with zero setup errors.


## 2026-10-04 S22b preview used an inferred database environment name

- **What happened:** the first preview set SHIFTWORK_DB instead of configured SHIFTWORK_DB_PATH. Startup created a new default shiftwork.db. The process was stopped; creation time and read-only counts confirmed this turn created it with zero runs, shifts, exposures, protected snapshots or ledger events. It was retained as mistaken-preview.db in the new evidence directory. The corrected preview uses the explicit evidence DB path.
- **Root cause:** I inferred the environment key without reading config.db_path.
- **Prevention rule:** inspect actual configuration lookup before launching a preview and verify the resolved database path first. Keep preview state inside a new disposable/evidence location; never reuse an existing database by accident.


## 2026-10-04 S22b version transition omitted historical inputs from shared test fixtures

- **What happened:** full offline verification returned 4 failed, 993 passed, 1 skip and 2 warnings. One workplace fault still removed the old active pin; three privacy checks staged partial packages missing the now-historical Northline v1 file.
- **Root cause:** I updated the focused active-family fixtures without auditing every shared disposable privacy inventory. The historical pin reader correctly refused missing input.
- **Prevention rule:** when a declared family moves versions, distinguish active-admission faults from historical preservation checks and stage every explicitly pinned historical sealed file in shared privacy fixtures. Preserve the failed full receipt and rerun focused plus full checks without relaxing scanner behavior.


## 2026-10-04 S22b journey fixture missed comparison-specific pins

- **What happened:** the first new journey group returned 18 passed and 4 setup errors. The real comparison reservation refused the test services before any slot ran. Raw log and JUnit remain in slice22b-journey-2026-10-04/journey-first.
- **Root cause:** I inspected the executor allowlist but missed the separate comparison admission check for compare_candidate_a/b.
- **Prevention rule:** inspect admission as well as execution before constructing disposable services. Bind both explicit fixture pins only inside the test monkeypatch; retain production restrictions and do not count setup errors as fault catches.


## 2026-10-04 S22b journey expected unknown offline usage

- **What happened:** the second journey group returned 1 failed and 21 passed. The comparison executed and both candidates were eligible; the new test expected input_tokens=None but the offline metrics reported zero. Raw log and JUnit remain in journey-second.
- **Root cause:** I applied the unknown-live-usage rule to a pure stdlib trusted-local service with known zero inference usage.
- **Prevention rule:** inspect the metrics evidence-mode branch before asserting missingness. Keep unknown live usage separate from explicitly model-free offline zero usage.


## 2026-10-04 S22b offline cost assertion inferred from token meter

- **What happened:** journey-clean retained 1 failed and 21 passed because the repaired assertion correctly expected zero tokens but incorrectly expected zero monetary cost. The failure and JUnit remain retained.
- **Root cause:** I inspected the inference-mode branch without reading CandidateMetrics cost_minor_units, which remains explicitly None. The earlier prevention entry overstated what offline zero usage established.
- **Prevention rule:** read the exact metric construction for every asserted field. Zero inference tokens do not establish a monetary cost; unknown costs must remain unknown.


## 2026-10-04 S22b migration comparator counted new schema columns

- **What happened:** journey-final-focused returned 1 failed and 37 passed. The old shift had identical historical values plus the new opening_mode=None column, so SELECT * comparison reported a false rewrite. The diagnostic is retained.
- **Root cause:** the test compared whole migrated rows with old-schema rows instead of retaining the original column inventory.
- **Prevention rule:** capture old column names before migration and compare those exact values afterwards; assert new migration fields independently. Never normalize old values to satisfy the comparison.


## 2026-10-04 S22b journey mutation preflight assumed inline next delimiter

- **What happened:** the mutation harness stopped before any source mutation because its compared-member anchor expected next() to close on the same line as the None default. Raw preflight traceback and original script remain retained.
- **Root cause:** I copied an abbreviated source excerpt rather than the complete measured multiline statement.
- **Prevention rule:** preflight all exact current anchors before execution and preserve rejected helpers. A source-anchor failure is setup evidence, never a behavioral fault catch.


## 2026-10-04 S22b mutation parser required an absent JUnit type attribute

- **What happened:** the first disposable prior-starter omission correctly returned 201 and failed its named 409 assertion, but the verifier rejected it. Its clean/fault streams, JUnit and parser preimage remain in mutations-verified.
- **Root cause:** pytest puts AssertionError in failure message/text and emits no type attribute in this JUnit format.
- **Prevention rule:** inspect actual structured failure output; require the named AssertionError, one failure, zero setup errors and expected exit without assuming an optional JUnit attribute.


## 2026-10-04 S22b completion omission was masked by an independent reader

- **What happened:** mutations-final proved the prior-starter row, then rejected completed-comparison because the fault test still passed after the explicit state guard was omitted. Both streams, JUnit and helper preimage remain.
- **Root cause:** the pure comparison reader independently rejects RUNNING experiments, so the original read-boundary substitution exercised two guards.
- **Prevention rule:** for explicit boundary-policy controls, hold a genuinely validated slot outcome fixed and change only the boundary field. Keep the real end-to-end reader checks separately; a fault caught by a backup cannot prove the omitted guard. The operation-history fault tests history loss as a policy input, not every individual retry guard.

## 2026-10-04 S22b safety reducer control assumed operation checks in a comparison

- **What happened:** the first pilot focused group returned 1 failed and 59 passed.
  Its safety reducer control had real route captures and passing public task
  assessments, but supplied an empty check tuple. The diagnostic is retained.
- **Root cause:** qualifying comparisons store public TaskAssessment rows and
  protected CheckResult rows; they do not create operation-style public checks.
- **Prevention rule:** inspect the actual persistence path before reusing captured
  evidence in a pure reducer control. Bind explicitly constructed unit-check
  provenance to the real public output; never claim it is a stored operation.

## 2026-10-04 S22b pilot tests inferred public API fields and status

- **What happened:** the expanded pilot group returned 2 failed and 66 passed.
  One test indexed the private context_id on a public RunView. Another expected
  diagnostic creation to return 201 rather than its declared 202 and also used
  id rather than the trial's run_id. The failed stream and JUnit are retained.
- **Root cause:** I reused internal model names and guessed the route contract
  instead of copying the current schema and a working diagnostic call.
- **Prevention rule:** check both public projections and route decorators before
  using HTTP fields/statuses; private context identifiers come from repo.get_run.
  The existing AGENTS.md call-contract rule applies to test fixtures as well.

## 2026-10-05 S22b evidence demo launched without repository import context

- **What happened:** invoking the new nested demo script directly failed at its
  shiftwork import before creating a database. The startup traceback is retained.
- **Root cause:** direct script execution places its evidence directory, not the
  repository root, first on Python's import path. Pytest had supplied repository
  context in the preceding checks.
- **Prevention rule:** invoke repository evidence demos through runpy from the
  repository root, or explicitly establish their import context. Verify no
  destination database exists before retrying a failed startup.

## 2026-10-05 S22b missing-check fault was masked by source provenance lookup

- **What happened:** the first four pilot source pairs reached their named
  assertion. The missing-check omission then raised KeyError at the later
  required-check provenance lookup and was rejected as the wrong failure.
  All raw results and the original harness remain retained.
- **Root cause:** replacing a required source check exercised the policy guard
  and the independent dictionary lookup. Omitting only the policy could not
  publish partial state because the missing source still stopped reduction.
- **Prevention rule:** isolate the inventory policy with a missing optional
  check while retaining required source provenance. Keep separate real capture
  completeness controls; a backup guard's crash cannot prove the omitted guard.

## 2026-10-05 S22b reducer keyword extension broke an older fault wrapper

- **What happened:** full offline verification returned 1 failed, 1049 passed,
  1 skipped and 2 warnings. The Bellwether incident-write control raised TypeError
  before injecting its intended transaction fault. The full receipt is retained.
- **Root cause:** the reducer now accepts verified deployment trace and frozen
  consequence keywords, while that test's forwarding shim accepted *args only.
- **Prevention rule:** inspect forwarding wrappers as well as direct callers when
  extending a signature. Forward **kwargs to the real implementation and keep
  the original fault and all rollback assertions unchanged; rerun the focused
  control and full suite against the final source.

## 2026-10-05 S22b browser checks assumed uppercase public verdicts

- **What happened:** the first browser journey reached the real blank-starter run and exact API/DOM evidence checks, then rejected its real lowercase fail verdict. Raw output and screenshot are retained in slice22b-ui-2026-10-05.
- **Root cause:** acceptance assertions used uppercase tokens without copying public CheckResultView wire values.
- **Prevention rule:** inspect a real serialized response for asserted tokens. Retain failed evidence and restart journey writes on a fresh database.

## 2026-10-05 S22b workshop SVG remained hidden

- **What happened:** the fresh functional UI reviewer found zero rendered artwork bounds while six station overlays appeared.
- **Root cause:** assigning hidden on SVGElement sets an expando rather than removing its initial hidden attribute.
- **Prevention rule:** use toggleAttribute for SVG visibility and assert nonzero rendered artwork bounds. An assigned JavaScript property is not proof that artwork renders.

## 2026-10-05 S22b shared bench did not release comparison controls

- **What happened:** the second browser journey recorded a valid investigation but the visible freeze controls stayed disabled. The failed browser receipt and real API entry are retained.
- **Root cause:** recording an investigation redraws the investigative panel after pending clears, but the new Northline bench also contains comparison controls and those retained their pending render.
- **Prevention rule:** when existing panels share one station, refresh every affected action state after pending clears. Prove the next UI action is available without an unrelated input change.

## 2026-10-05 S22b browser runner used an inferred row key

- **What happened:** an existing Bellwether regression invocation was rejected before launching a preview because baseline-selected is not a supported key. Its output directory and log remain.
- **Root cause:** I copied a display label without inspecting the runner's generated row-key mapping.
- **Prevention rule:** read the exact runner key construction before selecting rows. Setup rejection is not a regression or fault catch; rerun in a fresh output directory with supported keys.

## 2026-10-05 S22b edit harness treated identical worksheet bytes as dirty

- **What happened:** the third browser journey rejected an enabled board selector when an input dispatch retained an already-saved worksheet. Its raw failure and screenshot remain.
- **Root cause:** the harness assumed every fixture assignment changes the draft. Some permission and shared A/B worksheet bytes already match.
- **Prevention rule:** compare editor bytes before assignment. Assert dirty protection only for an actual change and verify the complete frozen file inventory independently.

## 2026-10-05 S22b checkpoint route followed the static catch-all

- **What happened:** the fourth browser journey completed a real six-slot comparison, then its test-only checkpoint POST returned an error. The browser failure and completed comparison DB remain.
- **Root cause:** create_app mounts static content at / before the preview app adds its test-only route, so the catch-all consumed the POST.
- **Prevention rule:** inspect route ordering when extending a mounted application. Place disposable test routes before the catch-all; keep production routing unchanged and retain rejected proof receipts.

## 2026-10-05 S22b browser predicate captured a Node-only variable

- **What happened:** the fifth browser journey chose A, inherited all its files and started the selected pilot, then its serialized wait predicate raised ReferenceError for chosen. The completed operation and traceback remain.
- **Root cause:** CDP evaluates serialized function text in the page, without the Node lexical closure.
- **Prevention rule:** pass needed values explicitly or derive a wait signal from page state, then verify its result independently against the API. A transport-side ReferenceError is not a product assertion failure.

The combined-bench pending-state repair also applies to help, help decisions and diagnostics; the reviewer found the same omitted comparison redraw in those completions. All affected finally blocks now refresh comparison/editor controls.

## 2026-10-05 existing inheritance demo staged the obsolete configuration pointer

- **What happened:** the required Bellwether inheritance preview stopped before launching its browser. The later comparison correctly refused because its operation had observed no condition change. Raw preview output remains.
- **Root cause:** S22a moved public-state ownership to the registered pack, but this older demo still changed PIVOT_PUBLIC_STATE. The operation therefore froze the unchanged registered world.
- **Prevention rule:** stage operator-side test worlds through a disposable owning package and its explicit pin, following the real admission guard. Keep production material and pins exact; never weaken the no-observed-change refusal to rescue a demo.

## 2026-10-05 S22b browser proof expected an unsupported edited offline diagnostic

- **What happened:** the sixth browser journey recorded the one allowed hint and its decision, saved both candidates, then waited for a public diagnostic that the real API refused. Its receipt and database remain.
- **Root cause:** I inspected the request shape but missed the retained local public-diagnostic admission rule, which permits only its reviewed starter and refuses an edited Northline candidate.
- **Prevention rule:** inspect admission conditions before requiring a successful UI journey. Preserve the source guard, verify the real refusal and restored controls, and retain successful edited isolated diagnostic execution as separately authorized live work.

## 2026-10-05 S22b event renderer inferred an absent public event id

- **What happened:** the seventh browser journey completed choice, inherited selected operation and both closes, then exact handover comparison found a rendered undefined identity. Its API/event payloads and failure remain.
- **Root cause:** LedgerEventView exposes seq within the owning ledger, not an id. The new renderer and assertion inferred the private model shape.
- **Prevention rule:** copy public field definitions and use the owning ledger plus seq for public identity. Compare event inventories and payloads to actual serialized responses; retain wrong-output diagnostics.

## 2026-10-05 S22b keyboard harness omitted the Enter character

- **What happened:** the eighth journey reached selection, selected pilot and handover, then its mobile focus assertion failed. The focused brief button never activated; Handover remained selected. Raw output and screenshots remain.
- **Root cause:** the new CDP keyDown omitted the carriage-return text supplied by the existing verified native keyboard harness. The desktop check also tested overflow without proving station activation.
- **Prevention rule:** copy the existing native input pattern and verify the resulting station title before focus or scroll assertions. Use keyboard and touch independently on the mobile surface.

The pending-state repair also covers opening/operating and close/next-shift completions. Their final redraw must release the shared draft and workplace controls without requiring an unrelated station change.

## 2026-10-05 S22b board-switch control edited a closed shift

- **What happened:** the first new snapshot reach check waited for Bellwether while an old Northline response was delayed. The switch was correctly refused and the test timed out. Raw streams and screenshot remain.
- **Root cause:** the test injected an unsaved draft into a closed shift, then clicked its disabled discard button. The retained dirty text also made the unavailable-board check inconclusive.
- **Prevention rule:** exercise edit/discard and dirty-switch guards on an open-shift snapshot. Keep mobile reach checks on the closed snapshot, and prove the draft is clean before testing an independent availability or refresh guard.

## 2026-10-05 S22b fresh browser readiness raced document creation

- **What happened:** the expanded source matrix stopped on stationNames/clean before any product assertion. Its first navigation predicate read dataset from a null document.body. Nine completed pairs and the rejected clean row remain retained.
- **Root cause:** Page.navigate acknowledges navigation before the new document must have created its body. The first fifteen-pair run did not happen to encounter that window.
- **Prevention rule:** initial browser readiness must tolerate the pre-document state while continuing to require the actual ready/empty signal. Retain setup errors separately from counted assertion catches; rerun in a fresh destination.

## 2026-10-05 S22b live receipt inspection used shell-fragile SQL quoting

- **What happened:** the first read-only inspection command raised SyntaxError before opening the retained database. The authorized live runner had already exited zero; no live retry followed.
- **Root cause:** double quotes around a SQL literal were escaped as if PowerShell used backslash escaping inside the Python command string.
- **Prevention rule:** put multi-statement receipt audits in a saved Python file and use ordinary SQL quoting there. Keep audit setup errors separate from the live execution verdict; never repeat a one-shot run to fix an inspection command.

## 2026-10-05 S22b read-only audit inferred a repository helper

- **What happened:** the saved receipt audit stopped with AttributeError on repo.list_events. The live runner had passed and no external retry followed. The failed helper and log remain retained.
- **Root cause:** the audit inferred a repository symbol instead of inspecting its signature. Source review also found the deployment trace uses actions, not events, before that assertion ran.
- **Prevention rule:** locate and read the current repository helper and domain field definitions before writing an audit. Repair inspection setup separately from live execution and preserve the original failure.


## 2026-10-05 S22b retained audit inferred a raw observation field

- **What happened:** the inherited read-only audit stopped on ExecutionObservation.raw_payload_json. The field does not exist. The consumed starter was never retried. Original source and logs remain.
- **Root cause:** the audit used the executor-side raw payload shape instead of the persisted observation's raw_payload_ref data URI.
- **Prevention rule:** inspect the stored model and repository decoder together. Validate the data-URI prefix, base64 wrapper and capture bytes, then use get_deployment_trace for the validated trace. Fix inspection separately from live execution.

## 2026-10-05 S22b corrected audit treated a Literal string as an enum

- **What happened:** the new read-only audit validated capture bytes and bindings, then stopped on CheckResult.verdict.value. The failed source and audit.log remain in the fresh audit folder. No database write or external request occurred.
- **Root cause:** I extended the audit before checking CheckResult.verdict, which is Literal['pass', 'fail', 'error'], rather than an enum. Reading the definition in the same command as execution was too late.
- **Prevention rule:** finish model inspection before running an extended audit. Compare a Literal directly; use .value only on an inspected enum. Retain the failure and run corrected inspection to a fresh log.

## 2026-10-05 S22b inspection guessed the incident request filename

- **What happened:** a read-only Get-Content requested northline_incident.jsonl, which does not exist. The actual reviewed file is northline_deployment_incident.jsonl; no execution used the guessed path.
- **Root cause:** I read a presumed filename before using the available rg file inventory.
- **Prevention rule:** discover the owning pack path or rg --files result before reading a fixture; never derive a shorter filename from a scenario label.

## 2026-10-05 S22b final preservation helper launched without repository import context

- **What happened:** the first final-preservation invocation compared entry bytes and Git state, then failed to import demos while loading the packet runner. Its log and exact helper source remain. No live call or original evidence overwrite followed.
- **Root cause:** I launched a script from the separate projectless work directory directly, so its script directory replaced the repository root on the Python import path. The existing runpy-from-repository rule was not applied.
- **Prevention rule:** launch repository-dependent helpers through python -c plus runpy from the repository root. Preserve failed inspection outputs and write the corrected result to a new log destination.


## 2026-10-05 S22b reserved command confused runpy module and file execution

- **What happened:** the final read-only command check rejected python -m runpy with a file path, before loading the packet runner. The original packet document, empty output and copied observed error remain in the packet evidence folder. No live call occurred.
- **Root cause:** I inferred the runpy CLI accepted file paths instead of reusing the verified python -c plus runpy.run_path invocation.
- **Prevention rule:** publish the exact invocation already exercised successfully. Verify its default read-only preflight from the declared working directory, then compare the manifest digest before presenting a live approval packet.


## 2026-10-05 S22b diagnostic runner missed a broken public projection

- **What happened:** the exact approved diagnostic executed once and the runner
  printed PASS, while its receipt contained the experiment endpoint's 409 conflict.
  Independent audit confirmed one valid isolated capture and useful booking, but
  the completed booking could not render. Three new regression cases fail on the
  original renderer with no setup errors; the consumed execution is never retried.
- **Root cause:** completed deployment tasks fell through Bellwether's factual
  renderer; the runner collected the experiment GET body without checking status.
- **Prevention rule:** verify every required public endpoint status and owning
  task vocabulary alongside execution and assessment. Preserve original runner,
  receipts and failed projection evidence; repair presentation offline and audit
  the retained capture before proposing any later live packet.

## 2026-10-05 S22b audit source lookup repeated an inferred filename

- **What happened:** a read-only Get-Content requested audit.py in the retained
  starter audit folder. That file does not exist; rg located audit_live.py. No
  database change or live retry followed the failed inspection.
- **Root cause:** the read used a guessed filename before the required inventory.
- **Prevention rule:** use the exact rg --files result before reading an evidence
  helper, including helpers whose conceptual name resembles the new audit.


## 2026-10-05 S22b read-only API audit blocked Windows asyncio socketpair

- **What happened:** the first read-only API recheck stopped while TestClient
  created its event loop, before any handler or database write. Original source
  and log remain in the diagnostic continuation folder; no live retry followed.
- **Root cause:** a blanket socket.connect trap also blocked the Windows stdlib
  loopback handshake used by asyncio's internal wakeup pipe.
- **Prevention rule:** distinguish the exact stdlib socketpair caller from product
  connections. Retain the setup failure; require product loopback and external
  connection controls to refuse while counting permitted internal handshakes.

## 2026-10-05 S22b API audit confused experiment state with trial state

- **What happened:** the corrected read-only recheck reached both HTTP 200
  endpoints, then expected COMPLETE on an experiment whose actual terminal state
  is FINALIZED. The stored trial is COMPLETE. Source and failed log remain.
- **Root cause:** the helper inferred a shared terminal-state vocabulary instead
  of reading Experiment.state and the trial projection separately.
- **Prevention rule:** inspect both types before asserting state labels; retain
  failures and rerun only the read-only audit to a fresh log destination.


## 2026-10-05 S22b notice update normalized mixed historical newlines

- **What happened:** a documentation helper normalized the existing status/brief
  mixed LF/CRLF endings while prepending current notices. Byte inspection caught
  this before completion. Failed copies remain in the continuation evidence.
- **Root cause:** the helper chose one newline style for each whole file instead
  of changing only the exact anchor bytes and new notice.
- **Prevention rule:** preserve historical suffix bytes, use the original anchor's
  own newline style, and verify backup hashes against the entry inventory before
  reconstructing narrowly. The corrected documents retain the original suffix
  except the explicit outdated pending-diagnostic paragraph.


## 2026-10-05 S22b new verification candidate assumed a local intent header

- **What happened:** the first completion rehearsal retained four failed booking
  slots with SERVICE_UNREACHABLE. Their exact candidate/runner/receipt and decoded
  logs remain; safety and refusal slots completed. No live call occurred.
- **Root cause:** the new candidate indexed X-Shiftwork-Intent-Key, which the
  isolated driver sends but the trusted-local adapter does not. HTTPMessage
  returned None; constructing the booking reference then raised TypeError.
- **Prevention rule:** inspect both delivery paths before relying on a header.
  Derive the documented intent from received public inputs as a compatible
  fallback, validate ambiguity, and rehearse booking and retry end to end.


## 2026-10-05 S22b continuation repeated an unverified inspection path

- **What happened:** a read-only Get-Content guessed audit_live.py in the
  diagnostic continuation folder. Inventory located audit.py there. Later rg
  also received a Windows wildcard as a literal path. No product execution or
  live retry followed either inspection error.
- **Root cause:** I reused conceptual filenames and shell glob assumptions
  instead of taking exact inventory paths and passing rg -g patterns.
- **Prevention rule:** finish rg --files discovery before a read. On Windows
  pass rg directory roots and -g filters, never a guessed wildcard path.


## 2026-10-05 S22b prepared live audit counted request meters as operations

- **What happened:** the approved completion runner passed all 14 Sandbox operations and one hint, but the separate frozen audit stopped on its meter-count assertion. The approved audit source and failed log remain in the completion review evidence. No live operation or hint was repeated.
- **Root cause:** a comparison slot has three request-level inference meters and two phase-level Sandbox operation bindings. The audit assumed both counts were two; its trusted-local rehearsal skipped this live-only branch.
- **Prevention rule:** check meter count and exact ordinals against captured requests, and operation count against executed phases. Exercise live-only inventory checks with representative observations and omit each guard independently. Preserve consumed manifest/source bytes and repair audit logic offline against the identical retained databases.


## 2026-10-05 S22b first meter-count omission control was masked

- **What happened:** the first audit-guard matrix rejected its missing-meter omission row because the test still passed. Its source, clean/omitted logs and XML remain. That row is not counted as guard proof.
- **Root cause:** removing a meter violated both cardinality and ordinal coverage, so the unchanged coverage guard caught the same fault and hid the omitted count guard.
- **Prevention rule:** inject an extra duplicate meter to preserve complete ordinal coverage while violating only count. Check each independent omission reaches its own intended DID NOT RAISE failure, with zero setup errors, and retain rejected overlapping controls separately.


## 2026-10-07 S23 helper contracts and inspection paths

- **What happened:** retained first-focused/second-journey failures assumed files in frozen-version JSON and used the wrong investigation URL. Direct nested authoring invocation failed imports; runpy worked. Several guessed read paths and PowerShell expressions failed, including this continuation's inferred executor/reducer/conftest paths.
- **Root cause:** conceptual helper/file names were reused without copying the actual response, route, source path or launch context.
- **Prevention rule:** discover exact paths with rg --files, inspect the current signature/model/route and copy a compatible call before invoking. Existing AGENTS.md already graduates this repeated pattern; preserve that rule rather than adding a duplicate.

## 2026-10-07 S23 malformed membership inputs

- **What happened:** malformed decision and decision-trace objects exposed unhashable membership checks during the prior draft session. Both guards were corrected; focused negative tests retain these shapes.
- **Root cause:** vocabulary membership was attempted before confirming a hashable string shape.
- **Prevention rule:** validate structural type before set membership and exercise malformed JSON objects, not only incorrect strings.

## 2026-10-07 S23 isolated baseline checked a sanitized error

- **What happened:** guards-first retained five failed assertions because admit_pack replaces internal error details with a public generic message. The implementation refused as intended. Isolated tests now exercise _verify_pack_material for the internal guard and keep the public refusal tests separately.
- **Root cause:** an internal error regex was asserted through the sanitized public wrapper.
- **Prevention rule:** isolate at the responsible layer; check public safe messages only at the public boundary. Preserve the failed baseline.

## 2026-10-07 S23 omission controls crashed or overlapped

- **What happened:** mutations-first rejected snapshot_type and trace_short crashes, a review-owner omission masked by condition agreement and a wrong-batch omission that indexed an empty list. All four original rows remain rejected; repaired controls produce named assertion failures with zero setup errors and exact restoration.
- **Root cause:** removing a guard also violated another prerequisite or made a later access unsafe.
- **Prevention rule:** supply all later fields and indices correctly while varying only the targeted predicate. Match review conditions across all tasks. Fault the batch equality predicate rather than the empty-workload cardinality predicate. Retain the rejected controls.

## 2026-10-07 S23 no-reason aspect used the enum member name as its value

- **What happened:** guards-complete retained one failed test using NO_TASK_HAS_REASON_CODE as serialized kind; the actual enum value is NO_TASK_REASON_CODE. Corrected guards-verified passes all 80 tests.
- **Root cause:** a familiar member name was guessed as its wire value.
- **Prevention rule:** read enum values and copy current serialization before authoring a fixture or asserting an API vocabulary.

## 2026-10-07 S23 ledger fault inserted zero rows

- **What happened:** mutations-repaired's experiment_ledger_write control passed because INSERT SELECT copied an empty GTM ledger. It is not counted as proof. A literal synthetic insertion in mutations-final reaches the intended unchanged-business-rows assertion.
- **Root cause:** the fault assumed the failing S23 starter had already produced a ledger row; GTM consequence reduction is S24 scope.
- **Prevention rule:** verify the initial row inventory and inject a guaranteed valid write that changes exactly the tested surface. Preserve empty/no-op fault controls as rejected evidence.

## 2026-10-07 S23 regression found CRLF in unreviewed request drafts

- **What happened:** the final full offline suite fails test_byte_addressed_fixtures_match_lf_checkout on the GTM manifest and pair 01/02 spec files. The focused suite did not cover this repository-wide LF guard. No repair or seal followed because the user requested a context handoff.
- **Root cause:** draft request edits did not retain the existing LF-only byte-addressed fixture contract. The proposed -text attributes preserve the current bytes, including this defect.
- **Prevention rule:** normalize only unreviewed affected drafts to LF, retain preimages and regenerate every changed inventory/seal/pin proposal before seeking approval. Reproduce the named guard and full suite without weakening them.


## 2026-10-07 S23 final preservation audit stopped on unexpected ignore change

- **What happened:** the post-document audit exited 1 because .gitignore contained a new /shiftwork/fixtures/requests/ rule outside the allowed tracked changes. It also hides new request drafts from ordinary git status.
- **Root cause:** ownership and origin are unverified. The prior successful audit predates this observed change and closeout documentation.
- **Prevention rule:** leave the unexpected change untouched, retain the blocked receipt and do not present the prior audit as final-state PASS. Resolve attribution and inventory completeness in a fresh authorized session.


## 2026-10-07 S23 packet refresh missed a multiline LF anchor

- **What happened:** readback found the inventory-history paragraph had not been replaced. The packet still correctly superseded the first draft, but did not explicitly name the pre-repair proposals. Corrected before operator review.
- **Root cause:** the helper used a CRLF multiline anchor against an LF-authored packet and did not assert that replacement matched.
- **Prevention rule:** inspect raw anchor endings and require exactly one match for every intended packet-text replacement before writing.

## 2026-10-07 S23 application verification preflight assumptions

- **What happened:** one inspection named a nonexistent executor conftest, and the new reviewed-inventory utility briefly assumed an undeclared pack catalog_path field. Both were corrected before test execution. The test-transition preflight then stopped three times before any test write: a non-unique damage-section marker, two equivalent one-line anchors with different inserted endings, and an LF-only assertion against the actual CRLF attributes tail. Raw rejected scripts, logs and zero-write receipts are retained in slice23-application-2026-10-07.
- **Root cause:** path/type and newline contracts were inferred instead of measuring the exact current definition and anchor. The application itself remained exact and intact.
- **Prevention rule:** use rg file inventory and model fields first; bind a complete unique section marker, measure the matching line ending, and validate all anchors before writing. The existing graduated AGENTS.md call-contract and anchor rules apply; no weaker fallback is permitted.

## 2026-10-07 S23 admission transition missed one legacy cardinality premise

- **What happened:** transition-focused retained 476 passes and two failures in the Northline admitted-v5 startup check. Its exact extra-one-row premise still relied on production GTM being unadmitted. A later read also named a nonexistent Northline mutation helper; no execution used that guessed path.
- **Root cause:** the search covered literal slug and availability assertions but missed the len(current) == len(expected) + 1 admission premise; the path-inventory rule was not followed on the later read.
- **Prevention rule:** inspect arithmetic cardinality and historical startup premises as well as slug lists before admitting another pack. Put the unrelated unavailable pack behind a disposable declaration, retain exact original-byte assertions, and add GTM's own admitted-v5 preservation proof. Discover every helper path before use. The original failing log and JUnit are retained; no production behavior was changed to satisfy the historical test.

## 2026-10-07 S23 GTM preservation test omitted a reused import

- **What happened:** admission-repair recorded two NameError failures because the newly copied GTM v5-preservation test used sqlite3 without importing it. These are rejected setup-level executions, not preservation proof. The Northline isolation repair already passed.
- **Root cause:** the existing test body was reused without checking its complete import dependencies.
- **Prevention rule:** audit every name imported by the source test before reusing its body, and run the new positive control before counting fault evidence. The failed log and JUnit remain intact.

## 2026-10-07 S23 publication inventory preserves an unowned ignore change

- **What happened:** exact request exceptions were temporarily added to .gitignore, then withdrawn before final publication preparation. Publishing that whole modified file could carry the incoming broad rule whose ownership is unverified. The superseded exception version remains in gitignore-exceptions-superseded.txt; incoming bytes are restored exactly.
- **Root cause:** making ordinary status complete was mistaken for defining a safe publication scope. The inventory can list ignored required paths without including an unrelated dirty ignore file.
- **Prevention rule:** preserve unknown incoming changes and exclude them from publication. Enumerate required ignored files explicitly with force-inclusion metadata, rather than treating whole-file staging as authorized. No user bytes, index entries or refs were discarded or changed.

## 2026-10-07 S23 entry backup duplicated the unique test sentinel

- **What happened:** the first post-application full suite recorded one failure, 1280 passes and one skip because the entry backup copied the sentinel-bearing test into the repository. The uniqueness guard correctly caught the duplicate.
- **Root cause:** the broad preimage snapshot was stored as scannable source without checking the repository uniqueness contract.
- **Prevention rule:** preserve unchanged sentinel-bearing test bytes in a verified lossless binary archive. Never weaken the uniqueness guard or include the literal token in notes. Retain the failed full log, verify the focused guard, then repeat the full suite. The original test bytes remain unchanged.

## 2026-10-07 S23 diagnostic assumed a receipt list

- **What happened:** a read-only inspection tried slicing prior_reviewed_pins as a list and stopped with KeyError before writing anything.
- **Root cause:** the receipt field is a path-to-hash mapping.
- **Prevention rule:** inspect JSON field types before indexing; use mapping items for pin inventories. The corrected inspection confirmed 42 preserved pin bindings.

## 2026-10-07 S23 signed CRLF source requires explicit whitespace metadata

- **What happened:** the final audit passed material, history, source, test, fault and publication checks, then Git diff --check rejected every preserved CRLF config line after -text was added. No final success receipt was written.
- **Root cause:** preserving approved CRLF bytes as a blob requires Git to recognize carriage returns as line endings for that path.
- **Prevention rule:** preserve exact approved bytes, declare cr-at-eol for that CRLF path while retaining all three default whitespace guards, and retain the failed audit diagnosis. Do not normalize signed source or suppress whitespace checks globally.


## 2026-10-08 S23 fresh-checkout scan hit a known path portability limit

- **What happened:** the first fresh Git checkout suite retained one failure, 1280 passes, one skip and two warnings. The payload scanner matched 25-character fragments of the long chat directory in a public snapshot path. The failed log, XML and result remain intact. The unchanged commit passed the focused guard and full suite from a short physical checkout path.
- **Root cause:** publication verification used a long directory component despite the historical scanner portability limit. The collector expands sealed absolute paths into fragments, which can coincide with the public absolute path. Scanner, fixture and test blobs are unchanged from the incoming main commit.
- **Prevention rule:** run fresh checkout verification from a short physical path, retain failed-path evidence and disclose the remaining portability limit. Do not weaken the scanner, rewrite reviewed source or claim arbitrary-path portability.

## 2026-10-08 S24 proof guessed an API field and helper

- **What happened:** the first lifecycle proof stopped on an absent inherited_selection_id field. Static inspection also found a nonexistent assertion helper. The subsequent multi-file repair was rejected on a guessed Mistakes Log header, with no writes. All failing output remains retained.
- **Root cause:** new proof code inferred contracts instead of copying current ShiftView and pivot_flow definitions; the repair guessed a document anchor.
- **Prevention rule:** inspect exact public response keys, helper names and signatures, and every patch anchor before editing. Prove inheritance through the real board selection and draft; use assert_prefix_unchanged plus exact business-row equality.

## 2026-10-08 S24 proof repeated the public/internal field error

- **What happened:** the second lifecycle proof reached inherited exactly-once operation and then stopped on absent public RunView.context_id. The first repair had inspected ShiftView only. No product state was lost.
- **Root cause:** an internal Run field was assumed to be a public API field.
- **Prevention rule:** inspect every response model used by a new flow at once. Resolve internal context_id through repo.get_run; retain public run/version/selection binding assertions separately.

## 2026-10-08 S24 projection fixture used the parsed mission encoding

- **What happened:** two projection tests returned no customer answer because a parsed MissionSpec model_dump was passed to the raw mission loader. The loader correctly refused its missing constants object. The product loader was unchanged.
- **Root cause:** the parsed model and original mission JSON have different schemas.
- **Prevention rule:** construct captured mission bytes from the actual reviewed source JSON, replacing only the explicit disposable request_specs field. Do not use a model dump as a substitute for its source encoding.

## 2026-10-08 S24 projection omitted its TaskOutcome reference

- **What happened:** final focused verification returned 2 failed, 315 passed and 2 warnings. The new GTM claim projection references TaskOutcome without importing or qualifying it. The earlier lifecycle proof passed before this projection addition. The defect is unrepaired at the user-requested handoff.
- **Root cause:** a bare enum name was added without checking the import list.
- **Prevention rule:** use the already-imported task_contract.TaskOutcome or verify an explicit import before adding the reference; run the affected projection tests and then regression. Never promote the earlier lifecycle PASS to a final-tree PASS.

## 2026-10-08 S24 handoff whitespace checker misread no-index status

- **What happened:** the closeout checker stopped on an LF new file with no whitespace output, no stderr and Git exit 1. No final receipt was written. The exact diagnostics are retained.
- **Root cause:** the helper treated the no-index difference status as a whitespace failure.
- **Prevention rule:** retain argv and both streams; for no-index --check accept a difference exit with empty whitespace diagnostics. Keep tracked diff checks strict and never infer that a missing receipt passed.


## 2026-10-08 S24 continuation mutation preflight needed function scopes

- **What happened:** the first anchor preflight refused four repeated statements; after scoping reducer/orchestrator rows, a second preflight still refused the comparison pin row. No mutation or product write ran. The rejected first diagnostics are retained in continuation/anchors-first-failure.json.
- **Root cause:** the new fault inventory used statement anchors shared by earlier reducers and comparison paths, and omitted the comparison scope on its first repair.
- **Prevention rule:** preflight every row at once against its owning function, rather than relying on global uniqueness. Replace and restore the full exact function bytes so only the selected statement changes.


## 2026-10-08 S24 mutation receipts exposed intercepted controls

- **What happened:** the first 49-control execution completed with one NOT_PROVED storage IntegrityError. Manual inspection rejected two further catches: the owning-pack fault failed an earlier history-refusal regex, and the incident check-id fault changed the reason before its provenance assertion. Those three controls are not counted. Raw first-round receipts remain unchanged.
- **Root cause:** one journey mixed a positive pin path with a prior negative-history test, one injected check substituted several fields, and the accounting omission reached the independent storage constraint before a named assertion.
- **Prevention rule:** separate refusal and positive journeys; alter only the intended check-id field; isolate the controller operation guard by neutralizing later retry reads in a disposable direct-reservation test. Require the expected named assertion text in new fault receipts, not merely any assertion in the test node.


## 2026-10-08 S24 restoration open failed in the OneDrive worktree

- **What happened:** a mutation's finally restoration raised OSError errno 22 while opening orchestrator.py. The remaining handoff-weight omission was reversed only after reconstructing bytes whose SHA256 exactly matched the prior preimage receipt. A binary preimage archive and restoration-recovery.json retain both states. No tests or further mutations ran before exact restoration.
- **Root cause:** unconfirmed Windows/filesystem write failure. The in-place runner had no persistent preimage to recover after its process exited; this fault's single exact inverse and earlier source hash made recovery possible.
- **Prevention rule:** execute source faults in a verified disposable physical copy outside OneDrive, retaining a binary archive of all target preimages before execution. Audit both restoration in the copy and unchanged bytes in the shared worktree. Do not count an interrupted receipt as completed proof.


## 2026-10-08 S24 completion review-probe setup contracts

- **What happened:** the extra retained human-review probe first failed collection
  because its evidence-folder launch did not load the tests directory import path.
  The next run failed with AttributeError because the stored operation draft helper
  returns serialized dictionaries, not LedgerEventDraft models. Both rejected logs,
  JUnit and lossless source preimages remain in completion/. Neither is behavioral proof.
- **Root cause:** the external proof reused a test module without its collection
  context and guessed an internal helper return shape instead of inspecting it.
- **Prevention rule:** inspect the imported module's prerequisites and the helper's
  current return contract before launching a nested proof. Use serialized keys when
  the stored-event helper returns dictionaries. The existing graduated call-contract
  rule applies; no additional duplicate AGENTS.md rule is needed.

## 2026-10-08 S24 completion review-probe changed only state

- **What happened:** after setup repair, lowering a public signal's confidence to
  50 produced one traced incident rather than the three expected success events.
  The shipped operation spec allows QUALIFIED only, so the independent assessor
  correctly rejected REVIEW. queue-corrected.log/xml and its source preimage remain.
- **Root cause:** the probe changed the observation without binding a matching
  operator workload before comparison and selection. This was a false positive
  test premise, not an observed product defect.
- **Prevention rule:** for a positive synthetic operator scenario, bind its complete
  mission before selecting, then retain the same observation across reprocessing.
  Keep production reviewed material and pins exact. Report this path as disposable
  operator mission/state proof, separately from the shipped-material API demo.


## 2026-10-08 S24 evidence audit launch syntax

- **What happened:** python -m runpy was given a filesystem path, so it rejected
  module resolution before the read-only demo audit ran. The corrected
  runpy.run_path invocation audited both retained databases successfully.
- **Root cause:** runpy's module CLI was confused with its filesystem-path API.
- **Prevention rule:** execute a saved script directly when it has no root imports;
  for repository imports use python -c with runpy.run_path and run_name=__main__.
  Do not pass a filesystem path to python -m runpy.


## 2026-10-08 S24 repair observer counted an aliased inventory twice

- **What happened:** the first disposable source-fault preflight stopped before
  pytest because the observer found the same freeze_duplicate_owner row twice.
  The runner had assigned the S24 inventory to the shared S23 module. The failed
  receipt is retained in C:/sw24-repair-20261008/preflight-control/. All 6215
  copied files restored exactly; this attempt is excluded from fault counts.
- **Root cause:** instrumentation concatenated two module inventory references
  without accounting for the CLI's deliberate alias assignment.
- **Prevention rule:** deduplicate observation candidates by exact fault identity
  before requiring unique source landing. Retain and exclude instrumentation
  failures; verify restoration before rerunning into a fresh destination.


## 2026-10-08 S24 repair test insertion crossed a function boundary

- **What happened:** readback found the new archived-history test inserted before
  the preceding test's final chain assertions. A broad follow-up anchor matched
  another replay assertion. Both were corrected before test execution.
- **Root cause:** a repeated assertion was used without its owning function as
  the exact patch scope.
- **Prevention rule:** scope multi-line test edits to the complete current function
  and inspect both adjacent boundaries immediately after writing.


## 2026-10-08 S24 repair archived-history test assumed comparison-state absence

- **What happened:** strengthened-final retained 1 failure and 33 passes. The
  archived-history setup assumed the reviewed comparison state omitted the
  operational APAC signal; it actually includes it. The failure preceded the
  inheritance assertion and is not product or guard proof.
- **Root cause:** the raw observation inventory was inferred instead of checked.
- **Prevention rule:** explicitly construct and assert the disposable archived
  observation by removing the target record from a copy. Preserve the reviewed
  source bytes and keep the rejected setup receipt separate from verification.


## 2026-10-08 S24 repair overlapped dependent copy refresh and proof

- **What happened:** the physical-copy refresh and pre-repair source proof were
  launched before the refresh completed. Both final binding checks failed on
  three intentionally newer test/log files. The disposable orchestrator source
  restored exactly; shared source was never faulted. Original manifests,
  preimages and failed outputs remain retained and excluded from completed proof.
- **Root cause:** dependent copy-refresh and proof operations were scheduled
  concurrently against a manifest describing the older copy state.
- **Prevention rule:** await refresh and its complete exact-binding audit before
  launching a dependent proof. When a binding fails, preserve the attempt and
  create a fresh short physical copy and fresh manifest/output names; never
  overwrite the old receipt or count an unissued restoration receipt.


## 2026-10-08 S24 final copy helper renamed its historical input

- **What happened:** the fresh copy helper stopped before creating a copy because
  it looked for continuation/physical-copy-final.json, which does not exist.
  The original continuation manifest and all source bytes remained unchanged.
- **Root cause:** a global filename replacement changed both the fresh output
  name and the historical input path.
- **Prevention rule:** distinguish immutable input bindings from new output
  destinations when adapting an evidence helper. Verify each path before launch.


## 2026-10-08 S24 human-review fixture leaked temporary material bindings

- **What happened:** the first repair full suite retained 2 failures, 1371 passes
  and 1 live-only skip. An ordered three-case proof reproduced both downstream
  failures after the human-review case. Temporary PACKAGE_DIR bindings survived
  fixture return, affecting mission-fault detection and the historical pin check.
- **Root cause:** mission staging used an internal binding, while state staging
  reused an outer binding. Outer cleanup reinstated the temporary mission root
  after the internal mission cleanup had restored the real package root.
- **Prevention rule:** nest a separate state-binding context inside the mission
  context so cleanup occurs in reverse acquisition order. Verify downstream
  configuration-sensitive cases together in one process, then run regression.

## 2026-10-08 S24 repair introduced an ambiguous retained S23 fault anchor

- **What happened:** the retained S23 CLI preflight refused prior_foreign_context
  before any fault ran. The new history verifier has the same context guard text.
  The rejected output and archived target preimages remain excluded.
- **Root cause:** the retained inventory relied on global statement uniqueness,
  which the new controller verifier invalidated.
- **Prevention rule:** bind the prior-input controls to their owning
  deployment_assessment_inputs function, preflight all anchors and observe the
  exact changed function/import. Keep all existing cases and assertions.

## 2026-10-08 S24 repair missed absent-result and out-of-try deceptions

- **What happened:** the second independent review demonstrated two residual
  defects. A required task omitted from the captured response left no task row
  for the projection to compare, so the derived text kept the generic no-action
  sentence while the assessment had marked REQUIRED_TASK_MISSING. Separately, a
  corrupted retained context row raised pydantic ValidationError while replay
  loaded the context, before the block that converts expected input failures into
  the UNKNOWN_MISSING_INPUTS verdict.
- **Root cause:** the rejection verdict was computed only from the tasks the
  response happened to carry, and the evidence-verdict conversion wrapped only
  the byte-decoding block that already had a try, not the retained-row loading
  calls that run before it.
- **Prevention rule:** derive partial-failure verdicts from the complete stored
  assessment for the request, including absent required results. Convert expected
  retained-input deserialization failures at every loading call that feeds
  replay, and keep assessment and reduction outside that conversion so
  programming errors still propagate.

## 2026-10-09: S24 R2 repair placed at one call site, not the loading boundary

- What happened: the R2 repair caught unreadable retained contexts only inside
  `replay_assessment`. GTM inheritance loads the same contexts and still leaked
  pydantic `ValidationError`. A later mutation needle also assumed pydantic's repr
  includes the class name; it does not, so two correct catches read NOT_PROVED.
- Root cause: the fix followed the reported trigger, not the reviewer's named
  boundary, and no other consumer of the same rows was searched. The needle was
  written from memory instead of from an observed failure message.
- Prevention: when a review names a boundary, grep every caller of that loader and
  add a falsifier per verification consumer. Copy mutation needles from a real
  observed failure message.

## 2026-10-10: `.venv313` interpreter blocked by Application Control

- What happened: `.venv313/Scripts/python.exe` failed with "An Application Control
  policy has blocked this file" from both Git Bash and PowerShell, before the S24
  fault rerun. AGENTS.md names this interpreter as the one to use.
- Root cause: the machine policy now covers the `.venv313` launcher as it earlier
  covered `.venv` (2026-09-17, 2026-09-26). Not caused by repository changes.
- Prevention: do not retry the blocked launcher. Run the venv's base interpreter
  from `pyvenv.cfg` (`home`) with `PYTHONPATH=.venv313/Lib/site-packages` and
  `PYTHONNOUSERSITE=1`, after confirming the venv has no `.pth` files and that
  `shiftwork` imports from the intended tree. Record the substitution with the
  evidence.

## 2026-10-11: S24 review-repair shell commands misfired before any source edit

- What happened: a preimage-archive command still carried an exploratory
  `cp <test file> "$TMPDIR/../"` fragment, which wrote a stray copy of
  `test_gtm_review_repairs.py` to `C:/Users/jayd0/AppData/Local/`. `cmp` proved it
  identical to the workspace file and it was deleted. A later command holding two
  heredocs failed to parse; it wrote nothing, which a hash check confirmed.
- Root cause: an unreviewed fragment left in a compound command, and multi-heredoc
  shell input instead of the file-writing tool.
- Prevention: write scratch files with the Write tool, keep one purpose per shell
  command, and confirm every destination in an archive command is inside the
  scratchpad before running it.

## 2026-10-11 (second session): S24 F2 repair commands misfired before any edit

- What happened: the session's first command used the `rtk` prefix from the
  user-level CLAUDE.md and failed with exit 127 (not installed). A later `&&`
  chain stopped at a failing `grep`, so its `pyvenv.cfg` and `.pth` checks did not
  run and had to be repeated. A scratch observation script that imported
  `tests.orchestrator.test_gtm_pipeline` failed on `from packs...` because only
  the repository root was on `PYTHONPATH`. None of the three wrote anything.
  Separately, a line-ending check with Git Bash `grep -c $'\r$'` reported every
  line as CRLF in LF files, and the session briefly told the user the edited
  files were "uniformly CRLF". Python byte counts showed the real state: each file
  kept its pre-session endings.
- Root cause: the global prefix rule was followed over AGENTS.md section 6, which
  says not to assume `rtk` exists; independent checks were chained with `&&`; the
  script lacked the `tests/` path entry that pytest's rootdir conftest adds; and a
  shell idiom was trusted for byte-level evidence without a known-LF control.
- Prevention: run `command -v rtk` once before using the prefix; separate
  independent checks with `;`; a scratch script importing test modules needs
  `PYTHONPATH=".;tests;.venv313/Lib/site-packages"`; count `\r\n` and `\n` bytes
  in Python, comparing with HEAD or a pre-session copy, before reporting line
  endings.

## 2026-10-11 (third session): S24 fresh clone made below the scanner's needle minimum

- What happened: the S24 publication's fresh Windows clone was made at `C:\s24f`.
  Its full non-packaging run gave 2 failed, 1,397 passed, 1 skipped: the
  `host_path` and `slash_path` cases of
  `test_workplace_scanner_detects_private_values_in_the_serialized_payload`
  returned 200 instead of 409. Nothing had been pushed. The same commit passed in
  a clone at `C:\s24fresh` (1,399 passed, 1 live-only skip). Separately, a
  secret-pattern scan of the evidence first used ripgrep, which skips binary
  files, and a bundle scan then flagged `sk-` inside `operation-task-v1` in a
  SQLite file; both scans were redone with a decompressed, boundary-anchored check.
- Root cause: the public-projection scanner adds the working directory as a needle
  but keeps only needles of at least 8 characters (`_private_public_needles`,
  since `e1366d5`); `C:\s24f` has 7. The path followed the S23 short-path lesson
  without checking a lower bound. No S24 source was involved. The scan errors came
  from trusting a text-only search for binary and compressed receipts.
- Prevention: make fresh-checkout clones at a short path of at least 8
  characters, such as `C:\swNNfresh`, and read a fresh-clone failure's needle
  setup before treating it as a source defect. Scan databases and decompressed
  archive members for secrets with a word-boundary pattern, not ripgrep defaults.

## 2026-10-12 (S25 session): GTM harness assertions written from another board's semantics

- What happened: three first-run failures in the new S25 GTM browser harness.
  (1) `attempts_remaining === 0` after the starter operation copied Bellwether's
  two-attempt retry rule; GTM's limit is 3 and the second operation is refused by
  the one-operation-per-shift rule, so the board still reported 2 remaining.
  (2) `verifyRoom` collected `[data-file]` nodes to prove GTM hides the checks and
  history tabs, but the draft textarea also carries `data-file="<name>"` once a
  draft loads, so the closed snapshot added `service.py` to the tab list.
  (3) The `pipelineClock` fault was caught by the owners group's assertion, not
  the clocks one, because all three wall groups share one renderer and the owners
  group is asserted first with a full-row equality that includes `record_ref`.
- Root cause: assertions were written from a remembered sibling board or from the
  renderer's shape instead of from the measured GTM surface, and a shared
  renderer let one group's equality absorb another group's fault.
- Prevention: copy every expected scalar from the probe output of the board under
  test, never from a sibling board; scope DOM selectors to the container whose
  contract they assert (`.file-tabs [data-file]`); when several groups share a
  renderer, give each group's assertion only the keys its heading promises plus
  shared provenance, so each fault fails exactly its named assertion.

## 2026-10-12 (S25 session, second): substring includes() made a denominator fault vacuous

- What happened: the GTM `comparisonDenominator` fault row passed in fault mode
  instead of failing. The rendered summary showed `public requests per candidate
  999` while the assertion asked whether the summary includes
  `public requests per candidate 9`; GTM's true shared denominator is 9, and
  `9` is a prefix of `999`, so the substring matched the mutated text.
- Root cause: `assert.ok(summary.includes(label + value))` proves only that some
  string starting with the expected value appears; it cannot distinguish 9 from
  99 or 999. The Bellwether arm escapes the same defect only because its
  recorded denominator is 6, which is not a prefix of 999.
- Prevention: parse the labelled number out of the rendered summary and compare
  with assert.equal, as gtm_browser.mjs now does for both denominators. When
  reusing an assertion shape from an older board, check whether the new board's
  actual value keeps the shape fail-capable instead of assuming it transfers.

## 2026-10-12 (S25 session, third): red-row attribution built from truncated needles

- What happened: the portability checkpoint's section 3.5 attributed the red `event`
  and `candidateReset` render-fault rows to duplicate anchors, claiming each anchor
  "occurs exactly twice in app.js where the harness requires one" and would fail on
  Windows too. Direct measurement during the S25 regression batch falsified it: the
  harness needles are the full strings `humanize(event.event_type)), element('small'`
  and `state.candidates = { A: null, B: null };\n    }`, each occurring exactly once at
  entry commit b5a9b95 and once in the S25 worktree, and both rows are CAUGHT in the
  S25 run. The "exactly two" counts came from truncated substrings.
- Root cause: the anchor count was taken from a remembered prefix of the needle instead
  of the exact string the harness destructures at browser.mjs:478, which carries
  trailing context and an embedded newline. A count on a prefix is not a count on the
  needle, and the wrong attribution then propagated into a durable document.
- Prevention: when attributing a fault-anchor failure, extract the needle from the
  FAULTS map programmatically and count that exact string against both the entry commit
  and the worktree before writing any causal claim, and record the measurement with the
  claim. The checkpoint carries a dated correction in its section 3.5 and section 7.

## 2026-10-14 (S25 live-arm records): a refusal attributed from the shape numbers, and a pushed commit range counted from memory

- What happened: the independent review round of the published S25 live arm found
  two false claims in durable records; both were reproduced and repaired the same
  day. (1) Checkpoint 8.5 said the GTM live comparison "calls a preflight that
  raises `live comparison shape, model or rate ceiling is unverified`". Executing
  that path against a copy of the recorded journey database shows the refusal
  comes earlier: the fresh-slot guard at `comparison_flow.py:1314-1321` pins each
  slot to `request_count == 2` / `executed_request_count == 3` (line 1317), the
  GTM comparison's recorded 3-and-4 slots fail that pin, and line 1321 raises
  `live comparison reservation does not have six fresh bound slots`; the preflight
  at 1322-1323 is never reached. (2) The 00-status publication bullet and the
  `46b6cdb` message recorded three commits on `shiftwork/slice-25-live`;
  `git log --oneline 61c621d..8751413` shows five.
- Root cause: the refusal mechanism was inferred from the frozen 18 against GTM's
  realized 24 at the preflight's code location without executing the refusal path,
  so the guard that actually binds was never observed; and the commit count was
  written from the session's memory of the commits it had just made instead of
  enumerating the pushed range.
- Prevention: attribute a refusal to a code path only from a reproduction of that
  exact path, capturing the raising file and line (a spy around the claimed caller
  makes the claim's absence falsifiable); and record any commit count by
  enumerating the actual range at record time. Records corrected in place the same
  day; the pushed `46b6cdb` message stands corrected on record, not rewritten.

## 2026-10-14 (S26 corpus freeze records): a staging claim written from check-ignore instead of the real `git add`

- What happened: the S26 corpus/freeze notice in `00-status.md` first claimed the
  tracked manifest "stages with a normal `git add`" because `git check-ignore`
  answered "not ignored" for it; the next staging attempt exited 1 with the
  ignored-paths warning and broke the `git add && git commit` chain. The bullet
  was rewritten before its commit to say a plain `git add` "refuses" the path,
  and a clean-room reproduction (git 2.50.1) then showed that too was imprecise:
  the tracked edit IS staged despite the exit-1 warning (the warning stops an
  `&&` chain, not the staging), while a new file in the directory is refused
  outright until `git add -f`. The bullet was refined to that in a follow-up
  record commit the same day; no run result or enforcement behavior was affected.
- Root cause: staging behavior was inferred from `git check-ignore` output, which
  without `--no-index` reports tracked files as not ignored regardless of the
  rules, instead of from the operation itself; the rewrite then over-corrected
  without reproducing the exit-1 path's actual effect on the index.
- Prevention: prove a staging claim by running that exact operation on a
  clean-room copy (never on the record itself), and reproduce an intermediate
  claim before writing it; in this git version a tracked file under an ignored
  directory stages with exit 1 and a warning while a new file there needs
  `-f`; `git check-ignore` needs `--no-index` to reveal the rule for tracked
  paths, and evidence-directory commits use `git add -f`.

## 2026-10-15 (S27 baseline): fresh-board readiness required a shift before the browser could open one

- What happened: the first GTM/Northline browser launch wrapper timed out before
  starting Chrome. Its healthy GTM preview had zero shifts; the wrapper demanded
  a non-null `latest_shift`. The failed attempt is retained in
  `/tmp/shiftwork-s27-board-baseline-e8vs2zm3/`.
- Root cause: a readiness predicate from a seeded comparison-snapshot runner was
  reused for an empty-board journey. The browser itself opens the first shift.
- Prevention: check the requested board's identity for fresh-board readiness;
  require a shift only when the preview contract seeds one. Inspect the preview
  and browser entry steps before reusing their launch wrapper.


## 2026-10-18 S28: detached proof runner left no receipts

- What happened: a Python launcher started the disposable mutation runner with
  Popen, then exited its tool call. At inspection the child no longer existed
  and its log was empty. No mutation result is claimed from that attempt.
- Root cause: the proof run had no retained tool session to monitor or finish.
  The child's exit status and termination cause are unknown.
- Prevention: launch long verification commands directly in a controllable exec
  session. Wait for its exit code and inspect its receipts before reporting proof.


## 2026-10-18 S28: disposable-copy filter removed essential artifact fixtures

- What happened: the first monitored mutation run could not set up eight action
  tests. Its copy filter ignored every directory named artifacts, including
  shiftwork/fixtures/artifacts. None of that run is counted as accepted proof.
- Root cause: a root-output exclusion was applied at every directory depth, and
  the copied test module had not first passed a complete clean baseline.
- Prevention: exclude generated artifacts only at the repository root. Run the
  full targeted clean suite inside each disposable copy before any mutation.


## 2026-10-19 S28: wrong hash domain in a fresh-starter repair and masked meter-type control

- What happened: routing Bellwether's legacy baseline into selected operation
  correctly returned 409 because its historical contract hash is not the newer
  mission hash. Separately, the wrong-meter mutation survived because that test
  lacked credentials and an independent credential guard returned the same 409.
- Root cause: the first repair inferred baseline compatibility without checking
  both requirement-hash domains; the mutation test did not isolate its guard.
- Prevention: preserve the baseline as an explicit saved inspection, route edited
  diagnostics and eligible choices through existing isolated contexts, and check
  fresh-host behavior. Supply synthetic credentials when probing meter type so
  only the intended wiring guard can produce the refusal. Keep rejected receipts.


## 2026-10-19 S28: browser profile cleanup raced Chrome shutdown

- What happened: all twelve rendered views and three board reads passed, but the
  browser command exited 1 when recursive removal raced Chrome writing its profile.
- Root cause: cleanup sent termination and removed the profile without awaiting
  the owned Chrome process exit.
- Prevention: await the exit event before removing the owned temporary profile,
  and require the entire browser command, including cleanup, to exit successfully.

## 2026-10-19 Gate 1 mockup generator assumed a newer pathlib API

- What happened: the first static mockup generator stopped before writing a
  screen because the system Python does not support `Path.write_text(newline=)`.
  No production code or evidence changed.
- Root cause: the writer assumed an optional argument from a newer interpreter.
- Prevention rule: write generated standalone HTML as explicit UTF-8 bytes, or
  verify the selected interpreter's writer signature before using optional APIs.
  The corrected generator uses byte writes and ran successfully.

## 2026-10-19 Gate 1 mockup hosting notice inherited a paragraph width cap

- What happened: the first desktop preview measured the proposed full-width
  hosting notice at 605px in a 1280px viewport. The mockup was not yet accepted.
- Root cause: the generic paragraph measure also constrained the notice block.
- Prevention rule: exempt full-width notices from prose measure and assert their
  rendered width against the viewport before claiming the composition is fixed.
  The mockup selector now sets `max-width: none`. Production source is unchanged.

## 2026-10-19 Gate 2 approval patch included an unverified sentence anchor

- What happened: the first multi-file approval patch was rejected because one
  proposed anchor sentence was absent. The patch changed no files.
- Root cause: an unnecessary wording edit used assumed context instead of an
  exact current-file anchor, contrary to the existing AGENTS.md rule.
- Prevention rule: preflight every anchor before a multi-file patch; omit optional
  edits whose context has not been copied from the file. The corrected patch
  records approval without that unsupported edit.

## 2026-10-19 Gate 3 design patch repeated an absent-anchor error

- What happened: a documentation repair patch included a sentence absent from
  the current draft. The tool rejected the patch before writing any files.
- Root cause: a leftover hunk used text from a different document without
  preflighting every anchor, repeating the logged Gate 2 patch mistake.
- Prevention rule: read every exact target range immediately before a patch,
  remove unrelated hunks and verify all anchors. The corrected patch changes
  only the confirmed draft statements. No production code was affected.

## 2026-10-19 Gate 3 static-study focus probe gave mixed observations

- What happened: one call batched three viewport changes, an anchor click and an
  immediate measurement. It saw no focused target and panel top 942.98px, after
  an earlier separate probe had seen target focus and top 15.98px. A later click
  followed by a fresh accessibility observation again saw focus and top 15.98px.
  The study source was unchanged between these observations. Both receipts are
  retained in `/tmp/shiftwork-gate3-browser.json` and
  `/tmp/shiftwork-gate3-settled-focus.json`.
- Root cause: unconfirmed. The combined resize/navigation/read probe was timing
  sensitive; the later pass does not establish reliable automated focus proof.
- Prevention rule: separate viewport changes from navigation verification, read
  settled URL/accessibility state before geometry, and report mixed results as a
  verification limit instead of overwriting the failed observation.


## 2026-10-19 S29: disposable root used the macOS default temporary directory

- What happened: the initial baseline copy used the macOS temporary directory instead of the approved /tmp/shiftwork-s29-* location. It was moved intact to /tmp before any test ran.
- Root cause: tempfile.mkdtemp omitted its dir argument.
- Prevention rule: pass dir="/tmp" explicitly for every S29 disposable root and assert its parent before writing artifacts.


## 2026-10-19 S29: browser failure check assumed the latest preview run failed

- What happened: the first connected browser check rendered WebGL2 but failed its independent-failure assertion because the latest preview run passed.
- Root cause: the recorded preview contains two runs, and the failure belongs to the first incident-opening run.
- Prevention rule: inspect actual preview records and navigate to the incident-opening run before asserting its literal failed check and captured answer. Preserve the rejected receipt.


## 2026-10-19 S29: fallback focus probe chose the wrong editor panel

- What happened: a graphics-failure probe preserved bytes and caret but reported lost focus.
- Root cause: it selected Investigate, while the editable draft is in Compare. The hidden editor could never receive focus.
- Prevention rule: inspect the current editor owner, select its visible panel and assert initial focus before releasing each graphics fault. The rejected receipt is retained.


## 2026-10-19 S29: packaging and performance probes had invalid harness bounds

- What happened: clean installation passed but the extracted browser rejected macOS /private/tmp, the canonical spelling of approved /tmp. A separate 30-second performance sample exceeded the runner's 30-second CDP deadline. Neither failed attempt counts as product proof.
- Root cause: path validation ignored the macOS alias, and the command deadline equalled the entire sample duration. Review also found timer-paced samples and renderer.info reset after shadows would misattribute the limiting work.
- Prevention rule: normalize owned path aliases, give CDP commands bounded overhead beyond samples, drive load with RAF, and reset renderer.info before the complete shadow/render pass. Retain rejected receipts.


## 2026-10-19 S29: added identity header pushed native intake control out of reach

- What happened: the unchanged Bellwether browser regression found the Customer queue control at y=871..921 in a 900px viewport at 390px width.
- Root cause: the new evidence identity header increased vertical height while intake remained on the second station row.
- Prevention rule: put inspection intake first in the labelled station list and run the existing native-touch initial-viewport reach assertion before accepting layout. No control or assertion was reduced.


## 2026-10-19 S29: fractional scroll alignment clipped the selected panel edge

- What happened: the unchanged GTM and Northline journeys reached their panels with focus, but the 390px panel top was -0.390625px and failed the required nonnegative reach assertion.
- Root cause: scrollIntoView aligned a fractional layout coordinate to an integer scroll position with no scroll margin.
- Prevention rule: give the selected panel an explicit scroll margin and reset desktop sticky styling at the actual stacked-layout breakpoint. Keep the precise reach assertion and rejected receipts.


## 2026-10-19 S29: optional-host watchdog started too late

- What happened: independent review found a hanging host import could remain loading indefinitely; the injected host-timeout case reproduced that failure.
- Root cause: the eight-second watchdog lived only inside the optional host, after its own import completed.
- Prevention rule: bound the outer optional import in the controller too, invalidate its epoch on timeout, and prove dirty-workbench fallback plus late-import rejection independently.


## 2026-10-19 S29: review exposed stale graphics and projection ownership assumptions

- What happened: independent review reproduced a failure notice hidden by history reset, a valid backend-nominated legacy first-choice inspection marked conflicting, an unchecked old-shift investigation, and static fallback art unhidden over WebGL by ordinary renderBoard. Failing focused probes retained each defect.
- Root cause: graphics failure/visibility ownership was split across reset/render paths, while projection ownership assumed every current inspection belonged to the new shift.
- Prevention rule: preserve latched graphics failure, let ready graphics own fallback visibility, check station shift ownership, and distinguish the backend-nominated legacy fallback without relaxing current-operation joins.


## 2026-10-19 S29: delayed graphics construction rendered before suspension

- What happened: review found a delayed import could construct and draw once after the scene became hidden, offscreen or expanded. Three isolated failing host checks reproduced allocation after suspension.
- Root cause: suspension was applied after scene construction instead of before starting or accepting a mount.
- Prevention rule: wait for observed visibility, cancel pending mount ownership when suspended, and test each suspension condition independently before accepting graphics lifecycle.


## 2026-10-19 S29: lifecycle probes assumed visibility from scroll intent

- What happened: the first lifecycle run waited for deferred graphics below its default viewport. A later offscreen probe counted a legitimate frame while the scene was still partly visible.
- Root cause: the harness assumed the default viewport and scrolling to document end established the desired visibility condition.
- Prevention rule: set the actual viewport explicitly and assert the canvas bounds establish offscreen state before interpreting frame counts. Keep both rejected attempts.


## 2026-10-19 S29: cold-start loop observed the previous document

- What happened: the corrected performance run printed five exactly identical cold timings. Those timings are rejected, not five measurements.
- Root cause: Page.navigate returned before the old ready DOM was replaced; the readiness predicate did not require a new timeOrigin. Source interception also cannot certify native download timing.
- Prevention rule: require five distinct document timeOrigin values, measure cold delivery with unmodified HTTP responses, and use separate injected instrumentation only for geometry/frame samples. Retain the rejected receipts.


## 2026-10-19 S29: performance instrumentation reused a fault-only import gate

- What happened: five native cold starts completed, but enabling frame instrumentation then left the scene import held and the warm-up failed. No complete performance receipt is claimed from that attempt.
- Root cause: the plain-source measurement mode was incorrectly treated as a graphics-fault mode after instrumentation was enabled.
- Prevention rule: exclude the plain measurement mode from fault-only import gates and persist each cold-start receipt before beginning frame samples.


## 2026-10-19 S29: context cleanup fault was intercepted by earlier lifecycle work

- What happened: geometry and material omission controls reached their intended assertions, but context omission hit the multiple-context guard before the intended old-context assertion. The context row is rejected.
- Root cause: the context omission affected the preliminary error/recovery case as well as the targeted switch.
- Prevention rule: enable the context omission only for the target switch and require the actual WebGL isContextLost assertion, then restore and rerun.


## 2026-10-19 S29: repeated baseline browser run reused a consumed preview

- What happened: a later baseline browser run expected two captured customers but the latest run was an earlier test diagnostic with one output.
- Root cause: the runner reused a preview changed by a previous browser journey rather than creating a fresh baseline.
- Prevention rule: start a new disposable preview for each complete baseline journey and retain failed fixture-state receipts. Do not change assertions to fit consumed state.

## 2026-10-19 S29: rendered control boundaries inherited insufficient contrast

- What happened: the rendered-style contrast check found unselected station borders at 1.71:1 and the graphics control focus ring below its approved 3:1 threshold.
- Root cause: translucent legacy station borders and a blue focus color were reused on the navy workplace.
- Prevention rule: measure the actual composed styles, use opaque boundaries and the approved amber focus on dark backgrounds, and keep text/control contrast checks beside the renderer.


## 2026-10-19 S29: context limit was discovered after being exceeded

- What happened: direct runtime-log inspection reported about 414k context against the project's 175k stop limit. Work had already continued beyond that limit. New work stopped and the current cleanup/handoff step finished.
- Root cause: no visible usage indicator was surfaced, and the agent's context estimate was too low.
- Prevention rule: inspect this chat's latest token_count.last_token_usage.input_tokens at phase boundaries when the UI indicator is absent. Stop at 175k unless the user explicitly extends it.

## 2026-10-19 S29 continuation: preview probe guessed an API path

- What happened: the first read-only preview probe returned 404 for
  `/api/boards/bookshop/board`. No data changed. The existing documented
  `/api/engagements/bookshop/board` returned 200.
- Root cause: the probe inferred a route instead of copying the current client.
- Prevention rule: copy `engagementPath()` or an existing browser request before
  constructing preview probes, including read-only resumption checks.

## 2026-10-19 S29: page-cache refresh lost restored editor focus

- What happened: two actual persisted page-cache returns kept the same dirty
  editor and backward caret range, but lost focus after controller refresh.
- Root cause: refresh temporarily disables the editor during loading, which
  drops the browser-restored focus after the pageshow event.
- Prevention rule: capture editor focus/selection before the return refresh and
  restore it only for the same generation, intent and node when another control
  has not received focus. Require actual persisted events in the browser test.

## 2026-10-19 S29: retry probe mixed data-refresh and graphics focus effects

- What happened: explicit graphics retry recovered, but its continuity assertion
  failed because the preceding test-only data refresh had already dropped focus.
- Root cause: the runner measured two different actions under one focus assertion.
- Prevention rule: assert or establish focus immediately before the action being
  measured. Keep the same dirty bytes, caret and original failure receipt.


## 2026-10-19 S29: zoom keyboard probe omitted Enter text

- What happened: native 200% zoom was established at 1280px, but the keyboard
  station activation probe did not activate the focused button.
- Root cause: the new runner omitted the Enter text/unmodifiedText fields that
  the existing browser runner supplies. The helper was corrected but not rerun
  before the context stop. This remains unproved, not a passing zoom result.
- Prevention rule: copy the current native-key helper contract before adding
  keyboard checks. Retain both the rejected receipt and the unverified status.


## 2026-10-19 S29 continuation: native zoom exposed narrow layout defects

- What happened: the corrected zoom runner passed keyboard activation, then one
  touch check failed. Diagnostic repeats reached the controls. Chrome also
  clamped a requested 390px native window to 500px. After retaining native 200%
  zoom and setting the exact viewport, the 195 CSS-pixel page overflowed to 266px.
  The picker imposed its minimum content width. Two-column station labels also
  escaped their cells. Visual inspection then found overlapping journey labels
  despite a zero-overflow page measurement.
- Root cause: the runner assumed the requested native window width was honored;
  the layout and its checks had not covered the resulting narrow CSS width or
  text escaping an otherwise bounded navigation cell.
- Prevention rule: record native zoom, pinch scale, actual viewport and outer
  window separately. Test label bounds as well as page bounds, inspect native
  screenshots, and independently omit each narrow-layout rule. Keep controls
  usable without clipping or reducing their target size.

## 2026-10-19 S29 continuation: zoom input observations were intermittent

- What happened: an early touch check failed once and passed diagnostic repeats.
  A later layout omission run failed keyboard reach before its intended CSS
  assertion. That row was rejected and did not count as a caught layout fault.
  A short diagnostic also read document.body before document creation and failed.
- Root cause: the input runner could observe a panel while smooth scrolling was
  unfinished. The precise missed event was not captured, so timing is a suspected
  cause, not an established explanation for every failed input observation. The
  diagnostic's readiness predicate separately lacked a null-safe body check.
- Prevention rule: wait for stable panel position, retain per-station focus and
  bounds receipts, and check null-safe readiness. Isolate a layout omission at
  its affected 195 CSS-pixel width before unrelated navigation. Clean/restored
  runs still exercise all three widths. Do not erase earlier flaky receipts.

## 2026-10-19 S29 continuation: fault table selected an inherited constructor

- What happened: fresh packaging passed its locked install, backend journeys and
  extracted room, then failed constructor fallback with "function is not
  iterable" from the test runner. The failed package receipt remains retained.
- Root cause: omissions[sceneFault] selected Object.prototype.constructor for the
  existing constructor-failure case, then tried to destructure that function.
  The previous continuation added the omission table after its last full package
  proof, leaving this combination untested.
- Prevention rule: use Object.hasOwn for fault-table membership, including new
  tables. Repeat the real extracted constructor-failure workbench path after
  fault-runner changes; unit or plain-room success cannot replace that check.

## 2026-10-19 S29 native continuation: default temporary directory escaped the approved root

- What happened: tempfile.mkdtemp used macOS TMPDIR under /var/folders instead
  of the approved /tmp/shiftwork-s29-* receipt root. Only owned snapshot files
  existed. They were moved intact to /tmp/shiftwork-s29-native-7w758y7j before
  the probe or production edit.
- Root cause: the helper relied on the platform default rather than an explicit
  directory argument.
- Prevention rule: use tempfile.mkdtemp(dir='/tmp', prefix='shiftwork-s29-') for
  these bounded receipts and verify the actual returned path before more writes.

## 2026-10-19 S29 native continuation: browser navigation and shortcuts changed probe conditions

- What happened: Cmd+Home navigated Safari to its Home page, and new diagnostic
  URLs reset native page zoom to 100%. The Home navigation was reversed; the
  nonmatching zoom observations were retained and excluded from 200% claims.
- Root cause: the probe assumed a scroll shortcut and persistent zoom across
  native navigations.
- Prevention rule: use observed native scroll controls, read Safari's actual zoom
  menu after navigation and require the recorded viewport/DPR/pinch preconditions
  before comparing variants. Native tool errors are not product-test passes.

## 2026-10-19 S29 exact-viewport harness: touch landed during a smooth scroll

- What happened: the new exact 640x900 and 390x844 checks failed with the touch
  activating a different station, then with a null hit point. Mobile emulation
  also reset native page zoom so innerWidth equaled the physical width.
- Root cause: activateStation smooth-scrolls the focused panel. The harness
  captured tap coordinates before that scroll settled, and mobile emulation
  changed the zoom and DPR preconditions the check was measuring.
- Prevention rule: use mobile=false for native-zoom viewport checks, wait for a
  stable scroll position, assert the hit element is the intended control, blur
  competing focus before a touch reach check and dispatch at freshly computed
  coordinates.

## 2026-10-20 S31 harness: page-evaluate scope, publication baseline and the wrong preview mode

- What happened: the ownership control runner threw `ReferenceError: beforeAttempts
  is not defined` because a page `evaluate` callback referenced Node-scope
  variables. The history hold control then counted legitimate comparison
  publications made after inspection was restored as stale. A board journey
  failed because it used the S31 preview with the recorded assist gateway, so
  the assist request correctly succeeded instead of producing the journey's
  expected 409.
- Root cause: browser `evaluate` callbacks run in isolated scope, the hold
  control needed a publication baseline captured before the fault, and the
  board journey's no-gateway denial requires `create_preview` without
  `recorded_assist`.
- Prevention rule: pass every value a page callback reads as an argument, scope
  publication assertions to a pre-fault index, and use the preview mode that
  matches the journey's expected failure (no assist gateway for `browser.mjs`).

## 2026-10-20 S33 source fault: a redundant guard hid its own proof

- What happened: the new no-selection later-experiment fault survived because the
  version-binding guard rejected the same fixture, so the mutation did not own a
  distinct assertion. The initial later test fixture also omitted the required
  observed run and original candidate versions.
- Root cause: the no-selection condition was already covered by the binding rule,
  and the test fixture was not modeled from the real later-experiment shape.
- Prevention rule: give every acceptance condition a fixture where only that
  condition can fail. Remove guards that duplicate a stricter binding rather than
  adding a fault row that cannot isolate them.

## 2026-10-20 S33 browser harness: new mode fell through the generic scene gate

- What happened: the first S33 `openBrowser` call used a new fault prefix. The
  generic gate held `workplace-scene.js`, so the room stayed in loading and the
  test timed out before exercising any S33 behavior.
- Root cause: the harness mode allowlist recognized S30, S31 and S32 prefixes but
  not S33.
- Prevention rule: when adding a browser control mode, inspect every mode gate in
  `openBrowser` first and add the new prefix to the allowlist before judging a
  graphics timeout as a product defect.

## 2026-10-20 S33 exact viewport: owner tabs overflowed at 200% zoom

- What happened: the expanded owner station list surfaced a real narrow-layout
  failure. The requirement tabs exceeded the viewport at 390px and 200% zoom, and
  the station order left the draft editor hidden before the Escape continuity
  check.
- Root cause: the file-tab row did not wrap, and the new stations were appended
  after Compare even though the editor check assumed Compare remained selected.
- Prevention rule: run every new panel through the exact narrow and zoom matrix
  before accepting it, and keep view-dependent test steps explicit instead of
  relying on the previous loop iteration's station.
