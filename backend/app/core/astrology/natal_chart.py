"""
Natal chart calculation engine using pyswisseph.
Computes planet positions, signs, houses, and retrograde status.
"""
import json
import os
from dataclasses import dataclass, field
import swisseph as swe
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from datetime import datetime
from typing import Any
import pytz
import logging
from app.config import settings

logger = logging.getLogger(__name__)

DATA_DIR = settings.DATA_DIR
EPHE_PATH = settings.EPHE_PATH

# Set ephemeris path
swe.set_ephe_path(EPHE_PATH)

with open(os.path.join(DATA_DIR, "planet_archetype_map.json")) as f:
    PLANET_ARCHETYPE_MAP = json.load(f)

with open(os.path.join(DATA_DIR, "house_sphere_map.json")) as f:
    HOUSE_SPHERE_MAP = json.load(f)

SIGN_ARCHETYPE_MAP = {}

SIGN_RULERS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Pluto", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Uranus", "Pisces": "Neptune"
}

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]


ZODIAC_SIGNS_RU = [
    "Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
    "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"
]

# Swiss Ephemeris planet constants
PLANET_CODES = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "TrueNode": swe.TRUE_NODE,
    "Chiron": swe.CHIRON,
    "Lilith": swe.MEAN_APOG,  # Black Moon Lilith
}


@dataclass
class PlanetPosition:
    name: str
    name_en: str
    degree: float
    sign: str
    sign_ru: str
    house: int
    retrograde: bool
    is_stationary: bool
    speed: float
    archetype_id: int
    sign_primary_archetype: int
    sign_secondary_archetype: int
    decan_ruler: str
    decan_ruler_archetype: int
    priority: str
    dignity: str = "neutral"
    dignity_score: int = 0


DIGNITY_TABLE = {
    "Domicile": {
        "Sun": ["Leo"],
        "Moon": ["Cancer"],
        "Mercury": ["Gemini", "Virgo"],
        "Venus": ["Taurus", "Libra"],
        "Mars": ["Aries", "Scorpio"],
        "Jupiter": ["Sagittarius", "Pisces"],
        "Saturn": ["Capricorn", "Aquarius"],
        "Uranus": ["Aquarius"],
        "Neptune": ["Pisces"],
        "Pluto": ["Scorpio"],
    },
    "Exaltation": {
        "Sun": ["Aries"],
        "Moon": ["Taurus"],
        "Mercury": ["Virgo"],
        "Venus": ["Pisces"],
        "Mars": ["Capricorn"],
        "Jupiter": ["Cancer"],
        "Saturn": ["Libra"],
    },
    "Detriment": {
        "Sun": ["Aquarius"],
        "Moon": ["Capricorn"],
        "Mercury": ["Sagittarius", "Pisces"],
        "Venus": ["Aries", "Scorpio"],
        "Mars": ["Taurus", "Libra"],
        "Jupiter": ["Gemini", "Virgo"],
        "Saturn": ["Cancer", "Leo"],
        "Uranus": ["Leo"],
        "Neptune": ["Virgo"],
        "Pluto": ["Taurus"],
    },
    "Fall": {
        "Sun": ["Libra"],
        "Moon": ["Scorpio"],
        "Mercury": ["Pisces"],
        "Venus": ["Virgo"],
        "Mars": ["Cancer"],
        "Jupiter": ["Capricorn"],
        "Saturn": ["Aries"],
    }
}


def calculate_dignity(planet_name: str, sign: str) -> tuple[str, int]:
    """Calculate the essential dignity of a planet in a sign."""
    if sign in DIGNITY_TABLE["Domicile"].get(planet_name, []):
        return "domicile", 5
    if sign in DIGNITY_TABLE["Exaltation"].get(planet_name, []):
        return "exaltation", 4
    if sign in DIGNITY_TABLE["Detriment"].get(planet_name, []):
        return "detriment", -5
    if sign in DIGNITY_TABLE["Fall"].get(planet_name, []):
        return "fall", -4
    return "neutral", 0


