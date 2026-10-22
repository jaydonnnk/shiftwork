import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { repoRoot } from './env.mjs';
import path from 'node:path';
const out=process.argv[2];
assert.ok(/^\/tmp\/shiftwork-s(?:29|30|31|32|33|34|35|36|37|38|39)-/.test(out ?? '')); await mkdir(out,{recursive:true});
const source=await readFile(path.join(repoRoot,'shiftwork/client/workplace-view.js'),'utf8');
const hostSource=await readFile(path.join(repoRoot,'shiftwork/client/workplace-host.js'),'utf8');
const rows=[
 ['board_owner', "if (board && board.engagement_slug !== slug) conflict();"],
 ['shift_owner', "if ((input.loadedShiftId ?? null) !== shiftId) conflict();"],
 ['selected_version', "if (selection && operatingVersion && operatingVersion.id !== selection.selected_version_id) conflict();"],
 ['selected_hash', "if (selection && operatingVersion && operatingVersion.content_hash !== selection.selected_content_hash) conflict();"],
 ['run_shift', "if (run && inspection.mode === 'current' && run.shift_id !== shiftId && !nominatedLegacy) conflict();"],
 ['station_shift', "if (stationView && stationView.shift_id !== shiftId) conflict();"],
 ['output_run', "if (outputs.some(output => output.run_id !== run?.id)) conflict();"],
 ['check_run', "if (checks.some(check => check.run_id !== run?.id)) conflict();"],
 ['ledger_status', "else if (input.ledgerStatus !== 'VALID') conflict();", 'else void 0;'],
 ['board_status', "if (board && board.chain_status !== 'VALID') conflict();"],
 ['ledger_count', 'const countMatches = board ? board.ledger_event_count === events.length : null;', 'const countMatches = true;'],
 ['ledger_histogram', 'if ((histogram[type] ?? 0) !== (board?.ledger_totals?.[type] ?? 0)) { histogramMatches = false; conflict(); }', 'if ((histogram[type] ?? 0) !== (board?.ledger_totals?.[type] ?? 0)) { histogramMatches = false; }'],
].map(([name,needle,replacement='void 0;'])=>({name,needle,replacement,test:`multi_read_conflict_${name}`,expect:`${name} disagreement was accepted`}));
rows.push(
 ...[
  ['purpose',"run?.purpose === 'LEGACY_OPERATION' && "],
  ['opening_mode',"board?.latest_shift?.opening_mode === 'LEGACY_FIRST_CHOICE' &&"],
  ['id','board.latest_run?.id === run.id && '],
  ['shift','board.latest_run.shift_id === run.shift_id && '],
  ['version',' && board.latest_run.artifact_version_id === run.artifact_version_id'],
 ].map(([relation,needle])=>({name:'legacy_'+relation,needle,replacement:'',test:`legacy_nomination_${relation}_must_match`,expect:`Legacy ${relation} disagreement was accepted`})),
 {name:'history_identity',needle:"if (run && inspection.mode === 'history' && run.id !== inspection.historicalRunId) conflict();",replacement:'void 0;',test:'history_run_identity_must_match',expect:'Wrong historical run was accepted'},
 {name:'operation_selection',needle:'if (!selection || run.selection_id !== selection.id) conflict();',replacement:'void 0;',test:'operation_selection_must_match',expect:'Operational selection disagreement was accepted'},
 {name:'operation_version',needle:'if (run.artifact_version_id !== selection?.selected_version_id) conflict();',replacement:'void 0;',test:'operation_version_must_match',expect:'Operational version disagreement was accepted'},
 ...[['run','link.run_id !== incident.opening_run_id || '],['output','link.observed_ref !== incident.failing_output_ref || '],['check',' || link.check_id !== incident.check_result_id']].map(([relation,needle])=>({name:'incident_'+relation,needle,replacement:'',test:`incident_${relation}_must_match`,expect:`Incident ${relation} disagreement was accepted`})),
 {name:'verdict',needle:'verdict: check.verdict',replacement:"verdict: 'pass'",test:'finalized_is_not_success',expect:'finalized_is_not_success'},
 {name:'saved',needle:'latestVersionId: board?.latest_saved_version_id ?? null',replacement:'latestVersionId: selection?.selected_version_id ?? null',test:'projection_separates_saved_selected_executed',expect:'projection_separates_saved_selected_executed'},
 {name:'source_absence',needle:'if (selection && !operatingVersion) incomplete();',replacement:'void 0;',test:'optional_selected_source_is_incomplete_not_conflict',expect:'optional_selected_source_is_incomplete_not_conflict'},
 {name:'serialized_leak',needle:'reasonCode: check.reason_code',replacement:'reasonCode: check.reason_code, expected: check.expected_ref',test:'projection_whitelists_scene_fields_and_detaches_arrays',expect:'projection_whitelists_scene_fields_and_detaches_arrays'},
 {name:'diagnostic_purpose',needle:"diagnostic: experiment(input.diagnostic ?? stationView?.latest_diagnostic, 'DIAGNOSTIC')",replacement:"diagnostic: experiment(input.diagnostic ?? stationView?.latest_diagnostic, 'QUALIFYING_COMPARISON')",test:'diagnostic_purpose_guard_rejects_other_kinds',expect:'a comparison was accepted into the diagnostic slot'},
 {name:'comparison_purpose',needle:"comparison: experiment(input.comparison ?? latest, 'QUALIFYING_COMPARISON')",replacement:"comparison: experiment(input.comparison ?? latest, 'DIAGNOSTIC')",test:'comparison_purpose_guard_rejects_other_kinds',expect:'a diagnostic was accepted into the comparison slot'},
 {name:'later_purpose',needle:"later: experiment(latest, 'LATER_CONDITION_COMPARISON')",replacement:"later: experiment(latest, 'QUALIFYING_COMPARISON')",test:'later_purpose_guard_rejects_other_kinds',expect:'a qualifying comparison was accepted into the later slot'},
 {name:'later_same_comparison',needle:'if (tests.later.id === selection?.comparison_id) conflict();',replacement:'void 0;',test:'later_binding_same_as_comparison',expect:'a later experiment reused the original comparison identity'},
 {name:'later_wrong_versions',needle:'if (laterVersions.size !== 2 || !laterVersions.has(selection?.selected_version_id) ||\n        !laterVersions.has(selection?.retained_alternative_version_id)) conflict();',replacement:'void 0;',test:'later_binding_wrong_versions',expect:'a later experiment did not bind the selected and retained versions'},
 {name:'later_missing_observed',needle:'if (!tests.later.observedRunId) conflict();',replacement:'void 0;',test:'later_binding_missing_observed_run',expect:'a later experiment was accepted without an observed operation'},
 {name:'later_observed_trial',needle:'if (tests.later.trials.some(trial => trial.runId === tests.later.observedRunId)) conflict();',replacement:'void 0;',test:'later_binding_observed_run_is_trial',expect:'a later trial run was accepted as the observed operation'},
 {name:'selection_promotion',needle:'if (selection?.comparison_id && tests.diagnostic?.id === selection.comparison_id) conflict();',replacement:'void 0;',test:'diagnostic_cannot_qualify_selection',expect:'a diagnostic was accepted as the selection comparison'},
 {name:'wall_promotion',needle:'if (events.some(event => diagnosticRuns.has(event.derivation?.run_id))) conflict();',replacement:'void 0;',test:'diagnostic_cannot_derive_ledger_event',expect:'a diagnostic trial run derived a ledger event'},
 {name:'test_update_duplicate',needle:'if (before !== after && after !== null) {',replacement:'if (after !== null) {',test:'diagnostic_test_update_is_continuous_and_duplicate_quiet',expect:'a duplicate accepted view produced a transition'},
 {name:'test_update_removal',needle:'if (before !== after && after !== null) {',replacement:'if (before !== after) {',test:'diagnostic_test_update_is_continuous_and_duplicate_quiet',expect:'a removed diagnostic produced a transition'},
 {name:'pending_evidence_suppression',needle:'if (before !== after && after !== null) {',replacement:"if (before !== after && after !== null && previous.evidence?.completeness === 'linked') {",test:'diagnostic_update_survives_pending_evidence_becoming_linked',expect:'a pending evidence route suppressed the test update'},
 {name:'history_quiet',needle:'if (beforeInspection.mode !== afterInspection.mode || beforeInspection.historicalRunId !== afterInspection.historicalRunId) return [];',replacement:'void 0;',test:'diagnostic_history_and_context_changes_are_quiet',expect:'a history change emitted a fresh test update'},
 {name:'comparison_label_unique',needle:'if (new Set(candidates.map(candidate => candidate.label)).size !== candidates.length) conflict();',replacement:'void 0;',test:'comparison_candidate_label_must_be_unique',expect:'a duplicate comparison candidate label was accepted'},
 {name:'comparison_trial_version',needle:'return !bound || trial.artifact_version_id !== bound.artifact_version_id;',replacement:'return false;',test:'comparison_trial_must_bind_the_exact_candidate_version',expect:'a comparison trial carried a different candidate version'},
 {name:'comparison_selected_member',needle:'const chosen = selected.length === 1 ? selected[0] : null;\n    if (!chosen) conflict();\n    else {',replacement:'const chosen = selected.length === 1 ? selected[0] : null;\n    if (chosen) {',test:'comparison_selection_must_bind_one_candidate',expect:'a selection cited a version outside its comparison'},
 {name:'comparison_selected_hash',needle:'if (chosen.contentHash !== selection.selected_content_hash) conflict();',replacement:'void 0;',test:'comparison_selection_content_hash_must_match',expect:'a selection content hash did not match its comparison candidate'},
 {name:'comparison_retained',needle:'if (alternative.length !== 1 || alternative[0].versionId !== selection.retained_alternative_version_id) conflict();',replacement:'void 0;',test:'comparison_selection_retained_alternative_must_match',expect:'a selection retained the wrong alternative'},
 {name:'comparison_missing_slots',needle:'const missingSlots = (item.trials ?? []).filter(trial => !trial.run_id ||\n      (trial.missing_evidence?.length ?? 0) > 0).length;',replacement:'const missingSlots = 0;',test:'comparison_projection_counts_missing_slots',expect:'a missing comparison slot was not counted'},
 {name:'comparison_incomparable',needle:"(item.state === 'INVALIDATED' || Boolean(item.outcome && item.outcome.status !== 'COMPLETE'))",replacement:'false',test:'comparison_projection_reports_blockers_and_incomparable_evidence',expect:'an incomparable comparison was reported as comparable'},
 {name:'comparison_cost',needle:'costMinorUnits: metrics.cost_minor_units ?? null',replacement:'costMinorUnits: metrics.cost_minor_units ?? 0',test:'comparison_projection_keeps_unknown_costs_unknown',expect:'an unknown cost was reported as a number'},
 {name:'comparison_duplicate',needle:'if (beforeComparison !== afterComparison && afterComparison !== null) {',replacement:'if (afterComparison !== null) {',test:'comparison_update_is_continuous_and_duplicate_quiet',expect:'a duplicate accepted view produced a comparison transition'},
 {name:'comparison_removal',needle:'if (beforeComparison !== afterComparison && afterComparison !== null) {',replacement:'if (beforeComparison !== afterComparison) {',test:'comparison_update_is_continuous_and_duplicate_quiet',expect:'a removed comparison produced a transition'},
 {name:'selection_duplicate',needle:'if (beforeSelection !== afterSelection && afterSelection !== null) {',replacement:'if (afterSelection !== null) {',test:'selection_update_is_continuous_and_duplicate_quiet',expect:'a duplicate accepted view produced a selection transition'},
 {name:'selection_removal',needle:'if (beforeSelection !== afterSelection && afterSelection !== null) {',replacement:'if (beforeSelection !== afterSelection) {',test:'selection_update_is_continuous_and_duplicate_quiet',expect:'a removed selection produced a transition'},
);
const wallRows=[
 ['wall_source_label',"source = link.run_id === run?.id && !historyMode ? 'current' : 'historical';","source = 'current';",'wall_projection_labels_sources_links_and_incident_joins','the historical consequence was mislabelled'],
 ['wall_event_run',"if (link.run_id !== run?.id) { linkState = 'historical'; meaning = 'historical'; }","if (false) { linkState = 'historical'; meaning = 'historical'; }",'wall_projection_labels_sources_links_and_incident_joins','the historical consequence was mislabelled'],
 ['wall_event_output',"if (!sourceOutput) { linkState = 'incomplete'; meaning = 'pending'; incomplete(); }","if (false) { linkState = 'incomplete'; meaning = 'pending'; incomplete(); }",'wall_event_route_requires_its_loaded_output_and_ordinal','an event without its output route was reported linked'],
 ['wall_event_check',"else if (!sourceCheck) { linkState = 'incomplete'; meaning = 'pending'; incomplete(); }","else if (false) { linkState = 'incomplete'; meaning = 'pending'; incomplete(); }",'wall_event_route_requires_its_loaded_output_and_ordinal','an event without its check route was reported linked'],
 ['wall_event_ordinal',"else if (!ordinalMatches) { contradiction = 'ordinal'; linkState = 'conflict'; meaning = 'conflict'; conflict(); }","else if (false) { contradiction = 'ordinal'; linkState = 'conflict'; meaning = 'conflict'; conflict(); }",'wall_event_route_contradictions_are_visible_and_conflicting','a ordinal contradiction reported the wrong reason'],
 ['wall_event_bridge',"else if (!bridged) { contradiction = 'link'; linkState = 'conflict'; meaning = 'conflict'; conflict(); }","else if (false) { contradiction = 'link'; linkState = 'conflict'; meaning = 'conflict'; conflict(); }",'wall_event_route_contradictions_are_visible_and_conflicting','a link contradiction was accepted as a linked event'],
 ['wall_event_verdict',"else if (sourceCheck.verdict !== link.verdict) { contradiction = 'verdict'; linkState = 'conflict'; meaning = 'conflict'; conflict(); }","else if (false) { contradiction = 'verdict'; linkState = 'conflict'; meaning = 'conflict'; conflict(); }",'wall_event_route_contradictions_are_visible_and_conflicting','a verdict contradiction was accepted as a linked event'],
 ['wall_incident_opened_type',"if (event.event_type !== 'INCIDENT_OPENED') { conflict(); continue; }","if (false) { conflict(); continue; }",'wall_incident_opened_event_must_be_an_incident_open','a sale event was accepted as an incident opening'],
 ['wall_incident_resolved_missing','if (!resolved) incomplete();','if (false) incomplete();','wall_incident_resolution_join_is_explicit','a missing resolution event was not incomplete'],
 ['wall_incident_resolved_type',"else if (resolvedType !== 'INCIDENT_RESOLVED') conflict();",'else if (false) conflict();','wall_incident_resolution_join_is_explicit','a non-resolution event was accepted as a resolution'],
 ['wall_incident_resolved_id',"else if (resolved.payload?.incident_id !== incident.id) conflict();",'else if (false) conflict();','wall_incident_resolution_join_is_explicit','a resolution for another incident was accepted'],
 ['wall_arrival_purpose',"const eligiblePurpose = run && run.purpose === 'OPERATION';",'const eligiblePurpose = Boolean(run);','wall_arrival_requires_operation_purpose_selection_version_and_shift','an arrival ignored the purpose guard'],
 ['wall_arrival_shift',"const eligibleShift = run && run.shiftId === currentShift;",'const eligibleShift = Boolean(run);','wall_arrival_requires_operation_purpose_selection_version_and_shift','an arrival ignored the shift guard'],
 ['wall_arrival_selection',"const eligibleSelection = run && operating && run.selectionId === operating.selectionId;",'const eligibleSelection = Boolean(run && operating);','wall_arrival_requires_operation_purpose_selection_version_and_shift','an arrival ignored the selection guard'],
 ['wall_arrival_version',"const eligibleVersion = run && operating && run.versionId === operating.versionId;",'const eligibleVersion = Boolean(run && operating);','wall_arrival_requires_operation_purpose_selection_version_and_shift','an arrival ignored the version guard'],
 ['wall_arrival_current',"const isCurrent = event.source === 'current';",'const isCurrent = true;','wall_arrival_requires_the_current_source_linked_route_and_synthetic_event','an arrival ignored the current source guard'],
 ['wall_arrival_linked',"const isLinked = event.linkState === 'linked';",'const isLinked = true;','wall_arrival_requires_the_current_source_linked_route_and_synthetic_event','an arrival ignored the linked route guard'],
 ['wall_arrival_synthetic',"const isSynthetic = event.synthetic === true;",'const isSynthetic = true;','wall_arrival_requires_the_current_source_linked_route_and_synthetic_event','an arrival ignored the synthetic event guard'],
 ['wall_arrival_new',"const isNew = !beforeEvents.has(event.id);",'const isNew = true;','wall_linked_consequence_arrival_is_one_transition_and_duplicate_quiet','a duplicate accepted view produced an arrival'],
].map(([name,needle,replacement,test,expect])=>({name,needle,replacement,test,expect}));
rows.push(...wallRows);
const hostRows=[
 {name:'host_generation',needle:'if(publication.generation!=null && publication.generation<generation) return;',replacement:'void 0;',test:'host_reset_cannot_accept_older_generation',expect:'Older generation mounted after reset'},
 {name:'host_import_token',needle:'if(disposed || owner!==token) return;',replacement:'if(disposed) return;',test:'host_replaced_import_owner_cannot_allocate',expect:'Old import allocated into a newer mount'},
 {name:'host_partial_handle',needle:'if(disposed || owner!==token) { handle.dispose(); return; }',replacement:'if(disposed) { handle.dispose(); return; }',test:'host_partial_initialization_failure_releases_returned_handle',expect:'Failed initialization leaked its returned handle'},
 {name:'host_cached_retry',needle:'if(disposed || brokenModule) return;',replacement:'if(disposed) return;',test:'host_retry_refuses_a_cached_module_failure',expect:'Retry repeated a failed module import'},
 {name:'host_retry_newest',needle:'const prior=previous; latest=publication;',replacement:'const prior=previous; if(!unavailable) latest=publication;',test:'host_retry_accepts_the_newest_publication',expect:'Retry applied an older public view'},
 {name:'host_constructor_failure',needle:"catch { if(owner===token && !disposed) failure('init-failed'); return; }",replacement:'catch { return; }',test:'host_constructor_throw_is_latched_until_explicit_retry',expect:'Thrown initialization did not fail the host'},
 {name:'host_loading_baseline',needle:"if(publication.kind==='loading') { if(!unavailable)",replacement:"if(publication.kind==='loading') { previous=null; if(!unavailable)",test:'host_loading_retains_test_baseline_and_duplicate_is_quiet',expect:'accepted test update did not reach the scene'},
 {name:'host_expanded_reference',needle:"if(view.consistency!=='conflict') previous=view;",replacement:"if(!expanded && view.consistency!=='conflict') previous=view;",test:'host_expanded_updates_advance_the_reference_without_replay',expect:'a duplicate after expansion replayed the suspended update'},
 {name:'host_conflict_reference',needle:"if(view.consistency!=='conflict') previous=view;",replacement:"previous=view.consistency==='conflict'?null:view;",test:'host_conflict_keeps_the_last_consistent_reference',expect:'a conflicting view cleared the consistent reference'},
 {name:'host_reset_reference',needle:"if(publication.kind==='reset') { release(); if(!unavailable)",replacement:"if(publication.kind==='reset') { release(); previous=null; if(!unavailable)",test:'host_reset_reference_replays_one_arrival_at_remount',expect:'an arrival across a reset and remount was lost or replayed'},
 {name:'host_mount_replay',needle:'if(handle.apply(view,transitions) && consequence) onConsequence?.({count: consequence.count ?? 1, eventIds: [...consequence.publicRefs]});',replacement:'if(false) onConsequence?.({count: consequence.count ?? 1, eventIds: [...consequence.publicRefs]});',test:'host_reset_reference_replays_one_arrival_at_remount',expect:'an arrival across a reset and remount was lost or replayed'},
 {name:'host_consequence_started',needle:'if(started && consequence) onConsequence?.',replacement:'if(consequence) onConsequence?.',test:'host_consequence_callback_requires_a_started_trace',expect:'a consequence label fired without a scene trace'},
 {name:'host_consequence_emitted',needle:'if(started && consequence) onConsequence?.({count: consequence.count ?? 1, eventIds: [...consequence.publicRefs]});',replacement:'void 0;',test:'host_consequence_callback_requires_a_started_trace',expect:'a started trace produced no consequence label'},
 {name:'host_resize_cleanup',needle:'size.disconnect();',replacement:'void 0;',test:'host_loading_retains_one_scene_and_double_disposal_is_idempotent',expect:'Resize observer remains attached'},
 {name:'host_intersection_cleanup',needle:'intersection.disconnect();',replacement:'void 0;',test:'host_loading_retains_one_scene_and_double_disposal_is_idempotent',expect:'Intersection observer remains attached'},
 ...[
  ['visibility',"document.removeEventListener('visibilitychange',suspend);"],
  ['motion',"motion.removeEventListener('change',onMotion);"],
  ['retry',"retryButton.removeEventListener('click',retry);"],
  ['simpler',"simplerButton.removeEventListener('click',lowerQuality);"],
 ].map(([owner,needle])=>({name:`host_${owner}_listener_cleanup`,needle,replacement:'void 0;',test:`host_disposes_${owner}_listener`,expect:`Owned ${owner} listener remains attached`})),
 ...[['hidden','document.hidden || '],['offscreen','!visible || '],['expanded',' || expanded']].map(([mode,needle])=>({name:'host_'+mode,needle,replacement:'',test:`host_${mode}_import_completion_draws_nothing`,expect:`${mode} completion initialized graphics`})),
];
rows.push(...hostRows.map(row=>({...row,host:true})));
const receipts=[];
rows.push(
  {name:'gtm_scalar_refs',needle:"typeof value === 'string' ? value : null",replacement:'value',test:'gtm_reference_fields_refuse_objects',expect:'A structured GTM payload reached scene references'},
  {name:'gtm_host_admission',host:true,needle:"board==='bookshop' || board==='gtm'",replacement:"board==='bookshop'",test:'host_gtm_mount_switch_and_stale_pick_keep_board_ownership',expect:'Stonebridge did not mount a real scene'},
  ...[['testStation','compare','test'],['operatingStation','service','selection'],['wallStation','ledger','consequence']].map(([variable,fallback,kind])=>({
    name:`gtm_station_${variable}`,needle:`next.context.board === 'gtm' ? '${variable==='wallStation'?'wall':'workflow'}' : '${fallback}'`,
    replacement:`'${fallback}'`,test:'gtm_transitions_use_canonical_workflow_and_wall',expect:`GTM ${kind} targeted a bookshop station`,
  })),
);
for (const type of ['OWNER_ASSIGNED', 'SLA_CLOCK_STARTED', 'HANDOFF_ESCALATED']) {
  rows.push(
    {name:`gtm_purpose_${type}`, scope:'gtm', needle:"run.purpose !== 'OPERATION'",
      replacement:`run.purpose !== 'OPERATION' && event.event_type !== '${type}'`,
      test:`gtm_purpose_${type}`, expect:`${type} experiment changed operational ownership`},
    {name:`gtm_link_${type}`, scope:'gtm', needle:"!['linked', 'historical'].includes(linkState)",
      replacement:`(!['linked', 'historical'].includes(linkState) && event.event_type !== '${type}')`,
      test:`gtm_link_${type}`, expect:`${type} without a link changed operational ownership`},
    {name:`gtm_synthetic_${type}`, scope:'gtm', needle:'event.synthetic !== true',
      replacement:`(event.synthetic !== true && event.event_type !== '${type}')`,
      test:`gtm_synthetic_${type}`, expect:`${type} non-synthetic event became a routing marker`},
  );
}
function run(row,bytes) {
  const inline=row.host?bytes:bytes.replace("'./evidence.js'",JSON.stringify(new URL('../../shiftwork/client/evidence.js',import.meta.url).href))
    .replace("'./workplace-story.js'",JSON.stringify(new URL('../../shiftwork/client/workplace-story.js',import.meta.url).href));
  return spawnSync(process.execPath,['--test',`--test-name-pattern=^${row.test}$`,path.join(repoRoot,'tests/client/workplace_view.test.mjs')],{encoding:'utf8',env:{...process.env,[row.host?'WORKPLACE_HOST_SOURCE':'WORKPLACE_VIEW_SOURCE']:Buffer.from(inline).toString('base64')}});
}
for (const [slug, types] of [['northline', ['BOOKING_COMMITTED','ESCALATION_TO_HUMAN','COUNTER_FOLLOWUP_RECORDED','ROLLOUT_APPROVED']], ['gtm', ['OWNER_ASSIGNED','SLA_CLOCK_STARTED','HANDOFF_ESCALATED']]]) {
  for (const type of types) {
    rows.push({name:`${slug}_null_run_${type}`,scope:slug,needle:'run && link?.run_id === run.id',replacement:'link?.run_id === run?.id',test:`${slug}_absent_run_and_derivation_${type}`,expect:`${type} absent run crashed ${slug} projection`});
    rows.push({name:`${slug}_synthetic_type_${type}`,scope:slug,needle:'event.synthetic !== true',replacement:`(!event.synthetic || (event.synthetic !== true && event.event_type !== '${type}'))`,test:`${slug}_synthetic_string_${type}`,expect:`${type} admitted non-boolean synthetic string`});
    if(slug !== 'northline') continue;
    rows.push(
      {name:`northline_mapping_${type}`,scope:'northline-wall',needle:`'${type}', `,replacement:'',test:`northline_mapping_${type}`,expect:`${type} has no recorded mapping`},
      {name:`northline_purpose_${type}`,scope:slug,needle:"run.purpose !== 'OPERATION'",replacement:`run.purpose !== 'OPERATION' && event.event_type !== '${type}'`,test:`northline_purpose_${type}`,expect:`${type} ignored its purpose guard`},
      {name:`northline_derivation_${type}`,scope:slug,needle:"!['linked', 'historical'].includes(linkState)",replacement:`(!['linked', 'historical'].includes(linkState) && event.event_type !== '${type}')`,test:`northline_derivation_${type}`,expect:`${type} ignored its derivation guard`},
      {name:`northline_synthetic_${type}`,scope:slug,needle:'event.synthetic !== true',replacement:`(event.synthetic !== true && event.event_type !== '${type}')`,test:`northline_synthetic_${type}`,expect:`${type} ignored its synthetic guard`},
      {name:`northline_link_state_${type}`,scope:slug,needle:"!['linked', 'historical'].includes(linkState)",replacement:`(!['linked', 'historical'].includes(linkState) && event.event_type !== '${type}')`,test:`northline_link_check_${type}`,expect:`${type} ignored its check link`},
    );
  }
}
for (const [name,needle,replacement,test,expect] of [
  ['synthetic','event.synthetic === true && ','','northline_handover_synthetic','Handover ignored its synthetic guard'],
  ['derivation','!link && ','','northline_handover_derivation','Handover ignored its derivation guard'],
  ['reference',"const runbook = publicRef(event.payload?.runbook_version_id);","const runbook = event.payload?.runbook_version_id;",'northline_handover_reference','Handover ignored its reference guard'],
  ['runbook','!link && runbook &&','!link &&','northline_handover_runbook','Handover ignored its runbook guard'],
  ['shift','publicRef(event.cause_refs[0]) && ','','northline_handover_shift','Handover ignored its shift guard'],
  ['arity','event.cause_refs?.length === 2 && ','','northline_handover_arity','Handover ignored its arity guard'],
  ['version','event.cause_refs[1] === runbook','true','northline_handover_version','Handover ignored its version guard'],
]) rows.push({name:`northline_handover_${name}`,scope:'handover',needle,replacement,test,expect});
for (const [variable,value,kind] of [['testStation','bench','test'],['operatingStation','bench','selection'],['wallStation','rollout','outcome']]) rows.push({name:`northline_station_${variable}`,needle:`const ${variable} = next.context.board === 'northline' ? '${value}' : `,replacement:`const ${variable} = `,test:'northline_transitions_use_its_own_stations',expect:`Northline ${kind} targeted another room`});
rows.push({name:'northline_host_admission',host:true,needle:" || board==='northline'",replacement:'',test:'host_gtm_mount_switch_and_stale_pick_keep_board_ownership',expect:'Northline did not mount its actual workshop'});
function mutate(original,row) {
  let start=0,end=original.length;
  if(row.scope==='northline-wall') {start=original.indexOf('  northline:');end=original.indexOf('\n',start);}
  else if(row.scope==='handover') {start=original.indexOf("if (slug === 'northline' && event.event_type === 'HANDOVER_DECLARED')");end=original.indexOf('\n    return {',start);}
  else if(row.scope) {start=original.indexOf(`if (${row.scope}Outcome) {`);end=original.indexOf('\n    }',start)+6;}
  assert.ok(start>=0 && end>start,`Fault scope ${row.name} is missing`);
  const section=original.slice(start,end);
  assert.equal(section.split(row.needle).length-1,1,`Fault anchor ${row.name} is not unique`);
  return original.slice(0,start)+section.replace(row.needle,row.replacement)+original.slice(end);
}
for(const row of rows) {
  const original=row.host?hostSource:source;
  const changed=mutate(original,row);
  const clean=run(row,original); assert.equal(clean.status,0,`Clean check ${row.name} failed: ${clean.stdout}`);
  const fault=run(row,changed);
  const log=fault.stdout+fault.stderr; await writeFile(path.join(out,row.name+'.log'),log);
  assert.notEqual(fault.status,0,`Fault ${row.name} survived`);
  assert.ok(log.includes('ERR_ASSERTION') && log.includes(row.expect),`Fault ${row.name} missed its intended assertion`);
  const restored=run(row,original); assert.equal(restored.status,0,`Restored check ${row.name} failed`);
  assert.equal(await readFile(path.join(repoRoot,'shiftwork/client/workplace-view.js'),'utf8'),source,'Production source changed during fault proof');
  assert.equal(await readFile(path.join(repoRoot,'shiftwork/client/workplace-host.js'),'utf8'),hostSource,'Production host changed during fault proof');
  receipts.push({name:row.name,test:row.test,result:'FAIL_CAUGHT',clean:clean.status,fault:fault.status,restored:restored.status});
}
await writeFile(path.join(out,'faults.json'),JSON.stringify(receipts,null,2)+'\n');
console.log(JSON.stringify({controls:receipts.length,result:'PASS',production:'unchanged'}));

