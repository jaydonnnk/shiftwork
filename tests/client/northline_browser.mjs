import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { once } from 'node:events';
import { chromePath, pythonPath } from './env.mjs';
import { blockExternalAssets } from './local_network.mjs';

const url = process.argv[2];
assert.equal(new URL(url).hostname, '127.0.0.1');
const out = path.resolve(process.env.SHIFTWORK_ARTIFACT_DIR);
await mkdir(out);
const fixture = JSON.parse(await readFile(process.env.SHIFTWORK_TEST_INPUTS, 'utf8'));
const profile = await mkdtemp(path.join(tmpdir(), 'shiftwork-northline-browser-'));
const child = spawn(chromePath, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
const endpoint = await new Promise((resolve, reject) => {
  let stderr = '';
  const timer = setTimeout(() => reject(new Error('Chrome startup timeout')), 15000);
  child.on('error', reject);
  child.stderr.on('data', data => { stderr += data; const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/); if (match) { clearTimeout(timer); resolve(match[1]); } });
});
const socket = new WebSocket(endpoint);
await once(socket, 'open');
let sequence = 0, session;
const pending = new Map(), exceptions = [];
socket.addEventListener('message', ({ data }) => {
  const message = JSON.parse(data);
  if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails);
  if (!message.id) return;
  const item = pending.get(message.id); if (!item) return;
  pending.delete(message.id); clearTimeout(item.timer);
  message.error ? item.reject(new Error(JSON.stringify(message.error))) : item.resolve(message.result);
});
function send(method, params = {}, scoped = true) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout ${method}`)); }, 210000);
    pending.set(id, { resolve, reject, timer });
    socket.send(JSON.stringify({ id, method, params, ...(session && scoped ? { sessionId: session } : {}) }));
  });
}
async function evaluate(fn, ...args) {
  const result = await send('Runtime.evaluate', { expression: `(${fn.toString()})(...${JSON.stringify(args)})`, awaitPromise: true, returnByValue: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text);
  return result.result.value;
}
async function waitFor(fn, message, timeout = 15000) {
  const result = await evaluate(async (code, timeout) => {
    const predicate = (0, eval)(`(${code})`), deadline = Date.now() + timeout;
    while (Date.now() < deadline) { if (predicate()) return true; await new Promise(resolve => setTimeout(resolve, 50)); }
    return { load: document.body.dataset.loadState, message: document.getElementById('load-message').textContent, draft: document.getElementById('draft-error').textContent, compare: document.getElementById('compare-error').textContent };
  }, fn.toString(), timeout);
  assert.equal(result, true, `${message}: ${JSON.stringify(result)}`);
}
async function click(id) { await evaluate(id => document.getElementById(id).click(), id); }
async function station(name) { await evaluate(name => document.querySelector(`#northline-stations [data-station="${name}"]`).click(), name); }
async function screenshot(name) {
  const { data } = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  await writeFile(path.join(out, name + '.png'), Buffer.from(data, 'base64'), { flag: 'wx' });
}
async function api(endpoint) { return evaluate(async endpoint => { const r = await fetch(endpoint); if (!r.ok) throw new Error(`API ${endpoint}: ${r.status}`); return r.json(); }, endpoint); }
async function editFiles(files) {
  for (const [name, source] of Object.entries(files)) {
    const changed = await evaluate((name, source) => {
      const select = document.getElementById('draft-file'); select.value = name; select.dispatchEvent(new Event('change'));
      const input = document.getElementById('draft-source'); const changed = input.value !== source; input.value = source; input.dispatchEvent(new Event('input')); return changed;
    }, name, source);
    if (!changed) continue;
    assert.equal(await evaluate(() => document.getElementById('workplace-board').disabled), true, 'Dirty draft permits board switching');
    await click('save-draft');
    await waitFor(() => document.getElementById('draft-source').dataset.dirty === 'false' && !document.getElementById('draft-source').disabled, `Save did not retain ${name}`);
  }
}
async function verifyOutput() {
  const board = await api('/api/engagements/northline/board');
  const run = board.latest_run;
  const [outputs, checks] = await Promise.all([api(`/api/runs/${run.id}/outputs`), api(`/api/runs/${run.id}/checks`)]);
  await station('acceptance');
  const actual = await evaluate(() => ({ run: document.querySelector('[data-selection-field="executed-version"] strong')?.textContent, outputs: [...document.querySelectorAll('.customer-button')].map(node => node.dataset.outputId), request: document.querySelector('#selected-evidence .request-quote')?.textContent, body: document.querySelector('#selected-evidence [data-body-base64]')?.dataset.bodyBase64, checks: [...document.querySelectorAll('#selected-evidence [data-check-id]')].map(node => ({ id: node.dataset.checkId, verdict: node.querySelector('strong').textContent })) }));
  assert.equal(actual.run, `${run.artifact_version_id} · ${run.id}`, 'Executed version differs from Northline API');
  const selection = await evaluate(() => document.querySelector('[data-selection-field="operating-choice"] strong')?.textContent);
  const choice = board.operating_selection;
  assert.equal(selection, `${choice.selected_version_id} · ${choice.selected_content_hash} · ${choice.state.toLowerCase().replaceAll('_', ' ')}`, 'Selected version differs from Northline API');
  assert.deepEqual(actual.outputs, outputs.map(row => row.id), 'Acceptance output inventory differs from API');
  assert.equal(actual.request, outputs[0].request_text, 'Acceptance request differs from Northline API');
  assert.equal(actual.body, outputs[0].body_base64, 'Acceptance capture differs from Northline API');
  const humanize = value => value.toLowerCase().replaceAll('_', ' ');
  assert.deepEqual(actual.checks, checks.filter(row => row.observed_ref === outputs[0].id).map(row => ({ id: row.id, verdict: humanize(row.verdict) + (row.reason_code ? ` · ${row.reason_code}` : '') })), 'Acceptance verdict differs from Northline API');
  return { board, outputs, checks };
}
async function verifyFiles(selector, filename) {
  const board = await api('/api/engagements/northline/board');
  const selected = await api(`/api/artifact-versions/${board.operating_selection.selected_version_id}`);
  const draft = await api(`/api/shifts/${board.latest_shift.id}/artifact`);
  const actual = await evaluate((selector, filename) => [...document.querySelectorAll(`${selector} [data-deployment-file="${filename}"]`)].map(node => ({ owner: node.dataset.fileOwner, source: node.querySelector('pre').textContent, version: node.dataset.versionId })), selector, filename);
  assert.equal(actual.find(row => row.owner === 'Selected version')?.source, selected.files[filename], 'Selected worksheet differs from exact Northline version');
  assert.equal(actual.find(row => row.owner === 'Selected version')?.version, selected.id, 'Selected worksheet version differs from API');
  assert.equal(actual.find(row => row.owner === 'Current draft')?.source, draft.files[filename], 'Draft worksheet differs from Northline API');
}
async function verifyEvents(selector, handover) {
  const ledger = await api('/api/engagements/northline/ledger');
  const expected = ledger.events.filter(event => (event.event_type === 'HANDOVER_DECLARED') === handover);
  const actual = await evaluate(selector => [...document.querySelectorAll(`${selector} [data-deployment-event]`)].map(node => ({ id: node.dataset.deploymentEvent, type: node.querySelector('strong').textContent, payload: JSON.parse(node.querySelector('pre').textContent) })), selector);
  assert.deepEqual(actual, expected.map(event => ({ id: String(event.seq), type: event.event_type.toLowerCase().replaceAll('_', ' '), payload: event.payload })), handover ? 'Handover history differs from recorded Northline API' : 'Pilot history differs from recorded Northline API');
  const label = await evaluate(selector => document.querySelector(selector).parentElement.querySelector('.synthetic')?.textContent, selector);
  assert.equal(label, 'Synthetic scenario', 'Northline consequence lacks its synthetic label');
}
async function verifyComparison() {
  await station('bench');
  const board = await api('/api/engagements/northline/board');
  const investigation = await api(`/api/shifts/${board.latest_shift.id}/investigations`);
  const comparison = investigation.latest_experiment;
  const actual = await evaluate(() => ({ slots: [...document.querySelectorAll('#comparison-slots [data-run-id]')].map(node => node.dataset.runId), summary: document.getElementById('compare-summary').textContent, candidates: [...document.querySelectorAll('#candidate-list [data-candidate-label] strong')].map(node => node.textContent), mode: document.querySelector('[data-comparison-field="mode"] strong')?.textContent, budget: document.getElementById('assist-budget').textContent, roles: [...document.getElementById('assist-role').options].filter(option => !option.disabled).map(option => option.value) }));
  assert.equal(comparison.state, 'FINALIZED');
  assert.equal(comparison.outcome.status, 'COMPLETE');
  assert.deepEqual(actual.slots, comparison.trials.map(row => row.run_id), 'Comparison slot ownership differs from Northline API');
  assert.equal(actual.mode, comparison.context_evidence_class, 'Comparison mode differs from Northline API');
  assert.ok(actual.summary.includes(`public requests per candidate ${comparison.shared_public_denominator_requests}`), 'Comparison public denominator differs from Northline API');
  assert.ok(actual.summary.includes(`protected steps per candidate ${comparison.protected_denominator_requests_per_candidate}`), 'Comparison protected denominator differs from Northline API');
  assert.deepEqual(actual.candidates, comparison.candidates.map(row => `${row.artifact_version_id} · content hash ${row.artifact_content_hash}`), 'Candidate identity differs from Northline API');
  assert.equal(actual.budget, `${investigation.assist_used} of ${investigation.assist_limit} help calls used this shift. Failed calls also count.`, 'Assistance budget differs from Northline API');
  assert.deepEqual(actual.roles, ['HINT'], 'Northline offers a forbidden assistance role');
  const rendered = await evaluate(() => ({
    fields: Object.fromEntries([...document.querySelectorAll('[data-comparison-field]')].map(node => [node.dataset.comparisonField, node.querySelector('strong').textContent])),
    slots: [...document.querySelectorAll('#comparison-slots [data-run-id]')].map(node => ({
      run: node.dataset.runId, version: node.dataset.versionId, state: node.dataset.state,
      requests: [...node.querySelectorAll('.request-quote')].map(item => item.textContent),
      tasks: [...node.querySelectorAll('[data-task-id]')].map(item => ({ id: item.dataset.taskId, ordinal: item.dataset.requestOrdinal, outcome: item.dataset.outcome, verdict: item.dataset.verdict, text: item.querySelector('strong').textContent })),
    })),
    cards: [...document.querySelectorAll('.comparison-outcome-card')].map(node => ({ label: node.dataset.candidateLabel, eligible: node.dataset.eligible, header: node.querySelector('h4').textContent, metrics: Object.fromEntries([...node.querySelectorAll('[data-metric]')].map(item => [item.dataset.metric, item.textContent])) })),
  }));
  const humanize = value => value.toLowerCase().replaceAll('_', ' ');
  assert.equal(rendered.fields.purpose, humanize(comparison.kind), 'Comparison purpose differs from Northline API');
  assert.equal(rendered.fields.context, comparison.context_hash, 'Comparison context differs from Northline API');
  for (const [index, trial] of comparison.trials.entries()) {
    const slot = rendered.slots[index];
    assert.equal(slot.version, trial.artifact_version_id, 'Trial version differs from Northline API');
    assert.deepEqual(slot.requests, trial.outputs.map(output => `Request ${output.request_ordinal}: ${output.request_text}`), 'Trial request differs from Northline API');
    assert.deepEqual(slot.tasks, trial.task_assessments.map(row => ({ id: row.task_id, ordinal: String(row.request_ordinal), outcome: row.outcome, verdict: row.mandatory_pass ? 'pass' : 'fail', text: `${row.task_id} · ${humanize(row.outcome)}${row.reason_codes.length ? ` · ${row.reason_codes.join(', ')}` : ''}` })), 'Trial outcome differs from Northline API');
  }
  for (const metrics of comparison.outcome.candidate_metrics) {
    const eligibility = comparison.outcome.eligibility.find(row => row.candidate_label === metrics.candidate_label);
    const card = rendered.cards.find(row => row.label === metrics.candidate_label);
    assert.equal(card.eligible, String(eligibility.eligible), 'Candidate eligibility differs from Northline API');
    assert.equal(card.header, `Candidate ${metrics.candidate_label} · ${eligibility.eligible ? 'eligible' : 'blocked'}${eligibility.blocking_reason_codes.length ? ` · ${eligibility.blocking_reason_codes.join(', ')}` : ''}`, 'Candidate blocker differs from Northline API');
    assert.deepEqual(card.metrics, Object.fromEntries(Object.keys(card.metrics).map(key => [key, String(metrics[key] ?? 'unknown')])), 'Candidate metrics differ from Northline API');
  }
  return comparison;
}
async function verifyRoom() {
  const boards = await api('/api/boards');
  const actual = await evaluate(() => ({ options: [...document.getElementById('workplace-board').options].map(option => ({ slug: option.value, disabled: option.disabled, label: option.textContent })), room: document.querySelector('.room').getAttribute('aria-label'), names: [...document.querySelectorAll('#northline-stations button')].map(node => node.lastChild.textContent), visible: [...document.querySelectorAll('[data-station]')].filter(node => node.getClientRects().length).length }));
  assert.deepEqual(actual.options.map(row => row.slug), boards.map(row => row.engagement_slug), 'Workplace order differs from API');
  assert.deepEqual(actual.options.map(row => row.disabled), boards.map(row => row.availability !== 'AVAILABLE'), 'Workplace availability differs from API');
  assert.deepEqual(actual.options.map(row => row.label), boards.map(row => `${row.role_name} · ${row.client ?? row.employer}${row.availability === 'AVAILABLE' ? '' : ' · awaiting operator review'}`), 'Workplace display differs from API');
  assert.equal(actual.room, 'Northline deployment workshop', 'Northline opens the wrong room');
  assert.deepEqual(actual.names, ['Deployment brief', 'System map', 'Integration bench', 'Acceptance', 'Rollout', 'Handover'], 'Native station names differ from approved direction');
  assert.equal(actual.visible, 6, 'Northline exposes the wrong station count');
  assert.equal(await evaluate(() => { const art = document.getElementById('northline-art'); return !art.hasAttribute('hidden') && art.getBoundingClientRect().width > 0 && getComputedStyle(art).display !== 'none'; }), true, 'Northline artwork is not visible');
}

