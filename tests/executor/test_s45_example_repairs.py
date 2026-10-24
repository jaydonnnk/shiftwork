"""The two proposed examples are operator-authored and still depend on a plan."""

import ast
import json
from pathlib import Path


def normalize_prompt(source):
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "ask_for_plan")
    assignment = next(node for node in function.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "prompt" for t in node.targets))
    assignment.value = ast.Constant("only the user prompt may differ")
    for node in ast.walk(function):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "gateway_call"
                and len(node.args) == 2 and isinstance(node.args[0], ast.Constant) and node.args[0].value == "/infer"):
            payload = node.args[1]
            pairs = [(key, value) for key, value in zip(payload.keys, payload.values)
                     if not (isinstance(key, ast.Constant) and key.value == "enable_thinking"
                             and isinstance(value, ast.Constant) and value.value is False)]
            payload.keys = [key for key, _ in pairs]
            payload.values = [value for _, value in pairs]
    return ast.dump(tree, include_attributes=False)


def test_example_repairs_change_only_prompt_or_reasoning_setting_and_keep_no_rescue_code():
    from demos.s45_repairs import candidate_files, candidate_prompt
    from shiftwork import config
    original = (config.PACKAGE_DIR / "fixtures/artifacts/bookshop/task_plan_starter_service.py").read_text()
    for label in ("A", "B"):
        source = candidate_files(label)["service.py"]
        assert "Operator-authored S45 example" in source
        assert normalize_prompt(source) == normalize_prompt(original), (
            "example repairs must preserve the model dependency and may not add hidden rescue code")
        prompt = candidate_prompt(label, "Public test: price and stock of a named paperback.")
        assert prompt.startswith("/no_think\n")
        assert "Public test: price and stock of a named paperback." in prompt
        assert len(prompt.encode()) <= 8192
    assert candidate_files("A") != candidate_files("B")


def test_example_b_changes_only_the_reasoning_setting_from_example_a():
    from demos.s45_repairs import candidate_files
    captured = {}
    for label in ("A", "B"):
        namespace = {"__name__": "operator_authored_example"}
        exec(compile(candidate_files(label)["service.py"], label, "exec"), namespace)
        payloads = []
        namespace["gateway_call"] = lambda path, payload: payloads.append(payload) or {}
        namespace["ask_for_plan"]("public request")
        captured[label] = payloads
    assert len(captured["A"]) == 1 and set(captured["A"][0]) == {"request_ordinal", "input_text"}, "A must preserve the probed default provider settings"
    assert captured["B"] == [{**captured["A"][0], "enable_thinking": False}], "B must use the same frozen wording and only request reasoning off"


def test_example_a_matches_the_separately_frozen_probe_prompt():
    from demos.s45_repairs import candidate_prompt
    from shiftwork import config
    from shiftwork.domain import task_contract
    mission = task_contract.load_mission(config.PACKAGE_DIR / "fixtures/mission/bookshop_pivot_v2.json")
    source = Path("/tmp/shiftwork-s45-probe-20261024/live-receipt.json")
    if source.exists():
        expected = json.loads(source.read_bytes())["prompt"]
    else:
        import runpy
        starter = runpy.run_path(str(config.PACKAGE_DIR / "fixtures/artifacts/bookshop/task_plan_starter_service.py"))
        prompts = []
        starter["ask_for_plan"].__globals__["gateway_call"] = lambda path, payload: prompts.append(payload["input_text"]) or {}
        starter["ask_for_plan"](mission.request_specs[0].text)
        expected = "/no_think\nReturn only the JSON task plan. Do not write reasoning or explanation.\n" + prompts[0]
    assert candidate_prompt("A", mission.request_specs[0].text) == expected, "the probe wording must not be tuned after its retained stop"
