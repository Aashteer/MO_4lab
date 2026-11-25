# Где лежит дополнительное задание

Читать сначала этот файл.

## Главные файлы доп. задания

| Что искать | Путь |
| --- | --- |
| **Описание доп. задания** | [`EXTRA_ASSIGNMENT.md`](EXTRA_ASSIGNMENT.md) |
| **Результаты / цифры** | [`RESULTS_EXTRA.md`](RESULTS_EXTRA.md) |
| **Раздел в отчёте** | [`report/REPORT.md`](report/REPORT.md) → **Приложение Д** |
| **Compose-стек доп. задания** | [`compose.extra.yaml`](compose.extra.yaml) |
| **MLflow Dockerfile** | [`Dockerfile.mlflow`](Dockerfile.mlflow) |
| **Train Dockerfile** | [`Dockerfile.train`](Dockerfile.train) |
| **Запуск стека** | [`scripts/run_extra_stack.ps1`](scripts/run_extra_stack.ps1), [`scripts/run_extra_stack.sh`](scripts/run_extra_stack.sh) |

## Код доп. задания

| Функция | Путь |
| --- | --- |
| Хеш модели | [`src/model_hash.py`](src/model_hash.py) |
| Нагрузочный тест | [`src/load_test.py`](src/load_test.py) |
| Дрейф признаков | [`src/drift_report.py`](src/drift_report.py) |
| Логирование запросов/ответов | [`src/app.py`](src/app.py) |
| Проверка целостности при сборке | [`Dockerfile`](Dockerfile) (`RUN_MODEL_INTEGRITY_CHECK`) |

## Скриншоты доп. задания

Каталог: [`screenshots/`](screenshots/)

| Файл | Содержание |
| --- | --- |
| `screenshots/E01_model_hash.png` | SHA-256 модели |
| `screenshots/E02_health_sha256.png` | `/health` и `/metadata` с `model_sha256` |
| `screenshots/E03_compose_extra.png` | схема `compose.extra.yaml` |
| `screenshots/E04_load_test.png` | нагрузочный тест |
| `screenshots/E05_api_request_log.png` | журнал запросов |
| `screenshots/E06_drift_report.png` | PSI / дрейф |
| `screenshots/E07_where_extra_files.png` | карта файлов |

Список также в [`screenshots/README.md`](screenshots/README.md) (секция «Дополнительное задание»).

## Артефакты прогона

| Файл | Содержание |
| --- | --- |
| `exported_model/model_sha256.txt` | контрольная сумма |
| `results/model_hash.json` | JSON хеша |
| `results/load_test_report.json` | latency / RPS |
| `results/drift_report.json` | отчёт дрейфа |
| `results/api_request_log_sample.jsonl` | образец аудита |
| `logs/api_requests.jsonl` | полный журнал API |

## Важно

- Базовый пример API: `compose.yaml`
- Доп. архитектура: **только** `compose.extra.yaml`
- Внутри сети сервисы ходят на `http://mlflow:5000` / `http://seeds-api:8000`, не на `127.0.0.1`
