import { execFileSync } from 'node:child_process';
// Authored public states. No model, Sandbox or learner evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { ownerLine, OWNER_LINES } from '../../shiftwork/client/workplace-story.js';
import { projectWorkplace } from '../../shiftwork/client/workplace-view.js';

const client = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../shiftwork/client');
const files = ['evidence.js', 'workplace-story.js', 'workplace-view.js'];
const pristine = Object.fromEntries(await Promise.all(files.map(async file => [file, await readFile(path.join(client, file), 'utf8')])));
const hash = source => createHash('sha256').update(source).digest('hex');

function input() {
  const candidates = ['A', 'B'].map(label => ({label, artifact_version_id: label}));
  return {slug: 'bookshop', loadedShiftId: 'shift', inspection: {mode: 'current'}, ledgerStatus: 'VALID',
    board: {engagement_slug: 'bookshop', latest_shift: {id: 'shift', state: 'open'}, chain_status: 'VALID', ledger_event_count: 0, ledger_totals: {}},
    comparison: {id: 'comparison', shift_id: 'shift', kind: 'QUALIFYING_COMPARISON', state: 'FINALIZED',
      outcome: {status: 'COMPLETE'}, public_repetitions: 3, workloads: [{}, {}, {}], candidates,
      trials: candidates.flatMap(candidate => [1, 2, 3].map(pair => ({candidate_label: candidate.label,
        artifact_version_id: candidate.artifact_version_id, pair_ordinal: pair,
        repetitions: [1, 2, 3].map(n => ({run_id: `${candidate.label}-${pair}-${n}`, state: 'COMPLETE', outputs: [{}], observations: []}))})))}};
}

const hiddenCases = [
  ['incomplete', i => { i.comparison.outcome.status = 'INCOMPLETE'; }],
  ['running', i => { i.comparison.state = 'RUNNING'; }],
  ['missing-count', i => { delete i.comparison.public_repetitions; }],
  ['missing-reduced-counts', i => { i.omitReducedCounts = true; }],
  ['zero-count', i => { i.comparison.public_repetitions = 0; i.comparison.trials = []; }],
  ['missing-candidate', i => { i.comparison.candidates.pop(); }],
  ['wrong-label', i => { i.comparison.candidates[1].label = 'C'; }],
  ['unequal', i => { i.comparison.trials.at(-1).repetitions.pop(); }],
  ['unexecuted', i => { i.comparison.trials[0].repetitions[0].state = 'RESERVED'; }],
  ['empty-evidence', i => { i.comparison.trials[0].repetitions[0].outputs = []; }],
];

function checkHidden(api, makeView, change, name) {
  const i = input(); change(i);
  const view = makeView(i);
  if (i.omitReducedCounts) for (const candidate of view.tests.comparison.candidates) {
    delete candidate.plannedRepetitions;
    delete candidate.retainedRepetitions;
  }
  assert.equal(api.ownerLine(view, {step: 4}), null, `owner line must be absent: ${name}`);
}
function checkPresent(api, makeView) {
  const v = makeView(input());
  assert.equal(api.ownerLine(v, {step: 4}), OWNER_LINES[4], 'owner line must be present: complete equal retained counts');
  assert.deepEqual(v.tests.comparison.candidates.map(c => [c.plannedRepetitions, c.retainedRepetitions]), [[9, 9], [9, 9]],
    'owner counts must come from retained repetition rows');
}

test('owner line clean states hide incomplete or missing counts and show complete equal counts', () => {
  for (const [name, change] of hiddenCases) checkHidden({ownerLine}, projectWorkplace, change, name);
  checkPresent({ownerLine}, projectWorkplace);
});

const faults = [
  ['incomplete', 'workplace-story.js', "comparison?.outcomeStatus !== 'COMPLETE'", 'false', 'incomplete'],
  ['running', 'workplace-story.js', "comparison.state !== 'FINALIZED'", 'false', 'running'],
  ['missing-count', 'workplace-view.js', 'item.public_repetitions * (item.workloads?.length ?? 0)', '(item.public_repetitions ?? 3) * (item.workloads?.length ?? 0)', 'missing-count'],
  ['missing-reduced-counts', 'workplace-story.js', '!Number.isInteger(candidate.plannedRepetitions) || ', '', 'missing-reduced-counts'],
  ['zero-count', 'workplace-story.js', 'candidate.plannedRepetitions < 1', 'false', 'zero-count'],
  ['labels', 'workplace-story.js', "comparison.candidates.map(candidate => candidate.label).sort().join('') !== 'AB'", 'false', 'missing-candidate'],
  ['unequal', 'workplace-story.js', 'candidate.retainedRepetitions !== candidate.plannedRepetitions', 'false', 'unequal'],
  ['unexecuted', 'workplace-view.js', "['COMPLETE', 'FAILED'].includes(row.state) &&\n              ", '', 'unexecuted'],
  ['empty-evidence', 'workplace-view.js', '(row.outputs?.length || row.observations?.length)', 'true', 'empty-evidence'],
  ['present', 'workplace-story.js', 'return OWNER_LINES[guide.step];', 'return null;', null],
];

for (const [name, file, needle, replacement, hidden] of faults) test(`owner line fault ${name} fails its named assertion`, async () => {
  assert.equal(pristine[file].split(needle).length - 1, 1, `unique source anchor: ${name}`);
  const dir = await mkdtemp(path.join(tmpdir(), 'shiftwork-s45-owner-'));
  try {
    // S46 reuses the accepted S45 checks on a descendant, with unchanged fault assertions.
    execFileSync('git', ['merge-base', '--is-ancestor', '087585ff690194e6fde5d67be9827d732474879e', 'HEAD'], {cwd: path.resolve(client, '../..')});
    for (const source of files) await writeFile(path.join(dir, source), source === file ? pristine[source].replace(needle, replacement) : pristine[source]);
    const story = await import(pathToFileURL(path.join(dir, 'workplace-story.js')).href);
    const view = await import(pathToFileURL(path.join(dir, 'workplace-view.js')).href);
    const expected = hidden ? `owner line must be absent: ${hidden}` : 'owner line must be present: complete equal retained counts';
    assert.throws(() => hidden ? checkHidden(story, view.projectWorkplace, hiddenCases.find(row => row[0] === hidden)[1], hidden)
      : checkPresent(story, view.projectWorkplace), error => error.code === 'ERR_ASSERTION' && error.message.includes(expected));
    if (hidden) checkHidden({ownerLine}, projectWorkplace, hiddenCases.find(row => row[0] === hidden)[1], hidden);
    else checkPresent({ownerLine}, projectWorkplace);
    for (const source of files) assert.equal(hash(await readFile(path.join(client, source), 'utf8')), hash(pristine[source]), 'source must remain byte-identical');
  } finally { await rm(dir, {recursive: true, force: true}); }
});
