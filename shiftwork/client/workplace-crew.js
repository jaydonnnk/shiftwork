// Gate 3 section 14 (S42): the robot crew. Original voxel bots built only from core
// Three.js primitives; nothing is taken from any reference repository or model file.
// Every box of every bot is one instance of one shared unit cube (and every light one
// instance of a second), so the whole crew draws in four calls at any bot count.

// Shortest path on a room's floor graph. Returns node ids from `from` to `to`, or null.
export function routeBetween(graph, from, to) {
  const { nodes, edges } = graph;
  if (!Object.hasOwn(nodes, from) || !Object.hasOwn(nodes, to)) return null;
  const adjacent = new Map(Object.keys(nodes).map(id => [id, []]));
  for (const [a, b] of edges) if (adjacent.has(a) && adjacent.has(b)) { adjacent.get(a).push(b); adjacent.get(b).push(a); }
  const length = (a, b) => Math.hypot(nodes[a][0] - nodes[b][0], nodes[a][1] - nodes[b][1]);
  const distance = new Map([[from, 0]]), previous = new Map(), open = new Set(Object.keys(nodes));
  while (open.size) {
    let current = null;
    for (const id of open) if (distance.has(id) && (current === null || distance.get(id) < distance.get(current))) current = id;
    if (current === null || current === to) break;
    open.delete(current);
    for (const next of adjacent.get(current)) {
      const candidate = distance.get(current) + length(current, next);
      if (!distance.has(next) || candidate < distance.get(next)) { distance.set(next, candidate); previous.set(next, current); }
    }
  }
  if (!distance.has(to)) return null;
  const path = [to];
  while (path[0] !== from) path.unshift(previous.get(path[0]));
  return path;
}

// Gate 3 section 14.2 rule 5 motion limits.
export const crewMotion = { speed: 2.6, walkBob: .09, idleBob: .02, idleHz: .3, blinkSeconds: .12, blinkEvery: [2, 5], lampSwing: .2 };
const CUSTOMER_BODIES = ['#7fa7a0', '#c98f7a', '#9a9cc4'];

