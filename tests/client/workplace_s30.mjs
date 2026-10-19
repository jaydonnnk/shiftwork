import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { openBrowser } from './workplace_browser.mjs';

const reported = new Set(['RESERVED', 'RUNNING', 'COMPLETE', 'FAILED']);

async function typeText(browser, value) {
  for (const char of value) {
    await browser.send('Input.dispatchKeyEvent', { type: 'keyDown', key: char, text: char, unmodifiedText: char });
    await browser.send('Input.dispatchKeyEvent', { type: 'keyUp', key: char });
  }
}
async function press(browser, key) {
  const info = { Enter: { code: 'Enter', vk: 13, text: '\r' }, Escape: { code: 'Escape', vk: 27 } }[key];
  assert.ok(info, `Unsupported key ${key}`);
  await browser.send('Input.dispatchKeyEvent', { type: 'keyDown', key, code: info.code,
    windowsVirtualKeyCode: info.vk, ...(info.text ? { text: info.text, unmodifiedText: info.text } : {}) });
  await browser.send('Input.dispatchKeyEvent', { type: 'keyUp', key, code: info.code, windowsVirtualKeyCode: info.vk });
}
async function touch(browser, selector) {
  await browser.send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 1 });
  const point = await browser.evaluate(async selector => {
    const element = document.querySelector(selector);
    if (!element) throw Error(`Missing touch target ${selector}`);
    element.scrollIntoView({ block: 'center', behavior: 'instant' });
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const box = element.getBoundingClientRect(), x = box.x + box.width / 2, y = box.y + box.height / 2;
    return { x, y, covered: document.elementFromPoint(x, y)?.closest(selector) !== element };
  }, selector);
  assert.equal(point.covered, false, `Touch target ${selector} is covered`);
  await browser.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: point.x, y: point.y }] });
  await browser.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
}
async function openBoard(browser, base, hash = '#board') {
  await browser.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  await browser.send('Page.navigate', { url: base + '/' + hash });
  assert.ok(await browser.until(() => document.body?.dataset.loadState === 'ready' && document.getElementById('graphics-status')?.dataset.state === 'ready', 15000), 'S30 workbench unavailable');
}
async function createInvestigation(browser, shiftId) {
  const setup = await browser.evaluate(async shiftId => {
    const response = await fetch(`/api/shifts/${encodeURIComponent(shiftId)}/investigations`, { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source_run_id: 'run-0001',
        source_request_ordinal: 1, cause: 'the starter asks instead of using the recorded record',
        falsifier: 'a captured answer with the recorded price disproves this', public_test: 'compare the answer with the frozen public record',
        revision_of_id: null, client_request_id: `s30-owner-${Date.now()}-${Math.random().toString(36).slice(2)}` }) });
    return { ok: response.ok, status: response.status, text: await response.text() };
  }, shiftId);
  assert.ok(setup.ok, `Investigation setup failed (${setup.status}): ${setup.text}`);
  return JSON.parse(setup.text);
}

