# -*- coding: utf-8 -*-
"""
Модуль прогнозирования грузопотоков лесоматериалов и оценки точности модели.

Использует метод наименьших квадратов (OLS линейный тренд) + сезонные индексы
лесозаготовительного цикла (зимний пик вывозки по зимникам и весенняя распутица).
Вычисляет метрики качества: MAE, RMSE, MAPE (%), R^2.
"""
import math
from dataclasses import dataclass
from typing import List, Dict, Any


# Отраслевые коэффициенты сезонности вывозки древесины в СЗФО (Санкт-Петербург и ЛО)
FORESTRY_SEASONAL_INDEX: Dict[int, float] = {
    1: 1.22,   # Январь — зимняя вывозка по замерзшим волокам
    2: 1.25,   # Февраль — пик зимнего сезона
    3: 1.15,   # Март — завершение зимнего сезона
    4: 0.72,   # Апрель — весенняя распутица, просушка дорог
    5: 0.78,   # Май — ограничения нагрузки на ось
    6: 0.94,   # Июнь — летний сезон
    7: 1.00,   # Июль — стабильная летняя вывозка
    8: 1.04,   # Август — летний максимум
    9: 0.98,   # Сентябрь — начало осенних дождей
    10: 0.85,  # Октябрь — осенняя распутица
    11: 0.95,  # Ноябрь — становление зимников
    12: 1.12,  # Декабрь — открытие зимней вывозки
}


@dataclass
class ForecastResult:
    """Результат прогнозирования временного ряда."""
    horizon_months: int
    slope: float
    intercept: float
    mae: float
    rmse: float
    mape_pct: float
    r2: float
    fitted_values: List[float]
    forecast_points: List[Dict[str, Any]]


def fit_ols_trend(y: List[float]) -> tuple[float, float]:
    """Линейная регрессия y = intercept + slope * t методом наименьших квадратов."""
    n = len(y)
    if n == 0:
        raise ValueError("Временной ряд не может быть пустым.")
    if n == 1:
        return 0.0, float(y[0])

    x = list(range(n))
    mean_x = sum(x) / n
    mean_y = sum(y) / n

    num = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den = sum((x[i] - mean_x) ** 2 for i in range(n))
    slope = num / den if den > 0 else 0.0
    intercept = mean_y - slope * mean_x
    return slope, intercept


def next_year_month(ym: str, steps: int) -> str:
    """Прибавляет steps месяцев к строке формата YYYY-MM."""
    year, month = map(int, ym.split("-"))
    total = (year * 12 + (month - 1)) + steps
    ny = total // 12
    nm = (total % 12) + 1
    return f"{ny:04d}-{nm:02d}"


def build_seasonal_forecast(
    months: List[str],
    volumes: List[float],
    horizon: int = 4,
    use_seasonality: bool = True,
) -> ForecastResult:
    """
    Строит прогноз объема перевозок на `horizon` месяцев вперед с оценкой
    точности на исторической выборке (MAE, RMSE, MAPE, R²).
    """
    if len(months) != len(volumes) or len(volumes) < 2:
        raise ValueError("Требуется минимум 2 точки временного ряда (months, volumes).")

    n = len(volumes)
    # 1. Десезонализация ряда при включенной сезонности
    deseasonalized: List[float] = []
    month_nums: List[int] = []
    for m_str, val in zip(months, volumes):
        m_num = int(m_str.split("-")[1])
        month_nums.append(m_num)
        s_idx = FORESTRY_SEASONAL_INDEX.get(m_num, 1.0) if use_seasonality else 1.0
        deseasonalized.append(val / s_idx)

    # 2. Оценка линейного тренда OLS
    slope, intercept = fit_ols_trend(deseasonalized)

    # 3. Восстановление модельных значений на истории и расчет метрик
    fitted: List[float] = []
    abs_errors: List[float] = []
    sq_errors: List[float] = []
    ape_list: List[float] = []

    for i in range(n):
        trend_val = intercept + slope * i
        s_idx = FORESTRY_SEASONAL_INDEX.get(month_nums[i], 1.0) if use_seasonality else 1.0
        hat = max(0.0, round(trend_val * s_idx, 2))
        fitted.append(hat)

        err = abs(volumes[i] - hat)
        abs_errors.append(err)
        sq_errors.append(err ** 2)
        if volumes[i] > 0:
            ape_list.append((err / volumes[i]) * 100.0)

    mae = round(sum(abs_errors) / n, 2)
    rmse = round(math.sqrt(sum(sq_errors) / n), 2)
    mape = round(sum(ape_list) / len(ape_list), 2) if ape_list else 0.0

    mean_y = sum(volumes) / n
    ss_tot = sum((v - mean_y) ** 2 for v in volumes)
    ss_res = sum(sq_errors)
    r2 = round(1.0 - (ss_res / ss_tot), 4) if ss_tot > 0 else 1.0

    # 4. Прогноз на horizon шагов вперед с доверительным интервалом (±1.96 * RMSE)
    last_month = months[-1]
    forecast_points: List[Dict[str, Any]] = []
    ci_half = round(1.96 * rmse, 2)

    for step in range(1, horizon + 1):
        t_idx = n - 1 + step
        target_ym = next_year_month(last_month, step)
        target_m_num = int(target_ym.split("-")[1])
        s_idx = FORESTRY_SEASONAL_INDEX.get(target_m_num, 1.0) if use_seasonality else 1.0
        point = max(0.0, round((intercept + slope * t_idx) * s_idx, 2))
        forecast_points.append({
            "month": target_ym,
            "predicted_volume_m3": point,
            "ci_lower_m3": max(0.0, round(point - ci_half, 2)),
            "ci_upper_m3": round(point + ci_half, 2),
            "seasonal_factor": s_idx,
        })

    return ForecastResult(
        horizon_months=horizon,
        slope=round(slope, 4),
        intercept=round(intercept, 4),
        mae=mae,
        rmse=rmse,
        mape_pct=mape,
        r2=r2,
        fitted_values=fitted,
        forecast_points=forecast_points,
    )
