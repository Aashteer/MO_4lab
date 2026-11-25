# Docker — финальный статус (вариант 21)

- Engine: running
- seeds-api:v1 = ff598d6a86e0 (champion KNN v2)
- seeds-api:v2 = 543808a01516 (LR v1 для демо обновления)
- compose: healthy, 127.0.0.1:8000
- check_api: SMOKE_OK predictions=[1,3,2]
- update: /metadata version=1 на образе v2
- rollback: /metadata version=2 на образе v1 без переобучения
- Отчёт: report/REPORT_variant21.docx и копия на Desktop\Вуз\4laba\
