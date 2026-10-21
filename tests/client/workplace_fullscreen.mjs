// S36 and S37 full-screen workplace checks (Gate 3 section 13.9).
// Each check passes clean; with --fault NAME the harness serves one in-memory
// mutation of a production file and the run must fail at that check's named
// assertion. Repository files are never modified.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { once } from 'node:events';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromePath } from './env.mjs';

// One fault per guard. `file` is the served path, `needle` must occur exactly once.
// A fault run executes only the check its expected assertion names, so one fault
// cannot be masked by an earlier check that it also happens to break.
export const FAULTS = {
  'skip-offset': { file: '/workplace-scene.js',
    needle: 'if(inset>0) camera.setViewOffset(width,height,-inset/2,0,width,height); else camera.clearViewOffset();',
    replacement: 'camera.clearViewOffset();', expect: 'inspector_keeps_stations_readable: the room is not centred in the uncovered stage' },
  'no-clamp': { file: '/app.js', needle: 'const minLeft = inspectorCover && point.x >= inspectorCover ? inspectorCover + 8 : 8;',
    replacement: 'const minLeft = 8;', expect: 'inspector_keeps_stations_readable: a station tag is under the inspector' },
  'tag-outside': { file: '/app.js',
    needle: "button.style.setProperty('--tag-x', `${Math.round(left)}px`);",
    replacement: "button.style.setProperty('--tag-x', `${Math.round(left) + 2000}px`);",
    expect: 'inspector_keeps_stations_readable: a station tag is outside the viewport' },
  'overlap-fallback': { file: '/app.js',
    needle: '      ?? inside.reduce((best, spot) => overlap(box(spot)) < overlap(box(best)) ? spot : best, inside[0] ?? candidates[0]);',
    replacement: '      ?? candidates[0];', expect: 'inspector_keeps_stations_readable: a station tag covers another station tag' },
  'leak-selection': { file: '/workplace-story.js',
    needle: '    live,\n', replacement: '    live: operating ? `${live} · ${operating.selectionId}` : live,\n',
    expect: 'main_view_has_no_internal_identifiers: the main view shows' },
  'stack-order': { file: '/styles.css', needle: '.room { order: 1;', replacement: '.room { order: -1;',
    expect: 'narrow_stack_reach: the narrow stack is out of order' },
  'stack-overflow': { file: '/styles.css', needle: '.status-fields dd { margin: 0;',
    replacement: '.status-fields dd { min-width: 900px; margin: 0;', expect: 'narrow_stack_reach: the page scrolls horizontally' },
  'small-target': { file: '/styles.css', needle: '.station { position: static; min-height: 44px;',
    replacement: '.room-hotspots .station { min-height: 30px !important; max-height: 30px; overflow: hidden; }\n.station { position: static; min-height: 44px;', expect: 'narrow_stack_reach: a main-view control is smaller than 44 by 44' },
  'no-reach': { file: '/app.js', needle: '  if (!narrowLayout()) return;\n  const panel', replacement: '  return;\n  const panel',
    expect: 'narrow_stack_reach: selected work is out of reach' },
  // S37 story layer.
  'chip-order': { file: '/styles.css', needle: '  .step-chip { order: 0; }\n', replacement: '  .step-chip { order: 3; }\n',
    expect: 'narrow_stack_reach: the step chip or next action is out of order' },
  'next-unreachable': { file: '/styles.css', needle: '#next-action-go { min-height: 44px; }', replacement: '#next-action-go { min-height: 44px; visibility: hidden; }',
    expect: 'narrow_stack_reach: the next action is out of reach' },
  'next-runs-shift': { file: '/app.js',
    needle: "$('next-action-go').addEventListener('click', () => activateStation(storyGuide?.stationId ?? state.station));",
    replacement: "document.getElementById('next-action-go').addEventListener('click', () => document.getElementById('run-shift').click());",
    expect: 'next_action_navigates_only: fresh shift next action opened' },
  'next-posts': { file: '/app.js',
    needle: "$('next-action-go').addEventListener('click', () => activateStation(storyGuide?.stationId ?? state.station));",
    replacement: "document.getElementById('next-action-go').addEventListener('click', () => { activateStation(storyGuide?.stationId ?? state.station); fetch('/api/engagements/bookshop/board', { method: 'POST' }).catch(() => {}); });",
    expect: 'next_action_navigates_only: fresh shift next action sent' },
  'both-actions': { file: '/styles.css', needle: '  .world[data-inspector="open"] .next-action { display: none; }\n', replacement: '',
    expect: 'main_view_shows_one_of_each: fresh shift shows 2 next actions or inspector footers' },
  'two-owner-lines': { file: '/app.js', needle: "  text('owner-bubble-text', owner ?? '');\n",
    replacement: "  text('owner-bubble-text', owner ?? '');\n  if (owner) document.getElementById('story-layer').append(Object.assign(document.getElementById('owner-bubble').cloneNode(true), { id: '' }));\n",
    expect: 'main_view_shows_one_of_each: investigating shows 2 owner' },
  'draft-enables': { file: '/app.js',
    needle: "for (const id of ['cause-input', 'falsifier-input']) $(id).addEventListener('input', () => renderGuide());",
    replacement: "for (const id of ['cause-input', 'falsifier-input']) $(id).addEventListener('input', () => { renderGuide(); document.getElementById('run-comparison').disabled = false; });",
    expect: "guide_never_credits_unsent_text: a cause draft changed a control's disabled state" },
  'draft-counts': { file: '/app.js',
    needle: "for (const id of ['cause-input', 'falsifier-input']) $(id).addEventListener('input', () => renderGuide());",
    replacement: "for (const id of ['cause-input', 'falsifier-input']) $(id).addEventListener('input', () => { renderGuide(); document.getElementById('investigation-tag').textContent = '1 recorded'; });",
    expect: 'guide_never_credits_unsent_text: a cause draft changed the investigation count' },
  'chip-leak': { file: '/app.js', needle: "  text('step-chip-name', storyGuide.step ? storyGuide.name : '');",
    replacement: "  text('step-chip-name', storyGuide.step ? `${storyGuide.name} ${view.run?.id ?? ''}` : '');",
    expect: 'main_view_has_no_internal_identifiers: the main view shows' },
  'picker-skips-guard': { file: '/app.js', needle: "  $('workplace-board').value = slug;\n  await switchWorkplace();",
    replacement: "  state.slug = slug; state.generation += 1;\n  await refresh();",
    expect: 'picker_uses_switch_guard: a dirty draft did not block the picker start' },
  'picker-stays': { file: '/app.js', needle: "  if (userIntent) $('shift-picker').hidden = true;\n", replacement: '',
    expect: 'picker_uses_switch_guard: choosing a station leaves the picker over the room' },
};

