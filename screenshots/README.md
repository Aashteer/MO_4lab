# Снимки экрана для отчёта

Снимки кладутся в этот каталог и вставляются в `report/REPORT.md`. Имена фиксированы, чтобы отчёт не пришлось переписывать.

| Файл | Что должно быть в кадре |
| --- | --- |
| `01_dataset_uci.png` | Страница UCI Seeds (id 236): 210 объектов, 7 признаков, 3 класса. |
| `02_raw_head.png` | Начало `data/raw/seeds_dataset.txt` и строка SHA-256 из `SHA256SUMS.txt`. |
| `03_mlflow_experiments.png` | UI эксперимента `lab4-seeds`: не меньше шести прогонов, колонка `val_f1_macro`. |
| `04_mlflow_run_detail.png` | Карточка champion-прогона: params, metrics, tags. |
| `05_confusion_matrix.png` | Артефакт `confusion_matrix_val.png` выбранного прогона. |
| `06_registry_versions.png` | Model Registry `seeds-classifier`: две версии. |
| `07_alias_champion.png` | Алиас `champion` на выбранной версии. |
| `08_api_health.png` | Ответ `GET /health`. |
| `09_api_metadata.png` | Ответ `GET /metadata` со списком из 7 признаков и классов Kama, Rosa, Canadian. |
| `10_api_predict.png` | Успешный `POST /predict` с `class_name` и `latency_ms`. |
| `11_api_422.png` | Ответ 422 на пустое тело, лишнее поле или строку вместо числа. |
| `12_rollback_alias.png` | История алиаса: update без переобучения и возврат `champion`. |
| `13_docker_build.png` | `docker build` образа `seeds-api:v1`. |
| `14_docker_images.png` | `docker images` с тегами `seeds-api:v1` и `seeds-api:v2`. |
| `15_compose_health.png` | `docker compose ps`: сервис healthy по проверке `/health`. |

## Что уже лежит в каталоге

Живые снимки UI:

- `03_mlflow_experiments.png` — MLflow 3.5.0, эксперимент `lab4-seeds`, 9 прогонов.
- `04_mlflow_run_detail.png` — карточка `knn-k-3-register`, `val_f1_macro` 0.952137, версия реестра 2.
- `06_registry_versions.png` — версии 1 и 2, у версии 2 алиас `champion`.
- `07_alias_champion.png` — список моделей, `seeds-classifier`, `@champion : Version 2`.
- `api_docs.png` — Swagger `Seeds classifier API`: `GET /health`, `GET /metadata`, `POST /predict`.

`05_confusion_matrix.png` — копия `results/test_confusion_matrix.png`.

`02`, `08`–`12` собраны из живых ответов этого прогона (текст файла, health, metadata, predict, 422 и история алиаса). Страница сырого JSON в браузере снимается чёрным холстом, поэтому для этих ответов оставлены читаемые карточки, а не пустой кадр.

## Docker на этой машине

Docker Desktop 4.99.0 установлен, но Linux-движок не стартует: Virtual Machine Platform выключена. Снимки 13–15 поэтому не сделаны. После включения компонента, перезагрузки и `docker compose build` их нужно снять по командам из README. Файл `01_dataset_uci.png` снимается вручную со страницы UCI.