export async function runJourney(base, out, fault = '') {
  const browser = await openBrowser(base, out, fault || 'diagnostic-journey');
  try {
    await browser.send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: false });
    await browser.send('Page.navigate', { url: base + '/#board' });
    assert.ok(await browser.until(() => document.body?.dataset.loadState === 'ready' && document.getElementById('graphics-status')?.dataset.state === 'ready', 15000), 'S30 journey workbench unavailable');
    await touch(browser, '.incident-row');
    assert.ok(await browser.until(() => document.getElementById('selected-evidence')?.dataset.runId === 'run-0001', 15000), 'Touch did not open the recorded failure');
    const requestText = await browser.evaluate(async () => (await (await fetch('/api/runs/run-0001/outputs')).json())[0].request_text);
    await touch(browser, '[data-station="investigate"]');
    assert.ok(await browser.until(() => document.getElementById('failed-request')?.dataset.runId === 'run-0001', 10000), 'Failed request did not stay visible');
    assert.ok(await browser.evaluate(text => document.getElementById('failed-request').textContent.includes(text), requestText), 'Failed request text differs from the API');
    const prediction = { 'cause-input': 'the starter asks for information instead of using the recorded public record',
      'falsifier-input': 'a captured answer that cites the recorded price disproves this cause',
      'public-test-input': 'compare the captured answer with the frozen public record' };
    for (const [id, value] of Object.entries(prediction)) {
      await browser.evaluate(id => { const field = document.getElementById(id); field.scrollIntoView({ block: 'center', behavior: 'instant' }); field.focus(); }, id);
      await typeText(browser, value);
    }
    assert.deepEqual(await browser.evaluate(() => ['cause-input', 'falsifier-input', 'public-test-input'].map(id => document.getElementById(id).value)), Object.values(prediction), 'Keyboard text was not entered');
    await browser.evaluate(() => document.getElementById('append-investigation').focus());
    await press(browser, 'Enter');
    assert.ok(await browser.until(() => document.querySelectorAll('.investigation-entry').length >= 1, 15000), 'Keyboard did not record the prediction');
    assert.equal(await browser.evaluate(() => document.getElementById('failed-request').dataset.runId), 'run-0001', 'The failed request left the panel after recording');
    await touch(browser, '[data-station="compare"]');
    assert.ok(await browser.until(() => !document.getElementById('draft-source').disabled, 15000), 'Draft editor unavailable');
    const beforeSave = await browser.evaluate(() => {
      const editor = document.getElementById('draft-source');
      editor.scrollIntoView({ block: 'center', behavior: 'instant' }); editor.focus();
      editor.setSelectionRange(editor.value.length, editor.value.length); globalThis.__s30Editor = editor;
      return { value: editor.value, start: editor.selectionStart, end: editor.selectionEnd };
    });
    await typeText(browser, ' s30 draft');
    const typed = await browser.evaluate(() => ({ value: document.getElementById('draft-source').value,
      start: document.getElementById('draft-source').selectionStart, end: document.getElementById('draft-source').selectionEnd,
      dirty: document.getElementById('draft-source').dataset.dirty }));
    assert.equal(typed.value, beforeSave.value + ' s30 draft', 'Keyboard edit did not reach the draft');
    assert.equal(typed.dirty, 'true', 'Keyboard edit was not marked dirty');
    await browser.evaluate(() => document.getElementById('save-draft').focus());
    await press(browser, 'Enter');
    assert.ok(await browser.until(() => document.getElementById('draft-source').dataset.dirty === 'false' && document.body.dataset.loadState === 'ready', 15000), 'Keyboard draft save did not complete');
    assert.deepEqual(await browser.evaluate(() => ({ same: document.getElementById('draft-source') === globalThis.__s30Editor,
      value: document.getElementById('draft-source').value })), { same: true, value: typed.value }, 'The draft save replaced the editor node or changed its bytes');
    await touch(browser, '[data-station="investigate"]');
    assert.ok(await browser.until(() => !document.getElementById('run-diagnostic').disabled, 15000), 'Diagnostic control unavailable');
    const beforeRun = await browser.evaluate(async () => {
      const board = await (await fetch('/api/engagements/bookshop/board')).json();
      return { selection: document.getElementById('selection-summary').textContent, events: document.getElementById('event-detail').textContent,
        ledger: board.ledger_event_count, totals: board.ledger_totals, assist: document.getElementById('assist-standing').textContent };
    });
    await browser.evaluate(() => document.getElementById('run-diagnostic').focus());
    await press(browser, 'Enter');
    assert.ok(await browser.until(() => globalThis.__s30Accepts?.some(item => ['COMPLETE', 'FAILED'].includes(item.state)), 30000), 'The diagnostic did not report COMPLETE or FAILED');
    assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready' && !document.getElementById('run-diagnostic').disabled, 15000), 'The final diagnostic refresh did not settle');
    const receipts = await browser.evaluate(() => ({ accepts: globalThis.__s30Accepts,
      result: document.getElementById('diagnostic-result').textContent, assist: document.getElementById('assist-standing').textContent,
      selection: document.getElementById('selection-summary').textContent, events: document.getElementById('event-detail').textContent }));
    for (const [index, accept] of receipts.accepts.entries()) {
      const label = index === 0 ? 'initial' : 'polled';
      assert.ok(reported.has(accept.tagState), `${label} diagnostic exposed an unreported state: ${accept.tagState}`);
      assert.equal(accept.tagState, accept.state, `${label} diagnostic publication did not update the test bench (${accept.state})`);
      if (accept.missing) assert.equal(accept.tagMissing, String(accept.missing), `${label} diagnostic publication hid missing evidence`);
    }
    assert.ok(receipts.accepts.some(item => item.state === 'RESERVED'), 'The initial RESERVED state was not observed');
    assert.ok(receipts.accepts.some(item => ['COMPLETE', 'FAILED'].includes(item.state)), 'The final reported state was not observed');
    assert.equal(receipts.assist, beforeRun.assist, 'The diagnostic changed assistance standing');
    const afterRun = await browser.evaluate(async () => {
      const board = await (await fetch('/api/engagements/bookshop/board')).json();
      return { selection: document.getElementById('selection-summary').textContent, events: document.getElementById('event-detail').textContent,
        ledger: board.ledger_event_count, totals: board.ledger_totals };
    });
    assert.deepEqual(afterRun, { selection: beforeRun.selection, events: beforeRun.events, ledger: beforeRun.ledger, totals: beforeRun.totals }, 'The diagnostic moved operational selection or the consequence wall');
    const unexpected = browser.commands.filter(url => !new URL(url).pathname.match(/^\/api\/shifts\/[^/]+\/(investigations|artifact|experiments)$/));
    assert.deepEqual(unexpected, [], 'The S30 journey submitted an unexpected command');
    assert.ok(!browser.commands.some(url => /\/(selections|runs|close)$/.test(url)), 'The diagnostic submitted an operator command');
    assert.deepEqual(browser.exceptions, [], 'S30 journey raised an uncaught exception');
    assert.deepEqual(browser.requests.filter(url => !url.startsWith(base) && !url.startsWith('data:')), [], 'S30 journey requested an external asset');
    await writeFile(out + '/journey.json', JSON.stringify({ accepts: receipts.accepts, beforeRun, afterRun, commands: browser.commands }, null, 2) + '\n');
    return { result: 'PASS', accepts: receipts.accepts.map(item => item.state) };
  } finally { await browser.close(); }
}

