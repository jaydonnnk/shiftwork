import { bodyBytes, selectEvidence, diagnosticRateLines } from './evidence.js';
import { projectWorkplace } from './workplace-view.js';
import { statusBarValues, logEntries, guideStep, narrator, restingTags, reduceShiftReport, STEP_NAMES, SHIFT_CARDS } from './workplace-story.js';

const $ = id => document.getElementById(id);
const state = { board: null, loadedShiftId: null, draft: null, stationView: null, run: null, outputs: [], checks: [], events: [], selected: null, station: 'service', view: 'board', file: 'contract', generation: 0, intent: 0, pending: false, diagnostic: null, comparison: null, candidates: { A: null, B: null } };
state.slug = 'bookshop';
state.workplaces = [];
const northline = () => state.slug === 'northline';
const gtm = () => state.slug === 'gtm';
const engagementPath = suffix => `/engagements/${encodeURIComponent(state.slug)}/${suffix}`;
let downloadUrl = null;
let pollTimer = null;
let workplaceHost = null, latestPresentation = null, hostEpoch = 0, hostLoading = false, hostTimer = null;
let inspection = { mode: 'current', historicalRunId: null };
let expandedWork = false;
let inspectorOpen = false, inspectorCover = 0, logFilter = 'all', openStationId = null;
let reportPrevious = null, chooseOpener = null, reportOpener = null;
const reportedRuns = new Set();
const REPORTED_TEST_STATES = new Set(['RESERVED', 'RUNNING', 'COMPLETE', 'FAILED']);
function renderTestBench(view) {
  const label = $('test-tag');
  const experiment = view.tests.diagnostic;
  if (!experiment) {
    label.textContent = 'No diagnostic reported';
    label.dataset.state = 'NONE';
    delete label.dataset.missingEvidence;
    return;
  }
  const trial = experiment.trials[0] ?? null;
  const state = trial && REPORTED_TEST_STATES.has(trial.state) ? trial.state : 'UNREPORTED';
  const missing = trial?.missingEvidenceCount;
  label.dataset.state = state;
  if (missing == null) delete label.dataset.missingEvidence;
  else label.dataset.missingEvidence = String(missing);
  label.textContent = state === 'UNREPORTED' ? 'Diagnostic state not reported'
    : `Diagnostic ${humanize(state)}${missing ? ` · ${missing} missing evidence` : ''}`;
}
const WALL_SOURCE_TEXT = { current: 'Current operation record', historical: 'Historical record · not loaded',
  administrative: 'Administrative record · no derivation' };
const WALL_MEANING_TEXT = { recorded: 'Recorded consequence', negative: 'Negative consequence · not success',
  pending: 'Incomplete route · no arrival inferred', conflict: 'Contradictory link',
  historical: 'Settled quietly', administrative: 'Settled quietly' };
