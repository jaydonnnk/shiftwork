import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { once } from 'node:events';
import { mkdir, writeFile, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { pythonPath } from './env.mjs';

// Failing-capability proof for the rendered-evidence harness. Every row serves a
// mutated in-memory copy of the production app.js to the browser and requires
// tests/client/browser.mjs to fail at the named assertion; the baseline row first
// proves the same harness passes the unmutated client, so a red fault row cannot
// be vacuous. The repository files are never modified. Run from the repo root:
//   node tests/client/render_faults.mjs [--port 8137]
// Each row starts its own isolated preview: a public diagnostic becomes the
// board's latest run, and the customer-evidence rows need the fresh operation
// run the preview seeds. Every row uses a disposable local database; the
// continuous journey baseline consumes its own operation reservation.

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const portIndex = process.argv.indexOf('--port');
const port = portIndex === -1 ? 8137 : Number(process.argv[portIndex + 1]);
const python = pythonPath;
const artifactIndex = process.argv.indexOf('--artifact-dir');
const artifactRoot = path.resolve(root, artifactIndex === -1 ? 'artifacts/slice21-checks' : process.argv[artifactIndex + 1]);
await mkdir(path.dirname(artifactRoot), { recursive: true });
// Refuse reused output roots BEFORE starting any preview or browser.
await mkdir(artifactRoot);
const onlyIndex = process.argv.indexOf('--only');
const only = onlyIndex === -1 ? null : process.argv[onlyIndex + 1].split(',');
const sourceDigests = {};
for (const file of ['shiftwork/client/app.js', 'tests/client/browser.mjs', 'tests/client/render_faults.mjs']) sourceDigests[file] = createHash('sha256').update(await readFile(path.join(root, file))).digest('hex');
await writeFile(path.join(artifactRoot, 'sources.json'), JSON.stringify(sourceDigests, null, 2), { flag: 'wx' });

// The preview prints its banner before uvicorn binds, so the banner is not
// proof the port answers: a foreign process holding the port leaves every row
// talking to the wrong server. Poll the board endpoint until this preview
// answers, or fail the row with the real cause.
async function waitReachable() {
  const deadline = Date.now() + 15000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/engagements/bookshop/board`);
      if (response.ok && (await response.json()).latest_shift?.id) return;
    } catch { /* not up yet */ }
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  throw new Error(`Preview on ${port} did not answer as this preview (is the port already in use?)`);
}

function startPreview(previewArgs = []) {
  // A disposable controller-side incident exercises real blocked API values.
  // This uses the production retirement operation after all six slots finalize;
  // seals, captures, candidate admission and the learner client stay unchanged.
  const blockedSource = `import tempfile
from pathlib import Path
import uvicorn
from demos.client import create_preview
from shiftwork.app import create_app
from shiftwork import comparison_flow
from shiftwork.store import db, repo
with tempfile.TemporaryDirectory(prefix='shiftwork-blocked-browser-') as directory:
    database = str(Path(directory) / 'preview.db')
    create_preview(database)
    app = create_app(database)
    @app.middleware('http')
    async def retire_completed_comparison(request, call_next):
        if request.method == 'GET' and request.url.path.startswith('/api/experiments/'):
            conn = db.connect(database)
            try:
                experiment = repo.get_experiment(conn, request.url.path.rsplit('/', 1)[-1])
                if experiment and experiment.kind == 'QUALIFYING_COMPARISON' and experiment.state == 'FINALIZED':
                    reservation = repo.get_exposure_reservation_for_experiment(conn, experiment.id)
                    comparison_flow.retire_comparison_exposure(conn, reservation.id)
            finally:
                conn.close()
        return await call_next(request)
    print('Preview: http://127.0.0.1:${port} (test-only invalidated exposure)', flush=True)
    uvicorn.run(app, host='127.0.0.1', port=${port}, log_level='error', access_log=False)
`;
  const args = previewArgs.includes('--blocked-preview') ? ['-c', blockedSource]
    : ['-m', 'demos.client', '--port', String(port), ...previewArgs];
  const preview = spawn(python, args, { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
  const stdout = [], stderr = [];
  preview.stdout.on('data', data => stdout.push(data));
  preview.stderr.on('data', data => stderr.push(data));
  let previewLog = '';
  const started = new Promise((resolve, reject) => {
    // The inherit preview builds the Slice 20 world through the offline
    // walkthrough before uvicorn starts, so it needs a longer budget.
    const timeout = setTimeout(() => reject(new Error(`Preview did not start in 120s:\n${previewLog}`)), 120000);
    preview.stdout.on('data', data => {
      previewLog += data;
      if (previewLog.includes(`Preview: http://127.0.0.1:${port}`)) { clearTimeout(timeout); resolve(); }
    });
    preview.stderr.on('data', data => { previewLog += data; });
    preview.once('exit', code => { clearTimeout(timeout); reject(new Error(`Preview exited ${code}:\n${previewLog}`)); });
  });
  return { preview, started, stdout, stderr };
}

