import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { once } from 'node:events';
import { chromePath, pythonPath } from './env.mjs';

// Fault-injection mode: with SHIFTWORK_FAULT set, the harness serves a mutated
// in-memory copy of the production app.js to the browser and then requires this
// run to fail at the named rendered-evidence assertion. The repository file is
// never modified. Each needle must match exactly one production behavior.
const FAULTS = {
  candidateRace: { needle: 'const previousShiftId = state.loadedShiftId;', replacement: 'const previousShiftId = state.board?.latest_shift?.id;', expect: 'Overlapping refresh retained a previous shift candidate' },
  unloadWarning: { needle: "  if (!hasUnsavedDraft()) return;\n  event.preventDefault();\n  event.returnValue = '';", replacement: '  return;', expect: 'Dirty browser reload did not show a beforeunload warning' },
  transientErrorLeak: { needle: 'clearData(error.message);', replacement: "clearData(error.message + ' S21_TEST_PROVIDER_SECRET');", expect: 'Client DOM contains private material (refresh-error)' },
  invalidatedPolling: { needle: "while (!['FINALIZED', 'FAILED', 'INVALIDATED'].includes(experiment.state) && Date.now() < deadline)", replacement: "while (!['FINALIZED', 'FAILED'].includes(experiment.state) && Date.now() < deadline)", expect: 'Timed out waiting for terminal comparison to release the draft editor' },
  draftSave: { needle: "[$('draft-file').value]: $('draft-source').value", replacement: "[$('draft-file').value]: $('draft-source').value + '\\n# wrong saved bytes'", expect: 'Draft editor saved different bytes' },
  unsavedFreeze: { needle: "function hasUnsavedDraft() { return $('draft-source').dataset.dirty === 'true'; }", replacement: 'function hasUnsavedDraft() { return false; }', expect: 'Unsaved draft can freeze a candidate' },
  candidateReload: { needle: 'state.candidates[candidate.label] ??= { id: candidate.artifact_version_id, content_hash: candidate.artifact_content_hash };', replacement: 'void candidate;', expect: 'Reload lost an API-backed frozen candidate' },
  candidateReset: { needle: 'state.candidates = { A: null, B: null };\n    }', replacement: 'void state.candidates;\n    }', expect: 'Next shift presents the previous comparison as current' },
  clientLeak: { needle: "document.body.dataset.loadState = board.latest_shift ? 'ready' : 'empty';", replacement: "document.body.dataset.loadState = board.latest_shift ? 'ready' : 'empty'; document.body.dataset.privateMaterial = 'S21_TEST_PROVIDER_SECRET';", expect: 'Client DOM contains private material' },
  executionPurpose: { needle: "['purpose', 'Execution purpose', humanize(run.purpose)]", replacement: "['purpose', 'Execution purpose', 'experiment']", expect: 'Execution purpose differs from the run API' },
  executionMode: { needle: "['mode', 'Evidence mode', run.evidence_mode ?? 'unknown']", replacement: "['mode', 'Evidence mode', 'ISOLATED_LIVE']", expect: 'Execution mode differs from the run API' },
  executionVersion: { needle: "['version', 'Executed version', run.artifact_version_id]", replacement: "['version', 'Executed version', 'ver-wrong']", expect: 'Execution version differs from the run API' },
  executionSnapshot: { needle: "['snapshot', 'Frozen public snapshot', output.public_shop_snapshot_hash ?? 'unknown']", replacement: "['snapshot', 'Frozen public snapshot', 'wrong-snapshot']", expect: 'Execution snapshot differs from the run API' },
  comparisonPurpose: { needle: "['purpose', 'Purpose', humanize(compare.kind)]", replacement: "['purpose', 'Purpose', 'operation']", expect: 'Comparison purpose differs from the experiment API' },
  comparisonMode: { needle: "['mode', 'Evidence mode', compare.context_evidence_class]", replacement: "['mode', 'Evidence mode', 'ISOLATED_LIVE']", expect: 'Comparison mode differs from the experiment API' },
  comparisonContext: { needle: "['context', 'Frozen context', compare.context_hash]", replacement: "['context', 'Frozen context', 'wrong-context']", expect: 'Comparison context differs from the experiment API' },
  comparisonHistory: { needle: "['history', 'Operational history', 'Unchanged by experiments']", replacement: "['history', 'Operational history', 'changed']", expect: 'Comparison hides unchanged operational history' },
  outcomeBlocker: { needle: "eligibility.blocking_reason_codes.join(', ')", replacement: "'WRONG_BLOCKER'", expect: 'renders the wrong blocking reasons' },
  selectedVersion: { needle: "`${choice.selected_version_id} · ${choice.selected_content_hash} · ${humanize(choice.state)}`", replacement: "`wrong-version · ${choice.selected_content_hash} · ${humanize(choice.state)}`", expect: 'Workbench selected version differs from the board API' },
  requirementVersion: { needle: 'const version = state.operatingVersion ?? state.board.latest_version;', replacement: 'const version = state.board.latest_version;', expect: 'Requirements differ from the exact operating version' },
  syntheticEvent: { needle: "ledger.append(element('span', 'Synthetic scenario', 'synthetic'))", replacement: "ledger.append(element('span', 'unlabelled', 'synthetic'))", expect: 'Missing rendered label: event' },
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
    needle: "humanize(event.event_type)), element('small'",
    replacement: "'sale completed'), element('small'",
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
  outcomeMetric: {
    needle: "        const value = element('dd', metrics[key] ?? 'unknown');",
    replacement: "        const value = element('dd', key === 'useful_completions' ? 99 : (metrics[key] ?? 'unknown'));",
    expect: 'renders the wrong useful_completions',
  },
  outcomeEligibility: {
    needle: '      card.dataset.eligible = String(eligibility.eligible);',
    replacement: '      card.dataset.eligible = String(!eligibility.eligible);',
    expect: 'renders the wrong eligibility',
  },
  outcomeLabelBinding: {
    needle: '      card.dataset.candidateLabel = label;',
    replacement: "      card.dataset.candidateLabel = 'A';",
    expect: 'renders no outcome card bound to candidate B',
  },
  inheritRationale: {
    needle: "      ['Recorded rationale', 'rationale', choice.rationale],",
    replacement: "      ['Recorded rationale', 'rationale', 'REVIEW_WRONG_RATIONALE'],",
    expect: 'does not display the original rationale',
  },
  inheritAlternative: {
    needle: "      ['Retained alternative', 'retained-alternative', choice.retained_alternative_version_id],",
    replacement: "      ['Retained alternative', 'retained-alternative', 'REVIEW_WRONG_ALTERNATIVE'],",
    expect: 'does not display the retained alternative',
  },
  inheritRequirementHash: {
    needle: "      ['Frozen requirement hash', 'requirement-hash', requirements.requirement_set_hash],",
    replacement: "      ['Frozen requirement hash', 'requirement-hash', requirements.visible_check_set_hash],",
    expect: 'does not display the inherited requirement hash',
  },
  inheritObservedRun: {
    needle: "    experiment.dataset.observedRunId = later.observed_run_id ?? '';",
    replacement: "    experiment.dataset.observedRunId = '';",
    expect: 'does not show the observed operation',
  },
  inheritSeparation: {
    // Must append after replaceChildren() wipes the region; a fault inserted
    // before it is erased by the render and never reaches the assertion.
    needle: '    history.replaceChildren();',
    replacement: "    history.replaceChildren();\n    history.append(element('p', state.stationView?.latest_experiment?.id ?? '', 'evidence-meta'));",
    expect: 'presents the hypothetical experiment as operational history',
  },
  inheritHistoryReturn: {
    needle: "$('inspect-current').addEventListener('click', returnToCurrent);",
    replacement: 'void returnToCurrent;',
    expect: 'Timed out waiting for the explicit return to current',
  },
  inheritLaterSelection: {
    needle: "    experiment.dataset.selectedVersion = choice?.selected_version_id ?? '';",
    replacement: "    experiment.dataset.selectedVersion = '';",
    expect: 'The later-condition region does not preserve the original selection',
  },
  inheritStaleLater: {
    needle: `    delete experiment.dataset.experimentId;
    delete experiment.dataset.observedRunId;
    delete experiment.dataset.selectedVersion;
    delete experiment.dataset.retainedAlternative;
    delete experiment.dataset.replacesSelection;`,
    replacement: '    void experiment.dataset;',
    expect: 'The previous shift later experiment identity survived the new shift',
  },
};

