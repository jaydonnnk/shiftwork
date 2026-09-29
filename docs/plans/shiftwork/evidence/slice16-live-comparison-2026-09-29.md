# Slice 16 single live comparison, 2026-09-29

Status: one authorized six-slot run completed. This is execution evidence for
S15's sealed comparison and S16's outcome policy. It does not select a candidate,
operate it, or prove customer or learning impact.

## Before the call

- Branch `shiftwork/slice-16` merged the two newer main commits. The operator-sealed
  manifest and family retained raw SHA-256
  `2391255db772f42577ad2676c16a39b85b5867923334155f5dd129e8f5930e3f`
  and `170dd925880b035c3a999512c982aaccaa2deda96e8d55950f4b7c14f0ce9a24`.
- On 2026-09-29 the [official Nemotron 3 Nano model card](https://tokenfactory.nebius.com/models/catalog/text2text/nvidia%2FNVIDIA-Nemotron-3-Nano-30B-A3B)
  displayed $0.06 per million input tokens and $0.24 per million output tokens.
  These are advertised approximate prices. The authenticated read-only models
  endpoint confirmed the configured model exists but returned no price fields.
- The [official Sandbox page](https://tokenfactory.nebius.com/sandboxes/about)
  advertised free use while in beta. The provider's billing page describes
  real-time credit debits but does not publish a separate Sandbox rate. Final
  invoice treatment was not measured here.
- The one-shot controller budget fixed six slots, at most twelve Sandbox operation
  attempts, eighteen inference call attempts, and $0.10 projected inference
  spend. It reserved 32,768 input tokens and 1,024 output tokens per possible
  call. At the checked rate, a full eighteen-call reservation projects
  `$0.03981312`, below the cap. The 32,768 input-token reservation is four times
  the gateway's 8,192-byte input ceiling, allowing margin for tokenization and
  message overhead. This is a projection at the advertised rate, not an invoice.
- `.venv313/Scripts/python.exe -m demos.slice16_live_comparison --preflight-only`
  returned `PASS` after checking current date, configured model, sealed raw hashes,
  credential presence and the absence of an earlier one-shot marker. It did not
  print a credential. The full offline suite before the run returned 566 passed,
  1 skipped, 2 warnings with `tests/packaging` excluded.

## One execution and independent readback

`.venv313/Scripts/python.exe -m demos.slice16_live_comparison` exited 0 and
created the ignored one-shot marker and database under
`artifacts/slice16-live-2026-09-29/`. It used a local diagnostic to prepare the
investigation, then the Token Factory adapter for the comparison. No second
comparison, paid retry or top-up was run.

| Readback | Result |
| --- | ---: |
| Reserved and completed slots | 6 / 6 |
| Sandbox operation attempts | 12 / 12 maximum |
| Captures and byte/digest-verified checkpoint readbacks | 18 / 18 |
| Controller request meters | 18 / 18 |
| Inference call attempts and persisted request rows | 0 / 0 |
| Projected inference spend at observed calls | $0 |
| Comparison outcome | COMPLETE |
| Per-candidate public / protected denominators | 6 / 3 |
| Per-candidate protected passes | 3 / 3 |
| Per-candidate useful completions and justified refusals | 4 and 2 |
| Eligible candidates | A and B |

The independent read-only audit
`.venv313/Scripts/python.exe -m demos.slice16_audit_live` exited 0 with
`verdict: PASS`; it counted the persisted operation observations, controller
meters, inference requests, captures and checkpoint readbacks. The controller
meters prove zero inference calls here. This run therefore does not measure
Nemotron answer quality or nonzero token usage. Candidate cost stays unknown;
neither candidate had a mandatory cost budget in this comparison. No candidate
was selected or operated.

The run budget is separate from candidate comparison metrics. It counts both
public and protected phases and increments before a Sandbox spawn or provider
request; failed attempts are not refunded. The one-shot marker prevents this
runner from repeating the run. Public API reservation with a live adapter and
no bounded budget now returns 409 before creating a comparison.

## Repair and offline proof boundary

- R2: a route-level candidate-label drift test first failed with `KeyError: 'B'`
  and now returns `NOT_COMPARABLE` with `candidates` in drift fields.
- R3: missing live controller meters first produced a misleading measured zero;
  the tests now require unknown service calls and usage. An unknown mandatory
  call budget blocks eligibility against a measured candidate. A complete
  controller meter proves a real zero. The live run produced all eighteen meters.
- The live budget tests reject a thirteenth operation, a nineteenth inference
  call, a wrong shape or rate, and a provider request after the cap. The route
  test rejects a live comparison without a budget before reservation.
