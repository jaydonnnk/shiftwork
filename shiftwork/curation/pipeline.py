"""Operator-only curation pipeline (program design S3.8; slice plan Slice 26).

This module is the human-gated lifecycle for reviewed mission curation:

    AUTHOR (preregistration) -> FREEZE -> DISCOVER (live Tavily) ->
    VERIFY/REJECT (human) -> FREEZE FIXTURE -> adjudicate in ``ablation.py``

The manifest file is the pre-registration. Its ``preregistered`` section (the
window, the four official domains, the 12-event corpus layout, the query set, the
watched URLs and the pinned thresholds) is digested with
``sha256(canonical_bytes(preregistered))`` at freeze time. The lifecycle methods
refuse to record results before the freeze and the comparator refuses to run
against an unfrozen or post-freeze-modified preregistration, so results cannot
tune the pre-registration after the fact.

Interpretation record (Slice 26, offline build). The slice contract pins the
retained historical rules; where it leaves mechanics open this module documents
the chosen reading rather than inventing a number:

- The pinned thresholds are protected by freeze validation: the corpus may not
  freeze if any threshold differs from the retained historical value.
- ``discover`` returns only qualifying quarantined sources (Gate 3 S3.8's
  ``discover(queries) -> tuple[MissionSource, ...]``; window and domains are
  keyword parameters supplied by the frozen preregistration, and one
  ``DiscoveryRun`` receipt per query is appended to ``transport.runs`` so raw
  results are retained before any derived view).
- ``verify`` and ``freeze`` are ``CurationManifest`` methods so manifest state
  stays with its file; the names and argument shapes follow S3.8, with keyword
  extras for the review record.
- The Tavily credential comes from ``TAVILY_API_KEY`` at transport construction.
  The key is never stored, echoed, or written into the manifest; errors name the
  query and HTTP status only.

This package is never imported by the runtime application; the isolation is
enforced by ``tests/curation/test_ablation.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, time, timezone
from email.utils import parsedate_to_datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Sequence
from urllib.parse import urlparse, urlunparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shiftwork.domain.canonical import canonical_bytes
from shiftwork.domain.models import Id, JsonValue

MANIFEST_KIND = "shiftwork-curation-manifest"
SCHEMA_VERSION = 1
DIGEST_RECIPE = "sha256(canonical_bytes(preregistered))"

# The retained historical preregistration (Gate 3 2026-09-16; Slice 26 contract).
WINDOW_START = date(2025, 8, 1)
WINDOW_END = date(2026, 7, 31)
DOMAINS: tuple[str, ...] = ("cpsc.gov", "gov.uk", "ec.europa.eu", "productsafety.gov.au")
KNOWN_PAGE_EVENTS_PER_DOMAIN = 2
STRUCTURAL_EVENTS_PER_DOMAIN = 1
EVENT_COUNT = len(DOMAINS) * (KNOWN_PAGE_EVENTS_PER_DOMAIN + STRUCTURAL_EVENTS_PER_DOMAIN)
SELECTION_RULE = "earliest_qualifying_publication_time"

# Pinned threshold values. ``validate_preregistration`` refuses any deviation, so
# the numbers cannot be tuned after results; the comparator reads them from the
# manifest only after this retention check has passed.
PINNED_THRESHOLDS = {
    "min_structural_discoveries": 2,
    "min_structural_domains": 2,
    "max_reviewed_candidates_per_useful_fixture": 10,
    "max_median_review_minutes": 30,
    "max_unverified_content_effects": 0,
}

# Live Tavily Search parameters (vendored reference: .tv/, POST https://api.tavily.com/search).
TAVILY_API_KEY_ENV = "TAVILY_API_KEY"
TAVILY_ENDPOINT = "https://api.tavily.com/search"
TAVILY_TOPIC = "general"
TAVILY_SEARCH_DEPTH = "basic"
TAVILY_MAX_RESULTS = 10

type Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

_FROZEN = ConfigDict(frozen=True, extra="forbid")


class CurationError(Exception):
    """A protocol or usage error. The CLI exits 2 and prints this message."""


class ManifestIntegrityError(CurationError):
    """The manifest contradicts its own frozen preregistration or record order."""


class MissionSourceState(StrEnum):
    QUARANTINED = "QUARANTINED"
    VERIFIED = "VERIFIED"
    FROZEN = "FROZEN"
    REJECTED = "REJECTED"


class MissionSource(BaseModel):
    """One retrieved candidate (program design S3.8).

    Retrieved text is quarantined data, never executable instructions. The record
    stores a content hash, not the text; the raw result text lives in the
    ``DiscoveryRun`` receipt that produced it.
    """

    model_config = _FROZEN

    id: Id
    source_url: str
    official_domain: str
    fetched_at: datetime
    content_hash: Sha256
    state: MissionSourceState
    human_verifier: str | None = None
    frozen_fixture_ref: str | None = None
    tavily_provenance_json: dict[str, JsonValue] | None = None


class SourceReview(BaseModel):
    """One human decision on one candidate, with its measured review time."""

    model_config = _FROZEN

    source_id: Id
    human_verifier: str
    reviewed_at: datetime
    minutes: float = Field(ge=0)
    decision: Literal["VERIFIED", "REJECTED"]
    reason: str | None = None


class FrozenChange(BaseModel):
    """One frozen executable-or-not change produced from a verified source.

    ``candidates`` lists every source reviewed in producing this fixture
    (including rejected ones); the ablation's review-cost thresholds are measured
    over exactly these sets.
    """

    model_config = _FROZEN

    fixture_ref: str
    source_id: Id
    event_id: Id | None = None
    change_kind: Literal["executable", "prose", "link"]
    change_sha256: Sha256
    candidates: tuple[Id, ...]
    frozen_at: datetime


class RetrievedResult(BaseModel):
    """One raw Tavily result, retained before any filtering view."""

    model_config = _FROZEN

    url: str
    title: str
    content: str
    score: float | None = None
    published_date_raw: str | None = None
    outcome: Literal["source", "drop"]
    source_id: Id | None = None
    drop_reason: Literal["off_domain", "undated", "out_of_window", "duplicate"] | None = None


class DiscoveryRun(BaseModel):
    """One live search: the request metadata plus every result as returned."""

    model_config = _FROZEN

    id: Id
    query: str
    started_at: datetime
    finished_at: datetime
    request_id: str | None = None
    response_time_s: float | None = None
    result_count: int
    results: tuple[RetrievedResult, ...]
    source_ids: tuple[Id, ...]


class PreregisteredWindow(BaseModel):
    model_config = _FROZEN

    start: date
    end: date


class PreregisteredEvent(BaseModel):
    """One dated ground-truth change on an allow-listed official domain.

    ``kind`` records how the change landed: ``known_page`` events sit on URLs the
    polling watch list already watches; ``structural`` events landed on pages the
    watch list cannot see, which is exactly the class the Tavily arm must find.

    ``verified_by``/``verified_at`` record the human source verification each
    event's URL and date received before the ablation; freeze refuses an
    unverified corpus.
    """

    model_config = _FROZEN

    id: Id
    domain: str
    kind: Literal["known_page", "structural"]
    title: str
    source_url: str
    published_at: datetime
    summary: str
    verified_by: str | None = None
    verified_at: datetime | None = None


class PreregisteredThresholds(BaseModel):
    model_config = _FROZEN

    min_structural_discoveries: int
    min_structural_domains: int
    max_reviewed_candidates_per_useful_fixture: int
    max_median_review_minutes: int
    max_unverified_content_effects: int


class Preregistration(BaseModel):
    model_config = _FROZEN

    window: PreregisteredWindow
    domains: tuple[str, ...]
    queries: tuple[str, ...]
    events: tuple[PreregisteredEvent, ...]
    known_urls: tuple[str, ...]
    thresholds: PreregisteredThresholds
    selection_rule: str
    notes: str | None = None


class FreezeRecord(BaseModel):
    model_config = _FROZEN

    frozen_at: datetime
    human_verifier: str
    preregistered_digest: Sha256
    digest_recipe: str


class CurationOutcomes(BaseModel):
    """Everything recorded after the freeze: the mutable, non-digested results."""

    model_config = ConfigDict(extra="forbid")

    sources: list[MissionSource] = Field(default_factory=list)
    reviews: list[SourceReview] = Field(default_factory=list)
    frozen_changes: list[FrozenChange] = Field(default_factory=list)
    discovery_runs: list[DiscoveryRun] = Field(default_factory=list)


def preregistration_digest(preregistration: Preregistration) -> str:
    """The frozen preregistration's digest, recomputable from the file alone."""
    payload = preregistration.model_dump(mode="json")
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def normalize_url(url: str) -> str:
    """Lowercase scheme/host, drop default ports and fragments, unify trailing slashes."""
    parsed = urlparse(url.strip())
    try:
        host = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError:
        host, port = "", None
    if not host:
        return url.strip()
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), netloc, path, "", parsed.query, ""))


