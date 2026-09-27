# Slice 12 live capability matrix: final verdict 2026-09-27

**Verdict: the live matrix is complete and the 2026-09-26 stop is resolved, with
the limits below; Slice 12 acceptance itself is the user's decision at the
review pause.** On 2026-09-26 a STOP was issued because a successful
non-disposable Sandbox operation did not retain a file it reported writing.
Under the 1 MiB layer limit, its stdout said it wrote 2 MiB of random bytes, the
operation reported `SUCCESS` and had no `size_cap` event or error, yet the
checkpoint listed the file at zero bytes and download returned zero bytes. The
reason is not established. That invalidated the checkpoint/capture path tested
here. A separately authorized small-file readback later passed under the normal
16 MiB cap. The raw redacted observations are in
`slice12-live-2026-09-26.jsonl`. That file has no listing or download record
and no per-record timestamp or code revision (review finding F2), and the
earlier readback ran outside the archived record set. A separately authorized
read-only re-inspection on 2026-09-26 made the zero-byte finding archival; its
raw records are in `slice12-reinspection-2026-09-26.jsonl`.

What resolves the stop, in order:

- The repaired byte-first verifier (`pair` phase, 2026-09-26) could not
  reproduce a silent loss: the 16 MiB control captured the deterministic 2 MiB
  payload and read it back byte-exact, while the 1 MiB treatment refused the
  copy loudly (`OSError: [Errno 5]`, exit 1, no completion marker, 0-byte
  checkpoint). The user's 2026-09-26 adjudication accepted the control run as
  establishing the transport/capture route and classified the treatment as a
  visible failed run with incomplete evidence, not a Gate 3 test 38 mismatch,
  with no further capture runs.
- The remaining authorized phases then ran: `controls`, `outage`, `escape`,
  `reuse` and `trials` on 2026-09-26, and the judge route, a confirming service
  call and `reset` on 2026-09-27. None of those eight closed on a stop
  condition, and each left a raw record in this directory.
- No Gate 3 section 8 hostile probe succeeded, the model produced a usable
  in-service decision under the fixed ceilings in the original run, all six
  trials and the confirming call, and six trials completed. No S12 Limits
  trigger in `04-slices.md` fires, so the stop no longer blocks Slice 13
  planning. It does not itself authorize Slice 13 work.

Limits that stay visible in this verdict:

- The original zero-byte observation remains unexplained and was never
  reproduced. Capture under a 1 MiB layer cap is not established; the treatment
  refused the write instead.
- Gate 3 section 8 probe 1's protected-fixture limb is N/A rather than PASS: a
  spike has no sealed cases, and the mounted sentinel is a positive control that
  is meant to be found.
- The six trials are six samples of one identical request at `temperature=0`.
  They measure repeatability, latency and cost, not workload coverage; the
  standing one-task-shape caveat weakens from one sample to six of the same one
  rather than being retired.
- Inference observations archived before the 2026-09-27 repair omit the model's
  `message.reasoning` text. The confirming call established what the missing
  tokens were; the earlier records cannot be repaired retroactively, and that
  includes the escape run's two empty completions, which stay indistinguishable
  from a refusal on archived data alone.
- The judge route is an offline prerequisites check, not a hosted demo or a
  measured judge walkthrough; no public ingress, test build or hosted URL was
  produced.

The 2026-09-26 sections below are preserved as history; where a later section
supersedes a sentence, the later section says so.

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
unchecked and S13 onward stays stopped. (Superseded 2026-09-27: the reset/branch
behavior and the rest of the live matrix ran under separate authorizations; see
the final verdict at the top of this document.)

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

### Reuse phase live run: 2026-09-26 (one authorized live step)

The user authorized the reuse phase only. It ran once as
`.venv313/Scripts/python.exe -m demos.gateway_spike --phase reuse` and exited 0.
Raw records: `evidence/slice12-reuse-20260926T171955Z.jsonl` (three records),
stamped with source SHA-256
`3b95ced65f764a017d526cf6f1e9845736cbec8af478a2f2362a14c6edcd1d11`, which differs
from the escape run's stamp because the `infer()` emit repair landed after it. No
tracked evidence file was rewritten.

