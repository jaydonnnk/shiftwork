"""Canonical hashing tests (program design S6 A: tests 1, 2, 3, full at Slice 2).

Each test can fail against broken behavior: a float that slips through, a hash
that drifts with key order or whitespace, or a silent change to the canonical
form that does not update the pinned golden vectors.
"""

import json
import unicodedata
from pathlib import Path

import pytest

from shiftwork.domain.canonical import (
    HASH_VERSION,
    CanonicalError,
    canonical_bytes,
    content_hash,
)

GOLDEN = Path(__file__).with_name("golden_hashes.json")


def test_canonical_bytes_key_order_invariance():
    # Test 1: same content, different key order and whitespace -> identical bytes and hash.
    a = {"b": 1, "a": [1, 2, {"z": None, "y": True}]}
    b = {"a": [1, 2, {"y": True, "z": None}], "b": 1}
    assert canonical_bytes(a) == canonical_bytes(b)
    assert content_hash(a) == content_hash(b)
    # Compact separators: no spaces after ',' or ':'.
    encoded = canonical_bytes(a).decode("utf-8")
    assert ", " not in encoded and ": " not in encoded
    # Keys are sorted at every level.
    assert encoded == '{"a":[1,2,{"y":true,"z":null}],"b":1}'


def test_canonical_nfc_normalization_folds_equivalent_strings():
    # NFC: a composed and a decomposed form of the same text hash identically.
    composed = {"note": unicodedata.normalize("NFC", "café résumé")}
    decomposed = {"note": unicodedata.normalize("NFD", "café résumé")}
    assert composed["note"] != decomposed["note"]  # genuinely different code points
    assert canonical_bytes(composed) == canonical_bytes(decomposed)
    assert content_hash(composed) == content_hash(decomposed)


@pytest.mark.parametrize(
    "payload",
    [
        1.5,
        0.0,
        {"a": 1.0},
        [1, 2.5],
        {"outer": {"inner": [0, {"deep": 0.1}]}},
    ],
)
def test_canonical_rejects_floats(payload):
    # Test 2: a float anywhere in a hashed payload raises.
    with pytest.raises(CanonicalError):
        canonical_bytes(payload)
    with pytest.raises(CanonicalError):
        content_hash(payload)


def test_canonical_rejects_non_json_values():
    with pytest.raises(CanonicalError):
        canonical_bytes({"bytes": b"raw"})
    with pytest.raises(CanonicalError):
        canonical_bytes({1: "non-string key"})


def test_golden_hash_vectors():
    # Test 3: fixed payloads -> pinned hashes; any change requires an explicit vector update.
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert data["hash_version"] == HASH_VERSION, (
        "bumping HASH_VERSION must re-pin every golden vector, not silently drift"
    )
    assert data["vectors"], "golden vector file is empty"
    for vector in data["vectors"]:
        payload = vector["payload"]
        assert canonical_bytes(payload).decode("utf-8") == vector["canonical"], vector["name"]
        assert content_hash(payload) == vector["hash"], vector["name"]


def test_golden_vectors_are_distinct():
    # Guards against a degenerate hash that collapses different payloads.
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    hashes = [vector["hash"] for vector in data["vectors"]]
    assert len(hashes) == len(set(hashes))
