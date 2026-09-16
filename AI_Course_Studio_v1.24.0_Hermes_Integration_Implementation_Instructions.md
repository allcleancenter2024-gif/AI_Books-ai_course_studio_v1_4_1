# AI 강의 활용 Studio v1.24.0
# Hermes Agent 안전 연동 및 단계적 도입 작업 지시서

- 문서 버전: 1.0
- 기준일: 2026-09-13
- 적용 대상: AI 강의 활용 Studio v1.24.0
- 연동 대상: Nous Research Hermes Agent
- 목적: 기존 Studio의 구조·데이터·Provider·RAG·Publisher·Quality Gate를 보존하면서 Hermes를 선택형 Agent Orchestration 계층으로 추가한다.
- 최우선 전략: **기존 구조 보존 → 읽기 전용 감사 → Adapter 경계 → 선택형 활성화 → 실패 격리 → 단계적 권한 확대 → 테스트 → 승인**
- 핵심 원칙: **Hermes는 Studio를 대체하지 않는다. Studio가 Hermes를 필요할 때 호출한다.**
- 기본 결론: **조건부 도입 권장 / 전체 재설계 금지 / 점진적 확장 권장**

---

# 0. 최종 구조 판정

## 0.1 최종 권고

Hermes는 다음 역할로만 도입한다.

```text
Hermes = Agent Orchestration Service
```

Hermes를 다음 역할로 사용하지 않는다.

```text
Hermes ≠ Studio Core
Hermes ≠ Database Owner
Hermes ≠ RAG Owner
Hermes ≠ Publisher
Hermes ≠ AI Provider Gateway Replacement
Hermes ≠ Job/Worker Replacement
Hermes ≠ Security Authority
```

최종 구조:

```text
                         User
                          │
                  Web UI / Admin UI
                          │
                    Web/API Gateway
                          │
          ┌───────────────┴────────────────┐
          │                                │
   Core Application                 Agent Gateway
          │                                │
  ┌───────┼────────┐               Hermes Adapter
  │       │        │                       │
Course  RAG   Generation                Hermes
  │       │        │                 ┌─────┼─────┐
  │       │        │              Skills Memory Agents
  │       │        │                       │
  │       │        └──── Studio Tool API ──┘
  │       │
  │    AI Provider Gateway
  │      ├─ LM Studio
  │      ├─ Ollama
  │      └─ Cloud
  │
  └──────────── Quality Gate
                    │
              Human Approval
                    │
             Publication Gate
                    │
            Publication Snapshot
                    │
                 Publisher
```

### 최종 판정

```text
STRUCTURAL COMPATIBILITY:        PASS
MAINTAINABILITY:                 PASS if Adapter boundary retained
UPDATE ISOLATION:                PASS if version pinned
PROVIDER CONFLICT RISK:          MEDIUM → LOW with Gateway isolation
RAG CONFLICT RISK:               MEDIUM → LOW with Tool API only
PUBLISHER CONFLICT RISK:         HIGH if direct access / LOW if Gate preserved
DB CONFLICT RISK:                HIGH if shared / LOW if isolated
SCHEDULER CONFLICT RISK:         MEDIUM
SECURITY RISK:                   MEDIUM ~ HIGH
RECOMMENDED METHOD:              OPTIONAL / ADDITIVE / ADAPTER-BASED
BIG-BANG INTEGRATION:            PROHIBITED
```

---

# 1. 기존 Studio의 절대 방향성

이번 Hermes 연동 작업은 기존 Master Plan을 절대로 대체하지 않는다.

기존 Studio의 방향은 다음을 최우선으로 유지한다.

1. 기존 기능과 사용자 데이터 보존
2. PHASE 0 Read-Only Audit 우선
3. Application → Service → Repository/Provider 경계 유지
4. 운영 DB와 테스트 DB 분리
5. 운영 MinIO와 테스트 Prefix 분리
6. Database Schema 변경은 Migration으로만 수행
7. UI가 DB / MinIO / Ollama / LM Studio에 직접 접근하지 않음
8. AI Provider 장애를 전체 Studio 장애로 확산시키지 않음
9. 대용량 작업은 Job/Worker 사용
10. AI 결과는 Quality Gate를 반드시 통과
11. Human Approval 유지
12. Publication Gate 유지
13. Publisher는 Publication API / Snapshot 경유
14. 내부 서비스 직접 외부 공개 금지
15. 각 Phase 실패 시 다음 단계 진행 금지
16. 모든 변경은 롤백 가능해야 함
17. CRITICAL 위험 발견 시 구현보다 보고 우선
18. 기능 추가보다 안정성과 유지보수성을 우선

Hermes 관련 요구사항이 위 원칙과 충돌할 경우:

