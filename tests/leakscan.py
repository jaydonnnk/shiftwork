"""Shared leak-scan helpers for the Slice 6 isolation tests (program design S6.D).

Two needle sets, because "would this string ever legitimately appear on this
surface?" has different answers per surface:

``all_sealed_strings``
    Every string in the sealed inventory (all three families), including record
    ids and expected claim values. Safe for the render-map lint, where the
    haystack is fixed operator wording that can never coincide with a learner's
    own output.

``sealed_identity_strings``
    Only material that cannot legitimately appear on a learner-visible surface:
    operator notes, sealed case and check identities, superseded refs and the
    sealed files' names and host paths. Record ids and expected claim values are
    deliberately EXCLUDED here, because the shop snapshot is public and a passing
    run echoes exactly the expected claim in the learner's own response body -
    scanning for them would report a correct answer as a leak. Note fragments are
    additionally filtered against the public corpus the API legitimately echoes,
    because operator notes name learner-visible contract option labels. Test 16
    covers expected values rigorously by injecting a unique sentinel that cannot
    coincide with anything.
"""

import base64
import json
from pathlib import Path

from shiftwork import config
from shiftwork.sealed import store as sealed_store

# Below this length a sealed string is a schema key name ("id", "note"), which
# occurs inside ordinary English words and proves nothing.
MIN_LENGTH = 8

# A shared fragment at least this long is a paste, not a coincidental English word.
WINDOW = 25


def family_paths() -> tuple[Path, ...]:
    """One path per enabled sealed family, asserted to exist."""
    paths = tuple(
        config.SEALED_CASES_DIR / name for name in sealed_store._FAMILY_FILES.values()
    )
    assert len(paths) == len(sealed_store._FAMILY_FILES), "two families share a file name"
    for path in paths:
        assert path.is_file(), f"sealed family file missing: {path}"
    return paths


def _walk_strings(value: object, found: list[str]) -> None:
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            _walk_strings(item, found)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _walk_strings(item, found)


def _raw_families() -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in family_paths()]


def _cases():
    cases = [
        case
        for family in sealed_store._FAMILY_FILES
        for case in sealed_store.load_family(family).cases
    ]
    assert cases, "sealed inventory loaded empty; every leak scan would be vacuous"
    return cases


def all_sealed_strings(min_length: int = MIN_LENGTH) -> tuple[str, ...]:
    """Every string in the sealed inventory, plus case identities and the file paths.

    Long strings are also expanded into their ``WINDOW``-character fragments: a full
    operator note is never a substring of a short learner-facing render string, so
    without the fragments a partial paste would go undetected.
    """
    found: list[str] = []
    for raw in _raw_families():
        _walk_strings(raw, found)
    for case in _cases():
        found.extend([case.id, case.check_id, case.family])
    for path in family_paths():
        found.extend([path.name, str(path)])
    expanded: list[str] = list(found)
    for value in found:
        expanded.extend(note_windows(value))
    needles = tuple(sorted({value for value in expanded if len(value) >= min_length}))
    assert any(value.startswith("catalog:") for value in needles), (
        "collector missed the sealed record ids; the scan would be weaker than it looks"
    )
    assert len(needles) > len(found), "note fragments were not expanded; the fragment arm is vacuous"
    return needles


def _public_corpus() -> str:
    """Text the API legitimately echoes: catalogs, batches, snapshots, mission only.

    Operator notes deliberately name learner-visible contract option labels, so a note
    window can coincide with catalog text a response is supposed to contain. Filtering
    against this corpus keeps the identity scan about sealed material only. The corpus
    is limited to fixed fixtures no audited surface can write: the served client and
    the artifact template are projections themselves, so a note pasted into one of
    them must never make its own fragments exempt.
    """
    roots = (
        config.CATALOG_DIR,
        config.FIXTURE_DIR / "requests",
        config.FIXTURE_DIR / "shop",
        config.FIXTURE_DIR / "mission",
    )
    chunks: list[str] = []
    for root in roots:
        assert root.is_dir(), f"public corpus root missing: {root}"
        for path in sorted(root.rglob("*")):
            if path.is_file():
                chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    corpus = "\n".join(chunks)
    assert "USE_NEWEST_RECORD_WITH_AGE" in corpus, (
        "the catalog labels are not in the corpus; note windows would be reported as leaks"
    )
    return corpus


