// S42 robot crew checks (Gate 3 section 14.4), GPU-free.
// Each check runs clean against the production modules, then once per fault against
// an in-memory mutation written to a scratch copy. A fault passes only when its own
// named assertion fails. The repository files are never modified.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import * as THREE from '../../shiftwork/client/vendor/three-r180/three.module.js';

const client = path.join(path.dirname(fileURLToPath(import.meta.url)), '../../shiftwork/client');
const FILES = ['workplace-crew.js', 'workplace-rooms.js', 'index.html'];
const pristine = Object.fromEntries(await Promise.all(FILES.map(async file => [file, await readFile(path.join(client, file), 'utf8')])));
const digest = text => createHash('sha256').update(text).digest('hex');

// One mutation per guard. `needle` must occur exactly once in its file.
export const FAULTS = {
  'bookshop-lane-through-console': { file: 'workplace-rooms.js', needle: 'service: [0,2.05]', replacement: 'service: [0,1.5]',
    check: 'routes', expect: 'crew_routes_stay_clear: bookshop lane service-h4 meets furniture' },
  'gtm-lane-through-table': { file: 'workplace-rooms.js', needle: 'workflow: [0,2.3]', replacement: 'workflow: [0,1.4]',
    check: 'routes', expect: 'crew_routes_stay_clear: gtm lane home-workflow meets furniture' },
  'northline-lane-through-rail': { file: 'workplace-rooms.js', needle: "['acceptance','rail']", replacement: "['acceptance','rollout']",
    check: 'routes', expect: 'crew_routes_stay_clear: northline lane acceptance-rollout meets furniture' },
  'ambient-drift': { file: 'workplace-crew.js', needle: 'bot.root.rotation.y = bot.yaw;',
    replacement: 'bot.root.rotation.y = bot.yaw; if (ambient) bot.root.position.x += .001;',
    check: 'walk', expect: 'bot_walks_only_on_learner_choice: bookshop moved without a choice' },
  'replan-off-lane': { file: 'workplace-crew.js',
    needle: 'if (Math.hypot(next[0] - here[0], next[1] - here[1]) < Math.hypot(last[0] - here[0], last[1] - here[1])) from = path[0];',
    replacement: 'from = openStation ? plan.stands[openStation] : plan.home;',
    check: 'walk', expect: 'bot_walks_only_on_learner_choice: bookshop replan left its lanes' },
  'compact-travels': { file: 'workplace-crew.js', needle: "if (tier === 'compact' || reducedMotion) settle();", replacement: 'void 0;',
    check: 'settle', expect: 'crew_settles_without_motion: bookshop compact left a route' },
  'settle-keeps-route': { file: 'workplace-crew.js', needle: 'if (path.length) { node = path.at(-1); place(you, point(node)); path = []; }',
    replacement: 'void 0;', check: 'settle', expect: 'crew_settles_without_motion: bookshop settle mid-walk left a route' },
  'settle-keeps-bob': { file: 'workplace-crew.js', needle: 'for (const bot of bots) pose(bot, 0, false);',
    replacement: 'for (const bot of bots) pose(bot, 0.8, true);', check: 'settle', expect: 'crew_settles_without_motion: bookshop settled bot still posed' },
  'fast-idle': { file: 'workplace-crew.js', needle: 'idleHz: .3', replacement: 'idleHz: .5',
    check: 'motion', expect: 'crew_motion_within_limits: idle bob cycle' },
  'register-twice': { file: 'workplace-crew.js', needle: "const circle = register(new THREE.CircleGeometry(.5, 24));",
    replacement: "const circle = register(register(new THREE.CircleGeometry(.5, 24)));",
    check: 'resources', expect: 'crew_disposed_once: a resource is registered twice' },
  'chip-carries-version': { file: 'index.html', needle: '<span id="you-chip" class="you-chip" hidden>You</span>',
    replacement: '<span id="you-chip" class="you-chip" hidden>You · ver-0002</span>',
    check: 'text', expect: 'crew_carries_no_result_text: chip text' },
};

