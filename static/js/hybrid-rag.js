const modes=[
  {modeId:'aiGenerationMode',qualityId:'aiWebQuality',beforeId:'aiWeeks',outId:'aiWeekOut'},
  {modeId:'bookGenerationMode',qualityId:'bookWebQuality',beforeId:'bookWeeks',outId:'bookOut'}
];
const nativeFetch=window.fetch.bind(window);
const safe=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const healthCache=new Map();

function syncModeControls(config){
  const mode=document.getElementById(config.modeId),quality=document.getElementById(config.qualityId);
  if(!mode||!quality)return;
  const web=mode.value==='web_enhanced';
  quality.hidden=!web;
  quality.disabled=!web;
  quality.setAttribute('aria-hidden',String(!web));
  const out=document.getElementById(config.outId);
  out?.querySelector('.hybrid-work-status')?.remove();
  if(mode.value==='local_only')out?.querySelector('.hybrid-source-summary')?.remove();
  syncHybridStatus(out);
}

function installHybridModeUI(){
  modes.forEach(config=>{
    const before=document.getElementById(config.beforeId);
    if(!before)return;
    let mode=document.getElementById(config.modeId);
    if(!mode){
      mode=document.createElement('select');mode.id=config.modeId;mode.setAttribute('aria-label','자료 활용 모드');
      mode.innerHTML='<option value="local_only">완전 로컬</option><option value="web_enhanced">웹 자료 보강</option><option value="external_edit">고품질 최종 편집(외부 전송)</option>';
      before.parentElement.insertBefore(mode,before);
    }
    let quality=document.getElementById(config.qualityId);
    if(!quality){
      quality=document.createElement('select');quality.id=config.qualityId;quality.className='web-quality-select';quality.setAttribute('aria-label','웹 검색 방식');
      quality.innerHTML='<option value="free">무료 기본 검색</option><option value="high_quality">고품질 보조 검색</option>';
      before.parentElement.insertBefore(quality,before);
    }
    mode.addEventListener('change',()=>syncModeControls(config));
    quality.addEventListener('change',()=>{healthCache.clear();document.getElementById(config.outId)?.querySelector('.hybrid-work-status')?.remove();syncHybridStatus(document.getElementById(config.outId))});
    syncModeControls(config);
  });
}
export {installHybridModeUI};

function requestConfig(url){return modes.find(config=>url.includes('/api/ai/book')?config.outId==='bookOut':config.outId==='aiWeekOut')}
function selectedScope(config){
  const mode=document.getElementById(config.modeId)?.value||'local_only';
  if(mode!=='web_enhanced')return'disabled';
  return document.getElementById(config.qualityId)?.value==='high_quality'?'high_quality':'official_and_expert';
}

window.fetch=async(input,init={})=>{
  const url=typeof input==='string'?input:input?.url||'',isGeneration=url.includes('/api/ai/week')||url.includes('/api/ai/book');
  const config=isGeneration?requestConfig(url):null;
  if(config&&init.body){
    try{const body=JSON.parse(init.body),mode=document.getElementById(config.modeId)?.value||'local_only';body.generation_mode=mode;body.web_scope=selectedScope(config);init={...init,body:JSON.stringify(body)}}catch(_){}
  }
  const response=await nativeFetch(input,init);
  if(config&&response.ok)response.clone().json().then(payload=>setTimeout(()=>renderEvidenceSources(config.outId,payload),120)).catch(()=>{});
  return response;
};

