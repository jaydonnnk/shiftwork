# Slice 14: optional assistance after learner commitment

Status: implementation started 2026-09-27 on `shiftwork/slice-14` under the
user's explicit Slice 14 go-ahead. The user separately authorized the bounded
live check below. This record is not slice acceptance or evidence of a live run.

## Scope

1. Keep deterministic orientation before help. Require an owned source run and
   nonblank cause, falsifier and public test before any model request.
2. Reserve and count every help attempt before the gateway call. Bellwether
   permits three calls total across hint, diagnosis and patch proposal, with
   at most one patch proposal. Northline permits one hint only.
3. Record the requested model, public prompt, reply, provider-reported model,
   usage, latency, safe failure code and one accept/reject decision. A proposal
   never edits code, freezes, grades, selects or writes business consequences.
4. Show the event history and counters in the Investigate panel. Keep the
   original and revised learner entries. Recorded help is labelled as a double.
5. Hide the live Investigate form and result when Return or Away is selected.
   Keep the stale Return/Away planning copy for Slices 20 to 22, as directed.

## Offline proof

- Test the API and controller with a recorded gateway, including incomplete
  entries, mixed-role budget, one-patch cap, idempotency, failure consumption,
  private-output rejection, Northline restriction and no business writes.
- Test the live gateway request shape with local HTTP transport only. Run the
  sealed import and prompt guards against real assist source and an injected
  sealed sentinel.
- Run the browser demo at a local URL on desktop and mobile with a recorded
  hint and patch proposal. Run the offline suite without the packaging test,
  whose clean-environment check installs dependencies.
- Run `tests/assist/mutation_proofs.py` so each of the shared-budget,
  one-patch, Northline-role, private-output, stranded-assist and
  injected-client-deadline guards fails independently.

## Authorized live check and observed limit

The user authorized up to three live calls on 2026-09-27. The key was found in
the ignored local `.env` after the environment check. All three calls ran once
in a disposable preview; their observations and limits are in
`evidence/slice14-assist-live-2026-09-27.md`. The original call plan was:

- Use `NEBIUS_API_KEY` from the local environment without printing or saving it.
  Use `SHIFTWORK_ASSIST_MODEL` or the approved default Nemotron model through
  the existing Token Factory chat-completions endpoint.
- Use one disposable preview database and its recorded Bellwether service run.
  Make at most three learner-triggered assist calls: one `HINT`, one `DIAGNOSIS`
  and one `PATCH_PROPOSAL`, each after the learner's recorded investigation.
- Each request has temperature 0, at most 1,024 output tokens, an 8 KiB input
  ceiling and a 20-second deadline. No automatic retry. Stop after a failure
  or unexpected private-output guard result and preserve its consumed budget.
- Read back the event rows and record only the public prompt/reply, requested
  and reported model, observed usage, latency and safe failure code. Do not
  modify a real learner database or use Sandbox execution in this check.

The authorized three-call budget is exhausted. The live feedback exposed a
prompt grounding failure, so the controller now includes the public captured
response and the gateway asks the model to challenge unsupported premises.
The gateway now enforces a total deadline. These repairs are tested offline
only. Neither the recorded double nor the three
pre-repair live calls establish revised-prompt model quality.

## As-built deltas from Gate 3 section 3.2

The independent review of 2026-09-27 confirmed the shipped interfaces differ
from the as-designed sketch, with no behavior difference:

- `request_assist` ships as a controller keyword surface,
  `request_assist(conn, shift_id, investigation_id, role, *, message,
  client_request_id, gateway)`, which the API route composes; Gate 3's single
  `AssistRequest` parameter remains the as-designed shape.
- `AssistRequest.investigation_id` is optional as built so the S11 prediction
  gate can refuse a null investigation with its own 409 before the gateway
  denial, and `client_request_id` is a required field for idempotent retries.
- `AssistEvent` and `AssistEventView` carry the fields the Slice 14
  requirements need and the Gate 3 sketch omits: `client_request_id`, `state`,
  `failure_code`, `reported_model_id`, `input_tokens`, `output_tokens` and
  `elapsed_ms`; projections stay sanitized by the sealed-import and
  serialized-sentinel guards.

No gate change follows: the approved budget, one-patch cap, attribution-only
decisions, Northline policy and projection boundaries behave as specified.
