"""
Natal chart calculation engine using pyswisseph.
Computes planet positions, signs, houses, and retrograde status.
"""
import json
import os
from dataclasses import dataclass, field
from typing import Optional
import swisseph as swe
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from datetime import datetime
import pytz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")

with open(os.path.join(DATA_DIR, "planet_archetype_map.json")) as f:
    PLANET_ARCHETYPE_MAP = json.load(f)

with open(os.path.join(DATA_DIR, "sign_archetype_map.json")) as f:
    SIGN_ARCHETYPE_MAP = json.load(f)

with open(os.path.join(DATA_DIR, "house_sphere_map.json")) as f:
    HOUSE_SPHERE_MAP = json.load(f)

with open(os.path.join(DATA_DIR, "decan_map.json")) as f:
    DECAN_MAP = json.load(f)

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


async def geocode_place(place: str) -> tuple[float, float, str]:
    """Get latitude, longitude and timezone from place name."""
    geolocator = Nominatim(user_agent="avatar_app")
    location = geolocator.geocode(place)
    if not location:
        raise ValueError(f"Cannot geocode place: {place}")

    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lng=location.longitude, lat=location.latitude)
    return location.latitude, location.longitude, tz_name or "UTC"


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

    # Get ascendant ruler
    asc_ruler = SIGN_ARCHETYPE_MAP.get(asc_sign_en, {}).get("ruler", "Sun")

    result = NatalChartData(
        ascendant_degree=ascendant_degree,
        ascendant_sign=asc_sign_en,
        ascendant_sign_ru=asc_sign_ru,
        ascendant_ruler=asc_ruler,
        mc_degree=mc_degree,
        raw_cusps=cusps,
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
            sign_data = SIGN_ARCHETYPE_MAP.get(sign_en, {})
            
            # Decan logic
            decan_idx = int(position_in_sign // 10)
            if decan_idx > 2: decan_idx = 2
            decan_ruler = DECAN_MAP.get(sign_en, ["Sun", "Sun", "Sun"])[decan_idx]
            decan_ruler_archetype = PLANET_ARCHETYPE_MAP.get(decan_ruler, {}).get("archetype_id", 0)

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
                sign_primary_archetype=sign_data.get("primary_archetype", 0),
                sign_secondary_archetype=sign_data.get("secondary_archetype", 0),
                decan_ruler=decan_ruler,
                decan_ruler_archetype=decan_ruler_archetype,
                priority=planet_data.get("priority", "medium"),
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
        south_sign_data = SIGN_ARCHETYPE_MAP.get(south_sign_en, {})

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
            sign_primary_archetype=south_sign_data.get("primary_archetype", 0),
            sign_secondary_archetype=south_sign_data.get("secondary_archetype", 0),
            decan_ruler=DECAN_MAP.get(south_sign_en, ["Sun", "Sun", "Sun"])[min(int((south_degree % 30) // 10), 2)],
            decan_ruler_archetype=PLANET_ARCHETYPE_MAP.get(DECAN_MAP.get(south_sign_en, ["Sun"])[0], {}).get("archetype_id", 0),
            priority="additional",
        )
        result.planets.append(south_node)
        result.south_node_degree = south_degree
        result.south_node_sign = south_sign_en
        result.south_node_sign_ru = south_sign_ru

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
            }
            for p in chart.planets
        ],
        "cusps": chart.raw_cusps,
    }
