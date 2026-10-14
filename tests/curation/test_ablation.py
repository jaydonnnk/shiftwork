"""Obligation 48: the retained frozen/polling/Tavily decision and its DROP rule.

``test_ablation.py`` retains the historical frozen/known-page polling/Tavily
decision and must return DROP when any pre-registered threshold is unmet
(program design S9 test 48). The suite also proves the runtime import isolation
from Gate 3 S3.8 in both directions: no runtime module imports curation code,
and importing curation loads neither the sealed store nor the executor.

Every threshold branch is exercised independently: exactly one threshold is
made unmet while all others pass, and the verdict flips to DROP with that
branch named. The per-branch anchors are mutation-proved in
``tests/s26_mutation_proofs.py``.

Two readings this suite implements, where the contract leaves mechanics open
(mirrored in the module docstrings): the review-cost thresholds are measured
over the candidate sets of useful structural fixtures only, and the
per-domain corpus layout normally makes the "two domains" clause collapse into
the "two discoveries" clause; the domains branch is still enforced and is
tested through a superseded-corpus construction.

All Tavily traffic in this suite is an injected fake; no network, credential or
live call is exercised here.
"""

import ast
import hashlib
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from shiftwork import config
from shiftwork.curation import ablation as ablation_module
from shiftwork.curation import pipeline as pipeline_module
from shiftwork.curation.ablation import (
    adjudicate_ablation,
    ablation_report,
    detect_changes,
    evaluate_events,
    threshold_checks,
)
from shiftwork.curation.pipeline import (
    DIGEST_RECIPE,
    DOMAINS,
    EVENT_COUNT,
    PINNED_THRESHOLDS,
    SELECTION_RULE,
    TAVILY_API_KEY_ENV,
    TAVILY_ENDPOINT,
    CurationError,
    CurationManifest,
    DiscoveryRun,
    FreezeRecord,
    FrozenChange,
    ManifestIntegrityError,
    MissionSource,
    MissionSourceState,
    PreregisteredEvent,
    PreregisteredThresholds,
    PreregisteredWindow,
    Preregistration,
)

REPO_ROOT = config.PACKAGE_DIR.parent
PACKAGE_ROOT = config.PACKAGE_DIR

FREEZE_AT = datetime(2026, 8, 10, 0, 0, tzinfo=timezone.utc)
AFTER = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
HEX64 = "ab" * 32
CHANGE_HEX = "cd" * 32

KNOWN_URLS = (
    "https://www.cpsc.gov/Recalls/2025/recall-alpha",
    "https://www.cpsc.gov/Recalls/2026/recall-beta",
    "https://www.gov.uk/product-safety-alert/delta",
    "https://www.gov.uk/product-safety-alert/epsilon",
    "https://ec.europa.eu/safety-gate-alerts/screen/webReport/alert-detail/eta",
    "https://ec.europa.eu/safety-gate-alerts/screen/webReport/alert-detail/theta",
    "https://www.productsafety.gov.au/recalls/kappa-recalls",
    "https://www.productsafety.gov.au/recalls/lambda-recalls",
)

EVENT_ROWS = (
    ("ev-cpsc-known-1", "cpsc.gov", "known_page", KNOWN_URLS[0], "2025-09-10T14:00:00Z"),
    ("ev-cpsc-known-2", "cpsc.gov", "known_page", KNOWN_URLS[1], "2026-02-04T09:30:00Z"),
    ("ev-cpsc-structural", "cpsc.gov", "structural", "https://www.cpsc.gov/Newsroom/2026/rule-gamma", "2026-04-18T16:45:00Z"),
    ("ev-govuk-known-1", "gov.uk", "known_page", KNOWN_URLS[2], "2025-11-21T11:00:00Z"),
    ("ev-govuk-known-2", "gov.uk", "known_page", KNOWN_URLS[3], "2026-03-09T08:15:00Z"),
    ("ev-govuk-structural", "gov.uk", "structural", "https://www.gov.uk/government/publications/zeta-framework", "2026-06-02T13:20:00Z"),
    ("ev-ec-known-1", "ec.europa.eu", "known_page", KNOWN_URLS[4], "2025-10-05T10:10:00Z"),
    ("ev-ec-known-2", "ec.europa.eu", "known_page", KNOWN_URLS[5], "2026-01-27T15:40:00Z"),
    ("ev-ec-structural", "ec.europa.eu", "structural", "https://ec.europa.eu/growth/tools-databases/iota-regime", "2026-05-14T07:05:00Z"),
    ("ev-au-known-1", "productsafety.gov.au", "known_page", KNOWN_URLS[6], "2025-12-02T03:25:00Z"),
    ("ev-au-known-2", "productsafety.gov.au", "known_page", KNOWN_URLS[7], "2026-04-01T05:55:00Z"),
    ("ev-au-structural", "productsafety.gov.au", "structural", "https://www.productsafety.gov.au/bans/mu-ban", "2026-07-15T09:00:00Z"),
)


def _corpus() -> tuple[PreregisteredEvent, ...]:
    return tuple(
        PreregisteredEvent(
            id=event_id,
            domain=domain,
            kind=kind,
            title=f"Dated change {event_id}",
            source_url=url,
            published_at=datetime.fromisoformat(published.replace("Z", "+00:00")),
            summary="A dated change on an allow-listed official domain.",
            verified_by="jaydon",
            verified_at=datetime(2026, 8, 8, 9, 0, tzinfo=timezone.utc),
        )
        for event_id, domain, kind, url, published in EVENT_ROWS
    )


def _preregistration(**overrides) -> Preregistration:
    base = dict(
        window=PreregisteredWindow(start=date(2025, 8, 1), end=date(2026, 7, 31)),
        domains=DOMAINS,
        queries=("cpsc recalls", "gov.uk alerts"),
        events=_corpus(),
        known_urls=KNOWN_URLS,
        thresholds=PreregisteredThresholds(**PINNED_THRESHOLDS),
        selection_rule=SELECTION_RULE,
        notes="test corpus",
    )
    base.update(overrides)
    return Preregistration(**base)


