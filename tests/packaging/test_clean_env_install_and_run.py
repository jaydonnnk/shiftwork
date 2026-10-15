"""Obligation 47: locked clean install and the full offline pivot, never a live PASS."""

import json
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
import venv
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _runs(python: Path) -> bool:
    try:
        probe = subprocess.run(
            [str(python), "-c", "print('ok')"], capture_output=True, text=True, timeout=120
        )
    except OSError:
        return False
    return probe.returncode == 0


def _fresh_interpreter(tmp_path: Path, lockfile: Path) -> tuple[Path, list[str], str]:
    stdlib_dir = tmp_path / "venv-pip"
    try:
        venv.create(stdlib_dir, with_pip=True, symlinks=os.name != "nt")
        stdlib_python = _venv_python(stdlib_dir)
        if _runs(stdlib_python):
            return (
                stdlib_python,
                [str(stdlib_python), "-m", "pip", "--isolated", "--disable-pip-version-check",
                 "install", "--quiet", "--no-deps", "-r", str(lockfile)],
                "stdlib venv + pip",
            )
    except OSError:
        pass

    uv = shutil.which("uv")
    assert uv is not None, "clean install BLOCKED: no usable fresh interpreter or installed uv"
    uv_dir = tmp_path / "venv-uv"
    create = subprocess.run(
        [uv, "venv", "--python", "3.12", str(uv_dir)],
        capture_output=True,
        text=True,
        env={**_scrubbed_env(), "UV_PYTHON_DOWNLOADS": "never"},
        timeout=300,
    )
    assert create.returncode == 0, f"uv venv failed:\n{create.stdout}\n{create.stderr}"
    uv_python = _venv_python(uv_dir)
    return (
        uv_python,
        [uv, "pip", "sync", "--python", str(uv_python), str(lockfile)],
        "uv venv + uv pip sync",
    )


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


_CREDENTIAL_MARKERS = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "SESSION")


def _scrubbed_env() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in _CREDENTIAL_MARKERS)
        and not key.startswith(("SHIFTWORK_", "PYTHON", "PYTEST_", "PIP_", "UV_"))
        and key != "VIRTUAL_ENV"
    }
    return {**env, "SHIFTWORK_EXECUTOR_ADAPTER": "recorded", "PYTHONDONTWRITEBYTECODE": "1"}


def _poll_board(port: int, timeout_s: float = 30.0) -> dict:
    url = f"http://127.0.0.1:{port}/api/engagements/bookshop/board"
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(0.25)
    raise AssertionError("uvicorn did not serve the board within the timeout")


def _offline_pivot(python: Path, source: Path, out: Path, env: dict) -> dict:
    demo = subprocess.run(
        [str(python), "-m", "demos.final_pivot", "--stage", "inheritance",
         "--preview-db", str(out / "bellwether.db")],
        cwd=source, env=env, capture_output=True, text=True, timeout=300,
    )
    (out / "bellwether.log").write_text(demo.stdout + demo.stderr, encoding="utf-8")
    assert demo.returncode == 0, f"pivot demo failed:\n{demo.stdout}\n{demo.stderr}"
    report = json.loads(demo.stdout)
    assert report["verdict"] == "PASS_OFFLINE_POLICY"
    assert report["evidence_class"] == "TRUSTED_LOCAL_DRAFT_POLICY_ONLY"
    assert report["inherited"]["draft_files_match_selected"] is True
    assert report["inherited"]["chain_status"] == "VALID"
    assert report["operational_run"]["evidence_mode"] == "TRUSTED_LOCAL"
    assert report["operational_run"]["artifact_version_id"] == report["inherited"]["selected_version_id"]
    later = report["later_condition_comparison"]
    assert later["trial_states"] == ["COMPLETE"] * 6
    assert later["outcome_status"] == "COMPLETE"
    assert later["candidate_b_version_id"] == report["inherited"]["retained_alternative_version_id"]
    assert later["operational_run_is_a_trial"] is False
    assert report["prior_bytes_identical"] is True

    gtm = subprocess.run(
        [str(python), "-m", "demos.gtm_operation", "--out", str(out / "gtm")],
        cwd=source, env=env, capture_output=True, text=True, timeout=300,
    )
    (out / "gtm.log").write_text(gtm.stdout + gtm.stderr, encoding="utf-8")
    assert gtm.returncode == 0, f"GTM journey failed:\n{gtm.stdout}\n{gtm.stderr}"
    gtm_report = json.loads(gtm.stdout)
    assert gtm_report["mode"] == "PRODUCTION_REVIEWED_TRUSTED_LOCAL"
    assert gtm_report["replay"] == "IDENTICAL"

    northline = subprocess.run(
        [str(python), "-m", "pytest",
         "tests/orchestrator/test_fde_deployment.py::test_fde_later_alternative_diagnostic_preserves_pilot_and_handover",
         "-q", "-p", "no:cacheprovider"],
        cwd=source, env=env, capture_output=True, text=True, timeout=300,
    )
    (out / "northline.log").write_text(northline.stdout + northline.stderr, encoding="utf-8")
    assert northline.returncode == 0, f"Northline journey failed:\n{northline.stdout}\n{northline.stderr}"
    assert "1 passed" in northline.stdout and "skipped" not in northline.stdout
    return {"bellwether": report, "gtm": gtm_report,
            "northline": "PASS_TRUSTED_LOCAL_TEST_CONTROL",
            "live_demo": "OFFLINE_SKIP: credentials excluded; a fresh live demo needs separate authorization"}


