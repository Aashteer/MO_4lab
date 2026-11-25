# Build and smoke-check the extra Compose stack (MLflow + API + gate).
# ASCII only for Windows PowerShell 5.1.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$env:Path = "C:\Program Files\Docker\Docker\resources\bin;" + $env:Path
$env:IMAGE_TAG = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "v1" }
$env:GIT_PYTHON_REFRESH = "quiet"

Write-Host "Computing model hash..."
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
& $Py -m src.model_hash --model-dir (Join-Path $Root "exported_model") --results-dir (Join-Path $Root "results")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Building and starting mlflow + seeds-api + api-check..."
docker compose -f compose.extra.yaml up -d --build mlflow seeds-api
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Waiting for API health..."
$Ready = $false
for ($i = 0; $i -lt 60; $i++) {
  try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 3
    if ($resp.StatusCode -eq 200) { $Ready = $true; break }
  } catch {
    Start-Sleep -Seconds 2
  }
}
if (-not $Ready) {
  Write-Host "API did not become healthy"
  docker compose -f compose.extra.yaml logs --tail 80
  exit 1
}

Write-Host "Running api-check gate..."
docker compose -f compose.extra.yaml run --rm api-check
if ($LASTEXITCODE -ne 0) {
  Write-Host "api-check FAILED; stack is not considered successful"
  exit $LASTEXITCODE
}

Write-Host "Optional train worker (profile=train):"
Write-Host '  docker compose -f compose.extra.yaml --profile train run --rm train'
Write-Host "EXTRA_STACK_OK"
exit 0
