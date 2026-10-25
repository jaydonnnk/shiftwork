// S47 review regressions use real navigation and public text in an owned preview.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {openBrowser, FAULTS, INSTRUMENT} from './workplace_fullscreen.mjs';
INSTRUMENT.push({file: '/app.js', needle: 'function renderInvestigations(station) {',
  replacement: 'globalThis.__s47RenderInvestigations = renderInvestigations; function renderInvestigations(station) {'});

export const REVIEW_FAULTS = {
  's47-review-station': {file: '/app.js', needle: '  if (firstRun) setFirstRun(false);\n  activateStation(name);',
    replacement: '  activateStation(name);', expect: 'first_run_review: station pick must open the full workbench', check: 'station', slug: 'northline'},
  's47-review-prose': {file: '/app.js', needle: '|RECORDED_INSPECTION|',
    replacement: '|run-[\\w-]+|RECORDED_INSPECTION|', expect: 'first_run_review: ordinary evidence words must stay exact', check: 'prose', slug: 'bookshop'},
  's47-review-refresh': {file: '/app.js', needle: '  if (view) {\n    const context =',
    replacement: '  if (true) {\n    view ??= {};\n    const context =', expect: 'first_run_review: loading must preserve the browsed panel', check: 'refresh', slug: 'bookshop'},
  's47-review-investigation': {file: '/app.js', needle: '    row.dataset.runId = entry.source_run_id;',
    replacement: '', expect: 'first_run_review: historical investigation ID must stay collapsed', check: 'investigation', slug: 'bookshop'},
};
Object.assign(FAULTS, REVIEW_FAULTS);
export const HISTORICAL_RUN_ATTRIBUTES = ['data-opening-run', 'data-wall-run', 'data-pipeline-run', 'data-pipeline-incident-run', 'data-selected-run-id', 'data-observed-run', 'data-latest-run', 'data-observed-run-id'];
export const IDENTITY_FAULTS = Object.fromEntries(HISTORICAL_RUN_ATTRIBUTES.map(attribute => [
  's47-id-' + attribute, {file: '/app.js', needle: "'" + attribute + "'", replacement: "'ignored-" + attribute + "'",
    expect: 'first_run_review: historical identity must stay collapsed: ' + attribute},
]));
Object.assign(FAULTS, IDENTITY_FAULTS);

