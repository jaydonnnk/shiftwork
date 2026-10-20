import assert from 'node:assert/strict';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {repoRoot} from './env.mjs';
import {runMarker,runMarkerGuards,runMarkerOverlap,runFailedRefresh} from './workplace_s34.mjs';

const [base,out]=process.argv.slice(2);
await mkdir(out,{recursive:true});
const files=['app.js','styles.css','workplace-scene.js'];
const digest=async file=>createHash('sha256').update(await readFile(path.join(repoRoot,'shiftwork/client',file))).digest('hex');
const before=await Promise.all(files.map(digest));
const rows=[
  ['s34-marker-omit-travel',runMarker,'Signal-bound owner marker did not travel'],
  ['s34-marker-omit-label',runMarker,'Routing marker lacks the exact synthetic signal and owner label'],
  ...[['reference','reference'],['type','type'],['signal','signal'],['owner','owner'],['unique','duplicate'],['current-link','historical-link'],['source','source'],['synthetic','synthetic']].map(([fault,guard])=>[`s34-marker-omit-${fault}`,runMarkerGuards,`Owner marker ignored ${guard} guard`]),
  ['s34-marker-omit-link',runMarkerGuards,'link marker label was admitted'],
  ['s34-marker-omit-label-dispose',runMarkerGuards,'Disposed scene retained an ownership label'],
  ['s34-marker-omit-overlap-settle',runMarkerOverlap,'A newer owner label inherited another signal travel'],
  ['s34-failed-refresh-omit-reset',runFailedRefresh,'Failed refresh retained a stale ownership claim'],
];
const results=[];
for(const [fault,run,expected] of rows) {
  for(const phase of ['clean','fault','restored']) {
    const folder=path.join(out,fault,phase);
    let error=null;
    try {await run(base,folder,phase==='fault'?fault:undefined);} catch(caught) {error=caught;}
    await writeFile(folder+'.log',error?.stack??'PASS\n');
    if(phase==='fault') {assert.equal(error?.code,'ERR_ASSERTION',`${fault} did not fail an assertion: ${error?.stack}`);assert.ok(error.message.includes(expected),`${fault} hit the wrong assertion: ${error.message}`);}
    else assert.equal(error,null,`${fault} ${phase}: ${error?.stack}`);
    results.push({fault,phase,result:error?'named assertion caught':'PASS'});
  }
  console.log(`${fault}: clean, caught, restored`);
}
assert.deepEqual(await Promise.all(files.map(digest)),before,'Served faults modified production');
await writeFile(path.join(out,'results.json'),JSON.stringify({results,production:'byte-identical'},null,2)+'\n');
