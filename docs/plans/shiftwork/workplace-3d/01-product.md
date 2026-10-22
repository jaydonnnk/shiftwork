# Product: Shiftwork 3D workplace

Gate 1 RE-APPROVED 2026-10-23 after the same-day backtrack for the robot crew and room declutter. The user answered "I re-approve Gates 1 to 4 for the robot crew and declutter. Commit the docs, then start S41 on shiftwork/slice-41."
The user compared the S40 Bellwether room at 100% zoom with the agentic-factory reference, called it "too cluttered", asked for "little robots and nice animation", and approved the backtrack with the role choice "Staff bots + your bot" for all three boards.
The [crew and declutter mockup](mockups/v2/17-robot-crew.html) is the reference for this revision.

Earlier: Gate 1 RE-APPROVED 2026-10-21 after the same-day backtrack. The user answered "Yep i approve, lets move on to gate 3 and gate 4. Then il approve all ar once".

History: Gate 1 was approved on 2026-10-19 when the user directed "Srue lets move to gate 2 now", with layout A, the room beside a persistent workbench, as the default.
On 2026-10-21 the user compared the built result with the agentic-factory reference and approved a backtrack with "Yes i approve the backtrack".
The [visual overhaul proposal](visual-overhaul-proposal-2026-10-21.md) records the analysis behind this revision.
This revision changes the presentation and the guidance, not the learning loop or its evidence rules.
The static mockups are structure and appearance references.
They do not claim final art, working 3D, performance or learner-study evidence.

## Problem

The product owner's words, 2026-10-21:

> I personally feel that our project is a tad bit complicated and technical.
> Yes we have the 3 job scopes, but it's not the level of intuitiveness I want.

Proposed learner need, not a participant quote:

> I want to see what is happening in the system I maintain, what I should do next, and how my chosen repair changes the next shift, without searching through a crowded set of controls and technical records.

The first approved direction placed a small room beside a dense workbench.
In the built result, the first thing a learner reads is a line of version identifiers and record types.
The room is a small, dark picture that rarely changes.
The learner is not told the single question of the shift or where they are in the loop.

Shiftwork's learning loop remains the product: inspect a failure, state a cause and what would prove it wrong, test, repair, compare, explicitly choose, operate and inherit the consequences.
This revision makes that loop the visible story of a living workplace.

## Intended experience

The learner first chooses a shift.
Each client card states one question in plain words, what the shift teaches, and the role.
The seven steps are shown before anything moves: read the complaints, explain the cause, say what would prove you wrong, try two fixes, choose one, run the shift, see what happened.

The workplace then fills the screen.
Small panels float over the room:

- a status bar with the client, shift, live version, open incidents, attempts left and a permanent synthetic-scenario label;
- a step chip showing "Step N of 7" and the current step's name;
- one next-action panel with a single labelled action;
- a shift log holding the detailed record, including identifiers.

Each station in the room is a labelled control with its status in words and a coloured lamp.
At rest the room shows no station tags except the one station that holds the next valid action, and any station that needs attention.
Every other tag appears on hover or keyboard focus, and the full labelled station list stays reachable from the keyboard and in the fallback.
A ring marks the station that holds the next valid action.
Choosing a station opens its work in an inspector panel beside the room, keeping the room in view.
Deliberate decisions, such as choosing the live version, open as a focused dialog that states what is being chosen, why it is being asked, and what happens to the alternative.

The room has a small crew of original, toy-like robots, in the spirit of the agentic-factory reference.

- **Your bot**, tagged "You", stands for the learner.
  It walks to a station only when the learner opens that station, and returns to its home spot when the inspector closes.
  It never moves, types, decides or speaks on its own; every choice, cause, test and repair still comes from the learner's own controls.
- **Staff bots** are the client's people: the owner at the owner desk and customers at the queue.
  The client's people give the room a voice through them.
  Customers' recorded requests appear as speech bubbles above a customer bot.
  The owner bot comments on what the recorded evidence already shows.
  Voices narrate; they never suggest a cause, a fix or a choice.

No bot is presented as an AI system, an assistant or a worker that diagnoses, repairs or chooses; the learner remains the engineer.
Bots idle with a small bob and blink.
Their movement never implies progress, success or a result.
With reduced motion or in the fallback, bots stand still and the same words appear in text.

The room has quiet life that reflects real state: lamps, the attention ring and small ambient movement.
When a run's recorded results arrive, request slips travel from the queue to the service, then to the locked inspector's desk, which stamps each one with its actual verdict, then to the incident wall.
This replay is always labelled as recorded and never runs ahead of a recorded result.
Ambient movement never implies progress, success or a result.

After the run, a shift report shows the before and after for the customers, incidents closed and opened, and the learner's decision, all labelled synthetic.
The next shift opens with the inherited live version, its original reason, the backup version and unresolved incidents.
A later experiment on the backup version is offered separately and cannot rewrite history.