const browserFlag=process.argv.indexOf('--browser');
if(browserFlag!==-1) {
  const base=process.argv[browserFlag+1];
  const resourceRows=[
    ...['pointerdown','pointerup','pointercancel','webglcontextlost'].map(type=>({name:`omit-${type}`,expected:`Owned ${type} listener remains attached`})),
    {name:'omit-shadow',expected:'Owned shadow target remains undisposed'},
    {name:'omit-environment',expected:'Owned environment target remains undisposed'},
    {name:'omit-rounded-cache',expected:'Owned rounded geometry remains allocated'},
    {name:'omit-dispose-raf',expected:'Owned disposal frame remains scheduled'},
    {name:'omit-suspend-raf',expected:'Owned suspension frame remains scheduled',suspend:true},
    {name:'page-cache-omit-focus',expected:'Page-cache return changed editor continuity or graphics ownership',cache:true},
    ...['generation','intent','current-focus','node','enabled'].map(focus=>({name:`focus-guard-${focus}`,expected:`Focus ${focus} guard restored a stale editor`,focus})),
    ...[
      ...['pointerdown','pointerup','pointercancel','webglcontextlost'].map(type=>[`omit-${type}`,`Partial ${type} listener remains attached`]),
      ['omit-shadow','Partial shadow target remains undisposed'],['omit-dispose-raf','Partial frame remains scheduled'],
      ['omit-environment','Partial environment target remains undisposed'],['omit-rounded-cache','Partial rounded geometry remains allocated'],
      ['omit-geometry','Partial geometry remains allocated'],['omit-material','Partial material remains allocated'],['omit-context','Partial context remains live'],
    ].map(([fault,expected])=>({name:`partial-${fault}`,expected,partial:true})),
    {name:'zoom-omit-picker',expected:'200% zoom causes horizontal page scrolling',zoom:true},
    {name:'zoom-omit-station-column',expected:'200% zoom station tag text escapes its control',zoom:true},
    {name:'zoom-omit-navigation',expected:'200% zoom navigation labels escape their controls',zoom:true},
    {name:'host-retry-omit-epoch',expected:'Host retry attached an obsolete import',outer:true},
    {name:'host-evaluation-omit-disable',expected:'Cached outer module retry remained enabled',outer:true,cachedHost:true},
  ];
  const browserReceipts=[];
  const script=`import {runResourceControl,runPageCache,runFocusGuard,runPartialInitialization,runZoom,runHostRetry} from './tests/client/workplace_browser.mjs';
    const [base,out,fault,suspend,cache,focus,partial,zoom,outer,cachedHost]=process.argv.slice(1);
    console.log(outer==='true'?await runHostRetry(base,out,cachedHost==='true',!!fault):zoom==='true'?await runZoom(base,out,fault):partial==='true'?await runPartialInitialization(base,out,fault||'partial-init'):focus?await runFocusGuard(base,out,focus,!!fault):cache==='true'?await runPageCache(base,out,fault||'page-cache'):await runResourceControl(base,out,fault,suspend==='true'));`;
  for(const row of resourceRows) {
    const phases=[];
    for(const phase of ['clean','fault','restored']) {
      const folder=path.join(out,row.name+'-'+phase);
      const result=spawnSync(process.execPath,['--input-type=module','-e',script,base,folder,phase==='fault'?row.name:'',String(!!row.suspend),String(!!row.cache),row.focus??'',String(!!row.partial),String(!!row.zoom),String(!!row.outer),String(!!row.cachedHost)],{cwd:repoRoot,encoding:'utf8',timeout:60000});
      const log=result.stdout+result.stderr;
      await writeFile(folder+'.log',log);
      if(phase==='fault') {assert.notEqual(result.status,0,`${row.name} survived`);assert.ok(log.includes('ERR_ASSERTION')&&log.includes(row.expected),`${row.name} missed its intended assertion: ${log}`);}
      else assert.equal(result.status,0,`${row.name} ${phase} failed: ${log}`);
      phases.push({phase,exit:result.status});
    }
    browserReceipts.push({name:row.name,assertion:row.expected,phases});
    await writeFile(path.join(out,'browser-faults.json'),JSON.stringify(browserReceipts,null,2)+'\n');
  }
  console.log(JSON.stringify({browserControls:browserReceipts.length,result:'PASS',production:'unchanged'}));
}
