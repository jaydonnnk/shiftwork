Three-board scope for Shiftwork
Direction memo approved 2026-09-30. Drafted the same day and revised after a
second-opinion review, a read-only adjudication pass and the user's five
decisions.

0. What this document is
The user directed one scope change to the approved product: three role boards in
one workplace instead of one role with two client engagements. The confirmed
parameters after the 2026-09-30 adjudication:
- each new board ships one complete journey before the October 30 submission,
  and each new board authors one operator-sealed comparison family (at least six
  distinct protected variants), because a comparison without a sealed family
  fails closed and dead-ends the journey before selection;
- the Forward Deployed Engineer board is built first after Slice 21 by upgrading
  the planned Slice 22 in place, now split into S22a (content written, reviewed
  and sealed, with an offline reproduction proof) and S22b (the journey and the
  workplace board selector), with the GTM pack following as three fixed slices
  (S23 to S25);
- the S20 Nemotron chain is a stretch goal with an October 20 drop point, not a
  hard requirement; and
- no feature drops are planned: full delivery is intended, and the S20 October
  20 checkpoint is the only pre-agreed stretch gate.
The 2026-09-30 read-only adjudication pass verified every finding of an
independent second-opinion review against the code and confirmed all of them
(the hidden-case blocker, the slice splits, the gate scoping gaps and the
bookkeeping items), and the user decided the five open questions in this
revision.
This memo was approved by the user on 2026-09-30. It is not Gate 1, 2, 3 or 4
approval, it authorizes no implementation, and no live call, credential, commit
or push follows from it. The gates are reconciled in order: Gate 1 (product
scope and mockups), scoped Gate 2 and Gate 3, then Gate 4 (slices).

1. What changes
One workplace holds three role boards, in this display order:
1. Applied AI Engineer at Bellwether Books. Built. This is the current product.
2. GTM Engineer at a newly authored fictional software employer.
3. Forward Deployed Engineer deployed at the Northline Bike Cooperative, which
   stops being the applied AI engineer's away shift and becomes the FDE board's
   customer deployment.
Each board is one role, one fictional employer or client, one continuing
artifact, one distinct failure class and one set of independently checked
synthetic consequences. The learning loop is shared and unchanged: inspect what
happened, state a cause and a falsifier, test it, edit the artifact, compare two
repairs fairly, select one with a rationale, operate it, inherit the
consequences, and later test the retained alternative without rewriting history.
Fairness means the same thing on every board: each comparison pair draws one
never-exposed protected variant from that board's operator-sealed family, and
both candidates run it in a separate protected phase under the ADR 0006
boundary. Demo determinism comes from the fixed checked-in fixture corpus, not
from the sealed family.
One earlier concern stands: three copies of Bellwether with new labels would miss
the point. Each board's failure and assessment must differ in kind, not
cosmetics.

2. The three boards

| | Board 1: Applied AI Engineer | Board 2: GTM Engineer | Board 3: FDE |
| Role and fiction | Junior applied AI engineer keeping the Bellwether Books service running (existing) | Junior GTM engineer at a fictional B2B software employer ("Stonebridge Software", working name); the client is the revenue team | Junior FDE at the platform vendor, deployed at the Northline Bike Cooperative |
| Learner artifact | The service: request interpretation, tool and data choice, response (existing) | The signal-to-owner workflow: qualification, routing, CRM write logic | The deployment integration: validation, escalation, retry-safe writes |
| Failure to diagnose | Task-relevant wrong or missing answer (existing) | A mis-routed, dropped or duplicated record, with its full decision trace | A duplicated booking, or a safety question auto-answered |
| Fair comparison | Two service policies under one contract (existing) | Rules-first with a review queue versus model-assisted with confidence thresholds and human review | Optimistic auto-confirm with rollback versus conservative validation with manual fallback |
| Comparison family | `task_completion`, operator-sealed (existing) | One new operator-sealed family, at least six variants | One new operator-sealed family, at least six variants |
| Independent checks | Customer task completion and correctness (existing) | Expected owner and qualification per pinned record; no unowned or duplicate records; idempotent reprocessing | Customer acceptance tests: no double bookings, escalation fires, commitments honored, access boundaries held |
| Consequences | Orders and incidents in the shop (existing) | Synthetic pipeline state: owners, SLA clocks, escalations, missed-handoff incidents | Pilot rollout state: bookings, incidents, and rollout and handover decisions |
| Later condition | Inventory or dependency outage (existing) | Enrichment provider outage, or a new region or product line | A schema change or a customer-side outage |
| Assistance rung | 3 assists plus 1 patch proposal (existing) | 2 assists, no patch proposal (new) | 1 hint (existing Northline policy) |

