from __future__ import annotations
"""
WesternAstrologyCalculator — Слой 1, активный калькулятор.

Использует существующий движок из app.core.astrology.natal_chart
и добавляет расчёт аспектов, стеллиумов, полусфер — всё что нужно для DSB.
"""

import asyncio
import json
import os
import math
from datetime import datetime
from typing import Optional

from app.dsb.calculators.base import Calculator, BirthData
from app.core.astrology.natal_chart import (
    calculate_natal_chart,
    geocode_place,
    to_dict,
)


# ─── Орбы для аспектов ───────────────────────────────────────────────────────
PERSONAL_PLANETS = {"Sun", "Moon"}
INNER_PLANETS = {"Mercury", "Venus", "Mars"}
SOCIAL_PLANETS = {"Jupiter", "Saturn"}
OUTER_PLANETS = {"Uranus", "Neptune", "Pluto"}
POINTS = {"TrueNode", "Lilith", "PartFortune", "SouthNode", "Chiron"}

ORB_TABLE: dict[str, float] = {
    "personal": 10.0,
    "inner": 8.0,
    "social": 6.0,
    "outer": 5.0,
    "point": 3.0,
}

ASPECT_ANGLES: dict[str, float] = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
    "quincunx": 150.0,
    "semi_square": 45.0,
    "sesquiquadrate": 135.0,
    "quintile": 72.0,
    "biquintile": 144.0,
}

ASPECT_ORBS: dict[str, float] = {
    "quincunx": 3.0,
    "semi_square": 2.0,
    "sesquiquadrate": 2.0,
    "quintile": 2.0,
    "biquintile": 2.0,
}


def _get_planet_tier(name: str) -> str:
    if name in PERSONAL_PLANETS:
        return "personal"
    if name in INNER_PLANETS:
        return "inner"
    if name in SOCIAL_PLANETS:
        return "social"
    if name in OUTER_PLANETS:
        return "outer"
    return "point"


def _max_orb(p1: str, p2: str, aspect: str) -> float:
    if aspect in ASPECT_ORBS:
        return ASPECT_ORBS[aspect]
    t1 = _get_planet_tier(p1)
    t2 = _get_planet_tier(p2)
    return max(ORB_TABLE[t1], ORB_TABLE[t2])


def _angular_distance(d1: float, d2: float) -> float:
    diff = abs(d1 - d2) % 360
    return diff if diff <= 180 else 360 - diff


def calculate_aspects(planets: list[dict]) -> list[dict]:
    """Рассчитывает аспекты между всеми парами планет."""
    aspects = []
    for i, p1 in enumerate(planets):
        for p2 in planets[i + 1:]:
            dist = _angular_distance(p1["degree"], p2["degree"])

            for aspect_name, target_angle in ASPECT_ANGLES.items():
                max_orb = _max_orb(p1["name_en"], p2["name_en"], aspect_name)
                orb = abs(dist - target_angle)
                if orb <= max_orb:
                    is_exact = orb < 1.0
                    is_applying = _is_applying(p1, p2, target_angle)
                    aspects.append({
                        "planet1": p1["name_en"],
                        "planet2": p2["name_en"],
                        "type": aspect_name,
                        "angle": target_angle,
                        "orb": round(orb, 3),
                        "is_exact": is_exact,
                        "is_applying": is_applying,
                        "is_separating": not is_applying,
                        "influence_weight": _aspect_weight(aspect_name, orb, p1, p2),
                    })
                    break  # Одна пара — один аспект

    return aspects


def _is_applying(p1: dict, p2: dict, angle: float) -> bool:
    """Определяет, является ли аспект сходящимся (applying)."""
    try:
        s1 = p1.get("speed", 0)
        s2 = p2.get("speed", 0)
        dist = (p1["degree"] - p2["degree"]) % 360
        rel_speed = s1 - s2
        return (rel_speed < 0 and dist > angle) or (rel_speed > 0 and dist < angle)
    except Exception:
        return False


def _aspect_weight(aspect: str, orb: float, p1: dict, p2: dict) -> float:
    """Базовый вес аспекта для influence_level."""
    base = {
        "conjunction": 1.0, "opposition": 0.9, "trine": 0.8,
        "square": 0.8, "sextile": 0.6, "quincunx": 0.5,
        "semi_square": 0.3, "sesquiquadrate": 0.3,
        "quintile": 0.4, "biquintile": 0.4
    }.get(aspect, 0.2)
    # Чем точнее орб — тем выше вес
    orb_limit = ASPECT_ORBS.get(aspect, 10.0)
    orb_factor = max(0.3, 1.0 - orb / orb_limit)
    tier_bonus = 0.1 if p1["name_en"] in PERSONAL_PLANETS or p2["name_en"] in PERSONAL_PLANETS else 0
    return round(min(1.0, base * orb_factor + tier_bonus), 3)