const url = process.argv[2] ?? 'http://127.0.0.1:8009';
assert.ok(['127.0.0.1', 'localhost'].includes(new URL(url).hostname), 'Browser checks target a local preview only');
const inheritDemo = process.argv.includes('--inherit-demo');
const fault = process.env.SHIFTWORK_FAULT ?? null;
if (fault) {
  assert.ok(FAULTS[fault], `Unknown fault: ${fault}`);
  assert.ok(!process.argv.includes('--exercise-run'), 'Fault runs never consume a preview attempt');
}
const browser = chromePath;
const profile = await mkdtemp(path.join(tmpdir(), 'shiftwork-browser-'));
const artifacts = path.resolve(process.env.SHIFTWORK_ARTIFACT_DIR ?? (fault ? `artifacts/slice21-faults/${fault}` : 'artifacts/slice21'));
await mkdir(path.dirname(artifacts), { recursive: true });
await mkdir(artifacts);
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
async function screenshot(name, force = false) {
  if (fault && !force) return;
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

async function assertPublicDOM(label = 'final') {
  const surface = await evaluate(() => ({ rendered_text: document.body.innerText, serialized_dom: document.body.outerHTML }));
  await writeFile(path.join(artifacts, `dom-${label}.json`), JSON.stringify(surface), { flag: 'wx' });
  const script = `import json,sys
sys.path.insert(0,'tests')
from leakscan import sealed_identity_strings
from shiftwork.gateway.redaction import serialized_contains
needles=(*sealed_identity_strings(),'S21_TEST_PROVIDER_SECRET','S21_TEST_SANDBOX_SECRET')
surface=json.load(sys.stdin)
controls=all(serialized_contains({**surface,'serialized_dom':surface['serialized_dom']+form},needle) for needle in needles for form in (needle,needle.replace('\\\\','/'),json.dumps(needle)[1:-1]))
print(json.dumps({'needles':len(needles),'controls':controls,'clean':not any(serialized_contains(surface,needle) for needle in needles)}))`;
  const scanned = await new Promise((resolve, reject) => {
    const scan = spawn(pythonPath, ['-c', script], { stdio: ['pipe', 'pipe', 'pipe'] });
    let out = '', err = '';
    const timeout = setTimeout(() => { scan.kill(); reject(new Error('DOM scanner timed out')); }, 30000);
    scan.stdout.on('data', data => { out += data; });
    scan.stderr.on('data', data => { err += data; });
    scan.once('error', error => { clearTimeout(timeout); reject(error); });
    scan.once('exit', code => { clearTimeout(timeout); if (code !== 0) reject(new Error(`DOM scanner failed: ${err}`)); else { try { resolve(JSON.parse(out)); } catch (error) { reject(error); } } });
    scan.stdin.end(JSON.stringify(surface));
  });
  await writeFile(path.join(artifacts, `dom-scan-${label}.json`), JSON.stringify(scanned, null, 2), { flag: 'wx' });
  assert.ok(scanned.controls, 'DOM scanner controls did not detect every serialized needle form');
  assert.ok(scanned.clean, `Client DOM contains private material (${label})`);
  return scanned.needles;
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
      for (const [field, value] of Object.entries({ purpose: humanize(run.purpose), mode: run.evidence_mode ?? 'unknown', version: run.artifact_version_id, snapshot: output.public_shop_snapshot_hash ?? 'unknown' })) {
        if (panel.querySelector(`[data-execution-field="${field}"] strong`)?.textContent !== value) throw new Error(`Execution ${field} differs from the run API`);
      }
      const workbench = document.querySelector('[data-selection-field="executed-version"] strong');
      if (workbench?.textContent !== `${run.artifact_version_id} · ${run.id}`) throw new Error('Workbench execution differs from the run API');
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
      } else {
        const expected = run.purpose === 'LEGACY_OPERATION' ? 'Historical public context unknown.'
          : checks.some(check => check.run_id === run.id && check.public_check_id?.startsWith('task:'))
            ? 'Task checks use the frozen public state' : 'No public comparison record';
        if (!recordStep.textContent.includes(expected)) throw new Error('Rendered no-record state is missing');
      }
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

async function verifyRenderedRequirements() {
  const board = await (await fetch('/api/engagements/bookshop/board')).json();
  const id = board.operating_selection?.selected_version_id ?? board.latest_version?.id;
  if (!id) return;
  const version = await (await fetch(`/api/artifact-versions/${encodeURIComponent(id)}`)).json();
  const field = name => document.querySelector(`[data-requirement-field="${name}"] strong`)?.textContent;
  const humanize = value => value.toLowerCase().replaceAll('_', ' ');
  if (field('requirement-version') !== `${version.id} · ${version.content_hash}`) throw new Error('Requirements differ from the exact operating version');
  if (field('committed-constraint') !== version.contract.must_never.map(humanize).join(', ')) throw new Error('Requirements hide a committed constraint');
  if (field(board.operating_selection ? 'operating-stance' : 'latest-saved-stance') !== Object.values(version.contract.selections).map(humanize).join(', ')) throw new Error('Requirements show the wrong stance');
  if (field('response-time-limit') !== `${version.contract.response_time_limit_ms} ms`) throw new Error('Requirements show the wrong response limit');
  if (field('frozen-requirement-hash') !== (board.inherited_requirements?.requirement_set_hash ?? 'No qualifying comparison selected yet')) throw new Error('Requirements show the wrong frozen hash');
}

async function verifyReloadWarning() {
  const dialogs = [];
  let navigations = 0;
  const listener = ({ data }) => {
    const message = JSON.parse(data);
    if (message.sessionId !== session) return;
    if (message.method === 'Page.frameNavigated' && !message.params.frame.parentId) navigations++;
    if (message.method === 'Page.javascriptDialogOpening') {
      dialogs.push(message.params);
      send('Page.handleJavaScriptDialog', { accept: false }).catch(error => console.error(error));
    }
  };
  socket.addEventListener('message', listener);
  const reload = async () => {
    const before = { dialogs: dialogs.length, navigations };
    await send('Page.reload');
    const deadline = Date.now() + 10000;
    while (dialogs.length === before.dialogs && navigations === before.navigations && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 25));
    assert.ok(dialogs.length > before.dialogs || navigations > before.navigations, 'Reload neither navigated nor showed a dialog');
    await ready();
    return dialogs.slice(before.dialogs);
  };
  const activateEditor = async () => {
    const box = await evaluate(() => {
      document.querySelector('[data-view="compare"]').click();
      const source = document.getElementById('draft-source');
      source.scrollIntoView({ block: 'center' });
      const rect = source.getBoundingClientRect();
      return { x: rect.x + 20, y: rect.y + 20 };
    });
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', ...box, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', ...box, button: 'left', clickCount: 1 });
    assert.ok(await evaluate(() => navigator.userActivation.hasBeenActive), 'Reload warning proof needs native user activation');
  };
  const edit = async () => {
    await activateEditor();
    await evaluate(() => { const source = document.getElementById('draft-source'); source.setSelectionRange(source.value.length, source.value.length); });
    await send('Input.insertText', { text: '\n# native unsaved reload probe' });
    const actual = await evaluate(() => ({ active: navigator.userActivation.hasBeenActive, dirty: document.getElementById('draft-source').dataset.dirty, text: document.getElementById('draft-source').value }));
    assert.ok(actual.active, 'Reload warning proof needs native user activation');
    assert.equal(actual.dirty, 'true');
    return actual.text;
  };
  try {
    await activateEditor();
    assert.deepEqual(await reload(), [], 'Clean reload showed an unnecessary warning');
    const edited = await edit();
    await evaluate(() => document.getElementById('refresh').click()); await ready();
    assert.equal(await evaluate(() => document.getElementById('draft-source').value), edited, 'In-app Refresh lost dirty text');
    await evaluate(() => {
      window.__saveFetch = window.fetch;
      window.fetch = (...args) => args[1]?.method === 'PUT' ? Promise.resolve(new Response(JSON.stringify({ detail: 'Offline save 503' }), { status: 503 })) : window.__saveFetch(...args);
      document.getElementById('save-draft').click();
    });
    await evaluate(async () => {
      const deadline = Date.now() + 10000;
      while (!document.getElementById('draft-error').textContent.includes('Offline save 503') && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 25));
      if (!document.getElementById('draft-error').textContent.includes('Offline save 503')) throw new Error('Save 503 was not rendered');
      window.fetch = window.__saveFetch;
    });
    assert.equal(await evaluate(() => document.getElementById('draft-source').value), edited, 'Save 503 lost dirty text');
    await assertPublicDOM('draft-save-error');
    const warning = await reload();
    assert.equal(warning.length, 1, 'Dirty browser reload did not show a beforeunload warning');
    assert.equal(warning[0].type, 'beforeunload');
    assert.equal(await evaluate(() => document.getElementById('draft-source').value), edited, 'Dismissing the warning lost dirty text');
    assert.equal(await evaluate(() => document.getElementById('draft-source').dataset.dirty), 'true');
    await screenshot('dirty-reload-dismissed', true);
    await evaluate(() => document.getElementById('discard-draft-edit').click());
    assert.deepEqual(await reload(), [], 'Discarded edit retained an unnecessary warning');
    const saved = await edit();
    await evaluate(() => document.getElementById('save-draft').click());
    await evaluate(async () => {
      const deadline = Date.now() + 10000;
      while ((document.getElementById('draft-source').dataset.dirty !== 'false' || document.body.dataset.loadState !== 'ready') && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 25));
      if (document.getElementById('draft-source').dataset.dirty !== 'false') throw new Error('Successful save stayed dirty');
    });
    assert.deepEqual(await reload(), [], 'Successful save retained an unnecessary warning');
    assert.equal(await evaluate(() => document.getElementById('draft-source').value), saved, 'Clean reload did not restore saved server text');
    const report = { nativeActivation: true, dirtyDialog: warning[0], dismissedEditRetained: true, refreshRetained: true, save503Retained: true, cleanReloadWarnings: 0, discardWarnings: 0, savedReloadWarnings: 0, protection: 'warning only, no browser-local persistence' };
    await writeFile(path.join(artifacts, 'reload-warning.json'), JSON.stringify(report, null, 2), { flag: 'wx' });
    return report;
  } finally { socket.removeEventListener('message', listener); }
}