def host_allowed(host: str, domains: Sequence[str]) -> bool:
    """True when a host equals an allow-listed domain or is a subdomain of one."""
    normalized = host.lower().rstrip(".")
    return any(normalized == domain or normalized.endswith("." + domain) for domain in domains)


def parse_published_date(raw: str | None) -> datetime | None:
    """Parse Tavily's ``published_date`` estimate to an aware UTC datetime.

    The beta field is documented as a best estimate and results with no detectable
    date return null; both the ISO form and the documented RFC-2822 style example
    are accepted. Anything unparseable is reported as no date, never guessed.
    """
    if not raw:
        return None
    text = raw.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None
        if parsed is None:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def window_contains(window: PreregisteredWindow, moment: datetime) -> bool:
    start = datetime.combine(window.start, time.min, tzinfo=timezone.utc)
    end = datetime.combine(window.end, time.max, tzinfo=timezone.utc)
    return start <= moment.astimezone(timezone.utc) <= end


def validate_preregistration(preregistration: Preregistration) -> list[str]:
    """Every retention rule from the Slice 26 contract, as refusal reasons.

    Returns an empty list for a complete, retained preregistration. The corpus is
    checked for exact counts and per-domain shape, every URL for host and watch
    list placement, and every event for in-window timing and recorded human
    verification.
    """
    problems: list[str] = []
    if (preregistration.window.start, preregistration.window.end) != (WINDOW_START, WINDOW_END):
        problems.append(
            f"window must retain {WINDOW_START.isoformat()} to {WINDOW_END.isoformat()} UTC"
        )
    if tuple(preregistration.domains) != DOMAINS:
        problems.append(f"domains must retain exactly {DOMAINS!r} in order")
    if preregistration.selection_rule != SELECTION_RULE:
        problems.append(f"selection_rule must retain {SELECTION_RULE!r}")
    pinned = PreregisteredThresholds(**PINNED_THRESHOLDS)
    if preregistration.thresholds != pinned:
        problems.append(f"thresholds must retain the historical pinned values {PINNED_THRESHOLDS!r}")

    if not preregistration.queries:
        problems.append("at least one preregistered query is required")
    if len(set(preregistration.queries)) != len(preregistration.queries):
        problems.append("preregistered queries must be unique")
    for query in preregistration.queries:
        if not query.strip():
            problems.append("preregistered queries must be non-blank")

    watched = {normalize_url(url) for url in preregistration.known_urls}
    if not preregistration.known_urls:
        problems.append("the polling watch list must retain at least the known-page event URLs")
    if len(watched) != len(preregistration.known_urls):
        problems.append("polling watch list URLs must be unique after normalization")
    for url in preregistration.known_urls:
        raw_host = urlparse(url).hostname or ""
        if not host_allowed(raw_host, DOMAINS):
            problems.append(f"polling watch list URL {url!r} is not on an allow-listed domain")

    if len(preregistration.events) != EVENT_COUNT:
        problems.append(
            f"the corpus must hold exactly {EVENT_COUNT} dated events, found {len(preregistration.events)}"
        )
    seen_ids: set[str] = set()
    for event in preregistration.events:
        if not event.id.strip():
            problems.append("every event needs a non-blank id")
        if event.id in seen_ids:
            problems.append(f"duplicate event id {event.id!r}")
        seen_ids.add(event.id)
        if not host_allowed(urlparse(event.source_url).hostname or "", (event.domain,)):
            problems.append(f"event {event.id!r} source URL is not on its own domain {event.domain!r}")
        if not window_contains(preregistration.window, event.published_at):
            problems.append(f"event {event.id!r} published_at is outside the retained window")
        if not event.verified_by or event.verified_at is None:
            problems.append(f"event {event.id!r} has no recorded human source verification")
        in_list = normalize_url(event.source_url) in watched
        if event.kind == "known_page" and not in_list:
            problems.append(f"known-page event {event.id!r} URL is missing from the polling watch list")
        if event.kind == "structural" and in_list:
            problems.append(f"structural event {event.id!r} URL must not be on the polling watch list")

    for domain in DOMAINS:
        known = sum(1 for e in preregistration.events if e.domain == domain and e.kind == "known_page")
        structural = sum(1 for e in preregistration.events if e.domain == domain and e.kind == "structural")
        if known != KNOWN_PAGE_EVENTS_PER_DOMAIN or structural != STRUCTURAL_EVENTS_PER_DOMAIN:
            problems.append(
                f"domain {domain!r} must hold exactly {KNOWN_PAGE_EVENTS_PER_DOMAIN} known-page and "
                f"{STRUCTURAL_EVENTS_PER_DOMAIN} structural events, found {known} and {structural}"
            )
    unknown = sorted({e.domain for e in preregistration.events} - set(DOMAINS))
    if unknown:
        problems.append(f"corpus domains outside the retained set: {unknown!r}")
    return problems


