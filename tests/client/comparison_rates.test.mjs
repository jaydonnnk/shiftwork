import test from 'node:test';
import assert from 'node:assert/strict';
import * as evidence from '../../shiftwork/client/evidence.js';

function fixture() {
  const trials = [];
  for (let pair = 1; pair <= 3; pair++) for (const label of ['A', 'B']) {
    trials.push({candidate_label: label, request_count: 2, repetitions: [1, 2, 3].map(ordinal => ({
      run_id: `${label}-${pair}-${ordinal}`, state: 'COMPLETE',
      task_assessments: [1, 2].map(request_ordinal => ({request_ordinal, task_id: 'collection', mandatory_pass: true, reason_codes: []})),
      outputs: [1, 2].map(request_ordinal => ({request_ordinal, transport_error: null, body_base64: 'e30='})), observations: [],
    }))});
  }
  return {public_repetitions: 3, workloads: [{}, {}, {}], trials,
    repetition_summary: {candidates: ['A', 'B'].map(candidate_label => ({candidate_label, passed: 9, retained: 9, declared: 9}))}};
}

test('comparison rate counts each retained repetition and attributes its failed reply', () => {
  assert.equal(typeof evidence.comparisonRateLines, 'function', 'a retained comparison rate must be implemented');
  const data = fixture(), failed = data.trials[0].repetitions[1];
  failed.task_assessments[0].mandatory_pass = false;
  failed.task_assessments[0].reason_codes = ['REQUIRED_TASK_MISSING'];
  failed.observations = [{kind: 'INFERENCE_RESULT', public_payload_json: {request_ordinal: 1, finish_reason: 'length', plan_failure: 'SCHEMA_INVALID'}}];
  data.repetition_summary.candidates[0].passed = 8;
  const lines = evidence.comparisonRateLines(data);
  assert.match(lines[0], /A: 8 of 9 public repetitions pass mandatory checks/, 'the displayed rate must count the failed repetition');
  assert.match(lines[0], /cut off 1, invalid plan 0, omitted task 0/, 'the cut-off cause must come from the same retained reply');
  assert.match(lines[1], /B: 9 of 9 public repetitions pass mandatory checks/);
});

test('comparison rate refuses a fabricated rate and duplicate run identity', () => {
  assert.equal(typeof evidence.comparisonRateLines, 'function');
  const data = fixture(); data.repetition_summary.candidates[0].passed = 8;
  assert.throws(() => evidence.comparisonRateLines(data), /disagrees/, 'a fabricated comparison rate must be refused');
  const duplicate = fixture(); duplicate.trials[0].repetitions[1].run_id = duplicate.trials[0].repetitions[0].run_id;
  assert.throws(() => evidence.comparisonRateLines(duplicate), /identity/, 'one run cannot supply two repetitions');
});

test('comparison rate refuses an empty retained capture counted as passing', () => {
  const data = fixture(); data.trials[0].repetitions[1].outputs[0].body_base64 = '';
  assert.throws(() => evidence.comparisonRateLines(data), /disagrees/, 'an empty retained capture cannot count as passing');
});

test('comparison rate distinguishes a missing repetition from a mandatory failure', () => {
  assert.equal(typeof evidence.comparisonRateLines, 'function');
  const data = fixture(); data.trials[0].repetitions.pop();
  data.repetition_summary.candidates[0].retained = 8;
  data.repetition_summary.candidates[0].passed = 8;
  assert.match(evidence.comparisonRateLines(data)[0], /8 retained; 1 missing/, 'a missing repetition must remain visible');
});

test('comparison causes distinguish invalid, omitted, unknown and other failures', () => {
  assert.equal(typeof evidence.comparisonRateLines, 'function');
  const data = fixture(); const rows = data.trials.filter(row => row.candidate_label === 'A').flatMap(row => row.repetitions);
  for (const row of rows.slice(0, 4)) {
    row.task_assessments[0].mandatory_pass = false;
    row.task_assessments[0].reason_codes = ['REQUIRED_TASK_MISSING'];
  }
  rows[0].observations = [{kind: 'INFERENCE_RESULT', public_payload_json: {request_ordinal: 1, plan_failure: 'SCHEMA_INVALID'}}];
  rows[1].observations = [{kind: 'INFERENCE_RESULT', public_payload_json: {request_ordinal: 1, plan: [{task_type: 'price'}]}}];
  rows[2].observations = [{kind: 'INFERENCE_RESULT', public_payload_json: {request_ordinal: 2, finish_reason: 'length'}}];
  rows[3].task_assessments[0].reason_codes = ['UNSUPPORTED_CLAIM'];
  data.repetition_summary.candidates[0].passed = 5;
  assert.match(evidence.comparisonRateLines(data)[0], /cut off 0, invalid plan 1, omitted task 1, other check failure 1, cause not retained 1/,
    'failure categories must be attributable and must not double count a repetition');
});

test('a failed public execution stays distinct from model check failures', () => {
  const data = fixture(); data.trials[0].repetitions[1].state = 'FAILED';
  data.repetition_summary.candidates[0].passed = 8;
  assert.match(evidence.comparisonRateLines(data)[0], /execution incomplete 1/,
    'a driver failure must not be attributed to model task omission');
});

test('client refuses a failed mandatory row counted as a pass', () => {
  const data = fixture(); data.trials[0].repetitions[1].task_assessments[0].mandatory_pass = false;
  assert.throws(() => evidence.comparisonRateLines(data), /disagrees/, 'a failed mandatory row cannot count as passing');
});
test('client refuses missing capture ordinals counted as a pass', () => {
  const data = fixture(); data.trials[0].repetitions[1].outputs.pop();
  assert.throws(() => evidence.comparisonRateLines(data), /disagrees/, 'a missing capture cannot count as passing');
});
test('client refuses a failed execution counted as a pass', () => {
  const data = fixture(); data.trials[0].repetitions[1].state = 'FAILED';
  assert.throws(() => evidence.comparisonRateLines(data), /disagrees/, 'a failed execution cannot count as passing');
});
test('client refuses an unexecuted reservation counted as retained evidence', () => {
  const data = fixture(), row = data.trials[0].repetitions[1];
  row.state = 'FAILED'; row.outputs = []; row.observations = []; row.task_assessments = [];
  data.repetition_summary.candidates[0].passed = 8;
  assert.throws(() => evidence.comparisonRateLines(data), /disagrees/, 'an unexecuted reservation cannot count as retained evidence');
});
test('client refuses more repetitions than the frozen plan', () => {
  const data = fixture();
  data.trials[0].repetitions.push({...data.trials[0].repetitions[0], run_id: 'extra-run'});
  data.repetition_summary.candidates[0].passed = 10; data.repetition_summary.candidates[0].retained = 10;
  assert.throws(() => evidence.comparisonRateLines(data), /disagrees/, 'retained repetitions cannot exceed the frozen plan');
});
test('client refuses a repetition without a run identity', () => {
  const data = fixture(); data.trials[0].repetitions[1].run_id = null;
  assert.throws(() => evidence.comparisonRateLines(data), /identity/, 'a missing run identity must be refused');
});