```text
기존 Studio Master Plan이 항상 우선한다.
```

---

# 2. 이번 작업의 절대 금지 사항

다음 작업은 승인 없이 절대 수행하지 않는다.

```text
PROHIBITED
```

## 2.1 데이터

- Hermes가 Studio SQLite 파일 직접 열기
- Hermes가 PostgreSQL 직접 접속
- Hermes가 pgvector 직접 쿼리
- Hermes가 MinIO 직접 읽기/쓰기
- Hermes `state.db`와 Studio DB 통합
- Studio 데이터를 Hermes Memory의 authoritative store로 사용
- Hermes Memory를 Course/Week/Lesson의 원본 저장소로 사용
- 테스트 DB와 운영 DB 혼합
- DB Schema를 Hermes 연동만을 이유로 즉시 변경

## 2.2 AI Provider

- Hermes가 Studio Provider Gateway를 우회하여 운영 Provider를 직접 제어
- 기존 LM Studio/Ollama Adapter 삭제
- 기존 Provider Gateway를 Hermes로 교체
- UI → Hermes → Provider를 기본 생성 경로로 강제
- Provider API Key를 Hermes와 Studio에 무분별하게 중복 저장

## 2.3 RAG

- 기존 Hybrid RAG 제거
- Hermes Memory를 Studio RAG 대체재로 사용
- Hermes가 pgvector index를 직접 갱신
- Studio Embedding pipeline을 Hermes 내부 구현으로 교체

## 2.4 Publisher

- Hermes → Publisher 직접 호출
- Hermes 자동 출판
- Hermes가 Human Approval 우회
- Hermes가 Publication Gate 우회
- Hermes가 Publication Snapshot 없이 Publisher 데이터 작성
- Hermes가 Published 데이터를 직접 수정

## 2.5 운영

- Hermes 설치를 위해 기존 Port를 임의 변경
- 기존 Docker/Network를 전면 재구성
- 기존 `.env`를 통째로 덮어쓰기
- 기존 사용자 파일 overwrite
- `git reset --hard`
- 무한 Retry
- 무제한 Terminal 권한
- 운영 환경에서 `--yolo` 등 승인 우회 모드 기본 사용
- Hermes 장애 때문에 Studio startup 실패

---

# 3. 역할과 데이터 소유권

## 3.1 Studio가 계속 소유해야 하는 것

```text
Studio Authoritative Domain
```

- Course
- Week
- Lesson
- Document
- Upload
- Parser
- Chunk
- Embedding
- RAG index
- Evidence
- Generation result
- Quality result
- Approval status
- Publication state
- Publication Snapshot
- Export
- Learner Profile
- Job
- Audit log
- Provider policy
- Security policy

## 3.2 Hermes가 소유할 수 있는 것

```text
Hermes Agent Domain
```

- Agent session
- Agent working memory
- Skill
- Subagent orchestration
- Bot role
- Agent planning context
- Tool invocation context
- Agent execution metadata
- Agent-specific Cron state
- Agent-specific temporary artifacts

## 3.3 공유 시 원칙

```text
Studio → API / Tool Contract → Hermes
Hermes → API / Command Contract → Studio
```

DB 공유 금지.

---

# 4. 새로 추가할 최소 구조

실제 파일명과 디렉터리는 PHASE H0에서 현재 코드 구조를 확인한 후 결정한다.

개념적 구조:

```text
application/
  agent/
    agent_service
    agent_policy
    agent_request
    agent_response

providers/
  agents/
    hermes_adapter
    hermes_health
    hermes_client
    hermes_capabilities

api/
  agent_router

config/
  hermes_settings

tests/
  agent/
  hermes/

docs/
  HERMES_INTEGRATION.md
  HERMES_SECURITY.md
  HERMES_ROLLBACK.md
```

하나의 `main.py`, 거대한 Router, 기존 Provider Adapter 안에 Hermes 코드를 몰아넣지 않는다.

---

# 5. Hermes Adapter 계약

Studio 내부 코드가 Hermes SDK/API를 직접 여러 곳에서 호출하지 않는다.

반드시 하나의 경계를 둔다.

```text
UI
 ↓
API
 ↓
Application Agent Service
 ↓
Hermes Adapter Interface
 ↓
Hermes Client
 ↓
Hermes Agent
```

개념적 Interface:

```text
AgentAdapter

health()
capabilities()
run_task()
cancel_task()
get_task_status()
list_available_skills()
```

향후 Hermes가 다른 Agent Framework로 변경되더라도:

```text
AgentAdapter
 ├─ HermesAdapter
 └─ FutureAgentAdapter
```

형태로 교체 가능해야 한다.

---

