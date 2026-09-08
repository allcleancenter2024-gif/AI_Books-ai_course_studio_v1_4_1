# 자체 서버 배포 가이드

Publisher는 기존 AI Course Studio와 별도 프로세스로 운영합니다. Studio의 포트 8765, SQLite 데이터, Docker Compose, API 키를 사용하거나 변경하지 않습니다. 도메인과 HTTPS가 준비되기 전 Publisher는 `127.0.0.1`에만 수신합니다.

## 공통 사전 점검

1. `publisher` 폴더만 서버에 배포합니다. `node_modules`, `.next`, `.env`는 복사하지 않습니다.
2. 서버에서 Node.js LTS를 설치합니다.
3. `npm.cmd ci`(Windows) 또는 `npm ci`(Ubuntu), `npm run check`, `npm run build`를 순서대로 실행합니다.
4. 정적 자산을 standalone 출력으로 복사합니다.

```powershell
# Windows PowerShell
New-Item -ItemType Directory -Force .next\standalone\.next\static | Out-Null
Get-ChildItem -Force .next\static | Copy-Item -Recurse -Force -Destination .next\standalone\.next\static
if (Test-Path public) {
  New-Item -ItemType Directory -Force .next\standalone\public | Out-Null
  Get-ChildItem -Force public | Copy-Item -Recurse -Force -Destination .next\standalone\public
}
```

```bash
# Ubuntu
mkdir -p .next/standalone/.next/static
cp -R .next/static/. .next/standalone/.next/static/
if [ -d public ]; then
  mkdir -p .next/standalone/public
  cp -R public/. .next/standalone/public/
fi
```

## Windows Preview

서버 콘솔에서 다음을 실행합니다.

```powershell
.\deploy\windows\start-publisher.ps1 -Port 3010
```

2026-09-08 접근성 보완 후 현재 릴리스는 `releases/v1.25.0-a11y-20260908`입니다. 현재 프로세스를 종료한 뒤 동일 배포본을 다시 실행하려면 아래 명령을 사용합니다. 실행 중인 서버 위에서 재빌드하지 않습니다.

```powershell
.\deploy\windows\start-publisher.ps1 -Port 3010 -ReleaseDirectory 'releases\v1.25.0-a11y-20260908'
```

현재 릴리스는 `.next-a11y` 빌드명과 정적 자산을 함께 보존합니다. 이전 Preview 릴리스와 `.next/standalone`은 보존했습니다. Windows 자동 시작 서비스는 등록하지 않았습니다.

같은 서버에서 `http://127.0.0.1:3010`을 먼저 확인합니다. 외부 공개가 필요할 경우에는 역방향 프록시와 HTTPS를 별도로 구성하고, Publisher만 대상으로 제한합니다. Studio의 8765 포트나 데이터베이스 포트를 공개하지 않습니다.

## Ubuntu 운영 서비스

1. Publisher를 `/opt/ai-course-studio/publisher`에 배치합니다.
2. 전용 비로그인 계정 `publisher`를 만들고 해당 디렉터리의 소유권을 부여합니다.
3. `deploy/ubuntu/ai-course-publisher.service`를 `/etc/systemd/system/`에 복사합니다.
4. 서비스 정의의 `User`, `WorkingDirectory`, `ExecStart` 경로를 실제 배치 경로에 맞춥니다.
5. 다음 명령을 실행합니다.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ai-course-publisher
sudo systemctl status ai-course-publisher
curl -f http://127.0.0.1:3010/
```

## Preview에서 운영으로 승격

1. Preview에서 `npm run check`를 통과시킵니다.
2. 브라우저에서 목록, 교재 상세, 교재 복귀와 모바일 레이아웃을 확인합니다.
3. 운영 서버에서도 `curl -f http://127.0.0.1:3010/`으로 스모크 테스트합니다.
4. HTTPS 역방향 프록시의 공개 도메인으로 최종 확인합니다.

운영 도메인, TLS 인증서, 역방향 프록시와 방화벽은 서버별 보안 경계에 영향을 주므로 자동으로 변경하지 않습니다.
