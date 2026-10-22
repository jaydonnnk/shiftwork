// Pure presentation of the main view's words. No DOM, engine, network or command
// access: every value is a reduction of an accepted SceneView or loaded public records.
import { selectEvidence } from './evidence.js';

const words = value => String(value).toLowerCase().replaceAll('_', ' ');

const UNRESOLVED = new Set(['OPEN', 'CLOSED_UNRESOLVED']);
const CHECK_WORDS = { pass: 'passed', fail: 'failed', error: 'errored' };

// Status bar values for the main view. Version labels are allowed here; run,
// selection, check and hash identities are not, so none of them is read.
export function statusBarValues(view, { client = null, shiftSeq = null, attemptsRemaining = null } = {}) {
  const conflict = view?.consistency === 'conflict';
  const operating = view?.operating ?? null;
  const live = conflict ? 'Unavailable'
    : !operating ? 'None chosen'
    : operating.validity === 'INVALIDATED' ? `${operating.versionId} · invalidated`
    : operating.kind === 'STARTER_BASELINE' ? `${operating.versionId} · starter`
    : operating.versionId;
  const incidents = view?.consequences?.incidents;
  return {
    client: client ?? 'Unknown client',
    shift: shiftSeq == null ? 'No shift' : `Shift ${shiftSeq}`,
    live,
    incidents: conflict || !Array.isArray(incidents) ? 'Unknown'
      : String(incidents.filter(incident => UNRESOLVED.has(incident.state)).length),
    attempts: attemptsRemaining == null ? 'Unknown' : String(attemptsRemaining),
    synthetic: 'Synthetic scenario',
  };
}

// The shift log keeps the full identities the main view leaves out.
// Newest last: selection, your notes, the loaded run, its checks, then ledger events.
export function logEntries(view, run, checks, events, investigations, selection) {
  const entries = [];
  if (selection) entries.push({ kind: 'selection', ids: [selection.id, selection.selected_version_id],
    text: selection.kind === 'LEARNER_CHOICE' ? `You chose ${selection.selected_version_id} as the live version${selection.state === 'INVALIDATED' ? ' · invalidated' : ''}`
      : `Starter ${selection.selected_version_id} is the live version`,
    tone: selection.kind === 'LEARNER_CHOICE' ? 'you' : 'info', recordedAt: selection.created_at ?? null });
  for (const entry of investigations ?? []) entries.push({ kind: 'note', ids: [entry.id, entry.source_run_id],
    text: `You recorded a cause and falsifier for request ${entry.source_request_ordinal}`, tone: 'you',
    recordedAt: entry.created_at ?? null });
  if (run) {
    entries.push({ kind: 'run', ids: [run.id, run.artifact_version_id],
      text: `${words(run.purpose)} run of ${run.artifact_version_id} · ${words(run.state)}`, tone: run.state === 'FAILED' ? 'fail' : 'info',
      recordedAt: run.started_at ?? null });
    for (const check of (checks ?? []).filter(item => item.run_id === run.id)) entries.push({ kind: 'check',
      ids: [check.id, ...(check.public_check_id ? [check.public_check_id] : [])],
      text: `Independent check ${CHECK_WORDS[check.verdict] ?? 'recorded'}${check.reason_code ? ` · ${check.reason_code}` : ''}`, tone: check.verdict === 'pass' ? 'pass' : 'fail',
      recordedAt: null });
  }
  for (const event of [...(events ?? [])].sort((a, b) => a.seq - b.seq)) entries.push({ kind: 'event',
    ids: [`seq ${event.seq}`, ...(event.cause_refs ?? [])],
    text: `${words(event.event_type)}${event.synthetic ? ' · synthetic' : ''}`,
    tone: event.event_type === 'INCIDENT_OPENED' ? 'fail' : event.event_type === 'INCIDENT_RESOLVED' ? 'pass' : 'info', recordedAt: null });
  if (view?.consistency === 'conflict') entries.push({ kind: 'note', ids: [],
    text: 'Recorded reads disagree; no outcome is inferred', tone: 'fail', recordedAt: null });
  return entries;
}

// The seven steps of a shift, in the learner's words (Gate 3 section 13.4).
export const STEP_NAMES = ['Read the complaints', 'Explain the cause', 'Say what would prove you wrong', 'Try two fixes',
  'Choose one', 'Run the shift', 'See what happened'];