- Entitlement: `whoami` returned all six Sandbox permissions true
  (`spawn`, `spawn_disposable`, `cancel`, `import`, `list`, `set_image_tag`),
  `running_instances: 0`, `running_imports: 0`, and the same limits as prior runs
  (`instance_max_concurrency: 50`, `instance_max_layer_bytes: 12884901888`,
  `instance_max_timeout: 3600`).
- Cross-run grant reuse: the probe took the newest prior terminal operation id
  from the archived evidence, `01a0de02-4961-7782-a709-0006382fdd1b`, which is
  the escape run's `escape_spawn` operation, and sent `reuse\n` to its subprocess
  stdin with the stream closed. The API rejected it with HTTP **409**,
  `succeeded: false`, verdict `PASS_PRIOR_OPERATION_REUSE_REJECTED`.
- Spend and residue: this run created no Sandbox operation and made no inference
  call, so there is no `resources.cost` value and no `nemotron_inference` record.
  The only account activity was two read/write API calls. No checkpoint image was
  created, so the non-deletable image total is unchanged by this run.
- Leakage: the archived records were re-scanned offline with the harness's own
  `no_secret_leak` against the credential, the host-only canary and the working
  directory, and the project id was checked absent from the raw file text. Both
  checks passed; the scanner self-tests that each needle is detectable in its
  serialized form, so the pass is capable of failing.
- Offline state after the run: full suite `414 passed, 1 skipped, 2 warnings`;
  `tests/spike/mutation_proofs_spike.py` `assertion-level catches: 53/53` with
  byte-identical restoration, exit 0. Neither changed from the pre-run baseline,
  because this step added one evidence file and no source.

What this run does and does not show: a prior run's terminal operation still
exists and actively refuses new input from a later run, and it refuses with a 409
conflict rather than a 404, so this is a rejection by the service and not merely a
missing record. It does not show that image, credential or project grants are
revoked between runs, and it says nothing about an operation that is still
running. The trials and reset phases stay unrun and each needs its own spend
authorization; Slice 12 remains unchecked and Slice 13 onward stays blocked.

Correction 2026-09-27: the paragraph above originally listed readback as unrun
alongside trials and reset. That was wrong and contradicted this document's own
"One-run small-file follow-up" section and its matrix row, which record the
readback phase running on 2026-09-26 and returning `PASS_ONE_SMALL_FILE_ONLY`.
`readback_probe` has not changed since `f5d37bc` and the archived expected and
actual digests both equal `sha256(b"SLICE12_MARKER")` at 14 bytes, so a re-run
would reproduce the same record and add a sixth non-deletable image. Readback is
not a remaining gap; its scope limit stands as written there, namely PASS for one
small file under the normal cap only.

Supersession: the "terminated grant reuse" item in `Stopped or unmeasured` below is
now measured by this run. The reset probe carries its own terminated-stdin check
and stays unrun, as do the six live trial slots and reset's own branch readback
(that paragraph's "reset/branch readback" item, which is the base-image-versus-
checkpoint comparison inside `reset_probe`, not the standalone readback phase).
That paragraph is otherwise left as written about the original stopped run.

### Trials phase live run: 2026-09-27 (one authorized live step)

The user authorized the trials phase only. It ran once as
`.venv313/Scripts/python.exe -m demos.gateway_spike --phase trials` and exited 0
at `2026-09-26T17:45:21Z` UTC, which is 2026-09-27 local. Raw records:
`evidence/slice12-trials-20260926T174521Z.jsonl`, 34 records stamped with source
SHA-256
`3b95ced65f764a017d526cf6f1e9845736cbec8af478a2f2362a14c6edcd1d11`, the same
revision as the reuse run. No tracked evidence file was rewritten.