async function assertPublicDOM(label) {
  const surface = await evaluate(() => ({ rendered_text: document.body.innerText, serialized_dom: document.body.outerHTML }));
  const script = `import json,sys
sys.path.insert(0,'tests')
from leakscan import sealed_identity_strings
from shiftwork.gateway.redaction import serialized_contains
needles=(*sealed_identity_strings(),'S22B_TEST_PROVIDER_SECRET','S22B_TEST_SANDBOX_SECRET')
surface=json.load(sys.stdin)
controls=all(serialized_contains({**surface,'serialized_dom':surface['serialized_dom']+form},needle) for needle in needles for form in (needle,needle.replace('\\\\','/'),json.dumps(needle)[1:-1]))
print(json.dumps({'needles':len(needles),'controls':controls,'clean':not any(serialized_contains(surface,needle) for needle in needles)}))`;
  const scanned = await new Promise((resolve, reject) => {
    const child = spawn(pythonPath, ['-c', script], { stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '', stderr = '';
    const timer = setTimeout(() => { child.kill(); reject(new Error('DOM scanner timed out')); }, 30000);
    child.stdout.on('data', data => { stdout += data; }); child.stderr.on('data', data => { stderr += data; });
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('exit', code => { clearTimeout(timer); code === 0 ? resolve(JSON.parse(stdout)) : reject(new Error(stderr)); });
    child.stdin.end(JSON.stringify(surface));
  });
  await writeFile(path.join(out, `dom-scan-${label}.json`), JSON.stringify(scanned), { flag: 'wx' });
  assert.equal(scanned.controls, true, 'DOM scanner did not detect every serialized needle form');
  assert.equal(scanned.clean, true, 'Northline DOM contains private material');
}

async function verifyWorkplaceGuards() {
  const before = await api('/api/engagements/northline/ledger');
  await station('bench');
  await evaluate(() => { const source = document.getElementById('draft-source'); source.value += '\n# unsaved control'; source.dispatchEvent(new Event('input')); });
  assert.equal(await evaluate(() => document.getElementById('workplace-board').disabled), true, 'Dirty draft permits board switching');
  await evaluate(() => { const select = document.getElementById('workplace-board'); select.value = 'bookshop'; select.dispatchEvent(new Event('change')); });
  assert.equal(await evaluate(() => document.getElementById('workplace-board').value), 'northline', 'Dirty programmatic board switch was accepted');
  await click('discard-draft-edit');
  // Every registered board is admitted now, so fabricate one awaiting review to
  // prove the client still refuses to open an unreviewed board.
  await evaluate(async () => {
    const original = window.fetch; window.__originalFetch = original;
    window.fetch = async (...args) => {
      const response = await original(...args);
      if (args[0] !== '/api/boards') return response;
      const payload = (await response.clone().json()).map(row => row.engagement_slug === 'gtm' ? { ...row, availability: 'AWAITING_OPERATOR_REVIEW' } : row);
      return new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } });
    };
    document.getElementById('refresh').click();
  });
  await waitFor(() => [...document.getElementById('workplace-board').options].some(option => option.value === 'gtm' && option.textContent.includes('awaiting operator review')), 'Fabricated unreviewed board did not render');
  await verifyRoom();
  await evaluate(() => { const select = document.getElementById('workplace-board'); select.value = 'gtm'; select.dispatchEvent(new Event('change')); });
  assert.equal(await evaluate(() => document.getElementById('workplace-board').value), 'northline', 'Unreviewed programmatic board switch was accepted');
  await evaluate(() => { window.fetch = window.__originalFetch; document.getElementById('refresh').click(); });
  await waitFor(() => document.body.dataset.loadState === 'ready' && ![...document.getElementById('workplace-board').options].some(option => option.disabled), 'Real workplace list did not return');
  // Delay an old Northline board response while selecting Bellwether, then
  // release it after the newer board has rendered. No persisted rows change.
  await evaluate(() => {
    const original = window.fetch; window.__originalFetch = original;
    window.__oldBoardArrived = false; window.__oldBoardFinished = false;
    window.fetch = async (...args) => {
      const response = await original(...args);
      if (args[0] === '/api/engagements/northline/board' && !window.__oldBoardArrived) {
        window.__oldBoardArrived = true;
        await new Promise(resolve => { window.__releaseOldBoard = resolve; });
        setTimeout(() => { window.__oldBoardFinished = true; }, 100);
      }
      return response;
    };
    document.getElementById('refresh').click();
  });
  await waitFor(() => window.__oldBoardArrived, 'Old board response was not delayed');
  await evaluate(() => { const select = document.getElementById('workplace-board'); select.value = 'bookshop'; select.dispatchEvent(new Event('change')); });
  await waitFor(() => document.body.dataset.board === 'bookshop' && ['ready', 'empty'].includes(document.body.dataset.loadState), 'Bellwether did not load during old Northline refresh');
  await evaluate(() => window.__releaseOldBoard());
  await waitFor(() => window.__oldBoardFinished, 'Old board response was not released');
  assert.equal(await evaluate(() => document.body.dataset.board), 'bookshop', 'Old Northline refresh replaced newer Bellwether board');
  assert.equal(await evaluate(() => document.getElementById('candidate-list').textContent.includes('content hash')), false, 'Previous board candidates survived workplace switch');
  await evaluate(() => { window.fetch = window.__originalFetch; const select = document.getElementById('workplace-board'); select.value = 'northline'; select.dispatchEvent(new Event('change')); });
  await waitFor(() => document.body.dataset.board === 'northline' && document.body.dataset.loadState === 'ready', 'Northline did not return');
  assert.deepEqual(await api('/api/engagements/northline/ledger'), before, 'Workplace navigation changed operational history');
  await verifyRoom();
}