function modeForOutput(out){const config=modes.find(item=>item.outId===out?.id);return config?{config,mode:document.getElementById(config.modeId)?.value||'local_only',quality:document.getElementById(config.qualityId)?.value||'free'}:null}
function statusLabel(value){return({connected:'연결됨',configured:'연결 준비',api_key_missing:'API 키 없음',disabled:'사용 안 함',unavailable:'연결 안 됨',error:'오류',ready:'준비됨',legacy:'호환 모드'})[value]||'확인 중'}
async function loadHybridHealth(box,highQuality){
  const key=String(highQuality);let promise=healthCache.get(key);
  if(!promise){promise=nativeFetch('/api/hybrid/health?high_quality='+key).then(r=>r.ok?r.json():Promise.reject()).catch(()=>({status:'unavailable',firecrawl:{status:'disabled'},local_extractor:{status:'ready'}}));healthCache.set(key,promise)}
  const health=await promise;if(!box.isConnected)return;
  const search=box.querySelector('[data-hybrid-search]'),fire=box.querySelector('[data-hybrid-firecrawl]'),privacy=box.querySelector('[data-hybrid-privacy]');
  if(search){search.textContent='SearXNG · '+statusLabel(health.search?.status||health.status);search.dataset.state=health.search?.status||health.status}
  if(fire){fire.textContent='Firecrawl · '+statusLabel(health.firecrawl?.status);fire.dataset.state=health.firecrawl?.status}
  if(privacy)privacy.textContent=highQuality&&health.firecrawl?.enabled?'공개 URL을 Firecrawl로 전송할 수 있음':'외부 생성형 AI로 문서 전송 없음';
}

function attachHybridStatus(out){
  if(!out||!out.classList.contains('generation-progress'))return;
  const state=modeForOutput(out),existing=out.querySelector('.hybrid-work-status');if(!state)return;
  if(state.mode==='local_only'){existing?.remove();return}if(existing)return;
  const web=state.mode==='web_enhanced',high=web&&state.quality==='high_quality';
  const label=web?(high?'고품질 웹 자료 보강':'무료 웹 자료 보강'):'고품질 최종 편집';
  const detail=web?'자료 점검 → 웹 검색 → 본문 정제 → 근거 검증 → 강의책 생성':'외부 전송 동의가 없으면 로컬 생성 결과를 유지합니다.';
  const box=document.createElement('div');box.className='hybrid-work-status';
  box.innerHTML='<div class="hybrid-work-status-head"><span class="hybrid-mode-dot"></span><b>'+label+'</b></div><p class="hybrid-live-message">현재 작업 정보를 확인하는 중입니다.</p><div class="hybrid-status-ledger">'+(web?'<span data-hybrid-search data-state="checking">SearXNG · 확인 중</span><span data-hybrid-firecrawl data-state="checking">Firecrawl · 확인 중</span>':'<span data-state="checking">외부 편집 · 동의 확인</span>')+'<span data-hybrid-privacy>외부 생성형 AI로 문서 전송 없음</span></div><small>'+detail+'</small>';
  out.appendChild(box);if(web)loadHybridHealth(box,high);
}

function syncHybridStatus(out){attachHybridStatus(out);const live=out?.querySelector('.hybrid-live-message'),source=out?.querySelector('.small');if(live&&source&&live.textContent!==source.textContent)live.textContent=source.textContent}
function watchHybridStatus(){modes.forEach(config=>{const out=document.getElementById(config.outId);if(!out)return;new MutationObserver(()=>syncHybridStatus(out)).observe(out,{childList:true,subtree:true});syncHybridStatus(out)})}

async function renderEvidenceSources(outId,payload){
  const out=document.getElementById(outId);if(!out)return;
  const ids=[...new Set([payload?.evidence_pack_id,...(payload?.content||[]).map(item=>item?.evidence_pack_id)].filter(Boolean))];
  out.querySelector('.hybrid-source-summary')?.remove();if(!ids.length)return;
  const packs=await Promise.all(ids.map(id=>nativeFetch('/api/hybrid/evidence-packs/'+id).then(r=>r.ok?r.json():null).catch(()=>null)));
  const items=packs.flatMap(pack=>pack?.items||[]);if(!items.length)return;
  const section=document.createElement('details');section.className='hybrid-source-summary';section.open=false;
  section.innerHTML='<summary>사용된 웹 출처 '+items.length+'개 보기</summary><div class="hybrid-source-list">'+items.map(item=>'<a href="'+safe(item.source_url)+'" target="_blank" rel="noopener noreferrer"><b>'+safe(item.source_title)+'</b><span>'+safe(item.publisher||'출처 기관 미확인')+' · '+safe((item.retrieved_at||'').slice(0,10))+' · '+safe(item.source_grade)+'등급</span></a>').join('')+'</div>';
  out.appendChild(section);
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',watchHybridStatus);else watchHybridStatus();
