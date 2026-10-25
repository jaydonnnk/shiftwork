# S46 independent comparison proposal

Executed once and COMPLETE. This action and every remainder are now CLOSED.
Neither candidate is eligible. See
[the actual result](slice46-independent-comparison-result-2026-10-25.md).
The approval text below is historical and does not authorize replay.

Status: APPROVED by the user on 2026-10-25 with "APPROVEWD", in response to the
named v3 comparison and its limits. It may execute once. Both earlier actions
and all their remainders remain CLOSED. The approval is recorded privately in
v3/approved.json and v3/approval-source.json. It includes no selection, operation,
S46 acceptance or publication. Execution evidence is pending.

The earlier "Just continue till 300k" extended the context limit for offline
work; it was not itself live authorization. The preparation text below preserves
the pre-approval checkpoint and the exact approved scope.

## What this action would establish

This is one new ordinary S45 comparison of the exact retained S46 versions A
and B. It reuses the actual accepted-and-saved checkpoint, avoiding another coach
call and another proposal diagnostic. It does not resume the failed comparison,
refund a slot in that store or change either original result.

A complete result could fill the missing comparison evidence. Mandatory-check
failures are valid results; neither version is guaranteed to pass or become
eligible. The patch adds `or []` before a caller already using `plan or []`, so
this action is not expected to establish a causal customer-facing repair.
Another transport or execution failure would leave S46 incomplete again.

This action also does not establish a continuous generation/run/accept/save/
compare browser journey. Earlier stages remain their retained operator-demo
checkpoints. S46 acceptance would still be a separate user decision, with any
remaining gaps explicit. No selection or operation is included.

## Exact store and versions

The untouched source checkpoint is:
`/tmp/shiftwork-s46-20261025/proposed-live-v2/accepted-draft.db`.
Its SHA-256 is
`c2577a9bced9d24291f11eecde00c240cc9cd0de9c5b9e37cc9fe9cb4095b29f`.
It has both finalized diagnostics, saved A and B, and no qualifying comparison.

The new prepared copy is byte-identical and read-only:
`/tmp/shiftwork-s46-comparison-proposal-20261025/v3/prepared.db`.
Only after fresh named approval could the runner create this new live store:
`/tmp/shiftwork-s46-comparison-proposal-20261025/v3/live.db`.
No live.db, approved.json or once.marker currently exists in that directory.

| Candidate | Saved version | Artifact hash | service.py SHA-256 |
| --- | --- | --- | --- |
| A | ver-0003 | fb394c5e18abe935edaec086932bfe9257b7aad867d68be68a1aa4414080c4a6 | 7736c38410ce24b52ba610b4062b228856aaad228c8a59a1eb0040e06185bdc1 |
| B | ver-0004 | 667d50c2384a1f0d7b136d1c48d540474f2d1206503ce2e977e288de3706ebc6 | 87c0a0b42851b75654820ca45bca15c8159d994114775cc061055a01b583ea59 |

B retains one accepted generated patch, learner_edited=false and the operator's
generated-use declaration. The new store will reuse local IDs, including c1;
the store path and action name distinguish the evidence. IDs cannot join stores.

## Requests, model and ceilings

Action name: `s46-independent-comparison-20261025`.

- Zero coach calls, zero new diagnostics, saves or acceptance decisions.
- One authenticated Sandbox permissions read, only after named approval.
- At most 42 Nano calls and 24 Sandbox operations, including failed attempts.
- Six ordered slots: two candidates across three existing public workload pairs.
  Each slot has three public repetitions of two requests, then one protected
  request. That is 36 public calls and six protected calls. Protected contents
  remain private and unchanged.