async function verifyCandidateRace() {
  const result = await evaluate(async () => {
    const wait = async check => {
      const deadline = Date.now() + 10000;
      while (!check()) { if (Date.now() > deadline) throw new Error('Candidate race setup did not settle'); await new Promise(resolve => setTimeout(resolve, 10)); }
    };
    const boardOf = async () => (await (await fetch('/api/engagements/bookshop/board')).json());
    document.querySelector('[data-view="compare"]').click();
    document.getElementById('freeze-candidate-a').click();
    await wait(() => !document.getElementById('freeze-candidate-a').disabled);
    const old = { shift: (await boardOf()).latest_shift.id, candidate: document.querySelector('#candidate-list strong').textContent };
    if (old.candidate === 'not frozen yet') throw new Error('Candidate race requires a frozen candidate');
    // Refresh and error/reconnect in the SAME shift must retain this candidate.
    document.getElementById('refresh').click(); await wait(() => document.body.dataset.loadState === 'ready');
    if (document.querySelector('#candidate-list strong').textContent !== old.candidate) throw new Error('Same-shift refresh lost its frozen candidate');
    const original = window.fetch;
    window.fetch = async () => { throw new Error('Offline race reconnect'); };
    document.getElementById('refresh').click(); await wait(() => document.body.dataset.loadState === 'error');
    window.fetch = original;
    document.getElementById('refresh').click(); await wait(() => document.body.dataset.loadState === 'ready');
    if (document.querySelector('#candidate-list strong').textContent !== old.candidate) throw new Error('Same-shift reconnect lost its frozen candidate');
    document.querySelector('[data-view="next"]').click(); document.getElementById('close-shift').click();
    await wait(() => !document.getElementById('open-next-shift').disabled);
    let calls = 0;
    let firstFinished;
    const finished = new Promise(resolve => { firstFinished = resolve; });
    window.fetch = async (...args) => {
      if (!String(args[0]).endsWith('/board') || ++calls !== 1) return original(...args);
      await new Promise(resolve => setTimeout(resolve, 400));
      try { return await original(...args); } finally { firstFinished(); }
    };
    document.getElementById('open-next-shift').click();
    await wait(() => document.body.dataset.loadState === 'loading' && calls === 1);
    document.getElementById('refresh').click(); await wait(() => document.body.dataset.loadState === 'ready');
    await finished;
    // Allow the discarded older refresh's dependent requests to complete.
    await new Promise(resolve => setTimeout(resolve, 200));
    window.fetch = original;
    const board = await boardOf();
    document.querySelector('[data-view="compare"]').click();
    const actual = [...document.querySelectorAll('#candidate-list strong')].map(node => node.textContent);
    document.getElementById('refresh').click(); await wait(() => document.body.dataset.loadState === 'ready');
    return { old, shift: board.latest_shift.id, latestSaved: board.latest_saved_version_id, actual, afterRefresh: [...document.querySelectorAll('#candidate-list strong')].map(node => node.textContent), sameShiftRefresh: true, reconnect: true, delayedBoardGets: 1 };
  });
  await writeFile(path.join(artifacts, 'candidate-race.json'), JSON.stringify(result, null, 2), { flag: 'wx' });
  await screenshot('candidate-race', true);
  assert.notEqual(result.old.shift, result.shift);
  assert.equal(result.latestSaved, null);
  assert.deepEqual(result.actual, ['not frozen yet', 'not frozen yet'], 'Overlapping refresh retained a previous shift candidate');
  assert.deepEqual(result.afterRefresh, ['not frozen yet', 'not frozen yet'], 'Ordinary refresh retained a previous shift candidate');
  return result;
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
  try { await ready(); }
  catch (error) { throw new Error(`${error.message}; page exceptions: ${exceptions.map(item => item.exception?.description ?? item.text).join(' | ')}`); }
  const publicDOMNeedles = await assertPublicDOM('initial');
  assert.equal(await evaluate(() => document.querySelectorAll('[data-station]').length), 10);
  const matrix = [];
  for (const width of [1280, 778, 640, 390]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
    await evaluate(() => { document.querySelector('[data-station="service"]').click(); window.scrollTo(0, 0); });
    const boardLabels = await labels();
    assert.deepEqual(boardLabels, ['board', 'incidents', 'ledger']);
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, `${width}px page overflows`);
    await screenshot(`board-${width}`);
    await evaluate(() => document.querySelector('[data-station="customers"]').click());
    const latestRunId = await evaluate(async () => (await (await fetch('/api/engagements/bookshop/board')).json()).latest_run.id);
    const result = await evaluate(verifyRenderedCustomerEvidence, latestRunId, 2);
    const customerLabels = await labels();
    assert.deepEqual(customerLabels, ['board', 'run', 'event']);
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, `${width}px evidence overflows`);
    await screenshot(`customers-${width}`);
    matrix.push({ width, ...result, labels: [...boardLabels, ...customerLabels] });
  }
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  const journey = [];
  // Full native mechanics run in every baseline. A value fault reuses that
  // proven harness and runs its own value assertions without repeated captures.
  if (!fault || fault === 'stationFocus') {
  await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  for (const width of [1280, 778, 640, 390]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
    for (const input of ['keyboard', 'touch']) for (const [view, station, panelId] of [
      ['board', 'service', 'board-view'], ['contract', 'owner', 'board-view'],
      ['investigate', 'investigate', 'investigate-view'], ['compare', 'compare', 'compare-view'],
      ['next', 'next', 'next-view'],
    ]) {
      const point = await evaluate(view => {
        const link = document.querySelector(`[data-view="${view}"]`);
        if (!link) throw new Error(`Missing journey link ${view}`);
        link.scrollIntoView({ block: 'center', behavior: 'instant' });
        link.focus({ preventScroll: true });
        const rect = link.getBoundingClientRect();
        return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
      }, view);
      if (input === 'keyboard') {
        await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' });
        await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
      } else {
        await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [point] });
        await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
      }
      await evaluate(async (view, station, panelId, width) => {
        const panel = document.getElementById('station-panel');
        const deadline = Date.now() + 5000;
        while (Date.now() < deadline && (location.hash !== `#${view}` || document.activeElement !== panel)) await new Promise(resolve => setTimeout(resolve, 20));
        if (location.hash !== `#${view}` || document.querySelector('[data-view][aria-current]')?.dataset.view !== view) throw new Error(`Journey ${view} loses its URL or active link`);
        if (document.querySelector('[data-station][aria-pressed="true"]')?.dataset.station !== station || document.getElementById(panelId).hidden) throw new Error(`Journey ${view} opens the wrong station`);
        if (document.activeElement !== panel) throw new Error(`Journey ${view} does not focus its panel`);
        if (width <= 760 && (panel.getBoundingClientRect().top < -2 || panel.getBoundingClientRect().top > innerHeight - 100)) throw new Error('Narrow station selection does not bring the panel into reach');
        if (document.documentElement.scrollWidth > document.documentElement.clientWidth) throw new Error(`Journey ${view} overflows at ${width}px`);
        if (getComputedStyle(panel).scrollBehavior !== 'auto' || !matchMedia('(prefers-reduced-motion: reduce)').matches) throw new Error('Journey ignores reduced motion');
      }, view, station, panelId, width);
      if (view === 'contract') await evaluate(verifyRenderedRequirements);
      if (input === 'touch') await screenshot(`journey-${view}-${width}`);
      journey.push({ width, input, view });
    }
  }
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  for (const view of ['board', 'contract', 'investigate', 'compare', 'next']) {
    await send('Page.navigate', { url: `${url}/#${view}` });
    await ready();
    await evaluate(() => document.getElementById('refresh').click());
    await ready();
    assert.equal(await evaluate(() => document.querySelector('[data-view][aria-current]')?.dataset.view), view, `Deep link/refresh loses ${view}`);
  }
  await evaluate(() => { document.querySelector('[data-view="board"]').focus(); });
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 });
  assert.equal(await evaluate(() => document.activeElement?.dataset.view), 'contract', 'Journey Tab order skips Requirements');
  }
  const navigationErrors = await evaluate(async () => {
    const errors = [];
    const tick = () => new Promise(resolve => setTimeout(resolve, 20));
    document.querySelector('[data-station="customers"]').click(); await tick();
    document.querySelector('[data-station="service"]').click();
    document.querySelector('[data-station="customers"]').click(); await tick();
    if (document.getElementById('customer-view').hidden) errors.push('journey link does not reopen after station navigation');
    document.querySelector('[data-station="customers"]').click();
    document.querySelector('.skip-link').click(); await tick();
    if (document.getElementById('customer-view').hidden) errors.push('skip link changes selected view');
    return errors;
  });
  await evaluate(async () => { document.querySelector('[data-view="next"]').click(); await new Promise(resolve => setTimeout(resolve, 20)); document.getElementById('refresh').click(); });
  await ready();
  if (!(await evaluate(() => !document.getElementById('next-view').hidden && document.getElementById('panel-title').textContent === 'Next shift'))) navigationErrors.push('refresh loses Next shift');
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
  await assertPublicDOM('loading');
  assert.equal(await evaluate(() => document.getElementById('selected-evidence').hasAttribute('data-run-id')), false);
  await labels(); await screenshot('loading');
  await evaluate(() => { window.fetch = window.__fetch; window.__release(); });
  await ready();
  await evaluate(() => { window.fetch = async () => { throw new Error('Offline test: refresh to retry.'); }; document.getElementById('refresh').click(); });
  await ready('error');
  assert.equal(await evaluate(() => document.querySelectorAll('[data-body-base64], .customer-button').length), 0);
  await labels(); await screenshot('error');
  await screenshot('refresh-error', true);
  await assertPublicDOM('refresh-error');
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
  await assertPublicDOM('empty');
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
  await assertPublicDOM('malformed-output');
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
  await assertPublicDOM('assist-denial');
  const investigateLabels = await labels();
  assert.deepEqual(investigateLabels, ['board', 'failed-request', 'source', 'diagnostic']);
  for (const journey of ['compare', 'next']) {
    await evaluate(journey => document.querySelector(`[data-view="${journey}"]`).click(), journey);
    assert.equal(await evaluate(() => document.getElementById('investigate-view').hidden), true,
      `${journey} must hide the live Investigate form and diagnostic result`);
    await evaluate(() => document.querySelector('[data-station="investigate"]').click());
    assert.equal(await evaluate(() => document.getElementById('investigate-view').hidden), false,
      'Investigate must reopen after a journey placeholder');
  }
  assert.equal(await evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, '1280px investigate panel overflows');
  await screenshot('investigate-1280');
  if (process.argv.includes('--assist-demo')) {
    await evaluate(() => document.getElementById('assist-events').scrollIntoView({ block: 'center' }));
    await screenshot('assist-1280');
    await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 900, deviceScaleFactor: 1, mobile: false });
    await evaluate(() => document.getElementById('assist-events').scrollIntoView({ block: 'center' }));
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, '390px assist panel overflows');
    await screenshot('assist-390');
    await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  }
  // The inherit-demo world carries a later-condition comparison as the shift's
  // latest experiment instead of a public diagnostic, so the diagnostic panel is
  // not exercised in that mode; the Next shift assertions below are.
  const diagnostic = inheritDemo ? {
    skipped: 'inherit-demo mode asserts the Next shift station instead of running a public diagnostic',
  } : await evaluate(async investigateShift => {
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
  const selectionDemo = process.argv.includes('--selection-demo');
  const reloadWarning = process.argv.includes('--reload-warning-demo') ? await verifyReloadWarning() : null;
  const comparison = (process.argv.includes('--compare-demo') || selectionDemo) ? await evaluate(async (candidateA, candidateB, choose, blocked) => {
    const humanize = value => value.toLowerCase().replaceAll('_', ' ');
    const shiftId = (await (await fetch('/api/engagements/bookshop/board')).json()).latest_shift.id;
    const historyBefore = await (await fetch('/api/engagements/bookshop/ledger')).json();
    const incidentsBefore = (await (await fetch('/api/engagements/bookshop/board')).json()).incidents;
    const put = async files => {
      document.querySelector('[data-view="compare"]').click();
      document.getElementById('draft-file').value = 'service.py';
      document.getElementById('draft-file').dispatchEvent(new Event('change'));
      document.getElementById('draft-source').value = files['service.py'];
      document.getElementById('draft-source').dispatchEvent(new Event('input'));
      if (!document.getElementById('freeze-candidate-a').disabled || !document.getElementById('freeze-candidate-b').disabled) throw new Error('Unsaved draft can freeze a candidate');
      if (document.getElementById('save-draft').disabled) throw new Error('Draft editor does not offer to save the edit');
      document.getElementById('save-draft').click();
      await wait('the draft save', () => document.getElementById('draft-source').dataset.dirty === 'false' && document.getElementById('save-draft').disabled);
      const saved = await (await fetch(`/api/shifts/${encodeURIComponent(shiftId)}/artifact`)).json();
      if (Object.keys(saved.files).length !== Object.keys(files).length || Object.entries(files).some(([name,value]) => saved.files[name] !== value)) throw new Error('Draft editor saved different bytes');
      return saved;
    };
    const wait = async (label, check) => {
      const deadline = Date.now() + 60000;
      while (Date.now() < deadline) { if (check()) return; await new Promise(resolve => setTimeout(resolve, 60)); }
      throw new Error(`Timed out waiting for ${label}: ${document.getElementById('compare-error').textContent}`);
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
    await wait('the comparison to reach a terminal state', () => ['FINALIZED', 'FAILED', 'INVALIDATED'].map(humanize).includes(document.getElementById('compare-state').textContent.split('·').pop().trim()));
    await wait('terminal comparison to release the draft editor', () => !document.getElementById('draft-source').disabled);
    const experimentId = document.getElementById('compare-state').textContent.match(/experiment-[^\s]+/)?.[0];
    const payload = await (await fetch(`/api/experiments/${encodeURIComponent(experimentId)}`)).json();
    for (const [field, value] of Object.entries({ purpose: humanize(payload.kind), mode: payload.context_evidence_class, context: payload.context_hash })) {
      if (document.querySelector(`[data-comparison-field="${field}"] strong`)?.textContent !== value) throw new Error(`Comparison ${field} differs from the experiment API`);
    }
    if (document.querySelector('[data-comparison-field="history"] strong')?.textContent !== 'Unchanged by experiments') throw new Error('Comparison hides unchanged operational history');
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
    const summaryText = document.getElementById('compare-summary').textContent;
    for (const value of [String(payload.shared_public_denominator_requests), String(payload.protected_denominator_requests_per_candidate)]) {
      if (!summaryText.includes(value)) throw new Error(`The comparison summary hides the shared denominator ${value}`);
    }
    const missingSlots = payload.trials.filter(trial => !trial.run_id || (trial.missing_evidence?.length ?? 0)).length;
    if (!summaryText.includes(`${missingSlots} missing slot`)) throw new Error(`The comparison summary hides its ${missingSlots} missing slots`);
    for (const candidate of payload.candidates) {
      if (!summaryText.includes(candidate.artifact_version_id) || !summaryText.includes(candidate.artifact_content_hash.slice(0, 12))) throw new Error(`The comparison summary hides candidate ${candidate.label} identity`);
    }
    if (blocked) {
      const denial = [...document.querySelectorAll('#comparison-outcome .denial')].map(node => node.textContent).join(' ');
      if (!denial.includes('not comparable')) throw new Error('The blocked comparison hides its incomparable evidence');
    }
    if (payload.outcome?.status !== (blocked ? 'NOT_COMPARABLE' : 'COMPLETE')) throw new Error('The terminal comparison has the wrong outcome status');
    if (blocked && !payload.outcome.eligibility.every(item => !item.eligible && item.blocking_reason_codes.length)) throw new Error('The blocked preview has no genuine API blocker');
    const cards = [...document.querySelectorAll('#comparison-outcome .comparison-outcome-card')];
    if (cards.length !== 2) throw new Error('The comparison does not show both candidate outcome cards');
    for (const label of ['A', 'B']) {
      const card = cards.find(node => node.dataset.candidateLabel === label);
      const metrics = payload.outcome.candidate_metrics.find(item => item.candidate_label === label);
      const eligibility = payload.outcome.eligibility.find(item => item.candidate_label === label);
      if (!card) throw new Error(`The comparison renders no outcome card bound to candidate ${label}`);
      if (!metrics || !eligibility) throw new Error(`The outcome payload carries no candidate_label binding for ${label}`);
      if (card.dataset.eligible !== String(eligibility.eligible)) throw new Error(`Candidate ${label} renders the wrong eligibility`);
      const expectedHeading = `Candidate ${label} · ${eligibility.eligible ? 'eligible' : 'blocked'}${eligibility.blocking_reason_codes.length ? ` · ${eligibility.blocking_reason_codes.join(', ')}` : ''}`;
      if (card.querySelector('h4')?.textContent !== expectedHeading) throw new Error(`Candidate ${label} renders the wrong blocking reasons`);
      for (const [key, value] of Object.entries(metrics)) {
        if (key === 'candidate_version_id' || key === 'candidate_label') continue;
        const rendered = card.querySelector(`[data-metric="${key}"]`)?.textContent;
        if (rendered !== String(value ?? 'unknown')) throw new Error(`Candidate ${label} renders the wrong ${key}`);
      }
    }
    if (!document.getElementById('comparison-outcome').textContent.includes('may overlap')) throw new Error('The comparison hides non-additive incidence meaning');
    let selection = null;
    if (choose) {
      const before = await (await fetch('/api/engagements/bookshop/board')).json();
      document.getElementById('selection-rationale').value = 'A answered the required tasks in the shared trial.';
      document.getElementById('selection-rationale').dispatchEvent(new Event('input'));
      await wait('eligible A to become selectable', () => !document.getElementById('select-candidate-a').disabled);
      document.getElementById('select-candidate-a').click();
      await wait('the recorded choice', () => document.getElementById('selection-note').textContent.startsWith('Choice '));
      const after = await (await fetch('/api/engagements/bookshop/board')).json();
      selection = after.operating_selection;
      if (selection?.selected_version_id !== payload.candidates[0].artifact_version_id || selection.selected_content_hash !== payload.candidates[0].artifact_content_hash) throw new Error('The choice did not bind exact A bytes');
      if (selection.retained_alternative_version_id !== payload.candidates[1].artifact_version_id || selection.comparison_id !== experimentId || selection.prior_selection_id !== before.operating_selection.id) throw new Error('The choice lost its alternative, comparison, or prior selection');
      if (!after.latest_shift.operation_allowed || after.operating_status !== 'SELECTED') throw new Error('The choice did not unlock operation');
      const summary = document.getElementById('selection-summary').textContent;
      if (document.querySelector('[data-selection-field="operating-choice"] strong')?.textContent !== `${selection.selected_version_id} · ${selection.selected_content_hash} · ${humanize(selection.state)}`) throw new Error('Workbench selected version differs from the board API');
      if (![selection.selected_content_hash, selection.retained_alternative_version_id, selection.comparison_id, selection.requirement_set_hash, after.latest_saved_version_id].every(value => summary.includes(value))) throw new Error('The board hides selected or saved evidence');
      const note = document.getElementById('selection-note').textContent;
      if (!note.includes(`Choice ${selection.id} is recorded`)) throw new Error('The selection acknowledgement does not name the recorded choice');
      for (const value of [selection.selected_version_id, selection.selected_content_hash, selection.retained_alternative_version_id]) {
        if (!note.includes(value)) throw new Error(`The selection acknowledgement hides ${value}`);
      }
      if (!document.getElementById('select-candidate-a').disabled || !document.getElementById('select-candidate-b').disabled) throw new Error('The same comparison offers a second choice');
    }
    if (JSON.stringify(await (await fetch('/api/engagements/bookshop/ledger')).json()) !== JSON.stringify(historyBefore) || JSON.stringify((await (await fetch('/api/engagements/bookshop/board')).json()).incidents) !== JSON.stringify(incidentsBefore)) throw new Error('Comparison or choice changed operational history');
    return { experiment: experimentId, state: payload.state, outcome: payload.outcome.status, blockers: payload.outcome.eligibility.map(item => ({ candidate: item.candidate_label, reasons: item.blocking_reason_codes })), slots: payload.trials.map(trial => `${trial.execution_ordinal}:${trial.pair_ordinal}${trial.candidate_label}/${trial.workload_id}/${trial.request_count}`).join(' '), selection };
  }, await readFile('shiftwork/fixtures/artifacts/bookshop/compare_repair_a_service.py', 'utf8'), await readFile('shiftwork/fixtures/artifacts/bookshop/compare_repair_b_service.py', 'utf8'), selectionDemo, process.argv.includes('--blocked-demo')) : null;
  if (comparison) {
    await evaluate(() => document.getElementById('comparison-slots').scrollIntoView({ block: 'start' }));
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, '1280px compare panel overflows');
    await screenshot('compare-1280');
    await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 900, deviceScaleFactor: 1, mobile: false });
    await evaluate(() => document.getElementById('comparison-slots').scrollIntoView({ block: 'start' }));
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, '390px compare panel overflows');
    await screenshot('compare-390');
    if (selectionDemo) {
      await evaluate(() => document.querySelector('[data-view="contract"]').click());
      await evaluate(verifyRenderedRequirements);
      await screenshot('selected-requirements-390');
      await evaluate(() => { document.querySelector('[data-station="service"]').click(); document.getElementById('selection-summary').scrollIntoView({ block: 'start' }); });
      await screenshot('selection-390');
    }
    await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    await send('Page.navigate', { url });
    await ready();
    await evaluate(() => document.querySelector('[data-station="investigate"]').click());
    await evaluate(async diagnosticId => {
      const deadline = Date.now() + 10000;
      const panel = document.getElementById('diagnostic-result');
      while (!panel.dataset.experimentId && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 50));
      if (panel.dataset.experimentId !== diagnosticId) throw new Error(`After a reload the diagnostic panel projects ${panel.dataset.experimentId || 'nothing'} instead of the earlier diagnostic ${diagnosticId}`);
      const eligibility = [...panel.querySelectorAll('.evidence-step')].find(node => node.querySelector('.step-label')?.textContent.includes('Eligibility'))?.querySelector('[data-eligible]');
      if (!eligibility) throw new Error('After a reload the diagnostic panel renders no eligibility step');
      if (eligibility.dataset.eligible !== 'false') throw new Error('After a reload the diagnostic panel reports eligible for a shift whose latest experiment is a comparison');
      const statement = eligibility.querySelector('strong')?.textContent;
      if (statement !== 'Not eligible · this diagnostic cannot qualify a version') throw new Error(`After a reload the diagnostic panel prints the wrong eligibility statement: ${statement}`);
    }, diagnostic.experiment);
    await evaluate(async () => {
      document.querySelector('[data-view="compare"]').click();
      const id = document.getElementById('compare-state').textContent.match(/experiment-[^\s]+/)?.[0];
      const payload = await (await fetch(`/api/experiments/${encodeURIComponent(id)}`)).json();
      for (const candidate of payload.candidates) {
        const row = document.querySelector(`#candidate-list [data-candidate-label="${candidate.label}"] strong`);
        if (row?.textContent !== `${candidate.artifact_version_id} · content hash ${candidate.artifact_content_hash}`) throw new Error('Reload lost an API-backed frozen candidate');
      }
      document.querySelector('[data-view="investigate"]').click();
    });
    await screenshot('investigate-diagnostic-after-comparison-reload-1280');
    await evaluate(() => document.querySelector('[data-station="service"]').click());
  }
  let operationJourney = null;
  if (process.argv.includes('--journey-demo')) {
    assert.ok(selectionDemo, 'The continuous journey needs an explicit eligible choice');
    // The preview's starter inspections are already completed operations. A new
    // learner choice inherits into the next shift before it can operate there.
    await evaluate(() => { document.querySelector('[data-view="next"]').click(); document.getElementById('close-shift').click(); });
    await evaluate(async () => {
      const deadline = Date.now() + 10000;
      while (document.getElementById('open-next-shift').disabled && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 30));
      if (document.getElementById('open-next-shift').disabled) throw new Error('The chosen version cannot advance to its operating shift');
      document.getElementById('open-next-shift').click();
    });
    await evaluate(async priorShift => {
      const deadline = Date.now() + 10000;
      while (Date.now() < deadline) {
        const board = await (await fetch('/api/engagements/bookshop/board')).json();
        if (board.latest_shift.id !== priorShift && document.getElementById('next-state').textContent.includes(board.latest_shift.id)) return;
        await new Promise(resolve => setTimeout(resolve, 30));
      }
      throw new Error('The operating shift did not open');
    }, investigateView.shift);
    const before = await evaluate(async () => (await (await fetch('/api/engagements/bookshop/board')).json()));
    await evaluate(() => {
      document.querySelector('[data-view="board"]').click();
      const button = document.getElementById('run-shift');
      if (button.disabled) throw new Error('The selected version cannot operate');
      button.focus();
    });
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, text: '\r' });
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    operationJourney = await evaluate(async before => {
      const deadline = Date.now() + 60000;
      let board;
      while (Date.now() < deadline) {
        board = await (await fetch('/api/engagements/bookshop/board')).json();
        if (board.latest_run?.id !== before.latest_run?.id && board.latest_run?.state === 'FINALIZED'
            && document.body.dataset.loadState === 'ready'
            && document.getElementById('run-state').textContent === `${board.latest_run.id} · FINALIZED`
            && document.querySelectorAll('.customer-button').length) break;
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      const run = board.latest_run;
      if (run?.id === before.latest_run?.id || run?.state !== 'FINALIZED') throw new Error('Selected operation did not finalize');
      if (document.body.dataset.loadState !== 'ready' || document.getElementById('run-state').textContent !== `${run.id} · FINALIZED` || !document.querySelectorAll('.customer-button').length) throw new Error('The finalized operation evidence did not finish loading');
      if (run.purpose !== 'OPERATION' || run.artifact_version_id !== before.operating_selection.selected_version_id || run.selection_id !== before.operating_selection.id) throw new Error('Operation did not use the exact choice');
      const ledger = await (await fetch('/api/engagements/bookshop/ledger')).json();
      const events = ledger.events.filter(event => event.derivation?.run_id === run.id);
      if (!events.length) throw new Error('Operation has no independently checked synthetic event');
      const rows = [...document.querySelectorAll('#wall-events .wall-event')].map(row => ({ id: row.dataset.wallEvent,
        seq: row.dataset.wallSeq, source: row.dataset.wallSource, link: row.dataset.wallLink, meaning: row.dataset.wallMeaning }));
      const shown = rows.filter(row => events.some(event => row.id === `bookshop:${event.seq}:${event.hash}`));
      if (shown.length !== events.length) throw new Error('The consequence wall does not show every linked operational event');
      if (!shown.every(row => row.source === 'current' && row.link === 'linked')) throw new Error('The consequence wall mislabels the operational event');
      const status = document.getElementById('wall-status');
      if (status.dataset.runState !== 'FINALIZED' || !status.textContent.includes(`Operation ${run.id} · FINALIZED`)
          || !status.textContent.includes('Counts agree') || !status.textContent.includes('Type totals agree')) throw new Error('The consequence wall does not explain the finalized operation');
      const totals = Object.fromEntries([...document.querySelectorAll('#ledger-totals .total-row')].map(row => [row.dataset.ledgerType, Number(row.dataset.ledgerCount)]));
      if (JSON.stringify(Object.entries(totals).sort()) !== JSON.stringify(Object.entries(board.ledger_totals).sort())) throw new Error('The consequence wall totals disagree with the board record');
      return { run: run.id, version: run.artifact_version_id, mode: run.evidence_mode, selection: run.selection_id,
        events: events.map(event => event.seq), wall: shown.map(row => row.seq) };
    }, before);
    await evaluate(() => document.querySelector('[data-station="customers"]').click());
    operationJourney.evidence = await evaluate(verifyRenderedCustomerEvidence, operationJourney.run, 1);
    await labels();
    await screenshot('selected-operation-1280');
    await evaluate(() => { document.querySelector('[data-view="next"]').click(); document.getElementById('close-shift').click(); });
    await evaluate(async () => {
      const deadline = Date.now() + 10000;
      while (document.getElementById('open-next-shift').disabled && Date.now() < deadline) await new Promise(resolve => setTimeout(resolve, 30));
      if (document.getElementById('open-next-shift').disabled) throw new Error('Closed shift offers no next shift');
      document.getElementById('open-next-shift').click();
    });
    operationJourney.nextShift = await evaluate(async before => {
      const deadline = Date.now() + 10000;
      let board;
      while (Date.now() < deadline) {
        board = await (await fetch('/api/engagements/bookshop/board')).json();
        if (board.latest_shift.id !== before.latest_shift.id && document.getElementById('next-state').textContent.includes(board.latest_shift.id)) break;
        await new Promise(resolve => setTimeout(resolve, 30));
      }
      if (board.latest_shift.id === before.latest_shift.id || board.operating_selection.selected_version_id !== before.operating_selection.selected_version_id || board.operating_selection.rationale !== before.operating_selection.rationale) throw new Error('Next shift lost the exact choice or rationale');
      if (!document.querySelector('[data-inherit-field="operating-choice"] strong')?.textContent.includes(before.operating_selection.selected_version_id)) throw new Error('Next shift hides its inherited choice');
      return board.latest_shift.id;
    }, before);
    await screenshot('continuous-next-shift-1280');
    await evaluate(() => {
      document.querySelector('[data-view="compare"]').click();
      if (document.querySelectorAll('#comparison-slots .comparison-slot').length || document.querySelector('#candidate-list strong')?.textContent !== 'not frozen yet') throw new Error('Next shift presents the previous comparison as current');
      document.querySelector('[data-view="next"]').click();
    });
  }
  let inheritDemoReport = null;
  if (inheritDemo) {
    const inherit = await evaluate(async () => {
      const humanize = value => value.toLowerCase().replaceAll('_', ' ');
      const wait = async (label, check) => {
        const deadline = Date.now() + 60000;
        while (Date.now() < deadline) { if (check()) return; await new Promise(resolve => setTimeout(resolve, 60)); }
        throw new Error(`Timed out waiting for ${label}`);
      };
      const boardOf = async () => (await (await fetch('/api/engagements/bookshop/board')).json());
      document.querySelector('[data-station="next"]').click();
      if (document.getElementById('next-view').hidden) throw new Error('The Next shift station does not open its own panel');
      const board = await boardOf();
      const shiftId = board.latest_shift.id;
      const stationView = await (await fetch(`/api/shifts/${encodeURIComponent(shiftId)}/investigations`)).json();
      const selected = board.operating_selection;
      if (!selected) throw new Error('The inherit preview carries no operating selection to display');
      const inheritedBefore = {
        selection: document.getElementById('next-inheritance').dataset.selectedVersion,
        retained: document.getElementById('next-inheritance').dataset.retainedAlternative,
        experiment: document.getElementById('next-experiment').dataset.experimentId,
      };
      if (!document.querySelector('#handover-incidents .incident-row')) throw new Error('The handover shelf has no unresolved incident to inspect');
      document.querySelector('#handover-incidents .incident-row').click();
      await wait('the historical incident to open', () => document.getElementById('inspection-bar').dataset.mode === 'history' &&
        !document.getElementById('inspect-current').hidden && document.getElementById('selected-evidence').dataset.runId);
      const historicalRun = document.getElementById('selected-evidence').dataset.runId;
      const historyHelp = document.getElementById('next-help').textContent;
      await new Promise(resolve => setTimeout(resolve, 1300));
      if (document.getElementById('inspection-bar').dataset.mode !== 'history') throw new Error('Ordinary polling left the historical inspection');
      document.getElementById('inspect-current').click();
      await wait('the explicit return to current', () => document.getElementById('inspection-bar').dataset.mode === 'current' &&
        document.getElementById('inspect-current').hidden && document.body.dataset.loadState === 'ready');
      document.querySelector('[data-station="next"]').click();
      const inheritedAfter = {
        selection: document.getElementById('next-inheritance').dataset.selectedVersion,
        retained: document.getElementById('next-inheritance').dataset.retainedAlternative,
        experiment: document.getElementById('next-experiment').dataset.experimentId,
      };
      if (JSON.stringify(inheritedBefore) !== JSON.stringify(inheritedAfter)) throw new Error('Returning to current changed the inherited choice or later experiment');
      if (!historyHelp.includes('Return to the current shift')) throw new Error('The historical inspection does not explain the explicit return');
      const inheritField = name => document.querySelector(`#next-inheritance [data-inherit-field="${name}"] strong`)?.textContent ?? '';
      if (!inheritField('operating-choice').includes(selected.id) || !inheritField('operating-choice').includes(selected.selected_version_id)) throw new Error('The station does not display the inherited operating choice');
      if (inheritField('rationale') !== selected.rationale) throw new Error('The station does not display the original rationale');
      if (inheritField('selected-hash') !== selected.selected_content_hash) throw new Error('The station does not display the selected content hash');
      if (inheritField('retained-alternative') !== selected.retained_alternative_version_id) throw new Error('The station does not display the retained alternative');
      if (inheritField('draft-base') !== board.draft_base_version_id || board.draft_base_version_id !== selected.selected_version_id) throw new Error('The displayed draft base is not the exact selection');
      if (!inheritField('latest-saved').includes('none in this shift')) throw new Error('The station hides that no latest save exists in the inherited shift');
      const testsField = name => document.querySelector(`#next-tests [data-inherit-field="${name}"] strong`)?.textContent ?? '';
      if (testsField('requirement-set') !== board.inherited_requirements.requirement_set_id) throw new Error('The station does not display the inherited requirement set id');
      if (testsField('requirement-hash') !== board.inherited_requirements.requirement_set_hash) throw new Error('The station does not display the inherited requirement hash');
      if (testsField('visible-check-hash') !== board.inherited_requirements.visible_check_set_hash) throw new Error('The station does not display the inherited visible check set hash');
      const history = document.getElementById('next-history');
      if (history.dataset.ledgerEvents !== String(board.ledger_event_count) || history.dataset.incidents !== String(board.incidents.length)) throw new Error('The recorded-history region does not match the board counters');
      if (history.dataset.chainStatus !== board.chain_status) throw new Error('The recorded-history region does not report the verified chain');
      for (const limit of board.unresolved_limits) if (!history.textContent.includes(limit)) throw new Error(`The recorded-history region hides the limit in force: ${limit}`);
      const later = stationView.latest_experiment?.kind === 'LATER_CONDITION_COMPARISON' ? stationView.latest_experiment : null;
      if (!later) throw new Error('The inherit preview holds no later-condition experiment to separate');
      const laterVersions = Object.fromEntries(later.candidates.map(candidate => [candidate.label, candidate.artifact_version_id]));
      if (laterVersions.A !== selected.selected_version_id || laterVersions.B !== selected.retained_alternative_version_id) throw new Error('The later experiment did not re-test the original selected and retained versions');
      const laterRuns = new Set(later.trials.map(trial => trial.run_id).filter(Boolean));
      if (laterRuns.has(board.latest_run?.id)) {
        if (history.dataset.latestRun !== '' || history.textContent.includes(board.latest_run.id)) throw new Error('The recorded-history region shows the hypothetical experiment slot run as operational history');
        if (!history.textContent.includes('hypothetical experiment below')) throw new Error('The recorded-history region does not point its missing newest run at the hypothetical experiment');
      } else if (board.latest_run?.id) {
        if (history.dataset.latestRun !== board.latest_run.id || !history.textContent.includes(board.latest_run.id)) throw new Error('The recorded-history region does not show the latest recorded run');
      }
      const experiment = document.getElementById('next-experiment');
      if (experiment.dataset.experimentId !== later.id) throw new Error('The hypothetical region does not carry the later-condition experiment');
      if (experiment.dataset.observedRunId !== later.observed_run_id) throw new Error('The hypothetical region does not show the observed operation');
      if (experiment.dataset.selectedVersion !== selected.selected_version_id ||
          experiment.dataset.retainedAlternative !== selected.retained_alternative_version_id ||
          experiment.dataset.replacesSelection !== 'false') throw new Error('The later-condition region does not preserve the original selection');
      if (experiment.dataset.outcomeStatus !== later.outcome.status) throw new Error('The hypothetical region does not show the experiment outcome');
      if (!experiment.textContent.includes(later.condition.public_label)) throw new Error('The hypothetical region does not show the observed condition label');
      if (history.textContent.includes(later.id)) throw new Error('The recorded-history region presents the hypothetical experiment as operational history');
      if (!document.getElementById('next-view').textContent.includes('hypothetical')) throw new Error('The station does not label the later-condition experiment as hypothetical');
      const refused = await fetch(`/api/shifts/${encodeURIComponent(shiftId)}/selections`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ comparison_id: later.id, selected_version_id: selected.retained_alternative_version_id, rationale: 'switch after the later-condition experiment', expected_prior_selection_id: selected.id, client_request_id: `inherit-switch-${Date.now()}` }) });
      if (refused.status !== 409) throw new Error(`A switch citing the later-condition experiment returned ${refused.status} instead of 409`);
      document.getElementById('close-shift').click();
      await wait('the closed shift to offer the next one', () => !document.getElementById('open-next-shift').disabled);
      document.getElementById('open-next-shift').click();
      const deadline = Date.now() + 60000;
      let after = board;
      while (Date.now() < deadline && after.latest_shift.id === shiftId) { await new Promise(resolve => setTimeout(resolve, 80)); after = await boardOf(); }
      if (after.latest_shift.id === shiftId) throw new Error('Opening the next shift did not change the board shift');
      await wait('the Next shift station to show the new shift', () => document.getElementById('next-state').textContent.includes(after.latest_shift.id));
      if (after.operating_selection?.selected_version_id !== selected.selected_version_id || after.operating_selection?.selected_content_hash !== selected.selected_content_hash) throw new Error('The next shift did not inherit the exact selected version and hash');
      if (after.operating_selection?.rationale !== selected.rationale || after.operating_selection?.retained_alternative_version_id !== selected.retained_alternative_version_id) throw new Error('The next shift did not inherit the rationale or retained alternative');
      if (inheritField('rationale') !== selected.rationale || inheritField('retained-alternative') !== selected.retained_alternative_version_id) throw new Error('The station lost the inherited rationale or alternative after the shift change');
      if (document.getElementById('next-experiment').dataset.experimentState !== 'none') throw new Error('The hypothetical region still shows the previous shift experiment as current');
      const clearedLater = document.getElementById('next-experiment').dataset;
      if (clearedLater.experimentId || clearedLater.observedRunId || clearedLater.selectedVersion ||
          clearedLater.retainedAlternative || clearedLater.replacesSelection) throw new Error('The previous shift later experiment identity survived the new shift');
      if (document.getElementById('next-history').textContent.includes(shiftId)) throw new Error('The recorded-history region mixes the previous shift identity into the new shift');
      return { shift: shiftId, nextShift: after.latest_shift.id, experiment: later.id, observedRun: later.observed_run_id, rationale: selected.rationale, retained: selected.retained_alternative_version_id, limits: board.unresolved_limits.length, historicalRun, historicalPollingStayedHistorical: true, historyHelp };
    });
    await evaluate(() => document.getElementById('next-inheritance').scrollIntoView({ block: 'start' }));
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, '1280px next-shift panel overflows');
    await screenshot('next-shift-1280');
    await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 900, deviceScaleFactor: 1, mobile: false });
    await evaluate(() => document.getElementById('next-inheritance').scrollIntoView({ block: 'start' }));
    assert.equal(await evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth), false, '390px next-shift panel overflows');
    await screenshot('next-shift-390');
    await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    inheritDemoReport = inherit;
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
  const candidateRace = process.argv.includes('--candidate-race-demo') ? await verifyCandidateRace() : null;
  await assertPublicDOM();
  await writeFile(path.join(artifacts, 'review-regressions.json'), JSON.stringify({ reloadWarning, candidateRace }, null, 2), { flag: 'wx' });
  const report = { matrix, journey, operationJourney, publicDOMNeedles, investigateStation: { ...investigateView, diagnostic }, assistDemo: process.argv.includes('--assist-demo') ? 'recorded double, hint and accepted patch attribution' : 'not enabled', compareDemo: comparison ?? 'not enabled', nextShiftDemo: inheritDemoReport ?? 'not enabled', navigationAndStaleIncident: 'PASS', keyboard: 'PASS (evaluator and customer Enter/Tab)', reducedMotion: 'PASS', states: ['loading', 'error', 'empty', 'no incidents', 'malformed body', 'no public record'], repairWithoutIncident: 'blocked', literalUntrustedText: 'PASS', realRunButton: operationJourney ? 'PASS (selected operation via native Enter)' : process.argv.includes('--exercise-run') ? 'PASS' : 'not exercised in this run', labelRemovalMutations: 'caught in every visible region', ordinalMutation: 'caught', renderedEvidence: 'exact answer, public record, verdict, event, investigation and diagnostic text against the API payload', narrowStationReach: 'native touch brings the panel into reach at 640/390', incidentNavigationFocus: 'keyboard activation focuses the selected request', downloadedBytes: 'exact', uncaughtExceptions: exceptions.length };
  await writeFile(path.join(artifacts, 'browser-report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} catch (error) {
  await screenshot('assertion-failure', true).catch(() => {});
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
