import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { openBrowser } from './workplace_browser.mjs';

const TERMINAL = ['FINALIZED', 'FAILED', 'INVALIDATED'];
const ELIGIBLE = '8fbf9f', BLOCKED = 'd98a7a', NEUTRAL = '6c5943', PLATE = 'edbd68', PLATE_NEUTRAL = '263443';
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const candidateA = () => readFile('shiftwork/fixtures/artifacts/bookshop/compare_repair_a_service.py', 'utf8');
const candidateB = () => readFile('shiftwork/fixtures/artifacts/bookshop/compare_repair_b_service.py', 'utf8');

async function waitReady(browser, timeout = 120000) {
  return browser.until(() => document.body?.dataset.loadState === 'ready' && document.getElementById('graphics-status')?.dataset.state === 'ready', timeout);
}
async function openBoard(browser, base, hash = '#board') {
  await browser.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  await browser.send('Page.navigate', { url: base + '/' + hash });
  assert.ok(await waitReady(browser), 'S31 workbench unavailable');
}
async function fetchJson(browser, path) {
  return browser.evaluate(async path => {
    const response = await fetch(path);
    return { ok: response.ok, status: response.status, body: response.ok ? await response.json() : await response.text() };
  }, path);
}
async function board(browser) { return (await fetchJson(browser, '/api/engagements/bookshop/board')).body; }
async function ledger(browser) { return (await fetchJson(browser, '/api/engagements/bookshop/ledger')).body; }
async function selections(browser) { return (await fetchJson(browser, '/api/engagements/bookshop/selections')).body; }
async function createInvestigation(browser, shiftId) {
  const setup = await browser.evaluate(async shiftId => {
    const response = await fetch(`/api/shifts/${encodeURIComponent(shiftId)}/investigations`, { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source_run_id: 'run-0001',
        source_request_ordinal: 1, cause: 'the starter asks instead of using the recorded public record',
        falsifier: 'a captured answer with the recorded price disproves this', public_test: 'compare the answer with the frozen public record',
        revision_of_id: null, client_request_id: `s31-owner-${Date.now()}-${Math.random().toString(36).slice(2)}` }) });
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
async function setupComparison(browser, sources) {
  const before = await board(browser);
  assert.ok(before.latest_shift?.id, 'The preview has no open shift');
  await createInvestigation(browser, before.latest_shift.id);
  await browser.evaluate(() => globalThis.__s29Refresh());
  assert.ok(await waitReady(browser), 'Owner setup refresh failed');
  await openCompare(browser);
  await saveDraft(browser, sources.a);
  await freeze(browser, 'A');
  await saveDraft(browser, sources.b);
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
async function sceneState(browser) {
  return browser.evaluate(() => ({ ...globalThis.__workplaceControls.state(),
    comparisonPulses: globalThis.__workplaceComparisonPulses ?? 0,
    comparisonDurations: globalThis.__workplaceComparisonDurations ?? [],
    selectionPulses: globalThis.__workplaceSelectionPulses ?? 0,
    selectionDurations: globalThis.__workplaceSelectionDurations ?? [] }));
}
async function wall(browser) {
  const [b, l, s] = [await board(browser), await ledger(browser), await selections(browser)];
  return { selection: b.operating_selection, latestRun: b.latest_run, events: l.events, totals: b.ledger_totals, incidents: b.incidents, selections: s };
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
  await browser.until(() => (globalThis.__s31Accepts ?? []).some(item => ['FINALIZED', 'FAILED', 'INVALIDATED'].includes(item.state)), 60000);
  assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready' && document.querySelectorAll('#comparison-slots .comparison-slot').length === 6, 180000), 'The comparison panel did not settle');
  const [attempts, accepts] = await browser.evaluate(() => [globalThis.__s31Attempts ?? [], globalThis.__s31Accepts ?? []]);
  return { id: payload.id, payload, initial, attempts, accepts };
}
function expectedMissing(payload) {
  return payload.trials.filter(trial => !trial.run_id || (trial.missing_evidence?.length ?? 0)).length;
}
async function assertStands(browser, payload) {
  const scene = await sceneState(browser);
  assert.equal(scene.comparisonId, payload.id, 'The scene lost the comparison identity');
  for (const label of ['A', 'B']) {
    const candidate = payload.candidates.find(item => item.label === label);
    const eligibility = payload.outcome?.eligibility?.find(item => item.candidate_label === label) ?? null;
    assert.equal(scene.candidates[label]?.versionId, candidate.artifact_version_id, `Stand ${label} lost the frozen version identity`);
    assert.equal(scene.candidates[label]?.contentHash, candidate.artifact_content_hash, `Stand ${label} lost the content hash`);
    assert.equal(scene.candidates[label]?.eligible, eligibility?.eligible ?? null, `Stand ${label} inferred eligibility outside the public outcome`);
    const expected = eligibility?.eligible === true ? ELIGIBLE : eligibility?.eligible === false ? BLOCKED : NEUTRAL;
    assert.equal(scene.candidates[label]?.color, expected, `Stand ${label} used the wrong public colour`);
  }
  assert.ok(scene.comparisonPulses >= 1, 'The comparison stands never pulsed');
  assert.deepEqual([...new Set(scene.comparisonDurations)], [160], 'The comparison emphasis did not use 160ms');
  return scene;
}
async function assertNoPreselection(browser, payload, before) {
  const after = await board(browser);
  assert.deepEqual(after.operating_selection, before.operating_selection, 'The comparison changed the operating selection');
  const scene = await sceneState(browser);
  const prior = before.operating_selection;
  assert.equal(scene.selection.id, prior?.id ?? null, 'The scene changed the operating selection id');
  assert.equal(scene.selection.versionId, prior?.selected_version_id ?? null, 'The scene changed the operating version');
  assert.equal(scene.selection.contentHash, prior?.selected_content_hash ?? null, 'The scene changed the operating content hash');
  assert.equal(scene.selection.plate, prior ? PLATE : PLATE_NEUTRAL, 'The operating plate changed before an explicit choice');
  for (const candidate of payload.candidates) {
    assert.notEqual(candidate.artifact_version_id, prior?.selected_version_id ?? null, 'The comparison reused the operating version as a candidate');
  }
}
async function choose(browser, base, shiftId, label, payload, beforeChoice) {
  const chosen = payload.candidates.find(item => item.label === label);
  const other = payload.candidates.find(item => item.label !== label);
  const commandIndex = browser.commands.length;
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
  const after = await board(browser);
  const selection = after.operating_selection;
  assert.ok(selection, 'The accepted refresh did not publish the operating selection');
  assert.equal(selection.selected_version_id, chosen.artifact_version_id, 'The choice did not bind the exact candidate version');
  assert.equal(selection.selected_content_hash, chosen.artifact_content_hash, 'The choice did not bind the exact content hash');
  assert.equal(selection.retained_alternative_version_id, other.artifact_version_id, 'The choice retained the wrong alternative');
  assert.equal(selection.comparison_id, payload.id, 'The choice lost its comparison identity');
  const scene = await sceneState(browser);
  assert.equal(scene.selection.id, selection.id, 'The operating plate shows a different selection id');
  assert.equal(scene.selection.versionId, selection.selected_version_id, 'The operating plate shows a different version');
  assert.equal(scene.selection.contentHash, selection.selected_content_hash, 'The operating plate shows a different content hash');
  assert.equal(scene.selection.plate, PLATE, 'The operating plate did not leave its neutral state after the choice');
  assert.equal(scene.selectionPulses, 1, 'The operating plate acknowledgement did not run exactly once');
  assert.deepEqual([...new Set(scene.selectionDurations)], [180], 'The selection acknowledgement did not use 180ms');
  const newCommands = browser.commands.slice(commandIndex).map(url => new URL(url).pathname);
  assert.deepEqual(newCommands, [`/api/shifts/${shiftId}/selections`], 'The choice submitted an extra command');
  assert.deepEqual((await wall(browser)).events, beforeChoice.events, 'The choice changed the recorded consequence wall');
  assert.deepEqual((await wall(browser)).incidents, beforeChoice.incidents, 'The choice changed operational incidents');
  assert.equal((await board(browser)).latest_run?.id, beforeChoice.latestRun?.id, 'The choice moved the latest run');
  const note = await browser.evaluate(() => document.getElementById('selection-note').textContent);
  const summary = await browser.evaluate(() => document.getElementById('selection-summary').textContent);
  for (const value of [selection.selected_version_id, selection.selected_content_hash, selection.retained_alternative_version_id]) {
    assert.ok(note.includes(value), `The compare panel hides ${value} after the choice`);
  }
  for (const value of [selection.selected_version_id, selection.selected_content_hash, selection.retained_alternative_version_id, selection.comparison_id]) {
    assert.ok(summary.includes(value), `The board hides ${value} after the choice`);
  }
  assert.equal(await browser.evaluate(() => document.getElementById('select-candidate-a').disabled &&
    document.getElementById('select-candidate-b').disabled), true, 'The same comparison offered a second choice');
  const origin = await browser.evaluate(() => performance.timeOrigin);
  await browser.send('Page.reload');
  assert.ok(await browser.until(old => performance.timeOrigin !== old &&
    document.body?.dataset.loadState === 'ready' &&
    document.getElementById('graphics-status')?.dataset.state === 'ready', 120000, origin), 'The workbench reload after the choice did not settle');
  const reopened = await board(browser);
  assert.deepEqual(reopened.operating_selection, selection, 'Reloading the workbench changed the operating selection');
  const reopenedScene = await sceneState(browser);
  assert.equal(reopenedScene.selection.id, selection.id, 'The reloaded plate shows a different selection id');
  assert.equal(reopenedScene.selection.versionId, selection.selected_version_id, 'The reloaded plate shows a different version');
  assert.equal(reopenedScene.selection.contentHash, selection.selected_content_hash, 'The reloaded plate shows a different content hash');
  assert.equal(reopenedScene.selection.plate, PLATE, 'The reloaded plate lost the selected identity');
  await openCompare(browser);
  return selection;
}
async function assertLayout(browser) {
  // S36 planned change (Gate 3 section 13.9): layout A's `sideBySide: workplace.right <= panel.left + 2`
  // is replaced by inspector_keeps_stations_readable at 1280x720.
  await browser.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
  await browser.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(resolve, 200)))));
  const desktop = await browser.evaluate(() => {
    const panel = document.getElementById('station-panel').getBoundingClientRect();
    const tags = [...document.querySelectorAll('.room-hotspots:not([hidden]) [data-station]')].map(node => node.getBoundingClientRect());
    return { inspectorOpen: document.getElementById('workplace-world').dataset.inspector === 'open' && panel.width > 0,
      stationsReadable: tags.length >= 4 && tags.every(r => r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight
        && !(r.left < panel.right && r.right > panel.left && r.top < panel.bottom && r.bottom > panel.top)),
      overflow: document.documentElement.scrollWidth <= innerWidth,
      cards: document.querySelectorAll('#comparison-outcome .comparison-outcome-card').length };
  });
  assert.deepEqual(desktop, { inspectorOpen: true, stationsReadable: true, overflow: true, cards: 2 }, 'The 1280px comparison inspector hides a station or the room');
  for (const [width, height] of [[640, 900], [390, 844]]) {
    await browser.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
    await new Promise(resolve => setTimeout(resolve, 120));
    const narrow = await browser.evaluate(() => {
      const workplace = document.querySelector('.workplace').getBoundingClientRect();
      const panel = document.getElementById('station-panel').getBoundingClientRect();
      return { stacked: workplace.bottom <= panel.top + 2, overflow: document.documentElement.scrollWidth <= innerWidth,
        cards: document.querySelectorAll('#comparison-outcome .comparison-outcome-card').length,
        compareVisible: !document.getElementById('compare-view').hidden };
    });
    assert.deepEqual(narrow, { stacked: true, overflow: true, cards: 2, compareVisible: true }, `The ${width}px comparison layout is not a readable stacked layout`);
  }
  await browser.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
}
async function assertIncomparable(browser, payload, before) {
  assert.ok(['INCOMPLETE', 'NOT_COMPARABLE'].includes(payload.outcome?.status), 'The terminal comparison reported a complete outcome');
  const denial = await browser.evaluate(() => [...document.querySelectorAll('#comparison-outcome .denial')].map(node => node.textContent).join(' '));
  assert.ok(denial.includes('not comparable'), 'The panel hid the incomparable evidence');
  const cards = await browser.evaluate(() => [...document.querySelectorAll('#comparison-outcome .comparison-outcome-card')].map(card => ({ label: card.dataset.candidateLabel, eligible: card.dataset.eligible, text: card.textContent })));
  assert.equal(cards.length, 2, 'The incomparable comparison hides a candidate');
  for (const card of cards) {
    const eligibility = payload.outcome.eligibility.find(item => item.candidate_label === card.label);
    assert.equal(card.eligible, String(eligibility.eligible), `Candidate ${card.label} renders the wrong incomparable eligibility`);
    for (const reason of eligibility.blocking_reason_codes) assert.ok(card.text.includes(reason), `Candidate ${card.label} hides blocker ${reason}`);
  }
  const missing = expectedMissing(payload);
  const summary = await browser.evaluate(() => document.getElementById('compare-summary').textContent);
  assert.ok(summary.includes(`${missing} missing slot`), 'The panel hid the missing comparison slots');
  const scene = await sceneState(browser);
  const prior = before.operating_selection;
  assert.equal(scene.selection.id, prior?.id ?? null, 'An incomparable comparison moved the operating plate');
  assert.equal(scene.selection.versionId, prior?.selected_version_id ?? null, 'An incomparable comparison changed the operating version');
  assert.equal(scene.selection.plate, prior ? PLATE : PLATE_NEUTRAL, 'An incomparable comparison changed the plate identity');
  assert.equal(await browser.evaluate(() => document.getElementById('select-candidate-a').disabled &&
    document.getElementById('select-candidate-b').disabled), true, 'An incomparable comparison offered a choice');
  return { missing, cards };
}

