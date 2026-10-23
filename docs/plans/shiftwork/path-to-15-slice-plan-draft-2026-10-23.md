# Path to 15/20: draft slice plan, 2026-10-23

**Status: DRAFT for review. Not approved.**
This draft authorizes nothing: no code, live call, spend, outreach, deployment, fixture seal or gate change.
Each slice below still needs its own go-ahead, and S43 and S46 change approved architecture, so they need a scoped Gate 2 and Gate 3 backtrack first.

## 1. Why this plan exists

An independent read-only judge pass on 2026-10-23 scored the current build 9/20 (Technology 2, Design 2, Impact 2, Idea 3).
The main finding: in the product path Nemotron picks one of two tool names, and the guard code completes the task whatever it picks (`shiftwork/fixtures/artifacts/bookshop/compare_repair_model_service.py:1-12`).
All ten calls in the successful S20 chain chose `public_record_lookup`.
The target is 15/20: Technology 4, Design 4, Impact 3, Idea 4.
These are judging guesses, not measured outcomes.

| Criterion | Now | Target | Slices that move it |
|---|---|---|---|
| Technology | 2 | 4 | S43, S44, S45, S46 |
| Design | 2 | 4 | S47, S48 |
| Impact | 2 | 3 | S49 |
| Idea | 3 | 4 | S43, S44 (the lesson is a real model failure) |

## 2. Fixed constraints

- Deadline: Devpost closes 2026-10-30 at 10:00 AM Pacific Time.
- Budget: only Token Factory credits (about $27 recorded in the S28 route revision). No Nebius Console spend, so Serverless Endpoints and Jobs stay out of scope.
- Hosting stays on the existing free Render service. Sandboxes have no public ingress.
- The evaluator, sealed cases, ledger rules and selection stay deterministic and controller-owned. Nemotron never reads or grades them.
- The learner owns the cause, falsifier, tests, repair code and final choice. Coach output stays labelled and attributable.
- Recorded output is never presented as live.
- Bellwether carries the demo. Northline and Stonebridge stay as they are.
- S42 (robot crew) is finished as recorded in its checkpoint. No further 3D work before submission.

## 3. Dependency order

| Day | Slice | Needs live calls | Can run in parallel with |
|---|---|---|---|
| Oct 23 | Gate 2/3 scoped backtrack (docs only) | No | S47 |
| Oct 24 | S43 Nemotron-led starter, offline | No | S47 |
| Oct 25 | S44 live trial batch | Yes | S47 |
| Oct 25-26 | S45 pass-rate comparison | Yes | S47 |
| Oct 26-27 | S46 coach agent loop | Yes | S48 |
| Oct 24-27 | S47 guided first-run path | No | S43 to S46 |
| Oct 27-28 | S48 redeploy main, judge README | Yes (one smoke call) | S49 |
| Oct 26-28 | S49 five learner sessions | Yes (hosted) | S48 |
| Oct 28-29 | S50 video and submission text | Yes (recorded run) | None |
| Oct 29-30 | Buffer | | |

**Cut line if time runs short:** S43, S44, S45, S47, S48 and S50 are the minimum.
Without S43 and S44 the Technology score stays near 2 and 15/20 is out of reach.
S46 is the first slice to cut, then S49.

## 4. Slice exit contracts

### S43: Nemotron reads the request and decides the path (offline)

- **Working result:** a new Bellwether starter service where Nemotron Nano interprets each customer request into strict JSON (`{"tasks": [...], "tool": "..."}`), choosing from four or five public tools (for example record lookup, catalog search, collection slots, alternative search, price lookup).
The service acts only on that JSON.
No guard code completes tasks the model missed.
A malformed or wrong parse produces a visible failed check, not a silent rescue.
- **Starter defect:** the starter prompt does not list the required task types, so the model can drop a task (for example the conditional alternative in a "collect" request).
Whether and how often that happens is unknown until S44 measures it.
- **Demo:** the recorded adapter replays labelled model replies and the offline journey runs end to end with the new starter.
- **Tests (fail-capable, each guard mutated once):**
  - a model reply that omits a required task fails the matching deterministic check;
  - a tool name outside the allowlist is refused by the gateway;
  - invalid JSON becomes `MALFORMED_RESPONSE`, never a pass;
  - deleting the "no rescue" rule (re-adding guard completion) makes a test fail;
  - the recorded replies are labelled `RECORDED_INSPECTION` in every surface.
- **Limits:** recorded replies are fixtures authored by the operator, not observed model behavior.
- **Authorization needed:** Gate 2/3 backtrack approved; slice go-ahead; operator review and seal of any new request fixtures.

### S44: live trial batch, real variation becomes the incident

