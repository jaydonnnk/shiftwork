# S40 checkpoint, 2026-10-22

S40 local implementation on `shiftwork/slice-40` from verified published main `cb39217f06a5eade46c16ca99fa083eef91dfe31`. Accepted by the user on 2026-10-23; publication verification is recorded below. The final 2026-10-23 section is authoritative; earlier blockers and pending-approval entries are historical. Local implementation, the slice branch and disposable previews/receipts were explicitly authorized. No S41/S42, install, download, credential, provider, deployment, protected-fixture edit or Git publication is authorized.

## Implementation and decisions

The accepted attention station owns the amber ring, never the selected station. Only attention/fail lamp materials vary brightness, with no hue change. Ring scale 1.00..1.05 and brightness 0.85..1.00 share a 2.5-second cosine cycle. Host input listeners on workplace-world renew a 20-second deadline. Scene remains the sole RAF owner, with at most 30Hz eligible ambient. Host owns visibility/on-screen/expanded/recency; scene owns tier/reduced/replay eligibility. Replay-running is a controlled sentinel in this slice; actual replay belongs to S41. No report-trigger change.

Camera ease is 180ms, within the 480ms ceiling. Station target offsets are at most 0.3 units from the room target, bounding any station-to-station move to 0.6. First inspector configuration is immediate. Only accepted station-focus transitions or inspector changes ease; narrow layouts stay fixed. The original 160ms stand, 180ms selection and 320ms wall trace remain.

A fresh reviewer found destination clipping planes applied at the starting camera position. The new 761/800/1280 intermediate-frame test failed before repair; the ease now uses clipping planes that enclose both endpoints and settles to the destination planes. The reviewer also requested independent cycle-period proof; a 1-second cycle mutation now has its own assertion.

## Proof and retained limits

Receipts: `/tmp/shiftwork-s40-20261022/`. Baseline Node257 passed. Extended fixture and three input-listener clean/fault/restored tests pass Node260. First ring RED is red-2.log. The 480ms initial choice failed the unchanged inspector centering check at its ~200ms observation; inspector-180 passes the unchanged check. Initial and superseded proofs are retained. Final motion pairs and remaining suites must complete before claiming slice verification.

Proof is this Mac's headless Chromium. It is not physical-device or audible-screen-reader certification; GPU bytes are estimates. Clean installation is excluded and unverified. Inherited port_dead and renderer failure inventories must be compared completely, with nonempty messages. Existing room overlaps and separate S37 visual sign-off remain outside S40.

## Existing-check text and setup changes

No existing observable assertion is weakened. Receipt routing admits S40 explicitly. The test DOM gains closest/world event ownership and scene setInspector/setAmbient methods; existing257 assertions stay. Performance retains five cold documents and three 30-second active samples, now exercising station-focus transitions, and adds three five-second ambient samples per tier. The fullscreen instrumentation array is exported so the S40 test can append observations without changing its assertions.

Old changed test lines, captured from published main:

```javascript
// tests/client/workplace_browser.mjs
  assert.ok(/^\/(?:private\/)?tmp\/shiftwork-s(?:29|30|31|32|33|34|35|36|37|38|39)-[^/]+(?:\/|$)/.test(path.resolve(out)), 'Workplace receipts must use an approved temporary root');
      source=replaceOnce(source,'return { apply, resize,', 'globalThis.__workplaceApply = station => apply({...view,station}, []); globalThis.__workplaceDispose = dispose; return { apply, resize,');
// tests/client/workplace_faults.mjs
assert.ok(/^\/tmp\/shiftwork-s(?:29|30|31|32|33|34|35|36|37|38|39)-/.test(out ?? '')); await mkdir(out,{recursive:true});
// tests/client/workplace_fullscreen.mjs
const INSTRUMENT = [{ file: '/app.js', needle: 'function updateShiftReport(view) {',
  assert.ok(/^\/(?:private\/)?tmp\/shiftwork-s3[6789]-[^/]+(?:\/|$)/.test(path.resolve(out)), 'S36 to S39 receipts must use /tmp/shiftwork-s36-*, /tmp/shiftwork-s37-*, /tmp/shiftwork-s38-* or /tmp/shiftwork-s39-*');
// tests/client/workplace_s32_faults.mjs
assert.ok(/^\/tmp\/shiftwork-s32-/.test(out ?? ''), 'Pass a disposable /tmp/shiftwork-s32-* output directory');
// tests/client/workplace_s33_controls.mjs
assert.ok(/^\/tmp\/shiftwork-s33-/.test(out ?? ''), 'Pass a disposable /tmp/shiftwork-s33-* output directory');
// tests/client/workplace_view.test.mjs
  const container={clientWidth:680,clientHeight:380,parentElement:{dataset:{},parentElement:controls}};
  const module={createWorkplaceScene(options){if(throwDuringCreate) throw Error('injected construction failure');allocations++;const h={options,applied:[],transitions:[],apply(view,transitions=[]){h.applied.push(view);h.transitions.push(transitions);return startsConsequence;},resize(){},setSuspended(v){suspension.push(v);},setReducedMotion(){},dispose(){disposals++;}};handles.push(h);if(failDuringCreate) options.onFailure('shader-failed');return h;}};
  return {host,status,fallback,observers,document,view,accepted,flush,handles,consequences,
// tests/client/workplace_perf.mjs
        while(performance.now()<end) { globalThis.__workplaceApply(n++%2?(document.body.dataset.board==='northline'?'brief':document.body.dataset.board==='gtm'?'signals':'customers'):(document.body.dataset.board==='northline'?'map':document.body.dataset.board==='gtm'?'rules':'evaluator')); await new Promise(requestAnimationFrame); }
```