async function load(fault) {
  const files = { ...pristine };
  if (fault) {
    const { file, needle, replacement } = FAULTS[fault];
    assert.equal(files[file].split(needle).length - 1, 1, `Fault ${fault} needle must occur exactly once`);
    files[file] = files[file].replace(needle, replacement);
  }
  const dir = await mkdtemp(path.join(tmpdir(), 'shiftwork-s42-crew-'));
  try {
    for (const file of FILES) await writeFile(path.join(dir, file), files[file]);
    const crew = await import(pathToFileURL(path.join(dir, 'workplace-crew.js')).href);
    const rooms = await import(pathToFileURL(path.join(dir, 'workplace-rooms.js')).href);
    return { ...crew, ...rooms, html: files['index.html'] };
  } finally { await rm(dir, { recursive: true, force: true }); }
}

const ROOMS = ['bookshop', 'gtm', 'northline'];
const CLEARANCE = .2, BOT_HEIGHT = 1.4;
const make = (api, board, options = {}) => api.createCrew({ THREE, room: api.roomDefinitions[board], tier: 'standard', reducedMotion: false, register: resource => resource, ...options });

// Floor footprint of every assembly a bot could walk into: anything that reaches
// below a bot's height except the floor itself.
function footprints(room) {
  return room.assemblies.filter(item => item.material !== 'floor' && item.position[1] - item.size[1] / 2 < BOT_HEIGHT).map(item => {
    const angle = item.rotation?.[2] ?? 0;
    const hx = Math.abs(item.size[0] / 2 * Math.cos(angle)) + Math.abs(item.size[1] / 2 * Math.sin(angle)), hz = item.size[2] / 2;
    return { x0: item.position[0] - hx, x1: item.position[0] + hx, z0: item.position[2] - hz, z1: item.position[2] + hz, station: item.station };
  });
}
const pointRect = ([x, z], r) => Math.hypot(Math.max(r.x0 - x, 0, x - r.x1), Math.max(r.z0 - z, 0, z - r.z1));
const pointSegment = ([x, z], [ax, az], [bx, bz]) => {
  const dx = bx - ax, dz = bz - az, length = dx * dx + dz * dz;
  const s = length ? Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / length)) : 0;
  return Math.hypot(x - ax - s * dx, z - az - s * dz);
};
// Exact: a segment meets a rectangle if it clips (Liang-Barsky); otherwise the gap is
// the least of its endpoints to the rectangle and the rectangle's corners to it.
function segmentRect(a, b, r) {
  let t0 = 0, t1 = 1;
  const dx = b[0] - a[0], dz = b[1] - a[1];
  const clips = [[-dx, a[0] - r.x0], [dx, r.x1 - a[0]], [-dz, a[1] - r.z0], [dz, r.z1 - a[1]]].every(([p, q]) => {
    if (p === 0) return q >= 0;
    const t = q / p;
    if (p < 0) t0 = Math.max(t0, t); else t1 = Math.min(t1, t);
    return t0 <= t1;
  });
  if (clips) return 0;
  return Math.min(pointRect(a, r), pointRect(b, r), ...[[r.x0, r.z0], [r.x0, r.z1], [r.x1, r.z0], [r.x1, r.z1]].map(c => pointSegment(c, a, b)));
}
const onLane = (plan, position) => plan.edges.some(([a, b]) => pointSegment(position, plan.nodes[a], plan.nodes[b]) < 1e-6);