# 6. Hermes를 Provider로 오해하지 말 것

Hermes는 LLM Provider가 아니다.

따라서 다음처럼 만들지 않는다.

```text
AI Provider Gateway
 ├─ Ollama
 ├─ LM Studio
 ├─ OpenAI
 └─ Hermes     ← 권장하지 않음
```

권장:

```text
AI Provider Gateway          Agent Gateway
 ├─ Ollama                   └─ Hermes Adapter
 ├─ LM Studio
 └─ Cloud
```

Hermes가 LLM을 필요로 할 경우 초기 도입 단계에서는 별도 Provider 정책을 최소화하고, Hermes Provider 설정과 Studio Provider 설정의 중복 범위를 문서화한다.

장기적으로 Provider 공유가 필요하면 별도 ADR(Architecture Decision Record) 승인 후 진행한다.

---

# 7. Hermes와 RAG 연동 원칙

## 7.1 권장

```text
Hermes
 ↓
Studio RAG Tool/API
 ↓
Hybrid RAG
 ↓
PostgreSQL FTS + pgvector
 ↓
Evidence
```

## 7.2 금지

```text
Hermes → pgvector direct
Hermes → PostgreSQL direct
Hermes → MinIO direct
Hermes Memory → Course RAG replacement
```

## 7.3 Tool Contract 예

Hermes에게 노출 가능한 기능:

```text
search_course_knowledge
search_uploaded_documents
get_evidence_packet
get_course_outline
get_week_content
```

모든 반환은 필요한 최소 정보만 제공한다.

---

# 8. Web Search / SearXNG 원칙

기존 Studio Web Search Router가 존재하면 Hermes는 이를 우선 Tool로 사용한다.

```text
Hermes
 ↓
Studio Search Tool
 ↓
Web Search Router
 ↓
SearXNG / Approved Search Provider
```

장점:

- 출처 정책 통일
- 날짜 검증 정책 통일
- 로그 일원화
- 비용/Rate Limit 관리
- 캐시 공유
- 검색 Provider 교체 용이

Hermes 전용 Web Search를 사용하는 경우 별도 기능 Flag로 격리한다.

---

# 9. Publisher 연동 원칙

Hermes는 출판자가 아니다.

허용:

```text
Hermes
 ↓
Draft
 ↓
Studio Application
 ↓
Quality Gate
 ↓
Preview
 ↓
Human Approval
 ↓
Publication Gate
 ↓
Publication Snapshot
 ↓
Publisher
```

금지:

```text
Hermes → Publisher
Hermes → Published DB
Hermes → Production Page
Hermes → Publication Gate bypass
```

Hermes가 생성한 모든 결과에는 최소 다음 metadata를 남긴다.

```text
agent_source
agent_version
task_id
generated_at
review_required=true
quality_gate_status
human_approval_status
```

기존 Data Model 변경이 필요할 경우 PHASE H0에서 보고하고 승인 전 Migration하지 않는다.

---

# 10. Job / Worker / Cron 소유권

중복 Scheduler를 만들지 않는다.

## 초기 권장

```text
Studio Job Service = Schedule Owner
Hermes = Execution Worker / Orchestrator
```

흐름:

```text
Studio Scheduler
 ↓
Job
 ↓
Hermes task request
 ↓
Hermes execution
 ↓
Result
 ↓
Studio Job status
```

초기 단계에서는 Hermes Cron을 비활성 또는 제한한다.

## Hermes Cron을 허용할 수 있는 경우

다음 조건을 모두 만족한 후 별도 승인:

- 중복 실행 방지
- idempotency 확보
- task ownership 명확
- timezone 명확
- retry ownership 명확
- cancel ownership 명확
- job history 연계
- duplicate execution test PASS

예:

```text
weekly_ai_research
```

같은 작업을 Studio Scheduler와 Hermes Cron 양쪽에 동시에 등록하지 않는다.

---

# 11. Health / Failure Isolation

Hermes 상태:

```text
healthy
degraded
unavailable
disabled
```

Startup 시:

- 빠른 health probe
- Hermes 실패는 Studio startup blocker가 아님
- Hermes가 꺼져 있어도 Course/RAG/Generation/Export/Publisher 기본 기능 정상
- health timeout과 task timeout 분리
- bounded retry
- exponential backoff
- cancellation 시 무의미한 retry 금지

Service Health Dashboard에 장기적으로 다음을 추가 가능:

```text
Hermes Agent       Healthy / Degraded / Unavailable / Disabled
Hermes Version
Last Health Check
Active Agent Jobs
```

일반 사용자 UI에 기술 세부정보를 과도하게 노출하지 않는다.

---

# 12. Configuration

