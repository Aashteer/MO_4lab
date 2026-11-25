# Лабораторная работа №4

## MLOps-контур для классификации сортов пшеницы

Вариант 21

Выполнил: ________________________________

Группа: __________________________________

Дата прогона: 10 ноября 2026 г.

Тот же текст лежит в `report/REPORT.docx`. Файл собран скриптом `scripts/build_report_docx.py` (пакет `python-docx` 1.2.0 стоит только в `.venv` и не входит в `requirements.txt`).

---

## 1. Цель работы

Собрать воспроизводимый контур обучения и поставки модели: фиксированные данные и разбиение, сравнение гиперпараметров в MLflow, регистрация двух версий, выбор champion по validation-метрике, экспорт без обращения к серверу в момент ответа API, проверка контракта HTTP и процедура смены алиаса без повторного обучения. Отложенная test-выборка используется один раз, уже после выбора версии.

## 2. Вариант задания

Вариант 21 — классификация сортов пшеницы.

- Источник: UCI Machine Learning Repository, набор Seeds, идентификатор 236.
- Вход: 7 геометрических признаков зерна.
- Выход: три сорта. В файле UCI это метки 1, 2 и 3; в сервисе им соответствуют имена Kama, Rosa и Canadian.
- Алгоритмы: k ближайших соседей и логистическая регрессия.
- Метрика отбора: `val_f1_macro`.
- Сравниваются `n_neighbors` и `C`.
- API принимает ровно семь числовых признаков с фиксированными именами.
- В трекинге не меньше шести прогонов, в реестре не меньше двух версий, у выбранной версии алиас `champion`.
- Предусмотрены образ Docker, smoke-тесты, ответ 422 на неверное тело, обновление и откат алиаса без переобучения, healthcheck в Docker Compose.

Имена в этой работе:

| Объект | Имя |
| --- | --- |
| Эксперимент MLflow | `lab4-seeds` |
| Зарегистрированная модель | `seeds-classifier` |
| Образы | `seeds-api:v1`, `seeds-api:v2` |
| Алиас | `champion` |

Порядок признаков: `area`, `perimeter`, `compactness`, `length_of_kernel`, `width_of_kernel`, `asymmetry_coefficient`, `length_of_kernel_groove`.

## 3. Набор данных

Файл скачан байт в байт с

`https://archive.ics.uci.edu/ml/machine-learning-databases/00236/seeds_dataset.txt`

и сохранён как `data/raw/seeds_dataset.txt`. Размер 9300 байт. SHA-256:

`1f3f83c0d8485ae9148061389d19628607e3f5660e3d6f40ec9102fb398bb12f`

Контрольная сумма продублирована в `data/raw/SHA256SUMS.txt`. Обучение читает сырой файл и сверяет хеш. Если файл изменить, запуск останавливается. Пробелы и табуляции разбирает `pandas` с разделителем `\s+`; сам файл при этом не переписывается.

В наборе 210 объектов, пропусков нет. Классы сбалансированы: Kama, Rosa и Canadian по 70 зерен. Признаки — площадь, периметр, компактность \(4\pi A / P^2\), длина и ширина зерна, коэффициент асимметрии и длина бороздки. Это измерения рентгеновских проекций ядер, описанные Charytanowicz и соавторами.

Краткая сводка по всем 210 строкам:

| Признак | mean | std | min | max |
| --- | ---: | ---: | ---: | ---: |
| area | 14.848 | 2.910 | 10.59 | 21.18 |
| perimeter | 14.559 | 1.306 | 12.41 | 17.25 |
| compactness | 0.871 | 0.024 | 0.8081 | 0.9183 |
| length_of_kernel | 5.629 | 0.443 | 4.899 | 6.675 |
| width_of_kernel | 3.259 | 0.378 | 2.630 | 4.033 |
| asymmetry_coefficient | 3.700 | 1.504 | 0.7651 | 8.456 |
| length_of_kernel_groove | 5.408 | 0.491 | 4.519 | 6.550 |