function showWallTrace(count) {
  const label = $('wall-trace');
  if (!label) return;
  label.textContent = count > 1 ? `Recorded evidence added · ${count} events` : 'Recorded evidence added';
  label.dataset.state = 'active';
}
function resetConsequenceWall(message) {
  const status = $('wall-status');
  status.textContent = message; status.dataset.consistency = ''; status.dataset.runState = '';
  delete status.dataset.countMatches; delete status.dataset.histogramMatches; delete status.dataset.chain;
  text('wall-trace', 'No recorded-evidence trace.'); $('wall-trace').dataset.state = 'idle';
  empty($('ledger-totals'), 'No verified data loaded.');
  empty($('wall-events'), 'No verified data loaded.');
}
function renderConsequenceWall(view) {
  const consequences = view.consequences;
  const status = $('wall-status');
  const lines = [];
  if (view.run?.purpose === 'OPERATION') {
    const runLine = `Operation ${view.run.id} · ${view.run.state}${view.run.failureKind ? ` · ${humanize(view.run.failureKind)}` : ''}`;
    lines.push(runLine);
    if (['QUEUED', 'RUNNING'].includes(view.run.state)) lines.push('Pending. No consequence is inferred from an unfinished run.');
    else if (view.run.state === 'FAILED') lines.push('Failed. Confirmed records stay visible; no success is implied.');
    else if (view.run.state === 'FINALIZED' && view.run.failedCheckCount > 0) {
      lines.push(`Finalized with ${view.run.failedCheckCount} failed mandatory check${view.run.failedCheckCount === 1 ? '' : 's'}. No success is implied.`);
    } else if (view.run.state === 'FINALIZED' && view.run.checkCount === 0) {
      lines.push('Finalized without independent checks. Evidence incomplete.');
    }
  }
  lines.push(`Chain ${humanize(consequences.chainStatus)}${view.consistency === 'conflict' ? ' · reads disagree' : ''}`);
  lines.push(consequences.countMatches === false
    ? `Count disagreement: board ${consequences.eventCount}, ledger ${consequences.ledgerEventLength}`
    : `Counts agree: ${consequences.eventCount} recorded events`);
  lines.push(consequences.histogramMatches === false ? 'Type totals disagree' : 'Type totals agree');
  if (consequences.otherEventCount) {
    lines.push(`${consequences.otherEventCount} other recorded event${consequences.otherEventCount === 1 ? '' : 's'} stay text-only: ${consequences.otherTypes.map(humanize).join(', ')}`);
  }
  status.textContent = lines.join(' · ');
  status.dataset.consistency = view.consistency;
  status.dataset.runState = view.run?.state ?? '';
  status.dataset.countMatches = String(consequences.countMatches);
  status.dataset.histogramMatches = String(consequences.histogramMatches);
  status.dataset.chain = consequences.chainStatus;
  const totals = $('ledger-totals');
  if (!consequences.totals.length) empty(totals, 'No ledger events yet.');
  else totals.replaceChildren(...consequences.totals.map(({ name, count }) => {
    const row = element('div', null, 'total-row');
    row.dataset.ledgerType = name; row.dataset.ledgerCount = String(count);
    row.append(element('span', humanize(name)), element('strong', count));
    return row;
  }));
  const wall = $('wall-events');
  if (!consequences.events.length) return empty(wall, 'No allowlisted consequence recorded. Other events stay in the text records above.');
  wall.replaceChildren(...consequences.events.map(event => {
    const row = element('article', null, 'wall-event');
    row.dataset.wallEvent = event.id; row.dataset.wallSeq = String(event.seq);
    row.dataset.wallType = event.type; row.dataset.wallSource = event.source;
    row.dataset.wallLink = event.linkState; row.dataset.wallMeaning = event.meaning;
    row.dataset.synthetic = String(event.synthetic);
    if (event.incidentId) row.dataset.wallIncident = event.incidentId;
    if (event.versionId) row.dataset.wallVersion = event.versionId;
    if (event.link) {
      row.dataset.wallRun = event.link.runId; row.dataset.wallCheck = event.link.checkId;
      row.dataset.wallOutput = event.link.outputId; row.dataset.wallOrdinal = String(event.link.ordinal);
      row.dataset.wallVerdict = event.link.verdict;
      if (event.reasonCode) row.dataset.wallReason = event.reasonCode;
    }
    row.append(element('strong', `${humanize(event.type)} · event ${event.seq}`));
    row.append(element('small', `${WALL_SOURCE_TEXT[event.source]} · ${WALL_MEANING_TEXT[event.meaning]}`, 'wall-source'));
    if (event.link) row.append(element('small', `Run ${event.link.runId} · check ${event.link.checkId} · output ${event.link.outputId} · request ${event.link.ordinal} · verdict ${event.link.verdict}${event.reasonCode ? ` · ${event.reasonCode}` : ''}`, 'evidence-meta'));
    if (event.incidentId) row.append(element('small', `Incident ${event.incidentId}`, 'evidence-meta'));
    return row;
  }));
}
function renderInspectionBar() {
  const bar = $('inspection-bar'), button = $('inspect-current');
  if (!bar || !button) return;
  bar.dataset.mode = inspection.mode;
  text('inspection-mode', inspection.mode === 'history'
    ? `Historical inspection · run ${inspection.historicalRunId ?? 'unknown'}`
    : 'Current inspection');
  button.hidden = inspection.mode !== 'history';
}
async function inspectIncident(incident) {
  if (state.pending) return;
  const owner = { slug: state.slug, shiftId: state.loadedShiftId, intent: ++state.intent };
  inspection = { mode: 'history', historicalRunId: incident.opening_run_id };
  publishPresentation('history');
  const accepted = await refresh(incident.opening_run_id);
  if (!accepted || owner.slug !== state.slug || owner.shiftId !== state.loadedShiftId || owner.intent !== state.intent ||
      inspection.mode !== 'history' || inspection.historicalRunId !== incident.opening_run_id ||
      state.run?.id !== incident.opening_run_id) return;
  state.selected = state.outputs.find(output => output.id === incident.failing_output_ref)?.id ?? null;
  activateStation('customers');
  const target = [...document.querySelectorAll('.customer-button')].find(node => node.dataset.outputId === state.selected);
  if (target) target.focus(); else $('station-panel').focus();
}
async function returnToCurrent() {
  if (state.pending || inspection.mode === 'current') return;
  const intent = ++state.intent;
  inspection = { mode: 'current', historicalRunId: null };
  publishPresentation('history');
  const accepted = await refresh();
  if (!accepted || intent !== state.intent) return;
  $('station-panel').focus({ preventScroll: true });
}
function incidentButton(incident) {
  const button = element('button', null, 'incident-row');
  const current = inspection.mode === 'current' && incident.opening_run_id === state.run?.id;
  button.dataset.incidentId = incident.id;
  button.dataset.incidentState = incident.state;
  button.dataset.incidentSource = current ? 'current' : 'historical';
  button.dataset.openedEventSeq = String(incident.opened_event_seq);
  button.dataset.openingRun = incident.opening_run_id;
  button.dataset.failingOutput = incident.failing_output_ref;
  button.dataset.checkResult = incident.check_result_id;
  if (incident.resolved_event_seq != null) button.dataset.resolvedEventSeq = String(incident.resolved_event_seq);
  button.append(element('strong', `${incident.id} · ${humanize(incident.state)}`), element('span', incident.reason_code));
  button.append(element('small', `${current ? 'Current operation record' : 'Historical record'} · opened by event ${incident.opened_event_seq} · run ${incident.opening_run_id}${incident.resolved_event_seq != null ? ` · resolved by event ${incident.resolved_event_seq}` : ''}`, 'evidence-meta'));
  button.addEventListener('click', () => inspectIncident(incident));
  return button;
}
function renderRepairTray() {
  if (!state.board) {
    text('repair-state', 'No incident loaded.');
    empty($('repair-incidents'), 'No verified data loaded.');
    empty($('repair-detail'), 'Select an incident to inspect its recorded run.');
    return;
  }
  const incidents = state.board.incidents;
  text('repair-state', incidents.length
    ? `${incidents.length} unresolved incident${incidents.length === 1 ? '' : 's'} · read only · ${inspection.mode === 'history' ? `historical run ${inspection.historicalRunId}` : 'current shift'}`
    : 'No unresolved incident. No repair authoring is available in this build.');
  if (!incidents.length) empty($('repair-incidents'), 'The tray has no incident to review.');
  else $('repair-incidents').replaceChildren(...incidents.map(incidentButton));
  const detail = $('repair-detail');
  const incident = inspection.mode === 'history'
    ? incidents.find(item => item.opening_run_id === inspection.historicalRunId) : null;
  if (!incident) return empty(detail, 'Select an incident to inspect its recorded run.');
  detail.replaceChildren();
  for (const [label, value] of [
    ['Inspected run', incident.opening_run_id],
    ['Recorded incident', `${incident.id} · ${humanize(incident.state)} · ${incident.reason_code}`],
    ['Failing output', incident.failing_output_ref],
    ['Independent check', incident.check_result_id],
    ['Opened event', String(incident.opened_event_seq)],
  ]) {
    const row = element('div', null, 'contract-line');
    row.dataset.repairField = label.toLowerCase().replaceAll(' ', '-');
    row.append(element('span', label), element('strong', value));
    detail.append(row);
  }
}
function renderOwnerRecord() {
  const record = $('owner-record'), target = $('owner-requirements');
  const visible = state.station === 'owner' && state.slug === 'bookshop' && Boolean(state.board);
  record.hidden = !visible;
  if (!visible) return target.replaceChildren();
  const choice = state.board.operating_selection;
  const requirements = state.board.inherited_requirements;
  const version = state.operatingVersion ?? state.board.latest_version;
  target.replaceChildren();
  for (const [label, field, value] of [
    ['Client requirement set', 'owner-requirement-set', requirements?.requirement_set_id ?? 'No inherited set'],
    ['Frozen requirement hash', 'owner-requirement-hash', requirements?.requirement_set_hash ?? 'none'],
    ['Visible check set hash', 'owner-visible-check-hash', requirements?.visible_check_set_hash ?? 'none'],
    ['Operating version', 'owner-operating-version', choice ? `${choice.selected_version_id} · ${choice.selected_content_hash}` : 'none selected'],
    ['Committed constraint', 'owner-constraint', version?.contract?.must_never.map(humanize).join(', ') ?? 'No committed contract loaded'],
    ['Declared limits in force', 'owner-limits', state.board.unresolved_limits.join(' · ') || 'none'],
  ]) {
    const row = element('div', null, 'contract-line');
    row.dataset.ownerField = field;
    row.append(element('span', label), element('strong', value));
    target.append(row);
  }
}
function renderHandoverIncidents() {
  const target = $('handover-incidents');
  if (!state.board) return empty(target, 'No verified data loaded.');
  if (!state.board.incidents.length) return empty(target, 'No unresolved incident is inherited.');
  target.replaceChildren(...state.board.incidents.map(incidentButton));
}
function publishPresentation(reason) {
  renderInspectionBar();
  const context = { board: state.slug, shiftId: state.loadedShiftId, inspection: { ...inspection } };
  let publication;
  if (['error', 'context', 'history', 'page-lifecycle'].includes(reason)) {
    reportPrevious = null;
    if ($('choose-dialog').open) $('choose-dialog').close();
    if ($('shift-report').open) $('shift-report').close();
    publication = { kind: 'reset', context, reason };
    text('workplace-state', reason === 'error' ? 'Recorded state unavailable. Refresh to inspect verified evidence.' : 'Loading recorded context.');
    resetConsequenceWall(reason === 'error' ? 'Recorded state unavailable.' : 'Loading recorded context.');
    resetStory(reason === 'error' ? 'Unavailable' : 'Loading');
  } else if (reason === 'loading') publication = { kind: 'loading', context, generation: state.generation };
  else {
    if (!state.board) return;
    const view = projectWorkplace({ slug: state.slug, loadedShiftId: state.loadedShiftId,
      generation: state.generation, intent: state.intent, loadState: document.body.dataset.loadState,
      inspection, board: state.board, operatingVersion: state.operatingVersion,
      stationView: state.stationView, run: state.run, outputs: state.outputs, checks: state.checks,
      events: state.events, ledgerStatus: state.ledgerStatus, comparison: state.comparison,
      diagnostic: state.diagnostic, candidates: state.candidates,
      selectedOutputId: state.selected, activeStation: state.station });
    publication = { kind: 'accepted', view, generation: state.generation, intent: state.intent, reason };
    renderTestBench(view);
    renderConsequenceWall(view);
    renderStory(view);
    updateShiftReport(view);
    const verdicts = view.evidence?.checks.map(check => `${check.verdict}: ${check.reasonCode ?? 'recorded check'}`).join('; ');
    text('workplace-state', view.consistency === 'conflict' ? 'Recorded reads disagree. Inspect the workbench; current labels are unavailable.' :
      `${view.context.inspection.mode === 'history' ? 'Historical inspection. ' : 'Current inspection. '}Live version: ${view.operating ? `${view.operating.versionId} (${view.operating.validity})` : 'None selected'}. Saved version: ${view.saved.latestVersionId ?? 'None'}. ` +
      (view.run ? `Inspected run: ${view.run.id}. Executed version: ${view.run.versionId}. ${view.run.purpose} / ${view.run.evidenceMode ?? 'unknown mode'}. ${verdicts || 'Independent evidence incomplete.'}` : 'No run loaded.'));
  }
  latestPresentation = publication;
  workplaceHost?.publish(publication);
}
const LOG_TONES = { fail: 'Fail', pass: 'Pass', info: 'Record', you: 'You' };
const reportContext = view => JSON.stringify([view.context.board, view.context.shiftId, view.context.inspection, view.operating?.selectionId]);
function updateShiftReport(view) {
  const previous = reportPrevious;
  if (view.consistency !== 'conflict') reportPrevious = view;
  const run = view.run;
  const key = `${view.context.board}:${run?.id}`;
  if (!previous || view.consistency === 'conflict' || reportContext(previous) !== reportContext(view) ||
      view.context.inspection.mode !== 'current' || run?.purpose !== 'OPERATION' || run.shiftId !== view.context.shiftId ||
      run.selectionId !== view.operating?.selectionId || !['FINALIZED', 'FAILED'].includes(run.state) ||
      view.slips?.runId !== run.id || previous.slips?.runId === run.id || reportedRuns.has(key)) return;
  reportedRuns.add(key);
  showShiftReport(view, true);
}
function showShiftReport(view, fresh = false) {
  const report = reduceShiftReport(view, state.run, state.checks, state.events, state.board?.operating_selection);
  const count = value => value == null ? 'unknown' : String(value);
  const list = $('report-counts');
  list.replaceChildren();
  for (const [label, value] of [
    ['Requests passed', report.requests.pass], ['Requests failed', report.requests.fail],
    ['Requests errored', report.requests.error], ['Requests without checks', report.requests.none],
    ['Open incidents before', report.openBefore], ['Open incidents after', report.openAfter],
    ['Incidents opened by this run', report.incidentsOpened], ['Incidents resolved by this run', report.incidentsResolved],
  ]) list.append(element('dt', label), element('dd', count(value)));
  text('report-freshness', fresh ? 'New operation report' : 'Recorded history');
  text('report-title', view?.run?.shiftId && view.run.shiftId !== view.context.shiftId ? 'Recorded operation report'
    : state.board?.latest_shift ? `Shift ${state.board.latest_shift.seq} report` : 'Shift report');
  text('report-state', !view?.run ? 'No accepted operation record is loaded.' :
    view.run.purpose !== 'OPERATION' ? 'This inspection is a test, not an operation.' :
    view.run.state === 'FAILED' ? 'The operation failed. These are its recorded results; no success is implied.' :
    ['FINALIZED', 'FAILED'].includes(view.run.state) ? 'Results from the recorded operation.' : 'The operation is unfinished. Results are unknown.');
  text('report-decision', `Run version: ${report.versionLabel ?? 'unknown'}. Backup: ${report.backupLabel ?? 'unknown'}.`);
  const choice = state.board?.operating_selection;
  text('report-rationale', choice?.id === state.run?.selection_id && choice.kind === 'LEARNER_CHOICE'
    ? `Your reason: ${choice.rationale}` : 'No learner decision is linked to this inspected run.');
  text('report-completeness', report.complete ? 'Loaded records are linked. These results do not measure learning.' : 'Evidence is incomplete. Unknown counts are not zero.');
  const dialog = $('shift-report');
  if (!dialog.open) {
    reportOpener = fresh ? $('open-shift-report') : document.activeElement;
    dialog.showModal();
    $('close-shift-report').focus();
  }
}
function openChoose(label) {
  if ($(`open-choose-${label.toLowerCase()}`).disabled) return;
  const candidate = state.comparison?.candidates.find(item => item.label === label);
  if (!candidate) return;
  chooseOpener = $(`open-choose-${label.toLowerCase()}`);
  $('selection-rationale').value = '';
  text('selection-error', '');
  text('choose-title', `Make ${candidate.artifact_version_id} the live version?`);
  const backup = state.comparison.candidates.find(item => item.label !== label);
  text('choose-backup-version', `${backup?.artifact_version_id ?? 'The other tested version'} stays saved. You can test it again later; that test never changes history.`);
  for (const key of ['A', 'B']) {
    const button = $(`select-candidate-${key.toLowerCase()}`);
    button.hidden = key !== label;
    button.textContent = `Make ${candidate.artifact_version_id} live`;
  }
  renderCompare();
  $('choose-dialog').showModal();
  $('selection-rationale').focus();
}
function renderShiftLog(entries) {
  const list = $('shift-log-list');
  text('shift-log-count', `${entries.length} ${entries.length === 1 ? 'entry' : 'entries'}`);
  const shown = entries.filter(entry => logFilter === 'all' || (logFilter === 'check' ? entry.kind === 'check' : entry.tone === 'you'));
  if (!shown.length) { list.replaceChildren(element('li', entries.length ? 'No entries match this filter.' : 'No recorded entries loaded.', 'log-empty')); return; }
  list.replaceChildren(...shown.map(entry => {
    const item = element('li', null, 'log-entry');
    item.dataset.kind = entry.kind; item.dataset.tone = entry.tone;
    const time = element('span', entry.recordedAt ? new Date(entry.recordedAt).toTimeString().slice(0, 5) : '--:--', 'log-time');
    item.append(time, element('span', LOG_TONES[entry.tone], 'log-tone'), element('span', entry.text, 'log-text'));
    if (entry.ids.length) item.append(element('code', entry.ids.join(' · '), 'log-ids'));
    return item;
  }));
}
let storyEntries = [];
function resetStory(word) {
  for (const id of ['status-client', 'status-shift', 'status-live', 'status-incidents', 'status-attempts']) text(id, word);
  storyEntries = []; renderShiftLog(storyEntries);
}
function renderStory(view) {
  const display = state.workplaces.find(board => board.engagement_slug === state.slug);
  const values = statusBarValues(view, { client: display ? display.client ?? display.employer : null,
    shiftSeq: state.board?.latest_shift?.seq ?? null, attemptsRemaining: state.board?.attempts_remaining ?? null });
  for (const key of ['client', 'shift', 'live', 'incidents', 'attempts']) text(`status-${key}`, values[key]);
  storyEntries = logEntries(view, state.run, state.checks, state.events, state.stationView?.investigations ?? [], state.board?.operating_selection ?? null);
  renderShiftLog(storyEntries);
  renderGuide(view);
  syncInspector();
  placeStationTags();
}
// The step guide, owner line, customer bubble and lamps are Bellwether's story
// layer (Gate 3 section 13.5). The guide only navigates: the next action opens a
// station and never sends a request or decides whether a command is allowed. The
// cause draft steers only the chip; it is never sent or credited.
let storyGuide = null;
function renderGuide(view = latestPresentation?.kind === 'accepted' ? latestPresentation.view : null) {
  const bookshop = state.slug === 'bookshop' && Boolean(view);
  $('step-chip').hidden = !bookshop;
  $('next-action-go').hidden = !bookshop;
  $('next-action-task').hidden = bookshop;
  if (!bookshop) {
    storyGuide = null;
    text('next-action-task', (stations[state.station] ?? stations.service)[0]);
    for (const id of ['customer-bubble', 'owner-bubble']) $(id).hidden = true;
    for (const button of document.querySelectorAll('#bookshop-stations [data-station]')) delete button.dataset.resting;
    return;
  }
  storyGuide = guideStep(view, { activeStation: state.station, causeDraft: $('cause-input').value.trim() !== '',
    falsifierDraft: $('falsifier-input').value.trim() !== '' });
  // The chip is a live region: write it only when its words change, so typing a draft is not announced.
  const announce = (id, value) => { if ($(id).textContent !== value) text(id, value); };
  announce('step-chip-count', storyGuide.step ? `Step ${storyGuide.step} of 7` : 'Step unknown');
  announce('step-chip-name', storyGuide.step ? storyGuide.name : '');
  $('step-chip-reason').hidden = !storyGuide.blockedReason;
  announce('step-chip-reason', storyGuide.blockedReason ?? '');
  $('step-chip').dataset.status = storyGuide.status;
  text('next-action-go', storyGuide.step ? storyGuide.name : 'Open the current station');
  // One narrator bubble (Gate 3 section 14.2 rule 2). It names its station, so that
  // station's own tag rests hidden while it speaks.
  const speaker = narrator(view, storyGuide, state.outputs.find(output => output.id === state.selected) ?? null);
  const said = role => speaker?.role === role ? speaker : null;
  $('owner-bubble').hidden = !said('owner');
  text('owner-bubble-text', said('owner')?.text ?? '');
  $('customer-bubble').hidden = !said('customer');
  text('customer-bubble-label', said('customer')?.label ?? ''); text('customer-bubble-text', said('customer')?.text ?? '');
  const lampText = id => (view.lamps ?? []).find(item => item.stationId === id)?.text;
  for (const [id, station] of [['customer-bubble-station', 'customers'], ['owner-bubble-station', 'owner']])
    text(id, [document.querySelector(`#bookshop-stations [data-station="${station}"] > span:last-child`)?.firstChild?.textContent, lampText(station)].filter(Boolean).join(' · '));
  const resting = restingTags(view, storyGuide);
  for (const button of document.querySelectorAll('#bookshop-stations [data-station]'))
    button.dataset.resting = button.dataset.station === speaker?.stationId ? 'speaker' : String(resting.has(button.dataset.station));
  for (const item of view.lamps ?? []) {
    const button = document.querySelector(`#bookshop-stations [data-station="${item.stationId}"]`);
    if (!button) continue;
    button.dataset.lamp = item.tone;
    button.querySelector('.lamp-text').textContent = item.text;
    if (item.stationId === view.attention) button.dataset.attention = 'true'; else delete button.dataset.attention;
  }
}
const narrowLayout = () => window.matchMedia('(max-width: 760px)').matches;
// The inspector is the existing #station-panel. Opening it never sends a request;
// the scene only learns how much of the stage it covers.
function syncInspector() {
  const world = $('workplace-world');
  world.dataset.inspector = inspectorOpen || expandedWork ? 'open' : 'closed';
  world.style.setProperty('--status-h', `${$('status-bar').offsetHeight}px`);
  world.style.setProperty('--chip-h', $('step-chip').hidden ? '0px' : `${$('step-chip').offsetHeight + 12}px`);
  const covered = inspectorOpen && !expandedWork && !narrowLayout()
    ? $('station-panel').getBoundingClientRect().right - $('workplace-canvas').getBoundingClientRect().left : 0;
  inspectorCover = Math.max(0, covered);
  workplaceHost?.setInspector({ open: covered > 0, widthPx: inspectorCover });
}
function openInspector() { inspectorOpen = true; syncInspector(); }
function closeInspector(returnFocus = true) {
  if (expandedWork) setExpandedWork(false);
  inspectorOpen = false; syncInspector();
  // Gate 3 section 14.2 rule 3: closing the inspector sends your bot home.
  openStationId = null; workplaceHost?.setOpenStation(null);
  if (returnFocus) document.querySelector(`.room-hotspots:not([hidden]) [data-station="${state.station}"]`)?.focus({ preventScroll: true });
}
// Tags sit just above their projected anchor. A tag that would cover another tag,
// the status bar, step chip, next action, graphics notice or shift log tries up to
// six rows up or down and at most 1.2 of its own width sideways, in steps of 0.3,
// nearest rows first. When no spot is
// free, it takes the spot that covers the least of the tags already placed, then
// the least of everything else (Gate 3 section 13.6). The inspector is not avoided
// here: only the scene's view offset keeps tags clear of it.
let tagAnchors = {}, crewPoints = {};
// The scene reports station and crew points together; a walk alone reports only the
// crew, so only the "You" chip moves and the tag layout is left as it is.
function placeAnchors({ crew, ...positions }) {
  crewPoints = crew ?? {};
  if (Object.keys(positions).length) placeStationTags(positions); else placeYouChip();
}
// The "You" chip is the only text on your bot (Gate 3 section 14.2 rule 6).
function placeYouChip() {
  const chip = $('you-chip'), point = crewPoints.you;
  chip.hidden = !point?.visible;
  if (chip.hidden) return;
  chip.style.setProperty('--chip-x', `${Math.round(point.x)}px`);
  chip.style.setProperty('--chip-y', `${Math.round(point.y)}px`);
}
function placeStationTags(positions = tagAnchors) {
  tagAnchors = positions;
  const stage = document.querySelector('.room').getBoundingClientRect();
  const local = rect => ({ left: rect.left - stage.left, top: rect.top - stage.top, right: rect.right - stage.left, bottom: rect.bottom - stage.top });
  const taken = [$('status-bar'), $('shift-log'), document.querySelector('.graphics-controls'), $('step-chip'), $('next-action')]
    .map(node => node.getBoundingClientRect()).filter(rect => rect.width && rect.height).map(local);
  const covers = (box, rects) => rects.reduce((sum, rect) => sum
    + Math.max(0, Math.min(box.right, rect.right) - Math.max(box.left, rect.left)) * Math.max(0, Math.min(box.bottom, rect.bottom) - Math.max(box.top, rect.top)), 0);
  const placed = [];
  const less = (a, b) => covers(a, placed) - covers(b, placed) || covers(a, taken) - covers(b, taken);
  // The evidence path has no object of its own; it sits between the queue and your service.
  const midpoint = (a, b) => a?.visible && b?.visible ? { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, visible: true } : null;
  const anchors = { ...positions, pipeline: positions.pipeline ?? midpoint(positions.customers, positions.service) };
  const tags = [...document.querySelectorAll('#station-tags [data-station]')].map(button => ({ button, point: anchors[button.dataset.station] }));
  // Keep each station's own object pickable: no tag covers a projected anchor.
  for (const point of Object.values(positions)) if (point?.visible) taken.push({ left: point.x - 12, top: point.y - 12, right: point.x + 12, bottom: point.y + 12 });
  for (const { button, point } of tags.sort((a, b) => (a.point?.y ?? 0) - (b.point?.y ?? 0))) {
    if (!point?.visible || button.closest('[hidden]')) {
      button.style.removeProperty('--tag-x'); button.style.removeProperty('--tag-y');
      delete button.dataset.anchored; delete button.dataset.anchorX;
      continue;
    }
    const width = button.offsetWidth, height = button.offsetHeight, step = height + 4;
    // A tag whose anchor is clear of the inspector stays clear of it; an anchor
    // under the inspector is left where it is so the fault stays visible.
    const minLeft = inspectorCover && point.x >= inspectorCover ? inspectorCover + 8 : 8;
    const clampLeft = x => Math.min(Math.max(minLeft, x), Math.max(minLeft, stage.width - width - 8));
    const box = ([left, top]) => ({ left, top, right: left + width, bottom: top + height });
    const candidates = [0, -1, 1, -2, 2, -3, 3, -4, 4, -5, 5, -6, 6].flatMap(row => [0, .3, -.3, .6, -.6, .9, -.9, 1.2, -1.2].map(shift =>
      [clampLeft(point.x - width / 2 + shift * width), point.y - height - 6 + row * step]));
    const inside = candidates.filter(([, y]) => y >= 8 && y + height <= stage.height - 8);
    const [left, top] = inside.find(spot => covers(box(spot), placed) + covers(box(spot), taken) === 0)
      ?? inside.reduce((best, spot) => less(box(spot), box(best)) < 0 ? spot : best, inside[0] ?? candidates[0]);
    placed.push(box([left, top]));
    button.style.setProperty('--tag-x', `${Math.round(left)}px`);
    button.style.setProperty('--tag-y', `${Math.round(top)}px`);
    button.dataset.anchored = 'true';
    button.dataset.anchorX = String(Math.round(point.x));
  }
  placeBubbles();
}
// Over the drawn room each bubble sits above its speaker bot; over the static room it
// sits next to its station's tag. It tries above, then below, then further out, and
// takes the first spot clear of every tag, panel and the other bubble, or the least
// covering one. Narrow layouts stack it instead.
function placeBubbles() {
  placeYouChip();
  const layer = $('station-tags').getBoundingClientRect();
  const local = r => ({ left: r.left - layer.left, top: r.top - layer.top, right: r.right - layer.left, bottom: r.bottom - layer.top });
  const room = local(document.querySelector('.room').getBoundingClientRect());
  // An open inspector covers the left of the room; bubbles stay to its right.
  room.left += inspectorCover;
  const taken = [...document.querySelectorAll('.room-hotspots:not([hidden]) [data-station]'), $('status-bar'), $('step-chip'),
    $('next-action'), $('shift-log'), document.querySelector('.graphics-controls')]
    .map(node => node.getBoundingClientRect()).filter(r => r.width && r.height).map(local);
  // Your bot's chip outweighs everything else: a bubble never hides who you are.
  const chip = [$('you-chip').getBoundingClientRect()].filter(r => r.width && r.height).map(local);
  const area = (box, rects) => rects.reduce((sum, r) => sum
    + Math.max(0, Math.min(box.right, r.right) - Math.max(box.left, r.left)) * Math.max(0, Math.min(box.bottom, r.bottom) - Math.max(box.top, r.top)), 0);
  const overlap = box => area(box, taken) + 1000 * area(box, chip);
  const drawn = document.querySelector('.room').dataset.graphics === 'ready';
  for (const [id, station, role] of [['customer-bubble', 'customers', 'customer'], ['owner-bubble', 'owner', 'owner']]) {
    const bubble = $(id), tag = document.querySelector(`#bookshop-stations [data-station="${station}"]`), speaker = drawn ? crewPoints[role] : null;
    if (bubble.hidden || !tag || narrowLayout()) { bubble.style.removeProperty('--bubble-x'); bubble.style.removeProperty('--bubble-y'); continue; }
    // The canvas and the tag layer share the room's origin, so a bot's point is already local.
    const t = speaker?.visible ? { left: speaker.x - 20, right: speaker.x + 20, top: speaker.y - 4, bottom: speaker.y + 4 } : local(tag.getBoundingClientRect());
    const width = bubble.offsetWidth, height = bubble.offsetHeight;
    // The static room's tag layer is narrower than the stage, so bubbles may use the whole room.
    const clampX = x => Math.min(Math.max(room.left + 8, x), Math.max(room.left + 8, room.right - width - 8));
    const clampY = y => Math.min(Math.max(room.top + 8, y), Math.max(room.top + 8, room.bottom - height - 8));
    // Nearest first: directly above or below the tag, then beside it, then one or two rows further out.
    // Gate 1: a speaker bot's words appear above it, never below.
    const rows = [0, 1, 2].flatMap(row => speaker?.visible ? [t.top - height - 6 - row * 24] : [[t.top - height - 6 - row * 24], [t.bottom + 6 + row * 24]]).flat();
    const spots = [...rows.flatMap(y => [t.left, t.right - width, t.left - width / 2, t.left - width, t.right].map(x => [x, y])),
      ...(speaker?.visible ? [] : [[t.right + 6, t.top], [t.left - width - 6, t.top]])].map(([x, y]) => [clampX(x), clampY(y)]);
    const box = ([x, y]) => ({ left: x, top: y, right: x + width, bottom: y + height });
    const [x, y] = spots.find(spot => overlap(box(spot)) === 0) ?? spots.reduce((best, spot) => overlap(box(spot)) < overlap(box(best)) ? spot : best);
    taken.push(box([x, y]));
    bubble.style.setProperty('--bubble-x', `${Math.round(x)}px`);
    bubble.style.setProperty('--bubble-y', `${Math.round(y)}px`);
  }
}
async function initializeGraphics() {
  if (workplaceHost || hostLoading) return;
  const epoch = ++hostEpoch; hostLoading = true;
  hostTimer = setTimeout(() => {
    if (epoch !== hostEpoch) return;
    hostEpoch += 1; hostLoading = false; hostTimer = null;
    $('graphics-status').dataset.state = 'unavailable';
    text('graphics-status', '3D view unavailable. Your workbench is ready. (load-timeout)');
    document.querySelector('[data-graphics-retry]').hidden = false;
    document.querySelector('[data-graphics-retry]').disabled = false;
  }, 8000);
  try {
    const { createWorkplaceHost } = await import('./workplace-host.js');
    if (epoch !== hostEpoch) return;
    clearTimeout(hostTimer); hostTimer = null;
    workplaceHost = createWorkplaceHost({ container: $('workplace-canvas'), fallback: document.querySelector('img.room-art'), status: $('graphics-status'),
      onConsequence({ count }) { showWallTrace(count); },
      onAnchors: placeAnchors,
      onHover(stationId) {
        for (const button of document.querySelectorAll('.room-hotspots [data-hover]')) delete button.dataset.hover;
        if (stationId) document.querySelector(`.room-hotspots:not([hidden]) [data-station="${stationId}"]`)?.setAttribute('data-hover', '');
      },
      onStation({ board, shiftId, stationId }) {
        if (latestPresentation?.kind !== 'accepted' || board !== state.slug || shiftId !== state.loadedShiftId || latestPresentation.generation !== state.generation || latestPresentation.intent !== state.intent) return;
        if (!document.querySelector(`#${board}-stations [data-station="${stationId}"]`)) return;
        activateStation(stationId);
      } });
    if (expandedWork) workplaceHost.setExpanded(true);
    syncInspector();
    workplaceHost.setOpenStation(openStationId);
    if (latestPresentation) workplaceHost.publish(latestPresentation);
  } catch {
    if (epoch !== hostEpoch) return;
    $('graphics-status').dataset.state = 'unavailable';
    text('graphics-status', '3D view unavailable. Your workbench is ready. Graphics installation needs repair.');
    document.querySelector('[data-graphics-retry]').hidden = false;
    document.querySelector('[data-graphics-retry]').disabled = true;
  } finally { if (epoch === hostEpoch) { clearTimeout(hostTimer); hostTimer = null; hostLoading = false; } }
}
const terminal = run => !run || ['FINALIZED', 'FAILED'].includes(run.state);
const humanize = value => value.toLowerCase().replaceAll('_', ' ');
const requestId = prefix => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function empty(target, text) { target.replaceChildren(element('p', text, 'empty')); }
function text(id, value) { $(id).textContent = value; }
async function api(path, options = {}) {
  const response = await fetch('/api' + path, { ...options, headers: { 'Content-Type': 'application/json' } });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Request failed (${response.status}). Refresh to load verified state.`);
  }
  return response.json();
}
function renderWorkplace() {
  const select = $('workplace-board');
  select.replaceChildren(...state.workplaces.map(board => {
    const option = element('option', `${board.role_name} · ${board.client ?? board.employer}${board.availability === 'AVAILABLE' ? '' : ' · awaiting operator review'}`);
    option.value = board.engagement_slug;
    option.disabled = board.availability !== 'AVAILABLE';
    return option;
  }));
  select.value = state.slug;
  select.disabled = state.pending || hasUnsavedDraft() || !state.workplaces.length;
}
async function switchWorkplace() {
  const slug = $('workplace-board').value;
  if (state.pending || hasUnsavedDraft() || !state.workplaces.some(board => board.engagement_slug === slug && board.availability === 'AVAILABLE')) {
    $('workplace-board').value = state.slug;
    text('workplace-message', 'Save or discard the draft and finish the current action before changing boards.');
    return;
  }
  if (expandedWork) setExpandedWork(false);
  state.generation += 1; state.intent += 1;
  inspection = { mode: 'current', historicalRunId: null };
  publishPresentation('context');
  state.slug = slug; state.loadedShiftId = null; state.comparison = null;
  state.candidates = { A: null, B: null }; state.selected = null;
  for (const id of ['cause-input', 'falsifier-input', 'public-test-input', 'assist-message', 'treatment-input', 'selection-rationale']) $(id).value = '';
  state.station = northline() ? 'brief' : gtm() ? 'signals' : 'service';
  const url = new URL(location.href); url.searchParams.set('board', slug); url.hash = northline() ? 'brief' : gtm() ? 'signals' : 'board';
  history.replaceState(null, '', url);
  text('workplace-message', '');
  await refresh();
}
function buildStations(prefix, names, labels) {
  const hotspots = $(`${prefix}-stations`);
  if (hotspots.children.length) return;
  names.forEach((name, index) => {
    const button = element('button', undefined, `station ${prefix}-${name}`);
    button.dataset.station = name;
    button.append(element('span', String(index + 1).padStart(2, '0'), 'station-marker'), element('span', labels[index]));
    button.addEventListener('click', () => activateStation(name));
    hotspots.append(button);
    const link = element('a', labels[index]); link.href = `#${name}`; link.dataset.view = name;
    link.addEventListener('click', event => { event.preventDefault(); navigate(name); });
    $(`${prefix}-journey`).append(link);
  });
}
function renderRoom() {
  const display = state.workplaces.find(board => board.engagement_slug === state.slug);
  if (!display) return;
  document.body.dataset.board = display.engagement_slug;
  document.title = `${display.client ?? display.employer} · Shiftwork`;
  text('client-name', `YOUR CLIENT / ${display.client ?? display.employer}`);
  text('role-description', `Your role: ${display.role_name}. Fictional client and simulated work.`);
  text('room-title', northline() ? 'An integration the counter can trust.' : gtm() ? 'Route every signal to the right owner, once.' : 'You keep this service running.');
  text('artifact-name', northline() ? 'Northline integration' : gtm() ? 'Stonebridge workflow' : 'Bellwether service');
  document.querySelector('[data-file="checks"]').textContent = northline() ? 'Acceptance tests' : 'Visible checks';
  document.querySelector('[data-file="history"]').textContent = northline() ? 'Discovery record' : 'Change log';
  for (const file of ['checks', 'history']) document.querySelector(`[data-file="${file}"]`).hidden = gtm();
  const room = document.querySelector('.room');
  room.setAttribute('aria-label', northline() ? 'Northline deployment workshop' : gtm() ? 'Stonebridge revenue floor' : 'Bellwether operational room');
  for (const id of ['bookshop-stations', 'bookshop-journey']) $(id).hidden = northline() || gtm();
  for (const id of ['northline-stations', 'northline-journey', 'northline-art']) $(id).toggleAttribute('hidden', !northline());
  for (const id of ['gtm-stations', 'gtm-journey', 'gtm-art']) $(id).toggleAttribute('hidden', !gtm());
  document.querySelector('img.room-art').hidden = northline() || gtm() || room.dataset.graphics === 'ready';
  document.querySelector('.room-bookplate').hidden = northline() || gtm();
  $('deployment-protocol').hidden = !northline();
  if (northline()) buildStations('northline', ['brief', 'map', 'bench', 'acceptance', 'rollout', 'handover'],
    ['Deployment brief', 'System map', 'Integration bench', 'Acceptance', 'Rollout', 'Handover']);
  if (gtm()) buildStations('gtm', ['signals', 'rules', 'workflow', 'wall'],
    ['Signal intake', 'Qualification rules', 'Workflow bench', 'Pipeline wall']);
}
function deploymentFile(target, filename) {
  const selected = state.operatingVersion;
  const draft = state.draft;
  for (const [owner, files, version] of [['Selected version', selected?.files, selected?.id], ['Current draft', draft?.files, state.board?.draft_base_version_id]]) {
    const detail = element('details');
    detail.dataset.deploymentFile = filename; detail.dataset.fileOwner = owner; detail.dataset.versionId = version ?? '';
    detail.append(element('summary', `${owner} · ${filename} · ${version ?? 'not loaded'}`), element('pre', files?.[filename] ?? 'No verified file loaded.'));
    target.append(detail);
  }
}
function deploymentEvents(target, events) {
  if (!events.length) return empty(target, 'No recorded events. No outcome is implied.');
  target.replaceChildren(...events.map(event => {
    const row = element('article', undefined, 'deployment-event'); row.dataset.deploymentEvent = String(event.seq);
    row.append(element('strong', humanize(event.event_type)), element('p', `Event ${event.seq} · cause ${event.cause_refs.join(', ')}`, 'evidence-meta'));
    row.append(element('pre', JSON.stringify(event.payload, null, 2)));
    return row;
  }));
}
function renderDeployment() {
  for (const id of ['map-records', 'pilot-records', 'handover-records']) $(id).replaceChildren();
  if (!northline() || !state.board) return;
  for (const file of ['discovery.md', 'permissions.json']) deploymentFile($('map-records'), file);
  deploymentEvents($('pilot-records'), state.events.filter(event => event.event_type !== 'HANDOVER_DECLARED'));
  deploymentFile($('handover-records'), 'runbook.md');
  const records = element('div');
  deploymentEvents(records, state.events.filter(event => event.event_type === 'HANDOVER_DECLARED'));
  $('handover-records').append(records);
  $('operate-pilot').disabled = $('run-shift').disabled;
  text('pilot-help', $('run-help').textContent);
}
const PIPELINE_GROUPS = [['pipeline-owners', 'OWNER_ASSIGNED'], ['pipeline-clocks', 'SLA_CLOCK_STARTED'],
  ['pipeline-escalations', 'HANDOFF_ESCALATED']];
