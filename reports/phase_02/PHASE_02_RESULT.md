# PHASE 2 완료 보고 — Service Boundary

## 작업 대상

- Course API의 직접 SQLite/service-record/file 처리 경계
- Provider API의 Provider Manager 직접 제어 경계

## 분석 결과

- 기존 `studio/services/`에는 document/source, storage, generation, search/RAG, job, course, publication/export의 논리적 service 경계가 이미 존재한다.
- `course_routes.py`만 책 목록·legacy fallback·Markdown export를 직접 처리해 API와 persistence/file layer가 섞여 있었다.
- `provider_routes.py`는 인증된 Router 안에서 Provider Manager 메서드를 직접 호출했다.
- API route와 frontend 계약을 유지한 채 두 지점을 facade service로 분리하는 것이 가장 작은 안전한 변경이다.

## 변경 파일

- `studio/api/course_routes.py`
- `studio/api/provider_routes.py`

## 신규 파일

- `studio/services/book_service.py`
- `studio/services/provider_service.py`
- `reports/phase_02/PHASE_02_RESULT.md`

## 삭제 파일

- 없음

## 변경하지 않은 중요 파일

- API URL, request/response schema, authentication/RBAC
- DB schema/migration 및 SQLite data
- Docker, provider endpoint, Tailscale, firewall, actual `.env`

## DB 변경

- 없음

## 테스트

| 테스트 | 결과 |
|---|---|
| 변경 파일 AST 문법 검사 | PASS |
| Provider/교재 변경 관련 회귀 5개 | PASS |
| 앱 health/UI 및 교재 변경 API 회귀 2개 | PASS |
| Router 직접 SQLite/service-record/Provider Manager 호출 정적 검사 | PASS |
| `git diff --check` | PASS |

## 발견 문제

### CRITICAL

- 없음

### HIGH

- 없음

### MEDIUM

- 없음

### LOW

- pytest cache 및 compileall의 `.pyc` 기록은 기존 workspace ACL 때문에 제한된다. 읽기 기반 AST 검사와 pytest 실행에는 영향이 없다.
- FastAPI 테스트의 Starlette/httpx 및 AnyIO dependency deprecation warning은 기존 상태로 남아 있다.

## 롤백 방법

1. `course_routes.py`와 `provider_routes.py`의 PHASE 2 hunk를 되돌린다.
2. `book_service.py`, `provider_service.py`, `reports/phase_02/`를 제거한다.
3. 데이터, DB schema, network/service configuration rollback은 필요 없다.

## 데이터 손실 가능성

- NONE

## 다음 단계

PHASE 2 RESULT: PASS

NEXT PHASE: READY FOR HUMAN REVIEW — PostgreSQL/pgvector/MinIO 안전성(Phase 3)은 현재 SQLite authoritative 구조 및 Docker integration 역할을 보존하는 별도 설계 검토가 필요하다.
