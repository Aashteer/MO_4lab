# Start the local MLflow tracking server (SQLite + artifact directory).
# ASCII only so Windows PowerShell 5.1 reads the file without a BOM.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:GIT_PYTHON_REFRESH = "quiet"
$env:MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"

$VenvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $VenvPy) { $Python = $VenvPy } else { $Python = "python" }

New-Item -ItemType Directory -Force -Path @(
  (Join-Path $Root "logs"),
  (Join-Path $Root "mlartifacts"),
  (Join-Path $Root "results")
) | Out-Null

function Test-MLflowUp {
  & $Python -c "import sys,urllib.request
try:
    urllib.request.urlopen('http://127.0.0.1:5000/', timeout=2)
except Exception:
    sys.exit(1)
sys.exit(0)"
  return ($LASTEXITCODE -eq 0)
}

if (Test-MLflowUp) {
  Write-Host "MLflow already responds on http://127.0.0.1:5000"
  exit 0
}

$OutLog = Join-Path $Root "logs\mlflow.out.log"
$ErrLog = Join-Path $Root "logs\mlflow.err.log"
$Proc = Start-Process -FilePath $Python -WorkingDirectory $Root -WindowStyle Hidden -PassThru `
  -RedirectStandardOutput $OutLog -RedirectStandardError $ErrLog -ArgumentList @(
    "-m", "mlflow", "server",
    "--backend-store-uri", "sqlite:///mlflow.db",
    "--default-artifact-root", "./mlartifacts",
    "--workers", "1",
    "--host", "127.0.0.1",
    "--port", "5000"
  )
Set-Content -Path (Join-Path $Root "logs\mlflow.pid") -Value $Proc.Id -Encoding ascii
Write-Host "Starting MLflow pid=$($Proc.Id)"

$Ready = $false
for ($i = 0; $i -lt 90; $i++) {
  Start-Sleep -Seconds 1
  if (Test-MLflowUp) { $Ready = $true; break }
  if ($Proc.HasExited) { break }
}
if (-not $Ready) {
  Write-Host "MLflow did not start. stderr tail:"
  if (Test-Path $ErrLog) { Get-Content $ErrLog -Tail 80 }
  if (Test-Path $OutLog) { Get-Content $OutLog -Tail 40 }
  exit 1
}
Write-Host "MLflow is up: http://127.0.0.1:5000"
exit 0