async function verifyReach() {
  const stations = { brief: 'Deployment brief', map: 'System map', bench: 'Integration bench', acceptance: 'Acceptance', rollout: 'Rollout', handover: 'Handover' };
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  for (const width of [1280, 390]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
    for (const [name, title] of Object.entries(stations)) {
      await evaluate(name => { const button = document.querySelector(`#northline-stations [data-station="${name}"]`); button.scrollIntoView({ block: 'center', behavior: 'instant' }); button.focus({ preventScroll: true }); }, name);
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
      const reachable = await evaluate(async () => { await new Promise(resolve => setTimeout(resolve, 100)); const panel = document.getElementById('station-panel'); return { overflow: document.documentElement.scrollWidth > innerWidth, focus: document.activeElement === panel, top: panel.getBoundingClientRect().top, title: document.getElementById('panel-title').textContent }; });
      assert.equal(reachable.title, title, 'Keyboard did not activate the Northline station');
      assert.equal(reachable.overflow, false, `Northline overflows at ${width}px`);
      if (width === 390) {
        assert.equal(reachable.focus, true, 'Mobile station does not focus its panel');
        assert.ok(reachable.top >= 0 && reachable.top < 900, 'Mobile station panel is out of reach');
        await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 1 });
        const point = await evaluate(name => { const button = document.querySelector(`#northline-stations [data-station="${name}"]`); button.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = button.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }, name);
        await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [point] });
        await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
        assert.equal(await evaluate(() => document.activeElement.id), 'station-panel', 'Mobile touch does not reach the selected panel');
        await send('Emulation.setTouchEmulationEnabled', { enabled: false });
      }
      await assertPublicDOM(`${width}-${name}`);
    }
    await station('rollout'); await verifyEvents('#pilot-records', false); await screenshot(`${width}-rollout`);
    await station('handover'); await verifyFiles('#handover-records', 'runbook.md'); await screenshot(`${width}-handover`);
    await evaluate(() => window.scrollTo(0, 0)); await screenshot(`${width}-workshop`);
  }
}