Полная сводка `describe` лежит в `results/data_profile.json`.

### Разбиение

Сначала `train_test_split(..., test_size=0.2, random_state=42, stratify=y)`, затем такое же разбиение остатка с `test_size=0.25`. Доля 0.25 от оставшихся 80% даёт validation 20% и train 60%.

| Часть | Объектов | Kama | Rosa | Canadian |
| --- | ---: | ---: | ---: | ---: |
| train | 126 | 42 | 42 | 42 |
| val | 42 | 14 | 14 | 14 |
| test | 42 | 14 | 14 | 14 |

Индексы пишутся в артефакт `split.json` каждого прогона. `StandardScaler` стоит первым шагом `sklearn.pipeline.Pipeline` и вызывается только из `fit` на train, поэтому статистика масштаба не видит val и test.

Test в `train.py` не считается. Его метрики пишет отдельный `evaluate.py` уже для экспортированного champion.

## 4. Окружение

| Компонент | Факт этого прогона |
| --- | --- |
| ОС | Windows 10 (10.0.19045) |
| Python локально | 3.10.11, `C:\Users\l-dan\AppData\Local\Programs\Python\Python310\python.exe` |
| Python в Dockerfile | 3.12-slim (образ не собран: нет Docker) |
| mlflow | 3.5.0 |
| scikit-learn | 1.7.2 |
| pandas | 2.3.3 |
| numpy | 2.2.6 |
| matplotlib | 3.10.7 |
| fastapi | 0.119.0 |
| uvicorn | 0.37.0 |
| sqlalchemy | 2.0.44 |
| pydantic (зависимость FastAPI) | 2.14.3 |

Целевые пины курса установились на Python 3.10.11 без понижения версий. Транзитивный снимок — `requirements.lock.txt` (139 пакетов). В нём есть `pywin32`, поэтому Docker ставит `requirements.txt`, а не Windows-lock.

Трекинг: `mlflow server` на `127.0.0.1:5000`, backend `sqlite:///mlflow.db`, каталог артефактов `./mlartifacts`, один worker. Несколько worker-процессов на SQLite дают блокировки базы, поэтому в скриптах явно указан `--workers 1`.

Виртуальное окружение: `mlops_lab/.venv`.

## 5. Ход работы

1. Создано окружение и установлены пины.
2. Скачан сырой Seeds и посчитан SHA-256 (`scripts/download_seeds.py`).
3. Поднят локальный MLflow (`scripts/start_mlflow.ps1`). Сервер ответил на `http://127.0.0.1:5000`.
4. Выполнены шесть поисковых прогонов (`scripts/run_all_experiments.ps1`):
   - логистическая регрессия, `C` = 0.1, 1, 10, solver `lbfgs`, `max_iter=1000`, `random_state=42`;
   - KNN, `n_neighbors` = 3, 5, 11, веса `uniform`, `n_jobs=1`.
5. `src/registry_plan.py` выбрал лучший прогон каждого семейства по `val_f1_macro`. При равенстве метрик скрипт смотрит `val_accuracy`, затем более ранний прогон. Равенства не было.
6. Эти два гиперпараметра запущены ещё раз с `--register`. Метрики совпали с поисковыми прогонами. В реестре появились версии 1 и 2.
7. `src.promote --best` поставил алиас `champion` на версию с большим `val_f1_macro`.
8. `src.export_model` один раз разрешил `models:/seeds-classifier@champion` и записал каталог `exported_model/` вместе с `lab_metadata.json`, `sample_request.json` и `expected_predictions.json`. Образцы — три строки test после JSON-круга, чтобы ожидаемые классы соответствовали тому, что увидит HTTP.
9. `src.evaluate` посчитал test и записал отдельный прогон `evaluate-champion` со стадией `evaluate`. Этот прогон ничего не обучает и в реестр не попадает.
10. Алиас перенесён на вторую версию и возвращён обратно (`scripts/demo_rollback.ps1`). Новых `fit` не было.
11. Локально поднят `uvicorn src.app:app` на `127.0.0.1:8000`. Пройдены `src.check_api` и `scripts/api_bad_requests.ps1`.
12. Команда `docker` завершилась ошибкой «имя не распознано». Сборка образов на этой машине не выполнялась.

