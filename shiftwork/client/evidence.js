export function evidenceLabel(code) {
  switch (code) {
    case 'RECORDED_INSPECTION': return 'replayed recording';
    case 'ISOLATED_LIVE': return 'ran live in a sandbox';
    case 'TRUSTED_LOCAL': return 'ran locally with trusted test code';
    default: return 'evidence unknown';
  }
}

export function selectEvidence(output, checks, events) {
  if (!output) return { checks: [], events: [] };
  const linkedChecks = checks.filter(check => check.run_id === output.run_id && check.observed_ref === output.id);
  const checkIds = new Set(linkedChecks.map(check => check.id));
  return {
    checks: linkedChecks,
    events: events.filter(({ derivation: link }) => link && link.run_id === output.run_id &&
      link.request_ordinal === output.request_ordinal && link.observed_ref === output.id && checkIds.has(link.check_id)),
  };
}

export function bodyBytes(base64) {
  return Uint8Array.from(atob(base64), character => character.charCodeAt(0));
}

export function comparisonRateLines(experiment) {
  if (!experiment.repetition_summary) return [];
  const seen = new Set();
  return experiment.repetition_summary.candidates.map(summary => {
    const slots = experiment.trials.filter(trial => trial.candidate_label === summary.candidate_label);
    const rows = slots.flatMap(trial => (trial.repetitions ?? []).map(row => ({trial, row})));
    for (const {row} of rows) {
      if (!row.run_id || seen.has(row.run_id)) throw new Error('Comparison repetition identity is missing or duplicated.');
      seen.add(row.run_id);
    }
    const passed = rows.filter(({trial, row}) => row.state === 'COMPLETE' && row.task_assessments.length > 0 &&
      row.task_assessments.every(task => task.mandatory_pass) &&
      new Set(row.outputs.filter(output => output.transport_error === null && output.body_base64).map(output => output.request_ordinal)).size === trial.request_count).length;
    const retained = rows.filter(({row}) => ['COMPLETE', 'FAILED'].includes(row.state) && (row.outputs.length || row.observations.length)).length;
    const declared = experiment.public_repetitions * experiment.workloads.length;
    if (summary.passed !== passed || summary.retained !== retained || summary.declared !== declared || rows.length > declared) {
      throw new Error('Comparison rate disagrees with retained repetitions.');
    }
    const causes = {cut: 0, invalid: 0, omitted: 0, other: 0, unknown: 0, execution: 0};
    for (const {row} of rows) {
      const failures = row.task_assessments.filter(task => !task.mandatory_pass);
      if (row.state === 'FAILED' && (row.outputs.length || row.observations.length)) {
        causes.execution += 1;
        continue;
      }
      if (!failures.length) continue;
      const missing = failures.filter(task => task.reason_codes.includes('REQUIRED_TASK_MISSING'));
      const retainedCauses = missing.map(task => missCause(row, task));
      const cause = ['cut', 'invalid', 'omitted'].find(kind => retainedCauses.includes(kind))
        ?? (missing.length ? 'unknown' : 'other');
      causes[cause] += 1;
    }
    return `${summary.candidate_label}: ${passed} of ${declared} public repetitions pass mandatory checks; ${retained} retained; ${declared - retained} missing or unfinished ` +
      `(cut off ${causes.cut}, invalid plan ${causes.invalid}, omitted task ${causes.omitted}, other check failure ${causes.other}, cause not retained ${causes.unknown}, execution incomplete ${causes.execution})`;
  });
}

export function diagnosticRateLines(experiment) {
  const summary = experiment.repetition_summary;
  if (!summary) return [];
  const count = experiment.public_repetitions;
  if (summary.retained_repetitions !== count || experiment.trials.length !== count ||
      experiment.trials.some(trial => trial.state !== 'COMPLETE')) {
    throw new Error('Miss-rate summary has incomplete retained repetitions.');
  }
  return summary.tasks.map(row => {
    const assessments = experiment.trials.map(trial => trial.task_assessments.filter(
      task => task.request_id === row.request_id && task.task_id === row.task_id));
    const missed = experiment.trials.filter((trial, index) =>
      assessments[index][0]?.reason_codes.includes('REQUIRED_TASK_MISSING'));
    const misses = missed.length;
    if (assessments.some(matches => matches.length !== 1) || row.total !== count || row.misses !== misses) {
      throw new Error('Miss-rate summary disagrees with retained assessments.');
    }
    const causes = {cut: 0, invalid: 0, omitted: 0, unknown: 0};
    for (const trial of missed) causes[missCause(trial, assessments[experiment.trials.indexOf(trial)][0])] += 1;
    const known = [`reply cut off at the output limit in ${causes.cut}`, `invalid plan in ${causes.invalid}`,
      `plan left the task out in ${causes.omitted}`];
    if (causes.unknown) known.push(`cause not retained in ${causes.unknown}`);
    return `${row.request_id}: ${row.task_id} task missing in ${misses} of ${count} runs (${known.join(', ')})`;
  });
}

// Classify one missing task only from that run's retained reply for the same request.
function missCause(trial, assessment) {
  const reply = (trial.observations ?? []).find(row => row.kind === 'INFERENCE_RESULT' &&
    row.public_payload_json?.request_ordinal === assessment.request_ordinal)?.public_payload_json;
  if (!reply) return 'unknown';
  if (reply.finish_reason === 'length') return 'cut';
  if (reply.plan_failure) return 'invalid';
  if (Array.isArray(reply.plan) && !reply.plan.some(step => step.task_type === assessment.task_id)) return 'omitted';
  return 'unknown';
}


export function proposalDiagnosticSummary(experiment) {
  if (experiment?.kind !== 'DIAGNOSTIC' || experiment.eligible !== false ||
      experiment.public_repetitions !== 1 || experiment.candidates?.length !== 1 ||
      !experiment.candidates[0].proposal_event_id || experiment.candidates[0].artifact_version_id !== null) {
    return 'Proposal report has inconsistent identity or eligibility.';
  }
  const trial = experiment.trials?.[0];
  if (!trial || ['RESERVED', 'RUNNING'].includes(trial.state)) return 'One isolated diagnostic is in progress.';
  const count = trial.request_count;
  const captured = new Set(trial.outputs.filter(output => output.transport_error === null && output.body_base64)
    .map(output => output.request_ordinal));
  const passed = experiment.trials.length === 1 && trial.state === 'COMPLETE' && Number.isInteger(count) && count > 0 &&
    trial.task_assessments.length > 0 && trial.task_assessments.every(task => task.mandatory_pass === true) &&
    Array.from({length: count}, (_, index) => index + 1).every(ordinal => captured.has(ordinal) &&
      trial.task_assessments.some(task => task.request_ordinal === ordinal));
  return `${passed ? 1 : 0} of 1 public batches passed mandatory checks. This diagnostic cannot qualify a version.`;
}
