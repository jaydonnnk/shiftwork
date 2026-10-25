import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { openBrowser, FAULTS } from './workplace_fullscreen.mjs';

const [base, out, fault = ''] = process.argv.slice(2);
FAULTS['s44-shown-rate'] = {file: '/evidence.js',
  needle: '${row.task_id} task missing in ${misses} of ${count} runs (',
  replacement: '${row.task_id} task missing in ${misses + 1} of ${count} runs (',
  expect: 'rendered_miss_rate: the exact retained rate is not shown'};
FAULTS['s44-stale-source'] = {file: '/app.js',
  needle: '    ?? experiment.trials.find(trial => trial.run_id === missed) ?? experiment.trials[0] ?? null;',
  replacement: '    ?? experiment.trials[0] ?? null;',
  expect: 'a stale selection must fall back to an observed miss'};
const browser = await openBrowser(base, out, fault, {webgl: false});
try {
  for (const [width, height] of [[1280, 800], [390, 844]]) {
    await browser.send('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: 1, mobile: false});
    await browser.send('Page.navigate', {url: base});
    assert.ok(await browser.until(() => document.body?.dataset.loadState === 'ready'), 'fixture board did not load');
    await browser.evaluate(() => document.querySelector('[data-station="investigate"]').click());
    assert.ok(await browser.until(() => document.getElementById('diagnostic-result').textContent.includes('Operator-authored')), 'rendering fixture label missing');
    const text = await browser.evaluate(() => document.getElementById('diagnostic-result').textContent);
    assert.ok(text.includes('alternative task missing in 1 of 2 runs (reply cut off at the output limit in 0, invalid plan in 0, plan left the task out in 1)'), 'rendered_miss_rate: the exact retained rate is not shown');
    assert.ok(text.includes('OPERATOR_AUTHORED_TEST_REPLY'), 'rendering fixture must never claim model output');
    assert.ok(text.includes('small sample'), 'sample limit missing');
    assert.equal(await browser.evaluate(() => document.getElementById('diagnostic-retained-run').options.length), 2);
    await browser.evaluate(() => {
      const select = document.getElementById('diagnostic-retained-run');
      select.value = 'fixture-run-1'; select.dispatchEvent(new Event('change'));
      document.getElementById('diagnostic-result').scrollIntoView({block: 'start', behavior: 'instant'});
    });
    assert.equal(await browser.evaluate(() => document.getElementById('diagnostic-retained-run').value), 'fixture-run-1');
    await browser.evaluate(() => {
      document.getElementById('diagnostic-result').dataset.selectedRunId = 'prior-experiment-run';
      document.getElementById('refresh').click();
    });
    assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready'), 'refreshed fixture did not load');
    assert.equal(await browser.evaluate(() => document.getElementById('diagnostic-retained-run')?.value), 'fixture-run-2', 'a stale selection must fall back to an observed miss');
    const bounds = await browser.evaluate(() => ({width: innerWidth, scroll: document.documentElement.scrollWidth,
      selects: [...document.querySelectorAll('select')].map(node => ({id: node.id, left: node.getBoundingClientRect().left, width: node.getBoundingClientRect().width}))}));
    await writeFile(path.join(out, `bounds-${width}.json`), JSON.stringify(bounds, null, 2));
    const shot = await browser.send('Page.captureScreenshot', {format: 'png'});
    await mkdir(out, {recursive: true});
    await writeFile(path.join(out, `diagnostic-${width}.png`), Buffer.from(shot.data, 'base64'));
    assert.ok(bounds.scroll <= bounds.width, 'diagnostic has horizontal page overflow');
  }
  browser.assertFaultServed();
  assert.deepEqual(browser.exceptions, [], 'JavaScript exception');
  await writeFile(path.join(out, 'result.json'), JSON.stringify({status: 'PASS', label: 'operator-authored rendering fixtures only', widths: [1280, 390]}, null, 2));
  console.log('PASS: diagnostic rates, both retained runs, fixture labels, desktop and mobile');
} finally { await browser.close(); }
