// Original S29 Bellwether geometry. No reference artwork or imported models.
const assemblies = [];
const box = (material, position, size, station = null) => assemblies.push({ material, position, size, station });
box('floor', [0,-.15,0], [12,.3,9]);
box('wall', [0,1.6,-4.5], [12,3.2,.18]);
box('wall', [-6,1.6,0], [.18,3.2,9]);
// Navy trim (visual spec 11.3): cap rails on the cut wall edges and skirting at the floor.
box('edge', [0,3.24,-4.5], [12.04,.08,.24]);
box('edge', [-6,3.24,0], [.24,.08,9.04]);
box('edge', [0,.08,-4.38], [11.8,.16,.06]);
box('edge', [-5.88,.08,0], [.06,.16,8.8]);
box('edge', [0,-.3,4.5], [12,.2,.2]);
box('edge', [6,-.3,0], [.2,.2,9]);
// A back-wall bookcase has open shelves and irregular muted book groups.
for (const x of [-4.5,-2.8,-1.1]) {
  box('shelf', [x,1.35,-4.15], [1.5,2.7,.38]);
  for (const y of [.2,1.05,1.9,2.7]) box('wood', [x,y,-3.9], [1.6,.12,.7]);
  for (const y of [.62,1.47,2.32]) for(let n=0;n<4;n++) {
    box(n%2 ? 'paper' : 'enamel', [x-.5+n*.32,y,-3.85], [.18+(n%2)*.04,.55+(n%3)*.07,.38]);
  }
}
// Intake tray, operating console and independent assessment occupy separate positions.
for(const [x,z,station] of [[-4,2.5,'customers'],[0,1.1,'service'],[3.3,-.2,'evaluator']]) {
  box('wood',[x,1,z],[2.1,.22,1.25],station);
  box('enamel',[x,.48,z],[1.5,.95,.8],station);
  box('edge',[x,.05,z],[2.25,.09,1.4],station);
}
box('navy',[0,1.65,.8],[1.35,.9,.16],'service');
box('screen',[0,1.65,.91],[1.12,.65,.05],'service');
box('edge',[0,1.2,.8],[.22,.3,.22],'service');
box('paper',[0,1.14,1.55],[1.05,.04,.32],'service');
box('wood',[-4,1.2,2.5],[1.55,.18,.88],'customers');
box('paper',[-4,1.31,2.5],[1.14,.06,.64],'customers');
box('enamel',[3.3,1.4,-.2],[.85,.6,.65],'evaluator');
box('paper',[3.3,1.73,-.2],[.65,.04,.45],'evaluator');
box('navy',[2.1,.6,-.6],[.12,1.2,2.2],'evaluator');
// Diagnosis desk: a two-part cause and falsifier worksheet with no written hypothesis.
box('wood',[0,1,-2.5],[2.2,.22,1.25],'investigate');
box('enamel',[0,.48,-2.5],[1.55,.95,.8],'investigate');
box('edge',[0,.05,-2.5],[2.35,.09,1.4],'investigate');
box('paper',[-.42,1.14,-2.5],[.78,.05,.5],'investigate');
box('paper',[.42,1.14,-2.5],[.78,.05,.5],'investigate');
// Paired test bench: equal stands with a public indicator for the reported test state.
box('wood',[.7,.95,3],[2.6,.2,1.2],'compare');
box('edge',[.7,.05,3],[2.75,.09,1.35],'compare');
box('enamel',[-.15,.45,3],[.7,.8,.7],'compare');
box('enamel',[1.55,.45,3],[.7,.8,.7],'compare');
box('paper',[-.15,.9,3],[.5,.04,.4],'compare');
box('paper',[1.55,.9,3],[.5,.04,.4],'compare');
box('navy',[.7,1.5,2.75],[.95,.55,.08],'compare');
box('screen',[.7,1.5,2.82],[.8,.4,.03],'compare');
// Incident and consequence wall: one labelled tally board, never one object per event.
box('navy',[4,1.9,-2.8],[2.9,1.9,.18],'ledger');
box('wood',[4,1.0,-2.8],[3.0,.14,.52],'ledger');
box('paper',[3.35,2.15,-2.65],[.95,.5,.03],'ledger');
box('paper',[4.65,2.15,-2.65],[.95,.5,.03],'ledger');
box('paper',[3.35,1.52,-2.65],[.95,.5,.03],'ledger');
box('paper',[4.65,1.52,-2.65],[.95,.5,.03],'ledger');
// Owner desk: the committed requirements folder stays read only.
box('wood',[-3.7,1,-2.4],[2.0,.22,1.15],'owner');
box('enamel',[-3.7,.48,-2.4],[1.35,.95,.75],'owner');
box('paper',[-3.7,1.13,-2.4],[1.3,.05,.7],'owner');
box('paper',[-3.45,1.17,-2.4],[.55,.04,.48],'owner');
box('paper',[-2.95,1.16,-2.45],[.5,.04,.45],'owner');
// Read-only incident review tray beside the wall.
box('wood',[-4.2,.8,-.2],[1.4,.18,.8],'repair');
box('enamel',[-4.2,.38,-.2],[1.05,.65,.55],'repair');
box('paper',[-4.35,1,-.2],[.6,.06,.42],'repair');
box('paper',[-3.9,1.02,-.15],[.5,.05,.4],'repair');
// Handover shelf: original choice, retained alternative and inherited limits.
box('wood',[4,.4,2.5],[1.8,2.4,.35],'next');
for(const y of [.4,1.1,1.8]) box('wood',[4,y,2.3],[1.9,.1,.75],'next');
box('paper',[3.62,1.2,2.45],[.5,.05,.42],'next');
box('paper',[4.38,1.2,2.45],[.5,.05,.42],'next');
box('paper',[4,1.9,2.45],[.65,.05,.45],'next');