function pipelineRow(event) {
  const payload = event.payload;
  const row = element('div', null, 'pipeline-row');
  row.dataset.pipelineEvent = String(event.seq);
  row.dataset.pipelineType = event.event_type;
  row.dataset.pipelineSignal = payload.signal_ref ?? '';
  row.dataset.pipelineOwner = payload.owner ?? '';
  row.dataset.pipelineRecord = payload.record_ref ?? '';
  row.dataset.pipelineTerminal = payload.terminal_action ?? '';
  row.dataset.pipelineConsequence = payload.consequence ?? '';
  row.dataset.pipelineWeight = String(payload.weight ?? '');
  row.dataset.pipelineRun = event.cause_refs[0] ?? '';
  row.dataset.pipelineCheck = event.cause_refs[1] ?? '';
  row.dataset.pipelineOutput = event.cause_refs[2] ?? '';
  row.dataset.synthetic = String(event.synthetic);
  row.append(element('strong', `${payload.signal_ref} · ${payload.owner ?? humanize(event.event_type)}`));
  row.append(element('small', `Event ${event.seq} · record ${payload.record_ref ?? 'none'} · terminal action ${payload.terminal_action ?? 'none'} · consequence ${payload.consequence ?? 'none'} · weight ${payload.weight ?? 'none'} · rules ${payload.rule_version} · catalog ${payload.catalog_version} · mission ${payload.mission_version}`, 'pipeline-fact'));
  row.append(element('small', `Captured by run ${event.cause_refs[0]} · check ${event.cause_refs[1]} · output ${event.cause_refs[2]}`, 'evidence-meta'));
  const detail = element('details');
  detail.append(element('summary', 'Inspect the recorded payload'), element('pre', JSON.stringify(payload, null, 2)));
  row.append(detail);
  return row;
}
function renderPipelineWall() {
  for (const [id] of PIPELINE_GROUPS) empty($(id), 'No verified data loaded.');
  empty($('pipeline-incidents'), 'No verified data loaded.');
  text('pipeline-counts', '');
  text('pipeline-ownership-status', 'No verified ownership records loaded.');
  if (!gtm() || !state.board) return;
  const events = state.events;
  const signals = [...new Set(events.map(event => event.payload.signal_ref).filter(Boolean))];
  const problems = signals.flatMap(signal => {
    const owners = events.filter(event => event.event_type === 'OWNER_ASSIGNED' && event.payload.signal_ref === signal);
    const labels = [];
    if (!owners.length || owners.some(event => !event.payload.owner)) labels.push(`${signal}: no recorded owner`);
    if (owners.length > 1) labels.push(`${signal}: ${owners.length} duplicate owner records`);
    return labels;
  });
  text('pipeline-ownership-status', problems.join(' · ') || 'No missing or duplicate owner records in the loaded ledger.');
  for (const [id, type] of PIPELINE_GROUPS) {
    const rows = events.filter(event => event.event_type === type);
    if (rows.length) $(id).replaceChildren(...rows.map(pipelineRow));
    else empty($(id), type === 'HANDOFF_ESCALATED'
      ? 'No operation recorded a human-handoff escalation. The compared workloads that do escalate are experiments, and an experiment never writes pipeline state.'
      : `No operation recorded ${humanize(type)}. Only operating the exact selection writes pipeline state.`);
  }
  const target = $('pipeline-incidents');
  const opened = events.filter(event => event.event_type === 'INCIDENT_OPENED');
  const rows = state.board.incidents.map(incident => {
    const event = opened.find(item => item.seq === incident.opened_event_seq);
    const row = element('div', null, 'pipeline-row');
    row.dataset.pipelineIncident = incident.id;
    row.dataset.pipelineIncidentState = incident.state;
    row.dataset.pipelineIncidentReason = incident.reason_code;
    row.dataset.pipelineIncidentRun = incident.opening_run_id;
    row.dataset.pipelineIncidentOutput = incident.failing_output_ref;
    row.dataset.pipelineIncidentCheck = incident.check_result_id;
    row.dataset.pipelineIncidentEvent = String(incident.opened_event_seq);
    row.dataset.pipelineSignal = event?.payload.signal_ref ?? '';
    row.dataset.pipelineFailedTasks = (event?.payload.failed_task_ids ?? []).join(',');
    row.dataset.pipelineTrace = String(event?.payload.decision_trace?.length ?? 0);
    row.append(element('strong', `${incident.id} · ${humanize(incident.state)} · ${incident.reason_code}`));
    row.append(element('small', `Signal ${event?.payload.signal_ref ?? 'not recorded'} · failed required tasks ${(event?.payload.failed_task_ids ?? []).join(', ') || 'none'} · decision trace ${event?.payload.decision_trace?.length ?? 0} recorded task results`, 'pipeline-fact'));
    row.append(element('small', `Opened by run ${incident.opening_run_id} · check ${incident.check_result_id} · output ${incident.failing_output_ref} · ledger event ${incident.opened_event_seq}`, 'evidence-meta'));
    return row;
  });
  for (const event of events.filter(item => item.event_type === 'INCIDENT_RESOLVED')) {
    const row = element('div', null, 'pipeline-row');
    row.dataset.pipelineIncident = event.payload.incident_id;
    row.dataset.pipelineIncidentState = 'RESOLVED';
    row.dataset.pipelineResolvingVersion = event.payload.resolving_version_id;
    row.dataset.pipelineRun = event.cause_refs[0];
    row.dataset.pipelineCheck = event.cause_refs[1];
    row.dataset.pipelineEvent = String(event.seq);
    row.dataset.synthetic = String(event.synthetic);
    row.append(element('strong', `${event.payload.incident_id} · resolved`));
    row.append(element('small', `Resolved by operating ${event.payload.resolving_version_id} · rules ${event.payload.rule_version}. A choice alone never closes an incident; only linked operational evidence does.`, 'pipeline-fact'));
    row.append(element('small', `Recorded by run ${event.cause_refs[0]} · regression check ${event.cause_refs[1]} · ledger event ${event.seq}`, 'evidence-meta'));
    rows.push(row);
  }
  if (rows.length) target.replaceChildren(...rows);
  else empty(target, 'No incident was opened or resolved by an operation. An empty wall implies no outcome.');
  text('pipeline-counts', `${state.board.incidents.length} unresolved of ${state.board.total_incidents} recorded in total · ${events.length} ledger events · chain ${humanize(state.board.chain_status)}`);
  $('operate-pipeline').disabled = $('run-shift').disabled;
  text('pipeline-help', $('run-help').textContent);
}
function clearEvidence() {
  if (downloadUrl) URL.revokeObjectURL(downloadUrl);
  downloadUrl = null;
  delete document.body.dataset.evidence;
  $('selected-evidence').removeAttribute('data-run-id');
  $('selected-evidence').removeAttribute('data-request-ordinal');
  empty($('selected-evidence'), 'No executed customer request selected.');
}
function clearData(message) {
  state.ledgerStatus = 'unknown';
  state.operatingVersion = null;
  state.board = null; state.draft = null; state.stationView = null; state.run = null;
  state.outputs = []; state.checks = []; state.events = []; state.selected = null; state.diagnostic = null;
  clearEvidence();
  text('load-message', message);
  text('session-state', 'Not connected');
  text('shift-number', 'No shift loaded');
  text('version-state', 'No verified version loaded');
  text('version-hash', '');
  empty($('selection-summary'), 'No live version loaded.');
  text('run-state', 'No run loaded');
  text('evidence-attempts', 'Attempts not loaded.');
  document.querySelector('[data-station="repair"]').setAttribute('aria-disabled', 'true');
  for (const id of ['metric-requests', 'metric-incidents', 'metric-attempts']) text(id, '…');
  for (const id of ['metric-chain', 'service-tag', 'queue-tag', 'repair-tag', 'attempt-detail', 'event-detail', 'investigation-tag', 'compare-tag']) text(id, 'Not loaded');
  text('incident-tag', 'Not loaded · Synthetic scenario');
  for (const id of ['artifact-detail', 'incident-list', 'limit-list', 'customer-list']) empty($(id), 'No verified data loaded.');
  empty($('orientation-list'), 'Orientation loads with your shift.');
  empty($('investigation-list'), 'No verified entries loaded.');
  empty($('diagnostic-result'), 'No verified diagnostic loaded.');
  text('test-tag', 'No diagnostic reported');
  $('test-tag').dataset.state = 'NONE';
  delete $('test-tag').dataset.missingEvidence;
  empty($('failed-request'), 'No executed request loaded.');
  text('investigate-state', 'No shift loaded');
  text('source-note', '');
  text('diagnostic-note', '');
  text('assist-standing', '');
  text('assist-budget', '');
  text('assist-denial', '');
  empty($('assist-events'), 'No assistance recorded.');
  text('investigate-error', '');
  text('compare-state', 'No shift loaded');
  text('compare-note', '');
  text('compare-summary', '');
  $('comparison-outcome').replaceChildren();
  text('compare-error', '');
  text('next-state', 'No shift loaded');
  text('next-tag', 'Not loaded');
  text('next-help', 'Loading shift actions…');
  text('next-error', '');
  for (const id of ['next-inheritance', 'next-tests', 'next-history', 'next-experiment', 'handover-incidents']) empty($(id), 'No verified data loaded.');
  $('close-shift').disabled = true; $('open-next-shift').disabled = true;
  text('repair-state', 'No incident loaded.');
  empty($('repair-incidents'), 'No verified data loaded.');
  empty($('repair-detail'), 'Select an incident to inspect its recorded run.');
  $('owner-record').hidden = true;
  empty($('owner-requirements'), 'No verified requirements loaded.');
  text('selection-note', 'A complete eligible comparison is required.');
  text('selection-error', '');
  empty($('candidate-list'), 'No candidates loaded.');
  empty($('comparison-slots'), 'No comparison loaded.');
  $('source-ordinal').replaceChildren();
  $('source-ordinal').disabled = true;
  for (const id of ['append-investigation', 'request-assist', 'run-diagnostic', 'freeze-candidate-a', 'freeze-candidate-b', 'run-comparison', 'select-candidate-a', 'select-candidate-b']) $(id).disabled = true;
  $('open-shift').disabled = true; $('run-shift').disabled = true;
  text('run-help', 'Refresh to load available actions.');
  for (const id of ['map-records', 'pilot-records', 'handover-records']) empty($(id), 'No verified data loaded.');
  $('operate-pilot').disabled = true;
  for (const id of ['pipeline-owners', 'pipeline-clocks', 'pipeline-escalations', 'pipeline-incidents']) empty($(id), 'No verified data loaded.');
  text('pipeline-counts', '');
  $('operate-pipeline').disabled = true;
  text('pipeline-ownership-status', 'No verified ownership records loaded.');
  renderDraftEditor();
}

