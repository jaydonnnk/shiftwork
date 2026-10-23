// S36 to S40 full-screen workplace checks (Gate 3 section 13.9).
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
  // S41 calm room (Gate 3 section 14.4).
  'resting-all-visible': { file: '/app.js',
    needle: "button.dataset.resting = button.dataset.station === speaker?.stationId ? 'speaker' : String(resting.has(button.dataset.station));",
    replacement: "button.dataset.resting = 'true';", expect: 'resting_tags_show_next_and_one_failure: rest-visible tags' },
  'speaker-tag-shows': { file: '/app.js',
    needle: "button.dataset.resting = button.dataset.station === speaker?.stationId ? 'speaker' : String(resting.has(button.dataset.station));",
    replacement: 'button.dataset.resting = String(resting.has(button.dataset.station));', expect: 'one_narrator_bubble: speaker tag beside its bubble' },
  'two-bubbles': { file: '/app.js', needle: "$('owner-bubble').hidden = !said('owner');", replacement: "$('owner-bubble').hidden = false;",
    expect: 'one_narrator_bubble: bubbles shown' },
  'open-tag-hidden': { file: '/styles.css', needle: '.world[data-inspector="open"] .room[data-graphics="ready"] .station[data-resting="false"][aria-pressed="true"] { opacity: 1; pointer-events: auto; }',
    replacement: '', expect: 'resting_tags_show_next_and_one_failure: the open station hides its tag' },
  'focus-stays-hidden': { file: '/styles.css', needle: '.station:is([data-resting="false"], [data-resting="speaker"]):not(:focus-visible):not([data-hover])',
    replacement: '.station:is([data-resting="false"], [data-resting="speaker"]):not([data-hover])', expect: 'hidden_tags_stay_reachable: a focused tag stays hidden' },
  'hidden-leaves-tab-order': { file: '/styles.css', needle: ':not([data-hover]) { opacity: 0; pointer-events: none; }',
    replacement: ':not([data-hover]) { opacity: 0; pointer-events: none; display: none; }', expect: 'hidden_tags_stay_reachable: a hidden tag cannot take focus' },
  'choose-confirm-focus': { file: '/app.js', needle: "  $('selection-rationale').focus();",
    replacement: "  document.getElementById('select-candidate-a').disabled = false; document.getElementById('select-candidate-a').focus();",
    expect: 'choose_dialog_has_no_default: rationale must receive focus' },
  'choose-close-selects': { file: '/app.js', needle: "$('cancel-choose').addEventListener('click', () => $('choose-dialog').close());",
    replacement: "document.getElementById('cancel-choose').addEventListener('click', () => { chooseCandidate('A'); document.getElementById('choose-dialog').close(); });",
    expect: 'choose_dialog_has_no_default: Cancel sent a request' },
  'report-null-zero': { file: '/workplace-story.js',
    needle: "const count = type => countable ? runEvents.filter(event => event.event_type === type).length : null;",
    replacement: "const count = type => countable ? runEvents.filter(event => event.event_type === type).length : 0;",
    expect: 'shift_report_matches_ledger: missing link must display unknown' },
  'dialog-tab-escapes': { file: '/app.js', needle: "    if (event.key !== 'Tab' || !dialog.open) return;",
    replacement: '    return;', expect: 'dialog_keyboard: shift-report did not trap' },
  'dialog-escape-inspector': { file: '/app.js', needle: "    if (event.key === 'Escape') event.stopPropagation();",
    replacement: '', expect: 'dialog_keyboard: Escape changed the workbench' },
  'report-loses-continuity': { file: '/app.js', needle: "  if (view.consistency !== 'conflict') reportPrevious = view;",
    replacement: "  reportPrevious = view.consistency === 'conflict' ? null : view;",
    expect: 'shift_report_matches_ledger: operation did not open its report' },
  'choose-stale-close': { file: '/app.js', needle: "$('choose-dialog').addEventListener('close', () => {\n  if ($('choose-dialog').open) return;",
    replacement: "$('choose-dialog').addEventListener('close', () => {",
    expect: 'choose_dialog_has_no_default: stale close hid the reopened confirmation' },
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
    needle: '      ?? inside.reduce((best, spot) => less(box(spot), box(best)) < 0 ? spot : best, inside[0] ?? candidates[0]);',
    replacement: '      ?? candidates[0];', expect: 'inspector_keeps_stations_readable: a station tag covers another station tag' },
  'tags-not-taken': { file: '/app.js', needle: '    placed.push(box([left, top]));',
    replacement: '', expect: 'inspector_keeps_stations_readable: a station tag covers another station tag' },
  'run-help-silent': { file: '/app.js',
    needle: `    : operationRecorded ? "This shift's operation run is recorded. Close the shift at Next shift; the operating version runs in the next shift."\n`,
    replacement: '', expect: 'run_help_matches_disabled_run: fresh shift' },
  'run-help-budget-words': { file: '/app.js',
    needle: "'No attempt remains in this shift, so the controller will not accept another run. Close the shift at Next shift to continue.'",
    replacement: "'Attempt budget exhausted. The controller will not accept another run.'",
    expect: 'run_help_matches_disabled_run: learner choice in a shift that already ran' },
  'chip-rewrites': { file: '/app.js',
    needle: "const announce = (id, value) => { if ($(id).textContent !== value) text(id, value); };",
    replacement: 'const announce = (id, value) => text(id, value);',
    expect: 'step_chip_announces_only_changes: typing' },
  'status-wraps': { file: '/styles.css',
    needle: '.graphics-controls { position: absolute; top: 16px; right: 16px; z-index: 5; width: 320px;',
    replacement: '.graphics-controls { position: absolute; top: 16px; right: 16px; z-index: 5; width: 320px; } .status-bar { max-width: calc(100% - 520px); } .x {',
    expect: 'status_bar_stays_one_row: bookshop' },
  'fallback-clip': { file: '/styles.css',
    needle: '#bookshop-stations .station > span:last-child { flex-direction: column; align-items: flex-start; gap: 0; max-width: none; overflow: visible; }',
    replacement: '#bookshop-stations .station > span:last-child { flex-direction: column; align-items: flex-start; gap: 0; max-width: 80px; overflow: hidden; }',
    expect: 'fallback_tag_text_is_not_clipped: bookshop' },
  'fallback-overlap': { file: '/styles.css',
    needle: '#bookshop-stations .station-compare { left: 35%; top: 66%; }', replacement: '#bookshop-stations .station-compare { left: 22%; top: 62%; }',
    expect: 'fallback_tags_do_not_overlap: bookshop' },
  'fallback-under-chip': { file: '/styles.css',
    needle: '#bookshop-stations .station-evaluator { left: 69%; top: 26%; }', replacement: '#bookshop-stations .station-evaluator { left: 52%; top: 21%; }',
    expect: 'fallback_tags_clear_of_panels: bookshop' },
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
  'two-owner-lines': { file: '/app.js', needle: "  text('owner-bubble-text', said('owner')?.text ?? '');\n",
    replacement: "  text('owner-bubble-text', said('owner')?.text ?? '');\n  if (said('owner') && !document.getElementById('duplicate-owner')) document.getElementById('story-layer').append(Object.assign(document.getElementById('owner-bubble').cloneNode(true), { id: 'duplicate-owner' }));\n",
    expect: 'main_view_shows_one_of_each: investigating shows 2 owner' },
  'draft-enables': { file: '/app.js',
    needle: "for (const id of ['cause-input', 'falsifier-input']) $(id).addEventListener('input', () => renderGuide());",
    replacement: "for (const id of ['cause-input', 'falsifier-input']) $(id).addEventListener('input', () => { renderGuide(); document.getElementById('run-comparison').disabled = false; });",
    expect: "guide_never_credits_unsent_text: a cause draft changed a control's disabled state" },
  'draft-counts': { file: '/app.js',
    needle: "for (const id of ['cause-input', 'falsifier-input']) $(id).addEventListener('input', () => renderGuide());",
    replacement: "for (const id of ['cause-input', 'falsifier-input']) $(id).addEventListener('input', () => { renderGuide(); document.getElementById('investigation-tag').textContent = '1 recorded'; });",
    expect: 'guide_never_credits_unsent_text: a cause draft changed the investigation count' },
  'chip-leak': { file: '/app.js', needle: "  announce('step-chip-name', storyGuide.step ? storyGuide.name : '');",
    replacement: "  announce('step-chip-name', storyGuide.step ? `${storyGuide.name} ${view.run?.id ?? ''}` : '');",
    expect: 'main_view_has_no_internal_identifiers: the main view shows' },
  'picker-skips-guard': { file: '/app.js', needle: "  $('workplace-board').value = slug;\n  await switchWorkplace();",
    replacement: "  state.slug = slug; state.generation += 1;\n  await refresh();",
    expect: 'picker_uses_switch_guard: a dirty draft did not block the picker start' },
  'picker-stays': { file: '/app.js', needle: "  if (userIntent) $('shift-picker').hidden = true;\n", replacement: '',
    expect: 'picker_uses_switch_guard: choosing a station leaves the picker over the room' },
  // S38 renderer recipe (Gate 3 sections 13.3 and 13.8).
  'recipe-env-compact': { file: '/workplace-scene.js', needle: "if(tier !== 'compact') { environment = buildStudioEnvironment(renderer);",
    replacement: 'if(true) { environment = buildStudioEnvironment(renderer);', expect: 'renderer_matches_tier_recipe: compact has an environment map' },
  'recipe-env-missing': { file: '/workplace-scene.js', needle: 'scene.environmentIntensity = .45;', replacement: 'scene.environmentIntensity = 1;',
    expect: 'renderer_matches_tier_recipe: standard lacks the PMREM environment' },
  'recipe-dpr-over-two': { file: '/workplace-scene.js', needle: 'return Math.min(requested,2,Math.sqrt(1850000/(width*height)));',
    replacement: 'return Math.min(requested,Math.sqrt(1850000/(width*height)));', expect: 'renderer_matches_tier_recipe: standard DPR above 2' },
  'recipe-backing-uncapped': { file: '/workplace-scene.js', needle: 'return Math.min(requested,2,Math.sqrt(1850000/(width*height)));',
    replacement: 'return Math.min(requested,2);', expect: 'renderer_matches_tier_recipe: the backing store exceeds 1,850,000 pixels' },
  'recipe-cap-too-low': { file: '/workplace-scene.js', needle: 'return Math.min(requested,2,Math.sqrt(1850000/(width*height)));',
    replacement: 'return Math.min(requested,2,Math.sqrt(1000000/(width*height)));', expect: 'renderer_matches_tier_recipe: the backing-store cap lowered DPR too far' },
  'recipe-compact-dpr': { file: '/workplace-scene.js', needle: "if(tier==='compact') return Math.min(requested,1);",
    replacement: "if(tier==='compact') return requested;", expect: 'renderer_matches_tier_recipe: compact DPR above 1' },
  'recipe-compact-low': { file: '/workplace-scene.js', needle: "if(tier==='compact') return Math.min(requested,1);",
    replacement: "if(tier==='compact') return Math.min(requested,.5);", expect: 'renderer_matches_tier_recipe: DPR 0.5 where 1 was expected' },
  'recipe-compact-shadow': { file: '/workplace-scene.js', needle: "renderer.shadowMap.enabled = tier !== 'compact';",
    replacement: 'renderer.shadowMap.enabled = true;', expect: 'renderer_matches_tier_recipe: compact draws shadow maps' },
  'recipe-texture': { file: '/workplace-scene.js', needle: 'renderer.setClearColor(room.fog);',
    replacement: 'renderer.setClearColor(room.fog); scene.background = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1); scene.background.needsUpdate = true;',
    expect: 'renderer_matches_tier_recipe: unexpected texture' },
  'recipe-orthographic': { file: '/workplace-scene.js', needle: 'const camera = new THREE.PerspectiveCamera(pose.fov,1,.1,100);',
    replacement: 'const camera = new THREE.OrthographicCamera(-8,8,6,-6,.1,100); camera.fov = pose.fov;', expect: 'renderer_matches_tier_recipe: camera is OrthographicCamera' },
  'recipe-fov': { file: '/workplace-scene.js', needle: 'const camera = new THREE.PerspectiveCamera(pose.fov,1,.1,100);',
    replacement: 'const camera = new THREE.PerspectiveCamera(45,1,.1,100);', expect: 'renderer_matches_tier_recipe: field of view is 45' },
  'recipe-tone': { file: '/workplace-scene.js', needle: 'renderer.toneMapping = THREE.ACESFilmicToneMapping;',
    replacement: 'renderer.toneMapping = THREE.NeutralToneMapping;', expect: 'renderer_matches_tier_recipe: tone mapping is' },
  'recipe-exposure': { file: '/workplace-scene.js', needle: 'renderer.toneMappingExposure = 1;', replacement: 'renderer.toneMappingExposure = 1.2;',
    expect: 'renderer_matches_tier_recipe: exposure is 1.2' },
  'recipe-fog': { file: '/workplace-scene.js', needle: 'scene.fog = new THREE.Fog(room.fog,1,2);', replacement: 'scene.fog = new THREE.FogExp2(room.fog,.01);',
    expect: 'renderer_matches_tier_recipe: fog is exp2' },
  'recipe-lights': { file: '/workplace-scene.js', needle: 'scene.add(fill,key); sceneLights.push(fill,key);', replacement: 'scene.add(key); sceneLights.push(key);',
    expect: 'renderer_matches_tier_recipe: lights are' },
  // S38 lamps (Gate 3 sections 13.3 and 13.5).
  'lamp-ignores-state': { file: '/workplace-scene.js',
    needle: '      for(const [stationId,lampMesh] of Object.entries(lampMeshes)) lampMesh.material = lampMaterials[next?.lamps?.find(lamp=>lamp.stationId===stationId)?.tone] ?? lampMaterials.idle;\n',
    replacement: '', expect: 'lamps_reflect_state_with_text: the customers room lamp disagrees with its attention tag' },
  'lamp-pass-colour': { file: '/workplace-scene.js', needle: "pass:'#4fd17a'", replacement: "pass:'#ffb648'",
    expect: 'lamps_reflect_state_with_text: the evaluator room lamp does not follow tone pass' },
  'lamp-tone-mapped': { file: '/workplace-scene.js', needle: 'new THREE.MeshBasicMaterial({color,toneMapped:false})', replacement: 'new THREE.MeshBasicMaterial({color})',
    expect: 'lamps_reflect_state_with_text: a lamp is lit or tone mapped' },
  'lamp-unshared': { file: '/workplace-scene.js', needle: 'lampMesh.material = lampMaterials[next?.lamps?.find(lamp=>lamp.stationId===stationId)?.tone] ?? lampMaterials.idle;',
    replacement: 'lampMesh.material = (lampMaterials[next?.lamps?.find(lamp=>lamp.stationId===stationId)?.tone] ?? lampMaterials.idle).clone();',
    expect: 'lamps_reflect_state_with_text: lamp materials are not shared per colour' },
  'lamp-missing': { file: '/workplace-rooms.js', needle: ' ledger: [5.3,2.75,-2.65],', replacement: '',
    expect: 'lamps_reflect_state_with_text: a station lamp is missing from the room' },
  'lamp-tag-tone': { file: '/app.js', needle: '    button.dataset.lamp = item.tone;', replacement: "    button.dataset.lamp = 'idle';",
    expect: 'lamps_reflect_state_with_text: the customers room lamp disagrees with its idle tag' },
  'lamp-no-text': { file: '/app.js', needle: "    button.querySelector('.lamp-text').textContent = item.text;", replacement: "    button.querySelector('.lamp-text').textContent = '';",
    expect: 'lamps_reflect_state_with_text: the customers tag has no lamp text' },
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