class TavilySearchTransport:
    """Live Tavily Search client (Bearer auth per the vendored API reference).

    The key is read from ``TAVILY_API_KEY`` once at construction. It is never
    stored in the manifest, echoed in output, or included in error messages; the
    request body carries no key. One HTTP POST per search and no retries, so a
    bounded run cannot silently double its credit spend. ``runs`` accumulates one
    ``DiscoveryRun`` receipt per query; the pipeline records them as evidence.
    """

    def __init__(self, *, api_key: str | None = None, timeout_s: float = 30.0):
        key = api_key if api_key is not None else os.environ.get(TAVILY_API_KEY_ENV)
        if not key:
            raise CurationError(
                f"{TAVILY_API_KEY_ENV} is not set; export it in the operator shell before a live discovery call"
            )
        self._api_key = key
        self._timeout_s = timeout_s
        self.runs: list[DiscoveryRun] = []

    def search(
        self,
        *,
        query: str,
        window: PreregisteredWindow,
        domains: Sequence[str],
        max_results: int,
        search_depth: str,
    ) -> dict:
        payload = {
            "query": query,
            "search_depth": search_depth,
            "topic": TAVILY_TOPIC,
            "max_results": max_results,
            "include_domains": list(domains),
            "include_domains_mode": "filter",
            "start_date": window.start.isoformat(),
            "end_date": window.end.isoformat(),
            "include_published_date": True,
            "filter_by_published_date": True,
        }
        try:
            response = httpx.post(
                TAVILY_ENDPOINT,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout_s,
            )
        except httpx.HTTPError as error:
            raise CurationError(
                f"Tavily search failed for query {query!r}: {type(error).__name__}"
            ) from error
        if response.status_code != 200:
            raise CurationError(f"Tavily search failed for query {query!r}: HTTP {response.status_code}")
        try:
            body = response.json()
        except ValueError as error:
            raise CurationError(f"Tavily search returned a non-JSON body for query {query!r}") from error
        if not isinstance(body, dict):
            raise CurationError(f"Tavily search returned an unexpected body type for query {query!r}")
        return body


