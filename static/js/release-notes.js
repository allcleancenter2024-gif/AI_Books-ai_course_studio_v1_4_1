import {esc} from './api.js';

const changeItems = [
  {group:'웹 RAG',feature:'SearXNG 검색·Firecrawl 선택 추출',importance:'high',basis:'2026-08-29',changed:'2026-08-29',version:'v1.24.0',before:'웹 보강은 DuckDuckGo 또는 Tavily 검색과 단일 로컬 HTML 추출기에 의존했습니다.',after:'localhost 전용 SearXNG를 기본 검색으로 사용하고, 고품질 모드에서 A/B 등급 URL만 Firecrawl로 추출합니다. 키·한도·오류 시 Trafilatura 로컬 추출과 내부 RAG로 안전하게 대체합니다.'},
  {group:'실행·안정성',feature:'Windows 실행 파일과 브라우저 상태 갱신',importance:'high',basis:'2026-08-29',changed:'2026-08-29',version:'v1.23.1',before:'실행 파일 이름이 v1.20.2에 머물렀고, EXE는 python.exe만 찾아 일부 Windows 환경에서 시작하지 못했습니다. 하이브리드 상태 UI는 300ms 상시 폴링을 사용했습니다.',after:'v1.23.1 EXE·BAT를 소스 버전과 일치시키고 py.exe와 python.exe를 모두 안전하게 탐색합니다. 상태 UI는 DOM 변경 이벤트 기반으로 갱신해 상시 폴링을 제거했습니다.'},
  {group:'보안·접근',feature:'관리자 로그인과 보호 API',importance:'high',basis:'2026-08-26',changed:'2026-08-27',version:'v1.10.0',before:'화면 접근과 API 호출의 서버 세션 경계가 명확하지 않았습니다.',after:'서버 기반 관리자 로그인, HttpOnly 세션 쿠키, 로그인 실패 제한과 보호 API 라우터를 적용했습니다.'},
  {group:'데이터·저장소',feature:'기본 운영 데이터베이스',importance:'high',basis:'2026-08-25',changed:'2026-08-26',version:'v1.8.2',before:'PostgreSQL과 MongoDB 실행 여부가 자료·과정·교재 저장을 막을 수 있었습니다.',after:'SQLite 3(data/studio.db)를 기본 실행·저장·벡터 검색 DB로 통합하고 외부 DB 의존성을 제거했습니다.'},
  {group:'로컬 AI',feature:'Ollama 생성 안정성',importance:'high',basis:'2026-08-27',changed:'2026-08-27',version:'v1.20.4',before:'사고형 모델의 내부 추론이 출력 예산을 소진하거나 본문이 비고, 단계마다 모델을 다시 불러올 수 있었습니다.',after:'네이티브 /api/chat, think=false, 10분 모델 유지와 단계별 출력 예산으로 본문 누락과 반복 로딩을 줄였습니다.'},
  {group:'교육 품질',feature:'교재 제작·검수 구조',importance:'high',basis:'2026-08-25',changed:'2026-08-26',version:'v1.9.0',before:'대상·기기별 절차와 출판 전 품질 판정이 일관된 데이터 구조로 관리되지 않았습니다.',after:'학습 경험·기기 경로·복구 방법·안전 등급을 포함하고 85점 미만 또는 치명 오류의 출판을 차단합니다.'},
  {group:'자료 처리',feature:'500MB 대용량 업로드',importance:'high',basis:'2026-08-13',changed:'2026-08-14',version:'v1.4.0',before:'업로드 한도가 80MB이고 큰 파일을 안정적으로 단계 처리하기 어려웠습니다.',after:'최대 500MB를 1MB 청크로 저장하고 PDF 페이지별·PPTX 슬라이드별·텍스트 블록별로 제한 추출합니다.'},
  {group:'AI 연결 범위',feature:'로컬 AI 전용 Provider 화면',importance:'high',basis:'2026-08-13',changed:'2026-08-27',version:'v1.20.x',before:'OpenAI·Gemini·Claude와 로컬 Provider가 한 연결 화면에 함께 노출되었습니다.',after:'Studio 생성 Provider는 LM Studio와 Ollama만 제공하며 외부 API 키 입력을 화면과 API에서 제외했습니다.'},
  {group:'자료 처리',feature:'참고자료 검색·최신화',importance:'medium',basis:'2026-08-14',changed:'2026-08-24',version:'v1.5.0',before:'추출한 긴 텍스트를 중심으로 자료를 저장하고 생성 문맥을 구성했습니다.',after:'텍스트 청크와 경량 벡터로 색인하고 관련 부분만 검색하며, 공개 웹자료는 하루 단위로 안전하게 갱신합니다.'},
  {group:'파일 출력',feature:'교재 결과 파일',importance:'medium',basis:'2026-08-24',changed:'2026-08-27',version:'v1.20.x',before:'생성 결과의 주된 저장·다운로드 형식은 Markdown이었습니다.',after:'Markdown 원본과 함께 PPTX·PDF·HWPX 파일을 열거나 내려받을 수 있습니다.'},
  {group:'Windows 실행',feature:'버전 안전 실행기',importance:'medium',basis:'2026-08-13',changed:'2026-08-27',version:'v1.10.0',before:'포트 충돌·이전 버전·시작 실패가 브라우저 실행 전에 충분히 구분되지 않을 수 있었습니다.',after:'Python·패키지·앱 import·8765 포트·실행 버전을 확인한 후 서버 준비 완료 시 브라우저를 엽니다.'},
  {group:'운영 상태',feature:'재부팅 후 서비스 확인',importance:'medium',basis:'2026-08-28',changed:'2026-08-28',version:'운영 점검',before:'재부팅 후 Tailscale, Docker 보조 스택과 Studio의 실행 상태가 확인되지 않았습니다.',after:'Tailscale과 Docker는 자동 복구됐고 DB/API health가 정상입니다. Studio 본체는 현재 수동 실행 방식입니다.'},
  {group:'운영 문서',feature:'설치 및 운영 설명서',importance:'medium',basis:'2026-08-28',changed:'2026-08-28',version:'v1.22.0',before:'설치·메뉴·백업·보안·장애 대응 정보가 여러 파일과 화면에 나뉘어 있었습니다.',after:'12번 메뉴에서 전체 운영 절차를 분야별·메뉴별 접이식 장, 검색과 필터로 확인할 수 있습니다.'},
  {group:'운영 문서',feature:'설명서 부분 갱신·PDF',importance:'medium',basis:'2026-08-28',changed:'2026-08-28',version:'v1.23.0',before:'운영 사실이 바뀌면 설명서 전체를 직접 비교해야 했고 통합 PDF 저장 기능이 없었습니다.',after:'실제 설정과 적용 스냅샷을 비교해 영향 장만 갱신하고, 25개 장 전체를 한국어 PDF로 내려받습니다.'},
  {group:'DB 관리',feature:'선택형 외부 DB 관리',importance:'low',basis:'2026-08-25',changed:'2026-08-26',version:'v1.8.2',before:'PostgreSQL·MongoDB가 운영 저장소 역할과 강하게 결합된 시기가 있었습니다.',after:'PostgreSQL·MongoDB·pgAdmin·Mongo Express는 localhost에 제한된 선택적 이전·분석 도구로 유지됩니다.'},
  {group:'최신 정보',feature:'AI 제품 변경 비교',importance:'low',basis:'2026-08-24',changed:'2026-08-24',version:'v1.4.4',before:'제품별 최신 정보는 목록에서 개별 확인해야 했습니다.',after:'기준 정보와 변경 정보, 수업 전 중요사항을 비교하고 Markdown으로 내려받을 수 있습니다.'},
  {group:'선택형 네트워크',feature:'Tailscale 독립성',importance:'unchanged',basis:'2026-08-28',changed:'변경 없음',version:'Host-only',before:'애플리케이션은 일반 TCP/IP·HTTP와 기존 인증으로 동작했습니다.',after:'동일합니다. Tailscale은 호스트의 선택형 관리망이며 앱 시작·로그인·DB·AI·Docker의 필수 조건이 아닙니다.'}
];

