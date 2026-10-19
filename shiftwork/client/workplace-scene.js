import * as THREE from './vendor/three-r180/three.module.js';
import { roomDefinitions } from './workplace-rooms.js';

export function createWorkplaceScene({ container, view, tier, reducedMotion, onPick, onFailure }) {
  let renderer, disposed = false, suspended = false, raf = null, pointer = null, lastDraw = -Infinity;
  const geometries = new Set(), materials = new Set(), targets = [];
  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-8,8,6,-6,.1,100);
  camera.position.set(12,11,14); camera.lookAt(0,.8,0);
  const raycaster = new THREE.Raycaster(), cursor = new THREE.Vector2();
  const room = roomDefinitions[view.context.board];
  if (!room) throw new Error('Unsupported room');
  const listeners = [];
  const listen = (type,fn) => { renderer.domElement.addEventListener(type,fn); listeners.push([type,fn]); };
  function draw(now = performance.now()) {
    raf = null;
    if (disposed || suspended) return;
    if (tier === 'compact' && now - lastDraw < 1000 / 30 - .2) { raf = requestAnimationFrame(draw); return; }
    lastDraw = now;
    try { renderer.render(scene, camera); }
    catch { onFailure('render-failed'); }
  }
  function requestFrame() { if (!disposed && !suspended && raf === null) raf = requestAnimationFrame(draw); }
  function resize({width,height,pixelRatio}) {
    if(disposed || width<=0 || height<=0) return;
    renderer.setPixelRatio(Math.min(pixelRatio,tier==='compact'?1:1.5));
    renderer.setSize(width,height,false);
    camera.updateMatrixWorld();
    const inverse = camera.matrixWorldInverse;
    const points = [];
    for(const x of [room.bounds.min[0],room.bounds.max[0]]) for(const y of [room.bounds.min[1],room.bounds.max[1]]) for(const z of [room.bounds.min[2],room.bounds.max[2]]) points.push(new THREE.Vector3(x,y,z).applyMatrix4(inverse));
    const margin = tier==='compact'?1.08:1.12;
    const halfWidth = Math.max(...points.map(p=>Math.abs(p.x)))*margin;
    const halfHeight = Math.max(...points.map(p=>Math.abs(p.y)))*margin;
    const h = Math.max(halfHeight,halfWidth/(width/height));
    camera.left = -h*width/height; camera.right = h*width/height; camera.top = h; camera.bottom = -h;
    camera.updateProjectionMatrix(); requestFrame();
  }
  function dispose() {
    if(disposed) return; disposed = true;
    if(raf!==null) cancelAnimationFrame(raf); raf = null;
    for(const [type,fn] of listeners) renderer?.domElement.removeEventListener(type,fn);
    listeners.length = 0; targets.length = 0;
    scene.clear();
    for(const g of geometries) g.dispose(); for(const m of materials) m.dispose();
    geometries.clear(); materials.clear();
    for(const light of sceneLights) light.shadow?.dispose();
    sceneLights.length = 0;
    renderer?.dispose(); renderer?.forceContextLoss(); renderer?.domElement.remove();
    renderer = null;
  }
  const sceneLights = [];
  try {
    renderer = new THREE.WebGLRenderer({antialias:tier!=='compact',alpha:false});
    renderer.domElement.setAttribute('aria-hidden','true'); renderer.domElement.tabIndex = -1;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = 1;
    renderer.setClearColor('#202c40');
    renderer.debug.onShaderError = () => onFailure('shader-failed');
    renderer.shadowMap.enabled = tier !== 'compact'; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    const fill = new THREE.HemisphereLight('#dbe6f2','#394453',2);
    const key = new THREE.DirectionalLight('#fff1d8',2.5); key.position.set(-6,10,6);
    key.castShadow = tier !== 'compact'; key.shadow.mapSize.set(1024,1024);
    Object.assign(key.shadow.camera,{left:-9,right:9,top:9,bottom:-9,near:.1,far:30});
    scene.add(fill,key); sceneLights.push(fill,key);
    const cube = new THREE.BoxGeometry(1,1,1); geometries.add(cube);
    const matrix = new THREE.Matrix4(), position = new THREE.Vector3(), scale = new THREE.Vector3();
    for(const [name,color] of Object.entries(room.materials)) {
      const definitions = room.assemblies.filter(item=>item.material===name);
      const material = new THREE.MeshStandardMaterial({color,roughness:name==='wood'?.85: name==='paper'?1:.95,metalness:0}); materials.add(material);
      const mesh = new THREE.InstancedMesh(cube,material,definitions.length);
      definitions.forEach((item,index)=>{ matrix.compose(position.fromArray(item.position),new THREE.Quaternion(),scale.fromArray(item.size)); mesh.setMatrixAt(index,matrix); });
      mesh.castShadow = true; mesh.receiveShadow = true; mesh.userData.stations = definitions.map(item=>item.station);
      scene.add(mesh); targets.push(mesh);
    }
    const rimMaterial = new THREE.MeshStandardMaterial({color:'#edbd68',roughness:1}); materials.add(rimMaterial);
    const rim = new THREE.Mesh(cube,rimMaterial); rim.scale.set(2.35,.06,1.5); scene.add(rim);
    function apply(next) {
      if(disposed) return;
      view = next; const anchor = next && room.stationAnchors[next.station];
      rim.visible = !!anchor; if(anchor) rim.position.set(anchor[0],.1,anchor[2]); requestFrame();
    }
    listen('pointerdown',event=>{ pointer = {x:event.clientX,y:event.clientY,id:event.pointerId,view}; });
    listen('pointercancel',()=>{ pointer=null; });
    listen('pointerup',event=>{
      const start=pointer; pointer=null;
      if(!start || start.id!==event.pointerId || start.view!==view || Math.hypot(start.x-event.clientX,start.y-event.clientY)>6) return;
      const r=renderer.domElement.getBoundingClientRect(); cursor.set((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1);
      raycaster.setFromCamera(cursor,camera);
      const hits=raycaster.intersectObjects(targets,false);
      const station=hits[0]?.object.userData.stations[hits[0]?.instanceId];
      if(station) onPick(station);
    });
    listen('webglcontextlost',event=>{ event.preventDefault(); onFailure('context-lost'); });
    container.append(renderer.domElement);
    apply(view,[]);
    resize({width:container.clientWidth,height:container.clientHeight,pixelRatio:devicePixelRatio});
    if(raf!==null) cancelAnimationFrame(raf); raf = null; draw();
    return { apply, resize, setSuspended(value) { suspended=value; if(value && raf!==null) { cancelAnimationFrame(raf); raf=null; } else if(!value) requestFrame(); },
      setReducedMotion(value) { reducedMotion=value; requestFrame(); }, dispose };
  } catch(error) { dispose(); throw error; }
}
