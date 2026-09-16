# AI 강의 활용 Studio v1.24.0
# Hermes Agent v0.21.2 최적화 연동 작업 지시서
## Stable Adapter · Minimal Surface · Safe Upgrade Edition

- 문서 버전: 2.0
- 기준일: 2026-09-13
- 대상 프로그램: AI 강의 활용 Studio v1.24.0
- Hermes 기준 버전: **v0.21.2 / 2026-09-11**
- 기본 전략: **최신 엔진을 사용하되, 운영 범위는 보수적으로 시작한다**
- 최우선 목표: **현재 Studio 구조를 보존하면서 Hermes를 쉽게 추가·교체·중지·업데이트할 수 있게 한다**
- 핵심 방식: **Adapter 분리 + 기본 비활성 + Read-only 우선 + Feature Flag + Version Pinning + Failure Isolation**
- 절대 원칙: **Hermes는 Studio를 대체하지 않는다. Studio가 Hermes를 선택적으로 호출한다.**

---

# 0. 최종 결정

## 0.1 이번 작업에서 채택할 구조

```text
                     AI 강의 활용 Studio
                              │
                    Web / API Gateway
                              │
          ┌───────────────────┴────────────────────┐
          │                                        │
    Core Application                         Agent Gateway
          │                                        │
 ┌────────┼─────────┐                      AgentAdapter
 │        │         │                           │
Course   RAG   Generation                 HermesAdapter
 │        │         │                           │
 │        │         │                      Hermes v0.21.2
 │        │         │                 ┌─────────┼─────────┐
 │        │         │               Skills    Memory   Subagents
 │        │         │                            │
 │        │         └──────────── Studio Tool API
 │        │
 │     AI Provider Gateway
 │       ├─ LM Studio
 │       ├─ Ollama
 │       └─ Cloud Provider
 │
 └──────────────── Quality Gate
                         │
                   Human Approval
                         │
                  Publication Gate
                         │
                Publication Snapshot
                         │
                     Publisher
```

## 0.2 Hermes의 역할

허용:
- Agent Orchestration
- Research
- Skill Execution
- Task Planning
- Limited Subagent Delegation
- Draft Generation
- Quality Pre-check
- Scheduled Research(후기 단계)

금지:
- Studio Core Replacement
- Database Owner
- RAG Owner
- Provider Gateway Replacement
- Publisher
- Security Authority
- Migration Engine
- Production Configuration Owner

---

# 1. 핵심 설계 철학

## 1.1 최신 버전 + 보수적 운영

Hermes v0.21.2를 기준 버전으로 사용한다.

초기 사용 범위:
- Health
- Skills
- Research
- Read-only Tools
- Limited Subagent

초기 비활성:
- Bot Mode
- MCP external servers
- Hermes Cron ownership
- A2A
- Voice
- unrestricted Browser control
- unrestricted Terminal
- direct write
- direct publish

목표는 v0.21.2의 최신 안정성 개선을 활용하면서 v0.17 시기 수준의 단순한 운영 복잡도로 시작하는 것이다.

---

# 2. 기존 Studio Master Plan 우선

다음 기존 원칙은 그대로 유지한다.

1. 기존 기능과 사용자 데이터 보존
2. PHASE 0 Read-Only Audit 우선
3. Application → Service → Repository/Provider 경계 유지
4. UI에서 DB/MinIO/Provider 직접 접근 금지
5. 운영/테스트 DB 분리
6. 운영/테스트 MinIO 분리
7. AI Provider 장애 격리
8. Job/Worker 경계 유지
9. Hybrid RAG 유지
10. Quality Gate 유지
11. Human Approval 유지
12. Publication Gate 유지
13. Publisher는 Publication Snapshot 경유
14. Public endpoint는 Web/API Gateway만 허용
15. 모든 변경 Rollback 가능
16. 한 Phase 실패 시 다음 단계 중단

충돌 시:
`Studio Master Plan > Hermes Integration Plan`

---

# 3. 절대 금지 사항

## 3.1 Database
금지:
- Hermes → SQLite direct
- Hermes → PostgreSQL direct
- Hermes → pgvector direct
- Hermes → MinIO direct
- Hermes state.db ↔ Studio DB merge

