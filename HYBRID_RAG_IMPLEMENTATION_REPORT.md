# AI 강의 활용 Studio — 하이브리드 RAG 구현 보고서

## 구현 범위

기존 SQLite 기반 내부 RAG와 LM Studio/Ollama Provider를 유지한 채, 선택형 하이브리드 RAG 계층을 추가했습니다.

- 자료 충분성 평가: 0~100점, 75/40 임계값
- 웹 검색 Provider 추상화
- Tavily 선택 연동 및 API 키 없는 DuckDuckGo 공개 검색 fallback
- 공개 URL 안전 검증 및 본문 정제
- 근거팩 생성과 출처 등급(A/B/C)
- 근거팩 SQLite 영구 저장 및 조회 API
- 근거팩 품질 점수 및 출판 가능 여부 검사
- 외부 편집 모드의 명시적 전송 동의 게이트
- 진행 상태 패널의 MutationObserver 자기 변경 루프 방지
- 1주차 내 웹 검색·근거팩 중복 호출 방지 및 근거팩 ID 결과 보존
- 웹 보강/외부 편집 모드 진행 패널 표시 안정화(동적 렌더링·모드별 노출)
- 생성 모드 필드 확장
- 하이브리드 평가·검색 API
- UI의 완전 로컬/웹 자료 보강/외부 편집 모드 선택 표시

## 변경 파일

- `studio/services/evidence_router.py`
- `studio/services/web_search.py`
- `studio/services/evidence_pack.py`
- `studio/api/hybrid_routes.py`
- `studio/application.py`
- `studio/schemas.py`
- `studio/services/generation_service.py`
- `studio/api/course_routes.py`
- `static/js/hybrid-rag.js`
- `tests/test_hybrid_rag.py`
- `HYBRID_RAG_IMPLEMENTATION_REPORT.md`

## 실행 방법

기존과 동일합니다.

```text
run_windows.bat
http://127.0.0.1:8765
```

기본 생성 모드는 `완전 로컬`입니다. 기존 생성 API를 그대로 호출해도 동작이 바뀌지 않습니다.

## 선택 설정

Tavily를 사용하려면 서버 환경 변수에만 설정합니다. 기본 `웹 자료 보강` 모드는 API 키 없이 DuckDuckGo 공개 검색 fallback을 사용합니다.

```text
AI_COURSE_STUDIO_WEB_SEARCH_PROVIDER=tavily
AI_COURSE_STUDIO_WEB_SEARCH_API_KEY=<서버 환경 변수>
AI_COURSE_STUDIO_WEB_SEARCH_TIMEOUT=15
```

API 키는 프론트엔드, 응답 JSON, 로그에 기록하지 않습니다. 공급자를 `disabled`로 설정하거나 검색 요청이 실패하면 내부 RAG/로컬 모델로 계속 진행합니다.

## API

- `POST /api/hybrid/evaluate`: 첨부자료 충분성 평가
- `POST /api/hybrid/search`: 선택형 웹 검색과 근거팩 생성
- `GET /api/hybrid/health`: 검색 Provider 활성 상태 확인
- `GET /api/hybrid/evidence-packs/{pack_id}`: 저장된 근거팩 조회
- `GET /api/hybrid/evidence-packs/{pack_id}/quality`: 근거팩 품질 검사

기존 `/api/ai/week`, `/api/ai/book` 요청은 `generation_mode`, `web_scope` 선택 필드를 추가로 받을 수 있으며 기존 요청 형식과 호환됩니다.

## 안전 동작

- 완전 로컬 모드에서는 웹 검색을 호출하지 않습니다.
- 검색 API 키가 없어도 공개 검색 fallback을 시도하며, 실패 시 오류가 아니라 로컬 fallback으로 처리합니다.
- 공개 URL만 허용하고 localhost·사설 IP·리디렉션 대상 사설 IP를 차단합니다.
- HTML 스크립트·스타일·메뉴·푸터·사이드바를 제거합니다.
- 웹 자료는 모델 지시문이 아닌 참고자료로 삽입합니다.
- 웹 검색 실패 시 기존 내부 RAG 문맥을 유지합니다.
- 기존 파일·사용자 자료·SQLite 레코드는 삭제하거나 덮어쓰지 않았습니다.
- Docker, Tailscale, 방화벽, 포트 바인딩은 변경하지 않았습니다.

## 테스트 결과

```text
Python compileall: PASS
JavaScript syntax check: PASS
pytest: 40 passed, 1 warning
```

경고는 Starlette/httpx 호환성 안내이며 기능 실패가 아닙니다.

## 남은 제한 사항

1. 검색 Provider는 DuckDuckGo 공개 검색 fallback과 Tavily 어댑터를 제공합니다.
2. 근거팩은 SQLite `evidence_packs`/`evidence_items` 테이블에 저장되며 만료 정리 작업은 후속 단계입니다.
3. 외부 최종 편집 모드는 선택 UI와 요청 필드 및 동의 게이트까지 구현되었지만, 실제 OpenAI/Gemini/Claude 호출은 의도적으로 연결하지 않았습니다. 외부 전송 동의·비용 상한·비식별화 정책 승인 후 별도 구현해야 합니다.
4. 주장 단위 자동 인용 검증과 단원별 부분 재생성은 후속 단계입니다.
5. 작업 취소·재개와 영구 작업 큐는 아직 기존 메모리 JobStore를 사용합니다.
6. 공식 도메인 허용 목록은 운영 정책 확정 후 추가해야 합니다.

## 복구 방법

구현 전 다음 백업을 생성했습니다.

`backups/hybrid_rag_pre_implementation_20260829_010117.zip`

문제가 발생하면 서버를 중지한 뒤 해당 ZIP에서 소스·설정 파일만 복원합니다. `data/`, `uploads/`, `exports/` 사용자 데이터는 백업에 포함하지 않았으며 삭제 대상이 아닙니다.

## 다음 승인 필요 항목

- Tavily API 사용 승인 및 월간 비용 상한
- 공식·전문기관 허용 도메인 목록
- 웹 자료 자동 검색 기본 활성화 여부
- 외부 AI 최종 편집 Provider와 전송 동의 화면
- Evidence Pack 영구 저장 마이그레이션
- 취소·재개 작업 큐 구현 우선순위