The existing omit-motion-settle source anchor is updated under Gate3 section13.9, preserving its separate pulse-settlement fault and assertion. Old anchor: `setReducedMotion(value) { reducedMotion=value; if(value) settleAllPulses(); requestFrame(); }`. New fault removes only settleAllPulses from the extended setter; ambient and camera settlement stay so they cannot mask the pulse assertion.

Context ruling: the user explicitly requested handoff at300k..400k actual structured context. AGENTS permits an explicit user extension past175k; this is that extension. Cumulative input is not used as context size.

## Recorded truthfulness and visual review

The final motion table covers the authoritative attention ring, null/conflicting attention, only attention/fail lamp variation, unchanged other tones, bounded scale and hue, the 2.5-second cycle, and every independent ambient stop. Synthetic DOM pointer/key/touch events call the actual owned listeners and resume motion; the real deadline stops it without another event. Double pagehide disposal stops frames. Headless desktop screenshot inspected at1280x720. Hiding tags/story only in the review control exposes the ring below the Customer queue furniture. Ring on/off screenshots differ in291 pixels within(443,420)..(506,450). This confirms drawn geometry rather than the existing HTML tag outline. Normal tags/story are retained; inherited bubble/tag overlap remains disclosed.

The fresh-context reviewer reported two actionable findings: clipping planes and absent cycle-period proof. Both were repaired with their own named failing/restored controls. It found no actionable orphan or duplicate abstraction and confirmed the host/scene ownership split. No cleanup deletion was needed or performed. Review did not itself run browsers; the parent owns the recorded browser proof.

The first served workplace fault pass stopped at omit-dispose-raf because its old disposal anchor no longer matched. The assertion was retained; the source anchor now includes ambient/camera settlement and the fault still removes only RAF cancellation. Old anchor: `if(disposed) return; disposed = true;\n    settleAllPulses();\n    if(raf!==null) cancelAnimationFrame(raf);`. The failed log remains under suites/workplace-faults-browser.

The Northline wheel observation was narrowed to instanced TorusGeometry meshes, preserving the exact two-bike-wheel assertion. Old observer: `scene.children.filter(m=>m.geometry?.type==='TorusGeometry').reduce((n,m)=>n+m.count,0)`. S40's regular torus ring is not a bike wheel. Its own allocation/disposal stays covered by the global resource controls. These are source-observer adaptations, not replacement expected values.

Review found that the retained s35-omit-wheel-dispose mutant would now leak both wheels and ring by omitting all TorusGeometry disposal. It now tags only the actual shared bicycle wheel geometry inside the served control, leaves it registered, and omits only that resource's disposal. Ring disposal cannot satisfy the wheel fault. Old fault replacement: `for(const g of geometries) if(g.type!=='TorusGeometry') g.dispose();`. The original wheel-leak assertion is retained and must be re-proven. Narrow supplement receipts record configured dimensions separately from measured CSS width/height and devicePixelRatio.

Performance's original ten-second zero-idle-frame assertion is retained. Since its active samples now exercise real station-focus transitions, the setup first observes the final camera ease settling, with a500ms deadline. This separates the end of active motion from the unchanged settled-idle measurement; it does not omit any interval inside the active samples or shorten the idle window.

## Continuation, 2026-10-23: scoped Gate 3 test conflict

S40 remains unaccepted and unpublished. No Gate 3 test correction has been approved or applied. The existing expanded-clean control failed `assert.ok(restored.frames <= 2, 'Restore replayed suspended work')`. A controlled diagnostic repeated the unchanged assertion and recorded4 frames over150ms, pulse=false, cameraEase=false. Eligible resumed ambient is allowed30fps. The separate restore-ambient proof records0 expanded frames and150 frames over5 seconds after restoring recent-input eligibility.