const TERMINAL = new Set(['FINALIZED', 'FAILED']);
// Counts describe loaded evidence, including a failed run. They never imply
// successful operation. A broken causal route leaves incident counts unknown.
export function reduceShiftReport(view, run, checks, events, selection) {
  const tally = run && view?.slips?.runId === run.id ? view.slips.tally : null;
  const bound = Boolean(run && run.purpose === 'OPERATION' && TERMINAL.has(run.state) &&
    view?.run?.id === run.id && selection?.id === run.selection_id && selection.selected_version_id === run.artifact_version_id);
  const accepted = bound && Array.isArray(checks) && tally?.total === view.run.outputCount;
  const requests = Object.fromEntries(['pass', 'fail', 'error', 'none'].map(key => [key, accepted ? tally[key] : null]));
  const ledger = bound && Array.isArray(events) && view.consistency !== 'conflict' &&
    view.consequences?.chainStatus === 'VALID' && view.consequences.countMatches === true && view.consequences.histogramMatches === true;
  const runEvents = (events ?? []).filter(event => run && (event.derivation?.run_id === run.id || event.cause_refs?.[0] === run.id));
  const linked = runEvents.every(event => {
    const link = event.derivation;
    return event.synthetic === true && link?.run_id === run.id &&
      checks?.some(check => check.id === link.check_id && check.run_id === run.id &&
        check.observed_ref === link.observed_ref && check.verdict === link.verdict) &&
      view?.consequences?.events.some(row => row.seq === event.seq && row.hash === event.hash && row.linkState === 'linked');
  });
  const incidentTypes = new Set(['INCIDENT_OPENED', 'INCIDENT_RESOLVED']);
  const incidentEvents = (events ?? []).filter(event => incidentTypes.has(event.event_type));
  const incidentLinks = incidentEvents.every(event => event.synthetic === true && event.derivation);
  const end = runEvents.length ? Math.max(...runEvents.map(event => event.seq))
    : view?.context?.inspection.mode === 'current' ? Infinity : null;
  const start = runEvents.length ? Math.min(...runEvents.map(event => event.seq)) : end;
  const countable = ledger && linked && incidentLinks;
  const count = type => countable ? runEvents.filter(event => event.event_type === type).length : null;
  const balance = predicate => {
    if (!countable || end == null) return null;
    const value = incidentEvents.filter(predicate).reduce((n, event) => n + (event.event_type === 'INCIDENT_OPENED' ? 1 : -1), 0);
    return value < 0 ? null : value;
  };
  const openBefore = balance(event => event.seq < start), openAfter = balance(event => event.seq <= end);
  return { runId: run?.id ?? null, versionLabel: run?.artifact_version_id ?? null,
    backupLabel: bound ? selection.retained_alternative_version_id ?? null : null, requests,
    incidentsOpened: count('INCIDENT_OPENED'), incidentsResolved: count('INCIDENT_RESOLVED'), openBefore, openAfter,
    complete: Boolean(accepted && tally.none === 0 && countable && openBefore != null && openAfter != null) };
}
const guide = (step, stationId, status = 'ready', blockedReason = null) =>
  ({ step, name: STEP_NAMES[step - 1], stationId, status, blockedReason });

// The step guide only navigates. It reads recorded state in the order of Gate 3
// section 13.5 and never decides whether a command is allowed. The local draft
// booleans steer only the chip between steps 1 and 3; they are never sent or credited.
export function guideStep(view, local = {}) {
  if (!view || view.consistency === 'conflict' || !view.context?.shiftId) return { step: null, name: null,
    stationId: local.activeStation ?? view?.station ?? 'customers', status: 'blocked', blockedReason: 'Step unknown: recorded state unavailable' };
  const shiftId = view.context.shiftId, operating = view.operating, run = view.run;
  const comparison = view.tests?.comparison?.shiftId === shiftId ? view.tests.comparison : null;
  if (view.shiftState === 'closed') return guide(7, 'next');
  // Only the learner's own choice ends the loop; the starter's run is what step 1 reads.
  if (operating?.kind === 'LEARNER_CHOICE' && run && run.purpose === 'OPERATION' && run.shiftId === shiftId && run.selectionId === operating.selectionId)
    return TERMINAL.has(run.state) ? guide(7, 'ledger') : guide(6, 'service', 'running');
  if (operating?.kind === 'LEARNER_CHOICE' && comparison && operating.comparisonId === comparison.id) return guide(6, 'service');
  // Rule 3a: a choice inherited into a later open shift has not yet run there.
  if (operating?.kind === 'LEARNER_CHOICE' && view.shiftState === 'open') return guide(6, 'service');
  if (comparison?.outcomeStatus === 'COMPLETE') {
    if (comparison.candidates.some(candidate => candidate.eligible === true)) return guide(5, 'compare');
    const code = comparison.candidates.flatMap(candidate => candidate.blockingReasonCodes)[0];
    return guide(4, 'compare', 'blocked', code ? `Neither version can be chosen: ${words(code)}` : 'Neither version can be chosen');
  }
  if ((view.investigation?.count ?? 0) >= 1) return guide(4, 'compare');
  if (local.activeStation === 'investigate') return local.causeDraft ? guide(3, 'investigate') : guide(2, 'investigate');
  return guide(1, 'customers');
}

