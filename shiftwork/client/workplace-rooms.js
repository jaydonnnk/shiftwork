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

export const roomDefinitions = {
  bookshop: {
    bounds: { min: [-6,-.5,-4.6], max: [6,3.3,4.6] }, cameraTarget: [0,.8,0],
    materials: { floor:'#a89477', navy:'#202c40', edge:'#263443', wood:'#b99a70',
      shelf:'#6c5943', paper:'#e7deca', enamel:'#48617a', screen:'#91acb9' },
    assemblies, stationAnchors: { customers: [-4,1,2.5], service: [0,1,1.1], evaluator: [3.3,1,-.2] },
  },
};
