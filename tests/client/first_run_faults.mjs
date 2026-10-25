// Independent S47 pure faults use owned copies. Production source is never edited.
import assert from 'node:assert/strict';
import {mkdir, mkdtemp, readFile, writeFile, rm} from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import * as cleanStory from '../../shiftwork/client/workplace-story.js';
import * as cleanEvidence from '../../shiftwork/client/evidence.js';
import {runFirstRunBrowser, FIRST_RUN_FAULTS} from './first_run_browser.mjs';
const out = path.resolve(process.argv[2]);
assert.ok(/^\/(?:private\/)?tmp\/shiftwork-s47-[^/]+(?:\/|$)/.test(out));
await mkdir(out, {recursive: true});
const source = Object.fromEntries(await Promise.all(['workplace-story.js', 'evidence.js'].map(async file => [file, await readFile(`shiftwork/client/${file}`, 'utf8')])));
const faults = [
  ...[[1,1],[2,2],[3,2],[4,3],[5,4],[6,4],[7,5]].map(([step,panel]) => ({name:`step-${step}`, file:'workplace-story.js', needle:`${step}: ${panel}`, replacement:`${step}: 9`, check:s => assert.equal(s.firstRunPanel({step}),panel,`step ${step} retains panel ${panel}`)})),
  {name:'noninteger', file:'workplace-story.js', needle:'  if (!Number.isInteger(guide?.step)) return null;\n', replacement:'', check:s => assert.equal(s.firstRunPanel({step:'3'}),null,'string step stays unknown')},
  {name:'unknown-step', file:'workplace-story.js', needle:')[guide?.step] ?? null;', replacement:')[guide?.step] ?? 1;', check:s => assert.equal(s.firstRunPanel({step:8}),null,'unrecognized step stays unknown')},
  ...[['RECORDED_INSPECTION','replayed recording'],['ISOLATED_LIVE','ran live in a sandbox'],['TRUSTED_LOCAL','ran locally with trusted test code']].map(([code,label]) => ({name:code,file:'evidence.js',needle:`case '${code}': return '${label}';`,replacement:`case '${code}': return 'wrong evidence';`,check:(_,e)=>assert.equal(e.evidenceLabel(code),label,`${code} retains its plain label`)})),
  {name:'unknown-mode',file:'evidence.js',needle:"default: return 'evidence unknown';",replacement:"default: return 'replayed recording';",check:(_,e)=>assert.equal(e.evidenceLabel('FUTURE_MODE'),'evidence unknown','unknown mode stays unknown')},
];
const receipts=[];
for(const fault of faults){
  assert.equal(source[fault.file].split(fault.needle).length-1,1,`unique anchor ${fault.name}`);
  fault.check(cleanStory,cleanEvidence);
  const dir=await mkdtemp(path.join(out,'copy-'));
  try{
    for(const [file,body] of Object.entries(source))await writeFile(path.join(dir,file),file===fault.file?body.replace(fault.needle,fault.replacement):body);
    const story=await import(pathToFileURL(path.join(dir,'workplace-story.js')));
    const evidence=await import(pathToFileURL(path.join(dir,'evidence.js')));
    let message=null;
    assert.throws(()=>fault.check(story,evidence),error=>{message=error.message;return error.code==='ERR_ASSERTION';},'the intended behavior must fail');
    await writeFile(path.join(out,fault.name+'.log'),message+'\n');
    fault.check(cleanStory,cleanEvidence);
    for(const [file,body] of Object.entries(source))assert.equal(await readFile(`shiftwork/client/${file}`,'utf8'),body,'source byte-identical');
    receipts.push({name:fault.name,result:'intended assertion caught',restored:'PASS'});
  }finally{await rm(dir,{recursive:true,force:true});}
}
await writeFile(path.join(out,'pure-faults.json'),JSON.stringify(receipts,null,2));
console.log(JSON.stringify({result:'PASS',faults:receipts.length}));

const browserIndex = process.argv.indexOf('--browser');
if (browserIndex !== -1) {
  const base = process.argv[browserIndex + 1];
  const comparisonIndex = process.argv.indexOf('--comparison');
  const comparisonBase = comparisonIndex === -1 ? base : process.argv[comparisonIndex + 1];
  const files = ['app.js', 'index.html', 'styles.css', 'evidence.js', 'workplace-story.js'];
  const original = await Promise.all(files.map(file => readFile('shiftwork/client/' + file)));
  const rows = [];
  for (const [name, fault] of Object.entries(FIRST_RUN_FAULTS)) {
    const slug = /restoration/.test(name) ? 'gtm' : 'bookshop';
    const target = name === 's47-outcomes' ? comparisonBase : base;
    await runFirstRunBrowser(target, path.join(out, name + '-clean'), slug, '', {quick: true});
    let caught = '';
    try { await runFirstRunBrowser(target, path.join(out, name + '-fault'), slug, name, {quick: true}); }
    catch (error) { assert.equal(error.code, 'ERR_ASSERTION'); assert.ok(error.message.includes(fault.expect), `${name} failed elsewhere: ${error.message}`); caught = error.message; }
    assert.ok(caught, `${name} survived`);
    await writeFile(path.join(out, name + '.log'), caught + '\n');
    for (let i = 0; i < files.length; i++) assert.deepEqual(await readFile('shiftwork/client/' + files[i]), original[i], 'source byte-identical');
    await runFirstRunBrowser(target, path.join(out, name + '-restored'), slug, '', {quick: true});
    rows.push({name, caught: fault.expect, restored: 'PASS'});
    await writeFile(path.join(out, 'browser-faults.json'), JSON.stringify(rows, null, 2));
    console.log('FAULT_CAUGHT', name, fault.expect);
  }
}
