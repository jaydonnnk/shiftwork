import assert from 'node:assert/strict';

export async function blockExternalAssets({socket,send,evaluate,url}) {
  if(process.env.SHIFTWORK_BLOCK_EXTERNAL!=='1') return;
  assert.ok(!process.env.SHIFTWORK_FAULT,'Network isolation and source faults require separate browser runs');
  const origin=new URL(url).origin;
  let caught=0;
  socket.addEventListener('message',({data})=>{
    const message=JSON.parse(data);
    if(message.method!=='Fetch.requestPaused') return;
    const {requestId,request}=message.params,target=new URL(request.url);
    const blocked=!['data:','about:'].includes(target.protocol)&&target.origin!==origin;
    if(blocked) caught++;
    send(blocked?'Fetch.failRequest':'Fetch.continueRequest',blocked?{requestId,errorReason:'BlockedByClient'}:{requestId}).catch(error=>console.error(error));
  });
  await send('Fetch.enable',{patterns:[{urlPattern:'*'}]});
  const refused=await evaluate(async()=>{try{await fetch('https://s34-network-control.invalid/asset.js');return false;}catch{return true;}});
  assert.equal(refused,true,'External asset control was not refused');
  assert.equal(caught,1,'External asset refusal did not reach the network guard');
  console.log('External asset interception self-test PASS');
}
