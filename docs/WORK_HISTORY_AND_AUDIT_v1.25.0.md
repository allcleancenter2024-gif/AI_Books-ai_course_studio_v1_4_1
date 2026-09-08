# AI Course Studio v1.25.0 작업 이력 및 검증 보고서

## 후속 텍스트 확대·보조기술 구조 점검

6개 페이지의 계산 글자 크기 200% 스트레스 검사 및 Chrome AX 트리 검사를 완료했다. 가로 넘침·텍스트 문자열 손실·이름 없는 링크 없음. 실제 브라우저 자체 200% 확대와 NVDA/VoiceOver 음성 검증은 완료로 간주하지 않는다. `publisher/scripts/audit-reading.mjs`와 접근성 보고서에 재현 방법·한계를 기록했다. 운영 애플리케이션 변경 및 재시작 없음.

## 후속 접근성 보완 — 2026-09-08

24개 화면 조합 자동 검사와 키보드 이동 점검을 수행하고 작은 브랜드/도움말 클릭 영역을 보완했다. 보완본은 releases/v1.25.0-a11y-20260908로 3010 Preview에 적용했다. 이전 릴리스는 보존했다. 세부 결과와 미실시 항목은 [접근성 보고서](PUBLISHER_ACCESSIBILITY_20260908.md) 참조.

## 후속 Publisher Preview 적용 — 2026-09-08 10:13 KST

- 기존 PID 22996의 Preview를 종료하고 검증된 standalone 빌드를 `publisher/releases/v1.25.0-preview-20260908`에 별도 보관하여 실행했다. 새 PID는 38472(재시작하면 달라짐).
- `127.0.0.1:3010`, 환경 preview, 공개 주소 미구성 유지. 이전 `.next/standalone`은 덮어쓰거나 삭제하지 않았다.
- 현재 빌드 ID: `45vGXXYyvUo800MraLwrq`. 릴리스 package.json 버전: 1.25.0.
- 주요 페이지 6개 200, 홈의 JS/CSS 자산 10개 200, 없는 교재 404 확인. Studio health는 계속 1.25.0/ok=true.
- Chrome에서 준비 상태 및 홈 목록의 콘텐츠·데스크톱 레이아웃 확인. 콘솔 전수 수집·모바일 실기기 검증은 미실시.
- Windows 실행 스크립트에 ReleaseDirectory 선택과 입력 검사 추가. PowerShell 구문 검사 통과. 재시작 명령은 publisher/deploy/README.md 참조.
- 정적 파일 복사 안내의 반복 실행 시 static/static 중첩 위험 수정. 릴리스 산출물은 Git·ESLint·소스 구문 검사에서 제외한다.
- 로그: logs/publisher-v125-stdout.log, logs/publisher-v125-stderr.log. 자동 시작 서비스는 미등록.
- 이번 단계에서 DB·네트워크·방화벽·Tailscale 설정 변경 없음. Ubuntu·모바일 접근성·PPT 템플릿 완성 및 실제 AI 종단간 검증은 남아 있다.


## 후속 운영 적용 기록 — 2026-09-08 10:10 KST

아래 본문의 '운영 프로세스 미전환'은 최초 보고 시점의 기록이다. 후속 진행 요청에 따라 Studio 운영 프로세스를 v1.25.0으로 전환했다.