export async function runJourney(base, out, mode = 'complete', choice = 'A', fault = '') {
  const browser = await openBrowser(base, out, fault || 'comparison-journey');
  try {
    await openBoard(browser, base);
    const before = await setupComparison(browser, { a: await candidateA(), b: await candidateB() });
    const sceneBefore = await sceneState(browser);
    const prior = before.operating_selection;
    assert.equal(sceneBefore.selection.id, prior?.id ?? null, 'The scene changed the prior operating selection before the comparison');
    assert.equal(sceneBefore.selection.versionId, prior?.selected_version_id ?? null, 'The scene changed the prior operating version');
    assert.equal(sceneBefore.selection.plate, prior ? PLATE : PLATE_NEUTRAL, 'The operating plate did not reflect the public prior selection');
    assert.deepEqual(Object.values(sceneBefore.candidates).map(candidate => candidate.eligible), [null, null], 'A stand inferred eligibility before the public outcome');
    assert.deepEqual(Object.values(sceneBefore.candidates).map(candidate => candidate.color), [NEUTRAL, NEUTRAL], 'A stand was coloured before the public outcome');
    const { id, payload, initial, attempts, accepts } = await comparisonToTerminal(browser);
    assert.ok(accepts.length >= 2, 'The comparison published no polled assignment');
    assert.equal(attempts[0]?.state, initial.state, 'The initial comparison assignment was not published');
    assert.equal(attempts[0]?.allowed, true, 'The initial comparison assignment was suppressed');
    assert.equal(accepts.at(-1).state, payload.state, 'The final comparison assignment was not published');
    assert.equal(accepts.at(-1).outcome, payload.outcome?.status ?? null, 'The final comparison publication hid the public outcome');
    assert.equal(accepts.at(-1).missing, expectedMissing(payload), 'The final comparison publication hid missing slots');
    assert.ok(accepts.every(item => item.latestReason === 'comparison'), 'A comparison assignment was published under another reason');
    assert.equal(payload.kind, 'QUALIFYING_COMPARISON', 'The Compare station payload is not a qualifying comparison');
    assert.equal(payload.trials.length, 6, 'The comparison does not carry six slots');
    const scene = await assertStands(browser, payload);
    await assertNoPreselection(browser, payload, before);
    if (mode === 'complete') {
      assert.equal(payload.outcome?.status, 'COMPLETE', 'The eligible pair did not complete comparably');
      assert.equal(expectedMissing(payload), 0, 'The eligible pair carries missing slots');
      assert.equal(payload.outcome.eligibility.every(item => item.eligible), true, 'The eligible pair reports an ineligible candidate');
      const beforeChoice = await wall(browser);
      const selection = await choose(browser, base, before.latest_shift.id, choice, payload, beforeChoice);
      await assertLayout(browser);
      await writeFile(out + '/journey.json', JSON.stringify({ mode, choice, comparison: id, initial: initial.state, accepts, scene: { comparisonPulses: scene.comparisonPulses, candidates: scene.candidates }, selection }, null, 2) + '\n');
      return { result: 'PASS', mode, choice, comparison: id, states: accepts.map(item => item.state) };
    }
    const detail = await assertIncomparable(browser, payload, before);
    if (mode === 'missing') {
      assert.ok(detail.missing >= 1, 'The missing preview carried no missing slot');
      assert.ok(payload.trials.some(trial => (trial.missing_evidence?.length ?? 0) > 0 && trial.state === 'FAILED'), 'The missing slots do not report an execution failure');
    }
    if (mode === 'blocked' || mode === 'incomparable') assert.equal(payload.outcome.status, 'NOT_COMPARABLE', 'The blocked preview did not report NOT_COMPARABLE');
    if (mode === 'blocked') assert.equal(detail.missing, 0, 'The blocked preview unexpectedly carried missing slots');
    await assertLayout(browser);
    await writeFile(out + '/journey.json', JSON.stringify({ mode, comparison: id, initial: initial.state, accepts, scene: { comparisonPulses: scene.comparisonPulses, candidates: scene.candidates }, detail }, null, 2) + '\n');
    return { result: 'PASS', mode, comparison: id, outcome: payload.outcome?.status, missing: detail.missing };
  } finally { await browser.close(); }
}

