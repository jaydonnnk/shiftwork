"""Narrow test-premise and publication-filter transition, preserving old bytes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
edits = {}


def replace(path, old, new, count=1):
    raw = edits.get(path, (ROOT / path).read_bytes())
    candidates = [(old.encode(), new.encode()),
                  (old.replace("\n", "\r\n").encode(), new.replace("\n", "\r\n").encode())]
    matches = [(before, after) for before, after in candidates if raw.count(before) == count]
    # For a one-line anchor adding lines, use that line's measured ending.
    if len(matches) == 2 and matches[0][0] == matches[1][0] and matches[0][1] != matches[1][1]:
        position = raw.index(matches[0][0])
        line_end = raw.index(b"\n", position)
        crlf = raw[line_end - 1:line_end] == b"\r"
        matches = [matches[1 if crlf else 0]]
    # Identical candidates for one-line changes are one binding.
    matches = list(dict.fromkeys(matches))
    assert len(matches) == 1, (path, old, [(raw.count(a), len(a)) for a, _ in candidates])
    before, after = matches[0]
    edits[path] = raw.replace(before, after)


path = "tests/packs/gtm_material.py"
old = (ROOT / path).read_bytes()
assert old.startswith(b'"""Hypothetical operator-approved copies')
edits[path] = b'''"""Disposable fault copies of exact approved S23 material; no inferred pins."""
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
'''

path = "tests/orchestrator/test_gtm_pipeline.py"
replace(path, '"""S23 draft policy and hypothetical reviewed-copy proofs; no production admission."""',
        '"""S23 exact approved material, disposable refusal guards and trusted-local proof."""')
replace(path, "from demos.gtm_review import MATERIAL_PATHS, draft_inventory, proposed_sealed_bytes\nfrom packs.gtm_material import pin_version, staged_gtm",
        "from demos.gtm_review import MATERIAL_PATHS\nfrom demos.gtm_reviewed import reviewed_inventory\nfrom packs.gtm_material import assert_version_pin, staged_gtm")