def discover(
    queries: Sequence[str],
    *,
    window: PreregisteredWindow,
    domains: Sequence[str],
    transport: TavilySearchTransport | None = None,
    max_results: int = TAVILY_MAX_RESULTS,
    search_depth: str = TAVILY_SEARCH_DEPTH,
    exclude_urls: Sequence[str] = (),
    first_ordinal: int = 1,
    first_run_ordinal: int = 1,
    now: datetime | None = None,
) -> tuple[MissionSource, ...]:
    """Run one live Tavily search per query and return the qualifying sources.

    Qualifying means: allow-listed host, a parseable publication date inside the
    frozen window, and no duplicate URL (within the run or against
    ``exclude_urls``). Every raw result, kept or dropped, is preserved in a
    ``DiscoveryRun`` appended to ``transport.runs``; the transport must expose a
    mutable ``runs`` list. Sources start QUARANTINED; nothing here verifies,
    freezes, or scores anything.
    """
    moment = now or datetime.now(timezone.utc)
    transport = transport if transport is not None else TavilySearchTransport()
    seen = {normalize_url(url) for url in exclude_urls}
    sources: list[MissionSource] = []
    ordinal = first_ordinal
    run_ordinal = first_run_ordinal
    for query in queries:
        response = transport.search(
            query=query, window=window, domains=domains, max_results=max_results, search_depth=search_depth
        )
        run_id = f"disc-{run_ordinal:04d}"
        run_ordinal += 1
        response_time_value = response.get("response_time")
        run_response_time = (
            float(response_time_value)
            if isinstance(response_time_value, (int, float)) and not isinstance(response_time_value, bool)
            else None
        )
        results: list[RetrievedResult] = []
        source_ids: list[str] = []
        for raw in response.get("results") or []:
            url = str(raw.get("url") or "")
            title = str(raw.get("title") or "")
            content = str(raw.get("content") or "")
            score_value = raw.get("score")
            score = (
                float(score_value)
                if isinstance(score_value, (int, float)) and not isinstance(score_value, bool)
                else None
            )
            published_raw = raw.get("published_date")
            published_raw = str(published_raw) if published_raw else None
            published_at = parse_published_date(published_raw)
            host = urlparse(url).hostname or ""
            outcome: Literal["source", "drop"] = "source"
            drop_reason: Literal["off_domain", "undated", "out_of_window", "duplicate"] | None = None
            source_id: str | None = None
            if not host_allowed(host, domains):
                outcome, drop_reason = "drop", "off_domain"
            elif published_at is None:
                outcome, drop_reason = "drop", "undated"
            elif not window_contains(window, published_at):
                outcome, drop_reason = "drop", "out_of_window"
            elif normalize_url(url) in seen:
                outcome, drop_reason = "drop", "duplicate"
            else:
                seen.add(normalize_url(url))
                source_id = f"src-{ordinal:04d}"
                ordinal += 1
                source_ids.append(source_id)
                sources.append(
                    MissionSource(
                        id=source_id,
                        source_url=url,
                        official_domain=host.lower(),
                        fetched_at=moment,
                        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        state=MissionSourceState.QUARANTINED,
                        tavily_provenance_json={
                            "query": query,
                            "run_id": run_id,
                            "request_id": response.get("request_id"),
                            "response_time_s": str(run_response_time) if run_response_time is not None else None,
                            "score": str(score) if score is not None else None,
                            "published_date_raw": published_raw,
                            "topic": TAVILY_TOPIC,
                            "search_depth": search_depth,
                            "max_results": max_results,
                            "window": {"start": window.start.isoformat(), "end": window.end.isoformat()},
                            "domains": list(domains),
                        },
                    )
                )
            results.append(
                RetrievedResult(
                    url=url,
                    title=title,
                    content=content,
                    score=score,
                    published_date_raw=published_raw,
                    outcome=outcome,
                    source_id=source_id,
                    drop_reason=drop_reason,
                )
            )
        transport.runs.append(
            DiscoveryRun(
                id=run_id,
                query=query,
                started_at=moment,
                finished_at=moment,
                request_id=str(response["request_id"]) if response.get("request_id") else None,
                response_time_s=run_response_time,
                result_count=len(results),
                results=tuple(results),
                source_ids=tuple(source_ids),
            )
        )
    return tuple(sources)


