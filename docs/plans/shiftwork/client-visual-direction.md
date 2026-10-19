**Concrete 3D visual specification approved at Gate 3. 2026-10-19 Asia/Singapore.**

The [visual specification](workplace-3d/visual-spec.md) and
[colour study](workplace-3d/mockups/08-visual-spec.html) now define the three
distinct workplaces, stable camera, matte materials, lighting, expanded editing
and truthful transitions. The [program design](workplace-3d/03-program-design.md)
sets the exact delivery and state contracts. Gate 3 is approved. These
are original planning diagrams, not final 3D art or performance evidence.
Focused commits and a main push of Gates 1 to 3 are separately authorized.
The approved grayscale studies remain unchanged. S28's shipped client remains
the delivered baseline; the prior notices retain their original dated scope.

**3D WORKPLACE PRODUCT AND ARCHITECTURE APPROVED, 2026-10-19 Asia/Singapore.**

The user approved [Gate 1](workplace-3d/01-product.md), including layout A,
and [Gate 2](workplace-3d/02-architecture.md), selecting a locally served
Three.js scene beside the persistent workbench. Distinct original rooms, direct
labelled access, full workbench fallbacks and confirmed-state motion remain
required. The contextual-panel mockup is a comparison, not a second build.
Final materials, lighting, detailed scene/motion mapping and release/asset pins
remain Gate 3 work. No final-art, WebGL or performance proof exists. The older
visual baseline remains the historical specification for the delivered S28 client.

**3D WORKPLACE PRESENTATION REVISION PROPOSED, 2026-10-19 Asia/Singapore.**

The user selected a 3D workplace as the intended post-S28 result. The
[Gate 1 proposal](workplace-3d/01-product.md) and
[grayscale HTML studies](workplace-3d/mockups/00-review.html) are under review.
A stable room with a persistent workbench is recommended; a contextual-panel
alternative is also shown. This is not approval of final art, an engine or
implementation. The historical visual baseline below is preserved for S28 and
remains operative until the scoped revision is approved through the relevant gates.

# Client visual direction: operational diorama

**Composition selected by the user:** 2026-09-18.
**Journey revision:** RE-APPROVED 2026-09-24 with Gate 1 after the final-pivot
backtrack. The selected room composition is retained; new runtime UI is not delivered.
**Three-board reconciliation:** APPROVED 2026-09-30 with Gate 1 under the approved
direction memo (`shiftwork_three_boards.md`). One workplace holds a
board selector above the journey navigation: Board 1 keeps the Bellwether service
room, Board 2 adds a revenue floor and Board 3 adds the Northline deployment
workshop.

**Purpose:** visual acceptance brief for the revised product journey. The prior
Slice 9 acceptance remains historical evidence. The new investigation, comparison,
choice and later-experiment requirements are not delivered by that slice and are
not assigned to old Slices 10 or 11 here. Future mapping requires Gate 4 revision.
This brief does not authorize implementation or change the rendering baseline.

## Reference

- [`references/shiftwork-operational-diorama.jpg`](references/shiftwork-operational-diorama.jpg)
  is the composition reference supplied by the user.
- Use its fixed isometric room, station layout, evidence panel and causal path as
  the visual target for every board's room.
- Do not treat text inside the generated image as product copy or evidence. Some
  labels are malformed. All shipped labels and values must come from the approved
  copy or the real API projections.
- The target is a 3D-looking operational space. Real-time WebGL, a walkable avatar
  and a free camera are not required. The approved baseline remains plain HTML,
  CSS and vanilla JavaScript. DOM, SVG, CSS transforms or canvas may produce the
  scene. Any proposed framework, rendering engine or package change belongs to the
  pending Gate 3 reconciliation and requires explicit approval before future
  implementation. Slice 9's historical acceptance is unchanged.

## Product intent

