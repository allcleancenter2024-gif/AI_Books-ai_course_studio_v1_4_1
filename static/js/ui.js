export function setOutput(el,kind,text){el.className=`out ${kind||''}`;el.textContent=text}
export function initBackToTop(){
  const b=document.querySelector('#backToTop');
  const refresh=()=>{const long=document.documentElement.scrollHeight>window.innerHeight+500;b.classList.toggle('show',long&&window.scrollY>420)};
  addEventListener('scroll',refresh,{passive:true});addEventListener('resize',refresh);new ResizeObserver(refresh).observe(document.body);b.onclick=()=>scrollTo({top:0,behavior:'smooth'});refresh();
}
