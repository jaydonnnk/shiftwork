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

    Existing families retain their historic family/id refs. The new comparison
    family binds its request ordinals and expected content, so an ID-only rename
    cannot turn an exposed comparison case into a fresh holdout.
    """
    if case.family == "task_completion":
        # This new comparison family has no legacy exposures to preserve. Its
        # identity binds content so a later refill cannot recycle a case by ID.
        identity = {"family": case.family, "request_ordinals": list(case.request_ordinals),
                    "expected": case.expected,
                    "stimulus": case.stimulus.model_dump(mode="json") if case.stimulus else None}
    else:
        identity = {"family": case.family, "case_id": case.id}
    return "var-" + canonical.content_hash(identity)[:16]


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


def select_pair_variants(
    family: str,
    cases: Sequence[SealedCase],
    exposed_refs: Iterable[str],
    *,
    pairs: int = 3,
) -> tuple[SealedCase, ...]:
    """One never-exposed variant per pair, deterministically, for one comparison.

    The same ordering rule as ``select_variant`` applies variant by variant: the
    lowest request ordinal first, file order breaking ties. The first ``pairs``
    unexposed variants are returned in pair order, so pair 1 and pair 2 never
    receive an ordinal bound to a later pair's request when an earlier one is
    available. Fewer available variants than pairs raises ``RotationUnavailable``
    and refuses the whole comparison rather than partially reserving it.
    """
    ordered = sorted(
        unexposed_cases(cases, exposed_refs),
        key=lambda case: (min(case.request_ordinals), list(cases).index(case)),
    )
    if len(cases) < 6 or len({variant_ref(case) for case in cases}) < 6:
        raise RotationMisconfigured(
            f"comparison family {family!r} requires at least six distinct reviewed variants"
        )
    if len(ordered) < pairs:
        raise RotationUnavailable(
            f"rotation group {family!r} holds {len(ordered)} never-exposed variant(s); "
            f"a qualifying comparison reserves {pairs}"
        )
    return tuple(ordered[:pairs])


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