export async function runOwnership(base, out, mode, fault = '') {
  assert.ok(['generation', 'intent', 'history', 'context', 'inspection'].includes(mode), 'Unknown ownership mode');
  const browserFault = fault || (['generation', 'intent', 'history'].includes(mode) ? 'diagnostic-hold-post' : 'diagnostic-observe');
  const browser = await openBrowser(base, out, browserFault);
  try {
    await openBoard(browser, base);
    const shiftId = await browser.evaluate(async () => (await (await fetch('/api/engagements/bookshop/board')).json()).latest_shift.id);
    const investigation = await createInvestigation(browser, shiftId);
    await browser.evaluate(() => globalThis.__s29Refresh());
    assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready', 15000), 'Owner setup refresh failed');
    if (['generation', 'intent', 'history'].includes(mode)) {
      await browser.evaluate(() => document.getElementById('run-diagnostic').click());
      await new Promise(resolve => setTimeout(resolve, 500));
      if (mode === 'generation') {
        await browser.evaluate(() => globalThis.__s29Refresh());
        assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready', 15000), 'Generation refresh did not settle');
      }
      if (mode === 'intent') {
        await browser.evaluate(() => document.querySelector('[data-station="customers"]').click());
        assert.ok(await browser.until(() => document.getElementById('panel-title').textContent === 'Customer evidence', 5000), 'Intent station change did not settle');
      }
      if (mode === 'history') {
        await browser.evaluate(() => document.querySelector('.incident-row').click());
        assert.ok(await browser.until(() => document.getElementById('selected-evidence')?.dataset.runId === 'run-0001', 15000), 'History navigation did not settle');
      }
      browser.releaseImports();
      assert.ok(await browser.until(() => globalThis.__s30Accepts?.length >= 1, 15000), 'The delayed diagnostic response was not accepted');
      const accept = await browser.evaluate(() => globalThis.__s30Accepts[0]);
      assert.notEqual(accept.latestReason, 'diagnostic', `${mode} ownership published a stale diagnostic update`);
      await writeFile(out + '/ownership.json', JSON.stringify({ mode, fault, accept, publications: await browser.evaluate(() => globalThis.__s30Publications) }, null, 2) + '\n');
      return { result: 'PASS', mode, reason: accept.latestReason };
    }
    const experiment = await browser.evaluate(async ({ shiftId, investigationId }) => {
      const board = await (await fetch('/api/engagements/bookshop/board')).json();
      const response = await fetch(`/api/shifts/${encodeURIComponent(shiftId)}/experiments`, { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind: 'DIAGNOSTIC', investigation_id: investigationId,
          candidate_a_version_id: board.latest_saved_version_id, client_request_id: `s30-owner-${Date.now()}` }) });
      return await response.json();
    }, { shiftId, investigationId: investigation.id });
    const outcome = await browser.evaluate(async ({ mode, experiment }) => {
      const owner = globalThis.__s30State();
      const before = globalThis.__s30Publications.length;
      if (mode === 'context') globalThis.__s30Accept({ ...owner, slug: 'gtm' }, experiment);
      else { globalThis.__s30SetInspection('history', 'run-0001'); globalThis.__s30Accept(owner, experiment); globalThis.__s30SetInspection('current', null); }
      return { before, after: globalThis.__s30Publications.length, publications: globalThis.__s30Publications.slice(before) };
    }, { mode, experiment });
    assert.equal(outcome.after, outcome.before, `${mode} ownership published a stale diagnostic update`);
    assert.deepEqual(outcome.publications, [], `${mode} ownership published a stale diagnostic update`);
    await writeFile(out + '/ownership.json', JSON.stringify({ mode, fault, outcome }, null, 2) + '\n');
    return { result: 'PASS', mode };
  } finally { await browser.close(); }
}

