import {api,post,esc} from './api.js';

const chapters = [
  {id:'windows-install',category:'install',label:'설치·시작',title:'Windows 설치와 첫 실행',summary:'ZIP 압축 해제부터 8765 화면 확인까지',body:`
    <ol class="manual-steps"><li><b>새 폴더에 압축 해제</b><p>기존 버전 폴더에 덮어쓰지 말고 쓰기 권한이 있는 새 폴더를 사용합니다.</p></li><li><b>Python 확인</b><p>Python 3.10 이상이 필요합니다. 실행기는 <code>py -3</code> 또는 <code>python</code>을 찾고 필요한 패키지만 설치합니다.</p></li><li><b><code>run_windows.bat</code> 실행</b><p>Python, 8765 포트, 필수 패키지, 앱 import를 순서대로 검사한 뒤 서버를 시작합니다.</p></li><li><b>브라우저와 버전 확인</b><p><code>http://127.0.0.1:8765</code>에서 제목과 상단 상태가 모두 현재 버전인지 확인합니다.</p></li></ol><div class="manual-callout"><b>정상 신호</b><span>실행 창에 <code>[READY]</code>와 현재 버전이 표시되고 로그인 화면이 열립니다.</span></div>`},
  {id:'linux-install',category:'install',label:'설치·시작',title:'Ubuntu Linux 설치와 실행',summary:'Windows 배치 없이 Python으로 실행하는 기본 절차',body:`
    <p>현재 제공된 자동 실행 배치는 Windows용입니다. Ubuntu에서는 프로젝트 폴더에서 Python 가상환경을 사용해 실행합니다.</p><div class="manual-code"><code>python3 -m venv .venv<br>source .venv/bin/activate<br>python -m pip install -r requirements.txt<br>python -m uvicorn app:app --host 127.0.0.1 --port 8765</code></div><ul><li>서버 자동 시작은 운영 환경의 서비스 관리 정책에 맞춰 별도로 구성합니다.</li><li>처음에는 <code>127.0.0.1</code> 바인딩을 유지합니다. 원격 접속을 위해 임의로 <code>0.0.0.0</code>으로 바꾸지 않습니다.</li><li>배포 전에 파일 권한, 로그 위치, 백업 경로와 HTTPS 게이트웨이를 별도로 검토합니다.</li></ul>`},
  {id:'login-session',category:'install',label:'설치·시작',title:'로그인과 세션 운영',summary:'관리자 계정, 로그인 제한, 로그아웃과 쿠키 정책',body:`
    <ul><li>기존 로컬 관리자 이름과 접속 암호로 로그인합니다. 비밀번호는 평문이 아니라 scrypt 해시로 SQLite에 저장됩니다.</li><li>같은 이름·접속 환경에서 5회 연속 실패하면 5분간 로그인이 제한됩니다.</li><li>로그인 세션은 HttpOnly·SameSite=Strict 쿠키를 사용하며 최대 7일입니다.</li><li>공용 PC에서는 ‘이 PC에서 로그인 유지’를 선택하지 말고 사용 후 반드시 로그아웃합니다.</li></ul><div class="manual-warning"><b>계정을 잃어버린 경우</b><span>DB 삭제나 초기화를 시도하지 마세요. 기존 <code>data/studio.db</code>를 보존하고 관리자에게 복구 절차를 요청합니다.</span></div>`},
  {id:'daily-checklist',category:'install',label:'설치·시작',title:'매일 시작·종료 체크리스트',summary:'수업 전 5분 점검과 안전한 종료',body:`
    <div class="manual-check-grid"><div><b>시작 전</b><label>□ 상단 서버 버전·날짜 확인</label><label>□ LM Studio 또는 Ollama 실행</label><label>□ AI 연결 테스트</label><label>□ 선택 자료 개수 확인</label></div><div><b>종료 전</b><label>□ 진행 중 생성 작업 완료 확인</label><label>□ 필요한 결과 파일 다운로드</label><label>□ 공용 PC에서 로그아웃</label><label>□ 서버 창은 Ctrl+C로 종료</label></div></div><p>브라우저 창만 닫아도 서버는 계속 실행될 수 있습니다. 서버를 끝내려면 실행 창에서 <code>Ctrl+C</code>를 사용합니다.</p>`},

  {id:'menu-ai',category:'menu',label:'메뉴 1',title:'1. AI 연결',summary:'LM Studio·Ollama 자동 연결, 모델 선택과 응답 시험',body:`
    <ol><li>LM Studio 또는 Ollama 서버를 먼저 실행합니다.</li><li><b>자동 연결</b>을 눌러 로컬 주소와 사용 가능한 범용 모델을 찾습니다.</li><li>모델과 서버 주소를 확인하고 <b>연결 테스트</b>로 실제 짧은 응답을 검증합니다.</li><li>필요할 때만 응답 대기 시간을 조정합니다. 기본 범위는 30~3600초입니다.</li></ol><p>현재 생성 Provider는 LM Studio와 Ollama만 노출됩니다. 서버 주소는 내 PC의 localhost 주소를 사용하며 외부 API 키 입력은 제공하지 않습니다.</p>`},
  {id:'menu-sources',category:'menu',label:'메뉴 2',title:'2. 참고자료',summary:'파일·웹·영상 수집, 선택, 요약과 최신화',body:`
    <ul><li><b>파일:</b> md·txt·html·pdf·pptx·png·jpg·webp, 파일당 최대 500MB</li><li><b>웹:</b> 공개 HTTP/HTTPS 페이지만 수집하며 localhost·사설 IP·link-local 주소는 차단</li><li><b>영상:</b> YouTube 공개·자동 자막을 우선 수집하고 실패 시 제목·채널·URL을 보관</li></ul><p>체크한 자료만 교재 생성에 사용됩니다. 대용량 파일은 업로드와 분석이 분리된 백그라운드 작업으로 처리되며, 원본 크기·SHA-256 체크섬·멱등 키가 기록됩니다. 같은 멱등 키로 재시도하면 기존 자료에 연결되고, 중단 작업은 원본 검증 후 재개할 수 있습니다. 긴 자료는 조각 요약 후 통합하며, 공개 웹자료는 필요할 때 최신화할 수 있습니다.</p>`},
  {id:'menu-notebook',category:'menu',label:'메뉴 3',title:'3. Gemini Notebook',summary:'선택 자료 ZIP 자료팩과 Gemini 앱 연계',body:`
    <ol><li>2번 메뉴에서 사용할 자료를 체크합니다.</li><li><b>선택 자료팩 만들기</b>로 ZIP을 생성합니다.</li><li><b>Gemini 열기</b>로 앱을 연 뒤 필요한 파일과 URL을 Notebook 소스로 추가합니다.</li></ol><p>일반 Gemini Notebook 자동 생성 API를 전제로 하지 않습니다. 자료팩은 <code>exports/source_packs</code>에 생성되며, Google Drive 직접 연동은 별도 Google 권한 구성이 필요합니다.</p>`},
  {id:'menu-course',category:'menu',label:'메뉴 4',title:'4. 과정 만들기',summary:'12주·15주 과정과 학습자 대상 구성',body:`
    <p>과정 길이와 대상을 선택하면 주차별 주제·대표 실습·수업 시간 구성을 만듭니다. 결과는 SQLite에 기록되며 Markdown 강의계획서로 저장할 수 있습니다.</p><div class="manual-callout"><b>수업 시간 기준</b><span>개념 18분 · 실기·실습 144분 · 정리·점검 18분</span></div>`},
  {id:'menu-preview',category:'menu',label:'메뉴 5',title:'5. 미리보기',summary:'AI 연결 없이 학생용·강사용 기본 구조 확인',body:`
    <p>주제를 선택하고 학생용 또는 강사용을 누르면 AI 호출 없이 기본 교재 구조를 확인합니다. 실제 모델 연결 전에 화면 흐름과 대상별 표현을 빠르게 점검할 때 사용합니다.</p><ul><li>학생용: 쉬운 설명과 학습 흐름 중심</li><li>강사용: 수업 목표와 지도 포인트 중심</li></ul>`},
  {id:'menu-week',category:'menu',label:'메뉴 6',title:'6. 1주 교재',summary:'작은 범위로 모델·자료·품질을 먼저 검증',body:`
    <ol><li>Provider, 과정 길이, 주차, 대상, 학생용·강사용·통합 유형을 선택합니다.</li><li>사용할 참고자료 체크 상태와 학습자 경험·기기 경로를 확인합니다.</li><li><b>1주 분량 생성</b> 후 설명·프롬프트·실습·파일 저장 진행률을 확인합니다.</li><li>품질 점수, 검증 상태와 경고를 읽고 결과를 열어 검수합니다.</li></ol><p>전체 교재보다 먼저 이 메뉴로 1주를 생성하는 것이 권장됩니다. 품질 검사를 통과해도 강사 승인 전에는 Publisher 발행이 차단됩니다. 로컬 모델이 중단되면 안전 기본 교재로 복구될 수 있으므로 경고가 있으면 반드시 내용을 다시 확인합니다.</p>`},
  {id:'menu-book',category:'menu',label:'메뉴 7',title:'7. 전체 교재',summary:'전체 또는 선택 구간을 학생용·강사용으로 생성',body:`
    <p>12주·15주 중 시작 주차와 끝 주차를 정해 생성합니다. 결과는 Markdown 원본과 함께 PPTX·PDF·HWPX로 내려받을 수 있습니다. 생성된 차시는 주차별로 독립 저장되어 Publisher handoff API에서 학생용·강사용·통합 형태로 조회할 수 있습니다.</p><ul><li>각 차시는 핵심 프롬프트 3개와 핵심 3·선택 3·도전 1의 실습 7개를 기준으로 검사합니다.</li><li>품질 점수 85점 미만 또는 치명 오류가 있으면 출판 가능 상태가 되지 않습니다.</li><li>AI 초안은 강사 검토와 승인 전 최종본으로 사용하지 않습니다.</li></ul>`},
  {id:'menu-latest',category:'menu',label:'메뉴 8',title:'8. 최신 정보',summary:'AI 제품 기준 정보와 공식 확인 상태 조회',body:`
    <p>제품명, 현재 정보, 기준일, 변경 상태, 공식 확인일과 공식 페이지를 보여줍니다. 빨간 표시는 기준 정보 이후 변경이 있는 항목, 파란 표시는 마지막 확인에서 변화가 없는 항목입니다.</p><div class="manual-warning"><b>강의 배포 전</b><span>제품 기능·가격·정책은 바뀔 수 있으므로 반드시 공식 링크에서 다시 확인합니다.</span></div>`},
  {id:'menu-changes',category:'menu',label:'메뉴 9',title:'9. 주요한 정보변경사항',summary:'변경 전·후 비교, Markdown 저장과 교재 반영',body:`
    <p><b>변경사항 보기</b>에서 기준 정보와 변경 정보를 비교합니다. 저장된 교재를 선택한 뒤 변경 카드를 교재에 추가할 수 있고, 전체 비교표는 Markdown으로 내려받을 수 있습니다.</p><p>교재 반영 후 파란색 밑줄 구간과 파일 저장 기록을 다시 확인하세요.</p>`},
  {id:'menu-dbms',category:'menu',label:'메뉴 10',title:'10. DBMS 관리',summary:'기본 SQLite와 선택형 PostgreSQL·MongoDB 관리',body:`
    <ul><li><b>기본:</b> <code>data/studio.db</code> SQLite 3, WAL 모드</li><li><b>선택:</b> PostgreSQL 5434·pgAdmin 5051</li><li><b>선택:</b> MongoDB 27018·Mongo Express 8082</li><li><b>상태 API:</b> Node.js <code>127.0.0.1:3001/health</code></li></ul><p>외부 DB 도구가 중지되어도 기본 Studio는 계속 작동해야 합니다. 관리 화면은 localhost에만 공개됩니다.</p>`},
  {id:'menu-updates',category:'menu',label:'메뉴 11',title:'11. 변경된 내용 안내',summary:'현재 적용 기능의 변경 전·후와 중요도 확인',body:`
    <p>기능별 변경 전·후, 기준일, 변경일자, 적용 근거를 확인합니다. 상·중·하·변화없음 필터와 검색을 이용해 필요한 변경만 좁힐 수 있습니다.</p><p>‘변화없음’은 설정 누락이 아니라 애플리케이션 구조를 그대로 유지했다는 뜻입니다.</p>`},
  {id:'menu-manual',category:'menu',label:'메뉴 12',title:'12. 설치 및 운영 설명서',summary:'현재 보고 있는 전체 운영 안내',body:`
    <p>분야 선택과 검색으로 필요한 장을 찾고 제목을 눌러 펼칩니다. 처음 운영할 때는 설치·시작 → 메뉴 1~7 → 데이터·백업 → 장애 대응 순서로 읽는 것이 좋습니다.</p><p>화면 내용은 현재 소스·설정·포트·테스트를 기준으로 작성되며, 실제 운영 정책이 달라지면 변경 안내와 함께 갱신해야 합니다.</p>`},

  {id:'data-paths',category:'data',label:'데이터·백업',title:'데이터와 결과 파일 위치',summary:'무엇이 어디에 저장되는지 확인',body:`
    <div class="manual-table-wrap"><table><thead><tr><th>경로</th><th>내용</th><th>운영 주의</th></tr></thead><tbody><tr><td><code>data/studio.db</code></td><td>계정·세션·과정·교재·자료·벡터</td><td>가장 중요한 기본 DB</td></tr><tr><td><code>exports/books</code></td><td>교재 Markdown·PPTX·PDF·HWPX</td><td>DB 기록과 함께 보존</td></tr><tr><td><code>exports/summaries</code></td><td>자료별 Markdown 요약</td><td>자료 삭제 시 연계 파일 확인</td></tr><tr><td><code>exports/source_packs</code></td><td>Gemini Notebook ZIP</td><td>필요 시 재생성 가능</td></tr><tr><td><code>logs</code></td><td>시작·서버 표준 출력·오류</td><td>비밀정보 공유 전 마스킹</td></tr><tr><td><code>uploads</code></td><td>검증 대기 중인 staging 원본</td><td>크기·SHA-256 검증 후 분석되며 만료 파일은 자동 정리</td></tr></tbody></table></div>`},
  {id:'sqlite-backup',category:'data',label:'데이터·백업',title:'SQLite 안전 백업과 복구',summary:'WAL 모드 DB를 손상 없이 보존하는 원칙',body:`
    <ol><li>진행 중인 업로드·요약·교재 생성을 완료합니다.</li><li>Studio 서버를 정상 종료합니다.</li><li><code>data/studio.db</code>와 필요한 <code>exports</code>를 날짜가 포함된 별도 폴더에 복사합니다.</li><li>백업 파일의 크기와 열람 가능 여부를 확인합니다.</li></ol><div class="manual-warning"><b>금지</b><span>실행 중 DB 파일만 임의 복사하거나 <code>studio.db-wal</code>·<code>studio.db-shm</code>을 삭제하지 않습니다. 복구 전에는 원본을 추가로 보존합니다.</span></div>`},
  {id:'docker-external',category:'data',label:'데이터·백업',title:'선택형 Docker와 외부 DB 이전',summary:'기본 앱과 분리된 PostgreSQL·MongoDB 활용',body:`
    <ol><li><code>.env.example</code>을 <code>.env</code>로 복사하고 모든 <code>CHANGE_ME</code>를 긴 무작위 값으로 변경합니다.</li><li><code>docker compose up -d --build</code>를 실행합니다.</li><li><code>http://127.0.0.1:3001/health</code>에서 PostgreSQL·MongoDB가 모두 true인지 확인합니다.</li><li><code>python scripts/sync_sqlite_to_multidb.py</code>로 SQLite 내용을 단방향·반복 가능 방식으로 복제합니다.</li></ol><p>이 스크립트는 SQLite 원본을 수정하지 않습니다. Docker 볼륨 삭제·prune은 명시적 백업과 승인 없이 실행하지 않습니다.</p>`},

  {id:'network-ports',category:'security',label:'보안·네트워크',title:'포트와 공개 범위',summary:'localhost·Docker 내부·선택형 관리망 구분',body:`
    <div class="manual-table-wrap"><table><thead><tr><th>서비스</th><th>주소</th><th>분류</th></tr></thead><tbody><tr><td>Studio</td><td>127.0.0.1:8765</td><td>LOCALHOST ONLY</td></tr><tr><td>외부 DB API</td><td>127.0.0.1:3001</td><td>LOCALHOST ONLY</td></tr><tr><td>PostgreSQL</td><td>127.0.0.1:5434</td><td>LOCALHOST ONLY</td></tr><tr><td>MongoDB</td><td>127.0.0.1:27018</td><td>LOCALHOST ONLY</td></tr><tr><td>Ollama</td><td>127.0.0.1:11434 사용 권장</td><td>LOCAL AI</td></tr><tr><td>LM Studio</td><td>127.0.0.1:1234/12345</td><td>LOCAL AI</td></tr></tbody></table></div><p>원격 사용이 필요해도 바인딩·방화벽·Docker 포트를 자동 변경하지 않습니다. Public 웹사이트와 OAuth·외부 Webhook은 별도 HTTPS 게이트웨이로 설계합니다.</p>`},
  {id:'tailscale-host',category:'security',label:'보안·네트워크',title:'Tailscale Host-only 운영 원칙',summary:'선택형 사설 관리망과 애플리케이션 독립성',body:`
    <ul><li>Tailscale은 Windows 또는 Ubuntu 호스트에 설치하는 선택형 관리망입니다.</li><li>Studio 시작·로그인·DB·AI·저장소·Docker의 필수 조건으로 사용하지 않습니다.</li><li>Exit Node, Subnet Router, Funnel, Serve, Docker Sidecar, Custom DNS는 기본 OFF입니다.</li><li>Tailscale을 꺼도 기본 앱은 정상이고 사설 원격 관리만 사용할 수 없어야 합니다.</li><li>기존 애플리케이션 인증과 DB 인증을 그대로 유지합니다.</li></ul><div class="manual-callout"><b>교체 가능성</b><span>WireGuard·Headscale·ZeroTier로 바꿔도 애플리케이션 코드 수정이 없어야 합니다.</span></div>`},
  {id:'public-security',category:'security',label:'보안·네트워크',title:'인터넷 공개 전 필수 검토',summary:'HTTPS·인증·콜백·내부 서비스 분리',body:`
    <ul><li>Studio를 인터넷에 직접 공개하지 말고 인증된 HTTPS 리버스 프록시·게이트웨이를 검토합니다.</li><li>HTTPS 환경에서는 <code>AI_COURSE_STUDIO_COOKIE_SECURE=1</code>을 설정합니다.</li><li>PostgreSQL·MongoDB·Redis·MinIO Console·Ollama·LM Studio를 Public Internet에 직접 노출하지 않습니다.</li><li>OAuth Callback과 외부 Webhook은 Public HTTPS 주소를 사용하고 Tailnet 전용 주소로 바꾸지 않습니다.</li><li>로그를 공유할 때 암호·토큰·API 키·개인정보를 마스킹합니다.</li></ul>`},

  {id:'startup-trouble',category:'trouble',label:'장애 대응·업데이트',title:'실행·포트·로그 문제 진단',summary:'Studio가 열리지 않을 때 확인 순서',body:`
    <ol><li><code>run_windows_debug.bat</code>으로 Python·패키지·앱 import·포트를 진단합니다.</li><li><code>logs/startup_error.log</code>, <code>server_stderr.log</code>, <code>server_stdout.log</code>의 마지막 오류를 확인합니다.</li><li>8765를 다른 프로그램이 사용하면 실행기는 그 프로세스를 종료하지 않고 중단합니다.</li><li>이전 Studio임이 HTTP로 확인된 경우에만 Windows 실행기가 해당 PID를 교체합니다.</li></ol><div class="manual-callout"><b>정상 확인</b><span><code>/api/health</code>가 ok=true와 현재 버전·수정일을 반환해야 합니다.</span></div>`},
  {id:'ai-trouble',category:'trouble',label:'장애 대응·업데이트',title:'AI 연결·생성 문제 진단',summary:'연결 거부, 시간초과, 메모리, 빈 출력 구분',body:`
    <div class="manual-table-wrap"><table><thead><tr><th>증상</th><th>먼저 확인할 것</th></tr></thead><tbody><tr><td>연결 거부</td><td>LM Studio/Ollama 실행 여부와 localhost 포트</td></tr><tr><td>모델 없음</td><td>모델 설치·로딩 후 자동 연결 또는 모델 찾기</td></tr><tr><td>시간초과</td><td>작은 범위·자료 수 축소·대기 시간·모델 응답</td></tr><tr><td>10054/메모리 종료</td><td>더 작은 범용 모델 선택, 대형 모델·GPU 프로그램 종료</td></tr><tr><td>본문 비어 있음</td><td>Ollama 네이티브 경로와 현재 실행 버전 일치 여부</td></tr><tr><td>품질 차단</td><td>필수 필드·실습 7개·안전·기기 절차·85점 기준</td></tr></tbody></table></div><p>먼저 1주 교재로 재현하고, 같은 조건에서 Provider 연결 테스트와 자료 요약을 분리해 원인을 좁힙니다.</p>`},
  {id:'update-rollback',category:'trouble',label:'장애 대응·업데이트',title:'업데이트와 롤백',summary:'기존 데이터 보호를 우선하는 버전 교체',body:`
    <ol><li>Studio를 종료하고 <code>data/studio.db</code>와 필요한 <code>exports</code>를 백업합니다.</li><li>새 버전은 기존 폴더에 덮어쓰지 않고 별도 폴더에 압축 해제합니다.</li><li>데이터 이전이 필요하면 복사본에서 먼저 검증합니다.</li><li>새 버전의 제목·상태 버전과 로그인·AI·자료·1주 교재를 확인합니다.</li><li>문제가 있으면 새 서버를 종료하고 보존한 이전 폴더와 DB로 돌아갑니다.</li></ol><p>Git 저장소가 아닌 배포 폴더에서는 파일 삭제·정리 명령보다 폴더 단위 보존과 명시적 백업을 우선합니다.</p>`}
];

