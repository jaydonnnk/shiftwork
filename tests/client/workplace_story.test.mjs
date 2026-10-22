// S37 story-layer checks (Gate 3 section 13.9), GPU-free.
// Each check runs clean against the production module, then once per fault
// against an in-memory mutation written to a scratch copy. A fault passes only
// when its own named assertion fails. The repository file is never modified.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { copyFile, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const client = path.join(path.dirname(fileURLToPath(import.meta.url)), '../../shiftwork/client');
const storyPath = path.join(client, 'workplace-story.js');
const pristine = await readFile(storyPath, 'utf8');
const digest = text => createHash('sha256').update(text).digest('hex');

// One mutation per guard. `needle` must occur exactly once in the served source.
export const FAULTS = {
  'latest-run': { needle: "run && run.purpose === 'OPERATION' && run.shiftId", replacement: 'run && run.shiftId',
    check: 'guide', expect: 'guide_step_follows_recorded_state: experiment run' },
  'saved-as-chosen': { needle: "if (operating?.kind === 'LEARNER_CHOICE' && comparison && operating.comparisonId === comparison.id)",
    replacement: "if (view.saved?.latestVersionId || (operating?.kind === 'LEARNER_CHOICE' && comparison && operating.comparisonId === comparison.id))",
    check: 'guide', expect: 'guide_step_follows_recorded_state: saved version is not chosen' },
  'eligible-any': { needle: 'comparison.candidates.some(candidate => candidate.eligible === true)', replacement: 'true',
    check: 'guide', expect: 'guide_step_follows_recorded_state: complete, none eligible' },
  'no-shift-match': { needle: 'run.shiftId === shiftId && ', replacement: '',
    check: 'guide', expect: 'guide_step_follows_recorded_state: operation run of an earlier shift' },
  'starter-ends-shift': { needle: "operating?.kind === 'LEARNER_CHOICE' && run && ", replacement: 'run && ',
    check: 'guide', expect: 'guide_step_follows_recorded_state: starter operation run' },
  'no-inherited-choice': { needle: "  if (operating?.kind === 'LEARNER_CHOICE' && view.shiftState === 'open') return guide(6, 'service');\n", replacement: '',
    check: 'guide', expect: 'guide_step_follows_recorded_state: inherited choice in a later shift' },
  'draft-advances': { needle: 'if ((view.investigation?.count ?? 0) >= 1)', replacement: 'if ((view.investigation?.count ?? 0) >= 1 || local.causeDraft)',
    check: 'drafts', expect: 'guide_never_credits_unsent_text: a draft moved the guide' },
  'suggestive-line': { needle: "5: 'Nothing goes live until you choose and say why.',",
    replacement: "5: 'Nothing goes live until you choose; version A looks better.',",
    check: 'owner', expect: 'owner_lines_never_suggest: line 5 suggests' },
  'starter-open-queue': { needle: "starterOpen ? lamp('customers', 'attention', `${open} open ${open === 1 ? 'complaint' : 'complaints'}`)\n    : ", replacement: '',
    check: 'lamps', expect: 'lamps_reflect_state_with_text: starter with open complaints (customers)' },
  'starter-open-service': { needle: "    : starterOpen ? lamp('service', 'attention', 'Live, complaints open')\n", replacement: '',
    check: 'lamps', expect: 'lamps_reflect_state_with_text: starter with open complaints (service)' },
  'starter-open-owner': { needle: "return open ? OWNER_LINES.openComplaints.replace('{n}', String(open)) : null;", replacement: 'return null;',
    check: 'owner', expect: 'owner_lines_never_suggest: open complaints under the starter' },
  'compare-pass': { needle: "lamp('compare', 'idle', 'No score, no default')", replacement: "lamp('compare', 'pass', 'No score, no default')",
    check: 'lamps', expect: 'lamps_reflect_state_with_text: compare shows pass' },
  'experiment-pass': { needle: "const ownOperation = Boolean(run && run.purpose === 'OPERATION' && operating && run.selectionId === operating.selectionId);",
    replacement: 'const ownOperation = Boolean(run && operating);', check: 'lamps', expect: 'lamps_reflect_state_with_text: passing experiment' },
  'lamp-no-text': { needle: "lamp('ledger', 'idle', 'None open')", replacement: "lamp('ledger', 'idle', '')",
    check: 'lamps', expect: 'lamps_reflect_state_with_text: a lamp has no text' },
};

