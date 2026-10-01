import { bodyBytes, selectEvidence } from './evidence.js';

const $ = id => document.getElementById(id);
const state = { board: null, draft: null, stationView: null, run: null, outputs: [], checks: [], events: [], selected: null, station: 'service', view: 'board', file: 'contract', generation: 0, intent: 0, pending: false, diagnostic: null, comparison: null, candidates: { A: null, B: null } };
let downloadUrl = null;
let pollTimer = null;
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
function clearEvidence() {
  if (downloadUrl) URL.revokeObjectURL(downloadUrl);
  downloadUrl = null;
  delete document.body.dataset.evidence;
  $('selected-evidence').removeAttribute('data-run-id');
  $('selected-evidence').removeAttribute('data-request-ordinal');
  empty($('selected-evidence'), 'No executed customer request selected.');
}
function clearData(message) {
  state.board = null; state.draft = null; state.stationView = null; state.run = null;
  state.outputs = []; state.checks = []; state.events = []; state.selected = null; state.diagnostic = null;
  clearEvidence();
  text('load-message', message);
  text('session-state', 'Not connected');
  text('shift-number', 'No shift loaded');
  text('version-state', 'No verified version loaded');
  text('version-hash', '');
  empty($('selection-summary'), 'No operating choice loaded.');
  text('run-state', 'No run loaded');
  text('evidence-attempts', 'Attempts not loaded.');
  document.querySelector('[data-station="repair"]').setAttribute('aria-disabled', 'true');
  for (const id of ['metric-requests', 'metric-incidents', 'metric-attempts']) text(id, '…');
  for (const id of ['metric-chain', 'service-tag', 'queue-tag', 'repair-tag', 'attempt-detail', 'event-detail', 'investigation-tag', 'compare-tag']) text(id, 'Not loaded');
  text('incident-tag', 'Not loaded · Synthetic scenario');
  for (const id of ['artifact-detail', 'incident-list', 'limit-list', 'ledger-totals', 'customer-list']) empty($(id), 'No verified data loaded.');
  empty($('orientation-list'), 'Orientation loads with your shift.');
  empty($('investigation-list'), 'No verified entries loaded.');
  empty($('diagnostic-result'), 'No verified diagnostic loaded.');
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
  for (const id of ['next-inheritance', 'next-tests', 'next-history', 'next-experiment']) empty($(id), 'No verified data loaded.');
  $('close-shift').disabled = true; $('open-next-shift').disabled = true;
  text('selection-note', 'A complete eligible comparison is required.');
  text('selection-error', '');
  empty($('candidate-list'), 'No candidates loaded.');
  empty($('comparison-slots'), 'No comparison loaded.');
  $('source-ordinal').replaceChildren();
  $('source-ordinal').disabled = true;
  for (const id of ['append-investigation', 'request-assist', 'run-diagnostic', 'freeze-candidate-a', 'freeze-candidate-b', 'run-comparison', 'select-candidate-a', 'select-candidate-b']) $(id).disabled = true;
  $('open-shift').disabled = true; $('run-shift').disabled = true;
  text('run-help', 'Refresh to load available actions.');
}

