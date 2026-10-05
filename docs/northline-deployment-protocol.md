# Northline deployment action protocol

Gate 3 amendment RE-APPROVED, 2026-10-04. The deterministic rule below has
been checked against every reviewed public request and all six approved v2
protected requests. Its driver header is implemented and verified offline.
The exact separately approved v2 packet is applied; v1 and original pins remain
unchanged. Evidence: `plans/shiftwork/slice22b-intent-v2-offline-checkpoint.md`.

The service receives one customer request and frozen public state. It must not
read controller task conditions or expected acceptance values.

## Stable intent from received inputs

Derive the key from the received request's `text` and `request_id`:

1. If text contains `counter intent TOKEN`, use that ASCII token literally.
   Tokens contain letters, digits, `_` and `-`, begin with a letter or digit,
   and are at most 256 characters. Sentence punctuation is not part of a token.
2. Otherwise, if text contains `visit V-NUMBER`, remove the hyphen in that
   visit token and prefix it with `northline-intent-`. For example, `visit V-11`
   produces `northline-intent-V11` on both initial delivery and retry.
3. Otherwise, use the received `request_id` literally. Distinct deliveries are
   distinct intents only when the customer text supplies no shared intent.
4. Reject malformed, overlong or conflicting explicit tokens. Never guess an
   intent, consult a task spec, or maintain a table keyed by protected cases.

The trusted driver also sends this value as
`X-Shiftwork-Intent-Key` on the service request, alongside its existing transient
request token. It derives the header from that received request alone, under
the same rule for both phases. Capture digests continue to bind the exact
original body. The header adds no grading rules or task specifications.

Use this key in a `WRITE_SLOT` operation. A repeat returns the same stable
commitment reference and makes no additional slot write. A customer-provided
prior reference can be echoed without writing, but does not prove that a prior
booking actually occurred. Keep that limit attached to the assessment.

## Booking assertions and receipts

The task result's top-level `commitment_ref` names the independently observed
final commitment. Optional `booking` claims have exactly this value shape:

```json
{"booking_date":"2026-10-04","commitment_ref":"example-service-reference"}
```

The date must equal the requested booking date. The reference must equal the
top-level reference and the observed final write. Claim `entity_ref` identifies
that slot. Claim `evidence_refs` contains exactly that write's trusted receipt,
and the envelope lists it. A retry may cite the earlier final-write receipt.
Where the only prior reference came from customer text, no executed receipt
exists: return the top-level reference without an unsupported booking claim.

Rolling back a final write fails, including on a later delivery. A provisional
write may be rolled back within that same visit before final confirmation.
Refusal, referral and retry labels cannot conceal a withdrawal.

The loopback resource kernel simulates bookings. These receipts establish
simulated actions and do not establish real customer bookings or live isolation.
