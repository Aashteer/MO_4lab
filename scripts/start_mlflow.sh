#!/usr/bin/env bash
# Start the local MLflow tracking server (SQLite + artifact directory).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export GIT_PYTHON_REFRESH=quiet
export MLFLOW_TRACKING_URI="http://127.0.0.1:5000"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="${PYTHON:-python3}"
fi
mkdir -p logs mlartifacts results

if "$PY" - <<'PY'
import sys, urllib.request
try:
    urllib.request.urlopen("http://127.0.0.1:5000/", timeout=2)
except Exception:
    sys.exit(1)
sys.exit(0)
PY
then
  echo "MLflow already responds on http://127.0.0.1:5000"
  exit 0
fi

nohup "$PY" -m mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root ./mlartifacts \
  --workers 1 \
  --host 127.0.0.1 \
  --port 5000 \
  > logs/mlflow.out.log 2>&1 &
echo $! > logs/mlflow.pid
echo "Starting MLflow pid=$(cat logs/mlflow.pid)"

for _ in $(seq 1 90); do
  if "$PY" - <<'PY'
import sys, urllib.request
try:
    urllib.request.urlopen("http://127.0.0.1:5000/", timeout=2)
except Exception:
    sys.exit(1)
sys.exit(0)
PY
  then
    echo "MLflow is up: http://127.0.0.1:5000"
    exit 0
  fi
  sleep 1
done
echo "MLflow did not start. Log tail:" >&2
tail -n 80 logs/mlflow.out.log >&2 || true
exit 1
