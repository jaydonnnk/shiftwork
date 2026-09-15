# Product: Shiftwork

**Gate state:** In progress for review. Nothing in this document is an approval,
measured result or production capability.

## Problem

> "I can follow an AI tutorial and produce a demo, but I do not know whether I can
> keep a real system dependable when its information, users and expectations change.
> I want work that continues across sessions, makes me own the important decisions,
> and shows whether one correction actually prevents the next mistake."

The proposed first learner has basic coding knowledge and wants applied-AI experience,
not another sequence of disconnected lessons. Their work should persist long enough
to accumulate decisions, incidents and consequences. The first responsibility is
maintaining a customer-information service for one fictional bookshop.

Career exploration supplies the setting. Employer proof is not part of the first
product promise. The first question is whether persistent responsibility improves
learning and motivation compared with a strong ordinary tutorial.

## Success metric

**Retained north star, not a claim:** at least a **20 percentage-point increase
in independently completed transfer tasks** against a matched static tutorial,
without increasing the median time or hint budget.

No impact claim will be made unless a sufficiently powered study is run. The
required sample size and the study's feasibility are decided at Gate 3, and the
comparison remains a proof slice after Gate 4. The transfer task uses a new
fictional business with new information and policies. Record which important
decisions and repairs the learner made, whether generated patches caused success,
and whether the learner voluntarily wants another engagement.

## Product decisions proposed at Gate 1

- The primary job is applied-AI-engineering education for people with basic coding
  knowledge. Career exploration is context; employer validation is excluded.
- The first engagement is one bookshop. The learner defines what the service must
  never get wrong, what uncertainty looks like and when it should decline an answer.
- The learner's work persists across shifts. Later work inherits the same system,
  decisions, incidents, unresolved limitations and transparent business state.
- Customer outcomes must follow from what the learner's system actually did. The
  product may explain a consequence, but it cannot invent one independently.
- A correction becomes meaningful only when it prevents a related unseen failure.
- The learner owns requirements, tradeoffs, examples and repair direction. Optional
  AI assistance is visible, bounded and attributable; it must not silently finish
  the important work.
- Correctness stances and repairs are chosen from genuinely competing directions
  with visible tradeoffs; nothing is preselected and no option is presented as the
  obvious quiz answer.
- Progress is shown through working service history, incidents resolved and limits
  understood—not XP, pets, cosmetic building upgrades or a competence meter.
- Orders, refunds, backlog and shop state are explicitly fictional scenario outcomes.
  They are not presented as real revenue, trust or employer proof.
- The first transfer case moves to a bike cooperative with less assistance and
  question families the bookshop did not have—estimated commitments, safety
  refusals, context-dependent compatibility. It tests whether the learner
  re-derives judgement rather than replays bookshop-specific answers.

## Announcement — the blog post before the feature

**Aspirational launch copy; these capabilities are not built or demonstrated.**

Meet Shiftwork, an applied-AI learning world where your work does not disappear when
the lesson ends. Take responsibility for one bookshop service, decide what it must
get right, and watch real customer requests expose the consequences of your choices.
Fix an incident once, then return for a later shift that inherits your system,
decisions and unresolved problems. When you are ready, take an away shift in a new
business with less help and find out what you can actually transfer.

## Screen journey

1. **Shift board:** choose the single active bookshop responsibility and see the
   persistent records that will survive later shifts.
2. **Owner brief:** commit one correctness stance from competing options with
   visible tradeoffs; define evidence, uncertainty and refusal boundaries before
   touching the system.
3. **Customer shift:** watch illustrative customer requests reach the learner's
   service and see the proposed observable outcomes.
4. **Incident review:** inspect one failure, choose among competing repair
   directions and see exactly how much assistance was used.
5. **Inherited shift:** return to the same system and face an unseen related case;
   the screen distinguishes intended causality from unmeasured storyboard claims.
6. **Away shift:** attempt a fresh business whose question families differ in kind
   from the bookshop's, with less assistance, and compare the promised evidence
   against a matched ordinary tutorial.

## Screens

- [`mockups/01-shift-board.html`](mockups/01-shift-board.html) — the active bookshop
  responsibility and persistent records.
- [`mockups/02-owner-brief.html`](mockups/02-owner-brief.html) — competing
  correctness stances with visible tradeoffs, committed by the learner.
- [`mockups/03-customer-shift.html`](mockups/03-customer-shift.html) — illustrative
  customer requests, service outputs and transparent consequences.
- [`mockups/04-incident-review.html`](mockups/04-incident-review.html) — evidence,
  competing repair directions and bounded assistance.
- [`mockups/05-inherited-shift.html`](mockups/05-inherited-shift.html) — the later
  unseen case and inherited work.
- [`mockups/06-away-shift.html`](mockups/06-away-shift.html) — reduced-assistance
  transfer with question families that differ in kind, and an honest evidence state.

## Unresolved product decisions

1. Do target learners want continuing responsibility, or does persistence feel like
   maintenance overhead added to a normal lab?
2. Which bookshop decisions are important enough to belong to the learner without
   turning the product into an expert-only developer console?
3. What amount of optional assistance preserves momentum without destroying authorship?
4. Can fictional business consequences feel meaningful while remaining visibly synthetic?
5. Is a 20-point transfer target both ambitious and measurable with the participants
   available before the deadline?
6. Does the away shift test transferable judgement or merely repeat the same pattern
   with renamed data?
7. Is the bookshop strong enough to make learners voluntarily return for another shift?

Track selection, technical architecture, execution environment, model choice,
evaluation isolation and external services remain Gate 2 and Gate 3 decisions.