On the main view, the words are plain: live version, backup version, what would prove you wrong.
Identifiers, hashes and record types stay available in the shift log and inspector, never as the first thing a learner reads.

On narrow screens, the status bar, step chip, a compact room, the next action and the log stack vertically.
There is no camera motion, no drag and no horizontal scrolling.
Every essential action works without moving the camera or walking.
The full task stays available when the 3D view is unavailable or motion is reduced.

The current hosting disclosure stays visible in its own full-width row above the workplace.
Shared state, sleep and reset limits remain clear.
Lower visual clutter must not hide an evidence limitation.

## What the workplace must explain

1. **Inspect.** Connect the customer's request, the service's answer and the inspector's independent result. Show observations before explanations and keep the failed task visible.
2. **Predict and test.** The learner writes a cause and what would prove it wrong. Optional diagnostic help unlocks only after both are saved and stays subject to the existing commitment and assistance rules.
3. **Compare.** Keep the two exact candidate versions, shared conditions, eligibility, missing evidence and mandatory failures visible, row by row. No aggregate score picks a winner and no option is visually preferred.
4. **Choose.** Choosing is a deliberate action with a written reason. Saving, freezing, comparing or closing cannot imply a choice. No default winner.
5. **Operate.** The live version sits at the service console. Queued, running, incomplete, failed and completed results look different. Only independently checked operation changes synthetic business history.
6. **Inherit.** The next shift restores the live version, its reason, the backup version and unresolved history. A later experiment on the backup version stays visibly separate and cannot overwrite operational consequences.

Motion follows the record.
A travelling slip, a stamp, a testing candidate or an updated incident wall refers to the same request, version and purpose as the visible record.
A moving slip is never proof of completion, and a stamp shows only the recorded verdict.
Reopening an old record shows it as history and must not look like a new run.

## Three distinct rooms

- **Bellwether Books, Applied AI Engineer.** A bookshop service room with a customer queue, the service console, a test bench, the locked inspector's desk, the owner desk, the incident wall and a handover shelf. Paper slips and stamps carry the story. Establish this complete journey first, including the later backup-version experiment.
- **Stonebridge Software, Go-To-Market Engineer.** A revenue-team workplace with signal intake, qualification rules, a workflow bench and a pipeline wall. Recorded owner assignments, response deadlines and escalations explain the consequences. No visual implies a real customer message or real revenue.
- **Northline Bike Cooperative, Forward Deployed Engineer.** The co-op workshop, with booking intake, permission boundaries, integration work, acceptance, pilot rollout and handover. A tidy scene cannot imply acceptance passed. Bookings, rollout and handover reflect the recorded checks and decisions.

Retain Shiftwork's client identities and the navy and amber direction: warm, light rooms with navy trim and interface, and amber for attention.
Use original room art and objects suited to these jobs.
From the agentic-factory reference, borrow the full-screen world, floating panels, the lesson card, the step guide, narrated speech bubbles, physical status lamps, the detailed log and focused decision dialogs.
Also borrow the feel of its robot: a small, friendly figure that walks to where the work is, bobs and blinks, and anchors one speech bubble.
Build the robots as original geometry; the reference repository publishes no licence, so do not copy its robot code, model, artwork or any other source.
Do not borrow its factory, conveyor, procurement or payment loop.

## Success metric and acceptance targets

All numbers below are proposed targets, not observed results.
No study has run.

Primary formative target: at least **4 of 5 first-time reviewers** answer all five questions correctly within **60 seconds per reviewed state**, without coaching:

1. Which role and fictional client am I working for?
2. What happened, or what is the current task?
3. What is my next valid action?
4. Which exact version is live, or is none chosen?
5. Am I viewing an experiment, an operation or historical evidence?

Use the entry state, a mid-loop decision state and a later consequence state.
Record answers and time per person and per state.
A timeout or incorrect answer fails that state.
Five people provide formative comprehension feedback only, not a learning-gain claim.
Outreach and sessions require separate authorization.

Additional acceptance targets:

- The main view of any state shows at most one question, one next action and one narrator line, and no hash or internal identifier.
- At rest, at 1280px and at 100% browser zoom, at most two station tags and one speech bubble are visible over the room, and no floating panel other than the status bar, the next action and the collapsed shift log covers it.
- Every bot movement is caused by the learner's own station choice or by a recorded state change; no bot moves to a station the learner did not open.
- At **1280px**, the room fills the area under the hosting row, and an open inspector leaves the room's stations readable.
- At **640px and 390px**, there is no horizontal page scrolling, mandatory drag interaction or obscured next action. Selected content is reachable by tap and keyboard, including Northline's carried narrow-screen case.
- Every essential action is available through a labelled keyboard control with visible focus. Status has text, not colour alone. A scene failure leaves the current task and complete work controls usable. Reduced motion shows the same evidence and outcomes without travel, ambient movement or camera animation.
- Mandatory failures, comparison validity, evidence mode and the live version remain visible in their relevant decisions. An unavailable value stays unknown.
- No experiment changes operational history. No animation, stamp or report marks a result as successful before the independently checked result exists.

