"""Sealed-store loader validation guards (program design S6 test 15).

These tests prove the schema-version and ordinal-validation guards are
failing-capable: a family file declaring an unsupported schema version or a
case with invalid request_ordinals must raise, not silently load.
"""

import json

import pytest

from shiftwork import config
from shiftwork.domain.errors import InvalidSealedCase, UnsupportedSealedSchema
from shiftwork.sealed import store as sealed_store


@pytest.fixture()
def writable_sealed(tmp_path, monkeypatch):
    """Point the sealed-store loader at a writable temp directory."""
    directory = tmp_path / "sealed-cases"
    directory.mkdir()
    for name in sealed_store._FAMILY_FILES.values():
        (directory / name).write_bytes((config.SEALED_CASES_DIR / name).read_bytes())
    monkeypatch.setattr(config, "SEALED_CASES_DIR", directory)
    return directory


def test_unsupported_file_schema_version_raises(writable_sealed):
    path = writable_sealed / sealed_store._FAMILY_FILES[sealed_store.STALE_INFORMATION]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["schema_version"] = 99
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(UnsupportedSealedSchema, match="unsupported file schema_version"):
        sealed_store.load_family(sealed_store.STALE_INFORMATION)


def test_unsupported_case_schema_version_raises(writable_sealed):
    path = writable_sealed / sealed_store._FAMILY_FILES[sealed_store.STALE_INFORMATION]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["cases"][0]["schema_version"] = 99
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(UnsupportedSealedSchema, match="unsupported schema_version"):
        sealed_store.load_family(sealed_store.STALE_INFORMATION)


def test_empty_ordinals_raises(writable_sealed):
    path = writable_sealed / sealed_store._FAMILY_FILES[sealed_store.STALE_INFORMATION]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["cases"][0]["request_ordinals"] = []
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InvalidSealedCase, match="non-empty"):
        sealed_store.load_family(sealed_store.STALE_INFORMATION)


def test_duplicate_ordinals_raises(writable_sealed):
    path = writable_sealed / sealed_store._FAMILY_FILES[sealed_store.STALE_INFORMATION]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["cases"][0]["request_ordinals"] = [1, 1]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InvalidSealedCase, match="duplicate-free"):
        sealed_store.load_family(sealed_store.STALE_INFORMATION)


def test_non_positive_ordinal_raises(writable_sealed):
    path = writable_sealed / sealed_store._FAMILY_FILES[sealed_store.STALE_INFORMATION]
    data = json.loads(path.read_text(encoding="utf-8"))
    data["cases"][0]["request_ordinals"] = [0]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InvalidSealedCase, match="positive request ordinals"):
        sealed_store.load_family(sealed_store.STALE_INFORMATION)
