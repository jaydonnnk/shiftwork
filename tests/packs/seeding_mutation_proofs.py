"""Failing-capability proof for registered seeding, with exact-byte restoration."""

import importlib.util
import json
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("shared_mutations", ROOT / "tests/mutation_proofs.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

TEST = "tests/packs/test_seeding.py"
SEEDS = "test_startup_seeds_only_admitted_packs_idempotently"
CASES = [
    dict(name="startup_registered_seeding_skipped", file="shiftwork/app.py",
         old="        orchestrator.seed_registered_engagements(conn)", new="        pass",
         tests=f"{TEST}::{SEEDS}", expect=SEEDS),
    dict(name="startup_seeds_only_first_pack", file="shiftwork/orchestrator.py",
         old='    for declaration in pack_registry.registered_packs():\n        try:\n            pack = admit_pack(declaration.slug)',
         new='    for declaration in pack_registry.registered_packs()[:1]:\n        try:\n            pack = admit_pack(declaration.slug)',
         tests=f"{TEST}::{SEEDS}", expect=SEEDS),
    dict(name="startup_material_admission_bypassed", file="shiftwork/orchestrator.py",
         old="            pack = admit_pack(declaration.slug)",
         new="            pack = pack_registry.resolve_pack(declaration.slug)",
         tests=shlex.quote(f"{TEST}::test_unavailable_pack_never_seeds_and_existing_history_survives[stale_pin]"),
         expect="test_unavailable_pack_never_seeds_and_existing_history_survives[stale_pin]"),
    dict(name="startup_attempt_families_substituted", file="shiftwork/orchestrator.py",
         old='            enabled_check_families=tuple(f.family for f in pack.families\n                                       if f.family_class is pack_registry.FamilyClass.ATTEMPT),',
         new='            enabled_check_families=config.BOOKSHOP_FAMILIES,',
         tests=f"{TEST}::{SEEDS}", expect=SEEDS),
    dict(name="startup_rewrites_historical_config", file="shiftwork/store/repo.py",
         old='        "INSERT OR IGNORE INTO engagement_config (slug, business_kind, assist_level, "',
         new='        "INSERT OR REPLACE INTO engagement_config (slug, business_kind, assist_level, "',
         tests=f"{TEST}::{SEEDS}", expect=SEEDS),
]

for name, file, old, new, node in (
    ("diagnostic_global_mission_substituted", "shiftwork/orchestrator.py",
     '    mission_path = config.PACKAGE_DIR / pack.mission_path\n    state_path = config.PACKAGE_DIR / pack.public_state_path',
     '    mission_path = config.PIVOT_MISSION\n    state_path = config.PACKAGE_DIR / pack.public_state_path',
     "test_public_context_reads_owning_pack"),
    ("diagnostic_global_state_substituted", "shiftwork/orchestrator.py",
     '    state_path = config.PACKAGE_DIR / pack.public_state_path',
     '    state_path = config.PIVOT_PUBLIC_STATE', "test_public_context_reads_owning_pack"),
    ("diagnostic_global_request_substituted", "shiftwork/orchestrator.py",
     '    batch_bytes = (config.PACKAGE_DIR / pack.incident_request_path).read_bytes()',
     '    batch_bytes = config.PIVOT_INCIDENT_REQUESTS.read_bytes()', "test_public_context_reads_owning_pack"),
    ("comparison_global_manifest_substituted", "shiftwork/comparison_flow.py",
     '    manifest_path = config.PACKAGE_DIR / pack.manifest_path',
     '    manifest_path = config.PIVOT_COMPARE_MANIFEST', "test_comparison_workloads_read_owning_manifest"),
    ("scanner_omits_other_registered_packs", "shiftwork/orchestrator.py",
     '    for pack in pack_registry.registered_packs():\n        for declaration in pack.families:',
     '    for pack in pack_registry.registered_packs()[:1]:\n        for declaration in pack.families:',
     "test_registered_families_supply_serialized_scanner_needles"),
    ("family_index_substitutes_bookshop", "shiftwork/sealed/store.py",
     '    for declaration in resolve_pack(slug).families:',
     '    for declaration in resolve_pack("bookshop").families:', "test_family_index_resolves_owning_pack"),
):
    CASES.append(dict(name=name, file=file, old=old, new=new,
                      tests=shlex.quote(f"{TEST}::{node}"), expect=node))

for kind, ending in (
    ("qualifying", "    failed reservation consumes nothing."),
    ("later", "    choice, resolve an incident or rewrite the ledger."),
):
    anchor = ending + '\n    """\n    conn.execute("BEGIN IMMEDIATE")\n    try:\n        shift = _require_open_shift(conn, shift_id)\n        pack = orchestrator.admit_pack(shift.engagement_slug)'
    node = f"test_comparison_admits_owning_pack_before_any_write[{kind}]"
    CASES.append(dict(name=f"{kind}_reservation_admission_bypassed", file="shiftwork/comparison_flow.py",
                      old=anchor, new=anchor.replace("pack = orchestrator.admit_pack(shift.engagement_slug)",
                                                    "pack = orchestrator.pack_registry.resolve_pack(shift.engagement_slug)"),
                      tests=shlex.quote(f"{TEST}::{node}"), expect=node))


def main():
    outcomes = [runner.run_mutation(case) for case in CASES]
    print(json.dumps(outcomes, indent=2))
    return 0 if all(row["status"] == "FAIL_CAUGHT" and row["sha256_restored"] for row in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