- Verdict: `PASS_SIX_TRIALS_FEASIBLE`, planned 6, completed 6, `budget_ok` true.
  Every trial recorded `complete: true` and `stock_decision: true`, so all six
  disposable service runs ended with the service emitting `"tool": "stock_lookup"`
  for the public request.
- End-to-end latency per trial: 4,136 / 4,006 / 3,944 / 3,983 / 3,601 / 3,722 ms.
  Sum 23,392 ms, mean 3,898.7 ms, min 3,601, max 4,136, spread 535 ms.
- Inference HTTP latency alone: 1,932 / 1,618 / 1,977 / 2,110 / 1,727 / 1,824 ms,
  mean 1,864.7 ms, so inference is about 48 percent of a trial and the remainder
  is upload, spawn, event polling and capture.
- Usage: `prompt_tokens` 45 on all six (sum 270); `completion_tokens`
  127 / 103 / 126 / 143 / 103 / 104 (sum 706, mean 117.7). All six returned
  `finish_reason: stop`, so none reached the 256-token ceiling.
- Estimated inference cost at the displayed rates: 3.318e-05 / 2.742e-05 /
  3.294e-05 / 3.702e-05 / 2.742e-05 / 2.766e-05 USD, sum **0.00018564**, which is
  about 5.6 percent of the 0.00331776 worst-case reservation taken before the loop.
- Sandbox `resources.cost` across the six operations sums to 0.00383704 at eight
  decimal places. As in prior runs the API states no currency for that field, so
  it is not counted as dollars.
- Budget: `prior_inference_spend` over all `slice12-*.jsonl` is now
  **0.00803670 USD** against the 3.00 USD cap, leaving 2.99196330 of headroom, and
  another six trials would reserve 0.00331776 and still be allowed. This figure
  remains a conservative bound rather than measured spend, because it sums
  worst-case reservations alongside actual estimates and the escape run's second
  call contributes only its reservation.
- Residue: `service_request` spawns with `disposable=true`, so none of the six
  operations left a checkpoint image and the non-deletable image total is
  unchanged at five. `whoami` before the run reported `running_instances: 0` and
  all six permissions true.
- Leakage: the 34 records were re-scanned offline with the harness's own
  `no_secret_leak` against the credential, the host-only canary and the working
  directory, on both the parsed records and the raw file text, and the credential,
  project id and canary were each confirmed absent from the raw text. The scanner
  self-tests that every needle is detectable in serialized form, so the pass is
  capable of failing.
- Offline state after the run: full suite `414 passed, 1 skipped, 2 warnings`;
  `tests/spike/mutation_proofs_spike.py` `assertion-level catches: 53/53` with
  byte-identical restoration, exit 0. Neither changed from the pre-run baseline,
  because this step added one evidence file and no source.

**New defect this run exposed: the archived inference observation omits most of
what the model produced.** Each trial's `completion_tokens` was 103 to 143 while
the archived `content` was the six characters `\nSTOCK`. `infer()` records only
`choices[0].message.content` and reads no other field the provider returns, so
roughly 100 to 140 billed completion tokens per call are absent from the
evidence. Whether they are `reasoning_content` or another field is **not
established by this run**, since the field was never captured; establishing it
would need another authorized call. This is the same class as the escape run's
unarchived second observation but a different instance: that defect lost a whole
record, this one keeps the record and drops part of its payload. It does not
change the feasibility verdict, which rests on `finish_reason`, the service's
`stock_lookup` output and the recorded usage, but the spike's raw inference
observation is incomplete. See `MISTAKES.md`.

What this run does and does not show: six trials of the public request are
feasible inside the $3 cap and inside the 256-token ceiling, at a mean 3.9 s and a
mean estimated $0.00003094 of inference each, and the model produced a usable
in-service tool decision every time. It does not show workload coverage. All six
trials used identical request text at `temperature=0`, so this measures
repeatability, latency and cost for one request shape; the standing caveat that
one task shape is not evidence the model works across the workload is unchanged in
kind and only weakened from a single sample to six samples of the same one. It
also does not re-test the escape run's two empty completions: those prompts were
harder and exhausted the ceiling, and this run shows only that easier prompts do
not.

