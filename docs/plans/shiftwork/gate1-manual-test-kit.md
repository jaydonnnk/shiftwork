# Gate 1 Manual Test Kit — Shiftwork

**Status:** prepared 2026-09-15. No test has run. This is formative evidence, not
statistical proof, and it is not a measurement of the 20-point north star (that
needs a sufficiently powered study, decided at Gate 3).

## Purpose and limits

Gate 1 asks whether the product definition on the six screens is understandable
and whether its decisions feel like real judgement. Use five people with basic
coding knowledge if possible. Run these personally; Gate 1 authorizes no external
outreach. Passing this kit must never be presented as learning, employer or
commercial evidence.

Watch items from the 2026-09-15 review:

- Decision authenticity is the weakest point: check whether the stance and repair
  choices read as genuine tradeoffs or as quiz answers.
- Away-shift validity needs a practitioner: judge whether the bike question
  families require new reasoning rather than renamed bookshop data.

## Setup

- Open `mockups/01-shift-board.html` in a browser; the six screens are plain HTML
  with no scripts. A local static server works too.
- One participant at a time, roughly 20–30 minutes each.
- Do not explain the product. Read each task exactly as written; use neutral
  prompts only ("keep going", "what makes you say that"). Record confusion without
  correcting it.
- Record verbatim quotes; do not paraphrase into pass language.
- After the run, record the verdict in `00-status.md`.

## Tests, tasks and pass conditions

### 1. Product comprehension

- Task: show only the shift board for 10 seconds. Ask: "What is this product, what
  are you responsible for, and why return?"
- Pass: at least 4/5 independently describe maintaining the same AI system across
  later shifts. Fail if they call it a generic course, chatbot or business game.

### 2. Complete learner journey

- Task: without coaching, define correctness, enter the customer shift, diagnose
  the stale-stock incident, choose a repair, find what persists, then locate the
  away shift.
- Pass: at least 4/5 complete the path and correctly explain each transition.

### 3. Decision authenticity

- Task: ask which decisions required real judgement and which felt like obvious
  quiz answers.
- Pass: learners identify at least two genuine tradeoffs. (The 2026-09-15 revision
  removed the preselected contract and strawman repairs; re-check this.)

### 4. Authority and evidence

- Task: ask who controls requirements, repairs, assistance, sealed tests and
  outcomes. Ask which displayed results are real.
- Pass: everyone understands that the learner owns important decisions, the
  evaluator owns results, and all current outcomes are storyboards. Any systematic
  confusion blocks approval.

### 5. Persistence versus transfer

- Task: ask participants to explain the difference between the inherited bookshop
  shift and the bike-cooperative away shift.
- Pass: at least 4/5 explain: the inherited shift tests whether a correction
  survives; the away shift tests whether judgement transfers.

### 6. Motivation

- Task: after the journey, ask whether they would voluntarily start another shift
  without badges, employer credentials or prizes. Ask why.
- Pass: at least 3/5 want to continue because of responsibility and consequences,
  not cosmetic progression.

### 7. Away-shift validity

- Task: have an applied-AI practitioner or educator compare the bookshop and bike
  tasks.
- Pass: they identify genuinely new reasoning or tradeoffs. Fail if the bike
  cooperative is merely renamed bookshop data.

### 8. Accessibility sanity

- Task: keyboard-only navigation, 200% zoom and a roughly 390px-wide window.
- Pass: logical focus order, visible focus, readable content, usable actions and no
  horizontal scrolling.

## Recording sheet

Copy one block per participant.

### Participant ___ — date ___ — coding background ___

| Test | Result (pass / partial / fail) | Verbatim notes |
| --- | --- | --- |
| 1 Product comprehension | | |
| 2 Complete learner journey | | |
| 3 Decision authenticity | | |
| 4 Authority and evidence | | |
| 5 Persistence versus transfer | | |
| 6 Motivation | | |
| 7 Away-shift validity | | |
| 8 Accessibility sanity | | |

## Decision rule

- Apply each pass condition exactly as written; do not average away a failed one.
- Any systematic confusion about authority or evidence (test 4) blocks approval.
- Failures in tests 1–3 or 7 mean the product definition needs revision, not a
  scheduling workaround.
- Record the aggregate verdict in `00-status.md`, then ask: "Approve Gate 1, or
  what should change?"
- This kit never produces a learning or impact claim; the 20-point north star
  requires a sufficiently powered study (feasibility decided at Gate 3).
