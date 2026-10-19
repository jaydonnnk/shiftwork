# Product: Shiftwork 3D workplace

Gate 1 APPROVED, 2026-10-19, Asia/Singapore.

The user approved the presented proposal by directing "Srue lets move to gate 2
now". Layout A, the room beside a persistent workbench, is the approved default.
The static mockups are structure references. Approval does not claim final art,
working 3D, performance or learner-study evidence.

## Problem

Proposed learner need, not a participant quote:

> I want to see what is happening in the system I maintain, what I should do next,
> and how my chosen repair changes the next shift, without searching through a
> crowded set of controls and technical records.

Shiftwork has completed S28. Its existing learning loop remains the product:
inspect a failure, state a cause and a falsifier, test, repair, compare, explicitly
choose, operate and inherit the consequences. The proposed change gives that work
a coherent 3D workplace with readable evidence and clear next actions.

The user explicitly selected a 3D workplace as the intended result. That settles
the destination, not the detailed experience or its technical implementation.

## Intended experience

The learner opens one of the existing three role boards and immediately sees
the fictional client, current task, operating version and next valid action.
The room has depth, lighting and distinct work objects. Selecting a station
brings its evidence or work into focus while preserving the room's identity.

Use a stable three-quarter view. A gentle change of focus may explain a selected
station, but every essential action works without camera manipulation or walking.
The learner can work directly through labelled controls. The full task remains
available when the 3D view is unavailable or motion is reduced.

Use a room with a persistent workbench on larger screens. Give the room
enough space to read as a workplace and the workbench enough space to inspect
requests and edit code. Detailed editing may expand the workbench. On narrow
screens, show a compact room overview followed by the current task and workbench.
Selecting a station brings the selected content into reach and moves focus
appropriately. A contextual-panel alternative is included for comparison.

The current hosting disclosure remains visible in its own full-width row. It
must not displace the room into the sidebar. Shared state, sleep and reset limits
remain clear. Lower visual clutter must not hide an evidence limitation.

## What the workplace must explain

1. **Inspect.** Connect the selected request, observed output and independent
   result. Show observations before explanations and keep the failed task visible.
2. **Predict and test.** The learner supplies a cause and a falsifier. Optional
   diagnostic help remains subject to the existing commitment and assistance rules.
3. **Compare.** Keep the two exact candidate versions, shared conditions,
   eligibility, missing evidence and mandatory failures visible. Let the learner
   inspect details without using an aggregate score to choose a winner.
4. **Select.** Make selection a deliberate action with a rationale. Saving,
   freezing, comparing or closing cannot imply a selection. No default winner.
5. **Operate.** Show the selected version in the operating position. Distinguish
   queued work, running work, an incomplete result, a failed action and a completed
   result. Only independently checked operation changes synthetic business history.
6. **Inherit.** The next shift restores the selected version, original rationale,
   retained alternative and unresolved history. A later alternative experiment
   remains visibly separate and cannot overwrite operational consequences.

Motion explains a confirmed transition. A travelling request, a testing candidate
or an updated incident wall must refer to the same request, version and purpose
as the visible record. A running animation is never proof of completion. Reopening
an old record shows it as history and must not look like a new execution.

## Three distinct rooms

- **Bellwether Books, Applied AI Engineer.** Keep the service room, books and
  customer work. Make the customer queue, service workstation, test bench,
  independent assessment and incident wall distinct. Establish this complete
  journey first, including the later retained-alternative experiment.
- **Stonebridge Software, Go-To-Market Engineer.** Use a revenue-team workplace
  with signal intake, qualification rules, workflow bench and a pipeline wall.
  Recorded owner assignments, SLA clocks and escalations explain the consequences.
  No visual implies a real customer message or real revenue.
- **Northline Bike Cooperative, Forward Deployed Engineer.** Keep the co-op
  workshop, with booking intake, permission boundaries, integration work,
  acceptance, pilot rollout and handover. A tidy scene cannot imply acceptance
  passed. Bookings, rollout and handover reflect the recorded checks and decisions.

Retain Shiftwork's client identities and navy/amber direction. Use original room
art and objects suited to these jobs. The reference project's useful patterns
are spatial continuity, selective panels and clear stages. Its robot, factory,
procurement and payment loop are not the product being proposed here.

## Success metric and acceptance targets

All numbers below are proposed targets, not observed results. No study has run.

Primary formative target: at least **4 of 5 first-time reviewers** answer all five
questions correctly within **60 seconds per reviewed state**, without coaching:

1. Which role and fictional client am I working for?
2. What happened, or what is the current task?
3. What is my next valid action?
4. Which exact version is selected, or is none selected?
5. Am I viewing an experiment, operation or historical evidence?