async function routesCheck(api) {
  for (const board of ROOMS) {
    const room = api.roomDefinitions[board], plan = room.crew, rects = footprints(room);
    assert.ok(plan && rects.length > 5, `crew_routes_stay_clear: ${board} has no crew plan or furniture`);
    for (const [a, b] of plan.edges) {
      assert.ok(plan.nodes[a] && plan.nodes[b], `crew_routes_stay_clear: ${board} lane ${a}-${b} names an unknown node`);
      const gap = Math.min(...rects.map(r => segmentRect(plan.nodes[a], plan.nodes[b], r)));
      assert.ok(gap >= CLEARANCE, `crew_routes_stay_clear: ${board} lane ${a}-${b} meets furniture (gap ${gap.toFixed(3)})`);
    }
    for (const stationId of Object.keys(room.stationAnchors)) {
      const stand = plan.stands[stationId];
      assert.ok(stand && plan.nodes[stand], `crew_routes_stay_clear: ${board} station ${stationId} has no stand`);
      assert.ok(api.routeBetween(plan, plan.home, stand), `crew_routes_stay_clear: ${board} station ${stationId} is unreachable`);
    }
    for (const spot of plan.staff) {
      const gap = Math.min(...rects.map(r => pointRect(spot.at, r)));
      assert.ok(gap >= CLEARANCE, `crew_routes_stay_clear: ${board} ${spot.role} stands in furniture (gap ${gap.toFixed(3)})`);
    }
  }
}

function walkUntilStill(crew, plan, board, label, limit = 1200) {
  let previous = crew.state().position, seconds = 0;
  for (let frame = 0; frame < limit && crew.walking; frame++) {
    crew.tick(1 / 60, frame / 60, true); seconds += 1 / 60;
    const now = crew.state().position;
    assert.ok(onLane(plan, now), `bot_walks_only_on_learner_choice: ${board} ${label} left its lanes`);
    assert.ok(Math.hypot(now[0] - previous[0], now[1] - previous[1]) <= 2.6 / 60 + 1e-9, `bot_walks_only_on_learner_choice: ${board} ${label} walked faster than 2.6`);
    previous = now;
  }
  assert.equal(crew.walking, false, `bot_walks_only_on_learner_choice: ${board} ${label} never arrived`);
  return seconds;
}

async function walkCheck(api) {
  let longest = 0;
  for (const board of ROOMS) {
    const plan = api.roomDefinitions[board].crew, crew = make(api, board);
    const home = crew.state().position;
    assert.deepEqual(home, plan.nodes[plan.home], `bot_walks_only_on_learner_choice: ${board} does not start home`);
    // Ambient ticks, settles and idle frames never move the bot without a choice.
    for (let frame = 0; frame < 600; frame++) { crew.tick(1 / 60, frame / 60, frame % 3 !== 0); if (frame % 97 === 0) crew.settle(); }
    assert.deepEqual(crew.state().position, home, `bot_walks_only_on_learner_choice: ${board} moved without a choice`);
    assert.equal(crew.state().node, plan.home, `bot_walks_only_on_learner_choice: ${board} moved without a choice`);
    for (const stationId of Object.keys(plan.stands)) {
      crew.walkTo(stationId);
      longest = Math.max(longest, walkUntilStill(crew, plan, board, `walk to ${stationId}`));
      assert.equal(crew.state().node, plan.stands[stationId], `bot_walks_only_on_learner_choice: ${board} did not reach ${stationId}`);
      const parked = crew.state().position;
      for (let frame = 0; frame < 120; frame++) crew.tick(1 / 60, 10 + frame / 60, true);
      assert.deepEqual(crew.state().position, parked, `bot_walks_only_on_learner_choice: ${board} moved without a choice`);
      crew.walkTo(null);
      longest = Math.max(longest, walkUntilStill(crew, plan, board, `return from ${stationId}`));
      assert.equal(crew.state().node, plan.home, `bot_walks_only_on_learner_choice: ${board} did not return home`);
    }
    // A new choice mid-walk replans from the nearer end of the current lane.
    const stands = Object.keys(plan.stands);
    for (const [first, second] of stands.flatMap(a => stands.filter(b => b !== a).map(b => [a, b]))) {
      crew.walkTo(first);
      for (let frame = 0; frame < 25 && crew.walking; frame++) crew.tick(1 / 60, frame / 60, true);
      crew.walkTo(second);
      walkUntilStill(crew, plan, board, 'replan');
      assert.equal(crew.state().node, plan.stands[second], `bot_walks_only_on_learner_choice: ${board} replan did not arrive`);
    }
    crew.walkTo('not-a-station');
    walkUntilStill(crew, plan, board, 'unknown station');
    assert.equal(crew.state().node, plan.home, `bot_walks_only_on_learner_choice: ${board} unknown station is not home`);
  }
  assert.ok(longest <= 3.5, `bot_walks_only_on_learner_choice: a walk took ${longest.toFixed(2)}s`);
  return longest;
}