async function load(fault) {
  if (!fault) return import(pathToFileURL(storyPath).href);
  const { needle, replacement } = FAULTS[fault];
  assert.equal(pristine.split(needle).length - 1, 1, `Fault ${fault} needle must occur exactly once`);
  const dir = await mkdtemp(path.join(tmpdir(), 'shiftwork-s37-story-'));
  await copyFile(path.join(client, 'evidence.js'), path.join(dir, 'evidence.js'));
  await writeFile(path.join(dir, 'workplace-story.js'), pristine.replace(needle, replacement));
  try { return await import(pathToFileURL(path.join(dir, 'workplace-story.js')).href); }
  finally { await rm(dir, { recursive: true, force: true }); }
}

// A literal public view with the fields the story module reads.
function view(change = () => {}) {
  const v = { context: { board: 'bookshop', shiftId: 'shift-2', inspection: { mode: 'current', historicalRunId: null } },
    station: 'service', shiftState: 'open', consistency: 'linked',
    operating: { selectionId: 'sel-0001', kind: 'STARTER_BASELINE', versionId: 'ver-0001', comparisonId: null, validity: 'VALID' },
    saved: { latestVersionId: null, draftBaseVersionId: null },
    run: null, slips: null, investigation: { latestEntryId: null, count: 0 },
    tests: { diagnostic: null, comparison: null, later: null },
    consequences: { chainStatus: 'VALID', incidents: [{ id: 'inc-1', state: 'OPEN' }] } };
  change(v);
  return v;
}
const run = (purpose, state, extra = {}) => ({ id: 'run-0009', shiftId: 'shift-2', versionId: 'ver-0003', selectionId: 'sel-0002',
  state, purpose, outputCount: 3, ...extra });
const comparison = (eligible, extra = {}) => ({ id: 'experiment-shift-2-c1', shiftId: 'shift-2', state: 'FINALIZED', outcomeStatus: 'COMPLETE',
  trials: [], candidates: [{ label: 'A', versionId: 'ver-0002', eligible: eligible[0], blockingReasonCodes: eligible[0] ? [] : ['MANDATORY_CHECK_FAILED'] },
    { label: 'B', versionId: 'ver-0003', eligible: eligible[1], blockingReasonCodes: eligible[1] ? [] : ['MISSING_EVIDENCE'] }], ...extra });
const chosen = v => { v.operating = { selectionId: 'sel-0002', kind: 'LEARNER_CHOICE', versionId: 'ver-0003', comparisonId: 'experiment-shift-2-c1', validity: 'VALID' }; };
const tally = (pass, fail, error = 0, none = 0) => ({ total: pass + fail + error + none, pass, fail, error, none });

