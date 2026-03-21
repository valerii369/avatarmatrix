from __future__ import annotations
"""
WesternAstrologyCalculator — Слой 1, активный калькулятор.

Использует существующий движок из app.core.astrology.natal_chart
и добавляет расчёт аспектов, стеллиумов, полусфер — всё что нужно для DSB.
"""

import asyncio
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


def _max_orb(p1: str, p2: str) -> float:
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
            max_orb = _max_orb(p1["name_en"], p2["name_en"])

            for aspect_name, target_angle in ASPECT_ANGLES.items():
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
    base = {"conjunction": 1.0, "opposition": 0.9, "trine": 0.8,
            "square": 0.8, "sextile": 0.6}.get(aspect, 0.5)
    # Чем точнее орб — тем выше вес
    orb_factor = max(0.3, 1.0 - orb / 10.0)
    tier_bonus = 0.1 if p1["name_en"] in PERSONAL_PLANETS or p2["name_en"] in PERSONAL_PLANETS else 0
    return round(min(1.0, base * orb_factor + tier_bonus), 3)


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

        # 6. Стеллиумы
        stelliums = detect_stelliums(planets)

        # 7. Полусферы
        hemispheres = calculate_hemispheres(planets, chart_dict["ascendant"]["degree"])

        # 8. Итоговый payload
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
            "stelliums": stelliums,
            "hemispheres": hemispheres,
            "dispositor_chains": chart_dict.get("dispositor_chains", {}),
            "geocoded": {"lat": lat, "lon": lon, "timezone": tz},
        }

        return self._base_envelope(birth_data, raw_data)
