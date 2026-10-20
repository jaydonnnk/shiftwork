import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {openBrowser} from './workplace_browser.mjs';

export async function runWorkshop(base,out,fault='s35-workshop') {
  const b=await openBrowser(base,out,fault);
  try {
    await b.send('Page.navigate',{url:base+'/?board=northline#brief'});
    assert.ok(await b.until(()=>['ready','empty'].includes(document.body?.dataset.loadState)),'Northline workbench unavailable');
    await b.evaluate(()=>document.getElementById('workplace-canvas').scrollIntoView({block:'center',behavior:'instant'}));
    assert.ok(await b.until(()=>document.getElementById('graphics-status')?.dataset.state==='ready'),'Northline graphics did not mount');
    const room=await b.evaluate(()=>globalThis.__s35Room());
    assert.equal(room.wheels,2,'The rendered workshop has no bicycle wheels');
    const types=['BOOKING_COMMITTED','ROLLOUT_APPROVED','HANDOVER_DECLARED','ESCALATION_TO_HUMAN','COUNTER_FOLLOWUP_RECORDED'];
    assert.deepEqual(Object.keys(room.markers).sort(),[...types].sort(),'Northline recorded markers are missing');
    const rows=await b.evaluate(types=>{
      const view=structuredClone(globalThis.__s29Latest().view),rows=[];
      for(const type of types) {
        const event={id:'northline:test:'+type,type,synthetic:true,source:type==='HANDOVER_DECLARED'?'administrative':'current',
          linkState:type==='HANDOVER_DECLARED'?'none':'linked',versionId:type==='HANDOVER_DECLARED'?'runbook-version':null};
        globalThis.__s35Apply({...view,consistency:'linked',consequences:{...view.consequences,events:[event]}},[]);
        rows.push({type,markers:globalThis.__s35Room().markers});
      }
      return rows;
    },types);
    for(const row of rows) for(const type of types) assert.equal(row.markers[type].visible,type===row.type,`${row.type} changed the wrong ${type} marker`);
    const guards=await b.evaluate(types=>{
      const view=structuredClone(globalThis.__s29Latest().view),rows=[];
      for(const type of types) {
        const event={id:'northline:guard:'+type,type,synthetic:true,source:type==='HANDOVER_DECLARED'?'administrative':'current',linkState:type==='HANDOVER_DECLARED'?'none':'linked',versionId:type==='HANDOVER_DECLARED'?'runbook-version':null};
        const cases=[['synthetic',{synthetic:false}],['synthetic-type',{synthetic:'true'}],['type',{type:'UNKNOWN_EVENT'}],['link',{linkState:'incomplete'}]];
        if(type==='HANDOVER_DECLARED') cases.push(['source',{source:'historical'}],['version',{versionId:null}]);
        for(const [guard,change] of cases) {
          globalThis.__s35Apply({...view,consistency:'linked',consequences:{...view.consequences,events:[{...event,...change}]}},[]);
          rows.push({type,guard,visible:globalThis.__s35Room().markers[type].visible});
        }
        globalThis.__s35Apply({...view,consistency:'conflict',consequences:{...view.consequences,events:[event]}},[]);
        rows.push({type,guard:'conflict',visible:globalThis.__s35Room().markers[type].visible});
        globalThis.__s35Apply({...view,consistency:'linked',consequences:{...view.consequences,events:[event,{...event,id:event.id+':second'}]}},[]);
        rows.push({type,guard:'aggregate',count:globalThis.__s35Room().markers[type].count});
      }
      return rows;
    },types);
    for(const row of guards) {
      if(row.guard==='aggregate') assert.equal(row.count,2,`${row.type} lost its aggregate record count`);
      else assert.equal(row.visible,false,`${row.type} ignored renderer ${row.guard} guard`);
    }
    await b.evaluate(()=>document.querySelector('#northline-stations [data-station="map"]').click());
    assert.match(await b.evaluate(()=>document.getElementById('map-view').textContent),/cannot grant.*permission/i,'Map does not explain declared permissions');
    await b.evaluate(()=>document.querySelector('#northline-stations [data-station="handover"]').click());
    assert.match(await b.evaluate(()=>document.getElementById('handover-record').textContent),/does not prove.*received.*read.*accepted/i,'Handover does not explain declaration limits');
    const {data}=await b.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
    await writeFile(path.join(out,'workshop.png'),Buffer.from(data,'base64'));
    assert.deepEqual(b.commands,[],'Workshop inspection issued a command');assert.deepEqual(b.exceptions,[]);
    await writeFile(path.join(out,'workshop.json'),JSON.stringify({room,rows,guards},null,2)+'\n');
    return {result:'PASS',wheels:room.wheels,markers:types.length};
  }finally{await b.close();}
}
export async function runLegacyHistory(base,out) {
  const b=await openBrowser(base,out,'plain');
  try {
    await b.send('Page.navigate',{url:base+'/#next'});
    assert.ok(await b.until(()=>document.body.dataset.loadState==='ready'),'Legacy history workbench unavailable');
    const board=await b.evaluate(async()=> (await fetch('/api/engagements/bookshop/board')).json());
    assert.equal(board.latest_run?.purpose,'LEGACY_OPERATION','Legacy history requires a real recorded legacy operation');
    const history=await b.evaluate(()=>({run:document.getElementById('next-history').dataset.latestRun,text:document.getElementById('next-history').textContent}));
    assert.equal(history.run,board.latest_run.id,'Operational history hid the recorded legacy operation');
    assert.ok(history.text.includes('legacy operation'),'Operational history lost the explicit legacy label');
    assert.deepEqual(b.commands,[]);assert.deepEqual(b.exceptions,[]);
    await writeFile(path.join(out,'legacy-history.json'),JSON.stringify({history,run:board.latest_run},null,2)+'\n');
    return {result:'PASS',legacyRun:board.latest_run.id};
  }finally{await b.close();}
}
export async function runContentReach(base,out,fault='') {
  const rows=[];
  for(const [width,height,zoom] of [[640,900,1],[640,900,2],[390,844,1],[390,844,2]]) {
    const cell=`${width}x${height}-zoom${zoom}`;
    const b=await openBrowser(base,path.join(out,cell),fault||'plain',{zoom,windowWidth:width,windowHeight:height});
    b.releaseImports();
    try {
      await b.send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:zoom===1?1:0,mobile:false});
      await b.send('Page.navigate',{url:base+'/?board=northline#bench'});
      assert.ok(await b.until(()=>document.body?.dataset.loadState==='ready'),'Content reach workbench unavailable');
      const metrics=await b.evaluate(()=>({width:innerWidth,height:innerHeight,dpr:devicePixelRatio,scale:visualViewport.scale,cssZoom:getComputedStyle(document.body).zoom}));
      assert.ok(Math.abs(metrics.width-width/zoom)<=2 && Math.abs(metrics.height-height/zoom)<=2 && Math.abs(metrics.dpr-zoom)<.01 && metrics.scale===1 && metrics.cssZoom==='1','Content reach native viewport/zoom mismatch');
      await b.evaluate(()=>document.getElementById('workplace-canvas').scrollIntoView({block:'center',behavior:'instant'}));
      assert.ok(await b.until(state=>document.getElementById('graphics-status')?.dataset.state===state,12000,fault?'unavailable':'ready'),'Content reach graphics precondition failed');
      await b.evaluate(()=>{
        const e=document.getElementById('draft-source');
        if(e.disabled) throw Error('Content reach needs an enabled draft');
        globalThis.__reachEditor=e;globalThis.__reachDraft=e.value+'\n# unsaved content reach draft\n';
        e.value=globalThis.__reachDraft;e.dispatchEvent(new Event('input',{bubbles:true}));e.setSelectionRange(4,12);
      });
      for(const input of ['keyboard','touch']) for(const [station,selector] of [
        ['acceptance','#selected-evidence .request-quote'],['rollout','#operate-pilot'],['handover','#handover-records [data-deployment-file="runbook.md"]']
      ]) {
        await b.send('Emulation.setTouchEmulationEnabled',{enabled:input==='touch',maxTouchPoints:1});
        const point=await b.evaluate(async station=>{
          const e=document.querySelector(`#northline-stations [data-station="${station}"]`);
          e.scrollIntoView({block:'center',behavior:'instant'});e.focus({preventScroll:true});
          await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
          const r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;
          return {x,y,width:r.width,height:r.height,hit:document.elementFromPoint(x,y)?.closest('[data-station]')?.dataset.station};
        },station);
        assert.ok(point.width>=44 && point.height>=44,'Content reach station target is below 44 CSS pixels');
        assert.equal(point.hit,station,'Content reach station control is covered');
        if(input==='keyboard') {
          await b.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r',unmodifiedText:'\r'});
          await b.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
        } else {
          await b.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:point.x,y:point.y}]});
          await b.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
        }
        const row=await b.evaluate(async (station,selector)=>{
          let last=null,stable=0,settled=false;
          for(let n=0;n<180;n++) {
            await new Promise(resolve=>requestAnimationFrame(resolve));
            const value=[scrollX,scrollY,document.querySelector(selector)?.getBoundingClientRect().top];
            if(JSON.stringify(value)===JSON.stringify(last)) {if(++stable>=6){settled=true;break;}} else {stable=0;last=value;}
          }
          const e=document.querySelector(selector),r=e?.getBoundingClientRect(),editor=document.getElementById('draft-source');
          const visible=!!r && r.width>0 && r.height>0 && r.left>=0 && r.right<=innerWidth+.5 && r.top>=0 && r.top+Math.min(r.height,44)<=innerHeight;
          return {station,selector,settled,visible,text:e?.textContent??'',rect:r?.toJSON(),viewport:{width:innerWidth,height:innerHeight},
            focus:document.activeElement===document.getElementById('station-panel'),active:document.querySelector(`#northline-stations [data-station="${station}"]`).getAttribute('aria-pressed'),
            overflow:document.documentElement.scrollWidth>innerWidth,dirty:editor===globalThis.__reachEditor && editor.value===globalThis.__reachDraft && editor.dataset.dirty==='true' && editor.selectionStart===4 && editor.selectionEnd===12};
        },station,selector);
        rows.push({cell,input,graphics:fault||'ready',metrics,...row});
        await writeFile(path.join(out,'content-reach.json'),JSON.stringify(rows,null,2)+'\n');
        if(!row.visible) {
          const {data}=await b.send('Page.captureScreenshot',{format:'png'});
          await writeFile(path.join(out,cell,`${input}-${station}.png`),Buffer.from(data,'base64'));
        }
      }
      assert.deepEqual(b.commands,[],'Content navigation submitted a command');
      assert.deepEqual(b.exceptions,[],'Content navigation raised a browser exception');
    }finally{await b.close();}
  }
  const failed=rows.filter(r=>!r.settled || !r.visible || !r.text || !r.focus || r.active!=='true' || r.overflow || !r.dirty);
  assert.deepEqual(failed.map(r=>`${r.cell}/${r.input}/${r.station}`),[],'Selected Northline content is not in reach with dirty-editor continuity');
  return {result:'PASS',observations:rows.length};
}
if(process.argv[1]===fileURLToPath(import.meta.url)) {
  const [base,out]=process.argv.slice(2);await mkdir(out,{recursive:true});
  console.log(JSON.stringify(process.argv.includes('--content-reach')?await runContentReach(base,out,process.argv.includes('--webgl')?'webgl':''):await runWorkshop(base,out)));
}