// [case name, view, local guidance, expected step, station, status]
const GUIDE_CASES = [
  ['closed shift', view(v => { v.shiftState = 'closed'; }), {}, 7, 'next', 'ready'],
  ['operation running', view(v => { chosen(v); v.run = run('OPERATION', 'RUNNING'); }), {}, 6, 'service', 'running'],
  ['operation captured', view(v => { chosen(v); v.run = run('OPERATION', 'CAPTURED'); }), {}, 6, 'service', 'running'],
  ['operation finalized', view(v => { chosen(v); v.run = run('OPERATION', 'FINALIZED'); }), {}, 7, 'ledger', 'ready'],
  ['operation failed', view(v => { chosen(v); v.run = run('OPERATION', 'FAILED'); }), {}, 7, 'ledger', 'ready'],
  ['learner choice', view(v => { chosen(v); v.tests.comparison = comparison([true, true]); }), {}, 6, 'service', 'ready'],
  // Rule 3a (re-approved 2026-10-22): the choice came from an earlier shift's comparison and has not run in this one.
  ['inherited choice in a later shift', view(v => { chosen(v); v.operating.comparisonId = 'experiment-shift-1-c1'; }), {}, 6, 'service', 'ready'],
  ['complete, one eligible', view(v => { v.tests.comparison = comparison([false, true]); v.investigation.count = 1; }), {}, 5, 'compare', 'ready'],
  ['complete, none eligible', view(v => { v.tests.comparison = comparison([false, false]); v.investigation.count = 1; }), {}, 4, 'compare', 'blocked'],
  ['investigation recorded', view(v => { v.investigation.count = 1; }), {}, 4, 'compare', 'ready'],
  ['investigating with a cause draft', view(), { activeStation: 'investigate', causeDraft: true }, 3, 'investigate', 'ready'],
  ['investigating', view(), { activeStation: 'investigate' }, 2, 'investigate', 'ready'],
  ['fresh shift', view(), {}, 1, 'customers', 'ready'],
  // Recorded state that a careless guide would misread.
  ['experiment run', view(v => { chosen(v); v.run = run('EXPERIMENT', 'FINALIZED'); }), {}, 6, 'service', 'ready'],
  ['saved version is not chosen', view(v => { v.saved.latestVersionId = 'ver-0004'; }), {}, 1, 'customers', 'ready'],
  ['operation run of an earlier shift', view(v => { chosen(v); v.run = run('OPERATION', 'FINALIZED', { shiftId: 'shift-1' }); }), {}, 6, 'service', 'ready'],
  // A fresh shift: the starter version's own operation run is already finalized (Gate 3 section 13.5 rule 2, re-approved 2026-10-21).
  ['starter operation run', view(v => { v.run = run('OPERATION', 'FINALIZED', { selectionId: 'sel-0001' }); }), {}, 1, 'customers', 'ready'],
  ['comparison of an earlier shift', view(v => { v.tests.comparison = comparison([true, true], { shiftId: 'shift-1' }); }), {}, 1, 'customers', 'ready'],
];

async function guideCheck(api) {
  for (const [name, v, local, step, station, status] of GUIDE_CASES) {
    const got = api.guideStep(v, local);
    assert.deepEqual([got.step, got.stationId, got.status], [step, station, status], `guide_step_follows_recorded_state: ${name}`);
    assert.equal(got.name, api.STEP_NAMES[step - 1], `guide_step_follows_recorded_state: ${name} step name`);
  }
  const blocked = api.guideStep(GUIDE_CASES.find(([name]) => name === 'complete, none eligible')[1], {});
  assert.equal(blocked.blockedReason, 'Neither version can be chosen: mandatory check failed', 'guide_step_follows_recorded_state: blocked reason in words');
  for (const unknown of [null, view(v => { v.consistency = 'conflict'; }), view(v => { v.context.shiftId = null; })]) {
    const got = api.guideStep(unknown, { activeStation: 'owner' });
    assert.deepEqual([got.step, got.stationId, got.blockedReason], [null, 'owner', 'Step unknown: recorded state unavailable'],
      'guide_step_follows_recorded_state: unknown state');
  }
}

async function draftsCheck(api) {
  const drafts = { causeDraft: true, falsifierDraft: true };
  for (const [name, v] of GUIDE_CASES) for (const activeStation of ['customers', 'investigate', 'compare']) {
    const before = JSON.stringify(v);
    const plain = api.guideStep(v, { activeStation }), drafted = api.guideStep(v, { activeStation, ...drafts });
    assert.equal(JSON.stringify(v), before, `guide_never_credits_unsent_text: the guide changed the view (${name})`);
    if (plain.step <= 3) assert.ok(drafted.step >= 1 && drafted.step <= 3, `guide_never_credits_unsent_text: a draft moved the guide past step 3 (${name})`);
    else assert.deepEqual(drafted, plain, `guide_never_credits_unsent_text: a draft moved the guide (${name}, ${activeStation})`);
    if (plain.step === 1 || plain.step === 2) assert.equal(drafted.stationId, plain.stationId, `guide_never_credits_unsent_text: a draft moved the guide to another station (${name})`);
  }
  // A cause draft alone, outside the investigate station, credits nothing.
  assert.equal(api.guideStep(view(), { activeStation: 'customers', causeDraft: true }).step, 1, 'guide_never_credits_unsent_text: a draft moved the guide away from step 1');
}

// Words that name a cause, a fix, a preference or a choice. Owner lines also
// must not name what failed for this client (CAUSE_WORDS); picker questions
// state the symptom, so they are scanned for fix and preference words only.
export const FIX_WORDS = ['because', 'caused by', 'the cause is', 'fix', 'repair', 'patch', 'bug', 'broken', 'should', 'better', 'best',
  'prefer', 'recommend', 'pick ', 'instead', 'try changing', 'change the', 'add a', 'remove the', 'candidate'];
