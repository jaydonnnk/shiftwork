import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';

const url = new URL('../../shiftwork/client/workplace-view.js', import.meta.url);
async function api() {
  assert.ok(existsSync(url), 'The engine-free workplace projection is missing');
  if (process.env.WORKPLACE_VIEW_SOURCE) return import('data:text/javascript;base64,' + process.env.WORKPLACE_VIEW_SOURCE);
  return import(url);
}
export function input() {
  return {
    slug: 'bookshop', loadedShiftId: 'shift-1', generation: 2, intent: 3,
    loadState: 'ready', inspection: { mode: 'current', historicalRunId: null },
    activeStation: 'customers', selectedOutputId: 'output-1', ledgerStatus: 'VALID',
    board: { engagement_slug: 'bookshop', latest_shift: { id: 'shift-1', state: 'OPEN' },
      latest_saved_version_id: 'saved-3', draft_base_version_id: 'base-0',
      operating_selection: { id: 'choice-1', kind: 'LEARNER_CHOICE', selected_version_id: 'selected-2',
        selected_content_hash: 'hash-2', comparison_id: 'comparison-1', retained_alternative_version_id: 'alt-4',
        requirement_set_hash: 'requirements-1', state: 'VALID', rationale: 'PRIVATE_RATIONALE' },
      chain_status: 'VALID', ledger_event_count: 0, ledger_totals: {}, incidents: [] },
    operatingVersion: { id: 'selected-2', content_hash: 'hash-2', source: 'PRIVATE_SOURCE' },
    run: { id: 'run-1', shift_id: 'shift-1', artifact_version_id: 'executed-5', selection_id: null,
      state: 'FINALIZED', purpose: 'EXPERIMENT', evidence_mode: 'RECORDED_INSPECTION' },
    outputs: [{ id: 'output-1', run_id: 'run-1', request_ordinal: 1, body_base64: 'PRIVATE_BODY', request_text: 'PRIVATE_REQUEST' }],
    checks: [{ id: 'check-1', run_id: 'run-1', observed_ref: 'output-1', verdict: 'fail', reason_code: 'TASK_MISSED', expected_ref: 'PRIVATE_EXPECTED' }],
    events: [], candidates: { A: null, B: null }, stationView: null, diagnostic: null, comparison: null,
  };
}
test('projection_separates_saved_selected_executed', async () => {
  const { projectWorkplace } = await api(); const v = projectWorkplace(input());
  assert.equal(v.saved.latestVersionId, 'saved-3');
  assert.equal(v.operating.versionId, 'selected-2');
  assert.equal(v.run.versionId, 'executed-5');
  assert.equal(v.run.purpose, 'EXPERIMENT');
  assert.equal(v.consistency, 'linked');
});
test('finalized_is_not_success', async () => {
  const { projectWorkplace } = await api();
  assert.deepEqual(projectWorkplace(input()).evidence.checks, [{ id: 'check-1', verdict: 'fail', reasonCode: 'TASK_MISSED' }]);
  const missing = input(); missing.checks = [];
  assert.equal(projectWorkplace(missing).evidence.completeness, 'missing');
});
test('empty_first_shift_has_no_fabricated_identity', async () => {
  const { projectWorkplace } = await api(); const i = input();
  i.loadedShiftId = null; i.board.latest_shift = null; i.board.operating_selection = null;
  i.run = null; i.outputs = []; i.checks = []; i.selectedOutputId = null;
  const v = projectWorkplace(i);
  assert.equal(v.context.shiftId, null); assert.equal(v.run, null); assert.equal(v.operating, null);
});
for (const [name, change] of [
  ['board_owner', i => { i.board.engagement_slug = 'northline'; }],
  ['shift_owner', i => { i.loadedShiftId = 'old-shift'; }],
  ['selected_version', i => { i.operatingVersion.id = 'wrong'; }],
  ['selected_hash', i => { i.operatingVersion.content_hash = 'wrong'; }],
  ['run_shift', i => { i.run.shift_id = 'wrong'; }],
  ['output_run', i => { i.outputs[0].run_id = 'wrong'; }],
  ['check_run', i => { i.checks[0].run_id = 'wrong'; }],
  ['station_shift', i => { i.stationView = { shift_id: 'old-shift', investigations: [{id:'old-entry'}] }; }],
  ['ledger_status', i => { i.ledgerStatus = 'BROKEN'; }],
  ['board_status', i => { i.board.chain_status = 'BROKEN'; }],
  ['ledger_count', i => { i.board.ledger_event_count = 1; }],
  ['ledger_histogram', i => { i.board.ledger_totals = { SALE_COMPLETED: 1 }; }],
]) test(`multi_read_conflict_${name}`, async () => {
  const { projectWorkplace } = await api(); const i = input(); change(i);
  assert.equal(projectWorkplace(i).consistency, 'conflict', `${name} disagreement was accepted`);
});
test('optional_selected_source_is_incomplete_not_conflict', async () => {
  const { projectWorkplace } = await api(); const i = input(); i.operatingVersion = null;
  assert.equal(projectWorkplace(i).consistency, 'incomplete');
});
test('historical_run_can_belong_to_an_earlier_shift', async () => {
  const { projectWorkplace } = await api(); const i = input(); i.run.shift_id = 'old-shift';
  i.inspection = { mode: 'history', historicalRunId: 'run-1' };
  assert.equal(projectWorkplace(i).consistency, 'linked');
});
test('nominated_legacy_first_choice_inspection_is_not_a_current_operation', async () => {
  const { projectWorkplace } = await api(); const i=input();
  i.run.shift_id='prior-shift'; i.run.purpose='LEGACY_OPERATION';
  i.board.latest_shift.opening_mode='LEGACY_FIRST_CHOICE'; i.board.latest_run={...i.run};
  i.board.operating_selection=null; i.operatingVersion=null;
  const v=projectWorkplace(i); assert.equal(v.consistency,'linked'); assert.equal(v.run.purpose,'LEGACY_OPERATION');
  assert.equal(v.operating,null);
});
for(const relation of ['purpose','opening_mode','id','shift','version']) test(`legacy_nomination_${relation}_must_match`,async()=>{
  const {projectWorkplace}=await api();const i=input();i.run.shift_id='prior-shift';i.run.purpose='LEGACY_OPERATION';
  i.board.latest_shift.opening_mode='LEGACY_FIRST_CHOICE';i.board.latest_run={...i.run};i.board.operating_selection=null;i.operatingVersion=null;
  if(relation==='purpose') i.run.purpose='EXPERIMENT';
  if(relation==='opening_mode') i.board.latest_shift.opening_mode='STANDARD';
  if(relation==='id') i.board.latest_run.id='other-run';
  if(relation==='shift') i.board.latest_run.shift_id='other-shift';
  if(relation==='version') i.board.latest_run.artifact_version_id='other-version';
  assert.equal(projectWorkplace(i).consistency,'conflict',`Legacy ${relation} disagreement was accepted`);
});
test('history_run_identity_must_match',async()=>{
  const {projectWorkplace}=await api();const i=input();i.inspection={mode:'history',historicalRunId:'other-run'};
  assert.equal(projectWorkplace(i).consistency,'conflict','Wrong historical run was accepted');
});
for(const relation of ['selection','version']) test(`operation_${relation}_must_match`,async()=>{
  const {projectWorkplace}=await api();const i=input();i.run.purpose='OPERATION';i.run.selection_id='choice-1';i.run.artifact_version_id='selected-2';
  if(relation==='selection') i.run.selection_id='other-choice'; else i.run.artifact_version_id='other-version';
  assert.equal(projectWorkplace(i).consistency,'conflict',`Operational ${relation} disagreement was accepted`);
});
for(const relation of ['run','output','check']) test(`incident_${relation}_must_match`,async()=>{
  const {projectWorkplace}=await api();const i=input();
  const link={run_id:'run-1',observed_ref:'output-1',check_id:'check-1',request_ordinal:1,verdict:'fail'};
  i.events=[{seq:1,hash:'event-1',event_type:'INCIDENT_OPENED',synthetic:true,derivation:link}];
  i.board.ledger_event_count=1;i.board.ledger_totals={INCIDENT_OPENED:1};
  i.board.incidents=[{id:'incident-1',opened_event_seq:1,opening_run_id:'run-1',failing_output_ref:'output-1',check_result_id:'check-1',state:'OPEN',reason_code:'TASK_MISSED'}];
  if(relation==='run') link.run_id='other-run';if(relation==='output') link.observed_ref='other-output';if(relation==='check') link.check_id='other-check';
  assert.equal(projectWorkplace(i).consistency,'conflict',`Incident ${relation} disagreement was accepted`);
});
test('projection_whitelists_scene_fields_and_detaches_arrays', async () => {
  const { projectWorkplace } = await api(); const i = input(); i.diagnostic = diagnostic('DIAGNOSTIC', 'COMPLETE', []); const v = projectWorkplace(i);
  assert.deepEqual(Object.keys(v).sort(), ['schemaVersion','context','station','shiftState','operating','saved','run','evidence','investigation','tests','consequences','inheritance','consistency'].sort());
  const needles = ['PRIVATE_RATIONALE','PRIVATE_SOURCE','PRIVATE_BODY','PRIVATE_REQUEST','PRIVATE_EXPECTED','PRIVATE_TREATMENT','PRIVATE_CUSTOMER_TEXT','PRIVATE_REASON', '/Users/private/secret', '\\Users\\private\\secret'];
  const scan = text => needles.filter(n => text.includes(n) || text.includes(JSON.stringify(n).slice(1,-1)) || text.includes(n.replaceAll('\\','/')));
  for (const needle of needles) assert.ok(scan(JSON.stringify({ value: needle })).includes(needle), 'serialized scanner cannot match its needle');
  assert.deepEqual(scan(JSON.stringify(v)), []);
  i.checks[0].verdict = 'pass'; assert.equal(v.evidence.checks[0].verdict, 'fail');
});
test('station_focus_is_the_only_transition_without_a_diagnostic_update', async () => {
  const { projectWorkplace, diffWorkplace } = await api(); const i = input(); const a = projectWorkplace(i);
  assert.deepEqual(diffWorkplace(null, a), []); assert.deepEqual(diffWorkplace(a,a), []);
  i.activeStation = 'evaluator'; const b = projectWorkplace(i);
  assert.deepEqual(diffWorkplace(a,b), [{ key: 'station:evaluator', kind: 'station-focus', stationId: 'evaluator', publicRefs: [] }]);
  i.inspection = { mode: 'history', historicalRunId: 'run-1' };
  assert.deepEqual(diffWorkplace(a, projectWorkplace(i)), []);
});

