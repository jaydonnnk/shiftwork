import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { openBrowser } from './workplace_browser.mjs';

const TERMINAL = ['FINALIZED', 'FAILED', 'INVALIDATED'];
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const candidateA = () => readFile('shiftwork/fixtures/artifacts/bookshop/compare_repair_a_service.py', 'utf8');
const candidateB = () => readFile('shiftwork/fixtures/artifacts/bookshop/compare_repair_b_service.py', 'utf8');

async function waitReady(browser, timeout = 120000) {
  return browser.until(() => document.body?.dataset.loadState === 'ready' &&
    document.getElementById('graphics-status')?.dataset.state === 'ready', timeout);
}
async function openBoard(browser, base, hash = '#board') {
  await browser.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  await browser.send('Page.navigate', { url: base + '/' + hash });
  assert.ok(await waitReady(browser), 'The S32 workbench was unavailable');
}
async function fetchJson(browser, path) {
  return browser.evaluate(async path => {
    const response = await fetch(path);
    return { ok: response.ok, status: response.status, body: response.ok ? await response.json() : await response.text() };
  }, path);
}
async function board(browser) { return (await fetchJson(browser, '/api/engagements/bookshop/board')).body; }
async function ledger(browser) { return (await fetchJson(browser, '/api/engagements/bookshop/ledger')).body; }
async function runRecord(browser, runId) { return (await fetchJson(browser, `/api/runs/${encodeURIComponent(runId)}`)).body; }
async function outputs(browser, runId) { return (await fetchJson(browser, `/api/runs/${encodeURIComponent(runId)}/outputs`)).body; }
async function checks(browser, runId) { return (await fetchJson(browser, `/api/runs/${encodeURIComponent(runId)}/checks`)).body; }
async function createInvestigation(browser, shiftId) {
  const setup = await browser.evaluate(async shiftId => {
    const response = await fetch(`/api/shifts/${encodeURIComponent(shiftId)}/investigations`, { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source_run_id: 'run-0001',
        source_request_ordinal: 1, cause: 'the starter asks instead of using the recorded public record',
        falsifier: 'a captured answer with the recorded price disproves this', public_test: 'compare the answer with the frozen public record',
        revision_of_id: null, client_request_id: `s32-owner-${Date.now()}-${Math.random().toString(36).slice(2)}` }) });
    return { ok: response.ok, status: response.status, text: await response.text() };
  }, shiftId);
  assert.ok(setup.ok, `Investigation setup failed (${setup.status}): ${setup.text}`);
  return JSON.parse(setup.text);
}
async function openCompare(browser) {
  await browser.evaluate(() => document.querySelector('[data-station="compare"]').click());
  assert.ok(await browser.until(() => !document.getElementById('compare-view').hidden, 30000), 'The Compare station did not open');
}
async function saveDraft(browser, source) {
  await browser.evaluate(source => {
    const file = document.getElementById('draft-file');
    if (file.value !== 'service.py') { file.value = 'service.py'; file.dispatchEvent(new Event('change')); }
    const editor = document.getElementById('draft-source');
    editor.value = source; editor.dispatchEvent(new Event('input'));
    if (document.getElementById('save-draft').disabled) throw Error('The draft editor refused the edit');
    document.getElementById('save-draft').click();
  }, source);
  assert.ok(await browser.until(() => document.getElementById('draft-source').dataset.dirty === 'false' &&
    document.body.dataset.loadState === 'ready' && !document.getElementById('freeze-candidate-a').disabled, 90000), 'The draft save did not settle');
}
async function freeze(browser, label) {
  const index = label === 'A' ? 0 : 1;
  await browser.evaluate(label => {
    const button = document.getElementById(`freeze-candidate-${label.toLowerCase()}`);
    if (button.disabled) throw Error('The freeze control is disabled');
    button.click();
  }, label);
  assert.ok(await browser.until(index => document.querySelectorAll('#candidate-list .contract-line strong')[index]?.textContent.includes('· content hash'), 90000, index), `Candidate ${label} did not freeze`);
  assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready' &&
    !document.getElementById('freeze-candidate-a').disabled && !document.getElementById('freeze-candidate-b').disabled, 90000), `Candidate ${label} freeze did not settle`);
}
async function setupComparison(browser) {
  const before = await board(browser);
  assert.ok(before.latest_shift?.id, 'The preview has no open shift');
  await createInvestigation(browser, before.latest_shift.id);
  await browser.evaluate(() => globalThis.__s29Refresh());
  assert.ok(await waitReady(browser), 'Owner setup refresh failed');
  await openCompare(browser);
  await saveDraft(browser, await candidateA());
  await freeze(browser, 'A');
  await saveDraft(browser, await candidateB());
  await freeze(browser, 'B');
  await browser.evaluate(() => {
    const field = document.getElementById('treatment-input');
    field.value = 'A resolves each task before answering; B plans the tasks first and reads the optional price only when asked';
    field.dispatchEvent(new Event('input'));
    if (document.getElementById('run-comparison').disabled) throw Error('The comparison control stayed disabled');
    document.getElementById('run-comparison').click();
  });
  return before;
}
async function comparisonToTerminal(browser) {
  assert.ok(await browser.until(() => globalThis.__s31Initial?.state, 120000), 'The comparison POST did not return');
  const initial = await browser.evaluate(() => globalThis.__s31Initial);
  assert.ok(initial?.id, 'The comparison POST returned no experiment identity');
  let payload = null;
  const deadline = Date.now() + 180000;
  while (Date.now() < deadline) {
    const current = (await fetchJson(browser, `/api/experiments/${encodeURIComponent(initial.id)}`)).body;
    if (current?.state && TERMINAL.includes(current.state)) { payload = current; break; }
    await sleep(500);
  }
  assert.ok(payload, 'The comparison did not reach a terminal state');
  assert.equal(payload.outcome?.status, 'COMPLETE', 'The comparison did not complete comparably');
  await browser.until(() => document.body.dataset.loadState === 'ready' &&
    document.querySelectorAll('#comparison-slots .comparison-slot').length === 6, 180000);
  return payload;
}
async function chooseVersion(browser, label) {
  await browser.evaluate(label => {
    const field = document.getElementById('selection-rationale');
    field.value = `Candidate ${label} answered every shared task in the frozen comparison.`;
    field.dispatchEvent(new Event('input'));
    const button = document.getElementById(`select-candidate-${label.toLowerCase()}`);
    if (button.disabled) throw Error('The explicit choice stayed disabled');
    button.click();
  }, label);
  assert.ok(await browser.until(() => document.getElementById('selection-note').textContent.startsWith('Choice '), 90000), 'The explicit choice was not recorded');
  assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready', 90000), 'The choice refresh did not settle');
  return (await board(browser)).operating_selection;
}
async function advanceToOperatingShift(browser) {
  const before = await board(browser);
  const priorShift = before.latest_shift.id;
  await browser.evaluate(() => document.querySelector('[data-view="next"]').click());
  assert.ok(await browser.until(() => !document.getElementById('close-shift').disabled, 60000), 'The chosen version cannot be closed');
  await browser.evaluate(() => document.getElementById('close-shift').click());
  assert.ok(await browser.until(() => !document.getElementById('open-next-shift').disabled, 60000), 'The closed shift offers no next shift');
  await browser.evaluate(() => document.getElementById('open-next-shift').click());
  assert.ok(await browser.until(async priorShift => {
    const next = await (await fetch('/api/engagements/bookshop/board')).json();
    return next.latest_shift?.id && next.latest_shift.id !== priorShift && document.body.dataset.loadState === 'ready';
  }, 90000, priorShift), 'The operating shift did not open');
  assert.ok(await waitReady(browser), 'The operating shift scene did not settle before operation');
  await browser.evaluate(() => document.querySelector('[data-view="board"]').click());
  return (await board(browser)).latest_shift.id;
}
async function operate(browser) {
  const before = await board(browser);
  assert.ok(await browser.evaluate(() => !document.getElementById('run-shift').disabled), 'The selected version cannot operate');
  await browser.evaluate(() => document.getElementById('run-shift').click());
  assert.ok(await browser.until(async before => {
    const next = await (await fetch('/api/engagements/bookshop/board')).json();
    return next.latest_run?.id && next.latest_run.id !== before.latest_run?.id &&
      ['FINALIZED', 'FAILED'].includes(next.latest_run.state) && document.body.dataset.loadState === 'ready';
  }, 120000, before), 'The operation did not reach a terminal state');
  const terminal = await board(browser);
  assert.ok(await browser.until(state => document.getElementById('wall-status').dataset.runState === state,
    120000, terminal.latest_run.state), 'The wall did not publish the terminal operation state');
  return board(browser);
}
async function prepareOperatingShift(browser) {
  await setupComparison(browser);
  await comparisonToTerminal(browser);
  const selection = await chooseVersion(browser, 'A');
  assert.ok(selection?.id, 'The explicit choice was not recorded');
  return advanceToOperatingShift(browser);
}
async function sceneState(browser) {
  return browser.evaluate(() => ({ ...globalThis.__workplaceControls.state(), arrivals: globalThis.__s32Arrivals ?? [] }));
}
async function wallSnapshot(browser) {
  return browser.evaluate(() => ({
    rows: [...document.querySelectorAll('#wall-events .wall-event')].map(row => ({
      event: row.dataset.wallEvent, seq: row.dataset.wallSeq, type: row.dataset.wallType,
      source: row.dataset.wallSource, link: row.dataset.wallLink, meaning: row.dataset.wallMeaning,
      synthetic: row.dataset.synthetic, incident: row.dataset.wallIncident ?? null,
      version: row.dataset.wallVersion ?? null, run: row.dataset.wallRun ?? null,
      check: row.dataset.wallCheck ?? null, output: row.dataset.wallOutput ?? null,
      ordinal: row.dataset.wallOrdinal ?? null, verdict: row.dataset.wallVerdict ?? null,
      reason: row.dataset.wallReason ?? null, text: row.textContent })),
    totals: [...document.querySelectorAll('#ledger-totals .total-row')].map(row => ({ type: row.dataset.ledgerType, count: row.dataset.ledgerCount })),
    status: { ...document.getElementById('wall-status').dataset, text: document.getElementById('wall-status').textContent },
    trace: { state: document.getElementById('wall-trace').dataset.state, text: document.getElementById('wall-trace').textContent },
    incidents: [...document.querySelectorAll('#incident-list .incident-row')].map(row => ({
      id: row.dataset.incidentId, state: row.dataset.incidentState, source: row.dataset.incidentSource,
      openedEventSeq: row.dataset.openedEventSeq, openingRun: row.dataset.openingRun,
      output: row.dataset.failingOutput, check: row.dataset.checkResult, text: row.textContent })),
    evidence: [...document.querySelectorAll('#selected-evidence .event-row')].map(row => ({
      seq: row.dataset.eventSeq, source: row.dataset.eventSource, meaning: row.dataset.eventMeaning,
      incident: row.dataset.incidentId ?? null, text: row.textContent })),
    verdict: document.getElementById('inspection-verdict').textContent,
  }));
}
function eventId(slug, event) { return `${slug}:${event.seq}:${event.hash}`; }
async function assertWallMatchesPublic(browser, snapshot, boardView, ledgerView, runId) {
  const run = await runRecord(browser, runId);
  const runChecks = await checks(browser, runId);
  const runOutputs = await outputs(browser, runId);
  assert.equal(snapshot.status.runState, run.state, 'The wall shows a different run state');
  assert.equal(snapshot.status.chain, 'VALID', 'The wall lost the ledger chain status');
  assert.equal(snapshot.status.countMatches, String(boardView.ledger_event_count === ledgerView.events.length), 'The wall hides the count agreement');
  assert.equal(snapshot.status.histogramMatches, 'true', 'The wall hides the type-histogram disagreement');
  const expectedTotals = Object.entries(boardView.ledger_totals).map(([type, count]) => ({ type, count: String(count) }))
    .sort((a, b) => a.type.localeCompare(b.type));
  assert.deepEqual([...snapshot.totals].sort((a, b) => a.type.localeCompare(b.type)), expectedTotals, 'The wall totals differ from the public ledger totals');
  const runEvents = ledgerView.events.filter(event => event.derivation?.run_id === run.id);
  for (const event of runEvents) {
    const row = snapshot.rows.find(item => item.event === eventId('bookshop', event));
    assert.ok(row, `The wall hides the linked event ${event.seq}`);
    assert.equal(row.source, 'current', 'A linked operational event is not labelled current');
    assert.equal(row.link, 'linked', 'A linked operational event is not labelled linked');
    assert.equal(row.synthetic, 'true');
    assert.equal(row.run, event.derivation.run_id);
    assert.equal(row.check, event.derivation.check_id);
    assert.equal(row.output, event.derivation.observed_ref);
    assert.equal(row.ordinal, String(event.derivation.request_ordinal));
    assert.equal(row.verdict, event.derivation.verdict);
    assert.equal(row.type, event.event_type);
    assert.equal(row.meaning, event.derivation.verdict === 'pass' ? 'recorded' : 'negative');
    const incident = boardView.incidents.find(item => item.opened_event_seq === event.seq);
    if (incident) assert.equal(row.incident, incident.id, 'The wall hides the linked incident identity');
  }
  const selected = snapshot.rows.filter(row => row.source === 'current');
  assert.equal(selected.length, runEvents.length, 'The wall shows a different number of current events');
  const incidentRows = snapshot.incidents;
  for (const incident of boardView.incidents) {
    const tab = incidentRows.find(item => item.id === incident.id);
    assert.ok(tab, `The incident tab ${incident.id} is missing`);
    assert.equal(tab.openingRun, incident.opening_run_id);
    assert.equal(tab.openedEventSeq, String(incident.opened_event_seq));
    assert.equal(tab.output, incident.failing_output_ref);
    assert.equal(tab.check, incident.check_result_id);
    const current = incident.opening_run_id === run.id;
    assert.equal(tab.source, current ? 'current' : 'historical', `Incident ${incident.id} has the wrong source label`);
  }
  return { run, checks: runChecks, outputs: runOutputs };
}
function assertSingleTrace(scene, arrivals, label, count = 1) {
  assert.equal(scene.wallTraces, 1, 'The linked consequence produced no single scene trace');
  assert.deepEqual(scene.wallDurations, [320], 'The evidence trace did not use 320ms');
  assert.deepEqual(scene.wallCounts, [count], 'The evidence trace carried the wrong arrival count');
  assert.equal(arrivals.length, 1, 'The consequence callback did not fire exactly once');
  assert.equal(arrivals[0].count, count, 'The consequence callback hid a multiple arrival');
  assert.equal(label.state, 'active', 'The recorded-evidence trace is not labelled as active');
  assert.ok(label.text.includes('Recorded evidence added'), 'The trace label text is missing');
  if (count > 1) assert.ok(label.text.includes(`${count} events`), 'The trace label hides the multiple arrival count');
}
async function quietCounts(browser) {
  const scene = await sceneState(browser);
  return { traces: scene.wallTraces ?? 0, arrivals: scene.arrivals.length };
}
async function assertQuiet(browser, before, name) {
  const after = await quietCounts(browser);
  assert.deepEqual(after, before, `${name} replayed the recorded evidence arrival`);
}
async function screenshot(browser, out, name) {
  const { data } = await browser.send('Page.captureScreenshot', { format: 'png' });
  await writeFile(`${out}/${name}.png`, Buffer.from(data, 'base64'));
}