PHASE H0에서 실제 설정 구조를 확인한 후 아래와 유사한 형태로 최소 추가한다.

```env
HERMES_ENABLED=false
HERMES_BASE_URL=
HERMES_HEALTH_TIMEOUT_SECONDS=
HERMES_TASK_TIMEOUT_SECONDS=
HERMES_ALLOW_WRITE=false
HERMES_ALLOW_BROWSER=false
HERMES_ALLOW_TERMINAL=false
HERMES_ALLOW_CRON=false
HERMES_ALLOW_MCP=false
HERMES_ALLOW_BOT_MODE=false
HERMES_ALLOW_WEBHOOK=false
HERMES_PROFILE=studio
```

실제 변수명은 기존 Configuration naming convention을 따른다.

원칙:

- 기본값은 안전 방향
- Hermes 기본 비활성
- Secret은 `.env.example`에 실제 값 기록 금지
- 운영/개발 설정 분리
- Feature Flag로 단계적 활성화
- 설정 누락 시 Studio 전체 startup 실패 금지

---

# 13. 권한 모델

## PHASE H1 기본 권한

```text
READ ONLY
```

허용:

- Course metadata read
- Week/Lesson read
- RAG query
- Search
- Public documentation research
- Draft 생성
- Validation request
- Job status read

금지:

- DB write
- File delete
- Publication
- Production config write
- Secret read
- Migration
- Arbitrary shell
- MinIO write
- Provider config change

## PHASE H2 이후

승인된 API를 통해서만 제한적 write 허용:

```text
create_draft
update_draft
attach_agent_result
request_quality_check
```

여전히 금지:

```text
approve_publication
publish
delete_course
migrate_database
change_secret
```

---

# 14. Terminal / Browser / MCP 정책

## Terminal

초기:

```text
HERMES_ALLOW_TERMINAL=false
```

필요 시 Allowlist 기반으로 별도 승인한다.

운영 서버에서는 임의 shell을 기본 허용하지 않는다.

## Browser

초기 목적:

- 공식 문서 조사
- 공개 정보 확인
- 개발 문서 검색

외부 게시, 결제, 계정 변경, 삭제는 자동 실행 금지.

## MCP

초기에는 비활성 또는 승인된 MCP Server만 허용.

각 MCP Server에 대해 기록:

```text
name
purpose
owner
permission
network_access
data_access
secret_access
risk
approval
```

---

# 15. Memory 정책

Hermes Memory와 Studio 데이터는 역할을 분리한다.

## Hermes Memory에 허용

- Agent 작업 방식
- 반복 Workflow
- 비민감 프로젝트 컨텍스트
- Agent Skill 관련 정보
- 실패/성공 패턴

## Hermes Memory에 금지 또는 제한

- 비밀번호
- API Key
- JWT Secret
- 운영 DB Credential
- MinIO Secret
- 민감한 사용자 문서 전문
- 민감 개인정보
- Publisher 승인 토큰

Memory purge/export 정책을 문서화한다.

Hermes `state.db`는 Studio DB와 분리하여 백업한다.

---

# 16. Skill 도입 원칙

Hermes 도입의 1차 핵심 가치는 Skill이다.

권장 Skill 후보:

```text
official_ai_update_research
course_outline_builder
beginner_explanation_rewriter
exercise_generator
fact_source_checker
image_prompt_builder
weekly_change_detector
release_note_analyzer
course_quality_precheck
```

각 Skill은 다음 형식으로 관리한다.

```text
SKILL ID:
VERSION:
PURPOSE:
INPUT:
OUTPUT:
ALLOWED TOOLS:
FORBIDDEN ACTIONS:
QUALITY REQUIREMENTS:
SOURCE REQUIREMENTS:
HUMAN REVIEW:
OWNER:
```

Skill 변경은 코드 변경과 별도로 version 관리한다.

---

# 17. Subagent / Bot Mode 정책

처음부터 Bot Mode 전체를 도입하지 않는다.

순서:

```text
1. Single Hermes Agent
2. Read-only Skill
3. Limited Subagent
4. Role-separated Subagents
5. Bot Mode Pilot
6. Bot collaboration
```

권장 역할:

```text
Research Agent
Curriculum Agent
Fact Check Agent
Visual Prompt Agent
QA Agent
```

Publisher Agent는 직접 Publisher를 제어하지 않는다.

대신:

```text
Publication Preparation Agent
```

로 명명하고 Publication Gate 이전까지만 담당한다.

---

# 18. Security

반드시 확인:

- Secret isolation
- Authentication
- Authorization
- CSRF
- CORS
- Rate Limit
- Request size
- Timeout
- Injection
- Prompt injection
- Tool injection
- Path traversal
- File access scope
- Network egress
- Webhook signature
- MCP permission
- Skill supply-chain risk
- Agent log secret leakage
- Private content logging
- Browser credential exposure

