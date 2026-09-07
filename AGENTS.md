# AGENTS.md
# AI Studio — Codex Project Safety & Tailscale Architecture Rules

## 1. Project Mission

이 프로젝트는 Windows 개발환경과 Ubuntu Linux 운영환경에서 장기적으로 운영할 수 있는 모듈형 AI Studio를 목표로 한다.

주요 구성 요소는 프로젝트에 실제 존재하는 것을 우선 확인한다.

예상 구성 요소:

- Frontend
- FastAPI 또는 Backend API
- PostgreSQL
- pgvector
- Redis
- MinIO 또는 S3-compatible storage
- n8n
- Ollama
- LM Studio
- Cloud AI Providers
- Docker / Docker Compose

추측으로 존재하지 않는 서비스를 추가하지 않는다.

---

## 2. 최우선 원칙

### 현재 정상 프로그램을 보호한다

기본 우선순위:

```text
Analyze > Report > Plan > Change
Repair > Rewrite
Backward Compatibility > Breaking Change
Small Change > Large Rewrite
```

사용자가 명시적으로 구현을 요청하지 않은 경우 코드를 수정하지 않는다.

---

## 3. 현재 Tailscale 작업의 기본 정책

Tailscale은 다음 역할만 가진다.

```text
OPTIONAL PRIVATE MANAGEMENT NETWORK
```

Tailscale은 Application의 핵심 구성 요소가 아니다.

권장 구조:

```text
Host OS
│
├── Tailscale
│
└── Existing Application
     ├── Docker
     ├── Studio
     ├── PostgreSQL
     ├── Redis
     ├── MinIO
     ├── n8n
     ├── Ollama
     └── LM Studio
```

---

## 4. 매우 중요한 Tailscale 독립성

Tailscale이 다음 작업의 필수 조건이 되어서는 안 된다.

```text
Application startup
Application login
Database login
AI Provider selection
Storage access
Queue processing
n8n execution
Application health
```

다음 조건을 반드시 만족해야 한다.

```text
Tailscale ON
→ Application 정상

Tailscale OFF
→ Application 정상
```

Tailscale OFF 시 허용되는 영향은:

```text
Private remote management unavailable
```

정도여야 한다.

---

## 5. Application에서 Tailscale을 직접 제어하지 않는다

다음과 같은 코드를 작성하지 않는다.

```python
if tailscale_connected():
    start_application()
```

다음과 같은 구조도 만들지 않는다.

```text
Studio
 ↓
Tailscale API
 ↓
Application Logic
```

Application은 일반적인 다음 네트워크 기술만 인식하도록 유지한다.

```text
TCP/IP
HTTP
HTTPS
DNS
```

Tailscale은 Host OS가 처리한다.

---

## 6. Tailscale Vendor Lock-in 금지

현재 Tailscale을 사용하더라도 향후 다음으로 교체 가능해야 한다.

```text
WireGuard
Headscale
ZeroTier
Other private networking solution
```

목표:

```text
Change private network provider
        ↓
Application code modification = 0
```

---

## 7. Tailscale을 인증 대체 수단으로 사용하지 않는다

금지:

```text
Tailscale user
=
Application Admin
```

금지:

```text
Tailscale access
=
Database authentication
```

기존 인증을 유지한다.

예:

```text
Network Access
+
Application Authentication
+
RBAC
+
Database Authentication
+
Service Authentication
```

---

## 8. 초기 Tailscale 도입 범위

초기에는 기본 Tailnet 연결만 검토한다.

다음 기능은 기본적으로 OFF로 간주한다.

```text
Exit Node
Subnet Router
Tailscale Funnel
Tailscale Serve
Custom Routes
Custom DNS
Docker Tailscale Sidecar
Custom netfilter mode
```

사용자가 별도로 요청하기 전에는 활성화를 제안하더라도 자동 적용하지 않는다.

---

## 9. Tailscale 설치 위치

우선 권장:

```text
Windows Host
or
Ubuntu Host
        │
    Tailscale
```

Tailscale을 애플리케이션 Docker network의 필수 gateway로 사용하지 않는다.

