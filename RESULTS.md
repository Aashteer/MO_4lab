# Результаты прогона (вариант 21)

Дата прогона: 10.11.2026. Интерпретатор: Python 3.10.11. Пакеты — пины из `requirements.txt` без замен: mlflow 3.5.0, scikit-learn 1.7.2, pandas 2.3.3, numpy 2.2.6, matplotlib 3.10.7, fastapi 0.119.0, uvicorn 0.37.0, sqlalchemy 2.0.44.

Данные: UCI Seeds, 210 строк, SHA-256 `1f3f83c0d8485ae9148061389d19628607e3f5660e3d6f40ec9102fb398bb12f`. Разбиение 126 / 42 / 42, в каждой части поровну Kama, Rosa и Canadian.

## Champion

| Поле | Значение |
| --- | --- |
| Реестр | `seeds-classifier` |
| Версия | **2** |
| Алиас | `champion` |
| Алгоритм | KNN, `n_neighbors=3`, `StandardScaler` |
| run_id | `aa59daab8a5e4aad8284069caf47dcd4` |
| val_f1_macro | 0.952137 |
| val_accuracy | 0.952381 |
| test_f1_macro | 0.900000 |
| test_accuracy | 0.904762 |
| test_precision_macro | 0.916667 |
| test_recall_macro | 0.904762 |

Вторая версия реестра — LogisticRegression `C=10` (версия 1, run `e1c6f836bcd742b185476f96181b1121`, val_f1_macro 0.926284). Алиас выбирался по validation и на test не смотрел.

Матрица ошибок на test (строки — истинный класс, столбцы — прогноз; порядок Kama, Rosa, Canadian):

|  | Kama | Rosa | Canadian |
| --- | ---: | ---: | ---: |
| Kama | 10 | 2 | 2 |
| Rosa | 0 | 14 | 0 |
| Canadian | 0 | 0 | 14 |

Прогнозы реестра `models:/seeds-classifier@champion` и каталога `exported_model/` на test совпали.

## Шесть поисковых прогонов

| Прогон | run_id | val_f1_macro | val_accuracy |
| --- | --- | ---: | ---: |
| lr C=0.1 | `e9f1eb7c500943dab86cdd1a1b11bfd6` | 0.879158 | 0.880952 |
| lr C=1 | `16e34abc385f49fdbb626d844493a62e` | 0.902741 | 0.904762 |
| lr C=10 | `7ac894ca3a4f461e8fc7a22bf8e88b45` | 0.926284 | 0.928571 |
| knn k=3 | `c130e6a8ccf74307a81287222ba98fa5` | 0.952137 | 0.952381 |
| knn k=5 | `e5baa6754bd040fda75ba22f96242484` | 0.900692 | 0.904762 |
| knn k=11 | `32c75f5cedee4f74a4aa74e5ab820896` | 0.877395 | 0.880952 |

Повторная регистрация лучших гиперпараметров дала те же validation-метрики. Версия 1 — lr C=10, версия 2 — knn k=3.

## API после выравнивания с методичкой

`POST /predict` принимает `{"instances":[...]}` (1–100 строк по 7 конечных чисел). Повторный прогон 10.11.2026: `SMOKE_OK`, предсказания `[1, 3, 2]`, `class_names` Kama / Canadian / Rosa, `model_version` `"2"`, `latency_ms` 2.557. `GET /health` → `{"status":"ok","model_version":"2"}`. Пустой `instances`, пропуск поля, лишнее поле, строка, null, bool, `1e309` и битый JSON дают 422. Скрипт `api_bad_requests.ps1` завершился `BAD_REQUESTS_OK`.

## Что выполнено

- MLflow-сервер `http://127.0.0.1:5000`, эксперимент `lab4-seeds` (9 прогонов: 6 train, 2 register, 1 evaluate).
- Алиас `champion` назначался, переносился на версию 1 и возвращался на версию 2 без нового `fit` (`results/alias_history.jsonl`).
- Локальный API `http://127.0.0.1:8000`: `/health`, `/metadata`, три `POST /predict` совпали с `expected_predictions.json`, восемь некорректных тел дали 422, `GET /predict` дал 405.
- Docker Desktop 4.99.0 установлен (`winget` завершился успешно, клиент 29.9.3). Движок не стартует: `Virtual Machine Platform not enabled`. Образы `seeds-api:v1` и `seeds-api:v2` не собирались. `Dockerfile` и `compose.yaml` с healthcheck на `/health` лежат в каталоге.

Полный текст — в `report/REPORT.md`.
