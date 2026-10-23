// S42 robot crew browser checks (Gate 3 section 14.4) on the three boards.
// Each check passes clean; with --fault NAME the harness serves one in-memory
// mutation of a production file and the run must fail at that fault's named
// assertion. Repository files are never modified.
import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { FAULTS as SHARED_FAULTS, INSTRUMENT, openBrowser } from './workplace_fullscreen.mjs';

export const FAULTS = {
  'walk-on-publish': { file: '/app.js', needle: 'function publishPresentation(reason) {\n  renderInspectionBar();',
    replacement: "function publishPresentation(reason) {\n  workplaceHost?.setOpenStation(state.slug === 'bookshop' ? 'ledger' : state.slug === 'gtm' ? 'wall' : 'rollout');\n  renderInspectionBar();",
    expect: 'bot_walks_only_on_learner_choice: bookshop a publication moved the bot' },
  'suspend-keeps-walk': { file: '/workplace-scene.js', needle: 'settleCamera(); crew?.settle(); crewWalking=false; crewDirty=true; } if(value && raf!==null)',
    replacement: 'settleCamera(); } if(value && raf!==null)', expect: 'crew_settles_without_motion: bookshop suspend left a route' },
  'resume-stale-chip': { file: '/workplace-scene.js', needle: 'crewWalking=false; crewDirty=true; } if(value && raf!==null)',
    replacement: 'crewWalking=false; } if(value && raf!==null)', expect: 'crew_settles_without_motion: bookshop chip left behind after a hidden tab' },
  'hidden-tab-walks': { file: '/workplace-host.js', needle: 'const suspended = () => document.hidden || !visible || expanded;',
    replacement: 'const suspended = () => !visible || expanded;', expect: 'crew_settles_without_motion: bookshop hidden tab left a route' },
  'reduced-walks': { file: '/workplace-scene.js', needle: "if(settled || tier==='compact' || reducedMotion || suspended) crew.settle();",
    replacement: "if(settled || tier==='compact' || suspended) crew.settle();", expect: 'crew_settles_without_motion: bookshop reduced motion left a route' },
  'crew-leak': { file: '/workplace-scene.js', needle: 'if(resource.isMaterial) materials.add(resource); else geometries.add(resource);',
    replacement: '', expect: 'crew_disposed_once: crew resources survive' },
  'walk-janks': { file: '/workplace-crew.js', needle: 'you.phase += dt * 13;',
    replacement: 'you.phase += dt * 13; for (const end = performance.now() + 40; performance.now() < end;);', expect: 'crew_walk_frames: bookshop walk intervals' },
  'chip-result': { file: '/', needle: '<span id="you-chip" class="you-chip" hidden>You</span>',
    replacement: '<span id="you-chip" class="you-chip" hidden>You · passed</span>', expect: 'crew_carries_no_result_text: bookshop chip' },
  'bubble-at-tag': { file: '/app.js', needle: 'const t = speaker?.visible ?', replacement: 'const t = false ?',
    expect: 'one_narrator_bubble: bookshop bubble is not at its speaker bot' },
};

// Observation only: the learner bot's node, route and pose, the crew's screen points and
// the crew's registered resources. Nothing here changes what the page does.
INSTRUMENT.push(
  { file: '/workplace-crew.js', needle: '  // Every bot starts on its settled spot;',
    replacement: '  globalThis.__crew = () => ({ node, walking: path.length > 0, position: [you.root.position.x, you.root.position.z], still: bots.every(bot => bot.rig.position.y === 0 && bot.head.rotation.y === 0 && bot.legs.every(leg => leg.rotation.x === 0)) });\n  // Every bot starts on its settled spot;' },
  { file: '/workplace-scene.js', needle: 'const register = resource => {',
    replacement: "globalThis.__crewResources ??= { created: 0, live: 0, disposed: 0 }; const register = resource => { globalThis.__crewResources.created++; globalThis.__crewResources.live++; resource.addEventListener('dispose', () => { globalThis.__crewResources.live--; globalThis.__crewResources.disposed++; });" },
  { file: '/workplace-host.js', needle: 'onAnchors(positions,crew) {', replacement: 'onAnchors(positions,crew) { globalThis.__crewPoints = crew;' });