const labels={high:'상',medium:'중',low:'하',unchanged:'변화없음'};
const order=['high','medium','low','unchanged'];

function itemMarkup(item){
  return `<article class="release-item" data-importance="${item.importance}">
    <div class="release-item-top"><div><span class="release-group">${esc(item.group)}</span><h3>${esc(item.feature)}</h3></div><span class="importance ${item.importance}">${labels[item.importance]}</span></div>
    <div class="release-dates"><span><b>기준일</b>${esc(item.basis)}</span><span><b>변경일자</b>${esc(item.changed)}</span><span><b>적용 근거</b>${esc(item.version)}</span></div>
    <div class="release-compare"><div class="release-before"><b>변경 전</b><p>${esc(item.before)}</p></div><div class="release-arrow" aria-hidden="true">→</div><div class="release-after"><b>변경 후</b><p>${esc(item.after)}</p></div></div>
  </article>`;
}

export function initReleaseNotes(){
  const list=document.getElementById('releaseNotesList'),summary=document.getElementById('releaseSummary'),search=document.getElementById('releaseSearch');
  if(!list||!summary||!search)return;
  summary.innerHTML=order.map(key=>`<div class="release-stat ${key}"><span>${labels[key]}</span><strong>${changeItems.filter(item=>item.importance===key).length}</strong><small>개 항목</small></div>`).join('');
  let filter='all';
  const render=()=>{
    const query=search.value.trim().toLocaleLowerCase('ko-KR');
    const visible=changeItems.filter(item=>(filter==='all'||item.importance===filter)&&(!query||`${item.group} ${item.feature} ${item.before} ${item.after} ${item.version}`.toLocaleLowerCase('ko-KR').includes(query)));
    const groups=[...new Set(visible.map(item=>item.group))];
    list.innerHTML=visible.length?groups.map(group=>`<section class="release-group-block" aria-labelledby="release-${groups.indexOf(group)}"><div class="release-group-title"><h3 id="release-${groups.indexOf(group)}">${esc(group)}</h3><span>${visible.filter(item=>item.group===group).length}개</span></div>${visible.filter(item=>item.group===group).map(itemMarkup).join('')}</section>`).join(''):'<div class="release-empty">조건에 맞는 변경 항목이 없습니다. 필터나 검색어를 바꿔 주세요.</div>';
  };
  document.querySelectorAll('[data-release-filter]').forEach(button=>button.addEventListener('click',()=>{
    filter=button.dataset.releaseFilter;
    document.querySelectorAll('[data-release-filter]').forEach(candidate=>{const selected=candidate===button;candidate.classList.toggle('is-selected',selected);candidate.setAttribute('aria-pressed',String(selected));});
    render();
  }));
  search.addEventListener('input',render);
  render();
}
