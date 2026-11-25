#!/usr/bin/env bash
# Build and smoke-check the extra Compose stack (MLflow + API + gate).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export IMAGE_TAG="${IMAGE_TAG:-v1}"
export GIT_PYTHON_REFRESH=quiet

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

echo "Computing model hash..."
"$PYTHON" -m src.model_hash --model-dir "$ROOT/exported_model" --results-dir "$ROOT/results"

echo "Building and starting mlflow + seeds-api..."
docker compose -f compose.extra.yaml up -d --build mlflow seeds-api

echo "Waiting for API health..."
ready=0
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  echo "API did not become healthy"
  docker compose -f compose.extra.yaml logs --tail 80
  exit 1
fi

echo "Running api-check gate..."
docker compose -f compose.extra.yaml run --rm api-check

echo "Optional train worker:"
echo '  docker compose -f compose.extra.yaml --profile train run --rm train'
echo "EXTRA_STACK_OK"