// Forbidden on the main view (Gate 3 section 13.6): identities from the API's ID
// formats in shiftwork/ (f"run-{...}", f"sel-{...}", f"cr-{...}", f"inv-{...},
// f"out-{...}" and the other prefixes below), 64-hex content and requirement
// hashes, ledger sequence numbers, and the API's upper-case Literal spellings in
// shiftwork/api/schemas.py. Version labels (ver-0002) are allowed.
const ID_PREFIXES = ['run', 'sel', 'cr', 'inv', 'out', 'experiment', 'assist', 'capture', 'context', 'disc', 'draw',
  'reservation', 'src', 'workload', 'shift'];
const ENUMS = ['AVAILABLE', 'AWAITING_OPERATOR_REVIEW', 'DIAGNOSTIC', 'QUALIFYING_COMPARISON', 'LATER_CONDITION_COMPARISON',
  'EXPERIMENT', 'OPERATION', 'LEGACY_OPERATION', 'HINT', 'DIAGNOSIS', 'PATCH_PROPOSAL', 'NEEDS_FIRST_CHOICE',
  'STARTER_BASELINE', 'SELECTED', 'INVALIDATED', 'OPEN', 'RESOLVED', 'CLOSED_UNRESOLVED', 'PENDING', 'COMPLETE', 'FAILED',
  'QUEUED', 'RUNNING', 'CAPTURED', 'FINALIZED', 'RECORDED_INSPECTION', 'TRUSTED_LOCAL', 'ISOLATED_LIVE', 'RESERVED',
  'STANDARD', 'LEGACY_FIRST_CHOICE', 'LEARNER_CHOICE', 'VALID', 'local_process', 'policy_answer', 'safety_route',
  'owner_assignment', 'pipeline_write', 'INCIDENT_OPENED', 'INCIDENT_RESOLVED', 'OWNER_ASSIGNED', 'HUMAN_HANDOFF'];
