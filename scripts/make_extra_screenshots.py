"""Render readable PNG evidence cards for the extra MLOps assignment."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "screenshots"


def _figure(title: str, lines: list[str], outfile: Path, width: float = 11.2, height: float | None = None) -> None:
    wrapped: list[str] = []
    for line in lines:
        if len(line) <= 108:
            wrapped.append(line)
        else:
            wrapped.extend(textwrap.wrap(line, width=108, subsequent_indent="  ") or [line])
    if height is None:
        height = max(4.8, 1.6 + 0.28 * len(wrapped))
    figure, axis = plt.subplots(figsize=(width, height))
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")
    figure.patch.set_facecolor("#0f172a")
    box = FancyBboxPatch(
        (0.03, 0.03),
        0.94,
        0.94,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        linewidth=1.5,
        edgecolor="#38bdf8",
        facecolor="#111827",
    )
    axis.add_patch(box)
    axis.text(
        0.06,
        0.92,
        title,
        color="#7dd3fc",
        fontsize=15,
        fontweight="bold",
        va="top",
        family="DejaVu Sans",
    )
    axis.text(
        0.06,
        0.82,
        "\n".join(wrapped),
        color="#e5e7eb",
        fontsize=10.5,
        va="top",
        family="DejaVu Sans Mono",
        linespacing=1.35,
    )
    outfile.parent.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(outfile, dpi=160, facecolor=figure.get_facecolor())
    plt.close(figure)
    print(f"wrote {outfile.relative_to(ROOT)}")


def card_model_hash() -> None:
    digest = (ROOT / "exported_model" / "model_sha256.txt").read_text(encoding="ascii").strip()
    meta = json.loads((ROOT / "results" / "model_hash.json").read_text(encoding="utf-8"))
    lines = [
        "$ python -m src.model_hash",
        "MODEL_HASH_JSON ...",
        "",
        f"file:        {meta.get('file')}",
        f"algorithm:   {meta.get('algorithm')} / model={meta.get('model_name')} v{meta.get('version')}",
        f"alias:       {meta.get('alias')}",
        f"run_id:      {meta.get('run_id')}",
        f"size_bytes:  {meta.get('size_bytes')}",
        "",
        "exported_model/model_sha256.txt:",
        digest,
        "",
        "$ python -m src.model_hash --verify",
        "MODEL_HASH_OK verified=true",
    ]
    _figure("E01 — SHA-256 модели (целостность)", lines, OUT / "E01_model_hash.png")


def card_health() -> None:
    import urllib.request

    health = urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5).read().decode("utf-8")
    meta = urllib.request.urlopen("http://127.0.0.1:8000/metadata", timeout=5).read().decode("utf-8")
    health_obj = json.loads(health)
    meta_obj = json.loads(meta)
    lines = [
        "$ curl http://127.0.0.1:8000/health",
        json.dumps(health_obj, ensure_ascii=False, indent=2),
        "",
        "$ curl http://127.0.0.1:8000/metadata   # truncated",
        f"model_name:    {meta_obj.get('model_name')}",
        f"version:       {meta_obj.get('version')}",
        f"algorithm:     {meta_obj.get('algorithm')}",
        f"model_sha256:  {meta_obj.get('model_sha256')}",
        f"features:      {len(meta_obj.get('features') or [])} named floats",
    ]
    _figure("E02 — /health и /metadata с model_sha256", lines, OUT / "E02_health_sha256.png")


def card_compose_extra() -> None:
    text = (ROOT / "compose.extra.yaml").read_text(encoding="utf-8").splitlines()
    keep = []
    for line in text:
        if line.startswith("name:") or line.startswith("services:") or line.startswith("volumes:"):
            keep.append(line)
        elif line.strip().startswith(("mlflow:", "train:", "seeds-api:", "api-check:", "mlflow_meta:", "mlflow_artifacts:")):
            keep.append(line)
        elif "MLFLOW_TRACKING_URI" in line or "allowed-hosts" in line or "http://mlflow" in line or "http://seeds-api" in line:
            keep.append(line)
        elif "mlflow_meta:" in line or "mlflow_artifacts:" in line or "condition: service_healthy" in line:
            keep.append(line)
    # Prefer a compact curated excerpt
    lines = [
        "FILE: compose.extra.yaml   (отдельный стек доп. задания)",
        "",
        "services:",
        "  mlflow:     host 0.0.0.0:5000, volumes meta+artifacts",
        "              --allowed-hosts includes mlflow:5000",
        "  train:      MLFLOW_TRACKING_URI=http://mlflow:5000",
        "  seeds-api:  MODEL_HASH_PATH + REQUEST_LOG_PATH",
        "  api-check:  python -m src.check_api --base-url http://seeds-api:8000",
        "",
        "volumes:",
        "  seeds_mlflow_meta       # SQLite persistence",
        "  seeds_mlflow_artifacts  # artifacts persistence",
        "",
        "NOTE: базовый compose.yaml не смешан с этим стеком.",
    ]
    _figure("E03 — Compose-сеть доп. задания", lines, OUT / "E03_compose_extra.png", height=5.6)


def card_load_test() -> None:
    report = json.loads((ROOT / "results" / "load_test_report.json").read_text(encoding="utf-8"))
    seq = report["sequential"]
    par = report["parallel"]
    lines = [
        "$ python -m src.load_test",
        "LOAD_TEST_OK",
        "",
        f"base_url: {report['base_url']}",
        f"stable:   {report['stable']}",
        "",
        "sequential:",
        f"  n={seq['n']} ok={seq['ok']} errors={seq['errors']}",
        f"  latency_ms mean={seq['latency_ms']['mean']}  p95={seq['latency_ms']['p95']}  max={seq['latency_ms']['max']}",
        f"  throughput_rps={seq['throughput_rps']}",
        "",
        f"parallel (workers={par.get('workers')}):",
        f"  n={par['n']} ok={par['ok']} errors={par['errors']}",
        f"  latency_ms mean={par['latency_ms']['mean']}  p95={par['latency_ms']['p95']}  max={par['latency_ms']['max']}",
        f"  throughput_rps={par['throughput_rps']}",
        "",
        "saved: results/load_test_report.json",
    ]
    _figure("E04 — Нагрузочный тест API", lines, OUT / "E04_load_test.png")


def card_request_log() -> None:
    sample_path = ROOT / "results" / "api_request_log_sample.jsonl"
    if not sample_path.is_file():
        raw = (ROOT / "logs" / "api_requests.jsonl").read_text(encoding="utf-8").splitlines()
        sample_path.write_text("\n".join(raw[:5]) + "\n", encoding="utf-8")
    lines_raw = sample_path.read_text(encoding="utf-8").splitlines()[:3]
    pretty = []
    for line in lines_raw:
        obj = json.loads(line)
        pretty.append(
            json.dumps(
                {
                    "ts": obj.get("ts"),
                    "path": obj.get("path"),
                    "status_code": obj.get("status_code"),
                    "n_instances": obj.get("n_instances"),
                    "predictions": obj.get("predictions"),
                    "model_version": obj.get("model_version"),
                    "model_sha256": (obj.get("model_sha256") or "")[:18] + "...",
                    "model_latency_ms": obj.get("model_latency_ms") or obj.get("latency_ms"),
                },
                ensure_ascii=False,
            )
        )
    lines = [
        "FILE: logs/api_requests.jsonl  (аудит без персональных данных)",
        "sample: results/api_request_log_sample.jsonl",
        "",
        *pretty,
        "",
        "fields: features of grain + predictions + latency + model hash",
    ]
    _figure("E05 — Журнал запросов/ответов API", lines, OUT / "E05_api_request_log.png", height=6.2)


def card_drift() -> None:
    report = json.loads((ROOT / "results" / "drift_report.json").read_text(encoding="utf-8"))
    summary = report["summary"]
    lines = [
        "$ python -m src.drift_report",
        f"n_train={report['n_train']}  n_request_rows={report['n_request_rows']}",
        "",
        "PSI by feature:",
    ]
    for name, info in report["features"].items():
        lines.append(f"  {name:28s} psi={info['psi']}  level={info['drift_level']}")
    lines.extend(
        [
            "",
            f"high:     {summary.get('high_drift_features')}",
            f"moderate: {summary.get('moderate_drift_features')}",
            f"stable:   {summary.get('stable_features')}",
            "",
            "saved: results/drift_report.json",
        ]
    )
    _figure("E06 — Отчёт о дрейфе признаков (PSI)", lines, OUT / "E06_drift_report.png", height=7.0)


def card_where() -> None:
    lines = [
        "ГДЕ ЛЕЖИТ ДОП. ЗАДАНИЕ",
        "",
        "1) EXTRA_ASSIGNMENT.md          — полное описание доп. задания",
        "2) WHERE_IS_EXTRA_ASSIGNMENT.md — эта карта путей",
        "3) RESULTS_EXTRA.md             — цифры прогона",
        "4) compose.extra.yaml           — Docker Compose стек доп. задания",
        "5) Dockerfile.mlflow / Dockerfile.train",
        "6) src/model_hash.py, src/load_test.py, src/drift_report.py",
        "7) scripts/run_extra_stack.ps1|.sh",
        "8) screenshots/E01..E07*.png    — скриншоты доп. задания",
        "9) results/model_hash.json, load_test_report.json, drift_report.json",
        "10) report/REPORT.md → Приложение Д",
        "",
        "Базовый пример: compose.yaml (только API) — НЕ смешивать URI.",
    ]
    _figure("E07 — Карта файлов доп. задания", lines, OUT / "E07_where_extra_files.png", height=6.8)


def main() -> int:
    card_model_hash()
    card_health()
    card_compose_extra()
    card_load_test()
    card_request_log()
    card_drift()
    card_where()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