다음 구조를 기본 구조로 만들지 않는다.

```text
Docker
├── Tailscale Gateway
├── Studio
├── PostgreSQL
└── ...
```

Tailscale container 장애가 전체 Application network 장애로 전파되지 않아야 한다.

---

## 10. Public / Private 역할 분리

Tailscale:

```text
Private administrator access
Private server management
SSH
Internal monitoring
Admin dashboards
Optional DB administration
Optional storage administration
```

Public Gateway:

```text
Public Website
Public API
OAuth Callback
n8n External Webhook
Third-party Callback
```

Tailscale을 Public Gateway 대체 수단으로 사용하지 않는다.

---

## 11. Tailscale Funnel 기본 금지

초기에는:

```text
Tailscale Funnel = OFF
```

특히 다음 서비스를 Funnel로 공개하지 않는다.

```text
PostgreSQL
Redis
MinIO Console
Ollama
LM Studio
Internal Admin APIs
```

---

## 12. Exit Node 기본 금지

Studio 서버에서:

```text
Exit Node = OFF
```

를 기본값으로 간주한다.

외부 AI Provider:

```text
OpenAI
Gemini
Claude
Other cloud APIs
```

의 outbound traffic을 Tailscale Exit Node로 강제로 우회시키지 않는다.

---

## 13. Subnet Router 기본 OFF

초기 Pilot에서는:

```text
Subnet Router = OFF
```

NAS나 별도 LAN 접근이 실제로 필요한 경우에만 향후 독립 기능으로 검토한다.

---

## 14. 기존 Docker 구성 보호

사용자가 변경을 명시적으로 요청하지 않는 한:

```text
docker-compose.yml
Dockerfile
Docker networks
Docker volumes
Docker published ports
```

를 변경하지 않는다.

Tailscale 적용 가능성 검토를 이유로 Docker 구성을 자동 변경하지 않는다.

---

## 15. Docker + Linux Network 주의사항

Linux에서는 다음 구성 요소가 상호작용할 수 있다.

```text
Tailscale
   │
tailscale0
   │
iptables / nftables
   │
Docker
```

검토 대상:

```text
iptables
nftables
UFW
firewalld
Docker NAT
Docker bridge
FORWARD
DOCKER-USER
routing
DNS
```

그러나 문제를 발견했다고 바로 설정을 변경하지 않는다.

먼저 보고한다.

---

## 16. Firewall 보호

분석 단계에서는 다음을 변경하지 않는다.

```text
UFW
iptables
nftables
firewalld
Windows Firewall
```

방화벽 문제 발견 시:

```text
finding
impact
risk
recommended change
rollback
```

을 보고한 후 기다린다.

---

## 17. 서비스 포트 보안

실제 프로젝트의 포트 값을 먼저 확인한다.

일반적으로 다음 서비스는 Public Internet에 직접 공개하지 않는 방향을 유지한다.

```text
PostgreSQL
Redis
MinIO Console
Ollama
LM Studio
Internal n8n Admin UI
Internal Admin APIs
```

포트 공개 상태를 다음처럼 분류한다.

```text
LOCALHOST ONLY
DOCKER INTERNAL
HOST
LAN
TAILNET
PUBLIC
UNKNOWN
```

---

## 18. Binding 자동 수정 금지

다음 값을 조사한다.

```text
127.0.0.1
localhost
0.0.0.0
::
host.docker.internal
```

예를 들어 Studio가:

```text
127.0.0.1:8765
```

에만 bind되어 있어서 Tailnet peer에서 접근할 수 없더라도 자동으로:

```text
0.0.0.0:8765
```

로 변경하지 않는다.

먼저 보안 영향과 대안을 보고한다.

---

## 19. PostgreSQL 원칙

PostgreSQL은 Tailscale 도입 후에도 기존 인증을 유지한다.

```text
User
Password / Secret
Role
Permission
Database
```

Tailscale 접속 가능성을 이유로 DB 인증을 약화시키지 않는다.

Public Internet에 PostgreSQL을 직접 공개하지 않는다.

---

