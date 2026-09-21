import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { once } from 'node:events';

// Fault-injection mode: with SHIFTWORK_FAULT set, the harness serves a mutated
// in-memory copy of the production app.js to the browser and then requires this
// run to fail at the named rendered-evidence assertion. The repository file is
// never modified. Each needle must match exactly one production behavior.
const FAULTS = {
  answer: {
    needle: "output.customer_answer?.display_text ?? 'No validated customer answer. Inspect the captured bytes below.'",
    replacement: "'REVIEW_WRONG_CUSTOMER_ANSWER'",
    expect: 'Rendered customer answer does not match the executed output',
  },
  record: {
    needle: 'const publicRecord = output.public_shop_record;',
    replacement: "const publicRecord = { ...output.public_shop_record, value: 'REVIEW_WRONG_PUBLIC_VALUE' };",
    expect: 'Rendered public record value does not match',
  },
  verdict: {
    needle: 'humanize(check.verdict)',
    replacement: "'pass'",
    expect: 'Rendered check row does not match result',
  },
  event: {
    needle: 'humanize(event.event_type)',
    replacement: "'sale completed'",
    expect: 'Rendered event row does not match event',
  },
  stationFocus: {
    needle: "  panel.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });",
    replacement: '  void panel;',
    expect: 'Narrow station selection does not bring the panel into reach',
  },
  incidentFocus: {
    needle: "      if (target) target.focus(); else $('station-panel').focus();",
    replacement: '      void target;',
    expect: 'Incident navigation does not move focus into the selected request',
  },
};

