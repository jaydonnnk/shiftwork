import { selectEvidence } from './evidence.js';

const WALL_TYPES = {
  bookshop: ['SALE_COMPLETED', 'REFUND_REQUIRED', 'ESCALATION_TO_HUMAN', 'BACKLOG_RECORDED', 'INCIDENT_OPENED', 'INCIDENT_RESOLVED', 'LIMIT_DECLARED'],
  gtm: ['OWNER_ASSIGNED', 'SLA_CLOCK_STARTED', 'HANDOFF_ESCALATED', 'INCIDENT_OPENED', 'INCIDENT_RESOLVED', 'BACKLOG_RECORDED', 'LIMIT_DECLARED'],
  northline: ['BOOKING_COMMITTED', 'ESCALATION_TO_HUMAN', 'COUNTER_FOLLOWUP_RECORDED', 'ROLLOUT_APPROVED', 'HANDOVER_DECLARED', 'INCIDENT_OPENED', 'INCIDENT_RESOLVED', 'BACKLOG_RECORDED', 'LIMIT_DECLARED'],
};

export function projectWorkplace(input) {
  const { board, run, operatingVersion, stationView, slug } = input;
  const outputs = input.outputs ?? [], checks = input.checks ?? [], events = input.events ?? [];
  const selection = board?.operating_selection;
  const shiftId = board?.latest_shift?.id ?? null;
  const inspection = { mode: input.inspection.mode, historicalRunId: input.inspection.historicalRunId };
  let consistency = 'linked';
  const incomplete = () => { if (consistency !== 'conflict') consistency = 'incomplete'; };
  const conflict = () => { consistency = 'conflict'; };
  if (!board) incomplete();
  if (board && board.engagement_slug !== slug) conflict();
  if ((input.loadedShiftId ?? null) !== shiftId) conflict();
  if (selection && !operatingVersion) incomplete();
  if (selection && operatingVersion && operatingVersion.id !== selection.selected_version_id) conflict();
  if (selection && operatingVersion && operatingVersion.content_hash !== selection.selected_content_hash) conflict();
  const nominatedLegacy = run?.purpose === 'LEGACY_OPERATION' && board?.latest_shift?.opening_mode === 'LEGACY_FIRST_CHOICE' &&
    board.latest_run?.id === run.id && board.latest_run.shift_id === run.shift_id && board.latest_run.artifact_version_id === run.artifact_version_id;
  if (run && inspection.mode === 'current' && run.shift_id !== shiftId && !nominatedLegacy) conflict();
  if (stationView && stationView.shift_id !== shiftId) conflict();
  if (run && inspection.mode === 'history' && run.id !== inspection.historicalRunId) conflict();
  if (run?.purpose === 'OPERATION' && inspection.mode === 'current') {
    if (!selection || run.selection_id !== selection.id) conflict();
    if (run.artifact_version_id !== selection?.selected_version_id) conflict();
  }
  if (outputs.some(output => output.run_id !== run?.id)) conflict();
  if (checks.some(check => check.run_id !== run?.id)) conflict();
  if (board && board.chain_status !== 'VALID') conflict();
  if (input.ledgerStatus === 'unknown' || input.ledgerStatus == null) incomplete();
  else if (input.ledgerStatus !== 'VALID') conflict();
  if (board && board.ledger_event_count !== events.length) conflict();
  const histogram = {};
  for (const event of events) histogram[event.event_type] = (histogram[event.event_type] ?? 0) + 1;
  for (const type of new Set([...Object.keys(histogram), ...Object.keys(board?.ledger_totals ?? {})])) {
    if ((histogram[type] ?? 0) !== (board?.ledger_totals?.[type] ?? 0)) conflict();
  }
  const output = outputs.find(item => item.id === input.selectedOutputId);
  const linked = selectEvidence(output, checks, events);
  if (output && !linked.checks.length) incomplete();
  if (input.selectedOutputId && !output) incomplete();
  for (const incident of board?.incidents ?? []) {
    const event = events.find(item => item.seq === incident.opened_event_seq);
    if (!event) { incomplete(); continue; }
    const link = event.derivation;
    if (link && (link.run_id !== incident.opening_run_id || link.observed_ref !== incident.failing_output_ref || link.check_id !== incident.check_result_id)) conflict();
  }
  const publicMetrics = metrics => metrics ? {
    publicDenominatorRequests: metrics.public_denominator_requests,
    usefulCompletions: metrics.useful_completions, incorrectOutputs: metrics.incorrect_outputs,
    justifiedRefusals: metrics.justified_refusals, justifiedReferrals: metrics.justified_referrals,
    justifiedClarifications: metrics.justified_clarifications,
    unjustifiedRefusals: metrics.unjustified_refusals, unjustifiedReferrals: metrics.unjustified_referrals,
    unjustifiedClarifications: metrics.unjustified_clarifications, missingOutputs: metrics.missing_outputs,
    protectedDenominator: metrics.protected_denominator, protectedPassed: metrics.protected_passed,
    protectedFailed: metrics.protected_failed, protectedMissing: metrics.protected_missing,
    serviceCalls: metrics.service_calls ?? null, inputTokens: metrics.input_tokens ?? null,
    outputTokens: metrics.output_tokens ?? null, serviceLatencyMs: metrics.service_latency_ms ?? null,
    provisioningLatencyMs: metrics.provisioning_latency_ms ?? null,
    costMinorUnits: metrics.cost_minor_units ?? null,
  } : null;
  const experiment = (item, expectedKind) => {
    if (!item) return null;
    if (item.kind !== expectedKind) return null;
    if (item.shift_id !== shiftId) { conflict(); return null; }
    const candidates = item.candidates ?? [];
    if (new Set(candidates.map(candidate => candidate.label)).size !== candidates.length) conflict();
    const candidateByLabel = new Map(candidates.map(candidate => [candidate.label, candidate]));
    if ((item.trials ?? []).some(trial => {
      if (!trial.candidate_label) return false;
      const bound = candidateByLabel.get(trial.candidate_label);
      return !bound || trial.artifact_version_id !== bound.artifact_version_id;
    })) conflict();
    const missingSlots = (item.trials ?? []).filter(trial => !trial.run_id ||
      (trial.missing_evidence?.length ?? 0) > 0).length;
    return {
      id: item.id, shiftId: item.shift_id, kind: item.kind, state: item.state,
      evidenceClass: item.context_evidence_class, contextHash: item.context_hash,
      conditionLabel: item.condition?.public_label ?? null,
      outcomeStatus: item.outcome?.status ?? null,
      sharedPublicDenominatorRequests: item.shared_public_denominator_requests ?? null,
      protectedDenominatorRequestsPerCandidate: item.protected_denominator_requests_per_candidate ?? null,
      missingSlots,
      incomparable: expectedKind === 'QUALIFYING_COMPARISON' &&
        (item.state === 'INVALIDATED' || Boolean(item.outcome && item.outcome.status !== 'COMPLETE')),
      candidates: candidates.map(candidate => {
        const eligibility = item.outcome?.eligibility?.find(row => row.candidate_label === candidate.label);
        const metrics = item.outcome?.candidate_metrics?.find(row => row.candidate_label === candidate.label);
        return { label: candidate.label, versionId: candidate.artifact_version_id,
          contentHash: candidate.artifact_content_hash, eligible: eligibility?.eligible ?? null,
          blockingReasonCodes: [...(eligibility?.blocking_reason_codes ?? [])],
          metrics: publicMetrics(metrics) };
      }),
      trials: (item.trials ?? []).map(trial => ({ ordinal: trial.execution_ordinal ?? trial.ordinal,
        pairOrdinal: trial.pair_ordinal ?? null, candidateLabel: trial.candidate_label,
        runId: trial.run_id, versionId: trial.artifact_version_id, state: trial.state,
        evidenceMode: trial.evidence_mode ?? null, missingEvidenceCount: trial.missing_evidence?.length ?? null })),
      observedRunId: item.observed_run_id ?? null,
    };
  };
  const latest = stationView?.latest_experiment;
  const tests = { diagnostic: experiment(input.diagnostic ?? stationView?.latest_diagnostic, 'DIAGNOSTIC'),
    comparison: experiment(input.comparison ?? latest, 'QUALIFYING_COMPARISON'),
    later: experiment(latest, 'LATER_CONDITION_COMPARISON') };
  if (selection?.comparison_id && tests.diagnostic?.id === selection.comparison_id) conflict();
  if (selection?.comparison_id && tests.comparison?.id === selection.comparison_id) {
    const selected = tests.comparison.candidates.filter(candidate => candidate.versionId === selection.selected_version_id);
    const chosen = selected.length === 1 ? selected[0] : null;
    if (!chosen) conflict();
    else {
      if (chosen.contentHash !== selection.selected_content_hash) conflict();
      const alternative = tests.comparison.candidates.filter(candidate => candidate !== chosen);
      if (alternative.length !== 1 || alternative[0].versionId !== selection.retained_alternative_version_id) conflict();
    }
  }
  const diagnosticRuns = new Set((tests.diagnostic?.trials ?? []).map(trial => trial.runId).filter(Boolean));
  if (events.some(event => diagnosticRuns.has(event.derivation?.run_id))) conflict();
  return {
    schemaVersion: 1, context: { board: slug, shiftId, inspection }, station: input.activeStation,
    shiftState: board?.latest_shift?.state?.toLowerCase() ?? null,
    operating: selection ? { selectionId: selection.id, kind: selection.kind,
      versionId: selection.selected_version_id, contentHash: selection.selected_content_hash,
      comparisonId: selection.comparison_id, retainedAlternativeId: selection.retained_alternative_version_id,
      requirementSetHash: selection.requirement_set_hash, validity: selection.state } : null,
    saved: { latestVersionId: board?.latest_saved_version_id ?? null, draftBaseVersionId: board?.draft_base_version_id ?? null },
    run: run ? { id: run.id, shiftId: run.shift_id, versionId: run.artifact_version_id,
      selectionId: run.selection_id, state: run.state, purpose: run.purpose, evidenceMode: run.evidence_mode } : null,
    evidence: output ? { runId: output.run_id, outputId: output.id, ordinal: output.request_ordinal,
      checks: linked.checks.map(check => ({ id: check.id, verdict: check.verdict, reasonCode: check.reason_code })),
      linkedEventIds: linked.events.map(event => `${slug}:${event.seq}:${event.hash}`),
      completeness: consistency === 'conflict' ? 'conflict' : linked.checks.length ? 'linked' : 'missing' } : null,
    investigation: { latestEntryId: stationView?.latest_investigation_id ?? null, count: stationView?.investigations?.length ?? 0 },
    tests,
    consequences: { chainStatus: input.ledgerStatus === 'VALID' ? 'VALID' : 'unknown',
      eventCount: board?.ledger_event_count ?? null,
      totals: Object.entries(board?.ledger_totals ?? {}).map(([name, count]) => ({ name, count })),
      events: events.filter(event => WALL_TYPES[slug]?.includes(event.event_type)).map(event => ({
        id: `${slug}:${event.seq}:${event.hash}`, seq: event.seq, hash: event.hash, type: event.event_type,
        synthetic: event.synthetic, link: event.derivation ? { runId: event.derivation.run_id,
          checkId: event.derivation.check_id, outputId: event.derivation.observed_ref,
          ordinal: event.derivation.request_ordinal, verdict: event.derivation.verdict } : null,
        signalRef: null, owner: null, recordRef: null, incidentId: null, versionId: null,
      })),
      incidents: (board?.incidents ?? []).map(incident => ({ id: incident.id, state: incident.state,
        reasonCode: incident.reason_code, openingRunId: incident.opening_run_id, openedEventSeq: incident.opened_event_seq })),
    },
    inheritance: { selectionId: selection?.id ?? null, comparisonId: board?.inherited_requirements?.comparison_id ?? null,
      requirementSetHash: board?.inherited_requirements?.requirement_set_hash ?? null,
      visibleCheckSetHash: board?.inherited_requirements?.visible_check_set_hash ?? null },
    consistency,
  };
}