export async function runExpanded(base, out, fault = '') {
  const browser = await openBrowser(base, out, fault || 'expand-observe');
  try {
    await openBoard(browser, base, '#compare');
    const before = await browser.evaluate(() => {
      const editor = document.getElementById('draft-source');
      editor.value += '\n# s30 expand draft'; editor.dispatchEvent(new Event('input', { bubbles: true }));
      editor.focus(); editor.setSelectionRange(5, 23, 'backward'); globalThis.__s30Editor = editor;
      return { value: editor.value, start: editor.selectionStart, end: editor.selectionEnd, direction: editor.selectionDirection, focus: editor === document.activeElement };
    });
    assert.equal(before.focus, true, 'The dirty editor was not focused before expansion');
    const point = await browser.evaluate(() => {
      const button = document.getElementById('expand-work'); button.scrollIntoView({ block: 'center', behavior: 'instant' });
      const box = button.getBoundingClientRect(); return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
    });
    await browser.send('Input.dispatchMouseEvent', { type: 'mousePressed', ...point, button: 'left', clickCount: 1 });
    await browser.send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...point, button: 'left', clickCount: 1 });
    assert.ok(await browser.until(() => document.querySelector('main').dataset.expanded === 'true', 3000), 'Pointer activation did not expand the workbench');
    const expanded = await browser.evaluate(() => {
      const editor = document.getElementById('draft-source'), panel = document.getElementById('station-panel');
      return { same: editor === globalThis.__s30Editor, value: editor.value, focus: editor === document.activeElement,
        start: editor.selectionStart, end: editor.selectionEnd, direction: editor.selectionDirection,
        aria: document.getElementById('expand-work').getAttribute('aria-expanded'),
        width: panel.getBoundingClientRect().width, overflow: document.documentElement.scrollWidth <= innerWidth };
    });
    assert.deepEqual({ same: expanded.same, value: expanded.value, focus: expanded.focus, start: expanded.start,
      end: expanded.end, direction: expanded.direction, aria: expanded.aria, overflow: expanded.overflow },
      { same: true, value: before.value, focus: true, start: 5, end: 23, direction: 'backward', aria: 'true', overflow: true },
      'Expanding moved focus off the dirty editor or changed its bytes');
    const width = expanded.width;
    assert.ok(width > 800 && width <= 1120, `Expanded workbench width ${width} is outside the approved range`);
    const stopped = await browser.evaluate(async () => {
      const before = globalThis.__workplaceProbe.frames;
      globalThis.__workplaceApply('customers');
      await new Promise(resolve => setTimeout(resolve, 150));
      return { frames: globalThis.__workplaceProbe.frames - before, pulse: globalThis.__workplaceControls.pulse() };
    });
    assert.equal(stopped.frames, 0, 'Expanded work kept drawing');
    assert.equal(stopped.pulse, false, 'Expanded work kept an active emphasis');
    const suspended = await browser.evaluate(() => {
      const latest = globalThis.__s29Latest(), view = JSON.parse(JSON.stringify(latest.view));
      view.tests.diagnostic = { id: 's30-expanded', shiftId: view.context.shiftId, kind: 'DIAGNOSTIC', state: 'RUNNING',
        evidenceClass: 'TRUSTED_LOCAL', contextHash: 'synthetic', outcomeStatus: null, candidates: [], observedRunId: null,
        trials: [{ ordinal: 1, candidateLabel: 'A', runId: 'synthetic-run', versionId: 'synthetic-version', state: 'COMPLETE', evidenceMode: 'TRUSTED_LOCAL', missingEvidenceCount: 0 }] };
      globalThis.__s29Host().publish({ kind: 'accepted', view, generation: latest.generation, intent: latest.intent, reason: 'synthetic-test' });
      return { pulse: globalThis.__workplaceControls.pulse(), applied: globalThis.__workplaceControls.state().applied };
    });
    assert.equal(suspended.pulse, false, 'Expanded work kept an active emphasis');
    await browser.send('Emulation.setDeviceMetricsOverride', { width: 640, height: 900, deviceScaleFactor: 1, mobile: false });
    await new Promise(resolve => setTimeout(resolve, 120));
    assert.deepEqual(await browser.evaluate(() => { const editor = document.getElementById('draft-source');
      return { same: editor === globalThis.__s30Editor, value: editor.value, focus: editor === document.activeElement,
        start: editor.selectionStart, end: editor.selectionEnd, overflow: document.documentElement.scrollWidth <= innerWidth }; }),
      { same: true, value: before.value, focus: true, start: 5, end: 23, overflow: true }, 'Resizing the expanded work changed editor continuity');
    await browser.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    await browser.evaluate(() => document.getElementById('expand-work').focus());
    await press(browser, 'Escape');
    assert.ok(await browser.until(() => document.querySelector('main').dataset.expanded === 'false', 3000), 'Escape did not restore the workbench');
    assert.ok(await browser.until(() => document.getElementById('graphics-status').dataset.state === 'ready', 12000), 'Restore did not return the room');
    const restored = await browser.evaluate(async () => {
      const editor = document.getElementById('draft-source'), frames = globalThis.__workplaceProbe.frames;
      editor.focus();
      await new Promise(resolve => setTimeout(resolve, 150));
      return { same: editor === globalThis.__s30Editor, value: editor.value, focus: editor === document.activeElement,
        start: editor.selectionStart, end: editor.selectionEnd, frames: globalThis.__workplaceProbe.frames - frames,
        pulse: globalThis.__workplaceControls.pulse() };
    });
    assert.deepEqual({ same: restored.same, value: restored.value, focus: restored.focus, start: restored.start,
      end: restored.end }, { same: true, value: before.value, focus: true, start: 5, end: 23 },
      'Restore changed editor continuity');
    assert.ok(restored.frames <= 2, 'Restore replayed suspended work');
    assert.equal(restored.pulse, false, 'Restore replayed a suspended emphasis');
    await browser.evaluate(() => document.querySelector('#workplace-canvas canvas').getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
    assert.ok(await browser.until(() => document.getElementById('graphics-status').dataset.state === 'unavailable', 5000), 'Graphics failure did not reach fallback');
    assert.deepEqual(await browser.evaluate(() => { const editor = document.getElementById('draft-source');
      return { same: editor === globalThis.__s30Editor, value: editor.value, focus: editor === document.activeElement,
        start: editor.selectionStart, end: editor.selectionEnd }; }),
      { same: true, value: before.value, focus: true, start: 5, end: 23 }, 'Graphics failure changed the dirty editor');
    await browser.evaluate(() => document.querySelector('[data-graphics-retry]').click());
    assert.ok(await browser.until(() => document.getElementById('graphics-status').dataset.state === 'ready', 12000), 'Explicit graphics retry did not rebuild the room');
    assert.deepEqual(browser.exceptions, [], 'Expanded work raised an uncaught exception');
    await writeFile(out + '/expanded.json', JSON.stringify({ before, width, stopped, suspended, restored }, null, 2) + '\n');
    return { result: 'PASS', width, framesAfterRestore: restored.frames };
  } finally { await browser.close(); }
}

