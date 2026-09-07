export const pretty=o=>JSON.stringify(o,null,2);
export const esc=(s='')=>String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
export async function api(url,opt){
  const r=await fetch(url,opt); const raw=await r.text(); let data={};
  if(raw){try{data=JSON.parse(raw)}catch{data={detail:raw}}}
  if(!r.ok){const d=data?.detail??raw??`HTTP ${r.status}`;throw new Error(typeof d==='string'?d:pretty(d))}
  return data;
}
export const post=(url,body)=>api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
export const upload=(url,form)=>api(url,{method:'POST',body:form});
export const del=(url)=>api(url,{method:'DELETE'});
