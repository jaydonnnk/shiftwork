"""Append-only hash-chained ledger (program design S3.5).

Slice 2 seals ONE real LedgerEventDraft into a hash-chained LedgerEvent and
verifies the chain on read. Each event's hash covers its own fields plus the
previous event's hash, so any edit to a stored event or to its ordering breaks
verification. The chain is synthetic scenario state, labelled as such; it is not
a claim about real revenue or real customer trust.
"""

from enum import StrEnum

from shiftwork import config
from shiftwork.domain import canonical
from shiftwork.domain.models import JsonValue, LedgerEvent, LedgerEventDraft


class ChainStatus(StrEnum):
    VALID = "VALID"
    BROKEN = "BROKEN"


def event_hash(
    *,
    seq: int,
    prev_hash: str,
    event_type: str,
    cause_refs: tuple[str, ...] | list[str],
    payload: dict[str, JsonValue],
    synthetic: bool,
) -> str:
    return canonical.content_hash(
        {
            "seq": seq,
            "prev_hash": prev_hash,
            "event_type": event_type,
            "cause_refs": list(cause_refs),
            "payload": payload,
            "synthetic": bool(synthetic),
        }
    )


def seal_draft(draft: LedgerEventDraft, *, seq: int, prev_hash: str) -> LedgerEvent:
    """Assign the next seq and compute this event's hash from its content + prev_hash."""
    digest = event_hash(
        seq=seq,
        prev_hash=prev_hash,
        event_type=draft.event_type.value,
        cause_refs=draft.cause_refs,
        payload=draft.payload,
        synthetic=draft.synthetic,
    )
    return LedgerEvent(**draft.model_dump(), seq=seq, prev_hash=prev_hash, hash=digest)


def append(
    drafts: list[LedgerEventDraft] | tuple[LedgerEventDraft, ...],
    *,
    prev_hash: str,
    start_seq: int,
) -> list[LedgerEvent]:
    """Seal drafts into ordered events; each hash chains to the previous (S3.5)."""
    events: list[LedgerEvent] = []
    seq = start_seq
    current_prev = prev_hash
    for draft in drafts:
        event = seal_draft(draft, seq=seq, prev_hash=current_prev)
        events.append(event)
        seq = event.seq + 1
        current_prev = event.hash
    return events


def next_seq(events: list[LedgerEvent]) -> int:
    return (events[-1].seq + 1) if events else 1


def next_prev_hash(events: list[LedgerEvent]) -> str:
    return events[-1].hash if events else config.GENESIS_HASH


def verify_chain(events: list[LedgerEvent]) -> ChainStatus:
    """Recompute every hash and link in order; any mismatch or gap is BROKEN."""
    expected_prev = config.GENESIS_HASH
    for position, event in enumerate(events, start=1):
        if event.seq != position:
            return ChainStatus.BROKEN
        if event.prev_hash != expected_prev:
            return ChainStatus.BROKEN
        recomputed = event_hash(
            seq=event.seq,
            prev_hash=event.prev_hash,
            event_type=event.event_type.value,
            cause_refs=event.cause_refs,
            payload=event.payload,
            synthetic=event.synthetic,
        )
        if event.hash != recomputed:
            return ChainStatus.BROKEN
        expected_prev = event.hash
    return ChainStatus.VALID