export async function runMotion(base, out, fault = '') {
  const browser = await openBrowser(base, out, fault || 'motion-observe');
  try {
    await openBoard(browser, base);
    const started = await browser.evaluate(() => {
      const latest = globalThis.__s29Latest(), view = JSON.parse(JSON.stringify(latest.view));
      view.tests.diagnostic = { id: 's30-synthetic', shiftId: view.context.shiftId, kind: 'DIAGNOSTIC', state: 'RUNNING',
        evidenceClass: 'TRUSTED_LOCAL', contextHash: 'synthetic', outcomeStatus: null, candidates: [], observedRunId: null,
        trials: [{ ordinal: 1, candidateLabel: 'A', runId: 'synthetic-run', versionId: 'synthetic-version', state: 'COMPLETE', evidenceMode: 'TRUSTED_LOCAL', missingEvidenceCount: 0 }] };
      globalThis.__s29Host().publish({ kind: 'accepted', view, generation: latest.generation, intent: latest.intent, reason: 'synthetic-test' });
      return { pulse: globalThis.__workplaceControls.pulse(), emissive: globalThis.__workplaceControls.state().emissive };
    });
    assert.equal(started.pulse, true, 'The accepted test update did not start a 160ms emphasis');
    assert.ok(started.emissive > 0, 'The accepted test update did not emphasize the test stand');
    await browser.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
    await new Promise(resolve => setTimeout(resolve, 60));
    const settled = await browser.evaluate(() => ({ pulse: globalThis.__workplaceControls.pulse(),
      emissive: globalThis.__workplaceControls.state().emissive, matches: matchMedia('(prefers-reduced-motion: reduce)').matches,
      frames: globalThis.__workplaceProbe.frames }));
    assert.equal(settled.matches, true, 'Reduced motion was not emulated');
    assert.equal(settled.pulse, false, 'An active motion preference change did not cancel the emphasis');
    assert.equal(settled.emissive, 0, 'An active motion preference change left an emphasis visible');
    await new Promise(resolve => setTimeout(resolve, 150));
    const after = await browser.evaluate(() => globalThis.__workplaceProbe.frames);
    assert.ok(after - settled.frames <= 1, 'The cancelled emphasis kept drawing');
    await browser.send('Emulation.setEmulatedMedia', { features: [] });
    await writeFile(out + '/motion.json', JSON.stringify({ started, settled, afterFrames: after - settled.frames }, null, 2) + '\n');
    return { result: 'PASS' };
  } finally { await browser.close(); }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [mode, base, out, ...rest] = process.argv.slice(2);
  const result = mode === 'journey' ? await runJourney(base, out, rest[0] ?? '')
    : mode === 'expanded' ? await runExpanded(base, out, rest[0] ?? '')
    : mode === 'motion' ? await runMotion(base, out, rest[0] ?? '')
    : mode === 'ownership' ? await runOwnership(base, out, rest[0], rest[1] ?? '')
    : (() => { throw Error(`Unknown S30 browser mode: ${mode}`); })();
  console.log(JSON.stringify(result));
}
