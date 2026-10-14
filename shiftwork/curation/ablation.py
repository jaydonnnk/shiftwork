"""Frozen/known-page polling/Tavily comparison with the retained DROP rule.

Obligation 48 and the Slice 26 contract: the comparison covers the retained
historical corpus and returns ``KEEP_TAVILY_CLAIM`` only when every
pre-registered threshold and the executable-change rule pass; any unmet
threshold returns ``DROP_TAVILY_CLAIM``. A link-only or prose-only outcome
cannot be counted as a useful change, and a run whose only structural
discoveries are non-executable fails the executable-change rule by name.

The three arms (Slice 26 contract; ``docs/SHIFTWORK_PLAN.md`` S8):

- frozen curriculum: the static material already frozen for the missions. The
  corpus is defined by the preregistration as fresh changes, so this control arm
  covers none of them by construction; it is printed so the comparison is
  visible rather than implied.
- known-page polling: a retained watch list of known URLs, compared by content
  hash. Polling keeps known URLs: the watch list never grows, so structural
  events (whose pages are not watched) are invisible to it. Freeze validation
  enforces known-page events inside the watch list and structural events
  outside it.
- Tavily discovery: the live ``pipeline discover`` run. An event is found when a
  recorded frozen fixture attributes a qualifying candidate to it; it is useful
  when at least one such fixture is an executable change. The event's detected
  time is the earliest qualifying publication time among its attributed
  candidates (the retained selection rule).

Interpretation record (Slice 26, offline build), where the contract leaves
mechanics open:

- ``useful`` requires a frozen fixture of kind ``executable``. A fixture of kind
  ``prose`` or ``link`` can be recorded but never counts; if structural
  discoveries exist and none is executable, the executable-change rule fails.
- The review-cost thresholds are measured over the candidate sets of the useful
  structural fixtures only (the sentence they appear in is about the structural
  discovery bar), including rejected candidates in those sets.
- Integrity problems (unfrozen manifest, digest mismatch, results dated before
  the freeze, dangling references, missing reviews) refuse loudly instead of
  returning a verdict: they are protocol defects, not measured outcomes.
- The ``ablation`` CLI exits 0 for a completed adjudication, KEEP or DROP alike;
  DROP is a recorded outcome, not an error. Refusals exit 2.

This package is never imported by the runtime application; the isolation is
enforced by ``tests/curation/test_ablation.py``.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict

from shiftwork.curation.pipeline import (
    CurationError,
    CurationManifest,
    CurationOutcomes,
    FrozenChange,
    ManifestIntegrityError,
    MissionSource,
    MissionSourceState,
    Preregistration,
    host_allowed,
    iso_utc,
    normalize_url,
    parse_published_date,
    window_contains,
)

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class EventEvaluation(BaseModel):
    """One corpus event's arm-by-arm outcome, pure over manifest plus outcomes."""

    model_config = _FROZEN

    event_id: str
    domain: str
    kind: Literal["known_page", "structural"]
    polling_visible: bool
    tavily_found: bool
    tavily_useful: bool
    earliest_qualifying: datetime | None


class ThresholdCheck(BaseModel):
    """One pre-registered threshold or rule, measured against the outcomes."""

    model_config = _FROZEN

    name: str
    measured: str
    requirement: str
    passed: bool


def detect_changes(known_urls: Mapping[str, str], fetched: Mapping[str, str]) -> tuple[str, ...]:
    """Known-page polling: hash-compare every retained watch URL against this poll.

    Polling keeps known URLs, never gains them: a fetched URL outside the watch
    list is invisible here, and a watched URL missing from this poll's fetches is
    not reported as changed (unreachable is not changed).
    """
    return tuple(
        sorted(url for url, baseline in known_urls.items() if url in fetched and fetched[url] != baseline)
    )


def _provenance_publication(source: MissionSource) -> datetime | None:
    provenance = source.tavily_provenance_json or {}
    raw = provenance.get("published_date_raw")
    return parse_published_date(raw if isinstance(raw, str) else None)


def _qualifying_publication(
    preregistration: Preregistration,
    sources_by_id: Mapping[str, MissionSource],
    fixture: FrozenChange,
) -> datetime | None:
    source = sources_by_id.get(fixture.source_id)
    if source is None:
        return None
    published = _provenance_publication(source)
    if published is None or not window_contains(preregistration.window, published):
        return None
    if not host_allowed(source.official_domain, preregistration.domains):
        return None
    return published


