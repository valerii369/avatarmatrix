import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    async def send_tg_message(tg_id: int, text: str, parse_mode: str = "HTML"):
        """Sends a telegram message from the backend."""
        url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": tg_id,
            "text": text,
            "parse_mode": parse_mode
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.error(f"Failed to send TG message to {tg_id}: {resp.text}")
                else:
                    logger.info(f"Successfully sent TG message to {tg_id}")
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Error sending TG message to {tg_id}: {e}")
            return False