export function createCrew({ THREE, room, tier, reducedMotion, register }) {
  const plan = room.crew;
  const graph = { nodes: plan.nodes, edges: plan.edges };
  const group = new THREE.Group();
  group.name = 'crew';
  const kinds = { box: [], glow: [], disc: [] };
  // A deterministic stand-in for randomness keeps blinks and phases reproducible.
  const scatter = seed => { const x = Math.sin(seed * 12.9898) * 43758.5453; return x - Math.floor(x); };

  function buildBot({ body, trim, lamp, hat = null, scale = 1, seed }) {
    const root = new THREE.Object3D(), rig = new THREE.Object3D(), head = new THREE.Object3D();
    const bot = { root, rig, head, legs: [], arms: [], eyes: [], lamp: null, lampColor: new THREE.Color(lamp), scale,
      phase: scatter(seed) * 6, seed, blinkAt: 1 + scatter(seed + .5) * 3, yaw: 0 };
    const part = (parent, kind, size, position, color) => {
      const object = new THREE.Object3D();
      object.position.fromArray(position); object.scale.fromArray(size);
      parent.add(object);
      const entry = { object, color: new THREE.Color(color), size };
      kinds[kind].push(entry);
      return entry;
    };
    root.add(rig);
    for (const x of [-.11, .11]) {
      const leg = new THREE.Object3D(); leg.position.set(x, .28, 0); rig.add(leg); bot.legs.push(leg);
      part(leg, 'box', [.13, .26, .15], [0, -.13, 0], trim);
      part(leg, 'box', [.16, .07, .22], [0, -.26, .03], trim);
    }
    part(rig, 'box', [.46, .4, .34], [0, .48, 0], body);
    part(rig, 'box', [.3, .18, .02], [0, .46, .18], trim);
    // The chest light repeats the antenna colour: no green or red that could read as a verdict.
    part(rig, 'glow', [.06, .04, .02], [.08, .52, .195], lamp);
    for (const x of [-.29, .29]) {
      const arm = new THREE.Object3D(); arm.position.set(x, .64, 0); rig.add(arm); bot.arms.push(arm);
      part(arm, 'box', [.1, .3, .12], [0, -.15, 0], body);
      part(arm, 'box', [.12, .08, .14], [0, -.32, 0], trim);
    }
    head.position.set(0, .71, 0); rig.add(head);
    part(head, 'box', [.5, .36, .4], [0, .18, 0], '#f3eee3');
    part(head, 'box', [.4, .24, .02], [0, .18, .205], '#1b2433');
    for (const x of [-.08, .08]) bot.eyes.push(part(head, 'glow', [.07, .09, .02], [x, .19, .22], '#8ff0ff'));
    for (const x of [-.27, .27]) part(head, 'box', [.06, .1, .06], [x, .18, 0], trim);
    part(head, 'box', [.03, .16, .03], [0, .44, 0], trim);
    bot.lamp = part(head, 'glow', [.09, .09, .09], [0, .55, 0], lamp);
    if (hat) part(head, 'box', [.54, .06, .44], [0, .39, 0], hat);
    const disc = part(root, 'disc', [.64, .64, 1], [0, .006, 0], '#000000');
    disc.object.rotation.x = -Math.PI / 2;
    root.scale.setScalar(scale);
    return bot;
  }
  const place = (bot, [x, z]) => bot.root.position.set(x, 0, z);
  const face = (bot, [x, z]) => { bot.yaw = Math.atan2(x - bot.root.position.x, z - bot.root.position.z); };

  // Visual spec section 12: You is amber with navy trim; staff trim takes the room's wood.
  const roomTrim = room.materials.wood ?? room.materials.pin ?? '#8a7052', paper = room.materials.paper ?? '#f6f0e2';
  const you = buildBot({ body: '#edbd68', trim: '#202c40', lamp: '#edbd68', scale: 1, seed: 1 });
  const staff = plan.staff.map((spot, index) => {
    const customers = plan.staff.slice(0, index).filter(item => item.role === 'customer').length;
    const look = spot.role === 'owner'
      ? { body: '#202c40', trim: roomTrim, lamp: paper, hat: roomTrim, scale: 1 }
      : { body: CUSTOMER_BODIES[customers % CUSTOMER_BODIES.length], trim: '#3b4656', lamp: paper, scale: .9 };
    const bot = buildBot({ ...look, seed: index + 2 });
    bot.role = spot.role;
    place(bot, spot.at); face(bot, spot.face);
    return bot;
  });
  const bots = [you, ...staff];

  const meshes = {};
  try {
    const cube = register(new THREE.BoxGeometry(1, 1, 1));
    const circle = register(new THREE.CircleGeometry(.5, 24));
    const materials = {
      box: register(new THREE.MeshStandardMaterial({ color: '#ffffff', roughness: .7 })),
      glow: register(new THREE.MeshBasicMaterial({ color: '#ffffff', toneMapped: false })),
      disc: register(new THREE.MeshBasicMaterial({ color: '#000000', transparent: true, opacity: .16, depthWrite: false })),
    };
    for (const [kind, entries] of Object.entries(kinds)) {
      const mesh = new THREE.InstancedMesh(kind === 'disc' ? circle : cube, materials[kind], entries.length);
      // Bots move, so the instance bounds are never stale-culled.
      mesh.frustumCulled = false;
      mesh.castShadow = kind === 'box' && tier !== 'compact';
      mesh.name = `crew-${kind}`;
      entries.forEach((entry, index) => { entry.mesh = mesh; entry.index = index; mesh.setColorAt(index, entry.color); });
      group.add(mesh); meshes[kind] = mesh;
    }
  } catch (error) { group.clear(); throw error; }

  // The learner's bot (Gate 3 section 14.2 rule 3). It leaves its node only through walkTo.
  let node = plan.home, path = [], openStation = null;
  const point = id => plan.nodes[id];
  place(you, point(node));
  face(you, plan.facing?.home ?? [0, 0]);
  const atRest = () => path.length === 0;
  const typing = () => atRest() && openStation !== null && node === plan.stands[openStation];
  function faceArrival() {
    const anchor = openStation && room.stationAnchors[openStation];
    if (typing() && anchor) face(you, [anchor[0], anchor[2]]);
    else if (node === plan.home && plan.facing?.home) face(you, plan.facing.home);
  }
  function walkTo(stationId) {
    openStation = stationId && Object.hasOwn(plan.stands, stationId) ? stationId : null;
    const goal = openStation ? plan.stands[openStation] : plan.home;
    // Mid-walk the bot replans from whichever end of its current lane is nearer, so
    // it never leaves an authored lane.
    let from = node;
    if (path.length) {
      const here = [you.root.position.x, you.root.position.z], next = point(path[0]), last = point(node);
      if (Math.hypot(next[0] - here[0], next[1] - here[1]) < Math.hypot(last[0] - here[0], last[1] - here[1])) from = path[0];
    }
    const route = routeBetween(graph, from, goal) ?? [from];
    const standing = Math.hypot(point(from)[0] - you.root.position.x, point(from)[1] - you.root.position.z) < 1e-6;
    path = standing ? route.slice(1) : route;
    if (standing) node = from;
    if (!path.length) faceArrival();
    // Gate 2 R7: the compact tier and reduced motion show the bot at its settled spot.
    if (tier === 'compact' || reducedMotion) settle();
  }
  function advance(dt) {
    let budget = crewMotion.speed * dt;
    while (budget > 0 && path.length) {
      const [x, z] = point(path[0]), dx = x - you.root.position.x, dz = z - you.root.position.z, gap = Math.hypot(dx, dz);
      if (gap > 1e-6) you.yaw = Math.atan2(dx, dz);
      if (gap <= budget) { you.root.position.set(x, 0, z); node = path.shift(); budget -= gap; }
      else { you.root.position.x += dx / gap * budget; you.root.position.z += dz / gap * budget; budget = 0; }
    }
    you.phase += dt * 13;
    if (!path.length) faceArrival();
  }
  function settle() {
    if (path.length) { node = path.at(-1); place(you, point(node)); path = []; }
    faceArrival();
    for (const bot of bots) pose(bot, 0, false);
    flush();
  }
  function pose(bot, t, ambient) {
    const walking = bot === you && !atRest(), swing = Math.sin(bot.phase);
    const busy = bot === you && typing();
    bot.root.rotation.y = bot.yaw;
    bot.rig.position.y = walking ? Math.abs(swing) * crewMotion.walkBob
      : ambient ? Math.sin(2 * Math.PI * crewMotion.idleHz * t + bot.phase) * crewMotion.idleBob : 0;
    bot.rig.rotation.z = walking ? swing * .05 : 0;
    bot.legs[0].rotation.x = walking ? swing * .7 : 0;
    bot.legs[1].rotation.x = walking ? -swing * .7 : 0;
    const reach = busy ? -1.1 : 0, tap = busy && ambient ? .15 : 0, sway = !busy && !walking && ambient ? .06 : 0;
    bot.arms[0].rotation.x = walking ? -swing * .8 : reach + Math.sin(t * 18) * tap + Math.sin(t * 1.3 + bot.phase) * sway;
    bot.arms[1].rotation.x = walking ? swing * .8 : reach + Math.cos(t * 18) * tap - Math.sin(t * 1.3 + bot.phase) * sway;
    bot.head.rotation.y = !walking && ambient ? Math.sin(t * .5 + bot.phase * 2) * .18 : 0;
    let closed = false;
    if (ambient) {
      if (t >= bot.blinkAt + crewMotion.blinkSeconds) {
        const [low, high] = crewMotion.blinkEvery;
        bot.blinkAt = t + low + scatter(bot.seed + t) * (high - low);
      }
      closed = t >= bot.blinkAt && t < bot.blinkAt + crewMotion.blinkSeconds;
    }
    for (const eye of bot.eyes) eye.object.scale.y = eye.size[1] * (closed ? .12 : 1);
    // Antenna lamp brightness stays within 80 to 100 percent of its colour.
    const glow = ambient ? 1 - crewMotion.lampSwing * (1 + Math.sin(t * 3 + bot.phase)) / 2 : 1;
    bot.lamp.mesh?.setColorAt(bot.lamp.index, bot.lamp.color.copy(bot.lampColor).multiplyScalar(glow));
  }
  function flush() {
    for (const bot of bots) bot.root.updateMatrixWorld(true);
    for (const [kind, entries] of Object.entries(kinds)) {
      const mesh = meshes[kind];
      if (!mesh) continue;
      for (const entry of entries) mesh.setMatrixAt(entry.index, entry.object.matrixWorld);
      mesh.instanceMatrix.needsUpdate = true;
      if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    }
  }
  // Returns true while the learner's bot is still walking, so the scene keeps drawing.
  function tick(dt, t, ambient) {
    if (path.length) advance(dt);
    for (const bot of bots) pose(bot, t, ambient);
    flush();
    return path.length > 0;
  }
  const head = bot => new THREE.Vector3(bot.root.position.x, 1.45 * bot.scale, bot.root.position.z);
  // Every bot starts on its settled spot; only a later walkTo starts travel, and the
  // scene settles that at once on the compact tier, with reduced motion or suspended.
  settle();
  return {
    group, walkTo, tick, settle,
    get walking() { return path.length > 0; },
    speakerAnchor(role) { const bot = staff.find(item => item.role === role); return bot ? head(bot) : null; },
    youAnchor() { return head(you); },
    // Test observation only: the learner bot's node and route, never shown on screen.
    state() {
      return { node, path: [...path], openStation, position: [you.root.position.x, you.root.position.z],
        bots: bots.map(bot => ({ role: bot.role ?? 'you', bob: bot.rig.position.y, sway: bot.rig.rotation.z, head: bot.head.rotation.y,
          legs: bot.legs.map(leg => leg.rotation.x), arms: bot.arms.map(arm => arm.rotation.x),
          eyes: bot.eyes[0].object.scale.y / bot.eyes[0].size[1], glow: bot.lamp.color.r / bot.lampColor.r })) };
    },
    dispose() { group.removeFromParent(); group.clear(); for (const key of Object.keys(meshes)) delete meshes[key]; path = []; },
  };
}