def evaluate_events(
    preregistration: Preregistration, outcomes: CurationOutcomes
) -> tuple[EventEvaluation, ...]:
    """Evaluate every corpus event across the frozen-curriculum, polling and Tavily arms."""
    watched = {normalize_url(url) for url in preregistration.known_urls}
    sources_by_id = {source.id: source for source in outcomes.sources}
    by_event: dict[str, list[FrozenChange]] = {}
    for fixture in outcomes.frozen_changes:
        if fixture.event_id is not None:
            by_event.setdefault(fixture.event_id, []).append(fixture)
    evaluations = []
    for event in sorted(preregistration.events, key=lambda item: (item.domain, item.kind, item.id)):
        qualifying = []
        for fixture in by_event.get(event.id, []):
            published = _qualifying_publication(preregistration, sources_by_id, fixture)
            if published is not None:
                qualifying.append((fixture, published))
        evaluations.append(
            EventEvaluation(
                event_id=event.id,
                domain=event.domain,
                kind=event.kind,
                polling_visible=normalize_url(event.source_url) in watched,
                tavily_found=bool(qualifying),
                tavily_useful=any(fixture.change_kind == "executable" for fixture, _ in qualifying),
                earliest_qualifying=min((published for _, published in qualifying), default=None),
            )
        )
    return tuple(evaluations)


def _refusal_checks(manifest: CurationManifest, outcomes: CurationOutcomes) -> None:
    """Protocol integrity: results cannot precede the freeze, references must resolve."""
    freeze = manifest.require_frozen()
    for run in outcomes.discovery_runs:
        if run.started_at < freeze.frozen_at:
            raise ManifestIntegrityError(
                f"discovery run {run.id!r} started at {iso_utc(run.started_at)}, before the "
                f"{iso_utc(freeze.frozen_at)} freeze; results cannot precede the pre-registration"
            )
    for review in outcomes.reviews:
        if review.reviewed_at < freeze.frozen_at:
            raise ManifestIntegrityError(
                f"the review of {review.source_id!r} is dated {iso_utc(review.reviewed_at)}, before the "
                f"{iso_utc(freeze.frozen_at)} freeze; results cannot precede the pre-registration"
            )
    for change in outcomes.frozen_changes:
        if change.frozen_at < freeze.frozen_at:
            raise ManifestIntegrityError(
                f"fixture {change.fixture_ref!r} froze at {iso_utc(change.frozen_at)}, before the "
                f"{iso_utc(freeze.frozen_at)} freeze; results cannot precede the pre-registration"
            )
    source_ids = {source.id for source in outcomes.sources}
    event_ids = {event.id for event in manifest.preregistration.events}
    for review in outcomes.reviews:
        if review.source_id not in source_ids:
            raise ManifestIntegrityError(f"review references unknown source {review.source_id!r}")
        if len([item for item in outcomes.reviews if item.source_id == review.source_id]) != 1:
            raise ManifestIntegrityError(
                f"source {review.source_id!r} has more than one review; each candidate carries exactly one"
            )
    for change in outcomes.frozen_changes:
        if change.source_id not in source_ids:
            raise ManifestIntegrityError(f"fixture {change.fixture_ref!r} references unknown source {change.source_id!r}")
        for candidate in change.candidates:
            if candidate not in source_ids:
                raise ManifestIntegrityError(f"fixture {change.fixture_ref!r} references unknown candidate {candidate!r}")
            if not any(review.source_id == candidate for review in outcomes.reviews):
                raise ManifestIntegrityError(
                    f"candidate {candidate!r} has no recorded review; review-cost thresholds cannot be measured"
                )
        if change.event_id is not None and change.event_id not in event_ids:
            raise ManifestIntegrityError(
                f"fixture {change.fixture_ref!r} references unknown event {change.event_id!r}"
            )
    for event in manifest.preregistration.events:
        watched = {normalize_url(url) for url in manifest.preregistration.known_urls}
        in_list = normalize_url(event.source_url) in watched
        if event.kind == "structural" and in_list:
            raise ManifestIntegrityError(
                f"structural event {event.id!r} sits inside the polling watch list; the corpus is inconsistent"
            )
        if event.kind == "known_page" and not in_list:
            raise ManifestIntegrityError(
                f"known-page event {event.id!r} is missing from the polling watch list; the corpus is inconsistent"
            )