def find_aspect_patterns(planets: list[dict], aspects: list[dict]) -> list[dict]:
    """Находит аспектные фигуры в карте: Тау-квадрат, Большой трин, Йод, Большой крест, Кайт, Прямоугольник."""
    patterns = []
    planet_names = [p["name_en"] for p in planets]
    
    # Вспомогательная мапа аспектов
    asp_map: dict[tuple[str, str], str] = {}
    for a in aspects:
        p1, p2 = a["planet1"], a["planet2"]
        asp_map[(p1, p2)] = a["type"]
        asp_map[(p2, p1)] = a["type"]

    # 1. Тау-квадрат (Opposition + 2 Squares)
    for opp in [a for a in aspects if a["type"] == "opposition"]:
        p1, p2 = opp["planet1"], opp["planet2"]
        for p3 in planet_names:
            if p3 in (p1, p2): continue
            if asp_map.get((p1, p3)) == "square" and asp_map.get((p2, p3)) == "square":
                p3_obj = next(p for p in planets if p["name_en"] == p3)
                patterns.append({
                    "type": "t_square",
                    "planets": [p3, p1, p2],
                    "apex": p3,
                    "apex_sign": p3_obj["sign"],
                    "apex_house": p3_obj["house"],
                })

    # 2. Большой трин (3 Trines)
    for i, p1 in enumerate(planet_names):
        for j, p2 in enumerate(planet_names[i+1:], i+1):
            if asp_map.get((p1, p2)) == "trine":
                for p3 in planet_names[j+1:]:
                    if asp_map.get((p1, p3)) == "trine" and asp_map.get((p2, p3)) == "trine":
                        # Определяем стихию (если все в одной стихии)
                        elements = {get_element(p["sign"]) for p in planets if p["name_en"] in (p1, p2, p3)}
                        patterns.append({
                            "type": "grand_trine",
                            "planets": [p1, p2, p3],
                            "element": list(elements)[0] if len(elements) == 1 else "mixed"
                        })

    # 3. Йод / Перст Судьбы (Sextile + 2 Quincunxes)
    for sxt in [a for a in aspects if a["type"] == "sextile"]:
        p1, p2 = sxt["planet1"], sxt["planet2"]
        for p3 in planet_names:
            if p3 in (p1, p2): continue
            if asp_map.get((p1, p3)) == "quincunx" and asp_map.get((p2, p3)) == "quincunx":
                p3_obj = next(p for p in planets if p["name_en"] == p3)
                patterns.append({
                    "type": "yod",
                    "planets": [p3, p1, p2],
                    "apex": p3,
                    "apex_sign": p3_obj["sign"],
                    "apex_house": p3_obj["house"],
                })

    # 4. Большой крест (4 Planets, 4 Squares, 2 Oppositions)
    for opp1 in [a for a in aspects if a["type"] == "opposition"]:
        p1, p2 = opp1["planet1"], opp1["planet2"]
        for opp2 in [a for a in aspects if a["type"] == "opposition"]:
            if opp2["planet1"] in (p1, p2) or opp2["planet2"] in (p1, p2): continue
            p3, p4 = opp2["planet1"], opp2["planet2"]
            if (asp_map.get((p1, p3)) == "square" and asp_map.get((p1, p4)) == "square" and
                asp_map.get((p2, p3)) == "square" and asp_map.get((p2, p4)) == "square"):
                sig = tuple(sorted([p1, p2, p3, p4]))
                if not any(set(sig) == set(p["planets"]) for p in patterns if p["type"] == "grand_cross"):
                    p1_obj = next(p for p in planets if p["name_en"] == p1)
                    patterns.append({
                        "type": "grand_cross",
                        "planets": list(sig),
                        "modality": get_modality(p1_obj["sign"])
                    })

    # 5. Кайт (Grand Trine + 1 Opposition + 2 Sextiles)
    for gt in [p for p in patterns if p["type"] == "grand_trine"]:
        p1, p2, p3 = gt["planets"]
        for i, p_apex in enumerate([p1, p2, p3]):
            p_base1, p_base2 = [p for j, p in enumerate([p1, p2, p3]) if i != j]
            for p4 in planet_names:
                if p4 in (p1, p2, p3): continue
                if asp_map.get((p_apex, p4)) == "opposition":
                    if asp_map.get((p_base1, p4)) == "sextile" and asp_map.get((p_base2, p4)) == "sextile":
                        patterns.append({
                            "type": "kite",
                            "planets": [p1, p2, p3, p4],
                            "apex": p4,
                            "grand_trine_planets": [p1, p2, p3]
                        })

    # 6. Мистический прямоугольник (2 Oppositions, 2 Trines, 2 Sextiles)
    for opp1 in [a for a in aspects if a["type"] == "opposition"]:
        p1, p2 = opp1["planet1"], opp1["planet2"]
        for opp2 in [a for a in aspects if a["type"] == "opposition"]:
            if opp2["planet1"] in (p1, p2) or opp2["planet2"] in (p1, p2): continue
            p3, p4 = opp2["planet1"], opp2["planet2"]
            if ((asp_map.get((p1, p3)) == "sextile" and asp_map.get((p2, p4)) == "sextile" and
                 asp_map.get((p1, p4)) == "trine" and asp_map.get((p2, p3)) == "trine") or
                (asp_map.get((p1, p3)) == "trine" and asp_map.get((p2, p4)) == "trine" and
                 asp_map.get((p1, p4)) == "sextile" and asp_map.get((p2, p3)) == "sextile")):
                sig = tuple(sorted([p1, p2, p3, p4]))
                if not any(set(sig) == set(p["planets"]) for p in patterns if p["type"] == "mystic_rectangle"):
                    patterns.append({
                        "type": "mystic_rectangle",
                        "planets": list(sig)
                    })

    return patterns


