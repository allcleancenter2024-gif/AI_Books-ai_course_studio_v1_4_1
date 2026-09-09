# TAILSCALE HOST-ONLY REPORT

Mode: READ-ONLY AUDIT

Files Modified: NONE (Phase 11)

## Application: PASS

- Studio 기본 주소는 `127.0.0.1:8765`입니다.
- Tailscale 연동 코드나 애플리케이션 시작 의존성은 확인되지 않았습니다.
- 전체 회귀 테스트는 이전 단계에서 통과했습니다.

## Tailscale Independence: PASS WITH CONDITIONS

- Tailscale은 애플리케이션 코드에서 직접 제어하지 않습니다.
- Tailscale CLI 설치는 확인했으나 `tailscale status`에 유효한 peer 상태가 출력되지 않아 실제 Tailnet 연결은 NOT TESTABLE입니다.
- Exit Node, Subnet Router, Funnel, Serve, Sidecar, Custom DNS/Routes 적용 흔적은 확인되지 않았습니다.

## Docker: PASS WITH CONDITIONS

- Compose의 PostgreSQL, MongoDB, pgAdmin, Mongo Express, app-api 포트는 모두 `127.0.0.1`에 게시됩니다.
- Docker daemon이 실행되지 않아 컨테이너·네트워크 실제 상태는 NOT TESTABLE입니다.
- Compose 파일과 네트워크 구성은 변경하지 않았습니다.

## Windows: PASS WITH CONDITIONS

- Windows 실행기는 8765 포트와 이전 Studio 식별을 검사하며 임의 프로세스를 종료하지 않습니다.
- 현재 테스트 환경에서 Docker 설정 파일 ACL 경고가 확인되었습니다.

## Linux: WARNING

- Ubuntu 실행 절차는 운영 설명서에 있으나 이 Windows 환경에서 Linux 프로세스·systemd·iptables/nftables를 측정할 수 없습니다.
- Linux 방화벽·라우팅 변경은 수행하지 않았습니다.

## Firewall: NOT TESTABLE

- Windows Firewall, UFW, iptables, nftables, firewalld 상태를 변경하거나 추정하지 않았습니다.

## PostgreSQL: PASS WITH CONDITIONS

- 선택 구성으로 유지되며 기본 Studio SQLite 동작과 분리되어 있습니다.
- Compose 게시 포트는 localhost 전용입니다.
- Docker daemon 미실행으로 실제 인증·접속 상태는 확인하지 못했습니다.

## Redis: PASS

- 프로젝트의 기본 실행 경로에서 Redis를 영구 데이터 소스로 사용하지 않습니다.
- Tailscale 도입을 이유로 Redis 포트를 노출하지 않았습니다.

## MinIO: PASS

- 실제 Studio 구성에서 MinIO/S3 클라이언트가 확인되지 않았습니다.
- MinIO를 추가하거나 공개하지 않았습니다.

## n8n: WARNING

- 실제 n8n 서비스가 현재 프로젝트 실행 구성에서 확인되지 않았습니다.
- 외부 Webhook 및 Admin/UI 분리는 설계 원칙으로 유지되며 런타임 검증은 NOT TESTABLE입니다.

## Ollama: PASS WITH CONDITIONS

- 기본 주소는 `127.0.0.1:11434`이며 Tailscale Exit Node 의존성이 없습니다.
- 실제 Ollama 프로세스·모델 응답은 이번 감사에서 호출하지 않았습니다.

## LM Studio: PASS WITH CONDITIONS

- 기본 주소는 `127.0.0.1:12345`이며 Tailscale과 독립적입니다.
- 실제 LM Studio 프로세스·모델 응답은 이번 감사에서 호출하지 않았습니다.

## Public/Private Separation: PASS WITH CONDITIONS

- Studio, DB, 관리 도구는 localhost 중심입니다.
- Public website, OAuth callback, external webhook은 별도 HTTPS gateway가 필요하며 현재 프로젝트 범위를 넘어섭니다.

## Vendor Independence: PASS

- 애플리케이션은 일반 TCP/IP·HTTP·HTTPS·DNS만 사용합니다.
- Tailscale 교체 시 애플리케이션 코드 수정이 필요한 결합은 확인되지 않았습니다.

## Production Readiness: 82%

점수는 코드·정적 구성·회귀 테스트 기준입니다. 실제 Docker/Linux firewall/Tailnet peer/외부 Publisher 통합 측정이 남아 있어 100%로 판정하지 않습니다.

## Critical Issues

없음.

## High Issues

없음.

## Medium Issues

- Docker daemon이 꺼져 있어 컨테이너 네트워크와 선택 DB의 실제 상태를 확인할 수 없음.
- Linux 및 Tailscale peer 간 direct/relay 상태를 측정하지 못함.
- Publisher 외부 실행 프로그램과의 실제 handoff 통합 테스트가 없음.

## Low Issues

- pytest 캐시 ACL 및 Starlette/httpx deprecation 경고.
- n8n/MinIO는 실제 구성 요소가 아니므로 운영 도입 시 별도 설계 필요.

## Final Judgement

**APPROVED WITH CONDITIONS** — Tailscale Host-only Pilot 구조는 애플리케이션 변경 없이 유지 가능하며, Tailscale OFF 시에도 기본 Studio 경로가 영향을 받지 않는 설계입니다. 단, 실제 Pilot 적용 전 Docker daemon, Linux host, Tailnet peer, firewall, Publisher 통합을 운영 환경에서 별도로 검증해야 합니다.

## Recommended Next Step

현재 승인된 코드 작업의 필수 다음 단계는 **없다**. 실제 Tailscale 설치·연결 또는 운영 환경 검증을 진행하려면 별도의 명시적 실행 승인이 필요합니다.