export async function runJourney(base, out, fault = '') {
  const browser = await openBrowser(base, out, fault || 's32-journey');
  try {
    await openBoard(browser, base);
    const shiftId = await prepareOperatingShift(browser);
    const finalBoard = await operate(browser);
    const runId = finalBoard.latest_run.id;
    const run = await runRecord(browser, runId);
    assert.equal(run.purpose, 'OPERATION');
    assert.equal(run.selection_id, finalBoard.operating_selection.id);
    assert.equal(run.artifact_version_id, finalBoard.operating_selection.selected_version_id);
    const publicBoard = await board(browser);
    const publicLedger = await ledger(browser);
    const records = await assertWallMatchesPublic(browser, await wallSnapshot(browser), publicBoard, publicLedger, runId);
    assert.deepEqual(run, records.run);
    const scene = await sceneState(browser);
    const snapshot = await wallSnapshot(browser);
    assertSingleTrace(scene, scene.arrivals, snapshot.trace, 1);
    assert.equal(publicLedger.events.filter(event => event.derivation?.run_id === runId).length, 1, 'The normal operation wrote more than one event');
    assert.equal(publicBoard.chain_status, 'VALID');
    assert.equal(snapshot.status.text.includes(`Operation ${runId} · FINALIZED`), true, 'The wall hides the finalized operation');
    assert.equal(snapshot.status.text.includes('Counts agree'), true, 'The wall does not state count agreement');
    assert.equal(snapshot.status.text.includes('Type totals agree'), true, 'The wall does not state histogram agreement');
    assert.equal(snapshot.status.text.includes('failed mandatory'), false, 'A successful operation claims a failed task');
    assert.ok(snapshot.rows.some(row => row.type === 'SALE_COMPLETED' && row.meaning === 'recorded'), 'The linked sale is not visible');
    assert.ok(snapshot.rows.some(row => row.source === 'historical' && row.incident), 'Historical incident records were dropped');
    assert.ok(snapshot.rows.some(row => row.source === 'administrative' && row.type === 'LIMIT_DECLARED'), 'Administrative records were promoted');
    assert.ok(snapshot.evidence.some(row => row.source === 'current' && row.meaning === 'recorded'), 'The selected evidence bridge lost the current consequence');
    const evidence = await browser.evaluate(runId => [...document.querySelectorAll('#selected-evidence .event-row')].map(row => row.textContent), runId);
    assert.ok(evidence.some(text => text.includes('Current operation record')), 'The selected evidence bridge hides its current source label');
    assert.equal(await browser.evaluate(() => document.body.dataset.evidence), 'finalized');
    const quiet = await quietCounts(browser);
    await browser.evaluate(() => globalThis.__s29Refresh());
    assert.ok(await waitReady(browser), 'The duplicate refresh did not settle');
    await assertQuiet(browser, quiet, 'A duplicate refresh');
    await browser.evaluate(() => document.querySelector('[data-station="customers"]').click());
    assert.ok(await browser.until(() => !document.getElementById('customer-view').hidden, 30000), 'The customer evidence station did not open');
    await assertQuiet(browser, quiet, 'Output inspection');
    await browser.evaluate(() => document.querySelector('.incident-row').click());
    assert.ok(await browser.until(() => document.getElementById('run-state').textContent.includes('run-0001'), 60000), 'The historical incident did not load');
    await assertQuiet(browser, quiet, 'Historical inspection');
    await browser.evaluate(() => document.getElementById('refresh').click());
    assert.ok(await waitReady(browser), 'The return to current did not settle');
    await assertQuiet(browser, quiet, 'Returning to current');
    const origin = await browser.evaluate(() => performance.timeOrigin);
    await browser.send('Page.reload');
    assert.ok(await browser.until(old => performance.timeOrigin !== old && document.body?.dataset.loadState === 'ready' &&
      document.getElementById('graphics-status')?.dataset.state === 'ready', 120000, origin), 'The first-load reload did not settle');
    const firstLoad = await sceneState(browser);
    const firstSnapshot = await wallSnapshot(browser);
    assert.equal(firstLoad.wallTraces ?? 0, 0, 'First load replayed the recorded evidence arrival');
    assert.equal(firstSnapshot.trace.state, 'idle', 'First load left the trace label active');
    assert.ok(firstSnapshot.rows.some(row => row.source === 'current' && row.type === 'SALE_COMPLETED'), 'First load dropped the recorded sale');
    const pageCacheQuiet = { traces: 0, arrivals: 0 };
    const history = await browser.send('Page.getNavigationHistory');
    await browser.send('Page.navigate', { url: base + '/room.svg' });
    assert.ok(await browser.until(() => location.pathname === '/room.svg'), 'The away document did not load');
    await browser.send('Page.navigateToHistoryEntry', { entryId: history.entries[history.currentIndex].id });
    assert.ok(await browser.until(() => document.body?.dataset.loadState === 'ready' &&
      document.getElementById('graphics-status')?.dataset.state === 'ready', 120000), 'The page-cache return did not settle');
    await assertQuiet(browser, pageCacheQuiet, 'Page-cache return');
    await browser.evaluate(() => {
      globalThis.__s32Hidden = { events: 0 };
      Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
      dispatchEvent(new Event('visibilitychange'));
    });
    await sleep(80);
    await browser.evaluate(() => {
      Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
      dispatchEvent(new Event('visibilitychange'));
    });
    await sleep(80);
    await assertQuiet(browser, pageCacheQuiet, 'Hidden return');
    await browser.evaluate(() => {
      const canvas = document.querySelector('#workplace-canvas canvas');
      canvas.getContext('webgl2').getExtension('WEBGL_lose_context').loseContext();
    });
    assert.ok(await browser.until(() => document.getElementById('graphics-status')?.dataset.state === 'unavailable', 30000), 'Graphics loss did not settle');
    const lost = await wallSnapshot(browser);
    assert.ok(lost.rows.some(row => row.source === 'current' && row.type === 'SALE_COMPLETED'), 'Graphics loss erased the recorded consequence');
    const complete = await browser.evaluate(() => ({ wall: Boolean(document.querySelector('#wall-events .wall-event')),
      refresh: !document.getElementById('refresh').disabled,
      customers: !document.querySelector('[data-station="customers"]').disabled }));
    assert.deepEqual(complete, { wall: true, refresh: true, customers: true }, 'Graphics loss disabled the complete workbench');
    await browser.evaluate(() => document.getElementById('wall-status').scrollIntoView({ block: 'center' }));
    await sleep(150);
    await screenshot(browser, out, 'wall-fallback-1280');
    await browser.evaluate(() => document.querySelector('[data-graphics-retry]').click());
    assert.ok(await browser.until(() => document.getElementById('graphics-status')?.dataset.state === 'ready', 120000), 'The graphics retry did not settle');
    await assertQuiet(browser, pageCacheQuiet, 'Graphics retry');
    await browser.send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
    await browser.evaluate(() => document.getElementById('refresh').click());
    assert.ok(await browser.until(() => document.body.dataset.loadState === 'error' ||
      document.getElementById('graphics-status')?.dataset.state === 'unavailable' ||
      document.getElementById('workplace-state').textContent.includes('unavailable'), 60000), 'The offline refresh did not surface an error');
    await browser.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
    await browser.evaluate(() => document.getElementById('refresh').click());
    assert.ok(await waitReady(browser), 'Error recovery did not settle');
    await assertQuiet(browser, pageCacheQuiet, 'Error recovery');
    const recovered = await wallSnapshot(browser);
    assert.ok(recovered.rows.some(row => row.source === 'current' && row.type === 'SALE_COMPLETED'), 'Error recovery dropped the recorded sale');
    await browser.evaluate(() => document.querySelector('[data-station="ledger"]').click());
    assert.ok(await browser.until(() => !document.getElementById('board-view').hidden, 30000));
    await browser.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    await browser.evaluate(() => document.getElementById('wall-status').scrollIntoView({ block: 'center' }));
    await sleep(150);
    await screenshot(browser, out, 'wall-1280');
    for (const [width, height] of [[640, 900], [390, 844]]) {
      await browser.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
      await sleep(120);
      const layout = await browser.evaluate(() => ({
        overflow: document.documentElement.scrollWidth <= innerWidth,
        wallVisible: Boolean(document.querySelector('#wall-events .wall-event')),
        statusVisible: document.getElementById('wall-status').getBoundingClientRect().height > 0,
      }));
      assert.deepEqual(layout, { overflow: true, wallVisible: true, statusVisible: true }, `The ${width}px wall layout is not readable`);
    }
    await browser.send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: false });
    await browser.evaluate(() => document.getElementById('wall-status').scrollIntoView({ block: 'center' }));
    await sleep(150);
    await screenshot(browser, out, 'wall-390');
    assert.deepEqual(browser.exceptions, [], 'The S32 journey raised an uncaught exception');
    await writeFile(out + '/journey.json', JSON.stringify({ run: records.run, checks: records.checks, outputs: records.outputs,
      board: { totals: publicBoard.ledger_totals, incidents: publicBoard.incidents.map(item => item.id) },
      events: publicLedger.events.map(event => ({ seq: event.seq, type: event.event_type, derivation: event.derivation && event.derivation.run_id })),
      wall: snapshot, scene: { wallTraces: scene.wallTraces, wallDurations: scene.wallDurations, wallCounts: scene.wallCounts, wall: scene.wall },
      quiet: { before: quiet, afterReload: firstLoad.wallTraces ?? 0 } }, null, 2) + '\n');
    return { result: 'PASS', run: runId, state: run.state, events: publicLedger.events.length, trace: scene.wallDurations };
  } finally { await browser.close(); }
}

