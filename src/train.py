"""Train LogisticRegression or KNN on UCI Seeds and log the run to MLflow.

Selection metric for later promotion is val_f1_macro. The held-out test split
is not scored here, so model choice cannot leak test labels.
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import platform
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.common import (
    CLASS_NAMES,
    EXPERIMENT_NAME,
    FEATURE_COLUMNS,
    MODEL_DESCRIPTION,
    MODEL_NAME,
    RANDOM_STATE,
    classification_metrics,
    configure_tracking,
    confusion_numbers,
    dataframe_profile,
    load_seeds,
    report_text,
    save_confusion_matrix,
    split_seeds,
    tracking_uri,
    write_json,
)


def build_pipeline(algorithm: str, c_value: float, n_neighbors: int) -> Pipeline:
    if algorithm == "lr":
        estimator = LogisticRegression(
            C=c_value,
            solver="lbfgs",
            max_iter=1000,
            random_state=RANDOM_STATE,
        )
    elif algorithm == "knn":
        estimator = KNeighborsClassifier(n_neighbors=n_neighbors, n_jobs=1)
    else:
        raise ValueError(f"Неизвестный алгоритм: {algorithm}")
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", estimator),
        ]
    )


def log_sklearn_model(pipeline: Pipeline, x_example, y_example):
    signature = infer_signature(x_example, y_example)
    parameters = inspect.signature(mlflow.sklearn.log_model).parameters
    base = {
        "sk_model": pipeline,
        "signature": signature,
        "input_example": x_example.iloc[:5],
    }
    if "name" in parameters and "artifact_path" not in parameters:
        attempts = [{"name": "model"}]
    elif "artifact_path" in parameters and "name" not in parameters:
        attempts = [{"artifact_path": "model"}]
    elif "name" in parameters and "artifact_path" in parameters:
        attempts = [{"name": "model"}, {"artifact_path": "model"}]
    else:
        raise RuntimeError("mlflow.sklearn.log_model: нет ни name, ни artifact_path")
    last_error: Exception | None = None
    for extra in attempts:
        try:
            return mlflow.sklearn.log_model(**base, **extra)
        except TypeError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def save_lr_coefficients(pipeline: Pipeline, directory: Path) -> None:
    estimator = pipeline.named_steps["clf"]
    coefficients = estimator.coef_
    intercept = estimator.intercept_
    csv_path = directory / "lr_coefficients.csv"
    lines = ["class," + ",".join(FEATURE_COLUMNS) + ",intercept"]
    for index, class_name in enumerate(CLASS_NAMES):
        values = [f"{float(value):.6f}" for value in coefficients[index]]
        lines.append(class_name + "," + ",".join(values) + f",{float(intercept[index]):.6f}")
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    figure, axis = plt.subplots(figsize=(10.2, 3.8))
    image = axis.imshow(coefficients, cmap="coolwarm", aspect="auto")
    axis.set_xticks(range(len(FEATURE_COLUMNS)), FEATURE_COLUMNS, rotation=30, ha="right")
    axis.set_yticks(range(len(CLASS_NAMES)), CLASS_NAMES)
    for row in range(coefficients.shape[0]):
        for column in range(coefficients.shape[1]):
            axis.text(column, row, f"{coefficients[row, column]:.2f}", ha="center", va="center", fontsize=8)
    axis.set_title("LogisticRegression coefficients in StandardScaler space")
    figure.colorbar(image, ax=axis, fraction=0.046)
    figure.tight_layout()
    figure.savefig(directory / "lr_coefficients.png", dpi=140)
    plt.close(figure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Обучение классификатора сортов пшеницы (UCI Seeds).")
    parser.add_argument("--algorithm", choices=["lr", "knn"], required=True)
    parser.add_argument("--C", type=float, default=1.0, dest="C")
    parser.add_argument("--n-neighbors", type=int, default=5)
    parser.add_argument("--register", action="store_true", help="Зарегистрировать модель как seeds-classifier.")
    parser.add_argument("--data-path", default=str(ROOT / "data" / "raw" / "seeds_dataset.txt"))
    parser.add_argument("--experiment", default=EXPERIMENT_NAME)
    parser.add_argument("--model-name", default=MODEL_NAME)
    parser.add_argument("--random-state", type=int, default=RANDOM_STATE)
    parser.add_argument("--tracking-uri", default=tracking_uri())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.algorithm == "knn" and args.n_neighbors < 1:
        raise SystemExit("--n-neighbors должен быть >= 1")
    if args.algorithm == "lr" and args.C <= 0:
        raise SystemExit("--C должен быть > 0")

    frame, digest = load_seeds(Path(args.data_path))
    profile = dataframe_profile(frame, digest)
    x_train, x_val, _x_test, y_train, y_val, _y_test, split_info = split_seeds(
        frame, random_state=args.random_state
    )
    pipeline = build_pipeline(args.algorithm, args.C, args.n_neighbors)
    pipeline.fit(x_train, y_train)
    train_pred = pipeline.predict(x_train)
    val_pred = pipeline.predict(x_val)
    train_metrics = classification_metrics(y_train, train_pred, "train")
    val_metrics = classification_metrics(y_val, val_pred, "val")

    if args.algorithm == "lr":
        run_name = f"lr-C-{args.C:g}"
    else:
        run_name = f"knn-k-{args.n_neighbors}"
    if args.register:
        run_name += "-register"

    configure_tracking(args.tracking_uri, args.experiment)
    try:
        client = MlflowClient(tracking_uri=args.tracking_uri)
        experiment = client.get_experiment_by_name(args.experiment)
        if experiment is not None:
            client.set_experiment_tag(experiment.experiment_id, "variant", "21")
            client.set_experiment_tag(experiment.experiment_id, "dataset", "uci-seeds")
    except Exception as exc:  # noqa: BLE001 - tagging must not block training
        print(f"WARNING: experiment tag was not set: {exc}")

    registered_version = None
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_param("algorithm", args.algorithm)
        mlflow.log_param("scaler", "StandardScaler")
        mlflow.log_param("random_state", args.random_state)
        mlflow.log_param("split", "60/20/20")
        mlflow.log_param("stratify", True)
        mlflow.log_param("selection_metric", "val_f1_macro")
        mlflow.log_param("sklearn_version", __import__("sklearn").__version__)
        mlflow.log_param("mlflow_version", mlflow.__version__)
        if args.algorithm == "lr":
            mlflow.log_param("C", args.C)
            mlflow.log_param("solver", "lbfgs")
            mlflow.log_param("max_iter", 1000)
        else:
            mlflow.log_param("n_neighbors", args.n_neighbors)
            mlflow.log_param("weights", "uniform")
        mlflow.set_tag("variant", "21")
        mlflow.set_tag("dataset", "uci-seeds")
        mlflow.set_tag("algorithm", args.algorithm)
        mlflow.set_tag("stage", "register" if args.register else "train")
        mlflow.set_tag("data_sha256", digest)
        mlflow.set_tag("python_version", platform.python_version())
        mlflow.set_tag("platform", platform.platform())
        mlflow.log_metrics(train_metrics)
        mlflow.log_metrics(val_metrics)

        with tempfile.TemporaryDirectory() as temp_name:
            directory = Path(temp_name)
            write_json(directory / "metrics.json", {**train_metrics, **val_metrics})
            write_json(
                directory / "params.json",
                {
                    "algorithm": args.algorithm,
                    "C": args.C if args.algorithm == "lr" else None,
                    "n_neighbors": args.n_neighbors if args.algorithm == "knn" else None,
                    "random_state": args.random_state,
                },
            )
            write_json(directory / "split.json", split_info)
            write_json(directory / "data_profile.json", profile)
            write_json(directory / "confusion_matrix_val.json", confusion_numbers(y_val, val_pred))
            (directory / "classification_report_val.txt").write_text(
                report_text(y_val, val_pred), encoding="utf-8"
            )
            save_confusion_matrix(
                y_val,
                val_pred,
                directory / "confusion_matrix_val.png",
                title=f"{run_name}  val_f1_macro={val_metrics['val_f1_macro']:.4f}",
            )
            if args.algorithm == "lr":
                save_lr_coefficients(pipeline, directory)
                n_iter = getattr(pipeline.named_steps["clf"], "n_iter_", None)
                if n_iter is not None:
                    if hasattr(n_iter, "__iter__"):
                        mlflow.log_param("n_iter_max", int(max(int(value) for value in n_iter)))
                    else:
                        mlflow.log_param("n_iter_max", int(n_iter))
            for artifact in directory.iterdir():
                mlflow.log_artifact(str(artifact))

        signature_pred = pipeline.predict(x_train)
        logged = log_sklearn_model(pipeline, x_train, signature_pred)
        model_uri = getattr(logged, "model_uri", None) or f"runs:/{run.info.run_id}/model"
        mlflow.set_tag("model_uri", model_uri)

        if args.register:
            registered = mlflow.register_model(model_uri, args.model_name)
            registered_version = str(registered.version)
            registry = MlflowClient(tracking_uri=args.tracking_uri)
            try:
                registry.update_registered_model(args.model_name, description=MODEL_DESCRIPTION)
            except Exception as exc:  # noqa: BLE001
                print(f"WARNING: registry description was not updated: {exc}")
            try:
                registry.update_model_version(
                    args.model_name,
                    registered_version,
                    description=(
                        f"{args.algorithm} val_f1_macro={val_metrics['val_f1_macro']:.6f} "
                        f"run={run.info.run_id}"
                    ),
                )
                registry.set_model_version_tag(args.model_name, registered_version, "algorithm", args.algorithm)
                registry.set_model_version_tag(
                    args.model_name,
                    registered_version,
                    "val_f1_macro",
                    f"{val_metrics['val_f1_macro']:.6f}",
                )
                registry.set_model_version_tag(args.model_name, registered_version, "variant", "21")
                registry.set_model_version_tag(args.model_name, registered_version, "dataset", "uci-seeds")
            except Exception as exc:  # noqa: BLE001
                print(f"WARNING: version tags were not set: {exc}")
            mlflow.set_tag("registered_version", registered_version)

        summary = {
            "run_id": run.info.run_id,
            "run_name": run_name,
            "algorithm": args.algorithm,
            "C": args.C if args.algorithm == "lr" else None,
            "n_neighbors": args.n_neighbors if args.algorithm == "knn" else None,
            "val_f1_macro": val_metrics["val_f1_macro"],
            "val_accuracy": val_metrics["val_accuracy"],
            "train_f1_macro": train_metrics["train_f1_macro"],
            "registered_version": registered_version,
            "model_uri": model_uri,
        }
        print("RESULT_JSON " + json.dumps(summary, ensure_ascii=False))
        log_path = ROOT / "results" / "train_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
