import test from 'node:test';
import assert from 'node:assert/strict';
import * as story from '../../shiftwork/client/workplace-story.js';
import * as evidence from '../../shiftwork/client/evidence.js';

for (const [step, expected] of [[1, 1], [2, 2], [3, 2], [4, 3], [5, 4], [6, 4], [7, 5]]) {
  test(`approved action ${step} recommends panel ${expected}`, () => {
    assert.equal(typeof story.firstRunPanel, 'function', 'first-run grouping is available');
    assert.equal(story.firstRunPanel({step}), expected);
  });
}
for (const guide of [null, {}, {step: null}, {step: 0}, {step: 8}, {step: "toString"}, {step: "3"}]) test(`unknown guide stays unknown ${JSON.stringify(guide)}`, () => {
  assert.equal(typeof story.firstRunPanel, 'function', 'first-run grouping is available');
  assert.equal(story.firstRunPanel(guide), null);
});
test('five panel names preserve the approved sequence', () => {
  assert.deepEqual(story.FIRST_RUN_PANELS, ['Read the failure', 'Explain it', 'Compare repairs', 'Choose', 'Next shift']);
});
for (const [code, label] of [['RECORDED_INSPECTION', 'replayed recording'], ['ISOLATED_LIVE', 'ran live in a sandbox'],
  ['TRUSTED_LOCAL', 'ran locally with trusted test code'], [null, 'evidence unknown'], ['FUTURE_MODE', 'evidence unknown'], ['constructor', 'evidence unknown']]) {
  test(`evidence ${code} has the literal plain label`, () => {
    assert.equal(typeof evidence.evidenceLabel, 'function', 'evidence labels are available');
    assert.equal(evidence.evidenceLabel(code), label);
  });
}
