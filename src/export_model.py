"""Resolve the alias once and write a self-contained model directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.tracking import MlflowClient

from src.common import (
    CLASS_MAP,
    FEATURE_COLUMNS,
    MODEL_NAME,
    load_seeds,
    split_seeds,
    tracking_uri,
    write_json,
)
from src.model_hash import write_hash_files


def save_model(model, output: Path) -> None:
    try:
        mlflow.sklearn.save_model(sk_model=model, path=str(output))
    except TypeError:
        mlflow.sklearn.save_model(model, str(output))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Экспорт модели по алиасу реестра.")
    parser.add_argument("--model-name", default=MODEL_NAME)
    parser.add_argument("--alias", default="champion")
    parser.add_argument("--output", default=str(ROOT / "exported_model"))
    parser.add_argument("--sample-size", type=int, default=3)
    parser.add_argument("--no-samples", action="store_true")
    parser.add_argument("--info-out", default="")
    parser.add_argument("--tracking-uri", default=tracking_uri())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = MlflowClient(tracking_uri=args.tracking_uri)
    mlflow.set_tracking_uri(args.tracking_uri)
    version = client.get_model_version_by_alias(args.model_name, args.alias)
    model_uri = f"models:/{args.model_name}@{args.alias}"
    model = mlflow.sklearn.load_model(model_uri)
    run = client.get_run(version.run_id)
    output = Path(args.output)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    save_model(model, output)

    metadata = {
        "model_name": args.model_name,
        "alias": args.alias,
        "version": str(version.version),
        "run_id": version.run_id,
        "model_uri": model_uri,
        "algorithm": run.data.params.get("algorithm"),
        "params": {
            key: run.data.params.get(key)
            for key in ("C", "n_neighbors", "scaler", "solver", "weights")
            if key in run.data.params
        },
        "val_f1_macro": run.data.metrics.get("val_f1_macro"),
        "val_accuracy": run.data.metrics.get("val_accuracy"),
        "features": list(FEATURE_COLUMNS),
        "class_names": [CLASS_MAP[label] for label in (1, 2, 3)],
        "class_map": {str(label): name for label, name in CLASS_MAP.items()},
        "exported_at": datetime.now().isoformat(timespec="seconds"),
    }
    write_json(output / "lab_metadata.json", metadata)
    hash_record = write_hash_files(output, ROOT / "results")
    metadata["model_sha256"] = hash_record["sha256"]
    write_json(output / "lab_metadata.json", metadata)

    if not args.no_samples:
        frame, _digest = load_seeds()
        _x_train, _x_val, x_test, _y_train, _y_val, _y_test, _info = split_seeds(frame)
        sample_size = min(args.sample_size, len(x_test))
        instances = []
        predictions: list[int] = []
        for position in range(sample_size):
            payload = {column: float(x_test.iloc[position][column]) for column in FEATURE_COLUMNS}
            roundtrip = json.loads(json.dumps(payload))
            instances.append(roundtrip)
            matrix = pd.DataFrame([[roundtrip[column] for column in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
            predictions.append(int(model.predict(matrix)[0]))
        sample_document = {"instances": instances}
        expected_document = predictions
        write_json(ROOT / "sample_request.json", sample_document)
        write_json(ROOT / "expected_predictions.json", expected_document)
        write_json(ROOT / "results" / "sample_request.json", sample_document)
        write_json(ROOT / "results" / "expected_predictions.json", expected_document)

    if args.info_out:
        info_path = Path(args.info_out)
    elif args.no_samples:
        info_path = ROOT / "results" / "challenger_export_info.json"
    else:
        info_path = ROOT / "results" / "export_info.json"
    write_json(info_path, metadata)
    print("EXPORT_JSON " + json.dumps(metadata, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