Hermes `state.db`는 Hermes 전용으로 분리한다.
Studio Course/Week/Lesson 데이터는 Studio DB가 authoritative source이다.

## 3.2 Provider
금지:
- UI → Hermes → LM Studio
- UI → Hermes → Ollama
- Hermes → Studio Provider config direct write
- Hermes가 Provider Gateway 대체

권장:
```text
Provider Gateway
 ├─ LM Studio
 ├─ Ollama
 └─ Cloud

Agent Gateway
 └─ Hermes
```

## 3.3 RAG
금지:
- Hermes Memory = Studio RAG
- Hermes → pgvector direct
- Hermes → embedding index direct update

권장:
```text
Hermes
 ↓
Studio RAG Tool
 ↓
Hybrid RAG
 ↓
Evidence
```

## 3.4 Publisher
절대 금지:
- Hermes → Publisher
- Hermes → Published Page
- Hermes → Publication DB
- Hermes → Human Approval bypass
- Hermes → Publication Gate bypass

허용되는 유일한 흐름:
```text
Hermes Draft
 ↓
Studio
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

---

# 4. 최적화된 구성 요소

최소 구성만 추가한다.

```text
AgentService
AgentAdapter
HermesAdapter
HermesClient
HermesHealth
HermesPolicy
HermesConfig
AgentTask
AgentResult
```

실제 이름은 기존 프로젝트 구조를 조사한 후 현재 naming convention에 맞춘다.

---

# 5. Stable AgentAdapter Contract

Hermes SDK/API 호출은 한 곳으로 집중한다.

권장 Interface:
```text
AgentAdapter

health()
version()
capabilities()

submit_task()
get_task()
cancel_task()

run_readonly_tool()
run_skill()

list_skills()
```

핵심:
```text
Studio knows AgentAdapter.
Studio does NOT know Hermes internals.
```

---

# 6. Configuration 최적화

Hermes는 기본 비활성이다.

```env
HERMES_ENABLED=false
HERMES_BASE_URL=
HERMES_VERSION=0.21.2

HERMES_HEALTH_TIMEOUT_SECONDS=3
HERMES_TASK_TIMEOUT_SECONDS=300

HERMES_ALLOW_READ=true
HERMES_ALLOW_WRITE=false
HERMES_ALLOW_SKILLS=true
HERMES_ALLOW_SUBAGENTS=false
HERMES_ALLOW_BROWSER=false
HERMES_ALLOW_TERMINAL=false
HERMES_ALLOW_MCP=false
HERMES_ALLOW_CRON=false
HERMES_ALLOW_BOT_MODE=false
HERMES_ALLOW_A2A=false
HERMES_ALLOW_WEBHOOK=false
HERMES_ALLOW_VOICE=false

HERMES_PROFILE=studio
```

실제 환경변수명은 기존 Configuration 규칙과 충돌 여부를 확인한 후 확정한다.

---

# 7. Version Pinning

운영에서 `latest`, `main`, `nightly` 사용 금지.

현재 승인 기준:
`v0.21.2`

업데이트 순서:
1. Release note 검토
2. Security 변경 확인
3. Breaking change 확인
4. state.db / Memory migration 확인
5. Adapter contract test
6. Sandbox
7. Regression
8. Canary
9. Human approval
10. Production

---

# 8. Health / Failure Isolation

상태:
- healthy
- degraded
- unavailable
- disabled

규칙:
1. Hermes가 꺼져 있어도 Studio startup 성공
2. Hermes timeout이 Studio 전체 timeout으로 확산되지 않음
3. Health timeout과 Task timeout 분리
4. 무한 Retry 금지
5. Retry owner는 한 곳
6. Cancellation 즉시 전파
7. Hermes 장애 시 Course/RAG/Generation/Publisher 유지

최우선 PASS:
`HERMES_ENABLED=false` 상태에서 기존 Studio 기능이 100% 정상.

---

# 9. Hermes Memory 정책

Hermes Memory 허용:
- Agent workflow preference
- Skill execution context
- Research history
- Agent task continuity
- Non-sensitive operational context

금지:
- API Key
- Password
- JWT
- Database credential
- MinIO secret
- Private user data
- Published authoritative content
- Course authoritative records

원칙:
`Studio DB = Business truth`
`Hermes Memory = Agent working context`

---

# 10. Studio Tool API

초기 허용 Tool:
- get_course_metadata
- get_course_outline
- get_week_content
- search_course_rag
- get_evidence_packet
- search_web
- get_job_status

초기 금지 Tool:
- delete_course
- publish_course
- modify_provider
- change_env
- migrate_database
- write_minio
- execute_shell

---

# 11. Search / SearXNG

권장:
```text
Hermes
 ↓
