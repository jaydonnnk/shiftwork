"""Disposable trusted-local browser preview. No production pins are changed."""
import argparse
import json
from pathlib import Path
import re
import sqlite3

import pytest
import uvicorn
from shiftwork.app import create_app
from shiftwork.assist.gateway import AssistReply
from shiftwork.store import db, repo
from tests.orchestrator.test_fde_deployment import FDE_TEST_SERVICE, _fde_pin


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # Test input only. The browser must author/save/freeze these bytes through
    # the normal UI. No production learner starter or reference repair changes.
    candidates = {}
    for label in ('A', 'B'):
        candidates[label] = {
            'service.py': FDE_TEST_SERVICE.replace('__LABEL__', repr(label)),
            'discovery.md': '# Discovery\nCheck parts and schedule before a simulated booking.\n',
            'permissions.json': json.dumps({'reads': ['parts_availability', 'mechanic_schedule'], 'writes': ['repair_slots']}),
            'acceptance_tests.py': '# Test fixture: assert retry retains exactly one simulated booking.\n',
            'runbook.md': '# Runbook ' + label + '\nEscalate uninspected faults to a human mechanic.\n',
        }
    if not (out / 'candidate-files.json').exists():
        (out / 'candidate-files.json').write_text(json.dumps(candidates), encoding='utf-8')
    with pytest.MonkeyPatch.context() as patch:
        class RecordedBrowserHint:
            def generate(self, *, model_id, role, prompt):
                return AssistReply('Recorded test hint: compare the required task with the captured response and verify resource receipts.', reported_model_id='recorded-browser-control', input_tokens=0, output_tokens=0, elapsed_ms=0)
        app = create_app(args.database, executor='local_process', assist_gateway=RecordedBrowserHint())

        def pin_latest(shift_id):
            conn = db.connect(args.database)
            try:
                version = repo.get_latest_version(conn, shift_id)
                if not version:
                    return
                label = next((label for label in ('A', 'B') if version.files.get('service.py') == candidates[label]['service.py']), None)
                if label:
                    _fde_pin({'id': version.id, 'content_hash': version.content_hash, 'files': version.files}, patch, label)
            finally:
                conn.close()

        @app.middleware('http')
        async def fixture_admission(request, call_next):
            response = await call_next(request)
            match = re.fullmatch(r'/api/shifts/([^/]+)/artifact/versions', request.url.path)
            if request.method == 'POST' and match and response.status_code == 201:
                pin_latest(match[1])
            return response

        static_mount = app.router.routes.pop()
        assert static_mount.name == 'client', 'test routes must precede the static catch-all'

        @app.post('/__test__/checkpoint/{name}')
        def checkpoint(name: str):
            assert name in {'comparison', 'closed'}
            target = out / (name + '.db')
            assert not target.exists(), 'never overwrite browser checkpoints'
            with sqlite3.connect(args.database) as source, sqlite3.connect(target) as destination:
                source.backup(destination)
            return {'checkpoint': name}

        app.router.routes.append(static_mount)

        print(f'TRUSTED_LOCAL preview http://127.0.0.1:{args.port}; DB {args.database}', flush=True)
        uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='error', access_log=False)


if __name__ == '__main__':
    main()