class CurationManifest:
    """The manifest file: frozen preregistration plus post-freeze outcomes."""

    def __init__(
        self,
        preregistration: Preregistration,
        freeze: FreezeRecord | None = None,
        outcomes: CurationOutcomes | None = None,
    ):
        self.preregistration = preregistration
        self.freeze = freeze
        self.outcomes = outcomes if outcomes is not None else CurationOutcomes()

    @classmethod
    def load(cls, path: Path) -> "CurationManifest":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise CurationError(f"manifest not found: {path}") from error
        except (OSError, json.JSONDecodeError) as error:
            raise CurationError(f"manifest cannot be read as JSON: {path} ({error})") from error
        if not isinstance(data, dict) or data.get("kind") != MANIFEST_KIND:
            raise CurationError(f"not a {MANIFEST_KIND!r} file: {path}")
        if data.get("schema_version") != SCHEMA_VERSION:
            raise CurationError(
                f"manifest schema_version {data.get('schema_version')!r} is not the supported {SCHEMA_VERSION}"
            )
        try:
            preregistration = Preregistration.model_validate(data["preregistered"])
            freeze = FreezeRecord.model_validate(data["freeze"]) if data.get("freeze") else None
            outcomes = CurationOutcomes.model_validate(data.get("outcomes") or {})
        except (KeyError, ValidationError) as error:
            raise CurationError(f"manifest is invalid: {error}") from error
        return cls(preregistration, freeze, outcomes)

    def save(self, path: Path) -> None:
        payload = {
            "kind": MANIFEST_KIND,
            "schema_version": SCHEMA_VERSION,
            "preregistered": self.preregistration.model_dump(mode="json"),
            "freeze": self.freeze.model_dump(mode="json") if self.freeze else None,
            "outcomes": self.outcomes.model_dump(mode="json"),
        }
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        target = Path(path)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, target)

    def require_frozen(self) -> FreezeRecord:
        """The freeze record, or a refusal: no comparator output without it."""
        if self.freeze is None:
            raise CurationError(
                "the manifest is not frozen; freeze-preregistration is required before discovery or comparator output"
            )
        current = preregistration_digest(self.preregistration)
        if current != self.freeze.preregistered_digest:
            raise ManifestIntegrityError(
                "preregistration digest mismatch: the preregistration was modified after the freeze "
                f"(recorded {self.freeze.preregistered_digest}, recomputed {current})"
            )
        return self.freeze

    def freeze_preregistration(self, human_verifier: str, *, when: datetime | None = None) -> FreezeRecord:
        """Pin the preregistration after corpus verification; never amendable."""
        if self.freeze is not None:
            raise CurationError("the preregistration is already frozen; it is never re-frozen or amended")
        if not human_verifier.strip():
            raise CurationError("human_verifier must name the operator freezing the preregistration")
        problems = validate_preregistration(self.preregistration)
        if problems:
            raise CurationError("preregistration is not ready to freeze:\n- " + "\n- ".join(problems))
        if (
            self.outcomes.discovery_runs
            or self.outcomes.sources
            or self.outcomes.reviews
            or self.outcomes.frozen_changes
        ):
            raise CurationError(
                "results exist before the freeze; the pre-registration must be frozen before any discovery, review or fixture record"
            )
        moment = when or datetime.now(timezone.utc)
        self.freeze = FreezeRecord(
            frozen_at=moment,
            human_verifier=human_verifier,
            preregistered_digest=preregistration_digest(self.preregistration),
            digest_recipe=DIGEST_RECIPE,
        )
        return self.freeze

    def find_source(self, source_id: str) -> MissionSource:
        for source in self.outcomes.sources:
            if source.id == source_id:
                return source
        raise CurationError(f"unknown source id: {source_id!r}")

    def find_event(self, event_id: str) -> PreregisteredEvent | None:
        for event in self.preregistration.events:
            if event.id == event_id:
                return event
        return None

    def reviews_for(self, source_id: str) -> tuple[SourceReview, ...]:
        return tuple(review for review in self.outcomes.reviews if review.source_id == source_id)

    def _replace_source(self, updated: MissionSource) -> None:
        for index, source in enumerate(self.outcomes.sources):
            if source.id == updated.id:
                self.outcomes.sources[index] = updated
                return
        raise CurationError(f"unknown source id: {updated.id!r}")

    def _require_after_freeze(self, moment: datetime) -> None:
        freeze = self.require_frozen()
        if moment < freeze.frozen_at:
            raise ManifestIntegrityError(
                f"a record dated {moment.isoformat()} would predate the {freeze.frozen_at.isoformat()} freeze; "
                "results cannot precede the pre-registration"
            )

    def run_discovery(self, *, transport: TavilySearchTransport | None = None, now: datetime | None = None) -> tuple[DiscoveryRun, ...]:
        """The separately authorized live step: one Tavily run over the frozen query set."""
        moment = now or datetime.now(timezone.utc)
        self._require_after_freeze(moment)
        transport = transport if transport is not None else TavilySearchTransport()
        preregistration = self.preregistration
        exclude = {normalize_url(source.source_url) for source in self.outcomes.sources}
        fresh = discover(
            preregistration.queries,
            window=preregistration.window,
            domains=preregistration.domains,
            transport=transport,
            exclude_urls=tuple(sorted(exclude)),
            first_ordinal=len(self.outcomes.sources) + 1,
            first_run_ordinal=len(self.outcomes.discovery_runs) + 1,
            now=moment,
        )
        runs = tuple(transport.runs)
        self.outcomes.discovery_runs.extend(runs)
        self.outcomes.sources.extend(fresh)
        return runs

    def verify(self, source_id: str, human_verifier: str, *, minutes: float, when: datetime | None = None) -> MissionSource:
        """Record one human verification of a quarantined source, timed."""
        moment = when or datetime.now(timezone.utc)
        self._require_after_freeze(moment)
        if not human_verifier.strip():
            raise CurationError("human_verifier must name the reviewer")
        source = self.find_source(source_id)
        if source.state is not MissionSourceState.QUARANTINED:
            raise CurationError(
                f"source {source_id!r} is {source.state.value}; only a QUARANTINED source can be verified"
            )
        if minutes < 0:
            raise CurationError("review minutes must be non-negative")
        self.outcomes.reviews.append(
            SourceReview(
                source_id=source_id,
                human_verifier=human_verifier,
                reviewed_at=moment,
                minutes=minutes,
                decision="VERIFIED",
                reason=None,
            )
        )
        updated = source.model_copy(
            update={"state": MissionSourceState.VERIFIED, "human_verifier": human_verifier}
        )
        self._replace_source(updated)
        return updated

    def reject(self, source_id: str, human_verifier: str, *, minutes: float, reason: str, when: datetime | None = None) -> MissionSource:
        """Record one human rejection of a quarantined source, timed and reasoned."""
        moment = when or datetime.now(timezone.utc)
        self._require_after_freeze(moment)
        if not human_verifier.strip():
            raise CurationError("human_verifier must name the reviewer")
        if not reason.strip():
            raise CurationError("a rejection needs a reason")
        source = self.find_source(source_id)
        if source.state is not MissionSourceState.QUARANTINED:
            raise CurationError(
                f"source {source_id!r} is {source.state.value}; only a QUARANTINED source can be rejected"
            )
        if minutes < 0:
            raise CurationError("review minutes must be non-negative")
        self.outcomes.reviews.append(
            SourceReview(
                source_id=source_id,
                human_verifier=human_verifier,
                reviewed_at=moment,
                minutes=minutes,
                decision="REJECTED",
                reason=reason,
            )
        )
        updated = source.model_copy(
            update={"state": MissionSourceState.REJECTED, "human_verifier": human_verifier}
        )
        self._replace_source(updated)
        return updated

    def freeze_change(
        self,
        source_id: str,
        fixture_ref: str,
        *,
        change_kind: Literal["executable", "prose", "link"],
        change_sha256: str,
        event_id: str | None = None,
        candidates: Sequence[str] | None = None,
        when: datetime | None = None,
    ) -> MissionSource:
        """Freeze one verified change into a fixture reference.

        The fixture material itself is authored outside this package (operator
        case authoring is a separate restricted step); this record binds the
        source, the reviewed candidate set and the change digest. Only a VERIFIED
        source can freeze, so no unverified content can reach a fixture.
        """
        moment = when or datetime.now(timezone.utc)
        self._require_after_freeze(moment)
        source = self.find_source(source_id)
        if not fixture_ref.strip():
            raise CurationError("fixture_ref must be non-blank")
        if any(change.fixture_ref == fixture_ref for change in self.outcomes.frozen_changes):
            raise CurationError(f"fixture_ref {fixture_ref!r} is already recorded")
        if source.state is not MissionSourceState.VERIFIED:
            raise CurationError(
                f"source {source_id!r} is {source.state.value}; only a VERIFIED source can be frozen"
            )
        if event_id is not None and self.find_event(event_id) is None:
            raise CurationError(f"unknown preregistered event id: {event_id!r}")
        candidate_ids = tuple(dict.fromkeys(candidates if candidates is not None else (source_id,)))
        if source_id not in candidate_ids:
            raise CurationError("the frozen source must be one of its reviewed candidates")
        for candidate_id in candidate_ids:
            self.find_source(candidate_id)
            if not self.reviews_for(candidate_id):
                raise CurationError(f"candidate {candidate_id!r} has no recorded review")
        try:
            change = FrozenChange(
                fixture_ref=fixture_ref,
                source_id=source_id,
                event_id=event_id,
                change_kind=change_kind,
                change_sha256=change_sha256,
                candidates=candidate_ids,
                frozen_at=moment,
            )
        except ValidationError as error:
            raise CurationError(f"invalid frozen change record: {error}") from error
        self.outcomes.frozen_changes.append(change)
        updated = source.model_copy(
            update={"state": MissionSourceState.FROZEN, "frozen_fixture_ref": fixture_ref}
        )
        self._replace_source(updated)
        return updated