export const CAUSE_WORDS = ['price', 'stock', 'collect', 'retriev', 'missing', 'tool', 'prompt', 'model', 'route', 'routing', 'permission', 'owner field'];
const LABELS = [/\bver-\d+/i, /\b(?:version|candidate|option|fix) [AB]\b/i, /\b[AB]\b/];
export function suggests(text, words) {
  const lower = text.toLowerCase();
  return [...words.filter(word => lower.includes(word)), ...LABELS.filter(rule => rule.test(text)).map(String)];
}

async function ownerCheck(api) {
  const lines = Object.entries(api.OWNER_LINES).map(([key, line]) => [key, line.replace('{n}', '3').replace('{p}', '2').replace('{m}', '5')]);
  // Nine lines since the 2026-10-22 re-approval added openComplaints.
  assert.equal(lines.length, 9, 'owner_lines_never_suggest: the catalogue changed size without a recorded review');
  // Scanner self-test: every needle is detected inside a rendered line.
  for (const needle of [...FIX_WORDS, ...CAUSE_WORDS, 'ver-0002', 'version A', ' B ']) {
    const rendered = `${lines[0][1]} ${needle} ${lines[1][1]}`;
    assert.ok(suggests(rendered, [...FIX_WORDS, ...CAUSE_WORDS]).length > 0, `Scanner self-test missed ${JSON.stringify(needle)}`);
  }
  for (const [key, line] of lines) assert.deepEqual(suggests(line, [...FIX_WORDS, ...CAUSE_WORDS]), [], `owner_lines_never_suggest: line ${key} suggests`);
  for (const card of api.SHIFT_CARDS) for (const field of ['question', 'teaches']) {
    assert.deepEqual(suggests(card[field], FIX_WORDS), [], `owner_lines_never_suggest: ${card.slug} ${field} suggests`);
  }
  // ownerLine substitutes public counts only and never invents a zero.
  const slips = v => { v.slips = { tally: tally(2, 3) }; };
  assert.equal(api.ownerLine(view(slips), { step: 1 }), '3 customers in the last recorded run did not get what they asked for.');
  const resolved = v => { v.consequences.incidents = []; };
  assert.equal(api.ownerLine(view(resolved), { step: 1 }), null, 'owner_lines_never_suggest: an unknown count became a line');
  // A passing starter run with complaints still open (S37 review F2): the open count, never the run's zero.
  const starterPassed = v => { v.run = run('OPERATION', 'FINALIZED', { selectionId: 'sel-0001' }); v.slips = { tally: tally(1, 0) };
    v.consequences.incidents = ['OPEN', 'OPEN', 'CLOSED_UNRESOLVED', 'RESOLVED'].map((state, i) => ({ id: `inc-${i}`, state })); };
  assert.equal(api.ownerLine(view(starterPassed), { step: 1 }), '3 customer complaints are still open.', 'owner_lines_never_suggest: open complaints under the starter');
  assert.equal(api.ownerLine(view(v => { starterPassed(v); chosen(v); }), { step: 1 }), null, 'owner_lines_never_suggest: open complaints credited to a learner choice');
  assert.equal(api.ownerLine(view(slips), { step: 7 }), "2 of 5 recorded requests passed the inspector's checks.");
  assert.equal(api.ownerLine(view(), { step: 7 }), null, 'owner_lines_never_suggest: an unknown count became a line');
  assert.equal(api.ownerLine(view(v => { v.shiftState = 'closed'; }), { step: 7 }), api.OWNER_LINES.closed);
  assert.equal(api.ownerLine(view(), { step: null }), null);
}

