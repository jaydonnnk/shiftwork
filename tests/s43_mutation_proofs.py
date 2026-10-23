"""S43 mutation proofs: each guard fails its own named test, then is restored byte-identically.

Each entry is (name, path, old, new) against T, or (name, path, old, new, target, expected_test)
where expected_test must be among the failures.
"""
import hashlib, subprocess, sys
from pathlib import Path
T = "tests/executor/test_task_plan_gateway.py"
M = [
 ("repair_drop_bad_steps", "shiftwork/gateway/service_inference.py",
  '    if any(step.task_type not in task_vocabulary for step in plan.plan):\n        return None, "TASK_TYPE_UNKNOWN"\n    if any(step.tool_name not in allowed_tool_names for step in plan.plan):\n        return None, "TOOL_NOT_ALLOWED"\n    return [step.model_dump() for step in plan.plan], None',
  '    kept = [s.model_dump() for s in plan.plan if s.task_type in task_vocabulary and s.tool_name in allowed_tool_names]\n    return (kept or None), (None if kept else "SCHEMA_INVALID")'),
 ("skip_task_check", "shiftwork/gateway/service_inference.py",
  '    if any(step.task_type not in task_vocabulary for step in plan.plan):\n        return None, "TASK_TYPE_UNKNOWN"\n', ''),
 ("skip_tool_check", "shiftwork/gateway/service_inference.py",
  '    if any(step.tool_name not in allowed_tool_names for step in plan.plan):\n        return None, "TOOL_NOT_ALLOWED"\n', ''),
 ("strip_fences", "shiftwork/gateway/service_inference.py",
  'plan = TaskPlan.model_validate_json(content.strip())',
  'plan = TaskPlan.model_validate_json(content.strip().removeprefix("```json").removesuffix("```").strip())'),
 ("allow_extra_step_keys", "shiftwork/gateway/protocol.py",
  'class TaskPlanStep(BaseModel):\n    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)',
  'class TaskPlanStep(BaseModel):\n    model_config = ConfigDict(extra="ignore", frozen=True, strict=True)'),
 ("request_accepts_extra", "shiftwork/gateway/protocol.py",
  'class InferenceRequest(BaseModel):\n    model_config = ConfigDict(extra="forbid", frozen=True)',
  'class InferenceRequest(BaseModel):\n    model_config = ConfigDict(extra="ignore", frozen=True)'),
 ("failure_raises", "shiftwork/gateway/service_inference.py",
  '        return {"kind": "inference_reply", "plan": plan, "plan_failure": plan_failure}',
  '        if plan_failure:\n            raise GatewayRejected(plan_failure)\n        return {"kind": "inference_reply", "plan": plan, "plan_failure": plan_failure}'),
 ("driver_no_tool_check", "shiftwork/executor/tokenfactory.py",
  "                        if plan is not None and any(step.get('tool_name') not in allowed for step in plan):\n                            return self.reply(403, {'error': 'TOOL_NOT_ALLOWED'})\n", ''),
 ("legacy_mode_lost", "shiftwork/gateway/service_inference.py",
  '        if self.policy.task_vocabulary:\n            return self._plan_reply(', '        if True:\n            return self._plan_reply('),
 ("dup_vocab_allowed", "shiftwork/gateway/service_inference.py",
  '        if len(set(policy.task_vocabulary)) != len(policy.task_vocabulary):\n            raise ValueError("a frozen unique task vocabulary is required")\n', ''),
]
TF = "shiftwork/executor/tokenfactory.py"
TC = "shiftwork/domain/task_contract.py"
M += [
 ("fixed_kind_swapped", TF, "'public_stock_lookup': 'stock'", "'public_stock_lookup': 'price'",
  T, "test_fixed_kind_tools_return_only_their_kind_for_the_entity"),
 ("fixed_kind_caller_kind", TF, "                    kind = FIXED_KIND_TOOLS[name]\n",
  "                    kind = body.get('record_kind', FIXED_KIND_TOOLS[name])\n",
  T, "test_fixed_kind_tool_ignores_a_caller_record_kind"),
 ("fixed_kind_no_entity_check", TF,
  "                    if not isinstance(entity, str):\n                        return self.reply(422, {'error': 'REQUEST_INVALID'})\n                    kind = FIXED_KIND_TOOLS[name]\n",
  "                    kind = FIXED_KIND_TOOLS[name]\n", T, "test_fixed_kind_tool_needs_an_entity_ref"),
 ("fixed_kind_bypasses_allowlist", TF, "                if name not in allowed:\n                    events.append({'kind': 'tool_rejected'",
  "                if name not in allowed and name not in FIXED_KIND_TOOLS:\n                    events.append({'kind': 'tool_rejected'",
  T, "test_v1_allowlist_does_not_gain_the_v2_tools"),
 ("loader_drops_task_vocabulary", TC, '            task_vocabulary=data.get("task_vocabulary", {}),\n', "",
  T, "test_mission_v2_freezes_task_vocabulary_and_five_tools"),
 ("loader_allows_empty_vocabulary", TC,
  '        if "task_vocabulary" in data and not data["task_vocabulary"]:\n            raise MissionSpecInvalid(f"mission {label} declares an empty task vocabulary")\n',
  "", T, "test_empty_task_vocabulary_is_refused"),
]
OR = "shiftwork/orchestrator.py"
RG = "shiftwork/packs/registry.py"
ST = "shiftwork/fixtures/artifacts/bookshop/task_plan_starter_service.py"
TB = "tests/orchestrator/test_mission_binding.py"
TS = "tests/executor/test_task_plan_starter.py"
M += [
 ("binding_swapped", OR,
  "    elif executor_name == TokenFactoryAdapter.name:\n        path = pack.mission_paths()[-1]\n    else:\n        path = pack.mission_path\n",
  "    elif executor_name == TokenFactoryAdapter.name:\n        path = pack.mission_path\n    else:\n        path = pack.mission_paths()[-1]\n",
  TB, "test_new_bellwether_shift_binds_v2_only_under_tokenfactory"),
 ("no_inheritance", OR, "    if previous is not None:\n        path = shift_mission_path(conn, previous, pack)\n    elif",
  "    if False:\n        path = shift_mission_path(conn, previous, pack)\n    elif",
  TB, "test_later_shift_inherits_its_predecessors_mission"),
 ("unpinned_binds", OR,
  "    if path not in pins or any(name not in pins for name in starter_paths):\n        raise LifecycleError(\"conflict\", \"the bound mission version awaits operator review\")\n    repo.insert_shift_mission_binding(conn, shift.id, path, pins[path], shift.opened_at)\n",
  "    repo.insert_shift_mission_binding(conn, shift.id, path, pins.get(path, \"unpinned\"), shift.opened_at)\n",
  TB, "test_unpinned_v2_is_refused_and_leaves_no_shift"),
 ("resolver_ignores_binding", OR, "    path = pack.mission_path if binding is None else binding[0]\n",
  "    path = pack.mission_path\n", TB, "test_open_shift_keeps_its_mission_when_the_executor_changes"),
 ("v2_baseline_replays_v1", OR,
  "            if shift_mission_path(conn, shift, pack) != pack.mission_path:\n                raise LifecycleError(\"conflict\", \"this starter has no reviewed capture to replay yet\")\n",
  "", TB, "test_v2_starter_baseline_never_replays_the_v1_capture"),
 ("adapter_drops_vocabulary", OR, "        task_vocabulary=tuple(mission.task_vocabulary),\n        token=", "        token=",
  TB, "test_service_adapter_takes_vocabulary_and_tools_from_the_frozen_mission"),
 ("later_version_specs_unchecked", OR, "                or later.request_specs != mission.request_specs):\n",
  "                or False):\n", TB, "test_pinned_later_mission_must_keep_the_graded_requests"),
 ("version_order_unchecked", RG, "        if self.mission_versions and self.mission_versions[0] != self.mission_path:\n",
  "        if False:\n", TB, "test_first_mission_version_must_be_the_pack_mission"),
 ("starter_rescues_alternative", ST, "    evidence_refs = []\n    for item in results:\n",
  "    if \"alternative\" not in done:\n        results.append(alternative_task(\"public_catalog_search\", snapshot, entity_ref, date, limit,\n                                        collection_confirmed))\n    evidence_refs = []\n    for item in results:\n",
  TS, "test_starter_omitting_a_required_task_fails_the_visible_check"),
 ("starter_ignores_named_tool", ST,
  "    if tool == \"public_record_lookup\" or tool == KIND_TOOLS[kind]:\n        return lookup(tool, entity_ref, kind)\n    return None\n",
  "    return lookup(KIND_TOOLS[kind], entity_ref, kind)\n",
  TS, "test_a_tool_that_cannot_do_the_task_leaves_it_out"),
 ("starter_reads_shop_directly", ST,
  "    try:\n        records = gateway_call(\"/tool\", body).get(\"records\", [])\n",
  "    try:\n        wanted = kind or {v: k for k, v in KIND_TOOLS.items()}[tool]\n        records = [r for r in json.loads(Path(\"shop.json\").read_bytes())[\"records\"]\n                   if r[\"entity_ref\"] == entity_ref and r[\"kind\"] == wanted]\n",
  TS, "test_starter_reads_records_only_through_the_driver"),
]
only = set(sys.argv[1:])
bad = 0
for entry in M:
    name, path, old, new = entry[:4]
    target, expected = (entry[4], entry[5]) if len(entry) == 6 else (T, None)
    if only and name not in only:
        continue
    p = Path(path); orig = p.read_bytes(); h = hashlib.sha256(orig).hexdigest()
    s = orig.decode(); assert s.count(old) == 1, name
    p.write_text(s.replace(old, new, 1))
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *target.split()],
                           capture_output=True, text=True)
        failed = [l.split("::")[-1].split(" ")[0].split("[")[0] for l in r.stdout.splitlines() if l.startswith("FAILED")]
    finally:
        p.write_bytes(orig)
    assert hashlib.sha256(p.read_bytes()).hexdigest() == h
    killed = r.returncode != 0 and (expected is None or expected in failed)
    print(f"{name}: rc={r.returncode} {'KILLED' if killed else 'SURVIVED'} failed={sorted(set(failed))}")
    bad += not killed
print("SURVIVORS", bad)
