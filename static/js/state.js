const state={phase:'idle',message:'대기 중',progress:0,provider:'미선택',sources:0};
const colors={idle:'idle',working:'work',success:'ok',warning:'warn',error:'bad'};
export function setStatus({phase,message,progress,provider}={}){
  if(phase)state.phase=phase;if(message!==undefined)state.message=message;if(progress!==undefined)state.progress=progress;if(provider!==undefined)state.provider=provider;
  const job=document.querySelector('#jobStatus');job.className=`pill ${colors[state.phase]||'idle'}`;job.textContent=state.message;
  document.querySelector('#providerStatus').textContent=`Provider: ${state.provider}`;const pct=Math.max(0,Math.min(100,state.progress));document.querySelector('#progressBar').style.width=`${pct}%`;document.querySelector('#progressText').textContent=`${Math.round(pct)}%`;
}
export function setServer(ok,version='',lastUpdated=''){const el=document.querySelector('#serverStatus');el.className=`pill ${ok?'ok':'bad'}`;el.textContent=ok?`서버 정상 · v${version}${lastUpdated?` [${lastUpdated}]`:''}`:'서버 연결 오류'}
export function setSourceCount(n){state.sources=n;const el=document.querySelector('#sourceStatus');el.className=`pill ${n?'ok':'idle'}`;el.textContent=`참고자료: ${n}개 선택`}
