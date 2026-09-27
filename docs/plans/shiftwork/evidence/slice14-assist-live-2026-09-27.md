# Slice 14 live assist check: 2026-09-27

Status: three authorized Token Factory calls completed in one disposable
Bellwether preview. This is live gateway evidence for the original S14 prompt,
not model-quality acceptance or a live check of the later prompt repair.

## Authority and setup

- The user authorized at most one HINT, one DIAGNOSIS and one PATCH_PROPOSAL,
  with 1,024 output tokens and 20 seconds per call, no retry. All three were
  used. No more live calls are covered by that authorization.
- The key was loaded in process from the ignored local `.env`. Its value was
  never printed, stored in this file or sent in the prompt. The database was
  created under a temporary directory and disposed after the run.
- The service run was recorded inspection, not fresh service execution. The
  source request at ordinal 1 was: "Do you still have the hardback of Dune on
  the shelf?"
- The probe's learner cause incorrectly said the router answered price but
  skipped collection and alternatives. Its falsifier and public test also
  discussed those extra tasks. This mismatch was my probe setup error, not a
  demonstrated learner behavior.

## Observed call records

Requested and provider-reported model for every call:
`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`. The gateway requested temperature 0,
max 1,024 output tokens and a 20-second deadline. The provider reported these
usage counts; no bill or charge was inspected.

| Role | State / failure | Input tokens | Output tokens | Elapsed ms | Response observation |
| --- | --- | ---: | ---: | ---: | --- |
| HINT | COMPLETE / none | 196 | 559 | 3,757 | Treated shelf availability as a collection task and advised checking alternatives, although the customer did not ask for alternatives. |
| DIAGNOSIS | COMPLETE / none | 198 | 387 | 2,919 | Restated the learner's asserted cause and gave a refuter equivalent to finding complete answers. It did not test the premise against the request. |
| PATCH_PROPOSAL | COMPLETE / none | 203 | 558 | 4,358 | Suggested revising the cause, falsifier and public test. It did not propose a service repair. |

The returned station view showed `assist_used=3`, `assist_limit=3` and three
events. No provider call failed, no automatic retry ran, and no model output
was applied as code, grading, selection or business history. The exact raw
response bytes were not retained after the disposable database closed; console
output replaced some non-ASCII punctuation, so the response observations above
are summaries rather than a byte-exact transcript.

## Adjudication and repair boundary

The three calls prove live routing, model identity and returned usage/timing for
one request shape. They do not establish useful diagnostic advice. The prompt
sent the request and learner reasoning but omitted the captured service
response, so a model could not inspect what the service actually did. After the
calls, the controller was changed to include the captured public response,
reject private response text before a provider call, and count the system
message inside the 8 KiB preflight. The gateway instruction now tells the model
to challenge a mismatched learner premise and to suggest a service repair for
PATCH_PROPOSAL. Offline tests cover that request shape and guard behavior.

The revised prompt has not received a live call. Its effect on model quality
remains unknown. The live calls used the original HTTPX per-operation timeout;
all observed elapsed times were below 20 seconds. Afterward the gateway was
changed to enforce a 20-second total call deadline. Its success and timeout
paths are covered by local mock transport tests, not a new provider call. The
three-call authorization is exhausted.
