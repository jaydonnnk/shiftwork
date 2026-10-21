# Proposal: make Shiftwork look and read like agentic-factory

Status: PROPOSAL ONLY, 2026-10-21.
Nothing here is approved.
Adopting it requires backtracking the workplace-3d Gate 1 visual direction (section 7 below).
No code changed while writing it.

Reference reviewed: `https://github.com/Aboyang/agentic-factory` (shallow clone, 2026-10-21), its ten screenshots in `docs/screenshots/`, and `game/src/world/World.js`, `palette.js`, `director.js`, `ui/UI.js`, `ui/agentpanel.js`, `ui/ui-shell.css`.
Shiftwork reviewed: local offline preview (`demos.client --recorded-assist`) at 1440x900, `shiftwork/client/workplace-scene.js`, `workplace-rooms.js`, `index.html`, `workplace-3d/visual-spec.md`, `workplace-3d/01-product.md`.

## 1. Verdict

The gap is mostly not rendering technology.
It has three causes, in order of weight:

1. **Our own spec forbids what makes agentic-factory feel alive.**
   `visual-spec.md` section 1 bans a conveyor, an avatar, floating values, automated choreography and travelling requests.
   Section 9 caps motion at one-shot pulses of 160 to 320ms.
   A room that is still until a 320ms pulse fires cannot feel like a living workplace, whatever the shader.
2. **Shiftwork is a document with a 3D picture in it. Agentic-factory is a world with panels floating on it.**
   Our canvas is roughly a fifth of the screen, dark navy on a dark navy page, below a paragraph of version IDs and hashes.
   Their canvas is the whole viewport, and every panel floats over it.
3. **We show the evidence record first and the story never.**
   Above our fold: "Operating choice: ver-0001 (VALID). Saved version: ver-0001. Inspected run: run-0002. Executed version: ver-0001. OPERATION / RECORDED_INSPECTION."
   Above theirs: "The servo throws the fault. Is the servo really the problem?"

Rendering differences are real but smaller (section 3).
Fixing only the renderer would give a prettier small box inside the same document.

## 2. What agentic-factory does, and why it works

| Pattern | Where | Why it reads well |
|---|---|---|
| Full-viewport world, UI floats over it | `ui-shell.css` `.slot-hud`, `.slot-log` are `position: fixed` over the canvas | The place is the product. Panels feel like tools you pick up, not pages you read. |
| One scenario card per lesson, with a one-line question and a "Teaches" line | `docs/screenshots/01-scenarios.jpg`, `ui/scenarios.js` | The learner knows the single question before anything moves. |
| A numbered step rail shown before play | Title screen: "1 Read sensors, 2 Read the plant log, 3 Diagnose, 4 Buy, 5 Pay, 6 Verify" | The whole loop is learned in one glance. |
| A progress chip top-centre: "Robot Arm · Diagnosing... 1/7" with seven dashes | `agentpanel.js` `STEPS`, line 20 | You always know where you are in the loop. |
| A narrator speech bubble pinned to the world | `UI.js` `say()`, bubble follows `world.screenPos('robot')` each frame | Every state change is explained in one plain sentence at the place it happens. |
| Status is physical: andon lamps, a red floor ring, a fault-code chip over the machine | `machines.js`, `World.js` `#rings()` | You see what is wrong before you read anything. |
| Idle life: belt moves, robot bobs and blinks, lamps blink when down | `robot.js` lines 302 to 353, `line.js` | The room feels running even when nothing is happening. |
| Details live in a terminal log, not the main view | `ui/plantlog.js`, `plant.log` panel bottom-right | Codes and numbers are available but never block the story. |
| A small HUD with four numbers and one budget bar | `ui/hud.js` | Business state at a glance. |
| Decision modal that says why it asks you | `06-approval.jpg`: "Why it asks you: over remaining budget" | The human decision is framed, bounded and consequential. |
| Result card with a cost breakdown | `07-fixed.jpg`: "Back online. Root cause: 24V power supply. Parts, Labor, Downtime, Total" | A visible before and after. |
| Camera eases to the place that matters, then back | `World.js` `fly`, `DOCK_FIT` | Attention is directed without the learner driving a camera. |

## 3. Rendering recipe differences