const categoryLabels={install:'설치·시작',menu:'메뉴별 사용법',data:'데이터·백업',security:'보안·네트워크',trouble:'장애 대응·업데이트'};

function renderChapter(chapter,index){return `<details class="manual-chapter" data-chapter-id="${chapter.id}" data-category="${chapter.category}"><summary><span class="manual-chapter-no">${String(index+1).padStart(2,'0')}</span><span class="manual-chapter-copy"><small>${chapter.label}</small><b>${chapter.title}</b><em>${chapter.summary}</em></span><span class="manual-chapter-toggle" aria-hidden="true"></span></summary><div class="manual-chapter-body">${chapter.body}</div></details>`}

function renderAppliedFacts(root,chapterRows,changedIds=[]){
  const changed=new Set(changedIds);
  root.querySelectorAll('.manual-auto-facts').forEach(node=>node.remove());
  root.querySelectorAll('.manual-chapter').forEach(node=>node.classList.remove('manual-just-updated'));
  for(const row of chapterRows||[]){
    const chapter=root.querySelector(`[data-chapter-id="${row.chapter_id}"]`);if(!chapter)continue;
    const block=document.createElement('div');block.className='manual-auto-facts';
    block.innerHTML=`<div class="manual-auto-facts-head"><b>자동 분석 적용값</b><span>현재 코드·설정 기준</span></div><div class="manual-auto-facts-grid">${row.facts.map(fact=>`<span><small>${esc(fact.label)}</small><b>${esc(fact.value)}</b></span>`).join('')}</div>`;
    chapter.querySelector('.manual-chapter-body').prepend(block);
    if(changed.has(row.chapter_id)){chapter.classList.add('manual-just-updated');chapter.open=true;}
  }
}