def _median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        return 0.0
    middle = count // 2
    if count % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def threshold_checks(manifest: CurationManifest, outcomes: CurationOutcomes) -> tuple[ThresholdCheck, ...]:
    """Measure every pre-registered threshold and rule against the outcomes."""
    preregistration = manifest.preregistration
    thresholds = preregistration.thresholds
    evaluations = evaluate_events(preregistration, outcomes)
    structural = [row for row in evaluations if row.kind == "structural"]
    useful = [row for row in structural if row.tavily_useful]

    checks = [
        ThresholdCheck(
            name="useful_structural_discoveries",
            measured=str(len(useful)),
            requirement=(
                f">= {thresholds.min_structural_discoveries} useful structural changes "
                "(structural events are never polling-visible by validation)"
            ),
            passed=len(useful) >= thresholds.min_structural_discoveries,
        ),
        ThresholdCheck(
            name="useful_structural_domains",
            measured=str(len({row.domain for row in useful})),
            requirement=f">= {thresholds.min_structural_domains} distinct domains",
            passed=len({row.domain for row in useful}) >= thresholds.min_structural_domains,
        ),
    ]

    sources_by_id = {source.id: source for source in outcomes.sources}
    useful_fixtures: list[FrozenChange] = []
    for change in outcomes.frozen_changes:
        if change.change_kind != "executable" or change.event_id is None:
            continue
        event = manifest.find_event(change.event_id)
        if event is None or event.kind != "structural":
            continue
        if _qualifying_publication(preregistration, sources_by_id, change) is None:
            continue
        useful_fixtures.append(change)

    over_cap = [
        (change.fixture_ref, len(change.candidates))
        for change in useful_fixtures
        if len(change.candidates) > thresholds.max_reviewed_candidates_per_useful_fixture
    ]
    largest = max((len(change.candidates) for change in useful_fixtures), default=0)
    checks.append(
        ThresholdCheck(
            name="reviewed_candidates_per_useful_fixture",
            measured=", ".join(f"{ref}: {count}" for ref, count in over_cap) if over_cap else f"max {largest}",
            requirement=f"<= {thresholds.max_reviewed_candidates_per_useful_fixture} per useful fixture",
            passed=not over_cap,
        )
    )

    durations = [
        review.minutes
        for change in useful_fixtures
        for candidate in change.candidates
        for review in outcomes.reviews
        if review.source_id == candidate
    ]
    median = _median(durations)
    checks.append(
        ThresholdCheck(
            name="median_review_minutes",
            measured=f"{median:.1f} over {len(durations)} review(s)",
            requirement=f"<= {thresholds.max_median_review_minutes}",
            passed=median <= thresholds.max_median_review_minutes,
        )
    )

    violations: list[str] = []
    for change in outcomes.frozen_changes:
        source = sources_by_id.get(change.source_id)
        if source is None:
            violations.append(f"{change.fixture_ref}: missing source")
            continue
        if source.state is not MissionSourceState.FROZEN:
            violations.append(f"{change.fixture_ref}: source is {source.state.value}")
        if source.frozen_fixture_ref != change.fixture_ref:
            violations.append(f"{change.fixture_ref}: source is bound to a different fixture")
        if not host_allowed(source.official_domain, preregistration.domains):
            violations.append(f"{change.fixture_ref}: source domain is not allow-listed")
        decision = [review.decision for review in outcomes.reviews if review.source_id == source.id]
        if decision != ["VERIFIED"]:
            violations.append(f"{change.fixture_ref}: source has no single human verification")
    checks.append(
        ThresholdCheck(
            name="unverified_or_non_allow_listed_effects",
            measured=str(len(violations)) + (f" ({'; '.join(violations[:3])})" if violations else ""),
            requirement=f"<= {thresholds.max_unverified_content_effects} effects on a fixture or score",
            passed=len(violations) <= thresholds.max_unverified_content_effects,
        )
    )

    found_structural = [row for row in structural if row.tavily_found]
    executable_found = sum(1 for row in found_structural if row.tavily_useful)
    rule_holds = not found_structural or executable_found > 0
    checks.append(
        ThresholdCheck(
            name="executable_change_rule",
            measured=f"{executable_found} executable of {len(found_structural)} found structural change(s)",
            requirement="at least one found structural change is executable; link-only or prose-only outcomes are not useful",
            passed=rule_holds,
        )
    )
    return tuple(checks)


