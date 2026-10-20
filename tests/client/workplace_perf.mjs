import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { openBrowser } from './workplace_browser.mjs';

export function verifyPerformance(tier) {
  const compact=tier.width<761;
  assert.equal(tier.cold.length,5,'Performance receipt needs five cold starts');
  assert.equal(new Set(tier.cold.map(r=>r.timeOrigin)).size,5,'Cold starts reused an earlier document');
  assert.equal(tier.samples.length,3,'Performance receipt needs three motion samples');
  assert.ok(tier.cold.every(r=>r.ms<=(compact?4000:3000)),'Cold graphics-ready budget missed');
  for(const sample of tier.samples) {
    assert.ok(sample.intervals.length>0,'No real frame work was sampled');
    assert.ok(sample.median<=(compact?33.4:16.7) && sample.p95<=(compact?50:33.4),'Motion interval budget missed');
    assert.ok(sample.maxTriangles<=(compact?20000:45000),'Triangle budget missed');
    assert.ok(sample.maxCalls<=(compact?45:90),'Draw-call budget missed');
  }
  assert.equal(tier.idle,0,'Idle frame budget missed');
  assert.ok(tier.estimatedBytes<=(compact?24:48)*1024**2,'Estimated allocation budget missed');
}

async function main() {
const [base,out]=process.argv.slice(2); await mkdir(out,{recursive:true});
const board=process.env.SHIFTWORK_PERF_BOARD ?? 'bookshop';
assert.ok(['bookshop','gtm'].includes(board));
const page=parameters=>base+'/?'+new URLSearchParams({board,...parameters})+'#board';
const report={board,scope:'Local headless browser measurements. Synthetic navigation stress. No physical-device certification.',host:{os:os.release(),architecture:os.arch(),powerState:'unmeasured'},tiers:[]};
if(process.platform==='darwin') {
  report.host.macOS=execFileSync('/usr/bin/sw_vers',['-productVersion'],{encoding:'utf8'}).trim();
  report.host.build=execFileSync('/usr/bin/sw_vers',['-buildVersion'],{encoding:'utf8'}).trim();
  report.host.powerState=execFileSync('/usr/bin/pmset',['-g','batt'],{encoding:'utf8'}).split('\n')[0];
}
const nearest=(values,p)=>[...values].sort((a,b)=>a-b)[Math.max(0,Math.ceil(values.length*p)-1)];
const capCheck=process.argv.includes('--cap-check');
for(const width of capCheck?[390]:process.argv.includes('--desktop-only')?[1280]:[1280,390]) {
  const b=await openBrowser(base,path.join(out,String(width)),capCheck?'':'plain');
  const height=width===1280?720:844;
  const tier={width,height,dpr:1,cold:[],samples:[],idle:null};
  try {
    await b.send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width===390});
    await b.send('Network.setCacheDisabled',{cacheDisabled:true});
    await b.send('Network.emulateNetworkConditions',{offline:false,latency:150,downloadThroughput:10000000/8,uploadThroughput:10000000/8});
    for(let n=0;n<(capCheck?1:5);n++) {
      const oldOrigin=await b.evaluate(()=>performance.timeOrigin);
      await b.send('Page.navigate',{url:page({cold:String(n)})});
      assert.ok(await b.until(old=>performance.timeOrigin!==old && ['ready','empty'].includes(document.body?.dataset.loadState),15000,oldOrigin),'Cold workbench did not complete in a new document');
      await b.evaluate(()=>document.getElementById('workplace-canvas').scrollIntoView({block:'center',behavior:'instant'}));
      assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready',15000),'Graphics cold-start did not complete in view');
      const timing=await b.evaluate(()=>{
        const entry=performance.getEntriesByType('resource').find(r=>r.name.endsWith('/workplace-host.js'));
        return {ms:performance.now()-entry.startTime,timeOrigin:performance.timeOrigin,pollingUpperBoundMs:40};
      });
      tier.cold.push(timing);
    }
    await b.send('Network.emulateNetworkConditions',{offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1});
    if(capCheck) {
      const count=await b.evaluate(async()=>{globalThis.__workplaceSamples=[];const end=performance.now()+1100;let n=0;while(performance.now()<end){globalThis.__workplaceApply(n++%2?(document.body.dataset.board==='gtm'?'signals':'customers'):(document.body.dataset.board==='gtm'?'rules':'evaluator'));await new Promise(requestAnimationFrame);}return globalThis.__workplaceSamples.length;});
      assert.ok(count<=34,`Compact scene exceeded 30Hz drawing cap: ${count} frames in 1.1 seconds`);
      console.log(JSON.stringify({compactCapFrames:count})); continue;
    }
    assert.equal(new Set(tier.cold.map(r=>r.timeOrigin)).size,5,'Cold starts reused an earlier document');
    report.tiers.push(tier);
    await writeFile(path.join(out,'performance.json'),JSON.stringify(report,null,2)+'\n');
    b.setInstrumentation(true);
    const oldOrigin=await b.evaluate(()=>performance.timeOrigin);
    await b.send('Page.navigate',{url:page({'motion-sample':'1'})});
    assert.ok(await b.until(old=>performance.timeOrigin!==old && ['ready','empty'].includes(document.body?.dataset.loadState),15000,oldOrigin));
    await b.evaluate(()=>document.getElementById('workplace-canvas').scrollIntoView({block:'center',behavior:'instant'}));
    assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready',15000));
    tier.browser=await b.send('Browser.getVersion',{},false);
    tier.gpu=await b.evaluate(()=>{const gl=document.querySelector('#workplace-canvas canvas').getContext('webgl2'), ext=gl.getExtension('WEBGL_debug_renderer_info');return ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):'unavailable';});
    await b.evaluate(async()=>{await new Promise(r=>setTimeout(r,5000));});
    for(let sample=0;sample<3;sample++) {
      const result=await b.evaluate(async compact=>{
        globalThis.__workplaceSamples=[]; const end=performance.now()+30000;
        let n=0;
        while(performance.now()<end) { globalThis.__workplaceApply(n++%2?(document.body.dataset.board==='gtm'?'signals':'customers'):(document.body.dataset.board==='gtm'?'rules':'evaluator')); await new Promise(requestAnimationFrame); }
        const samples=globalThis.__workplaceSamples; globalThis.__workplaceSamples=null; return samples;
      },width===390);
      const intervals=result.slice(1).map((r,i)=>r.time-result[i].time);
      assert.ok(result.length>1,'No real frame work was sampled');
      tier.samples.push({intervals,median:nearest(intervals,.5),p95:nearest(intervals,.95),maxTriangles:Math.max(...result.map(r=>r.triangles)),maxCalls:Math.max(...result.map(r=>r.calls))});
    }
    tier.idle=await b.evaluate(async()=>{await new Promise(r=>setTimeout(r,100));const before=globalThis.__workplaceProbe.frames;await new Promise(r=>setTimeout(r,10000));return globalThis.__workplaceProbe.frames-before;});
    assert.equal(tier.idle,0,'Idle scene keeps scheduling frames');
    tier.estimatedBytes=await b.evaluate(()=>{const p=globalThis.__workplaceProbe;return p.width*p.height*(p.tier==='compact'?12:48)+(p.tier==='compact'?0:1024*1024*8)+1024*1024;});
    tier.budgetMisses=[];
    if(tier.cold.some(r=>r.ms>(width===390?4000:3000))) tier.budgetMisses.push('cold graphics-ready');
    if(tier.samples.some(r=>r.median>(width===390?33.4:16.7)||r.p95>(width===390?50:33.4))) tier.budgetMisses.push('motion intervals');
    if(tier.samples.some(r=>r.maxTriangles>(width===390?20000:45000)||r.maxCalls>(width===390?45:90))) tier.budgetMisses.push('geometry/draw calls');
    if(tier.estimatedBytes>(width===390?24:48)*1024**2) tier.budgetMisses.push('estimated GPU allocation');
    await writeFile(path.join(out,'performance.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({width,cold:tier.cold.map(r=>r.ms),idle:tier.idle,misses:tier.budgetMisses}));
    verifyPerformance(tier);
  } finally {await b.close();}
}
}
if(process.argv[1]===fileURLToPath(import.meta.url)) await main();
