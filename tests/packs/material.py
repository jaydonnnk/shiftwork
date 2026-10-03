"""Disposable controller material; real declaration/pin/seal checks remain active."""

import contextlib
import hashlib
import json
import shutil

from shiftwork import config
from shiftwork.packs import registry


def protected_family_bytes(cases):
    """An exact disposable family seal, retaining the real loader path."""
    pack = registry.resolve_pack("bookshop")
    family = next(f for f in pack.families if f.family_class is registry.FamilyClass.COMPARISON)
    data = json.loads((config.PACKAGE_DIR / family.case_file).read_bytes())
    data["cases"] = [case.model_dump(mode="json") for case in cases]
    data["sealed_payload_sha256"] = hashlib.sha256(json.dumps(
        data["cases"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    return json.dumps(data).encode()


def apply_staged_material(monkeypatch, root, replacements, *, reseal_manifest=False):
    """Stage explicit test bytes behind the owning declaration and restore bindings.

    Re-pinning is a disposable operator action. It does not change production
    bytes, admit unreviewed actual packs or bypass the admission implementation.
    A None replacement withdraws a file. Manifest seals are recomputed only when
    a test explicitly needs to reach a deeper workload guard.
    """
    if root.resolve().is_relative_to(config.PACKAGE_DIR.resolve()):
        raise ValueError("disposable destination must be outside the source package")
    root.mkdir(exist_ok=False)
    for directory in ("fixtures", "sealed/cases", "templates"):
        shutil.copytree(config.PACKAGE_DIR / directory, root / directory)
    for relative, raw in replacements.items():
        path = root / relative
        if raw is None:
            path.unlink()
        else:
            path.write_bytes(raw)
    packs = []
    for pack in registry.registered_packs():
        if reseal_manifest and pack.manifest_path in replacements:
            path = root / pack.manifest_path
            data = json.loads(path.read_bytes())
            data["sealed_payload_sha256"] = hashlib.sha256(json.dumps(
                data["workloads"], sort_keys=True, separators=(",", ":"),
                ensure_ascii=False).encode()).hexdigest()
            path.write_bytes(json.dumps(data).encode())
        pins = tuple(pin.model_copy(update={"sha256": hashlib.sha256(
            (root / pin.path).read_bytes()).hexdigest()}) if (root / pin.path).is_file()
            else pin for pin in pack.reviewed_pins)
        packs.append(pack.model_copy(update={"reviewed_pins": pins}))
    monkeypatch.setattr(config, "PACKAGE_DIR", root)
    monkeypatch.setattr(config, "CATALOG_DIR", root / "fixtures/catalogs")
    monkeypatch.setattr(config, "SEALED_CASES_DIR", root / "sealed/cases")
    monkeypatch.setattr(registry, "_PACKS", tuple(packs))
    return root


@contextlib.contextmanager
def staged_material(monkeypatch, root, replacements, *, reseal_manifest=False):
    with monkeypatch.context() as binding:
        yield apply_staged_material(binding, root, replacements, reseal_manifest=reseal_manifest)