export const FORBIDDEN = [
  { name: 'prefixed identity', pattern: new RegExp(`\\b(?:${ID_PREFIXES.join('|')})-[0-9A-Za-z][0-9A-Za-z_-]*`), sample: 'run-0002' },
  { name: 'check identity', pattern: /\bcr-[0-9A-Za-z_-]+/, sample: 'cr-PUBLIC-1-2' },
  { name: '64-hex hash', pattern: /\b[0-9a-f]{64}\b/, sample: 'a'.repeat(64) },
  { name: 'abbreviated hash', pattern: /\b[0-9a-f]{12,63}\b/, sample: '230d6f8aeb3eff61' },
  { name: 'ledger sequence', pattern: /\bseq(?:uence)?\s*#?\d+|#\d+\b/i, sample: 'seq 12' },
  { name: 'API enum spelling', pattern: new RegExp(`\\b(?:${ENUMS.join('|')})\\b`), sample: 'FINALIZED' },
];
export const scan = text => FORBIDDEN.filter(rule => rule.pattern.test(text)).map(rule => rule.name);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

export async function openBrowser(base, out, fault = '', { zoom = 1 } = {}) {
  assert.ok(base.startsWith('http://127.0.0.1:'), 'Only owned local previews are allowed');
  assert.ok(/^\/(?:private\/)?tmp\/shiftwork-s3[67]-[^/]+(?:\/|$)/.test(path.resolve(out)), 'S36 and S37 receipts must use /tmp/shiftwork-s36-* or /tmp/shiftwork-s37-*');
  const patch = fault ? FAULTS[fault] : null;
  if (fault) assert.ok(patch, `Unknown S36 fault ${fault}`);
  await mkdir(out, { recursive: true });
  const profile = await mkdtemp(path.join(out, 'profile-'));
  if (zoom !== 1) {
    await mkdir(path.join(profile, 'Default'));
    await writeFile(path.join(profile, 'Default/Preferences'), JSON.stringify({ partition: { default_zoom_level: { x: Math.log(zoom) / Math.log(1.2) } } }));
  }
  const child = spawn(chromePath, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0',
    '--window-size=1280,900', `--user-data-dir=${profile}`, 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
  const endpoint = await new Promise((resolve, reject) => {
    let stderr = ''; const timer = setTimeout(() => reject(Error('Chrome startup timed out')), 15000);
    child.once('error', reject);
    child.stderr.on('data', data => { stderr += data; const m = stderr.match(/DevTools listening on (ws:\/\/\S+)/); if (m) { clearTimeout(timer); resolve(m[1]); } });
  });
  const socket = new WebSocket(endpoint); await once(socket, 'open');
  let session = null, sequence = 0, patched = 0;
  const pending = new Map(), exceptions = [], commands = [], harness = [];
  function send(method, params = {}, scoped = true) {
    return new Promise((resolve, reject) => {
      const id = ++sequence, timer = setTimeout(() => { pending.delete(id); reject(Error(`CDP timeout: ${method}`)); }, 120000);
      pending.set(id, { resolve, reject, timer });
      socket.send(JSON.stringify({ id, method, params, ...(scoped && session ? { sessionId: session } : {}) }));
    });
  }
  async function intercept({ requestId, request }) {
    const url = new URL(request.url);
    if (url.origin !== new URL(base).origin) return send('Fetch.failRequest', { requestId, errorReason: 'BlockedByClient' });
    if (!patch || url.pathname !== patch.file) return send('Fetch.continueRequest', { requestId });
    const response = await fetch(request.url);
    const source = await response.text();
    const count = source.split(patch.needle).length - 1;
    if (count !== 1) harness.push(`Fault ${fault} anchor matched ${count} times in ${patch.file}`);
    patched += 1;
    const body = Buffer.from(source.replace(patch.needle, patch.replacement)).toString('base64');
    return send('Fetch.fulfillRequest', { requestId, responseCode: 200, body,
      responseHeaders: [{ name: 'Content-Type', value: response.headers.get('content-type') }, { name: 'Cache-Control', value: 'no-store' }] });
  }
  socket.addEventListener('message', ({ data }) => {
    const m = JSON.parse(data);
    if (m.method === 'Runtime.exceptionThrown') exceptions.push(m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text);
    if (m.method === 'Network.requestWillBeSent' && m.params.request.method !== 'GET') commands.push(m.params.request.url);
    if (m.method === 'Fetch.requestPaused') intercept(m.params).catch(error => harness.push(error.message));
    const p = pending.get(m.id); if (!p) return; pending.delete(m.id); clearTimeout(p.timer);
    m.error ? p.reject(Error(m.error.message)) : p.resolve(m.result);
  });
  const target = await send('Target.createTarget', { url: 'about:blank' }, false);
  session = (await send('Target.attachToTarget', { targetId: target.targetId, flatten: true }, false)).sessionId;
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
  await send('Network.setCacheDisabled', { cacheDisabled: true });
  await send('Fetch.enable', { patterns: [{ urlPattern: '*' }] });
  async function evaluate(fn, ...args) {
    const r = await send('Runtime.evaluate', { expression: `(${fn.toString()})(...${JSON.stringify(args)})`, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
    return r.result.value;
  }
  async function until(fn, timeout = 20000, ...args) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) { if (await evaluate(fn, ...args)) return true; await sleep(50); }
    return false;
  }
  async function close() {
    try { await send('Browser.close', {}, false); } catch { /* killed below */ }
    try {
      socket.close(); if (child.exitCode === null && child.signalCode === null) { const exited = once(child, 'exit'); child.kill(); await exited; }
      await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
    } catch { /* cleanup never replaces a check result */ }
  }
  // A fault that never reached the page, or matched more than once, proves nothing.
  function assertFaultServed() {
    assert.deepEqual(harness, [], 'Fault harness error');
    if (patch) assert.ok(patched >= 1, `Fault ${fault} was never served`);
  }
  return { send, evaluate, until, close, exceptions, commands, assertFaultServed };
}

async function load(browser, base, slug, width, height, hash = '') {
  await browser.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
  await browser.send('Page.navigate', { url: `${base}/?board=${slug}${hash}` });
  assert.ok(await browser.until(() => ['ready', 'empty'].includes(document.body?.dataset.loadState), 60000), `${slug} did not load at ${width}px`);
  // An offscreen room stays suspended by design; bring it into view to let it mount.
  await browser.evaluate(() => document.getElementById('workplace-canvas').scrollIntoView({ block: 'center', behavior: 'instant' }));
  assert.ok(await browser.until(() => ['ready', 'unavailable'].includes(document.getElementById('graphics-status')?.dataset.state), 60000), `${slug} graphics did not settle at ${width}px`);
  await browser.evaluate(() => scrollTo(0, 0));
  await browser.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(resolve, 150)))));
}
const settle = browser => browser.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(resolve, 200)))));
const FIRST_STATION = { bookshop: 'customers', gtm: 'signals', northline: 'acceptance' };

