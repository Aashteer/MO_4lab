#!/usr/bin/env bash
# Six exploration runs, then register the best LogisticRegression and the best KNN.
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

run() {
  echo "RUN $PY $*"
  "$PY" "$@"
}

run -m src.train --algorithm lr --C 0.1
run -m src.train --algorithm lr --C 1
run -m src.train --algorithm lr --C 10
run -m src.train --algorithm knn --n-neighbors 3
run -m src.train --algorithm knn --n-neighbors 5
run -m src.train --algorithm knn --n-neighbors 11
run -m src.registry_plan

"$PY" - "$PY" <<'PY'
import json, subprocess, sys
from pathlib import Path
py = sys.argv[1]
plan = json.loads(Path("results/register_plan.json").read_text(encoding="utf-8"))
for item in plan["candidates"]:
    if item["algorithm"] == "lr":
        cmd = [py, "-m", "src.train", "--algorithm", "lr", "--C", str(item["C"]), "--register"]
    else:
        cmd = [py, "-m", "src.train", "--algorithm", "knn", "--n-neighbors", str(int(item["n_neighbors"])), "--register"]
    print("RUN", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
PY

run -m src.registry_plan --dump "$ROOT/results/experiments.json"
echo "EXPERIMENTS_DONE"