const BOARDS = { bookshop: { home: 'h1', stand: 'ledger' }, gtm: { home: 'home', stand: 'wall' }, northline: { home: 'home', stand: 'rollout' } };
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const setHidden = (browser, hidden) => browser.evaluate(hidden => {
  Object.defineProperty(document, 'hidden', { value: hidden, configurable: true });
  document.dispatchEvent(new Event('visibilitychange'));
}, hidden);
const crew = browser => browser.evaluate(() => globalThis.__crew?.() ?? null);
async function load(browser, base, slug, width, height) {
  await browser.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
  await browser.send('Page.navigate', { url: `${base}/?board=${slug}` });
  assert.ok(await browser.until(() => ['ready', 'empty'].includes(document.body?.dataset.loadState), 60000), `${slug} did not load`);
  await browser.evaluate(() => document.getElementById('workplace-canvas').scrollIntoView({ block: 'center', behavior: 'instant' }));
  assert.ok(await browser.until(() => document.getElementById('graphics-status')?.dataset.state === 'ready' && globalThis.__crew, 60000), `${slug} room did not mount`);
  await browser.evaluate(() => scrollTo(0, 0));
  await sleep(600);
}
async function shot(browser, name) {
  const { data } = await browser.send('Page.captureScreenshot', { format: 'png' });
  await writeFile(path.join(browser.out, `${name}.png`), Buffer.from(data, 'base64'));
}
const open = (browser, slug, station) => browser.evaluate((slug, station) => { document.querySelector(`#${slug}-stations [data-station="${station}"]`).click(); document.activeElement?.blur(); }, slug, station);
async function arrive(browser, label) {
  assert.ok(await browser.until(() => globalThis.__crew?.().walking === false, 6000), `bot_walks_only_on_learner_choice: ${label} never arrived`);
  return crew(browser);
}

// Gate 3 section 14.2 rules 2, 3 and 6 on one board: publications, polls and ambient
// input never move your bot; your station choice does, and closing sends it home.
async function boardJourney(browser, base, slug) {
  await load(browser, base, slug, 1280, 720);
  const home = await crew(browser);
  assert.ok(home.node === BOARDS[slug].home && !home.walking, `bot_walks_only_on_learner_choice: ${slug} a publication moved the bot before any choice`);
  await shot(browser, `${slug}-rest`);
  const chipAtRest = await browser.evaluate(() => { const chip = document.getElementById('you-chip'); return { text: chip.textContent, children: chip.children.length, hidden: chip.hidden, rect: chip.getBoundingClientRect().toJSON() }; });
  assert.ok(chipAtRest.text === 'You' && chipAtRest.children === 0, `crew_carries_no_result_text: ${slug} chip reads "${chipAtRest.text}"`);
  assert.equal(chipAtRest.hidden, false, `crew_carries_no_result_text: ${slug} chip is not shown`);
  for (let round = 0; round < 2; round++) {
    await browser.evaluate(() => document.getElementById('refresh').click());
    await browser.evaluate(() => document.getElementById('workplace-world').dispatchEvent(new PointerEvent('pointerdown', { bubbles: true })));
    await sleep(1500);
  }
  const after = await crew(browser);
  assert.ok(after.node === home.node && after.position.every((value, i) => Math.abs(value - home.position[i]) < 1e-9) && !after.walking,
    `bot_walks_only_on_learner_choice: ${slug} a publication moved the bot`);
  if (slug === 'bookshop') {
    const bubble = await browser.evaluate(() => {
      const node = [...document.querySelectorAll('.bubble')].find(item => !item.hidden), r = node.getBoundingClientRect(), chip = document.getElementById('you-chip').getBoundingClientRect();
      const room = document.querySelector('.room').getBoundingClientRect(), role = node.id === 'owner-bubble' ? 'owner' : 'customer', point = globalThis.__crewPoints?.[role];
      return { id: node.id, rect: r.toJSON(), point: point && { x: point.x + room.left, y: point.y + room.top }, chip: chip.toJSON() };
    });
    const { rect, point } = bubble;
    assert.ok(point && rect.bottom <= point.y + 12 && rect.bottom >= point.y - 160 && rect.left <= point.x + 40 && rect.right >= point.x - 40,
      `one_narrator_bubble: bookshop bubble is not at its speaker bot (${JSON.stringify(bubble)})`);
    const overlap = !(rect.right <= bubble.chip.left || rect.left >= bubble.chip.right || rect.bottom <= bubble.chip.top || rect.top >= bubble.chip.bottom);
    assert.ok(!overlap, 'one_narrator_bubble: bookshop bubble covers the You chip');
  }
  const { stand } = BOARDS[slug];
  await open(browser, slug, stand);
  // Gate 3 section 13.8 active-motion intervals while the bot walks (this Mac's headless Chrome only).
  const intervals = await browser.evaluate(() => new Promise(resolve => {
    const marks = [];
    const step = now => { marks.push(now); if (now - marks[0] < 1000) requestAnimationFrame(step); else resolve(marks.slice(1).map((t, i) => t - marks[i])); };
    requestAnimationFrame(step);
  }));
  const nearest = (values, q) => [...values].sort((x, y) => x - y)[Math.max(0, Math.ceil(q * values.length) - 1)];
  const frames = { median: nearest(intervals, .5), p95: nearest(intervals, .95), count: intervals.length };
  assert.ok(frames.median <= 16.7 && frames.p95 <= 33.4, `crew_walk_frames: ${slug} walk intervals ${JSON.stringify(frames)}`);
  const mid = await crew(browser);
  assert.equal(mid.walking, true, `bot_walks_only_on_learner_choice: ${slug} choosing ${stand} did not start a walk`);
  await shot(browser, `${slug}-walk`);
  const there = await arrive(browser, `${slug} ${stand}`);
  assert.notEqual(there.node, home.node, `bot_walks_only_on_learner_choice: ${slug} did not reach ${stand}`);
  const chipThere = await browser.evaluate(() => ({ text: document.getElementById('you-chip').textContent, rect: document.getElementById('you-chip').getBoundingClientRect().toJSON() }));
  assert.ok(Math.hypot(chipThere.rect.left - chipAtRest.rect.left, chipThere.rect.top - chipAtRest.rect.top) > 20, `bot_walks_only_on_learner_choice: ${slug} chip did not follow the bot`);
  assert.equal(chipThere.text, 'You', `crew_carries_no_result_text: ${slug} chip`);
  await shot(browser, `${slug}-at-${stand}`);
  await browser.evaluate(() => document.getElementById('close-inspector').click());
  const back = await arrive(browser, `${slug} home`);
  assert.equal(back.node, home.node, `bot_walks_only_on_learner_choice: ${slug} closing did not send the bot home`);
  return { slug, home: home.node, stand: there.node, chip: chipAtRest.text, frames };
}

