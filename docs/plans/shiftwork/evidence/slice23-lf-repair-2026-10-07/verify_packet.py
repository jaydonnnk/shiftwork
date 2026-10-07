"""Check the unapplied packet against current bytes and narrow source changes."""
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from demos.gtm_review import draft_inventory, proposed_application_sources, proposed_sealed_bytes
from shiftwork import config
from shiftwork.domain import canonical
from shiftwork.packs import registry

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def assignment(tree, name):
    matches = [n for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    assert len(matches) == 1, name
    return matches[0]

def dump(tree):
    return ast.dump(tree, include_attributes=False)

def literal_calls(node, class_name):
    rows = []
    for call in node.elts:
        assert isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
        assert call.func.id == class_name and not call.args
        rows.append({kw.arg: ast.literal_eval(kw.value) for kw in call.keywords})
    return rows

def main():
    inventory = json.loads((OUT / "review-inventory.json").read_bytes())
    assert inventory == draft_inventory(), "packet drift"
    signed = dict(inventory)
    digest = signed.pop("approval_digest")
    assert sha(canonical.canonical_bytes(signed)) == digest
    assert inventory["production_reviewed"] is False and inventory["production_sealed"] is False
    assert registry.resolve_pack("gtm").reviewed_pins == ()
    assert not any(k.startswith("gtm_") for k in config.TRUSTED_LOCAL_FIXTURES)
    changed_material = []
    for row in inventory["files"]:
        raw = (ROOT / "shiftwork" / row["path"]).read_bytes()
        assert sha(raw) == row["sha256"] and len(raw) == row["bytes"]
        expected = proposed_sealed_bytes(row["path"], raw)
        assert sha(expected) == row["proposed_sha256"]
        if raw != expected:
            proposal = OUT / "proposed-application/shiftwork" / row["path"]
            assert proposal.read_bytes() == expected and b"\r\n" not in expected
            before, after = json.loads(raw), json.loads(expected)
            assert {k for k in before if before[k] != after[k]} == {"review_status", "sealed_payload_sha256"}
            changed_material.append(row["path"])
    assert set(changed_material) == {"fixtures/requests/gtm_compare_manifest.json", "sealed/cases/gtm_pipeline_ownership.json"}
    proposals = proposed_application_sources(inventory)
    preservation = []
    for row in inventory["application_sources"]:
        path = row["path"]
        raw = (ROOT / path).read_bytes()
        proposed = (OUT / "proposed-application" / path).read_bytes()
        assert sha(raw) == row["preimage_sha256"]
        assert sha(proposed) == row["proposed_sha256"] and proposed == proposals[path]
        compile(proposed, path, "exec")
        old_lines, new_lines = raw.splitlines(keepends=True), proposed.splitlines(keepends=True)
        matcher = difflib.SequenceMatcher(a=[line.rstrip(b"\r\n") for line in old_lines],
                                         b=[line.rstrip(b"\r\n") for line in new_lines], autojunk=False)
        count = 0
        for block in matcher.get_matching_blocks():
            assert old_lines[block.a:block.a+block.size] == new_lines[block.b:block.b+block.size]
            count += block.size
        preservation.append({"path": path, "unchanged_lines_byte_exact": count})
        diff = "".join(difflib.unified_diff(raw.decode().replace("\r\n", "\n").splitlines(keepends=True),
                    proposed.decode().replace("\r\n", "\n").splitlines(keepends=True),
                    fromfile=path, tofile=path + " (proposed)"))
        with (OUT / (Path(path).stem + "-application.diff")).open("xb") as stream:
            stream.write(diff.encode())
    raw_tree = ast.parse((ROOT / "shiftwork/packs/registry.py").read_bytes())
    proposed_tree = ast.parse(proposals["shiftwork/packs/registry.py"])
    pins_node = assignment(proposed_tree, "_GTM_PINS")
    docs_node = assignment(proposed_tree, "_GTM_DOCUMENTS")
    pins = literal_calls(pins_node.value, "ReviewedPin")
    docs = literal_calls(docs_node.value, "PackDocument")
    assert pins == inventory["reviewed_pins"] and docs == inventory["documents"]
    for row in pins:
        registry.ReviewedPin.model_validate(row)
    for row in docs:
        registry.PackDocument.model_validate(row)
    narrowed = copy.deepcopy(proposed_tree)
    narrowed.body = [n for n in narrowed.body if not (isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id in {"_GTM_PINS", "_GTM_DOCUMENTS"} for t in n.targets))]
    pack_calls = assignment(narrowed, "_PACKS").value.elts
    gtm = [call for call in pack_calls if any(kw.arg == "slug" and isinstance(kw.value, ast.Constant)
                                             and kw.value.value == "gtm" for kw in call.keywords)]
    assert len(gtm) == 1
    for kw in gtm[0].keywords:
        if kw.arg in {"documents", "reviewed_pins"}:
            expected_name = "_GTM_DOCUMENTS" if kw.arg == "documents" else "_GTM_PINS"
            assert isinstance(kw.value, ast.Name) and kw.value.id == expected_name
            kw.value = ast.Tuple(elts=[], ctx=ast.Load())
    assert dump(raw_tree) == dump(narrowed), "registry changed outside three approved declarations"
    raw_config = ast.parse((ROOT / "shiftwork/config.py").read_bytes())
    proposed_config = ast.parse(proposals["shiftwork/config.py"])
    old_fixtures = ast.literal_eval(assignment(raw_config, "TRUSTED_LOCAL_FIXTURES").value)
    fixtures_node = assignment(proposed_config, "TRUSTED_LOCAL_FIXTURES").value
    new_fixtures = ast.literal_eval(fixtures_node)
    additional = {row["key"]: (row["artifact_content_hash"], row["files_hash"])
                  for row in inventory["offline_fixture_pins"]}
    assert new_fixtures == {**old_fixtures, **additional}
    kept = [(k, v) for k, v in zip(fixtures_node.keys, fixtures_node.values, strict=True)
            if ast.literal_eval(k) not in additional]
    fixtures_node.keys = [k for k, v in kept]
    fixtures_node.values = [v for k, v in kept]
    assert dump(raw_config) == dump(proposed_config), "config changed outside three fixture pins"
    application_paths = sorted(p.relative_to(OUT / "proposed-application").as_posix()
                               for p in (OUT / "proposed-application").rglob("*") if p.is_file())
    assert application_paths == sorted([*proposals, *("shiftwork/" + p for p in changed_material)])
    attr = subprocess.check_output(["git", "check-attr", "text", "--",
            *("shiftwork/" + row["path"] for row in inventory["files"])], cwd=ROOT, text=True)
    assert len(attr.splitlines()) == 19 and all(line.endswith(": text: unset") for line in attr.splitlines())
    result = {"status": "PASS", "approval_digest": digest, "material_preimages": 19,
              "application_paths": application_paths, "document_bindings": 3, "offline_fixture_pins": 3,
              "source_ast_scope": "only GTM pins/documents and three fixture entries", "newline_preservation": preservation,
              "git_text_attributes": attr.splitlines(), "production_application": False}
    with (OUT / "packet-verification.json").open("xb") as stream:
        stream.write((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps(result))

if __name__ == "__main__":
    main()