raw = edits[path]
start = b"def test_actual_gtm_drafts_remain_unreviewed_unsealed_and_unseeded(tmp_path):"
end = b'@pytest.mark.parametrize("damage", ["unknown_region", "bool_confidence", "negative_confidence", "extra_fact", "duplicate_signal", "wrong_domain", "incomplete_existing", "wrong_existing_ref"])'
assert raw.count(start) == raw.count(end) == 1
left, right = raw.index(start), raw.index(end)
block = '''def test_actual_gtm_reviewed_material_is_admitted_and_seeded_idempotently(tmp_path):
    reviewed_inventory()
    assert orchestrator.admit_pack("gtm") == registry.resolve_pack("gtm")
    path = tmp_path / "reviewed-seed.db"
    conn = db.connect(path)
    try:
        db.ensure_schema(conn)
        orchestrator.seed_registered_engagements(conn)
        tables = ("engagements", "engagement_config", "engagement_assist_policy")
        before = {table: tuple(tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY slug")) for table in tables}
        assert repo.get_engagement(conn, "gtm") is not None
        for _ in range(3):
            orchestrator.seed_registered_engagements(conn)
        assert before == {table: tuple(tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY slug")) for table in tables}
        policy = orchestrator.verified_assist_policy(conn, "gtm")
        assert policy.total_calls_per_shift == 2
        assert [role.value for role in policy.allowed_roles] == ["HINT", "DIAGNOSIS"]
        for table in ("shifts", "artifact_versions", "exposure_items", "operating_selections", "ledger_events", "incidents"):
            assert conn.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0
    finally:
        conn.close()
    with TestClient(create_app(str(path))) as client:
        boards = client.get("/api/boards")
        assert boards.status_code == 200
        assert boards.json()[1]["availability"] == "AVAILABLE"


def test_unreviewed_gtm_declaration_refuses_before_seed_or_exposure(tmp_path, monkeypatch):
    packs = registry.registered_packs()
    monkeypatch.setattr(registry, "_PACKS", tuple(pack.model_copy(update={"reviewed_pins": ()})
                      if pack.slug == "gtm" else pack for pack in packs))
    with pytest.raises(registry.PackUnavailable):
        orchestrator.admit_pack("gtm")
    path = tmp_path / "unreviewed.db"
    with TestClient(create_app(str(path))) as client:
        boards = client.get("/api/boards")
        assert boards.status_code == 200
        assert boards.json()[1]["availability"] == "AWAITING_OPERATOR_REVIEW"
        assert client.post("/api/engagements/gtm/shifts").status_code == 404
    conn = db.connect(path)
    try:
        assert repo.get_engagement(conn, "gtm") is None
        assert conn.execute("SELECT count(*) FROM exposure_items WHERE engagement_slug='gtm'").fetchone()[0] == 0
    finally:
        conn.close()


def test_packet_inventory_binds_exact_approved_material_and_literal_pins():
    inventory = reviewed_inventory()
    assert len(inventory["files"]) == len(MATERIAL_PATHS) == 19
    assert inventory["workload_request_counts"] == [3, 3, 3]
    assert len(inventory["reviewed_pins"]) == 19 and len(inventory["documents"]) == 3
    assert {row["key"] for row in inventory["offline_fixture_pins"]} == {
        "gtm_starter", "gtm_compare_candidate_a", "gtm_compare_candidate_b"}


'''
# Replace only the prereview premise block; every later refusal/assessment guard stays.
ending = b"\r\n" if b"\r\n" in raw[left:right] else b"\n"
edits[path] = raw[:left] + block.replace("\n", ending.decode()).encode() + raw[right:]
replace(path, 'tmp_path / "hypothetical-package"', 'tmp_path / "fault-package"')
replace(path, 'pin_version(monkeypatch, source_version.json(), "gtm_starter")', 'assert_version_pin(source_version.json(), "gtm_starter")')
replace(path, 'pin_version(monkeypatch, source.json(), "gtm_compare_candidate_" + label.lower())', 'assert_version_pin(source.json(), "gtm_compare_candidate_" + label.lower())')
replace(path, 'def test_hypothetical_reviewed_copy_runs_six_fair_slots_without_business_writes(tmp_path, monkeypatch, reviewed_copy):',
        'def test_reviewed_production_runs_six_fair_slots_without_business_writes(tmp_path, monkeypatch):\n    reviewed_inventory()')
replace(path, 'proof = {"mode": "DISPOSABLE_HYPOTHETICAL_REVIEW", "production_sealed": False,\n                    "production_admitted": False,',
        'proof = {"mode": "PRODUCTION_REVIEWED_TRUSTED_LOCAL", "production_sealed": True,\n                    "production_admitted": True, "assist_gateway": "FAKE_NO_MODEL_CALL",')
replace(path, '"test_only_fixture_pins":', '"production_fixture_pins":')

replace("tests/packs/gtm_mutation_proofs.py", "test_hypothetical_reviewed_copy_runs_six_fair_slots_without_business_writes",
        "test_reviewed_production_runs_six_fair_slots_without_business_writes", count=2)

for path in ("tests/api/test_workplace_boards.py", "tests/packs/test_northline_review.py"):
    replace(path, '"AVAILABLE", "AWAITING_OPERATOR_REVIEW", "AVAILABLE"]', '"AVAILABLE", "AVAILABLE", "AVAILABLE"]')
replace("tests/packs/test_northline_review.py", 'assert registry.resolve_pack("gtm").reviewed_pins == ()',
        'assert orchestrator.admit_pack("gtm") == registry.resolve_pack("gtm")')
replace("tests/packs/test_northline_review.py", '== ["bookshop"], "drifted material must not seed Northline"',
        '== ["bookshop", "gtm"], "drifted material must not seed Northline"')