export async function runFirstRunRegression(base, out, check, slug = 'bookshop', fault = '') {
  const b = await openBrowser(base, out, fault);
  try {
    await b.send('Emulation.setDeviceMetricsOverride', {width: 1280, height: 720, deviceScaleFactor: 1, mobile: false});
    await b.send('Page.navigate', {url: `${base}/?board=${slug}&guide=1`});
    assert.ok(await b.until(() => ['ready', 'empty'].includes(document.body?.dataset.loadState)), 'review: board did not settle');
    assert.equal(await b.evaluate(() => document.body.dataset.firstRun), 'true');
    const before = b.commands.length;
    if (check === 'station') {
      const station = {bookshop: 'owner', gtm: 'rules', northline: 'map'}[slug];
      await b.evaluate(station => document.querySelector(`[data-station="${station}"]`).click(), station);
      assert.equal(await b.evaluate(() => document.body.dataset.firstRun), 'false', 'first_run_review: station pick must open the full workbench');
      assert.ok(await b.evaluate(slug => document.getElementById(slug === 'northline' ? 'map-view' : 'board-view').getBoundingClientRect().height > 0, slug), 'first_run_review: picked station content must be visible');
    } else if (check === 'prose') {
      await b.evaluate(() => {
        document.querySelector('[data-first-run-go="1"]').click();
        const words = document.createElement('p'); words.id = 'review-prose';
        words.textContent = 'The run-time limit caused the failure. This is a run-of-the-mill timeout.';
        const metadata = document.createElement('p'); metadata.id = 'review-run'; metadata.dataset.runId = 'run-9001';
        metadata.textContent = 'Observed run-9001; mandatory failure; cost unknown.';
        document.getElementById('guided-panel-1').append(words, metadata);
      });
      assert.ok(await b.until(() => document.querySelector('#review-run .technical-value')), 'first_run_review: public run ID positive control');
      assert.equal(await b.evaluate(() => document.getElementById('review-prose').innerText), 'The run-time limit caused the failure. This is a run-of-the-mill timeout.', 'first_run_review: ordinary evidence words must stay exact');
      assert.ok(await b.evaluate(() => !document.getElementById('review-run').innerText.includes('run-9001')), 'first_run_review: public run ID must stay collapsed');
      await b.evaluate(() => document.getElementById('guided-technical').click());
      assert.ok(await b.evaluate(() => document.getElementById('review-run').innerText.includes('run-9001')), 'first_run_review: exact public run ID must be revealed');
    } else if (check === 'investigation') {
      await b.evaluate(() => {
        document.querySelector('[data-first-run-go="2"]').click();
        globalThis.__s47RenderInvestigations({investigations: [{id: 'inv-S47-history', authored_by: 'learner', source_run_id: 'run-9199', source_request_ordinal: 1,
          cause: 'A run-time limit', falsifier: 'A complete timely answer', public_test: 'Keep both customer tasks.'}]});
        const control = document.createElement('p'); control.id = 'investigation-control'; control.dataset.runId = 'run-9299'; control.textContent = 'run-9299';
        document.getElementById('guided-panel-2').append(control);
      });
      assert.ok(await b.until(() => document.querySelector('#investigation-control .technical-value')), 'first_run_review: investigation scanner positive control');
      assert.ok(await b.evaluate(() => !document.getElementById('investigation-list').innerText.includes('run-9199')), 'first_run_review: historical investigation ID must stay collapsed');
      assert.ok(await b.evaluate(() => document.getElementById('investigation-list').innerText.includes('A run-time limit')), 'first_run_review: investigation cause must stay exact');
      await b.evaluate(() => document.getElementById('guided-technical').click());
      assert.ok(await b.evaluate(() => document.getElementById('investigation-list').innerText.includes('run-9199')), 'first_run_review: historical investigation ID must be revealed');
    } else if (check === 'history') {
      await b.evaluate(attributes => {
        document.querySelector('[data-first-run-go="1"]').click();
        for (const [index, attribute] of ['data-run-id', ...attributes].entries()) {
          const p = document.createElement('p'); p.id = 'review-history-' + index;
          p.setAttribute(attribute, 'run-' + (9100 + index)); p.textContent = 'Historical record run-' + (9100 + index);
          document.getElementById('guided-panel-1').append(p);
        }
      }, HISTORICAL_RUN_ATTRIBUTES);
      assert.ok(await b.until(() => document.querySelector('#review-history-0 .technical-value')), 'first_run_review: history scanner positive control');
      for (const [index, attribute] of HISTORICAL_RUN_ATTRIBUTES.entries()) {
        assert.ok(await b.evaluate(index => !document.getElementById('review-history-' + (index + 1)).innerText.includes('run-' + (9101 + index)), index), 'first_run_review: historical identity must stay collapsed: ' + attribute);
      }
      await b.evaluate(() => document.getElementById('guided-technical').click());
      for (const index of HISTORICAL_RUN_ATTRIBUTES.keys()) assert.ok(await b.evaluate(index => document.getElementById('review-history-' + (index + 1)).innerText.includes('run-' + (9101 + index)), index), 'first_run_review: exact historical identity must be revealed');
    } else if (check === 'refresh') {
      await b.evaluate(() => {
        document.querySelector('[data-first-run-go="5"]').click();
        const original = window.fetch;
        window.__reviewRestore = () => { window.fetch = original; };
        window.fetch = async (...args) => {
          if (args[0] === '/api/runtime') await new Promise(resolve => { window.__reviewRelease = resolve; });
          return original(...args);
        };
        document.getElementById('refresh').click();
      });
      assert.ok(await b.until(() => document.body.dataset.loadState === 'loading' && typeof window.__reviewRelease === 'function'), 'first_run_review: loading control did not run');
      assert.equal(await b.evaluate(() => document.getElementById('guided-view').dataset.panel), '5', 'first_run_review: loading must preserve the browsed panel');
      await b.evaluate(() => window.__reviewRelease());
      assert.ok(await b.until(() => ['ready', 'empty'].includes(document.body.dataset.loadState)), 'first_run_review: restored refresh did not settle');
      assert.equal(await b.evaluate(() => document.getElementById('guided-view').dataset.panel), '5', 'first_run_review: same-shift refresh must preserve browsing');
      await b.evaluate(() => {
        window.__reviewRestore();
        const select = document.getElementById('workplace-board'); select.value = 'northline'; select.dispatchEvent(new Event('change'));
      });
      assert.ok(await b.until(() => document.body.dataset.board === 'northline' && ['ready', 'empty'].includes(document.body.dataset.loadState)), 'first_run_review: new board did not settle');
      assert.equal(await b.evaluate(() => document.getElementById('guided-view').dataset.panel), '1', 'first_run_review: a different board must reset browsing');
    } else throw Error('Unknown review check: ' + check);
    assert.equal(b.commands.length, before, 'first_run_review: inspection must send no command');
    assert.deepEqual(b.exceptions, []);
    b.assertFaultServed();
    await writeFile(out + '/review.json', JSON.stringify({check, slug, result: 'PASS', commands: b.commands.length - before}));
    console.log('PASS', check, slug);
  } finally { await b.close(); }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await runFirstRunRegression(...process.argv.slice(2));