// Served controls follow fault patches. The S39 control inserts one conflicting
// publication before accepted terminal checks, without racing the preview server.
export const INSTRUMENT = [{ file: '/app.js', needle: 'function updateShiftReport(view) {',
  replacement: `function updateShiftReport(view) {
    if (globalThis.__s39ConflictArmed && view.run?.purpose === 'OPERATION' &&
        ['FINALIZED', 'FAILED'].includes(view.run.state) && view.slips?.runId === view.run.id) {
      globalThis.__s39ConflictArmed = false;
      globalThis.__s39ConflictInserted = (globalThis.__s39ConflictInserted ?? 0) + 1;
      updateShiftReport({ ...view, consistency: 'conflict' });
    }` }, { file: '/workplace-scene.js', needle: 'return { apply, resize,',
  replacement: `globalThis.__s38Scene = {
    recipe: () => ({ tier, camera: camera.type, fov: camera.fov, toneMapping: renderer.toneMapping === THREE.ACESFilmicToneMapping ? 'ACESFilmic' : String(renderer.toneMapping),
      exposure: renderer.toneMappingExposure, environment: scene.environment ? { width: scene.environment.image.width, height: scene.environment.image.height } : null,
      environmentIntensity: scene.environmentIntensity, fog: scene.fog?.isFog ? 'linear' : scene.fog?.isFogExp2 ? 'exp2' : null,
      pixelRatio: renderer.getPixelRatio(), backing: [renderer.domElement.width, renderer.domElement.height],
      shadows: renderer.shadowMap.enabled, shadowSizes: sceneLights.filter(light => light.castShadow).map(light => [light.shadow.mapSize.x, light.shadow.mapSize.y]),
      lights: sceneLights.map(light => light.type).sort(), textures: renderer.info.memory.textures }),
    lamps: () => Object.fromEntries(Object.entries(lampMeshes).map(([id, mesh]) => [id, { color: '#' + mesh.material.color.getHexString(),
      visible: mesh.visible, basic: mesh.material.isMeshBasicMaterial === true, toneMapped: mesh.material.toneMapped, material: mesh.material.uuid }])),
    applyLamps: lamps => { apply({ ...view, lamps }, []); } };
  return { apply, resize,` }];