async function refresh(runId = null) {
  // Candidate ownership outlives the temporary loading/error board clear.
  const previousShiftId = state.loadedShiftId;
  const generation = ++state.generation;
  const selected = state.selected;
  clearTimeout(pollTimer);
  document.body.dataset.loadState = 'loading';
  publishPresentation('loading');
  clearData('Loading your shift…');
  try {
    const runtime = await api('/runtime');
    text('runtime-notice', runtime.notice);
    const workplaces = await api('/boards');
    const available = workplaces.find(item => item.engagement_slug === state.slug && item.availability === 'AVAILABLE');
    state.workplaces = workplaces;
    renderWorkplace();
    if (!available) throw new Error('This board is awaiting operator review. Choose an available role board.');
    const board = await api(engagementPath('board'));
    const historicalRunId = !runId && inspection.mode === 'history' ? inspection.historicalRunId : null;
    const run = runId ? await api(`/runs/${encodeURIComponent(runId)}`)
      : historicalRunId ? await api(`/runs/${encodeURIComponent(historicalRunId)}`)
      : board.latest_run;
    const [draft, stationView, ledger, outputs, checks, operatingVersion] = await Promise.all([
      board.latest_shift ? api(`/shifts/${encodeURIComponent(board.latest_shift.id)}/artifact`) : null,
      board.latest_shift ? api(`/shifts/${encodeURIComponent(board.latest_shift.id)}/investigations`) : null,
      api(engagementPath('ledger')),
      run ? api(`/runs/${encodeURIComponent(run.id)}/outputs`) : [],
      run ? api(`/runs/${encodeURIComponent(run.id)}/checks`) : [],
      board.operating_selection ? api(`/artifact-versions/${encodeURIComponent(board.operating_selection.selected_version_id)}`) : null,
    ]);
    if (generation !== state.generation) return;
    let comparison = stationView?.latest_experiment?.kind === 'QUALIFYING_COMPARISON' ? stationView.latest_experiment
      : previousShiftId === board.latest_shift?.id ? state.comparison : null;
    if (comparison && comparison !== stationView?.latest_experiment) {
      try { comparison = await api(`/experiments/${encodeURIComponent(comparison.id)}`); }
      catch { comparison = null; }
    }
    if (generation !== state.generation) return;
    Object.assign(state, { board, loadedShiftId: board.latest_shift?.id ?? null, draft, stationView, run, outputs, checks, operatingVersion, comparison, events: ledger.events, ledgerStatus: ledger.chain_status });
    if (previousShiftId && previousShiftId !== board.latest_shift?.id) {
      publishPresentation('context');
      state.candidates = { A: null, B: null };
    }
    if (state.comparison && state.comparison.shift_id === board.latest_shift?.id) for (const candidate of state.comparison.candidates) {
      state.candidates[candidate.label] ??= { id: candidate.artifact_version_id, content_hash: candidate.artifact_content_hash };
    }
    state.selected = outputs.some(output => output.id === selected) ? selected : outputs[0]?.id ?? null;
    document.body.dataset.loadState = board.latest_shift ? 'ready' : 'empty';
    text('load-message', board.latest_shift ? '' : 'No shift yet. Open one to begin your service history.');
    renderBoard();
    activateStation(state.station, false);
    publishPresentation('refresh');
    if (!terminal(run)) pollTimer = setTimeout(() => refresh(run.id), 1000);
    return true;
  } catch (error) {
    if (generation !== state.generation) return;
    clearData(error.message);
    document.body.dataset.loadState = 'error';
    publishPresentation('error');
  }
}

function renderBoard() {
  renderRoom();
  const board = state.board;
  const version = board.latest_version;
  const shift = board.latest_shift;
  const needsChoice = board.operating_status === 'NEEDS_FIRST_CHOICE';
  text('session-state', shift ? `Shift ${shift.seq} · ${needsChoice ? 'needs first choice' : shift.state}` : needsChoice ? 'Needs first choice' : 'Ready for your first shift');
  text('shift-number', shift ? `Shift ${String(shift.seq).padStart(2, '0')}` : 'Not started');
  text('metric-requests', board.requests_run);
  text('metric-incidents', board.incidents.length);
  text('metric-attempts', board.attempts_remaining);
  text('metric-chain', board.chain_status === 'VALID' ? 'Verified' : 'Not verified');
  text('attempt-detail', `${board.attempts_used} of ${board.attempt_limit} attempts used`);
  text('evidence-attempts', `${board.attempts_remaining} attempt${board.attempts_remaining === 1 ? '' : 's'} remaining in the current shift · ${board.attempts_used} of ${board.attempt_limit} used`);
  document.querySelector('[data-station="repair"]').setAttribute('aria-disabled', String(!board.incidents.length));
  text('event-detail', `${board.ledger_event_count} recorded events`);
  text('service-tag', board.operating_selection ? `${board.operating_selection.selected_version_id} · ${humanize(board.operating_status)}` : version ? `${version.id} · candidate only` : 'Draft · not frozen');
  text('queue-tag', `${state.outputs.length} executed requests`);
  text('incident-tag', `${board.incidents.length} unresolved · Synthetic scenario`);
  text('repair-tag', board.incidents.length ? 'Incident available · read only' : 'No unresolved incident');
  const entries = state.stationView?.investigations ?? [];
  text('investigation-tag', !state.stationView ? 'Not loaded' : entries.length ? `${entries.length} recorded` : 'Orientation only');
  text('version-state', version ? `${version.id} · latest saved${board.operating_selection?.selected_version_id === version.id ? ' and selected' : ''}` : 'Draft · no frozen version');
  text('version-hash', version ? `Content hash ${version.content_hash}` : '');
  const choice = board.operating_selection;
  const summary = $('selection-summary');
  summary.replaceChildren();
  // Field keys stay stable when a label is reworded in plain words.
  for (const [field, label, value] of [
    ['latest-saved', 'Latest saved', board.latest_saved_version_id ?? 'none'],
    ['operating-choice', 'Live version', choice ? `${choice.selected_version_id} · ${choice.selected_content_hash} · ${humanize(choice.state)}` : 'none'],
    ['retained-alternative', 'Backup version', choice?.retained_alternative_version_id ?? 'none'],
    ['comparison', 'Comparison', choice?.comparison_id ?? 'none'],
    ['original-requirement-hash', 'Original requirement hash', choice?.requirement_set_hash ?? 'none'],
    ['executed-version', 'Executed version', state.run ? `${state.run.artifact_version_id} · ${state.run.id}` : 'none'],
  ]) {
    const row = element('div', null, 'contract-line');
    row.dataset.selectionField = field;
    row.append(element('span', label), element('strong', value));
    summary.append(row);
  }
  const adapter = state.run?.adapter;
  const liveDiagnostic = state.stationView?.latest_experiment?.trials?.some(trial => trial.evidence_mode === 'ISOLATED_LIVE');
  text('execution-note', state.run?.evidence_mode === 'ISOLATED_LIVE'
    ? `Isolated live ${humanize(state.run.purpose)} · ${state.run.id} · ${state.run.artifact_version_id}. Synthetic business consequences are independently checked. The simulated role is not a credential.`
    : liveDiagnostic
    ? `An isolated ${humanize(state.stationView.latest_experiment.kind)} ran. Experiments leave operational history unchanged. The simulated role is not a credential.`
    : state.run?.purpose === 'LEGACY_OPERATION'
    ? `Legacy operation · ${state.run.evidence_mode ?? 'evidence mode unknown'}. Missing historical inputs remain unknown; old captures are not a fresh test. No live model or sandbox is established.`
    : adapter === 'local_process'
    ? 'Offline trusted-fixture execution. Not hostile-code isolation. No live model or sandbox. The simulated role is not a credential.'
    : adapter === 'recorded' ? 'Recorded replay: captured bytes, not execution of your current artifact. No live model or sandbox. The simulated role is not a credential.'
    : 'Offline client. No live model or sandbox connection. The simulated role is not a credential.');
  const incidents = $('incident-list');
  if (!board.incidents.length) empty(incidents, 'No unresolved incidents. The room reflects the recorded state.');
  else incidents.replaceChildren(...board.incidents.map(incidentButton));
  const limits = [...new Set([...(version?.contract.declared_limits ?? []), ...board.unresolved_limits])];
  if (!limits.length) empty($('limit-list'), 'No limits declared.');
  else {
    const list = element('ul');
    list.append(...limits.map(limit => element('li', limit, 'limit-item')));
    $('limit-list').replaceChildren(list);
  }
  $('open-shift').disabled = state.pending || inspection.mode !== 'current' || shift?.state === 'open';
  const operationRecorded = board.latest_run?.purpose === 'OPERATION' && board.latest_run?.state === 'FINALIZED' && board.latest_run?.shift_id === shift?.id;
  $('run-shift').disabled = state.pending || inspection.mode !== 'current' || !version || !shift?.operation_allowed || shift?.state !== 'open' || board.attempts_remaining === 0 || !terminal(board.latest_run) ||
    operationRecorded;
  text('run-help', needsChoice ? 'Operation is blocked. Compare qualifying repairs and explicitly choose an eligible tested version; saving or freezing a draft does not choose it.'
    : !version ? 'No frozen version is available to operate.'
    : !terminal(board.latest_run) ? 'Your run is in progress. Results appear only after the controller records them.'
    : shift?.state !== 'open' ? 'This shift is closed. Its recorded evidence stays available.'
    : operationRecorded ? "This shift's operation run is recorded. Close the shift at Next shift; the operating version runs in the next shift."
    : board.attempts_remaining === 0 ? 'No attempt remains in this shift, so the controller will not accept another run. Close the shift at Next shift to continue.'
    : 'Runs the selected version. A started attempt consumes one reservation, even if it fails.');
  renderArtifact();
  renderDeployment();
  renderPipelineWall();
  renderRepairTray();
  renderOwnerRecord();
  renderInspectionBar();
}

function renderArtifact() {
  const target = $('artifact-detail');
  if (!state.board) return empty(target, 'No verified artifact loaded.');
  const files = state.draft?.files ?? {};
  target.replaceChildren();
  if (state.file === 'contract') {
    const version = state.operatingVersion ?? state.board.latest_version;
    const contract = version?.contract;
    if (!contract) return empty(target, 'No committed contract. Authoring is not available in this build; no stance is preselected.');
    for (const [label, value] of [
      ['Requirement version', `${version.id} · ${version.content_hash}`],
      ['Committed constraint', contract.must_never.map(humanize).join(', ')],
      [state.operatingVersion ? 'Operating stance' : 'Latest saved stance', Object.values(contract.selections).map(humanize).join(', ')],
      ['Response time limit', `${contract.response_time_limit_ms} ms`],
      ['Contract catalog', `Version ${contract.catalog_version}`],
      ['Frozen requirement hash', state.board.inherited_requirements?.requirement_set_hash ?? 'No qualifying comparison selected yet'],
    ]) {
      const row = element('div', null, 'contract-line');
      row.dataset.requirementField = label.toLowerCase().replaceAll(' ', '-');
      row.append(element('span', label), element('strong', value)); target.append(row);
    }
  } else if (state.file === 'files') {
    target.append(element('p', 'Files in the frozen version', 'empty'));
    const frozen = element('ul');
    frozen.append(...state.board.artifact_files.map(name => element('li', name)));
    target.append(frozen);
    target.append(element('p', 'Current draft files · read only here. The hash above identifies the frozen version, not this editable draft.', 'empty'));
    for (const [name, content] of Object.entries(files)) {
      const detail = element('details'); detail.append(element('summary', name), element('pre', content)); target.append(detail);
    }
  } else {
    const name = northline() ? (state.file === 'checks' ? 'acceptance_tests.py' : 'discovery.md') : gtm() ? 'service.py' : state.file === 'checks' ? 'checks.json' : 'change_log.md';
    target.append(element('p', northline() ? 'Current draft worksheet. Independent acceptance comes from the captured service and controller checks.' : gtm() ? 'Current draft workflow. Independent qualification comes from the captured output and controller checks.' : state.file === 'checks' ? 'Current draft checks. Visible-check scoring is not available in this build.' : 'Current draft change log. Decisions are not inferred from saves or runs.', 'empty'));
    target.append(files[name] ? element('pre', files[name]) : element('p', `No ${name} file in the draft.`, 'empty'));
  }
}