async function refresh(runId = null) {
  const generation = ++state.generation;
  const selected = state.selected;
  clearTimeout(pollTimer);
  document.body.dataset.loadState = 'loading';
  clearData('Loading your shift…');
  try {
    const board = await api('/engagements/bookshop/board');
    const run = runId ? await api(`/runs/${encodeURIComponent(runId)}`) : board.latest_run;
    const [draft, stationView, ledger, outputs, checks] = await Promise.all([
      board.latest_shift ? api(`/shifts/${encodeURIComponent(board.latest_shift.id)}/artifact`) : null,
      board.latest_shift ? api(`/shifts/${encodeURIComponent(board.latest_shift.id)}/investigations`) : null,
      api('/engagements/bookshop/ledger'),
      run ? api(`/runs/${encodeURIComponent(run.id)}/outputs`) : [],
      run ? api(`/runs/${encodeURIComponent(run.id)}/checks`) : [],
    ]);
    if (generation !== state.generation) return;
    Object.assign(state, { board, draft, stationView, run, outputs, checks, events: ledger.events });
    if (stationView?.latest_experiment?.kind === 'QUALIFYING_COMPARISON') state.comparison = stationView.latest_experiment;
    else if (state.comparison) {
      try { state.comparison = await api(`/experiments/${encodeURIComponent(state.comparison.id)}`); }
      catch { state.comparison = null; }
    }
    state.selected = outputs.some(output => output.id === selected) ? selected : outputs[0]?.id ?? null;
    document.body.dataset.loadState = board.latest_shift ? 'ready' : 'empty';
    text('load-message', board.latest_shift ? '' : 'No shift yet. Open one to begin your service history.');
    renderBoard();
    if (['return', 'away'].includes(state.view)) navigate(state.view, false);
    else activateStation(state.station, false);
    if (!terminal(run)) pollTimer = setTimeout(() => refresh(run.id), 1000);
    return true;
  } catch (error) {
    if (generation !== state.generation) return;
    clearData(error.message);
    document.body.dataset.loadState = 'error';
  }
}

function renderBoard() {
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
  for (const [label, value] of [
    ['Latest saved', board.latest_saved_version_id ?? 'none'],
    ['Operating choice', choice ? `${choice.selected_version_id} · ${choice.selected_content_hash} · ${humanize(choice.state)}` : 'none'],
    ['Retained alternative', choice?.retained_alternative_version_id ?? 'none'],
    ['Comparison', choice?.comparison_id ?? 'none'],
    ['Original requirement hash', choice?.requirement_set_hash ?? 'none'],
  ]) {
    const row = element('div', null, 'contract-line');
    row.dataset.selectionField = label.toLowerCase().replaceAll(' ', '-');
    row.append(element('span', label), element('strong', value));
    summary.append(row);
  }
  const adapter = state.run?.adapter;
  const liveDiagnostic = state.stationView?.latest_experiment?.trials?.some(trial => trial.evidence_mode === 'ISOLATED_LIVE');
  text('execution-note', liveDiagnostic
    ? 'A real isolated diagnostic ran this saved service. Its result is evidence only; no version was selected or operated. The simulated role is not a credential.'
    : state.run?.purpose === 'LEGACY_OPERATION'
    ? `Legacy operation · ${state.run.evidence_mode ?? 'evidence mode unknown'}. Missing historical inputs remain unknown; old captures are not a fresh test. No live model or sandbox is established.`
    : adapter === 'local_process'
    ? 'Offline trusted-fixture execution. Not hostile-code isolation. No live model or sandbox. The simulated role is not a credential.'
    : adapter === 'recorded' ? 'Recorded replay: captured bytes, not execution of your current artifact. No live model or sandbox. The simulated role is not a credential.'
    : 'Offline client. No live model or sandbox connection. The simulated role is not a credential.');
  const incidents = $('incident-list');
  if (!board.incidents.length) empty(incidents, 'No unresolved incidents. The room reflects the recorded state.');
  else incidents.replaceChildren(...board.incidents.map(incident => {
    const button = element('button', null, 'incident-row');
    button.append(element('strong', `${incident.id} · ${humanize(incident.state)}`), element('span', incident.reason_code));
    button.addEventListener('click', async () => {
      const intent = ++state.intent;
      const accepted = await refresh(incident.opening_run_id);
      if (!accepted || intent !== state.intent || state.run?.id !== incident.opening_run_id) return;
      state.selected = state.outputs.find(output => output.id === incident.failing_output_ref)?.id ?? null;
      activateStation('customers');
      const target = [...document.querySelectorAll('.customer-button')].find(node => node.dataset.outputId === state.selected);
      if (target) target.focus(); else $('station-panel').focus();
    });
    return button;
  }));
  const limits = [...new Set([...(version?.contract.declared_limits ?? []), ...board.unresolved_limits])];
  if (!limits.length) empty($('limit-list'), 'No limits declared.');
  else {
    const list = element('ul');
    list.append(...limits.map(limit => element('li', limit, 'limit-item')));
    $('limit-list').replaceChildren(list);
  }
  const totals = Object.entries(board.ledger_totals);
  if (!totals.length) empty($('ledger-totals'), 'No ledger events yet.');
  else $('ledger-totals').replaceChildren(...totals.map(([name, count]) => {
    const row = element('div', null, 'total-row');
    row.append(element('span', humanize(name)), element('strong', count));
    return row;
  }));
  $('open-shift').disabled = state.pending || shift?.state === 'open';
  $('run-shift').disabled = state.pending || !version || !shift?.operation_allowed || shift?.state !== 'open' || board.attempts_remaining === 0 || !terminal(board.latest_run) ||
    (board.latest_run?.purpose === 'OPERATION' && board.latest_run?.state === 'FINALIZED' && board.latest_run?.shift_id === shift.id);
  text('run-help', needsChoice ? 'Operation is blocked. Compare qualifying repairs and explicitly choose an eligible tested version; saving or freezing a draft does not choose it.'
    : !version ? 'No frozen version is available to operate.'
    : !terminal(board.latest_run) ? 'Your run is in progress. Results appear only after the controller records them.'
    : shift?.state !== 'open' ? 'This shift is closed. Its recorded evidence stays available.'
    : board.attempts_remaining === 0 ? 'Attempt budget exhausted. The controller will not accept another run.'
    : 'Runs the selected version. A started attempt consumes one reservation, even if it fails.');
  renderArtifact();
}

