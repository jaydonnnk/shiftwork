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
const profile = await mkdtemp(path.join(tmpdir(), 'shiftwork-gtm-browser-'));
const child = spawn(chromePath, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
const endpoint = await new Promise((resolve, reject) => {
  let stderr = '';
  const timer = setTimeout(() => reject(new Error('Chrome startup timeout')), 15000);
  child.on('error', reject);
  child.stderr.on('data', data => { stderr += data; const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/); if (match) { clearTimeout(timer); resolve(match[1]); } });
});
const socket = new WebSocket(endpoint);
await Promise.race([once(socket, 'open'), new Promise((resolve, reject) => setTimeout(() => reject(new Error('CDP socket open timeout')), 20000))]);
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
async function station(name) { await evaluate(name => document.querySelector(`#gtm-stations [data-station="${name}"]`).click(), name); }
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
  const board = await api('/api/engagements/gtm/board');
  const run = board.latest_run;
  const [outputs, checks] = await Promise.all([api(`/api/runs/${run.id}/outputs`), api(`/api/runs/${run.id}/checks`)]);
  await station('signals');
  const actual = await evaluate(() => ({ run: document.querySelector('[data-selection-field="executed-version"] strong')?.textContent, outputs: [...document.querySelectorAll('.customer-button')].map(node => node.dataset.outputId), request: document.querySelector('#selected-evidence .request-quote')?.textContent, body: document.querySelector('#selected-evidence [data-body-base64]')?.dataset.bodyBase64, purpose: document.querySelector('[data-execution-field="purpose"] strong')?.textContent, mode: document.querySelector('[data-execution-field="mode"] strong')?.textContent, checks: [...document.querySelectorAll('#selected-evidence [data-check-id]')].map(node => ({ id: node.dataset.checkId, verdict: node.querySelector('strong').textContent })) }));
  assert.equal(actual.run, `${run.artifact_version_id} · ${run.id}`, 'Executed version differs from GTM API');
  assert.equal(actual.purpose, humanize(run.purpose), 'Signal execution purpose differs from GTM API');
  assert.equal(actual.mode, run.evidence_mode ?? 'unknown', 'Signal evidence mode differs from GTM API');
  const selection = await evaluate(() => document.querySelector('[data-selection-field="operating-choice"] strong')?.textContent);
  const choice = board.operating_selection;
  assert.equal(selection, `${choice.selected_version_id} · ${choice.selected_content_hash} · ${humanize(choice.state)}`, 'Selected version differs from GTM API');
  assert.deepEqual(actual.outputs, outputs.map(row => row.id), 'Signal intake output inventory differs from API');
  assert.equal(actual.request, outputs[0].request_text, 'Signal intake request differs from API');
  assert.equal(actual.body, outputs[0].body_base64, 'Signal intake capture differs from API');
  assert.deepEqual(actual.checks, checks.filter(row => row.observed_ref === outputs[0].id).map(row => ({ id: row.id, verdict: humanize(row.verdict) + (row.reason_code ? ` · ${row.reason_code}` : '') })), 'Signal intake verdict differs from GTM API');
  return { board, outputs, checks };
}
function humanize(value) { return value.toLowerCase().replaceAll('_', ' '); }
async function verifyPipelineWall() {
  await station('wall');
  const [ledger, board] = await Promise.all([api('/api/engagements/gtm/ledger'), api('/api/engagements/gtm/board')]);
  const actual = await evaluate(() => ({
    groups: Object.fromEntries(['pipeline-owners', 'pipeline-clocks', 'pipeline-escalations', 'pipeline-incidents'].map(id => [id, [...document.querySelectorAll(`#${id} .pipeline-row`)].map(node => ({ ...node.dataset, provenance: node.querySelector('.evidence-meta')?.textContent ?? null, payload: node.querySelector('pre') ? JSON.parse(node.querySelector('pre').textContent) : null }))])),
    empties: Object.fromEntries(['pipeline-owners', 'pipeline-clocks', 'pipeline-escalations', 'pipeline-incidents'].map(id => [id, document.querySelector(`#${id} .empty`)?.textContent ?? null])),
    counts: document.getElementById('pipeline-counts').textContent,
    synthetic: document.querySelector('#pipeline-view .synthetic')?.textContent,
    operate: document.getElementById('operate-pipeline').disabled,
  }));
  const byType = type => ledger.events.filter(event => event.event_type === type);
  const shared = row => ({ signal: row.pipelineSignal ?? '', consequence: row.pipelineConsequence ?? '', weight: row.pipelineWeight ?? '', run: row.pipelineRun ?? '', check: row.pipelineCheck ?? '', output: row.pipelineOutput ?? '', synthetic: row.synthetic ?? '', type: row.pipelineType ?? '', event: row.pipelineEvent ?? '' });
  const groupKeys = { 'pipeline-owners': row => ({ ...shared(row), owner: row.pipelineOwner ?? '' }), 'pipeline-clocks': row => ({ ...shared(row), record: row.pipelineRecord ?? '' }), 'pipeline-escalations': row => ({ ...shared(row), terminal: row.pipelineTerminal ?? '' }) };
  const expectedShared = event => ({ signal: event.payload.signal_ref ?? '', consequence: event.payload.consequence ?? '', weight: String(event.payload.weight ?? ''), run: event.cause_refs[0] ?? '', check: event.cause_refs[1] ?? '', output: event.cause_refs[2] ?? '', synthetic: String(event.synthetic), type: event.event_type, event: String(event.seq) });
  const expectedKeys = { 'pipeline-owners': event => ({ ...expectedShared(event), owner: event.payload.owner ?? '' }), 'pipeline-clocks': event => ({ ...expectedShared(event), record: event.payload.record_ref ?? '' }), 'pipeline-escalations': event => ({ ...expectedShared(event), terminal: event.payload.terminal_action ?? '' }) };
  for (const [id, type] of [['pipeline-owners', 'OWNER_ASSIGNED'], ['pipeline-clocks', 'SLA_CLOCK_STARTED'], ['pipeline-escalations', 'HANDOFF_ESCALATED']]) {
    const rows = byType(type);
    assert.deepEqual(actual.groups[id].map(groupKeys[id]), rows.map(expectedKeys[id]), `Pipeline wall ${id} differs from recorded GTM API`);
    if (!rows.length) assert.equal(actual.empties[id], type === 'HANDOFF_ESCALATED'
      ? 'No operation recorded a human-handoff escalation. The compared workloads that do escalate are experiments, and an experiment never writes pipeline state.'
      : `No operation recorded ${humanize(type)}. Only operating the exact selection writes pipeline state.`, `Pipeline wall ${id} hides an absent consequence`);
    for (const row of actual.groups[id]) assert.deepEqual(row.payload, ledger.events.find(event => String(event.seq) === row.pipelineEvent).payload, 'Pipeline payload differs from recorded GTM API');
  }
  for (const [id, type] of [['pipeline-owners', 'OWNER_ASSIGNED'], ['pipeline-clocks', 'SLA_CLOCK_STARTED'], ['pipeline-escalations', 'HANDOFF_ESCALATED']]) {
    assert.deepEqual(actual.groups[id].map(row => row.provenance), byType(type).map(event => `Captured by run ${event.cause_refs[0]} · check ${event.cause_refs[1]} · output ${event.cause_refs[2]}`), `Pipeline provenance ${id} differs from recorded GTM API`);
  }
  const opened = byType('INCIDENT_OPENED');
  const resolved = byType('INCIDENT_RESOLVED');
  const normalizeIncidentRow = row => ({ incident: row.pipelineIncident ?? '', state: row.pipelineIncidentState ?? '', reason: row.pipelineIncidentReason ?? '', run: row.pipelineIncidentRun ?? row.pipelineRun ?? '', output: row.pipelineIncidentOutput ?? '', check: row.pipelineIncidentCheck ?? row.pipelineCheck ?? '', event: row.pipelineIncidentEvent ?? row.pipelineEvent ?? '', signal: row.pipelineSignal ?? '', tasks: row.pipelineFailedTasks ?? '', trace: row.pipelineTrace ?? '', version: row.pipelineResolvingVersion ?? '', synthetic: row.synthetic ?? '' });
  const expectedIncidents = board.incidents.map(incident => {
    const event = opened.find(item => item.seq === incident.opened_event_seq);
    return { incident: incident.id, state: incident.state, reason: incident.reason_code, run: incident.opening_run_id, output: incident.failing_output_ref, check: incident.check_result_id, event: String(incident.opened_event_seq), signal: event?.payload.signal_ref ?? '', tasks: (event?.payload.failed_task_ids ?? []).join(','), trace: String(event?.payload.decision_trace?.length ?? 0), version: '', synthetic: '' };
  });
  const expectedResolved = resolved.map(event => ({ incident: event.payload.incident_id, state: 'RESOLVED', reason: '', run: event.cause_refs[0], output: '', check: event.cause_refs[1], event: String(event.seq), signal: '', tasks: '', trace: '', version: event.payload.resolving_version_id, synthetic: String(event.synthetic) }));
  assert.deepEqual(actual.groups['pipeline-incidents'].map(normalizeIncidentRow), [...expectedIncidents, ...expectedResolved], 'Pipeline incidents differ from GTM API');
  assert.equal(actual.counts, `${board.incidents.length} unresolved of ${board.total_incidents} recorded in total · ${ledger.events.length} ledger events · chain ${humanize(board.chain_status)}`, 'Pipeline counts differ from GTM API');
  assert.equal(actual.synthetic, 'Synthetic scenario', 'GTM pipeline consequence lacks its synthetic label');
  return { ledger, board };
}
async function verifyComparison() {
  await station('workflow');
  const board = await api('/api/engagements/gtm/board');
  const investigation = await api(`/api/shifts/${board.latest_shift.id}/investigations`);
  const comparison = investigation.latest_experiment;
  const actual = await evaluate(() => ({ slots: [...document.querySelectorAll('#comparison-slots [data-run-id]')].map(node => node.dataset.runId), summary: document.getElementById('compare-summary').textContent, candidates: [...document.querySelectorAll('#candidate-list [data-candidate-label] strong')].map(node => node.textContent), mode: document.querySelector('[data-comparison-field="mode"] strong')?.textContent, history: document.querySelector('[data-comparison-field="history"] strong')?.textContent, budget: document.getElementById('assist-budget').textContent, roles: [...document.getElementById('assist-role').options].filter(option => !option.disabled).map(option => option.value), patchDisabled: [...document.getElementById('assist-role').options].find(option => option.value === 'PATCH_PROPOSAL')?.disabled }));
  assert.equal(comparison.state, 'FINALIZED');
  assert.equal(comparison.outcome.status, 'COMPLETE');
  assert.equal(actual.history, 'Unchanged by experiments', 'Experiment view does not state that history is unchanged');
  assert.deepEqual(actual.slots, comparison.trials.map(row => row.run_id), 'Comparison slot ownership differs from GTM API');
  assert.equal(actual.mode, comparison.context_evidence_class, 'Comparison mode differs from GTM API');
  const denominators = actual.summary.match(/public requests per candidate (\d+) · protected steps per candidate (\d+)/);
  assert.ok(denominators, 'Comparison summary lacks its denominator pair');
  assert.equal(Number(denominators[1]), comparison.shared_public_denominator_requests, 'Comparison public denominator differs from GTM API');
  assert.equal(Number(denominators[2]), comparison.protected_denominator_requests_per_candidate, 'Comparison protected denominator differs from GTM API');
  assert.deepEqual(actual.candidates, comparison.candidates.map(row => `${row.artifact_version_id} · content hash ${row.artifact_content_hash}`), 'Candidate identity differs from GTM API');
  assert.equal(actual.budget, `${investigation.assist_used} of ${investigation.assist_limit} help calls used this shift. Failed calls also count.`, 'Assistance budget differs from GTM API');
  assert.deepEqual(actual.roles, ['HINT', 'DIAGNOSIS'], 'GTM offers a forbidden assistance role');
  assert.equal(actual.patchDisabled, true, 'GTM offers a forbidden assistance role');
  const rendered = await evaluate(() => ({
    fields: Object.fromEntries([...document.querySelectorAll('[data-comparison-field]')].map(node => [node.dataset.comparisonField, node.querySelector('strong').textContent])),
    slots: [...document.querySelectorAll('#comparison-slots [data-run-id]')].map(node => ({
      run: node.dataset.runId, version: node.dataset.versionId, state: node.dataset.state,
      requests: [...node.querySelectorAll('.request-quote')].map(item => item.textContent),
      tasks: [...node.querySelectorAll('[data-task-id]')].map(item => ({ id: item.dataset.taskId, ordinal: item.dataset.requestOrdinal, outcome: item.dataset.outcome, verdict: item.dataset.verdict, text: item.querySelector('strong').textContent })),
    })),
    cards: [...document.querySelectorAll('.comparison-outcome-card')].map(node => ({ label: node.dataset.candidateLabel, eligible: node.dataset.eligible, header: node.querySelector('h4').textContent, metrics: Object.fromEntries([...node.querySelectorAll('[data-metric]')].map(item => [item.dataset.metric, item.textContent])) })),
  }));
  assert.equal(rendered.fields.purpose, humanize(comparison.kind), 'Comparison purpose differs from GTM API');
  assert.equal(rendered.fields.context, comparison.context_hash, 'Comparison context differs from GTM API');
  for (const [index, trial] of comparison.trials.entries()) {
    const slot = rendered.slots[index];
    assert.equal(slot.version, trial.artifact_version_id, 'Trial version differs from GTM API');
    assert.deepEqual(slot.requests, trial.outputs.map(output => `Request ${output.request_ordinal}: ${output.request_text}`), 'Trial request differs from GTM API');
    assert.deepEqual(slot.tasks, trial.task_assessments.map(row => ({ id: row.task_id, ordinal: String(row.request_ordinal), outcome: row.outcome, verdict: row.mandatory_pass ? 'pass' : 'fail', text: `${row.task_id} · ${humanize(row.outcome)}${row.reason_codes.length ? ` · ${row.reason_codes.join(', ')}` : ''}` })), 'Trial outcome differs from GTM API');
  }
  for (const metrics of comparison.outcome.candidate_metrics) {
    const eligibility = comparison.outcome.eligibility.find(row => row.candidate_label === metrics.candidate_label);
    const card = rendered.cards.find(row => row.label === metrics.candidate_label);
    assert.equal(card.eligible, String(eligibility.eligible), 'Candidate eligibility differs from GTM API');
    assert.equal(card.header, `Candidate ${metrics.candidate_label} · ${eligibility.eligible ? 'eligible' : 'blocked'}${eligibility.blocking_reason_codes.length ? ` · ${eligibility.blocking_reason_codes.join(', ')}` : ''}`, 'Candidate blocker differs from GTM API');
    assert.deepEqual(card.metrics, Object.fromEntries(Object.keys(card.metrics).map(key => [key, String(metrics[key] ?? 'unknown')])), 'Candidate metrics differ from GTM API');
  }
  return comparison;
}
async function verifyNext() {
  await station('wall');
  const board = await api('/api/engagements/gtm/board');
  const actual = await evaluate(() => ({ fields: Object.fromEntries([...document.querySelectorAll('[data-inherit-field]')].map(node => [node.dataset.inheritField, node.querySelector('strong').textContent])), note: document.querySelector('#next-view [data-synthetic-region="next-experiment"] .help-text')?.textContent }));
  const choice = board.operating_selection;
  assert.equal(actual.fields['operating-choice'], `${choice.id} · ${choice.selected_version_id} · ${humanize(choice.state)}`, 'Inherited choice differs from GTM API');
  assert.equal(actual.fields['selected-hash'], choice.selected_content_hash, 'Inherited choice differs from GTM API');
  assert.equal(actual.fields['retained-alternative'], choice.retained_alternative_version_id, 'Inherited alternative differs from GTM API');
  assert.equal(actual.fields['requirement-hash'], board.inherited_requirements.requirement_set_hash, 'Inherited requirement hash differs from GTM API');
  assert.ok(actual.note.includes('never rewrites the history above'), 'Experiment view does not state that history is unchanged');
  return choice;
}
async function verifyBinding(runId) {
  const [board, ledger] = await Promise.all([api('/api/engagements/gtm/board'), api('/api/engagements/gtm/ledger')]);
  const run = board.latest_run;
  assert.equal(run.id, runId, 'Latest run differs from the operated request id');
  const outputs = await api(`/api/runs/${run.id}/outputs`);
  const checks = await api(`/api/runs/${run.id}/checks`);
  await station('signals');
  const bound = await evaluate(() => ({ selection: document.querySelector('[data-selection-field="executed-version"] strong')?.textContent, evidence: document.querySelector('#selected-evidence .evidence-meta')?.textContent, runId: document.getElementById('selected-evidence').dataset.runId, ordinal: document.getElementById('selected-evidence').dataset.requestOrdinal, checks: [...document.querySelectorAll('#selected-evidence [data-check-id]')].map(node => node.dataset.checkId) }));
  assert.ok(bound.selection.includes(run.id) && bound.selection.includes(run.artifact_version_id), 'Room selection does not bind the operated run');
  assert.equal(bound.runId, run.id, 'Selected evidence does not bind the operated run');
  assert.ok(bound.evidence.includes(run.id), 'Workbench evidence does not bind the operated run');
  assert.deepEqual(new Set(checks.map(row => row.run_id)), new Set([run.id]), 'Checks do not bind the operated run');
  assert.deepEqual(new Set(checks.map(row => row.observed_ref)), new Set(outputs.map(row => row.id)), 'Checks do not bind the captured outputs');
  const generated = ledger.events.filter(event => event.cause_refs[0] === run.id && event.event_type !== 'INCIDENT_RESOLVED');
  assert.ok(generated.length > 0, 'No operational event binds the operated run');
  for (const event of generated) assert.ok(outputs.some(output => output.id === event.cause_refs[2]), 'Operational event does not bind a captured output');
  return { run, outputs, checks, ledger };
}
async function verifyRoom() {
  const boards = await api('/api/boards');
  const actual = await evaluate(() => ({ options: [...document.getElementById('workplace-board').options].map(option => ({ slug: option.value, disabled: option.disabled, label: option.textContent })), room: document.querySelector('.room').getAttribute('aria-label'), names: [...document.querySelectorAll('#gtm-stations button')].map(node => node.lastChild.textContent), visible: [...document.querySelectorAll('[data-station]')].filter(node => node.getClientRects().length).length, tabs: [...document.querySelectorAll('.file-tabs [data-file]')].filter(node => !node.hidden).map(node => node.dataset.file) }));
  assert.deepEqual(actual.options.map(row => row.slug), boards.map(row => row.engagement_slug), 'Workplace order differs from API');
  assert.deepEqual(actual.options.map(row => row.disabled), boards.map(row => row.availability !== 'AVAILABLE'), 'Workplace availability differs from API');
  assert.deepEqual(actual.options.map(row => row.label), boards.map(row => `${row.role_name} · ${row.client ?? row.employer}${row.availability === 'AVAILABLE' ? '' : ' · awaiting operator review'}`), 'Workplace display differs from API');
  assert.equal(actual.room, 'Stonebridge revenue floor', 'GTM opens the wrong room');
  assert.deepEqual(actual.names, ['Signal intake', 'Qualification rules', 'Workflow bench', 'Pipeline wall'], 'Native GTM station names differ from approved direction');
  assert.equal(actual.visible, 4, 'GTM exposes the wrong station count');
  assert.deepEqual(actual.tabs, ['contract', 'files'], 'GTM exposes draft files it does not own');
  await waitFor(() => document.getElementById('graphics-status').dataset.state === 'ready', 'Stonebridge real room did not render');
  assert.equal(await evaluate(() => Boolean(document.querySelector('#workplace-canvas canvas')) && getComputedStyle(document.getElementById('gtm-art')).display === 'none'), true, 'Stonebridge room did not replace its static fallback');
  await screenshot('stonebridge-room');
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
  assert.equal(scanned.clean, true, 'GTM DOM contains private material');
}

