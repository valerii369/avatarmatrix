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

SPHERES = [
    "IDENTITY", "RESOURCES", "COMMUNICATION", "ROOTS",
    "CREATIVITY", "SERVICE", "PARTNERSHIP", "TRANSFORMATION",
    "EXPANSION", "STATUS", "VISION", "SPIRIT"
]


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

    Rules for 12-Sphere Precision:
    - 🔴 Critical: Sun, Moon, Ascendant Ruler, MC (in STATUS), any Stationary planet.
    - 🟠 High: Stellium planets (3+ in sign/house), Nodes, Chiron.
    - 🟡 Medium: All other planets in their houses.
    - 🟢 Additional: Lilith, Decan rulers, secondary sign archetypes.
    """
    recommended: list[RecommendedCard] = []
    seen_keys = set()  # (archetype_id, sphere)

    # Detect stelliums
    sign_counts: dict[str, list[str]] = {}
    house_counts: dict[int, list[str]] = {}

    for planet in chart.planets:
        sign_counts.setdefault(planet.sign, []).append(planet.name_en)
        house_counts.setdefault(planet.house, []).append(planet.name_en)

    stellium_planets = set()
    for planets in sign_counts.values():
        if len(planets) >= 3: stellium_planets.update(planets)
    for planets in house_counts.values():
        if len(planets) >= 3: stellium_planets.update(planets)

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

    # 1. Ascendant Ruler - Critical in IDENTITY
    for planet in chart.planets:
        if planet.name_en == chart.ascendant_ruler:
            add_card(
                planet.archetype_id, "IDENTITY", "critical",
                f"{planet.name} — управитель Асцендента (Путь Личности)",
                planet.name_en, planet.retrograde
            )

    # 2. Main Planet Pass
    for planet in chart.planets:
        priority = planet.priority
        is_stationary = getattr(planet, "is_stationary", False)
        
        # Override priorities based on special conditions
        if planet.name_en in ["Sun", "Moon"] or is_stationary:
            priority = "critical"
        elif planet.name_en in stellium_planets:
            priority = "high"

        planet_spheres = get_spheres_for_house(planet.house)
        retro_suffix = " (Ретроград — внутренняя работа)" if planet.retrograde else ""
        stat_suffix = " (Стационар — точка фиксации)" if is_stationary else ""
        reason_base = f"{planet.name} в {planet.house} доме{retro_suffix}{stat_suffix}"

        for sphere in planet_spheres:
            # Main Planet Archetype
            add_card(planet.archetype_id, sphere, priority, reason_base,
                     planet.name_en, planet.retrograde)
            
            # Sign Primary Archetype - adds secondary depth
            if planet.sign_primary_archetype != planet.archetype_id:
                sign_priority = "medium" if priority == "critical" else "additional"
                add_card(planet.sign_primary_archetype, sphere, sign_priority,
                         f"{planet.name} в знаке {planet.sign_ru}",
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