const fault = process.env.SHIFTWORK_FAULT;
const FAULTS = {
  selectedWorksheet: ["['Selected version', selected?.files, selected?.id]", "['Selected version', draft?.files, selected?.id]", 'Selected worksheet differs from exact Northline version'],
  pilotPayload: ['JSON.stringify(event.payload, null, 2)', "JSON.stringify({ ...event.payload, weight: 999 }, null, 2)", 'Pilot history differs from recorded Northline API'],
  handoverPayload: ['JSON.stringify(event.payload, null, 2)', "JSON.stringify(event.event_type === 'HANDOVER_DECLARED' ? { ...event.payload, runbook_version_id: 'wrong-version' } : event.payload, null, 2)", 'Handover history differs from recorded Northline API'],
  assistanceRole: ['option.disabled = !station?.assist_allowed_roles?.includes(option.value)', 'option.disabled = false', 'Northline offers a forbidden assistance role'],
  comparisonMode: ["['mode', 'Evidence mode', compare.context_evidence_class]", "['mode', 'Evidence mode', 'ISOLATED_LIVE']", 'Comparison mode differs from Northline API'],
  comparisonDenominator: ['public requests per candidate ${compare.shared_public_denominator_requests}', 'public requests per candidate 999', 'Comparison public denominator differs from Northline API'],
  candidateIdentity: ['`${version.id} · content hash ${version.content_hash}`', '`wrong-version · content hash ${version.content_hash}`', 'Candidate identity differs from Northline API'],
  outputVersion: ["['version', 'Executed version', run.artifact_version_id]", "['version', 'Executed version', 'wrong-version']", 'Acceptance execution version differs from Northline API'],
  availability: ["option.disabled = board.availability !== 'AVAILABLE';", 'option.disabled = false;', 'Workplace availability differs from API'],
  stationNames: ["element('span', labels[index])", "element('span', 'Wrong station')", 'Native station names differ from approved direction'],
  privateDOM: ["document.body.dataset.loadState = board.latest_shift ? 'ready' : 'empty';", "document.body.dataset.loadState = board.latest_shift ? 'ready' : 'empty'; document.body.dataset.secret = 'S22B_TEST_PROVIDER_SECRET';", 'Northline DOM contains private material'],
  mobileFocus: ["panel.focus({ preventScroll: true });", 'void panel;', 'Mobile station does not focus its panel'],
  protectedDenominator: ['protected steps per candidate ${compare.protected_denominator_requests_per_candidate}', 'protected steps per candidate 999', 'Comparison protected denominator differs from Northline API'],
  dirtySwitch: ["state.pending || hasUnsavedDraft() || !state.workplaces.some", "state.pending || false || !state.workplaces.some", 'Dirty programmatic board switch was accepted'],
  unreviewedSwitch: ["board.engagement_slug === slug && board.availability === 'AVAILABLE'", 'board.engagement_slug === slug', 'Unreviewed programmatic board switch was accepted'],
  purpose: ["['purpose', 'Purpose', humanize(compare.kind)]", "['purpose', 'Purpose', 'operation']", 'Comparison purpose differs from Northline API'],
  context: ["['context', 'Frozen context', compare.context_hash]", "['context', 'Frozen context', 'wrong-context']", 'Comparison context differs from Northline API'],
  trialRequest: ['`Request ${output.request_ordinal}: ${output.request_text}`', '`Request ${output.request_ordinal}: wrong Northline request`', 'Trial request differs from Northline API'],
  trialOutcome: ['item.dataset.outcome = result.outcome;', "item.dataset.outcome = 'WRONG_OUTCOME';", 'Trial outcome differs from Northline API'],
  outcomeMetric: ["const value = element('dd', metrics[key] ?? 'unknown');", "const value = element('dd', key === 'useful_completions' ? 999 : (metrics[key] ?? 'unknown'));", 'Candidate metrics differ from Northline API'],
  falseBlocker: ["eligibility.blocking_reason_codes.length ? ` · ${eligibility.blocking_reason_codes.join(', ')}` : ''", "' · WRONG_BLOCKER'", 'Candidate blocker differs from Northline API'],
  selectedVersion: ["`${choice.selected_version_id} · ${choice.selected_content_hash} · ${humanize(choice.state)}`", "`wrong-version · ${choice.selected_content_hash} · ${humanize(choice.state)}`", 'Selected version differs from Northline API'],
  syntheticLabel: ["$('operate-pilot').disabled = $('run-shift').disabled;", "$('operate-pilot').disabled = $('run-shift').disabled; document.querySelector('#rollout-view .synthetic').textContent = 'unlabelled';", 'Northline consequence lacks its synthetic label'],
};

