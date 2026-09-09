# AI 강의 활용 Studio v1.24.0
# 구조 안정화 및 최종 구현 마스터 작업 지시서

- 문서 버전: 1.0
- 기준일: 2026-09-09
- 적용 대상: AI 강의 활용 Studio v1.24.0
- 작업 목적: 기존 기능을 보존하면서 프로그램을 장기 운영 가능한 구조로 안정화한다.
- 최우선 전략: **기능 추가보다 구조 안정화**
- 기본 방식: **분석 → 계획 → 최소 변경 → 테스트 → 보고 → 승인 → 다음 단계**
- 적용 방식: Codex CLI / 개발 에이전트 / 수동 개발 공통
- 권장 운영 환경: Windows 개발환경 + Docker + PostgreSQL + pgvector + MinIO + Ollama + LM Studio
- 외부 접근 원칙: Web/API Gateway만 공개하고 DB·스토리지·AI Provider는 직접 공개하지 않는다.

---

# 0. 최종 목표

현재 AI 강의 활용 Studio를 다음과 같은 구조로 안정화한다.

```text
                 AI 강의 활용 Studio
                         │
          ┌──────────────┴──────────────┐
          │                             │
     User Interface                 Admin UI
          │                             │
          └──────────────┬──────────────┘
                         ▼
                Web / API Gateway
                         │
────────────────────────────────────────────────────
                    Application
────────────────────────────────────────────────────
 Course Service
 Document Service
 Generation Service
 Export Service
 Publication Service
 Learner Profile Service
────────────────────────────────────────────────────
                         │
                         ▼
────────────────────────────────────────────────────
                   Quality Gate
────────────────────────────────────────────────────
 Schema Validation
 Fact Validation
 Source Validation
 Safety Validation
 Copyright Validation
 Accessibility Validation
 Device Validation
 Human Approval
────────────────────────────────────────────────────
               │             │             │
               ▼             ▼             ▼
          Hybrid RAG     AI Gateway     Job Service
               │             │             │
       PostgreSQL FTS     Provider       Workers
          + pgvector      Adapters
               │        /    |     \
               │    Ollama LM Studio Cloud
               │
────────────────────────────────────────────────────
 PostgreSQL      pgvector       MinIO       Redis/Queue
────────────────────────────────────────────────────
                         │
                      Backup
```

---

# 1. 절대 작업 원칙

다음 규칙은 모든 Phase보다 우선한다.

1. 기존 프로그램을 먼저 분석한다.
2. 분석이 끝나기 전에 구조를 변경하지 않는다.
3. 기존 정상 기능을 삭제하지 않는다.
4. 대규모 일괄 재작성보다 작은 모듈 단위 변경을 우선한다.
5. 한 Phase가 PASS 되기 전에 다음 Phase로 진행하지 않는다.
6. 테스트 실패 시 즉시 작업을 중단하고 BLOCKED로 보고한다.
7. 운영 데이터가 존재할 경우 임의 초기화, 삭제, 재생성을 금지한다.
8. PostgreSQL Schema 변경은 별도 Migration으로 수행한다.
9. 기존 Migration 파일을 수정하지 않는다.
10. MinIO 기존 Object를 자동 삭제하지 않는다.
11. API Key, Password, Token, Secret은 소스코드에 기록하지 않는다.
12. `.env` 실제 파일을 Git에 커밋하지 않는다.
13. PostgreSQL, MinIO, Redis, Ollama, LM Studio 포트를 인터넷에 직접 공개하지 않는다.
14. 외부 사용자는 Web/API Gateway를 통해서만 접근한다.
15. UI가 PostgreSQL, MinIO, Ollama, LM Studio를 직접 호출하지 않게 한다.
16. AI Provider 장애가 Studio 전체 장애로 이어지지 않게 한다.
17. 500MB급 파일은 단일 HTTP 요청 안에서 전체 처리하지 않는다.
18. AI 생성 결과를 검수 없이 Publisher로 보내지 않는다.
19. 사용자의 실제 개인정보를 테스트 데이터로 사용하지 않는다.
20. 모든 변경에는 테스트 결과와 롤백 방법을 기록한다.
21. Human Approval이 필요한 단계는 자동 승인하지 않는다.
22. 구조 변경 전 Git 작업트리와 데이터 백업 상태를 확인한다.
23. 기존 사용자 변경사항을 덮어쓰지 않는다.
24. 파일 전체 덮어쓰기는 특별한 이유가 없으면 금지한다.
25. 새 Framework 도입은 기존 구조로 해결할 수 없을 때만 검토한다.

