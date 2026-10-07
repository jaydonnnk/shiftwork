# S23 LF repair checkpoint, 2026-10-07

Status: LF blocker repaired. Exact packet ready for operator material review,
with the incoming ignore-rule exception disclosed. NOT APPROVED OR APPLIED.
S23 remains incomplete, unaccepted, unstaged and uncommitted.

Branch `shiftwork/slice-23`; HEAD `3e02f1e5176cd34d6dc355bbc4529234fa51fe62`.
The user's `Go` resumed offline implementation and packet preparation only.

## Verified repair

- `lf-before.log/xml`: the unchanged repository LF guard reproduced one failed
  assertion identifying the GTM manifest and pair 01/02 task-spec JSON.
- `lf-repair.json`: replaced only 36, 225 and 221 CRLF sequences respectively.
  Every parsed JSON value is identical; manifest/family remain DRAFT/null.
  Original bytes are retained under this continuation's `preimages/`.
- `lf-after.log/xml`: 2 passed, 2 warnings, including the existing LF guard and
  packet preimage/proposed-seal check. No test or assertion was weakened.
- `full-offline.log/xml`: **1278 passed, 1 skipped, 2 warnings in 967.15s (0:16:07)**, exit 0. JUnit confirms 1279
  cases, zero failures, zero errors and one skip. Packaging was excluded because
  installation is unauthorized. The skip is the separately authorized live
  Token Factory conformance arm. The two deprecation warnings remain.

## Refreshed packet

Approval digest: `8d87c2dc279f31f3206ec389e0f72b34b50e038c59bc764ef60c13489b62d1fa`.

Current records: [operator packet](slice23-gtm-operator-review-packet.md) and
[machine inventory](slice23-gtm-review-inventory.json).
Fresh proposal files and narrow source diffs are in
`evidence/slice23-lf-repair-2026-10-07/proposed-application/` and its parent.
`packet-verification.json` verifies all 19 material preimages, two seal-only
JSON edits, 19 proposed material pins, three document bindings and three offline
fixture pins. AST comparison confines source edits to GTM declarations and
the three fixture entries. All matching registry/config lines retain their
exact bytes and line endings. All 19 effective Git text attributes are unset.
Canonical workload/case seals and artifact fixture hashes did not change.
The seven changed hash fields and new digest are in `packet-refresh-changes.json`.
The original first-draft and pre-repair proposals remain preserved and superseded.

## Preservation and limits

`pre-document-preservation.json` verifies 4803 pre-S23 historical evidence
files, all 5065 incoming evidence files and 42 existing reviewed material files.
All incoming production source and tests are unchanged. The 106 retained
source-fault controls were audited against their exact source hashes, unique
anchors, named raw JUnit assertions and log hashes; they were not rerun.
Five rejected controls remain excluded. The full suite reruns ordinary guard,
material and hypothetical comparison checks. Earlier disposable six-slot
evidence remains hypothetical and is not the production-reviewed S23 exit.

The incoming `.gitignore` SHA-256 remains
`03ba60bd890227f4538781177ecf291eb07719043f52ddb6d870f3a9aa7b97a4`. Ownership of its request-directory rule is
unverified. All eight hidden GTM request drafts are explicitly inventoried.
The earlier post-document audit remains a failed historical receipt. This
continuation's checks disclose the preserved incoming exception and do not
claim that the original whole-tree hold is resolved. Final document/scope
verification is recorded separately in `continuation-preservation.json`;
read that receipt for its actual verdict.

No production pins/seals, actual GTM admission, credentials, installs, live
calls, spending, Git staging/commits/pushes, S24 or S25. Retry scaling and the
existing live two-request preflight remain later-slice limits.

## Next authorized boundary

The operator must approve the exact 19-file material packet, its four proposed
production replacements and the offline admission/starter/six-slot comparison.
Retain that explicit authorization and refuse preimage/digest drift before
application. Only then may production review authority be applied. Complete
the actual reviewed comparison and post-slice architecture cleanup before
requesting S23 acceptance. Live work and later slices remain separately gated.

Post-approval verification must also transition the prereview-only tests and
disposable helper in `test_gtm_pipeline.py` and `gtm_material.py` to the exact
approved inventory. They currently require DRAFT/null production material.
Keep the draft inventory CLI draft-only, retain the reviewed receipt, preserve
all refusal/fault guards, and rerun the full suite before acceptance. The current
green suite is pre-application evidence, not evidence of that later state.