try {
  const { targetId } = await send('Target.createTarget', { url: 'about:blank' }, false);
  session = (await send('Target.attachToTarget', { targetId, flatten: true }, false)).sessionId;
  await send('Page.enable'); await send('Runtime.enable');
  await blockExternalAssets({socket,send,evaluate,url});
  if (fault) {
    const source = (await readFile('shiftwork/client/app.js', 'utf8')).replaceAll('\r\n', '\n');
    const [needle, replacement] = FAULTS[fault];
    assert.equal(source.split(needle).length - 1, 1, `Fault anchor ${fault} is not unique`);
    socket.addEventListener('message', ({ data }) => {
      const message = JSON.parse(data); if (message.method !== 'Fetch.requestPaused') return;
      send('Fetch.fulfillRequest', { requestId: message.params.requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'text/javascript' }], body: Buffer.from(source.replace(needle, replacement)).toString('base64') }).catch(error => console.error(error));
    });
    await send('Fetch.enable', { patterns: [{ urlPattern: '*/app.js', requestStage: 'Request' }] });
  }
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url });
  const snapshot = process.env.SHIFTWORK_SNAPSHOT;
  await waitFor(() => ['ready', 'empty'].includes(document.body?.dataset.loadState), 'Client did not load');
  if (!new URL(url).searchParams.has('board')) {
    await evaluate(() => { const select = document.getElementById('workplace-board'); select.value = 'northline'; select.dispatchEvent(new Event('change')); });
    await waitFor(() => document.body.dataset.board === 'northline' && ['ready', 'empty'].includes(document.body.dataset.loadState), 'Workplace did not open Northline');
  }
  await verifyRoom();
  if (snapshot === 'comparison') {
    await verifyComparison();
    await station('map'); await verifyFiles('#map-records', 'discovery.md');
    await verifyWorkplaceGuards(); await verifyComparison();
  } else if (snapshot === 'closed' || snapshot === 'reach') {
    await verifyOutput();
    const executionVersion = await evaluate(() => document.querySelector('[data-execution-field="version"] strong')?.textContent);
    assert.equal(executionVersion, (await api('/api/engagements/northline/board')).latest_run.artifact_version_id, 'Acceptance execution version differs from Northline API');
    await station('rollout'); await verifyEvents('#pilot-records', false);
    await station('handover'); await verifyFiles('#handover-records', 'runbook.md'); await verifyEvents('#handover-records', true);
    if (snapshot === 'reach') await verifyReach();
  } else {
    await click('open-shift');
    await waitFor(() => document.body.dataset.loadState === 'ready' && !document.getElementById('run-shift').disabled, 'Blank starter did not open');
    await click('run-shift');
    await waitFor(() => document.getElementById('run-state').textContent.includes('FINALIZED'), 'Blank starter did not finalize', 60000);
    const starter = await verifyOutput();
    assert.ok(starter.checks.some(row => row.verdict === 'fail'), 'Blank starter did not fail acceptance');
    await station('bench');
    await evaluate(() => { for (const [id, value] of [['cause-input', 'The blank integration returns no booking task.'], ['falsifier-input', 'An independently verified booking already exists for this request.'], ['public-test-input', 'Require the booking result and matching resource receipts.']]) document.getElementById(id).value = value; });
    await click('append-investigation');
    await waitFor(() => document.querySelectorAll('#investigation-list [data-investigation-id]').length === 1 && !document.getElementById('freeze-candidate-a').disabled, 'Investigation was not recorded');
    await evaluate(() => { document.getElementById('assist-message').value = 'Give one hint from this captured response.'; });
    await click('request-assist');
    await waitFor(() => document.querySelectorAll('#assist-events [data-assist-event-id]').length === 1 && !document.getElementById('draft-source').disabled && !document.getElementById('workplace-board').disabled, 'Recorded hint left editor controls disabled');
    await evaluate(() => document.querySelector('#assist-events button').click());
    await waitFor(() => !document.querySelector('#assist-events button') && !document.getElementById('draft-source').disabled && !document.getElementById('workplace-board').disabled, 'Hint decision left editor controls disabled');
    assert.equal(await evaluate(() => document.getElementById('request-assist').disabled), true, 'Northline permits a second hint');
    for (const label of ['A', 'B']) {
      await editFiles(fixture[label]);
      await click('freeze-candidate-' + label.toLowerCase());
      await waitFor(() => [...document.querySelectorAll('#candidate-list strong')].every(node => node.textContent !== 'not frozen yet') || document.querySelector('#candidate-list [data-candidate-label="A"] strong')?.textContent.startsWith('ver-'), `Candidate ${label} did not freeze`);
      await waitFor(() => !document.getElementById('draft-source').disabled, 'Freeze did not finish');
      const board = await api('/api/engagements/northline/board');
      const saved = await api(`/api/artifact-versions/${board.latest_version.id}`);
      assert.deepEqual(saved.files, fixture[label], 'UI saved different candidate files');
    }
    await station('map'); await verifyFiles('#map-records', 'discovery.md'); await verifyFiles('#map-records', 'permissions.json');
    await station('bench');
    const beforeDiagnostic = await api('/api/engagements/northline/ledger');
    await click('run-diagnostic');
    await waitFor(() => document.getElementById('investigate-error').textContent && !document.getElementById('draft-source').disabled && !document.getElementById('workplace-board').disabled, 'Diagnostic refusal left editor controls disabled', 15000);
    assert.equal(await evaluate(() => document.getElementById('investigate-error').textContent), 'only the pinned reviewed starter is executable as a public diagnostic candidate', 'Edited offline diagnostic bypassed its source guard');
    assert.deepEqual(await api('/api/engagements/northline/ledger'), beforeDiagnostic, 'Diagnostic rewrote operational history');
    await evaluate(() => { const input = document.getElementById('treatment-input'); input.value = 'Separate commitment reference namespaces.'; input.dispatchEvent(new Event('input')); });
    await click('run-comparison');
    await waitFor(() => document.getElementById('compare-summary').textContent.includes('COMPLETE') && !document.getElementById('draft-source').disabled, 'Six-slot comparison did not complete', 180000);
    const comparison = await verifyComparison();
    assert.equal(comparison.trials.length, 6);
    assert.ok(comparison.outcome.eligibility.every(row => row.eligible));
    await evaluate(async () => { const r = await fetch('/__test__/checkpoint/comparison', { method: 'POST' }); if (!r.ok) throw new Error('Comparison checkpoint failed'); });
    await evaluate(() => { const input = document.getElementById('selection-rationale'); input.value = 'Keep candidate A with its exact verified commitments and worksheets.'; input.dispatchEvent(new Event('input')); });
    await click('select-candidate-a');
    await waitFor(() => document.getElementById('selection-note').textContent.startsWith('Choice '), 'Explicit choice was not retained');
    const chosen = (await api('/api/engagements/northline/board')).operating_selection;
    assert.equal(chosen.selected_version_id, comparison.candidates.find(row => row.label === 'A').artifact_version_id);
    await station('handover'); await click('close-shift');
    await waitFor(() => !document.getElementById('open-next-shift').disabled, 'First shift did not close');
    await click('open-next-shift');
    await waitFor(() => !document.getElementById('close-shift').disabled && !document.getElementById('run-shift').disabled, 'Selected next shift did not open');
    const inherited = await api('/api/engagements/northline/board');
    assert.deepEqual((await api(`/api/shifts/${inherited.latest_shift.id}/artifact`)).files, fixture.A, 'Next shift did not inherit every selected file');
    await station('rollout'); await click('operate-pilot');
    await waitFor(() => document.getElementById('run-state').textContent.includes('FINALIZED') && document.querySelector('[data-selection-field="executed-version"] strong').textContent.split(' · ')[0] === document.querySelector('[data-selection-field="operating-choice"] strong').textContent.split(' · ')[0], 'Selected pilot did not finalize', 60000);
    const pilot = await verifyOutput();
    assert.equal(pilot.board.latest_run.artifact_version_id, chosen.selected_version_id);
    assert.ok(pilot.checks.every(row => row.verdict === 'pass'), 'Selected pilot failed acceptance');
    const pilotEvents = (await api('/api/engagements/northline/ledger')).events.filter(row => row.cause_refs[0] === pilot.board.latest_run.id);
    assert.equal(pilotEvents.filter(row => row.event_type === 'ROLLOUT_APPROVED').length, 1);
    await station('bench'); await editFiles({ 'runbook.md': '# Newer unselected runbook\nThis must not replace A.\n' });
    await click('freeze-candidate-b'); await waitFor(() => !document.getElementById('draft-source').disabled, 'Newer save did not finish');
    await station('handover'); await verifyFiles('#handover-records', 'runbook.md');
    await click('close-shift'); await waitFor(() => !document.getElementById('open-next-shift').disabled, 'Pilot shift did not close');
    await verifyEvents('#handover-records', true);
    await evaluate(async () => { const r = await fetch('/__test__/checkpoint/closed', { method: 'POST' }); if (!r.ok) throw new Error('Closed checkpoint failed'); });
    await writeFile(path.join(out, 'journey.json'), JSON.stringify({ starter: starter.board.latest_run, comparison, choice: chosen, pilot: pilot.board.latest_run, ledger: await api('/api/engagements/northline/ledger'), mode: 'TRUSTED_LOCAL', test_only_pins: true }, null, 2), { flag: 'wx' });
    await verifyReach();
  }
  await assertPublicDOM('final');
  assert.deepEqual(exceptions, [], 'Browser raised JavaScript exceptions');
  console.log(JSON.stringify({ status: 'PASS', snapshot: snapshot ?? 'real UI journey', mode: 'TRUSTED_LOCAL', fault: fault ?? null }));
} catch (error) {
  await screenshot('failure').catch(() => {});
  console.error(error.stack);
  console.error(JSON.stringify({ exceptions }));
  process.exitCode = 1;
} finally {
  socket.close(); child.kill(); await once(child, 'exit').catch(() => {});
  assert.equal(path.dirname(profile), tmpdir(), 'Browser profile cleanup escaped temp root');
  assert.ok(path.basename(profile).startsWith('shiftwork-northline-browser-'));
  await rm(profile, { recursive: true, force: true, maxRetries: 5 });
}
