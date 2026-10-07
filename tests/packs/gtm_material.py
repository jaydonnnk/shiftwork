"""Disposable fault copies of exact approved S23 material; no inferred pins."""
import base64

from demos.gtm_reviewed import reviewed_inventory
from packs.material import apply_staged_material
from shiftwork import config
from shiftwork.domain import canonical
from shiftwork.packs import registry


def staged_gtm(monkeypatch, root):
    inventory = reviewed_inventory()
    apply_staged_material(monkeypatch, root, {})
    pack = registry.resolve_pack("gtm")
    assert [pin.model_dump(mode="json") for pin in pack.reviewed_pins] == inventory["reviewed_pins"]
    assert [doc.model_dump(mode="json") for doc in pack.documents] == inventory["documents"]
    return root


def assert_version_pin(version, key):
    file_hash = canonical.content_hash({name: base64.b64encode(text.encode()).decode()
                                       for name, text in version["files"].items()})
    assert (version["content_hash"], file_hash) == config.TRUSTED_LOCAL_FIXTURES[key], "version must match its literal production fixture pin"