В каждом обучающем прогоне MLflow получает параметры, train- и val-метрики (accuracy, macro-F1, macro-precision, macro-recall и F1 по классам), теги `variant=21`, `dataset=uci-seeds`, `stage`, хеш данных и версию Python, артефакты `split.json`, `confusion_matrix_val.png`, текстовый отчёт классификации и сигнатуру `mlflow.sklearn.log_model`. Для логистической регрессии дополнительно сохраняются коэффициенты в пространстве `StandardScaler`.

## 6. Протокол экспериментов

Эксперимент `lab4-seeds`, id `1`. Ниже все прогоны в порядке запуска. Полные JSON-метрики: `results/experiments.json`.

| Прогон | run_id | stage | Параметр | val_f1_macro | val_accuracy | train_f1_macro |
| --- | --- | --- | --- | ---: | ---: | ---: |
| lr-C-0.1 | `e9f1eb7c500943dab86cdd1a1b11bfd6` | train | C=0.1 | 0.8792 | 0.8810 | 0.9527 |
| lr-C-1 | `16e34abc385f49fdbb626d844493a62e` | train | C=1 | 0.9027 | 0.9048 | 0.9683 |
| lr-C-10 | `7ac894ca3a4f461e8fc7a22bf8e88b45` | train | C=10 | 0.9263 | 0.9286 | 1.0000 |
| knn-k-3 | `c130e6a8ccf74307a81287222ba98fa5` | train | k=3 | 0.9521 | 0.9524 | 0.9603 |
| knn-k-5 | `e5baa6754bd040fda75ba22f96242484` | train | k=5 | 0.9007 | 0.9048 | 0.9444 |
| knn-k-11 | `32c75f5cedee4f74a4aa74e5ab820896` | train | k=11 | 0.8774 | 0.8810 | 0.9291 |
| lr-C-10-register | `e1c6f836bcd742b185476f96181b1121` | register | C=10 | 0.9263 | 0.9286 | 1.0000 |
| knn-k-3-register | `aa59daab8a5e4aad8284069caf47dcd4` | register | k=3 | 0.9521 | 0.9524 | 0.9603 |
| evaluate-champion | `a48e140c1b5e4a068288b253d49e7c0d` | evaluate | модель v2 | test_f1_macro = 0.9000 | test_accuracy = 0.9048 | — |

Точные значения `val_f1_macro` поисковых прогонов: 0.879158, 0.902741, 0.926284, 0.952137, 0.900692, 0.877395. Зарегистрированные прогоны повторили 0.926284 и 0.952137. Повторный `fit` детерминирован: те же индексы, `random_state=42`, нечётное число соседей.

F1 по классам на validation у лучшего KNN (k=3): Kama 0.9231, Rosa 1.0000, Canadian 0.9333. У лучшей логистической регрессии (C=10): Kama 0.8800, Rosa 0.9655, Canadian 0.9333.

Наблюдение по сетке. У логистической регрессии и validation, и train растут вместе с `C`: при C=10 модель идеально разделяет train (`train_f1_macro = 1`), но validation остаётся ниже KNN. У KNN увеличение k с 3 до 11 монотонно ухудшает validation: на 210 компактных кластерах широкая окрестность смешивает сорта. Критерий отбора — validation, поэтому идеальный train при C=10 не делает эту модель champion.

## 7. Обоснование champion