The workplace persists across three role boards. Board 1 is the bookshop's
persistent operational room; Board 2 is a revenue floor; Board 3 is the Northline
deployment workshop. The rooms are the workplace of the learner, who is cast
explicitly as a junior engineer on shift, one role board at a time, and each
business or employer reads as fictional rather than the learner's own. The roles
are fiction, never a credential or job-readiness claim. The learner selects
stations rather than opening unrelated dashboard cards. Every room must make this
chain legible:

`request -> interpretation and information/tool use -> output -> independent task and correctness checks -> synthetic operational consequence`

Investigation follows that evidence into a prediction and a controlled repair
comparison. Only an explicit choice changes the operating version; only operation
produces business consequences. The experiment path must not visually flow into the
operational ledger as though every trial changes the shop.

No room is an open-world game. Movement, characters and environmental detail must
never hide the learner-owned artifact or replace recorded evidence with narrative
animation.

## Station map

### Board 1 · Bellwether service room

| Station | Product responsibility | Required state |
| --- | --- | --- |
| Owner desk | Shared mandatory requirements, learner priorities and visible tests | Distinguishes fixed obligations from learner choices; no repair preselected |
| Service workbench | Learner-owned code, tested candidates and operating version | Shows starter, candidate, explicitly chosen and changed-since-test states separately |
| Customer queue | Executed operational requests | Selected customer maps to the exact executed request and operating version |
| Evidence pipeline | Interpretation, tool use, records, output and independent checks | Shows task relevance as well as factual support; observations separate from hypotheses |
| Independent evaluator booth | Separation of learner work from assessment | Non-editable; no protected answers or model-declared passes |
| Incident and ledger wall | Operational incidents and synthetic consequences | Experiment results never masquerade as incidents resolved or sales completed |
| Repair bench | Prediction, falsifier, learner code, fair experiment and explicit choice | Shows shared conditions, repetition/variation, eligibility, tradeoffs and selected version |

### Board 2 · revenue floor

| Station | Product responsibility | Required state |
| --- | --- | --- |
| Signal intake | Inbound signals and their pinned records | Shows the signal, its source and its recorded qualification, separate from any explanation |
| Qualification rules | The visible contract both workflows must satisfy | Distinguishes mandatory ownership rules from learner additions; nothing sends a customer message |
| Workflow bench | Learner-owned qualification, routing and CRM write logic | Shows candidate, tested and explicitly chosen workflows separately |
| Pipeline wall | Owners, SLA clocks, escalations and missed-handoff incidents | Synthetic pipeline state; experiments never move an owner or start a clock |

### Board 3 · Northline deployment workshop

| Station | Product responsibility | Required state |
| --- | --- | --- |
| Deployment brief | Conflicting requirements and the pilot's rollout gate | Distinguishes the co-op's mandatory acceptance checks from learner choices; no candidate preselected |
| System map | Discovery record, integration surface and permissions map | Access boundaries visible; the integration reads availability and writes slots only |
| Integration bench | Learner-owned validation, escalation and retry-safe writes | Shows starter, candidate, explicitly chosen and changed-since-test states separately |
| Acceptance | Customer acceptance checks and their results | Independently checked: no double bookings, escalation fires, commitments honored, access boundaries held |
| Rollout | Pilot bookings, incidents and rollout decisions | Synthetic pilot state; experiments never change the pilot |
| Handover | What the co-op team receives | Known limits, runbook, unresolved incidents and the retained alternative |

Optional assistance stays visibly separate from the service under investigation
and the evaluator. Show attribution and the applicable shared assistance limit;
diagnostic help follows the learner's initial prediction. Future slice ownership
is deferred to the revised Gate 4.

## Interaction rules

- A workplace selector listing the three role boards sits above the journey
  navigation; opening a board shows its own room and stations. Board 1's journey
  navigation remains: Shift board, Requirements, Investigate, Compare and choose,
  Next shift. The later boards carry the same loop under their own station labels
  (revenue floor: signal intake, qualification rules, workflow bench, pipeline
  wall; Northline deployment workshop: deployment brief, system map, integration
  bench, acceptance, rollout, handover).
