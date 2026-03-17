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
    Generate prioritized list of recommended cards from natal chart using weighted resonance.
    
    Resonance Ranks (Updated):
    - 🔴 Critical: Asc Ruler, MC Ruler, Final Dispositors, Stationary Planets.
    - 🟠 High: House Rulers (Planetary Directors of Spheres), Stelliums, Aspect King.
    - 🟡 Medium: Planets in houses (Ocurrants), Nodes.
    - 🟢 Low: Decan rulers, Sign-only markers.
    """
    recommended: list[RecommendedCard] = []
    seen_keys = set()  # (archetype_id, sphere)
    aspects = aspects or []

    # 1. Context extraction
    planet_map = {p.name_en: p for p in chart.planets}
    house_rulers = getattr(chart, "house_rulers", {})
    finals = getattr(chart, "dispositor_chains", {}).get("finals", [])
    
    # 2. Detect stelliums
    house_counts: dict[int, list[str]] = {}
    for planet in chart.planets:
        house_counts.setdefault(planet.house, []).append(planet.name_en)

    stellium_planets = set()
    for planets in house_counts.values():
        if len(planets) >= 3: stellium_planets.update(planets)

    # 3. Aspect Weighting (Aspect King)
    aspect_counts = {}
    for asp in aspects:
        p1 = asp.get("planet1") if isinstance(asp, dict) else getattr(asp, "planet1", None)
        p2 = asp.get("planet2") if isinstance(asp, dict) else getattr(asp, "planet2", None)
        if p1: aspect_counts[p1] = aspect_counts.get(p1, 0) + 1
        if p2: aspect_counts[p2] = aspect_counts.get(p2, 0) + 1
    
    aspect_king = max(aspect_counts, key=aspect_counts.get) if aspect_counts else None

    def add_card(archetype_id: int, sphere: str, priority: str, reason: str,
                 planet_name: str = None, retrograde: bool = False):
        if not archetype_id: return
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

    # 4. Critical Drivers
    # 4.1 Ascendant Ruler (The Driver of the Whole Chart)
    if chart.ascendant_ruler in planet_map:
        p = planet_map[chart.ascendant_ruler]
        add_card(p.archetype_id, "IDENTITY", "critical", "Управитель Асцендента (Вектор самореализации)", p.name_en, p.retrograde)

    # 4.2 Final Dispositors (The Psychotype Center)
    for f in finals:
        if isinstance(f, str) and f in planet_map:
            p = planet_map[f]
            # Recommend for IDENTITY or appropriate spheres
            add_card(p.archetype_id, "IDENTITY", "critical", "Конечный диспозитор (Центр психики)", p.name_en, p.retrograde)
        elif isinstance(f, tuple): # Mutual reception
            for name in f:
                if name in planet_map:
                    p = planet_map[name]
                    add_card(p.archetype_id, "IDENTITY", "critical", f"Взаимная рецепция ({', '.join(f)})", p.name_en, p.retrograde)

    # 5. House Rulers Pass (Directors of Life Spheres)
    for h_num, ruler_name in house_rulers.items():
        if ruler_name in planet_map:
            p = planet_map[ruler_name]
            spheres = get_spheres_for_house(h_num)
            for sphere in spheres:
                add_card(p.archetype_id, sphere, "high", f"Управитель {h_num} дома (Хозяин сферы)", p.name_en, p.retrograde)

    # 6. Occupant Planets Pass (Ocurrants)
    for p in chart.planets:
        spheres = get_spheres_for_house(p.house)
        priority = "medium"
        reasons = []
        
        if p.name_en in stellium_planets: 
            priority = "high"
            reasons.append("Стеллиум")
        if p.name_en == aspect_king:
            priority = "high"
            reasons.append("Король аспектов")
        if getattr(p, "is_stationary", False):
            priority = "critical"
            reasons.append("Стационарная планета")

        reason_base = f"{p.name} в {p.house} доме"
        if reasons: reason_base += f" [{', '.join(reasons)}]"

        # Planet-based archetypes (traditional resonance)
        if p.archetype_id > 0:
            for sphere in spheres:
                add_card(p.archetype_id, sphere, priority, reason_base, p.name_en, p.retrograde)

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