Studio Search Tool
 ↓
Web Search Router
 ↓
SearXNG / Approved Provider
```

목표:
- Search policy 한 곳
- Source policy 한 곳
- 날짜 검증 한 곳
- Cache 한 곳
- Rate limit 한 곳
- Audit 한 곳

---

# 12. Skill 최적화

초기 핵심 기능은 Bot Mode가 아니라 Skills이다.

권장 Skill:
- official_ai_update_research
- release_note_analyzer
- course_outline_builder
- beginner_explanation_rewriter
- fact_source_checker
- exercise_generator
- image_prompt_builder
- course_quality_precheck
- weekly_change_detector

각 Skill Metadata:
- id
- version
- purpose
- inputs
- outputs
- allowed_tools
- forbidden_actions
- source_policy
- quality_policy
- review_required
- owner

---

# 13. Subagent 최적화

초기에는 최대 2~3개 역할만 사용한다.

권장:
- Research Agent
- Fact Check Agent
- Curriculum Agent

후기:
- Visual Prompt Agent
- QA Agent

처음부터 Bot Mode 활성화 금지.

Subagent 규칙:
- maximum depth 제한
- concurrent agents 제한
- task timeout
- token/cost budget
- cancellation 지원
- parent task ID 필수

---

# 14. Bot Mode

초기:
`HERMES_ALLOW_BOT_MODE=false`

도입 조건:
- Single Agent 안정성 확인
- Skill 안정성 확인
- Subagent 안정성 확인
- Job 상태 추적 PASS
- 비용/리소스 측정 완료
- 중복 Tool 실행 방지 완료

---

# 15. Cron / Scheduler 최적화

초기 Schedule Owner:
`Studio Job/Scheduler`

권장:
```text
Studio Scheduler
 ↓
Agent Job
 ↓
Hermes Task
```

Hermes Cron은 비활성.

Hermes Cron 사용 조건:
- 동일 작업 Studio Scheduler에서 제거
- idempotency key
- timezone 명확
- retry owner 명확
- duplicate detection
- cancel policy
- audit history

Schedule Owner는 항상 하나만 존재.

---

# 16. MCP

초기:
`HERMES_ALLOW_MCP=false`

필요 시 MCP allowlist를 만든다.

등록 필드:
- server_name
- version
- owner
- purpose
- network
- data_scope
- write_permission
- secret_access
- risk_level
- approved_by
- approved_at

Unknown MCP 자동 연결 금지.

---

# 17. Browser

초기:
`HERMES_ALLOW_BROWSER=false`

후기 Research Pilot에서 제한적으로 허용.

허용 후보:
- official documentation
- public research
- release notes
- public technical references

금지:
- payment
- account change
- delete
- publish
- credential submission
- production admin

---

# 18. Terminal

기본:
`HERMES_ALLOW_TERMINAL=false`

운영 환경 unrestricted shell 금지.

필요 시 allowlist:
- read-only diagnostics
- approved test commands
- approved status commands

---

# 19. A2A / Webhook / Voice

현재 우선순위 낮음:
- A2A = Future
- Webhook = Future
- Voice = Future

추가 필요성이 명확해졌을 때 별도 ADR 작성 후 검토.

---

# 20. Job / Worker Integration

긴 Agent 작업은 동기 HTTP에서 실행하지 않는다.

```text
User Request
 ↓
Studio Job
 ↓
AgentTask
 ↓
Hermes
 ↓
Progress
 ↓
AgentResult
 ↓
