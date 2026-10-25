// S47 offline presentation checks. Existing command handlers remain the owners.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {openBrowser, FAULTS} from './workplace_fullscreen.mjs';

export const FIRST_RUN_FAULTS = {
  's47-mode': {file:'/app.js',needle:"if (new URL(location.href).searchParams.get('guide') === '1') setFirstRun(true);",replacement:'',expect:'first_run: mode must be available'},
  's47-panels': {file:'/app.js',needle:'node.hidden = Number(node.dataset.guidedPanel) !== panel;',replacement:'node.hidden = false;',expect:'first_run: one panel at a time'},
  's47-navigation': {file:'/app.js',needle:'  browsedPanel = panel;',replacement:"  browsedPanel = panel; fetch('/__s47_navigation_fault', {method:'POST'});",expect:'first_run: navigation must send no command'},
  's47-visible': {file:'/styles.css',needle:'body[data-first-run="true"] .technical-literal { display: none; }',replacement:'body[data-first-run="true"] .technical-literal { display: inline; }',expect:'first_run: technical hash visible by default'},
  's47-literal': {file:'/app.js',needle:"element('code', value, 'technical-literal')",replacement:"element('code', value + '-changed', 'technical-literal')",expect:'first_run: exact technical literal missing'},
  's47-run-restoration': {file:'/app.js',needle:"    $('run-shift').hidden = workbenchRunHidden;",replacement:'',expect:'first_run: run control visibility restored'},
  's47-node-restoration': {file:'/app.js',needle:'anchor.replaceWith(node); node.hidden = hidden;',replacement:'anchor.replaceWith(node);',expect:'first_run: moved control visibility restored'},
  's47-clone': {file:'/app.js',needle:"    $('run-shift').hidden = workbenchRunHidden;",replacement:"    $('run-shift').hidden = workbenchRunHidden; $('run-shift').after($('run-shift').cloneNode(true));",expect:'first_run: commands must not be cloned'},
  's47-skip': {file:'/styles.css',needle:'transform: translateY(-160%);',replacement:'transform: none;',expect:'first_run: skip link hidden until focus'},
  's47-fade': {file:'/styles.css',needle:'.room[data-graphics="ready"] .station:is([data-resting="false"], [data-resting="speaker"]):not(:focus-visible):not([data-hover]) { transition: none; }',replacement:'.room[data-graphics="ready"] .station:is([data-resting="false"], [data-resting="speaker"]):not(:focus-visible):not([data-hover]) { transition: opacity 180ms ease; }',expect:'first_run: hidden labels must disappear immediately'},
  's47-prefix': {file:'/app.js',needle:'if (match.index > end) fragment.append(document.createTextNode(node.textContent.slice(end, match.index)));',replacement:'void 0;',expect:'first_run: outcome before technical value stays visible'},
  's47-option': {file:'/app.js',needle:"original.replaceAll(option.value, 'recorded run').replaceAll(mode, evidenceLabel(mode))",replacement:'original',expect:'first_run: unknown option evidence stays unknown'},
  's47-option-reveal': {file:'/app.js',needle:"const shown = document.body.dataset.technicalOpen === 'true' ? original",replacement:"const shown = false ? original",expect:'first_run: exact option literal must be revealed'},
  's47-toggle-reset': {file:'/app.js',needle:"  document.querySelectorAll('[data-guided-technical-toggle]').forEach(node => node.setAttribute('aria-pressed', 'false'));",replacement:'',expect:'first_run: technical toggle resets on re-entry'},
  's47-outcomes': {file:'/app.js',needle:'if (records.parentNode !== parent) {',replacement:'if (false) {',expect:'first_run: comparison outcomes stay visible in Choose'},
  's47-suffix': {file:'/app.js',needle:'if (end < node.textContent.length) fragment.append(document.createTextNode(node.textContent.slice(end)));',replacement:'void 0;',expect:'first_run: outcome after technical value stays visible'},
};
export async function runFirstRunBrowser(base, out, slug = 'bookshop', fault = '', {quick = false} = {}) {
Object.assign(FAULTS, FIRST_RUN_FAULTS);
const boardData = await fetch(`${base}/api/engagements/${slug}/board`).then(r => r.json());
const stationData = boardData.latest_shift ? await fetch(`${base}/api/shifts/${boardData.latest_shift.id}/investigations`).then(r => r.json()) : null;
const comparison = stationData?.latest_experiment?.kind === 'QUALIFYING_COMPARISON' ? stationData.latest_experiment : null;
const publicOutputs = boardData.latest_run ? await fetch(`${base}/api/runs/${boardData.latest_run.id}/outputs`).then(r => r.json()) : [];
const hashes = [boardData.latest_version?.content_hash, boardData.operating_selection?.selected_content_hash, comparison?.context_hash, ...(comparison?.candidates ?? []).map(row => row.artifact_content_hash), ...publicOutputs.map(row => row.public_shop_snapshot_hash)].filter(value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value));
const b = await openBrowser(base, out, fault);
const rows = [];
try {
  for (const [width, height] of ((fault || quick) ? [[1440, 900]] : [[1440, 900], [1280, 720], [390, 844]])) {
    await b.send('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: 1, mobile: false});
    await b.send('Page.navigate', {url: `${base}/?board=${slug}&guide=1`});
    assert.ok(await b.until(() => ['ready', 'empty'].includes(document.body?.dataset.loadState)), 'first_run: board did not settle');
    assert.ok(await b.evaluate(() => document.body.dataset.firstRun === 'true'), 'first_run: mode must be available');
    assert.ok(await b.until(() => document.querySelector('.room')?.dataset.graphics === 'ready'), 'first_run: WebGL room must remain available');
    assert.ok(await b.evaluate(() => document.querySelector('.skip-link').getBoundingClientRect().bottom < 0), 'first_run: skip link hidden until focus');
    await b.send('Input.dispatchKeyEvent', {type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9});
    await b.send('Input.dispatchKeyEvent', {type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9});
    assert.ok(await b.evaluate(() => document.activeElement === document.querySelector('.skip-link') && document.activeElement.getBoundingClientRect().bottom > 0), 'first_run: keyboard reveals the skip link');
    const recommendedBefore = await b.evaluate(() => document.getElementById('guided-status').textContent.split('. Viewing')[0]);
    const commands = b.commands.length;
    for (let panel = 1; panel <= 5; panel++) {
      await b.evaluate(panel => document.querySelector(`[data-first-run-go="${panel}"]`).click(), panel);
      assert.ok(await b.until(panel => document.querySelector(`[data-guided-panel="${panel}"]`)?.hidden === false, 3000, panel), 'first_run: navigation must open the requested panel');
      assert.equal(await b.evaluate(() => document.querySelectorAll('[data-guided-panel]:not([hidden])').length), 1, 'first_run: one panel at a time');
      assert.ok(await b.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'first_run: horizontal overflow');
      const rendered = await b.evaluate(() => document.getElementById('station-panel').innerText);
      for (const hash of hashes) assert.ok(!rendered.includes(hash) && !rendered.includes(hash.slice(0, 12) + '…'), 'first_run: technical hash visible by default');
      if (panel === 2) assert.ok(await b.evaluate(() => ['cause-input', 'falsifier-input', 'public-test-input', 'append-investigation', 'run-diagnostic'].every(id => document.getElementById(id).getClientRects().length)), 'first_run: cause falsifier and public test must remain available');
      if (panel === 4) assert.ok(await b.evaluate(slug => document.getElementById(slug === 'gtm' ? 'operate-pipeline' : slug === 'northline' ? 'operate-pilot' : 'run-shift').getClientRects().length > 0, slug), 'first_run: operation stays explicit in Choose');
      if (panel === 4 && comparison?.outcome) {
        const actual = await b.evaluate(() => [...document.querySelectorAll('#comparison-outcome .comparison-outcome-card')].map(card => ({label: card.dataset.candidateLabel, eligible: card.dataset.eligible, visible: card.getClientRects().length > 0, metrics: Object.fromEntries([...card.querySelectorAll('[data-metric]')].map(node => [node.dataset.metric, node.innerText]))})));
        assert.ok(actual.length === comparison.outcome.candidate_metrics.length && actual.every(row => row.visible), 'first_run: comparison outcomes stay visible in Choose');
        for (const expected of comparison.outcome.candidate_metrics) {
          const card = actual.find(row => row.label === expected.candidate_label);
          for (const key of ['useful_completions', 'justified_refusals', 'missing_outputs', 'cost_minor_units']) assert.equal(card.metrics[key], String(expected[key] ?? 'unknown'), `first_run: important metric ${key} remains exact`);
          assert.equal(card.eligible, String(comparison.outcome.eligibility.find(row => row.candidate_label === card.label).eligible), 'first_run: eligibility stays exact');
        }
        assert.ok(await b.evaluate(() => [...document.querySelectorAll('[data-provider-reasoning]')].every(node => !node.open)), 'first_run: provider reasoning stays separately collapsed');
      }
      if (panel === 5) assert.ok(await b.evaluate(() => ['close-shift', 'open-next-shift', 'guided-review-report'].every(id => document.getElementById(id).getClientRects().length)), 'first_run: consequence review closure and inheritance remain available');
      if (width === 390) assert.ok(await b.until(() => { const r = document.getElementById('guided-controls').getBoundingClientRect(); return r.top >= 0 && r.top < innerHeight; }), 'first_run: current panel must be in reach');
      assert.ok(await b.evaluate(() => [...document.querySelectorAll('.station:is([data-resting="false"], [data-resting="speaker"]):not(:focus-visible):not([data-hover])')].every(node => getComputedStyle(node).transitionDuration === '0s')), 'first_run: hidden labels must disappear immediately');
      const geometry = await b.evaluate(() => {
        const visible = [...document.querySelectorAll('.station, .bubble')].filter(node => { const r = node.getBoundingClientRect(), c = getComputedStyle(node); return r.width && r.height && c.display !== 'none' && c.visibility !== 'hidden' && Number(c.opacity) > 0; });
        const overlaps = [];
        for (let i = 0; i < visible.length; i++) for (let j = i + 1; j < visible.length; j++) { const a = visible[i].getBoundingClientRect(), c = visible[j].getBoundingClientRect(); if (a.left < c.right && c.left < a.right && a.top < c.bottom && c.top < a.bottom) overlaps.push([visible[i].innerText, visible[j].innerText]); }
        return {overlaps, canvas: document.getElementById('workplace-canvas').getBoundingClientRect().height};
      });
      assert.deepEqual(geometry.overlaps, [], 'first_run: room labels must not overlap');
      assert.ok(geometry.canvas >= (width === 390 ? 200 : height - 230), 'first_run: room must use available layout');
      const image = await b.send('Page.captureScreenshot', {format: 'png'});
      await writeFile(path.join(out, `${slug}-${width}-panel-${panel}.png`), Buffer.from(image.data, 'base64'));
    }
    assert.equal(b.commands.length, commands, 'first_run: navigation must send no command');
    assert.equal(await b.evaluate(() => document.getElementById('guided-status').textContent.split('. Viewing')[0]), recommendedBefore, 'first_run: browsing must not complete recorded work');
    await b.evaluate(() => document.querySelector('[data-first-run-go="1"]').click());
    const board = await fetch(`${base}/api/engagements/${slug}/board`).then(r => r.json());
    await b.evaluate(() => { const p = document.createElement('p'); p.id = 's47-scanner-control'; p.dataset.runId = 'run-S47-display-control'; p.textContent = 'Mandatory failure before run-S47-display-control; cost unknown after'; document.getElementById('guided-panel-1').append(p); });
    assert.ok(await b.until(() => document.querySelector('#s47-scanner-control .technical-value')), 'first_run: technical scanner positive control');
    assert.ok(await b.evaluate(() => document.getElementById('s47-scanner-control').innerText.includes('Mandatory failure before')), 'first_run: outcome before technical value stays visible');
    assert.ok(await b.evaluate(() => document.getElementById('s47-scanner-control').innerText.includes('; cost unknown after')), 'first_run: outcome after technical value stays visible');
    await b.evaluate(() => document.getElementById('s47-scanner-control').remove());
    await b.evaluate(() => { const select = document.createElement('select'); select.id = 's47-mode-control'; const option = document.createElement('option'); option.value = 'run-S47-unknown'; option.dataset.evidenceMode = 'FUTURE_MODE'; option.textContent = 'Run 1: run-S47-unknown · COMPLETE · FUTURE_MODE'; select.append(option); document.getElementById('guided-panel-1').append(select); });
    assert.ok(await b.until(() => document.querySelector('#s47-mode-control option').textContent.includes('evidence unknown'), 2000), 'first_run: unknown option evidence stays unknown');
    const run = board.latest_run;
    if (run) {
      const outputs = await fetch(`${base}/api/runs/${run.id}/outputs`).then(r => r.json());
      const values = [run.id, outputs.find(o => o.public_shop_snapshot_hash)?.public_shop_snapshot_hash, run.evidence_mode].filter(Boolean);
      const visible = await b.evaluate(() => document.getElementById('station-panel').innerText);
      for (const value of values) assert.ok(!visible.includes(value), `first_run: technical literal visible by default: ${value}`);
      await b.evaluate(() => document.getElementById('guided-technical').click());
      assert.equal(await b.evaluate(() => document.querySelector('#s47-mode-control option').textContent), 'Run 1: run-S47-unknown · COMPLETE · FUTURE_MODE', 'first_run: exact option literal must be revealed');
      const shown = await b.evaluate(() => [...document.querySelectorAll('#station-panel .technical-literal')].map(node => node.textContent));
      for (const value of values) assert.ok(shown.includes(value), `first_run: exact technical literal missing: ${value}`);
      // Prove the rendered-text detector sees its actual needle.
      assert.ok(values.every(value => shown.includes(value)), 'first_run: scanner positive control');
    }
    await b.evaluate(() => document.getElementById('s47-mode-control').remove());
    await b.evaluate(() => { document.getElementById('cause-input').value = 'S47 unsaved authorship'; document.getElementById('guided-toggle').click(); });
    assert.ok(await b.evaluate(() => document.body.dataset.firstRun === 'false' && document.getElementById('cause-input').value === 'S47 unsaved authorship'), 'first_run: full workbench preserves unsaved authorship');
    assert.ok(await b.evaluate(() => !document.getElementById('run-shift').hidden), 'first_run: run control visibility restored');
    assert.ok(await b.evaluate(() => !document.getElementById('operate-pilot').hidden && !document.getElementById('operate-pipeline').hidden), 'first_run: moved control visibility restored');
    assert.ok(await b.evaluate(() => ['run-shift', 'operate-pilot', 'operate-pipeline', 'save-draft', 'falsifier-input', 'open-next-shift'].every(id => document.querySelectorAll(`#${id}`).length === 1)), 'first_run: commands must not be cloned');
    await b.evaluate(() => document.getElementById('guided-toggle').click());
    assert.ok(await b.evaluate(() => document.body.dataset.technicalOpen === 'false' && document.getElementById('guided-technical').getAttribute('aria-pressed') === 'false'), 'first_run: technical toggle resets on re-entry');
    await b.evaluate(() => document.getElementById('guided-toggle').click());
    rows.push({slug, width, height, panels: 5});
  }
  assert.deepEqual(b.exceptions, [], 'first_run: browser exceptions');
  b.assertFaultServed();
  await writeFile(path.join(out, 'first-run.json'), JSON.stringify({rows, commands: b.commands}, null, 2));
  console.log(JSON.stringify({result: 'PASS', rows}));
} catch (error) { b.assertFaultServed(); throw error; } finally { await b.close(); }

}
if (process.argv[1] === fileURLToPath(import.meta.url)) { const [base, out, slug = 'bookshop', fault = ''] = process.argv.slice(2); await runFirstRunBrowser(base, out, slug, fault); }