Supersession: the escape section's "the reuse and trials phases stay unrun" and
its "the earlier recorded STOCK decision remains the only positive service answer"
are both superseded here, which adds six more positive service answers. In
`Stopped or unmeasured` below, the "six live trial slots" item is now measured,
while the "four-request-per-trial estimate" remains a projection, because each
trial made exactly one customer request rather than four. That paragraph is
otherwise left as written about the original stopped run.

### Judge route archived offline: 2026-09-27 (no live call)

The judge delivery route had no archived record: `--phase judge` printed its
result but never set an evidence sink, so matrix clause 12 rested on prose in
this document while every other clause had a `slice12-*.jsonl` file. The phase
now writes its own stamped run sink through the same `build_record`/`emit`
discipline as the live phases, and its route check gained a fifth requirement:
the evidence directory must actually contain `slice12-*.jsonl` records, so the
route cannot pass on an empty delivery.

One offline run on 2026-09-27,
`.venv313/Scripts/python.exe -m demos.gateway_spike --phase judge`, exited 0 and
wrote `slice12-judge-20260927T000104Z.jsonl` (one record, source SHA-256
`5389c0342b315dd36fd7fb7025df318aaa0f280a9b347b1180f8c81fb81e46f6`). The record
carries all five checks (all true), verdict `PASS_JUDGE_ROUTE_READY`, the
environment names a judge needs, the two offline commands and the ten live
phase commands. A missing prerequisite still archives a
`STOP_JUDGE_ROUTE_INCOMPLETE` record and exits 2. Offline guards: two new checks
in `tests/spike/test_spike_verifiers.py` (a ready root archives its checks and
verdict; a bare root fails closed and archives the incomplete verdict) and three
new mutation rows, each failing at assertion level. The file was re-scanned with
the harness's own `no_secret_leak` on the parsed records and the raw text; both
pass, with the credential loaded from the gitignored `.env`. The phase reads no
credential and made no live call.

### Inference payload archiving repaired, one authorized confirming call: 2026-09-27

The trials defect (logged in `MISTAKES.md`, 2026-09-27) is repaired. `infer()`
previously archived a hand-picked field list, so every `nemotron_inference`
record from before this date omits roughly 100 to 140 billed completion tokens
per call. It now archives the whole provider response body under
`provider_response`, minus an explicit `REDACTED_RESPONSE_FIELDS` list (empty
today) whose dropped keys are recorded in `redacted_fields`, so a deliberate
omission is visible rather than silent. The single emit site inside `infer()` is
unchanged; the repair changes what that record contains, not where it is
produced.

Offline proof: two new checks
(`test_inference_record_archives_the_whole_provider_payload` runs `infer()`
against a fake HTTP client and requires every field back, including
`choices[0].message.reasoning_content` and `usage.completion_tokens_details`;
`test_an_explicit_redaction_is_dropped_and_named` forces a redaction and
requires it dropped and named) plus two mutation rows
(`inference_archive_allowlist`, `inference_redaction_not_named`). Both new
checks failed against the pre-fix code. The spike mutation table is now 58 of 58
assertion-level catches with byte-identical restoration, and the full suite is
at 418 passed, 1 skipped, 2 warnings, against 414 and 1 before.

The user authorized one confirming service call. It ran on 2026-09-27 as
`--phase service`, exited 0, and wrote `slice12-service-20260927T000314Z.jsonl`
(seven records, source SHA-256 `5389c034...46f6`). One inference call: 45 prompt
tokens, 104 completion tokens, `finish_reason: stop`, HTTP 1,623 ms inside a
3,679 ms end-to-end disposable service request that emitted
`"tool": "stock_lookup"`; the estimated inference cost at the displayed rates is
0.00002766 USD, and the Sandbox operation reported `resources.cost` 0.00063545
in the same currency-less field as before. The archived payload is the whole
response: `content` `"\nSTOCK"` beside `message.reasoning`, 438 characters of
the model's working text, plus every other returned field (`prompt_text`,
`system_fingerprint` `vllm-0.22.0-b08c96cd`, `moderation`, `tool_calls`, and so
on). This establishes what the earlier records could not: the previously
invisible completion tokens were the model's reasoning text in the `reasoning`
field, and the provider returns `completion_tokens_details: null`, so that text
is not separately counted in usage. The six trial observations and the escape
run's records from before the repair stay incomplete and cannot be repaired
retroactively; the escape run's two empty completions still cannot be told apart
from a purposeful refusal on archived data alone, and this call did not re-test
those harder prompts. The record was re-scanned with the harness's own
`no_secret_leak` on the parsed records and the raw text; both pass.

