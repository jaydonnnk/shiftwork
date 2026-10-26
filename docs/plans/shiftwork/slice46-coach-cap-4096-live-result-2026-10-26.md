**Current S46 result, 2026-10-26 Asia/Singapore:** the approved coach-cap-4096 action
ran once and stopped at the retained 20-second coach deadline with no response
retained. All five actions and every unused remainder are CLOSED, without retry.
S46 remains INCOMPLETE and UNACCEPTED. No commit or publication occurred.

# S46 coach cap 4096 journey: actual outcome

The user approved the named action `s46-coach-cap-4096-journey-20261026` and its
US$1 all-in ceiling on 2026-10-26, exactly as pinned in
[the proposal](slice46-coach-cap-4096-live-proposal-2026-10-26.md). `approved.json`
matched the runner's expected packet, the pricing expiry was still in the future,
and no once marker or live store existed. Execution then proceeded once.

## What ran

| Counter | Actual |
| --- | --- |
| Credentialed entitlement reads | 1, all required Sandbox permissions true |
| Coach requests sent | 1 |
| Coach responses retained | 0 |
| Service inference calls | 0 |
| Sandbox operations | 0 |
| Selections or operations | 0 |
| Ledger and selection rows | identical to the prepared store |
| Reserved inference at stop | US$0.01351680, inside the US$1 ceiling |
| Actual billing | unknown |

## Measured outcome

The single coach request left the host with the pinned 6,505-byte body at
`max_tokens` 4096. The gateway's assist event is `FAILED` with
`failure_code` `ASSIST_TRANSPORT_FAILED` and `elapsed_ms` 20005, and
`output_tokens` is null. No `coach-metadata.json` exists, because the pinned
transport wrapper only writes response metadata after a response returns, and none
returned. The mechanism is [shiftwork/assist/gateway.py:159](file:///Users/jayd0/.codex/worktrees/s46-continuation/shiftwork/shiftwork/assist/gateway.py#L159)
through line 172: the client and the surrounding `wait_for` both bound the call at
`DEADLINE_S` 20, and any exception becomes `ASSIST_TRANSPORT_FAILED`. The runner's
`require(event.state=='COMPLETE')` then closed the action and every remainder
before any Sandbox operation, exactly as its stop rule requires.

The terminal store retains the one FAILED assist event, the unchanged ledger and
selection rows, and the closure record. `once.marker`, `live.db`, `terminal.db` and
`closure.json` exist, so `authorize()` refuses any replay of this action.

## Honest cause analysis

The receipt establishes that the 20-second deadline fired and that no response
bytes were retained. It does not establish why no response arrived. Two
explanations are consistent with it:

- A near-cap generation exceeded the retained deadline. The public catalog lists
  Super at 127 tokens per second, so a 4,096-output-token response can need about
  32 seconds of generation, beyond the unchanged 20-second coach deadline. The
  approved amendment raised only the output cap and explicitly retained the
  deadline, so this is a consequence of the amendment's own scope, not a defect in
  its implementation.
- Provider or network loss unrelated to the cap. Nothing in the retained evidence
  separates this from the first explanation, because a timed-out non-streaming call
  retains no partial output.

For contrast, the closed V2 action at the 1,024 cap returned in 6,453 ms with
`finish_reason` length, so the deadline was not binding there. This run shows no
truncation at 4,096 because it shows no response at all. The amended cap removed
the measured truncation cause offline; it does not establish that a full-cap Super
response fits the retained deadline.

## Limits and next step

This outcome is not evidence about repair efficacy, model reliability, learning
gain or S46 acceptance. It consumed one entitlement read and one coach request and
nothing else. Generated service code never ran on the host.

Any further live attempt needs a new scoped decision about the coach deadline, a
newly prepared and pinned proposal, and fresh named approval. This action's
remainder is CLOSED and cannot be resumed. Commits and publication remain
unauthorized.