Studio Job Complete
```

Task fields:
- job_id
- agent_task_id
- type
- status
- progress
- current_step
- created_at
- started_at
- updated_at
- completed_at
- timeout
- retry_count
- error_code
- review_required

---

# 21. Retry 정책

권장:
`Job Service = high-level retry owner`
`HermesAdapter = transport retry only`

중복 Retry 폭증 금지.

---

# 22. Timeout 정책

분리:
- health_timeout
- connect_timeout
- read_timeout
- task_timeout
- tool_timeout
- job_timeout

---

# 23. Security

원칙:
`Default Deny`
`Least Privilege`
`Explicit Allow`
`Human Approval`
`Audit Everything Important`

검토:
- authentication
- authorization
- CSRF
- CORS
- rate limit
- prompt injection
- tool injection
- path traversal
- secret leakage
- private content logging
- browser credential access
- MCP permission
- Skill supply-chain risk
- webhook signature
- file permission
- network egress

---

# 24. Audit Logging

상관관계 ID:
- request_id
- job_id
- agent_task_id
- course_id

기록:
- task requested
- task started
- skill invoked
- tool invoked
- tool denied
- subagent created
- task cancelled
- task completed
- task failed
- quality check requested
- human review requested

기록 금지:
- password
- api key
- jwt
- database secret
- full sensitive documents
- private prompt contents containing secrets

---

# 25. Publisher 안전 규칙

Hermes 결과는 항상 Draft.

가능하면 metadata:
- agent_generated=true
- review_required=true
- agent_provider=hermes
- agent_version=0.21.2
- skill_id
- skill_version
- agent_task_id
- generated_at
- source_count
- quality_gate_status
- human_approval_status

기존 Data Model 변경이 필요하면 PHASE H0에서 먼저 보고하고 승인 전 Migration 금지.

---

# 26. PHASE 구조

## PHASE H0 — Read-Only Audit

절대 모드:
```text
READ ONLY
NO CODE CHANGE
NO DB CHANGE
NO ENV CHANGE
NO NETWORK CHANGE
NO HERMES INSTALL
```

확인:
- project root
- AGENTS.md
- backend
- frontend
- routers
- services
- repositories
- configuration
- provider gateway
- LM Studio
- Ollama
- job/worker
- scheduler
- RAG
- web search/SearXNG
- quality gate
- human approval
- publication gate
- publisher
- auth
- logging
- timeout/retry/cancel
- tests
- backup/rollback
- docker/network
- ports

산출물:
```text
reports/hermes_h0/
  CURRENT_ARCHITECTURE.md
  AGENT_BOUNDARY_MAP.md
  DATA_OWNERSHIP.md
  TOOL_API_CANDIDATES.md
  PROVIDER_CONFLICT.md
  RAG_CONFLICT.md
  SCHEDULER_CONFLICT.md
  PUBLISHER_CONFLICT.md
  SECURITY_RISK.md
  H0_RESULT.md
```

판정:
- GO
- CONDITIONAL GO
- BLOCKED

---

## PHASE H1 — Adapter Skeleton

조건:
`H0 = GO`

구현:
- AgentAdapter
- HermesAdapter skeleton
- disabled config
- health model
- contract unit tests

PASS:
`HERMES_ENABLED=false` 상태에서 기존 Studio 회귀 0.

---

## PHASE H2 — Hermes v0.21.2 Local Connection

구현:
- Hermes version pin
- health
- version
- capability probe

기본:
`read-only`

PASS:
Hermes OFF/ON 모두 Studio 정상.

---

## PHASE H3 — Read-only Research Pilot

허용:
- Course read
- RAG search
- Search
- Evidence read
- Draft response

대표 Pilot:
```text
현재 12주 강의자료를 읽고
공식 최신자료와 비교하여
업데이트가 필요한 항목만 제안하라.
```

Studio 데이터 쓰기 금지.

---

## PHASE H4 — Skills

도입:
1. official_ai_update_research
2. release_note_analyzer
3. fact_source_checker
4. course_outline_builder

Skill output은 Draft.

---

## PHASE H5 — Controlled Draft Write

API를 통해서만:
- create_agent_draft
- update_agent_draft
- attach_research_result
- request_quality_check

자동 승인/자동 출판 금지.

---

## PHASE H6 — Limited Subagents

최대 2~3개.

권장:
- Research
- Fact Check
- Curriculum

Concurrency, timeout, cancel, budget 검증.

---

## PHASE H7 — Job Integration

Studio Job Service가 owner.

- progress
- retry
- cancel
- timeout
- result
- audit

Hermes Cron 여전히 비활성.

---

## PHASE H8 — Optional Advanced Features

별도 승인 후 하나씩:
- Bot Mode
- MCP
- Browser
- Cron
- A2A
- Webhook
- Voice

한 Phase에서 여러 고급 기능 동시 활성화 금지.

---

# 27. 업데이트 최적화 정책

Hermes 업데이트 순서:
1. Release note
2. Security note
3. Breaking change
4. state.db change
5. Memory migration
6. Tool/API change
7. Adapter contract test
8. Sandbox
9. Regression
10. Canary
11. Human approval
12. Production

Studio 업데이트 시 확인:
- AgentAdapter
- Tool API
- Auth Policy
- Job Contract
- RAG Contract
- Publication Gate

---

# 28. Canary

단계:
```text
Developer only
 ↓