Use both the entry state and a later consequence state. Record answers and time
per person and per state. A timeout or incorrect answer fails that state. Five
people provide formative comprehension feedback only, not a learning-gain claim.
Outreach and sessions require separate authorization.

Additional acceptance targets:

- At **1280px**, both the room and selected work are readable without a hosting
  notice occupying their intended column.
- At **640px and 390px**, there is no horizontal page scrolling, mandatory
  drag interaction or obscured next action. Selected content is reachable by tap
  and keyboard, including Northline's carried narrow-screen case.
- Every essential action is available through a labelled keyboard control with
  visible focus. Status has text, not colour alone. A scene failure leaves the
  current task and complete work controls usable. Reduced motion shows the same
  evidence and outcomes without travel or camera animations.
- Mandatory failures, comparison validity, evidence mode and selected version
  remain visible in their relevant decisions. An unavailable value stays unknown.
- No experiment changes operational history. No animation marks a result as
  successful before the independently checked result exists.

The broader approved transfer-learning target remains separate and unproved.
Visual polish, reviewer preference and task completion do not establish learning,
job readiness, commercial impact or better model quality.

## Scope and exclusions

In scope: the existing three boards, room composition, station interaction,
evidence hierarchy, current-task guidance, purposeful motion, responsive access,
fallback states and the confirmed desktop notice-placement problem.

Preserve the existing contracts for learner authorship, independent assessment,
protected information, comparable trials, explicit selection, operation,
inheritance, assistant limits, execution modes and budgets. Keep the current
public demo and downloadable build usable throughout an eventual rollout.

Out of scope: new roles or curriculum, an open-world town, avatar progression,
mandatory walking, a mascot, autonomous diagnosis or repair selection, new model
providers, payments, procurement, participant recruitment, production claims and
submission changes. S28's other known limitations are not silently included as
repairs. Any prerequisite outside this presentation scope must return for a
specific scope decision.

Do not extend the work into every board before the complete Bellwether journey
is understandable and usable. If the 3D view prevents reading, editing or access
on an intended device, stop expansion and revise the design. A fallback is an
access route; it does not change the intended 3D result into a cosmetic reskin.

## Screens

These are plain HTML storyboards, one file per preview. They are grayscale
structure studies with a static perspective sketch, not final 3D art. All
requests, versions, results and consequences are explicitly illustrative. No
screen runs, saves, selects, calls a model or changes an operating system.

- [Review hub](mockups/00-review.html): scope, layout options and preview links.
- [Bellwether room](mockups/01-bellwether-room.html): recommended persistent
  workbench layout, current objective and entry state.
- [Investigate](mockups/02-investigate.html): failed task, evidence, learner cause
  and falsifier, optional help and diagnostic state distinctions.
- [Compare and choose](mockups/03-compare.html): exact candidates, shared
  conditions, eligibility and a deliberate, unselected operating choice.
- [Operation and next shift](mockups/04-operation-inheritance.html): a separate
  predeclared selected-A illustration, pending/failed/completed distinctions,
  inherited history and the retained alternative's separate experiment.
- [Revenue floor](mockups/05-revenue-floor.html): signal ownership, workflow
  bench and recorded synthetic pipeline consequences.
- [Northline workshop](mockups/06-northline-workshop.html): permission boundaries,
  acceptance, pilot work and handover.
- [Contextual layout alternative](mockups/07-contextual-layout.html): larger
  scene with a contextual panel; useful for orientation, weaker for long editing.

Native inputs and disclosures illustrate interaction only. Navigation to the
selected-A preview does not represent a saved choice on the comparison screen.
All work remains usable through labels outside the scene. The final visual
treatment is reviewed before it becomes implementation scope.

## Announcement

Aspirational copy for this proposed extension, not a release announcement:

Shiftwork puts the system you maintain into a 3D workplace. Inspect a failed
request, explain its cause and test your prediction at the workbench. Compare
repairs and choose the exact version you want to operate. See its independently
checked synthetic consequences in the room, then return to the history and
responsibilities that the next shift inherits. The engineer role is simulated;
your decisions stay yours.

## Questions this gate settles

- Is 3D used to explain the existing engineering work without replacing it?
- Is the persistent-workbench layout the right default, with direct labelled
  access and a compact mobile overview?
- Are the three room identities and the proposed success targets appropriate?

The approved default is the persistent workbench. The alternative remains a
comparison, not a second build direction. Rendering engine,
dependencies, state interfaces, performance budgets and implementation slices are
decisions for later gates.

Gate 2 architecture follows under its own approval boundary.
