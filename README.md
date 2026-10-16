# LesoTrans-ETL — Конвейер открытых данных, прогноз грузопотоков и нормативный контроль лесоперевозок

[![CI](https://github.com/nikitaserbakov351-dotcom/lesotrans-etl/actions/workflows/ci.yml/badge.svg)](https://github.com/nikitaserbakov351-dotcom/lesotrans-etl/actions)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Tests](https://img.shields.io/badge/tests-28%20passed-brightgreen)
![Offline-First](https://img.shields.io/badge/mode-offline--first-success)

**LesoTrans-ETL** — прикладной инженерный проект на стыке **анализа данных (ETL + прогнозирование временных рядов)** и **транспортной логистики лесопользования**. Разработан как независимый программный комплекс с реляционным хранилищем SQLite, интерактивным аналитическим дашбордом и встроенным модулем нормативного контроля по актуальным приказам Минприроды России.

---

## Ключевые возможности

1. **ETL-конвейер открытых данных (`lesotrans_etl/etl.py`)**:
   - Извлечение и валидация данных о рейсах лесозаготовительных предприятий и тендерах (`data.gov.ru` / `zakupki.gov.ru`);
   - Дедупликация, отбраковка некорректных записей с журналированием причин, расчёт транспортной работы (`т·км`) и удельной ставки (`₽/м³·км`);
   - Персистентное хранение и SQL-агрегация KPI в `SQLite`.
2. **Нормативный контроль лесосечных работ и пород (`lesotrans_etl/compliance.py`)**:
   - Автоматическая сверка партий с полным перечнем из **56 запрещённых к заготовке видов деревьев и кустарников** по **Приказу Минприроды России от 14.03.2025 № 102** (русские и латинские таксоны: *Береза карельская*, *Бархат амурский*, *Сосна корейская / кедр корейский*, *Тис ягодный* и др.);
   - Проверка соблюдения очерёдности лесосечных работ (`подготовительные -> основные -> заключительные`), наличия технологической карты и акта заключительного осмотра лесосеки по **Приказу Минприроды России от 17.01.2022 № 23** и **Лесному кодексу РФ (№ 200-ФЗ)**.
3. **Прогнозная модель грузопотоков (`lesotrans_etl/forecast.py`)**:
   - Декомпозиция временного ряда на линейный тренд (МНК / OLS) и отраслевые коэффициенты сезонности вывозки древесины в СЗФО (зимники vs весенне-осенняя распутица);
   - Построение 95% доверительного интервала и расчёт метрик `MAE`, `RMSE`, `MAPE (%)`, `R²`.
4. **Интерактивный веб-дашборд (`dashboard/lesotrans_etl_dashboard.html`)**:
   - Работает в браузере без внешних зависимостей бэкенда: графики `Chart.js`, интерактивный калькулятор прогноза, проверщик технологических карт и генератор реферата Роспатента.

---

## Быстрый старт (3 команды)

```bash
# 1. Прогон всех 28 модульных тестов (оффлайн, 0 сетевых зависимостей)
python -m unittest discover -s tests -p "test_*.py" -v

# 2. Запуск ETL-пайплайна на демонстрационном массиве СПб и Ленинградской области
python -m lesotrans_etl.cli ingest --input data/demo_shipments_spb_lenobl.json

# 3. Проверка породы древесины по Приказу Минприроды России № 102
python -m lesotrans_etl.cli check-species --species "Береза карельская"
```

---

## Архитектура репозитория

```text
lesotrans-etl/
├── lesotrans_etl/
│   ├── __init__.py       # Метаданные пакета
│   ├── models.py         # Датаклассы рейсов, тендеров и техкарт
│   ├── compliance.py     # Валидатор по Приказам Минприроды № 102 и № 23 + ЛК РФ
│   ├── etl.py            # ETL-конвейер и SQLite-хранилище
│   ├── forecast.py       # Прогнозная модель OLS + сезонность (MAE, RMSE, MAPE, R²)
│   └── cli.py            # Консольный интерфейс
├── data/
│   └── demo_shipments_spb_lenobl.json  # Демо-выгрузка перевозок по лесничествам ЛО
├── docs/
│   └── rospatent_abstract_draft.md     # Черновик реферата программы для ЭВМ (ФИПС)
├── tests/
│   └── test_lesotrans_etl.py           # 28 юнит-тестов (ETL, SQLite, НПА, прогноз, CLI)
├── .github/workflows/ci.yml            # GitHub Actions CI (Python 3.11 / 3.12)
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

---

## Публикация в новый репозиторий GitHub (`nikitaserbakov351-dotcom`)

```bash
git init
git add .
git commit -m "feat: initial release of LesoTrans-ETL (ETL, seasonal forecast, Order 102/23 compliance, 28 tests)"
git branch -M main
git remote add origin https://github.com/nikitaserbakov351-dotcom/lesotrans-etl.git
git push -u origin main
```
