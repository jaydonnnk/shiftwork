# Program design: Shiftwork 3D workplace

Gate 3 APPROVED, 2026-10-19, Asia/Singapore.

Jaydon said "seems good. I approve." and separately authorized committing Gates
1 to 3 in focused batches and pushing main. Gate 4 remains unwritten.

[Gate 1](01-product.md) and [Gate 2](02-architecture.md) are approved. S28
remains accepted. This document specifies presentation only. It contains no
implementation, dependency acquisition or Gate 4 slice assignment.

## 1. Approved decisions

- Four new vanilla-JavaScript modules separate public projection, graphics
  lifecycle, rendering and original room definitions. The existing controller
  retains all requests, commands, drafts and navigation.
- Pin Three.js r180, package 0.180.0, with two local runtime modules. Section 3
  fixes the source and checksum procedure. No vendor file is acquired here.
- Use the [visual specification](visual-spec.md) and its
  [colour and composition study](mockups/08-visual-spec.html). The study is a
  static planning illustration, not final artwork or working 3D.
- Ordinary loading preserves one accepted presentation reference. Errors,
  contradictory joins and context changes break motion continuity. Several
  HTTP reads still do not form an atomic snapshot.
- Establish the entire Bellwether decision and inheritance journey before
  extending the same boundary to distinct Stonebridge and Northline rooms.
  This is an acceptance dependency, not a slice plan.

## 2. Files and dependency direction

All paths in this section are repository-relative. These are future file
contracts. Only planning documents and the static study are written at this gate.

| File | Responsibility |
|---|---|
| `shiftwork/client/app.js` | Publish accepted presentation inputs at the sites in section 6. Route picks through `activateStation()`. Own the expanded-workbench control. Keep all existing command handlers. |
| `shiftwork/client/index.html` | Full-width hosting notice, optional scene container, graphics status and retry, labelled station navigation, complete persistent workbench, expand and restore controls. Preserve existing control IDs and sections. |
| `shiftwork/client/styles.css` | Approved two-column layout, compact layout, evidence hierarchy, focus, motion preference and expanded-workbench layout. Replace the old unconditional `data-evidence` success-looking animation. |
| `shiftwork/client/workplace-view.js` | Pure allowlisted projection, identity consistency checks and a pure confirmed-difference function. Import only `selectEvidence` from `evidence.js`. No DOM, engine, network or command imports. |
| `shiftwork/client/workplace-host.js` | Optional graphics coordinator. Own lazy import, latest publication, continuity reference, observers, retry, page lifecycle and callback fencing. No API access. |
| `shiftwork/client/workplace-scene.js` | Three.js renderer, picking, shared primitive builders, resource ownership, on-demand drawing and bounded transitions. Import local engine and room definitions only. |
| `shiftwork/client/workplace-rooms.js` | Original declarative geometry, material choices, station anchors and camera bounds for the three rooms. Plain data, no engine, network or DOM imports. |
| `shiftwork/client/vendor/three-r180/three.module.js` | Unmodified upstream renderer entry module. |
| `shiftwork/client/vendor/three-r180/three.core.js` | Unmodified upstream core module, imported by the entry module. |
| `shiftwork/client/vendor/three-r180/LICENSE` | Exact upstream MIT notice, shipped locally. |
| `shiftwork/client/vendor/three-r180/manifest.json` | Source, version, package integrity and per-file byte length and SHA-256 records. Acquisition is a later authorized action. |
| `shiftwork/client/workplace-assets.json` | Original-asset provenance for each room assembly, fallback and shared primitive/material definitions. Record source file and digest after authoring. |
| `shiftwork/client/THIRD_PARTY_NOTICES.md` | Engine version, MIT attribution and local license link. Design reference is separately credited as inspiration, never as an imported asset. |
| `shiftwork/client/room.svg` | Preserve the accepted original Bellwether static fallback. Existing Northline and GTM inline artwork remains fallback content in `index.html`. No dependency on a new exported image. |
| `tests/client/workplace_view.test.mjs` | GPU-free projection and transition checks using literal public examples. |
| `tests/client/workplace_browser.mjs` | Serve the real client, drive stations, editing, lifecycle, failure and responsive access. Reuse `env.mjs` and existing browser-runner patterns. |
| `tests/client/workplace_faults.mjs` | In-memory served-source faults with one named failing assertion per guard. Never mutate untracked production files. |
| `tests/client/workplace_perf.mjs` | Repeatable graphics budget measurements and machine-readable receipts. Test instrumentation is injected by the browser runner, not exposed as a production global. |
| `tests/packaging/test_client_asset_closure.py` | Enumerate local imports and asset references, verify manifests and reject missing, external or undeclared dependencies. |
| `tests/packaging/test_clean_env_install_and_run.py` | Replace the three-asset-only check with complete extracted HTTP delivery and actual browser module loading. Existing clean-install authority is still required. |
| `tests/client/browser.mjs`, `gtm_browser.mjs`, `northline_browser.mjs` | Preserve their behavioral assertions and extend rendered integration checks. Update fault anchors in `render_faults.mjs`, `gtm_faults.mjs` and `northline_faults.mjs` only when changed production statements require it. |
| `README.md` | Explain local HTTP delivery, graphics fallback, pinned notices and supported-device evidence after implementation. |
| Scoped and root authority documents | Record only approved decisions and actual later evidence. Keep historical S28 records intact. |