def _frozen_manifest(**overrides) -> CurationManifest:
    manifest = CurationManifest(_preregistration(**overrides))
    manifest.freeze_preregistration("jaydon", when=FREEZE_AT)
    return manifest


def _add_source(
    manifest: CurationManifest,
    source_id: str,
    *,
    url: str,
    domain: str,
    published: str,
    content: str = "retrieved text",
    state: MissionSourceState = MissionSourceState.QUARANTINED,
) -> MissionSource:
    source = MissionSource(
        id=source_id,
        source_url=url,
        official_domain=domain,
        fetched_at=AFTER,
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        state=state,
        tavily_provenance_json={"published_date_raw": published, "query": "q", "run_id": "disc-0001"},
    )
    manifest.outcomes.sources.append(source)
    return source


def _freeze_useful(
    manifest: CurationManifest,
    event_id: str,
    source_id: str,
    fixture_ref: str,
    *,
    minutes: float = 12.0,
    extra_rejected: int = 1,
    change_kind: str = "executable",
) -> None:
    event = manifest.find_event(event_id)
    assert event is not None, f"missing test event {event_id}"
    published = event.published_at.isoformat()
    _add_source(manifest, source_id, url=event.source_url, domain=event.domain, published=published)
    manifest.verify(source_id, "jaydon", minutes=minutes, when=AFTER)
    candidates = [source_id]
    for index in range(extra_rejected):
        rejected = f"{source_id}-reject-{index + 1}"
        _add_source(
            manifest,
            rejected,
            url=f"{event.source_url}#cand-{index + 1}",
            domain=event.domain,
            published=published,
        )
        manifest.reject(rejected, "jaydon", minutes=minutes, reason="not a distinct change", when=AFTER)
        candidates.append(rejected)
    manifest.freeze_change(
        source_id,
        fixture_ref,
        change_kind=change_kind,
        change_sha256=CHANGE_HEX,
        event_id=event_id,
        candidates=candidates,
        when=AFTER,
    )


def _passing_manifest() -> CurationManifest:
    """Two useful structural discoveries across two domains, plus non-counting extras."""
    manifest = _frozen_manifest()
    _freeze_useful(manifest, "ev-cpsc-structural", "src-0001", "fixture-cpsc-gamma")
    _freeze_useful(manifest, "ev-govuk-structural", "src-0003", "fixture-govuk-zeta")
    _freeze_useful(manifest, "ev-ec-structural", "src-0005", "fixture-ec-iota", change_kind="prose")
    extra = _add_source(
        manifest,
        "src-0007",
        url="https://www.cpsc.gov/Newsroom/2026/rule-gamma?noise=1",
        domain="cpsc.gov",
        published="2026-04-18T16:45:00Z",
    )
    assert extra.state is MissionSourceState.QUARANTINED
    manifest.reject("src-0007", "jaydon", minutes=45.0, reason="duplicate coverage", when=AFTER)
    return manifest


class FakeTransport:
    """Offline stand-in for the live Tavily transport: canned responses, run receipts."""

    def __init__(self, responses: dict[str, dict]):
        self.responses = responses
        self.calls: list[str] = []
        self.runs: list[DiscoveryRun] = []

    def search(self, *, query, window, domains, max_results, search_depth) -> dict:
        self.calls.append(query)
        return self.responses[query]


def _result(url: str, *, published: str | None = "2026-05-02T10:00:00Z", content: str = "raw result text") -> dict:
    return {
        "url": url,
        "title": "result title",
        "content": content,
        "score": 0.91,
        "published_date": published,
    }


def _check(checks, name: str):
    matches = [check for check in checks if check.name == name]
    assert len(matches) == 1, f"expected exactly one {name!r} check, found {len(matches)}"
    return matches[0]


# ---------------------------------------------------------------------------
# Freeze validation and preregistration retention
# ---------------------------------------------------------------------------


def test_freeze_retention_matrix():
    base = _preregistration()
    events = base.events
    cpsc_structural = next(event for event in events if event.id == "ev-cpsc-structural")
    swapped = cpsc_structural.model_copy(update={"kind": "known_page"})
    late = events[0].model_copy(
        update={"published_at": datetime(2026, 8, 5, tzinfo=timezone.utc)}
    )
    wrong_host = events[0].model_copy(update={"source_url": "https://evil.example/recall"})
    duplicate_id = events[1].model_copy(update={"id": events[0].id})
    unverified = events[0].model_copy(update={"verified_by": None})
    tuned = PreregisteredThresholds(**(PINNED_THRESHOLDS | {"min_structural_discoveries": 1}))

    variants = [
        ("window", base.model_copy(update={"window": PreregisteredWindow(start=date(2025, 7, 1), end=date(2026, 7, 31))}), "window must retain"),
        ("domains", base.model_copy(update={"domains": DOMAINS[:-1]}), "domains must retain"),
        ("count", base.model_copy(update={"events": events[:-1]}), "exactly 12"),
        (
            "per-domain shape",
            base.model_copy(
                update={
                    "events": tuple(swapped if event.id == cpsc_structural.id else event for event in events),
                    "known_urls": base.known_urls + (cpsc_structural.source_url,),
                }
            ),
            "known-page and 1 structural events",
        ),
        ("thresholds", base.model_copy(update={"thresholds": tuned}), "thresholds must retain"),
        ("selection rule", base.model_copy(update={"selection_rule": "latest"}), "selection_rule must retain"),
        (
            "unverified event",
            base.model_copy(update={"events": (unverified,) + events[1:]}),
            "no recorded human source verification",
        ),
        (
            "known-page outside watch list",
            base.model_copy(update={"known_urls": base.known_urls[1:]}),
            "missing from the polling watch list",
        ),
        (
            "structural inside watch list",
            base.model_copy(update={"known_urls": base.known_urls + (cpsc_structural.source_url,)}),
            "must not be on the polling watch list",
        ),
        (
            "outside window",
            base.model_copy(update={"events": (late,) + events[1:]}),
            "outside the retained window",
        ),
        (
            "wrong host",
            base.model_copy(update={"events": (wrong_host,) + events[1:]}),
            "not on its own domain",
        ),
        (
            "duplicate id",
            base.model_copy(update={"events": (events[0], duplicate_id) + events[2:]}),
            "duplicate event id",
        ),
        ("no queries", base.model_copy(update={"queries": ()}), "at least one preregistered query"),
        ("no watch list", base.model_copy(update={"known_urls": ()}), "watch list must retain"),
    ]
    for label, preregistration, phrase in variants:
        manifest = CurationManifest(preregistration)
        with pytest.raises(CurationError, match=phrase):
            manifest.freeze_preregistration("jaydon", when=FREEZE_AT)

    # Non-vacuity: the retained corpus itself freezes, and the event count matches the layout.
    manifest = CurationManifest(_preregistration())
    freeze = manifest.freeze_preregistration("jaydon", when=FREEZE_AT)
    assert freeze.frozen_at == FREEZE_AT
    assert EVENT_COUNT == 12


