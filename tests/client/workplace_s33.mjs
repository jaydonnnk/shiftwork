import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { openBrowser } from './workplace_browser.mjs';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function waitReady(browser, timeout = 120000) {
  return browser.until(() => document.body?.dataset.loadState === 'ready' &&
    document.getElementById('graphics-status')?.dataset.state === 'ready', timeout);
}
async function fetchJson(browser, path, options) {
  return browser.evaluate(async ({ path, options }) => {
    const response = await fetch(path, options);
    return { ok: response.ok, status: response.status, body: response.ok ? await response.json() : await response.text() };
  }, { path, options });
}
async function board(browser) {
  return (await fetchJson(browser, '/api/engagements/bookshop/board')).body;
}
async function sceneState(browser) {
  return browser.evaluate(() => ({ ...globalThis.__workplaceControls.state(), arrivals: globalThis.__s32Arrivals ?? [] }));
}
async function screenshot(browser, out, name, width = 1280, height = 900) {
  await browser.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
  const { data } = await browser.send('Page.captureScreenshot', { format: 'png' });
  await writeFile(`${out}/${name}.png`, Buffer.from(data, 'base64'));
}
function inheritFields() {
  return {
    selection: document.getElementById('next-inheritance').dataset.selectedVersion,
    retained: document.getElementById('next-inheritance').dataset.retainedAlternative,
    observed: document.getElementById('next-inheritance').dataset.observedRun ?? '',
    experiment: document.getElementById('next-experiment').dataset.experimentId ?? '',
    experimentState: document.getElementById('next-experiment').dataset.experimentState ?? '',
    replaces: document.getElementById('next-experiment').dataset.replacesSelection ?? '',
  };
}

