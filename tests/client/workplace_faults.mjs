import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { repoRoot } from './env.mjs';
import path from 'node:path';
const out=process.argv[2];
assert.ok(out?.startsWith('/tmp/shiftwork-s29-')); await mkdir(out,{recursive:true});
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
 ['ledger_count', "if (board && board.ledger_event_count !== events.length) conflict();"],
 ['ledger_histogram', "if ((histogram[type] ?? 0) !== (board?.ledger_totals?.[type] ?? 0)) conflict();"],
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
);
const hostRows=[
 {name:'host_generation',needle:'if(publication.generation!=null && publication.generation<generation) return;',replacement:'void 0;',test:'host_reset_cannot_accept_older_generation',expect:'Older generation mounted after reset'},
 {name:'host_import_token',needle:'if(disposed || owner!==token) return;',replacement:'if(disposed) return;',test:'host_replaced_import_owner_cannot_allocate',expect:'Old import allocated into a newer mount'},
 {name:'host_partial_handle',needle:'if(disposed || owner!==token) { handle.dispose(); return; }',replacement:'if(disposed) { handle.dispose(); return; }',test:'host_partial_initialization_failure_releases_returned_handle',expect:'Failed initialization leaked its returned handle'},
 {name:'host_cached_retry',needle:'if(disposed || brokenModule) return;',replacement:'if(disposed) return;',test:'host_retry_refuses_a_cached_module_failure',expect:'Retry repeated a failed module import'},
 {name:'host_retry_newest',needle:'const prior=previous; latest=publication;',replacement:'const prior=previous; if(!unavailable) latest=publication;',test:'host_retry_accepts_the_newest_publication',expect:'Retry applied an older public view'},
 {name:'host_constructor_failure',needle:"catch { if(owner===token && !disposed) failure('init-failed'); return; }",replacement:'catch { return; }',test:'host_constructor_throw_is_latched_until_explicit_retry',expect:'Thrown initialization did not fail the host'},
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
function run(row,bytes) {
  const inline=row.host?bytes:bytes.replace("'./evidence.js'",JSON.stringify(new URL('../../shiftwork/client/evidence.js',import.meta.url).href));
  return spawnSync(process.execPath,['--test',`--test-name-pattern=^${row.test}$`,path.join(repoRoot,'tests/client/workplace_view.test.mjs')],{encoding:'utf8',env:{...process.env,[row.host?'WORKPLACE_HOST_SOURCE':'WORKPLACE_VIEW_SOURCE']:Buffer.from(inline).toString('base64')}});
}
for(const row of rows) {
  const original=row.host?hostSource:source;
  assert.equal(original.split(row.needle).length-1,1,`Fault anchor ${row.name} is not unique`);
  const clean=run(row,original); assert.equal(clean.status,0,`Clean check ${row.name} failed: ${clean.stdout}`);
  const fault=run(row,original.replace(row.needle,row.replacement));
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
    {name:'omit-dispose-raf',expected:'Owned disposal frame remains scheduled'},
    {name:'omit-suspend-raf',expected:'Owned suspension frame remains scheduled',suspend:true},
    {name:'page-cache-omit-focus',expected:'Page-cache return changed editor continuity or graphics ownership',cache:true},
    ...['generation','intent','current-focus','node','enabled'].map(focus=>({name:`focus-guard-${focus}`,expected:`Focus ${focus} guard restored a stale editor`,focus})),
    ...[
      ...['pointerdown','pointerup','pointercancel','webglcontextlost'].map(type=>[`omit-${type}`,`Partial ${type} listener remains attached`]),
      ['omit-shadow','Partial shadow target remains undisposed'],['omit-dispose-raf','Partial frame remains scheduled'],
      ['omit-geometry','Partial geometry remains allocated'],['omit-material','Partial material remains allocated'],['omit-context','Partial context remains live'],
    ].map(([fault,expected])=>({name:`partial-${fault}`,expected,partial:true})),
    ...['picker','station-column'].map(owner=>({name:`zoom-omit-${owner}`,expected:'200% zoom causes horizontal page scrolling',zoom:true})),
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