- 변경 전 `/api/health`: v1.24.0. 작업 상태: complete 12건, error 1건, 진행 상태 없음.
- SQLite backup API로 `data/studio-pre-v125-20260908-100929.sqlite` 복구본 생성. 인증 정보를 포함할 수 있으므로 외부 공유 금지.
- 확인된 기존 Uvicorn PID 11076을 종료하고, 테스트에 사용한 `.venv` Python으로 새 서버 실행.
- 바인딩은 기존 `127.0.0.1:8765` 유지. 새 실행은 숨김 백그라운드 프로세스이며 Windows 자동 시작 서비스 등록은 하지 않았다.
- 변경 후 health: ok=true, version=1.25.0. 홈 200 및 버전 헤더 1.25.0, Publisher 메뉴 확인.
- workspace.css 및 app.js: 200. 비로그인 `/api/auth/session`, `/api/books`: 401로 인증 보호 유지.
- 로그: `logs/v125-server-stdout.log`, `logs/v125-server-stderr.log`.
- 이번 전환은 Studio 대상이다. 기존 Publisher Preview의 새 버전 교체 및 Ubuntu·모바일·실제 AI 생성·PPT 템플릿 검증은 별도 남은 항목이다.
- 재시작 시 기존 초기화 코드는 실행되지만, 새로운 DB 스키마 변경 코드를 추가하거나 데이터 삭제를 수행하지 않았다.


작성일: 2026-09-08. 이 문서는 실제 변경 파일과 실행한 검사 결과를 기준으로 작성한다.
상태: 소스 개선 및 Windows 로컬 Publisher 검증 완료. 운영 프로세스 교체, EXE 재패키징, 전체 기능의 외부 서비스 실연결 검증까지 완료했다는 의미는 아니다.

## 1. 기존 작업과 유지하는 구조

- 기존 Studio의 강의 생성 기능, 인증, DB와 Provider 구성을 유지한다.
- `publisher/`는 Studio와 분리된 Next.js 웹 교재 발행 계층이다. 검토한 Markdown을 소비하며 Studio 시작의 필수 의존성이 아니다.
- 기존 Publisher에는 smartphone-basics/week-01 예제, 파스텔 테마, 교재/도움말/법률 초안/준비 상태 화면과 Windows·Ubuntu 실행 안내가 있다.
- 실제 도메인이 없는 상태를 정상적인 미구성 상태로 취급한다. DNS, TLS, 공개 포트는 변경하지 않았다.
- PPT 기준본 선택은 `exports/books/book_55_12weeks_1-1_combined.pptx`이다. 개인 PPT 템플릿 스킬 패키징과 반복 산출물 품질 검증은 완료로 간주하지 않는다.

```text
Studio: 작성·생성·기존 저장소
  └─ 검토된 Markdown
       └─ Publisher: 공통 파서 → 검사 → Next.js 빌드 → 별도 Preview

선택형 Host 관리 네트워크(Tailscale)
  └─ 애플리케이션 시작·인증·저장소·AI Provider의 필수 조건 아님
```

## 2. v1.25.0 변경 분류

| 분류 | 변경 | 주요 파일 |
|---|---|---|
| 버전 | 소스 버전 1.25.0, 날짜 및 실행 안내 갱신 | studio/config.py, run_windows.bat, README.md |
| 안전성 | HTTP 500 응답에서 내부 예외 상세 제거 | studio/application.py, tests/test_release_safety.py |
| 안내 정확성 | 로그인 문구를 로컬 서버 인증 방식에 맞게 수정 | static/index.html |
| 메뉴 | 교육 준비 / 교재 제작 / 정보 검토 / 운영 관리 / 웹 교재 발행으로 그룹화 | static/index.html, static/css/workspace.css |
| 메뉴 접근 | 교육 제작 설정 및 Publisher 이동 추가, 기존 앵커 유지 | static/index.html |
| 접근성 기반 | 포커스 표시, 큰 클릭 영역, 본문 바로가기, 모션 감소 대응 | workspace.css, publisher/app/layout.tsx, globals.css |
| 모듈화 | CLI 검사와 웹 렌더링이 같은 Markdown 계약 파서를 사용 | publisher/lib/markdown-contract.mjs, content.ts, scripts/check-content.mjs |
| 입력 검증 | ID·published·소요 시간·필수 제목·중복 메타데이터 검사 | markdown-contract.mjs, publisher/tests/content.test.mjs |
| 설정 분리 | URL 형식과 실제 DNS/TLS 검증을 분리, 공개 승인 false 유지 | config-policy.mjs, public-config.ts, readiness.ts |
| 성능 | 요청 내 콘텐츠 조회 재사용, 알려지지 않은 교재 경로 404 | content.ts, courses/[courseId]/[lessonId]/page.tsx |
| 의존성 | Next.js 및 eslint-config-next 16.3.4 적용, lockfile 갱신 | publisher/package.json, package-lock.json |
| 검증 안정성 | Windows pytest 임시 폴더 충돌 수정 | tests/conftest.py |
| 재현성 | 소스 검사 도구와 회귀 테스트 추가, 별도 빌드 디렉터리 지원 | scripts/audit_source.py, next.config.ts |
| 검사 수정 | `.next-review` 등 생성 산출물을 ESLint에서 제외 | publisher/eslint.config.mjs |

