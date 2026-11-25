"""Shared constants, the untouched raw loader, and the 60/20/20 split."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "seeds_dataset.txt"
HASH_PATH = ROOT / "data" / "raw" / "SHA256SUMS.txt"
RESULTS_DIR = ROOT / "results"

FEATURE_COLUMNS = [
    "area",
    "perimeter",
    "compactness",
    "length_of_kernel",
    "width_of_kernel",
    "asymmetry_coefficient",
    "length_of_kernel_groove",
]
TARGET_COLUMN = "target"
CLASS_MAP = {1: "Kama", 2: "Rosa", 3: "Canadian"}
LABELS = [1, 2, 3]
CLASS_NAMES = [CLASS_MAP[label] for label in LABELS]
EXPERIMENT_NAME = "lab4-seeds"
MODEL_NAME = "seeds-classifier"
RANDOM_STATE = 42
TRACKING_URI_DEFAULT = "http://127.0.0.1:5000"
MODEL_DESCRIPTION = (
    "Классификатор сортов пшеницы (UCI Seeds, вариант 21). "
    "Признаки: 7 геометрических измерений зерна. Классы: Kama, Rosa, Canadian."
)


def tracking_uri() -> str:
    return os.environ.get("MLFLOW_TRACKING_URI", TRACKING_URI_DEFAULT)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_raw_unchanged(path: Path, actual_hash: str) -> None:
    if not HASH_PATH.is_file():
        return
    recorded = HASH_PATH.read_text(encoding="ascii").split()[0].strip()
    if recorded != actual_hash:
        raise RuntimeError(
            "SHA-256 сырого файла не совпадает с data/raw/SHA256SUMS.txt. "
            "Файл data/raw/seeds_dataset.txt изменять нельзя."
        )


def load_seeds(path: Path | None = None) -> tuple[pd.DataFrame, str]:
    path = Path(path) if path else RAW_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"Нет файла данных: {path}. Скачайте его: python scripts/download_seeds.py"
        )
    digest = sha256_file(path)
    assert_raw_unchanged(path, digest)
    frame = pd.read_csv(path, sep=r"\s+", header=None, engine="python")
    if frame.shape[1] != 8:
        raise ValueError(f"Ожидалось 8 столбцов, получено {frame.shape[1]}")
    frame.columns = FEATURE_COLUMNS + [TARGET_COLUMN]
    frame[TARGET_COLUMN] = frame[TARGET_COLUMN].astype(int)
    unknown = sorted(set(frame[TARGET_COLUMN].tolist()) - set(LABELS))
    if unknown:
        raise ValueError(f"Неизвестные метки классов: {unknown}")
    if len(frame) != 210:
        raise ValueError(f"Ожидалось 210 объектов UCI Seeds, получено {len(frame)}")
    if frame[FEATURE_COLUMNS].isna().any().any():
        raise ValueError("В признаках есть пропуски")
    return frame, digest


def dataframe_profile(frame: pd.DataFrame, digest: str) -> dict[str, Any]:
    described = frame[FEATURE_COLUMNS].describe()
    describe = {
        stat: {feature: round(float(described.loc[stat, feature]), 6) for feature in FEATURE_COLUMNS}
        for stat in described.index
    }
    counts = frame[TARGET_COLUMN].value_counts().to_dict()
    return {
        "source": "UCI Machine Learning Repository, Seeds (id 236)",
        "sha256": digest,
        "n_rows": int(len(frame)),
        "n_features": len(FEATURE_COLUMNS),
        "features": list(FEATURE_COLUMNS),
        "class_counts": {CLASS_MAP[int(label)]: int(count) for label, count in sorted(counts.items())},
        "describe": describe,
    }


def split_seeds(frame: pd.DataFrame, random_state: int = RANDOM_STATE):
    """60/20/20: test_size=0.2, then test_size=0.25 of the remainder. Stratified."""
    target = frame[TARGET_COLUMN]
    indices = frame.index.to_numpy()
    idx_temp, idx_test = train_test_split(
        indices,
        test_size=0.2,
        random_state=random_state,
        stratify=target.loc[indices],
    )
    idx_train, idx_val = train_test_split(
        idx_temp,
        test_size=0.25,
        random_state=random_state,
        stratify=target.loc[idx_temp],
    )

    def take(index_values):
        part = frame.loc[list(index_values)]
        return part[FEATURE_COLUMNS].copy(), part[TARGET_COLUMN].copy()

    x_train, y_train = take(idx_train)
    x_val, y_val = take(idx_val)
    x_test, y_test = take(idx_test)

    def counts(series: pd.Series) -> dict[str, int]:
        counted = series.value_counts().reindex(LABELS, fill_value=0)
        return {str(int(label)): int(counted.loc[label]) for label in LABELS}

    info = {
        "random_state": random_state,
        "test_size_outer": 0.2,
        "test_size_inner": 0.25,
        "stratify": True,
        "fractions": {"train": 0.6, "val": 0.2, "test": 0.2},
        "n_train": int(len(idx_train)),
        "n_val": int(len(idx_val)),
        "n_test": int(len(idx_test)),
        "train_indices": [int(value) for value in idx_train],
        "val_indices": [int(value) for value in idx_val],
        "test_indices": [int(value) for value in idx_test],
        "class_counts": {
            "train": counts(y_train),
            "val": counts(y_val),
            "test": counts(y_test),
        },
    }
    return x_train, x_val, x_test, y_train, y_val, y_test, info


def classification_metrics(y_true, y_pred, prefix: str) -> dict[str, float]:
    y_true = [int(value) for value in y_true]
    y_pred = [int(value) for value in y_pred]
    metrics = {
        f"{prefix}_accuracy": float(accuracy_score(y_true, y_pred)),
        f"{prefix}_f1_macro": float(f1_score(y_true, y_pred, average="macro", labels=LABELS)),
        f"{prefix}_precision_macro": float(
            precision_score(y_true, y_pred, average="macro", labels=LABELS, zero_division=0)
        ),
        f"{prefix}_recall_macro": float(
            recall_score(y_true, y_pred, average="macro", labels=LABELS, zero_division=0)
        ),
    }
    per_class = f1_score(y_true, y_pred, average=None, labels=LABELS, zero_division=0)
    for label, value in zip(LABELS, per_class):
        metrics[f"{prefix}_f1_{CLASS_MAP[label]}"] = float(value)
    return metrics


def report_text(y_true, y_pred) -> str:
    return classification_report(
        y_true,
        y_pred,
        labels=LABELS,
        target_names=CLASS_NAMES,
        digits=4,
        zero_division=0,
    )


def confusion_numbers(y_true, y_pred) -> list[list[int]]:
    matrix = confusion_matrix(y_true, y_pred, labels=LABELS)
    return [[int(value) for value in row] for row in matrix]


def save_confusion_matrix(y_true, y_pred, path: Path, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import ConfusionMatrixDisplay

    matrix = confusion_matrix(y_true, y_pred, labels=LABELS)
    display = ConfusionMatrixDisplay(confusion_matrix=matrix, display_labels=CLASS_NAMES)
    figure, axis = plt.subplots(figsize=(5.6, 4.6))
    display.plot(ax=axis, cmap="Blues", colorbar=False)
    axis.set_title(title)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=140)
    plt.close(figure)


def configure_tracking(uri: str, experiment: str) -> str:
    os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")
    import mlflow

    mlflow.set_tracking_uri(uri)
    experiment_info = mlflow.set_experiment(experiment)
    return experiment_info.experiment_id