export async function runQueued(base, out) {
  const browser = await openBrowser(base, out, 'operation-queued');
  try {
    await openBoard(browser, base);
    await prepareOperatingShift(browser);
    const before = await board(browser);
    assert.ok(await browser.evaluate(() => !document.getElementById('run-shift').disabled), 'The selected version cannot operate');
    await browser.evaluate(() => document.getElementById('run-shift').click());
    assert.ok(await browser.until(async before => {
      const current = await (await fetch('/api/engagements/bookshop/board')).json();
      return current.latest_run?.id && current.latest_run.id !== before.latest_run?.id && current.latest_run.state === 'QUEUED';
    }, 60000, before), 'The operation never published a queued run');
    await browser.evaluate(() => globalThis.__s29Refresh());
    assert.ok(await waitReady(browser), 'The queued refresh did not settle');
    const queued = await wallSnapshot(browser);
    assert.ok(queued.status.text.includes('QUEUED') && queued.status.text.includes('Pending'), 'The wall hides the queued state');
    assert.equal(queued.rows.filter(row => row.source === 'current').length, 0, 'A queued run produced a current consequence');
    assert.equal((await sceneState(browser)).wallTraces ?? 0, 0, 'A queued run produced an arrival trace');
    assert.ok(await browser.until(async before => {
      const current = await (await fetch('/api/engagements/bookshop/board')).json();
      return current.latest_run?.id === before && current.latest_run.state === 'RUNNING';
    }, 60000, (await board(browser)).latest_run.id), 'The operation never published a running run');
    await browser.evaluate(() => globalThis.__s29Refresh());
    assert.ok(await waitReady(browser), 'The running refresh did not settle');
    const running = await wallSnapshot(browser);
    assert.ok(running.status.text.includes('RUNNING') && running.status.text.includes('Pending'), 'The wall hides the running state');
    assert.equal(running.rows.filter(row => row.source === 'current').length, 0, 'A running run produced a current consequence');
    assert.equal((await sceneState(browser)).wallTraces ?? 0, 0, 'A running run produced an arrival trace');
    assert.ok(await browser.until(async before => {
      const current = await (await fetch('/api/engagements/bookshop/board')).json();
      return current.latest_run?.state === 'FINALIZED' && document.body.dataset.loadState === 'ready';
    }, 120000), 'The delayed operation did not finalize');
    await browser.evaluate(() => globalThis.__s29Refresh());
    assert.ok(await waitReady(browser), 'The finalized refresh did not settle');
    awaitWallCurrent(browser);
    const after = await wallSnapshot(browser);
    assert.ok(after.status.text.includes('FINALIZED'), 'The finalized state is hidden');
    assert.ok(after.rows.some(row => row.source === 'current' && row.link === 'linked'), 'The finalized operation did not add a linked consequence');
    const scene = await sceneState(browser);
    assertSingleTrace(scene, scene.arrivals, after.trace, 1);
    await writeFile(out + '/queued.json', JSON.stringify({ queued, running, after, traces: scene.wallTraces }, null, 2) + '\n');
    return { result: 'PASS', queued: true, running: true, traces: scene.wallTraces };
  } finally { await browser.close(); }
}
async function awaitWallCurrent(browser) {
  assert.ok(await browser.until(() => document.querySelector('#wall-events .wall-event[data-wall-source="current"]'), 30000), 'The wall did not render a current consequence');
}