// One slip per loaded output in ordinal order, with the verdict its linked checks
// give. Null until the run is terminal and its checks read has been accepted.
export function planSlips(run, outputs, checks, events = []) {
  if (!run || !TERMINAL.has(run.state) || !Array.isArray(checks)) return null;
  const slips = [...(outputs ?? [])].filter(output => output.run_id === run.id)
    .sort((a, b) => a.request_ordinal - b.request_ordinal).map(output => {
      const linked = selectEvidence(output, checks, events).checks;
      const verdict = linked.some(check => check.verdict === 'fail') ? 'fail'
        : linked.some(check => check.verdict === 'error') ? 'error'
        : linked.length ? 'pass' : 'none';
      return { ordinal: output.request_ordinal, outputId: output.id, verdict, checkCount: linked.length };
    });
  return { runId: run.id, purpose: run.purpose, state: run.state, slips: slips.slice(0, 12), overflow: Math.max(0, slips.length - 12),
    tally: { total: slips.length, ...Object.fromEntries(['pass', 'fail', 'error', 'none'].map(v => [v, slips.filter(slip => slip.verdict === v).length])) } };
}

// Station lamps for Bellwether (Gate 3 section 13.5). Text is always present, so
// the tone is never the only signal.
const lamp = (stationId, tone, text) => ({ stationId, tone, text });
export function lampStates(view) {
  if (!view || view.consistency === 'conflict') return ['customers', 'service', 'evaluator', 'ledger', 'compare', 'investigate', 'owner', 'next', 'repair', 'pipeline']
    .map(id => lamp(id, 'unknown', 'Unavailable'));
  const operating = view.operating, run = view.run, tally = view.slips?.tally ?? null;
  const ownOperation = Boolean(run && run.purpose === 'OPERATION' && operating && run.selectionId === operating.selectionId);
  const complaints = tally ? tally.fail + tally.error + tally.none : 0;
  const allPassed = Boolean(ownOperation && tally && tally.total > 0 && tally.pass === tally.total);
  // Under the starter, recorded complaints stay open whatever the loaded run shows (13.5, re-approved 2026-10-22).
  const open = (view.consequences?.incidents ?? []).filter(incident => UNRESOLVED.has(incident.state)).length;
  const starterOpen = operating?.kind === 'STARTER_BASELINE' && open > 0;
  const customers = starterOpen ? lamp('customers', 'attention', `${open} open ${open === 1 ? 'complaint' : 'complaints'}`)
    : !run || !run.outputCount ? lamp('customers', 'idle', 'No recorded requests')
    : allPassed ? lamp('customers', 'pass', 'No complaints')
    : complaints ? lamp('customers', 'attention', `${complaints} ${complaints === 1 ? 'complaint' : 'complaints'}`)
    : lamp('customers', 'idle', `${run.outputCount} recorded ${run.outputCount === 1 ? 'request' : 'requests'}`);
  const service = !operating ? lamp('service', 'idle', 'No live version')
    : operating.validity === 'INVALIDATED' ? lamp('service', 'fail', 'Invalidated')
    : starterOpen ? lamp('service', 'attention', 'Live, complaints open')
    : ownOperation && tally && TERMINAL.has(run.state) ? (allPassed ? lamp('service', 'pass', 'Live, checks passed') : lamp('service', 'fail', 'Live, checks failed'))
    : lamp('service', 'attention', 'Live, not yet run');
  const evaluator = run && !TERMINAL.has(run.state) ? lamp('evaluator', 'idle', `Locked · ${words(run.state)}`) : lamp('evaluator', 'idle', 'Locked');
  const ledger = view.consequences?.chainStatus !== 'VALID' ? lamp('ledger', 'unknown', 'Unavailable')
    : open ? lamp('ledger', 'fail', `${open} open`) : lamp('ledger', 'idle', 'None open');
  const comparison = view.tests?.comparison;
  const running = comparison && (['PLANNED', 'RUNNING'].includes(comparison.state) || comparison.trials.some(trial => ['RESERVED', 'RUNNING'].includes(trial.state)));
  const compare = running ? lamp('compare', 'attention', 'Running')
    : !comparison ? lamp('compare', 'idle', 'Not started')
    : comparison.outcomeStatus === 'COMPLETE' ? lamp('compare', 'idle', 'No score, no default')
    : lamp('compare', 'idle', 'Incomplete');
  const count = view.investigation?.count ?? 0;
  const lamps = [customers, service, evaluator, ledger, compare,
    lamp('investigate', 'idle', count ? `${count} recorded` : 'Nothing recorded'),
    lamp('owner', 'idle', 'Read only'),
    lamp('next', 'idle', view.shiftState === 'closed' ? 'Shift closed' : 'Shift open'),
    lamp('repair', 'idle', 'Read only'),
    lamp('pipeline', 'idle', 'Follow the record')];
  // Only these quiet stations take the guide's attention; the others keep their recorded tone.
  for (const item of lamps) if (item.stationId === view.attention && ['investigate', 'owner', 'next', 'repair', 'pipeline'].includes(item.stationId)) item.tone = 'attention';
  return lamps;
}

