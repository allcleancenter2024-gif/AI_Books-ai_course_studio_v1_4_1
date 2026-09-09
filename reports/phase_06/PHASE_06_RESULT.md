# PHASE 6 완료 보고 — Hybrid RAG

## 작업 대상

- SQLite authoritative source/vector 검색 경로
- lexical + vector 결합 및 출처 귀속
- optional Web Search Router와 local fallback
- evidence pack의 출처·수집일·등급·품질 검증

## 분석 결과

- 현재 프로젝트에는 PostgreSQL FTS/pgvector가 없으므로, 근거 없이 해당 서비스를 추가하지 않았다.
- 기존 `vector_index.retrieve()`는 SQLite BLOB vector cosine 신호만 사용했다.
- source chunk별 token lexical overlap을 추가하고 vector 신호와 결합해 `hybrid_rrf` retrieval type으로 반환하도록 보완했다.
- 결과에 `source_id`, `source_name`, `score`, `retrieval_type`, 출처가 포함된 text block을 유지해 생성 context와 추적성을 보존했다.
- Web Search는 `generation_mode=web_enhanced`이고 `web_scope`가 활성인 경우에만 실행되며, 실패 시 local RAG와 생성 fallback을 유지한다.

## 변경 파일

- `studio/services/vector_index.py`
- `tests/test_rag_retrieval.py`

## 신규 파일

- `reports/phase_06/PHASE_06_RESULT.md`

## DB / Docker / Environment 변경

- 없음

## 테스트

| 테스트 | 결과 |
|---|---|
| Hybrid retrieval attribution/lexical signal | PASS |
| Evidence pack persistence and quality | PASS |
| Web Search disabled/local-only routing | PASS |
| Web failure keeps local generation | PASS |
| Search cache expiry/boundedness | PASS |
| Upload source retrieval regression | PASS |
| AST syntax / `git diff --check` | PASS |
| Live SearXNG/Firecrawl/provider network | NOT RUN — external services not started |

## 발견 문제

### CRITICAL

- 없음

### HIGH

- 없음

### MEDIUM

- 현행 lexical 신호는 SQLite에서 계산하는 compact local fallback이며 PostgreSQL Full Text Search나 pgvector의 운영 성능을 대체한다고 주장하지 않는다. 데이터 규모가 커지거나 운영 전환이 승인되면 별도 benchmark와 migration이 필요하다.
- reranker는 아직 없으며, 현재 fusion은 bounded chunk 후보에 대한 vector/lexical 결합이다.

### LOW

- pytest cache/`.pyc` 기록은 기존 workspace ACL 때문에 제한된다.
- 기존 Starlette/httpx 및 AnyIO deprecation warning이 남아 있다.

## 롤백 방법

1. `studio/services/vector_index.py`와 `tests/test_rag_retrieval.py`의 PHASE 6 변경을 되돌린다.
2. `reports/phase_06/`를 제거한다.
3. DB/vector data와 외부 검색 서비스에는 변경이 없다.

## 데이터 손실 가능성

- NONE

## 판정

PHASE 6 RESULT: PASS WITH CONDITIONS

NEXT PHASE: READY FOR HUMAN REVIEW — PHASE 7 교육 콘텐츠 Data Model의 필수 필드·학생/강사 일치·독립 로딩 검토로 진행할 수 있다.
