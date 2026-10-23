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
