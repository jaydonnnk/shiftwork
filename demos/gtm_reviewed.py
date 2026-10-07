"""Read-only verification of the operator-approved S23 material and literal pins."""
import hashlib
import json
from pathlib import Path

from demos.gtm_review import offline_fixture_pins
from shiftwork import config
from shiftwork.domain import canonical, contract_catalog
from shiftwork.packs import registry

DOCS = Path(__file__).resolve().parents[1] / "docs/plans/shiftwork"
APPROVAL_DIGEST = "8d87c2dc279f31f3206ec389e0f72b34b50e038c59bc764ef60c13489b62d1fa"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def reviewed_inventory():
    raw = (DOCS / "slice23-gtm-review-inventory.json").read_bytes()
    inventory = json.loads(raw)
    authorization = json.loads((DOCS / "evidence/slice23-approval-handoff-2026-10-07/authorization.json").read_bytes())
    signed = dict(inventory)
    digest = signed.pop("approval_digest")
    require(digest == authorization["approval_digest"] == APPROVAL_DIGEST
            == hashlib.sha256(canonical.canonical_bytes(signed)).hexdigest(), "approved inventory digest drift")
    require(hashlib.sha256(raw).hexdigest() == authorization["machine_inventory_sha256"], "approved inventory bytes drift")
    require(hashlib.sha256((DOCS / "slice23-gtm-operator-review-packet.md").read_bytes()).hexdigest()
            == authorization["prepared_packet_sha256"], "prepared packet bytes drift")
    require(authorization["application_authorized"] is True, "application is not authorized")
    require(len(inventory["files"]) == 19, "approved material inventory is incomplete")
    for row in inventory["files"]:
        material = (config.PACKAGE_DIR / row["path"]).read_bytes()
        require((len(material), hashlib.sha256(material).hexdigest())
                == (row["proposed_bytes"], row["proposed_sha256"]), "approved material drift: " + row["path"])
    for path, payload, expected in (
        ("fixtures/requests/gtm_compare_manifest.json", "workloads", inventory["workloads_payload_sha256"]),
        ("sealed/cases/gtm_pipeline_ownership.json", "cases", inventory["cases_payload_sha256"]),
    ):
        data = json.loads((config.PACKAGE_DIR / path).read_bytes())
        actual = hashlib.sha256(json.dumps(data[payload], sort_keys=True, separators=(",", ":"),
                                          ensure_ascii=False).encode()).hexdigest()
        require(data["review_status"] == "OPERATOR_SEALED" and data["sealed_payload_sha256"] == actual == expected,
                "approved seal drift: " + path)
    pack = registry.resolve_pack("gtm")
    require([pin.model_dump(mode="json") for pin in pack.reviewed_pins] == inventory["reviewed_pins"], "approved material pins drift")
    require([doc.model_dump(mode="json") for doc in pack.documents] == inventory["documents"], "approved document bindings drift")
    catalog = json.loads((config.PACKAGE_DIR / "fixtures/catalogs/gtm_v1.json").read_bytes())
    require(contract_catalog.compute_catalog_hash(catalog) == inventory["catalog_hash"], "approved catalog drift")
    require(config.GTM_STARTER_CONTRACT_JSON == inventory["starter_contract"], "approved starter contract drift")
    require(offline_fixture_pins(inventory["catalog_hash"]) == inventory["offline_fixture_pins"], "approved artifact fixture drift")
    actual_pins = {key: value for key, value in config.TRUSTED_LOCAL_FIXTURES.items() if key.startswith("gtm_")}
    expected_pins = {row["key"]: (row["artifact_content_hash"], row["files_hash"]) for row in inventory["offline_fixture_pins"]}
    require(actual_pins == expected_pins, "approved offline fixture pins drift")
    return inventory


if __name__ == "__main__":
    inventory = reviewed_inventory()
    print(json.dumps({"status": "PASS", "approval_digest": inventory["approval_digest"],
                      "reviewed_material_files": 19, "document_bindings": 3, "offline_fixture_pins": 3}))