export async function runLater(base, out) {
  const browser = await openBrowser(base, out, 's33-later');
  try {
    await browser.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    await browser.send('Page.navigate', { url: base + '/#next' });
    assert.ok(await waitReady(browser), 'The inherited Bellwether shift was unavailable');
    const before = await board(browser);
    assert.ok(before.operating_selection?.id, 'The inherit preview has no operating choice');
    const stationView = (await fetchJson(browser, `/api/shifts/${encodeURIComponent(before.latest_shift.id)}/investigations`)).body;
    const later = stationView.latest_experiment;
    assert.equal(later?.kind, 'LATER_CONDITION_COMPARISON', 'The inherit preview has no later-condition experiment');
    assert.ok(later.observed_run_id, 'The later experiment has no observed operation');
    if (later.candidates.find(candidate => candidate.label === 'A')?.artifact_version_id !== before.operating_selection.selected_version_id ||
        later.candidates.find(candidate => candidate.label === 'B')?.artifact_version_id !== before.operating_selection.retained_alternative_version_id) {
      throw new Error('The later experiment no longer re-tests the original selected and retained versions');
    }
    if (later.trials.some(trial => trial.run_id === later.observed_run_id)) throw new Error('The later observed run is a trial run');
    await browser.evaluate(() => document.querySelector('[data-station="next"]').click());
    assert.ok(await browser.until(() => !document.getElementById('next-view').hidden, 30000), 'The handover shelf did not open');
    const initial = await browser.evaluate(inheritFields);
    assert.equal(initial.selection, before.operating_selection.selected_version_id, 'The shelf hides the inherited selected version');
    assert.equal(initial.retained, before.operating_selection.retained_alternative_version_id, 'The shelf hides the retained alternative');
    assert.equal(initial.observed, later.observed_run_id, 'The shelf hides the observed operation');
    assert.equal(initial.experiment, later.id, 'The shelf hides the later experiment');
    assert.equal(initial.replaces, 'false', 'The shelf claims the later experiment replaces the selection');
    const inheritedScene = await sceneState(browser);
    assert.equal(inheritedScene.selection.versionId, before.operating_selection.selected_version_id, 'The scene operating plate lost the inherited choice');
    assert.equal(inheritedScene.handover.selectionId, before.operating_selection.id, 'The scene handover shelf lost the inherited choice');
    assert.equal(inheritedScene.later.id, later.id, 'The scene lost the later experiment');
    assert.equal(inheritedScene.later.observedRunId, later.observed_run_id, 'The scene lost the later observed run');
    assert.equal(inheritedScene.wallTraces ?? 0, 0, 'Inheritance started an evidence trace');
    await screenshot(browser, out, 'handover-later-1280');
    await browser.evaluate(() => document.getElementById('next-experiment').scrollIntoView({ block: 'center' }));
    await sleep(150);
    await screenshot(browser, out, 'later-experiment-1280');
    await screenshot(browser, out, 'handover-later-390', 390, 844);
    await browser.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    assert.ok(await browser.until(() => document.getElementById('graphics-status')?.dataset.state === 'ready' &&
      document.querySelector('#workplace-canvas canvas'), 30000), 'The richer Bellwether scene did not settle after the later-test layout checks');
    await browser.evaluate(() => document.querySelector('[data-station="owner"]').click());
    assert.ok(await browser.until(() => !document.getElementById('owner-record').hidden, 30000), 'The owner desk did not open');
    assert.ok(await browser.evaluate(() => {
      const folder = document.getElementById('owner-record').getBoundingClientRect();
      const panel = document.getElementById('station-panel').getBoundingClientRect();
      return folder.top >= panel.top && folder.top < panel.bottom;
    }), 'The owner requirements folder stayed outside the visible workbench');
    await screenshot(browser, out, 'owner-desk-1280');
    await browser.evaluate(() => document.querySelector('[data-station="repair"]').click());
    assert.ok(await browser.until(() => !document.getElementById('repair-view').hidden &&
      document.querySelectorAll('#repair-incidents .incident-row').length > 0, 30000), 'The incident review tray did not open');
    await screenshot(browser, out, 'repair-tray-1280');
    await browser.evaluate(() => document.querySelector('[data-station="next"]').click());
    const quiet = { traces: inheritedScene.wallTraces ?? 0, arrivals: inheritedScene.arrivals.length };
    const incidentCount = await browser.evaluate(() => document.querySelectorAll('#handover-incidents .incident-row').length);
    assert.ok(incidentCount > 0, 'The handover shelf has no unresolved incident to inspect');
    await browser.evaluate(() => document.querySelector('#handover-incidents .incident-row').click());
    assert.ok(await browser.until(() => document.getElementById('inspection-bar').dataset.mode === 'history' &&
      !document.getElementById('inspect-current').hidden && document.getElementById('selected-evidence').dataset.runId, 60000), 'The historical incident did not open');
    const history = await browser.evaluate(() => ({
      mode: document.getElementById('inspection-bar').dataset.mode,
      run: document.getElementById('selected-evidence').dataset.runId,
      help: document.getElementById('next-help').textContent,
      closeDisabled: document.getElementById('close-shift').disabled,
      openDisabled: document.getElementById('open-next-shift').disabled,
    }));
    assert.equal(history.mode, 'history', 'The incident inspection is not historical');
    assert.ok(history.help.includes('Return to the current shift'), 'The historical state does not explain the explicit return');
    assert.equal(history.closeDisabled, true, 'A historical inspection can close the current shift');
    assert.equal(history.openDisabled, true, 'A historical inspection can open a new shift');
    await screenshot(browser, out, 'historical-inspection-1280');
    await sleep(1300);
    assert.equal(await browser.evaluate(() => document.getElementById('inspection-bar').dataset.mode), 'history', 'Ordinary polling changed the inspection mode');
    const afterPoll = await sceneState(browser);
    assert.equal(afterPoll.wallTraces ?? 0, quiet.traces, 'Polling a historical incident replayed an evidence trace');
    assert.equal(afterPoll.arrivals.length, quiet.arrivals, 'Polling a historical incident fired an arrival callback');
    assert.equal(await browser.evaluate(() => document.getElementById('next-inheritance').dataset.selectedVersion), before.operating_selection.selected_version_id, 'Historical polling changed the inherited selection');
    await browser.evaluate(() => document.getElementById('inspect-current').click());
    assert.ok(await browser.until(() => document.getElementById('inspection-bar').dataset.mode === 'current' &&
      document.getElementById('inspect-current').hidden && document.body.dataset.loadState === 'ready', 60000), 'The explicit return to current did not settle');
    const current = await sceneState(browser);
    assert.equal(current.wallTraces ?? 0, quiet.traces, 'Returning to current replayed an evidence trace');
    assert.equal(current.arrivals.length, quiet.arrivals, 'Returning to current fired an arrival callback');
    await browser.evaluate(() => document.querySelector('[data-station="next"]').click());
    assert.ok(await browser.until(() => !document.getElementById('next-view').hidden, 30000), 'The handover shelf did not reopen');
    assert.deepEqual(await browser.evaluate(inheritFields), initial, 'Returning to current changed the inherited choice or later experiment');
    const refused = await browser.evaluate(async ({ shiftId, selection, later }) => {
      const response = await fetch(`/api/shifts/${encodeURIComponent(shiftId)}/selections`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comparison_id: later.id, selected_version_id: selection.retained_alternative_version_id,
          rationale: 'switch after the later-condition experiment', expected_prior_selection_id: selection.id,
          client_request_id: `s33-switch-${Date.now()}` }),
      });
      return { status: response.status, detail: await response.text() };
    }, { shiftId: before.latest_shift.id, selection: before.operating_selection, later });
    assert.equal(refused.status, 409, 'A selection citing the later experiment was accepted');
    await browser.evaluate(() => document.getElementById('close-shift').click());
    assert.ok(await browser.until(() => !document.getElementById('open-next-shift').disabled, 60000), 'The closed shift offers no next shift');
    await browser.evaluate(() => document.getElementById('open-next-shift').click());
    assert.ok(await browser.until(async previous => {
      const next = await (await fetch('/api/engagements/bookshop/board')).json();
      return next.latest_shift?.id && next.latest_shift.id !== previous && document.body.dataset.loadState === 'ready';
    }, 90000, before.latest_shift.id), 'The next shift did not open');
    await waitReady(browser);
    const afterShift = await board(browser);
    assert.equal(afterShift.operating_selection?.selected_version_id, before.operating_selection.selected_version_id, 'The next shift lost the selected version');
    assert.equal(afterShift.operating_selection?.selected_content_hash, before.operating_selection.selected_content_hash, 'The next shift lost the selected hash');
    assert.equal(afterShift.operating_selection?.rationale, before.operating_selection.rationale, 'The next shift lost the rationale');
    assert.equal(afterShift.operating_selection?.retained_alternative_version_id, before.operating_selection.retained_alternative_version_id, 'The next shift lost the retained alternative');
    await browser.evaluate(() => document.querySelector('[data-station="next"]').click());
    const newShift = await browser.evaluate(inheritFields);
    assert.equal(newShift.selection, before.operating_selection.selected_version_id, 'The new shelf lost the inherited selection');
    assert.equal(newShift.experimentState, 'none', 'The previous shift later experiment is presented as current');
    assert.equal(newShift.experiment, '', 'The previous shift later experiment identity survived the new shift');
    assert.equal(newShift.observed, '', 'The previous shift observed operation survived the new shift');
    assert.equal(newShift.replaces, '', 'The previous shift replacement flag survived the new shift');
    const newScene = await sceneState(browser);
    assert.equal(newScene.wallTraces ?? 0, quiet.traces, 'Opening the next shift replayed an evidence trace');
    await browser.evaluate(() => document.querySelector('[data-view="compare"]').click());
    await browser.evaluate(() => {
      const file = document.getElementById('draft-file');
      if (file.value !== 'service.py') { file.value = 'service.py'; file.dispatchEvent(new Event('change')); }
      const editor = document.getElementById('draft-source');
      editor.value += '\n# s33 newer save\n';
      editor.dispatchEvent(new Event('input'));
      if (document.getElementById('save-draft').disabled) throw new Error('The newer save control is disabled');
      document.getElementById('save-draft').click();
    });
    assert.ok(await browser.until(() => document.getElementById('draft-source').dataset.dirty === 'false' && document.body.dataset.loadState === 'ready', 90000), 'The newer save did not settle');
    const afterSave = await board(browser);
    assert.equal(afterSave.operating_selection.id, before.operating_selection.id, 'A newer save replaced the recorded choice');
    assert.equal(afterSave.operating_selection.selected_version_id, before.operating_selection.selected_version_id, 'A newer save replaced the selected version');
    await browser.evaluate(() => document.querySelector('[data-station="next"]').click());
    const afterSaveShelf = await browser.evaluate(inheritFields);
    assert.equal(afterSaveShelf.selection, before.operating_selection.selected_version_id, 'The shelf promoted a newer save');
    const origin = await browser.evaluate(() => performance.timeOrigin);
    await browser.send('Page.reload');
    assert.ok(await browser.until(old => performance.timeOrigin !== old && document.body?.dataset.loadState === 'ready' &&
      document.getElementById('graphics-status')?.dataset.state === 'ready', 120000, origin), 'The browser-cache return did not settle');
    const reloadScene = await sceneState(browser);
    assert.equal(reloadScene.wallTraces ?? 0, quiet.traces, 'The browser-cache return replayed an evidence trace');
    assert.equal(reloadScene.later.id, null, 'The browser-cache return presented the previous later experiment as current');
    await screenshot(browser, out, 'inheritance-1280');
    await screenshot(browser, out, 'inheritance-390', 390, 844);
    await browser.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    assert.ok(await browser.until(() => document.getElementById('graphics-status')?.dataset.state === 'ready' &&
      document.querySelector('#workplace-canvas canvas'), 30000), 'The richer Bellwether scene did not settle after the layout checks');
    await browser.evaluate(() => document.querySelector('#workplace-canvas canvas').getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
    assert.ok(await browser.until(() => document.getElementById('graphics-status')?.dataset.state === 'unavailable', 30000), 'Graphics loss did not settle');
    assert.ok(await browser.evaluate(() => document.querySelector('#next-inheritance [data-inherit-field="operating-choice"] strong')?.textContent.includes(document.getElementById('next-inheritance').dataset.selectedVersion)), 'Graphics loss hid the inherited choice');
    assert.ok(await browser.evaluate(() => document.querySelector('#repair-view') !== null && document.querySelector('#handover-incidents .incident-row') !== null), 'Graphics loss erased the handover or incident tray');
    assert.deepEqual(browser.exceptions, [], 'The S33 journey raised an uncaught exception');
    await writeFile(out + '/later.json', JSON.stringify({ before: {
      shift: before.latest_shift.id, selection: before.operating_selection, later: { id: later.id, observedRun: later.observed_run_id, state: later.state, outcome: later.outcome?.status } },
      initial, history, newShift, afterShift: { shift: afterShift.latest_shift.id, selection: afterShift.operating_selection },
      refusal: refused, scene: { inherited: inheritedScene, current, new: newScene, reload: reloadScene }, quiet }, null, 2) + '\n');
    return { result: 'PASS', shift: before.latest_shift.id, historyRun: history.run, later: later.id, observed: later.observed_run_id, newShift: afterShift.latest_shift.id };
  } finally { await browser.close(); }
}