Why the two new roles are credible, in one line each: (GTM) 2025-2026 postings at
Marqeta and Sierra describe exactly these pipelines plus LLM prompt design with
eval loops, and a 0 to 2 year associate posting exists whose first tasks are
enrichment and hygiene automation, troubleshooting and runbooks. (FDE) Palantir,
OpenAI, Anthropic and Scale postings describe embedding with one customer,
scoping ambiguous problems into working software, building integrations and LLM
workflows inside customer systems, evaluation against the customer's success
criteria, and staged rollout; Palantir's new-grad posting confirms junior entry.
Full postings, quotes and sources: references/role-scope-research-2026-09-30.md.

3. What stays the same
- The central mechanism, the room grammar, the evidence discipline, the sealed
  evaluator boundary and the synthetic labelling.
- No real people, no real outreach, no real customers. The GTM board's terminal
  action is a human handoff, never a sent message; synthetic pipeline changes are
  never presented as real revenue.
- The role fiction is not a credential, certification or job-readiness claim.
  Employer proof stays excluded.
- Replacing an unnecessary AI step with ordinary code remains a valid choice.
- No XP, competence meters, pets, marketplaces, multi-agent theatre or extra
  roles beyond these three. Further roles need a new decision.

4. Frontend
A workplace screen holds a board selector above the journey navigation. Each
board opens its own workshop with the same evidence grammar and role-specific
station labels: the Bellwether service room (existing), a GTM revenue floor
(signal intake, qualification rules, workflow bench, pipeline wall), and the
Northline deployment workshop (deployment brief, system map, integration bench,
acceptance, rollout and handover). Each board keeps one persistent history.
Boards unlock as their packs land; all three are expected playable before the
package slice.
Mockups (plain HTML, no framework) to be authored with the Gate 1
reconciliation: 00-workplace (board selector), 06-gtm-floor, and
07-northline-deployment (revised from 06-away-shift). Existing screens 01 to 05
stay Board 1.

5. Evidence depth
Each new board ships one complete journey: brief, investigation, comparison,
selection, operation, consequences, inheritance, later-condition alternative.
Both boards run through the same verified execution path and can be
live-capable. Each new board authors one operator-sealed comparison family (at
least six distinct protected variants, one drawn per pair and shared by both
candidates), so comparison, selection and operation actually qualify instead of
failing closed: the family list is hardcoded to the bookshop and the workload
loader refuses every other engagement today, so a new board dead-ends before
selection without this work. The engine gains per-engagement family registration
as a scoped Gate 2 item. The Bellwether board keeps the deep sealed proof.
Operator review and sealing of both new families precedes use and is part of the
schedule risk below: the single human reviewer is the bottleneck. Every board's
evidence labels stay honest about what was and was not exercised.

6. Gate impact
- Gate 1: S6 scope boundary, the problem framing, the announcement, the success
  metric's transfer wording, the screens table and the visual direction.
- Gate 2, scoped: the engagement pack as a declared concept; the GTM pipeline
  consequence vocabulary; naming where the FDE discovery and rollout records
  live; and the protected comparison stimulus boundary extended per board (the
  ADR 0006 boundary), including per-engagement family registration that replaces
  the hardcoded bookshop family list and the bookshop-only workload loader
  (config.py:199, orchestrator.py:2380-2381). The endpoint part stays small;
  these comparison items are the real work.
- Gate 3, scoped: section 6.9 becomes FDE board ownership; a new GTM pack
  contract (artifact, checks, consequence rules, budgets); a third assistance
  level in the budget table (GTM: two assist calls per shift, no patch
  proposal), because the design and the code model exactly two regimes today
  (Bellwether's three roles versus everyone else's single hint); the clause map
  and the learning-evidence wording, because Northline stops being the
  same-role away shift and the transfer north star is now read across boards.
- Gate 4: the slice restructure below, plus reconciling the two pending
  Nemotron-chain reminders already in the plan.
