# Client visual direction: operational diorama

**Composition selected by the user:** 2026-09-18.
**Journey revision:** RE-APPROVED 2026-09-24 with Gate 1 after the final-pivot
backtrack. The selected room composition is retained; new runtime UI is not delivered.

**Purpose:** visual acceptance brief for the revised product journey. The prior
Slice 9 acceptance remains historical evidence. The new investigation, comparison,
choice and later-experiment requirements are not delivered by that slice and are
not assigned to old Slices 10 or 11 here. Future mapping requires Gate 4 revision.
This brief does not authorize implementation or change the rendering baseline.

## Reference

- [`references/shiftwork-operational-diorama.jpg`](references/shiftwork-operational-diorama.jpg)
  is the composition reference supplied by the user.
- Use its fixed isometric room, station layout, evidence panel and causal path as
  the visual target.
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

The bookshop becomes one persistent operational room. The room is the workplace of
the learner, who is cast explicitly as a junior applied AI engineer on shift, and the
business reads as a fictional client rather than the learner's own shop. The role is
fiction, never a credential or job-readiness claim. The learner selects stations
rather than opening unrelated dashboard cards. The room must make this chain legible:

`request -> interpretation and information/tool use -> output -> independent task and correctness checks -> synthetic operational consequence`

Investigation follows that evidence into a prediction and a controlled repair
comparison. Only an explicit choice changes the operating version; only operation
produces business consequences. The experiment path must not visually flow into the
operational ledger as though every trial changes the shop.

The room is not an open-world game. Movement, characters and environmental detail
must never hide the learner-owned artifact or replace recorded evidence with
narrative animation.

## Station map

| Station | Product responsibility | Required state |
| --- | --- | --- |
| Owner desk | Shared mandatory requirements, learner priorities and visible tests | Distinguishes fixed obligations from learner choices; no repair preselected |
| Service workbench | Learner-owned code, tested candidates and operating version | Shows starter, candidate, explicitly chosen and changed-since-test states separately |
| Customer queue | Executed operational requests | Selected customer maps to the exact executed request and operating version |
| Evidence pipeline | Interpretation, tool use, records, output and independent checks | Shows task relevance as well as factual support; observations separate from hypotheses |
| Independent evaluator booth | Separation of learner work from assessment | Non-editable; no protected answers or model-declared passes |
| Incident and ledger wall | Operational incidents and synthetic consequences | Experiment results never masquerade as incidents resolved or sales completed |
| Repair bench | Prediction, falsifier, learner code, fair experiment and explicit choice | Shows shared conditions, repetition/variation, eligibility, tradeoffs and selected version |

Optional assistance stays visibly separate from the service under investigation
and the evaluator. Show attribution and the applicable shared assistance limit;
diagnostic help follows the learner's initial prediction. Future slice ownership
is deferred to the revised Gate 4.

## Interaction rules

- The top journey navigation remains available: Shift board, Requirements,
  Investigate, Compare and choose, Next shift and Away shift.
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
6. **Away shift:** preserve the spatial grammar but create a genuinely different
   Northline Bike Cooperative workshop. Start with a blank artifact, fewer assist
   affordances and stations for future commitments, safety escalation and
   retry-safe booking. Do not reskin bookshop shelves and rename the labels.

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

A viewer should identify the learner's service and current activity within five
seconds. After walking the six screens, they should explain without coaching:

1. why a supported fact can still fail to answer the customer's question;
2. how the learner's prediction affects the experiment;
3. which comparison conditions are shared and which repair tradeoff is accepted;
4. why experiments do not change operational history;
5. which exact version was explicitly chosen and will return;
6. why consequences are independently checked, synthetic and recorded; and
7. why a later alternative experiment cannot erase what the chosen version did.

These are proposed comprehension criteria, not observed human results. Gate 1
mockups label all evidence as illustrative; future runtime views must use captured
evidence. An attractive room alone does not satisfy these requirements.
