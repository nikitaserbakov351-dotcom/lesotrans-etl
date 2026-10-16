# -*- coding: utf-8 -*-
"""
ETL-конвейер открытых данных о лесопромышленных перевозках и закупках:
Extract (JSON/CSV) -> Transform (очистка, дедупликация, нормативный фильтр) -> Load (SQLite).
"""
import sqlite3
import json
from typing import List, Dict, Any, Tuple
from .models import ShipmentRecord
from .compliance import check_species_prohibited


class ForestFreightETL:
    """Конвейер извлечения, трансформации и загрузки данных в SQLite."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS shipments (
                shipment_id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                month TEXT NOT NULL,
                origin_forestry TEXT NOT NULL,
                destination_hub TEXT NOT NULL,
                species TEXT NOT NULL,
                volume_m3 REAL NOT NULL,
                weight_tons REAL NOT NULL,
                distance_km REAL NOT NULL,
                freight_cost_rub REAL NOT NULL,
                ton_km REAL NOT NULL,
                unit_cost_rub_per_m3_km REAL NOT NULL,
                tender_id TEXT,
                has_tech_map INTEGER NOT NULL,
                has_final_act INTEGER NOT NULL,
                is_compliant INTEGER NOT NULL,
                compliance_note TEXT
            )
            """
        )
        self.conn.commit()

    def transform_raw_records(
        self, raw_rows: List[Dict[str, Any]]
    ) -> Tuple[List[ShipmentRecord], List[Dict[str, Any]]]:
        """
        Очищает сырые записи, отбрасывает дубликаты и некорректные строки,
        возвращает список валидных записей и лог отбракованных строк.
        """
        seen_ids = set()
        cleaned: List[ShipmentRecord] = []
        rejected: List[Dict[str, Any]] = []

        for row in raw_rows:
            sid = str(row.get("shipment_id", "")).strip()
            if not sid:
                rejected.append({"row": row, "reason": "missing_shipment_id"})
                continue
            if sid in seen_ids:
                rejected.append({"row": row, "reason": "duplicate_shipment_id"})
                continue

            try:
                vol = float(row.get("volume_m3", 0))
                weight = float(row.get("weight_tons", 0))
                dist = float(row.get("distance_km", 0))
                cost = float(row.get("freight_cost_rub", 0))
            except (TypeError, ValueError):
                rejected.append({"row": row, "reason": "invalid_numeric_fields"})
                continue

            if vol <= 0 or weight <= 0 or dist <= 0 or cost <= 0:
                rejected.append({"row": row, "reason": "non_positive_metrics"})
                continue

            date_str = str(row.get("date", "")).strip()
            if len(date_str) < 7:
                rejected.append({"row": row, "reason": "invalid_date"})
                continue
            month_str = date_str[:7]

            seen_ids.add(sid)
            rec = ShipmentRecord(
                shipment_id=sid,
                date=date_str,
                month=month_str,
                origin_forestry=str(row.get("origin_forestry", "Неизвестное лесничество")).strip(),
                destination_hub=str(row.get("destination_hub", "Терминал СПб")).strip(),
                species=str(row.get("species", "Сосна обыкновенная")).strip(),
                volume_m3=round(vol, 2),
                weight_tons=round(weight, 2),
                distance_km=round(dist, 2),
                freight_cost_rub=round(cost, 2),
                tender_id=row.get("tender_id"),
                has_tech_map=bool(row.get("has_tech_map", True)),
                has_final_act=bool(row.get("has_final_act", True)),
            )
            cleaned.append(rec)

        return cleaned, rejected

    def load_records(self, records: List[ShipmentRecord]) -> int:
        """Загружает очищенные записи в таблицу SQLite с автоматической проверкой НПА."""
        cur = self.conn.cursor()
        inserted = 0
        for r in records:
            prohibited = check_species_prohibited(r.species)
            reasons = []
            if prohibited:
                reasons.append(f"Запрещенная порода (Приказ № 102 п.{prohibited['id']}: {prohibited['ru']})")
            if not r.has_tech_map:
                reasons.append("Нет техкарты лесосечных работ (Приказ № 23)")
            if not r.has_final_act:
                reasons.append("Нет акта осмотра лесосеки (Приказ № 23)")

            is_compliant = 1 if len(reasons) == 0 else 0
            note = "OK" if is_compliant else "; ".join(reasons)

            cur.execute(
                """
                INSERT OR REPLACE INTO shipments (
                    shipment_id, date, month, origin_forestry, destination_hub,
                    species, volume_m3, weight_tons, distance_km, freight_cost_rub,
                    ton_km, unit_cost_rub_per_m3_km, tender_id,
                    has_tech_map, has_final_act, is_compliant, compliance_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r.shipment_id,
                    r.date,
                    r.month,
                    r.origin_forestry,
                    r.destination_hub,
                    r.species,
                    r.volume_m3,
                    r.weight_tons,
                    r.distance_km,
                    r.freight_cost_rub,
                    r.ton_km,
                    r.unit_cost_rub_per_m3_km,
                    r.tender_id,
                    1 if r.has_tech_map else 0,
                    1 if r.has_final_act else 0,
                    is_compliant,
                    note,
                ),
            )
            inserted += 1
        self.conn.commit()
        return inserted

    def run_pipeline(self, raw_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Полный цикл ETL: очистка, загрузка в БД и возврат сводной статистики."""
        cleaned, rejected = self.transform_raw_records(raw_rows)
        loaded = self.load_records(cleaned)
        summary = self.get_summary_kpis()
        return {
            "raw_count": len(raw_rows),
            "cleaned_count": len(cleaned),
            "rejected_count": len(rejected),
            "loaded_count": loaded,
            "rejected_details": rejected,
            "kpis": summary,
        }

    def get_summary_kpis(self) -> Dict[str, Any]:
        """Агрегированные показатели по загруженным перевозкам."""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(volume_m3), 0),
                COALESCE(SUM(ton_km), 0),
                COALESCE(SUM(freight_cost_rub), 0),
                COALESCE(AVG(unit_cost_rub_per_m3_km), 0),
                COALESCE(SUM(is_compliant), 0)
            FROM shipments
            """
        )
        cnt, vol, tkm, cost, avg_unit, comp_cnt = cur.fetchone()
        comp_rate = round((comp_cnt / cnt) * 100.0, 1) if cnt > 0 else 0.0
        return {
            "total_shipments": cnt,
            "total_volume_m3": round(vol, 2),
            "total_ton_km": round(tkm, 2),
            "total_freight_cost_rub": round(cost, 2),
            "avg_unit_cost_rub_m3_km": round(avg_unit, 4),
            "compliant_shipments": comp_cnt,
            "compliance_rate_pct": comp_rate,
        }

    def get_monthly_series(self) -> List[Dict[str, Any]]:
        """Помесячный временной ряд объемов (м³) и затрат (руб.) для прогнозной модели."""
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT month, ROUND(SUM(volume_m3), 2) AS vol, ROUND(SUM(freight_cost_rub), 2) AS cost, COUNT(*)
            FROM shipments
            GROUP BY month
            ORDER BY month ASC
            """
        )
        rows = cur.fetchall()
        return [
            {"month": r[0], "volume_m3": r[1], "freight_cost_rub": r[2], "shipments_count": r[3]}
            for r in rows
        ]