추가 원칙:

```text
Default Deny
Least Privilege
Explicit Allow
Human Approval for High Impact Actions
```

Hermes가 실행한 모든 변경 가능 작업은 Audit 가능한 `task_id`를 가져야 한다.

---

# 19. Logging / Observability

로그는 Studio와 Hermes를 연결할 수 있어야 한다.

권장 ID:

```text
request_id
job_id
agent_task_id
course_id
user_id (safe internal identifier only)
```

로그 금지:

```text
API Key
Password
JWT
Raw Secret
Private document full text
Prompt containing secrets
Sensitive personal data
```

최소 기록:

```text
Agent requested
Agent started
Tool invoked
Tool denied
Agent completed
Agent failed
Agent cancelled
Quality Gate requested
Human review requested
```

---

# 20. Version / Update 정책

Hermes는 빠르게 업데이트될 수 있으므로 `latest` 추종 금지.

운영에서는 Version Pinning 사용.

예:

```text
HERMES_VERSION=<approved-version>
```

업데이트 절차:

```text
1. Release Note 검토
2. Security 변경 확인
3. state.db / Memory migration 확인
4. Tool/API breaking change 확인
5. Adapter contract test
6. Sandbox test
7. Regression test
8. Backup
9. Canary
10. 승인
11. Production
```

Hermes 업데이트가 Studio 업데이트를 강제하지 않아야 한다.

Studio 업데이트가 Hermes 업데이트를 강제하지 않아야 한다.

목표:

```text
Loose Coupling
Stable Contract
Replaceable Adapter
```

---

# 21. PHASE H0 — Read-Only Integration Audit

## 목적

현재 프로그램을 수정하지 않고 Hermes 연동 가능 지점을 실제 코드에서 확인한다.

## 작업 모드

```text
READ ONLY
NO CODE CHANGE
NO DB CHANGE
NO ENV CHANGE
NO NETWORK CHANGE
NO HERMES INSTALL
```

## 반드시 확인

1. Project Root
2. AGENTS.md / project rules
3. Backend entrypoint
4. Frontend entrypoint
5. API Router
6. Service layer
7. Repository layer
8. Provider Gateway
9. LM Studio Adapter
10. Ollama Adapter
11. Cloud Provider Adapter
12. Job / Worker
13. Scheduler
14. RAG pipeline
15. Web Search Router / SearXNG integration
16. Quality Gate
17. Human Approval
18. Publication Gate
19. Publication API
20. Publication Snapshot
21. Publisher connection
22. Authentication
23. Authorization
24. Configuration
25. Secret handling
26. Logging
27. Retry / Timeout / Cancel
28. Test structure
29. Docker / Port
30. Backup / Rollback

## 탐지해야 하는 위반

```text
UI → Provider direct
UI → DB direct
UI → Storage direct
Router → Provider SDK direct
Router → raw SQL
Publisher → DB direct
Publisher → Provider direct
RAG ↔ Generation hard coupling
Multiple Scheduler ownership
Hardcoded Secret
Hardcoded Port
Test/Production DB mixing
```

## 산출물

```text
reports/hermes_phase_h0/
  HERMES_INTEGRATION_CURRENT_ARCHITECTURE.md
  HERMES_BOUNDARY_MAP.md
  HERMES_API_CANDIDATES.md
  HERMES_SECURITY_RISK.md
  HERMES_DATA_OWNERSHIP.md
  HERMES_SCHEDULER_CONFLICT.md
  HERMES_PROVIDER_CONFLICT.md
  HERMES_RAG_CONFLICT.md
  HERMES_PUBLISHER_CONFLICT.md
  HERMES_PHASE_H0_RESULT.md
```

## PASS

- 기존 구조 지도 작성 완료
- Hermes Adapter 위치 후보 확정
- DB direct access 필요 없음
- Publisher direct access 필요 없음
- Provider Gateway 우회 필요 없음
- 기존 RAG 재설계 필요 없음
- rollback 가능
- CRITICAL 없음

## BLOCKED

다음 중 하나라도 필요하면 중단:

- Hermes 도입을 위해 DB 직접 접근 필요
- Publisher Gate 우회 필요
- 기존 Provider Gateway 제거 필요
- 기존 RAG 제거 필요
- 운영 DB 변경이 선행 필수
- 운영 데이터 migration이 즉시 필요
- 기존 핵심 테스트 실패
- rollback 불가능

---

# 22. PHASE H1 — Adapter Skeleton / Disabled by Default

선행:

```text
PHASE H0 = PASS
```