The broader approved transfer-learning target remains separate and unproved.
Visual polish, reviewer preference and task completion do not establish learning, job readiness, commercial impact or better model quality.

## Scope and exclusions

In scope: the existing three boards, the shift picker, the full-screen room, floating status, step guidance, station interaction and status, the inspector panel, decision dialogs, narrated voices, the robot crew, room declutter, recorded replays, the shift report, plain-language naming, responsive access, fallback states and hosting-notice placement.

Preserve the existing contracts for learner authorship, independent assessment, protected information, comparable trials, explicit selection, operation, inheritance, assistant limits, execution modes and budgets.
Keep the current public demo and downloadable build usable throughout an eventual rollout.

Out of scope: new roles or curriculum, an open-world town, avatar progression or customisation, mandatory walking, free player-controlled movement, a mascot that rewards or scores, any bot presented as an AI worker, autonomous diagnosis or repair selection, new model providers, payments, procurement, participant recruitment, production claims and submission changes.
S28's other known limitations are not silently included as repairs.
Any prerequisite outside this presentation scope must return for a specific scope decision.

Complete the Bellwether journey before extending the treatment to Northline and Stonebridge.
If the full-screen room prevents reading, editing or access on an intended device, stop expansion and revise the design.
A fallback is an access route; it does not turn the intended result into a cosmetic reskin.

Timing context: the hackathon submission period closes on 2026-10-30 at 10:00 AM Pacific Time.
A later gate decides which parts can land before then; this gate does not promise a date.

## Screens

Plain HTML storyboards, one file per screen, in [mockups/v2](mockups/v2/index.html).
All requests, versions, results and consequences are illustrative.
The room picture is the existing original Shiftwork room art standing in for the real 3D room.
No screen runs, saves, chooses, calls a model or changes an operating system.
Each screen reflows for narrow widths.

- [Review hub](mockups/v2/index.html): screen list and what changed.
- [Choose a shift](mockups/v2/10-shift-picker.html): one question per client, what it teaches, the seven steps.
- [Bellwether shift opens](mockups/v2/11-bellwether-shift.html): full-screen room, status bar, step chip, station lamps, attention ring, voices and shift log.
- [Investigate a complaint](mockups/v2/12-investigate.html): request slip, the service's answer, the inspector's checks, the learner's cause and what would prove it wrong.
- [Compare and choose](mockups/v2/13-compare-choose.html): two candidates on shared requests, no score and no default, a choice dialog that needs a reason.
- [Run the shift](mockups/v2/14-run-replay.html): labelled recorded replay with stamps from actual verdicts.
- [Shift report](mockups/v2/15-shift-report.html): synthetic before and after, incidents and the learner's decision.
- [Next shift](mockups/v2/16-next-shift.html): inherited state, read-only history and a separate optional experiment.
- [Robot crew and declutter](mockups/v2/17-robot-crew.html), added 2026-10-23: the room at rest with one tag, your bot walking to an opened station, the owner and customer bots speaking, and the before-and-after tag count.

The 2026-10-19 [structure mockups](mockups/00-review.html) remain as history.
Their Stonebridge and Northline room contents still describe those rooms until the Bellwether journey is complete.

## Announcement

Aspirational copy for this proposed extension, not a release announcement:

Shiftwork puts you on shift in a living workplace.
Pick a client, read what their customers asked and what the AI service actually said, and write down why you think it failed and what would prove you wrong.
Test two fixes the same way, then choose the one that goes live, in your own words.
Watch the recorded results come in, see what your choice did for the customers, and pick up the next shift where you left it.
The clients are fictional and the role is simulated; your decisions stay yours.

## Questions this gate settles

- Is a full-screen workplace with floating panels and an inspector the right default, replacing the persistent workbench?
- Do the shift card, seven-step guide, plain naming and narrated voices make the next action obvious without hiding evidence?
- Are labelled recorded replays, station lamps and ambient room life acceptable within the honesty rules above?
- Are the three room identities, the Bellwether-first order and the proposed success targets still right?
- Does the robot crew, with your bot moving only on your own station choice and staff bots narrating only, add life without implying that a bot does the engineering?
- Does hiding resting tags make the room calmer without hiding a station from keyboard or fallback users?

Rendering engine, dependencies, state interfaces, motion timings, performance budgets and implementation slices are decisions for later gates.
After re-approval, Gate 2 and Gate 3 are checked against this revision and any affected decision returns for approval before Gate 4 planning.