const CHECK_OF = { inspector_keeps_stations_readable: 'inspector', main_view_has_no_internal_identifiers: 'identifiers', narrow_stack_reach: 'narrow',
  next_action_navigates_only: 'story', main_view_shows_one_of_each: 'story', guide_never_credits_unsent_text: 'story', picker_uses_switch_guard: 'picker' };

export async function inspectorKeepsStationsReadable(browser, base, slug) {
  await load(browser, base, slug, 1280, 720);
  assert.equal(await browser.evaluate(() => document.querySelector('.room').dataset.graphics), 'ready', `${slug} 3D room is not ready`);
  await browser.evaluate(station => document.querySelector(`.room-hotspots:not([hidden]) [data-station="${station}"]`).click(), FIRST_STATION[slug]);
  assert.ok(await browser.until(() => document.getElementById('workplace-world').dataset.inspector === 'open'), `${slug} inspector did not open`);
  await settle(browser);
  const layout = await browser.evaluate(() => {
    const panel = document.getElementById('station-panel').getBoundingClientRect();
    return { panel: { left: panel.left, right: panel.right, top: panel.top, bottom: panel.bottom }, width: innerWidth, height: innerHeight,
      tags: [...document.querySelectorAll('.room-hotspots:not([hidden]) [data-station]')].map(button => {
        const r = button.getBoundingClientRect();
        return { station: button.dataset.station, left: r.left, right: r.right, top: r.top, bottom: r.bottom, anchored: button.dataset.anchored === 'true',
          anchorX: Number(button.dataset.anchorX) + document.querySelector('.room').getBoundingClientRect().left };
      }) };
  });
  assert.ok(layout.panel.right > layout.panel.left, `${slug} inspector has no area`);
  const outside = layout.tags.filter(tag => tag.left < 0 || tag.top < 0 || tag.right > layout.width || tag.bottom > layout.height);
  assert.deepEqual(outside, [], 'inspector_keeps_stations_readable: a station tag is outside the viewport');
  const under = layout.tags.filter(tag => tag.left < layout.panel.right && tag.right > layout.panel.left && tag.top < layout.panel.bottom && tag.bottom > layout.panel.top);
  assert.deepEqual(under, [], 'inspector_keeps_stations_readable: a station tag is under the inspector');
  assert.ok(layout.tags.length >= 4 && layout.tags.every(tag => tag.anchored), `${slug} tags are not placed at projected anchors`);
  // The view offset centres the room in the stage the inspector leaves uncovered:
  // the anchors' mean sits within 10% of that area's centre.
  const uncovered = { left: layout.panel.right, right: layout.width };
  const centre = (uncovered.left + uncovered.right) / 2, mean = layout.tags.reduce((sum, tag) => sum + tag.anchorX, 0) / layout.tags.length;
  assert.ok(Math.abs(mean - centre) <= (uncovered.right - uncovered.left) * .1,
    `inspector_keeps_stations_readable: the room is not centred in the uncovered stage (anchor mean ${Math.round(mean)}, centre ${Math.round(centre)})`);
  const covered = layout.tags.flatMap((a, i) => layout.tags.slice(i + 1)
    .filter(b => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top).map(b => `${a.station}/${b.station}`));
  assert.deepEqual(covered, [], 'inspector_keeps_stations_readable: a station tag covers another station tag');
  return { slug, inspector: layout.panel, tags: layout.tags.length, anchorMean: Math.round(mean), uncoveredCentre: Math.round(centre) };
}

// The main view: status bar, step chip, next action, station tags and bubbles (Gate 3 section 13.6).
const MAIN_VIEW = () => {
  const shown = node => node && !node.closest('[hidden]');
  const nodes = [document.getElementById('status-bar'), document.getElementById('step-chip'), document.getElementById('next-action'),
    ...document.querySelectorAll('.bubble'), ...document.querySelectorAll('.room-hotspots:not([hidden]) [data-station]')].filter(shown);
  // Text nodes are joined with spaces: textContent would glue "requests" to a
  // following "run-0002" and hide it from word-boundary patterns.
  const words = node => { const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT), out = [];
    while (walker.nextNode()) out.push(walker.currentNode.nodeValue); return out.join(' '); };
  return nodes.map(node => [words(node), node.getAttribute('aria-label') ?? '', node.getAttribute('title') ?? '',
    ...[...node.querySelectorAll('[aria-label],[title]')].map(child => `${child.getAttribute('aria-label') ?? ''} ${child.getAttribute('title') ?? ''}`)].join(' ')).join('\n');
};
export async function mainViewHasNoInternalIdentifiers(browser, base, slug) {
  await load(browser, base, slug, 1280, 720);
  // Self-test: every pattern must detect its needle inside the same serialized surface.
  for (const rule of FORBIDDEN) {
    const text = await browser.evaluate((needle, serialize) => {
      const probe = document.createElement('small'); probe.textContent = needle;
      document.querySelector('.room-hotspots:not([hidden]) [data-station]').append(probe);
      try { return new Function(`return (${serialize})()`)(); } finally { probe.remove(); }
    }, rule.sample, MAIN_VIEW.toString());
    assert.ok(rule.pattern.test(text), `Scanner self-test: ${rule.name} did not detect ${rule.sample} in the serialized main view`);
  }
  const text = await browser.evaluate(MAIN_VIEW);
  const found = scan(text);
  assert.deepEqual(found, [], `main_view_has_no_internal_identifiers: the main view shows ${found.join(', ')}: ${text.replace(/\s+/g, ' ').slice(0, 400)}`);
  assert.match(text, /Synthetic scenario/, `${slug} status bar lost its synthetic label`);
  return { slug, characters: text.length };
}