Import graph: `app.js` statically imports the pure view and dynamically imports
the host after workbench startup. The host dynamically imports
`workplace-scene.js`. The scene imports `workplace-rooms.js` and
`vendor/three-r180/three.module.js`. The latter imports `./three.core.js`.
No import map, bare package specifier, addon, external font, worker, loader,
post-processing library, runtime Node service or build step is required.

The pure view is a required engine-free application module, like existing
`evidence.js`. The host and its graphics descendants are optional and load
behind a caught promise after DOM navigation and initial refresh have started.
A failed host, scene or engine module cannot prevent workbench startup. Until
the host exists, the controller retains just its newest publication for delivery
on attachment; the static fallback and HTML status remain available. No schema,
endpoint, Python dependency, database, protected fixture or domain ADR changes.
The current `pyproject.toml` has no client package-data declaration. Verify actual
source-archive contents and served bytes rather than assuming a wheel includes
nested assets. A wheel-distribution change would need an explicit scope decision.

## 3. Engine release, import closure and records

Select a fixed inspected release rather than a moving latest URL:

| Record | Value |
|---|---|
| Upstream | `https://github.com/mrdoob/three.js` |
| Release | [r180](https://github.com/mrdoob/three.js/releases/tag/r180), npm `three@0.180.0` |
| Commit | `0af9729d0c143a86a1d725d6e2c3ad83301f3f34` |
| Authorized future acquisition source | `https://registry.npmjs.org/three/-/three-0.180.0.tgz` |
| Registry metadata read at this gate | `https://registry.npmjs.org/three/0.180.0` |
| Published package SHA-512 integrity | `sha512-o+qycAMZrh+TsE01GqWUxUIKR1AL0S8pq7zDkYOQw8GqfX8b8VoCKYUoHbhiX5j+7hr8XsuHDVU6+gkQJQKg9w==` |
| License | MIT. Retain the complete release LICENSE and existing source headers. |
| Runtime extraction allowlist | `package/build/three.module.js`, `package/build/three.core.js` |
| Notice extraction | `package/LICENSE` |
| Per-file SHA-256 and size | NOT ACQUIRED. Required in the future manifest before use or packaging. No invented digest or null treated as verified. |

Read-only primary-source inspection at this gate confirms the release/package
identity and the entry module's relative core dependency. The specified closure
is two runtime modules. The complete acquired bytes must still pass recursive
import verification before acceptance. Source inspection is not an extracted
package test. See the [release source entry][module], [core][core],
[package metadata][package] and [license][license].

After separate acquisition authority, verify the tarball against the published
SHA-512 before extracting only the allowlist. Record acquisition date, source URL,
commit, version, license SPDX identifier and each retained file's relative path,
byte length and SHA-256. Reject an unexpected import instead of adding it
silently. Serve these exact bytes unchanged, without minification or line-ending
conversion. Do not ship the package's examples, tests or other builds.

`manifest.json` has `schema_version`, `name`, `version`, `upstream_commit`,
`source_url`, `archive_integrity`, `acquired_at`, `license` and `files` fields.
Each file record has `path`, `bytes` and `sha256`. The validator rejects
placeholders, duplicate paths, path escape, missing files and digest mismatch.
The manifest does not hash itself. It does hash the retained LICENSE.

Each `workplace-assets.json` entry has `asset_id`, `board`, `source_path`,
`source_sha256`, `origin`, `author`, `license` and `external_inputs`.
Procedural rooms cite `workplace-rooms.js`, shared geometry cites
`workplace-scene.js`, and static fallbacks cite their existing source files.
Use actual authorship when assets exist. `origin` is `shiftwork-original` or
`shiftwork-existing`; external inputs are an empty list for these assemblies.
No robot, factory set, screenshot texture, reference source, purchased model,
font download or generated bitmap is part of this plan.

This older fixed release is a deliberate, challengeable pin, not a claim that it
is newest or security-certified. Before acquisition, review its current upstream
advisories and browser syntax. A required release or graph change returns to this
design for explicit revision. Gate 3 approval alone does not acquire anything.

## 4. Types and signatures

Notation below describes plain JavaScript objects and JSDoc contracts. These
are signatures, not TypeScript files, runtime validators or implementation bodies.
Public API enum spellings are preserved. Unknown values stay unknown.

```text
BoardSlug = "bookshop" | "gtm" | "northline"
StationId = one of the active board's IDs in section 7
LoadState = "loading" | "ready" | "empty" | "error"
Inspection = { mode: "current" | "history", historicalRunId: string | null }

PublicPresentationInput = {
	slug, loadedShiftId, generation, intent, loadState, inspection,
	board, operatingVersion, stationView, run, outputs, checks, events, ledgerStatus,
	comparison, diagnostic, candidates, selectedOutputId, activeStation
}
// API objects above are existing public projections, never repository rows.
// This input stays within the controller/view boundary; the scene sees SceneView.

SceneView = {
	schemaVersion: 1,
	context: { board: BoardSlug, shiftId: string | null, inspection: Inspection },
	station: StationId,
	shiftState: "open" | "closed" | null,
	operating: null | {
		selectionId, kind, versionId, contentHash, comparisonId,
		retainedAlternativeId, requirementSetHash, validity
	},
	saved: { latestVersionId: string | null, draftBaseVersionId: string | null },
	run: null | { id, shiftId, versionId, selectionId, state, purpose, evidenceMode },
	evidence: null | {
		runId, outputId, ordinal, checks: [{ id, verdict, reasonCode }],
		linkedEventIds: string[], completeness: "linked" | "missing" | "conflict"
	},
	investigation: { latestEntryId: string | null, count: number },
	tests: { diagnostic: ExperimentSummary | null,
		comparison: ExperimentSummary | null, later: ExperimentSummary | null },
	consequences: { chainStatus: "VALID" | "unknown", eventCount: number | null,
		totals: [{ name, count }], events: ConsequenceSummary[],
		incidents: [{ id, state, reasonCode, openingRunId, openedEventSeq }] },
	inheritance: { selectionId: string | null, comparisonId: string | null,
		requirementSetHash: string | null, visibleCheckSetHash: string | null },
	consistency: "linked" | "incomplete" | "conflict"
}
ExperimentSummary = {
	id, shiftId, kind, state, evidenceClass, contextHash, outcomeStatus,
	candidates: [{ label, versionId, contentHash, eligible: boolean | null,
		blockingReasonCodes: string[] }],
	trials: [{ ordinal, candidateLabel, runId, versionId, state, evidenceMode,
		missingEvidenceCount }], observedRunId: string | null
}
ConsequenceSummary = {
	id, seq, hash, type, synthetic,
	link: null | { runId, checkId, outputId, ordinal, verdict },
	signalRef: string | null, owner: string | null, recordRef: string | null,
	incidentId: string | null, versionId: string | null
}

Publication =
	{ kind: "loading", context, generation } |
	{ kind: "accepted", view: SceneView, generation, intent, reason } |
	{ kind: "reset", context, reason: "error" | "context" | "history" |
		"conflict" | "unavailable" | "page-lifecycle" }

projectWorkplace(input: PublicPresentationInput): SceneView
diffWorkplace(previous: SceneView | null, next: SceneView): Transition[]
Transition = { key, kind: "station-focus" | "test-update" |
	"selection-change" | "linked-consequence", stationId, publicRefs: string[] }

createWorkplaceHost({ container, fallback, status, onStation }): WorkplaceHost
WorkplaceHost.publish(publication: Publication): void
WorkplaceHost.setExpanded(expanded: boolean): void
WorkplaceHost.retry(): void
WorkplaceHost.dispose(): void
onStation({ board, shiftId, stationId, mountToken }): void

createWorkplaceScene({ container, view, tier, reducedMotion, onPick,
	onFailure }): SceneHandle
onPick(stationId: StationId): void
SceneHandle.apply(view: SceneView, transitions: Transition[]): void
SceneHandle.resize({ width, height, pixelRatio }): void
SceneHandle.setSuspended(suspended: boolean): void
SceneHandle.setReducedMotion(reduced: boolean): void
SceneHandle.dispose(): void
onFailure(code: "webgl-unavailable" | "context-lost" | "shader-failed" |
	"render-failed"): void

roomDefinitions: Readonly<Record<BoardSlug, RoomDefinition>>
RoomDefinition = { bounds, cameraTarget, materials, assemblies, stationAnchors }
```

`view` is a fresh allowlisted object with no references to mutable controller
arrays. Treat it as immutable; development checks freeze it. No full response
body, source file, cause/falsifier prose, rationale, request text, raw event
payload, opaque expected reference, catalog record, private path or credential
enters the scene. The workbench retains all public detail and full identities.
The scene may show an abbreviated version hash, but its HTML selection summary
always exposes the complete value. Labels use text nodes, never HTML injection.

## 5. Field ownership, consistency and motion

| View field | Current source and rule |
|---|---|
| Context and shift | `state.slug`, `board.engagement_slug`, `board.latest_shift`, `loadedShiftId`. Reject board/shift disagreement; a missing shift is a legitimate empty state. |
| Operating version | `board.operating_selection`, separately from `latest_version`. When selected source is loaded, require matching `id` and `content_hash`. Never promote a candidate based on save, experiment, timestamp or scene position. |
| Executed version and purpose | `state.run`, using `RunView.purpose`, `evidence_mode`, `selection_id`, `artifact_version_id` and `shift_id`. Show `LEGACY_OPERATION` explicitly. |
| Selected evidence | Output with `id === state.selected`, matching the loaded run. Call existing `selectEvidence(output, checks, events)`. Copy only check identities/verdicts and event references. An empty result means missing evidence, not pass. |
| Investigation | `stationView.investigations` and `latest_investigation_id`, with matching station shift. No credit from unsent text or accepted help. |
| Diagnostic | Current matching `state.diagnostic`, otherwise matching `stationView.latest_diagnostic`. It remains a diagnostic even if complete. |
| Qualifying comparison | Matching `state.comparison`, otherwise `stationView.latest_experiment` only when kind is `QUALIFYING_COMPARISON`. Candidate identity comes from `candidates`; eligibility and blockers come from `outcome.eligibility`. Missing outcome is unknown. |
| Later experiment | `stationView.latest_experiment` only when kind is `LATER_CONDITION_COMPARISON`. Preserve `observed_run_id`; it cannot replace operation, selection or wall totals. |
| Consequence wall | Public ledger `events`, `board.ledger_totals`, `ledger_event_count`, `incidents`, chain status. Event identity is board plus `seq` plus `hash`. Copy only the board-specific allowlist below. |
| Inheritance | Selection identity plus `board.inherited_requirements` hashes. Rationale, tests, limits, runbook and complete history remain in existing `renderNext()` and deployment panels. No copied prose in scene state. |

The controller adds `state.ledgerStatus`, reset to unknown by `clearData()` and
assigned `ledger.chain_status` with `events: ledger.events` at accepted refresh.
Pass it explicitly as `PublicPresentationInput.ledgerStatus`. Require VALID
board and ledger status and `board.ledger_event_count === events.length`.
The existing `board_snapshot()` at `orchestrator.py:2066-2068` counts events by
type. Compare that same simple type histogram against `board.ledger_totals`,
treating an absent type as zero. This checks whether the reads agree; it does
not recalculate business effects or validate assessment. Check
available relations, including incident opening seq/run/check/output and
comparison candidate versions. Do not recompute grading, sum ledger business
rules or claim the client re-verifies the server's hash chain.

Multi-read disagreement yields `consistency: conflict`. Keep independently
confirmed records labelled by source, show the inconsistency, reset continuity
and suppress causal travel. A missing optional check yields `incomplete`, with
that evidence route quiet. Do not invent a join, merge different selections or
erase already recorded partial consequences. There is no extra scene fetch,
retry loop or new snapshot endpoint. Existing refresh can later reconcile reads.

Board-specific wall allowlist:

- Bellwether: `SALE_COMPLETED`, `REFUND_REQUIRED`, `ESCALATION_TO_HUMAN`,
  `BACKLOG_RECORDED`, `INCIDENT_OPENED`, `INCIDENT_RESOLVED`, `LIMIT_DECLARED`.
- Stonebridge: `OWNER_ASSIGNED`, `SLA_CLOCK_STARTED`, `HANDOFF_ESCALATED`,
  `INCIDENT_OPENED`, `INCIDENT_RESOLVED`, `BACKLOG_RECORDED`, `LIMIT_DECLARED`.
- Northline: `BOOKING_COMMITTED`, `ESCALATION_TO_HUMAN`,
  `COUNTER_FOLLOWUP_RECORDED`, `ROLLOUT_APPROVED`, `HANDOVER_DECLARED`,
  `INCIDENT_OPENED`, `INCIDENT_RESOLVED`, `BACKLOG_RECORDED`, `LIMIT_DECLARED`.

Other public events remain visible in the workbench as recorded text. No unknown
event becomes a new visual outcome. Geometry never duplicates event quantities
as a crowd of objects. A labelled tally represents the recorded count.

### Continuity and motion eligibility

The continuity identity is board, shift and inspection mode, with historical run
ID only in history mode. It excludes refresh generation and active station.
Generation still rejects stale network results. A station or output selection
updates focus immediately; inspecting evidence never creates fresh-execution motion.

The host stores only the latest publication and one prior accepted `SceneView`.
There is no event replay queue or persistent cursor. A repeated accepted view
produces no transition. Every accepted view advances the reference even while
motion is disabled or graphics is suspended.

`linked-consequence` is allowed only on a continuous, visible, current-context
update with all of these facts:

1. A new event ID was absent from the previous accepted view.
2. The loaded run has purpose `OPERATION`, the current shift ID and the exact
   selection ID and version. Neither view has a conflict. The new event's route
   is linked; the previous route may legitimately have been pending/incomplete.
3. The event is synthetic and its derivation matches a loaded output ordinal,
   run and check through `selectEvidence`. Verdict and type remain explicit.
4. The change is accepted after loading, not after a reset, history navigation,
   retry, page-cache return or board/shift change.

This is recorded evidence arrival, never proof of real-time execution. Failed
operations may have confirmed partial events; their negative or pending meanings
remain visible. FINALIZED alone does not pass a check or create a sale. An event
with no derivation, including an administrative handover/limit record, settles
quietly. Historical events whose run is not loaded also settle quietly without
additional fetches. Preserve them; do not infer their purpose or label them fresh.

Selection change is a short focus/label update after accepted selection only.
It never moves a customer request or changes the wall. Experiment motion remains
on the test bench. Only reported slot states change; no fabricated intermediate
tool steps, completion percentage, inferred model thinking or time-to-finish.

## 6. Exact controller publication sites

Line references below are anchors in `app.js` at `1a943d9`; copy current complete
statements before implementation. Rendering a panel is not itself data acceptance.
Add one controller-local `publishPresentation(reason)` entry point. It assembles
input, calls the pure projector and sends one publication to the host.

| Existing site | Required publication |
|---|---|
| Startup after event bindings, `navigate()` and first `refresh()` invocation | Lazy-import optional host behind a caught promise. Retain only the newest publication until it attaches. Host failure leaves static fallback and HTML status. Initial view is loading or empty, never illustrative data. |
| `refresh()` 273-325, before `clearData('Loading your shift…')` | Publish `loading` for the current context. Preserve last accepted host reference. Do not project temporarily emptied state as accepted. |
| `refresh()` after final generation fence, assignment and selected-output restoration, 307-318 | Publish accepted only after the bundle and station normalization are complete. Carry ledger status. On changed shift, reset before the first new accepted view. |
| `refresh()` catch, after generation check and `clearData(error.message)` | Publish reset/error. Drop continuity and replace numeric scene labels with unavailable markers. Preserve draft behavior and complete DOM recovery controls. |
| `switchWorkplace()` 43-58, after guard admits switch and before slug replacement | Reset/context, invalidate mount and pick tokens. The new room starts from its own first accepted baseline. A refused switch publishes no new board. |
| Incident button in `renderBoard()` 385-395 | Set inspection mode to history and reset before `refresh(opening_run_id)`. After its intent/run fence and output selection, publish the historical baseline. |
| Output button in `renderCustomers()` 482 | After `intent` and selected output change, publish inspection/focus only. Cancel the old evidence route transition; no new-operation motion. |
| `activateStation()` 1180-1223 and `navigate()` 1229-1235 | Publish after mapping, visible-panel and URL/focus updates. No `userIntent` increment during automatic refresh normalization. |
| `saveDraft()` 877-888 | Publish accepted saved identity only after response and refresh; unsaved typing has no tested-version effect. Pending/finally updates never fabricate data acceptance. |
| `freezeCandidate()` 990-1006 | Candidate assignment remains candidate-only. Publish once matching accepted board refresh completes, including failure recovery. |
| `runComparison()` 1008-1038 | After every owned initial/polled `state.comparison = experiment`, publish accepted test state if the board bundle remains available. If loading, retain loading and wait for refresh acceptance. |
| `runDiagnostic()` 1116-1144 | Same rule at both initial and polled `state.diagnostic` assignments. Completion never changes operating history. |
| `chooseCandidate()`, `appendInvestigation()`, assist handlers, `act()` and `shiftAction()` | Their successful data change flows through accepted `refresh()`. No optimistic scene selection, hint success, operation or shift transition before that response. |
| Explicit current-view Refresh, manual operation or newly opened shift | Set inspection mode back to current only as part of the explicit controller action, then reset the history reference. Internal `refresh()` polling never changes inspection mode by inference. |
| `pagehide` 1296 and new `pageshow` handling | Dispose graphics on hide, cancel transient motion. On page-cache return, reattach quietly and use one ordinary controller refresh with existing draft guards; do not resubmit any action. Dirty draft contents and caret survive. |

At comparison/diagnostic acceptance, require the captured slug and loaded shift
to match the returned experiment and current controller owner. Reject an older
generation's attempted scene publication. Navigation intent fences delayed picks
and historical-output selection. Do not cancel a server action because a person
changed station; accepted results can appear through the next ordinary refresh.
A delayed graphics import always applies the newest accepted publication, never
the view captured when import began. An old mount cannot overwrite a newer board.

Call stacks:

```text
Existing refresh reads -> generation/context checks -> controller assignment
  -> existing DOM renders and station normalization
  -> publishPresentation -> projectWorkplace -> host.publish
  -> quiet baseline or diffWorkplace -> scene.apply -> one requested frame

Existing diagnostic/comparison request and polling
  -> owner and identity checks -> accepted test assignment -> publication
  -> test-bench status only -> existing final refresh -> same boundary

Pointer pick -> scene emits station ID only
  -> host adds captured board/shift/mount token and checks current ownership
  -> app checks active board/shift and station list
  -> activateStation(stationId) -> existing panel/focus/history -> publication

Existing explicit selection/operation/close/open button
  -> existing handler and API guard -> accepted refresh -> publication
  -> scene reflects the record; scene never invokes this command stack

Graphics failure -> host cancels/disposes -> static overview and status/retry
  -> existing labelled controls and workbench continue independently
```

## 7. Stations and interactions

Keep the current `activateStation()` aliases and guards as the navigation owner.
The scene emits canonical IDs, never endpoint names or commands.

| Board | Object and emitted station ID |
|---|---|
| Bellwether `bookshop` | Service console `service`; owner desk `owner`; queue `customers`; evidence bridge `pipeline`; assessment plinth `evaluator`; incident wall `ledger`; read-only incident tray `repair`; diagnosis desk `investigate`; paired test bench `compare`; handover shelf `next`. |
| Stonebridge `gtm` | Intake desk `signals`; qualification board `rules`; routing/workflow table `workflow`; ownership and escalation wall `wall`. |
| Northline `northline` | Counter brief `brief`; permission map `map`; integration workbench `bench`; acceptance fixture `acceptance`; pilot schedule `rollout`; runbook shelf `handover`. |

No new combined action or privileged scene callback. The read-only `repair` tray
remains read-only. An unavailable station explains why through the current guard.
The HTML current-task header uses the active station's existing title and links
to its existing work controls. Their current enabled states and help text own
availability. A read-only station offers evidence inspection; if an action is
blocked, keep its reason visible rather than inventing a different unlocked step.
Do not introduce a global workflow planner or copy command-eligibility logic
into the scene projector.
Labels below the canvas duplicate every station destination as normal controls.
At compact widths use that list rather than tiny world-space targets. The canvas
is decorative to assistive technology, `aria-hidden`, and is not a tab stop.
Pointer picking uses a pointer-up hit with at most 6 CSS pixels of movement;
scrolling or dragging never activates a station. No pointer capture blocks scrolling.

Expanded editing uses the same workbench node, not a copied editor or dialog.
An HTML button toggles `aria-expanded` and the CSS layout, suspends the room and
keeps the operating identity, evidence mode and failures above the work. Focus
and caret remain in place. Restore returns the room, quietly, without replay.
Escape restores only when focus is on the expand/restore control or panel chrome;
it never consumes textarea/editor Escape behavior. Mobile station activation
focuses `station-panel` and scrolls it into view through the existing helper.
The first automatic load never steals focus. Exact visual dimensions and motion
timings are in [visual-spec.md](visual-spec.md).

## 8. Lifecycle and failure contract

One host, one active room and at most one live WebGL context. Reuse the renderer
for a board switch; release the previous board's geometry and materials before
creating the next room. Each owned geometry, material and any future texture is
registered once and disposed once, including shared instances. Remove scene
references and picking targets. Dispose renderer resources and release the
context on host teardown. No asset cache survives teardown.

The host owns ResizeObserver, IntersectionObserver, visibility and reduced-motion
listeners and lazy-import tokens. The scene owns canvas pointer/context listeners
and its single cancellable RAF. `apply()` and `resize()` request a frame;
`setSuspended(true)` cancels it, and `dispose()` cancels it and detaches listeners.
No host RAF or separate scheduler exists. Host disposal disconnects its observers,
invalidates callbacks, disposes the scene and removes the canvas.
Dispose is idempotent. Import cannot be cancelled, so its late completion may
cache module code but cannot attach an obsolete scene. A partially created scene
must release allocated resources when initialization throws.

Draw on state, resize, hover/focus changes and active finite transitions only.
No `setAnimationLoop` or permanent idle RAF. Suspend drawing while hidden,
offscreen or expanded. Cancel unfinished transitions when suspended and settle
at the newest state on return. Clamp animation delta to 50ms. A preference
change to reduced motion settles immediately and cancels further travel.

Catch dynamic-import, construction, shader compilation, render and context-loss
failures. Three.js can report shader errors without throwing; hook its shader
error callback as well as thrown failures. Do not print shader/source bodies.
Failure codes are a fixed allowlist: `module-unavailable`, `init-failed`,
`webgl-unavailable`, `context-lost`, `shader-failed`, `render-failed`, `load-timeout`.
After 8 seconds without a ready renderer, invalidate that mount and show fallback.
No stale promise may attach after timeout. No automatic recreation loop.

The fallback says "3D view unavailable. Your workbench is ready." It retains
the static room, all station labels and all existing evidence/editing/command
controls. Retry is a local graphics action, never a page reload, API command or
provider call. Retry uses the newest accepted state as a quiet baseline. Retry
uses the same literal local module URLs, without cache-busting or computed
imports. A browser may retain a failed module evaluation. In that case retry
stays unavailable and explains that the graphics installation needs repair;
it never reloads the page or repeats automatically. Host-import failure uses
the controller-owned retry/status control until a host can attach.
File URLs, CORS errors and missing nested modules fail through the same boundary.
Only the code and tier go to diagnostics, never raw exceptions, payloads or paths.

## 9. Compatibility and numeric budgets

These are proposed acceptance budgets, not measured performance. No device or
browser passes until a later receipt names its exact OS, browser build, GPU,
viewport, DPR, tier and power state. Do not label an emulator a physical device.

| Target | Required future checks |
|---|---|
| Desktop Chromium | Chrome and Edge stable and previous stable at execution time, Windows 11, integrated Intel UHD 620-class GPU, 8GB RAM, 1280x720. |
| Desktop WebKit | Safari stable and previous stable on supported macOS, Apple M1-class hardware, 1280x720. Record exact OS/browser versions rather than guessing future version numbers. |
| Desktop Gecko | Firefox stable on Windows 11 or macOS, same desktop view; full workbench plus WebGL2 smoke and station journey. |
| Narrow browser layout | 640x900 and 390x844 in Chromium and WebKit. Real viewport resize, not screenshot crop. Keyboard, touch and 200% zoom. |
| Physical mobile | iPhone 12-class Safari and Pixel 6-class Chrome, native viewport and compact tier. These are targets, not available or verified hardware claims. |
| Unsupported graphics | WebGL2 denied, software/disabled GPU, module 404, shader failure and context loss. Complete DOM workbench acceptance on every supported browser. |
| Assistive access | Keyboard in Chromium and Safari; VoiceOver with Safari and NVDA with Edge for names, focus and live-status behavior. Browser AX data alone cannot claim audible screen-reader proof. |

Do not UA-detect success. Require WebGL2 construction and actual render success.
Default to compact rendering below 761 CSS pixels or when explicitly selected.
Use standard otherwise. A visible HTML "Simpler 3D" control lowers quality
without changing evidence; no automatic oscillating quality controller.

| Budget | Standard | Compact |
|---|---|---|
| Maximum DPR | 1.5 | 1.0 |
| Triangles per settled frame | 45,000 | 20,000 |
| Draw calls, including shadows | 90 | 45 |
| Lighting | Hemisphere + one directional key | Same, lower-cost materials allowed |
| Shadow maps | One 1024x1024 map; fixed scene bounds | None; simple contact-shadow geometry |
| Authored textures and post-processing | None | None |
| Active-motion frame intervals, median / p95 | <=16.7ms / <=33.4ms | <=33.4ms / <=50ms, cap drawing at 30Hz |
| Estimated owned GPU allocation | <=48MiB | <=24MiB |

Count GPU buffers, shadow/depth attachments and canvas attachments conservatively
from dimensions and formats. Report this as an estimate, not exact driver VRAM.
Use `renderer.info` for draw/triangle/resource counts. No private customer data
enters a performance receipt.

Common budgets:

- Additional engine bytes <=3MiB uncompressed. Additional first-party scene
  JavaScript <=180KiB uncompressed. No downloaded texture/font bytes.
- Additional DOM startup work <=50ms before graphics import. Station activation
  to next painted panel p95 <=100ms, measured separately from network/provider wait.
- Cold graphics-ready time <=3 seconds desktop and <=4 seconds mobile under
  10Mbit/s, 150ms RTT, cold HTTP cache. Measure from optional import request to
  first successful settled frame, including module download, parse and compile.
- Zero scheduled idle graphics frames across 10 seconds after settling. Zero
  graphics frames while hidden/offscreen/expanded, except the final settle frame
  before suspension. Backend polling is measured separately and stays unchanged.
- Across 30 board switches, no more than one live context, old room references
  released, no monotonic geometry/material count growth. After ten warm cycles,
  final live resources may not exceed the same board's warm baseline. Teardown
  returns application-owned resource/listener/frame counts to zero.
- Total source-build zip <35,000,000 bytes. Record the actual final size and
  SHA-256; prior S27/S28 archive measurements do not prove the new package.

Measurement recipe: five cold starts, then three 30-second visible motion samples
per target/tier after a five-second warm-up, plus the idle/hidden/switch cases.
Use deterministic injected public views for repeatable render load; label them
synthetic and separately run the real existing offline browser journeys. For each
sample retain frame intervals, draw counts, startup timings and exclusions.
Compute p95 by nearest rank. Every sample must meet its tier budget; report misses
without averaging them away. Software-rendered CI checks functional behavior,
never certifies physical GPU performance. Missing physical targets remain unproved.
If compact also fails on an intended device, keep work usable through fallback,
record the miss and stop board expansion pending a design decision.

## 10. Test plan and fail-capable controls

These tests are designed here, not implemented or run. Reuse literal public
examples from existing disposable/recorded test inputs; do not author new sealed
cases or consume live calls for graphics proof. Keep current baseline failures
and known evidence limits attached to every later full-suite result.

| Planned check | Observable assertion and deliberate fault that must fail it |
|---|---|
| `projection_separates_saved_selected_executed` | Three different version IDs remain distinct. Swap latest saved for selection and require literal identity mismatch. |
| `projection_whitelists_scene_fields` | Exact scene keys contain no bodies, source, prose or expected refs. Inject each forbidden needle into a representative serialized view/DOM/debug surface and require scanner detection. Include raw, JSON-escaped and slash-normalized paths. |
| `experiment_never_moves_operation_wall` | Completed diagnostic, qualifying and later experiments leave selection/wall unchanged. Remove each purpose guard separately; each must fail its own assertion. |
| `finalized_is_not_success` | FINALIZED with failing checks displays failure; missing checks display incomplete. Substitute completion for verdict and require failure. |
| `only_linked_operational_event_animates` | Exact selection/run/output/check/ordinal/event linkage permits one labelled recorded transition. Break each relation independently and require no travel. Remove each join guard independently and require its matching control to fail. |
| `partial_failed_operation_keeps_recorded_events` | A failed run with a confirmed negative/partial event preserves it without success styling. Erase that event and require failure. |
| `multi_read_conflict_is_visible` | Board/ledger count, selection/source hash or incident-link disagreement shows conflict and no causal motion. Remove each consistency guard independently. |
| `loading_keeps_continuity_error_breaks_it` | Loading between same-context views permits one confirmed new transition, including a previously pending route that now has linked checks. Actual error or conflict followed by recovery permits none. Mutate loading and error policies separately. |
| `duplicates_and_history_are_quiet` | Duplicate poll, output inspection, first load, historical incident, board/shift change, page-cache return and graphics retry create no fresh operation transition. Remove each reset/dedup condition independently. |
| `publication_sites_cover_live_updates` | Diagnostic/comparison intermediate slot state reaches the test bench before final refresh; accepted selection, output and station changes agree with DOM. Suppress each publication site separately and require the named visible mismatch. |
| `late_import_and_pick_keep_owner` | Delay graphics/import/poll, switch context and deliver old callbacks. Only current board labels and station can appear. Remove token, generation and context guards one at a time. |
| `station_mapping_has_no_commands` | Every object and HTML station opens its existing panel. Record zero command requests from picks. Replace one mapping or call an action and require failure. |
| `graphics_failure_keeps_complete_workbench` | Separately inject import 404, core-module 404, constructor throw, shader callback, render throw, timeout and context loss. Edit the same draft, inspect evidence and use valid offline controls through fallback. Hanging or throwing graphics must not block DOM. |
| `expanded_work_keeps_draft_focus_and_caret` | Expand/restore, resize and page-cache return preserve the same node, dirty bytes, selection and focus. Copy/recreate editor or overwrite dirty bytes and require failure. |
| `responsive_reach_and_keyboard` | At 1280, 640 and 390px verify actual notice span, no page overflow, target >=44 CSS pixels, focus and content reach. Include Northline acceptance, rollout and handover. Remove scroll/focus behavior and require the historical reach case to fail. |
| `reduced_motion_and_visibility_settle` | Live preference change cancels travel, settled labels remain identical and hidden/expanded views stop drawing. Remove each cancellation independently. |
| `disposal_has_one_owner` | Thirty board switches plus partial initialization failure, retry and double disposal meet section 9 resource limits. Omit each owned cleanup independently and require a matching resource/listener assertion. |
| `performance_receipt_meets_named_tier` | Real target receipts meet every budget above. Synthetic slow frame, extra render loop and inflated geometry independently fail the relevant budget. Test injection is not a measured speedup. |
| `local_asset_graph_is_closed` | Parse all literal static/dynamic imports and re-exports and HTML/CSS URLs, recurse from `app.js`, compare to exact manifest inventory and fetch each via HTTP with correct MIME. Reject computed imports and external/bare dependencies. Remove core module, alter MIME, corrupt bytes or add external import independently and require failure. |
| `extracted_build_runs_without_external_assets` | On clean extraction, block external hosts, load actual module graph in a browser, inspect all three rooms and trigger graphics failure fallback. A 200 response containing HTML instead of JS fails. Verify license/provenance records and archive limit. |
| Existing product regressions | Bellwether, GTM and Northline journeys preserve exact comparison, explicit choice, operation and inheritance. Protected scans and relevant full offline suite retain their assertions. No provider calls or new fixture seals are needed for presentation tests. |

For each control, first pass the named clean check, apply one in-memory fault,
require the named assertion failure and restore exactly. A setup error, unrelated
guard or another assertion catching the fault is not proof. If two tests can
catch a shared fault, isolate their conditions. Browser fixtures must be clean
before mutation. Retain failed attempts and baseline limits. Clean-install tests
remain separate because they install dependencies. No test is weakened to fit art.

## 11. Least confident decisions

1. **Two-module r180 delivery.** It keeps the approved architecture simple, but
   full acquired import closure, advisories and extracted execution are unproved.
   A failed closure check blocks use; it does not authorize a bundler migration.
2. **Legibility at 390px.** Compact composition and labelled controls have explicit
   reach requirements. Static studies cannot certify real 3D or physical touch.
3. **Conservative motion.** Some genuine new records will settle quietly because
   their run/check links are not loaded. Truthful missing motion is preferable to
   inferred execution. Richer live traces would require new evidence contracts.
4. **Target hardware availability.** The intended mobile/assistive matrix is
   concrete, but hardware and human sessions have not been arranged. Missing
   coverage must remain visible and can block acceptance for that target.
5. **Original art quality.** Coordinates, materials and room-specific objects make
   the art direction reviewable. Final render review must still judge depth,
   hierarchy and distinction; a functional fallback alone does not meet 3D intent.

## 12. Authority and approval boundary

This proposal extends only the rendering baseline in the root program design,
including its file rows for `index.html`, `app.js`, `styles.css` and `room.svg`.
The separate root program-design notice links here so its older SVG-only file
map cannot be mistaken for the extension's complete implementation contract.
Existing API/domain, learner, protected assessment and synthetic-ledger contracts
are unchanged. Approved Gates 1 and 2 need no backtrack for these bounded details.

Gate 3 approval selects this program design and its visual specification. It does
not approve Gate 4, assign new slice numbers, acquire dependencies, authorize
implementation, arrange sessions, spend credentials, publish Git or deploy.
Gate 4 remains unwritten. S28 and all carried limits remain unchanged.

Jaydon approved this design on 2026-10-19. The separate Git authorization covers
this planning packet only. Stop after publication; do not draft Gate 4 or begin
implementation under that instruction.

[module]: https://raw.githubusercontent.com/mrdoob/three.js/0af9729d0c143a86a1d725d6e2c3ad83301f3f34/build/three.module.js
[core]: https://raw.githubusercontent.com/mrdoob/three.js/0af9729d0c143a86a1d725d6e2c3ad83301f3f34/build/three.core.js
[package]: https://raw.githubusercontent.com/mrdoob/three.js/0af9729d0c143a86a1d725d6e2c3ad83301f3f34/package.json
[license]: https://raw.githubusercontent.com/mrdoob/three.js/0af9729d0c143a86a1d725d6e2c3ad83301f3f34/LICENSE
