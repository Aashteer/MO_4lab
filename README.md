# MLOps lab, вариант 21 — классификация сортов пшеницы

Учебный контур для UCI Seeds: шесть прогонов Logistic Regression и KNN в MLflow, реестр `seeds-classifier` с алиасом `champion`, экспорт модели и HTTP API. Сырой файл `data/raw/seeds_dataset.txt` не изменяется.

Локальная машина этой сдачи: Windows 10, Python 3.10.11. Образ Docker рассчитан на Python 3.12. Команды ниже даны и для PowerShell, и для bash.

Прогон на этой копии уже выполнен 10.11.2026. Пины из `requirements.txt` встали на Python 3.10.11 без замены версий. Champion — версия 2 модели `seeds-classifier` (KNN, `n_neighbors=3`). Цифры собраны в `RESULTS.md` и `report/REPORT.md`. Каталоги `mlflow.db`, `mlartifacts/` и `exported_model/` сохранены: UI поднимается тем же `scripts/start_mlflow.ps1`, если порт 5000 ещё свободен.

## Состав

```text
mlops_lab/
  requirements.txt          прямые версии, их ставит и venv, и Docker
  requirements.lock.txt     pip freeze локальной Windows-среды
  Dockerfile
  compose.yaml
  data/raw/seeds_dataset.txt
  data/raw/SHA256SUMS.txt
  src/train.py              обучение и регистрация
  src/promote.py            алиас без переобучения
  src/export_model.py       снимок champion
  src/evaluate.py           метрики отложенного test
  src/app.py                FastAPI
  src/check_api.py          сверка с expected_predictions.json и 422
  src/registry_plan.py      лучший lr и лучший knn по val_f1_macro
  scripts/                  PowerShell и bash
  report/REPORT.md
  RESULTS.md
  screenshots/README.md
```

Признаки в фиксированном порядке: `area`, `perimeter`, `compactness`, `length_of_kernel`, `width_of_kernel`, `asymmetry_coefficient`, `length_of_kernel_groove`.

Классы UCI: `1 Kama`, `2 Rosa`, `3 Canadian`.

Метрика выбора модели: `val_f1_macro`. Test в выборе не участвует. Разбиение 60/20/20: сначала `test_size=0.2`, затем `test_size=0.25` от остатка, `random_state=42`, `stratify`. `StandardScaler` стоит внутри `Pipeline` и обучается только на train.

## Версии

Целевые пины курса записаны в `requirements.txt` (`mlflow==3.5.0`, `scikit-learn==1.7.2`, `pandas==2.3.3`, `numpy==2.2.6`, `matplotlib==3.10.7`, `fastapi==0.119.0`, `uvicorn==0.37.0`, `sqlalchemy==2.0.44`). На Python 3.10.11 этот набор ставится без замены версий. Фактический список транзитивных пакетов — `requirements.lock.txt`.

Lock снят на Windows и содержит `pywin32`. В Linux-образ его не ставят: `Dockerfile` устанавливает `requirements.txt`.

## Windows (PowerShell)

Из каталога `mlops_lab`:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\download_seeds.py
powershell -ExecutionPolicy Bypass -File .\scripts\start_mlflow.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run_all_experiments.ps1
$env:MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
$env:GIT_PYTHON_REFRESH = "quiet"
.\.venv\Scripts\python.exe -m src.promote --best --alias champion --note initial-champion
.\.venv\Scripts\python.exe -m src.export_model
.\.venv\Scripts\python.exe -m src.evaluate
.\.venv\Scripts\python.exe -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```

Во втором окне:

```powershell
$env:MLFLOW_TRACKING_URI = "http://127.0.0.1:5000"
.\.venv\Scripts\python.exe -m src.check_api
powershell -ExecutionPolicy Bypass -File .\scripts\api_bad_requests.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\demo_rollback.ps1
```

Остановить MLflow:

```powershell
Stop-Process -Id (Get-Content .\logs\mlflow.pid)
```

UI: <http://127.0.0.1:5000>. Эксперимент `lab4-seeds`, реестр `seeds-classifier`.

## Ubuntu (bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python scripts/download_seeds.py
chmod +x scripts/*.sh
./scripts/start_mlflow.sh
./scripts/run_all_experiments.sh
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
export GIT_PYTHON_REFRESH=quiet
python -m src.promote --best --alias champion --note initial-champion
python -m src.export_model
python -m src.evaluate
python -m uvicorn src.app:app --host 127.0.0.1 --port 8000
```

Во втором терминале:

