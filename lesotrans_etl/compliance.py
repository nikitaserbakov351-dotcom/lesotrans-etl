# -*- coding: utf-8 -*-
"""
Модуль нормативного контроля лесосечных работ и породного состава древесины.

Основания:
1. Приказ Минприроды России от 14.03.2025 № 102 (вступил в силу 01.09.2025, действует до 01.09.2031)
   «Об утверждении перечня видов (пород) деревьев и кустарников, заготовка древесины которых не допускается».
2. Приказ Минприроды России от 17.01.2022 № 23 (действует с 01.09.2022 до 01.09.2028)
   «Об утверждении видов лесосечных работ, порядка и последовательности их выполнения,
   формы технологической карты лесосечных работ, формы акта заключительного осмотра лесосеки...».
3. Лесной кодекс Российской Федерации от 04.12.2006 № 200-ФЗ (ст. 19, 23.2, 29).
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from .models import TechMapCheckInput


# Реестр запрещенных к заготовке видов по Приказу Минприроды РФ от 14.03.2025 № 102
PROHIBITED_SPECIES_ORDER_102: List[Dict[str, str]] = [
    {"id": 1, "ru": "Абрикос", "lat": "Armeniaca Scop.", "category": "tree"},
    {"id": 2, "ru": "Бархат амурский", "lat": "Phellodendron amurense", "category": "tree"},
    {"id": 3, "ru": "Бархат сахалинский", "lat": "Phellodendron sachalinense", "category": "tree"},
    {"id": 4, "ru": "Береза карельская", "lat": "Betula pendula Roth var. carelica", "category": "tree"},
    {"id": 5, "ru": "Береза Максимовича", "lat": "Betula maximowicziana", "category": "tree"},
    {"id": 6, "ru": "Береза Радде", "lat": "Betula raddeana", "category": "tree"},
    {"id": 7, "ru": "Береза Шмидта", "lat": "Betula schmidtii", "category": "tree"},
    {"id": 8, "ru": "Ботрокариум спорный", "lat": "Bothrocaryum controversum", "category": "tree"},
    {"id": 9, "ru": "Вишня", "lat": "Cerasus Mill.", "category": "tree"},
    {"id": 10, "ru": "Груша", "lat": "Pyrus L.", "category": "tree"},
    {"id": 11, "ru": "Дзельква", "lat": "Zelkova carpinifolia", "category": "tree"},
    {"id": 12, "ru": "Дуб зубчатый", "lat": "Quercus dentata", "category": "tree"},
    {"id": 13, "ru": "Дуб курчавый", "lat": "Quercus crispula", "category": "tree"},
    {"id": 14, "ru": "Ель Глена", "lat": "Picea glehnii", "category": "tree"},
    {"id": 15, "ru": "Калопанакс семилопастный (диморфант)", "lat": "Kalopanax septemlobus", "category": "tree"},
    {"id": 16, "ru": "Каштан посевной", "lat": "Castanea sativa", "category": "tree"},
    {"id": 17, "ru": "Клен ложноплатановый (белый, явор)", "lat": "Acer pseudoplatanus", "category": "tree"},
    {"id": 18, "ru": "Клен японский", "lat": "Acer japonicum", "category": "tree"},
    {"id": 19, "ru": "Лапина крылоплодная", "lat": "Pterocarya pterocarpa", "category": "tree"},
    {"id": 20, "ru": "Липа Максимовича", "lat": "Tilia maximowicziana", "category": "tree"},
    {"id": 21, "ru": "Лиственница ольгинская", "lat": "Larix olgensis", "category": "tree"},
    {"id": 22, "ru": "Магнолия снизу-белая", "lat": "Magnolia hypoleuca", "category": "tree"},
    {"id": 23, "ru": "Мелкоплодник ольхолистный (рябина ольхолистная)", "lat": "Micromeles alnifolia", "category": "tree"},
    {"id": 24, "ru": "Можжевельник вонючий", "lat": "Juniperus foetidissima", "category": "tree"},
    {"id": 25, "ru": "Можжевельник высокий", "lat": "Juniperus excelsa", "category": "tree"},
    {"id": 26, "ru": "Можжевельник твердый", "lat": "Juniperus rigida", "category": "tree"},
    {"id": 27, "ru": "Орех айлантолистный", "lat": "Juglans ailanthifolia", "category": "tree"},
    {"id": 28, "ru": "Орех маньчжурский", "lat": "Juglans mandshurica", "category": "tree"},
    {"id": 29, "ru": "Орех грецкий", "lat": "Juglans regia", "category": "tree"},
    {"id": 30, "ru": "Орех медвежий (лещина древовидная)", "lat": "Corylus colurna", "category": "tree"},
    {"id": 31, "ru": "Пихта Майра", "lat": "Abies mayriana", "category": "tree"},
    {"id": 32, "ru": "Пихта цельнолистная (маньчжурская)", "lat": "Abies holophylla", "category": "tree"},
    {"id": 33, "ru": "Пихта грациозная", "lat": "Abies gracilis", "category": "tree"},
    {"id": 34, "ru": "Платан восточный", "lat": "Platanus orientalis", "category": "tree"},
    {"id": 35, "ru": "Самшит", "lat": "Buxus L.", "category": "tree"},
    {"id": 36, "ru": "Слива растопыренная (алыча)", "lat": "Prunus divaricata", "category": "tree"},
    {"id": 37, "ru": "Сосна корейская (кедр корейский)", "lat": "Pinus koraiensis", "category": "tree"},
    {"id": 38, "ru": "Сосна густоцветная", "lat": "Pinus densiflora", "category": "tree"},
    {"id": 39, "ru": "Сосна меловая", "lat": "Pinus sylvestris var. cretacea", "category": "tree"},
    {"id": 40, "ru": "Сосна могильная", "lat": "Pinus funebris", "category": "tree"},
    {"id": 41, "ru": "Сосна Палласа", "lat": "Pinus pallasiana", "category": "tree"},
    {"id": 42, "ru": "Сосна пицундская", "lat": "Pinus pityusa", "category": "tree"},
    {"id": 43, "ru": "Тис остроконечный", "lat": "Taxus cuspidata", "category": "tree"},
    {"id": 44, "ru": "Тис ягодный", "lat": "Taxus baccata", "category": "tree"},
    {"id": 45, "ru": "Фисташка туполистная", "lat": "Pistacia mutica", "category": "tree"},
    {"id": 46, "ru": "Хмелеграб обыкновенный", "lat": "Ostrya carpinifolia", "category": "tree"},
    {"id": 47, "ru": "Хурма обыкновенная", "lat": "Diospyros lotus", "category": "tree"},
    {"id": 48, "ru": "Шелковица (тут)", "lat": "Morus L.", "category": "tree"},
    {"id": 49, "ru": "Яблоня", "lat": "Malus Mill.", "category": "tree"},
    {"id": 50, "ru": "Ясень шерстистый (ясень Зибольда)", "lat": "Fraxinus lanuginosa", "category": "tree"},
    {"id": 51, "ru": "Жимолость Толмачева", "lat": "Lonicera tolmatchevii", "category": "shrub"},
    {"id": 52, "ru": "Калина Райта", "lat": "Viburnum wrightii", "category": "shrub"},
    {"id": 53, "ru": "Клекачка колхидская", "lat": "Staphylea colchica", "category": "shrub"},
    {"id": 54, "ru": "Клекачка перистая", "lat": "Staphylea pinnata", "category": "shrub"},
    {"id": 55, "ru": "Падуб Сугероки", "lat": "Ilex sugerokii", "category": "shrub"},
    {"id": 56, "ru": "Экзохорда пильчатолистная", "lat": "Exochorda serratifolia", "category": "shrub"},
]

REQUIRED_STAGE_ORDER = ["preparatory", "main", "final"]


@dataclass
class ComplianceReport:
    """Результат проверки технологической карты и партии древесины."""
    is_compliant: bool
    prohibited_species_match: Optional[Dict[str, str]] = None
    violations: List[str] = field(default_factory=list)
    legal_references: List[str] = field(default_factory=list)


def check_species_prohibited(species_query: str) -> Optional[Dict[str, str]]:
    """
    Проверяет, входит ли порода древесины или кустарника в Перечень видов,
    заготовка древесины которых не допускается (Приказ Минприроды РФ от 14.03.2025 № 102).
    """
    q = species_query.strip().lower().replace("ё", "е")
    if not q:
        return None

    # Разрешенные промышленные виды по умолчанию (если не указан запрещенный подвид):
    # Например, «Сосна обыкновенная (Pinus sylvestris)» разрешена, но «Сосна меловая (Pinus sylvestris var. cretacea)» запрещена.
    safe_industrial = {
        "сосна обыкновенная", "pinus sylvestris",
        "ель европейская", "picea abies",
        "береза повислая", "береза пушистая", "betula pendula", "betula pubescens",
        "лиственница сибирская", "larix sibirica",
        "осина", "populus tremula",
        "ольха черная", "ольха серая", "alnus glutinosa", "alnus incana",
        "дуб черешчатый", "quercus robur",
    }
    if q in safe_industrial:
        return None

    for item in PROHIBITED_SPECIES_ORDER_102:
        ru_norm = item["ru"].lower().replace("ё", "е")
        lat_norm = item["lat"].lower()
        if q == ru_norm or q == lat_norm:
            return item
        # Проверка вхождения ключевого названия (например, «береза карельская» или «кедр корейский»)
        if len(q) >= 4 and (q in ru_norm or ru_norm in q or q in lat_norm):
            # Защита от ложного срабатывания просто «сосна» или «береза» без видового эпитета
            if q in {"сосна", "береза", "ель", "дуб", "лиственница", "пихта", "клен", "липа", "ясень"}:
                continue
            return item
    return None


def validate_logging_operation(data: TechMapCheckInput) -> ComplianceReport:
    """
    Комплексная проверка лесосечных работ и партии древесины на соответствие:
    - ч. 7 ст. 29 Лесного кодекса РФ и Приказу Минприроды России от 14.03.2025 № 102;
    - ч. 10 ст. 23.2 Лесного кодекса РФ и Приказу Минприроды России от 17.01.2022 № 23.
    """
    violations: List[str] = []
    refs: List[str] = []

    match = check_species_prohibited(data.species_name)
    if match is not None:
        violations.append(
            f"Запрещенная к заготовке порода: «{match['ru']}» ({match['lat']}), п. {match['id']} Перечня."
        )
        refs.append("Приказ Минприроды России от 14.03.2025 № 102; ч. 7 ст. 29 Лесного кодекса РФ № 200-ФЗ")

    if not data.has_tech_map:
        violations.append(
            "Отсутствует технологическая карта лесосечных работ (нарушение п. 3, 4 Приложения № 1 к Приказу № 23)."
        )
        refs.append("Приказ Минприроды России от 17.01.2022 № 23 (Приложение № 2)")

    if not data.has_forest_declaration:
        violations.append(
            "Отсутствует лесная декларация / проект освоения лесов (нарушение п. 4 Приложения № 1 к Приказу № 23)."
        )
        refs.append("Лесной кодекс РФ от 04.12.2006 № 200-ФЗ (ст. 26); Приказ Минприроды России № 23")

    if data.stages_completed != REQUIRED_STAGE_ORDER:
        violations.append(
            "Нарушена обязательная последовательность лесосечных работ: подготовительные -> основные -> заключительные (п. 5 Приложения № 1 к Приказу № 23)."
        )
        refs.append("Приказ Минприроды России от 17.01.2022 № 23 (п. 5 Приложения № 1)")

    if not data.skid_trail_markup_done or not data.emergency_trees_cleared:
        violations.append(
            "Не выполнены обязательные подготовительные работы: разметка границ волоков/погрузочных пунктов и уборка аварийных деревьев (п. 6 Приложения № 1 к Приказу № 23)."
        )
        refs.append("Приказ Минприроды России от 17.01.2022 № 23 (п. 6 Приложения № 1)")

    if not data.has_final_inspection_act:
        violations.append(
            "Отсутствует акт заключительного осмотра лесосеки (Приложение № 3 и № 4 к Приказу № 23)."
        )
        refs.append("Приказ Минприроды России от 17.01.2022 № 23 (Приложения № 3, № 4)")

    if data.volume_m3 <= 0:
        violations.append("Объем партии древесины должен быть строго положительным (м³ > 0).")

    return ComplianceReport(
        is_compliant=(len(violations) == 0),
        prohibited_species_match=match,
        violations=violations,
        legal_references=sorted(list(set(refs))),
    )
