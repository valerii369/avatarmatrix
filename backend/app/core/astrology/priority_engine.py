"""
Priority engine: generates recommended cards from natal chart data.
Applies priority rules: stelliums, retrograde, ascendant ruler, etc.
"""
import json
import os
from dataclasses import dataclass
from typing import Optional

from app.config import settings
from app.core.astrology.natal_chart import NatalChartData

DATA_DIR = settings.DATA_DIR

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


def generate_recommended_cards(chart: NatalChartData, aspects: list = None) -> list[RecommendedCard]:
    """
    Generate prioritized list of recommended cards from natal chart.

    Refined Rules:
    - 🔴 Critical: Sun, Moon, Asc Ruler, MC, Stationary, Final Dispositor.
    - 🟠 High: Stelliums, Angular Houses (1,4,7,10), Aspect King, Strong Dignities, Nodes.
    - 🟡 Medium: Standard placements.
    - 🟢 Additional: Minor points.
    """
    recommended: list[RecommendedCard] = []
    seen_keys = set()  # (archetype_id, sphere)
    aspects = aspects or []

    # 1. Detect stelliums
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

    # 2. Aspect Weighting (Aspect King)
    aspect_counts = {}
    for asp in aspects:
        # aspects can be Aspect objects or dicts
        p1 = asp.get("planet1") if isinstance(asp, dict) else getattr(asp, "planet1", None)
        p2 = asp.get("planet2") if isinstance(asp, dict) else getattr(asp, "planet2", None)
        if p1: aspect_counts[p1] = aspect_counts.get(p1, 0) + 1
        if p2: aspect_counts[p2] = aspect_counts.get(p2, 0) + 1
    
    aspect_king = max(aspect_counts, key=aspect_counts.get) if aspect_counts else None

    # 3. Final Dispositor Logic
    # Map sign -> ruler (using same mapping as natal_chart)
    # Note: For speed, we'll use a simplified mapping here or rely on chart data
    planet_map = {p.name_en: p for p in chart.planets}
    
    def get_ruler(planet_name):
        p = planet_map.get(planet_name)
        if not p: return None
        # We need the ruler of the sign the planet is in
        # This is a bit recursive. 
        from app.core.astrology.natal_chart import DIGNITY_TABLE
        for ruler, signs in DIGNITY_TABLE["Domicile"].items():
            if p.sign in signs:
                return ruler
        return None

    final_dispositor = None
    # Simple check for a planet in its own domicile
    domiciles = [p.name_en for p in chart.planets if getattr(p, "dignity", None) == "domicile"]
    if len(domiciles) == 1:
        final_dispositor = domiciles[0]
    # More complex chain logic could be added here, but domicile-owner is the strongest signal

    def add_card(archetype_id: int, sphere: str, priority: str, reason: str,
                 planet_name: str = None, retrograde: bool = False):
        key = (archetype_id, sphere)
        if key in seen_keys:
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

    # 4. Ascendant Ruler
    for planet in chart.planets:
        if planet.name_en == chart.ascendant_ruler:
            add_card(
                planet.archetype_id, "IDENTITY", "critical",
                "Управитель Асцендента (Главный вектор реализации)",
                planet.name_en, planet.retrograde
            )

    # 5. Main Planet Pass
    for planet in chart.planets:
        priority = planet.priority
        is_stationary = getattr(planet, "is_stationary", False)
        dignity = getattr(planet, "dignity", "neutral")
        
        reasons = []
        if is_stationary: reasons.append("Стационар")
        
        # Priority Logic
        if planet.name_en in ["Sun", "Moon"] or is_stationary or planet.name_en == final_dispositor:
            priority = "critical"
            if planet.name_en == final_dispositor: reasons.append("Конечный диспозитор")
        elif planet.name_en in stellium_planets or planet.name_en == aspect_king:
            priority = "high"
            if planet.name_en == aspect_king: reasons.append("Король аспектов")
        
        if dignity in ["domicile", "exaltation"]:
            if priority not in ["critical"]: priority = "high"
            reasons.append(f"Сила ({dignity})")
        elif dignity in ["detriment", "fall"]:
            if priority not in ["critical"]: priority = "high"
            reasons.append(f"Вызов ({dignity})")

        if planet.house in [1, 4, 7, 10]:
            if priority == "medium": priority = "high"
            reasons.append("Угловой дом")

        planet_spheres = get_spheres_for_house(planet.house)
        reason_str = f"{planet.name} в {planet.house} доме"
        if reasons: reason_str += f" [{', '.join(reasons)}]"

        for sphere in planet_spheres:
            add_card(planet.archetype_id, sphere, priority, reason_str,
                     planet.name_en, planet.retrograde)
            
            if planet.sign_primary_archetype != planet.archetype_id:
                s_priority = "medium" if priority in ["critical", "high"] else "additional"
                add_card(planet.sign_primary_archetype, sphere, s_priority,
                         f"Знак {planet.sign_ru}", planet.name_en, planet.retrograde)

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
