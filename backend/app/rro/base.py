import datetime
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

class RiverOutput(BaseModel):
    """
    Standardized output from any Level 2 (River) service.
    """
    source: str = Field(..., description="Name of the source river (e.g., 'astro_river')")
    domain: str = Field(..., description="Domain of knowledge (e.g., 'astrology', 'psychology')")
    content: Dict[str, Any] = Field(..., description="The interpreted psychological/domain data")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())

class BaseRiver(ABC):
    """
    Abstract Base Class for Level 2 (River) services.
    """

    @abstractmethod
    async def flow(self, db: AsyncSession, user_id: int, rain_data: Any) -> RiverOutput:
        """
        Processes Rain data and returns a structured interpretation for the Ocean.
        """
        pass
