import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdir, copyFile, writeFile, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { once } from 'node:events';
import { pythonPath } from './env.mjs';

const root = process.cwd();
const base = path.resolve(process.argv[2]);
const snapshots = path.resolve(process.argv[3]);
const port = Number(process.argv[4] ?? 8170);
await mkdir(base, { recursive: true });
const source = (await readFile('shiftwork/client/app.js', 'utf8')).replaceAll('\r\n', '\n');
// Keep this inventory tied to the single production-source mutation definitions.
// Preflight every exact anchor before starting any fault browser.
const harness = await readFile('tests/client/gtm_browser.mjs', 'utf8');
const definitions = harness.match(/const FAULTS = (\{[\s\S]*?\n\});/)[1];
const faults = (0, eval)(`(${definitions})`);
for (const [name, [needle]] of Object.entries(faults)) assert.equal(source.split(needle).length - 1, 1, `Unique current anchor required: ${name}`);
const digests = {};
for (const filename of ['shiftwork/client/app.js', 'shiftwork/client/index.html', 'shiftwork/client/styles.css', 'tests/client/gtm_browser.mjs', 'tests/client/gtm_preview.py']) digests[filename] = createHash('sha256').update(await readFile(filename)).digest('hex');
// A resume keeps the first invocation's digests and rows: reruns after a stall or
// a repaired row must not rewrite history or repeat already-valid pairs.
const priorSources = await readFile(path.join(base, 'sources.json'), 'utf8').catch(() => null);
if (priorSources) assert.deepEqual(JSON.parse(priorSources), digests, 'Sources changed between fault-suite invocations');
else await writeFile(path.join(base, 'sources.json'), JSON.stringify(digests, null, 2), { flag: 'wx' });
const priorRows = JSON.parse(await readFile(path.join(base, 'results.json'), 'utf8').catch(() => '[]'));
const carried = new Set();
for (const row of priorRows) if (row.valid) carried.add(`${row.fault}/${row.mode}`);
// The wall rows for owners, clocks, provenance, payload, counts, synthetic label,
// resolutions and the executed/selected/inherited values only exist after the
// operated snapshot; the open incident, the comparison and the assistance guards
// exist in the comparison snapshot.
const closed = new Set(['pipelineOwner', 'pipelineClock', 'pipelineResolving', 'pipelinePayload', 'pipelineProvenance', 'pipelineCounts', 'pipelineSynthetic', 'escalationHonesty', 'outputVersion', 'selectedVersion', 'inheritance', 'purpose', 'evidenceMode']);
const reach = new Set(['mobileFocus']);
const rows = [...priorRows];
async function stop(child) {
  if (child.exitCode === null) child.kill();
  if (child.exitCode === null) await Promise.race([once(child, 'exit'), new Promise(resolve => setTimeout(resolve, 2000))]);
}
for (const [fault, [, , expected]] of Object.entries(faults)) {
  if (carried.has(`${fault}/clean`) && carried.has(`${fault}/fault`)) {
    console.log(`${fault} carried from an earlier invocation of this suite`);
    continue;
  }
  const snapshot = reach.has(fault) ? 'reach' : closed.has(fault) ? 'closed' : 'comparison';
  for (const mode of ['clean', 'fault']) {
    const directory = path.join(base, fault + '-' + mode); await mkdir(directory, { recursive: true });
    const database = path.join(directory, 'preview.db');
    await copyFile(path.join(snapshots, (snapshot === 'reach' ? 'closed' : snapshot) + '.db'), database);
    const code = "import runpy,sys; sys.argv=['gtm_preview.py',*sys.argv[1:]]; runpy.run_path('tests/client/gtm_preview.py',run_name='__main__')";
    const preview = spawn(pythonPath, ['-c', code, '--database', database, '--out', directory, '--port', String(port)], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
    const previewOut = [], previewErr = [];
    preview.stdout.on('data', value => previewOut.push(value)); preview.stderr.on('data', value => previewErr.push(value));
    let browser;
    try {
      let reached = false;
      const deadline = Date.now() + 15000;
      while (Date.now() < deadline && preview.exitCode === null) {
        try { const response = await fetch(`http://127.0.0.1:${port}/api/engagements/gtm/board`); if (response.ok && (await response.json()).latest_shift) { reached = true; break; } } catch {}
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      assert.equal(reached, true, `Preview setup failed: ${Buffer.concat(previewErr).toString()}`);
      browser = spawn(process.execPath, ['tests/client/gtm_browser.mjs', `http://127.0.0.1:${port}/?board=gtm`], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, SHIFTWORK_FAULT: mode === 'fault' ? fault : '', SHIFTWORK_SNAPSHOT: snapshot, SHIFTWORK_ARTIFACT_DIR: path.join(directory, 'browser'), SHIFTWORK_TEST_INPUTS: path.join(directory, 'candidate-files.json') } });
      const stdout = [], stderr = [];
      browser.stdout.on('data', value => stdout.push(value)); browser.stderr.on('data', value => stderr.push(value));
      const [exit] = await once(browser, 'exit');
      const output = Buffer.concat(stdout), error = Buffer.concat(stderr);
      await writeFile(path.join(directory, 'stdout.txt'), output, { flag: 'wx' });
      await writeFile(path.join(directory, 'stderr.txt'), error, { flag: 'wx' });
      const text = error.toString();
      const valid = mode === 'clean' ? exit === 0 : exit === 1 && text.includes('AssertionError') && text.includes(expected) && text.includes('"exceptions":[]');
      rows.push({ fault, mode, snapshot, exit, intended_assertion: expected, valid });
      await writeFile(path.join(base, 'results.json'), JSON.stringify(rows, null, 2));
      assert.equal(valid, true, `Invalid ${fault}/${mode} result: ${text}`);
      console.log(`${fault}/${mode} ${mode === 'clean' ? 'PASS' : 'ASSERTION_CAUGHT'}`);
    } finally {
      if (browser) await stop(browser);
      await stop(preview);
      await writeFile(path.join(directory, 'preview-stdout.txt'), Buffer.concat(previewOut), { flag: 'wx' });
      await writeFile(path.join(directory, 'preview-stderr.txt'), Buffer.concat(previewErr), { flag: 'wx' });
    }
  }
}
for (const [filename, digest] of Object.entries(digests)) assert.equal(createHash('sha256').update(await readFile(filename)).digest('hex'), digest, `Source changed during fault proof: ${filename}`);
console.log(JSON.stringify({ pairs: rows.length / 2, intended_assertion_failures: rows.filter(row => row.mode === 'fault' && row.valid).length, source_preserved: true }));