const still = bot => bot.bob === 0 && bot.sway === 0 && bot.head === 0 && bot.legs.every(value => value === 0) && bot.eyes === 1 && bot.glow === 1;
async function settleCheck(api) {
  for (const board of ROOMS) {
    const plan = api.roomDefinitions[board].crew;
    const crew = make(api, board), target = Object.keys(plan.stands).at(-1);
    crew.walkTo(target);
    for (let frame = 0; frame < 20; frame++) crew.tick(1 / 60, 7.3 + frame / 60, true);
    assert.equal(crew.walking, true, `crew_settles_without_motion: ${board} test walk ended too early`);
    crew.settle();
    assert.equal(crew.walking, false, `crew_settles_without_motion: ${board} settle mid-walk left a route`);
    assert.equal(crew.state().node, plan.stands[target], `crew_settles_without_motion: ${board} settle mid-walk left a route`);
    assert.ok(crew.state().bots.every(still), `crew_settles_without_motion: ${board} settled bot still posed`);
    // Ambient ending puts every bot back to rest on the next drawn frame.
    for (let frame = 0; frame < 60; frame++) crew.tick(1 / 60, 9 + frame / 60, true);
    crew.tick(1 / 60, 11, false);
    assert.ok(crew.state().bots.every(still), `crew_settles_without_motion: ${board} ambient end left a bot posed`);
    for (const [label, options] of [['compact', { tier: 'compact' }], ['reduced motion', { reducedMotion: true }]]) {
      const crew = make(api, board, options);
      for (const stationId of [...Object.keys(plan.stands), null]) {
        crew.walkTo(stationId);
        assert.equal(crew.walking, false, `crew_settles_without_motion: ${board} ${label} left a route`);
        assert.equal(crew.state().node, stationId ? plan.stands[stationId] : plan.home, `crew_settles_without_motion: ${board} ${label} not at its settled spot`);
        crew.tick(1 / 60, 3, false);
        assert.ok(crew.state().bots.every(still), `crew_settles_without_motion: ${board} ${label} bot still posed`);
      }
    }
  }
}

// Gate 3 section 14.2 rule 5, measured over 30 seconds of ambient frames at 60Hz.
async function motionCheck(api) {
  const crew = make(api, 'bookshop'), frames = 30 * 60, samples = [];
  for (let frame = 0; frame < frames; frame++) { crew.tick(1 / 60, frame / 60, true); samples.push(crew.state().bots); }
  for (let index = 0; index < samples[0].length; index++) {
    const series = samples.map(bots => bots[index]);
    const bob = series.map(bot => bot.bob);
    assert.ok(Math.max(...bob.map(Math.abs)) <= .02 + 1e-9, 'crew_motion_within_limits: idle bob height');
    const crossings = bob.slice(1).filter((value, i) => Math.sign(value) !== Math.sign(bob[i]) && value !== 0).length;
    assert.ok(crossings / 2 / 30 <= .35, `crew_motion_within_limits: idle bob cycle ${(crossings / 60).toFixed(2)}Hz`);
    const glow = series.map(bot => bot.glow);
    assert.ok(Math.min(...glow) / Math.max(...glow) >= .6, 'crew_motion_within_limits: lamp brightness');
    const closed = [];
    series.forEach((bot, frame) => { if (bot.eyes < 1 && (frame === 0 || series[frame - 1].eyes === 1)) closed.push({ start: frame, end: frame }); if (bot.eyes < 1) closed.at(-1).end = frame; });
    assert.ok(closed.length >= 5, 'crew_motion_within_limits: no blinks');
    for (const blink of closed) assert.ok((blink.end - blink.start + 1) / 60 <= .12 + 1 / 60, 'crew_motion_within_limits: blink length');
    for (let i = 1; i < closed.length; i++) {
      const gap = (closed[i].start - closed[i - 1].start) / 60;
      assert.ok(gap >= 2 - 1 / 60 && gap <= 5 + .12 + 2 / 60, `crew_motion_within_limits: blink gap ${gap.toFixed(2)}s`);
    }
  }
  crew.walkTo('ledger');
  let walkBob = 0;
  while (crew.walking) { crew.tick(1 / 60, 40, false); walkBob = Math.max(walkBob, Math.abs(crew.state().bots[0].bob)); }
  assert.ok(walkBob > 0 && walkBob <= .09 + 1e-9, 'crew_motion_within_limits: walk bob');
}

