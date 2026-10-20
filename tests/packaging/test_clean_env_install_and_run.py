"""Obligation 47: locked clean install and the full offline pivot, never a live PASS."""

import json
import os
import signal
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
import venv
import zipfile
import hashlib
from pathlib import Path

import pytest
from test_client_asset_closure import verify_records, verify_http_delivery

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


def _run_owned_browser(args, *, cwd, env, timeout):
    process = subprocess.Popen(args, cwd=cwd, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=os.name != 'nt')
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=10)
        else:
            os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate(timeout=10)
        return subprocess.CompletedProcess(args, 124, stdout, stderr + '\nBrowser process group timed out and was terminated.\n')


def verify_three_browser_journeys(source: Path, python: Path, out: Path):
    """Exercise extracted source with an explicit interpreter; never install here."""
    node = shutil.which('node')
    assert node, 'Browser proof unavailable: node is not installed'
    out.mkdir(parents=True, exist_ok=True)
    results = {}
    env = {**_scrubbed_env(), 'SHIFTWORK_PYTHON': str(python),
           'SHIFTWORK_BLOCK_EXTERNAL': '1', 'PYTHONPATH': str(source)}
    for slug in ('bookshop', 'gtm', 'northline'):
        port = _free_port()
        inputs = out / (slug + '-input')
        preview_args = ([str(python), '-m', 'demos.client', '--port', str(port)] if slug == 'bookshop'
                        else [str(python), '-m', 'tests.client.' + slug + '_preview',
                              '--port', str(port), '--database', str(out / (slug + '.db')),
                              '--out', str(inputs)])
        if slug == 'northline':
            preview_args.append('--retained-diagnostic-control')
        with (out / (slug + '-preview.log')).open('w') as log:
            preview = subprocess.Popen(preview_args, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                _poll_board(port)
                browser_file = 'browser.mjs' if slug == 'bookshop' else slug + '_browser.mjs'
                url = f'http://127.0.0.1:{port}' + ('' if slug == 'bookshop' else f'/?board={slug}')
                args = [node, 'tests/client/' + browser_file, url]
                if slug == 'bookshop':
                    args += ['--selection-demo', '--journey-demo']
                run_env = {**env, 'SHIFTWORK_ARTIFACT_DIR': str(out / (slug + '-browser')),
                           'SHIFTWORK_TEST_INPUTS': str(inputs / 'candidate-files.json')}
                if slug == 'northline':
                    run_env['SHIFTWORK_LATER_ALTERNATIVE'] = '1'
                browser = _run_owned_browser(args, cwd=source, env=run_env, timeout=480)
                (out / (slug + '-browser.log')).write_text(browser.stdout + browser.stderr)
                assert browser.returncode == 0, f'{slug} extracted journey failed; see {out / (slug + "-browser.log")}'
                if slug != 'bookshop':
                    preview.terminate()
                    preview.wait(timeout=10)
                    room_db = out / (slug + '-room.db')
                    shutil.copyfile(inputs / 'comparison.db', room_db)
                    room_args = list(preview_args)
                    room_args[room_args.index('--database') + 1] = str(room_db)
                    preview = subprocess.Popen(room_args, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT)
                    _poll_board(port)
                room_code = ('import {runBrowser} from "./tests/client/workplace_browser.mjs";'
                             f'console.log(await runBrowser("http://127.0.0.1:{port}",{json.dumps(str(out / (slug + "-room")))},"",false,{json.dumps(slug)}));')
                room = _run_owned_browser([node, '--input-type=module', '-e', room_code], cwd=source, env=env, timeout=180)
                (out / (slug + '-room.log')).write_text(room.stdout + room.stderr)
                assert room.returncode == 0, f'{slug} extracted actual room failed'
                if slug == 'northline':
                    fallback_code = room_code.replace(json.dumps(str(out / (slug + '-room'))), json.dumps(str(out / 'northline-fallback'))).replace(',"",false,', ',"constructor",false,')
                    fallback = _run_owned_browser([node, '--input-type=module', '-e', fallback_code], cwd=source, env=env, timeout=180)
                    (out / 'northline-fallback.log').write_text(fallback.stdout + fallback.stderr)
                    assert fallback.returncode == 0, 'Extracted Northline graphics-failure workbench failed'
                results[slug] = {'journey': 'PASS', 'actual_room': 'PASS', 'external_asset_block': 'self-tested'}
                (out / 'complete-browser-results.json').write_text(json.dumps(results, indent=2) + '\n')
            finally:
                preview.terminate()
                try:
                    preview.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    preview.kill()
                    preview.wait(timeout=10)
    return results


def test_clean_env_install_and_run(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()
    for directory in ("shiftwork", "demos", "tests", "docs"):
        shutil.copytree(REPO_ROOT / directory, source / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", ".env", ".env.*"))
    for filename in ("requirements.lock", "pyproject.toml", "README.md", "LICENSE", "HACKATHON_REQUIREMENTS.md"):
        shutil.copyfile(REPO_ROOT / filename, source / filename)
    assert not (source / ".venv").exists() and not (source / ".git").exists()
    archive = tmp_path / 'shiftwork-source.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for file in sorted(source.rglob('*')):
            if file.is_file():
                bundle.write(file, file.relative_to(source))
    assert archive.stat().st_size < 35_000_000, 'Source archive exceeds submission limit'
    (tmp_path / 'archive.json').write_text(json.dumps({'bytes': archive.stat().st_size,
        'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}) + '\n')
    extracted = tmp_path / 'extracted'
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(extracted)
    source = extracted
    graph = verify_records(source / 'shiftwork/client')
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
            def fetch_asset(asset):
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/{asset}") as response:
                    return response.read(), response.headers.get_content_type()
            verify_http_delivery(source / 'shiftwork/client', graph | {'vendor/three-r180/LICENSE',
                'vendor/three-r180/manifest.json', 'workplace-assets.json', 'THIRD_PARTY_NOTICES.md'}, fetch_asset)
            node = shutil.which('node')
            assert node, 'Extracted browser proof unavailable: Node is missing'
            browser_out = tmp_path / 'extracted-browser'
            browser = subprocess.run([node, 'tests/client/workplace_browser.mjs',
                f'http://127.0.0.1:{port}', str(browser_out), '--empty'],
                cwd=source, env={**env, 'SHIFTWORK_PYTHON': str(python)},
                capture_output=True, text=True, timeout=180)
            (tmp_path / 'browser.log').write_text(browser.stdout + browser.stderr)
            assert browser.returncode == 0, f'Extracted browser proof failed:\n{browser.stdout}\n{browser.stderr}'
            preview_port = _free_port()
            with (tmp_path / 'recorded-preview.log').open('w') as preview_log:
                preview = subprocess.Popen([str(python), '-m', 'demos.client', '--port', str(preview_port)],
                    cwd=source, env={**env, 'TMPDIR': str(tmp_path)}, stdout=preview_log, stderr=subprocess.STDOUT)
                try:
                    _poll_board(preview_port)
                    fallback = subprocess.run([node, 'tests/client/workplace_browser.mjs',
                        f'http://127.0.0.1:{preview_port}', str(tmp_path / 'extracted-fallback'), 'constructor'],
                        cwd=source, env={**env, 'SHIFTWORK_PYTHON': str(python)},
                        capture_output=True, text=True, timeout=180)
                    (tmp_path / 'fallback-browser.log').write_text(fallback.stdout + fallback.stderr)
                    assert fallback.returncode == 0, f'Extracted fallback workbench failed:\n{fallback.stdout}\n{fallback.stderr}'
                finally:
                    preview.terminate()
                    try:
                        preview.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        preview.kill()
                        preview.wait(timeout=10)
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)
    report['complete_browser_delivery'] = verify_three_browser_journeys(source, python, tmp_path / 'complete-browser-delivery')
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
