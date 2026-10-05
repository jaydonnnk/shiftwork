import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdir, copyFile, writeFile, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { once } from 'node:events';

const root = process.cwd();
const base = path.resolve(process.argv[2]);
const snapshots = path.resolve(process.argv[3]);
const port = Number(process.argv[4] ?? 8160);
await mkdir(base);
const source = (await readFile('shiftwork/client/app.js', 'utf8')).replaceAll('\r\n', '\n');
// Keep this inventory tied to the single production-source mutation definitions.
// Preflight every exact anchor before starting any fault browser.
const harness = await readFile('tests/client/northline_browser.mjs', 'utf8');
const definitions = harness.match(/const FAULTS = (\{[\s\S]*?\n\});/)[1];
const faults = (0, eval)(`(${definitions})`);
for (const [name, [needle]] of Object.entries(faults)) assert.equal(source.split(needle).length - 1, 1, `Unique current anchor required: ${name}`);
const digests = {};
for (const filename of ['shiftwork/client/app.js', 'shiftwork/client/index.html', 'shiftwork/client/styles.css', 'tests/client/northline_browser.mjs', 'tests/client/northline_preview.py']) digests[filename] = createHash('sha256').update(await readFile(filename)).digest('hex');
await writeFile(path.join(base, 'sources.json'), JSON.stringify(digests, null, 2), { flag: 'wx' });
const closed = new Set(['pilotPayload', 'handoverPayload', 'selectedWorksheet', 'outputVersion', 'selectedVersion', 'syntheticLabel']);
const reach = new Set(['mobileFocus']);
const rows = [];
async function stop(child) {
  if (child.exitCode === null) child.kill();
  if (child.exitCode === null) await Promise.race([once(child, 'exit'), new Promise(resolve => setTimeout(resolve, 2000))]);
}
for (const [fault, [, , expected]] of Object.entries(faults)) {
  const snapshot = reach.has(fault) ? 'reach' : closed.has(fault) ? 'closed' : 'comparison';
  for (const mode of ['clean', 'fault']) {
    const directory = path.join(base, fault + '-' + mode); await mkdir(directory);
    const database = path.join(directory, 'preview.db');
    await copyFile(path.join(snapshots, (snapshot === 'reach' ? 'closed' : snapshot) + '.db'), database);
    const code = "import runpy,sys; sys.argv=['northline_preview.py',*sys.argv[1:]]; runpy.run_path('tests/client/northline_preview.py',run_name='__main__')";
    const preview = spawn(path.join(root, '.venv313/Scripts/python.exe'), ['-c', code, '--database', database, '--out', directory, '--port', String(port)], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] });
    const previewOut = [], previewErr = [];
    preview.stdout.on('data', value => previewOut.push(value)); preview.stderr.on('data', value => previewErr.push(value));
    let browser;
    try {
      let reached = false;
      const deadline = Date.now() + 15000;
      while (Date.now() < deadline && preview.exitCode === null) {
        try { const response = await fetch(`http://127.0.0.1:${port}/api/engagements/northline/board`); if (response.ok && (await response.json()).latest_shift) { reached = true; break; } } catch {}
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      assert.equal(reached, true, `Preview setup failed: ${Buffer.concat(previewErr).toString()}`);
      browser = spawn(process.execPath, ['tests/client/northline_browser.mjs', `http://127.0.0.1:${port}/?board=northline`], { cwd: root, stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, SHIFTWORK_FAULT: mode === 'fault' ? fault : '', SHIFTWORK_SNAPSHOT: snapshot, SHIFTWORK_ARTIFACT_DIR: path.join(directory, 'browser'), SHIFTWORK_TEST_INPUTS: path.join(directory, 'candidate-files.json') } });
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