---

# 2. 이번 안정화 작업에서 추가를 보류할 기능

다음 항목은 핵심 안정화가 끝날 때까지 원칙적으로 추가하지 않는다.

- 새로운 AI Provider
- 새로운 Vector DB
- 새로운 Agent Framework
- 새로운 Workflow Framework
- 새로운 대형 Dashboard
- 새로운 인증 Framework
- 새로운 Storage Backend
- 불필요한 Microservice 분리
- 실험 목적의 신규 Database
- 기존 기능과 중복되는 자동화 도구

예외:

- 치명적 보안 문제 해결
- 현재 기능 정상화에 반드시 필요한 Dependency
- 테스트 자동화를 위해 필요한 최소 도구

---

# 3. 전체 Phase

```text
PHASE 0   Read-Only 전체 감사
PHASE 1   Configuration / Environment 표준화
PHASE 2   Service Boundary 고정
PHASE 3   Database / pgvector / MinIO 안전성 확정
PHASE 4   Job / Worker 구조 완성
PHASE 5   AI Provider Gateway 안정화
PHASE 6   Hybrid RAG 안정화
PHASE 7   교육 콘텐츠 Data Model 구조화
PHASE 8   Quality Gate 구현
PHASE 9   Learner Profile + Device-aware UI
PHASE 10  Publication Gate 구현
PHASE 11  Publisher / Public Domain / HTTPS
PHASE 12  UI/UX 단순화 및 상태 Dashboard
PHASE 13  Security / Backup / Recovery
PHASE 14  전체 회귀·성능·장애 테스트
PHASE 15  운영 문서·Release Gate
```

---

# PHASE 0 — Read-Only 전체 감사

## 목적

프로그램을 수정하지 않은 상태에서 현재 구조를 정확하게 파악한다.

## 작업 모드

```text
READ ONLY
NO CODE CHANGE
NO DB CHANGE
NO ENV CHANGE
NO NETWORK CHANGE
```

## 반드시 확인할 항목

1. 프로젝트 전체 디렉터리 구조
2. Backend 진입점
3. Frontend 진입점
4. API Router 구조
5. Service 구조
6. Repository 구조
7. Database Model
8. Migration
9. PostgreSQL 연결
10. pgvector 연결
11. MinIO 연결
12. Redis 또는 Queue 사용 여부
13. RAG Pipeline
14. Ollama 연결
15. LM Studio 연결
16. Cloud Provider 연결
17. File Upload
18. Parser
19. Chunk
20. Embedding
21. Indexing
22. Generation
23. Export
24. Publisher
25. Authentication
26. Authorization
27. Logging
28. Error Handling
29. Retry
30. Timeout
31. Docker / docker-compose
32. Port
33. `.env` / `.env.example`
34. Test
35. Backup
36. Public URL / Domain
37. Tailscale 또는 기타 Private Network
38. Browser responsive structure
39. Accessibility
40. Deprecated / duplicate code

## 특별 탐지 항목

다음 구조를 찾는다.

```text
God Object
Massive main.py
Massive Router
UI → DB 직접 접근
UI → MinIO 직접 접근
UI → AI Provider 직접 접근
Router → SQL 직접 실행
Router → Provider SDK 직접 실행
Provider별 중복 코드
RAG와 Generation 강결합
Upload와 Generation 동기 결합
Publisher와 AI 생성 직접 연결
Configuration 하드코딩
Secret 하드코딩
운영/테스트 DB 혼합
운영/테스트 MinIO Prefix 혼합
```

## 실행 가능한 테스트

코드를 수정하지 않고 현재 존재하는 테스트만 실행한다.

예:

```bash
pytest
npm test
npm run lint
npm run build
```

실제 프로젝트에서 존재하는 명령만 사용한다.

## 산출물

```text
reports/
└─ phase_00/
   ├─ CURRENT_ARCHITECTURE.md
   ├─ DEPENDENCY_MAP.md
   ├─ PORT_MAP.md
   ├─ ENVIRONMENT_AUDIT.md
   ├─ DATA_FLOW.md
   ├─ SECURITY_FINDINGS.md
   ├─ PERFORMANCE_RISKS.md
   ├─ DUPLICATION_REPORT.md
   ├─ TEST_BASELINE.md
   └─ PHASE_00_RESULT.md
```