def get_element(sign: str) -> str:
    elements = {
        "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
        "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
        "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
        "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
    }
    return elements.get(sign, "Unknown")


def get_modality(sign: str) -> str:
    modalities = {
        "Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal", "Capricorn": "Cardinal",
        "Taurus": "Fixed", "Leo": "Fixed", "Scorpio": "Fixed", "Aquarius": "Fixed",
        "Gemini": "Mutable", "Virgo": "Mutable", "Sagittarius": "Mutable", "Pisces": "Mutable",
    }
    return modalities.get(sign, "Unknown")


def calc_element_balance(planets: list[dict]) -> dict:
    """Считает распределение по стихиям и модальностям."""
    ELEMENTS = {
        "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
        "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
        "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
        "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
    }
    MODALITIES = {
        "Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal", "Capricorn": "Cardinal",
        "Taurus": "Fixed", "Leo": "Fixed", "Scorpio": "Fixed", "Aquarius": "Fixed",
        "Gemini": "Mutable", "Virgo": "Mutable", "Sagittarius": "Mutable", "Pisces": "Mutable",
    }
    
    main_planets_names = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    main_planets = [p for p in planets if p["name_en"] in main_planets_names]
    
    elements = {"Fire": 0, "Earth": 0, "Air": 0, "Water": 0}
    modalities = {"Cardinal": 0, "Fixed": 0, "Mutable": 0}
    
    for p in main_planets:
        elements[ELEMENTS[p["sign"]]] += 1
        modalities[MODALITIES[p["sign"]]] += 1
    
    dominant_element = max(elements, key=elements.get)
    deficit_element = min(elements, key=elements.get)
    dominant_modality = max(modalities, key=modalities.get)
    
    return {
        "elements": elements,
        "modalities": modalities,
        "dominant_element": dominant_element,
        "deficit_element": deficit_element,
        "dominant_modality": dominant_modality,
    }