function renderArtifact() {
  const target = $('artifact-detail');
  if (!state.board) return empty(target, 'No verified artifact loaded.');
  const files = state.draft?.files ?? {};
  target.replaceChildren();
  if (state.file === 'contract') {
    const contract = state.board.latest_version?.contract;
    if (!contract) return empty(target, 'No committed contract. Authoring is not available in this build; no stance is preselected.');
    for (const [label, value] of [
      ['Committed constraint', contract.must_never.map(humanize).join(', ')],
      [state.board.operating_selection?.selected_version_id === state.board.latest_version?.id ? 'Operating stance' : 'Latest saved stance', Object.values(contract.selections).map(humanize).join(', ')],
      ['Response time limit', `${contract.response_time_limit_ms} ms`],
      ['Contract catalog', `Version ${contract.catalog_version}`],
    ]) {
      const row = element('div', null, 'contract-line');
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
    const name = state.file === 'checks' ? 'checks.json' : 'change_log.md';
    target.append(element('p', state.file === 'checks' ? 'Current draft checks. Visible-check scoring is not available in this build.' : 'Current draft change log. Decisions are not inferred from saves or runs.', 'empty'));
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
    button.addEventListener('click', () => { state.intent += 1; state.selected = output.id; renderCustomers(); });
    return button;
  }));
  if (focusedOutput) [...list.children].find(button => button.dataset.outputId === focusedOutput)?.focus({ preventScroll: true });
  const output = state.outputs.find(item => item.id === state.selected);
  if (!output) return;
  const selected = $('selected-evidence');
  selected.dataset.runId = output.run_id;
  selected.dataset.requestOrdinal = output.request_ordinal;
  selected.replaceChildren();
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
    row.append(element('strong', humanize(event.event_type)), element('small', `Event ${event.seq} · result ${event.derivation.check_id}`)); ledger.append(row);
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
    for (const [label, value] of [['Cause', entry.cause], ['Falsifier', entry.falsifier], ['Public test', entry.public_test]]) {
      const line = element('div', null, 'contract-line');
      line.append(element('span', label), element('strong', value));
      row.append(line);
    }
    if (entry.revision_of_id) row.append(element('p', `The earlier entry ${entry.revision_of_id} stays in this list unchanged.`, 'evidence-meta'));
    return row;
  }));
}
function renderSource(station) {
  const select = $('source-ordinal');
  const run = state.run;
  const previous = select.value;
  select.replaceChildren(...state.outputs.map(output => {
    const option = element('option', `Request ${output.request_ordinal}`);
    option.value = String(output.request_ordinal);
    return option;
  }));
  if (previous && [...select.options].some(option => option.value === previous)) select.value = previous;
  const ready = Boolean(station && run && state.outputs.length);
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
  for (const option of $('assist-role').options) option.disabled = station?.assist_limit === 1 && option.value !== 'HINT';
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
  $('request-assist').disabled = state.pending || !station;
}
function renderDiagnostic(station) {
  const experiment = state.diagnostic ?? station?.latest_diagnostic ?? null;
  const trial = experiment?.trials?.[0] ?? null;
  const output = trial?.outputs?.[0] ?? null;
  const result = $('diagnostic-result');
  $('run-diagnostic').disabled = state.pending || !(station?.latest_investigation_id || station?.bootstrap_available) || !state.board?.latest_saved_version_id;
  if (!station) { text('diagnostic-note', ''); return empty(result, 'No shift loaded.'); }
  if (!experiment) {
    text('diagnostic-note', station.bootstrap_available && !station.latest_investigation_id
      ? 'Freeze your inherited draft to own an exact version, then run the one public source diagnostic. It cannot qualify a version or change business history.'
      : station.latest_investigation_id
        ? 'Ready. The diagnostic runs your frozen version against the reviewed public request and state, then checks each requested task.'
        : 'Record your cause, falsifier and public test first. The diagnostic cites your entry and cannot run before it exists.');
    return empty(result, 'No public diagnostic has run in this shift, and none can qualify a version.');
  }
  text('diagnostic-note', experiment.declared_treatment);
  result.dataset.experimentId = experiment.id;
  result.replaceChildren();
  for (const [label, value] of [
    ['Evidence class', `${experiment.context_evidence_class} · ${humanize(experiment.kind)}`],
    ['Trial state', trial ? `${trial.state} · candidate ${trial.candidate_label}` : 'No trial reserved'],
    ['Frozen context', `${experiment.context_hash} · workload ${trial?.workload_id ?? 'not reserved'}`],
  ]) {
    const line = element('div', null, 'contract-line');
    line.append(element('span', label), element('strong', value));
    result.append(line);
  }
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
  if (trial.missing_evidence.length) eligibility.append(element('p', `Missing evidence: ${trial.missing_evidence.join('; ')}`, 'denial'));
  result.append(eligibility);
}
function renderInvestigate() {
  const station = state.stationView;
  text('investigate-state', station ? `${station.shift_id} · ${station.opening_mode ? humanize(station.opening_mode) : 'opening mode unknown'} · ${station.latest_investigation_id ?? 'no entry yet'}` : 'No shift loaded');
  const orientation = $('orientation-list');
  orientation.replaceChildren(...(station?.orientation?.steps ?? ['Orientation loads with your shift.']).map(step => element('li', step)));
  if (station) renderInvestigations(station); else empty($('investigation-list'), 'No verified entries loaded.');
  renderAssist(station);
  renderSource(station);
  renderDiagnostic(station);
}
function renderCompare() {
  const board = state.board;
  const shift = board?.latest_shift ?? null;
  const compare = state.comparison;
  const candidates = state.candidates;
  text('compare-state', shift ? `${shift.id} · ${compare ? `${compare.id} · ${humanize(compare.state)}` : 'no comparison reserved'}` : 'No shift loaded');
  text('compare-tag', !shift ? 'Not loaded' : compare ? `${compare.trials.length} slots · ${humanize(compare.state)}` : 'Not reserved');
  const selectedHere = Boolean(compare && board?.operating_selection?.comparison_id === compare.id);
  const rationale = $('selection-rationale').value.trim();
  const eligible = label => compare?.outcome?.status === 'COMPLETE' &&
    compare.outcome.eligibility.some(item => item.candidate_label === label && item.eligible);
  for (const label of ['A', 'B']) $('select-candidate-' + label.toLowerCase()).disabled =
    state.pending || !shift || shift.state !== 'open' || selectedHere || !eligible(label) || !rationale;
  text('selection-note', selectedHere ? `Choice ${board.operating_selection.id} is recorded. Saving or testing does not change it.`
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
  for (const id of ['freeze-candidate-a', 'freeze-candidate-b']) $(id).disabled = state.pending || !shift || !editable;
  $('run-comparison').disabled = state.pending || !shift || !editable || !candidates.A || !candidates.B || candidates.A.id === candidates.B.id || !state.stationView?.latest_investigation_id || !treatment;
  text('compare-note', !shift ? 'Open a shift to compare candidates.'
    : !editable ? 'This shift is closed. Its recorded comparison evidence stays available.'
    : !candidates.A || !candidates.B ? 'Freeze two distinct candidate versions to reserve a comparison. Freezing never selects one.'
    : candidates.A.id === candidates.B.id ? 'The two candidates are the same frozen version. Freeze a second, different version.'
    : !state.stationView?.latest_investigation_id ? 'Record your cause, falsifier and public test first. A comparison cites your investigation entry and cannot run before it exists.'
    : !treatment ? 'Name the one declared treatment that differs between the two candidates.'
    : 'The controller requires operator-sealed workloads and protected variants before reservation. Draft material is refused. This station derives no winner.');
  const slots = $('comparison-slots');
  const outcomeView = $('comparison-outcome');
  if (!compare) { text('compare-summary', ''); outcomeView.replaceChildren(); return empty(slots, 'Every slot, its run, version, batch count and missing evidence appear here once reserved.'); }
  const protectedStatus = compare.protected_counts
    ? Object.entries(compare.protected_counts).map(([label, count]) => `${label}: ${count.captured} captured, ${count.missing} missing of ${count.reserved}`).join(' · ')
    : 'protected capture counts appear after the comparison ends';
  const outcome = compare.outcome;
  text('compare-summary', `${compare.candidates.map(candidate => `Candidate ${candidate.label} · ${candidate.artifact_version_id} · ${candidate.artifact_content_hash.slice(0, 12)}…`).join(' · ')} · ${outcome?.status ?? 'INCOMPLETE'} · public requests per candidate ${compare.shared_public_denominator_requests} · protected steps per candidate ${compare.protected_denominator_requests_per_candidate} · ${protectedStatus} · no winner derived here`);
  outcomeView.replaceChildren();
  if (outcome) {
    const note = element('p', `${compare.context_evidence_class} evidence. Public efficiency excludes protected steps. Non-completion categories are incidences and may overlap. Unknown usage or cost is never treated as zero.`, 'comparison-outcome-note');
    outcomeView.append(note);
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
  if (!shift || !choice) empty(inheritance, 'No inherited selection. Make an explicit choice in a comparison first.');
  else {
    inheritance.replaceChildren();
    for (const [label, field, value] of [
      ['Operating choice', 'operating-choice', `${choice.id} · ${choice.selected_version_id} · ${humanize(choice.state)}`],
      ['Recorded rationale', 'rationale', choice.rationale],
      ['Selected content hash', 'selected-hash', choice.selected_content_hash],
      ['Retained alternative', 'retained-alternative', choice.retained_alternative_version_id],
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
    const run = board.latest_run && !laterRuns.has(board.latest_run.id) ? board.latest_run : null;
    history.dataset.latestRun = run?.id ?? '';
    history.replaceChildren();
    for (const [label, value] of [
      ['Latest recorded run', run ? `${run.id} · ${humanize(run.purpose)} · ${humanize(run.state)} · ${run.evidence_mode ?? 'evidence mode unknown'}` : 'The newest run is a slot of the hypothetical experiment below, not operational history.'],
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
    experiment.dataset.experimentState = 'none';
    empty(experiment, 'No later-condition experiment on this shift. One becomes available after an operation records an observed condition change, such as a dependency outage, and it never replaces that operation.');
  } else {
    experiment.dataset.experimentId = later.id;
    experiment.dataset.experimentState = later.state;
    experiment.dataset.outcomeStatus = later.outcome?.status ?? 'INCOMPLETE';
    experiment.dataset.observedRunId = later.observed_run_id ?? '';
    experiment.replaceChildren();
    const versions = Object.fromEntries(later.candidates.map(candidate => [candidate.label, candidate.artifact_version_id]));
    for (const [label, value] of [
      ['Experiment', `${later.id} · ${humanize(later.state)}`],
      ['Observed operation', later.observed_run_id ?? 'none'],
      ['Observed condition', later.condition ? `${later.condition.public_label} (${later.condition.kind})` : 'not recorded'],
      ['Re-tested versions', `A ${versions.A ?? 'none'} (selected) · B ${versions.B ?? 'none'} (retained alternative)`],
      ['Outcome', later.outcome?.status ?? 'INCOMPLETE'],
      ['Slots', `${later.trials.filter(trial => trial.state === 'COMPLETE').length} of ${later.trials.length} complete`],
    ]) {
      const row = element('div', null, 'contract-line');
      row.append(element('span', label), element('strong', value));
      experiment.append(row);
    }
  }
  const open = shift?.state === 'open';
  $('close-shift').disabled = state.pending || !shift || !open;
  $('open-next-shift').disabled = state.pending || !shift || open;
  text('next-help', !shift ? 'No shift loaded.'
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
    if (state.board) { renderBoard(); renderCompare(); }
  }
}
async function runComparison() {
  const shiftId = state.board?.latest_shift?.id;
  const [a, b] = [state.candidates.A, state.candidates.B];
  if (!shiftId || !a || !b || state.pending) return;
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
    state.comparison = experiment;
    renderCompare();
    const deadline = Date.now() + 180000;
    while (!['FINALIZED', 'FAILED'].includes(experiment.state) && Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 500));
      experiment = await api(`/experiments/${encodeURIComponent(experiment.id)}`);
      state.comparison = experiment;
      renderCompare();
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
      source_run_id: state.run.id,
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
    if (state.board) { renderBoard(); renderInvestigate(); }
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
    if (state.board) { renderBoard(); renderInvestigate(); }
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
    if (state.board) renderInvestigate();
  }
}
async function runDiagnostic() {
  const shiftId = state.board?.latest_shift?.id;
  const versionId = state.board?.latest_saved_version_id;
  if (!shiftId || !versionId || state.pending) return;
  state.pending = true; renderBoard(); renderInvestigate();
  try {
    let experiment = await api(`/shifts/${encodeURIComponent(shiftId)}/experiments`, { method: 'POST', body: JSON.stringify({
      kind: 'DIAGNOSTIC',
      investigation_id: state.stationView?.latest_investigation_id ?? null,
      candidate_a_version_id: versionId,
      client_request_id: requestId('diagnostic'),
    }) });
    state.diagnostic = experiment;
    renderInvestigate();
    const deadline = Date.now() + 75000;
    while (!['COMPLETE', 'FAILED'].includes(experiment.trials[0]?.state) && Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 400));
      experiment = await api(`/experiments/${encodeURIComponent(experiment.id)}`);
      state.diagnostic = experiment;
      renderInvestigate();
    }
    await refresh();
  } catch (error) {
    await refresh();
    text('investigate-error', error.message);
  } finally {
    state.pending = false;
    if (state.board) { renderBoard(); renderInvestigate(); }
  }
}

const stations = {
  service: ['Service workbench', 'YOUR WORKING ARTIFACT', 'Your version, contract and files belong to you. Independent scoring stays separate.'],
  owner: ['Committed contract', 'OWNER DESK', 'Inspect your committed contract. Contract editing and visible-check authoring are not available in this build.'],
  customers: ['Customer evidence', 'FOLLOW AN EXECUTED REQUEST', 'Select a customer. Every output, public record, check and event below belongs to that request.'],
  pipeline: ['Evidence trail', 'OUTPUT → CHECK → LEDGER', 'This path traces recorded evidence, not a prediction of success.'],
  ledger: ['Incident & ledger wall', 'RECORDED CONSEQUENCES', 'Synthetic scenario. Select an incident to inspect the output and result that opened it.'],
  repair: ['Repair review', 'REPAIR BENCH · READ ONLY', 'Inspect an actual incident below. Repair authoring and rerunning a new version are not available in this build.'],
  evaluator: ['Independent evaluator', 'LOCKED · NOT EDITABLE', 'Neither the learner nor an assistant can edit the scoring rules or see sealed expected values.'],
  investigate: ['Investigate a failure', 'REVIEW THE EXECUTED REQUEST', 'Read the exact request and output, then write your cause, falsifier and public test. A diagnostic cannot qualify a version.'],
  compare: ['Compare two repairs', 'PAIRED CANDIDATE EXECUTION', 'Both candidates run the same frozen workloads under shared requirements and ceilings. This station shows every slot and its missing evidence; it never picks a winner.'],
  next: ['Next shift', 'INHERITED EXACTLY, TESTED LATER', 'Close this shift and open the next one from the exact selection. Recorded operational history and a later-condition experiment are shown as two separate things: the experiment is hypothetical and never rewrites the history.'],
};
function bringStationPanelIntoReach() {
  // Narrow layouts stack the panel below the room, so a station selection can
  // leave its content entirely below the viewport. Move focus and scroll to the
  // selected station's panel so the authoritative view is immediately reachable.
  // Skipped before the first load paints, so a page open still starts at the room.
  if (!state.board) return;
  if (!window.matchMedia('(max-width: 760px)').matches) return;
  const panel = $('station-panel');
  panel.focus({ preventScroll: true });
  panel.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
}
function activateStation(name, userIntent = true) {
  if (userIntent) state.intent += 1;
  if (name === 'repair' && !state.board?.incidents.length) {
    text('station-context', 'No unresolved incident is loaded. The repair bench becomes available for an actual incident.');
    return;
  }
  state.station = name;
  document.querySelectorAll('[data-station]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.station === name)));
  const [title, kicker, context] = stations[name];
  text('panel-title', title); text('panel-kicker', kicker); text('station-context', context);
  $('deferred-view').hidden = name !== 'evaluator';
  $('customer-view').hidden = !['customers', 'pipeline'].includes(name);
  $('investigate-view').hidden = name !== 'investigate';
  $('compare-view').hidden = name !== 'compare';
  $('next-view').hidden = name !== 'next';
  $('board-view').hidden = !['service', 'owner', 'ledger', 'repair'].includes(name);
  if (name === 'evaluator') {
    text('deferred-title', 'Separate by design.');
    text('deferred-copy', 'The controller scores captured service outputs against independent checks. You can inspect recorded results at the customer queue, but this booth has no editing controls and never displays sealed expected values.');
  }
  if (name === 'owner') { state.file = 'contract'; selectFile('contract'); }
  if (state.board) text('service-tag', state.board.operating_selection
    ? `${state.board.operating_selection.selected_version_id} · ${humanize(state.board.operating_status)}`
    : state.board.latest_version ? `${state.board.latest_version.id} · candidate only` : 'Draft · not frozen');
  renderCustomers();
  renderInvestigate();
  renderCompare();
  renderNext();
  const view = name === 'owner' ? 'contract' : name === 'repair' ? 'repair' : ['customers', 'pipeline', 'evaluator'].includes(name) ? 'customers' : 'board';
  state.view = view;
  if (userIntent) history.replaceState(null, '', `#${view}`);
  document.querySelectorAll('[data-view]').forEach(link => {
    if (link.dataset.view === view) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
  });
  if (userIntent) bringStationPanelIntoReach();
}
function selectFile(name) {
  state.file = name;
  document.querySelectorAll('[data-file]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.file === name)));
  renderArtifact();
}
function navigate(view, userIntent = true) {
  if (view === 'station-panel') return;
  if (['return', 'away'].includes(view)) {
    if (userIntent) { state.intent += 1; history.replaceState(null, '', `#${view}`); }
    state.view = view;
    document.querySelectorAll('[data-station]').forEach(button => button.setAttribute('aria-pressed', 'false'));
    text('station-context', 'This journey view is planned for Slice 11; no later shift is started here.');
    delete document.body.dataset.evidence;
    $('board-view').hidden = true; $('customer-view').hidden = true; $('investigate-view').hidden = true; $('deferred-view').hidden = false;
    text('panel-title', view === 'return' ? 'Return to your work' : 'Northline workshop');
    text('panel-kicker', 'PLANNED FOR SLICE 11');
    text('deferred-title', 'Not part of this client slice yet.');
    text('deferred-copy', view === 'return' ? 'The inherited-room view arrives in Slice 11. This preview does not start a later shift or disclose its customer requests.' : 'The distinct bike-cooperative workshop arrives in Slice 11. No bookshop results are presented as away-shift work.');
    document.querySelectorAll('[data-view]').forEach(link => {
      if (link.dataset.view === view) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
    });
  } else activateStation({ board: 'service', contract: 'owner', customers: 'customers', repair: 'repair' }[view] ?? 'service', userIntent);
}
async function act(action) {
  if (state.pending) return;
  state.pending = true; renderBoard();
  try { await action(); await refresh(); }
  catch (error) { await refresh(); text('load-message', error.message); }
  finally { state.pending = false; if (state.board) renderBoard(); }
}
$('open-shift').addEventListener('click', () => act(() => api('/engagements/bookshop/shifts', { method: 'POST' })));
$('run-shift').addEventListener('click', () => {
  const shiftId = state.board?.latest_shift?.id;
  if (!shiftId) return;
  activateStation('customers');
  act(() => api(`/shifts/${encodeURIComponent(shiftId)}/runs`, { method: 'POST',
    body: JSON.stringify({ client_request_id: requestId('operation') }) }));
});
$('refresh').addEventListener('click', () => refresh());
$('append-investigation').addEventListener('click', appendInvestigation);
$('request-assist').addEventListener('click', requestAssist);
$('run-diagnostic').addEventListener('click', runDiagnostic);
$('freeze-candidate-a').addEventListener('click', () => freezeCandidate('A'));
$('freeze-candidate-b').addEventListener('click', () => freezeCandidate('B'));
$('run-comparison').addEventListener('click', runComparison);
$('treatment-input').addEventListener('input', () => renderCompare());
async function shiftAction(path) {
  if (state.pending || !path) return;
  state.pending = true; renderBoard(); renderNext();
  text('next-error', '');
  try { await api(path, { method: 'POST' }); await refresh(); }
  catch (error) { await refresh(); text('next-error', error.message); }
  finally { state.pending = false; if (state.board) { renderBoard(); renderNext(); } }
}
$('close-shift').addEventListener('click', () => shiftAction(state.board?.latest_shift ? `/shifts/${encodeURIComponent(state.board.latest_shift.id)}/close` : null));
$('open-next-shift').addEventListener('click', () => shiftAction('/engagements/bookshop/shifts'));
$('select-candidate-a').addEventListener('click', () => chooseCandidate('A'));
$('select-candidate-b').addEventListener('click', () => chooseCandidate('B'));
$('selection-rationale').addEventListener('input', () => renderCompare());
$('back-board').addEventListener('click', () => { location.hash = 'board'; navigate('board'); });
document.querySelectorAll('[data-station]').forEach(button => button.addEventListener('click', () => activateStation(button.dataset.station)));
document.querySelectorAll('[data-file]').forEach(button => button.addEventListener('click', () => selectFile(button.dataset.file)));
window.addEventListener('hashchange', () => navigate(location.hash.slice(1)));
window.addEventListener('pagehide', () => { clearTimeout(pollTimer); if (downloadUrl) URL.revokeObjectURL(downloadUrl); });
navigate(location.hash.slice(1) || 'board');
refresh();
