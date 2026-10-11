"""Run the reviewed offline S24 API journey and retain its real database receipt.

Uses the installed test environment; performs no dependency installation or live
service call. The outage is a disposable synthetic operator observation. Raw
results and failures are retained; an existing output directory is refused.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    proof = out / "journey.json"
    env = {key: value for key, value in os.environ.items()
           if not any(word in key.upper() for word in ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "SESSION"))}
    env["SHIFTWORK_S24_PROOF_OUT"] = str(proof)
    with (out / "journey.log").open("xb") as log:
        result = subprocess.run([sys.executable, "-m", "pytest",
            "tests/orchestrator/test_gtm_pipeline.py::test_gtm_exact_selection_operation_restart_inheritance_and_later_condition",
            "-q", "--tb=short", f"--junitxml={out / 'journey.xml'}"],
            cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    if result.returncode:
        print((out / "journey.log").read_text(encoding="utf-8", errors="replace"))
        return result.returncode
    data = json.loads(proof.read_bytes())
    print(json.dumps({"status": "PASS", "mode": data["mode"],
        "selected_version_id": data["selected_version_id"], "retained_version_id": data["retained_version_id"],
        "operation_run_id": data["operation"]["id"], "inherited_reprocessing_run_id": data["inherited_reprocessing"]["id"],
        "later_comparison_id": data["later_comparison"]["id"], "replay": data["replay"]["status"],
        "proof": str(proof), "database": str(proof.with_suffix('.db'))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
