"""Point a registry alias at an already registered version. No training."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mlflow.tracking import MlflowClient

from src.common import MODEL_NAME, tracking_uri


def iter_versions(client: MlflowClient, model_name: str):
    found = None
    errors: list[str] = []
    for kwargs in (
        {"filter_string": f"name='{model_name}'"},
        {},
    ):
        try:
            found = client.search_model_versions(**kwargs) if kwargs else client.search_model_versions()
            break
        except TypeError as exc:
            errors.append(str(exc))
            found = None
    if found is None:
        raise RuntimeError("search_model_versions failed: " + "; ".join(errors))
    if hasattr(found, "to_list"):
        found = found.to_list()
    versions = list(found)
    return [version for version in versions if getattr(version, "name", model_name) == model_name]


def metric_of(client: MlflowClient, version) -> tuple[float, float]:
    run = client.get_run(version.run_id)
    return (
        float(run.data.metrics.get("val_f1_macro", -1.0)),
        float(run.data.metrics.get("val_accuracy", -1.0)),
    )


def choose_best(client: MlflowClient, versions) -> str:
    if not versions:
        raise RuntimeError("В реестре нет версий модели.")

    def sort_key(version):
        f1_value, accuracy = metric_of(client, version)
        algorithm = ""
        try:
            algorithm = client.get_run(version.run_id).data.params.get("algorithm", "")
        except Exception:  # noqa: BLE001
            algorithm = ""
        # Higher metric wins. On a full tie, prefer logistic regression, then the earlier version.
        return (f1_value, accuracy, 1 if algorithm == "lr" else 0, -int(version.version))

    winner = max(versions, key=sort_key)
    return str(winner.version)


def choose_other(client: MlflowClient, model_name: str, alias: str, versions) -> str:
    current = client.get_model_version_by_alias(model_name, alias)
    others = [version for version in versions if str(version.version) != str(current.version)]
    if not others:
        raise RuntimeError("Нет другой зарегистрированной версии для обновления алиаса.")
    return choose_best(client, others)


def append_history(entry: dict) -> None:
    path = ROOT / "results" / "alias_history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Назначить алиас зарегистрированной версии без переобучения.")
    parser.add_argument("--model-name", default=MODEL_NAME)
    parser.add_argument("--alias", default="champion")
    parser.add_argument("--version", help="Номер версии в реестре.")
    parser.add_argument("--best", action="store_true", help="Выбрать версию с максимальным val_f1_macro.")
    parser.add_argument(
        "--to-other",
        action="store_true",
        help="Перевести алиас на лучшую версию, которая сейчас не носит этот алиас.",
    )
    parser.add_argument("--note", default="")
    parser.add_argument("--tracking-uri", default=tracking_uri())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    modes = [bool(args.version), bool(args.best), bool(args.to_other)]
    if sum(modes) != 1:
        raise SystemExit("Укажите ровно один из флагов: --version, --best или --to-other.")
    client = MlflowClient(tracking_uri=args.tracking_uri)
    versions = iter_versions(client, args.model_name)
    if args.version:
        version = str(args.version)
    elif args.best:
        version = choose_best(client, versions)
    else:
        version = choose_other(client, args.model_name, args.alias, versions)
    known = {str(item.version) for item in versions}
    if version not in known:
        raise SystemExit(f"Версия {version} не найдена. Есть версии: {sorted(known, key=int)}")
    client.set_registered_model_alias(args.model_name, args.alias, version)
    confirmed = client.get_model_version_by_alias(args.model_name, args.alias)
    f1_value, accuracy = metric_of(client, confirmed)
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "model_name": args.model_name,
        "alias": args.alias,
        "version": str(confirmed.version),
        "run_id": confirmed.run_id,
        "val_f1_macro": f1_value,
        "val_accuracy": accuracy,
        "note": args.note,
    }
    append_history(entry)
    print("ALIAS_JSON " + json.dumps(entry, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
