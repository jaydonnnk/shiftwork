"""Run authorized offline evidence with scrubbed credentials and fresh receipts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
COPY = Path("C:/sw24-y6rzzs69")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("full", "anchors24", "anchors23", "faults24", "faults23", "demo", "material", "queue"))
    parser.add_argument("--label")
    args = parser.parse_args()
    mode = args.mode
    label = args.label or mode
    cwd = COPY if mode.startswith(("anchors", "faults")) else ROOT
    if mode == "full":
        argv = [sys.executable, "-m", "pytest", "tests", "--ignore=tests/packaging", "-q", "--tb=short", f"--junitxml={OUT / 'full.xml'}"]
    elif mode.startswith(("anchors", "faults")):
        module = "tests.packs.gtm_operation_mutation_proofs" if mode.endswith("24") else "tests.packs.gtm_mutation_proofs"
        argv = [sys.executable, "-m", module, "--out", str(OUT / ("faults" + mode[-2:]))]
        if mode.startswith("anchors"):
            argv.append("--check-anchors")
    elif mode == "queue":
        argv = [sys.executable, "-m", "pytest", str(OUT / "review_queue_probe.py"), "-q", "--tb=short", f"--junitxml={OUT / (label + '.xml')}"]
    elif mode == "demo":
        argv = [sys.executable, "-m", "demos.gtm_operation", "--out", str(OUT / "demo")]
    else:
        argv = [sys.executable, "-m", "demos.gtm_reviewed"]
    env = {key: value for key, value in os.environ.items()
           if not any(word in key.upper() for word in ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "SESSION"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if mode == "queue":
        env["SHIFTWORK_QUEUE_OUT"] = str(OUT / (label + "-demo"))
    log = OUT / (label + ".log")
    started = time.monotonic()
    with log.open("xb") as stream:
        result = subprocess.run(argv, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=7200)
    receipt = {"mode": mode, "argv": argv, "cwd": str(cwd), "returncode": result.returncode,
               "elapsed_seconds": round(time.monotonic() - started, 2),
               "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()}
    xml = OUT / "full.xml"
    if mode == "full" and xml.is_file():
        suites = list(ET.parse(xml).getroot().iter("testsuite"))
        receipt["junit"] = {key: sum(int(s.get(key, "0")) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
        receipt["xml_sha256"] = hashlib.sha256(xml.read_bytes()).hexdigest()
    (OUT / (label + "-receipt.json")).write_bytes((json.dumps(receipt, indent=2) + "\n").encode())
    print(json.dumps(receipt))
    print(log.read_text(encoding="utf-8", errors="replace")[-2500:])
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
