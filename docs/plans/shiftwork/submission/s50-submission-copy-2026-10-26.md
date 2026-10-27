# S50 submission copy, 2026-10-26

Offline draft at accepted S48 main `097bdbbdd27b9c04e22487503ee785f6edcd492e`.
S50 remains INCOMPLETE. These blocks are ready to copy into reviewed fields,
subject to the evidence limits below. Nothing was entered into Devpost.
Current authenticated field names and length limits remain unverified.

## Project name

Shiftwork

## Short description

Practice taking responsibility for an AI service. Explain a failure, compare
exact repairs, choose an eligible version, and carry its consequences into the
next shift.

Source: [approved problem and learning loop](../01-product.md#problem).

## Inspiration

An AI answer leaves someone responsible for checking whether the customer's
task was completed. Shiftwork gives people with basic coding skills a place
to practise that responsibility: inspect a failure, explain its cause, test
what would disprove the explanation, and own the repair they choose.

Source: [approved product](../01-product.md#problem). This is the product
rationale, not a participant quotation or measured demand.

## What it does

Shiftwork is a persistent engineering practice workplace. In Bellwether Books,
a fictional client, the learner investigates an AI service, records a cause
and falsifier, and compares saved repairs under shared requirements and starting
conditions. Mandatory failures block eligibility. The learner explicitly
chooses an eligible exact version, operates it, and inspects the next shift's
inherited version and checked synthetic consequences. Experiments cannot
rewrite operational history.

The guided path uses Read the failure, Explain it, Compare repairs, Choose,
and Next shift. Technical details expose the evidence behind those steps.
The fictional engineering role is practice, not a job-readiness credential.

Sources: [approved product](../01-product.md#approved-product-decisions),
[accepted S47 path](../workplace-3d/s47-publication-2026-10-25.md), and
[S48 hosted evidence](../slice48-release-checkpoint-2026-10-26.md#hosted-verification-and-acceptance-boundary).

## How we built it

The application uses one FastAPI process, SQLite, and an HTML and JavaScript
client with a locally served Three.js workplace. NVIDIA Nemotron 3 Nano on
Nebius Token Factory interprets bookshop requests into a constrained task plan.
The service acts on that plan without silently adding omitted tasks. Token
Factory Sandboxes execute the candidate service. Controller-owned checks
evaluate retained outputs and determine eligibility. The learner owns the
final version choice.

Sources: [architecture](../02-architecture.md),
[task-plan starter](../../../../shiftwork/fixtures/artifacts/bookshop/task_plan_starter_service.py),
[hosted composition](../../../../shiftwork/hosted.py), and
[S48 model evidence](../evidence/slice48-release-2026-10-26/release-proof.json).

## What the retained evidence shows

S48's accepted hosted release includes a guided browser path and one closed
live diagnostic. That diagnostic completed the required collection and
alternative tasks. Optional price output was absent. It did not include a
comparison, explicit selection, selected operation, or inheritance chain.

An earlier operator-authored S45 comparison retained all declared public
batches. A passed 7 of 9 and B passed 9 of 9. Both passed 3 of 3 protected
phases, and only B was eligible. The operator explicitly selected B. Passing
batches include justified refusals. These are results for those versions and
conditions, not learner results, general reliability, or a model ranking.

Sources: [S48 closed smoke](../slice48-release-checkpoint-2026-10-26.md#published-release-and-closed-smoke),
[S45 actual results](../evidence/slice45-revised-live-2026-10-24.md#actual-results),
[S45 comparison JSON](../evidence/slice45-revised-live-2026-10-24.json), and
[S45 selection JSON](../evidence/slice45-selected-b-2026-10-24.json).

## Challenges and limits

Sandbox completion and a usable model response are separate observations.
The earlier S44 diagnostic retained output-limit failures with null answer
content. We preserve failed attempts, public results, protected checks, and
eligibility separately. A successful repair in one workload cannot establish
learning gain or general model reliability.

S49 has no verified participant results in this packet. Synthetic agent checks
would remain synthetic. S46 is CLOSED INCOMPLETE and UNACCEPTED, so this draft
makes no successful coach-repair claim and the planned video omits the coach.
The new S50 hosted recording, reviewed export, and public video remain pending.

Sources: [S44 retained evidence](../slice44-checkpoint-2026-10-24.md#retained-live-evidence),
[S49 contract](../04-slices.md#slice-49-five-short-learner-sessions), and
[current S50 boundary](../slice50-continuation-2026-10-26.md).

## Model and platform feedback

### Model and use

`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` through Nebius Token Factory interprets
fictional bookshop requests into allowed task and tool plans. The service uses
the returned plan, and independent checks assess the resulting customer tasks.

### Tuning and comparison

Prompt-engineered. No fine-tuning is evidenced. S45 compares service repairs
under the same Nano configuration, not different models. Its candidates also
use different prompts, so the result does not isolate the validator's effect.

### Useful feedback

Token Factory inference and isolated Sandbox execution let us retain the
model plan beside the checked service output. Retained failures exposed empty
replies at the output limit and incorrect task boundaries in a later repair.
Clearer output-budget diagnostics and more reliable task adherence would help.
These observations are bounded to the retained workloads.

### Nebius capabilities

Token Factory inference API and Token Factory Sandboxes. The controller runs
on Render. We claim no AI Cloud GPU deployment, Serverless Jobs, Serverless
Endpoints, DevPods, autoscaling result, or measured development-speed gain.
Actual billing and total Sandbox charges are unavailable.

Sources for these answers: [S44](../slice44-checkpoint-2026-10-24.md#retained-live-evidence),
[S45 exact action](../evidence/slice45-revised-live-2026-10-24.md#authority-and-exact-action),
[S45 costs and limits](../evidence/slice45-revised-live-2026-10-24.md#calls-timing-and-cost),
and [S48 release](../slice48-release-checkpoint-2026-10-26.md#hosted-verification-and-acceptance-boundary).

### Tavily

No, for current app-runtime use. Historical S26 used Tavily in an operator-only
curation CLI and retained `DROP_TAVILY_CLAIM`. Curation is outside the learner
runtime. We claim neither discovery benefit nor bonus qualification, and add
no call for qualification.

Sources: [S50 decision](../04-slices.md#slice-50-video-and-submission-text),
[curation boundary](../02-architecture.md#11-tavily-mission-curation-boundary),
and [historical manifest](../evidence/test3-manifest.json), `/outcomes`.

## Links and entrant inputs

- Track: Best Apps and Agents.
- Demo candidate: [shared practice demo](https://shiftwork.onrender.com).
  S48 verified it previously. This preparation made no runtime request.
  The free host sleeps, and its shared ephemeral database can reset or change.
- Source candidate: [Shiftwork repository](https://github.com/jaydonnnk/shiftwork).
  Recheck anonymous access and visible license before submission.
- Public YouTube URL: ______.
- Quality rating: ______. Recommendation rating: ______. Experience rating: ______.
- Submitter type, country, representative, eligibility, ownership, and
  new-versus-existing project declaration: ______.
- Optional IRL city and attendance declaration: ______.

Do not infer entrant declarations or ratings from test counts or Git history.
Do not paste internal source citations as participant endorsements.

## Rules verified now and remaining boundary

The [official rules](https://nebiusglobalaihackathon.devpost.com/rules), sections
1 and 4, and [overview](https://nebiusglobalaihackathon.devpost.com/) were read
live on 2026-10-26. Submission closes 2026-10-30 at 10:00 PDT, which is
2026-10-31 at 01:00 Singapore time. Judging ends 2026-12-15 at 12:00 Pacific,
which is 2026-12-16 at 04:00 Singapore time. Free judge access must continue
through that endpoint. The public overview confirms the selected track.

Required materials include a working-project link, public licensed source,
English description, tool feedback, and a public YouTube demonstration.
S50 requires a measured export strictly below 180 seconds. The authenticated
form and its current field limits were not accessed. The historical 35 MB
upload observation is not a current verified limit.

Retained local evidence was inspected and rehashed, including all 40 entries
in [the current audit](s50-current-source-audit-2026-10-26.json),
`/current_sources`. Its deployment and pricing observations remain earlier
receipts, not checks repeated here. No new host, provider, Sandbox, recording,
publication, or submission action ran. Use the
[recording checklist](s50-recording-checklist-2026-10-26.md) before seeking
approval for a concrete new action.
