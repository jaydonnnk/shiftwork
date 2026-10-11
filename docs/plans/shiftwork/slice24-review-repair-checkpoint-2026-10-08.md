# S24 independent-review repair checkpoint

F1 to F4 are repaired and verified within the authorized offline scope. S24
remains **unaccepted, unstaged and uncommitted**. This repair checkpoint does
not replace the independent review or constitute a fresh independent PASS.

Date: 2026-10-08, Asia/Singapore. Workspace:
`C:/Users/jayd0/OneDrive/Desktop/nebius_nvidia`. Branch: `shiftwork/slice-24`.
HEAD: `66f9b8d5d286f67bb2e7dd75acf24c0ed1e029c0`.

## Authority and preserved scope

The user authorized narrow offline source/test repairs of the verified findings
and new repair evidence, then requested another agent continue with the existing
tests. No gates, reviewed material, seals, pins, old checkpoint or review receipts
were edited. No install, credentials, live service call, spend, staging, commit,
publication or S25 work was authorized or performed.

The complete original review remains at
[S24-review.md](C:/sw24-review-20261008/S24-review.md). Gate 4 S24, Gate 3 section
3.11 and obligation 58 with its references, and Gate 2 section 21.3 remain the
contracts. This record supersedes earlier completion wording only for the
current repair/evidence state; historical bytes and labels remain intact.

## Finding dispositions

| Finding | Narrow change and verified result |
| --- | --- |
| F1: derived text presented rejected ownership/write success | The GTM display renders assessed accepted task results, omits generic no-action assurance on partial failure, and labels rejected task output. The captured faulty bytes remain exact. The real selected API proof checks WRONG_ACTION owner/write assessments, one full-trace incident, accepted qualification only and absence of the rejected success text. |
| F2: valid-chain corrupt history was inherited | Before applying ownership, the controller verifies owner/clock/handoff cause-run provenance and replays complete finalized frozen GTM consequence sets. Missing, duplicate, conflicting and foreign consequences are refused, including missing both owner and clock. Archived ownership absent from today's batch uses historical captures and rules. Human-review handoff omissions/cause/terminal faults are refused on a disposable operator mission/state. |
| F3: replay ignored captured identity/specification bindings | Operational replay verifies the producer's context identity domain, raw specification hash, mission/specification agreement, count, requirement/condition bindings and captured byte domains. Specification-byte and hash guards are isolated by keeping overall context identity valid. Damaged inputs return UNKNOWN_MISSING_INPUTS with zero writes. |
| F4: invalid replay captures raised ValueError | Duplicate/foreign/transport-failed capture inventories are refused before reduction with UNKNOWN_MISSING_INPUTS and zero writes. Missing/extra-ordinal cases remain covered. Unexpected reducer ValueError/RuntimeError still propagate; no broad catch hides programming errors. |

Production repairs are confined to
[orchestrator.py](C:/Users/jayd0/OneDrive/Desktop/nebius_nvidia/shiftwork/orchestrator.py:1301),
its GTM display at line 1901 and its historical verifier at line 2561.
`source-edits.json` reconstructs all six original raw-byte edits exactly.

Repair-only test changes are:

- `tests/orchestrator/test_gtm_review_repairs.py`: 33 existing repair cases,
  retained through handoff; only the final fixture cleanup nesting changed.
- `tests/orchestrator/test_gtm_pipeline.py`: replaces the assertion that required
  prepared-write success text after rejection with absence and rejection-label
  assertions. Its original bytes are archived.
- `tests/orchestrator/test_gtm_operation_guards.py`: duplicate-owner control uses
  a real finalized operation and duplicates its actual owner. The later semantic
  verifier is neutralized solely to isolate the earlier cardinality guard.
- `tests/packs/gtm_mutation_proofs.py`: retained prior-input controls gain their
  owning-function anchor scope after the new verifier made one text ambiguous.
  All 106 controls and their behavioral assertions remain.
- `MISTAKES.md`: append-only repair/setup incidents and prevention rules.
  Status and supporting brief receive current-state notices with exact historical
  suffix preservation. Inherited source/test changes stay untouched.

## Fresh verification

All receipts below are in `C:/sw24-repair-20261008/`. Commands use the existing
`.venv313/Scripts/python.exe`, `-B`, and scrubbed credential environment variables.
The physical copies have no Git metadata and are copies of the dirty tree.

| Check | Actual result and retained receipt |
| --- | --- |
| Copied reviewer defects before repair | 14 failed, 10 passed, zero setup errors; `review-before.log/xml` |
| Copied reviewer probes and guards after repair | 36 passed; `review-after.log/xml` |
| Initial new repair cases before/after | 20 failed, 7 passed before; 27 passed after; `regressions-before/after.log/xml` |
| Final 33 cases against exact pre-repair orchestrator | 23 failed, 10 passed, zero setup errors; `stable-preimage.log/xml`, import observation and receipt. Ten cases confirm already-working behavior. All 6,215 bound files restored. |
| Final repair and operation guards | 57 passed, two existing warnings; `strengthened-stable.log/xml` |
| Initial broad focused run | 374 passed, two warnings; `focused.log/xml`, predating final test strengthening |
| First repair full suite | 2 failed, 1,371 passed, 1 skipped, two warnings; `full.log/xml`. The fixture leak is retained, not counted as clean verification. |
| Fixture leak reproduction and correction | Ordered three-case before: 2 failed, 1 passed. After nested cleanup: 3 passed. `isolation-before/after.log/xml` |
| Final non-packaging regression | 1,373 passed, 1 live-only skip, two existing warnings, zero failures/errors; `full-final.log/xml/receipt` |
| Final real S24 source-fault CLI | 55 intended named assertion catches, zero setup errors; `stable-controls24/receipts/` |
| Final real refreshed S23 source-fault CLI | 106 intended assertion catches at their historical current statements, zero setup errors; `stable-controls23/receipts/` |
| Exact fault/import/restoration audit | `final-fault-audit.json`: exact replacement landing, imported copy path, current compiled function code, one named case, green baseline node, assertion statement and JUnit hashes per control. All 6,215 bound files remain exact after both sequential inventories. |
| Shipped-material demo and read-only audit | Exit 0; `demo/`, `demo-receipt.json`, `fresh-demo-audit.json`. 16 runs, 52 captures, 16 check rows, one owner/clock, two incident opens and one resolution. All four operational runs replay IDENTICAL, database hash unchanged, integrity ok and no FK errors. |
| Reviewed material checker | `material-final.log/receipt`: 19 files, three document bindings, three artifact pins, original approval digest and seals verify. |

