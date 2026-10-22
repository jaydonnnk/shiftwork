# Visual specification: the work and its consequences

**Revision APPROVED, 2026-10-21, in one batch with Gates 2 and 4.** The user answered "Yes i approve gates 2 to four" on 2026-10-21.
[Section 11](#11-full-screen-workplace-revision-2026-10-21) specifies the re-approved full-screen Gate 1.
Where a section below carries a "Revised by section 11" note, section 11 wins for new work; the older text is history.

Part of Gate 3 APPROVED, 2026-10-19, Asia/Singapore, with
[03-program-design.md](03-program-design.md). This specifies original art to be
made later. The [static colour study](mockups/08-visual-spec.html) illustrates
composition, identity and hierarchy. It is not a Three.js render or execution
receipt. The eight approved grayscale studies remain unchanged.

## 1. Visual idea

Revised by section 11.1: the exclusion list changes.

Show a working place where a learner's decision acquires consequences. The room
has recognizable objects, useful empty space and a fixed orientation. The
workbench has the evidence and controls. A small assessment plinth separates
observed output from recorded consequences; two candidate stands stay visibly
apart from the operating console. These positions teach the distinction before
any animation starts.

Borrow spatial coherence, selective detail and clear stages from the reviewed
[agentic-factory reference](https://github.com/Aboyang/agentic-factory/tree/607e77bc38703ff4704241c532d0b78d9f7dd245).
Do not borrow its geometry, artwork, source, mascot, factory process or payments.
No conveyor, robot workforce, avatar, floating score, victory flash or automated
repair choreography. The learner remains the person who explains, tests and chooses.

## 2. Screen composition and evidence hierarchy

Revised by section 11.2: layout A is replaced; the four-level evidence hierarchy stays for the inspector.

Use layout A. At 1280px, reserve a full-width hosting row above a 58% room and
42% workbench composition. The workbench is at least 480px wide, both columns
have `min-width: 0`, and the main region is at most 1600px wide. Use a 24px
desktop gutter and 16px internal panel spacing. At widths where both minimum
columns do not fit, stack before either becomes cramped; the breakpoint is
1100px. This stack breakpoint is separate from the 760px compact-render tier.

At 640px and 390px, show role/client, hosting disclosure, current task and exact
operating identity first, then a compact room with its labelled station list,
then the workbench. Room height is 240px at 640px and 200px at 390px. Never put
mandatory evidence only in a canvas label. A station selection scrolls and
focuses the panel immediately. Room rendering may suspend once out of view.

Four levels of information, in this order:

1. Current learner task and its next existing valid control. Label the current
   selection or "None selected", evidence purpose and mode in the same visible
   header. An action blocked by evidence states the concrete missing condition.
2. Selected request, observed answer and independent verdict. A failed mandatory
   task appears above optional supporting detail. "Complete experiment" never
   replaces eligibility or task verdict.
3. Compared versions, conditions, missing slots and tradeoffs. Show blockers
   beside their candidates; never behind a disclosure. No winner badge or
   preselected choice. Rationale and explicit choice remain separate from operation.
4. Supporting public records, full hashes, raw captured bytes, slot detail and
   history in native disclosures. Preserve existing evidence access and limits.

The room is the memorable element. Keep the surrounding interface quiet: one
workbench with section dividers, not a collection of equal floating cards.
Use rounded corners only where they indicate a control or physical object.
No gradient headings, glow, glass, full-screen camera intro or ornamental numbers.

Expanded work uses the full main width with a maximum 1120px reading/editing
area, a persistent task/identity header and an ordinary Restore room button.
No modal, duplicated textarea or detached editor. At narrow widths, expansion
collapses the optional overview rather than making code smaller. A code block
may scroll internally; the page never scrolls horizontally. Forms, evidence
text and tables wrap or reflow. Workbench text never uses 3D perspective.

## 3. Palette, type and materials

Revised by section 11.3: light room, navy panels, emissive lamps.

Preserve Shiftwork's navy and amber identity. The light workbench is cool white,
distinct from the warm materials inside Bellwether. No remote fonts.

| Token | Value and use |
|---|---|
| Navy | `#202c40`, application navigation and room cut edges |
| Ink | `#263443`, workbench text |
| Work surface | `#f4f6f8`, workbench background; `#ffffff`, input/evidence area |
| Amber | `#edbd68`, selected station rim and current operating position |
| Muted text | `#526273` on light surfaces; `#c3cdd8` on navy |
| Line | `#c7d0d9`, control and evidence-section separation |
| Failure | `#a43832` on light surfaces; text and a failure symbol accompany it |
| Verified local result | `#32684d` on light surfaces, only beside the check it describes |
| Focus | `#176799`, 3px outline with a contrasting offset on both backgrounds |

Use the existing system sans stack, `Segoe UI`, system-ui, sans-serif. Titles
28px/34px, panel headings 22px/28px, task headings 18px/26px, body 16px/24px,
secondary metadata 14px/20px. Use the existing local monospace stack only for
code and identities. Controls are at least 44x44 CSS pixels. Body line measure
is 68 characters. A small Bellwether sign may retain the existing Georgia
bookshop wordmark; it is not the application's default heading style.

Measure text contrast at implementation: at least 4.5:1 for normal text, 3:1
for large text and control/focus boundaries. Do not assume a palette sample
proves contrast in the rendered scene. Amber is an accent on navy, never small
yellow text on white. Colour alone never communicates state.

Use physically simple, mostly matte materials. Metal roughness 0.65, metalness
0.15. Painted wall roughness 0.95, metalness 0. Wood roughness 0.85, metalness 0.
Paper roughness 1.0. Use three flat tones per wood assembly rather than a wood
texture. Small bevels come from authored low-poly geometry, not a bevel shader
or imported model. No emissive status glow; labels carry the meaning.

## 4. Shared spatial grammar, camera and lighting

Revised by sections 11.2 and 11.4: perspective camera, ACES, environment and fog; station tags over the room replace the caption below it. The room grid and anchors stay.

World units are design units, not metres. Use a 12-unit wide by 9-unit deep
floor, y-up, front at z=+4.5 and back at z=-4.5. Back and left walls are 3.2
units high; front and right remain open. The room's object groups have clear
silhouettes and at least 0.6 units of separation. No full roof, dense town,
decorative clutter or inaccessible tiny text baked into textures.

Orthographic camera starts at `(12, 11, 14)` looking at `(0, 0.8, 0)`. Frame the
room bounds with a 12% screen-space safety margin on desktop and 8% in compact
mode. Recompute the orthographic extents from the container aspect. Fit bounds,
never crop a wall or station to fill the canvas. Keep camera azimuth and elevation
fixed. A selected station permits a target shift of at most 0.5 units and zoom
of at most 1.08x, only when all essential station anchors remain within bounds.
On compact screens, use the whole-room frame with no camera motion.

Use `MeshStandardMaterial`, sRGB output and Neutral tone mapping, exposure 1.0.
One hemisphere fill uses sky `#dbe6f2`, ground `#394453`, intensity 2.0. One
directional key at `(-6, 10, 6)`, colour `#fff1d8`, intensity 2.5 provides shape.
These are starting authoring values under the pinned engine, not measured
photometry. The single standard-tier soft shadow is bounded to the room. Compact
mode uses shallow translucent contact patches under furniture, no shadow map.
No HDR image, bloom, ambient-occlusion pass or point-light collection.

All labels remain HTML. Show one selected-object caption aligned below the
room and a clear station list, rather than ten overlapping speech balloons.
An unobtrusive hover outline may identify a pickable object. The selected object
has a stable amber base/rim, not a pulse. Status text outside the canvas remains
readable when the 3D projection is small or unavailable.

## 5. Bellwether Books: service room

Revised by section 11.3: Bellwether's colours turn light. Its anchors, objects and meanings stay.

Warm ash shelves and paper sit inside navy painted walls. Use floor `#a89477`,
wood `#b99a70`, shelf shadow `#6c5943`, paper `#e7deca`, blue workstation enamel
`#48617a`. Books are short irregular groups, not repeated rainbow stripes.
Only a sign, books and a small staff tray establish the shop; there is no store
simulation or shopkeeper NPC.

| Anchor, x/z | Object and meaning |
|---|---|
| `(-4, +2.5)` | Customer intake tray and one selected request marker. Recorded request count is a label, never an invented live queue. |
| `(-3.7, -2.4)` | Owner desk with open requirements folder, canonical `owner` station. |
| `(0, +1.1)` | Operating console. Its inset version plate belongs only to the accepted operating selection. An empty plate says no selection. |
| `(+3.3, -0.2)` | Small independent-assessment plinth behind a low divider. Its public result is inspectable; no editable scoring screen or exposed expected answer. |
| `(0, -2.5)` | Diagnosis desk with an empty two-part cause/falsifier worksheet before learner commitment. No automatically written hypothesis. |
| `(+0.7, +3)` | Paired A/B test bench with equal-sized candidate stands. No physical winner position. |
| `(+4, -2.8)` | Incident and consequence wall with labelled totals and unresolved incident tabs. No generic room health meter. |
| `(-4.2, -0.2)` | Read-only incident review tray for `repair`. |
| `(+4, +2.5)` | Handover shelf for original choice, retained alternative and inherited limits. |

`pipeline` uses a selectable narrow evidence bridge between console and assessment,
not a production conveyor. Trace only one selected request at a time. Lines are
absent when no linked evidence exists. A dashed link means missing evidence,
with its reason in text. A short trace after accepted arrival explicitly means
"Recorded evidence added", never "The customer succeeded".

## 6. Bellwether's complete story

Each row is a distinct state in one continuous room. The learner may inspect
other stations freely; this is not an enforced linear wizard.

| Beat | Room treatment | Workbench and meaningful transition |
|---|---|---|
| Inspect failure | Intake tray and assessment plinth are in focus; operating plate remains whatever is actually selected. | Exact request, answer, version, purpose/mode and failed mandatory task first. Historical entry is still. |
| Learner cause/falsifier | Diagnosis desk becomes selected; failed request stays visible in the panel. | Cause, falsifier and public test inputs. Recorded entry gets an identity only after acceptance. Help follows existing commitment rules. |
| Test | One test-stand status changes to the actual RESERVED/RUNNING/COMPLETE/FAILED state. | Diagnostic labels, missing evidence and public results. It cannot qualify selection or touch the wall. No invented path inside the model. |
| Compare repairs | Equal A/B stands, both version identities present; operating console unchanged. | Shared frozen conditions, exact versions, mandatory blockers and public metrics. Compare slot states directly; unknown cost stays unknown. |
| Select exact version | The operating plate updates only after accepted selection. Candidate stands and alternative remain. | Rationale and explicit eligible choice. A 180ms plate emphasis acknowledges the recorded choice, with no business outcome. |
| Operate | Existing operation control stays in the workbench. Room labels queued/running/captured without implied success. | Exact run and selection IDs. Only a new, linked synthetic ledger event may cause a 320ms evidence-arrival trace to the relevant wall entry. Failure or incomplete evidence keeps its actual meaning. |
| Inherit consequences | The new shift opens to a quiet baseline with the same selected plate, inherited markers and unresolved tabs. | Original rationale, tests, requirements, limits and retained alternative. Later-condition experiment stays on the A/B bench and never rewrites the wall. |

Closing a shift is not selection. Opening the next shift is not a success
ceremony. A late alternative that performs better creates comparison evidence,
not retroactive approval or replacement of the original choice.

## 7. Stonebridge Software: routing and ownership

Use a broad team routing table and a stepped ownership wall, not bookshop
furniture. Floor `#8b959f`, walls navy, anodized desk `#61758a`, routing pins
`#d7bb75`, slate wall lanes `#35495e`. Keep navy/amber application identity;
do not use a neon sales dashboard or a bank/payment visual.

- Signal intake at `(-4,+2.2)`: a short rack of signal folders. The selected
  signal follows its recorded ID; count labels do not fabricate unexecuted leads.
- Qualification rules at `(-3.5,-2.5)`: a wall-mounted rules sheet with no score
  ranking or hidden grading controls.
- Workflow bench at `(0,+0.6)`: a branching routing table with equal test stands.
  Experiments illuminate its local route only and leave operational owners alone.
- Pipeline wall at `(+3.7,-2)`: vertically separated owner lanes, recorded SLA
  start markers and a human-handoff tray. `OWNER_ASSIGNED` moves one labelled
  synthetic routing marker only under the program design's linkage guard.

`SLA_CLOCK_STARTED` shows its recorded start state, not a fabricated live
countdown. `HANDOFF_ESCALATED` adds a labelled review marker, never an outgoing
message animation. Duplicate/missing ownership stays a visible problem. No
currency, revenue growth, real CRM write, email-send icon or progress celebration.
History and later experiments remain separate even when the newest run is a trial.

## 8. Northline Bike Cooperative: permission and handover

Use a repair counter, booking-slot rail, steel integration bench and a runbook
shelf. One bicycle on a stand gives the workshop its silhouette. Floor
`#87978c`, painted walls `#28494a`, bench steel `#657b7c`, plywood `#b4a17e`,
tool outlines `#d3d9cf`. This is a co-op integration workplace, not bicycle racing
or a shop sales game.

- Brief at `(-4,+2.5)`: counter clipboard for customer requirements.
- Map at `(-3.7,-2.2)`: two separated read lanes for availability/schedules and
  one permitted repair-slot write lane. A boundary bar marks permission. It
  describes the declared contract; it cannot grant, expand or prove permissions.
- Bench at `(0,+0.6)`: integration assembly, learner worksheets and A/B tests.
- Acceptance at `(+3.5,-1.5)`: a check fixture beside the booking rail, visibly
  separate from the test bench. It displays the recorded checks and missing data.
- Rollout at `(+3.8,+2.2)`: pilot schedule rail. Only `BOOKING_COMMITTED` creates
  a committed-slot marker. `ROLLOUT_APPROVED` alone creates an approval label;
  a tidy bench, passing experiment or chosen integration cannot imply it.
- Handover at `(0,-3)`: runbook shelf with explicit proposed/recorded distinction.
  `HANDOVER_DECLARED` shows a recorded declaration. It does not prove a person
  received, read or accepted the handover.

Experiments may show sample booking evidence in the panel but cannot place a
pilot booking. Safety escalation moves to a human-review tray only when its
record exists. Retain retry-safe booking and selected permission/runbook evidence
in the workbench. Acceptance, rollout and handover must each move their panel
into reach at 390px using labelled buttons, not only object picks.

## 9. Motion, loading and failure states

Revised by section 11.5: replay and ambient motion added; the 160, 180 and 320ms rules stay.

Timings are design limits. They are not claims about execution latency.

| Trigger | Treatment |
|---|---|
| Selected station | Immediate HTML focus/content update; 180ms ease-out focus-rim change. Optional bounded desktop camera target adjustment <=220ms. |
| Accepted experiment update | 160ms local test-stand emphasis. Show only observed slot states, with no per-slot progress bar. |
| Accepted operating selection | 180ms plate/caption change. No travelling request or wall update. |
| Confirmed linked consequence arrival | At most one 320ms evidence trace, annotated as recorded arrival. Multiple arrivals settle together with a count, never a replay queue. |
| Normal polling load | Keep geometry and last accepted view visibly dimmed, with "Refreshing recorded state". No moving spinner suggesting execution. Workbench action guards remain owned by current controller state. |
| Error or conflicting reads | Static room geometry, unavailable current labels and explicit error/inconsistent-evidence text. No stale pass/status badge. Recovery begins quietly. |
| Reduced motion | Immediate settled states, no path travel, camera adjustment or repeated effects. Same labels, outcomes and controls. |
| Graphics failure | Existing static fallback and complete HTML workbench. Explicit local graphics retry. Never show made-up evidence to fill the space. |

There is no idle motion, blinking warning, continuous request stream or background
camera drift. New data remains readable immediately; animation never gates a
command or delays a verdict. Change motion preference during an active trace and
the view settles immediately. Hidden, expanded or offscreen scenes settle and
discard animation rather than playing catch-up when shown again.

## 10. Visual review obligations

Extended by section 11.6.

Compare real desktop and physical mobile renders to this specification after
implementation. Inspect silhouettes with labels hidden, then inspect the actual
labels and workbench at normal size and 200% zoom. Check that each room is
recognizable without its title, that the active object does not occlude another
station and that the operating plate cannot be mistaken for the newest candidate.

Review the whole Bellwether journey, including failure, blocked comparison,
selection without operation, failed partial operation, inheritance and the later
alternative. Then review Stonebridge's signal/owner and Northline's permission,
booking, acceptance and handover differences. Measure the program design's
budgets and access targets; screenshots alone cannot pass them.

User approval of this design does not prove art quality, frame rate, browser
compatibility, comprehension or learning. Final scene art and performance evidence
remain future work under separately approved implementation authority.

## 11. Full-screen workplace revision, 2026-10-21

Status: APPROVED 2026-10-21 in the user's batch approval of Gates 2 to 4.
This section specifies the look and motion of the re-approved [Gate 1](01-product.md) and its [v2 mockups](mockups/v2/index.html).
The mockups use the existing `room.svg` as a stand-in; they are not renders.
Every value below is a starting authoring value, not a measured result.
Sections 5 to 8 (room contents, Bellwether's story beats and the other two rooms) stay in force except where this section changes them.

### 11.1 Visual idea (replaces section 1's exclusion list)

The room is the whole screen, and the learner's work floats over it as small panels.
Paper is the signature: requests are slips, verdicts are stamps, incidents are pinned cards, the live version is a framed plate on the service console.

Still excluded: a robot, mascot, avatar, AI worker or any character standing in for the learner; a floating score; a victory flash; automated repair choreography; the reference's artwork, geometry, source, factory, conveyor, procurement or payments.
Now allowed: labelled recorded slip replays, station lamps, an attention ring and slow ambient movement, all bound by the rules in Gate 3 section 13.5.

### 11.2 Composition (replaces section 2's layout A)

- **Hosting row.** Full width, first, never overlapped. Unchanged text.
- **Stage.** Fills the remaining viewport height, minimum 560px at 761px and wider. The canvas fills the stage.
- **Floating panels, 16px inset, 12px radius, navy surface.** Status bar top-left; step chip top-centre; next-action panel bottom-left; shift log bottom-right, 410px wide, list at most 168px tall before it scrolls inside itself; inspector left, `clamp(360px, 32vw, 480px)` wide, from below the step chip to the stage bottom.
- **Station tags.** Pill buttons at each station's projected anchor: name, status words and a small lamp dot. At least 44 by 44 CSS pixels including padding. The tag of the attention station gets an amber outline.
- **Bubbles.** At most one customer bubble above the queue and one owner bubble above the owner desk, 270px maximum width, a speaker label above the text.
- **Dialogs.** Centred, 520px maximum width, over a 55% navy scrim. The choose dialog and the shift report follow screens 13 and 15.
- **Shift picker.** Full stage overlay with the seven steps and one card per board, as screen 10.
- **Evidence hierarchy.** Section 2's four levels still order the inspector's content. The main view carries only level 1: role and client, current step, next action, live version label and one narrator line.
- **760px and below.** Panels become a single column in this order: hosting row, status bar, step chip, room (240px tall at 640px, 200px at 390px), station tags as a two-column list, next action, inspector content, shift log. No overlap, no horizontal scroll, no camera motion.
- **Expanded work.** Unchanged from section 2 except that it spans the stage instead of the main grid.

### 11.3 Palette and materials (replaces section 3's light workbench and "no emissive glow")

The room turns light; the interface stays navy; amber marks attention.

| Token | Value and use |
|---|---|
| Panel surface | `#121b27` with 1px `#2a3a4f` border; text `#eef2f6`, muted `#a9b6c4` |
| Navy trim | `#202c40`, room cut edges, skirting and console bodies |
| Amber | `#edbd68`, attention ring, attention tag outline, current step name |
| Fail | `#e86b74` on navy panels; `#a43832` on light surfaces |
| Pass | `#84c787` on navy panels; `#32684d` on light surfaces |
| Info | `#8fb8e0` on navy panels |
| Focus | `#7cc4ff` 3px outline on navy panels; `#176799` on light surfaces |
| Bellwether floor | warm light wood `#d6c3a0` |
| Bellwether walls | cream `#efe6d4` |
| Bellwether wood and shelves | `#c7a77a` and `#8a7052` |
| Paper and slips | `#f6f0e2` |
| Lamps | fail `#ff5a4e`, attention `#ffb648`, pass `#4fd17a`, idle `#9aa6b2`, unbloomed `MeshBasicMaterial`, `toneMapped: false` |

System sans stack and the existing monospace stack, as section 3; monospace only inside the shift log and code. No remote font.
Text contrast is measured on the rendered page: at least 4.5:1 for normal text and 3:1 for large text and control or focus boundaries. Lamp colour never carries meaning alone; the tag text does.

Materials: wood roughness 0.7, painted wall 0.85, paper 0.9, metal 0.42 with metalness 0.3, console enamel 0.55.
Rounded edges on furniture and props with a 0.04 to 0.06 unit bevel on the standard tier; plain boxes on compact.

### 11.4 Camera and lighting (replaces section 4's camera and lighting paragraphs)

The room grid, anchors and object separation in section 4 stay.

- `PerspectiveCamera`, vertical field of view 30 degrees, looking at `(0, 0.8, 0)` from azimuth 45 degrees and elevation 39 degrees. Distance is fitted so the room bounds sit inside an 8% screen margin. Azimuth and elevation never change.
- Inspector open at 761px and wider: shift the view offset so the room centre sits in the uncovered part of the stage, eased in at most 480ms. A station choice may move the target at most 0.6 units, within the same ease.
- 760px and below: the same fixed pose fitted to the compact room, with no view offset and no motion.
- `ACESFilmicToneMapping`, exposure 1.0, sRGB output.
- Hemisphere fill sky `#f3efe6`, ground `#8a7b66`, intensity 1.2. Directional key at `(-6, 10, 6)`, `#fff1d8`, intensity 2.2, with the single 1024 shadow map on standard.
- Environment: the first-party PMREM studio environment from Gate 3 section 13.3, intensity 0.45, standard only.
- Fog: linear, colour equal to the wall tone, near at 1.4 and far at 2.6 times the camera distance.
- Still no HDR image, bloom, ambient-occlusion pass, post-processing or point-light collection.

### 11.5 Motion (replaces section 9's table and its no-idle-motion paragraph)

Timings are design limits, not execution latency.

| Trigger | Treatment |
|---|---|
| Station chosen | Immediate HTML focus and content; inspector slides in over 200ms; camera ease at most 480ms at 761px and wider; 180ms rim change on the tag. |
| Accepted experiment update | Unchanged: 160ms test-stand emphasis, observed slot states only. |
| Accepted live-version choice | Unchanged: 180ms plate change. No slip, no wall change. |
| Linked consequence arrival | Unchanged: one 320ms trace, annotated as recorded arrival. |
| Recorded replay | Slips leave the queue in ordinal order, 250ms apart; each leg (queue to service, service to inspector's desk, desk to wall) takes 400ms; the stamp shows the actual verdict for 240ms before the last leg. At most 12 slips move; the rest settle with a count. Whole replay at most 6 seconds. The "Recorded replay" chip shows throughout and "Show settled result" skips. A slip with no linked event settles at the desk instead of reaching the wall. |
| Ambient | The attention ring scales between 1.00 and 1.05 and attention or fail lamps vary brightness by 15%, both on a 2.5-second cycle. No blinking, no hue change, nothing faster than 0.5 cycles per second. Stops by the Gate 3 section 13.5 rules. |
| Polling, error, reduced motion, graphics failure | Unchanged from section 9. Reduced motion shows settled stamps, lamps and ring with no travel, ambient or camera motion. |

Animation never gates a command or delays a verdict. Hidden, expanded or offscreen scenes settle rather than catch up.

### 11.6 Review obligations (adds to section 10)

- Review the main view of the entry, mid-loop decision and later consequence states against Gate 1's limit of one question, one next action and one narrator line, with no hash or internal identifier.
- Watch a failed operation replay and check that nothing in it could make a reviewer believe the customer was helped.
- Read every owner line and picker question for hints at a cause, a fix or a choice.
- Inspect the light room with labels hidden and with the inspector open at 1280px, and compare against screens 11 to 16. Screenshots of the stand-in picture do not pass art review.
- Measure contrast of tags, bubbles and panels over the light room, and over the static fallback.

## 12. Robot crew and declutter, 2026-10-23

Status: APPROVED 2026-10-23 in the user's batch re-approval of Gates 1 to 4: "I re-approve Gates 1 to 4 for the robot crew and declutter. Commit the docs, then start S41 on shiftwork/slice-41."
Reference: [crew mockup](mockups/v2/17-robot-crew.html).
This section replaces section 11.1's exclusion of a robot or character; the rest of section 11.1's exclusion list stands.

**Look.** Voxel-like, friendly and small: a box body, a cream head with a dark screen face and two glowing eyes, short legs, swinging arms and an antenna lamp. About 1.1 metres tall in room units after scale, so a bot reads at a glance at 1280px.

| Bot | Body | Trim | Lamp | Extra |
|---|---|---|---|---|
| You | amber `#edbd68` | navy `#202c40` | amber | "YOU" chip above |
| Owner | navy `#202c40` | room wood | paper | flat cap |
| Customers | muted teal, clay, lavender | slate `#3b4656` | paper | slightly smaller |

Away rooms reuse the same bot with their room palette for trim.

**Calm room at rest.** At 1280px, the room shows the next-action tag, at most one failure tag, one bubble and the "You" chip. The 3D hint card is removed; the room label stays available to assistive technology. Tags fade in over 180ms on hover or focus.

**Camera.** The fit uses the floor footprint, not the wall tops, so the room fills more of the screen; wall tops may crop under the status bar, as in the reference.

Motion values are in Gate 3 section 14.2 rule 5.