## 20. Redis 원칙

Redis는 기본적으로 내부 서비스로 유지한다.

Tailscale 사용을 이유로 Redis를 Host/Public에 노출하지 않는다.

Permanent Data Source로 Redis를 사용하지 않는다.

---

## 21. MinIO 원칙

MinIO API와 MinIO Console을 구분한다.

```text
MinIO API
→ Application internal usage

MinIO Console
→ Administrator/private access
```

MinIO Console을 Public Internet에 직접 노출하지 않는다.

---

## 22. Ollama 원칙

Ollama는 내부 AI Provider로 유지한다.

Tailscale 도입을 이유로:

```text
OLLAMA_HOST
bind address
port exposure
```

를 자동 변경하지 않는다.

필요성을 먼저 분석한다.

---

## 23. LM Studio 원칙

LM Studio도 내부 Provider로 취급한다.

Tailscale 적용이 LM Studio 연결 구조 변경의 이유가 되어서는 안 된다.

Windows와 Linux 차이는 별도로 보고한다.

---

## 24. Cloud AI Provider 원칙

Cloud providers는 Tailscale과 독립적으로 동작해야 한다.

예:

```text
Studio
 ↓
OpenAI / Gemini / Claude
```

기본 Host Internet route를 사용한다.

Tailscale Exit Node 의존성을 만들지 않는다.

---

## 25. n8n 원칙

n8n을 두 영역으로 구분한다.

```text
Admin/UI
→ Private

External Webhook
→ Public HTTPS Endpoint
```

외부 Webhook을 Tailnet-only 주소로 변경하지 않는다.

---

## 26. OAuth 원칙

Production OAuth callback은 Public HTTPS endpoint를 유지하는 방향을 우선한다.

예:

```text
https://example.com/auth/callback
```

다음 주소를 Production OAuth callback으로 자동 교체하지 않는다.

```text
localhost
127.0.0.1
100.x.x.x
*.ts.net
```

---

## 27. 대용량 파일

프로젝트에서 대용량 파일을 처리하는 경우:

```text
PDF
PPTX
DOCX
Image
Audio
Video
up to approximately 500MB
```

Tailscale Direct/Relay 성능 문제와 Application 처리 성능 문제를 분리해서 분석한다.

다음 원인을 구분한다.

```text
NETWORK
APPLICATION
WORKER
STORAGE
DATABASE
AI PROVIDER
```

---

## 28. Direct / DERP 진단

Tailscale이 이미 설치되어 있다면 상태를 변경하지 않는 안전한 진단만 고려한다.

예:

```text
tailscale status
tailscale netcheck
tailscale ping <existing-peer>
```

결과:

```text
DIRECT
PEER RELAY
DERP
NOT TESTABLE
```

실제 측정을 하지 못했으면 임의 숫자를 만들지 않는다.

---

## 29. Read-only Audit 모드

사용자가:

```text
분석
검사
검증
테스트만
변경하지 마
```

라고 요청하면 반드시 Read-only Audit Mode로 동작한다.

허용:

```text
READ
INSPECT
ANALYZE
GET
STATUS
REPORT
SAFE TEST
```

금지:

```text
EDIT
WRITE
PATCH
DELETE
INSTALL
UNINSTALL
RESTART
MIGRATE
APPLY
RESET
PRUNE
```

---

## 30. Destructive 명령 금지

사용자 명시 승인 없이 실행하지 않는다.

```text
rm -rf
DROP DATABASE
DROP TABLE
TRUNCATE
docker system prune
docker volume prune
docker network prune
git reset --hard
git clean -fd
database reset
volume delete
credential delete
```

---

## 31. Git 안전성

기존 사용자 변경사항을 보호한다.

자동으로:

```text
git restore
git reset
git clean
git stash
```

하지 않는다.

Read-only 분석 시 작업 시작과 종료 시 Git 상태를 비교한다.

목표:

```text
Files modified by audit:
NONE
```

---

## 32. Secrets 보호

다음 값을 출력하거나 Git에 저장하지 않는다.