## PASS 조건

- 소스 변경: 0건
- DB 변경: 0건
- MinIO 변경: 0건
- 현재 구조 지도 작성 완료
- 테스트 기준선 기록 완료
- 위험도 CRITICAL/HIGH/MEDIUM/LOW 분류 완료

## BLOCKED 조건

- 프로젝트 Root를 확정할 수 없음
- 핵심 실행파일 탐지 실패
- DB 종류를 확정할 수 없음
- 기존 테스트 자체가 실행 불가
- 운영/테스트 환경 구분 불가

---

# PHASE 1 — Configuration / Environment 표준화

## 목적

코드에 흩어진 URL, Port, Model, Secret, 기능 플래그를 중앙 Configuration으로 통합한다.

## 권장 환경변수

```env
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8765

PUBLIC_ACCESS=false
PUBLIC_BASE_URL=

DATABASE_URL=
POSTGRES_HOST=
POSTGRES_PORT=5432

RAG_BACKEND=pgvector
RAG_BACKEND_ENABLED=true
RAG_PGVECTOR_CAPABILITY_VERIFIED=false
RAG_PGVECTOR_FALLBACK_TO_SQLITE=false
RAG_PGVECTOR_DATABASE_URL=

MINIO_ENABLED=false
MINIO_ENDPOINT=http://127.0.0.1:9000
MINIO_BUCKET=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_SECURE=false

OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://127.0.0.1:11434

LMSTUDIO_ENABLED=true
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1

DEFAULT_AI_PROVIDER=auto

WEB_SEARCH_ENABLED=false

MAX_UPLOAD_SIZE_MB=500
```

실제 변수 이름은 기존 코드와 충돌하지 않도록 PHASE 0 결과를 기준으로 결정한다.

## 작업

- 하드코딩된 Port 탐지
- 하드코딩된 URL 탐지
- 하드코딩된 Model Name 탐지
- API Key 하드코딩 탐지
- Secret 하드코딩 탐지
- 중복 Configuration 탐지
- Config Loader 하나로 통합
- 안전한 Default 적용
- 설정 Validation 추가
- `.env.example` 작성 또는 정비

## 금지

- 실제 Password를 `.env.example`에 기록
- 운영 DB URL 자동 생성
- 테스트 DB를 운영 DB로 자동 승격
- MinIO Credential 자동 생성 후 운영 적용

## PASS

- Secret 하드코딩 0건
- Port 하드코딩 제거 또는 명시적 예외 기록
- Config Validation PASS
- 기존 실행 PASS

---

# PHASE 2 — Service Boundary 고정

## 목적

Studio가 거대한 단일 프로그램으로 성장하는 것을 방지한다.

## 목표

```text
app/
├─ api/
├─ application/
├─ core/
├─ domain/
├─ services/
│  ├─ course/
│  ├─ document/
│  ├─ rag/
│  ├─ search/
│  ├─ generation/
│  ├─ publication/
│  ├─ export/
│  └─ storage/
├─ providers/
├─ repositories/
├─ workers/
├─ db/
└─ ui/
```

현재 Framework가 이 구조와 다르면 기존 구조에 맞춰 논리적 경계만 적용한다.

## 핵심 규칙

```text
UI
 ↓
API / Application
 ↓
Service
 ↓
Repository / Provider
 ↓
Infrastructure
```

금지:

```text
UI → DB
UI → MinIO
UI → Ollama
UI → LM Studio

Router → raw SQL
Router → Provider SDK
Router → MinIO SDK
```

## 작업 우선순위

1. Document Service
2. Storage Service
3. AI Provider Service
4. RAG Service
5. Job Service
6. Course Service
7. Publication Service
8. Export Service

## PASS

- UI 직접 Infrastructure 접근 0건 또는 예외 문서화
- Router 비즈니스 로직 감소
- 기존 API Contract 유지
- 회귀 테스트 PASS

---

# PHASE 3 — PostgreSQL / pgvector / MinIO 안전성 확정

## 목적

운영 데이터와 테스트 데이터를 절대 혼합하지 않는 저장구조를 확정한다.

## PostgreSQL 역할