export async function runFailedTask(base, out, fault = '') {
  const browser = await openBrowser(base, out, fault || 'operation-failed-task');
  try {
    await openBoard(browser, base);
    await prepareOperatingShift(browser);
    const finalBoard = await operate(browser);
    assert.equal(finalBoard.latest_run.state, 'FINALIZED');
    const runId = finalBoard.latest_run.id;
    const runChecks = await checks(browser, runId);
    assert.equal(runChecks.length, 3);
    assert.equal(runChecks.every(check => check.verdict === 'fail'), true, 'The failed-task preview did not fail every mandatory check');
    const publicBoard = await board(browser);
    const publicLedger = await ledger(browser);
    const snapshot = await wallSnapshot(browser);
    await assertWallMatchesPublic(browser, snapshot, publicBoard, publicLedger, runId);
    assert.ok(snapshot.status.text.includes('Finalized with 3 failed mandatory checks'), 'The wall hides the failed mandatory task');
    assert.equal(snapshot.rows.some(row => row.source === 'current' && row.type === 'SALE_COMPLETED'), false, 'A failed mandatory task produced a sale');
    const current = snapshot.rows.filter(row => row.source === 'current');
    assert.equal(current.length, 2, 'The failed operation did not preserve both linked negative events');
    assert.equal(current.every(row => row.meaning === 'negative' && row.verdict === 'fail' && row.incident), true, 'A negative consequence was promoted or lost its incident join');
    assert.deepEqual(snapshot.incidents.filter(item => item.source === 'current').map(item => item.id).sort(),
      current.map(row => row.incident).sort(), 'The current incident tabs do not join the current events');
    const scene = await sceneState(browser);
    assertSingleTrace(scene, scene.arrivals, snapshot.trace, 2);
    await browser.evaluate(() => document.querySelector('[data-station="customers"]').click());
    const evidence = await browser.evaluate(() => [...document.querySelectorAll('#selected-evidence .result-row')].map(row => ({ verdict: row.dataset.verdict, id: row.dataset.checkId })));
    assert.equal(evidence.length, 3);
    assert.equal(evidence.every(item => item.verdict === 'fail'), true, 'The selected evidence bridge hides the failed checks');
    const selectedEvents = await browser.evaluate(() => [...document.querySelectorAll('#selected-evidence .event-row')].map(row => ({ source: row.dataset.eventSource, meaning: row.dataset.eventMeaning })));
    assert.equal(selectedEvents.every(item => item.source === 'current' && item.meaning === 'negative'), true, 'The selected evidence bridge promotes a negative event');
    await writeFile(out + '/failed.json', JSON.stringify({ run: runId, checks: runChecks, wall: snapshot, scene: { traces: scene.wallTraces, durations: scene.wallDurations, counts: scene.wallCounts }, evidence }, null, 2) + '\n');
    return { result: 'PASS', run: runId, current: current.length, trace: scene.wallDurations };
  } finally { await browser.close(); }
}