@dataclass
class NatalChartData:
    planets: list[PlanetPosition] = field(default_factory=list)
    ascendant_degree: float = 0.0
    ascendant_sign: str = ""
    ascendant_sign_ru: str = ""
    ascendant_ruler: str = ""
    mc_degree: float = 0.0
    south_node_degree: float = 0.0
    south_node_sign: str = ""
    south_node_sign_ru: str = ""
    raw_cusps: list[float] = field(default_factory=list)
    house_rulers: dict[int, str] = field(default_factory=dict)
    dispositor_chains: dict[str, Any] = field(default_factory=dict)



def degree_to_sign(degree: float) -> tuple[str, str, float]:
    """Convert ecliptic degree to sign name and position within sign."""
    sign_idx = int(degree / 30)
    sign_en = ZODIAC_SIGNS[sign_idx]
    sign_ru = ZODIAC_SIGNS_RU[sign_idx]
    position_in_sign = degree % 30
    return sign_en, sign_ru, position_in_sign


def get_house(degree: float, cusps: list[float]) -> int:
    """Determine which house a degree falls in."""
    for i in range(11, -1, -1):
        if cusps[i] <= degree < cusps[(i + 1) % 12]:
            return i + 1
    # Handle wrap-around
    if degree >= cusps[11] or degree < cusps[0]:
        return 12
    return 1


def calculate_dispositor_chains(planets: list[PlanetPosition]) -> dict[str, Any]:
    """
    Build chains of dispositors to find the 'Final Dispositor' or 'Mutual Reception'.
    A dispositor is the ruler of the sign a planet is in.
    """
    planet_map = {p.name_en: p for p in planets if p.name_en in PLANET_CODES}
    dispositor_map = {}

    for name, p in planet_map.items():
        sign = p.sign
        # Modern rulers
        ruler = SIGN_RULERS.get(sign, "Sun")
        dispositor_map[name] = ruler

    chains = {}
    for start_planet in planet_map:
        chain = [start_planet]
        current = start_planet
        visited = {start_planet}
        
        while True:
            nxt = dispositor_map.get(current)
            if not nxt or nxt not in planet_map:
                break
            if nxt in visited:
                # Cycle or Final Dispositor
                chain.append(nxt)
                break
            chain.append(nxt)
            visited.add(nxt)
            current = nxt
        chains[start_planet] = chain
    
    # Identify unique final dispositors/receptions
    finals = []
    for chain in chains.values():
        last = chain[-1]
        if len(chain) > 1 and chain[-1] == chain[-2]: # Planet in its own sign
             finals.append(last)
        elif len(chain) >= 2 and chain[-1] in chain[:-1]: # Mutual reception or cycle
             cycle_start_idx = chain.index(chain[-1])
             cycle = chain[cycle_start_idx:]
             # Convert cycle to a stable format for set
             finals.append(tuple(sorted(list(set(cycle)))))
    
    # Final cleanup of finals (removing duplicates and ensuring only unique cycles/planets)
    unique_finals = []
    seen = set()
    for f in finals:
        if f not in seen:
            unique_finals.append(f)
            seen.add(f)

    return {
        "chains": chains,
        "finals": unique_finals
    }



import anyio

async def geocode_place(place: str) -> tuple[float, float, str]:
    """Get latitude, longitude and timezone from place name."""
    logger.info(f"[Geocode] Started for place: {place}")
    try:
        # Using a fixed unique user agent to avoid rate limiting and encoding issues
        geolocator = Nominatim(user_agent="avatar_app_v1_0_prod_geocoder")
        
        # Run synchronous geocode in a thread
        location = await anyio.to_thread.run_sync(lambda: geolocator.geocode(place, timeout=15))
        
        if not location:
            logger.warning(f"[Geocode] Location NOT FOUND for: {place}")
            raise ValueError(f"Не удалось найти место: {place}")

        tf = TimezoneFinder()
        tz_name = await anyio.to_thread.run_sync(lambda: tf.timezone_at(lng=location.longitude, lat=location.latitude))
        
        logger.info(f"[Geocode] Found: {location.latitude}, {location.longitude}, TZ: {tz_name}")
        return location.latitude, location.longitude, tz_name or "UTC"
    except Exception as e:
        logger.error(f"[Geocode] Error for {place}: {e}")
        raise e