export async function runOwnership(base, out, mode, fault = '') {
  assert.ok(['generation', 'intent', 'history', 'context', 'shift', 'experiment', 'inspection', 'loading'].includes(mode), 'Unknown ownership mode');
  const hold = ['generation', 'intent', 'history'].includes(mode);
  const browserFault = fault || (hold ? 'comparison-hold-post' : 'comparison-observe');
  const browser = await openBrowser(base, out, browserFault);
  try {
    await openBoard(browser, base);
    const before = await setupComparison(browser, {
      a: await candidateA(), b: await candidateB(),
    });
    if (hold) {
      const experimentPath = `/api/shifts/${before.latest_shift.id}/experiments`;
      const startDeadline = Date.now() + 30000;
      while (Date.now() < startDeadline && !browser.commands.some(url => new URL(url).pathname === experimentPath)) await sleep(50);
      assert.ok(browser.commands.some(url => new URL(url).pathname === experimentPath), 'The held comparison POST did not start');
      await sleep(400);
      if (mode === 'generation') {
        await browser.evaluate(() => globalThis.__s29Refresh());
        assert.ok(await waitReady(browser), 'The generation refresh did not settle');
      }
      if (mode === 'intent') {
        await browser.evaluate(() => document.querySelector('[data-station="customers"]').click());
        assert.ok(await browser.until(() => document.getElementById('panel-title').textContent === 'Customer evidence', 30000), 'The intent change did not settle');
      }
      if (mode === 'history') {
        await browser.evaluate(() => globalThis.__s31SetInspection('history', 'run-0001'));
      }
      const [attemptIndex, publicationIndex] = await browser.evaluate(() => [
        (globalThis.__s31Attempts ?? []).length,
        (globalThis.__s31Publications ?? []).length,
      ]);
      browser.releaseImports();
      assert.ok(await browser.until(index => (globalThis.__s31Attempts ?? []).length > index, 60000, attemptIndex), 'The held comparison assignment was not observed');
      const attempt = await browser.evaluate(index => globalThis.__s31Attempts[index], attemptIndex);
      assert.equal(attempt.allowed, false, `${mode} ownership published a stale comparison update`);
      const initial = await browser.evaluate(() => globalThis.__s31Initial);
      assert.ok(initial?.id, 'The held comparison POST returned no experiment');
      let payload = null;
      const completionDeadline = Date.now() + 180000;
      while (Date.now() < completionDeadline) {
        const current = (await fetchJson(browser, `/api/experiments/${encodeURIComponent(initial.id)}`)).body;
        if (current?.state && TERMINAL.includes(current.state)) { payload = current; break; }
        await sleep(500);
      }
      assert.ok(payload, 'The held comparison did not reach a terminal state');
      await browser.until(() => document.body.dataset.loadState === 'ready', 90000);
      const publications = await browser.evaluate(() => globalThis.__s31Publications ?? []);
      assert.deepEqual(publications.slice(publicationIndex).filter(item => item.reason === 'comparison'), [], `${mode} ownership published a stale comparison update`);
      if (mode === 'history') await browser.evaluate(() => globalThis.__s31SetInspection('current', null));
      await writeFile(out + '/ownership.json', JSON.stringify({ mode, fault: browserFault, attempt, payload: payload.state, publications: publications.slice(publicationIndex) }, null, 2) + '\n');
      return { result: 'PASS', mode, allowed: attempt.allowed, publicationCount: publications.length };
    }
    const { id, payload } = await comparisonToTerminal(browser);
    const owner = await browser.evaluate(() => globalThis.__s31State());
    const experiment = await browser.evaluate(() => globalThis.__s31Comparison());
    const beforePublications = await browser.evaluate(() => (globalThis.__s31Publications ?? []).length);
    const beforeAttempts = await browser.evaluate(() => (globalThis.__s31Attempts ?? []).length);
    await browser.evaluate(({ mode, owner, experiment }) => {
      if (mode === 'context') { globalThis.__s31SetSlug('gtm'); globalThis.__s31Accept(owner, experiment); globalThis.__s31SetSlug(owner.slug); }
      if (mode === 'shift') { globalThis.__s31SetShift('other-shift'); globalThis.__s31Accept(owner, experiment); globalThis.__s31SetShift(owner.shiftId); }
      if (mode === 'experiment') globalThis.__s31Accept(owner, { ...experiment, shift_id: 'other-shift' });
      if (mode === 'inspection') { globalThis.__s31SetInspection('history', 'run-0001'); globalThis.__s31Accept(owner, experiment); globalThis.__s31SetInspection('current', null); }
      if (mode === 'loading') { document.body.dataset.loadState = 'loading'; globalThis.__s31Accept(owner, experiment); document.body.dataset.loadState = 'ready'; }
    }, { mode, owner, experiment });
    const outcome = await browser.evaluate(({ beforeAttempts, beforePublications }) => ({
      attempts: (globalThis.__s31Attempts ?? []).slice(beforeAttempts),
      publications: (globalThis.__s31Publications ?? []).slice(beforePublications),
    }), { beforeAttempts, beforePublications });
    assert.equal(outcome.attempts.length, 1, `${mode} ownership did not reach the comparison guard`);
    assert.equal(outcome.attempts[0].allowed, false, `${mode} ownership published a stale comparison update`);
    assert.deepEqual(outcome.publications.filter(item => item.reason === 'comparison'), [], `${mode} ownership published a stale comparison update`);
    await writeFile(out + '/ownership.json', JSON.stringify({ mode, fault: browserFault, id, outcome }, null, 2) + '\n');
    return { result: 'PASS', mode, allowed: outcome.attempts[0].allowed };
  } finally { await browser.close(); }
}

