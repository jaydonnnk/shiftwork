# S45 revised live comparison, 2026-10-24

Publication update, 2026-10-25: the accepted S45 code, tests and named public
evidence were pushed to origin/shiftwork/slice-45 at b7babdd572978e4b1a91ca6ea74a56587211f92d.
This report and the public comparison/selection packages are now deliberately
tracked. Earlier uncommitted/ignored-only statements below describe their
pre-publication checkpoints. Private databases and restricted captures remain
local. See [the publication record](../slice45-publication-2026-10-25.md).
No merge to main, deployment or additional live action is implied.

S45 is COMPLETE and ACCEPTED. After reviewing this result, the user explicitly
said "Select B and accept S45". Choice sel-0002 now selects the exact tested B,
ver-0004, with artifact hash
a71808a838c2df4cfa62883ea992d50bb942ab29beb0f6821162ccc9fbf41667.
A is retained as ver-0003. Selection added only its own row, preserved every
pre-existing database row and the operational ledger, and made zero additional
provider calls or Sandbox operations. The source examples and investigation
remain operator-authored demo activity, not learner work or learning evidence.

The one approved action completed with outcome COMPLETE. All nine planned public
batches per candidate and all protected phases are retained. B is eligible;
A is ineligible. The comparison itself caused no choice or operational ledger
change; the separate explicit user choice above followed it. S45 is uncommitted.

## Authority and exact action

The user said: "Sure lets do the live testing to get the live proof and finish
this slice" in response to the exact revised pair and one bounded comparison.
The [approved proposal](../slice45-revised-comparison-proposal-2026-10-24.md)
permits 42 model calls, 24 Sandbox operations and US$0.09289728 reserved inference
within the existing US$5 inference ceiling. Deadlines and protected rules stay
unchanged. Preparation and freeze are included; no automatic choice is permitted.

The action is /tmp/shiftwork-s45-revised-live-20261024/. It has its own store,
one-shot marker, source/runtime freeze and receipts. The earlier two stopped
stores remain byte-identical. IDs repeat across these stores and must not be
used to merge their histories.

- A is the revised prompt repair, template-authored ver-0003. Source SHA-256:
  3f0e1ce4bb030e455d86abd42c8d178f82eb4a3826c42705536891c162892354.
- B is revised schema guidance plus structural validation, template-authored
  ver-0004. Source SHA-256:
  7d08d2833130cf3f6de155d3ecd925e9d1e7bff0d670d3b936b91ad4fdee628f.

Both exact sources retain reasoning off, the approved Nano model, one user
message, one call per customer request, no retry, 8 KiB input, 1,024 output
tokens, the 20-second gateway deadline and 45-second workspace deadline.
Both are operator-authored examples, not learner work or learning evidence.
The investigation is operator-performed retained S44 RECORDED_INSPECTION and
adds no call. No source byte changed during execution.

## Actual results

| Measure | A | B |
| --- | ---: | ---: |
| Public batches passing every mandatory check | 7 of 9 | 9 of 9 |
| Public batches retained | 9 of 9 | 9 of 9 |
| Public customer responses retained | 18 of 18 | 18 of 18 |
| Useful completions | 10 of 18 | 12 of 18 |
| Justified refusals | 6 of 18 | 6 of 18 |
| Invalid public response envelopes | 2 | 0 |
| Protected phases passing | 3 of 3 | 3 of 3 |
| Missing protected evidence | 0 | 0 |
| Eligible | No | Yes |

A's two failed public batches are pair 2 repetitions 1 and 2, run-0020 and
run-0021 in this action. On public request bellwether-compare-022, the customer
asks for price and shelf stock. A returns collection and price, adding an
unrequested task and omitting stock. Independent envelope validation rejects
the extra collection result; assessment then marks both required results as
missing execution evidence. Both captures exist. This is a semantic response
failure, not a transport failure or lost capture. The UI counts two other-check
failures. No task was removed or silently completed to improve a rate.

There are no unknown-task plan failures, truncation failures or provider transport
failures in this action. B's results establish eligibility only for this frozen
workload and these versions. Nine batches contain six public requests repeated
three times, a small sample. Passing mandatory checks includes justified
refusals; it does not mean all 18 responses are useful completions. The protected
evidence remains private and only terminal aggregates are public.

The repair packages have different prompts as well as B's validator. This result
does not isolate validation's causal effect, establish general reliability,
prove learning gains or explain either old transport stop.

## Calls, timing and cost

Execution reserved and used all 42 model calls and 24 Sandbox operations. All
42 replies have reported usage: 18,241 input and 1,877 output tokens. At repository
projection rates, this is US$0.00154494 in reported-usage inference projection.
The conservative inference reservation is US$0.09289728. Actual billing and
Sandbox cost are unknown. The complete action took 272,691 milliseconds.

Earlier S45 inference reservations total US$0.06856704. Including this action
gives US$0.16146432. Reservations and reported-usage projections are not bills.
The action allowance is exhausted. No further probe, retry, comparison or source
tuning follows from it.

## Proof and preserved artifacts

Receipts are under /tmp/shiftwork-s45-revised-live-20261024/.

