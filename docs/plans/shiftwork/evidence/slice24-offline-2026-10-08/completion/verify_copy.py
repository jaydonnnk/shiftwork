"""Read-only copy/source binding check before and after disposable faults."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
MANIFEST = ROOT / "docs/plans/shiftwork/evidence/slice24-offline-2026-10-08/continuation/physical-copy.json"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_bytes())
    copy = Path(manifest["path"])
    mismatches = [name for name, expected in manifest["files"].items()
                  if not (copy / name).is_file() or digest((copy / name).read_bytes()) != expected]
    targets = ["shiftwork/ledger/reducer.py", "shiftwork/domain/task_contract.py",
               "shiftwork/evaluator/evaluator.py", "shiftwork/orchestrator.py",
               "shiftwork/comparison_flow.py", "shiftwork/sealed/store.py",
               "shiftwork/domain/comparison.py", "tests/packs/gtm_mutation_proofs.py",
               "tests/packs/gtm_operation_mutation_proofs.py",
               "tests/orchestrator/test_gtm_pipeline.py",
               "tests/orchestrator/test_gtm_guards.py",
               "tests/orchestrator/test_gtm_operation_guards.py"]
    bindings = {name: digest((ROOT / name).read_bytes()) for name in targets}
    source_drift = [name for name in targets if (copy / name).read_bytes() != (ROOT / name).read_bytes()]
    result = {"status": "PASS" if not mismatches and not source_drift else "FAIL",
              "copy": str(copy), "verified_files": len(manifest["files"]),
              "copy_drift": mismatches, "source_drift": source_drift, "source_bindings": bindings}
    destination = OUT / "copy-verification.json"
    if destination.exists():
        destination = OUT / "copy-restoration.json"
    assert not destination.exists(), "receipt already exists"
    destination.write_bytes((json.dumps(result, indent=2) + "\n").encode())
    archive = OUT / "target-preimages.zip"
    if not archive.exists():
        with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as saved:
            for name in targets:
                saved.writestr(name, (ROOT / name).read_bytes())
        with zipfile.ZipFile(archive) as saved:
            assert all(saved.read(name) == (ROOT / name).read_bytes() for name in targets)
    print(json.dumps({key: result[key] for key in ("status", "copy", "verified_files", "copy_drift", "source_drift")}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
