# SearXNG + Firecrawl 하이브리드 웹 RAG 구현 보고서

## 적용 버전

- AI Course Studio v1.24.0
- 적용일: 2026-08-29

## 적용 구조

```text
업로드 자료 평가
├─ 75점 이상: 내부 RAG
└─ 부족: SearXNG 검색
   ├─ 무료 기본: Trafilatura 로컬 추출
   └─ 고품질: A/B URL Firecrawl 추출
      └─ 키·한도·오류: Trafilatura 로컬 추출
         └─ 실패: 검색 요약 근거
            └─ 실패: 내부 RAG/로컬 모델
```

## 변경 파일

- `studio/services/web_search.py`: SearXNG, Firecrawl, 로컬 추출, 캐시, 요청 제한
- `studio/services/evidence_pack.py`: A/B/C 정책과 0~100 점수, 추출 fallback
- `studio/services/generation_service.py`: 근거팩 공유와 단계별 상태
- `studio/api/hybrid_routes.py`: 고품질 모드와 안전한 로컬 fallback
- `studio/schemas.py`: 중복 선언 정리와 `high_quality` 범위
- `studio/db.py`: 키·검색어를 저장하지 않는 월별 Firecrawl 요청 카운터
- `static/js/hybrid-rag.js`, `static/css/app.css`: 검색 방식·상태·출처 UI
- `docker-compose.searxng.yml`, `searxng/settings.yml`: 독립 SearXNG 서비스
- `start_searxng.ps1`, `stop_searxng.ps1`: 비밀키 자동 생성과 시작·중지
- `.env.example`, `.gitignore`, `requirements.txt`: 설정 이름과 로컬 추출 의존성
- `tests/test_hybrid_rag.py`: 검색·오류·SSRF·예산·fallback 테스트

## 실제 네트워크

- Studio: `127.0.0.1:8765` — 기존 유지
- SearXNG: `127.0.0.1:8888` → 컨테이너 `8080`
- SearXNG는 별도 Compose 프로젝트 `ai-course-studio-web-rag`에서 실행
- 기존 `docker-compose.yml`, 기존 네트워크와 데이터 볼륨은 변경하지 않음

## 보안

- Firecrawl 키는 서버 환경 변수에서만 읽고 API 응답·화면·근거팩에 저장하지 않습니다.
- 업로드 문서 본문은 SearXNG·Firecrawl로 전송하지 않습니다.
- 공개 강의 주제와 검증된 공개 URL만 외부 요청에 사용합니다.
- localhost, 사설 IP, 비 HTTP(S), 자격증명 포함 URL을 차단합니다.
- A/B 등급 URL만 Firecrawl 본문 추출 대상으로 사용합니다.
- 월별 요청 카운터에는 월·공급자·요청 수만 저장합니다.

## 호환성

- SQLite 내부 RAG: 유지
- Ollama·LM Studio: 유지
- 기존 로그인·업로드·내보내기: 유지
- 기존 Docker DB 서비스: 유지
- Firecrawl 키 없음: 정상 로컬 fallback
- SearXNG 중지: 교재 생성 전체 중단 없이 내부 RAG/로컬 생성 유지

## 테스트 결과

- Python 전체 컴파일: PASS
- JavaScript 문법 검사: PASS
- Docker Compose 구성 검사: PASS
- 전체 회귀 테스트: **50 passed, 1 deprecation warning**
- SearXNG 컨테이너: `healthy`
- 실제 JSON 검색: 20개 결과 반환
- A등급 실제 근거팩: SearXNG 검색 → Trafilatura 로컬 추출 → SQLite 저장 PASS
- Firecrawl 키 없음: `api_key_missing` 상태와 로컬 fallback PASS
- Firecrawl 429 분류 및 fallback: PASS
- 월간 요청 상한 사전 차단: PASS
- localhost·사설 IP·비 HTTP(S) 차단: PASS
- SearXNG 중지 시 빈 결과 안전 반환 및 재시작 복구: PASS
- 보호된 하이브리드 상태 API 비로그인 접근: HTTP 401 PASS
- 키 패턴 소스·로그 검사: 노출 없음
- 실행 중 Studio: v1.24.0, health PASS

## 실행 파일

- `AI_Course_Studio_v1_24_0.exe`
- SHA-256: `5205C881BD9B6672D229186E842478FD00CCF0B771A2FAA89B116D4BFACA06D8`

## 실제 자원 측정

- SearXNG 메모리: 약 109.5MiB / 제한 512MiB
- 점검 시 CPU: 0.00%, 실제 검색 순간에는 일시적으로 증가

## 알려진 제한

- 검색 품질은 SearXNG에 활성화된 외부 검색 엔진 상태에 영향을 받습니다.
- Firecrawl 무료 크레딧과 속도 제한은 서비스 정책에 따라 달라질 수 있습니다.
- Firecrawl 실제 성공 호출 테스트는 사용자가 새 키를 서버 `.env`에 직접 입력한 후 수행해야 합니다.
- 웹 출처의 발행일이 제공되지 않으면 확인일을 중심으로 표시합니다.

## 복구 기준점

- `backups/searxng_firecrawl_pre_20260829_0325.zip`
- SHA-256: `10330E87E24138E15204F08C7D8BB496092B0993DB6DFE53523ACF619620940B`
