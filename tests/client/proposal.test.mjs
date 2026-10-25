import test from 'node:test';
import assert from 'node:assert/strict';
import * as evidence from '../../shiftwork/client/evidence.js';
import { readFile } from 'node:fs/promises';

const view = (state = 'COMPLETE', mandatory = true, body = 'e30=') => ({
  kind: 'DIAGNOSTIC', public_repetitions: 1, eligible: false,
  candidates: [{artifact_version_id: null, proposal_event_id: 'coach-1'}],
  trials: [{state, request_count: 1, outputs: [{request_ordinal: 1, body_base64: body, transport_error: null}],
    task_assessments: [{request_ordinal: 1, mandatory_pass: mandatory}]}],
});

test('proposal rate comes from the retained deterministic diagnostic', () => {
  assert.equal(typeof evidence.proposalDiagnosticSummary, 'function', 'the proposal diagnostic summary is missing');
  const {proposalDiagnosticSummary} = evidence;
  assert.equal(proposalDiagnosticSummary(view()), '1 of 1 public batches passed mandatory checks. This diagnostic cannot qualify a version.');
  for (const input of [view('FAILED'), view('COMPLETE', false), view('COMPLETE', true, '')]) {
    assert.equal(proposalDiagnosticSummary(input), '0 of 1 public batches passed mandatory checks. This diagnostic cannot qualify a version.');
  }
  assert.equal(proposalDiagnosticSummary(view('RUNNING')), 'One isolated diagnostic is in progress.');
  assert.equal(proposalDiagnosticSummary({...view(), eligible: true}), 'Proposal report has inconsistent identity or eligibility.');
});

test('a late proposal report cannot publish on a different board', async () => {
  const source = await readFile(new URL('../../shiftwork/client/app.js', import.meta.url), 'utf8');
  const start = source.indexOf('function diagnosticOwner()');
  const end = source.indexOf('async function runDiagnostic(', start);
  assert.ok(start >= 0 && end > start);
  const state = {slug: 'bookshop', board: {latest_shift: {id: 'shift-1'}}, loadedShiftId: 'shift-1', generation: 1, intent: 1, diagnostic: null};
  const inspection = {mode: 'current', historicalRunId: null};
  let release;
  const gate = new Promise(resolve => {release = resolve;});
  const report = {shift_id: 'shift-1', id: 'proposal-report'};
  const api = async url => { if (url.startsWith('/runs/')) { await gate; return {experiment_id: report.id}; } return report; };
  let rendered = 0;
  const inspect = new Function('state', 'inspection', 'api', 'renderInvestigate', 'publishPresentation', 'text',
    source.slice(start, end) + '\nreturn inspectProposalReport;')(state, inspection, api, () => {rendered++;}, () => {}, () => {});
  const pending = inspect('proposal-run');
  Object.assign(state, {slug: 'gtm', loadedShiftId: 'shift-2', generation: 2});
  release(); await pending;
  assert.equal(state.diagnostic, null, 'a stale proposal report replaced the new board state');
  assert.equal(rendered, 0, 'a stale proposal report rendered on the new board');
});

async function requestSummary() {
  const source = await readFile(new URL('../../shiftwork/client/app.js', import.meta.url), 'utf8');
  const start = source.indexOf('function failedRequestOutput()');
  const end = source.indexOf('function renderInvestigate()', start);
  assert.ok(start >= 0 && end > start);
  const element = (_tag, text = '') => ({
    dataset: {}, children: [], textContent: text ?? '',
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; this.textContent = ''; },
  });
  const target = element('div');
  const run = {id: 'run-0011', shift_id: 'bookshop-shift-01', experiment_id: 'diagnostic-2',
    artifact_version_id: null, proposal_event_id: 'coach-1', purpose: 'EXPERIMENT', evidence_mode: 'ISOLATED_LIVE'};
  const trial = {run_id: run.id, artifact_version_id: null, proposal_event_id: run.proposal_event_id,
    outputs: [{request_ordinal: 1}], customer_text: 'Harbour Atlas is available for collection.',
    task_assessments: [{request_ordinal: 1, task_id: 'collection', mandatory_pass: true, reason_codes: []},
      {request_ordinal: 1, task_id: 'alternative', mandatory_pass: true, reason_codes: []}]};
  const diagnostic = {id: run.experiment_id, shift_id: run.shift_id, kind: 'DIAGNOSTIC', trials: [trial]};
  const output = {id: 'run-0011-out-1', run_id: run.id, request_ordinal: 1,
    request_text: 'Can I collect Salt Roads? If not, suggest an alternative.', customer_answer: null};
  const state = {run, outputs: [output], checks: [], events: [], selected: output.id,
    diagnostic: null, stationView: {latest_diagnostic: diagnostic}};
  const render = new Function('state', '$', 'element', 'empty', 'selectEvidence', 'humanize',
    source.slice(start, end) + '\nreturn renderFailedRequest;')(
    state, () => target, element, (node, text) => node.append(element('p', text)),
    evidence.selectEvidence, value => String(value).replaceAll('_', ' ').toLowerCase());
  const flatten = node => [node.textContent, ...node.children.map(flatten)].join('\n');
  return {state, diagnostic, trial, output, render: () => {render(); return flatten(target);}};
}