Admin only
 ↓
Internal pilot
 ↓
Selected tasks
 ↓
General availability
```

---

# 29. Feature Flag

최우선:
`HERMES_ENABLED=false`

세부:
- READ
- WRITE
- SKILLS
- SUBAGENTS
- BROWSER
- TERMINAL
- MCP
- CRON
- BOT_MODE
- A2A
- WEBHOOK
- VOICE

---

# 30. Rollback

최종 목표:
`HERMES_ENABLED=false`

한 번으로 기존 Studio 구조 복귀.

Rollback 영향 0:
- Course DB
- RAG
- Provider settings
- Publication state
- Publisher
- MinIO
- User data

---

# 31. 회귀 테스트

반드시 유지:
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
- Preview
- Quality Gate
- Human Approval
- Publication Gate
- Publisher
- Publication rollback

---

# 32. 장애 테스트

반드시 테스트:
- Hermes OFF
- Hermes crash
- Hermes timeout
- Hermes malformed response
- Hermes state.db error
- Hermes tool failure
- Hermes subagent failure
- Web Search failure
- RAG failure
- LM Studio OFF
- Ollama OFF
- Worker stop
- Network disconnect

PASS:
`해당 기능만 실패하고 Studio 전체는 계속 동작한다.`

---

# 33. 최종 PASS Checklist

- [ ] H0 Read-Only Audit PASS
- [ ] 기존 기능 회귀 0
- [ ] Hermes disabled에서 Studio 정상
- [ ] Hermes 장애 시 Studio 정상
- [ ] Adapter boundary 유지
- [ ] DB direct access 0
- [ ] MinIO direct access 0
- [ ] pgvector direct access 0
- [ ] Provider Gateway replacement 0
- [ ] RAG ownership 유지
- [ ] Scheduler owner 하나
- [ ] Publisher direct access 0
- [ ] Quality Gate bypass 0
- [ ] Human Approval bypass 0
- [ ] Publication Gate bypass 0
- [ ] Secret leakage 0
- [ ] Retry bounded
- [ ] Timeout 분리
- [ ] Cancel 동작
- [ ] Audit 가능
- [ ] Version pinned
- [ ] Feature Flags 존재
- [ ] Rollback 가능

---

# 34. BLOCKED 조건

다음 중 하나라도 발생하면 즉시 중단:
- Hermes 도입을 위해 Studio DB direct access 필요
- Hermes 도입을 위해 Provider Gateway 제거 필요
- Hermes 도입을 위해 Hybrid RAG 제거 필요
- Hermes 도입을 위해 Publisher Gate 우회 필요
- 운영 데이터 migration 즉시 필요
- Secret 노출
- Rollback 불가
- 기존 핵심 회귀
- Hermes 실패가 Studio startup 실패를 유발
- Scheduler ownership 불명확

---

# 35. 권장 최종 운영 수준

적극 사용:
- Skills
- Research
- RAG Tool
- Search Tool
- Draft Generation
- Fact Check
- Limited Subagents

조건부 사용:
- Browser
- Job integration
- Scheduled Research
- MCP
- Bot Mode

현재 우선순위 낮음:
- A2A
- Voice
- External Webhook automation
- Unrestricted Terminal

---

# 36. Codex / 개발 Agent 실행 지시문

```text
AI 강의 활용 Studio v1.24.0에 Nous Research Hermes Agent v0.21.2를
안전하게 연동하기 위한 최적화 작업을 수행하라.

