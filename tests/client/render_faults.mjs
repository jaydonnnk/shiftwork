import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { once } from 'node:events';

// Failing-capability proof for the rendered-evidence harness. Every row serves a
// mutated in-memory copy of the production app.js to the browser and requires
// tests/client/browser.mjs to fail at the named assertion; the baseline row first
// proves the same harness passes the unmutated client, so a red fault row cannot
// be vacuous. The repository files are never modified. Run from the repo root:
//   node tests/client/render_faults.mjs [--port 8137]
// The runner starts its own isolated preview (pinned trusted fixtures) and stops
// it afterwards. It installs nothing and consumes no attempts.

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const portIndex = process.argv.indexOf('--port');
const port = portIndex === -1 ? 8137 : Number(process.argv[portIndex + 1]);
const python = path.join(root, '.venv', 'Scripts', 'python.exe');

const preview = spawn(python, ['-m', 'demos.client', '--port', String(port)], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
let previewLog = '';
const started = new Promise((resolve, reject) => {
  const timeout = setTimeout(() => reject(new Error(`Preview did not start in 30s:\n${previewLog}`)), 30000);
  preview.stdout.on('data', data => {
    previewLog += data;
    if (previewLog.includes(`Preview: http://127.0.0.1:${port}`)) { clearTimeout(timeout); resolve(); }
  });
  preview.stderr.on('data', data => { previewLog += data; });
  preview.once('exit', code => { clearTimeout(timeout); reject(new Error(`Preview exited ${code}:\n${previewLog}`)); });
});

function harness(fault) {
  return new Promise(resolve => {
    const child = spawn(process.execPath, ['tests/client/browser.mjs', `http://127.0.0.1:${port}`], {
      cwd: root,
      env: { ...process.env, ...(fault ? { SHIFTWORK_FAULT: fault } : {}) },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let out = '', err = '';
    child.stdout.on('data', data => { out += data; });
    child.stderr.on('data', data => { err += data; });
    child.once('exit', code => resolve({ code, out, err }));
  });
}

const FAULTS = ['answer', 'record', 'verdict', 'event', 'stationFocus', 'incidentFocus'];
const results = [];
let failures = 0;
try {
  await started;
  console.log(`Preview on ${port} ready; running baseline then ${FAULTS.length} fault rows.`);
  const baseline = await harness(null);
  if (baseline.code === 0) {
    results.push('baseline (no fault)                PASS   harness green against the unmutated client');
  } else {
    failures += 1;
    results.push(`baseline (no fault)                FAIL   exit ${baseline.code}\n${(baseline.out + baseline.err).slice(-1500)}`);
  }
  for (const fault of FAULTS) {
    const run = await harness(fault);
    const caughtLine = run.out.match(new RegExp(`FAULT_CAUGHT ${fault}:[^\\n]*`))?.[0];
    if (run.code === 0 && caughtLine) {
      results.push(`fault: ${fault.padEnd(28)} CAUGHT ${caughtLine}`);
    } else {
      failures += 1;
      results.push(`fault: ${fault.padEnd(28)} ${run.code === 0 ? 'SURVIVED (harness exited green)' : `WRONG FAILURE (exit ${run.code})`}\n${(run.out + run.err).slice(-2000)}`);
    }
  }
} finally {
  preview.kill();
  await Promise.race([once(preview, 'exit'), new Promise(resolve => setTimeout(resolve, 3000))]).catch(() => {});
  if (preview.exitCode === null) preview.kill();
  console.log(results.join('\n'));
  console.log(`render-fault rows: ${results.length - failures} of ${results.length} as expected`);
}
process.exitCode = failures === 0 && results.length === FAULTS.length + 1 ? 0 : 1;