| Setting | agentic-factory | Shiftwork now | Effect |
|---|---|---|---|
| Canvas size | Whole viewport | Small box inside the page | Biggest single visual difference |
| Camera | `PerspectiveCamera`, FOV 30, pitch about 39 degrees | `OrthographicCamera` | Perspective gives depth; ortho reads as a diagram |
| Tone mapping | `ACESFilmicToneMapping` | `NeutralToneMapping` | ACES gives the soft, saturated toy look |
| Environment light | `RoomEnvironment` through `PMREMGenerator`, intensity 0.42 | None, hemisphere plus one directional | The environment map is what makes surfaces look soft and lit from everywhere |
| Geometry | `RoundedBoxGeometry` everywhere (bevel up to 0.06) | Plain `BoxGeometry` | Bevels catch light; sharp boxes look like blockout |
| Material roughness | 0.68 matte, 0.42 metal | 0.95 to 1.0 | Ours are chalky with no highlights |
| Palette | Light floor and walls (`#dfe4ec`, `#eaeef4`), saturated accents | Navy room on navy page | Ours has almost no value contrast |
| Light sources | Emissive `MeshBasicMaterial` with `toneMapped: false` | Emissive pulses only | Their lamps read as glowing lights |
| Pixel ratio | Up to 2, lowered adaptively | Capped at 1.5, 1 on compact | Ours is softer on Retina |
| Fog | `Fog(FOG, 55, 135)` | None | Fog gives distance |

Their addons come from `three/examples/jsm`.
Our vendored r180 has only `three.module.js` and `three.core.js`.
`RoundedBoxGeometry.js` and `RoomEnvironment.js` from the same r180 release are MIT and would be vendored locally, keeping the no-CDN, no-build-step rule.
`workplace-assets.json`, `vendor/three-r180/manifest.json`, `THIRD_PARTY_NOTICES.md` and `tests/packaging/test_client_asset_closure.py` would need the new files.

## 4. Translation: their pattern, our version

The rule: borrow the shape, keep our honesty and our product.
The learner stays the person who explains, tests and chooses.
Nothing moves unless a recorded event caused it, and every replay is labelled as one.

| agentic-factory | Shiftwork version (Bellwether first) |
|---|---|
| Scenario picker cards with "Teaches" | Shift picker. Card example: "Customers ask about pickup hours and get a price list. Is it the lookup or the router?" Teaches: "Write what would prove you wrong before you touch code." |
| Step rail 1 to 6 | Learner rail: 1 Read the complaints, 2 Explain the cause, 3 Say what would prove you wrong, 4 Try two fixes, 5 Choose one, 6 Run the shift, 7 See what happened. |
| Top-centre chip "Diagnosing... 1/7" | "Bellwether · Step 3 of 7 · Say what would prove you wrong", seven dashes, driven by the real controller state. |
| Wrench-bot speech bubble | The shop owner and customers speak, never decide. Owner bubble at the owner desk: "Three people asked about collection yesterday and left without an answer." Customer bubbles over the queue show the actual recorded request text. |
| Andon lamps | One lamp per station from real state: ledger wall red while incidents are open, compare bench amber while a comparison is unreserved, service console green only after a selected version passed its checks. |
| Red floor ring under the broken machine | Amber ring under the station that holds the next valid action. |
| Conveyor with parts | During a run replay only: paper request slips move from the customer queue to your service console, then to the evaluator plinth, which stamps each PASS or FAIL from the actual check result, then to the ledger wall. Chip: "Recorded replay". Reduced motion shows the settled stamps. |
| plant.log terminal | `shift.log` terminal bottom-right, streaming real events: run started, check `cr-0001` failed `MISSING_EVIDENCE`, incident `BWB-01` opened. All hashes and IDs move here and to the station inspector. |
| HUD top bar | Shift clock, customers answered, unresolved incidents, attempts left with a bar, and a permanent "Synthetic scenario" badge. |
| Approval modal "Why it asks you" | Choose-version modal: "Make ver-0002 the live version?" Why: the comparison results. What you keep: ver-0001 stays as the backup. What changes: only the next operation uses it. |
| "Back online" cost card | Shift report: complaints before and after, checks passed, incidents opened and closed, all labelled synthetic. |
| Machine popover with sparklines | Station inspector panel sliding in from the right, holding today's workbench content for that station. |
| Manager dashboard | Shift history: every run, choice and incident across shifts. |

### Plain-language rename

| Now | Proposed on screen | Kept in the log and inspector |
|---|---|---|
| Operating choice | Live version | Yes |
| Retained alternative | Backup version | Yes |
| Falsifier | What would prove me wrong | Yes |
| Executed version, inspected run, content hash, requirement hash | Hidden from the main view | Yes |
| OPERATION / RECORDED_INSPECTION | "Recorded replay" chip | Yes |
| Independent evaluator | Inspector's desk (locked) | Yes |

Copy rule: the main view shows at most one question, one next action and one narrator line.

## 5. Visual direction with our own flair

- Keep navy and amber, but invert the room: warm light wood floor, cream walls, navy as trim and UI chrome, amber as the attention colour.
  This gives the value contrast agentic-factory gets from its light floor.