목적:

Hermes 실행 없이 Adapter 경계만 만든다.

구현:

- Agent Service interface
- Hermes Adapter interface
- Disabled implementation
- Configuration flag
- Health state model
- Unit Test

기본:

```text
HERMES_ENABLED=false
```

PASS:

- Hermes 없어도 Studio 100% 기존 기능 정상
- 기존 DB 변경 없음
- Publisher 변경 없음
- Provider 변경 없음
- RAG 변경 없음
- Test baseline 유지

---

# 23. PHASE H2 — Local Health / Capability Probe

목적:

Hermes가 켜져 있을 때만 연결 상태를 감지한다.

구현:

```text
health()
capabilities()
version()
```

상태:

```text
healthy
degraded
unavailable
disabled
```

원칙:

- Startup blocker 금지
- 짧은 health timeout
- secret-safe logging
- bounded retry
- Hermes OFF 상태 테스트

PASS:

Hermes 종료 상태에서도 Studio 정상.

---

# 24. PHASE H3 — Read-Only Tool Pilot

허용 Tool:

```text
get_course_metadata
get_course_outline
get_week_content
search_course_rag
search_web
get_job_status
```

금지:

```text
write
delete
publish
migrate
config change
secret access
```

Pilot use case:

```text
“현재 강의자료를 읽고 최신 공식자료와 비교해 변경 제안서 작성”
```

결과는 Draft만 생성한다.

---

# 25. PHASE H4 — Draft Generation

Hermes가 Studio API를 통해 Draft를 만들 수 있게 한다.

허용:

```text
create_draft
update_agent_draft
attach_research_result
request_quality_check
```

모든 Agent 결과:

```text
review_required=true
```

자동 Human Approval 금지.

자동 Publication 금지.

---

# 26. PHASE H5 — Skill / Subagent

선행:

- H3/H4 회귀 테스트 PASS
- Agent task audit PASS
- Timeout/Cancel PASS

도입:

- Research Skill
- Fact-check Skill
- Curriculum Skill
- Visual Prompt Skill

Subagent는 2~3개 역할부터 시작.

Bot Mode는 아직 기본 비활성.

---

# 27. PHASE H6 — Job Integration

Studio Job Service와 Hermes task를 연결한다.

```text
Studio Job
  ↓
Hermes task
  ↓
status callback / polling
  ↓
Studio Job status
```

반드시:

- retry owner 하나
- cancel owner 하나
- timeout owner 명확
- duplicate execution 방지
- idempotency key
- task correlation ID

Hermes Cron 기본 비활성.

---

# 28. PHASE H7 — Optional Bot Mode / MCP

충분한 안정성 확인 후에만 진행.

Bot Mode:

```text
HERMES_ALLOW_BOT_MODE=true
```

MCP:

승인 목록 기반.

각 MCP Server 별 Security Review 필수.

이 단계도 Publisher 직접 접근은 금지.

---

# 29. PHASE H8 — Optional Scheduled Research

적합한 사용 사례:

```text
주간 AI 공식자료 업데이트
신규 릴리스 감지
교재의 오래된 버전 정보 탐지
출처 변경 감지
```

권장:

Studio Scheduler가 owner.

Hermes Cron을 사용할 경우 Studio Scheduler와 동일 작업 중복 등록 금지.

---

# 30. 테스트 매트릭스

## Functional

- Hermes disabled
- Hermes enabled
- Hermes unavailable
- Read-only task
- RAG tool
- Search tool
- Draft creation
- Quality check request
- Cancel
- Timeout

## Regression

반드시 기존 기능:

- 새 강의
- 저장
- 불러오기
- 수정
- Upload
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

## Failure

- Hermes process stop
- Hermes timeout
- Hermes malformed response
- Hermes DB/state failure
- Hermes tool error
- Search error
- RAG error
- LM Studio off
- Ollama off
- Network disconnect
- Job worker stop

핵심:

```text
Hermes 장애가 Studio 전체 장애가 되면 FAIL
```

---

# 31. 성능

Agent가 긴 작업을 수행할 경우 동기 HTTP 요청에 장시간 묶지 않는다.

권장:

```text
Request
 ↓
Job ID
 ↓
Background execution
 ↓
Progress
 ↓
Result
```

긴 Agent 작업은 기존 Job/Worker 원칙에 맞춘다.

---

# 32. 롤백

모든 Phase는 독립적으로 롤백 가능해야 한다.

최우선 롤백:

```text
HERMES_ENABLED=false
```

이 한 설정으로 기존 Studio 기능이 정상으로 돌아와야 한다.

롤백 시:

- DB rollback 의존 금지
- 기존 Course data 영향 0
- Publication state 영향 0
- Provider settings 영향 0
- RAG index 영향 0