const url = process.argv[2] ?? 'http://127.0.0.1:8009';
assert.ok(['127.0.0.1', 'localhost'].includes(new URL(url).hostname), 'Browser checks target a local preview only');
const fault = process.env.SHIFTWORK_FAULT ?? null;
if (fault) {
  assert.ok(FAULTS[fault], `Unknown fault: ${fault}`);
  assert.ok(!process.argv.includes('--exercise-run'), 'Fault runs never consume a preview attempt');
}
const browser = process.env.CHROME_PATH ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const profile = await mkdtemp(path.join(tmpdir(), 'shiftwork-browser-'));
const artifacts = path.resolve(fault ? `artifacts/slice9-faults/${fault}` : 'artifacts/slice9');
await mkdir(artifacts, { recursive: true });
const child = spawn(browser, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
const endpoint = await new Promise((resolve, reject) => {
  let stderr = '';
  const timeout = setTimeout(() => reject(new Error('Chrome did not expose its local DevTools endpoint')), 15000);
  child.once('error', reject);
  child.stderr.on('data', data => { stderr += data; const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/); if (match) { clearTimeout(timeout); resolve(match[1]); } });
  child.once('exit', code => { clearTimeout(timeout); reject(new Error(`Chrome exited ${code}`)); });
});
const socket = new WebSocket(endpoint);
await once(socket, 'open');
let sequence = 0;
let session;
const pending = new Map();
const exceptions = [];
socket.addEventListener('message', ({ data }) => {
  const message = JSON.parse(data);
  if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails);
  if (message.id) {
    const item = pending.get(message.id);
    if (!item) return;
    pending.delete(message.id); clearTimeout(item.timer);
    if (message.error) item.reject(new Error(JSON.stringify(message.error))); else item.resolve(message.result);
  }
});
function send(method, params = {}, useSession = true) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, 20000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params, ...(useSession && session ? { sessionId: session } : {}) }));
  });
}
async function evaluate(fn, ...args) {
  const result = await send('Runtime.evaluate', { expression: `(${fn.toString()})(...${JSON.stringify(args)})`, awaitPromise: true, returnByValue: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text);
  return result.result.value;
}
async function ready(expected = 'ready') {
  await evaluate(async expected => {
    const deadline = Date.now() + 10000;
    while (document.body?.dataset.loadState !== expected) {
      if (Date.now() > deadline) throw new Error(`Expected ${expected}, got ${document.body?.dataset.loadState}: ${document.getElementById('load-message')?.textContent}`);
      await new Promise(resolve => setTimeout(resolve, 25));
    }
  }, expected);
}
async function screenshot(name) {
  const { data } = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  await writeFile(path.join(artifacts, `${name}.png`), Buffer.from(data, 'base64'));
}
async function labels() {
  return evaluate(() => {
    const regions = [...document.querySelectorAll('[data-synthetic-region]')].filter(node => node.getClientRects().length);
    const check = () => {
      for (const region of regions) {
        const label = [...region.querySelectorAll('.synthetic')].find(node => node.closest('[data-synthetic-region]') === region);
        if (!label || label.textContent !== 'Synthetic scenario' || !label.getClientRects().length || getComputedStyle(label).visibility === 'hidden') throw new Error(`Missing rendered label: ${region.dataset.syntheticRegion}`);
      }
    };
    check();
    for (const region of regions) {
      const label = region.querySelector('.synthetic');
      const next = label.nextSibling, parent = label.parentNode;
      label.remove();
      let caught = false;
      try { check(); } catch { caught = true; }
      parent.insertBefore(label, next);
      if (!caught) throw new Error('Label-removal mutation survived');
    }
    return regions.map(node => node.dataset.syntheticRegion);
  });
}

let faultOutcome = null;
try {
  const { targetId } = await send('Target.createTarget', { url: 'about:blank' }, false);
  session = (await send('Target.attachToTarget', { targetId, flatten: true }, false)).sessionId;
  await send('Page.enable'); await send('Runtime.enable');
  if (fault) {
    const source = (await readFile(new URL('../../shiftwork/client/app.js', import.meta.url), 'utf8')).replaceAll('\r\n', '\n');
    const { needle, replacement } = FAULTS[fault];
    assert.equal(source.split(needle).length - 1, 1, `Fault ${fault} must match exactly one production behavior`);
    const faulty = source.replace(needle, replacement);
    socket.addEventListener('message', ({ data }) => {
      const message = JSON.parse(data);
      if (message.method !== 'Fetch.requestPaused') return;
      send('Fetch.fulfillRequest', {
        requestId: message.params.requestId, responseCode: 200,
        responseHeaders: [{ name: 'Content-Type', value: 'text/javascript' }],
        body: Buffer.from(faulty).toString('base64'),
      }).catch(error => { console.error(error); });
    });
    await send('Fetch.enable', { patterns: [{ urlPattern: '*/app.js', requestStage: 'Request' }] });
  }
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url });
  await ready();
  assert.equal(await evaluate(() => document.querySelectorAll('[data-station]').length), 7);
  const matrix = [];
  for (const width of [1280, 640, 390]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
    await evaluate(() => { document.querySelector('[data-station="service"]').click(); window.scrollTo(0, 0); });
    const boardLabels = await labels();
    assert.deepEqual(boardLabels, ['board', 'incidents', 'ledger']);
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${width}px page overflows`);
    await screenshot(`board-${width}`);
    await evaluate(() => document.querySelector('[data-station="customers"]').click());
    const result = await evaluate(async () => {
      const humanize = value => value.toLowerCase().replaceAll('_', ' ');
      const board = await (await fetch('/api/engagements/bookshop/board')).json();
      const run = board.latest_run;
      const [outputs, checks, ledger] = await Promise.all([`/api/runs/${run.id}/outputs`, `/api/runs/${run.id}/checks`, '/api/engagements/bookshop/ledger'].map(async path => (await fetch(path)).json()));
      const buttons = [...document.querySelectorAll('.customer-button')];
      if (buttons.length < 2 || buttons.length !== outputs.length) throw new Error('Preview needs two actual executed customers');
      for (const output of [...outputs].reverse()) {
        buttons.find(button => button.dataset.outputId === output.id).click();
        const panel = document.getElementById('selected-evidence');
        const verify = () => {
          if (panel.dataset.runId !== output.run_id || Number(panel.dataset.requestOrdinal) !== output.request_ordinal) throw new Error('Customer identity mismatch');
          if (panel.querySelector('.request-quote').textContent !== output.request_text) throw new Error('Wrong request text');
          if (panel.querySelector('[data-body-base64]').dataset.bodyBase64 !== output.body_base64) throw new Error('Body byte mismatch');
          // Substantive rendered values, each against the independently fetched API payload.
          const steps = [...panel.querySelectorAll('.evidence-step')];
          const answer = steps[1]?.querySelector('.evidence-text');
          const expectedAnswer = output.customer_answer ? output.customer_answer.display_text : 'No validated customer answer. Inspect the captured bytes below.';
          if (answer?.textContent !== expectedAnswer) throw new Error(`Rendered customer answer does not match the executed output: ${answer?.textContent}`);
          const record = output.public_shop_record;
          const recordStep = steps[2];
          if (record) {
            const title = [record.title, record.edition].filter(Boolean).join(' · ') || record.record_id;
            if (recordStep.querySelector('.evidence-text')?.textContent !== title) throw new Error(`Rendered public record title does not match: ${recordStep.querySelector('.evidence-text')?.textContent}`);
            const value = typeof record.value === 'string' ? humanize(record.value) : JSON.stringify(record.value);
            const expectedValue = `${humanize(record.kind)}: ${value}`;
            if (recordStep.querySelector('.public-value')?.textContent !== expectedValue) throw new Error(`Rendered public record value does not match: ${recordStep.querySelector('.public-value')?.textContent}`);
            if (!recordStep.textContent.includes(`Record age ${record.record_age_ms} ms`)) throw new Error('Rendered public record age does not match');
          } else if (!recordStep.textContent.includes('No public comparison record')) throw new Error('Rendered no-record state is missing');
          const linked = checks.filter(c => c.run_id === output.run_id && c.observed_ref === output.id);
          const ids = new Set(linked.map(c => c.id));
          const events = ledger.events.filter(e => e.derivation?.run_id === output.run_id && e.derivation?.request_ordinal === output.request_ordinal && ids.has(e.derivation.check_id));
          if (panel.querySelectorAll('[data-check-id]').length !== linked.length || panel.querySelectorAll('[data-event-seq]').length !== events.length) throw new Error('Incomplete evidence links');
          for (const check of linked) {
            const expected = `${humanize(check.verdict)}${check.reason_code ? ` · ${check.reason_code}` : ''}`;
            const row = panel.querySelector(`[data-check-id="${check.id}"]`);
            if (!row || row.querySelector('strong')?.textContent !== expected) throw new Error(`Rendered check row does not match result ${check.id}: ${row?.querySelector('strong')?.textContent} is not ${expected}`);
          }
          for (const event of events) {
            const row = panel.querySelector(`[data-event-seq="${event.seq}"]`);
            if (!row) throw new Error(`Missing rendered event ${event.seq}`);
            if (row.querySelector('strong')?.textContent !== humanize(event.event_type)) throw new Error(`Rendered event row does not match event ${event.seq}: ${row.querySelector('strong')?.textContent}`);
            if (!row.querySelector('small')?.textContent.includes(`result ${event.derivation.check_id}`)) throw new Error(`Rendered event row is missing its result link for event ${event.seq}`);
          }
          if (output.public_shop_snapshot_hash && !panel.textContent.includes(output.public_shop_snapshot_hash)) throw new Error('Provenance missing');
        };
        verify();
        const originalOrdinal = panel.dataset.requestOrdinal;
        panel.dataset.requestOrdinal = '999';
        let caught = false; try { verify(); } catch { caught = true; }
        panel.dataset.requestOrdinal = originalOrdinal;
        if (!caught) throw new Error('Ordinal mutation survived');
        const bytes = new Uint8Array(await (await fetch(panel.querySelector('.download').href)).arrayBuffer());
        if (btoa(Array.from(bytes, byte => String.fromCharCode(byte)).join('')) !== output.body_base64) throw new Error('Downloaded bytes changed');
      }
      return { outputs: outputs.length, run: run.id };
    });
    const customerLabels = await labels();
    assert.deepEqual(customerLabels, ['board', 'run', 'event']);
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${width}px evidence overflows`);
    await screenshot(`customers-${width}`);
    matrix.push({ width, ...result, labels: [...boardLabels, ...customerLabels] });
  }
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  const navigationErrors = await evaluate(async () => {
    const errors = [];
    const tick = () => new Promise(resolve => setTimeout(resolve, 20));
    document.querySelector('[data-view="customers"]').click(); await tick();
    document.querySelector('[data-station="service"]').click();
    document.querySelector('[data-view="customers"]').click(); await tick();
    if (document.getElementById('customer-view').hidden) errors.push('journey link does not reopen after station navigation');
    document.querySelector('[data-station="customers"]').click();
    document.querySelector('.skip-link').click(); await tick();
    if (document.getElementById('customer-view').hidden) errors.push('skip link changes selected view');
    return errors;
  });
  await evaluate(async () => { document.querySelector('[data-view="away"]').click(); await new Promise(resolve => setTimeout(resolve, 20)); document.getElementById('refresh').click(); });
  await ready();
  if (!(await evaluate(() => !document.getElementById('deferred-view').hidden && document.getElementById('panel-title').textContent === 'Northline workshop'))) navigationErrors.push('refresh loses away placeholder');
  await evaluate(() => document.querySelector('[data-station="customers"]').click());
  await evaluate(() => document.querySelectorAll('.customer-button')[1].focus());
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r', unmodifiedText: '\r' });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  if (!(await evaluate(() => document.activeElement.dataset.outputId === document.querySelectorAll('.customer-button')[1].dataset.outputId))) navigationErrors.push('customer keyboard selection loses focus');
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  if (!(await evaluate(() => document.activeElement.tagName === 'SUMMARY'))) navigationErrors.push('Tab does not continue from the selected customer into its captured evidence');
  // Narrow layouts: a native touch on a station control must bring that station's
  // panel into reach (focus plus scroll), not leave it below the viewport.
  await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  let narrowReach = 'pass';
  for (const width of [640, 390]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
    const setup = await evaluate(async () => {
      window.scrollTo(0, 0);
      await new Promise(resolve => setTimeout(resolve, 250));
      window.scrollTo(0, 0);
      const station = document.querySelector('[data-station="customers"]');
      const rect = station.getBoundingClientRect();
      return { x: Math.round(rect.left + rect.width / 2), y: Math.round(rect.top + rect.height / 2), top: Math.round(rect.top), bottom: Math.round(rect.bottom), viewport: innerHeight };
    });
    if (setup.top < 0 || setup.bottom > setup.viewport) { narrowReach = `station control is not tappable at ${width}px (${setup.top}-${setup.bottom} of ${setup.viewport})`; break; }
    await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: setup.x, y: setup.y }] });
    await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    const reach = await evaluate(async () => {
      const panel = document.getElementById('station-panel');
      const deadline = Date.now() + 5000;
      while (Date.now() < deadline) {
        if (document.activeElement === panel && panel.getBoundingClientRect().top < innerHeight) return 'pass';
        await new Promise(resolve => setTimeout(resolve, 25));
      }
      return `active=${document.activeElement?.id || document.activeElement?.tagName} panelTop=${Math.round(panel.getBoundingClientRect().top)} viewport=${innerHeight}`;
    });
    if (reach !== 'pass') { narrowReach = `${reach} at ${width}px`; break; }
  }
  await send('Emulation.setTouchEmulationEnabled', { enabled: false });
  if (narrowReach !== 'pass') navigationErrors.push(`Narrow station selection does not bring the panel into reach: ${narrowReach}`);
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  // Following an incident must move keyboard focus into the selected request,
  // not drop it on BODY while the board list is rebuilt.
  const incidentArmed = await evaluate(async () => {
    document.querySelector('[data-station="service"]').click();
    const board = await (await fetch('/api/engagements/bookshop/board')).json();
    if (!board.incidents.length) return 'no incident in the preview';
    const row = document.querySelector('.incident-row');
    if (!row) return 'no incident row rendered';
    row.focus();
    if (document.activeElement !== row) return 'incident row is not focusable';
    return 'armed';
  });
  if (incidentArmed === 'armed') {
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r', unmodifiedText: '\r' });
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    const focus = await evaluate(async () => {
      const board = await (await fetch('/api/engagements/bookshop/board')).json();
      const incident = board.incidents[0];
      const deadline = Date.now() + 10000;
      while (Date.now() < deadline) {
        if (document.activeElement?.dataset?.outputId === incident.failing_output_ref) return 'pass';
        await new Promise(resolve => setTimeout(resolve, 25));
      }
      return `focus ended on ${document.activeElement?.tagName ?? 'nothing'} instead of ${incident.failing_output_ref}`;
    });
    if (focus !== 'pass') navigationErrors.push(`Incident navigation does not move focus into the selected request: ${focus}`);
  } else navigationErrors.push(`Incident focus check could not arm: ${incidentArmed}`);
  await evaluate(() => {
    document.querySelector('[data-station="service"]').click();
    window.__raceFetch = window.fetch;
    let held = false;
    window.__oldFinished = new Promise(resolve => { window.__finishOld = resolve; });
    window.fetch = async (...args) => {
      if (!held && String(args[0]).endsWith('/board')) {
        held = true;
        await new Promise(resolve => { window.__releaseIncident = resolve; });
      }
      const response = await window.__raceFetch(...args);
      if (String(args[0]).endsWith('/runs/run-0001/checks')) {
        await response.clone().json(); setTimeout(window.__finishOld, 30);
      }
      return response;
    };
    document.querySelector('.incident-row').click();
  });
  await evaluate(() => document.getElementById('refresh').click());
  await ready();
  await evaluate(async () => { document.querySelector('[data-station="service"]').click(); window.__releaseIncident(); await window.__oldFinished; window.fetch = window.__raceFetch; });
  if (!(await evaluate(() => !document.getElementById('board-view').hidden))) navigationErrors.push('obsolete incident callback overrides newer navigation');
  assert.deepEqual(navigationErrors, []);
  await evaluate(() => document.querySelector('[data-station="evaluator"]').focus());
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r', unmodifiedText: '\r' });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
  assert.equal(await evaluate(() => document.querySelector('[data-station="evaluator"]').getAttribute('aria-pressed')), 'true');
  assert.equal(await evaluate(() => getComputedStyle(document.activeElement).outlineStyle), 'solid');
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  assert.equal(await evaluate(() => document.activeElement.dataset.station), 'ledger');
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  await evaluate(() => document.querySelector('[data-station="customers"]').click());
  assert.equal(await evaluate(() => getComputedStyle(document.querySelector('.evidence-path circle')).animationName), 'none');
  assert.equal(await evaluate(() => getComputedStyle(document.querySelector('.evidence-path')).opacity), '0.85');
  await screenshot('reduced-motion');

  await evaluate(() => {
    window.__fetch = window.fetch;
    window.fetch = (...args) => new Promise(resolve => { window.__release = () => resolve(window.__fetch(...args)); });
    document.getElementById('refresh').click();
  });
  await ready('loading');
  assert.equal(await evaluate(() => document.getElementById('selected-evidence').hasAttribute('data-run-id')), false);
  await labels(); await screenshot('loading');
  await evaluate(() => { window.fetch = window.__fetch; window.__release(); });
  await ready();
  await evaluate(() => { window.fetch = async () => { throw new Error('Offline test: refresh to retry.'); }; document.getElementById('refresh').click(); });
  await ready('error');
  assert.equal(await evaluate(() => document.querySelectorAll('[data-body-base64], .customer-button').length), 0);
  await labels(); await screenshot('error');
  await evaluate(() => { window.fetch = window.__fetch; document.getElementById('refresh').click(); });
  await ready();
  await evaluate(() => {
    window.fetch = async (...args) => {
      const response = await window.__fetch(...args);
      if (!String(args[0]).endsWith('/board')) return response;
      const board = await response.json();
      Object.assign(board, { latest_shift: null, latest_version: null, latest_run: null, artifact_files: [], requests_run: 0, attempts_used: 0, attempts_remaining: 3, incidents: [], total_incidents: 0, unresolved_limits: [], ledger_event_count: 0, ledger_totals: {} });
      return new Response(JSON.stringify(board), { headers: { 'Content-Type': 'application/json' } });
    };
    document.querySelector('[data-station="service"]').click(); document.getElementById('refresh').click();
  });
  await ready('empty');
  await labels();
  assert.equal(await evaluate(() => document.getElementById('run-shift').disabled), true);
  assert.equal(await evaluate(() => document.getElementById('open-shift').disabled), false);
  assert.ok(await evaluate(() => document.getElementById('incident-list').textContent.includes('No unresolved incidents')));
  await evaluate(() => document.querySelector('[data-station="repair"]').click());
  assert.notEqual(await evaluate(() => document.querySelector('[data-station="repair"]').getAttribute('aria-pressed')), 'true', 'Repair cannot activate without an actual incident');
  await screenshot('empty');
  await evaluate(() => { window.fetch = window.__fetch; document.getElementById('refresh').click(); });
  await ready();
  await evaluate(() => {
    window.fetch = async (...args) => {
      const response = await window.__fetch(...args);
      if (!String(args[0]).endsWith('/outputs')) return response;
      const outputs = await response.json();
      return new Response(JSON.stringify(outputs.map(output => ({ ...output, request_text: '<img src=x onerror="window.__injected=true">', body_base64: '/wA=', customer_answer: null, public_shop_record: null, public_shop_record_ref: null, public_shop_snapshot_hash: null }))), { headers: { 'Content-Type': 'application/json' } });
    };
    document.querySelector('[data-station="customers"]').click(); document.getElementById('refresh').click();
  });
  await ready();
  const malformed = await evaluate(async () => {
    const panel = document.getElementById('selected-evidence');
    const bytes = new Uint8Array(await (await fetch(panel.querySelector('.download').href)).arrayBuffer());
    return { literal: panel.querySelector('.request-quote').textContent, image: !!panel.querySelector('img'), injected: !!window.__injected, bytes: [...bytes], noRecord: panel.textContent.includes('No public comparison record'), rawFallback: panel.textContent.includes('not valid UTF-8'), sealedDigest: panel.textContent.includes('sealed:') };
  });
  assert.deepEqual(malformed, { literal: '<img src=x onerror="window.__injected=true">', image: false, injected: false, bytes: [255, 0], noRecord: true, rawFallback: true, sealedDigest: false });
  await evaluate(() => { window.fetch = window.__fetch; document.getElementById('refresh').click(); });
  await ready();
  if (process.argv.includes('--exercise-run')) {
    const beforeRun = await evaluate(async () => (await (await fetch('/api/engagements/bookshop/board')).json()).latest_run.id);
    assert.equal(await evaluate(() => document.getElementById('metric-attempts').textContent), '1', 'Run-button proof needs a fresh preview with one remaining attempt');
    assert.equal(await evaluate(() => document.getElementById('run-shift').disabled), false);
    await evaluate(() => { document.querySelector('[data-station="service"]').click(); document.getElementById('run-shift').click(); });
    await evaluate(async previousRun => {
      const deadline = Date.now() + 15000;
      while (document.getElementById('metric-attempts').textContent !== '0' || !document.getElementById('run-state').textContent.includes('FINALIZED') || document.getElementById('run-state').textContent.includes(previousRun)) {
        if (Date.now() > deadline) throw new Error('Run button did not reach finalized exhausted-budget state');
        await new Promise(resolve => setTimeout(resolve, 30));
      }
    }, beforeRun);
    assert.equal(await evaluate(() => document.getElementById('run-shift').disabled), true);
    assert.equal(await evaluate(() => document.querySelectorAll('.customer-button').length), 3);
  }
  assert.equal(exceptions.length, 0, JSON.stringify(exceptions));
  const report = { matrix, navigationAndStaleIncident: 'PASS', keyboard: 'PASS (evaluator and customer Enter/Tab)', reducedMotion: 'PASS', states: ['loading', 'error', 'empty', 'no incidents', 'malformed body', 'no public record'], repairWithoutIncident: 'blocked', literalUntrustedText: 'PASS', realRunButton: process.argv.includes('--exercise-run') ? 'PASS' : 'not exercised in this run', labelRemovalMutations: 'caught in every visible region', ordinalMutation: 'caught', renderedEvidence: 'exact answer, public record, verdict and event text against the API payload', narrowStationReach: 'native touch brings the panel into reach at 640/390', incidentNavigationFocus: 'keyboard activation focuses the selected request', downloadedBytes: 'exact', uncaughtExceptions: exceptions.length };
  await writeFile(path.join(artifacts, 'browser-report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  if (!fault) throw error;
  const message = String(error?.message ?? error);
  faultOutcome = { message, caught: message.includes(FAULTS[fault].expect) };
} finally {
  await send('Browser.close', {}, false).catch(() => {});
  socket.close();
  if (child.exitCode === null) await Promise.race([once(child, 'exit'), new Promise(resolve => setTimeout(resolve, 2000))]);
  if (child.exitCode === null) child.kill();
  await rm(profile, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 }).catch(() => {});
}
if (fault) {
  if (faultOutcome?.caught) console.log(`FAULT_CAUGHT ${fault}: ${faultOutcome.message}`);
  else console.error(`FAULT_${faultOutcome ? 'WRONG_FAILURE' : 'SURVIVED'} ${fault}: ${faultOutcome?.message ?? 'every assertion passed with the fault applied'}`);
  process.exitCode = faultOutcome?.caught ? 0 : 1;
}
