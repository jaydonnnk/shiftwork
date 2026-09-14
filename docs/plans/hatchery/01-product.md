# Product: Hatchery

**Gate state:** In progress for review. Nothing in this document is an approval,
a measured result or a production capability.

## Problem

> "My children's activities arrive as scattered notices, changes and exceptions.
> I have to keep the calendar and everything they need in sync, and I keep checking
> work I already corrected once. I want help that prepares something useful first,
> remembers the way our household handles recurring situations, and never quietly
> takes responsibility I did not give it."

The proposed first user is a parent managing several recurring extracurricular
activities. The product must connect two responsibilities that are easy to separate
incorrectly: keep commitments correct and keep preparation ready. A changed event
can affect supplies and deadlines; cancelling one child's event must not remove an
item another child still needs.

Family activities are the first responsibility set, not Hatchery's full identity.
The audience remains a hypothesis until real workflow evidence shows frequent
procedural failures, repeat use and less total work for parents.

## Success metric

**Proposed primary target, not achieved:** at least **20% lower median total weekly
handling time** for the same recurring-activity workload, compared with each
household's existing method.

Total time includes setup, reviewing drafts, teaching, checking, clarifying and
recovering from mistakes—not only time spent entering events. Record incorrect or
unauthorized outcomes and useful completion alongside the time result so silence,
abstention or hidden cleanup cannot count as success. The study shape and sufficient
sample size remain open; this threshold alone would be directional evidence, not
proof of market demand or an Impact score.

## Product decisions proposed at Gate 1

- The first useful moment is a linked draft commitment and preparation list. The
  parent does not have to train the apprentice before receiving value.
- A factual change updates the current plan. It does not by itself trigger practice
  or a new procedure.
- A necessary correction to reusable behaviour can create a bounded practice task.
  The parent can inspect the lesson, the miniature cases and what remains uncertain.
- The emotional payoff is: **"I corrected this once, and it handled the next unseen
  case correctly."** The eventual product must prove that outcome; the mockups only
  storyboard it.
- Passing practice never grants real responsibility. Reading, drafting and changing
  real tools are separate, understandable choices that can be revoked.
- The workshop is evidence and explanation, not a pet-care chore, game score or
  developer console. Routine work stays on the week view; deeper inspection is optional.
- Shared product defects should be fixed once for everyone. Personal practice is for
  household-specific or responsibility-specific procedures that earn their place
  against a strong fixed approach.

## Announcement — the blog post before the feature

**Aspirational launch copy; capabilities are not yet built or demonstrated.**

Meet Hatchery, a personal AI apprentice for the recurring responsibilities that
keep everyday life moving. Forward an activity notice and Hatchery prepares a
linked calendar draft and ready-list before asking you to teach it anything. When
you correct a reusable mistake, Hatchery rehearses that lesson in a miniature week
and shows what passed, what failed and what it still cannot safely decide. You stay
in control of what it may read, draft or change—and a successful rehearsal never
expands those permissions.

## Screen journey

1. **Useful draft:** a parent opens a synthetic activity notice and immediately sees
   a linked commitment and preparation draft, with uncertainty exposed.
2. **Correct once:** the parent corrects a procedural mistake; the screen distinguishes
   that lesson from an ordinary factual update.
3. **Workshop:** the correction becomes a bounded practice plan in miniature worlds;
   no result is implied before independent checks exist.
4. **Later case:** an explicitly simulated storyboard shows the memorable transfer
   moment and the remaining uncertainty the apprentice still surfaces.
5. **Responsibility controls:** the parent chooses separate read, draft and change
   boundaries and can revoke them without affecting practice history.

## Screens

- [`mockups/01-week-draft.html`](mockups/01-week-draft.html) — linked commitment
  and preparation drafts from a clearly synthetic notice.
- [`mockups/02-correct-once.html`](mockups/02-correct-once.html) — a necessary
  procedural correction, contrasted with a factual update.
- [`mockups/03-workshop.html`](mockups/03-workshop.html) — the visible miniature
  practice world, queued cases, independent-check boundary and open limits.
- [`mockups/04-later-case.html`](mockups/04-later-case.html) — the illustrative,
  unmeasured "next unseen case" moment.
- [`mockups/05-responsibility-controls.html`](mockups/05-responsibility-controls.html)
  — selected responsibilities, revocable permissions and remaining uncertainty.

## Unresolved product decisions

1. Do extracurricular-activity households experience enough repeated procedural
   mistakes to justify practice, or are most failures simple data entry that a
   strong fixed product already handles?
2. Is the workshop reassuring and legible when optional, or does it make a busy
   parent feel responsible for maintaining another dependent?
3. Which first real responsibility boundary feels both useful and safe: drafts only,
   selected low-risk changes, or a mixed default by action type?
4. What evidence should be understandable on the ordinary week view before a parent
   needs to open the workshop?
5. How should a parent recognize that a correction is household-specific rather
   than a shared product defect?

The separate hackathon-dependence conflict remains unresolved in the supporting
brief. Gate 1 does not silently waive or resolve it.
