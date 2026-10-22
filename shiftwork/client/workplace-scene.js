import * as THREE from './vendor/three-r180/three.module.js';
import { roomDefinitions } from './workplace-rooms.js';

export function createWorkplaceScene({ container, view, tier, reducedMotion, onPick, onFailure, onAnchors }) {
  let renderer, disposed = false, suspended = false, raf = null, pointer = null, lastDraw = -Infinity, pulse = null, indicatorMaterial = null;
  let comparisonPulse = null, selectionPulse = null, plateMaterial = null, wallTrace = null, wallMaterial = null, traceMaterial = null, traceLine = null;
  let handoverMaterial = null, laterMaterial = null;
  let ownerMarker = null, routingLabel = null, routingTravel = null;
  let size = null, inspector = { open: false, widthPx: 0 }, anchorsDirty = true;
  let environment = null, attentionRing = null, ambientActive = false, replayRunning = false;
  let cameraEase = null, inspectorReady = false, drawInset = 0;
  const drawTarget = new THREE.Vector3();
  const lampMeshes = {}, lampMaterials = {};
  const candidateMaterials = {}, routingMaterials = {}, northlineMarkers = {}, geometries = new Set(), materials = new Set(), targets = [];
  const roundedCache = new Map();
  const scene = new THREE.Scene();
  const raycaster = new THREE.Raycaster(), cursor = new THREE.Vector2();
  const room = roomDefinitions[view.context.board];
  if (!room) throw new Error('Unsupported room');
  // Visual spec section 11.4: one fixed perspective pose per room; only the distance is fitted.
  const pose = room.camera, target = new THREE.Vector3(...room.cameraTarget);
  const camera = new THREE.PerspectiveCamera(pose.fov,1,.1,100);
  const azimuth = THREE.MathUtils.degToRad(pose.azimuth), elevation = THREE.MathUtils.degToRad(pose.elevation);
  const direction = new THREE.Vector3(Math.sin(azimuth)*Math.cos(elevation),Math.sin(elevation),Math.cos(azimuth)*Math.cos(elevation));
  camera.position.copy(target).add(direction); camera.lookAt(target); drawTarget.copy(target);
  scene.fog = new THREE.Fog(room.fog,1,2);
  const listeners = [];
  const listen = (type,fn) => { renderer.domElement.addEventListener(type,fn); listeners.push([type,fn]); };
  function settlePulse() { pulse = null; if (indicatorMaterial) indicatorMaterial.emissiveIntensity = 0; }
  function settleComparisonPulse() { comparisonPulse = null; for (const material of Object.values(candidateMaterials)) material.emissiveIntensity = 0; }
  function settleSelectionPulse() { selectionPulse = null; if (plateMaterial) plateMaterial.emissiveIntensity = 0; }
  function settleWallTrace() { wallTrace = null; if (routingTravel) ownerMarker.position.copy(routingTravel.to); routingTravel = null; if (traceLine) traceLine.visible = false; if (traceMaterial) traceMaterial.opacity = 0; if (wallMaterial) wallMaterial.emissiveIntensity = 0; }
  function settleAllPulses() { settlePulse(); settleComparisonPulse(); settleSelectionPulse(); settleWallTrace(); }
  function ambientEligible() { return ambientActive && tier !== 'compact' && !reducedMotion && !suspended && !replayRunning; }
  function settleAmbient() {
    attentionRing?.scale.setScalar(1);
    for(const tone of ['attention','fail']) lampMaterials[tone]?.color.set(tone==='attention'?'#ffb648':'#ff5a4e');
  }
  function setAmbient(active) {
    if(disposed || ambientActive===active) return;
    ambientActive=active;
    if(!ambientEligible()) settleAmbient();
    requestFrame();
  }
  function cameraFrame(now) {
    if(!cameraEase) return;
    const progress=Math.min(1,(now-cameraEase.start)/180), eased=progress*progress*(3-2*progress);
    camera.position.lerpVectors(cameraEase.fromPosition,cameraEase.toPosition,eased);
    drawTarget.lerpVectors(cameraEase.fromTarget,cameraEase.toTarget,eased);
    drawInset=THREE.MathUtils.lerp(cameraEase.fromInset,cameraEase.toInset,eased);
    camera.lookAt(drawTarget);
    camera.near=progress===1?cameraEase.toNear:cameraEase.near; camera.far=progress===1?cameraEase.toFar:cameraEase.far;
    viewOffset(drawInset,size.width,size.height);
    camera.updateProjectionMatrix(); camera.updateMatrixWorld(); anchorsDirty=true;
    if(progress===1) cameraEase=null;
  }
  function settleCamera() { if(cameraEase) cameraFrame(cameraEase.start+180); }
  function draw(now = performance.now()) {
    raf = null;
    if (disposed || suspended) return;
    if ((tier === 'compact' || (ambientEligible() && !pulse && !comparisonPulse && !selectionPulse && !wallTrace && !cameraEase)) && now - lastDraw < 1000 / 30 - .2) { raf = requestAnimationFrame(draw); return; }
    lastDraw = now;
    cameraFrame(now);
    if(ambientEligible()) {
      const wave=(1-Math.cos(now*2*Math.PI/2500))/2;
      attentionRing?.scale.setScalar(1+.05*wave);
      for(const tone of ['attention','fail']) lampMaterials[tone]?.color.set(tone==='attention'?'#ffb648':'#ff5a4e').multiplyScalar(1-.15*wave);
    }
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
    if (anchorsDirty && !disposed) { anchorsDirty = false; onAnchors?.(anchorPositions()); }
    if (pulse || comparisonPulse || selectionPulse || wallTrace || cameraEase || ambientEligible()) requestFrame();
  }
  function requestFrame() { if (!disposed && !suspended && raf === null) raf = requestAnimationFrame(draw); }
  function resize({width,height,pixelRatio}) {
    if(disposed || width<=0 || height<=0) return;
    renderer.setPixelRatio(tierPixelRatio(width,height,pixelRatio));
    renderer.setSize(width,height,false);
    size = {width,height}; fit();
  }
  // Gate 3 section 13.8: standard DPR at most 2, lowered so the backing store stays
  // within 1,850,000 pixels (backtracked 2026-10-22 from 4,200,000); compact at most 1.
  function tierPixelRatio(width,height,requested) {
    if(tier==='compact') return Math.min(requested,1);
    return Math.min(requested,2,Math.sqrt(1850000/(width*height)));
  }
  // The inspector covers the left of the stage, so the room is fitted to the
  // uncovered width and the view offset centres it there. Same pose; the camera
  // only moves along its fixed direction so every bound corner keeps the margin.
  function viewOffset(inset,width,height) {
    if(inset>0) camera.setViewOffset(width,height,-inset/2,0,width,height); else camera.clearViewOffset();
  }
  function fit(animate = false) {
    const fromPosition=camera.position.clone(), fromTarget=drawTarget.clone(), fromInset=drawInset, fromNear=camera.near, fromFar=camera.far;
    if(disposed || !size) return;
    const {width,height} = size;
    const inset = inspector.open && size.width>=761 ? Math.min(Math.max(0,inspector.widthPx),width*.6) : 0;
    camera.position.copy(target).add(direction); camera.lookAt(target); camera.updateMatrixWorld();
    const inverse = camera.matrixWorldInverse, keep = 1-pose.margin;
    const tanV = Math.tan(THREE.MathUtils.degToRad(pose.fov)/2), tanH = tanV*(width-inset)/height;
    let distance = 0, reach = 0;
    for(const x of [room.bounds.min[0],room.bounds.max[0]]) for(const y of [room.bounds.min[1],room.bounds.max[1]]) for(const z of [room.bounds.min[2],room.bounds.max[2]]) {
      const p = new THREE.Vector3(x,y,z).applyMatrix4(inverse);
      // At distance d the corner's depth is d-1-p.z; it must cover |p.x| and |p.y| inside the margin.
      distance = Math.max(distance, 1+p.z+Math.abs(p.x)/(tanH*keep), 1+p.z+Math.abs(p.y)/(tanV*keep));
      reach = Math.max(reach, Math.hypot(x-target.x,y-target.y,z-target.z));
    }
    camera.position.copy(target).addScaledVector(direction,distance); camera.lookAt(target);
    camera.near = Math.max(.1,distance-reach-1); camera.far = distance+reach+1; camera.aspect = width/height;
    scene.fog.near = distance*1.4; scene.fog.far = distance*2.6;
    viewOffset(inset,width,height);
    camera.updateProjectionMatrix();
    cameraEase=null;
    if(animate && size.width>=761 && !reducedMotion && !suspended) {
      cameraEase={start:performance.now(),fromPosition,fromTarget,fromInset,toPosition:camera.position.clone(),toTarget:target.clone(),toInset:inset,near:Math.min(fromNear,camera.near),far:Math.max(fromFar,camera.far),toNear:camera.near,toFar:camera.far};
      cameraFrame(cameraEase.start);
    } else { drawTarget.copy(target); drawInset=inset; }
    anchorsDirty = true; requestFrame();
  }
  // Gate 3 section 13.3: a cached first-party rounded box, one bevel segment.
  // Too-small parts and the compact tier use the shared unit box.
  function roundedBox(width,height,depth,radius,tierName) {
    const corner = radius/2, flat = [width-2*(radius+corner),height-2*(radius+corner),depth-2*radius];
    if(tierName==='compact' || flat.some(value=>value<=.01)) return null;
    const key = `${width},${height},${depth},${radius}`;
    if(roundedCache.has(key)) return roundedCache.get(key);
    const w = flat[0]/2+corner, h = flat[1]/2+corner, shape = new THREE.Shape();
    shape.moveTo(-w+corner,-h); shape.lineTo(w-corner,-h); shape.absarc(w-corner,-h+corner,corner,-Math.PI/2,0);
    shape.lineTo(w,h-corner); shape.absarc(w-corner,h-corner,corner,0,Math.PI/2);
    shape.lineTo(-w+corner,h); shape.absarc(-w+corner,h-corner,corner,Math.PI/2,Math.PI);
    shape.lineTo(-w,-h+corner); shape.absarc(-w+corner,-h+corner,corner,Math.PI,Math.PI*1.5);
    const geometry = new THREE.ExtrudeGeometry(shape,{depth:flat[2],bevelEnabled:true,bevelThickness:radius,bevelSize:radius,bevelSegments:1,curveSegments:3});
    geometry.translate(0,0,-flat[2]/2);
    geometries.add(geometry); roundedCache.set(key,geometry);
    return geometry;
  }
  // Gate 3 section 13.3: an original light box with three emissive panels, converted
  // once to a PMREM target. The generator and the source scene are released here.
  function buildStudioEnvironment(renderer) {
    const studio = new THREE.Scene(), unit = new THREE.BoxGeometry(1,1,1);
    const shell = new THREE.MeshBasicMaterial({color:'#8c8478',side:THREE.BackSide});
    const glow = new THREE.MeshBasicMaterial({color:new THREE.Color(4,3.8,3.5)});
    const box = new THREE.Mesh(unit,shell); box.scale.set(16,8,16); box.position.y = 3; studio.add(box);
    for(const [position,scale] of [[[0,6.9,0],[8,.1,5]],[[-7.9,3.5,2],[.1,3,5]],[[3,3.5,-7.9],[5,3,.1]]]) {
      const panel = new THREE.Mesh(unit,glow); panel.position.fromArray(position); panel.scale.fromArray(scale); studio.add(panel);
    }
    const generator = new THREE.PMREMGenerator(renderer);
    try { return generator.fromScene(studio,0,.1,100,{size:128}); }
    finally { generator.dispose(); unit.dispose(); shell.dispose(); glow.dispose(); studio.clear(); }
  }
  function setInspector(value) {
    const next = { open: !!value?.open, widthPx: value?.open ? Number(value.widthPx) || 0 : 0 };
    const changed=next.open!==inspector.open || next.widthPx!==inspector.widthPx;
    inspector=next;
    if(changed) fit(inspectorReady);
    inspectorReady=true;
  }
  function anchorPositions() {
    const positions = {};
    if(!size) return positions;
    for(const [stationId,anchor] of Object.entries(room.stationAnchors)) {
      const point = new THREE.Vector3(...anchor).project(camera);
      const x = (point.x+1)/2*size.width, y = (1-point.y)/2*size.height;
      positions[stationId] = { x, y, visible: point.z>=-1 && point.z<=1 && x>=0 && x<=size.width && y>=0 && y<=size.height };
    }
    return positions;
  }
  function dispose() {
    if(disposed) return; disposed = true;
    settleAllPulses(); settleAmbient(); cameraEase=null; ambientActive=false;
    if(raf!==null) cancelAnimationFrame(raf); raf = null;
    for(const [type,fn] of listeners) renderer?.domElement.removeEventListener(type,fn);
    listeners.length = 0; targets.length = 0;
    scene.clear();
    for(const g of geometries) g.dispose(); for(const m of materials) m.dispose();
    geometries.clear(); materials.clear(); roundedCache.clear();
    scene.environment = null; environment?.dispose(); environment = null;
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
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1;
    renderer.setClearColor(room.fog);
    renderer.debug.onShaderError = () => onFailure('shader-failed');
    renderer.shadowMap.enabled = tier !== 'compact'; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    const fill = new THREE.HemisphereLight('#f3efe6','#8a7b66',1.2);
    const key = new THREE.DirectionalLight('#fff1d8',2.2); key.position.set(-6,10,6);
    key.castShadow = tier !== 'compact'; key.shadow.mapSize.set(1024,1024);
    Object.assign(key.shadow.camera,{left:-9,right:9,top:9,bottom:-9,near:.1,far:30});
    scene.add(fill,key); sceneLights.push(fill,key);
    if(tier !== 'compact') { environment = buildStudioEnvironment(renderer); scene.environment = environment.texture; scene.environmentIntensity = .45; }
    const cube = new THREE.BoxGeometry(1,1,1); geometries.add(cube);
    const wheel = room.assemblies.some(item=>item.shape==='wheel') ? new THREE.TorusGeometry(.5,.035,6,24) : null;
    if(wheel) geometries.add(wheel);
    const matrix = new THREE.Matrix4(), position = new THREE.Vector3(), scale = new THREE.Vector3(), rotation = new THREE.Quaternion();
    for(const [name,color] of Object.entries(room.materials)) {
      // Visual spec section 11.3 material values.
      const metal = ['metal','steel'].includes(name);
      const roughness = metal ? .42 : ['wood','floor','shelf'].includes(name) ? .7 : name==='paper' ? .9 : ['enamel','navy','edge'].includes(name) ? .55 : .85;
      const material = new THREE.MeshStandardMaterial({color,roughness,metalness:metal?.3:0}); materials.add(material);
      // One instanced mesh per geometry: the shared unit box is scaled per part, a rounded box is built at size.
      const groups = new Map();
      for(const item of room.assemblies.filter(item=>item.material===name)) {
        const geometry = (item.shape ?? 'box')==='wheel' ? wheel : roundedBox(...item.size,.05,tier) ?? cube;
        if(!groups.has(geometry)) groups.set(geometry,[]);
        groups.get(geometry).push(item);
      }
      for(const [geometry,definitions] of groups) {
        const mesh = new THREE.InstancedMesh(geometry,material,definitions.length);
        definitions.forEach((item,index)=>{ rotation.setFromEuler(new THREE.Euler(...(item.rotation ?? [0,0,0]))); matrix.compose(position.fromArray(item.position),rotation,geometry===cube||geometry===wheel?scale.fromArray(item.size):scale.set(1,1,1)); mesh.setMatrixAt(index,matrix); });
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
    // Static status lamps (Gate 3 section 13.3): unlit, never tone mapped, one shared material per colour.
    // The tag beside each lamp carries the same state in words.
    const lampColors = {fail:'#ff5a4e',attention:'#ffb648',pass:'#4fd17a',idle:'#9aa6b2'};
    if(room.lampAnchors) {
      const bulb = new THREE.SphereGeometry(.12,16,12); geometries.add(bulb);
      for(const [tone,color] of Object.entries(lampColors)) { const material = new THREE.MeshBasicMaterial({color,toneMapped:false}); materials.add(material); lampMaterials[tone] = material; }
      for(const [stationId,anchor] of Object.entries(room.lampAnchors)) {
        const lampMesh = new THREE.Mesh(bulb,lampMaterials.idle); lampMesh.position.fromArray(anchor); scene.add(lampMesh); lampMeshes[stationId] = lampMesh;
      }
    }
    const ringGeometry=new THREE.TorusGeometry(.82,.035,6,48); geometries.add(ringGeometry);
    const ringMaterial=new THREE.MeshBasicMaterial({color:'#ffb648',toneMapped:false}); materials.add(ringMaterial);
    attentionRing=new THREE.Mesh(ringGeometry,ringMaterial); attentionRing.rotation.x=-Math.PI/2; scene.add(attentionRing);
    const testColors = {RESERVED:'#edbd68',RUNNING:'#91acb9',COMPLETE:'#8fbf9f',FAILED:'#d98a7a'};
    function apply(next, transitions = []) {
      if(disposed) return false;
      let startedConsequence = false;
      view = next; const anchor = next && room.stationAnchors[next.station];
      const attention=next?.consistency!=='conflict' && room.stationAnchors[next?.attention];
      attentionRing.visible=!!attention; attentionRing.userData.stationId=attention?next.attention:null;
      if(attention) attentionRing.position.set(attention[0],.12,attention[2]);
      if(transitions.some(item=>item.kind==='station-focus') && size?.width>=761) {
        const offset=new THREE.Vector3(...(anchor ?? room.cameraTarget)).sub(new THREE.Vector3(...room.cameraTarget)).clampLength(0,.3);
        target.fromArray(room.cameraTarget).add(offset); fit(true);
      }
      for(const [stationId,lampMesh] of Object.entries(lampMeshes)) lampMesh.material = lampMaterials[next?.lamps?.find(lamp=>lamp.stationId===stationId)?.tone] ?? lampMaterials.idle;
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
    return { apply, resize, setInspector, anchorPositions, setSuspended(value) { suspended=value; if(value) { settleAllPulses(); settleAmbient(); settleCamera(); } if(value && raf!==null) { cancelAnimationFrame(raf); raf=null; } else if(!value) requestFrame(); },
      setReducedMotion(value) { reducedMotion=value; if(value) { settleAllPulses(); settleAmbient(); settleCamera(); } requestFrame(); }, setAmbient, dispose };
  } catch(error) { dispose(); throw error; }
}
