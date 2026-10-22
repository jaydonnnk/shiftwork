import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import net from 'node:net';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { once } from 'node:events';
import { pythonPath, repoRoot } from './env.mjs';
import { runFaultControl } from './workplace_s32.mjs';

const out = process.argv[2];
assert.ok(/^\/tmp\/shiftwork-s(?:32|40)-/.test(out ?? ''), 'Pass a disposable /tmp/shiftwork-s32-* or /tmp/shiftwork-s40-* output directory');
await mkdir(out, { recursive: true });
const onlyIndex = process.argv.indexOf('--only');
const only = onlyIndex === -1 ? null : process.argv[onlyIndex + 1].split(',');

const rows = [
  { name: 'operation-omit-wall-label', mode: 'conflict', expected: 'The trace label text is missing' },
  { name: 'operation-omit-wall-trace', mode: 'conflict', expected: 'The confirmed linked consequence did not start a trace' },
  { name: 'operation-short-wall-trace', mode: 'conflict', expected: 'The evidence trace did not use 320ms' },
  { name: 'operation-omit-arrival-callback', mode: 'conflict', expected: 'The consequence callback did not fire exactly once' },
  { name: 'operation-conflict-reference', mode: 'conflict', expected: 'The confirmed linked consequence did not start a trace' },
  { name: 'operation-reset-reference', mode: 'conflict', expected: 'The reset and remount lost the confirmed arrival' },
  { name: 'operation-omit-mount-replay', mode: 'conflict', expected: 'The reset and remount lost the confirmed arrival' },
  { name: 'operation-omit-wall-settle', mode: 'motion', expected: 'Reduced motion did not cancel the evidence trace' },
];

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
  });
}
async function waitReachable(port, proc, log) {
  const deadline = Date.now() + 60000;
  while (Date.now() < deadline) {
    if (proc.exitCode !== null) throw new Error(`preview exited ${proc.exitCode}:\n${log()}`);
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/engagements/bookshop/board`);
      if (response.ok) return;
    } catch { /* starting */ }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error(`preview did not answer:\n${log()}`);
}
async function startPreview(port) {
  const source = `import tempfile
from pathlib import Path
import uvicorn
from demos.client import create_preview
with tempfile.TemporaryDirectory(prefix='shiftwork-s32-faults-') as directory:
    app = create_preview(str(Path(directory) / 'preview.db'))
    uvicorn.run(app, host='127.0.0.1', port=${port}, log_level='error', access_log=False)
`;
  const proc = spawn(pythonPath, ['-c', source], { cwd: repoRoot, stdio: ['ignore', 'pipe', 'pipe'] });
  let log = '';
  proc.stdout.on('data', data => { log += data; });
  proc.stderr.on('data', data => { log += data; });
  try {
    await waitReachable(port, proc, () => log);
  } catch (error) {
    proc.kill();
    throw error;
  }
  return { proc, log: () => log };
}
async function stopPreview(proc) {
  proc.kill('SIGINT');
  await Promise.race([once(proc, 'exit'), new Promise(resolve => setTimeout(resolve, 5000))]);
  if (proc.exitCode === null) proc.kill();
}

const sourceFiles = ['shiftwork/client/workplace-host.js', 'shiftwork/client/workplace-scene.js',
  'shiftwork/client/app.js', 'tests/client/workplace_browser.mjs', 'tests/client/workplace_s32.mjs'];
const digests = {};
for (const file of sourceFiles) {
  digests[file] = createHash('sha256').update(await readFile(path.join(repoRoot, file))).digest('hex');
}
const port = await freePort();
const preview = await startPreview(port);
const base = `http://127.0.0.1:${port}`;
const receipts = [];
try {
  for (const row of rows.filter(item => !only || only.includes(item.name))) {
    const phases = [];
    for (const phase of ['clean', 'fault', 'restored']) {
      const folder = path.join(out, `${row.name}-${phase}`);
      await mkdir(folder, { recursive: true });
      let error = null;
      try {
        await runFaultControl(base, folder, row.mode, phase === 'fault' ? row.name : '');
      } catch (caught) {
        error = caught;
      }
      await writeFile(path.join(folder, 'result.json'), JSON.stringify(error
        ? { passed: false, name: error.name, message: error.message }
        : { passed: true }, null, 2) + '\n');
      if (phase === 'fault') {
        assert.ok(error, `${row.name} survived`);
        assert.equal(error.name, 'AssertionError', `${row.name} failed outside an assertion: ${error.message}`);
        assert.ok(error.message.includes(row.expected), `${row.name} missed its intended assertion: ${error.message}`);
      } else {
        assert.equal(error, null, `${row.name} ${phase} failed: ${error?.message}`);
      }
      phases.push({ phase, passed: !error });
    }
    receipts.push({ name: row.name, mode: row.mode, assertion: row.expected, phases });
    await writeFile(path.join(out, 'browser-faults.json'), JSON.stringify(receipts, null, 2) + '\n');
  }
} finally {
  await stopPreview(preview.proc);
}
for (const file of sourceFiles) {
  assert.equal(createHash('sha256').update(await readFile(path.join(repoRoot, file))).digest('hex'), digests[file],
    `${file} changed during the browser fault proof`);
}
await writeFile(path.join(out, 'sources.json'), JSON.stringify(digests, null, 2) + '\n');
console.log(JSON.stringify({ browserControls: receipts.length, result: 'PASS', production: 'unchanged' }));
