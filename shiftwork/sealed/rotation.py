"""Draw-without-replacement policy for sealed rotation groups (program design S2, S5.3, S7.1).

A family is a rotation group of variants (sealed cases). Each attempt draws one
never-exposed variant per enabled family, deterministically: the lowest unexposed
request ordinal wins, file order breaks ties. Determinism is the point - a retry
or a restart must not be able to redraw an exposed stimulus, and "unseen" must not
depend on chance.

Exhaustion fails closed for the whole run (``RotationUnavailable``); recycling,
renaming or relabelling an exposed case does not create a new holdout. A refill
appends newly authored variants and increments the family's ``cycle`` without
touching a single exposure record, and retiring a compromised group is a state
change on existing draws, never a deletion (ADR 0001).

This module is policy only: no file, database or network access. The caller loads
cases and exposure rows and persists the returned decisions.
"""

from collections.abc import Iterable, Mapping, Sequence

from shiftwork.domain import canonical
from shiftwork.domain.errors import RotationMisconfigured, RotationUnavailable
from shiftwork.evaluator.evaluator import SealedCase


def variant_ref(case: SealedCase) -> str:
    """Opaque, stable identity of one variant; never reused within an engagement.

    The digest covers the family and the case id, so a relabelled copy of an
    exposed case still collides and can never count as a new holdout.
    """
    return "var-" + canonical.content_hash({"family": case.family, "case_id": case.id})[:16]


def unexposed_cases(cases: Sequence[SealedCase], exposed_refs: Iterable[str]) -> tuple[SealedCase, ...]:
    exposed = set(exposed_refs)
    return tuple(case for case in cases if variant_ref(case) not in exposed)


def select_variant(family: str, cases: Sequence[SealedCase], exposed_refs: Iterable[str]) -> SealedCase:
    """The never-exposed variant with the lowest request ordinal, file order as tiebreak.

    Raises ``RotationUnavailable`` when the family is exhausted: the whole run is
    refused rather than partially reserved.
    """
    available = unexposed_cases(cases, exposed_refs)
    if not available:
        raise RotationUnavailable(
            f"rotation group {family!r} has no never-exposed variant left; "
            "author and review new variants to continue"
        )
    return min(available, key=lambda case: (min(case.request_ordinals), cases.index(case)))


def shared_ordinal(draws: Mapping[str, SealedCase]) -> int:
    """The single request ordinal every drawn variant binds for this attempt.

    A run executes one stimulus prefix and each drawn case scores the response at
    its ordinal, so the draws must agree on exactly one ordinal. Disagreement is
    an authoring error surfaced as ``RotationMisconfigured``, never resolved by
    silently picking one.
    """
    tuples = {case.request_ordinals for case in draws.values()}
    if len(tuples) != 1:
        raise RotationMisconfigured(
            "drawn variants must share exactly one request ordinal; got "
            + ", ".join(f"{family}: {case.request_ordinals}" for family, case in sorted(draws.items()))
        )
    (shared,) = tuples
    if len(shared) != 1:
        raise RotationMisconfigured(f"a drawn variant binds several request ordinals: {shared}")
    return shared[0]


def validate_refill(
    new_cases: Sequence[SealedCase],
    exposed_refs: Iterable[str],
) -> None:
    """A refill must append genuinely new identities (program design S7.1).

    Reusing an exposed variant's identity - or repeating an identity inside the
    refill itself - is rejected: a relabelled copy is not a new holdout.
    """
    exposed = set(exposed_refs)
    seen: set[str] = set()
    for case in new_cases:
        ref = variant_ref(case)
        if ref in exposed:
            raise RotationMisconfigured(
                f"refill reuses the exposed identity of variant {case.id!r} ({ref})"
            )
        if ref in seen:
            raise RotationMisconfigured(f"refill repeats the identity of variant {case.id!r} ({ref})")
        seen.add(ref)