function diagnosticKey(summary) {
  if (!summary) return null;
  const trial = summary.trials[0] ?? null;
  return [summary.id, summary.state, trial?.state ?? 'none', trial?.runId ?? 'none',
    trial?.missingEvidenceCount ?? 'none'].join('|');
}

function comparisonKey(summary) {
  if (!summary) return null;
  const candidates = summary.candidates.map(candidate => [candidate.label,
    candidate.eligible === null ? 'unknown' : candidate.eligible ? 'eligible' : 'blocked',
    candidate.blockingReasonCodes.join(',')].join(':')).sort().join(';');
  return [summary.id, summary.state, summary.outcomeStatus ?? 'none',
    summary.missingSlots ?? 'none', candidates].join('|');
}

function selectionKey(operating) {
  if (!operating) return null;
  return [operating.selectionId, operating.versionId, operating.contentHash].join('|');
}

export function diffWorkplace(previous, next) {
  if (!previous || previous.consistency === 'conflict' || next.consistency === 'conflict') return [];
  if (previous.context.board !== next.context.board || previous.context.shiftId !== next.context.shiftId) return [];
  const beforeInspection = previous.context.inspection, afterInspection = next.context.inspection;
  if (beforeInspection.mode !== afterInspection.mode || beforeInspection.historicalRunId !== afterInspection.historicalRunId) return [];
  const transitions = [];
  if (beforeInspection.mode === 'current' && previous.station !== next.station) {
    transitions.push({ key: `station:${next.station}`, kind: 'station-focus', stationId: next.station, publicRefs: [] });
  }
  const diagnostic = next.tests?.diagnostic ?? null;
  const before = diagnosticKey(previous.tests?.diagnostic);
  const after = diagnosticKey(diagnostic);
  if (before !== after && after !== null) {
    const trial = diagnostic?.trials?.[0] ?? null;
    transitions.push({ key: `test:diagnostic:${after}`, kind: 'test-update', stationId: 'compare',
      publicRefs: (diagnostic ? [diagnostic.id, trial?.runId, trial?.versionId] : []).filter(Boolean) });
  }
  const comparison = next.tests?.comparison ?? null;
  const beforeComparison = comparisonKey(previous.tests?.comparison);
  const afterComparison = comparisonKey(comparison);
  if (beforeComparison !== afterComparison && afterComparison !== null) {
    transitions.push({ key: `comparison:${afterComparison}`, kind: 'comparison-update', stationId: 'compare',
      publicRefs: [comparison?.id, ...(comparison?.candidates ?? []).map(candidate => candidate.versionId)].filter(Boolean) });
  }
  const operating = next.operating ?? null;
  const beforeSelection = selectionKey(previous.operating);
  const afterSelection = selectionKey(operating);
  if (beforeSelection !== afterSelection && afterSelection !== null) {
    transitions.push({ key: `selection:${afterSelection}`, kind: 'selection-update', stationId: 'service',
      publicRefs: [operating?.selectionId, operating?.versionId].filter(Boolean) });
  }
  return transitions;
}