- **Working result:** the starter runs each of the six Bellwether requests k times (proposal: k = 10) through the live Sandbox and Nano.
The run keeps every reply, parse and check result.
The board shows a per-request miss rate, for example "collection task missed in 7 of 10 trials", built only from observed results.
The incident the learner diagnoses comes from these observed misses.
- **Falsifier:** if Nano never misses a task across the batch, the starter defect is not real.
Then stop and choose with the user: harder reviewed request shapes, or a different defect. Do not script a failure and present it as a model failure.
- **Tests:** a variation summary built from fewer than k retained results is refused; a summary number that does not match the retained rows fails; the meter stops at its ceiling.
- **Cost estimate:** 60 Nano calls at roughly 100 input and 150 output tokens.
At the projection rates in `shiftwork/hosted.py` that is under $0.01.
This is an estimate from existing projection rates, not a vendor quote.
- **Authorization needed:** slice go-ahead plus an explicit call count and spend ceiling.

### S45: repairs compared on pass rates, not single runs

- **Working result:** the existing paired comparison runs each learner repair (prompt wording, schema, validation, fallback rule) k times under the same requests and conditions.
Eligibility needs every mandatory check passed in every trial; efficiency is compared only after that.
The choose screen shows "A: 10 of 10 complete, B: 6 of 10" with links to each retained trial.
- **Tests:** a candidate with any mandatory failure in any trial is ineligible; trial counts must match between candidates or the comparison is `INCOMPLETE`; changing one retained trial changes the shown rate.
- **Limits:** k trials on six requests is a small sample. The UI says so.
- **Authorization needed:** slice go-ahead plus call count and ceiling (estimate: 120 Nano calls, under $0.02 at the same projection rates).

### S46: coach agent loop after the learner commits

- **Working result:** after the learner records a cause and falsifier, an optional coach on a larger Nemotron model (Super, or Ultra if Token Factory lists it) runs a bounded loop:
read the public trace, propose one labelled patch, run it in the Sandbox against the learner's public tests only, report the pass rate.
The learner accepts the patch as a new saved version, edits it or rejects it.
A coach patch must still go through S45's comparison before anyone can choose it.
- **Tests:** the coach is refused before cause and falsifier exist; the coach never receives sealed cases, evaluator code or credentials (leak scan with a self-test needle); a coach patch is marked as coach-authored in the version history; the loop stops at its step and call limits.
- **Open question:** which larger Nemotron models Token Factory serves today and at what rate is unverified. Check before the go-ahead.
- **Authorization needed:** Gate 2/3 backtrack approved; slice go-ahead; model choice; call count and ceiling.

### S47: guided first-run path in plain language (offline)

- **Working result:** a first-run mode with five steps, one panel at a time: Read the failure, Explain it, Compare repairs, Choose, Next shift.
Hashes, run IDs and evidence-mode codes move behind a "Technical details" toggle.
Evidence modes get plain labels ("replayed recording", "ran live in a sandbox").
Fix the overlapping room labels and the empty dark area at 1440px, and keep the skip link hidden until it has focus.
- **Tests:** browser checks at 1440x900, 1280x720 and 390x844 that labels do not overlap and no hash text is visible by default; the toggle reveals the same values; existing journeys still pass.
- **Authorization needed:** slice go-ahead.

### S48: redeploy main and rewrite the judge path

- **Working result:** main is deployed to the existing Render service with both credentials set, so the hosted demo matches the code judges read.
The README opens with a five-line judge path and the model, Sandbox and Token Factory explanation; slice history moves to `docs/`.
- **Tests:** existing hosted checks against the deployed URL; one live smoke diagnostic; a recorded wake from sleep.
- **Authorization needed:** deployment and one live smoke call.

### S49: five short learner sessions

- **Working result:** five people with basic coding skills each try the hosted guided path for about 20 minutes.
Record task completion, whether they named the observed cause, time taken and one quote each, with consent.
Report the real numbers, including weak ones.
- **Limits:** five sessions show usability, not learning gain. No comparison group.
- **Authorization needed:** outreach and recruitment; a consent note; live call ceiling for the hosted sessions.

### S50: video and submission text

- **Working result:** a video under three minutes of one live hosted run:
model miss observed, learner explains, coach proposes, Sandbox comparison on pass rates, learner chooses, next shift inherits.
Submission text and model feedback answers are filled only from retained calls.
The Tavily answer is "no" unless a genuine runtime call ships, which this plan does not include.
- **Authorization needed:** live calls for the recorded run; YouTube publication; Devpost submission.

## 5. Open decisions for the user

1. Approve the scoped Gate 2/3 backtrack for S43 and S46, or keep Nemotron's role as is (then 15/20 is unlikely).
2. Trial count k (proposal: 10) and the total live call ceiling for S44 to S46.
3. Coach model: Super, Ultra or skip S46.
4. Whether S49 outreach is acceptable this week.
