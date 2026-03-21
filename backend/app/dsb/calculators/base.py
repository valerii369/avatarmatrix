from __future__ import annotations
"""
DSB Calculators — базовый класс.

Каждый калькулятор реализует Calculator.calculate(birth_data) → dict.
Принцип plug-and-play: добавление нового учения = написать класс-наследник.
Ядро системы (Слои 3-4) не меняется.
"""

from abc import ABC, abstractmethod
import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BirthData(BaseModel):
    """Входные данные для любого калькулятора."""
    date: datetime.date                     # Дата рождения (YYYY-MM-DD)
    time: Optional[datetime.time] = None    # Время рождения (HH:MM)
    place: str                           # Город / место рождения
    lat: Optional[float] = None          # Широта (геокодированная)
    lon: Optional[float] = None          # Долгота (геокодированная)
    timezone: Optional[str] = None       # Часовой пояс (напр. "Europe/Kiev")
    full_name: Optional[str] = None      # ФИО (для нумерологии)

    class Config:
        json_encoders = {datetime.date: str, datetime.time: str}


class Calculator(ABC):
    """
    Абстрактный базовый класс для всех калькуляторов учений.

    Каждый подкласс:
    - Определяет system_name (идентификатор учения)
    - Реализует calculate(birth_data) → dict в формате из секции 3.2 документа
    - Является идемпотентным: одни входные данные = один и тот же выход
    - Не знает о других калькуляторах
    """

    system_name: str = ""

    @abstractmethod
    async def calculate(self, birth_data: BirthData) -> dict:
        """
        Рассчитывает сырые данные учения по данным рождения.

        Возвращает JSON в формате:
        {
            "system": "<system_name>",
            "raw_data": { ... },
            "calculated_at": "<ISO timestamp>",
            "input_birth_data": { ... }
        }
        """
        pass

    def _base_envelope(self, birth_data: BirthData, raw_data: dict) -> dict:
        """Оборачивает raw_data в стандартный конверт."""
        from datetime import datetime, timezone
        return {
            "system": self.system_name,
            "raw_data": raw_data,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "input_birth_data": birth_data.model_dump(mode="json"),
        }