def test_clean_env_install_and_run(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()
    for directory in ("shiftwork", "demos", "tests", "docs"):
        shutil.copytree(REPO_ROOT / directory, source / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", ".env", ".env.*"))
    for filename in ("requirements.lock", "pyproject.toml", "README.md", "LICENSE", "HACKATHON_REQUIREMENTS.md"):
        shutil.copyfile(REPO_ROOT / filename, source / filename)
    assert not (source / ".venv").exists() and not (source / ".git").exists()
    python, install_command, mechanism = _fresh_interpreter(tmp_path, source / "requirements.lock")
    env = {**_scrubbed_env(), "UV_PYTHON_DOWNLOADS": "never",
           "SHIFTWORK_DB_PATH": str(tmp_path / "serve.db")}
    install = subprocess.run(install_command, capture_output=True, text=True, env=env, timeout=900)
    (tmp_path / "install.log").write_text(install.stdout + install.stderr, encoding="utf-8")
    assert install.returncode == 0, f"lock install failed:\n{install.stdout}\n{install.stderr}"
    check_command = ([str(python), "-m", "pip", "check"] if mechanism == "stdlib venv + pip"
                     else [install_command[0], "pip", "check", "--python", str(python)])
    check = subprocess.run(check_command, capture_output=True, text=True, env=env, timeout=60)
    assert check.returncode == 0, f"locked dependencies conflict:\n{check.stdout}\n{check.stderr}"
    report = _offline_pivot(python, source, tmp_path, env)

    port = _free_port()
    with (tmp_path / "server.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen(
            [str(python), "-m", "uvicorn", "shiftwork.app:create_app", "--factory",
             "--host", "127.0.0.1", "--port", str(port)],
            cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            board = _poll_board(port)
            assert board["engagement_slug"] == "bookshop"
            assert board["chain_status"] == "VALID"
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/boards") as response:
                boards = json.load(response)
            assert [(row["engagement_slug"], row["availability"]) for row in boards] == [
                ("bookshop", "AVAILABLE"), ("gtm", "AVAILABLE"), ("northline", "AVAILABLE")]
            for slug in ("bookshop", "northline", "gtm"):
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/engagements/{slug}/board") as response:
                    assert json.load(response)["engagement_slug"] == slug
            for asset in ("index.html", "app.js", "styles.css"):
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/{asset}") as response:
                    assert response.read() == (source / "shiftwork/client" / asset).read_bytes()
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)
    (tmp_path / "offline-pivot.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with capsys.disabled():
        print(f"\nclean-env mechanism: {mechanism}; three-board offline pivot PASS")
        print(report["live_demo"])
        print(f"package receipts: {tmp_path}")


@pytest.mark.parametrize("name,value", [
    ("SHIFTWORK_EXECUTOR_ADAPTER", "tokenfactory"),
    ("SHIFTWORK_DB_PATH", "/host/database.db"),
    ("SHIFTWORK_MODEL_ID", "host-model"),
    ("PYTHONPATH", "/host/packages"),
    ("VIRTUAL_ENV", "/host/environment"),
    ("PYTEST_ADDOPTS", "--collect-only"),
])
def test_offline_environment_ignores_host_execution_settings(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    env = _scrubbed_env()
    if name == "SHIFTWORK_EXECUTOR_ADAPTER":
        assert env[name] == "recorded"
    else:
        assert name not in env