function showManualMessage(kind,message){const panel=document.getElementById('manualUpdateMessage');panel.hidden=false;panel.className=`manual-update-message ${kind}`;panel.textContent=message;}

async function checkManualUpdates(root){
  const button=document.getElementById('manualUpdateButton'),badge=document.getElementById('manualUpdateBadge');
  try{const status=await api('/api/manual/updates');renderAppliedFacts(root,status.applied_chapters);button.hidden=!status.has_updates;
    if(status.has_updates){badge.textContent=`${status.affected_chapter_count}개 장`;showManualMessage('pending',`${status.change_count}개 운영 값이 달라졌습니다. 영향받은 ${status.affected_chapter_count}개 장만 갱신할 수 있습니다.`)}
  }catch(error){button.hidden=true;showManualMessage('error',`변경 분석 상태를 확인하지 못했습니다: ${error.message}`)}
}

async function applyManualUpdates(root){
  const button=document.getElementById('manualUpdateButton');button.disabled=true;button.textContent='변경 내용 분석·적용 중…';
  try{const result=await post('/api/manual/updates/apply',{}),changed=[...new Set(result.changes.flatMap(change=>change.chapter_ids))];renderAppliedFacts(root,result.applied_chapters,changed);button.hidden=true;
    showManualMessage('success',`${result.affected_chapter_count}개 장의 변경된 운영 값만 갱신했습니다. 적용 시각: ${result.applied_at.replace('T',' ')}`);
  }catch(error){showManualMessage('error',`내용을 갱신하지 못했습니다: ${error.message}`)}finally{button.disabled=false;button.textContent='내용 업데이터';}
}