- Exact model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`.
- Existing temperature 0, output cap 1,024 tokens, input cap 8 KiB and provider
  deadline 20 seconds. The existing Nano reasoning-off permission is retained;
  it is not a new coach or service protocol.
- Existing isolated execution deadline 45 seconds per operation. No retry,
  lexical fallback, source tuning, local executor or extra repetition.
- The private runner refuses starting another operation/call after 30 minutes.
  An already-started bounded operation may finish after that check.

Public request pairs are unchanged:

| Pair | Request 1 | Request 2 |
| --- | --- | --- |
| 1 | Salt Roads paperback collection and alternative under GBP20 | Same request under GBP15 |
| 2 | Salt Roads hardback collection and alternative under GBP20 | Harbour Atlas paperback price and shelf stock |
| 3 | Salt Roads paperback price and shelf stock | Harbour Atlas paperback collection and alternative under GBP20 |

The manifest retains each exact public request string, raw batch hash and count.
No workload, mission, starter, protected fixture or sealed content is changed.

## Cost basis

The public [model catalog API](https://tokenfactory.nebius.com/api/public/models_info)
was read without credentials on 2026-10-25. It lists the exact Nano model active,
at US$0.06 input and US$0.24 output per million tokens. Public catalog status is
not proof of account entitlement or provider success.

The logged-out, rendered [official Sandbox page](https://tokenfactory.nebius.com/sandboxes/about)
was inspected the same day. It states that beta runs do not consume credits.
The text and screenshot are preserved under
`/tmp/shiftwork-s46-completion-20261025/` as sandbox-beta-terms-full.txt and
sandbox-beta-terms.png. The first text receipt contained only an AX diff and is
excluded; the full receipt contains the actual pricing statement.

The unchanged conservative reservation is 32,768 input and 1,024 output tokens
per call. At the verified rates, 42 calls reserve US$0.09289728 inference.
The proposed new all-in usage ceiling is US$1, conditional on unchanged
published rates and the zero-credit beta terms. Actual invoice charges and any
account-specific adjustments are unknown; the reservation is not a bill or an
account-enforced billing cap. Do not execute if those terms cannot support the
all-in ceiling or a paid option is required. Reverify public terms before
granting/exercising approval if execution occurs later.

This is a proposed NEW allowance. Neither the earlier US$5 ceiling nor its
unused balance grants authority. Prior S46 reserved inference remains
US$0.05468160; a full additional reservation would total US$0.14757888.

## Prepared runner and verification

The prepared runner, manifest, store and controls are under:
`/tmp/shiftwork-s46-comparison-proposal-20261025/v3/`.

| File | SHA-256 |
| --- | --- |
| action.py | 1b537392a142c42915b7f16b01d37ffac2037233aa5ca1b6bc051db3a898fef9 |
| manifest.json | 8fe4aec9020ce32419b473762b33d93b6c1085fa2a5e8e3df312420363231e9c |
| prepared.db | c2577a9bced9d24291f11eecde00c240cc9cd0de9c5b9e37cc9fe9cb4095b29f |
| test_controls.py | 4a454ccd3726d1ada518924da90d8256e138b74fe912d61f18b41ffa7b521e03 |

The manifest pins 167 repository runtime files and 179 installed dependency
source/binary files, package versions, Python version and binary hash, and the
unchanged lockfile hash. The Python binary SHA-256 is
`acb9914e9834d6b97c2883689da32bc33fa0820c48d704193001671f2abb52b6`.
The interpreter is `/Users/jayd0/Desktop/shiftwork/.venv/bin/python`.

Preparation copied the checkpoint and made a separate disposable reservation
probe under a network-denial control. No executor ran, no credential was read,
and no provider or Sandbox request was made. The probe did not change prepared.db
or any original store. The earlier draft runner and its receipts are preserved
in the parent directory and v2; v3 is the only current proposal. The final
proposal uses US$1 rather than the earlier drafts' tight US$0.10 ceiling, while
retaining the exact same inference reservation and request/operation counts.

All 22 v3 offline controls pass. They verify absent/mismatched approval, altered
limits, source/store/runtime/model drift and once-only refusal. An authored
adapter double exercises all 24 operations and 42 calls without executing service
code, tests the final export and unchanged selection/ledger rows, and separately
proves stopping at the first execution failure. Socket connections and the host
executor are denied during those controls. These are test-double controls, not
new live evidence or a repetition of the production mutation matrix.

Eleven separate edits in disposable runner copies each fail their intended
assertion, with passing clean/restored controls and byte-identical restoration.
These cover approval shape, runner binding, prepared/original checkpoint hashes,
configured model, source/installed runtime, once-only refusal, existing-store
preservation and each wall-clock guard. Setup errors and unrelated exceptions
are rejected through the JUnit failure checks. The current runner and prepared
store are unchanged by this fault round. Receipts: controls.txt, guard-faults.txt
and guard-fault-receipts/summary.json under v3.

```sh
/Users/jayd0/Desktop/shiftwork/.venv/bin/python -B -m pytest -q /tmp/shiftwork-s46-comparison-proposal-20261025/v3/test_controls.py
```

The execution mode requires an exact separate approved.json matching the action,
manifest/runner hashes and ceilings before reading credentials or creating a live
store. No approval file has been created in the proposed action directory.
Synthetic approval packets exist only inside disposable offline-control stores.

## Stop rule and decision boundary

The first failed permission read, execution failure, export/integrity failure,
ceiling failure or incomplete outcome closes this action and every remainder.
Ordinary mandatory-check failures remain evidence and do not trigger retries.
The runner records a terminal receipt and closure; once.marker prevents restart
or resume even after an interrupted process. There is no automatic selection,
operation, source edit or public export. Generated source executes only under
the isolated executor if this action is approved.

The concrete user decision is whether to authorize this named comparison, with
its limits, or choose bounded S46 closure with the missing evidence retained.
This document does not accept S46 or authorize commits, merge, push, installation,
deployment, a coach/source correction or S47 work.
