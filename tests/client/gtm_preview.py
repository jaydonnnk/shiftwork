"""Disposable trusted-local GTM browser preview. No production pins are changed."""
import argparse
import json
from pathlib import Path
import sqlite3

import uvicorn
from shiftwork import config
from shiftwork.app import create_app
from shiftwork.assist.gateway import AssistReply


def candidate_files():
    """The two reviewed candidate workflows, byte-exact from the sealed pack.

    The browser must save and freeze these bytes through the normal UI, so the
    frozen versions match their literal production pins with no test-only patch.
    """
    return {
        label: {'service.py': (config.PACKAGE_DIR
                               / f'fixtures/artifacts/gtm/gtm_compare_repair_{label.lower()}_workflow.py'
                               ).read_text(encoding='utf-8')}
        for label in ('A', 'B')
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    candidates = candidate_files()
    if not (out / 'candidate-files.json').exists():
        (out / 'candidate-files.json').write_text(json.dumps(candidates), encoding='utf-8')

    class RecordedBrowserHint:
        def generate(self, *, model_id, role, prompt):
            return AssistReply('Recorded test hint: compare the recorded owner and pipeline write with the frozen route before trusting a confidence score.',
                               reported_model_id='recorded-browser-control', input_tokens=0,
                               output_tokens=0, elapsed_ms=0)

    app = create_app(args.database, executor='local_process', assist_gateway=RecordedBrowserHint())
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
