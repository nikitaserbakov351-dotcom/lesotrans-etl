# -*- coding: utf-8 -*-
"""Консольный интерфейс (CLI) пакета lesotrans-etl."""
import argparse
import json
import sys
from .etl import ForestFreightETL
from .compliance import TechMapCheckInput, validate_logging_operation
from .forecast import build_seasonal_forecast


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="lesotrans-etl",
        description="ETL-конвейер, прогноз грузопотоков и нормативный контроль лесоперевозок (Приказы № 23 и № 102)",
    )
    sub = parser.add_subparsers(dest="command")

    p_etl = sub.add_parser("ingest", help="Запустить ETL-пайплайн на JSON-файле")
    p_etl.add_argument("--input", required=True, help="Путь к JSON с данными рейсов")
    p_etl.add_argument("--db", default=":memory:", help="Путь к файлу SQLite БД")

    p_chk = sub.add_parser("check-species", help="Проверить породу по Приказу Минприроды № 102")
    p_chk.add_argument("--species", required=True, help="Название породы (рус. или лат.)")

    args = parser.parse_args(argv)
    if args.command == "ingest":
        with open(args.input, "r", encoding="utf-8") as f:
            raw = json.load(f)
        etl = ForestFreightETL(args.db)
        res = etl.run_pipeline(raw)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    elif args.command == "check-species":
        rep = validate_logging_operation(
            TechMapCheckInput(
                cutting_area_id="CLI-CHECK",
                forestry_unit="СПбГЛТУ-Тест",
                species_name=args.species,
                volume_m3=100.0,
            )
        )
        print(json.dumps({
            "is_compliant": rep.is_compliant,
            "prohibited_species_match": rep.prohibited_species_match,
            "violations": rep.violations,
            "legal_references": rep.legal_references,
        }, ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