def test_freeze_refuses_unverified_corpus_and_pre_results():
    manifest = CurationManifest(_preregistration(queries=()))
    with pytest.raises(CurationError, match="at least one preregistered query"):
        manifest.freeze_preregistration("jaydon", when=FREEZE_AT)

    manifest = CurationManifest(_preregistration())
    _add_source(
        manifest,
        "src-0001",
        url=KNOWN_URLS[0],
        domain="cpsc.gov",
        published="2025-09-10T14:00:00Z",
    )
    with pytest.raises(CurationError, match="results exist before the freeze"):
        manifest.freeze_preregistration("jaydon", when=FREEZE_AT)

    # An unfrozen manifest cannot discover or adjudicate at all.
    unfrozen = CurationManifest(_preregistration())
    with pytest.raises(CurationError, match="not frozen"):
        unfrozen.run_discovery(transport=FakeTransport({}), now=AFTER)
    with pytest.raises(CurationError, match="not frozen"):
        adjudicate_ablation(unfrozen, unfrozen.outcomes)


def test_freeze_immutability_digest_and_reefuse():
    manifest = _frozen_manifest()
    with pytest.raises(CurationError, match="already frozen"):
        manifest.freeze_preregistration("jaydon", when=FREEZE_AT)

    tampered = manifest.preregistration.model_copy(
        update={"selection_rule": "latest_qualifying_publication_time"}
    )
    manifest.preregistration = tampered
    with pytest.raises(ManifestIntegrityError, match="digest mismatch"):
        manifest.require_frozen()
    with pytest.raises(ManifestIntegrityError, match="digest mismatch"):
        adjudicate_ablation(manifest, manifest.outcomes)


def test_preregistered_digest_recipe_is_recomputable():
    manifest = _frozen_manifest()
    digest = manifest.freeze.preregistered_digest
    payload = manifest.preregistration.model_dump(mode="json")
    from shiftwork.domain.canonical import canonical_bytes

    recomputed = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    assert recomputed == digest
    assert manifest.freeze.digest_recipe == DIGEST_RECIPE


# ---------------------------------------------------------------------------
# Source lifecycle and discovery
# ---------------------------------------------------------------------------


def test_source_lifecycle_verify_reject_freeze_and_refusals():
    manifest = _frozen_manifest()
    _add_source(manifest, "src-0001", url=KNOWN_URLS[0], domain="cpsc.gov", published="2025-09-10T14:00:00Z")
    _add_source(manifest, "src-0002", url=KNOWN_URLS[1], domain="cpsc.gov", published="2026-02-04T09:30:00Z")

    source = manifest.verify("src-0001", "jaydon", minutes=8.5, when=AFTER)
    assert source.state is MissionSourceState.VERIFIED
    reviews = manifest.reviews_for("src-0001")
    assert len(reviews) == 1 and reviews[0].minutes == 8.5 and reviews[0].decision == "VERIFIED"
    with pytest.raises(CurationError, match="only a QUARANTINED source can be verified"):
        manifest.verify("src-0001", "jaydon", minutes=1.0, when=AFTER)
    with pytest.raises(CurationError, match="only a QUARANTINED source can be rejected"):
        manifest.reject("src-0001", "jaydon", minutes=1.0, reason="late change of mind", when=AFTER)
    with pytest.raises(CurationError, match="only a VERIFIED source can be frozen"):
        manifest.freeze_change(
            "src-0002", "fixture-unverified", change_kind="executable", change_sha256=CHANGE_HEX, when=AFTER
        )
    with pytest.raises(CurationError, match="unknown source id"):
        manifest.verify("src-9999", "jaydon", minutes=1.0, when=AFTER)
    with pytest.raises(CurationError, match="unknown preregistered event id"):
        manifest.freeze_change(
            "src-0001",
            "fixture-bad-event",
            change_kind="executable",
            change_sha256=CHANGE_HEX,
            event_id="ev-nope",
            when=AFTER,
        )

    rejected = manifest.reject("src-0002", "jaydon", minutes=4.0, reason="not a distinct change", when=AFTER)
    assert rejected.state is MissionSourceState.REJECTED
    assert manifest.reviews_for("src-0002")[0].reason == "not a distinct change"

    frozen = manifest.freeze_change(
        "src-0001",
        "fixture-alpha",
        change_kind="executable",
        change_sha256=CHANGE_HEX,
        event_id="ev-cpsc-known-1",
        when=AFTER,
    )
    assert frozen.state is MissionSourceState.FROZEN
    assert frozen.frozen_fixture_ref == "fixture-alpha"
    change = manifest.outcomes.frozen_changes[0]
    assert change.candidates == ("src-0001",)
    with pytest.raises(CurationError, match="already recorded"):
        manifest.freeze_change(
            "src-0001",
            "fixture-alpha",
            change_kind="executable",
            change_sha256=CHANGE_HEX,
            when=AFTER,
        )
    with pytest.raises(CurationError, match="only a VERIFIED source can be frozen"):
        manifest.freeze_change(
            "src-0002", "fixture-beta", change_kind="prose", change_sha256=CHANGE_HEX, when=AFTER
        )

    # A candidate set is only valid when every candidate carries a review.
    _add_source(manifest, "src-0003", url=KNOWN_URLS[2], domain="gov.uk", published="2025-11-21T11:00:00Z")
    manifest.verify("src-0003", "jaydon", minutes=3.0, when=AFTER)
    _add_source(manifest, "src-0004", url=KNOWN_URLS[3], domain="gov.uk", published="2026-03-09T08:15:00Z")
    with pytest.raises(CurationError, match="has no recorded review"):
        manifest.freeze_change(
            "src-0003",
            "fixture-gamma",
            change_kind="executable",
            change_sha256=CHANGE_HEX,
            candidates=["src-0003", "src-0004"],
            when=AFTER,
        )
    with pytest.raises(CurationError, match="must be one of its reviewed candidates"):
        manifest.freeze_change(
            "src-0003",
            "fixture-gamma",
            change_kind="executable",
            change_sha256=CHANGE_HEX,
            candidates=["src-0001"],
            when=AFTER,
        )


