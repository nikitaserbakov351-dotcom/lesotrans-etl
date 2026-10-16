# -*- coding: utf-8 -*-
"""
Набор из 28 автоматических модульных тестов для пакета lesotrans-etl.
Выполняется полностью оффлайн без внешних сетевых запросов (для GitHub Actions CI).
"""
import unittest
import json
import os
from lesotrans_etl.models import ShipmentRecord, TechMapCheckInput
from lesotrans_etl.compliance import (
    check_species_prohibited,
    validate_logging_operation,
    PROHIBITED_SPECIES_ORDER_102,
)
from lesotrans_etl.etl import ForestFreightETL
from lesotrans_etl.forecast import fit_ols_trend, next_year_month, build_seasonal_forecast
from lesotrans_etl.cli import main as cli_main


class TestComplianceOrder102And23(unittest.TestCase):
    """Тесты нормативного контроля по Приказам Минприроды России № 102 и № 23."""

    def test_01_registry_has_56_prohibited_species(self):
        self.assertEqual(len(PROHIBITED_SPECIES_ORDER_102), 56)
        trees = [x for x in PROHIBITED_SPECIES_ORDER_102 if x["category"] == "tree"]
        shrubs = [x for x in PROHIBITED_SPECIES_ORDER_102 if x["category"] == "shrub"]
        self.assertEqual(len(trees), 50)
        self.assertEqual(len(shrubs), 6)

    def test_02_detects_prohibited_karelian_birch_ru(self):
        res = check_species_prohibited("Берёза карельская")
        self.assertIsNotNone(res)
        self.assertEqual(res["id"], 4)

    def test_03_detects_prohibited_korean_pine_ru_and_lat(self):
        res_ru = check_species_prohibited("Кедр корейский")
        res_lat = check_species_prohibited("Pinus koraiensis")
        self.assertIsNotNone(res_ru)
        self.assertIsNotNone(res_lat)
        self.assertEqual(res_ru["id"], 37)
        self.assertEqual(res_lat["id"], 37)

    def test_04_detects_prohibited_amur_cork_tree(self):
        res = check_species_prohibited("Бархат амурский")
        self.assertIsNotNone(res)
        self.assertEqual(res["id"], 2)

    def test_05_detects_prohibited_yew_and_walnut(self):
        self.assertEqual(check_species_prohibited("Taxus baccata")["id"], 44)
        self.assertEqual(check_species_prohibited("Орех маньчжурский")["id"], 28)

    def test_06_detects_prohibited_shrubs(self):
        self.assertEqual(check_species_prohibited("Калина Райта")["id"], 52)
        self.assertEqual(check_species_prohibited("Экзохорда пильчатолистная")["id"], 56)

    def test_07_allows_industrial_species(self):
        for sp in ["Сосна обыкновенная", "Ель европейская", "Береза повислая", "Лиственница сибирская", "Осина"]:
            self.assertIsNone(check_species_prohibited(sp), f"Ошибочная блокировка разрешенной породы: {sp}")

    def test_08_generic_genus_name_does_not_false_trigger(self):
        self.assertIsNone(check_species_prohibited("Сосна"))
        self.assertIsNone(check_species_prohibited("Береза"))

    def test_09_empty_species_query_returns_none(self):
        self.assertIsNone(check_species_prohibited("   "))

    def test_10_valid_tech_map_passes_order_23(self):
        inp = TechMapCheckInput(
            cutting_area_id="LES-2026-01",
            forestry_unit="Тихвинское",
            species_name="Сосна обыкновенная",
            volume_m3=350.0,
        )
        rep = validate_logging_operation(inp)
        self.assertTrue(rep.is_compliant)
        self.assertEqual(len(rep.violations), 0)

    def test_11_missing_tech_map_fails_order_23(self):
        inp = TechMapCheckInput(
            cutting_area_id="LES-2026-02",
            forestry_unit="Выборгское",
            species_name="Ель европейская",
            volume_m3=200.0,
            has_tech_map=False,
        )
        rep = validate_logging_operation(inp)
        self.assertFalse(rep.is_compliant)
        self.assertTrue(any("технологическая карта" in v for v in rep.violations))

    def test_12_wrong_stage_sequence_fails_order_23(self):
        inp = TechMapCheckInput(
            cutting_area_id="LES-2026-03",
            forestry_unit="Приозерское",
            species_name="Сосна обыкновенная",
            volume_m3=150.0,
            stages_completed=["main", "preparatory", "final"],
        )
        rep = validate_logging_operation(inp)
        self.assertFalse(rep.is_compliant)
        self.assertTrue(any("последовательность" in v for v in rep.violations))

    def test_13_missing_final_inspection_act_fails_order_23(self):
        inp = TechMapCheckInput(
            cutting_area_id="LES-2026-04",
            forestry_unit="Гатчинское",
            species_name="Сосна обыкновенная",
            volume_m3=180.0,
            has_final_inspection_act=False,
        )
        rep = validate_logging_operation(inp)
        self.assertFalse(rep.is_compliant)
        self.assertTrue(any("акт заключительного осмотра" in v for v in rep.violations))

    def test_14_unprepared_skid_trails_fail_order_23(self):
        inp = TechMapCheckInput(
            cutting_area_id="LES-2026-05",
            forestry_unit="Тихвинское",
            species_name="Сосна обыкновенная",
            volume_m3=180.0,
            skid_trail_markup_done=False,
        )
        rep = validate_logging_operation(inp)
        self.assertFalse(rep.is_compliant)


