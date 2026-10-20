import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openBrowser } from './workplace_browser.mjs';

const TYPES = ['OWNER_ASSIGNED', 'SLA_CLOCK_STARTED', 'HANDOFF_ESCALATED'];
const empty = Object.fromEntries(TYPES.map(type => [type, '35495e']));

export async function runMarker(base, out, fault='s34-marker') {
  const b=await openBrowser(base,out,fault);
  try {
    await b.send('Page.navigate',{url:base+'/?board=gtm#signals'});
    assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready'),'Marker room unavailable');
    const report=await b.evaluate(async()=>{
      const next=structuredClone(globalThis.__s29Latest().view);
      const event={id:'synthetic:owner-arrival',type:'OWNER_ASSIGNED',signalRef:'signal:route-7',owner:'owner-seven',recordRef:'pipeline:route-7',source:'current',synthetic:true,linkState:'linked'};
      const transition={kind:'linked-consequence',publicRefs:[event.id],count:1};
      const sample=()=>{const label=document.querySelector('.workplace-routing-label'),r=label?.getBoundingClientRect();return {position:globalThis.__s34Marker(),screen:globalThis.__s34MarkerScreen(),label:label?.textContent??null,labelBottom:r?.bottom??null};};
      globalThis.__s34SceneApply({...next,consequences:{...next.consequences,events:[event]}},[transition]);
      const frames=[sample()],end=performance.now()+420;
      while(performance.now()<end){await new Promise(requestAnimationFrame);frames.push(sample());}
      return {frames,event};
    });
    assert.ok(new Set(report.frames.map(row=>JSON.stringify(row.position))).size>2,'Signal-bound owner marker did not travel');
    assert.ok(report.frames.some(row=>row.label?.includes(report.event.signalRef)&&row.label.includes(report.event.owner)&&row.label.includes('Synthetic')),'Routing marker lacks the exact synthetic signal and owner label');
    assert.deepEqual(report.frames.at(-1).position,[2.65,1.45,-1.82],'Owner marker did not settle in its ownership lane');
    assert.ok(Math.abs(report.frames.at(-1).screen.y-report.frames.at(-1).labelBottom-8)<2,'Owner label detached from its rendered marker');
    const clip=await b.evaluate(()=>{const r=document.getElementById('workplace-canvas').getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1};});
    const {data}=await b.send('Page.captureScreenshot',{format:'png',clip});
    await writeFile(path.join(out,'owner-marker.png'),Buffer.from(data,'base64'));
    assert.deepEqual(b.commands,[],'Routing marker issued a command');
    assert.deepEqual(b.exceptions,[]);
    await writeFile(path.join(out,'marker.json'),JSON.stringify(report,null,2)+'\n');
    return {frames:report.frames.length,positions:new Set(report.frames.map(row=>JSON.stringify(row.position))).size};
  } finally {await b.close();}
}

export async function runFailedRefresh(base,out,fault='s34-failed-refresh') {
  const b=await openBrowser(base,out,fault);
  try {
    await b.send('Page.navigate',{url:base+'/?board=gtm#wall'});
    assert.ok(await b.until(()=>document.body.dataset.loadState==='ready'),'Ownership wall unavailable');
    const before=await b.evaluate(()=>document.getElementById('pipeline-ownership-status').textContent);
    assert.ok(before.includes('loaded ledger'),'Ownership summary was not loaded before the failure');
    b.releaseImports();
    await b.evaluate(()=>globalThis.__s29Refresh());
    const after=await b.evaluate(()=>({status:document.getElementById('pipeline-ownership-status').textContent,rows:document.querySelectorAll('#pipeline-owners .pipeline-row').length,load:document.body.dataset.loadState}));
    assert.equal(after.status,'No verified ownership records loaded.','Failed refresh retained a stale ownership claim');
    assert.equal(after.rows,0);
    assert.notEqual(after.load,'ready');
    assert.deepEqual(b.commands,[]);
    assert.deepEqual(b.exceptions,[]);
    await writeFile(path.join(out,'failed-refresh.json'),JSON.stringify({before,after},null,2)+'\n');
    return after;
  } finally {await b.close();}
}

