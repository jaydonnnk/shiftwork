"""Test 51: a fresh environment installs requirements.lock, runs the demo and serves.

Lands at Slice 1 and re-runs at Slice 16 (04-slices.md). The preferred path is a
stdlib venv plus pip, exactly as specified, and that is the path selected on this
machine (re-verified 2026-09-17: `clean-env mechanism: stdlib venv + pip`). A
one-off `WinError 4551` Application Control block was seen once but is not
reproducible on re-test; for machines where freshly created stdlib venv binaries
genuinely cannot execute, the test probes the interpreter and falls back to a
uv-managed venv plus `uv pip sync` against the same pins file, with identical
assertions either way. Requires network access for the installer.
"""

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
LOCKFILE = REPO_ROOT / "requirements.lock"


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


def _fresh_interpreter(tmp_path: Path) -> tuple[Path, list[str], str]:
    stdlib_dir = tmp_path / "venv-pip"
    try:
        venv.create(stdlib_dir, with_pip=True)
        stdlib_python = _venv_python(stdlib_dir)
        if _runs(stdlib_python):
            return (
                stdlib_python,
                [str(stdlib_python), "-m", "pip", "install", "--quiet", "-r", str(LOCKFILE)],
                "stdlib venv + pip",
            )
    except OSError:
        pass

    uv = shutil.which("uv")
    if uv is None:
        pytest.skip(
            "no usable fresh-environment mechanism: stdlib venv execution is blocked "
            "by OS policy and uv is not installed"
        )
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
        [uv, "pip", "sync", "--python", str(uv_python), str(LOCKFILE)],
        "uv venv + uv pip sync",
    )


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


_CREDENTIAL_MARKERS = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "SESSION")


def _scrubbed_env() -> dict[str, str]:
    """Host env with credential-bearing variables removed.

    Program-design test 51 requires the clean-env run to complete without
    credentials and to fail if it needs a key. Inheriting the full host env would
    let a real NEBIUS_API_KEY (or similar) silently satisfy a run that secretly
    needs one, so strip anything credential-shaped before launching children.
    """
    return {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in _CREDENTIAL_MARKERS)
    }


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


def test_clean_env_install_and_run(tmp_path):
    python, install_command, mechanism = _fresh_interpreter(tmp_path)
    print(f"clean-env mechanism: {mechanism}")
    env = {
        **_scrubbed_env(),
        "UV_PYTHON_DOWNLOADS": "never",
        "SHIFTWORK_DB_PATH": str(tmp_path / "clean-env.db"),
    }

    install = subprocess.run(
        install_command, capture_output=True, text=True, env=env, timeout=900
    )
    assert install.returncode == 0, f"lock install failed:\n{install.stdout}\n{install.stderr}"

    demo = subprocess.run(
        [str(python), "-m", "demos.lifecycle"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert demo.returncode == 0, f"demo failed:\n{demo.stdout}\n{demo.stderr}"
    assert "FINALIZED" in demo.stdout

    port = _free_port()
    server = subprocess.Popen(
        [
            str(python),
            "-m",
            "uvicorn",
            "shiftwork.app:create_app",
            "--factory",
            "--port",
            str(port),
        ],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        board = _poll_board(port)
        assert board["engagement_slug"] == "bookshop"
        assert board["chain_status"] == "VALID"
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