// Gate 2 R7 and Gate 3 section 14.2 rule 5: suspend, reduced motion and the compact tier never leave a bot mid-route or posed.
async function settles(browser, base) {
  await load(browser, base, 'bookshop', 1280, 720);
  await open(browser, 'bookshop', 'ledger');
  await sleep(150);
  await browser.evaluate(() => document.getElementById('expand-work').click());
  await sleep(150);
  const suspended = await crew(browser);
  assert.ok(!suspended.walking && suspended.node === 'ledger', `crew_settles_without_motion: bookshop suspend left a route (${JSON.stringify(suspended)})`);
  assert.ok(suspended.still, 'crew_settles_without_motion: bookshop suspend left a bot posed');
  await browser.evaluate(() => document.getElementById('expand-work').click());
  await browser.evaluate(() => document.getElementById('close-inspector').click());
  await arrive(browser, 'bookshop home after suspend');
  // A hidden tab suspends mid-walk with no resize; on return the chip must sit where it
  // sits after a full walk to the same station.
  await open(browser, 'bookshop', 'ledger');
  await arrive(browser, 'bookshop ledger before hidden tab');
  await sleep(200);
  const expected = await browser.evaluate(() => document.getElementById('you-chip').getBoundingClientRect().toJSON());
  await browser.evaluate(() => document.getElementById('close-inspector').click());
  await arrive(browser, 'bookshop home before hidden tab');
  await open(browser, 'bookshop', 'ledger');
  // Hide after the 480ms camera ease has finished, so only the crew can refresh the chip.
  await sleep(800);
  assert.equal((await crew(browser)).walking, true, 'crew_settles_without_motion: bookshop walk ended before the hidden tab');
  await setHidden(browser, true);
  await sleep(150);
  const hidden = await crew(browser);
  assert.ok(!hidden.walking && hidden.node === 'ledger', `crew_settles_without_motion: bookshop hidden tab left a route (${JSON.stringify(hidden)})`);
  await setHidden(browser, false);
  await sleep(400);
  const chip = await browser.evaluate(() => document.getElementById('you-chip').getBoundingClientRect().toJSON());
  assert.ok(Math.hypot(chip.left - expected.left, chip.top - expected.top) <= 2,
    `crew_settles_without_motion: bookshop chip left behind after a hidden tab (${JSON.stringify({ chip, expected })})`);
  await browser.evaluate(() => document.getElementById('close-inspector').click());
  await arrive(browser, 'bookshop home after hidden tab');
  await browser.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  await sleep(300);
  await open(browser, 'bookshop', 'compare');
  await sleep(100);
  const reduced = await crew(browser);
  assert.ok(!reduced.walking && reduced.node === 'compare', `crew_settles_without_motion: bookshop reduced motion left a route (${JSON.stringify(reduced)})`);
  assert.ok(reduced.still, 'crew_settles_without_motion: bookshop reduced motion left a bot posed');
  await browser.send('Emulation.setEmulatedMedia', { features: [] });
  const compact = {};
  for (const slug of Object.keys(BOARDS)) {
    await load(browser, base, slug, 390, 844);
    await open(browser, slug, BOARDS[slug].stand);
    await sleep(100);
    compact[slug] = await crew(browser);
    assert.ok(!compact[slug].walking && compact[slug].node === BOARDS[slug].stand, `crew_settles_without_motion: ${slug} compact left a route`);
    assert.ok(compact[slug].still, `crew_settles_without_motion: ${slug} compact left a bot posed`);
  }
  return { suspended, reduced, compact };
}

