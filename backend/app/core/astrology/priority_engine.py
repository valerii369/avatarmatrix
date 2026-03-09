"""
Priority engine: generates recommended cards from natal chart data.
Applies priority rules: stelliums, retrograde, ascendant ruler, etc.
"""
import json
import os
from dataclasses import dataclass
from typing import Optional

from app.core.astrology.natal_chart import NatalChartData

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")

with open(os.path.join(DATA_DIR, "house_sphere_map.json")) as f:
    HOUSE_SPHERE_MAP = json.load(f)

PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "additional": 3}

SPHERES = ["IDENTITY", "MONEY", "RELATIONS", "FAMILY", "MISSION", "HEALTH", "SOCIETY", "SPIRIT"]


@dataclass
class RecommendedCard:
    archetype_id: int
    sphere: str
    priority: str  # critical, high, medium, additional
    reason: str
    planet: Optional[str] = None
    is_retrograde: bool = False


def get_spheres_for_house(house_num: int) -> list[str]:
    """Get spheres associated with a house number."""
    house_data = HOUSE_SPHERE_MAP.get(str(house_num), {})
    return house_data.get("spheres", [])


def generate_recommended_cards(chart: NatalChartData) -> list[RecommendedCard]:
    """
    Generate prioritized list of recommended cards from natal chart.

    Rules (from architecture):
    - 🔴 Critical: Sun, Moon, Pluto, Saturn; Stellium planets; Ascendant ruler; Stationary planets
    - 🟠 High: North Node, Chiron, Lilith
    - 🟡 Medium: Mars, Venus, Jupiter, Mercury
    - 🟢 Additional: Uranus, Neptune, South Node, Decan rulers
    - Retrograde planets → archetype active in SHADOW (still recommended, marked)
    """
    recommended: list[RecommendedCard] = []
    seen_keys = set()  # (archetype_id, sphere) to avoid duplicates

    # Detect stelliums: 3+ planets in same sign or house
    sign_counts: dict[str, list[str]] = {}
    house_counts: dict[int, list[str]] = {}

    for planet in chart.planets:
        sign_counts.setdefault(planet.sign, []).append(planet.name_en)
        house_counts.setdefault(planet.house, []).append(planet.name_en)

    stellium_signs = {sign for sign, planets in sign_counts.items() if len(planets) >= 3}
    stellium_houses = {house for house, planets in house_counts.items() if len(planets) >= 3}
    stellium_planets = set()
    for sign in stellium_signs:
        stellium_planets.update(sign_counts[sign])
    for house in stellium_houses:
        stellium_planets.update(house_counts[house])

    def add_card(archetype_id: int, sphere: str, priority: str, reason: str,
                 planet_name: str = None, retrograde: bool = False):
        key = (archetype_id, sphere)
        if key in seen_keys:
            # Upgrade priority if we see it again
            for card in recommended:
                if card.archetype_id == archetype_id and card.sphere == sphere:
                    if PRIORITY_RANK.get(priority, 3) < PRIORITY_RANK.get(card.priority, 3):
                        card.priority = priority
                        card.reason += f" + {reason}"
            return
        seen_keys.add(key)
        recommended.append(RecommendedCard(
            archetype_id=archetype_id,
            sphere=sphere,
            priority=priority,
            reason=reason,
            planet=planet_name,
            is_retrograde=retrograde,
        ))

    for planet in chart.planets:
        # Determine effective priority
        priority = planet.priority
        is_stationary = getattr(planet, "is_stationary", False)
        
        if planet.name_en in stellium_planets or is_stationary:
            priority = "critical"

        # Ascendant ruler → critical in IDENTITY
        if planet.name_en == chart.ascendant_ruler:
            identity_spheres = ["IDENTITY"]
            for sphere in identity_spheres:
                add_card(
                    planet.archetype_id, sphere, "critical",
                    f"{planet.name} — управитель Асцендента",
                    planet.name_en, planet.retrograde
                )

        # Planet archetype in its house spheres
        planet_spheres = get_spheres_for_house(planet.house)
        retro_suffix = " (в ТЕНИ — ретроград)" if planet.retrograde else ""
        stat_suffix = " (Точка опоры — стационарна)" if is_stationary else ""
        reason_planet = f"{planet.name} в доме {planet.house}{retro_suffix}{stat_suffix}"

        for sphere in planet_spheres:
            # Planet archetype
            add_card(planet.archetype_id, sphere, priority, reason_planet,
                     planet.name_en, planet.retrograde)
            # Sign primary archetype
            if planet.sign_primary_archetype != planet.archetype_id:
                sign_priority = min(priority, "medium", key=lambda p: PRIORITY_RANK.get(p, 3))
                add_card(planet.sign_primary_archetype, sphere, sign_priority,
                         f"{planet.name} в {planet.sign_ru} (знак, основной)",
                         planet.name_en, planet.retrograde)
            # Sign secondary archetype (lower priority)
            if planet.sign_secondary_archetype not in (planet.archetype_id, planet.sign_primary_archetype):
                add_card(planet.sign_secondary_archetype, sphere, "additional",
                         f"{planet.name} в {planet.sign_ru} (знак, доп.)",
                         planet.name_en, planet.retrograde)
                         
            # Decan ruler archetype
            decan_archetype = getattr(planet, "decan_ruler_archetype", 0)
            if decan_archetype and decan_archetype not in (planet.archetype_id, planet.sign_primary_archetype, planet.sign_secondary_archetype):
                add_card(decan_archetype, sphere, "additional",
                         f"{planet.name} в {planet.sign_ru} (декан: {getattr(planet, 'decan_ruler', '')})",
                         planet.name_en, planet.retrograde)

    # Sort by priority
    recommended.sort(key=lambda c: PRIORITY_RANK.get(c.priority, 3))
    return recommended


def to_dict(cards: list[RecommendedCard]) -> list[dict]:
    return [
        {
            "archetype_id": c.archetype_id,
            "sphere": c.sphere,
            "priority": c.priority,
            "reason": c.reason,
            "planet": c.planet,
            "is_retrograde": c.is_retrograde,
        }
        for c in cards
    ]