const lampOf = (api, v) => Object.fromEntries(api.lampStates(v).map(item => [item.stationId, [item.tone, item.text]]));
async function lampsCheck(api) {
  const rows = [
    // S37 review F2: the starter's passing run with complaints still open (13.5, re-approved 2026-10-22).
    ['starter with open complaints', view(v => { v.run = run('OPERATION', 'FINALIZED', { selectionId: 'sel-0001' }); v.slips = { tally: tally(1, 0) };
      v.consequences.incidents = ['OPEN', 'OPEN', 'OPEN'].map((state, i) => ({ id: `inc-${i}`, state })); }),
      { customers: ['attention', '3 open complaints'], service: ['attention', 'Live, complaints open'], ledger: ['fail', '3 open'] }],
    ['no run', view(v => { v.consequences.incidents = [{ id: 'inc-1', state: 'RESOLVED' }]; }),
      { customers: ['idle', 'No recorded requests'], service: ['attention', 'Live, not yet run'], ledger: ['idle', 'None open'], compare: ['idle', 'Not started'] }],
    ['no run, one open', view(), { customers: ['attention', '1 open complaint'], ledger: ['fail', '1 open'] }],
    ['failing operation', view(v => { chosen(v); v.run = run('OPERATION', 'FINALIZED'); v.slips = { tally: tally(1, 1, 1) }; }),
      { customers: ['attention', '2 complaints'], service: ['fail', 'Live, checks failed'], evaluator: ['idle', 'Locked'] }],
    ['passing operation', view(v => { chosen(v); v.run = run('OPERATION', 'FINALIZED'); v.slips = { tally: tally(3, 0) }; }),
      { customers: ['pass', 'No complaints'], service: ['pass', 'Live, checks passed'] }],
    ['passing experiment', view(v => { chosen(v); v.run = run('EXPERIMENT', 'FINALIZED'); v.slips = { tally: tally(3, 0) }; }),
      { customers: ['idle', '3 recorded requests'], service: ['attention', 'Live, not yet run'] }],
    ['running', view(v => { v.run = run('EXPERIMENT', 'RUNNING'); }), { evaluator: ['idle', 'Locked · running'] }],
    ['no live version', view(v => { v.operating = null; }), { service: ['idle', 'No live version'] }],
    ['invalidated', view(v => { v.operating.validity = 'INVALIDATED'; }), { service: ['fail', 'Invalidated'] }],
    ['no open incident', view(v => { v.consequences.incidents = []; }), { ledger: ['idle', 'None open'] }],
    ['broken chain', view(v => { v.consequences.chainStatus = 'unknown'; }), { ledger: ['unknown', 'Unavailable'] }],
    ['comparison running', view(v => { v.tests.comparison = comparison([null, null], { state: 'RUNNING', outcomeStatus: null }); }), { compare: ['attention', 'Running'] }],
    ['complete comparison', view(v => { v.tests.comparison = comparison([true, true]); }), { compare: ['idle', 'No score, no default'] }],
    ['attention on a quiet station', view(v => { v.attention = 'investigate'; }), { investigate: ['attention', 'Nothing recorded'], owner: ['idle', 'Read only'] }],
  ];
  for (const [name, v, expected] of rows) {
    const lamps = lampOf(api, v);
    // Text presence and the compare rule run first, so their own faults cannot hide behind a row value.
    assert.ok(Object.values(lamps).every(([, text]) => typeof text === 'string' && text.length > 0), `lamps_reflect_state_with_text: a lamp has no text (${name})`);
    assert.ok(lamps.compare[0] !== 'pass', `lamps_reflect_state_with_text: compare shows pass (${name})`);
    for (const [station, value] of Object.entries(expected)) assert.deepEqual(lamps[station], value, `lamps_reflect_state_with_text: ${name} (${station})`);
  }
  assert.ok(Object.values(lampOf(api, view(v => { v.consistency = 'conflict'; }))).every(([tone]) => tone === 'unknown'), 'lamps_reflect_state_with_text: conflict');
}

async function bubbleCheck(api) {
  const v = view(v => { v.run = run('OPERATION', 'FINALIZED'); });
  const output = { id: 'out-1', run_id: 'run-0009', request_text: `  Can I collect it today? ${'x'.repeat(200)}` };
  const bubble = api.customerBubble(v, output);
  assert.equal(bubble.label, 'Recorded request · operation');
  assert.equal(bubble.text.length, 140, 'customer bubble is not truncated to 140 characters');
  assert.ok(bubble.text.startsWith('Can I collect it today?') && bubble.text.endsWith('…'));
  assert.equal(api.customerBubble(v, null), null, 'a bubble appeared with no output');
  assert.equal(api.customerBubble(v, { ...output, run_id: 'run-0001' }), null, 'a bubble showed another run');
  assert.equal(api.customerBubble(view(w => { w.run = run('EXPERIMENT', 'FINALIZED'); }), output).label, 'Recorded request · test');
  assert.equal(api.customerBubble(view(w => { w.run = run('OPERATION', 'FINALIZED'); w.context.inspection.mode = 'history'; }), output).label, 'Recorded request · history');
}