async function downloadManualPDF(root){
  const button=document.getElementById('manualPdfButton');button.disabled=true;button.textContent='PDF 만드는 중…';
  const payload={title:'AI 강의 활용 Studio 설치 및 운영 설명서',chapters:[...root.querySelectorAll('.manual-chapter')].map((item,index)=>({index:index+1,category:item.querySelector('.manual-chapter-copy small').textContent.trim(),title:item.querySelector('.manual-chapter-copy b').textContent.trim(),summary:item.querySelector('.manual-chapter-copy em').textContent.trim(),text:item.querySelector('.manual-chapter-body').innerText.trim()}))};
  try{const response=await fetch('/api/manual/pdf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!response.ok){let message=`HTTP ${response.status}`;try{message=(await response.json()).detail||message}catch{}throw new Error(message)}
    const blob=await response.blob(),url=URL.createObjectURL(blob),link=document.createElement('a'),disposition=response.headers.get('Content-Disposition')||'',match=disposition.match(/filename="?([^";]+)"?/i);link.href=url;link.download=match?.[1]||'AI_Course_Studio_Installation_Operations_Manual.pdf';link.click();setTimeout(()=>URL.revokeObjectURL(url),0);showManualMessage('success','설치 및 운영 설명서 25개 장 전체를 PDF로 만들었습니다.');
  }catch(error){showManualMessage('error',`PDF를 만들지 못했습니다: ${error.message}`)}finally{button.disabled=false;button.textContent='전체 PDF 다운로드';}
}

