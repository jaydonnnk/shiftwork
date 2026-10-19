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
  const { projectWorkplace } = await api(); const i = input(); const v = projectWorkplace(i);
  assert.deepEqual(Object.keys(v).sort(), ['schemaVersion','context','station','shiftState','operating','saved','run','evidence','investigation','tests','consequences','inheritance','consistency'].sort());
  const needles = ['PRIVATE_RATIONALE','PRIVATE_SOURCE','PRIVATE_BODY','PRIVATE_REQUEST','PRIVATE_EXPECTED', '/Users/private/secret', '\\Users\\private\\secret'];
  const scan = text => needles.filter(n => text.includes(n) || text.includes(JSON.stringify(n).slice(1,-1)) || text.includes(n.replaceAll('\\','/')));
  for (const needle of needles) assert.ok(scan(JSON.stringify({ value: needle })).includes(needle), 'serialized scanner cannot match its needle');
  assert.deepEqual(scan(JSON.stringify(v)), []);
  i.checks[0].verdict = 'pass'; assert.equal(v.evidence.checks[0].verdict, 'fail');
});
test('S29_focus_is_the_only_transition_and_history_is_quiet', async () => {
  const { projectWorkplace, diffWorkplace } = await api(); const i = input(); const a = projectWorkplace(i);
  assert.deepEqual(diffWorkplace(null, a), []); assert.deepEqual(diffWorkplace(a,a), []);
  i.activeStation = 'evaluator'; const b = projectWorkplace(i);
  assert.deepEqual(diffWorkplace(a,b), [{ key: 'station:evaluator', kind: 'station-focus', stationId: 'evaluator', publicRefs: [] }]);
  i.inspection = { mode: 'history', historicalRunId: 'run-1' };
  assert.deepEqual(diffWorkplace(a, projectWorkplace(i)), []);
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
  const module={createWorkplaceScene(options){if(throwDuringCreate) throw Error('injected construction failure');allocations++;const h={options,apply(){},resize(){},setSuspended(v){suspension.push(v);},setReducedMotion(){},dispose(){disposals++;}};handles.push(h);if(failDuringCreate) options.onFailure('shader-failed');return h;}};
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