В реестр попадают победители семейств, а не вся сетка. Лучший lr — C=10 (val_f1_macro 0.926284). Лучший knn — k=3 (val_f1_macro 0.952137). Глобальный максимум среди шести прогонов совпадает с лучшим семейством, потому что победитель всегда принадлежит одному из двух семейств.

`promote --best` сравнивает уже зарегистрированные версии по `val_f1_macro`, затем по `val_accuracy`. При полном равенстве предпочтение у логистической регрессии как у более прозрачной модели, затем у меньшего номера версии. Равенства не случилось.

Выбрана **версия 2**, KNN с `n_neighbors=3`, run `aa59daab8a5e4aad8284069caf47dcd4`. Разница с версией 1 на validation: 0.952137 − 0.926284 = 0.025853 macro-F1. Это около одного дополнительного верного объекта на 42 строках validation, и она устойчиво видна и в accuracy (0.952381 против 0.928571).

Test этой версии, посчитанный после выбора:

| Метрика | Значение |
| --- | ---: |
| test_accuracy | 0.904762 |
| test_f1_macro | 0.900000 |
| test_precision_macro | 0.916667 |
| test_recall_macro | 0.904762 |
| test_f1 Kama | 0.833333 |
| test_f1 Rosa | 0.933333 |
| test_f1 Canadian | 0.933333 |

Матрица ошибок на test (порядок строк и столбцов: Kama, Rosa, Canadian):

|  | Kama | Rosa | Canadian |
| --- | ---: | ---: | ---: |
| Kama | 10 | 2 | 2 |
| Rosa | 0 | 14 | 0 |
| Canadian | 0 | 0 | 14 |

Верно классифицированы 38 из 42 объектов. Все четыре ошибки — зерна Kama, которые модель отнесла к Rosa или Canadian (по два). Rosa и Canadian на test распознаны полностью. Падение macro-F1 с 0.952 на validation до 0.900 на test ожидаемо при 42 объектах и в выборе модели не участвовало.

Прогнозы файла `exported_model` и URI `models:/seeds-classifier@champion` на test совпали (`registry_predictions_match: true` в `results/test_metrics.json`). Рисунок матрицы: `results/test_confusion_matrix.png`.

## 8. Model Registry и алиас

Реестр `seeds-classifier`. Описание модели на русском зафиксировано клиентом при регистрации.

| Версия | run_id | Алгоритм | val_f1_macro | Алиас в конце прогона |
| --- | --- | --- | ---: | --- |
| 1 | `e1c6f836bcd742b185476f96181b1121` | LogisticRegression, C=10, lbfgs | 0.926284 | нет |
| 2 | `aa59daab8a5e4aad8284069caf47dcd4` | KNeighborsClassifier, k=3 | 0.952137 | `champion` |

На версии записаны теги `algorithm`, `val_f1_macro`, `variant=21`, `dataset=uci-seeds`.

В MLflow 3.5 `log_model(..., name="model")` возвращает URI вида `models:/m-<id>` — это logged model внутри прогона. `mlflow.register_model` по этому URI создаёт версию реестра `seeds-classifier`. Алиас читается отдельно: `models:/seeds-classifier@champion`. Так сервис не привязан к номеру версии в коде: смена champion меняет то, что разрешит следующий экспорт.

Снимок UI эксперимента, карточки прогона, двух версий и алиаса нужно положить в `screenshots/` по списку `screenshots/README.md` (файлы 03–07 и 12). Сервер для снимков: `http://127.0.0.1:5000`.

## 9. Тестирование API

Сервис: `uvicorn src.app:app --host 127.0.0.1 --port 8000`. Модель читается из `MODEL_PATH` (по умолчанию `exported_model/`) через `mlflow.sklearn.load_model` в lifespan. Пока процесс жив, он держит уже загруженный pipeline: смена алиаса в реестре сама по себе ответ не меняет, нужен новый экспорт и перезапуск.

Контракт совпадает с методичкой (пакет `instances`):

