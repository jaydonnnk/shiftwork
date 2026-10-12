"""Scanner self-tests for the shared leak-scan helpers (``tests/leakscan.py``).

The leak scans are only as strong as their decoders: one that returns the response
envelope alone turns every absence assertion that uses it into a pass. Each check
below injects a payload into a representative serialized surface and requires
detection, so a removed decoding arm, a lowered nesting bound or a missing recursion
guard fails here before it can silently weaken test 16, 18, 20 or 45.

Recorded counts (2026-09-19, Slice 7 all-family extension): 4 of the 4077 identity
needles contain a backslash and cannot match a serialized JSON surface as written;
each is masked by a slash-free twin, which the last test pins rather than assumes.
"""

import base64
import json
from pathlib import Path

import pytest

from leakscan import (
    BASE64_DECODINGS,
    MAX_JSON_NESTING,
    REPO_ROOT,
    all_sealed_strings,
    decoded_surfaces,
    family_paths,
    leaks_in,
    sealed_identity_strings,
    sealed_locators,
)
from shiftwork import config
from shiftwork.sealed import store as sealed_store

TOKEN = "leakscan-decoder-token"


@pytest.mark.parametrize("encoding", ("utf-8", "utf-16-le", "utf-16-be"))
def test_base64_field_is_decoded_under_each_declared_encoding(encoding: str) -> None:
    """A payload base64-encoded in UTF-16 is invisible to a UTF-8-only decode.

    The three encodings are listed here literally rather than read from
    ``BASE64_DECODINGS``: a case parametrized by the constant under test vanishes
    when that constant is narrowed, which is a vacuity trap, not a failure. The
    membership assert ties the requirement back to the implementation.
    """
    assert encoding in BASE64_DECODINGS, f"{encoding} is not in BASE64_DECODINGS"
    body = json.dumps({"log_base64": base64.b64encode(TOKEN.encode(encoding)).decode("ascii")})
    surfaces = decoded_surfaces(body)
    assert any(TOKEN in surface for surface in surfaces), f"{encoding} payload was not decoded"


def test_deeply_nested_base64_payloads_are_reached_within_the_bound() -> None:
    """Each level re-encodes the same value; a 12-level payload is reached inside the bound."""
    payload = TOKEN
    for _ in range(12):
        payload = base64.b64encode(json.dumps({"log_base64": payload}).encode("utf-8")).decode("ascii")
    body = json.dumps({"log_base64": payload})
    assert any(TOKEN in surface for surface in decoded_surfaces(body)), (
        f"a 12-level nested payload was not decoded (bound {MAX_JSON_NESTING})"
    )


def test_deeply_nested_envelope_does_not_error_the_scan() -> None:
    """A pathological JSON-looking body must not raise out of the scanner."""
    pathological = "[" * 20000
    assert decoded_surfaces(pathological) == [pathological]


def test_deeply_nested_string_value_does_not_error_the_scan() -> None:
    """A pathological JSON-looking string value must not raise out of the recursive walk."""
    pathological = "[" * 20000
    body = json.dumps({"detail": pathological})
    surfaces = decoded_surfaces(body)
    assert surfaces[0] == body and pathological in surfaces


def test_identity_needles_a_serialized_surface_cannot_carry_have_a_capable_twin() -> None:
    """The backslash-only identity needles are masked by capable twins, and the mask is checked.

    ``json.dumps`` doubles every backslash, so a needle containing one cannot appear
    in the envelope as serialized. Both such needles are masked by a slash-free twin
    (the family file name or ``sealed/cases``), so the identity scan is not weakened
    by their absence; this test pins that property instead of assuming it.
    """
    needles = sealed_identity_strings()
    incapable = [needle for needle in needles
                 if needle not in json.dumps({"probe": needle}, ensure_ascii=False)]
    assert incapable, "no needle was found incapable; this check would be vacuous"
    for needle in incapable:
        twins = {needle.replace("\\", "/"), Path(needle).name}
        capable = [twin for twin in twins if twin in needles and twin not in incapable]
        assert capable, f"a needle a serialized surface cannot carry has no capable twin: {needle!r}"


def test_every_enabled_sealed_family_contributes_needles() -> None:
    """A scanner that quietly reads one family would pass every absence scan.

    The needle sets are only as wide as the families they read, so this pins that
    the enabled family lists, the file map and the needle collection all agree.
    Slice 15 enables a fourth family for comparisons only, so the enabled set is
    the rotation families plus the comparison families.
    """
    enabled = set(config.BOOKSHOP_FAMILIES) | set(config.BOOKSHOP_COMPARISON_FAMILIES)
    assert set(sealed_store._FAMILY_FILES) == enabled, (
        "an enabled family has no sealed file, or a sealed file is not enabled"
    )
    assert len(config.BOOKSHOP_FAMILIES) >= 3, "the all-family scans would be mostly vacuous"
    needles = set(sealed_identity_strings())
    for path in family_paths():
        assert path.name in needles, f"{path.name} is not an identity needle"
    for family in enabled:
        for case in sealed_store.load_family(family).cases:
            assert case.check_id in needles, f"{case.check_id} is not an identity needle"


def test_sealed_string_needles_a_serialized_surface_cannot_carry_have_a_capable_twin() -> None:
    """``all_sealed_strings`` gets the same non-vacuity proof as the identity set.

    Its sealed-locator arm used to be the absolute host path. That needle fails in two
    invisible ways at once: a JSON envelope doubles its backslashes, so it could never
    match a serialized payload on Windows, and its leading fragments coincide with
    every other host path in the same payload, so it fired on material that was not
    sealed on POSIX. Only the first was silent, so the arm needs this pin.
    """
    needles = all_sealed_strings()
    incapable = [needle for needle in needles
                 if needle not in json.dumps({"probe": needle}, ensure_ascii=False)]
    for needle in incapable:
        twins = {needle.replace("\\", "/"), Path(needle).name}
        capable = [twin for twin in twins if twin in needles and twin not in incapable]
        assert capable, f"a needle a serialized surface cannot carry has no capable twin: {needle!r}"


def test_sealed_locator_is_host_prefix_free_and_detected_in_a_serialized_payload() -> None:
    """The locator arm names the sealed store, not the checkout, and really can match."""
    needles = all_sealed_strings()
    for path in family_paths():
        forward, backslash = sealed_locators(path)
        assert forward.startswith("shiftwork/sealed/cases/"), f"unexpected locator shape: {forward}"
        assert str(REPO_ROOT) not in forward, "the locator carries the host prefix it exists to avoid"
        assert "\\" not in forward and backslash.replace("\\", "/") == forward
        assert forward in needles, f"{forward} is not a needle; the arm is absent"
        assert forward in json.dumps({"probe": forward}), "the locator cannot match as serialized"

        payload = json.dumps({"files": [{"path": forward}, {"path": str(config.FIXTURE_DIR)}]})
        assert forward in leaks_in(payload, needles), (
            "an injected sealed locator was not detected in a representative serialized payload"
        )
        unrelated = json.dumps({"files": [{"path": str(config.FIXTURE_DIR / "shop.json")}]})
        assert not leaks_in(unrelated, needles), (
            f"an ordinary repository host path matched a sealed needle: {leaks_in(unrelated, needles)[:3]}"
        )