- Bellwether is a bookshop, not a factory: shelves, a counter, a till, paper slips and stamps instead of belts and robots.
  Northline is a bike workshop with a parts wall and a booking board.
  Stonebridge is an office with a pipeline wall.
- Paper and stamps are the signature motif: requests are slips, verdicts are stamps, incidents are pinned cards, the chosen version is a framed certificate on the console.
- Fonts: Inter for UI, a monospace only inside `shift.log`, the existing Georgia Bellwether sign kept.

## 6. Honesty guardrails that must survive

- Motion replays a recorded event and is labelled; it never stands in for one.
- A stamp shows the actual check verdict; failure and incomplete evidence keep their meaning.
- No celebration unless the recorded check passed, and the report card still says synthetic.
- The owner and customers narrate; they never suggest the cause, the fix or the choice.
- Optional diagnostic help keeps its current rule: only after the learner's own cause and falsifier.
- The full HTML workbench path remains for graphics failure, reduced motion and narrow screens.

## 7. Approvals this needs

These lines were explicit approved decisions and must be revised through a backtrack, not overridden:

- `workplace-3d/visual-spec.md` section 1: "No conveyor, robot workforce, avatar, floating score, victory flash or automated repair choreography."
  Proposed: no robot, mascot or AI worker; recorded replays of request flow are allowed and labelled.
- `workplace-3d/visual-spec.md` section 2: layout A (58% room, 42% workbench).
  Proposed: full-viewport room with floating HUD, log and a slide-in inspector.
- `workplace-3d/visual-spec.md` section 9: 160 to 320ms single pulses.
  Proposed: ambient idle motion, labelled replays up to the recorded run's own duration, camera focus ease up to about 600ms, with reduced motion unchanged.
- `workplace-3d/01-product.md` "Three distinct rooms": the line excluding the reference's robot, factory and process stays; only the layout and motion parts change.
- `workplace-3d/03-program-design.md` sections 5 and 9 for motion eligibility and the renderer settings.

Per the Gate 1 rule, the revision would come with one plain HTML mockup per screen.

## 8. Proposed slices

The deadline is 2026-10-30 10:00 PT, nine days from this proposal.
The hosted demo is still S28, and a new deployment is separately authorized.
So the order front-loads the largest visible change and keeps every slice shippable alone.

| Slice | Visible result | Main files |
|---|---|---|
| S36 Full-bleed world | Bellwether room fills the viewport; workbench becomes a slide-in inspector; HUD bar and `shift.log` float on top; hashes move to the log. | `index.html`, `styles.css`, `app.js`, `workplace-host.js` |
| S37 Render recipe | Perspective camera, ACES, `RoomEnvironment`, rounded geometry, light palette, emissive lamps, fog, pixel ratio 2. | `workplace-scene.js`, `workplace-rooms.js`, vendored addons, asset manifest and closure test |
| S38 Story layer | Shift picker card, seven-step rail and progress chip, plain-language rename, owner and customer bubbles. | `index.html`, `app.js`, new `client/story.js` |
| S39 Living room | Station lamps, attention ring, idle motion, camera focus ease, reduced-motion path. | `workplace-scene.js` |
| S40 Recorded request replay | Slips travel and get stamped from real check results during and after a run. | `workplace-scene.js`, `app.js` |
| S41 Decisions and report | Choose-version modal, shift report card, shift history. | `app.js`, `styles.css` |
| S42 Other rooms | Northline and Stonebridge get the same treatment. | `workplace-rooms.js` |

S36 and S37 together produce most of the visual jump.
S38 produces most of the intuitiveness jump.
If time runs short, S36 to S38 on Bellwether alone is the smallest version worth deploying.

Each slice keeps the existing browser suites green, adds fail-capable checks for any new honesty rule (for example: a stamp never shows PASS for a failed check), and keeps the performance tiers.

## 9. Risks and falsifiers

- **Deadline.** Seven slices in nine days is tight under the current evidence standard; S39 to S42 may not land.
- **Existing tests encode the current layout.** `tests/client/workplace_s30.mjs` to `workplace_s35_controls.mjs` assert layout A, pulse timings and panel positions; many will need deliberate updates, which must be reviewed as spec changes, not silenced.
- **Accessibility.** A full-bleed canvas must not trap focus; every station stays a real button and the inspector stays keyboard reachable.
- **Compact tier performance.** The environment map and pixel ratio 2 cost GPU; keep the adaptive drop that agentic-factory uses (`World.js` `#adapt`).
- **Honesty drift.** Request replay is the feature most likely to look like proof. The falsifier: a reviewer who sees a FAIL run must not believe the customer was helped.
- **Prettier is not better learning.** This improves legibility and appeal; it does not establish learning gain.