class TestETLPipelineAndSQLite(unittest.TestCase):
    """Тесты очистки данных, дедупликации и SQLite-агрегаций."""

    def test_15_shipment_record_computed_properties(self):
        rec = ShipmentRecord(
            shipment_id="S1",
            date="2026-10-01",
            month="2026-10",
            origin_forestry="Тихвинское",
            destination_hub="Парголово",
            species="Сосна обыкновенная",
            volume_m3=100.0,
            weight_tons=75.0,
            distance_km=200.0,
            freight_cost_rub=150000.0,
        )
        self.assertEqual(rec.ton_km, 15000.0)
        self.assertEqual(rec.unit_cost_rub_per_m3_km, 7.5)

    def test_16_etl_deduplication_and_filtering(self):
        etl = ForestFreightETL(":memory:")
        raw = [
            {"shipment_id": "A1", "date": "2026-01-10", "volume_m3": 100, "weight_tons": 70, "distance_km": 150, "freight_cost_rub": 120000},
            {"shipment_id": "A1", "date": "2026-01-10", "volume_m3": 100, "weight_tons": 70, "distance_km": 150, "freight_cost_rub": 120000},
            {"shipment_id": "", "date": "2026-01-10", "volume_m3": 100, "weight_tons": 70, "distance_km": 150, "freight_cost_rub": 120000},
            {"shipment_id": "A2", "date": "2026-02-10", "volume_m3": -10, "weight_tons": 70, "distance_km": 150, "freight_cost_rub": 120000},
            {"shipment_id": "A3", "date": "bad", "volume_m3": 100, "weight_tons": 70, "distance_km": 150, "freight_cost_rub": 120000},
        ]
        cleaned, rejected = etl.transform_raw_records(raw)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(len(rejected), 4)

    def test_17_etl_sqlite_load_and_kpis(self):
        etl = ForestFreightETL(":memory:")
        raw = [
            {"shipment_id": "S1", "date": "2026-01-15", "species": "Сосна обыкновенная", "volume_m3": 200, "weight_tons": 150, "distance_km": 100, "freight_cost_rub": 160000, "has_tech_map": True, "has_final_act": True},
            {"shipment_id": "S2", "date": "2026-02-15", "species": "Береза карельская", "volume_m3": 100, "weight_tons": 80, "distance_km": 100, "freight_cost_rub": 90000, "has_tech_map": True, "has_final_act": True},
        ]
        res = etl.run_pipeline(raw)
        self.assertEqual(res["loaded_count"], 2)
        self.assertEqual(res["kpis"]["total_volume_m3"], 300.0)
        self.assertEqual(res["kpis"]["compliant_shipments"], 1)
        self.assertEqual(res["kpis"]["compliance_rate_pct"], 50.0)

    def test_18_monthly_series_ordering(self):
        etl = ForestFreightETL(":memory:")
        raw = [
            {"shipment_id": "S2", "date": "2026-03-10", "volume_m3": 150, "weight_tons": 110, "distance_km": 100, "freight_cost_rub": 100000},
            {"shipment_id": "S1", "date": "2026-01-10", "volume_m3": 120, "weight_tons": 90, "distance_km": 100, "freight_cost_rub": 80000},
        ]
        etl.run_pipeline(raw)
        series = etl.get_monthly_series()
        self.assertEqual([s["month"] for s in series], ["2026-01", "2026-03"])


