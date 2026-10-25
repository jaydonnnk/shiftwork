"""S47-owned offline browser fixtures. No model or Sandbox call."""
import argparse
from pathlib import Path
import re

import uvicorn

from demos.client import create_preview
from shiftwork import config
from shiftwork.app import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--scenario', choices=['starter', 'comparison', 'inherit'], default='starter')
    args = parser.parse_args()
    database = Path(args.database).resolve()
    assert re.match(r'^/(?:private/)?tmp/shiftwork-s47-[^/]+(?:/|$)', str(database)), 'Use an S47-owned disposable store'
    assert not database.exists(), 'Never overwrite an existing store'
    assert config.EXECUTOR_ADAPTER == 'recorded', 'Offline preview requires recorded mode'
    if args.scenario == 'comparison':
        from tests.client.s45_preview import seed
        seed(str(database))
        app = create_app(str(database), executor='recorded')
    else:
        app = create_preview(str(database), inherit=args.scenario == 'inherit', recorded_assist=True)
    app.state.hosted_runtime = {'hosted': False, 'configured_executor': 'recorded',
        'notice': 'S47 OFFLINE TEST. Authored fixtures and recorded inspections; no model call, live Sandbox run or learner evidence.'}
    print(f'S47 preview: http://127.0.0.1:{args.port}/?board=bookshop&guide=1', flush=True)
    uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='error', access_log=False)


if __name__ == '__main__':
    main()