def adjudicate_ablation(
    manifest: CurationManifest, outcomes: CurationOutcomes
) -> Literal["KEEP_TAVILY_CLAIM", "DROP_TAVILY_CLAIM"]:
    """The pre-registered verdict: KEEP only if every threshold and rule passes.

    Raises ``ManifestIntegrityError`` (a ``CurationError``) for protocol defects,
    which are refusals rather than verdicts.
    """
    _refusal_checks(manifest, outcomes)
    checks = threshold_checks(manifest, outcomes)
    return "KEEP_TAVILY_CLAIM" if all(check.passed for check in checks) else "DROP_TAVILY_CLAIM"


def ablation_report(manifest: CurationManifest) -> str:
    """The printable report: quarantine, verification, frozen changes, comparison, verdict."""
    freeze = manifest.require_frozen()
    outcomes = manifest.outcomes
    _refusal_checks(manifest, outcomes)
    preregistration = manifest.preregistration
    evaluations = evaluate_events(preregistration, outcomes)
    checks = threshold_checks(manifest, outcomes)

    states: dict[str, int] = {}
    for source in outcomes.sources:
        states[source.state.value] = states.get(source.state.value, 0) + 1
    kinds: dict[str, int] = {}
    for change in outcomes.frozen_changes:
        kinds[change.change_kind] = kinds.get(change.change_kind, 0) + 1
    passed = [check for check in checks if check.passed]
    failed = [check for check in checks if not check.passed]
    verdict = "KEEP_TAVILY_CLAIM" if not failed else "DROP_TAVILY_CLAIM"

    lines = [
        "CURATION ABLATION REPORT",
        f"frozen: {iso_utc(freeze.frozen_at)} by {freeze.human_verifier}; digest {freeze.preregistered_digest}",
        f"window: {preregistration.window.start.isoformat()}..{preregistration.window.end.isoformat()} UTC; "
        f"domains: {', '.join(preregistration.domains)}",
        f"quarantined discovery: {len(outcomes.discovery_runs)} run(s); "
        f"sources {len(outcomes.sources)} "
        f"(QUARANTINED {states.get('QUARANTINED', 0)}, VERIFIED {states.get('VERIFIED', 0)}, "
        f"FROZEN {states.get('FROZEN', 0)}, REJECTED {states.get('REJECTED', 0)})",
        f"human source verification: {len(outcomes.reviews)} review(s)",
        f"frozen executable change: {len(outcomes.frozen_changes)} fixture(s) "
        f"(executable {kinds.get('executable', 0)}, prose {kinds.get('prose', 0)}, link {kinds.get('link', 0)})",
        "",
        "frozen curriculum arm: static; the corpus is fresh changes, so it covers none of them by construction",
        f"{'event':<30} {'domain':<20} {'kind':<11} {'polling':<8} {'tavily':<7} earliest_qualifying",
    ]
    for row in evaluations:
        tavily = "useful" if row.tavily_useful else ("found" if row.tavily_found else "missed")
        earliest = iso_utc(row.earliest_qualifying) if row.earliest_qualifying else "-"
        lines.append(
            f"{row.event_id:<30} {row.domain:<20} {row.kind:<11} "
            f"{'yes' if row.polling_visible else 'no':<8} {tavily:<7} {earliest}"
        )
    lines.append("")
    lines.append(f"{'threshold':<44} {'status':<5} measured / requirement")
    for check in checks:
        lines.append(
            f"{check.name:<44} {'PASS' if check.passed else 'FAIL':<5} {check.measured} / {check.requirement}"
        )
    lines.append("")
    lines.append(f"thresholds passed: {len(passed)} of {len(checks)}")
    for check in failed:
        lines.append(f"DROP reason: {check.name}: {check.measured} does not satisfy {check.requirement}")
    lines.append(f"VERDICT: {verdict}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m shiftwork.curation.ablation",
        description="Frozen/known-page polling/Tavily comparison with the retained DROP rule (Slice 26).",
    )
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = CurationManifest.load(args.manifest)
        report = ablation_report(manifest)
    except CurationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
