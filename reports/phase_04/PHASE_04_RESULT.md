# PHASE 4 완료 보고 — Job / Worker 구조

## 작업 대상

- 최대 500MB 자료 업로드 후의 parse/index 작업을 HTTP 요청과 분리
- job 상태의 SQLite 지속성, bounded worker, 취소·실패 시 임시 파일 정리

## 분석 결과

- 교재 생성과 자료 요약은 이미 SQLite `job_states` 및 daemon worker로 요청과 분리되어 있었다.
- 기존 파일 업로드는 원본 저장 뒤 parse/index를 같은 HTTP 요청에서 수행했다. 대형 PDF/PPTX 처리 시 browser request가 장시간 점유될 수 있는 HIGH 문제였다.
- 업로드 원본을 저장한 다음 parser/index worker에 전달하는 방식이 기존 SQLite authoritative 구조를 유지하는 최소 변경이다.
- 승인된 정책에 따라 staging 원본의 SHA-256, 크기, idempotency key를 job payload와 source metadata에 기록하고, `interrupted` 작업은 파일 경로·크기·체크섬을 모두 검증한 경우에만 `/jobs/{job_id}/resume`으로 재개한다.

## 변경 파일

- `.env.example`
- `studio/config.py`
- `studio/services/upload.py`
- `studio/services/source_service.py`
- `studio/api/source_routes.py`
- `studio/api/course_routes.py`
- `tests/test_regression.py`

## 신규 파일

- `reports/phase_04/PHASE_04_RESULT.md`

## 삭제 파일

- 없음

## 동작 변경

```text
Browser upload
  -> bounded disk staging (HTTP request)
  -> persistent queued job in SQLite
  -> bounded background parse/index worker
  -> complete/error/cancelled status via /api/jobs/{job_id}
```

- 새 환경 설정: `AI_COURSE_STUDIO_UPLOAD_PARSE_MAX_CONCURRENT=1`, `AI_COURSE_STUDIO_UPLOAD_PARSE_QUEUE_LIMIT=2`.
- 새 환경 설정: `AI_COURSE_STUDIO_UPLOAD_STAGING_RETENTION_SECONDS=86400` (5분~7일 범위로 제한).
- 대기열이 포화되면 파일을 저장하기 전에 `429`로 거부한다.
- 성공, 실패, 취소, thread-start 실패 모두 staging original을 삭제한다.
- 취소 시 parser 완료 후 source record를 만들지 않는다. 이미 진행 중인 parser 자체를 강제 중단하지는 않는다.
- 동일 `idempotency_key + SHA-256 + size` 재시도는 기존 source에 연결하며, 다른 key는 별도 자료로 허용한다.
- 만료 staging 파일은 새 업로드 수락 시 정리한다.

## DB 변경

- Schema 변경 없음. 기존 `job_states`에 payload/result 상태만 기록한다.

## 테스트

| 테스트 | 결과 |
|---|---|
| Upload job accepted → parse/index → completed | PASS |
| Declared oversize rejection | PASS |
| Streaming text/PPTX parse bounds | PASS |
| Missing job response | PASS |
| Existing source summary queue behavior | PASS |
| SHA-256/idempotency metadata path | PASS — upload regression and source persistence path |
| Verified interrupted-upload resume path | Static/AST PASS; live restart not executed |
| 변경 파일 AST syntax | PASS |
| `git diff --check` | PASS |

## 발견 문제

### CRITICAL

- 없음

### HIGH

- 없음

### MEDIUM

- 업로드 parse job은 서버 재시작 후 `interrupted`로 보존되며, 수동 resume 요청 시 staged input의 경로·크기·SHA-256을 검증한 경우에만 재개한다. 실제 프로세스 강제 종료 후 재시작 측정은 수행하지 않았다.

### LOW

- pytest cache/`.pyc` cache write는 기존 workspace ACL로 제한된다. source execution에는 영향이 없다.

## 롤백 방법

1. 나열한 PHASE 4 source/test/config hunk를 되돌린다.
2. `reports/phase_04/`를 제거한다.
3. 기존 SQLite data와 Docker/network configuration은 변경하지 않았으므로 데이터/서비스 롤백은 필요 없다.

## 데이터 손실 가능성

- 기존 정책과 동일하게 upload staging 원본은 분석 뒤 보관하지 않는다.
- 실패/취소 job에 남은 원본은 정리되며, 사용자는 원본을 다시 업로드할 수 있다.

## 판정

PHASE 4 RESULT: PASS WITH CONDITIONS

NEXT PHASE: READY FOR HUMAN REVIEW — AI Provider Gateway(Phase 5)는 현재 ProviderManager의 local-only contract, disabled state 및 provider failure isolation을 별도로 검토한다.