function evidenceStep(number, label) {
  const section = element('section', null, 'evidence-step');
  const heading = element('h3', null, 'step-label');
  heading.append(element('b', number), document.createTextNode(label));
  section.append(heading); return section;
}
function renderCustomers() {
  text('inspection-verdict', 'Independent evidence incomplete.');
  const focusedOutput = document.activeElement?.dataset.outputId;
  clearEvidence();
  const run = state.run;
  text('run-state', run ? `${run.id} · ${run.state}` : 'No run yet');
  const list = $('customer-list');
  if (!state.outputs.length) {
    empty(list, !run ? 'Requests stay hidden until they execute.' : run.state === 'FAILED' ? 'Run failed. No customer output was captured.' : 'No customer outputs captured yet.');
    return;
  }
  list.replaceChildren(...state.outputs.map(output => {
    const button = element('button', null, 'customer-button');
    button.dataset.outputId = output.id;
    button.setAttribute('aria-pressed', String(state.selected === output.id));
    button.append(element('span', String(output.request_ordinal).padStart(2, '0')), element('span', output.request_text));
    button.addEventListener('click', () => { state.intent += 1; state.selected = output.id; renderCustomers(); publishPresentation('output'); });
    return button;
  }));
  if (focusedOutput) [...list.children].find(button => button.dataset.outputId === focusedOutput)?.focus({ preventScroll: true });
  const output = state.outputs.find(item => item.id === state.selected);
  if (!output) return;
  const selected = $('selected-evidence');
  selected.dataset.runId = output.run_id;
  selected.dataset.requestOrdinal = output.request_ordinal;
  selected.replaceChildren();
  for (const [field, label, value] of [
    ['purpose', 'Execution purpose', humanize(run.purpose)],
    ['mode', 'Evidence mode', run.evidence_mode ?? 'unknown'],
    ['version', 'Executed version', run.artifact_version_id],
    ['snapshot', 'Frozen public snapshot', output.public_shop_snapshot_hash ?? 'unknown'],
  ]) {
    const row = element('div', null, 'contract-line');
    row.dataset.executionField = field;
    row.append(element('span', label), element('strong', value));
    selected.append(row);
  }
  const request = evidenceStep(1, 'Executed customer request');
  request.append(element('p', output.request_text, 'evidence-text request-quote'), element('p', `${output.run_id} · request ${output.request_ordinal} · artifact ${run.artifact_version_id}`, 'evidence-meta'));
  const answer = evidenceStep(2, 'Exact service output');
  answer.append(element('p', output.customer_answer?.display_text ?? 'No validated customer answer. Inspect the captured bytes below.', 'evidence-text'));
  answer.append(element('p', `HTTP ${output.http_status ?? 'not received'} · ${output.elapsed_ms ?? 'unknown'} ms${output.transport_error ? ` · ${output.transport_error}` : ''}`, 'evidence-meta'));
  const bytes = bodyBytes(output.body_base64);
  const raw = element('details'); raw.append(element('summary', `Captured body · ${bytes.length} bytes`));
  try { raw.append(element('pre', new TextDecoder('utf-8', { fatal: true }).decode(bytes))); }
  catch { raw.append(element('p', 'The body is not valid UTF-8. Base64 and download preserve every byte.', 'empty')); }
  const base64 = element('pre', output.body_base64); base64.dataset.bodyBase64 = output.body_base64;
  raw.append(element('p', 'Original bytes encoded as base64', 'evidence-meta'), base64);
  downloadUrl = URL.createObjectURL(new Blob([bytes], { type: 'application/octet-stream' }));
  const download = element('a', 'Download original bytes', 'download');
  download.href = downloadUrl; download.download = `${output.id}.bin`; raw.append(download); answer.append(raw);
  const record = evidenceStep(3, 'Supporting public record');
  if (output.public_shop_record) {
    const publicRecord = output.public_shop_record;
    record.append(element('p', [publicRecord.title, publicRecord.edition].filter(Boolean).join(' · ') || publicRecord.record_id, 'evidence-text'));
    const value = typeof publicRecord.value === 'string' ? humanize(publicRecord.value) : JSON.stringify(publicRecord.value);
    record.append(element('p', `${humanize(publicRecord.kind)}: ${value}`, 'public-value'));
    record.append(element('p', `Record age ${publicRecord.record_age_ms} ms`, 'evidence-meta'));
    const source = element('details');
    source.append(element('summary', 'Inspect the public record'), element('pre', JSON.stringify(publicRecord, null, 2)));
    record.append(source, element('p', `Public record ${output.public_shop_record_ref}\nRun snapshot ${output.public_shop_snapshot_hash}`, 'evidence-meta'));
  } else record.append(element('p', run.purpose === 'LEGACY_OPERATION'
    ? 'Historical public context unknown. The original output and checks remain available; current files cannot fill missing old inputs.'
    : state.checks.some(check => check.run_id === run.id && check.public_check_id?.startsWith('task:'))
    ? 'Task checks use the frozen public state and the citations in the captured answer. No single record represents this multi-task request.'
    : 'No public comparison record. Sealed expectations are not shown.', 'empty'));
  const comparison = evidenceStep(4, 'Independent check result');
  const linked = selectEvidence(output, state.checks, state.events);
  text('inspection-verdict', linked.checks.length ? linked.checks.map(check => `${check.verdict}${check.reason_code ? `: ${check.reason_code}` : ''}`).join('; ') : 'Independent evidence incomplete.');
  if (!linked.checks.length) comparison.append(element('p', 'No independent result recorded for this output.', 'empty'));
  for (const check of linked.checks) {
    const row = element('div', null, 'result-row'); row.dataset.verdict = check.verdict; row.dataset.checkId = check.id;
    row.append(element('strong', `${humanize(check.verdict)}${check.reason_code ? ` · ${check.reason_code}` : ''}`), element('small', check.public_check_id ? `Visible check ${check.public_check_id}` : 'Independent sealed check · expectation withheld'));
    comparison.append(row);
  }
  const ledger = evidenceStep(5, 'Recorded ledger consequence');
  ledger.dataset.syntheticRegion = 'event'; ledger.append(element('span', 'Synthetic scenario', 'synthetic'));
  if (!linked.events.length) ledger.append(element('p', 'No linked ledger event recorded. No outcome is implied.', 'empty'));
  for (const event of linked.events) {
    const row = element('div', null, 'event-row'); row.dataset.eventSeq = event.seq;
    const link = event.derivation ?? null;
    const current = link && inspection.mode === 'current' && link.run_id === run.id;
    const source = !link ? 'administrative' : current ? 'current' : 'historical';
    const incident = state.board?.incidents?.find(item => item.opened_event_seq === event.seq || item.resolved_event_seq === event.seq) ?? null;
    row.dataset.eventSource = source;
    row.dataset.eventMeaning = !link ? 'administrative' : link.verdict === 'pass' ? 'recorded' : 'negative';
    if (incident) row.dataset.incidentId = incident.id;
    row.append(element('strong', humanize(event.event_type)));
    row.append(element('small', `Event ${event.seq} · ${WALL_SOURCE_TEXT[source]}${link ? ` · result ${link.check_id} · output ${link.observed_ref} · request ${link.request_ordinal} · verdict ${link.verdict}${link.reason_code ? ` · ${link.reason_code}` : ''}` : ' · no derivation'}${incident ? ` · incident ${incident.id}` : ''}`, 'evidence-meta'));
    ledger.append(row);
  }
  selected.append(request, answer, record, comparison, ledger);
  if (run.state === 'FINALIZED' && ['customers', 'pipeline'].includes(state.station)) document.body.dataset.evidence = 'finalized';
  if (['customers', 'pipeline'].includes(state.station)) text('service-tag', `Output from ${run.artifact_version_id}`);
}