---

# 33. 업데이트 유지보수 기준

향후 Studio 업데이트 시:

1. AgentAdapter contract test
2. API compatibility
3. Auth policy
4. Job integration
5. RAG Tool contract
6. Publisher Gate
7. Regression test

향후 Hermes 업데이트 시:

1. Hermes version diff
2. API/CLI change
3. state.db change
4. Memory change
5. Permission change
6. Tool change
7. MCP change
8. Cron change
9. Security advisory
10. Adapter test

핵심 목표:

```text
Studio 내부 코드는 Hermes 버전 세부사항을 몰라도 된다.
Hermes 내부 코드는 Studio DB 구조를 몰라도 된다.
```

---

# 34. UI/UX

일반 사용자 화면에 Hermes 기술 용어를 과도하게 노출하지 않는다.

권장 사용자 표현:

```text
AI 작업 도우미
AI 자동화
AI 조사
AI 작업 상태
```

관리자 화면:

```text
Hermes
Version
Health
Capabilities
Agent Jobs
Skills
MCP
Bot Mode
```

Hermes Disabled 상태에서도 UI 깨짐 없음.

---

# 35. 운영 Dashboard

관리자 Service Health에 장기적으로 추가:

| Service | Status |
|---|---|
| Studio | |
| PostgreSQL | |
| pgvector | |
| MinIO | |
| Queue | |
| Ollama | |
| LM Studio | |
| Web Search | |
| Hermes Agent | |
| Publisher | |

Agent Job:

| Field | Description |
|---|---|
| Task | 작업명 |
| Agent | 역할 |
| Status | 상태 |
| Progress | 진행률 |
| Current step | 현재 단계 |
| Started | 시작 |
| Updated | 최근 갱신 |
| Timeout | 제한 |
| Cancel | 취소 |
| Error | 오류 |
| Review | 검토 상태 |

---

# 36. 위험도

## HIGH

### H-01 Hermes → Publisher direct
대응: Publication API + Gate만 허용.

### H-02 Hermes → DB direct
대응: Studio API/Tool만 허용.

### H-03 unrestricted Terminal
대응: Disabled → Allowlist.

### H-04 duplicated Scheduler
대응: Single Schedule Owner.

### H-05 Secret leakage
대응: Secret isolation + sanitized log.

## MEDIUM

### M-01 Provider 중복
대응: Provider Gateway와 Agent Gateway 분리.

### M-02 Memory 데이터 중복
대응: Data Ownership 명시.

### M-03 Hermes 빠른 업데이트
대응: Version Pin + Canary.

### M-04 Long task timeout
대응: Job/Worker.

### M-05 Bot Mode 복잡도
대응: 마지막 단계에서 선택 도입.

---

# 37. 최종 PASS 기준

Hermes 통합은 다음을 모두 만족해야 PASS.

```text
[ ] 기존 Studio 핵심 기능 회귀 0
[ ] Hermes disabled에서 기존 기능 100% 동작
[ ] Hermes failure가 Studio startup 차단 안 함
[ ] DB direct access 0
[ ] MinIO direct access 0
[ ] Publisher direct access 0
[ ] Provider Gateway 우회 0
[ ] Quality Gate 우회 0
[ ] Human Approval 우회 0
[ ] Publication Gate 우회 0
[ ] RAG ownership 유지
[ ] bounded retry
[ ] timeout 명시
[ ] cancel 동작
[ ] secret leakage 0
[ ] rollback 가능
[ ] version pinning
[ ] documentation 완료
```

하나라도 핵심 항목이 FAIL이면 다음 Phase 진행 금지.

---

# 38. 최종 구현 우선순위

## 반드시 먼저

```text
H0 Read-Only Audit
H1 Adapter Skeleton
H2 Health Probe
H3 Read-only Tool Pilot
```

## 검증 후

```text
H4 Draft Generation
H5 Skills/Subagents
H6 Job Integration
```

## 장기 선택 기능

```text
H7 Bot Mode / MCP
H8 Scheduled Research
A2A
Webhook
Voice
```

처음부터 전체 Hermes 기능을 켜지 않는다.

---

# 39. 개발 에이전트/Codex용 실행 지시문

