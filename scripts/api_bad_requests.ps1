# Black-box HTTP checks. Bad bodies must return 422. One valid batch must return 200.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not $env:BASE_URL) { $BaseUrl = "http://127.0.0.1:8000" } else { $BaseUrl = $env:BASE_URL }
$Curl = Join-Path $env:SystemRoot "System32\curl.exe"
if (-not (Test-Path $Curl)) { $Curl = "curl" }
$OutDir = Join-Path $Root "results\bad_requests"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Invoke-Http([string]$Name, [string]$Method, [string]$Path, [string]$Body, [int]$Expected) {
  $out = Join-Path $OutDir "$Name.json"
  $tmp = Join-Path $env:TEMP "seeds_$Name.json"
  if ($Body -ne "") {
    [System.IO.File]::WriteAllText($tmp, $Body, (New-Object System.Text.UTF8Encoding $false))
    $code = & $Curl -sS -o $out -w "%{http_code}" -X $Method "$BaseUrl$Path" -H "Content-Type: application/json" --data-binary "@$tmp"
  } else {
    $code = & $Curl -sS -o $out -w "%{http_code}" -X $Method "$BaseUrl$Path"
  }
  $code = "$code".Trim()
  Write-Host "$Name -> $code (expected $Expected)"
  if ($code -ne "$Expected") { throw "$Name expected $Expected but got $code" }
}

Invoke-Http "health" "GET" "/health" "" 200
Invoke-Http "metadata" "GET" "/metadata" "" 200

$row = '{"area":15.26,"perimeter":14.84,"compactness":0.871,"length_of_kernel":5.763,"width_of_kernel":3.312,"asymmetry_coefficient":2.221,"length_of_kernel_groove":5.22}'
$missing = '{"area":15.26,"perimeter":14.84,"compactness":0.871,"length_of_kernel":5.763,"width_of_kernel":3.312,"asymmetry_coefficient":2.221}'
$extra = $row.TrimEnd('}') + ',"extra":1}'
Invoke-Http "empty_object" "POST" "/predict" "{}" 422
Invoke-Http "empty_instances" "POST" "/predict" '{"instances":[]}' 422
Invoke-Http "missing_field" "POST" "/predict" "{`"instances`":[$missing]}" 422
Invoke-Http "extra_field" "POST" "/predict" "{`"instances`":[$extra]}" 422
Invoke-Http "string_value" "POST" "/predict" "{`"instances`":[$($row.Replace('"area":15.26', '"area":"15.26"'))]}" 422
Invoke-Http "null_value" "POST" "/predict" "{`"instances`":[$($row.Replace('"area":15.26', '"area":null'))]}" 422
Invoke-Http "bool_value" "POST" "/predict" "{`"instances`":[$($row.Replace('"area":15.26', '"area":true'))]}" 422
Invoke-Http "non_finite" "POST" "/predict" "{`"instances`":[$($row.Replace('"area":15.26', '"area":1e309'))]}" 422
Invoke-Http "bare_array" "POST" "/predict" "[1,2,3,4,5,6,7]" 422
Invoke-Http "invalid_json" "POST" "/predict" "{" 422
Invoke-Http "valid_predict" "POST" "/predict" "{`"instances`":[$row]}" 200
Invoke-Http "get_predict" "GET" "/predict" "" 405
Write-Host "BAD_REQUESTS_OK"
exit 0
