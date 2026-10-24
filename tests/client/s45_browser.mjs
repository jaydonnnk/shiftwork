// Offline rendering and served faults. No live calls or learner actions.
import assert from 'node:assert/strict';
import {mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {openBrowser, FAULTS} from './workplace_fullscreen.mjs';

const [base, out, fault = '', zoomText = '1'] = process.argv.slice(2);
const zoom = Number(zoomText);
assert.ok([1, 2].includes(zoom));
FAULTS['s45-shown-rate'] = {file: '/evidence.js',
  needle: '${summary.candidate_label}: ${passed} of ${declared} public repetitions',
  replacement: '${summary.candidate_label}: ${passed + 1} of ${declared} public repetitions',
  expect: 'rendered_comparison_rate: exact retained rate missing'};
FAULTS['s45-wrong-run-link'] = {file: '/app.js',
  needle: '            const detail = document.getElementById(target);',
  replacement: "            const detail = document.querySelector('details[id^=comparison-repetition-]');",
  expect: 'repetition_link: wrong retained run opened'};
FAULTS['s45-reasoning-open'] = {file: '/app.js',
  needle: "    detail.dataset.providerReasoning = 'true';",
  replacement: "    detail.dataset.providerReasoning = 'true'; detail.open = true;",
  expect: 'provider_reasoning_toggle: full text must start collapsed'};
FAULTS['s45-reasoning-html'] = {file: '/app.js',
  needle: "    detail.append(element('pre', reasoning));",
  replacement: "    const unsafe = element('pre'); unsafe.innerHTML = reasoning; detail.append(unsafe);",
  expect: 'provider_reasoning_is_text: provider text was parsed as HTML'};
FAULTS['s45-choose-rate'] = {file: '/app.js',
  needle: "  $('choose-rates').replaceChildren(...comparisonRateLines(state.comparison).map(line => element('p', line)));",
  replacement: "  $('choose-rates').replaceChildren();",
  expect: 'choose_rate: confirmation must show both retained rates'};
FAULTS['s45-choose-links'] = {file: '/app.js', needle: "  $('choose-links').replaceChildren(links);",
  replacement: "  $('choose-links').replaceChildren();", expect: 'choose_links: confirmation needs every retained repetition link'};
FAULTS['s45-choose-keyboard'] = {file: '/app.js',
  needle: "dialog.querySelectorAll('button, textarea, a[href], summary')",
  replacement: "dialog.querySelectorAll('button, textarea')", expect: 'choose_keyboard: Tab must wrap to the evidence controls'};
FAULTS['s45-limit-contrast'] = {file: '/styles.css',
  needle: '#choose-rate-limit { color: #a9b6c4; }',
  replacement: '#choose-rate-limit { color: #526273; }', expect: 'choose_limit_contrast: sample warning must be legible'};
FAULTS['s45-evidence-contrast'] = {file: '/styles.css',
  needle: '#choose-links-summary { color: #a9b6c4; font-size: 16px; }',
  replacement: '#choose-links-summary { color: #486c5b; font-size: 16px; }', expect: 'choose_evidence_contrast: evidence label must be legible'};

await mkdir(out, {recursive: true});
const browser = await openBrowser(base, out, fault, {zoom, webgl: false});
const receipts = [];
try {
  for (const [width, height] of [[1280, 720], [390, 844]]) {
    await browser.send('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: 1, mobile: false});
    await browser.send('Page.navigate', {url: `${base}/?board=bookshop#compare`});
    assert.ok(await browser.until(() => document.body?.dataset.loadState === 'ready'), 'rendering board did not load');
    await browser.evaluate(() => document.querySelector('[data-station="compare"]').click());
    assert.ok(await browser.until(() => document.querySelectorAll('.comparison-pass-rate').length === 2), 'comparison rates did not render');
    assert.notEqual(await browser.evaluate(() => document.getElementById('workplace-state').textContent),
      'Recorded reads disagree. Inspect the workbench; current labels are unavailable.', 'room evidence bindings disagree');
    assert.ok(await browser.evaluate(() => document.getElementById('comparison-outcome').textContent.includes('No model call in the public repetitions.')), 'zero-call label must stay scoped to public evidence');
    const lines = await browser.evaluate(() => [...document.querySelectorAll('.comparison-pass-rate')].map(node => node.textContent));
    assert.match(lines[0], /A: 8 of 9 public repetitions pass mandatory checks/, 'rendered_comparison_rate: exact retained rate missing');
    assert.match(lines[0], /cut off 1, invalid plan 0, omitted task 0/, 'rendered_comparison_cause: cut-off attribution missing');
    assert.match(lines[1], /B: 9 of 9 public repetitions pass mandatory checks/);
    assert.ok(await browser.evaluate(() => document.getElementById('comparison-outcome').textContent.includes('Small sample')), 'small sample limit missing');
    assert.ok(await browser.evaluate(() => document.getElementById('runtime-notice').textContent.includes('Operator-authored')), 'fixture authorship label missing');
    const before = browser.commands.length;
    const links = await browser.evaluate(() => [...document.querySelectorAll('a[data-repetition-run-id]')].map(node => node.dataset.repetitionRunId));
    assert.equal(links.length, 18, 'every retained repetition needs its own link');
    for (const runId of links) {
      await browser.evaluate(runId => document.querySelector(`a[data-repetition-run-id="${runId}"]`).click(), runId);
      assert.ok(await browser.evaluate(runId => document.getElementById(`comparison-repetition-${runId}`).open, runId),
        'repetition_link: wrong retained run opened');
      assert.ok(await browser.evaluate(runId => document.getElementById(`comparison-repetition-${runId}`).textContent.includes(runId), runId));
    }
    assert.equal(browser.commands.length, before, 'inspection links must send no mutation');
    await browser.evaluate(() => document.getElementById('open-choose-b').click());
    assert.ok(await browser.evaluate(() => document.getElementById('choose-dialog').open), 'eligible choice dialog did not open');
    assert.ok(await browser.evaluate(() => {
      const rates = document.getElementById('choose-rates')?.textContent ?? '';
      return rates.includes('A: 8 of 9') && rates.includes('B: 9 of 9');
    }), 'choose_rate: confirmation must show both retained rates');
    const chooseLinks = await browser.evaluate(() => [...document.querySelectorAll('#choose-dialog a[data-choose-repetition-run-id]')].map(node => node.dataset.chooseRepetitionRunId));
    assert.equal(chooseLinks.length, 18, 'choose_links: confirmation needs every retained repetition link');
    const contrast = await browser.evaluate(() => {
      const luminance = color => {
        const linear = color.match(/[\d.]+/g).slice(0, 3).map(value => {
          const channel = Number(value) / 255;
          return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
        });
        return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
      };
      const background = luminance(getComputedStyle(document.getElementById('choose-dialog')).backgroundColor);
      return ['choose-rate-limit', 'choose-links-summary'].map(id => {
        const foreground = luminance(getComputedStyle(document.getElementById(id)).color);
        return (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05);
      });
    });
    assert.ok(contrast[0] >= 4.5, 'choose_limit_contrast: sample warning must be legible');
    assert.ok(contrast[1] >= 4.5, 'choose_evidence_contrast: evidence label must be legible');
    await browser.evaluate(() => document.getElementById('cancel-choose').focus());
    await browser.send('Input.dispatchKeyEvent', {type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9});
    await browser.send('Input.dispatchKeyEvent', {type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9});
    assert.equal(await browser.evaluate(() => document.activeElement.id), 'choose-links-summary', 'choose_keyboard: Tab must wrap to the evidence controls');
    await browser.evaluate(() => document.getElementById('choose-links-summary').click());
    await browser.send('Input.dispatchKeyEvent', {type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9});
    await browser.send('Input.dispatchKeyEvent', {type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9});
    assert.equal(await browser.evaluate(() => document.activeElement.dataset.chooseRepetitionRunId), chooseLinks[0], 'choose_keyboard: expanded evidence links must be reachable');
    const inspectRun = chooseLinks.at(-1);
    await browser.evaluate(run => {
      for (const detail of document.querySelectorAll('details[id^=comparison-repetition-]')) detail.open = false;
      const links = [...document.querySelectorAll('#choose-dialog a[data-choose-repetition-run-id]')];
      links.find(node => node.dataset.chooseRepetitionRunId === run).click();
    }, inspectRun);
    assert.ok(await browser.until(run => !document.getElementById('choose-dialog').open &&
      document.getElementById(`comparison-repetition-${run}`)?.open, 3000, inspectRun), 'choose_links: inspection must close confirmation and open the exact run');
    assert.equal(browser.commands.length, before, 'inspecting from confirmation must send no selection');
    const toggle = await browser.evaluate(() => {
      const detail = document.querySelector('details[data-provider-reasoning]');
      return {open: detail.open, label: detail.querySelector('summary').textContent,
        text: detail.querySelector('pre').textContent, html: detail.querySelectorAll('script').length};
    });
    assert.equal(toggle.html, 0, 'provider_reasoning_is_text: provider text was parsed as HTML');
    assert.equal(toggle.text, 'Operator-authored display fixture: <script>globalThis.s45Unsafe=true</script>',
      'provider_reasoning_is_text: retained text was changed');
    assert.equal(toggle.open, false, 'provider_reasoning_toggle: full text must start collapsed');
    assert.equal(toggle.label, "model's reasoning, as returned by the provider");
    await browser.evaluate(() => {
      const detail = document.querySelector('details[data-provider-reasoning]');
      detail.querySelector('summary').click(); detail.scrollIntoView({block: 'start', behavior: 'instant'});
    });
    assert.ok(await browser.evaluate(() => document.querySelector('details[data-provider-reasoning]').open));
    assert.equal(await browser.evaluate(() => globalThis.s45Unsafe === true), false);
    const bounds = await browser.evaluate(() => ({width: innerWidth, height: innerHeight,
      scrollWidth: document.documentElement.scrollWidth, text: document.getElementById('comparison-slots').textContent}));
    assert.ok(bounds.scrollWidth <= bounds.width, 'comparison has horizontal page overflow');
    assert.ok(!bounds.text.includes('PROTECTED-ONLY-S45-REASON'), 'protected reasoning reached the public UI');
    if (zoom === 2 && width === 1280) assert.deepEqual([bounds.width, bounds.height], [640, 360], 'native 200% zoom did not apply');
    const shot = await browser.send('Page.captureScreenshot', {format: 'png'});
    await writeFile(path.join(out, `comparison-${width}-${zoom}x.png`), Buffer.from(shot.data, 'base64'));
    receipts.push({width, height, zoom, cssViewport: [bounds.width, bounds.height], links, lines});
  }
  assert.deepEqual(browser.exceptions, [], 'JavaScript exception');
  browser.assertFaultServed();
  await writeFile(path.join(out, 'result.json'), JSON.stringify({status: 'PASS',
    label: 'Operator-authored rendering fixtures only; no model call or learner action', receipts}, null, 2));
  console.log('PASS: retained rates, causes, 18 exact links, safe collapsed reasoning, desktop and mobile');
} finally { await browser.close(); }