def calculate_natal_chart(
    birth_date: datetime,
    birth_time_str: str,
    lat: float,
    lon: float,
    tz_name: str,
) -> NatalChartData:
    """
    Main function: calculate full natal chart.
    Returns NatalChartData with planet positions and house info.
    """
    # Parse time
    hour, minute = map(int, birth_time_str.split(":"))

    # Convert local time to UTC
    tz = pytz.timezone(tz_name)
    local_dt = tz.localize(datetime(
        birth_date.year, birth_date.month, birth_date.day, hour, minute
    ))
    utc_dt = local_dt.astimezone(pytz.utc)

    # Julian Day
    jd = swe.julday(
        utc_dt.year, utc_dt.month, utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60.0
    )

    # Calculate houses (Placidus with Whole Sign fallback)
    try:
        cusps_raw, ascmc = swe.houses(jd, lat, lon, b"P")
    except Exception as e:
        print(f"Placidus calculation failed or skewed (e.g. extreme latitude): {e}. Falling back to Whole Sign.")
        cusps_raw, ascmc = swe.houses(jd, lat, lon, b"W")

    cusps = list(cusps_raw)

    ascendant_degree = ascmc[0]
    mc_degree = ascmc[1]

    asc_sign_en, asc_sign_ru, _ = degree_to_sign(ascendant_degree)

    # Calculate house rulers
    house_rulers = {}
    for i, cusp in enumerate(cusps):
         sign_en, _, _ = degree_to_sign(cusp)
         ruler = SIGN_RULERS.get(sign_en, "Sun")
         house_rulers[i+1] = ruler

    # Get ascendant ruler
    asc_ruler = SIGN_RULERS.get(asc_sign_en, "Sun")

    result = NatalChartData(
        ascendant_degree=ascendant_degree,
        ascendant_sign=asc_sign_en,
        ascendant_sign_ru=asc_sign_ru,
        ascendant_ruler=asc_ruler,
        mc_degree=mc_degree,
        raw_cusps=cusps,
        house_rulers=house_rulers
    )


    # Calculate planet positions
    for planet_name, planet_code in PLANET_CODES.items():
        try:
            pos, flags = swe.calc_ut(jd, planet_code, swe.FLG_SWIEPH | swe.FLG_SPEED)
            degree = pos[0] % 360
            speed = pos[3]  # negative = retrograde
            retrograde = speed < 0
            is_stationary = abs(speed) < 0.03

            sign_en, sign_ru, position_in_sign = degree_to_sign(degree)
            house_num = get_house(degree, cusps)

            planet_data = PLANET_ARCHETYPE_MAP.get(planet_name, {})
            
            dignity, dignity_score = calculate_dignity(planet_name, sign_en)

            planet_pos = PlanetPosition(
                name=planet_data.get("name", planet_name),
                name_en=planet_name,
                degree=round(degree, 4),
                sign=sign_en,
                sign_ru=sign_ru,
                house=house_num,
                retrograde=retrograde,
                is_stationary=is_stationary,
                speed=round(speed, 6),
                archetype_id=planet_data.get("archetype_id", 0),
                sign_primary_archetype=0,
                sign_secondary_archetype=0,
                decan_ruler="",
                decan_ruler_archetype=0,
                priority=planet_data.get("priority", "medium"),
                dignity=dignity,
                dignity_score=dignity_score,
            )
            result.planets.append(planet_pos)

        except Exception as e:
            print(f"Error calculating {planet_name}: {e}")

    # Add South Node (opposite of True Node)
    true_node = next((p for p in result.planets if p.name_en == "TrueNode"), None)
    if true_node:
        south_degree = (true_node.degree + 180) % 360
        south_sign_en, south_sign_ru, _ = degree_to_sign(south_degree)
        south_house = get_house(south_degree, cusps)

        south_node = PlanetPosition(
            name="Южный узел",
            name_en="SouthNode",
            degree=round(south_degree, 4),
            sign=south_sign_en,
            sign_ru=south_sign_ru,
            house=south_house,
            retrograde=False,
            is_stationary=False,
            speed=0.0,
            archetype_id=12,  # Повешенный
            sign_primary_archetype=0,
            sign_secondary_archetype=0,
            decan_ruler="",
            decan_ruler_archetype=0,
            priority="additional",
        )
        result.planets.append(south_node)
        result.south_node_degree = south_degree
        result.south_node_sign = south_sign_en
        result.south_node_sign_ru = south_sign_ru

    # Add Part of Fortune (Фортуна)
    # Day: Asc + Moon - Sun | Night: Asc + Sun - Moon
    sun = next((p for p in result.planets if p.name_en == "Sun"), None)
    moon = next((p for p in result.planets if p.name_en == "Moon"), None)
    if sun and moon:
        sun_degree = sun.degree
        moon_degree = moon.degree
        # Determine if day or night (Sun above/below horizon)
        is_day = get_house(sun_degree, cusps) > 6

        if is_day:
            fortune_degree = (ascendant_degree + moon_degree - sun_degree) % 360
        else:
            fortune_degree = (ascendant_degree + sun_degree - moon_degree) % 360
        
        f_sign_en, f_sign_ru, _ = degree_to_sign(fortune_degree)
        f_house = get_house(fortune_degree, cusps)

        fortune = PlanetPosition(
            name="Колесо Фортуны",
            name_en="PartFortune",
            degree=round(fortune_degree, 4),
            sign=f_sign_en,
            sign_ru=f_sign_ru,
            house=f_house,
            retrograde=False,
            is_stationary=False,
            speed=0.0,
            archetype_id=10,  # Колесо Фортуны
            sign_primary_archetype=0,
            sign_secondary_archetype=0,
            decan_ruler="",
            decan_ruler_archetype=0,
            priority="high",
        )
        result.planets.append(fortune)

    # 4. Calculate dispositor chains
    result.dispositor_chains = calculate_dispositor_chains(result.planets)

    return result


