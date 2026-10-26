**Current S46 result, 2026-10-26 Asia/Singapore:** no live authority exists for this
proposal. All five historical actions and every unused remainder stay CLOSED. S46
remains INCOMPLETE and UNACCEPTED. Preparation made no authenticated request, no
provider call and no Sandbox operation.

# S46 coach deadline 60 journey: proposed, not authorized

**Subsequent approval recorded:** the user replied "Sure i approve" to the exact
named action and its US$1 all-in ceiling on 2026-10-26 Asia/Singapore.
`approved.json` exists in the proposed directory and equals the runner's expected
packet. This document's exact inputs, limits, expiry and stop rules remain
unchanged. Commits and publication were not part of this approval and remain
unauthorized. Execution outcome is recorded in
[slice46-coach-deadline-60-live-result-2026-10-26.md](slice46-coach-deadline-60-live-result-2026-10-26.md).

Prepared 2026-10-26 Asia/Singapore on `shiftwork/slice-46-continuation` from verified
main `1533cc4`, with both approved scoped Gate 3 amendments applied and uncommitted:
the 4,096 coach output cap and the 60-second coach deadline. The measured causes and
the offline proofs are in [the cap diagnosis](slice46-coach-output-cap-diagnosis-2026-10-25.md)
and [the closed deadline action's result](slice46-coach-cap-4096-live-result-2026-10-26.md).
This document supersedes only the closed V3 proposal's deadline pin; every earlier
input, outcome and closure stays exactly as recorded.

## Exact proposed action

Name: `s46-coach-deadline-60-journey-20261026`.

1. Read Sandbox entitlements once after fresh named approval.
2. Request one Super patch using the pinned corrected coach context at the amended
   4,096 output-token cap and the amended 60-second deadline.
3. Run its exact retained source once as a public diagnostic in the isolated
   Sandbox. Retain failed task checks as evidence. A completed diagnostic does not
   prove repair and cannot qualify a version.
4. As an explicitly labelled operator demonstration, copy the proposal into the
   draft after completed execution, even if task checks fail, then explicitly save
   B with one accepted coach patch and no learner-edit credit.
5. Compare A and B once through S45, with three public repetitions per pair and the
   existing protected checks. Preserve every result and missing repetition.

This action includes no source tuning, second generation, retry, selection,
operation, learner study, S46 acceptance, publication or deployment. Generated
service code executes only in the isolated Sandbox, never on the host. B's unknown
source becomes fixed by the one retained coach response and its hashes. There is no
advance claim that the proposal repairs the customer failure.

## Models, limits and pricing

| Boundary | Fixed setting or maximum |
| --- | --- |
| Coach | `nvidia/nemotron-3-super-120b-a12b`, one call, temperature 0, 4,096 output tokens, 60-second amended deadline |
| Coach input | 6,105 system/user UTF-8 bytes; unchanged 8,192-byte cap; exact HTTP body 6,505 bytes |
| Service | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, at most 43 calls, temperature 0, 1,024 output tokens |
| Service policy | Existing frozen reasoning-off permission and 45-second execution deadline; no coach reasoning-off option |
| Sandbox | At most 25 operations: one proposal diagnostic and 24 comparison operations |
| Other authenticated preflight | One entitlement read |
| Action time | 1,800-second execution budget, with remaining-time I/O bounds and checks before later stages; cleanup may finish afterward |
| Proposed all-in ceiling | US$1, separate from every closed historical allowance |

Current public rates per million input/output tokens are Nano US$0.06/0.24 and Super
US$0.30/0.90, re-read at 2026-10-26 00:55:21 Asia/Singapore. The catalog response is
byte-identical to the earlier reads at
`626d6327596f959a4db8f8802d5985c67c6f4bccdf8a7b6b70b57e9167614eee`, so no price
changed and both models remain listed active. The rendered Sandbox page still states
that beta runs do not consume credits; the retained rendered capture and screenshot
were taken earlier this same session at 00:10 Asia/Singapore and are re-pinned here
unchanged. These public reads are not authenticated entitlement or availability
evidence. Sources: [model pricing](https://tokenfactory.nebius.com/api/public/models_info)
and [rendered Sandbox beta terms](https://tokenfactory.nebius.com/sandboxes/about).

Conservative inference reservation is unchanged at US$0.10862592: a deadline change
alters no token count. It is US$0.0135168 for the coach (32,768 input tokens at 0.30
plus 4,096 output tokens at 0.90 per million), US$0.00221184 for the proposal
diagnostic and US$0.09289728 for the comparison, each service inference still
reserving 32,768 input and 1,024 output tokens. This is a reservation, not an actual
bill or a future price guarantee. This proposal expires at
2026-10-27 00:55:21 Asia/Singapore; later approval requires fresh public pricing
verification and a newly pinned manifest, without reusing an allowance.

## Frozen inputs and once-only controls

Only `live-proposal-v4/` is proposed, beneath the private continuation receipt root
recorded in [the implementation checkpoint](slice46-coach-context-progress-2026-10-25.md).
V1 to V3 remain preserved and superseded, and V2 and V3 additionally carry their own
closed live state, so neither is a source for this action.

The prepared store is a fresh copy of the pristine pre-action checkpoint
`/tmp/shiftwork-s46-20261025/proposed-live-v2/prepared.db`, byte-identical at the
digest below and verified unchanged before and after this preparation. Copying it
grants no old call authority. It contains the reviewed task-plan mission, exact
source A, the original investigation and one consumed recorded-inspection diagnostic
slot, so exactly one proposal slot remains. It has no coach event or qualifying
comparison. IDs remain local to each store.

- Prepared/source store SHA-256: `7bd6538756f372a6f23ae884a7f154ef7c0d39ef19d8c604e3fe944ea4428d04`.
- Mission SHA-256: `9defd8e35e2afc59b993095c706935a130f4dd70a3051ec484f5d38161fdd9d4`.
- A in this prepared store: `ver-0003`, artifact hash `fb394c5e18abe935edaec086932bfe9257b7aad867d68be68a1aa4414080c4a6`.
- Coach HTTP-body SHA-256: `a3dcbb074a93cbf1ee2db052347a4642515f0cfc89e47b07b72a538231be1b44`, carrying `max_tokens` 4096.
- Runner SHA-256: `6e3faab97064e408fc649c8a5adff7ab21ab212d34e1b68632c7eef79444cfc5`.
- Manifest SHA-256: `26c4aacb41989e5f55fc2cf600729413f3b77855c9e65970e21748a13fa6f2d4`.

The manifest also pins effective model, image and endpoint settings including
`coach_output_tokens` 4096 and `coach_deadline_s` 60, public request and workload
hashes, source files, installed runtime files, Python and lockfile, public prices and
rendered terms. The exact proposed approval packet is `approval-request.json`. It is
not authorization. No `approved.json`, once marker or live database exists in the
proposed directory.

The runner refuses missing or altered approval and any pin drift before reading
credentials. An exclusive once marker is claimed before the entitlement read. The
first coach/protocol, identity, execution, budget, deadline or missing-evidence
failure closes the action and every remainder. An irreversible failure latch
prevents the real adapter from making another provider call in the same batch. Wrong
or missing reported service-model identity also stops it. Sealing refuses a coach
output cap other than 4,096 or a coach deadline other than 60, and authorization
compares the live tree's effective settings, including both, against the sealed
manifest, so a reverted cap or deadline cannot reach a provider call. Ordinary
returned plan_failure remains service behavior and is assessed without hidden rescue
code. Intermediate stores, exact response and source bytes, deterministic reports,
counters and closure are retained. There is no retry or resume.

## Offline evidence and limits

- 62 authored controls pass, one more than V3: the new control proves sealing
  refuses a reverted 20-second coach deadline, and the literal pin control now also
  pins the tree deadline at 60.
- 40 independent private-runner source faults were injected one at a time, each with
  a passing clean control, exactly one intended assertion failure and a passing
  byte-identical restored control. The two new faults are the removed seal-time
  deadline guard and the deadline constant reverted to 20; each is caught only by the
  new sealing control. Receipts are `/tmp/shiftwork-s46-v4-faults/summary.json` plus
  each fault's clean, fault and restored pytest output, and the proposed directory's
  `guard-faults.txt` and `controls.txt`.
- Three repository mutation proofs were added for the deadline amendment and each
  returned FAIL_CAUGHT with byte-identical restoration: the constant reverted to 20,
  the async client timeout reverted to 20, and the absolute wait_for wrapper
  reverted to 20. Each is caught by exactly one named repository check, including a
  new check that a 21-second reply still completes.
- The amended tree's full offline regression passes 1,806 Python tests, one
  live-only skip, the exact installation deselection and two existing warnings, plus
  361 Node tests with zero failures. The two added Python passes are this
  amendment's new checks.
- Four uninterrupted S46 proposal journeys at desktop 1440x1000 and mobile 390x844,
  each at native Chrome 100% and 200%, passed on this tree with the amended cap, as
  recorded in the cap diagnosis. They predate the deadline amendment, which changes
  no rendered surface.

These are offline mechanics, safety and identity checks. They establish neither live
repair efficacy, general model reliability, learning gain nor S46 acceptance. The
60-second deadline removes the measured timeout cause of the closed V3 action; it
does not guarantee a valid patch, and a response slower than 60 seconds would still
close this action empty. No provider call, Sandbox operation, credentialed
entitlement read, installation, new selection or operation, Git staging, publication
or deployment occurred. The only external reads were the two unauthenticated public
pages named above.

The next dependent step is fresh named approval of this exact proposed action and
its US$1 all-in ceiling. Any changed request, model, source, store, runtime,
setting, limit or expired pricing requires a revised reviewable preparation.