### Reset phase live run: 2026-09-27 (one authorized live step)

The user authorized the reset phase only. It ran once as
`.venv313/Scripts/python.exe -m demos.gateway_spike --phase reset`, exited 0 at
`2026-09-27T00:03:31Z` UTC, and wrote `slice12-reset-20260927T000331Z.jsonl`
(ten records, source SHA-256 `5389c034...46f6`).

- `reset_seed`: a non-disposable run wrote `/tmp/slice12-reset-marker.txt`
  (`SEED_WRITTEN`, exit 0) and produced checkpoint image
  `b7c5c81d-447e-47f1-b620-1a711e4a865e`, the sixth non-deletable image (the
  `whoami` permission set still has no delete).
- `reset_from_base`: a disposable run from the public base image printed
  `False`, so a fresh instance does not see the marker.
- `checkpoint_readback`: a disposable run from the checkpoint image printed
  `True`, and `inspect_image_download` returned exactly 14 bytes equal to
  `SLICE12_MARKER`.
- `terminated_stdin_reuse`: sending `reuse\n` to the seed operation's closed
  stdin returned HTTP 409. This is the same run's just-finished operation, a
  different claim from the reuse phase's cross-run 409; both reject.
- No inference call ran. The three operations reported `resources.cost`
  0.00019813, 0.0001896 and 0.00014546 (sum 0.00053319) in the currency-less
  field, and no account charge was inspected. The ten records were re-scanned
  with the harness's own `no_secret_leak` on the parsed records and the raw
  text; both pass.

This closes matrix clause 9 and the last F5 items: a base image does not see a
checkpoint's marker while the checkpoint does, and the marker file survives
byte-exact under the normal 16 MiB cap.

### Final matrix, hostile probes and stop verdict: 2026-09-27

Every clause of the Slice 12 working matrix now has an archived record. File
names are in this directory; the 2026-09-26 runs are the `slice12-<phase>-` and
`slice12-live-` files, and the 2026-09-27 runs are the `judge`, `service` and
`reset` files.