class TestForecastEngine(unittest.TestCase):
    """Тесты модели прогнозирования временных рядов (OLS + сезонность)."""

    def test_19_ols_exact_linear_fit(self):
        slope, intercept = fit_ols_trend([100.0, 110.0, 120.0, 130.0])
        self.assertAlmostEqual(slope, 10.0, places=5)
        self.assertAlmostEqual(intercept, 100.0, places=5)

    def test_20_ols_single_element(self):
        slope, intercept = fit_ols_trend([250.0])
        self.assertEqual(slope, 0.0)
        self.assertEqual(intercept, 250.0)

    def test_21_ols_empty_raises(self):
        with self.assertRaises(ValueError):
            fit_ols_trend([])

    def test_22_next_year_month_rollover(self):
        self.assertEqual(next_year_month("2026-10", 3), "2027-01")
        self.assertEqual(next_year_month("2026-12", 1), "2027-01")

    def test_23_seasonal_forecast_metrics_and_horizon(self):
        months = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
        vols = [295.0, 365.0, 395.0, 415.0, 398.0, 355.0]
        fc = build_seasonal_forecast(months, vols, horizon=4, use_seasonality=True)
        self.assertEqual(len(fc.forecast_points), 4)
        self.assertEqual(fc.forecast_points[0]["month"], "2026-11")
        self.assertEqual(fc.forecast_points[-1]["month"], "2027-02")
        self.assertGreaterEqual(fc.r2, 0.7)
        self.assertLess(fc.mape_pct, 15.0)

    def test_24_forecast_without_seasonality_zero_error_on_line(self):
        months = ["2026-01", "2026-02", "2026-03", "2026-04"]
        vols = [100.0, 120.0, 140.0, 160.0]
        fc = build_seasonal_forecast(months, vols, horizon=2, use_seasonality=False)
        self.assertEqual(fc.mae, 0.0)
        self.assertEqual(fc.rmse, 0.0)
        self.assertEqual(fc.r2, 1.0)
        self.assertEqual(fc.forecast_points[0]["predicted_volume_m3"], 180.0)

    def test_25_forecast_invalid_length_raises(self):
        with self.assertRaises(ValueError):
            build_seasonal_forecast(["2026-01"], [100.0])


class TestCLIAndDemoDataset(unittest.TestCase):
    """Тесты CLI и демонстрационного набора данных СПб и ЛО."""

    def test_26_demo_dataset_loads_cleanly(self):
        demo_path = os.path.join(os.path.dirname(__file__), "..", "data", "demo_shipments_spb_lenobl.json")
        with open(demo_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        etl = ForestFreightETL(":memory:")
        res = etl.run_pipeline(raw)
        self.assertEqual(res["loaded_count"], 10)
        self.assertEqual(res["kpis"]["compliant_shipments"], 8)

    def test_27_cli_check_species_runs(self):
        code = cli_main(["check-species", "--species", "Бархат амурский"])
        self.assertEqual(code, 0)

    def test_28_cli_ingest_runs(self):
        demo_path = os.path.join(os.path.dirname(__file__), "..", "data", "demo_shipments_spb_lenobl.json")
        code = cli_main(["ingest", "--input", demo_path])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
