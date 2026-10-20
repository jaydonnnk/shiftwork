import * as THREE from './vendor/three-r180/three.module.js';
import { roomDefinitions } from './workplace-rooms.js';

export function createWorkplaceScene({ container, view, tier, reducedMotion, onPick, onFailure }) {
  let renderer, disposed = false, suspended = false, raf = null, pointer = null, lastDraw = -Infinity, pulse = null, indicatorMaterial = null;
  let comparisonPulse = null, selectionPulse = null, plateMaterial = null, wallTrace = null, wallMaterial = null, traceMaterial = null, traceLine = null;
  let handoverMaterial = null, laterMaterial = null;
  let ownerMarker = null, routingLabel = null, routingTravel = null;
  const candidateMaterials = {}, routingMaterials = {}, northlineMarkers = {}, geometries = new Set(), materials = new Set(), targets = [];
  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-8,8,6,-6,.1,100);
  camera.position.set(12,11,14); camera.lookAt(0,.8,0);
  const raycaster = new THREE.Raycaster(), cursor = new THREE.Vector2();
  const room = roomDefinitions[view.context.board];
  if (!room) throw new Error('Unsupported room');
  const listeners = [];
  const listen = (type,fn) => { renderer.domElement.addEventListener(type,fn); listeners.push([type,fn]); };
  function settlePulse() { pulse = null; if (indicatorMaterial) indicatorMaterial.emissiveIntensity = 0; }
  function settleComparisonPulse() { comparisonPulse = null; for (const material of Object.values(candidateMaterials)) material.emissiveIntensity = 0; }
  function settleSelectionPulse() { selectionPulse = null; if (plateMaterial) plateMaterial.emissiveIntensity = 0; }
  function settleWallTrace() { wallTrace = null; if (routingTravel) ownerMarker.position.copy(routingTravel.to); routingTravel = null; if (traceLine) traceLine.visible = false; if (traceMaterial) traceMaterial.opacity = 0; if (wallMaterial) wallMaterial.emissiveIntensity = 0; }
  function settleAllPulses() { settlePulse(); settleComparisonPulse(); settleSelectionPulse(); settleWallTrace(); }
  function draw(now = performance.now()) {
    raf = null;
    if (disposed || suspended) return;
    if (tier === 'compact' && now - lastDraw < 1000 / 30 - .2) { raf = requestAnimationFrame(draw); return; }
    lastDraw = now;
    if (pulse) {
      const progress = (now - pulse.start) / 160;
      if (progress >= 1) settlePulse();
      else indicatorMaterial.emissiveIntensity = .8 * (1 - progress);
    }
    if (comparisonPulse) {
      const progress = (now - comparisonPulse.start) / comparisonPulse.duration;
      if (progress >= 1) settleComparisonPulse();
      else for (const material of Object.values(candidateMaterials)) material.emissiveIntensity = .8 * (1 - progress);
    }
    if (selectionPulse) {
      const progress = (now - selectionPulse.start) / selectionPulse.duration;
      if (progress >= 1) settleSelectionPulse();
      else if (plateMaterial) plateMaterial.emissiveIntensity = .8 * (1 - progress);
    }
    if (wallTrace) {
      const progress = (now - wallTrace.start) / wallTrace.duration;
      if (progress >= 1) settleWallTrace();
      else {
        if (routingTravel) ownerMarker.position.lerpVectors(routingTravel.from, routingTravel.to, Math.min(1, progress));
        if (traceMaterial) traceMaterial.opacity = .9 * (1 - progress);
        if (wallMaterial) wallMaterial.emissiveIntensity = .6 * (1 - progress);
      }
    }
    if (routingLabel && !routingLabel.hidden) {
      const point = ownerMarker.position.clone().project(camera);
      routingLabel.style.left = `${(point.x + 1) * 50}%`;
      routingLabel.style.top = `${(1 - point.y) * 50}%`;
    }
    try { renderer.render(scene, camera); }
    catch { onFailure('render-failed'); }
    if (pulse || comparisonPulse || selectionPulse || wallTrace) requestFrame();
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
    settleAllPulses();
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
    routingLabel?.remove(); routingLabel = null;
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
    const wheel = room.assemblies.some(item=>item.shape==='wheel') ? new THREE.TorusGeometry(.5,.035,6,24) : null;
    if(wheel) geometries.add(wheel);
    const matrix = new THREE.Matrix4(), position = new THREE.Vector3(), scale = new THREE.Vector3(), rotation = new THREE.Quaternion();
    for(const [name,color] of Object.entries(room.materials)) {
      const metal = ['metal','steel'].includes(name);
      const material = new THREE.MeshStandardMaterial({color,roughness:metal?.65:name==='wood'?.85: name==='paper'?1:.95,metalness:metal?.15:0}); materials.add(material);
      for(const shape of ['box','wheel']) {
        const definitions = room.assemblies.filter(item=>item.material===name && (item.shape ?? 'box')===shape);
        if(!definitions.length) continue;
        const mesh = new THREE.InstancedMesh(shape==='wheel'?wheel:cube,material,definitions.length);
        definitions.forEach((item,index)=>{ rotation.setFromEuler(new THREE.Euler(...(item.rotation ?? [0,0,0]))); matrix.compose(position.fromArray(item.position),rotation,scale.fromArray(item.size)); mesh.setMatrixAt(index,matrix); });
        mesh.castShadow = true; mesh.receiveShadow = true; mesh.userData.stations = definitions.map(item=>item.station);
        scene.add(mesh); targets.push(mesh);
      }
    }
    const rimMaterial = new THREE.MeshStandardMaterial({color:'#edbd68',roughness:1}); materials.add(rimMaterial);
    const rim = new THREE.Mesh(cube,rimMaterial); rim.scale.set(2.35,.06,1.5); scene.add(rim);
    indicatorMaterial = new THREE.MeshStandardMaterial({color:'#6c5943',emissive:'#000000',emissiveIntensity:0,roughness:1}); materials.add(indicatorMaterial);
    const indicator = new THREE.Mesh(cube,indicatorMaterial);
    indicator.position.fromArray(room.anchors?.indicator ?? [.7,1.5,2.88]); indicator.scale.set(.78,.32,.04); scene.add(indicator);
    for (const [label, anchor] of [['A', room.anchors?.candidateA], ['B', room.anchors?.candidateB]]) {
      if (!anchor) continue;
      const material = new THREE.MeshStandardMaterial({color:'#6c5943',emissive:'#000000',emissiveIntensity:0,roughness:1});
      materials.add(material); candidateMaterials[label] = material;
      const marker = new THREE.Mesh(cube, material);
      marker.position.fromArray(anchor); marker.scale.set(.55,.05,.4); scene.add(marker);
    }
    if (room.anchors?.plate) {
      plateMaterial = new THREE.MeshStandardMaterial({color:'#263443',emissive:'#000000',emissiveIntensity:0,roughness:1});
      materials.add(plateMaterial);
      const plate = new THREE.Mesh(cube, plateMaterial);
      plate.position.fromArray(room.anchors.plate); plate.scale.set(.8,.05,.42); scene.add(plate);
    }
    wallMaterial = new THREE.MeshStandardMaterial({color:'#48617a',emissive:'#000000',emissiveIntensity:0,roughness:1});
    materials.add(wallMaterial);
    const wallPanel = new THREE.Mesh(cube, wallMaterial);
    wallPanel.position.fromArray(room.anchors?.wallPanel ?? [4,1.9,-2.69]);
    wallPanel.scale.fromArray(room.anchors?.wallSize ?? [2.45,1.35,.04]); scene.add(wallPanel);
    for (const [kind, anchor] of [['OWNER_ASSIGNED', room.anchors?.owner], ['SLA_CLOCK_STARTED', room.anchors?.clock], ['HANDOFF_ESCALATED', room.anchors?.handoff]]) {
      if (!anchor) continue;
      const material = new THREE.MeshStandardMaterial({color:'#35495e',roughness:.65,metalness:.15});
      materials.add(material); routingMaterials[kind] = material;
      const marker = new THREE.Mesh(cube,material);
      marker.position.fromArray(anchor); marker.scale.set(.3,.16,.16); scene.add(marker);
      if (kind === 'OWNER_ASSIGNED') {
        ownerMarker = marker;
        routingLabel = document.createElement('span');
        routingLabel.className = 'workplace-routing-label';
        routingLabel.setAttribute('aria-hidden', 'true'); routingLabel.hidden = true;
        container.append(routingLabel);
      }
    }
    for(const [kind,anchor] of [['BOOKING_COMMITTED',room.anchors?.booking],['ROLLOUT_APPROVED',room.anchors?.approval],
      ['HANDOVER_DECLARED',room.anchors?.declaration],['ESCALATION_TO_HUMAN',room.anchors?.escalation],['COUNTER_FOLLOWUP_RECORDED',room.anchors?.followup]]) {
      if(!anchor) continue;
      const material = new THREE.MeshStandardMaterial({color:'#edbd68',roughness:1}); materials.add(material);
      const marker = new THREE.Mesh(cube,material); marker.position.fromArray(anchor); marker.scale.set(.32,.18,.14);
      marker.visible=false; scene.add(marker); northlineMarkers[kind]=marker;
    }
    if (room.anchors?.handover) {
      handoverMaterial = new THREE.MeshStandardMaterial({color:'#6c5943',emissive:'#000000',emissiveIntensity:0,roughness:1});
      materials.add(handoverMaterial);
      const handoverCard = new THREE.Mesh(cube, handoverMaterial);
      handoverCard.position.fromArray(room.anchors.handover); handoverCard.scale.set(.7,.05,.48); scene.add(handoverCard);
    }
    if (room.anchors?.later) {
      laterMaterial = new THREE.MeshStandardMaterial({color:'#6c5943',emissive:'#000000',emissiveIntensity:0,roughness:1});
      materials.add(laterMaterial);
      const laterMarker = new THREE.Mesh(cube, laterMaterial);
      laterMarker.position.fromArray(room.anchors.later); laterMarker.scale.set(.45,.05,.35); scene.add(laterMarker);
    }
    if (room.anchors?.plate && room.anchors?.wall) {
      const traceGeometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(...room.anchors.plate), new THREE.Vector3(...room.anchors.wall)]);
      geometries.add(traceGeometry);
      traceMaterial = new THREE.LineBasicMaterial({color:'#edbd68',transparent:true,opacity:0});
      materials.add(traceMaterial);
      traceLine = new THREE.Line(traceGeometry, traceMaterial);
      traceLine.visible = false; scene.add(traceLine);
    }
    const testColors = {RESERVED:'#edbd68',RUNNING:'#91acb9',COMPLETE:'#8fbf9f',FAILED:'#d98a7a'};
    function apply(next, transitions = []) {
      if(disposed) return false;
      let startedConsequence = false;
      view = next; const anchor = next && room.stationAnchors[next.station];
      rim.visible = !!anchor; if(anchor) rim.position.set(anchor[0],.1,anchor[2]);
      const trialState = next?.tests?.diagnostic?.trials?.[0]?.state;
      indicatorMaterial.color.set(testColors[trialState] ?? '#6c5943');
      const comparison = next?.tests?.later ?? next?.tests?.comparison;
      for (const [label, material] of Object.entries(candidateMaterials)) {
        const candidate = comparison?.candidates?.find(item => item.label === label);
        material.color.set(candidate?.eligible === true ? '#8fbf9f' : candidate?.eligible === false ? '#d98a7a' : '#6c5943');
      }
      if (plateMaterial) plateMaterial.color.set(next?.operating ? '#edbd68' : '#263443');
      if (handoverMaterial) handoverMaterial.color.set(next?.consistency === 'conflict' ? '#263443' :
        next?.inheritance?.selectionId && next?.operating ? '#edbd68' : '#6c5943');
      if (laterMaterial) laterMaterial.color.set(next?.consistency === 'conflict' ? '#263443' :
        next?.tests?.later ? '#91acb9' : '#6c5943');
      const currentWallEvents = (next?.consequences?.events ?? []).filter(event => event.source === 'current');
      const negativeWall = currentWallEvents.some(event => event.meaning === 'negative' || event.meaning === 'pending');
      if (wallMaterial) wallMaterial.color.set(next?.consistency === 'conflict' ? '#263443' :
        negativeWall ? '#d98a7a' : currentWallEvents.some(event => event.linkState === 'linked') ? '#8fbf9f' : '#48617a');
      for (const [kind, material] of Object.entries(routingMaterials)) {
        const records = (next?.consequences?.events ?? []).filter(event => event.type === kind && event.signalRef && ['linked', 'historical'].includes(event.linkState));
        const ownerCounts = new Map();
        for (const event of records) ownerCounts.set(event.signalRef, (ownerCounts.get(event.signalRef) ?? 0) + 1);
        const ownershipProblem = kind === 'OWNER_ASSIGNED' && records.some(event => !event.owner || ownerCounts.get(event.signalRef) > 1);
        material.color.set(ownershipProblem ? '#d98a7a' : records.length ? '#d7bb75' : '#35495e');
      }
      for(const [kind,marker] of Object.entries(northlineMarkers)) {
        const records=(next?.consequences?.events ?? []).filter(event=>event.type===kind && event.synthetic===true &&
          (kind==='HANDOVER_DECLARED'
            ? event.source==='administrative' && event.linkState==='none' && Boolean(event.versionId)
            : ['linked','historical'].includes(event.linkState)));
        marker.userData.recordCount=records.length;
        marker.visible=next?.consistency!=='conflict' && records.length>0;
      }
      if (!reducedMotion && transitions.some(item => item.kind === 'test-update')) {
        pulse = { start: performance.now() };
        indicatorMaterial.emissive.set('#edbd68');
        indicatorMaterial.emissiveIntensity = .8;
      }
      if (!reducedMotion && transitions.some(item => item.kind === 'comparison-update')) {
        comparisonPulse = { start: performance.now(), duration: 160 };
        for (const material of Object.values(candidateMaterials)) { material.emissive.set('#edbd68'); material.emissiveIntensity = .8; }
      }
      if (!reducedMotion && transitions.some(item => item.kind === 'selection-update')) {
        selectionPulse = { start: performance.now(), duration: 180 };
        if (plateMaterial) { plateMaterial.emissive.set('#edbd68'); plateMaterial.emissiveIntensity = .8; }
      }
      const arrival = transitions.find(item => item.kind === 'linked-consequence');
      if (!reducedMotion && !wallTrace && arrival && next?.consistency !== 'conflict') {
        wallTrace = { start: performance.now(), duration: 320, count: arrival.count ?? 1 };
        if (traceLine) traceLine.visible = true;
        if (traceMaterial) traceMaterial.opacity = .9;
        if (wallMaterial) { wallMaterial.emissive.set('#edbd68'); wallMaterial.emissiveIntensity = .6; }
        startedConsequence = true;
      }
      if (ownerMarker) {
        const owners = (next?.consequences?.events ?? []).filter(event => event.type === 'OWNER_ASSIGNED' && event.signalRef && ['linked', 'historical'].includes(event.linkState));
        const unique = owners.filter(event => event.owner && owners.filter(other => other.signalRef === event.signalRef).length === 1);
        const assigned = unique.find(event => arrival?.publicRefs.includes(event.id) && event.source === 'current' && event.linkState === 'linked' && event.synthetic === true);
        const labelled = assigned ?? unique.find(event => event.id === routingLabel.dataset.eventId) ?? unique.at(-1);
        if (routingTravel && labelled?.id !== routingLabel.dataset.eventId) {
          ownerMarker.position.copy(routingTravel.to); routingTravel = null;
        }
        routingLabel.hidden = !labelled || next?.consistency === 'conflict';
        routingLabel.textContent = labelled ? `${labelled.signalRef} · ${labelled.owner} · Synthetic recorded assignment` : '';
        routingLabel.dataset.eventId = labelled?.id ?? '';
        if (assigned && startedConsequence && !suspended) {
          routingTravel = {from: new THREE.Vector3(...room.anchors.plate), to: new THREE.Vector3(...room.anchors.owner)};
          ownerMarker.position.copy(routingTravel.from);
        } else if (!routingTravel) ownerMarker.position.fromArray(room.anchors.owner);
        if ((!labelled && routingTravel) || next?.consistency === 'conflict') settleWallTrace();
      }
      requestFrame();
      return startedConsequence;
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
    return { apply, resize, setSuspended(value) { suspended=value; if(value) settleAllPulses(); if(value && raf!==null) { cancelAnimationFrame(raf); raf=null; } else if(!value) requestFrame(); },
      setReducedMotion(value) { reducedMotion=value; if(value) settleAllPulses(); requestFrame(); }, dispose };
  } catch(error) { dispose(); throw error; }
}