- `GET /health` → `{"status":"ok","model_version":"2"}`.
- `GET /metadata` → `model_name` (`seeds-classifier`), `version` и `model_version`, `run_id`, алгоритм, `features` из семи имён, `classes` и `class_names` = `["Kama","Rosa","Canadian"]`.
- `POST /predict` принимает `{"instances":[ {...}, ... ]}`, от 1 до 100 строк. В каждой строке ровно семь конечных JSON-чисел, без лишних ключей. Ответ: `predictions` (целые 1, 2, 3), `class_names`, `model_version`, `latency_ms`.

Фактический пакет из трёх строк test (`sample_request.json`) вернул:

```json
{"predictions":[1,3,2],"class_names":["Kama","Canadian","Rosa"],"model_version":"2","latency_ms":2.557}
```

`expected_predictions.json` — список `[1, 3, 2]`. `python -m src.check_api` завершился `SMOKE_OK`. Строки пакета:

1. area 14.29, perimeter 14.09, compactness 0.905, length 5.291, width 3.337, asymmetry 2.699, groove 4.825 → 1 Kama.
2. area 12.15, perimeter 13.45, compactness 0.8443, length 5.417, width 2.837, asymmetry 3.638, groove 5.338 → 3 Canadian.
3. area 15.57, perimeter 15.15, compactness 0.8527, length 5.92, width 3.231, asymmetry 2.64, groove 5.879 → 2 Rosa.

`scripts/api_bad_requests.ps1` (curl) и те же случаи внутри `check_api.py`:

| Запрос | Ожидание | Факт |
| --- | ---: | ---: |
| GET /health | 200 | 200 |
| GET /metadata | 200 | 200 |
| POST `{}` (нет `instances`) | 422 | 422 |
| POST `{"instances":[]}` | 422 | 422 |
| POST одна строка без `length_of_kernel_groove` | 422 | 422 |
| POST строка с лишним полем `extra` | 422 | 422 |
| POST, `area` — строка | 422 | 422 |
| POST, `area`: null | 422 | 422 |
| POST, `area`: true | 422 | 422 |
| POST, `area`: 1e309 (не конечное) | 422 | 422 |
| POST массив из семи чисел | 422 | 422 |
| POST битый JSON `{` | 422 | 422 |
| POST один корректный объект в `instances` | 200 | 200 |
| GET /predict | 405 | 405 |

Пустое тело требует поле `instances`:

```json
{"detail":[{"type":"missing","loc":["body","instances"],"msg":"Field required","input":{}}]}
```

Целые JSON-числа принимаются. Строка, `null` и boolean отвергаются до приведения к float. Неконечное значение тоже даёт 422: обработчик `RequestValidationError` убирает `Infinity` из тела ошибки, иначе стандартный JSON-encoder FastAPI отвечал бы 500. Схема не проверяет агрономический диапазон признаков.

Снимки `/health`, `/metadata`, успешного predict и 422: файлы 08–11 в `screenshots/`. Интерактивная схема: `http://127.0.0.1:8000/docs`.

## 10. Контейнеризация Docker

`Dockerfile` основан на `python:3.12-slim`, ставит `requirements.txt`, копирует `src/` и `exported_model/`, запускает процесс от пользователя `appuser` и слушает порт 8000. Переменная `MODEL_PATH=/app/exported_model`. В образ вшит `HEALTHCHECK` на `http://127.0.0.1:8000/health`.

Сначала в системе не было команды `docker` (`results/docker_status.txt`). Затем запущена установка:

```powershell
winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements --disable-interactivity
```

