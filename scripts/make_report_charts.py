"""Generate comparison / EDA charts for the lab report (variant 21)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "screenshots"
RESULTS = ROOT / "results"
DATA = ROOT / "data" / "raw" / "seeds_dataset.txt"

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "#fafafa",
        "axes.grid": True,
        "grid.alpha": 0.35,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
    }
)

COLORS = {
    "lr-C-0.1": "#4C78A8",
    "lr-C-1": "#F58518",
    "lr-C-10": "#E45756",
    "knn-k-3": "#54A24B",
    "knn-k-5": "#B279A2",
    "knn-k-11": "#72B7B2",
}


def load_search_runs():
    exp = json.loads((RESULTS / "experiments.json").read_text(encoding="utf-8"))
    names = ["lr-C-0.1", "lr-C-1", "lr-C-10", "knn-k-3", "knn-k-5", "knn-k-11"]
    by_name = {r["run_name"]: r for r in exp["runs"]}
    return [by_name[n] for n in names]


def save(fig, name: str):
    path = SHOTS / name
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print("wrote", path.name)


def chart_val_f1_macro(runs):
    names = [r["run_name"] for r in runs]
    vals = [r["metrics"]["val_f1_macro"] for r in runs]
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    bars = ax.bar(names, vals, color=[COLORS[n] for n in names], edgecolor="black", linewidth=0.4)
    ax.set_ylim(0.85, 1.0)
    ax.set_ylabel("val_f1_macro")
    ax.set_title("Сравнение поисковых запусков по метрике выбора (val_f1_macro)")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.004, f"{v:.4f}", ha="center", va="bottom", fontsize=9)
    ax.axhline(max(vals), color="#54A24B", linestyle="--", linewidth=1, alpha=0.7, label="лучший = knn-k-3")
    ax.legend(loc="lower right")
    fig.tight_layout()
    save(fig, "G01_val_f1_macro.png")


def chart_train_vs_val(runs):
    names = [r["run_name"] for r in runs]
    train = [r["metrics"]["train_f1_macro"] for r in runs]
    val = [r["metrics"]["val_f1_macro"] for r in runs]
    x = np.arange(len(names))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    ax.bar(x - w / 2, train, w, label="train_f1_macro", color="#4C78A8")
    ax.bar(x + w / 2, val, w, label="val_f1_macro", color="#54A24B")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15)
    ax.set_ylim(0.85, 1.02)
    ax.set_ylabel("F1 macro")
    ax.set_title("Train vs Validation: контроль переобучения")
    ax.legend()
    fig.tight_layout()
    save(fig, "G02_train_vs_val.png")


def chart_per_class_val(runs):
    names = [r["run_name"] for r in runs]
    classes = ["Kama", "Rosa", "Canadian"]
    keys = ["val_f1_Kama", "val_f1_Rosa", "val_f1_Canadian"]
    x = np.arange(len(names))
    w = 0.25
    fig, ax = plt.subplots(figsize=(10, 4.6))
    palette = ["#E45756", "#F2CF5B", "#4C78A8"]
    for i, (cls, key, c) in enumerate(zip(classes, keys, palette)):
        vals = [r["metrics"][key] for r in runs]
        ax.bar(x + (i - 1) * w, vals, w, label=cls, color=c)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15)
    ax.set_ylim(0.75, 1.05)
    ax.set_ylabel("val F1")
    ax.set_title("F1 по классам на validation (Kama / Rosa / Canadian)")
    ax.legend(ncol=3)
    fig.tight_layout()
    save(fig, "G03_val_f1_per_class.png")


def chart_hyperparams(runs):
    lr = [r for r in runs if r["run_name"].startswith("lr-")]
    knn = [r for r in runs if r["run_name"].startswith("knn-")]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))

    c_vals = [float(r["params"]["C"]) for r in lr]
    lr_f1 = [r["metrics"]["val_f1_macro"] for r in lr]
    axes[0].plot(c_vals, lr_f1, "o-", color="#E45756", linewidth=2, markersize=8)
    for c, y, name in zip(c_vals, lr_f1, [r["run_name"] for r in lr]):
        axes[0].annotate(f"{y:.3f}", (c, y), textcoords="offset points", xytext=(0, 8), ha="center")
    axes[0].set_xscale("log")
    axes[0].set_xlabel("C (LogisticRegression)")
    axes[0].set_ylabel("val_f1_macro")
    axes[0].set_title("Зависимость LR от C")
    axes[0].set_ylim(0.86, 0.96)

    k_vals = [int(r["params"]["n_neighbors"]) for r in knn]
    knn_f1 = [r["metrics"]["val_f1_macro"] for r in knn]
    axes[1].plot(k_vals, knn_f1, "s-", color="#54A24B", linewidth=2, markersize=8)
    for k, y in zip(k_vals, knn_f1):
        axes[1].annotate(f"{y:.3f}", (k, y), textcoords="offset points", xytext=(0, 8), ha="center")
    axes[1].set_xlabel("n_neighbors (KNN)")
    axes[1].set_ylabel("val_f1_macro")
    axes[1].set_title("Зависимость KNN от k")
    axes[1].set_ylim(0.86, 0.98)

    fig.suptitle("Влияние гиперпараметров на метрику выбора", y=1.02)
    fig.tight_layout()
    save(fig, "G04_hyperparams.png")


def chart_test_metrics():
    tm = json.loads((RESULTS / "test_metrics.json").read_text(encoding="utf-8"))
    m = tm["metrics"]
    labels = [
        "accuracy",
        "f1_macro",
        "precision_macro",
        "recall_macro",
        "f1_Kama",
        "f1_Rosa",
        "f1_Canadian",
    ]
    keys = [
        "test_accuracy",
        "test_f1_macro",
        "test_precision_macro",
        "test_recall_macro",
        "test_f1_Kama",
        "test_f1_Rosa",
        "test_f1_Canadian",
    ]
    vals = [m[k] for k in keys]
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    bars = ax.bar(labels, vals, color="#4C78A8", edgecolor="black", linewidth=0.4)
    ax.set_ylim(0.7, 1.0)
    ax.set_ylabel("значение")
    ax.set_title("Итоговые test-метрики champion (KNN k=3, version 2)")
    ax.tick_params(axis="x", rotation=20)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)
    fig.tight_layout()
    save(fig, "G05_test_metrics.png")


def chart_confusion():
    tm = json.loads((RESULTS / "test_metrics.json").read_text(encoding="utf-8"))
    cm = np.array(tm["confusion_matrix"], dtype=float)
    labels = tm["confusion_matrix_labels"]
    fig, ax = plt.subplots(figsize=(5.2, 4.6))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels(labels)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Матрица ошибок champion на test")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center", color="black" if cm[i, j] < cm.max() / 2 else "white", fontsize=14)
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    save(fig, "G06_confusion_test.png")


def chart_class_balance_and_features():
    cols = [
        "area",
        "perimeter",
        "compactness",
        "length_of_kernel",
        "width_of_kernel",
        "asymmetry_coefficient",
        "length_of_kernel_groove",
        "class",
    ]
    df = pd.read_csv(DATA, sep=r"\s+", header=None, names=cols)
    map_cls = {1: "Kama", 2: "Rosa", 3: "Canadian"}
    df["variety"] = df["class"].map(map_cls)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
    counts = df["variety"].value_counts().reindex(["Kama", "Rosa", "Canadian"])
    axes[0].bar(counts.index, counts.values, color=["#E45756", "#F2CF5B", "#4C78A8"], edgecolor="black", linewidth=0.4)
    axes[0].set_ylim(0, 90)
    axes[0].set_title("Баланс классов (n=210)")
    axes[0].set_ylabel("число объектов")
    for i, v in enumerate(counts.values):
        axes[0].text(i, v + 2, str(v), ha="center")

    means = df.groupby("variety")[["area", "perimeter", "asymmetry_coefficient"]].mean().reindex(
        ["Kama", "Rosa", "Canadian"]
    )
    means.plot(kind="bar", ax=axes[1], rot=0, color=["#4C78A8", "#54A24B", "#E45756"])
    axes[1].set_title("Средние значения ключевых признаков по сортам")
    axes[1].set_xlabel("")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    save(fig, "G07_eda_balance_features.png")


def chart_pca_scatter():
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    cols = [
        "area",
        "perimeter",
        "compactness",
        "length_of_kernel",
        "width_of_kernel",
        "asymmetry_coefficient",
        "length_of_kernel_groove",
        "class",
    ]
    df = pd.read_csv(DATA, sep=r"\s+", header=None, names=cols)
    X = StandardScaler().fit_transform(df[cols[:-1]].values)
    xy = PCA(n_components=2, random_state=42).fit_transform(X)
    map_cls = {1: "Kama", 2: "Rosa", 3: "Canadian"}
    colors = {1: "#E45756", 2: "#F2CF5B", 3: "#4C78A8"}
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    for c in (1, 2, 3):
        mask = df["class"] == c
        ax.scatter(xy[mask, 0], xy[mask, 1], c=colors[c], label=map_cls[c], s=36, alpha=0.85, edgecolors="k", linewidths=0.25)
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title("PCA проекция Seeds (7 признаков → 2 компоненты)")
    ax.legend()
    fig.tight_layout()
    save(fig, "G08_pca_scatter.png")


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    runs = load_search_runs()
    chart_val_f1_macro(runs)
    chart_train_vs_val(runs)
    chart_per_class_val(runs)
    chart_hyperparams(runs)
    chart_test_metrics()
    chart_confusion()
    chart_class_balance_and_features()
    chart_pca_scatter()


if __name__ == "__main__":
    main()