def test_discover_sends_the_pinned_request_and_never_echoes_the_key(monkeypatch):
    monkeypatch.delenv(TAVILY_API_KEY_ENV, raising=False)
    with pytest.raises(CurationError, match=TAVILY_API_KEY_ENV):
        pipeline_module.TavilySearchTransport()

    captured: dict = {}

    class OkResponse:
        status_code = 200

        def json(self):
            return {"results": [], "request_id": "req-1", "response_time": 1.25}

    def fake_post(url, *, json, headers, timeout):
        captured.update(url=url, json=json, headers=headers, timeout=timeout)
        return OkResponse()

    monkeypatch.setattr(pipeline_module.httpx, "post", fake_post)
    window = PreregisteredWindow(start=date(2025, 8, 1), end=date(2026, 7, 31))
    transport = pipeline_module.TavilySearchTransport(api_key="tvly-test-secret")
    body = transport.search(query="cpsc recalls", window=window, domains=DOMAINS, max_results=10, search_depth="basic")
    assert body["request_id"] == "req-1"
    assert captured["url"] == TAVILY_ENDPOINT
    assert captured["headers"]["Authorization"] == "Bearer tvly-test-secret"
    assert "api_key" not in captured["json"]
    assert captured["json"]["include_domains"] == list(DOMAINS)
    assert captured["json"]["start_date"] == "2025-08-01"
    assert captured["json"]["end_date"] == "2026-07-31"
    assert captured["json"]["filter_by_published_date"] is True
    assert captured["json"]["include_published_date"] is True

    class Unauthorized:
        status_code = 401

    monkeypatch.setattr(pipeline_module.httpx, "post", lambda *args, **kwargs: Unauthorized())
    with pytest.raises(CurationError) as caught:
        pipeline_module.TavilySearchTransport(api_key="tvly-test-secret").search(
            query="cpsc recalls", window=window, domains=DOMAINS, max_results=10, search_depth="basic"
        )
    message = str(caught.value)
    assert "401" in message and "cpsc recalls" in message
    assert "tvly-test-secret" not in message


def test_discover_filters_dedupes_and_records_receipts():
    manifest = _frozen_manifest()
    responses = {
        "cpsc recalls": {
            "request_id": "req-1",
            "response_time": 1.1,
            "results": [
                _result(KNOWN_URLS[0], published="2025-09-10T14:00:00Z", content="alpha body"),
                _result("https://example.com/off-domain", published="2026-05-02T10:00:00Z"),
                _result(KNOWN_URLS[2], published=None),
                _result("https://www.cpsc.gov/Recalls/2026/late", published="2026-09-01T10:00:00Z"),
                _result(KNOWN_URLS[0], published="2025-09-10T14:00:00Z", content="alpha body again"),
            ],
        },
        "gov.uk alerts": {
            "request_id": "req-2",
            "response_time": 0.9,
            "results": [
                _result(KNOWN_URLS[0], published="2025-09-10T14:00:00Z"),
                _result(KNOWN_URLS[3], published="2026-03-09T08:15:00Z"),
            ],
        },
    }
    runs = manifest.run_discovery(transport=FakeTransport(responses), now=AFTER)

    assert [run.id for run in runs] == ["disc-0001", "disc-0002"]
    assert [source.id for source in manifest.outcomes.sources] == ["src-0001", "src-0002"]
    alpha = manifest.find_source("src-0001")
    assert alpha.state is MissionSourceState.QUARANTINED
    assert alpha.official_domain == "www.cpsc.gov"
    provenance = alpha.tavily_provenance_json
    assert provenance["query"] == "cpsc recalls" and provenance["request_id"] == "req-1"
    assert provenance["run_id"] == "disc-0001"
    assert provenance["published_date_raw"] == "2025-09-10T14:00:00Z"
    assert provenance["score"] == "0.91"

    first = runs[0]
    assert first.result_count == 5
    assert [result.outcome for result in first.results] == ["source", "drop", "drop", "drop", "drop"]
    assert [result.drop_reason for result in first.results] == [
        None,
        "off_domain",
        "undated",
        "out_of_window",
        "duplicate",
    ]
    assert first.results[0].content == "alpha body"
    assert first.results[0].source_id == "src-0001"
    second = runs[1]
    assert [result.outcome for result in second.results] == ["drop", "source"]
    assert second.results[0].drop_reason == "duplicate"

    # A rerun dedupes against previously recorded sources and continues ordinals.
    rerun = manifest.run_discovery(transport=FakeTransport(responses), now=AFTER)
    assert [run.id for run in rerun] == ["disc-0003", "disc-0004"]
    assert len(manifest.outcomes.sources) == 2
    assert all(result.outcome == "drop" for result in rerun[0].results)
    assert rerun[0].results[0].drop_reason == "duplicate"


