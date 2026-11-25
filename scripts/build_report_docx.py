"""Build a fuller DOCX report for variant 21 (more text + screenshots)."""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "screenshots"
OUT = ROOT / "report" / "REPORT_variant21.docx"
OUT_DESKTOP = ROOT.parent / "Отчет_ЛР4_MLOps_вариант21.docx"


def set_run_font(run, name="Times New Roman", size=14, bold=False):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run._element.rPr.rFonts.set(qn("w:ascii"), name)
    run._element.rPr.rFonts.set(qn("w:hAnsi"), name)
    run._element.rPr.rFonts.set(qn("w:cs"), name)
    run.font.size = Pt(size)
    run.bold = bold


FIG_N = 0
TABLE_N = 0


def add_p(doc, text, *, bold=False, center=False, size=14, indent=True, after=6, font="Times New Roman"):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    if indent and not center and not bold and font == "Times New Roman":
        p.paragraph_format.first_line_indent = Cm(1.25)
    else:
        p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run(text)
    set_run_font(run, name=font, size=size, bold=bold)
    return p


def add_cmd(doc, text):
    """Terminal/code line: Courier New 9."""
    return add_p(doc, text, size=9, indent=False, after=2, font="Courier New", center=False)


def add_h(doc, text, size=14):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=True)


def add_fig(doc, filename, title, note: str | None = None):
    global FIG_N
    FIG_N += 1
    path = SHOTS / filename
    if path.is_file():
        doc.add_picture(str(path), width=Cm(15.8))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        add_p(doc, f"[нет файла {filename}]", center=True, size=14, indent=False)
    add_p(doc, f"Рисунок {FIG_N} – {title}", center=True, bold=True, size=14, indent=False, after=2)
    if note:
        add_p(doc, note, size=14, indent=True, after=8)
    return FIG_N


def add_table(doc, headers, rows, caption: str | None = None):
    global TABLE_N
    if caption:
        if caption.startswith("Таблица"):
            title = caption.split(" – ", 1)[1] if " – " in caption else caption
            TABLE_N += 1
            caption = f"Таблица {TABLE_N} – {title}"
        else:
            TABLE_N += 1
            caption = f"Таблица {TABLE_N} – {caption}"
        add_p(doc, caption, center=True, bold=True, size=14, indent=False)
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        set_run_font(run, size=14, bold=True)
    for r_i, row in enumerate(rows):
        for c_i, value in enumerate(row):
            cell = table.rows[r_i + 1].cells[c_i]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(value))
            set_run_font(run, size=14)
    doc.add_paragraph()


def add_code(doc, title: str, text: str, limit: int | None = None):
    """Insert a titled code listing (Courier New 9). limit=None means full file."""
    add_h(doc, title, size=14)
    cleaned = text.replace("\x00", "").replace("\r", "")
    lines = cleaned.splitlines() or [""]
    shown = lines if limit is None else lines[:limit]
    for line in shown:
        para = doc.add_paragraph()
        para.paragraph_format.space_after = Pt(0)
        para.paragraph_format.line_spacing = 1.0
        para.paragraph_format.first_line_indent = Cm(0)
        run = para.add_run(line if line.strip() else " ")
        set_run_font(run, name="Courier New", size=9)
    if limit is not None and len(lines) > limit:
        add_p(
            doc,
            f"… (показаны первые {limit} строк из {len(lines)}; полный файл — в каталоге проекта)",
            size=9,
            indent=False,
            font="Courier New",
        )