const NORTHLINE_REACH = { acceptance: '#selected-evidence', rollout: '#operate-pilot', handover: '#handover-records' };
export async function narrowStackReach(browser, base, slug, width, height, zoom) {
  await load(browser, base, slug, width, height);
  const geometry = await browser.evaluate(() => {
    const top = selector => document.querySelector(selector).getBoundingClientRect();
    const notice = top('#runtime-notice'), status = top('#status-bar'), canvas = top('#workplace-canvas');
    const chip = document.getElementById('step-chip').hidden ? null : top('#step-chip'), next = top('#next-action');
    const tags = [...document.querySelectorAll('.room-hotspots:not([hidden]) [data-station]')].map(node => node.getBoundingClientRect());
    return { notice: notice.bottom, status: [status.top, status.bottom], canvas: [canvas.top, canvas.bottom],
      chip: chip && [chip.top, chip.bottom], next: [next.top, next.bottom],
      tagsTop: Math.min(...tags.map(r => r.top)), tagsBottom: Math.max(...tags.map(r => r.bottom)),
      scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth,
      small: [...document.querySelectorAll('#workplace-world :is(button, summary, select, a):not([hidden])')]
        .filter(node => node.offsetParent && !node.closest('#station-panel') && !node.closest('details:not([open]) > :not(summary)'))
        .map(node => ({ id: node.id || node.dataset.station || node.dataset.logFilter || node.textContent.trim().slice(0, 20), r: node.getBoundingClientRect() }))
        .filter(({ r }) => r.width < 44 || r.height < 44).map(({ id, r }) => `${id} ${Math.round(r.width)}x${Math.round(r.height)}`) };
  });
  assert.equal(geometry.scrollWidth, geometry.clientWidth, 'narrow_stack_reach: the page scrolls horizontally');
  const ordered = geometry.notice <= geometry.status[0] + 1 && geometry.status[1] <= geometry.canvas[0] + 1 && geometry.canvas[1] <= geometry.tagsTop + 1;
  assert.ok(ordered, `narrow_stack_reach: the narrow stack is out of order ${JSON.stringify(geometry)}`);
  // S37: the step chip sits between the status bar and the room; the next action follows the tags.
  const storyOrdered = (!geometry.chip || (geometry.status[1] <= geometry.chip[0] + 1 && geometry.chip[1] <= geometry.canvas[0] + 1))
    && geometry.tagsBottom <= geometry.next[0] + 1;
  assert.ok(storyOrdered, `narrow_stack_reach: the step chip or next action is out of order ${JSON.stringify(geometry)}`);
  if (slug === 'bookshop') {
    const reachNext = await browser.evaluate(() => {
      const button = document.getElementById('next-action-go');
      button.focus(); button.scrollIntoView({ block: 'nearest', behavior: 'instant' });
      const r = button.getBoundingClientRect();
      return { focused: document.activeElement === button, top: r.top, bottom: r.bottom, height: innerHeight, width: r.width };
    });
    assert.ok(reachNext.focused && reachNext.top >= 0 && reachNext.bottom <= reachNext.height, `narrow_stack_reach: the next action is out of reach ${JSON.stringify(reachNext)}`);
    await browser.evaluate(() => scrollTo(0, 0));
  }
  assert.deepEqual(geometry.small, [], 'narrow_stack_reach: a main-view control is smaller than 44 by 44');
  const reach = [];
  for (const [station, selector] of slug === 'northline' ? Object.entries(NORTHLINE_REACH) : [[FIRST_STATION[slug], '#station-panel']]) {
    await browser.evaluate(() => scrollTo(0, 0));
    const before = browser.commands.length;
    await browser.evaluate(station => document.querySelector(`.room-hotspots:not([hidden]) [data-station="${station}"]`).click(), station);
    await sleep(700);
    const placed = await browser.evaluate(selector => {
      const target = document.querySelector(selector).getBoundingClientRect();
      const tags = [...document.querySelectorAll('.room-hotspots:not([hidden]) [data-station]')].map(node => node.getBoundingClientRect().bottom);
      const panel = document.getElementById('station-panel').getBoundingClientRect(), log = document.getElementById('shift-log').getBoundingClientRect();
      return { top: target.top, height: innerHeight, panelTop: panel.top, panelBottom: panel.bottom, tagsBottom: Math.max(...tags), logTop: log.top,
        scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth };
    }, selector);
    assert.ok(placed.top >= -1 && placed.top < placed.height - 44, `narrow_stack_reach: selected work is out of reach (${station} ${JSON.stringify(placed)})`);
    assert.ok(placed.tagsBottom <= placed.panelTop + 1 && placed.panelBottom <= placed.logTop + 1, `narrow_stack_reach: the narrow stack is out of order after opening ${station}`);
    assert.equal(placed.scrollWidth, placed.clientWidth, 'narrow_stack_reach: the page scrolls horizontally');
    assert.equal(browser.commands.length, before, `Opening ${station} sent a command`);
    reach.push({ station, top: Math.round(placed.top) });
  }
  return { slug, width, height, zoom, reach };
}