- 사용자/프로필
- 프로젝트
- 강의
- 차시
- 문서 Metadata
- Chunk Metadata
- Source Metadata
- Job
- Publication
- Audit
- Approval

## pgvector 역할

- Document Embedding
- Chunk Embedding
- Query Embedding

## MinIO 역할

- PDF
- PPTX
- DOCX
- HTML
- 이미지
- 오디오
- 영상
- Export 파일
- Thumbnail
- Derived Asset

## 금지

대형 Binary를 PostgreSQL에 저장하지 않는다.

## 데이터 분리

반드시 구분:

```text
development
test
staging
production
```

## 테스트 환경

Production Prefix를 사용하지 않는다.

예:

```text
tests/
verification/
development/
```

## 데이터 무결성 테스트

- DB Transaction rollback
- Object upload 실패
- DB 성공 + Object 실패
- Object 성공 + DB 실패
- Orphan 탐지
- Duplicate Object
- Checksum
- Metadata mismatch

## PASS

- 운영/테스트 DB 분리 확인
- 운영/테스트 Object Prefix 분리
- Transaction/rollback PASS
- Orphan 판정 PASS
- SHA-256 또는 동등 무결성 검사 PASS

---

# PHASE 4 — Job / Worker 구조 완성

## 목적

대형 파일 처리와 AI 생성을 동기 HTTP Request에서 분리한다.

## 금지 구조

```text
Upload
→ Parse
→ Chunk
→ Embed
→ Index
→ Generate
```

하나의 Request에서 전체 실행하지 않는다.

## 목표 구조

```text
Upload
 ↓
Job 생성
 ↓
Queue
 ↓
┌──────────────────┐
Parser Worker
Chunk Worker
Embedding Worker
Media Worker
Generation Worker
Export Worker
Publication Worker
└──────────────────┘
```

## Job 상태

```text
queued
uploading
parsing
chunking
embedding
indexing
generating
validating
exporting
publishing
completed
failed
cancelled
```

## Job 필드

- id
- type
- status
- progress
- current_stage
- started_at
- updated_at
- completed_at
- error_code
- error_message
- retry_count
- max_retry
- owner
- project_id
- source_id

## 대용량 Upload

검토:

- Multipart Upload
- Chunk Upload
- Resume
- Retry
- Checksum
- Temporary storage
- Cleanup

## 실패 정책

각 Worker 실패가 Studio 전체 종료로 이어지면 FAIL.

## PASS

- 500MB 목표 파일 처리 구조가 비동기
- Retry 가능
- Cancel 가능
- 진행상태 저장
- Worker 하나 종료 시 Studio 유지

---

# PHASE 5 — AI Provider Gateway 안정화

## 목적

Ollama, LM Studio, Cloud Provider 차이를 Application에서 제거한다.

## 공통 Interface 예

```python
generate()
chat()
stream()
embed()
vision()
health()
list_models()
capabilities()
```

## Provider 상태

```text
healthy
degraded
unavailable
disabled
```

## auto 정책 예

```text
Embedding
→ Ollama 우선

Background Summary
→ Ollama 우선

고품질 장문 생성
→ LM Studio 우선

Vision
→ capability 확인 후 선택

Provider 장애
→ 명시된 fallback 정책
```

## 필수 기능 탐지

Provider마다 확인:

- context length
- streaming
- vision
- embedding
- file input
- structured output
- timeout
- health
- model availability

## 중요

LM Studio와 Ollama의 대형 모델을 동시에 GPU에 상주시켜 VRAM 부족을 만들지 않는다.

## PASS

- Provider 직접 호출 위치 최소화
- Provider Gateway를 통한 호출
- Provider 장애 시 Studio 실행 유지
- Unsupported Capability 오류 명확화

---

# PHASE 6 — Hybrid RAG 안정화

## 목표

```text
Question
 ↓
Query Analyzer
 ↓
┌───────────────┐
FTS          Vector
│               │
└──────┬────────┘
       ↓
     Fusion
       ↓
    Reranker
       ↓
 Context Builder
       ↓
      LLM
```

## 기본 검색

- PostgreSQL Full Text Search
- pgvector Semantic Search

## Fusion

우선 RRF 적용.

Reranker는 필요할 때 추가한다.

## Metadata

최소:

```text
document_id
source_name
source_type
page
chunk_id
score
retrieval_type
created_at
license
verified_at
```