The shipped demo selects `ver-0002`, retains `ver-0003`, operates `run-0008`,
reprocesses `run-0009`, and completes six later-condition slots without rewriting
prior business rows. It demonstrates the QUALIFIED operational workload.

Principal final commands, retained exactly in command receipts:

```text
# cwd C:/Users/jayd0/OneDrive/Desktop/nebius_nvidia
.venv313/Scripts/python.exe -B -m pytest tests --ignore=tests/packaging -q --tb=short --junitxml=C:/sw24-repair-20261008/full-final.xml
.venv313/Scripts/python.exe -B -m demos.gtm_operation --out C:/sw24-repair-20261008/demo
.venv313/Scripts/python.exe -B -m demos.gtm_reviewed

# cwd C:/swr24-sf8yr9a9; same absolute existing interpreter, observed bare CLIs
python.exe -B -m tests.packs.gtm_operation_mutation_proofs --out C:/sw24-repair-20261008/stable-controls24/receipts
python.exe -B -m tests.packs.gtm_mutation_proofs --out C:/sw24-repair-20261008/stable-controls23/receipts
```

The observer instruments child invocation without changing inventory behavior.
Target preimages are archived before faults; source faults never ran in the
shared OneDrive tree during this repair. Counts are finite controls, not branch
coverage or an assurance that no other defect exists.

## Excluded evidence and narrow verification repairs

Retain the aliased-inventory observer failure, the earlier intercepted fictitious
duplicate-owner control, the archived-history setup failure and the dependent
copy-refresh/preimage attempt whose final binding failed. They are not added to
the final control counts. The latter source restored exactly, but three intended
newer files differed from its old manifest and no completed receipt was issued.

This continuation also retained a fresh-helper input-path failure and an S23
anchor preflight refusal before any fault ran. Both were corrected into fresh
destinations. The first full regression's two downstream failures came from the
human-review fixture's cleanup order: an outer binding restored a temporary
mission root after the inner mission binding had restored the real root. A
separate state-binding context now exits before mission cleanup. The ordered
before/after proof validates this change without changing product assertions.

The final copy is independently prepared and bound. Original copied trees,
manifests, archives and rejected outputs remain available. No failed receipt was
overwritten, weakened or silently counted as passing evidence.

## Bounded architect-reviewer cleanup

This is the continuing agent's scoped cleanup review, not an independent oracle.

| Area | Result and action |
| --- | --- |
| Ownership and reduction | Keep. Assessment, projection, frozen replay and inheritance remain controller-owned. Reducer behavior and earlier pack paths are unchanged by these repairs. |
| Helpers and tests | Keep. The historical verifier is called before ownership application. Semantic-history tests and the isolated duplicate-cardinality test cover different guards; no deletion is justified. |
| Modules and dependencies | Keep. All 56 production Python modules parse; no new production import, dependency, endpoint, storage schema, framework, CI or lockfile change. |
| History verification cost | RISK, unmeasured. Freezing replays each finalized GTM v3 operation. No speculative cache or refactor was added during this correctness repair. |
| Fixtures and records | Keep all reviewed material and historical evidence. Temporary human-review and outage observations remain disposable. Old completion/PASS labels are historical and limited by the later independent review. |
| ADRs and gates | Keep unchanged. Deterministic replay, exact selected inheritance, experiment separation and the protected-comparison boundary remain the approved design. |

No deletion or architecture backtrack is proposed. `scope-audit.json` records
6,807 entry-bound repository files, all 576 reviewer files, permitted deltas,
exact unchanged source-line bytes, exact source-edit reconstruction, historical
log prefix/document suffix preservation and unchanged branch/HEAD/index/refs.
The post-checkpoint `final-preservation.json` supplies the final byte audit.

## Remaining limits and review boundary

- The changed-hash/ineligible selection matrix, detailed inherited
  rationale/requirements/test/limit negatives and experimental/unselected
  incident-resolution negatives remain shared-pack evidence. No separate complete
  GTM-specific matrix is claimed.
- Human-review positive/negative controller cases bind a disposable consistent
  operator mission/state with confidence 50 and REVIEW admitted before selection.
  They do not approve or demonstrate a shipped human-review operational workload.
  If acceptance requires that shipped workload, this packet does not provide it.
- Packaging is excluded; live Sandbox conformance is the explicit skip. No S25
  browser journey, clean installed-package reproduction, arbitrary Windows-path
  portability, model quality, learner gain, real CRM action/customer messaging,
  cost, hostile isolation, adoption or production readiness is established.
- Original review-map limitations remain explicit. A finite repair proof is not
  automatic S24 acceptance or permission for S25 or publication.

No process remains running at closeout. Await user instructions on review or
acceptance; do not stage, commit, publish or continue to another slice.