# ---------------------------------------------------------------------------
# The ablation: KEEP baseline, one failing branch per threshold, refusals
# ---------------------------------------------------------------------------


def test_ablation_keeps_only_when_every_threshold_and_rule_pass():
    manifest = _passing_manifest()
    checks = threshold_checks(manifest, manifest.outcomes)
    assert all(check.passed for check in checks), [check for check in checks if not check.passed]
    assert adjudicate_ablation(manifest, manifest.outcomes) == "KEEP_TAVILY_CLAIM"

    evaluations = evaluate_events(manifest.preregistration, manifest.outcomes)
    structural = [row for row in evaluations if row.kind == "structural"]
    assert sum(1 for row in structural if row.tavily_useful) == 2
    assert {row.domain for row in structural if row.tavily_useful} == {"cpsc.gov", "gov.uk"}
    # The prose fixture was found but is not useful, and the unattributed review
    # at 45 minutes stays outside the median's scoped candidate sets.
    ec = next(row for row in structural if row.event_id == "ev-ec-structural")
    assert ec.tavily_found and not ec.tavily_useful
    median_check = _check(checks, "median_review_minutes")
    assert median_check.measured == "12.0 over 4 review(s)"
    assert _check(checks, "reviewed_candidates_per_useful_fixture").measured == "max 2"


def test_ablation_drops_when_fewer_than_two_useful_structural_discoveries():
    manifest = _frozen_manifest()
    _freeze_useful(manifest, "ev-cpsc-structural", "src-0001", "fixture-cpsc-gamma")
    checks = threshold_checks(manifest, manifest.outcomes)
    count_check = _check(checks, "useful_structural_discoveries")
    assert not count_check.passed and count_check.measured == "1"
    assert adjudicate_ablation(manifest, manifest.outcomes) == "DROP_TAVILY_CLAIM"
    report = ablation_report(manifest)
    assert "DROP reason: useful_structural_discoveries" in report


def test_ablation_drops_when_useful_structural_discoveries_span_one_domain():
    """The "across two domains" clause, tested through a superseded-corpus construction.

    The pinned layout holds one structural event per domain, so under a retained
    corpus two useful discoveries always span two domains; this construction
    replaces the corpus (freeze validation bypassed, digest recomputed to match)
    so the domains branch itself must be the deciding one.
    """
    base = _preregistration()
    cpsc_structural = next(event for event in base.events if event.id == "ev-cpsc-structural")
    second_cpsc = cpsc_structural.model_copy(
        update={"id": "ev-cpsc-structural-2", "source_url": "https://www.cpsc.gov/Newsroom/2026/rule-delta"}
    )
    events = tuple(second_cpsc if event.id == "ev-govuk-structural" else event for event in base.events)
    superseded = base.model_copy(update={"events": events})
    manifest = CurationManifest(superseded)
    manifest.freeze = FreezeRecord(
        frozen_at=FREEZE_AT,
        human_verifier="superseded-corpus-test",
        preregistered_digest=pipeline_module.preregistration_digest(superseded),
        digest_recipe=DIGEST_RECIPE,
    )
    _freeze_useful(manifest, "ev-cpsc-structural", "src-0001", "fixture-cpsc-gamma")
    _freeze_useful(manifest, "ev-cpsc-structural-2", "src-0003", "fixture-cpsc-delta")
    checks = threshold_checks(manifest, manifest.outcomes)
    assert _check(checks, "useful_structural_discoveries").passed
    domains_check = _check(checks, "useful_structural_domains")
    assert not domains_check.passed and domains_check.measured == "1"
    assert adjudicate_ablation(manifest, manifest.outcomes) == "DROP_TAVILY_CLAIM"


def test_ablation_drops_when_a_useful_fixture_exceeds_ten_reviewed_candidates():
    manifest = _frozen_manifest()
    _freeze_useful(manifest, "ev-cpsc-structural", "src-0001", "fixture-cpsc-gamma", extra_rejected=10)
    _freeze_useful(manifest, "ev-govuk-structural", "src-0101", "fixture-govuk-zeta", extra_rejected=9)
    checks = threshold_checks(manifest, manifest.outcomes)
    cap = _check(checks, "reviewed_candidates_per_useful_fixture")
    assert not cap.passed
    assert "fixture-cpsc-gamma: 11" in cap.measured
    assert adjudicate_ablation(manifest, manifest.outcomes) == "DROP_TAVILY_CLAIM"
    assert "DROP reason: reviewed_candidates_per_useful_fixture" in ablation_report(manifest)

    # Boundary: exactly ten candidates per useful fixture passes.
    boundary = _frozen_manifest()
    _freeze_useful(boundary, "ev-cpsc-structural", "src-0001", "fixture-cpsc-gamma", extra_rejected=9)
    _freeze_useful(boundary, "ev-govuk-structural", "src-0101", "fixture-govuk-zeta", extra_rejected=1)
    assert _check(threshold_checks(boundary, boundary.outcomes), "reviewed_candidates_per_useful_fixture").passed