replace("tests/packs/test_northline_review.py", '== ["bookshop", "northline"], "admitted Northline must seed once"',
        '== ["bookshop", "gtm", "northline"], "admitted Northline must seed once"')

# These historical tests explicitly require both non-Bellwether packs unavailable.
for path in ("tests/packs/test_registry.py", "tests/api/test_pivot_routes.py",
             "tests/store/test_pivot_migration.py", "tests/orchestrator/test_fde_deployment.py"):
    replace(path, '(*packs[:2], packs[2].model_copy(update={"reviewed_pins": ()}))',
            '(packs[0], *(pack.model_copy(update={"reviewed_pins": ()}) for pack in packs[1:]))')
replace("tests/assist/test_gateway.py", '(bookshop, packs[1], packs[2].model_copy(update={"reviewed_pins": ()}))',
        '(bookshop, *(pack.model_copy(update={"reviewed_pins": ()}) for pack in packs[1:]))')

path = "tests/executor/test_conformance.py"
replace(path, '    compare_names = {f"compare_candidate_{label.lower()}" for label in config.PIVOT_COMPARE_CANDIDATE_SOURCES}',
        '    compare_names = {f"compare_candidate_{label.lower()}" for label in config.PIVOT_COMPARE_CANDIDATE_SOURCES}\n'
        '    gtm_names = {"gtm_starter", "gtm_compare_candidate_a", "gtm_compare_candidate_b"}')
replace(path, '    } | compare_names, (', '    } | compare_names | gtm_names, (')
replace(path, 'or name in compare_names:', 'or name in compare_names or name in gtm_names:')
replace(path, '\n\ndef test_pivot_review_bytes_and_catalog_binding():',
        '\n    # Each added GTM fixture is recomputed against the approved GTM contract/catalog.\n'
        '    from demos.gtm_review import offline_fixture_pins\n'
        '    gtm_catalog = contract_catalog.load_catalog("gtm", 1)\n'
        '    for row in offline_fixture_pins(gtm_catalog.content_hash):\n'
        '        assert config.TRUSTED_LOCAL_FIXTURES[row["key"]] == (row["artifact_content_hash"], row["files_hash"])\n'
        '\n\ndef test_pivot_review_bytes_and_catalog_binding():')

path = ".gitignore"
requests = ["gtm_pipeline_incident.jsonl", "gtm_compare_manifest.json", *(
    f"gtm_compare_pair_{n:02d}{suffix}" for n in (1, 2, 3) for suffix in (".jsonl", "_specs.json"))]
replace(path, "/shiftwork/fixtures/requests/\n",
        "/shiftwork/fixtures/requests/\n"
        "# S23 publication: preserve the incoming broad rule, expose only these approved files.\n"
        "!/shiftwork/fixtures/requests/\n/shiftwork/fixtures/requests/*\n" +
        "".join("!/shiftwork/fixtures/requests/" + name + "\n" for name in requests))

# Signed packet bytes and selected raw receipts must survive Windows Git filters.
path = ".gitattributes"
raw = (ROOT / path).read_bytes()
assert raw.endswith(b"shiftwork/fixtures/documents/gtm/workflow_treatments.md -text\r\n")
addition = b'''\n# Preserve the signed S23 packet and offline application receipts byte-for-byte.
docs/plans/shiftwork/slice23-gtm-operator-review-packet.md -text
docs/plans/shiftwork/slice23-gtm-review-inventory.json -text
docs/plans/shiftwork/evidence/slice23-approval-handoff-2026-10-07/authorization.json -text
docs/plans/shiftwork/evidence/slice23-lf-repair-2026-10-07/proposed-application/** -text
docs/plans/shiftwork/evidence/slice23-application-2026-10-07/** -text
'''
edits[path] = raw + addition.replace(b"\n", b"\r\n")

# All anchors were checked before any edit is written.
for path, raw in edits.items():
    (ROOT / path).write_bytes(raw)
print("Transitioned", len(edits), "files with exact anchors")
