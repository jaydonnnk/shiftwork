# Northline Bike Cooperative: deployment brief

DRAFT FOR OPERATOR REVIEW. Fictional requirements, not a customer interview.

You are a Forward Deployed Engineer helping the co-op connect its booking
widget to repair slots. The integration starts blank. You own the code,
discovery record, permissions map, visible tests and runbook.

## Conflicting requirements

- Counter request C-01: keep the queue moving and confirm quickly.
- Co-op policy P-01: a final confirmation requires current parts stock and a
  mechanic slot. Speed cannot waive either check.
- Mechanic policy P-02: an uninspected brake or steering safety question goes
  to a human mechanic. The integration gives no riding assurance.
- Widget ticket W-01: a dropped reply can cause a second delivery of the same
  intent. Keep one stable booking and do not retract an existing confirmation.
- Access policy P-03: read parts availability and mechanic schedules; write
  repair slots only. No payment, account or customer-history access.

## Frozen fixture interface

The snapshot clock is 2026-10-03T01:00:00Z, Asia/Singapore. Dates and revisions
come from frozen inputs, never today's live clock. The shared state schema uses
title/edition/genre for resource label/revision/resource type; stock is parts
quantity, and availability.collection_date/can_collect means the slot date and
mechanic availability. These are internal compatibility keys, not book data.
No price records are supplied. Request conditions declare the slot, part,
idempotency key and access boundary to be independently checked.

Do not treat a response's booking claim as proof of a real write or a tool log
as verified access. Independent commitment/access assessment is required before
this material can support acceptance. No repair system, customer account or
payment service is connected by this draft.

## Your work

1. Record the requirements conflict and one cause, falsifier and visible test.
2. Fill your discovery record and permissions map from the public sources.
3. Build two distinct integrations and state their intended tradeoff. An
   optimistic provisional path must still honor P-01 before final confirmation;
   a conservative path may wait or refer when necessary information is absent.
4. Compare both under the same three public pairs and independent protected
   checks. Saving, diagnosing or comparing never selects an operating version.
5. After an eligible explicit choice, operate that exact version in a later
   shift. Full acceptance is required before any synthetic pilot booking or
   rollout approval. Record the selected runbook and unresolved incidents at
   handover. A later alternative experiment cannot rewrite that history.

One hint per shift, no patch proposal and no worked solution. The role is
fiction; no job-readiness, certification or learning-transfer result is claimed.
