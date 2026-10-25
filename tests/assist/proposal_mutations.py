"""S46 guard faults in a disposable source copy, with fresh runtime controls."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid


ROOT = Path(__file__).resolve().parents[2]
TARGET = "tests/assist/test_proposal.py::"
MAIN = "test_proposal_executes_retained_bytes_once_without_saving_a_version"
ACCEPT = "test_accepted_proposal_is_draft_only_and_attributed"


def faults():
    rows = []
    for field in ("cause", "falsifier", "public_test"):
        fields = tuple(value for value in ("cause", "falsifier", "public_test") if value != field)
        replacement = '(' + ', '.join(json.dumps(value) for value in fields) + ')'
        rows.append(("investigation-" + field, "shiftwork/experiments.py",
            '("cause", "falsifier", "public_test")', replacement,
            f"test_assist_proposal_run_requires_complete_investigation[{field}]",
            "incomplete investigation allowed proposal execution"))
    rows += [
        ("second-run", "shiftwork/experiments.py", "if proposal_event.diagnostic_run_id is not None:", "if False:", MAIN, "a second proposal run must refuse"),
        ("diagnostic-cap", "shiftwork/experiments.py", "if used >= DIAGNOSTIC_EXPERIMENTS_PER_SHIFT:", "if used > DIAGNOSTIC_EXPERIMENTS_PER_SHIFT:", "test_assist_proposal_run_requires_a_diagnostic_slot", "exhausted diagnostic budget allowed proposal execution"),
    ]
    for adapter in ("recorded", "local_process"):
        rows.append(("configured-" + adapter, "shiftwork/experiments.py",
            "if adapter != orchestrator.TokenFactoryAdapter.name:", "if False:",
            f"test_assist_proposal_never_runs_trusted_local_or_recorded[{adapter}]",
            "unsafe executor allowed a coach proposal"))
    rows += [
        ("queued-local", "shiftwork/experiments.py", "run.adapter != orchestrator.TokenFactoryAdapter.name\n                or ", "", "test_queued_proposal_rejects_an_unsafe_adapter_before_dispatch[local_process]", "unsafe queued proposal did not fail closed"),
        ("local-fallback", "shiftwork/experiments.py", "adapter = orchestrator.service_adapter(run, mission, context, live_budget=live_budget)", "adapter = orchestrator.LocalProcessAdapter()", MAIN, "a coach proposal fell back to a trusted local executor"),
        ("source-sha", "shiftwork/orchestrator.py", '_hash_bytes(files["service.py"].encode("utf-8")) != snapshot["proposal_source_sha256"]', "False", "test_proposal_hash_damage_refuses_before_execution[proposal_source_sha256]", "changed proposal identity allowed execution"),
        ("artifact-sha", "shiftwork/orchestrator.py", 'canonical.artifact_content_hash(files, canonical.contract_params_json(base.contract),\n                 base.contract_catalog_hash) != snapshot["artifact_content_hash"]', "False", "test_proposal_hash_damage_refuses_before_execution[artifact_content_hash]", "changed proposal identity allowed execution"),
        ("base-sha", "shiftwork/orchestrator.py", 'canonical.artifact_content_hash(base_files, canonical.contract_params_json(base.contract),\n                 base.contract_catalog_hash) != snapshot["base_hash"]', "False", "test_proposal_hash_damage_refuses_before_execution[base_hash]", "changed proposal identity allowed execution"),
        ("executed-source", "shiftwork/orchestrator.py", 'return base.model_copy(update={"files": files, "content_hash": snapshot["artifact_content_hash"],', 'return base.model_copy(update={"files": base.files, "content_hash": snapshot["artifact_content_hash"],', MAIN, "executed proposal bytes differ"),
        ("draft-copy", "shiftwork/orchestrator.py", 'repo.upsert_draft(conn, event.shift_id, version.files, _now())', 'pass', ACCEPT, "acceptance must copy the exact proposal into the draft"),
        ("auto-save", "shiftwork/orchestrator.py", 'repo.upsert_draft(conn, event.shift_id, version.files, _now())', 'repo.upsert_draft(conn, event.shift_id, version.files, _now())\n            repo.insert_version(conn, version.model_copy(update={"id": f"ver-{repo.count_versions(conn) + 1:04d}"}))', ACCEPT, "acceptance created a version, selection or business effect"),
        ("accepted-count", "shiftwork/orchestrator.py", 'generated_patch_accepted_count=accepted_count,', 'generated_patch_accepted_count=0,', ACCEPT, "acceptance must be counted once on explicit save"),
        ("learner-credit", "shiftwork/orchestrator.py", 'learner_edited=learner_edited,', 'learner_edited=True,', ACCEPT, "coach-only source was credited as a learner edit"),
        ("changed-draft", "shiftwork/orchestrator.py", 'if draft is None or draft[0] != json.loads(snapshot["base_files_json"]):', 'if False:', "test_acceptance_refuses_to_overwrite_a_later_draft_edit", "acceptance overwrote a later learner edit"),
        ("unicode-edit", "shiftwork/orchestrator.py", 'if draft is None or draft[0] != json.loads(snapshot["base_files_json"]):', 'if draft is None or canonical.content_hash(draft[0]) != canonical.content_hash(json.loads(snapshot["base_files_json"])):', "test_acceptance_preserves_a_byte_distinct_unicode_draft_edit[proposal0]", "NFC-equivalent learner bytes were silently overwritten"),
        ("eligibility", "shiftwork/experiments.py", '"eligible": False,', '"eligible": True,', "test_assist_proposal_run_sees_no_protected_material_and_cannot_qualify", "a proposal diagnostic qualified a version"),
        ("source-preview", "shiftwork/orchestrator.py", '"proposal_source": event.proposal_source,', '"proposal_source": None,', "test_proposal_preview_exposes_the_exact_retained_public_source", "the learner cannot review the exact proposed source"),
    ]
    rows.append(("atomic-save", "shiftwork/orchestrator.py",
        'if not conn.in_transaction:\n        conn.execute("BEGIN IMMEDIATE")\n    try:',
        'if not conn.in_transaction:\n        pass\n    try:',
        "test_saving_source_and_authorship_is_atomic_with_acceptance",
        "a concurrent acceptance attributed a coach patch to different saved bytes"))
    return rows + context_faults()


def context_faults():
    gateway = "shiftwork/assist/gateway.py"
    controller = "shiftwork/orchestrator.py"
    main = "test_coach_receives_exact_definitions_and_historical_identity"
    unavailable = "a missing, ambiguous or malformed trace was presented as evidence"
    rows = []
    def add(name, file, old, new, target, marker):
        rows.append(("context-" + name, file, old, new, target, marker))
    for name in ("TASK_VOCABULARY", "TOOLS", "ask_for_plan", "answer"):
        condition = (f'getattr(node, "name", None) != "{name}"' if name.islower() else
                     f'not any(isinstance(t, ast.Name) and t.id == "{name}" for t in (node.targets if isinstance(node, ast.Assign) else []))')
        add("definition-" + name, gateway, "for node in selected:", "for node in [node for node in selected if " + condition + "]:", main,
            "an exact public definition is missing from the outbound request")
    add("source-order", gateway, "for node in selected:", "for node in reversed(selected):", main, "source order changed")
    add("duplicate-definitions", gateway, "if any(found.count(name) != 1 for name in names):", "if any(found.count(name) < 1 for name in names):",
        "test_coach_falls_back_to_complete_source[duplicate]", "incomplete or ambiguous definitions silently dropped source")
    add("missing-definitions", gateway, "if any(found.count(name) != 1 for name in names):", "if False:",
        "test_coach_falls_back_to_complete_source[missing]", "incomplete or ambiguous definitions silently dropped source")
    add("syntax-fallback", gateway, "except SyntaxError:\n        return source", "except SyntaxError:\n        return ''",
        "test_coach_falls_back_to_complete_source[syntax]", "incomplete or ambiguous definitions silently dropped source")
    add("historical-identity", controller, '"artifact_content_hash": source_version.content_hash,',
        '"artifact_content_hash": repo.get_version(conn, proposal_base_version).content_hash,', main,
        "historical identity was replaced by current draft identity")
    for name, old in (
        ("run", "row.run_id == investigation.source_run_id\n            and "),
        ("stored_ordinal", "row.request_ordinal == investigation.source_request_ordinal\n            and "),
        ("kind", 'row.kind == "INFERENCE_RESULT"\n            and '),
        ("provenance", 'row.public_payload_json.get("source") == "controller_verified"\n            and '),
        ("payload_ordinal", 'and row.public_payload_json.get("request_ordinal") == investigation.source_request_ordinal'),
    ):
        add(name, controller, old, "", f"test_coach_excludes_unbound_trace[{name}]", "an unbound trace reached the coach")
    add("ordinal-type", controller, 'and type(row.public_payload_json.get("request_ordinal")) is int', "",
        "test_coach_labels_unavailable_trace[ordinal_bool]", unavailable)
    add("duplicate-traces", controller, "if len(rows) != 1:", "if not rows:", "test_coach_labels_unavailable_trace[duplicate]", unavailable)
    add("absent-label", controller, "if len(rows) != 1:\n        return unavailable", 'if len(rows) != 1:\n        return "{}"',
        "test_coach_labels_unavailable_trace[absent]", unavailable)
    add("missing-field", controller, 'if not all(field in payload for field in fields):\n        return unavailable',
        'if not all(field in payload for field in fields):\n        return json.dumps({field: payload.get(field) for field in fields})',
        "test_coach_labels_unavailable_trace[missing_field]", unavailable)
    for field in ("model", "plan_failure", "finish_reason"):
        old = 'for field in ("model", "plan_failure", "finish_reason")):'
        remaining = ', '.join(repr(name) for name in ("model", "plan_failure", "finish_reason") if name != field)
        add(field + "-type", controller, old, f"for field in ({remaining})):", f"test_coach_labels_unavailable_trace[{field}]", unavailable)
    add("output-type", controller, 'type(payload["output_tokens"]) is not int', 'not isinstance(payload["output_tokens"], int)',
        "test_coach_labels_unavailable_trace[output_tokens]", unavailable)
    add("output-negative", controller, 'or payload["output_tokens"] < 0', '',
        "test_coach_labels_unavailable_trace[negative_tokens]", unavailable)
    for name, old, new in (
        ("plan", 'not isinstance(plan, list)', 'False'),
        ("plan_step", 'set(step) != {"task_type", "tool_name"}', 'False'),
        ("plan_value", 'any(not isinstance(value, str) for value in step.values())', 'False'),
    ):
        add(name + "-type", controller, old, new, f"test_coach_labels_unavailable_trace[{name}]", unavailable)
    # Top-level scalar plans otherwise enter iteration and fail for a second reason;
    # deliberately model the incorrect permissive scalar projection for its own check.
    rows = [r if r[0] != "context-plan-type" else (*r[:2],
        'if plan is not None and (not isinstance(plan, list) or any(',
        'if isinstance(plan, list) and (False or any(', *r[4:]) for r in rows]
    add("whitelist", controller, 'return json.dumps({field: payload[field] for field in fields}, ensure_ascii=False)',
        'return json.dumps(payload, ensure_ascii=False)', "test_coach_forwards_valid_plan_without_other_observation_fields", "private observation content escaped into a serialized context")
    add("controller-cap", controller,
        'if len(prompt.encode("utf-8")) + len(assist_system_message(role).encode("utf-8")) > MAX_INPUT_BYTES:',
        'if False:', "test_coach_context_cap_refuses_without_reservation[selected]", "oversized complete coach context was admitted")
    add("gateway-cap", gateway,
        'if sum(len(message["content"].encode("utf-8")) for message in body["messages"]) > MAX_INPUT_BYTES:',
        'if False:', "tests/assist/test_gateway.py::test_gateway_counts_complete_role_specific_utf8_input_before_transport[PATCH_PROPOSAL]",
        "gateway admitted a complete UTF-8 request over its input cap")
    add("system-evidence", gateway,
        'supplied public service.py source and controller-verified public inference result', 'supplied context', main,
        "patch role lacks authority for its supplied public evidence")
    add("system-diagnostic", gateway, ' A successful diagnostic does not prove a repair.', '', main,
        "a diagnostic was treated as proof of repair")
    add("physical-lines", gateway, 'source.encode("utf-8").splitlines(keepends=True)',
        '[line.encode("utf-8") for line in source.splitlines(keepends=True)]',
        r"test_coach_source_preserves_unicode_physical_lines[\u2028]", "Unicode physical lines changed exact definition bytes")
    add("same-line", gateway, 'else node.end_col_offset', 'else len(lines[end])',
        "test_coach_source_excludes_same_line_unselected_statement", "a same-line unselected statement reached the excerpt")
    add("destructuring", gateway, 'for binding in targets for target in ast.walk(binding)', 'for target in targets',
        r'test_coach_source_rebinding_uses_whole_source[TASK_VOCABULARY, TOOLS = ("changed",), ("different",)\n]',
        "a duplicate top-level binding was silently omitted")
    add("plan-step-object", controller, 'not isinstance(step, dict) or set(step) != {"task_type", "tool_name"}\n            or any(not isinstance(value, str) for value in step.values())',
        'isinstance(step, dict) and (set(step) != {"task_type", "tool_name"} or any(not isinstance(value, str) for value in step.values()))', "test_coach_labels_unavailable_trace[plan_scalar_step]", unavailable)
    for identity, fallback in (("run", 'source_run = type("WrongHistoricalRun", (), {"id": investigation.source_run_id, "artifact_version_id": proposal_base_version})()'),
                               ("version", 'source_version = repo.get_latest_version(conn, shift.id)')):
        variable = "source_" + identity
        add("missing-" + identity, controller,
            f'if {variable} is None:\n            raise LifecycleError("conflict", "the historical source identity is unavailable")',
            f'if {variable} is None:\n            {fallback}',
            f"test_coach_refuses_missing_historical_identity[{identity}]", "missing historical identity allowed a coach call")
    for field, sentinel in (("reasoning", "PROVIDER_REASONING_PRIVATE"), ("grades", "PROTECTED_GRADE_PRIVATE"),
                            ("expected_ref", r"C:\private\sealed.json")):
        add("private-" + field, controller,
            'return json.dumps({field: payload[field] for field in fields}, ensure_ascii=False)',
            'return json.dumps({**{field: payload[field] for field in fields}, "leak": payload["' + field + '"]}, ensure_ascii=False)',
            "test_coach_forwards_valid_plan_without_other_observation_fields", "private observation content escaped into a serialized context: " + sentinel)
    add("private-raw", controller, 'return json.dumps({field: payload[field] for field in fields}, ensure_ascii=False)',
        'return json.dumps({**{field: payload[field] for field in fields}, "leak": repo.list_observations(conn, investigation.source_run_id)[0].raw_payload_ref}, ensure_ascii=False)',
        "test_coach_forwards_valid_plan_without_other_observation_fields", "private observation content escaped into a serialized context: RAW_PROVIDER_PRIVATE")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--only")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    selected = [row for row in faults() if args.only is None or row[0] == args.only]
    assert selected, "no selected S46 mutation"
    pristine = {row[1]: (ROOT / row[1]).read_bytes() for row in selected}
    for name, file, old, _, _, _ in selected:
        assert pristine[file].decode().count(old) == 1, f"non-unique fault anchor: {name}"
    results = []
    with tempfile.TemporaryDirectory(prefix="shiftwork-s46-faults-") as directory:
        copy = Path(directory)
        for folder in ("shiftwork", "tests"):
            shutil.copytree(ROOT / folder, copy / folder, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(ROOT / "pyproject.toml", copy / "pyproject.toml")

        def run(name, phase, target):
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                       PYTHONPYCACHEPREFIX=str(args.out / ("cache-" + uuid.uuid4().hex)))
            result = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", (target if "::" in target else TARGET + target)],
                cwd=copy, env=env, capture_output=True, text=True, timeout=120)
            (args.out / f"{name}-{phase}.txt").write_text(result.stdout + result.stderr)
            return result.returncode, result.stdout + result.stderr

        for name, file, old, new, target, marker in selected:
            path = copy / file
            clean_code, clean = run(name, "clean", target)
            assert clean_code == 0, f"clean control failed: {name}"
            try:
                path.write_bytes(pristine[file].decode().replace(old, new, 1).encode())
                code, output = run(name, "fault", target)
                killed = code != 0 and "AssertionError" in output and marker in output and "1 failed" in output and "ERROR at setup" not in output
            finally:
                path.write_bytes(pristine[file])
            assert path.read_bytes() == pristine[file], f"restoration differs: {name}"
            restored_code, restored = run(name, "restored", target)
            results.append({"name": name, "target": target, "intended_assertion_failed": killed,
                            "clean_passed": clean_code == 0, "restored_passed": restored_code == 0,
                            "source_sha256": hashlib.sha256(pristine[file]).hexdigest()})
            (args.out / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
            print(name, "PASS" if killed and restored_code == 0 else "INVALID", flush=True)
            assert killed and restored_code == 0, f"fault did not prove its named assertion: {name}"
    for file, data in pristine.items():
        assert (ROOT / file).read_bytes() == data, "working source changed during the proof run"


if __name__ == "__main__":
    main()