- Documentation sync, whenever the drafts above land: the four stale one-role
  texts (AGENTS.md section 4 needs the user's sign-off; docs/SHIFTWORK_PLAN.md
  line 307; client-visual-direction.md's Away shift step; the app.js "arrives in
  Slice 11" copy), the S21 exit wording that still defers checks to the Away
  shift, and the two browser test filenames (the plan cites pivot-browser.mjs
  and pivot-render-faults.mjs; the repository holds browser.mjs and
  render_faults.mjs).

7. Slice restructure (fixed after the 2026-09-30 adjudication)

| Slice | Now | Proposed |
| --- | --- | --- |
| 19 | Read-only semantic replay | unchanged |
| 20 | Inheritance and the retained-alternative experiment | unchanged, plus the existing Nemotron-chain reminder; the chain is a stretch goal with an October 20 drop point |
| 21 | Complete the Bellwether room journey | unchanged; Board 1 complete |
| 22a | Northline transfer journey (split) | FDE pack part 1: write, operator-review and seal the FDE material in journey order (deployment brief with conflicting requirements, discovery record, permissions map, acceptance tests, rollout and handover) and the execution fixtures (Northline mission, initial and three paired request files, ordinal manifest, starting state, compatible catalog, blank learner scaffold), author the Northline operator-sealed comparison family, and prove offline that the initial failure reproduces. The workplace selector client work may start during the operator-review window |
| 22b | Northline transfer journey (split) | FDE pack part 2: execute the FDE board journey (six A/B slots, explicit selection, live-capable booking arm, six-station browser journey) plus the workplace board selector and Boards 2 and 3 entry; Board 3 complete |
| 23 | (was optional Tavily curation) | GTM pack part 1: fiction, brief, workload records, contract, expected-decision checks, artifact scaffold, offline comparison proving eligibility and writing nothing to the ledger, operator workload review |
| 24 | (was full-pivot package) | GTM pack part 2: pipeline consequence vocabulary (owners, SLA clocks, escalations, missed-handoff incidents), operate and inherit offline, idempotent reprocessing and no-unowned-or-duplicate checks. The vocabulary is new construction, not reuse, so the split decided 2026-09-30 is fixed, not conditional |
| 25 | | GTM pack part 3: GTM revenue floor room stations, browser journey, live-capable path; Board 2 complete |
| 26 | (was conditional hosting) | was 23: optional Tavily curation |
| 27 | | was 24: full-pivot package and judge evidence, plus the existing reminder |
| 28 | | was 25: conditional hosted demo |

Eleven remaining slices instead of seven (nine in the morning version; the FDE
split adds one and the fixed GTM third slice adds one). Build order: FDE first
(it upgrades the already-planned Slice 22 in place and authors Northline once),
then GTM. Display order stays 1, 2, 3. Slices 19 to 21 are unaffected by this
scope change and can run under their own go-aheads while the gate reconciliation
is drafted.

8. Risks and limits
- The date. Roughly 30 days remain; the review rounds, operator fixture reviews
  and seals (now including two comparison families), and live authorizations are
  the real cost, not the code. No feature drops are planned after the 2026-09-30
  decision; the only pre-agreed checkpoint is the S20 chain's October 20 drop
  point. Plan a feature freeze in the final week for the video, README and
  submission form.
- Content load. Two new boards need credible briefs, workloads, checks,
  consequence rules and one operator-sealed comparison family each. Operator
  review of each board's material precedes use.
- Live cost. A live arm per board multiplies sandbox and inference spend; each
  still needs its own authorization. The one live comparison so far measured
  zero inference calls, so the S20 chain and any new live arm are unmeasured
  spend shapes; the existing estimate does not cover them.
- Engine scope. The protected comparison machinery is bookshop-only today
  (hardcoded family list, bookshop-only workload loader, two assistance
  regimes); the scoped Gate 2 and Gate 3 items above are required for the new
  boards, not optional polish.
- Honest framing. Three boards broaden the practice surface but prove no
  learning improvement. The 20-point transfer comparison remains an unproven
  north star with its construct reconciled in Gate 3.

9. What the approval authorizes
Drafting the reconciling gate revisions only: Gate 1 first (including the three
mockups), then the scoped Gate 2 and Gate 3 revisions, then the Gate 4 slice
revision. The five 2026-09-30 decisions are already incorporated in this
revision. No implementation, install, credential, external call, fixture
authoring, sealing, commit, push, deployment or submission is authorized by this
memo or its approval.

Sources: docs/plans/shiftwork/references/role-scope-research-2026-09-30.md;
docs/plans/shiftwork/00-status.md entry "Three-board scope direction and
revision memo: 2026-09-30".
