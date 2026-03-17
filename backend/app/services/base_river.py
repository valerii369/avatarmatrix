from abc import ABC, abstractmethod
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

class BaseRiver(ABC):
    """
    Base class for Level 2 (River) services.
    A River takes Level 1 (Rain) data and uses an LLM Agent to interpret it.
    """
    
    @abstractmethod
    async def flow(self, db: AsyncSession, user_id: int, rain_data: Any) -> Dict[str, Any]:
        """
        Processes Rain data and returns a structured interpretation for the Ocean.
        """
        pass
