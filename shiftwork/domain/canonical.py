"""Canonical serialization and content hashing (program design S3.1).

This is the ONLY place canonical serialization/hashing exists. Every content
hash in Shiftwork (artifact versions, contract catalogs, ledger events) is
computed here so that identical inputs reproduce identical bytes and hashes
across machines and process restarts.

Floats are rejected: a hashed payload may not contain them, because float
repr is not stable enough to pin a reproducible hash. Integer minor units
(cents, milliseconds) carry every quantity that would otherwise be a float.
"""

import base64
import hashlib
import json
import unicodedata
from typing import TypedDict

from shiftwork.domain.models import JsonValue

HASH_VERSION = 1

_HASH_PREFIX = f"shiftwork.v{HASH_VERSION}".encode("ascii")


class CanonicalError(TypeError):
    """Raised when a value cannot be canonically serialized (e.g. a float)."""


class ArtifactHashEnvelope(TypedDict):
    hash_version: int
    files_base64: dict[str, str]
    contract_json: dict[str, JsonValue]
    contract_catalog_hash: str


def _normalize(value: JsonValue) -> JsonValue:
    """Recursively NFC-normalize strings and reject floats and other non-JSON types.

    Dict keys are normalized too, and re-checked for collisions after folding
    (two distinct keys could NFC-fold to the same string; that is rejected rather
    than silently dropped).
    """
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        raise CanonicalError("floats are forbidden in a hashed payload")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalError(f"non-string key in hashed payload: {key!r}")
            folded = unicodedata.normalize("NFC", key)
            if folded in normalized:
                raise CanonicalError(f"key collision after NFC folding: {folded!r}")
            normalized[folded] = _normalize(item)
        return normalized
    raise CanonicalError(f"non-JSON value in hashed payload: {type(value).__name__}")


def canonical_bytes(value: JsonValue) -> bytes:
    """Deterministic JSON: sorted keys, compact separators, UTF-8, NFC.

    Floats anywhere in the payload raise CanonicalError.
    """
    normalized = _normalize(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def content_hash(value: JsonValue) -> str:
    """sha256 hex of the HASH_VERSION prefix followed by canonical_bytes(value)."""
    digest = hashlib.sha256()
    digest.update(_HASH_PREFIX)
    digest.update(canonical_bytes(value))
    return digest.hexdigest()


def contract_params_json(contract) -> dict[str, JsonValue]:
    """Stable JSON view of a ContractParams for hashing and storage.

    ``freeze_version`` and the repository read-back both call this, so the dict
    fed into ``artifact_content_hash`` is identical on write and verify.
    """
    return contract.model_dump(mode="json")


def artifact_content_hash(
    files: dict[str, str],
    contract_json: dict[str, JsonValue],
    contract_catalog_hash: str,
) -> str:
    """The artifact version fingerprint: files + ContractParams + catalog hash.

    Both ``freeze_version`` and the read-back verification in the repository call
    this, so a stored version that no longer reproduces its recorded hash is
    detected as tampering rather than silently trusted.
    """
    envelope: ArtifactHashEnvelope = {
        "hash_version": HASH_VERSION,
        "files_base64": {
            path: base64.b64encode(text.encode("utf-8")).decode("ascii")
            for path, text in files.items()
        },
        "contract_json": contract_json,
        "contract_catalog_hash": contract_catalog_hash,
    }
    return content_hash(envelope)