export async function runMarkerGuards(base,out,fault='s34-marker-guards') {
  const b=await openBrowser(base,out,fault);
  try {
    await b.send('Page.navigate',{url:base+'/?board=gtm#signals'});
    assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready'));
    const rows=await b.evaluate(async()=>{
      const view=structuredClone(globalThis.__s29Latest().view);
      const owner={id:'owner:guard',type:'OWNER_ASSIGNED',signalRef:'signal:guard',owner:'owner-guard',source:'current',linkState:'linked',synthetic:true};
      const cases=[['reference',[owner],['different:event']],['type',[{...owner,type:'SLA_CLOCK_STARTED'}]],['signal',[{...owner,signalRef:null}]],['owner',[{...owner,owner:null}]],['link',[{...owner,linkState:'incomplete'}]],['historical-link',[{...owner,linkState:'historical'}]],['source',[{...owner,source:'historical'}]],['synthetic',[{...owner,synthetic:false}]],['duplicate',[owner,{...owner,id:'owner:duplicate',owner:'another-owner'}]],['conflict',[owner],[owner.id],'conflict']];
      const rows=[];
      for(const [name,events,refs=[owner.id],consistency='linked'] of cases) {
        globalThis.__s34SceneApply({...view,consistency,consequences:{...view.consequences,events}},[{kind:'linked-consequence',publicRefs:refs,count:1}]);
        const traceStarted=globalThis.__workplaceControls.state().wallTrace;
        const positions=[],end=performance.now()+370;
        do {positions.push(globalThis.__s34Marker());await new Promise(requestAnimationFrame);} while(performance.now()<end);
        rows.push({name,positions,traceStarted,labelHidden:document.querySelector('.workplace-routing-label')?.hidden});
      }
      return rows;
    });
    for(const row of rows) assert.equal(new Set(row.positions.map(p=>JSON.stringify(p))).size,1,`Owner marker ignored ${row.name} guard`);
    assert.equal(rows.find(row=>row.name==='type').traceStarted,true,'Clock arrival lost its shared recorded-evidence trace');
    for(const row of rows.filter(row=>['type','signal','owner','link','duplicate','conflict'].includes(row.name))) assert.equal(row.labelHidden,true,`${row.name} marker label was admitted`);
    const settled=await b.evaluate(async()=>{
      const next=structuredClone(globalThis.__s29Latest().view),event={id:'owner:motion',type:'OWNER_ASSIGNED',signalRef:'signal:motion',owner:'owner-motion',source:'current',linkState:'linked',synthetic:true};
      globalThis.__s34SceneApply({...next,consequences:{...next.consequences,events:[event]}},[{kind:'linked-consequence',publicRefs:[event.id],count:1}]);
      return {before:globalThis.__s34Marker()};
    });
    await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
    assert.ok(await b.until(()=>!globalThis.__workplaceControls.state().wallTrace),'Reduced motion did not settle owner travel');
    assert.deepEqual(await b.evaluate(()=>globalThis.__s34Marker()),[2.65,1.45,-1.82]);
    await b.evaluate(()=>globalThis.__workplaceDispose());
    assert.equal(await b.evaluate(()=>document.querySelectorAll('.workplace-routing-label').length),0,'Disposed scene retained an ownership label');
    assert.deepEqual(b.commands,[]);assert.deepEqual(b.exceptions,[]);
    await writeFile(path.join(out,'marker-guards.json'),JSON.stringify({rows,settled},null,2)+'\n');
    return {guards:rows.map(row=>row.name),reducedMotion:true,labelDisposed:true};
  } finally {await b.close();}
}