export function diagnostic(kind = 'DIAGNOSTIC', trialState = 'RUNNING', missing = ['pending capture']) {
  return { id: 'experiment-diag-1', shift_id: 'shift-1', kind, context_evidence_class: 'TRUSTED_LOCAL',
    context_hash: 'context-diag', declared_treatment: 'PRIVATE_TREATMENT', state: 'RUNNING',
    eligible: false, eligibility_reason: 'PRIVATE_REASON',
    candidates: [{ label: 'A', artifact_version_id: 'diag-version-9', artifact_content_hash: 'diag-hash-9' }],
    trials: [{ ordinal: 1, candidate_label: 'A', run_id: 'diag-run-1', artifact_version_id: 'diag-version-9',
      state: trialState, evidence_mode: 'TRUSTED_LOCAL', missing_evidence: missing,
      outputs: [{ request_text: 'PRIVATE_REQUEST', body_base64: 'PRIVATE_BODY' }],
      customer_text: 'PRIVATE_CUSTOMER_TEXT', task_assessments: [], observations: [] }] };
}
test('diagnostic_purpose_guard_rejects_other_kinds', async () => {
  const { projectWorkplace } = await api(); const i = input();
  i.diagnostic = diagnostic('QUALIFYING_COMPARISON');
  assert.equal(projectWorkplace(i).tests.diagnostic, null, 'a comparison was accepted into the diagnostic slot');
});
test('comparison_purpose_guard_rejects_other_kinds', async () => {
  const { projectWorkplace } = await api(); const i = input();
  i.comparison = diagnostic('DIAGNOSTIC');
  assert.equal(projectWorkplace(i).tests.comparison, null, 'a diagnostic was accepted into the comparison slot');
});
test('later_purpose_guard_rejects_other_kinds', async () => {
  const { projectWorkplace } = await api(); const i = input();
  i.stationView = { shift_id: 'shift-1', latest_experiment: diagnostic('QUALIFYING_COMPARISON') };
  const v = projectWorkplace(i);
  assert.equal(v.tests.later, null, 'a qualifying comparison was accepted into the later slot');
});
test('experiment_never_moves_operation_wall', async () => {
  const { projectWorkplace } = await api();
  const plain = projectWorkplace(input());
  for (const change of [
    i => { i.diagnostic = diagnostic('DIAGNOSTIC', 'COMPLETE', []); },
    i => { i.comparison = diagnostic('QUALIFYING_COMPARISON', 'COMPLETE', []); i.stationView = { shift_id: 'shift-1', latest_experiment: i.comparison }; },
    i => { i.stationView = { shift_id: 'shift-1', latest_experiment: diagnostic('LATER_CONDITION_COMPARISON', 'COMPLETE', []) }; },
  ]) {
    const i = input(); change(i); const v = projectWorkplace(i);
    assert.deepEqual(v.operating, plain.operating, 'an experiment moved the operating selection');
    assert.deepEqual(v.consequences, plain.consequences, 'an experiment moved the consequence wall');
    assert.deepEqual(v.inheritance, plain.inheritance, 'an experiment changed inheritance');
    assert.equal(v.consistency, 'linked');
  }
});
test('diagnostic_cannot_qualify_selection', async () => {
  const { projectWorkplace } = await api(); const i = input();
  i.board.operating_selection.comparison_id = 'experiment-diag-1';
  i.diagnostic = diagnostic('DIAGNOSTIC', 'COMPLETE', []);
  assert.equal(projectWorkplace(i).consistency, 'conflict', 'a diagnostic was accepted as the selection comparison');
});
test('diagnostic_cannot_derive_ledger_event', async () => {
  const { projectWorkplace } = await api(); const i = input();
  i.diagnostic = diagnostic('DIAGNOSTIC', 'COMPLETE', []);
  i.events = [{ seq: 1, hash: 'event-diag', event_type: 'SALE_COMPLETED', synthetic: true,
    derivation: { run_id: 'diag-run-1', check_id: 'check-1', observed_ref: 'output-1', request_ordinal: 1, verdict: 'pass' } }];
  i.board.ledger_event_count = 1; i.board.ledger_totals = { SALE_COMPLETED: 1 };
  assert.equal(projectWorkplace(i).consistency, 'conflict', 'a diagnostic trial run derived a ledger event');
});
test('diagnostic_test_update_is_continuous_and_duplicate_quiet', async () => {
  const { projectWorkplace, diffWorkplace } = await api();
  const running = input(); running.diagnostic = diagnostic('DIAGNOSTIC', 'RUNNING', ['pending capture']);
  const complete = input(); complete.diagnostic = diagnostic('DIAGNOSTIC', 'COMPLETE', []);
  const a = projectWorkplace(running), b = projectWorkplace(complete);
  const expected = [{ key: 'test:diagnostic:experiment-diag-1|RUNNING|COMPLETE|diag-run-1|0', kind: 'test-update',
    stationId: 'compare', publicRefs: ['experiment-diag-1', 'diag-run-1', 'diag-version-9'] }];
  assert.deepEqual(diffWorkplace(a, b), expected);
  assert.deepEqual(diffWorkplace(b, b), [], 'a duplicate accepted view produced a transition');
  assert.deepEqual(diffWorkplace(b, a), [{ key: 'test:diagnostic:experiment-diag-1|RUNNING|RUNNING|diag-run-1|1',
    kind: 'test-update', stationId: 'compare', publicRefs: ['experiment-diag-1', 'diag-run-1', 'diag-version-9'] }]);
  assert.deepEqual(diffWorkplace(a, projectWorkplace(Object.assign(input(), { diagnostic: null }))), [], 'a removed diagnostic produced a transition');
});
test('diagnostic_update_survives_pending_evidence_becoming_linked', async () => {
  const { projectWorkplace, diffWorkplace } = await api();
  const pending = input(); pending.diagnostic = diagnostic('DIAGNOSTIC', 'RUNNING', ['pending capture']); pending.checks = [];
  const linked = input(); linked.diagnostic = diagnostic('DIAGNOSTIC', 'COMPLETE', []);
  const a = projectWorkplace(pending), b = projectWorkplace(linked);
  assert.equal(a.evidence.completeness, 'missing'); assert.equal(b.evidence.completeness, 'linked');
  assert.equal(diffWorkplace(a, b).filter(item => item.kind === 'test-update').length, 1, 'a pending evidence route suppressed the test update');
});
test('diagnostic_history_and_context_changes_are_quiet', async () => {
  const { projectWorkplace, diffWorkplace } = await api();
  const current = input(); current.diagnostic = diagnostic('DIAGNOSTIC', 'RUNNING', ['pending capture']);
  const a = projectWorkplace(current);
  const history = input(); history.diagnostic = diagnostic('DIAGNOSTIC', 'COMPLETE', []);
  history.inspection = { mode: 'history', historicalRunId: 'run-1' };
  assert.deepEqual(diffWorkplace(a, projectWorkplace(history)), [], 'a history change emitted a fresh test update');
  const otherShift = input(); otherShift.loadedShiftId = null; otherShift.board.latest_shift = null;
  otherShift.diagnostic = diagnostic('DIAGNOSTIC', 'COMPLETE', []);
  assert.deepEqual(diffWorkplace(a, projectWorkplace(otherShift)), [], 'a context change emitted a fresh test update');
});
test('diagnostic_history_test_update_is_continuous_within_the_same_inspection', async () => {
  const { projectWorkplace, diffWorkplace } = await api();
  const running = input(); running.inspection = { mode: 'history', historicalRunId: 'run-1' }; running.diagnostic = diagnostic('DIAGNOSTIC', 'RUNNING', ['pending capture']);
  const complete = input(); complete.inspection = { mode: 'history', historicalRunId: 'run-1' }; complete.diagnostic = diagnostic('DIAGNOSTIC', 'COMPLETE', []);
  const transitions = diffWorkplace(projectWorkplace(running), projectWorkplace(complete));
  assert.equal(transitions.filter(item => item.kind === 'test-update').length, 1, 'a stable historical inspection suppressed the test update');
  assert.equal(transitions.filter(item => item.kind === 'station-focus').length, 0, 'history navigation emitted focus motion');
});

