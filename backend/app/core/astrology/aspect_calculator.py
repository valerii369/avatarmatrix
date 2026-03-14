"""
Aspect calculator for natal charts.
Calculates major aspects between planets and returns connection data.
"""
from dataclasses import dataclass


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
    is_dissociated: bool = False
    is_stationary: bool = False


ASPECT_DEFINITIONS = {
    "conjunction":  {"angle": 0,   "orb": 8.0,  "symbol": "☌", "strength_base": 5, "label": "Слияние сил", "harmonic": 1},
    "opposition":   {"angle": 180, "orb": 8.0,  "symbol": "☍", "strength_base": 4, "label": "Противостояние, полярность", "harmonic": 2},
    "square":       {"angle": 90,  "orb": 7.0,  "symbol": "□", "strength_base": 4, "label": "Динамический вызов, трение", "harmonic": 4},
    "trine":        {"angle": 120, "orb": 8.0,  "symbol": "△", "strength_base": 4, "label": "Естественный поток, талант", "harmonic": 3},
    "sextile":      {"angle": 60,  "orb": 5.0,  "symbol": "⚹", "strength_base": 2, "label": "Возможность реализации", "harmonic": 6},
}

# Planetary weights for dynamic orbs
PLANET_ORB_WEIGHTS = {
    "Sun": 4.0,
    "Moon": 4.0,
    "Mercury": 1.0,
    "Venus": 1.0,
    "Mars": 1.0,
    "Jupiter": 1.5,
    "Saturn": 1.5,
    "Uranus": 0.0,
    "Neptune": 0.0,
    "Pluto": 0.0,
    "TrueNode": -1.0,
    "SouthNode": -1.0,
    "Chiron": -1.0,
}

# Qualities for dissociate aspect checking
SIGN_QUALITIES = {
    "Aries":       {"element": "Fire",    "modality": "Cardinal"},
    "Taurus":      {"element": "Earth",   "modality": "Fixed"},
    "Gemini":      {"element": "Air",     "modality": "Mutable"},
    "Cancer":      {"element": "Water",   "modality": "Cardinal"},
    "Leo":         {"element": "Fire",    "modality": "Fixed"},
    "Virgo":       {"element": "Earth",   "modality": "Mutable"},
    "Libra":       {"element": "Air",     "modality": "Cardinal"},
    "Scorpio":     {"element": "Water",   "modality": "Fixed"},
    "Sagittarius": {"element": "Fire",    "modality": "Mutable"},
    "Capricorn":   {"element": "Earth",   "modality": "Cardinal"},
    "Aquarius":    {"element": "Air",     "modality": "Fixed"},
    "Pisces":      {"element": "Water",   "modality": "Mutable"},
}


def angle_diff(a: float, b: float) -> float:
    """Minimum angle between two ecliptic degrees."""
    diff = abs(a - b) % 360
    return diff if diff <= 180 else 360 - diff


def calculate_aspects(planets: list[dict]) -> list[Aspect]:
    """
    Calculate all major aspects between planets with professional refinements.
    Refinements: Dynamic orbs, dissociated aspects, and stationarity handling.
    """
    aspects = []

    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            p1 = planets[i]
            p2 = planets[j]

            # 1. Base Geometry
            diff = angle_diff(p1["degree"], p2["degree"])
            
            # 2. Dynamics (Speeds and Stationarity)
            v1 = p1.get("speed", 0.0)
            v2 = p2.get("speed", 0.0)
            is_stat_1 = p1.get("is_stationary", False)
            is_stat_2 = p2.get("is_stationary", False)
            is_stationary = is_stat_1 or is_stat_2
            
            p1_next = (p1["degree"] + v1) % 360
            p2_next = (p2["degree"] + v2) % 360
            future_diff = angle_diff(p1_next, p2_next)

            for aspect_name, aspect_def in ASPECT_DEFINITIONS.items():
                target = aspect_def["angle"]
                base_orb = aspect_def["orb"]
                
                # Dynamic Orb adjustment
                w1 = PLANET_ORB_WEIGHTS.get(p1["name_en"], 0.0)
                w2 = PLANET_ORB_WEIGHTS.get(p2["name_en"], 0.0)
                orb_limit = base_orb + w1 + w2
                
                actual_orb = abs(diff - target)
                if actual_orb <= orb_limit:
                    # 3. Dissociated Aspect Check
                    # Aspects usually occur between signs of certain elements/modalities
                    # e.g. Trines are same element, Solids same modality (square/opp)
                    s1 = p1.get("sign")
                    s2 = p2.get("sign")
                    is_dissociated = False
                    
                    if s1 and s2 and s1 in SIGN_QUALITIES and s2 in SIGN_QUALITIES:
                        q1 = SIGN_QUALITIES[s1]
                        q2 = SIGN_QUALITIES[s2]
                        
                        harmony = aspect_def.get("harmonic", 1)
                        if harmony == 3: # Trine: should be same element
                            is_dissociated = q1["element"] != q2["element"]
                        elif harmony in [2, 4]: # Square/Opposition: should be same modality
                            is_dissociated = q1["modality"] != q2["modality"]
                        elif harmony == 6: # Sextile: should be complementary elements (Fire/Air or Earth/Water)
                            complementary = {
                                "Fire": ["Fire", "Air"], "Air": ["Fire", "Air"],
                                "Earth": ["Earth", "Water"], "Water": ["Earth", "Water"]
                            }
                            is_dissociated = q2["element"] not in complementary.get(q1["element"], [])
                        elif harmony == 1: # Conjunction: should be same sign
                            is_dissociated = s1 != s2

                    # 4. Applying/Exact Logic
                    is_exact = actual_orb <= 1.0
                    future_orb = abs(future_diff - target)
                    
                    # Special case: check if planets are at exactly 0.0 speed (stationary)
                    # If both are stationary, it's effectively "holding"
                    if abs(v1) < 1e-6 and abs(v2) < 1e-6:
                        is_applying = True # Consider stationary exact as applying
                    else:
                        is_applying = future_orb < actual_orb

                    # 5. Strength Calculation
                    # Base strength depends on orb proximity
                    strength = max(1, round(aspect_def["strength_base"] * (1 - actual_orb / orb_limit)))
                    if is_exact: strength += 2
                    if is_applying: strength += 1
                    if is_stationary: strength += 1
                    if is_dissociated: strength = max(1, strength - 1)
                    
                    strength = min(strength, 9) # Max 9

                    # 6. Labels
                    label_parts = []
                    if is_exact: label_parts.append("Точный")
                    if is_stationary: label_parts.append("Стационарный")
                    if is_dissociated: label_parts.append("Диссоциированный")
                    
                    if is_applying: label_parts.append("Сходящийся")
                    else: label_parts.append("Расходящийся")
                    
                    full_label = f"{aspect_def['label']} ({', '.join(label_parts)})"

                    aspects.append(Aspect(
                        planet1=p1["name_en"],
                        planet2=p2["name_en"],
                        aspect_type=aspect_name,
                        orb=round(actual_orb, 2),
                        is_applying=is_applying,
                        is_exact=is_exact,
                        is_dissociated=is_dissociated,
                        is_stationary=is_stationary,
                        strength=strength,
                        connection_label=full_label,
                    ))
                    break  # Only one major aspect per pair

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
            "is_dissociated": asp.is_dissociated,
            "is_stationary": asp.is_stationary,
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
            "is_dissociated": a.is_dissociated,
            "is_stationary": a.is_stationary,
            "strength": a.strength,
            "label": a.connection_label,
        }
        for a in aspects
    ]