export async function runMarkerOverlap(base,out,fault='s34-marker-overlap') {
  const b=await openBrowser(base,out,fault);
  try {
    await b.send('Page.navigate',{url:base+'/?board=gtm#signals'});
    assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready'));
    const result=await b.evaluate(async()=>{
      const view=structuredClone(globalThis.__s29Latest().view);
      const first={id:'owner:first',type:'OWNER_ASSIGNED',signalRef:'signal:first',owner:'owner-first',source:'current',linkState:'linked',synthetic:true};
      const second={...first,id:'owner:second',signalRef:'signal:second',owner:'owner-second'};
      const apply=(events,id)=>globalThis.__s34SceneApply({...view,consequences:{...view.consequences,events}},[{kind:'linked-consequence',publicRefs:[id],count:1}]);
      apply([first],first.id);
      await new Promise(r=>setTimeout(r,70));
      const moving=globalThis.__s34Marker();
      apply([first,second],second.id);
      const after=globalThis.__s34Marker(),label=document.querySelector('.workplace-routing-label').textContent;
      await new Promise(r=>setTimeout(r,400));
      return {moving,after,label,final:globalThis.__s34Marker(),trace:globalThis.__workplaceControls.state().wallTrace};
    });
    assert.notDeepEqual(result.moving,[2.65,1.45,-1.82],'Overlap precondition did not enter owner travel');
    assert.deepEqual(result.after,[2.65,1.45,-1.82],'A newer owner label inherited another signal travel');
    assert.ok(result.label.includes('signal:second')&&result.label.includes('owner-second'));
    assert.deepEqual(result.final,result.after,'Overlapping owner arrivals queued another animation');
    assert.equal(result.trace,false);
    assert.deepEqual(b.commands,[]);assert.deepEqual(b.exceptions,[]);
    await writeFile(path.join(out,'overlap.json'),JSON.stringify(result,null,2)+'\n');
    return result;
  } finally {await b.close();}
}

export async function runRouting(base, out, fault = 's34-routing') {
  const b = await openBrowser(base, out, fault);
  const rows = [];
  try {
    await b.send('Page.navigate', {url:base+'/?board=gtm#signals'});
    assert.ok(await b.until(() => document.getElementById('graphics-status')?.dataset.state === 'ready'), 'Stonebridge renderer unavailable');
    const real = await b.evaluate(() => ({board:globalThis.__s29Latest().view.context.board, graphics:globalThis.__workplaceProbe}));
    assert.equal(real.board, 'gtm');
    assert.ok(real.graphics.triangles > 100, 'Stonebridge did not draw geometry');
    const clip = await b.evaluate(() => {
      const e = document.querySelector('#workplace-canvas canvas');
      e.scrollIntoView({block:'center',behavior:'instant'});
      const r = e.getBoundingClientRect();
      return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height,scale:1};
    });
    const {data} = await b.send('Page.captureScreenshot', {format:'png',clip});
    await writeFile(path.join(out,'stonebridge-silhouette.png'), Buffer.from(data,'base64'));
    const apply = async records => {
      await b.evaluate(records => {
        const latest = globalThis.__s29Latest(), view = structuredClone(latest.view);
        view.consistency = 'linked'; view.consequences.events = records;
        globalThis.__s29Host().publish({...latest, view});
      }, records);
      return b.evaluate(() => globalThis.__workplaceControls.state().routing);
    };
    assert.deepEqual(await apply([]), empty, 'An empty ledger created a routing marker');
    for (const type of TYPES) {
      const event = {id:`synthetic:${type}`,type,signalRef:'signal:synthetic',owner:'owner-synthetic',recordRef:'pipeline:signal:synthetic',source:'current',linkState:'linked'};
      assert.deepEqual(await apply([event]), {...empty,[type]:'d7bb75'}, `${type} illuminated another routing lane`);
      if(type !== 'OWNER_ASSIGNED') assert.deepEqual(await apply([{...event,owner:null}]), {...empty,[type]:'d7bb75'}, `${type} was treated as an ownership assignment`);
      assert.deepEqual(await apply([{...event, signalRef:null}]), empty, `${type} without a signal created a routing marker`);
      assert.deepEqual(await apply([{...event, linkState:'incomplete'}]), empty, `${type} without a linked route created a routing marker`);
      rows.push(`${type}: exact lane, missing signal and missing link`);
    }
    const owner = {id:'synthetic:owner',type:'OWNER_ASSIGNED',signalRef:'signal:synthetic',owner:null,source:'historical',linkState:'historical'};
    assert.equal((await apply([owner])).OWNER_ASSIGNED, 'd98a7a', 'Missing owner problem was hidden');
    assert.equal((await apply([{...owner,owner:'owner-a'}, {...owner,id:'synthetic:duplicate',owner:'owner-b'}])).OWNER_ASSIGNED, 'd98a7a', 'Duplicate owner problem was hidden');
    rows.push('missing and duplicate owners remain problems');
    const record = {seq:1,event_type:'OWNER_ASSIGNED',synthetic:true,cause_refs:[],payload:{signal_ref:'signal:synthetic',owner:'owner-a'}};
    const issue = events => b.evaluate(events=>globalThis.__s34Pipeline(events),events);
    assert.equal(await issue([{...record,event_type:'INCIDENT_OPENED'}]), 'signal:synthetic: no recorded owner', 'A signal without an owner row was hidden');
    assert.equal(await issue([{...record,payload:{...record.payload,owner:null}}]), 'signal:synthetic: no recorded owner', 'An owner row without its owner value was hidden');
    assert.equal(await issue([record,{...record,seq:2}]), 'signal:synthetic: 2 duplicate owner records', 'Duplicate owner rows were hidden');
    rows.push('HTML missing row, missing value and duplicate record labels');
    await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
    await apply([]);
    assert.equal(await b.evaluate(() => globalThis.__workplaceControls.state().wallTrace), false, 'Reduced motion retained a routing trace');
    rows.push('reduced motion settles routing');
    assert.deepEqual(b.commands, [], 'Scene-only routing checks issued a command');
    assert.deepEqual(b.exceptions, []);
    const report = {scope:'Synthetic public SceneView inputs in real WebGL2; no operational or handoff execution claim',real,checks:rows};
    await writeFile(path.join(out,'routing.json'), JSON.stringify(report,null,2)+'\n');
    return report;
  } finally {await b.close();}
}