function renderInvestigations(station) {
  const list = $('investigation-list');
  if (!station.investigations.length) return empty(list, 'No entry yet. Orientation stays available before your first entry.');
  list.replaceChildren(...station.investigations.map(entry => {
    const row = element('div', null, 'investigation-entry');
    row.dataset.investigationId = entry.id;
    row.dataset.authoredBy = entry.authored_by;
    if (entry.revision_of_id) row.dataset.revisionOf = entry.revision_of_id;
    row.append(element('strong', `${entry.id} · ${entry.authored_by === 'learner' ? 'your entry' : entry.authored_by}${entry.revision_of_id ? ` · revises ${entry.revision_of_id}` : ''}`));
    row.append(element('p', `Source ${entry.source_run_id} · request ${entry.source_request_ordinal}`, 'evidence-meta'));
    for (const [label, value] of [['Cause', entry.cause], ['What would prove you wrong', entry.falsifier], ['Public test', entry.public_test]]) {
      const line = element('div', null, 'contract-line');
      line.append(element('span', label), element('strong', value));
      row.append(line);
    }
    if (entry.revision_of_id) row.append(element('p', `The earlier entry ${entry.revision_of_id} stays in this list unchanged.`, 'evidence-meta'));
    return row;
  }));
}
function repeatedDiagnosticTrial() {
  const experiment = state.diagnostic ?? state.stationView?.latest_diagnostic;
  if (!(experiment?.public_repetitions > 1)) return null;
  const selected = $('diagnostic-result').dataset.selectedRunId;
  const missed = experiment.repetition_summary?.tasks.find(row => row.misses > 0)?.miss_run_ids?.[0];
  return experiment.trials.find(trial => trial.run_id === selected)
    ?? experiment.trials.find(trial => trial.run_id === missed) ?? experiment.trials[0] ?? null;
}
function renderSource(station) {
  const select = $('source-ordinal');
  const diagnostic = repeatedDiagnosticTrial();
  const run = diagnostic ? {id: diagnostic.run_id, state: diagnostic.state, evidence_mode: diagnostic.evidence_mode} : state.run;
  const previous = select.value;
  select.replaceChildren(...(diagnostic?.outputs ?? state.outputs).map(output => {
    const option = element('option', `Request ${output.request_ordinal}`);
    option.value = String(output.request_ordinal);
    return option;
  }));
  if (previous && [...select.options].some(option => option.value === previous)) select.value = previous;
  const ready = Boolean(station && run && (diagnostic?.outputs ?? state.outputs).length);
  select.disabled = !ready;
  text('append-investigation', station?.latest_investigation_id ? 'Record revision of latest entry' : 'Record entry');
  $('append-investigation').disabled = state.pending || !ready;
  text('source-note', ready
    ? `Source ${run.id} · ${run.state}${run.evidence_mode ? ` · ${run.evidence_mode}` : ''}. Your entry cites this executed request. A revision keeps every earlier entry.`
    : run ? 'This run captured no request ordinal, so no entry can cite it.' : `No executed run is loaded, so no entry can cite a source request yet. ${station?.bootstrap_available ? '' : station?.bootstrap_reason ?? ''}`.trim());
}
function renderAssist(station) {
  text('assist-standing', station?.assist_reason ?? '');
  text('assist-budget', station ? `${station.assist_used} of ${station.assist_limit} help calls used this shift. Failed calls also count.` : '');
  for (const option of $('assist-role').options) option.disabled = !station?.assist_allowed_roles?.includes(option.value);
  if ($('assist-role').selectedOptions[0]?.disabled) $('assist-role').value = 'HINT';
  const list = $('assist-events');
  if (!station?.assist_events?.length) empty(list, 'No assistance recorded.');
  else list.replaceChildren(...station.assist_events.map(event => {
    const row = element('div', null, 'investigation-entry');
    row.dataset.assistEventId = event.id;
    row.append(element('strong', `${humanize(event.role)} · ${event.model_id} · ${humanize(event.state)}`));
    if (event.reported_model_id || event.elapsed_ms !== null || event.input_tokens !== null || event.output_tokens !== null) {
      row.append(element('p', `Provider reported ${event.reported_model_id ?? 'unknown model'} · ${event.input_tokens ?? 'unknown'} input tokens · ${event.output_tokens ?? 'unknown'} output tokens · ${event.elapsed_ms ?? 'unknown'} ms`, 'evidence-meta'));
    }
    if (event.state === 'COMPLETE') {
      row.append(element('p', event.response_text, 'evidence-text'));
      if (event.role === 'PATCH_PROPOSAL') {
        row.append(element('p', event.accepted === null ? 'Proposal only. It has not changed code, checks, or selection.' :
          `${event.accepted ? 'Accepted' : 'Rejected'} as help attribution. Code remains yours to edit.`, 'evidence-meta'));
      }
      if (event.accepted !== null && event.role !== 'PATCH_PROPOSAL') row.append(element('p',
        event.accepted ? 'Marked as used help.' : 'Marked as dismissed help.', 'evidence-meta'));
      if (event.accepted === null) for (const [label, accepted] of [['Mark used', true], ['Dismiss', false]]) {
        const button = element('button', label, 'button secondary');
        button.type = 'button'; button.disabled = state.pending;
        button.addEventListener('click', () => decideAssist(event.id, accepted));
        row.append(button);
      }
    } else if (event.state === 'FAILED') row.append(element('p', `Help failed: ${event.failure_code}. This call used budget.`, 'denial'));
    else row.append(element('p', 'Help request reserved. Refresh for its result.', 'help-text'));
    return row;
  }));
  $('request-assist').disabled = state.pending || !station || ((northline() || gtm()) && !station.assist_available);
}
function renderDiagnostic(station) {
  const experiment = state.diagnostic ?? station?.latest_diagnostic ?? null;
  const trial = repeatedDiagnosticTrial() ?? experiment?.trials?.[0] ?? null;
  const trialState = trial && REPORTED_TEST_STATES.has(trial.state) ? trial.state : null;
  const output = trial?.outputs?.[0] ?? null;
  const result = $('diagnostic-result');
  $('run-diagnostic').disabled = state.pending || !(station?.latest_investigation_id || station?.bootstrap_available) || !state.board?.latest_saved_version_id;
  if (!station) { text('diagnostic-note', ''); return empty(result, 'No shift loaded.'); }
  if (!experiment) {
    text('diagnostic-note', station.bootstrap_available && !station.latest_investigation_id
      ? 'Freeze your inherited draft to own an exact version, then run the one public source diagnostic. It cannot qualify a version or change business history.'
      : station.latest_investigation_id
        ? 'Ready. The diagnostic runs your frozen version against the reviewed public request and state, then checks each requested task.'
        : 'Record your cause, what would prove you wrong and a public test first. The diagnostic cites your entry and cannot run before it exists.');
    return empty(result, 'No public diagnostic has run in this shift, and none can qualify a version.');
  }
  text('diagnostic-note', experiment.declared_treatment);
  result.dataset.experimentId = experiment.id;
  result.replaceChildren();
  $('diagnostic-repetitions').disabled = state.pending || experiment.state === 'RUNNING';
  if (experiment.public_repetitions > 1) {
    result.append(element('p', `${experiment.trials.filter(row => ['COMPLETE', 'FAILED'].includes(row.state)).length} of ${experiment.public_repetitions} retained repetitions finished.`, 'evidence-meta'));
    if (experiment.summary_refusal) result.append(element('p', experiment.summary_refusal, 'denial'));
    try {
      for (const line of diagnosticRateLines(experiment)) result.append(element('p', line, 'evidence-text'));
    } catch (error) { result.append(element('p', error.message, 'denial')); }
    if (experiment.repetition_summary) {
      result.append(element('p', experiment.repetition_summary.limits, 'help-text'));
      result.append(element('p', experiment.repetition_summary.stop_rule_triggered
        ? 'No required task was missed. Stop: the starter defect was not observed. The operator must decide the next defect or request shapes.'
        : 'Observed incident: investigate a retained run where a required task is missing. The selected repetition below is the source for your entry.', 'evidence-text'));
    }
    const label = element('label', 'Inspect a retained repetition');
    const select = element('select'); select.id = 'diagnostic-retained-run'; label.htmlFor = select.id;
    for (const row of experiment.trials) {
      const option = element('option', `Run ${row.execution_ordinal}: ${row.run_id} · ${row.state} · ${row.evidence_mode}`);
      option.value = row.run_id; select.append(option);
    }
    select.value = trial?.run_id ?? '';
    select.addEventListener('change', () => {
      result.dataset.selectedRunId = select.value;
      renderDiagnostic(station); renderSource(station);
    });
    const field = element('div', null, 'field'); field.append(label, select); result.append(field);
  }
  for (const [label, value] of [
    ['Evidence class', `${experiment.context_evidence_class} · ${humanize(experiment.kind)}`],
    ['Trial state', trial ? `${trialState ?? 'Not reported'} · candidate ${trial.candidate_label}` : 'No trial reserved'],
    ['Frozen context', `${experiment.context_hash} · workload ${trial?.workload_id ?? 'not reserved'}`],
  ]) {
    const line = element('div', null, 'contract-line');
    line.append(element('span', label), element('strong', value));
    result.append(line);
  }
  const missing = trial?.missing_evidence ?? [];
  if (missing.length) result.append(element('p', `Missing evidence: ${missing.join('; ')}`, 'denial'));
  if (!trial || !['COMPLETE', 'FAILED'].includes(trial.state)) return;
  let step = 0;
  if (output) {
    step += 1;
    const request = evidenceStep(step, 'Frozen incident request');
    request.append(element('p', output.request_text, 'evidence-text request-quote'));
    result.append(request);
    step += 1;
    const answer = evidenceStep(step, 'Exact output the starter produced');
    let decoded = null;
    try { decoded = new TextDecoder('utf-8', { fatal: true }).decode(bodyBytes(output.body_base64)); } catch { decoded = null; }
    answer.append(element('p', decoded ?? 'The captured body is not valid UTF-8. The base64 below preserves every byte.', 'evidence-text'));
    answer.append(element('p', `HTTP ${output.http_status ?? 'not received'} · ${output.elapsed_ms ?? 'unknown'} ms${output.transport_error ? ` · ${output.transport_error}` : ''}`, 'evidence-meta'));
    const raw = element('details');
    raw.append(element('summary', `Captured body · ${bodyBytes(output.body_base64).length} bytes`));
    const base64 = element('pre', output.body_base64);
    base64.dataset.bodyBase64 = output.body_base64;
    raw.append(element('p', 'Original bytes encoded as base64', 'evidence-meta'), base64);
    answer.append(raw);
    result.append(answer);
  }
  step += 1;
  const customer = evidenceStep(step, 'Rendered customer answer');
  customer.append(element('p', trial.customer_text ?? 'No customer answer was rendered for this trial.', 'evidence-text'));
  result.append(customer);
  step += 1;
  const assessment = evidenceStep(step, 'Independently assessed required tasks');
  if (!trial.task_assessments.length) assessment.append(element('p', 'No task assessment was recorded for this trial.', 'empty'));
  for (const row of trial.task_assessments) {
    const item = element('div', null, 'result-row');
    item.dataset.taskId = row.task_id;
    item.dataset.outcome = row.outcome;
    item.dataset.verdict = row.mandatory_pass ? 'pass' : 'fail';
    item.append(element('strong', `${row.task_id} · ${humanize(row.outcome)}${row.reason_codes.length ? ` · ${row.reason_codes.join(', ')}` : ''}`));
    item.append(element('small', `${row.mandatory_pass ? 'Mandatory task passes' : 'Mandatory task fails'} · request ${row.request_ordinal}`));
    assessment.append(item);
  }
  result.append(assessment);
  step += 1;
  const observations = evidenceStep(step, 'Observed interpretation and tool use');
  if (!trial.observations.length) observations.append(element('p', 'The service reported no interpretation or tool events for this run. Nothing is inferred from their absence.', 'empty'));
  for (const observation of trial.observations) {
    const row = element('div', null, 'event-row');
    row.append(element('strong', humanize(observation.kind)), element('pre', JSON.stringify(observation.public_payload_json, null, 2)));
    observations.append(row);
  }
  result.append(observations);
  step += 1;
  const eligibility = evidenceStep(step, 'Eligibility');
  const line = element('div', null, 'result-row');
  line.dataset.verdict = experiment.eligible ? 'pass' : 'fail';
  line.dataset.eligible = String(experiment.eligible);
  line.append(element('strong', experiment.eligible ? 'Eligible' : 'Not eligible · this diagnostic cannot qualify a version'), element('small', experiment.eligibility_reason));
  eligibility.append(line);
  result.append(eligibility);
}
function failedRequestOutput() {
  const linkedFailure = output => selectEvidence(output, state.checks, state.events).checks.some(check => check.verdict !== 'pass');
  return state.outputs.find(output => output.id === state.selected && linkedFailure(output))
    ?? state.outputs.find(linkedFailure)
    ?? state.outputs.find(output => output.id === state.selected)
    ?? state.outputs[0] ?? null;
}
function renderFailedRequest() {
  const target = $('failed-request');
  const run = state.run;
  target.replaceChildren();
  if (!run) return empty(target, 'No executed request is loaded. Refresh to inspect a recorded failure.');
  const output = failedRequestOutput();
  if (!output) return empty(target, run.state === 'FAILED' ? 'The run failed before a customer request was executed.' : 'No customer output is recorded for this run.');
  const linked = selectEvidence(output, state.checks, state.events);
  target.dataset.runId = run.id;
  target.dataset.outputId = output.id;
  target.append(element('p', output.request_text, 'evidence-text request-quote'));
  target.append(element('p', `Run ${run.id} · request ${output.request_ordinal} · executed ${run.artifact_version_id} · ${humanize(run.purpose)} · ${run.evidence_mode ?? 'unknown mode'}`, 'evidence-meta'));
  target.append(element('p', output.customer_answer?.display_text ?? 'No validated customer answer is recorded for this request.', 'evidence-text'));
  const failed = linked.checks.filter(check => check.verdict !== 'pass');
  target.append(element('p', failed.length
    ? `Reported independent evidence: ${failed.map(check => `${humanize(check.verdict)}${check.reason_code ? ` · ${check.reason_code}` : ''}`).join('; ')}`
    : linked.checks.length ? 'Reported independent evidence is linked. Read it before stating a cause.' : 'Independent evidence is incomplete for this request.',
    'evidence-meta'));
}
function renderInvestigate() {
  const station = state.stationView;
  text('investigate-state', station ? `${station.shift_id} · ${station.opening_mode ? humanize(station.opening_mode) : 'opening mode unknown'} · ${station.latest_investigation_id ?? 'no entry yet'}` : 'No shift loaded');
  renderFailedRequest();
  const orientation = $('orientation-list');
  orientation.replaceChildren(...(station?.orientation?.steps ?? ['Orientation loads with your shift.']).map(step => element('li', step)));
  if (station) renderInvestigations(station); else empty($('investigation-list'), 'No verified entries loaded.');
  renderAssist(station);
  renderSource(station);
  renderDiagnostic(station);
}
function renderCompare() {
  renderDraftEditor();
  const board = state.board;
  const shift = board?.latest_shift ?? null;
  const compare = state.board ? state.comparison : null;
  const evidence = $('compare-evidence');
  evidence.replaceChildren();
  if (compare) for (const [field, label, value] of [
    ['purpose', 'Purpose', humanize(compare.kind)],
    ['mode', 'Evidence mode', compare.context_evidence_class],
    ['context', 'Frozen context', compare.context_hash],
    ['history', 'Operational history', 'Unchanged by experiments'],
  ]) {
    const row = element('div', null, 'contract-line');
    row.dataset.comparisonField = field;
    row.append(element('span', label), element('strong', value));
    evidence.append(row);
  }
  const candidates = state.candidates;
  text('compare-state', shift ? `${shift.id} · ${compare ? `${compare.id} · ${humanize(compare.state)}` : 'no comparison reserved'}` : 'No shift loaded');
  text('compare-tag', !shift ? 'Not loaded' : compare ? `${compare.trials.length} slots · ${humanize(compare.state)}` : 'Not reserved');
  const selectedHere = Boolean(compare && board?.operating_selection?.comparison_id === compare.id);
  const rationale = $('selection-rationale').value.trim();
  const eligible = label => compare?.outcome?.status === 'COMPLETE' &&
    compare.outcome.eligibility.some(item => item.candidate_label === label && item.eligible);
  for (const label of ['A', 'B']) {
    const blocked = state.pending || !shift || shift.state !== 'open' || selectedHere || !eligible(label);
    $('open-choose-' + label.toLowerCase()).disabled = blocked;
    $('select-candidate-' + label.toLowerCase()).disabled = blocked || !rationale;
    const candidate = compare?.candidates.find(item => item.label === label);
    text('open-choose-' + label.toLowerCase(), candidate ? `Choose ${candidate.artifact_version_id}…` : `Choose ${label}…`);
  }
  if (selectedHere && $('choose-dialog').open) $('choose-dialog').close();
  text('selection-note', selectedHere ? `Choice ${board.operating_selection.id} is recorded. Selected ${board.operating_selection.selected_version_id} · ${board.operating_selection.selected_content_hash}; retained ${board.operating_selection.retained_alternative_version_id}. Saving or testing does not change it.`
    : !compare ? 'Run a qualifying comparison first.'
    : compare.outcome?.status !== 'COMPLETE' ? 'The comparison must finish complete and comparable before a choice.'
    : !eligible('A') && !eligible('B') ? 'Neither candidate is eligible under the frozen requirements.'
    : !rationale ? 'Write a rationale, then choose an eligible exact version.'
    : 'Your choice will keep the other tested version and original requirement hash in history.');
  const list = $('candidate-list');
  if (!shift) empty(list, 'No shift loaded.');
  else list.replaceChildren(...['A', 'B'].map(label => {
    const version = candidates[label];
    const row = element('div', null, 'contract-line');
    row.dataset.candidateLabel = label;
    row.append(element('span', `Candidate ${label}`), element('strong', version ? `${version.id} · content hash ${version.content_hash}` : 'not frozen yet'));
    return row;
  }));
  const editable = shift?.state === 'open';
  const treatment = $('treatment-input').value.trim();
  for (const id of ['freeze-candidate-a', 'freeze-candidate-b']) $(id).disabled = state.pending || !shift || !editable || hasUnsavedDraft();
  $('run-comparison').disabled = state.pending || !shift || !editable || !candidates.A || !candidates.B || candidates.A.id === candidates.B.id || !state.stationView?.latest_investigation_id || !treatment;
  text('compare-note', !shift ? 'Open a shift to compare candidates.'
    : !editable ? 'This shift is closed. Its recorded comparison evidence stays available.'
    : !candidates.A || !candidates.B ? 'Freeze two distinct candidate versions to reserve a comparison. Freezing never selects one.'
    : candidates.A.id === candidates.B.id ? 'The two candidates are the same frozen version. Freeze a second, different version.'
    : !state.stationView?.latest_investigation_id ? 'Record your cause, what would prove you wrong and a public test first. A comparison cites your investigation entry and cannot run before it exists.'
    : !treatment ? 'Name the one declared treatment that differs between the two candidates.'
    : 'The controller requires operator-sealed workloads and protected variants before reservation. Draft material is refused. This station derives no winner.');
  const slots = $('comparison-slots');
  const outcomeView = $('comparison-outcome');
  if (!compare) { text('compare-summary', ''); outcomeView.replaceChildren(); return empty(slots, 'Every slot, its run, version, batch count and missing evidence appear here once reserved.'); }
  const protectedStatus = compare.protected_counts
    ? Object.entries(compare.protected_counts).map(([label, count]) => `${label}: ${count.captured} captured, ${count.missing} missing of ${count.reserved}`).join(' · ')
    : 'protected capture counts appear after the comparison ends';
  const missingSlots = compare.trials.filter(trial => !trial.run_id || (trial.missing_evidence?.length ?? 0)).length;
  const outcome = compare.outcome;
  text('compare-summary', `${compare.candidates.map(candidate => `Candidate ${candidate.label} · ${candidate.artifact_version_id} · ${candidate.artifact_content_hash.slice(0, 12)}…`).join(' · ')} · ${outcome?.status ?? 'INCOMPLETE'} · public requests per candidate ${compare.shared_public_denominator_requests} · protected steps per candidate ${compare.protected_denominator_requests_per_candidate} · ${protectedStatus} · ${missingSlots} missing slot${missingSlots === 1 ? '' : 's'} · no winner derived here`);
  outcomeView.replaceChildren();
  if (outcome) {
    const note = element('p', `${compare.context_evidence_class} evidence. Public efficiency excludes protected steps. Non-completion categories are incidences and may overlap. Unknown usage or cost is never treated as zero.`, 'comparison-outcome-note');
    outcomeView.append(note);
    if (compare.state === 'INVALIDATED' || outcome.status !== 'COMPLETE') {
      outcomeView.append(element('p', compare.state === 'INVALIDATED'
        ? 'This comparison was invalidated. Its evidence is not comparable and cannot qualify a version.'
        : 'This comparison is not comparable. Its evidence cannot qualify a version until a complete comparable outcome is recorded.', 'denial'));
    }
    const fields = [
      ['Public requests', 'public_denominator_requests'], ['Useful completions', 'useful_completions'],
      ['Incorrect outputs', 'incorrect_outputs'], ['Justified refusals', 'justified_refusals'],
      ['Unjustified refusals', 'unjustified_refusals'], ['Justified referrals', 'justified_referrals'],
      ['Unjustified referrals', 'unjustified_referrals'], ['Justified clarifications', 'justified_clarifications'],
      ['Unjustified clarifications', 'unjustified_clarifications'], ['Missing outputs', 'missing_outputs'],
      ['Protected steps', 'protected_denominator'], ['Protected passed', 'protected_passed'],
      ['Protected failed', 'protected_failed'], ['Protected missing', 'protected_missing'],
      ['Recorded public model calls', 'service_calls'], ['Public input tokens', 'input_tokens'],
      ['Public output tokens', 'output_tokens'], ['Public model latency ms', 'service_latency_ms'],
      ['Public provisioning latency ms', 'provisioning_latency_ms'],
      ['Public cost minor units', 'cost_minor_units'],
    ];
    for (const metrics of outcome.candidate_metrics) {
      const label = metrics.candidate_label;
      const eligibility = outcome.eligibility.find(item => item.candidate_label === label);
      const card = element('section', null, 'comparison-outcome-card');
      card.dataset.candidateLabel = label;
      card.dataset.eligible = String(eligibility.eligible);
      card.append(element('h4', `Candidate ${label} · ${eligibility.eligible ? 'eligible' : 'blocked'}${eligibility.blocking_reason_codes.length ? ` · ${eligibility.blocking_reason_codes.join(', ')}` : ''}`));
      card.append(element('p', eligibility.blocking_reason_codes.length
        ? `Blocking reasons: ${eligibility.blocking_reason_codes.join(', ')}`
        : 'Blocking reasons: none recorded.', 'evidence-meta'));
      const list = element('dl');
      for (const [name, key] of fields) {
        const value = element('dd', metrics[key] ?? 'unknown');
        value.dataset.metric = key;
        list.append(element('dt', name), value);
      }
      card.append(list);
      outcomeView.append(card);
    }
  }
  slots.replaceChildren(...compare.trials.map(trial => {
    const row = element('div', null, 'comparison-slot');
    row.dataset.pair = String(trial.pair_ordinal);
    row.dataset.executionOrdinal = String(trial.execution_ordinal);
    row.dataset.candidateLabel = trial.candidate_label;
    row.dataset.workloadId = trial.workload_id;
    row.dataset.requestCount = String(trial.request_count);
    row.dataset.protectedRequestCount = String(trial.protected_request_count);
    row.dataset.versionId = trial.artifact_version_id ?? '';
    row.dataset.runId = trial.run_id ?? '';
    row.dataset.state = trial.state;
    row.append(element('strong', `Pair ${trial.pair_ordinal} · candidate ${trial.candidate_label} · step ${trial.execution_ordinal} of 6 · ${humanize(trial.state)}`));
    row.append(element('p', `${trial.workload_id} · ${trial.request_count} public request${trial.request_count === 1 ? '' : 's'} + ${trial.protected_request_count} protected step · ${trial.artifact_version_id} · ${trial.artifact_content_hash ?? 'hash not loaded'} · run ${trial.run_id ?? 'not created'} · ${trial.evidence_mode ?? 'evidence mode pending'}`, 'evidence-meta'));
    if (trial.task_assessments.length) {
      const detail = element('details');
      detail.append(element('summary', `${trial.task_assessments.length} assessed task result${trial.task_assessments.length === 1 ? '' : 's'}`));
      for (const result of trial.task_assessments) {
        const item = element('div', null, 'result-row');
        item.dataset.taskId = result.task_id;
        item.dataset.requestOrdinal = String(result.request_ordinal);
        item.dataset.outcome = result.outcome;
        item.dataset.verdict = result.mandatory_pass ? 'pass' : 'fail';
        item.append(element('strong', `${result.task_id} · ${humanize(result.outcome)}${result.reason_codes.length ? ` · ${result.reason_codes.join(', ')}` : ''}`), element('small', `request ${result.request_ordinal} · ${result.mandatory_pass ? 'mandatory task passes' : 'mandatory task fails'}`));
        detail.append(item);
      }
      row.append(detail);
    }
    for (const output of trial.outputs) row.append(element('p', `Request ${output.request_ordinal}: ${output.request_text}`, 'evidence-text request-quote'));
    if (trial.missing_evidence.length) row.append(element('p', `Missing evidence: ${trial.missing_evidence.join('; ')}`, 'denial'));
    return row;
  }));
}
function hasUnsavedDraft() { return $('draft-source').dataset.dirty === 'true'; }
function setExpandedWork(value) {
  if (expandedWork === value) return;
  const editor = $('draft-source');
  const hadFocus = document.activeElement === editor;
  const range = hadFocus ? { start: editor.selectionStart, end: editor.selectionEnd, direction: editor.selectionDirection } : null;
  expandedWork = value;
  document.querySelector('main').dataset.expanded = String(value);
  $('expand-work').setAttribute('aria-expanded', String(value));
  $('expand-work').textContent = value ? 'Restore the room' : 'Expand the workbench';
  workplaceHost?.setExpanded(value);
  syncInspector();
  if (hadFocus) { editor.focus({ preventScroll: true }); editor.setSelectionRange(range.start, range.end, range.direction); }
}
function renderDraftEditor() {
  const shift = state.board?.latest_shift;
  const files = state.draft?.files;
  const file = $('draft-file'), source = $('draft-source');
  if (!shift || !files) {
    for (const id of ['draft-file', 'draft-source', 'save-draft', 'discard-draft-edit']) $(id).disabled = true;
    text('draft-note', 'No verified draft loaded. Unsaved text stays in this tab while you reconnect.');
    return;
  }
  const changedShift = source.dataset.shiftId !== shift.id;
  if (changedShift || !file.options.length) {
    file.replaceChildren(...[...new Set([...Object.keys(files), ...(northline() || gtm() ? [] : ['checks.json', 'change_log.md'])])].map(name => {
      const option = element('option', name); option.value = name; return option;
    }));
    if ('service.py' in files) file.value = 'service.py';
  }
  if (changedShift || source.dataset.file !== file.value || !hasUnsavedDraft()) {
    source.value = files[file.value] ?? '';
    source.dataset.shiftId = shift.id;
    source.dataset.file = file.value;
    source.dataset.dirty = 'false';
  }
  const editable = shift.state === 'open' && !state.pending;
  file.disabled = !editable || hasUnsavedDraft();
  source.disabled = !editable;
  $('save-draft').disabled = !editable || !hasUnsavedDraft();
  $('discard-draft-edit').disabled = !editable || !hasUnsavedDraft();
  renderWorkplace();
  text('draft-note', hasUnsavedDraft() ? 'Unsaved edit. Save or discard it before switching files, freezing candidates or changing shifts.'
    : file.value in files ? 'Saved draft from this shift. Saving does not select a version or change operational history.'
    : `${file.value} is not in this draft yet. Add content and save to create it.`);
}
async function saveDraft() {
  if (state.pending || !state.board?.latest_shift || !hasUnsavedDraft()) return;
  const shiftId = state.board.latest_shift.id;
  const files = { ...state.draft.files, [$('draft-file').value]: $('draft-source').value };
  state.pending = true; renderDraftEditor(); renderCompare(); renderNext();
  text('draft-error', '');
  try {
    state.draft = await api(`/shifts/${encodeURIComponent(shiftId)}/artifact`, { method: 'PUT', body: JSON.stringify({ files }) });
    $('draft-source').dataset.dirty = 'false';
    await refresh();
  } catch (error) { text('draft-error', error.message); }
  finally { state.pending = false; renderDraftEditor(); renderCompare(); renderNext(); }
}
function renderNext() {
  const board = state.board;
  const shift = board?.latest_shift ?? null;
  const choice = board?.operating_selection ?? null;
  const requirements = board?.inherited_requirements ?? null;
  const later = state.stationView?.latest_experiment?.kind === 'LATER_CONDITION_COMPARISON'
    ? state.stationView.latest_experiment : null;
  text('next-state', shift ? `${shift.id} · ${shift.state === 'open' ? 'open' : 'closed'} · ${humanize(board.operating_status)}` : 'No shift loaded');
  text('next-tag', !shift ? 'Not loaded' : choice ? `${choice.selected_version_id} · ${humanize(board.operating_status)}` : 'No selection yet');
  const inheritance = $('next-inheritance');
  inheritance.dataset.selectionId = choice?.id ?? '';
  inheritance.dataset.selectedVersion = choice?.selected_version_id ?? '';
  inheritance.dataset.selectedHash = choice?.selected_content_hash ?? '';
  inheritance.dataset.retainedAlternative = choice?.retained_alternative_version_id ?? '';
  inheritance.dataset.comparison = choice?.comparison_id ?? '';
  inheritance.dataset.observedRun = later?.observed_run_id ?? '';
  if (!shift || !choice) empty(inheritance, 'No inherited selection. Make an explicit choice in a comparison first.');
  else {
    inheritance.replaceChildren();
    for (const [label, field, value] of [
      ['Live version', 'operating-choice', `${choice.id} · ${choice.selected_version_id} · ${humanize(choice.state)}`],
      ['Recorded rationale', 'rationale', choice.rationale],
      ['Selected content hash', 'selected-hash', choice.selected_content_hash],
      ['Backup version', 'retained-alternative', choice.retained_alternative_version_id],
      ['Prior choice', 'prior-choice', choice.prior_selection_id ?? 'none'],
      ['Comparison', 'comparison', choice.comparison_id],
      ['Draft descends from', 'draft-base', board.draft_base_version_id ?? 'none'],
      ['Newest saved version', 'latest-saved', board.latest_saved_version_id ?? `none in this shift (newest in the engagement: ${board.latest_version?.id ?? 'none'})`],
    ]) {
      const row = element('div', null, 'contract-line');
      row.dataset.inheritField = field;
      row.append(element('span', label), element('strong', value));
      inheritance.append(row);
    }
  }
  const tests = $('next-tests');
  if (!requirements) empty(tests, 'No inherited requirement set. The visible checks load with an explicit choice.');
  else {
    tests.replaceChildren();
    for (const [label, field, value] of [
      ['Requirement set', 'requirement-set', requirements.requirement_set_id],
      ['Frozen requirement hash', 'requirement-hash', requirements.requirement_set_hash],
      ['Visible check set hash', 'visible-check-hash', requirements.visible_check_set_hash],
    ]) {
      const row = element('div', null, 'contract-line');
      row.dataset.inheritField = field;
      row.append(element('span', label), element('strong', value));
      tests.append(row);
    }
  }
  const history = $('next-history');
  if (!shift) empty(history, 'No verified data loaded.');
  else {
    history.dataset.ledgerEvents = String(board.ledger_event_count);
    history.dataset.incidents = String(board.incidents.length);
    history.dataset.chainStatus = board.chain_status;
    const laterRuns = new Set(later ? later.trials.map(trial => trial.run_id).filter(Boolean) : []);
    const run = ['OPERATION', 'LEGACY_OPERATION'].includes(board.latest_run?.purpose) && !laterRuns.has(board.latest_run.id) ? board.latest_run : null;
    history.dataset.latestRun = run?.id ?? '';
    history.replaceChildren();
    for (const [label, value] of [
      ['Latest recorded run', run ? `${run.id} · ${humanize(run.purpose)} · ${humanize(run.state)} · ${run.evidence_mode ?? 'evidence mode unknown'}` : 'No operational run loaded here. Inspect experiment results in their own panel.'],
      ['Unresolved incidents', board.incidents.map(incident => `${incident.id} · ${humanize(incident.state)}`).join(' · ') || 'none'],
      ['Declared limits in force', board.unresolved_limits.join(' · ') || 'none'],
      ['Ledger', `${board.ledger_event_count} recorded events · chain ${humanize(board.chain_status)}`],
      ['Ledger totals', Object.entries(board.ledger_totals).map(([name, count]) => `${humanize(name)} ${count}`).join(' · ') || 'no events'],
    ]) {
      const row = element('div', null, 'contract-line');
      row.append(element('span', label), element('strong', value));
      history.append(row);
    }
  }
  const experiment = $('next-experiment');
  if (!shift) empty(experiment, 'No verified data loaded.');
  else if (!later) {
    delete experiment.dataset.experimentId;
    delete experiment.dataset.observedRunId;
    delete experiment.dataset.selectedVersion;
    delete experiment.dataset.retainedAlternative;
    delete experiment.dataset.replacesSelection;
    experiment.dataset.experimentState = 'none';
    empty(experiment, 'No later-condition experiment on this shift. One becomes available after an operation records an observed condition change, such as a dependency outage, and it never replaces that operation.');
  } else {
    experiment.dataset.experimentId = later.id;
    experiment.dataset.experimentState = later.state;
    experiment.dataset.outcomeStatus = later.outcome?.status ?? 'INCOMPLETE';
    experiment.dataset.observedRunId = later.observed_run_id ?? '';
    experiment.dataset.selectedVersion = choice?.selected_version_id ?? '';
    experiment.dataset.retainedAlternative = choice?.retained_alternative_version_id ?? '';
    experiment.dataset.replacesSelection = 'false';
    experiment.replaceChildren();
    const versions = Object.fromEntries(later.candidates.map(candidate => [candidate.label, candidate.artifact_version_id]));
    for (const [label, value] of [
      ['Experiment', `${later.id} · ${humanize(later.state)}`],
      ['Observed operation', later.observed_run_id ?? 'none'],
      ['Observed condition', later.condition ? `${later.condition.public_label} (${later.condition.kind})` : 'not recorded'],
      ['Re-tested versions', `A ${versions.A ?? 'none'} (selected) · B ${versions.B ?? 'none'} (backup version)`],
      ['Outcome', later.outcome?.status ?? 'INCOMPLETE'],
      ['Slots', `${later.trials.filter(trial => trial.state === 'COMPLETE').length} of ${later.trials.length} complete`],
    ]) {
      const row = element('div', null, 'contract-line');
      row.append(element('span', label), element('strong', value));
      experiment.append(row);
    }
  }
  const open = shift?.state === 'open';
  const currentInspection = inspection.mode === 'current';
  $('close-shift').disabled = state.pending || !currentInspection || !shift || !open || hasUnsavedDraft();
  $('open-next-shift').disabled = state.pending || !currentInspection || !shift || open || hasUnsavedDraft();
  renderHandoverIncidents();
  text('next-help', !shift ? 'No shift loaded.'
    : !currentInspection ? 'Historical inspection. Return to the current shift before closing or opening one.'
    : open ? (choice ? `Closing writes the declared limits to the ledger and never selects a version. The next shift starts from ${choice.selected_version_id} and keeps ${choice.retained_alternative_version_id} in history.`
      : 'This shift has no explicit choice. Close it to open the next shift, but no version is inherited as operating.')
    : 'This shift is closed. Open the next shift to inherit the exact selection and continue the history.');
}
async function freezeCandidate(label) {
  const shiftId = state.board?.latest_shift?.id;
  const contract = state.board?.latest_version?.contract;
  if (!shiftId || !contract || state.pending) return;
  state.pending = true; renderBoard(); renderCompare();
  try {
    const version = await api(`/shifts/${encodeURIComponent(shiftId)}/artifact/versions`, { method: 'POST', body: JSON.stringify({ contract }) });
    state.candidates[label] = version;
    text('compare-error', '');
    await refresh();
  } catch (error) {
    await refresh();
    text('compare-error', error.message);
  } finally {
    state.pending = false;
    if (state.board) { renderBoard(); renderCompare(); renderInvestigate(); }
  }
}
function comparisonOwner() {
  return { slug: state.slug, shiftId: state.board?.latest_shift?.id ?? null,
    generation: state.generation, intent: state.intent, inspection: { ...inspection } };
}
function comparisonPublicationAllowed(owner, experiment) {
  return owner.slug === state.slug &&
    owner.shiftId === state.loadedShiftId &&
    owner.shiftId === experiment?.shift_id &&
    owner.generation === state.generation &&
    owner.intent === state.intent &&
    owner.inspection.mode === inspection.mode &&
    owner.inspection.historicalRunId === inspection.historicalRunId &&
    document.body.dataset.loadState !== 'loading';
}
function acceptComparison(owner, experiment) {
  if (!comparisonPublicationAllowed(owner, experiment)) return;
  state.comparison = experiment;
  renderCompare();
  publishPresentation('comparison');
}
async function runComparison() {
  const shiftId = state.board?.latest_shift?.id;
  const [a, b] = [state.candidates.A, state.candidates.B];
  if (!shiftId || !a || !b || state.pending) return;
  const owner = comparisonOwner();
  state.pending = true; renderBoard(); renderCompare();
  try {
    let experiment = await api(`/shifts/${encodeURIComponent(shiftId)}/experiments`, { method: 'POST', body: JSON.stringify({
      kind: 'QUALIFYING_COMPARISON',
      investigation_id: state.stationView?.latest_investigation_id ?? null,
      candidate_a_version_id: a.id,
      candidate_b_version_id: b.id,
      declared_treatment: $('treatment-input').value,
      client_request_id: requestId('comparison'),
    }) });
    acceptComparison(owner, experiment);
    const deadline = Date.now() + 180000;
    while (!['FINALIZED', 'FAILED', 'INVALIDATED'].includes(experiment.state) && Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 500));
      experiment = await api(`/experiments/${encodeURIComponent(experiment.id)}`);
      acceptComparison(owner, experiment);
    }
    await refresh();
  } catch (error) {
    await refresh();
    text('compare-error', error.message);
  } finally {
    state.pending = false;
    if (state.board) { renderBoard(); renderCompare(); }
  }
}
async function chooseCandidate(label) {
  const shiftId = state.board?.latest_shift?.id;
  const candidate = state.comparison?.candidates.find(item => item.label === label);
  if (!shiftId || !candidate || state.pending) return;
  state.pending = true; renderCompare();
  try {
    await api(`/shifts/${encodeURIComponent(shiftId)}/selections`, { method: 'POST', body: JSON.stringify({
      comparison_id: state.comparison.id,
      selected_version_id: candidate.artifact_version_id,
      rationale: $('selection-rationale').value,
      expected_prior_selection_id: state.board.operating_selection?.id ?? null,
      client_request_id: requestId('selection'),
    }) });
    text('selection-error', '');
    await refresh();
  } catch (error) {
    await refresh();
    text('selection-error', error.message);
  } finally {
    state.pending = false;
    if (state.board) { renderBoard(); renderCompare(); }
  }
}
async function appendInvestigation() {
  const shiftId = state.board?.latest_shift?.id;
  const ordinal = Number($('source-ordinal').value);
  if (!shiftId || !state.run || !ordinal || state.pending) return;
  state.pending = true; renderBoard(); renderInvestigate();
  try {
    await api(`/shifts/${encodeURIComponent(shiftId)}/investigations`, { method: 'POST', body: JSON.stringify({
      source_run_id: repeatedDiagnosticTrial()?.run_id ?? state.run.id,
      source_request_ordinal: ordinal,
      cause: $('cause-input').value,
      falsifier: $('falsifier-input').value,
      public_test: $('public-test-input').value,
      revision_of_id: state.stationView?.latest_investigation_id ?? null,
      client_request_id: requestId('investigation'),
    }) });
    for (const id of ['cause-input', 'falsifier-input', 'public-test-input']) $(id).value = '';
    await refresh();
  } catch (error) {
    await refresh();
    text('investigate-error', error.message);
  } finally {
    state.pending = false;
    if (state.board) { renderBoard(); renderInvestigate(); renderCompare(); }
  }
}
async function requestAssist() {
  const shiftId = state.board?.latest_shift?.id;
  if (!shiftId || state.pending) return;
  state.pending = true; renderBoard(); renderInvestigate();
  try {
    const event = await api(`/shifts/${encodeURIComponent(shiftId)}/assist`, { method: 'POST', body: JSON.stringify({ investigation_id: state.stationView?.latest_investigation_id ?? null, role: $('assist-role').value, message: $('assist-message').value, client_request_id: requestId('assist') }) });
    await refresh();
    text('assist-denial', event.state === 'FAILED' ? `Help failed: ${event.failure_code}. This call used budget.` : 'Help recorded below. Check it against your evidence.');
  } catch (error) {
    text('assist-denial', error.message);
  } finally {
    state.pending = false;
    if (state.board) { renderBoard(); renderInvestigate(); renderCompare(); }
  }
}
async function decideAssist(eventId, accepted) {
  if (state.pending) return;
  state.pending = true; renderInvestigate();
  try {
    await api(`/assist-events/${encodeURIComponent(eventId)}/decision`, { method: 'POST', body: JSON.stringify({ accepted }) });
    await refresh();
  } catch (error) {
    text('assist-denial', error.message);
  } finally {
    state.pending = false;
    if (state.board) { renderInvestigate(); renderCompare(); }
  }
}
function diagnosticOwner() {
  return { slug: state.slug, shiftId: state.board?.latest_shift?.id ?? null,
    generation: state.generation, intent: state.intent, inspection: { ...inspection } };
}
function diagnosticPublicationAllowed(owner) {
  return owner.generation === state.generation && owner.intent === state.intent &&
    owner.inspection.mode === inspection.mode &&
    owner.inspection.historicalRunId === inspection.historicalRunId;
}
function acceptDiagnostic(owner, experiment) {
  if (owner.slug !== state.slug || owner.shiftId !== state.loadedShiftId ||
      owner.shiftId !== experiment?.shift_id) return;
  state.diagnostic = experiment;
  renderInvestigate();
  if (diagnosticPublicationAllowed(owner)) publishPresentation('diagnostic');
}
async function runDiagnostic() {
  const shiftId = state.board?.latest_shift?.id;
  const versionId = state.board?.latest_saved_version_id;
  if (!shiftId || !versionId || state.pending) return;
  const owner = diagnosticOwner();
  state.pending = true; renderBoard(); renderInvestigate();
  try {
    let experiment = await api(`/shifts/${encodeURIComponent(shiftId)}/experiments`, { method: 'POST', body: JSON.stringify({
      kind: 'DIAGNOSTIC',
      investigation_id: state.stationView?.latest_investigation_id ?? null,
      candidate_a_version_id: versionId,
      client_request_id: requestId('diagnostic'),
      public_repetitions: Number($('diagnostic-repetitions').value),
    }) });
    acceptDiagnostic(owner, experiment);
    const deadline = Date.now() + 600000;
    while (!['FINALIZED', 'FAILED'].includes(experiment.state) && Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 400));
      experiment = await api(`/experiments/${encodeURIComponent(experiment.id)}`);
      acceptDiagnostic(owner, experiment);
    }
    await refresh();
  } catch (error) {
    await refresh();
    text('investigate-error', error.message);
  } finally {
    state.pending = false;
    if (state.board) { renderBoard(); renderInvestigate(); renderCompare(); }
  }
}

