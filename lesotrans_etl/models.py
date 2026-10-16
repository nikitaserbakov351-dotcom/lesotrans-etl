# -*- coding: utf-8 -*-
"""Модели данных партий лесоматериалов, рейсов, тендеров и технологических карт."""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class TechMapCheckInput:
    """Данные технологической карты лесосечных работ (Приказ Минприроды РФ от 17.01.2022 № 23)."""
    cutting_area_id: str
    forestry_unit: str
    species_name: str
    volume_m3: float
    has_tech_map: bool = True
    has_forest_declaration: bool = True
    has_final_inspection_act: bool = True
    stages_completed: List[str] = field(default_factory=lambda: ["preparatory", "main", "final"])
    skid_trail_markup_done: bool = True
    emergency_trees_cleared: bool = True


@dataclass
class ShipmentRecord:
    """Запись о лесопромышленной перевозке / лоте открытых данных."""
    shipment_id: str
    date: str  # YYYY-MM-DD
    month: str  # YYYY-MM
    origin_forestry: str
    destination_hub: str
    species: str
    volume_m3: float
    weight_tons: float
    distance_km: float
    freight_cost_rub: float
    tender_id: Optional[str] = None
    has_tech_map: bool = True
    has_final_act: bool = True

    @property
    def ton_km(self) -> float:
        return round(self.weight_tons * self.distance_km, 2)

    @property
    def unit_cost_rub_per_m3_km(self) -> float:
        denom = self.volume_m3 * self.distance_km
        if denom <= 0:
            return 0.0
        return round(self.freight_cost_rub / denom, 4)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["ton_km"] = self.ton_km
        d["unit_cost_rub_per_m3_km"] = self.unit_cost_rub_per_m3_km
        return d