The proposed correction keeps every original assertion and makes ambient ineligible only in this legacy replay-safety served control. The original pulse, focus, caret, same-node and ARIA checks remain. Ambient restoration remains separately proven. This setup change is not in Gate 3 section13.9's currently listed S30 changes, so the user was asked for scoped approval. That answer is pending; no local S40 implementation go-ahead was requested again.

Independent completed proof now includes19 named motion guards, both native-zoom narrow supplements with measured CSS viewports/DPR,260 Node,9 closure,57 retained fullscreen fault/restored pairs,3 complete journeys/actual rooms,31 corrected served browser controls,152 source controls,26 resource/focus controls,3 clean fullscreen boards and200-percent dialogs. Fresh performance has5 cold documents and3 active/ambient samples per tier; no13.8 budget miss, all desktop ambient samples150 draws over5 seconds and compact0. Python retains only port_dead with1454 passes,1 skip,2 warnings.

The full renderer run is38/50, not39/50. All11 inherited failing records match S39 in full, with nonempty matching messages. An additional baseline-transient case failed the778px overflow assertion; old/new source diagnosis is ongoing. Do not replace the full-run result with a targeted rerun.

First new200-percent supplement had an offscreen readiness failure, retained under narrow-2-fault and narrow-final.log. Corrected scrolling/readiness then passed the named narrow fault/restoration. The corrected disposal anchor passed31 served controls. Wheel observer/disposal mutations now distinguish the bicycle geometry from the ring; S35 controls pass.

Performance claims are local budget compliance only, not a comparative speedup. Actual renderer work is counted inside the measured interval. The pre-run host-load snapshot was not retained; host-load-after.txt is explicitly a post-run observation. No physical-device, audible AT, clean-install or exact-browser certification is added.

## Final independent-proof boundary, 2026-10-23

The additional renderer overflow is not classified as inherited or S40-caused. Diagnostic roots diagnosis, diagnosis-v2, diagnosis-v3 and diagnosis-v4 retain setup failures and non-clean comparisons. No comparison is accepted as a clean rerun. The last setup enabled recorded assist although baseline-transient uses the unassisted default. After the three distinct setup failures this diagnostic is stopped incomplete. `diagnosis-next/run.py` has the corrected unassisted preview and separate browser artifact child, prepared but not executed. The original full renderer receipt remains38/50.

The original expanded-work assertions and Gate3 documents are unchanged. The approval question concerns the exact proposed test-only correction in the projectless outputs/s40-gate3-test-correction.md. No answer has arrived at this boundary. Do not assume a preselected option means approval. After approval, record the scoped gate correction, implement the served ambient-ineligible precondition only for expand-* controls, retain and reprove every old assertion/fault, and continue overflow diagnosis with the actual renderer preview configuration. Do not ask for local S40 go-ahead again.

Independent proof receipt source hashes remain frozen. Source,fixtures and index must be reverified before resuming. No S41/S42, commit, stage, merge, push, download, install, credential, provider, protected edit or deployment occurred. Do not ask S40 acceptance until both blockers are resolved and the strict final audit passes.

## Scoped Gate3 approval,2026-10-23

The user answered the pending approval question with "Approve scoped Gate 3 correction". This authorizes only the proposed legacy-control isolation, preserving every original assertion and proving ambient resumption separately. Gate3 section13.9 now records the scoped re-approval. The served expand-* host forwards false to setAmbient; its asserted precondition ensures isolation is active. No production behavior changed. The earlier pending-approval entries above are historical. Renderer overflow classification remains open.

## Final local verification and acceptance boundary, 2026-10-23

S40 is locally verified within its exit contract and awaits user acceptance. It remains uncommitted and unpublished. All 19 independent motion guard mutations pass restored, including each ambient stop, cap, cycle, authoritative ring, narrow stillness, camera trigger/duration/distance/clipping, initial inspector and duplicate inspector guards. Both native-zoom narrow supplements record configured dimensions separately from measured CSS viewports and DPR. Three input listener disposal mutations pass within 260 Node tests.

The user-approved Gate 3 test correction is fully re-proven. Every original S30 expanded-work assertion remains unchanged; the served expand-* setup isolates ambient and asserts that precondition. All three old expanded-work clean/fault/restored triples pass, and all 34 broader controls pass. Separate actual rendering proof records zero frames while expanded and 150 frames over five seconds on eligible restoration.

Final evidence: audit.json; approved-controls/expanded-pairs.json; controls-final/controls-summary.json; motion-all-pairs.json; fullscreen/summary.json and done.json; journeys/complete-browser-results.json; suites/perf/out/performance.json; rest/browser-faults.json; node-final.log; closure-final.log; python.log. Counts are 57 retained fullscreen fault pairs, three complete journeys and actual rooms, 31 served browser controls, 152 source controls, 26 resource/focus fault triples, three clean fullscreen boards, and the existing 100/200-percent dialog and keyboard/reach matrices. Performance has five cold documents and three active plus three ambient samples at 1280 DPR1, 1280 DPR2 and 390 DPR3. No section 13.8 budget misses; every standard ambient sample is 150 draws over five seconds, every compact sample zero. Python retains only port_dead, with 1454 passed, one skipped and two warnings. Closure is nine passed; engine inventory remains two modules.

