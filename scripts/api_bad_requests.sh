#!/usr/bin/env bash
# Black-box HTTP checks. Bad bodies must return 422. One valid batch must return 200.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
OUT="$ROOT/results/bad_requests"
mkdir -p "$OUT"

hit() {
  local name="$1" method="$2" path="$3" body="$4" expected="$5"
  local out="$OUT/$name.json"
  local code
  if [[ -n "$body" ]]; then
    code="$(curl -sS -o "$out" -w "%{http_code}" -X "$method" "$BASE_URL$path" -H "Content-Type: application/json" --data "$body")"
  else
    code="$(curl -sS -o "$out" -w "%{http_code}" -X "$method" "$BASE_URL$path")"
  fi
  echo "$name -> $code (expected $expected)"
  if [[ "$code" != "$expected" ]]; then
    echo "$name expected $expected but got $code" >&2
    exit 1
  fi
}

ROW='{"area":15.26,"perimeter":14.84,"compactness":0.871,"length_of_kernel":5.763,"width_of_kernel":3.312,"asymmetry_coefficient":2.221,"length_of_kernel_groove":5.22}'
MISSING='{"area":15.26,"perimeter":14.84,"compactness":0.871,"length_of_kernel":5.763,"width_of_kernel":3.312,"asymmetry_coefficient":2.221}'
EXTRA="${ROW%\},\"extra\":1}"
hit health GET /health "" 200
hit metadata GET /metadata "" 200
hit empty_object POST /predict "{}" 422
hit empty_instances POST /predict '{"instances":[]}' 422
hit missing_field POST /predict "{\"instances\":[$MISSING]}" 422
hit extra_field POST /predict "{\"instances\":[$EXTRA]}" 422
hit string_value POST /predict "{\"instances\":[${ROW/\"area\":15.26/\"area\":\"15.26\"}]}" 422
hit null_value POST /predict "{\"instances\":[${ROW/\"area\":15.26/\"area\":null}]}" 422
hit bool_value POST /predict "{\"instances\":[${ROW/\"area\":15.26/\"area\":true}]}" 422
hit non_finite POST /predict "{\"instances\":[${ROW/\"area\":15.26/\"area\":1e309}]}" 422
hit bare_array POST /predict "[1,2,3,4,5,6,7]" 422
hit invalid_json POST /predict "{" 422
hit valid_predict POST /predict "{\"instances\":[$ROW]}" 200
hit get_predict GET /predict "" 405
echo "BAD_REQUESTS_OK"
