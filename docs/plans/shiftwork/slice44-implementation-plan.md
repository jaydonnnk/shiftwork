# S44 implementation and evidence plan

Authority: S44 go-ahead in chat on 2026-10-24. The user said,
"GO ahead and the spend ceiling is roughly 5 bucks i have 27 bucks in token factory call count is based on call spending so go ahead and start s44 for reals".
The earlier "Yes it has my go ahead" authorizes this branch and offline work.
No commit, merge, push, deployment, installation or pinned-material edit is authorized.

Contract: Gate 4 Slice 44 and Gate 3 obligations 62 and 68, diagnostic arm.
The pinned mission has one public request. Fix the batch at ten repetitions,
at most ten Nano calls and ten Sandbox operations, with no retries. The user's
latest instruction delegates the call count to the spending limit. Treat $5 as
a hard inference ceiling, not a target. Sandbox billing remains unknown; do not
claim this meter can bound unknown vendor charges. No live call until the
credential environment and a conservative inference projection pass preflight.

Use the existing SQLite experiment, context, run, capture and assessment rows.
Freeze the public repetition count in the hashed context before queuing all runs.
Each repetition has a fresh workspace and its own retained output and assessments.
There is one diagnostic reservation, no protected draw and no eligibility.
Keep old single-run diagnostics and comparison behavior unchanged.

- [x] Reproduce the full Python and S43 mutation baselines.
- [x] Add failing API and stored-evidence checks for declaration, idempotency,
  changed counts, complete retention and independently derived miss totals.
- [x] Implement diagnostic repetition reservation, sequential execution, complete
  summary refusal and the controller-owned operation/call/spend meter.
- [x] Show the frozen count, progress, every repetition and per-task misses in
  the diagnostic panel, with the one-model/request-set/small-sample limit.
- [x] Add a provenance-bound capture import/replay path. Refuse missing or
  mismatched captures, retain RECORDED_INSPECTION and no eligibility. Never
  silently replay v1 captures as v2 output.
- [x] Kill each new guard with a named-assertion mutation, restore exact bytes
  and rerun clean. Inspect desktop and mobile rendered output.
- [x] Record live authority and frozen shape in 00-status before any call.
  Run once, retain every reply, parse, failure and check. If all required tasks
  are present in every reply, stop for the user's defect decision.
- [x] Replay the same retained captures offline, report actual usage plus cost
  limits, run the full regression and diff check, then architect cleanup.

Review focus: partial batches must not get a denominator; failed calls consume
budget; duplicate workers must not execute again; changing the declaration must
not reuse an idempotency key; transport failures must not be called model misses;
replay provenance must identify the actual starter and mission.

Initial verification: main and origin/main both 1c2a6a2, clean, verified before
creating shiftwork/slice-44. Credential presence check found none of
NEBIUS_API_KEY, NEBIUS_PROJECT_ID, CONTREE_TOKEN, CONTREE_PROJECT or
NEBIUS_AI_PROJECT. Values were never printed. Python is .venv/bin/python on
macOS. Baseline runs are in progress; do not infer their result from old notes.

The user then identified the existing credential source: "they are in .env.local".
The local launcher loads only relevant assignments into its process environment,
without printing them or installing dotenv. Presence, project format and six
Sandbox permissions passed. The room at http://127.0.0.1:8445 has all other live
actions disabled. This preflight sent no model request or Sandbox spawn.

Verified live outcome: ten calls, five empty replies at the 1,024-token cap with
SCHEMA_INVALID, five valid plans completing both required tasks. This is an
output-budget incident. No semantic omission claim follows. The same ten
captures replay offline with RECORDED_INSPECTION and identical evidence.
See slice44-checkpoint-2026-10-24.md for usage, retained paths, proof and limits.
Acceptance remains pending; S45 has no go-ahead.
