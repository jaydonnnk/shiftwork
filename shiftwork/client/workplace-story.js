// Pure presentation of the main view's words. No DOM, engine, network or command
// access: every value is a reduction of an accepted SceneView or loaded public records.

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
