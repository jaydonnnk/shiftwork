"""Retain exclusive raw pytest logs, JUnit and result bindings for this run."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent


def main():
    name, *selection = sys.argv[1:]
    assert name.replace("-", "").isalnum()
    log, xml, receipt = (OUT / (name + suffix) for suffix in (".log", ".xml", "-result.json"))
    assert not any(path.exists() for path in (log, xml, receipt))
    command = [sys.executable, "-B", "-m", "pytest", *selection, "-q", "--tb=short",
               "-p", "no:cacheprovider", "--junitxml=" + str(xml)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("SHIFTWORK_S23_PROOF_OUT", None)
    if name in {"production-proof", "production-retained"}:
        env["SHIFTWORK_S23_PROOF_OUT"] = str(OUT / (name + ".json"))
    with log.open("xb") as stream:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in iter(process.stdout.readline, b""):
            stream.write(line)
            stream.flush()
            print(line.decode(errors="replace").rstrip(), flush=True)
        code = process.wait()
    suites = list(ET.parse(xml).getroot().iter("testsuite"))
    summary = {key: sum(int(s.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    result = {"exit_code": code, "command": command, **summary, "log_sha256": sha(log), "xml_sha256": sha(xml)}
    with receipt.open("xb") as stream:
        stream.write((json.dumps(result, indent=2) + "\n").encode())
    print(json.dumps(result), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