def test_ablation_drops_when_median_review_time_exceeds_thirty_minutes():
    manifest = _frozen_manifest()
    _freeze_useful(manifest, "ev-cpsc-structural", "src-0001", "fixture-cpsc-gamma", minutes=31.0, extra_rejected=0)
    _freeze_useful(manifest, "ev-govuk-structural", "src-0003", "fixture-govuk-zeta", minutes=32.0, extra_rejected=0)
    checks = threshold_checks(manifest, manifest.outcomes)
    median_check = _check(checks, "median_review_minutes")
    assert not median_check.passed and median_check.measured.startswith("31.5")
    assert adjudicate_ablation(manifest, manifest.outcomes) == "DROP_TAVILY_CLAIM"

    # Boundary: a median of exactly 30.0 passes.
    boundary = _frozen_manifest()
    _freeze_useful(boundary, "ev-cpsc-structural", "src-0001", "fixture-cpsc-gamma", minutes=30.0, extra_rejected=0)
    _freeze_useful(boundary, "ev-govuk-structural", "src-0003", "fixture-govuk-zeta", minutes=30.0, extra_rejected=0)
    reviews = boundary.outcomes.reviews
    assert [review.minutes for review in reviews] == [30.0, 30.0]
    median_check = _check(threshold_checks(boundary, boundary.outcomes), "median_review_minutes")
    assert median_check.passed and median_check.measured.startswith("30.0")


def test_ablation_drops_on_any_unverified_or_non_allow_listed_effect():
    baseline = _passing_manifest()
    assert adjudicate_ablation(baseline, baseline.outcomes) == "KEEP_TAVILY_CLAIM"

    # Tamper 1: the fixture's source is no longer the frozen constant.
    broken_state = _passing_manifest()
    index = next(
        position
        for position, source in enumerate(broken_state.outcomes.sources)
        if source.id == "src-0001"
    )
    broken_state.outcomes.sources[index] = broken_state.outcomes.sources[index].model_copy(
        update={"state": MissionSourceState.VERIFIED}
    )
    checks = threshold_checks(broken_state, broken_state.outcomes)
    effects = _check(checks, "unverified_or_non_allow_listed_effects")
    assert not effects.passed and "source is VERIFIED" in effects.measured
    assert adjudicate_ablation(broken_state, broken_state.outcomes) == "DROP_TAVILY_CLAIM"

    # Tamper 2: a fixture's source sits on a domain outside the allow list.
    broken_domain = _passing_manifest()
    index = next(
        position
        for position, source in enumerate(broken_domain.outcomes.sources)
        if source.id == "src-0001"
    )
    broken_domain.outcomes.sources[index] = broken_domain.outcomes.sources[index].model_copy(
        update={"official_domain": "evil.example"}
    )
    checks = threshold_checks(broken_domain, broken_domain.outcomes)
    effects = _check(checks, "unverified_or_non_allow_listed_effects")
    assert not effects.passed and "allow-listed" in effects.measured
    assert adjudicate_ablation(broken_domain, broken_domain.outcomes) == "DROP_TAVILY_CLAIM"


def test_ablation_drops_when_discoveries_are_link_or_prose_only():
    manifest = _frozen_manifest()
    _freeze_useful(manifest, "ev-cpsc-structural", "src-0001", "fixture-cpsc-gamma", change_kind="link")
    _freeze_useful(manifest, "ev-govuk-structural", "src-0003", "fixture-govuk-zeta", change_kind="prose")
    checks = threshold_checks(manifest, manifest.outcomes)
    rule = _check(checks, "executable_change_rule")
    assert not rule.passed and rule.measured == "0 executable of 2 found structural change(s)"
    assert adjudicate_ablation(manifest, manifest.outcomes) == "DROP_TAVILY_CLAIM"
    report = ablation_report(manifest)
    assert "DROP reason: executable_change_rule" in report

    # A mixed outcome keeps counting only executable changes: two executable
    # discoveries plus one prose discovery still KEEP (the prose one is not useful).
    mixed = _passing_manifest()
    assert adjudicate_ablation(mixed, mixed.outcomes) == "KEEP_TAVILY_CLAIM"


def test_earliest_qualifying_publication_time_dedupes_and_excludes():
    manifest = _frozen_manifest()
    event = manifest.find_event("ev-cpsc-structural")
    assert event is not None
    _freeze_useful(manifest, "ev-cpsc-structural", "src-0001", "fixture-cpsc-gamma")
    # A second attributed candidate for the same event, published earlier.
    _add_source(
        manifest,
        "src-0003",
        url="https://www.cpsc.gov/Newsroom/2026/rule-gamma?mirror=1",
        domain="cpsc.gov",
        published="2026-03-01T08:00:00Z",
    )
    manifest.verify("src-0003", "jaydon", minutes=6.0, when=AFTER)
    manifest.freeze_change(
        "src-0003",
        "fixture-cpsc-gamma-mirror",
        change_kind="executable",
        change_sha256=CHANGE_HEX,
        event_id="ev-cpsc-structural",
        when=AFTER,
    )
    # A third attributed candidate whose only date is outside the window.
    _add_source(
        manifest,
        "src-0005",
        url="https://www.cpsc.gov/Newsroom/2026/rule-gamma?late=1",
        domain="cpsc.gov",
        published="2026-09-01T10:00:00Z",
    )
    manifest.verify("src-0005", "jaydon", minutes=6.0, when=AFTER)
    manifest.freeze_change(
        "src-0005",
        "fixture-cpsc-gamma-late",
        change_kind="executable",
        change_sha256=CHANGE_HEX,
        event_id="ev-cpsc-structural",
        when=AFTER,
    )

    evaluations = evaluate_events(manifest.preregistration, manifest.outcomes)
    row = next(item for item in evaluations if item.event_id == "ev-cpsc-structural")
    assert row.tavily_found and row.tavily_useful
    assert row.earliest_qualifying == datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    assert sum(1 for item in evaluations if item.event_id == "ev-cpsc-structural") == 1

    # A candidate whose source domain is tampered off the allow list stops qualifying.
    index = next(
        position
        for position, source in enumerate(manifest.outcomes.sources)
        if source.id == "src-0001"
    )
    manifest.outcomes.sources[index] = manifest.outcomes.sources[index].model_copy(
        update={"official_domain": "evil.example"}
    )
    evaluations = evaluate_events(manifest.preregistration, manifest.outcomes)
    row = next(item for item in evaluations if item.event_id == "ev-cpsc-structural")
    assert row.tavily_found and row.earliest_qualifying == datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)


