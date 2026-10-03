"""Independent guard faults for typed aspects and exact compatibility."""
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
TEST = "tests/orchestrator/test_acceptance_aspects.py"
POLICY = "shiftwork/domain/comparison.py"
PARAMETERS = "test_kind_parameters_fail_independently"
CASES = []


def fault(name, old, new, node, file=POLICY):
    CASES.append(dict(name=name, file=file, old=old, new=new,
                      tests=shlex.quote(f"{TEST}::{node}"), expect=node))


for name, old, new in (
    ("kind_vocabulary", "    kind: AcceptanceAspectKind", "    kind: str"),
    ("named_task_required", "not self.task_id or not self.expected_outcomes", "False or not self.expected_outcomes"),
    ("named_outcomes_required", "not self.task_id or not self.expected_outcomes", "not self.task_id or False"),
    ("named_reason_forbidden", "not self.expected_outcomes or self.reason_code is not None", "not self.expected_outcomes or False"),
    ("reason_required", "self.reason_code is None or self.task_id is not None", "False or self.task_id is not None"),
    ("reason_task_forbidden", "self.reason_code is None or self.task_id is not None", "self.reason_code is None or False"),
    ("reason_outcomes_forbidden", "self.task_id is not None or self.expected_outcomes:\n                raise ValueError(\"no-task", "self.task_id is not None or False:\n                raise ValueError(\"no-task"),
    ("every_task_forbidden", "elif self.task_id is not None or self.expected_outcomes", "elif False or self.expected_outcomes"),
    ("every_outcomes_forbidden", "elif self.task_id is not None or self.expected_outcomes", "elif self.task_id is not None or False"),
    ("every_reason_forbidden", "elif self.task_id is not None or self.expected_outcomes or self.reason_code is not None", "elif self.task_id is not None or self.expected_outcomes or False"),
    ("reason_vocabulary", "    reason_code: ReasonCode | None = None", "    reason_code: str | None = None"),
    ("outcome_vocabulary", "    expected_outcomes: tuple[TaskOutcome, ...] = ()", "    expected_outcomes: tuple[str, ...] = ()"),
):
    fault(name, old, new, PARAMETERS)

fault("named_task_spec_binding", "and aspect.task_id not in {task.id for task in case.stimulus.task_spec.tasks}",
      "and False", "test_invalid_aspect_refuses_before_any_write")
node = "test_legacy_decoder_pin_owner_and_raw_type_checks_are_independent"
fault("legacy_complete_model_pin", "if pinned is None or case.family != \"task_completion\":",
      "if False:\n            pass\n        if pinned is None:\n            pinned = next(iter(_LEGACY_ASPECT_PINS.values()))\n        if case.family != \"task_completion\":", node)
fault("legacy_raw_json_types", "if _LEGACY_SOURCE_TO_SNAPSHOT.get(_payload_sha256(raw)) != _payload_sha256(case.model_dump(mode=\"json\")):",
      "if False:", node)
fault("legacy_owner_binding", "and engagement_slug != \"bookshop\":", "and False:", node)
fault("family_validation_removed", "validate_acceptance_aspect(case, engagement_slug=slug)",
      "None", "test_family_validates_typed_aspects_without_deeper_snapshot_guard", file="shiftwork/sealed/store.py")
fault("snapshot_owner_binding_removed", "validate_acceptance_aspect(case, engagement_slug=reservation.engagement_slug)",
      'validate_acceptance_aspect(case, engagement_slug="bookshop")',
      "test_reserved_legacy_uses_pins_without_current_file_and_refuses_cross_pack", file="shiftwork/sealed/store.py")
fault("named_outcome_assessment_removed", "return by_id[aspect.task_id].outcome in aspect.expected_outcomes",
      "return True", "test_each_typed_aspect_passes_and_fails")
fault("no_reason_assessment_removed", "return all(aspect.reason_code not in entry.reason_codes for entry in assessments)",
      "return True", "test_each_typed_aspect_passes_and_fails")
fault("every_result_assessment_removed", "return all(by_id[task.id].outcome is not TaskOutcome.MISSING_OUTPUT\n                   for task in spec.tasks if task.required)",
      "return True", "test_each_typed_aspect_passes_and_fails")
CASES.append(dict(name="typed_scanner_kind_omitted", file="shiftwork/sealed/store.py",
    old="                needles.add(kind)", new="                pass",
    tests="tests/packs/test_seeding.py::test_registered_families_supply_serialized_scanner_needles",
    expect="test_registered_families_supply_serialized_scanner_needles"))


if __name__ == "__main__":
    outcomes = [runner.run_mutation(case) for case in CASES]
    print(json.dumps(outcomes, indent=2))
    raise SystemExit(0 if all(row["status"] == "FAIL_CAUGHT" and row["sha256_restored"] for row in outcomes) else 1)
