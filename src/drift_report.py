"""Feature drift report: training distribution vs logged API request features."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.common import FEATURE_COLUMNS, load_seeds, split_seeds, write_json


def _stats(series: pd.Series) -> dict:
    values = series.dropna().astype(float)
    if len(values) == 0:
        return {"n": 0}
    return {
        "n": int(len(values)),
        "mean": round(float(values.mean()), 6),
        "std": round(float(values.std(ddof=0)), 6),
        "min": round(float(values.min()), 6),
        "p25": round(float(values.quantile(0.25)), 6),
        "median": round(float(values.median()), 6),
        "p75": round(float(values.quantile(0.75)), 6),
        "max": round(float(values.max()), 6),
    }


def population_stability_index(ref: pd.Series, cur: pd.Series, bins: int = 10) -> float:
    """PSI between two numeric series using reference quantiles."""
    ref = ref.dropna().astype(float)
    cur = cur.dropna().astype(float)
    if len(ref) < 2 or len(cur) < 1:
        return float("nan")
    quantiles = ref.quantile([i / bins for i in range(bins + 1)]).to_numpy()
    # Ensure strictly increasing edges
    edges = [float(quantiles[0]) - 1e-9]
    for value in quantiles[1:]:
        edge = float(value)
        if edge <= edges[-1]:
            edge = edges[-1] + 1e-9
        edges.append(edge)
    edges[-1] = edges[-1] + 1e-9
    ref_counts = pd.cut(ref, bins=edges, include_lowest=True).value_counts(sort=False)
    cur_counts = pd.cut(cur, bins=edges, include_lowest=True).value_counts(sort=False)
    ref_pct = (ref_counts / max(len(ref), 1)).clip(lower=1e-6)
    cur_pct = (cur_counts / max(len(cur), 1)).clip(lower=1e-6)
    psi = float(((cur_pct - ref_pct) * (cur_pct / ref_pct).map(math.log)).sum())
    return round(psi, 6)


def load_request_features(log_path: Path) -> pd.DataFrame:
    rows: list[dict] = []
    if not log_path.is_file():
        return pd.DataFrame(columns=FEATURE_COLUMNS)
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("path") != "/predict" or event.get("status_code") != 200:
                continue
            for instance in event.get("instances") or []:
                if not isinstance(instance, dict):
                    continue
                if all(column in instance for column in FEATURE_COLUMNS):
                    rows.append({column: float(instance[column]) for column in FEATURE_COLUMNS})
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS)


def build_report(train_frame: pd.DataFrame, request_frame: pd.DataFrame) -> dict:
    features = {}
    for column in FEATURE_COLUMNS:
        ref = train_frame[column]
        cur = request_frame[column] if column in request_frame.columns else pd.Series(dtype=float)
        psi = population_stability_index(ref, cur) if len(cur) else None
        mean_shift = None
        if len(cur) and float(ref.std(ddof=0)) > 0:
            mean_shift = round(abs(float(cur.mean()) - float(ref.mean())) / float(ref.std(ddof=0)), 6)
        level = "insufficient_requests"
        if psi is not None and not math.isnan(psi):
            if psi < 0.1:
                level = "stable"
            elif psi < 0.25:
                level = "moderate"
            else:
                level = "high"
        features[column] = {
            "train": _stats(ref),
            "requests": _stats(cur),
            "psi": psi,
            "abs_mean_shift_in_train_std": mean_shift,
            "drift_level": level,
        }
    high = [name for name, info in features.items() if info["drift_level"] == "high"]
    moderate = [name for name, info in features.items() if info["drift_level"] == "moderate"]
    return {
        "n_train": int(len(train_frame)),
        "n_request_rows": int(len(request_frame)),
        "features": features,
        "summary": {
            "high_drift_features": high,
            "moderate_drift_features": moderate,
            "stable_features": [
                name for name, info in features.items() if info["drift_level"] == "stable"
            ],
            "note": (
                "PSI < 0.1 — стабильно, 0.1–0.25 — умеренный дрейф, >= 0.25 — сильный дрейф. "
                "Сравнение: train split vs успешные /predict из журнала запросов."
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Отчёт о дрейфе признаков.")
    parser.add_argument("--data-path", default=str(ROOT / "data" / "raw" / "seeds_dataset.txt"))
    parser.add_argument("--request-log", default=str(ROOT / "logs" / "api_requests.jsonl"))
    parser.add_argument("--output", default=str(ROOT / "results" / "drift_report.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    frame, _digest = load_seeds(Path(args.data_path))
    x_train, _x_val, _x_test, _y_train, _y_val, _y_test, _info = split_seeds(frame)
    requests = load_request_features(Path(args.request_log))
    report = build_report(x_train, requests)
    report["request_log"] = str(Path(args.request_log).as_posix())
    write_json(Path(args.output), report)
    print("DRIFT_REPORT_JSON " + json.dumps({"summary": report["summary"], "n_request_rows": report["n_request_rows"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