const stations = {
  brief: ['Deployment brief', 'NORTHLINE / CUSTOMER REQUIREMENTS', 'The blank starter is labelled. Saving and comparing never select your operating version.'],
  map: ['System map', 'DISCOVERY AND PERMISSIONS', 'Inspect your integration worksheets and the exact selected version. Availability reads and repair-slot writes are the permitted boundary.'],
  bench: ['Integration bench', 'INVESTIGATE, REPAIR, COMPARE AND CHOOSE', 'State a cause and what would prove you wrong before help. One hint per shift. Compare two exact versions; no winner is chosen automatically.'],
  acceptance: ['Acceptance', 'INDEPENDENT TASK RESULTS', 'Inspect the actual request, captured reply, independent checks and their recorded consequences.'],
  rollout: ['Rollout', 'PILOT OPERATIONS', 'Synthetic pilot state. Only a fully accepted operation records rollout approval. Experiments write no pilot state.'],
  handover: ['Handover', 'WHAT THE CO-OP INHERITS', 'Close records the selected runbook, declared limits and unresolved incidents. Newer saves cannot replace this handover.'],
  signals: ['Signal intake', 'FOLLOW ONE EXECUTED SIGNAL', 'Select a captured signal. The request, the exact output, the independent checks and the recorded consequence below all belong to that one request.'],
  rules: ['Qualification rules', 'STONEBRIDGE / VISIBLE CONTRACT', 'The mandatory ownership rules are fixed and the selections are yours. This workflow prepares work for a person; it never sends a customer message.'],
  workflow: ['Workflow bench', 'INVESTIGATE, COMPARE AND CHOOSE', 'State a cause and what would prove you wrong before help. Two help calls per shift and no patch proposals. Compare two exact workflows; no winner is chosen automatically.'],
  wall: ['Pipeline wall', 'SYNTHETIC PIPELINE STATE', 'Owners, SLA clocks, escalations and missed-handoff incidents, derived only from operational captures. An experiment never moves an owner or starts a clock.'],
  service: ['Service workbench', 'YOUR WORKING ARTIFACT', 'Your version, contract and files belong to you. Independent scoring stays separate.'],
  owner: ['Requirements', 'OWNER DESK', 'Inspect the operating version\'s committed requirements and frozen requirement hash. Saved candidates keep their own contracts.'],
  customers: ['Customer evidence', 'FOLLOW AN EXECUTED REQUEST', 'Select a customer. Every output, public record, check and event below belongs to that request.'],
  pipeline: ['Evidence trail', 'OUTPUT → CHECK → LEDGER', 'This path traces recorded evidence, not a prediction of success.'],
  ledger: ['Incident & ledger wall', 'RECORDED CONSEQUENCES', 'Synthetic scenario. Select an incident to inspect the output and result that opened it.'],
  repair: ['Repair review', 'REPAIR BENCH · READ ONLY', 'Inspect an actual incident below. Repair authoring and rerunning a new version are not available in this build.'],
  evaluator: ['Independent evaluator', 'LOCKED · NOT EDITABLE', 'Neither the learner nor an assistant can edit the scoring rules or see sealed expected values.'],
  investigate: ['Investigate a failure', 'REVIEW THE EXECUTED REQUEST', 'Read the exact request and output, then write your cause, what would prove you wrong and a public test. A diagnostic cannot qualify a version.'],
  compare: ['Compare and choose', 'PAIRED CANDIDATE EXECUTION', 'Both candidates run the same frozen workloads under shared requirements and ceilings. Experiments leave operational history unchanged. Choose an eligible exact version and record your rationale.'],
  next: ['Next shift', 'INHERITED EXACTLY, TESTED LATER', 'Close this shift and open the next one from the exact selection. Recorded operational history and a later-condition experiment are shown as two separate things: the experiment is hypothetical and never rewrites the history.'],
};
function bringStationPanelIntoReach() {
  // Northline's evidence can sit below a tall header at native 200% zoom.
  // Skipped before the first load paints, so a page open still starts at the room.
  if (!state.board) return;
  if (!narrowLayout()) return;
  const panel = $('station-panel');
  panel.focus({ preventScroll: true });
  const content = northline() ? {
    acceptance: document.querySelector('#selected-evidence .request-quote') ?? $('selected-evidence'),
    rollout: $('operate-pilot'),
    handover: $('handover-records'),
  }[state.station] : null;
  (content ?? panel).scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
}
function activateStation(name, userIntent = true) {
  if (userIntent) state.intent += 1;
  // Choosing a station keeps the current shift, so the picker steps aside.
  if (userIntent) $('shift-picker').hidden = true;
  if (name === 'repair' && !state.board?.incidents.length) {
    text('station-context', 'No unresolved incident is loaded. The repair bench becomes available for an actual incident.');
    return;
  }
  if (northline()) name = ({ service: 'brief', owner: 'brief', customers: 'acceptance', pipeline: 'acceptance', ledger: 'rollout', repair: 'bench', investigate: 'bench', compare: 'bench', next: 'handover' })[name] ?? name;
  if (gtm()) name = ({ service: 'signals', owner: 'rules', brief: 'rules', map: 'rules', customers: 'signals', pipeline: 'signals', acceptance: 'signals', ledger: 'wall', repair: 'workflow', investigate: 'workflow', compare: 'workflow', bench: 'workflow', next: 'wall', rollout: 'wall', handover: 'wall' })[name] ?? name;
  state.station = name;
  document.querySelectorAll('[data-station]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.station === name)));
  const [title, kicker, context] = stations[name] ?? stations.service;
  text('panel-title', title); text('panel-kicker', kicker); text('station-context', context);
  $('deferred-view').hidden = name !== 'evaluator';
  $('customer-view').hidden = !['customers', 'pipeline', 'acceptance', 'signals', 'evaluator'].includes(name);
  $('investigate-view').hidden = !['investigate', 'bench', 'workflow'].includes(name);
  $('compare-view').hidden = !['compare', 'bench', 'workflow'].includes(name);
  $('next-view').hidden = !['next', 'handover', 'wall'].includes(name);
  $('board-view').hidden = !['service', 'owner', 'ledger', 'brief', 'rules', 'signals'].includes(name);
  $('repair-view').hidden = name !== 'repair';
  $('northline-brief').hidden = name !== 'brief';
  $('gtm-rules').hidden = name !== 'rules';
  $('map-view').hidden = name !== 'map';
  $('rollout-view').hidden = name !== 'rollout';
  $('pipeline-view').hidden = name !== 'wall';
  $('handover-record').hidden = !northline();
  if (name === 'evaluator') {
    text('deferred-title', 'Separate by design.');
    text('deferred-copy', 'The controller scores captured service outputs against independent checks. You can inspect recorded results at the customer queue, but this booth has no editing controls and never displays sealed expected values.');
  }
  if (name === 'owner' || name === 'rules') { state.file = 'contract'; selectFile('contract'); }
  if (state.board) text('service-tag', state.board.operating_selection
    ? `${state.board.operating_selection.selected_version_id} · ${humanize(state.board.operating_status)}`
    : state.board.latest_version ? `${state.board.latest_version.id} · candidate only` : 'Draft · not frozen');
  renderCustomers();
  renderInvestigate();
  renderCompare();
  renderNext();
  renderRepairTray();
  renderOwnerRecord();
  renderInspectionBar();
  if (userIntent && name === 'owner') $('owner-record').scrollIntoView({ block: 'start' });
  if (userIntent && name === 'repair') $('repair-view').scrollIntoView({ block: 'start' });
  const view = northline() || gtm() ? name : { owner: 'contract', investigate: 'investigate', compare: 'compare', next: 'next' }[name] ?? 'board';
  state.view = view;
  if (userIntent) history.replaceState(null, '', `#${view}`);
  document.querySelectorAll('[data-view]').forEach(link => {
    if (link.dataset.view === view) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
  });
  if (userIntent) { openInspector(); bringStationPanelIntoReach(); openStationId = name; workplaceHost?.setOpenStation(name); }
  publishPresentation('station');
}
function selectFile(name) {
  state.file = name;
  document.querySelectorAll('[data-file]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.file === name)));
  renderArtifact();
}
function navigate(view, userIntent = true) {
  if (view === 'station-panel') return;
  if (northline()) { activateStation({ board: 'brief', contract: 'brief', investigate: 'bench', compare: 'bench', next: 'handover' }[view] ?? (['brief', 'map', 'bench', 'acceptance', 'rollout', 'handover'].includes(view) ? view : 'brief'), userIntent); return; }
  if (gtm()) { activateStation({ board: 'signals', contract: 'rules', investigate: 'workflow', compare: 'workflow', next: 'wall', return: 'wall', customers: 'signals', repair: 'workflow' }[view] ?? (['signals', 'rules', 'workflow', 'wall'].includes(view) ? view : 'signals'), userIntent); return; }
  activateStation({ board: 'service', contract: 'owner', investigate: 'investigate', compare: 'compare', next: 'next', return: 'next', customers: 'customers', repair: 'repair' }[view] ?? 'service', userIntent);
  if (userIntent && state.board) $('station-panel').focus({ preventScroll: true });
}
async function act(action, operation = false) {
  if (state.pending) return;
  if (inspection.mode !== 'current') { text('load-message', 'Return to the current shift before acting.'); return; }
  state.pending = true; renderBoard();
  try { await action(); inspection = { mode: 'current', historicalRunId: null }; publishPresentation(operation ? 'operation' : 'history'); await refresh(); }
  catch (error) { await refresh(); text('load-message', error.message); }
  finally { state.pending = false; if (state.board) { renderBoard(); renderCompare(); } }
}
$('open-shift').addEventListener('click', () => act(() => api(engagementPath('shifts'), { method: 'POST' })));
$('run-shift').addEventListener('click', () => {
  const shiftId = state.board?.latest_shift?.id;
  if (!shiftId) return;
  activateStation('customers');
  act(() => api(`/shifts/${encodeURIComponent(shiftId)}/runs`, { method: 'POST',
    body: JSON.stringify({ client_request_id: requestId('operation') }) }), true);
});
$('refresh').addEventListener('click', () => { inspection = { mode: 'current', historicalRunId: null }; publishPresentation('history'); refresh(); });
$('append-investigation').addEventListener('click', appendInvestigation);
$('request-assist').addEventListener('click', requestAssist);
$('run-diagnostic').addEventListener('click', runDiagnostic);
$('save-draft').addEventListener('click', saveDraft);
$('draft-file').addEventListener('change', renderDraftEditor);
$('draft-source').addEventListener('input', () => {
  $('draft-source').dataset.dirty = String($('draft-source').value !== state.draft?.files[$('draft-file').value]);
  renderCompare(); renderNext();
});
$('discard-draft-edit').addEventListener('click', () => {
  $('draft-source').dataset.dirty = 'false';
  text('draft-error', '');
  renderCompare(); renderNext();
});
$('freeze-candidate-a').addEventListener('click', () => freezeCandidate('A'));
$('freeze-candidate-b').addEventListener('click', () => freezeCandidate('B'));
$('run-comparison').addEventListener('click', runComparison);
$('open-choose-a').addEventListener('click', () => openChoose('A'));
$('open-choose-b').addEventListener('click', () => openChoose('B'));
$('cancel-choose').addEventListener('click', () => $('choose-dialog').close());
$('choose-dialog').addEventListener('cancel', event => { event.preventDefault(); $('choose-dialog').close(); });
$('choose-dialog').addEventListener('close', () => {
  if ($('choose-dialog').open) return;
  $('selection-rationale').value = '';
  for (const key of ['a', 'b']) $(`select-candidate-${key}`).hidden = true;
  if (state.board) renderCompare();
  (chooseOpener?.isConnected && !chooseOpener.disabled ? chooseOpener : $('selection-note')).focus({ preventScroll: true });
});
$('open-shift-report').addEventListener('click', event => {
  event.preventDefault(); event.stopPropagation();
  showShiftReport(latestPresentation?.kind === 'accepted' ? latestPresentation.view : null);
});
$('close-shift-report').addEventListener('click', () => $('shift-report').close());
$('shift-report').addEventListener('cancel', event => { event.preventDefault(); $('shift-report').close(); });
$('shift-report').addEventListener('close', () => (reportOpener?.isConnected ? reportOpener : $('open-shift-report')).focus({ preventScroll: true }));
for (const id of ['choose-dialog', 'shift-report']) {
  const dialog = $(id);
  dialog.addEventListener('keydown', event => {
    if (event.key === 'Escape') event.stopPropagation();
    if (event.key !== 'Tab' || !dialog.open) return;
    const controls = [...dialog.querySelectorAll('button, textarea')].filter(node => !node.disabled && !node.hidden);
    const first = controls[0], last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
}
$('treatment-input').addEventListener('input', () => renderCompare());
async function shiftAction(path) {
  if (state.pending || !path) return;
  if (inspection.mode !== 'current') { text('next-error', 'Return to the current shift before closing or opening one.'); return; }
  state.pending = true; renderBoard(); renderNext();
  text('next-error', '');
  try { await api(path, { method: 'POST' }); await refresh(); }
  catch (error) { await refresh(); text('next-error', error.message); }
  finally { state.pending = false; if (state.board) { renderBoard(); renderNext(); renderCompare(); } }
}
$('inspect-current').addEventListener('click', returnToCurrent);
$('close-shift').addEventListener('click', () => shiftAction(state.board?.latest_shift ? `/shifts/${encodeURIComponent(state.board.latest_shift.id)}/close` : null));
$('open-next-shift').addEventListener('click', () => shiftAction(engagementPath('shifts')));
$('select-candidate-a').addEventListener('click', () => chooseCandidate('A'));
$('select-candidate-b').addEventListener('click', () => chooseCandidate('B'));
$('selection-rationale').addEventListener('input', () => renderCompare());
// The next action only opens the guide's station; it sends no request.
$('next-action-go').addEventListener('click', () => activateStation(storyGuide?.stationId ?? state.station));
// A cause draft moves the chip between steps 2 and 3 only; nothing is sent or credited.
for (const id of ['cause-input', 'falsifier-input']) $(id).addEventListener('input', () => renderGuide());
$('back-board').addEventListener('click', () => { location.hash = 'board'; navigate('board'); });
document.querySelectorAll('[data-station]').forEach(button => button.addEventListener('click', () => activateStation(button.dataset.station)));
document.querySelectorAll('[data-view]').forEach(link => link.addEventListener('click', event => {
  event.preventDefault();
  navigate(link.dataset.view);
}));
document.querySelectorAll('[data-file]').forEach(button => button.addEventListener('click', () => selectFile(button.dataset.file)));
window.addEventListener('hashchange', () => navigate(location.hash.slice(1)));
window.addEventListener('beforeunload', event => {
  if (!hasUnsavedDraft()) return;
  event.preventDefault();
  event.returnValue = '';
});
window.addEventListener('pagehide', () => { clearTimeout(pollTimer); clearTimeout(hostTimer); hostTimer = null; if (downloadUrl) URL.revokeObjectURL(downloadUrl); hostEpoch += 1; hostLoading = false; workplaceHost?.dispose(); workplaceHost = null; publishPresentation('page-lifecycle'); });
window.addEventListener('pageshow', async event => {
  if (!event.persisted) return;
  const editor = $('draft-source');
  const focus = document.activeElement === editor
    ? { start: editor.selectionStart, end: editor.selectionEnd, direction: editor.selectionDirection, intent: state.intent } : null;
  initializeGraphics();
  const refreshed = refresh(), generation = state.generation;
  await refreshed;
  // Loading temporarily disables the editor and drops native page-cache focus.
  if (focus && generation === state.generation && focus.intent === state.intent && !editor.disabled &&
      editor === $('draft-source') && [document.body, editor].includes(document.activeElement)) {
    editor.focus({ preventScroll: true });
    editor.setSelectionRange(focus.start, focus.end, focus.direction);
  }
});
$('operate-pilot').addEventListener('click', () => $('run-shift').click());
$('operate-pipeline').addEventListener('click', () => $('run-shift').click());
$('expand-work').addEventListener('pointerdown', event => {
  if (document.activeElement === $('draft-source')) event.preventDefault();
});
$('expand-work').addEventListener('click', () => setExpandedWork(!expandedWork));
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || !expandedWork) return;
  if (event.target !== $('expand-work') && event.target !== $('station-panel')) return;
  event.preventDefault();
  setExpandedWork(false);
  $('expand-work').focus({ preventScroll: true });
});
$('workplace-board').addEventListener('change', switchWorkplace);
// The shift picker shows authored copy only. "Start shift" goes through the same
// switchWorkplace() guard as the board selector, so a dirty draft still blocks it.
function showPicker(open) {
  $('shift-picker').hidden = !open;
  if (open) { text('shift-picker-message', ''); $('shift-picker').querySelector('button').focus({ preventScroll: true }); }
  else $('change-shift').focus({ preventScroll: true });
}
async function startShift(slug) {
  const generation = state.generation;
  $('workplace-board').value = slug;
  await switchWorkplace();
  // The guard returns before the generation moves, so an unchanged generation means it blocked the switch.
  if (state.generation !== generation) return showPicker(false);
  text('shift-picker-message', state.workplaces.some(board => board.engagement_slug === slug && board.availability === 'AVAILABLE')
    ? $('workplace-message').textContent : 'This shift is not available in this preview.');
}
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || $('shift-picker').hidden) return;
  event.preventDefault();
  showPicker(false);
});
$('shift-picker-steps').replaceChildren(...STEP_NAMES.map(name => element('li', name)));
$('shift-picker-cards').replaceChildren(...SHIFT_CARDS.map(card => {
  const item = element('article', null, 'shift-card');
  item.dataset.slug = card.slug;
  const start = element('button', 'Start shift', 'button primary');
  start.type = 'button'; start.setAttribute('aria-label', `Start shift: ${card.client}`);
  start.addEventListener('click', () => startShift(card.slug));
  item.append(element('p', card.badge, 'shift-card-badge'), element('h3', card.client), element('p', card.role, 'shift-card-role'),
    element('p', card.question, 'shift-card-question'), element('p', `What it teaches: ${card.teaches}`, 'shift-card-teaches'), start);
  return item;
}));
$('change-shift').addEventListener('click', () => showPicker(true));
$('close-picker').addEventListener('click', () => showPicker(false));
const requestedSlug = new URL(location.href).searchParams.get('board');
if (requestedSlug) state.slug = requestedSlug;
const deepLink = location.hash.slice(1);
navigate(deepLink || 'board');
if (!deepLink || deepLink === 'board') closeInspector(false);
// A first-time visitor (no board parameter and no station link) starts at the picker.
// It opens after the start-up navigation, which would otherwise close it.
if (!requestedSlug && !deepLink) showPicker(true);
$('close-inspector').addEventListener('click', () => closeInspector());
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || !inspectorOpen || expandedWork || event.defaultPrevented) return;
  if (event.target.closest?.('textarea, input, select, [contenteditable="true"]')) return;
  event.preventDefault();
  closeInspector();
});
document.querySelectorAll('[data-log-filter]').forEach(button => button.addEventListener('click', () => {
  logFilter = button.dataset.logFilter;
  document.querySelectorAll('[data-log-filter]').forEach(other => other.setAttribute('aria-pressed', String(other === button)));
  renderShiftLog(storyEntries);
}));
window.addEventListener('resize', syncInspector);
$('shift-log').addEventListener('toggle', () => placeStationTags());
$('shift-details').addEventListener('toggle', () => placeStationTags());
refresh();
document.querySelector('[data-graphics-retry]').addEventListener('click', () => { if (!workplaceHost && !hostLoading) initializeGraphics(); });
initializeGraphics();