```text
API keys
Passwords
JWT secrets
OAuth secrets
Database credentials
MinIO secret keys
Access tokens
Refresh tokens
Tailscale auth keys
```

로그에서도 마스킹한다.

---

## 33. 분석 우선순위

프로젝트를 다음 순서로 분석한다.

```text
1. Repository structure
2. Application architecture
3. Running services
4. Ports and bindings
5. Docker networks
6. Database/storage
7. AI Providers
8. n8n
9. Windows compatibility
10. Linux compatibility
11. Firewall/netfilter
12. Tailscale Host-only suitability
13. Failure isolation
14. Rollback feasibility
15. Production readiness
```

---

## 34. 위험도

모든 발견사항을 다음 등급으로 분류한다.

```text
CRITICAL
HIGH
MEDIUM
LOW
```

CRITICAL/HIGH 문제를 발견하더라도 사용자의 명시 승인 없이는 수정하지 않는다.

---

## 35. Pilot 승인 기준

다음을 만족하면 Tailscale Host-only Pilot을 승인할 수 있다.

```text
Application unchanged
Tailscale optional
Docker independent
Database independent
Storage independent
AI Providers independent
Public/Private separation maintained
No critical routing conflict
No critical firewall conflict
Simple rollback available
```

최종 판정:

```text
APPROVED
APPROVED WITH CONDITIONS
NOT APPROVED
```

---

## 36. Pilot 적용 순서

향후 사용자가 실제 Pilot 적용을 명시적으로 승인했을 경우에도 다음 순서를 사용한다.

```text
1. Record baseline
2. Verify Git status
3. Verify running services
4. Record listening ports
5. Record Docker networks
6. Record firewall/routing
7. Install Tailscale on Host only
8. Do not enable advanced Tailscale features
9. Verify existing Application
10. Verify Windows ↔ Linux Tailnet
11. Verify mobile ↔ server Tailnet
12. Check direct/relay status
13. Verify Docker connectivity
14. Verify Cloud AI outbound
15. Compare with baseline
16. Stop and report
```

---

## 37. Pilot에서 하지 않을 것

초기 Pilot에서는 다음을 사용하지 않는다.

```text
Exit Node
Subnet Router
Funnel
Serve
Docker Sidecar
Custom Routes
Custom DNS
Custom netfilter mode
Firewall redesign
Application binding changes
Database configuration changes
```

---

## 38. Rollback 목표

Tailscale 문제가 발생할 경우 목표 rollback은:

```text
Disable/remove Tailscale
         ↓
Original Application state
```

이어야 한다.

Application source rollback이 필요하다면 아키텍처 설계가 잘못된 것이다.

---

## 39. 보고서 요구사항

분석 작업 후 다음 형식으로 보고한다.

```text
TAILSCALE HOST-ONLY REPORT

Mode:
READ-ONLY / PILOT / IMPLEMENTATION

Files Modified:
NONE or list

Application:
PASS / WARNING / FAIL

Tailscale Independence:
PASS / WARNING / FAIL

Docker:
PASS / WARNING / FAIL

Windows:
PASS / WARNING / FAIL

Linux:
PASS / WARNING / FAIL

Firewall:
PASS / WARNING / FAIL

PostgreSQL:
PASS / WARNING / FAIL

Redis:
PASS / WARNING / FAIL

MinIO:
PASS / WARNING / FAIL

n8n:
PASS / WARNING / FAIL

Ollama:
PASS / WARNING / FAIL

LM Studio:
PASS / WARNING / FAIL

Public/Private Separation:
PASS / WARNING / FAIL

Vendor Independence:
PASS / WARNING / FAIL

Production Readiness:
0-100%

Critical Issues:
...

High Issues:
...

Medium Issues:
...

Low Issues:
...

Recommended Next Step:
...
```

---

## 40. 최종 성공 조건

가장 중요한 조건은 다음이다.

> Tailscale이 있어도 Application은 정상이어야 하고, Tailscale을 제거해도 Application은 정상이어야 한다.

그리고:

> Tailscale은 Host OS의 선택형 Private Management Network일 뿐 Application dependency가 아니다.