| Clause | Evidence | Outcome |
| --- | --- | --- |
| 1 exact model/image/settings | `whoami` and spawn records in every run; the settings block in each `nemotron_inference` | public `python:3.11-slim` image `c7ad32fe-8621-3cd2-9022-521c6da02ac1`, `networking.enabled=false`, model `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `temperature=0`, 256-token ceiling, per-phase timeouts and layer caps |
| 2 request interpretation and tool choice | `service_capture` stdout in the `service`, `trials` and `escape` files | `"tool": "stock_lookup"` for the public request in the original run, all six trials and the confirming call; the adversarial request mapped to `none` |
| 3 file transfer | `service_upload` and `pair_payload` | the uploaded service artifact returned its size and SHA-256; the 2 MiB payload digest matched before and after |
| 4 request streaming | the service `stdout` event stream plus the host stdin write in `service_capture` | the service streamed the bound `inference_request` line and the host streamed the choice back on subprocess stdin |
| 5 output/capture retrieval | `pair_run` control, `marker_readback_verdict` (appended in the `live` file), `capture_file_download` in `reset` | 2 MiB read back byte-exact under the 16 MiB cap; a 14-byte marker byte-exact twice |
| 6 cleanup | `marker_readback_cleanup` | `running_instances: 0`; a nonterminal run emits a cancel record by construction |
| 7 six-trial latency, usage and cost | `trials` | `PASS_SIX_TRIALS_FEASIBLE`, mean 3,898.7 ms, mean estimated 0.00003094 USD per trial |
| 8 dependency outage | `outage` | `PASS_OUTAGE_FAILURES_RECORDED` (transport `ConnectError`, provider HTTP 404) with zero business writes |
| 9 reset | `reset` | base `False`, checkpoint `True`, marker byte-exact, terminated stdin 409 |
| 10 crash | `crash_retention` in `controls` | `CAPTURE_BEFORE_CRASH` retained with inner exit code 7 and no automatic retry |
| 11 deadlines, resources and egress | `deadline` and `access_egress` in `controls`; the ceiling probe in `escape` | `timed_out` with signal 9; all three egress attempts failed; the output ceiling held at 256 tokens |
| 12 judge delivery route | `judge` | `PASS_JUDGE_ROUTE_READY` with the pinned offline and live commands and a nonempty evidence directory |

The six Gate 3 section 8 hostile probes, and what the archived records show:

1. No provider credential, controller path, host-only canary or other grant was
   reachable. The controls phase's absence checks each fired a positive control
   first, the cross-run reuse was rejected HTTP 409 (`reuse`), and the same-run
   terminated stdin was rejected HTTP 409 (`reset`). The protected-fixture limb
   is N/A, not PASS: a spike has no sealed cases, and the mounted sentinel is a
   positive control that is meant to be found.
2. No undeclared tool escaped and no limit gave way. The service mapped the
   adversarial answer to `none`, the direct over-long request stayed within the
   declared model and the 256-token ceiling, the deadline probe timed out with
   signal 9, terminated operations rejected new input twice, and the disabled
   networking flag was honoured for all three attempted endpoints. A grant
   calling a model directly is structurally absent: the host makes the only
   inference call, and the Sandbox holds no provider credential.
3. No secret was found on any scanned surface (service, escape, outage, reuse,
   trials, reset), and each scanner needle is self-tested in serialized form so
   the pass can fail. The inference record now archives the whole provider
   payload rather than a chosen field list.
4. A crash retained its completed capture (`CAPTURE_BEFORE_CRASH`, exit 7), and
   the independent review verified the SDK does not blind-retry POSTs.
5. Reset leaves no candidate-visible state: the base image printed `False`, the
   checkpoint printed `True`, and the marker downloaded byte-exact.
6. One historical observation reads as a success and stays unexplained: the
   original run's outer `SUCCESS` with stdout claiming a 2 MiB write and a
   0-byte checkpoint, confirmed archivally by the re-inspection. It was never
   reproduced under the repaired verifier, the cause is unproven, and the user
   adjudicated it on 2026-09-26 as recorded above.

**Stop verdict.** No section 8 hostile probe succeeded against the archived
evidence, and the six-trial and service results show the model doing the
reviewed in-service work under the fixed ceilings, so neither S12 Limits
trigger fires and the stop is resolved. The residual limits at the top of this
document stay attached to this verdict, and Slice 12 acceptance, later Slice 13
planning and any commit or push of this work remain the user's decisions.

Spend and residue at the verdict: estimated inference across all
`slice12-*.jsonl` records is bounded at **0.00861732 USD** against the 3.00 USD
cap, a conservative bound that sums worst-case reservations alongside actual
estimates rather than measured spend, and no account balance or charge was
inspected. Six non-deletable checkpoint images exist, the newest
`b7c5c81d-447e-47f1-b620-1a711e4a865e` from the reset seed; the permission set
has no delete.

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
re-approved.

**Supersession 2026-09-27:** this section was written under the stop rule. The
reset/branch readback, the terminated grant reuse checks (cross-run and
same-run) and the six live trial slots are now measured by the records above,
and the judge delivery route now has an archived offline check; only the
four-request-per-trial estimate remains a projection, because each trial made
exactly one customer request rather than four. The stop itself is resolved by
the final verdict at the top of this document, and S12 remains unchecked
pending the user's acceptance.