// Gate 3 section 14.2 rule 7 over 30 board switches: each crew's resources are released once.
async function disposedOnce(browser, base) {
  await load(browser, base, 'bookshop', 1280, 900);
  const rows = [];
  for (let n = 0; n < 30; n++) {
    const slug = ['gtm', 'northline', 'bookshop'][n % 3];
    await browser.evaluate(slug => { scrollTo(0, 0); const select = document.getElementById('workplace-board'); select.value = slug; select.dispatchEvent(new Event('change')); }, slug);
    assert.ok(await browser.until(() => ['ready', 'empty'].includes(document.body.dataset.loadState)), `${slug} did not load`);
    await browser.evaluate(() => document.getElementById('workplace-canvas').scrollIntoView({ block: 'center', behavior: 'instant' }));
    assert.ok(await browser.until(() => document.getElementById('graphics-status').dataset.state === 'ready'), `${slug} room did not mount`);
    rows.push(await browser.evaluate(() => ({ ...globalThis.__crewResources })));
  }
  const last = rows.at(-1);
  assert.ok(rows.every(row => row.live <= 5), `crew_disposed_once: crew resources survive (${JSON.stringify(rows.find(row => row.live > 5))})`);
  assert.equal(last.live, 5, 'crew_disposed_once: crew resources survive');
  assert.equal(last.disposed, last.created - 5, 'crew_disposed_once: a crew resource was disposed twice');
  return { switches: rows.length, last };
}

export async function runAll(base, out, fault = '') {
  if (fault) { assert.ok(FAULTS[fault], `Unknown S42 fault ${fault}`); SHARED_FAULTS[fault] = FAULTS[fault]; }
  const only = fault ? FAULTS[fault].expect.split(':')[0] : '';
  const results = [];
  const run = async (name, checks, fn) => {
    if (only && !checks.includes(only)) return;
    const browser = await openBrowser(base, path.join(out, name), fault);
    try {
      results.push(await fn(browser));
      assert.deepEqual(browser.exceptions, [], 'Uncaught client exceptions');
      browser.assertFaultServed();
    } catch (error) { browser.assertFaultServed(); throw error; }
    finally { await browser.close(); }
  };
  const journeyChecks = ['bot_walks_only_on_learner_choice', 'crew_carries_no_result_text', 'one_narrator_bubble', 'crew_walk_frames'];
  for (const slug of Object.keys(BOARDS)) await run(`journey-${slug}`, journeyChecks, browser => boardJourney(browser, base, slug));
  await run('settles', ['crew_settles_without_motion'], browser => settles(browser, base));
  await run('disposal', ['crew_disposed_once'], browser => disposedOnce(browser, base));
  await writeFile(path.join(out, 'crew-browser.json'), JSON.stringify(results, null, 2) + '\n');
  return results;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [base, out] = process.argv.slice(2);
  const index = process.argv.indexOf('--fault'), fault = index === -1 ? '' : process.argv[index + 1];
  if (!fault) console.log(JSON.stringify(await runAll(base, out)));
  else {
    try { await runAll(base, out, fault); console.error(`FAULT ${fault} NOT CAUGHT`); process.exit(1); }
    catch (error) {
      if (!String(error.message).includes(FAULTS[fault].expect)) { console.error(`FAULT ${fault} failed elsewhere: ${error.message}`); process.exit(1); }
      console.log(JSON.stringify({ fault, caught: FAULTS[fault].expect, message: String(error.message).split('\n')[0] }));
    }
  }
}
