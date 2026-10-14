# S25 live arm: entitlement preflight and rate check, 2026-10-14

Branch `shiftwork/slice-25-live`. Nothing was spent by this record. No Sandbox was
created, no inference call was made, no model call was made.

## 1. Entitlement preflight: PASS

Command, run by the operator with a new API key in the process environment:

```
.venv/bin/python -m demos.gateway_spike --phase preflight
```

Reported output, verbatim except for reformatting onto one block:

```json
{"elapsed_ms": 961,
 "limits": {"images_import_max_concurrency": 8, "images_import_max_timeout": 3600,
            "instance_max_concurrency": 50, "instance_max_layer_bytes": 12884901888,
            "instance_max_timeout": 3600},
 "operations_stat": {"running_imports": 0, "running_instances": 0},
 "permissions": {"cancel": true, "import": true, "list": true, "set_image_tag": true,
                 "spawn": true, "spawn_disposable": true},
 "probe": "sandbox_whoami",
 "result": "ready_for_capability_probes"}
```

All six permissions are true, matching the corrected S12 result. The response contains
no token, token UUID, project identifier or expiration, so it is safe to retain.

What this proves: a `spawn`-capable entitlement exists for the configured project.
What it does not prove: any isolation, latency, cost or model-quality property. This was
one control-plane `whoami` request at 961 ms wall time. The `limits` block reports
account limits, not proof that this token can use them at scale.

Note on credentials: the values live only in the operator shell. `demos/gateway_spike.py`
deliberately never reads `.env`, so exporting was required. The earlier key was not
recoverable on this machine and a replacement was created; the entitlement comes from
the `aiproject-...` project identifier, not from the specific key.

## 2. Same-day rate check: partial, conservative bound accepted

The check is required to fall on the run day; this was performed on 2026-10-14.

The vendor page did not render a pricing table to any retrieval attempted today: the
Nebius Token Factory Nemotron page, the Nebius prices page and the Token Factory overview
each returned without per-million rates for this model. Reachable third-party sources
agree on $0.05 per million input and $0.20 per million output for the Nebius-served
`nvidia/nemotron-3-nano-30b-a3b`; artificialanalysis reports Nebius at $0.08 per million
blended, which is consistent with a blended form of those two figures.

Decision, by the operator: keep the pinned $0.06 per million input and $0.24 per million
output. Both sit above every quote found, so the $0.10 projection cap remains a
conservative upper bound rather than an under-estimate. The vendor's own table was not
read, and that limitation is recorded rather than papered over.

## 3. Scope decision: operations only

Measurement on the same day falsified the comparison stage of the plan; see checkpoint
section 8.5. `LiveComparisonBudget.preflight` requires exactly 6 slots and 18 requests,
while the GTM comparison executes 24 (6 slots at 4 executed requests each, measured from
the recorded comparison database). The live comparison fails closed and cannot run.

Operator decision: the live arm runs the **operations only**. The starter diagnostic and
the inherited selected operation each run once under their own `LiveOperationBudget`
(one Sandbox operation, one inference call). The qualifying comparison, the selection,
the close and the inheritance stay TRUSTED_LOCAL. The GTM operational workload is exactly
one request, `gtm-incident-001`, which is what that meter requires.

Widening the frozen comparison shape is not authorised by this record. It would change a
reviewed S16 and S22b control and needs its own decision and review.

## 4. Projected spend for the reduced live arm

At the pinned rates with 32768 reserved input tokens and 1024 reserved output tokens per
call, the projection is $0.00221184 per call. Two operations project at **$0.0044**
total, each hard-capped at one spawn and one call by its own meter, with failed attempts
counted and never refunded. No meter can be topped up and no stage retries.
