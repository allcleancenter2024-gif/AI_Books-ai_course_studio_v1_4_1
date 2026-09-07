$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $projectRoot ".env.searxng"
$composeFile = Join-Path $projectRoot "docker-compose.searxng.yml"

if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Host "SearXNG 환경 파일이 없어 중지할 별도 서비스가 없습니다."
    exit 0
}

docker compose --env-file $envFile -f $composeFile down
if ($LASTEXITCODE -ne 0) { throw "SearXNG 컨테이너 중지에 실패했습니다." }
Write-Host "SearXNG 별도 서비스가 중지되었습니다. Studio와 기존 Docker 서비스는 변경하지 않았습니다."