## Web Search Router

모든 질문에 Web Search를 실행하지 않는다.

외부 검색 후보:

- 최신
- 오늘
- 현재
- 가격
- 법률
- 버전
- 업데이트
- Local RAG confidence 낮음

## PASS

동일 Question Set에서 비교:

```text
Vector-only
FTS-only
Hybrid
Hybrid + Rerank
```

출처 연결 정확도를 평가한다.

---

# PHASE 7 — 교육 콘텐츠 Data Model 구조화

## 목적

하나의 긴 Markdown 원고를 프로그램의 핵심 데이터 모델로 사용하지 않는다.

## 핵심 Entity

```text
Course
Module
Week
Lesson
LearnerProfile
LearningObjective
Activity
DeviceInstruction
Prompt
ExpectedResult
Verification
SafetyNote
Source
AccessibilityRule
InstructorNote
Approval
Publication
```

## Lesson 필수 필드

- 대상
- 기기
- 목표
- 준비물
- 예상 시간
- 단계
- 성공 신호
- 검증
- 안전
- 출처
- 강사용 안내
- 복구 방법

## 기본 학습 구조

```text
보기
→ 따라하기
→ 혼자하기
→ 설명하기
```

## 대상 구성

공통 핵심 60%

대상별 사례 25%

기기별 절차 15%

## PASS

- 필수 필드 DB/Schema 정의
- 빈 필드 탐지
- 학생용/강사용 목표 일치 검사
- Week/Lesson 독립 로딩 가능

---

# PHASE 8 — Quality Gate 구현

## 목적

AI가 생성했다고 바로 완성품으로 인정하지 않는다.

## Pipeline

```text
AI Draft
 ↓
Schema Validation
 ↓
Fact Validation
 ↓
Source Validation
 ↓
Safety Validation
 ↓
Copyright Validation
 ↓
Accessibility Validation
 ↓
Device Validation
 ↓
Instructor Review
```

## 자동 BLOCK 조건

다음 하나라도 충족하면 Publication 불가.

- 목표 없음
- 준비물 없음
- 단계 없음
- 성공 기준 없음
- 검증 없음
- 안전 정보 없음
- 현재 정보인데 Source 없음
- 확인일 없음
- 기기 표시 없음
- 개인정보 위험
- 의료/금융 고위험 조언
- 저작권 문제
- 학생/강사 목표 불일치
- 깨진 Markdown
- 깨진 JSON
- 비어 있는 결과 Field

## 상태

```text
draft
validation_failed
needs_review
approved
rejected
publish_ready
```

## PASS

- AI Draft와 Published Content가 별도 상태
- 검수 결과 저장
- Human Approval 저장
- 검수 없이 Publish 불가능

---

# PHASE 9 — Learner Profile + Device-aware UI

## 목적

중학생부터 60대까지 하나의 화면과 동일한 설명으로 처리하지 않는다.

## Learner Profile

최소 입력:

```text
대상
중학생
고등학생
성인
40~50대
60대 이상

기기
PC
Android
iPhone/iPad

디지털 경험
처음
도움 있으면 가능
혼자 가능
```

연령만으로 능력을 단정하지 않는다.

## 기기별 UI

```text
PC
Android
iPhone / iPad
```

각 단계:

- 정확한 버튼명
- 화면 위치
- 수행 행동 하나
- 성공 신호
- 실패 복구

## 접근성

- 모바일 본문 최소 18px 권장
- 200% 확대 대응
- Keyboard Navigation
- Screen Reader
- 색상만으로 상태 구분 금지
- 핵심 Touch Target 44px 수준 권장
- 320px 폭에서도 핵심 내용 접근

## PASS

대표 기기에서 실제 핵심 실습 완료.

---

# PHASE 10 — Publication Gate 구현

## 목적

Publisher와 AI 생성기를 직접 연결하지 않는다.

## 절대 금지

```text
AI Generate
 ↓
Publish
```

## 목표

```text
Generate
 ↓
Quality Gate
 ↓
Human Approval
 ↓
Publication Gate
 ↓
Publisher
```

## Publication Gate 확인

- Quality PASS
- Source PASS
- Safety PASS
- Copyright PASS
- Accessibility PASS
- Device PASS
- Instructor Approval
- Version 생성
- Validation date
- Published by
- Rollback version

## 상태