def to_dict(chart: NatalChartData) -> dict:
    """Serialize NatalChartData to JSON-serializable dict."""
    return {
        "ascendant": {
            "degree": chart.ascendant_degree,
            "sign": chart.ascendant_sign,
            "sign_ru": chart.ascendant_sign_ru,
            "ruler": chart.ascendant_ruler,
        },
        "mc_degree": chart.mc_degree,
        "south_node": {
            "degree": chart.south_node_degree,
            "sign": chart.south_node_sign,
            "sign_ru": chart.south_node_sign_ru,
        },
        "planets": [
            {
                "name": p.name,
                "name_en": p.name_en,
                "degree": p.degree,
                "sign": p.sign,
                "sign_ru": p.sign_ru,
                "house": p.house,
                "retrograde": p.retrograde,
                "is_stationary": p.is_stationary,
                "speed": p.speed,
                "archetype_id": p.archetype_id,
                "sign_primary_archetype": p.sign_primary_archetype,
                "sign_secondary_archetype": p.sign_secondary_archetype,
                "decan_ruler": p.decan_ruler,
                "decan_ruler_archetype": p.decan_ruler_archetype,
                "priority": p.priority,
                "dignity": p.dignity,
                "dignity_score": p.dignity_score,
            }
            for p in chart.planets
        ],
        "cusps": chart.raw_cusps,
        "house_rulers": chart.house_rulers,
        "dispositor_chains": chart.dispositor_chains,
    }