// S37: the story layer on one fresh Bellwether demo, walked through the seven steps
// with real recorded actions. Only the actions between states send requests; the
// next action itself never does. This consumes the preview's shift, so it runs last.
const STORY_READ = () => {
  const visible = node => Boolean(node) && !node.closest('[hidden]') && node.getClientRects().length > 0
    && getComputedStyle(node).visibility !== 'hidden';
  const pressed = document.querySelector('#bookshop-stations [aria-pressed="true"]');
  return { chip: document.getElementById('step-chip').innerText.replace(/\s+/g, ' ').trim(), next: document.getElementById('next-action-go').textContent,
    station: pressed?.dataset.station ?? null, inspector: document.getElementById('workplace-world').dataset.inspector,
    owners: [...document.querySelectorAll('.owner-bubble')].filter(visible).length,
    customers: [...document.querySelectorAll('.customer-bubble')].filter(visible).length,
    actions: [document.getElementById('next-action'), document.querySelector('#station-panel .panel-footer')].filter(visible).length };
};
const STORY_STEPS = [
  [1, 'Read the complaints', 'customers'], [2, 'Explain the cause', 'investigate'], [3, 'Say what would prove you wrong', 'investigate'],
  [4, 'Try two fixes', 'compare'], [5, 'Choose one', 'compare'], [6, 'Run the shift', 'service'], [7, 'See what happened', 'ledger'],
  [7, 'See what happened', 'next']];