The raw renderer result remains 38/50. All eleven inherited failure records match S39 in full and have nonempty identical messages. The additional baseline-transient 778px overflow occurred while 3D was loading and the SVG fallback was visible. A controlled WebGL-disabled fallback at the same 778x900 viewport and service inspector reproduces the exact 832px document width and original overflow assertion on both the published S39 source and S40. Old host/scene/manifest bytes match HEAD exactly; app, HTML and CSS are unchanged from that publication. Receipts are diagnosis-next/fallback-old-1/browser/result.json and fallback-new-1/browser/result.json, plus screenshots and fallback-778.log. This supports classification as a newly discovered inherited fallback-layout defect. It does not establish whether S40 changes how often the transient loading state exposes it. No CSS fix or new room redesign is included. No failed full run is replaced by a targeted green claim.

The final fresh-context review accepts this bounded classification, confirms the approved test adaptation preserves original assertions, and recommends no code change or cleanup deletion. This is review approval, not user acceptance or publication authority. Existing room overlaps, separate S37 sign-off, clean-install exclusion, physical-device and audible-AT limits remain. GPU allocation is estimated.

All 96 protected fixture-path files, including the two archived copies, are unchanged. All client files match the source hashes retained by the fullscreen matrix; no production change followed those proofs. HEAD, main and origin/main remain cb39217; remote main was reverified equal, and the index is empty. No install, download, provider, credential, deployment, protected edit, staging, commit, merge or push occurred. No S41 or S42 implementation.

Review URL: http://127.0.0.1:8366/?board=bookshop#board. Its fresh disposable database is /tmp/shiftwork-s40-20261022/review.db. Owned process metadata is in previews.json. The initial owned 8365 preview was stopped; S39 review previews were untouched. At widths at least 761 CSS pixels, recent pointer, key or touch input enables standard-tier quiet motion. The normal compact layout stays still.

At that local-verification stop, the next boundary was the S40 acceptance question. The later acceptance and publication sections supersede that stop.

## Acceptance and publication authority, 2026-10-23

In reply to "Is S40 accepted, or what should change?", the user wrote:
"I accept. Push and merge to main thanks"

This accepts S40 with the disclosed evidence limits and authorizes focused commits, publishing `shiftwork/slice-40`, merging to main and pushing main. No co-author trailers. The branch will be retained. S41/S42, installation, downloads, credentials, providers, protected edits, deployment and unrelated cleanup remain excluded. No new slice branch is authorized.

The accepted renderer result stays 38/50; the additional 778px fallback overflow reproduces on published S39, but its transient-frequency effect remains unknown. The other eleven failure records match in full. The known port_dead failure and all previously disclosed evidence limits remain. No failure is waived or relabelled green by publication.

Before publication, the branch and local/remote main were reverified at cb39217f06a5eade46c16ca99fa083eef91dfe31, with no existing remote slice-40 ref and an empty index. Node 260, closure nine and the accepted audit passed again. The scoped Python recheck is recorded under /tmp/shiftwork-s40-ship-20261023/. No installer is invoked.

The fresh shipping Python process completed before commits: 1454 passed, one skipped, two warnings and only the known port_dead failure in163.89s. Node260, closure9 and the accepted audit pass. Client hashes and all96 protected paths remain unchanged. Receipts: /tmp/shiftwork-s40-ship-20261023/.

## Verified S40 publication, 2026-10-23

Six focused commits, 961fe065 through 76264973, were created on shiftwork/slice-40 with no co-author trailers. The slice branch was published and main fast-forwarded from cb39217f to 762649732d8b9481972b867fa0289e60a2007cd7. Main was pushed. git ls-remote then confirmed both remote refs at that implementation and acceptance tip; main and origin/main had left/right counts 0/0, with a clean working tree and index.

Node260 and closure9 passed on the merged main, with exact client hash equality to the accepted source. The precommit scoped Python run completed with 1454 passed, one skipped, two warnings and only the known port_dead failure. All96 protected fixture-path files remain unchanged. No installer or excluded provider, credential, deployment, protected edit or next-slice action occurred.

This documentation-only publication receipt follows the verified implementation tip without changing the tested client. Resolve the latest tip live; final exact refs, commit inventory and preservation proof are recorded outside the repository under /tmp/shiftwork-s40-ship-20261023/final-publication.json. The slice branch is retained and published. S41 and S42 remain unauthorized.
