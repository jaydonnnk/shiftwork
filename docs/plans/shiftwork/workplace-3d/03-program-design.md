# Program design: Shiftwork 3D workplace

**Revision APPROVED, 2026-10-21, in one batch with Gates 2 and 4.** The user answered "Yes i approve gates 2 to four" on 2026-10-21.
Gate 1 was re-approved on 2026-10-21 with a full-screen workplace, and [Gate 2 section 11](02-architecture.md#11-revision-for-the-full-screen-workplace-2026-10-21) proposes decisions R1 to R6.
[Section 13](#13-full-screen-workplace-revision-2026-10-21) of this document and [section 11 of the visual specification](visual-spec.md#11-full-screen-workplace-revision-2026-10-21) specify them.
Where a section below carries a "Revised by section 13" note, section 13 wins for new work; the older text is history.
Sections 3, 4, 6 and 8 stay in force except where section 13 adds to them.

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

Revised by section 13.2: one new pure module, new test files and changed file roles.

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

Revised by sections 13.4 and 13.5: new view fields and three new motion classes. The truth and continuity rules below stay in force.

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

Revised by section 13.6: station tags over the room, the inspector, the next action and dialogs. The station IDs and guarded navigation below stay in force.

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

Revised by section 13.8: the evidence matrix stays; the budget table and idle-frame rule change.

These are acceptance budgets and the program's narrowed evidence scope, not
claims about untested targets. No device or browser passes until a later receipt
names its exact OS, browser build, GPU, viewport, DPR, tier and power state. Do
not label an emulator a physical device. Targets outside this scope remain
unproved and unclaimed.

| Evidence area | Required checks for this program |
|---|---|
| Desktop Chromium | Chrome 155.0.8059.84 headless on macOS 26.5.1 build 25F80, Apple M4 Pro, 24 GiB RAM, 1280x720. Actual WebGL2 construction and render, complete workbench, fallback, lifecycle and package checks. No Windows, Edge or physical-GPU claim. |
| Narrow browser layout | 640x900 and 390x844 in the same Chromium build at 100% and 200% native profile zoom, with keyboard, touch emulation, 44 CSS-pixel targets, no page overflow and editor continuity. Headless viewport emulation is layout and interaction evidence, not physical mobile proof. |
| Native Safari | Safari 26.5 build 21624.2.5.11.4 on macOS 26.5.1, Apple M4 Pro. Actual WebGL2 rendering and station navigation observed in an owned native window, plus native 200% picker layout controls at 378x413 CSS pixels. The functional viewport was not recorded and the layout controls were hidden-page observations. No previous-stable Safari claim. |
| Unsupported graphics | WebGL2 denied, software/disabled GPU, module 404, shader failure and context loss, with complete DOM workbench acceptance in Chromium. Native Safari failure isolation was not exercised. |
| Assistive access | Keyboard in Chromium and the recorded native Safari observations. Audible VoiceOver with Safari and NVDA with Edge are unverified and not claimed by this program version. Browser AX data alone cannot claim audible screen-reader proof. |

Deferred and unclaimed targets: Windows 11 Chrome/Edge stable and previous
stable, Firefox, previous-stable Safari, physical iPhone 12-class and Pixel
6-class devices, minimum Intel UHD 620-class hardware, physical-device
performance and power records, audible VoiceOver and NVDA, and comprehension
sessions. They remain unproved, are not passes and must not appear as
supported-device claims. A later program decision may add targets and fresh
evidence without rewriting earlier receipts.

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
never certifies physical GPU performance. Targets outside the narrowed scope
remain unproved and unclaimed; they are not passes and do not block acceptance.
If a tested compact tier fails, keep work usable through fallback, record the
miss and stop board expansion pending a design decision.

## 10. Test plan and fail-capable controls

Extended by section 13.9: new checks and planned, reviewed changes to existing browser checks. Every check below stays.

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
| `responsive_reach_and_keyboard` | At 1280x720, 640x900 and 390x844 in Chromium, and at the recorded native Safari state, verify actual notice span, no page overflow, target >=44 CSS pixels, focus and content reach. Include Northline acceptance, rollout and handover. Remove scroll/focus behavior and require the historical reach case to fail. |
| `reduced_motion_and_visibility_settle` | Live preference change cancels travel, settled labels remain identical and hidden/expanded views stop drawing. Remove each cancellation independently. |
| `disposal_has_one_owner` | Thirty board switches plus partial initialization failure, retry and double disposal meet section 9 resource limits. Omit each owned cleanup independently and require a matching resource/listener assertion. |
| `performance_receipt_meets_named_tier` | The tested Chromium tiers meet every applicable budget above; native Safari performance and other untested targets remain unproved and unclaimed. Synthetic slow frame, extra render loop and inflated geometry independently fail the relevant budget. Test injection is not a measured speedup. |
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

Extended by section 13.10.

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

## 13. Full-screen workplace revision, 2026-10-21

Status: APPROVED 2026-10-21 in the user's batch approval of Gates 2 to 4.
Scoped backtrack, 2026-10-21: S37's browser smoke showed rule 2 of section 13.5 sending a first-time Bellwether visitor to step 7, because the starter version's own operation run is already `FINALIZED` on a fresh shift. The user chose to limit rule 2 to a `LEARNER_CHOICE` selection and RE-APPROVED the revised rule 2 in chat the same day.
This section turns [Gate 2 section 11](02-architecture.md#11-revision-for-the-full-screen-workplace-2026-10-21) decisions R1 to R6 into files, types, signatures, call stacks, timings, budgets and fail-capable checks.
It was written from source inspection of `main` at `94e651b` and the re-approved Gate 1 mockups in [mockups/v2](mockups/v2/index.html).
Nothing here was run, rendered or measured.
Line references are anchors only; copy the current complete statement before any edit.

### 13.1 What stays fixed

- The five accepted modules keep their roles: `app.js` owns state, requests, commands, drafts and navigation; `workplace-view.js` is the pure projection; `workplace-host.js` owns lifecycle; `workplace-scene.js` owns rendering; `workplace-rooms.js` is plain room data.
- The engine closure stays `three.module.js`, `three.core.js` and `LICENSE` under `vendor/three-r180/`, with the existing manifest. No import map, bare specifier, addon or new vendor file (decision R5).
- `SceneView` keeps every field in section 4. Section 5's truth, consistency and continuity rules, section 6's publication sites and section 8's lifecycle and failure contract stay in force.
- The existing 160ms comparison emphasis, 180ms selection acknowledgement and 320ms evidence trace keep their durations and trigger rules. Their test anchors therefore stay valid.
- Every existing control ID, section and handler in `index.html` and `app.js` is preserved. Nodes move; they are not copied or recreated.

### 13.2 Files

| File | Change |
|---|---|
| `shiftwork/client/index.html` | Keep `#runtime-notice` as the first full-width row. Wrap the room in `<div class="world" id="workplace-world">` that fills the remaining viewport height (minimum 560px at 761px and wider). Inside it: the existing `.workplace` canvas container `#workplace-canvas` and static fallback; a `#station-tags` layer holding the existing `[data-station]` buttons for each board; a `#story-layer` with at most one customer bubble and one owner bubble; floating `#status-bar`, `#step-chip`, `#next-action` (one button `#next-action-go`) and `#shift-log` (a native disclosure holding `<ol id="shift-log-list">`). The existing `#station-panel` becomes the inspector (`<aside>`), gaining `#close-inspector`. Add `<dialog id="choose-dialog">`, `<dialog id="shift-report">` and `<section id="shift-picker">`. Move the existing `#selection-rationale`, `#select-candidate-a` and `#select-candidate-b` nodes into `#choose-dialog`; the compare section gains `#open-choose-a` and `#open-choose-b`. |
| `shiftwork/client/styles.css` | Remove the layout A grid rules (the `main` 58fr/42fr template and its 1099px stack). Add the full-screen stage, floating panels, inspector, dialogs, picker, narrow stacking at 760px and below, expanded inspector, lamp text and reduced-motion rules from visual-spec section 11. |
| `shiftwork/client/app.js` | Publish as today, then call `renderStory()` with the accepted view. Own inspector open and close, the picker, both dialogs, the shift log, report triggering and the next-action click. All new handlers navigate or open HTML only, except the existing `chooseCandidate()` reached from the dialog. |
| `shiftwork/client/workplace-story.js` | New pure module. Exports `guideStep`, `lampStates`, `ownerLine`, `customerBubble`, `planSlips`, `reduceShiftReport` and `logEntries`. Imports only `selectEvidence` from `evidence.js`. No DOM, engine, network or command imports. |
| `shiftwork/client/workplace-view.js` | `projectWorkplace` adds `attention`, `lamps` and `slips` to `SceneView` by calling `guideStep`, `lampStates` and `planSlips`. Imports `workplace-story.js`; the story module never imports the view module. |
| `shiftwork/client/workplace-host.js` | Forward inspector state, input activity and anchor positions; start an explicit or eligible replay. No API access. |
| `shiftwork/client/workplace-scene.js` | Perspective camera, view offset and focus ease, ACES tone mapping, fog, first-party rounded geometry and environment, emissive lamps, attention ring, slips and stamps, ambient scheduling and anchor projection. Still the only RAF owner. |
| `shiftwork/client/workplace-rooms.js` | Bellwether light palette, lamp and ring anchors per station, slip path points (queue, service, inspector desk, wall) and camera pose. Plain data. |
| `shiftwork/client/workplace-assets.json` | New provenance rows for the rounded geometry builder, the environment scene and the slip and stamp assemblies, all `shiftwork-original`. |
| `tests/client/workplace_story.test.mjs` | New GPU-free checks for the story module (section 13.9). |
| `tests/client/workplace_fullscreen.mjs` | New browser checks for layout, inspector, next action, dialogs, picker, main-view text and narrow stacking. |
| `tests/client/workplace_replay.mjs` | New browser checks for slips, stamps, ambient stop rules and camera rules. |
| Existing `tests/client/*.mjs` | Planned, reviewed edits listed in section 13.9. No assertion is deleted, skipped or weakened. |
| `tests/packaging/test_client_asset_closure.py` | Add `workplace-story.js` to the expected inventory. The engine inventory assertion stays at two modules. |
| `README.md`, notices | Describe the full-screen layout and fallback after implementation. `THIRD_PARTY_NOTICES.md` is unchanged because no third-party file is added. |

Import graph: `app.js` statically imports `workplace-view.js` and `workplace-story.js`.
`workplace-view.js` imports `evidence.js` and `workplace-story.js`.
`workplace-story.js` imports `evidence.js` only.
The host and scene import graph is unchanged.

### 13.3 Engine and first-party recipe

All of these exist in the vendored `three.module.js` or `three.core.js` (verified by text search at this gate, not by execution): `PerspectiveCamera`, `ACESFilmicToneMapping`, `Fog`, `PMREMGenerator`, `ExtrudeGeometry`, `Shape`, `InstancedMesh`.

- `roundedBox(width, height, depth, radius, tier)` in `workplace-scene.js` returns a core `ExtrudeGeometry` built from a rounded-rectangle `Shape` with one bevel segment, cached per size key and registered once for disposal. On the compact tier it returns the shared `BoxGeometry`.
- `buildStudioEnvironment(renderer)` builds an original procedural scene (a light box with three emissive panels), converts it once with core `PMREMGenerator.fromScene` at the smallest size that passes the art review (start at 128), disposes the generator and the source scene, and returns the render target for `scene.environment`. Standard tier only.
- Lamps and the ring use `MeshBasicMaterial` with `toneMapped: false`, shared per colour.

### 13.4 Types and signatures

Additions only; everything in section 4 stays.

```text
GuideStep = { step: 1 | 2 | 3 | 4 | 5 | 6 | 7, name: StepName,
	stationId: StationId, status: "ready" | "running" | "blocked",
	blockedReason: string | null }
StepName = "Read the complaints" | "Explain the cause" |
	"Say what would prove you wrong" | "Try two fixes" | "Choose one" |
	"Run the shift" | "See what happened"
LocalGuidance = { activeStation: StationId | null, causeDraft: boolean,
	falsifierDraft: boolean }
// UI-only booleans. They steer the chip between steps 1 and 3 and are never
// sent, stored or credited.

Lamp = { stationId, tone: "fail" | "attention" | "pass" | "idle" | "unknown",
	text: string }
Slip = { ordinal: number, outputId: string,
	verdict: "pass" | "fail" | "error" | "none", checkCount: number }
SlipPlan = { runId, purpose, state, slips: Slip[], overflow: number }
// At most 12 slips animate; overflow counts the rest, which settle together.

SceneView additions = {
	attention: StationId | null,
	lamps: Lamp[],
	slips: SlipPlan | null
}

guideStep(view: SceneView, local: LocalGuidance): GuideStep
lampStates(view: SceneView): Lamp[]
planSlips(run, outputs, checks): SlipPlan | null
ownerLine(view: SceneView, guide: GuideStep): string | null
customerBubble(view: SceneView, output): { label, text } | null
reduceShiftReport(view: SceneView, run, checks, events, selection): ShiftReport
logEntries(view: SceneView, run, checks, events, investigations,
	selection): LogEntry[]
ShiftReport = { runId, versionLabel, backupLabel, requests: { pass, fail,
	error, none }, incidentsOpened, incidentsResolved, openBefore, openAfter,
	complete: boolean }
// Every count is a reduction of loaded public records. A missing link makes
// the count null and the report says "unknown", never zero.
LogEntry = { kind: "run" | "check" | "event" | "selection" | "note",
	ids: string[], text: string, tone: "fail" | "pass" | "info" | "you",
	recordedAt: string | null }

SceneHandle.setInspector({ open: boolean, widthPx: number }): void
SceneHandle.setAmbient(active: boolean): void
SceneHandle.playReplay(plan: SlipPlan, label: "recorded" | "history"): boolean
SceneHandle.settleReplay(): void
SceneHandle.anchorPositions(): Record<StationId, { x, y, visible }>
WorkplaceHost.setInspector({ open, widthPx }): void
WorkplaceHost.noteInput(): void
WorkplaceHost.replay(kind: "explicit"): void
createWorkplaceHost({ ..., onAnchors }) // onAnchors(positions) after a
	// drawn frame that changed camera or size; never per idle frame.
```

`slips` carries ordinals, output IDs and verdicts only.
`request_text`, rationale, owner lines, cause and falsifier prose never enter `SceneView`.
They are rendered by `app.js` into HTML from the controller's accepted state.

### 13.5 Field ownership and motion eligibility

**Step guide (`guideStep`).**
Rules are evaluated in this order, Bellwether first; S42 adds board station maps.

1. Shift state `closed`: step 7, station `next`.
2. Operating selection of kind `LEARNER_CHOICE` and a loaded run with purpose `OPERATION`, the current shift ID and that selection's ID: `QUEUED`, `RUNNING` or `CAPTURED` gives step 6 `running` at `service`; `FINALIZED` or `FAILED` gives step 7 at `ledger`. A run of a `STARTER_BASELINE` selection never matches this rule; it is the recorded run that step 1 reads.
3. Operating selection of kind `LEARNER_CHOICE` whose `comparisonId` equals the current qualifying comparison ID: step 6 at `service`.

3a. Operating selection of kind `LEARNER_CHOICE`, shift state `open`, and no loaded run with purpose `OPERATION`, the current shift ID and that selection's ID: step 6 at `service`. Re-approved 2026-10-22 after the S37 review: an inherited choice in a later shift had fallen through to step 1.

4. Current qualifying comparison `COMPLETE` with at least one candidate `eligible === true`: step 5 at `compare`. With none eligible: step 4 `blocked`, with the first recorded blocking reason code shown in words.
5. `investigation.count >= 1` for the current shift: step 4 at `compare`.
6. Otherwise: step 3 at `investigate` when the investigate station is active and `causeDraft` is true; step 2 at `investigate` when it is active; step 1 at `customers`.

The guide never reads `latest_run` as an operation, never treats a saved or frozen version as chosen, and never enables, disables or explains a command.
Command availability stays with the existing handlers and their help text.
An unknown or conflicting view gives step `null` behaviour: the chip says "Step unknown: recorded state unavailable" and the next action opens the current station.

**Lamps (`lampStates`).** Text is always present; tone is never the only signal.

| Station | Tone and text |
|---|---|
| `customers` | `attention` with "N complaints" when the loaded run has a `fail`, `error` or `none` slip; `idle` with "No recorded requests" when no output is loaded; `pass` only when the loaded run is the current selection's operation and every slip is `pass`. |
| `service` | `idle` "No live version"; `attention` "Live, not yet run"; `pass` "Live, checks passed" only under the `customers` pass rule; `fail` "Live, checks failed"; `fail` "Invalidated" for an invalidated selection. |
| `evaluator` | `idle` "Locked" always; the run's reported state in words while it is not terminal. |
| `ledger` | `fail` "N open" when unresolved incidents exist; `idle` "None open"; `unknown` "Unavailable" when chain status is not VALID. |
| `compare` | `attention` for `RESERVED` or `RUNNING`; `idle` otherwise; text "No score, no default" when complete. Never `pass`. |
| `investigate`, `owner`, `next`, `repair`, `pipeline` | `idle` with existing status words; `attention` only when the guide points there. |

When the operating selection is of kind `STARTER_BASELINE` and unresolved incidents exist: the customers lamp is `attention` with "N open complaints", N being the unresolved incident count; the service lamp is `attention` "Live, complaints open" and never `pass`; and the step 1 owner line, when the loaded run has no complaint, is the new catalogue entry "{n} customer complaints are still open." with the same N.
Re-approved 2026-10-22 after the S37 review: on a fresh demo the starter's passing second run had hidden three open complaints from the first.

**Customer bubble.** Shows `request_text` of the selected output of the loaded run, truncated to 140 characters with an ellipsis, labelled "Recorded request" plus the purpose in words ("operation", "test", "history").
No output loaded means no customer bubble.

**Owner line.** One entry from a frozen catalogue keyed by step, with only public counts substituted.
Draft catalogue for review: step 1 "{n} customers in the last recorded run did not get what they asked for."; step 2 and 3 "Write down your own explanation first; I will not guess for you."; step 4 "Both versions get the same requests, so the comparison is fair."; step 5 "Nothing goes live until you choose and say why."; step 6 "The version you chose is the one that runs."; step 7 "{p} of {m} recorded requests passed the inspector's checks."; closed shift "Your choice carries into the next shift."
The catalogue may not name a cause, a fix, a candidate, a version preference or a choice; section 13.9 checks this.

**Slips (`planSlips`).** One slip per loaded output in ordinal order.
The verdict joins checks through `selectEvidence`: any linked `fail` gives `fail`; otherwise any `error` gives `error`; otherwise at least one linked check, all `pass`, gives `pass`; no linked check gives `none`.
`planSlips` returns null unless the run is terminal (`FINALIZED` or `FAILED`) and the checks read has been accepted for that run.

**Motion eligibility.**

- *Automatic replay* uses the existing `linked-consequence` continuity facts 1, 2 and 4 from section 5, applied to the run instead of a single event: same context, accepted after loading, purpose `OPERATION`, current shift and exact selection, terminal state, and the run ID absent from the previous accepted view's `slips`. It plays at most once per run ID per page session. Experiments, legacy evidence, first load, history, retry and page-cache return never auto-play.
- *Explicit replay* is the "Replay recorded run" button in the inspector for the service station. It plays any loaded terminal operation run, labelled "Recorded replay of history", and changes no lamp, wall count or report.
- The existing 320ms wall trace remains the final leg when a linked consequence arrives; a slip that reaches the wall without a linked event settles without a trace.
- *Ambient* runs only when all hold: standard tier, visible, on screen, not expanded, not reduced motion, a replay is not running, and learner input was seen in the last 20 seconds. It animates only the ring under `attention` and lamps whose tone is `attention` or `fail`.
- *Camera focus* runs only at 761px and wider, only on a station activation or inspector open or close, never on load, refresh or history.

### 13.6 Layout, stations and interaction

- **Stage.** `#workplace-world` fills the viewport below the hosting row. At 761px and wider the canvas fills the stage and every floating panel is inset 16px. The page never scrolls horizontally.
- **Station tags.** The existing `[data-station]` buttons are positioned at `anchorPositions()`, are real buttons in a logical tab order (queue, service, inspector, wall, test bench, owner, then the rest), carry the lamp text, and are at least 44 by 44 CSS pixels including padding. When graphics are unavailable they sit at fixed fallback positions over `room.svg`. The canvas stays `aria-hidden` and outside the tab order.
- **Tags never cover tags.** From 761px to 1280px wide, with the inspector open or closed, no station tag's rectangle intersects another station tag's rectangle.
When no nearby spot is clear of everything, a tag takes the spot that avoids other tags first and covers the least of the panels second.

Backtracked 2026-10-22 during S38: the perspective camera moved the anchors, and at 1024x720 the Bellwether evaluator and pipeline tags overlapped with the inspector open and closed (at S37 only closed); at 900x640 and 800x600 overlaps grew in both versions.
1280x720, 1366x768, 1440x900 and 1920x1080 were clean in both.
At 1280x720 every tag now finds a free spot, so the existing least-overlap fault could no longer fail any check.
The user chose to fix the placement in S38 and to add the 1024x720 cells in section 13.9.
- **Inspector.** Opening a station opens `#station-panel` as a left-side panel, width `clamp(360px, 32vw, 480px)`, from below the step chip to the stage bottom. The scene receives `setInspector({open, widthPx})` and shifts its view offset so the room centre sits in the uncovered area. `#close-inspector` and Escape (outside text fields and editors) close it and return focus to the station's tag. While open, the inspector footer replaces the next-action panel.
- **Expanded work.** `#expand-work` keeps its role: the inspector spans the stage with a 1120px reading column and the room suspends. `main[data-expanded]` and `aria-expanded` keep their values and meaning.
- **Next action.** `#next-action-go` is labelled with the guide's step name and calls `activateStation(guide.stationId)`. It sends no request.
- **Choose dialog.** `#open-choose-a` and `#open-choose-b` use the existing select-button eligibility conditions except the required rationale. The rationale is inside the dialog, so requiring it to open would prevent the first choice. Confirmation keeps every existing condition, including a nonempty rationale. This scoped correction was RE-APPROVED by the user on 2026-10-22 during S39. They call `showModal()` on `#choose-dialog`, which states the exact version, "Why we ask: only the version you choose goes live", and "The other version stays as your backup". Focus moves to `#selection-rationale`. No option is preselected. Cancel and Escape close without a request. The existing `chooseCandidate()` handler and server guard are unchanged.
- **Shift report.** `#shift-report` opens once after an automatic replay ends or is skipped, and from a "Shift report" button at any time, labelled "Recorded history" when not fresh. It shows `reduceShiftReport` values and the permanent "Synthetic scenario: not real customers or revenue" line. Closing it changes nothing. S39 sequencing interpretation, APPROVED by the user on 2026-10-22: until S41 adds replay, open once when a continuous new operation reaches a terminal state with accepted checks; S41 moves the trigger to replay completion. First load, history, retry, page-cache return and experiments never open it automatically.
- **Shift picker.** `#shift-picker` shows when the URL has no board parameter and from a "Change shift" button in the status bar. Each card's "Start shift" goes through the existing `switchWorkplace()` guard, so a dirty draft still blocks a switch. Cards show authored text only, with no live counts.
- **Shift log.** `logEntries` from loaded public records, newest last, with full IDs, check reason codes and ledger sequence numbers. Filters: All, Checks, You. Collapsed by default below 761px.
- **Main view text.** The status bar, chip, next action, tags and bubbles may show version labels such as `ver-0002` because they name what the learner chooses. They may not show content or requirement hashes, run, selection, check, investigation or output IDs, ledger sequence numbers, or API enum spellings. Those stay in the log and inspector.
- **Narrow, 760px and below.** Order: hosting row, status bar, step chip, compact room (240px tall at 640px, 200px at 390px) with its tags as a two-column list below it, next action, inspector content, shift log. No camera motion, no drag, no pointer capture. Station activation scrolls and focuses the inspector through the existing helper.

Call stacks added:

```text
Accepted publication -> projectWorkplace (+ guideStep, lampStates, planSlips)
  -> host.publish -> scene.apply (lamps, ring, slip settle)
  -> app.renderStory(view, guide) -> chip, next action, bubbles, tags, log

Next-action click -> activateStation(guide.stationId) -> existing panel, focus,
  URL -> publication. No request.

Scene frame that moved camera or resized -> scene.anchorPositions
  -> host onAnchors -> app positions tags and bubbles

Eligible accepted terminal operation run -> host checks continuity and the
  per-run played set -> scene.playReplay(plan, "recorded") -> slips travel and
  stamp actual verdicts -> settle -> app opens #shift-report

Open choose button -> dialog.showModal -> learner writes reason -> existing
  select button -> chooseCandidate -> existing API guard -> accepted refresh
```

### 13.7 Lifecycle additions

- The scene's single RAF also serves ambient and replay frames. `setAmbient(false)`, `setSuspended(true)`, reduced motion and `dispose()` cancel ambient and settle any replay at its final stamps.
- The host calls `noteInput()` from pointer, key and touch listeners it owns on `#workplace-world`; ambient stops 20 seconds after the last input and resumes on the next one.
- The environment render target, rounded geometry cache, lamp, ring, slip and stamp resources are registered once and disposed once. Partial initialization failure releases them.
- A board switch, history navigation, reset or conflict settles any replay immediately and clears the per-run played set for that context.

### 13.8 Budgets

Section 9's evidence matrix, deferred targets and measurement recipe stay.
This table replaces section 9's budget table.
S38 measured the recipe against these values on one Mac's headless Chrome (Chrome/155, ANGLE Metal, M4 Pro) on 2026-10-22: no budget missed at 1280x720 DPR 1, 1280x720 DPR 2 and 390px DPR 3, with tight margins recorded in the S38 checkpoint. Real-device fit is [unknown].

Backtracked 2026-10-22 during S38, after the first measurement and before any art work: on this Mac's headless Chrome the recipe at 1280x720 and DPR 2 drew a 2560x1140 backing store, estimated at 144.1MiB against the 96MiB standard budget (48 bytes per backing pixel for multisampled colour and depth plus resolve, one shadow map, the PMREM target).
The original 4,200,000-pixel cap would allow about 200MiB, so the cap and the budget could not both hold, and dropping the environment map (1.5MiB) could not close the gap.
The user chose to lower the backing-store cap to 1,850,000 pixels and keep antialiasing; the other budgets are unchanged.
The bytes-per-pixel figure is an estimate, not a GPU reading.

| Budget | Standard | Compact |
|---|---|---|
| Maximum DPR | 2.0, lowered so the canvas backing store stays at or below 1,850,000 pixels | 1.0 |
| Triangles per settled frame | 120,000 | 40,000 |
| Draw calls, including shadows | 120 | 60 |
| Lighting | Hemisphere, one directional key, first-party PMREM environment | Hemisphere and key, no environment map |
| Shadow maps | One 1024x1024 map, fixed room bounds | None; contact geometry |
| Tone mapping and fog | ACES filmic, linear fog | Same |
| Authored textures and post-processing | None | None |
| Active-motion frame intervals, median / p95 | <=16.7ms / <=33.4ms | <=33.4ms / <=50ms, cap drawing at 30Hz |
| Ambient drawing | <=30 frames per second while eligible; zero otherwise | Zero |
| Estimated owned GPU allocation | <=96MiB | <=24MiB |

Common budgets change as follows; the rest of section 9's list stays:

- Additional engine bytes: zero for this revision. First-party scene, view, host, rooms and story JavaScript together <=180KiB uncompressed (60,695 bytes for the four scene modules at `94e651b`).
- Idle frames: replace "zero scheduled idle graphics frames across 10 seconds after settling" with zero frames across 10 seconds when ambient is ineligible, and at most 30 frames per second when it is eligible.
- Station activation to painted inspector content p95 <=100ms. The inspector's 200ms slide is CSS and never delays content paint or focus.
- Camera focus ease <=480ms. Replay: each leg 400ms, stamp 240ms, slips staggered 250ms, whole replay <=6 seconds, skip at any time with "Show settled result".
- Cold graphics-ready <=3 seconds desktop and <=4 seconds mobile, now including environment generation.

### 13.9 Test plan additions and planned changes

Each new check follows section 10's rule: pass clean, apply one in-memory fault, require the named assertion to fail, restore exactly, pass again.

| Planned check | Observable assertion and the deliberate fault that must fail it |
|---|---|
| `guide_step_follows_recorded_state` | Ten literal public views give the exact step and station for every rule in 13.5. Separately: read `latest_run` instead of the operation run; treat the newest saved version as chosen; give step 5 when no candidate is eligible; drop the shift-ID match. Each fails its own case. |
| `guide_never_credits_unsent_text` | Draft booleans change only the chip between steps 1 and 3; `investigation.count` and every control's `disabled` state are identical with and without drafts. Fault: let a cause draft advance to step 4. |
| `next_action_navigates_only` | In each of the seven states, clicking `#next-action-go` opens the guide's station and records zero non-GET requests. Fault: wire the button to `#run-shift`. |
| `owner_lines_never_suggest` | Every catalogue line, rendered with sample counts, contains no denylisted cause, fix or preference word and no candidate or version label. Scanner self-test: inject each needle into a rendered line and require detection. A reviewer also reads the catalogue; the word list alone is not proof. |
| `main_view_has_no_internal_identifiers` | Serialized text of status bar, chip, next action, tags and bubbles matches none of the forbidden patterns in 13.6, enumerated from `schemas.py` Literal values and ID formats before writing the scanner. Self-test: inject each pattern into that serialized surface and require detection. |
| `main_view_shows_one_of_each` | In each of the seven states: at most one customer bubble, at most one owner bubble, exactly one visible next action or inspector footer. Fault: render two owner lines. |
| `slip_verdicts_match_checks` | Literal outputs and checks give the exact verdict per slip. Separately: missing checks become `pass`; `error` becomes `pass`; a `fail` is ignored when another check passes. Each fails. |
| `replay_waits_for_recorded_results` | With checks delayed, a `FINALIZED` run starts no slip; `RUNNING` starts none. Fault: drop the terminal or checks-accepted guard, each separately. |
| `replay_auto_only_on_continuous_operation` | First load, history, retry, page-cache return, a diagnostic and a comparison never auto-play; a continuous new operation plays once; a repeated poll does not replay. Remove each guard separately. |
| `explicit_replay_is_labelled_history` | The button plays with the "Recorded replay of history" label and leaves lamps, wall counts and report unchanged. Faults: remove the label; let explicit replay open the report as fresh. |
| `ambient_stops_where_required` | Five-second frame counts are zero for compact, hidden, offscreen, expanded, reduced motion, running replay and 20 seconds without input; eligible ambient stays <=30 frames per second. Remove each stop condition separately. |
| `lamps_reflect_state_with_text` | Every row of the lamp table, with text present. Faults: `compare` shows `pass`; `service` shows `pass` for an experiment run; text omitted. |
| `inspector_keeps_stations_readable` | At 1280x720 and 1024x720 with the inspector open, every station tag's rectangle is inside the viewport and outside the inspector, and at 1280x720 and 1024x720 with the inspector open and closed no station tag covers another (13.6, backtracked 2026-10-22). Faults: skip the view offset; let an unplaceable tag take its first candidate instead of the least covering spot; stop counting already placed tags as taken. Each fails its own assertion at a named cell. |
| `choose_dialog_has_no_default` | Dialog opens with focus on the rationale, no option preselected; Cancel and Escape send zero requests; the existing guard still blocks an empty rationale. Faults: autofocus the confirm button; close-as-choose. |
| `shift_report_matches_ledger` | Literal ledger and checks give the exact report counts; a missing link shows "unknown"; the synthetic line is present. Faults: count all events instead of linked ones; turn null into zero. |
| `picker_uses_switch_guard` | A dirty draft blocks a picker switch exactly as the existing switch control does. Fault: call the slug change directly. |
| `narrow_stack_reach_and_still_camera` | At 640x900 and 390x844, at 100% and 200% zoom: the stated order, no page overflow, 44px targets, next action reachable by tap and keyboard, Northline Acceptance, Rollout and Handover in reach, and the camera matrix unchanged across station picks. Fault: allow camera ease at compact width. |
| `renderer_matches_tier_recipe` | Standard and compact report the camera type, tone mapping, environment presence, DPR cap and backing-store cap of 13.8. Faults: environment on compact; DPR above the cap. |
| `local_asset_graph_is_closed` (extended) | Inventory includes `workplace-story.js`; the engine inventory remains exactly two modules. Fault: add an import from an examples path. |
| `performance_receipt_meets_named_tier` (extended) | Adds ambient and replay samples to the recipe at both tiers. |

Planned, reviewed changes to existing checks. Each change is recorded with the old assertion text in that slice's checkpoint:

- `workplace_s31.mjs` `assertLayout`: the 1280px `sideBySide: workplace.right <= panel.left + 2` encodes layout A. Replace it with the `inspector_keeps_stations_readable` assertion. The 640px and 390px `stacked` assertion and the two-card and overflow assertions stay.
- `workplace_s30.mjs` expanded editing: IDs and `main.dataset.expanded` are kept, so the same-node, value, focus, caret and `aria-expanded` assertions stay unchanged. Only the expected panel width context changes, and that value is not asserted today. S40 scoped test correction RE-APPROVED by the user,2026-10-23: the served expanded-work replay-safety control makes ambient ineligible, with an asserted setup precondition. Every original assertion stays, including `restored.frames <= 2` and no restored pulse; every retained expanded-work fault must still fail its named assertion and pass restored. S40 proves actual eligible ambient resumption separately at at most 30fps. Product behavior is unchanged.
- `workplace_s33.mjs` owner folder inside `#station-panel`: unchanged, because the inspector is the same node.
- `workplace_s31.mjs`, `workplace_s32.mjs` and `workplace_browser.mjs` duration assertions (160, 180, 320) and their source anchors: unchanged, because those durations are kept.
- `workplace_browser.mjs` has 79 served-source `replace` calls. Any anchor whose production statement changes (for example the scene's `return { apply, resize,` handle and `renderer.render(scene, camera);`) is updated to the new exact statement and its fault re-proven. Every `replace` gains an exactly-once assertion where it lacks one, so a changed anchor fails loudly instead of silently skipping its fault.
- `workplace_s34.mjs` marker projection and canvas clip: the projection uses the scene camera, so it stays valid with a perspective camera; the clip size changes with the full-screen canvas and its baseline image is re-recorded with the old one retained.
- `workplace_s35.mjs` narrow Northline reach: rerun under the new stack order; any new failure is recorded, never overwritten by a later pass.
- `browser.mjs`, `gtm_browser.mjs`, `northline_browser.mjs` selection steps: open `#open-choose-a` or `#open-choose-b` before writing the rationale and pressing the existing select button. The selection, operation and inheritance assertions stay.

How many existing checks break under the new layout is [unknown] until S36 runs them; the list above is from source reading.

### 13.10 Least confident decisions

1. **One shell for all three boards in S36.** User decision, 2026-10-21: all three boards. A shared layout cannot serve two shells without a permanent alternate shell, which Gate 2 forbids. So Stonebridge and Northline get the full-screen layout in S36 while the story layer stays Bellwether-only until S42. If S42 misses the deadline, those boards ship full-screen without step guidance. The alternative, keeping layout A for them, needs a temporary second layout and doubles the narrow-screen proof.
2. **First-party rounded geometry and environment.** Avoids an import map and an acquisition, but the art may look less polished than the upstream addons. The S38 art review decides; the fallback is a recorded Gate 2 and 3 change.
3. **The step guide is a planner.** Section 7 forbade a global workflow planner. The guide is allowed only because it navigates and never decides command eligibility. If a guide rule ever needs to know whether a command is allowed, stop and revisit.
4. **Owner lines.** User decision, 2026-10-21: the seven drafted lines are OK as drafted; the S37 human read still applies. A word list cannot prove a line does not hint. The catalogue is short and reviewed by a person; any new line needs the same review.
5. **Budgets.** User decision, 2026-10-21: approve as provisional; S38 measures the recipe before any art work. DPR 2 with an environment map on a full-viewport canvas may exceed 96MiB or the frame budget on the compact tier or lower hardware. The adaptive backing-store cap is the first lever; the second is dropping the environment map. Neither is measured.
6. **Picker question copy.** User decision, 2026-10-21: reword. The Stonebridge card now reads "Promising leads sit unassigned past their response deadline. What is going wrong?", replacing "Is it the rules or the routing?", which named two places to look. Screen 10 of the v2 mockups is updated to match; no other Gate 1 text changes.

[module]: https://raw.githubusercontent.com/mrdoob/three.js/0af9729d0c143a86a1d725d6e2c3ad83301f3f34/build/three.module.js
[core]: https://raw.githubusercontent.com/mrdoob/three.js/0af9729d0c143a86a1d725d6e2c3ad83301f3f34/build/three.core.js
[package]: https://raw.githubusercontent.com/mrdoob/three.js/0af9729d0c143a86a1d725d6e2c3ad83301f3f34/package.json
[license]: https://raw.githubusercontent.com/mrdoob/three.js/0af9729d0c143a86a1d725d6e2c3ad83301f3f34/LICENSE

## 14. Robot crew and declutter revision, 2026-10-23

Status: APPROVED 2026-10-23 in the user's batch re-approval of Gates 1 to 4: "I re-approve Gates 1 to 4 for the robot crew and declutter. Commit the docs, then start S41 on shiftwork/slice-41."
This section turns [Gate 2 section 12](02-architecture.md#12-revision-for-the-robot-crew-and-declutter-2026-10-23) into files, signatures, rules and fail-capable checks.
It was written from source inspection of `main` at `70cb2f7` and the [crew mockup](mockups/v2/17-robot-crew.html), which runs the real Bellwether geometry with a prototype crew.
The mockup was rendered in a local browser at 1280x800; nothing in the product was changed, measured or tested.

### 14.1 Files

| File | Change |
|---|---|
| `workplace-crew.js` (new) | `createCrew({ THREE, room, tier, reducedMotion, register })` builds the bots and returns `{ group, walkTo(stationId \| null), tick(dt, t, ambient), settle(), speakerAnchor(role), youAnchor(), dispose() }`. Pure route planner `routeBetween(graph, from, to)` is exported for tests. |
| `workplace-rooms.js` | Each room gains `crew: { home, nodes, edges, stands, staff }`: the learner bot's home node, floor nodes, hand-checked clear edges, one stand node per station and fixed staff spots with roles (`owner`, `customer`). |
| `workplace-scene.js` | Adds the crew group, calls `tick` from the single RAF, exposes `setOpenStation(stationId \| null)` and `crewAnchors()`, adds the crew to suspend, reduced-motion and dispose paths, and adds `onHover(stationId \| null)` from the existing pointer raycast. |
| `workplace-host.js` | Forwards `setOpenStation` and `onHover`; adds `crew` positions to the `onAnchors` payload. |
| `workplace-story.js` | New pure `restingTags(view, guide, lamps)` and `narrator(view, guide, output)`. |
| `app.js`, `index.html`, `styles.css` | Tags carry `data-resting`; the single bubble is placed at the speaker bot; a "You" chip follows the learner bot; the 3D hint card is removed at 761px and wider. |
| `workplace-assets.json` | Closure inventory gains `workplace-crew.js`. |

### 14.2 Rules

1. **Resting tags (R9).** At 761px and wider, `restingTags` returns the guide's `stationId` plus at most one other station: the first lamp with tone `fail` in tag order. Every other tag has `data-resting="false"` and is visually hidden until pointer hover (via `onHover` or the tag itself), keyboard focus, or its station being the open one. Hidden tags stay in the tab order with the same accessible name. At 760px and below, the two-column tag list is unchanged and shows every station. The fallback over `room.svg` shows every tag.
2. **One narrator bubble.** `narrator` returns one `{ role, text, stationId }`: the customer's recorded request (the existing `customerBubble`) at step 1, otherwise the existing `ownerLine`. A null line shows no bubble. The bubble carries the speaker station's name and lamp text, and that station's separate tag is suppressed while the bubble shows. The owner line catalogue is unchanged, so `owner_lines_never_suggest` still covers every line.
3. **Learner bot.** `walkTo(stationId)` is called only from `setOpenStation`, which the app calls only from `activateStation` and inspector close. The route is the shortest path on the room graph from the bot's current node. Speed 2.6 room units per second, so a walk takes at most about 3 seconds. On arrival the bot faces the station and plays a small typing gesture while the inspector stays open. On close it walks home. A new choice mid-walk replans from the nearest node.
4. **Staff bots.** Fixed spots per room: Bellwether has the owner beside the owner desk and up to three customers at the queue; Stonebridge has a revenue owner at the pipeline wall and one requester at signal intake; Northline has the co-op owner at the brief counter and one rider at booking intake. Staff bots never walk. Customer count shows at most three and is decoration, never a count of records.
5. **Motion limits.** Walk bob at most 0.09 units; idle bob at most 0.02 units on a cycle no faster than 0.35 Hz; blink 120ms every 2 to 5 seconds; antenna lamp brightness varies by at most 40%. Idle motion runs only when `ambientEligible()` is true. Compact tier, reduced motion and suspend place every bot at its settled spot with no travel and no idle motion.
6. **Honesty.** No bot carries a verdict, slip, score, version label or result. No bot has an "AI" label. The "You" chip is the only text on the learner bot.
7. **Resources.** Crew geometries and materials are registered once through the scene's existing `register` sets and disposed once. Partial initialization releases them.

### 14.3 Budgets

Section 13.8 budgets stay. The crew adds at most 5 bots of about 30 meshes each at the standard tier. If a receipt misses a budget, merge each bot's static meshes into one geometry per material before dropping anything visible.

### 14.4 New fail-capable checks

| Check | Fails when |
|---|---|
| `resting_tags_show_next_and_one_failure` | more than two tags rest-visible, or the guide station or the first failing station is hidden, across the seven steps |
| `hidden_tags_stay_reachable` | a resting-hidden tag leaves the tab order, loses its name, or is not visible on focus |
| `one_narrator_bubble` | two bubbles show, or the speaker station's tag shows beside its bubble |
| `bot_walks_only_on_learner_choice` | any publication, poll, replay or ambient tick moves the learner bot off its node without `setOpenStation` |
| `crew_routes_stay_clear` | a route segment between graph nodes intersects any station furniture footprint, for every room |
| `crew_settles_without_motion` | reduced motion, compact tier or suspend leaves a bot mid-route or bobbing |
| `crew_disposed_once` | a crew geometry or material survives dispose, or is disposed twice, over 30 board switches |
| `crew_carries_no_result_text` | the "You" chip or any bot label contains a verdict, version, score or "AI" |

Each check gets one mutation that makes it fail, recorded in the slice checkpoint.
Existing checks change only where listed here: the S37 bubble assertions move from two bubbles to one, and the S38 tag-overlap cells measure rest-visible tags plus the hovered tag; the old assertion text is recorded in the checkpoint.

### 14.5 Least confident decisions

1. **Freezing idle crew after 20 seconds.** Reusing the ambient stop rule keeps the frame budget and honesty rule simple, but the room goes still where the reference keeps moving. The alternative, a crew-only always-on idle, needs its own budget.
2. **Hidden tags.** Fewer tags may slow discovery for a first-time visitor; the hover reveal and the 3D lamps carry that load. The five-question comprehension target remains unmeasured.
3. **Robots as the client's people.** Toy robots standing in for bookshop customers is a style choice; the bubble still names them as customers.