export function comparison({ state = 'FINALIZED', outcome = 'COMPLETE', eligibleA = true, eligibleB = true,
  blockersA = [], blockersB = [], missing = [] } = {}) {
  const versions = { A: 'version-a', B: 'version-b' }, hashes = { A: 'hash-a', B: 'hash-b' };
  const metrics = label => ({ candidate_label: label, candidate_version_id: versions[label],
    public_denominator_requests: 6, useful_completions: 6, incorrect_outputs: 0,
    justified_refusals: 0, justified_referrals: 0, justified_clarifications: 0,
    unjustified_refusals: 0, unjustified_referrals: 0, unjustified_clarifications: 0,
    missing_outputs: 0, protected_denominator: 3, protected_passed: 3, protected_failed: 0,
    protected_missing: 0, service_calls: null, input_tokens: null, output_tokens: null,
    service_latency_ms: null, provisioning_latency_ms: null, cost_minor_units: null });
  const trials = [];
  for (let pair = 1; pair <= 3; pair += 1) for (const [index, label] of ['A', 'B'].entries()) {
    const ordinal = (pair - 1) * 2 + index + 1;
    const unavailable = missing.includes(ordinal);
    trials.push({ pair_ordinal: pair, execution_ordinal: ordinal, candidate_label: label,
      artifact_version_id: versions[label], artifact_content_hash: hashes[label],
      workload_id: `workload-${pair}`, request_count: 2, protected_request_count: 1,
      run_id: unavailable ? null : `run-${label.toLowerCase()}-${pair}`,
      state: unavailable ? 'RESERVED' : 'COMPLETE', evidence_mode: 'TRUSTED_LOCAL',
      outputs: [{ request_text: 'PRIVATE_REQUEST', body_base64: 'PRIVATE_BODY' }],
      missing_evidence: unavailable ? [`slot ${ordinal} has no capture`] : [],
      task_assessments: [], observations: [] });
  }
  const out = outcome === null ? null : { experiment_id: 'experiment-cmp-1', status: outcome,
    shared_public_denominator_requests: 6, candidate_metrics: [metrics('A'), metrics('B')],
    eligibility: [
      { candidate_label: 'A', candidate_version_id: 'version-a', eligible: eligibleA, blocking_reason_codes: blockersA },
      { candidate_label: 'B', candidate_version_id: 'version-b', eligible: eligibleB, blocking_reason_codes: blockersB },
    ], drift_fields: [], noncompletion_incidence_non_additive: true };
  return { id: 'experiment-cmp-1', shift_id: 'shift-1', kind: 'QUALIFYING_COMPARISON',
    investigation_id: 'investigation-1', declared_treatment: 'PRIVATE_TREATMENT',
    context_hash: 'context-cmp', context_evidence_class: 'TRUSTED_LOCAL',
    condition: { id: 'condition-1', kind: 'DEPENDENCY_OUTAGE', public_label: 'Dependency outage',
      content_hash: 'PRIVATE_CONDITION_HASH' }, observed_run_id: null,
    workloads: [{ id: 'workload-1', ordinal: 1, request_batch_hash: 'batch-1', request_count: 2 }],
    candidates: [{ label: 'A', artifact_version_id: 'version-a', artifact_content_hash: 'hash-a' },
      { label: 'B', artifact_version_id: 'version-b', artifact_content_hash: 'hash-b' }],
    trials, shared_public_denominator_requests: 6, protected_denominator_requests_per_candidate: 3,
    protected_counts: { A: { reserved: 3, captured: 3, missing: 0 }, B: { reserved: 3, captured: 3, missing: 0 } },
    outcome: out, eligible: true, eligibility_reason: 'PRIVATE_REASON', state };
}
function comparisonInput(options = {}) {
  const i = input(); i.board.operating_selection = null; i.operatingVersion = null;
  i.comparison = comparison(options); return i;
}
test('comparison_projection_carries_public_condition_denominators_and_metrics', async () => {
  const { projectWorkplace } = await api(); const v = projectWorkplace(comparisonInput());
  const summary = v.tests.comparison;
  assert.equal(summary.conditionLabel, 'Dependency outage');
  assert.equal(summary.sharedPublicDenominatorRequests, 6);
  assert.equal(summary.protectedDenominatorRequestsPerCandidate, 3);
  assert.equal(summary.missingSlots, 0);
  assert.equal(summary.incomparable, false);
  assert.equal(summary.candidates.length, 2);
  assert.deepEqual(summary.candidates.map(candidate => [candidate.label, candidate.versionId, candidate.contentHash, candidate.eligible]),
    [['A', 'version-a', 'hash-a', true], ['B', 'version-b', 'hash-b', true]]);
  assert.equal(summary.candidates[0].metrics.usefulCompletions, 6);
  assert.equal(summary.trials.length, 6);
  assert.deepEqual([summary.trials[0].ordinal, summary.trials[0].pairOrdinal, summary.trials[0].candidateLabel], [1, 1, 'A']);
  assert.equal(summary.trials[5].ordinal, 6); assert.equal(summary.trials[5].candidateLabel, 'B');
});
test('comparison_projection_keeps_unknown_costs_unknown', async () => {
  const { projectWorkplace } = await api(); const i = comparisonInput();
  i.comparison.outcome.candidate_metrics[0].cost_minor_units = null;
  i.comparison.outcome.candidate_metrics[0].service_calls = null;
  const metrics = projectWorkplace(i).tests.comparison.candidates[0].metrics;
  assert.strictEqual(metrics.costMinorUnits, null, 'an unknown cost was reported as a number');
  assert.strictEqual(metrics.serviceCalls, null, 'an unknown call count was reported as zero');
});
test('comparison_projection_counts_missing_slots', async () => {
  const { projectWorkplace } = await api(); const v = projectWorkplace(comparisonInput({ missing: [6] }));
  assert.equal(v.tests.comparison.missingSlots, 1, 'a missing comparison slot was not counted');
  assert.equal(v.tests.comparison.trials[5].missingEvidenceCount, 1, 'a missing slot hid its missing evidence');
  assert.equal(v.tests.comparison.trials[5].runId, null);
});
test('comparison_projection_reports_blockers_and_incomparable_evidence', async () => {
  const { projectWorkplace } = await api();
  const blocked = projectWorkplace(comparisonInput({ state: 'FINALIZED', outcome: 'NOT_COMPARABLE',
    eligibleA: false, eligibleB: false, blockersA: ['MANDATORY_TASK_FAILED'], blockersB: ['MISSING_CAPTURE'] }));
  assert.equal(blocked.tests.comparison.outcomeStatus, 'NOT_COMPARABLE');
  assert.equal(blocked.tests.comparison.incomparable, true, 'an incomparable comparison was reported as comparable');
  assert.deepEqual(blocked.tests.comparison.candidates.map(candidate => candidate.blockingReasonCodes),
    [['MANDATORY_TASK_FAILED'], ['MISSING_CAPTURE']], 'comparison blockers were hidden');
  const invalidated = projectWorkplace(comparisonInput({ state: 'INVALIDATED', outcome: 'NOT_COMPARABLE',
    eligibleA: false, eligibleB: false, blockersA: ['EXPOSURE_RETIRED'] }));
  assert.equal(invalidated.tests.comparison.incomparable, true, 'an invalidated comparison was reported as comparable');
});
test('comparison_projection_has_no_default_winner_or_preselection', async () => {
  const { projectWorkplace } = await api(); const v = projectWorkplace(comparisonInput());
  assert.equal(v.operating, null, 'a completed comparison selected a version');
  assert.equal(Object.hasOwn(v.tests.comparison, 'winner'), false, 'the projection implied a default winner');
  for (const candidate of v.tests.comparison.candidates) {
    assert.equal(Object.hasOwn(candidate, 'selected'), false, 'a candidate was preselected');
    assert.equal(Object.hasOwn(candidate.metrics, 'score'), false, 'the projection invented a score');
  }
});
test('comparison_selection_binding_accepts_the_public_choice', async () => {
  const { projectWorkplace } = await api(); const i = comparisonInput();
  i.board.operating_selection = { id: 'choice-cmp', kind: 'LEARNER_CHOICE', selected_version_id: 'version-a',
    selected_content_hash: 'hash-a', comparison_id: 'experiment-cmp-1', retained_alternative_version_id: 'version-b',
    requirement_set_hash: 'requirements-1', state: 'VALID', rationale: 'PRIVATE_RATIONALE' };
  i.operatingVersion = { id: 'version-a', content_hash: 'hash-a', source: 'PRIVATE_SOURCE' };
  assert.equal(projectWorkplace(i).consistency, 'linked', 'a public selection identity was rejected');
});
test('comparison_candidate_label_must_be_unique', async () => {
  const { projectWorkplace } = await api(); const i = comparisonInput();
  i.comparison.candidates.push({ label: 'A', artifact_version_id: 'version-a', artifact_content_hash: 'hash-a' });
  assert.equal(projectWorkplace(i).consistency, 'conflict', 'a duplicate comparison candidate label was accepted');
});
test('comparison_trial_must_bind_the_exact_candidate_version', async () => {
  const { projectWorkplace } = await api(); const i = comparisonInput();
  i.comparison.trials[0].artifact_version_id = 'version-b';
  assert.equal(projectWorkplace(i).consistency, 'conflict', 'a comparison trial carried a different candidate version');
});
test('comparison_selection_must_bind_one_candidate', async () => {
  const { projectWorkplace } = await api(); const i = comparisonInput();
  i.board.operating_selection = { id: 'choice-cmp', kind: 'LEARNER_CHOICE', selected_version_id: 'version-x',
    selected_content_hash: 'hash-x', comparison_id: 'experiment-cmp-1', retained_alternative_version_id: 'version-b',
    requirement_set_hash: 'requirements-1', state: 'VALID', rationale: 'PRIVATE_RATIONALE' };
  i.operatingVersion = { id: 'version-x', content_hash: 'hash-x', source: 'PRIVATE_SOURCE' };
  assert.equal(projectWorkplace(i).consistency, 'conflict', 'a selection cited a version outside its comparison');
});
test('comparison_selection_content_hash_must_match', async () => {
  const { projectWorkplace } = await api(); const i = comparisonInput();
  i.board.operating_selection = { id: 'choice-cmp', kind: 'LEARNER_CHOICE', selected_version_id: 'version-a',
    selected_content_hash: 'hash-wrong', comparison_id: 'experiment-cmp-1', retained_alternative_version_id: 'version-b',
    requirement_set_hash: 'requirements-1', state: 'VALID', rationale: 'PRIVATE_RATIONALE' };
  i.operatingVersion = { id: 'version-a', content_hash: 'hash-wrong', source: 'PRIVATE_SOURCE' };
  assert.equal(projectWorkplace(i).consistency, 'conflict', 'a selection content hash did not match its comparison candidate');
});
test('comparison_selection_retained_alternative_must_match', async () => {
  const { projectWorkplace } = await api(); const i = comparisonInput();
  i.board.operating_selection = { id: 'choice-cmp', kind: 'LEARNER_CHOICE', selected_version_id: 'version-a',
    selected_content_hash: 'hash-a', comparison_id: 'experiment-cmp-1', retained_alternative_version_id: 'version-x',
    requirement_set_hash: 'requirements-1', state: 'VALID', rationale: 'PRIVATE_RATIONALE' };
  i.operatingVersion = { id: 'version-a', content_hash: 'hash-a', source: 'PRIVATE_SOURCE' };
  assert.equal(projectWorkplace(i).consistency, 'conflict', 'a selection retained the wrong alternative');
});
test('comparison_update_is_continuous_and_duplicate_quiet', async () => {
  const { projectWorkplace, diffWorkplace } = await api();
  const running = projectWorkplace(comparisonInput({ state: 'RUNNING', outcome: null }));
  const complete = projectWorkplace(comparisonInput());
  const transitions = diffWorkplace(running, complete);
  const update = transitions.find(item => item.kind === 'comparison-update');
  assert.ok(update, 'a completed comparison emitted no comparison update');
  assert.equal(update.stationId, 'compare');
  assert.equal(update.key, 'comparison:experiment-cmp-1|FINALIZED|COMPLETE|0|A:eligible:;B:eligible:');
  assert.deepEqual(update.publicRefs, ['experiment-cmp-1', 'version-a', 'version-b']);
  assert.equal(transitions.some(item => item.kind === 'selection-update'), false, 'a comparison moved the operating plate');
  assert.deepEqual(diffWorkplace(complete, complete), [], 'a duplicate accepted view produced a comparison transition');
  assert.deepEqual(diffWorkplace(running, projectWorkplace(comparisonInput({ state: 'RUNNING', outcome: null }))), [], 'a duplicate running view produced a comparison transition');
  const without = comparisonInput(); without.comparison = null;
  assert.deepEqual(diffWorkplace(complete, projectWorkplace(without)), [], 'a removed comparison produced a transition');
});
test('comparison_blocker_transition_is_visible', async () => {
  const { projectWorkplace, diffWorkplace } = await api();
  const eligible = projectWorkplace(comparisonInput());
  const blocked = projectWorkplace(comparisonInput({ state: 'FINALIZED', outcome: 'NOT_COMPARABLE',
    eligibleA: false, eligibleB: false, blockersA: ['MANDATORY_TASK_FAILED'] }));
  const update = diffWorkplace(eligible, blocked).find(item => item.kind === 'comparison-update');
  assert.ok(update?.key.includes('A:blocked:MANDATORY_TASK_FAILED'), 'a blocker change produced no comparison update');
});
test('selection_update_is_continuous_and_duplicate_quiet', async () => {
  const { projectWorkplace, diffWorkplace } = await api();
  const before = comparisonInput();
  const after = comparisonInput();
  after.board.operating_selection = input().board.operating_selection;
  after.operatingVersion = input().operatingVersion;
  const a = projectWorkplace(before), b = projectWorkplace(after);
  const update = diffWorkplace(a, b).find(item => item.kind === 'selection-update');
  assert.ok(update, 'a recorded choice emitted no selection update');
  assert.equal(update.stationId, 'service');
  assert.equal(update.key, 'selection:choice-1|selected-2|hash-2');
  assert.deepEqual(update.publicRefs, ['choice-1', 'selected-2']);
  assert.deepEqual(diffWorkplace(b, b), [], 'a duplicate accepted view produced a selection transition');
  assert.deepEqual(diffWorkplace(b, a), [], 'a removed selection produced a transition');
});
test('first_baseline_conflict_context_and_history_are_quiet', async () => {
  const { projectWorkplace, diffWorkplace } = await api();
  const completed = projectWorkplace(comparisonInput());
  assert.deepEqual(diffWorkplace(null, completed), [], 'a first accepted comparison emitted motion');
  const chosen = projectWorkplace(input());
  assert.deepEqual(diffWorkplace(null, chosen), [], 'a first accepted selection emitted motion');
  const conflict = comparisonInput();
  conflict.board.chain_status = 'BROKEN';
  conflict.board.operating_selection = { ...input().board.operating_selection, selected_version_id: 'version-a',
    selected_content_hash: 'hash-a', comparison_id: 'experiment-cmp-1', retained_alternative_version_id: 'version-b' };
  conflict.operatingVersion = { id: 'version-a', content_hash: 'hash-a', source: 'PRIVATE_SOURCE' };
  assert.deepEqual(diffWorkplace(completed, projectWorkplace(conflict)), [], 'a conflict emitted comparison motion');
  const history = comparisonInput(); history.inspection = { mode: 'history', historicalRunId: 'run-1' };
  assert.deepEqual(diffWorkplace(completed, projectWorkplace(history)), [], 'a history change emitted comparison motion');
  const otherShift = comparisonInput(); otherShift.loadedShiftId = null; otherShift.board.latest_shift = null;
  assert.deepEqual(diffWorkplace(completed, projectWorkplace(otherShift)), [], 'a context change emitted comparison motion');
});
test('diagnostics_remain_non_qualifying_and_do_not_move_comparison_or_selection', async () => {
  const { projectWorkplace, diffWorkplace } = await api();
  const i = comparisonInput(); i.diagnostic = diagnostic('DIAGNOSTIC', 'RUNNING', ['pending capture']);
  const a = projectWorkplace(i); i.diagnostic = diagnostic('DIAGNOSTIC', 'COMPLETE', []);
  const transitions = diffWorkplace(a, projectWorkplace(i));
  assert.equal(transitions.filter(item => item.kind === 'test-update').length, 1, 'a diagnostic update was weakened');
  assert.equal(transitions.filter(item => item.kind === 'comparison-update').length, 0, 'a diagnostic moved the comparison stands');
  assert.equal(transitions.filter(item => item.kind === 'selection-update').length, 0, 'a diagnostic moved the operating plate');
  assert.equal(projectWorkplace(i).tests.comparison.candidates.every(candidate => candidate.eligible), true);
});
test('comparison_projection_whitelists_private_material', async () => {
  const { projectWorkplace } = await api(); const i = comparisonInput();
  const v = projectWorkplace(i);
  const needles = ['PRIVATE_TREATMENT', 'PRIVATE_REQUEST', 'PRIVATE_BODY', 'PRIVATE_REASON',
    'PRIVATE_CONDITION_HASH', 'PRIVATE_RATIONALE', 'PRIVATE_SOURCE'];
  const scan = text => needles.filter(needle => text.includes(needle));
  for (const needle of needles) assert.ok(scan(JSON.stringify({ value: needle })).includes(needle), 'serialized scanner cannot match its needle');
  assert.deepEqual(scan(JSON.stringify(v)), [], 'private comparison material reached the scene projection');
});