def sealed_identity_strings(min_length: int = MIN_LENGTH) -> tuple[str, ...]:
    """Sealed material that can never legitimately reach a learner-visible surface."""
    found: list[str] = []
    for case in _cases():
        found.extend([case.id, case.check_id])
        note = case.expected.get("note")
        if isinstance(note, str):
            found.append(note)
            found.extend(note_windows(note))
        for ref in case.expected.get("superseded_refs", ()):
            if isinstance(ref, str):
                found.append(ref)
    # The backslash-bearing entries cannot match a serialized JSON surface as
    # written (the envelope doubles every backslash), so they are masked by their
    # slash-free twins: the family file names and "sealed/cases". The mask is pinned
    # by the self-tests in tests/sealed/test_leakscan_self_tests.py, not assumed.
    found.extend(["sealed/cases", "sealed\\cases"])
    for path in family_paths():
        found.extend([path.name, str(path)])
    candidates = {value for value in found if len(value) >= min_length}
    corpus = _public_corpus()
    needles = tuple(sorted(value for value in candidates if value not in corpus))

    dropped = candidates - set(needles)
    assert dropped, "nothing was filtered; the corpus is not overlapping the notes as expected"
    assert all(value in corpus for value in dropped), "a needle was dropped without corpus cause"
    # Over-filtering guard: the genuinely sealed identities must survive.
    for case in _cases():
        assert case.check_id in needles, f"{case.check_id} was filtered out as public"
        assert case.id in needles, f"{case.id} was filtered out as public"
    assert any(len(value) == WINDOW for value in needles), (
        "every note fragment was filtered as public; the note arm would be vacuous"
    )
    return needles


def note_windows(text: str, width: int = WINDOW) -> tuple[str, ...]:
    """Every ``width``-character fragment of a long sealed string."""
    if len(text) < width:
        return ()
    return tuple(text[start:start + width] for start in range(len(text) - width + 1))


def leaks_in(haystack: str, needles) -> list[str]:
    """Needles present in ``haystack``, longest first so the report is readable."""
    return sorted((needle for needle in needles if needle in haystack), key=len, reverse=True)


def path_forms(text: str) -> tuple[str, ...]:
    """The haystack plus its backslash-unescaped and forward-slash variants.

    A Windows absolute path is backslash-escaped inside a JSON response
    (``C:\\\\Users\\\\...``), so scanning the serialized surface for the raw path
    string never matches and a host-path scan silently passes. Every host-path
    needle must be checked against all three forms.
    """
    return (text, text.replace("\\\\", "\\"), text.replace("\\", "/"))


def host_leaks(surface: str, needles) -> list[tuple[str, str]]:
    """Host-path needles present in ``surface`` under any escaping form.

    Both sides are normalized. The surface arrives backslash-escaped, escaped
    twice (inside a nested JSON string) or forward-slash; the needle itself is a
    Windows path whose separators must also be tried in both forms, or a
    forward-slash leak matches nothing.
    """
    forms = path_forms(surface)
    return [
        (name, value)
        for name, value in needles.items()
        if value
        and any(
            variant in form
            for variant in (value, value.replace("\\\\", "\\"), value.replace("\\", "/"))
            for form in forms
        )
    ]


# Nesting bound for re-parsed JSON-looking strings. Every extra level is another
# re-encoding of the same value; no surface this repository produces nests past two
# levels, so the bound exists to make unbounded recursion impossible rather than to
# match a real depth, and surfaces nested deeper than this are not decoded (recorded
# as a limitation, not claimed).
MAX_JSON_NESTING = 24

# Decodings attempted for a base64 payload. UTF-8 covers ordinary text; a UTF-16
# payload would render an ASCII sentinel as NUL-interleaved bytes, so a UTF-8-only
# decode shows it as garbage rather than partially, and the UTF-16 forms are
# attempted explicitly instead of being assumed to fail loudly.
BASE64_DECODINGS = ("utf-8", "utf-16-le", "utf-16-be")


def decoded_surfaces(body: str) -> list[str]:
    """The response envelope plus every decoded string value it carries.

    Three leak paths exist beyond the raw text: base64 fields hide an encoded
    capture body or log, nested JSON strings are double-escaped by the envelope,
    and an ordinary string value is already decoded by the parser. All three are
    surfaces. Fields whose name ends in ``_base64`` are decoded and scanned as text
    under each of ``BASE64_DECODINGS``, with undecodable bytes replaced rather than
    dropped; every other string value is added as its own surface; JSON-looking
    strings are parsed and walked recursively up to ``MAX_JSON_NESTING`` levels. A
    value split across two JSON fields is not reassembled, and a depth beyond the
    bound is not decoded.
    """
    surfaces = [body]
    try:
        parsed = json.loads(body)
    except (json.JSONDecodeError, RecursionError):
        return surfaces

    def walk_nested(text: str, depth: int) -> None:
        stripped = text.strip()
        if not stripped or stripped[0] not in "[{":
            return
        try:
            walk(json.loads(stripped), depth)
        except (json.JSONDecodeError, RecursionError):
            return

    def walk(value: object, depth: int = 0) -> None:
        if depth > MAX_JSON_NESTING:
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, str) and key.endswith("_base64") and item:
                    try:
                        decoded = base64.b64decode(item, validate=True)
                    except ValueError:
                        continue
                    for encoding in BASE64_DECODINGS:
                        text = decoded.decode(encoding, errors="replace")
                        surfaces.append(text)
                        walk_nested(text, depth + 1)
                else:
                    walk(item, depth)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item, depth)
        elif isinstance(value, str):
            surfaces.append(value)
            walk_nested(value, depth + 1)

    walk(parsed)
    return surfaces
