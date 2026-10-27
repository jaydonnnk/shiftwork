# S49 synthetic contract review, 2026-10-26

Status: DRAFT, UNAPPROVED, UNRUN. S49 remains INCOMPLETE.
This file proposes wording. It changes no approved gate or acceptance record.

## Decision to review

Replace S49's delivery requirement with five explicitly synthetic walkthroughs,
after one separate runner pilot. Use five fresh contexts on the same pinned
Jev decision model and the same separately pinned companion text model.
Vary only the five authored persona instructions in the
[proposed protocol](slice49-synthetic-protocol-2026-10-26.md).

These are constraints assigned to software, not validated models of human
backgrounds. Neither model confidence nor generated prose proves completion.
The companion model authors typed explanations, tests, and code. Attribute that
work to the combined agent system rather than to Jev alone.

The approved [Gate 3 section 10](03-program-design.md#10-learning-and-product-evidence-plan)
requires moderated human comprehension sessions. The approved
[Gate 4 S49](04-slices.md#slice-49-five-short-learner-sessions) requires five
consenting people with basic coding skills, about 20 minutes each, completion,
cause recognition, elapsed time, and one genuine quote each.
No verified human session or permitted quote is supplied here.
The private human protocol and blank observation template remain historical
records. Approval of a new deliverable cannot make that old contract fulfilled.

## First review: exact Gate 3 section 10 addendum

Insert the following immediately after "The service checks above prove software
behavior, not learning." Keep both existing subsections, including the human
formative requirements and transfer comparison, unchanged.

```markdown
### S49 synthetic walkthrough contract, 2026-10-26

Subject to separate Gate 4 S49 approval, the replacement delivery requirement is
five synthetic agent walkthroughs of the hosted guided path following the
[synthetic protocol](slice49-synthetic-protocol-2026-10-26.md).
Until that approval, the current human-session exit contract still governs S49.
After replacement, the original five-person requirement remains historically
unmet. The human formative and transfer plans below remain unrun.
Synthetic runs do not satisfy either human evidence plan.

Run one separately bounded technical pilot before the five counted contexts.
Exclude the pilot from those five records. Hold the pinned Jev decision model,
companion typing model, runner, tasks, settings, build, workload, and starting
application state constant. Use the five authored personas in the protocol.
Separate contexts isolate agent history. They do not isolate server state.

For each run, retain observable task actions, the first saved cause and
falsifier, generated tests and code, assistance, failures, agent wall time,
usage, and externally adjudicated outcomes. Label all records
SYNTHETIC_AGENT_WALKTHROUGH. Preserve missing and contradictory evidence.
Generated comments are model output, never participant quotes.

The revised S49 evidence deliverable requires the pilot record and five actual
run records under the frozen protocol, with every task adjudicated or marked
missing. Retain blocked and unsuccessful outcomes. It does not require five
successful journeys. Missing runs or unauditable actions keep S49 incomplete.
The user separately decides acceptance after reviewing the report.

This exercise may identify automation failures or candidate interface problems.
It establishes no human usability, accessibility, learning gain, demand,
job readiness, background ranking, or model ranking. Human testing is still
required before claiming that learners understand the room.

Protocol approval does not authorize installation, credentials, provider calls,
spend, state resets, hosting changes, recording, publication, or S50 execution.
Resolve protected state, exact aggregate limits, transport retries and provider
fallbacks before any separately authorized pilot or counted run.
```

## Second review: exact Gate 4 amendments

Review these only after the Gate 3 addendum is explicitly approved.
Keep unrelated slice contracts and prior approval notices unchanged.

### Replace dependency-table rows 49 and 50

Replace the two rows in [Gate 4 section 2](04-slices.md#2-proposed-dependency-order)
with exactly:

```markdown
| 49 | Five clearly labelled synthetic agent walkthrough records after a separate runner pilot, with externally verified actions and failures | 48; approved Gate 3 section 10 synthetic contract; separate runner, state, provider, and aggregate-spend authority |
| 50 | A video under three minutes and submission text, filled only from retained evidence | 48; 49 only for any S49 evidence used; separate recorded-run, publication, and submission authority |
```

### Replace the complete S49 entry

```markdown
### Slice 49: five synthetic agent walkthroughs

Branch: none. Evidence only, recorded under `docs/plans/shiftwork/evidence/`.

- **Working result:** after one separately bounded technical pilot, run five
  fresh agent contexts on the hosted guided path using the same pinned Jev
  decision model and companion typing model. Use the five authored personas,
  shared tasks, frozen conditions, and evidence fields in the
  [synthetic protocol](slice49-synthetic-protocol-2026-10-26.md).
  A named external observer adjudicates actual UI actions against authorized
  controller evidence. Record task outcomes, first cause and falsifier, code
  authorship, agent timings, failures, missing evidence, and separate usage.
- **Exit evidence:** retain the pilot and five actual walkthrough records,
  including blocked or unsuccessful runs, plus an aggregate report with actual
  denominators. A runner's done status or an agent's success claim is insufficient.
  Missing runs or unauditable actions keep S49 incomplete. Acceptance remains
  the user's explicit decision.
- **Limits:** label every result SYNTHETIC_AGENT_WALKTHROUGH. No person took
  part as a learner. No human completion time, consent, participant quote,
  usability validation, learning gain, or ranking follows. The superseded
  five-person contract remains historically unmet. Gate 3 section 10's human
  formative and transfer studies remain unrun.
- **Authorization:** separately approve the runner and installation, one pilot,
  protected fresh state, model identities and settings, aggregate agent and
  service limits, spend, evidence capture, and any evidence-preserving reset.
  Approve the five-run action only after pilot review. Include no coach,
  retry, replacement run, deployment, recording, publication, or submission
  unless explicitly named. S46 and S48 allowances remain closed.
```

### Add this paragraph to S50 after its working-result bullet

```markdown
S49 synthetic evidence, if used, must be labelled as synthetic agent testing.
It supplies no human learner result or quote and cannot replace S50's new
actual hosted chain: observed miss, demonstrator explanation, fair comparison,
eligible exact choice, selected operation, and next-shift inheritance.
Omit the coach while S46 remains unaccepted. S49 approval or completion grants
no S50 call, recording, publication, or submission authority.
```

## Cross-references for the coordinator

After each separate approval, apply only that approved wording and record its
date and scope in [00-status.md](00-status.md). The second review includes both
dependency rows, the S49 entry, and the S50 paragraph. Update links that use the
old S49 heading after that heading changes.

Reconcile the current notice and evidence-plan cross-reference in
[SHIFTWORK_PLAN.md](../../SHIFTWORK_PLAN.md#9-evidence-plan-to-revise-at-later-gates).
State that human evidence remains absent. Preserve dated original notices,
[readiness](evidence/slice49-readiness-2026-10-26.md), the
[earlier proposal](evidence/slice49-synthetic-walkthrough-proposal-2026-10-26.md),
and the private human kit. Link the approved replacement rather than rewriting
those records as successful studies.

The [Gate 1 metric](01-product.md#success-metric), Gate 3 transfer rubric and
study-size discussion, and Gate 3 section 11's learning-evidence warning remain
unchanged. This proposal supplies none of their missing human evidence.
No product behavior or architecture change is proposed. Any new product control
needed for state isolation or budgets requires its own applicable gate review.

S50 preparation may continue independently. Its evidence ledger must distinguish
the proposed S49 contract, future synthetic observations, retained live product
evidence, and the still-missing human study. No S49 result exists to cite today.

## Readiness checked now and remaining approvals

Local inspection confirmed branch `shiftwork/slice-50`, HEAD
`097bdbbdd27b9c04e22487503ee785f6edcd492e`, and preserved inherited dirty work.
`/Users/jayd0/Documents/shiftwork-agent-checks` does not exist. No installed
runner, lockfile, connection test, key, credit, or balance was verified.

Public metadata checked 2026-10-26 reports runner 0.8.10 at
`817b09eea6e21aad836b5ed32a613c68e5644a08`. The handoff's 0.8.8 is historical.
See the [protocol source record](slice49-synthetic-protocol-2026-10-26.md#source-and-runner-readiness)
for package integrity and concrete context, retry, identity, and usage gaps.
Public documentation is not a successful compatibility test.

The public host's source declares shared, ephemeral state in
[hosted.py](../../../shiftwork/hosted.py). Fresh browser profiles do not provide
separate stores. No current runtime GET, state check, provider call, reset,
installation, recording, deployment, or Git mutation ran for this preparation.
S48 acceptance and hosted receipts are retained historical evidence, not new
runtime verification here. S46 stays CLOSED INCOMPLETE and UNACCEPTED.

Next approval: review the exact Gate 3 addendum first. Gate 4 amendments require
their own subsequent approval. Neither approval alone permits a pilot.
Before a pilot proposal is executable, resolve the runner/context path, package
pin, protected target/store, safe state preservation, exact aggregate limits,
available credits, unknown Sandbox charges, provider policies, and named observer.