// Original Stonebridge routing room. The metal table branches toward stepped
// ownership lanes; no bookshop shelf, sales counter or borrowed asset is used.
const routing = [];
const routeBox = (material, position, size, station = null) => routing.push({material, position, size, station});
routeBox('floor', [0,-.15,0], [12,.3,9]);
routeBox('navy', [0,1.6,-4.5], [12,3.2,.18]);
routeBox('navy', [-6,1.6,0], [.18,3.2,9]);
for (const [position, size] of [[[0,-.3,4.5],[12,.2,.2]], [[6,-.3,0],[.2,.2,9]]]) routeBox('edge', position, size);
// Open signal rack with upright folders, rather than a queue of invented leads.
routeBox('metal', [-4,.55,2.2], [1.9,1.1,.8], 'signals');
routeBox('edge', [-4,.08,2.2], [2.1,.12,1], 'signals');
for (let n=0;n<4;n++) {
  routeBox('paper', [-4.65+n*.42,1.36,2.2], [.08,.62,.58], 'signals');
  routeBox('pin', [-4.65+n*.42,1.7,2.2], [.13,.1,.6], 'signals');
}
// Wall-mounted qualification sheet and its metal frame.
routeBox('metal', [-3.5,1.85,-2.5], [2.25,1.65,.16], 'rules');
routeBox('paper', [-3.5,1.85,-2.39], [1.98,1.37,.04], 'rules');
for (const x of [-4.15,-2.85]) routeBox('edge', [x,.65,-2.5], [.12,1.3,.2], 'rules');
for (const y of [1.48,1.85,2.22]) routeBox('lane', [-3.5,y,-2.34], [1.5,.07,.025], 'rules');
// Broad team routing table with two equal candidate stands and branching pins.
routeBox('metal', [0,1,.6], [4,.24,2.15], 'workflow');
for (const x of [-1.55,1.55]) routeBox('edge', [x,.5,.6], [.22,1,1.6], 'workflow');
routeBox('lane', [0,1.14,.75], [.12,.04,1.45], 'workflow');
for (const x of [-.85,.85]) {
  routeBox('lane', [x,1.14,.1], [1.7,.04,.12], 'workflow');
  routeBox('paper', [x,1.18,1.1], [.65,.06,.5], 'workflow');
  routeBox('pin', [x,1.18,.1], [.22,.1,.22], 'workflow');
}
routeBox('metal', [0,1.6,-.1], [1.05,.62,.12], 'workflow');
routeBox('screen', [0,1.6,-.02], [.86,.43,.025], 'workflow');
// Vertically separated owner lanes make the wall silhouette visibly stepped.
for (const [x,y,height] of [[2.65,1.3,1.65],[3.7,1.65,2.35],[4.75,2,3.05]]) {
  routeBox('lane', [x,y,-2], [.95,height,.22], 'wall');
  routeBox('metal', [x,y-height/2,-1.78], [1.02,.12,.65], 'wall');
  routeBox('paper', [x,y+.35,-1.85], [.65,.34,.035], 'wall');
}
routeBox('metal', [4.5,.5,.2], [1.65,.16,1], 'wall');
routeBox('edge', [4.5,.25,.2], [1.35,.5,.75], 'wall');
routeBox('paper', [4.5,.61,.2], [1.1,.06,.65], 'wall');