async function verifyWorkplaceGuards() {
  const before = await api('/api/engagements/gtm/ledger');
  await station('workflow');
  await evaluate(() => { const source = document.getElementById('draft-source'); source.value += '\n# unsaved control'; source.dispatchEvent(new Event('input')); });
  assert.equal(await evaluate(() => document.getElementById('workplace-board').disabled), true, 'Dirty draft permits board switching');
  await evaluate(() => { const select = document.getElementById('workplace-board'); select.value = 'bookshop'; select.dispatchEvent(new Event('change')); });
  assert.equal(await evaluate(() => document.getElementById('workplace-board').value), 'gtm', 'Dirty programmatic board switch was accepted');
  await click('discard-draft-edit');
  // Every registered board is admitted now, so fabricate one awaiting review to
  // prove the client still refuses to open an unreviewed board.
  await evaluate(async () => {
    const original = window.fetch; window.__originalFetch = original;
    window.fetch = async (...args) => {
      const response = await original(...args);
      if (args[0] !== '/api/boards') return response;
      const payload = (await response.clone().json()).map(row => row.engagement_slug === 'northline' ? { ...row, availability: 'AWAITING_OPERATOR_REVIEW' } : row);
      return new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } });
    };
    document.getElementById('refresh').click();
  });
  await waitFor(() => [...document.getElementById('workplace-board').options].some(option => option.value === 'northline' && option.textContent.includes('awaiting operator review')), 'Fabricated unreviewed board did not render');
  await verifyRoom();
  await evaluate(() => { const select = document.getElementById('workplace-board'); select.value = 'northline'; select.dispatchEvent(new Event('change')); });
  assert.equal(await evaluate(() => document.getElementById('workplace-board').value), 'gtm', 'Unreviewed programmatic board switch was accepted');
  await evaluate(() => { window.fetch = window.__originalFetch; document.getElementById('refresh').click(); });
  await waitFor(() => document.body.dataset.loadState === 'ready' && ![...document.getElementById('workplace-board').options].some(option => option.disabled), 'Real workplace list did not return');
  // Delay an old GTM board response while selecting Bellwether, then release it
  // after the newer board has rendered. No persisted rows change.
  await evaluate(() => {
    const original = window.fetch; window.__originalFetch = original;
    window.__oldBoardArrived = false; window.__oldBoardFinished = false;
    window.fetch = async (...args) => {
      const response = await original(...args);
      if (args[0] === '/api/engagements/gtm/board' && !window.__oldBoardArrived) {
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
  await waitFor(() => document.body.dataset.board === 'bookshop' && ['ready', 'empty'].includes(document.body.dataset.loadState), 'Bellwether did not load during old GTM refresh');
  await evaluate(() => window.__releaseOldBoard());
  await waitFor(() => window.__oldBoardFinished, 'Old board response was not released');
  assert.equal(await evaluate(() => document.body.dataset.board), 'bookshop', 'Old GTM refresh replaced newer Bellwether board');
  assert.equal(await evaluate(() => document.getElementById('candidate-list').textContent.includes('content hash')), false, 'Previous board candidates survived workplace switch');
  await evaluate(() => { window.fetch = window.__originalFetch; const select = document.getElementById('workplace-board'); select.value = 'gtm'; select.dispatchEvent(new Event('change')); });
  await waitFor(() => document.body.dataset.board === 'gtm' && document.body.dataset.loadState === 'ready', 'GTM did not return');
  assert.deepEqual(await api('/api/engagements/gtm/ledger'), before, 'Workplace navigation changed operational history');
  await verifyRoom();
}

async function verifyReach() {
  const stations = { signals: 'Signal intake', rules: 'Qualification rules', workflow: 'Workflow bench', wall: 'Pipeline wall' };
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  for (const width of [1280, 640, 390]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
    for (const [name, title] of Object.entries(stations)) {
      await evaluate(name => { const button = document.querySelector(`#gtm-stations [data-station="${name}"]`); button.scrollIntoView({ block: 'center', behavior: 'instant' }); button.focus({ preventScroll: true }); }, name);
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
      const reachable = await evaluate(async () => { await new Promise(resolve => setTimeout(resolve, 100)); const panel = document.getElementById('station-panel'); return { overflow: document.documentElement.scrollWidth > innerWidth, focus: document.activeElement === panel, top: panel.getBoundingClientRect().top, title: document.getElementById('panel-title').textContent }; });
      assert.equal(reachable.title, title, 'Keyboard did not activate the GTM station');
      assert.equal(reachable.overflow, false, `GTM overflows at ${width}px`);
      if (width === 390) {
        assert.equal(reachable.focus, true, 'Mobile station does not focus its panel');
        assert.ok(reachable.top >= 0 && reachable.top < 900, 'Mobile station panel is out of reach');
        await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 1 });
        const point = await evaluate(name => { const button = document.querySelector(`#gtm-stations [data-station="${name}"]`); button.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = button.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }, name);
        await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [point] });
        await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
        assert.equal(await evaluate(() => document.activeElement.id), 'station-panel', 'Mobile touch does not reach the selected panel');
        await send('Emulation.setTouchEmulationEnabled', { enabled: false });
      }
      await assertPublicDOM(`${width}-${name}`);
    }
    await station('wall'); await verifyPipelineWall(); await screenshot(`${width}-wall`);
    await evaluate(() => window.scrollTo(0, 0)); await screenshot(`${width}-floor`);
  }
}