async function stopPreview(preview) {
  preview.kill();
  await Promise.race([once(preview, 'exit'), new Promise(resolve => setTimeout(resolve, 3000))]).catch(() => {});
  if (preview.exitCode === null) preview.kill();
}

function harness(fault, args = [], key) {
  return new Promise(resolve => {
    const child = spawn(process.execPath, ['tests/client/browser.mjs', `http://127.0.0.1:${port}`, ...args], {
      cwd: root,
      env: { ...process.env, SHIFTWORK_ARTIFACT_DIR: path.join(artifactRoot, key), SHIFTWORK_FAULT: fault ?? '' },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    const stdout = [], stderr = [];
    child.stdout.on('data', data => stdout.push(data));
    child.stderr.on('data', data => stderr.push(data));
    child.once('exit', async code => {
      const outBytes = Buffer.concat(stdout), errBytes = Buffer.concat(stderr);
      const out = outBytes.toString('utf8'), err = errBytes.toString('utf8');
      const directory = path.join(artifactRoot, key);
      await mkdir(directory, { recursive: true });
      await writeFile(path.join(directory, 'stdout.txt'), outBytes, { flag: 'wx' });
      await writeFile(path.join(directory, 'stderr.txt'), errBytes, { flag: 'wx' });
      await writeFile(path.join(directory, 'exit.json'), JSON.stringify({ code, args, fault }, null, 2), { flag: 'wx' });
      resolve({ code, out, err });
    });
  });
}

const FAULTS = ['answer', 'record', 'verdict', 'event', 'eligibility', 'stationFocus', 'incidentFocus', 'candidateFreeze', 'slotOrdinalText', 'slotOrdinalKey', 'slotProtectedCount', 'outcomeMetric', 'outcomeEligibility', 'outcomeLabelBinding', 'inheritRationale', 'inheritAlternative', 'inheritRequirementHash', 'inheritObservedRun', 'inheritSeparation', 'inheritHistoryReturn', 'inheritLaterSelection', 'inheritStaleLater'];
// The compare-path rows need the flag that exercises them, and each baseline runs
// the same flags against its own unmutated preview so a red row cannot be vacuous.
const FAULT_ARGS = { candidateFreeze: ['--compare-demo'], slotOrdinalText: ['--compare-demo'], slotOrdinalKey: ['--compare-demo'], slotProtectedCount: ['--compare-demo'], outcomeMetric: ['--compare-demo'], outcomeEligibility: ['--compare-demo'], outcomeLabelBinding: ['--compare-demo'], inheritRationale: ['--inherit-demo'], inheritAlternative: ['--inherit-demo'], inheritRequirementHash: ['--inherit-demo'], inheritObservedRun: ['--inherit-demo'], inheritSeparation: ['--inherit-demo'], inheritHistoryReturn: ['--inherit-demo'], inheritLaterSelection: ['--inherit-demo'], inheritStaleLater: ['--inherit-demo'] };
// The next-shift rows need the preview that builds the Slice 20 inheritance and
// staged-outage world; the baseline pair mirrors the two worlds.
const PREVIEW_ARGS = { inheritRationale: ['--inherit'], inheritAlternative: ['--inherit'], inheritRequirementHash: ['--inherit'], inheritObservedRun: ['--inherit'], inheritSeparation: ['--inherit'], inheritHistoryReturn: ['--inherit'], inheritLaterSelection: ['--inherit'], inheritStaleLater: ['--inherit'] };
const BASELINE_ROWS = [
  { label: 'baseline (transient surfaces)', key: 'baseline-transient', args: [], preview: [] },
  { label: 'baseline (reload warning)', key: 'baseline-reload', args: ['--reload-warning-demo'], preview: [] },
  { label: 'baseline (candidate race)', key: 'baseline-race', args: ['--selection-demo', '--journey-demo', '--candidate-race-demo'], preview: [] },
  { label: 'baseline (no fault)', args: ['--compare-demo'], preview: [] },
  { label: 'baseline (invalidated exposure)', args: ['--compare-demo', '--blocked-demo'], preview: ['--blocked-preview'] },
  { label: 'baseline (selected journey)', args: ['--compare-demo', '--selection-demo', '--journey-demo'], preview: [] },
  { label: 'baseline (inherit, no fault)', args: ['--inherit-demo'], preview: ['--inherit'] },
];
FAULTS.push('executionPurpose', 'executionMode', 'executionVersion', 'executionSnapshot', 'comparisonPurpose', 'comparisonMode', 'comparisonContext', 'comparisonHistory', 'outcomeBlocker', 'selectedVersion', 'requirementVersion', 'syntheticEvent', 'clientLeak');
for (const name of ['comparisonPurpose', 'comparisonMode', 'comparisonContext', 'comparisonHistory']) FAULT_ARGS[name] = ['--compare-demo'];
FAULT_ARGS.outcomeBlocker = ['--compare-demo', '--blocked-demo'];
PREVIEW_ARGS.outcomeBlocker = ['--blocked-preview'];
FAULTS.push('invalidatedPolling');
FAULT_ARGS.invalidatedPolling = ['--compare-demo', '--blocked-demo'];
PREVIEW_ARGS.invalidatedPolling = ['--blocked-preview'];
for (const name of ['selectedVersion', 'requirementVersion']) FAULT_ARGS[name] = ['--selection-demo'];
FAULTS.push('draftSave', 'unsavedFreeze', 'candidateReload', 'candidateReset');
for (const name of ['draftSave', 'unsavedFreeze', 'candidateReload']) FAULT_ARGS[name] = ['--compare-demo'];
FAULT_ARGS.candidateReset = ['--selection-demo', '--journey-demo'];
FAULTS.push('transientErrorLeak', 'candidateRace', 'unloadWarning');
FAULT_ARGS.candidateRace = ['--selection-demo', '--journey-demo', '--candidate-race-demo'];
FAULT_ARGS.unloadWarning = ['--reload-warning-demo'];
const results = [];
let failures = 0;
const allRows = [
  ...BASELINE_ROWS.map(baseline => ({ ...baseline, key: baseline.key ?? (baseline.args.includes('--inherit-demo') ? 'baseline-inherit' : baseline.args.includes('--journey-demo') ? 'baseline-journey' : baseline.args.includes('--blocked-demo') ? 'baseline-blocked' : 'baseline-compare'), fault: null })),
  ...FAULTS.map(name => ({ label: `fault: ${name}`, fault: name,
                           key: name, args: FAULT_ARGS[name] ?? [], preview: PREVIEW_ARGS[name] ?? [] })),
];
if (only) for (const key of only) if (!allRows.some(row => row.key === key)) throw new Error(`Unknown row: ${key}`);
const rows = only ? allRows.filter(row => only.includes(row.key)) : allRows;
console.log(`Running ${rows.filter(row => !row.fault).length} baselines then ${rows.filter(row => row.fault).length} fault rows, each against its own preview on port ${port}.`);
for (const row of rows) {
  const { label, fault } = row;
  const { preview, started, stdout, stderr } = startPreview(row.preview);
  try {
    await started;
    await waitReachable();
    const run = await harness(fault, row.args, row.key);
    if (fault === null) {
      if (run.code === 0) {
        results.push(`${label.padEnd(34)} PASS   harness green against the unmutated client`);
      } else {
        failures += 1;
        results.push(`${label.padEnd(34)} FAIL   exit ${run.code}\n${(run.out + run.err).slice(-1500)}`);
      }
    } else {
      const caughtLine = run.out.match(new RegExp(`FAULT_CAUGHT ${fault}:[^\\n]*`))?.[0];
      if (run.code === 0 && caughtLine) {
        results.push(`fault: ${fault.padEnd(28)} CAUGHT ${caughtLine}`);
      } else {
        failures += 1;
        results.push(`fault: ${fault.padEnd(28)} ${run.code === 0 ? 'SURVIVED (harness exited green)' : `WRONG FAILURE (exit ${run.code})`}\n${(run.out + run.err).slice(-2000)}`);
      }
    }
  } catch (error) {
    failures += 1;
    results.push(`${label.padEnd(36)} PREVIEW FAILED ${error.message}`);
  } finally {
    await stopPreview(preview);
    const directory = path.join(artifactRoot, row.key);
    await mkdir(directory, { recursive: true });
    await writeFile(path.join(directory, 'preview-stdout.txt'), Buffer.concat(stdout), { flag: 'wx' });
    await writeFile(path.join(directory, 'preview-stderr.txt'), Buffer.concat(stderr), { flag: 'wx' });
    await writeFile(path.join(directory, 'preview-exit.json'), JSON.stringify({ code: preview.exitCode, signal: preview.signalCode }, null, 2), { flag: 'wx' });
  }
  console.log(results.at(-1));
}
console.log(`render-fault rows: ${results.length - failures} of ${results.length} as expected`);
await writeFile(path.join(artifactRoot, 'results.json'), JSON.stringify({ results, failures }, null, 2), { flag: 'wx' });
process.exitCode = failures === 0 && results.length === rows.length ? 0 : 1;
