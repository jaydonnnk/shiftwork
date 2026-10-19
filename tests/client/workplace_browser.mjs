import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, mkdir, writeFile, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromePath, repoRoot } from './env.mjs';

export async function openBrowser(base, out, fault = '', {zoom=1,windowWidth=1280,windowHeight=900}={}) {
  assert.ok(base.startsWith('http://127.0.0.1:'), 'Only owned local previews are allowed');
  assert.ok(/^\/(?:private\/)?tmp\/shiftwork-s29-[^/]+(?:\/|$)/.test(path.resolve(out)), 'S29 receipts must use the approved temporary root');
  await mkdir(out, { recursive: true });
  const profile = await mkdtemp(path.join(out, 'profile-'));
  if(zoom!==1) {
    await mkdir(path.join(profile,'Default'));
    await writeFile(path.join(profile,'Default/Preferences'),JSON.stringify({partition:{default_zoom_level:{x:Math.log(zoom)/Math.log(1.2)}}}));
  }
  const child = spawn(chromePath, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--window-size=${windowWidth},${windowHeight}`, `--user-data-dir=${profile}`, 'about:blank'], { stdio: ['ignore','ignore','pipe'] });
  let socket, session, sequence = 0;
  const pending = new Map(), exceptions = [], commands = [], requests = [], gates = [], events = [];
  let importsReleased = false, instrumented = !['plain','page-cache'].includes(fault);
  const endpoint = await new Promise((resolve,reject) => {
    let stderr = ''; const timer = setTimeout(() => reject(Error('Chrome startup timed out')),15000);
    child.once('error',reject);
    child.stderr.on('data', data => { stderr += data; const m = stderr.match(/DevTools listening on (ws:\/\/\S+)/); if(m) { clearTimeout(timer); resolve(m[1]); } });
  });
  socket = new WebSocket(endpoint); await once(socket,'open');
  function send(method,params = {},scoped = true) {
    return new Promise((resolve,reject) => {
      const id = ++sequence, timer = setTimeout(() => { pending.delete(id); reject(Error(`CDP timeout: ${method}`)); },60000);
      pending.set(id,{resolve,reject,timer}); socket.send(JSON.stringify({id,method,params,...(scoped && session ? {sessionId:session} : {})}));
    });
  }
  socket.addEventListener('message', ({data}) => {
    const m = JSON.parse(data);
    if(['Page.backForwardCacheNotUsed','Page.javascriptDialogOpening'].includes(m.method)) events.push(m);
    if(m.method === 'Page.javascriptDialogOpening' && fault.startsWith('page-cache')) send('Page.handleJavaScriptDialog',{accept:true}).catch(error=>exceptions.push(error.message));
    if(m.method === 'Runtime.exceptionThrown') exceptions.push(m.params.exceptionDetails.text);
    if(m.method === 'Network.requestWillBeSent') { requests.push(m.params.request.url); if(m.params.request.method !== 'GET') commands.push(m.params.request.url); }
    if(m.method === 'Fetch.requestPaused') intercept(m.params).catch(error => { exceptions.push(error.message); });
    const p = pending.get(m.id); if(!p) return; pending.delete(m.id); clearTimeout(p.timer);
    m.error ? p.reject(Error(m.error.message)) : p.resolve(m.result);
  });
  async function intercept({requestId,request}) {
    const url = new URL(request.url), name = url.pathname;
    const hostTimeout=fault==='host-timeout' || fault.startsWith('host-retry');
    const hostEvaluation=fault.startsWith('host-evaluation');
    if(url.origin !== new URL(base).origin && !['data:','about:'].includes(url.protocol)) {
      return send('Fetch.failRequest',{requestId,errorReason:'BlockedByClient'});
    }
    if(!instrumented) return send('Fetch.continueRequest',{requestId});
    const fail = (['host-import','startup-blocking-host'].includes(fault) && name === '/workplace-host.js') ||
      (fault === 'scene-import' && name === '/workplace-scene.js') ||
      (fault === 'core-import' && name.endsWith('/three.core.js'));
    if(fault && fault!=='startup-blocking-host' && !fault.startsWith('omit-') && !fault.startsWith('page-cache') && fault !== 'plain' && fault !== 'context' && (fail || name === '/workplace-scene.js' || ((hostTimeout || hostEvaluation) && name==='/workplace-host.js')) && !importsReleased) await new Promise(resolve=>gates.push(resolve));
    if((hostTimeout || hostEvaluation) && name==='/workplace-host.js') {
      let source=await readFile(path.join(repoRoot,'shiftwork/client/workplace-host.js'),'utf8');
      const needle='export function createWorkplaceHost({container,fallback,status,onStation}) {';
      assert.equal(source.split(needle).length-1,1,'Host construction observation anchor changed');
      source=source.replace(needle,needle+' globalThis.__s29HostConstructions=(globalThis.__s29HostConstructions??0)+1;');
      if(hostEvaluation) source='globalThis.__s29HostEvaluations=(globalThis.__s29HostEvaluations??0)+1;throw Error("injected host evaluation");\n'+source;
      if(hostTimeout) await new Promise(resolve=>setTimeout(resolve,9000));
      return send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'text/javascript'}],body:Buffer.from(source).toString('base64')});
    }
    if(fail) return send('Fetch.fulfillRequest',{requestId,responseCode:404,body:''});
    if(name==='/styles.css' && fault.startsWith('zoom-omit-')) {
      let source=await readFile(path.join(repoRoot,'shiftwork/client/styles.css'),'utf8');
      const needles={'zoom-omit-picker':'.board-picker { display: grid; grid-template-columns: minmax(0,1fr); min-width: 0; gap: 5px; padding: 8px 0; }\n  .board-picker select { width: 100%; }',
        'zoom-omit-navigation':'.journey { grid-template-columns: minmax(0,1fr); }',
        'zoom-omit-station-column':'body[data-board="bookshop"] .room-hotspots { grid-template-columns: minmax(0,1fr); }'};
      assert.ok(Object.hasOwn(needles,fault),'Unknown zoom layout fault');
      const needle=needles[fault];
      assert.equal(source.split(needle).length-1,1,'Zoom layout fault anchor changed');
      source=source.replace(needle,fault==='zoom-omit-picker'?'.board-picker { flex-wrap: wrap; gap: 5px; padding: 8px 0; }\n  .board-picker select { flex: 1; width: 250px; }':'');
      return send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'text/css'}],body:Buffer.from(source).toString('base64')});
    }
    if(name === '/app.js') {
      let source=await readFile(path.join(repoRoot,'shiftwork/client/app.js'),'utf8');
      if(hostTimeout || hostEvaluation) {
        source=source.replace('async function initializeGraphics() {','async function initializeGraphics() { globalThis.__s29InitializeAttempts=(globalThis.__s29InitializeAttempts??0)+1;');
        if(fault==='host-retry-omit-epoch') {
          const needle='    if (epoch !== hostEpoch) return;\n    clearTimeout(hostTimer); hostTimer = null;\n    workplaceHost = createWorkplaceHost';
          assert.equal(source.split(needle).length-1,1,'Host retry epoch anchor changed');
          source=source.replace(needle,needle.replace('    if (epoch !== hostEpoch) return;\n',''));
        }
        if(fault==='host-evaluation-omit-disable') {
          const needle="document.querySelector('[data-graphics-retry]').disabled = true;";
          assert.equal(source.split(needle).length-1,1,'Host module retry guard anchor changed');
          source=source.replace(needle,"document.querySelector('[data-graphics-retry]').disabled = false;");
        }
      }
      const focusGuard=fault.match(/^focus-guard-(generation|intent|current-focus|node|enabled)(-omit)?$/);
      if(focusGuard) {
        const [,guard,omit]=focusGuard;
        const conditions={generation:'generation === state.generation',intent:'focus.intent === state.intent',
          'current-focus':'[document.body, editor].includes(document.activeElement)',node:"editor === $('draft-source')",enabled:'!editor.disabled'};
        if(omit) {
          const needle=conditions[guard];
          assert.equal(source.split(needle).length-1,1,'Focus guard fault anchor changed');
          source=source.replace(needle,'true');
        }
        const needle='  await refreshed;';
        assert.equal(source.split(needle).length-1,1,'Focus race hook anchor changed');
        source=source.replace(needle,`${needle}
          if(globalThis.__s29FocusArmed) {
            if(${JSON.stringify(guard)}==='generation') state.generation++;
            if(${JSON.stringify(guard)}==='intent') state.intent++;
            if(${JSON.stringify(guard)}==='node') editor.replaceWith(editor.cloneNode(true));
            if(${JSON.stringify(guard)}==='enabled') editor.disabled=true;
            if(${JSON.stringify(guard)}==='current-focus') document.querySelector('[data-graphics-simple]').focus({preventScroll:true});
            const r=globalThis.__s29FocusResult={focusCalls:0,selectionCalls:0,guards:{
              generation:generation===state.generation,intent:focus?.intent===state.intent,
              node:editor===$('draft-source'),enabled:!editor.disabled,
              'current-focus':[document.body,editor].includes(document.activeElement)}};
            const focusEditor=editor.focus.bind(editor),select=editor.setSelectionRange.bind(editor);
            editor.focus=(...args)=>{r.focusCalls++;focusEditor(...args);};
            editor.setSelectionRange=(...args)=>{r.selectionCalls++;select(...args);};
          }`);
        const end='    editor.setSelectionRange(focus.start, focus.end, focus.direction);\n  }\n});';
        assert.equal(source.split(end).length-1,1,'Focus completion hook anchor changed');
        source=source.replace(end,end.replace('\n});','\n  globalThis.__s29FocusDone=true;\n});'));
      }
      if(fault==='page-cache-omit-focus') {
        const needle='editor.focus({ preventScroll: true });';
        assert.equal(source.split(needle).length-1,1,'Page-cache focus fault anchor changed');
        source=source.replace(needle,'void 0;');
      }
      if(fault==='startup-blocking-host') source="import './workplace-host.js';\n"+source;
      return send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'text/javascript'}],body:Buffer.from('const __s29Boot=performance.now();\n'+source+'\nglobalThis.__s29BootMs=performance.now()-__s29Boot; globalThis.__s29Refresh=refresh; globalThis.__s29Host=()=>workplaceHost; globalThis.__s29Latest=()=>latestPresentation;\n').toString('base64')});
    }
    if(name === '/workplace-scene.js') {
      let source = await readFile(path.join(repoRoot,'shiftwork/client/workplace-scene.js'),'utf8');
      const sceneFault=fault.startsWith('partial-')?fault.slice('partial-'.length):fault;
      if(sceneFault==='omit-geometry') source=source.replace('for(const g of geometries) g.dispose();','void 0;');
      if(sceneFault==='omit-material') source=source.replace('for(const m of materials) m.dispose();','void 0;');
      if(sceneFault==='omit-context') source=source.replace('renderer?.forceContextLoss();','if(!globalThis.__s29ResourceFaultActive) { renderer?.forceContextLoss(); }');
      const omissions={
        'omit-shadow':['for(const light of sceneLights) light.shadow?.dispose();','void 0;'],
        ...Object.fromEntries(['pointerdown','pointerup','pointercancel','webglcontextlost'].map(type=>[`omit-${type}`,['renderer?.domElement.removeEventListener(type,fn);',`if(type!==${JSON.stringify(type)}) renderer?.domElement.removeEventListener(type,fn);`]])),
        'omit-dispose-raf':['if(disposed) return; disposed = true;\n    if(raf!==null) cancelAnimationFrame(raf);','if(disposed) return; disposed = true;'],
        'omit-suspend-raf':['cancelAnimationFrame(raf); raf=null;','raf=null;'],
      };
      if(Object.hasOwn(omissions,sceneFault)) {
        const [needle,replacement]=omissions[sceneFault];
        assert.equal(source.split(needle).length-1,1,`Missing or nonunique ${fault} anchor`);
        source=source.replace(needle,replacement);
      }
      if(fault.startsWith('partial-')) {
        const needle='if(raf!==null) cancelAnimationFrame(raf); raf = null; draw();';
        assert.equal(source.split(needle).length-1,1,'Partial initialization fault anchor changed');
        source=source.replace(needle,`${needle}
          apply(view,[]);
          globalThis.__s29ResourceFaultActive=true;
          globalThis.__s29PartialBefore={pending:owned.frames.size,shadows:owned.shadows.length,listeners:[...owned.canvases.at(-1).listeners].map(([type,set])=>[type,set.size]),resources:{...globalThis.__s29Resources}};
          throw Error('injected failure before returning the scene handle');`);
        const cleanup='catch(error) { dispose(); throw error; }';
        assert.equal(source.split(cleanup).length-1,1,'Partial cleanup observation anchor changed');
        source=source.replace(cleanup,`catch(error) { dispose();
          globalThis.__s29PartialAfter={before:globalThis.__s29PartialBefore,resources:{...globalThis.__s29Resources},
            pending:owned.frames.size,listeners:Object.fromEntries([...owned.canvases.at(-1).listeners].map(([type,set])=>[type,set.size])),
            shadows:owned.shadows.map(r=>r.disposed),lost:globalThis.__s29GLs.every(gl=>gl.isContextLost()),canvases:container.querySelectorAll('canvas').length};
          throw error; }`);
      }
      source=source.replace('const sceneLights = [];',`const sceneLights = [];
        const owned=globalThis.__s29Owned ??= {canvases:[],shadows:[],frames:new Set()};
        const requestAnimationFrame=callback=>{const id=window.requestAnimationFrame(time=>{owned.frames.delete(id);callback(time);});owned.frames.add(id);return id;};
        const cancelAnimationFrame=id=>{window.cancelAnimationFrame(id);owned.frames.delete(id);};`);
      source=source.replace("renderer.domElement.setAttribute('aria-hidden','true');",`
        const record={node:renderer.domElement,listeners:new Map()};owned.canvases.push(record);
        const add=record.node.addEventListener.bind(record.node),remove=record.node.removeEventListener.bind(record.node);
        record.node.addEventListener=(type,fn,...args)=>{if(!record.listeners.has(type)) record.listeners.set(type,new Set());record.listeners.get(type).add(fn);add(type,fn,...args);};
        record.node.removeEventListener=(type,fn,...args)=>{record.listeners.get(type)?.delete(fn);remove(type,fn,...args);};
        renderer.domElement.setAttribute('aria-hidden','true');`);
      source=source.replace('renderer.render(scene, camera);',`renderer.render(scene, camera);
        for(const light of sceneLights) if(light.shadow?.map && !owned.shadows.some(r=>r.target===light.shadow.map)) {
          const r={target:light.shadow.map,disposed:false};owned.shadows.push(r);r.target.addEventListener('dispose',()=>{r.disposed=true;});
        }`);
      source = source.replace('renderer.outputColorSpace', 'renderer.info.autoReset = false; renderer.outputColorSpace');
      source = source.replace("renderer.domElement.setAttribute('aria-hidden','true');", "globalThis.__s29Resources ??= { contexts:0, geometries:0, materials:0 }; globalThis.__s29GLs ??= []; globalThis.__s29GLs.push(renderer.getContext()); globalThis.__s29Resources.contexts++; renderer.domElement.setAttribute('aria-hidden','true');");
      source = source.replace('renderer?.forceContextLoss();', 'if(renderer) globalThis.__s29Resources.contexts--; renderer?.forceContextLoss();');
      source = source.replace('geometries.add(cube);', "geometries.add(cube); globalThis.__s29Resources.geometries++; cube.addEventListener('dispose',()=>globalThis.__s29Resources.geometries--);");
      for(const name of ['material','rimMaterial']) source=source.replace(`materials.add(${name});`, `materials.add(${name}); globalThis.__s29Resources.materials++; ${name}.addEventListener('dispose',()=>globalThis.__s29Resources.materials--);`);
      source = source.replace('renderer.render(scene, camera);', `renderer.render(scene, camera); globalThis.__workplaceProbe = { frames: (globalThis.__workplaceProbe?.frames ?? 0)+1, triangles: renderer.info.render.triangles, calls: renderer.info.render.calls, geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures, tier, time: performance.now(), width: renderer.domElement.width, height: renderer.domElement.height }; if(globalThis.__workplaceSamples) globalThis.__workplaceSamples.push(globalThis.__workplaceProbe);`);
      source = source.replace('renderer.render(scene, camera);', 'renderer.info.reset(); renderer.render(scene, camera);');
      source = source.replace('return { apply, resize,', 'globalThis.__workplaceApply = station => apply({...view,station}, []); globalThis.__workplaceDispose = dispose; return { apply, resize,');
      source = source.replace('view = next;', 'view = next; globalThis.__s29Applied=structuredClone(next);');
      source = source.replace('return { apply, resize,', `globalThis.__workplaceStationPoint = station => { const p = new THREE.Vector3(...room.stationAnchors[station]); p.y=1.15; p.project(camera); const r=renderer.domElement.getBoundingClientRect(); return {x:r.left+(p.x+1)*r.width/2,y:r.top+(1-p.y)*r.height/2}; }; return { apply, resize,`);
      if(fault === 'constructor') source = source.replace('renderer = new THREE.WebGLRenderer(', 'throw new Error("injected constructor"); renderer = new THREE.WebGLRenderer(');
      if(fault === 'render') source = source.replace('renderer.render(scene, camera);','throw new Error("injected render");');
      if(fault === 'shader') source = source.replace('renderer.render(scene, camera);','renderer.debug.onShaderError();');
      if(fault === 'timeout') source = 'await new Promise(() => {});\n' + source;
      if(fault === 'module-evaluation') source='globalThis.__s29ModuleEvaluations=(globalThis.__s29ModuleEvaluations??0)+1;throw Error("injected module evaluation");\n'+source;
      return send('Fetch.fulfillRequest',{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'text/javascript'}],body:Buffer.from(source).toString('base64')});
    }
    return send('Fetch.continueRequest',{requestId});
  }
  const target = await send('Target.createTarget',{url:'about:blank'},false);
  session = (await send('Target.attachToTarget',{targetId:target.targetId,flatten:true},false)).sessionId;
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable');
  await send('Fetch.enable',{patterns:[{urlPattern:'*'}]});
  if(fault === 'webgl') await send('Page.addScriptToEvaluateOnNewDocument',{source:`const original = HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext = function(type,...args) { return type === 'webgl2' ? null : original.call(this,type,...args); };`});
  async function evaluate(fn,...args) {
    const r = await send('Runtime.evaluate',{expression:`(${fn.toString()})(...${JSON.stringify(args)})`,awaitPromise:true,returnByValue:true});
    if(r.exceptionDetails) throw Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
    return r.result.value;
  }
  async function until(fn,timeout = 12000,...args) {
    const deadline = Date.now()+timeout;
    while(Date.now()<deadline) { if(await evaluate(fn,...args)) return true; await new Promise(r=>setTimeout(r,40)); }
    return false;
  }
  async function close() {
    try { await send('Browser.close',{},false); } finally {
      socket.close(); if(child.exitCode === null && child.signalCode === null) { const exited = once(child,'exit'); child.kill(); await exited; }
      await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:100});
    }
  }
  return {send,evaluate,until,close,exceptions,commands,requests,events,setInstrumentation(value){instrumented=value;},releaseImports() {importsReleased=true; for(const resolve of gates) resolve(); gates.length=0;}};
}

export async function runPageCache(base,out,fault='page-cache') {
  const b=await openBrowser(base,out,fault);
  try {
    await b.send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
    await b.send('Page.navigate',{url:base+'/#compare'});
    assert.ok(await b.until(()=>document.body.dataset.loadState==='ready' && document.getElementById('graphics-status')?.dataset.state==='ready'),'Page-cache initial state unavailable');
    const before=await b.evaluate(()=>{
      const editor=document.getElementById('draft-source');
      editor.value+='\n# S29 page-cache draft\n';editor.dispatchEvent(new Event('input',{bubbles:true}));editor.focus();editor.setSelectionRange(5,19,'backward');
      globalThis.__cacheEditor=editor;globalThis.__cacheGL=document.querySelector('#workplace-canvas canvas').getContext('webgl2');
      globalThis.__cacheEvents=[];
      for(const type of ['pageshow','pagehide']) addEventListener(type,event=>globalThis.__cacheEvents.push({type,persisted:event.persisted,focus:document.activeElement?.id}));
      return {value:editor.value,origin:performance.timeOrigin,focus:document.activeElement===editor};
    });
    assert.equal(before.focus,true,'Editor was not focused before leaving the page');
    const history=await b.send('Page.getNavigationHistory');
    await b.send('Page.navigate',{url:base+'/room.svg'});
    assert.ok(await b.until(()=>location.pathname==='/room.svg'),'Away document did not load');
    await b.send('Page.navigateToHistoryEntry',{entryId:history.entries[history.currentIndex].id});
    assert.ok(await b.until(()=>document.body?.dataset.loadState==='ready' && document.getElementById('graphics-status')?.dataset.state==='ready'),'Page-cache return did not restore the workbench');
    const after=await b.evaluate(()=>{
      const e=document.getElementById('draft-source');
      return {origin:performance.timeOrigin,same:e===globalThis.__cacheEditor,value:e.value,dirty:e.dataset.dirty,focus:e===document.activeElement,start:e.selectionStart,end:e.selectionEnd,direction:e.selectionDirection,events:globalThis.__cacheEvents,oldContextLost:globalThis.__cacheGL?.isContextLost(),canvases:document.querySelectorAll('#workplace-canvas canvas').length};
    });
    await writeFile(path.join(out,'page-cache.json'),JSON.stringify({before,after,cdp:b.events},null,2)+'\n');
    assert.equal(after.origin,before.origin,'Return created a fresh document instead of using page cache');
    assert.deepEqual(after.events?.map(({type,persisted})=>({type,persisted})),[{type:'pagehide',persisted:true},{type:'pageshow',persisted:true}],'Actual persisted page-cache events missing');
    assert.deepEqual({...after,origin:undefined,events:undefined},{origin:undefined,events:undefined,same:true,value:before.value,dirty:'true',focus:true,start:5,end:19,direction:'backward',oldContextLost:true,canvases:1},'Page-cache return changed editor continuity or graphics ownership');
    assert.deepEqual(b.commands,[],'Page-cache return submitted a command');assert.deepEqual(b.exceptions,[]);
    return {result:'PASS',persisted:true,dirtyEditor:true};
  } finally {await b.close();}
}

export async function runResourceControl(base,out,fault='',suspend=false) {
  const b=await openBrowser(base,out,fault);
  try {
    await b.send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
    await b.send('Page.navigate',{url:base+'/'});
    assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready'),'Resource-control room unavailable');
    const result=await b.evaluate(suspend=>{
      const owned=globalThis.__s29Owned, canvas=owned.canvases.at(-1);
      const before=Object.fromEntries([...canvas.listeners].map(([type,set])=>[type,set.size]));
      globalThis.__workplaceApply('customers');
      const pendingBefore=owned.frames.size;
      if(suspend) globalThis.__s29Host().setExpanded(true);
      else {globalThis.__s29Host().dispose();globalThis.__s29Host().dispose();}
      return {before,pendingBefore,pendingAfter:owned.frames.size,listeners:Object.fromEntries([...canvas.listeners].map(([type,set])=>[type,set.size])),shadows:owned.shadows.map(r=>r.disposed),resources:globalThis.__s29Resources};
    },suspend);
    await writeFile(path.join(out,'resources.json'),JSON.stringify(result,null,2)+'\n');
    assert.ok(result.pendingBefore>0,'Pending frame precondition missing');
    assert.equal(result.pendingAfter,0,`Owned ${suspend?'suspension':'disposal'} frame remains scheduled`);
    if(!suspend) {
      for(const type of ['pointerdown','pointerup','pointercancel','webglcontextlost']) {
        assert.equal(result.before[type],1,`${type} listener precondition missing`);
        assert.equal(result.listeners[type],0,`Owned ${type} listener remains attached`);
      }
      assert.ok(result.shadows.length>0,'Actual shadow target precondition missing');
      assert.ok(result.shadows.every(Boolean),'Owned shadow target remains undisposed');
      assert.deepEqual(result.resources,{contexts:0,geometries:0,materials:0},'Resource control leaked scene resources');
    }
    assert.deepEqual(b.exceptions,[]);return {result:'PASS',suspend};
  } finally {await b.close();}
}

export async function runFocusGuard(base,out,guard,omit=false) {
  assert.ok(['generation','intent','current-focus','node','enabled'].includes(guard),'Unknown focus guard');
  const b=await openBrowser(base,out,`focus-guard-${guard}${omit?'-omit':''}`);
  b.releaseImports();
  try {
    await b.send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
    await b.send('Page.navigate',{url:base+'/#compare'});
    assert.ok(await b.until(()=>document.body?.dataset.loadState==='ready'),'Focus guard workbench unavailable');
    const before=await b.evaluate(()=>{
      const e=document.getElementById('draft-source');e.value+='\n# focus race draft\n';e.dispatchEvent(new Event('input',{bubbles:true}));e.focus();e.setSelectionRange(5,19,'backward');
      if(document.activeElement!==e) throw Error('Focus capture precondition missing');
      globalThis.__s29FocusArmed=true;
      const value=e.value;dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}));return value;
    });
    assert.ok(await b.until(()=>globalThis.__s29FocusDone===true),'Focus guard handler did not finish');
    const result=await b.evaluate(()=>({...globalThis.__s29FocusResult,value:document.getElementById('draft-source').value,dirty:document.getElementById('draft-source').dataset.dirty}));
    await writeFile(path.join(out,'focus.json'),JSON.stringify({guard,omit,event:'synthetic persisted pageshow',result},null,2)+'\n');
    assert.deepEqual(result.guards,Object.fromEntries(['generation','intent','current-focus','node','enabled'].map(key=>[key,key!==guard])),'Focus guard scenario was intercepted by another condition');
    assert.equal(result.focusCalls,0,`Focus ${guard} guard restored a stale editor`);
    assert.equal(result.selectionCalls,0,`Focus ${guard} guard rewrote a stale selection`);
    assert.equal(result.value,before,'Focus race changed dirty bytes');assert.equal(result.dirty,'true');
    assert.deepEqual(b.commands,[],'Focus race submitted a command');assert.deepEqual(b.exceptions,[]);
    return {result:'PASS',guard};
  }finally{await b.close();}
}

export async function runPartialInitialization(base,out,fault='partial-init') {
  const b=await openBrowser(base,out,fault);b.releaseImports();
  try {
    await b.send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
    await b.send('Page.navigate',{url:base+'/#customers'});
    assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='unavailable'),'Partial initialization did not fail graphics');
    const result=await b.evaluate(()=>globalThis.__s29PartialAfter);
    await writeFile(path.join(out,'partial.json'),JSON.stringify(result,null,2)+'\n');
    assert.ok(result.before?.pending>0 && result.before.shadows>0 && result.before.resources.contexts===1 && result.before.resources.geometries>0 && result.before.resources.materials>0,'Partial allocation preconditions missing');
    assert.ok(result.lost,'Partial context remains live');assert.equal(result.canvases,0,'Partial canvas remains connected');
    assert.equal(result.pending,0,'Partial frame remains scheduled');
    for(const type of ['pointerdown','pointerup','pointercancel','webglcontextlost']) {
      assert.equal(Object.fromEntries(result.before.listeners)[type],1,'Partial listener precondition missing');
      assert.equal(result.listeners[type],0,`Partial ${type} listener remains attached`);
    }
    assert.ok(result.shadows.every(Boolean),'Partial shadow target remains undisposed');
    assert.equal(result.resources.geometries,0,'Partial geometry remains allocated');
    assert.equal(result.resources.materials,0,'Partial material remains allocated');
    assert.equal(result.resources.contexts,0,'Partial context count remains allocated');
    assert.deepEqual(b.commands,[]);assert.deepEqual(b.exceptions,[]);return {result:'PASS',partial:true};
  }finally{await b.close();}
}

export async function runRetry(base,out,cachedFailure=false) {
  const b=await openBrowser(base,out,cachedFailure?'module-evaluation':'context');
  try {
    await b.send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
    await b.send('Page.navigate',{url:base+'/#compare'});
    assert.ok(await b.until(()=>document.body.dataset.loadState==='ready'),'Retry workbench unavailable');
    if(!cachedFailure) assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready'));
    const before=await b.evaluate(()=>{
      const e=document.getElementById('draft-source');e.value+='\n# S29 retry draft\n';e.dispatchEvent(new Event('input',{bubbles:true}));e.focus();e.setSelectionRange(7,23,'backward');
      globalThis.__retryEditor=e;return {value:e.value,origin:performance.timeOrigin};
    });
    b.releaseImports();
    if(!cachedFailure) await b.evaluate(()=>document.querySelector('#workplace-canvas canvas').getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
    assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='unavailable'),'Retry precondition did not fail graphics');
    if(cachedFailure) {
      const cached=await b.evaluate(async()=>{
        const button=document.querySelector('[data-graphics-retry]');button.click();globalThis.__s29Host().retry();
        let rejected=false;try {await import('/workplace-scene.js');}catch {rejected=true;}
        return {disabled:button.disabled,explained:document.getElementById('graphics-status').textContent.includes('Graphics installation needs repair.'),rejected,evaluations:globalThis.__s29ModuleEvaluations};
      });
      assert.deepEqual(cached,{disabled:true,explained:true,rejected:true,evaluations:1},'Cached module evaluation failure did not remain unavailable with an explanation');
    } else {
      // Accept a newer publication while failed; retry must use it, not the old baseline.
      await b.evaluate(()=>globalThis.__s29Refresh());
      // The data-loading path disables controls. Reestablish focus before the
      // graphics-only action so its effect is measured separately.
      await b.evaluate(()=>document.getElementById('draft-source').focus({preventScroll:true}));
      const count=b.requests.length;
      await b.evaluate(()=>document.querySelector('[data-graphics-retry]').click());
      assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready'),'Explicit retry did not rebuild graphics');
      assert.ok(await b.evaluate(()=>JSON.stringify(globalThis.__s29Applied)===JSON.stringify(globalThis.__s29Latest().view)),'Retry applied stale public state');
      assert.deepEqual(b.requests.slice(count),[],'Cached graphics retry requested new URLs');
    }
    const after=await b.evaluate(()=>{
      const e=document.getElementById('draft-source');return {same:e===globalThis.__retryEditor,value:e.value,dirty:e.dataset.dirty,focus:e===document.activeElement,start:e.selectionStart,end:e.selectionEnd,direction:e.selectionDirection,origin:performance.timeOrigin};
    });
    await writeFile(path.join(out,'retry.json'),JSON.stringify({cachedFailure,before,after,sceneRequests:b.requests.filter(url=>url.endsWith('/workplace-scene.js'))},null,2)+'\n');
    assert.deepEqual(after,{same:true,value:before.value,dirty:'true',focus:true,start:7,end:23,direction:'backward',origin:before.origin},'Retry changed dirty editor continuity');
    assert.deepEqual(b.commands,[],'Graphics retry submitted a command');assert.deepEqual(b.exceptions,[]);
    return {result:'PASS',cachedFailure};
  } finally {await b.close();}
}

export async function runHostRetry(base,out,cachedFailure=false,omit=false) {
  const mode=cachedFailure?`host-evaluation${omit?'-omit-disable':''}`:`host-retry${omit?'-omit-epoch':''}`;
  const b=await openBrowser(base,out,mode);
  try {
    await b.send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
    await b.send('Page.navigate',{url:base+'/#compare'});
    assert.ok(await b.until(()=>document.body?.dataset.loadState==='ready'),'Host retry workbench unavailable');
    const before=await b.evaluate(()=>{
      const e=document.getElementById('draft-source');e.value+='\n# outer host retry draft\n';e.dispatchEvent(new Event('input',{bubbles:true}));e.focus();e.setSelectionRange(6,18,'backward');
      globalThis.__s29OuterEditor=e;return {value:e.value,origin:performance.timeOrigin};
    });
    b.releaseImports();
    assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='unavailable'),'Host retry failure precondition missing');
    if(cachedFailure) {
      const result=await b.evaluate(async()=>{
        const button=document.querySelector('[data-graphics-retry]');button.click();
        let rejected=false;try{await import('/workplace-host.js');}catch{rejected=true;}
        return {disabled:button.disabled,explained:document.getElementById('graphics-status').textContent.includes('Graphics installation needs repair.'),rejected,evaluations:globalThis.__s29HostEvaluations,attempts:globalThis.__s29InitializeAttempts};
      });
      await writeFile(path.join(out,'host-module.json'),JSON.stringify(result,null,2)+'\n');
      assert.equal(result.disabled,true,'Cached outer module retry remained enabled');
      assert.deepEqual(result,{disabled:true,explained:true,rejected:true,evaluations:1,attempts:1});
    }else{
      await b.evaluate(()=>document.querySelector('[data-graphics-retry]').click());
      assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready'),'Timed-out host retry did not recover');
      const resources=await b.evaluate(()=>({contexts:globalThis.__s29GLs.filter(gl=>!gl.isContextLost()).length,constructions:globalThis.__s29HostConstructions,canvases:document.querySelectorAll('#workplace-canvas canvas').length,applied:JSON.stringify(globalThis.__s29Applied)===JSON.stringify(globalThis.__s29Latest().view)}));
      await writeFile(path.join(out,'host-resources.json'),JSON.stringify(resources,null,2)+'\n');
      assert.equal(resources.contexts,1,'Host retry attached an obsolete import');
      assert.deepEqual(resources,{contexts:1,constructions:1,canvases:1,applied:true});
    }
    const after=await b.evaluate(()=>{const e=document.getElementById('draft-source');return {same:e===globalThis.__s29OuterEditor,value:e.value,dirty:e.dataset.dirty,focus:e===document.activeElement,start:e.selectionStart,end:e.selectionEnd,direction:e.selectionDirection,origin:performance.timeOrigin};});
    await writeFile(path.join(out,'host-retry.json'),JSON.stringify({cachedFailure,after,hostRequests:b.requests.filter(url=>url.endsWith('/workplace-host.js'))},null,2)+'\n');
    assert.deepEqual(after,{same:true,value:before.value,dirty:'true',focus:true,start:6,end:18,direction:'backward',origin:before.origin},'Outer host retry changed editor continuity');
    assert.equal(b.requests.filter(url=>url.endsWith('/workplace-host.js')).length,1,'Outer retry requested a different module URL');
    assert.deepEqual(b.commands,[]);assert.deepEqual(b.exceptions,[]);return {result:'PASS',outerHost:true,cachedFailure};
  }finally{await b.close();}
}

export async function runZoom(base,out,fault='') {
  assert.ok(['','zoom-omit-picker','zoom-omit-station-column','zoom-omit-navigation'].includes(fault),'Unknown zoom fault');
  const rows=[];
  for(const width of fault?[390]:[1280,640,390]) {
    const b=await openBrowser(base,path.join(out,String(width)),fault||'plain',{zoom:2,windowWidth:width,windowHeight:900});
    b.releaseImports();
    try {
      // Chrome clamps native windows below 500px. Override viewport dimensions,
      // retaining the native profile zoom and the display's actual scale factor.
      await b.send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:0,mobile:false});
      await b.send('Page.navigate',{url:base+'/#customers'});
      assert.ok(await b.until(()=>document.body?.dataset.loadState==='ready'),'Zoomed workbench unavailable');
      const metrics=await b.evaluate(()=>({inner:innerWidth,outer:outerWidth,dpr:devicePixelRatio,pinch:visualViewport.scale,scroll:document.documentElement.scrollWidth,bodyZoom:getComputedStyle(document.body).zoom}));
      assert.ok(Math.abs(metrics.dpr-2)<.01 && Math.abs(metrics.inner-width/2)<=2 && metrics.pinch===1 && metrics.bodyZoom==='1','Native 200% browser zoom was not established');
      await writeFile(path.join(out,String(width),'metrics.json'),JSON.stringify(metrics,null,2)+'\n');
      assert.ok(metrics.scroll<=metrics.inner,'200% zoom causes horizontal page scrolling');
      assert.ok(await b.evaluate(()=>[...document.querySelectorAll('.journey:not([hidden]) a')].every(link=>{
        const box=link.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(link);
        return [...range.getClientRects()].every(r=>!r.width || r.left>=box.left-.5 && r.right<=box.right+.5);
      })),'200% zoom navigation labels escape their controls');
      const top=await b.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
      await writeFile(path.join(out,String(width),'zoom-top.png'),Buffer.from(top.data,'base64'));
      for(const station of ['customers','evaluator','compare']) {
        const control=await b.evaluate(station=>{
          const e=document.querySelector(`#bookshop-stations [data-station="${station}"]`);e.scrollIntoView({block:'center',behavior:'instant'});e.focus();const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,width:r.width,height:r.height};
        },station);
        assert.ok(control.width>=44 && control.height>=44,'Zoomed station control is below 44 CSS pixels');
        await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r',unmodifiedText:'\r'});
        await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
        const reached=await b.until(async station=>{
          const p=document.getElementById('station-panel'),r=p.getBoundingClientRect();
          await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
          return document.querySelector(`#bookshop-stations [data-station="${station}"]`).getAttribute('aria-pressed')==='true' && document.activeElement===p && r.top>=0 && r.top<innerHeight && Math.abs(p.getBoundingClientRect().top-r.top)<.1;
        },3000,station);
        const reach=await b.evaluate(station=>({station,pressed:document.querySelector(`#bookshop-stations [data-station="${station}"]`).getAttribute('aria-pressed'),active:document.activeElement?.id,panel:document.getElementById('station-panel').getBoundingClientRect().toJSON(),scroll:scrollY,height:innerHeight,graphics:document.getElementById('graphics-status').dataset.state}),station);
        await writeFile(path.join(out,String(width),station+'-keyboard.json'),JSON.stringify(reach,null,2)+'\n');
        assert.ok(reached,`Zoomed keyboard station ${station} at ${width}px did not reach and focus its panel`);
        // CDP coordinates are viewport CSS pixels after the native browser zoom.
        const point=await b.evaluate(async station=>{
          const e=document.querySelector(`#bookshop-stations [data-station="${station}"]`);e.scrollIntoView({block:'center',behavior:'instant'});e.focus();
          await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
          const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};
        },station);
        await b.send('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:1});
        await b.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[point]});
        await b.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
        assert.ok(await b.until(()=>document.activeElement===document.getElementById('station-panel'),3000),`Zoomed touch station ${station} at ${width}px did not focus the panel`);
        assert.ok(await b.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Zoomed ${station} panel causes horizontal page scrolling`);
      }
      await b.evaluate(()=>{const e=document.getElementById('draft-source');e.value+='\n# zoom draft\n';e.dispatchEvent(new Event('input',{bubbles:true}));e.focus();e.setSelectionRange(4,12);});
      await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
      await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
      assert.ok(await b.evaluate(()=>{const e=document.getElementById('draft-source');return e===document.activeElement && e.selectionStart===4 && e.selectionEnd===12 && e.value.endsWith('# zoom draft\n');}),'Native editor Escape changed zoomed draft continuity');
      const screenshot=await b.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
      await writeFile(path.join(out,String(width),'zoom.png'),Buffer.from(screenshot.data,'base64'));
      const editorShot=await b.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
      await writeFile(path.join(out,String(width),'zoom-editor.png'),Buffer.from(editorShot.data,'base64'));
      assert.deepEqual(b.commands,[],'Zoom navigation submitted commands');assert.deepEqual(b.exceptions,[]);
      rows.push({viewportWidthBeforeZoom:width,viewportEmulated:true,...metrics});
    } finally {await b.close();}
  }
  await writeFile(path.join(out,'zoom.json'),JSON.stringify(rows,null,2)+'\n');return rows;
}

export async function runExactViewports(base,out,fault='') {
  assert.ok(['','zoom-omit-picker','zoom-omit-station-column','zoom-omit-navigation'].includes(fault),'Unknown exact-viewport fault');
  const cells=fault?[[390,844,2]]:[[640,900,1],[640,900,2],[390,844,1],[390,844,2]],rows=[];
  for(const [width,height,zoom] of cells) {
    const name=`${width}x${height}-zoom${zoom}`;
    const b=await openBrowser(base,path.join(out,name),fault||'plain',{zoom,windowWidth:width,windowHeight:height});
    b.releaseImports();
    try {
      // Mobile emulation resets native page zoom; these are desktop viewport resizes.
      await b.send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:zoom===1?1:0,mobile:false});
      await b.send('Page.navigate',{url:base+'/#customers'});
      assert.ok(await b.until(()=>document.body?.dataset.loadState==='ready'),'Exact viewport workbench unavailable');
      const metrics=await b.evaluate(()=>({innerWidth,innerHeight,dpr:devicePixelRatio,pinch:visualViewport.scale,scroll:document.documentElement.scrollWidth,bodyZoom:getComputedStyle(document.body).zoom}));
      assert.ok(Math.abs(metrics.innerWidth-width/zoom)<=2,'Viewport width was not established');
      assert.ok(Math.abs(metrics.innerHeight-height/zoom)<=2,'Viewport height was not established');
      assert.ok(Math.abs(metrics.dpr-zoom)<.01 && metrics.pinch===1 && metrics.bodyZoom==='1','Native browser zoom was not established');
      await writeFile(path.join(out,name,'metrics.json'),JSON.stringify({target:{width,height,zoom},...metrics},null,2)+'\n');
      assert.ok(metrics.scroll<=metrics.innerWidth,'Exact viewport causes horizontal page scrolling');
      assert.ok(await b.evaluate(()=>[...document.querySelectorAll('.journey:not([hidden]) a')].every(link=>{
        const box=link.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(link);
        return [...range.getClientRects()].every(r=>!r.width || r.left>=box.left-.5 && r.right<=box.right+.5);
      })),'Exact viewport navigation labels escape their controls');
      await b.evaluate(()=>document.getElementById('workplace-canvas').scrollIntoView({block:'center',behavior:'instant'}));
      assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready',12000),'Exact viewport real 3D room did not become ready');
      assert.ok(await b.evaluate(()=>!!document.querySelector('#workplace-canvas canvas')?.getContext('webgl2')),'Exact viewport actual WebGL2 context missing');
      for(const station of ['customers','evaluator','compare']) {
        const control=await b.evaluate(station=>{
          const e=document.querySelector(`#bookshop-stations [data-station="${station}"]`);e.scrollIntoView({block:'center',behavior:'instant'});e.focus();const r=e.getBoundingClientRect();return {width:r.width,height:r.height};
        },station);
        assert.ok(control.width>=44 && control.height>=44,'Exact viewport station control is below 44 CSS pixels');
        await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r',unmodifiedText:'\r'});
        await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
        assert.ok(await b.until(station=>document.querySelector(`#bookshop-stations [data-station="${station}"]`).getAttribute('aria-pressed')==='true' && document.activeElement===document.getElementById('station-panel'),3000,station),`Exact viewport keyboard station ${station} did not focus its panel`);
        await b.send('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:1});
        const point=await b.evaluate(async station=>{
          const e=document.querySelector(`#bookshop-stations [data-station="${station}"]`);
          let last=-1,stable=0,settled=false;
          for(let i=0;i<180;i++){
            await new Promise(resolve=>requestAnimationFrame(resolve));
            if(scrollY===last){if(++stable>=3){settled=true;break;}}else{stable=0;last=scrollY;}
          }
          e.scrollIntoView({block:'center',behavior:'instant'});
          await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
          document.activeElement?.blur();
          const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;
          return {x,y,settled,hitStation:document.elementFromPoint(x,y)?.closest('[data-station]')?.dataset.station??null};
        },station);
        assert.ok(point.settled,`Exact viewport scroll did not settle before ${station} touch`);
        assert.equal(point.hitStation,station,`Exact viewport touch point for ${station} is covered by another element`);
        await b.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:point.x,y:point.y}]});
        await b.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
        assert.ok(await b.until(()=>document.activeElement===document.getElementById('station-panel'),3000),`Exact viewport touch station ${station} did not focus the panel`);
        assert.ok(await b.until(station=>document.querySelector(`#bookshop-stations [data-station="${station}"]`).getAttribute('aria-pressed')==='true',2000,station),`Exact viewport touch station ${station} did not activate`);
        assert.ok(await b.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Exact viewport ${station} panel causes horizontal page scrolling`);
      }
      await b.evaluate(()=>{const e=document.getElementById('draft-source');e.value+='\n# exact viewport draft\n';e.dispatchEvent(new Event('input',{bubbles:true}));e.focus();e.setSelectionRange(4,12);});
      await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
      await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
      assert.ok(await b.evaluate(()=>{const e=document.getElementById('draft-source');return e===document.activeElement && e.selectionStart===4 && e.selectionEnd===12 && e.value.endsWith('# exact viewport draft\n');}),'Exact viewport editor Escape changed draft continuity');
      assert.deepEqual(b.commands,[],'Exact viewport navigation submitted commands');assert.deepEqual(b.exceptions,[],'Exact viewport raised an uncaught exception');
      const {data}=await b.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
      await writeFile(path.join(out,name,'exact-viewport.png'),Buffer.from(data,'base64'));
      rows.push({target:{width,height,zoom},...metrics});
    } finally {await b.close();}
  }
  await writeFile(path.join(out,'exact-viewports.json'),JSON.stringify(rows,null,2)+'\n');return rows;
}

export async function runBrowser(base,out,fault = '',empty = false) {
  const b = await openBrowser(base,out,fault);
  const report = {fault,views:[]};
  try {
    for(const width of fault ? [390] : [1280,640,390]) {
      await b.send('Emulation.setDeviceMetricsOverride',{width,height:844,deviceScaleFactor:1,mobile:width<761});
      await b.send('Page.navigate',{url:base+'/#board'});
      assert.ok(await b.until(()=>['ready','empty'].includes(document.body?.dataset.loadState)), 'Complete workbench did not start');
      if(fault) {
        if(fault === 'context') assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready'));
        const draft=await b.evaluate(()=>{
          document.querySelector('[data-station="compare"]').click();
          const editor=document.getElementById('draft-source'); globalThis.__s29Editor=editor;
          editor.value+='\n# S29 disposable offline check\n'; editor.dispatchEvent(new Event('input',{bubbles:true}));
          editor.focus({preventScroll:true}); editor.setSelectionRange(3,11);
          document.getElementById('workplace-canvas').scrollIntoView({block:'center',behavior:'instant'});
          if(document.activeElement!==editor) throw new Error('Dirty editor was not focused before the graphics fault');
          return editor.value;
        });
        b.releaseImports();
        if(fault==='context') await b.evaluate(()=>document.querySelector('#workplace-canvas canvas').getContext('webgl2').getExtension('WEBGL_lose_context').loseContext());
        assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state === 'unavailable'), `Graphics failure ${fault} did not reach fallback`);
        assert.deepEqual(await b.evaluate(()=>{const e=document.getElementById('draft-source');return {same:e===globalThis.__s29Editor,focus:e===document.activeElement,start:e.selectionStart,end:e.selectionEnd,value:e.value};}),{same:true,focus:true,start:3,end:11,value:draft},'Graphics failure changed dirty editor, focus or caret');
        await b.evaluate(()=>document.getElementById('save-draft').click());
        assert.ok(await b.until(()=>document.getElementById('draft-source').dataset.dirty==='false' && document.body.dataset.loadState==='ready'),'Valid recorded offline save failed through graphics fallback');
        assert.equal(await b.evaluate(()=>document.getElementById('graphics-status').dataset.state),'unavailable','Data refresh automatically recreated failed graphics');
      }
      else {
        assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state === 'ready'), 'Real WebGL2 room did not become ready');
        assert.ok(await b.evaluate(()=>!!document.querySelector('#workplace-canvas canvas')?.getContext('webgl2')), 'Actual WebGL2 context missing');
        assert.ok(await b.evaluate(()=>globalThis.__workplaceProbe?.triangles > 100), 'No real geometry was drawn');
        for(const [station,title] of [['customers','Customer evidence'],['evaluator','Independent evaluator']]) {
          await b.evaluate(()=>document.getElementById('workplace-canvas').scrollIntoView({block:'center',behavior:'instant'}));
          const point=await b.evaluate(station=>globalThis.__workplaceStationPoint(station),station);
          const count=b.commands.length;
          await b.send('Input.dispatchMouseEvent',{type:'mousePressed',...point,button:'left',clickCount:1});
          await b.send('Input.dispatchMouseEvent',{type:'mouseReleased',...point,button:'left',clickCount:1});
          assert.equal(await b.evaluate(()=>document.getElementById('panel-title').textContent),title,'Native canvas pick opened the wrong panel');
          assert.equal(b.commands.length,count,'Canvas pick submitted a command');
        }
      }
      if(!empty) {
        await b.evaluate(()=>document.querySelector('.incident-row')?.click());
        assert.ok(await b.until(()=>document.body.dataset.loadState==='ready' && document.getElementById('selected-evidence')?.dataset.runId==='run-0001'),'Recorded failure inspection did not load');
        if(fault) assert.equal(await b.evaluate(()=>document.getElementById('graphics-status').dataset.state),'unavailable','History reset hid a latched graphics failure');
      } else {
        assert.equal(await b.evaluate(()=>document.body.dataset.loadState),'empty','First-shift state is not empty');
        assert.ok(await b.evaluate(()=>document.getElementById('workplace-state').textContent.includes('None selected') && document.getElementById('workplace-state').textContent.includes('No run loaded.')),'Empty scene invented a choice or run');
      }
      const before = b.commands.length;
      await b.evaluate(()=>document.querySelector('[data-station="customers"]').click());
      assert.equal(await b.evaluate(()=>document.getElementById('customer-view').hidden),false,'Intake navigation did not open captured evidence');
      assert.equal(b.commands.length,before,'Station navigation issued a command');
      const run = await b.evaluate(()=>({id:document.getElementById('selected-evidence').dataset.runId}));
      if(run.id) {
        const literal = await b.evaluate(async id => {
          const outputs = await(await fetch(`/api/runs/${id}/outputs`)).json();
          const checks = await(await fetch(`/api/runs/${id}/checks`)).json();
          return {answer:outputs[0]?.customer_answer?.display_text, failed:checks.some(c=>c.verdict==='fail')};
        },run.id);
        assert.equal(literal.failed,true,'Recorded fixture must contain a failed independent task');
        if(literal.answer) assert.ok(await b.evaluate(value=>document.getElementById('selected-evidence').textContent.includes(value),literal.answer),'Captured answer differs from API');
      }
      const geometry=await b.evaluate(()=>({width:innerWidth,document:document.documentElement.scrollWidth,notice:document.getElementById('runtime-notice').getBoundingClientRect().width,main:document.querySelector('main').getBoundingClientRect().width}));
      assert.ok(geometry.document<=width,'Page overflows horizontally');
      assert.equal(geometry.notice,geometry.main,'Hosting notice does not span both columns');
      assert.ok(await b.evaluate(()=>document.getElementById('workplace-state').getBoundingClientRect().top < document.getElementById('workplace-canvas').getBoundingClientRect().top),'Operating identity is below the optional room');
      const {data}=await b.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
      await writeFile(path.join(out,`${width}.png`),Buffer.from(data,'base64'));
      report.views.push({width,geometry,graphics:await b.evaluate(()=>globalThis.__workplaceProbe ?? null)});
    }
    assert.deepEqual(b.exceptions,[],'Uncaught client exceptions');
    assert.deepEqual(b.requests.filter(url=>!url.startsWith(base)&&!url.startsWith('data:')),[],'Client requested external assets');
    await writeFile(path.join(out,'browser.json'),JSON.stringify(report,null,2)+'\n');
    return report;
  } finally { await b.close(); }
}
export async function runLifecycle(base,out,fault='') {
  const b=await openBrowser(base,out,fault);const rows=[];
  try {
    await b.send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
    await b.send('Page.navigate',{url:base+'/'});assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready'));
    const continuity=await b.evaluate(async()=>{
      const canvas=document.querySelector('#workplace-canvas canvas'), original=fetch;let release;
      window.fetch=async(...args)=>{if(String(args[0]).endsWith('/ledger')) await new Promise(r=>release=r);return original(...args);};
      const refreshed=globalThis.__s29Refresh();while(!release) await new Promise(r=>setTimeout(r,10));
      const loading={same:document.querySelector('#workplace-canvas canvas')===canvas,status:document.getElementById('graphics-status').textContent,blocked:document.getElementById('run-shift').disabled};
      release();await refreshed;window.fetch=original;return {loading,same:document.querySelector('#workplace-canvas canvas')===canvas,uncovered:getComputedStyle(document.querySelector('img.room-art')).display==='none'};
    });
    assert.deepEqual(continuity,{loading:{same:true,status:'Refreshing recorded state',blocked:true},same:true,uncovered:true},'Ordinary refresh replaced or covered the retained scene');rows.push('loading continuity and uncovered geometry');
    const error=await b.evaluate(async()=>{const original=fetch;window.fetch=()=>Promise.reject(Error('injected read failure'));await globalThis.__s29Refresh();window.fetch=original;return document.querySelectorAll('#workplace-canvas canvas').length;});assert.equal(error,0);rows.push('error resets graphics');
    await b.evaluate(()=>globalThis.__s29Refresh());assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready'));
    await b.evaluate(()=>document.getElementById('workplace-canvas').scrollIntoView({block:'center',behavior:'instant'}));
    const expanded=await b.evaluate(async()=>{await new Promise(r=>setTimeout(r,100));globalThis.__s29Host().setExpanded(true);const n=globalThis.__workplaceProbe.frames;globalThis.__workplaceApply('customers');await new Promise(r=>setTimeout(r,150));return globalThis.__workplaceProbe.frames-n;});assert.equal(expanded,0);rows.push('expanded drawing stops');
    await b.evaluate(()=>globalThis.__s29Host().setExpanded(false));
    const hidden=await b.evaluate(async()=>{
      Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'));
      const n=globalThis.__workplaceProbe.frames;globalThis.__workplaceApply('evaluator');await new Promise(r=>setTimeout(r,150));const frames=globalThis.__workplaceProbe.frames-n;
      delete document.hidden;document.dispatchEvent(new Event('visibilitychange'));return frames;
    });assert.equal(hidden,0,'Synthetic hidden event allowed graphics frames');rows.push('synthetic hidden event stops drawing');
    await b.send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
    const offscreen=await b.evaluate(async()=>{
      window.scrollTo(0,document.documentElement.scrollHeight);await new Promise(r=>setTimeout(r,200));const n=globalThis.__workplaceProbe.frames;
      const rect=document.getElementById('workplace-canvas').getBoundingClientRect();
      globalThis.__workplaceApply('customers');await new Promise(r=>setTimeout(r,150));const frames=globalThis.__workplaceProbe.frames-n;window.scrollTo(0,0);return {frames,offscreen:rect.bottom<=0 || rect.top>=innerHeight};
    });assert.equal(offscreen.offscreen,true,'Offscreen precondition was not established');assert.equal(offscreen.frames,0,'Offscreen room allowed graphics frames');rows.push('observed offscreen drawing stops');
    await b.send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
    const resources=[];
    await b.evaluate(()=>{globalThis.__s29ResourceFaultActive=true;});
    for(let n=0;n<30;n++) {
      const slug=n%2?'bookshop':'gtm';
      await b.evaluate(slug=>{window.scrollTo(0,0);const s=document.getElementById('workplace-board');s.value=slug;s.dispatchEvent(new Event('change'));},slug);
      assert.ok(await b.until(()=>['ready','empty'].includes(document.body.dataset.loadState)));
      if(slug==='bookshop') assert.ok(await b.until(()=>document.getElementById('graphics-status').dataset.state==='ready'));
      const r=await b.evaluate(()=>globalThis.__s29Resources);assert.ok(r.contexts<=1,'Multiple active contexts');
      if(slug==='gtm') {
        assert.equal(r.geometries,0,'Old room geometry remains');
        assert.equal(r.materials,0,'Old room material remains');
        assert.ok(await b.evaluate(()=>globalThis.__s29GLs.every(gl=>gl.isContextLost())),'Old room context remains live');
        assert.equal(r.contexts,0,'Old room context count remains');
      }
      resources.push(r);
    }
    assert.deepEqual(resources.at(-1),resources[1],'Warm resources grew across board switches');rows.push('thirty switches release old resources');
    const cleanup=await b.evaluate(()=>{const host=globalThis.__s29Host();host.dispose();host.dispose();return {resources:globalThis.__s29Resources,canvas:document.querySelectorAll('#workplace-canvas canvas').length};});
    assert.deepEqual(cleanup,{resources:{contexts:0,geometries:0,materials:0},canvas:0},'Double disposal leaked owned resources');rows.push('idempotent full resource teardown');
    assert.deepEqual(b.exceptions,[]);await writeFile(path.join(out,'lifecycle.json'),JSON.stringify({checks:rows,resources},null,2)+'\n');return rows;
  }finally{await b.close();}
}
export async function runContrast(base,out) {
  const b=await openBrowser(base,out);
  try {
    await b.send('Emulation.setDeviceMetricsOverride',{width:1280,height:720,deviceScaleFactor:1,mobile:false});
    await b.send('Page.navigate',{url:base+'/'});assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready'));
    await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
    await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
    const rows=await b.evaluate(()=>{
      const rgba=s=>{const a=s.match(/[\d.]+/g).map(Number);return [...a.slice(0,3),a[3]??1];};
      const blend=(a,b)=>a.slice(0,3).map((v,n)=>v*a[3]+b[n]*(1-a[3]));
      const lum=a=>a.map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,n)=>s+v*[.2126,.7152,.0722][n],0);
      const ratio=(a,b)=>{const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
      const bg=e=>{const nodes=[];for(let p=e;p;p=p.parentElement)nodes.unshift(p);return nodes.reduce((c,p)=>blend(rgba(getComputedStyle(p).backgroundColor),c),[255,255,255]);};
      return [...document.querySelectorAll('#graphics-status,#workplace-state,#bookshop-stations .station:not([aria-disabled="true"]),[data-graphics-simple]')].map(e=>{
        e.focus({preventScroll:true});const c=getComputedStyle(e),background=bg(e),control=e.tagName==='BUTTON';
        return {element:e.id||e.dataset.station||'simpler-3d',text:ratio(blend(rgba(c.color),background),background),border:control?ratio(blend(rgba(c.borderTopColor),background),background):null,focus:control?ratio(blend(rgba(c.outlineColor),background),background):null};
      });
    });
    await writeFile(path.join(out,'contrast.json'),JSON.stringify(rows,null,2)+'\n');
    assert.deepEqual(rows.filter(r=>r.text<4.5 || r.border!==null&&r.border<3 || r.focus!==null&&r.focus<3),[],'Rendered control contrast is below its approved threshold');
    return rows;
  }finally{await b.close();}
}
export async function runLatency(base,out) {
  const b=await openBrowser(base,out),rows=[];
  try {
    for(const width of [1280,390]) {
      await b.send('Emulation.setDeviceMetricsOverride',{width,height:width===1280?720:844,deviceScaleFactor:1,mobile:false});
      const origin=await b.evaluate(()=>performance.timeOrigin);
      await b.send('Page.navigate',{url:base+`/?latency=${width}`});
      assert.ok(await b.until(old=>performance.timeOrigin!==old && document.getElementById('graphics-status')?.dataset.state==='ready',12000,origin));
      const boot=await b.evaluate(()=>globalThis.__s29BootMs);assert.ok(boot<=50,'Total synchronous DOM startup exceeds the additional-work budget');
      const samples=[];
      for(let n=0;n<30;n++) samples.push(await b.evaluate(station=>new Promise(resolve=>{
        const button=document.querySelector(`[data-station="${station}"]`);
        button.addEventListener('click',()=>{const start=performance.now();requestAnimationFrame(()=>requestAnimationFrame(()=>resolve(performance.now()-start)));},{once:true,capture:true});button.click();
      }),n%2?'customers':'evaluator'));
      const sorted=[...samples].sort((a,b)=>a-b),p95=sorted[Math.ceil(samples.length*.95)-1];
      assert.ok(p95<=100,'Station activation to painted panel exceeds 100ms');rows.push({width,totalSynchronousDomStartupMs:boot,stationPaintUpperBoundMs:samples,p95});
    }
    assert.deepEqual(b.commands,[],'Latency navigation submitted commands');await writeFile(path.join(out,'latency.json'),JSON.stringify(rows,null,2)+'\n');return rows.map(r=>({width:r.width,bootMs:r.totalSynchronousDomStartupMs,p95:r.p95}));
  }finally{await b.close();}
}
if(process.argv[1] === fileURLToPath(import.meta.url)) console.log(JSON.stringify(process.argv.includes('--page-cache') ? await runPageCache(process.argv[2],process.argv[3]) : process.argv.includes('--latency') ? await runLatency(process.argv[2],process.argv[3]) : process.argv.includes('--contrast') ? await runContrast(process.argv[2],process.argv[3]) : process.argv.includes('--lifecycle') ? await runLifecycle(process.argv[2],process.argv[3],process.argv.find(x=>x.startsWith('omit-'))??'') : process.argv.includes('--exact-viewports') ? await runExactViewports(process.argv[2],process.argv[3],process.argv.find(x=>x.startsWith('zoom-omit-'))??'') : await runBrowser(process.argv[2],process.argv[3],process.argv[4]==='--empty'?'':process.argv[4],process.argv.includes('--empty'))));
