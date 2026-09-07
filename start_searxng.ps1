param([int]$Port = 8888)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $projectRoot ".env.searxng"
$composeFile = Join-Path $projectRoot "docker-compose.searxng.yml"

if (-not (Test-Path -LiteralPath $envFile)) {
    $bytes = New-Object byte[] 32
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    $secret = [BitConverter]::ToString($bytes).Replace("-", "").ToLowerInvariant()
    [IO.File]::WriteAllText($envFile, "SEARXNG_SECRET=$secret`r`nSEARXNG_HOST_PORT=$Port`r`n", [Text.UTF8Encoding]::new($false))
}

docker compose --env-file $envFile -f $composeFile up -d
if ($LASTEXITCODE -ne 0) { throw "SearXNG 컨테이너 시작에 실패했습니다." }

Write-Host "SearXNG 시작 요청 완료: http://127.0.0.1:$Port"
Write-Host "상태 확인: docker compose --env-file .env.searxng -f docker-compose.searxng.yml ps"