export async function runLater(base, out) {
  const b = await openBrowser(base, out, 's34-later');
  try {
    await b.send('Page.navigate',{url:base+'/?board=gtm#wall'});
    assert.ok(await b.until(() => document.getElementById('graphics-status')?.dataset.state === 'ready'), 'Later Stonebridge room unavailable');
    const before = await b.evaluate(() => globalThis.__s29Latest().view);
    assert.equal(before.tests.later?.kind, 'LATER_CONDITION_COMPARISON', 'Later GTM experiment is missing');
    assert.equal(before.tests.later.state, 'FINALIZED');
    assert.deepEqual(before.tests.later.candidates.map(row=>row.versionId).sort(), [before.operating.versionId,before.operating.retainedAlternativeId].sort(), 'Later GTM versions replaced the inherited choice');
    const records = view => view.consequences.events.map(row => [row.id,row.signalRef,row.owner,row.recordRef]);
    const operation = before.operating;
    await b.evaluate(() => document.querySelector('#handover-incidents .incident-row')?.click());
    assert.ok(await b.until(() => globalThis.__s29Latest()?.view?.context.inspection.mode === 'history'), 'GTM history did not open');
    const historical = await b.evaluate(() => globalThis.__s29Latest().view);
    assert.deepEqual(records(historical), records(before), 'GTM history replaced recorded ownership');
    await b.evaluate(() => globalThis.__s29Refresh());
    assert.equal(await b.evaluate(() => globalThis.__s29Latest().view.context.inspection.mode), 'history', 'Polling left GTM history');
    await b.evaluate(() => document.getElementById('inspect-current').click());
    assert.ok(await b.until(() => globalThis.__s29Latest()?.view?.context.inspection.mode === 'current'), 'GTM explicit return did not restore current');
    const after = await b.evaluate(() => globalThis.__s29Latest().view);
    assert.deepEqual(after.operating, operation, 'GTM history changed the selection');
    assert.deepEqual(records(after), records(before), 'GTM later experiment rewrote owners, clocks or handoffs');
    assert.equal(await b.evaluate(() => globalThis.__workplaceControls.state().wallTrace), false, 'GTM history return replayed an outcome');
    assert.deepEqual(b.commands, [], 'GTM later inspection issued a command');
    assert.deepEqual(b.exceptions, []);
    const report = {selection:operation,later:after.tests.later.id,observedRun:after.tests.later.observedRunId,historicalRun:historical.run.id,records:records(after),current:after.context.inspection};
    await writeFile(path.join(out,'later.json'), JSON.stringify(report,null,2)+'\n');
    return report;
  } finally {await b.close();}
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [base,out,mode] = process.argv.slice(2); await mkdir(out,{recursive:true});
  console.log(JSON.stringify(mode==='overlap'?await runMarkerOverlap(base,out):mode==='guards'?await runMarkerGuards(base,out):mode==='marker'?await runMarker(base,out):mode==='reset'?await runFailedRefresh(base,out):mode==='later'?await runLater(base,out):await runRouting(base,out,mode)));
}
