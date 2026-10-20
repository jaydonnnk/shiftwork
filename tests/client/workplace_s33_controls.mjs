import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import net from 'node:net';
import path from 'node:path';
import { once } from 'node:events';
import { pythonPath, repoRoot } from './env.mjs';
import { runJourney } from './workplace_s32.mjs';
import { runLater } from './workplace_s33.mjs';

const out = process.argv[2];
assert.ok(/^\/tmp\/shiftwork-s33-/.test(out ?? ''), 'Pass a disposable /tmp/shiftwork-s33-* output directory');
await mkdir(out, { recursive: true });
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
  const deadline = Date.now() + 180000;
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
async function startPreview(port, inherit) {
  const source = `import tempfile
from pathlib import Path
import uvicorn
from demos.client import create_preview
with tempfile.TemporaryDirectory(prefix='shiftwork-s33-controls-') as directory:
    app = create_preview(str(Path(directory) / 'preview.db')${inherit ? ', inherit=True' : ''})
    uvicorn.run(app, host='127.0.0.1', port=${port}, log_level='error', access_log=False)
`;
  const proc = spawn(pythonPath, ['-c', source], { cwd: repoRoot, stdio: ['ignore', 'pipe', 'pipe'] });
  let log = '';
  proc.stdout.on('data', data => { log += data; });
  proc.stderr.on('data', data => { log += data; });
  try { await waitReachable(port, proc, () => log); }
  catch (error) { proc.kill(); throw error; }
  return { proc, log: () => log };
}
async function stopPreview(proc) {
  proc.kill('SIGINT');
  await Promise.race([once(proc, 'exit'), new Promise(resolve => setTimeout(resolve, 5000))]);
  if (proc.exitCode === null) proc.kill();
}
const sourceFiles = ['shiftwork/client/app.js', 'shiftwork/client/index.html', 'shiftwork/client/styles.css',
  'shiftwork/client/workplace-view.js', 'shiftwork/client/workplace-scene.js', 'shiftwork/client/workplace-rooms.js',
  'tests/client/workplace_s32.mjs', 'tests/client/workplace_s33.mjs'];
const digests = {};
for (const file of sourceFiles) digests[file] = createHash('sha256').update(await readFile(path.join(repoRoot, file))).digest('hex');
const receipts = {};
const normalPort = await freePort();
let preview = await startPreview(normalPort, false);
try {
  receipts.journey = await runJourney(`http://127.0.0.1:${normalPort}`, path.join(out, 'journey'));
} finally { await stopPreview(preview.proc); }
const inheritPort = await freePort();
preview = await startPreview(inheritPort, true);
try {
  receipts.later = await runLater(`http://127.0.0.1:${inheritPort}`, path.join(out, 'later'));
} finally { await stopPreview(preview.proc); }
for (const file of sourceFiles) {
  assert.equal(createHash('sha256').update(await readFile(path.join(repoRoot, file))).digest('hex'), digests[file],
    `${file} changed during the S33 controls`);
}
await writeFile(path.join(out, 'summary.json'), JSON.stringify({ receipts, sources: digests, result: 'PASS' }, null, 2) + '\n');
console.log(JSON.stringify({ result: 'PASS', journey: receipts.journey.run, later: receipts.later.later, history: receipts.later.historyRun, newShift: receipts.later.newShift }));