export async function runMissing(base, out) {
  const browser = await openBrowser(base, out, 'operation-missing');
  try {
    await openBoard(browser, base);
    await prepareOperatingShift(browser);
    const finalBoard = await operate(browser);
    assert.equal(finalBoard.latest_run.state, 'FAILED');
    const runId = finalBoard.latest_run.id;
    assert.equal(finalBoard.latest_run.failure_kind, 'SERVICE_UNREACHABLE');
    const runChecks = await checks(browser, runId);
    assert.equal(runChecks.length, 0, 'The missing-checks preview captured checks');
    const publicBoard = await board(browser);
    const publicLedger = await ledger(browser);
    const snapshot = await wallSnapshot(browser);
    assert.ok(snapshot.status.text.includes(`Operation ${runId} · FAILED · service unreachable`), 'The wall hides the failed run');
    assert.ok(snapshot.status.text.includes('Failed. Confirmed records stay visible'), 'The wall implies a success for a failed run');
    assert.equal(snapshot.rows.some(row => row.source === 'current'), false, 'A failed run without captures invented a current consequence');
    assert.equal(snapshot.rows.filter(row => row.source === 'historical').length, 3, 'The failed run erased historical consequences');
    assert.equal((await sceneState(browser)).wallTraces ?? 0, 0, 'A failed run without new evidence produced an arrival');
    assert.equal(await browser.evaluate(() => document.getElementById('inspection-verdict').textContent), 'Independent evidence incomplete.');
    const evidence = await browser.evaluate(() => [...document.querySelectorAll('#selected-evidence .event-row')].length);
    assert.equal(evidence, 0, 'The missing evidence bridge invented an event');
    assert.deepEqual(publicBoard.ledger_totals, { INCIDENT_OPENED: 3, LIMIT_DECLARED: 1 });
    assert.equal(publicBoard.ledger_event_count, publicLedger.events.length);
    await writeFile(out + '/missing.json', JSON.stringify({ run: runId, checks: runChecks, wall: snapshot, totals: publicBoard.ledger_totals }, null, 2) + '\n');
    return { result: 'PASS', run: runId, state: finalBoard.latest_run.state, current: 0 };
  } finally { await browser.close(); }
}