const fault = process.env.SHIFTWORK_FAULT;
const FAULTS = {
  pipelineOwner: ['row.dataset.pipelineOwner = payload.owner ?? \'\';', 'row.dataset.pipelineOwner = \'wrong-owner\';', 'Pipeline wall pipeline-owners differs from recorded GTM API'],
  pipelineClock: ['row.dataset.pipelineRecord = payload.record_ref ?? \'\';', 'row.dataset.pipelineRecord = \'wrong-record\';', 'Pipeline wall pipeline-clocks differs from recorded GTM API'],
  pipelineResolving: ['row.dataset.pipelineResolvingVersion = event.payload.resolving_version_id;', 'row.dataset.pipelineResolvingVersion = \'wrong-version\';', 'Pipeline incidents differ from GTM API'],
  pipelineIncident: ['row.dataset.pipelineIncidentReason = incident.reason_code;', 'row.dataset.pipelineIncidentReason = \'WRONG_REASON\';', 'Pipeline incidents differ from GTM API'],
  pipelinePayload: ['element(\'pre\', JSON.stringify(payload, null, 2))', 'element(\'pre\', JSON.stringify({ ...payload, weight: 999 }, null, 2))', 'Pipeline payload differs from recorded GTM API'],
  pipelineProvenance: ['`Captured by run ${event.cause_refs[0]} · check ${event.cause_refs[1]} · output ${event.cause_refs[2]}`', '`Captured by run wrong-run · check ${event.cause_refs[1]} · output ${event.cause_refs[2]}`', 'Pipeline provenance pipeline-owners differs from recorded GTM API'],
  pipelineCounts: ['`${state.board.incidents.length} unresolved of ${state.board.total_incidents} recorded in total', '`0 unresolved of 0 recorded in total', 'Pipeline counts differ from GTM API'],
  pipelineSynthetic: ['$(\'operate-pipeline\').disabled = $(\'run-shift\').disabled;', '$(\'operate-pipeline\').disabled = $(\'run-shift\').disabled; document.querySelector(\'#pipeline-view .synthetic\').textContent = \'unlabelled\';', 'GTM pipeline consequence lacks its synthetic label'],
  escalationHonesty: ['? \'No operation recorded a human-handoff escalation. The compared workloads that do escalate are experiments, and an experiment never writes pipeline state.\'', '? \'Escalated to the SMB pod after one retry.\'', 'Pipeline wall pipeline-escalations hides an absent consequence'],
  stationNames: ['[\'Signal intake\', \'Qualification rules\', \'Workflow bench\', \'Pipeline wall\']);', '[\'Signal inbox\', \'Workflow\', \'Comparison bench\', \'Pipeline wall\']);', 'Native GTM station names differ from approved direction'],
  purpose: ['[\'purpose\', \'Execution purpose\', humanize(run.purpose)]', '[\'purpose\', \'Execution purpose\', \'experiment\']', 'Signal execution purpose differs from GTM API'],
  evidenceMode: ['[\'mode\', \'Evidence mode\', run.evidence_mode ?? \'unknown\'],', '[\'mode\', \'Evidence mode\', \'ISOLATED_LIVE\'],', 'Signal evidence mode differs from GTM API'],
  outputVersion: ['[\'version\', \'Executed version\', run.artifact_version_id]', '[\'version\', \'Executed version\', \'wrong-version\']', 'Signal intake execution version differs from GTM API'],
  selectedVersion: ['`${choice.selected_version_id} · ${choice.selected_content_hash} · ${humanize(choice.state)}`', '`wrong-version · ${choice.selected_content_hash} · ${humanize(choice.state)}`', 'Selected version differs from GTM API'],
  inheritance: ['[\'Live version\', \'operating-choice\', `${choice.id} · ${choice.selected_version_id} · ${humanize(choice.state)}`]', '[\'Live version\', \'operating-choice\', `wrong-choice · ${choice.selected_version_id} · ${humanize(choice.state)}`]', 'Inherited choice differs from GTM API'],
  experimentHistory: ['[\'history\', \'Operational history\', \'Unchanged by experiments\'],', '[\'history\', \'Operational history\', \'Rewritten by experiments\'],', 'Experiment view does not state that history is unchanged'],
  comparisonMode: ['[\'mode\', \'Evidence mode\', compare.context_evidence_class]', '[\'mode\', \'Evidence mode\', \'ISOLATED_LIVE\']', 'Comparison mode differs from GTM API'],
  comparisonDenominator: ['public requests per candidate ${compare.shared_public_denominator_requests}', 'public requests per candidate 999', 'Comparison public denominator differs from GTM API'],
  protectedDenominator: ['protected steps per candidate ${compare.protected_denominator_requests_per_candidate}', 'protected steps per candidate 999', 'Comparison protected denominator differs from GTM API'],
  candidateIdentity: ['`${version.id} · content hash ${version.content_hash}`', '`wrong-version · content hash ${version.content_hash}`', 'Candidate identity differs from GTM API'],
  trialOutcome: ['item.dataset.outcome = result.outcome;', 'item.dataset.outcome = \'WRONG_OUTCOME\';', 'Trial outcome differs from GTM API'],
  outcomeMetric: ['const value = element(\'dd\', metrics[key] ?? \'unknown\');', 'const value = element(\'dd\', key === \'useful_completions\' ? 999 : (metrics[key] ?? \'unknown\'));', 'Candidate metrics differ from GTM API'],
  falseBlocker: ['eligibility.blocking_reason_codes.length ? ` · ${eligibility.blocking_reason_codes.join(\', \')}` : \'\'', '\' · WRONG_BLOCKER\'', 'Candidate blocker differs from GTM API'],
  assistanceRole: ['option.disabled = !station?.assist_allowed_roles?.includes(option.value)', 'option.disabled = false', 'GTM offers a forbidden assistance role'],
  assistanceBudget: ['`${station.assist_used} of ${station.assist_limit} help calls used this shift. Failed calls also count.`', '`0 of 9 help calls used this shift. Failed calls also count.`', 'Assistance budget differs from GTM API'],
  availability: ['option.disabled = board.availability !== \'AVAILABLE\';', 'option.disabled = false;', 'Workplace availability differs from API'],
  dirtySwitch: ['state.pending || hasUnsavedDraft() || !state.workplaces.some', 'state.pending || false || !state.workplaces.some', 'Dirty programmatic board switch was accepted'],
  unreviewedSwitch: ['board.engagement_slug === slug && board.availability === \'AVAILABLE\'', 'board.engagement_slug === slug', 'Unreviewed programmatic board switch was accepted'],
  privateDOM: ['document.body.dataset.loadState = board.latest_shift ? \'ready\' : \'empty\';', 'document.body.dataset.loadState = board.latest_shift ? \'ready\' : \'empty\'; document.body.dataset.secret = \'S22B_TEST_PROVIDER_SECRET\';', 'GTM DOM contains private material'],
  mobileFocus: ['panel.focus({ preventScroll: true });', 'void panel;', 'Mobile station does not focus its panel'],
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
    await evaluate(() => { const select = document.getElementById('workplace-board'); select.value = 'gtm'; select.dispatchEvent(new Event('change')); });
    await waitFor(() => document.body.dataset.board === 'gtm' && ['ready', 'empty'].includes(document.body.dataset.loadState), 'Workplace did not open GTM');
  }
  await verifyRoom();
  if (snapshot === 'comparison') {
    await verifyComparison();
    await verifyWorkplaceGuards();
    await verifyComparison();
    await verifyPipelineWall();
  } else if (snapshot === 'closed' || snapshot === 'reach') {
    const operated = await verifyOutput();
    const executionVersion = await evaluate(() => document.querySelector('[data-execution-field="version"] strong')?.textContent);
    assert.equal(executionVersion, (await api('/api/engagements/gtm/board')).latest_run.artifact_version_id, 'Signal intake execution version differs from GTM API');
    await verifyPipelineWall();
    await verifyBinding(operated.board.latest_run.id);
    await verifyNext();
    if (snapshot === 'reach') await verifyReach();
  } else {
    await click('open-shift');
    await waitFor(() => document.body.dataset.loadState === 'ready' && !document.getElementById('run-shift').disabled, 'Pinned starter did not open');
    await click('run-shift');
    await waitFor(() => document.getElementById('run-state').textContent.includes('FINALIZED'), 'Pinned starter did not finalize', 60000);
    const starter = await verifyOutput();
    assert.ok(starter.checks.some(row => row.verdict === 'fail'), 'Pinned starter did not fail qualification');
    assert.equal(await evaluate(() => document.getElementById('run-shift').disabled), true, 'Starter shift permits a second operation');
    assert.equal(starter.board.attempts_used, 1, 'Starter operation was not counted');
    await station('workflow');
    await evaluate(() => { for (const [id, value] of [['cause-input', 'The starter ignores the region and product owner map.'], ['falsifier-input', 'The captured APAC output already names its APAC owner.'], ['public-test-input', 'Compare the captured owner and pipeline record with the frozen route.']]) document.getElementById(id).value = value; });
    await click('append-investigation');
    await waitFor(() => document.querySelectorAll('#investigation-list [data-investigation-id]').length === 1 && !document.getElementById('freeze-candidate-a').disabled, 'Investigation was not recorded');
    await evaluate(() => { document.getElementById('assist-message').value = 'Give one hint from this captured response.'; });
    await click('request-assist');
    await waitFor(() => document.querySelectorAll('#assist-events [data-assist-event-id]').length === 1 && !document.getElementById('draft-source').disabled && !document.getElementById('workplace-board').disabled, 'Recorded hint left editor controls disabled');
    await evaluate(() => document.querySelector('#assist-events button').click());
    await waitFor(() => !document.querySelector('#assist-events button') && !document.getElementById('draft-source').disabled && !document.getElementById('workplace-board').disabled, 'Hint decision left editor controls disabled');
    await evaluate(() => { const select = document.getElementById('assist-role'); select.value = 'DIAGNOSIS'; document.getElementById('assist-message').value = 'Check the recorded owner against the frozen route.'; });
    await click('request-assist');
    await waitFor(() => document.querySelectorAll('#assist-events [data-assist-event-id]').length === 2 && !document.getElementById('draft-source').disabled, 'Second GTM help call was not recorded');
    assert.equal(await evaluate(() => document.getElementById('request-assist').disabled), true, 'GTM permits a third help call');
    for (const label of ['A', 'B']) {
      await editFiles(fixture[label]);
      await click('freeze-candidate-' + label.toLowerCase());
      await waitFor(() => [...document.querySelectorAll('#candidate-list strong')].every(node => node.textContent !== 'not frozen yet') || document.querySelector('#candidate-list [data-candidate-label="A"] strong')?.textContent.startsWith('ver-'), `Candidate ${label} did not freeze`);
      await waitFor(() => !document.getElementById('draft-source').disabled, 'Freeze did not finish');
      const board = await api('/api/engagements/gtm/board');
      const saved = await api(`/api/artifact-versions/${board.latest_version.id}`);
      assert.deepEqual(saved.files, fixture[label], 'UI saved different candidate files');
    }
    await station('workflow');
    const beforeDiagnostic = await api('/api/engagements/gtm/ledger');
    await click('run-diagnostic');
    await waitFor(() => document.getElementById('investigate-error').textContent && !document.getElementById('draft-source').disabled && !document.getElementById('workplace-board').disabled, 'Diagnostic refusal left editor controls disabled', 15000);
    assert.equal(await evaluate(() => document.getElementById('investigate-error').textContent), 'only the pinned reviewed starter is executable as a public diagnostic candidate', 'Edited offline diagnostic bypassed its source guard');
    assert.deepEqual(await api('/api/engagements/gtm/ledger'), beforeDiagnostic, 'Diagnostic rewrote operational history');
    await evaluate(() => { const input = document.getElementById('treatment-input'); input.value = 'Rules-first review versus recorded-confidence routing.'; input.dispatchEvent(new Event('input')); });
    await click('run-comparison');
    await waitFor(() => document.getElementById('compare-summary').textContent.includes('COMPLETE') && !document.getElementById('draft-source').disabled, 'Six-slot comparison did not complete', 180000);
    const comparison = await verifyComparison();
    assert.equal(comparison.trials.length, 6);
    assert.ok(comparison.outcome.eligibility.every(row => row.eligible));
    await evaluate(async () => { const r = await fetch('/__test__/checkpoint/comparison', { method: 'POST' }); if (!r.ok) throw new Error('Comparison checkpoint failed'); });
    await click('open-choose-a');
    await evaluate(() => { const input = document.getElementById('selection-rationale'); input.value = 'Choose the independently eligible rules-first repair.'; input.dispatchEvent(new Event('input')); });
    await click('select-candidate-a');
    await waitFor(() => document.getElementById('selection-note').textContent.startsWith('Choice '), 'Explicit choice was not retained');
    const chosen = (await api('/api/engagements/gtm/board')).operating_selection;
    assert.equal(chosen.selected_version_id, comparison.candidates.find(row => row.label === 'A').artifact_version_id);
    await station('wall'); await click('close-shift');
    await waitFor(() => !document.getElementById('open-next-shift').disabled, 'First shift did not close');
    await click('open-next-shift');
    await waitFor(() => !document.getElementById('close-shift').disabled && !document.getElementById('run-shift').disabled, 'Selected next shift did not open');
    const inherited = await api('/api/engagements/gtm/board');
    assert.deepEqual((await api(`/api/shifts/${inherited.latest_shift.id}/artifact`)).files, fixture.A, 'Next shift did not inherit the selected workflow');
    await station('wall'); await click('operate-pipeline');
    await waitFor(() => document.getElementById('run-state').textContent.includes('FINALIZED') && document.querySelector('[data-selection-field="executed-version"] strong').textContent.split(' · ')[0] === document.querySelector('[data-selection-field="operating-choice"] strong').textContent.split(' · ')[0], 'Selected operation did not finalize', 60000);
    const operated = await verifyOutput();
    await waitFor(() => document.getElementById('shift-report').open, 'The completed operation did not open its report');
    await click('close-shift-report');
    await waitFor(() => !document.getElementById('shift-report').open && document.activeElement.id === 'open-shift-report', 'The report did not close and return focus');
    assert.equal(operated.board.latest_run.artifact_version_id, chosen.selected_version_id);
    assert.ok(operated.checks.every(row => row.verdict === 'pass'), 'Selected operation failed qualification');
    const operatedEvents = (await api('/api/engagements/gtm/ledger')).events.filter(row => row.cause_refs[0] === operated.board.latest_run.id);
    assert.deepEqual(operatedEvents.filter(row => row.event_type !== 'INCIDENT_RESOLVED').map(row => row.event_type), ['OWNER_ASSIGNED', 'SLA_CLOCK_STARTED']);
    assert.equal(operatedEvents.filter(row => row.event_type === 'INCIDENT_RESOLVED').length, 1, 'Operated repair did not resolve the traced incident');
    await verifyPipelineWall();
    await verifyBinding(operated.board.latest_run.id);
    await station('workflow'); await editFiles(fixture.B);
    await click('freeze-candidate-b'); await waitFor(() => !document.getElementById('draft-source').disabled, 'Newer save did not finish');
    await station('wall');
    await click('close-shift'); await waitFor(() => !document.getElementById('open-next-shift').disabled, 'Operated shift did not close');
    await verifyPipelineWall();
    await verifyNext();
    await evaluate(async () => { const r = await fetch('/__test__/checkpoint/closed', { method: 'POST' }); if (!r.ok) throw new Error('Closed checkpoint failed'); });
    await writeFile(path.join(out, 'journey.json'), JSON.stringify({ starter: starter.board.latest_run, comparison, choice: chosen, operation: operated.board.latest_run, ledger: await api('/api/engagements/gtm/ledger'), mode: 'TRUSTED_LOCAL', test_only_pins: false }, null, 2), { flag: 'wx' });
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
  assert.ok(path.basename(profile).startsWith('shiftwork-gtm-browser-'));
  await rm(profile, { recursive: true, force: true, maxRetries: 5 });
}