export async function initOperationsManual(){
  const root=document.getElementById('manualChapters'),search=document.getElementById('manualSearch'),category=document.getElementById('manualCategory'),count=document.getElementById('manualResultCount');
  if(!root||!search||!category||!count)return;
  root.innerHTML=chapters.map(renderChapter).join('');
  const details=()=>[...root.querySelectorAll('.manual-chapter')];
  const refresh=()=>{
    const query=search.value.trim().toLocaleLowerCase('ko-KR'),selected=category.value;
    let visible=0;
    details().forEach(item=>{const matchCategory=selected==='all'||item.dataset.category===selected,matchText=!query||item.textContent.toLocaleLowerCase('ko-KR').includes(query),show=matchCategory&&matchText;item.hidden=!show;if(show){visible++;if(query)item.open=true;}});
    count.textContent=`${selected==='all'?'전체':categoryLabels[selected]} · ${visible}개 장 표시`;
  };
  search.addEventListener('input',refresh);category.addEventListener('change',refresh);
  document.getElementById('manualExpandAll').addEventListener('click',()=>details().filter(item=>!item.hidden).forEach(item=>item.open=true));
  document.getElementById('manualCollapseAll').addEventListener('click',()=>details().forEach(item=>item.open=false));
  document.getElementById('manualUpdateButton').addEventListener('click',()=>applyManualUpdates(root));
  document.getElementById('manualPdfButton').addEventListener('click',()=>downloadManualPDF(root));
  refresh();
  await checkManualUpdates(root);
}
