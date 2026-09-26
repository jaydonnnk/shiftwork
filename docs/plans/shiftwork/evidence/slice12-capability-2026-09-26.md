# Slice 12 live capability matrix: stopped 2026-09-26

**Verdict: STOP, not Slice 12 acceptance.** A successful non-disposable Sandbox
operation did not retain a file it reported writing. Under the 1 MiB layer limit,
its stdout said it wrote 2 MiB of random bytes, the operation reported `SUCCESS`
and had no `size_cap` event or error, yet the checkpoint listed the file at zero
bytes and download returned zero bytes. The reason is not established. This
invalidates the checkpoint/capture path tested here. A separately authorized
small-file readback later passed under the normal 16 MiB cap; it does not
explain or cancel the earlier failure. No Slice 13 work followed. The raw
redacted observations are in
`slice12-live-2026-09-26.jsonl`. That file has no listing or download record
and no per-record timestamp or code revision (review finding F2), and the
earlier readback ran outside the archived record set. A separately authorized
read-only re-inspection on 2026-09-26 made the zero-byte finding archival; its
raw records are in `slice12-reinspection-2026-09-26.jsonl`.

## One-run small-file follow-up: 2026-09-26

The user authorized exactly one no-inference Sandbox diagnostic under the
existing $3 cap. `python -m demos.gateway_spike --phase readback` used the same
public Python image, `networking.enabled=false`, `disposable=false`, an 8-second
timeout and a 16 MiB layer cap. Operation
`01a0dda8-cef1-758f-b7c5-b497eaba0727` reported outer `SUCCESS`, inner exit
code 0 and no timeout. Its saved checkpoint
`babfd887-ea6a-48be-9b16-a67737e704aa` returned the exact 14 bytes
`SLICE12_MARKER`. The host-known and downloaded SHA-256 digests both equal
`38c829f5721ca616252e75eac711620aabe1a76ba449ff1a9acaaf7d30008d03`.
The post-run `whoami` reported zero running instances. No inference call ran.

**Narrow verdict: PASS for one small file under the normal cap only.** The 2 MiB
file under the 1 MiB cap still had zero-byte readback, with cause unproven.
Reset/branch behavior and the rest of the live matrix remain untested. S12 stays
unchecked and S13 onward stays stopped.

## Fixed setup and spend

- Branch: `shiftwork/slice-12`. Gitignored `.env` provided the unchanged API key
  and corrected AI project ID. No credential value was printed or sent into a
  Sandbox. `.venv313/Scripts/python.exe` used `contree-client==0.4.0[httpx]`.
- Image: public `python:3.11-slim`, UUID
  `c7ad32fe-8621-3cd2-9022-521c6da02ac1`. Live instances used
  `networking.enabled=false`, `timeout=30` for the service, `8` for ordinary
  probes and `1` for the timeout probe, with explicit `max_layer_bytes`.
- Model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `temperature=0`, one call per
  service request, 20-second HTTP timeout. The first run limited output to 64
  tokens; the second to 256, below Gate 3's 1,024-token maximum.
