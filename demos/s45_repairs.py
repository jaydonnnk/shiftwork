"""Two frozen operator-authored prompt repairs, not learner or model work.

The changes from the approved starter are the user prompt and B's approved
reasoning-off request field. Both examples retain the model dependency.
These are proposals for the S45 demo, with no measured repair effectiveness.
"""

import argparse
import ast
import hashlib
import json
from pathlib import Path

from shiftwork import config, orchestrator
from shiftwork.domain import canonical
from shiftwork.domain.models import ContractParams
from shiftwork.domain import contract_catalog


PREFIX = "/no_think\nReturn only the JSON task plan. Do not write reasoning or explanation.\n"
DESCRIPTIONS = {"A": "Original descriptive prompt with reasoning-off wording in the user message",
                "B": "The same prompt with the approved enable_thinking=false gateway setting"}


def candidate_files(label: str) -> dict[str, str]:
    orchestrator.admit_pack("bookshop")
    source = (config.PACKAGE_DIR / "fixtures/artifacts/bookshop/task_plan_starter_service.py").read_text()
    function = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == "ask_for_plan")
    assignment = next(node for node in function.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "prompt" for t in node.targets))
    original = ast.get_source_segment(source, assignment.value)
    lines = source.splitlines(keepends=True)
    replacement = "    prompt = " + repr(PREFIX) + " + (\n        " + original + "\n    )\n"
    source = "".join(lines[:assignment.lineno - 1]) + replacement + "".join(lines[assignment.end_lineno:])
    if label == "B":
        request_call = 'gateway_call("/infer", {"request_ordinal": ordinal, "input_text": prompt})'
        assert source.count(request_call) == 1
        source = source.replace(request_call, 'gateway_call("/infer", {"request_ordinal": ordinal, "input_text": prompt, "enable_thinking": False})', 1)
    source = f"# Operator-authored S45 example {label}. Not learner work or learning evidence.\n" + source
    compile(source, f"s45-example-{label}", "exec")
    return {"service.py": source}


def candidate_prompt(label: str, text: str) -> str:
    namespace = {"__name__": "operator_authored_example"}
    exec(compile(candidate_files(label)["service.py"], f"s45-example-{label}", "exec"), namespace)
    prompts = []
    namespace["gateway_call"] = lambda path, payload: prompts.append(payload["input_text"]) or {}
    namespace["ask_for_plan"](text)
    return prompts[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    contract = ContractParams.model_validate(config.PIVOT_STARTER_CONTRACT_JSON)
    catalog = contract_catalog.load_catalog("bookshop", contract.catalog_version)
    metadata = {"authorship": "operator-authored examples, not learner work", "measured_effectiveness": "unknown", "candidates": []}
    for label in ("A", "B"):
        files = candidate_files(label)
        folder = args.out / label
        folder.mkdir()
        (folder / "service.py").write_text(files["service.py"])
        metadata["candidates"].append({"label": label, "description": DESCRIPTIONS[label],
            "service_sha256": hashlib.sha256(files["service.py"].encode()).hexdigest(),
            "artifact_content_hash": canonical.artifact_content_hash(files,
                canonical.contract_params_json(contract), catalog.content_hash)})
    (args.out / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