test('proposal request summary uses its exact diagnostic answer and task evidence', async () => {
  const ui = await requestSummary();
  const summary = ui.render();
  assert.match(summary, /executed coach proposal coach-1/, 'the proposal was displayed as a nullable saved version');
  assert.match(summary, /Harbour Atlas is available for collection\./, 'the retained proposal answer was omitted');
  assert.match(summary, /collection: mandatory check passes; alternative: mandatory check passes/,
    'the summary omitted passing diagnostic task evidence');
  assert.doesNotMatch(summary, /executed null|No validated customer answer|Independent evidence is incomplete/);
});

test('proposal summary refuses reports with a different experiment, shift, run or proposal', async () => {
  for (const [identity, change] of [
    ['experiment', ui => { ui.diagnostic.id = 'other-experiment'; }],
    ['shift', ui => { ui.diagnostic.shift_id = 'other-shift'; }],
    ['kind', ui => { ui.diagnostic.kind = 'QUALIFYING_COMPARISON'; }],
    ['run', ui => { ui.trial.run_id = 'other-run'; }],
    ['proposal', ui => { ui.trial.proposal_event_id = 'other-proposal'; }],
    ['trial-version', ui => { ui.trial.artifact_version_id = 'saved-version'; }],
    ['run-version', ui => { ui.state.run.artifact_version_id = 'saved-version'; }],
    ['output-run', ui => { ui.output.run_id = 'other-run'; }],
  ]) {
    const ui = await requestSummary(); change(ui);
    const summary = ui.render();
    assert.match(summary, /No matching proposal diagnostic is loaded/, `unrelated ${identity} evidence was not refused`);
    assert.doesNotMatch(summary, /Harbour Atlas|mandatory check passes/, 'unrelated diagnostic evidence leaked into the summary');
  }
});

test('proposal task summary reports failures and missing evidence without inventing a pass', async () => {
  const ui = await requestSummary();
  ui.trial.task_assessments[1].mandatory_pass = false;
  ui.trial.task_assessments[1].reason_codes = ['REQUIRED_TASK_MISSING'];
  assert.match(ui.render(), /alternative: mandatory check fails.*REQUIRED_TASK_MISSING/);
  ui.trial.customer_text = null; ui.trial.task_assessments = [];
  assert.match(ui.render(), /No customer answer was rendered for this trial/);
  assert.match(ui.render(), /No task assessment was recorded for this request/);
});

test('proposal summary uses the matching report and only the loaded request tasks', async () => {
  const ui = await requestSummary();
  ui.state.diagnostic = {id: 'unrelated', kind: 'DIAGNOSTIC', shift_id: ui.state.run.shift_id, trials: []};
  ui.trial.task_assessments.push({request_ordinal: 2, task_id: 'other-request', mandatory_pass: false, reason_codes: []});
  const summary = ui.render();
  assert.match(summary, /Harbour Atlas is available for collection\./);
  assert.doesNotMatch(summary, /other-request/, 'task evidence from another request was included');
  ui.state.diagnostic = ui.diagnostic; ui.state.stationView.latest_diagnostic = null;
  assert.match(ui.render(), /Harbour Atlas is available for collection\./);
});

test('saved-version request summaries keep their own output and linked checks', async () => {
  const ui = await requestSummary();
  ui.state.run.proposal_event_id = null; ui.state.run.artifact_version_id = 'ver-0003';
  ui.output.customer_answer = {display_text: 'Saved service answer.'};
  ui.state.checks = [{run_id: ui.state.run.id, observed_ref: ui.output.id, verdict: 'fail', reason_code: 'REQUIRED_TASK_MISSING'}];
  const summary = ui.render();
  assert.match(summary, /executed ver-0003/);
  assert.match(summary, /Saved service answer\./);
  assert.match(summary, /fail.*REQUIRED_TASK_MISSING/);
  assert.doesNotMatch(summary, /Harbour Atlas|coach proposal/);
});