async function slipsCheck(api) {
  const r = { id: 'run-0009', state: 'FINALIZED', purpose: 'OPERATION' };
  const outputs = [3, 1, 2, 4].map(n => ({ id: `out-${n}`, run_id: 'run-0009', request_ordinal: n }));
  const checks = [['out-1', 'pass'], ['out-1', 'fail'], ['out-2', 'error'], ['out-3', 'pass']]
    .map(([ref, verdict], i) => ({ id: `chk-${i}`, run_id: 'run-0009', observed_ref: ref, verdict }));
  const plan = api.planSlips(r, outputs, checks, []);
  assert.deepEqual(plan.slips.map(slip => [slip.ordinal, slip.verdict]), [[1, 'fail'], [2, 'error'], [3, 'pass'], [4, 'none']], 'slip verdicts');
  assert.deepEqual(plan.tally, tally(1, 1, 1, 1));
  assert.equal(api.planSlips({ ...r, state: 'RUNNING' }, outputs, checks, []), null, 'a running run produced slips');
  assert.equal(api.planSlips(r, outputs, null, []), null, 'slips before the checks read');
}

const CHECKS = { guide: guideCheck, drafts: draftsCheck, owner: ownerCheck, lamps: lampsCheck, bubble: bubbleCheck, slips: slipsCheck };
const NAMES = { guide: 'guide_step_follows_recorded_state', drafts: 'guide_never_credits_unsent_text', owner: 'owner_lines_never_suggest',
  lamps: 'lamps_reflect_state_with_text', bubble: 'customer_bubble_shows_recorded_request', slips: 'slip_verdicts_follow_linked_checks' };

for (const [key, check] of Object.entries(CHECKS)) test(NAMES[key], async () => check(await load()));
for (const [fault, row] of Object.entries(FAULTS)) test(`fault_${fault}_fails_${NAMES[row.check]}`, async () => {
  const api = await load(fault);
  await assert.rejects(() => CHECKS[row.check](api), error => {
    assert.ok(String(error.message).includes(row.expect), `Fault ${fault} failed elsewhere: ${error.message}`);
    return true;
  }, `Fault ${fault} was not caught`);
});
test('story_source_is_unchanged', async () => assert.equal(digest(await readFile(storyPath, 'utf8')), digest(pristine)));