def test_polling_keeps_known_urls_and_never_sees_structural_events():
    changed = detect_changes(
        {"https://a.example/one": "hash-1", "https://b.example/two": "hash-2"},
        {
            "https://a.example/one": "hash-1",
            "https://b.example/two": "hash-3",
            "https://c.example/new": "hash-4",
        },
    )
    assert changed == ("https://b.example/two",)
    # A watched URL that was not fetched is unreachable, not changed.
    assert detect_changes({"https://a.example/one": "hash-1"}, {}) == ()
    # Polling never gains URLs: a changed fetched URL outside the watch list is invisible.
    assert detect_changes({"https://a.example/one": "hash-1"}, {"https://c.example/new": "hash-4", "https://a.example/one": "hash-1"}) == ()

    manifest = _passing_manifest()
    evaluations = evaluate_events(manifest.preregistration, manifest.outcomes)
    known = [row for row in evaluations if row.kind == "known_page"]
    structural = [row for row in evaluations if row.kind == "structural"]
    assert known and all(row.polling_visible for row in known)
    assert structural and not any(row.polling_visible for row in structural)


def test_refusals_for_ordering_dangling_references_and_missing_reviews():
    # A review dated before the freeze refuses.
    manifest = _passing_manifest()
    early_review = manifest.reviews_for("src-0001")[0].model_copy(update={"reviewed_at": FREEZE_AT - timedelta(hours=1)})
    manifest.outcomes.reviews.append(early_review)
    with pytest.raises(ManifestIntegrityError, match="cannot precede the pre-registration"):
        adjudicate_ablation(manifest, manifest.outcomes)

    # A discovery run dated before the freeze refuses.
    manifest = _passing_manifest()
    manifest.outcomes.discovery_runs.append(
        DiscoveryRun(
            id="disc-9999",
            query="q",
            started_at=FREEZE_AT - timedelta(hours=1),
            finished_at=AFTER,
            result_count=0,
            results=(),
            source_ids=(),
        )
    )
    with pytest.raises(ManifestIntegrityError, match="cannot precede the pre-registration"):
        adjudicate_ablation(manifest, manifest.outcomes)

    # A fixture referencing an unknown event refuses.
    manifest = _passing_manifest()
    manifest.outcomes.frozen_changes.append(
        FrozenChange(
            fixture_ref="fixture-dangling",
            source_id="src-0001",
            event_id="ev-nope",
            change_kind="executable",
            change_sha256=CHANGE_HEX,
            candidates=("src-0001",),
            frozen_at=AFTER,
        )
    )
    with pytest.raises(ManifestIntegrityError, match="unknown event"):
        adjudicate_ablation(manifest, manifest.outcomes)

    # A fixture candidate without a review refuses (review costs cannot be measured).
    manifest = _passing_manifest()
    _add_source(
        manifest,
        "src-0500",
        url="https://www.cpsc.gov/Newsroom/2026/rule-gamma?unreviewed=1",
        domain="cpsc.gov",
        published="2026-04-18T16:45:00Z",
    )
    manifest.outcomes.frozen_changes[0] = manifest.outcomes.frozen_changes[0].model_copy(
        update={"candidates": ("src-0001", "src-0500")}
    )
    with pytest.raises(ManifestIntegrityError, match="no recorded review"):
        adjudicate_ablation(manifest, manifest.outcomes)

    # A structural event sitting inside the polling watch list refuses even when
    # the digest matches (a superseded corpus cannot slip through validation).
    base = _preregistration()
    cpsc_structural = next(event for event in base.events if event.id == "ev-cpsc-structural")
    superseded = base.model_copy(update={"known_urls": base.known_urls + (cpsc_structural.source_url,)})
    manifest = CurationManifest(superseded)
    manifest.freeze = FreezeRecord(
        frozen_at=FREEZE_AT,
        human_verifier="superseded-corpus-test",
        preregistered_digest=pipeline_module.preregistration_digest(superseded),
        digest_recipe=DIGEST_RECIPE,
    )
    with pytest.raises(ManifestIntegrityError, match="inside the polling watch list"):
        adjudicate_ablation(manifest, manifest.outcomes)


def test_ablation_report_prints_comparison_and_verdict_last():
    passing = _passing_manifest()
    report = ablation_report(passing)
    lines = report.splitlines()
    assert lines[-1] == "VERDICT: KEEP_TAVILY_CLAIM"
    assert "DROP reason:" not in report
    assert sum(1 for line in lines if line.startswith("ev-")) == EVENT_COUNT
    for section in (
        "quarantined discovery:",
        "human source verification:",
        "frozen executable change:",
        "frozen curriculum arm:",
        "thresholds passed:",
    ):
        assert section in report, section

    dropping = _frozen_manifest()
    _freeze_useful(dropping, "ev-cpsc-structural", "src-0001", "fixture-cpsc-gamma", change_kind="link")
    report = ablation_report(dropping)
    assert report.splitlines()[-1] == "VERDICT: DROP_TAVILY_CLAIM"
    assert "DROP reason: executable_change_rule" in report


# ---------------------------------------------------------------------------
# Persistence, CLI wiring, and runtime import isolation (Gate 3 S3.8)
# ---------------------------------------------------------------------------


