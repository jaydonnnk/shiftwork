"""Read-only S23 draft inventory and exact proposed seal application bytes."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

from shiftwork import config
from shiftwork.domain import canonical, contract_catalog

MATERIAL_PATHS = (
    "fixtures/catalogs/gtm_v1.json",
    "fixtures/mission/gtm_pipeline_v1.json",
    "fixtures/state/gtm_pipeline_public_state.json",
    "fixtures/state/gtm_compare_state_v1.json",
    "fixtures/requests/gtm_pipeline_incident.jsonl",
    "fixtures/requests/gtm_compare_manifest.json",
    *(f"fixtures/requests/gtm_compare_pair_{n:02d}{suffix}" for n in (1, 2, 3)
      for suffix in (".jsonl", "_specs.json")),
    "sealed/cases/gtm_pipeline_ownership.json",
    *("fixtures/artifacts/gtm/" + name for name in ("pipeline_starter_failure.py",
      "gtm_compare_repair_a_workflow.py", "gtm_compare_repair_b_workflow.py")),
    *("fixtures/documents/gtm/" + name for name in ("revenue_team_brief.md",
      "qualification_routing_rules.md", "workflow_treatments.md")),
)
DOCUMENTS = (
    ("revenue-brief", "fixtures/documents/gtm/revenue_team_brief.md", "Signal inbox"),
    ("qualification-rules", "fixtures/documents/gtm/qualification_routing_rules.md", "Workflow"),
    ("workflow-treatments", "fixtures/documents/gtm/workflow_treatments.md", "Comparison bench"),
)


def proposed_sealed_bytes(path: str, raw: bytes) -> bytes:
    """Return proposed bytes, without authorizing or writing a seal anywhere."""
    key = {"fixtures/requests/gtm_compare_manifest.json": "workloads",
           "sealed/cases/gtm_pipeline_ownership.json": "cases"}.get(path)
    if key is None:
        return raw
    data = json.loads(raw)
    if data.get("review_status") != "DRAFT" or data.get("sealed_payload_sha256") is not None:
        raise ValueError("proposed seal needs the original unsealed draft preimage")
    digest = hashlib.sha256(json.dumps(data[key], sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()
    old_status = b'"review_status": "DRAFT"'
    old_digest = b'"sealed_payload_sha256": null'
    if raw.count(old_status) != 1 or raw.count(old_digest) != 1:
        raise ValueError("seal anchors must be unique")
    return raw.replace(old_status, b'"review_status": "OPERATOR_SEALED"', 1).replace(
        old_digest, ('"sealed_payload_sha256": "' + digest + '"').encode(), 1)


def draft_inventory():
    rows = []
    for relative in MATERIAL_PATHS:
        raw = (config.PACKAGE_DIR / relative).read_bytes()
        proposed = proposed_sealed_bytes(relative, raw)
        rows.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                     "proposed_bytes": len(proposed), "proposed_sha256": hashlib.sha256(proposed).hexdigest()})
    manifest = json.loads((config.PACKAGE_DIR / "fixtures/requests/gtm_compare_manifest.json").read_bytes())
    family = json.loads((config.PACKAGE_DIR / "sealed/cases/gtm_pipeline_ownership.json").read_bytes())
    catalog = json.loads((config.PACKAGE_DIR / "fixtures/catalogs/gtm_v1.json").read_bytes())
    payload = {"schema_version": 1, "engagement_slug": "gtm", "files": rows,
               "workloads_payload_sha256": hashlib.sha256(json.dumps(manifest["workloads"], sort_keys=True,
                   separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
               "cases_payload_sha256": hashlib.sha256(json.dumps(family["cases"], sort_keys=True,
                   separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
               "catalog_hash": contract_catalog.compute_catalog_hash(catalog),
               "starter_contract": config.GTM_STARTER_CONTRACT_JSON,
               "documents": [{"doc_id": doc_id, "path": path, "station": station} for doc_id, path, station in DOCUMENTS],
               "production_reviewed": False, "production_sealed": False,
               "evidence_limit": "Preparation and disposable policy tests do not authorize production use."}
    payload["workload_request_counts"] = [row["request_count"] for row in manifest["workloads"]]
    payload["reviewed_pins"] = [{"path": row["path"], "sha256": row["proposed_sha256"]} for row in rows]
    hashes = {row["path"]: row["proposed_sha256"] for row in rows}
    payload["documents"] = [{**row, "sha256": hashes[row["path"]]} for row in payload["documents"]]
    payload["offline_fixture_pins"] = offline_fixture_pins(payload["catalog_hash"])
    proposals = proposed_application_sources(payload)
    payload["application_sources"] = [{"path": path,
        "preimage_sha256": hashlib.sha256((config.PACKAGE_DIR.parent / path).read_bytes()).hexdigest(),
        "proposed_sha256": hashlib.sha256(raw).hexdigest(), "proposed_bytes": len(raw)} for path, raw in proposals.items()]
    payload["approval_digest"] = hashlib.sha256(canonical.canonical_bytes(payload)).hexdigest()
    return payload


def offline_fixture_pins(catalog_hash):
    rows = []
    for key, relative in (("gtm_starter", "pipeline_starter_failure.py"),
                          ("gtm_compare_candidate_a", "gtm_compare_repair_a_workflow.py"),
                          ("gtm_compare_candidate_b", "gtm_compare_repair_b_workflow.py")):
        path = "fixtures/artifacts/gtm/" + relative
        # Match Path.read_text used by the starter and candidate-authoring API.
        files = {"service.py": (config.PACKAGE_DIR / path).read_text(encoding="utf-8")}
        rows.append({"key": key, "path": path,
            "artifact_content_hash": canonical.artifact_content_hash(files, config.GTM_STARTER_CONTRACT_JSON, catalog_hash),
            "files_hash": canonical.content_hash({name: base64.b64encode(value.encode()).decode() for name, value in files.items()})})
    return rows


def replace_exact(raw, old, new):
    for before, after in ((old.encode(), new.encode()),
                          (old.replace("\n", "\r\n").encode(), new.replace("\n", "\r\n").encode())):
        if raw.count(before) == 1: return raw.replace(before, after, 1)
    raise ValueError("application anchor must match exactly once")


def proposed_application_sources(inventory):
    """Prepare literal registry/config replacements without applying production authority."""
    root = config.PACKAGE_DIR.parent
    registry_raw = (root / "shiftwork/packs/registry.py").read_bytes()
    pins = "_GTM_PINS = (\n" + "".join('    ReviewedPin(path="' + row["path"] + '", sha256="' + row["sha256"] + '"),\n'
        for row in inventory["reviewed_pins"]) + ")\n\n_GTM_DOCUMENTS = (\n" + "".join(
        '    PackDocument(doc_id="' + row["doc_id"] + '", path="' + row["path"] + '",\n'
        '                 sha256="' + row["sha256"] + '", station="' + row["station"] + '"),\n'
        for row in inventory["documents"]) + ")\n\n\n"
    proposed_registry = replace_exact(registry_raw, "_PACKS = (\n", pins + "_PACKS = (\n")
    proposed_registry = replace_exact(proposed_registry,
        '        manifest_path="fixtures/requests/gtm_compare_manifest.json", documents=(),',
        '        manifest_path="fixtures/requests/gtm_compare_manifest.json", documents=_GTM_DOCUMENTS,')
    proposed_registry = replace_exact(proposed_registry,
        '        reviewed_pins=(),\n    ),', '        reviewed_pins=_GTM_PINS,\n    ),')
    config_raw = (root / "shiftwork/config.py").read_bytes()
    inserted = "".join('    "' + row["key"] + '": ("' + row["artifact_content_hash"] + '", "' + row["files_hash"] + '"),\n'
        for row in inventory["offline_fixture_pins"])
    marker = "TRUSTED_LOCAL_FIXTURES = {\n"
    return {"shiftwork/packs/registry.py": proposed_registry,
            "shiftwork/config.py": replace_exact(config_raw, marker, marker + inserted)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path)
    parser.add_argument("--proposal-dir", type=Path)
    args = parser.parse_args()
    inventory = draft_inventory()
    encoded = json.dumps(inventory, indent=2) + "\n"
    if args.out is not None:
        with args.out.open("xb") as destination:
            destination.write(encoded.encode())
    if args.proposal_dir is not None:
        args.proposal_dir.mkdir(parents=True, exist_ok=False)
        proposals = proposed_application_sources(inventory)
        for path in ("fixtures/requests/gtm_compare_manifest.json", "sealed/cases/gtm_pipeline_ownership.json"):
            proposals["shiftwork/" + path] = proposed_sealed_bytes(path, (config.PACKAGE_DIR / path).read_bytes())
        for path, raw in proposals.items():
            destination = args.proposal_dir / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
    print(json.dumps({"draft_files": len(inventory["files"]), "approval_digest": inventory["approval_digest"],
                      "production_sealed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