function reportFixture() {
  const operation = { id: 'run-report', shift_id: 'shift-2', purpose: 'OPERATION', state: 'FINALIZED',
    artifact_version_id: 'ver-0002', selection_id: 'sel-report' };
  const selection = { id: 'sel-report', selected_version_id: 'ver-0002', retained_alternative_version_id: 'ver-0003' };
  const checks = [{ id: 'check-report', run_id: operation.id, observed_ref: 'out-report', verdict: 'fail' }];
  const historical = { seq: 1, hash: 'old', event_type: 'INCIDENT_OPENED', synthetic: true,
    cause_refs: ['old-run', 'old-check', 'old-output'],
    derivation: { run_id: 'old-run', check_id: 'old-check', observed_ref: 'old-output', request_ordinal: 1, verdict: 'fail' } };
  const linked = (seq, type) => ({ seq, hash: `hash-${seq}`, event_type: type, synthetic: true,
    cause_refs: [operation.id, 'check-report', 'out-report'],
    derivation: { run_id: operation.id, check_id: 'check-report', observed_ref: 'out-report', request_ordinal: 1, verdict: 'fail' } });
  const events = [historical, linked(2, 'INCIDENT_OPENED'), linked(3, 'INCIDENT_RESOLVED'),
    { ...historical, seq: 4, hash: 'future', cause_refs: ['future-run'], derivation: { ...historical.derivation, run_id: 'future-run' } }];
  const v = view();
  v.run = { id: operation.id, outputCount: 2 };
  v.slips = { runId: operation.id, tally: { total: 2, pass: 1, fail: 1, error: 0, none: 0 } };
  v.consequences = { chainStatus: 'VALID', countMatches: true, histogramMatches: true,
    events: events.map(event => ({ seq: event.seq, hash: event.hash, linkState: 'linked' })) };
  return { v, operation, checks, events, selection };
}
async function reportCheck(api) {
  assert.equal(typeof api.reduceShiftReport, 'function', 'shift_report_matches_ledger: reducer is missing');
  const f = reportFixture();
  const reduce = () => api.reduceShiftReport(f.v, f.operation, f.checks, f.events, f.selection);
  const got = reduce();
  assert.deepEqual([got.incidentsOpened, got.incidentsResolved], [1, 1], 'shift_report_matches_ledger: count only this run linked events');
  assert.deepEqual(got, { runId: 'run-report', versionLabel: 'ver-0002', backupLabel: 'ver-0003',
    requests: { pass: 1, fail: 1, error: 0, none: 0 }, incidentsOpened: 1, incidentsResolved: 1,
    openBefore: 1, openAfter: 1, complete: true }, 'shift_report_matches_ledger: literal report');
  f.events[1].derivation.check_id = 'missing-check';
  const missing = reduce();
  assert.equal(missing.incidentsOpened, null, 'shift_report_matches_ledger: missing link stays null');
  assert.equal(missing.openAfter, null, 'shift_report_matches_ledger: missing link makes the after count unknown');
  assert.equal(missing.complete, false, 'shift_report_matches_ledger: missing link is incomplete');
  const failed = reportFixture();
  failed.operation.state = 'FAILED'; failed.events = [];
  failed.v.slips.tally = { total: 0, pass: 0, fail: 0, error: 0, none: 0 }; failed.v.run.outputCount = 0;
  assert.deepEqual(api.reduceShiftReport(failed.v, failed.operation, [], [], failed.selection), {
    runId: 'run-report', versionLabel: 'ver-0002', backupLabel: 'ver-0003', requests: { pass: 0, fail: 0, error: 0, none: 0 },
    incidentsOpened: 0, incidentsResolved: 0, openBefore: 0, openAfter: 0, complete: true,
  }, 'shift_report_matches_ledger: failed operation has no invented requests or success');
}
test('shift_report_matches_ledger', async () => reportCheck(await load()));
test('shift_report_absent_run_is_unknown', async () => {
  const api = await load();
  let report;
  assert.doesNotThrow(() => { report = api.reduceShiftReport(null, null, [], [{ synthetic: true, event_type: 'LIMIT_DECLARED', cause_refs: [] }], null); },
    'shift_report_matches_ledger: absent run must stay unknown without throwing');
  assert.equal(report.incidentsOpened, null);
});

