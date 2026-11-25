# Дополнительное задание (MLOps, вариант 21)

Расширение обязательного цикла: MLflow в Docker с постоянным хранилищем, train-сервис в Compose-сети, gate-проверка API, хеш модели, нагрузочный тест, аудит запросов и отчёт о дрейфе признаков.

Базовый пример `compose.yaml` (только API) **не смешан** с этой архитектурой. Расширенный стек — `compose.extra.yaml`.

## Архитектура

| Сервис | Имя в сети | URI из другого контейнера | С хоста |
| --- | --- | --- | --- |
| MLflow | `mlflow` | `http://mlflow:5000` | `http://127.0.0.1:5000` |
| Train | `train` | пишет в MLflow по имени сервиса | one-shot |
| API | `seeds-api` | `http://seeds-api:8000` | `http://127.0.0.1:8000` |
| Gate | `api-check` | `http://seeds-api:8000` | exit ≠ 0 → стек неуспешен |

- MLflow слушает `0.0.0.0:5000`.
- `--allowed-hosts` включает `mlflow:5000` (иначе 403 Invalid Host header).
- Volumes: `seeds_mlflow_meta` (SQLite) и `seeds_mlflow_artifacts` (artifacts).

## Файлы

- `Dockerfile.mlflow`, `Dockerfile.train`, `compose.extra.yaml`
- `src/model_hash.py` — SHA-256 `model.pkl`
- `src/load_test.py` — последовательная и параллельная нагрузка
- `src/drift_report.py` — PSI train vs журнал `/predict`
- `src/app.py` — JSONL-аудит запросов/ответов (без ПДн)
- `scripts/run_extra_stack.ps1` / `.sh`

## Запуск

```powershell
# 1) Хеш экспортированной модели
.\.venv\Scripts\python.exe -m src.model_hash

# 2) Стек: MLflow + API + gate
powershell -ExecutionPolicy Bypass -File .\scripts\run_extra_stack.ps1

# 3) Обучение через Compose-сеть (не 127.0.0.1)
docker compose -f compose.extra.yaml --profile train run --rm train `
  python -m src.train --algorithm knn --n-neighbors 3 --register

# 4) Нагрузка и дрейф (API должен отвечать)
.\.venv\Scripts\python.exe -m src.load_test
.\.venv\Scripts\python.exe -m src.drift_report
```

Ubuntu:

```bash
python -m src.model_hash
chmod +x scripts/run_extra_stack.sh
./scripts/run_extra_stack.sh
docker compose -f compose.extra.yaml --profile train run --rm train
python -m src.load_test
python -m src.drift_report
```

## Проверка API в сборке/запуске

1. **Build:** `Dockerfile` при `RUN_MODEL_INTEGRITY_CHECK=1` считает/сверяет SHA-256 и загружает `model.pkl`. Битый артефакт → build fail.
2. **Start:** healthcheck на `/health`.
3. **Gate:** сервис `api-check` гоняет `src.check_api` против `http://seeds-api:8000`. Ненулевой код → стек не считается успешным.

## Артефакты результатов

| Файл | Содержание |
| --- | --- |
| `exported_model/model_sha256.txt` | контрольная сумма |
| `results/model_hash.json` | метаданные хеша |
| `results/api_smoke_report_extra.json` | gate smoke |
| `results/load_test_report.json` | latency / RPS / errors |
| `logs/api_requests.jsonl` | аудит запросов и ответов |
| `results/drift_report.json` | PSI по признакам |

## Наблюдаемость API

Каждый успешный `POST /predict` пишет в `logs/api_requests.jsonl`: timestamp, request_id, признаки зерна, predictions, class_names, model_version, model_sha256, latency. Персональных данных нет (только геометрические измерения семян).

## Зафиксированные результаты прогона (25.11.2026)

- **model SHA-256:** `131df221e3bd481d9926b313d4276118196c173b241f40e9f7aadd90164acffb`
- **load test:** sequential 20 req → mean ~14 ms, ~71 RPS; parallel 24/6 workers → mean ~24 ms, ~222 RPS; errors=0
- **drift:** PSI `asymmetry_coefficient` ≈ 0.40 (high), `area` ≈ 0.17 (moderate); остальные признаки стабильны на смеси in-distribution + сдвинутых запросов
- **smoke:** `SMOKE_OK` (predictions `[1,3,2]`)
- Файлы: `results/model_hash.json`, `results/load_test_report.json`, `results/drift_report.json`, `results/api_request_log_sample.jsonl`

Compose-образы на этой Windows-машине могут не собраться, если Docker Engine не стартует (Virtual Machine Platform). Код и YAML готовы; локальный API-прогон подтверждает хеш, нагрузку, логи и дрейф.