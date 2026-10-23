import { diffWorkplace } from './workplace-view.js';

export function createWorkplaceHost({container,fallback,status,onStation,onConsequence,onAnchors,onHover}) {
  let latest=null, previous=null, scene=null, token=0, disposed=false, expanded=false, visible=false, mounting=false, timer=null, brokenModule=false;
  let simple=false, unavailable=false, mountedTier=null, failureCode=null, generation=-1, inspector={open:false,widthPx:0};
  let lastInput=-Infinity, inputTimer=null, openStation=null;
  const world=container.closest('#workplace-world');
  const motion=matchMedia('(prefers-reduced-motion: reduce)');
  const controls=container.parentElement.parentElement;
  const retryButton=controls.querySelector('[data-graphics-retry]');
  const simplerButton=controls.querySelector('[data-graphics-simple]');
  const contextKey=view=>JSON.stringify(view.context);
  const hasRoom=board=>board==='bookshop' || board==='gtm' || board==='northline';
  const roomLabel=board=>board==='northline' ? '3D Northline workshop. Select the brief, permission map, bench, acceptance, rollout or handover.' : board==='gtm' ? '3D Stonebridge room. Select signal intake, qualification, routing or ownership.' : '3D Bellwether room. Select intake, the console, diagnosis or assessment.';
  function message(state,text) { status.dataset.state=state; status.textContent=text; }
  function release() { clearTimeout(inputTimer); inputTimer=null; clearTimeout(timer); timer=null; token+=1; mounting=false; scene?.dispose(); scene=null; container.parentElement.dataset.graphics='fallback'; fallback.hidden=(latest?.view?.context.board ?? latest?.context?.board)!=='bookshop'; }
  function showFailure() { message('unavailable',`3D view unavailable. Your workbench is ready. (${failureCode})${brokenModule?' Graphics installation needs repair.':''}`); retryButton.hidden=false; retryButton.disabled=brokenModule; }
  function failure(code) { unavailable=true; failureCode=code; release(); previous=null; showFailure(); }
  const suspended = () => document.hidden || !visible || expanded;
  function suspend() {
    const paused=suspended(); scene?.setSuspended(paused); updateAmbient();
    if(paused && mounting) { release(); previous=null; }
    else if(!paused && !scene) mount();
  }
  function updateAmbient() {
    clearTimeout(inputTimer); inputTimer=null;
    const recent=performance.now()-lastInput<20000;
    scene?.setAmbient(!suspended() && recent);
    if(scene && recent && !disposed) inputTimer=setTimeout(updateAmbient,Math.max(1,20000-(performance.now()-lastInput)));
  }
  function noteInput() { if(disposed) return; lastInput=performance.now(); updateAmbient(); }
  const tier = () => simple || matchMedia('(max-width: 760px)').matches ? 'compact' : 'standard';
  function resize() { if(scene && mountedTier!==tier()) { release(); previous=null; mount(); return; } scene?.resize({width:container.clientWidth,height:container.clientHeight,pixelRatio:devicePixelRatio}); suspend(); }
  async function mount() {
    if(disposed || suspended() || unavailable || mounting || scene || latest?.kind!=='accepted' || !hasRoom(latest.view.context.board)) return;
    const owner=++token; mounting=true; message('loading','Loading 3D view. Your workbench is ready.');
    timer=setTimeout(()=>{ if(owner===token && !disposed) failure('load-timeout'); },8000);
    let createWorkplaceScene;
    try { ({createWorkplaceScene}=await import('./workplace-scene.js')); }
    catch { if(owner===token && !disposed) { brokenModule=true; failure('module-unavailable'); } return; }
    if(disposed || owner!==token) return;
    if(latest?.kind!=='accepted') { clearTimeout(timer); timer=null; mounting=false; return; }
    const view=latest.view;
    let handle;
    try {
      mountedTier=tier();
      handle=createWorkplaceScene({container,view,tier:mountedTier,reducedMotion:motion.matches,
        onPick(stationId) { if(!disposed && owner===token && latest?.kind==='accepted' && latest.view.context.board===view.context.board && latest.view.context.shiftId===view.context.shiftId) onStation({board:view.context.board,shiftId:view.context.shiftId,stationId,mountToken:owner}); },
        onFailure(code) { if(owner===token && !disposed) failure(code); },
        // Gate 3 section 14.1: crew screen points ride in the same payload under `crew`.
        onAnchors(positions,crew) { if(owner===token && !disposed) onAnchors?.(positions ? {...positions,crew:crew ?? {}} : {crew:crew ?? {}}); },
        onHover(stationId) { if(owner===token && !disposed) onHover?.(stationId); }});
    } catch { if(owner===token && !disposed) failure('init-failed'); return; }
    if(disposed || owner!==token) { handle.dispose(); return; }
    clearTimeout(timer); timer=null; mounting=false; scene=handle; handle.setInspector(inspector);
    // A remount shows the learner's bot already at the open station: no walk without a new choice.
    handle.setOpenStation(openStation,{settled:true});
    const transitions=diffWorkplace(previous,view);
    previous=view.consistency==='conflict'?previous:view;
    fallback.hidden=true; container.parentElement.dataset.graphics='ready'; retryButton.hidden=true;
    message('ready',roomLabel(view.context.board));
    if(transitions.length) {
      const consequence=transitions.find(item=>item.kind==='linked-consequence');
      if(handle.apply(view,transitions) && consequence) onConsequence?.({count: consequence.count ?? 1, eventIds: [...consequence.publicRefs]});
    }
    resize();
  }
  function publish(publication) {
    if(disposed) return;
    if(publication.generation!=null && publication.generation<generation) return;
    if(publication.generation!=null) generation=publication.generation;
    const prior=previous; latest=publication;
    if(publication.kind==='reset') { release(); if(!unavailable) message('waiting',publication.reason==='error'?'Recorded state unavailable. Refresh your workbench.':'Loading recorded context.'); return; }
    if(publication.kind==='loading') { if(!unavailable) message('loading','Refreshing recorded state'); return; }
    const view=publication.view;
    if(!hasRoom(view.context.board)) { release(); previous=view; message('static','This workplace keeps its existing static overview.'); return; }
    if(unavailable) { previous=view; showFailure(); return; }
    if(prior && contextKey(prior)!==contextKey(view)) release();
    const transitions = view.consistency==='conflict' ? [] : diffWorkplace(previous,view);
    const consequence = transitions.find(item => item.kind==='linked-consequence');
    if(scene) {
      if(view.consistency!=='conflict') previous=view;
      const started=scene.apply(view,transitions); suspend();
      if(started && consequence) onConsequence?.({count: consequence.count ?? 1, eventIds: [...consequence.publicRefs]});
    } else mount();
    if(scene) message('ready',view.consistency==='conflict'?'Recorded reads disagree. Inspect the workbench; no outcome is inferred.':roomLabel(view.context.board));
  }
  function retry() { if(disposed || brokenModule) return; unavailable=false; release(); previous=null; mount(); }
  function onMotion() { scene?.setReducedMotion(motion.matches); updateAmbient(); }
  function lowerQuality() { simple=true; simplerButton.setAttribute('aria-pressed','true'); retry(); }
  const size=new ResizeObserver(resize), intersection=new IntersectionObserver(entries=>{ visible=entries[0]?.isIntersecting ?? false; suspend(); });
  size.observe(container); intersection.observe(container);
  document.addEventListener('visibilitychange',suspend); motion.addEventListener('change',onMotion);
  for(const type of ['pointerdown','keydown','touchstart']) world.addEventListener(type,noteInput,{passive:true});
  retryButton.addEventListener('click',retry); simplerButton.addEventListener('click',lowerQuality);
  function setInspector(value) { inspector={open:!!value?.open,widthPx:value?.open?Math.max(0,Number(value.widthPx)||0):0}; scene?.setInspector(inspector); }
  // Gate 3 section 14.2 rule 3: only the app's station choice and inspector close call this.
  function setOpenStation(stationId) { openStation=stationId ?? null; scene?.setOpenStation(openStation); }
  return {publish,setExpanded(value) {expanded=value;suspend();},setInspector,setOpenStation,noteInput,retry,dispose() {
    if(disposed) return; disposed=true; release(); previous=null; latest=null;
    for(const type of ['pointerdown','keydown','touchstart']) world.removeEventListener(type,noteInput);
    size.disconnect(); intersection.disconnect(); document.removeEventListener('visibilitychange',suspend); motion.removeEventListener('change',onMotion);
    retryButton.removeEventListener('click',retry); simplerButton.removeEventListener('click',lowerQuality);
  }};
}