```bash
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
python -m src.check_api
./scripts/api_bad_requests.sh
./scripts/demo_rollback.sh
```

Остановить сервер: `kill "$(cat logs/mlflow.pid)"`.

Скрипты `*.sh` должны быть с переводами строк LF. Если файл копировали с Windows: `sed -i 's/\r$//' scripts/*.sh`.

## Что делают шесть прогонов

| Команда | Смысл |
| --- | --- |
| `--algorithm lr --C 0.1` | логистическая регрессия, сильная регуляризация |
| `--algorithm lr --C 1` | то же, C по умолчанию |
| `--algorithm lr --C 10` | слабая регуляризация |
| `--algorithm knn --n-neighbors 3` | KNN, k=3 |
| `--algorithm knn --n-neighbors 5` | KNN, k=5 |
| `--algorithm knn --n-neighbors 11` | KNN, k=11 |

`src/registry_plan.py` оставляет лучший прогон каждого семейства по `val_f1_macro` (при равенстве — по `val_accuracy`, затем более ранний run). Эти два гиперпараметра запускаются ещё раз с `--register` и попадают в реестр как последовательные версии. Повторный fit детерминирован: те же данные, `random_state=42`, нечётное `k`.

`promote --best` вешает алиас `champion` на версию с большим `val_f1_macro`. При полном равенстве предпочтение у логистической регрессии.

## API

`POST /predict` принимает пакет:

```json
{"instances":[{"area":15.26,"perimeter":14.84,"compactness":0.871,"length_of_kernel":5.763,"width_of_kernel":3.312,"asymmetry_coefficient":2.221,"length_of_kernel_groove":5.22}]}
```

В `instances` от 1 до 100 объектов. У каждого объекта ровно семь числовых полей. Пустой список, пропуск поля, лишнее поле, строка, `null`, `true`/`false`, нечисловое значение и неконечное число дают **422**. `GET /predict` даёт 405.

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/metadata
curl -s -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"instances":[{"area":15.26,"perimeter":14.84,"compactness":0.871,"length_of_kernel":5.763,"width_of_kernel":3.312,"asymmetry_coefficient":2.221,"length_of_kernel_groove":5.22}]}'
```

`GET /health` возвращает `status` и `model_version`. Ответ `POST /predict`: `predictions` (метки 1, 2, 3), `class_names` (`Kama` / `Rosa` / `Canadian`), `model_version` и `latency_ms`.

`sample_request.json` — `{"instances":[...]}` из трёх строк test. `expected_predictions.json` — JSON-список целых меток. `check_api.py` сравнивает списки.

## Дополнительное задание (Compose + наблюдаемость)

Отдельный стек в `compose.extra.yaml` (не смешивается с базовым `compose.yaml`):

- MLflow в Docker, volumes для SQLite и artifacts, `--host 0.0.0.0`, `--allowed-hosts` с именем сервиса `mlflow:5000`
- сервис `train` ходит в `http://mlflow:5000`, не в `127.0.0.1`
- gate `api-check` + проверка хеша модели на этапе `docker build`
- `src/model_hash.py`, `src/load_test.py`, `src/drift_report.py`, JSONL-аудит в `logs/api_requests.jsonl`

Подробности и команды: [`EXTRA_ASSIGNMENT.md`](EXTRA_ASSIGNMENT.md).

```powershell
.\.venv\Scripts\python.exe -m src.model_hash
powershell -ExecutionPolicy Bypass -File .\scripts\run_extra_stack.ps1
docker compose -f compose.extra.yaml --profile train run --rm train
.\.venv\Scripts\python.exe -m src.load_test
.\.venv\Scripts\python.exe -m src.drift_report
```

## Docker Desktop и Docker на Ubuntu

Сначала нужен `exported_model/` (`python -m src.export_model`). Образ не ходит в MLflow: модель запечена в каталог.

Windows (Docker Desktop):

```powershell
docker version
$env:IMAGE_TAG = "v1"
docker compose build
docker tag seeds-api:v1 seeds-api:v2
docker compose up -d
docker compose ps
curl http://127.0.0.1:8000/health
docker compose down
```

Ubuntu:

```bash
docker version
IMAGE_TAG=v1 docker compose build
docker tag seeds-api:v1 seeds-api:v2
docker compose up -d
docker compose ps
curl -s http://127.0.0.1:8000/health
docker compose down
```

Образ называется `seeds-api:v1` при `IMAGE_TAG=v1` и `seeds-api:v2` при `IMAGE_TAG=v2`. Проверка жизни есть и в `Dockerfile`, и в `compose.yaml`: процесс внутри контейнера открывает `http://127.0.0.1:8000/health`.

