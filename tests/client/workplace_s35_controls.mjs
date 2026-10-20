import assert from 'node:assert/strict';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {repoRoot} from './env.mjs';
import {runWorkshop} from './workplace_s35.mjs';
import {runResourceControl} from './workplace_browser.mjs';

const [base,out]=process.argv.slice(2);
await mkdir(out,{recursive:true});
const files=['app.js','index.html','styles.css','workplace-scene.js'];
const digest=async file=>createHash('sha256').update(await readFile(path.join(repoRoot,'shiftwork/client',file))).digest('hex');
const before=await Promise.all(files.map(digest)),rows=[];
const cases=[];
for(const kind of ['BOOKING_COMMITTED','ROLLOUT_APPROVED','HANDOVER_DECLARED','ESCALATION_TO_HUMAN','COUNTER_FOLLOWUP_RECORDED']) {
  for(const guard of ['type','synthetic','synthetic-type','link','conflict','aggregate',...(kind==='HANDOVER_DECLARED'?['source','version']:[])]) {
    const expected=guard==='type' && kind!=='HANDOVER_DECLARED'?`changed the wrong ${kind} marker`:guard==='aggregate'?`${kind} lost its aggregate record count`:`${kind} ignored renderer ${guard} guard`;
    cases.push([`s35-marker-${kind}--${guard}`,runWorkshop,expected]);
  }
}
cases.push(['s35-label-map',runWorkshop,'Map does not explain declared permissions'],
  ['s35-label-handover',runWorkshop,'Handover does not explain declaration limits'],
  ['s35-omit-wheel-dispose',(base,out,fault)=>runResourceControl(base,out,fault??'s35-resources',false,'northline'),'Resource control leaked scene resources']);
for(const [fault,run,expected] of cases) {
  for(const phase of ['clean','fault','restored']) {
    const folder=path.join(out,fault,phase);let error=null;
    try{await run(base,folder,phase==='fault'?fault:undefined);}catch(caught){error=caught;}
    await writeFile(folder+'.log',error?.stack??'PASS\n');
    if(phase==='fault') {
      assert.equal(error?.code,'ERR_ASSERTION',`${fault} did not fail an assertion: ${error?.stack}`);
      assert.ok(error.message.includes(expected),`${fault} hit the wrong assertion: ${error.message}`);
    } else assert.equal(error,null,`${fault} ${phase}: ${error?.stack}`);
    rows.push({fault,phase,result:error?'named assertion caught':'PASS'});
    await writeFile(path.join(out,'results.json'),JSON.stringify({rows},null,2)+'\n');
  }
  console.log(`${fault}: clean, caught, restored`);
}
assert.deepEqual(await Promise.all(files.map(digest)),before,'Served faults modified production');
await writeFile(path.join(out,'results.json'),JSON.stringify({rows,production:'byte-identical'},null,2)+'\n');
