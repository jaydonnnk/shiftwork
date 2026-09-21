import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import test from 'node:test';

const modulePath = new URL('../../shiftwork/client/evidence.js', import.meta.url);
test('evidence joins by run and output identity, preserving every result and event', async () => {
  assert.ok(existsSync(modulePath), 'production evidence selection is not implemented');
  const { selectEvidence, bodyBytes } = await import(modulePath);
  const output = { id: 'r2-out-7', run_id: 'r2', request_ordinal: 7, body_base64: '/wDDqQ==' };
  const checks = [
    { id: 'wrong-run', run_id: 'r1', observed_ref: output.id },
    { id: 'c2', run_id: 'r2', observed_ref: output.id },
    { id: 'wrong-output', run_id: 'r2', observed_ref: 'r2-out-8' },
    { id: 'c1', run_id: 'r2', observed_ref: output.id },
  ];
  const derivation = { run_id: 'r2', request_ordinal: 7, observed_ref: output.id, check_id: 'c1' };
  const events = [
    { seq: 1, derivation: null },
    { seq: 2, derivation: { ...derivation, run_id: 'r1' } },
    { seq: 3, derivation },
    { seq: 4, derivation: { ...derivation, check_id: 'c2' } },
    { seq: 5, derivation: { ...derivation, request_ordinal: 8 } },
    { seq: 6, derivation: { ...derivation, check_id: 'unrelated' } },
    { seq: 7, derivation: { ...derivation, observed_ref: 'wrong' } },
  ];
  const selected = selectEvidence(output, checks, events);
  assert.deepEqual(selected.checks.map(c => c.id), ['c2', 'c1']);
  assert.deepEqual(selected.events.map(e => e.seq), [3, 4]);
  assert.deepEqual(Array.from(bodyBytes(output.body_base64)), [255, 0, 195, 169]);
  assert.deepEqual(selectEvidence(null, checks, events), { checks: [], events: [] });
});