// Original Northline workshop. The bicycle, open permission lanes and slot rail
// have distinct silhouettes; all record labels remain in HTML.
const workshop = [];
const workshopPart = (material, position, size, station = null, shape = 'box', rotation = [0,0,0]) => workshop.push({material, position, size, station, shape, rotation});
workshopPart('floor',[0,-.15,0],[12,.3,9]);
workshopPart('wall',[0,1.6,-4.5],[12,3.2,.18]);
workshopPart('wall',[-6,1.6,0],[.18,3.2,9]);
workshopPart('edge',[0,-.3,4.5],[12,.2,.2]);
workshopPart('edge',[6,-.3,0],[.2,.2,9]);
// Repair counter and its requirements clipboard.
workshopPart('wood',[-4,.65,2.5],[2.4,1.3,1.1],'brief');
workshopPart('steel',[-4,1.34,2.5],[2.6,.14,1.25],'brief');
workshopPart('edge',[-4,1.45,2.5],[.8,.06,.85],'brief');
workshopPart('paper',[-4,1.49,2.5],[.65,.03,.68],'brief');
// Two read lanes and a separated write lane. The boundary grants no access.
for(const [x,width] of [[-4.45,.55],[-3.65,.55],[-2.6,.55]]) {
  workshopPart('steel',[x,1.55,-2.2],[width,.12,2.2],'map');
  workshopPart('paper',[x,1.65,-2.65],[width*.7,.08,.55],'map');
}
workshopPart('edge',[-3.13,1.75,-2.2],[.12,.5,2.5],'map');
for(const x of [-4.5,-2.6]) workshopPart('steel',[x,.75,-2.2],[.14,1.5,1.7],'map');
// Bicycle on a stand, beside the counter rather than on the integration bench.
for(const x of [-4.6,-2.9]) workshopPart('edge',[x,.8,.15],[1.35,1.35,1],'brief','wheel');
for(const [x,y,width,angle] of [[-4.16,.8,.9,0],[-3.38,.8,.9,0],[-4.03,1.19,1.15,1.03],[-3.43,1.19,1.15,-1.03],[-3.73,1.58,1.05,0]])
  workshopPart('tool',[x,y,.15],[width,.075,.075],'brief','box',[0,0,angle]);
workshopPart('steel',[-3.75,.8,.15],[.12,1.6,.12],'brief');
workshopPart('steel',[-3.75,.08,.15],[1.1,.16,1.3],'brief');
workshopPart('edge',[-4.25,1.7,.15],[.5,.1,.25],'brief');
workshopPart('tool',[-2.94,1.55,.15],[.12,.8,.12],'brief');
// Steel integration bench, equal candidate positions and learner worksheets.
workshopPart('steel',[0,1,.6],[2.8,.22,1.8],'bench');
for(const x of [-1.1,1.1]) workshopPart('edge',[x,.5,.6],[.15,1,1.55],'bench');
for(const x of [-.7,.7]) workshopPart('paper',[x,1.15,.9],[.65,.06,.55],'bench');
workshopPart('steel',[0,1.65,.05],[1,.65,.12],'bench');
workshopPart('screen',[0,1.65,.13],[.8,.45,.03],'bench');
// Independent acceptance fixture, separated from the learner's test bench.
workshopPart('steel',[3.5,.7,-1.5],[1.65,1.4,1.1],'acceptance');
workshopPart('tool',[3.5,1.5,-1.5],[1.8,.16,1.25],'acceptance');
for(const x of [2.85,4.15]) workshopPart('edge',[x,1.95,-1.8],[.12,.9,.12],'acceptance');
workshopPart('tool',[3.5,2.4,-1.8],[1.45,.12,.12],'acceptance');
workshopPart('paper',[3.5,1.62,-1.4],[.8,.08,.55],'acceptance');
// Pilot-slot rail: an aggregate recorded marker, never invented appointments.
for(const x of [2.8,4.8]) workshopPart('steel',[x,.9,2.2],[.12,1.8,.12],'rollout');
for(const y of [.85,1.65]) workshopPart('steel',[3.8,y,2.2],[2.3,.12,.12],'rollout');
for(const x of [3.15,3.8,4.45]) workshopPart('wood',[x,1.15,2.2],[.46,.55,.08],'rollout');
// Runbook shelf with open compartments and a separate human-review tray.
for(const x of [-1,1]) workshopPart('steel',[x,1.2,-3],[.13,2.4,.75],'handover');
for(const y of [.3,1.1,1.9]) workshopPart('wood',[0,y,-3],[2.15,.12,.85],'handover');
for(const x of [-.6,0,.6]) workshopPart('paper',[x,1.45,-3],[.16,.55,.5],'handover');
workshopPart('steel',[4.7,.6,.35],[1.1,.12,.85],'acceptance');
workshopPart('paper',[4.7,.71,.35],[.7,.06,.5],'acceptance');

