# Six exploration runs, then register the best LogisticRegression and the best KNN.
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

Invoke-Step @("-m", "src.train", "--algorithm", "lr", "--C", "0.1")
Invoke-Step @("-m", "src.train", "--algorithm", "lr", "--C", "1")
Invoke-Step @("-m", "src.train", "--algorithm", "lr", "--C", "10")
Invoke-Step @("-m", "src.train", "--algorithm", "knn", "--n-neighbors", "3")
Invoke-Step @("-m", "src.train", "--algorithm", "knn", "--n-neighbors", "5")
Invoke-Step @("-m", "src.train", "--algorithm", "knn", "--n-neighbors", "11")
Invoke-Step @("-m", "src.registry_plan")

$plan = Get-Content -Raw -Encoding UTF8 (Join-Path $Root "results\register_plan.json") | ConvertFrom-Json
foreach ($item in $plan.candidates) {
  if ($item.algorithm -eq "lr") {
    Invoke-Step @("-m", "src.train", "--algorithm", "lr", "--C", "$($item.C)", "--register")
  } else {
    Invoke-Step @("-m", "src.train", "--algorithm", "knn", "--n-neighbors", "$([int]$item.n_neighbors)", "--register")
  }
}
Invoke-Step @("-m", "src.registry_plan", "--dump", (Join-Path $Root "results\experiments.json"))
Write-Host "EXPERIMENTS_DONE"
exit 0
