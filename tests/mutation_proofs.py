"""Mutation proofs for the Slice 7 guard branches.

Each mutation independently breaks one guard branch with a valid code change,
runs the named test selection, and requires that the named expected test fails
with an assertion-level outcome: AssertionError, or pytest's Failed (for
example "DID NOT RAISE" from pytest.raises). A mutation that only trips a
collection error, an unexpected exception or a timeout is NOT a proof of the
guard and is reported distinctly, so a crash can never masquerade as coverage.
Every file is restored byte-identically (sha256 before == after). Windows
trap: restoration uses raw bytes, never git checkout.
"""

import hashlib
import shlex
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PYTHON = str(REPO / ".venv" / "Scripts" / "python.exe")

MUTATIONS = [
    {
        "name": "budget_comparison_off_by_one",
        "file": "shiftwork/orchestrator.py",
        "old": b"if used >= limit:",
        "new": b"if used > limit:",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_budget_enforced_controller_side",
        "expect": "test_budget_enforced_controller_side",
    },
    {
        "name": "exposure_filter_removed",
        "file": "shiftwork/sealed/rotation.py",
        "old": b"return tuple(case for case in cases if variant_ref(case) not in exposed)",
        "new": b"return tuple(case for case in cases)",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_select_variant_excludes_exposed_variants",
        "expect": "test_select_variant_excludes_exposed_variants",
    },
    {
        "name": "select_variant_tiebreak_reversed",
        "file": "shiftwork/sealed/rotation.py",
        "old": b"return min(available, key=lambda case: (min(case.request_ordinals), cases.index(case)))",
        "new": b"return min(available, key=lambda case: (min(case.request_ordinals), len(cases) - 1 - cases.index(case)))",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_select_variant_ordinal_tie_prefers_earlier_file_order",
        "expect": "test_select_variant_ordinal_tie_prefers_earlier_file_order",
    },
    {
        "name": "shared_ordinal_misconfig_not_raised",
        "file": "shiftwork/sealed/rotation.py",
        "old": b"""    if len(tuples) != 1:
        raise RotationMisconfigured(
            "drawn variants must share exactly one request ordinal; got "
            + ", ".join(f"{family}: {case.request_ordinals}" for family, case in sorted(draws.items()))
        )""",
        "new": b"""    if len(tuples) != 1:
        pass""",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_shared_ordinal_rejects_mismatched_draws",
        "expect": "test_shared_ordinal_rejects_mismatched_draws",
    },
    {
        "name": "shared_ordinal_multi_ordinal_not_raised",
        "file": "shiftwork/sealed/rotation.py",
        "old": b"""    if len(shared) != 1:
        raise RotationMisconfigured(f"a drawn variant binds several request ordinals: {shared}")""",
        "new": b"""    if len(shared) != 1:
        pass  # MUTATION: was raise""",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_shared_ordinal_rejects_multi_ordinal_variant",
        "expect": "test_shared_ordinal_rejects_multi_ordinal_variant",
    },
    {
        "name": "rollback_except_path_removed",
        "file": "shiftwork/orchestrator.py",
        "old": b"""    except Exception:
        conn.rollback()
        raise
    return run""",
        "new": b"""    except Exception:
        raise
    return run""",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_reservation_fault_rolls_back_the_whole_reservation",
        "expect": "test_reservation_fault_rolls_back_the_whole_reservation",
    },
    {
        "name": "resolution_gate_version_removed",
        "file": "shiftwork/orchestrator.py",
        "old": b"if opening is None or opening.artifact_version_id == run.artifact_version_id:",
        "new": b"if opening is None:",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_repair_resolution_same_version_never_resolves",
        "expect": "test_repair_resolution_same_version_never_resolves",
    },
    {
        "name": "resolution_gate_regression_removed",
        "file": "shiftwork/orchestrator.py",
        "old": b"if regression is None or regression.verdict != \"pass\":",
        "new": b"if regression is None:",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_repair_resolution_failing_regression_never_resolves",
        "expect": "test_repair_resolution_failing_regression_never_resolves",
    },
    {
        "name": "resolution_gate_acceptance_removed",
        "file": "shiftwork/orchestrator.py",
        "old": b"if acceptance_result is None or acceptance_result.verdict != \"pass\":",
        "new": b"if acceptance_result is None:",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_repair_resolution_failing_acceptance_never_resolves",
        "expect": "test_repair_resolution_failing_acceptance_never_resolves",
    },
    {
        "name": "invalidate_state_filter_removed",
        "file": "shiftwork/store/repo.py",
        "old": b"\"UPDATE rotation_draws SET state = ? WHERE engagement_slug = ? AND family = ? AND state = ?\",\n        (DrawState.INVALIDATED.value, slug, family, DrawState.ACTIVE.value),",
        "new": b"\"UPDATE rotation_draws SET state = ? WHERE engagement_slug = ? AND family = ?\",\n        (DrawState.INVALIDATED.value, slug, family),",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_invalidate_rotation_group_retires_only_active_draws",
        "expect": "test_invalidate_rotation_group_retires_only_active_draws",
    },
    {
        "name": "cycle_hardcoded_to_one",
        "file": "shiftwork/orchestrator.py",
        "old": b"cycle=sealed_store.family_cycle(family),",
        "new": b"cycle=1,",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_rotation_exhaustion_fail_closed",
        "expect": "test_rotation_exhaustion_fail_closed",
    },
    {
        "name": "validate_refill_exposed_rejection_removed",
        "file": "shiftwork/sealed/rotation.py",
        "old": b"""        if ref in exposed:
            raise RotationMisconfigured(
                f"refill reuses the exposed identity of variant {case.id!r} ({ref})"
            )""",
        "new": b"""        if ref in exposed:
            pass  # MUTATION: was raise""",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_rotation_exhaustion_fail_closed",
        "expect": "test_rotation_exhaustion_fail_closed",
    },
    {
        "name": "validate_refill_repeated_rejection_removed",
        "file": "shiftwork/sealed/rotation.py",
        "old": b"""        if ref in seen:
            raise RotationMisconfigured(f"refill repeats the identity of variant {case.id!r} ({ref})")""",
        "new": b"""        if ref in seen:
            pass  # MUTATION: was raise""",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_rotation_exhaustion_fail_closed",
        "expect": "test_rotation_exhaustion_fail_closed",
    },
    {
        "name": "sealed_store_schema_validation_removed",
        "file": "shiftwork/sealed/store.py",
        "old": b"""    if file_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnsupportedSealedSchema(
            f"sealed family {family!r} declares unsupported file schema_version {file_version!r}"
        )""",
        "new": b"""    if file_version not in SUPPORTED_SCHEMA_VERSIONS:
        pass""",
        "tests": "tests/sealed/test_store_validation.py",
        "expect": "test_unsupported_file_schema_version_raises",
    },
    {
        "name": "sealed_store_ordinal_validation_removed",
        "file": "shiftwork/sealed/store.py",
        "old": b"""        if (
            not isinstance(ordinals, list)
            or not ordinals
            or any(isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1 for ordinal in ordinals)
            or len(set(ordinals)) != len(ordinals)
        ):
            raise InvalidSealedCase(
                f"sealed case {raw.get('id')!r} needs a non-empty, duplicate-free list of "
                f"positive request ordinals; got {ordinals!r}"
            )""",
        "new": b"""        if (
            not isinstance(ordinals, list)
            or not ordinals
            or any(isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1 for ordinal in ordinals)
            or len(set(ordinals)) != len(ordinals)
        ):
            pass""",
        "tests": "tests/sealed/test_store_validation.py",
        "expect": "test_empty_ordinals_raises",
    },
    {
        "name": "load_drawn_cases_incident_filter_removed",
        "file": "shiftwork/sealed/store.py",
        "old": b"if incident.state is not IncidentState.OPEN:",
        "new": b"if False:",
        "tests": "tests/orchestrator/test_budget_rotation.py::test_resolved_incident_regression_excluded_from_later_run",
        "expect": "test_resolved_incident_regression_excluded_from_later_run",
    },
    {
        "name": "migration_v2_log_ref_skipped",
        "file": "shiftwork/store/db.py",
        "old": b"""        if current == 2:
            conn.execute("ALTER TABLE run_outputs ADD COLUMN log_ref TEXT")""",
        "new": b"""        if current == 2:
            pass  # MUTATION: was ALTER TABLE run_outputs ADD COLUMN log_ref""",
        "tests": "tests/executor/test_conformance.py::test_existing_schema_two_gets_log_column_without_data_loss",
        "expect": "test_existing_schema_two_gets_log_column_without_data_loss",
    },
    {
        "name": "migration_v2_runs_columns_skipped",
        "file": "shiftwork/store/db.py",
        "old": b"        if current in (2, 3):",
        "new": b"        if current in (3,):",
        "tests": "tests/executor/test_conformance.py::test_existing_schema_two_gets_log_column_without_data_loss",
        "expect": "test_existing_schema_two_gets_log_column_without_data_loss",
    },
    {
        "name": "migration_v3_runs_columns_skipped",
        "file": "shiftwork/store/db.py",
        "old": b"        if current in (2, 3):",
        "new": b"        if current == 2:",
        "tests": "tests/executor/test_conformance.py::test_existing_schema_three_gets_rotation_columns_without_data_loss",
        "expect": "test_existing_schema_three_gets_rotation_columns_without_data_loss",
    },
    {
        "name": "migration_backfill_removed",
        "file": "shiftwork/store/db.py",
        "old": b"""            conn.execute(
                "UPDATE runs SET request_batch_ref = ?, shop_snapshot_ref = ? "
                "WHERE request_batch_ref IS NULL",
                (_LEGACY_RUN_BATCH, _LEGACY_RUN_SNAPSHOT),
            )""",
        "new": b"""            pass  # MUTATION: was the legacy-run backfill UPDATE""",
        "tests": "tests/executor/test_conformance.py::test_existing_schema_two_gets_log_column_without_data_loss",
        "expect": "test_existing_schema_two_gets_log_column_without_data_loss",
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def catch_kind(message: str) -> str:
    """Assertion-level catches only.

    pytest's junit message for a failed assertion is the rendered assertion
    ("assert 409 == 202"), or "AssertionError: ..." when the assertion carried a
    message; pytest.raises and pytest.fail failures read "Failed: ...". Any
    exception class name (sqlite3.ProgrammingError, ValueError, ...) is a crash.
    """
    head = (message or "").strip()
    if head.startswith(("assert", "AssertionError", "Failed:")):
        return "clean"
    return "incidental"


def summary_line(stdout: str) -> str:
    """The pytest summary line, ignoring any trailing stderr noise."""
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith(("=", "FAILED", "ERROR")):
            continue
        if "passed" in line or "failed" in line or "error" in line or "no tests ran" in line:
            return line
    return lines[-1] if lines else "no output"


def read_junit(report: Path) -> tuple[dict[str, dict], dict[str, str]]:
    """Per-test failure kinds and setup errors from a pytest junit report."""
    failures: dict[str, dict] = {}
    errors: dict[str, str] = {}
    if not report.exists():
        return failures, errors
    for case in ET.parse(report).getroot().iter("testcase"):
        module = (case.get("classname") or "").lstrip(".").replace(".", "/")
        key = f"{module}.py::{case.get('name')}"
        for failure in case.findall("failure"):
            message = failure.get("message") or ""
            failures[key] = {"kind": catch_kind(message), "message": message}
        for error in case.findall("error"):
            errors[key] = error.get("message") or ""
    return failures, errors


def run_mutation(mutation: dict) -> dict:
    target = REPO / mutation["file"]
    original_bytes = target.read_bytes()
    original_hash = hashlib.sha256(original_bytes).hexdigest()

    old = mutation["old"]
    new = mutation["new"]
    if isinstance(old, str):
        old = old.encode("utf-8")
    if isinstance(new, str):
        new = new.encode("utf-8")

    # Handle CRLF: the worktree may use CRLF
    if old not in original_bytes:
        old_crlf = old.replace(b"\n", b"\r\n")
        if old_crlf in original_bytes:
            old = old_crlf
            new = new.replace(b"\n", b"\r\n")
        else:
            return {"name": mutation["name"], "status": "SKIP", "reason": "pattern not found"}

    count = original_bytes.count(old)
    if count != 1:
        return {"name": mutation["name"], "status": "SKIP", "reason": f"pattern found {count} times"}

    mutated = original_bytes.replace(old, new, 1)
    target.write_bytes(mutated)

    timeout = False
    stdout = ""
    failures: dict[str, dict] = {}
    errors: dict[str, str] = {}
    try:
        test_args = shlex.split(mutation["tests"])
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "junit.xml"
            result = subprocess.run(
                [PYTHON, "-m", "pytest", *test_args, "-q", "--tb=short", "--no-header", "-rf",
                 f"--junitxml={report}"],
                capture_output=True, text=True, cwd=str(REPO), timeout=240,
            )
            stdout = result.stdout + "\n" + result.stderr
            failures, errors = read_junit(report)
    except subprocess.TimeoutExpired:
        timeout = True
    finally:
        target.write_bytes(original_bytes)
        restored_hash = sha256(target)
        assert restored_hash == original_hash, (
            f"RESTORATION FAILED for {mutation['name']}: {restored_hash} != {original_hash}"
        )

    base = {"name": mutation["name"], "sha256_restored": restored_hash == original_hash}
    last_line = summary_line(stdout)

    if timeout:
        return {**base, "status": "NOT_CAUGHT", "detail": "TIMEOUT: no test failed"}

    expect = mutation["expect"]
    matched = [key for key in failures if expect in key]

    if not matched:
        if failures or errors:
            detail = "expected " + expect + " to fail; failures: " + ", ".join(sorted(failures))
            if errors:
                detail += "; errors: " + ", ".join(sorted(errors))
        else:
            detail = "no test-level failure (" + last_line + ")"
        return {**base, "status": "NOT_CAUGHT", "detail": detail}

    entry = failures[matched[0]]
    message = entry["message"].replace("\n", " ")[:110]
    if entry["kind"] != "clean":
        return {**base, "status": "CAUGHT_INCIDENTAL",
                "detail": f"{expect}: {message} (not an assertion-level failure)"}

    return {**base, "status": "FAIL_CAUGHT", "detail": f"{message} [{last_line}]"}


def main():
    results = []
    for mutation in MUTATIONS:
        print(f"  mutating: {mutation['name']}...", end=" ", flush=True)
        result = run_mutation(mutation)
        results.append(result)
        print(result["status"])

    print("\n=== MUTATION PROOF TABLE ===")
    print(f"{'mutation':<47} {'status':<17} {'sha256 ok':<10} catch")
    print("-" * 150)
    for r in results:
        sha_ok = r.get("sha256_restored", "N/A")
        print(f"{r['name']:<47} {r['status']:<17} {str(sha_ok):<10} "
              f"{r.get('detail', r.get('reason', ''))}")

    caught = [r for r in results if r["status"] == "FAIL_CAUGHT"]
    incidental = [r["name"] for r in results if r["status"] == "CAUGHT_INCIDENTAL"]
    not_caught = [r["name"] for r in results if r["status"] == "NOT_CAUGHT"]
    skipped = [r["name"] for r in results if r["status"] == "SKIP"]

    print(f"\nassertion-level catches: {len(caught)}/{len(results)}")
    if incidental:
        print(f"INCIDENTAL catches (crash, not an assertion-level proof): {incidental}")
    if not_caught:
        print(f"NOT CAUGHT (guard may be vacuous): {not_caught}")
    if skipped:
        print(f"SKIPPED (pattern issue): {skipped}")
    return 1 if len(caught) != len(results) else 0


if __name__ == "__main__":
    sys.exit(main())
