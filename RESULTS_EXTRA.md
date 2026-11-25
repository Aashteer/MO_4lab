# Результаты дополнительного задания

Дата прогона: 25.11.2026 (локальный API на Windows; Docker Engine на этой машине не стартовал).

## Хеш модели

```text
131df221e3bd481d9926b313d4276118196c173b241f40e9f7aadd90164acffb  model.pkl
```

Файл: `exported_model/model_sha256.txt`, JSON: `results/model_hash.json`.

## Smoke API

`SMOKE_OK` — predictions `[1, 3, 2]`, 12 негативных кейсов на 422/405.

## Нагрузочный тест (`results/load_test_report.json`)

| Режим | N | OK | mean ms | p95 ms | RPS |
| --- | ---: | ---: | ---: | ---: | ---: |
| sequential | 20 | 20 | 14.0 | 26.3 | 70.9 |
| parallel (6 workers) | 24 | 24 | 23.6 | 33.1 | 222.2 |

`stable: true`, ошибок нет.

## Дрейф (`results/drift_report.json`)

Смесь in-distribution запросов и партии со сдвигом `area` / `asymmetry_coefficient`.

| Признак | PSI | Уровень |
| --- | ---: | --- |
| asymmetry_coefficient | 0.397 | high |
| area | 0.171 | moderate |
| perimeter, compactness, length_of_kernel, width_of_kernel, length_of_kernel_groove | ~0 | stable |

## Аудит

Журнал: `logs/api_requests.jsonl`. Образец: `results/api_request_log_sample.jsonl`.

## Compose

Конфигурация: `compose.extra.yaml`, образы `Dockerfile.mlflow` / `Dockerfile.train` / `Dockerfile`.
Внутренний URI: `http://mlflow:5000`, volumes `seeds_mlflow_meta` и `seeds_mlflow_artifacts`.
