# SearXNG + Firecrawl 운영 설명서

## 1. SearXNG 시작

PowerShell에서 프로젝트 폴더로 이동한 뒤 실행합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start_searxng.ps1
```

처음 실행할 때 `.env.searxng`에 난수 비밀키를 자동 생성합니다. 파일 내용은 화면이나 로그에 출력하지 않습니다.

## 2. 상태 확인

```powershell
docker compose --env-file .env.searxng -f docker-compose.searxng.yml ps
Invoke-RestMethod http://127.0.0.1:8888/search?q=test`&format=json
```

Studio 로그인 후 `/api/hybrid/health`에서도 SearXNG·Firecrawl·로컬 추출 상태를 확인할 수 있습니다.

## 3. SearXNG 중지

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop_searxng.ps1
```

SearXNG가 중지돼도 Studio, SQLite, 업로드 RAG, Ollama와 LM Studio는 계속 사용할 수 있습니다.

## 4. Firecrawl 선택 설정

Firecrawl 대시보드에서 새 API 키를 발급한 뒤 프로젝트의 실제 `.env` 파일에 직접 입력합니다. 키를 채팅·브라우저·JavaScript에 입력하지 않습니다.

```env
FIRECRAWL_API_KEY=사용자가_직접_입력
FIRECRAWL_ENABLED=true
FIRECRAWL_MAX_RESULTS=5
FIRECRAWL_MONTHLY_BUDGET_ENABLED=true
FIRECRAWL_MONTHLY_REQUEST_LIMIT=100
```

변경 후 Studio 서버를 재시작합니다. 키가 없거나 `FIRECRAWL_ENABLED=false`이면 정상적인 비활성 상태입니다.

## 5. 화면 사용

1. `6. 실제 AI로 1주 교재 생성` 또는 `7. 전체·구간 교재 생성`으로 이동합니다.
2. `웹 자료 보강`을 선택합니다.
3. `무료 기본 검색` 또는 `고품질 보조 검색`을 선택합니다.
4. 무료 기본 검색은 SearXNG와 로컬 추출만 사용합니다.
5. 고품질 보조 검색은 Firecrawl이 활성화된 경우 A/B 등급 URL만 외부 추출합니다.
6. 생성 완료 후 `사용된 웹 출처 보기`에서 제목·기관·확인일·등급을 확인합니다.

## 6. 장애 확인

- `SearXNG · 연결 안 됨`: `start_searxng.ps1` 실행 및 포트 8888 확인
- `Firecrawl · API 키 없음`: 무료 기본 검색 사용 또는 서버 `.env`에 키 입력
- `무료 한도 또는 오류`: 로컬 추출로 자동 전환되며 다음 요청 전에 한도를 확인
- `출처 부족`: 첨부 자료를 추가하거나 검색 범위를 조정
- 컨테이너 로그: `docker compose --env-file .env.searxng -f docker-compose.searxng.yml logs --tail 100 searxng`

## 7. 개인정보 원칙

- 업로드 문서 본문을 검색어로 사용하지 않습니다.
- 개인정보·API 키·내부 경로가 검색어에 감지되면 제거합니다.
- 공개 URL 외에는 추출하지 않습니다.
- 근거팩에는 짧은 요약과 출처 메타데이터만 저장합니다.