Winget нашёл Docker Desktop 4.99.0, проверил хеш установщика и завершился с кодом 0 («Успешно установлено»). Клиент лежит в `C:\Program Files\Docker\Docker\resources\bin\docker.exe` и отвечает версией 29.9.3. Движок Linux при этом не поднялся: `docker version` по полному пути возвращает HTTP 500, а журнал `com.docker.backend` фиксирует `engine linux/wsl failed to start` с причиной `Virtual Machine Platform not enabled` и `No virtualization available`. Редакция системы — Windows Home (бэкенд Hyper-V в настройках Desktop отключён). `wsl.exe -l -v` тоже завершается с кодом 1. Образы `seeds-api:v1` и `seeds-api:v2` не собраны: без виртуализации собирать их не из чего.

Что сделать вручную, в PowerShell от администратора:

```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

1. Перезагрузить компьютер. Включение Virtual Machine Platform без перезагрузки движок не запускает.
2. Если после перезагрузки Docker Desktop снова показывает «No virtualization», включить Intel VT-x или AMD-V в BIOS и загрузиться ещё раз.
3. Запустить Docker Desktop и дождаться состояния Engine running. В новом терминале `docker version` должен показать и Client, и Server.
4. Из каталога `mlops_lab`, когда `exported_model/` уже есть, выполнить команды ниже. Порт опубликован только на `127.0.0.1`. Перед `compose up` остановить локальный uvicorn, если он слушает 8000.

После установки Docker команды такие:

```powershell
$env:IMAGE_TAG = "v1"
docker compose build
docker tag seeds-api:v1 seeds-api:v2
docker compose up -d
docker compose ps
```

На Ubuntu те же шаги: `IMAGE_TAG=v1 docker compose build`, затем `docker tag seeds-api:v1 seeds-api:v2`. Поле `image: seeds-api:${IMAGE_TAG:-v1}` в `compose.yaml` задаёт имя. Повторная сборка с `IMAGE_TAG=v2` нужна, если в контекст положили другой `exported_model`; простой `docker tag` даёт второй тег того же image id.

Место для снимков, которых сейчас нет:

- `screenshots/13_docker_build.png` — успешный `docker compose build`.
- `screenshots/14_docker_images.png` — список с `seeds-api:v1` и `seeds-api:v2`.
- `screenshots/15_compose_health.png` — `docker compose ps` со статусом healthy.

Локальная замена проверки сервиса на этой машине — uvicorn и тесты из раздела 9. Они подтверждают код `src/app.py`, но не подтверждают сборку Linux-образа.

## 11. Обновление и откат без переобучения

Откат в этой работе — смена алиаса реестра, а не новый `train.py`. `scripts/demo_rollback.ps1` выполнился до конца и напечатал `ROLLBACK_OK champion=2`.

История `results/alias_history.jsonl`:

| Время | Версия | val_f1_macro | note |
| --- | --- | ---: | --- |
| 2026-11-10T16:23:03 | 2 | 0.952137 | initial-champion |
| 2026-11-10T16:26:16 | 1 | 0.926284 | update-without-retrain |
| 2026-11-10T16:26:28 | 2 | 0.952137 | rollback-without-retrain |

Между второй и третьей строкой модель версии 1 (логистическая регрессия, C=10) была экспортирована в `results/exported_challenger`. Файл `results/challenger_export_info.json` фиксирует version `"1"` и run `e1c6f836bcd742b185476f96181b1121`. Образцы `sample_request.json` в этот момент не перезаписывались (`--no-samples`). Затем алиас возвращён на версию 2 и `exported_model/` собран заново. Финальный `results/export_info.json` снова указывает version `"2"`.

Новых строк в `results/train_log.jsonl` на этом шаге нет: скрипт вызывает только `promote` и `export_model`.

Для контейнеров тот же смысл: поднять уже собранный `seeds-api:v1` (`IMAGE_TAG=v1 docker compose up -d`) либо пересобрать каталог после отката алиаса и выпустить `seeds-api:v2`. Оба пути не требуют нового обучения. На этой машине выполнен путь реестра и каталогов, путь docker tag не выполнен.

## 12. Docker Compose и healthcheck

Сервис `seeds-api` в `compose.yaml`:

- образ `seeds-api:${IMAGE_TAG:-v1}`;
- публикация порта только на петлю хоста: `127.0.0.1:8000:8000`;
- `MODEL_PATH=/app/exported_model`;
- healthcheck: `python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"`;
- interval 10 с, timeout 5 с, retries 5, start_period 40 с.