const REPORT_GUARDS = [
  ['purpose', f => { f.operation.purpose = 'EXPERIMENT'; }, "const bound = Boolean(run && run.purpose === 'OPERATION' && TERMINAL.has(run.state) &&", 'const bound = Boolean(run && TERMINAL.has(run.state) &&', 'requests.pass'],
  ['terminal', f => { f.operation.state = 'RUNNING'; }, 'TERMINAL.has(run.state) &&\n    view?.run', 'true &&\n    view?.run', 'requests.pass'],
  ['run-identity', f => { f.v.run.id = 'other-run'; }, 'view?.run?.id === run.id && ', '', 'requests.pass'],
  ['selection-identity', f => { f.selection.id = 'other-choice'; }, 'selection?.id === run.selection_id && ', '', 'requests.pass'],
  ['selected-version', f => { f.selection.selected_version_id = 'other-version'; }, 'selection.selected_version_id === run.artifact_version_id', 'true', 'requests.pass'],
  ['checks-accepted', f => { f.checks = null; }, 'bound && Array.isArray(checks) && tally', 'bound && tally', 'requests.pass'],
  ['slips-identity', f => { f.v.slips.runId = 'other-run'; }, 'view?.slips?.runId === run.id ? view.slips.tally', 'true ? view.slips.tally', 'requests.pass'],
  ['capture-count', f => { f.v.run.outputCount = 3; }, 'tally?.total === view.run.outputCount', 'true', 'requests.pass'],
  ['conflict', f => { f.v.consistency = 'conflict'; }, "view.consistency !== 'conflict' &&\n", '', 'incidentsOpened'],
  ['chain', f => { f.v.consequences.chainStatus = 'unknown'; }, "view.consequences?.chainStatus === 'VALID' && ", '', 'incidentsOpened'],
  ['ledger-count', f => { f.v.consequences.countMatches = false; }, 'view.consequences.countMatches === true && ', '', 'incidentsOpened'],
  ['ledger-histogram', f => { f.v.consequences.histogramMatches = false; }, 'view.consequences.histogramMatches === true', 'true', 'incidentsOpened'],
  ['synthetic', f => { f.events[1].synthetic = false; f.events[1].event_type = 'SALE_COMPLETED'; }, 'event.synthetic === true && link?.run_id', 'true && link?.run_id', 'incidentsOpened'],
  ['link-run', f => { f.events[1].derivation.run_id = 'other-run'; }, 'link?.run_id === run.id &&\n', 'true &&\n', 'incidentsOpened'],
  ['check-identity', f => { f.events[1].derivation.check_id = 'missing-check'; }, 'check.id === link.check_id && ', '', 'incidentsOpened'],
  ['check-run', f => { f.checks[0].run_id = 'other-run'; }, 'check.run_id === run.id &&\n', '', 'incidentsOpened'],
  ['check-output', f => { f.checks[0].observed_ref = 'other-output'; }, 'check.observed_ref === link.observed_ref && ', '', 'incidentsOpened'],
  ['check-verdict', f => { f.checks[0].verdict = 'pass'; }, 'check.verdict === link.verdict', 'true', 'incidentsOpened'],
  ['projected-sequence', f => { f.v.consequences.events[1].seq = 99; }, 'row.seq === event.seq && ', '', 'incidentsOpened'],
  ['projected-hash', f => { f.v.consequences.events[1].hash = 'other-hash'; }, 'row.hash === event.hash && ', '', 'incidentsOpened'],
  ['projected-link', f => { f.v.consequences.events[1].linkState = 'incomplete'; }, "row.linkState === 'linked'", 'true', 'incidentsOpened'],
  ['historical-link', f => { f.events[0].derivation = null; }, 'event.synthetic === true && event.derivation);', 'true);', 'incidentsOpened'],
  ['historical-synthetic', f => { f.events[0].synthetic = false; }, 'event.synthetic === true && event.derivation);', 'event.derivation);', 'incidentsOpened'],
  ['history-boundary', f => { f.events = []; f.v.context.inspection.mode = 'history'; }, "view?.context?.inspection.mode === 'current' ? Infinity : null", 'Infinity', 'openBefore'],
  ['negative-balance', f => { f.events = [f.events[2]]; }, 'return value < 0 ? null : value;', 'return value;', 'openAfter'],
];
for (const [name, modify, needle, replacement, field] of REPORT_GUARDS) test(`report_guard_${name}`, async () => {
  const f = reportFixture(); modify(f);
  const check = api => {
    const got = api.reduceShiftReport(f.v, f.operation, f.checks, f.events, f.selection);
    assert.equal(field.includes('.') ? got.requests.pass : got[field], null, `shift_report_matches_ledger: ${name} must stay unknown`);
  };
  check(await load());
  FAULTS[name] = { needle, replacement };
  try {
    const broken = await load(name);
    assert.throws(() => check(broken), error => error.message.includes(`shift_report_matches_ledger: ${name} must stay unknown`));
    check(await load());
    assert.equal(digest(await readFile(storyPath, 'utf8')), digest(pristine));
  } finally { delete FAULTS[name]; }
});

for (const [name, needle, replacement, expected] of [
  ['report-all-events', 'const runEvents = (events ?? []).filter(event => run && (event.derivation?.run_id === run.id || event.cause_refs?.[0] === run.id));',
    'const runEvents = events ?? [];', 'count only this run linked events'],
  ['report-null-zero', "const count = type => countable ? runEvents.filter(event => event.event_type === type).length : null;",
    "const count = type => countable ? runEvents.filter(event => event.event_type === type).length : 0;", 'missing link stays null'],
]) test(`fault_${name}_fails_shift_report_matches_ledger`, async () => {
  const row = { needle, replacement }; FAULTS[name] = row;
  try {
    const api = await load(name);
    await assert.rejects(() => reportCheck(api), error => String(error.message).includes(expected));
    await reportCheck(await load());
    assert.equal(digest(await readFile(storyPath, 'utf8')), digest(pristine));
  }
  finally { delete FAULTS[name]; }
});