큰 전면 재작성이나 데이터 이전 대신 공통 로직 분리와 회귀 검사 추가를 우선했다. 최적화 효과의 수치 벤치마크는 수행하지 않았다.

## 3. 확인된 문제와 처리

- MEDIUM: 임의 문자열 또는 HTTPS 접두사만으로 공개 준비를 판정하던 오류 수정. 유효한 주소도 네트워크 실검증 전에는 미검증이다.
- MEDIUM: 원고 검사와 렌더러의 해석 불일치 수정. 하나의 제한된 Markdown 메타데이터 계약을 공유한다.
- MEDIUM: 내부 예외 상세가 응답에 포함되는 문제 수정. 회귀 테스트 추가.
- MEDIUM: Windows 공유 임시 디렉터리 ACL로 테스트 1개가 실패하던 문제 수정.
- LOW: 로그인 안내와 실제 동작 불일치 수정.
- LOW: 재빌드 후 생성 파일까지 ESLint가 검사하여 실패하던 문제 수정. 소스 검사 규칙을 완화하지 않고 빌드 산출물만 제외했다.
- 의존성 검사에서 보고된 HIGH 항목은 Next.js 관련 패키지 갱신 후 재검사했다. 현재 운영 의존성 audit 결과는 0건이다.

## 4. 실행 검증 결과

| 검사 | 결과 | 범위/제한 |
|---|---|---|
| Python pytest 전체 | 61 passed, 2 warnings, 12.52초 | 테스트에 포함된 기능만 증명 |
| Python 의존성 일관성 | pip check 통과 | 취약점 전수 검사는 아님 |
| 소스 구문·메뉴 앵커 검사 | Issues: 0 | Python 52개 및 JS/MJS 등; 사용자 데이터·라이브러리·빌드 제외 |
| Publisher 단위 테스트 | 6 passed | 설정 정책 및 Markdown 계약 |
| 콘텐츠 스키마/상대 링크 | 통과 | 외부 링크 전체 가용성 검사는 아님 |
| ESLint/TypeScript/production build | 통과 | Next.js 16.3.4, .next-review 격리 빌드 |
| 운영 의존성 npm audit | 0 vulnerabilities | 실행 시점 레지스트리 기준 |
| standalone HTTP | 6개 정상 경로 200, 없는 교재 404 | 127.0.0.1:3012 검증 서버 |
| 정적 자산 | 홈에서 추출한 10개 자산 모두 200 | JS/CSS 로딩 응답 확인 |
| Chrome 화면 | 준비 상태/대표 교재 콘텐츠 및 데스크톱 레이아웃 확인 | 큰 글씨·카드 출력, 빈 화면 없음 |
| Git diff --check | 공백 오류 없음 | CRLF 변환 안내만 있음 |

단독 브라우저 CLI가 없어 연결된 Chrome으로 검증 스킬의 화면 확인 항목을 대체했다. 브라우저 콘솔 전체 수집, 모바일 실기기, 스크린리더, WCAG 정식 감사는 미실시다. 테스트의 두 경고는 Starlette/httpx 및 AnyIO deprecated API 관련이며 이번 실행은 실패하지 않았다.

