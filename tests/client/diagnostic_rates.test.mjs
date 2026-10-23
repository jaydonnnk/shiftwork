import test from 'node:test';
import assert from 'node:assert/strict';
import { diagnosticRateLines } from '../../shiftwork/client/evidence.js';

const experiment = () => ({public_repetitions: 2, repetition_summary: {
  retained_repetitions: 2, tasks: [{request_id: 'request-1', task_id: 'alternative', misses: 1, total: 2}],
}, trials: [
  {state: 'COMPLETE', task_assessments: [{request_id: 'request-1', task_id: 'alternative', reason_codes: []}]},
  {state: 'COMPLETE', task_assessments: [{request_id: 'request-1', task_id: 'alternative', reason_codes: ['REQUIRED_TASK_MISSING']}]},
]});

const reply = fields => ({kind: 'INFERENCE_RESULT', public_payload_json: {request_ordinal: 1, ...fields}});
const missing = observations => ({state: 'COMPLETE', observations, task_assessments: [
  {request_id: 'request-1', request_ordinal: 1, task_id: 'alternative', reason_codes: ['REQUIRED_TASK_MISSING']}]});

test('displayed miss rate agrees with retained assessments', () => {
  assert.deepEqual(diagnosticRateLines(experiment()), ['request-1: alternative task missing in 1 of 2 runs ' +
    '(reply cut off at the output limit in 0, invalid plan in 0, plan left the task out in 0, cause not retained in 1)']);
});
test('each missing task is attributed only to its own retained reply', () => {
  const data = experiment();
  data.public_repetitions = 5; data.repetition_summary.retained_repetitions = 5;
  data.repetition_summary.tasks[0] = {request_id: 'request-1', task_id: 'alternative', misses: 5, total: 5};
  data.trials = [
    missing([reply({finish_reason: 'length', plan: null, plan_failure: 'SCHEMA_INVALID'})]),
    missing([reply({finish_reason: 'stop', plan: null, plan_failure: 'TOOL_NOT_ALLOWED'})]),
    missing([reply({finish_reason: 'stop', plan: [{task_type: 'collection', tool_name: 'public_record_lookup'}], plan_failure: null})]),
    missing([reply({finish_reason: 'length', plan: null, plan_failure: 'SCHEMA_INVALID', request_ordinal: 2})]),
    missing([reply({finish_reason: 'stop', plan: [{task_type: 'alternative', tool_name: 'public_catalog_search'}], plan_failure: null})]),
  ];
  assert.deepEqual(diagnosticRateLines(data), ['request-1: alternative task missing in 5 of 5 runs ' +
    '(reply cut off at the output limit in 1, invalid plan in 1, plan left the task out in 1, cause not retained in 2)']);
});
test('a fabricated server rate is refused', () => {
  const data = experiment(); data.repetition_summary.tasks[0].misses = 0;
  assert.throws(() => diagnosticRateLines(data), /disagrees/);
});
test('a missing retained repetition is refused', () => {
  const data = experiment(); data.trials.pop();
  assert.throws(() => diagnosticRateLines(data), /retained/);
});