- pre-call.json verifies the exact new shift had zero comparisons and choices,
  unchanged ledger, both source/artifact hashes, 63 runtime hashes, all 106
  material hashes and 66 preserved evidence hashes before sending.
- guards-clean.log and separate marker/receipt fault/restored logs prove each
  one-shot refusal. The simulated meter refuses operation 25 and call 43.
  These controls make no provider or Sandbox call.
- prepared.json retains the operator-performed preparation and actual version
  identities. live-receipt.json and live.log retain the one real action.
- audit_result.py and audit.json independently recompute public batch counts
  from retained captures, frozen public task identities and mandatory assessment
  rows. All 42 inference requests and replies are retained. Exact version hashes,
  one real comparison, zero choices and unchanged ledger are verified.
- The [scanned public package](slice45-revised-live-2026-10-24.json) has SHA-256
  465ef763b1724df2a1a7081afcd2f07d422162a7f0b43b8da4137b8dc3811564.
- Preserved comparison-terminal.db retains the pre-selection live.db bytes with SHA-256
  d6a5e8ed2aaedb9da1585e54b1c50912262896d35a819481b535ab461c5c10ac.
  live-receipt.json has SHA-256
  6f0cbbaf1b71b0ebd67ecef32092a24a4cb860569d2376be57f1987ff8ce2ce5.
  Restricted captures stay in the private store.

These report and JSON files are ignored by the existing evidence-directory
rule. They are preserved local evidence, not staged or published. Later
authorized publication must deliberately include the public files.

## Actual browser result and remaining boundary

The read-only review is http://127.0.0.1:8456/?board=bookshop#compare. It uses a
logical copy of the actual terminal live database, no live budget and a middleware
that refuses mutations. Startup reconciliation is disabled. The review database
remains logically identical to the terminal source after browser inspection.

Fresh checks pass at 1280x720 and 390x844, at native 100% and 200%. They verify
actual rates and cause splits, all 18 retained-run links, A disabled/B enabled,
Step 5 of 7, B's confirmation evidence and cancel behavior, collapsed reasoning,
no horizontal overflow, zero mutation requests and zero JavaScript exceptions.
Mobile 100% and desktop 200% screenshots were visually inspected. These are
Chromium checks with WebGL disabled, not physical-device or AT evidence.

The first browser check copied Step 4 from the old incomplete action. Source
inspection confirms the guide correctly advances to Step 5 when a complete
comparison has an eligible version. That setup failure is retained at
browser-1x-first.log and logged in MISTAKES.md. No product code changed.
The corrected browser-1x.log and browser-2x.log pass all assertions.

The earlier 1,732-pass Python regression, 310-pass Node regression and mutation
evidence remain retained, not rerun. This action changed no product source or
dependency. No installation or Git publication occurred. Scoped architecture
cleanup retains both historical generators and evidence; no deletion is needed.

## Explicit selection and acceptance

The user's "Select B and accept S45" authorizes the stored choice and acceptance.
selection-receipt.json and selection.log retain the production selection result.
The schema calls this LEARNER_CHOICE, but this is the user's choice between
operator-authored demo examples. The recorded rationale is an operator-written
summary of verified evidence, not a verbatim user explanation or learner study.

Only operating_selections changed, with one new row. Comparing every other
table and the selection table with the new row excluded reproduces the complete
pre-selection database. A's source and all original comparison rows remain.
The new live.db SHA-256 is
f808a0ca2a83d7725db7f3bceeed02f14dd438a6e18e2da9667cb82e2b14f3a5.
The original terminal hash above remains valid for comparison-terminal.db.
The original public comparison JSON remains unchanged and records the comparison
before choice. The separate [public selection record](slice45-selected-b-2026-10-24.json)
contains the scanned exact selection and acceptance authority. It is also ignored
local evidence and must be deliberately included in any authorized publication.

The current selected-state read-only review is
http://127.0.0.1:8457/?board=bookshop#compare. The 8456 copy remains the pre-choice
snapshot. The selected view advances to Step 6, shows the exact saved B choice
and disables both further-choice buttons for that completed comparison.
The first selected-state check wrongly retained the earlier enabled-B assertion;
its failed receipt is preserved and the setup error is logged. Product source
was unchanged. Corrected selected-state browser proof is retained separately.

selection-browser-1x.log and selection-browser-2x.log pass desktop 1280x720 and
mobile 390x844 at native 100% and 200%. They verify sel-0002, B's exact selected
hash and comparison, Step 6, both choice buttons disabled, all 18 retained links,
no horizontal overflow, zero mutations and zero JavaScript exceptions.
selection-final-preservation.json verifies the single added selection row,
all original rows and evidence, all 106 material hashes, 63 runtime hashes and
66 previous-evidence hashes. The scoped architect-reviewer cleanup retains all
three historical/current generators with their test callers; no deletion is
recommended. Branch/HEAD and the empty index are unchanged.

The public selection package SHA-256 is
5cb30d56af922dc3f624d539cd066fa34da48ff396e4e18e0dd85318da6a8d33.

S45 is COMPLETE and ACCEPTED. Operation, publication, deployment and S46 remain
separately authorized. No further live action or operational consequence is
implied by this acceptance.
