import httpx
import logging
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class AstrologyAPIClient:
    """
    Client for https://astrologyapi.com/
    Uses Western Astrology endpoints.
    """
    BASE_URL = "https://json.astrologyapi.com/v1"

    def __init__(self):
        self.user_id = settings.ASTROLOGY_API_USER_ID
        self.api_key = settings.ASTROLOGY_API_KEY
        if not self.user_id or not self.api_key:
            logger.warning("ASTROLOGY_API_USER_ID or ASTROLOGY_API_KEY not set in config.")

    async def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/{endpoint}"
        auth = (self.user_id, self.api_key)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=data, auth=auth, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"AstrologyAPI HTTP error: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"AstrologyAPI error: {e}")
                raise

    async def get_western_horoscope(
        self, 
        day: int, month: int, year: int, 
        hour: int, minute: int, 
        lat: float, lon: float, tzone: float
    ) -> Dict[str, Any]:
        """
        Fetches full western horoscope data (planets, houses, aspects).
        """
        data = {
            "day": day,
            "month": month,
            "year": year,
            "hour": hour,
            "min": minute,
            "lat": lat,
            "lon": lon,
            "tzone": tzone
        }
        return await self._post("western_horoscope", data)

    async def get_natal_chart_data(self, birth_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper to fetch data based on a combined birth data dict.
        """
        # AstrologyAPI expects tzone as a float (e.g. 3.0)
        # We might need to convert tz_name to offset if not provided.
        # For now, we assume birth_data has day, month, year, hour, min, lat, lon, tzone.
        return await self.get_western_horoscope(
            day=birth_data["day"],
            month=birth_data["month"],
            year=birth_data["year"],
            hour=birth_data["hour"],
            minute=birth_data["min"],
            lat=birth_data["lat"],
            lon=birth_data["lon"],
            tzone=birth_data.get("tzone", 0.0)
        )
