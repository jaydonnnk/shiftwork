# S25 live arm: two bounded live operations, 2026-10-14 Asia/Singapore

Branch `shiftwork/slice-25-live`. Phase B ran once, by the operator, with the
exported credentials; Phase A had rehearsed the whole journey offline twice at
zero spend (proof_scope `TRUSTED_LOCAL_TEST_DOUBLE`). Scope: operations only,
per the same-day decision recorded in `preflight.md`; the qualifying comparison,
the selection, the close and the inheritance ran `TRUSTED_LOCAL` in the same
journey.

## 1. Command and result

The run bound the exact approved manifest bytes
`d969ab95e0c65688281f034da87b1e84c0175717e43d918fef55803a54c57c10`:

```
.venv/bin/python -m demos.slice25_live_gtm --execute \
  --out docs/plans/shiftwork/evidence/slice25-live-2026-10-14 \
  --approved-manifest-sha256 d969ab95e0c65688281f034da87b1e84c0175717e43d918fef55803a54c57c10
```

Reported output, verbatim:

```json
{"status": "PASS", "proof_scope": "LIVE", "live_operations": 2,
 "inference_calls": 0,
 "out": "/Users/jayd0/Desktop/shiftwork/docs/plans/shiftwork/evidence/slice25-live-2026-10-14"}
```

`receipt.json` holds 31 endpoint receipts including both intended 409 refusals
(a stale prior selection and a second first-shift operation).

## 2. The two live operations

| | shift-1 starter | shift-2 selected |
| --- | --- | --- |
| run | `run-0001`, shift `gtm-shift-01` | `run-0008`, shift `gtm-shift-02` |
| artifact | `ver-0001`, content hash equal to the `gtm_starter` pin | `ver-0002`, content hash equal to the `gtm_compare_candidate_a` pin |
| adapter / evidence | `tokenfactory` / `ISOLATED_LIVE` | `tokenfactory` / `ISOLATED_LIVE` |
| Sandbox operation | `01a1393f-0521-73bb-9dac-d1b78b720861` | `01a1393f-1727-7709-b80f-e7e5c97d27be` |
| status / wall | SUCCESS, 3795 ms | SUCCESS, 3672 ms |
| result checkpoint | `634eba86-fd80-4927-b82c-24184be214ac` | `a76ce302-220d-45eb-bc59-87ce4d2f2b59` |
| capture readback | 1713 bytes, sha256 `3f1dbffd03a20b838d79ff3b0b0da0f6e6c90b3165dadec9102b3d03b740db69`, verified | 1697 bytes, sha256 `b5801bfdf27f97a3490e2f9cb4668ebe9847a5593edf886fe6cc434539cf5d82`, verified |
| inference calls | 0 of 1 allowed | 0 of 1 allowed |
| checks | 2 fail (WRONG_ACTION) and 2 pass | 4 pass |

Each operation processed exactly one request (`gtm-incident-001`) with Sandbox
networking disabled. The captures were downloaded from each result checkpoint
and verified against the driver's `capture_written` summary by byte count and
SHA-256 before acceptance. Consequences: the starter wrote `INCIDENT_OPENED`;
the selected operation wrote `OWNER_ASSIGNED` and `SLA_CLOCK_STARTED` for
`signal:incident-apac` with owner `owner-apac-platform`, then
`INCIDENT_RESOLVED`; ledger chain VALID and operation replay IDENTICAL. The
recorded browser journey's run ids (`run-0001`, `run-0008`) and versions
(`ver-0001`, `ver-0002`, `ver-0003`) recur exactly.

## 3. Meter actuals

`meter.json`: one Sandbox operation per meter, zero calls per meter, projected
spend `0.00000000` each. The approved worst-case ceiling stays
`0.00221184` per call and `0.00442368` for the two meters; it was authorized,
not spent. Sandbox compute cost is unverified and no zero total-cost claim is
made.

## 4. Privacy

Run time: every HTTP response payload and the final receipt were scanned
against `orchestrator._private_public_needles()` plus both exported credential
values, and the receipt was written only after all scans passed (fail-closed).

Post run: the independent scan recorded in `privacy.json` checked
`receipt.json` and `meter.json` against 202 private needles in raw,
forward-slash, base64 and JSON-escaped forms: zero hits. In `journey.db`, needle
strings occur only in controller-side protected comparison evidence
(`protected_case_snapshots` and the six trusted-local comparison runs' retained
raw outputs and task assessments, run-0002 through run-0007); the operation
runs `run-0001` and `run-0008` contain none.

## 5. Limits

- Zero inference calls were made; the reviewed GTM workflows are rule-based by
  design. This run makes no model-quality, latency or inference-cost claim.
- Sandbox compute cost is unverified.
- The date guard pins live runs to the rate check of 2026-10-14; any later run
  needs a fresh same-day rate check and updated constants, and its own evidence
  directory.
- This run proves real Sandbox execution and checkpoint readback of the exact
  pinned starter and selected candidate bytes. Isolation properties are covered
  by the separately accepted S12 capability record, not by this run.
- The live comparison remains blocked by the frozen 18-request shape; widening
  it is still its own decision and review.