검사 예시(PowerShell):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\audit_source.py
Set-Location publisher
$env:PUBLISHER_BUILD_DIR = '.next-review'
npm.cmd run check
npm.cmd audit --omit=dev --audit-level=low
```

## 5. 배포 및 되돌리기

- 운영 중인 Studio와 기존 Preview는 자동 재시작하지 않았다. 브라우저의 기존 Studio는 v1.24.0으로 표시되며 소스 버전과 실행 프로세스 버전은 구분해야 한다.
- 새 실행 파일(EXE)을 만든 것은 아니다. 새 소스를 적용하려면 진행 중인 생성 작업을 종료한 뒤 관리자가 소스 실행 절차로 재시작해야 한다.
- `.next-review`는 운영 `.next`를 덮어쓰지 않는 검증 빌드다. 실제 서비스 교체 시 기존 배포본 보관 → 동일 환경 빌드/자산 포함 → 새 프로세스 점검 → 전환 → 스모크 테스트 순서가 필요하다.
- standalone 배포에는 생성 서버뿐 아니라 해당 빌드의 static 자산도 함께 포함해야 한다.
- 기존 DB, 내보내기 결과, Docker, 방화벽, 바인딩, AI Provider 및 Tailscale 설정은 변경하지 않았다.
- Git commit/reset/clean/stash는 수행하지 않았다. 기존 untracked Publisher를 보존했고 신규 변경도 아직 커밋하지 않았다. 되돌릴 때 사용자 변경과 이번 변경을 diff로 구분하여 선택 복원해야 한다.

## 6. 남은 확인 사항

1. 운영 프로세스에 v1.25.0 적용 및 해당 프로세스의 스모크 테스트.
2. Ubuntu 실제 서버에서 실행·권한·서비스 관리자 동작 확인. 현재 Windows 검증을 Ubuntu 성공으로 확대하지 않는다.
3. 실제 AI Provider 생성, 대용량 파일, 전체 관리자 흐름에 대한 실환경 종단간 검사. 비용·데이터 변경을 수반하는 작업은 이번 자동 검사 범위에서 제외했다.
4. 모바일/키보드/스크린리더 및 정식 접근성 검사.
5. 선택 PPTX 기반 개인 템플릿 스킬 완성 및 PPT·웹 반복 출력 비교.
6. 공개 운영이 필요해지면 실제 도메인, TLS, 운영자 정보, 개인정보/약관 검토를 별도 수행.

## 7. TAILSCALE HOST-ONLY REPORT

Mode: IMPLEMENTATION (애플리케이션 소스 개선; Tailscale Pilot은 미실시)

Files Modified: 위 변경 분류와 Git diff 참조. 네트워크 설정 변경 없음.

Application: PASS (명시한 테스트 범위), Tailscale Independence: WARNING (ON/OFF 실측 미실시), Docker: WARNING (런타임 미검증), Windows: PASS (로컬 검사 범위), Linux: WARNING (실서버 미검증).

Firewall / PostgreSQL / Redis / MinIO / n8n / Ollama / LM Studio: WARNING (해당 서비스의 존재·가동·연동 성공을 이번 결과만으로 확정하지 않음).

Public/Private Separation: WARNING (공개 설정 변경 없음; 외부 노출 전수 조사 미실시).

Vendor Independence: WARNING (애플리케이션에 Tailscale 의존성을 추가하지 않았으나 전 환경 장애 격리 실험은 미실시).

Production Readiness: 산정하지 않음. 근거 없는 0–100% 점수 대신 위 완료/미검증 항목으로 판정한다.

Critical Issues: 이번 검사에서 확인되지 않음. 전수 부재 보장은 아님.

High Issues: 의존성 검사 보고 항목 조치 후 운영 npm audit 0건.

Medium/Low Issues: 3절 조치 내역 및 6절 미검증 항목 참조.

Recommended Next Step: 운영 중 작업 보호 후 v1.25.0 프로세스 적용 및 실환경 스모크 테스트. Tailscale Pilot 승인 판정은 이번 작업 범위가 아니다.