```text
draft
review
approved
publish_ready
publishing
published
publish_failed
withdrawn
```

## PASS

승인 없는 Published 상태 생성이 불가능해야 한다.

---

# PHASE 11 — Publisher / Public Domain / HTTPS

## 목적

공개 도메인이 연결되어도 내부 서비스는 보호한다.

## 구조

```text
Internet
 ↓
Domain
 ↓
HTTPS
 ↓
Caddy / Nginx
 ↓
Web/API Gateway
 ↓
Studio Internal Network
```

## Public

허용:

```text
80
443
```

상황에 따라 80은 HTTPS Redirect 용도로만 사용.

## 직접 공개 금지

```text
PostgreSQL
MinIO
Redis
Ollama
LM Studio
Internal Admin
```

## 설정

예:

```env
PUBLIC_ACCESS=true
PUBLIC_BASE_URL=https://studio.example.com
```

실제 Domain이 없으면:

```env
PUBLIC_ACCESS=false
PUBLIC_BASE_URL=
```

상태로도 Studio가 정상 작동해야 한다.

## 기능

Gateway에서 처리:

- TLS
- Reverse Proxy
- Security Header
- Rate Limit
- Upload limit
- OAuth Callback
- Webhook
- Request ID

## PASS

- Domain 없어도 Local Mode 정상
- Domain 연결 시 HTTPS
- 내부 Port 외부 노출 없음

---

# PHASE 12 — UI/UX 단순화 및 상태 Dashboard

## 목적

기술 기능이 많아져도 사용자 화면은 단순하게 유지한다.

## 권장 첫 화면

```text
AI 강의 활용 Studio

[ 새 강의 만들기 ]

[ 내 강의 ]

[ 자료실 ]

[ AI 설정 ]

[ 출판하기 ]

[ 관리 ]
```

일반 화면에서 다음 기술 용어를 최소화한다.

- pgvector
- MinIO
- Embedding
- RRF
- Chunk
- Provider Adapter

관리자 화면에서는 표시 가능.

## Job Dashboard

최소:

```text
작업명
상태
진행률
현재 단계
시작 시간
최근 업데이트
오류
재시도
취소
```

## Service Health

관리자용:

```text
Studio
PostgreSQL
pgvector
MinIO
Queue
Ollama
LM Studio
Web Search
Publisher
```

상태:

```text
Healthy
Degraded
Unavailable
Disabled
```

## PASS

사용자가 작업이 멈춘 것인지 진행 중인지 구별할 수 있어야 한다.

---

# PHASE 13 — Security / Backup / Recovery

## Security

확인:

- Secret
- Authentication
- Authorization
- CSRF
- CORS
- Rate Limit
- Upload type validation
- MIME validation
- File extension validation
- Path traversal
- Archive bomb
- Request size
- Timeout
- Injection
- SQL Injection
- Log secret leakage
- Error detail leakage

## Network

Default Deny Inbound 원칙 검토.

## Backup

별도:

```text
PostgreSQL Backup
MinIO Backup
Configuration Backup
Migration Backup
Course Export Backup
```

## 복구 테스트

Backup 존재만 확인하지 말고 Restore를 실제 테스트한다.

## Disaster Test

- PostgreSQL 중단
- MinIO 중단
- Queue 중단
- Ollama 중단
- LM Studio 중단
- Web Search 실패
- Parser 실패
- Embedding 실패
- Network 단절
- Worker 비정상 종료

## 핵심 기준

하나의 서비스 실패가 가능한 한 전체 프로그램 종료로 확산되지 않게 한다.

---

# PHASE 14 — 전체 회귀·성능·장애 테스트

## Functional

- 새 강의
- 강의 저장
- 강의 불러오기
- 수정
- 문서 Upload
- PDF
- PPTX
- DOCX
- 이미지
- RAG
- Hybrid Search
- Web Search
- Ollama
- LM Studio
- Provider fallback
- Export MD
- Export HTML
- Export PDF
- Publisher
- Publication rollback

## Performance

최소 구간:

```text
10MB
50MB
100MB
250MB
500MB
```

각각:

- Upload
- Parse
- Memory
- CPU
- Disk
- Queue
- Timeout
- Recovery

## Browser

대표:

- Chrome Desktop
- Edge Desktop
- Android Chrome
- iPhone Safari
- Tablet

## Viewport

최소:

```text
320
375
768
1024
1440
```

## Accessibility

- Keyboard only
- Focus
- Screen Reader
- 200% Zoom
- Contrast
- Form Label
- Error Message

## PASS

CRITICAL 0건.

HIGH는 Release 전에 해결.

MEDIUM은 Known Issues에 기록 가능하나 사용자 핵심 흐름을 방해하면 해결 후 Release.

---

# PHASE 15 — 운영 문서 및 Release Gate

## 필수 문서

```text
ARCHITECTURE.md
DEPLOYMENT.md
CONFIGURATION.md
DATABASE.md
RAG_PIPELINE.md
AI_PROVIDER.md
JOB_WORKER.md
PUBLISHER.md
SECURITY.md
BACKUP_RESTORE.md
TROUBLESHOOTING.md
TESTING.md
KNOWN_ISSUES.md
CHANGELOG.md
RELEASE_CHECKLIST.md
```

## Release Checklist

- [ ] Phase 0 Audit 완료
- [ ] Service Boundary 완료
- [ ] Config 표준화
- [ ] Production/Test DB 분리
- [ ] MinIO 분리
- [ ] Job/Worker 완료
- [ ] Provider Gateway 완료
- [ ] Hybrid RAG 검증
- [ ] Quality Gate 완료
- [ ] Human Approval 완료
- [ ] Publication Gate 완료
- [ ] HTTPS 검증
- [ ] 내부 Port 비공개
- [ ] Backup 생성
- [ ] Restore 성공
- [ ] Regression PASS
- [ ] Performance PASS
- [ ] Accessibility PASS
- [ ] Browser PASS
- [ ] Security Critical 0
- [ ] Rollback 검증
- [ ] 운영 문서 완료

---

# 4. 각 Phase 공통 실행 형식

모든 단계에서 아래 순서를 지킨다.

```text
1. ANALYZE
2. REPORT
3. PLAN
4. HUMAN REVIEW
5. MINIMAL CHANGE
6. TEST
7. RESULT
8. READY / BLOCKED
```

---

# 5. 공통 완료 보고 양식

```markdown
# PHASE X 완료 보고

## 작업 대상
- ...

## 분석 결과
- ...

## 변경 파일
- ...

## 신규 파일
- ...

## 삭제 파일
- 없음 / ...

## 변경하지 않은 중요 파일
- ...

## DB 변경
- 없음 / Migration ...

## MinIO 변경
- 없음 / ...

## Environment 변경
- 없음 / ...

## 테스트

| 테스트 | 결과 |
|---|---|
| 기존 실행 | PASS / FAIL |
| 신규 기능 | PASS / FAIL |
| Regression | PASS / FAIL |
| DB 무결성 | PASS / FAIL |
| Security | PASS / FAIL |
| Browser | PASS / FAIL |

## 발견 문제

### CRITICAL
- 없음

### HIGH
- ...

### MEDIUM
- ...

### LOW
- ...

## 롤백 방법
1. ...
2. ...

## 데이터 손실 가능성
- NONE / ...

## 다음 단계
READY / BLOCKED

## BLOCKED 사유
- ...
```

---

# 6. Codex / 개발 에이전트용 마스터 실행 프롬프트

아래 지시를 프로젝트 Root에서 사용한다.

