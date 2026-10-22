// S40 ambient and focus proof. S41 owns recorded replay behavior.
import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { roomDefinitions } from '../../shiftwork/client/workplace-rooms.js';
import { openBrowser, INSTRUMENT, FAULTS } from './workplace_fullscreen.mjs';

INSTRUMENT.push({file:'/workplace-host.js',needle:'return {publish,',
  replacement:`globalThis.__s40Host = {noteInput,setExpanded: value=>{expanded=value;suspend();},
    expire:()=>{lastInput=performance.now()-20001;updateAmbient();},
    visible:value=>{visible=value;suspend();},state:()=>({lastInput,visible,expanded})}; return {publish,`});
INSTRUMENT.push({file:'/workplace-host.js',needle:'scene=handle; handle.setInspector(inspector);',
  replacement:'scene=handle; handle.setInspector(globalThis.__s40FirstInspector ?? inspector);'});
INSTRUMENT.push({file:'/workplace-scene.js',needle:'return { apply, resize,',
  replacement:`globalThis.__s40 = {state:()=>({attention:view.attention,ring:attentionRing.visible,
    station:attentionRing.userData.stationId,scale:attentionRing.scale.x,position:attentionRing.position.toArray(),
    lamps:Object.fromEntries(Object.entries(lampMeshes).map(([id,m])=>[id,{tone:view.lamps.find(l=>l.stationId===id)?.tone,color:m.material.color.toArray()}])),
    camera:camera.matrixWorld.toArray(),projection:camera.projectionMatrix.toArray(),target:drawTarget.toArray(),ease:!!cameraEase,
    clip:[room.bounds.min[0],room.bounds.max[0]].flatMap(x=>[room.bounds.min[1],room.bounds.max[1]].flatMap(y=>[room.bounds.min[2],room.bounds.max[2]].map(z=>new THREE.Vector3(x,y,z).project(camera).z))),
    cameraStarts:globalThis.__s40CameraStarts??0,ambient:ambientEligible(),suspended,frames:globalThis.__s40Frames??0}),
    ring:value=>{attentionRing.visible=value;requestFrame();},
    replay:value=>{replayRunning=value;setAmbient(false);setAmbient(true);},
    apply:changes=>apply({...view,...changes},[]),
    pick:station=>apply({...view,station},[{kind:'station-focus'}]),setAmbient,setInspector,dispose}; return { apply, resize,`});
INSTRUMENT.push({file:'/workplace-scene.js',needle:'cameraEase={start:performance.now(),',
  replacement:'globalThis.__s40CameraStarts=(globalThis.__s40CameraStarts??0)+1; cameraEase={start:performance.now(),'});
INSTRUMENT.push({file:'/workplace-scene.js',needle:'renderer.render(scene, camera);',
  replacement:`renderer.render(scene, camera); globalThis.__s40Frames=(globalThis.__s40Frames??0)+1;
    if(globalThis.__s40Samples) globalThis.__s40Samples.push({time:performance.now(),scale:attentionRing.scale.x,
      attention:attentionRing.userData.stationId,colors:Object.fromEntries(Object.entries(lampMeshes).map(([id,m])=>[id,m.material.color.toArray()]))});`});

const faults={
  compact:['/workplace-scene.js',"tier !== 'compact' && ", ''],
  hidden:['/workplace-host.js','document.hidden || ',''],
  offscreen:['/workplace-host.js','!visible || ',''],
  expanded:['/workplace-host.js',' || expanded;',';'],
  reduced:['/workplace-scene.js','!reducedMotion && !suspended','!suspended'],
  replay:['/workplace-scene.js',' && !replayRunning',''],
  stale:['/workplace-host.js','performance.now()-lastInput<20000','true'],
  cycle:['/workplace-scene.js','now*2*Math.PI/2500','now*2*Math.PI/1000'],
  cap:['/workplace-scene.js',"(tier === 'compact' || (ambientEligible() && !pulse && !comparisonPulse && !selectionPulse && !wallTrace && !cameraEase))","tier === 'compact'"],
  narrow:['/workplace-scene.js',"transitions.some(item=>item.kind==='station-focus') && size?.width>=761","transitions.some(item=>item.kind==='station-focus')"],
  truth:['/workplace-scene.js','room.stationAnchors[next?.attention]','room.stationAnchors[next?.station]'],
  trigger:['/workplace-scene.js',"transitions.some(item=>item.kind==='station-focus') && size?.width>=761","size?.width>=761"],
  cameraReduced:['/workplace-scene.js','if(animate && size.width>=761 && !reducedMotion && !suspended)','if(animate && size.width>=761 && !suspended)'],
  cameraSuspended:['/workplace-scene.js','if(animate && size.width>=761 && !reducedMotion && !suspended)','if(animate && size.width>=761 && !reducedMotion)'],
  cameraDuration:['/workplace-scene.js','(now-cameraEase.start)/180','(now-cameraEase.start)/960'],
  cameraDistance:['/workplace-scene.js','clampLength(0,.3)','clampLength(0,1.5)'],
  cameraLoad:['/workplace-scene.js','fit(inspectorReady);','fit(true);'],
  cameraRepeat:['/workplace-scene.js','if(changed) fit(inspectorReady);','fit(inspectorReady);'],
  cameraClip:['/workplace-scene.js','camera.near=progress===1?cameraEase.toNear:cameraEase.near; camera.far=progress===1?cameraEase.toFar:cameraEase.far;',''],
};
for(const [name,[file,needle,replacement]] of Object.entries(faults)) FAULTS['s40-'+name]={file,needle,replacement,expect:'s40_'+name};
const pause=(b,ms)=>b.evaluate(ms=>new Promise(r=>setTimeout(r,ms)),ms);
const state=b=>b.evaluate(()=>globalThis.__s40.state());
const count=async(b,ms=5000)=>{await pause(b,600);const a=await state(b);await pause(b,ms);const z=await state(b);return {frames:z.frames-a.frames,seconds:ms/1000,before:a,after:z};};

