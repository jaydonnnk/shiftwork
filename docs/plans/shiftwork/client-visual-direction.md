# Client visual direction: operational diorama

**Selected by the user:** 2026-09-18.

**Purpose:** implementation acceptance brief for Slices 9 through 11. This
direction changes the client composition, not the approved learner journey,
authority boundaries, evidence rules or slice order. It does not authorize client
implementation before Slice 9.

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
  scene. Adding a framework, rendering engine or package requires a Gate 3
  backtrack and explicit re-approval before Slice 9.

## Product intent

The bookshop becomes one persistent operational room. The room is the workplace of
the learner, who is cast explicitly as a junior applied AI engineer on shift, and the
business reads as a fictional client rather than the learner's own shop. The role is
fiction, never a credential or job-readiness claim. The learner selects stations
rather than opening unrelated dashboard cards. The room must make this chain legible:

`customer request -> learner service output -> independent comparison -> synthetic ledger consequence -> repair`

The room is not an open-world game. Movement, characters and environmental detail
must never hide the learner-owned artifact or replace recorded evidence with
narrative animation.

## Station map

| Station | Product responsibility | Required state |
| --- | --- | --- |
| Owner desk | Contract choices, declared limits and visible check authoring | Shows committed versus draft state; nothing preselected |
| Service workbench | Learner-owned files, version, contract, visible checks and change log | Central visual focus; exact version and ownership visible |
| Customer queue | Current executed request batch | Selected customer maps to the exact executed request ordinal |
| Evidence pipeline | Output to public comparison to ledger derivation | Every step resolves to real evidence; no invented connector |
| Independent evaluator booth | Separation of learner work from scoring | Visually locked and non-editable; never reveals sealed values |
| Incident and ledger wall | Open incidents and synthetic scenario consequences | Shows reason code, incident state and explicit `Synthetic scenario` label |
| Repair bench | Evidence inspection, repair direction, artifact edit and rerun | Becomes active only for an actual incident |

Slice 12 may add an assist terminal, but it must remain visibly separate from the
evaluator and must show role, attribution and remaining shared assist budget.

## Interaction rules

- The top journey navigation remains available: Shift board, Contract, Customer
  shift, Repair, Return and Away shift.
- Selecting a journey step activates the matching station while keeping the same
  room visible. Selecting a station updates the evidence or work panel.
- Essential labels, controls and values are HTML overlays, not baked into the room
  artwork. They must be selectable, keyboard reachable and exposed to assistive
  technology.
- The right evidence panel is the authoritative detail view. It shows the current
  request, exact service output, supporting public record when permitted,
  independent result, synthetic ledger consequence and attempts remaining.
- The selected customer, workbench output, evidence path and evidence panel must
  always refer to the same run and request ordinal.
- Animation may trace the evidence path after a run, but reduced-motion mode must
  show the final state without animation. Animation cannot imply success before
  finalization.
- No XP, coins, badges, skill tree, cosmetic shop upgrades, free-roam objective,
  health bar or competence meter.

## State changes across the journey

1. **Shift board:** the room is calm. The service workbench is central and displays
   the current artifact, open incidents, unresolved limits and attempts remaining.
2. **Contract:** the owner desk becomes active. Contract choices and the visible
   check builder appear as editable HTML beside the room.
3. **Customer shift:** customer requests enter the service workbench. The selected
   request illuminates the evidence pipeline into the evaluator and ledger wall.
4. **Repair:** the actual incident activates the incident wall and repair bench.
   The mismatch and repair controls remain tied to the selected evidence.
5. **Return:** the same Bellwether room and service workbench return with the new
   artifact version, prior incident history and unresolved limits. The next case
   remains visually sealed until execution.
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

## Slice 11 acceptance test

By the end of Slice 11, a viewer should understand within five seconds:

1. this is the learner's service;
2. a customer request entered it;
3. its recorded output caused the shown result;
4. a separate evaluator produced the check result;
5. the consequence is synthetic and recorded; and
6. the same service and history return in the next shift.

If the room is attractive but any of those statements depends on explanatory prose
outside the product, the visual direction has not landed.
