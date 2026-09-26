# Slice 12 Sandbox entitlement preflight: 2026-09-26

**Later state:** the corrected preflight did permit live probes, but the partial
matrix stopped on a checkpoint readback mismatch. See
[Slice 12 capability evidence](slice12-capability-2026-09-26.md). The next-action
sentence at the end of this dated preflight is historical.

## Corrected project header: entitlement available

A screenshot of a 2026-09-23 Nebius Support reply supplied the correct Sandbox
`Project` header value, an `aiproject-...` identifier. The existing `.env` used a
different `project-...` identifier. Retesting with the same API key and the
support-provided AI project ID returned HTTP 200 with `spawn`,
`spawn_disposable`, `import`, `list`, `cancel` and `set_image_tag` all **true**.
`list_images(limit=1)` also returned HTTP 200 with one image. The corrected ID
is now in the gitignored local `.env`; the API key is unchanged. A repeat of
`python -m demos.gateway_spike` exits 0 and reports
`ready_for_capability_probes`. This clears only the entitlement blocker. No
instance or inference run has yet tested Slice 12's safety, cost or latency.

The denied result below is retained as the historical result for the wrong
project header, not evidence that this token lacks Sandbox access.

**Earlier result: BLOCKED before the capability matrix.** `GET /sandboxes/v1/whoami`
authenticated but returned `spawn=false` and `spawn_disposable=false`. Every
permission in its response was false. No instance was created, no image was
imported, and no inference request or six-trial run was made. Slice 12 is not
complete and S13 onward cannot rely on a Sandbox isolation claim.

## Reproduction

From the repository root, with `.venv313/Scripts/python.exe` and the installed
`contree-client==0.4.0` `httpx` extra:

```powershell
Get-Content .env | Where-Object { $_ -match '^NEBIUS_(API_KEY|PROJECT_ID)=' } | ForEach-Object { $pair = $_.Split('=', 2); [Environment]::SetEnvironmentVariable($pair[0], $pair[1], 'Process') }
.venv313/Scripts/python.exe -m demos.gateway_spike
```

With the earlier `project-...` header, the command exited 2 and reported
`blocked_no_spawn_permission`. It emits no
credential, token UUID or token expiration. The local `.env` key had a leading
space, producing an initial HTTP 401; that local formatting was corrected
without recording the value. The authenticated response then reported:

```json
{
  "permissions": {
    "cancel": false,
    "import": false,
    "list": false,
    "set_image_tag": false,
    "spawn": false,
    "spawn_disposable": false
  },
  "operations_stat": {"running_imports": 0, "running_instances": 0},
  "limits": {
    "images_import_max_concurrency": 8,
    "images_import_max_timeout": 3600,
    "instance_max_concurrency": 50,
    "instance_max_layer_bytes": 12884901888,
    "instance_max_timeout": 3600
  }
}
```

The final CLI run reported `elapsed_ms=634`. This is one request's wall time,
not a sandbox latency estimate. The response contains account limits, not proof
that this token can use them.

Local verification after the preflight: `.venv313/Scripts/python.exe -m pytest
tests -q` returned **363 passed, 1 skipped, 2 deprecation warnings** in 61.51
seconds. The suite is offline and does not turn the unrun matrix into a pass.

## Evidence boundaries and next action

| Planned probe | Observation | Result |
| --- | --- | --- |
| Entitlement | Authenticated `whoami`; all returned permissions false | BLOCKED |
| Exact model/image/settings and meaningful interpretation/tool choice | No request | UNMEASURED |
| File transfer, request stream, output and capture retrieval, cleanup | No instance | UNMEASURED |
| Six trial slots: latency, usage, failures and cost | No trial | UNMEASURED |
| Dependency outage, reset, crash and retained captures | No instance | UNMEASURED |
| Deadline, resources, egress and arbitrary URL access | No instance | UNMEASURED |
| Cross-run grant reuse, model/limit escape | No grant | UNMEASURED |
| Provider key, controller/database/host/protected file access | No instance | UNMEASURED |
| Normal/error/log leakage | No instance or gateway | UNMEASURED |
| Reproducible judge delivery route | No live build | UNMEASURED |

No model, image, settings, token usage, trial cost or judge route was measured.
The $3 spend cap remains in force, but actual billing for the preflight is
unknown; no account balance or pricing meter was inspected.

The corrected project header supplies Sandbox `spawn` access. Execute the
bounded matrix next. Do not mark S12 complete or start S13 until its real
probes pass.