def get_decan(degree_in_sign: float, sign: str) -> tuple[int, str]:
    """Возвращает номер деканата и его управителя по халдейской системе."""
    DECAN_RULERS = {
        "Aries": ["Mars", "Sun", "Venus"],
        "Taurus": ["Mercury", "Moon", "Saturn"],
        "Gemini": ["Jupiter", "Mars", "Sun"],
        "Cancer": ["Venus", "Mercury", "Moon"],
        "Leo": ["Saturn", "Jupiter", "Mars"],
        "Virgo": ["Sun", "Venus", "Mercury"],
        "Libra": ["Moon", "Saturn", "Jupiter"],
        "Scorpio": ["Mars", "Sun", "Venus"],
        "Sagittarius": ["Mercury", "Moon", "Saturn"],
        "Capricorn": ["Jupiter", "Mars", "Sun"],
        "Aquarius": ["Venus", "Mercury", "Moon"],
        "Pisces": ["Saturn", "Jupiter", "Mars"],
    }
    decan = int(degree_in_sign // 10) + 1
    if decan > 3: decan = 3
    ruler = DECAN_RULERS.get(sign, ["Sun", "Sun", "Sun"])[decan - 1]
    return decan, ruler


def detect_stelliums(planets: list[dict]) -> list[dict]:
    """Определяет стеллиумы (3+ планеты в знаке или доме)."""
    sign_groups: dict[str, list] = {}
    house_groups: dict[int, list] = {}

    real_planets = [p for p in planets if p["name_en"] not in POINTS]

    for p in real_planets:
        sign_groups.setdefault(p["sign"], []).append(p["name_en"])
        house_groups.setdefault(p["house"], []).append(p["name_en"])

    stelliums = []
    for sign, names in sign_groups.items():
        if len(names) >= 3:
            stelliums.append({"type": "sign", "location": sign, "planets": names})
    for house, names in house_groups.items():
        if len(names) >= 3:
            stelliums.append({"type": "house", "location": house, "planets": names})

    return stelliums


def calculate_hemispheres(planets: list[dict], asc_degree: float) -> dict:
    """Определяет распределение по полусферам и квадрантам."""
    counts = {"north": 0, "south": 0, "east": 0, "west": 0}
    quadrants = {1: 0, 2: 0, 3: 0, 4: 0}

    real = [p for p in planets if p["name_en"] not in POINTS]

    for p in real:
        h = p["house"]
        # N/S: дома 1-6 = South, 7-12 = North (астрологическая конвенция)
        if h <= 6:
            counts["south"] += 1
        else:
            counts["north"] += 1
        # E/W: дома 10-3 = East (восходящий), 4-9 = West
        if h in (10, 11, 12, 1, 2, 3):
            counts["east"] += 1
        else:
            counts["west"] += 1
        # Квадранты
        if h in (1, 2, 3):
            quadrants[1] += 1
        elif h in (4, 5, 6):
            quadrants[2] += 1
        elif h in (7, 8, 9):
            quadrants[3] += 1
        else:
            quadrants[4] += 1

    total = len(real) or 1
    return {
        "north_pct": round(counts["north"] / total, 2),
        "south_pct": round(counts["south"] / total, 2),
        "east_pct": round(counts["east"] / total, 2),
        "west_pct": round(counts["west"] / total, 2),
        "dominant_hemisphere": max(counts, key=counts.get),
        "quadrants": quadrants,
    }


class WesternAstrologyCalculator(Calculator):
    """
    Калькулятор западной астрологии — единственный активный на старте.

    Рассчитывает:
    - Все планеты (знак, дом, градус, ретроградность, достоинство)
    - Аспекты с орбами по стандарту
    - Дома Плацидус, ASC/MC, управители
    - Стеллиумы, полусферы и квадранты

    Выход: JSON по формату секции 3.2 документа DSB.
    """

    system_name = "western_astrology"

    async def calculate(self, birth_data: BirthData) -> dict:
        # 1. Геокодирование (если координаты не переданы)
        lat = birth_data.lat
        lon = birth_data.lon
        tz = birth_data.timezone

        if lat is None or lon is None:
            lat, lon, tz = await geocode_place(birth_data.place)

        if tz is None:
            tz = "UTC"

        # 2. Формирование строки времени (HH:MM)
        birth_time_str = "12:00"  # полдень по умолчанию если время не указано
        if birth_data.time:
            birth_time_str = birth_data.time.strftime("%H:%M")

        # 3. Расчёт натальной карты через существующий движок
        birth_datetime = datetime(
            birth_data.date.year,
            birth_data.date.month,
            birth_data.date.day,
        )

        chart = await asyncio.get_event_loop().run_in_executor(
            None,
            calculate_natal_chart,
            birth_datetime,
            birth_time_str,
            lat,
            lon,
            tz,
        )

        # 4. Сериализация в dict
        chart_dict = to_dict(chart)
        planets = chart_dict["planets"]

        # 5. Расчёт аспектов
        aspects = calculate_aspects(planets)

        # 6. Аспектные фигуры
        aspect_patterns = find_aspect_patterns(planets, aspects)

        # 7. Стеллиумы
        stelliums = detect_stelliums(planets)

        # 8. Полусферы и квадранты
        hemispheres = calculate_hemispheres(planets, chart_dict["ascendant"]["degree"])

        # 9. Элементный баланс
        element_balance = calc_element_balance(planets)

        # 10. Дополнительные точки (Арабские части)
        arabic_parts = calculate_arabic_parts(chart_dict, planets)
        planets.extend(arabic_parts)

        # 11. Обогащение планет данными (деканаты, градусы, сабианские символы)
        sabian_data = {}
        # Path: backend/app/dsb/calculators/western_astrology.py -> backend/data/sabian_symbols.json
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        sabian_path = os.path.join(base_dir, "data", "sabian_symbols.json")
        if os.path.exists(sabian_path):
            with open(sabian_path, "r", encoding="utf-8") as f:
                sabian_data = json.load(f)

        for p in planets:
            p["degree_in_sign"] = round(p["degree"] % 30, 4)
            p["critical_degree"] = "0_degree" if p["degree_in_sign"] < 1.0 else ("29_degree" if p["degree_in_sign"] > 29.0 else None)
            decan, decan_ruler = get_decan(p["degree_in_sign"], p["sign"])
            p["decan"] = decan
            p["decan_ruler"] = decan_ruler
            
            # Sabian Symbol: degree is rounded UP (1-30)
            sabian_deg = math.ceil(p["degree_in_sign"]) or 1
            p["sabian_symbol"] = sabian_data.get(p["sign"], {}).get(str(sabian_deg), "")

        # 11. Дополнительные расчеты (Арабские точки)
        arabic_parts = calculate_arabic_parts(chart_dict, planets)

        # 12. Итоговый payload
        raw_data = {
            "planets": planets,
            "houses": {
                "cusps": chart_dict["cusps"],
                "rulers": chart_dict["house_rulers"],
            },
            "ascendant": chart_dict["ascendant"],
            "mc_degree": chart_dict["mc_degree"],
            "south_node": chart_dict["south_node"],
            "aspects": aspects,
            "aspect_patterns": aspect_patterns,
            "arabic_parts": arabic_parts,
            "stelliums": stelliums,
            "technical_summary": {
                **hemispheres,
                **element_balance
            },
            "dispositor_chains": chart_dict.get("dispositor_chains", {}),
            "geocoded": {"lat": lat, "lon": lon, "timezone": tz},
        }

        return self._base_envelope(birth_data, raw_data)


def calculate_arabic_parts(chart_dict: dict, planets: list[dict]) -> list[dict]:
    """Рассчитывает дополнительные арабские точки (Дух, Брак, Профессия)."""
    parts = []
    asc = chart_dict["ascendant"]["degree"]
    mc = chart_dict["mc_degree"]
    
    sun = next((p for p in planets if p["name_en"] == "Sun"), None)
    moon = next((p for p in planets if p["name_en"] == "Moon"), None)
    venus = next((p for p in planets if p["name_en"] == "Venus"), None)
    
    if sun and moon:
        # Точка Духа (Part of Spirit) - инверсия Фортуны
        is_day = sun["house"] > 6
        if is_day:
            spirit_deg = (asc + sun["degree"] - moon["degree"]) % 360
        else:
            spirit_deg = (asc + moon["degree"] - sun["degree"]) % 360
        parts.append(_create_part("Точка Духа", "PartSpirit", spirit_deg))

    if venus:
        # Точка Брака (Part of Marriage) = Asc + Dsc - Venus
        dsc = (asc + 180) % 360
        marriage_deg = (asc + dsc - venus["degree"]) % 360
        parts.append(_create_part("Точка Брака", "PartMarriage", marriage_deg))

    if sun:
        # Точка Профессии = Asc + MC - Sun
        prof_deg = (asc + mc - sun["degree"]) % 360
        parts.append(_create_part("Точка Профессии", "PartProfession", prof_deg))

    return parts


def _create_part(name: str, name_en: str, degree: float) -> dict:
    from app.core.astrology.natal_chart import degree_to_sign
    sign_en, sign_ru, _ = degree_to_sign(degree)
    return {
        "name": name,
        "name_en": name_en,
        "degree": round(degree, 4),
        "sign": sign_en,
        "sign_ru": sign_ru,
        "house": 0,  # Будет уточнено позже если нужно, пока 0
        "retrograde": False,
        "is_stationary": False,
        "speed": 0.0,
        "priority": "additional",
        "dignity": "neutral",
        "dignity_score": 0
    }