export async function runMotion(base,out,only='',fault='',zoom=1) {
  const b=await openBrowser(base,out,fault?'s40-'+fault:'',{zoom});
  const report={only,fault,rows:[]};
  try {
    await b.send('Emulation.setDeviceMetricsOverride',{width:1280,height:720,deviceScaleFactor:1,mobile:false});
    if(only==='cameraLoad') await b.send('Page.addScriptToEvaluateOnNewDocument',{source:'globalThis.__s40FirstInspector={open:true,widthPx:376};'});
    await b.send('Page.navigate',{url:base+'/?board=bookshop'+(only==='cameraLoad'?'#customers':'#board')});
    assert.ok(await b.until(()=>['ready','empty'].includes(document.body?.dataset.loadState),30000),'S40 workbench did not load');
    await b.evaluate(()=>document.getElementById('workplace-canvas').scrollIntoView({block:'center',behavior:'instant'}));
    assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready',30000),'S40 graphics did not mount');
    b.assertFaultServed();
    const initial=await b.evaluate(()=>globalThis.__s40?.state());
    assert.ok(initial?.ring && initial.station===initial.attention,'ambient_truthful: ring must mark the authoritative attention station');
    assert.equal(await b.evaluate(()=>typeof globalThis.__s40Host?.noteInput),'function','ambient_input: host must expose noteInput');
    const cases=only?[only]:Object.keys(faults);
    for(const name of cases) {
      await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'no-preference'}]});
      await b.send('Emulation.setDeviceMetricsOverride',{width:name==='compact'||name==='narrow'?390:1280,height:720,deviceScaleFactor:1,mobile:false});
      await b.evaluate(()=>{document.getElementById('workplace-canvas').scrollIntoView({block:'center'});globalThis.__s40Host.setExpanded(false);globalThis.__s40Host.visible(true);globalThis.__s40.replay(false);});
      await pause(b,650);
      await b.evaluate(()=>globalThis.__s40Host.noteInput());
      if(name==='lifecycle') await b.evaluate(()=>globalThis.__s40Host.expire());
      if(name==='hidden') await b.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));});
      if(name==='offscreen') await b.evaluate(()=>globalThis.__s40Host.visible(false));
      if(name==='expanded') await b.evaluate(()=>globalThis.__s40Host.setExpanded(true));
      if(name==='reduced') await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
      if(name==='replay') await b.evaluate(()=>globalThis.__s40.replay(true));
      if(name==='stale') await b.evaluate(()=>globalThis.__s40Host.expire());
      if(['compact','hidden','offscreen','expanded','reduced','replay','stale'].includes(name)) {
        const row=await count(b);report.rows.push({name,...row});
        assert.equal(row.frames,0,`s40_${name}: ambient must draw zero frames in five seconds`);
        assert.equal(row.after.scale,1,`s40_${name}: ring must settle`);
      } else if(name==='cap'||name==='cycle') {
        await b.evaluate(()=>{globalThis.__s40Samples=[];});
        const row=await count(b);const samples=await b.evaluate(()=>{const s=globalThis.__s40Samples;globalThis.__s40Samples=null;return s;});
        assert.ok(row.frames>0 && row.frames<=150,`s40_cap: eligible ambient must draw 1..150 frames in five seconds, got ${row.frames}`);
        assert.ok(samples.every(s=>s.scale>=1 && s.scale<=1.05),'s40_amplitude: ring exceeded 1.00..1.05');
        assert.ok(Math.max(...samples.map(s=>s.scale))>1.049 && Math.min(...samples.map(s=>s.scale))<1.001,'s40_amplitude: full cycle was not observed');
        const reference=samples.reduce((a,b)=>a.scale<b.scale?a:b);
        for(const [id,lamp] of Object.entries(row.before.lamps)) {
          const colors=samples.map(s=>s.colors[id]);
          if(['attention','fail'].includes(lamp.tone)) {
            const magnitudes=colors.map(c=>Math.hypot(...c)),ratio=Math.min(...magnitudes)/Math.max(...magnitudes);
            assert.ok(ratio>=.849 && ratio<=.852,`s40_lamp: ${id} brightness must vary 15%`);
            assert.ok(colors.every(c=>c.every((v,i)=>Math.abs(v/reference.colors[id][i]-c[0]/reference.colors[id][0])<1e-6)),'s40_lamp: hue changed');
          } else assert.ok(colors.every(c=>JSON.stringify(c)===JSON.stringify(colors[0])),`s40_lamp: ${lamp.tone} lamp moved`);
        }
        const peaks=samples.filter((s,i)=>i>0&&i<samples.length-1&&s.scale>samples[i-1].scale&&s.scale>=samples[i+1].scale);
        const periods=peaks.slice(1).map((s,i)=>s.time-peaks[i].time);
        assert.ok(periods.length>0 && periods.every(ms=>ms>=2400&&ms<=2600),'s40_cycle: ambient cycle must be 2.5 seconds');
        report.rows.push({name,...row,samples});
      } else if(name==='narrow') {
        for(const [width,height] of [[640,900],[390,844]]) {
          await b.send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
          await b.evaluate(()=>document.getElementById('workplace-canvas').scrollIntoView({block:'center',behavior:'instant'}));await pause(b,650);
          const viewport=await b.evaluate(()=>({width:innerWidth,height:innerHeight,dpr:devicePixelRatio}));
          assert.ok(Math.abs(viewport.dpr-zoom)<.01,'s40_narrow: requested native zoom was not observed');
          const a=await state(b);await b.evaluate(()=>globalThis.__s40.pick('evaluator'));await pause(b,650);const z=await state(b);
          assert.deepEqual(z.camera,a.camera,'s40_narrow: camera moved on a narrow station activation');
          assert.deepEqual(z.projection,a.projection,'s40_narrow: camera projection moved');report.rows.push({name,configured:{width,height,zoom},viewport});
        }
      } else if(name==='truth') {
        await b.evaluate(()=>globalThis.__s40.apply({station:'evaluator',attention:'customers'}));
        const z=await state(b);
        assert.equal(z.station,'customers','s40_truth: ring used chosen station instead of authoritative attention');
        const anchor=roomDefinitions.bookshop.stationAnchors.customers;
        assert.deepEqual(z.position,[anchor[0],.12,anchor[2]],'s40_truth: ring position used chosen station instead of authoritative attention');
        await b.evaluate(()=>globalThis.__s40.apply({attention:null}));assert.equal((await state(b)).ring,false,'s40_truth: null attention has a ring');
        await b.evaluate(()=>globalThis.__s40.apply({attention:'customers',consistency:'conflict'}));assert.equal((await state(b)).ring,false,'s40_truth: conflict has a ring');report.rows.push({name});
      } else if(name==='trigger') {
        const a=await state(b);
        await b.evaluate(()=>{globalThis.__s40.apply({station:'owner'});});await pause(b,650);
        const z=await state(b);assert.deepEqual(z.camera,a.camera,'s40_trigger: a poll/refresh/history apply moved the camera');
        assert.deepEqual(z.projection,a.projection,'s40_trigger: apply changed projection');report.rows.push({name});
      } else if(name==='cameraReduced'||name==='cameraSuspended') {
        if(name==='cameraReduced') await b.send('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
        else await b.evaluate(()=>globalThis.__s40Host.setExpanded(true));
        await pause(b,600);await b.evaluate(()=>globalThis.__s40.pick('service'));
        assert.equal((await state(b)).ease,false,`s40_${name}: camera ease started while motion is forbidden`);report.rows.push({name});
      } else if(name==='cameraDuration'||name==='cameraDistance') {
        const a=await state(b);await b.evaluate(()=>globalThis.__s40.pick('ledger'));await pause(b,500);const z=await state(b);
        if(name==='cameraDuration') assert.equal(z.ease,false,'s40_cameraDuration: camera exceeded 480ms');
        else assert.ok(Math.hypot(...z.target.map((v,i)=>v-a.target[i]))<=.600001,'s40_cameraDistance: station target moved over 0.6 units');
        report.rows.push({name,before:a,after:z});
      } else if(name==='cameraLoad') {
        assert.equal(initial.cameraStarts,0,'s40_cameraLoad: first inspector installation started camera ease');report.rows.push({name});
      } else if(name==='cameraRepeat') {
        await b.evaluate(()=>{globalThis.__s40Host.expire();globalThis.__s40.setInspector({open:true,widthPx:376});});await pause(b,600);
        const a=await state(b);await b.evaluate(()=>globalThis.__s40.setInspector({open:true,widthPx:376}));await pause(b,300);const z=await state(b);
        assert.equal(z.cameraStarts,a.cameraStarts,'s40_cameraRepeat: unchanged inspector state restarted camera ease');report.rows.push({name});
      } else if(name==='cameraClip') {
        for(const width of [761,800,1280]) {
          await b.send('Emulation.setDeviceMetricsOverride',{width,height:720,deviceScaleFactor:1,mobile:false});await pause(b,650);
          const clips=await b.evaluate(async()=>{
            const rows=[];globalThis.__s40.setInspector({open:false,widthPx:0});await new Promise(r=>setTimeout(r,250));
            for(const open of [true,false]) {
              globalThis.__s40.setInspector({open,widthPx:376});
              const end=performance.now()+210;
              while(performance.now()<end){await new Promise(requestAnimationFrame);rows.push(globalThis.__s40.state().clip);}
            }return rows;
          });
          assert.ok(clips.length>=10 && clips.flat().every(z=>z>=-1 && z<=1),`s40_cameraClip: room clipped during inspector ease at ${width}px`);report.rows.push({name,width,clips});
        }
      } else if(name==='restoreAmbient') {
        await b.evaluate(()=>globalThis.__s40Host.setExpanded(true));const paused=await count(b);assert.equal(paused.frames,0,'s40_restoreAmbient: expanded room drew');
        await b.evaluate(()=>globalThis.__s40Host.setExpanded(false));const resumed=await count(b);
        assert.ok(resumed.frames>0 && resumed.frames<=150,'s40_restoreAmbient: recent-input restoration did not resume bounded ambient');report.rows.push({name,paused,resumed});
      } else if(name==='ringReview') {
        await b.evaluate(()=>{globalThis.__s40Host.expire();document.getElementById('station-tags').style.visibility='hidden';document.getElementById('story-layer').style.visibility='hidden';globalThis.__s40.ring(true);});await pause(b,100);
        for(const visible of [true,false]) {
          await b.evaluate(v=>globalThis.__s40.ring(v),visible);await pause(b,100);
          const png=await b.send('Page.captureScreenshot',{format:'png'});await writeFile(out+(visible?'/ring.png':'/no-ring.png'),Buffer.from(png.data,'base64'));
        }report.rows.push({name});
      } else if(name==='lifecycle') {
        const idle=await count(b,10000);assert.equal(idle.frames,0,'s40_lifecycle: load without input drew idle frames');
        for(const type of ['pointerdown','keydown','touchstart']) {
          const before=await b.evaluate(()=>globalThis.__s40Host.state().lastInput);
          await b.evaluate(type=>{document.getElementById('workplace-world').dispatchEvent(type==='keydown'?new KeyboardEvent(type,{key:'Shift',bubbles:true}):new Event(type,{bubbles:true}));},type);
          assert.ok(await b.evaluate(old=>globalThis.__s40Host.state().lastInput>old,before),`s40_lifecycle: ${type} did not renew activity`);
          assert.equal((await state(b)).ambient,true,`s40_lifecycle: ${type} did not resume ambient`);await pause(b,30);
        }
        await pause(b,20500);const expired=await count(b);assert.equal(expired.frames,0,'s40_lifecycle: real 20-second timer failed');
        await b.evaluate(()=>globalThis.__s40Host.noteInput());await pause(b,200);
        const png=await b.send('Page.captureScreenshot',{format:'png'});await writeFile(out+'/desktop.png',Buffer.from(png.data,'base64'));
        await b.evaluate(()=>{window.dispatchEvent(new PageTransitionEvent('pagehide'));window.dispatchEvent(new PageTransitionEvent('pagehide'));});
        const disposed=await count(b);assert.equal(disposed.frames,0,'s40_lifecycle: disposed scene kept drawing');report.rows.push({name,idle,expired,disposed});
      }
      if(name==='hidden') await b.evaluate(()=>{delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));});
    }
    b.assertFaultServed(); assert.deepEqual(b.exceptions,[]);
    await writeFile(out+'/motion.json',JSON.stringify(report,null,2)+'\n');
  } finally {await b.close();}
}
if(process.argv[1]===fileURLToPath(import.meta.url)) await runMotion(...process.argv.slice(2));
