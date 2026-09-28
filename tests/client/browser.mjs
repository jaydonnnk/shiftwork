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
  eligibility: {
    needle: "experiment.eligible ? 'Eligible' : 'Not eligible · this diagnostic cannot qualify a version'",
    replacement: "'REVIEW_WRONG_ELIGIBILITY'",
    expect: 'does not state that the diagnostic cannot qualify a version',
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
  candidateFreeze: {
    needle: 'state.candidates[label] = version;',
    replacement: 'void version;',
    expect: 'Timed out waiting for candidate A freeze',
  },
  slotOrdinalText: {
    needle: 'request ${result.request_ordinal}',
    replacement: 'request 99',
    expect: 'does not display the request ordinal',
  },
  slotOrdinalKey: {
    needle: 'item.dataset.requestOrdinal = String(result.request_ordinal);',
    replacement: "item.dataset.requestOrdinal = String(result.request_ordinal) + '9';",
    expect: 'row with the payload verdict',
  },
  slotProtectedCount: {
    needle: '+ ${trial.protected_request_count} protected step',
    replacement: '+ 7 protected step',
    expect: 'renders the wrong protected step count',
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
// Must outlive the longest in-page polling deadline (60s) or a real page timeout surfaces as this opaque transport error.
const CDP_TIMEOUT_MS = 90000;
function send(method, params = {}, useSession = true) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, CDP_TIMEOUT_MS);
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

// Page-side verification: the customer station's rendered evidence must equal the
// API payload for the run's exact captures. This runs inside the browser through
// evaluate(), so the matrix rows and the failing incident run share one body.
async function verifyRenderedCustomerEvidence(runId, minimumOutputs) {
  const humanize = value => value.toLowerCase().replaceAll('_', ' ');
  const [run, outputs, checks, ledger] = await Promise.all([`/api/runs/${runId}`, `/api/runs/${runId}/outputs`, `/api/runs/${runId}/checks`, '/api/engagements/bookshop/ledger'].map(async path => (await fetch(path)).json()));
  const buttons = [...document.querySelectorAll('.customer-button')];
  if (buttons.length < minimumOutputs || buttons.length !== outputs.length) throw new Error(`Preview needs ${minimumOutputs} actual executed customers on ${runId}, saw ${buttons.length} buttons for ${outputs.length} captured outputs`);
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
  assert.equal(await evaluate(() => document.querySelectorAll('[data-station]').length), 9);
  const matrix = [];
  for (const width of [1280, 640, 390]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
    await evaluate(() => { document.querySelector('[data-station="service"]').click(); window.scrollTo(0, 0); });
    const boardLabels = await labels();
    assert.deepEqual(boardLabels, ['board', 'incidents', 'ledger']);
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${width}px page overflows`);
    await screenshot(`board-${width}`);
    await evaluate(() => document.querySelector('[data-station="customers"]').click());
    const latestRunId = await evaluate(async () => (await (await fetch('/api/engagements/bookshop/board')).json()).latest_run.id);
    const result = await evaluate(verifyRenderedCustomerEvidence, latestRunId, 2);
    const customerLabels = await labels();
    assert.deepEqual(customerLabels, ['board', 'run', 'event']);
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${width}px evidence overflows`);
    await screenshot(`customers-${width}`);
    matrix.push({ width, ...result, labels: [...boardLabels, ...customerLabels] });
  }
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
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
    // The incident's opening run is the failing evidence the customer station can
    // load: its rendered checks and ledger events must equal the API payload too.
    const incidentRunId = await evaluate(async () => (await (await fetch('/api/engagements/bookshop/board')).json()).incidents[0].opening_run_id);
    await evaluate(verifyRenderedCustomerEvidence, incidentRunId, 1);
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
  await evaluate(() => document.querySelector('[data-station="investigate"]').click());
  const investigateView = await evaluate(async assistDemo => {
    const humanize = value => value.toLowerCase().replaceAll('_', ' ');
    const wait = async (label, condition) => {
      const deadline = Date.now() + 15000;
      while (Date.now() < deadline) {
        if (condition()) return;
        await new Promise(resolve => setTimeout(resolve, 25));
      }
      throw new Error(`Timed out waiting for ${label}: ${document.getElementById('investigate-error')?.textContent ?? ''}`);
    };
    const panel = document.getElementById('investigate-view');
    if (panel.hidden) throw new Error('Investigate station does not open its own panel');
    if (document.querySelector('[data-station="investigate"]').getAttribute('aria-pressed') !== 'true') throw new Error('Investigate hotspot is not marked pressed');
    const board = await (await fetch('/api/engagements/bookshop/board')).json();
    const shiftId = board.latest_shift.id;
    const stationUrl = `/api/shifts/${encodeURIComponent(shiftId)}/investigations`;
    const station = await (await fetch(stationUrl)).json();
    const steps = [...panel.querySelectorAll('#orientation-list li')].map(node => node.textContent);
    if (JSON.stringify(steps) !== JSON.stringify(station.orientation.steps)) throw new Error(`Orientation copy does not match the API payload: ${JSON.stringify(steps)}`);
    const checkDenial = async investigationId => {
      const denial = document.getElementById('assist-denial');
      denial.textContent = '';
      document.getElementById('request-assist').click();
      await wait('the denial detail', () => denial.textContent !== '');
      const response = await fetch(`/api/shifts/${shiftId}/assist`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ investigation_id: investigationId, role: 'HINT', client_request_id: `harness-${Date.now()}` }) });
      const expected = await response.json();
      if (response.status !== 409 || denial.textContent !== expected.detail) throw new Error(`Rendered denial is not the API detail: ${denial.textContent} is not ${expected.detail}`);
      return expected.detail;
    };
    const denials = {};
    if (!station.investigations.length) denials.beforeEntry = await checkDenial(null);
    const stamp = Date.now();
    for (const [id, value] of [['cause-input', `harness cause ${stamp}`], ['falsifier-input', `harness falsifier ${stamp}`], ['public-test-input', `harness public test ${stamp}`]]) document.getElementById(id).value = value;
    const requestedOrdinal = Number(document.getElementById('source-ordinal').value);
    document.getElementById('append-investigation').click();
    await wait('the entry to be recorded', () => document.querySelectorAll('#investigation-list [data-investigation-id]').length === station.investigations.length + 1);
    const recorded = await (await fetch(stationUrl)).json();
    const latest = recorded.investigations[recorded.investigations.length - 1];
    const row = panel.querySelector(`[data-investigation-id="${latest.id}"]`);
    if (!row || row.dataset.authoredBy !== 'learner') throw new Error(`Recorded entry ${latest.id} is not rendered as the learner's`);
    for (const [label, value] of [['Cause', latest.cause], ['Falsifier', latest.falsifier], ['Public test', latest.public_test]]) {
      const line = [...row.querySelectorAll('.contract-line')].find(node => node.querySelector('span')?.textContent === label);
      if (line?.querySelector('strong')?.textContent !== value) throw new Error(`Rendered ${label} does not match entry ${latest.id}`);
    }
    if (latest.revision_of_id) {
      if (row.dataset.revisionOf !== latest.revision_of_id) throw new Error('Revision linkage is not rendered');
      if (!panel.querySelector(`[data-investigation-id="${latest.revision_of_id}"]`)) throw new Error('The revised entry is not retained');
    } else if (latest.source_request_ordinal !== requestedOrdinal) {
      throw new Error(`Recorded entry cites request ${latest.source_request_ordinal} instead of ${requestedOrdinal}`);
    }
    if (assistDemo) {
      document.getElementById('assist-role').value = 'HINT';
      document.getElementById('assist-message').value = 'What public evidence should I check?';
      document.getElementById('request-assist').click();
      await wait('recorded hint', () => document.querySelectorAll('#assist-events [data-assist-event-id]').length === 1);
      const hint = document.querySelector('#assist-events [data-assist-event-id]');
      if (!hint.textContent.includes('recorded-assist-double') || !hint.textContent.includes('collection')) throw new Error('Recorded hint is not visibly attributed');
      document.getElementById('assist-role').value = 'PATCH_PROPOSAL';
      document.getElementById('request-assist').click();
      await wait('recorded patch proposal', () => document.querySelectorAll('#assist-events [data-assist-event-id]').length === 2);
      const patch = document.querySelectorAll('#assist-events [data-assist-event-id]')[1];
      if (!patch.textContent.includes('Proposal for learner review only') || !patch.textContent.includes('not changed code')) throw new Error('Patch proposal lacks its attribution and no-edit warning');
      patch.querySelector('button').click();
      await wait('accepted help attribution', () => document.querySelectorAll('#assist-events [data-assist-event-id]')[1]?.textContent.includes('Accepted as help attribution'));
      const assisted = await (await fetch(stationUrl)).json();
      if (assisted.assist_used !== 2 || assisted.assist_events[1].accepted !== true) throw new Error('UI attribution did not round trip to the assist event');
      denials.withEntry = 'recorded assist, 2 of 3 calls used';
    } else denials.withEntry = await checkDenial(latest.id);
    return { shift: shiftId, entries: recorded.investigations.length, revision: Boolean(latest.revision_of_id), denials };
  }, process.argv.includes('--assist-demo'));
  const investigateLabels = await labels();
  assert.deepEqual(investigateLabels, ['board', 'source', 'diagnostic']);
  for (const journey of ['return', 'away']) {
    await evaluate(journey => document.querySelector(`[data-view="${journey}"]`).click(), journey);
    assert.equal(await evaluate(() => document.getElementById('investigate-view').hidden), true,
      `${journey} must hide the live Investigate form and diagnostic result`);
    await evaluate(() => document.querySelector('[data-station="investigate"]').click());
    assert.equal(await evaluate(() => document.getElementById('investigate-view').hidden), false,
      'Investigate must reopen after a journey placeholder');
  }
  assert.equal(await evaluate(() => document.documentElement.scrollWidth > innerWidth), false, '1280px investigate panel overflows');
  await screenshot('investigate-1280');
  if (process.argv.includes('--assist-demo')) {
    await evaluate(() => document.getElementById('assist-events').scrollIntoView({ block: 'center' }));
    await screenshot('assist-1280');
    await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 900, deviceScaleFactor: 1, mobile: false });
    await evaluate(() => document.getElementById('assist-events').scrollIntoView({ block: 'center' }));
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > innerWidth), false, '390px assist panel overflows');
    await screenshot('assist-390');
    await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  }
  const diagnostic = await evaluate(async investigateShift => {
    const humanize = value => value.toLowerCase().replaceAll('_', ' ');
    const panel = document.getElementById('investigate-view');
    const stepFor = label => [...panel.querySelectorAll('#diagnostic-result .evidence-step')].find(node => node.querySelector('.step-label')?.textContent.includes(label));
    const stationUrl = `/api/shifts/${encodeURIComponent(investigateShift)}/investigations`;
    let experiment = (await (await fetch(stationUrl)).json()).latest_experiment;
    let started = false;
    if (!experiment) {
      const runButton = document.getElementById('run-diagnostic');
      if (runButton.disabled) throw new Error('The public diagnostic button is disabled with an entry recorded');
      runButton.click();
      started = true;
      const deadline = Date.now() + 20000;
      while (Date.now() < deadline) {
        if (document.getElementById('diagnostic-result').querySelector('.evidence-step')) break;
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      if (!document.getElementById('diagnostic-result').querySelector('.evidence-step')) throw new Error(`The diagnostic did not reach a rendered result: ${document.getElementById('investigate-error')?.textContent ?? ''}`);
    }
    const id = document.getElementById('diagnostic-result').dataset.experimentId;
    experiment = await (await fetch(`/api/experiments/${encodeURIComponent(id)}`)).json();
    const trial = experiment.trials[0];
    const output = trial.outputs[0];
    if (!output) throw new Error('The diagnostic produced no capture to verify');
    const trialLine = [...panel.querySelectorAll('.contract-line')].find(node => node.querySelector('span')?.textContent === 'Trial state');
    if (trialLine?.querySelector('strong')?.textContent !== `${trial.state} · candidate ${trial.candidate_label}`) throw new Error(`Rendered trial state does not match: ${trialLine?.querySelector('strong')?.textContent}`);
    const request = stepFor('Frozen incident request');
    if (request?.querySelector('.request-quote')?.textContent !== output.request_text) throw new Error('Rendered frozen request does not match the capture');
    const exact = stepFor('Exact output the starter produced');
    const bytes = Uint8Array.from(atob(output.body_base64), character => character.charCodeAt(0));
    if (exact?.querySelector('.evidence-text')?.textContent !== new TextDecoder('utf-8', { fatal: true }).decode(bytes)) throw new Error('Rendered exact output does not match the capture bytes');
    if (exact?.querySelector('[data-body-base64]')?.dataset.bodyBase64 !== output.body_base64) throw new Error('Rendered base64 capture does not match the capture');
    if (!exact.textContent.includes(`HTTP ${output.http_status}`)) throw new Error('Rendered HTTP status does not match the capture');
    const customer = stepFor('Rendered customer answer');
    if (customer?.querySelector('.evidence-text')?.textContent !== (trial.customer_text ?? 'No customer answer was rendered for this trial.')) throw new Error('Rendered customer answer does not match the trial');
    const assessment = stepFor('Independently assessed required tasks');
    const rows = [...assessment.querySelectorAll('[data-task-id]')];
    if (rows.length !== trial.task_assessments.length) throw new Error('Rendered task assessment count differs from the API payload');
    for (const entry of trial.task_assessments) {
      const item = rows.find(node => node.dataset.taskId === entry.task_id);
      const expected = `${entry.task_id} · ${humanize(entry.outcome)}${entry.reason_codes.length ? ` · ${entry.reason_codes.join(', ')}` : ''}`;
      if (item?.querySelector('strong')?.textContent !== expected) throw new Error(`Rendered task row does not match the API payload for ${entry.task_id}: ${item?.querySelector('strong')?.textContent} is not ${expected}`);
      if (item.dataset.outcome !== entry.outcome || item.dataset.verdict !== (entry.mandatory_pass ? 'pass' : 'fail')) throw new Error(`Rendered mandatory outcome is wrong for ${entry.task_id}`);
    }
    const observations = stepFor('Observed interpretation and tool use');
    if (observations.querySelectorAll('.event-row').length !== trial.observations.length) throw new Error('Rendered observation count differs from the API payload');
    if (!trial.observations.length && !observations.textContent.includes('no interpretation or tool events')) throw new Error('The empty observation state is missing');
    const eligibility = stepFor('Eligibility').querySelector('[data-eligible]');
    if (experiment.eligible || eligibility.dataset.eligible !== 'false') throw new Error('Diagnostic eligibility is misreported as eligible');
    if (eligibility.querySelector('small')?.textContent !== experiment.eligibility_reason) throw new Error('Rendered eligibility reason does not match the API payload');
    const statement = eligibility.querySelector('strong')?.textContent;
    if (statement !== 'Not eligible · this diagnostic cannot qualify a version') throw new Error(`Rendered eligibility statement does not state that the diagnostic cannot qualify a version: ${statement}`);
    if (!panel.textContent.includes(experiment.context_evidence_class) || !panel.textContent.includes('Evidence class')) throw new Error('The evidence class is not rendered');
    return { experiment: id, started, state: trial.state, tasks: trial.task_assessments.length, observations: trial.observations.length, customerText: trial.customer_text };
  }, investigateView.shift);
  await evaluate(() => document.getElementById('diagnostic-result').scrollIntoView({ block: 'start' }));
  await screenshot('investigate-diagnostic-1280');
  await evaluate(() => document.querySelector('[data-station="service"]').click());
  const comparison = process.argv.includes('--compare-demo') ? await evaluate(async (candidateA, candidateB) => {
    const humanize = value => value.toLowerCase().replaceAll('_', ' ');
    const shiftId = (await (await fetch('/api/engagements/bookshop/board')).json()).latest_shift.id;
    const put = files => fetch(`/api/shifts/${encodeURIComponent(shiftId)}/artifact`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ files }) }).then(response => {
      if (!response.ok) throw new Error(`Artifact save failed: ${response.status}`);
      return response.json();
    });
    const wait = async (label, check) => {
      const deadline = Date.now() + 60000;
      while (Date.now() < deadline) { if (check()) return; await new Promise(resolve => setTimeout(resolve, 60)); }
      throw new Error(`Timed out waiting for ${label}`);
    };
    document.querySelector('[data-station="compare"]').click();
    if (document.getElementById('compare-view').hidden) throw new Error('The Compare station does not open its own panel');
    if (document.getElementById('run-comparison').disabled !== true) throw new Error('The comparison can start without two frozen candidates and a treatment');
    const frozenLabel = index => document.getElementById('candidate-list').querySelectorAll('.contract-line strong')[index]?.textContent ?? '';
    const freezeIdle = () => !document.getElementById('freeze-candidate-a').disabled && !document.getElementById('freeze-candidate-b').disabled;
    await put({ 'service.py': candidateA });
    await wait('the Compare station to accept the first freeze', freezeIdle);
    document.getElementById('freeze-candidate-a').click();
    await wait('candidate A freeze', () => frozenLabel(0).startsWith('ver-') && freezeIdle());
    await put({ 'service.py': candidateB });
    await wait('the Compare station to accept the second freeze', freezeIdle);
    document.getElementById('freeze-candidate-b').click();
    await wait('candidate B freeze', () => frozenLabel(1).startsWith('ver-') && freezeIdle());
    if (frozenLabel(0) === frozenLabel(1)) throw new Error('Both candidates froze the same version, so the comparison cannot bind two distinct repairs');
    const frozen = await (await fetch(`/api/engagements/bookshop/board`)).json();
    if (frozen.latest_version.id === frozen.operating_selection?.selected_version_id) throw new Error('Freezing a candidate changed the operating selection');
    document.getElementById('treatment-input').value = 'A answers the optional price fact everywhere; B answers it only when the request asks for it';
    document.getElementById('treatment-input').dispatchEvent(new Event('input'));
    if (document.getElementById('run-comparison').disabled) throw new Error('The comparison button stays disabled after two distinct candidates, a treatment and a recorded investigation');
    document.getElementById('run-comparison').click();
    await wait('the six rendered comparison slots', () => document.querySelectorAll('#comparison-slots .comparison-slot').length === 6);
    await wait('the comparison to reach a terminal state', () => ['FINALIZED', 'FAILED'].map(humanize).includes(document.getElementById('compare-state').textContent.split('·').pop().trim()));
    const experimentId = document.getElementById('compare-state').textContent.match(/experiment-[^\s]+/)?.[0];
    const payload = await (await fetch(`/api/experiments/${encodeURIComponent(experimentId)}`)).json();
    if (payload.kind !== 'QUALIFYING_COMPARISON' || payload.trials.length !== 6) throw new Error('The Compare station payload is not a six-slot qualifying comparison');
    const rows = [...document.querySelectorAll('#comparison-slots .comparison-slot')];
    const seenVersions = new Set();
    for (const trial of payload.trials) {
      const row = rows.find(node => Number(node.dataset.executionOrdinal) === trial.execution_ordinal);
      if (!row) throw new Error(`Slot ${trial.execution_ordinal} is not rendered`);
      if (row.dataset.pair !== String(trial.pair_ordinal) || row.dataset.candidateLabel !== trial.candidate_label) throw new Error(`Slot ${trial.execution_ordinal} renders the wrong pair or candidate`);
      if (row.dataset.versionId !== trial.artifact_version_id || row.dataset.runId !== (trial.run_id ?? '')) throw new Error(`Slot ${trial.execution_ordinal} renders the wrong version or run identity`);
      if (row.dataset.requestCount !== String(trial.request_count) || !row.textContent.includes(`${trial.request_count} public request`)) throw new Error(`Slot ${trial.execution_ordinal} renders the wrong frozen batch size`);
      if (row.dataset.protectedRequestCount !== String(trial.protected_request_count) || !row.textContent.includes(`${trial.protected_request_count} protected step`)) throw new Error(`Slot ${trial.execution_ordinal} renders the wrong protected step count`);
      if (row.dataset.state !== trial.state) throw new Error(`Slot ${trial.execution_ordinal} renders the wrong state`);
      if (trial.missing_evidence.length && !row.textContent.includes('Missing evidence')) throw new Error(`Slot ${trial.execution_ordinal} hides its missing evidence`);
      seenVersions.add(trial.artifact_version_id);
      const assessed = [...row.querySelectorAll('[data-task-id]')];
      if (assessed.length !== trial.task_assessments.length) throw new Error(`Slot ${trial.execution_ordinal} renders the wrong task-assessed count`);
      for (const entry of trial.task_assessments) {
        const item = assessed.find(node => node.dataset.taskId === entry.task_id && node.dataset.requestOrdinal === String(entry.request_ordinal) && node.dataset.verdict === (entry.mandatory_pass ? 'pass' : 'fail'));
        if (!item) throw new Error(`Slot ${trial.execution_ordinal} renders no ${entry.task_id} request ${entry.request_ordinal} row with the payload verdict`);
        if (!item.querySelector('small')?.textContent.includes(`request ${entry.request_ordinal}`)) throw new Error(`Slot ${trial.execution_ordinal} does not display the request ordinal for ${entry.task_id}`);
        const expected = `${entry.task_id} · ${humanize(entry.outcome)}${entry.reason_codes.length ? ` · ${entry.reason_codes.join(', ')}` : ''}`;
        if (item.querySelector('strong')?.textContent !== expected) throw new Error(`Slot ${trial.execution_ordinal} task row does not match the API payload for ${entry.task_id} request ${entry.request_ordinal}`);
      }
      for (const output of trial.outputs) if (!row.textContent.includes(output.request_text)) throw new Error(`Slot ${trial.execution_ordinal} does not render its frozen request text`);
    }
    if (seenVersions.size !== 2) throw new Error('The six slots do not bind exactly the two frozen candidate versions');
    const pairs = payload.trials.reduce((acc, trial) => { (acc[trial.pair_ordinal] ??= new Set()).add(trial.workload_id); return acc; }, {});
    if (Object.values(pairs).some(workloads => workloads.size !== 1)) throw new Error('A pair does not share one frozen workload');
    if (!document.getElementById('compare-summary').textContent.includes('no winner derived here')) throw new Error('The Compare station does not state that it derives no winner');
    if (payload.eligible !== false) throw new Error('A raw paired comparison reports eligibility before its outcome slice');
    return { experiment: experimentId, state: payload.state, slots: payload.trials.map(trial => `${trial.execution_ordinal}:${trial.pair_ordinal}${trial.candidate_label}/${trial.workload_id}/${trial.request_count}`).join(' ') };
  }, await readFile('shiftwork/fixtures/artifacts/bookshop/compare_repair_a_service.py', 'utf8'), await readFile('shiftwork/fixtures/artifacts/bookshop/compare_repair_b_service.py', 'utf8')) : null;
  if (comparison) {
    await evaluate(() => document.getElementById('comparison-slots').scrollIntoView({ block: 'start' }));
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > innerWidth), false, '1280px compare panel overflows');
    await screenshot('compare-1280');
    await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 900, deviceScaleFactor: 1, mobile: false });
    await evaluate(() => document.getElementById('comparison-slots').scrollIntoView({ block: 'start' }));
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > innerWidth), false, '390px compare panel overflows');
    await screenshot('compare-390');
    await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    await evaluate(() => document.querySelector('[data-station="service"]').click());
  }
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
  const report = { matrix, investigateStation: { ...investigateView, diagnostic }, assistDemo: process.argv.includes('--assist-demo') ? 'recorded double, hint and accepted patch attribution' : 'not enabled', compareDemo: comparison ?? 'not enabled', navigationAndStaleIncident: 'PASS', keyboard: 'PASS (evaluator and customer Enter/Tab)', reducedMotion: 'PASS', states: ['loading', 'error', 'empty', 'no incidents', 'malformed body', 'no public record'], repairWithoutIncident: 'blocked', literalUntrustedText: 'PASS', realRunButton: process.argv.includes('--exercise-run') ? 'PASS' : 'not exercised in this run', labelRemovalMutations: 'caught in every visible region', ordinalMutation: 'caught', renderedEvidence: 'exact answer, public record, verdict, event, investigation and diagnostic text against the API payload', narrowStationReach: 'native touch brings the panel into reach at 640/390', incidentNavigationFocus: 'keyboard activation focuses the selected request', downloadedBytes: 'exact', uncaughtExceptions: exceptions.length };
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
