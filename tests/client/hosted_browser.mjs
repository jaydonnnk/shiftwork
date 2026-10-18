// Read-only hosted/client checks. This runner never clicks a billable action.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { chromePath } from './env.mjs';

const base = process.argv[2];
const out = process.argv[3];
assert.ok(base && out);
await mkdir(out, { recursive: true });
const profile = await mkdtemp(path.join(tmpdir(), 'shiftwork-s28-browser-'));
const chrome = spawn(chromePath, ['--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
let socket;
try {
  const endpoint = await new Promise((resolve, reject) => {
    let stderr = '';
    const timer = setTimeout(() => reject(new Error('Chrome startup timed out')), 15000);
    chrome.once('error', reject);
    chrome.stderr.on('data', data => {
      stderr += data;
      const match = stderr.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) { clearTimeout(timer); resolve(match[1]); }
    });
  });
  socket = new WebSocket(endpoint);
  await once(socket, 'open');
  let sequence = 0, session;
  const pending = new Map(), exceptions = [];
  socket.addEventListener('message', ({ data }) => {
    const message = JSON.parse(data);
    if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails.text);
    const request = pending.get(message.id);
    if (!request) return;
    pending.delete(message.id); clearTimeout(request.timer);
    message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result);
  });
  function send(method, params = {}, scoped = true) {
    return new Promise((resolve, reject) => {
      const id = ++sequence;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout ${method}`)); }, 90000);
      pending.set(id, { resolve, reject, timer });
      socket.send(JSON.stringify({ id, method, params, ...(scoped && session ? { sessionId: session } : {}) }));
    });
  }
  async function evaluate(fn, ...args) {
    const result = await send('Runtime.evaluate', { expression: `(${fn.toString()})(...${JSON.stringify(args)})`, awaitPromise: true, returnByValue: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text);
    return result.result.value;
  }
  const target = await send('Target.createTarget', { url: 'about:blank' }, false);
  session = (await send('Target.attachToTarget', { targetId: target.targetId, flatten: true }, false)).sessionId;
  await send('Page.enable'); await send('Runtime.enable');
  const report = { url: base, scope: 'read-only representative views; no inference or model-quality proof', screens: [], boards: [], consoleExceptions: exceptions };
  for (const width of [1440, 390]) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 960, deviceScaleFactor: 1, mobile: width === 390 });
    await send('Page.navigate', { url: base + '/?board=bookshop#board' });
    await evaluate(async () => {
      const deadline = Date.now() + 65000;
      while (!['ready', 'empty'].includes(document.body?.dataset.loadState)) {
        if (Date.now() > deadline) throw new Error('Client did not become ready: ' + document.getElementById('load-message')?.textContent);
        await new Promise(resolve => setTimeout(resolve, 50));
      }
    });
    const notice = await evaluate(() => document.getElementById('runtime-notice')?.textContent);
    const runtime = await evaluate(async () => (await fetch('/api/runtime')).json());
    assert.equal(notice, runtime.notice, 'Rendered hosted notice must match the runtime API');
    assert.ok(notice?.includes('fresh practice database'), 'Rendered hosted reset warning is missing');
    for (const [view, region] of [['board', 'board-view'], ['contract', 'board-view'], ['investigate', 'investigate-view'], ['compare', 'compare-view'], ['customers', 'customer-view'], ['next', 'next-view']]) {
      await evaluate(view => { location.hash = view; }, view);
      await evaluate(async () => { await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))); });
      assert.equal(await evaluate(id => !document.getElementById(id).hidden, region), true, `Screen ${view} is hidden at ${width}px`);
      const { data } = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
      await writeFile(path.join(out, `${width}-${view}.png`), Buffer.from(data, 'base64'));
      report.screens.push({ view, width, visible: true });
    }
  }
  for (const board of ['bookshop', 'gtm', 'northline']) {
    const result = await evaluate(async board => { const r = await fetch(`/api/engagements/${board}/board`); const body = await r.json(); return { status: r.status, slug: body.engagement_slug, chain: body.chain_status }; }, board);
    assert.equal(result.status, 200); assert.equal(result.slug, board);
    report.boards.push(result);
  }
  assert.deepEqual(exceptions, [], 'Client has JavaScript exceptions');
  await writeFile(path.join(out, 'browser.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ screens: report.screens.length, boards: report.boards.length, consoleExceptions: exceptions.length }));
  await send('Browser.close', {}, false);
} finally {
  socket?.close();
  if (chrome.exitCode === null && chrome.signalCode === null) {
    const exited = once(chrome, 'exit');
    chrome.kill();
    await exited;
  }
  await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}