// The owner's one line per step, from a frozen catalogue reviewed by a person.
// Only public counts are substituted; no line names a cause, a fix, a candidate,
// a version or a choice (owner_lines_never_suggest).
export const OWNER_LINES = {
  1: '{n} customers in the last recorded run did not get what they asked for.',
  2: 'Write down your own explanation first; I will not guess for you.',
  3: 'Write down your own explanation first; I will not guess for you.',
  4: 'Both versions get the same requests, so the comparison is fair.',
  5: 'Nothing goes live until you choose and say why.',
  6: 'The version you chose is the one that runs.',
  7: '{p} of {m} recorded requests passed the inspector\'s checks.',
  closed: 'Your choice carries into the next shift.',
  openComplaints: '{n} customer complaints are still open.',
};
export function ownerLine(view, guide) {
  if (!guide?.step || !view) return null;
  const tally = view.slips?.tally ?? null;
  if (view.shiftState === 'closed') return OWNER_LINES.closed;
  if (guide.step === 1) {
    const n = tally ? tally.fail + tally.error + tally.none : null;
    if (n) return OWNER_LINES[1].replace('{n}', String(n));
    const open = view.operating?.kind === 'STARTER_BASELINE' ? (view.consequences?.incidents ?? []).filter(incident => UNRESOLVED.has(incident.state)).length : 0;
    return open ? OWNER_LINES.openComplaints.replace('{n}', String(open)) : null;
  }
  if (guide.step === 7) return tally ? OWNER_LINES[7].replace('{p}', String(tally.pass)).replace('{m}', String(tally.total)) : null;
  return OWNER_LINES[guide.step];
}

// The customer's recorded request, shown in a bubble at the queue.
const PURPOSE_WORDS = { OPERATION: 'operation', EXPERIMENT: 'test', LEGACY_OPERATION: 'history' };
export function customerBubble(view, output) {
  if (!view?.run || !output || output.run_id !== view.run.id || typeof output.request_text !== 'string') return null;
  const purpose = view.context?.inspection?.mode === 'history' ? 'history' : PURPOSE_WORDS[view.run.purpose] ?? 'history';
  const raw = output.request_text.trim();
  return { label: `Recorded request · ${purpose}`, text: raw.length > 140 ? `${raw.slice(0, 139).trimEnd()}…` : raw };
}

// Gate 3 section 14.2 rule 1: at 761px and wider only the guide's station and the
// first failing station rest visible over the room. A presentation filter only;
// every other tag stays a reachable button and shows on hover or focus.
export function restingTags(view, guide, lamps = view?.lamps) {
  const resting = new Set(guide?.stationId ? [guide.stationId] : []);
  const failing = (lamps ?? []).find(item => item.tone === 'fail' && !resting.has(item.stationId));
  if (failing) resting.add(failing.stationId);
  return resting;
}

// Gate 3 section 14.2 rule 2: one narrator bubble. The customer's recorded request
// speaks at step 1; otherwise the owner's catalogued line, or nobody.
export function narrator(view, guide, output) {
  const request = guide?.step === 1 ? customerBubble(view, output) : null;
  if (request) return { role: 'customer', stationId: 'customers', ...request };
  const line = ownerLine(view, guide);
  return line ? { role: 'owner', stationId: 'owner', label: 'Owner', text: line } : null;
}

// Shift picker copy (Gate 1 mockup screen 10, Gate 3 section 13.10 item 6).
// Authored text only: no live counts, and no question names a cause or a fix.
export const SHIFT_CARDS = [
  { slug: 'bookshop', client: 'Bellwether Books', badge: 'Start here', role: "Junior Applied AI Engineer · a bookshop's customer service",
    question: 'Customers ask to collect a book and for similar titles. The service answers with a price only. Why?',
    teaches: 'Say what would prove you wrong before you change any code.' },
  { slug: 'northline', client: 'Northline Bike Co-op', badge: 'Away shift', role: "Forward Deployed Engineer · a repair workshop's bookings",
    question: 'The co-op wants online bookings. Can you roll out without crossing the permissions they set?',
    teaches: "Acceptance comes before rollout, and the client's boundaries come first." },
  { slug: 'gtm', client: 'Stonebridge Software', badge: 'Revenue team', role: 'Go-To-Market Engineer · lead routing for a sales team',
    question: 'Promising leads sit unassigned past their response deadline. What is going wrong?',
    teaches: 'Owners and deadlines are the consequence you can check.' },
];