export async function runPartial(base, out) {
  const browser = await openBrowser(base, out, 'operation-partial');
  try {
    await openBoard(browser, base);
    await prepareOperatingShift(browser);
    const finalBoard = await operate(browser);
    assert.equal(finalBoard.latest_run.state, 'FAILED');
    const runId = finalBoard.latest_run.id;
    const runChecks = await checks(browser, runId);
    assert.equal(runChecks.length, 3);
    const publicBoard = await board(browser);
    const publicLedger = await ledger(browser);
    const snapshot = await wallSnapshot(browser);
    await assertWallMatchesPublic(browser, snapshot, publicBoard, publicLedger, runId);
    const current = snapshot.rows.filter(row => row.source === 'current');
    assert.equal(current.length, 2, 'The failed partial operation erased its confirmed events');
    assert.equal(current.every(row => row.meaning === 'negative' && row.verdict === 'fail'), true, 'A failed partial consequence was promoted');
    assert.ok(snapshot.status.text.includes(`Operation ${runId} · FAILED`), 'The wall hides the failed partial run');
    assert.ok(snapshot.status.text.includes('Failed. Confirmed records stay visible'), 'The wall implies success for a failed partial run');
    const scene = await sceneState(browser);
    assertSingleTrace(scene, scene.arrivals, snapshot.trace, 2);
    await writeFile(out + '/partial.json', JSON.stringify({ run: runId, checks: runChecks, wall: snapshot, traces: scene.wallTraces }, null, 2) + '\n');
    return { result: 'PASS', run: runId, current: current.length, state: finalBoard.latest_run.state };
  } finally { await browser.close(); }
}