// Visual spec section 11.4: one fixed perspective pose shared by the three rooms.
const studioPose = { fov: 30, azimuth: 45, elevation: 39, margin: .08 };

export const roomDefinitions = {
  bookshop: {
    bounds: { min: [-6,-.5,-4.6], max: [6,3.3,4.6] }, cameraTarget: [0,.8,0], camera: studioPose, fog: '#efe6d4',
    // Visual spec section 11.3: warm light wood, cream walls, navy trim and console bodies.
    materials: { floor:'#d6c3a0', wall:'#efe6d4', navy:'#202c40', edge:'#202c40', wood:'#c7a77a',
      shelf:'#8a7052', paper:'#f6f0e2', enamel:'#202c40', screen:'#91acb9' },
    assemblies, stationAnchors: { customers: [-4,1,2.5], service: [0,1,1.1], evaluator: [3.3,1,-.2],
      investigate: [0,1.05,-2.5], compare: [.7,1.1,3], ledger: [4,1,-2.8],
      owner: [-3.7,1,-2.4], repair: [-4.2,.8,-.2], next: [4,1.2,2.5] },
    // One status lamp per station, on the front corner of its furniture.
    lampAnchors: { customers: [-3.15,1.25,3], service: [.85,1.25,1.6], evaluator: [4.15,1.25,.3],
      investigate: [.95,1.25,-2], compare: [1.85,1.2,3.5], ledger: [5.3,2.75,-2.65],
      owner: [-2.85,1.25,-1.95], repair: [-3.6,1.03,.1], next: [4.8,1.75,2.6] },
    anchors: { candidateA: [-.15,1.02,3], candidateB: [1.55,1.02,3], plate: [0,1.2,1.25],
      wall: [4,1.9,-2.55], handover: [4,1.5,2.2], later: [2.2,1.2,3] },
  },
  gtm: {
    bounds: { min: [-6,-.5,-4.6], max: [6,3.6,4.6] }, cameraTarget: [0,.8,0], camera: studioPose, fog: '#202c40',
    materials: {floor:'#8b959f', navy:'#202c40', edge:'#263443', metal:'#61758a',
      pin:'#d7bb75', lane:'#35495e', paper:'#e7deca', screen:'#91acb9'},
    assemblies: routing,
    stationAnchors: {signals:[-4,1,2.2], rules:[-3.5,1.85,-2.5], workflow:[0,1,.6], wall:[3.7,1.65,-2]},
    anchors: {candidateA:[-.85,1.25,1.1], candidateB:[.85,1.25,1.1], plate:[0,1.2,.6],
      indicator:[0,1.6,.01], wall:[3.7,1.65,-1.76], wallPanel:[3.7,1.65,-1.76], wallSize:[.65,.9,.035],
      owner:[2.65,1.45,-1.82], clock:[3.7,2,-1.82], handoff:[4.5,.7,.2]},
  },
  northline: {
    bounds:{min:[-6,-.5,-4.6],max:[6,3.3,4.6]},cameraTarget:[0,.8,0],camera:studioPose,fog:'#28494a',
    materials:{floor:'#87978c',wall:'#28494a',edge:'#263443',steel:'#657b7c',wood:'#b4a17e',tool:'#d3d9cf',paper:'#e7deca',screen:'#91acb9'},
    assemblies:workshop,
    stationAnchors:{brief:[-4,1.4,2.5],map:[-3.7,1.6,-2.2],bench:[0,1,.6],acceptance:[3.5,1.6,-1.5],rollout:[3.8,1.2,2.2],handover:[0,1.4,-3]},
    anchors:{candidateA:[-.7,1.21,.9],candidateB:[.7,1.21,.9],plate:[0,1.2,.5],indicator:[0,1.65,.15],
      wall:[3.8,1.25,2.3],wallPanel:[3.5,2.1,-1.79],wallSize:[.8,.35,.04],
      booking:[3.15,1.2,2.3],approval:[4.45,1.2,2.3],declaration:[0,1.97,-2.9],escalation:[4.7,.82,.35],followup:[4.7,.82,.8],later:[1.1,1.2,.8]},
  },
};