export async function runSelection(base, out, fault = '') {
  const browser = await openBrowser(base, out, fault || 'selection-observe');
  try {
    await openBoard(browser, base);
    const before = await setupComparison(browser, {
      a: await candidateA(), b: await candidateB(),
    });
    const { id, payload } = await comparisonToTerminal(browser);
    const beforeChoice = await wall(browser);
    const selectionCountBefore = beforeChoice.selections.length;
    const selection = await choose(browser, base, before.latest_shift.id, 'A', payload, beforeChoice);
    const afterWall = await wall(browser);
    assert.deepEqual(afterWall.events, beforeChoice.events, 'The selection acknowledgement changed the consequence wall');
    assert.deepEqual(afterWall.incidents, beforeChoice.incidents, 'The selection acknowledgement changed incidents');
    assert.equal(afterWall.latestRun?.id, beforeChoice.latestRun?.id, 'The selection acknowledgement started or moved a run');
    assert.equal(afterWall.selections.length, selectionCountBefore + 1, 'The selection was recorded more than once');
    assert.equal(afterWall.selections.at(-1).id, selection.id, 'The recorded selection differs from the published choice');
    await writeFile(out + '/selection.json', JSON.stringify({ comparison: id, selection, wall: { before: beforeChoice, after: afterWall } }, null, 2) + '\n');
    return { result: 'PASS', selection: selection.id, version: selection.selected_version_id };
  } finally { await browser.close(); }
}