async function resourcesCheck(api) {
  for (const board of ROOMS) for (const tier of ['standard', 'compact']) {
    const registered = [];
    const crew = make(api, board, { tier, register: resource => { registered.push(resource); return resource; } });
    assert.equal(new Set(registered).size, registered.length, 'crew_disposed_once: a resource is registered twice');
    const used = new Set();
    crew.group.traverse(object => { if (object.isMesh) { used.add(object.geometry); used.add(object.material); } });
    for (const resource of used) assert.ok(registered.includes(resource), 'crew_disposed_once: a resource is not registered');
    assert.ok(crew.group.children.length <= 4, `crew_disposed_once: ${board} crew draws ${crew.group.children.length} meshes`);
    crew.dispose();
    assert.equal(crew.group.children.length, 0, 'crew_disposed_once: dispose left meshes');
  }
}

const RESULT_WORDS = /\b(pass(ed)?|fail(ed|ure)?|eligible|verdict|score|selected|chosen|correct|wrong|ver-\d+|version|ai|assistant)\b/i;
async function textCheck(api) {
  const chip = api.html.match(/<span id="you-chip"[^>]*>([^<]*)<\/span>/);
  assert.equal(chip?.[1], 'You', 'crew_carries_no_result_text: chip text');
  for (const board of ROOMS) {
    const crew = make(api, board);
    crew.group.traverse(object => {
      assert.ok(object === crew.group || object.isInstancedMesh, `crew_carries_no_result_text: ${board} bot carries a ${object.type}`);
      assert.ok(!object.material?.map, `crew_carries_no_result_text: ${board} bot carries a texture`);
      assert.ok(!RESULT_WORDS.test(object.name), `crew_carries_no_result_text: ${board} bot name ${object.name}`);
    });
  }
}

const CHECKS = { routes: routesCheck, walk: walkCheck, settle: settleCheck, motion: motionCheck, resources: resourcesCheck, text: textCheck };
const NAMES = { routes: 'crew_routes_stay_clear', walk: 'bot_walks_only_on_learner_choice', settle: 'crew_settles_without_motion',
  motion: 'crew_motion_within_limits', resources: 'crew_disposed_once', text: 'crew_carries_no_result_text' };

for (const [check, name] of Object.entries(NAMES)) test(name, async () => { await CHECKS[check](await load()); });

for (const [fault, row] of Object.entries(FAULTS)) test(`fault_${fault}_fails_${NAMES[row.check]}`, async () => {
  const broken = await load(fault);
  await assert.rejects(() => CHECKS[row.check](broken), error => {
    assert.ok(String(error.message).includes(row.expect), `Fault ${fault} failed elsewhere: ${error.message}`);
    return true;
  });
  await CHECKS[row.check](await load());
  for (const file of FILES) assert.equal(digest(await readFile(path.join(client, file), 'utf8')), digest(pristine[file]), `${file} changed`);
});