async function hostFixture({ hidden=false, offscreen=false, delayed=false, failDuringCreate=false, moduleFailure=false, throwDuringCreate=false } = {}) {
  const node = () => {
    const target=new EventTarget(), listeners=new Map();
    const add=target.addEventListener.bind(target), remove=target.removeEventListener.bind(target);
    return Object.assign(target,{dataset:{},hidden:false,disabled:false,setAttribute(){},listeners,
      addEventListener(type,fn,...args) {if(!listeners.has(type)) listeners.set(type,new Set());listeners.get(type).add(fn);add(type,fn,...args);},
      removeEventListener(type,fn,...args) {listeners.get(type)?.delete(fn);remove(type,fn,...args);}});
  };
  const retry=node(), simpler=node(), status=node(), fallback=node(), controls={querySelector:s=>s.includes('retry')?retry:simpler};
  const container={clientWidth:680,clientHeight:380,parentElement:{dataset:{},parentElement:controls}};
  const document=Object.assign(node(),{hidden}); globalThis.document=document;
  globalThis.devicePixelRatio=1;
  const motion=Object.assign(node(),{matches:false}); globalThis.matchMedia=()=>motion;
  const observers=[];
  globalThis.ResizeObserver=class {constructor(fn){this.fn=fn;observers.push(this);}observe(){}disconnect(){this.closed=true;}};
  globalThis.IntersectionObserver=class {constructor(fn){this.fn=fn;observers.push(this);}observe(){this.fn([{isIntersecting:!offscreen}]);}disconnect(){this.closed=true;}};
  const releases=[]; let allocations=0, disposals=0, picked=0, imports=0, suspension=[];
  const handles=[];
  const module={createWorkplaceScene(options){if(throwDuringCreate) throw Error('injected construction failure');allocations++;const h={options,applied:[],transitions:[],apply(view,transitions=[]){h.applied.push(view);h.transitions.push(transitions);},resize(){},setSuspended(v){suspension.push(v);},setReducedMotion(){},dispose(){disposals++;}};handles.push(h);if(failDuringCreate) options.onFailure('shader-failed');return h;}};
  globalThis.__s29LoadScene=()=>{imports++;return moduleFailure?Promise.reject(Error('injected module failure')):delayed?new Promise(r=>releases.push(()=>r(module))):Promise.resolve(module);};
  let source=process.env.WORKPLACE_HOST_SOURCE ? Buffer.from(process.env.WORKPLACE_HOST_SOURCE,'base64').toString() : await readFile(new URL('../../shiftwork/client/workplace-host.js',import.meta.url),'utf8');
  source=source.replace("'./workplace-view.js'",JSON.stringify(url.href)).replace("await import('./workplace-scene.js')",'await globalThis.__s29LoadScene()');
  const {createWorkplaceHost}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
  const host=createWorkplaceHost({container,fallback,status,onStation(){picked++;}});
  const {projectWorkplace}=await api();const view=projectWorkplace(input());
  const accepted=(generation=2,v=view)=>({kind:'accepted',view:v,generation,intent:3,reason:'test'});
  const flush=async()=>{await new Promise(r=>setImmediate(r));};
  return {host,status,fallback,observers,document,view,accepted,flush,handles,
    listenerCount(owner) {return [...({visibility:document,motion,retry,simpler}[owner]).listeners.values()].reduce((n,set)=>n+set.size,0);},
    release(index=0){releases[index]?.();},visible(value){observers[1].fn([{isIntersecting:value}]);},
    get counts(){return {allocations,disposals,picked};},get importCount(){return imports;},get suspension(){return suspension;}};
}
test('host_loading_retains_one_scene_and_double_disposal_is_idempotent', async()=>{
  const f=await hostFixture();f.host.publish(f.accepted());await f.flush();
  f.host.publish({kind:'loading',context:f.view.context,generation:3});
  assert.equal(f.status.textContent,'Refreshing recorded state');assert.equal(f.counts.allocations,1);assert.equal(f.counts.disposals,0);
  f.host.publish(f.accepted(3));await f.flush();assert.equal(f.counts.allocations,1);
  f.host.dispose();f.host.dispose();assert.equal(f.counts.disposals,1);
  assert.ok(f.observers[0].closed,'Resize observer remains attached');assert.ok(f.observers[1].closed,'Intersection observer remains attached');
});
test('host_reset_cannot_accept_older_generation',async()=>{
  const f=await hostFixture();f.host.publish(f.accepted(4));await f.flush();
  f.host.publish({kind:'reset',context:f.view.context,reason:'error'});f.host.publish(f.accepted(3));await f.flush();
  assert.equal(f.counts.allocations,1,'Older generation mounted after reset');f.host.dispose();
});
function diagnosticSummary(trialState='RUNNING',missing=1) {
  return { id:'d1', shiftId:'shift-1', kind:'DIAGNOSTIC', state:'RUNNING', evidenceClass:'TRUSTED_LOCAL',
    contextHash:'context-diag', outcomeStatus:null, candidates:[], observedRunId:null,
    trials:[{ordinal:1,candidateLabel:'A',runId:'r1',versionId:'v1',state:trialState,evidenceMode:'TRUSTED_LOCAL',missingEvidenceCount:missing}] };
}
test('host_loading_retains_test_baseline_and_duplicate_is_quiet',async()=>{
  const f=await hostFixture();
  const base={...f.view,tests:{...f.view.tests,diagnostic:diagnosticSummary('RUNNING',1)}};
  f.host.publish(f.accepted(2,base));await f.flush();
  const scene=f.handles[0];
  f.host.publish({kind:'loading',context:base.context,generation:3});await f.flush();
  assert.equal(scene.transitions.length,0,'loading published a test transition');
  const next={...base,tests:{...base.tests,diagnostic:diagnosticSummary('COMPLETE',0)}};
  f.host.publish(f.accepted(3,next));await f.flush();
  assert.deepEqual(scene.transitions.at(-1),[{key:'test:diagnostic:d1|RUNNING|COMPLETE|r1|0',kind:'test-update',stationId:'compare',publicRefs:['d1','r1','v1']}],'accepted test update did not reach the scene');
  f.host.publish(f.accepted(3,next));await f.flush();
  assert.deepEqual(scene.transitions.at(-1),[],'duplicate accepted view produced a transition');
  f.host.publish({kind:'reset',context:base.context,reason:'error'});await f.flush();
  f.host.publish(f.accepted(4,next));await f.flush();
  assert.equal(f.counts.allocations,2,'error recovery did not remount once');
  assert.equal(f.handles[1].applied.length,0,'error recovery replayed a stale test update');
  f.host.dispose();
});
test('host_expanded_updates_advance_the_reference_without_replay',async()=>{
  const f=await hostFixture();
  const base={...f.view,tests:{...f.view.tests,diagnostic:diagnosticSummary('RUNNING',1)}};
  f.host.publish(f.accepted(2,base));await f.flush();
  f.host.setExpanded(true);
  const next={...base,tests:{...base.tests,diagnostic:diagnosticSummary('COMPLETE',0)}};
  f.host.publish(f.accepted(3,next));await f.flush();
  f.host.setExpanded(false);
  const scene=f.handles[0];
  assert.ok(f.suspension.includes(true)&&f.suspension.includes(false),'expanded suspension was not applied');
  f.host.publish(f.accepted(3,next));await f.flush();
  assert.deepEqual(scene.transitions.at(-1),[],'a duplicate after expansion replayed the suspended update');
  assert.equal(f.counts.allocations,1,'expanded updates remounted the scene');
  f.host.dispose();
});
for(const mode of ['hidden','offscreen','expanded']) test(`host_${mode}_import_completion_draws_nothing`,async()=>{
  const f=await hostFixture({delayed:true});f.host.publish(f.accepted());
  if(mode==='hidden') {f.document.hidden=true;f.document.dispatchEvent(new Event('visibilitychange'));}
  if(mode==='offscreen') f.visible(false);
  if(mode==='expanded') f.host.setExpanded(true);
  f.release();await f.flush();assert.equal(f.counts.allocations,0,`${mode} completion initialized graphics`);f.host.dispose();
});
test('host_stale_import_never_attaches_after_disposal',async()=>{
  const f=await hostFixture({delayed:true});f.host.publish(f.accepted());f.host.dispose();f.release();await f.flush();assert.equal(f.counts.allocations,0);
});
test('host_replaced_import_owner_cannot_allocate',async()=>{
  const f=await hostFixture({delayed:true});f.host.publish(f.accepted());
  f.host.publish({kind:'reset',context:f.view.context,reason:'context'});f.host.publish(f.accepted(3));
  f.release(0);await f.flush();assert.equal(f.counts.allocations,0,'Old import allocated into a newer mount');
  f.release(1);await f.flush();assert.equal(f.counts.allocations,1);f.host.dispose();
});
test('host_partial_initialization_failure_releases_returned_handle',async()=>{
  const f=await hostFixture({failDuringCreate:true});f.host.publish(f.accepted());await f.flush();
  assert.equal(f.counts.disposals,1,'Failed initialization leaked its returned handle');assert.equal(f.status.dataset.state,'unavailable');f.host.dispose();
});
test('host_old_pick_does_not_navigate_after_context_reset',async()=>{
  const f=await hostFixture();f.host.publish(f.accepted());await f.flush();const pick=f.handles[0].options.onPick;
  f.host.publish({kind:'reset',context:f.view.context,reason:'context'});pick('customers');assert.equal(f.counts.picked,0);f.host.dispose();
});
test('host_failure_stays_latched_and_retry_is_explicit',async()=>{
  const f=await hostFixture();f.host.publish(f.accepted());await f.flush();f.handles[0].options.onFailure('context-lost');
  f.host.publish({kind:'reset',context:f.view.context,reason:'history'});f.host.publish(f.accepted(3));await f.flush();
  assert.equal(f.status.dataset.state,'unavailable');assert.equal(f.counts.allocations,1);
  f.host.retry();await f.flush();assert.equal(f.counts.allocations,2);f.host.dispose();
});
test('host_retry_refuses_a_cached_module_failure',async()=>{
  const f=await hostFixture({moduleFailure:true});
  try {
    f.host.publish(f.accepted());await f.flush();assert.equal(f.importCount,1);
    assert.equal(f.status.dataset.state,'unavailable');
    f.host.retry();await f.flush();
    assert.equal(f.importCount,1,'Retry repeated a failed module import');
    assert.equal(f.counts.allocations,0);
  }finally{f.host.dispose();}
});
test('host_retry_accepts_the_newest_publication',async()=>{
  const f=await hostFixture();
  try {
    f.host.publish(f.accepted());await f.flush();f.handles[0].options.onFailure('context-lost');
    const newest={...f.view,station:'evaluator',run:{...f.view.run,id:'newer-run'}};
    f.host.publish(f.accepted(3,newest));await f.flush();assert.equal(f.counts.allocations,1);
    f.host.retry();await f.flush();
    assert.deepEqual(f.handles[1].options.view,newest,'Retry applied an older public view');
    assert.equal(f.counts.disposals,1,'Retry retained the failed scene');
  }finally{f.host.dispose();}
});
test('host_constructor_throw_is_latched_until_explicit_retry',async()=>{
  const f=await hostFixture({throwDuringCreate:true});
  try {
    f.host.publish(f.accepted());await f.flush();
    assert.equal(f.status.dataset.state,'unavailable','Thrown initialization did not fail the host');
    f.host.publish(f.accepted(3));await f.flush();assert.equal(f.importCount,1,'Initialization retried without user action');
    f.host.retry();await f.flush();assert.equal(f.importCount,2);assert.equal(f.status.dataset.state,'unavailable');
  }finally{f.host.dispose();}
});
for(const owner of ['visibility','motion','retry','simpler']) test(`host_disposes_${owner}_listener`,async()=>{
  const f=await hostFixture();f.host.publish(f.accepted());await f.flush();
  assert.equal(f.listenerCount(owner),1,`${owner} listener precondition missing`);
  f.host.dispose();f.host.dispose();
  assert.equal(f.listenerCount(owner),0,`Owned ${owner} listener remains attached`);
});
test('performance_receipt_guards_reject_separate_synthetic_faults',async()=>{
  const {verifyPerformance}=await import('./workplace_perf.mjs');
  const valid=()=>({width:1280,cold:[1,2,3,4,5].map(timeOrigin=>({timeOrigin,ms:2000})),samples:[1,2,3].map(()=>({intervals:[16,17],median:16,p95:17,maxTriangles:1000,maxCalls:20})),idle:0,estimatedBytes:1024});
  assert.doesNotThrow(()=>verifyPerformance(valid()));
  for(const [change,message] of [
    [r=>{r.cold[0].ms=3001;},'Cold graphics-ready budget missed'],
    [r=>{r.cold[0].timeOrigin=2;},'Cold starts reused an earlier document'],
    [r=>{r.samples[0].intervals=[];},'No real frame work was sampled'],
    [r=>{r.samples[0].p95=1000;},'Motion interval budget missed'],
    [r=>{r.samples[0].maxTriangles=45001;},'Triangle budget missed'],
    [r=>{r.samples[0].maxCalls=91;},'Draw-call budget missed'],
    [r=>{r.idle=1;},'Idle frame budget missed'],
    [r=>{r.estimatedBytes=49*1024**2;},'Estimated allocation budget missed'],
  ]) {const r=valid();change(r);assert.throws(()=>verifyPerformance(r),error=>error.message.includes(message));assert.doesNotThrow(()=>verifyPerformance(valid()));}
});
