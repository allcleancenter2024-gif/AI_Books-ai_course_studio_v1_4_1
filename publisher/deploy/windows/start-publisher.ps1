param(
  [ValidateRange(1, 65535)][int]$Port = 3010,
  [string]$ReleaseDirectory = '.next\standalone'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root
$release = (Resolve-Path -LiteralPath $ReleaseDirectory).Path
if (-not (Test-Path -LiteralPath (Join-Path $release 'server.js'))) {
  throw 'Release server.js is missing.'
}
Set-Location $release
$env:NODE_ENV = 'production'
$env:PUBLISHER_APP_ENV = 'preview'
$env:PORT = $Port
$env:HOSTNAME = '127.0.0.1'
& node server.js
exit $LASTEXITCODE
