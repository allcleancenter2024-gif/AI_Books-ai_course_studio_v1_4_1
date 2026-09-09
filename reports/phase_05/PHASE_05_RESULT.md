# PHASE 5 완료 보고 — AI Provider Gateway

## 작업 대상

- LM Studio/Ollama 공통 gateway 상태·capability 계약
- 비활성 Provider의 경계 차단
- 기존 model selection, LM Studio failover, Ollama/LM Studio native 호출 보존

## 변경 내용

- `ProviderManager`에 구현된 capability 선언(`chat`, `stream`, `vision`, `structured_output`, `embeddings`)을 추가했다.
- `list_public()` 응답에 secret-free `enabled`, `status`, `capabilities`를 추가했다.
- 상태 snapshot은 네트워크 probe를 하지 않는다. Provider가 켜져 있으나 모델이 아직 선택되지 않으면 `degraded`, 모델이 선택되면 `configured`, 환경 비활성은 `disabled`로 표시한다.
- `/api/status`에 상태와 capability를 추가하되 기존 `name`, `model`, `configured` 필드는 유지했다.
- 비활성 Provider는 `get()` gateway 경계에서 명시적인 `ProviderError`로 거부된다.

## 변경 파일

- `providers/engine.py`
- `studio/services/provider_service.py`
- `studio/api/routes.py`
- `tests/test_provider_gateway.py`

## DB / Docker / Environment 변경

- DB schema/migration 없음
- Docker, provider endpoint, Tailscale, firewall 변경 없음
- 실제 `.env` 변경 없음

## 테스트

| 테스트 | 결과 |
|---|---|
| Provider health/capability snapshot | PASS |
| Disabled Provider boundary | PASS |
| Existing health/UI and local-provider contract | PASS |
| Auto-connect contract | PASS |
| AST syntax / diff check | PASS |
| Live Ollama/LM Studio network probe | NOT RUN — local services not started |

## 발견 문제

### CRITICAL

- 없음

### HIGH

- 없음

### MEDIUM

- `stream`과 `embeddings`는 현재 gateway에서 구현되지 않아 `False`로 명시했다. 향후 capability를 `True`로 바꾸려면 실제 provider API와 테스트를 함께 추가해야 한다.
- 상태 snapshot은 의도적으로 live health probe가 아니다. 실제 연결 상태는 사용자가 명시적으로 Provider test/auto-connect를 실행할 때 확인한다.

### LOW

- 기존 Starlette/httpx 및 AnyIO deprecation warning과 workspace cache ACL 이슈가 남아 있다.

## 롤백 방법

1. `providers/engine.py`, `provider_service.py`, `studio/api/routes.py`, gateway test의 PHASE 5 hunk를 되돌린다.
2. `reports/phase_05/`를 제거한다.
3. 데이터·서비스·네트워크 롤백은 필요 없다.

## 판정

PHASE 5 RESULT: PASS WITH CONDITIONS

NEXT PHASE: READY FOR HUMAN REVIEW — PHASE 6 Hybrid RAG 검색 경로와 source/evidence metadata 평가로 진행할 수 있다.