Тот же запрос продублирован инструкцией `HEALTHCHECK` в `Dockerfile`. В slim-образе нет `curl`, поэтому проверка идёт стандартной библиотекой Python. `start_period` 40 с оставлен с запасом: импорт MLflow при старте тяжелее, чем сам `predict`.

`docker compose ps` на этой машине не запускался. Когда Docker появится, здоровый контейнер должен показывать healthy после того, как `/health` начнёт отвечать 200. Пока процесс не загрузил модель, lifespan завершается с ошибкой и проверка не проходит — это и есть нужное поведение.

## 13. Выводы

1. На сетке из шести прогонов champion — KNN с тремя соседями (версия 2, `val_f1_macro` 0.952137). Логистическая регрессия улучшается с ростом `C`, но даже при C=10 остаётся ниже на validation, хотя train уже размечен идеально.
2. Честная оценка champion на 42 объектах test: accuracy 0.904762, macro-F1 0.900000. Ошибается только класс Kama. Rosa и Canadian отделяются геометрией надёжно.
3. Контур отделяет сырой файл (хеш), обучение (только train внутри Pipeline), выбор (validation), разовый test и поставку (алиас → каталог → процесс API).
4. Две версии реестра позволяют сменить отвечающую модель без `fit`. Это проверено переносом `champion` на версию 1 и возвратом на версию 2.
5. HTTP принимает пакет `instances` длиной от 1 до 100. Неполный объект, лишнее поле, нечисло и неконечное значение дают 422. Успешный ответ содержит список меток, имена классов, версию модели и `latency_ms`.
6. Сборка `seeds-api:v1` / `seeds-api:v2` не выполнена. Docker Desktop 4.99.0 установлен, но Linux-движок не стартует: Virtual Machine Platform выключена, виртуализации нет. `Dockerfile` и `compose.yaml` с healthcheck и привязкой `127.0.0.1:8000:8000` готовы. После включения компонента и перезагрузки команды из раздела 10 собирают образы. На Ubuntu тот же compose поднимается пакетом Docker без Desktop.

Ограничение эксперимента: одно разбиение `random_state=42` и 42 объекта в test. Для отчёта по варианту этого достаточно; для промышленной оценки той же задачи понадобилась бы повторная кросс-валидация, а test по-прежнему стоило бы держать закрытым до финального отчёта.

## 14. Источники

1. UCI Machine Learning Repository. Seeds. Dataset id 236. https://archive.ics.uci.edu/dataset/236/seeds
2. Файл данных: https://archive.ics.uci.edu/ml/machine-learning-databases/00236/seeds_dataset.txt
3. Charytanowicz M., Niewczas J., Kulczycki P., Kowalski P. A., Lukasik S., Zak S. Complete Gradient Clustering Algorithm for Features Analysis of X-ray Images. Information Technologies in Biomedicine, 2010.
4. Документация MLflow: tracking server, model registry, aliases. https://mlflow.org/docs/latest/index.html
5. scikit-learn: `Pipeline`, `StandardScaler`, `LogisticRegression`, `KNeighborsClassifier`, `train_test_split`, метрики F1. https://scikit-learn.org/
6. FastAPI и Pydantic v2: проверка тела запроса и код 422. https://fastapi.tiangolo.com/

