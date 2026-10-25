import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { lampStates } from '../../shiftwork/client/workplace-story.js';

async function refreshFixture(change = () => {}) {
  const source = await readFile(new URL('../../shiftwork/client/app.js', import.meta.url), 'utf8');
  const start = source.indexOf('async function refresh(runId = null)');
  const end = source.indexOf('function renderBoard()', start);
  const terminal = source.match(/^const terminal = .*;$/m)?.[0];
  assert.ok(start >= 0 && end > start && terminal, 'actual refresh/terminal functions were not found');
  const run = {id: 'run-0029', shift_id: 'shift-1', experiment_id: 'comparison-1', purpose: 'EXPERIMENT', state: 'QUEUED'};
  const parent = {id: run.experiment_id, shift_id: run.shift_id, kind: 'QUALIFYING_COMPARISON', state: 'FAILED', candidates: []};
  const state = {slug: 'bookshop', loadedShiftId: run.shift_id, generation: 0, selected: null,
    station: 'compare', comparison: null, candidates: {A: null, B: null}};
  const board = {latest_shift: {id: run.shift_id}, latest_run: run};
  const station = {latest_experiment: parent};
  const fixture = {run, parent, state, board, station, inspection: {mode: 'current', historicalRunId: null}};
  change(fixture);
  const scheduled = [], cleared = [];
  const api = async url => {
    if (url === '/runtime') return {notice: 'Offline test'};
    if (url === '/boards') return [{engagement_slug: 'bookshop', availability: 'AVAILABLE'}];
    if (url === '/engagements/bookshop/board') return board;
    if (url === '/engagements/bookshop/ledger') return {events: [], chain_status: 'VALID'};
    if (url === `/shifts/${board.latest_shift.id}/artifact`) return {};
    if (url === `/shifts/${board.latest_shift.id}/investigations`) return station;
    if (url === `/experiments/${parent.id}`) return parent;
    if (url === `/runs/${run.id}`) return run;
    if (url === `/runs/${run.id}/outputs` || url === `/runs/${run.id}/checks`) return [];
    throw Error(`Unexpected read: ${url}`);
  };
  const refresh = new Function('state', 'document', 'inspection', 'api', 'clearTimeout',
    'publishPresentation', 'clearData', 'text', 'renderWorkplace', 'engagementPath',
    'renderBoard', 'activateStation', 'setTimeout',
    `${terminal}\nlet pollTimer = 77;\n${source.slice(start, end)}\nreturn refresh;`)(
    state, {body: {dataset: {loadState: 'ready'}}}, fixture.inspection, api,
    timer => cleared.push(timer), () => {}, () => {}, () => {}, () => {},
    suffix => `/engagements/bookshop/${suffix}`, () => {}, () => {},
    (callback, delay) => {scheduled.push({callback, delay}); return 78;});
  const savedRun = structuredClone(run);
  assert.equal(await refresh(), true, 'refresh did not complete');
  assert.deepEqual(run, savedRun, 'polling correction changed the stored run projection');
  assert.deepEqual(cleared, [77], 'refresh did not clear the prior timer');
  return {...fixture, scheduled};
}

for (const parentState of ['FAILED', 'FINALIZED', 'INVALIDATED']) {
  test(`stopped comparison ${parentState} does not poll its queued child`, async () => {
    const f = await refreshFixture(f => {f.parent.state = parentState;});
    assert.equal(f.scheduled.length, 0, `${parentState} parent still polls its queued child`);
    assert.equal(f.state.comparison, f.parent, 'stopped comparison was not retained');
    assert.equal(f.state.run.state, 'QUEUED', 'reserved evidence was reconciled by the client');
  });
}

for (const [name, change] of [
  ['active-running', f => {f.parent.state = 'RUNNING';}],
  ['active-planned', f => {f.parent.state = 'PLANNED';}],
  ['different-experiment', f => {f.parent.id = 'other-comparison';}],
  ['different-shift', f => {f.parent.shift_id = 'other-shift';}],
  ['different-kind', f => {f.parent.kind = 'DIAGNOSTIC'; f.station.latest_experiment = null; f.state.comparison = f.parent;}],
  ['operation', f => {f.run.purpose = 'OPERATION';}],
  ['no-parent', f => {f.station.latest_experiment = null;}],
  ['unknown-parent-state', f => {f.parent.state = 'UNREPORTED';}],
  ['historical-other-run', f => {f.inspection = {mode: 'history', historicalRunId: f.run.id}; f.run.experiment_id = 'earlier-comparison';}],
]) test(`refresh keeps polling ${name}`, async () => {
  const f = await refreshFixture(change);
  assert.equal(f.scheduled.length, 1, `${name} lost its normal polling`);
  assert.equal(f.scheduled[0].delay, 1000, `${name} polling interval changed`);
});

for (const runState of ['FINALIZED', 'FAILED']) test(`terminal run ${runState} is not polled`, async () => {
  const f = await refreshFixture(f => {f.run.state = runState; f.parent.state = 'RUNNING';});
  assert.equal(f.scheduled.length, 0, 'terminal run started polling');
});

test('an absent run is not polled', async () => {
  const f = await refreshFixture(f => {f.board.latest_run = null;});
  assert.equal(f.scheduled.length, 0, 'absent run started polling');
});

for (const state of ['FAILED', 'FINALIZED', 'INVALIDATED']) {
  for (const childState of ['RESERVED', 'RUNNING']) test(`lamp respects ${state} parent with ${childState} child`, () => {
    const view = {consistency: 'linked', tests: {comparison: {state, outcomeStatus: 'INCOMPLETE', trials: [{state: childState}]}},
      consequences: {chainStatus: 'VALID', incidents: []}};
    const lamp = lampStates(view).find(item => item.stationId === 'compare');
    assert.equal(lamp.text, 'Incomplete', `${state} parent with ${childState} child is displayed as running`);
    assert.equal(lamp.tone, 'idle');
  });
}

for (const state of ['PLANNED', 'RUNNING']) test(`lamp keeps active ${state} parent running`, () => {
  const lamp = lampStates({consistency: 'linked', tests: {comparison: {state, trials: []}},
    consequences: {chainStatus: 'VALID', incidents: []}}).find(item => item.stationId === 'compare');
  assert.equal(lamp.text, 'Running');
  assert.equal(lamp.tone, 'attention');
});