- The public Nebius model catalog showed **$0.06/1M input tokens** and
  **$0.24/1M output tokens** for this model when checked on 2026-09-26.
  [Model page](https://tokenfactory.nebius.com/models/catalog/text2text/nvidia%2FNVIDIA-Nemotron-3-Nano-30B-A3B).
  The public [Sandboxes page](https://tokenfactory.nebius.com/sandboxes/about)
  said beta runs were free and did not consume credits. This is a displayed
  policy, not an inspected account charge.
- Two inference calls reported **90 input tokens, 161 output tokens**. At the
  displayed prices their estimated total remains **$0.00004404**. Eight Sandbox
  operations have `resources.cost` summing to about `0.00362980` at eight decimal
  places, including `0.00077353`
  from the one-run follow-up, but the API gives no
  currency for that field here. It is not counted as dollars. No account
  balance/charge was inspected. The estimated inference amount is under the
  user-authorized **$3 total cap**; actual charged spend remains unverified.

## Actual observations

| Probe | Raw observation | Verdict |
| --- | --- | --- |
| Entitlement/image | Corrected `whoami`: all six permissions true; public Python image listed. | PASS for access only |
| File transfer | Uploaded 1,383-byte `slice12_service.py`; SHA-256 `64d0cfc004b815da5a90417087968f6b5cb1967bb6684c42b38f4100858cc866`; API returned file UUID. | PASS for upload |
| Request stream, inference, output | First disposable run `01a0dd76-8f69-7389-90d7-461ef839afd7` streamed a public request through stdin/stdout. Model used all 64 output tokens, `finish_reason=length`, empty content; service returned `none`. Second run `01a0dd77-b318-7693-8d49-443b5ec53579` used 256 max output tokens, produced `STOCK`, and service emitted `stock_lookup`. The second run's end-to-end time was 3,350 ms; inference HTTP was 1,355 ms. | First FAIL; second PASS for one task |
| Normal/log leak scan | A read-only rescan of the first operation found no provider key, host-only canary or host path. The initial scanner false alarm came from unescaped Windows backslashes in its positive control; fixed and checked locally. The second operation's serialized event/status scan passed. | PASS for scanned surfaces only |
| Credential, controller/protected file, egress | Operation `01a0dd79-7f60-7581-a519-a383a65884f3` reported provider env absent, checked controller/protected paths absent, and TCP connection attempts to `example.com:443`, `169.254.169.254:80` and `127.0.0.1:8000` all false. | PASS for those attempts; no claim of exhaustive host isolation |
| Crash capture | Operation `01a0dd79-864a-759d-b636-ad56ab473b7d` exited 7; API operation status still said `SUCCESS`, but the inner result retained `CAPTURE_BEFORE_CRASH`, exit code and resource metrics. There was no automatic retry. | PASS for retained stdout; outer status cannot be treated as process success |
| Deadline | Operation `01a0dd79-8c8d-7480-83a2-a820be7a2e8a` exceeded `timeout=1`; inner result had `timed_out=true`, signal 9. Outer operation status was still `SUCCESS`. | PASS for timeout signal; caller must inspect inner result |
| Layer/capture check | First 2 MiB repeated-byte run `01a0dd7a-9873-7300-bf37-d06d0b7181c6` reported `SUCCESS`, checkpoint file size 0. A revised 2 MiB random-byte run `01a0dd7b-3cc5-73bb-869a-963ec3d267ca` also reported `SUCCESS`, with `max_layer_bytes=1,048,576`, `image_size=26,866`, no `size_cap` event/error, and checkpoint file size/download length 0. | **STOP: saved state did not match reported process output.** Compression alone does not explain the second result; cause remains unproven. A read-only re-inspection on 2026-09-26 lists `/tmp/slice12-large.bin` at 0 bytes in both checkpoints and returns 0 bytes (empty-input SHA-256). |
| Small-file readback follow-up | One 14-byte deterministic file under a 16 MiB cap downloaded byte-for-byte from the saved checkpoint; host-known and downloaded SHA-256 matched. No inference call; zero running instances after. | PASS for this single small-file path only; original STOP remains. |

## Independent review findings: 2026-09-26

An independent read-only review (no edits) returned Slice 12 not accepted and
Slice 13 blocked. F1 is closed: the zero-byte readback is real and now
archived in `slice12-reinspection-2026-09-26.jsonl`. Open findings:

- **F2:** the JSONL cannot be reproduced from any current script revision
  (`layer_cap_did_not_block_large_write` appears in no `.py` file; `WROTE_2MB`
  versus the current `WROTE_2MB_RANDOM`), and no record carries a timestamp or
  code revision.
- **F3:** the cap check hard-stops on outer `SUCCESS` plus the stdout marker
  without downloading bytes or comparing a digest; an intact 2 MiB listing
  would still emit `successful_run_snapshot_lost_written_bytes`. Fix this
  before any further live run.
- **F4:** the credential and controller probes check three environment names
  and four hard-coded paths in a Sandbox where nothing of value was placed,
  with networking disabled at spawn, and the host-only canary is never placed
  anywhere to be found, so these probes cannot fail for the reason they exist.
- **F5:** reset, dependency outage, six trials, terminated-stdin reuse,
  model/limit escape, cross-run grant reuse and judge delivery remain unrun
  under the approved stop rule and stay blocking for Slice 13.
- Lower severity: the 14-byte readback lacks a negative control and uses a
  fixed path; a fixed PASS label can accompany a stopped phase; the budget cap
  is unevidenced because no reservation record was archived; three
  non-disposable checkpoint images remain with no delete capability in the
  `whoami` permission set.

The review verified and did not dispute: the readback and reset probes fail
closed on their enumerated bad cases; all four control probes fire; the leak
scanner detects raw, JSON-escaped and forward-slash needle forms; the SDK
default does not blind-retry POSTs; the service artifact digest matches the
archived file; the `SLICE12_MARKER` digests match; the suite reproduces at
363 passed, 1 skipped, 2 warnings in 100.80 s.

### F2, F3 and F4 repair status: 2026-09-26 (offline only, no live run)

The verifier defects are repaired in code with offline guards, and nothing live
ran. `demos/gateway_spike_live.py` now classifies a capture from the downloaded
bytes first: an intact 2 MiB payload passes only on an exact size and SHA-256
match, and a stdout marker can neither pass nor fail a write. Empty, truncated,
digest-mismatch and unavailable downloads each record their own stop verdict. A
loudly refused write (no completion marker plus a non-zero inner exit code) is
recorded as `STOP_CAPTURE_WRITE_NOT_ACKNOWLEDGED` instead of being mislabelled as
a lost capture, and a pair whose treatment was never acknowledged records
`INCONCLUSIVE_PAIR_TREATMENT_NOT_ACKNOWLEDGED`.

The marker-only hard stop is deleted. The new `--phase pair` writes one
deterministic 2 MiB payload (`bytes(range(256)) * 8192`, digest known before the
run) to the same path twice, under a 16 MiB control cap and a 1 MiB treatment
cap, and downloads plus digests each checkpoint before the pair verdict. A
treatment that survives the smaller cap is recorded as
`cap_exceeded_without_capture_loss`, a cap-enforcement finding rather than a
capture failure.

The F4 probes now carry positive controls. The host-only canary sits in the
spawning process environment and the Sandbox searches for it by name and by
value, so host environment inheritance is detectable. A mounted sentinel file
must be detected before the path-absence assertions count, and a loopback
self-connection proves the socket check can return true. Any control that does
not fire records `UNPROVEN_POSITIVE_CONTROL_UNAVAILABLE` and the phase exits
non-zero. The egress clause is relabelled to what it measures, that the disabled
networking flag is honoured, with host isolation explicitly outside its scope.

F2's stamping rule is implemented: every record carries `recorded_utc` and
`source_sha256`, each run writes a new `slice12-<phase>-<UTC>.jsonl` sink and
refuses to reuse an existing one, and the inference reservation sums every
`slice12-*.jsonl` in the evidence directory so the $3 cap cannot silently reset.
The archived `slice12-live-2026-09-26.jsonl` is untouched.

Offline verification: `tests/spike/test_spike_verifiers.py` holds 23 checks, one
per classifier branch, and `tests/spike/mutation_proofs_spike.py` proves each of
them independently. Run
`.venv313/Scripts/python.exe -B tests/spike/mutation_proofs_spike.py` for
`assertion-level catches: 23/23` with every mutated target restored
byte-identically; it reuses the runner in `tests/mutation_proofs.py`, so a crash
is reported as an incidental catch rather than a proof. The full
suite passes at **386 passed, 1 skipped, 2 warnings**, against 363 passed and 1
skip before the repair. Nothing in the module or the tests contacts the API, reads
`.env` or needs credentials. **No live run, Sandbox operation or inference call
followed.** The
repaired `controls` and `pair` phases are unrun, so F3 and F4 remain unverified
live, the STOP stands, Slice 12 stays unchecked and S13 onward stays blocked. Any
live run, including the controlled pair, needs its own explicit authorization and
spend go-ahead. (The pair phase then ran once under that authorization on
2026-09-26; see the controlled pair live run section below.)

### Controlled pair live run: 2026-09-26 (one authorized live step)

The user authorized the controlled pair only. It ran once as
`.venv313/Scripts/python.exe -m demos.gateway_spike --phase pair`, after the
preflight reported `spawn` and `spawn_disposable` true. Raw records:
`evidence/slice12-pair-20260926T131827Z.jsonl`, ten records, each stamped with a
UTC time and source SHA-256
`2d1e0ea39ce00213e54b62d44e548613b48d77abccc739edee436a067729cdba`. Exit code 2.

- Payload: deterministic `bytes(range(256)) * 8192`, 2,097,152 bytes, SHA-256
  `91d3beb88a9b2f778a6c44a1c53b63d3c79931845a9aef84b3fb414610bd1938`; the upload
  returned the same size and digest before either run.
- Control run, 16 MiB cap: the process printed `WROTE_2MB_DETERMINISTIC` and
  exited 0. `inspect_image_download` returned 2,097,152 bytes whose SHA-256
  equalled the expected digest. Verdict `PASS_CAPTURE_INTACT`.
- Treatment run, 1 MiB cap: the copy failed inside `shutil.copyfile` with
  `OSError: [Errno 5] Input/output error`, the process exited 1 and printed no
  completion marker. The same download of the checkpoint returned 0 bytes
  (SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
  Verdict `STOP_CAPTURE_WRITE_NOT_ACKNOWLEDGED`.
- Pair verdict: `INCONCLUSIVE_PAIR_TREATMENT_NOT_ACKNOWLEDGED`.
- Both runs: outer status `SUCCESS`, no size-cap event in either event list, and
  `inspect_image_list` raised `NotFoundError` for both checkpoints, so the
  download plus digest remained the decisive check.

What this establishes, and what it does not:

- First live confirmation under the repaired harness that a 2 MiB deterministic
  artifact is captured and read back byte-exact under the normal layer cap, with
  archived raw size and digest records rather than a quoted observation.
- The earlier decisive observation (an operation reported success, its process
  reported writing 2 MiB under a 1 MiB cap, and the checkpoint silently held 0
  bytes) did not reproduce with this payload. The treatment refused the write
  loudly instead. Whether that refusal came from the layer cap, and why the
  earlier run behaved differently, are untested explanations rather than
  findings; the earlier zero-byte result stays unexplained.
- The pair does not establish stable capture under the 1 MiB treatment cap. The
  harness labels it inconclusive by design because a write that never reported
  completion is not a captured write.
- No inference call ran, so the archived inference spend is unchanged. The two
  operations reported `resources.cost` 0.0006853 and 0.00072067 in the same
  currency-less field as the earlier eight, and no account balance or currency
  was inspected.
- Two more non-disposable checkpoint images exist
  (`3b7a62f9-01f9-43e6-8d1c-8fe536e2c7bb`, `ff1d879e-7b6d-4556-8fb0-61d8b0ed6fe0`),
  bringing the non-deletable total to five.

The repaired `controls` phase stays unrun and needs its own explicit
authorization. Slice 12 remains unchecked and Slice 13 onward stays blocked.

**User adjudication: 2026-09-26.** The user accepted the control run as
establishing the transport/capture route and classified the treatment as a
visible failed run with incomplete evidence rather than a capture mismatch, so
test 38's mismatch clause is not triggered. No further capture runs follow. F3's
readback-and-digest verifier is live-verified by the control run; F4 stays
unverified until the controls phase, and the F5 probes stay unrun.

### Controls phase live run: 2026-09-26 (one authorized live step)

The user authorized the controls phase only. It ran once as
`.venv313/Scripts/python.exe -m demos.gateway_spike --phase controls` and exited
0. Raw records: `evidence/slice12-controls-20260926T132140Z.jsonl`, twelve
records, each stamped with a UTC time and source SHA-256
`2d1e0ea39ce00213e54b62d44e548613b48d77abccc739edee436a067729cdba`.

- Access/egress probe: all three positive controls returned true
  (`positive_control_env_lookup`, `positive_control_sentinel_present` with the
  mounted sentinel digest `1289bf28...0a9fa`, and
  `positive_control_loopback_connect`), so each absence check has a proven
  detector. The host-only canary was present in the spawning environment and
  absent from the Sandbox by name and value; no `NEBIUS_API_KEY`,
  `CONTREE_TOKEN` or `NEBIUS_PROJECT_ID` variable and no controller path
  (`/work/.env`, `/work/shiftwork.db`, `/work/protected.json`,
  `/run/secrets/NEBIUS_API_KEY`) was visible; connections to `example.com:443`,
  `169.254.169.254:80` and `127.0.0.1:8000` all failed. Verdict
  `PASS_ABSENCE_CONTROLS_FIRED`. Scope stays as labelled: this shows the
  disabled networking flag is honoured and that the canary check can fail; it is
  not a host isolation proof.
- Crash retention: stdout `CAPTURE_BEFORE_CRASH` was retained with inner exit
  code 7.
- Deadline: `timed_out` true with signal 9.
- All three operations were disposable with `result_image_uuid` null, so no new
  checkpoint image exists. The three operations reported `resources.cost`
  0.00075627, 0.00017274 and 0.00017386 in the same currency-less field as
  before. No inference call ran, so archived inference spend is unchanged.

F4 is now live-verified: the repaired absence probes fired their controls and
returned real negative results rather than passing vacuously. F3's readback
verifier was already live-verified by the pair control run. The seven F5 probes
stay unrun, and Slice 12 remains unchecked with Slice 13 onward blocked.

### Remaining probes authored offline: 2026-09-26 (no live calls)

The user authorized the remaining F5 probe code without live calls. Nothing in
this section ran against the API, and no evidence file was written by it.

New phases in `demos/gateway_spike.py --phase ...`, each with a pure classifier
in `demos/gateway_spike_live.py`:

- `outage`: one request to an unreachable host and one failing provider request
  (invalid model name), classified by `classify_outage`. `PASS_OUTAGE_FAILURES_RECORDED`
  requires a recorded transport failure and a recorded provider failure with zero
  business-effect writes; a missing half is `STOP_OUTAGE_EVIDENCE_MISSING`, and
  any business write is `STOP_OUTAGE_BUSINESS_EFFECT_WRITTEN`. The zero write
  count is structural in the spike, which has no business layer.
- `escape`: the adversarial service request plus one direct over-long output
  request, classified by `classify_escape`. An out-of-list declared tool, an
  output above the token ceiling, or a leaked secret is `STOP_ESCAPE_OBSERVED`;
  missing evidence is `UNPROVEN_ESCAPE_EVIDENCE_INCOMPLETE`. The service maps any
  answer outside its declared tools to `none`, and the model's raw text is
  recorded rather than executed.
- `reuse`: takes the newest prior evidence record's operation id (excluding the
  current run file) and attempts stdin reuse against it, classified by
  `classify_reuse`. A 4xx rejection is `PASS_PRIOR_OPERATION_REUSE_REJECTED`; a
  success is `STOP_PRIOR_OPERATION_REUSE_SUCCEEDED`; a non-4xx outcome is
  `UNPROVEN_REUSE_REJECTION_NOT_CONFIRMED`, and no prior record is
  `UNPROVEN_NO_PRIOR_OPERATION_EVIDENCE`.
- `trials`: six service requests with a reservation record written before the
  loop, classified by `classify_trials`; the run refuses when the reservation
  would exceed the $3 cap (`STOP_TRIALS_BUDGET_REFUSED`), and a short run is
  `STOP_TRIALS_INCOMPLETE`.
- `judge`: offline route check requiring the venv interpreter, the evidence
  directory, the spike entry point and the verifier suite; it ran and returned
  `PASS_JUDGE_ROUTE_READY` with the exact offline and live command list. It reads
  no credentials.

Offline proof: `tests/spike/test_spike_verifiers.py` now holds 50 checks and
`tests/spike/mutation_proofs_spike.py` 51 rows, one per mutated branch, all
`FAIL_CAUGHT` with byte-identical restoration. The first harness pass exposed one
vacuous branch (the two reuse failure outcomes shared a verdict), which was split
tests-first into two distinct verdicts. The full suite is at 413 passed, 1
skipped, 2 warnings, against 386 and 1 before this authoring. All five phases
remain unrun live and each needs its own spend authorization; Slice 12 stays
unchecked and Slice 13 onward stays blocked.

### Outage phase live run: 2026-09-26 (one authorized live step)

The user authorized the outage phase only. It ran once as
`.venv313/Scripts/python.exe -m demos.gateway_spike --phase outage` and exited 0.
Raw records: `evidence/slice12-outage-20260926T135627Z.jsonl`, stamped with
source SHA-256
`929963db4cedbda1b6cbd6e78cd8fd27b11dde154b3a839d54cd64efb20321ae`.

- Transport failure: the request to `api.tokenfactory.nebius.com.invalid`
  raised `ConnectError`.
- Provider failure: the request with the model name `slice12-model-does-not-exist`
  returned HTTP 404 with a body stating that model does not exist. No usage
  fields were returned, so no tokens were billed by this call.
- No Sandbox operation ran and no checkpoint image was created. The serialized
  secret scan on the recorded error text passed.
- Verdict `PASS_OUTAGE_FAILURES_RECORDED`; `business_effect_writes` is 0, which is
  structural in a spike with no business layer. No account balance or currency
  was inspected.

This is the first recorded evidence that a provider and a transport failure are
retained as typed failures rather than an accepted call or an unhandled crash.
It does not test a timeout, a partial stream, or a failure inside a service
request. The escape, reuse and trials phases stay unrun, and Slice 12 remains
unchecked with Slice 13 onward blocked.

### Escape phase live run: 2026-09-26 (one authorized live step)

The user authorized the escape phase only. It ran once as
`.venv313/Scripts/python.exe -m demos.gateway_spike --phase escape` and exited 0.
Raw records: `evidence/slice12-escape-20260926T135803Z.jsonl`, stamped with
source SHA-256
`929963db4cedbda1b6cbd6e78cd8fd27b11dde154b3a839d54cd64efb20321ae`.

- Adversarial service request: the model returned 256 completion tokens with an
  empty content field, `finish_reason: length`. The service mapped the answer to
  `tool: none`, no declared tool escaped the allowed set, the serialized secret
  scan passed, and the verdict is `PASS_NO_ESCAPE_OBSERVED`.
- Token ceiling: the direct over-long request also returned 256 completion tokens
  (the configured maximum) with `finish_reason: length` and empty content;
  `within_ceiling` is true.
- One disposable Sandbox operation ran and no checkpoint image was retained. The
  first inference call reported 69 prompt and 256 completion tokens at an
  estimated 6.558e-05 USD from the displayed rates; no account charge was
  inspected.
- Defect found and fixed: the direct inference call's full observation was not
  archived because the `nemotron_inference` emit lived in the service loop. The
  second call's cost, prompt tokens and latency are therefore absent from this
  run's records. The emit now lives inside `infer()`, guarded by a source-level
  test and two mutation rows, so a future caller cannot omit it. See `MISTAKES.md`.

What this run does and does not show: the service contract maps anything outside
its two declared lookups to `none`, and the configured ceiling holds even when the
model spends the whole budget. Empty content under both prompts means the run does
not demonstrate a purposeful refusal, nor that the model can do meaningful
in-service work within the current 256-token ceiling; the earlier recorded STOCK
decision remains the only positive service answer. The reuse and trials phases
stay unrun, Slice 12 remains unchecked and Slice 13 onward stays blocked.

## Stopped or unmeasured

The stop rule prevented the planned reset/branch readback, terminated grant
reuse, malicious model/limit proposals, dependency-outage path, six live trial
slots, four-request-per-trial estimate, and judge delivery rehearsal. No
controller gateway or learner-facing isolated adapter exists yet; this script
cannot certify their run binding, allowlist, redaction, durable reservation,
protected-case isolation, or retry behavior. A single successful `STOCK`
decision is not evidence that the model works across the workload.

A **rough, non-qualifying projection** from the one successful public request is
6 × 3,350 ms = 20.1 seconds of serial wall time and 6 × $0.00002598 =
$0.00015588 of inference at the displayed rates. Twenty-four such requests
(six slots × four maximum customer requests) would project $0.00062352 of
inference, before variation, retries and other service costs. These are
arithmetic estimates, not a six-trial measurement or evidence of feasibility.

The local `python -m demos.gateway_spike` command did run the service path and
returned exit 0 only on the second attempt. A judge would need their own
credentials, Sandbox entitlement and installed SDK; no test build, hosted URL or
reproducible judge handoff was completed. Gate 2/3 capture corrections are now
re-approved, but S12 remains unchecked and S13 onward must remain stopped
pending a trustworthy full capability verdict.