export async function storyJourney(browser, base) {
  await load(browser, base, 'bookshop', 1280, 720);
  const files = await Promise.all(['a', 'b'].map(label => readFile(`shiftwork/fixtures/artifacts/bookshop/compare_repair_${label}_service.py`, 'utf8')));
  const results = [];
  const expectStep = async ([step, name, station], label) => {
    const chip = `Step ${step} of 7 ${name}`;
    assert.ok(await browser.until(expected => document.getElementById('step-chip').innerText.replace(/\s+/g, ' ').trim() === expected, 120000, chip),
      `guide_step_follows_recorded_state: ${label} shows "${(await browser.evaluate(STORY_READ)).chip}", not "${chip}"`);
    await settle(browser);
    // One of each: checked with the inspector closed here and open after the next action.
    const oneOfEach = seen => {
      assert.ok(seen.owners <= 1 && seen.customers <= 1, `main_view_shows_one_of_each: ${label} shows ${seen.owners} owner and ${seen.customers} customer bubbles`);
      assert.equal(seen.actions, 1, `main_view_shows_one_of_each: ${label} shows ${seen.actions} next actions or inspector footers (inspector ${seen.inspector})`);
    };
    await browser.evaluate(() => document.getElementById('close-inspector').click());
    oneOfEach(await browser.evaluate(STORY_READ));
    const text = await browser.evaluate(MAIN_VIEW);
    const found = scan(text);
    assert.deepEqual(found, [], `main_view_has_no_internal_identifiers: the main view shows ${found.join(', ')} at ${label}: ${text.replace(/\s+/g, ' ').slice(0, 400)}`);
    const read = await browser.evaluate(STORY_READ);
    assert.equal(read.next, name, `next_action_navigates_only: ${label} next action reads "${read.next}"`);
    const before = browser.commands.length;
    await browser.evaluate(() => document.getElementById('next-action-go').click());
    await sleep(400);
    const after = await browser.evaluate(STORY_READ);
    assert.equal(browser.commands.length, before, `next_action_navigates_only: ${label} next action sent ${browser.commands.slice(before).join(', ')}`);
    assert.deepEqual([after.station, after.inspector], [station, 'open'], `next_action_navigates_only: ${label} next action opened ${after.station}`);
    await settle(browser);
    oneOfEach(await browser.evaluate(STORY_READ));
    results.push({ step, name, station, owners: read.owners, customers: read.customers });
  };
  const act = (fn, ...args) => browser.evaluate(fn, ...args);
  const wait = (label, fn, ...args) => browser.until(fn, 180000, ...args).then(ok => assert.ok(ok, `Story journey: timed out waiting for ${label}`));

  await expectStep(STORY_STEPS[0], 'fresh shift');
  await act(() => document.querySelector('#bookshop-stations [data-station="investigate"]').click());
  await expectStep(STORY_STEPS[1], 'investigating');
  // guide_never_credits_unsent_text: a cause draft moves only the chip.
  const controls = () => ({ count: document.querySelectorAll('#investigation-list [data-investigation-id]').length,
    tag: document.getElementById('investigation-tag').textContent,
    disabled: [...document.querySelectorAll('button, input, select, textarea')].filter(node => node.id !== 'cause-input').map(node => `${node.id || node.dataset.station || node.textContent.trim().slice(0, 24)}:${node.disabled}`) });
  const clean = await act(controls);
  await act(() => { const input = document.getElementById('cause-input'); input.value = 'A draft cause that is never sent'; input.dispatchEvent(new Event('input')); });
  await sleep(200);
  const drafted = await act(controls);
  assert.deepEqual(drafted.disabled, clean.disabled, 'guide_never_credits_unsent_text: a cause draft changed a control\'s disabled state');
  assert.deepEqual([drafted.count, drafted.tag], [clean.count, clean.tag], 'guide_never_credits_unsent_text: a cause draft changed the investigation count');
  await expectStep(STORY_STEPS[2], 'investigating with a cause draft');
  await act(() => {
    for (const [id, value] of [['cause-input', 'The service reads only the price field.'], ['falsifier-input', 'A request that asks only for the price would still be wrong.'],
      ['public-test-input', 'Ask to collect a title and expect a collection answer.']]) { const node = document.getElementById(id); node.value = value; node.dispatchEvent(new Event('input')); }
    document.getElementById('append-investigation').click();
  });
  await wait('the recorded investigation', count => document.querySelectorAll('#investigation-list [data-investigation-id]').length === count + 1, clean.count);
  await expectStep(STORY_STEPS[3], 'investigation recorded');
  await act(async (candidateA, candidateB) => {
    const until = async check => { const deadline = Date.now() + 120000; while (Date.now() < deadline) { if (check()) return; await new Promise(r => setTimeout(r, 60)); } throw new Error(`Story journey comparison stalled: ${document.getElementById('compare-error').textContent}`); };
    const freezeIdle = () => !document.getElementById('freeze-candidate-a').disabled && !document.getElementById('freeze-candidate-b').disabled;
    const frozen = index => document.getElementById('candidate-list').querySelectorAll('.contract-line strong')[index]?.textContent ?? '';
    const put = async source => {
      document.getElementById('draft-file').value = 'service.py'; document.getElementById('draft-file').dispatchEvent(new Event('change'));
      document.getElementById('draft-source').value = source; document.getElementById('draft-source').dispatchEvent(new Event('input'));
      document.getElementById('save-draft').click();
      await until(() => document.getElementById('draft-source').dataset.dirty === 'false' && document.getElementById('save-draft').disabled);
    };
    document.querySelector('#bookshop-stations [data-station="compare"]').click();
    await put(candidateA); await until(freezeIdle); document.getElementById('freeze-candidate-a').click(); await until(() => frozen(0).startsWith('ver-') && freezeIdle());
    await put(candidateB); await until(freezeIdle); document.getElementById('freeze-candidate-b').click(); await until(() => frozen(1).startsWith('ver-') && freezeIdle());
    const treatment = document.getElementById('treatment-input');
    treatment.value = 'A answers the optional price fact everywhere; B answers it only when the request asks for it'; treatment.dispatchEvent(new Event('input'));
    document.getElementById('run-comparison').click();
  }, ...files);
  await expectStep(STORY_STEPS[4], 'comparison complete');
  await act(() => { const node = document.getElementById('selection-rationale'); node.value = 'A answered the required tasks in the shared trial.'; node.dispatchEvent(new Event('input')); });
  await wait('candidate A to be selectable', () => !document.getElementById('select-candidate-a').disabled);
  await act(() => document.getElementById('select-candidate-a').click());
  await expectStep(STORY_STEPS[5], 'learner choice');
  // The demo's first shift already ran the starter, so a new choice operates in the
  // next shift: close (step 7 at Next shift), open shift 2 (step 1), then run (step 7).
  await act(() => { document.querySelector('[data-view="next"]').click(); document.getElementById('close-shift').click(); });
  await expectStep(STORY_STEPS[7], 'closed shift');
  await wait('the next shift to be openable', () => !document.getElementById('open-next-shift').disabled);
  await act(() => document.getElementById('open-next-shift').click());
  await expectStep(STORY_STEPS[0], 'next shift with the inherited choice');
  await act(() => document.querySelector('#bookshop-stations [data-station="service"]').click());
  await wait('the run to be allowed', () => !document.getElementById('run-shift').disabled);
  await act(() => document.getElementById('run-shift').click());
  await expectStep(STORY_STEPS[6], 'operation finished');
  return { slug: 'bookshop', steps: results };
}