export async function openBrowser(base, out, fault = '', { zoom = 1, webgl = true } = {}) {
  assert.ok(base.startsWith('http://127.0.0.1:'), 'Only owned local previews are allowed');
  assert.ok(/^\/(?:private\/)?tmp\/shiftwork-s(?:3[6789]|40|41|42|44)-[^/]+(?:\/|$)/.test(path.resolve(out)), 'Workplace receipts must use an owned disposable /tmp/shiftwork-sN-* root');
  const patch = fault ? FAULTS[fault] : null;
  if (fault) assert.ok(patch, `Unknown S36 fault ${fault}`);
  await mkdir(out, { recursive: true });
  const profile = await mkdtemp(path.join(out, 'profile-'));
  if (zoom !== 1) {
    await mkdir(path.join(profile, 'Default'));
    await writeFile(path.join(profile, 'Default/Preferences'), JSON.stringify({ partition: { default_zoom_level: { x: Math.log(zoom) / Math.log(1.2) } } }));
  }
  const child = spawn(chromePath, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0',
    '--window-size=1280,900', `--user-data-dir=${profile}`, ...(webgl ? [] : ['--disable-webgl']), 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
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
    const faulted = patch && url.pathname === patch.file, probes = INSTRUMENT.filter(item => item.file === url.pathname);
    if (!faulted && !probes.length) return send('Fetch.continueRequest', { requestId });
    const response = await fetch(request.url);
    let source = await response.text();
    if (faulted) {
      const count = source.split(patch.needle).length - 1;
      if (count !== 1) harness.push(`Fault ${fault} anchor matched ${count} times in ${patch.file}`);
      patched += 1;
      source = source.replace(patch.needle, () => patch.replacement);
    }
    for (const probe of probes) {
      const count = source.split(probe.needle).length - 1;
      if (count !== 1) harness.push(`Probe anchor matched ${count} times in ${probe.file}`);
      source = source.replace(probe.needle, () => probe.replacement);
    }
    const body = Buffer.from(source).toString('base64');
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
  return { send, evaluate, until, close, exceptions, commands, assertFaultServed, out };
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
  choose_dialog_has_no_default: 'dialogs', shift_report_matches_ledger: 'dialogs',
  dialog_keyboard: 'dialogs',
  next_action_navigates_only: 'story', main_view_shows_one_of_each: 'story', guide_never_credits_unsent_text: 'story', picker_uses_switch_guard: 'picker',
  run_help_matches_disabled_run: 'story', step_chip_announces_only_changes: 'story', status_bar_stays_one_row: 'inspector',
  renderer_matches_tier_recipe: 'recipe', lamps_reflect_state_with_text: 'lamps',
  resting_tags_show_next_and_one_failure: 'calm', one_narrator_bubble: 'calm', hidden_tags_stay_reachable: 'calm',
  fallback_tag_text_is_not_clipped: 'fallback', fallback_tags_do_not_overlap: 'fallback', fallback_tags_clear_of_panels: 'fallback' };

// S37 review F4: the static room a browser without WebGL gets, at the required 1280x720 cell.
// Clipped text is checked first, then tag pairs, then panels, so each fault fails its own assertion.
export async function fallbackKeepsTagsReadable(browser, base, slug) {
  await load(browser, base, slug, 1280, 720);
  assert.equal(await browser.evaluate(() => document.getElementById('graphics-status').dataset.state), 'unavailable', `${slug} did not fall back to the static room`);
  await browser.evaluate(() => document.getElementById('close-inspector')?.click());
  await settle(browser);
  const seen = await browser.evaluate(() => {
    const visible = node => node && !node.closest('[hidden]') && node.getClientRects().length > 0;
    const hit = (a, b) => a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
    const tags = [...document.querySelectorAll('.room-hotspots:not([hidden]) [data-station]')].filter(visible)
      .map(node => ({ station: node.dataset.station, node, rect: node.getBoundingClientRect() }));
    const clipped = tags.flatMap(({ station, node }) => [node, ...node.querySelectorAll('*')].filter(visible)
      .filter(part => part.scrollWidth > part.clientWidth + 1 || part.scrollHeight > part.clientHeight + 1).map(part => `${station}: ${part.textContent.trim()}`));
    const pairs = tags.flatMap((a, i) => tags.slice(i + 1).filter(b => hit(a.rect, b.rect)).map(b => `${a.station}/${b.station}`));
    const panels = [document.getElementById('status-bar'), document.getElementById('step-chip'), document.getElementById('next-action'), document.getElementById('shift-log'),
      document.querySelector('.graphics-controls'), document.getElementById('customer-bubble'), document.getElementById('owner-bubble')].filter(visible);
    const covered = panels.flatMap(panel => tags.filter(tag => hit(panel.getBoundingClientRect(), tag.rect)).map(tag => `${panel.id || panel.className}/${tag.station}`));
    return { tags: tags.length, clipped, pairs, covered };
  });
  assert.ok(seen.tags >= 4, `${slug} static room shows only ${seen.tags} station tags`);
  assert.deepEqual(seen.clipped, [], `fallback_tag_text_is_not_clipped: ${slug} clips ${seen.clipped.join('; ')}`);
  assert.deepEqual(seen.pairs, [], `fallback_tags_do_not_overlap: ${slug} tags overlap ${seen.pairs.join(', ')}`);
  assert.deepEqual(seen.covered, [], `fallback_tags_clear_of_panels: ${slug} panels cover ${seen.covered.join(', ')}`);
  return { slug, fallback: { tags: seen.tags } };
}

// Tag rectangles, the inspector and the anchor x positions in viewport pixels.
const measureTags = browser => browser.evaluate(() => {
  const panel = document.getElementById('station-panel').getBoundingClientRect();
  return { panel: { left: panel.left, right: panel.right, top: panel.top, bottom: panel.bottom }, width: innerWidth, height: innerHeight,
    tags: [...document.querySelectorAll('.room-hotspots:not([hidden]) [data-station]')].map(button => {
      const r = button.getBoundingClientRect();
      return { station: button.dataset.station, left: r.left, right: r.right, top: r.top, bottom: r.bottom, anchored: button.dataset.anchored === 'true',
        anchorX: Number(button.dataset.anchorX) + document.querySelector('.room').getBoundingClientRect().left };
    }) };
});
// Gate 3 section 13.6 (backtracked 2026-10-22): no tag covers another tag from 761px to 1280px.
function assertTagsApart(layout, cell) {
  const covered = layout.tags.flatMap((a, i) => layout.tags.slice(i + 1)
    .filter(b => a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top).map(b => `${a.station}/${b.station}`));
  assert.deepEqual(covered, [], `inspector_keeps_stations_readable: a station tag covers another station tag at ${cell}`);
}

// 1280x720 and 1024x720, each with the inspector closed and then open
// (Gate 3 section 13.9, backtracked 2026-10-22). The room is centred in the
// uncovered stage at 1280x720 only.
export async function inspectorKeepsStationsReadable(browser, base, slug) {
  const cells = [];
  for (const [width, height] of [[1280, 720], [1024, 720]]) {
    await load(browser, base, slug, width, height);
    if (width === 1280) {
      // status_bar_stays_one_row (S37 review F5): at 1280px every board's status bar, Change shift included, is one row.
      const bar = await browser.evaluate(() => { const bar = document.getElementById('status-bar').getBoundingClientRect(), change = document.getElementById('change-shift').getBoundingClientRect();
        return { height: Math.round(bar.height), changeTop: Math.round(change.top - bar.top) }; });
      assert.ok(bar.height <= 80 && bar.changeTop <= 24, `status_bar_stays_one_row: ${slug} status bar is ${bar.height}px tall with Change shift ${bar.changeTop}px down`);
    }
    assert.equal(await browser.evaluate(() => document.querySelector('.room').dataset.graphics), 'ready', `${slug} 3D room is not ready`);
    assert.equal(await browser.evaluate(() => document.getElementById('workplace-world').dataset.inspector), 'closed', `${slug} inspector is not closed after load`);
    const closed = await measureTags(browser);
    assert.ok(closed.tags.length >= 4 && closed.tags.every(tag => tag.anchored), `${slug} tags are not placed at projected anchors (${width}x${height} closed)`);
    assertTagsApart(closed, `${width}x${height} closed`);
    await browser.evaluate(station => document.querySelector(`.room-hotspots:not([hidden]) [data-station="${station}"]`).click(), FIRST_STATION[slug]);
    assert.ok(await browser.until(() => document.getElementById('workplace-world').dataset.inspector === 'open'), `${slug} inspector did not open`);
    await settle(browser);
    const layout = await measureTags(browser), cell = `${width}x${height} open`;
    assert.ok(layout.panel.right > layout.panel.left, `${slug} inspector has no area`);
    const outside = layout.tags.filter(tag => tag.left < 0 || tag.top < 0 || tag.right > layout.width || tag.bottom > layout.height);
    assert.deepEqual(outside, [], 'inspector_keeps_stations_readable: a station tag is outside the viewport');
    const under = layout.tags.filter(tag => tag.left < layout.panel.right && tag.right > layout.panel.left && tag.top < layout.panel.bottom && tag.bottom > layout.panel.top);
    assert.deepEqual(under, [], 'inspector_keeps_stations_readable: a station tag is under the inspector');
    assert.ok(layout.tags.length >= 4 && layout.tags.every(tag => tag.anchored), `${slug} tags are not placed at projected anchors (${cell})`);
    // The view offset centres the room in the stage the inspector leaves uncovered:
    // the anchors' mean sits within 10% of that area's centre.
    const uncovered = { left: layout.panel.right, right: layout.width };
    const centre = (uncovered.left + uncovered.right) / 2, mean = layout.tags.reduce((sum, tag) => sum + tag.anchorX, 0) / layout.tags.length;
    if (width === 1280) assert.ok(Math.abs(mean - centre) <= (uncovered.right - uncovered.left) * .1,
      `inspector_keeps_stations_readable: the room is not centred in the uncovered stage (anchor mean ${Math.round(mean)}, centre ${Math.round(centre)})`);
    assertTagsApart(layout, cell);
    cells.push({ cell: `${width}x${height}`, inspector: layout.panel, tags: layout.tags.length, anchorMean: Math.round(mean), uncoveredCentre: Math.round(centre) });
  }
  return { slug, cells };
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
export async function storyJourney(browser, base, { beforeChoose, beforeRun, afterRun } = {}) {
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

  // run_help_matches_disabled_run (S37 review F3): a shift whose operation is recorded says so, not "Runs the selected version".
  const RECORDED_HELP = "This shift's operation run is recorded. Close the shift at Next shift; the operating version runs in the next shift.";
  const NO_ATTEMPT_HELP = 'No attempt remains in this shift, so the controller will not accept another run. Close the shift at Next shift to continue.';
  const runHelp = async (label, help = RECORDED_HELP) => {
    const seen = await browser.evaluate(() => ({ disabled: document.getElementById('run-shift').disabled, help: document.getElementById('run-help').textContent }));
    assert.deepEqual(seen, { disabled: true, help }, `run_help_matches_disabled_run: ${label} reads ${JSON.stringify(seen)}`);
  };
  await expectStep(STORY_STEPS[0], 'fresh shift');
  await runHelp('fresh shift');
  await act(() => document.querySelector('#bookshop-stations [data-station="investigate"]').click());
  await expectStep(STORY_STEPS[1], 'investigating');
  // guide_never_credits_unsent_text: a cause draft moves only the chip.
  const controls = () => ({ count: document.querySelectorAll('#investigation-list [data-investigation-id]').length,
    tag: document.getElementById('investigation-tag').textContent,
    disabled: [...document.querySelectorAll('button, input, select, textarea')].filter(node => node.id !== 'cause-input').map(node => `${node.id || node.dataset.station || node.textContent.trim().slice(0, 24)}:${node.disabled}`) });
  const clean = await act(controls);
  // step_chip_announces_only_changes (S37 review F6): ten keystrokes move the chip from step 2 to 3 once,
  // which rewrites its count and name; every other keystroke leaves the live region untouched.
  const chipWrites = await act(async () => {
    const records = [];
    const observer = new MutationObserver(list => records.push(...list));
    observer.observe(document.getElementById('step-chip'), { childList: true, subtree: true, characterData: true });
    const input = document.getElementById('cause-input');
    for (const ch of 'abcdefghij') { input.value += ch; input.dispatchEvent(new Event('input')); await new Promise(r => setTimeout(r, 50)); }
    await new Promise(r => setTimeout(r, 200));
    observer.disconnect();
    input.value = ''; input.dispatchEvent(new Event('input'));
    return records.length;
  });
  assert.ok(chipWrites <= 2, `step_chip_announces_only_changes: typing ten characters wrote the step chip ${chipWrites} times`);
  await expectStep(STORY_STEPS[1], 'investigating after clearing a draft');
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
  if (beforeChoose) await beforeChoose();
  await act(() => document.getElementById('open-choose-a').click());
  await act(() => { const node = document.getElementById('selection-rationale'); node.value = 'A answered the required tasks in the shared trial.'; node.dispatchEvent(new Event('input')); });
  await wait('candidate A to be selectable', () => !document.getElementById('select-candidate-a').disabled);
  await act(() => document.getElementById('select-candidate-a').click());
  await expectStep(STORY_STEPS[5], 'learner choice');
  // The loaded run is now the comparison's last trial, so the client sees only the board's zero remaining attempts.
  await runHelp('learner choice in a shift that already ran', NO_ATTEMPT_HELP);
  // The demo's first shift already ran the starter, so a new choice operates in the
  // next shift: close (step 7 at Next shift), open shift 2 (step 6, rule 3a re-approved
  // 2026-10-22), then run (step 7).
  await act(() => { document.querySelector('[data-view="next"]').click(); document.getElementById('close-shift').click(); });
  await expectStep(STORY_STEPS[7], 'closed shift');
  await wait('the next shift to be openable', () => !document.getElementById('open-next-shift').disabled);
  await act(() => document.getElementById('open-next-shift').click());
  await expectStep(STORY_STEPS[5], 'next shift with the inherited choice');
  await act(() => document.querySelector('#bookshop-stations [data-station="service"]').click());
  await wait('the run to be allowed', () => !document.getElementById('run-shift').disabled);
  if (beforeRun) await beforeRun();
  await act(() => document.getElementById('run-shift').click());
  await expectStep(STORY_STEPS[6], 'operation finished');
  if (afterRun) await afterRun();
  return { slug: 'bookshop', steps: results };
}

export async function dialogJourney(browser, base) {
  await load(browser, base, 'bookshop', 1280, 720);
  assert.equal(await browser.evaluate(() => document.querySelectorAll('dialog#choose-dialog, dialog#shift-report').length), 2,
    'choose_dialog_has_no_default: both native dialogs must exist');
  const key = async (key, modifiers = 0) => {
    const code = { Tab: 9, Escape: 27 }[key];
    await browser.send('Input.dispatchKeyEvent', { type: 'keyDown', key, code: key, windowsVirtualKeyCode: code, modifiers });
    await browser.send('Input.dispatchKeyEvent', { type: 'keyUp', key, code: key, windowsVirtualKeyCode: code, modifiers });
  };
  const trap = async id => {
    const tabs = await browser.evaluate(id => [...document.getElementById(id).querySelectorAll('button,textarea')]
      .filter(node => !node.disabled && !node.hidden && node.getClientRects().length).map(node => node.id), id);
    for (const reverse of [false, true]) {
      await browser.evaluate((id, reverse) => { const nodes = [...document.getElementById(id).querySelectorAll('button,textarea')]
        .filter(node => !node.disabled && !node.hidden && node.getClientRects().length); nodes[reverse ? 0 : nodes.length - 1].focus(); }, id, reverse);
      await key('Tab', reverse ? 8 : 0);
      assert.equal(await browser.evaluate(() => document.activeElement.id), tabs[reverse ? tabs.length - 1 : 0], `dialog_keyboard: ${id} did not trap ${reverse ? 'reverse ' : ''}Tab`);
    }
  };
  const geometry = async id => {
    const r = await browser.evaluate(id => { const d = document.getElementById(id), r = d.getBoundingClientRect();
      return { x: r.x, y: r.y, right: r.right, bottom: r.bottom, width: r.width, viewport: [innerWidth, innerHeight],
        overflow: d.scrollWidth > d.clientWidth + 1, scrim: getComputedStyle(d, '::backdrop').backgroundColor,
        small: [...d.querySelectorAll('button')].filter(n => !n.hidden && !n.disabled && n.getClientRects().length).some(n => n.offsetWidth < 44 || n.offsetHeight < 44) }; }, id);
    assert.ok(r.x >= 0 && r.y >= 0 && r.right <= r.viewport[0] + 1 && r.bottom <= r.viewport[1] + 1 && r.width <= 520 && !r.overflow && !r.small,
      `dialog_keyboard: ${id} is clipped or has a small target: ${JSON.stringify(r)}`);
    assert.equal(r.scrim, 'rgba(11, 18, 39, 0.55)', `dialog_keyboard: ${id} scrim`);
    return r;
  };
  const receipts = [];
  let imageNumber = 0;
  const screenshot = async id => {
    await browser.evaluate(id => { document.getElementById(id).scrollTop = 0; }, id);
    const { data } = await browser.send('Page.captureScreenshot', { format: 'png' });
    await writeFile(path.join(browser.out, `${id}-${imageNumber++}.png`), Buffer.from(data, 'base64'));
  };
  const workbench = () => ({ inspector: document.getElementById('workplace-world').dataset.inspector,
    station: document.querySelector('[data-station][aria-pressed="true"]')?.dataset.station,
    selection: document.getElementById('selection-note').textContent, ledger: document.getElementById('event-detail').textContent });
  // Leave the controller untouched. This response-boundary control removes checks
  // from a loaded run, so the rendered report must expose the missing causal link.
  const noChecks = await browser.send('Page.addScriptToEvaluateOnNewDocument', { source: `const originalFetch = window.fetch; window.fetch = async (...args) => { const response = await originalFetch(...args); return String(args[0]).endsWith('/checks') ? new Response('[]', {status:200,headers:{'content-type':'application/json'}}) : response; };` });
  await load(browser, base, 'bookshop', 1280, 720);
  await browser.evaluate(() => document.querySelector('#incident-list button').click());
  assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready' && document.getElementById('inspection-bar').dataset.mode === 'history'), 'shift_report_matches_ledger: missing-link historical record did not load');
  await browser.evaluate(() => { const b = document.getElementById('open-shift-report'); b.focus(); b.click(); });
  assert.ok(await browser.until(() => document.getElementById('shift-report').open), 'shift_report_matches_ledger: manual report did not open');
  assert.equal(await browser.evaluate(() => { const rows = [...document.querySelectorAll('#report-counts dt')]; return rows.find(n => n.textContent === 'Incidents opened by this run').nextElementSibling.textContent; }),
    'unknown', 'shift_report_matches_ledger: missing link must display unknown');
  await browser.send('Page.removeScriptToEvaluateOnNewDocument', { identifier: noChecks.identifier });
  await load(browser, base, 'bookshop', 1280, 720);
  const checkReport = async fresh => {
    const before = browser.commands.length;
    const unchanged = await browser.evaluate(workbench);
    if (!fresh) await browser.evaluate(() => { const b = document.getElementById('open-shift-report'); b.focus(); b.click(); });
    assert.ok(await browser.until(() => document.getElementById('shift-report').open), 'shift_report_matches_ledger: operation did not open its report');
    assert.equal(await browser.evaluate(() => document.getElementById('report-freshness').textContent), fresh ? 'New operation report' : 'Recorded history', 'shift_report_matches_ledger: freshness');
    assert.equal(await browser.evaluate(() => document.getElementById('report-synthetic').textContent), 'Synthetic scenario: not real customers or revenue', 'shift_report_matches_ledger: synthetic line');
    await trap('shift-report');
    receipts.push({ report: await geometry('shift-report') });
    await screenshot('shift-report');
    await key('Escape');
    assert.deepEqual(await browser.evaluate(workbench), unchanged, 'dialog_keyboard: Escape changed the workbench');
    assert.ok(await browser.until(() => !document.getElementById('shift-report').open), 'dialog_keyboard: Escape did not close report');
    assert.ok(await browser.until(() => document.activeElement.id === 'open-shift-report', 3000), 'dialog_keyboard: report focus did not return');
    assert.equal(browser.commands.length, before, 'shift_report_matches_ledger: closing report sent a request');
  };
  await checkReport(false);
  const result = await storyJourney(browser, base, { beforeChoose: async () => {
    const beforeRapid = browser.commands.length;
    await browser.evaluate(() => {
      document.getElementById('open-choose-a').click();
      globalThis.__s39RapidClosed = false;
      document.getElementById('choose-dialog').addEventListener('close', () => { globalThis.__s39RapidClosed = true; }, { once: true });
      document.getElementById('choose-dialog').close();
      document.getElementById('open-choose-b').click();
      const input = document.getElementById('selection-rationale'); input.value = 'A new reason after reopening'; input.dispatchEvent(new Event('input'));
    });
    assert.ok(await browser.until(() => globalThis.__s39RapidClosed), 'choose_dialog_has_no_default: rapid close event did not arrive');
    assert.deepEqual(await browser.evaluate(() => { const b = document.getElementById('select-candidate-b'); return { open: document.getElementById('choose-dialog').open, hidden: b.hidden, disabled: b.disabled, shown: b.getClientRects().length > 0 }; }),
      { open: true, hidden: false, disabled: false, shown: true }, 'choose_dialog_has_no_default: stale close hid the reopened confirmation');
    await browser.evaluate(() => { globalThis.__s39RapidClosed = false; const d = document.getElementById('choose-dialog'); d.addEventListener('close', () => { globalThis.__s39RapidClosed = true; }, { once: true }); d.close(); });
    assert.ok(await browser.until(() => globalThis.__s39RapidClosed && !document.getElementById('choose-dialog').open), 'choose_dialog_has_no_default: rapid reopened dialog did not close');
    assert.equal(browser.commands.length, beforeRapid, 'choose_dialog_has_no_default: rapid cancellation sent a request');
    for (const [width, height] of [[1280,720], [640,900], [390,844]]) {
      await browser.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
      for (const label of ['a', 'b']) {
        const before = browser.commands.length;
        await browser.evaluate(label => { const b = document.getElementById(`open-choose-${label}`); b.focus(); b.click(); }, label);
        assert.equal(await browser.evaluate(() => document.activeElement.id), 'selection-rationale', 'choose_dialog_has_no_default: rationale must receive focus');
        const read = await browser.evaluate(() => ({ title: document.getElementById('choose-title').textContent,
          checked: document.querySelectorAll('#choose-dialog input:checked, #choose-dialog [aria-selected="true"]').length,
          empty: document.getElementById('selection-rationale').value,
          blocked: [...document.querySelectorAll('#choose-dialog [id^="select-candidate-"]')].every(b => b.disabled),
          why: document.getElementById('choose-why').textContent, backup: document.getElementById('choose-backup').textContent }));
        assert.equal(read.checked, 0, 'choose_dialog_has_no_default: an option is preselected');
        assert.ok(read.blocked && read.empty === '', 'choose_dialog_has_no_default: empty rationale is not guarded');
        assert.match(read.title, /^Make ver-\d+ the live version\?$/, 'choose_dialog_has_no_default: exact version missing');
        assert.equal(read.why, 'Why we ask: only the version you choose goes live');
        assert.equal(read.backup, 'The other version stays as your backup');
        await browser.evaluate(() => { const f = document.getElementById('selection-rationale'); f.value = 'A reason that is cancelled'; f.dispatchEvent(new Event('input')); });
        assert.deepEqual(await browser.evaluate(label => { const b = document.getElementById(`select-candidate-${label}`); return { hidden: b.hidden, disabled: b.disabled, shown: b.getClientRects().length > 0 }; }, label),
          { hidden: false, disabled: false, shown: true }, 'choose_dialog_has_no_default: a reason must enable a visible confirmation');
        await trap('choose-dialog');
        receipts.push({ choose: await geometry('choose-dialog') });
        await screenshot('choose-dialog');
        await browser.evaluate(() => document.getElementById('cancel-choose').click());
        await sleep(100);
        assert.equal(browser.commands.length, before, 'choose_dialog_has_no_default: Cancel sent a request');
        assert.equal(await browser.evaluate(() => document.activeElement.id), `open-choose-${label}`, 'dialog_keyboard: choose focus did not return');
        await browser.evaluate(label => document.getElementById(`open-choose-${label}`).click(), label);
        await browser.evaluate(() => { globalThis.__s39ChooseClosed = false; document.getElementById('choose-dialog').addEventListener('close', () => { globalThis.__s39ChooseClosed = true; }, { once: true }); });
        await key('Escape');
        assert.equal(browser.commands.length, before, 'choose_dialog_has_no_default: Escape sent a request');
        assert.equal(await browser.evaluate(() => document.getElementById('choose-dialog').open), false, 'choose_dialog_has_no_default: Escape did not close');
        assert.ok(await browser.until(label => globalThis.__s39ChooseClosed && document.activeElement.id === `open-choose-${label}`, 3000, label), 'dialog_keyboard: Escape did not return choose focus');
      }
      await checkReport(false);
    }
    await browser.send('Emulation.setDeviceMetricsOverride', { width:1280, height:720, deviceScaleFactor:1, mobile:false });
  }, beforeRun: async () => {
    await browser.evaluate(() => document.querySelector('#incident-list button').click());
    assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready' && document.getElementById('inspection-bar').dataset.mode === 'history'), 'shift_report_matches_ledger: prior-shift inspection did not load');
    await checkReport(false);
    assert.equal(await browser.evaluate(() => document.getElementById('report-title').textContent), 'Recorded operation report', 'shift_report_matches_ledger: a historical run was labelled as the current shift');
    await browser.evaluate(() => document.getElementById('inspect-current').click());
    assert.ok(await browser.until(() => document.body.dataset.loadState === 'ready' && document.getElementById('inspection-bar').dataset.mode === 'current'), 'shift_report_matches_ledger: current inspection did not return');
    await browser.evaluate(() => { globalThis.__s39ConflictArmed = true; });
  }, afterRun: async () => {
    assert.equal(await browser.evaluate(() => globalThis.__s39ConflictInserted), 1, 'shift_report_matches_ledger: conflicting publication control did not run exactly once');
    await checkReport(true);
    await sleep(1200);
    assert.equal(await browser.evaluate(() => document.getElementById('shift-report').open), false, 'shift_report_matches_ledger: duplicate publication reopened the report');
    await browser.evaluate(() => document.getElementById('refresh').click());
    await browser.until(() => document.body.dataset.loadState === 'ready');
    assert.equal(await browser.evaluate(() => document.getElementById('shift-report').open), false, 'shift_report_matches_ledger: manual refresh opened a fresh report');
    await checkReport(false);
  } });
  return { ...result, dialogs: receipts };
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

// renderer_matches_tier_recipe (Gate 3 section 13.8 and 13.9). The cells test each
// cap: a small 780x600 standard stage at DPR 3 must stop at 2; 1280x720 and 1920x1080
// at DPR 2 must lower DPR so the backing store stays within 1,850,000 pixels (13.8 as
// backtracked 2026-10-22); a 390px phone at DPR 3 must draw at 1.
const RECIPE_CELLS = [{ width: 780, height: 600, dpr: 3, tier: 'standard', ratio: 2 }, { width: 1280, height: 720, dpr: 2, tier: 'standard' },
  { width: 1920, height: 1080, dpr: 2, tier: 'standard' },
  { width: 390, height: 844, dpr: 3, tier: 'compact', ratio: 1 }];
export async function rendererMatchesTierRecipe(browser, base, slug) {
  const receipts = [];
  for (const cell of RECIPE_CELLS) {
    await browser.send('Emulation.setDeviceMetricsOverride', { width: cell.width, height: cell.height, deviceScaleFactor: cell.dpr, mobile: cell.width < 761 });
    await browser.send('Page.navigate', { url: `${base}/?board=${slug}` });
    assert.ok(await browser.until(() => ['ready', 'empty'].includes(document.body?.dataset.loadState), 60000), `${slug} did not load at ${cell.width}px`);
    await browser.evaluate(() => document.getElementById('workplace-canvas').scrollIntoView({ block: 'center', behavior: 'instant' }));
    assert.ok(await browser.until(() => document.getElementById('graphics-status')?.dataset.state === 'ready' && globalThis.__s38Scene, 60000), `${slug} graphics not ready at ${cell.width}px`);
    await settle(browser);
    const r = await browser.evaluate(() => globalThis.__s38Scene.recipe());
    const at = `${slug} ${cell.width}x${cell.height} DPR ${cell.dpr}`;
    receipts.push({ cell: at, ...r });
    assert.equal(r.tier, cell.tier, `${at} mounted the ${r.tier} tier`);
    if (cell.tier === 'compact') {
      assert.equal(r.environment, null, `renderer_matches_tier_recipe: compact has an environment map (${at})`);
      assert.ok(r.pixelRatio <= 1, `renderer_matches_tier_recipe: compact DPR above 1 (${at}: ${r.pixelRatio})`);
      assert.equal(r.shadows, false, `renderer_matches_tier_recipe: compact draws shadow maps (${at})`);
      assert.equal(r.textures, 0, `renderer_matches_tier_recipe: unexpected texture (${at}: ${r.textures})`);
    } else {
      assert.ok(r.environment && r.environment.width > 0 && Math.abs(r.environmentIntensity - .45) < 1e-9, `renderer_matches_tier_recipe: standard lacks the PMREM environment (${at})`);
      assert.ok(r.pixelRatio <= 2, `renderer_matches_tier_recipe: standard DPR above 2 (${at}: ${r.pixelRatio})`);
      assert.ok(r.backing[0] * r.backing[1] <= 1850000, `renderer_matches_tier_recipe: the backing store exceeds 1,850,000 pixels (${at}: ${r.backing.join('x')})`);
      assert.ok(r.shadows && r.shadowSizes.length === 1 && r.shadowSizes[0].join('x') === '1024x1024', `renderer_matches_tier_recipe: standard shadow is not one 1024 map (${at})`);
      // The PMREM target and the shadow map; no authored texture.
      assert.equal(r.textures, 2, `renderer_matches_tier_recipe: unexpected texture (${at}: ${r.textures})`);
    }
    // A DPR lowered below the device's (at most 2) must still use most of the 1,850,000-pixel allowance.
    if (cell.tier === 'standard' && r.pixelRatio < Math.min(cell.dpr, 2)) assert.ok(r.backing[0] * r.backing[1] > 1650000, `renderer_matches_tier_recipe: the backing-store cap lowered DPR too far (${at}: ${r.pixelRatio})`);
    if (cell.ratio) assert.equal(r.pixelRatio, cell.ratio, `renderer_matches_tier_recipe: DPR ${r.pixelRatio} where ${cell.ratio} was expected (${at})`);
    assert.equal(r.camera, 'PerspectiveCamera', `renderer_matches_tier_recipe: camera is ${r.camera} (${at})`);
    assert.equal(r.fov, 30, `renderer_matches_tier_recipe: field of view is ${r.fov} (${at})`);
    assert.equal(r.toneMapping, 'ACESFilmic', `renderer_matches_tier_recipe: tone mapping is ${r.toneMapping} (${at})`);
    assert.equal(r.exposure, 1, `renderer_matches_tier_recipe: exposure is ${r.exposure} (${at})`);
    assert.equal(r.fog, 'linear', `renderer_matches_tier_recipe: fog is ${r.fog} (${at})`);
    assert.deepEqual(r.lights, ['DirectionalLight', 'HemisphereLight'], `renderer_matches_tier_recipe: lights are ${r.lights} (${at})`);
  }
  return { check: 'renderer_matches_tier_recipe', slug, receipts };
}

// lamps_reflect_state_with_text (Gate 3 section 13.5 lamp table, visual-spec 11.3). Literal
// spec colours; unknown uses the idle grey, as the tag dot does.
const LAMP_COLOURS = { fail: '#ff5a4e', attention: '#ffb648', pass: '#4fd17a', idle: '#9aa6b2', unknown: '#9aa6b2' };
const BELLWETHER_LAMPS = ['customers', 'service', 'evaluator', 'investigate', 'compare', 'ledger', 'owner', 'repair', 'next'];
export async function lampsReflectStateWithText(browser, base) {
  await load(browser, base, 'bookshop', 1280, 720);
  assert.ok(await browser.until(() => Boolean(globalThis.__s38Scene)), 'Scene probe unavailable');
  const shown = await browser.evaluate(() => ({ scene: globalThis.__s38Scene.lamps(),
    tags: Object.fromEntries([...document.querySelectorAll('#bookshop-stations [data-station][data-lamp]')].map(button =>
      [button.dataset.station, { tone: button.dataset.lamp, text: button.querySelector('.lamp-text')?.textContent.trim() ?? '' }])) }));
  for (const [station, tag] of Object.entries(shown.tags)) assert.ok(tag.text.length > 0, `lamps_reflect_state_with_text: the ${station} tag has no lamp text`);
  assert.deepEqual(Object.keys(shown.scene).sort(), [...BELLWETHER_LAMPS].sort(), 'lamps_reflect_state_with_text: a station lamp is missing from the room');
  for (const station of BELLWETHER_LAMPS) {
    const lamp = shown.scene[station], tag = shown.tags[station];
    assert.ok(tag, `lamps_reflect_state_with_text: the ${station} tag carries no lamp`);
    assert.equal(lamp.color, LAMP_COLOURS[tag.tone], `lamps_reflect_state_with_text: the ${station} room lamp disagrees with its ${tag.tone} tag`);
  }
  const lampMaterials = Object.values(shown.scene);
  assert.ok(lampMaterials.every(lamp => lamp.basic && lamp.toneMapped === false), 'lamps_reflect_state_with_text: a lamp is lit or tone mapped');
  assert.ok(new Set(lampMaterials.map(lamp => lamp.material)).size <= new Set(lampMaterials.map(lamp => lamp.color)).size, 'lamps_reflect_state_with_text: lamp materials are not shared per colour');
  // Every tone, applied to every station in turn, lands in the room as its literal colour.
  const tones = Object.keys(LAMP_COLOURS);
  for (let shift = 0; shift < tones.length; shift++) {
    const lamps = BELLWETHER_LAMPS.map((stationId, index) => ({ stationId, tone: tones[(index + shift) % tones.length], text: 'probe' }));
    const scene = await browser.evaluate(lamps => { globalThis.__s38Scene.applyLamps(lamps); return globalThis.__s38Scene.lamps(); }, lamps);
    for (const lamp of lamps) assert.equal(scene[lamp.stationId].color, LAMP_COLOURS[lamp.tone], `lamps_reflect_state_with_text: the ${lamp.stationId} room lamp does not follow tone ${lamp.tone}`);
  }
  return { check: 'lamps_reflect_state_with_text', tags: shown.tags };
}

// S41: at rest over the drawn Bellwether room, the next-action station (spoken for by
// the bubble) and at most one failing station show; every other tag stays a focusable
// button that becomes visible on keyboard focus. Counting runs first, then the bubble,
// then reachability, so each fault fails its own assertion.
export async function calmRoom(browser, base) {
  await load(browser, base, 'bookshop', 1280, 720);
  const shown = () => browser.evaluate(() => new Promise(resolve => setTimeout(() => {
    const seen = node => { const r = node.getBoundingClientRect(); return !node.closest('[hidden]') && Number(getComputedStyle(node).opacity) > .5
      && r.width > 0 && r.right > 0 && r.bottom > 0 && r.left < innerWidth && r.top < innerHeight; };
    resolve({ tags: [...document.querySelectorAll('#bookshop-stations [data-station]')].filter(seen).map(node => node.dataset.station),
      bubbles: [...document.querySelectorAll('.bubble')].filter(seen).map(node => node.id),
      stations: [...document.querySelectorAll('#bookshop-stations [data-station]')].map(node => node.dataset.station),
      step: document.getElementById('step-chip-count').textContent });
  }, 400)));
  const rest = await shown();
  assert.ok(rest.tags.length <= 2, `resting_tags_show_next_and_one_failure: rest-visible tags ${rest.tags.join(', ')}`);
  assert.deepEqual(rest.bubbles, ['customer-bubble'], `one_narrator_bubble: bubbles shown ${rest.bubbles.join(', ')}`);
  assert.ok(!rest.tags.includes('customers'), 'one_narrator_bubble: speaker tag beside its bubble');
  assert.deepEqual(rest.tags, ['ledger'], 'resting_tags_show_next_and_one_failure: the failing ledger rests visible');
  const reach = [];
  for (const station of rest.stations.filter(id => !rest.tags.includes(id))) {
    const got = await browser.evaluate(station => new Promise(resolve => {
      const node = document.querySelector(`#bookshop-stations [data-station="${station}"]`);
      node.focus({ focusVisible: true, preventScroll: true });
      setTimeout(() => resolve({ focused: document.activeElement === node, opacity: getComputedStyle(node).opacity,
        name: node.textContent.trim(), tab: node.tabIndex }), 300);
    }), station);
    assert.ok(got.focused && got.tab >= 0, `hidden_tags_stay_reachable: a hidden tag cannot take focus (${station})`);
    assert.ok(got.name.length > 0, `hidden_tags_stay_reachable: ${station} lost its name`);
    assert.equal(got.opacity, '1', `hidden_tags_stay_reachable: a focused tag stays hidden (${station})`);
    reach.push(station);
  }
  await browser.evaluate(() => document.activeElement?.blur());
  // An open station shows its tag beside the inspector; the speaking station stays named by its bubble.
  const opened = {};
  for (const station of ['compare', 'customers']) {
    opened[station] = await browser.evaluate(station => new Promise(resolve => {
      document.querySelector(`#bookshop-stations [data-station="${station}"]`).click(); document.activeElement?.blur();
      setTimeout(() => resolve({ inspector: document.getElementById('workplace-world').dataset.inspector,
        opacity: getComputedStyle(document.querySelector(`#bookshop-stations [data-station="${station}"]`)).opacity }), 400);
    }), station);
  }
  assert.equal(opened.compare.inspector, 'open', 'resting_tags_show_next_and_one_failure: compare did not open');
  assert.equal(opened.compare.opacity, '1', 'resting_tags_show_next_and_one_failure: the open station hides its tag');
  assert.equal(opened.customers.opacity, '0', 'one_narrator_bubble: speaker tag beside its bubble while open');
  return { check: 'calm_room', rest, reach, opened };
}

export async function runAll(base, out, slug, fault = '', only = '', dialogZoom = 1) {
  const results = [];
  const run = async (name, zoom, fn, options = {}) => {
    if (only && only !== name) return;
    const browser = await openBrowser(base, path.join(out, `${name}-${zoom}x`), fault, { zoom, ...options });
    try {
      results.push(await fn(browser));
      assert.deepEqual(browser.exceptions, [], 'Uncaught client exceptions');
      browser.assertFaultServed();
    } catch (error) { browser.assertFaultServed(); throw error; }
    finally { await browser.close(); }
  };
  await run('inspector', 1, browser => inspectorKeepsStationsReadable(browser, base, slug));
  await run('identifiers', 1, browser => mainViewHasNoInternalIdentifiers(browser, base, slug));
  await run('fallback', 1, browser => fallbackKeepsTagsReadable(browser, base, slug), { webgl: false });
  await run('recipe', 1, browser => rendererMatchesTierRecipe(browser, base, slug));
  if (slug === 'bookshop') await run('lamps', 1, browser => lampsReflectStateWithText(browser, base));
  if (slug === 'bookshop') await run('calm', 1, browser => calmRoom(browser, base));
  for (const zoom of [1, 2]) await run('narrow', zoom, async browser => [
    // 1280x720 at 200% zoom lays out at 640 CSS pixels, so it stacks too.
    ...(zoom === 2 ? [await narrowStackReach(browser, base, slug, 1280, 720, zoom)] : []),
    await narrowStackReach(browser, base, slug, 640, 900, zoom), await narrowStackReach(browser, base, slug, 390, 844, zoom)]);
  if (slug === 'bookshop') {
    await run('picker', 1, browser => pickerUsesSwitchGuard(browser, base));
    if (only === 'dialogs') await run('dialogs', dialogZoom, browser => dialogJourney(browser, base));
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
  if (!fault) { console.log(JSON.stringify(await runAll(base, out, slug, '', only, Number(flag('--zoom') || 1)))); }
  else {
    // A fault run passes only when the named assertion fails.
    try { await runAll(base, out, slug, fault, only); console.error(`FAULT ${fault} NOT CAUGHT`); process.exit(1); }
    catch (error) {
      if (!String(error.message).includes(FAULTS[fault].expect)) { console.error(`FAULT ${fault} failed elsewhere: ${error.message}`); process.exit(1); }
      console.log(JSON.stringify({ fault, caught: FAULTS[fault].expect, message: String(error.message).split('\n')[0] }));
    }
  }
}
