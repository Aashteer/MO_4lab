# Move the champion alias to the other registered version, export it aside,
# then move the alias back. No training commands are invoked.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:GIT_PYTHON_REFRESH = "quiet"
$env:MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $VenvPy) { $Python = $VenvPy } else { $Python = "python" }

function Invoke-Step([string[]]$ArgList) {
  Write-Host ("RUN python " + ($ArgList -join " "))
  & $Python @ArgList
  if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): python $($ArgList -join ' ')" }
}

$infoPath = Join-Path $Root "results\export_info.json"
if (-not (Test-Path $infoPath)) { throw "results\export_info.json is missing. Export the champion first." }
$original = [string](Get-Content -Raw -Encoding UTF8 $infoPath | ConvertFrom-Json).version
Write-Host "ORIGINAL_CHAMPION $original"
Invoke-Step @("-m", "src.promote", "--to-other", "--alias", "champion", "--note", "update-without-retrain")
Invoke-Step @("-m", "src.export_model", "--output", (Join-Path $Root "results\exported_challenger"), "--no-samples")
Invoke-Step @("-m", "src.promote", "--version", $original, "--alias", "champion", "--note", "rollback-without-retrain")
Invoke-Step @("-m", "src.export_model")
$final = [string](Get-Content -Raw -Encoding UTF8 $infoPath | ConvertFrom-Json).version
if ($final -ne $original) { throw "Rollback left champion at version $final, expected $original" }
Write-Host "ROLLBACK_OK champion=$final"
exit 0
