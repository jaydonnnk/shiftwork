"""Preserve incoming S23 bytes and repair only three unreviewed LF drafts."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
OLD = OUT.parent / "slice23-preflight-2026-10-07"
sys.path.insert(0, str(ROOT))
from demos.gtm_review import MATERIAL_PATHS

TARGETS = (
    "shiftwork/fixtures/requests/gtm_compare_manifest.json",
    "shiftwork/fixtures/requests/gtm_compare_pair_01_specs.json",
    "shiftwork/fixtures/requests/gtm_compare_pair_02_specs.json",
)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write_new(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)

def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()

def capture():
    assert git("branch", "--show-current") == "shiftwork/slice-23"
    assert git("rev-parse", "HEAD") == "3e02f1e5176cd34d6dc355bbc4529234fa51fe62"
    assert not git("diff", "--cached", "--name-only")
    tracked = git("ls-files").splitlines()
    changes = git("diff", "--name-only").splitlines()
    material = ["shiftwork/" + path for path in MATERIAL_PATHS]
    docs = [p for p in (ROOT / "docs/plans/shiftwork").glob("*.md")]
    paths = set(tracked + material + [p.relative_to(ROOT).as_posix() for p in docs])
    paths.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    historical = [p for p in (ROOT / "docs/plans/shiftwork/evidence").rglob("*")
                  if p.is_file() and OUT not in p.parents and "__pycache__" not in p.parts]
    for p in historical:
        paths.add(p.relative_to(ROOT).as_posix())
    inventory = {}
    for path in sorted(paths):
        raw = (ROOT / path).read_bytes()
        inventory[path] = sha(raw)
        if path in material or path in changes or path in {
                "docs/plans/shiftwork/slice23-gtm-operator-review-packet.md",
                "docs/plans/shiftwork/slice23-gtm-review-inventory.json"}:
            write_new(OUT / "preimages" / path, raw)
    ignore = (ROOT / ".gitignore").read_bytes()
    blocked = json.loads((OLD / "post-document-preservation-blocked.json").read_bytes())
    assert sha(ignore) == blocked["gitignore_current_sha256"]
    result = {"head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
              "index_entries_sha256": sha(subprocess.check_output(["git", "ls-files", "--stage"], cwd=ROOT)), "files": inventory,
              "historical_evidence_paths": [p.relative_to(ROOT).as_posix() for p in historical],
              "material": material, "tracked_changes": changes,
              "untracked": git("ls-files", "--others", "--exclude-standard").splitlines(),
              "gitignore_sha256": sha(ignore), "gitignore_ownership": "unverified; preserve incoming bytes"}
    write_new(OUT / "incoming.json", (json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps({"incoming_files": len(inventory), "historical_receipts": len(historical),
                      "material_files": len(material), "gitignore_preserved": True}))

def repair():
    incoming = json.loads((OUT / "incoming.json").read_bytes())
    rows = []
    for path in TARGETS:
        raw = (ROOT / path).read_bytes()
        assert sha(raw) == incoming["files"][path]
        assert (OUT / "preimages" / path).read_bytes() == raw
        assert raw.count(b"\r\n") > 0
        fixed = raw.replace(b"\r\n", b"\n")
        assert json.loads(raw) == json.loads(fixed)
        assert b"\r" not in fixed
        if "manifest" in path:
            data = json.loads(fixed)
            assert data["review_status"] == "DRAFT" and data["sealed_payload_sha256"] is None
        (ROOT / path).write_bytes(fixed)
        assert (ROOT / path).read_bytes() == fixed
        rows.append({"path": path, "preimage_sha256": sha(raw), "repaired_sha256": sha(fixed),
                     "crlf_replaced": raw.count(b"\r\n"), "json_identical": True})
    write_new(OUT / "lf-repair.json", (json.dumps({"status": "PASS", "files": rows,
              "production_seal_applied": False}, indent=2) + "\n").encode())
    print(json.dumps(rows))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=("capture", "repair"))
    args = parser.parse_args()
    globals()[args.step]()
