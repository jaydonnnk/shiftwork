import { diffWorkplace } from './workplace-view.js';

export function createWorkplaceHost({container,fallback,status,onStation}) {
  let latest=null, previous=null, scene=null, token=0, disposed=false, expanded=false, visible=false, mounting=false, timer=null, brokenModule=false;
  let simple=false, unavailable=false, mountedTier=null, failureCode=null, generation=-1;
  const motion=matchMedia('(prefers-reduced-motion: reduce)');
  const controls=container.parentElement.parentElement;
  const retryButton=controls.querySelector('[data-graphics-retry]');
  const simplerButton=controls.querySelector('[data-graphics-simple]');
  const contextKey=view=>JSON.stringify(view.context);
  function message(state,text) { status.dataset.state=state; status.textContent=text; }
  function release() { clearTimeout(timer); timer=null; token+=1; mounting=false; scene?.dispose(); scene=null; container.parentElement.dataset.graphics='fallback'; fallback.hidden=(latest?.view?.context.board ?? latest?.context?.board)!=='bookshop'; }
  function showFailure() { message('unavailable',`3D view unavailable. Your workbench is ready. (${failureCode})${brokenModule?' Graphics installation needs repair.':''}`); retryButton.hidden=false; retryButton.disabled=brokenModule; }
  function failure(code) { unavailable=true; failureCode=code; release(); previous=null; showFailure(); }
  const suspended = () => document.hidden || !visible || expanded;
  function suspend() {
    const paused=suspended(); scene?.setSuspended(paused);
    if(paused && mounting) { release(); previous=null; }
    else if(!paused && !scene) mount();
  }
  const tier = () => simple || matchMedia('(max-width: 760px)').matches ? 'compact' : 'standard';
  function resize() { if(scene && mountedTier!==tier()) { release(); previous=null; mount(); return; } scene?.resize({width:container.clientWidth,height:container.clientHeight,pixelRatio:devicePixelRatio}); suspend(); }
  async function mount() {
    if(disposed || suspended() || unavailable || mounting || scene || latest?.kind!=='accepted' || latest.view.context.board!=='bookshop') return;
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
        onFailure(code) { if(owner===token && !disposed) failure(code); }});
    } catch { if(owner===token && !disposed) failure('init-failed'); return; }
    if(disposed || owner!==token) { handle.dispose(); return; }
    clearTimeout(timer); timer=null; mounting=false; scene=handle; previous=latest.view;
    fallback.hidden=true; container.parentElement.dataset.graphics='ready'; retryButton.hidden=true;
    message('ready','3D Bellwether room. Select intake, the console or independent assessment.'); resize();
  }
  function publish(publication) {
    if(disposed) return;
    if(publication.generation!=null && publication.generation<generation) return;
    if(publication.generation!=null) generation=publication.generation;
    const prior=previous; latest=publication;
    if(publication.kind==='reset') { release(); previous=null; if(!unavailable) message('waiting',publication.reason==='error'?'Recorded state unavailable. Refresh your workbench.':'Loading recorded context.'); return; }
    if(publication.kind==='loading') { if(!unavailable) message('loading','Refreshing recorded state'); return; }
    const view=publication.view;
    if(view.context.board!=='bookshop') { release(); previous=view; message('static','This workplace keeps its existing static overview.'); return; }
    if(unavailable) { previous=view; showFailure(); return; }
    if(prior && contextKey(prior)!==contextKey(view)) release();
    const transitions = view.consistency==='conflict' ? [] : diffWorkplace(previous,view);
    previous=view.consistency==='conflict'?null:view;
    if(scene) { scene.apply(view,transitions); suspend(); }
    else mount();
    if(scene) message('ready',view.consistency==='conflict'?'Recorded reads disagree. Inspect the workbench; no outcome is inferred.':'3D Bellwether room. Select intake, the console or independent assessment.');
  }
  function retry() { if(disposed || brokenModule) return; unavailable=false; release(); previous=null; mount(); }
  function onMotion() { scene?.setReducedMotion(motion.matches); }
  function lowerQuality() { simple=true; simplerButton.setAttribute('aria-pressed','true'); retry(); }
  const size=new ResizeObserver(resize), intersection=new IntersectionObserver(entries=>{ visible=entries[0]?.isIntersecting ?? false; suspend(); });
  size.observe(container); intersection.observe(container);
  document.addEventListener('visibilitychange',suspend); motion.addEventListener('change',onMotion);
  retryButton.addEventListener('click',retry); simplerButton.addEventListener('click',lowerQuality);
  return {publish,setExpanded(value) {expanded=value;suspend();},retry,dispose() {
    if(disposed) return; disposed=true; release(); previous=null; latest=null;
    size.disconnect(); intersection.disconnect(); document.removeEventListener('visibilitychange',suspend); motion.removeEventListener('change',onMotion);
    retryButton.removeEventListener('click',retry); simplerButton.removeEventListener('click',lowerQuality);
  }};
}