function syntheticViewed(browser, events, reduced = false, consistency = 'linked') {
  return browser.evaluate(({ events, reduced, consistency }) => {
    const latest = globalThis.__s29Latest();
    if (latest?.kind !== 'accepted') throw Error('No accepted baseline is available');
    const view = JSON.parse(JSON.stringify(latest.view));
    view.operating = { selectionId: 's32-synthetic-selection', kind: 'LEARNER_CHOICE', versionId: 's32-synthetic-version',
      contentHash: 's32-synthetic-hash', comparisonId: 's32-synthetic-comparison', retainedAlternativeId: 's32-synthetic-alt',
      requirementSetHash: 's32-synthetic-requirements', validity: 'VALID' };
    view.run = { id: 's32-synthetic-run', shiftId: view.context.shiftId, versionId: 's32-synthetic-version',
      selectionId: 's32-synthetic-selection', state: 'FINALIZED', purpose: 'OPERATION', evidenceMode: 'TRUSTED_LOCAL',
      failureKind: null, outputCount: 1, checkCount: 1, failedCheckCount: 0 };
    view.consequences.events = events.map(event => ({ ...event, id: `bookshop:${event.seq}:${event.hash}`,
      synthetic: true, source: 'current', linkState: 'linked', meaning: 'recorded', versionId: 's32-synthetic-version',
      reasonCode: null, contradiction: null, incidentId: null,
      link: { runId: 's32-synthetic-run', checkId: 's32-synthetic-check', outputId: 's32-synthetic-output', ordinal: 1, verdict: 'pass' } }));
    view.consistency = consistency;
    globalThis.__s29Host().publish({ kind: 'accepted', view, generation: latest.generation, intent: latest.intent,
      reason: reduced ? 'synthetic-reduced' : 'synthetic-arrival' });
    return true;
  }, { events, reduced, consistency });
}