def iso_utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _status_lines(manifest: CurationManifest) -> list[str]:
    preregistration = manifest.preregistration
    lines = [f"manifest: {MANIFEST_KIND} schema {SCHEMA_VERSION}"]
    if manifest.freeze:
        lines.append(
            f"frozen: yes, at {iso_utc(manifest.freeze.frozen_at)} by {manifest.freeze.human_verifier}; "
            f"preregistered digest {manifest.freeze.preregistered_digest}"
        )
    else:
        lines.append("frozen: no (freeze-preregistration must run before discovery or comparator output)")
    known = sum(1 for event in preregistration.events if event.kind == "known_page")
    structural = sum(1 for event in preregistration.events if event.kind == "structural")
    lines.append(
        f"corpus: {len(preregistration.events)}/{EVENT_COUNT} events "
        f"(known_page {known}, structural {structural}); "
        f"queries {len(preregistration.queries)}; watched URLs {len(preregistration.known_urls)}"
    )
    problems = validate_preregistration(preregistration)
    lines.append(
        "preregistration validation: " + ("ready to freeze" if not problems else f"{len(problems)} problem(s)")
    )
    for problem in problems:
        lines.append(f"- {problem}")
    states: dict[str, int] = {}
    for source in manifest.outcomes.sources:
        states[source.state.value] = states.get(source.state.value, 0) + 1
    lines.append(
        "outcomes: "
        f"discovery runs {len(manifest.outcomes.discovery_runs)}; "
        f"sources {len(manifest.outcomes.sources)} {dict(sorted(states.items()))}; "
        f"reviews {len(manifest.outcomes.reviews)}; "
        f"frozen changes {len(manifest.outcomes.frozen_changes)}"
    )
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m shiftwork.curation.pipeline",
        description="Operator-only curation lifecycle for the Tavily ablation (program design S3.8).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def with_manifest(name: str, help_text: str) -> argparse.ArgumentParser:
        subparser = subparsers.add_parser(name, help=help_text)
        subparser.add_argument("--manifest", required=True, type=Path)
        return subparser

    with_manifest("status", "Print freeze and corpus state")
    freeze_parser = with_manifest("freeze-preregistration", "Pin the preregistration after corpus verification")
    freeze_parser.add_argument("--verifier", required=True)
    with_manifest("discover", "Run the live Tavily discovery over the frozen query set")
    verify_parser = with_manifest("verify", "Record a human verification of a quarantined source")
    verify_parser.add_argument("--source", required=True)
    verify_parser.add_argument("--verifier", required=True)
    verify_parser.add_argument("--minutes", required=True, type=float)
    reject_parser = with_manifest("reject", "Record a human rejection of a quarantined source")
    reject_parser.add_argument("--source", required=True)
    reject_parser.add_argument("--verifier", required=True)
    reject_parser.add_argument("--minutes", required=True, type=float)
    reject_parser.add_argument("--reason", required=True)
    fixture_parser = with_manifest("freeze", "Freeze a verified change into a fixture reference")
    fixture_parser.add_argument("--source", required=True)
    fixture_parser.add_argument("--fixture-ref", required=True)
    fixture_parser.add_argument("--change-kind", required=True, choices=("executable", "prose", "link"))
    fixture_parser.add_argument("--change-sha256", required=True)
    fixture_parser.add_argument("--event", default=None)
    fixture_parser.add_argument("--candidates", default=None, help="Comma-separated reviewed candidate source ids")

    args = parser.parse_args(argv)
    try:
        manifest = CurationManifest.load(args.manifest)
        if args.command == "status":
            for line in _status_lines(manifest):
                print(line)
            return 0
        if args.command == "freeze-preregistration":
            freeze = manifest.freeze_preregistration(args.verifier)
            print(f"frozen at {iso_utc(freeze.frozen_at)} by {freeze.human_verifier}")
            print(f"preregistered digest: {freeze.preregistered_digest} ({freeze.digest_recipe})")
        elif args.command == "discover":
            runs = manifest.run_discovery()
            for run in runs:
                print(
                    f"{run.id} query={run.query!r}: results={run.result_count} "
                    f"sources={len(run.source_ids)} drops={run.result_count - len(run.source_ids)}"
                )
            print(f"recorded {len(runs)} discovery run(s) with {sum(len(run.source_ids) for run in runs)} quarantined source(s)")
        elif args.command == "verify":
            source = manifest.verify(args.source, args.verifier, minutes=args.minutes)
            print(f"{source.id} is {source.state.value}; review recorded for {args.minutes} minute(s)")
        elif args.command == "reject":
            source = manifest.reject(args.source, args.verifier, minutes=args.minutes, reason=args.reason)
            print(f"{source.id} is {source.state.value}: {args.reason}")
        elif args.command == "freeze":
            candidate_ids = (
                [part.strip() for part in args.candidates.split(",") if part.strip()]
                if args.candidates
                else None
            )
            source = manifest.freeze_change(
                args.source,
                args.fixture_ref,
                change_kind=args.change_kind,
                change_sha256=args.change_sha256,
                event_id=args.event,
                candidates=candidate_ids,
            )
            print(f"{source.id} is {source.state.value}; fixture {source.frozen_fixture_ref} recorded")
        manifest.save(args.manifest)
        return 0
    except CurationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
