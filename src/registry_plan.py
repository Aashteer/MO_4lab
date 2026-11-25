"""Choose the best logged run of each family and dump the experiment."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mlflow.tracking import MlflowClient

from src.common import EXPERIMENT_NAME, MODEL_NAME, tracking_uri, write_json


def search_runs(client: MlflowClient, experiment_id: str):
    try:
        found = client.search_runs(
            experiment_ids=[experiment_id],
            max_results=500,
            order_by=["attributes.start_time ASC"],
        )
    except Exception:
        found = client.search_runs(experiment_ids=[experiment_id], max_results=500)
    if hasattr(found, "to_list"):
        found = found.to_list()
    return sorted(list(found), key=lambda run: run.info.start_time or 0)


def family_best(runs, family: str):
    subset = [
        run
        for run in runs
        if run.data.tags.get("stage") == "train" and run.data.params.get("algorithm") == family
    ]
    if not subset:
        raise RuntimeError(f"Нет прогонов stage=train для алгоритма {family}.")

    def score(run):
        return (
            float(run.data.metrics.get("val_f1_macro", -1.0)),
            float(run.data.metrics.get("val_accuracy", -1.0)),
            -(run.info.start_time or 0),
        )

    return max(subset, key=score)


def candidate(run) -> dict:
    algorithm = run.data.params.get("algorithm")
    item = {
        "algorithm": algorithm,
        "source_run_id": run.info.run_id,
        "run_name": run.info.run_name,
        "val_f1_macro": float(run.data.metrics.get("val_f1_macro", -1.0)),
        "val_accuracy": float(run.data.metrics.get("val_accuracy", -1.0)),
    }
    if algorithm == "lr":
        item["C"] = float(run.data.params["C"])
    else:
        item["n_neighbors"] = int(float(run.data.params["n_neighbors"]))
    return item


def aliases_of(registered) -> dict[str, str]:
    raw = getattr(registered, "aliases", None)
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return {str(key): str(value) for key, value in raw.items()}
    result = {}
    for item in raw:
        alias = getattr(item, "alias", None) or (item.get("alias") if isinstance(item, dict) else None)
        version = getattr(item, "version", None) or (item.get("version") if isinstance(item, dict) else None)
        if alias is not None:
            result[str(alias)] = str(version)
    return result


def iter_versions(client: MlflowClient, model_name: str):
    try:
        found = client.search_model_versions(filter_string=f"name='{model_name}'")
    except TypeError:
        found = client.search_model_versions()
    if hasattr(found, "to_list"):
        found = found.to_list()
    return [version for version in list(found) if getattr(version, "name", model_name) == model_name]


def iso_ms(value):
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000).isoformat(timespec="seconds")


def dump_runs(client: MlflowClient, path: Path) -> dict:
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        raise RuntimeError(f"Эксперимент {EXPERIMENT_NAME} не найден.")
    runs = search_runs(client, experiment.experiment_id)
    run_rows = []
    for run in runs:
        run_rows.append(
            {
                "run_id": run.info.run_id,
                "run_name": run.info.run_name,
                "status": run.info.status,
                "start_time": iso_ms(run.info.start_time),
                "end_time": iso_ms(run.info.end_time),
                "params": dict(run.data.params),
                "metrics": {key: float(value) for key, value in run.data.metrics.items()},
                "tags": {
                    key: value
                    for key, value in run.data.tags.items()
                    if key in {"stage", "variant", "dataset", "algorithm", "data_sha256", "registered_version", "python_version"}
                    or key.startswith("evaluated")
                },
            }
        )
    registry = None
    try:
        registered = client.get_registered_model(MODEL_NAME)
        versions = []
        for version in iter_versions(client, MODEL_NAME):
            run = client.get_run(version.run_id)
            versions.append(
                {
                    "version": str(version.version),
                    "run_id": version.run_id,
                    "algorithm": run.data.params.get("algorithm"),
                    "params": {
                        key: run.data.params.get(key)
                        for key in ("C", "n_neighbors")
                        if key in run.data.params
                    },
                    "val_f1_macro": run.data.metrics.get("val_f1_macro"),
                    "val_accuracy": run.data.metrics.get("val_accuracy"),
                    "description": getattr(version, "description", None),
                }
            )
        versions.sort(key=lambda item: int(item["version"]))
        registry = {
            "name": MODEL_NAME,
            "description": getattr(registered, "description", None),
            "aliases": aliases_of(registered),
            "versions": versions,
        }
    except Exception as exc:  # noqa: BLE001
        registry = {"error": str(exc)}
    document = {
        "experiment": EXPERIMENT_NAME,
        "experiment_id": experiment.experiment_id,
        "runs": run_rows,
        "registry": registry,
    }
    write_json(path, document)
    return document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="План регистрации и снимок эксперимента.")
    parser.add_argument("--tracking-uri", default=tracking_uri())
    parser.add_argument("--output", default=str(ROOT / "results" / "register_plan.json"))
    parser.add_argument("--dump", default="", help="Если указан путь, только записать снимок прогонов.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = MlflowClient(tracking_uri=args.tracking_uri)
    if args.dump:
        document = dump_runs(client, Path(args.dump))
        print(f"DUMPED runs={len(document['runs'])} path={args.dump}")
        return 0
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        raise SystemExit(f"Эксперимент {EXPERIMENT_NAME} не найден.")
    runs = search_runs(client, experiment.experiment_id)
    plan = {"candidates": [candidate(family_best(runs, "lr")), candidate(family_best(runs, "knn"))]}
    write_json(Path(args.output), plan)
    print("PLAN_JSON " + __import__("json").dumps(plan, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
