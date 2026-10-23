// Explicitly invoked S44 room demonstration. No retries or automatic new batches.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { openBrowser } from './workplace_fullscreen.mjs';

const [base, out, mode] = process.argv.slice(2);
const width = Number(process.env.SHIFTWORK_PREVIEW_WIDTH || 1280);
assert.ok([390, 1280].includes(width), 'Use a verified demonstration viewport');
assert.ok(['live', 'inspect-live', 'recorded', 'inspect-recorded'].includes(mode), 'Explicit live or recorded demonstration/inspection mode is required');
assert.ok(base?.startsWith('http://127.0.0.1:'), 'Use an owned local controller');
await mkdir(out, {recursive: true});
const before = await (await fetch(`${base}/api/engagements/bookshop/board`)).json();
if (mode.startsWith('inspect-')) assert.ok(before.latest_shift, 'Read-only inspection needs the retained batch');
else assert.equal(before.latest_shift, null, 'This demonstration needs a fresh disposable database');
const browser = await openBrowser(base, out);
try {
  await browser.send('Emulation.setDeviceMetricsOverride', {width, height: width === 390 ? 844 : 800, deviceScaleFactor: 1, mobile: false});
  await browser.send('Page.navigate', {url: `${base}/?board=bookshop`});
  assert.ok(await browser.until(expected => document.body?.dataset.loadState === expected,
    20000, mode.startsWith('inspect-') ? 'ready' : 'empty'), 'Room did not load');
  if (!mode.startsWith('inspect-')) await browser.evaluate(() => {
      document.querySelector('[data-station="customers"]').click();
      document.getElementById('open-shift').click();
    });
  assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready'), 'Shift did not open');
  if (mode === 'live') {
    await browser.evaluate(() => {
      document.querySelector('[data-station="compare"]').click();
      document.getElementById('freeze-candidate-a').click();
    });
    assert.ok(await browser.until(() => !document.getElementById('freeze-candidate-a').disabled), 'Starter freeze did not finish');
    await browser.evaluate(() => document.querySelector('[data-station="investigate"]').click());
    assert.ok(await browser.until(() => !document.getElementById('run-diagnostic').disabled), 'Public starter diagnostic is unavailable');
    await browser.evaluate(() => {
      document.getElementById('diagnostic-repetitions').value = '10';
      document.getElementById('run-diagnostic').click();
    });
  } else if (mode === 'recorded') {
    await browser.evaluate(() => document.getElementById('run-shift').click());
  }
  const board = await (await fetch(`${base}/api/engagements/bookshop/board`)).json();
  const shiftId = board.latest_shift.id;
  const deadline = Date.now() + 590000;
  let experiment = null, completed = -1;
  while (Date.now() < deadline) {
    const response = await fetch(`${base}/api/shifts/${shiftId}/investigations`);
    assert.ok(response.ok, 'Investigation projection request failed');
    const station = await response.json();
    experiment = station.latest_diagnostic;
    if (experiment) {
      const count = experiment.trials.filter(row => ['COMPLETE', 'FAILED'].includes(row.state)).length;
      if (count !== completed) { console.log(`${mode}: ${count} of ${experiment.public_repetitions} repetitions terminal`); completed = count; }
      if (['FINALIZED', 'FAILED'].includes(experiment.state)) break;
    }
    await new Promise(resolve => setTimeout(resolve, 1500));
  }
  assert.ok(experiment && ['FINALIZED', 'FAILED'].includes(experiment.state), 'Batch remains nonterminal; no automatic retry is allowed');
  await writeFile(path.join(out, 'experiment.json'), JSON.stringify(experiment, null, 2));
  await browser.evaluate(() => document.getElementById('refresh').click());
  assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready'), 'Room refresh did not finish');
  await browser.evaluate(() => {
    document.querySelector('[data-station="investigate"]').click();
    document.getElementById('diagnostic-result').scrollIntoView({block: 'start', behavior: 'instant'});
  });
  const shot = await browser.send('Page.captureScreenshot', {format: 'png'});
  await writeFile(path.join(out, 'room.png'), Buffer.from(shot.data, 'base64'));
  assert.ok(await browser.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Room has horizontal page overflow');
  assert.equal(experiment.public_repetitions, 10);
  assert.equal(experiment.trials.length, 10);
  assert.equal(experiment.eligible, false);
  assert.ok(experiment.trials.every(row => row.evidence_mode === (mode.endsWith('recorded') ? 'RECORDED_INSPECTION' : 'ISOLATED_LIVE')));
  assert.notEqual(await browser.evaluate(() => document.getElementById('workplace-state').textContent),
    'Recorded reads disagree. Inspect the workbench; current labels are unavailable.', 'Room evidence bindings disagree');
  assert.deepEqual(browser.exceptions, []);
  browser.assertFaultServed();
  console.log(JSON.stringify({mode, experiment_id: experiment.id, state: experiment.state,
    retained_summary: !!experiment.repetition_summary, stop_rule_triggered: experiment.repetition_summary?.stop_rule_triggered ?? null}));
} finally { await browser.close(); }