// S37: a picker start goes through the same switch guard as the board selector.
export async function pickerUsesSwitchGuard(browser, base) {
  await browser.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 720, deviceScaleFactor: 1, mobile: false });
  await browser.send('Page.navigate', { url: `${base}/` });
  assert.ok(await browser.until(() => document.body?.dataset.loadState === 'ready', 60000), 'Picker page did not load');
  assert.equal(await browser.evaluate(() => document.getElementById('shift-picker').hidden), false, 'picker_uses_switch_guard: a bare address does not show the picker');
  const cards = await browser.evaluate(() => [...document.querySelectorAll('.shift-card')].map(card => ({ slug: card.dataset.slug, text: card.innerText })));
  assert.deepEqual(cards.map(card => card.slug), ['bookshop', 'northline', 'gtm'], 'picker_uses_switch_guard: the picker does not show the three shifts');
  assert.equal(await browser.evaluate(() => document.querySelectorAll('#shift-picker-steps li').length), 7, 'picker_uses_switch_guard: the picker does not list the seven steps');
  // A dirty draft blocks the start exactly as the board selector's switch does.
  // Choosing a station keeps the current shift, so the picker steps aside.
  await browser.evaluate(() => document.querySelector('[data-view="compare"]').click());
  assert.equal(await browser.evaluate(() => document.getElementById('shift-picker').hidden), true, 'picker_uses_switch_guard: choosing a station leaves the picker over the room');
  await browser.until(() => !document.getElementById('draft-source').disabled, 30000);
  await browser.evaluate(() => { const source = document.getElementById('draft-source'); source.value += '\n# unsaved learner edit\n'; source.dispatchEvent(new Event('input')); });
  assert.equal(await browser.evaluate(() => document.getElementById('draft-source').dataset.dirty), 'true', 'Picker check could not make the draft dirty');
  const before = browser.commands.length;
  const blocked = await browser.evaluate(async () => {
    document.getElementById('change-shift').click();
    document.querySelector('.shift-card[data-slug="bookshop"] button').click();
    await new Promise(resolve => setTimeout(resolve, 800));
    return { open: !document.getElementById('shift-picker').hidden, message: document.getElementById('shift-picker-message').textContent,
      url: location.search, dirty: document.getElementById('draft-source').dataset.dirty, draft: document.getElementById('draft-source').value.includes('unsaved learner edit') };
  });
  assert.deepEqual([blocked.open, blocked.dirty, blocked.draft], [true, 'true', true], `picker_uses_switch_guard: a dirty draft did not block the picker start ${JSON.stringify(blocked)}`);
  assert.match(blocked.message, /Save or discard the draft/, 'picker_uses_switch_guard: the blocked start does not say why');
  assert.equal(browser.commands.length, before, 'picker_uses_switch_guard: a blocked start sent a request');
  return { blocked };
}

export async function runAll(base, out, slug, fault = '', only = '') {
  const results = [];
  const run = async (name, zoom, fn) => {
    if (only && only !== name) return;
    const browser = await openBrowser(base, path.join(out, `${name}-${zoom}x`), fault, { zoom });
    try {
      results.push(await fn(browser));
      assert.deepEqual(browser.exceptions, [], 'Uncaught client exceptions');
      browser.assertFaultServed();
    } catch (error) { browser.assertFaultServed(); throw error; }
    finally { await browser.close(); }
  };
  await run('inspector', 1, browser => inspectorKeepsStationsReadable(browser, base, slug));
  await run('identifiers', 1, browser => mainViewHasNoInternalIdentifiers(browser, base, slug));
  for (const zoom of [1, 2]) await run('narrow', zoom, async browser => [
    // 1280x720 at 200% zoom lays out at 640 CSS pixels, so it stacks too.
    ...(zoom === 2 ? [await narrowStackReach(browser, base, slug, 1280, 720, zoom)] : []),
    await narrowStackReach(browser, base, slug, 640, 900, zoom), await narrowStackReach(browser, base, slug, 390, 844, zoom)]);
  if (slug === 'bookshop') {
    await run('picker', 1, browser => pickerUsesSwitchGuard(browser, base));
    // Last: the story journey records an investigation, a comparison, a choice and a run.
    await run('story', 1, browser => storyJourney(browser, base));
  }
  await writeFile(path.join(out, `${slug}-fullscreen.json`), JSON.stringify(results, null, 2) + '\n');
  return results;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [base, out, slug = 'bookshop'] = process.argv.slice(2);
  const flag = name => { const index = process.argv.indexOf(name); return index === -1 ? '' : process.argv[index + 1]; };
  const fault = flag('--fault'), only = flag('--only') || (fault && CHECK_OF[FAULTS[fault]?.expect.split(':')[0]]) || '';
  if (!fault) { console.log(JSON.stringify(await runAll(base, out, slug, '', only))); }
  else {
    // A fault run passes only when the named assertion fails.
    try { await runAll(base, out, slug, fault, only); console.error(`FAULT ${fault} NOT CAUGHT`); process.exit(1); }
    catch (error) {
      if (!String(error.message).includes(FAULTS[fault].expect)) { console.error(`FAULT ${fault} failed elsewhere: ${error.message}`); process.exit(1); }
      console.log(JSON.stringify({ fault, caught: FAULTS[fault].expect }));
    }
  }
}