`compose.yaml` публикует порт только на петлю: `127.0.0.1:8000:8000`.

На этой машине `winget install -e --id Docker.DockerDesktop` завершился успешно: установлен Docker Desktop 4.99.0 (клиент 29.9.3). Команда `docker` в уже открытом PowerShell не находится, пока не открыт новый терминал; полный путь — `C:\Program Files\Docker\Docker\resources\bin\docker.exe`. Движок при этом не стартует: журнал пишет `Virtual Machine Platform not enabled` и `No virtualization available` (редакция Windows Home, `wsl -l -v` тоже завершается с ошибкой). Образы `seeds-api:v1` и `seeds-api:v2` поэтому не собраны.

Дальше вручную, в PowerShell от администратора:

```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

Перезагрузить компьютер. Если после перезагрузки Docker Desktop снова пишет, что виртуализации нет, включить Intel VT-x или AMD-V в BIOS и загрузиться ещё раз. Затем запустить Docker Desktop, дождаться Engine running, открыть новый терминал и только потом выполнять `docker compose build`. Перед `compose up` остановить локальный uvicorn, если он занял порт 8000.

Откат контейнера без нового обучения: снова выставить алиас на прежнюю версию, заново экспортировать каталог и поднять уже собранный тег `seeds-api:v1` (`IMAGE_TAG=v1 docker compose up -d`). Либо пересобрать `seeds-api:v2` уже с другим `exported_model` и вернуть трафик на `v1`.

## Откат алиаса без переобучения

`scripts/demo_rollback.ps1` и `scripts/demo_rollback.sh`:

1. Запоминают текущую версию `champion` из `results/export_info.json`.
2. `promote --to-other` переносит алиас на вторую зарегистрированную версию.
3. Экспортируют её в `results/exported_challenger` (образцы API не перезаписываются).
4. Возвращают алиас на исходную версию и обновляют `exported_model`.

Новых `fit` нет. История пишется в `results/alias_history.jsonl`. Уже запущенный uvicorn держит модель в памяти: после смены алиаса процесс нужно перезапустить, либо смотреть новый каталог экспорта.

## Данные

Официальный файл: <https://archive.ics.uci.edu/ml/machine-learning-databases/00236/seeds_dataset.txt>.

Карточка набора: <https://archive.ics.uci.edu/dataset/236/seeds>.

Повторная загрузка: `python scripts/download_seeds.py`. Скрипт пишет байты как есть и строку SHA-256 в `data/raw/SHA256SUMS.txt`. `train.py` сверяет хеш и останавливается, если сырой файл изменили.

## Если что-то не поднимается

- Порт 5000 занят: в скриптах сервер слушает только `127.0.0.1:5000`. Освободите порт или остановите прошлый `logs/mlflow.pid`.
- Порт 8000 занят: не держите uvicorn и compose одновременно.
- `sqlite is locked`: не запускайте второй `mlflow server` на тот же `mlflow.db`.
- Пустой реестр: `run_all_experiments` должен закончиться двумя строками `registered_version`. Затем `promote --best`.
- Docker: `docker version` должен печатать клиент и сервер. Ошибка «docker не распознано» значит, что Desktop не установлен; код сервиса при этом уже лежит в репозитории.
- Кириллица в пути (`Вуз`) на этой машине не мешает относительным `sqlite:///mlflow.db` и `./mlartifacts`, если команды запускаются из `mlops_lab`.

## Docker Desktop на этой Windows-машине

Docker Desktop 4.99.0 уже установлен, но Linux-движок не стартует без компонентов виртуализации.

1. Откройте PowerShell **от имени администратора**.
2. Выполните:

```powershell
cd "c:\Users\l-dan\Desktop\Вуз\4laba\mlops_lab"
powershell -ExecutionPolicy Bypass -File .\scripts\enable_docker_features.ps1
```

3. Перезагрузите ПК.
4. Запустите Docker Desktop и дождитесь статуса Engine running.
5. В новом терминале:

```powershell
cd "c:\Users\l-dan\Desktop\Вуз\4laba\mlops_lab"
$env:Path = "C:\Program Files\Docker\Docker\resources\bin;" + $env:Path
docker compose build
docker tag seeds-api:v1 seeds-api:v2
docker compose up -d
docker compose ps
curl.exe -f http://127.0.0.1:8000/health
.\.venv\Scripts\python.exe -m src.check_api
```

Снимите кадры `screenshots/13_docker_build.png`, `14_docker_images.png`, `15_compose_health.png` и вставьте в отчёт.