```markdown
당신은 AI 강의 활용 Studio v1.24.0의 Senior Software Architect,
Reliability Engineer, Security Engineer, AI/RAG Engineer 역할을 수행한다.

최우선 목표는 새로운 기능 추가가 아니다.

현재 프로그램의 기존 기능과 사용자 데이터를 보존하면서
장기 유지보수 가능한 안정적인 구조로 만드는 것이 목표다.

반드시 다음 원칙을 지켜라.

1. 현재 저장소와 AGENTS.md 및 프로젝트 규칙을 먼저 읽는다.
2. PHASE 0 Read-Only Audit부터 시작한다.
3. 감사가 끝나기 전 코드를 변경하지 않는다.
4. 기존 기능 삭제를 금지한다.
5. 사용자 수정사항을 덮어쓰지 않는다.
6. 운영 DB와 테스트 DB를 절대 혼합하지 않는다.
7. 운영 MinIO와 테스트 Object Prefix를 절대 혼합하지 않는다.
8. Database Schema 변경은 Migration으로만 수행한다.
9. API Key, Token, Password를 코드에 기록하지 않는다.
10. UI에서 DB, MinIO, Ollama, LM Studio를 직접 접근하지 않는다.
11. Application → Service → Repository/Provider 경계를 유지한다.
12. 500MB급 파일 처리는 Job/Worker 방식으로 분리한다.
13. Provider 장애가 전체 프로그램 장애가 되지 않게 한다.
14. AI 생성 결과는 Quality Gate와 Human Approval 없이 Publisher로 전달하지 않는다.
15. Public 서비스는 Web/API Gateway 하나만 외부에 공개한다.
16. PostgreSQL, MinIO, Redis, Ollama, LM Studio는 직접 공개하지 않는다.
17. 한 Phase의 테스트가 실패하면 다음 Phase로 진행하지 않는다.
18. 각 Phase 종료 시 PASS/BLOCKED 판정을 한다.
19. 모든 변경에 롤백 절차를 제공한다.
20. CRITICAL 위험을 발견하면 변경보다 먼저 보고한다.

작업 순서:

PHASE 0  Read-Only 전체 감사
PHASE 1  Configuration 표준화
PHASE 2  Service Boundary
PHASE 3  PostgreSQL/pgvector/MinIO
PHASE 4  Job/Worker
PHASE 5  AI Provider Gateway
PHASE 6  Hybrid RAG
PHASE 7  Education Data Model
PHASE 8  Quality Gate
PHASE 9  Learner Profile / Device UI
PHASE 10 Publication Gate
PHASE 11 Publisher / HTTPS
PHASE 12 UI/UX / Progress Dashboard
PHASE 13 Security / Backup / Recovery
PHASE 14 Regression / Performance / Failure Test
PHASE 15 Documentation / Release Gate

지금은 PHASE 0만 수행하라.

PHASE 0에서 파일을 수정하지 마라.

현재 구조, 파일 경로, 의존성, DB, RAG, Provider, Upload,
Job, Publisher, Network, Security, Test 상태를 실제 코드 근거로 조사하라.

결과를 다음 문서 형태로 제시하라.

reports/phase_00/
- CURRENT_ARCHITECTURE.md
- DEPENDENCY_MAP.md
- PORT_MAP.md
- ENVIRONMENT_AUDIT.md
- DATA_FLOW.md
- SECURITY_FINDINGS.md
- PERFORMANCE_RISKS.md
- DUPLICATION_REPORT.md
- TEST_BASELINE.md
- PHASE_00_RESULT.md

PHASE 0 완료 후 다음 단계로 자동 진행하지 마라.

최종 출력에서 반드시 표시한다.

PHASE 0 RESULT: PASS / BLOCKED
NEXT PHASE: READY / NOT READY
```

---

# 7. 권장 실제 적용 순서

현재 프로젝트에서 바로 전체 구조를 변경하지 않는다.

첫 실행은 다음만 한다.

```text
PHASE 0
Read-Only Audit
```

그 결과를 검토한 뒤

```text
PHASE 1
Configuration
```

으로 이동한다.

특히 다음 변경은 PHASE 0 결과 없이 먼저 수행하지 않는다.

- 폴더 대규모 이동
- main.py 분해
- Router 분해
- Repository 전체 교체
- DB Migration
- Redis 도입
- Queue Framework 도입
- 인증 구조 교체
- Public Domain 연결
- Docker Network 변경
- Production DB 전환
- Production MinIO 전환

---

# 8. 최종 완료 기준

AI 강의 활용 Studio v1.24.x가 다음 조건을 충족하면
구조 안정화 완료로 판단한다.

```text
기존 기능 유지
+
Service Boundary
+
Provider Gateway
+
Hybrid RAG
+
Job/Worker
+
PostgreSQL/pgvector/MinIO 안전 분리
+
Quality Gate
+
Human Approval
+
Publication Gate
+
HTTPS Publisher
+
Backup/Restore
+
Regression Test
+
Security Test
+
Responsive/Accessibility Test
```

최종 목표는 기능이 가장 많은 프로그램이 아니라,

**장애가 발생해도 원인을 찾을 수 있고,
데이터를 잃지 않으며,
AI Provider가 바뀌어도 유지되고,
초보 사용자도 쉽게 사용할 수 있고,
검증되지 않은 교육자료가 자동 출판되지 않는 프로그램**

으로 완성하는 것이다.

---

# END