def main() -> int:
    global FIG_N, TABLE_N
    FIG_N = 0
    TABLE_N = 0
    metrics = json.loads((ROOT / "results" / "test_metrics.json").read_text(encoding="utf-8"))
    digest = "1f3f83c0d8485ae9148061389d19628607e3f5660e3d6f40ec9102fb398bb12f"
    m = metrics["metrics"]

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(3)
    section.right_margin = Cm(1.5)

    # ---- TITLE ----
    for line in [
        "Министерство науки и высшего образования Российской Федерации",
        "_____________________________________________________________",
        "(полное наименование образовательной организации)",
        "Кафедра ___________________________________________",
    ]:
        add_p(doc, line, center=True, indent=False)
    doc.add_paragraph()
    add_p(doc, "ОТЧЁТ", center=True, bold=True, size=14, indent=False)
    add_p(doc, "по лабораторной работе № 4", center=True, size=14, indent=False)
    add_p(doc, "по дисциплине «_____________________________________»", center=True, indent=False)
    add_p(
        doc,
        "«MLOps: учёт экспериментов в MLflow, реестр моделей, развёртывание сервиса предсказаний в Docker»",
        center=True,
        bold=True,
        size=14,
        indent=False,
    )
    add_p(doc, "Вариант 21. Классификация сортов пшеницы", center=True, bold=True, size=14, indent=False)
    doc.add_paragraph()
    add_p(doc, "Выполнил:", indent=False)
    add_p(doc, "студент группы ____________", indent=False)
    add_p(doc, "_______________ (Ф. И. О.)", indent=False)
    add_p(doc, "Проверил:", indent=False)
    add_p(doc, "_______________ (Ф. И. О.)", indent=False)
    add_p(doc, "«___» ___________ 2026 г.", center=True, indent=False)
    add_p(doc, "2026", center=True, indent=False)
    doc.add_page_break()

    add_h(doc, "Содержание отчёта")
    for item in [
        "1. Цель работы и постановка задачи (индивидуальный вариант 21)",
        "2. Описание набора данных: источник, признаки, целевая переменная, подготовка и разбиение",
        "3. Программное окружение, версии зависимостей и структура проекта",
        "4. Последовательность выполнения работы (команды, пояснения, скриншоты)",
        "5. Сравнительная таблица не менее шести экспериментов",
        "6. Обоснование выбора модели и результаты итоговой оценки",
        "7. Регистрация версий модели и назначение alias champion",
        "8. Описание API, формата входных данных и проверки запросов",
        "9. Сборка и запуск Docker-контейнера, совпадение предсказаний API и экспорта",
        "10. Демонстрация обновления и отката (версии моделей и теги образов)",
        "11. Запуск через Docker Compose и проверка healthcheck",
        "12. Воспроизводимость",
        "Выводы по работе",
        "Список использованных источников",
        "Приложение: исходный код, файлы зависимостей, Dockerfile, Compose и примеры запросов",
    ]:
        add_p(doc, item, indent=False, after=3)
    doc.add_page_break()

    # ---- 1 ----
    add_h(doc, "1. Цель работы и постановка задачи")
    add_p(
        doc,
        "Цель лабораторной работы № 4 — освоить основы MLOps на полном учебном цикле: "
        "от учёта экспериментов и сравнения моделей до публикации сервиса предсказаний. "
        "В рамках работы требуется научиться логировать параметры, метрики, теги и артефакты "
        "в MLflow Tracking; регистрировать модели в Model Registry; назначать и менять alias "
        "champion; экспортировать снимок модели вместе с преобразованиями признаков; "
        "разворачивать FastAPI-сервис в Docker и Docker Compose; проверять корректные и "
        "некорректные запросы; демонстрировать обновление и откат без повторного обучения.",
    )
    add_p(
        doc,
        "Индивидуальный вариант 21 — классификация сортов пшеницы по набору UCI Seeds "
        "(https://archive.ics.uci.edu/dataset/236/seeds). Постановка задачи: по семи "
        "геометрическим измерениям зерна предсказать один из трёх сортов — Kama, Rosa или "
        "Canadian. Это задача многоклассовой классификации с сбалансированными классами. "
        "Согласно методическим указаниям для варианта 21 рекомендуется сравнить семейства "
        "KNeighborsClassifier и LogisticRegression. Метрикой выбора модели зафиксирована "
        "macro-усреднённая F1 на валидационной выборке (val_f1_macro). Отложенная test-выборка "
        "не участвует в подборе гиперпараметров и используется один раз после назначения "
        "champion для итоговой оценки качества.",
    )
    add_p(
        doc,
        "Практическая ценность постановки для курса MLOps состоит не в достижении максимальной "
        "точности любой ценой, а в воспроизводимом процессе: одинаковые данные и разбиение, "
        "прозрачное сравнение не менее шести запусков, явный критерий выбора, версионирование "
        "модели и контейнера, проверяемый контракт API. Имя эксперимента в Tracking — "
        "lab4-seeds; имя модели в Registry — seeds-classifier; теги Docker-образов — "
        "seeds-api:v1 и seeds-api:v2.",
    )
    add_p(doc, "В соответствии с заданием необходимо:")
    for item in [
        "выбрать набор данных, указать источник, признаки, целевую переменную и метрики;",
        "подготовить данные и корректно разбить выборку на train / validation / test;",
        "выполнить не менее шести экспериментов и сохранить в MLflow параметры, метрики, теги и артефакты;",
        "сравнить результаты и обосновать выбор модели;",
        "зарегистрировать не менее двух версий в Model Registry и назначить alias champion;",
        "экспортировать модель вместе с преобразованиями и реализовать API предсказаний;",
        "подготовить Dockerfile, собрать образ и запустить сервис в контейнере;",
        "проверить корректные и некорректные запросы, а также совпадение ответов API с экспортированной моделью;",
        "продемонстрировать обновление и откат без повторного обучения;",
        "запустить сервис через Docker Compose с healthcheck;",
        "зафиксировать зависимости, исходные данные и разбиение для воспроизводимости.",
    ]:
        add_p(doc, "– " + item, indent=False)
    add_p(
        doc,
        "Кратко о используемых понятиях. Experiment в MLflow объединяет набор runs. Для каждого "
        "run сохраняются parameters (гиперпараметры и настройки пайплайна), metrics (числовые "
        "показатели качества), tags (метаданные вроде variant, dataset, data_sha256) и artifacts "
        "(файлы: split.json, матрицы ошибок, отчёты, сериализованная модель). Model Registry "
        "хранит пронумерованные версии именованной модели; alias champion — изменяемая ссылка "
        "на выбранную для эксплуатации версию и сам по себе не создаёт новую модель. "
        "Docker-образ содержит снимок экспортированной модели и FastAPI-приложение; Compose "
        "описывает декларативный запуск и периодическую проверку /health. После сборки "
        "контейнер не обращается к серверу MLflow за предсказаниями: inference идёт только "
        "по локальному файлу model.pkl внутри образа.",
    )
    add_p(
        doc,
        "Критерий успеха работы по методичке: не менее шести успешных run в одном эксперименте; "
        "не менее двух версий в Registry с назначенным champion; работающий HTTP API; "
        "совпадение предсказаний контейнера с эталоном expected_predictions.json; "
        "демонстрация update/rollback по тегам образов и alias; статус healthy у Compose-сервиса.",
    )

    # ---- 2 ----
    add_h(doc, "2. Описание набора данных")
    add_p(
        doc,
        "Источник данных — набор Seeds из UCI Machine Learning Repository (dataset id 236, "
        "лицензия CC BY 4.0). Авторы набора — Charytanowicz и др.; данные получены измерением "
        "геометрии зёрен пшеницы трёх сортов. Файл скачан по адресу "
        "https://archive.ics.uci.edu/ml/machine-learning-databases/00236/seeds_dataset.txt "
        "и сохранён без каких-либо правок как data/raw/seeds_dataset.txt. Для контроля "
        "целостности вычислена контрольная сумма SHA-256 (ниже); она же записывается в тег "
        "data_sha256 каждого запуска MLflow, чтобы связать метрики с конкретным сырым файлом.",
    )
    add_p(doc, digest, center=True, size=14, indent=False)
    add_p(
        doc,
        "Набор содержит 210 объектов: по 70 зёрен сортов Kama, Rosa и Canadian. Пропусков и "
        "дубликатов строк в исходнике нет. Целевая переменная — целочисленная метка сорта: "
        "1 = Kama, 2 = Rosa, 3 = Canadian. Входные признаки — семь вещественных геометрических "
        "характеристик зерна (таблица 1). Задача относится к учебной классификации: цель — "
        "построить воспроизводимый MLOps-конвейер, а не выдать агрономическую рекомендацию.",
    )
    add_p(
        doc,
        "Метрики качества. Для выбора модели используется val_f1_macro (macro-average F1 на "
        "validation). Дополнительно логируются val_accuracy, val_precision_macro, "
        "val_recall_macro и F1 по каждому сорту. На train сохраняются те же показатели для "
        "контроля переобучения. После выбора champion один раз считаются аналогичные метрики "
        "на отложенном test (test_f1_macro, test_accuracy и др.). Macro-усреднение выбрано "
        "осознанно: классы сбалансированы, но важно одинаково учитывать ошибки по каждому сорту.",
    )
    add_table(
        doc,
        ["Признак", "Описание"],
        [
            ["area", "площадь зерна"],
            ["perimeter", "периметр"],
            ["compactness", "компактность 4πA/P²"],
            ["length_of_kernel", "длина зерна"],
            ["width_of_kernel", "ширина зерна"],
            ["asymmetry_coefficient", "коэффициент асимметрии"],
            ["length_of_kernel_groove", "длина бороздки"],
        ],
        "Таблица 1 – Признаки модели",
    )
    add_p(
        doc,
        "Подготовка данных выполняется только в коде загрузки и не изменяет файл в data/raw/. "
        "Строки разбираются по пробельным разделителям (в исходнике встречаются табуляции и "
        "пробелы), столбцам назначаются осмысленные имена признаков и class, проверяется "
        "совпадение SHA-256 с эталоном. Масштабирование StandardScaler не применяется «глобально "
        "ко всему датасету заранее»: оно является первым шагом sklearn.pipeline.Pipeline и "
        "обучается исключительно на train-части каждого запуска. Это исключает утечку статистики "
        "масштаба (mean/std) на validation и test. Внутри Pipeline затем следует классификатор "
        "(LogisticRegression или KNeighborsClassifier). Для API экспорт включает весь Pipeline, "
        "поэтому на инференсе клиент передаёт сырые геометрические признаки в исходном масштабе.",
    )
    add_p(
        doc,
        "Способ разбиения. Выборка делится на train / validation / test в два шага функцией "
        "sklearn.model_selection.train_test_split. Сначала из полной выборки выделяется 20 % "
        "в итоговый test (test_size=0.2). Затем из оставшихся 80 % выделяется 25 % в validation "
        "(что даёт 20 % от исходной выборки). Итоговые доли составляют примерно 60/20/20 "
        "(126 / 42 / 42 объекта). Во всех вызовах зафиксированы random_state=42 и stratify по "
        "целевой переменной, поэтому доли сортов внутри каждой части одинаковы. Индексы "
        "объектов сохраняются в артефакт split.json каждого run — это позволяет повторно "
        "воспроизвести то же разбиение и проверить, что test не «подглядывали» при выборе модели.",
    )
    add_p(
        doc,
        "Предварительный анализ (EDA) подтверждает идеальный баланс классов и частичное "
        "перекрытие сортов в пространстве признаков. На диаграммах ниже видно, что Rosa "
        "отделяется лучше по размерам зерна, а Kama чаще лежит на границе с другими сортами — "
        "это согласуется с более низким F1 именно для Kama на итоговой test-оценке.",
    )
    add_fig(
        doc,
        "R01_uci.png",
        "Страница набора Seeds на сайте UCI",
        "На кадре видны 210 instances, задача Classification/Clustering и описание трёх сортов пшеницы.",
    )
    add_fig(
        doc,
        "R02b_raw.png",
        "Сырой файл data/raw/seeds_dataset.txt и SHA-256",
        "Исходный файл не переписывается; преобразования выполняются только в памяти при загрузке.",
    )
    add_table(
        doc,
        ["Часть", "Объектов", "Kama", "Rosa", "Canadian"],
        [["train", "126", "42", "42", "42"], ["validation", "42", "14", "14", "14"], ["test", "42", "14", "14", "14"]],
        "Таблица 2 – Стратифицированное разбиение выборки",
    )
    add_fig(
        doc,
        "G07_eda_balance_features.png",
        "Баланс классов и средние значения ключевых признаков",
        "Классы идеально сбалансированы (по 70); по area/perimeter сорт Rosa заметно крупнее.",
    )
    add_fig(
        doc,
        "G08_pca_scatter.png",
        "PCA-проекция объектов Seeds (7 признаков → 2 компоненты)",
        "Кластеры сортов частично перекрываются (особенно Kama), что объясняет ошибки на границе.",
    )

    # ---- 3 ----
    add_h(doc, "3. Программное окружение и структура проекта")
    add_p(
        doc,
        "Работа выполнена на ОС Windows 10 (сборка 10.0.19045) с Docker Desktop и бэкендом WSL2. "
        "Локальное обучение, Tracking и экспорт модели выполнялись в виртуальном окружении "
        "Python 3.10.11 (.venv). Docker-образ API собран на базе официального python:3.12-slim, "
        "чтобы уменьшить размер runtime-слоя. Версии ключевых компонентов приведены в таблице 3; "
        "фактическая проверка версий на хосте показана на рисунке 3.",
    )
    add_p(
        doc,
        "Зависимости разделены по назначению. Файл requirements.txt содержит прямые пакеты для "
        "обучения и Tracking (mlflow, scikit-learn, pandas, fastapi и др.). Файл "
        "requirements.lock.txt фиксирует полный снимок установленных версий на хосте для "
        "воспроизводимости. Файл requirements-serve.txt описывает облегчённый набор пакетов "
        "внутри контейнера (без полного tracking-стека MLflow): контейнер загружает уже "
        "экспортированный model.pkl формата cloudpickle и обслуживает HTTP-запросы через "
        "uvicorn/FastAPI. Такое разделение ускоряет сборку образа и уменьшает поверхность "
        "зависимостей в production-подобном runtime.",
    )
    add_table(
        doc,
        ["Компонент", "Версия"],
        [
            ["Python (host)", "3.10.11"],
            ["Python (Docker)", "3.12-slim"],
            ["MLflow", "3.5.0"],
            ["scikit-learn", "1.7.2"],
            ["pandas / numpy", "2.3.3 / 2.2.6"],
            ["FastAPI / uvicorn", "0.119.0 / 0.37.0"],
            ["Docker Engine", "29.9.3"],
        ],
        "Таблица 3 – Версии программного окружения",
    )
    add_fig(
        doc,
        "R02_versions.png",
        "Проверка версий Python / MLflow / scikit-learn и requirements.txt",
        "Команда выполнена в активированном виртуальном окружении .venv проекта.",
    )
    add_p(
        doc,
        "Структура каталога mlops_lab/ организована так, чтобы этапы лабораторной работы "
        "соответствовали отдельным модулям и артефактам. Каталог src/ содержит исполняемый код: "
        "train.py — обучение Pipeline, логирование в MLflow и опциональная регистрация в Registry; "
        "promote.py — назначение/смена alias champion; export_model.py — выгрузка снимка модели "
        "в exported_model/; evaluate.py — однократная оценка champion на test; app.py — FastAPI-"
        "сервис; check_api.py — автоматическая сверка ответов API с expected_predictions.json; "
        "common.py — общие константы и загрузка данных. Каталог data/raw/ хранит неизменяемый "
        "исходный файл Seeds. Каталог mlruns/ и файл mlflow.db относятся к локальному Tracking; "
        "mlartifacts/ — к артефактам запусков. Каталог exported_model/ — снимок champion для Docker. "
        "В корне лежат Dockerfile, compose.yaml, requirements*.txt, sample_request.json и "
        "expected_predictions.json. Каталоги screenshots/ и report/ используются для оформления "
        "отчёта; results/ — для служебных JSON с метриками и планом регистрации.",
    )
    add_p(
        doc,
        "Такое разделение упрощает проверку по чек-листу методички: данные отделены от кода, "
        "обучение отделено от serving, снимок модели для контейнера не зависит от живого "
        "Tracking Server, а скрипты обновления/отката работают с alias и тегами образов.",
    )
    add_fig(
        doc,
        "R03_tree.png",
        "Структура ключевых каталогов проекта",
        "Относительные пути в командах рассчитаны на текущий каталог mlops_lab.",
    )
    add_fig(
        doc,
        "R30_project_tree.png",
        "Дерево каталога mlops_lab в проводнике IDE",
        "Видны data/, exported_model/, mlruns/, src/, Dockerfile, compose.yaml и файлы requirements*.",
    )

    # ---- 4 ----
    add_h(doc, "4. Последовательность выполнения работы")
    add_p(
        doc,
        "Ниже приведена фактическая последовательность шагов, выполненная при подготовке "
        "лабораторной работы варианта 21. Команды запускались из каталога mlops_lab при "
        "активированном виртуальном окружении. Для Tracking использовался отдельный терминал "
        "с MLflow UI; обучение и экспорт — второй терминал с переменной MLFLOW_TRACKING_URI.",
    )
    add_h(doc, "4.1. Создание окружения и запуск MLflow", size=14)
    add_p(
        doc,
        "Сначала создано виртуальное окружение Python 3.10 и установлены зависимости из "
        "requirements.txt. Затем скриптом download_seeds.py загружен (или проверен) сырой файл "
        "Seeds и выведена контрольная сумма. Локальный MLflow Tracking Server поднят на "
        "адресе 127.0.0.1:5000 с backend SQLite (mlflow.db) и каталогом артефактов mlartifacts. "
        "В рабочем терминале задана переменная окружения MLFLOW_TRACKING_URI, после чего "
        "доступность сервера проверена обращением к /health. Использовались команды:",
    )
    for cmd in [
        "py -3.10 -m venv .venv",
        ".\\.venv\\Scripts\\Activate.ps1",
        "python -m pip install -U pip",
        "python -m pip install -r requirements.txt",
        "python scripts\\download_seeds.py",
        "powershell -ExecutionPolicy Bypass -File .\\scripts\\start_mlflow.ps1",
        "$env:MLFLOW_TRACKING_URI='http://127.0.0.1:5000'",
        "curl.exe -f http://127.0.0.1:5000/health",
    ]:
        add_cmd(doc, cmd)
    add_p(
        doc,
        "Согласованные имена сущностей: эксперимент Tracking — lab4-seeds; модель в Registry — "
        "seeds-classifier; Docker-образы сервиса — seeds-api:v1 (базовый champion) и "
        "seeds-api:v2 (демонстрация обновления). Эти имена используются во всех скриптах и "
        "скринах отчёта, чтобы избежать путаницы при проверке.",
    )

    add_h(doc, "4.2. Проведение экспериментов", size=14)
    add_p(
        doc,
        "Выполнены шесть поисковых запусков с различными гиперпараметрами в соответствии с "
        "вариантом 21: LogisticRegression с параметром регуляризации C ∈ {0.1, 1, 10} и "
        "KNeighborsClassifier с числом соседей n_neighbors ∈ {3, 5, 11}. Для каждого run в "
        "MLflow записаны: параметры алгоритма, random_state, схема разбиения и версии пакетов; "
        "метрики train/val (accuracy, macro F1, precision, recall и F1 по классам Kama/Rosa/"
        "Canadian); теги variant=21, dataset=uci-seeds, algorithm, stage=train, data_sha256; "
        "артефакты split.json, confusion_matrix_val.png/.json, classification_report_val.txt, "
        "params.json, metrics.json и сама модель со signature/input example.",
    )
    add_p(
        doc,
        "Для поисковой сетки (терминал B при работающем MLflow и заданном MLFLOW_TRACKING_URI) "
        "использовались команды:",
    )
    for cmd in [
        "python -m src.train --algorithm lr --C 0.1",
        "python -m src.train --algorithm lr --C 1",
        "python -m src.train --algorithm lr --C 10",
        "python -m src.train --algorithm knn --n-neighbors 3",
        "python -m src.train --algorithm knn --n-neighbors 5",
        "python -m src.train --algorithm knn --n-neighbors 11",
    ]:
        add_cmd(doc, cmd)
    add_p(
        doc,
        "Каждый завершённый run печатает run_id и model_uri. Ошибочные (FAILED) запуски в "
        "сравнение не включались. После сравнения по val_f1_macro лучшие настройки каждого "
        "семейства регистрируются отдельно (раздел 7), затем выполняются назначение champion, "
        "экспорт снимка и итоговая оценка на test:",
    )
    for cmd in [
        "python -m src.promote --best --alias champion",
        "python -m src.export_model",
        "python -m src.evaluate",
    ]:
        add_cmd(doc, cmd)
    add_p(
        doc,
        "Имена run могут быть похожими (например, knn-k-3 и knn-k-3-register), поэтому в "
        "таблицах и при защите идентификация ведётся по полному run_id. Скриншоты ниже "
        "фиксируют список экспериментов, карточку champion-run, состав артефактов и "
        "результаты итоговой оценки/экспорта.",
    )
    add_fig(
        doc,
        "R04_mlflow_runs.png",
        "Эксперимент lab4-seeds: список успешных запусков в MLflow UI",
        "В списке видны шесть поисковых run, два регистрационных и evaluate-champion.",
    )
    add_fig(
        doc,
        "03_mlflow_experiments.png",
        "Дополнительный кадр списка запусков lab4-seeds (обзор эксперимента)",
        "Кадр подтверждает наличие не менее шести успешных прогонов с разными гиперпараметрами.",
    )
    add_fig(
        doc,
        "R05_run_detail.png",
        "Карточка запуска knn-k-3-register (champion): метрики и параметры",
        "На overview зафиксированы val_f1_macro≈0.9521, n_neighbors=3, split 60/20/20, random_state=42.",
    )
    add_fig(
        doc,
        "R06_artifacts.png",
        "Артефакты запуска: split.json, confusion matrix, metrics/params",
        "Артефакты подтверждают, что в run сохранены не только метрики, но и файлы для аудита разбиения.",
    )
    add_fig(
        doc,
        "R05b_cm.png",
        "Матрица ошибок champion на отложенной test-выборке",
        "Ошибается только класс Kama (4 объекта из 14); Rosa и Canadian распознаны полностью.",
    )
    add_fig(
        doc,
        "R20_export_metrics.png",
        "Результат export_model и итоговые test-метрики champion",
        "В metadata зафиксированы version=2, run_id champion и val_f1_macro; test_f1_macro=0.9000.",
    )
    add_fig(
        doc,
        "R24_runs_again.png",
        "Повторный обзор запусков lab4-seeds в UI MLflow",
        "Кадр дополнительно подтверждает наличие поисковых и регистрационных run.",
    )

    # ---- 5 ----
    add_h(doc, "5. Сравнение экспериментов")
    add_p(
        doc,
        "Сравнение экспериментов выполнялось строго по заранее выбранной метрике val_f1_macro. "
        "Значения test на этом этапе не использовались и даже не вычислялись для поисковых run, "
        "чтобы исключить неявный подбор гиперпараметров по отложенной выборке. В таблице 4 "
        "приведены шесть обязательных поисковых запусков: алгоритм, ключевой гиперпараметр, "
        "две validation-метрики и полный идентификатор run_id. Дополнительно в таблице 5 "
        "собраны все run, включая регистрационные и evaluate-champion.",
    )
    add_table(
        doc,
        ["Прогон", "Алгоритм / гиперпараметр", "val_f1_macro", "val_accuracy", "run_id"],
        [
            ["lr-C-0.1", "LogisticRegression, C=0.1", "0.8792", "0.8810", "e9f1eb7c500943dab86cdd1a1b11bfd6"],
            ["lr-C-1", "LogisticRegression, C=1", "0.9027", "0.9048", "16e34abc385f49fdbb626d844493a62e"],
            ["lr-C-10", "LogisticRegression, C=10", "0.9263", "0.9286", "7ac894ca3a4f461e8fc7a22bf8e88b45"],
            ["knn-k-3", "KNN, n_neighbors=3", "0.9521", "0.9524", "c130e6a8ccf74307a81287222ba98fa5"],
            ["knn-k-5", "KNN, n_neighbors=5", "0.9007", "0.9048", "e5baa6754bd040fda75ba22f96242484"],
            ["knn-k-11", "KNN, n_neighbors=11", "0.8774", "0.8810", "32c75f5cedee4f74a4aa74e5ab820896"],
        ],
        "Таблица 4 – Сравнение не менее шести экспериментов на validation",
    )
    add_p(
        doc,
        "Наблюдения по семейству LogisticRegression. При увеличении C (ослаблении L2-регуляризации) "
        "val_f1_macro растёт: 0.8792 → 0.9027 → 0.9263. Одновременно при C=10 train_f1_macro "
        "достигает 1.0, то есть модель идеально разделяет обучающую часть. Это типичный признак "
        "сильной подстройки под train: validation остаётся высоким, но уже заметно ниже train. "
        "Тем не менее среди LR именно C=10 даёт лучший validation и поэтому регистрируется как "
        "версия 1 (challenger для демонстрации update/rollback).",
    )
    add_p(
        doc,
        "Наблюдения по семейству KNN. При увеличении числа соседей validation монотонно падает: "
        "0.9521 (k=3) → 0.9007 (k=5) → 0.8774 (k=11). На компактных, но частично пересекающихся "
        "кластерах Seeds широкая окрестность начинает смешивать сорта, особенно Kama. Лучший "
        "результат всей сетки — KNeighborsClassifier с k=3: val_f1_macro=0.9521 при "
        "val_accuracy=0.9524. Разница с лучшей LR составляет около 0.026 macro-F1 на validation.",
    )
    add_p(
        doc,
        "Диаграммы ниже дублируют таблицу в наглядной форме: ранжирование по val_f1_macro, "
        "сопоставление train/val, F1 по классам и кривые зависимости от гиперпараметров. "
        "Скриншоты Charts из MLflow UI подтверждают те же соотношения метрик, что и расчёт "
        "по артефактам экспериментов.",
    )
    add_table(
        doc,
        ["Роль", "Прогон", "Полный run_id"],
        [
            ["поиск", "lr-C-0.1", "e9f1eb7c500943dab86cdd1a1b11bfd6"],
            ["поиск", "lr-C-1", "16e34abc385f49fdbb626d844493a62e"],
            ["поиск", "lr-C-10", "7ac894ca3a4f461e8fc7a22bf8e88b45"],
            ["поиск", "knn-k-3", "c130e6a8ccf74307a81287222ba98fa5"],
            ["поиск", "knn-k-5", "e5baa6754bd040fda75ba22f96242484"],
            ["поиск", "knn-k-11", "32c75f5cedee4f74a4aa74e5ab820896"],
            ["реестр v1", "lr-C-10-register", "e1c6f836bcd742b185476f96181b1121"],
            ["реестр v2 / champion", "knn-k-3-register", "aa59daab8a5e4aad8284069caf47dcd4"],
            ["итоговая оценка", "evaluate-champion", "a48e140c1b5e4a068288b253d49e7c0d"],
        ],
        "Таблица 4а – Идентификаторы запусков (run_id) в MLflow",
    )
    add_p(
        doc,
        "Для отчёта и защиты удобно ссылаться именно на run_id, а не на совпадающие имена run. "
        "Регистрационные прогоны lr-C-10-register и knn-k-3-register повторили validation-метрики "
        "поисковых запусков с теми же гиперпараметрами (0.9263 и 0.9521 соответственно). Это "
        "подтверждает детерминированность Pipeline при фиксированном разбиении, одинаковом "
        "random_state и неизменном сыром файле данных.",
    )
    add_fig(
        doc,
        "G01_val_f1_macro.png",
        "Столбчатая диаграмма val_f1_macro по шести поисковым запускам",
        "Лучший результат — knn-k-3 (0.9521); худшие — lr-C-0.1 и knn-k-11.",
    )
    add_fig(
        doc,
        "G02_train_vs_val.png",
        "Сопоставление train_f1_macro и val_f1_macro",
        "У LR C=10 train=1.0 при заметно более низком validation — признак переобучения.",
    )
    add_fig(
        doc,
        "G03_val_f1_per_class.png",
        "F1 по классам на validation (Kama / Rosa / Canadian)",
        "Класс Rosa почти всегда распознаётся лучше остальных; Kama — самый сложный.",
    )
    add_fig(
        doc,
        "G04_hyperparams.png",
        "Влияние гиперпараметров: C у LR и k у KNN",
        "Рост C улучшает LR; рост k ухудшает KNN на данном разбиении.",
    )
    add_fig(
        doc,
        "R29_mlflow_charts_val_macro.png",
        "Сравнение в MLflow UI: val_f1_macro / precision / recall",
        "Встроенные bar-charts Tracking UI подтверждают те же ранжирования прогонов.",
    )
    add_fig(
        doc,
        "R28_mlflow_charts_val_f1.png",
        "MLflow UI: val_accuracy и F1 по сортам на validation",
        "Наглядно видно преимущество knn-k-3 и lr-C-10-register по validation.",
    )
    add_fig(
        doc,
        "R27_mlflow_charts_train.png",
        "MLflow UI: train-метрики по запускам",
        "Train-графики дополняют анализ переобучения (особенно LR C=10).",
    )

    # ---- 6 ----
    add_h(doc, "6. Обоснование выбора модели и итоговая оценка")
    add_p(
        doc,
        "Правило выбора модели было зафиксировано до просмотра test-выборки и не менялось по "
        "ходу экспериментов: 1) максимум val_f1_macro; 2) при равенстве — большая val_accuracy; "
        "3) при дальнейшем равенстве — предпочтение более простой/стабильной конфигурации. "
        "По этому правилу победителем стал KNeighborsClassifier с n_neighbors=3. Он "
        "зарегистрирован как версия 2 модели seeds-classifier (run_id "
        "aa59daab8a5e4aad8284069caf47dcd4) и получил alias champion. Лучшая логистическая "
        "регрессия (C=10) сохранена как версия 1 для последующей демонстрации обновления и "
        "отката. Выбор KNN обусловлен не только формальным максимумом метрики, но и тем, что "
        "при близком качестве LR C=10 демонстрирует идеальный train (признак переобучения), "
        "тогда как у KNN k=3 разрыв train/val умеренный.",
    )
    add_p(
        doc,
        "После назначения champion модель экспортирована командой python -m src.export_model. "
        "Каталог exported_model/ содержит файлы формата MLflow Model (MLmodel, model.pkl, "
        "conda.yaml/requirements, signature) и служебный lab_metadata.json с номером версии, "
        "run_id и val_f1_macro. Параллельно сформированы sample_request.json (три объекта с "
        "семью признаками) и expected_predictions.json (эталонные метки и имена классов). "
        "Эти файлы далее используются и для ручной проверки curl, и для автоматического "
        "smoke-теста src.check_api внутри/снаружи контейнера.",
    )
    add_table(
        doc,
        ["Метрика", "Значение на test (n=42)"],
        [
            ["test_accuracy", f"{m['test_accuracy']:.6f}"],
            ["test_f1_macro", f"{m['test_f1_macro']:.6f}"],
            ["test_precision_macro", f"{m['test_precision_macro']:.6f}"],
            ["test_recall_macro", f"{m['test_recall_macro']:.6f}"],
            ["test_f1 Kama / Rosa / Canadian", "0.833 / 0.933 / 0.933"],
        ],
        "Таблица 5 – Итоговая оценка модели seeds-classifier@champion (версия 2)",
    )
    add_p(
        doc,
        "Итоговая независимая оценка на test (n=42) дала accuracy 0.9048 и macro-F1 0.9000 "
        "(таблица 6). По классам: F1(Kama)=0.833, F1(Rosa)=0.933, F1(Canadian)=0.933. Матрица "
        "ошибок показывает, что Rosa и Canadian распознаны полностью (по 14 из 14), а все "
        "ошибки относятся к Kama (4 объекта: 2 предсказаны как Rosa и 2 как Canadian). Это "
        "согласуется с PCA-проекцией, где Kama частично перекрывается с соседними сортами.",
    )
    add_p(
        doc,
        "Дополнительная проверка целостности: прогнозы каталога exported_model и URI "
        "models:/seeds-classifier@champion на всей test-выборке совпали "
        "(registry_predictions_match: true в results/test_metrics.json). Таким образом, "
        "экспортированный снимок действительно соответствует champion в Registry. Подчеркнём: "
        "test не использовался для подбора гиперпараметров и не влиял на выбор alias.",
    )
    add_fig(
        doc,
        "G05_test_metrics.png",
        "Сводка test-метрик champion (accuracy / F1 / precision / recall)",
        "Macro-F1 на test = 0.900; F1 класса Kama ниже остальных (0.833).",
    )
    add_fig(
        doc,
        "G06_confusion_test.png",
        "Матрица ошибок champion на test (построенная по артефактам evaluate)",
        "Ошибки только у Kama (4 объекта): 2 → Rosa и 2 → Canadian.",
    )
    add_fig(
        doc,
        "R26_mlflow_charts_test.png",
        "MLflow UI Charts: test-метрики run evaluate-champion",
        "В Tracking UI зафиксированы test_accuracy≈0.90 и per-class F1 (Kama/Rosa/Canadian).",
    )

    # ---- 7 ----
    add_h(doc, "7. Регистрация версий модели и назначение alias champion")
    add_p(
        doc,
        "Для регистрации моделей были выполнены два дополнительных запуска с флагом "
        "--register: для лучшей логистической регрессии (C=10) и для выбранного KNN "
        "(n_neighbors=3). Обе версии относятся к одной зарегистрированной модели "
        "seeds-classifier (рисунки 25–27). Использовались команды:",
    )
    for cmd in [
        "python -m src.train --algorithm lr --C 10 --register",
        "python -m src.train --algorithm knn --n-neighbors 3 --register",
        "python -m src.promote --best --alias champion",
    ]:
        add_cmd(doc, cmd)
    add_p(
        doc,
        "В результате в Model Registry появились версия 1 (LogisticRegression C=10, "
        "run e1c6f836bcd742b185476f96181b1121, val_f1_macro≈0.9263) и версия 2 "
        "(KNeighborsClassifier k=3, run aa59daab8a5e4aad8284069caf47dcd4, "
        "val_f1_macro≈0.9521). Команда promote --best назначила alias champion версии с "
        "наибольшим val_f1_macro, то есть версии 2. Alias не создаёт новую модель и не "
        "копирует веса заново, а лишь меняет именованный указатель на уже существующую "
        "версию. Поэтому дальнейшее обновление и откат выполняются без повторного обучения.",
    )
    add_p(
        doc,
        "Экспорт для Docker резолвит URI models:/seeds-classifier@champion в конкретный номер "
        "версии на момент выгрузки. Если после смены alias не выполнить export_model и не "
        "пересобрать образ, контейнер продолжит обслуживать старый снимок. Поэтому в работе "
        "разделены понятия «версия в Registry», «содержимое exported_model/» и «тег Docker-образа».",
    )
    add_table(
        doc,
        ["Версия", "Алгоритм", "val_f1_macro", "run_id", "Alias"],
        [
            ["1", "LogisticRegression C=10", "0.926284", "e1c6f836bcd742b185476f96181b1121", "—"],
            ["2", "KNN k=3", "0.952137", "aa59daab8a5e4aad8284069caf47dcd4", "champion"],
        ],
        "Таблица 6 – Версии в MLflow Model Registry",
    )
    add_fig(
        doc,
        "R07_registry.png",
        "Model Registry: seeds-classifier, две версии, alias @champion на версии 2",
        "В описании модели указан вариант 21 и классы Kama/Rosa/Canadian; у версии 2 теги algorithm=knn и val_f1_macro.",
    )
    add_fig(
        doc,
        "06_registry_versions.png",
        "Карточка реестра с тегами версий 1 и 2",
        "Версия 1: algorithm=lr, val_f1_macro=0.926284; версия 2: algorithm=knn, alias champion.",
    )
    add_fig(
        doc,
        "07_alias_champion.png",
        "Подтверждение alias champion → Version 2 в списке Models",
        "Alias читается как models:/seeds-classifier@champion и резолвится в конкретный номер при экспорте.",
    )
    add_fig(
        doc,
        "R22_version2.png",
        "Страница Version 2: source run knn-k-3-register, alias @champion, теги",
        "На странице версии видны описание с val_f1_macro и связь с исходным run.",
    )
    add_fig(
        doc,
        "R23_version1.png",
        "Страница Version 1: source run lr-C-10-register (вторая зарегистрированная версия)",
        "Версия 1 нужна для демонстрации обновления/отката без повторного обучения.",
    )
    add_fig(
        doc,
        "R12_alias_history.png",
        "История смены alias champion без повторного обучения",
        "Alias переносился на версию 1 (update) и возвращался на версию 2 (rollback); новых fit не выполнялось.",
    )
    add_fig(
        doc,
        "R21_alias_history.png",
        "Журнал alias_history.jsonl (initial / update / rollback)",
        "Файл фиксирует время, номер версии и note без новых train-run.",
    )

    # ---- 8 ----
    add_h(doc, "8. Описание API и проверка запросов")
    add_p(
        doc,
        "Сервис предсказаний реализован на FastAPI (файл src/app.py) и предназначен для "
        "пакетного scoring по контракту, близкому к распространённым MLflow/serving-схемам. "
        "Формат входных данных POST /predict — JSON-объект вида "
        "{\"instances\":[{...}, {...}, ...]}, где каждый элемент массива instances содержит "
        "ровно семь числовых признаков с фиксированными именами: area, perimeter, compactness, "
        "length_of_kernel, width_of_kernel, asymmetry_coefficient, length_of_kernel_groove. "
        "Лишние поля запрещены (extra=forbid), типы строго числовые; пустой массив instances "
        "также считается ошибкой валидации.",
    )
    add_p(
        doc,
        "Формат ответа POST /predict включает: predictions — список целочисленных меток "
        "классов (1/2/3); class_names — текстовые имена сортов; model_version — номер версии "
        "модели из metadata снимка; latency_ms — время инференса внутри обработчика. "
        "Эндпоинт GET /health возвращает status=ok и model_version и используется healthcheck "
        "Compose. Эндпоинт GET /metadata отдаёт перечень признаков, карту классов, algorithm, "
        "alias и run_id — это удобно для проверки, какая именно модель сейчас обслуживается.",
    )
    add_p(
        doc,
        "Проверка корректных запросов: GET /health и /metadata возвращают HTTP 200; "
        "POST /predict с sample_request.json возвращает predictions=[1, 3, 2] "
        "(Kama, Canadian, Rosa), что совпадает с expected_predictions.json; скрипт "
        "python -m src.check_api завершается сообщением SMOKE_OK. Проверка некорректных "
        "запросов: пустой instances, отсутствие обязательного поля, строка/null/bool вместо "
        "числа, лишнее поле — всё это даёт HTTP 422 (валидация Pydantic), а не 500. "
        "Обращение методом GET к /predict возвращает 405. Результаты сведены в таблице 8 "
        "и подтверждены скриншотами Swagger, curl и 422-ответов.",
    )
    add_fig(
        doc,
        "R08_swagger.png",
        "Интерактивная документация Swagger UI (/docs)",
        "В описании API явно указан вариант 21 и эндпоинты /health, /metadata, /predict.",
    )
    add_fig(
        doc,
        "R25_swagger_predict.png",
        "Раскрытый POST /predict в Swagger: формат instances и Try it out",
        "В примере тела запроса показаны семь числовых признаков одного объекта.",
    )
    add_fig(
        doc,
        "R08_health.png",
        "Ответ GET /health из работающего контейнера",
        "status=ok, model_version=2 соответствует champion.",
    )
    add_fig(
        doc,
        "R09_metadata.png",
        "Ответ GET /metadata: семь признаков и карта классов",
        "Список features совпадает с таблицей 1; algorithm=knn, alias=champion.",
    )
    add_fig(
        doc,
        "R10_predict.png",
        "Корректный POST /predict и совпадение с expected_predictions.json",
        "predictions=[1,3,2] (Kama, Canadian, Rosa). Скрипт check_api.py завершился SMOKE_OK.",
    )
    add_fig(
        doc,
        "R11_422.png",
        "Некорректные запросы: пустой instances и неполный объект → HTTP 422",
        "Это демонстрирует контролируемую валидацию входа (не 500).",
    )
    add_fig(
        doc,
        "R19_422_more.png",
        "Дополнительные 422: строка вместо числа и лишнее поле",
        "Pydantic отклоняет нечисловые значения и неизвестные ключи при extra=forbid.",
    )
    add_table(
        doc,
        ["Запрос", "Ожидание", "Факт"],
        [
            ["GET /health", "200", "200"],
            ["GET /metadata", "200", "200"],
            ["POST /predict (3 instances)", "200, [1,3,2]", "200, [1,3,2]"],
            ["POST {\"instances\":[]}", "422", "422"],
            ["POST без обязательного поля", "422", "422"],
            ["POST с лишним полем / строкой / null / bool", "422", "422"],
            ["GET /predict", "405", "405"],
        ],
        "Таблица 7 – Результаты проверки корректных и некорректных запросов",
    )

    # ---- 9 ----
    add_h(doc, "9. Сборка и запуск Docker-контейнера")
    add_p(
        doc,
        "Контейнеризация выполнена по схеме «снимок модели + лёгкий runtime». Dockerfile "
        "берёт базовый образ python:3.12-slim, устанавливает зависимости из "
        "requirements-serve.txt (через зеркало PyPI для ускорения сборки), копирует пакет "
        "src/ и каталог exported_model/, создаёт непривилегированного пользователя appuser и "
        "запускает uvicorn src.app:app. Путь к модели задаётся переменной окружения MODEL_PATH "
        "и по умолчанию указывает на /app/exported_model. Важно: в runtime не монтируется "
        "mlruns и не требуется доступный Tracking Server — предсказания строятся только по "
        "локальному model.pkl, упакованному на этапе export.",
    )
    add_p(
        doc,
        "Сборка и запуск выполнялись через Docker Compose (тот же compose.yaml, что и для "
        "healthcheck), чтобы не дублировать параметры порта и переменных окружения. После "
        "подъёма контейнера выполнялись проверки /health, /metadata, /predict и автоматический "
        "smoke-тест check_api.py. Совпадение предсказаний API с экспортированной моделью "
        "подтверждено: ответ контейнера на sample_request.json равен эталону "
        "expected_predictions.json (predictions=[1,3,2]), статус SMOKE_OK. "
        "Использовались команды:",
    )
    for cmd in [
        "$env:IMAGE_TAG='v1'",
        "docker compose build",
        "docker images seeds-api",
        "docker compose up -d",
        "docker compose ps",
        "curl.exe -f http://127.0.0.1:8000/health",
        "curl.exe -f http://127.0.0.1:8000/metadata",
        "curl.exe -f -X POST http://127.0.0.1:8000/predict -H \"Content-Type: application/json\" --data-binary @sample_request.json",
        "python -m src.check_api",
    ]:
        add_cmd(doc, cmd)
    add_p(
        doc,
        "Внутри контейнера uvicorn слушает 0.0.0.0:8000, на хосте порт опубликован только как "
        "127.0.0.1:8000. Это соответствует методичке: сервис доступен локально для проверки, "
        "без отдельной аутентификации и без публикации «наружу» на 0.0.0.0 хоста. Тег образа "
        "seeds-api:v1 соответствует снимку champion (версия модели 2, KNN k=3). Позднее для "
        "демо обновления был собран отдельный тег seeds-api:v2 с другим Image ID.",
    )
    add_fig(
        doc,
        "R13_build.png",
        "Успешная сборка образа seeds-api:v1",
        "В логе видны установка зависимостей и naming to docker.io/library/seeds-api:v1.",
    )
    add_fig(
        doc,
        "R14_images.png",
        "Локальные образы seeds-api:v1 и seeds-api:v2 с разными Image ID",
        "Тег образа и номер версии модели — разные идентификаторы; фактическая версия хранится в metadata.",
    )

    # ---- 10 ----
    add_h(doc, "10. Обновление и откат")
    add_p(
        doc,
        "Требование методички — показать обновление и откат модели без повторного обучения. "
        "Сценарий обновления: alias champion временно назначен уже существующей версии 1 "
        "(LogisticRegression C=10); затем выполнен export_model и собран образ seeds-api:v2. "
        "После старта GET /metadata вернул model_version=1; check_api прошёл для нового "
        "эталона. Новых запусков train/fit не выполнялось. Использовались команды:",
    )
    for cmd in [
        "python -m src.promote --version 1 --alias champion",
        "python -m src.export_model",
        "$env:IMAGE_TAG='v2'",
        "docker compose build",
        "docker compose up -d",
        "curl.exe -f http://127.0.0.1:8000/metadata",
        "python -m src.check_api",
    ]:
        add_cmd(doc, cmd)
    add_p(
        doc,
        "Сценарий отката: контейнер v2 остановлен; снова поднят уже сохранённый образ "
        "seeds-api:v1 (пересборка не нужна); alias champion возвращён на версию 2; выполнен "
        "export для согласования эталона. После отката /metadata снова показал "
        "model_version=2, check_api подтвердил predictions=[1,3,2]. Журнал смен alias "
        "сохранён в alias_history.jsonl (рисунки 30–31). Использовались команды:",
    )
    for cmd in [
        "docker compose down",
        "$env:IMAGE_TAG='v1'",
        "docker compose up -d",
        "python -m src.promote --version 2 --alias champion",
        "python -m src.export_model",
        "curl.exe -f http://127.0.0.1:8000/metadata",
        "python -m src.check_api",
    ]:
        add_cmd(doc, cmd)
    add_p(
        doc,
        "Таким образом, обновление и откат опираются на две оси версионирования: номер "
        "версии в Model Registry и тег/ID Docker-образа (таблица 9).",
    )
    add_table(
        doc,
        ["Тег образа", "Image ID", "Версия модели", "Алгоритм", "Назначение"],
        [
            ["seeds-api:v1", "ff598d6a86e0", "2", "KNN k=3", "champion / откат"],
            ["seeds-api:v2", "543808a01516", "1", "LogisticRegression C=10", "демо обновления"],
        ],
        "Таблица 8 – Соответствие тегов Docker-образов и версий Model Registry",
    )

    # ---- 11 ----
    add_h(doc, "11. Запуск через Docker Compose и проверка healthcheck")
    add_p(
        doc,
        "Файл compose.yaml описывает единственный сервис seeds-api в проекте seeds-mlops. "
        "Ключевые параметры: образ seeds-api:${IMAGE_TAG:-v1}; публикация порта "
        "127.0.0.1:8000:8000; политика restart: unless-stopped; переменная MODEL_PATH; "
        "healthcheck, который каждые 10 секунд выполняет внутри контейнера запрос к "
        "http://127.0.0.1:8000/health (через python urllib). Параметры start_period / retries "
        "дают сервису время на загрузку model.pkl до первых проверок. Команда "
        "docker compose up -d поднимает контейнер в фоне; docker compose ps показывает "
        "переход STATUS из starting в healthy.",
    )
    add_p(
        doc,
        "Проверка healthcheck выполнялась двумя способами. Во-первых, встроенный механизм "
        "Compose меняет состояние контейнера на healthy — это видно в docker compose ps. "
        "Во-вторых, с хоста выполнялся curl к /health, который возвращал "
        "{\"status\":\"ok\",\"model_version\":\"2\"}. Дополнительно снимались логи и "
        "docker stats. Полный текст compose.yaml — в приложении Г. Использовались команды:",
    )
    for cmd in [
        "$env:IMAGE_TAG='v1'",
        "docker compose up -d",
        "docker compose ps",
        "curl.exe -f http://127.0.0.1:8000/health",
        "docker compose logs --tail 40 seeds-api",
        "docker stats --no-stream seeds-api",
        "python -m src.check_api",
    ]:
        add_cmd(doc, cmd)
    add_fig(
        doc,
        "R15_compose.png",
        "docker compose ps: STATUS healthy и проверка /health",
        "Healthcheck выполняется внутри контейнера; внешний curl подтверждает тот же ответ.",
    )
    add_fig(
        doc,
        "R16_stats.png",
        "Минимальная эксплуатационная проверка: ресурсы и latency_ms",
        "latency_ms измеряет предсказание в обработчике; полный сетевой round-trip больше.",
    )
    add_fig(
        doc,
        "R17_compose_logs.png",
        "Журнал контейнера docker compose logs (startup /predict)",
        "В логах видны старт uvicorn и обработка запросов без падений приложения.",
    )
    add_fig(
        doc,
        "R18_docker_stats.png",
        "docker stats --no-stream для сервиса seeds-api",
        "Кадр фиксирует фактическое потребление CPU/RAM учебного контейнера.",
    )
    add_p(
        doc,
        "Таким образом, обязательные этапы Compose выполнены: сервис поднят декларативно из "
        "конфигурационного файла, healthcheck переводит контейнер в состояние healthy, внешние "
        "проверки /health и check_api подтверждают готовность модели к обслуживанию запросов. "
        "Это замыкает контур MLOps лабораторной работы: от эксперимента до эксплуатируемого "
        "контейнерного сервиса с наблюдаемым статусом здоровья.",
    )

    # ---- 12 ----
    add_h(doc, "12. Воспроизводимость")
    add_p(
        doc,
        "Воспроизводимость результатов обеспечивается фиксацией всех критичных входов "
        "эксперимента. Сырой файл data/raw/seeds_dataset.txt сопровождается SHA-256 "
        f"{digest}; разбиение задано random_state=42, stratify и артефактом split.json; "
        "зависимости зафиксированы в requirements.txt, requirements.lock.txt и "
        "requirements-serve.txt; выбранная модель идентифицируется run_id "
        "aa59daab8a5e4aad8284069caf47dcd4, версией Registry 2 и alias champion; контейнеры "
        "идентифицируются тегами seeds-api:v1/v2 и Image ID. Повторный запуск train-скриптов "
        "при том же сыром файле и тех же версиях пакетов воспроизводит validation-метрики "
        "поисковой сетки; повторный export+check_api воспроизводит эталонные предсказания.",
    )
    add_p(
        doc,
        "Для проверяющего достаточно: поднять MLflow, убедиться в наличии эксперимента "
        "lab4-seeds и модели seeds-classifier@champion, собрать/запустить compose-сервис и "
        "выполнить check_api. Полные тексты Dockerfile, compose.yaml, зависимостей и примеров "
        "запросов приведены в приложениях.",
    )

    # ---- conclusions ----
    add_h(doc, "Выводы по работе")
    add_p(
        doc,
        "В ходе лабораторной работы № 4 по индивидуальному варианту 21 выполнен полный учебный "
        "контур MLOps: учёт экспериментов, выбор и регистрация модели, экспорт, API, Docker/"
        "Compose, обновление и откат. Основные результаты сформулированы ниже.",
    )
    add_p(
        doc,
        "1. На сетке из шести экспериментов (LR с C∈{0.1,1,10} и KNN с k∈{3,5,11}) лучший "
        "результат по заранее выбранной метрике val_f1_macro показал KNeighborsClassifier с "
        "тремя соседями (0.9521). Логистическая регрессия улучшается с ростом C (до 0.9263), "
        "но остаётся ниже KNN k=3; при C=10 наблюдается идеальный train, что указывает на "
        "переобучение относительно validation.",
    )
    add_p(
        doc,
        "2. Итоговая независимая оценка champion на отложенном test (n=42): accuracy 0.9048, "
        "macro-F1 0.9000, precision/recall macro ≈ 0.917/0.905. Ошибки сосредоточены в классе "
        "Kama; Rosa и Canadian распознаны полностью. Test не использовался при выборе модели.",
    )
    add_p(
        doc,
        "3. В Model Registry зарегистрированы две версии seeds-classifier; alias champion "
        "указывает на версию 2 (KNN k=3). Экспорт в exported_model/ и HTTP API доставляют "
        "именно этот снимок; прогнозы экспорта и Registry на test совпали.",
    )
    add_p(
        doc,
        "4. Сервис FastAPI в Docker Compose имеет STATUS healthy. Корректные запросы "
        "(/health, /metadata, /predict) отрабатывают успешно и совпадают с "
        "expected_predictions.json; некорректные тела запросов стабильно дают HTTP 422.",
    )
    add_p(
        doc,
        "5. Обновление до образа seeds-api:v2 (модель версии 1) и откат к seeds-api:v1 "
        "(модель версии 2) выполнены без повторного обучения — за счёт смены alias champion "
        "и тегов Docker-образов. Это подтверждает практический смысл версионирования моделей "
        "и контейнеров в MLOps.",
    )
    add_p(
        doc,
        "6. Воспроизводимость обеспечена фиксацией хеша данных, seed/разбиения, зависимостей, "
        "run_id, номера версии Registry и идентификаторов образов. Полученный конвейер "
        "соответствует требованиям методических указаний лабораторной работы № 4.",
    )

    add_h(doc, "Список использованных источников")
    for s in [
        "1. Charytanowicz M. et al. Seeds [Dataset] // UCI Machine Learning Repository. – URL: https://archive.ics.uci.edu/dataset/236/seeds (дата обращения: 10.11.2026).",
        "2. MLflow Tracking Server // MLflow Documentation. – URL: https://mlflow.org/docs/latest/self-hosting/architecture/tracking-server/ (дата обращения: 10.11.2026).",
        "3. MLflow Model Registry Tutorials // MLflow Documentation. – URL: https://mlflow.org/docs/latest/ml/model-registry/tutorial/ (дата обращения: 10.11.2026).",
        "4. MLflow sklearn API // MLflow Documentation. – URL: https://mlflow.org/docs/latest/api_reference/python_api/mlflow.sklearn.html (дата обращения: 10.11.2026).",
        "5. Common pitfalls and recommended practices // scikit-learn. – URL: https://scikit-learn.org/stable/common_pitfalls.html (дата обращения: 10.11.2026).",
        "6. Metrics and scoring: quantifying the quality of predictions // scikit-learn. – URL: https://scikit-learn.org/stable/modules/model_evaluation.html (дата обращения: 10.11.2026).",
        "7. Request Body // FastAPI. – URL: https://fastapi.tiangolo.com/tutorial/body/ (дата обращения: 10.11.2026).",
        "8. Dockerfile reference // Docker Docs. – URL: https://docs.docker.com/reference/dockerfile/ (дата обращения: 10.11.2026).",
        "9. Compose file reference: services / healthcheck // Docker Docs. – URL: https://docs.docker.com/reference/compose-file/services/ (дата обращения: 10.11.2026).",
        "10. Лабораторная работа 4. MLOps: учёт экспериментов в MLflow, реестр моделей, развёртывание сервиса предсказаний в Docker: методические указания. – 2026. – 42 с.",
    ]:
        add_p(doc, s, size=14, indent=False)

    # ---- appendix ----
    add_h(doc, "Приложение. Исходный код, зависимости, Dockerfile, Compose и примеры запросов")
    add_p(
        doc,
        "Согласно требованиям к отчёту ниже приведены: файлы зависимостей; Dockerfile; "
        "конфигурация Docker Compose; примеры корректного запроса и эталонного ответа API; "
        "полный исходный код основных модулей проекта (каталог src/). Тексты соответствуют "
        "файлам в каталоге mlops_lab на момент подготовки отчёта.",
    )
    add_p(doc, "Содержание приложений:", indent=False)
    for item in [
        "А. requirements.txt — зависимости обучения и MLflow Tracking;",
        "Б. requirements-serve.txt — зависимости Docker-образа API;",
        "В. requirements.lock.txt — полный снимок версий окружения хоста;",
        "Г. Dockerfile — сборка образа seeds-api;",
        "Д. compose.yaml — запуск сервиса и healthcheck;",
        "Е. Примеры HTTP-запросов (curl) и тел JSON — корректные и некорректные;",
        "Ж. sample_request.json — файл эталонного тела POST /predict;",
        "З. expected_predictions.json — эталон ответа для check_api;",
        "И. .dockerignore — исключение лишнего из контекста сборки;",
        "К. src/common.py — загрузка данных, константы, общие утилиты;",
        "Л. src/train.py — обучение, логирование в MLflow, регистрация;",
        "М. src/promote.py — назначение alias champion;",
        "Н. src/export_model.py — экспорт снимка модели;",
        "О. src/evaluate.py — итоговая оценка на test;",
        "П. src/app.py — FastAPI-сервис предсказаний;",
        "Р. src/check_api.py — проверка API и совпадение с эталоном.",
    ]:
        add_p(doc, "– " + item, indent=False)

    def read_text(rel: str) -> str:
        return (ROOT / rel).read_text(encoding="utf-8")

    add_code(doc, "Приложение А. requirements.txt", read_text("requirements.txt"))
    add_code(doc, "Приложение Б. requirements-serve.txt", read_text("requirements-serve.txt"))
    add_code(doc, "Приложение В. requirements.lock.txt", read_text("requirements.lock.txt"))
    add_code(doc, "Приложение Г. Dockerfile", read_text("Dockerfile"))
    add_code(doc, "Приложение Д. compose.yaml", read_text("compose.yaml"))
    add_h(doc, "Приложение Е. Примеры запросов к API", size=14)
    add_p(
        doc,
        "Ниже приведены примеры корректных и некорректных HTTP-запросов к сервису "
        "seeds-api (база http://127.0.0.1:8000). Корректный POST /predict использует файл "
        "sample_request.json (приложение Ж); эталон предсказаний — expected_predictions.json "
        "(приложение З).",
    )
    add_p(doc, "1) Корректные запросы (ожидается HTTP 200):", indent=False)
    add_cmd(doc, "curl.exe -f http://127.0.0.1:8000/health")
    add_cmd(doc, "curl.exe -f http://127.0.0.1:8000/metadata")
    add_cmd(
        doc,
        "curl.exe -f -X POST http://127.0.0.1:8000/predict -H \"Content-Type: application/json\" --data-binary @sample_request.json",
    )
    add_code(
        doc,
        "Тело корректного POST /predict (один объект; полный файл — в приложении Ж)",
        '{\n'
        '  "instances": [\n'
        '    {\n'
        '      "area": 14.29,\n'
        '      "perimeter": 14.09,\n'
        '      "compactness": 0.905,\n'
        '      "length_of_kernel": 5.291,\n'
        '      "width_of_kernel": 3.337,\n'
        '      "asymmetry_coefficient": 2.699,\n'
        '      "length_of_kernel_groove": 4.825\n'
        '    }\n'
        '  ]\n'
        '}',
    )
    add_p(doc, "Ожидаемый результат для полного sample_request.json (три объекта):", indent=False)
    add_cmd(doc, 'predictions = [1, 3, 2]   # Kama, Canadian, Rosa')
    add_p(doc, "2) Некорректные тела POST /predict (ожидается HTTP 422):", indent=False)
    add_code(
        doc,
        "Пустой массив instances",
        '{\n  "instances": []\n}',
    )
    add_code(
        doc,
        "Отсутствует обязательное поле length_of_kernel_groove",
        '{\n'
        '  "instances": [\n'
        '    {\n'
        '      "area": 15.26,\n'
        '      "perimeter": 14.84,\n'
        '      "compactness": 0.871,\n'
        '      "length_of_kernel": 5.763,\n'
        '      "width_of_kernel": 3.312,\n'
        '      "asymmetry_coefficient": 2.221\n'
        '    }\n'
        '  ]\n'
        '}',
    )
    add_code(
        doc,
        "Строка вместо числа и лишнее поле",
        '{\n'
        '  "instances": [\n'
        '    {\n'
        '      "area": "15.26",\n'
        '      "perimeter": 14.84,\n'
        '      "compactness": 0.871,\n'
        '      "length_of_kernel": 5.763,\n'
        '      "width_of_kernel": 3.312,\n'
        '      "asymmetry_coefficient": 2.221,\n'
        '      "length_of_kernel_groove": 5.22,\n'
        '      "extra": 1\n'
        '    }\n'
        '  ]\n'
        '}',
    )
    add_p(doc, "3) Неверный метод (ожидается HTTP 405):", indent=False)
    add_cmd(doc, "curl.exe -i http://127.0.0.1:8000/predict")

    add_code(doc, "Приложение Ж. sample_request.json (полный файл)", read_text("sample_request.json"))
    add_code(doc, "Приложение З. expected_predictions.json", read_text("expected_predictions.json"))
    dockerignore = ROOT / ".dockerignore"
    if dockerignore.is_file():
        add_code(doc, "Приложение И. .dockerignore", dockerignore.read_text(encoding="utf-8"))
    add_code(doc, "Приложение К. Исходный код src/common.py", read_text("src/common.py"))
    add_code(doc, "Приложение Л. Исходный код src/train.py", read_text("src/train.py"))
    add_code(doc, "Приложение М. Исходный код src/promote.py", read_text("src/promote.py"))
    add_code(doc, "Приложение Н. Исходный код src/export_model.py", read_text("src/export_model.py"))
    add_code(doc, "Приложение О. Исходный код src/evaluate.py", read_text("src/evaluate.py"))
    add_code(doc, "Приложение П. Исходный код src/app.py", read_text("src/app.py"))
    add_code(doc, "Приложение Р. Исходный код src/check_api.py", read_text("src/check_api.py"))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"Wrote {OUT}")
    for alt in (OUT_DESKTOP, ROOT.parent / "Отчет_ЛР4_MLOps_вариант21_полный.docx"):
        try:
            doc.save(alt)
            print(f"Wrote {alt}")
        except PermissionError:
            print(f"SKIP locked: {alt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