- Selecting a journey step activates the matching station while keeping the same
  room identity visible. Selecting a station exposes its evidence or work panel.
- Essential labels, controls and values are HTML overlays, not baked into the room
  artwork. They must be selectable, keyboard reachable and exposed to assistive
  technology.
- The evidence panel shows the selected request, interpretation, tool use, consumed
  public records, output and independent result. Operational views additionally
  show the synthetic consequence; experiment views explicitly say history is unchanged.
- The selected customer, workbench output, evidence path and evidence panel must
  always refer to the same run, request and version. A paired comparison names both
  candidates and its shared conditions rather than merging their evidence.
- Label recorded inspection, fresh trials, experiment and operation in text.
  Show eligibility and Not comparable states before efficiency metrics. Mandatory
  failures cannot disappear behind a collapsed detail or a green summary score.
- Keep initial prediction and later reflection distinct. Use short inputs and
  optional details; no prefilled diagnosis, repair winner or automatic selection.
- Animation may trace the evidence path after a run, but reduced-motion mode must
  show the final state without animation. Animation cannot imply success before
  finalization.
- No XP, coins, badges, skill tree, cosmetic shop upgrades, free-roam objective,
  health bar or competence meter.

## State changes across the journey

1. **Shift board:** centre the inherited service, open incident, unresolved limits
   and operating version. Explain experiment, choose and operate as separate actions.
2. **Requirements:** the owner desk shows the shared obligations, learner priorities
   and a visible test. A weaker contract cannot manufacture a winning repair.
3. **Investigate:** show the complete request-to-consequence evidence path. Ask for
   a cause and disconfirming test before revealing optional diagnostic help.
4. **Compare and choose:** the repair bench shows two code candidates, comparable
   trials, repetition/variation, correctness eligibility and cost/completion tradeoffs.
   Explicit selection is distinct from running, saving and ending a shift.
5. **Next shift:** restore the selected version and original reasoning, with prior
   incidents and limits. Keep future requests hidden before operation. After the
   changed condition occurs, separate its operational consequences from a later
   experiment against the retained alternative; that experiment cannot rewrite history.
6. **Later boards:** preserve the spatial grammar but make each board a different
   kind of work. The revenue floor opens on a mis-routed, dropped or duplicated
   record and its full decision trace; the Northline deployment workshop opens on
   conflicting requirements and a pilot rollout. Do not reskin bookshop shelves and
   rename the labels; each board keeps one persistent history and offers less
   assistance than the one before (three assists and one optional patch proposal on
   Board 1, two assists without patch proposals on Board 2, a single hint on
   Board 3).

## Responsive and accessibility acceptance

- At 1280 px, show the full isometric room and a persistent evidence panel similar
  to the reference composition.
- At 640 px and 390 px, keep a readable room overview, then stack the selected
  station and evidence panel. Do not require precise pointer targeting, drag-only
  navigation or horizontal page scrolling.
- Every station has a matching focusable control and visible focus state. Hotspots
  alone are insufficient.
- Do not encode status using colour alone. Incident, selected, sealed and synthetic
  states need text labels.
- Background art has empty, loading, error and no-incident treatments. It must not
  display stale sample values while real data is unavailable.

## Product comprehension acceptance

A viewer should identify the learner's board and current activity within five
seconds. After walking the storyboard, they should explain without coaching:

1. why a supported fact can still fail to answer the customer's question;
2. how the learner's prediction affects the experiment;
3. which comparison conditions are shared and which repair tradeoff is accepted;
4. why experiments do not change operational history;
5. which exact version was explicitly chosen and will return;
6. why consequences are independently checked, synthetic and recorded; and
7. why a later alternative experiment cannot erase what the chosen version did; and
8. why the three boards are different kinds of engineering work, not three skins of
   one board.

These are proposed comprehension criteria, not observed human results. Gate 1
mockups label all evidence as illustrative; future runtime views must use captured
evidence. An attractive room alone does not satisfy these requirements.