async function setMotion(browser, reduced) {
  await browser.send('Emulation.setEmulatedMedia', { features: reduced ? [{ name: 'prefers-reduced-motion', value: 'reduce' }] : [] });
  assert.ok(await browser.until(value => matchMedia('(prefers-reduced-motion: reduce)').matches === value, 10000, reduced),
    `Reduced motion did not ${reduced ? 'apply' : 'clear'}`);
  await sleep(50);
}
export async function runMotion(base, out, fault = '') {
  const browser = await openBrowser(base, out, fault || 'operation-motion');
  try {
    await openBoard(browser, base);
    await browser.evaluate(() => document.querySelector('[data-station="ledger"]').click());
    await syntheticViewed(browser, []);
    await setMotion(browser, true);
    await syntheticViewed(browser, [{ seq: 1, hash: 'reduced-1', type: 'SALE_COMPLETED' }], true);
    await sleep(80);
    const reduced = await sceneState(browser);
    assert.equal(reduced.wallTraces ?? 0, 0, 'Reduced motion started an evidence trace');
    await setMotion(browser, false);
    await syntheticViewed(browser, [{ seq: 2, hash: 'arrival-2', type: 'SALE_COMPLETED' }]);
    assert.ok(await browser.until(() => globalThis.__workplaceControls.state().wallTrace, 10000), 'The synthetic linked consequence did not start a trace');
    await setMotion(browser, true);
    await sleep(80);
    const cancelled = await sceneState(browser);
    assert.equal(cancelled.wallTrace, false, 'Reduced motion did not cancel the evidence trace');
    assert.equal(cancelled.wall.emissive, 0, 'Reduced motion left the wall emphasis visible');
    await setMotion(browser, false);
    await syntheticViewed(browser, [{ seq: 2, hash: 'arrival-2', type: 'SALE_COMPLETED' }]);
    await sleep(400);
    const replay = await sceneState(browser);
    assert.equal(replay.wallTraces, 1, 'A duplicate accepted view replayed the evidence trace');
    await writeFile(out + '/motion.json', JSON.stringify({ reduced, cancelled, replay: replay.wallTraces }, null, 2) + '\n');
    return { result: 'PASS', traces: replay.wallTraces };
  } finally { await browser.close(); }
}

export async function runConflict(base, out, fault = '') {
  const browser = await openBrowser(base, out, fault || 'operation-conflict');
  try {
    await openBoard(browser, base);
    await browser.evaluate(() => document.querySelector('[data-station="ledger"]').click());
    await syntheticViewed(browser, []);
    const event = { seq: 1, hash: 'confirmed-1', type: 'SALE_COMPLETED' };
    await syntheticViewed(browser, [event], false, 'conflict');
    await sleep(80);
    const conflicted = await sceneState(browser);
    assert.equal(conflicted.wallTraces ?? 0, 0, 'A conflicting read started a trace');
    assert.equal(conflicted.arrivals.length, 0, 'A conflicting read fired the arrival callback');
    await syntheticViewed(browser, [event]);
    assert.ok(await browser.until(() => globalThis.__workplaceControls.state().wallTrace, 10000), 'The confirmed linked consequence did not start a trace');
    const scene = await sceneState(browser);
    const snapshot = await wallSnapshot(browser);
    assertSingleTrace(scene, scene.arrivals, snapshot.trace, 1);
    await browser.evaluate(() => {
      const latest = globalThis.__s29Latest();
      globalThis.__s29Host().publish({ kind: 'reset', context: latest.view.context, reason: 'synthetic-reset' });
    });
    await syntheticViewed(browser, [event, { seq: 2, hash: 'confirmed-2', type: 'SALE_COMPLETED' }]);
    assert.ok(await browser.until(() => globalThis.__workplaceControls.state().wallTraces === 2, 15000),
      'The reset and remount lost the confirmed arrival');
    const remounted = await sceneState(browser);
    assert.deepEqual(remounted.wallDurations, [320, 320], 'The remounted evidence trace did not use 320ms');
    assert.deepEqual(remounted.wallCounts, [1, 1], 'The remounted evidence trace carried the wrong count');
    assert.equal(remounted.arrivals.length, 2, 'The remount did not report exactly one confirmed arrival');
    const afterReset = await wallSnapshot(browser);
    assert.equal(afterReset.trace.state, 'active', 'The remounted evidence trace is not labelled active');
    await writeFile(out + '/conflict.json', JSON.stringify({ conflicted, confirmed: scene, trace: snapshot.trace, remounted, afterReset: afterReset.trace }, null, 2) + '\n');
    return { result: 'PASS', traces: remounted.wallTraces };
  } finally { await browser.close(); }
}
export async function runFaultControl(base, out, mode, fault) {
  return mode === 'journey' ? runJourney(base, out, fault)
    : mode === 'failed' ? runFailedTask(base, out, fault)
    : mode === 'motion' ? runMotion(base, out, fault)
    : mode === 'conflict' ? runConflict(base, out, fault)
    : (() => { throw Error(`Unknown S32 fault mode: ${mode}`); })();
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [mode, base, out, ...rest] = process.argv.slice(2);
  const result = mode === 'journey' ? await runJourney(base, out, rest[0] ?? '')
    : mode === 'queued' ? await runQueued(base, out)
    : mode === 'failed' ? await runFailedTask(base, out, rest[0] ?? '')
    : mode === 'missing' ? await runMissing(base, out)
    : mode === 'partial' ? await runPartial(base, out)
    : mode === 'motion' ? await runMotion(base, out, rest[0] ?? '')
    : mode === 'conflict' ? await runConflict(base, out, rest[0] ?? '')
    : (() => { throw Error(`Unknown S32 browser mode: ${mode}`); })();
  console.log(JSON.stringify(result));
}