def test_manifest_round_trip_is_canonical_and_refuses_unknown_fields(tmp_path):
    path = tmp_path / "test3-manifest.json"
    manifest = _passing_manifest()
    manifest.save(path)
    raw = path.read_bytes()
    assert b"\r" not in raw and raw.endswith(b"\n")

    loaded = CurationManifest.load(path)
    assert loaded.preregistration == manifest.preregistration
    assert loaded.freeze == manifest.freeze
    assert loaded.outcomes == manifest.outcomes
    resaved = tmp_path / "again.json"
    loaded.save(resaved)
    assert resaved.read_bytes() == raw

    tampered = json.loads(raw)
    tampered["preregistered"]["unexpected"] = True
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(CurationError, match="manifest is invalid"):
        CurationManifest.load(path)


def test_cli_end_to_end_lifecycle_and_report(tmp_path, monkeypatch):
    path = tmp_path / "test3-manifest.json"
    manifest = CurationManifest(_preregistration())
    manifest.save(path)

    assert pipeline_module.main(["status", "--manifest", str(path)]) == 0
    # The ablation refuses an unfrozen manifest.
    assert ablation_module.main(["--manifest", str(path)]) == 2
    assert pipeline_module.main(["freeze-preregistration", "--manifest", str(path), "--verifier", "jaydon"]) == 0

    loaded = CurationManifest.load(path)
    assert loaded.freeze is not None and loaded.freeze.human_verifier == "jaydon"
    assert b"\r" not in path.read_bytes()

    monkeypatch.delenv(TAVILY_API_KEY_ENV, raising=False)
    assert pipeline_module.main(["discover", "--manifest", str(path)]) == 2
    with pytest.raises(CurationError, match=TAVILY_API_KEY_ENV):
        pipeline_module.TavilySearchTransport()

    # Ablating with an empty outcomes section is a legitimate DROP, exit 0.
    assert ablation_module.main(["--manifest", str(path)]) == 0

    _add_source(loaded, "src-0001", url=KNOWN_URLS[0], domain="cpsc.gov", published="2025-09-10T14:00:00Z")
    loaded.save(path)
    assert pipeline_module.main(["verify", "--manifest", str(path), "--source", "src-0001", "--verifier", "jaydon", "--minutes", "7"]) == 0
    assert pipeline_module.main(["freeze", "--manifest", str(path), "--source", "src-0001", "--fixture-ref", "fixture-alpha", "--change-kind", "executable", "--change-sha256", CHANGE_HEX, "--event", "ev-cpsc-known-1"]) == 0
    loaded = CurationManifest.load(path)
    assert loaded.outcomes.frozen_changes[0].fixture_ref == "fixture-alpha"
    assert pipeline_module.main(["verify", "--manifest", str(path), "--source", "src-9999", "--verifier", "jaydon", "--minutes", "7"]) == 2


def _runtime_package_files() -> list[Path]:
    files = sorted(
        path
        for path in PACKAGE_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
        and path.relative_to(PACKAGE_ROOT).parts[0] != "curation"
    )
    assert files, "no runtime package modules found; the scan would be vacuous"
    return files


def _dotted_imports(tree: ast.AST, module_name: str) -> set[str]:
    """Every dotted name a module imports, resolving relative levels."""
    package_parts = module_name.split(".")[:-1]
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package_parts[: len(package_parts) - (node.level - 1)]
                prefix = ".".join([*base, node.module] if node.module else base)
            else:
                prefix = node.module or ""
            if prefix:
                names.add(prefix)
                names.update(f"{prefix}.{alias.name}" for alias in node.names)
            else:
                names.update(alias.name for alias in node.names)
    return names


def _curation_import_findings(source: str, module_name: str) -> list[str]:
    """Dotted imports plus the literal ``__import__`` form that would reach curation."""
    findings = [
        name
        for name in _dotted_imports(ast.parse(source), module_name)
        if name == "shiftwork.curation" or name.startswith("shiftwork.curation.")
    ]
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "__import__"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value.startswith("shiftwork.curation")
        ):
            findings.append(node.args[0].value)
    return findings


def test_runtime_package_never_imports_curation():
    scanned: dict[str, list[str]] = {}
    for path in _runtime_package_files():
        relative = path.relative_to(PACKAGE_ROOT).as_posix()
        module_name = "shiftwork." + relative[:-3].replace("/", ".")
        findings = _curation_import_findings(path.read_text(encoding="utf-8"), module_name)
        if findings:
            scanned[relative] = findings
    assert not scanned, f"runtime modules import curation code: {scanned}"

    # Non-vacuity: the entrypoints were really in the scan.
    scanned_names = {path.relative_to(PACKAGE_ROOT).as_posix() for path in _runtime_package_files()}
    assert {"app.py", "orchestrator.py", "api/routes.py"} <= scanned_names

    # Scanner self-tests: a plain import, relative imports and the __import__ form are caught.
    assert _curation_import_findings("from shiftwork.curation import pipeline\n", "shiftwork.app")
    assert _curation_import_findings("from .curation import pipeline\n", "shiftwork.app")
    assert _curation_import_findings("from ..curation import pipeline\n", "shiftwork.api.routes")
    assert _curation_import_findings("__import__('shiftwork.curation.pipeline')\n", "shiftwork.app")
    assert not _curation_import_findings("from shiftwork import config\n", "shiftwork.app")


def test_import_probes_load_no_forbidden_modules():
    """Gate 3 S3.8 at runtime: the app never pulls curation; curation pulls no protected stack."""
    app_probe = (
        "import shiftwork.app, sys\n"
        "leaked = [name for name in sys.modules if name == 'shiftwork.curation' or name.startswith('shiftwork.curation.')]\n"
        "assert not leaked, leaked\n"
    )
    curation_probe = (
        "import shiftwork.curation.pipeline, shiftwork.curation.ablation, sys\n"
        "assert 'shiftwork.sealed' not in sys.modules\n"
        "assert 'shiftwork.executor' not in sys.modules\n"
    )
    for label, code in (("runtime app", app_probe), ("curation", curation_probe)):
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, f"{label} probe failed: {result.stdout}\n{result.stderr}"
