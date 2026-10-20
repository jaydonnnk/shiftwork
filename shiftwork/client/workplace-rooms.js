// Original S29 Bellwether geometry. No reference artwork or imported models.
const assemblies = [];
const box = (material, position, size, station = null) => assemblies.push({ material, position, size, station });
box('floor', [0,-.15,0], [12,.3,9]);
box('navy', [0,1.6,-4.5], [12,3.2,.18]);
box('navy', [-6,1.6,0], [.18,3.2,9]);
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

export const roomDefinitions = {
  bookshop: {
    bounds: { min: [-6,-.5,-4.6], max: [6,3.3,4.6] }, cameraTarget: [0,.8,0],
    materials: { floor:'#a89477', navy:'#202c40', edge:'#263443', wood:'#b99a70',
      shelf:'#6c5943', paper:'#e7deca', enamel:'#48617a', screen:'#91acb9' },
    assemblies, stationAnchors: { customers: [-4,1,2.5], service: [0,1,1.1], evaluator: [3.3,1,-.2],
      investigate: [0,1.05,-2.5], compare: [.7,1.1,3], ledger: [4,1,-2.8],
      owner: [-3.7,1,-2.4], repair: [-4.2,.8,-.2], next: [4,1.2,2.5] },
    anchors: { candidateA: [-.15,1.02,3], candidateB: [1.55,1.02,3], plate: [0,1.2,1.25],
      wall: [4,1.9,-2.55], handover: [4,1.5,2.2], later: [2.2,1.2,3] },
  },
};
