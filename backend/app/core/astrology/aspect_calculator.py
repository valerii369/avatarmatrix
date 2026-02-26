"""
Aspect calculator for natal charts.
Calculates major aspects between planets and returns connection data.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Aspect:
    planet1: str
    planet2: str
    aspect_type: str  # conjunction, opposition, square, trine, sextile
    orb: float
    is_applying: bool
    is_exact: bool
    strength: int  # 1-7 (base max 5, exact +2)
    connection_label: str


ASPECT_DEFINITIONS = {
    "conjunction":  {"angle": 0,   "orb": 7.0,  "symbol": "☌", "strength_base": 5, "label": "Слияние"},
    "opposition":   {"angle": 180, "orb": 7.0,  "symbol": "☍", "strength_base": 4, "label": "Напряжённая полярность"},
    "square":       {"angle": 90,  "orb": 6.0,  "symbol": "□", "strength_base": 3, "label": "Конфликт, точка роста"},
    "trine":        {"angle": 120, "orb": 7.0,  "symbol": "△", "strength_base": 4, "label": "Гармония"},
    "sextile":      {"angle": 60,  "orb": 5.0,  "symbol": "⚹", "strength_base": 2, "label": "Возможность"},
}


def angle_diff(a: float, b: float) -> float:
    """Minimum angle between two ecliptic degrees."""
    diff = abs(a - b) % 360
    return diff if diff <= 180 else 360 - diff


def calculate_aspects(planets: list[dict]) -> list[Aspect]:
    """
    Calculate all major aspects between planets.
    planets: list of {name_en, degree, priority}
    """
    aspects = []

    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            p1 = planets[i]
            p2 = planets[j]

            diff = angle_diff(p1["degree"], p2["degree"])

            v1 = p1.get("speed", 0.0)
            v2 = p2.get("speed", 0.0)
            p1_next = (p1["degree"] + v1) % 360
            p2_next = (p2["degree"] + v2) % 360
            future_diff = angle_diff(p1_next, p2_next)

            for aspect_name, aspect_def in ASPECT_DEFINITIONS.items():
                target = aspect_def["angle"]
                orb_limit = aspect_def["orb"]

                actual_orb = abs(diff - target)
                if actual_orb <= orb_limit:
                    is_exact = actual_orb <= 1.0
                    
                    # Applying check
                    future_orb = abs(future_diff - target)
                    is_applying = future_orb < actual_orb

                    # Strength decreases with orb
                    strength = max(1, round(aspect_def["strength_base"] * (1 - actual_orb / orb_limit)))
                    if is_exact:
                        strength += 2

                    label_suffix = []
                    if is_exact: label_suffix.append("Точный")
                    if is_applying: label_suffix.append("Сходящийся")
                    else: label_suffix.append("Расходящийся")
                    
                    full_label = f"{aspect_def['label']} ({', '.join(label_suffix)})"

                    aspects.append(Aspect(
                        planet1=p1["name_en"],
                        planet2=p2["name_en"],
                        aspect_type=aspect_name,
                        orb=round(actual_orb, 2),
                        is_applying=is_applying,
                        is_exact=is_exact,
                        strength=strength,
                        connection_label=full_label,
                    ))
                    break  # Only one aspect per pair

    return aspects


def aspects_to_connections(aspects: list[Aspect], planets: list[dict]) -> list[dict]:
    """
    Convert aspects to card connections.
    Each aspect between two planets creates a connection between their cards.
    """
    # Build planet → archetype mapping
    planet_archetypes = {p["name_en"]: p["archetype_id"] for p in planets}
    planet_spheres = {}
    for p in planets:
        house_sphere_data = p.get("house_spheres", [])
        planet_spheres[p["name_en"]] = house_sphere_data

    connections = []
    for asp in aspects:
        arch1 = planet_archetypes.get(asp.planet1)
        arch2 = planet_archetypes.get(asp.planet2)
        if arch1 is None or arch2 is None:
            continue

        connections.append({
            "archetype_id_1": arch1,
            "archetype_id_2": arch2,
            "type": "aspect",
            "aspect_type": asp.aspect_type,
            "strength": asp.strength,
            "label": f"{asp.aspect_type.title()}: {asp.connection_label}",
        })

    return connections


def to_dict(aspects: list[Aspect]) -> list[dict]:
    return [
        {
            "planet1": a.planet1,
            "planet2": a.planet2,
            "type": a.aspect_type,
            "orb": a.orb,
            "is_applying": a.is_applying,
            "is_exact": a.is_exact,
            "strength": a.strength,
            "label": a.connection_label,
        }
        for a in aspects
    ]
