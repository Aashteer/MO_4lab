#!/usr/bin/env bash
# Move the champion alias to the other registered version, export it aside,
# then move the alias back. No training commands are invoked.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export GIT_PYTHON_REFRESH=quiet
export MLFLOW_TRACKING_URI="${MLFLOW_TRACKING_URI:-http://127.0.0.1:5000}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="${PYTHON:-python3}"
fi
INFO="$ROOT/results/export_info.json"
if [[ ! -f "$INFO" ]]; then
  echo "results/export_info.json is missing. Export the champion first." >&2
  exit 1
fi
ORIGINAL="$("$PY" -c "import json; print(json.load(open('results/export_info.json', encoding='utf-8'))['version'])")"
echo "ORIGINAL_CHAMPION $ORIGINAL"
"$PY" -m src.promote --to-other --alias champion --note update-without-retrain
"$PY" -m src.export_model --output "$ROOT/results/exported_challenger" --no-samples
"$PY" -m src.promote --version "$ORIGINAL" --alias champion --note rollback-without-retrain
"$PY" -m src.export_model
FINAL="$("$PY" -c "import json; print(json.load(open('results/export_info.json', encoding='utf-8'))['version'])")"
if [[ "$FINAL" != "$ORIGINAL" ]]; then
  echo "Rollback left champion at version $FINAL, expected $ORIGINAL" >&2
  exit 1
fi
echo "ROLLBACK_OK champion=$FINAL"