## Приложение А. Команды этого прогона (PowerShell)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\download_seeds.py
powershell -ExecutionPolicy Bypass -File .\scripts\start_mlflow.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run_all_experiments.ps1
$env:MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
.\.venv\Scripts\python.exe -m src.promote --best --alias champion --note initial-champion
.\.venv\Scripts\python.exe -m src.export_model
.\.venv\Scripts\python.exe -m src.evaluate
powershell -ExecutionPolicy Bypass -File .\scripts\demo_rollback.ps1
.\.venv\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000
.\.venv\Scripts\python.exe -m src.check_api
powershell -ExecutionPolicy Bypass -File .\scripts\api_bad_requests.ps1
```

Те же шаги для Ubuntu записаны в `README.md` скриптами `*.sh`.

## Приложение Б. Дерево рабочих артефактов

```text
data/raw/seeds_dataset.txt
data/raw/SHA256SUMS.txt
mlflow.db
mlartifacts/
exported_model/                 champion, версия 2
results/exported_challenger/    версия 1 на время update
results/experiments.json
results/test_metrics.json
results/alias_history.jsonl
results/export_info.json
results/challenger_export_info.json
results/api_smoke_report.json
results/bad_requests/
results/docker_status.txt
sample_request.json
expected_predictions.json
```

## Приложение В. Пример неверного и верного запроса

Неверный:

```http
POST /predict
Content-Type: application/json

{"instances":[]}
```

Ответ: 422, список короче допустимого минимума.

Верный пакет (контрольное зерно):

```json
{
  "instances": [
    {
      "area": 15.26,
      "perimeter": 14.84,
      "compactness": 0.871,
      "length_of_kernel": 5.763,
      "width_of_kernel": 3.312,
      "asymmetry_coefficient": 2.221,
      "length_of_kernel_groove": 5.22
    }
  ]
}
```

Успешный ответ имеет вид `{"predictions":[...],"class_names":[...],"model_version":"2","latency_ms":...}`. Пакет из трёх тестовых строк дал `[1, 3, 2]` за 2.557 мс.

## Приложение Г. Снимки экрана

Список кадров — `screenshots/README.md`. Сняты живые экраны MLflow (прогоны, карточка champion, две версии реестра, алиас `champion`) и Swagger (`screenshots/api_docs.png`). Ответы `/health`, `/metadata`, `/predict` и 422 положены карточками: встроенный просмотрщик JSON снимается пустым кадром. Кадры Docker (13–15) не сняты: Desktop установлен, но Linux-движок не стартует без Virtual Machine Platform.

## Приложение Д. Дополнительное задание

Выполнено расширение контура (см. `EXTRA_ASSIGNMENT.md` и `compose.extra.yaml`).

1. **MLflow в Docker.** Сервис `mlflow`, слушатель `0.0.0.0:5000`, `--allowed-hosts` включает `mlflow:5000`. Постоянные volumes `seeds_mlflow_meta` (SQLite) и `seeds_mlflow_artifacts`.
2. **Train-сервис.** `Dockerfile.train` + профиль `train`. URI трекинга — `http://mlflow:5000` (имя сервиса Compose-сети).
3. **Проверка API в сборке/запуске.** В `Dockerfile` при сборке считаются и сверяются SHA-256 `model.pkl` и загружается Pipeline. Сервис `api-check` вызывает `src.check_api` по `http://seeds-api:8000`; ненулевой exit не даёт считать запуск успешным.
4. **Хеш модели.** `src/model_hash.py` → `exported_model/model_sha256.txt`, `results/model_hash.json`. Значение также отдаётся в `/health` и `/metadata`.
5. **Нагрузочный тест.** `src/load_test.py` — последовательные и параллельные `POST /predict`, отчёт `results/load_test_report.json` (latency min/mean/p95/max, RPS, errors).
6. **Логирование запросов.** Middleware + запись результата предсказания в `logs/api_requests.jsonl` (признаки зерна, predictions, latency; без персональных данных).
7. **Дрейф признаков.** `src/drift_report.py` сравнивает train-split и успешные запросы из журнала (PSI), пишет `results/drift_report.json`.

Базовый `compose.yaml` оставлен без смешения URI: расширенный стек поднимается только через `compose.extra.yaml`.