```text
AI 강의 활용 Studio v1.24.0에 Hermes Agent 연동을 준비하라.

절대 목표는 Hermes 기능 추가 자체가 아니다.
현재 Studio의 구조 안정성, 데이터 무결성, Provider 격리, Hybrid RAG,
Quality Gate, Human Approval, Publication Gate, Publisher 경계를 그대로
보존하면서 Hermes를 선택형 Agent Orchestration 계층으로 추가하는 것이다.

Hermes는 Studio Core, DB, RAG, Provider Gateway, Job/Worker, Publisher를
대체하지 않는다.

먼저 PHASE H0 Read-Only Integration Audit만 수행하라.

READ ONLY
NO CODE CHANGE
NO DB CHANGE
NO ENV CHANGE
NO NETWORK CHANGE
NO HERMES INSTALL

반드시 실제 코드에서 다음을 확인하라.

- Backend/Frontend entrypoint
- API Router
- Service/Repository
- Provider Gateway
- LM Studio/Ollama Adapter
- Job/Worker/Scheduler
- RAG pipeline
- Web Search/SearXNG
- Quality Gate
- Human Approval
- Publication Gate
- Publication API/Snapshot
- Publisher
- Auth/AuthZ
- Configuration/Secret
- Retry/Timeout/Cancel
- Logging
- Test/Backup/Rollback

Hermes는 다음 경계에서만 연동 가능한지 판단하라.

UI
→ API
→ Application Agent Service
→ AgentAdapter
→ HermesAdapter
→ Hermes

Hermes가 Studio DB, PostgreSQL, pgvector, MinIO, Publisher 또는 AI Provider에
직접 접근해야만 구현할 수 있다면 BLOCKED로 판정하라.

Studio RAG는 유지하고 Hermes는 Studio RAG Tool/API의 사용자로만 동작해야 한다.

Studio Provider Gateway는 유지한다.
Hermes를 기존 LM Studio/Ollama Provider 구조의 대체재로 만들지 않는다.

Publisher 흐름은 반드시 다음을 유지한다.

Hermes Draft
→ Studio
→ Quality Gate
→ Preview
→ Human Approval
→ Publication Gate
→ Publication Snapshot
→ Publisher

Hermes 장애는 Studio 전체 장애로 확산되어서는 안 된다.
최종 구조는 HERMES_ENABLED=false 하나로 Hermes를 끄고 기존 Studio 기능으로
즉시 돌아갈 수 있어야 한다.

PHASE H0 결과로 다음 파일을 작성하라.

reports/hermes_phase_h0/
- HERMES_INTEGRATION_CURRENT_ARCHITECTURE.md
- HERMES_BOUNDARY_MAP.md
- HERMES_API_CANDIDATES.md
- HERMES_SECURITY_RISK.md
- HERMES_DATA_OWNERSHIP.md
- HERMES_SCHEDULER_CONFLICT.md
- HERMES_PROVIDER_CONFLICT.md
- HERMES_RAG_CONFLICT.md
- HERMES_PUBLISHER_CONFLICT.md
- HERMES_PHASE_H0_RESULT.md

최종 판정:

GO
CONDITIONAL GO
BLOCKED

PHASE H0가 GO 또는 조건 해소된 CONDITIONAL GO가 아니면
어떠한 Hermes 코드도 추가하지 마라.
```

---

# 40. 최종 결론

이 프로젝트에서 Hermes의 가장 좋은 위치는:

```text
“Studio를 대체하는 Agent Framework”
```

가 아니라

```text
“Studio가 필요할 때 호출하는 교체 가능한 Agent Orchestration Service”
```

이다.

가장 중요한 설계 원칙:

```text
Loose Coupling
Stable Adapter
Single Data Owner
Single Scheduler Owner
No Direct DB
No Direct Publisher
No Gate Bypass
Failure Isolation
Feature Flag
Version Pinning
Rollback First
```

이 원칙을 유지하면:

- 현재 Studio 구조와 충돌을 최소화할 수 있고
- Hermes 업데이트 영향을 Adapter 내부로 제한할 수 있으며
- Studio 자체 업데이트도 독립적으로 수행할 수 있고
- Hermes를 나중에 제거하거나 다른 Agent로 바꾸기도 쉬워지고
- 운영 장애가 전체 프로그램으로 확산되는 것을 방지할 수 있다.

따라서 최종 권고는:

**Hermes 도입은 진행하되, PHASE H0 Read-Only Audit부터 시작하고,
처음에는 Read-Only + Adapter + Disabled-by-default 구조로만 도입한다.**

---

## 기준 문서

- AI_Course_Studio_v1.24.0_Final_Implementation_Master_Instructions.md
- AI_Course_Studio_v1.24.0_Local_AI_Provider_Connection_Stability_Patch_Instructions.md
- AI_Course_Studio_v1.24.0_UI_Publisher_Preview_Week_Image_Bilingual_Prompt_Implementation_Instructions.md
- AI_Course_Studio_v1.24.0_Publisher_Optimization_Proposals_1-10_Implementation_Instructions.md
- Hermes_Agent_2026_최신_학습가이드.md