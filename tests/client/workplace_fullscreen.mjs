// S36 full-screen workplace checks (Gate 3 section 13.9).
// Each check passes clean; with --fault NAME the harness serves one in-memory
// mutation of a production file and the run must fail at that check's named
// assertion. Repository files are never modified.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
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
  assert.ok(/^\/(?:private\/)?tmp\/shiftwork-s36-[^/]+(?:\/|$)/.test(path.resolve(out)), 'S36 receipts must use /tmp/shiftwork-s36-*');
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

const CHECK_OF = { inspector_keeps_stations_readable: 'inspector', main_view_has_no_internal_identifiers: 'identifiers', narrow_stack_reach: 'narrow' };

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

const MAIN_VIEW = () => {
  const nodes = [document.getElementById('status-bar'), ...document.querySelectorAll('.room-hotspots:not([hidden]) [data-station]')];
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
    const tags = [...document.querySelectorAll('.room-hotspots:not([hidden]) [data-station]')].map(node => node.getBoundingClientRect());
    return { notice: notice.bottom, status: [status.top, status.bottom], canvas: [canvas.top, canvas.bottom],
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
    await narrowStackReach(browser, base, slug, 640, 900, zoom), await narrowStackReach(browser, base, slug, 390, 844, zoom)]);
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