export async function runFailure(base, out, fault = 'selection-fail-once') {
  const browser = await openBrowser(base, out, fault);
  try {
    await openBoard(browser, base);
    const before = await setupComparison(browser, {
      a: await candidateA(), b: await candidateB(),
    });
    const { id, payload } = await comparisonToTerminal(browser);
    const beforeChoice = await wall(browser);
    const commandIndex = browser.commands.length;
    await browser.evaluate(() => {
      const field = document.getElementById('selection-rationale');
      field.value = 'Candidate A answered every shared task; retry the recorded choice once.';
      field.dispatchEvent(new Event('input'));
      document.getElementById('select-candidate-a').click();
    });
    assert.ok(await browser.until(() => document.getElementById('selection-error').textContent.trim().length > 0, 90000), 'The failed selection showed no error');
    assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready' && !document.getElementById('select-candidate-a').disabled, 90000), 'The failed selection did not release the workbench');
    assert.equal((await board(browser)).operating_selection?.id ?? null, beforeChoice.selection?.id ?? null, 'A failed selection changed the operating choice');
    const baselineCount = beforeChoice.selections.length;
    assert.equal((await selections(browser)).length, baselineCount, 'A failed selection recorded a choice');
    await browser.evaluate(() => document.getElementById('select-candidate-a').click());
    assert.ok(await browser.until(() => document.getElementById('selection-note').textContent.startsWith('Choice '), 90000), 'The explicit retry did not record a choice');
    assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready', 90000), 'The retry refresh did not settle');
    const recorded = await selections(browser);
    assert.equal(recorded.length, baselineCount + 1, 'The retry recorded more than one choice');
    const latest = recorded.at(-1);
    assert.equal(latest.selected_version_id, payload.candidates.find(item => item.label === 'A').artifact_version_id, 'The retry recorded a different version');
    const commands = browser.commands.slice(commandIndex).map(url => new URL(url).pathname);
    assert.deepEqual(commands, [`/api/shifts/${before.latest_shift.id}/selections`, `/api/shifts/${before.latest_shift.id}/selections`], 'The retry replayed the choice or submitted another command');
    await new Promise(resolve => setTimeout(resolve, 1200));
    assert.equal((await selections(browser)).length, baselineCount + 1, 'A repeated poll replayed the choice');
    assert.deepEqual((await wall(browser)).events, beforeChoice.events, 'Selection recovery changed the consequence wall');
    assert.deepEqual(browser.exceptions, [], 'Selection recovery raised an uncaught exception');
    await writeFile(out + '/failure.json', JSON.stringify({ comparison: id, recorded, commands }, null, 2) + '\n');
    return { result: 'PASS', selections: recorded.length };
  } finally { await browser.close(); }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [mode, base, out, ...rest] = process.argv.slice(2);
  const result = mode === 'journey' ? await runJourney(base, out, rest[0] ?? 'complete', rest[1] ?? 'A', rest[2] ?? '')
    : mode === 'ownership' ? await runOwnership(base, out, rest[0], rest[1] ?? '')
    : mode === 'selection' ? await runSelection(base, out, rest[0] ?? '')
    : mode === 'failure' ? await runFailure(base, out, rest[0] ?? 'selection-fail-once')
    : (() => { throw Error(`Unknown S31 browser mode: ${mode}`); })();
  console.log(JSON.stringify(result));
}
