"""Score the exported champion on the held-out test split. Does not refit."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mlflow
import mlflow.sklearn

from src.common import (
    EXPERIMENT_NAME,
    FEATURE_COLUMNS,
    MODEL_NAME,
    classification_metrics,
    configure_tracking,
    confusion_numbers,
    load_seeds,
    report_text,
    save_confusion_matrix,
    split_seeds,
    tracking_uri,
    write_json,
)


def load_exported(path: Path):
    try:
        return mlflow.sklearn.load_model(str(path))
    except TypeError:
        return mlflow.sklearn.load_model(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test-метрики экспортированного champion.")
    parser.add_argument("--model-path", default=str(ROOT / "exported_model"))
    parser.add_argument("--output", default=str(ROOT / "results" / "test_metrics.json"))
    parser.add_argument("--experiment", default=EXPERIMENT_NAME)
    parser.add_argument("--tracking-uri", default=tracking_uri())
    parser.add_argument("--skip-mlflow", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model_path = Path(args.model_path)
    metadata_path = model_path / "lab_metadata.json"
    if not metadata_path.is_file():
        raise SystemExit(f"Нет экспортированной модели: {model_path}")
    metadata = json_load(metadata_path)
    model = load_exported(model_path)
    frame, digest = load_seeds()
    _x_train, _x_val, x_test, _y_train, _y_val, y_test, split_info = split_seeds(frame)
    predictions = model.predict(x_test)
    metrics = classification_metrics(y_test, predictions, "test")
    matrix = confusion_numbers(y_test, predictions)
    report = report_text(y_test, predictions)

    registry_match = None
    registry_error = None
    try:
        mlflow.set_tracking_uri(args.tracking_uri)
        registry_model = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")
        registry_pred = registry_model.predict(x_test)
        registry_match = bool(all(int(a) == int(b) for a, b in zip(predictions, registry_pred)))
    except Exception as exc:  # noqa: BLE001
        registry_error = str(exc)

    document = {
        "model_name": metadata.get("model_name"),
        "alias": metadata.get("alias"),
        "version": metadata.get("version"),
        "run_id": metadata.get("run_id"),
        "algorithm": metadata.get("algorithm"),
        "params": metadata.get("params"),
        "val_f1_macro": metadata.get("val_f1_macro"),
        "data_sha256": digest,
        "n_train": split_info["n_train"],
        "n_val": split_info["n_val"],
        "n_test": split_info["n_test"],
        "class_counts": split_info["class_counts"],
        "features": list(FEATURE_COLUMNS),
        "metrics": metrics,
        "confusion_matrix_labels": ["Kama", "Rosa", "Canadian"],
        "confusion_matrix": matrix,
        "classification_report": report,
        "registry_predictions_match": registry_match,
        "registry_error": registry_error,
    }
    output = Path(args.output)
    write_json(output, document)
    report_path = output.with_name("test_classification_report.txt")
    report_path.write_text(report, encoding="utf-8")
    save_confusion_matrix(
        y_test,
        predictions,
        output.with_name("test_confusion_matrix.png"),
        title=f"test  f1_macro={metrics['test_f1_macro']:.4f}",
    )
    print(report)
    print(
        "TEST_JSON "
        + json_dumps(
            {
                "version": document["version"],
                "run_id": document["run_id"],
                "algorithm": document["algorithm"],
                "test_f1_macro": metrics["test_f1_macro"],
                "test_accuracy": metrics["test_accuracy"],
                "test_precision_macro": metrics["test_precision_macro"],
                "test_recall_macro": metrics["test_recall_macro"],
                "registry_predictions_match": registry_match,
            }
        )
    )

    if not args.skip_mlflow:
        try:
            configure_tracking(args.tracking_uri, args.experiment)
            with mlflow.start_run(run_name="evaluate-champion"):
                mlflow.set_tag("stage", "evaluate")
                mlflow.set_tag("variant", "21")
                mlflow.set_tag("evaluated_version", str(metadata.get("version")))
                mlflow.set_tag("evaluated_run_id", str(metadata.get("run_id")))
                mlflow.log_param("algorithm", metadata.get("algorithm"))
                mlflow.log_param("model_version", metadata.get("version"))
                mlflow.log_metrics(metrics)
                mlflow.log_artifact(str(output))
                mlflow.log_artifact(str(report_path))
                mlflow.log_artifact(str(output.with_name("test_confusion_matrix.png")))
                mlflow.set_tag("mlflow_eval_logged", "true")
            document["mlflow_eval_logged"] = True
            write_json(output, document)
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: evaluate run was not logged to MLflow: {exc}")
            document["mlflow_eval_logged"] = False
            document["mlflow_eval_error"] = str(exc)
            write_json(output, document)
    return 0


def json_load(path: Path):
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def json_dumps(payload) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    raise SystemExit(main())