최우선 목표는 Hermes 기능 추가가 아니다.

현재 Studio의 Course, Document, Hybrid RAG, Provider Gateway,
LM Studio, Ollama, Job/Worker, Quality Gate, Human Approval,
Publication Gate, Publisher 구조를 그대로 보존하면서 Hermes를
교체 가능한 Agent Orchestration Service로 추가할 수 있는지를 먼저 검증한다.

Hermes는 Studio Core, Database, RAG, Provider Gateway, Job/Worker,
Publisher, Security Authority를 대체하지 않는다.

반드시 다음 경계를 목표로 하라.

UI
→ API
→ Application Agent Service
→ AgentAdapter
→ HermesAdapter
→ Hermes v0.21.2

Hermes가 내부 시스템을 사용할 때는 Studio Tool API만 사용한다.

금지:
- SQLite/PostgreSQL/pgvector/MinIO direct
- Provider direct
- Publisher direct
- Quality Gate bypass
- Human Approval bypass
- Publication Gate bypass
- unrestricted terminal
- automatic latest Hermes upgrade

운영 Hermes 버전은 v0.21.2로 Pin한다.

처음부터 Bot Mode, MCP, Cron, A2A, Voice를 활성화하지 마라.

초기 목표는:
1. Adapter
2. Health
3. Read-only
4. Skills
5. Research
6. 제한된 Subagent

첫 작업은 PHASE H0 Read-Only Audit만 수행하라.

READ ONLY
NO CODE CHANGE
NO DB CHANGE
NO ENV CHANGE
NO NETWORK CHANGE
NO HERMES INSTALL

실제 프로젝트에서 다음을 조사하라.

- project root / AGENTS.md
- backend / frontend
- routers / services / repositories
- configuration
- Provider Gateway
- LM Studio / Ollama adapters
- Job / Worker / Scheduler
- RAG / pgvector
- Search / SearXNG
- Quality Gate
- Human Approval
- Publication Gate
- Publication API / Snapshot
- Publisher
- Auth/AuthZ
- Logging
- Retry / Timeout / Cancel
- Tests
- Backup / Rollback
- Docker / Ports

다음 보고서를 작성하라.

reports/hermes_h0/
- CURRENT_ARCHITECTURE.md
- AGENT_BOUNDARY_MAP.md
- DATA_OWNERSHIP.md
- TOOL_API_CANDIDATES.md
- PROVIDER_CONFLICT.md
- RAG_CONFLICT.md
- SCHEDULER_CONFLICT.md
- PUBLISHER_CONFLICT.md
- SECURITY_RISK.md
- H0_RESULT.md

최종 판정:
GO
CONDITIONAL GO
BLOCKED

H0가 GO 또는 조건을 해결한 CONDITIONAL GO가 아니면
Hermes 코드를 추가하거나 설치하지 마라.

가장 중요한 최종 조건:

HERMES_ENABLED=false

상태에서 현재 AI 강의 활용 Studio의 모든 기존 핵심 기능이
변경 전과 동일하게 동작해야 한다.
```

---

# 37. 최종 아키텍처 원칙

- Loose Coupling
- Stable Contract
- Replaceable Adapter
- Single Data Owner
- Single Scheduler Owner
- Provider Isolation
- RAG Isolation
- Publisher Isolation
- Failure Isolation
- Least Privilege
- Version Pinning
- Feature Flag
- Canary
- Rollback First

---

# 38. 최종 권고

현재 프로그램에는 Hermes v0.21.2를 기준 버전으로 채택한다.

그러나 v0.21.2의 모든 기능을 한꺼번에 사용하지 않는다.

가장 안정적인 전략은 다음이다.

```text
최신 Hermes Engine
       +
단순한 초기 운영 범위
       +
Studio 주도권 유지
       +
Adapter 격리
       +
단계적 기능 활성화
```

이 방식이 현재 Studio의 구조 안정성, 장기 유지보수, 업데이트 용이성,
향후 Agent 교체 가능성을 모두 만족시키는 최적 방향이다.
